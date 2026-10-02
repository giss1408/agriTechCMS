from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..models import PurchasePrice


async def price_on(db: AsyncSession, cooperative_id: str, product: str, quality: str, day: date) -> PurchasePrice:
    stmt = (
        select(PurchasePrice)
        .where(
            PurchasePrice.cooperative_id == cooperative_id,
            PurchasePrice.product == product,
            PurchasePrice.quality == quality,
            PurchasePrice.effective_from <= day,
            or_(PurchasePrice.effective_to.is_(None), PurchasePrice.effective_to >= day),
        )
        .order_by(PurchasePrice.effective_from.desc())
        .limit(1)
    )
    price = (await db.execute(stmt)).scalar_one_or_none()
    if price is None:
        raise ApiError(
            422, "no_price", f"Aucun prix d'achat défini pour {product} qualité {quality} au {day:%d/%m/%Y}"
        )
    return price


async def prices_in_force(db: AsyncSession, cooperative_id: str, day: date) -> list[PurchasePrice]:
    stmt = (
        select(PurchasePrice)
        .where(
            PurchasePrice.cooperative_id == cooperative_id,
            PurchasePrice.effective_from <= day,
            or_(PurchasePrice.effective_to.is_(None), PurchasePrice.effective_to >= day),
        )
        .order_by(PurchasePrice.product, PurchasePrice.quality, PurchasePrice.effective_from.desc())
    )
    latest: dict[tuple[str, str], PurchasePrice] = {}
    for p in (await db.execute(stmt)).scalars():
        latest.setdefault((p.product, p.quality), p)
    return list(latest.values())


def amount_for(weight_kg: Decimal, unit_price: int) -> int:
    return int((weight_kg * unit_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
