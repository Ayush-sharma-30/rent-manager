from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from rent_manager.db.base import Base, TimestampMixin


class Property(Base, TimestampMixin):
    __tablename__ = "properties"
    __table_args__ = (Index("ix_properties_org_archived", "organization_id", "archived_at"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), default="apartment_building", nullable=False)
    address_line: Mapped[str | None] = mapped_column(String(300), nullable=True)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="Bengaluru", nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
