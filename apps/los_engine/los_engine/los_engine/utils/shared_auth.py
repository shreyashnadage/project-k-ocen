# Copyright (c) 2026, Project K
# License: MIT
"""
LOS side of the shared-secret auth for the LOS <-> OCEN channel (ADR 0005).
See ocen_connector/utils/shared_auth.py's docstring for why this replaced
Frappe's own User api_key/api_secret mechanism for this specific channel.
"""

import hmac

import frappe

HEADER_NAME = "X-Integration-Secret"


def require_shared_secret(request) -> None:
	settings = frappe.get_single("OCEN Integration Settings")
	expected = settings.get_password("integration_shared_secret", raise_exception=False)
	if not expected:
		frappe.throw(
			"integration_shared_secret is not configured in OCEN Integration Settings.",
			frappe.PermissionError,
		)

	provided = request.headers.get(HEADER_NAME)
	if not provided or not hmac.compare_digest(provided.encode(), expected.encode()):
		frappe.throw("Invalid or missing integration secret.", frappe.PermissionError)
