"""Demo data for field validation meetings: `python -m app.seed --reset`.

Creates one cocoa cooperative near Daloa with 3 staff accounts, 40 producers and their parcels,
two weeks of collections (pending / validated / paid), advances, a sealed lot and payments.
Deterministic: the same command always produces the same cooperative.
"""

import argparse
import asyncio
import math
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from . import db as dbmod
from .core import geo
from .core.timeutil import utcnow
from .models import Advance, Base, Collection, Cooperative, Parcel, Producer, PurchasePrice, User, Zone
from .schemas import CollectionIn, GpsIn
from .services import collections as collection_service
from .services import issues as issue_service
from .services import lots as lot_service
from .services import payments as payment_service

DEMO_USERS = [
    ("Aïcha Traoré", "+2250700000001", "super_admin"),
    ("Konan Yao", "+2250700000002", "collector"),
    ("Mariam Ouattara", "+2250700000003", "collector"),
]
ZONES = {"Gonaté": (6.93, -6.38), "Gboguhé": (6.80, -6.55), "Zaïbo": (6.97, -6.55), "Bédiala": (6.98, -6.30)}
FIRST = ["Amadou", "Brigitte", "Kouadio", "Adjoua", "Yao", "Aya", "Koffi", "Affoué", "Sékou", "Mariam", "Bamba",
         "Akissi", "Didier", "Fatou", "Hervé", "Rachelle", "Issouf", "Clarisse", "Ange", "Nadège"]
LAST = ["Koffi", "Yao", "Kouassi", "Konan", "N'Guessan", "Kouamé", "Bamba", "Coulibaly", "Ouattara", "Traoré",
        "Gbagbo", "Zadi", "Gnahoré", "Tapé", "Dosso", "Koné", "Aké", "Bléhoué", "Djédjé", "Séri"]
OPERATORS = ["orange_money", "mtn_momo", "wave", "moov_money"]
OPERATOR_PREFIX = {"orange_money": "07", "mtn_momo": "05", "wave": "07", "moov_money": "01"}


def _polygon_around(lat: float, lng: float, hectares: float, rnd: random.Random) -> dict:
    """An irregular quadrilateral of roughly `hectares`, like a parcel walked with a GPS."""
    side_m = math.sqrt(hectares * 10_000)
    dlat = side_m / 111_320
    dlng = side_m / (111_320 * math.cos(math.radians(lat)))
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]
    ring = [[round(lng + (x + rnd.uniform(-0.12, 0.12)) * dlng, 6), round(lat + (y + rnd.uniform(-0.12, 0.12)) * dlat, 6)] for x, y in corners]
    return geo.validate_geometry({"type": "Polygon", "coordinates": [ring]})


