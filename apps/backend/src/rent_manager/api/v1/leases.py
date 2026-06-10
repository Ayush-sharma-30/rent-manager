from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from rent_manager.db.models import Lease, Tenant, Unit
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.lease import LeaseCreate, LeaseEndIn, LeaseOut, LeaseRenewIn

router = APIRouter()


@router.get("", response_model=list[LeaseOut])
async def list_leases(
    current: CurrentUserDep,
    db: DbSession,
    status_filter: str | None = None,
    expiring_within_days: int | None = None,
) -> list[LeaseOut]:
    stmt = select(Lease).where(Lease.organization_id == current.organization_id)
    if status_filter:
        stmt = stmt.where(Lease.status == status_filter)
    if expiring_within_days is not None:
        cutoff = date.today() + timedelta(days=expiring_within_days)
        stmt = stmt.where(Lease.end_date <= cutoff, Lease.status == "active")
    stmt = stmt.order_by(Lease.end_date.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [LeaseOut.model_validate(r) for r in rows]


@router.post("", response_model=LeaseOut, status_code=status.HTTP_201_CREATED)
async def create_lease(
    body: LeaseCreate, current: CurrentUserDep, db: DbSession
) -> LeaseOut:
    unit = (
        await db.execute(
            select(Unit).where(
                Unit.id == body.unit_id, Unit.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    tenant = (
        await db.execute(
            select(Tenant).where(
                Tenant.id == body.tenant_id, Tenant.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")

    lease = Lease(
        organization_id=current.organization_id,
        unit_id=body.unit_id,
        tenant_id=body.tenant_id,
        start_date=body.start_date,
        end_date=body.end_date,
        monthly_rent=body.monthly_rent,
        security_deposit=body.security_deposit,
        billing_day=body.billing_day,
        notes=body.notes,
        status="active",
    )
    db.add(lease)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Active lease already exists for this unit"
        ) from exc
    await db.refresh(lease)
    return LeaseOut.model_validate(lease)


async def _get_or_404(db, current, lease_id: UUID) -> Lease:
    lease = (
        await db.execute(
            select(Lease).where(
                Lease.id == lease_id, Lease.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if lease is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    return lease


@router.get("/{lease_id}", response_model=LeaseOut)
async def get_lease(lease_id: UUID, current: CurrentUserDep, db: DbSession) -> LeaseOut:
    return LeaseOut.model_validate(await _get_or_404(db, current, lease_id))


@router.post("/{lease_id}/renew", response_model=LeaseOut)
async def renew_lease(
    lease_id: UUID, body: LeaseRenewIn, current: CurrentUserDep, db: DbSession
) -> LeaseOut:
    lease = await _get_or_404(db, current, lease_id)
    if lease.status != "active":
        raise HTTPException(status_code=409, detail="Only active leases can be renewed")
    lease.end_date = body.new_end_date
    lease.monthly_rent = body.new_monthly_rent
    lease.renewal_status = "renewed"
    await db.commit()
    await db.refresh(lease)
    return LeaseOut.model_validate(lease)


@router.post("/{lease_id}/end", response_model=LeaseOut)
async def end_lease(
    lease_id: UUID, body: LeaseEndIn, current: CurrentUserDep, db: DbSession
) -> LeaseOut:
    lease = await _get_or_404(db, current, lease_id)
    lease.status = "terminated_early" if body.ended_on < lease.end_date else "ended"
    lease.end_date = body.ended_on
    if body.reason:
        lease.notes = (lease.notes + " | " if lease.notes else "") + f"Ended: {body.reason}"
    await db.commit()
    await db.refresh(lease)
    return LeaseOut.model_validate(lease)
