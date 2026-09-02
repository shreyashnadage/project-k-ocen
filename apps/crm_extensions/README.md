# crm_extensions

Anchor relationship pipeline + Vendor lead pipeline (spec §2.1, §3.3).

Named `crm_extensions`, not `crm` — Frappe CRM itself installs as an app
literally named `crm`; a same-named local app would collide with it on a
real bench.

## Approach

Never modify Frappe CRM core (it's AGPL — spec §3.6). Extend only via:

- **Custom Field fixtures** (`fixtures/custom_field.json`) on `CRM
  Organization` (anchor pipeline) and `CRM Lead` (vendor lead pipeline):
  `tenant_id` for row-level isolation (§3.2B), `is_anchor` to distinguish
  Anchors from other CRM organizations, `anchor`/`assigned_field_agent` on
  leads, `performed_by_agent` for the proxy-action pattern (§4.3).
- **doc_events** (`doc_events/crm_lead.py`) — proxy-action stamping when a
  Field Agent captures a vendor lead on the vendor's behalf, wired via
  Frappe's `doc_events` hook rather than editing Frappe CRM's controller.
- **Vendor Attestation** — the one doctype this app owns outright: an
  Anchor confirming a vendor relationship (spec §1.2), which is also the
  record `Anchor Admin`'s scope in §4.1 ("their own vendor list and
  attestation records only") refers to.

## Known gap — needs a User Permission, not just DocType Permission

`Vendor Attestation`'s DocType Permissions (in `vendor_attestation.json`)
grant `Anchor Portal User` read/write/create — but that alone lets any
Anchor see every anchor's attestation records, not just their own. Per spec
§4.2, row-level restriction to "their own" requires a **User Permission**
record linking each Anchor Portal User to their specific `CRM Organization`
row (`allow: "CRM Organization"`), the same mechanism used for tenant
isolation elsewhere. Not yet set up as a fixture — needs real anchor user
accounts to exist first.

## Requires

`identity_core`, `crm` (upstream Frappe CRM — install before this app).

## Not yet built

Vendor lead → Loan Lead handoff (los_engine's `Loan Lead.vendor_lead`
already links to `CRM Lead`; nothing here creates that link automatically
yet — likely a `doc_events` hook on `CRM Lead` status change, once the
lead-qualification flow is designed).
