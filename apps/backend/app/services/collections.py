"""The core rule set. Both `POST /collections` and `POST /sync/push` go through `ingest`."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError, not_found
from ..core.ids import new_id
from ..core.timeutil import ensure_utc, utcnow
from ..models import Collection, Cooperative, Producer, User
from ..schemas import CollectionIn, CollectionOut
from . import audit
from .pricing import amount_for, price_on

# Below this drift we trust the phone clock (network time on Android is usually within seconds).
CLOCK_TOLERANCE = timedelta(minutes=2)
EDITABLE = {"pending_validation"}


def to_out(c: Collection) -> CollectionOut:
    out = CollectionOut.model_validate(c)
    out.producer_name = c.producer.full_name
    out.producer_code = c.producer.code
    out.collector_name = c.collector.name
    return out


def corrected_time(device_at: datetime, clock_offset: timedelta) -> datetime:
    """`clock_offset` = server_now - device_now, measured when the batch arrives."""
    device_at = ensure_utc(device_at)
    fixed = device_at + clock_offset if abs(clock_offset) > CLOCK_TOLERANCE else device_at
    return min(fixed, utcnow())  # a delivery cannot be in the future


async def find_by_client_uuid(db: AsyncSession, cooperative_id: str, client_uuid: str) -> Collection | None:
    stmt = select(Collection).where(Collection.cooperative_id == cooperative_id, Collection.client_uuid == client_uuid)
    return (await db.execute(stmt)).scalar_one_or_none()


async def ingest(
    db: AsyncSession,
    user: User,
    data: CollectionIn,
    *,
    source: str,
    device_id: str | None = None,
    clock_offset: timedelta = timedelta(0),
) -> tuple[Collection, bool]:
    """Create a collection, or return the existing one if this `client_uuid` was already received.

    Returns (collection, created). Raises ApiError on business rule violations.
    """
    coop: Cooperative = user.cooperative
    existing = await find_by_client_uuid(db, coop.id, data.client_uuid)
    if existing:
        return existing, False

    producer = await db.get(Producer, data.producer_id)
    if not producer or producer.cooperative_id != coop.id:
        raise ApiError(422, "unknown_producer", "Producteur inconnu dans cette coopérative")
    if producer.status != "active":
        raise ApiError(422, "inactive_producer", f"{producer.full_name} est désactivé")
    if data.weight_kg > coop.max_weight_kg:
        raise ApiError(
            422, "weight_above_max", f"Poids {data.weight_kg} kg supérieur au maximum autorisé ({coop.max_weight_kg} kg)"
        )
    if data.moisture_percent is not None and data.moisture_percent > coop.max_moisture_percent:
        raise ApiError(
            422,
            "moisture_above_threshold",
            f"Humidité {data.moisture_percent} % au-dessus du seuil ({coop.max_moisture_percent} %) : lot à re-sécher",
        )

    collected_at = corrected_time(data.collected_at, clock_offset)
    price = await price_on(db, coop.id, data.product, data.quality, collected_at.date())

    collection = Collection(
        cooperative_id=coop.id,
        client_uuid=data.client_uuid,
        producer_id=producer.id,
        collector_id=user.id,
        product=data.product,
        quality=data.quality,
        weight_kg=data.weight_kg,
        moisture_percent=data.moisture_percent,
        unit_price=price.price_per_kg,
        amount=amount_for(data.weight_kg, price.price_per_kg),
        collected_at=collected_at,
        collected_at_device=ensure_utc(data.collected_at),
        clock_offset_seconds=int(clock_offset.total_seconds()),
        gps_lat=data.gps.lat if data.gps else None,
        gps_lng=data.gps.lng if data.gps else None,
        notes=data.notes,
        photo_ids=data.photos,
        producer_signature=data.producer_signature,
        sync_source=source,
        device_id=device_id,
    )
    collection.reference = f"COL-{collected_at:%Y%m%d}-{new_id('x')[-6:].upper()}"
    db.add(collection)
    await db.flush()
    audit.record(
        db,
        cooperative_id=coop.id,
        actor_id=user.id,
        entity="collection",
        entity_id=collection.id,
        action="created",
        changes={"weight_kg": data.weight_kg, "quality": data.quality, "amount": collection.amount, "source": source},
    )
    await db.refresh(collection, ["producer", "collector"])
    return collection, True


async def get_for(db: AsyncSession, user: User, collection_id: str) -> Collection:
    c = await db.get(Collection, collection_id)
    if not c or c.cooperative_id != user.cooperative_id:
        raise not_found("Collecte")
    if user.role == "collector" and c.collector_id != user.id:
        raise not_found("Collecte")
    return c


async def admin_edit(db: AsyncSession, user: User, c: Collection, **changes) -> Collection:
    reason = changes.pop("reason")
    if c.status not in EDITABLE:
        raise ApiError(409, "not_editable", "Seule une collecte en attente de validation peut être modifiée")
    updates = {k: v for k, v in changes.items() if v is not None}
    if "weight_kg" in updates and updates["weight_kg"] > user.cooperative.max_weight_kg:
        raise ApiError(422, "weight_above_max", "Poids supérieur au maximum autorisé")
    if "quality" in updates or "weight_kg" in updates:
        quality = updates.get("quality", c.quality)
        price = await price_on(db, c.cooperative_id, c.product, quality, c.collected_at.date())
        updates["unit_price"] = price.price_per_kg
        updates["amount"] = amount_for(updates.get("weight_kg", c.weight_kg), price.price_per_kg)
    changed = audit.diff(c, updates)
    for k, v in updates.items():
        setattr(c, k, v)
    audit.record(
        db, cooperative_id=c.cooperative_id, actor_id=user.id, entity="collection", entity_id=c.id,
        action="edited", changes={**changed, "reason": reason},
    )
    return c


def validate(db: AsyncSession, user: User, c: Collection) -> None:
    if c.status == "validated":
        return
    if c.status != "pending_validation":
        raise ApiError(409, "invalid_transition", f"Impossible de valider une collecte « {c.status} »")
    c.status = "validated"
    c.validated_by = user.id
    c.validated_at = utcnow()
    audit.record(db, cooperative_id=c.cooperative_id, actor_id=user.id, entity="collection", entity_id=c.id, action="validated")


def reject(db: AsyncSession, user: User, c: Collection, reason: str) -> None:
    if c.status != "pending_validation":
        raise ApiError(409, "invalid_transition", f"Impossible de rejeter une collecte « {c.status} »")
    c.status = "rejected"
    c.rejection_reason = reason
    audit.record(
        db, cooperative_id=c.cooperative_id, actor_id=user.id, entity="collection", entity_id=c.id,
        action="rejected", changes={"reason": reason},
    )


def cancel(db: AsyncSession, user: User, c: Collection) -> None:
    if c.status == "paid" or c.payment_id or c.lot_id:
        raise ApiError(409, "invalid_transition", "Collecte déjà payée, en paiement ou dans un lot : annulation impossible")
    previous = c.status
    c.status = "cancelled"
    audit.record(
        db, cooperative_id=c.cooperative_id, actor_id=user.id, entity="collection", entity_id=c.id,
        action="cancelled", changes={"status": [previous, "cancelled"]},
    )
