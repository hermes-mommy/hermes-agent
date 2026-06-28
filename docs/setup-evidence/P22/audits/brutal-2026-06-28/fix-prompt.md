# P22 BRUTAL AUDIT — FULL FIX PROMPT

Copy-paste the prompt below into a fresh Claude Code session.

---

## PROMPT START

You are Guinevere, an autonomous AI engineering agent operating under the Guinevere AGENTS.md contract. Your operator is Faiz.

Read `AGENTS.md` first. Then read `docs/setup-evidence/P22/audits/brutal-2026-06-28/brutal-audit-report.md` for the full audit context.

### MISSION

Fix ALL 32 findings from the P22 brutal audit (5 CRITICAL, 10 HIGH, 17 MEDIUM). No findings are skipped. No findings are deferred. All severities are in scope.

### WORKFLOW (MANDATORY — AGENTS.md compliant)

1. **Read AGENTS.md first**, then read the brutal audit report at `docs/setup-evidence/P22/audits/brutal-2026-06-28/brutal-audit-report.md`.
2. **Create unlimited TODO list** — one todo per finding (32 todos minimum), plus verification todos and evidence todos.
3. **Research wave** — fire unlimited parallel `explore` sub-agents (background) to read every file referenced in the findings. Do NOT manually search what agents are searching.
4. **Planner gate** — for each finding, create a per-step verification scaffold with: expected files, forbidden patterns, required commands, hard rejection criteria.
5. **Collision scan** — identify shared files that multiple findings touch. Sequence them. One sub-agent per implementation step.
6. **Implementation wave** — delegate each fix to a `deep` or `unspecified-high` sub-agent. One sub-agent = one finding. Fire parallel for independent fixes. Use `task_id` for follow-ups.
7. **Parent verification** — after each fix, verify: file exists, `lsp_diagnostics` clean, tests pass, grep for forbidden patterns returns 0.
8. **Auditor wave** — spawn unlimited parallel auditor sub-agents for all verified fixes. Each writes a report to `docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/`.
9. **Fix auditor findings** — re-audit via `task_id` until PASS.
10. **Update PROGRESS.md** — set P22 status to reflect actual post-fix state.
11. **Write evidence** — create `docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/summary.md` with all 32 findings, their fix status, and verification results.

### CONSTRAINTS (BLOCKING — NEVER VIOLATE)

- NO `as any`, `@ts-ignore`, `@ts-expect-error`, `# type: ignore`, avoidable `Any`
- NO empty catch/except blocks
- NO deleting/skipping failing tests to pass
- NO committing secrets (Discord bot token, API keys, DB passwords, SOPS/age keys)
- NO `background_cancel(all=true)` — cancel individually by taskId
- NO bypass of consent-safety boundaries
- NO type error suppression
- NEVER claim "done" without running verification commands yourself
- Every fix must pass `lsp_diagnostics` on changed files
- Every fix must pass relevant tests
- Evidence files must be created AFTER implementation passes, not before

### FILE LANDSCAPE

**Core source** (19 files in `src/life_integrations/`):
- `__init__.py`, `types.py`, `base.py`, `registry.py`, `router.py`, `permissions.py`, `consent.py`, `consent_checker.py`, `consent_ledger_writer.py`, `audit.py`, `audit_db_writer.py`, `project_context.py`, `secrets.py`, `scheduler.py`, `errors.py`, `runtime.py`, `wiring.py`, `tombstone.py`, `_shims.py`

**Adapters** (13 in `src/life_integrations/adapters/`):
- `browser_adapter.py`, `calendar_adapter.py`, `discord_adapter.py`, `drive_adapter.py`, `filesystem_adapter.py`, `finance_adapter.py`, `github_adapter.py`, `gmail_adapter.py`, `memory_adapter.py`, `notion_adapter.py`, `telegram_adapter.py`, `vps_adapter.py`, `whatsapp_adapter.py`

**Clients** (10 in `src/life_integrations/_clients/`):
- `calendar_client.py`, `drive_client.py`, `notion_client.py`, `telegram_client.py`, `github_client_shim.py`, `whatsapp_bridge_shim.py`, `finance_read_shim.py`, `memory_pipeline_shim.py`, `obscura_cdp_shim.py`, `fetch_client_shim.py`

**Tests** (51 files in `tests/p22/`)

**Discord** (in `src/discord/`):
- `_entrypoint.py`, `_command_registry.py`, `cmd_integrations.py`, `cmd_consent.py`

**API** (in `src/core/api/`):
- `routes.py` (or `src/core/main.py` for router includes), `auth.py`

**External** (outside P22 but touched by findings):
- `x_poster/main.py` (F10 — token leak)

### ALL 32 FINDINGS — FIX SPECIFICATIONS

#### CRITICAL (F01-F05) — FIX FIRST, BLOCKS PRODUCTION

---

**F01 — Discord slash commands NOT REGISTERED in bot tree**

