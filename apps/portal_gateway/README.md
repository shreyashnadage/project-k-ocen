# portal_gateway

**Placeholder — Phase 4** (spec §9). Installable on the bench, no API
methods yet; intentionally not built out ahead of its phase (build starts
once the Field Agent PWA spike, per spec §3.5/§Phase 4, is ready to consume
it).

## When this gets built (spec §3.3)

Whitelisted, read-mostly API methods that compose responses across
`identity_core` / `los_engine` / `ocen_connector` / `crm_extensions`
doctypes for a specific frontend screen — so frontends aren't making 3+
chained REST calls per screen. Must still enforce permissions through the
underlying doctype calls under the requesting user's own session; never a
bypass layer (spec §3.5).

## Requires

`identity_core`, `los_engine`, `ocen_connector`, `crm_extensions`.
