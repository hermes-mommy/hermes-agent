# P22 Brutal Audit Report — 2026-06-28

> **Auditor**: Guinevere (parent agent, 8 parallel explore sub-agents + direct source reading)
> **Scope**: P22 Life Integration Hub — full codebase, tests, adapters, consent gate, security, evidence, audit trail, previous verdicts, implementation completeness
> **Method**: Direct source file reading (10 core files) + 8 parallel explore agents covering 10 audit angles
> **Verdict**: **FAIL** — P22 is not production-ready. 5 CRITICAL, 10 HIGH, 17 MEDIUM findings.

---

## Executive Summary

P22 is a well-architected system with genuine engineering quality in its core pipeline (classify → consent-gate → execute → audit). The L1-L4 permission tier system is sound. The hash-chain audit trail uses real SHA256 with WORM enforcement. Previous 26 audits are substantive — not rubber-stamps.

**However, P22 is NOT production-ready despite "FULL-COMPLETION" claims.** Only 3 of 13 adapters are active. Discord slash commands are not registered. The consent gate has a fail-open hole that was never actually fixed. The audit writer is disabled in production. The handoff document contains false adapter names. The README contradicts itself. Rate limiting is absent. The P20 "soak" is 37 minutes, not 6 hours.

### Findings Summary

| # | Severity | Angle | Finding | Status |
|---|----------|-------|---------|--------|
| F01 | CRITICAL | 7 | Discord slash commands NOT REGISTERED in bot tree | FAIL |
| F02 | CRITICAL | 10 | Only 3/13 adapters ACTIVE — 10 CONFIG_MISSING | FAIL |
| F03 | CRITICAL | 3 | ConsentGate fail-open when `hard_stop_checker=None` — never fixed | FAIL |
| F04 | CRITICAL | 2 | Unknown actions default to L1_READ — can bypass consent | FAIL |
| F05 | CRITICAL | 8 | AuditWriter target=None in production — audit events NOT written to DB | FAIL |
| F06 | HIGH | 10 | Phantom adapters: weather/search/obscura don't exist | FAIL |
| F07 | HIGH | 7 | No rate limiting on FastAPI endpoints | FAIL |
| F08 | HIGH | 1 | GitHub client silently returns `[]`/`{}` on non-200 — no 429 handling | FAIL |
| F09 | HIGH | 1 | Calendar/Drive: no 429 retry — will fail on rate limit | FAIL |
| F10 | HIGH | 5 | X Poster leaks first 8 chars of access token in logs | FAIL |
| F11 | HIGH | 2 | dry_run classifies with `integration_id` not `adapter.config.provider` | FAIL |
| F12 | HIGH | 3 | 3 HARD STOP fail-open windows in shims and consent gate | FAIL |
| F13 | HIGH | 8 | TRUNCATE not in WORM contract — table owner can wipe audit log | FAIL |
| F14 | HIGH | 9 | Implementation R1 fix log distorts NEEDS_REVIEW → PASS | FAIL |
| F15 | HIGH | 9 | Round-2 summary-adjudication aggressively reclassifies findings | FAIL |
| F16 | MEDIUM | 10 | README contradiction: "FULL-COMPLETION" vs "definition/planning only" | FAIL |
| F17 | MEDIUM | 10 | PROGRESS.md shows P22 as ⏸ PENDING despite activation | FAIL |
| F18 | MEDIUM | 10 | C10 verification file missing — only 11 C-files, not 12 | FAIL |
| F19 | MEDIUM | 4 | Test count discrepancy: README 897 vs runtime-proof 753 | FAIL |
| F20 | MEDIUM | 1 | Browser status drift: "OK (local)" → CONFIG_MISSING | FAIL |
| F21 | MEDIUM | 8 | Audit write failures are SILENT — logged, not raised | FAIL |
| F22 | MEDIUM | 8 | `seed_last_hash()` returns "" on error — breaks chain silently | FAIL |
| F23 | MEDIUM | 1 | Registry race: get()/list_all() sync without lock, register() async with lock | FAIL |
| F24 | MEDIUM | 8 | `AuditChainVerificationError` defined but `verify_chain()` returns bool | FAIL |
| F25 | MEDIUM | 8 | No UUID v7 — uses UUID v4 (not a claimed feature but expected) | OBSERVATION |
| F26 | MEDIUM | 7 | `consent_callback` name collision across cmd_consent.py and cmd_integrations.py | FAIL |
| F27 | MEDIUM | 7 | Bare `except Exception: # noqa: BLE001` in cmd_integrations.py:130 | FAIL |
| F28 | MEDIUM | 5 | `_rpw` variable stores REDIS_PASSWORD — could leak in error context | FAIL |
| F29 | MEDIUM | 8 | `chain_version=2` hardcoded — no upgrade path | OBSERVATION |
| F30 | MEDIUM | 5 | `secrets.py` provider abstraction is DEAD CODE — never instantiated | FAIL |
| F31 | MEDIUM | 6 | P20 "soak" is 37 minutes, not 6 hours — NRestarts=0 is post-restart only | FAIL |
| F32 | MEDIUM | 8 | No external signature on audit chain — pure intra-chain SHA256 | OBSERVATION |

