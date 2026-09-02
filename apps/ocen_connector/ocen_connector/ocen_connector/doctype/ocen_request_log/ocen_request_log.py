# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.model.document import Document


class OCENRequestLog(Document):
	def before_insert(self):
		if not self.logged_at:
			self.logged_at = frappe.utils.now_datetime()

	@staticmethod
	def record(
		direction: str,
		endpoint: str,
		request_id: str | None = None,
		ocen_loan_application: str | None = None,
		http_status: int | None = None,
		payload: dict | None = None,
		response_payload: dict | None = None,
		error: str | None = None,
	) -> "OCENRequestLog":
		doc = frappe.get_doc(
			{
				"doctype": "OCEN Request Log",
				"direction": direction,
				"endpoint": endpoint,
				"request_id": request_id,
				"ocen_loan_application": ocen_loan_application,
				"http_status": http_status,
				"payload": frappe.as_json(payload) if payload is not None else None,
				"response_payload": frappe.as_json(response_payload)
				if response_payload is not None
				else None,
				"error": error,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc
