app_name = "ddp_engine"
app_title = "DDP Engine"
app_publisher = "Project K"
app_description = "Trust Graph entry, AA data ingestion, thin proprietary-scoring adapter"
app_email = "dev@projectk.example"
app_license = "mit"
required_apps = ["frappe", "identity_core"]

# Placeholder — Phase 3 in the build plan (spec §9). Deliberately not
# building Trust Graph Entry / AA Consent doctypes ahead of that phase.
#
# When built: per spec §3.6, if Trust Graph scoring logic is proprietary,
# this app must be a thin adapter calling an external service via REST or
# an event bus — never import proprietary scoring code directly into this
# (MIT-licensed, but living alongside AGPL Frappe CRM on the same bench)
# Python codebase.
