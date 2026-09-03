# Compliance & business-decision questions — tracked, not blocking

This is a running list of things discovered during POC build-out that need
a real decision from the founder / lending / credit / compliance side
before this platform handles real money or real borrower data. None of
these block POC development — where code needs *something* to run, a
clearly-labeled placeholder is used instead (grep for `PLACEHOLDER` /
`POC-ONLY` across the codebase to find them all). This file is the index.

## Open

1. **RBI IRAC collection offset sequences** (ADR 0004) — Frappe Lending's
   `Loan Product` requires `collection_offset_sequence_for_standard_asset`
   and `..._for_sub_standard_asset`: how a delinquent loan's payments get
   allocated across principal/interest/penalty, mapped to RBI's asset
   classification tiers (Standard / Sub-Standard / Doubtful / Loss).
   **Unblocked for POC**: a single `Loan Demand Offset Order` (EMI →
   Additional Interest → Penalty → Charges) applied to both tiers, titled
   `"POC-ONLY Collection Offset Order — NOT a real collection policy"` so
   it's unmistakable in the Desk UI too (`los_engine/setup.py`). End-to-end
   Loan Lead → Loan Application conversion is verified working against
   this placeholder. Needs real collection policy from lending/credit
   before this leaves POC — the placeholder's title is deliberately
   impossible to mistake for a real one.

2. **Real Loan Product terms** — interest rate, tenure, fees. **Placeholder
   in use**: 18% p.a., term loan, no fees (`los_engine/setup.py`,
   `PLACEHOLDER_LOAN_PRODUCT`).

3. **Real Company entity details** — legal name, currency, country,
   chart of accounts template. **Placeholder in use**: "Project K", INR,
   India, Standard COA (`los_engine/setup.py`).

4. **CGTMSE vs. FLDG mutual exclusivity** (spec §1.4) — already enforced
   in code (`ocen_connector`'s `OCEN Offer` controller refuses `cgtmse_flag`
   when the loan already has `fldg_flag` set) — no placeholder needed, but
   flagging that this is a real regulatory constraint the code encodes
   without a compliance review of the logic itself.

5. **AA SDK provider — Setu vs. Perfios** (original spec §10 #4) — which is
   contractually/technically finalized? `ddp_engine` (AA Consent
   integration) hasn't been built yet — needed before that phase starts.

6. **WhatsApp Business API provider** (original spec §10 #7, Twilio noted
   as under evaluation) — confirm current status and cost model before
   Phase 5 (`whatsapp_adapter`) starts.

7. **DPDP Act 2023/Rules 2025 retention & erasure periods** (spec §8) —
   no retention/erasure logic implemented yet at all (not even a
   placeholder). Needs real data-retention schedules per record type
   before this is anything but a POC.

8. **OCEN webhook JWS format** (spec §6.5) — `ocen_connector`'s signature
   verification assumes the Account Aggregator/ReBIT `X-Jws-Signature`
   detached-JWS convention. Not confirmed against real OCEN sandbox
   traffic — needs real OCEN sandbox credentials/docs to verify or correct.

9. **Lender site-per-tenant scope** (original spec §10 #3) — confirmed as
   the model, but which lenders in the near-term pipeline actually require
   full site isolation vs. would accept pooled tenancy with strong
   row-level isolation?

## Resolved

- Full pivot to Frappe over the Fineract/Temporal scaffold (ADR 0001).
- Frappe Lending v16 as LOS core over a thin Fineract tracking layer or
  fully custom doctypes (ADR 0001, spec §3.4).
- Trust Graph scoring: defaults to fully separate non-Frappe service per
  spec §3.6 IP-boundary principle, until told otherwise.
