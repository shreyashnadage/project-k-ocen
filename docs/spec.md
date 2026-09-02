# OCEN Loan Agent Platform — Technical Specification

**Version:** 1.0 draft
**Purpose:** Handoff spec for coding agent implementation
**Scope:** Frappe-based Loan Origination System (LOS) + CRM + multi-role UI
layer for an OCEN 4.0 Loan Agent (LA) / Derived Data Provider (DDP) fintech
platform

> This is the specification as handed off. Architecture decisions resolving
> its open questions (§0, §10) live in `docs/decisions/` — read those
> alongside this document, as they supersede options this spec left open.

## 0. CRITICAL — Read Before Starting

**Open architectural conflict, resolved — see `docs/decisions/0001-frappe-full-pivot.md`.**

This venture had a separately scaffolded, already-in-progress architecture
using Postgres + Apache AGE (graph) + Temporal (workflow orchestration) +
Redpanda (event bus) + GoRules Zen Engine (decision tables) + Keycloak + Ory
Kratos/Hydra + Apache APISIX + SigNoz, with Apache Fineract explicitly chosen
over Frappe Lending as the loan management core, deployed on RKE2/AWS Mumbai.
A Claude Code scaffold (CLAUDE.md, Docker Compose, Pydantic domain models,
decision receipt signer, GoRules D0–D3 gates, Temporal origination saga,
ADRs) already existed against that stack.

This document specifies a different, Frappe-based stack. Three options were
on the table:

1. This Frappe-based spec **replaces** the Fineract/Temporal architecture
   (full pivot).
2. This spec covers a **bounded subset** (e.g., CRM + borrower UX only) that
   must integrate with the existing Fineract/Temporal/GoRules core rather
   than duplicate it.
3. These are **parallel exploratory tracks** and only one proceeds past
   prototype.

**Decision: option 1, full pivot.** Rationale in the ADR. Do not build
against the Fineract/Temporal scaffold going forward — this repo is the
system of record.

## 1. Business Context

### 1.1 What the company does

The company operates as a Loan Agent (LA) and Derived Data Provider (DDP) on
the OCEN 4.0 framework, originating anchor-led vendor-side receivables
financing for deep-tier MSME vendors of mid-market auto-ancillary and
manufacturing corporates in western Maharashtra (Kolhapur–Sangli–Satara,
Pune, Chakan, Aurangabad, Nashik clusters).

### 1.2 The actors

- **Anchors** — mid-market auto-ancillary/manufacturing corporates (e.g.
  Zanvar Group, Quality Power, prospects like Ghatge Patil, Sound Castings,
  Mantri Metallics). Attestation partners, confirming vendor relationships
  and (where possible) transaction data. Not the borrower, not the customer
  in the traditional sense — data/trust partners.
- **Vendors / Borrowers** — deep-tier MSME suppliers to the anchors. The
  actual borrower population. Largely low digital literacy, Marathi/Hindi
  first, WhatsApp-native, workshop/small-manufacturing operators.
- **Lenders** — banks/NBFCs on the OCEN network who fund loans and purchase
  DDP-derived signals. The platform does not lend its own capital.
- **Field Agents** — the company's own on-ground credit officers who source,
  pre-qualify, and assist vendors through onboarding in the
  Kolhapur–Sangli–Satara belt.
- **Platform Ops / Credit Ops / DDP Analysts** — internal roles managing the
  LOS pipeline, underwriting support, and Trust Graph data curation.

### 1.3 Revenue model

LA origination fees plus DDP data sales to lenders. Fees are collected from
the borrower side per OCEN LA convention (LAs are agents of the borrower, not
the lender — collecting fees from lenders would be a conflict of interest).
DDP monetization (selling Trust Scores/signals to lenders) is a separate
revenue stream and must be accounted for separately (separate cost centers).

### 1.4 Regulatory constraints the build must respect

