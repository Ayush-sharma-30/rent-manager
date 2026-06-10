import logging
from typing import Any
from uuid import uuid4

from rent_manager.config import settings

logger = logging.getLogger(__name__)


SUBJECTS: dict[str, dict[str, str]] = {
    "reminder_day_3": {
        "en": "Rent reminder — {month}",
        "hi": "किराया स्मरण — {month}",
        "kn": "ಬಾಡಿಗೆ ಜ್ಞಾಪನೆ — {month}",
    },
    "reminder_day_5": {"en": "Overdue: Rent for {month}"},
    "reminder_day_7": {"en": "Final reminder: Rent for {month}"},
    "reminder_manual": {
        "en": "Rent reminder — {month}",
        "hi": "किराया स्मरण — {month}",
        "kn": "ಬಾಡಿಗೆ ಜ್ಞಾಪನೆ — {month}",
    },
}


def send_email(
    *,
    to_email: str,
    subject_key: str,
    body_text: str,
    language: str = "en",
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    variables = variables or {}
    subject = (
        SUBJECTS.get(subject_key, {}).get(language)
        or SUBJECTS.get(subject_key, {}).get("en")
        or subject_key
    ).format(**variables)
    if not settings.SES_ENABLED:
        external_id = f"dev_email_{uuid4().hex[:12]}"
        logger.info(
            "[stub-email] from=%s to=%s subject=%r body=%r external_id=%s",
            settings.SES_FROM_EMAIL,
            to_email,
            subject,
            body_text,
            external_id,
        )
        return {"external_id": external_id, "status": "sent"}

    # Real SES path would go here (boto3.client('ses').send_email(...))
    raise NotImplementedError("SES sending not wired in V1 starter; set SES_ENABLED=false")
