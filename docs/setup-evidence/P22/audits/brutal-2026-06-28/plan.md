# P22 Brutal-Audit Fix — Batch Plan + Per-Step Scaffolds

**Date:** 2026-06-28
**Author:** Guinevere (parent)
**Mission:** Fix all 32 findings (5 CRITICAL, 10 HIGH, 17 MEDIUM) from `brutal-audit-report.md`.
**Research inputs:** R1–R6 reports in `research/` (read by parent). R7 (docs/tests) in flight — F14–F20 specifics filled when it lands; scaffolds below already cite the audit's stated claims.

---

## 1. Ground-Truth Corrections (research → audit deltas)

These CHANGE the implementation vs. the raw audit text. Implementers must follow the CORRECTION, not the audit wording.

| Finding | Audit claim | Research correction (ground truth) |
|---|---|---|
| F05 | runtime.py constructs AuditLogger target=None | **TRUE on main.** Literal `audit_writer=None` at `src/core/main.py:468` → flows runtime.py:315 → wiring.py:149 → audit.py:190. `IntegrationAuditWriter` is NOT imported/instantiated on the live path. NO file fallback exists. Fix site = `src/core/main.py` (lifespan) + `runtime.py`. P22.1 memory claim is STALE (never merged / reverted). |
| F08 | github_client silently returns []/{} | **HOLDS.** 18 inline-REST methods. Path is `src/life_integrations/adapters/_clients/github_client_shim.py` (NOT `src/life_integrations/_clients/` — the fix-prompt FILE LANDSCAPE has the wrong path). |
| F09 | Calendar/Drive no 429 retry | **PARTIAL.** Drive already maps 429→ProviderError (`drive_client.py:312-316`, constant `_HTTP_RATE_LIMIT=429` line 92) but no retry/backoff. Calendar has NO 429 branch at all (429 falls into `except Exception → _fail_missing` → CONFIG_MISSING). Different fix shape per client. |
| F24 | `AuditChainVerificationError` defined but unused | **PARTIAL — name correction.** Actual class is `ChainVerificationError` (errors.py:70-71), NOT `AuditChainVerificationError`. Both are unused. Fix must use the REAL name `ChainVerificationError`. |
| F11 | dry_run uses integration_id not adapter.config.provider | **HOLDS.** router.py:252 has `provider = adapter.config.provider` (DEAD CODE) then router.py:254 calls `classify(provider=integration_id, action=action)`. Fix = change line 254 to `provider=provider`. |
| F13 | TRUNCATE not revoked | **PARTIAL.** Migration IS idempotent (`CREATE TABLE IF NOT EXISTS`) + chains correctly (`down_revision="p19_003_audit_chain_version"`). Only UPDATE/DELETE revoked (migration:78-83). Fix = new migration adding `REVOKE TRUNCATE`. |
| F23 | registry get/list_all sync without lock | **HOLDS.** Callers: `router.py:122` (execute), `router.py:240` (dry_run), `routes.py:255` (status endpoint), `scripts/p22_smoke_test.py:92-93`. Fix = thread-safe snapshot under lock (keep sync signatures to avoid caller ripple). |
| F28 | _rpw stores REDIS_PASSWORD | **HOLDS (variable present), PARTIALLY-HOLDS (no live leak).** `_rpw` only at runtime.py:286+293, not in any logger call. Fix = inline `os.environ.get("REDIS_PASSWORD", "") or None`. |
| F30 | secrets.py dead code | **HOLDS.** `EnvSecretProvider`/`ProjectVaultSecretProvider` defined but instantiated ONLY in `tests/p22/test_project_isolation.py`. Unused imports at wiring.py:42 + runtime.py:42. Fix = Option 2 (remove dead code + unused imports). |
| F20 | Browser status drift | **HOLDS (docs only).** Code is honest (returns config_missing). Fix = doc note only. |
| F10 | x_poster token leak | **HOLDS.** `src/x_poster/main.py:67` (note: `src/x_poster/` not `x_poster/`). Fix = redact. |
| F26/F27 | consent_callback collision + bare except | **HOLDS.** cmd_integrations.py:451 `consent_callback`; :130 `except Exception: # noqa: BLE001`. Fix F01 (which imports cmd_integrations) creates the live collision → F01+F26+F27 MUST be one owner. |

---

## 2. Collision Scan + Ownership Map

Shared-file findings → single owner. Independent files → parallel.

