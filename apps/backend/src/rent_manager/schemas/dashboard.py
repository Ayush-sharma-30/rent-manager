from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class NeedsAttentionItem(BaseModel):
    tenant_id: UUID
    tenant_name: str
    unit_identifier: str
    amount_due: Decimal
    due_date: date
    days_overdue: int


class RecentlyPaidItem(BaseModel):
    payment_id: UUID
    tenant_id: UUID
    tenant_name: str
    amount: Decimal
    paid_on: date


class DashboardSummary(BaseModel):
    month: str
    collected: Decimal
    target: Decimal
    paid_count: int
    pending_count: int
    overdue_count: int
    needs_attention: list[NeedsAttentionItem]
    recently_paid: list[RecentlyPaidItem]


class LeaseExpiringItem(BaseModel):
    lease_id: UUID
    tenant_id: UUID
    tenant_name: str
    unit_identifier: str
    end_date: date
    days_until_expiry: int


class LeasesExpiringOut(BaseModel):
    leases: list[LeaseExpiringItem]
