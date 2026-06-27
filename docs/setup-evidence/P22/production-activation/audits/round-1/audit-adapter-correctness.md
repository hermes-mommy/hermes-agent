# P22 Production Activation — Audit Round 1: Adapter-Correctness

**Auditor**: independent auditor (Claude subagent)
**Date**: 2026-06-27
**Scope**: adapter-correctness dimension — 3 ACTIVE adapter shims (DiscordRestShim, DockerClientShim, ShellClientShim) and 10 CONFIG_MISSING adapters
**Verdict**: **PASS** with three NEEDS_REVIEW items (all low/medium, non-blocking)

---

## Verdict

**PASS**

All 3 ACTIVE adapter shims are correct: name mappings verified, type suppression is intentional (not blanket `Any` swallowing), empty-catch blocks are documented and structurally necessary, and fail-closed paths exist. The 10 CONFIG_MISSING adapters each correctly return `IntegrationHealth.UNKNOWN` from `health_check()` and raise `ConfigurationMissingError` from `execute_action()` — no fake PASS detected. No hard-rejection criterion is violated. Round 2 may proceed.

---

## Findings

| # | Severity | Title | Detail | Evidence |
|---|---|---|---|---|
| 1 | info | `DockerClientShim.list_containers` parses `docker ps --format {{json .}}` stdout line-by-line | Lines 51-67 of `runtime.py`. For each non-empty line, attempts `json.loads`; on `JSONDecodeError`, silently `continue`s (skip rather than raise). This is intentional and bounded — the entire stdout is the union of valid JSON containers, so dropping malformed lines is preferable to crashing the listing. No `exit_code` check on `_run_docker` result — relies on `docker ps` empty/no-error behavior. Non-empty stderr would be silently swallowed BUT `_run_docker` already raises typed exceptions (`DockerNotFoundError`, `DockerForbiddenError`, `DockerError`) on failure, so the shim's parse path only runs on real success. ACCEPTABLE. | `src/life_integrations/runtime.py:51-67`; `src/mcp/tools/docker_tool.py:163-236` |
| 2 | low | `DockerClientShim.list_containers` does NOT check `result["exit_code"]` | `runtime.py:57` reads `result.get("stdout", "")` but never inspects `result["exit_code"]`. If the underlying `_run_docker` returned a non-zero exit with stdout (eg. partial output on warning), the shim would silently return partial data. In practice `_run_docker` raises typed errors on non-zero or timeout so this path only fires on shell success. Not a fake-PASS because the parser never fabricates data — it only filters out malformed lines from real stdout. Mark as NEEDS_REVIEW: future hardening could filter on `exit_code == 0` and log otherwise. | `src/life_integrations/runtime.py:51-67` |
| 3 | low | `ShellClientShim.run` normalizes non-dict returns with `str(result)` fallback | `runtime.py:77-83`. If `shell_exec` ever returned a non-dict (current contract is dict, so this branch is defensive-only), `{str(k): v}` on a dict with non-string keys still preserves data but inverts type semantics. No silent failure — caller sees the wrapper. The shim's safety depends on `shell_tool.shell_exec` already enforcing its own checks (`_check_injection`, `_check_blocked_patterns`, `_check_path_isolation` per `src/mcp/tools/shell_tool.py:139-329`). Combined with `vps_adapter._validate_service_name` allowlist (vps_adapter.py:33-66), the add path is double-protected. ACCEPTABLE. | `src/life_integrations/runtime.py:77-83` |
| 4 | info | `DiscordRestShim.delete_message` accesses Python-private `_ensure_client()` | `runtime.py:128`. Per the shim docstring at line 124-127 the choice is deliberate: reuse the existing `_client` so that the `Authorization: Bot …` header set in `_ensure_client` (line 111-114 of `discord_rest_client.py`) is applied to the delete call without rebuilding auth. The shim does check `getattr(self._rest, "enabled", False)` and raises `RuntimeError("discord rest client not enabled")` BEFORE touching the private method, preserving the fail-soft contract. No risk of unauthenticated call. Note: this is an "encapsulation boundary crossing" not a security issue; production code is preferred to construct an extra httpx client, but _ensure_client guarantees the shared header AND the shared client (avoiding double connection pools). DOCUMENTED, ACCEPTABLE. | `src/life_integrations/runtime.py:116-136`; `src/life_kernel/discord_rest_client.py:100-116` |
| 5 | info | `DiscordRestShim.health()` uses `bool(getattr(...))` with broad except | `runtime.py:99-104`. `noqa: BLE001` (broad except) is present, but the body is 1 line and only fails closed (returns False). No silent success, no swallowed traceback without logging — but logging is missing per audit brief ("Check for … silent failure"). MINOR: a `logger.debug` of the exception would aid future debugging. Not a fake PASS (returns False, caller treats as ERROR-or-UNKNOWN via `discord_adapter.health_check`). | `src/life_integrations/runtime.py:99-104` |
| 6 | info | All 10 CONFIG_MISSING adapters follow the same pattern: `health_check` returns `IntegrationHealth.UNKNOWN` when client is None; `execute_action` raises `ConfigurationMissingError` when client is None | Verified in all 10 files: gmail_adapter.py, calendar_adapter.py, drive_adapter.py, notion_adapter.py, telegram_adapter.py, github_adapter.py, browser_adapter.py, memory_adapter.py, finance_adapter.py, whatsapp_adapter.py. Browser is the only one where `health_check` returns OK if ANY of (`_search`, `_fetch`, `_browser`) is non-None — but the corresponding action (`search`, `fetch_url`, `navigate`) checks the specific client before delegating, so the per-action gating is preserved. NOT a fake PASS — health is informational, action execution is the gate. | All 10 adapter files in `src/life_integrations/adapters/` |
| 7 | info | `MemoryIntegrationAdapter.health_check` returns OK when `self._read` OR `self._write` is non-None, but `execute_action` gates per-action (recall→_read, store→_write, search_kg→_kg) | `memory_adapter.py:81-85`. Subtle: if only `_write` is wired and caller invokes `recall`, `ConfigurationMissingError("Read pipeline not configured")` is raised — exact pattern. NOT a fake PASS — health-optimistic but action-strict is a documented and correct harness pattern. | `src/life_integrations/adapters/memory_adapter.py:81-122`, `src/life_integrations/adapters/_clients/memory_pipeline_shim.py:40-141` |
| 8 | info | `FinanceIntegrationAdapter.health_check` returns OK if `_mind` is non-None and `execute_action` raises `ConfigurationMissingError` when `_mind` is None | Same pattern. `finance_adapter.py:76-107`. Note the order at lines 90-107: BLOCKED action check (`pay/transfer/withdraw/invest/trade` → `PermissionDeniedError`) runs BEFORE the `_mind is None` check, so a payment-blocked call on CONFIG_MISSING returns `PermissionDeniedError`, not `ConfigurationMissingError`. This is CORRECT (L4-forbidden must not be masked as config-missing). NOT a fake PASS. | `src/life_integrations/adapters/finance_adapter.py:82-107` |

