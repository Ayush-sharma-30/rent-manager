from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from rent_manager.db.models import Property, Unit
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.unit import BulkCreateResult, UnitBulkCreate, UnitCreate, UnitOut, UnitUpdate

router = APIRouter()


async def _ensure_property(db, current, property_id: UUID) -> Property:
    prop = (
        await db.execute(
            select(Property).where(
                Property.id == property_id, Property.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.get("/properties/{property_id}/units", response_model=list[UnitOut])
async def list_units(
    property_id: UUID,
    current: CurrentUserDep,
    db: DbSession,
    include_archived: bool = False,
) -> list[UnitOut]:
    await _ensure_property(db, current, property_id)
    stmt = select(Unit).where(Unit.property_id == property_id)
    if not include_archived:
        stmt = stmt.where(Unit.archived_at.is_(None))
    stmt = stmt.order_by(Unit.identifier.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [UnitOut.model_validate(r) for r in rows]


@router.post(
    "/properties/{property_id}/units",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    property_id: UUID, body: UnitCreate, current: CurrentUserDep, db: DbSession
) -> UnitOut:
    await _ensure_property(db, current, property_id)
    unit = Unit(
        organization_id=current.organization_id,
        property_id=property_id,
        **body.model_dump(),
    )
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.post(
    "/properties/{property_id}/units/bulk",
    response_model=BulkCreateResult,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_units(
    property_id: UUID, body: UnitBulkCreate, current: CurrentUserDep, db: DbSession
) -> BulkCreateResult:
    await _ensure_property(db, current, property_id)
    created: list[Unit] = []
    for u in body.units:
        unit = Unit(
            organization_id=current.organization_id, property_id=property_id, **u.model_dump()
        )
        db.add(unit)
        created.append(unit)
    await db.commit()
    for u in created:
        await db.refresh(u)
    return BulkCreateResult(
        created_count=len(created), units=[UnitOut.model_validate(u) for u in created]
    )


async def _get_unit(db, current, unit_id: UUID) -> Unit:
    unit = (
        await db.execute(
            select(Unit).where(
                Unit.id == unit_id, Unit.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.get("/units/{unit_id}", response_model=UnitOut)
async def get_unit(unit_id: UUID, current: CurrentUserDep, db: DbSession) -> UnitOut:
    return UnitOut.model_validate(await _get_unit(db, current, unit_id))


@router.patch("/units/{unit_id}", response_model=UnitOut)
async def update_unit(
    unit_id: UUID, body: UnitUpdate, current: CurrentUserDep, db: DbSession
) -> UnitOut:
    unit = await _get_unit(db, current, unit_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(unit, k, v)
    await db.commit()
    await db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_unit(unit_id: UUID, current: CurrentUserDep, db: DbSession) -> None:
    unit = await _get_unit(db, current, unit_id)
    unit.archived_at = datetime.now(timezone.utc)
    await db.commit()
