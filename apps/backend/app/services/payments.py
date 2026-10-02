"""Producer payments: validated collections -> one transfer per producer, advances recovered first.

Advances are *reserved* when the payment is created (so two batches cannot recover the same advance)
and released only if the payment is cancelled. A failed payment keeps its collections and reservation
so it can be retried.
"""

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import db as dbmod
from ..core.errors import ApiError, not_found
from ..core.timeutil import utcnow
from ..models import Advance, Collection, Payment, PaymentBatch, Producer, User
from ..schemas import PayableOut, PaymentOut
from . import audit
from .providers import ProviderResult, get_provider
from .sms import fcfa, send_sms

log = logging.getLogger("agritech.payments")


def to_out(p: Payment) -> PaymentOut:
    out = PaymentOut.model_validate(p)
    out.producer_name = p.producer.full_name
    return out


def _payable_filter(cooperative_id: str):
    return (
        Collection.cooperative_id == cooperative_id,
        Collection.status == "validated",
        Collection.payment_id.is_(None),
    )


async def payables(db: AsyncSession, cooperative_id: str) -> list[PayableOut]:
    rows = (await db.execute(select(Collection).where(*_payable_filter(cooperative_id)))).scalars().all()
    grouped: dict[str, list[Collection]] = defaultdict(list)
    for c in rows:
        grouped[c.producer_id].append(c)
    if not grouped:
        return []
    advances = defaultdict(int)
    for a in (await db.execute(select(Advance).where(Advance.producer_id.in_(list(grouped)), Advance.remaining > 0))).scalars():
        advances[a.producer_id] += a.remaining
    out = []
    for producer_id, cols in grouped.items():
        prod = cols[0].producer
        gross = sum(c.amount for c in cols)
        out.append(
            PayableOut(
                producer_id=producer_id,
                producer_name=prod.full_name,
                producer_code=prod.code,
                momo_operator=prod.momo_operator,
                momo_account=prod.momo_account,
                collections_count=len(cols),
                gross_amount=gross,
                outstanding_advances=advances[producer_id],
                net_amount=max(0, gross - advances[producer_id]),
                oldest_collection_at=min(c.collected_at for c in cols),
            )
        )
    return sorted(out, key=lambda p: p.oldest_collection_at)


async def _reserve_advances(db: AsyncSession, producer_id: str, gross: int) -> tuple[int, list[dict]]:
    stmt = (
        select(Advance)
        .where(Advance.producer_id == producer_id, Advance.remaining > 0)
        .order_by(Advance.given_at, Advance.created_at)
    )
    left, allocations = gross, []
    for adv in (await db.execute(stmt)).scalars():
        if left == 0:
            break
        take = min(adv.remaining, left)
        adv.remaining -= take
        left -= take
        allocations.append({"advance_id": adv.id, "amount": take})
    return gross - left, allocations


async def create_batch(
    db: AsyncSession, user: User, producer_ids: list[str], collection_ids: list[str], note: str | None
) -> tuple[PaymentBatch, list[Payment], list[dict]]:
    if not producer_ids and not collection_ids:
        raise ApiError(400, "empty_selection", "Sélectionnez des producteurs ou des collectes à payer")
    stmt = select(Collection).where(*_payable_filter(user.cooperative_id))
    if collection_ids:
        stmt = stmt.where(Collection.id.in_(collection_ids))
    if producer_ids:
        stmt = stmt.where(Collection.producer_id.in_(producer_ids))
    cols = (await db.execute(stmt.with_for_update())).scalars().all()
    if not cols:
        raise ApiError(422, "nothing_to_pay", "Aucune collecte validée non payée dans la sélection")

    grouped: dict[str, list[Collection]] = defaultdict(list)
    for c in cols:
        grouped[c.producer_id].append(c)

    provider = get_provider()
    batch = PaymentBatch(cooperative_id=user.cooperative_id, reference_note=note, created_by=user.id)
    db.add(batch)
    await db.flush()

    payments, skipped = [], []
    for producer_id, items in grouped.items():
        producer: Producer = items[0].producer
        gross = sum(c.amount for c in items)
        if not producer.momo_account:
            skipped.append({"producer_id": producer_id, "reason": "Aucun compte mobile money renseigné"})
            continue
        deduction, allocations = await _reserve_advances(db, producer_id, gross)
        payment = Payment(
            cooperative_id=user.cooperative_id,
            batch_id=batch.id,
            producer_id=producer_id,
            gross_amount=gross,
            advance_deduction=deduction,
            amount=gross - deduction,
            advance_allocations=allocations,
            operator=producer.momo_operator,
            account=producer.momo_account,
            provider=provider.name if gross > deduction else "advance_offset",
        )
        db.add(payment)
        await db.flush()
        for c in items:
            c.payment_id = payment.id
        if payment.amount == 0:  # entirely recovered by advances: nothing to send
            await _mark_success(db, payment, external_ref=None)
        payments.append(payment)
        batch.total_amount += payment.amount
        batch.count += 1

    audit.record(
        db, cooperative_id=user.cooperative_id, actor_id=user.id, entity="payment_batch", entity_id=batch.id,
        action="created", changes={"count": batch.count, "total_amount": batch.total_amount},
    )
    for p in payments:
        await db.refresh(p, ["producer"])
    return batch, payments, skipped