| Owner batch | Findings | Shared files | Mode |
|---|---|---|---|
| **OWNER-A: Discord layer** | F01 + F26 + F27 | `cmd_integrations.py`, `_entrypoint.py`, `_command_registry.py` | ONE sub-agent, sequential within (F26 rename first → F27 except fix → F01 wire) |
| **OWNER-B: Runtime layer** | F02 + F05 + F28 | `runtime.py` (+ F05 also `src/core/main.py`) | ONE sub-agent, sequential (F28 inline → F05 wire writer → F02 logs) |
| **OWNER-C: Consent/shims** | F03 + F12 | `consent.py` (F03), `_shims.py` (F12) | F03 first (consent.py), then F12 (_shims.py) — different files, but F12.3 cross-refs F03 |
| **Independent (parallel)** | F04 (permissions.py), F11 (router.py), F08 (github_client_shim.py), F09 (calendar+drive clients), F10 (x_poster/main.py), F13 (new migration), F07 (main.py+routes.py — NOTE: main.py also touched by F05 OWNER-B → F07 must run AFTER OWNER-B or be folded into OWNER-B), F21+F22+F24+F25+F29+F32 (audit.py/audit_db_writer.py/errors.py — SINGLE audit-owner), F23 (registry.py), F30 (secrets.py+wiring.py+runtime.py — runtime.py touched by OWNER-B → F30 AFTER OWNER-B) | — | parallel, respecting the runtime.py/main.py/audit.py sequencing |

### Sequencing constraints (hard)
1. **OWNER-B (F02/F05/F28) runs BEFORE F07** (F07 adds middleware to main.py; F05 edits main.py lifespan). Either fold F07 into OWNER-B, or run F07 after OWNER-B completes. **Decision: fold F07 into OWNER-B** (both touch main.py) → OWNER-B = F02+F05+F07+F28.
2. **OWNER-B runs BEFORE F30** (F30 removes unused import at runtime.py:42 + wiring.py:42; OWNER-B edits runtime.py). Run F30 after OWNER-B.
3. **F03 runs BEFORE F12** (F12.3 cross-refs consent.py lines fixed by F03; F12 touches _shims.py only after F03 consent gate is fail-closed).
4. **Audit-owner (F21/F22/F24/F25/F29/F32) is ONE sub-agent** — all touch audit.py / audit_db_writer.py / errors.py. Sequential within.
5. **F09 is ONE sub-agent** for both calendar_client.py + drive_client.py (shared retry helper pattern).

### Refined ownership batches (final)
- **B1 (Discord)**: F26→F27→F01 — one agent
- **B2 (Runtime+API)**: F28→F05→F02→F07 — one agent (all touch runtime.py or main.py)
- **B3 (Consent/Shims)**: F03→F12 — one agent
- **B4 (Audit trail)**: F22→F21→F24→F25→F29→F32 — one agent (audit.py/audit_db_writer.py/errors.py)
- **B5 (Router/perms)**: F04 (permissions.py) + F11 (router.py) — one agent (both classifier/router, related)
- **B6 (Clients)**: F08 (github) + F09 (calendar+drive) — one agent (client error-handling theme)
- **B7 (Registry)**: F23 — one agent
- **B8 (Migration)**: F13 — one agent
- **B9 (Secrets dead code)**: F30 — AFTER B2 — one agent
- **B10 (x_poster)**: F10 — one agent
- **B11 (Docs batch)**: F06+F14+F15+F16+F17+F18+F19+F20+F31 — one agent (all docs, no code) — needs R7b results

### Parallelism plan
- **Wave 1 (parallel)**: B1, B2, B3, B4, B5, B6, B7, B8, B10 — 9 independent agents
- **Wave 2 (after B2)**: B9 (F30 — needs runtime.py stable)
- **Wave 2 (after R7b)**: B11 (docs — needs ground-truth verdicts)

---

## 3. Per-Step Verification Scaffolds

Each scaffold = (Expected Files, Forbidden Patterns, Required Commands, Hard Rejection Criteria). Delegation prompts include the scaffold verbatim.

### B1 — Discord (F26→F27→F01)

