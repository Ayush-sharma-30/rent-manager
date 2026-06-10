from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, select

from rent_manager.db.models import Invoice, Payment, Tenant, Unit
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.payment import (
    InvoiceMatchSummary,
    MatchSuggestionIn,
    MatchSuggestionsOut,
    PaymentCreate,
    PaymentCreateOut,
    PaymentMatchIn,
    PaymentOut,
)
from rent_manager.services.payment_matcher import InvoiceCandidate, rank_candidates

router = APIRouter()


async def _open_invoices_for_org(db, org_id: UUID) -> list[Invoice]:
    stmt = select(Invoice).where(
        Invoice.organization_id == org_id,
        Invoice.status.in_(["pending", "partial", "overdue"]),
    )
    return list((await db.execute(stmt)).scalars().all())


async def _build_summaries(
    db, current_org_id: UUID, scored
) -> list[InvoiceMatchSummary]:
    invoice_ids = [s.candidate.invoice_id for s in scored]
    if not invoice_ids:
        return []
    rows = (
        await db.execute(
            select(Invoice, Tenant, Unit)
            .join(Tenant, Tenant.id == Invoice.tenant_id)
            .join(Unit, Unit.id == Invoice.unit_id)
            .where(Invoice.id.in_(invoice_ids), Invoice.organization_id == current_org_id)
        )
    ).all()
    by_id = {inv.id: (inv, tenant, unit) for inv, tenant, unit in rows}
    summaries: list[InvoiceMatchSummary] = []
    for s in scored:
        inv, tenant, unit = by_id[s.candidate.invoice_id]
        summaries.append(
            InvoiceMatchSummary(
                invoice_id=inv.id,
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                unit_identifier=unit.identifier,
                amount_due=inv.amount_due,
                due_date=inv.due_date,
                confidence=s.score,
            )
        )
    return summaries


@router.post("/match-suggestions", response_model=MatchSuggestionsOut)
async def match_suggestions(
    body: MatchSuggestionIn, current: CurrentUserDep, db: DbSession
) -> MatchSuggestionsOut:
    invoices = await _open_invoices_for_org(db, current.organization_id)
    candidates = [
        InvoiceCandidate(
            invoice_id=i.id,
            tenant_id=i.tenant_id,
            amount_due=i.amount_due,
            due_date=i.due_date,
        )
        for i in invoices
    ]
    scored = rank_candidates(candidates, body.amount, body.paid_on, body.tenant_id)
    return MatchSuggestionsOut(suggestions=await _build_summaries(db, current.organization_id, scored))


def _apply_payment_to_invoice(invoice: Invoice, amount: Decimal) -> None:
    invoice.amount_paid = invoice.amount_paid + amount
    if invoice.amount_paid >= invoice.amount_due:
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
    else:
        invoice.status = "partial"


def _allocate_fifo(invoices: list[Invoice], amount: Decimal) -> tuple[list[Invoice], Decimal]:
    """Apply ``amount`` to the given invoices oldest-first, capping each at its
    outstanding balance. Returns the invoices that were touched and any leftover
    (e.g. an overpayment with no remaining due). Invoices must be pre-sorted by
    due date ascending.
    """
    remaining = amount
    touched: list[Invoice] = []
    for inv in invoices:
        if remaining <= 0:
            break
        outstanding = inv.amount_due - inv.amount_paid
        if outstanding <= 0:
            continue
        applied = min(outstanding, remaining)
        _apply_payment_to_invoice(inv, applied)
        remaining -= applied
        touched.append(inv)
    return touched, remaining


