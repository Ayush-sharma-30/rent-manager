from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from rent_manager.db.models import Invoice, Lease
from rent_manager.db.session import SyncSessionLocal
from rent_manager.workers.celery_app import celery_app


def _billing_month_for_today(today: date) -> date:
    return today.replace(day=1)


def _due_date_for(today: date, billing_day: int) -> date:
    last_day = monthrange(today.year, today.month)[1]
    return today.replace(day=min(billing_day, last_day))


@celery_app.task(name="rent_manager.workers.tasks.invoices.generate_monthly_invoices")
def generate_monthly_invoices() -> dict:
    today = date.today()
    billing_month = _billing_month_for_today(today)
    created = 0
    with SyncSessionLocal() as db:
        leases = db.execute(
            select(Lease).where(Lease.status == "active", Lease.billing_day == today.day)
        ).scalars().all()
        for lease in leases:
            exists = db.execute(
                select(Invoice).where(
                    Invoice.lease_id == lease.id, Invoice.billing_month == billing_month
                )
            ).scalar_one_or_none()
            if exists:
                continue
            due_date = _due_date_for(today, lease.billing_day)
            inv = Invoice(
                organization_id=lease.organization_id,
                lease_id=lease.id,
                tenant_id=lease.tenant_id,
                unit_id=lease.unit_id,
                billing_month=billing_month,
                due_date=due_date,
                amount_due=Decimal(lease.monthly_rent),
                amount_paid=Decimal("0"),
                status="pending",
                last_reminder_day=0,
            )
            db.add(inv)
            created += 1
        db.commit()
    return {"created": created, "billing_month": billing_month.isoformat()}


@celery_app.task(name="rent_manager.workers.tasks.invoices.mark_overdue_invoices")
def mark_overdue_invoices() -> dict:
    yesterday = date.today() - timedelta(days=1)
    updated = 0
    with SyncSessionLocal() as db:
        rows = db.execute(
            select(Invoice).where(
                Invoice.due_date < yesterday,
                Invoice.status.in_(["pending", "partial"]),
            )
        ).scalars().all()
        for inv in rows:
            inv.status = "overdue"
            updated += 1
        db.commit()
    return {"updated": updated}
