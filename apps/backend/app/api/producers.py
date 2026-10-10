import io
from decimal import Decimal

import segno
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import geo
from ..core.deps import current_user, page_params, require_admin, require_staff
from ..core.envelope import Envelope, Meta, Page, ok
from ..core.errors import ApiError, not_found
from ..core.phone import normalize_phone
from ..core.timeutil import campaign_of, utcnow
from ..db import get_db
from ..models import Advance, Parcel, Producer, User
from ..schemas import (
    AdvanceIn,
    AdvanceOut,
    BalanceOut,
    ParcelIn,
    ParcelOut,
    ParcelPatch,
    ProducerIn,
    ProducerOut,
    ProducerPatch,
)
from ..services import audit
from ..services import producers as svc
from ..services.balances import producer_balance

router = APIRouter(tags=["producers"])


@router.get("/producers", response_model=Envelope[list[ProducerOut]])
async def list_producers(
    search: str | None = None,
    zone_id: str | None = None,
    status: str | None = Query(None, pattern="^(active|inactive)$"),
    missing_parcel: bool = False,
    sort: str = Query("code", pattern="^-?(code|last_name|created_at|updated_at)$"),
    page: Page = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    stmt = select(Producer).where(Producer.cooperative_id == user.cooperative_id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Producer.first_name.ilike(like), Producer.last_name.ilike(like), Producer.code.ilike(like), Producer.phone.ilike(like))
        )
    if zone_id:
        stmt = stmt.where(Producer.zone_id == zone_id)
    if status:
        stmt = stmt.where(Producer.status == status)
    if missing_parcel:
        has_geo = select(Parcel.producer_id).where(Parcel.geometry.is_not(None))
        stmt = stmt.where(Producer.id.not_in(has_geo))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    column = getattr(Producer, sort.lstrip("-"))
    stmt = stmt.order_by(column.desc() if sort.startswith("-") else column).offset(page.offset).limit(page.per_page)
    rows = (await db.execute(stmt)).scalars().all()
    return ok([svc.producer_out(p, geometry=False) for p in rows], Meta(page=page.page, per_page=page.per_page, total=total))


