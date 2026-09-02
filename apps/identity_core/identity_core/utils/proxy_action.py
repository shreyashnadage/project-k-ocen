# Copyright (c) 2026, Project K
# License: MIT
"""
Shared "acting on behalf of" (proxy action) helper — spec §4.3.

Field Agents frequently perform writes (data capture, AA consent
initiation, document upload) on behalf of a Borrower who is present but not
directly operating the system. Every such write must be stamped as a proxy
action, not silent impersonation — this is a DPDP Act accountability
requirement and a dispute-resolution necessity, not optional.

Any DocType that can be written to by both a Borrower directly and a Field
Agent acting on their behalf (Loan Application, AA Consent, KYC documents,
etc., living in los_engine / ocen_connector / ddp_engine) should call
`stamp_proxy_action(doc)` from its controller's `before_insert` / `before_save`
hook. The DocType must declare a `performed_by_agent` Link(User) field.

Deliberately does not trust any client-supplied flag — the session's roles
are the only signal used, exactly per the spec's instruction not to trust
client-supplied flags for this determination.
"""

import frappe


def stamp_proxy_action(doc, field: str = "performed_by_agent") -> None:
	"""Stamp `field` on `doc` with the acting Field Agent's user, if the
	current session belongs to a Field Agent rather than the record's own
	Borrower. Call from before_insert/before_save on Borrower-owned DocTypes.
	"""
	if not doc.meta.has_field(field):
		frappe.throw(
			f"{doc.doctype} must declare a '{field}' Link(User) field to use "
			"the proxy-action pattern (spec §4.3)."
		)

	session_user = frappe.session.user
	if session_user in ("Administrator", "Guest"):
		return

	acting_roles = set(frappe.get_roles(session_user))
	if "Field Agent" not in acting_roles:
		# Genuine self-service action — leave the field unset/unchanged.
		return

	owner_user = getattr(doc, "owner", None) if doc.is_new() else frappe.db.get_value(
		doc.doctype, doc.name, "owner"
	)
	if session_user == owner_user:
		# The Field Agent is also the record owner (e.g. created it directly
		# under their own account) — not a proxy action against someone else.
		return

	doc.set(field, session_user)
