"""Manually-triggered rent reminders.

The scheduled reminder ladder (§10.2) only fires at fixed day-3/5/7 milestones.
These endpoints let an owner send a reminder on demand from the app, for a single
invoice or for every open invoice of a tenant. They dispatch immediately (no Celery
worker required) and log each send to notifications_log.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from rent_manager.db.models import Invoice, NotificationLog, Tenant
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.integrations.email import send_email
from rent_manager.integrations.whatsapp import render, send_whatsapp_message

router = APIRouter()

MANUAL_PURPOSE = "reminder_manual"
OPEN_STATUSES = ("pending", "partial", "overdue")


class ReminderResult(BaseModel):
    sent: int
    skipped: int
    channels: list[str]
    detail: str


async def _record(
    db: DbSession,
    *,
    organization_id: UUID,
    tenant_id: UUID,
    channel: str,
    language: str,
    payload: dict,
    external_id: str,
    idempotency_key: str,
) -> None:
    stmt = (
        insert(NotificationLog)
        .values(
            organization_id=organization_id,
            tenant_id=tenant_id,
            channel=channel,
            purpose=MANUAL_PURPOSE,
            language=language,
            template_key=MANUAL_PURPOSE,
            payload_snapshot=payload,
            external_id=external_id,
            status="sent",
            idempotency_key=idempotency_key,
        )
        .on_conflict_do_nothing(constraint="uq_notifications_org_idempotency")
    )
    await db.execute(stmt)


async def _send_for_invoice(db: DbSession, tenant: Tenant, invoice: Invoice) -> list[str]:
    """Dispatch a manual reminder for one invoice. Returns the channels used."""
    channels: list[str] = []
    variables = {
        "name": tenant.name,
        "amount": str(invoice.amount_due - invoice.amount_paid),
        "month": invoice.billing_month.strftime("%B %Y"),
    }
    # A fresh idempotency key per call so an owner can re-send if they want.
    stamp = uuid4().hex[:8]

    if tenant.whatsapp_opt_in:
        sent = send_whatsapp_message(
            to_phone_e164=tenant.phone_e164,
            template_key=MANUAL_PURPOSE,
            language=tenant.language,
            variables=variables,
        )
        await _record(
            db,
            organization_id=invoice.organization_id,
            tenant_id=tenant.id,
            channel="whatsapp",
            language=tenant.language,
            payload={"variables": variables, "body": sent.get("body")},
            external_id=sent["external_id"],
            idempotency_key=f"{invoice.id}:manual:{stamp}:whatsapp",
        )
        channels.append("whatsapp")

    if tenant.email and tenant.email_opt_in:
        body = render(MANUAL_PURPOSE, tenant.language, variables)
        sent = send_email(
            to_email=tenant.email,
            subject_key=MANUAL_PURPOSE,
            body_text=body,
            language=tenant.language,
            variables=variables,
        )
        await _record(
            db,
            organization_id=invoice.organization_id,
            tenant_id=tenant.id,
            channel="email",
            language=tenant.language,
            payload={"variables": variables, "body": body},
            external_id=sent["external_id"],
            idempotency_key=f"{invoice.id}:manual:{stamp}:email",
        )
        channels.append("email")

    return channels


@router.post("/tenant/{tenant_id}", response_model=ReminderResult)
async def remind_tenant(
    tenant_id: UUID, current: CurrentUserDep, db: DbSession
) -> ReminderResult:
    tenant = (
        await db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.organization_id == current.organization_id,
            )
        )
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    invoices = (
        await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant.id,
                Invoice.organization_id == current.organization_id,
                Invoice.status.in_(OPEN_STATUSES),
            )
        )
    ).scalars().all()

    if not invoices:
        raise HTTPException(status_code=409, detail="This tenant has no pending rent to remind about")

    used: set[str] = set()
    sent = 0
    skipped = 0
    for inv in invoices:
        channels = await _send_for_invoice(db, tenant, inv)
        if channels:
            sent += 1
            used.update(channels)
        else:
            skipped += 1
    await db.commit()

    if sent == 0:
        raise HTTPException(
            status_code=409,
            detail="Tenant has opted out of WhatsApp and email reminders",
        )

    return ReminderResult(
        sent=sent,
        skipped=skipped,
        channels=sorted(used),
        detail=f"Reminder sent to {tenant.name} via {', '.join(sorted(used))}.",
    )


@router.post("/invoice/{invoice_id}", response_model=ReminderResult)
async def remind_invoice(
    invoice_id: UUID, current: CurrentUserDep, db: DbSession
) -> ReminderResult:
    invoice = (
        await db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.organization_id == current.organization_id,
            )
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == invoice.tenant_id))
    ).scalar_one()

    channels = await _send_for_invoice(db, tenant, invoice)
    await db.commit()
    if not channels:
        raise HTTPException(
            status_code=409, detail="Tenant has opted out of WhatsApp and email reminders"
        )
    return ReminderResult(
        sent=1,
        skipped=0,
        channels=sorted(set(channels)),
        detail=f"Reminder sent to {tenant.name} via {', '.join(sorted(set(channels)))}.",
    )
