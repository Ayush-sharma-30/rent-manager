from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from rent_manager.db.models import Invoice, NotificationLog, Tenant
from rent_manager.db.session import SyncSessionLocal
from rent_manager.integrations.email import send_email
from rent_manager.integrations.whatsapp import render, send_whatsapp_message
from rent_manager.workers.celery_app import celery_app


REMINDER_PURPOSE = {3: "reminder_day_3", 5: "reminder_day_5", 7: "reminder_day_7"}


def _record_notification(
    db,
    *,
    organization_id: UUID,
    tenant_id: UUID,
    channel: str,
    purpose: str,
    language: str,
    template_key: str,
    payload: dict[str, Any],
    external_id: str,
    idempotency_key: str,
) -> bool:
    stmt = (
        insert(NotificationLog)
        .values(
            organization_id=organization_id,
            tenant_id=tenant_id,
            channel=channel,
            purpose=purpose,
            language=language,
            template_key=template_key,
            payload_snapshot=payload,
            external_id=external_id,
            status="sent",
            idempotency_key=idempotency_key,
        )
        .on_conflict_do_nothing(constraint="uq_notifications_org_idempotency")
        .returning(NotificationLog.id)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


@celery_app.task(name="rent_manager.workers.tasks.reminders.send_whatsapp_reminder")
def send_whatsapp_reminder(invoice_id: str, day: int) -> dict:
    purpose = REMINDER_PURPOSE[day]
    idem = f"{invoice_id}:{day}:whatsapp"
    with SyncSessionLocal() as db:
        invoice = db.execute(select(Invoice).where(Invoice.id == UUID(invoice_id))).scalar_one_or_none()
        if invoice is None:
            return {"skipped": "invoice_missing"}
        tenant = db.execute(select(Tenant).where(Tenant.id == invoice.tenant_id)).scalar_one()
        if not tenant.whatsapp_opt_in:
            return {"skipped": "opted_out"}
        variables = {
            "name": tenant.name,
            "amount": str(invoice.amount_due - invoice.amount_paid),
            "month": invoice.billing_month.strftime("%B %Y"),
        }
        sent = send_whatsapp_message(
            to_phone_e164=tenant.phone_e164,
            template_key=purpose,
            language=tenant.language,
            variables=variables,
        )
        inserted = _record_notification(
            db,
            organization_id=invoice.organization_id,
            tenant_id=tenant.id,
            channel="whatsapp",
            purpose=purpose,
            language=tenant.language,
            template_key=purpose,
            payload={"variables": variables, "body": sent.get("body")},
            external_id=sent["external_id"],
            idempotency_key=idem,
        )
        db.commit()
        return {"inserted": inserted, "external_id": sent["external_id"]}


@celery_app.task(name="rent_manager.workers.tasks.reminders.send_email_reminder")
def send_email_reminder(invoice_id: str, day: int) -> dict:
    purpose = REMINDER_PURPOSE[day]
    idem = f"{invoice_id}:{day}:email"
    with SyncSessionLocal() as db:
        invoice = db.execute(select(Invoice).where(Invoice.id == UUID(invoice_id))).scalar_one_or_none()
        if invoice is None:
            return {"skipped": "invoice_missing"}
        tenant = db.execute(select(Tenant).where(Tenant.id == invoice.tenant_id)).scalar_one()
        if not tenant.email or not tenant.email_opt_in:
            return {"skipped": "no_email_or_opt_out"}
        variables = {
            "name": tenant.name,
            "amount": str(invoice.amount_due - invoice.amount_paid),
            "month": invoice.billing_month.strftime("%B %Y"),
        }
        body = render(purpose, tenant.language, variables)
        sent = send_email(
            to_email=tenant.email,
            subject_key=purpose,
            body_text=body,
            language=tenant.language,
            variables=variables,
        )
        inserted = _record_notification(
            db,
            organization_id=invoice.organization_id,
            tenant_id=tenant.id,
            channel="email",
            purpose=purpose,
            language=tenant.language,
            template_key=purpose,
            payload={"variables": variables, "body": body},
            external_id=sent["external_id"],
            idempotency_key=idem,
        )
        db.commit()
        return {"inserted": inserted, "external_id": sent["external_id"]}


@celery_app.task(name="rent_manager.workers.tasks.reminders.run_reminder_ladder")
def run_reminder_ladder() -> dict:
    """Implements §10.2 — dispatch reminders for invoices at day 3, 5, 7 of unpaid."""
    today = date.today()
    queued = 0
    with SyncSessionLocal() as db:
        invoices = db.execute(
            select(Invoice).where(Invoice.status.in_(["pending", "partial", "overdue"]))
        ).scalars().all()
        for inv in invoices:
            days_overdue = (today - inv.due_date).days
            for milestone in (7, 5, 3):
                if days_overdue == milestone and inv.last_reminder_day < milestone:
                    send_whatsapp_reminder.delay(str(inv.id), milestone)
                    send_email_reminder.delay(str(inv.id), milestone)
                    inv.last_reminder_day = milestone
                    queued += 2
                    break
        db.commit()
    return {"queued_tasks": queued}
