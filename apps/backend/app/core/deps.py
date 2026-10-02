from collections.abc import Callable

import jwt
from fastapi import Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from .envelope import Page
from .errors import ApiError
from .security import decode_access_token

ADMIN_ROLES = ("super_admin", "admin")


async def current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Jeton d'accès manquant")
    try:
        claims = decode_access_token(authorization.split(" ", 1)[1])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "token_expired", "Session expirée") from None
    except jwt.InvalidTokenError:
        raise ApiError(401, "unauthorized", "Jeton d'accès invalide") from None
    user = await db.get(User, claims["sub"])
    if not user or not user.is_active:
        raise ApiError(401, "unauthorized", "Compte inactif")
    return user


def require(*roles: str) -> Callable:
    async def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise ApiError(403, "forbidden", "Action non autorisée pour votre rôle")
        return user

    return _dep


require_admin = require(*ADMIN_ROLES)
require_staff = require(*ADMIN_ROLES, "collector")


def page_params(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)) -> Page:
    return Page(page=page, per_page=per_page)


def is_admin(user: User) -> bool:
    return user.role in ADMIN_ROLES