- **Files**: `src/discord/_entrypoint.py`, `src/discord/_command_registry.py`, `src/discord/cmd_integrations.py`
- **Issue**: 6 callback functions exist in `cmd_integrations.py` (657 lines) with passing tests, but NONE are wired into `GuinevereBot.tree` in `_entrypoint.py:setup_hook`. The entrypoint registers 35 commands but does NOT import `cmd_integrations` at all. The 6 P22 command names are absent from `COMMAND_SPECS` in `_command_registry.py`. `require_canonical_registry()` enforces exactly 35 commands — would crash if P22 were added.
- **Fix**:
  1. Import `cmd_integrations` module in `_entrypoint.py`
  2. Add the 6 P22 command specs to `COMMAND_SPECS` in `_command_registry.py` (command names: `integration-status`, `integration-capabilities`, `integration-test`, `integration-missing`, `integration-consent`, `integration-dry-run` — verify exact names from `cmd_integrations.py` callback decorators)
  3. Update `require_canonical_registry()` expected count from 35 to 41
  4. Wire the 6 callbacks into `GuinevereBot.tree` in `setup_hook`
- **Verify**:
  - `grep -r "cmd_integrations" src/discord/_entrypoint.py` returns ≥1 match
  - `grep -r "integration-status\|integration-capabilities\|integration-test\|integration-missing\|integration-consent\|integration-dry-run" src/discord/_command_registry.py` returns ≥6 matches
  - `python -m pytest tests/p22/test_cmd_integrations.py -v` passes
  - `python -c "from src.discord._command_registry import COMMAND_SPECS; assert len(COMMAND_SPECS) == 41"`
- **Forbidden**: Adding commands without updating registry count, breaking existing 35 commands

---

**F02 — Only 3/13 adapters ACTIVE in production runtime**

- **Files**: `src/life_integrations/runtime.py`, `src/life_integrations/wiring.py`
- **Issue**: `build_runtime_registry()` shows only 3 adapters ACTIVE (discord, vps, filesystem). 10 are CONFIG_MISSING. This is partially an accepted risk (operator credentials needed), but the "FULL-COMPLETION" claim is inaccurate.
- **Fix**: This finding has two parts:
  1. **Documentation fix**: Update `docs/setup-evidence/P22/README.md` and all status documents to accurately reflect "3/13 ACTIVE, 10/13 CONFIG_MISSING (deferred for operator credentials)" instead of "FULL-COMPLETION"
  2. **Runtime hardening**: For each CONFIG_MISSING adapter, add a startup log line that clearly states which environment variable / credential file is missing and what the operator must provide. Make it actionable, not just "CONFIG_MISSING".
- **Verify**:
  - `grep -r "FULL-COMPLETION" docs/setup-evidence/P22/` returns 0 matches (or is qualified with "3/13 active")
  - Runtime startup logs clearly identify missing credentials per adapter
  - `python -m pytest tests/p22/ -v` still passes
- **Forbidden**: Faking adapter activation, hardcoding credentials, suppressing CONFIG_MISSING status

---

**F03 — ConsentGate fail-open when `hard_stop_checker=None`**

- **Files**: `src/life_integrations/consent.py` (lines 104-112)
- **Issue**: When `_hard_stop_checker is None`, `ConsentGate.check()` SKIPS the HARD STOP check entirely ("assumes clear"). This was identified as F2 HIGH in round-1 audit and declared fixed in round-2, but the fix only addressed `HardStopShim` construction, NOT the ConsentGate fail-open asymmetry. `consent.py:104-112` still has `_hard_stop_checker is None → fail-open` semantic.
- **Fix**: Fail-closed for L2+ actions when `hard_stop_checker is None`. Specifically:
  1. In `ConsentGate.check()`, when `self._hard_stop_checker is None` AND tier >= L2_WRITE, return `False` (deny) with reason `"hard_stop_checker not configured — fail-closed"`
  2. L1_READ can still pass without hard_stop_checker (L1 is auto-read, no consent needed)
  3. L4_FORBIDDEN always returns False regardless
  4. Add a test: `test_consent_gate_fail_closed_without_hard_stop_checker` that verifies L2+ is denied when hard_stop_checker is None
- **Verify**:
  - `grep -n "hard_stop_checker is None" src/life_integrations/consent.py` — the line should NOT have a pass-through/skip for L2+
  - `python -m pytest tests/p22/test_consent_gate*.py -v` passes including new test
  - `python -m pytest tests/p22/ -v` still passes (no regressions)
- **Forbidden**: Breaking L1 auto-read, breaking L4 always-forbidden, suppressing the fail-closed behavior with a workaround

---

**F04 — Unknown actions default to L1_READ**