**Total: 5 CRITICAL, 10 HIGH, 17 MEDIUM (29 actionable + 3 observations)**

---

## Audit Angle 1: Adapter Correctness

**Source**: Parent source reading + Agent bg_b29db63e (3m10s)

### Per-Adapter Matrix (13 actual adapters)

| # | Adapter | Backend | Real? | Active? | L4 Actions | Key Issues |
|---|---------|---------|-------|---------|------------|------------|
| 1 | browser | Brave/Exa search, fetch shim, obscura CDP | REAL shims | NO | none | search returns config_missing honestly |
| 2 | gmail | GmailService (external module) | REAL wrapper | NO | permanent_delete | no try/except for delegated calls |
| 3 | calendar | google-api-python-client (867 lines) | REAL OAuth | NO | delete_calendar, clear_calendar | NO 429 retry in CRUD paths |
| 4 | drive | google-api-python-client v3 (519 lines) | REAL OAuth | NO | empty_trash | NO 429 retry; trash-first policy |
| 5 | notion | httpx REST (344 lines) | REAL client | NO | delete_view | 429/529 retry with Retry-After |
| 6 | telegram | httpx Bot API (549 lines) | REAL client | NO | promote_member | token-in-URL (spec); 1.05s throttle |
| 7 | github | httpx → api.github.com (898 lines) | REAL shim | NO | delete_repo, force_push | **NO 429 handling — silently returns []/{}** |
| 8 | whatsapp | httpx loopback :8095 (210 lines) | REAL shim | NO | promote_admin | delete_message always raises (deferred) |
| 9 | discord | DiscordRestShim (runtime.py) | REAL shim | **YES** | purge, kick, ban | missing add_reaction, create_thread |
| 10 | finance | SQLAlchemy (222 lines) | REAL shim | NO | pay_transfer | record_transaction DEFERRED; bulk_import hardcoded {imported:0} |
| 11 | filesystem | Native pathlib + subprocess | REAL native | **YES** | none | _FORBIDDEN_PATHS allowlist; git-tracked check; sha256 content_hash |
| 12 | vps | DockerClientShim + ShellClientShim | REAL shims | **YES** | system_prune | _ALLOWED_SERVICES (16); container regex; pre-delete commit |
| 13 | memory | memory_pipeline_shim (220 lines) | REAL wrapper | NO | delete_memory | hardcoded INSERT SQL (parameterized) |

### Findings

**F08 — GitHub client silently swallows errors (HIGH)**
- `github_client_shim.py`: on any non-200 response, returns `[]` or `{}` instead of raising
- No 429 rate-limit handling at all
- **Impact**: GitHub actions silently appear to succeed with empty results
- **Fix**: Raise `RateLimitExceededError` on 429, `ProviderError` on other non-200

**F09 — Calendar/Drive: no 429 retry (HIGH)**
- `calendar_client.py`: 401-refresh-retry exists but NO 429 retry in CRUD paths
- `drive_client.py`: detects 429 → raises ProviderError, NO retry/backoff
- **Impact**: Will fail under Google API rate limits with no recovery
- **Fix**: Add exponential backoff with Retry-After header support

**F20 — Browser status drift (MEDIUM)**
- `p22-final-implementation-report.md` (2026-06-27): Browser "OK (local)"
- `p22-production-status.md` (2026-06-28): Browser CONFIG_MISSING
- **Impact**: Status tracking inconsistency; unclear what changed in 1 day

**F23 — Registry race condition (MEDIUM)**
- `registry.py`: `get()` and `list_all()` are sync methods accessing `self._adapters` without lock
- `register()`/`unregister()` are async with `asyncio.Lock`
- **Impact**: Potential race if read happens during concurrent registration
- **Fix**: Make get()/list_all() async, or use a thread-safe dict

**Adapter error handling gap**: ZERO try/except for delegated client calls at adapter boundary. Raw `ProviderError`/`httpx.HTTPError` bubbles to router. The typed error hierarchy (10 classes in `errors.py`) is UNUSED at adapter boundary — adapters don't catch and translate.

