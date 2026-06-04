# P7 Surveillance Phase -- Final Audit Report

| Field | Value |
|---|---|
| Phase | P7 -- Surveillance Pipeline (22 steps) |
| Date | 2026-06-03 |
| Auditor | Guinevere (14-dimension parallel audit) |
| Dimensions | D01-D14 |
| Source Modules | 14 files in `src/surveillance/` |
| Test Files | 15 files in `tests/surveillance/` (482 tests) |
| Discord Commands | 3 (status, pause, resume) |
| Systemd | `systemd/guinevere-surveillance.service` |
| Tasker Docs | 6 guides + 1 JavaScriptlet |
| Evidence Root | `docs/setup-evidence/P7/` |
| Overall Verdict | **NOT READY FOR P8 -- REMEDIATION REQUIRED** |

---

## 1. Executive Summary

P7 implements a complete surveillance pipeline: Tasker (Android) -> HMAC-signed POST -> FastAPI receiver -> authentication -> replay protection -> classification -> secret scanning -> Redis buffer -> async consumer -> consent gate -> TimescaleDB ingestion. Three Discord commands provide operational control. All 22 implementation steps are complete with 482 passing tests.

**However, 5 CRITICAL blockers and 4 HIGH findings prevent P8 (MVP gate) readiness.** The pipeline is structurally broken at two points: the router does not push events to the Redis buffer (entry gap), and the consumer's DB session factory raises NotImplementedError (exit gap). Additionally, the data classification system is systematically under-classifying all 12 event types versus the SurveillanceDataPolicy, the consent cache invalidation has no production callers creating a 300-second stale window, and the SurveillanceSafeModeGuard is not wired to any production output path.

**Positive findings**: Security architecture is sound (HMAC chain, replay protection, fail-closed), Aizanta isolation is complete (9/9 checks), data privacy is clean (zero raw data leakage), and integration with P3/P4/P5 is clean (zero cross-imports).

---

## 2. Overall Verdict

### **NOT READY FOR P8**

**P8 gate requires:**
- Zero CRITICAL findings
- All HIGH findings resolved or explicitly accepted by operator
- Pipeline must function end-to-end (entry and exit gaps closed)

**Current status:** 5 CRITICAL + 4 HIGH + 9 MEDIUM/LOW findings.

---

## 3. Per-Dimension Verdict Summary

| Dim | Dimension | Verdict | Key Metrics |
|-----|-----------|---------|-------------|
| D01 | Completeness | **PASS** | 22/22 steps, 14 source modules, 14 test files, PROGRESS.md accurate |
| D02 | Code Quality | **NEEDS REVIEW** | 1 type:ignore, 1 non-frozen dataclass, 314 LSP warnings (env, not code) |
| D03 | Security/HMAC | **PASS** | Chain correct, compare_digest, SET NX EX 660, fail-closed 503 |
| D04 | Safety Compliance | **NEEDS REVIEW** | SafeModeGuard unwired, unknown SAFE actions default ALLOW, _BLOCKED_ACTIONS incomplete |
| D05 | Consent Gate | **NEEDS REVIEW** | invalidate_cache() zero callers, 300s stale window, evidence inaccurate |
| D06 | Test Coverage | **PASS** | 482 tests, AC-SAFE-008 covered, models.py gap (minor) |
| D07 | ADR Compliance | **NEEDS REVIEW** | 6 PASS + 1 PARTIAL, 5 title mismatches, consent invalidation gap |
| D08 | Architecture | **NEEDS REVIEW** | Router->buffer gap, subprocess in async, naming collision, NotImplementedError |
| D09 | Integration | **PASS** | 7/7 points clean, P3/P4/P5 zero surveillance imports |
| D10 | Operational Safety | **NEEDS REVIEW** | Restart=always without StartLimitBurst (infinite crash-loop risk) |
| D11 | Aizanta Isolation | **PASS** | 9/9 checks, ports 6380/5433 only, DB2 only, guinevere user/slice |
| D12 | Data Privacy | **PASS** | Zero raw data in logs/evidence/Discord/tests, redact-not-drop |
| D13 | Tasker Docs | **NEEDS REVIEW** | P7-012 signing string newlines vs colons (100% HMAC failure), 5 em dashes |
| D14 | P8 Readiness | **NOT READY** | 3 CRITICAL + 2 HIGH blockers, pipeline broken at entry and exit |

**Score: 7 PASS, 6 NEEDS REVIEW, 1 NOT READY**

---

