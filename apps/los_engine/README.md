# los_engine

LOS core. Per the resolved §3.4 decision, this is a **thin extension over
Frappe Lending v16** (the `lending` app), not a reimplementation — do not
create a competing `Loan Application` doctype here.

## What this app owns

- **Loan Lead** (`los_engine/doctype/loan_lead`) — the pre-application stage
  Frappe Lending doesn't model: a vendor's expression of interest and
  eligibility pre-screening before a formal Loan Application exists.
  `LoanLead.run_eligibility_check()` is the platform's pre-screening gate,
  short of the lender's D4 underwriting decision (spec §1.4, §2.2) —
  checks tenant is Active, requested amount is within the (placeholder)
  product band, and — since this is anchor-led financing — that the anchor
  has a Confirmed Vendor Attestation for this vendor (spec §1.2). Sets
  status to Eligible/Ineligible and records why in `eligibility_notes`. A
  first pass, not a port of the Fineract scaffold's GoRules D0–D3 gates —
  those remain a useful reference for shape even though that runtime is
  retired (ADR 0001). `convert_to_application()` still requires status =
  Eligible before creating the Loan Application.
- **Custom Field fixtures on Loan Application** (`fixtures/custom_field.json`):
  `loan_lead` (back-link), `tenant_id` (row-level isolation, §3.2B),
  `performed_by_agent` (proxy-action stamp, §4.3), `fldg_flag` (mutual
  exclusivity with CGTMSE, §1.4 — checked in `ocen_connector`'s OCEN Offer
  controller).
- **doc_events on Loan Application** (`los_engine/doc_events/loan_application.py`)
  — proxy-action stamping and tenant_id propagation from the linked Loan
  Lead. Wired via Frappe's `doc_events` hook rather than a controller
  override, since Loan Application belongs to the `lending` app, not this
  one.

- **doc_events on CRM Lead** (`los_engine/doc_events/crm_lead.py`) — the
  vendor lead → Loan Lead handoff: auto-creates a `Loan Lead` (status
  `New`, `requested_amount`/applicant fields left blank for a Field Agent
  to fill in) when a `CRM Lead` reaches Frappe CRM's built-in `Qualified`
  status. Idempotent (won't create a second one on a later save), and
  safely skips (logs a warning, doesn't crash the CRM Lead's own save) if
  `tenant_id` isn't set yet, since that's mandatory on Loan Lead. Requires
  `crm` (upstream Frappe CRM) — added to `required_apps` for this reason.
- **setup.py** (`los_engine/setup.py`) — `bootstrap_default_company_and_product()`,
  a whitelisted, explicitly-called (never automatic) function that
  provisions the ERPNext `Company` + Frappe Lending `Loan Product` that
  `Loan Application` cannot be created without. Goes through ERPNext's own
  setup-wizard completion function rather than a bare insert — see ADR
  0004 for why a bare insert doesn't work on a headlessly-installed bench.

## Requires

`identity_core` (Tenant, proxy-action helper), `lending` (Frappe Lending
v16), and `crm` (upstream Frappe CRM — the vendor lead → Loan Lead
handoff listens for its `CRM Lead` doctype). Install all three on the
bench before `los_engine`.

## Verified end-to-end against the live dev bench (ADR 0003, ADR 0004)

The full flow — Loan Lead creation → `run_eligibility_check()`
(Ineligible/Eligible transitions, the anchor Vendor Attestation check) →
`convert_to_application()` (blocked for non-Eligible leads;
succeeds for Eligible ones, creating a real Frappe Lending `Loan
Application` with its applicant `Customer` auto-created correctly) — is
confirmed working, using the POC-only placeholder Company/Loan
Product/collection-offset-order from `setup.py`. See ADR 0004's update and
`docs/compliance-questions.md` before touching those placeholders.

## Not yet built

- Real per-lender product bounds for the eligibility check (currently a
  hardcoded ₹2–10 lakh placeholder band, `MIN_LOAN_AMOUNT`/
  `MAX_LOAN_AMOUNT` in `loan_lead.py`).
- Real Loan Demand Offset Sequences, Loan Product terms, Company details,
  and loan tenure defaults to replace the POC placeholders in `setup.py`
  and `loan_lead.py` (ADR 0004, `docs/compliance-questions.md`) — needs
  lending/credit/compliance input, not more coding.
- The `CRM Lead` doctype `vendor_lead` links to is owned by the
  `crm_extensions` app (extending upstream Frappe CRM) — see that app's
  README.
