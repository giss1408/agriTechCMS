# REST API

> Replaces `archive/cahier-des-charges-api-v0.md` (which was truncated in the middle of the payments
> section). The **live, exhaustive reference is the OpenAPI page** served by the backend at `/docs`; this
> document gives the conventions, the endpoint map and every deliberate change from v0.

Base URL: `https://<host>/v1` · JSON everywhere · French error messages, stable English error codes.

## Conventions

### Envelope

```json
{ "success": true, "data": { }, "meta": { "page": 1, "per_page": 20, "total": 340 }, "errors": [] }
```

Errors: `{"success": false, "data": null, "errors": [{"code": "moisture_above_threshold", "message": "Humidité 9.1 % au-dessus du seuil (8.0 %) : lot à re-sécher"}]}`.
Clients switch on `code`, show `message`.

### Headers

| Header | When |
|---|---|
| `Authorization: Bearer <jwt>` | every authenticated call |
| `X-Device-Id: <uuid>` | mobile app (sync, collections) |
| `X-Signature: <hex hmac>` | payment webhooks |

`X-Idempotency-Key` from v0 is **dropped**: idempotency is carried by `client_uuid` in the collection body,
which survives app restarts and works the same online and in sync batches.

### Status codes

| Code | Meaning |
|---|---|
| 200 / 201 | OK / created. A replayed collection (same `client_uuid`) returns **200 with the stored collection** and `X-Duplicate: true` — v0 used 409, which forced clients to treat a success as an error |
| 202 | accepted, processed asynchronously (payment batch, retry) |
| 400 | malformed input (`validation_error` with `field`) |
| 401 / 403 | not authenticated / role not allowed |
| 404 | not found **or belongs to another cooperative** (no existence leak) |
| 409 | invalid state transition (validate a paid collection, change a sealed lot…) |
| 413 / 415 | upload too large / wrong type |
| 422 | business rule (`moisture_above_threshold`, `weight_above_max`, `no_price`, `unknown_producer`, `nothing_to_pay`…) |
| 429 | OTP throttling |

### Bandwidth

Responses ≥ 860 bytes are gzip-compressed (`Accept-Encoding: gzip`); request bodies may be sent with
`Content-Encoding: gzip`. GET JSON responses carry an `ETag`; send `If-None-Match` to get `304` when
unchanged. See [09-low-bandwidth.md](09-low-bandwidth.md).

### Pagination and filters

`?page=1&per_page=20` (max 200) on list endpoints; `meta.total` is returned. Filters are plain query params
(`status`, `date_from`, `date_to`, `collector_id`, `producer_id`, `quality`, `product`, `zone_id`, `lot_id`, `unlotted`).

