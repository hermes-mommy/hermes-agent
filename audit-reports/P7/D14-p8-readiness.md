# D14: P8 Readiness Audit -- P7 Surveillance MVP Gate Assessment

| Field | Value |
|---|---|
| Audit ID | D14 |
| Phase | P7 Surveillance (P8 Readiness Gate) |
| Date | 2026-06-03 |
| Auditor | P8 Readiness Auditor (independent) |
| Scope | End-to-end P7 pipeline readiness for P8 MVP gate |
| Overall Verdict | **NOT READY** |

---

## 1. Readiness Criteria Table

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | TimescaleDB ingestion path: consumer -> timescale.py -> surveillance.events hypertable | **NOT READY** | `consumer.main()` db_session_factory raises `NotImplementedError`; router does not push events to Redis buffer |
| 2 | Structured logging: all modules use structlog, no raw surveillance data in logs | **READY** | 12/14 modules use `structlog.get_logger()`; 2 acceptable omissions (`__init__.py`, `models.py`); D04 raw data scan found zero matches for GPS, clipboard content, notification body |
| 3 | Health check: /health endpoint exists, surveillance router mounted | **READY** | `GET /health` returns `{"status": "healthy"}`; `GET /health/detailed` checks loop_manager, guardian, Redis; `surveillance_router` imported and mounted at `src/core/main.py:139-141` |
| 4 | No blocking issues: all CRITICAL findings resolved or documented | **NOT READY** | 3 CRITICAL findings unresolved, 2 HIGH findings unresolved (see Section 2) |
| 5 | Dependencies satisfied: Redis, PostgreSQL, TimescaleDB all accessible | **PARTIAL** | Redis DB2 configured on port 6380 with password from env; PostgreSQL/TimescaleDB referenced but session factory not wired; systemd service declares DATABASE_URL env |
| 6 | systemd service ready: can be enabled and started | **PARTIAL** | Service file is structurally complete with security hardening, resource limits, and WantedBy=multi-user.target; however, the consumer it starts will immediately fail due to NotImplementedError in db_session_factory |
| 7 | Discord commands functional: status/pause/resume wired | **READY** | All 3 commands wired in `src/discord/bot.py` lines 213-224; included in `core_names` tuple (lines 231); metadata-only responses with no raw data exposure; Faiz-only access via `is_faiz_interaction()` |

**Summary:** 3 READY, 2 NOT READY, 2 PARTIAL. The pipeline cannot process a single event end-to-end in its current state.

---

## 2. Blocker Summary -- CRITICAL and HIGH Findings

### CRITICAL Findings (3)

#### C1: Data Classification Under-Classified vs Policy

**Source:** Known blocker from research wave.

The `DataClassification` enum in `src/surveillance/classification.py` defines only 3 tiers:

| Tier | Enum Value |
|---|---|
| Internal | `DataClassification.INTERNAL` |
| Confidential | `DataClassification.CONFIDENTIAL` |
| Restricted | `DataClassification.RESTRICTED` |

**Missing:** The Data Governance and Classification Policy requires a **Critical** tier for the most sensitive data categories (biometric, intimate, health-adjacent surveillance data). The enum has no `CRITICAL` member.

**Impact:** All 12 event types in `EVENT_TYPE_CLASSIFICATION` are mapped to one of 3 tiers. Events that should be classified as Critical (e.g. `camera`, `screenshot`, `location`) are currently mapped to Restricted or Confidential, which may result in insufficient encryption profiles, overly permissive access policies, and incorrect retention classes.

**Evidence file:** `src/surveillance/classification.py` lines 39-46 (enum definition), lines 70-157 (12 event type mappings).

#### C2: `invalidate_cache()` Has Zero Production Callers

**Source:** D05-CRIT-01.

The `invalidate_cache()` function in `src/surveillance/consent_gate.py` (line 292) is defined, exported via `__all__` (line 420), and re-exported via `src/surveillance/__init__.py` (lines 16, 76). However, grep across all `src/` files confirms **zero production callers**.