**F26**: Rename `cmd_integrations.py:451` `consent_callback` → `integration_consent_callback`. Update `__all__` (line 650-657) + any internal callers.
**F27**: `cmd_integrations.py:130` — replace `except Exception as exc: # noqa: BLE001` with specific catches: `httpx.HTTPError` (superset of HTTPStatusError+RequestError), `json.JSONDecodeError`, `KeyError`, `ValueError`. Keep `logger.exception` structured logging. Remove `# noqa`.
**F01**: `_entrypoint.py` — import `cmd_integrations`; add 6 `self.tree.command(name=..., description=..., guild=...)(cb)` calls in setup_hook for: `integration-status`→`status_callback`, `integration-capabilities`→`capabilities_callback`, `integration-test`→`test_callback`, `integration-missing`→`missing_callback`, `integration-consent`→`integration_consent_callback` (renamed), `integration-dry-run`→`dry_run_callback`. Add 6 `CommandSpec` entries to `COMMAND_SPECS` (`_command_registry.py:130-253`). Bump `require_canonical_registry()` count 35→41 (`:296-297`). Add the 6 names to `core_names` tuple (`:406-426`) so they're wired (not stubbed) OR let stub loop handle — but wiring explicitly is correct.

- **Expected Files**: `src/discord/cmd_integrations.py`, `src/discord/_entrypoint.py`, `src/discord/_command_registry.py`
- **Forbidden Patterns**: `def consent_callback` in cmd_integrations.py (0 matches after rename); `except Exception` in cmd_integrations.py (0 matches); `# noqa` in cmd_integrations.py (0 new); `as any`/`# type: ignore`/`@ts-ignore` (0)
- **Required Commands**: `python -m pytest tests/p22/test_cmd_integrations.py -v` → exit 0; `python -c "from src.discord._command_registry import COMMAND_SPECS, require_canonical_registry; require_canonical_registry(); assert len(COMMAND_SPECS)==41"` → exit 0; `grep -rn "def consent_callback" src/discord/` → exactly 1 match (cmd_consent.py only)
- **Hard Rejection**: registry count != 41; any test in test_cmd_integrations.py fails; consent_callback still in cmd_integrations.py; bare except remains; existing 35 commands broken (test_cmd_consent / other discord tests fail)

### B2 — Runtime+API (F28→F05→F02→F07)

**F28**: runtime.py:286 — inline `password=os.environ.get("REDIS_PASSWORD", "") or None` into the `Redis(...)` ctor at :293; delete `_rpw` variable.
**F05**: `src/core/main.py:468` — replace `audit_writer=None` with a real writer: construct `IntegrationAuditWriter(session_factory=...)` from `DATABASE_URL` (async engine). If DB unavailable, fall back to a file-based writer writing JSON-lines to `logs/audit-integration.log` (create a small `FileAuditWriter` if none exists, or extend `IntegrationAuditWriter` with a file fallback). Add startup log `p22.audit_writer_wired target=db` or `p22.audit_writer_db_unavailable fallback=file`. Wire the writer through `build_runtime_registry(audit_writer=...)`.
**F02**: runtime.py — for each of the 10 CONFIG_MISSING adapters, replace generic `logger.info("p22.adapter.config_missing", adapter=missing)` with an actionable log naming the missing env var / credential (e.g. `adapter=missing, missing_env="GITHUB_PAT", hint="..."`). Use a small lookup dict `adapter → (env_var, hint)`.
**F07**: `src/core/main.py` — add rate-limiting. Prefer a custom token-bucket middleware (avoid new dep `slowapi` unless already installed — check `pip show slowapi`). Limits: reads 60/min/IP, mutations 10/min/API-key, dry-run 5/min/API-key. Return 429 + `Retry-After` header. Add to `app.add_middleware(...)`. Add test `test_rate_limiting_returns_429`.

- **Expected Files**: `src/life_integrations/runtime.py`, `src/core/main.py`, `src/life_integrations/audit_db_writer.py` (if file fallback added here), `src/core/api/routes.py` (if middleware helpers), new test files
- **Forbidden Patterns**: `target=None`/`audit_writer=None` in main.py (0); `_rpw` in runtime.py (0); `as any`/`# type: ignore` (0); empty except (0); hardcoded DB credentials (0)
- **Required Commands**: `python -m pytest tests/p22/test_audit*.py tests/p22/test_integrations_endpoints.py -v` → exit 0; `python -m pytest tests/p22/ -v` → exit 0 (no regressions); `grep -n "_rpw" src/life_integrations/runtime.py` → 0; `grep -n "audit_writer=None" src/core/main.py` → 0; `grep -rn "slowapi\|Limiter\|rate_limit\|RateLimit\|TokenBucket\|token_bucket" src/core/` → ≥1
- **Hard Rejection**: audit writer still None in main.py; `_rpw` persists; rate-limit test fails; any P22 test regresses; DB credentials hardcoded; startup crashes when DB unreachable (file fallback must work)