- **Files**: `src/life_integrations/permissions.py` — `SemanticActionClassifier.classify()` method
- **Issue**: When `classify()` encounters an action that matches no provider in `_PROVIDER_TIER_MAP` AND matches no keyword pattern, it defaults to `L1_READ` (auto-read). This is dangerous — an unrecognized destructive action could be classified as L1 and bypass consent entirely.
- **Fix**: Change the default from `L1_READ` to `L2_WRITE` (require consent). Specifically:
  1. In `classify()`, the fallback return should be `PermissionTier.L2_WRITE` instead of `PermissionTier.L1_READ`
  2. Add a log warning: `logger.warning(f"Unknown action '{action}' for provider '{provider}' — defaulting to L2_WRITE (consent required)")`
  3. Add a test: `test_unknown_action_defaults_to_l2_not_l1` that verifies an unrecognized action returns L2_WRITE
  4. Update any existing tests that expect unknown actions to return L1 — they should now expect L2
- **Verify**:
  - `grep -n "L1_READ" src/life_integrations/permissions.py` — the default fallback should NOT be L1_READ
  - `python -m pytest tests/p22/test_permissions*.py tests/p22/test_*dispatch*.py -v` passes
  - `python -m pytest tests/p22/ -v` still passes (no regressions)
- **Forbidden**: Defaulting to L4 (too restrictive — would block legitimate unknown read actions), suppressing the warning log

---

**F05 — AuditWriter target=None in production**

- **Files**: `src/life_integrations/runtime.py` — `build_runtime_registry()` function
- **Issue**: Production `runtime.py` constructs `AuditLogger` with `target=None`. Events emit to structured log, NOT to `audit.integration_api_log` DB table. Hash chain exists only in logs, not in WORM table. Documented as "Accepted Risk #2" but this is a CRITICAL gap — the audit trail is incomplete in production.
- **Fix**: Wire AuditWriter to DB in production. Specifically:
  1. In `build_runtime_registry()`, construct `IntegrationAuditWriter` with a real DB connection (from `DATABASE_URL` env var or async engine)
  2. If DB connection fails, fall back to file-based audit log (write to `logs/audit-integration.log` with JSON lines) — do NOT silently drop to None
  3. Add a startup log line: `"P22 audit writer wired to DB"` or `"P22 audit writer DB unavailable, falling back to file log at logs/audit-integration.log"`
  4. Add a test: `test_audit_writer_not_none_in_production` that verifies the AuditLogger has a non-None target
- **Verify**:
  - `grep -n "target=None" src/life_integrations/runtime.py` returns 0 matches (or is explicitly documented as file-fallback)
  - `python -m pytest tests/p22/test_audit*.py -v` passes including new test
  - `python -m pytest tests/p22/ -v` still passes
- **Forbidden**: Hardcoding DB credentials, suppressing DB connection errors silently, using `target=None` without file fallback

---

#### HIGH (F06-F15) — FIX BEFORE CLAIMING PRODUCTION-READY

---

**F06 — Phantom adapters in handoff document**

- **Files**: `docs/setup-evidence/P22-brutal-audit-handoff.md`, `docs/setup-evidence/P22/README.md`, any document claiming "weather/search/obscura" as adapters
- **Issue**: Handoff claims 13 adapters include "weather, search, obscura". Actual 13: browser, calendar, discord, drive, filesystem, finance, github, gmail, memory, notion, telegram, vps, whatsapp. "obscura" is a CDP shim in `_clients/`, not an adapter.
- **Fix**: Correct all documents that reference "weather/search/obscura" as adapters. Replace with the actual 13 adapter names.
- **Verify**: `grep -r "weather.*search.*obscura" docs/` returns 0 matches
- **Forbidden**: Inventing adapter names, deleting evidence files

---

**F07 — No rate limiting on FastAPI endpoints**

- **Files**: `src/core/main.py`, `src/core/api/routes.py` (or wherever P22 routes are included)
- **Issue**: Only `_PrometheusMiddleware` is configured. No SlowAPI, no per-key throttle, no IP throttling. Auth exists on mutations but no abuse mitigation.
- **Fix**: Add rate limiting middleware. Options:
  1. Use `slowapi` library: `pip install slowapi`, add `Limiter` middleware with per-endpoint limits
  2. Or implement a simple token-bucket middleware in `src/core/api/`
  - Read endpoints: 60 req/min per IP
  - Mutation endpoints: 10 req/min per API key
  - Dry-run endpoint: 5 req/min per API key
  3. Return 429 with `Retry-After` header when limit exceeded
  4. Add test: `test_rate_limiting_returns_429` that sends >limit requests and verifies 429
- **Verify**:
  - `grep -r "slowapi\|Limiter\|rate_limit\|RateLimit" src/core/` returns ≥1 match
  - `python -m pytest tests/p22/test_integrations_endpoints.py -v` passes including new test
- **Forbidden**: Breaking existing endpoint tests, rate-limiting so aggressively that normal use fails

---

**F08 — GitHub client silently returns []/{} on non-200**