async def seed(reset: bool) -> None:
    if reset:
        async with dbmod.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    async with dbmod.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    rnd = random.Random(2026)
    now = utcnow()
    async with dbmod.SessionLocal() as db:
        if (await db.execute(select(Cooperative).where(Cooperative.code == "DAL"))).scalar_one_or_none():
            print("Demo cooperative already present (use --reset to rebuild).")
            return

        coop = Cooperative(name="Coopérative Espoir de Daloa (démo)", code="DAL", region="Haut-Sassandra",
                           phone="+2250700000001", max_moisture_percent=Decimal("8.0"), max_weight_kg=Decimal("1000"))
        db.add(coop)
        await db.flush()
        users = [User(cooperative_id=coop.id, name=n, phone=p, role=r) for n, p, r in DEMO_USERS]
        db.add_all(users)
        zones = {name: Zone(cooperative_id=coop.id, name=name) for name in ZONES}
        db.add_all(zones.values())

        campaign_start = date(now.year if now.month >= 10 else now.year - 1, 10, 1)
        db.add_all([
            PurchasePrice(cooperative_id=coop.id, product="cacao", quality="A", price_per_kg=2200,
                          effective_from=campaign_start - timedelta(days=183), effective_to=campaign_start - timedelta(days=1)),
            PurchasePrice(cooperative_id=coop.id, product="cacao", quality="B", price_per_kg=2100,
                          effective_from=campaign_start - timedelta(days=183), effective_to=campaign_start - timedelta(days=1)),
            PurchasePrice(cooperative_id=coop.id, product="cacao", quality="A", price_per_kg=2800, effective_from=campaign_start),
            PurchasePrice(cooperative_id=coop.id, product="cacao", quality="B", price_per_kg=2700, effective_from=campaign_start),
        ])
        await db.flush()

        producers = []
        for i in range(40):
            zone_name = list(ZONES)[i % len(ZONES)]
            lat0, lng0 = ZONES[zone_name]
            op = rnd.choice(OPERATORS)
            phone = f"+225{OPERATOR_PREFIX[op]}{rnd.randint(10_000_000, 99_999_999)}"
            p = Producer(
                cooperative_id=coop.id, code=f"DAL-{i + 1:05d}", first_name=rnd.choice(FIRST), last_name=LAST[i % len(LAST)],
                phone=phone, gender=rnd.choice("MMMF"), birth_year=rnd.randint(1958, 1998), zone_id=zones[zone_name].id,
                membership_date=date(rnd.randint(2012, 2025), rnd.randint(1, 12), 1),
                momo_operator=op if i % 9 else None, momo_account=phone if i % 9 else None,
            )
            producers.append(p)
            db.add(p)
            await db.flush()
            lat, lng = lat0 + rnd.uniform(-0.06, 0.06), lng0 + rnd.uniform(-0.06, 0.06)
            hectares = round(rnd.uniform(1.2, 7.5), 1)
            kind = "polygon" if i % 10 < 7 else ("point" if i % 10 < 9 else "none")
            if kind != "none":
                geometry = _polygon_around(lat, lng, hectares, rnd) if kind == "polygon" else {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]}
                measured = geo.polygon_area_ha(geometry)
                db.add(Parcel(cooperative_id=coop.id, producer_id=p.id, crop="cacao", area_hectares=Decimal(str(hectares)),
                              measured_area_hectares=Decimal(str(measured)) if measured else None, geometry=geometry,
                              planted_year=rnd.randint(1995, 2018), deforestation_status="clear" if i % 6 else "unchecked"))
        coop.producer_seq = len(producers)
        await db.commit()

        admin, collectors = users[0], users[1:]
        await db.refresh(admin, ["cooperative"])
        for c in collectors:
            await db.refresh(c, ["cooperative"])

        # Two weeks of deliveries
        n = 0
        for days_ago in range(13, -1, -1):
            for _ in range(rnd.randint(6, 14)):
                n += 1
                prod = rnd.choice(producers)
                collector = rnd.choice(collectors)
                at = (now - timedelta(days=days_ago)).replace(hour=rnd.randint(7, 16), minute=rnd.randint(0, 59))
                if at > now:
                    at = now - timedelta(minutes=rnd.randint(5, 90))
                lat0, lng0 = ZONES[next(z for z, zz in zones.items() if zz.id == prod.zone_id)]
                body = CollectionIn(
                    client_uuid=f"seed-{n:05d}-{rnd.getrandbits(32):08x}", producer_id=prod.id, collected_at=at, product="cacao",
                    quality="A" if rnd.random() < 0.8 else "B", weight_kg=Decimal(rnd.randint(35, 260)),
                    moisture_percent=Decimal(str(round(rnd.uniform(5.4, 7.9), 1))),
                    gps=GpsIn(lat=lat0 + rnd.uniform(-0.05, 0.05), lng=lng0 + rnd.uniform(-0.05, 0.05)),
                )
                c, _ = await collection_service.ingest(db, collector, body, source="offline_mobile", device_id=f"demo-{collector.phone[-4:]}")
                if days_ago >= 2:
                    collection_service.validate(db, admin, c)
        await db.commit()

        for p in producers[:5]:
            amount = rnd.choice([50_000, 75_000, 100_000])
            db.add(Advance(cooperative_id=coop.id, producer_id=p.id, amount=amount, remaining=amount,
                           reason="Avance pré-récolte", given_at=(now - timedelta(days=40)).date(), created_by=admin.id))
        await db.commit()

        # A sealed lot made of the oldest validated deliveries
        old = (
            await db.execute(
                select(Collection.id).where(Collection.cooperative_id == coop.id, Collection.status == "validated",
                                            Collection.collected_at < now - timedelta(days=8)).order_by(Collection.collected_at)
            )
        ).scalars().all()
        lot = await lot_service.create(db, admin, "cacao", None, "Premier lot de la campagne")
        await lot_service.add_collections(db, admin, lot, list(old))
        lot_service.seal(db, admin, lot, bags_count=max(1, int(lot.total_weight_kg // 65)))
        await lot_service.create(db, admin, "cacao", "A", "Lot en constitution")
        await db.commit()

        # Pay the producers of the first week
        week1 = (
            await db.execute(
                select(Collection.producer_id).where(Collection.cooperative_id == coop.id, Collection.status == "validated",
                                                     Collection.collected_at < now - timedelta(days=7)).distinct()
            )
        ).scalars().all()
        _, payments, _ = await payment_service.create_batch(db, admin, list(week1)[:15], [], "Paiement semaine 1 (démo)")
        await db.commit()
        await payment_service.dispatch([p.id for p in payments if p.status == "initiated"])

        # Two reports in the inbox: a producer disputing a weight by USSD, a collector with a sync problem
        disputed = producers[3]
        last = (
            await db.execute(select(Collection).where(Collection.producer_id == disputed.id).order_by(Collection.collected_at.desc()))
        ).scalars().first()
        await issue_service.create(
            db, cooperative_id=coop.id, source="ussd", category="data_error", message="Poids ou montant conteste par le producteur",
            reporter_name=disputed.full_name, reporter_phone=disputed.phone, producer_id=disputed.id,
            collection_id=last.id if last else None,
        )
        await issue_service.create(
            db, cooperative_id=coop.id, source="mobile", category="sync", reporter=collectors[0],
            message="Hier soir à Gonaté les collectes restaient « en attente d'envoi » malgré le réseau 3G.",
            context={"app": "mobile", "app_version": "0.1.0", "pending_collections": 6, "last_sync_error": "Le serveur ne répond pas"},
        )
        await db.commit()

        print(f"Seeded {coop.name}: {len(producers)} producers, {n} collections, lot {lot.reference}.")
        print("Log in on the web app with +2250700000001 (admin) or on the phone with +2250700000002 (collector).")
        print(f"Public trace page: {lot_service.to_out(lot).trace_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    asyncio.run(seed(parser.parse_args().reset))


if __name__ == "__main__":
    main()
