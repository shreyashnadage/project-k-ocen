# Copyright (c) 2026, Project K
# License: MIT
"""
Shared-secret auth for the LOS <-> OCEN site-to-site channel (ADR 0005).

Originally this used Frappe's own User api_key/api_secret mechanism (the
same one Frappe's REST API always uses). That worked correctly for
requests to the LOS site but consistently failed — an unexplained
AuthenticationError — for requests to this (non-default, second) site on
this bench, despite the underlying data being verified correct at every
layer (direct SQL, direct Python reproduction of the exact comparison
logic) — see the extensive debugging trail in this session for the full
account. Rather than depend on unresolved Frappe-core multi-site behavior,
the integration endpoints check a pre-shared secret directly, the same
pattern already used successfully for the OCEN webhook JWS auth. Simpler,
fully within this app's own code, and testable in isolation.
"""

import hmac

import frappe

HEADER_NAME = "X-Integration-Secret"


def require_shared_secret(request) -> None:
	settings = frappe.get_single("OCEN Settings")
	expected = settings.get_password("integration_shared_secret", raise_exception=False)
	if not expected:
		frappe.throw("integration_shared_secret is not configured in OCEN Settings.", frappe.PermissionError)

	provided = request.headers.get(HEADER_NAME)
	if not provided or not hmac.compare_digest(provided.encode(), expected.encode()):
		frappe.throw("Invalid or missing integration secret.", frappe.PermissionError)
