from .test_collections_sync import collection
from .test_lots_payments_ussd import _validated


async def test_collector_reports_from_phone_idempotently(client, world):
    c = (await client.post("/collections", json=collection(world), headers=world.collector_h)).json()["data"]
    body = {
        "client_uuid": "iss-0001-aaaa",
        "category": "data_error",
        "message": "J'ai saisi 120 kg au lieu de 102 kg",
        "collection_id": c["id"],
        "context": {"app_version": "0.1.0", "pending": 0, "screen": "today"},
    }
    h = {**world.collector_h, "X-Device-Id": "device-abc-123"}
    first = await client.post("/issues", json=body, headers=h)
    assert first.status_code == 201, first.text
    issue = first.json()["data"]
    assert issue["reference"] == "SIG-0001" and issue["source"] == "mobile"
    assert issue["producer_id"] == world.koffi.id  # derived from the collection
    assert issue["collection_reference"] == c["reference"]
    # the phone retries its offline queue: no duplicate
    again = await client.post("/issues", json=body, headers=h)
    assert again.status_code == 200 and again.json()["data"]["id"] == issue["id"]

    mine = (await client.get("/issues", headers=world.collector_h)).json()
    assert mine["meta"]["total"] == 1


async def test_admin_inbox_resolution_and_dashboard(client, world):
    await client.post("/issues", json={"category": "app_bug", "message": "Le bouton exporter ne fait rien"}, headers=world.admin_h)
    d = (await client.get("/dashboard/summary", headers=world.admin_h)).json()["data"]
    assert any(a["code"] == "open_issues" for a in d["alerts"])
    inbox = (await client.get("/issues", params={"status": "unresolved"}, headers=world.admin_h)).json()["data"]
    assert inbox[0]["source"] == "web" and inbox[0]["reporter_name"] == "Awa Admin"
    r = await client.patch(f"/issues/{inbox[0]['id']}", json={"status": "resolved", "resolution_note": "Corrigé"}, headers=world.admin_h)
    assert r.json()["data"]["status"] == "resolved" and r.json()["data"]["resolved_at"]
    # collectors cannot handle reports
    assert (await client.patch(f"/issues/{inbox[0]['id']}", json={"status": "open"}, headers=world.collector_h)).status_code == 403


async def test_report_cannot_point_to_another_cooperative(client, world, session):
    from .conftest import build_world

    other = await build_world(session, code="KOR", phone_suffix="5")
    r = await client.post("/issues", json={"category": "data_error", "message": "test de lien", "producer_id": other.koffi.id}, headers=world.admin_h)
    assert r.status_code == 422


async def test_producer_reports_by_ussd_and_gets_sms_on_resolution(client, world):
    await _validated(client, world, "clt-ussd-iss-1", weight="25")
    url = "/channels/ussd?key=dev-ussd-key"
    menu = await client.post(url, data={"phoneNumber": world.koffi.phone, "text": "4"})
    assert menu.text.startswith("CON") and "Paiement non recu" in menu.text
    done = await client.post(url, data={"phoneNumber": world.koffi.phone, "text": "4*1"})
    assert done.text.startswith("END Signalement SIG-0001")

    issue = (await client.get("/issues", params={"source": "ussd"}, headers=world.admin_h)).json()["data"][0]
    assert issue["category"] == "data_error" and issue["collection_id"] and issue["producer_name"] == "KOFFI Amadou"
    await client.patch(f"/issues/{issue['id']}", json={"status": "resolved", "resolution_note": "Pesée vérifiée : 25 kg confirmés."}, headers=world.admin_h)
    sms = (await client.get("/dev/sms", params={"phone": world.koffi.phone})).json()["data"]
    assert "SIG-0001 a été traité" in sms[0]["body"] and "25 kg confirmés" in sms[0]["body"]


async def test_buyer_reports_on_public_lot_page_with_cap(client, world):
    c = await _validated(client, world, "clt-pub-iss-1")
    lot = (await client.post("/lots", json={"product": "cacao", "collection_ids": [c["id"]]}, headers=world.admin_h)).json()["data"]["lot"]
    token = (await client.post(f"/lots/{lot['id']}/seal", json={}, headers=world.admin_h)).json()["data"]["trace_url"].rsplit("/", 1)[1]
    for i in range(5):
        r = await client.post(f"/public/trace/{token}/issues", json={"message": f"Le poids du lot ne correspond pas ({i})", "contact": "qualite@exportateur.example"})
        assert r.status_code == 201
    capped = await client.post(f"/public/trace/{token}/issues", json={"message": "Encore un signalement de test"})
    assert capped.status_code == 429
    inbox = (await client.get("/issues", params={"source": "public"}, headers=world.admin_h)).json()
    assert inbox["meta"]["total"] == 5 and inbox["data"][0]["lot_reference"] == lot["reference"]
    assert (await client.post("/public/trace/bad-token/issues", json={"message": "lot inconnu test"})).status_code == 404
