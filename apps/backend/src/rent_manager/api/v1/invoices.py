from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from rent_manager.db.models import Invoice
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.invoice import InvoiceOut

router = APIRouter()


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    current: CurrentUserDep,
    db: DbSession,
    status: str | None = None,
    month: str | None = None,
    tenant_id: UUID | None = None,
) -> list[InvoiceOut]:
    stmt = select(Invoice).where(Invoice.organization_id == current.organization_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if tenant_id is not None:
        stmt = stmt.where(Invoice.tenant_id == tenant_id)
    if month:
        try:
            month_date = date.fromisoformat(month + "-01")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="month must be YYYY-MM") from exc
        stmt = stmt.where(Invoice.billing_month == month_date)
    stmt = stmt.order_by(Invoice.due_date.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [InvoiceOut.model_validate(r) for r in rows]


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: UUID, current: CurrentUserDep, db: DbSession) -> InvoiceOut:
    inv = (
        await db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.organization_id == current.organization_id,
            )
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceOut.model_validate(inv)
