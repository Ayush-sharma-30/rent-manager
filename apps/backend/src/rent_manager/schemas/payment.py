from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from rent_manager.schemas.common import ORMModel


class PaymentCreate(BaseModel):
    tenant_id: UUID
    amount: Decimal
    paid_on: date
    method: str = "upi"
    reference: str | None = None
    screenshot_path: str | None = None
    invoice_id: UUID | None = None
    notes: str | None = None


class PaymentOut(ORMModel):
    id: UUID
    organization_id: UUID
    invoice_id: UUID | None
    tenant_id: UUID
    amount: Decimal
    paid_on: date
    method: str
    reference: str | None
    screenshot_path: str | None
    notes: str | None
    match_confidence: Decimal
    matched_automatically: bool
    recorded_by_user_id: UUID
    created_at: datetime


class MatchSuggestionIn(BaseModel):
    amount: Decimal
    paid_on: date
    tenant_id: UUID | None = None
    screenshot_path: str | None = None


class InvoiceMatchSummary(BaseModel):
    invoice_id: UUID
    tenant_id: UUID
    tenant_name: str
    unit_identifier: str
    amount_due: Decimal
    due_date: date
    confidence: Decimal


class MatchSuggestionsOut(BaseModel):
    suggestions: list[InvoiceMatchSummary]


class PaymentCreateOut(BaseModel):
    payment: PaymentOut
    suggested_invoice_match: InvoiceMatchSummary | None = None


class PaymentMatchIn(BaseModel):
    invoice_id: UUID
