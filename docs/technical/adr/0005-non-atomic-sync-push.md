# 0005 — Non-atomic sync push, idempotent on client UUID

**Context.** v0 described `/sync/push` as an "atomic batch" yet returned per-item accepted/rejected lists,
and used both an idempotency header and a client UUID.

**Decision.** Each collection in a push is processed independently. The only idempotency key is the
`client_uuid` generated on the phone; a replay returns the stored collection (`duplicate: true`, or HTTP 200 +
`X-Duplicate` on `POST /collections`). Business validation happens before any write, so a rejected item leaves nothing behind.

**Consequences.** A wet bag or a deactivated producer never blocks the rest of a day's work. The phone keeps
rejected entries with the server's message for correction.
