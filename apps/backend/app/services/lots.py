"""Lots: collection -> lot -> buyer. Sealing a lot freezes its content and issues the public trace link."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core import geo
from ..core.errors import ApiError, not_found
from ..core.ids import new_token
from ..core.timeutil import utcnow
from ..models import Collection, Cooperative, Lot, Parcel, Producer, User
from ..schemas import LotOut
from . import audit


def to_out(lot: Lot) -> LotOut:
    out = LotOut.model_validate(lot)
    if lot.trace_token:
        out.trace_url = f"{settings.public_web_url}/trace/{lot.trace_token}"
    return out


async def get_for(db: AsyncSession, user: User, lot_id: str) -> Lot:
    lot = await db.get(Lot, lot_id)
    if not lot or lot.cooperative_id != user.cooperative_id:
        raise not_found("Lot")
    return lot


async def create(db: AsyncSession, user: User, product: str, quality: str | None, notes: str | None) -> Lot:
    coop: Cooperative = user.cooperative
    coop.lot_seq += 1
    lot = Lot(
        cooperative_id=coop.id,
        reference=f"LOT-{utcnow():%Y}-{coop.code}-{coop.lot_seq:04d}",
        product=product,
        quality=quality,
        notes=notes,
    )
    db.add(lot)
    await db.flush()
    audit.record(db, cooperative_id=coop.id, actor_id=user.id, entity="lot", entity_id=lot.id, action="created")
    return lot


async def _recount(db: AsyncSession, lot: Lot) -> None:
    rows = (await db.execute(select(Collection.weight_kg).where(Collection.lot_id == lot.id))).scalars().all()
    lot.total_weight_kg = sum(rows, Decimal("0"))
    lot.collections_count = len(rows)


async def add_collections(db: AsyncSession, user: User, lot: Lot, ids: list[str]) -> list[dict]:
    if lot.status != "open":
        raise ApiError(409, "lot_not_open", "Le lot est scellé : son contenu ne peut plus changer")
    stmt = select(Collection).where(Collection.cooperative_id == lot.cooperative_id, Collection.id.in_(ids))
    found = {c.id: c for c in (await db.execute(stmt)).scalars()}
    refused = []
    for cid in ids:
        c = found.get(cid)
        reason = None
        if not c:
            reason = "Collecte introuvable"
        elif c.status not in ("validated", "paid"):
            reason = "Seules les collectes validées entrent dans un lot"
        elif c.product != lot.product:
            reason = f"Produit {c.product} différent du lot ({lot.product})"
        elif lot.quality and c.quality != lot.quality:
            reason = f"Qualité {c.quality} différente du lot ({lot.quality})"
        elif c.lot_id and c.lot_id != lot.id:
            reason = "Déjà dans un autre lot"
        if reason:
            refused.append({"id": cid, "reason": reason})
        else:
            c.lot_id = lot.id
    await db.flush()
    await _recount(db, lot)
    return refused


async def remove_collection(db: AsyncSession, lot: Lot, collection_id: str) -> None:
    if lot.status != "open":
        raise ApiError(409, "lot_not_open", "Le lot est scellé : son contenu ne peut plus changer")
    c = await db.get(Collection, collection_id)
    if not c or c.lot_id != lot.id:
        raise not_found("Collecte du lot")
    c.lot_id = None
    await db.flush()
    await _recount(db, lot)


def seal(db: AsyncSession, user: User, lot: Lot, bags_count: int | None = None) -> None:
    if lot.status != "open":
        raise ApiError(409, "invalid_transition", "Lot déjà scellé")
    if lot.collections_count == 0:
        raise ApiError(422, "empty_lot", "Impossible de sceller un lot vide")
    lot.status = "sealed"
    lot.sealed_at = utcnow()
    lot.bags_count = bags_count or lot.bags_count
    lot.trace_token = new_token(12)
    audit.record(
        db, cooperative_id=lot.cooperative_id, actor_id=user.id, entity="lot", entity_id=lot.id, action="sealed",
        changes={"total_weight_kg": lot.total_weight_kg, "collections": lot.collections_count},
    )


def ship(db: AsyncSession, user: User, lot: Lot, buyer_name: str, destination: str | None, bags_count: int | None) -> None:
    if lot.status != "sealed":
        raise ApiError(409, "invalid_transition", "Seul un lot scellé peut être expédié")
    lot.status = "shipped"
    lot.shipped_at = utcnow()
    lot.buyer_name = buyer_name
    lot.destination = destination
    if bags_count:
        lot.bags_count = bags_count
    audit.record(
        db, cooperative_id=lot.cooperative_id, actor_id=user.id, entity="lot", entity_id=lot.id, action="shipped",
        changes={"buyer_name": buyer_name},
    )


async def traceability(db: AsyncSession, lot: Lot, *, public: bool) -> dict:
    """Producers and parcels behind a lot. `public=True` strips personal data (phone, ID number, full first name)."""
    collections = (
        (await db.execute(select(Collection).where(Collection.lot_id == lot.id).order_by(Collection.collected_at)))
        .scalars()
        .all()
    )
    coop = await db.get(Cooperative, lot.cooperative_id)
    by_producer: dict[str, dict] = {}
    for c in collections:
        entry = by_producer.setdefault(c.producer_id, {"weight_kg": Decimal("0"), "collections": 0})
        entry["weight_kg"] += c.weight_kg
        entry["collections"] += 1

    producers = (
        (await db.execute(select(Producer).where(Producer.id.in_(list(by_producer))))).scalars().all()
        if by_producer
        else []
    )
    parcels = (
        (
            await db.execute(
                select(Parcel).where(Parcel.producer_id.in_(list(by_producer)), Parcel.crop == lot.product)
            )
        )
        .scalars()
        .all()
        if by_producer
        else []
    )
    parcels_by_producer: dict[str, list[Parcel]] = {}
    for p in parcels:
        parcels_by_producer.setdefault(p.producer_id, []).append(p)

    producer_rows, features, ready_parcels = [], [], 0
    for prod in sorted(producers, key=lambda p: p.code):
        own = parcels_by_producer.get(prod.id, [])
        rows = []
        for parcel in own:
            area = float(parcel.measured_area_hectares or parcel.area_hectares or 0) or None
            issues = geo.eudr_issues(parcel.geometry, area, parcel.deforestation_status)
            ready_parcels += not issues
            rows.append({"id": parcel.id, "area_hectares": area, "geometry_type": (parcel.geometry or {}).get("type"),
                         "deforestation_status": parcel.deforestation_status, "eudr_issues": issues})
            if parcel.geometry:
                features.append({
                    "type": "Feature",
                    "geometry": parcel.geometry,
                    "properties": {"parcel_id": parcel.id, "producer_code": prod.code, "crop": parcel.crop,
                                   "area_ha": area, "eudr_ready": not issues},
                })
        name = f"{prod.last_name.upper()} {prod.first_name[:1]}." if public else prod.full_name
        producer_rows.append({
            "code": prod.code,
            "name": name,
            **({} if public else {"id": prod.id, "phone": prod.phone}),
            "weight_kg": by_producer[prod.id]["weight_kg"],
            "collections": by_producer[prod.id]["collections"],
            "parcels": rows,
            "eudr_ready": bool(rows) and all(not r["eudr_issues"] for r in rows),
        })

    total_parcels = len(parcels)
    return {
        "lot": to_out(lot).model_dump(mode="json"),
        "cooperative": {"name": coop.name, "region": coop.region, "code": coop.code},
        "summary": {
            "producers": len(producer_rows),
            "parcels": total_parcels,
            "parcels_eudr_ready": ready_parcels,
            "producers_without_parcel": sum(1 for r in producer_rows if not r["parcels"]),
            "eudr_ready": bool(producer_rows) and all(r["eudr_ready"] for r in producer_rows),
            "first_collection_at": collections[0].collected_at.isoformat() if collections else None,
            "last_collection_at": collections[-1].collected_at.isoformat() if collections else None,
        },
        "producers": producer_rows,
        "geojson": {"type": "FeatureCollection", "features": features},
    }
