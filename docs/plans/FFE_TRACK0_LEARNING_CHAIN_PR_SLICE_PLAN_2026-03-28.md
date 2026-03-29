# FFE Track 0 — Learning-Chain Integrity PR-Slice Plan

Date: 2026-03-28
Status: active
Source of truth for live/dev verification: `asus-rog-old-laptop:/home/cmp6510/finance_feedback_engine`
Roadmap anchor: `docs/plans/FFE_1_0_HARDENING_ROADMAP_2026-03-27.md` → Track 0

## Objective

Turn Track 0 from a thesis into an auditable delivery sequence.

The goal is not just to "improve learning."
It is to prove the end-to-end chain:

1. execution occurs
2. durable outcome artifact lands
3. decision lineage survives
4. learning ingests the outcome
5. memory/performance state changes durably
6. provider/model weighting or later decision behavior reflects the update

## Operating stance

- Work from the authoritative FFE repo on the gpu laptop / `asus-rog-old-laptop`
- Prefer small TDD-first slices
- No large refactors without a specific live or auditability symptom attached
- Each PR slice should create new proof artifacts, not just move code around
- "Recorded" is not enough; each slice must tighten evidence of "used"

---

## PR-1 — Preserve decision lineage while positions are still open

### Goal
Reduce or eliminate learning skips caused by missing `decision_id` at close time.

### Scope
- preserve/enrich `decision_id` on active position snapshots before they enter recorder state
- prefer existing recorder state, then trade-monitor associations, then other already-existing low-risk lookups
- make close-time lineage recovery a fallback, not the primary strategy

### Why first
This is the first semantic link in the chain that is still visibly breaking.
If lineage is lost, every downstream learning or weight-adaptation claim is compromised.

### Required artifacts
- focused regression coverage for active-position decision-id enrichment
- focused regression coverage for close-time lineage recovery fallback
- explicit logs showing lineage source / attempted sources when recovery is needed

### Acceptance
- `missing decision_id; durable artifact recorded but learning update skipped` drops materially or is eliminated for the covered path
- recorder state preserves decision lineage for normal open→close lifecycle

### Status notes
- Initial seam patch started 2026-03-28 on `trading_loop_agent.py`
- Focused test coverage added for trade-monitor fallback enrichment

---

## PR-2 — Make learning ingestion explicit and non-silent

### Goal
No closed trade should quietly disappear between durable outcome recording and learning ingestion.

### Scope
- create explicit event/log markers for:
  - durable outcome saved
  - learning handoff attempted
  - learning handoff accepted
  - learning handoff skipped
  - learning handoff failed
- ensure every skip/failure includes reason and identifiers sufficient for audit
- normalize distinction between:
  - pending queue state
  - durable outcome artifact
  - learning ingestion event

### Why second
Before changing adaptation behavior, we need trustworthy observability for whether learning actually happened.

### Required artifacts
- structured or high-signal log lines with order id / decision id / product / lineage source
- test coverage for skip/failure reason paths
- operator-facing log trail for one closed trade

### Acceptance
- for every recorded close, an operator can answer whether it was ingested, skipped, or failed
- no ambiguous "recorded but maybe used" path remains in the critical seam

---

## PR-3 — Durable before/after memory/performance state proof

### Goal
Prove that ingested outcomes mutate durable performance/memory state in a way we can inspect later.

### Scope
- identify canonical durable state artifacts for learning effects
- add explicit before/after snapshots or deltas for the learning update path
- make it possible to tie one outcome to one durable state change

### Why third
Learning that only exists in transient logs is not trustworthy.
We need durable evidence that a specific outcome changed memory/performance state.

### Required artifacts
- canonical file(s) or store entry points documented for:
  - outcome persistence
  - memory/performance persistence
- audit fields linking:
  - order id
  - decision id
  - outcome record
  - memory/performance update id or timestamp
- tests for persistence/update behavior where practical

### Acceptance
- one real or near-live closed trade can be traced to a durable state mutation
- operators can inspect the state change without reconstructing everything from logs

---

## PR-4 — Provider/model adaptation proof path

### Goal
Prove that learning-state updates can affect provider/model weighting or selection behavior.

