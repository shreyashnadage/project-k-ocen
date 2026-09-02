# los_engine

LOS core. Per the resolved §3.4 decision, this is a **thin extension over
Frappe Lending v16** (the `lending` app), not a reimplementation — do not
create a competing `Loan Application` doctype here.

## What this app owns

- **Loan Lead** (`los_engine/doctype/loan_lead`) — the pre-application stage
  Frappe Lending doesn't model: a vendor's expression of interest and
  eligibility pre-screening before a formal Loan Application exists.
  `LoanLead.convert_to_application()` is where eligibility-gate logic
  belongs (the platform's pre-screening, short of the lender's D4
  underwriting decision — spec §1.4, §2.2). That gate logic itself is not
  built yet; the Fineract scaffold's GoRules D0–D3 gate definitions are a
  useful reference for its shape even though that runtime is retired (ADR
  0001).
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

## Requires

`identity_core` (Tenant, proxy-action helper) and `lending` (Frappe Lending
v16 — install this app on the bench before `los_engine`).

## Not yet built

- Eligibility-gate logic in `LoanLead.convert_to_application()` (currently
  just moves data across, no actual eligibility checks).
- The `CRM Lead` doctype `vendor_lead` links to is owned by the `crm` app —
  see that app's README for its (also not yet built) state.
