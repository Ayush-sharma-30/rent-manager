import re


_DIGITS = re.compile(r"\D+")


def normalize_indian_phone(raw: str) -> str:
    if not raw:
        raise ValueError("phone is required")
    digits = _DIGITS.sub("", raw)
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return f"+{digits}"
    raise ValueError(f"Cannot normalize phone: {raw!r}")
