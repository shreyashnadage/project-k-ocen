# ocen_connector

OCEN 4.0 async API adapter (spec §6). As of **ADR 0005**, this app runs on
its own standalone Frappe site (`ocen-network.localhost`), separate from
the LOS site — not installed alongside `identity_core`/`los_engine`.
Depends on nothing but `frappe`. `OCEN Loan Application.loan_application`
holds the LOS-side ID as a plain string, not a Link — the two sites talk
over REST.

## DocTypes

- **OCEN Settings** (single) — OAuth2 client-credentials config + JWS
  signing key for the real OCEN network, plus this site's connection to
  the LOS site (`los_site_url`, `integration_shared_secret`).
  `OCENSettings.get_access_token()` handles OAuth2 token caching/refresh.
- **OCEN Participant** — directory of network participants: one `is_self=1`
  row for this platform's own LA identity, one row per subscribed lender.
- **OCEN Loan Application** — the async journey state machine per
  application, plus a `fldg_flag` mirror (from LOS, at submission time —
  see below) and `tenant_code` (informational, not a Link). Only ever
  mutated via `apply_webhook_stage()` — never edit `ocen_stage` by hand in
  the Desk UI in production.
- **OCEN Offer** — one row per responding lender per application. Its
  CGTMSE/FLDG mutual-exclusivity check (spec §1.4) reads the local
  `fldg_flag` mirror on `OCEN Loan Application`, not a cross-site query.
- **OCEN Request Log** — append-only audit trail of every outbound call and
  inbound response/webhook.

## LOS ↔ OCEN integration (ADR 0005)

- **`api/integration.py`** — `submit_loan_application()`, called by LOS
  (`los_engine.api.ocen_integration.submit_to_ocen`) to hand over a Loan
  Application. Idempotent per `loan_application`.
- **`utils/los_client.py`** — outbound calls back to LOS
  (`notify_stage_change`/`notify_offer`), made by the webhook receivers
  after processing a real OCEN callback, so LOS's local mirror
  (`Loan Application.ocen_stage`, `Loan Offer`) stays current without
  polling.
- **`utils/shared_auth.py`** — auth for this channel, in both directions:
  a pre-shared secret in a custom header (`X-Integration-Secret`), checked
  with `hmac.compare_digest`. **Not** Frappe's own User `api_key`/
  `api_secret` mechanism — that was tried first and, for reasons fully
  written up in **ADR 0006**, consistently failed for real HTTP requests
  to this specific site in this dev environment despite the underlying
  data being verified correct at every layer. The shared-secret scheme
  sidesteps that unresolved issue and is fully verified working — see ADR
  0006 for the real, over-HTTP proof (OCEN → LOS push, both
  `notify_stage_change` and `notify_offer`, confirmed landing correctly on
  the LOS side).

**Known gap (ADR 0006):** inbound HTTP requests specifically to this site
(`ocen-network.localhost`) — the webhook receivers below and
`submit_loan_application` — fail in this dev environment with a
misleading `AppNotInstalledError`, despite the app being genuinely
installed (verified via `list-apps`, `site_config.json`, the DB global
Frappe actually reads, and direct Python calls to the functions
themselves — all correct). This is a dev-server/environment issue, not a
code bug; see ADR 0006 for the full investigation and what to try in a
fresh environment.

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
missing headers are all rejected. Sandbox still allows an unsigned call
through (logged as a warning) so the webhook flow can be exercised before
real OCEN credentials exist; Production always requires a valid signature.
**What's not verified**: the actual header name (`X-Jws-Signature`) and
detached-JWS shape are assumed from the Account Aggregator/ReBIT
convention OCEN's ecosystem generally follows — confirm against real OCEN
sandbox traffic before relying on this (spec §6.5).

## Not yet built (later phases)

The outbound side — `POST /v4/loanApplications` and the remaining four API
groups for offer acceptance → disbursement (spec §6.3 stage 3) — is not
implemented in this pass. `OCENSettings.sign_request()` is ready for them.
