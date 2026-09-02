# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document


class VendorAttestation(Document):
	def before_save(self):
		if self.attestation_status == "Confirmed" and not self.attested_on:
			self.attested_on = frappe.utils.now_datetime()