@router.post("/producers", response_model=Envelope[ProducerOut], status_code=201)
async def create_producer(body: ProducerIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    producer = await svc.create(db, user, body)
    await db.commit()
    return ok(svc.producer_out(producer))


@router.post("/producers/import", response_model=Envelope[dict])
async def import_producers(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise ApiError(413, "file_too_large", "Fichier trop volumineux (5 Mo max)")
    result = await svc.import_csv(db, user, content)
    await db.commit()
    return ok(result)


@router.get("/producers/by-phone/{phone}", response_model=Envelope[list[ProducerOut]])
async def by_phone(phone: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    # Several family members often share one phone: return all of them.
    rows = (
        await db.execute(select(Producer).where(Producer.cooperative_id == user.cooperative_id, Producer.phone == normalize_phone(phone)))
    ).scalars()
    return ok([svc.producer_out(p) for p in rows])


@router.get("/producers/{producer_id}", response_model=Envelope[ProducerOut])
async def get_producer(producer_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    return ok(svc.producer_out(await svc.get_for(db, user, producer_id)))


@router.patch("/producers/{producer_id}", response_model=Envelope[ProducerOut])
async def patch_producer(producer_id: str, body: ProducerPatch, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    p = await svc.get_for(db, user, producer_id)
    updates = body.model_dump(exclude_unset=True)
    if "mobile_money" in updates:
        momo = updates.pop("mobile_money")
        updates["momo_operator"] = momo["operator"] if momo else None
        updates["momo_account"] = momo["account"] if momo else None
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="producer", entity_id=p.id, action="updated", changes=audit.diff(p, updates))
    for k, v in updates.items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p, ["zone", "parcels"])
    return ok(svc.producer_out(p))


@router.delete("/producers/{producer_id}", response_model=Envelope[ProducerOut])
async def deactivate_producer(producer_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    return await patch_producer(producer_id, ProducerPatch(status="inactive"), db, user)


@router.get("/producers/{producer_id}/qr-code", responses={200: {"content": {"image/png": {}}}})
async def producer_qr(producer_id: str, scale: int = Query(8, ge=2, le=20), db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    p = await svc.get_for(db, user, producer_id)
    buf = io.BytesIO()
    segno.make(svc.qr_payload(p), error="m").save(buf, kind="png", scale=scale, border=2)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/producers/{producer_id}/balance", response_model=Envelope[BalanceOut])
async def balance(producer_id: str, campaign: str | None = Query(None, pattern=r"^\d{4}-\d{4}$"), db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    p = await svc.get_for(db, user, producer_id)
    coop = user.cooperative
    campaign = campaign or campaign_of(utcnow().date(), coop.campaign_start_month)
    return ok(await producer_balance(db, p, campaign, coop.campaign_start_month))


# ---------------------------------------------------------------- parcels


@router.get("/producers/{producer_id}/parcels", response_model=Envelope[list[ParcelOut]])
async def list_parcels(producer_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    p = await svc.get_for(db, user, producer_id)
    return ok([svc.parcel_out(x) for x in p.parcels])


@router.post("/producers/{producer_id}/parcels", response_model=Envelope[ParcelOut], status_code=201)
async def add_parcel(producer_id: str, body: ParcelIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    p = await svc.get_for(db, user, producer_id)
    parcel = svc.build_parcel(user, p.id, body)
    db.add(parcel)
    p.updated_at = utcnow()  # so phones pull the producer (and its parcels) again
    await db.flush()
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="parcel", entity_id=parcel.id, action="created")
    await db.commit()
    return ok(svc.parcel_out(parcel))


async def _parcel(db: AsyncSession, user: User, parcel_id: str) -> Parcel:
    parcel = await db.get(Parcel, parcel_id)
    if not parcel or parcel.cooperative_id != user.cooperative_id:
        raise not_found("Parcelle")
    return parcel


@router.patch("/parcels/{parcel_id}", response_model=Envelope[ParcelOut])
async def patch_parcel(parcel_id: str, body: ParcelPatch, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    parcel = await _parcel(db, user, parcel_id)
    updates = body.model_dump(exclude_unset=True)
    if "geometry" in updates:
        geometry = geo.validate_geometry(updates["geometry"]) if updates["geometry"] else None
        updates["geometry"] = geometry
        measured = geo.polygon_area_ha(geometry) if geometry else None
        updates["measured_area_hectares"] = Decimal(str(measured)) if measured is not None else None
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="parcel", entity_id=parcel.id, action="updated", changes=audit.diff(parcel, updates))
    for k, v in updates.items():
        setattr(parcel, k, v)
    await db.commit()
    return ok(svc.parcel_out(parcel))


@router.delete("/parcels/{parcel_id}", response_model=Envelope[dict])
async def delete_parcel(parcel_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    parcel = await _parcel(db, user, parcel_id)
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="parcel", entity_id=parcel.id, action="deleted", changes={"geometry": parcel.geometry})
    await db.delete(parcel)
    await db.commit()
    return ok({"deleted": parcel_id})


# ---------------------------------------------------------------- advances


@router.get("/producers/{producer_id}/advances", response_model=Envelope[list[AdvanceOut]])
async def list_advances(producer_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    p = await svc.get_for(db, user, producer_id)
    rows = (await db.execute(select(Advance).where(Advance.producer_id == p.id).order_by(Advance.given_at.desc()))).scalars()
    return ok([AdvanceOut.model_validate(a) for a in rows])


@router.post("/producers/{producer_id}/advances", response_model=Envelope[AdvanceOut], status_code=201)
async def add_advance(producer_id: str, body: AdvanceIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    p = await svc.get_for(db, user, producer_id)
    adv = Advance(
        cooperative_id=user.cooperative_id, producer_id=p.id, amount=body.amount, remaining=body.amount,
        reason=body.reason, given_at=body.given_at or utcnow().date(), created_by=user.id,
    )
    db.add(adv)
    await db.flush()
    audit.record(db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="advance", entity_id=adv.id, action="created", changes={"amount": body.amount})
    await db.commit()
    return ok(AdvanceOut.model_validate(adv))
