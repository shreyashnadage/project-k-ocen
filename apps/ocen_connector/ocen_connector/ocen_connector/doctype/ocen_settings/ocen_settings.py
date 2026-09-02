# Copyright (c) 2026, Project K
# License: MIT

from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document


class OCENSettings(Document):
	def get_access_token(self) -> str:
		"""Return a cached OAuth2 access token, refreshing via client-credentials
		grant if missing or expired. Spec §6.4.
		"""
		if self.cached_access_token and self.token_expires_at:
			if frappe.utils.now_datetime() < self.token_expires_at - timedelta(seconds=60):
				return self.get_password("cached_access_token")

		return self._refresh_access_token()

	def _refresh_access_token(self) -> str:
		import requests

		response = requests.post(
			self.token_url,
			data={
				"grant_type": "client_credentials",
				"client_id": self.client_id,
				"client_secret": self.get_password("client_secret"),
			},
			timeout=30,
		)
		response.raise_for_status()
		payload = response.json()

		token = payload["access_token"]
		expires_in = payload.get("expires_in", 3600)

		self.db_set("cached_access_token", token)
		self.db_set(
			"token_expires_at",
			frappe.utils.now_datetime() + timedelta(seconds=expires_in),
		)
		return token

	def sign_request(self, payload: dict) -> str:
		"""Sign a request payload as a detached JWS (spec §6.4), matching the
		format `ocen_connector.utils.jws.verify_detached_jws` expects on
		inbound webhooks — see that module's docstring for the same caveat:
		not yet confirmed against real OCEN sandbox traffic (spec §6.5).
		"""
		from ocen_connector.utils.jws import sign_detached_jws

		signing_key = self.get_password("jws_signing_key")
		if not signing_key:
			frappe.throw("JWS signing key not configured in OCEN Settings.")
		return sign_detached_jws(frappe.as_json(payload).encode("utf-8"), signing_key)
