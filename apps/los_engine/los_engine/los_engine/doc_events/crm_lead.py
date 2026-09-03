# Copyright (c) 2026, Project K
# License: MIT
"""
Vendor lead -> Loan Lead handoff. Owned here (not crm_extensions) because
it creates a Loan Lead, a los_engine concept — see hooks.py for the full
reasoning.

Deliberately triggers on the CRM Lead reaching "Qualified" status, not on
every save — "Qualified" is Frappe CRM's own built-in status (confirmed
against this bench: New / Contacted / Nurture / Qualified / Converted /
Unqualified / Junk), reused here as-is rather than inventing a
parallel status field, since it already means roughly the right thing
("ready to move to the next stage").

Does not require amount/applicant details to exist yet on the CRM Lead —
it doesn't capture them. The created Loan Lead starts in "New" with those
fields blank; a Field Agent or Credit Ops fills them in before running
run_eligibility_check(). This mirrors the field-agent-assisted workflow
(spec §5.2) rather than assuming the loan amount is known at the CRM
pipeline stage.
"""

import frappe

QUALIFIED_STATUS = "Qualified"


def on_update(doc, method=None):
	if doc.status != QUALIFIED_STATUS:
		return

	previous = doc.get_doc_before_save()
	if previous and previous.status == QUALIFIED_STATUS:
		return  # already was Qualified, not a fresh transition

	if frappe.db.exists("Loan Lead", {"vendor_lead": doc.name}):
		return  # idempotent — don't create a second one on a later save

	if not doc.get("tenant_id"):
		# tenant_id is mandatory on Loan Lead. Don't let a missing value here
		# blow up the CRM Lead's own save with an unrelated MandatoryError —
		# log it and leave the handoff for a human to do manually instead.
		frappe.logger("los_engine").warning(
			f"CRM Lead {doc.name} reached Qualified with no tenant_id set — "
			"skipping automatic Loan Lead creation. Create it manually once "
			"tenant_id is set."
		)
		return

	frappe.get_doc(
		{
			"doctype": "Loan Lead",
			"vendor_lead": doc.name,
			"tenant_id": doc.get("tenant_id"),
			"assigned_field_agent": doc.get("assigned_field_agent"),
			"status": "New",
		}
	).insert(ignore_permissions=True)
