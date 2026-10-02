from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import current_user, require_admin
from ..core.envelope import Envelope, ok
from ..core.errors import ApiError, not_found
from ..db import get_db
from ..models import User
from ..schemas import MeOut, UserIn, UserOut, UserPatch
from ..services import audit
from .auth import me_out

router = APIRouter(prefix="/users", tags=["users"])


async def _get(db: AsyncSession, admin: User, user_id: str) -> User:
    u = await db.get(User, user_id)
    if not u or u.cooperative_id != admin.cooperative_id:
        raise not_found("Utilisateur")
    return u


@router.get("/me", response_model=Envelope[MeOut])
async def me(user: User = Depends(current_user)):
    return ok(me_out(user))


@router.get("", response_model=Envelope[list[UserOut]])
async def list_users(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (await db.execute(select(User).where(User.cooperative_id == admin.cooperative_id).order_by(User.role, User.name))).scalars()
    return ok([UserOut.model_validate(u) for u in rows])


@router.post("", response_model=Envelope[UserOut], status_code=201)
async def create_user(body: UserIn, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    if body.role == "super_admin" and admin.role != "super_admin":
        raise ApiError(403, "forbidden", "Seul un super administrateur peut en créer un autre")
    u = User(cooperative_id=admin.cooperative_id, name=body.name, phone=body.phone, role=body.role)
    db.add(u)
    try:
        await db.flush()
    except IntegrityError:
        raise ApiError(409, "phone_taken", "Ce numéro est déjà utilisé par un autre compte") from None
    audit.record(db, cooperative_id=admin.cooperative_id, actor_id=admin.id, entity="user", entity_id=u.id, action="created", changes={"role": body.role})
    await db.commit()
    return ok(UserOut.model_validate(u))


@router.get("/{user_id}", response_model=Envelope[UserOut])
async def get_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    return ok(UserOut.model_validate(await _get(db, admin, user_id)))


@router.patch("/{user_id}", response_model=Envelope[UserOut])
async def patch_user(user_id: str, body: UserPatch, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    u = await _get(db, admin, user_id)
    updates = body.model_dump(exclude_unset=True)
    if u.id == admin.id and (updates.get("is_active") is False or updates.get("role", u.role) != u.role):
        raise ApiError(422, "self_lockout", "Vous ne pouvez pas modifier votre propre rôle ou vous désactiver")
    changes = audit.diff(u, updates)
    for k, v in updates.items():
        setattr(u, k, v)
    audit.record(db, cooperative_id=admin.cooperative_id, actor_id=admin.id, entity="user", entity_id=u.id, action="updated", changes=changes)
    await db.commit()
    return ok(UserOut.model_validate(u))


@router.delete("/{user_id}", response_model=Envelope[UserOut])
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    return await patch_user(user_id, UserPatch(is_active=False), db, admin)
