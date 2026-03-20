# FFE Stage 54 — Adaptive Control Notification Delivery Contract Seam

## Why this stage exists

Stage 53 closed the **adaptive control dashboard status aggregation contract** seam, normalizing how health/readiness observability state is composed into the high-level `/status` payload, `DashboardAggregator`, and WebSocket fanout.

The next careful seam in the live repo is the **adaptive control notification delivery contract**.

This is the layer where internal dashboard-ready state crosses the system boundary into external notification channels: Telegram bot messages, webhook POST deliveries, and alert dispatch. It formalizes the contract between aggregated internal state and outbound delivery without collapsing into channel-specific implementation details.

## Live repo evidence used for this draft

### Notification delivery paths already exist
- `finance_feedback_engine/integrations/telegram_bot.py`
  - `TelegramApprovalBot`
  - `send_message(...)` / `bot.send_message(...)`
  - `setup_webhook(...)` / webhook registration
  - `callback_query` handling (inline keyboard approval flow)
  - `init_telegram_bot(config)`
- `finance_feedback_engine/integrations/tunnel_manager.py`
  - ngrok tunnel for webhook endpoints
- `finance_feedback_engine/agent/trading_loop_agent.py`
  - `_validate_notification_config()`
  - Telegram delivery fallback to webhook delivery
  - Signal-only mode notification requirement semantics
- `finance_feedback_engine/monitoring/alert_manager.py`
  - `AlertManager` with win-rate and drawdown alert checks
- `finance_feedback_engine/cli/main.py`
  - `--send-alerts` flag for volatility alerts

### Why this stands apart from channel-specific internals
- This stage captures the **delivery contract shape** — which channels exist, how delivery is validated, and how delivery outcomes are reflected back — without re-implementing Telegram's API or ngrok's tunnel protocol.

## Why this is the next honest seam

The live repo separates:
1. Dashboard status aggregation (Stage 53)
2. Notification delivery contract (how aggregated state crosses into external channels)
3. Channel-specific implementation internals (Telegram API wire protocol, ngrok session management)

Stage 54 covers the second.

## Stage 54 scope

### Build from
- Stage 53 adaptive-control-dashboard-status-aggregation-contract summaries
- Notification delivery validation, channel selection, and delivery outcome reflection

### Still explicitly NOT this stage
- Telegram API wire protocol details
- ngrok tunnel session management internals
- Multi-host deployment coordination
- Thompson posterior math / Kelly sizing internals

## PR-sized breakdown
1. **PR-1** — `build_policy_selection_adaptive_control_notification_delivery_contract_set(...)`
2. **PR-2** — `build_policy_selection_adaptive_control_notification_delivery_contract_summary(...)`
3. **PR-3** — end-to-end adaptive-control-notification-delivery-contract chain hardening
4. **PR-4** — `extract_policy_selection_adaptive_control_notification_delivery_contract_summaries(...)`
5. **PR-5** — persistence-backed closeout hardening

## Mapping rule used for this draft
- derive from live repo evidence, not stale intention alone
- keep one narrow abstraction layer at a time
- prefer policy-facing summaries before channel-specific wire protocol details
- keep the system auditable, understandable, and re-derivable later