### B3 — Consent/Shims (F03→F12)

**F03**: `consent.py` ConsentGate.check() — when `self._hard_stop_checker is None` AND `tier >= PermissionTier.L2_WRITE`, return `False, "hard_stop_checker not configured — fail-closed"` (place this check BEFORE the L4 check so L2/L3 are denied; L1 still passes at the top; L4 always False). Update docstring (remove "assumes clear if None"). Add test `test_consent_gate_fail_closed_without_hard_stop_checker`.
**F12**: `_shims.py` — (1) `:128-133` (and async `:166-169`): when neither Redis nor handler wired, return `True` (fail-closed = HARD STOP active) + `logger.error("hard_stop_shim.no_source_fail_closed")`. (2) `:117-126` (and async `:159-164`): when handler raises, return `True` (assume active = safer) + `logger.error("hard_stop_shim.handler_check_failed_fail_closed", error=str(e))`. Do NOT swallow+continue. Add tests `test_hard_stop_fail_closed_no_redis_no_handler`, `test_hard_stop_fail_closed_on_handler_exception`.

- **Expected Files**: `src/life_integrations/consent.py`, `src/life_integrations/_shims.py`, new test files
- **Forbidden Patterns**: `handler_active = False` swallowed-without-fail-closed in _shims.py (0); `as any`/`# type: ignore` (0); bare except (0 — but the existing `except Exception as e: # noqa: BLE001` in _shims handler check is the TARGET of the fix; after fix it should log+return True, the except can stay specific or remain with fail-closed return — verify no silent swallow)
- **Required Commands**: `python -m pytest tests/p22/test_consent*.py tests/p22/test_*shim*.py -v` → exit 0; `python -m pytest tests/p22/ -v` → exit 0; `grep -n "hard_stop_checker is None" src/life_integrations/consent.py` → line must NOT skip for L2+ (verify fail-closed branch present)
- **Hard Rejection**: L1 auto-read broken; L4 always-forbidden broken; HARD STOP always-active (blocks everything — must only fail-closed when checker missing/raises, not unconditionally); any consent/shim test regresses

### B4 — Audit trail (F22→F21→F24→F25→F29→F32)

**F22**: `audit_db_writer.py:seed_last_hash()` — on DB error, log CRITICAL `"audit chain may be broken"`, return `None` (not `""`). Caller checks None → mark audit DEGRADED. Keep empty-result returning `""` (legitimate fresh chain) OR also return None — DECISION: empty result returns `""` (valid fresh chain), DB error returns `None` (distinct). Add test `test_seed_last_hash_returns_none_on_error`.
**F21**: `audit_db_writer.py` write method — keep non-blocking BUT add Prometheus counter `p22_audit_write_failures_total` (labels: integration_id, error_type) + log ERROR structured. Add a module-level `Counter` (reuse `prometheus_client` if available; check imports). Add test `test_audit_write_failure_increments_counter`.
**F24**: `audit.py:verify_chain()` — raise `ChainVerificationError` (the REAL class name from errors.py:70) on verification failure, with failing-event details. Update callers/tests that check bool return.
**F25**: `audit.py` — add comment documenting UUID v4 is intentional (sufficient for uniqueness; DB-side `gen_random_uuid()` fallback; v7 not needed for correctness, only time-sortability). No code change.
**F29**: `audit_db_writer.py` + `audit.py` — `chain_version` from env `P22_AUDIT_CHAIN_VERSION` (default 2) + comment on upgrade path. Don't change default.
**F32**: `audit.py` — add comment noting intra-chain SHA256 only, no external signature, relies on DB WORM; consider external notarization for high-integrity. No code change.