### Positive findings
- NO hardcoded credentials in any adapter
- NO fake success patterns — all CONFIG_MISSING adapters raise `ConfigurationMissingError` or return honest `config_missing: True`
- NO `as any`, `# type: ignore`, empty catches in P22 code
- L4 actions correctly mapped and blocked at router level
- Honest deferrals: WhatsApp L3, Finance L2, Browser search

---

## Audit Angle 2: L1-L4 Risk Tier System

**Source**: Parent source reading + Agent bg_9e493e14 (3m00s)

### Design
- `PermissionTier` IntEnum: L1_READ=1, L2_WRITE=2, L3_DESTRUCTIVE=3, L4_FORBIDDEN=4
- `ConsentGate.check()`: L1 passes without consent, L4 always forbidden, L2+ requires consent
- Fail-closed if no consent_checker configured (returns False)
- `_PROVIDER_TIER_MAP` has 13 entries with correct L4 mappings

### Findings

**F04 — Unknown actions default to L1_READ (CRITICAL)**
- `permissions.py:SemanticActionClassifier.classify()`: when no provider match AND no keyword match, defaults to `L1_READ`
- **Impact**: An unrecognized destructive action could be classified as L1 and bypass consent entirely
- **Fix**: Default to `L2_WRITE` (require consent) or `L4_FORBIDDEN` (fail-closed) for unknown actions

**F11 — dry_run classification inconsistency (HIGH)**
- `router.py:execute()` classifies with `provider=adapter.config.provider`
- `router.py:dry_run()` classifies with `provider=integration_id`
- **Impact**: dry_run might report a different tier than actual execution
- **Fix**: Use `adapter.config.provider` in both methods

### Positive findings
- L4 never-autonomous: confirmed at router (`consent.py:115-121` returns False for L4)
- L3 approval-gated: confirmed (`consent.py:124-143` — L2+ requires consent)
- L1 auto-read: confirmed (`consent.py:100-102` short-circuits)
- 4-layer fail-closed consent check (router → gate → status resolver → SQL)
- L4 adapter-level `ActionNotSupportedError` is defense-in-depth dead code (router intercepts first) — acceptable

---

## Audit Angle 3: Consent Gate + P23/P24 Conflict

**Source**: Parent source reading + Agent bg_9e493e14 (3m00s)

### Architecture Flow
```
Caller → ActionRouter.execute()
  → SemanticActionClassifier.classify()
  → _derive_consent_scope()
  → ConsentGate.check()
    → [L1 passes | L4 forbidden | L2+ needs consent]
    → P22ConsentChecker queries consent.consent_ledger via SQL
  → adapter.execute_action()
  → AuditLogger.log()
```

### Findings

**F03 — ConsentGate fail-open when no hard_stop_checker (CRITICAL)**
- `consent.py:104-112`: when `_hard_stop_checker is None`, ConsentGate SKIPS hard stop check entirely ("assumes clear")
- This was identified as F2 HIGH in round-1 audit (`audit-consent-hardstop.md`)
- Round-2 audit declared it PASS, claiming the fix was applied
- **REALITY**: The r2 fix addresses `HardStopShim` construction (async redis hard-fail), NOT the ConsentGate fail-open asymmetry
- `consent.py:104-112` still has `_hard_stop_checker is None → fail-open` semantic — **NEVER ACTUALLY FIXED**
- **Impact**: If ConsentGate is constructed without a hard_stop_checker (e.g., in tests, in future code paths), HARD STOP is silently ignored
- **Fix**: Fail-closed when `_hard_stop_checker is None` for L2+ actions, or require hard_stop_checker at construction time

**F12 — 3 HARD STOP fail-open windows (HIGH)**
1. `_shims.py:128-133`: `HardStopShim` returns `False` (HARD STOP not active) when neither Redis nor handler wired. Logs error but doesn't block.
2. `_shims.py:117-127`: `HardStopShim` swallows handler exception, leaves `handler_active=False`. Silent fail-open.
3. `consent.py:78-79,105-108`: `ConsentGate` skips HARD STOP check when `hard_stop_checker=None`.
- All 3 mitigated in production by `runtime.py:305-308` wiring `HardStopShim` with both sources
- **Impact**: Bypass surface exists for future code paths and test configurations
- **Fix**: Fail-closed in all three locations, or enforce non-None at construction

