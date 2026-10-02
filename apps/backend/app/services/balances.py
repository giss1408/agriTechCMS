from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.timeutil import campaign_bounds
from ..models import Advance, Collection, Producer
from ..schemas import BalanceOut


async def outstanding_advances(db: AsyncSession, producer_id: str) -> int:
    stmt = select(func.coalesce(func.sum(Advance.remaining), 0)).where(Advance.producer_id == producer_id)
    return int((await db.execute(stmt)).scalar_one())


async def producer_balance(db: AsyncSession, producer: Producer, campaign: str, start_month: int) -> BalanceOut:
    start, end = campaign_bounds(campaign, start_month)
    in_campaign = (
        Collection.producer_id == producer.id,
        Collection.collected_at >= start,
        Collection.collected_at < end,
    )

    async def total(*conds, col=Collection.amount):
        stmt = select(func.coalesce(func.sum(col), 0)).where(*in_campaign, *conds)
        return (await db.execute(stmt)).scalar_one()

    earned_statuses = Collection.status.in_(("validated", "paid"))
    delivered = Decimal(str(await total(earned_statuses, col=Collection.weight_kg)))
    earned = int(await total(earned_statuses))
    paid = int(await total(Collection.status == "paid"))
    pending = int(await total(Collection.status == "pending_validation"))
    last = (
        await db.execute(select(func.max(Collection.collected_at)).where(*in_campaign, Collection.status != "cancelled"))
    ).scalar_one()
    advances = await outstanding_advances(db, producer.id)
    due = earned - paid
    return BalanceOut(
        producer_id=producer.id,
        campaign=campaign,
        total_delivered_kg=delivered,
        total_earned=earned,
        total_paid=paid,
        balance_due=due,
        outstanding_advances=advances,
        net_payable=max(0, due - advances),
        pending_validation_amount=pending,
        last_delivery=_as_date(last),
    )


def _as_date(value) -> date | None:
    if value is None:
        return None
    return value.date() if hasattr(value, "date") else date.fromisoformat(str(value)[:10])