- RBI Digital Lending Directions 2025 — repayments go direct to lender, no
  third-party pooling account on this platform.
- DPDP Act 2023 / Rules 2025 — data fiduciary obligations; hard enforcement
  from May 2027. Consent, retention, and erasure logic must be designed in
  from day one, not retrofitted.
- CGTMSE and FLDG are mutually exclusive — do not design a credit
  enhancement flow that assumes both can co-exist on the same loan.
- The platform must not encode lender underwriting decisions (D4 gate) —
  this is a regulatory and commercial boundary. The platform's decisioning
  stops at pre-screening/eligibility, not credit sanction.

## 2. Goals and Non-Goals

### 2.1 Goals

- Build a Loan Origination System (LOS) covering the full OCEN borrower
  journey: discovery → AA consent → application → offer comparison →
  KYC/eSign → disbursement tracking → repayment visibility.
- Build a CRM layer managing two distinct pipelines: Anchor relationship
  pipeline and Vendor/borrower lead pipeline.
- Implement multi-tenant, RBAC-governed access so lenders, anchors, field
  agents, ops, and borrowers each see only what they should.
- Build an OCEN 4.0 API adapter implementing the async
  request/response/webhook pattern for all OCEN-mandated calls.
- Build borrower-facing experiences appropriate to a low-digital-literacy,
  vernacular-first, WhatsApp-native user base — not a generic fintech app UX.
- Keep the UI layer visually independent of Frappe's default look, using a
  custom design system, while retaining Frappe's permission-aware
  data-fetching "magic."

### 2.2 Non-Goals (explicitly out of scope for this build)

- The platform does **not** underwrite or sanction loans — that decision
  remains with lenders (D4 gate, out of scope).
- The platform does **not** hold or pool borrower repayments.
- This spec does not cover the DDP Trust Graph's proprietary scoring
  algorithm internals (lives in a separate, non-Frappe service per the
  IP-boundary principle, §3.6).
- Company entity registration, licensing (FACE SRO membership etc.) are
  business-process items, not build items.

## 3. System Architecture

### 3.1 Framework choice

Frappe Framework (Python/MariaDB) as the backend engine, decomposed into
multiple bounded-context Frappe apps installed on a shared bench. Custom,
non-Frappe-UI frontends per role, built in React/Next.js, consuming Frappe's
REST API.

### 3.2 Multi-tenancy model (hybrid)

Two tenancy strategies used deliberately for two different populations:

**A. Site-per-tenant** (Frappe-native site isolation — separate database,
separate URL, full data isolation) — used for **lender partners**. Rationale:
banks/NBFCs may have compliance requirements precluding shared infrastructure
with other lenders; the population is small (single digits to low tens), so
operational overhead of N sites is manageable.

**B. Pooled multi-tenant with row-level isolation** — used for
**vendor/borrower population and anchor relationships**. Every relevant
DocType carries a `tenant_id` field (mapped to anchor/cluster), enforced via
Frappe's native User Permission mechanism at the query layer — not custom
application code. Rationale: thousands of vendors; per-tenant sites would be
absurd overhead for a borrower taking a ₹2–10 lakh loan.

Do not build custom tenant-isolation logic in Python where Frappe's native
User Permission / Role Permission mechanism can express it declaratively.

### 3.3 Service decomposition — Frappe apps as bounded contexts

| App | Owns | Notes |
|---|---|---|
| `identity_core` | Users, Roles, Role Profiles, tenant registry, org hierarchy | Auth source of truth for all other apps |
| `crm` | Anchor pipeline (Organization/Deal), Vendor lead pipeline (Lead) | Fork/extend Frappe CRM; do not modify core, extend via custom app |
| `los_engine` | Loan Lead, Loan Application, underwriting workflow, offer records | Frappe Lending v16 selected as LOS core per full-pivot decision — see §3.4 |
| `ocen_connector` | OCEN Participant, OCEN Request Log, async request/response state machine, webhook receivers | See §6 for full spec |
| `ddp_engine` | Trust Graph Entry, AA data ingestion, scoring interface | Thin adapter calling an external service, never hosts proprietary scoring logic in-process — see §3.6 |
| `portal_gateway` | BFF layer — role-aware, cross-doctype composed API responses for each frontend | Read-mostly; exists to avoid frontends making 3+ chained calls per screen |

