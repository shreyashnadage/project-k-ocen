app_name = "los_engine"
app_title = "LOS Engine"
app_publisher = "Project K"
app_description = "LOS core: Loan Lead, thin extensions over Frappe Lending's Loan Application, offer/eligibility tracking"
app_email = "dev@projectk.example"
app_license = "mit"

# Per the resolved §3.4 decision, los_engine builds on Frappe Lending v16
# (the `lending` app) as the LOS core rather than duplicating it or mirroring
# state from Fineract. This app's own doctypes are limited to what Frappe
# Lending does not model (Loan Lead, the pre-application stage) plus custom
# fields/hooks layered onto Lending's own doctypes.
#
# `crm` (upstream Frappe CRM) is a dependency too — Loan Lead.vendor_lead
# links to its CRM Lead doctype, and this app listens for CRM Lead status
# changes to auto-create the handoff Loan Lead (doc_events below). This
# app owns that handoff, not crm_extensions, because it's a Loan Lead
# (a los_engine concept) being created — crm_extensions shouldn't need to
# know los_engine's schema.
required_apps = ["frappe", "identity_core", "lending", "crm"]

# Custom Field fixtures added onto Frappe Lending's Loan Application —
# tenant_id (row-level isolation, §3.2B), performed_by_agent (proxy-action
# stamp target, §4.3), fldg_flag (credit-enhancement mutual exclusivity
# with CGTMSE, §1.4). Re-export after changing these in the Desk UI with
# `bench --site <site> export-fixtures --app los_engine`.
fixtures = [
    {"doctype": "Custom Field", "filters": [["dt", "=", "Loan Application"]]},
]

# The proxy-action pattern (§4.3) must be implemented via a before_save/
# before_insert hook on the doctype's controller. Loan Application belongs
# to the `lending` app, not this one, so we attach via Frappe's doc_events
# hook mechanism rather than editing lending's source — this is the
# Frappe-idiomatic way to extend a doctype owned by another app.
doc_events = {
    "Loan Application": {
        "before_insert": "los_engine.los_engine.doc_events.loan_application.before_insert",
        "before_save": "los_engine.los_engine.doc_events.loan_application.before_save",
    },
    # Vendor lead -> Loan Lead handoff: auto-creates a Loan Lead when a CRM
    # Lead reaches the "Qualified" status, so a Field Agent doesn't have to
    # remember to do it by hand. See doc_events/crm_lead.py.
    "CRM Lead": {
        "on_update": "los_engine.los_engine.doc_events.crm_lead.on_update",
    },
}
