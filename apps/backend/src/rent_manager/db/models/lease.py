from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from rent_manager.db.base import Base, TimestampMixin


class Lease(Base, TimestampMixin):
    __tablename__ = "leases"
    __table_args__ = (
        Index(
            "uq_leases_unit_active",
            "unit_id",
            unique=True,
            postgresql_where="status = 'active'",
        ),
        Index("ix_leases_org_status", "organization_id", "status"),
        Index("ix_leases_end_status", "end_date", "status"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    unit_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    security_deposit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    billing_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    renewal_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
