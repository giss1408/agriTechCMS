import os

os.environ["AGT_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AGT_ENV"] = "test"
os.environ["AGT_UPLOAD_DIR"] = "/tmp/agritech-test-uploads"

from datetime import date
from decimal import Decimal

import httpx
import pytest

from app import db as dbmod
from app.core.security import create_access_token
from app.main import app
from app.models import Base, Cooperative, Producer, PurchasePrice, User, Zone


@pytest.fixture(autouse=True)
async def schema():
    async with dbmod.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def session():
    async with dbmod.SessionLocal() as s:
        yield s


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/v1") as c:
        yield c


class World:
    """A cooperative with an admin, a collector, two producers and cocoa prices."""

    coop: Cooperative
    admin: User
    collector: User
    koffi: Producer
    yao: Producer

    def headers(self, user: User) -> dict:
        token, _ = create_access_token(user.id, user.cooperative_id, user.role)
        return {"Authorization": f"Bearer {token}"}

    @property
    def admin_h(self):
        return self.headers(self.admin)

    @property
    def collector_h(self):
        return self.headers(self.collector)


async def build_world(session, code="DAL", phone_suffix="1") -> World:
    w = World()
    w.coop = Cooperative(name=f"Coop {code}", code=code, region="Haut-Sassandra", max_moisture_percent=Decimal("8.0"), max_weight_kg=Decimal("1000"))
    session.add(w.coop)
    await session.flush()
    zone = Zone(cooperative_id=w.coop.id, name="Gonaté")
    session.add(zone)
    w.admin = User(cooperative_id=w.coop.id, name="Awa Admin", phone=f"+22507000000{phone_suffix}1", role="admin")
    w.collector = User(cooperative_id=w.coop.id, name="Konan Collecteur", phone=f"+22507000000{phone_suffix}2", role="collector")
    session.add_all([w.admin, w.collector])
    await session.flush()
    w.koffi = Producer(cooperative_id=w.coop.id, code=f"{code}-00001", first_name="Amadou", last_name="Koffi",
                       phone=f"+22501000000{phone_suffix}1", momo_operator="orange_money", momo_account=f"+22507111111{phone_suffix}1", zone_id=zone.id)
    w.yao = Producer(cooperative_id=w.coop.id, code=f"{code}-00002", first_name="Brigitte", last_name="Yao",
                     phone=f"+22501000000{phone_suffix}2", momo_operator="mtn_momo", momo_account=f"+22505222222{phone_suffix}2")
    session.add_all([w.koffi, w.yao])
    session.add_all([
        PurchasePrice(cooperative_id=w.coop.id, product="cacao", quality="A", price_per_kg=2200, effective_from=date(2026, 4, 1), effective_to=date(2026, 9, 30)),
        PurchasePrice(cooperative_id=w.coop.id, product="cacao", quality="A", price_per_kg=2800, effective_from=date(2026, 10, 1)),
        PurchasePrice(cooperative_id=w.coop.id, product="cacao", quality="B", price_per_kg=2700, effective_from=date(2026, 10, 1)),
    ])
    w.coop.producer_seq = 2
    await session.commit()
    return w


@pytest.fixture
async def world(session) -> World:
    return await build_world(session)
