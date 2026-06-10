from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from rent_manager.schemas.common import ORMModel


class UnitCreate(BaseModel):
    type: str = "flat"
    identifier: str
    default_rent: Decimal = Field(default=Decimal("0"))
    notes: str | None = None


class UnitBulkCreate(BaseModel):
    units: list[UnitCreate] = Field(..., max_length=50)


class UnitUpdate(BaseModel):
    type: str | None = None
    identifier: str | None = None
    default_rent: Decimal | None = None
    notes: str | None = None


class UnitOut(ORMModel):
    id: UUID
    organization_id: UUID
    property_id: UUID
    type: str
    identifier: str
    default_rent: Decimal
    notes: str | None
    archived_at: datetime | None
    created_at: datetime


class BulkCreateResult(BaseModel):
    created_count: int
    units: list[UnitOut]
