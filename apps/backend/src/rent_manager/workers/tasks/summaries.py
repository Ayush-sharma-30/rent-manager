from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from rent_manager.db.models import Invoice, Lease, NotificationLog, Organization, User
from rent_manager.db.session import SyncSessionLocal
from rent_manager.integrations.whatsapp import send_whatsapp_message
from rent_manager.workers.celery_app import celery_app


@celery_app.task(name="rent_manager.workers.tasks.summaries.send_weekly_summary")
def send_weekly_summary() -> dict:
    today = date.today()
    iso_week = today.isocalendar()
    week_key = f"{iso_week.year}-W{iso_week.week:02d}"
    month_start = today.replace(day=1)
    cutoff = today + timedelta(days=45)
    sent = 0

    with SyncSessionLocal() as db:
        orgs = db.execute(select(Organization)).scalars().all()
        for org in orgs:
            owner = db.execute(
                select(User).where(User.organization_id == org.id, User.role == "owner")
            ).scalar_one_or_none()
            if owner is None:
                continue

            collected = db.execute(
                select(func.coalesce(func.sum(Invoice.amount_paid), 0)).where(
                    Invoice.organization_id == org.id,
                    Invoice.billing_month == month_start,
                )
            ).scalar_one()
            target = db.execute(
                select(func.coalesce(func.sum(Invoice.amount_due), 0)).where(
                    Invoice.organization_id == org.id,
                    Invoice.billing_month == month_start,
                )
            ).scalar_one()
            overdue = db.execute(
                select(func.coalesce(func.sum(Invoice.amount_due - Invoice.amount_paid), 0)).where(
                    Invoice.organization_id == org.id,
                    Invoice.status == "overdue",
                )
            ).scalar_one()
            expiring_count = db.execute(
                select(func.count()).where(
                    Lease.organization_id == org.id,
                    Lease.status == "active",
                    Lease.end_date <= cutoff,
                )
            ).scalar_one()

            variables = {
                "collected": str(Decimal(collected)),
                "pending": str(Decimal(target) - Decimal(collected)),
                "overdue": str(Decimal(overdue)),
                "expiring_count": str(expiring_count),
            }
            res = send_whatsapp_message(
                to_phone_e164=owner.phone_e164,
                template_key="owner_weekly_summary",
                language=owner.language,
                variables=variables,
            )
            stmt = (
                insert(NotificationLog)
                .values(
                    organization_id=org.id,
                    user_id=owner.id,
                    channel="whatsapp",
                    purpose="weekly_summary",
                    language=owner.language,
                    template_key="owner_weekly_summary",
                    payload_snapshot={"variables": variables, "body": res.get("body")},
                    external_id=res["external_id"],
                    status="sent",
                    idempotency_key=f"summary:{org.id}:{week_key}",
                )
                .on_conflict_do_nothing(constraint="uq_notifications_org_idempotency")
                .returning(NotificationLog.id)
            )
            if db.execute(stmt).scalar_one_or_none() is not None:
                sent += 1
        db.commit()
    return {"summaries_sent": sent, "iso_week": week_key}