Start all apps on one shared bench (simplest ops model). Split into separate
benches/sites only when a specific service has a concrete, demonstrated
load- or failure-isolation need — not preemptively.

### 3.4 Frappe Lending vs. custom LOS doctypes — resolved

Frappe Lending v16 provides Loan Lead → Loan Application → KYC →
disbursement flow out of the box, plus a co-lending module (`Loan Partner`
doctype) that can be repurposed for LA pass-through tracking (the company is
not the lender, so disbursement/repayment is managed by the lender partner;
the Loan Account exists for audit/tracking only).

Per the full-pivot decision (`docs/decisions/0001-frappe-full-pivot.md`),
`los_engine` builds on Frappe Lending v16 as the LOS core rather than
mirroring state from Fineract. The Fineract scaffold's domain modeling
(Pydantic models, D0–D3 gate logic) remains a useful reference for
eligibility-gate design even though the runtime is retired.

### 3.5 Frontend architecture

No Frappe UI (Vue) in the visual layer — founder has explicitly rejected its
default aesthetic. Options evaluated, in order of recommendation:

1. **frapkit** (React) — open-source library giving Desk-grade,
   DocType-metadata-driven form/list rendering via Frappe's existing
   whitelisted API, no backend changes required, fully restylable. Preferred
   starting point.
2. **Custom metadata-driven renderer** — hand-built React component set
   (~10–15 field-type components: text, select, date, link/lookup, currency,
   etc.) driven by DocType metadata fetched via API, with a form-renderer
   component that walks metadata and respects permission-filtered field
   lists returned by the API. Build this if frapkit's layout opinions don't
   fit a given role-front (e.g., Borrower app needs a radically different
   layout from Lender Dashboard).
3. Reuse only `frappe-ui`'s data-fetching composables (`createResource` /
   `useCall`) if a Vue-based front is acceptable for any specific role-UI —
   not recommended given the "ugly" rejection, documented as fallback.

**Principle to enforce:** permission enforcement is a backend-only concern
(Role + Perm Level + User Permission, checked server-side on every API call)
— it does not depend on which frontend framework is used and must never be
re-implemented as a frontend-side check.

Each role gets its own deployable SPA:

- Field Agent app (PWA, mobile-first, offline-tolerant capture)
- Lender Dashboard (desktop-first, offer/portfolio views)
- Ops/Underwriting Console (desktop, dense data views)
- Anchor Admin portal (lightweight, anchor-side vendor list management)
- Borrower experience — not a conventional SPA, see §5.

### 3.6 IP / licensing boundary

Any GPL/AGPL system-of-record (which Frappe/ERPNext and Frappe CRM are,
noting **Frappe CRM specifically carries AGPL** requiring separate legal
review) must communicate with any proprietary component (e.g., Trust Graph
scoring) only via REST or an event bus, never via code linking. If
`ddp_engine` needs to host or call proprietary scoring logic, this boundary
must be preserved architecturally — never import proprietary scoring code
directly into the Frappe app's Python codebase. Do not modify Frappe CRM
core; extend only via a separate custom app.

## 4. RBAC Specification

### 4.1 Role taxonomy (Role Profiles)

