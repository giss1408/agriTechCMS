"""Dashboard, reports, uploads, the public buyer trace page, the USSD channel and dev helpers."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.deps import current_user, require_admin, require_staff
from ..core.envelope import Envelope, ok
from ..core.errors import ApiError, not_found
from ..core.timeutil import campaign_bounds, campaign_of, utcnow
from ..db import get_db
from ..models import Collection, Lot, Notification, Parcel, Producer, Upload, User, Zone
from ..services import dashboard, lots, ussd

router = APIRouter()

# ---------------------------------------------------------------- dashboard & reports


@router.get("/dashboard/summary", response_model=Envelope[dict], tags=["dashboard"])
async def dashboard_summary(db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    return ok(await dashboard.summary(db, user.cooperative))


@router.get("/reports/campaign", response_model=Envelope[dict], tags=["reports"])
async def campaign_report(
    campaign: str | None = Query(None, pattern=r"^\d{4}-\d{4}$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    coop = user.cooperative
    campaign = campaign or campaign_of(utcnow().date(), coop.campaign_start_month)
    start, end = campaign_bounds(campaign, coop.campaign_start_month)
    base = (
        Collection.cooperative_id == coop.id,
        Collection.collected_at >= start,
        Collection.collected_at < end,
        Collection.status.in_(("validated", "paid")),
    )
    agg = (func.count(), func.coalesce(func.sum(Collection.weight_kg), 0), func.coalesce(func.sum(Collection.amount), 0))

    def rows(result):
        return [{"key": k, "count": n, "weight_kg": float(w), "amount": int(a)} for k, n, w, a in result]

    by_quality = rows(await db.execute(select(Collection.product + " " + Collection.quality, *agg).where(*base).group_by(Collection.product, Collection.quality)))
    by_collector = rows(await db.execute(select(User.name, *agg).join(User, User.id == Collection.collector_id).where(*base).group_by(User.name)))
    by_zone = rows(
        await db.execute(
            select(func.coalesce(Zone.name, "Sans zone"), *agg)
            .join(Producer, Producer.id == Collection.producer_id)
            .outerjoin(Zone, Zone.id == Producer.zone_id)
            .where(*base)
            .group_by(Zone.name)
        )
    )
    return ok({"campaign": campaign, "by_quality": by_quality, "by_collector": by_collector, "by_zone": by_zone})


@router.get("/reports/eudr.geojson", tags=["reports"])
async def eudr_all(db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    """Every geolocated parcel of the cooperative (for a due-diligence statement covering the whole campaign)."""
    rows = (
        await db.execute(
            select(Parcel, Producer.code).join(Producer, Producer.id == Parcel.producer_id)
            .where(Parcel.cooperative_id == user.cooperative_id, Parcel.geometry.is_not(None))
        )
    ).all()
    features = [
        {"type": "Feature", "geometry": p.geometry,
         "properties": {"parcel_id": p.id, "producer_code": code, "crop": p.crop,
                        "area_ha": float(p.measured_area_hectares or p.area_hectares or 0) or None}}
        for p, code in rows
    ]
    return JSONResponse({"type": "FeatureCollection", "features": features}, media_type="application/geo+json",
                        headers={"Content-Disposition": 'attachment; filename="parcelles-eudr.geojson"'})


# ---------------------------------------------------------------- public buyer page


@router.get("/public/trace/{token}", response_model=Envelope[dict], tags=["public"])
async def public_trace(token: str, db: AsyncSession = Depends(get_db)):
    """No login: anyone with the link (or the QR on the bags) sees where the lot comes from.
    Personal data (phones, ID numbers, first names) is never included."""
    lot = (await db.execute(select(Lot).where(Lot.trace_token == token))).scalar_one_or_none()
    if not lot:
        raise not_found("Lot")
    return ok(await lots.traceability(db, lot, public=True))


# ---------------------------------------------------------------- USSD


@router.post("/channels/ussd", response_class=PlainTextResponse, tags=["channels"])
async def ussd_callback(
    key: str = Query(..., description="Shared secret configured in the aggregator's callback URL"),
    sessionId: str = Form(""),  # noqa: N803 - aggregator field names
    phoneNumber: str = Form(...),  # noqa: N803
    text: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if key != settings.ussd_key:
        raise ApiError(401, "unauthorized", "Clé USSD invalide")
    return await ussd.handle(db, phoneNumber, text)


# ---------------------------------------------------------------- uploads

ALLOWED_IMAGES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("/uploads/photo", response_model=Envelope[dict], status_code=201, tags=["uploads"])
async def upload_photo(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    if file.content_type not in ALLOWED_IMAGES:
        raise ApiError(415, "unsupported_type", "Formats acceptés : JPEG, PNG, WebP")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, "file_too_large", "Photo trop volumineuse (compressez-la sur le téléphone)")
    digest = hashlib.sha256(content).hexdigest()
    folder = Path(settings.upload_dir) / user.cooperative_id
    folder.mkdir(parents=True, exist_ok=True)
    upload = Upload(cooperative_id=user.cooperative_id, uploaded_by=user.id, content_type=file.content_type,
                    size_bytes=len(content), sha256=digest, path="")
    db.add(upload)
    await db.flush()
    path = folder / f"{upload.id}{ALLOWED_IMAGES[file.content_type]}"
    path.write_bytes(content)
    upload.path = str(path)
    await db.commit()
    return ok({"id": upload.id, "size_bytes": len(content), "sha256": digest})


@router.get("/uploads/{upload_id}", tags=["uploads"])
async def get_upload(upload_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    upload = await db.get(Upload, upload_id)
    if not upload or upload.cooperative_id != user.cooperative_id or not Path(upload.path).exists():
        raise not_found("Photo")
    return FileResponse(upload.path, media_type=upload.content_type)


# ---------------------------------------------------------------- dev helpers (never in prod)


@router.get("/dev/sms", response_model=Envelope[list[dict]], tags=["dev"])
async def dev_sms(phone: str | None = None, limit: int = Query(30, le=200), db: AsyncSession = Depends(get_db)):
    """The console SMS gateway's outbox: lets the demo show OTPs and payment confirmations."""
    if settings.is_prod:
        raise not_found("Ressource")
    stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    if phone:
        stmt = stmt.where(Notification.phone == phone)
    rows = (await db.execute(stmt)).scalars()
    return ok([{"id": n.id, "phone": n.phone, "kind": n.kind, "body": n.body, "created_at": n.created_at} for n in rows])
