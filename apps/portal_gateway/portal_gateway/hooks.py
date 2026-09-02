app_name = "portal_gateway"
app_title = "Portal Gateway"
app_publisher = "Project K"
app_description = "BFF layer — role-aware, cross-doctype composed API responses per frontend"
app_email = "dev@projectk.example"
app_license = "mit"
required_apps = ["frappe", "identity_core", "los_engine", "ocen_connector", "crm_extensions"]

# Placeholder — Phase 4 in the build plan (spec §9), built alongside the
# first frontend (Field Agent PWA). Read-mostly whitelisted API methods
# composing responses across identity_core/los_engine/ocen_connector/
# crm_extensions doctypes, so frontends don't make 3+ chained REST calls
# per screen (spec §3.3). Permission enforcement still happens in the
# underlying doctype calls (frappe.get_list / frappe.get_doc with the
# requesting user's session) — this app must never bypass that to compose
# a response, per spec §3.5's "permission enforcement is a backend-only
# concern" principle.
