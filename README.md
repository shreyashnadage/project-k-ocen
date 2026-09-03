# Project K — OCEN Loan Agent Platform

Frappe-based Loan Origination System (LOS) + CRM + multi-role UI layer for an
OCEN 4.0 Loan Agent (LA) / Derived Data Provider (DDP) fintech platform.

Full background: `docs/spec.md` (technical specification handed off for
implementation). Architecture decisions made against that spec's open
questions: `docs/decisions/`.

## Status

Phase 1 (Foundation) in progress. See `docs/decisions/0001-frappe-full-pivot.md`
for why this repo exists as a standalone Frappe bench rather than extending
the previously-scaffolded Fineract/Temporal/GoRules architecture.

## Two Frappe sites, one bench (ADR 0005)

- **LOS site** — `identity_core`, `crm_extensions`, `los_engine`, `ddp_engine`,
  `portal_gateway`, plus upstream `erpnext`/`lending`/`crm`. Everything
  borrower/lending/CRM-facing.
- **OCEN site** — `ocen_connector` alone, plus bare `frappe`. Deliberately
  standalone (founder direction) — no in-process dependency on the LOS
  site's doctypes. The two talk over REST, authenticated with a pre-shared
  secret; see ADR 0005 for the design and ADR 0006 for a known dev-environment
  HTTP-serving issue on the OCEN site (not a code bug — see that ADR before
  assuming something's broken).

## Repo layout

```
apps/                   Frappe apps (bounded contexts), one per subdirectory.
  identity_core/         Users, Roles, Role Profiles, tenant registry, org hierarchy.
  crm_extensions/        Anchor pipeline + Vendor lead pipeline, extends Frappe CRM
                         (requires the upstream `crm` app — see its README).
  los_engine/            Loan Lead + thin extensions over Frappe Lending's Loan
                         Application (requires the upstream `lending` app).
  ocen_connector/        OCEN 4.0 async adapter — standalone site, own database
                         (ADR 0005). Participant directory, request log, webhooks,
                         LOS integration API. Depends only on `frappe`.
  ddp_engine/            Placeholder (Phase 3) — Trust Graph entry, AA data ingestion,
                         thin proprietary-scoring adapter. See spec §3.6.
  portal_gateway/        Placeholder (Phase 4) — BFF layer, role-aware composed API
                         responses per frontend.
docker-compose.yml       Local dev bench: MariaDB, Redis, Frappe.
docs/
  spec.md                Full technical specification (source of truth for scope).
  decisions/             ADRs resolving the spec's open questions (§0, §10), plus
                         architecture decisions made along the way.
  compliance-questions.md Open questions needing lending/credit/compliance input —
                         tracked, not blocking POC development.
```

Frontends (Field Agent PWA, Lender Dashboard, Ops Console, Anchor Admin,
Borrower experience) are separate repos/packages, built against these apps'
REST API — not included here. See spec §3.5, §5.

## Local development

Requires Docker. This repo does not vendor a full bench; `docker-compose.yml`
brings up MariaDB + Redis + a Frappe container, then each app under `apps/`
is installed into the site via `bench get-app /workspace/apps/<app> && bench
install-app <app>` (see `docker-compose.yml` comments for the exact sequence).

```
docker compose up -d
```

## Apps as bounded contexts

One shared bench for all apps (simplest ops model for a 1–5 engineer team).
Split into separate benches/sites only when a specific app has a concrete,
demonstrated load- or failure-isolation need — not preemptively.

Do not build custom tenant-isolation or permission logic in Python where
Frappe's native User Permission / Role Permission / Perm Level mechanisms can
express it declaratively. See spec §3.2, §4.2.