@router.post("", response_model=PaymentCreateOut, status_code=status.HTTP_201_CREATED)
async def record_payment(
    body: PaymentCreate, current: CurrentUserDep, db: DbSession
) -> PaymentCreateOut:
    tenant = (
        await db.execute(
            select(Tenant).where(
                Tenant.id == body.tenant_id, Tenant.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    invoice: Invoice | None = None
    suggested: InvoiceMatchSummary | None = None
    confidence = Decimal("0")
    matched_auto = False

    if body.invoice_id is not None:
        invoice = (
            await db.execute(
                select(Invoice).where(
                    Invoice.id == body.invoice_id,
                    Invoice.organization_id == current.organization_id,
                    Invoice.tenant_id == body.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found or wrong tenant")
        _apply_payment_to_invoice(invoice, body.amount)
        confidence = Decimal("100")
        matched_auto = True
    else:
        # Manual entry: the owner chose this tenant, so apply the money to that
        # tenant's outstanding invoices oldest-first. This deterministically
        # reduces the tenant's due and keeps the dashboard metrics in sync,
        # rather than depending on a fuzzy match score.
        open_invoices = (
            await db.execute(
                select(Invoice)
                .where(
                    Invoice.organization_id == current.organization_id,
                    Invoice.tenant_id == body.tenant_id,
                    Invoice.status.in_(["pending", "partial", "overdue"]),
                )
                .order_by(Invoice.due_date.asc())
            )
        ).scalars().all()
        outstanding = sum(
            (inv.amount_due - inv.amount_paid for inv in open_invoices), Decimal("0")
        )
        if body.amount > outstanding:
            # Safety net — the client validates this first with a localized
            # message; this guards direct API use.
            raise HTTPException(
                status_code=422,
                detail=f"Amount exceeds the tenant's total due of ₹{outstanding}.",
            )
        touched, _leftover = _allocate_fifo(list(open_invoices), body.amount)
        if touched:
            invoice = touched[0]
            confidence = Decimal("100")
            matched_auto = True

    payment = Payment(
        organization_id=current.organization_id,
        invoice_id=invoice.id if invoice else None,
        tenant_id=body.tenant_id,
        amount=body.amount,
        paid_on=body.paid_on,
        method=body.method,
        reference=body.reference,
        screenshot_path=body.screenshot_path,
        notes=body.notes,
        match_confidence=confidence,
        matched_automatically=matched_auto,
        recorded_by_user_id=current.user_id,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return PaymentCreateOut(
        payment=PaymentOut.model_validate(payment), suggested_invoice_match=suggested
    )


@router.get("", response_model=list[PaymentOut])
async def list_payments(
    current: CurrentUserDep,
    db: DbSession,
    from_date: date | None = None,
    to_date: date | None = None,
    tenant_id: UUID | None = None,
) -> list[PaymentOut]:
    stmt = select(Payment).where(Payment.organization_id == current.organization_id)
    if from_date:
        stmt = stmt.where(Payment.paid_on >= from_date)
    if to_date:
        stmt = stmt.where(Payment.paid_on <= to_date)
    if tenant_id:
        stmt = stmt.where(Payment.tenant_id == tenant_id)
    stmt = stmt.order_by(Payment.paid_on.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [PaymentOut.model_validate(r) for r in rows]


@router.post("/{payment_id}/match", response_model=PaymentOut)
async def match_payment(
    payment_id: UUID, body: PaymentMatchIn, current: CurrentUserDep, db: DbSession
) -> PaymentOut:
    payment = (
        await db.execute(
            select(Payment).where(
                Payment.id == payment_id, Payment.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    invoice = (
        await db.execute(
            select(Invoice).where(
                Invoice.id == body.invoice_id,
                Invoice.organization_id == current.organization_id,
                Invoice.tenant_id == payment.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found or wrong tenant")

    if payment.invoice_id and payment.invoice_id != invoice.id:
        prev = (
            await db.execute(select(Invoice).where(Invoice.id == payment.invoice_id))
        ).scalar_one_or_none()
        if prev:
            prev.amount_paid = max(Decimal("0"), prev.amount_paid - payment.amount)
            prev.status = "pending" if prev.amount_paid == 0 else "partial"
            prev.paid_at = None

    payment.invoice_id = invoice.id
    _apply_payment_to_invoice(invoice, payment.amount)
    await db.commit()
    await db.refresh(payment)
    return PaymentOut.model_validate(payment)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(payment_id: UUID, current: CurrentUserDep, db: DbSession) -> None:
    payment = (
        await db.execute(
            select(Payment).where(
                Payment.id == payment_id, Payment.organization_id == current.organization_id
            )
        )
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.invoice_id:
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == payment.invoice_id))
        ).scalar_one_or_none()
        if invoice:
            invoice.amount_paid = max(Decimal("0"), invoice.amount_paid - payment.amount)
            if invoice.amount_paid == 0:
                invoice.status = "pending"
                invoice.paid_at = None
            elif invoice.amount_paid < invoice.amount_due:
                invoice.status = "partial"
                invoice.paid_at = None
    await db.delete(payment)
    await db.commit()
