# ADR 0005: OCEN connector as a standalone Frappe site, connected via REST

**Status:** Accepted
**Date:** 2026-09-03

## Context

`ocen_connector` was built as one app among several installed on a single
combined site (`identity_core`, `los_engine`, `crm_extensions`,
`ocen_connector`, `ddp_engine`, `portal_gateway`, plus upstream
`lending`/`crm`/`erpnext`). `OCEN Loan Application.loan_application` was a
Frappe `Link` field directly into `los_engine`'s (Frappe Lending's) `Loan
Application` doctype — an in-process, same-database coupling.

Founder direction: OCEN should be architecturally standalone — able to
run and be reasoned about on its own, connected to the LOS rather than
merged into it.

## Decision

**Split into two Frappe sites on the same bench**, not two fully separate
tech stacks:

- **`ocen.localhost`** (the original combined site, keeping its existing
  data — the `identity_core`/`los_engine`/`crm_extensions` work and the
  ERPNext Company/Loan Product/Fiscal Year setup from ADR 0004, all
  preserved in place) — `identity_core`, `erpnext`, `lending`, `crm`,
  `los_engine`, `crm_extensions`, `ddp_engine`, `portal_gateway`, with
  `ocen_connector` uninstalled from it. Its name is now a naming artifact
  from before the split (this is really the LOS site) — this bench
  version has no `rename-site` command, and manually renaming a live
  site's directory/DB grants was judged riskier than living with the
  name. Not worth fixing until this site is recreated for some other
  reason anyway.
- **`ocen-network.localhost`** (fresh site) — `ocen_connector` only, plus
  bare `frappe`. This one's name is accurate.

Same bench, same codebase, same EC2 instance for now — the two sites
already don't share a database or a Python process, which is the part
that actually matters for "standalone." Splitting onto separate
infrastructure later is straightforward from here (different bench,
different instance, even a different stack) precisely because the
boundary is already a network boundary, not an in-process one.

### What changes in `ocen_connector`

- `OCEN Loan Application.loan_application` — was `Link` to `Loan
  Application`, becomes a plain `Data` field holding the LOS-side ID as a
  string. No DB-level referential integrity across the boundary; the API
  layer is the contract instead.
- `OCEN Loan Application.tenant_id` — was `Link` to `Tenant`, becomes a
  plain `Data` field (`tenant_code`) — informational/filtering only, not a
  Frappe User Permission-enforced boundary. Tenant-scoped access control
  for who can see what stays a LOS-side concern (LOS callers to the OCEN
  API authenticate as a service account, not as individual borrowers/field
  agents).
- `OCEN Offer`'s CGTMSE/FLDG mutual-exclusivity check (spec §1.4) used to
  cross-site-query `Loan Application.fldg_flag` directly — impossible once
  it's a different database. `fldg_flag` is now mirrored onto `OCEN Loan
  Application` at submission time (LOS tells OCEN this fact when it
  submits), and the check reads that local mirror instead.
- `required_apps` drops `identity_core` and `los_engine` — `ocen_connector`
  now depends on nothing but `frappe`.
- `OCEN Settings` gains LOS connection fields (base URL + API key/secret)
  so the webhook handlers can push status/offer updates back to LOS after
  processing an inbound OCEN webhook.

### What's new

- **`ocen_connector/api/integration.py`** — `submit_loan_application()`,
  the inbound API endpoint LOS calls to hand a loan application to OCEN
  (creates the `OCEN Loan Application` record here, mirrors `fldg_flag`).
  This is also what the spec's §6.3 stage 1 outbound submission will
  eventually build on top of, once real OCEN network calls are wired in.
- **`los_engine`'s `OCEN Integration Settings`** (new singleton doctype) —
  this site's OCEN connection fields (base URL + API key/secret), the
  mirror image of the new fields on `OCEN Settings`.
- **`los_engine`'s `Loan Offer`** (new doctype) — a LOS-side, UI-facing
  mirror of what the borrower needs to see (lender, amount, rate, tenure,
  status) to compare offers (spec §5.3 "N lenders offered you a loan").
  OCEN owns the full protocol-level state (`OCEN Offer`, raw payloads,
  `requestId`s); LOS owns just enough to drive its own UI without
  reaching into OCEN's database.
- **`los_engine/api/ocen_integration.py`** — `submit_to_ocen()` (LOS →
  OCEN, calls the endpoint above) and the inbound receivers
  `receive_ocen_stage_update()` / `receive_ocen_offer()` that
  `ocen_connector`'s webhook handlers call after processing a real OCEN
  webhook, so LOS's own `Loan Application`/`Loan Offer` records reflect
  what happened without LOS needing to poll.

### Auth between sites

Frappe's built-in API key/secret mechanism (`Authorization: token
<key>:<secret>`), one integration user per site dedicated to this, not a
shared admin credential. Configured via the new settings doctypes on each
side rather than hardcoded.

## Consequences

- Real network latency and failure modes now exist between "LOS decides to
  submit a loan application" and "OCEN has recorded it" — this didn't
  exist when it was one in-process call. Both integration endpoints should
  eventually get retry/idempotency handling; not built in this pass (the
  webhook side already has this via `OCEN Request Log`'s audit trail and
  `apply_webhook_stage`'s terminal-stage guard — the new LOS-facing calls
  don't yet).
- Two sites to `bench migrate`, two `OCEN Settings`-shaped configs to keep
  in sync (LOS's pointing at OCEN, OCEN's pointing at LOS) instead of one.
- Genuinely reusable now: another LA/LOS could integrate with this same
  OCEN site without needing to be a Frappe app on the same bench at all —
  it only needs to speak the REST contract this ADR defines.
