# FFE Stage 36 — Execution Receipt Seam

## Why this stage exists

Stage 35 closed the **execution-result** seam: a bounded, policy-selection-facing summary of whether a dispatch attempt ultimately resolved into a success/failure/deferred-style outcome.

The next careful seam is **execution receipt**.

This is the first layer where we intentionally preserve a normalized, policy-facing record of execution identifiers and receipt-like metadata without collapsing all the way into provider-native response parsing or live worker orchestration.

## Stage 36 scope

### Build from
- Stage 35 execution-result summaries
- existing execution-path concepts already present in live code:
  - `order_id`
  - `order_status`
  - provider execution response payloads
  - idempotency/request identifiers such as `clientRequestID`

### Still explicitly NOT this stage
- raw provider response modeling
- exchange-specific fill/reject transaction parsing
- worker/runtime callback orchestration
- rollback automation / compensating action machinery
- final "migration complete" collapse

## Careful seam definition

### execution-result-ready / execution-receipt-ready
A normalized policy-selection layer that says:
- how many comparable execution outcomes produced receipt-like artifacts
- how many were shadow / primary-cutover / manual-hold / deferred shaped
- and that the chain can safely export those receipt summaries for downstream persistence checks

It does **not** yet promise provider-native receipt fidelity.

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_execution_receipt_set(...)`
2. **PR-2** — `build_policy_selection_execution_receipt_summary(...)`
3. **PR-3** — end-to-end execution-receipt chain hardening
4. **PR-4** — `extract_policy_selection_execution_receipt_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
We are following the pseudocode-roadmap discipline already used across Stages 29–35:
- one narrow seam at a time
- summary-oriented policy-selection abstractions
- explicit refusal to jump from execution-result directly to provider-native response or rollback machinery

## Why this is conservative in the right way
If we skip straight from execution-result to raw provider responses, we lose the staged migration discipline that has kept the chain testable and reviewable.

Execution receipt is the smallest next seam that still reflects the real runtime path while avoiding a rushed final collapse.
