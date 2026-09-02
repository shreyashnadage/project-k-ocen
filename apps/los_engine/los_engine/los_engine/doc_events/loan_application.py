# Copyright (c) 2026, Project K
# License: MIT
"""
doc_events hooks attached to Frappe Lending's Loan Application doctype
(owned by the `lending` app, not this one — see hooks.py for why this is
wired via doc_events rather than a controller override).
"""

import frappe

from identity_core.utils.proxy_action import stamp_proxy_action


def before_insert(doc, method=None):
	_propagate_tenant(doc)
	stamp_proxy_action(doc)


def before_save(doc, method=None):
	stamp_proxy_action(doc)


def _propagate_tenant(doc):
	"""Loan Application doesn't have its own concept of Tenant — it inherits
	the borrower's tenant_id, set here at creation so User Permission-based
	row-level isolation (spec §3.2B, §4.2) applies without borrowers or field
	agents having to set it manually.
	"""
	if getattr(doc, "tenant_id", None):
		return

	loan_lead = getattr(doc, "loan_lead", None)
	if not loan_lead:
		return

	tenant_id = frappe.db.get_value("Loan Lead", loan_lead, "tenant_id")
	if tenant_id:
		doc.tenant_id = tenant_id
