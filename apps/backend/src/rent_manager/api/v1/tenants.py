from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from rent_manager.db.models import Tenant
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.tenant import TenantCreate, TenantOut, TenantUpdate
from rent_manager.utils.phone import normalize_indian_phone

router = APIRouter()


@router.get("", response_model=list[TenantOut])
async def list_tenants(
    current: CurrentUserDep,
    db: DbSession,
    q: str | None = None,
    active: bool = True,
) -> list[TenantOut]:
    stmt = select(Tenant).where(Tenant.organization_id == current.organization_id)
    if active:
        stmt = stmt.where(Tenant.archived_at.is_(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Tenant.name.ilike(like), Tenant.phone_e164.ilike(like)))
    stmt = stmt.order_by(Tenant.name.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [TenantOut.model_validate(r) for r in rows]


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate, current: CurrentUserDep, db: DbSession
) -> TenantOut:
    try:
        phone = normalize_indian_phone(body.phone_e164)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    payload = body.model_dump()
    payload["phone_e164"] = phone
    tenant = Tenant(organization_id=current.organization_id, **payload)
    db.add(tenant)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Tenant with this phone already exists in your organization"
        ) from exc
    await db.refresh(tenant)
    return TenantOut.model_validate(tenant)


async def _get_or_404(db, current, tenant_id: UUID) -> Tenant:
    t = (
        await db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id, Tenant.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: UUID, current: CurrentUserDep, db: DbSession) -> TenantOut:
    return TenantOut.model_validate(await _get_or_404(db, current, tenant_id))


@router.patch("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: UUID, body: TenantUpdate, current: CurrentUserDep, db: DbSession
) -> TenantOut:
    t = await _get_or_404(db, current, tenant_id)
    data = body.model_dump(exclude_none=True)
    if "phone_e164" in data:
        try:
            data["phone_e164"] = normalize_indian_phone(data["phone_e164"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    for k, v in data.items():
        setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    return TenantOut.model_validate(t)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_tenant(tenant_id: UUID, current: CurrentUserDep, db: DbSession) -> None:
    t = await _get_or_404(db, current, tenant_id)
    t.archived_at = datetime.now(timezone.utc)
    await db.commit()
