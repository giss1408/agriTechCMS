from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import current_user, require, require_admin
from ..core.envelope import Envelope, ok
from ..core.errors import ApiError, not_found
from ..core.timeutil import campaign_of, utcnow
from ..db import get_db
from ..models import Cooperative, PurchasePrice, User, Zone
from ..schemas import AlertSettings, CooperativeOut, CooperativePatch, PriceIn, PriceOut, PricePatch, ZoneIn, ZoneOut
from ..services import audit

router = APIRouter(tags=["cooperative & settings"])


def coop_out(c: Cooperative) -> CooperativeOut:
    out = CooperativeOut.model_validate(c)
    out.current_campaign = campaign_of(utcnow().date(), c.campaign_start_month)
    return out


@router.get("/cooperative", response_model=Envelope[CooperativeOut])
async def get_cooperative(user: User = Depends(current_user)):
    return ok(coop_out(user.cooperative))


@router.patch("/cooperative", response_model=Envelope[CooperativeOut])
async def patch_cooperative(
    body: CooperativePatch, db: AsyncSession = Depends(get_db), user: User = Depends(require("super_admin", "admin"))
):
    coop = user.cooperative
    updates = body.model_dump(exclude_unset=True)
    audit.record(db, cooperative_id=coop.id, actor_id=user.id, entity="cooperative", entity_id=coop.id, action="updated", changes=audit.diff(coop, updates))
    for k, v in updates.items():
        setattr(coop, k, v)
    await db.commit()
    return ok(coop_out(coop))


# ---------------------------------------------------------------- prices


@router.get("/settings/purchase-prices", response_model=Envelope[list[PriceOut]])
async def list_prices(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        await db.execute(
            select(PurchasePrice)
            .where(PurchasePrice.cooperative_id == user.cooperative_id)
            .order_by(PurchasePrice.product, PurchasePrice.quality, PurchasePrice.effective_from.desc())
        )
    ).scalars()
    return ok([PriceOut.model_validate(p) for p in rows])


@router.post("/settings/purchase-prices", response_model=Envelope[PriceOut], status_code=201)
async def add_price(body: PriceIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    """Adding a price closes the previous open-ended one for the same product/quality the day before."""
    if body.effective_to and body.effective_to < body.effective_from:
        raise ApiError(400, "invalid_period", "La date de fin précède la date de début")
    previous = (
        await db.execute(
            select(PurchasePrice).where(
                PurchasePrice.cooperative_id == user.cooperative_id,
                PurchasePrice.product == body.product,
                PurchasePrice.quality == body.quality,
                PurchasePrice.effective_to.is_(None),
                PurchasePrice.effective_from < body.effective_from,
            )
        )
    ).scalars().all()
    for p in previous:
        p.effective_to = body.effective_from - timedelta(days=1)
    price = PurchasePrice(cooperative_id=user.cooperative_id, **body.model_dump())
    db.add(price)
    await db.flush()
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="price", entity_id=price.id, action="created", changes=body.model_dump())
    await db.commit()
    return ok(PriceOut.model_validate(price))


@router.patch("/settings/purchase-prices/{price_id}", response_model=Envelope[PriceOut])
async def patch_price(price_id: str, body: PricePatch, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    price = await db.get(PurchasePrice, price_id)
    if not price or price.cooperative_id != user.cooperative_id:
        raise not_found("Prix")
    updates = body.model_dump(exclude_unset=True)
    # Existing collections keep the unit price they were valued with: changing a price never rewrites history.
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="price", entity_id=price.id, action="updated", changes=audit.diff(price, updates))
    for k, v in updates.items():
        setattr(price, k, v)
    await db.commit()
    return ok(PriceOut.model_validate(price))


# ---------------------------------------------------------------- alert thresholds


@router.get("/settings/alerts", response_model=Envelope[AlertSettings])
async def get_alerts(user: User = Depends(current_user)):
    c = user.cooperative
    return ok(AlertSettings(max_moisture_percent=c.max_moisture_percent, max_weight_kg=c.max_weight_kg))


@router.put("/settings/alerts", response_model=Envelope[AlertSettings])
async def put_alerts(body: AlertSettings, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    c = user.cooperative
    audit.record(db, cooperative_id=c.id, actor_id=user.id, entity="cooperative", entity_id=c.id, action="alerts_updated", changes=audit.diff(c, body.model_dump()))
    c.max_moisture_percent = body.max_moisture_percent
    c.max_weight_kg = body.max_weight_kg
    await db.commit()
    return ok(body)


# ---------------------------------------------------------------- zones


@router.get("/zones", response_model=Envelope[list[ZoneOut]])
async def list_zones(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    rows = (await db.execute(select(Zone).where(Zone.cooperative_id == user.cooperative_id).order_by(Zone.name))).scalars()
    return ok([ZoneOut.model_validate(z) for z in rows])


@router.post("/zones", response_model=Envelope[ZoneOut], status_code=201)
async def create_zone(body: ZoneIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    zone = Zone(cooperative_id=user.cooperative_id, name=body.name.strip())
    db.add(zone)
    try:
        await db.commit()
    except IntegrityError:
        raise ApiError(409, "zone_exists", "Cette zone existe déjà") from None
    return ok(ZoneOut.model_validate(zone))