**Impact:** When Faiz withdraws, pauses, or restores consent, the Redis consent cache (TTL 300s) is not invalidated. This creates:
- Up to 300 seconds of continued ingestion after consent withdrawal (SEV1 per ConsentRevocationPolicy Section 16: "Action proceeds with revoked consent").
- Up to 300 seconds of blocked ingestion after consent restoration (SEV2).

The evidence file `docs/setup-evidence/P7/consent-gate-20260602.md` line 64 claims Pub/Sub invalidation via `consent:invalidate` channel, but this is **not implemented**.

**Evidence files:** `src/surveillance/consent_gate.py`, `src/surveillance/__init__.py`.

#### C3: Router-to-Buffer Integration Gap

**Source:** D08-NR-1.

The FastAPI endpoint `POST /surveillance/events` in `src/surveillance/router.py` validates the event and returns 202 Accepted. However, it does **not** push the event to the Redis buffer. The consumer in `consumer.py` expects events to be in the Redis buffer via `buffer.pop_events()`.

**Impact:** The HTTP ingestion path and the async consumer pipeline are disconnected. Events received via the webhook are accepted and immediately lost. No event ever reaches the Redis buffer, the consent gate, the classifier, or the database.

**Evidence file:** `src/surveillance/router.py` (42 lines, no buffer import, no push call).

### HIGH Findings (2)

#### H1: SurveillanceSafeModeGuard Not Wired to Output Paths

**Source:** D04 safety compliance audit.

`SurveillanceSafeModeGuard` in `src/surveillance/safe_mode.py` is well-implemented with 65 parametrized tests. It correctly blocks 6 confrontation action types in SAFE mode. However, **no production code outside the surveillance module** invokes `check_confrontation()` or `check_message_safety()`.

**Production paths NOT wired:**
- Discord message send/response paths
- LLM response rendering / prompt assembly
- Memory recall pipeline
- Persona output chain

**Impact:** In SAFE/HARD STOP mode, surveillance data could still flow to confrontation output because the guard is never called at any output boundary. The safety property is enforced at unit-test level only, not as a runtime guarantee.

**Evidence file:** `src/surveillance/safe_mode.py`, D04 audit report Section 2.

#### H2: `consumer.main()` DB Session Factory Raises NotImplementedError

**Source:** D08-NR-6.

The `main()` entry point in `src/surveillance/consumer.py` (line 409) defines:

```python
def db_session_factory() -> _AsyncDBSession:
    raise NotImplementedError(
        "DB session factory must be configured via environment or dependency injection..."
    )
```

The systemd service (`systemd/guinevere-surveillance.service`) executes `python -m src.surveillance.consumer`, which calls `main()`. The consumer will start, attempt to process its first event, and crash on `_store_event()` when it calls the session factory.

**Impact:** The surveillance consumer service cannot persist any events to the database. Even if the router-to-buffer gap (C3) were fixed, events would accumulate in Redis and never be stored.

**Evidence file:** `src/surveillance/consumer.py` lines 405-412.

---

## 3. Additional MODERATE/LOW Findings from Audit Dimensions

| ID | Severity | Finding | Source |
|---|---|---|---|
| M1 | MODERATE | `get_hmac_secret()` blocks event loop on first call (SOPS subprocess) | D08-NR-2 |
| M2 | MODERATE | `get_retention_days` naming collision between classification.py and retention.py | D08-NR-3 |
| M3 | MODERATE | Evidence file `consent-gate-20260602.md` claims unimplemented Pub/Sub invalidation | D05-MED-01 |
| L1 | LOW | 1 `# type: ignore[union-attr]` in timescale.py line 128 | D02 |
| L2 | LOW | Non-frozen `@dataclass` for `RedisSurveillanceBuffer` | D02 |
| L3 | LOW | `_AsyncDBSession` Protocol defined twice with minor differences | D08-NR-4 |
| L4 | LOW | `_map_event_to_scope` (private) exported in `__all__` | D08-NR-5 |
| L5 | LOW | `asyncio.create_task()` result not assigned in consumer.py | D02 |
| INFO | INFORMATIONAL | SOPS stderr leakage in error logs | D03-M1 |
| INFO | INFORMATIONAL | Nonce prefix logging (acceptable) | D03-M2 |
| INFO | INFORMATIONAL | REDIS_PASSWORD empty string fallback | D03-M3 |

