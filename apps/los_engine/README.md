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

- **setup.py** (`los_engine/setup.py`) — `bootstrap_default_company_and_product()`,
  a whitelisted, explicitly-called (never automatic) function that
  provisions the ERPNext `Company` + Frappe Lending `Loan Product` that
  `Loan Application` cannot be created without. Goes through ERPNext's own
  setup-wizard completion function rather than a bare insert — see ADR
  0004 for why a bare insert doesn't work on a headlessly-installed bench.

## Requires

`identity_core` (Tenant, proxy-action helper) and `lending` (Frappe Lending
v16 — install this app on the bench before `los_engine`).

## Verified end-to-end against the live dev bench (ADR 0003, ADR 0004)

`run_eligibility_check()`'s Ineligible/Eligible transitions, the anchor
Vendor Attestation check, and `convert_to_application()`'s blocking of
non-Eligible leads are all confirmed working. `convert_to_application()`
itself is implemented correctly for everything in this app's control —
verified up to the point where Frappe Lending's `Loan Product` correctly
demands real collection-policy configuration (RBI IRAC offset sequences)
that doesn't exist yet. That is a genuine business/compliance decision,
not a bug — see ADR 0004 before trying to "fix" it by fabricating values.

## Not yet built

- Real per-lender product bounds for the eligibility check (currently a
  hardcoded ₹2–10 lakh placeholder band, `MIN_LOAN_AMOUNT`/
  `MAX_LOAN_AMOUNT` in `loan_lead.py`).
- Real Loan Demand Offset Sequences, Loan Product terms, and Company
  details to replace the placeholders in `setup.py` (ADR 0004) — needs
  lending/credit/compliance input, not more coding.
- The `CRM Lead` doctype `vendor_lead` links to is owned by the
  `crm_extensions` app (extending upstream Frappe CRM) — see that app's
  README.
