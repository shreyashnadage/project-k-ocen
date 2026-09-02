app_name = "ocen_connector"
app_title = "OCEN Connector"
app_publisher = "Project K"
app_description = "OCEN 4.0 async API adapter: participant directory, loan application/offer state, request log, webhook receivers"
app_email = "dev@projectk.example"
app_license = "mit"
required_apps = ["frappe", "identity_core", "los_engine"]

# OCEN Loan Application links 1:1 to los_engine's Loan Application (spec §6.2),
# so los_engine must be installed first.

# Webhook receivers — spec §6.3. Registered here as whitelisted API endpoints
# rather than a generic doc_event, because OCEN webhooks are not writes to a
# Frappe doctype from a Frappe client; they are inbound HTTP calls from the
# OCEN Registry / lenders that this app must authenticate and translate.
# See ocen_connector/api/webhooks.py.