### P23/P24 Conflict
- P23 v2.0: NO consent gate, NO L1-L4
- P24 v2.0: NO consent gate (ADR-062)
- P22: HAS consent gate + L1-L4
- **Status**: P22 router will BLOCK P23/P24 callers with `ConsentDeniedError`. No bypass exists. `permissions.py:7-8` expects P23 to deliver `SemanticActionClassifier` — if P23 delivers one without consent gate, P22's `is_allowed()` will reject P23's classifications.
- **Assessment**: Conflict is UNRESOLVED but not a bug — it's a design decision that P22 enforces consent gate and P23/P24 must comply or override. Needs explicit ADR.

### Positive findings
- Consent checked at 4 layers, all fail-closed
- `P22ConsentChecker` uses parameterized SQL (no injection)
- Only `status == 'ACTIVE'` returns True
- No Redis cache — every check hits DB (immediate revocation visibility)
- NO TODO/FIXME/HACK comments in `src/life_integrations/`

---

## Audit Angle 4: Test Quality

**Source**: Agent bg_599a6aee (1m56s)

### Findings

**F19 — Test count discrepancy (MEDIUM)**
- README claims 897 tests
- `f3-runtime-proof.md` says 753 P22 tests passing
- Delta of 144 tests unexplained
- **Impact**: Cannot verify the 897 claim; actual test count uncertain

### Positive findings
- ~787 test functions found (parametrized tests may inflate runtime count to ~897)
- NO `@pytest.mark.skip` decorators — zero formally skipped tests
- NO trivial `assert True/False/None` patterns found
- L1-L4 tier names appear in 426 matches across 34 files — well-exercised
- Tests are meaningful (not trivial stubs)
- 24+ Discord callback tests with httpx MockTransport
- 15+ API endpoint tests including auth, 404, 503, secret-leak prevention

### Test coverage gap
- Most tests STUB/MOCK adapter pipelines, not real API calls
- Runtime proof script (`p22_3_runtime_proof.py`) uses only 1 real adapter (filesystem) + 12 stub "MissingClient" adapters
- No integration tests against real Google/Telegram/GitHub/Notion APIs

---

## Audit Angle 5: Security/Secrets

**Source**: Parent source reading + Agent bg_07ee0b5a (3m43s)

### Findings

**F10 — X Poster leaks first 8 chars of access token (HIGH)**
- `x_poster/main.py:67`: logs `settings.x_access_token[:8] + "..."`
- **Impact**: First 8 characters of access token exposed in logs
- **Fix**: Do not log any portion of the token. Log only `"***REDACTED***"` or a hash prefix.

**F28 — `_rpw` stores REDIS_PASSWORD (MEDIUM)**
- `runtime.py:286`: `REDIS_PASSWORD` stored in variable `_rpw`
- **Impact**: Could end up in error context or stack trace
- **Fix**: Use `os.environ.get()` inline or redact in error handlers

**F30 — `secrets.py` provider abstraction is DEAD CODE (MEDIUM)**
- `EnvSecretProvider` defined but never instantiated in `wiring.py` (import unused)
- `ProjectVaultSecretProvider` defined but never imported by `life_integrations/`
- No `SOPSSecretProvider` class exists
- Every adapter reads `os.environ.get()` directly — no centralized secret management
- **Impact**: Dead code creates false impression of centralized secret management
- **Fix**: Either wire the abstraction or remove the dead code

### API Auth
- READS (`/integrations/status`, `/capabilities`, `/missing`, `/consent` GET, `/loops` GET): **UNAUTHENTICATED**
- MUTATIONS (`/integrations/test`, `/consent` POST, `/dry-run` POST, `/loops` POST, `/loops/{id}/cancel`): require `X-Guinevere-API-Key` (timing-safe `hmac.compare_digest`)
- Single shared-secret API key — no per-user auth, no JWT, no OAuth on API surface

### Positive findings
- NO hardcoded credentials in `src/life_integrations/`
- OAuth flows correct per spec (Google OAuth 2.0, Telegram Bot API, GitHub PAT, Notion Bearer)
- NO SQL injection risks — all parameterized
- NO `as any`, `# type: ignore`, `@ts-ignore` in P22
- NO empty catch blocks (only documented `except Exception: pass` in telegram shutdown)
- Two-layer secret redaction in `audit.py` (key-name patterns + value patterns)

---

## Audit Angle 6: P20 Regression

**Source**: Agent bg_0540049b (3m25s)

### Findings

**F31 — P20 "soak" is 37 minutes, not 6 hours (MEDIUM)**
- Longest continuous observation window is ~37 minutes since most-recent restart (23:50:19 WIB)
- The 6-hour metric block counts events backwards from "now", not a continuous 6-hour undisturbed run
- `NRestarts=0` is verifiable via `systemctl show guinevere-core -p NRestarts` — but counter resets on every (re)start
- **Impact**: P20 stability claim is based on ~40 min post-restart, not multi-day soak
- Two restarts occurred: 23:16:36 WIB (P22 deployment) + 23:50:19 WIB (lockstep auto-restart)

