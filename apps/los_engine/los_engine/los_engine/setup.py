# Copyright (c) 2026, Project K
# License: MIT
"""
Import path: los_engine.los_engine.setup (this file lives at
apps/los_engine/los_engine/los_engine/setup.py — one level deeper than
identity_core/crm_extensions's equivalents, matching this app's doc_events
convention).

Frappe Lending's Loan Application cannot be created at all without a
Company and at least one Loan Product — this was discovered by actually
trying to convert a Loan Lead, not documented anywhere upfront (ADR 0003
follow-up). Company/Loan Product are ERPNext/Lending accounting-setup
records, not the business-process "company entity registration" the spec
excludes from build scope (§2.2) — those are two different things sharing
a confusing name.

Deliberately NOT wired as an `after_install` hook: silently fabricating a
Company record (legal name, currency, country) on every fresh install
without a human confirming those details is the wrong default for
something this consequential. Call `bootstrap_default_company_and_product`
explicitly (Desk console, or a future setup-wizard step) instead, and
replace the placeholder values below with the real ones before relying on
this in anything beyond a dev bench.

This also includes a POC-ONLY placeholder Loan Demand Offset Order for
Loan Product's mandatory collection-offset-sequence fields (RBI IRAC asset
classification collection policy) — tracked as an open decision in
docs/compliance-questions.md #1, not silently treated as settled. Building
this POC intentionally proceeds past that open question rather than
blocking on it (founder direction); real values are still needed before
anything here leaves POC.

Company creation goes through ERPNext's own setup-wizard completion
function (`erpnext.setup.setup_wizard.setup_wizard.setup_complete`), not a
bare `frappe.get_doc({"doctype": "Company", ...}).insert()` — a bare
insert was tried first and failed (`LinkValidationError: Could not find
Warehouse Type: Transit`), because `Company.on_update()` assumes the
country-specific preset fixtures (Warehouse Types, UOMs, Fiscal Year,
Chart of Accounts, ...) that the setup wizard normally seeds are already
there. This bench skipped the wizard entirely (headless install), so
nothing had seeded them. `setup_complete()` runs fixtures → company →
defaults in the correct order and handles all of that.
"""

import frappe

PLACEHOLDER_COMPANY = "Project K"
PLACEHOLDER_COMPANY_ABBR = "PK"
PLACEHOLDER_LOAN_PRODUCT = "Vendor Receivables Financing"
POC_OFFSET_ORDER_TITLE = "POC-ONLY Collection Offset Order — NOT a real collection policy"


@frappe.whitelist()
def bootstrap_default_company_and_product() -> dict:
	"""Idempotent. Returns {"company": ..., "loan_product": ...}. Safe to
	call repeatedly — does nothing if the records already exist.
	"""
	frappe.only_for("System Manager")

	company_name = _ensure_company()
	product_name = _ensure_loan_product(company_name)
	return {"company": company_name, "loan_product": product_name}


def _ensure_company() -> str:
	existing = frappe.db.exists("Company", {"company_name": PLACEHOLDER_COMPANY})
	if existing:
		return existing

	from erpnext.setup.setup_wizard.setup_wizard import setup_complete

	current_year = frappe.utils.today()[:4]
	setup_complete(
		frappe._dict(
			{
				"company_name": PLACEHOLDER_COMPANY,
				"company_abbr": PLACEHOLDER_COMPANY_ABBR,
				"currency": "INR",
				"country": "India",
				"fy_start_date": f"{current_year}-04-01",
				"fy_end_date": f"{int(current_year) + 1}-03-31",
				"chart_of_accounts": "Standard",
				"domain": "Services",
				"language": "English",
			}
		)
	)
	return frappe.db.exists("Company", {"company_name": PLACEHOLDER_COMPANY})


def _ensure_poc_offset_order() -> str:
	"""POC-ONLY placeholder, not a real collection policy — see
	docs/compliance-questions.md #1. Real values need lending/credit/
	compliance sign-off before this leaves POC (ADR 0004). Uses a plain
	EMI-first-then-Charges ordering with no basis beyond "something that
	lets the POC create a Loan Application" — do not treat this as
	representing any actual decision about how Project K will sequence
	collections against principal/interest/penalty for delinquent loans.
	"""
	existing = frappe.db.exists("Loan Demand Offset Order", {"title": POC_OFFSET_ORDER_TITLE})
	if existing:
		return existing

	order = frappe.get_doc(
		{
			"doctype": "Loan Demand Offset Order",
			"title": POC_OFFSET_ORDER_TITLE,
			"components": [
				{"demand_type": "EMI (Principal + Interest)"},
				{"demand_type": "Additional Interest"},
				{"demand_type": "Penalty"},
				{"demand_type": "Charges"},
			],
		}
	)
	order.insert(ignore_permissions=True)
	return order.name


def _ensure_loan_product(company_name: str) -> str:
	"""Uses the POC-ONLY offset order above for both the standard and
	sub-standard asset tiers — see docs/compliance-questions.md #1 and ADR
	0004. Replace with real, distinct sequences per tier before this leaves
	POC; do not read anything into the fact both tiers currently point at
	the same placeholder.
	"""
	existing = frappe.db.exists(
		"Loan Product", {"product_name": PLACEHOLDER_LOAN_PRODUCT, "company": company_name}
	)
	if existing:
		return existing

	offset_order = _ensure_poc_offset_order()

	product = frappe.get_doc(
		{
			"doctype": "Loan Product",
			"product_code": "VRF-001",
			"product_name": PLACEHOLDER_LOAN_PRODUCT,
			"company": company_name,
			"rate_of_interest": 18.0,
			"is_term_loan": 1,
			"collection_offset_sequence_for_standard_asset": offset_order,
			"collection_offset_sequence_for_sub_standard_asset": offset_order,
		}
	)
	product.insert(ignore_permissions=True)
	return product.name


def get_default_company_and_product() -> dict:
	"""Read-only lookup used by LoanLead.convert_to_application(). Raises a
	clear error rather than silently bootstrapping mid-transaction — an
	admin must run bootstrap_default_company_and_product() first.
	"""
	company = frappe.db.exists("Company", {"company_name": PLACEHOLDER_COMPANY})
	product = (
		frappe.db.exists("Loan Product", {"product_name": PLACEHOLDER_LOAN_PRODUCT, "company": company})
		if company
		else None
	)
	if not company or not product:
		frappe.throw(
			"No default Company/Loan Product configured. An admin must run "
			"los_engine.los_engine.setup.bootstrap_default_company_and_product() "
			"(or set up real ones) before Loan Leads can be converted."
		)
	return {"company": company, "loan_product": product}
