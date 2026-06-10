import logging
from datetime import datetime, timezone

from sqlalchemy import select

from rent_manager.db.models import WebhookInbox
from rent_manager.db.session import SyncSessionLocal
from rent_manager.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="rent_manager.workers.tasks.webhooks.process_whatsapp_webhook")
def process_whatsapp_webhook(inbox_id: str) -> dict:
    with SyncSessionLocal() as db:
        row = db.execute(select(WebhookInbox).where(WebhookInbox.id == inbox_id)).scalar_one_or_none()
        if row is None or row.processed_at is not None:
            return {"skipped": True}
        # Real impl: update NotificationLog status to delivered/read/failed based on row.payload
        logger.info("processing WhatsApp webhook %s", row.external_event_id)
        row.processed_at = datetime.now(timezone.utc)
        db.commit()
    return {"processed": True}


@celery_app.task(name="rent_manager.workers.tasks.webhooks.process_razorpay_webhook")
def process_razorpay_webhook(inbox_id: str) -> dict:
    with SyncSessionLocal() as db:
        row = db.execute(select(WebhookInbox).where(WebhookInbox.id == inbox_id)).scalar_one_or_none()
        if row is None or row.processed_at is not None:
            return {"skipped": True}
        logger.info("processing Razorpay webhook %s", row.external_event_id)
        # Real impl: update Subscription state from row.payload
        row.processed_at = datetime.now(timezone.utc)
        db.commit()
    return {"processed": True}
