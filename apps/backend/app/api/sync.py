from datetime import datetime

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import require_admin, require_staff
from ..core.envelope import Envelope, ok
from ..db import get_db
from ..models import SyncDevice, User
from ..schemas import DeviceOut, SyncPullOut, SyncPushIn, SyncPushOut
from ..services import sync as svc

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/push", response_model=Envelope[SyncPushOut])
async def push(body: SyncPushIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    """Send collections recorded offline. Each item is accepted, recognised as a duplicate, or rejected
    with a reason; the phone marks accepted and duplicate items as synced and shows rejected ones."""
    return ok(await svc.push(db, user, body))


@router.get("/pull", response_model=Envelope[SyncPullOut])
async def pull(
    since: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
    x_device_id: str | None = Header(default=None),
):
    """Everything the phone needs to work offline. Omit `since` for a full download; afterwards pass the
    `cursor` from the previous response."""
    return ok(await svc.pull(db, user, since, x_device_id))


@router.get("/devices", response_model=Envelope[list[DeviceOut]])
async def devices(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (
        await db.execute(
            select(SyncDevice, User.name)
            .join(User, User.id == SyncDevice.user_id)
            .where(SyncDevice.cooperative_id == admin.cooperative_id)
            .order_by(SyncDevice.last_push_at.desc())
        )
    ).all()
    out = []
    for device, name in rows:
        d = DeviceOut.model_validate(device)
        d.user_name = name
        out.append(d)
    return ok(out)


@router.get("/status/{device_id}", response_model=Envelope[DeviceOut | None])
async def device_status(device_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    device = await db.get(SyncDevice, device_id)
    if not device or device.cooperative_id != admin.cooperative_id:
        return ok(None)
    return ok(DeviceOut.model_validate(device))
