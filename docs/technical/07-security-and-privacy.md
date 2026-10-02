# Security and personal data

## Authentication

- Login = phone number + 6-digit SMS code, for every role ([ADR 0003](adr/0003-otp-for-every-role.md)).
- Codes: random, valid 5 min, 5 attempts, stored only as HMAC bound to the phone number.
- Throttling: 1 code per minute and 5 per hour per number (SMS pumping is the main cost risk).
- Unknown numbers get the same answer as known ones and no SMS (no account enumeration).
- Access token: JWT HS256, 12 h. Refresh token: random, 90 days, stored as HMAC, **rotated on every use**,
  revoked on logout.
- `AGT_SECRET_KEY` must be set in production (startup refuses the default).

## Authorisation

- Role checks per endpoint (`require_admin`, `require_staff`).
- Tenancy: every query filters by the user's `cooperative_id`; another cooperative's object returns 404.
- Collectors only read their own collections.

## Other protections

- Payment webhooks: HMAC signature, constant-time comparison, idempotent.
- USSD callback: shared key in the callback URL (aggregators do not sign).
- Uploads: type allow-list, 5 MB cap, stored outside the web root, served only to the same cooperative.
- Public trace page: unguessable token (≈ 96 bits), **no personal data**: no phone, no ID number, first name reduced to an initial.
- Audit log of every change to weights, prices, statuses and payments.
- CORS restricted to the web app origin (`AGT_CORS_ORIGINS`).

## Personal data (Côte d'Ivoire)

The platform processes names, phone numbers, ID card numbers, GPS positions of farms, and payment data.
Law n° 2013-450 on personal data protection applies; the regulator is **ARTCI**.

Before the pilot:

- [ ] Declare / request authorisation for the processing with ARTCI (the cooperative is data controller; we are processor)
- [ ] Data processing agreement with each cooperative (purpose, retention, sub-processors: hosting, SMS, payment)
- [ ] Producer information notice (oral + printed on the QR card back) and consent for GPS mapping
- [ ] Hosting location decision (cross-border transfer rules)
- [ ] Retention policy (e.g. 5 campaigns for traceability evidence, then anonymisation)

Data minimisation already in place: ID number optional, public page stripped, buyers only see lot-level data.

## To do before production

- HTTPS only, HSTS, secrets in a vault, database backups with restore drills
- Rate limiting at the proxy for public endpoints (`/public/trace`, `/channels/ussd`)
- Error tracking and uptime monitoring
- Rotate `AGT_PAYMENT_WEBHOOK_SECRET` and `AGT_USSD_KEY` per environment
