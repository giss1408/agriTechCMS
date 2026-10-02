"""Phone numbers are the login identity. Ivorian numbers have 10 digits since 2021 (+225 07 12 34 56 78)."""

import re

from .errors import ApiError

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    elif digits.startswith("225") and len(digits) == 13:
        digits = "+" + digits
    elif not digits.startswith("+") and len(digits) == 10:
        digits = "+225" + digits
    if not _E164.match(digits) or (digits.startswith("+225") and len(digits) != 14):
        raise ApiError(400, "invalid_phone", f"Numéro de téléphone invalide : {raw!r}")
    return digits


def mask_phone(phone: str) -> str:
    return phone[:-6] + "••••" + phone[-2:] if len(phone) > 8 else "••••"
