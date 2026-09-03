# Copyright (c) 2026, Project K
# License: MIT
"""
OCEN 4.0 webhook receivers — spec §6.3.

OCEN APIs are fully async: every outbound request gets an immediate
acknowledgement, and the real result arrives later via one of these
webhooks. Every call in and out is logged to OCEN Request Log regardless of
outcome, per spec §8 auditability.

Signature header/JWS shape (spec §6.5) is not yet confirmed against real
OCEN sandbox traffic — see ocen_connector/utils/jws.py's docstring before
relying on this in anything beyond dev.
"""

import frappe

from ocen_connector.ocen_connector.doctype.ocen_request_log.ocen_request_log import (
	OCENRequestLog,
)
from ocen_connector.utils import los_client
from ocen_connector.utils.jws import SignatureVerificationError, verify_detached_jws

SIGNATURE_HEADER = "X-Jws-Signature"


def _verify_signature(request) -> dict:
	"""Verifies the inbound webhook's detached JWS and returns the payload
	parsed from the exact bytes that were verified — never re-parse the
	body separately afterward, or a signed-vs-used mismatch becomes
	possible.

	Sandbox with no signature header present is allowed through unverified
	(logged as a warning) so the webhook flow can be exercised before real
	OCEN sandbox credentials/signing exist. A signature header that IS
	present is always verified, even in Sandbox — if a sandbox partner
	signs its calls, we should be checking them. Production always
	requires a valid signature.
	"""
	settings = frappe.get_single("OCEN Settings")
	raw_body = request.get_data()
	signature_header = request.headers.get(SIGNATURE_HEADER)

	if not signature_header:
		if settings.environment == "Sandbox":
			frappe.logger("ocen_connector").warning(
				f"Webhook received with no {SIGNATURE_HEADER} header — allowed "
				"because environment is Sandbox. This must never happen in Production."
			)
			return frappe.parse_json(raw_body)
		frappe.throw(f"Missing {SIGNATURE_HEADER} header.", frappe.PermissionError)

	try:
		return verify_detached_jws(raw_body, signature_header, settings.registry_public_key)
	except SignatureVerificationError as exc:
		frappe.throw(f"Webhook signature verification failed: {exc}", frappe.PermissionError)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def loan_application_status():
	"""Callback target for `loanApplicationStatus` — spec §6.3 stage 1."""
	payload = _verify_signature(frappe.request)
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
	los_client.notify_stage_change(doc.loan_application, doc.ocen_stage)

	log.db_set("ocen_loan_application", application_name)
	return {"status": "ok"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def offer_response():
	"""Callback target for `offerResponse` — spec §6.3 stage 2. Creates or
	updates the OCEN Offer for the responding lender.
	"""
	payload = _verify_signature(frappe.request)
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

	new_offer = frappe.get_doc(
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
	)
	new_offer.insert(ignore_permissions=True)

	doc = frappe.get_doc("OCEN Loan Application", application_name)
	if doc.ocen_stage in ("Submitted", "Acknowledged"):
		doc.apply_webhook_stage("Offers Received", payload)

	lender_name = frappe.db.get_value("OCEN Participant", lender_participant, "participant_name")
	los_client.notify_offer(
		doc.loan_application,
		{
			"ocen_offer_id": new_offer.name,
			"lender_name": lender_name,
			"amount": new_offer.amount,
			"interest_rate": new_offer.interest_rate,
			"tenure_months": new_offer.tenure_months,
			"processing_fee": new_offer.processing_fee,
			"offer_status": new_offer.offer_status,
		},
	)

	log.db_set("ocen_loan_application", application_name)
	return {"status": "ok"}
