# FFE Stage 52 — Adaptive Control Health and Readiness Observability Contract Seam

## Why this stage exists

Stage 51 closed the **adaptive control agent lifecycle control contract** seam: a normalized, policy-selection-facing summary that adaptive-control-config-update-transport-contract artifacts can progress into authenticated start/stop/pause/resume operational state.

The next careful seam in the live repo is **adaptive control health and readiness observability contract**.

This is the layer where authenticated execution intent connects to cross-component health checks and deployment-level readiness probes. It formalizes how policy-facing lifecycle states reflect in the broader `/health` and `/readiness` operational surfaces, without yet collapsing into high-level dashboard payloads, WebSocket fanout, or multi-host infrastructure orchestration.

## Live repo evidence used for this draft

### Health and readiness observability endpoints already exist
- `finance_feedback_engine/api/routes.py`
  - `@health_router.get("/health")`
  - `@health_router.get("/readiness")`
  - `status.HTTP_503_SERVICE_UNAVAILABLE` error shaping for failed readiness
- `finance_feedback_engine/api/health_checks.py`
  - `get_enhanced_health_status(engine)`
  - `get_readiness_status(engine)`
- `finance_feedback_engine/deployment/health.py`
  - internal orchestration readiness checks

### Aggregated state reflection
- readiness involves checking:
  - database connectivity
  - provider initialization
  - runtime config presence (`config.local.runtime.yaml`)
  - agent instance `is_running` / `_paused` status

### Why this stands apart from Dashboard/Pulse/WebSocket
- separate dashboard/status-aggregation surface exists outside this seam:
  - `finance_feedback_engine/cli/dashboard_aggregator.py`
  - `finance_feedback_engine/cli/live_dashboard.py`
  - `finance_feedback_engine/cli/formatters/pulse_formatter.py`
  - `@status_router.get("/status")`
  - WebSocket (`/ws`) implementations

## Why this is the next honest seam

The live repo still separates at least three nearby concerns:
1. authenticated agent lifecycle control (`/start`, `/stop`, `/pause`, `/resume`) — now covered by Stage 51
2. cross-component health and readiness observability (`/health`, `/readiness`, `get_enhanced_health_status(...)`)
3. high-level dashboard aggregation, PnL reporting, and WebSocket stream fanout (`/status`, `DashboardAggregator`)

Stage 52 should cover the second.
A later stage can decide whether the dashboard status payload or WebSocket fanout deserves its own seam.

## Stage 52 scope

### Build from
- Stage 51 adaptive-control-agent-lifecycle-control-contract summaries
- live repo evidence around health and readiness observability behavior:
  - `/health` and `/readiness` endpoint contracts
  - cross-component status aggregation shaping
  - HTTP 503 unavailability signaling

### Stage 52 should preserve as policy-facing signals
- how many comparable adaptive-control-agent-lifecycle-control-contract artifacts progressed into health-and-readiness-observability-ready state updates
- how many remained shadow / primary-cutover / manual-hold / deferred shaped
- that health/readiness observability reflections remain exportable and persistence-verifiable without turning into an opaque “monitoring happened” blob

## Still explicitly NOT this stage
- websocket / SSE stream payload schemas
- `DashboardAggregator` PnL formatting
- `pulse_formatter` multi-timeframe market context logic
- external deployment rollout coordination (Kubernetes, Docker Swarm)
- manual-trade execution behavior
- Thompson posterior math
- Kelly sizing internals

## Careful seam definition

### adaptive-control-health-readiness-observability-contract-ready
A normalized policy-selection layer that says:
- adaptive-control-agent-lifecycle-control-contract artifacts were eligible to reflect their state into cross-component health and readiness observability
- the observability-facing summary preserves endpoint shape discipline (`/health` and `/readiness`)
- running / paused / degraded state pathways remain visible as structured control summaries

It does **not** yet promise dashboard layout correctness, PnL math, or real-time WebSocket fanout guarantees.

## Why not jump straight to the Dashboard payload
The dashboard payload (`/status`) aggregates PnL, active trades, pulse metrics, and lifecycle state into a heavy composite object. The `/health` and `/readiness` endpoints represent a distinct, lower-level operational observability contract that precedes dashboard UI concerns.

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_control_health_readiness_observability_contract_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_control_health_readiness_observability_contract_summary(...)`
3. **PR-3** — end-to-end adaptive-control-health-readiness-observability-contract chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_control_health_readiness_observability_contract_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
We are still following the same seam discipline used across the prior stages:
- derive from live repo evidence, not stale intention alone
- keep one narrow abstraction layer at a time
- prefer policy-facing summaries before broad UI aggregation
- keep the system auditable, understandable, and re-derivable later

## Documentation cohesion note
Keep the seam trail in `docs/plans/` instead of bloating root docs with migration-by-migration detail.
