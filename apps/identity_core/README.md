# identity_core

Auth source of truth for the OCEN platform bench. Owns:

- **Role / Role Profile** definitions matching spec §4.1 (shipped as
  fixtures in `identity_core/fixtures/`, auto-loaded on `bench migrate`).
  `Platform Admin` is intentionally not a separate Role Profile — spec §4.1
  defines it as "System Manager equivalent"; assign the core `System
  Manager` role directly, sparingly.
- **Tenant** doctype (`identity_core/doctype/tenant`) — the registry + org
  hierarchy (Cluster → Anchor) for the pooled multi-tenant population (spec
  §3.2B). `tenant_code` is the value every other app's DocTypes store in
  their `tenant_id` field; row-level isolation is enforced via Frappe User
  Permission against this doctype, not custom Python (spec §3.2, §4.2).
  Lender tenants are site-isolated (§3.2A) and are **not** registered here.
- `utils.proxy_action.stamp_proxy_action` — shared helper implementing the
  Field Agent → Borrower delegation pattern (spec §4.3). Other apps'
  DocTypes that a Field Agent can write to on a Borrower's behalf (Loan
  Application, AA Consent, KYC uploads, ...) should declare a
  `performed_by_agent` Link(User) field and call this from a
  `before_insert`/`before_save` controller hook.

No other app should be a dependency of this one. Every other app in this
bench (`crm_extensions`, `los_engine`, `ocen_connector`, `ddp_engine`, `portal_gateway`)
should list `identity_core` as a required app.
