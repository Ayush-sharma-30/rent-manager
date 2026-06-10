from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from rent_manager.db.models import Invoice, Lease, Payment, Tenant, Unit
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.dashboard import (
    DashboardSummary,
    LeaseExpiringItem,
    LeasesExpiringOut,
    NeedsAttentionItem,
    RecentlyPaidItem,
)

router = APIRouter()


def _parse_month(month: str | None) -> date:
    if month is None:
        today = date.today()
        return today.replace(day=1)
    try:
        return date.fromisoformat(month + "-01")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="month must be YYYY-MM") from exc


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current: CurrentUserDep, db: DbSession, month: str | None = None
) -> DashboardSummary:
    start = _parse_month(month)
    target = (
        await db.execute(
            select(func.coalesce(func.sum(Invoice.amount_due), 0)).where(
                Invoice.organization_id == current.organization_id,
                Invoice.billing_month == start,
            )
        )
    ).scalar_one()
    collected = (
        await db.execute(
            select(func.coalesce(func.sum(Invoice.amount_paid), 0)).where(
                Invoice.organization_id == current.organization_id,
                Invoice.billing_month == start,
            )
        )
    ).scalar_one()
    today = date.today()
    # Bucket this month's invoices. "overdue" is driven by the due date rather
    # than the status column, because in deployments without the Celery worker
    # nothing flips pending -> overdue. An invoice is overdue when it's still
    # open (not fully paid) and its due date has passed.
    status_rows = (
        await db.execute(
            select(Invoice.status, Invoice.due_date).where(
                Invoice.organization_id == current.organization_id,
                Invoice.billing_month == start,
            )
        )
    ).all()
    paid_count = 0
    open_count = 0  # all unpaid invoices (the "pending" bucket / outstanding)
    overdue_count = 0
    for inv_status, inv_due in status_rows:
        if inv_status == "paid":
            paid_count += 1
            continue
        open_count += 1
        if inv_due < today:
            overdue_count += 1
    needs_rows = (
        await db.execute(
            select(Invoice, Tenant, Unit)
            .join(Tenant, Tenant.id == Invoice.tenant_id)
            .join(Unit, Unit.id == Invoice.unit_id)
            .where(
                Invoice.organization_id == current.organization_id,
                Invoice.status.in_(["pending", "partial", "overdue"]),
                Invoice.due_date <= today,
            )
            .order_by(Invoice.due_date.asc())
            .limit(20)
        )
    ).all()
    needs_attention = [
        NeedsAttentionItem(
            tenant_id=t.id,
            tenant_name=t.name,
            unit_identifier=u.identifier,
            amount_due=(i.amount_due - i.amount_paid),
            due_date=i.due_date,
            days_overdue=max(0, (today - i.due_date).days),
        )
        for i, t, u in needs_rows
    ]

    paid_rows = (
        await db.execute(
            select(Payment, Tenant)
            .join(Tenant, Tenant.id == Payment.tenant_id)
            .where(Payment.organization_id == current.organization_id)
            .order_by(Payment.paid_on.desc(), Payment.created_at.desc())
            .limit(10)
        )
    ).all()
    recently_paid = [
        RecentlyPaidItem(
            payment_id=p.id,
            tenant_id=t.id,
            tenant_name=t.name,
            amount=p.amount,
            paid_on=p.paid_on,
        )
        for p, t in paid_rows
    ]

    return DashboardSummary(
        month=start.isoformat()[:7],
        collected=Decimal(collected),
        target=Decimal(target),
        paid_count=paid_count,
        pending_count=open_count,
        overdue_count=overdue_count,
        needs_attention=needs_attention,
        recently_paid=recently_paid,
    )


@router.get("/leases-expiring", response_model=LeasesExpiringOut)
async def leases_expiring(
    current: CurrentUserDep, db: DbSession, within_days: int = 45
) -> LeasesExpiringOut:
    today = date.today()
    cutoff = today + timedelta(days=within_days)
    rows = (
        await db.execute(
            select(Lease, Tenant, Unit)
            .join(Tenant, Tenant.id == Lease.tenant_id)
            .join(Unit, Unit.id == Lease.unit_id)
            .where(
                Lease.organization_id == current.organization_id,
                Lease.status == "active",
                Lease.end_date <= cutoff,
            )
            .order_by(Lease.end_date.asc())
        )
    ).all()
    items = [
        LeaseExpiringItem(
            lease_id=l.id,
            tenant_id=t.id,
            tenant_name=t.name,
            unit_identifier=u.identifier,
            end_date=l.end_date,
            days_until_expiry=(l.end_date - today).days,
        )
        for l, t, u in rows
    ]
    return LeasesExpiringOut(leases=items)
