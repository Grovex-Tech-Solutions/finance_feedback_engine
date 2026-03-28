# Finance Feedback Engine — Repository Audit

**Date:** 2026-03-28  
**Scope:** 515 Python files, ~69K lines of code

This document captures the broader repository audit findings referenced from the main roadmap.
It is intentionally more detailed than the roadmap spine.

---

## Critical Issues

### 1. Root Directory Sprawl
- ~115 `.md` files at repo root
- 13 root-level `test_*.py` files outside `tests/`
- duplicate-looking `core.py` at repo root vs `finance_feedback_engine/core.py`
- assorted root debug / verify / demo scripts
- committed result artifacts not fully covered by `.gitignore`

Suggested remediation:
- archive root markdown/report clutter under a dedicated docs archive
- move orphan tests into `tests/`
- verify and remove stale root duplicate files only after reachability checks
- extend `.gitignore` for result/report artifacts

### 2. Python Version Mismatch
- `pyproject.toml`: `requires-python = ">=3.13"`
- mypy config still targets `3.12`

Suggested remediation:
- align mypy `python_version` to `3.13`

### 3. Test Coverage Gap / CI-Gate Ambiguity
Audit reported approximately:
- 42.3% line coverage
- 30.85% branch coverage

A nominal 70% CI gate appears to exist, but the effective enforcement semantics are unclear.

Suggested remediation:
- explicitly document whether the 70% figure is:
  - enforced,
  - partial-scope,
  - aspirational,
  - or currently bypassed
- then decide whether to raise coverage, adjust the gate, or narrow the measured subset

---

## Architectural Issues

### Duplicate Module Families
Potentially overlapping or stale pairs:
- `backtest/` vs `backtesting/`
- `monitoring/` vs `observability/`
- `coinbase_data.py` vs `coinbase_data_refactored.py`
- `decision_validation.py` vs `decision_validator.py`

Suggested remediation:
- do not delete on sight
- verify import reachability and runtime/reference status first
- then consolidate or clearly delineate ownership

### Pre-commit Config Sprawl
Multiple `.pre-commit-config*.yaml` variants exist, but only one appears active.

Suggested remediation:
- verify active config
- delete or archive stale experimental variants
- document whether flake8 remains intentionally deferred

### Dependency Bounding Strategy
Many dependencies use `>=` with no upper bounds.

Suggested remediation:
- review critical/runtime-sensitive dependencies for upper-bound policy
- document where open upper bounds are intentional

---

## Security Assessment (strong)
The audit reported:
- no hardcoded secrets found
- no dangerous `shell=True` subprocess usage
- pickle deprecation/migration handled
- YAML uses `safe_load`
- JWT validation checks algorithm/expiry/issuer/audience
- SQL uses parameterized queries
- Bandit reported 0 high/medium severity issues

---

## Code Quality / Tooling Notes
The audit reported:
- strong custom exception hierarchy
- no circular import problems detected
- targeted strict mypy use in critical modules
- a few remaining broad `except Exception` blocks worth tightening later

---

## Prioritized Remediation Summary

### P0
- align mypy Python version to 3.13
- extend `.gitignore` for result/report artifacts
- document coverage/gate semantics explicitly

### P1
- move orphan root test files into `tests/`
- verify and remove stale root `core.py` if truly dead
- remove/archive stale pre-commit variants
- archive root markdown/report clutter into a dedicated docs area

### P2
- consolidate duplicate module families or explicitly delineate them
- revisit dependency bounding strategy
- decide whether flake8 should be enabled or intentionally deferred

### P3
- replace broad `except Exception` blocks where they still obscure real failure modes
- continue raising coverage around critical seams

---

## Guardrail
This audit creates a repository-hygiene / architecture-debt workstream.
It does **not** outrank newly exposed live Track 0 regressions in the learning chain.
