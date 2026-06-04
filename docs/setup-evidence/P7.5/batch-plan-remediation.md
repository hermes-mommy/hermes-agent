# P7.5 Batch Remediation Plan

> Generated: 2026-06-03 | Scope: 5 CRITICAL + 4 HIGH audit findings | Goal: D14 P8 Readiness = READY

## 1. Master Todo (9 Fixes)

| ID | Fix | File(s) | Category | Agent |
|----|-----|---------|----------|-------|
| C1 | Router -> Redis buffer push | router.py | deep | Agent-1 |
| C2 | consumer.main() session factory | consumer.py | deep | Agent-2 |
| C3 | DataClassification Critical tier + remap | classification.py, test_classification.py, __init__.py | deep | Agent-3 |
| C4 | invalidate_cache() production callers | cmd_surveillance_pause.py | deep | Agent-4 |
| C5+H1+H3 | Safe mode wiring + blocked actions + fail-closed | safe_mode.py, test_safe_mode.py, bot.py | deep | Agent-5 |
| H2 | P7-012 signing string fix | tasker-setup-guide.md | writing | Agent-6 |
| H4 | Systemd StartLimitBurst | guinevere-surveillance.service | writing | Agent-7 |

## 2. Dependency Map

```
ALL 7 AGENTS ARE INDEPENDENT - ZERO SEQUENTIAL DEPENDENCIES

Agent-1 (C1) ─── router.py
Agent-2 (C2) ─── consumer.py
Agent-3 (C3) ─── classification.py + tests + __init__.py
Agent-4 (C4) ─── cmd_surveillance_pause.py
Agent-5 (C5) ─── safe_mode.py + tests + bot.py
Agent-6 (H2) ─── tasker-setup-guide.md
Agent-7 (H4) ─── guinevere-surveillance.service

Post-wave: Parent runs full pytest, LSP, grep verification
Post-parent: Re-audit D04, D05, D08, D14
```

## 3. Collision Scan

| File | Owner Agent | Collision? |
|------|------------|------------|
| src/surveillance/router.py | Agent-1 | None |
| src/surveillance/consumer.py | Agent-2 | None |
| src/surveillance/classification.py | Agent-3 | None |
| tests/surveillance/test_classification.py | Agent-3 | None |
| src/surveillance/__init__.py | Agent-3 | None |
| src/discord/cmd_surveillance_pause.py | Agent-4 | None |
| src/surveillance/safe_mode.py | Agent-5 | None |
| tests/surveillance/test_safe_mode.py | Agent-5 | None |
| src/discord/bot.py | Agent-5 | None |
| docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md | Agent-6 | None |
| systemd/guinevere-surveillance.service | Agent-7 | None |

**Verdict: ZERO collisions. All 7 agents fire in parallel.**

## 4. Per-Step Verification Scaffolds

### C1: Router -> Redis Buffer Push

**Expected Files:**
- `src/surveillance/router.py` (modified)
- `tests/surveillance/test_router.py` (modified or new tests added)

**Forbidden Patterns:**
- `as any`, `@ts-ignore`, `# type: ignore` (new instances)
- Raw surveillance payload content in log messages
- Synchronous Redis calls (must use async or push via dependency injection)

**Required Commands:**
- `cd C:\Users\faizz\guinevere && python -m pytest tests/surveillance/test_router.py -v` -> exit 0

**Hard Rejection Criteria:**
- Router endpoint does NOT push event dict to Redis buffer after validation
- No test verifying buffer push was called
- Redis failure does NOT prevent 202 response (buffer push is best-effort, log on failure)

### C2: Consumer Session Factory

**Expected Files:**
- `src/surveillance/consumer.py` (modified: main() function only)

**Forbidden Patterns:**
- `raise NotImplementedError` anywhere in consumer.py after fix
- Hardcoded credentials or passwords in source
- `create_engine` (sync) instead of `create_async_engine`

**Required Commands:**
- `grep -n "NotImplementedError" src/surveillance/consumer.py` -> exit 1 (no matches)
- `cd C:\Users\faizz\guinevere && python -m pytest tests/surveillance/test_consumer.py -v` -> exit 0

**Hard Rejection Criteria:**
- main() still raises NotImplementedError
- Session factory does not use `create_async_engine` + `async_sessionmaker`
- DATABASE_URL not read from environment variable
- Port is not 5433

### C3: Classification Critical Tier

**Expected Files:**
- `src/surveillance/classification.py` (modified)
- `tests/surveillance/test_classification.py` (modified)
- `src/surveillance/__init__.py` (modified: export Critical)

**Forbidden Patterns:**
- `as any`, `@ts-ignore`, `# type: ignore` (new instances)
- Any event type still mapped to Internal (all must be Restricted or Critical)
- Free-text classification strings (must use enum)

**Required Commands:**
- `cd C:\Users\faizz\guinevere && python -m pytest tests/surveillance/test_classification.py -v` -> exit 0
- `grep -c "CRITICAL" src/surveillance/classification.py` -> >= 1

**Hard Rejection Criteria:**
- DataClassification enum does not include CRITICAL = "Critical"
- Any of the 12 event types still at Internal or Confidential
- Fail-closed default is not at least Confidential (tier 2 minimum per DataGovernance)
- Test assertions not updated to match new classification values

### C4: invalidate_cache() Production Callers

