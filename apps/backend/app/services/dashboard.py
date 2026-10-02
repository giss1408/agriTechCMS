from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.timeutil import campaign_bounds, campaign_of, utcnow
from ..models import Collection, Cooperative, Lot, Parcel, Payment, Producer, SyncDevice, User


def _day_start(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


async def summary(db: AsyncSession, coop: Cooperative) -> dict:
    now = utcnow()
    today = _day_start(now)
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)
    campaign = campaign_of(now.date(), coop.campaign_start_month)
    c_start, c_end = campaign_bounds(campaign, coop.campaign_start_month)
    mine = Collection.cooperative_id == coop.id
    live = Collection.status.not_in(("rejected", "cancelled"))

    async def scalar(stmt):
        return (await db.execute(stmt)).scalar_one()

    today_row = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(Collection.weight_kg), 0), func.coalesce(func.sum(Collection.amount), 0))
            .where(mine, live, Collection.collected_at >= today)
        )
    ).one()
    campaign_row = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(Collection.weight_kg), 0), func.coalesce(func.sum(Collection.amount), 0))
            .where(mine, live, Collection.collected_at >= c_start, Collection.collected_at < c_end)
        )
    ).one()
    to_pay = await scalar(
        select(func.coalesce(func.sum(Collection.amount), 0)).where(mine, Collection.status == "validated", Collection.payment_id.is_(None))
    )
    pending = await scalar(select(func.count()).where(mine, Collection.status == "pending_validation"))
    stale_pending = await scalar(
        select(func.count()).where(mine, Collection.status == "pending_validation", Collection.created_at < now - timedelta(hours=48))
    )
    failed_payments = await scalar(select(func.count()).where(Payment.cooperative_id == coop.id, Payment.status == "failed"))
    near_threshold = await scalar(
        select(func.count()).where(
            mine, Collection.collected_at >= week_start, Collection.moisture_percent >= coop.max_moisture_percent - Decimal("0.5")
        )
    )
    producers_total = await scalar(select(func.count()).where(Producer.cooperative_id == coop.id, Producer.status == "active"))
    with_parcel = await scalar(
        select(func.count(func.distinct(Parcel.producer_id))).where(Parcel.cooperative_id == coop.id, Parcel.geometry.is_not(None))
    )
    silent_devices = await scalar(
        select(func.count()).where(
            SyncDevice.cooperative_id == coop.id,
            SyncDevice.last_push_at < now - timedelta(days=3),
        )
    )
    open_lots = await scalar(select(func.count()).where(Lot.cooperative_id == coop.id, Lot.status == "open"))

    day_col = func.date(Collection.collected_at)
    series_rows = (
        await db.execute(
            select(day_col, func.count(), func.coalesce(func.sum(Collection.weight_kg), 0))
            .where(mine, live, Collection.collected_at >= week_start)
            .group_by(day_col)
        )
    ).all()
    by_day = {str(d): (n, w) for d, n, w in series_rows}
    series = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).date().isoformat()
        n, w = by_day.get(d, (0, 0))
        series.append({"date": d, "count": n, "weight_kg": float(w)})

    top = (
        await db.execute(
            select(User.id, User.name, func.count(Collection.id), func.coalesce(func.sum(Collection.weight_kg), 0))
            .join(Collection, Collection.collector_id == User.id)
            .where(mine, live, Collection.collected_at >= month_start)
            .group_by(User.id, User.name)
            .order_by(func.count(Collection.id).desc())
            .limit(5)
        )
    ).all()

    alerts = []
    if stale_pending:
        alerts.append({"level": "warning", "code": "stale_pending", "count": stale_pending,
                       "message": f"{stale_pending} collecte(s) en attente de validation depuis plus de 48 h", "link": "/collections?status=pending_validation"})
    if failed_payments:
        alerts.append({"level": "danger", "code": "failed_payments", "count": failed_payments,
                       "message": f"{failed_payments} paiement(s) échoué(s) à relancer", "link": "/payments?status=failed"})
    if near_threshold:
        alerts.append({"level": "info", "code": "moisture_near_threshold", "count": near_threshold,
                       "message": f"{near_threshold} livraison(s) cette semaine proches du seuil d'humidité ({coop.max_moisture_percent} %)", "link": "/collections"})
    if producers_total and with_parcel < producers_total:
        missing = producers_total - with_parcel
        alerts.append({"level": "warning", "code": "parcels_missing", "count": missing,
                       "message": f"{missing} producteur(s) sans parcelle géolocalisée (bloquant pour l'EUDR)", "link": "/producers?missing_parcel=1"})
    if silent_devices:
        alerts.append({"level": "warning", "code": "silent_devices", "count": silent_devices,
                       "message": f"{silent_devices} téléphone(s) collecteur non synchronisé(s) depuis 3 jours", "link": "/settings"})

    return {
        "campaign": campaign,
        "today": {"count": today_row[0], "weight_kg": float(today_row[1]), "amount": int(today_row[2])},
        "campaign_totals": {"count": campaign_row[0], "weight_kg": float(campaign_row[1]), "amount": int(campaign_row[2])},
        "amount_to_pay": int(to_pay),
        "pending_validation": pending,
        "open_lots": open_lots,
        "producers": {"active": producers_total, "geolocated": with_parcel},
        "series_7d": series,
        "top_collectors": [{"id": i, "name": n, "count": c, "weight_kg": float(w)} for i, n, c, w in top],
        "alerts": alerts,
    }
