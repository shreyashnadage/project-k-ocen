# ADR 0003: Phase 1 dev instance provisioned and validated on AWS

**Status:** Accepted
**Date:** 2026-09-02

## Context

Local Docker wasn't usable (memory constraints), so per the founder's
direction the Phase 1 bench was stood up on AWS instead of locally, ahead of
schedule relative to ADR 0002's "defer until it runs locally" — the
local-run checkpoint became an AWS-run checkpoint instead. This also served
as the first real validation of the hand-scaffolded Frappe apps against an
actual bench (they had only been JSON/Python syntax-validated before this).

## What was provisioned

- **EC2 instance**: `t3.medium`, Ubuntu 22.04, `ap-south-1`, 30GB gp3 —
  tagged `Project=project-k-ocen`, `Phase=1`. Named `ocen-frappe-bench-dev`.
- **Security group**: `ocen-frappe-bench-sg` — ports 22 and 8000 only,
  restricted to the developer's IP at provisioning time (not 0.0.0.0/0).
  Distinct from a pre-existing, unrelated `ocen-platform-sg` found already
  in the account (wide open on 22/80/443/3000/8000/8180/8233 — a leftover
  from the retired Fineract/Temporal track per ADR 0001, no instance
  attached to it; not touched, should be cleaned up separately).
- **Key pair**: `ocen-platform-key`, generated fresh for this project —
  not reused from any other project's credentials.
- **Credentials used**: the account's existing `tally-sync-admin` IAM user
  (AdministratorAccess). This is broader than this task needed and tied to
  an unrelated project; used by explicit founder choice for speed over
  creating a scoped-down provisioning user.
- **Docker + docker-compose stack**: installed via cloud-init on boot,
  matches the repo's `docker-compose.yml` (MariaDB 10.6, two Redis 6.2
  instances for cache/queue, `frappe/bench:latest`).

## What was validated

Site `ocen.localhost` created; all 10 apps installed with no errors:
`frappe`, `identity_core`, `erpnext`, `lending`, `crm`, `los_engine`,
`crm_extensions`, `ocen_connector`, `ddp_engine`, `portal_gateway`.
Confirmed via `bench console`:

- All 6 Role Profile fixtures present (`identity_core`)
- `Loan Application` custom fields present: `tenant_id`,
  `performed_by_agent`, `fldg_flag` (`los_engine`)
- `CRM Lead` custom fields present: `tenant_id`, `anchor`
  (`crm_extensions`)
- `Loan Lead`, `Vendor Attestation` doctypes present
- All 5 `OCEN *` doctypes present (`ocen_connector`)
- `Tenant` is a working nested-set tree

Dev server reachable at `http://<instance-ip>:8000` (Administrator login).

## Findings that change assumptions made during scaffolding

1. **`frappe/bench:latest` installs the `develop` branch**, not a pinned
   v16 — `bench init` needs `--frappe-branch version-16` (or whichever tag
   is actually wanted) if version pinning matters before this goes further.
   Not yet re-done; current dev instance runs on `develop`.
2. **Frappe Lending genuinely depends on ERPNext** (`Required
   frappe-dependency 'erpnext' not found`) — it is not the standalone LOS
   core the spec's §3.4 assumed. ERPNext (a large app, ~2500+ doctypes) is
   now installed alongside it. This is a materially bigger footprint than
   "Frappe Lending v16 as a thin LOS core" implied — worth a follow-up
   conversation with the founder on whether that scope is acceptable, or
   whether a lighter-weight custom LOS core (spec's originally-considered
   alternative in §3.4) should be reconsidered given this.
3. **This bench version's `bench get-app` has a bug** resolving local
   filesystem paths (`AttributeError: 'App' object has no attribute
   'org'`) — worked around by manually symlinking each app into `apps/`,
   `pip install -e`, and registering in `sites/apps.txt` rather than using
   `get-app` for the local apps. Fine for dev; if this bench version ships
   this bug long-term, worth filing upstream or pinning to a release tag
   instead of `develop`.
4. `bench init --no-procfile` (used for a leaner first init) meant `bench
   start` had nothing to run — regenerated via `bench setup procfile`, then
   removed the two `redis_cache`/`redis_queue` process lines (this bench
   uses the compose network's separate Redis containers, not
   locally-spawned ones), and added `--host 0.0.0.0` to the `web:` line
   (defaults to `127.0.0.1`, unreachable through the Docker port mapping
   otherwise).

## Not done here

No Terraform — this was provisioned by hand via AWS CLI for speed, per the
founder's direction. Capturing it as IaC is follow-up work if this instance
is meant to persist rather than be thrown away once local Docker is
available or a real staging environment is set up.
