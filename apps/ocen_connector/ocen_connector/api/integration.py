# Copyright (c) 2026, Project K
# License: MIT
"""
Inbound API for the LOS site to call (ADR 0005) — the counterpart to
ocen_connector/utils/los_client.py's outbound calls. This is where a Loan
Application enters the OCEN world: creates the OCEN Loan Application
record here, generates the requestId, and (once Phase 2's real outbound
OCEN network calls are built) would kick off `POST /v4/loanApplications`
against the actual OCEN Registry — not implemented yet, this only records
local state and returns a requestId for LOS to track.

Authenticated via a pre-shared secret (allow_guest=True + shared_auth's
own check), not Frappe's User api_key/api_secret — see utils/shared_auth.py's
docstring for why.
"""

import uuid

import frappe

from ocen_connector.ocen_connector.doctype.ocen_request_log.ocen_request_log import (
	OCENRequestLog,
)
from ocen_connector.utils.shared_auth import require_shared_secret


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_loan_application(
	loan_application: str,
	tenant_code: str | None = None,
	loan_amount: float | None = None,
	fldg_flag: bool = False,
) -> dict:
	"""Called by LOS (los_engine.api.ocen_integration.submit_to_ocen) when a
	Loan Application is ready to enter the OCEN flow. Idempotent per
	loan_application — calling again for one already submitted returns the
	existing record rather than creating a duplicate.
	"""
	require_shared_secret(frappe.request)

	existing = frappe.db.get_value("OCEN Loan Application", {"loan_application": loan_application}, "name")
	if existing:
		doc = frappe.get_doc("OCEN Loan Application", existing)
		return {"ocen_loan_application": doc.name, "request_id": doc.request_id, "ocen_stage": doc.ocen_stage}

	request_id = str(uuid.uuid4())

	doc = frappe.get_doc(
		{
			"doctype": "OCEN Loan Application",
			"loan_application": loan_application,
			"tenant_code": tenant_code,
			"fldg_flag": bool(fldg_flag),
			"request_id": request_id,
			"ocen_stage": "Draft",
		}
	)
	doc.insert(ignore_permissions=True)

	self_participant = frappe.db.get_value("OCEN Participant", {"is_self": 1}, "name")
	if self_participant:
		doc.db_set("participant", self_participant)

	OCENRequestLog.record(
		direction="Outbound",
		endpoint="loanApplications (local record only — real OCEN network call not yet built)",
		request_id=request_id,
		ocen_loan_application=doc.name,
		payload={"loan_application": loan_application, "tenant_code": tenant_code, "loan_amount": loan_amount},
	)

	# TODO (Phase 2, spec §6.3 stage 1): actually call POST /v4/loanApplications
	# against the real OCEN Registry here using OCENSettings.get_access_token()
	# and .sign_request(). Until then, ocen_stage stays "Draft" rather than
	# advancing to "Submitted" — it would be misleading to claim a stage this
	# adapter hasn't actually reached with the network yet.

	return {"ocen_loan_application": doc.name, "request_id": request_id, "ocen_stage": doc.ocen_stage}
