# ddp_engine

**Placeholder — Phase 3** (spec §9). Installable on the bench (valid app
skeleton, no doctypes yet) so the bench structure is complete, but
intentionally not built out ahead of its phase.

## When this gets built (spec §7, §3.6)

- **AA Consent** doctype — consent artefacts from the AA SDK (Setu or
  Perfios — open question, spec §10 #4), linked to the borrower record;
  doubles as the DPDP Act audit trail.
- **Trust Graph Entry** — ingestion pipeline for AA-fetched data.
- **Scoring interface** — per spec §3.6, if the scoring algorithm is
  proprietary, this must be a thin REST/event-bus adapter to an external
  service, never in-process proprietary code inside this (otherwise
  MIT-licensed) app.

## Requires

`identity_core`.
