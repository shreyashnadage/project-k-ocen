# Copyright (c) 2026, Project K
# License: MIT
"""
Outbound calls from the OCEN site to the LOS site (ADR 0005) — the push
half of keeping LOS's local mirror (Loan Offer, Loan Application's OCEN
stage) up to date after this site processes a real OCEN webhook. Auth via
a pre-shared secret header (utils/shared_auth.py's HEADER_NAME), not
Frappe's User api_key/api_secret — see that module's docstring for why.

Deliberately soft-fails (logs, doesn't raise) when the LOS connection
isn't configured or the call fails — an OCEN webhook must still succeed
and get recorded in OCEN Request Log even if LOS is temporarily
unreachable. No retry queue yet (see ADR 0005 Consequences) — a failed
push is only visible in the error log until that's built.
"""

import frappe
import requests

from ocen_connector.utils.shared_auth import HEADER_NAME

RECEIVE_STAGE_UPDATE_METHOD = "los_engine.los_engine.api.ocen_integration.receive_ocen_stage_update"
RECEIVE_OFFER_METHOD = "los_engine.los_engine.api.ocen_integration.receive_ocen_offer"


def _post_to_los(method: str, payload: dict) -> None:
	settings = frappe.get_single("OCEN Settings")
	if not settings.los_site_url:
		frappe.logger("ocen_connector").warning(
			f"LOS site connection not configured — skipping call to {method}."
		)
		return

	shared_secret = settings.get_password("integration_shared_secret", raise_exception=False)
	if not shared_secret:
		frappe.logger("ocen_connector").warning(
			f"integration_shared_secret not configured — skipping call to {method}."
		)
		return

	url = f"{settings.los_site_url.rstrip('/')}/api/method/{method}"
	try:
		response = requests.post(
			url,
			headers={HEADER_NAME: shared_secret},
			json=payload,
			timeout=15,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.log_error(
			title=f"Failed to notify LOS ({method})",
			message=f"payload={payload!r}\nerror={exc}",
		)


def notify_stage_change(loan_application: str, ocen_stage: str) -> None:
	_post_to_los(
		RECEIVE_STAGE_UPDATE_METHOD,
		{"loan_application": loan_application, "ocen_stage": ocen_stage},
	)


def notify_offer(loan_application: str, offer: dict) -> None:
	_post_to_los(RECEIVE_OFFER_METHOD, {"loan_application": loan_application, "offer": offer})
