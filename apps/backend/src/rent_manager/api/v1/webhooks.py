import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from rent_manager.config import settings
from rent_manager.db.models import WebhookInbox
from rent_manager.deps import DbSession
from rent_manager.workers.tasks.webhooks import process_razorpay_webhook, process_whatsapp_webhook

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/whatsapp")
async def verify_whatsapp(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> Any:
    if hub_mode == "subscribe" and hub_verify_token == settings.OTP_FIXED:
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="invalid verify token")


@router.post("/whatsapp")
async def receive_whatsapp(request: Request, db: DbSession) -> dict:
    payload = await request.json()
    event_id = None
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        statuses = change.get("statuses") or []
        messages = change.get("messages") or []
        event_id = (statuses[0].get("id") if statuses else None) or (
            messages[0].get("id") if messages else None
        )
    except (KeyError, IndexError, TypeError):
        event_id = None
    if not event_id:
        logger.warning("whatsapp webhook with no event id: %s", payload)
        return {"ok": True}

    stmt = (
        insert(WebhookInbox)
        .values(provider="whatsapp", external_event_id=event_id, payload=payload)
        .on_conflict_do_nothing(constraint="uq_webhook_provider_event")
        .returning(WebhookInbox.id)
    )
    inserted = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    if inserted is not None:
        process_whatsapp_webhook.delay(str(inserted))
    return {"ok": True}


@router.post("/razorpay")
async def receive_razorpay(request: Request, db: DbSession) -> dict:
    payload = await request.json()
    event_id = payload.get("id") or payload.get("event") or ""
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event id")
    stmt = (
        insert(WebhookInbox)
        .values(provider="razorpay", external_event_id=event_id, payload=payload)
        .on_conflict_do_nothing(constraint="uq_webhook_provider_event")
        .returning(WebhookInbox.id)
    )
    inserted = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    if inserted is not None:
        process_razorpay_webhook.delay(str(inserted))
    return {"ok": True}
