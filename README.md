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

## Repo layout

```
apps/                   Frappe apps (bounded contexts), one per subdirectory.
  identity_core/        Users, Roles, Role Profiles, tenant registry, org hierarchy.
  crm_extensions/        Anchor pipeline + Vendor lead pipeline, extends Frappe CRM.
  los_engine/            Loan Lead, Loan Application, underwriting workflow, offers.
  ocen_connector/        OCEN 4.0 async adapter — participant, request log, webhooks.
  ddp_engine/            Trust Graph entry, AA data ingestion, scoring adapter (thin —
                         see docs/decisions/0002-ip-boundary.md).
  portal_gateway/        BFF layer — role-aware composed API responses per frontend.
docker-compose.yml       Local dev bench: MariaDB, Redis, Frappe.
docs/
  spec.md                Full technical specification (source of truth for scope).
  decisions/             ADRs resolving the spec's open questions (§0, §10).
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
