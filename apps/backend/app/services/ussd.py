"""Producer self-service over USSD (works on any phone, no data plan).

Follows the common aggregator convention (Africa's Talking and others): each request carries the whole
input so far as `text` ("", "1", "2*1"…); we answer "CON …" to keep the session open or "END …" to close it.
Screens stay under ~160 characters and avoid characters outside the GSM alphabet.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.phone import normalize_phone
from ..core.timeutil import campaign_of, utcnow
from ..models import Collection, Cooperative, Producer
from .balances import producer_balance
from .pricing import prices_in_force


def _n(amount: int | float) -> str:
    return f"{int(amount):,}".replace(",", " ")


async def handle(db: AsyncSession, phone_raw: str, text: str) -> str:
    try:
        phone = normalize_phone(phone_raw)
    except ApiError:
        return "END Numero non reconnu."
    producer = (
        await db.execute(
            select(Producer).where(Producer.phone == phone, Producer.status == "active").order_by(Producer.created_at)
        )
    ).scalars().first()
    if not producer:
        return "END Ce numero n'est inscrit dans aucune cooperative. Contactez votre cooperative."
    coop = await db.get(Cooperative, producer.cooperative_id)
    choice = (text or "").split("*")[-1] if text else ""

    if choice == "":
        return (
            f"CON {coop.name[:40]}\n"
            f"Bonjour {producer.first_name}\n"
            "1. Mon solde\n2. Mes dernieres livraisons\n3. Prix du jour"
        )
    if choice == "1":
        campaign = campaign_of(utcnow().date(), coop.campaign_start_month)
        b = await producer_balance(db, producer, campaign, coop.campaign_start_month)
        lines = [
            f"END Campagne {campaign}",
            f"Livre: {_n(b.total_delivered_kg)} kg",
            f"Gagne: {_n(b.total_earned)} F",
            f"Paye: {_n(b.total_paid)} F",
            f"Reste a payer: {_n(b.balance_due)} F",
        ]
        if b.outstanding_advances:
            lines.append(f"Avance due: {_n(b.outstanding_advances)} F")
        if b.pending_validation_amount:
            lines.append(f"En verification: {_n(b.pending_validation_amount)} F")
        return "\n".join(lines)
    if choice == "2":
        rows = (
            await db.execute(
                select(Collection)
                .where(Collection.producer_id == producer.id, Collection.status != "cancelled")
                .order_by(Collection.collected_at.desc())
                .limit(3)
            )
        ).scalars().all()
        if not rows:
            return "END Aucune livraison enregistree."
        label = {"pending_validation": "en verif.", "validated": "a payer", "paid": "paye", "rejected": "refuse"}
        body = [f"{c.collected_at:%d/%m} {_n(c.weight_kg)}kg {c.quality} {_n(c.amount)}F {label.get(c.status, '')}" for c in rows]
        return "END " + "\n".join(body)
    if choice == "3":
        prices = await prices_in_force(db, coop.id, utcnow().date())
        if not prices:
            return "END Prix non encore publies."
        return "END Prix du jour:\n" + "\n".join(f"{p.product} {p.quality}: {_n(p.price_per_kg)} F/kg" for p in prices)
    return "END Choix invalide."