## 4. CRITICAL Blockers (Must Fix Before P8)

### C1: Router Does Not Push Events to Redis Buffer
- **Source:** D08-NR-1, D14
- **Impact:** Pipeline broken at entry -- events received but never buffered for consumer
- **Location:** `src/surveillance/router.py` -- `POST /surveillance/events` handler
- **Fix:** After successful HMAC/auth/classification, call `RedisSurveillanceBuffer.push_event()` to push to DB2
- **Effort:** 30 min
- **Verification:** Unit test confirming push_event called after 202 response

### C2: Consumer DB Session Factory = NotImplementedError
- **Source:** D08-NR-6, D14
- **Impact:** Pipeline broken at exit -- consumer can pop from Redis but cannot write to TimescaleDB
- **Location:** `src/surveillance/consumer.py` `main()` function
- **Fix:** Implement async SQLAlchemy session factory using `DATABASE_URL` env var + asyncpg
- **Effort:** 1 hour
- **Verification:** consumer.main() starts without raising NotImplementedError, session_factory produces working sessions

### C3: DataClassification Missing Critical Tier + Under-Classification
- **Source:** D04, D07, research (bg_cde50054)
- **Impact:** All 12 event types systematically under-classified vs SurveillanceDataPolicy
- **Location:** `src/surveillance/classification.py`
- **Fix:**
  1. Add `Critical` to `DataClassification` enum
  2. Re-map all 12 event types per SurveillanceDataPolicy Appendix A:
     - app_usage, screen_state, active_window, idle_time -> Restricted (not Internal)
     - notification, browser -> Restricted (not Confidential)
     - location, health -> Critical (not Confidential)
     - clipboard, screenshot, camera -> Critical (not Restricted)
  3. Update retention day mappings for Critical tier
  4. Update 37+ existing classification tests
- **Effort:** 45 min (code) + 30 min (test updates)
- **Verification:** All 12 event types match SurveillanceDataPolicy Appendix A classifications

### C4: invalidate_cache() Has Zero Production Callers
- **Source:** D05-CRIT-01
- **Impact:** Consent withdrawal delayed up to 300 seconds due to stale positive cache; operator revokes consent but system continues ingesting for 5 minutes
- **Location:** `src/surveillance/consent_gate.py` -- `invalidate_cache()` function exists but is never called
- **Fix:** Two options (pick one):
  - **Option A (Redis Pub/Sub):** Subscribe consumer to `consent:invalidate` channel, call `invalidate_cache(scope)` on message
  - **Option B (Discord command hook):** Wire `/consent-revoke` Discord command to call `invalidate_cache()` via API
  - **Option C (TTL reduction):** Reduce consent cache TTL from 300s to 30s (tradeoff: more DB queries)
- **Effort:** 1.5 hours (Option A), 30 min (Option C)
- **Verification:** After consent revocation, next event check returns BLOCK within the chosen window

### C5: SurveillanceSafeModeGuard NOT Wired to Production Output
- **Source:** D04
- **Impact:** Confrontation blocking logic exists but is never invoked; in SAFE mode, surveillance data could theoretically reach persona output paths through future integrations
- **Location:** `src/surveillance/safe_mode.py` -- `SurveillanceSafeModeGuard` class is exported but has zero production callers
- **Fix:** Wire into persona response pipeline or memory injection pipeline:
  - Add guard check in `src/memory/read_pipeline.py` before surveillance context injection
  - Or add guard check in `src/persona/` response generation before including surveillance-derived facts
- **Effort:** 2 hours (requires understanding persona pipeline)
- **Verification:** In SAFE mode, surveillance-derived confrontation attempts are blocked with logged decision

---

## 5. HIGH Findings

### H1: _BLOCKED_ACTIONS Does Not Cover All 7 Prohibited Uses
- **Source:** D04
- **Gap:** PersonaSafetyPolicy section 12.2 lists 7 prohibited uses. `_BLOCKED_ACTIONS` covers 6 (confrontation, blackmail, punishment, jealousy_escalation, dependency_manipulation, intimate_data_reference). Missing: humiliation and public disclosure as distinct actions.
- **Fix:** Add `humiliation` and `public_disclosure` to `_BLOCKED_ACTIONS` frozenset
- **Effort:** 15 min
- **Verification:** test_safe_mode.py covers all 8 blocked actions (6 existing + 2 new)

