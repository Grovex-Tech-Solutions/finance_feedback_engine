# FFE Stage 48 — Adaptive Control Config Patch Contract Seam

## Why this stage exists

Stage 47 closed the **adaptive control runtime apply** seam: a normalized, policy-selection-facing summary that adaptive-control-snapshot artifacts can progress into runtime-apply-ready control updates.

The next careful seam in the live repo is **adaptive control config patch contract**.

This is the first layer where we preserve a normalized, policy-facing record that adaptive-control-runtime-apply artifacts can progress into **control-plane patch-contract-ready updates**, grounded in the repo's real API config update path, without collapsing into raw HTTP transport/auth concerns or final YAML/runtime-file serialization details.

## Live repo evidence used for this draft

### Explicit control-plane config patch concepts already present
- `finance_feedback_engine/api/bot_control.py`
  - `ConfigUpdateRequest`
  - `@bot_control_router.patch("/config")`
  - `updates_for_agent`
  - `updates_for_ensemble`
  - `response_updates`
  - atomic mutation via `config_snapshot`
  - commit via `engine.config.clear()` / `engine.config.update(config_snapshot)`
- config-field validation / normalization already visible in:
  - `finance_feedback_engine/utils/config_validator.py`
  - `finance_feedback_engine/utils/config_schema_validator.py`
  - `finance_feedback_engine/utils/config_loader.py`

### Control-state fields still clearly in play
- `provider_weights`
- `enabled_providers`
- confidence / sizing / concurrency control fields adjacent to adaptive controls
- request/update/response field grouping around `/config`

## Stage 48 scope

### Build from
- Stage 47 adaptive-control-runtime-apply summaries
- real config patch / update contract semantics already visible in the repo:
  - update grouping into request-style fields
  - agent vs ensemble update partitioning
  - response update summaries
  - atomic snapshot-and-replace application contract

### Still explicitly NOT this stage
- raw HTTP auth, API-key, or network transport concerns
- websocket / dashboard / SSE payload schemas
- YAML file write format / disk serialization details
- durable runtime config file materialization (`config.local.runtime.yaml`) as a persistence target
- Thompson posterior math
- Kelly sizing internals

## Careful seam definition

### adaptive-control-config-patch-contract-ready
A normalized policy-selection layer that says:
- how many comparable adaptive-control-runtime-apply artifacts progressed into config-patch-contract-ready control updates
- how many remained shadow / primary-cutover / manual-hold / deferred shaped
- and that the chain can safely summarize those contract-ready updates for downstream transport or persistence layers

It does **not** yet promise concrete HTTP exchange behavior, authentication, or file-on-disk serialization fidelity.

## Why this is the smallest honest next seam

The live repo currently separates three ideas even if they sit near each other:
1. **runtime application** of config changes
2. **control-plane patch contract** shape (`ConfigUpdateRequest`, grouped updates, response summary)
3. **disk/runtime-file serialization/materialization** (`config.local.runtime.yaml`, YAML write paths)

Stage 47 covered the first.
Stage 48 should cover the second.
A later stage can cover runtime-config materialization / serialization if the live repo still supports that split.

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_control_config_patch_contract_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_control_config_patch_contract_summary(...)`
3. **PR-3** — end-to-end adaptive-control-config-patch-contract chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_control_config_patch_contract_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
We are still following the same seam discipline used across the prior stages:
- derive from live repo evidence, not stale intention alone
- keep one narrow abstraction layer at a time
- prefer policy-facing summaries before raw transport or persistence payloads
- keep the system auditable, understandable, and re-derivable later

## Documentation cohesion note
Keep the seam trail in `docs/plans/` and avoid bloating the root README with stage-by-stage migration detail.
