# P14 Boundary Compliance Audit

> **Auditor:** Independent boundary compliance auditor (Oracle)
> **Date:** 2026-06-18
> **Scope:** P14 (Wearable Health Pipeline) — consent enforcement, persona safety, data classification, HARD STOP compliance
> **Authority:** AGENTS.md §2.1 Consent-Safety Mandate; §4 Post-Step Checklist; §5 Anti-Pattern Catalog; PersonaSafetyPolicy; Data Governance & Classification Policy

## Summary

| Item | Value |
|---|---|
| Total boundary checks | 24 |
| PASS | 14 |
| FAIL | 8 |
| PARTIAL | 2 |
| **Verdict** | **FAIL — 8 boundary violations must be fixed before completion** |

## Persona Safety Boundary

### mood_integration.py — PASS

- Does NOT import `yandere_fsm.py` (verified via grep: zero matches in all wearable files)
- Imports ONLY `from src.persona.mood_engine import Mood`
- Returns `None` or soft `MoodModifier` (intensity ≤ 0.7) — never mutates Y-level state
- Docstring explicitly states: "Does NOT touch yandere_fsm.py. Only modifies mood_engine.py."

### Y-level isolation proof — PASS

- grep for `yandere_fsm`, `Y5`, `Y6` across all `src/wearable/*.py` returns zero matches
- No health data drives persona escalation
- Punishment/confrontation text never generated from health metrics

### Distress state handling — PARTIAL (M-7)

- `mood_integration.py` checks `persona:state:active` for `argument`/`distress` states
- **Issue:** When Redis key is missing/stale, the safety check silently ALLOWS mood modification
- **Required fix:** Treat `state is None` as deny (fail-closed)

## Consent Boundary

### Scope isolation — PASS

- 7 valid scopes: `wearable-health-hr`, `wearable-health-activity`, `wearable-health-spo2`, `wearable-health-stress`, `wearable-health-sleep`, `wearable-health-ghi`, `wearable-health-alerts`
- `METRIC_TO_SCOPE` maps all 6 `HealthMetricType` values to correct scopes
- Unknown scopes rejected (fail-closed)

### Fail-closed verification — PASS

- `health_consent.py:136-138` returns `_BLOCK_DB_FAILURE` on DB error
- Cache TTL: 300s (5 minutes) — balances revocation latency and DB load

### Revocation completeness — PASS

- `grant_consent()`, `revoke_consent()`, `pause_consent()`, `withdraw_consent()` all implemented
- Redis cache invalidated on grant/revoke
- Paused/withdrawn states distinguished via `ConsentStatus` enum

### Consent gate called by pipeline — FAIL (BC-1)

- `check_wearable_consent()` only referenced inside `health_consent.py` itself
- **No wearable consumer calls it:**
  - `sync.py` — does NOT check consent before fetching from Mi Fitness Cloud
  - `writer.py` — does NOT check consent before persisting to TimescaleDB
  - `alert_router.py` — does NOT check consent before delivering alerts
  - `cmd_health_report.py` — does NOT check consent before querying health data
- **Required fix:** Add consent checks to sync, writer, alert_router pipeline entry points

### Scope cross-contamination — PASS

- Revoking `wearable-health-hr` does not affect `wearable-health-sleep`
- Per-scope consent ledger with independent Redis keys

## Data Classification Boundary

### Wearable vs Surveillance separation — PASS

- Wearable uses `wearable-health:*` scope prefix
- Surveillance uses separate consent ledger
- Redis key namespaces: `wearable:health:*` vs surveillance keys
- No surveillance data mixed into health tables

### Encryption coverage — FAIL (BC-2)

- `encryption.py` defines `encrypt_health_record()` and `decrypt_health_record()`
- **NEVER imported by writer.py or any other consumer**
- `device_id` and `owner_id` stored as plaintext UUIDs in TimescaleDB
- `SENSITIVE_FIELDS = ("notes", "raw_json", "device_id")` declared but contract not honored
- **Required fix:** Wire `encrypt_health_record` into writer.py before persisting

