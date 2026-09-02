# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document

from identity_core.utils.proxy_action import stamp_proxy_action


class LoanLead(Document):
	def before_insert(self):
		stamp_proxy_action(self)

	def before_save(self):
		stamp_proxy_action(self)

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

		application = frappe.get_doc(
			{
				"doctype": "Loan Application",
				"loan_lead": self.name,
				"tenant_id": self.tenant_id,
				"loan_amount": self.requested_amount,
			}
		)
		application.insert(ignore_permissions=True)

		self.db_set("loan_application", application.name)
		self.db_set("status", "Converted")
		return application.name
