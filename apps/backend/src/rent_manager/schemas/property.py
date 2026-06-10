from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from rent_manager.schemas.common import ORMModel


class PropertyCreate(BaseModel):
    name: str
    type: str = "apartment_building"
    address_line: str | None = None
    area: str | None = None
    city: str = "Bengaluru"
    pincode: str | None = None


class PropertyUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    address_line: str | None = None
    area: str | None = None
    city: str | None = None
    pincode: str | None = None


class PropertyOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    type: str
    address_line: str | None
    area: str | None
    city: str
    pincode: str | None
    archived_at: datetime | None
    created_at: datetime
