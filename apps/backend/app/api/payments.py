from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import current_user, page_params, require_admin
from ..core.envelope import Envelope, Meta, Page, ok
from ..core.errors import ApiError
from ..core.security import webhook_signature_valid
from ..db import get_db
from ..models import Payment, User
from ..schemas import PayableOut, PaymentBatchIn, PaymentBatchOut, PaymentOut, WebhookIn
from ..services import payments as svc

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/payables", response_model=Envelope[list[PayableOut]])
async def payables(db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    """Producers with validated, unpaid collections — the 'to pay' screen."""
    return ok(await svc.payables(db, user.cooperative_id))


@router.get("", response_model=Envelope[list[PaymentOut]])
async def list_payments(
    status: str | None = Query(None, pattern="^(initiated|processing|success|failed|cancelled)$"),
    producer_id: str | None = None,
    batch_id: str | None = None,
    page: Page = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    conds = [Payment.cooperative_id == user.cooperative_id]
    if status:
        conds.append(Payment.status == status)
    if producer_id:
        conds.append(Payment.producer_id == producer_id)
    if batch_id:
        conds.append(Payment.batch_id == batch_id)
    total = (await db.execute(select(func.count()).where(*conds))).scalar_one()
    rows = (await db.execute(select(Payment).where(*conds).order_by(Payment.created_at.desc()).offset(page.offset).limit(page.per_page))).scalars()
    return ok([svc.to_out(p) for p in rows], Meta(page=page.page, per_page=page.per_page, total=total))


@router.get("/summary", response_model=Envelope[dict])
async def summary(db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    rows = (
        await db.execute(
            select(Payment.status, func.count(), func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.cooperative_id == user.cooperative_id)
            .group_by(Payment.status)
        )
    ).all()
    by_status = {s: {"count": n, "amount": int(a)} for s, n, a in rows}
    return ok({"by_status": by_status})


@router.post("/batch", response_model=Envelope[PaymentBatchOut], status_code=202)
async def create_batch(body: PaymentBatchIn, tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    """Asynchronous: transfers are sent after the response. Poll `GET /payments?batch_id=` for outcomes."""
    batch, payments, skipped = await svc.create_batch(db, user, body.producer_ids, body.collection_ids, body.reference_note)
    await db.commit()
    tasks.add_task(svc.dispatch, [p.id for p in payments if p.status == "initiated"])
    return ok(PaymentBatchOut(batch_id=batch.id, total_amount=batch.total_amount, count=batch.count,
                              payments=[svc.to_out(p) for p in payments], skipped=skipped))


@router.get("/{payment_id}", response_model=Envelope[PaymentOut])
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    return ok(svc.to_out(await svc.get_for(db, user, payment_id)))


@router.post("/{payment_id}/retry", response_model=Envelope[PaymentOut], status_code=202)
async def retry(payment_id: str, tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    p = await svc.get_for(db, user, payment_id)
    svc.prepare_retry(p)
    tasks.add_task(svc.dispatch, [p.id])
    return ok(svc.to_out(p))


@router.post("/{payment_id}/cancel", response_model=Envelope[PaymentOut])
async def cancel(payment_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    p = await svc.get_for(db, user, payment_id)
    await svc.cancel(db, user, p)
    await db.commit()
    return ok(svc.to_out(p))


@router.post("/webhook/{provider}", response_model=Envelope[dict], include_in_schema=True)
async def webhook(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Provider callback. The body must be signed: `X-Signature: hex(HMAC-SHA256(body, AGT_PAYMENT_WEBHOOK_SECRET))`.
    Provider-specific formats (CinetPay's x-token…) are translated to this shape by a thin adapter."""
    raw = await request.body()
    if not webhook_signature_valid(raw, request.headers.get("x-signature")):
        raise ApiError(401, "bad_signature", "Signature invalide")
    body = WebhookIn.model_validate_json(raw)
    payment = await svc.handle_webhook(db, body.payment_id, body.external_ref, body.status, body.reason, body.trans_id)
    await db.commit()
    return ok({"payment_id": payment.id, "status": payment.status, "provider": provider})
