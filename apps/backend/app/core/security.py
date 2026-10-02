"""Access tokens (JWT, short-lived), refresh tokens and OTP codes (random, stored as HMAC only)."""

import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt

from ..config import settings
from .timeutil import utcnow

OTP_LENGTH = 6
OTP_TTL = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_AFTER = timedelta(seconds=60)
# SMS pumping (bots triggering sends to premium numbers) is the main cost risk of OTP login.
OTP_MAX_SENDS_PER_HOUR = 5

_ALGO = "HS256"


def _hmac(purpose: str, value: str) -> str:
    return hmac.new(settings.secret_key.encode(), f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def new_otp() -> str:
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def hash_otp(phone: str, code: str) -> str:
    # Bound to the number, so a stored hash cannot be replayed for another phone.
    return _hmac(f"otp:{phone}", code)


def otp_matches(phone: str, code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(phone, code), stored_hash)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return _hmac("refresh", token)


def create_access_token(user_id: str, cooperative_id: str, role: str) -> tuple[str, int]:
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    now = utcnow()
    claims = {"sub": user_id, "coop": cooperative_id, "role": role, "typ": "access", "iat": now, "exp": now + ttl}
    return jwt.encode(claims, settings.secret_key, algorithm=_ALGO), int(ttl.total_seconds())


def decode_access_token(token: str) -> dict:
    claims = jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
    if claims.get("typ") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return claims


def sign_webhook(body: bytes, secret: str | None = None) -> str:
    return hmac.new((secret or settings.payment_webhook_secret).encode(), body, hashlib.sha256).hexdigest()


def webhook_signature_valid(body: bytes, signature: str | None) -> bool:
    return bool(signature) and hmac.compare_digest(sign_webhook(body), signature)