### H2: P7-012 Signing String Format Mismatch
- **Source:** D13
- **Impact:** 100% Tasker HMAC failure -- P7-012 section 5.1 documents newlines but server uses colons
- **Location:** `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` lines 224-237 and 389
- **Fix:** Replace newline-separated signing string with colon-separated: `method:path:timestamp:nonce:body`
- **Effort:** 15 min
- **Verification:** P7-012 signing format matches auth.py:71 and hmac-sign.js:34

### H3: Unknown SAFE-Mode Actions Default to ALLOWED
- **Source:** D04
- **Impact:** In SAFE mode, an unrecognized action type passes through without blocking; conservative safety would default to BLOCK
- **Location:** `src/surveillance/safe_mode.py` -- `check_action()` default branch
- **Fix:** Change default from `allowed=True` to `allowed=False` for unknown actions in SAFE mode
- **Effort:** 15 min
- **Verification:** test_safe_mode.py includes unknown action test case returning blocked in SAFE mode

### H4: systemd Restart=always Without StartLimitBurst
- **Source:** D10
- **Impact:** Infinite crash-loop possible if consumer has a persistent bug; could exhaust Redis connections or DB pool
- **Location:** `systemd/guinevere-surveillance.service`
- **Fix:** Add `StartLimitIntervalSec=300` and `StartLimitBurst=5` to [Unit] section
- **Effort:** 10 min
- **Verification:** Service stops restarting after 5 failures in 5 minutes

---

## 6. MEDIUM/LOW Findings

| ID | Finding | Severity | Fix |
|----|---------|----------|-----|
| M1 | `# type: ignore[union-attr]` in timescale.py:128 | MEDIUM | Replace with proper Optional handling or assert |
| M2 | Non-frozen dataclass `RedisSurveillanceBuffer` holds mutable Redis client | LOW | Document as intentional (mutable state holder) or refactor to Protocol-only |
| M3 | `get_retention_days` naming collision: classification.py and retention.py | LOW | Rename classification.py version to `get_classification_retention_days` |
| M4 | `_map_event_to_scope` (private) exported in `__all__` | LOW | Remove from __all__ or rename without underscore |
| M5 | `get_hmac_secret()` blocks event loop via subprocess.run() on first call | MEDIUM | Use asyncio.create_subprocess_exec() or cache secret at startup |
| M6 | 5 em dashes in P7-012 doc | LOW | Replace with hyphens |
| M7 | Evidence file claims Redis Pub/Sub invalidation that doesn't exist in code | MEDIUM | Remove Pub/Sub claim from consent-gate evidence file |
| M8 | SOPS stderr included in error message (minor info leak) | LOW | Strip stderr before including in exception message |
| M9 | models.py has no dedicated test file | LOW | Add test_models.py for Pydantic model validation |

---

## 7. Dimensions That PASS Cleanly

### D01: Completeness -- PASS
All 22 P7 steps (P7-001 through P7-022) plus P7-NEW implemented. Evidence folders exist for all 23 steps. PROGRESS.md accurately reflects 77.3% overall progress. 14 source modules, 15 test files, 3 Discord commands, 1 systemd service, 6 Tasker docs, 1 JavaScriptlet.

### D03: Security & HMAC -- PASS
Authentication chain verified: `validate_timestamp` (300s window) -> `check_nonce` (atomic SET NX EX 660, Redis DB2) -> `verify_hmac` (hmac.compare_digest, timing-safe). Signing string format `method:path:timestamp:nonce:body` consistent across server (auth.py:71) and client (hmac-sign.js:34). Redis failure returns 503 (fail-closed). Secret resolution: env var -> SOPS decrypt -> singleton cache. TLS configuration documented for Cloudflare Tunnel and Tailscale HTTPS.

### D06: Test Coverage -- PASS
482 tests collected across 15 files. All 14 source modules have test coverage (models.py tested indirectly via test_router.py). AC-SAFE-008 fully covered in test_safe_mode.py (63 tests). Security scenarios: HMAC rejection (15 tests), replay attack (26 tests), nonce dedup (26 tests). Fail-closed consent (54 tests). Secret scanning (50 tests). E2E pipeline (10 tests, gated by --run-e2e). Minor gap: no dedicated test_models.py.

### D09: Integration -- PASS
All 7 integration points verified clean:
1. main.py: surveillance_router mounted at `/surveillance` prefix
2. bot.py: 3 commands wired (status, pause, resume), 11 wired + 22 stubs, core_names updated
3. Redis DB2: 4 files use port 6380 db=2, key namespaces non-overlapping
4. TimescaleDB: surveillance.events hypertable in surveillance schema
5. P3 Memory: ZERO surveillance imports (schema table definitions only)
6. P4 Persona: ZERO surveillance references
7. P5 Agent Loop: only main.py router mount, routes.py and loops/ have zero surveillance refs

