import gzip
import json

from app.core.timeutil import utcnow


async def test_responses_are_gzipped(client, world):
    r = await client.get("/sync/pull", headers={**world.collector_h, "Accept-Encoding": "gzip"})
    assert r.headers["content-encoding"] == "gzip"
    assert r.json()["success"] is True  # httpx decompresses transparently


async def test_etag_gives_304_when_unchanged(client, world):
    first = await client.get("/dashboard/summary", headers=world.admin_h)
    etag = first.headers["etag"]
    again = await client.get("/dashboard/summary", headers={**world.admin_h, "If-None-Match": etag})
    assert again.status_code == 304 and again.content == b""
    # a change invalidates it
    await client.post("/zones", json={"name": "Nouvelle zone"}, headers=world.admin_h)
    body = {"client_uuid": "clt-etag-0001", "producer_id": world.koffi.id, "collected_at": utcnow().isoformat(),
            "quality": "A", "weight_kg": "10"}
    await client.post("/collections", json=body, headers=world.collector_h)
    changed = await client.get("/dashboard/summary", headers={**world.admin_h, "If-None-Match": etag})
    assert changed.status_code == 200


async def test_gzip_request_body_accepted(client, world):
    body = {
        "device_id": "device-gzip-001",
        "device_time": utcnow().isoformat(),
        "collections": [{"client_uuid": "clt-gz-00001", "producer_id": world.koffi.id,
                         "collected_at": utcnow().isoformat(), "quality": "A", "weight_kg": "50"}],
    }
    r = await client.post("/sync/push", content=gzip.compress(json.dumps(body).encode()),
                          headers={**world.collector_h, "Content-Type": "application/json", "Content-Encoding": "gzip"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["accepted"][0]["amount"] == 140000
    bad = await client.post("/sync/push", content=b"not gzip", headers={**world.collector_h, "Content-Encoding": "gzip"})
    assert bad.status_code == 400


async def test_pull_is_slim_and_skips_unchanged_reference_data(client, world):
    first = (await client.get("/sync/pull", headers=world.collector_h)).json()["data"]
    assert set(first["producers"][0]) == {"id", "code", "first_name", "last_name", "phone", "zone_name", "status"}
    assert first["prices"] and first["settings"]
    second = (await client.get("/sync/pull", params={"since": first["cursor"], "ref": first["ref_hash"]}, headers=world.collector_h)).json()["data"]
    assert second["prices"] is None and second["zones"] is None and second["settings"] is None
    await client.put("/settings/alerts", json={"max_moisture_percent": "7.5", "max_weight_kg": "1000"}, headers=world.admin_h)
    third = (await client.get("/sync/pull", params={"since": first["cursor"], "ref": first["ref_hash"]}, headers=world.collector_h)).json()["data"]
    assert third["settings"]["max_moisture_percent"] == "7.5" and third["ref_hash"] != first["ref_hash"]


async def test_producer_list_has_no_geometry_but_detail_does(client, world):
    await client.post(f"/producers/{world.koffi.id}/parcels", json={"latitude": 6.9, "longitude": -6.4}, headers=world.admin_h)
    listed = (await client.get("/producers", headers=world.admin_h)).json()["data"]
    koffi = next(p for p in listed if p["id"] == world.koffi.id)
    assert koffi["parcels"][0]["geometry"] is None and koffi["parcels"][0]["eudr_issues"]
    detail = (await client.get(f"/producers/{world.koffi.id}", headers=world.admin_h)).json()["data"]
    assert detail["parcels"][0]["geometry"]["type"] == "Point"
