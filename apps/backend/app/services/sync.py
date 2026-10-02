"""Offline-first sync. See docs/technical/05-synchronisation-offline.md for the protocol."""

from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.timeutil import campaign_of, ensure_utc, utcnow
from ..models import Collection, Producer, PurchasePrice, SyncDevice, User, Zone
from ..schemas import (
    PriceOut,
    SyncAccepted,
    SyncPullOut,
    SyncPushIn,
    SyncPushOut,
    SyncRejected,
    SyncSettings,
    ZoneOut,
)
from . import collections as collection_service
from .producers import producer_out

# A row committed just after we read the clock can carry an earlier updated_at. Handing back a cursor
# slightly in the past means the next pull re-sends a few rows; the app upserts, so that is harmless.
CURSOR_SAFETY = timedelta(seconds=30)
FIRST_PULL_HISTORY = timedelta(days=14)
PRICE_HISTORY = timedelta(days=60)


async def _device(db: AsyncSession, user: User, device_id: str) -> SyncDevice:
    device = await db.get(SyncDevice, device_id)
    if device and device.cooperative_id != user.cooperative_id:
        raise ApiError(409, "device_conflict", "Cet appareil est enregistré dans une autre coopérative")
    if not device:
        device = SyncDevice(id=device_id, cooperative_id=user.cooperative_id, user_id=user.id)
        db.add(device)
    device.user_id = user.id
    return device


async def push(db: AsyncSession, user: User, body: SyncPushIn) -> SyncPushOut:
    server_now = utcnow()
    offset = server_now - ensure_utc(body.device_time)
    accepted, rejected = [], []
    # Not atomic on purpose: one bad collection must not block the rest of a day's work.
    # `ingest` validates everything before writing, so a rejected item leaves nothing behind.
    for item in body.collections:
        try:
            c, created = await collection_service.ingest(
                db, user, item, source="offline_mobile", device_id=body.device_id, clock_offset=offset
            )
        except ApiError as exc:
            rejected.append(SyncRejected(client_uuid=item.client_uuid, code=exc.code, message=exc.message))
            continue
        accepted.append(
            SyncAccepted(
                client_uuid=c.client_uuid, id=c.id, reference=c.reference, amount=c.amount,
                unit_price=c.unit_price, status=c.status, duplicate=not created,
            )
        )
    device = await _device(db, user, body.device_id)
    device.last_push_at = server_now
    device.last_clock_offset_seconds = int(offset.total_seconds())
    device.app_version = body.app_version or device.app_version
    device.pending_on_device = max(0, body.pending_on_device - len(accepted))
    user.last_seen_at = server_now
    await db.commit()
    return SyncPushOut(
        accepted=accepted, rejected=rejected, clock_offset_seconds=int(offset.total_seconds()), server_time=server_now
    )


async def pull(db: AsyncSession, user: User, since: datetime | None, device_id: str | None) -> SyncPullOut:
    server_now = utcnow()
    coop = user.cooperative
    full = since is None
    since = ensure_utc(since) if since else None

    producer_stmt = select(Producer).where(Producer.cooperative_id == coop.id)
    if full:
        producer_stmt = producer_stmt.where(Producer.status == "active")
    else:
        # inactive producers are sent too, so the phone can hide them
        producer_stmt = producer_stmt.where(Producer.updated_at >= since)
    producers = (await db.execute(producer_stmt.order_by(Producer.code))).scalars().all()

    # Prices and zones are small: always sent in full, the phone replaces its copy.
    oldest_price_day: date = (server_now - PRICE_HISTORY).date()
    prices = (
        await db.execute(
            select(PurchasePrice).where(
                PurchasePrice.cooperative_id == coop.id,
                or_(PurchasePrice.effective_to.is_(None), PurchasePrice.effective_to >= oldest_price_day),
            )
        )
    ).scalars().all()
    zones = (await db.execute(select(Zone).where(Zone.cooperative_id == coop.id))).scalars().all()

    col_stmt = select(Collection).where(Collection.cooperative_id == coop.id, Collection.collector_id == user.id)
    col_stmt = col_stmt.where(
        Collection.collected_at >= server_now - FIRST_PULL_HISTORY if full else Collection.updated_at >= since
    )
    cols = (await db.execute(col_stmt.order_by(Collection.collected_at.desc()).limit(1000))).scalars().all()

    if device_id:
        device = await _device(db, user, device_id)
        device.last_pull_at = server_now
    user.last_seen_at = server_now
    await db.commit()

    return SyncPullOut(
        server_time=server_now,
        cursor=server_now - CURSOR_SAFETY,
        full=full,
        settings=SyncSettings(
            max_moisture_percent=coop.max_moisture_percent,
            max_weight_kg=coop.max_weight_kg,
            campaign=campaign_of(server_now.date(), coop.campaign_start_month),
            currency=coop.currency,
        ),
        producers=[producer_out(p) for p in producers],
        prices=[PriceOut.model_validate(p) for p in prices],
        zones=[ZoneOut.model_validate(z) for z in zones],
        collections=[collection_service.to_out(c) for c in cols],
    )
