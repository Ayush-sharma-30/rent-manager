from datetime import date
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select

from rent_manager.db.models import Payment, Tenant
from rent_manager.deps import CurrentUserDep, DbSession

router = APIRouter()


@router.get("/payments-excel")
async def payments_excel(
    current: CurrentUserDep,
    db: DbSession,
    from_date: date,
    to_date: date,
    property_id: UUID | None = None,
) -> StreamingResponse:
    stmt = (
        select(Payment, Tenant)
        .join(Tenant, Tenant.id == Payment.tenant_id)
        .where(
            Payment.organization_id == current.organization_id,
            Payment.paid_on >= from_date,
            Payment.paid_on <= to_date,
        )
        .order_by(Payment.paid_on.asc())
    )
    rows = (await db.execute(stmt)).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Payments"
    headers = [
        "Paid on",
        "Tenant name",
        "Tenant phone",
        "Amount (INR)",
        "Method",
        "Reference",
        "Invoice ID",
        "Notes",
    ]
    ws.append(headers)
    for payment, tenant in rows:
        ws.append(
            [
                payment.paid_on.isoformat(),
                tenant.name,
                tenant.phone_e164,
                float(payment.amount),
                payment.method,
                payment.reference or "",
                str(payment.invoice_id) if payment.invoice_id else "",
                payment.notes or "",
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"payments_{from_date.isoformat()}_{to_date.isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
