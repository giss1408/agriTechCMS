import csv
import io
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import current_user, is_admin, page_params, require_admin, require_staff
from ..core.envelope import Envelope, Meta, Page, ok
from ..core.errors import ApiError
from ..core.timeutil import utcnow
from ..db import get_db
from ..models import AuditEvent, Collection, Producer, User
from ..schemas import BulkIds, CollectionIn, CollectionOut, CollectionPatch, CollectionTotals, RejectIn
from ..services import collections as svc

router = APIRouter(prefix="/collections", tags=["collections"])

STATUSES = "^(pending_validation|validated|rejected|paid|cancelled)$"


def _filters(
    user: User,
    date_from: date | None,
    date_to: date | None,
    status: str | None,
    collector_id: str | None,
    producer_id: str | None,
    quality: str | None,
    product: str | None,
    zone_id: str | None,
    lot_id: str | None,
    unlotted: bool,
):
    conds = [Collection.cooperative_id == user.cooperative_id]
    if not is_admin(user):
        conds.append(Collection.collector_id == user.id)  # collectors only see their own work
    if date_from:
        conds.append(Collection.collected_at >= datetime.combine(date_from, time.min))
    if date_to:
        conds.append(Collection.collected_at < datetime.combine(date_to + timedelta(days=1), time.min))
    if status:
        conds.append(Collection.status == status)
    if collector_id:
        conds.append(Collection.collector_id == collector_id)
    if producer_id:
        conds.append(Collection.producer_id == producer_id)
    if quality:
        conds.append(Collection.quality == quality)
    if product:
        conds.append(Collection.product == product)
    if zone_id:
        conds.append(Collection.producer_id.in_(select(Producer.id).where(Producer.zone_id == zone_id)))
    if lot_id:
        conds.append(Collection.lot_id == lot_id)
    if unlotted:
        conds.append(Collection.lot_id.is_(None))
    return conds


def filter_params(
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = Query(None, pattern=STATUSES),
    collector_id: str | None = None,
    producer_id: str | None = None,
    quality: str | None = None,
    product: str | None = None,
    zone_id: str | None = None,
    lot_id: str | None = None,
    unlotted: bool = False,
) -> dict:
    return locals()


@router.get("", response_model=Envelope[list[CollectionOut]])
async def list_collections(
    f: dict = Depends(filter_params),
    page: Page = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    conds = _filters(user, **f)
    total = (await db.execute(select(func.count()).where(*conds))).scalar_one()
    rows = (
        await db.execute(
            select(Collection).where(*conds).order_by(Collection.collected_at.desc()).offset(page.offset).limit(page.per_page)
        )
    ).scalars().all()
    return ok([svc.to_out(c) for c in rows], Meta(page=page.page, per_page=page.per_page, total=total))


@router.get("/totals", response_model=Envelope[CollectionTotals])
async def totals(f: dict = Depends(filter_params), db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    """Totals for the current filters (footer of the collections table)."""
    conds = _filters(user, **f)
    if not f.get("status"):
        conds.append(Collection.status.not_in(("rejected", "cancelled")))
    n, w, a = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(Collection.weight_kg), 0), func.coalesce(func.sum(Collection.amount), 0)).where(*conds)
        )
    ).one()
    return ok(CollectionTotals(count=n, weight_kg=w, amount=int(a)))


@router.get("/stats/daily", response_model=Envelope[CollectionTotals])
async def stats_daily(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    today = utcnow().date()
    f = dict.fromkeys(("status", "collector_id", "producer_id", "quality", "product", "zone_id", "lot_id"))
    return await totals({**f, "date_from": today, "date_to": today, "unlotted": False}, db, user)


@router.get("/export")
async def export_csv(f: dict = Depends(filter_params), db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    rows = (await db.execute(select(Collection).where(*_filters(user, **f)).order_by(Collection.collected_at))).scalars().all()
    buf = io.StringIO()
    buf.write("﻿")  # Excel opens UTF-8 with accents correctly only with a BOM
    w = csv.writer(buf, delimiter=";")  # French Excel expects semicolons
    w.writerow(["reference", "date", "producteur_code", "producteur", "collecteur", "produit", "qualite", "poids_kg",
                "humidite_pct", "prix_kg", "montant_fcfa", "statut", "lot_id", "paiement_id", "gps_lat", "gps_lng"])
    for c in rows:
        w.writerow([c.reference, c.collected_at.strftime("%Y-%m-%d %H:%M"), c.producer.code, c.producer.full_name, c.collector.name,
                    c.product, c.quality, str(c.weight_kg).replace(".", ","),
                    str(c.moisture_percent or "").replace(".", ","), c.unit_price, c.amount, c.status, c.lot_id or "",
                    c.payment_id or "", c.gps_lat or "", c.gps_lng or ""])
    name = f"collectes-{utcnow():%Y%m%d-%H%M}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("", response_model=Envelope[CollectionOut], status_code=201)
async def create_collection(
    body: CollectionIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
    x_device_id: str | None = Header(default=None),
):
    """Idempotent on `client_uuid`: replaying the same collection returns the stored one with 200."""
    c, created = await svc.ingest(db, user, body, source="online" if x_device_id else "web", device_id=x_device_id)
    await db.commit()
    payload = ok(svc.to_out(c))
    if not created:
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"), headers={"X-Duplicate": "true"})
    return payload


@router.post("/validate", response_model=Envelope[dict])
async def validate_many(body: BulkIds, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    """Bulk validation from the web table. Collections that cannot be validated are reported, not fatal."""
    done, refused = [], []
    for cid in body.ids:
        try:
            c = await svc.get_for(db, user, cid)
            svc.validate(db, user, c)
            done.append(cid)
        except ApiError as exc:
            refused.append({"id": cid, "reason": exc.message})
    await db.commit()
    return ok({"validated": done, "refused": refused})


@router.get("/{collection_id}", response_model=Envelope[CollectionOut])
async def get_collection(collection_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    return ok(svc.to_out(await svc.get_for(db, user, collection_id)))


@router.get("/{collection_id}/history", response_model=Envelope[list[dict]])
async def history(collection_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    c = await svc.get_for(db, user, collection_id)
    rows = (
        await db.execute(
            select(AuditEvent, User.name)
            .outerjoin(User, User.id == AuditEvent.actor_id)
            .where(AuditEvent.entity_id == c.id)
            .order_by(AuditEvent.at)
        )
    ).all()
    return ok([{"at": e.at, "action": e.action, "actor": name, "changes": e.changes} for e, name in rows])


@router.patch("/{collection_id}", response_model=Envelope[CollectionOut])
async def patch_collection(collection_id: str, body: CollectionPatch, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    c = await svc.get_for(db, user, collection_id)
    await svc.admin_edit(db, user, c, **body.model_dump(exclude_unset=True))
    await db.commit()
    return ok(svc.to_out(c))


@router.post("/{collection_id}/validate", response_model=Envelope[CollectionOut])
async def validate_one(collection_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    c = await svc.get_for(db, user, collection_id)
    svc.validate(db, user, c)
    await db.commit()
    return ok(svc.to_out(c))


@router.post("/{collection_id}/reject", response_model=Envelope[CollectionOut])
async def reject_one(collection_id: str, body: RejectIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    c = await svc.get_for(db, user, collection_id)
    svc.reject(db, user, c, body.reason)
    await db.commit()
    return ok(svc.to_out(c))


@router.delete("/{collection_id}", response_model=Envelope[CollectionOut])
async def cancel_one(collection_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    c = await svc.get_for(db, user, collection_id)
    svc.cancel(db, user, c)
    await db.commit()
    return ok(svc.to_out(c))