### Log sanitization — PARTIAL

- `device_id` appears in structlog events (re-identifiable with timestamps)
- Acceptable for single-user private Loki but risky if logs are ever exported

## HARD STOP Compliance — FAIL (BC-3)

- grep for `HARD_STOP`, `HALT`, `safe_mode`, `persona.*halt` across all wearable files: **zero matches**
- `mood_integration.py` checks persona state but does NOT check HARD STOP / safe_mode flag
- `alert_router.py` has NO halt awareness — alerts deliver even during system halt
- **Required fix:** Add HARD STOP / safe_mode check to mood_integration.py and alert_router.py

## Operator Autonomy — PASS

- Faiz can revoke any scope via Discord at any time
- No automatic re-granting of consent
- `is_faiz_interaction` auth guard on all Discord commands
- Commands are owner-only (guild.owner_id check)

## Evidence Completeness

### ADR-037 adequacy — PASS

- Documents architecture decision, consent model, persona safety gates, data flow
- References PersonaSafetyPolicy and Data Governance Policy
- Accepted 2026-06-18

### Evidence file coverage — PASS

- `docs/setup-evidence/p14-expansion/evidence-p14-expansion.md` covers all 20 steps
- 12-section schema, file inventory, architecture diagram, risk register, rollback plan

## Findings

### Critical Boundary Violations

| ID | Violation | File | Required Fix |
|---|---|---|---|
| BC-1 | Consent gate never called by pipeline consumers | sync.py, writer.py, alert_router.py, cmd_health_report.py | Add `check_wearable_consent()` calls at pipeline entry points |
| BC-2 | Encryption module unused — sensitive fields stored plaintext in DB | writer.py | Wire `encrypt_health_record` into writer before persist |
| BC-3 | No HARD STOP awareness | mood_integration.py, alert_router.py | Add safe_mode check; refuse to act when system halted |

### High Boundary Violations

| ID | Violation | File | Required Fix |
|---|---|---|---|
| BC-4 | mood_integration.py uses side-channel Redis flag for consent instead of structured ledger | mood_integration.py | Replace `REDIS_CONSENT_REVOKED_KEY` check with `check_wearable_consent()` call |
| BC-5 | Redis buffer stores plaintext sample JSON (device_id, owner_id) | redis_buffer.py | Encrypt buffer payload or strip sensitive fields before pushing |
| BC-6 | cmd_health_report.py queries health data without consent check | cmd_health_report.py | Add consent check before DB query (operator-only mitigates but doesn't eliminate) |

### Medium Boundary Violations

| ID | Violation | File | Required Fix |
|---|---|---|---|
| BC-7 | Missing persona state defaults to allow instead of deny | mood_integration.py:88-95 | Invert: `if state is None: return None` |
| BC-8 | Alert embeds include raw health values (value, baseline, deviation) | alert_router.py | Redact or hash for SEV2/SEV3; keep for SEV0 only |

## Compliance Matrix

| Boundary | Status | Evidence |
|---|---|---|
| Persona safety (no yandere FSM) | PASS | grep: zero matches |
| Distress suppression | PARTIAL | Checks state but missing-state→allow |
| Consent revocation (structured) | PASS | 7 scopes, fail-closed, 300s TTL |
| Consent gate (pipeline) | FAIL | Never called by consumers |
| Data classification (wearable vs surveillance) | PASS | Separate scopes and namespaces |
| Encryption at rest (Critical data) | FAIL | Module defined but unused |
| HARD STOP compliance | FAIL | Zero awareness |
| Operator autonomy | PASS | Discord auth guard, scope revocation |
| Evidence completeness | PASS | ADR-037, evidence file |

## Recommendation

**FAIL** — 8 boundary violations (3 critical, 3 high, 2 medium) must be fixed before completion. Re-audit after fixes.
