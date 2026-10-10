# Features and screens

> Replaces `archive/fonctionnalites-et-vues-v0.md`. View numbers (V1–V10) are kept so the archive mockups
> remain a useful reference. Status reflects this repository.

## Web — cooperative manager (`apps/web-admin`)

| View | Route | What it does | Status |
|---|---|---|---|
| V1 Dashboard | `/` | Today's collections, to-validate count, amount left to pay, campaign totals, 7-day chart, actionable alerts (stale validations, failed payments, moisture near threshold, producers without geolocated parcel, silent phones), top collectors, EUDR readiness | ✅ |
| V2 Producers | `/producers`, `/producers/:id` | Search/filter, create, CSV import, detail tabs: identity, parcels on a map with EUDR issues and deforestation check, deliveries, payments & advances, printable QR card | ✅ |
| V3 Collections | `/collections` | Filters (status, dates, collector, quality) kept in the URL, bulk validation, detail drawer with GPS link, clock correction, audit history, reject with reason, CSV export (Excel-friendly) | ✅ |
| V4 Payments | `/payments` | "To pay" list grouped by producer with advance deduction, batch payout, history with live status, retry / cancel failed payments | ✅ |
| V5 Reports & traceability | `/lots` | Lots: compose from validated deliveries, seal (issues the buyer link), ship, GeoJSON export for EUDR due-diligence. Campaign report via API | ✅ (PDF templates: later) |
| V6 Settings | `/settings` | Versioned purchase prices, alert thresholds, users (collectors/admins), zones, phones' sync status, demo SMS outbox | ✅ |
| V10 Buyer portal | `/trace/:token` | Public, no login: lot summary, parcels map, producers (no personal data), EUDR completeness, "Signaler une anomalie" form | ✅ (accounts for buyers: later) |
| V11 Problem reports | `/issues` + "Signaler un problème" button on every page and in the collection drawer | One inbox for all channels (web, collector app, producer USSD, buyer page): filter by status/origin, take charge, resolve with a note (sent by SMS to USSD reporters). Reports carry diagnostics automatically (page, browser, connection, last API errors) | ✅ |

## Mobile — collector (`apps/mobile-collector`)

| View | What it does | Status |
|---|---|---|
| Login | Phone + SMS code; demo shows the code | ✅ |
| V7 Home | Online/offline indicator, pending count, last sync, scan / new / today | ✅ |
| V8 New collection | Producer by QR scan or offline search, weight (French comma accepted), quality A/B, moisture with threshold check, live estimated amount from cached prices, GPS fix (best effort), notes | ✅ |
| V9 Today | Synced / pending / rejected per entry, server status (validated, paid), edit or delete unsent entries, correct rejected ones, tap a sent entry to report an error on it | ✅ |
| Report a problem | From the home screen or a sent collection: category + message; app version, sync state and last error attached. **Works offline**: queued on the phone, sent at the next sync (idempotent) | ✅ |

Not in the MVP: photo of the weighing (API ready: `POST /uploads/photo`), producer signature, adding a parcel
from the phone (API ready: `POST /producers/{id}/parcels`).

## Producer — USSD (`POST /channels/ussd`)

```
CON Coopérative Espoir de Daloa
Bonjour Amadou
1. Mon solde
2. Mes dernieres livraisons
3. Prix du jour
4. Signaler un probleme   → 1. Poids ou montant faux / 2. Paiement non recu / 3. Autre (etre rappele)
```

A USSD report is linked to the producer (and their last delivery for a weight dispute); when the office
resolves it, the producer receives an SMS with the resolution note.

WhatsApp notifications: later. Payment confirmations are sent by SMS today.

## Role matrix (as implemented)

The archive's matrix said collectors had read-only access to producers while the API let them create
producers — the code settles it: collectors **can register producers and parcels** in the field (common in
practice), admins validate.

| Capability | Admin / super admin | Collector | Producer | Buyer |
|---|---|---|---|---|
| Dashboard, reports | ✅ | ❌ | ❌ | ❌ |
| Producers: read | ✅ | ✅ (sync) | own balance via USSD | ❌ |
| Producers & parcels: create | ✅ | ✅ | ❌ | ❌ |
| Producers: edit, deactivate, advances | ✅ | ❌ | ❌ | ❌ |
| Collections: create | ✅ | ✅ | ❌ | ❌ |
| Collections: read | all | own only | own via USSD | via lot |
| Collections: edit (pending only), validate, reject, cancel | ✅ | ❌ | ❌ | ❌ |
| Lots, payments, settings, users | ✅ | ❌ | ❌ | ❌ |
| Report a problem | ✅ | ✅ (sees own reports) | ✅ USSD | ✅ on a lot page |
| Handle reports (inbox, resolve) | ✅ | ❌ | ❌ | ❌ |
| Lot trace page | ✅ | ❌ | ❌ | ✅ (link) |

`super_admin` additionally edits cooperative identity and can create other super admins.
