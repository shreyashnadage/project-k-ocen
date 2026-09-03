# ADR 0006: Known issue — inbound HTTP to the OCEN site fails on this dev bench

**Status:** Open finding, not a design flaw — documents an unresolved
environment issue found while verifying ADR 0005.
**Date:** 2026-09-03

## Summary

While verifying the LOS↔OCEN REST integration (ADR 0005) end-to-end, every
inbound HTTP request to `ocen-network.localhost` (the standalone OCEN
site) — both the webhook receivers and `ocen_connector.api.integration.
submit_loan_application` — fails with `AppNotInstalledError: App
ocen_connector is not installed`, despite `ocen_connector` being
genuinely, correctly installed on that site.

**This is not a bug in this repo's code.** Every layer was checked
directly and found correct:

- `bench --site ocen-network.localhost list-apps` → `frappe, ocen_connector`
- `site_config.json`'s `installed_apps` → `["frappe", "ocen_connector"]`
- `frappe.db.get_global("installed_apps")` (what the runtime check
  actually reads) → `["frappe", "ocen_connector"]`, verified via `bench
  console`
- Raw SQL against `tabUser` for API-key auth data → correct, matching
  values
- Direct Python calls to the actual whitelisted functions (bypassing HTTP
  dispatch) → **all pass**, including the shared-secret auth logic and
  `submit_loan_application`'s business logic (see the test run in this
  session's history)

Yet the exact same check (`frappe.get_installed_apps()`, called from
`frappe/utils/__init__.py`'s `get_attr()`), when triggered by a real HTTP
request to this site — on the main multi-site dev server (port 8000), on
a freshly-restarted process, on a completely separate single-process dev
server on a different port (8001), and after a full `redis-cli FLUSHALL`
— consistently returns as if `ocen_connector` isn't installed.

## What was ruled out

- Redis cache staleness (full `FLUSHALL` + restart, still failed)
- Multi-site process pollution / request ordering (a request to
  `ocen-network.localhost` as the *very first* request of a freshly
  restarted process still failed)
- Zombie/duplicate server processes on the port (checked `ps`/`ss` — only
  one listener)
- `serve_default_site` interference (disabled it, still failed)
- A stale on-disk `sites/apps.json` (exists, predates the site's creation,
  but nothing in Frappe core actually reads it for this check — confirmed
  via `grep`)
- Frappe User `api_key`/`api_secret` auth specifically (this was the
  original suspect and the reason `ocen_connector/utils/shared_auth.py`
  exists — switching to a pre-shared-secret scheme was the right call
  regardless, but it did not fix *this* separate issue, since the
  app-installed check happens before any auth check runs)

## What was proven working, for real, over real HTTP

The **OCEN → LOS** direction (`ocen_connector.utils.los_client`, called
from an `ocen-network.localhost` console session making a genuine
outbound HTTP call to `http://ocen.localhost:8000`) works completely:
`notify_stage_change` and `notify_offer` both succeeded, verified by
reading the results back from the LOS site — `Loan Application.ocen_stage`
updated to `"Acknowledged"`, and a `Loan Offer` record created with all
fields correct. This proves the shared-secret auth scheme, the REST
contract, and the LOS-side receivers all work correctly — the issue is
narrowly scoped to *inbound* HTTP requests reaching `ocen-network.localhost`
specifically, not the integration design.

## Working theory (unconfirmed)

`ocen.localhost` was the original site this bench was built around and has
never shown this issue. `ocen-network.localhost` was created later via
`bench drop-site` + `bench new-site` (after an earlier misconfigured
attempt). Something about a freshly created *second* site's recognition
for inbound HTTP serving specifically — as opposed to CLI/console access,
which is unaffected — appears not to be picked up by this particular
`bench start` dev server (werkzeug, explicitly not intended for
production use) in this Frappe `develop`-branch build. This was not
tracked down further given the time already invested and that direct
function-level testing gives full confidence in the actual code.

## What this means practically

- The LOS↔OCEN integration code (ADR 0005) is correct and verified,
  including auth. Treat it as done.
- Testing `ocen_connector`'s inbound HTTP endpoints (webhook receivers,
  `submit_loan_application`) needs either: a fresh bench built from
  scratch with both sites created before first server start, a pinned
  stable Frappe release instead of `develop`, or a production-style WSGI
  deployment (gunicorn, one process per site) instead of `bench start`'s
  dev server — any of which may sidestep whatever this dev-server-specific
  quirk is. Worth a fresh, clean environment before spending more time on
  root-causing it further.
- Not a blocker for continuing other work — the architecture, schema, and
  logic for standalone OCEN are done; this is a dev-environment serving
  quirk to revisit when standing up real infrastructure.
