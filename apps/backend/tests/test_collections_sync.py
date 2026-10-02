from datetime import timedelta

from app.core.timeutil import utcnow


def collection(world, uuid="clt-0001-aaaa", **over):
    body = {
        "client_uuid": uuid,
        "producer_id": world.koffi.id,
        "collected_at": utcnow().isoformat(),
        "product": "cacao",
        "quality": "A",
        "weight_kg": "120.5",
        "moisture_percent": "6.5",
        "gps": {"lat": 6.88, "lng": -6.45},
    }
    body.update(over)
    return body


async def test_server_computes_amount_from_dated_price(client, world):
    r = await client.post("/collections", json=collection(world), headers=world.collector_h)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["unit_price"] == 2800
    assert data["amount"] == 337400  # 120.5 kg x 2800
    assert data["status"] == "pending_validation"
    assert data["reference"].startswith("COL-")


async def test_old_collection_uses_old_price(client, world):
    # Recorded during the previous campaign, synced today: valued at the price of its collection date.
    when = utcnow().replace(year=2026, month=9, day=15, hour=9)
    r = await client.post("/collections", json=collection(world, collected_at=when.isoformat()), headers=world.collector_h)
    assert r.json()["data"]["unit_price"] == 2200


async def test_replay_is_idempotent(client, world):
    first = await client.post("/collections", json=collection(world), headers=world.collector_h)
    again = await client.post("/collections", json=collection(world, weight_kg="999"), headers=world.collector_h)
    assert again.status_code == 200
    assert again.headers["x-duplicate"] == "true"
    assert again.json()["data"]["id"] == first.json()["data"]["id"]
    assert again.json()["data"]["weight_kg"] == "120.50"


async def test_business_rules(client, world):
    wet = await client.post("/collections", json=collection(world, "clt-wet-00001", moisture_percent="9.1"), headers=world.collector_h)
    assert wet.status_code == 422
    assert wet.json()["errors"][0]["code"] == "moisture_above_threshold"
    heavy = await client.post("/collections", json=collection(world, "clt-heavy-0001", weight_kg="1500"), headers=world.collector_h)
    assert heavy.json()["errors"][0]["code"] == "weight_above_max"
    no_price = await client.post("/collections", json=collection(world, "clt-noprice-01", quality="C"), headers=world.collector_h)
    assert no_price.json()["errors"][0]["code"] == "no_price"
    bad = await client.post("/collections", json=collection(world, "clt-bad-000001", weight_kg="-3"), headers=world.collector_h)
    assert bad.status_code == 400


async def test_sync_push_mixed_batch_and_clock_correction(client, world):
    # The phone clock is 3 hours behind the server.
    device_now = utcnow() - timedelta(hours=3)
    typed_at = device_now - timedelta(minutes=30)
    body = {
        "device_id": "device-abc-123",
        "device_time": device_now.isoformat(),
        "pending_on_device": 3,
        "collections": [
            collection(world, "clt-sync-0001", collected_at=typed_at.isoformat()),
            collection(world, "clt-sync-0002", collected_at=typed_at.isoformat(), moisture_percent="12"),
            collection(world, "clt-sync-0001", collected_at=typed_at.isoformat()),  # retried in the same batch
        ],
    }
    r = await client.post("/sync/push", json=body, headers=world.collector_h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert [a["duplicate"] for a in data["accepted"]] == [False, True]
    assert data["rejected"][0]["code"] == "moisture_above_threshold"
    assert abs(data["clock_offset_seconds"] - 3 * 3600) < 5

    stored = (await client.get(f"/collections/{data['accepted'][0]['id']}", headers=world.admin_h)).json()["data"]
    assert stored["clock_offset_seconds"] > 3 * 3600 - 5
    assert stored["sync_source"] == "offline_mobile"
    # corrected time ~ 30 minutes ago in server time
    from datetime import datetime

    corrected = datetime.fromisoformat(stored["collected_at"])
    assert abs((utcnow() - corrected) - timedelta(minutes=30)) < timedelta(seconds=10)

    devices = (await client.get("/sync/devices", headers=world.admin_h)).json()["data"]
    assert devices[0]["id"] == "device-abc-123"
    assert devices[0]["user_name"] == "Konan Collecteur"


async def test_sync_pull_full_then_incremental(client, world):
    full = (await client.get("/sync/pull", headers={**world.collector_h, "X-Device-Id": "device-abc-123"})).json()["data"]
    assert full["full"] is True
    assert {p["code"] for p in full["producers"]} == {"DAL-00001", "DAL-00002"}
    assert {(p["quality"], p["price_per_kg"]) for p in full["prices"]} >= {("A", 2800), ("B", 2700)}
    assert full["settings"]["campaign"]

    await client.patch(f"/producers/{world.yao.id}", json={"status": "inactive"}, headers=world.admin_h)
    inc = (await client.get("/sync/pull", params={"since": full["cursor"]}, headers=world.collector_h)).json()["data"]
    assert inc["full"] is False
    # the cursor is 30 s in the past (safety window), so recently created rows may come again: upserts are harmless
    assert ("DAL-00002", "inactive") in {(p["code"], p["status"]) for p in inc["producers"]}


async def test_collector_sees_only_own_collections(client, world, session):
    from app.models import User

    other = User(cooperative_id=world.coop.id, name="Autre", phone="+2250700000099", role="collector")
    session.add(other)
    await session.commit()
    await client.post("/collections", json=collection(world, "clt-mine-00001"), headers=world.collector_h)
    await client.post("/collections", json=collection(world, "clt-other-0001"), headers=world.headers(other))
    mine = (await client.get("/collections", headers=world.collector_h)).json()
    assert mine["meta"]["total"] == 1
    everything = (await client.get("/collections", headers=world.admin_h)).json()
    assert everything["meta"]["total"] == 2


async def test_admin_edit_is_audited_and_reprices(client, world):
    c = (await client.post("/collections", json=collection(world), headers=world.collector_h)).json()["data"]
    r = await client.patch(f"/collections/{c['id']}", json={"quality": "B", "reason": "Fèves plates au contrôle"}, headers=world.admin_h)
    assert r.json()["data"]["unit_price"] == 2700
    history = (await client.get(f"/collections/{c['id']}/history", headers=world.admin_h)).json()["data"]
    assert [h["action"] for h in history] == ["created", "edited"]
    assert history[1]["changes"]["quality"] == ["A", "B"]
    assert history[1]["actor"] == "Awa Admin"

    await client.post(f"/collections/{c['id']}/validate", headers=world.admin_h)
    locked = await client.patch(f"/collections/{c['id']}", json={"weight_kg": "1", "reason": "test"}, headers=world.admin_h)
    assert locked.status_code == 409


async def test_tenant_isolation(client, world, session):
    from .conftest import build_world

    other = await build_world(session, code="KOR", phone_suffix="5")
    r = await client.post("/collections", json=collection(world, producer_id=other.koffi.id), headers=world.collector_h)
    assert r.json()["errors"][0]["code"] == "unknown_producer"
    assert (await client.get(f"/producers/{other.koffi.id}", headers=world.admin_h)).status_code == 404
