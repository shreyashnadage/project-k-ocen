# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document

from identity_core.utils.proxy_action import stamp_proxy_action

# Placeholder product bounds matching the spec's own framing of the
# borrower population ("a borrower taking a ₹2-10 lakh loan", §3.2B).
# Real bounds belong in per-lender product config once that exists — this
# is a pre-screening sanity check, not a credit decision (see the D0-D3
# note below).
MIN_LOAN_AMOUNT = 200_000
MAX_LOAN_AMOUNT = 1_000_000


class LoanLead(Document):
	def before_insert(self):
		stamp_proxy_action(self)

	def before_save(self):
		stamp_proxy_action(self)

	def run_eligibility_check(self) -> str:
		"""Pre-screening only — explicitly NOT the lender's underwriting
		decision (spec §1.4, §2.2: the platform's decisioning stops at
		pre-screening/eligibility, the D4 credit-sanction gate belongs to the
		lender and is out of scope here). Deterministic checks in the spirit
		of the retired Fineract scaffold's GoRules D0-D3 gates (ADR 0001) —
		this is a first pass, not a port of that logic.

		Sets status to Eligible or Ineligible and records why in
		eligibility_notes. Safe to re-run; re-evaluates from current field
		values each time.
		"""
		if self.status in ("Converted", "Dropped"):
			frappe.throw(f"Cannot run an eligibility check on a {self.status} lead.")

		reasons = []

		if not self.tenant_id:
			reasons.append("No tenant/cluster set.")
		elif frappe.db.get_value("Tenant", self.tenant_id, "status") != "Active":
			reasons.append(f"Tenant {self.tenant_id} is not Active.")

		if not self.requested_amount:
			reasons.append("No requested amount set.")
		elif not (MIN_LOAN_AMOUNT <= self.requested_amount <= MAX_LOAN_AMOUNT):
			reasons.append(
				f"Requested amount {self.requested_amount} is outside the "
				f"₹{MIN_LOAN_AMOUNT:,}–₹{MAX_LOAN_AMOUNT:,} band."
			)

		if self.vendor_lead:
			anchor = frappe.db.get_value("CRM Lead", self.vendor_lead, "anchor")
			if not anchor:
				reasons.append(f"Vendor lead {self.vendor_lead} has no anchor set.")
			else:
				confirmed = frappe.db.exists(
					"Vendor Attestation",
					{
						"anchor": anchor,
						"vendor_lead": self.vendor_lead,
						"attestation_status": "Confirmed",
					},
				)
				if not confirmed:
					reasons.append(
						f"No Confirmed Vendor Attestation from anchor {anchor} for "
						f"vendor lead {self.vendor_lead} — anchor-led financing "
						"requires the anchor to confirm the vendor relationship "
						"(spec §1.2)."
					)

		if reasons:
			self.status = "Ineligible"
			self.eligibility_notes = "\n".join(reasons)
		else:
			self.status = "Eligible"
			self.eligibility_notes = "All pre-screening checks passed."

		self.save(ignore_permissions=True)
		return self.status

	def convert_to_application(self) -> str:
		"""Create the Frappe Lending Loan Application this lead graduates
		into, per spec §9 Phase 1 ("basic LOS doctypes on Frappe Lending
		v16"). Eligibility-gate logic (the D0-D3-style pre-screening the
		platform is allowed to do, short of the lender's D4 underwriting
		decision — spec §1.4, §2.2) belongs here, not in the Frappe Lending
		doctype itself.
		"""
		if self.status != "Eligible":
			frappe.throw("Only an Eligible Loan Lead can be converted to a Loan Application.")
		if self.loan_application:
			frappe.throw(f"Already converted to {self.loan_application}.")
		if not self.applicant_name:
			frappe.throw("Applicant Name is required before converting to a Loan Application.")

		# Import path is los_engine.los_engine.setup, not los_engine.setup —
		# this app nests everything one level under the "los_engine" module
		# subfolder (apps/los_engine/los_engine/los_engine/...), unlike
		# crm_extensions/identity_core which don't. Got this wrong twice
		# already for doc_events before settling on the right depth; do not
		# "fix" it back to the shallower path without checking the actual
		# directory structure first.
		from los_engine.los_engine.setup import get_default_company_and_product

		defaults = get_default_company_and_product()

		application = frappe.get_doc(
			{
				"doctype": "Loan Application",
				"loan_lead": self.name,
				"tenant_id": self.tenant_id,
				"loan_amount": self.requested_amount,
				"company": defaults["company"],
				"loan_product": defaults["loan_product"],
				"applicant_type": "Customer",
				"applicant_name": self.applicant_name,
				"applicant_phone_number": self.applicant_phone_number,
				"applicant_email_address": self.applicant_email_address,
				"posting_date": frappe.utils.today(),
				"is_term_loan": 1,
				"repayment_method": "Repay Over Number of Periods",
				"repayment_periods": self.requested_tenure_months or 12,
			}
		)
		application.insert(ignore_permissions=True)

		self.db_set("loan_application", application.name)
		self.db_set("status", "Converted")
		return application.name
