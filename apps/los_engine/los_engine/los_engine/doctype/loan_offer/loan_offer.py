# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document


class LoanOffer(Document):
	def before_insert(self):
		if not self.tenant_id and self.loan_application:
			self.tenant_id = frappe.db.get_value("Loan Application", self.loan_application, "tenant_id")
