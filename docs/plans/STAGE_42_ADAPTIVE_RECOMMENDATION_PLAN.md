# FFE Stage 42 — Adaptive Recommendation Seam

## Why this stage exists

Stage 41 closed the **learning analytics** seam: a normalized, policy-selection-facing summary that learning-feedback artifacts can progress into analytics-ready / reporting-ready artifacts.

The next careful seam is **adaptive recommendation**.

This is the first layer where we preserve a normalized, policy-facing record that learning-analytics artifacts can progress into adaptive provider/sizing recommendation artifacts, without collapsing into Thompson-sampling internals, Kelly-calculation math, or direct ensemble-weight mutation mechanics.

## Stage 42 scope

### Build from
- Stage 41 learning-analytics summaries
- existing runtime concepts already present in live code:
  - `get_provider_recommendations`
  - `get_provider_stats` / `get_regime_stats`
  - `adaptive_learning` in the ensemble manager
  - `check_kelly_activation_criteria`
  - ensemble weight update entry points in `core.py`

### Still explicitly NOT this stage
- Thompson-sampling posterior update math
- Kelly fraction calculation internals
- direct base-weight mutation / failover orchestration internals
- dashboard / CSV / webhook export schemas
- final migration collapse of adaptive-control logic

## Careful seam definition

### adaptive-recommendation-ready
A normalized policy-selection layer that says:
- how many comparable learning-analytics artifacts progressed into adaptive recommendation artifacts
- how many remained shadow / primary-cutover / manual-hold / deferred shaped
- and that the chain can safely export those adaptive-recommendation summaries for downstream persistence checks

It does **not** yet promise Thompson/Kelly-engine-grade or ensemble-mutation-grade fidelity.

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_recommendation_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_recommendation_summary(...)`
3. **PR-3** — end-to-end adaptive-recommendation chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_recommendation_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
We are continuing the same pseudocode-roadmap discipline used across Stages 29–41:
- one narrow seam at a time
- summary-oriented policy-selection abstractions
- no skipping directly from learning-analytics normalization into Thompson/Kelly internals or direct ensemble mutation mechanics

## Why this is conservative in the right way
Learning analytics answers “did the learning-ready artifact become an analytics-ready / reporting-ready artifact?”
Adaptive recommendation answers “did that analytics-ready artifact become a normalized adaptive recommendation artifact?”

That is the smallest next seam that reflects the live repo shape (`get_provider_recommendations`, Thompson stats, Kelly activation checks, adaptive ensemble hooks) without prematurely modeling Thompson/Kelly internals or direct ensemble-weight mutation logic.