- **Expected Files**: `src/life_integrations/audit.py`, `src/life_integrations/audit_db_writer.py`, `src/life_integrations/errors.py` (if class rename/clarify), new test files
- **Forbidden Patterns**: `return ""` in seed_last_hash on DB-error path (0); silent swallow in write (counter must increment); `AuditChainVerificationError` (wrong name — use `ChainVerificationError`); `as any`/`# type: ignore` (0)
- **Required Commands**: `python -m pytest tests/p22/test_audit*.py -v` → exit 0; `python -m pytest tests/p22/ -v` → exit 0; `grep -n "ChainVerificationError" src/life_integrations/audit.py` → ≥1; `grep -n "external signature\|Ed25519\|notarization" src/life_integrations/audit.py` → ≥1
- **Hard Rejection**: verify_chain still returns bool only; seed_last_hash returns "" on DB error; audit write failures still silent (no counter); existing audit tests regress

### B5 — Router/Perms (F04 + F11)

**F04**: `permissions.py:213-218` — change fallback `PermissionTier.L1_READ` → `PermissionTier.L2_WRITE`; add `logger.warning(f"classifier.unknown_action action={action!r} provider={provider!r} — defaulting to L2_WRITE (consent required)")`. Update existing tests expecting L1 for unknown → L2.
**F11**: `router.py:254` — change `classify(provider=integration_id, action=action)` → `classify(provider=provider, action=action)` (uses the already-assigned `provider = adapter.config.provider` at :252, removing the dead-code bypass).

- **Expected Files**: `src/life_integrations/permissions.py`, `src/life_integrations/router.py`, test files
- **Forbidden Patterns**: `L1_READ` as classify fallback (0); `provider=integration_id` in dry_run (0); `as any`/`# type: ignore` (0)
- **Required Commands**: `python -m pytest tests/p22/test_permissions*.py tests/p22/test_router*.py tests/p22/test_*dispatch*.py -v` → exit 0; `python -m pytest tests/p22/ -v` → exit 0
- **Hard Rejection**: unknown action defaults to L4 (too restrictive) or L1; dry_run still uses integration_id; dispatch tests regress

### B6 — Clients (F08 + F09)

**F08**: `adapters/_clients/github_client_shim.py` — for each non-200 path: 403+`X-RateLimit-Remaining: 0`/429 → `RateLimitExceededError(provider="github", retry_after=<from Retry-After or X-RateLimit-Reset>)`; 404 → `ProviderError("github", 404, "resource not found: {url}")`; 401 → `AuthenticationError("github PAT invalid or expired")`; 5xx → `ProviderError("github", status, "GitHub API error")`. NO silent `return []`/`return {}` on non-200. Note: methods that delegate to MCP tools (list_repos, get_file, search_code, create_issue, create_pr) are OUT of scope. Add per-status tests.
**F09**: `calendar_client.py` — add `elif status == 429:` branch in each CRUD method's except block (5 methods: list_events, get_event, create_event, update_event, delete_event) reading `Retry-After` → raise `RateLimitExceededError(provider="google-calendar", retry_after=...)`. `drive_client.py` `_call_with_retry` (:288-320) — add 429 retry with exponential backoff (1s/2s/4s/8s, max 3, honor Retry-After) before raising `RateLimitExceededError(provider="google-drive", retry_after=...)` (currently raises ProviderError — change to RateLimitExceededError). Add `test_calendar_429_retry`, `test_drive_429_retry`.

- **Expected Files**: `src/life_integrations/adapters/_clients/github_client_shim.py`, `src/life_integrations/adapters/_clients/calendar_client.py`, `src/life_integrations/adapters/_clients/drive_client.py`, test files
- **Forbidden Patterns**: `return []`/`return {}` on non-200 in github shim (0 — except delegated MCP methods); silent 429 swallow (0); infinite retry (0 — max 3); `as any`/`# type: ignore` (0)
- **Required Commands**: `python -m pytest tests/p22/test_github*.py tests/p22/test_calendar*.py tests/p22/test_drive*.py -v` → exit 0; `python -m pytest tests/p22/ -v` → exit 0
- **Hard Rejection**: silent empty returns on errors; no Retry-After; infinite loop; client tests regress

### B7 — Registry (F23)

**F23**: `registry.py` — keep `get()`/`list_all()`/`list_by_capability()`/`get_audit_summary()` SYNC but make them thread-safe: acquire a sync lock (`threading.Lock`) for the snapshot, OR replace `asyncio.Lock` with `threading.RLock` and snapshot `dict(self._adapters)` under it in readers. Update the docstring (:35-38) to match reality. DECISION: use `threading.Lock` for readers + keep `asyncio.Lock` for writers is messy — cleaner: switch to `threading.RLock` for both (writers drop async? NO — register/unregister are async-called from wiring). Safest: add a separate `threading.Lock` for read-snapshots, keep `asyncio.Lock` for async writes; readers do `with self._read_lock: return dict(self._adapters).get(...)` etc. This avoids changing caller signatures (callers stay sync).

