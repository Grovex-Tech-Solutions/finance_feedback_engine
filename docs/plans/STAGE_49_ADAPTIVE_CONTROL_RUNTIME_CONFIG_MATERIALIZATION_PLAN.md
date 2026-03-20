# FFE Stage 49 — Adaptive Control Runtime Config Materialization Seam

## Why this stage exists

Stage 48 closed the **adaptive control config patch contract** seam: a normalized, policy-selection-facing summary that adaptive-control-runtime-apply artifacts can progress into config-patch-contract-ready control updates.

The next careful seam in the live repo is **adaptive control runtime config materialization**.

This is the first layer where we preserve a normalized, policy-facing record that adaptive-control-config-patch-contract artifacts can progress into **runtime-config-materialization-ready updates**, grounded in the repo's real runtime-config file pathways and atomic file I/O helpers, without collapsing into raw HTTP/auth exchange details or broad infra/dashboard concerns.

## Live repo evidence used for this draft

### Runtime config materialization concepts already present
- `finance_feedback_engine/api/health_checks.py`
  - `runtime_config_path = data_dir / "config.local.runtime.yaml"`
  - preference for runtime config path when present
- `finance_feedback_engine/utils/file_io.py`
  - `FileIOManager`
  - `write_yaml(...)`
  - atomic file write / backup semantics
- broader config load / validation paths already visible in:
  - `finance_feedback_engine/utils/config_loader.py`
  - `finance_feedback_engine/utils/config_validator.py`
  - `finance_feedback_engine/utils/config_schema_validator.py`

### Config-state fields still clearly in play
- `provider_weights`
- `enabled_providers`
- runtime-local config precedence
- materialized runtime config state vs in-memory patch/update contract state

## Stage 49 scope

### Build from
- Stage 48 adaptive-control-config-patch-contract summaries
- real runtime-config materialization semantics already visible in the repo:
  - runtime config file precedence
  - YAML write helpers
  - atomic write / backup semantics
  - runtime-local config artifact presence as a health/readiness input

### Still explicitly NOT this stage
- raw HTTP/auth/API-key exchange behavior
- websocket / dashboard / SSE payload schemas
- full operational rollout / restart semantics
- external deployment orchestration or infra mutation
- Thompson posterior math
- Kelly sizing internals

## Careful seam definition

### adaptive-control-runtime-config-materialization-ready
A normalized policy-selection layer that says:
- how many comparable adaptive-control-config-patch-contract artifacts progressed into runtime-config-materialization-ready control updates
- how many remained shadow / primary-cutover / manual-hold / deferred shaped
- and that the chain can safely summarize those materialization-ready updates for downstream transport / restart / operational layers

It does **not** yet promise concrete file contents, process restart behavior, or auth/transport exchange semantics.

## Why this is the smallest honest next seam

The live repo still separates at least three nearby concerns:
1. config patch contract shape
2. runtime config materialization / file presence / file I/O semantics
3. operational transport, auth, or restart behavior around those updates

Stage 48 covered the first.
Stage 49 should cover the second.
A later stage can decide whether transport/auth exchange or operational rollout deserves its own seam.

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_control_runtime_config_materialization_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_control_runtime_config_materialization_summary(...)`
3. **PR-3** — end-to-end adaptive-control-runtime-config-materialization chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_control_runtime_config_materialization_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
We are still following the same seam discipline used across the prior stages:
- derive from live repo evidence, not stale intention alone
- keep one narrow abstraction layer at a time
- prefer policy-facing summaries before raw transport or operational side effects
- keep the system auditable, understandable, and re-derivable later

## Documentation cohesion note
Keep the seam trail in `docs/plans/` instead of bloating root docs with migration-by-migration detail.