- **Files**: `src/life_integrations/_clients/github_client_shim.py`
- **Issue**: On any non-200 response from GitHub API, the client silently returns `[]` or `{}` instead of raising. No 429 rate-limit handling. Errors are swallowed.
- **Fix**:
  1. On 200: return parsed JSON (existing behavior)
  2. On 403 with `X-RateLimit-Remaining: 0`: raise `RateLimitExceededError` with retry-after from `X-RateLimit-Reset` header
  3. On 404: raise `ProviderError(f"GitHub resource not found: {url}")`
  4. On 429: raise `RateLimitExceededError` with retry-after from `Retry-After` header
  5. On 401: raise `AuthenticationError("GitHub PAT invalid or expired")`
  6. On 5xx: raise `ProviderError(f"GitHub API error: {status_code}")`
  7. Add tests for each status code path
- **Verify**:
  - `grep -n "return \[\]\|return {}" src/life_integrations/_clients/github_client_shim.py` — should NOT have silent empty returns on non-200
  - `python -m pytest tests/p22/test_github*.py -v` passes
- **Forbidden**: Silently returning empty results on errors, swallowing HTTP errors

---

**F09 — Calendar/Drive: no 429 retry**

- **Files**: `src/life_integrations/_clients/calendar_client.py`, `src/life_integrations/_clients/drive_client.py`
- **Issue**: Calendar has 401-refresh-retry but NO 429 retry in CRUD paths. Drive detects 429 → raises ProviderError, NO retry/backoff. Will fail under Google API rate limits.
- **Fix**:
  1. Add a `_retry_with_backoff` decorator/method that catches 429, reads `Retry-After` header (or uses exponential backoff: 1s, 2s, 4s, 8s, max 3 retries), and retries
  2. Apply to all CRUD methods in both `calendar_client.py` and `drive_client.py`
  3. If still 429 after 3 retries: raise `RateLimitExceededError`
  4. Add tests: `test_calendar_429_retry`, `test_drive_429_retry`
- **Verify**:
  - `grep -n "429\|RateLimitExceeded\|retry\|backoff\|Retry-After" src/life_integrations/_clients/calendar_client.py` returns ≥1 match
  - `grep -n "429\|RateLimitExceeded\|retry\|backoff\|Retry-After" src/life_integrations/_clients/drive_client.py` returns ≥1 match
  - `python -m pytest tests/p22/test_calendar*.py tests/p22/test_drive*.py -v` passes
- **Forbidden**: Infinite retry loops, retrying without backoff, swallowing 429 silently

---

**F10 — X Poster leaks first 8 chars of access token in logs**

- **Files**: `x_poster/main.py` line 67
- **Issue**: `settings.x_access_token[:8] + "..."` logs first 8 characters of access token.
- **Fix**: Replace with `"***REDACTED***"` or a SHA256 hash prefix: `hashlib.sha256(settings.x_access_token.encode()).hexdigest()[:8]}`
- **Verify**:
  - `grep -n "x_access_token\[" x_poster/main.py` returns 0 matches
  - `grep -n "REDACTED\|redacted\|hash" x_poster/main.py` returns ≥1 match near line 67
- **Forbidden**: Logging any portion of the actual token, using `print()` instead of logger

---

**F11 — dry_run classification inconsistency**

- **Files**: `src/life_integrations/router.py` — `dry_run()` method
- **Issue**: `execute()` classifies with `provider=adapter.config.provider` but `dry_run()` classifies with `provider=integration_id`. These could differ, causing dry_run to report a different tier than actual execution.
- **Fix**: In `dry_run()`, change `provider=integration_id` to `provider=adapter.config.provider` (same as `execute()`). Ensure the adapter is resolved before classification, same as in `execute()`.
- **Verify**:
  - `grep -n "provider=" src/life_integrations/router.py` — both `execute()` and `dry_run()` should use `adapter.config.provider`
  - `python -m pytest tests/p22/test_router*.py tests/p22/test_*dispatch*.py -v` passes
- **Forbidden**: Changing `execute()` to use `integration_id` (that would make it worse)

---

**F12 — 3 HARD STOP fail-open windows**

- **Files**: `src/life_integrations/_shims.py` (lines 117-133), `src/life_integrations/consent.py` (lines 78-79, 105-108)
- **Issue**: Three locations where HARD STOP check fails open (returns "not active") instead of failing closed:
  1. `_shims.py:128-133`: `HardStopShim` returns `False` when neither Redis nor handler wired
  2. `_shims.py:117-127`: `HardStopShim` swallows handler exception, leaves `handler_active=False`
  3. `consent.py:78-79,105-108`: `ConsentGate` skips HARD STOP check when `hard_stop_checker=None`
- **Fix**:
  1. `_shims.py:128-133`: When neither Redis nor handler is wired, return `True` (HARD STOP active = fail-closed) with error log `"HARD STOP checker not configured — failing closed"`. Alternatively, raise `HardStopBlockedError`.
  2. `_shims.py:117-127`: When handler raises exception, return `True` (assume HARD STOP active = safer) with error log. Do NOT swallow and continue.
  3. `consent.py:78-79,105-108`: Already addressed in F03 for L2+. For L1, HARD STOP should still be checked if a checker is configured. If no checker, L1 passes (by design — L1 is auto-read).
  - Note: F03 fix covers consent.py part. This fix covers _shims.py parts.
  - Add tests: `test_hard_stop_fail_closed_no_redis_no_handler`, `test_hard_stop_fail_closed_on_handler_exception`