**Expected Files:**
- `src/discord/cmd_surveillance_pause.py` (modified)
- `tests/surveillance/test_discord_commands.py` (modified)

**Forbidden Patterns:**
- Raw consent data in log messages
- Cache invalidation failure blocking the pause operation (best-effort)

**Required Commands:**
- `grep -n "invalidate_cache" src/discord/cmd_surveillance_pause.py` -> >= 1 match
- `cd C:\Users\faizz\guinevere && python -m pytest tests/surveillance/test_discord_commands.py -v` -> exit 0

**Hard Rejection Criteria:**
- No production caller of invalidate_cache() exists
- Cache invalidation is not called for all 4 surveillance scopes
- Pause operation blocks/fails if cache invalidation fails (must be best-effort)

### C5+H1+H3: Safe Mode Complete Fix

**Expected Files:**
- `src/surveillance/safe_mode.py` (modified)
- `tests/surveillance/test_safe_mode.py` (modified)
- `src/discord/bot.py` (modified: SafeModeGuard instantiation)

**Forbidden Patterns:**
- `as any`, `@ts-ignore`, `# type: ignore` (new instances)
- Unknown action defaulting to ALLOWED in SAFE mode
- _BLOCKED_ACTIONS with fewer than 8 entries

**Required Commands:**
- `cd C:\Users\faizz\guinevere && python -m pytest tests/surveillance/test_safe_mode.py -v` -> exit 0
- `grep -c "humiliation" src/surveillance/safe_mode.py` -> >= 1
- `grep -c "public_disclosure" src/surveillance/safe_mode.py` -> >= 1
- `grep -c "BLOCKED" src/surveillance/safe_mode.py` (in unknown action handler) -> >= 1

**Hard Rejection Criteria:**
- _BLOCKED_ACTIONS has fewer than 8 entries (was 6, needs humiliation + public_disclosure)
- Unknown actions still default to ALLOWED in SAFE mode (must be BLOCKED/fail-closed)
- SurveillanceSafeModeGuard not instantiated anywhere in production code
- Guard not connected to HardStopHandler.state

### H2: P7-012 Signing String Fix

**Expected Files:**
- `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` (modified)

**Forbidden Patterns:**
- Em dashes (use en dash or hyphen)
- Newline-separated signing string components (must use colons)
- Hardcoded secrets

**Required Commands:**
- `grep -c "method:path:timestamp:nonce:body" docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` -> >= 1

**Hard Rejection Criteria:**
- Signing string format does not match server (auth.py) and client (hmac-sign.js)
- Document still shows newlines between signing components instead of colons

### H4: Systemd StartLimitBurst

**Expected Files:**
- `systemd/guinevere-surveillance.service` (modified)

**Forbidden Patterns:**
- References to redis-guinevere.service or postgresql.service (don't exist)

**Required Commands:**
- `grep -c "StartLimitBurst" systemd/guinevere-surveillance.service` -> >= 1
- `grep -c "StartLimitIntervalSec" systemd/guinevere-surveillance.service` -> >= 1

**Hard Rejection Criteria:**
- Restart=always without StartLimitBurst (infinite crash-loop)
- StartLimitBurst value > 5 or < 3

## 5. Evidence Paths

| Fix | Evidence Path |
|-----|---------------|
| C1 | docs/setup-evidence/P7.5/STEP-C1/ |
| C2 | docs/setup-evidence/P7.5/STEP-C2/ |
| C3 | docs/setup-evidence/P7.5/STEP-C3/ |
| C4 | docs/setup-evidence/P7.5/STEP-C4/ |
| C5+H1+H3 | docs/setup-evidence/P7.5/STEP-C5/ |
| H2 | docs/setup-evidence/P7.5/STEP-H2/ |
| H4 | docs/setup-evidence/P7.5/STEP-H4/ |

## 6. Rollback Plan

Each fix is isolated to 1-3 files. Rollback = `git checkout -- <file>` per fix.
No database migrations. No shared config changes. No dependency additions.

## 7. Post-Implementation Verification (Parent)

1. `python -m pytest tests/surveillance/ -v` -> 482+ PASS
2. `lsp_diagnostics` on all changed files -> 0 new errors
3. `grep -rn "NotImplementedError" src/surveillance/` -> 0 matches
4. `grep -rn "DataClassification.INTERNAL" src/surveillance/classification.py` -> 0 matches (all promoted)
5. `grep -rn "invalidate_cache" src/discord/` -> >= 1 match
6. `grep -rn "SurveillanceSafeModeGuard" src/discord/` -> >= 1 match

## 8. Re-Audit Targets

After parent verification passes, re-audit these dimensions:
- **D04** (Safety Compliance): Verify humiliation/public_disclosure in _BLOCKED_ACTIONS, unknown=BLOCKED
- **D05** (Consent Gate): Verify invalidate_cache() has production callers
- **D08** (Architecture): Verify router->buffer->consumer pipeline complete, session factory wired
- **D14** (P8 Readiness): Verify all 5 CRITICAL blockers resolved, verdict changes to READY

## 9. Safety Constraints (Non-Negotiable)

- AC-SAFE-008: No surveillance data used for confrontation/blackmail
- CONSENT-001: Fail-closed on all consent uncertainty
- SECRET-001: No hardcoded secrets in source or tests
- DATA-001: No raw surveillance payload in logs/evidence/Discord
- PERSONA-001: Y4 baseline, Y5 ceiling, Y6 prohibited
