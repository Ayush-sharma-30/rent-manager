from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from rent_manager.schemas.common import ORMModel


class OtpSendIn(BaseModel):
    phone_e164: str = Field(..., examples=["+919876543210", "9876543210"])


class OtpSendOut(BaseModel):
    request_id: str
    dev_otp_hint: str | None = None


class OtpVerifyIn(BaseModel):
    phone_e164: str
    otp: str = Field(..., min_length=4, max_length=8)
    request_id: str
    name: str | None = None
    organization_name: str | None = None
    default_language: str = "en"


class UserOut(ORMModel):
    id: UUID
    organization_id: UUID
    role: str
    name: str
    phone_e164: str
    email: str | None
    language: str
    last_seen_at: datetime | None


class OrganizationOut(ORMModel):
    id: UUID
    name: str
    phone_e164: str
    email: str | None
    default_language: str
    tier: str


class OtpVerifyOut(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut
    organization: OrganizationOut


class RefreshIn(BaseModel):
    refresh_token: str


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str


class MeOut(BaseModel):
    user: UserOut
    organization: OrganizationOut


class UpdateMeIn(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    language: str | None = None
    push_token: str | None = None
