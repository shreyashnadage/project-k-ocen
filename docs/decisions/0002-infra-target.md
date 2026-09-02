# ADR 0002: Target AWS for deployment; defer provisioning until Phase 1 runs locally

**Status:** Accepted
**Date:** 2026-09-02

## Context

AWS was confirmed as available infrastructure for this project (separate
from the AWS account/instance the existing `project-k-backend-service`
Tally Sync Platform deploys to — a PEM key surfaced during this
conversation was for that unrelated project and is not reused here).

At the time of this decision, no Frappe app in this repo has been installed
onto a running bench — Phase 1 (`identity_core`, `ocen_connector`
scaffolding) is source-only.

## Decision

- **Target platform: AWS**, EC2-based, Mumbai region (`ap-south-1`) —
  consistent with the existing Tally Sync deployment and appropriate for an
  India-only regulated lending product (data residency).
- **Provisioning is deferred** until the bench installs and runs locally via
  `docker-compose.yml` and at least `identity_core` + `ocen_connector` are
  installable without errors. No EC2 instance, RDS, or other billed
  resource is created for this repo until then.
- When we do provision: follow the existing repo's pattern (GitHub Actions
  CD to EC2, see `project-k-backend-service/.github/workflows/deploy.yml`)
  rather than inventing a new deploy mechanism, unless Frappe's bench-based
  deployment model requires a materially different pipeline (likely, given
  bench's own release/asset-build step) — revisit in a follow-up ADR
  once Phase 1 is verified locally.

## Consequences

- No idle infrastructure cost during Phase 1 scaffolding.
- Actual instance sizing (CPU/RAM for MariaDB + Redis + bench workers) gets
  decided from real observed local resource use, not guessed upfront.
- This session has no AWS API credentials configured; provisioning (via
  Terraform or console) will need to be either run by a human with AWS
  access, or this session given IAM credentials scoped to what it needs —
  not a reused SSH keypair from an unrelated project.
