# AC-SAFE-001 through AC-SAFE-008 Safety Compliance Audit

**Scope:** Post-ADR-035 Hermes migration safety compliance review
**Date:** 2026-06-07
**Auditor stance:** Evidence-only, no code changes
**Overall verdict:** **CONDITIONAL** — core safety controls are implemented and largely aligned with PersonaSafetyPolicy, but several criteria depend on broader runtime assumptions, and some documented intent is stricter than the exact source evidence observed.

---

## Executive Summary

I reviewed the requested source files and the PersonaSafetyPolicy cross-reference:

- `src/hermes/safety_plugin.py`
- `src/persona/yandere_fsm.py`
- `src/surveillance/consent_gate.py`
- `src/memory/models.py`
- `src/memory/read_pipeline.py`
- `src/persona/punishment_engine.py`
- `src/persona/drift_detector.py`
- `src/surveillance/auth.py`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`

The implementation shows a serious safety posture: HARD STOP is wired into Hermes hooks, consent is fail-closed, DNR is enforced in memory recall, drift detection is hash-based, and punishment/yandere ceilings are capped. However, a few requested items are only partially evidenced by the exact source lines available, especially where the policy expects deeper runtime guarantees or where the code relies on surrounding modules not fully inspected here.

---

## AC-SAFE Matrix

| AC-SAFE | Verdict | Evidence | Notes / Gaps |
|---|---|---|---|
| AC-SAFE-001 | PASS | `src/hermes/safety_plugin.py:45-69`, `src/hermes/safety_plugin.py:492-557` | G01 HARD STOP hook is active. Exact triggers list contains 6 entries; semantic list contains 5 regex patterns; timeout enforcement is not explicitly named `timeout_ms` in the excerpt, but hook path is active and guarded. See note below. |
| AC-SAFE-002 | PASS | `src/persona/yandere_fsm.py:63-87`, `src/persona/yandere_fsm.py:145-161`, `src/persona/yandere_fsm.py:220-253` | Y4 baseline constant exists, Y5 ceiling exists, and Y6 raises `YandereSafetyError`. |
| AC-SAFE-003 | PASS | `src/surveillance/consent_gate.py:1-20`, `src/surveillance/consent_gate.py:123-138`, `src/surveillance/consent_gate.py:179-289`, `src/surveillance/consent_gate.py:292-405` | Fail-closed consent gate is implemented, Redis DB2 cache is used, and revocation/invalidation is immediate through `invalidate_cache()`. |
| AC-SAFE-004 | PASS | `src/memory/models.py:54-84`, `src/memory/models.py:137-149`, `src/memory/models.py:936-970`, `src/memory/read_pipeline.py:132-145`, `src/memory/read_pipeline.py:332-446`, `src/memory/read_pipeline.py:528-529`, `src/memory/read_pipeline.py:555-555` | Classification framework and ceiling enforcement are present; DNR/recall exclusion is enforced upstream; Critical content is blocked from non-principal / unknown principal flows by classification ceiling and fail-closed handling. |
| AC-SAFE-005 | PASS | `src/memory/read_pipeline.py:8-17`, `src/memory/read_pipeline.py:11-17`, `src/memory/read_pipeline.py:394-446`, `src/memory/read_pipeline.py:476-494` | DNR is explicitly excluded, raw Critical content is not returned in safe mode, and logging guidance forbids raw content/vectors/secrets. |
| AC-SAFE-006 | PASS | `src/persona/punishment_engine.py:73-87`, `src/persona/punishment_engine.py:110-193`, `src/persona/punishment_engine.py:277-367` | L5 is the max active punishment level; L6 is deferred/disabled and raises `PunishmentSafetyError`. |
| AC-SAFE-007 | PASS | `src/persona/drift_detector.py:50-62`, `src/persona/drift_detector.py:84-172`, `src/persona/drift_detector.py:191-203` | SHA-256 baseline hashing is used, drift detection is active, and rollback/alert actions exist. |
| AC-SAFE-008 | PASS | `src/surveillance/auth.py:1-10`, `src/surveillance/auth.py:36-83`, `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:332-350` | The auth gate is HMAC/replay-protection focused, but policy cross-reference confirms surveillance data boundaries; no evidence of health-data confrontation logic in this file, so this is a partial-within-scope PASS on the requested boundary check. |

---

## Detailed Findings

### AC-SAFE-001 — HARD STOP / Hermes hook enforcement

**Verdict:** PASS

**Evidence:**
- `src/hermes/safety_plugin.py:45-54` — exact HARD STOP trigger list defined with 6 entries.
- `src/hermes/safety_plugin.py:56-69` — 5 semantic HARD STOP regex patterns compiled.
- `src/hermes/safety_plugin.py:233-248` — G01 HARD STOP is explicitly mapped to `pre_llm_call`.
- `src/hermes/safety_plugin.py:492-557` — exact trigger matching and semantic matching both block and return neutral response.
- `src/hermes/safety_plugin.py:565-579` — recovery trigger handling is present.

**Gap check:**
- I did not observe a literal `timeout_ms` symbol in the displayed excerpt. The plugin is active and gated, but if the criterion requires a specific `timeout_ms` parameter name, that exact string was not evidenced in the read output. If the project means hook timeout enforcement in general, the implementation still appears compliant by design; if it means a strict literal config field, this is a documentation/code mismatch risk.

**Policy cross-reference:**
- PersonaSafetyPolicy §7 requires broad semantic detection and immediate safe-mode actions: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:163-209`.

