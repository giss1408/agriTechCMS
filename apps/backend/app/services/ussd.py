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
from . import issues as issue_service
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
    steps = (text or "").split("*") if text else []
    choice = steps[-1] if steps else ""

    if steps[:1] == ["4"]:
        return await _report(db, producer, steps[1:])

    if choice == "":
        return (
            f"CON {coop.name[:40]}\n"
            f"Bonjour {producer.first_name}\n"
            "1. Mon solde\n2. Mes dernieres livraisons\n3. Prix du jour\n4. Signaler un probleme"
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


USSD_ISSUES = {
    "1": ("data_error", "Poids ou montant conteste par le producteur"),
    "2": ("payment", "Paiement non recu selon le producteur"),
    "3": ("other", "Demande de rappel du producteur"),
}


async def _report(db: AsyncSession, producer: Producer, steps: list[str]) -> str:
    """4 -> choose the problem -> recorded; the cooperative calls back, and an SMS confirms resolution."""
    if not steps:
        return "CON Quel probleme ?\n1. Poids ou montant faux\n2. Paiement non recu\n3. Autre (etre rappele)"
    if steps[0] not in USSD_ISSUES:
        return "END Choix invalide."
    category, message = USSD_ISSUES[steps[0]]
    last = (
        await db.execute(
            select(Collection).where(Collection.producer_id == producer.id).order_by(Collection.collected_at.desc()).limit(1)
        )
    ).scalars().first()
    issue, _ = await issue_service.create(
        db, cooperative_id=producer.cooperative_id, source="ussd", category=category, message=message,
        reporter_name=producer.full_name, reporter_phone=producer.phone, producer_id=producer.id,
        collection_id=last.id if last and category == "data_error" else None,
    )
    await db.commit()
    return f"END Signalement {issue.reference} enregistre. La cooperative va vous rappeler."
