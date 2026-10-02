async def test_otp_login_refresh_and_me(client, world):
    r = await client.post("/auth/request-otp", json={"phone": "07 00 00 00 12"})  # local format accepted
    assert r.status_code == 200, r.text
    code = r.json()["data"]["dev_code"]

    bad = await client.post("/auth/verify-otp", json={"phone": "+2250700000012", "otp": "000000" if code != "000000" else "111111"})
    assert bad.status_code == 401
    assert bad.json()["errors"][0]["attempts_left"] == 4

    r = await client.post("/auth/verify-otp", json={"phone": "+2250700000012", "otp": code, "device_id": "dev-1234-abcd"})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["user"]["role"] == "collector"
    assert data["user"]["cooperative"]["code"] == "DAL"

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.json()["data"]["name"] == "Konan Collecteur"

    r2 = await client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r2.status_code == 200
    # rotation: the old refresh token is dead
    r3 = await client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r3.status_code == 401


async def test_unknown_number_gets_same_answer_but_no_sms(client, world):
    r = await client.post("/auth/request-otp", json={"phone": "+2250799999999"})
    assert r.status_code == 200
    assert "dev_code" not in r.json()["data"]
    sms = await client.get("/dev/sms", params={"phone": "+2250799999999"})
    assert sms.json()["data"] == []


async def test_resend_throttle(client, world):
    assert (await client.post("/auth/request-otp", json={"phone": "+2250700000012"})).status_code == 200
    r = await client.post("/auth/request-otp", json={"phone": "+2250700000012"})
    assert r.status_code == 429
    assert r.json()["errors"][0]["code"] == "resend_too_soon"


async def test_collector_cannot_use_admin_endpoints(client, world):
    r = await client.get("/payments/payables", headers=world.collector_h)
    assert r.status_code == 403
    assert r.json()["success"] is False
