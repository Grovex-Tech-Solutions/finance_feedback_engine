# FFE Track 0 Audit Runbook

_Status: draft_

## Purpose

This runbook explains how to verify the FFE learning/adaptation chain without deep code spelunking.

Target outcome:
- prove whether a recent close reached
  1. durable outcome persistence
  2. lineage recovery / attribution
  3. learning handoff
  4. adaptive state mutation

---

## What "good" looks like

A fully qualified adaptive proof packet contains all of the following:

1. **A persisted decision artifact**
   - decision id known
   - decision file exists
2. **A persisted outcome artifact**
   - outcome file exists for the same decision id
3. **Accepted learning handoff**
   - `Learning handoff ACCEPTED`
4. **Adaptive handoff log**
   - `Adaptive learning handoff | ...`
5. **Adaptive mutation log**
   - `Adaptive weights updated | ...`
6. **A real delta**
   - `weights_before != weights_after`

If all six are present, PR-4 is live-proved for that packet.

---

## Key artifact locations

On the Asus host / in the backend container:

- decisions:
  - `/app/data/decisions/*.json`
- outcomes:
  - `/app/data/memory/outcome_*.json`
- portfolio memory:
  - `/app/data/memory/portfolio_memory.json`
- adaptive history:
  - `/app/data/decisions/ensemble_history.json`

---

## Key log markers

### Lower-chain markers
- `Decision saved:`
- `Expecting new trade for ... from decision ...`
- `Learning handoff ATTEMPT`
- `Learning handoff ACCEPTED`
- `Portfolio memory state updated`

### PR-4 markers
- `Adaptive learning handoff | ...`
- `Adaptive weights updated | ...`

### Recovery/attribution markers
- `Upgraded existing recovery decision ... with preserved attribution`
- `shadowed_from_decision_id`

---

## Classification guide

### Plain recovery anchor
This is **not** sufficient for PR-4 proof.

Typical signs:
- `ai_provider = "recovery"`
- no `shadowed_from_decision_id`
- no preserved `ensemble_metadata`
- no preserved `policy_trace`

### Enriched recovery wrapper
This is a good intermediate state and can still satisfy PR-4 if the preserved attribution survives to adaptive mutation.

Typical signs:
- recovery-shaped position or recovery metadata present
- `ai_provider = "ensemble"`
- `recovery_metadata.shadowed_from_decision_id` present
- `ensemble_metadata` preserved
- `policy_trace` preserved

### Fully qualified adaptive packet
This is the target.

Typical signs:
- enriched recovery wrapper or direct ensemble decision
- `Learning handoff ACCEPTED`
- `Adaptive learning handoff | ai_provider=ensemble ...`
- `Adaptive weights updated | ... weights_before != weights_after`

---

## Manual verification checklist

### Step 1 — Identify a candidate recent close
Find a recent `Learning handoff ACCEPTED` line.
Record:
- timestamp
- decision id
- product
- realized pnl

### Step 2 — Inspect the decision artifact
Confirm:
- decision file exists
- `ai_provider`
- `decision_source`
- `recovery_metadata`
- `ensemble_metadata`
- `policy_trace`

Questions:
- is this plain recovery?
- enriched recovery wrapper?
- direct ensemble decision?

### Step 3 — Inspect the outcome artifact
Confirm:
- outcome file exists
- same decision id
- realized pnl present
- timestamp aligns with the accepted handoff window

### Step 4 — Verify lower-chain success
Confirm all of:
- decision persisted
- outcome persisted
- learning handoff accepted
- portfolio memory updated

### Step 5 — Verify adaptation
Look for:
- `Adaptive learning handoff | ...`
- `Adaptive weights updated | ...`

Extract:
- `weights_before`
- `weights_after`
- `history_path`

### Step 6 — Final verdict
Use this matrix:

- lower chain passed, no adaptive logs:
  - learning durability works, PR-4 not proved for this packet
- adaptive logs present, no weight delta:
  - adaptation path fired, but no effective change proved
- adaptive logs present, weight delta present:
  - PR-4 proved for this packet

---

## Operator summary template

```text
Track 0 packet summary
- decision_id:
- product:
- ai_provider:
- shadowed_from_decision_id:
- accepted close:
- outcome artifact:
- adaptive handoff seen: yes/no
- adaptive weight delta seen: yes/no
- weights_before:
- weights_after:
- verdict:
```

---

## Draft next automation target

This runbook should become executable by a proof-packet collector that accepts either:
- a `decision_id`, or
- a recent close window

and emits the summary template above automatically.

### Current draft tool

The first draft collector now exists at:
- `scripts/collect_track0_proof_packet.py`

Example usage:

```bash
python scripts/collect_track0_proof_packet.py <decision_id> \
  --data-dir /app/data \
  --log-file /tmp/ffe-backend.log
```

JSON output:

```bash
python scripts/collect_track0_proof_packet.py <decision_id> \
  --data-dir /app/data \
  --log-file /tmp/ffe-backend.log \
  --json
```