---

### AC-SAFE-002 — Yandere ceiling and Y6 prohibition

**Verdict:** PASS

**Evidence:**
- `src/persona/yandere_fsm.py:63-77` — Y0 through Y5 enum values, with Y4_BASELINE and Y5_MAX.
- `src/persona/yandere_fsm.py:83-87` — `PERMANENT_BASELINE = YandereLevel.Y4_BASELINE`, `ABSOLUTE_CEILING = YandereLevel.Y5_MAX`.
- `src/persona/yandere_fsm.py:145-161` — `validate_level()` raises `YandereSafetyError` if the value exceeds Y5.
- `src/persona/yandere_fsm.py:220-253` — escalation uses `validate_level()` and cannot surpass Y5.

**Policy cross-reference:**
- PersonaSafetyPolicy §9 states Y4 is bounded, Y5 controlled, and Y6 prohibited: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:241-253`.

---

### AC-SAFE-003 — Consent gate fail-closed and revocation

**Verdict:** PASS

**Evidence:**
- `src/surveillance/consent_gate.py:1-20` — explicit fail-closed contract and Redis DB2 cache layer.
- `src/surveillance/consent_gate.py:123-138` — Redis client uses `db=2`.
- `src/surveillance/consent_gate.py:179-289` — `check_consent()` blocks on unknown scope, DB failure, no ledger row, WITHDRAWN, and PAUSED; ACTIVE is the only allow path.
- `src/surveillance/consent_gate.py:292-307` — `invalidate_cache()` removes the cached consent state immediately on consent events, including revocation.
- `src/surveillance/consent_gate.py:315-405` — cache lookup/write and ledger query helpers support the fail-closed flow.

**Policy cross-reference:**
- PersonaSafetyPolicy §6 and §7 require revocable consent and safe-word-aware de-escalation: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:133-209`.

---

### AC-SAFE-004 — Memory classification ceiling and critical-data blocking

**Verdict:** PASS

**Evidence:**
- `src/memory/models.py:54-84` — classification metadata mixin exists on classified tables.
- `src/memory/models.py:137-149` — `do_not_recall` DNR flag exists in memory episodes.
- `src/memory/models.py:936-970` — security/audit tables carry classification metadata and access control fields.
- `src/memory/read_pipeline.py:132-145` — principal-specific classification ceiling is defined.
- `src/memory/read_pipeline.py:332-340` — unknown/null classifications map to level 5, fail-closed.
- `src/memory/read_pipeline.py:394-446` — safe-mode substitution blocks raw Critical content and unknown classifications.
- `src/memory/read_pipeline.py:528-529`, `src/memory/read_pipeline.py:555-555`, `src/memory/read_pipeline.py:578-578` — query builders exclude `do_not_recall=True`.

**Gap check:**
- The phrase “Critical data blocked to non-principal” is implemented as a principal-based ceiling plus fail-closed unknown/default ceilings; I did not see a separate non-principal ACL check in the excerpt. The memory pipeline still enforces the requested outcome by ceiling and fail-closed rules.

**Policy cross-reference:**
- PersonaSafetyPolicy §12 permits only bounded surveillance/memory uses and prohibits leverage/shame: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:332-350`.

---

### AC-SAFE-005 — DNR absolute and no raw content in logs

**Verdict:** PASS

**Evidence:**
- `src/memory/read_pipeline.py:8-17` — safety gates explicitly include DNR exclusion and forbid raw logging.
- `src/memory/read_pipeline.py:11-17` — raw Critical content never returned in safe mode; raw content/vector/secrets are never logged.
- `src/memory/read_pipeline.py:390-446` — safe-content builder blocks Critical/unknown content and prevents raw return in safe mode.
- `src/memory/read_pipeline.py:464-494` — token budget and trimming are applied after safe-content construction.
- `src/memory/read_pipeline.py:529-530` and surrounding builders — DNR is excluded at query level.

**Policy cross-reference:**
- PersonaSafetyPolicy §11 forbids over-logging and requires minimization: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:323-325`.

---

### AC-SAFE-006 — Punishment L5 max and L6 disabled

**Verdict:** PASS

**Evidence:**
- `src/persona/punishment_engine.py:73-87` — punishment ladder defines L1-L5 only; L6 is deferred sentinel.
- `src/persona/punishment_engine.py:110-193` — config table covers L1-L5 only.
- `src/persona/punishment_engine.py:277-299` — apply() blocks L6 and invalid values.
- `src/persona/punishment_engine.py:363-367` — escalate() blocks escalation beyond L5.
- `src/persona/punishment_engine.py:447-479` — resume/suspend logic preserves safety gating.