### D11: Aizanta Isolation -- PASS
9/9 isolation checks pass:
- Redis: port 6380 only, DB2 only (not DB0/DB1/DB3/DB5)
- PostgreSQL: port 5433 only, guinevere database only
- Docker: guinevere-net (172.28.0.0/16) separate from aizanta (172.18.0.0/16)
- Code: zero aizanta text references in surveillance code
- Schema: surveillance schema only, never public
- systemd: guinevere user/slice, ProtectSystem=strict

### D12: Data Privacy -- PASS
Zero raw surveillance data found in:
- Log output: all structlog messages contain metadata only (event_type, device_id, classification)
- Evidence files: all synthetic/placeholder data, no real GPS/clipboard/notifications
- Discord responses: embed shows event counts, last event type, consent status -- no payloads
- Test fixtures: 100% synthetic (device_id="test-device-001", coordinates 0.0/0.0)
- Secret redaction: clipboard scanner redacts with [REDACTED] marker, does not drop events

---

## 8. P8 Gate Decision

### **GATE: BLOCKED**

P7 surveillance implementation is **structurally complete** but **functionally broken** at two critical pipeline points and has safety/compliance gaps that must be resolved before P8 (MVP gate).

**What is ready for P8:**
- Security architecture (HMAC, replay, TLS) -- fully implemented and verified
- Data privacy (zero leakage, redact-not-drop) -- clean
- Aizanta isolation (ports, DBs, networks, user) -- clean
- Integration boundaries (P3/P4/P5 zero cross-imports) -- clean
- Test coverage (482 tests, AC-SAFE-008 covered) -- comprehensive
- Operational infrastructure (systemd, Redis TTL, retention tiers) -- configured

**What blocks P8:**
1. Pipeline entry gap (router -> Redis buffer not connected)
2. Pipeline exit gap (consumer -> TimescaleDB session factory not implemented)
3. Data classification under-classified vs policy (all 12 event types wrong)
4. Consent cache invalidation not wired (300s stale window)
5. Safe mode guard not wired to production output
6. Tasker doc signing format mismatch (100% HMAC failure)

---

## 9. Remediation Priority Order

| Priority | ID | Fix | Est. Time | Blocks P8? |
|----------|----|-----|-----------|------------|
| 1 | C1 | Wire router -> Redis buffer push | 30 min | YES |
| 2 | C2 | Implement consumer DB session factory | 1 hour | YES |
| 3 | C3 | Fix DataClassification enum + event mappings | 1.25 hours | YES |
| 4 | H2 | Fix P7-012 signing string format | 15 min | YES |
| 5 | H4 | Add StartLimitBurst to systemd | 10 min | YES |
| 6 | C4 | Wire consent cache invalidation | 30 min - 1.5 hours | YES |
| 7 | C5 | Wire SafeModeGuard to production output | 2 hours | YES |
| 8 | H1 | Add humiliation + public_disclosure to blocked actions | 15 min | YES |
| 9 | H3 | Change unknown SAFE action default to BLOCK | 15 min | YES |
| 10 | M5 | Replace subprocess.run with async subprocess | 30 min | NO |
| 11 | M1 | Fix type:ignore in timescale.py | 15 min | NO |
| 12 | M7 | Fix consent evidence Pub/Sub claim | 10 min | NO |
| 13 | M3 | Rename get_retention_days collision | 10 min | NO |
| 14 | M6 | Fix 5 em dashes in P7-012 | 10 min | NO |
| 15 | M4 | Remove private function from __all__ | 5 min | NO |
| 16 | M8 | Strip SOPS stderr from error messages | 10 min | NO |
| 17 | M2 | Document non-frozen dataclass as intentional | 5 min | NO |
| 18 | M9 | Add test_models.py | 30 min | NO |

**Total estimated remediation: ~8 hours for P8 blockers, ~1.5 hours for non-blockers.**

---

## 10. Appendix A: Audit Report File Index