- **Verify**:
  - `grep -n "handler_active = False" src/life_integrations/_shims.py` — should NOT exist after fix (should be `True` or raise)
  - `python -m pytest tests/p22/test_*shim*.py tests/p22/test_consent*.py -v` passes
- **Forbidden**: Breaking production wiring (runtime.py wires both sources), making HARD STOP always active (would block everything)

---

**F13 — TRUNCATE not in WORM contract**

- **Files**: Database migration `alembic/versions/p22_001_integration_schema.py` or a new migration
- **Issue**: DB-level WORM enforcement revokes UPDATE and DELETE but NOT TRUNCATE. Table owner can wipe audit log via TRUNCATE.
- **Fix**: Create a new Alembic migration that:
  1. `REVOKE TRUNCATE ON audit.integration_api_log FROM guinevere_core;`
  2. Optionally: `ALTER TABLE audit.integration_api_log OWNER TO guinevere_audit_owner;` (separate role that can't be assumed by the app)
  3. Document the WORM contract in the migration docstring
- **Verify**:
  - Migration file exists and is idempotent
  - `grep -r "TRUNCATE" alembic/versions/` returns ≥1 match in the new migration
  - `python -m pytest tests/p22/test_audit*.py -v` passes
- **Forbidden**: Revoking INSERT or SELECT (would break audit writing/reading), dropping the table

---

**F14 — Implementation R1 fix log distorts verdicts**

- **Files**: `docs/setup-evidence/P22/implementation/audits/round-1/fix-log.md` (or equivalent path)
- **Issue**: Fix log claims `audit-consent-hardstop.md (PASS — no findings)` but actual audit has F2 HIGH. Claims `audit-project-namespace.md (PASS — no findings)` but actual audit has F4 MEDIUM. Claims `audit-audit-trail.md (completed in workflow)` but actual audit has 3 HIGH findings.
- **Fix**: Correct the fix log to accurately reflect the actual audit verdicts:
  1. `audit-consent-hardstop.md`: NEEDS_REVIEW (F2 HIGH — HARD STOP fail-open)
  2. `audit-project-namespace.md`: NEEDS_REVIEW (F4 MEDIUM — broad except)
  3. `audit-audit-trail.md`: NEEDS_REVIEW (3 HIGH — hash canonicalization, redaction gaps, concurrency)
  4. Add a note: "These findings were later addressed in round-2 fixes, see [commit/reference]"
- **Verify**: `grep -r "PASS — no findings" docs/setup-evidence/P22/implementation/audits/round-1/fix-log.md` returns 0 matches for the 3 audits listed above
- **Forbidden**: Deleting or rewriting the original audit files, falsifying verdict history

---

**F15 — Round-2 summary-adjudication aggressively reclassifies findings**

- **Files**: `docs/setup-evidence/P22/production-activation/audits/round-2/round-2-summary-adjudication.md`
- **Issue**: Reclassifies NEEDS_REVIEW to PASS via "fix in commit 4efe4c2". F-10 (secrets-in-journal) dismissed as "out of P22 scope" despite being a real MEDIUM finding.
- **Fix**: Add a caveat section to the summary-adjudication:
  1. Note that F2 HIGH (ConsentGate fail-open) was NOT actually fixed by commit 4efe4c2 (which only fixed HardStopShim construction). Cross-reference F03 in this brutal audit.
  2. Note that F-10 (9ROUTER_API_KEY in journal) is a real MEDIUM finding that was dismissed as out-of-scope. Recommend it be tracked as P20 technical debt.
  3. Do NOT change the PASS/FAIL verdicts — just add the caveats honestly.
- **Verify**: `grep -r "caveat\|NOTE\|WARNING\|brutal audit" docs/setup-evidence/P22/production-activation/audits/round-2/round-2-summary-adjudication.md` returns ≥1 match
- **Forbidden**: Changing historical verdicts, deleting the summary-adjudication file

---

#### MEDIUM (F16-F32) — FIX AS TECHNICAL DEBT

---

**F16 — README contradiction**

- **Files**: `docs/setup-evidence/P22/README.md`
- **Issue**: Status says "P22.3 FULL-COMPLETION" but progress table shows ALL waves as "⏸️ HOLD" and bottom note says "definition/planning phase only. No runtime code, adapters, or deployed services exist." But 45 source files + 51 test files DO exist.
- **Fix**: Rewrite README to accurately reflect:
  1. Status: "P22.3 IMPLEMENTED — BRUTAL AUDIT FAIL (5 CRITICAL, 10 HIGH, 17 MEDIUM) — FIXES IN PROGRESS"
  2. Remove "definition/planning phase only" note — implementation EXISTS
  3. Update progress table to show actual state of each wave
- **Verify**: `grep -r "definition/planning phase only" docs/setup-evidence/P22/README.md` returns 0 matches
- **Forbidden**: Claiming FULL-COMPLETION, deleting the README

---

**F17 — PROGRESS.md out of date**

- **Files**: `PROGRESS.md` (already partially fixed — verify consistency)
- **Issue**: Previously showed P22 as ⏸ PENDING. Updated by brutal audit to show 🔴 BRUTAL AUDIT FAIL. Verify all 3 P22 lines are consistent.
- **Fix**: Verify all 3 P22 references in PROGRESS.md show the updated status. If any were missed, update them.
- **Verify**: `grep "P22" PROGRESS.md` — all lines should show updated status, not "TBD"
- **Forbidden**: Reverting to TBD status

---

**F18 — C10 verification file missing**

- **Files**: `docs/setup-evidence/P22/full-completion/verification/`
- **Issue**: Has c1-c9, c11-c12 (11 files), NOT c1-c12 (12 files). C10 never existed.
- **Fix**: Identify what C10 was supposed to verify (check plan files or verification checklist). Either:
  1. Create C10 verification file with the actual verification, OR
  2. Document why C10 was skipped (e.g., "C10 was removed during planning, verification scope reduced to 11 items")
- **Verify**: `ls docs/setup-evidence/P22/full-completion/verification/c10*` returns a file OR a documented explanation exists
- **Forbidden**: Creating a fake verification file, deleting other verification files

---

**F19 — Test count discrepancy**

- **Files**: `docs/setup-evidence/P22/README.md`, `docs/setup-evidence/P22/full-completion/verification/f3-runtime-proof.md`
- **Issue**: README says 897 tests, f3-runtime-proof says 753. Delta of 144 unexplained.
- **Fix**: Run `python -m pytest tests/p22/ --co -q | wc -l` to get actual test count. Update both documents to the same number. Document whether parametrization inflates the runtime count.
- **Verify**: Both documents show the same test count number
- **Forbidden**: Inventing test counts, deleting test files to match a number

---

**F20 — Browser status drift**

- **Files**: `docs/setup-evidence/P22/implementation/p22-final-implementation-report.md`, `docs/setup-evidence/P22/production-activation/p22-production-status.md`
- **Issue**: Implementation report (2026-06-27) says Browser "OK (local)". Production status (2026-06-28) says CONFIG_MISSING.
- **Fix**: Add a note to the implementation report: "Browser status updated to CONFIG_MISSING on 2026-06-28 — 3 MCP tools need instance shims. See production-status.md for current status."
- **Verify**: Implementation report references the production status update
- **Forbidden**: Deleting either document

---

**F21 — Audit write failures are SILENT**

- **Files**: `src/life_integrations/audit_db_writer.py`
- **Issue**: Catches Exception, logs error, does NOT raise. "Audit must not block action path." Audit failures go undetected.
- **Fix**:
  1. Keep the non-blocking behavior (audit must not block actions) BUT add:
  2. Increment a Prometheus counter: `p22_audit_write_failures_total` with labels (integration_id, error_type)
  3. Log at ERROR level (not WARNING) with structured fields
  4. Add a health check endpoint or metric that surfaces audit write failure count
  5. Add test: `test_audit_write_failure_increments_counter`
- **Verify**:
  - `grep -n "Counter\|counter\|metric\|prometheus" src/life_integrations/audit_db_writer.py` returns ≥1 match
  - `python -m pytest tests/p22/test_audit*.py -v` passes
- **Forbidden**: Raising exceptions from audit writer (would block action path), swallowing errors without any counter/metric

---

**F22 — `seed_last_hash()` returns "" on error**

- **Files**: `src/life_integrations/audit_db_writer.py`
- **Issue**: Returns empty string on DB error — starts fresh chain. DB error could break hash chain silently.
- **Fix**:
  1. On DB error, log at CRITICAL level: `"Failed to seed last hash — audit chain may be broken"`
  2. Return `None` instead of `""` — caller should check for None and handle
  3. Add a health check: if `seed_last_hash()` returns None, mark audit as "DEGRADED"
  4. Add test: `test_seed_last_hash_returns_none_on_error`
- **Verify**:
  - `grep -n 'return ""' src/life_integrations/audit_db_writer.py` returns 0 matches in `seed_last_hash()`
  - `python -m pytest tests/p22/test_audit*.py -v` passes
- **Forbidden**: Raising from `seed_last_hash()` (would block startup), silently returning ""

---

**F23 — Registry race condition**

- **Files**: `src/life_integrations/registry.py`
- **Issue**: `get()` and `list_all()` are sync methods accessing `self._adapters` without lock. `register()`/`unregister()` are async with `asyncio.Lock`.
- **Fix**: Make `get()` and `list_all()` async and acquire `self._lock` before accessing `self._adapters`. OR use a thread-safe approach (e.g., `copy.deepcopy` of the dict under lock, then return the copy). Update all callers.
- **Verify**:
  - `grep -n "def get\|def list_all" src/life_integrations/registry.py` — both should be `async def`
  - OR: `grep -n "async with self._lock" src/life_integrations/registry.py` should appear in get/list_all
  - `python -m pytest tests/p22/ -v` passes (no regressions)
- **Forbidden**: Using a global lock that deadlocks, breaking existing callers without updating them

---

**F24 — `AuditChainVerificationError` defined but unused**

- **Files**: `src/life_integrations/audit.py`, `src/life_integrations/errors.py`
- **Issue**: `errors.py:71` defines `AuditChainVerificationError` but `audit.py:verify_chain()` returns `bool`, doesn't raise.
- **Fix**: Make `verify_chain()` raise `AuditChainVerificationError` on verification failure (with details about which event failed). Callers should catch and handle. Update existing tests that check the return value.
- **Verify**:
  - `grep -n "AuditChainVerificationError" src/life_integrations/audit.py` returns ≥1 match
  - `python -m pytest tests/p22/test_audit*.py -v` passes
- **Forbidden**: Removing the exception class, breaking callers without updating them

---

**F25 — No UUID v7 (OBSERVATION)**

- **Files**: `src/life_integrations/audit_db_writer.py`, `src/life_integrations/audit.py`
- **Issue**: Uses UUID v4. UUID v7 is the modern standard for time-sortable IDs.
- **Fix**: Either:
  1. Install `uuid-utils` or `pg_uuidv7` extension and use UUID v7 for `event_id`, OR
  2. Document that UUID v4 is intentional (sufficient for uniqueness, no time-sorting needed) and add a comment explaining why v7 is not needed
- **Verify**: Either UUID v7 is used, or a documented decision exists in code comments
- **Forbidden**: Breaking existing audit records, changing UUID format without migration

---

**F26 — `consent_callback` name collision**

- **Files**: `src/discord/cmd_consent.py` (line 67), `src/discord/cmd_integrations.py` (line 451)
- **Issue**: Both define `async def consent_callback`. Not a live collision (cmd_integrations not imported) but a latent landmine.
- **Fix**: Rename the callback in `cmd_integrations.py` to `integration_consent_callback` (or similar). Update any references in tests.
- **Verify**:
  - `grep -rn "def consent_callback" src/discord/` returns exactly 1 match (in cmd_consent.py)
  - `python -m pytest tests/p22/test_cmd_integrations.py -v` passes
- **Forbidden**: Renaming the one in cmd_consent.py (it's the canonical consent command)

---

**F27 — Bare `except Exception` in cmd_integrations.py**

- **Files**: `src/discord/cmd_integrations.py` line 130
- **Issue**: `except Exception: # noqa: BLE001` — AGENTS.md §5 lists bare except as forbidden.
- **Fix**: Catch specific exceptions instead of bare `Exception`. Likely candidates: `httpx.HTTPError`, `httpx.TimeoutException`, `KeyError`, `ValueError`. Add structured logging for the caught exception.
- **Verify**:
  - `grep -n "except Exception" src/discord/cmd_integrations.py` returns 0 matches
  - `python -m pytest tests/p22/test_cmd_integrations.py -v` passes
- **Forbidden**: Using `# noqa` to suppress linter warnings instead of fixing the code

---

**F28 — `_rpw` stores REDIS_PASSWORD**

- **Files**: `src/life_integrations/runtime.py` line 286
- **Issue**: `REDIS_PASSWORD` stored in variable `_rpw` — could end up in error context or stack trace.
- **Fix**: Use `os.environ.get("REDIS_PASSWORD")` inline (not stored in a variable). Or if a variable is needed, name it `_REDIS_PASS` and ensure it's not logged. Add `__repr__` redaction if it's in a class.
- **Verify**:
  - `grep -n "_rpw\|_REDIS_PASS" src/life_integrations/runtime.py` — variable should not appear in any log statement or error message
- **Forbidden**: Logging the password variable, storing it in a class without `__repr__` redaction

---

**F29 — `chain_version=2` hardcoded (OBSERVATION)**

- **Files**: `src/life_integrations/audit_db_writer.py`, `src/life_integrations/audit.py`
- **Issue**: `chain_version = 2` hardcoded in both schema default and writer INSERT literal. No upgrade path to v3.
- **Fix**: Make `chain_version` configurable via environment variable or settings. Default to 2. Add a comment: `# To upgrade: increment chain_version, run migration, update AuditLogger.verify_chain() to handle version-specific canonicalization`
- **Verify**: `grep -n "chain_version" src/life_integrations/audit_db_writer.py` shows configurable value, not hardcoded literal
- **Forbidden**: Changing the default value (would break existing chain), removing the field

---

**F30 — `secrets.py` provider abstraction is DEAD CODE**

- **Files**: `src/life_integrations/secrets.py`, `src/life_integrations/wiring.py`
- **Issue**: `EnvSecretProvider` defined but never instantiated. `ProjectVaultSecretProvider` defined but never imported. Every adapter reads `os.environ.get()` directly.
- **Fix**: Either:
  1. Wire the abstraction: instantiate `EnvSecretProvider` in `wiring.py`, pass to adapters, replace direct `os.environ.get()` calls, OR
  2. Remove the dead code: delete `secrets.py` and update imports
  - Option 2 is simpler and lower-risk. Option 1 is better architecture but higher effort.
  - Recommended: Option 2 (remove dead code) for now, create a TODO for Option 1 as future improvement.
- **Verify**:
  - If removing: `grep -r "EnvSecretProvider\|ProjectVaultSecretProvider" src/life_integrations/` returns 0 matches
  - `python -m pytest tests/p22/ -v` passes
- **Forbidden**: Leaving dead code in place, breaking imports

---

**F31 — P20 "soak" is 37 minutes, not 6 hours**

- **Files**: `docs/setup-evidence/P22/implementation/audits/round-1/audit-p20-p19-regression.md` or equivalent evidence files
- **Issue**: Longest continuous observation is ~37 minutes, not 6 hours. NRestarts=0 measures ~40 min post-restart.
- **Fix**: Add a caveat to the P20 regression evidence:
  1. Note: "P20 stability observation window is ~37 minutes post-restart, not a 6-hour soak. The 6-hour metric block counts events backwards from 'now', not a continuous undisturbed run. NRestarts=0 is valid but measures post-restart stability only."
  2. Recommend: "A proper 6-hour soak should be conducted post-fix to verify long-term stability."
- **Verify**: `grep -r "37 min\|post-restart\|not a.*soak" docs/setup-evidence/P22/` returns ≥1 match
- **Forbidden**: Deleting the P20 regression evidence, falsifying NRestarts=0

---

**F32 — No external signature on audit chain (OBSERVATION)**

- **Files**: `src/life_integrations/audit.py`
- **Issue**: Pure intra-chain SHA256 — no Ed25519/RSA/Merkle root/timestamping authority.
- **Fix**: This is an observation, not a blocking finding. Add a comment in `audit.py`:
  ```python
  # NOTE: Audit chain uses intra-chain SHA256 only. No external signature
  # (Ed25519/RSA/Merkle root/timestamping authority). Chain integrity relies
  # on DB-level WORM enforcement (REVOKE UPDATE, DELETE, TRUNCATE).
  # For high-integrity use cases, consider adding external notarization.
  ```
- **Verify**: `grep -n "external signature\|Ed25519\|notarization" src/life_integrations/audit.py` returns ≥1 match
- **Forbidden**: Implementing external notarization without an ADR (this is an architecture decision)

---

### EXECUTION ORDER

1. **Research wave** (parallel): Fire explore agents to read every file referenced above
2. **CRITICAL fixes** (F01-F05): Can be parallel if no collision:
   - F01 (Discord entrypoint) — independent
   - F02 (runtime/docs) — independent
   - F03 (consent.py) — independent
   - F04 (permissions.py) — independent
   - F05 (runtime.py audit writer) — **COLLISION with F02** (both touch runtime.py) — sequence F02 then F05, or single owner
3. **HIGH fixes** (F06-F15):
   - F06 (docs) — independent
   - F07 (FastAPI middleware) — independent
   - F08 (github client) — independent
   - F09 (calendar/drive clients) — independent
   - F10 (x_poster) — independent
   - F11 (router.py) — independent
   - F12 (_shims.py) — **DEPENDS on F03** (both touch consent/hard-stop) — sequence after F03
   - F13 (DB migration) — independent
   - F14 (docs fix log) — independent
   - F15 (docs summary) — independent
4. **MEDIUM fixes** (F16-F32): All independent of each other. Can be fully parallel.
   - F23 (registry.py) — touches registry.py, check collision with F03 tests
   - F24 (audit.py) — touches audit.py, check collision with F05
   - F26/F27 (cmd_integrations.py) — **COLLISION** — single owner, fix both in one pass

### VERIFICATION REQUIREMENTS

After ALL fixes:
1. Run `python -m pytest tests/p22/ -v` — all tests pass
2. Run `python -m pytest tests/p22/ --co -q | wc -l` — record actual test count
3. Run `lsp_diagnostics` on all changed files — clean
4. Run `grep -rn "as any\|# type: ignore\|@ts-ignore\|@ts-expect-error" src/life_integrations/` — 0 matches
5. Run `grep -rn "except Exception.*:" src/life_integrations/ src/discord/cmd_integrations.py` — 0 bare excepts (documented ones need `# noqa` with justification)
6. Write evidence summary to `docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/summary.md`
7. Update PROGRESS.md P22 status to reflect post-fix state
8. Spawn auditor sub-agents to verify each fix — write reports to `docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/`

### OUTPUT

- Changed files list
- Test results (pass/fail counts)
- `lsp_diagnostics` results
- Evidence summary path
- Auditor reports paths
- PROGRESS.md update
- Remaining issues (if any)

## PROMPT END
