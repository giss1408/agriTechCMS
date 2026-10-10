"""Problem reports ("signalements"). One inbox per cooperative, whatever the channel."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError, not_found
from ..core.timeutil import utcnow
from ..models import Collection, Cooperative, Issue, Lot, Producer, User
from ..schemas import IssueOut
from . import audit
from .sms import send_sms

CATEGORY_LABEL = {
    "app_bug": "problème d'application",
    "sync": "synchronisation",
    "data_error": "erreur de données",
    "payment": "paiement",
    "account": "compte",
    "other": "autre",
}


async def _next_reference(db: AsyncSession, cooperative_id: str) -> str:
    coop = await db.get(Cooperative, cooperative_id)
    coop.issue_seq += 1
    return f"SIG-{coop.issue_seq:04d}"


async def _check_link(db: AsyncSession, model, obj_id: str | None, cooperative_id: str, label: str) -> None:
    if obj_id:
        obj = await db.get(model, obj_id)
        if not obj or obj.cooperative_id != cooperative_id:
            raise ApiError(422, "unknown_reference", f"{label} introuvable dans cette coopérative")


async def create(
    db: AsyncSession,
    *,
    cooperative_id: str,
    source: str,
    category: str,
    message: str,
    reporter: User | None = None,
    reporter_name: str | None = None,
    reporter_phone: str | None = None,
    client_uuid: str | None = None,
    collection_id: str | None = None,
    producer_id: str | None = None,
    lot_id: str | None = None,
    context: dict | None = None,
) -> tuple[Issue, bool]:
    """Returns (issue, created). Idempotent on `client_uuid` (the phone retries its offline queue)."""
    if client_uuid:
        existing = (
            await db.execute(select(Issue).where(Issue.cooperative_id == cooperative_id, Issue.client_uuid == client_uuid))
        ).scalar_one_or_none()
        if existing:
            return existing, False
    await _check_link(db, Collection, collection_id, cooperative_id, "Collecte")
    await _check_link(db, Producer, producer_id, cooperative_id, "Producteur")
    await _check_link(db, Lot, lot_id, cooperative_id, "Lot")
    if collection_id and not producer_id:
        producer_id = (await db.get(Collection, collection_id)).producer_id

    issue = Issue(
        cooperative_id=cooperative_id,
        client_uuid=client_uuid,
        reference=await _next_reference(db, cooperative_id),
        source=source,
        category=category,
        message=message.strip(),
        reporter_id=reporter.id if reporter else None,
        reporter_name=reporter.name if reporter else reporter_name,
        reporter_phone=reporter.phone if reporter else reporter_phone,
        collection_id=collection_id,
        producer_id=producer_id,
        lot_id=lot_id,
        context=context or {},
    )
    db.add(issue)
    await db.flush()
    audit.record(
        db, cooperative_id=cooperative_id, actor_id=reporter.id if reporter else None, entity="issue",
        entity_id=issue.id, action="reported", changes={"source": source, "category": category},
    )
    return issue, True


async def to_out(db: AsyncSession, issue: Issue) -> IssueOut:
    out = IssueOut.model_validate(issue)
    if issue.collection_id:
        c = await db.get(Collection, issue.collection_id)
        out.collection_reference = c.reference if c else None
    if issue.producer_id:
        p = await db.get(Producer, issue.producer_id)
        out.producer_name = p.full_name if p else None
    if issue.lot_id:
        lot = await db.get(Lot, issue.lot_id)
        out.lot_reference = lot.reference if lot else None
    return out


async def get_for(db: AsyncSession, user: User, issue_id: str) -> Issue:
    issue = await db.get(Issue, issue_id)
    if not issue or issue.cooperative_id != user.cooperative_id:
        raise not_found("Signalement")
    if user.role == "collector" and issue.reporter_id != user.id:
        raise not_found("Signalement")
    return issue


async def update(db: AsyncSession, user: User, issue: Issue, status: str | None, note: str | None) -> None:
    changes = audit.diff(issue, {k: v for k, v in {"status": status, "resolution_note": note}.items() if v is not None})
    if note is not None:
        issue.resolution_note = note
    if status and status != issue.status:
        issue.status = status
        if status == "resolved":
            issue.resolved_by = user.id
            issue.resolved_at = utcnow()
            await _tell_reporter(db, issue)
        else:
            issue.resolved_by = None
            issue.resolved_at = None
    audit.record(db, cooperative_id=issue.cooperative_id, actor_id=user.id, entity="issue", entity_id=issue.id, action="updated", changes=changes)


async def _tell_reporter(db: AsyncSession, issue: Issue) -> None:
    """Producers who reported by USSD have no app: they hear back by SMS."""
    if issue.source != "ussd" or not issue.reporter_phone:
        return
    body = f"Votre signalement {issue.reference} a été traité par la coopérative."
    if issue.resolution_note:
        body += f" {issue.resolution_note[:110]}"
    await send_sms(db, issue.reporter_phone, body, kind="info", cooperative_id=issue.cooperative_id)