| File | Dimension | Size | Verdict |
|------|-----------|------|---------|
| `audit-reports/P7/D01-completeness.md` | Completeness | 14.0 KB | PASS |
| `audit-reports/P7/D02-code-quality.md` | Code Quality | 11.7 KB | NEEDS REVIEW |
| `audit-reports/P7/D03-security-hmac.md` | Security/HMAC | ~15 KB | PASS |
| `audit-reports/P7/D04-safety-compliance.md` | Safety Compliance | 19.0 KB | NEEDS REVIEW |
| `audit-reports/P7/D05-consent-gate.md` | Consent Gate | ~12 KB | NEEDS REVIEW |
| `audit-reports/P7/D06-test-coverage.md` | Test Coverage | 19.0 KB | PASS |
| `audit-reports/P7/D07-adr-compliance.md` | ADR Compliance | 22.5 KB | NEEDS REVIEW |
| `audit-reports/P7/D08-architecture.md` | Architecture | ~15 KB | NEEDS REVIEW |
| `audit-reports/P7/D09-integration.md` | Integration | ~12 KB | PASS |
| `audit-reports/P7/D10-operational-safety.md` | Operational Safety | 12.4 KB | NEEDS REVIEW |
| `audit-reports/P7/D11-aizanta-isolation.md` | Aizanta Isolation | ~10 KB | PASS |
| `audit-reports/P7/D12-data-privacy.md` | Data Privacy | 13.6 KB | PASS |
| `audit-reports/P7/D13-tasker-docs.md` | Tasker Docs | ~12 KB | NEEDS REVIEW |
| `audit-reports/P7/D14-p8-readiness.md` | P8 Readiness | 15.9 KB | NOT READY |

---

## 11. Appendix B: Research Report Index

| File | Topic |
|------|-------|
| `research-reports/P7/timescaledb-patterns.md` | TimescaleDB hypertable patterns, 3-tier retention |
| `research-reports/P7/fastapi-hmac-patterns.md` | FastAPI HMAC auth, Redis nonce, Stream buffering |
| `research-reports/P7/consent-ledger-patterns.md` | Consent hash chain, fail-closed, cache invalidation |
| `research-reports/P7/systemd-service-patterns.md` | Service unit template, resource limits, security |
| `research-reports/P7/tasker-hmac-patterns.md` | Tasker HTTP Request + CryptoJS HMAC patterns |
| `research-reports/P7/secret-scanning-patterns.md` | Gitleaks/detect-secrets regex patterns |
| `research-reports/P7/discord-command-patterns.md` | GuinevereBot command wiring, ephemeral responses |

---

## 12. Appendix C: Methodology

### Audit Process
1. **Research wave**: 10 parallel explore agents mapped P7 surfaces (module deps, safety boundaries, HMAC chain, test coverage, Redis DB usage, Aizanta isolation, Tasker docs, cross-ref P3/P4/P5, data classification, AC-SAFE-008 compliance)
2. **Audit wave**: 14 parallel specialist agents, each writing an independent dimension report to `audit-reports/P7/`
3. **Synthesis**: Parent (Guinevere) collected all 14 reports, cross-referenced findings, classified severity, and produced this final synthesis

### Agent Categories Used
- `explore` (10 agents): Codebase mapping, pattern discovery, cross-reference scanning
- `unspecified-high` (5 agents): D01, D02, D07, D08, D09 -- completeness, code quality, ADR, architecture, integration
- `security` (5 agents): D03, D04, D05, D11, D12 -- HMAC, safety, consent, isolation, privacy
- `testing` (1 agent): D06 -- test coverage analysis
- `writing` (1 agent): D13 -- Tasker documentation audit
- `unspecified-high` (1 agent): D14 -- P8 readiness assessment

### Evidence Standards
- Each dimension agent independently verified file existence via filesystem tools
- Code analysis based on direct file reads, not cached summaries
- Cross-dimensional findings validated against multiple sources before classification
- CRITICAL classification requires pipeline break or safety boundary violation
- HIGH classification requires spec non-compliance or functional gap
- MEDIUM classification requires code quality or documentation issue
- LOW classification requires minor cleanup or improvement opportunity

---

## 13. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-03 | Guinevere | Initial P7 final audit -- 14 dimensions, 5 CRITICAL + 4 HIGH + 9 MEDIUM/LOW findings |

### Operator Sign-Off

P8 gate BLOCKED pending remediation of 5 CRITICAL + 4 HIGH findings. Estimated remediation effort: ~8 hours. Recommend Faiz reviews CRITICAL findings C1-C5 and approves remediation order before proceeding.

> Audit complete. 7 of 14 dimensions PASS cleanly. Pipeline architecture is sound but broken at entry and exit points. Safety boundaries are designed but not fully wired. Ready for targeted remediation, not for P8.