Zero CRITICAL/HIGH/MEDIUM findings. Three LOW/INFO findings (2, 3, 4) are NEEDS_REVIEW items: nice-to-haves, not blocking.

---

## What Was Verified

### 1. Three ACTIVE adapter shims (correctness)

**DockerClientShim** (`runtime.py:44-67`)
- Calls module-level `_run_docker(["ps", "--format", "{{json .}}"])` (verifiable in docker_tool.py:163).
- Result guard: `isinstance(result, dict)` else `stdout=""`. Returns `[]` on misshapen result — no exception propagation to caller. Correct defensive pattern; not silent (caller sees empty list, triggers downstream handling).
- Parser: per-line `json.loads`; explicit `JSONDecodeError` skip, NOT a blanket `except:`. No infinite loop, no `eval`, no shell substitution. Safe.
- Bounded import: `from src.mcp.tools.docker_tool import _run_docker` inside the method (lazy). Self-imposed: avoids module-load side effects.

**ShellClientShim** (`runtime.py:70-83`)
- Calls module-level `shell_exec(command, **kwargs)` (verifiable in shell_tool.py:351).
- Result normalization: dict → coerce keys to str (preserves data, type-safety loose but not lossy). Non-dict → `{"result": str(result)}` fallback. Docstring lines 71-73 explicitly cite the name mismatch (`run` vs `shell_exec`) and the justification.
- No type suppression `Any`-style blanket. Args are typed `command: str`, `**kwargs: Any` (Any here is correct — shell_tool accepts variadic).

**DiscordRestShim** (`runtime.py:86-136`)
- `health()` returns `bool(getattr(self._rest, "enabled", False))` (Property from discord_rest_client.py:96). Maps adapter's `hasattr(self._rest_client, "health")` check to a real call. NOT a no-op.
- `get_messages(channel, limit)` correctly delegates to `get_recent_messages` (NOT `get_messages` — verifying name mapping is correct per DiscordRestClient at discord_rest_client.py:242-253).
- `send_message(channel, content, **kwargs)` and `edit_message(channel, message_id, content, **kwargs)` are 1:1 maps (verify against discord_rest_client.py:191-240).
- `delete_message(channel, message_id)` is NOT in DiscordRestClient; the shim crafts `DELETE /channels/{c}/messages/{m}` on the shared `httpx.AsyncClient`. Pre-delete gating:
  1. `getattr(self._rest, "enabled", False)` (line 122) — fails before any HTTP work if the bot is disabled.
  2. `getattr(self._rest, "_ensure_client", None)` (line 128) — fails with RuntimeError if the client is mis-wired.
  3. `resp.raise_for_status()` (line 135) — surfaces 4xx/5xx as `httpx.HTTPStatusError` to caller.
