# Low-bandwidth design

Cooperative offices and collectors work on 2G/3G/EDGE, prepaid data bundles, and links that drop. Every
kilobyte costs money and seconds. Measured on the demo cooperative (40 producers, 150 deliveries).

## Results

| What | Before | After | How |
|---|---|---|---|
| Phone — first sync (full pull) | 100.3 KB | **4.9 KB** | slim sync schema (no parcels/polygons), gzip |
| Phone — routine sync (nothing new) | ~100 KB¹ | **0.2 KB** | incremental cursor + `ref_hash` skips unchanged prices/zones/settings |
| Phone — upload 25 weighings | 7.7 KB | **1.3 KB** | gzip request body |
| Web — collections page (25 rows) | 21.1 KB | **3.4 KB** | gzip |
| Web — producers page (25 rows) | 22.1 KB | **3.2 KB** | no polygons in lists, gzip |
| Web — dashboard poll, unchanged | 1.2 KB | **0 B body (304)** | ETag / If-None-Match |
| Web — first load (JS+CSS, gzip) | ~140 KB | **~77 KB** | code splitting, vendor chunks; map (51 KB) only on map pages |
| Web — repeat visit | ~140 KB | **~0 KB** of app code | service worker + immutable hashed assets |
| Web — map tiles on 2G/3G/data saver | auto (200–500 KB) | **on demand** | "Afficher la carte" button |

¹ before, prices/zones/settings and every changed producer with its parcels were re-sent on each pull.

Re-measure by calling each endpoint with `Accept-Encoding: gzip` and compare raw
vs. transferred bytes (the numbers above come from such a script against `make seed` data).

## Backend (`apps/backend/app/core/bandwidth.py`, `main.py`)

- **Response compression**: `GZipMiddleware` for bodies ≥ 860 bytes (JSON compresses 5–10×).
- **Compressed uploads**: `Content-Encoding: gzip` request bodies are accepted (10 MB decompressed cap
  against gzip bombs; invalid gzip → 400).
- **Conditional GET**: every successful GET JSON response carries a weak `ETag` and `Cache-Control:
  private, no-cache`; a matching `If-None-Match` gets `304` with an empty body. Browsers do this
  automatically for `fetch`, so the web app needed no code for it.
- **Slim sync**: `/sync/pull` returns `SyncProducer` (7 fields) and `SyncCollection` (6 fields) instead of
  the full web objects.
- **Reference-data versioning**: `/sync/pull` returns `ref_hash`; when the phone sends it back as `?ref=`,
  unchanged prices, zones and settings come back as `null`.
- **Lists without geometry**: `GET /producers` omits parcel polygons; the detail endpoint has them.

## Web (`apps/web-admin`)

- Routes are lazy-loaded; vendor code is split into stable chunks (`react`, `query`, `map`) so an app update
  only re-downloads our own code.
- Service worker (`public/sw.js`): cache-first for hashed `/assets/*`, network-first HTML with cached
  fallback. API calls are never cached by it.
- `src/lib/network.ts` reads `navigator.connection`: on `slow-2g`/`2g`/`3g` or data-saver, polling intervals
  are ×4 and map tiles wait for a click. Polling pauses in background tabs (TanStack Query default).
- Data is reused for 60 s across page switches (`staleTime`).
- `deploy/nginx.conf` + `Dockerfile`: pre-gzipped assets (`gzip_static`), one-year immutable caching for
  `/assets/`, revalidated HTML. Serving the API on the same origin (commented `location /v1/`) also removes
  the CORS preflight round-trip, which matters on high-latency links.

## Mobile (`apps/mobile-collector`)

- Responses are gzip (dart:io sends `Accept-Encoding: gzip` and inflates transparently).
- Push batches are gzip-compressed and limited to **25 collections**: on a flaky link, each batch that gets
  through is saved instead of losing one large upload.
- Pull sends `since` (cursor) and `ref` (hash); automatic syncs pull at most every **15 minutes** — a new
  weighing triggers a push only. Manual sync always pulls.
- Network failures back off **1 → 2 → 4 → 8 → 16 → 30 minutes** for automatic attempts; a connectivity
  change resets the backoff.
- Everything needed to work (producers, prices, thresholds) is local: a day of collection needs zero bytes
  until the collector chooses to sync.

## Next steps if needed

- Photos: compress on the phone to ~60 KB JPEG (1280 px, q=60) and upload only on Wi-Fi or on demand.
- Brotli at the reverse proxy (≈15 % smaller than gzip for JSON).
- HTTP/2 or HTTP/3 at the proxy to cut connection setup on high-latency links.
- SMS fallback for critical sync (a day's totals) where there is no data coverage at all.
