import json

from app.core.security import sign_webhook

from .test_collections_sync import collection

SQUARE_5HA = {  # ~224 m x 224 m near Daloa
    "type": "Polygon",
    "coordinates": [[[-6.450, 6.880], [-6.44797, 6.880], [-6.44797, 6.88203], [-6.450, 6.88203]]],
}


async def _validated(client, world, uuid, producer=None, weight="100"):
    body = collection(world, uuid, weight_kg=weight, producer_id=(producer or world.koffi).id)
    c = (await client.post("/collections", json=body, headers=world.collector_h)).json()["data"]
    await client.post(f"/collections/{c['id']}/validate", headers=world.admin_h)
    return c


async def test_parcel_polygon_area_and_eudr_flags(client, world):
    r = await client.post(f"/producers/{world.koffi.id}/parcels", json={"crop": "cacao", "area_hectares": "5", "geometry": SQUARE_5HA}, headers=world.admin_h)
    assert r.status_code == 201, r.text
    parcel = r.json()["data"]
    assert 4.8 < float(parcel["measured_area_hectares"]) < 5.2
    assert parcel["geometry"]["coordinates"][0][0] == parcel["geometry"]["coordinates"][0][-1]  # ring closed
    assert parcel["eudr_issues"] == ["deforestation_unchecked"]

    point = await client.post(f"/producers/{world.yao.id}/parcels", json={"area_hectares": "6", "latitude": 6.9, "longitude": -6.4}, headers=world.collector_h)
    assert "polygon_required_above_4ha" in point.json()["data"]["eudr_issues"]


async def test_lot_lifecycle_and_public_trace(client, world):
    parcel = (await client.post(f"/producers/{world.koffi.id}/parcels", json={"area_hectares": "5", "geometry": SQUARE_5HA}, headers=world.admin_h)).json()["data"]
    await client.patch(f"/parcels/{parcel['id']}", json={"deforestation_status": "clear"}, headers=world.admin_h)
    c1 = await _validated(client, world, "clt-lot-00001")
    c2 = await _validated(client, world, "clt-lot-00002", producer=world.yao, weight="50")
    pending = (await client.post("/collections", json=collection(world, "clt-lot-00003"), headers=world.collector_h)).json()["data"]

    r = await client.post("/lots", json={"product": "cacao", "collection_ids": [c1["id"], c2["id"], pending["id"]]}, headers=world.admin_h)
    assert r.status_code == 201, r.text
    lot = r.json()["data"]["lot"]
    assert lot["reference"].startswith("LOT-") and "-DAL-0001" in lot["reference"]
    assert lot["collections_count"] == 2 and lot["total_weight_kg"] == "150.00"
    assert r.json()["data"]["refused"] == [{"id": pending["id"], "reason": "Seules les collectes validées entrent dans un lot"}]

    other = (await client.post("/lots", json={"product": "cacao", "collection_ids": [c1["id"]]}, headers=world.admin_h)).json()["data"]
    assert other["refused"][0]["reason"] == "Déjà dans un autre lot"

    sealed = (await client.post(f"/lots/{lot['id']}/seal", json={"bags_count": 3}, headers=world.admin_h)).json()["data"]
    assert sealed["status"] == "sealed" and sealed["trace_url"]
    token = sealed["trace_url"].rsplit("/", 1)[1]
    assert (await client.post(f"/lots/{lot['id']}/collections", json={"ids": [pending["id"]]}, headers=world.admin_h)).status_code == 409

    shipped = (await client.post(f"/lots/{lot['id']}/ship", json={"buyer_name": "Exportateur Démo SA"}, headers=world.admin_h)).json()["data"]
    assert shipped["status"] == "shipped"

    public = (await client.get(f"/public/trace/{token}")).json()["data"]
    assert public["summary"]["producers"] == 2
    assert public["summary"]["producers_without_parcel"] == 1  # Yao has no parcel yet
    assert public["summary"]["eudr_ready"] is False
    koffi = next(p for p in public["producers"] if p["code"] == "DAL-00001")
    assert koffi["name"] == "KOFFI A." and "phone" not in koffi and koffi["eudr_ready"] is True
    assert len(public["geojson"]["features"]) == 1

    # a collection in a lot can no longer be cancelled
    assert (await client.delete(f"/collections/{c1['id']}", headers=world.admin_h)).status_code == 409