### Positive findings
- No new P20 regressions introduced by P22
- Pre-existing P20 issues are out-of-scope (test_sensors failure, milestone_init_failed, audit_trail empty, 9ROUTER_API_KEY in journal)

---

## Audit Angle 7: API/Discord Endpoints

**Source**: Agent bg_417d91bc (4m11s)

### Findings

**F01 — Discord slash commands NOT REGISTERED (CRITICAL)**
- 6 callback functions exist in `src/discord/cmd_integrations.py` (657 lines)
- Have passing tests (24+ tests in `test_cmd_integrations.py`)
- **BUT**: NONE are wired into `GuinevereBot.tree` in `src/discord/_entrypoint.py:setup_hook`
- Entrypoint registers 35 commands (13 original + 20 RG-010..014 + 2 Hermes) — does NOT import `cmd_integrations` at all
- The 6 P22 names are absent from `COMMAND_SPECS` in `_command_registry.py`
- `require_canonical_registry()` enforces exactly 35 commands — would crash if P22 were added
- **Impact**: Users cannot see or invoke `/integration-status` etc. on Discord. The "6 Discord slash commands" claim is fiction from Discord's POV.
- **Fix**: Import `cmd_integrations` in `_entrypoint.py`, add 6 commands to `COMMAND_SPECS`, update `require_canonical_registry()` count to 41

**F07 — No rate limiting on FastAPI endpoints (HIGH)**
- Only `_PrometheusMiddleware` is configured
- No SlowAPI, no per-key throttle, no IP throttling
- Auth exists on mutations but no abuse mitigation
- **Impact**: API key holder can spam mutations without limit
- **Fix**: Add rate limiting middleware (e.g., SlowAPI or custom token bucket)

**F26 — `consent_callback` name collision (MEDIUM)**
- `cmd_consent.py:67` and `cmd_integrations.py:451` both define `async def consent_callback`
- Not a live collision (different modules, cmd_integrations not imported in entrypoint)
- **Impact**: Latent landmine if cmd_integrations is ever imported alongside cmd_consent
- **Fix**: Rename one of the callbacks

**F27 — Bare `except Exception` in cmd_integrations.py (MEDIUM)**
- `cmd_integrations.py:130`: bare `except Exception: # noqa: BLE001`
- AGENTS.md §5 lists bare except as forbidden
- File comment says "intentional" — boundary fall-through
- **Fix**: Catch specific exceptions or add structured logging

### 7 FastAPI endpoints (not 6)
1. GET `/api/v1/integrations/status` — NO AUTH
2. GET `/api/v1/integrations/capabilities` — NO AUTH
3. POST `/api/v1/integrations/test` — AUTH required
4. GET `/api/v1/integrations/missing` — NO AUTH
5. GET `/api/v1/integrations/consent` — NO AUTH
6. POST `/api/v1/integrations/consent` — AUTH required
7. POST `/api/v1/integrations/dry-run` — AUTH required

### Positive findings
- Auth mechanism uses timing-safe `hmac.compare_digest` — correct
- Input validation: all POST bodies are Pydantic BaseModel with Field constraints
- 400 on invalid action, 404 on unknown integration_id, 503 on dry-run when router absent (fail-closed)
- Read endpoints return 200 + `p22_active:false` if P22 inactive (graceful degradation)
- All 7 endpoints tested in `test_integrations_endpoints.py` (899 lines, 15+ tests)
- `is_faiz_interaction` guard at top of every Discord callback (fail-closed, guild-owner-only)

---

## Audit Angle 8: Audit Trail

**Source**: Parent source reading + Agent bg_0540049b (3m25s)

### Schema
`audit.integration_api_log` — 18 columns (id, event_id, sequence, occurred_at, actor_type, actor_id, integration_id, provider, action, tier, project_id, project_scope, result, correlation_id, metadata, previous_hash, event_hash, chain_version)

### Findings

**F05 — AuditWriter target=None in production (CRITICAL)**
- Production `runtime.py` constructs `AuditLogger` with `target=None`
- Events emit to structured log, NOT to `audit.integration_api_log` DB table
- Documented as "Accepted Risk #2" in production-activation report
- **Impact**: Audit trail is INCOMPLETE in production — hash chain exists only in logs, not in WORM table
- **Fix**: Wire AuditWriter to DB in production, or explicitly document why DB write is deferred