- **Expected Files**: `src/life_integrations/registry.py`, test files
- **Forbidden Patterns**: unsynchronized read of `self._adapters` (0 — all reads under lock); `as any`/`# type: ignore` (0); deadlock (read lock not held across await — readers are sync so safe)
- **Required Commands**: `python -m pytest tests/p22/ -v` → exit 0 (no regressions); `grep -n "def get\|def list_all" src/life_integrations/registry.py` → still sync signatures; `grep -n "with self._read_lock\|threading.Lock" src/life_integrations/registry.py` → ≥1
- **Hard Rejection**: caller signatures changed (would ripple); deadlock; registry tests regress

### B8 — Migration (F13)

**F13**: new idempotent Alembic migration `p22_002_revoke_truncate_audit.py` (or next number) — `REVOKE TRUNCATE ON audit.integration_api_log FROM guinevere_core;` (and optionally `ALTER TABLE ... OWNER TO guinevere_audit_owner` if role exists — check first; if not, just REVOKE + document). `down_revision = "p22_001_integration_schema"`. Document WORM contract in docstring (UPDATE/DELETE/TRUNCATE all revoked; only INSERT/SELECT granted). Idempotent (REVOKE is safe to re-run).

- **Expected Files**: `alembic/versions/p22_002_*.py`
- **Forbidden Patterns**: `REVOKE INSERT`/`REVOKE SELECT` (0 — would break audit); `DROP TABLE` (0); non-idempotent; `as any`/`# type: ignore` (0)
- **Required Commands**: `python -m pytest tests/p22/test_audit*.py -v` → exit 0; `grep -r "TRUNCATE" alembic/versions/p22_002_*` → ≥1; migration imports clean (`python -c "import importlib.util, pathlib; p=pathlib.Path('alembic/versions/p22_002_revoke_truncate_audit.py'); spec=importlib.util.spec_from_file_location('m', p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.revision, m.down_revision)"` → prints revision + p22_001)
- **Hard Rejection**: revokes INSERT/SELECT; drops table; breaks migration chain; non-idempotent

### B9 — Secrets dead code (F30) — AFTER B2

**F30**: Option 2 (remove dead code). Delete `src/life_integrations/secrets.py` classes `EnvSecretProvider`/`ProjectVaultSecretProvider`/`SecretProvider` IF NOT used by tests — BUT R3 says they ARE used in `tests/p22/test_project_isolation.py`. So: KEEP secrets.py (tests use it), but REMOVE the unused imports at `wiring.py:42` and `runtime.py:42`. Document that secrets.py is test-only / future-fork scaffolding (Hermes). Add a module docstring to secrets.py noting "test/future-fork scaffolding — not instantiated in P22 production wiring; adapters read env directly by design (local deviation)".

- **Expected Files**: `src/life_integrations/wiring.py`, `src/life_integrations/runtime.py`, `src/life_integrations/secrets.py` (docstring only)
- **Forbidden Patterns**: unused `EnvSecretProvider` import in wiring.py/runtime.py (0); deleting test-used code (0); `as any`/`# type: ignore` (0)
- **Required Commands**: `python -m pytest tests/p22/test_project_isolation.py -v` → exit 0; `python -m pytest tests/p22/ -v` → exit 0; `grep -n "EnvSecretProvider" src/life_integrations/wiring.py src/life_integrations/runtime.py` → 0
- **Hard Rejection**: breaks test_project_isolation.py; deletes code tests depend on; runtime.py/wiring.py regress

### B10 — x_poster (F10)

**F10**: `src/x_poster/main.py:67` — replace `x_access_token=settings.x_access_token[:8] + "..." if settings.x_access_token else "not_set"` with `x_access_token_present=bool(settings.x_access_token)` (cleanest — no token fragment). Verify 0 matches of `x_access_token[:` in file.

- **Expected Files**: `src/x_poster/main.py`
- **Forbidden Patterns**: `x_access_token[:` (0); `settings.x_access_token[:8]` (0); logging any token portion (0); `as any`/`# type: ignore` (0)
- **Required Commands**: `grep -n "x_access_token\[" src/x_poster/main.py` → 0; `grep -n "x_access_token_present" src/x_poster/main.py` → ≥1; (if x_poster has tests) run them
- **Hard Rejection**: any token fragment in logs; `print()` instead of logger

