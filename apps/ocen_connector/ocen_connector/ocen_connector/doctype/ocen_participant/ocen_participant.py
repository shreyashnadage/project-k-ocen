# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document


class OCENParticipant(Document):
	def validate(self):
		if self.is_self:
			existing_self = frappe.db.exists(
				"OCEN Participant", {"is_self": 1, "name": ("!=", self.name)}
			)
			if existing_self:
				frappe.throw(
					f"Another OCEN Participant ({existing_self}) is already marked as "
					"is_self. Only one participant record may represent this "
					"platform's own LA identity."
				)
