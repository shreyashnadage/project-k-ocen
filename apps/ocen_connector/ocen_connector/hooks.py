app_name = "ocen_connector"
app_title = "OCEN Connector"
app_publisher = "Project K"
app_description = "OCEN 4.0 async API adapter: participant directory, loan application/offer state, request log, webhook receivers"
app_email = "dev@projectk.example"
app_license = "mit"
required_apps = ["frappe"]

# As of ADR 0005, this app is deployed on its own Frappe site
# (ocen-network.localhost), separate from the LOS site — not installed
# alongside identity_core/los_engine as it originally was. OCEN Loan
# Application no longer Links to los_engine's Loan Application; it holds
# the LOS-side ID as a plain string and the two sites talk over REST
# instead. See docs/decisions/0005-ocen-standalone-site.md.

# Webhook receivers — spec §6.3. Registered here as whitelisted API endpoints
# rather than a generic doc_event, because OCEN webhooks are not writes to a
# Frappe doctype from a Frappe client; they are inbound HTTP calls from the
# OCEN Registry / lenders that this app must authenticate and translate.
# See ocen_connector/api/webhooks.py.