### Scope
- isolate the actual adaptation mechanism(s):
  - provider weights
  - performance tracker
  - debate/ensemble selection logic
  - any reward/feedback analyzer path
- instrument before/after state around adaptation
- separate config normalization from true learning-driven change

### Why fourth
This is the dividing line between a system that records outcomes and a system that adapts.

### Required artifacts
- explicit evidence of weight/selection state before and after a learning-triggering event
- tests proving outcome-driven updates hit the intended adaptation path
- clear logs distinguishing:
  - config merge normalization
  - runtime adaptive update

### Acceptance
- outcome-driven adaptation can be demonstrated with before/after evidence
- no operator needs to guess whether a weight change was learned or merely normalized from config

---

## PR-5 — End-to-end audit harness and live verification runbook

### Goal
Make Track 0 repeatably verifiable by operators, not just developers with context in their heads.

### Scope
- create a compact audit/runbook for proving the chain end to end
- define the exact artifacts/logs/files to inspect
- add a near-live or fixture-driven verification path for regression checks
- update roadmap audit notes with completion evidence per slice

### Why fifth
The last mile is not code; it is trust and repeatability.
The system is only "special" if the learning chain can be demonstrated on demand.

### Required artifacts
- runbook/checklist for:
  - execution → outcome → lineage → learning → state update → adaptation
- operator summary template for future overnight checks
- roadmap updates marking what is proved vs merely suspected

### Acceptance
- an operator can verify the learning chain without deep code spelunking
- Track 0 status can be reported in roadmap terms with evidence, not vibes

---

## Slice ordering rationale

This sequence is intentionally narrow:

- **PR-1** fixes the first broken semantic link
- **PR-2** makes ingestion observable
- **PR-3** proves durable memory/performance mutation
- **PR-4** proves adaptation rather than mere recording
- **PR-5** makes the whole thing auditable and repeatable

Each slice should leave the system better instrumented than before.
If a slice cannot produce new proof artifacts, it is probably too fuzzy and needs to be narrowed.

---

## Audit checklist to update as work lands

- [x] PR-1 landed
- [x] PR-1 live-verified enough to move out of immediate fire-fighting, while still deserving ongoing soak observation
- [x] PR-2 landed
- [x] PR-2 live-verified
- [x] PR-3 landed
- [x] PR-3 live-verified (after surfacing and then resolving autosave/load compatibility regressions under live conditions)
- [ ] PR-4 landed
- [ ] PR-4 live-verified
- [ ] PR-5 landed
- [ ] PR-5 live-verified

## Notes

- Track 0 is now the immediate top-priority roadmap item because reliable learning/adaptation is the differentiator.
- A boring runtime is now a feature; the next work is about subtlety, lineage, memory, and proof.
- If the chain cannot be proved, FFE remains a competent but expensive state-processing machine rather than an adaptive system.

---

## Track 0 verification spine — immediate surgical next steps

This section is the operational spine for the next session(s).
It is intentionally narrower than the roadmap language.
Do not start broad PR-4 implementation from vibes.
Use this spine to verify that the recent Track 0 fixes are actually boring under live conditions.

Working rule:
- if any item below fails, treat that failure as the active Track 0 task
- do not advance to adaptation-proof work while a lower-link verification item is still failing
- prefer one sharply-proved seam over three half-proved ones

### Step 1 — Resolve the `pending_outcomes.json` ambiguity

#### Why this is first
The overnight check showed real executions and repeated `Registered executed order ... for outcome tracking` logs, while `data/pending_outcomes.json` was still `{}`.
That is exactly the kind of ambiguity Track 0 is supposed to eliminate.

#### Questions to answer
- What code path emits `Registered executed order ... for outcome tracking`?
- After that log line, what durable artifact is supposed to exist?
- Is `data/pending_outcomes.json` still the canonical queue/state file?
- If not, what replaced it?
- If yes, why can registration be logged while the file remains empty?

#### Surgical inspection plan
1. locate the exact emitter(s) of the registration log line
2. trace the immediate downstream persistence write(s)
3. identify the canonical durable state location for pending/registered outcomes
4. compare implementation reality vs operator assumption
5. classify the empty-file observation as one of:
   - expected queue drain
   - storage location moved
   - stale/misleading log line
   - true persistence failure

