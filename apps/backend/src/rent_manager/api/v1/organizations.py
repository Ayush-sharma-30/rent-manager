from fastapi import APIRouter
from sqlalchemy import select

from rent_manager.db.models import Organization
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.auth import OrganizationOut

router = APIRouter()


@router.get("/me", response_model=OrganizationOut)
async def get_my_org(current: CurrentUserDep, db: DbSession) -> OrganizationOut:
    org = (
        await db.execute(select(Organization).where(Organization.id == current.organization_id))
    ).scalar_one()
    return OrganizationOut.model_validate(org)


@router.patch("/me", response_model=OrganizationOut)
async def update_my_org(
    body: dict, current: CurrentUserDep, db: DbSession
) -> OrganizationOut:
    org = (
        await db.execute(select(Organization).where(Organization.id == current.organization_id))
    ).scalar_one()
    allowed = {"name", "email", "default_language"}
    for k, v in body.items():
        if k in allowed:
            setattr(org, k, v)
    await db.commit()
    await db.refresh(org)
    return OrganizationOut.model_validate(org)