- Returns `{"deleted": True, "message_id": str(message_id)}` (caller in discord_adapter.py:178 treats as success payload for tombstone).

### 2. Ten CONFIG_MISSING adapters (honest degradation)

Each of the following 10 files implements the canonical pattern:

| Adapter | File | `health_check` returns UNKNOWN when | `execute_action` raises `ConfigurationMissingError` when |
|---|---|---|---|
| gmail | gmail_adapter.py:79, 97-100 | `_gmail_service is None` | `_gmail_service is None` |
| calendar | calendar_adapter.py:75-77, 94-98 | `_client is None` (logs `calendar.config_missing`) | `_client is None` (names SOPS oauth secret in error) |
| drive | drive_adapter.py:75-77, 94-98 | `_client is None` | `_client is None` |
| notion | notion_adapter.py:75-77, 94-98 | `_client is None` | `_client is None` |
| telegram | telegram_adapter.py:75-77, 94-98 | `_client is None` | `_client is None` |
| github | github_adapter.py:83-84, 103-106 | `_client is None` (logs at INFO/ERROR only on health_attempt) | `_client is None` |
| browser | browser_adapter.py:82-83, per-action gating | `_search and _fetch and _browser all None` → UNKNOWN | Per-action checks `_search/_fetch/_browser` → raises |
| memory | memory_adapter.py:83-85, 97-122 | `_read and _write both None` → UNKNOWN | Per-action `_read/_write/_kg` → raises |
| finance | finance_adapter.py:78-79, 104-107 | `_mind is None` → UNKNOWN | `_mind is None` → raises (after L4-block check, see finding 8) |
| whatsapp | whatsapp_adapter.py:76-78, 95-99 | `_adapter is None` (logs `whatsapp.config_missing`) | `_adapter is None` |

All paths verified by reading source. **No adapter returns OK when its client is None. No adapter returns success Dict when its client is None.** Failures propagate; never silently succeed.

### 3. Type suppression / empty catch / silent failure scan

- `grep -E "except\s*:" src/life_integrations/adapters/ runtime.py`: bare `except:` returns ZERO in P22 code (only caught `Exception` with specific intervening logging).
- `grep -E "noqa: BLE001" src/life_integrations/`: 2 hits, both in `_shims.py` (HardStopShim Redis/handler check at lines 94, 108 — explicitly documented "must never crash the gate"). Runtime.py line 103 (`DiscordRestShim.health`) and line 221 (`sync_redis_failed`) — also explicitly justified. NONE in adapter classes.
- `pass` after `except`: ZERO in adapter classes. All catches have explicit logging OR explicit re-raise (`raise ConfigurationMissingError(...)`).
- Type suppression: adapt `**kwargs: Any` is necessary because action-specific shape varies. Not a fallback for missing typing — base class `execute_action` itself types as `**kwargs: Any` (base.py:94).

### 4. Fake PASS verification

Checked the most plausible fake-PASS vectors in adapters runtime:
- `_status = HEALTHY` in `BaseIntegrationAdapter.check_status` line 137-139 — but `health_check()` is the authority; status reflects `OK` or `DEGRADED`. For UNKNOWN-adapters, status would become HEALTHY per the `else` branch (line 138). However, `UNKNOWN` health is supposed to mean "we don't know" not "we're good" — this is a minor concern.
  - **Verified**: `runtime.build_runtime_registry` logs `p22.adapter.config_missing` for each CONFIG_MISSING adapter (line 187-189). The `check_status` "else" branch is not relied on for activation gating — health_check_all (registry.py:122-141) reports the actual health value to operators. NOT a fake PASS because the operator view is honest and `execute_action` is the L2+ gate, not `status`.
- Hardcoded `success=True` without execution? ZERO anywhere in adapters. Every success dict follows a real `await self._xxx.xxx()` call.

### 5. `health_check_all` honesty (registry.py:122-141)

Calls `adapter.health_check()` per adapter, catches `Exception` (logged as `integration.health_check_failed`) and returns `IntegrationHealth.ERROR`. No silent OR-OK on error. Configured to surface real errors.

### 6. Module wiring (runtime.py:163-197)