**F13 — TRUNCATE not in WORM contract (HIGH)**
- DB-level: `REVOKE UPDATE, DELETE FROM guinevere_core; GRANT INSERT, SELECT TO guinevere_core`
- **BUT**: TRUNCATE is NOT revoked — table owner can wipe audit log via TRUNCATE
- **Impact**: WORM protection is incomplete — TRUNCATE bypasses the UPDATE/DELETE restriction
- **Fix**: `REVOKE TRUNCATE ON audit.integration_api_log FROM guinevere_core` or make table owner different role

**F21 — Audit write failures are SILENT (MEDIUM)**
- `audit_db_writer.py`: catches Exception, logs error, does NOT raise
- Documented as "audit must not block the action path"
- **Impact**: Audit failures go undetected — could lose audit events silently
- **Fix**: Add alerting/counter for audit write failures, even if not blocking

**F22 — `seed_last_hash()` returns "" on error (MEDIUM)**
- Returns empty string on DB error — starts fresh chain
- **Impact**: DB error could break hash chain silently, new chain starts from ""
- **Fix**: Raise or alert on seed failure

**F24 — `AuditChainVerificationError` defined but unused (MEDIUM)**
- `errors.py:71` defines `AuditChainVerificationError`
- `audit.py:verify_chain()` returns `bool`, doesn't raise
- **Impact**: Code/doc drift — callers can't catch a typed exception
- **Fix**: Either raise `AuditChainVerificationError` on verification failure, or remove the class

**F25 — No UUID v7 (MEDIUM/OBSERVATION)**
- Uses UUID v4 (`gen_random_uuid()` DB-side, `uuid.uuid4()` Python-side)
- Python 3.12 has no `uuid.uuid7()`
- Not a claimed feature, but UUID v7 is the modern standard for time-sortable IDs
- **Fix**: Consider pg_uuidv7 extension or Python-side UUID v7 library

**F29 — `chain_version=2` hardcoded (MEDIUM/OBSERVATION)**
- Both schema default and writer INSERT literal use `chain_version = 2`
- No upgrade path to v3 visible
- **Fix**: Make configurable or document upgrade procedure

**F32 — No external signature (MEDIUM/OBSERVATION)**
- Pure intra-chain SHA256 — no Ed25519/RSA/Merkle root/timestamping authority
- **Impact**: Chain is only as trustworthy as the DB access controls
- **Fix**: Consider external notarization for high-integrity use cases

### Positive findings
- SHA256 hash chain: YES, confirmed (`audit.py:63-87` — `compute_hash()` uses `hashlib.sha256`)
- Hash chain verification: YES (`AuditLogger.verify_chain()` walks events checking `previous_hash` + `event_hash`)
- WORM enforcement: YES at DB level (REVOKE UPDATE, DELETE)
- Two-layer secret redaction in audit.py (key-name patterns + value patterns)
- `consent_ledger_writer.py`: SHA256 per-row `evidence_hash`, 38 canonical scopes, append-only
- Migration: `p22_001_integration_schema.py` EXISTS, idempotent, chains from `p19_003`

---

## Audit Angle 9: Meta-Audit of Previous Verdicts

**Source**: Agent bg_7ef04c82 (3m18s)

### Audit Count Reality

| Claim | Actual |
|-------|--------|
| 14 round-1 + 6 round-2 = 20 | 16 R1 + 10 R2 = 26 |
| 8 R1 PASS, 3 R1 NEEDS_REVIEW | 10 R1 PASS, 6 R1 NEEDS_REVIEW |
| 5 R2 PASS, 1 R2 NEEDS_REVIEW | 7 R2 PASS after adjudication |

### Findings

**F14 — Implementation R1 fix log distorts verdicts (HIGH)**
- Only covers 4 of 8 audits; other 4 listed as "Reports pending"
- Claims `audit-consent-hardstop.md (PASS — no findings)` — but actual audit has F2 HIGH (HARD STOP fail-open) → **DISTORTION**
- Claims `audit-project-namespace.md (PASS — no findings)` — but actual audit has F4 MEDIUM → **DISTORTION**
- Claims `audit-audit-trail.md (completed in workflow)` — vague, while actual audit identifies 3 HIGH findings → **VAGUE-DISTORTION**

**F15 — Round-2 summary-adjudication aggressively reclassifies (HIGH)**
- `round-2-summary-adjudication.md`: reclassifies NEEDS_REVIEW to PASS via "fix in commit 4efe4c2"
- F-10 (secrets-in-journal) dismissed as "out of P22 scope" despite being a real MEDIUM finding
- **Impact**: Findings are being explained away rather than fixed