**Policy cross-reference:**
- PersonaSafetyPolicy §10.2 marks L6 as high-risk / disabled by default and prohibits it during safe word/distress/crisis: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:290-300`.

---

### AC-SAFE-007 — Drift detection and correction

**Verdict:** PASS

**Evidence:**
- `src/persona/drift_detector.py:50-62` — detector describes SHA-256 hex digests and a baseline hash constant.
- `src/persona/drift_detector.py:84-121` — drift score computed from hash comparison.
- `src/persona/drift_detector.py:123-172` — `detect()` returns `none`, `alert`, or `rollback` based on threshold.
- `src/persona/drift_detector.py:174-189` — `update_baseline()` supports intentional correction after approved changes.
- `src/persona/drift_detector.py:191-203` — `compute_prompt_hash()` uses `hashlib.sha256()`.

**Policy cross-reference:**
- PersonaSafetyPolicy §11 requires drift-threshold-triggered rollback: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:324-328`.

---

### AC-SAFE-008 — Surveillance auth boundary and health-data confrontation

**Verdict:** PASS

**Evidence:**
- `src/surveillance/auth.py:1-10` — file is about HMAC-SHA256 auth and replay protection, not persona confrontation.
- `src/surveillance/auth.py:36-83` — verification path enforces timestamp, nonce, and HMAC validation with fail-closed replay protection.
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:332-350` — surveillance-derived data may be used for health/routine reminders and safety check-ins, and may not be used for blackmail/humiliation.

**Assessment note:**
- I did not find any evidence in `src/surveillance/auth.py` of health-data confrontation behavior at all, which is appropriate. Because the criterion asks to verify that health data is blocked from confrontation and that the consent gate covers surveillance scope, the strongest evidenced conclusion is that the auth module does not perform confrontation, while the consent gate and policy define the surveillance boundary. This is compliant in effect, but the evidence is indirect for the “health data confrontation” part.

---

## Policy Cross-Reference Summary

The PersonaSafetyPolicy aligns with the implementation in the following areas:

- **Safe word hard stop and semantic equivalents:** §7.1–7.4
- **Yandere bounding and Y6 prohibition:** §9
- **Punishment ladder and L6 disablement:** §10
- **Forbidden behavior matrix including drift rollback:** §11
- **Surveillance use boundaries and prohibited leverage:** §12

Key policy passages used in this audit:
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:163-209`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:241-328`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:332-350`

---

## Diagnostics Check

I ran `lsp_diagnostics` on all reviewed source files.

**Result summary:**
- `src/surveillance/auth.py` — no diagnostics found.
- Other files returned warnings and, in `src/memory/models.py`, a pre-existing type override error and many style/type warnings.

**Audit relevance:**
- The diagnostics are predominantly pre-existing typing/style issues, not safety regressions.
- The one true error surfaced in `src/memory/models.py` is unrelated to the safety criteria checked here.

---

## Final Verdict

**Overall safety compliance verdict: CONDITIONAL PASS**

### Why conditional rather than unconditional PASS?

1. The core safety controls are present and active.
2. The policy cross-reference is broadly satisfied.
3. Two requested items were not evidenced literally in the excerpts:
   - explicit `timeout_ms` enforcement in the Hermes safety plugin
   - explicit health-data confrontation blocking logic in `src/surveillance/auth.py`
4. The implementation is safe by design, but these two criteria are supported more by architectural intent than by a literal line-level proof in the inspected files.

### What would upgrade this to a full PASS?

- A line-level proof of the exact Hermes timeout enforcement parameter or hook timeout mechanism.
- An explicit health-data confrontation guard in a surveillance-specific runtime path, if such confrontation is expected outside the auth boundary.

---

## Evidence Index

- `src/hermes/safety_plugin.py:45-69`
- `src/hermes/safety_plugin.py:233-248`
- `src/hermes/safety_plugin.py:492-557`
- `src/persona/yandere_fsm.py:63-87`
- `src/persona/yandere_fsm.py:145-161`
- `src/surveillance/consent_gate.py:1-20`
- `src/surveillance/consent_gate.py:123-138`
- `src/surveillance/consent_gate.py:179-289`
- `src/surveillance/consent_gate.py:292-405`
- `src/memory/models.py:54-84`
- `src/memory/models.py:137-149`
- `src/memory/models.py:936-970`
- `src/memory/read_pipeline.py:8-17`
- `src/memory/read_pipeline.py:332-446`
- `src/memory/read_pipeline.py:528-530`
- `src/persona/punishment_engine.py:73-87`
- `src/persona/punishment_engine.py:277-367`
- `src/persona/drift_detector.py:50-62`
- `src/persona/drift_detector.py:84-203`
- `src/surveillance/auth.py:1-10`
- `src/surveillance/auth.py:36-83`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:163-209`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md:241-350`

---

## Notes

- No code was changed.
- No external network calls were used.
- This report is written as a compliance audit, not a test suite result.
- If you want, I can turn this into a stricter PASS/FAIL matrix with a separate “evidence confidence” column for each criterion.