### B11 — Docs batch (F06+F14+F15+F16+F17+F18+F19+F20+F31) — PARENT-OWNED (R7b complete)

All docs, no code. R7b ground-truth absorbed. **Parent owns this batch** (surgical per-file edits). Exact paths + corrections from R7b:

- **F06**: `docs/setup-evidence/P22-brutal-audit-handoff.md:13` lists "weather, search, obscura" alongside 10 real adapters → replace with the real 13: `browser, gmail, calendar, drive, notion, telegram, github, whatsapp, discord, finance, vps, memory, filesystem` (alphabetical or as-wired). Verify `grep -rn "weather" docs/setup-evidence/P22*` and `grep -rn "obscura" docs/setup-evidence/P22-brutal-audit-handoff.md` → 0 phantom-adapter mentions.
- **F14**: `docs/setup-evidence/P22/implementation/fixes/p22-round-1-fix-log.md` — line 29 `audit-consent-hardstop.md (PASS — no findings)` → NEEDS_REVIEW (F2 HIGH HARD-STOP fail-open); line 33 `audit-project-namespace.md (PASS — no findings)` → NEEDS_REVIEW (F4 MEDIUM broad except); line 37 `audit-audit-trail.md (completed in workflow)` → NEEDS_REVIEW (2 HIGH + 4 MED per audit-audit-trail.md:30 "PASS WITH ACCEPTED RISK"); add note "these were later addressed in round-2 + brutal audit F03/F04/F21-F24 — see brutal-2026-06-28 fix-verification". Do NOT delete originals.
- **F15**: `docs/setup-evidence/P22/production-activation/audits/round-2/round-2-summary-adjudication.md` — add a caveat section: (a) F2 HIGH (ConsentGate fail-open when hard_stop_checker=None) was NOT fixed by commit 4efe4c2 (which only fixed HardStopShim construction / wiring.py docstring) — cross-ref brutal audit F03; (b) F-10 (9ROUTER_API_KEY in journal) is a real MEDIUM finding dismissed as "out of P22 scope" — recommend tracking as P20 technical debt. Do NOT change the PASS/FAIL verdicts.
- **F16**: `docs/setup-evidence/P22/README.md` — line 3 status → "P22.3 IMPLEMENTED — BRUTAL AUDIT FAIL (5 CRITICAL, 10 HIGH, 17 MEDIUM) — FIXES IN PROGRESS"; lines 105-110 progress table → mark waves as IMPLEMENTED (not ⏸️ HOLD); line 126 → remove "definition/planning phase only. No runtime code, adapters, or deployed services exist." (runtime code DOES exist). Verify `grep "definition/planning phase only" docs/setup-evidence/P22/README.md` → 0.
- **F17**: `PROGRESS.md` — lines 52, 991, 994, 1024, 1075 already show 🔴 BRUTAL AUDIT FAIL (good); line 991/994 "P22: Additional Integrations TBD" + "P22-001 TBD" → update to reflect implemented+audit-fail state. Verify all P22 lines consistent (no stale TBD).
- **F18**: `docs/setup-evidence/P22/full-completion/verification/c10-filesystem-dispatch.md` — CREATE this file (genuine verification, not fake). C10 = "filesystem_adapter: verify write/delete (content hash) complete" (per plan:51). Ground it in: filesystem_adapter uses pathlib + subprocess, `_FORBIDDEN_PATHS` allowlist, git-tracked check, `sha256` content_hash, tombstone on delete (per brutal-audit Angle 1 row 11). Verify `ls docs/setup-evidence/P22/full-completion/verification/c10*` returns a file.
- **F19**: ACTUAL = 897 (R7b confirmed `897 tests collected`). README's 897 is CORRECT. The UNDER-COUNT is in `f3-runtime-proof.md` (lines 6, 114, 119: "753"), `d5-runtime-wiring.md` (lines 5, 110, 140: "753"), `local-tests.md` (line 119: "753"). Fix = update those three files 753→897. Do NOT touch README's 897.
- **F20**: `docs/setup-evidence/P22/implementation/final/p22-final-implementation-report.md:65` (Browser "OK (local)") → add note "⚠️ Browser status updated to CONFIG_MISSING on 2026-06-28 — 3 MCP tools (search/fetch/browser-CDP) need instance shims. See production-activation/final/p22-production-status.md for current status."
- **F31**: `docs/setup-evidence/P22/production-activation/runtime/p22-p19-p20-regression-proof.md` — add caveat near line 16/62: "⚠️ Soak caveat: longest continuous observation window is ~5 min post-restart (23:16:36 WIB), NOT a 6-hour soak. NRestarts=0 is valid but measures post-restart stability only (counter resets on restart). A proper 6-hour soak should be conducted post-fix to verify long-term stability."
- **Required Commands**: `grep -rn "weather" docs/setup-evidence/P22-brutal-audit-handoff.md` → 0; `grep "definition/planning phase only" docs/setup-evidence/P22/README.md` → 0; `grep "753" docs/setup-evidence/P22/full-completion/verification/f3-runtime-proof.md docs/setup-evidence/P22/full-completion/verification/d5-runtime-wiring.md docs/setup-evidence/P22/full-completion/verification/local-tests.md` → 0 after fix; `ls docs/setup-evidence/P22/full-completion/verification/c10*` → exists
- **Hard Rejection**: falsifying verdicts; deleting original audit files; claiming FULL-COMPLETION; fake C10 file (must be genuine); touching README's correct 897

