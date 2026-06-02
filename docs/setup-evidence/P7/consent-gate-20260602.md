# P7 Consent Gate Evidence — 2026-06-02

**Phase**: P7 — Surveillance Integration
**Date**: 2026-06-02
**Author**: Guinevere (agent) + Faiz (operator)
**Status**: VERIFIED

## 1. Consent Verification Summary

| Check | Status | Evidence |
|-------|--------|----------|
| Surveillance scope consent exists | ✅ PASS | ConsentRevocationPolicy §4 defines `surveillance.*` scopes |
| Consent ledger schema exists | ✅ PASS | `consent.consent_ledger` table in `src/memory/models.py` (line 888) |
| Revocation log schema exists | ✅ PASS | `consent.revocation_log` table in `src/memory/models.py` (line 910) |
| Scope registry exists | ✅ PASS | `consent.scope_registry` table in `src/memory/models.py` (line 931) |
| Safe word protocol defined | ✅ PASS | PersonaSafetyPolicy §7.2, hard_stop_handler.py implemented |
| Surveillance use boundaries defined | ✅ PASS | PersonaSafetyPolicy §12 (allowed vs prohibited uses) |
| Data classification policy exists | ✅ PASS | DataGovernance v1.0 (5 tiers, required metadata) |
| Retention policy defined | ✅ PASS | SurveillanceDataPolicy (7d raw, 90d agg, 1y summaries) |
| AC-SAFE-008 enforcement | ✅ PASS | PersonaSafetyPolicy §12.1 blocks confrontation from surveillance |

## 2. Safety Boundary Compliance

### PersonaSafetyPolicy Constraints
- **F-03 (CRITICAL)**: Surveillance data MUST NOT be used for blackmail/shame → blocked by runtime gate
- **F-13 (HIGH)**: Safe mode surveillance disable is NOT a violation
- **§12 Surveillance Use Boundaries**: Allowed (productivity, health, safety, context, cost) vs Prohibited (blackmail, humiliation, threatening, public disclosure, punishing safe-word, proving cannot escape, intensifying yandere during distress)
- **§12.3 Sensitive Context**: Summarize rather than quote raw data
- **§15 Runtime Enforcement**: Surveillance-use gate required before using raw surveillance facts

### Consent Scopes for P7
| Scope ID | Description | Default Status |
|----------|-------------|----------------|
| `surveillance.app_usage` | Foreground app tracking | GIVEN (opt-out) |
| `surveillance.location` | GPS + geofencing | GIVEN (opt-out) |
| `surveillance.notifications` | Notification capture | GIVEN (opt-out) |
| `surveillance.clipboard` | Clipboard monitoring | GIVEN (opt-out, secret scanning active) |
| `surveillance.screen` | Screen activity | GIVEN (opt-out) |

## 3. Implementation Constraints

1. **Consent check before storage**: Every event MUST pass consent gate before TimescaleDB ingestion
2. **Fail-closed**: If consent DB/cache unavailable → BLOCK ingestion (do not default to ALLOW)
3. **Safe mode**: Pause confrontation features, preserve ingestion pipeline, consent checks still enforced
4. **Secret scanning**: Clipboard events MUST pass secret scanner before storage
5. **No raw data in artifacts**: Evidence files contain only summaries and metadata, never raw payloads
6. **Yandere boundary**: Y4 baseline, Y5 ceiling, Y6 prohibited — surveillance data cannot trigger Y5+ escalation

## 4. Gate Decision

**VERDICT: PROCEED**

All consent prerequisites satisfied. P7 implementation may proceed with the following mandatory gates:
- P7-010: Consent verification gate (runtime check per event)
- P7-011: Safe-mode surveillance blocking (pause confrontation, preserve ingestion)
- P7-009: Clipboard secret scanner (redact before storage)
- AC-SAFE-008: No confrontation/blackmail from surveillance data

## 5. Revocation Path

If Faiz revokes surveillance consent at any time:
1. Safe word triggers HARD STOP → all persona + surveillance paused
2. Consent ledger records WITHDRAWN event
3. Redis cache invalidated via `consent:invalidate` Pub/Sub
4. Consumer checks consent before each event → BLOCK
5. Resume requires explicit `CONSENT_GIVEN` event + recovery trigger

---

*This evidence file satisfies the consent gate requirement for P7 Surveillance Integration.*
*Authority: PersonaSafetyPolicy v1.0 §12, ConsentRevocationPolicy v1.0, SurveillanceDataPolicy v1.0*
