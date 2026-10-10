# Offline-first synchronisation

The collector app must work for days without network. The protocol is deliberately simple: the phone
**pushes** what it recorded, then **pulls** what changed.

```mermaid
sequenceDiagram
  participant P as Phone (SQLite)
  participant S as API
  Note over P: Offline: each weighing saved in `outbox`<br/>with a client_uuid, sync_state = pending
  P->>S: POST /sync/push {device_id, device_time, collections[≤25]} (gzip body)
  S->>S: offset = server_now − device_time<br/>for each item: ingest (idempotent on client_uuid)
  S-->>P: accepted[] (incl. duplicates), rejected[] {code, message}, clock_offset_seconds
  P->>P: accepted → synced (store id, reference, server amount)<br/>rejected → shown to the collector for correction
  P->>S: GET /sync/pull?since=<cursor>&ref=<ref_hash>  (X-Device-Id)
  S-->>P: producers changed (slim), own collections changed (statuses),<br/>prices/zones/settings only if ref_hash changed, new cursor + ref_hash
  P->>P: upsert; replace prices if sent; store cursor and ref_hash
```

## Rules

| Rule | Why |
|---|---|
| Push before pull | The collector's work is the scarce resource; reference data can wait |
| Push is **not atomic**: per-item `accepted` / `rejected` | One wet bag must not block 40 good weighings |
| Idempotent on `client_uuid` | Retries after a timeout, double taps, re-sent batches are harmless; duplicates come back as `accepted` with `duplicate: true` |
| Rejected items stay on the phone (`sync_state = rejected`) with the server message | The collector corrects and re-sends, nothing is lost silently |
| The outbox is never purged on logout | A dead session must not destroy unsent work |
| Server computes amounts and statuses | Phone shows an estimate from cached prices; the server's value replaces it after sync |
| Prices, zones and settings versioned by `ref_hash`: sent in full when changed, `null` otherwise | Small when sent, zero when unchanged; no deletion tracking needed |
| Producers sent incrementally, including `inactive` ones | So the phone can hide deactivated producers |
| `cursor` = server time − 30 s | A row committed just after the read could carry an earlier `updated_at`; the overlap re-sends a few rows, harmless with upserts |

## Clock correction

Low-end phones often have wrong clocks (battery removed, no network time). Each push carries `device_time`.
The server computes `offset = server_now − device_time`; when `|offset| > 2 min` it corrects each
`collected_at` by that offset, keeps the original in `collected_at_device`, records `clock_offset_seconds`,
and never accepts a future date. The web drawer shows "heure du téléphone corrigée de N min"; *Paramètres →
Téléphones* lists phones with drifting clocks.

The price applied is the one in force on the **corrected collection date**, never the sync date: a weighing
made on 30 September and synced on 2 October keeps the old campaign price.

## Triggers on the phone

- Connectivity comes back (`connectivity_plus` event)
- A new weighing is saved while online (push only; automatic pulls at most every 15 min)
- Every 3 minutes while there is something pending (some phones report connectivity late)
- After a network failure, automatic attempts back off 1 → 30 min; a connectivity change resets it
- Pull-to-refresh and the *Synchroniser* button; *Tout re-télécharger* forces a full pull

Bandwidth details: [09-low-bandwidth.md](09-low-bandwidth.md).

## Limits (accepted for the MVP)

- Conflicts on reference data are "server wins": collectors do not edit producers offline.
- Photos are not yet sent by the app (the endpoint exists): they will be uploaded separately after the
  collection, so a missing photo never blocks the data.
- A concurrent duplicate `client_uuid` racing in two requests at the same millisecond hits the unique
  constraint and returns a 500 to the second request; the phone retries and gets the duplicate answer.
