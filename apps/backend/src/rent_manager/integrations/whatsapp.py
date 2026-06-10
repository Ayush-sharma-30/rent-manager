import logging
from typing import Any
from uuid import uuid4

import httpx

from rent_manager.config import settings

logger = logging.getLogger(__name__)


GRAPH_BASE = "https://graph.facebook.com/v20.0"

TEMPLATES: dict[str, dict[str, str]] = {
    "reminder_day_3": {
        "en": "Hi {name}, this is a reminder that your rent of ₹{amount} for {month} is pending. Please pay at your earliest.",
        "hi": "नमस्ते {name}, आपका {month} का किराया ₹{amount} अभी तक जमा नहीं हुआ है। कृपया जल्द से जल्द भुगतान करें।",
        "kn": "ನಮಸ್ಕಾರ {name}, ನಿಮ್ಮ {month} ತಿಂಗಳ ಬಾಡಿಗೆ ₹{amount} ಬಾಕಿ ಇದೆ. ದಯವಿಟ್ಟು ಶೀಘ್ರವಾಗಿ ಪಾವತಿಸಿ.",
    },
    "reminder_day_5": {
        "en": "Reminder: Your rent of ₹{amount} for {month} is overdue by 5 days.",
        "hi": "स्मरण: {month} का किराया ₹{amount} 5 दिन से लंबित है।",
        "kn": "ಜ್ಞಾಪನೆ: {month} ತಿಂಗಳ ಬಾಡಿಗೆ ₹{amount} 5 ದಿನಗಳಿಂದ ಬಾಕಿ ಇದೆ.",
    },
    "reminder_day_7": {
        "en": "Final reminder: Please pay ₹{amount} rent for {month}. Owner will be notified.",
        "hi": "अंतिम स्मरण: कृपया {month} का ₹{amount} किराया जमा करें।",
        "kn": "ಕೊನೆಯ ಜ್ಞಾಪನೆ: ದಯವಿಟ್ಟು {month} ತಿಂಗಳ ₹{amount} ಬಾಡಿಗೆ ಪಾವತಿಸಿ.",
    },
    "reminder_manual": {
        "en": "Hi {name}, a quick reminder that your rent of ₹{amount} for {month} is pending. Please pay at your earliest. Thank you.",
        "hi": "नमस्ते {name}, एक छोटा सा स्मरण — आपका {month} का किराया ₹{amount} अभी तक जमा नहीं हुआ है। कृपया जल्द से जल्द भुगतान करें। धन्यवाद।",
        "kn": "ನಮಸ್ಕಾರ {name}, ಒಂದು ಸಣ್ಣ ಜ್ಞಾಪನೆ — ನಿಮ್ಮ {month} ತಿಂಗಳ ಬಾಡಿಗೆ ₹{amount} ಬಾಕಿ ಇದೆ. ದಯವಿಟ್ಟು ಶೀಘ್ರವಾಗಿ ಪಾವತಿಸಿ. ಧನ್ಯವಾದಗಳು.",
    },
    "owner_weekly_summary": {
        "en": "Weekly summary: Collected ₹{collected}, Pending ₹{pending}, Overdue ₹{overdue}. {expiring_count} leases expire in next 45 days.",
        "hi": "साप्ताहिक सारांश: एकत्रित ₹{collected}, लंबित ₹{pending}, अतिदेय ₹{overdue}। अगले 45 दिनों में {expiring_count} लीज समाप्त।",
        "kn": "ವಾರದ ಸಾರಾಂಶ: ಸಂಗ್ರಹಿಸಿದ ₹{collected}, ಬಾಕಿ ₹{pending}, ತಡವಾದ ₹{overdue}.",
    },
    "owner_lease_expiring": {
        "en": "Lease for tenant {tenant} in unit {unit} expires on {end_date}.",
        "hi": "{unit} के किरायेदार {tenant} का लीज {end_date} को समाप्त हो रहा है।",
        "kn": "{unit} ನ ಬಾಡಿಗೆದಾರ {tenant} ರ ಬಾಡಿಗೆ ಒಪ್ಪಂದ {end_date} ರಂದು ಮುಗಿಯುತ್ತದೆ.",
    },
    "tenant_payment_confirmed": {
        "en": "Hi {name}, we have received your payment of ₹{amount} for {month}. Thank you.",
        "hi": "नमस्ते {name}, हमें {month} के लिए आपका ₹{amount} का भुगतान प्राप्त हुआ है।",
        "kn": "ನಮಸ್ಕಾರ {name}, {month} ಗಾಗಿ ₹{amount} ಪಾವತಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ.",
    },
}


def render(template_key: str, language: str, variables: dict[str, Any]) -> str:
    bank = TEMPLATES.get(template_key, {})
    body = bank.get(language) or bank.get("en") or template_key
    try:
        return body.format(**variables)
    except KeyError as exc:
        logger.warning("template %s missing var %s", template_key, exc)
        return body


def send_whatsapp_message(
    *,
    to_phone_e164: str,
    template_key: str,
    language: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    """Send a WhatsApp message.

    In dev/local (WHATSAPP_ENABLED=false) returns a fake external_id and logs the body.
    """
    body = render(template_key, language, variables)
    if not settings.WHATSAPP_ENABLED:
        external_id = f"dev_wa_{uuid4().hex[:12]}"
        logger.info(
            "[stub-whatsapp] to=%s template=%s lang=%s body=%r external_id=%s",
            to_phone_e164,
            template_key,
            language,
            body,
            external_id,
        )
        return {"external_id": external_id, "status": "sent", "body": body}

    url = f"{GRAPH_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone_e164.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    external_id = (data.get("messages") or [{}])[0].get("id", f"wa_{uuid4().hex[:8]}")
    return {"external_id": external_id, "status": "sent", "body": body}
