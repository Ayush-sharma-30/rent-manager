from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID


@dataclass(frozen=True)
class InvoiceCandidate:
    invoice_id: UUID
    tenant_id: UUID
    amount_due: Decimal
    due_date: date


@dataclass(frozen=True)
class Scored:
    candidate: InvoiceCandidate
    score: Decimal


def score_invoice(
    candidate: InvoiceCandidate,
    payment_amount: Decimal,
    payment_paid_on: date,
    payment_tenant_id: UUID | None,
) -> Decimal:
    """Score per §10.3 of the spec."""
    score = Decimal("0")

    delta = abs(candidate.amount_due - payment_amount)
    if delta < 1:
        score += 60
    elif delta <= 100:
        score += 40
    elif delta <= 1000:
        score += 20

    days_diff = abs((candidate.due_date - payment_paid_on).days)
    if days_diff <= 2:
        score += 25
    elif days_diff <= 7:
        score += 15
    elif days_diff <= 14:
        score += 5

    if payment_tenant_id is not None and candidate.tenant_id == payment_tenant_id:
        score += 15

    return score


def rank_candidates(
    candidates: Iterable[InvoiceCandidate],
    payment_amount: Decimal,
    payment_paid_on: date,
    payment_tenant_id: UUID | None,
    *,
    min_score: Decimal = Decimal("30"),
    top_n: int = 3,
) -> list[Scored]:
    scored = [
        Scored(candidate=c, score=score_invoice(c, payment_amount, payment_paid_on, payment_tenant_id))
        for c in candidates
    ]
    filtered = [s for s in scored if s.score >= min_score]
    filtered.sort(key=lambda s: s.score, reverse=True)
    return filtered[:top_n]