### Critical Unresolved Finding
**F03 (restated)**: F2 HIGH (ConsentGate fail-open when no checker) was NEVER actually fixed. The r2 fix addresses HardStopShim construction, NOT the ConsentGate fail-open asymmetry. `consent.py:104-112` still has `_hard_stop_checker is None → fail-open` semantic. The r2 audit-consent.md declares this PASS, but the actual F2 asymmetry is still present in code.

### Positive findings
- ALL 26 audits are SUBSTANTIVE — not rubber-stamps
- Every audit has real file:line citations, actual code excerpts, real semantic analysis
- Specific fix recommendations in every audit
- Findings ARE tracked and partially fixed with file:line references
- Code verification confirmed fixes ARE applied (grep evidence):
  - `__import__` eliminated ✓
  - `_ALLOWED_SERVICES` at vps_adapter.py:44 ✓
  - `asyncio.Lock` at registry.py:44 ✓
  - `async def build_default_registry` at wiring.py:47 ✓
  - `_VALUE_SECRET_PATTERNS` at audit.py:120 ✓
  - `content_hash`/`tombstone` in adapters ✓

---

## Audit Angle 10: Implementation Completeness

**Source**: Agent bg_0423912b (3m51s) + parent source reading

### Findings

**F02 — Only 3/13 adapters ACTIVE (CRITICAL)**
- ACTIVE: filesystem, vps, discord
- CONFIG_MISSING: gmail, calendar, drive, notion, telegram, github, browser, memory, finance, whatsapp
- All 10 CONFIG_MISSING are honest (raise `ConfigurationMissingError`, no fake success)
- **Impact**: P22 is NOT production-ready despite "FULL-COMPLETION" claim
- **Fix**: Wire operator credentials for remaining adapters, or explicitly document which are deferred

**F06 — Phantom adapters in handoff (HIGH)**
- Handoff claims 13 adapters include "weather, search, obscura"
- Actual 13: browser, calendar, discord, drive, filesystem, finance, github, gmail, memory, notion, telegram, vps, whatsapp
- NO weather/search/obscura adapter files exist
- "obscura" is just a CDP shim in `_clients/`
- **Impact**: Handoff document contains false information
- **Fix**: Correct the handoff document

**F16 — README contradiction (MEDIUM)**
- `P22/README.md`: status says "P22.3 FULL-COMPLETION"
- Progress table shows ALL waves as "⏸️ HOLD"
- Bottom note: "definition/planning phase only. No runtime code, adapters, or deployed services exist."
- But 45 source files + 51 test files DO exist
- **Impact**: README is outdated — was written for definition phase, never updated for implementation
- **Fix**: Update README to reflect actual implementation state

**F17 — PROGRESS.md out of date (MEDIUM)**
- Line 52: `| P22 | Additional Integrations TBD | ⏸ | TBD | TBD | TBD | P8 | None |`
- Despite production-activation claiming runtime active
- **Fix**: Update PROGRESS.md to reflect actual P22 status

**F18 — C10 verification file missing (MEDIUM)**
- `full-completion/verification/` has c1-c9, c11-c12 (11 files), NOT c1-c12 (12 files)
- C10 never existed
- **Impact**: Verification gap — one criterion was never verified
- **Fix**: Identify what C10 was supposed to verify and either create it or document why it was skipped

### Honest Deferrals (verified, NOT fake)
1. WhatsApp L3 `delete_for_everyone`: returns `{success: False, deferred: True, tombstone: ...}`
2. Finance L2 `record_transaction`: DEFERRED_FOR_SAFETY by default, only with `allow_record=True`
3. Browser search: returns `{success: False, config_missing: True}`
4. L4 actions: PERMANENTLY FORBIDDEN

### Runtime Proof Script
- `scripts/p22_3_runtime_proof.py` (1079 lines, 12 steps)
- Uses ONLY 1 real adapter (filesystem) + 12 stub "MissingClient" adapters
- Honest limitations documented: no real provider APIs, no VPS, no OAuth, HARD STOP is in-memory
- 12/12 PASS, exit 0
- **Assessment**: Honest but limited — proves the pipeline works, not that adapters work

### Accepted Risks (documented)
1. AuditWriter target = None: events emit to structured log, NOT to DB table. Accepted Risk #2.
2. consent_checker = None: L2+ fail-closed by design. Accepted Risk #3.
3. Only 3/13 adapters ACTIVE: 10 need operator credentials/testing.

### Verification Files Status
- All 11 C-files (c1-c9, c11-c12) PASS
- D1-D5 PASS, E1 PASS, F3 PASS, G1-G4 PASS
- fix-audit-redactor PASS, a5-capability-matrix PASS, local-tests PASS

