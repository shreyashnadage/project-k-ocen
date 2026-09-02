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
doc_events = {
    "CRM Lead": {
        "before_insert": "crm_extensions.crm_extensions.doc_events.crm_lead.before_insert",
        "before_save": "crm_extensions.crm_extensions.doc_events.crm_lead.before_save",
    }
}
