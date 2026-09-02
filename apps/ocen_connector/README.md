# ocen_connector

OCEN 4.0 async API adapter (spec §6). Depends on `identity_core` (Tenant,
Role Profiles) and `los_engine` (Loan Application — `OCEN Loan Application`
links 1:1 to it).

## DocTypes

- **OCEN Settings** (single) — OAuth2 client-credentials config + JWS
  signing key, all secrets via Frappe's encrypted Password fieldtype.
  `OCENSettings.get_access_token()` handles caching/refresh.
- **OCEN Participant** — directory of network participants: one `is_self=1`
  row for this platform's own LA identity, one row per subscribed lender.
- **OCEN Loan Application** — the async journey state machine per
  application. Only ever mutated via `apply_webhook_stage()`, called from
  the webhook receivers — never edit `ocen_stage` by hand in the Desk UI in
  production.
- **OCEN Offer** — one row per responding lender per application.
- **OCEN Request Log** — append-only audit trail of every outbound call and
  inbound response/webhook.

## Webhooks

`ocen_connector/api/webhooks.py` exposes the inbound callback targets:

- `POST /api/method/ocen_connector.api.webhooks.loan_application_status`
- `POST /api/method/ocen_connector.api.webhooks.offer_response`

Both are `allow_guest=True` (OCEN calls them unauthenticated as a webhook,
not as a logged-in Frappe user) and log every call to OCEN Request Log
regardless of outcome. `_verify_signature` does real RS256 detached-JWS
verification (`ocen_connector/utils/jws.py`) against
`OCEN Settings.registry_public_key` — verified with a self-generated test
keypair: valid signatures pass, tampered payloads/wrong keys/malformed or
missing headers are all rejected (see git history for the test). Sandbox
still allows an unsigned call through (logged as a warning) so the webhook
flow can be exercised before real OCEN credentials exist; Production always
requires a valid signature. **What's not verified**: the actual header name
(`X-Jws-Signature`) and detached-JWS shape are assumed from the Account
Aggregator/ReBIT convention OCEN's ecosystem generally follows — confirm
against real OCEN sandbox traffic before relying on this (spec §6.5).

## Not yet built (later phases)

The outbound side — `POST /v4/loanApplications` and the remaining four API
groups for offer acceptance → disbursement (spec §6.3 stage 3) — is not
implemented in this pass. `OCENSettings.sign_request()` is ready for them.
