"""Outgoing SMS. The console provider stores messages in `notifications` and logs them; a real gateway
(Orange SMS API, an aggregator…) plugs in behind `send_sms` without touching callers."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Notification

log = logging.getLogger("agritech.sms")


async def send_sms(db: AsyncSession, phone: str, body: str, *, kind: str, cooperative_id: str | None = None) -> None:
    if settings.sms_provider != "console":
        raise NotImplementedError(f"SMS provider {settings.sms_provider!r} is not wired yet")
    db.add(Notification(phone=phone, body=body, kind=kind, cooperative_id=cooperative_id, provider="console"))
    log.info("SMS to %s [%s]: %s", phone, kind, body)


def fcfa(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " FCFA"
