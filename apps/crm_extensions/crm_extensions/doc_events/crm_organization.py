# Copyright (c) 2026, Project K
# License: MIT
"""
Closes the row-level isolation gap flagged in crm_extensions/README.md:
DocType Permissions alone let any Anchor Portal User see every anchor's
Vendor Attestation records, not just their own. Spec §4.2 requires a User
Permission keyed on the anchor for that — this creates/updates/removes it
automatically from the CRM Organization's `portal_user` field, so nobody
has to remember to set it up by hand when onboarding an anchor.
"""

import frappe

USER_PERMISSION_ALLOW = "CRM Organization"


def after_insert(doc, method=None):
	_sync_portal_user_permission(doc)


def on_update(doc, method=None):
	_sync_portal_user_permission(doc)


def _sync_portal_user_permission(doc):
	if not doc.is_anchor:
		return

	previous_user = doc.get_doc_before_save().portal_user if doc.get_doc_before_save() else None
	if previous_user and previous_user != doc.portal_user:
		_delete_user_permission(previous_user, doc.name)

	if not doc.portal_user:
		return

	exists = frappe.db.exists(
		"User Permission",
		{
			"user": doc.portal_user,
			"allow": USER_PERMISSION_ALLOW,
			"for_value": doc.name,
		},
	)
	if exists:
		return

	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": doc.portal_user,
			"allow": USER_PERMISSION_ALLOW,
			"for_value": doc.name,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)


def _delete_user_permission(user: str, for_value: str) -> None:
	name = frappe.db.get_value(
		"User Permission",
		{"user": user, "allow": USER_PERMISSION_ALLOW, "for_value": for_value},
	)
	if name:
		frappe.delete_doc("User Permission", name, ignore_permissions=True)