---

## 4. Per-Dimension Verdict Summary

| Dimension | Report | Verdict | Blocking for P8? |
|---|---|---|---|
| D01 Completeness | `D01-completeness.md` | PASS | No |
| D02 Code Quality | `D02-code-quality.md` | NEEDS REVIEW | No (low-severity items only) |
| D03 Security (HMAC) | `D03-security-hmac.md` | PASS | No |
| D04 Safety Compliance | `D04-safety-compliance.md` | NEEDS REVIEW | Yes (H1: guard not wired) |
| D05 Consent Gate | `D05-consent-gate.md` | NEEDS REVIEW | Yes (C2: no invalidation callers) |
| D06 Test Coverage | `D06-test-coverage.md` | PASS (referenced in D01) | No |
| D08 Architecture | `D08-architecture.md` | NEEDS REVIEW | Yes (C3: router-to-buffer, H2: DB session) |
| D09 Integration | `D09-integration.md` | PASS | No |
| D11 Aizanta Isolation | `D11-aizanta-isolation.md` | Referenced but not blocking | No |
| D13 Tasker Docs | `D13-tasker-docs.md` | Referenced but not blocking | No |

---

## 5. Risk Assessment

### What Can Proceed to P8 (No Blockers)

These components are production-ready and do not require changes before P8:

| Component | Status | Rationale |
|---|---|---|
| Health check endpoints (`/health`, `/health/detailed`) | Ready | Functional, tested, mounted |
| Surveillance router (HTTP endpoint) | Ready | HMAC auth, validation, response all work |
| Structured logging | Ready | All modules compliant, no raw data leakage |
| Discord commands (status/pause/resume) | Ready | Wired, metadata-only, Faiz-gated |
| HMAC authentication chain | Ready | Timing-safe, correct ordering, fail-closed |
| Replay protection | Ready | Atomic SET NX EX, correct TTL |
| Redis DB2 buffer module | Ready | Protocol-based, tested |
| Consent gate logic (check_consent) | Ready | All 7 fail-closed conditions pass |
| Data classification engine (logic) | Ready | Fail-closed default, enum-gated |
| Secret scanner | Ready | Regex + entropy, clipboard-only |
| Safe mode guard (logic) | Ready | 65 tests, correct blocking matrix |
| systemd service file (structure) | Ready | Security hardened, resource limited |
| TLS documentation | Ready | Comprehensive, dual-path |
| SOPS secret resolution | Ready | Cache -> env -> SOPS chain |

### What Must Be Fixed Before P8 (Blockers)

These items prevent end-to-end operation or violate safety/policy requirements:

| ID | Finding | Blocks What | Fix Complexity |
|---|---|---|---|
| C3 | Router does not push to Redis buffer | Entire ingestion pipeline | Low: add `buffer.push_event()` call to router endpoint |
| H2 | DB session factory NotImplementedError | Consumer cannot persist events | Medium: wire async SQLAlchemy session factory using DATABASE_URL env |
| C2 | invalidate_cache() has no callers | Consent revocation is delayed 300s | Medium: add calls to consent revocation/restoration handlers |
| H1 | SafeModeGuard not wired to output paths | Safety guarantee not enforced at runtime | Medium: integrate `check_message_safety()` into Discord send and LLM output paths |
| C1 | DataClassification missing Critical tier | Policy non-compliance for sensitive events | Low: add CRITICAL enum member, re-map affected event types |

---

## 6. Recommended Fix Priority Order

The fixes are ordered by dependency chain and impact on end-to-end operability:

| Priority | Fix ID | Action | Depends On | Estimated Effort |
|---|---|---|---|---|
| 1 | C3 | Wire `buffer.push_event()` into `router.receive_event()` | None | 30 min |
| 2 | H2 | Implement async SQLAlchemy session factory in `consumer.main()` using DATABASE_URL | None | 1 hour |
| 3 | C1 | Add `CRITICAL` tier to `DataClassification` enum; re-map camera, screenshot, location events | None | 45 min |
| 4 | C2 | Add `invalidate_cache()` calls to consent revocation/restoration handlers; implement Pub/Sub or direct-call pattern | None | 1.5 hours |
| 5 | H1 | Integrate `SurveillanceSafeModeGuard.check_message_safety()` into Discord send path and LLM output rendering | H2 (consumer must be functional to test) | 2 hours |

