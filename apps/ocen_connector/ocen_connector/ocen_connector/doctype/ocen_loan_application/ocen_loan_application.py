# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document

# Stage transitions considered terminal — once reached, further webhook
# updates should be logged (OCEN Request Log) but not silently overwrite
# the stage. Guards against a late/duplicate webhook resurrecting a
# rejected or disbursed application.
TERMINAL_STAGES = {"Disbursed", "Rejected", "Failed"}


class OCENLoanApplication(Document):
	def before_save(self):
		if self.has_value_changed("ocen_stage"):
			self.last_status_update = frappe.utils.now_datetime()

	def apply_webhook_stage(self, new_stage: str, raw_payload: dict) -> None:
		"""Called by the webhook receivers (ocen_connector.api.webhooks) to move
		this application's stage forward. Refuses to move a terminal-stage
		application, per spec §8 auditability — the attempt is still logged by
		the caller in OCEN Request Log.
		"""
		if self.ocen_stage in TERMINAL_STAGES:
			frappe.log_error(
				title="OCEN webhook after terminal stage",
				message=(
					f"{self.name} is already {self.ocen_stage}; ignoring webhook "
					f"attempt to move it to {new_stage}."
				),
			)
			return

		self.ocen_stage = new_stage
		self.raw_last_webhook_payload = frappe.as_json(raw_payload)
		self.save(ignore_permissions=True)