| Role Profile | Roles bundled | Scope |
|---|---|---|
| Borrower | `Borrower` | Own records only (User Permission on `borrower_id` / `tenant_id`) |
| Field Agent | `Field Agent`, `CRM User` | Assigned vendor leads/applications in their cluster; write access to capture, no access to DDP scores |
| Credit Ops | `Underwriter`, `LOS User` | Full Loan Application read/write within eligibility-check scope; no lender-side offer editing |
| DDP Analyst | `DDP User` | Trust Graph data read/write; Loan Application read-only |
| Lender Reviewer | `Lender Portal User` | Read-only on Applications/Offers scoped to their own lender `tenant_id` (site-isolated per §3.2A, so this is largely enforced by site boundary, with User Permission as defense-in-depth) |
| Anchor Admin | `Anchor Portal User` | Read/write on their own vendor list and attestation records only |
| Platform Admin | `System Manager` equivalent | Full access, used sparingly |

### 4.2 Enforcement mechanisms (all native Frappe, no custom permission code
unless a rule genuinely cannot be expressed declaratively)

- **DocType Permissions** (Role Permissions Manager) — coarse
  read/write/create/delete/submit per role per doctype.
- **Perm Level** — field-level grouping (e.g., DDP score fields at Perm
  Level 2, visible only to DDP Analyst + Underwriter roles, hidden from
  Field Agent).
- **User Permission** — row-level restriction keyed on `tenant_id` /
  `borrower_id` / `anchor_id` link fields — this is the multi-tenant
  enforcement mechanism for the pooled-tenant population (§3.2B).
- **Data Masking** (Frappe v16, experimental — verify stability before
  relying on it in production) — for showing-but-masking sensitive fields
  (e.g., bank account numbers) across roles that need partial visibility.

### 4.3 Delegation / "acting on behalf of" pattern (Field Agent → Borrower)

Field agents will frequently perform actions (data capture, AA consent
initiation, document upload) on behalf of a borrower who is present but not
directly operating the system. This must be logged as **proxy action**, not
silent impersonation:

