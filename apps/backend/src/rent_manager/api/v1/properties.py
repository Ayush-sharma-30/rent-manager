from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from rent_manager.db.models import Property
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.property import PropertyCreate, PropertyOut, PropertyUpdate

router = APIRouter()


@router.get("", response_model=list[PropertyOut])
async def list_properties(
    current: CurrentUserDep, db: DbSession, include_archived: bool = False
) -> list[PropertyOut]:
    stmt = select(Property).where(Property.organization_id == current.organization_id)
    if not include_archived:
        stmt = stmt.where(Property.archived_at.is_(None))
    stmt = stmt.order_by(Property.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [PropertyOut.model_validate(r) for r in rows]


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
async def create_property(
    body: PropertyCreate, current: CurrentUserDep, db: DbSession
) -> PropertyOut:
    prop = Property(organization_id=current.organization_id, **body.model_dump())
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return PropertyOut.model_validate(prop)


async def _get_or_404(db, current, property_id: UUID) -> Property:
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


@router.get("/{property_id}", response_model=PropertyOut)
async def get_property(property_id: UUID, current: CurrentUserDep, db: DbSession) -> PropertyOut:
    prop = await _get_or_404(db, current, property_id)
    return PropertyOut.model_validate(prop)


@router.patch("/{property_id}", response_model=PropertyOut)
async def update_property(
    property_id: UUID, body: PropertyUpdate, current: CurrentUserDep, db: DbSession
) -> PropertyOut:
    prop = await _get_or_404(db, current, property_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(prop, k, v)
    await db.commit()
    await db.refresh(prop)
    return PropertyOut.model_validate(prop)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_property(property_id: UUID, current: CurrentUserDep, db: DbSession) -> None:
    prop = await _get_or_404(db, current, property_id)
    prop.archived_at = datetime.now(timezone.utc)
    await db.commit()
