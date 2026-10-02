from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import page_params, require_admin
from ..core.envelope import Envelope, Meta, Page, ok
from ..db import get_db
from ..models import Lot, User
from ..schemas import BulkIds, LotIn, LotOut, LotShipIn
from ..services import lots as svc

router = APIRouter(prefix="/lots", tags=["lots & traceability"])


class SealIn(BaseModel):
    bags_count: int | None = Field(default=None, gt=0)


@router.get("", response_model=Envelope[list[LotOut]])
async def list_lots(
    status: str | None = Query(None, pattern="^(open|sealed|shipped)$"),
    page: Page = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    conds = [Lot.cooperative_id == user.cooperative_id]
    if status:
        conds.append(Lot.status == status)
    total = (await db.execute(select(func.count()).where(*conds))).scalar_one()
    rows = (await db.execute(select(Lot).where(*conds).order_by(Lot.created_at.desc()).offset(page.offset).limit(page.per_page))).scalars()
    return ok([svc.to_out(x) for x in rows], Meta(page=page.page, per_page=page.per_page, total=total))


@router.post("", response_model=Envelope[dict], status_code=201)
async def create_lot(body: LotIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    lot = await svc.create(db, user, body.product, body.quality, body.notes)
    refused = await svc.add_collections(db, user, lot, body.collection_ids) if body.collection_ids else []
    await db.commit()
    return ok({"lot": svc.to_out(lot), "refused": refused})


@router.get("/{lot_id}", response_model=Envelope[LotOut])
async def get_lot(lot_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    return ok(svc.to_out(await svc.get_for(db, user, lot_id)))


@router.post("/{lot_id}/collections", response_model=Envelope[dict])
async def add_collections(lot_id: str, body: BulkIds, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    lot = await svc.get_for(db, user, lot_id)
    refused = await svc.add_collections(db, user, lot, body.ids)
    await db.commit()
    return ok({"lot": svc.to_out(lot), "refused": refused})


@router.delete("/{lot_id}/collections/{collection_id}", response_model=Envelope[LotOut])
async def remove_collection(lot_id: str, collection_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    lot = await svc.get_for(db, user, lot_id)
    await svc.remove_collection(db, lot, collection_id)
    await db.commit()
    return ok(svc.to_out(lot))


@router.post("/{lot_id}/seal", response_model=Envelope[LotOut])
async def seal(lot_id: str, body: SealIn | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    lot = await svc.get_for(db, user, lot_id)
    svc.seal(db, user, lot, body.bags_count if body else None)
    await db.commit()
    return ok(svc.to_out(lot))


@router.post("/{lot_id}/ship", response_model=Envelope[LotOut])
async def ship(lot_id: str, body: LotShipIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    lot = await svc.get_for(db, user, lot_id)
    svc.ship(db, user, lot, body.buyer_name, body.destination, body.bags_count)
    await db.commit()
    return ok(svc.to_out(lot))


@router.get("/{lot_id}/traceability", response_model=Envelope[dict])
async def traceability(lot_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    lot = await svc.get_for(db, user, lot_id)
    return ok(await svc.traceability(db, lot, public=False))


@router.get("/{lot_id}/eudr.geojson")
async def eudr_geojson(lot_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    """Parcel polygons/points behind the lot, as GeoJSON — the format the EU information system accepts
    for due-diligence statements."""
    lot = await svc.get_for(db, user, lot_id)
    trace = await svc.traceability(db, lot, public=True)
    return JSONResponse(
        trace["geojson"],
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="{lot.reference}.geojson"'},
    )
