# 0003 — SMS one-time codes for every role, no passwords

**Context.** v0 mixed OTP for collectors with a password for admins (`/auth/change-password`) without a
password login endpoint. In the field, password resets are a support burden, and phones are the identity.

**Decision.** Every internal user logs in with phone + SMS code. Rotating refresh tokens keep users logged in
for up to 90 days, so codes are rarely needed.

**Consequences.** One mechanism to secure (throttling, HMAC storage, no enumeration). SMS cost per login is
small given long sessions. A lost phone = deactivate the user from the web, which kills their refresh tokens' use.
