from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from rent_manager.schemas.common import ORMModel


class InvoiceOut(ORMModel):
    id: UUID
    organization_id: UUID
    lease_id: UUID
    tenant_id: UUID
    unit_id: UUID
    billing_month: date
    due_date: date
    amount_due: Decimal
    amount_paid: Decimal
    status: str
    paid_at: datetime | None
    last_reminder_day: int
    created_at: datetime
