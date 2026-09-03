# ADR 0004: Frappe Lending's real setup depth

**Status:** Accepted; superseded in part 2026-09-03 (see Update below) —
this is a POC, and the founder directed proceeding past the compliance
question with a clearly-labeled placeholder rather than blocking on it.
**Date:** 2026-09-03

## Context

Continuing Phase 1 testing (ADR 0003), `LoanLead.convert_to_application()`
was exercised end-to-end against the live dev bench for the first time.
This surfaced a chain of real prerequisites Frappe Lending's `Loan
Application` needs that nothing in the spec or the original scaffold
anticipated:

1. `Tenant` (identity_core) was missing its `lft`/`rgt`/`old_parent`
   nested-set DB columns despite `is_tree: 1` in the doctype JSON — fixed
   by declaring those fields explicitly (Frappe only auto-injects them when
   a DocType is saved through the full Document lifecycle, e.g. via the
   Desk UI; a JSON-file-based doctype sync, which is how a git-tracked app
   installs, doesn't trigger that).
2. `Loan Application.applicant_type` defaults to `"Customer"`, and its
   `before_save()` auto-creates a linked ERPNext `Customer` — needing
   `applicant_name`/`applicant_phone_number`/`applicant_email_address`.
   `Loan Lead` didn't capture these; added them (§ fix, this session).
3. `Loan Application.company` and `.loan_product` are both mandatory, and
   this bench had **zero** `Company` or `Loan Product` records — ERPNext's
   setup wizard, which normally seeds these plus Warehouse Types, UOMs,
   Fiscal Year, and Chart of Accounts, was never run (headless
   `bench get-app`/`install-app` bootstrap, not the Desk UI onboarding
   flow). A bare `Company` insert failed immediately
   (`LinkValidationError: Could not find Warehouse Type: Transit`) because
   `Company.on_update()` assumes those presets already exist.
4. Fixed by routing through ERPNext's own programmatic setup-wizard
   completion function (`erpnext.setup.setup_wizard.setup_wizard.
   setup_complete`) instead of a bare insert — this runs fixtures → company
   → defaults in the right order. Exposed as
   `los_engine.los_engine.setup.bootstrap_default_company_and_product()`,
   deliberately **not** wired as an automatic `after_install` hook —
   silently fabricating a real company's legal name/currency/country on
   every fresh install without a human confirming those details is the
   wrong default for something this consequential.
5. Even past that, `Loan Product` itself requires
   `collection_offset_sequence_for_standard_asset` and
   `..._for_sub_standard_asset` — Links to a "Loan Demand Offset Sequence"
   governing how a delinquent loan's payments get allocated across
   principal/interest/penalty, mapped to RBI IRAC asset-classification
   tiers (Standard / Sub-Standard / Doubtful / Loss).

## Decision

**Stop here, deliberately, rather than fabricate #5.** Items 1-4 were code
bugs or missing-but-mechanical setup — fixed and verified live. Item 5 is
not: it's a real collection-policy decision for this venture's lending/
credit/compliance function, not something a coding agent should invent a
plausible-looking value for. A wrong guess wouldn't just be a bug, it would
silently encode an NPA collection policy nobody actually decided on, in a
regulated financial product.

`bootstrap_default_company_and_product()` correctly creates the Company
(fully, via the real setup wizard — this part is genuinely done) and then
fails with Frappe Lending's own clear `ValidationError` when it reaches the
Loan Product step. That failure is left as-is, not caught and re-wrapped,
so the real Frappe error (naming the exact missing field) reaches whoever
runs it next.

## What this means for Phase 1's status

`LoanLead.run_eligibility_check()` and the Ineligible/Eligible status
machinery are fully implemented and verified end-to-end against the live
bench, including the anchor-attestation check calling into
`crm_extensions`. `convert_to_application()` is implemented correctly for
everything within los_engine/identity_core's control (applicant fields,
company/product references, tenant propagation) — verified up to the exact
point where it now correctly requires real Loan Product configuration that
doesn't exist yet.

**Before Loan Leads can actually convert to live Loan Applications**, someone
with lending/credit/compliance authority needs to define:
- The Loan Demand Offset Sequences for at least the Standard and
  Sub-Standard asset tiers (and realistically Doubtful/Loss too, before
  going live).
- Real Loan Product terms (interest rate, tenure, fees) to replace the
  18%/term-loan placeholder in `setup.py`.
- Real Company details to replace "Project K" placeholder before this
  leaves a dev bench.

This is not a small residual task — it's a distinct, regulated-product
configuration exercise that belongs with the people who own compliance for
this venture, not something to complete inside a coding session.

## Update 2026-09-03: unblocked for POC with a clearly-labeled placeholder

Founder direction: this is a POC, note compliance questions rather than
block on them. `_ensure_poc_offset_order()` in `los_engine/setup.py` now
creates a single `Loan Demand Offset Order` (EMI → Additional Interest →
Penalty → Charges — no basis beyond "unblocks the POC"), titled
`"POC-ONLY Collection Offset Order — NOT a real collection policy"` so it
reads as a placeholder even from the Desk UI, and applies it to both the
Standard and Sub-Standard asset tiers. The open question itself moved to
`docs/compliance-questions.md` #1, tracked rather than dropped.

`LoanLead.convert_to_application()` is now verified working **fully
end-to-end** against the live dev bench: Loan Lead → eligibility check →
Loan Application creation → auto-created applicant `Customer`, using this
POC placeholder plus a `Loan Application.repayment_periods` fix (the same
default-value gotcha as `applicant_type` — `repayment_method` defaults to
`"Repay Over Number of Periods"`, which then requires
`repayment_periods`; added `Loan Lead.requested_tenure_months`, falling
back to 12 months, to supply it).

Real Loan Product terms, real Company details, and — most importantly —
real RBI IRAC collection-offset sequences are all still needed before this
leaves POC. Nothing above should be read as those decisions having been
made; it's the minimum to make the POC's happy path actually run.
