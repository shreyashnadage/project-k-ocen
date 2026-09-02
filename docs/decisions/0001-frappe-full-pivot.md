# ADR 0001: Full pivot to Frappe, retire the Fineract/Temporal scaffold

**Status:** Accepted
**Date:** 2026-09-02
**Deciders:** Founder/CTO (Shreyash Nadage)

## Context

Spec §0 identified an open architectural conflict: a separately scaffolded,
already-in-progress architecture existed using Postgres + Apache AGE +
Temporal + Redpanda + GoRules Zen Engine + Keycloak + Ory Kratos/Hydra +
Apache APISIX + SigNoz, with Apache Fineract as the loan-management core
(the `project-k-backend-service` repo is a related but distinct service —
the Tally Sync Platform — not this loan-core scaffold itself). A separate,
Frappe-based spec (this repo) proposed a different stack for the same LOS/CRM
domain. Building against both simultaneously would produce two incompatible
systems of record.

Three options were on the table (spec §0):
1. Frappe replaces the Fineract/Temporal architecture (full pivot).
2. Frappe covers a bounded subset (CRM + borrower UX) integrating with the
   existing core.
3. Parallel exploratory tracks, only one proceeds past prototype.

Deciding factor: engineering capacity is **1–5 FTE** for the next 6–12
months, building *and* operating whatever is chosen.

## Decision

**Option 1 — full pivot to Frappe.** This repo (`project-k-ocen`) is the
system of record for the OCEN LOS/CRM/DDP platform going forward. The
Fineract/Temporal/GoRules/Redpanda/Keycloak/Ory/APISIX/SigNoz scaffold is
retired as a runtime target.

## Rationale

- **Team size is the deciding constraint.** Operating Temporal + Redpanda +
  GoRules + Keycloak + Ory Kratos/Hydra + Apache APISIX + SigNoz + Apache AGE
  + Fineract as coordinated services is realistically a full-time
  platform-engineering job by itself, before any loan-origination logic
  ships. A 1–5 person team cannot carry that operational load and still
  build product.
- **Frappe is production-grade at this venture's near-term volumes**
  (single-digit-to-low-tens lenders, thousands of vendors, ₹2–10L tickets).
  It is not a toy framework — ERPNext runs mission-critical, regulated
  financial workflows for thousands of companies on it.
- **Maintainability favors one bench over nine services.** A single Frappe
  bench with a handful of apps has one deployment model, one upgrade
  cadence, one thing for a small team to learn deeply.
- **Event-native orchestration and Temporal-scale saga complexity are not
  yet needed.** The platform explicitly does not sanction loans (D4 gate is
  the lender's, out of scope — spec §2.2), so there is no complex
  multi-step distributed transaction to orchestrate on this platform's side.
  Frappe's hooks/background jobs cover the OCEN async state machine (§6.1)
  at this volume.
- **Bounded-subset integration (option 2) does not reduce operational
  load enough to matter.** Even a CRM/UX-only Frappe layer still requires
  running Fineract + Temporal + GoRules alongside it — for a 1–5 person
  team, that is still most of the heavyweight stack's operational cost, for
  partial benefit.

## Consequences

- **Sunk work is not lost, but is not runtime.** The Fineract scaffold's
  Pydantic domain models and GoRules D0–D3 gate logic remain a useful
  reference for eligibility-gate design in `los_engine`, even though the
  runtime (Fineract, Temporal, GoRules) is retired.
- **Apache 2.0 licensing is given up in favor of Frappe's licensing.**
  Frappe core itself is MIT. **Frappe CRM is AGPL** — mitigated by never
  modifying Frappe CRM core, only extending via a separate custom app
  (`crm`), per spec §3.6. Revisit with legal counsel before any scenario
  involving distributing modified Frappe CRM code externally (not a concern
  for operating it as an internal SaaS product).
- **Scale is deferred, not ignored.** If a specific component (most likely
  the OCEN async adapter or Trust Graph scoring) becomes a genuine
  bottleneck once real transaction volume exists, it can be extracted into
  a dedicated service (strangler pattern) at that point, with real load
  data to justify the added operational cost — not preemptively.
- This decision resolves spec §10 open questions #1 and #2.
