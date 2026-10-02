"""Prefixed, time-sortable identifiers: `prod_01k6f3…`. Readable in logs, safe to expose."""

import secrets
import time

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"  # Crockford base32, lower case


def _b32(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(out))


def new_id(prefix: str) -> str:
    millis = int(time.time() * 1000)
    return f"{prefix}_{_b32(millis, 10)}{_b32(secrets.randbits(80), 16)}"


def new_token(nbytes: int = 16) -> str:
    return secrets.token_urlsafe(nbytes)