async def _collections_of(db: AsyncSession, payment: Payment) -> list[Collection]:
    return (await db.execute(select(Collection).where(Collection.payment_id == payment.id))).scalars().all()


async def _mark_success(db: AsyncSession, payment: Payment, external_ref: str | None) -> None:
    if payment.status == "success":
        return
    payment.status = "success"
    payment.paid_at = utcnow()
    payment.failure_reason = None
    if external_ref:
        payment.external_ref = external_ref
    for c in await _collections_of(db, payment):
        c.status = "paid"
    producer = await db.get(Producer, payment.producer_id)
    if producer and producer.phone:
        parts = [f"Bonjour {producer.first_name}, votre paiement de {fcfa(payment.amount)} a été envoyé"]
        if payment.operator:
            parts[0] += f" sur {payment.operator.replace('_', ' ').title()}"
        if payment.advance_deduction:
            parts.append(f"Avance remboursée : {fcfa(payment.advance_deduction)}")
        await send_sms(db, producer.phone, ". ".join(parts) + ".", kind="payment", cooperative_id=payment.cooperative_id)


def _mark_failed(payment: Payment, reason: str | None) -> None:
    payment.status = "failed"
    payment.failure_reason = reason or "Échec du transfert"


async def apply_result(db: AsyncSession, payment: Payment, result: ProviderResult) -> None:
    if result.external_ref:
        payment.external_ref = result.external_ref
    if result.status == "success":
        await _mark_success(db, payment, result.external_ref)
    elif result.status == "failed":
        _mark_failed(payment, result.reason)
    else:
        payment.status = "processing"


async def dispatch(payment_ids: list[str]) -> None:
    """Runs after the HTTP response (BackgroundTasks). Uses its own session."""
    provider = get_provider()
    async with dbmod.SessionLocal() as db:
        for pid in payment_ids:
            payment = await db.get(Payment, pid)
            if not payment or payment.status not in ("initiated", "failed"):
                continue
            payment.attempts += 1
            payment.status = "processing"
            await db.commit()
            try:
                result = await provider.send(payment)
            except Exception as exc:  # never leave a payment stuck in "processing" because of a bug
                log.exception("provider crash for %s", pid)
                result = ProviderResult("failed", reason=f"Erreur interne : {exc.__class__.__name__}")
            await apply_result(db, payment, result)
            await db.commit()


async def handle_webhook(db: AsyncSession, payment_id: str | None, external_ref: str | None, status: str, reason: str | None, trans_id: str | None) -> Payment:
    payment = await db.get(Payment, payment_id) if payment_id else None
    if not payment and external_ref:
        payment = (await db.execute(select(Payment).where(Payment.external_ref == external_ref))).scalar_one_or_none()
    if not payment:
        raise not_found("Paiement")
    if payment.status == "success":
        return payment  # webhooks are retried by providers: idempotent
    # Keep the reference we matched on: providers retry callbacks and look the payment up by it again.
    await apply_result(db, payment, ProviderResult(status, external_ref=payment.external_ref or trans_id, reason=reason))
    audit.record(
        db, cooperative_id=payment.cooperative_id, actor_id=None, entity="payment", entity_id=payment.id,
        action=f"webhook_{status}", changes={"trans_id": trans_id, "reason": reason},
    )
    return payment


async def get_for(db: AsyncSession, user: User, payment_id: str) -> Payment:
    p = await db.get(Payment, payment_id)
    if not p or p.cooperative_id != user.cooperative_id:
        raise not_found("Paiement")
    return p


def prepare_retry(payment: Payment) -> None:
    if payment.status != "failed":
        raise ApiError(409, "invalid_transition", "Seul un paiement échoué peut être relancé")


async def cancel(db: AsyncSession, user: User, payment: Payment) -> None:
    """Give up on a failed payment: collections become payable again and reserved advances are released."""
    if payment.status != "failed":
        raise ApiError(409, "invalid_transition", "Seul un paiement échoué peut être annulé")
    for alloc in payment.advance_allocations:
        adv = await db.get(Advance, alloc["advance_id"])
        if adv:
            adv.remaining += alloc["amount"]
    for c in await _collections_of(db, payment):
        c.payment_id = None
    payment.status = "cancelled"
    audit.record(db, cooperative_id=payment.cooperative_id, actor_id=user.id, entity="payment", entity_id=payment.id, action="cancelled")