async def test_payment_batch_with_advance_and_failure_retry(client, world, session):
    # Koffi received a 100 000 F advance; delivers 2 x 100 kg x 2800 = 560 000 F
    await client.post(f"/producers/{world.koffi.id}/advances", json={"amount": 100000, "reason": "Avance rentrée scolaire"}, headers=world.admin_h)
    await _validated(client, world, "clt-pay-00001")
    await _validated(client, world, "clt-pay-00002")
    # Yao's mobile money account ends with "00": the sandbox makes that transfer fail
    world.yao.momo_account = "+2250522222200"
    session.add(world.yao)
    await session.commit()
    await _validated(client, world, "clt-pay-00003", producer=world.yao, weight="10")

    payables = (await client.get("/payments/payables", headers=world.admin_h)).json()["data"]
    koffi = next(p for p in payables if p["producer_id"] == world.koffi.id)
    assert (koffi["gross_amount"], koffi["outstanding_advances"], koffi["net_amount"]) == (560000, 100000, 460000)

    r = await client.post("/payments/batch", json={"producer_ids": [world.koffi.id, world.yao.id], "reference_note": "Octobre S1"}, headers=world.admin_h)
    assert r.status_code == 202, r.text
    assert r.json()["data"]["total_amount"] == 460000 + 28000  # 10 kg x 2800

    # background dispatch has run by the time the ASGI call returns
    pays = {p["producer_id"]: p for p in (await client.get("/payments", headers=world.admin_h)).json()["data"]}
    assert pays[world.koffi.id]["status"] == "success"
    assert pays[world.koffi.id]["advance_deduction"] == 100000
    assert pays[world.yao.id]["status"] == "failed"

    bal = (await client.get(f"/producers/{world.koffi.id}/balance", headers=world.admin_h)).json()["data"]
    assert (bal["total_earned"], bal["total_paid"], bal["balance_due"], bal["outstanding_advances"]) == (560000, 560000, 0, 0)

    sms = (await client.get("/dev/sms", params={"phone": world.koffi.phone})).json()["data"]
    assert "460 000 FCFA" in sms[0]["body"] and "Avance remboursée : 100 000 FCFA" in sms[0]["body"]

    # Failed payment: nothing left to pay twice, then cancel frees the collections again
    assert (await client.get("/payments/payables", headers=world.admin_h)).json()["data"] == []
    yao_pay = pays[world.yao.id]["id"]
    assert (await client.post(f"/payments/{yao_pay}/cancel", headers=world.admin_h)).json()["data"]["status"] == "cancelled"
    assert len((await client.get("/payments/payables", headers=world.admin_h)).json()["data"]) == 1


async def test_webhook_signature_and_idempotency(client, world, monkeypatch):
    from app.services import providers

    class Slow:  # behaves like a real provider: accepted now, result later by webhook
        name = "slow"

        async def send(self, payment):
            return providers.ProviderResult("processing", external_ref="ext-42")

    monkeypatch.setattr("app.services.payments.get_provider", lambda: Slow())
    await _validated(client, world, "clt-hook-0001")
    await client.post("/payments/batch", json={"producer_ids": [world.koffi.id]}, headers=world.admin_h)
    pay = (await client.get("/payments", headers=world.admin_h)).json()["data"][0]
    assert pay["status"] == "processing"

    body = json.dumps({"external_ref": "ext-42", "status": "success", "trans_id": "OM123"}).encode()
    forged = await client.post("/payments/webhook/cinetpay", content=body, headers={"X-Signature": "nope"})
    assert forged.status_code == 401
    for _ in range(2):  # providers retry callbacks
        ok = await client.post("/payments/webhook/cinetpay", content=body, headers={"X-Signature": sign_webhook(body)})
        assert ok.json()["data"]["status"] == "success"
    cols = (await client.get("/collections", params={"status": "paid"}, headers=world.admin_h)).json()
    assert cols["meta"]["total"] == 1


async def test_ussd_menu(client, world):
    await _validated(client, world, "clt-ussd-0001", weight="25")
    url = "/channels/ussd?key=dev-ussd-key"
    home = await client.post(url, data={"sessionId": "s1", "phoneNumber": world.koffi.phone, "text": ""})
    assert home.text.startswith("CON ") and "1. Mon solde" in home.text
    balance = await client.post(url, data={"sessionId": "s1", "phoneNumber": world.koffi.phone, "text": "1"})
    assert balance.text.startswith("END ") and "Reste a payer: 70 000 F" in balance.text
    prices = await client.post(url, data={"sessionId": "s1", "phoneNumber": world.koffi.phone, "text": "3"})
    assert "cacao A: 2 800 F/kg" in prices.text
    unknown = await client.post(url, data={"sessionId": "s2", "phoneNumber": "+2250199999999", "text": ""})
    assert unknown.text.startswith("END")
    assert (await client.post("/channels/ussd?key=wrong", data={"phoneNumber": "x"})).status_code == 401


async def test_dashboard_and_exports(client, world):
    await _validated(client, world, "clt-dash-0001")
    await client.post("/collections", json=collection(world, "clt-dash-0002", moisture_percent="7.8"), headers=world.collector_h)
    d = (await client.get("/dashboard/summary", headers=world.admin_h)).json()["data"]
    assert d["today"]["count"] == 2
    assert d["amount_to_pay"] == 280000
    assert d["pending_validation"] == 1
    assert len(d["series_7d"]) == 7 and d["series_7d"][-1]["count"] == 2
    assert {a["code"] for a in d["alerts"]} >= {"moisture_near_threshold", "parcels_missing"}

    csv = await client.get("/collections/export", headers=world.admin_h)
    assert csv.status_code == 200 and csv.text.lstrip("﻿").startswith("reference;date;")
    report = (await client.get("/reports/campaign", headers=world.admin_h)).json()["data"]
    assert report["by_quality"][0]["key"] == "cacao A"
