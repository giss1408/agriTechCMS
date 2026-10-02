# Producer payments

## Flow

1. Admin opens *Paiements → À payer*: validated, unpaid collections grouped by producer, with outstanding
   advances and the net amount (`GET /payments/payables`).
2. Admin selects producers → `POST /payments/batch` (202). For each producer:
   - producers without a mobile-money account are **skipped** and reported;
   - advances are **reserved** oldest-first up to the gross amount (`advance_allocations`);
   - one `payment` is created; its collections get `payment_id` (so they cannot be paid twice);
   - if the advance covers everything, the payment is `success` immediately (nothing to send).
3. After the response, a background task sends each transfer through the provider.
4. Outcome: `success` (collections → `paid`, SMS to the producer) or `failed` (reason stored).
   Asynchronous providers confirm through the signed webhook.
5. A failed payment can be **retried** (same payment, `attempts + 1`) or **cancelled** (collections become
   payable again, reserved advances are released).

## Providers (`apps/backend/app/services/providers.py`)

| Provider | Use | Behaviour |
|---|---|---|
| `sandbox` | demo, tests | instant success; accounts ending in `00` fail (to show retries) |
| `cinetpay` | production target | Transfer API adapter; **endpoints must be checked against CinetPay's current documentation and tested in their sandbox before enabling** |

Adding Julaya or a direct operator API = one class with `async send(payment) -> ProviderResult`.

## Webhook

`POST /v1/payments/webhook/{provider}` with header `X-Signature: hex(HMAC-SHA256(raw_body, AGT_PAYMENT_WEBHOOK_SECRET))`
and body `{"payment_id" | "external_ref", "status": "success" | "failed", "trans_id", "reason"}`.
Unsigned or wrongly signed calls get 401. Callbacks are idempotent (providers retry). A provider whose callback
format differs gets a thin translating adapter in front of this endpoint.

## Accounting rules

- `gross_amount` = sum of the collections' amounts; `amount` = sent = gross − advance deduction.
- Producer balance for a campaign: earned = validated + paid collections; paid = paid collections;
  `balance_due` = earned − paid; `net_payable` = max(0, balance_due − outstanding advances).
- The cooperative needs a funded disbursement account at the provider; reconciliation export: `GET /payments`
  filtered by period (CSV export to add with the accounting integration).