**Total estimated fix effort:** approximately 5.5 hours.

**Execution order rationale:**
- Priority 1-2 are the minimum viable pipeline: events must flow from HTTP to Redis to DB.
- Priority 3 is a policy compliance fix that can be done independently.
- Priority 4 is a consent-safety fix that can be done independently.
- Priority 5 is a persona-safety fix that benefits from a working pipeline for integration testing.

---

## 7. systemd Service Assessment

The service file at `systemd/guinevere-surveillance.service` is structurally sound:

| Aspect | Status | Details |
|---|---|---|
| Unit dependencies | PASS | After=guinevere-core.service, docker.service, network.target |
| User/Group isolation | PASS | User=guinevere, Group=guinevere |
| Working directory | PASS | /home/guinevere/code/guinevere |
| Environment variables | PASS | REDIS_PASSWORD, GUINEVERE_DB_PASSWORD, DATABASE_URL from systemd credentials |
| ExecStart | PASS | .venv/bin/python -m src.surveillance.consumer |
| Restart policy | PASS | Restart=always, RestartSec=10 |
| Resource limits | PASS | MemoryHigh=512M, MemoryMax=768M, CPUQuota=100% |
| Security hardening | PASS | NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only |
| ReadWritePaths | PASS | Scoped to code, data, logs, evidence directories |
| Install target | PASS | WantedBy=multi-user.target (can be enabled) |
| Runtime viability | **FAIL** | Consumer will crash on first event due to NotImplementedError in db_session_factory (H2) |

**Verdict:** The service file can be enabled and started (`systemctl enable --now guinevere-surveillance`), but the process will enter a crash-restart loop until H2 is resolved.

---

## 8. Dependency Infrastructure Check

| Dependency | Configured | Accessible | Notes |
|---|---|---|---|
| Redis (port 6380, DB2) | Yes | Assumed yes (connection code correct) | Used by 4 modules: replay, consent_gate, consumer, redis_buffer |
| PostgreSQL/TimescaleDB (port 5433) | Yes (DATABASE_URL in systemd) | Cannot verify without running service | Session factory not wired in consumer.main() |
| SOPS + age keys | Yes (secrets.py) | Assumed yes (subprocess-based) | Cached after first call |
| Cloudflare Tunnel / Tailscale | Documented only | N/A (external infra) | TLS doc covers setup |

---

## 9. Overall Verdict

### NOT READY

P7 surveillance has strong foundations: 22/22 steps complete, 14 well-structured modules, 14 test files, solid security (HMAC + replay + SOPS), correct fail-closed consent logic, and proper Discord command wiring. However, the system **cannot process a single event end-to-end** due to three integration gaps that break the pipeline at two critical points:

1. **Entry point broken:** The HTTP router accepts events but does not buffer them (C3).
2. **Exit point broken:** The consumer can start but cannot write to the database (H2).
3. **Safety gap:** Even if the pipeline worked, consent revocation has a 300-second stale window (C2) and the safe-mode guard is not wired to any output path (H1).

### Conditions for P8 Entry

P8 may proceed **only after** all 5 blockers (C1, C2, C3, H1, H2) are resolved and verified:

- [ ] C3: Router pushes events to Redis buffer
- [ ] H2: Consumer DB session factory connects to TimescaleDB
- [ ] C1: DataClassification enum includes Critical tier with correct event mappings
- [ ] C2: invalidate_cache() called from consent state change handlers
- [ ] H1: SurveillanceSafeModeGuard integrated into at least one production output path

Once these 5 items pass verification, a follow-up D14v2 readiness check should confirm end-to-end event flow before P8 MVP gate approval.

---

## Footer

| Version | Date | Auditor | Changes |
|---|---|---|---|
| 1.0 | 2026-06-03 | D14 P8 Readiness Auditor | Initial P8 readiness assessment. Verdict: NOT READY. 3 CRITICAL, 2 HIGH blockers identified. |

*Read-only audit. No source files were modified.*
