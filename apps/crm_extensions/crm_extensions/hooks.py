app_name = "crm_extensions"
app_title = "CRM Extensions"
app_publisher = "Project K"
app_description = "Anchor relationship pipeline + Vendor lead pipeline, extending Frappe CRM without modifying its core"
app_email = "dev@projectk.example"
app_license = "mit"

# Named crm_extensions, not crm, because Frappe CRM itself installs as an
# app literally named "crm" — a same-named local app would collide with it
# on a real bench. This app extends CRM Organization (anchor pipeline) and
# CRM Lead (vendor lead pipeline) via Custom Field + doc_events only, per
# spec §3.3/§3.6: never modify Frappe CRM's own (AGPL) core.
required_apps = ["frappe", "identity_core", "crm"]

fixtures = [
    {"doctype": "Custom Field", "filters": [["dt", "in", ["CRM Organization", "CRM Lead"]]]},
]

# Vendor lead pipeline: Field Agents create/edit CRM Lead records on behalf
# of vendors who are present but not operating the system themselves —
# same proxy-action pattern as los_engine's Loan Application (spec §4.3).
# NOTE on the module path below: doc_events/ sits directly under the app
# package (apps/crm_extensions/crm_extensions/doc_events/), one level
# shallower than los_engine's equivalent (which nests it inside that app's
# module subfolder) — so the import path here is "crm_extensions.doc_events.*",
# not "crm_extensions.crm_extensions.doc_events.*". Getting this wrong is a
# silent failure: Frappe only imports the handler when the hook actually
# fires, so a bad path here does not surface until something inserts/saves
# a CRM Lead or CRM Organization — as happened here (ADR 0003 follow-up).
doc_events = {
    "CRM Lead": {
        "before_insert": "crm_extensions.doc_events.crm_lead.before_insert",
        "before_save": "crm_extensions.doc_events.crm_lead.before_save",
    },
    # Row-level isolation for Anchor Admin (spec §4.1, §4.2) — see
    # doc_events/crm_organization.py for why this exists.
    "CRM Organization": {
        "after_insert": "crm_extensions.doc_events.crm_organization.after_insert",
        "on_update": "crm_extensions.doc_events.crm_organization.on_update",
    },
}
