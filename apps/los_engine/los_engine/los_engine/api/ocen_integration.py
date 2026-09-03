# Copyright (c) 2026, Project K
# License: MIT
"""
LOS side of the LOS <-> OCEN REST integration (ADR 0005).

submit_to_ocen() is the outbound half — LOS calling the OCEN site.
receive_ocen_stage_update()/receive_ocen_offer() are the inbound half —
the OCEN site calling back into LOS after processing a real OCEN webhook
(see ocen_connector/utils/los_client.py on the other side). Both inbound
functions are allow_guest=True + shared-secret checked (utils/shared_auth.py)
rather than Frappe User api_key/api_secret — see that module's docstring
for why.
"""

import frappe
import requests

from los_engine.los_engine.utils.shared_auth import HEADER_NAME, require_shared_secret


@frappe.whitelist(methods=["POST"])
def submit_to_ocen(loan_application: str) -> dict:
	"""Hands a Loan Application to the OCEN site. Idempotent on the OCEN
	side (calling again returns the existing OCEN-side record rather than
	duplicating it) — safe to call more than once if a previous attempt's
	response was lost.
	"""
	settings = frappe.get_single("OCEN Integration Settings")
	if not settings.ocen_site_url:
		frappe.throw("OCEN Integration Settings is not configured — set ocen_site_url/integration_shared_secret first.")

	shared_secret = settings.get_password("integration_shared_secret")

	loan_app = frappe.get_doc("Loan Application", loan_application)

	url = f"{settings.ocen_site_url.rstrip('/')}/api/method/ocen_connector.api.integration.submit_loan_application"
	response = requests.post(
		url,
		headers={HEADER_NAME: shared_secret},
		json={
			"loan_application": loan_app.name,
			"tenant_code": loan_app.get("tenant_id"),
			"loan_amount": loan_app.loan_amount,
			"fldg_flag": bool(loan_app.get("fldg_flag")),
		},
		timeout=15,
	)
	response.raise_for_status()
	result = response.json().get("message", {})

	loan_app.db_set("ocen_request_id", result.get("request_id"))
	loan_app.db_set("ocen_stage", result.get("ocen_stage"))

	return result


@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive_ocen_stage_update(loan_application: str, ocen_stage: str) -> None:
	"""Called by the OCEN site after processing a loanApplicationStatus
	webhook. Purely a local-mirror update — does not re-validate against
	OCEN's own state machine (apply_webhook_stage on the OCEN side already
	did that, including the terminal-stage guard); this just reflects it.
	"""
	require_shared_secret(frappe.request)

	if not frappe.db.exists("Loan Application", loan_application):
		frappe.throw(f"No such Loan Application: {loan_application}", frappe.DoesNotExistError)

	frappe.db.set_value("Loan Application", loan_application, "ocen_stage", ocen_stage)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive_ocen_offer(loan_application: str, offer: dict) -> str:
	"""Called by the OCEN site after processing an offerResponse webhook.
	Creates or updates the matching Loan Offer (matched on ocen_offer_id,
	so a re-delivered webhook updates in place rather than duplicating).
	"""
	require_shared_secret(frappe.request)

	if not frappe.db.exists("Loan Application", loan_application):
		frappe.throw(f"No such Loan Application: {loan_application}", frappe.DoesNotExistError)

	existing = frappe.db.get_value(
		"Loan Offer",
		{"loan_application": loan_application, "ocen_offer_id": offer.get("ocen_offer_id")},
		"name",
	)

	fields = {
		"loan_application": loan_application,
		"ocen_offer_id": offer.get("ocen_offer_id"),
		"lender_name": offer.get("lender_name"),
		"amount": offer.get("amount"),
		"interest_rate": offer.get("interest_rate"),
		"tenure_months": offer.get("tenure_months"),
		"processing_fee": offer.get("processing_fee"),
		"offer_status": offer.get("offer_status") or "Received",
	}

	if existing:
		doc = frappe.get_doc("Loan Offer", existing)
		doc.update(fields)
		doc.save(ignore_permissions=True)
		return doc.name

	doc = frappe.get_doc({"doctype": "Loan Offer", **fields})
	doc.insert(ignore_permissions=True)
	return doc.name