---

## 4. Auditor Matrix

After each batch's parent verification, spawn an auditor sub-agent. Auditor writes `docs/setup-evidence/P22/audits/brutal-2026-06-28/fix-verification/FXX.md`.

| Batch | Findings | Auditor report(s) |
|---|---|---|
| B1 | F01, F26, F27 | F01.md, F26.md, F27.md |
| B2 | F02, F05, F07, F28 | F02.md, F05.md, F07.md, F28.md |
| B3 | F03, F12 | F03.md, F12.md |
| B4 | F21, F22, F24, F25, F29, F32 | F21.md, F22.md, F24.md, F25.md, F29.md, F32.md |
| B5 | F04, F11 | F04.md, F11.md |
| B6 | F08, F09 | F08.md, F09.md |
| B7 | F23 | F23.md |
| B8 | F13 | F13.md |
| B9 | F30 | F30.md |
| B10 | F10 | F10.md |
| B11 | F06, F14, F15, F16, F17, F18, F19, F20, F31 | one per finding |

Auditors verify: scaffold criteria all pass, no forbidden patterns, tests green, no regressions, no type suppression, no bare excepts, no secret leaks, evidence honest.

---

## 5. Rollback Plan

- All changes on `main` working tree (no commit unless Faiz asks).
- Per-batch: if a batch regresses tests, `git checkout -- <files>` for that batch's files and re-delegate with corrected prompt via `task_id`.
- Migration F13: `alembic downgrade -1` if applied (but won't apply locally — just file exists).
- No destructive ops without explicit approval.

---

## 6. Execution Checklist

- [x] Research wave (R1–R6 done; R7b in flight)
- [x] Planner gate (this file)
- [x] Collision scan (§2)
- [x] Per-step scaffolds (§3)
- [ ] Wave 1: B1–B8, B10 (9 parallel agents)
- [ ] Wave 2: B9 (after B2), B11 (after R7b)
- [ ] Parent verification per batch (scaffold commands re-run by parent)
- [ ] Auditor wave (parallel per fix)
- [ ] Fix auditor findings via task_id
- [ ] Parent final verification (full pytest + lsp + grep gates)
- [ ] Write fix-verification/summary.md
- [ ] Update PROGRESS.md

---

## 7. Caveats

- **F05 is the highest-risk fix**: wiring `IntegrationAuditWriter` needs a DB session factory. In CI/dev without DB, the file fallback MUST engage without crashing startup. Implementer must test both paths (DB available + DB unavailable).
- **F23 caller-impact**: keeping sync signatures is mandatory; changing them would ripple to router.py + routes.py + smoke_test. The `threading.Lock`-for-readers approach avoids this.
- **F04 test updates**: existing tests expecting L1 for unknown actions MUST be updated to L2 — this is NOT deleting failing tests, it's updating expectations to match the new (correct) behavior.
- **F25/F29/F32 are OBSERVATIONS**: fixes are comments/config, not behavior changes. Low risk.
- **B2 folds F07 into the runtime/main.py owner** to avoid main.py collision — F07 is HIGH but its middleware addition is sequenced after F05's lifespan edit.