## Endpoint map

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/request-otp`, `POST /auth/verify-otp`, `POST /auth/refresh` (rotating), `POST /auth/logout` |
| Users | `GET /users/me`, `GET/POST /users`, `GET/PATCH/DELETE /users/{id}` |
| Cooperative & settings | `GET/PATCH /cooperative`, `GET/POST /settings/purchase-prices`, `PATCH /settings/purchase-prices/{id}`, `GET/PUT /settings/alerts`, `GET/POST /zones` |
| Producers | `GET/POST /producers`, `POST /producers/import` (CSV), `GET /producers/by-phone/{phone}` (list: families share phones), `GET/PATCH/DELETE /producers/{id}`, `GET /producers/{id}/qr-code` (PNG), `GET /producers/{id}/balance?campaign=` |
| Parcels | `GET/POST /producers/{id}/parcels`, `PATCH/DELETE /parcels/{id}` — GeoJSON `Point` or `Polygon`, or `latitude`/`longitude` shorthand |
| Advances | `GET/POST /producers/{id}/advances` |
| Collections | `GET/POST /collections`, `GET /collections/totals`, `GET /collections/stats/daily`, `GET /collections/export` (CSV), `POST /collections/validate` (bulk), `GET/PATCH/DELETE /collections/{id}`, `GET /collections/{id}/history`, `POST /collections/{id}/validate`, `POST /collections/{id}/reject` |
| Sync | `POST /sync/push`, `GET /sync/pull?since=&ref=`, `GET /sync/devices`, `GET /sync/status/{device_id}` — see [05-offline-sync.md](05-offline-sync.md) |
| Lots | `GET/POST /lots`, `GET /lots/{id}`, `POST /lots/{id}/collections`, `DELETE /lots/{id}/collections/{cid}`, `POST /lots/{id}/seal`, `POST /lots/{id}/ship`, `GET /lots/{id}/traceability`, `GET /lots/{id}/eudr.geojson` |
| Payments | `GET /payments/payables`, `GET /payments`, `GET /payments/summary`, `POST /payments/batch`, `GET /payments/{id}`, `POST /payments/{id}/retry`, `POST /payments/{id}/cancel`, `POST /payments/webhook/{provider}` — see [06-payments.md](06-payments.md) |
| Problem reports | `POST /issues` (idempotent on `client_uuid`; source = `mobile` when `X-Device-Id` is sent), `GET /issues?status=unresolved&source=`, `GET/PATCH /issues/{id}`, public `POST /public/trace/{token}/issues` (max 5 open per lot) |
| Dashboard & reports | `GET /dashboard/summary`, `GET /reports/campaign?campaign=`, `GET /reports/eudr.geojson` |
| Public | `GET /public/trace/{token}` (no auth, no personal data) |
| Channels | `POST /channels/ussd?key=` (form fields `sessionId`, `phoneNumber`, `text`; answers `CON …`/`END …`) |
| Uploads | `POST /uploads/photo` (JPEG/PNG/WebP ≤ 5 MB), `GET /uploads/{id}` |
| Dev only | `GET /dev/sms` (console SMS outbox; 404 in prod) |

## Key payloads

```jsonc
// POST /collections  — also the item shape inside POST /sync/push
{
  "client_uuid": "6f1c…",            // generated on the phone, idempotency key
  "producer_id": "prod_01k6…",
  "collected_at": "2026-10-01T08:30:00Z",
  "product": "cacao", "quality": "A",
  "weight_kg": "120.5",               // decimals as strings: exact
  "moisture_percent": "6.5",
  "gps": { "lat": 6.8774, "lng": -6.4502 },
  "notes": "Séchage correct", "photos": ["img_…"]
}
// 201 → amount computed server-side
{ "id": "col_…", "reference": "COL-20261001-7K2Q9A", "unit_price": 2800, "amount": 337400,
  "status": "pending_validation", "collected_at": "…", "collected_at_device": "…", "clock_offset_seconds": 0, … }
```

```jsonc
// POST /payments/batch
{ "producer_ids": ["prod_…"], "reference_note": "Octobre S1" }
// 202
{ "batch_id": "pbat_…", "total_amount": 488000, "count": 2,
  "payments": [{ "producer_id": "prod_…", "gross_amount": 560000, "advance_deduction": 100000, "amount": 460000, "status": "initiated", … }],
  "skipped": [{ "producer_id": "prod_…", "reason": "Aucun compte mobile money renseigné" }] }
```

## Changes from v0, summarised

| v0 | Now | Why |
|---|---|---|
| Duplicate collection → 409 | 200 + `X-Duplicate` | A replay is a success for the client |
| `X-Idempotency-Key` header | `client_uuid` in body | One mechanism, survives restarts |
| `/sync/push` "atomic batch" | Per-item results, not atomic | One bad entry must not block a day of work |
| `pull?since=<timestamp>` | `pull?since=<cursor>` returned by the server (30 s safety overlap) | No missed rows on concurrent commits |
| Admin password login (`/auth/change-password`) | OTP for every role | One login mechanism, no password resets in the field |
| No lots | `/lots/*` + public trace | Traceability needs collection → lot → buyer |
| Parcel = point | Point or Polygon, measured area, EUDR issues | EUDR requires polygons above 4 ha |
| — | Advances, payables, cancel payment | Coops pre-finance producers; failed payouts must be releasable |
| — | USSD channel | Producers will not install an app |
