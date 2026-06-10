from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from rent_manager.schemas.common import ORMModel


class TenantCreate(BaseModel):
    name: str
    phone_e164: str
    email: str | None = None
    language: str = "hi"
    whatsapp_opt_in: bool = True
    email_opt_in: bool = True
    notes: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    phone_e164: str | None = None
    email: str | None = None
    language: str | None = None
    whatsapp_opt_in: bool | None = None
    email_opt_in: bool | None = None
    notes: str | None = None


class TenantOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    phone_e164: str
    email: str | None
    language: str
    whatsapp_opt_in: bool
    email_opt_in: bool
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
