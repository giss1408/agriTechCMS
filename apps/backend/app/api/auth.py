"""Phone + SMS code login for every internal role (no passwords: see ADR 0003)."""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core import security
from ..core.deps import current_user
from ..core.envelope import Envelope, ok
from ..core.errors import ApiError
from ..core.timeutil import utcnow
from ..db import get_db
from ..models import OtpChallenge, RefreshToken, User
from ..schemas import CooperativeBrief, MeOut, OtpRequest, OtpVerify, RefreshIn, TokenOut, UserOut
from ..services.sms import send_sms

router = APIRouter(prefix="/auth", tags=["auth"])

PERMISSIONS = {
    "collector": ["collections:create", "collections:read:own", "producers:read", "producers:create", "sync"],
    "admin": ["*"],
    "super_admin": ["*"],
}


def me_out(user: User) -> MeOut:
    return MeOut(
        **UserOut.model_validate(user).model_dump(),
        cooperative=CooperativeBrief.model_validate(user.cooperative),
        permissions=PERMISSIONS[user.role],
    )


async def _issue_tokens(db: AsyncSession, user: User, device_id: str | None) -> TokenOut:
    access, expires_in = security.create_access_token(user.id, user.cooperative_id, user.role)
    refresh = security.new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=security.hash_refresh_token(refresh),
            device_id=device_id,
            expires_at=utcnow() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    user.last_seen_at = utcnow()
    await db.commit()
    return TokenOut(access_token=access, refresh_token=refresh, expires_in=expires_in, user=me_out(user))


@router.post("/request-otp", response_model=Envelope[dict])
async def request_otp(body: OtpRequest, db: AsyncSession = Depends(get_db)):
    now = utcnow()
    recent = (
        await db.execute(
            select(func.count(), func.max(OtpChallenge.created_at)).where(
                OtpChallenge.phone == body.phone, OtpChallenge.created_at > now - timedelta(hours=1)
            )
        )
    ).one()
    if recent[0] >= security.OTP_MAX_SENDS_PER_HOUR:
        raise ApiError(429, "too_many_codes", "Trop de codes demandés. Réessayez dans une heure.")
    if recent[1] and now - recent[1] < security.OTP_RESEND_AFTER:
        raise ApiError(429, "resend_too_soon", "Patientez une minute avant de redemander un code.")

    data: dict = {"sent": True, "expires_in": int(security.OTP_TTL.total_seconds())}
    user = (await db.execute(select(User).where(User.phone == body.phone, User.is_active))).scalar_one_or_none()
    code = security.new_otp()
    # Same answer whether the number is known or not: no account enumeration. Unknown numbers get no SMS.
    db.add(OtpChallenge(phone=body.phone, code_hash=security.hash_otp(body.phone, code), expires_at=now + security.OTP_TTL))
    if user:
        await send_sms(db, body.phone, f"Votre code de connexion : {code}. Valable 5 minutes. Ne le partagez avec personne.", kind="otp", cooperative_id=user.cooperative_id)
        if settings.echo_otp:
            data["dev_code"] = code
    await db.commit()
    return ok(data)


@router.post("/verify-otp", response_model=Envelope[TokenOut])
async def verify_otp(body: OtpVerify, db: AsyncSession = Depends(get_db)):
    now = utcnow()
    challenge = (
        await db.execute(
            select(OtpChallenge)
            .where(OtpChallenge.phone == body.phone, OtpChallenge.consumed_at.is_(None))
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not challenge or challenge.expires_at < now:
        raise ApiError(401, "otp_expired", "Code expiré. Demandez un nouveau code.")
    if challenge.attempts >= security.OTP_MAX_ATTEMPTS:
        raise ApiError(429, "otp_locked", "Trop d'essais. Demandez un nouveau code.")
    challenge.attempts += 1
    if not security.otp_matches(body.phone, body.otp, challenge.code_hash):
        await db.commit()
        raise ApiError(401, "otp_invalid", "Code incorrect.", attempts_left=security.OTP_MAX_ATTEMPTS - challenge.attempts)
    user = (await db.execute(select(User).where(User.phone == body.phone, User.is_active))).scalar_one_or_none()
    if not user:
        await db.commit()
        raise ApiError(401, "otp_invalid", "Code incorrect.")
    challenge.consumed_at = now
    return ok(await _issue_tokens(db, user, body.device_id))


@router.post("/refresh", response_model=Envelope[TokenOut])
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == security.hash_refresh_token(body.refresh_token)))
    ).scalar_one_or_none()
    if not token or token.revoked_at or token.expires_at < utcnow():
        raise ApiError(401, "refresh_invalid", "Session expirée, reconnectez-vous.")
    user = await db.get(User, token.user_id)
    if not user or not user.is_active:
        raise ApiError(401, "unauthorized", "Compte inactif")
    token.revoked_at = utcnow()  # rotation: each refresh token works once
    return ok(await _issue_tokens(db, user, token.device_id))


@router.post("/logout", response_model=Envelope[dict])
async def logout(body: RefreshIn, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == security.hash_refresh_token(body.refresh_token)))
    ).scalar_one_or_none()
    if token and token.user_id == user.id:
        token.revoked_at = utcnow()
        await db.commit()
    return ok({"logged_out": True})
