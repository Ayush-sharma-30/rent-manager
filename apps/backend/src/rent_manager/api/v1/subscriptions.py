from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from rent_manager.db.models import Organization, Subscription, User
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.integrations.razorpay import PLANS, create_subscription

router = APIRouter()


class PlanOut(BaseModel):
    name: str
    price_inr: int
    razorpay_plan_id: str


class CheckoutIn(BaseModel):
    plan_name: str


class CheckoutOut(BaseModel):
    razorpay_subscription_id: str
    short_url: str


class SubscriptionOut(BaseModel):
    plan_name: str
    status: str
    monthly_price_inr: Decimal
    razorpay_subscription_id: str | None
    current_period_end: datetime | None


@router.get("/plans", response_model=list[PlanOut])
async def list_plans() -> list[PlanOut]:
    return [PlanOut(**p) for p in PLANS]


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    body: CheckoutIn, current: CurrentUserDep, db: DbSession
) -> CheckoutOut:
    user = (await db.execute(select(User).where(User.id == current.user_id))).scalar_one()
    try:
        result = create_subscription(plan_name=body.plan_name, customer_phone=user.phone_e164)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    plan = result["plan"]
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == current.organization_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        sub = Subscription(
            organization_id=current.organization_id,
            razorpay_subscription_id=result["razorpay_subscription_id"],
            razorpay_plan_id=result["razorpay_plan_id"],
            plan_name=plan["name"],
            monthly_price_inr=Decimal(plan["price_inr"]),
            status="created",
        )
        db.add(sub)
    else:
        sub.razorpay_subscription_id = result["razorpay_subscription_id"]
        sub.razorpay_plan_id = result["razorpay_plan_id"]
        sub.plan_name = plan["name"]
        sub.monthly_price_inr = Decimal(plan["price_inr"])
        sub.status = "created"
    await db.commit()
    return CheckoutOut(
        razorpay_subscription_id=result["razorpay_subscription_id"],
        short_url=result["short_url"],
    )


@router.get("/current", response_model=SubscriptionOut | None)
async def current_subscription(current: CurrentUserDep, db: DbSession) -> SubscriptionOut | None:
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == current.organization_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        return None
    return SubscriptionOut(
        plan_name=sub.plan_name,
        status=sub.status,
        monthly_price_inr=sub.monthly_price_inr,
        razorpay_subscription_id=sub.razorpay_subscription_id,
        current_period_end=sub.current_period_end,
    )


@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(current: CurrentUserDep, db: DbSession) -> SubscriptionOut:
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == current.organization_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription to cancel")
    sub.status = "cancelled"
    sub.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    return SubscriptionOut(
        plan_name=sub.plan_name,
        status=sub.status,
        monthly_price_inr=sub.monthly_price_inr,
        razorpay_subscription_id=sub.razorpay_subscription_id,
        current_period_end=sub.current_period_end,
    )
