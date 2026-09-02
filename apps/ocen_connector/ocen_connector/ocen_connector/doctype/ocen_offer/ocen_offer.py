# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document


class OCENOffer(Document):
	def validate(self):
		if not self.cgtmse_flag:
			return

		loan_application = frappe.db.get_value(
			"OCEN Loan Application", self.ocen_loan_application, "loan_application"
		)
		if not loan_application or not frappe.db.exists("Loan Application", loan_application):
			return

		# CGTMSE and FLDG are mutually exclusive on the same underlying loan
		# (spec §1.4). los_engine's Loan Application is expected to expose an
		# `fldg_flag` field once its credit-enhancement fields are built out —
		# guard defensively in case that field doesn't exist yet.
		meta = frappe.get_meta("Loan Application")
		if meta.has_field("fldg_flag"):
			if frappe.db.get_value("Loan Application", loan_application, "fldg_flag"):
				frappe.throw(
					"This loan already has FLDG credit enhancement. CGTMSE and FLDG "
					"cannot co-exist on the same loan (spec §1.4)."
				)