#### Required proof artifact
For one real registration event, record:
- timestamp
- asset/product
- order id
- log line text
- code path/module
- canonical durable artifact path
- evidence that the artifact was or was not updated

#### Pass / fail box
- [ ] PASS: one real registration event can be tied to a canonical durable artifact, or the lack of an artifact is explicitly proved to be expected
- [ ] FAIL: registration is logged but durable state is absent, ambiguous, or only inferable from code spelunking

#### If fail
- fix the persistence seam or stale log wording first
- add a focused regression test for "registration claimed but durable pending-state proof missing"
- do not move to PR-4 work until this ambiguity is removed

---

### Step 2 — Re-soak close-path lineage after PR-1b

#### Why this is second
A missing `decision_id` at close time invalidates every downstream learning/adaptation claim.
PR-1b appears to have improved this, but the roadmap explicitly says it still needs soak verification.

#### Questions to answer
- Are any normal closes still producing `Learning handoff SKIPPED ... reason=missing_decision_id`?
- When lineage is recovered, which source actually wins?
- Is the recent decision-store fallback only a rescue path, or is it masking earlier preservation failure?

#### Surgical inspection plan
1. gather a fresh soak window of close events after commit `914371d`
2. search for:
   - `Learning handoff ATTEMPT`
   - `Learning handoff ACCEPTED`
   - `Learning handoff FAILED`
   - `Learning handoff SKIPPED`
   - `reason=missing_decision_id`
3. build a tiny per-close classification table:
   - close timestamp
   - product/asset
   - order id
   - decision id present or absent
   - lineage source used
   - final handoff outcome
4. for any skip, capture attempted lineage sources in order
5. decide whether the failure is:
   - a preservation bug while position is still open
   - a recovery ordering bug
   - an edge case outside the current intended seam

#### Required proof artifact
A small soak summary covering all closes in the window with explicit handoff status and lineage source.

#### Pass / fail box
- [ ] PASS: no fresh normal close in the verification window ends with `missing_decision_id`
- [ ] FAIL: at least one fresh normal close still skips learning because decision lineage was lost

#### If fail
- patch the earliest preservation point possible, not the broadest fallback layer
- add one narrow regression test for the exact failed lifecycle
- repeat Step 2 before touching adaptation proof work

---

### Step 3 — Re-soak portfolio-memory autosave after `115dc12`

#### Why this is third
The autosave serialization failure was explicitly elevated to priority #1 once it was discovered live.
A learning chain that mutates memory but cannot save it durably is not boring enough.

#### Questions to answer
- Did the `'dict' object has no attribute 'to_dict'` warning actually disappear after deploy?
- Do mixed object/dict entries now round-trip through save/load safely?
- Is the persisted memory artifact still readable after fresh learning events?

#### Surgical inspection plan
1. gather logs after commit `115dc12` deploy window
2. search for:
   - `Failed to auto-save portfolio memory`
   - `'dict' object has no attribute 'to_dict'`
   - portfolio memory update success markers
3. correlate a fresh learning event with:
   - handoff accepted
   - memory update logged
   - autosave path completing without warning
4. inspect the resulting durable memory artifact
5. confirm the artifact can be reloaded without compatibility errors

#### Required proof artifact
For one fresh learning event, record:
- timestamp
- order id
- decision id
- memory update log evidence
- autosave status evidence
- durable file/store path
- load/read confirmation

#### Pass / fail box
- [ ] PASS: no fresh autosave warning appears and the saved memory artifact remains readable after the learning event
- [ ] FAIL: autosave warnings persist, or save/load compatibility remains uncertain

#### If fail
- patch serialization/load compatibility before any adaptation work
- add a regression test that round-trips mixed dict/object entries through save and load
- repeat Step 3 until the seam is boring

---

### Step 4 — Build a one-trade audit trace record

#### Why this is fourth
This converts the new instrumentation into operator-proof evidence instead of scattered greps.
It is also the seed for PR-5, but should be built now while Track 0 is being soaked.

#### Record template
For one real closed trade, capture in one place:
- close timestamp
- asset / product id
- order id
- decision id
- lineage source used
- durable outcome artifact path and record locator
- learning handoff status
- memory/performance mutation evidence
- pending outcome registration/persistence evidence
- adaptive-state evidence (if any)
- open questions / anomalies

