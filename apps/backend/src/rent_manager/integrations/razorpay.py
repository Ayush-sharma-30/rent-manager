import logging
from uuid import uuid4

from rent_manager.config import settings

logger = logging.getLogger(__name__)

PLANS = [
    {"name": "starter", "price_inr": 500, "razorpay_plan_id": "plan_dev_starter"},
    {"name": "growth", "price_inr": 999, "razorpay_plan_id": "plan_dev_growth"},
    {"name": "scale", "price_inr": 1499, "razorpay_plan_id": "plan_dev_scale"},
]


def create_subscription(*, plan_name: str, customer_phone: str) -> dict:
    plan = next((p for p in PLANS if p["name"] == plan_name), None)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_name}")
    if not settings.RAZORPAY_ENABLED:
        sub_id = f"sub_dev_{uuid4().hex[:12]}"
        logger.info(
            "[stub-razorpay] create_subscription plan=%s phone=%s -> %s",
            plan_name,
            customer_phone,
            sub_id,
        )
        return {
            "razorpay_subscription_id": sub_id,
            "razorpay_plan_id": plan["razorpay_plan_id"],
            "short_url": f"https://example.com/pay/{sub_id}",
            "plan": plan,
        }
    raise NotImplementedError("Razorpay live mode not wired in V1 starter")
