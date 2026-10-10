from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import current_user, is_admin, page_params, require_admin, require_staff
from ..core.envelope import Envelope, Meta, Page, ok
from ..core.errors import ApiError, not_found
from ..db import get_db
from ..models import Issue, Lot, User
from ..schemas import IssueIn, IssueOut, IssuePatch, PublicIssueIn
from ..services import issues as svc

router = APIRouter(tags=["problem reports"])

# A public link must not become a spam channel: cap open buyer reports per lot.
MAX_OPEN_PUBLIC_PER_LOT = 5


@router.post("/issues", response_model=Envelope[IssueOut], status_code=201)
async def report(
    body: IssueIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
    x_device_id: str | None = Header(default=None),
):
    """Report a problem from the web app or the collector app (identified by `X-Device-Id`).
    Idempotent on `client_uuid`."""
    issue, created = await svc.create(
        db,
        cooperative_id=user.cooperative_id,
        source="mobile" if x_device_id else "web",
        category=body.category,
        message=body.message,
        reporter=user,
        client_uuid=body.client_uuid,
        collection_id=body.collection_id,
        producer_id=body.producer_id,
        lot_id=body.lot_id,
        context=body.context,
    )
    await db.commit()
    payload = ok(await svc.to_out(db, issue))
    if not created:
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"), headers={"X-Duplicate": "true"})
    return payload


@router.get("/issues", response_model=Envelope[list[IssueOut]])
async def list_issues(
    status: str | None = Query(None, pattern="^(open|in_progress|resolved|unresolved)$"),
    source: str | None = Query(None, pattern="^(web|mobile|ussd|public)$"),
    page: Page = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    conds = [Issue.cooperative_id == user.cooperative_id]
    if not is_admin(user):
        conds.append(Issue.reporter_id == user.id)
    if status == "unresolved":
        conds.append(Issue.status != "resolved")
    elif status:
        conds.append(Issue.status == status)
    if source:
        conds.append(Issue.source == source)
    total = (await db.execute(select(func.count()).where(*conds))).scalar_one()
    rows = (await db.execute(select(Issue).where(*conds).order_by(Issue.created_at.desc()).offset(page.offset).limit(page.per_page))).scalars()
    return ok([await svc.to_out(db, i) for i in rows], Meta(page=page.page, per_page=page.per_page, total=total))


@router.get("/issues/{issue_id}", response_model=Envelope[IssueOut])
async def get_issue(issue_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    return ok(await svc.to_out(db, await svc.get_for(db, user, issue_id)))


@router.patch("/issues/{issue_id}", response_model=Envelope[IssueOut])
async def update_issue(issue_id: str, body: IssuePatch, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)):
    issue = await svc.get_for(db, user, issue_id)
    await svc.update(db, user, issue, body.status, body.resolution_note)
    await db.commit()
    return ok(await svc.to_out(db, issue))


@router.post("/public/trace/{token}/issues", response_model=Envelope[dict], status_code=201, tags=["public"])
async def report_on_lot(token: str, body: PublicIssueIn, db: AsyncSession = Depends(get_db)):
    """A buyer flags an inconsistency on a lot from the public trace page (no login)."""
    lot = (await db.execute(select(Lot).where(Lot.trace_token == token))).scalar_one_or_none()
    if not lot:
        raise not_found("Lot")
    open_count = (
        await db.execute(select(func.count()).where(Issue.lot_id == lot.id, Issue.source == "public", Issue.status != "resolved"))
    ).scalar_one()
    if open_count >= MAX_OPEN_PUBLIC_PER_LOT:
        raise ApiError(429, "too_many_reports", "Plusieurs signalements sont déjà en cours sur ce lot. La coopérative va les traiter.")
    issue, _ = await svc.create(
        db, cooperative_id=lot.cooperative_id, source="public", category=body.category, message=body.message,
        reporter_name=body.contact, lot_id=lot.id,
    )
    await db.commit()
    return ok({"reference": issue.reference, "message": "Merci. La coopérative a reçu votre signalement."})