#### Surgical inspection plan
1. pick one clean close from the recent live window
2. trace it forward from close detection to outcome recording
3. trace it through learning handoff
4. trace it into memory/performance mutation
5. note whether adaptation evidence exists yet or remains unproved

#### Required proof artifact
A single compact audit note that proves the chain for one trade without re-reading broad runtime history.

#### Pass / fail box
- [ ] PASS: one real trade can be traced end-to-end through outcome, lineage, handoff, and memory evidence with no ad hoc spelunking
- [ ] FAIL: proving one trade still requires broad manual reconstruction from logs and code

#### If fail
- add the missing instrumentation or documentation at the narrowest missing link
- do not compensate with a bigger runbook yet; fix the missing seam evidence first

---

### Step 5 — Only after Steps 1–4 pass: scope PR-4 narrowly

#### Rule
Do not begin with "prove adaptation" as an abstract goal.
Pick one adaptive mechanism and prove that one mechanism changes because of outcomes and is later used.

#### Candidate mechanisms
- provider weights
- performance tracker
- debate / ensemble selector
- reward / feedback analyzer state

#### Surgical inspection plan
1. identify the single true adaptive state holder to target first
2. map:
   - update trigger
   - durable state location
   - later read/use site
3. instrument before/after state around one learning-triggering event
4. prove the later selector/weighting path actually read the changed state

#### Required proof artifact
A before/after record showing:
- learning-triggering outcome identifiers
- adaptive state before
- adaptive state after
- later runtime read/use evidence
- distinction between runtime learning update vs config normalization

#### Pass / fail box
- [ ] PASS: one adaptive mechanism is shown to change because of a real/near-live outcome and later influence runtime behavior
- [ ] FAIL: only memory/performance stats changed, with no proved downstream adaptive effect

#### If fail
- narrow the mechanism further
- instrument the later read/use site
- do not broaden to multiple adaptive paths until one is fully proved

---

## Session-start execution checklist

Use this as the literal next-session checklist.
Proceed top to bottom.
Do not skip a failing box just because a later item sounds more interesting.

### A. Pending outcome persistence seam
- [ ] locate `Registered executed order ... for outcome tracking` emitter
- [ ] identify canonical pending outcome durable state location
- [ ] verify one real registration event against that state
- [ ] classify `{}` in `data/pending_outcomes.json` as expected or broken
- [ ] if broken, patch seam or log wording and add regression test

### B. Close-path lineage soak
- [ ] collect fresh close events after `914371d`
- [ ] classify each close as ACCEPTED / FAILED / SKIPPED
- [ ] verify no fresh `reason=missing_decision_id` on normal closes
- [ ] capture lineage source for each close in sample window
- [ ] if broken, patch earliest preservation point and retest

### C. Portfolio-memory autosave soak
- [ ] collect fresh post-`115dc12` learning events
- [ ] verify no `'dict' object has no attribute 'to_dict'` warnings
- [ ] verify memory update followed by quiet durable save
- [ ] inspect saved memory artifact
- [ ] confirm load/read compatibility after save

### D. One-trade audit note
- [ ] choose one real closed trade
- [ ] capture outcome artifact evidence
- [ ] capture lineage evidence
- [ ] capture handoff evidence
- [ ] capture memory/performance mutation evidence
- [ ] capture pending-state evidence
- [ ] note whether adaptation evidence exists yet

### E. PR-4 narrow scoping (only if A-D pass)
- [ ] choose exactly one adaptive mechanism
- [ ] map update trigger, durable state, and later read site
- [ ] instrument before/after state
- [ ] prove later runtime use of changed state
- [ ] document result as adaptation proof or not-yet-proved

## Stop conditions

Stop forward progress and treat the discovered issue as the active task if any of the following occur:
- a fresh normal close still skips with `missing_decision_id`
- outcome registration still cannot be tied to a durable artifact
- autosave warnings persist or saved memory cannot be read back
- proving one trade still requires broad manual reconstruction

## Advancement rule

PR-4 becomes the active implementation stream only when:
- Step 1 passes
- Step 2 passes
- Step 3 passes
- Step 4 passes

Until then, the correct move is not broader cleverness.
It is making the lower links boring enough to trust.
