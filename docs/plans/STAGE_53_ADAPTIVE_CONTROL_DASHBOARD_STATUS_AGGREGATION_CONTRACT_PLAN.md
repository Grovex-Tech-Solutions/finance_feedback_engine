# FFE Stage 53 — Adaptive Control Dashboard Status Aggregation Contract Seam

## Why this stage exists

Stage 52 closed the **adaptive control health readiness observability contract** seam, normalizing how lifecycle control state is reflected in low-level `/health` and `/readiness` endpoints.

The next careful seam in the live repo is the **adaptive control dashboard status aggregation contract**.

This is the layer where operational health, lifecycle control state, active trade metrics, and portfolio PnL are combined into a high-level composite status payload. It feeds the `/status` endpoint, the `DashboardAggregator`, the live CLI UI, and the WebSocket (`/ws`) stream.

## Live repo evidence used for this draft

### Dashboard status and aggregation endpoints already exist
- `finance_feedback_engine/api/routes.py`
  - `@status_router.get("/status")`
- `finance_feedback_engine/cli/dashboard_aggregator.py`
  - Aggregates active positions, best/worst trades, daily/weekly PnL, and market pulse context
- `finance_feedback_engine/api/bot_control.py`
  - `AgentStatusResponse` model and websocket (`/ws`) fanout of status updates
- `finance_feedback_engine/cli/live_dashboard.py` and `pulse_formatter.py`
  - Rich terminal UIs dependent on this aggregated data shape

### Why this stands apart from external integrations
- This is the final internal observability shape before data leaves the system entirely (via Telegram bots, external webhooks, or multi-host orchestration meshes).

## Why this is the next honest seam

The live repo separates:
1. Low-level health/readiness observability (Stage 52)
2. High-level dashboard status aggregation and WebSocket fanout (Stage 53)
3. External notification/alerting channels (like Telegram bots)

Stage 53 covers the second point, cleanly encapsulating the composite observability payload without yet taking responsibility for delivering it to third-party integrations like Telegram.

## Stage 53 scope

### Build from
- Stage 52 adaptive-control-health-readiness-observability-contract summaries
- The composite state dependencies of `/status` and `DashboardAggregator`

### Stage 53 should preserve as policy-facing signals
- How many comparable adaptive-control-health-readiness-observability-contract artifacts progressed into dashboard-status-aggregation-ready state updates
- How many remained shadow / primary-cutover / manual-hold / deferred shaped
- Ensure that the generation of the heavy dashboard payload remains a traceable policy node rather than an opaque side-effect

## Still explicitly NOT this stage
- Telegram bot notification logic
- External webhook deliveries
- Advanced cross-host orchestration metrics
- Manual trade execution pathways

## Careful seam definition

### adaptive-control-dashboard-status-aggregation-contract-ready
A normalized policy-selection layer that says:
- adaptive-control-health-readiness-observability-contract artifacts were eligible to be aggregated into the high-level dashboard status payload
- the status-facing summary preserves the composite payload shape discipline
- visibility of the dashboard fanout pipeline remains traceable

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_control_dashboard_status_aggregation_contract_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_control_dashboard_status_aggregation_contract_summary(...)`
3. **PR-3** — end-to-end adaptive-control-dashboard-status-aggregation-contract chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_control_dashboard_status_aggregation_contract_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
- derive from live repo evidence, not stale intention alone
- keep one narrow abstraction layer at a time
- prefer policy-facing summaries before broad UI aggregation
- keep the system auditable, understandable, and re-derivable later
