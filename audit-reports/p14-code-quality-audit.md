# P14 Code Quality Audit

> **Auditor:** Independent code quality auditor (Oracle)
> **Date:** 2026-06-18
> **Scope:** All src/wearable/*.py (17 modules), src/discord/cmd_health_report.py, tests/test_wearable.py, tests/test_wearable_integration.py
> **Authority:** AGENTS.md §5 Anti-Pattern Catalog; AGENTS.md §0 BLOCKING Rules

## Summary

| Item | Value |
|---|---|
| Files audited | 20 |
| Critical findings | 2 |
| Warning findings | 5 |
| Info findings | 1 |
| **Verdict** | **NEEDS FIX** |

## Findings

### Critical (blocks completion)

#### CQ-1 — `# type: ignore[import-not-found]` in mi_fitness_client.py:351

- **Evidence:** `src/wearable/mi_fitness_client.py:351` — `import redis  # type: ignore[import-not-found]`
- **Rule violated:** AGENTS.md BLOCKING rule "NEVER use type-safety suppression: `as any`, `@ts-ignore`, `@ts-expect-error`, `# type: ignore`, avoidable `Any`"
- **Required action:** Remove `# type: ignore` comment. Either add `redis` to `pyproject.toml`/`requirements.txt` so the type checker finds it, or use a conditional import pattern that doesn't require suppression.

#### CQ-2 — Duplicate model classes across modules

- **Evidence:**
  - `GHIResult`: defined as `BaseModel` (Pydantic v2) in `models.py:96` AND as `dataclass` in `ghi.py:71`
  - `BaselineResult`: defined in `baseline.py:25` AND as `dataclass` in `ghi.py:33`
  - `MoodModifier`: defined as `BaseModel` (Pydantic v2) in `models.py:135` AND as `dataclass` in `mood_integration.py:52`
- **Rule violated:** Single source of truth for data models; no shadowing canonical types
- **Risk:** Type confusion, inconsistent serialization, dead Pydantic models in models.py
- **Required action:** Consolidate to `models.py` Pydantic models. Remove module-local dataclass definitions. Update imports in ghi.py, baseline.py, mood_integration.py.

### Warning (should fix)

#### CQ-3 — Emoji in user-facing strings

- **Evidence:** `src/wearable/alert_router.py` uses `🚨`, `⚠️`, `ℹ️`, `📋` in Discord embed strings
- **Context:** These are Discord embed titles/content, not internal code. The AGENTS.md rule is "No emoji in code" — debatable for user-facing strings, but flagging for consistency.
- **Required action:** Document the exception or remove emoji and use text labels.

#### CQ-4 — Dead stub methods

- **Evidence:** `alert_router.py:_inc_alert_counter()`, `_observe_delivery_latency()`, `_send_discord_dm()` — all stubs returning `None` or logging only. These are pre-wired hooks for future Prometheus + Discord integration.
- **Required action:** Add `# TODO: wire up after Prometheus/Discord integration` comment or remove stubs.

#### CQ-5 — sync.py uses `importlib.import_module` for static imports

- **Evidence:** `src/wearable/sync.py` uses `importlib.import_module` to import sibling modules at runtime
- **Risk:** Circular import avoidance pattern, slower, harder to trace dependencies
- **Required action:** Replace with direct imports unless circular dependency is confirmed.

#### CQ-6 — Broad `except Exception` in baseline.py and sync.py

- **Evidence:** `baseline.py` and `sync.py` use `except Exception` with `# noqa: BLE001`
- **Context:** Acceptable per noqa BLE001 (broad exception caught intentionally for safety), but flagging for review.
- **Required action:** Document why broad exception is necessary at each site.

#### CQ-7 — Test files use `# type: ignore[assignment]`

- **Evidence:** `tests/test_wearable.py` uses `# type: ignore[assignment]` and `# type: ignore[method-assign]` for monkey-patching private attributes
- **Context:** Acceptable for test-only monkey-patching, not a production code concern
- **Required action:** None (documented as acceptable).

### Info

#### CQ-8 — ghi.py uses `cast()` extensively

- **Evidence:** `src/wearable/ghi.py` has 6 instances of `cast()`
- **Context:** Acceptable for typing when dealing with dynamic SQLAlchemy-like records, but increases type-checker noise.

## Per-File Verdict

| File | Verdict | Notes |
|---|---|---|
| `__init__.py` | PASS | Clean |
| `config.py` | PASS | Clean |
| `errors.py` | PASS | Clean |
| `models.py` | WARNING | GHIResult, MoodModifier defined but never imported by consumers (shadowed by module-local dataclasses) |
| `mi_fitness_client.py` | FAIL | CQ-1: `# type: ignore` at line 351 |
| `normalizer.py` | PASS | Clean |
| `redis_buffer.py` | PASS | Clean |
| `sync.py` | WARNING | CQ-5: importlib pattern, CQ-6: broad exception |
| `writer.py` | PASS | Clean (encryption integration is a separate security finding) |
| `baseline.py` | WARNING | CQ-2: BaselineResult duplicated in ghi.py; CQ-6: broad exception |
| `anomaly.py` | PASS | Clean |
| `ghi.py` | FAIL | CQ-2: GHIResult + BaselineResult duplicated from models.py |
| `mood_integration.py` | FAIL | CQ-2: MoodModifier duplicated from models.py |
| `alert_router.py` | WARNING | CQ-3: emoji, CQ-4: dead stubs |
| `health_consent.py` | PASS | Clean |
| `metrics.py` | PASS | Clean |
| `encryption.py` | PASS | Clean (integration gap is a separate security finding) |
| `cmd_health_report.py` | PASS | Clean |
| `test_wearable.py` | INFO | CQ-7: type:ignore for test monkey-patching (acceptable) |
| `test_wearable_integration.py` | PASS | Clean |

## Recommendation

**NEEDS FIX** — 2 critical findings (CQ-1: type suppression, CQ-2: duplicate models) must be resolved before completion. 5 warnings recommended but not blocking.
