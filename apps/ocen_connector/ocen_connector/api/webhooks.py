# Copyright (c) 2026, Project K
# License: MIT
"""
OCEN 4.0 webhook receivers — spec §6.3.

OCEN APIs are fully async: every outbound request gets an immediate
acknowledgement, and the real result arrives later via one of these
webhooks. Every call in and out is logged to OCEN Request Log regardless of
outcome, per spec §8 auditability.

TODO before sandbox testing (spec §6.5): verify the exact JWS signature
header OCEN webhooks carry and enforce verification in `_verify_signature`
below — this stub accepts unsigned payloads, which is only acceptable
against a sandbox that has no adversarial traffic, never in production.
"""

import frappe

from ocen_connector.ocen_connector.doctype.ocen_request_log.ocen_request_log import (
	OCENRequestLog,
)


def _verify_signature(request) -> bool:
	settings = frappe.get_single("OCEN Settings")
	if settings.environment == "Sandbox":
		return True
	# TODO: verify JWS signature on the webhook payload against the OCEN
	# Registry's published public key before trusting it in Production.
	frappe.throw("Production webhook signature verification is not implemented yet.")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def loan_application_status():
	"""Callback target for `loanApplicationStatus` — spec §6.3 stage 1."""
	_verify_signature(frappe.request)
	payload = frappe.request.get_json(force=True)
	request_id = payload.get("requestId")

	log = OCENRequestLog.record(
		direction="Inbound",
		endpoint="loanApplicationStatus",
		request_id=request_id,
		response_payload=payload,
	)

	application_name = frappe.db.get_value(
		"OCEN Loan Application", {"request_id": request_id}, "name"
	)
	if not application_name:
		log.db_set("error", f"No OCEN Loan Application found for requestId {request_id}")
		frappe.local.response.http_status_code = 404
		return {"status": "unknown_request_id"}

	new_stage = payload.get("status")
	doc = frappe.get_doc("OCEN Loan Application", application_name)
	doc.apply_webhook_stage(new_stage, payload)

	log.db_set("ocen_loan_application", application_name)
	return {"status": "ok"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def offer_response():
	"""Callback target for `offerResponse` — spec §6.3 stage 2. Creates or
	updates the OCEN Offer for the responding lender.
	"""
	_verify_signature(frappe.request)
	payload = frappe.request.get_json(force=True)
	request_id = payload.get("requestId")

	log = OCENRequestLog.record(
		direction="Inbound",
		endpoint="offerResponse",
		request_id=request_id,
		response_payload=payload,
	)

	application_name = frappe.db.get_value(
		"OCEN Loan Application", {"request_id": request_id}, "name"
	)
	if not application_name:
		log.db_set("error", f"No OCEN Loan Application found for requestId {request_id}")
		frappe.local.response.http_status_code = 404
		return {"status": "unknown_request_id"}

	offer = payload.get("offer", {})
	lender_participant = frappe.db.get_value(
		"OCEN Participant", {"participant_code": payload.get("lenderId")}, "name"
	)
	if not lender_participant:
		log.db_set(
			"error", f"Unknown lender participant_code {payload.get('lenderId')}"
		)
		frappe.local.response.http_status_code = 422
		return {"status": "unknown_lender"}

	frappe.get_doc(
		{
			"doctype": "OCEN Offer",
			"ocen_loan_application": application_name,
			"offer_id": offer.get("offerId"),
			"lender": lender_participant,
			"amount": offer.get("amount"),
			"interest_rate": offer.get("interestRate"),
			"tenure_months": offer.get("tenureMonths"),
			"processing_fee": offer.get("processingFee"),
			"cgtmse_flag": bool(offer.get("cgtmseFlag")),
			"offer_status": "Received",
			"received_on": frappe.utils.now_datetime(),
			"raw_offer_payload": frappe.as_json(payload),
		}
	).insert(ignore_permissions=True)

	doc = frappe.get_doc("OCEN Loan Application", application_name)
	if doc.ocen_stage in ("Submitted", "Acknowledged"):
		doc.apply_webhook_stage("Offers Received", payload)

	log.db_set("ocen_loan_application", application_name)
	return {"status": "ok"}
