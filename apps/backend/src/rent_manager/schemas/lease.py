from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from rent_manager.schemas.common import ORMModel


class LeaseCreate(BaseModel):
    unit_id: UUID
    tenant_id: UUID
    start_date: date
    end_date: date
    monthly_rent: Decimal
    security_deposit: Decimal = Decimal("0")
    billing_day: int = Field(default=1, ge=1, le=28)
    notes: str | None = None


class LeaseRenewIn(BaseModel):
    new_end_date: date
    new_monthly_rent: Decimal


class LeaseEndIn(BaseModel):
    ended_on: date
    reason: str | None = None


class LeaseOut(ORMModel):
    id: UUID
    organization_id: UUID
    unit_id: UUID
    tenant_id: UUID
    start_date: date
    end_date: date
    monthly_rent: Decimal
    security_deposit: Decimal
    billing_day: int
    status: str
    renewal_status: str
    notes: str | None
