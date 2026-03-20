# FFE Stage 44 — Adaptive Weight Mutation Seam

## Why this stage exists

Stage 43 closed the **adaptive activation** seam: a normalized, policy-selection-facing summary that adaptive recommendation artifacts can progress into activation-ready / control-ready adaptive decisions.

The next careful seam is **adaptive weight mutation**.

This is the first layer where we preserve a normalized, policy-facing record that adaptive activation artifacts can progress into weight-mutation / provider-control artifacts, without collapsing into Thompson posterior math, Kelly sizing formulas, or raw config-persistence/export mechanics.

## Stage 44 scope

### Build from
- Stage 43 adaptive-activation summaries
- existing runtime concepts already present in live code:
  - `update_base_weights`
  - `apply_failover`
  - `base_weights` / `provider_weights`
  - enabled-provider mutation paths in `ensemble_manager.py` and `core.py`
  - adaptive-learning mutation hooks that feed live provider control

### Still explicitly NOT this stage
- Thompson posterior update math
- Kelly sizing/fraction internals
- raw config serialization / API patch payload schemas
- dashboard / webhook / reporting export schemas
- final migration collapse of adaptive-control implementation details

## Careful seam definition

### adaptive-weight-mutation-ready
A normalized policy-selection layer that says:
- how many comparable adaptive-activation artifacts progressed into weight-mutation / provider-control artifacts
- how many remained shadow / primary-cutover / manual-hold / deferred shaped
- and that the chain can safely export those adaptive-weight-mutation summaries for downstream persistence checks

It does **not** yet promise mutation-engine-grade, config-persistence-grade, or posterior-math-grade fidelity.

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_weight_mutation_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_weight_mutation_summary(...)`
3. **PR-3** — end-to-end adaptive-weight-mutation chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_weight_mutation_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
We are continuing the same pseudocode-roadmap discipline used across Stages 29–43:
- one narrow seam at a time
- summary-oriented policy-selection abstractions
- no skipping directly from adaptive-activation normalization into Kelly/Thompson internals or raw config/export mechanics

## Why this is conservative in the right way
Adaptive activation answers “did the adaptive recommendation become a normalized activation-ready control artifact?”
Adaptive weight mutation answers “did that activation-ready artifact become a normalized provider-weight / failover mutation artifact?”

That is the smallest next seam that reflects the live repo shape (`update_base_weights`, `apply_failover`, `base_weights`, `provider_weights`) without prematurely modeling posterior math, Kelly internals, or raw config persistence/export details.
