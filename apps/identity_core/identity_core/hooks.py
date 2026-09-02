app_name = "identity_core"
app_title = "Identity Core"
app_publisher = "Project K"
app_description = "Auth source of truth: Users, Roles, Role Profiles, tenant registry, org hierarchy"
app_email = "dev@projectk.example"
app_license = "mit"
required_apps = ["frappe"]

# Every other app in this bench (crm_extensions, los_engine, ocen_connector,
# ddp_engine, portal_gateway) depends on identity_core for Role/Role Profile
# definitions and the Tenant registry. identity_core depends on nothing but
# frappe.

# Fixtures — Role and Role Profile records matching spec §4.1. Re-export
# with `bench --site <site> export-fixtures --app identity_core` after
# changing role/permission definitions in the Desk UI.
fixtures = [
    {"doctype": "Role", "filters": [["name", "in", [
        "Borrower",
        "Field Agent",
        "CRM User",
        "Underwriter",
        "LOS User",
        "DDP User",
        "Lender Portal User",
        "Anchor Portal User",
    ]]]},
    {"doctype": "Role Profile", "filters": [["name", "in", [
        "Borrower",
        "Field Agent",
        "Credit Ops",
        "DDP Analyst",
        "Lender Reviewer",
        "Anchor Admin",
    ]]]},
]

# doc_events / scheduler_events intentionally left empty here — identity_core
# owns definitions (Role, Role Profile, Tenant), not behavior on other apps'
# doctypes. See identity_core.utils.proxy_action for the shared before_save
# helper other apps' controllers should call for the Field Agent → Borrower
# delegation pattern (spec §4.3).
