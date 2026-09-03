# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document


class OCENOffer(Document):
	def validate(self):
		if not self.cgtmse_flag:
			return

		# CGTMSE and FLDG are mutually exclusive on the same underlying loan
		# (spec §1.4). Prior to ADR 0005 this queried los_engine's Loan
		# Application directly, in-process — impossible now that OCEN runs
		# on its own site. fldg_flag is mirrored onto OCEN Loan Application
		# at submission time (ocen_connector.api.integration), and this
		# checks that local mirror instead.
		fldg_flag = frappe.db.get_value(
			"OCEN Loan Application", self.ocen_loan_application, "fldg_flag"
		)
		if fldg_flag:
			frappe.throw(
				"This loan already has FLDG credit enhancement. CGTMSE and FLDG "
				"cannot co-exist on the same loan (spec §1.4)."
			)