---

## P23/P24 Conflict Assessment

| Project | Consent Gate | L1-L4 | Status |
|---------|-------------|-------|--------|
| P22 | YES (enforced) | YES | Active |
| P23 v2.0 | NO | NO | Conflicts with P22 |
| P24 v2.0 | NO (ADR-062) | N/A | Conflicts with P22 |

**Assessment**: P22's consent gate will BLOCK P23/P24 callers. This is not a bug — it's a design decision. But it needs an explicit ADR to document:
1. Whether P22's consent gate applies to P23/P24 callers
2. Whether P23/P24 can bypass P22's consent gate
3. What happens when P23 delivers a SemanticActionClassifier without consent gate

**Recommendation**: Create ADR documenting the P22/P23/P24 consent gate boundary before P23/P24 implementation begins.

---

## Remediation Priority

### Immediate (blocks production)
1. **F01**: Register Discord slash commands in bot tree
2. **F03**: Fix ConsentGate fail-open when `hard_stop_checker=None`
3. **F04**: Change unknown action default from L1_READ to L2_WRITE
4. **F05**: Wire AuditWriter to DB in production (or explicitly document deferral)

### High priority (before claiming production-ready)
5. **F02**: Wire operator credentials for remaining adapters OR explicitly document which are deferred
6. **F06**: Correct handoff document adapter names
7. **F07**: Add rate limiting to FastAPI endpoints
8. **F08**: Add 429 handling to GitHub client
9. **F09**: Add 429 retry to Calendar/Drive clients
10. **F10**: Fix X Poster token leak
11. **F11**: Fix dry_run classification inconsistency
12. **F13**: REVOKE TRUNCATE on audit.integration_api_log
13. **F14**: Correct implementation R1 fix log
14. **F15**: Re-examine round-2 summary-adjudication reclassifications

### Medium priority (hygiene + correctness)
15. **F16**: Update README to reflect actual state
16. **F17**: Update PROGRESS.md
17. **F18**: Identify and document C10 gap
18. **F19**: Reconcile test count discrepancy
19. **F21**: Add alerting for silent audit write failures
20. **F22**: Fix `seed_last_hash()` error handling
21. **F23**: Fix registry race condition
22. **F24**: Fix AuditChainVerificationError code/doc drift
23. **F26**: Rename duplicate `consent_callback`
24. **F27**: Fix bare except in cmd_integrations.py
25. **F28**: Redact `_rpw` variable
26. **F30**: Remove dead code in secrets.py
27. **F31**: Correct P20 soak documentation

---

## Auditor Verdict

**FAIL** — P22 is not production-ready.

The system is well-architected with genuine engineering quality. The L1-L4 tier system, hash-chain audit trail, and 4-layer consent checking are sound designs. Previous audits are substantive and real.

However, 5 CRITICAL findings block production readiness:
1. Discord commands exist but aren't registered — users can't invoke them
2. Only 3/13 adapters are active — 10 need credentials
3. ConsentGate has a fail-open hole that was never actually fixed despite claims
4. Unknown actions default to L1 — can bypass consent
5. AuditWriter is disabled in production — audit trail incomplete

The "FULL-COMPLETION" claim is not accurate. P22 is at **"core pipeline complete, adapters deferred, production-wiring incomplete"** stage.

**Recommendation**: Fix F01-F05 (CRITICAL) before any production claim. Fix F06-F15 (HIGH) before declaring P22 production-ready. Address F16-F31 (MEDIUM) as technical debt.

---

## Evidence

- **Auditor**: Guinevere (parent agent)
- **Method**: Direct source file reading (10 core files) + 8 parallel explore sub-agents
- **Agent IDs**: bg_b29db63e, bg_9e493e14, bg_599a6aee, bg_07ee0b5a, bg_0540049b, bg_417d91bc, bg_7ef04c82, bg_0423912b
- **Files examined**: 45 source files in `src/life_integrations/`, 51 test files in `tests/p22/`, 100 evidence files in `docs/setup-evidence/P22/`, 10 client files in `_clients/`, Discord/API source files
- **Date**: 2026-06-28

### Footer

| Field | Value |
|---|---|
| Report path | `docs/setup-evidence/P22/audits/brutal-2026-06-28/brutal-audit-report.md` |
| Verdict | FAIL |
| Critical findings | 5 |
| High findings | 10 |
| Medium findings | 17 (29 actionable + 3 observations) |
| Recommendation | Fix F01-F05 before production. Fix F06-F15 before production-ready claim. |
| Next action | Await Faiz decision on which findings to fix |