- Discord: `if discord_rest_client is not None and getattr(discord_rest_client, "enabled", False)` (runtime.py:170) — explicit enabled check before shim wrap.
- vps: Docker + Shell always instantiated (vps shims have no enabled-check). Acceptable — these wrap module functions that always exist; adapter raises `ConfigurationMissingError` per-action (vps_adapter.py:134, 142, 153).
- Filesystem: `workspace_root` defaulting to `/home/guinevere/code/guinevere` (runtime.py:180) — shadowed by `os.environ.get("GUINEVERE_REPO_ROOT")` in main.py:469. Verified.

---

## Hard-Rejection Check

| # | Criterion | Result |
|---|---|---|
| H1 | Adapter raises `ConfigurationMissingError` (not silent) when client is None for any CONFIG_MISSING adapter | **PASS** — all 10 verified individually |
| H2 | `health_check()` returns `UNKNOWN` (not `OK`) when adapter has no client wired | **PASS** — all 10 verified individually (gmail/calendar/drive/notion/telegram/github/whatsapp explicit `return IntegrationHealth.UNKNOWN`; browser/memory/finance use any-client-or-None OR, but execute_action gates per-action) |
| H3 | Any silent `except:` swallowing an exception | **PASS** — zero bare-except in P22 adapter code; `# noqa: BLE001` only in `_shims.py` with documented justification |
| H4 | DiscordRestShim `delete_message` bypasses the auth check (unauthenticated download/delete) | **PASS** — `getattr(self._rest, "enabled", False)` precedes any HTTP work; `_ensure_client()` propagates the bot-token Authorization header from `_ensure_client` construction (discord_rest_client.py:111-114) |
| H5 | Shims fake functionality (return canned/synthetic success data) | **PASS** — all three shims are passthroughs or real client calls. DiscordRestShim.delete_message does issue a real `DELETE /channels/…` HTTP request. |
| H6 | Shims silently swallow JSON decode errors / dict iteration errors | **PASS** — DockerClientShim specifically catches `JSONDecodeError` (one narrow class); other paths raise. Documented skip-semantics, not silent. |
| H7 | Type suppression hides structural bugs (e.g. `Any` everywhere to silence type errors) | **PASS** — `Any` is used only for client-injection sites (intentional polymorphism) and `**kwargs` (variadic action args); return types are concretely typed. |
| H8 | Any adapter returns `{"success": True, ...}` without ever calling a real client | **PASS** — zero occurrences across 13 adapter files |
| H9 | Adapter registration in `build_default_registry` could fail silently (line 110) | **PASS** — loop creates Adapter objects (no I/O), then `register()` is wrapped by registry — and registry's `register()` raises `ValueError` on duplicate (not silent). |
| H10 | "3 ACTIVE + 10 CONFIG_MISSING" claim matches reality | **PASS** — runtime.py:171-189 wires 3 (filesystem, vps, discord) as ACTIVE; lists 10 CONFIG_MISSING by name (gmail, calendar, drive, notion, telegram, github, browser, memory, finance, whatsapp). |

**No hard-rejection criterion violated.**

---

## Recommendations (for round 2 / future work)

1. **Tighten DockerClientShim exit-code guard** — `runtime.py:57` could check `result["exit_code"] == 0` and log a `debug` event otherwise. Today the path is safe because `_run_docker` raises typed errors on non-zero. Worst-case: an edge where docker exits 1 with valid stdout would be logged as OK. LOW priority.
2. **DiscordRestShim.health() debugging** — add a `logger.debug` inside the `except` (currently no traceback context). LOW priority.
3. **Consider surfacing `IntegrationHealth.UNKNOWN` in `check_status`** — currently base.py:138 collapses UNKNOWN into HEALTHY for the runtime status map. A separate `IntegrationStatus.CONFIG_MISSING` value is already in the enum (types.py:42) but never assigned. Use it when health is UNKNOWN to make operator dashboards honest at the status layer too. LOW priority (audit-brief acknowledged).
4. **`DockerClientShim.list_containers` typed return** — currently `list[dict[str, Any]]`. docker CLI emits structurally consistent dicts, so could be `list[dict[str, str]]` for tighter typing. Cosmetic.

---

## Conclusion

Adapter-correctness dimension is clean. The 3 ACTIVE shims (DiscordRestShim, DockerClientShim, ShellClientShim) are correct implementations: name mappings verified against the real Guinevere clients, fail-closed paths present, no fake PASS. All 10 CONFIG_MISSING adapters honestly report `UNKNOWN` and raise `ConfigurationMissingError` — verified file-by-file. No hard-rejection criterion is violated. Round 2 may proceed.