- Every write performed by a Field Agent session against a Borrower-owned
  record must stamp a `performed_by_agent` field (link to the agent's User)
  alongside the standard `owner` / `modified_by` fields, distinct from
  genuine borrower self-service actions.
- This is a compliance/audit requirement (DPDP Act accountability, and
  useful for dispute resolution) — not optional.
- Implement via a standard `before_save` / `before_insert` hook pattern in
  the relevant doctypes' controllers, checking session role, rather than
  trusting client-supplied flags.

## 5. Borrower-Facing Experience Specification

### 5.1 Design premise

The primary borrower is a deep-tier MSME vendor with low digital literacy,
Marathi/Hindi-first, WhatsApp-native, and higher trust in the anchor
corporate than in a new fintech brand. Do not design a conventional
self-service fintech app as the primary channel. Design assisted-first,
self-serve-second.

### 5.2 Channels (in order of primacy)

1. **Field-agent-assisted onboarding** — the Field Agent app (§3.5) is the
   primary onboarding tool; the borrower rarely operates a screen directly
   during onboarding.
2. **WhatsApp** — for status nudges, offer notifications, document requests,
   repayment reminders, disbursement confirmations. Implement via WhatsApp
   Business API (Twilio integration under evaluation — confirm current
   status before building). Use the utility template category where
   possible for cost efficiency.
3. **Lightweight PWA** (not native app — avoid app-store install friction) —
   reserved for moments that need a real screen: comparing multiple lender
   offers side by side, eKYC/eSign, viewing repayment schedule. Must run
   acceptably on 3G, minimal image weight, tolerate connection drops
   without losing form state.

### 5.3 Borrower journey → channel mapping

| OCEN stage | Borrower-facing moment | Primary channel |
|---|---|---|
| Discovery | Anchor-branded introduction | Field agent, in person |
| AA Consent | Plain-language consent explanation | Field agent assisted + simple consent screen |
| Application submitted | — | (no borrower action needed) |
| Offer comparison | "N lenders offered you a loan" | WhatsApp notify → PWA to compare |
| KYC / eSign | Aadhaar OTP, agreement signature | PWA (Digio-based, minimal steps) |
| Disbursement | Confirmation of credit | WhatsApp/SMS |
| Repayment | EMI due reminders, auto-debit confirmation | WhatsApp |
| Support | Escalation to human | WhatsApp + agent callback, always available |

### 5.4 UX requirements (binding, not optional)

- Marathi and Hindi as first-class languages, English optional — including
  numeral and date formatting conventions, not just string translation.
- Anchor's name/logo displayed prominently alongside (not subordinate to)
  the platform's own branding on borrower-facing surfaces — borrowed trust
  is a deliberate design lever.
- One decision per screen maximum on the PWA — no combined "compare +
  adjust + read T&C + confirm" screens.
- A visible human-fallback affordance (call/WhatsApp the assigned Field
  Agent) present on every borrower-facing screen.
- "Lite mode" performance target: usable on 3G, degrades gracefully, caches
  in-progress form state client-side so a dropped connection doesn't lose
  borrower input.

### 5.5 Backend implication

The Borrower Role Profile (§4.1) applies identically regardless of which
channel (WhatsApp bot backend, PWA, or Field Agent proxy action) originates
the request — all channels authenticate against the same Frappe
session/permission layer. WhatsApp bot backend should be implemented as its
own thin service (`whatsapp_adapter` app) translating WhatsApp webhook
payloads into authenticated Frappe API calls, never bypassing the
permission layer.

## 6. OCEN 4.0 Integration Adapter (`ocen_connector`) — Detailed Spec

### 6.1 Design constraint

OCEN 4.0 APIs are fully asynchronous: every request carries a `requestId`,
generates an immediate acknowledgement, and the actual result arrives later
via webhook or polling. The adapter must be built as a durable async state
machine, not a synchronous request/response wrapper.

### 6.2 DocTypes to implement

- **OCEN Participant** — LA credentials, registered product networks,
  subscribed lender list.
- **OCEN Loan Application** — linked 1:1 to `los_engine`'s Loan Application;
  stores `requestId`, `application_id`, current OCEN journey stage enum.
- **OCEN Offer** — many-per-application, one per responding lender; stores
  `offer_id`, `lender_id`, amount, rate, tenure, processing fee, CGTMSE flag.
- **OCEN Request Log** — every outbound call and inbound response/webhook,
  timestamped, for audit and debugging of async flows.

### 6.3 Stages to implement

1. **Loan Application submission** — `POST /v4/loanApplications`; webhook
   listener updates OCEN Loan Application stage on `loanApplicationStatus`
   callback.
2. **Offer generation** — webhook/poll for `offerResponse` per lender;
   populate OCEN Offer records; surface in Lender-comparison UI for
   borrower.
3. **Offer acceptance → disbursement** — five API groups: KYC completion,
   loan agreement receipt/OTP acceptance, loan status updates, repayment
   plan finalization (e-NACH), disbursement trigger confirmation.

### 6.4 Auth

OAuth2 client credentials against the OCEN Registry; token refresh; request
signing (JWS, per OCEN spec). Store credentials in a Frappe `OCEN Settings`
singleton doctype using Frappe's encrypted Password field type — never in
plaintext config.

### 6.5 Sandbox

Test against the OCEN sandbox environment before any production credential
is used. Confirm current sandbox access/credentials with the founder before
starting this module.

## 7. Account Aggregator (AA) Consent Integration

- Use a hosted AA SDK (Setu or Perfios — confirm which is contractually
  finalized before building; open question, §10).
- Consent flow: borrower (or Field Agent on their behalf, per §4.3 proxy
  pattern) is redirected to/embedded with the AA provider's hosted consent
  URL; callback triggers fetch of bank statement / GST data from FIPs.
- Store consent artefacts in an `AA Consent` doctype linked to the borrower
  record; this consent record is also the audit trail for DPDP Act
  compliance.
- Fetched AA data feeds both: (a) the OCEN `loanApplication` payload as the
  consent artefact, and (b) `ddp_engine`'s Trust Graph ingestion pipeline —
  per §3.6, `ddp_engine` forwards this data via REST/event bus, does not
  process it in-process.

## 8. Non-Functional Requirements

- **Compliance:** DPDP Act 2023/Rules 2025 — consent architecture, Data
  Principal rights (access/correction/erasure), Rule 6 security safeguards,
  and breach notification logic must be designed in, not bolted on. RBI
  Digital Lending Directions 2025 — no pooled repayment account;
  disbursement/repayment flows must route direct lender-to-borrower.
- **Auditability:** every OCEN API call, every AA consent event, every
  proxy action by a Field Agent must be logged with actor, timestamp, and
  target record — this is both a regulatory requirement and a
  dispute-resolution necessity.
- **Localization:** Marathi and Hindi are first-class, not afterthought
  translations, on all borrower-facing surfaces.
- **Performance (borrower channels only):** PWA must function on 3G with
  graceful degradation; WhatsApp is the fallback for any borrower without
  reliable data connectivity.
- **Extensibility:** new DocType fields, new roles, and new permission rules
  should be addable via Frappe's native metadata/UI configuration wherever
  possible, without requiring a code deploy.

## 9. Phased Build Plan

**Phase 1 — Foundation (4–6 weeks)**
`identity_core` app; Role Profiles and permission matrix from §4; Frappe CRM
fork/extension for anchor + vendor pipelines; basic LOS doctypes on Frappe
Lending v16.

**Phase 2 — OCEN adapter (6–8 weeks)**
`ocen_connector` full build per §6; test against OCEN sandbox; async state
machine, webhook handling, offer comparison data model.

**Phase 3 — AA + DDP (4–6 weeks)**
AA SDK integration per §7; `ddp_engine` adapter (respecting the IP boundary
in §3.6); Trust Graph data ingestion pipeline (scoring algorithm itself out
of scope for this Frappe build).

**Phase 4 — Frontend builds** (parallel-able with Phase 2/3, staggered by
role)
Field Agent PWA first (simplest, most form-heavy — used as the
pattern-proving spike for frapkit vs. custom renderer, §3.5). Then Lender
Dashboard, Ops Console, Anchor Admin portal, and the Borrower experience
(§5) last, since it has the most distinct, non-standard UX requirements.

**Phase 5 — WhatsApp integration**
`whatsapp_adapter` service; webhook-to-Frappe-API translation layer;
template registration with Meta; cost monitoring given the October 2026
pricing policy change.

## 10. Open Questions Requiring Founder Decision

Tracked as ADRs in `docs/decisions/`; status noted here.

1. ~~**[BLOCKING]** Does this Frappe-based architecture replace, subset, or
   run parallel to the existing Fineract/Temporal/GoRules/Redpanda
   architecture?~~ **Resolved** — full pivot. See
   `docs/decisions/0001-frappe-full-pivot.md`.
2. ~~Frappe Lending v16 as LOS core, vs. thin tracking layer over Fineract,
   vs. fully custom doctypes?~~ **Resolved** — Frappe Lending v16 (§3.4).
3. Site-per-lender-tenant: confirmed as the model, but which lenders in the
   near-term pipeline actually require this vs. would accept pooled tenancy
   with strong row-level isolation? **Open.**
4. Setu vs. Perfios as the AA SDK provider — which is
   contractually/technically finalized? **Open.**
5. Frapkit vs. custom metadata renderer — resolve via the Field Agent app
   spike before committing across all role-fronts. **Open, deferred to
   Phase 4.**
6. Where does the Trust Graph scoring algorithm actually live — inside
   `ddp_engine` as a thin proprietary adapter, or as a fully separate
   non-Frappe service communicating via REST/event bus? **Open** — default
   to fully separate per §3.6 until decided otherwise.
7. WhatsApp Business API provider (Twilio noted as under evaluation) —
   confirm current status and cost model before Phase 5 starts. **Open.**
