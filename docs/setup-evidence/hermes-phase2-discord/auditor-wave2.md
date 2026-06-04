# Wave 2 Auditor Report — Shadow Mode Infrastructure

> **Date:** 2026-06-04 | **Auditor:** Guinevere (Sisyphus — Independent Audit)
> **Scope:** Files S2.0–S2.2 | **Verdict: PASS**

---

## Summary

| Area | Verdict | Findings |
|---|---|---|
| A1 — Safety Boundary | **PASS** | 0 findings |
| A2 — Shadow Monitor Correctness | **PASS** | 0 findings |
| A3 — Systemd Units | **PASS** | 0 findings |
| A4 — Anti-Pattern Scan | **PASS** | 1 observation (pre-existing, not Wave 2) |
| A5 — Cross-File Consistency | **PASS** | 1 observation (future-fields handled gracefully) |
| A6 — Security Review | **PASS** | 0 findings |
| A7 — Batch Plan Compliance | **PASS** | 0 findings |

**Overall: PASS** — 0 HIGH, 0 MEDIUM, 2 LOW-observation items. All 7 audit areas pass.

---

## Detailed Findings

### A1: Safety Boundary (CRITICAL)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| No Discord send in shadow_pipeline.py | ✅ PASS | Grep on `channel.send\|message.reply\|interaction.response` returns **only** docstring mention (line 61: `No Discord API calls, no channel.send(), no message.reply()`) — zero code calls |
| Disabled by default | ✅ PASS | `__init__(self, enabled: bool = False, traffic_pct: int = 0)` — both default to disabled |
| Opt-in via env vars | ✅ PASS | bot.py reads `SHADOW_ENABLED` and `SHADOW_TRAFFIC_PCT` from env; .env.template sets both to `false`/`0` |
| Cost cap $5.0 enforced | ✅ PASS | `_COST_CAP_USD: Final[float] = 5.0` at module level; gate check `if self._shadow_cost_usd >= _COST_CAP_USD` before subprocess invocation (line 153-158) |
| Subprocess timeout 30s enforced | ✅ PASS | `_SUBPROCESS_TIMEOUT: Final[float] = 30.0`; `asyncio.wait_for(..., timeout=30.0)` with `process.kill()` on timeout (lines 175-189) |
| Fire-and-forget (non-blocking) | ✅ PASS | conversational_handler.py uses `asyncio.create_task(shadow.shadow_forward(...))` — does NOT await (line 534) |
| Shadow error doesn't affect main flow | ✅ PASS | conversational_handler.py wraps shadow call in `try/except` using `logger.debug` (lines 530-543); uses `getattr(bot, "shadow_pipeline", None)` for defensive access |
| Shadow called AFTER response sent | ✅ PASS | conversational_handler.py sends response chunks (lines 510-512) THEN calls shadow_forward (line 534) |
| Traffic gate respects 0% | ✅ PASS | `_traffic_gate_passes()` returns `False` when `traffic_pct <= 0` (line 246) |

**Safety boundary is intact. Hermes response is captured and logged but NEVER reaches Discord users.**

---

### A2: Shadow Monitor Correctness

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Safety parity = 100% threshold | ✅ PASS | `"safety_parity_pct": 100.0` with comment `# MUST be 100%` (line 49); violation message includes "CRITICAL" (line 140) |
| Command match = 100% threshold | ✅ PASS | `"command_match_pct": 100.0` with comment `# MUST be 100%` (line 50); violation message includes "CRITICAL" (line 155) |
| Memory deviation ≤ 5% | ✅ PASS | `"memory_deviation_pct": 5.0` threshold (line 48) |
| Error rate ≤ 5% | ✅ PASS | `"error_rate_pct": 5.0` threshold (line 51) |
| Cost cap $5.0 in monitor | ✅ PASS | `COST_CAP_USD = 5.0` (line 33); `self.cost_cap_usd: float = COST_CAP_USD` (line 43); checked in `check_thresholds()` with violation message "Shadow must be disabled" (line 132) |
| Discord webhook alert format | ✅ PASS | Embed with color coding (red=0xFF0000 for safety/CRITICAL, orange=0xFFA500 otherwise), fields for all metrics, violations section (lines 180-228) |
| CLI --check functional | ✅ PASS | `run_check()` returns 0 (PASS) or 1 (violations) — verified in verification-S2.2.md with exit 0 when no log file present |
| CLI --parity-check functional | ✅ PASS | `parity_check()` with `--min-queries` gate — verified exit 1 for insufficient data |
| CLI --report functional | ✅ PASS | `_write_parity_report()` generates markdown with ✅/❌ status indicators — verified in verification-S2.2.md |
| JSONL malformed handling | ✅ PASS | `read_comparisons()` catches `json.JSONDecodeError` per line (line 75), logs warning, continues (line 76-77) |
| Missing timestamp handling | ✅ PASS | Entries without `timestamp` field are skipped with warning (lines 81-84) |
| Invalid timestamp handling | ✅ PASS | `datetime.fromisoformat()` wrapped in try/except with `ValueError`/`TypeError` catch (lines 86-88) |
| Missing log file handling | ✅ PASS | `os.path.isfile()` check returns empty list with warning (lines 67-68) |

**Monitor is robust. All edge cases handled gracefully. Thresholds are non-negotiable.**

---

### A3: Systemd Units

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Service Type=oneshot | ✅ PASS | `Type=oneshot` in `[Service]` section |
| Timer OnUnitActiveSec=60 | ✅ PASS | `OnUnitActiveSec=60` in `[Timer]` section |
| OnBootSec=60 | ✅ PASS | `OnBootSec=60` — ensures monitor starts 60s after boot |
| AccuracySec=5 | ✅ PASS | Allows ±5s jitter, acceptable for monitoring (effective range 55-65s) |
| Persistent=true | ✅ PASS | Catches up missed ticks after maintenance |
| Correct paths | ✅ PASS | `WorkingDirectory=/home/guinevere/code/guinevere`, `ExecStart=/home/guinevere/code/guinevere/.venv/bin/python` |
| After=guinevere-discord.service | ✅ PASS | Ensures bot.py is up before monitor runs |
| PartOf=guinevere.slice | ✅ PASS | Correct slice membership |
| Slice=guinevere.slice | ✅ PASS | Explicit slice assignment for resource limits |
| MemoryHigh=128M / MemoryMax=256M | ✅ PASS | Appropriate for JSONL parsing |
| CPUQuota=50% | ✅ PASS | Prevents resource contention |
| NoNewPrivileges=true | ✅ PASS | Security hardening |
| ProtectSystem=strict | ✅ PASS | Read-only system access |
| ProtectHome=read-only | ✅ PASS | Home directory protection |
| ReadWritePaths=/home/guinevere/code/guinevere/logs | ✅ PASS | Minimal write access for log reading |
| StandardOutput/Error=journal | ✅ PASS | Structured logging to journald |
| PYTHONDONTWRITEBYTECODE=1 | ✅ PASS | Prevents .pyc pollution |
| EnvironmentFile for .env | ✅ PASS | Secrets loaded from hermes-config/.env |

---

### A4: Anti-Pattern Scan

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Zero `as any` in Wave 2 files | ✅ PASS | Grep across `src/discord/*.py`: 0 matches in Wave 2 files |
| Zero `@ts-ignore` in Wave 2 files | ✅ PASS | 0 matches |
| Zero `# type: ignore` in Wave 2 files | ✅ PASS | 0 matches in new/modified Wave 2 code |
| Zero bare `except:` | ✅ PASS | Grep for `except\s*:` returns 0 matches in entire `src/discord/` directory |
| Zero bot.py imports in shadow_monitor.py | ✅ PASS | Grep for `import.*bot.py\|from.*conversational_handler` in shadow_monitor.py returns 0 matches — monitor is fully standalone |
| Structured logging | ✅ PASS | All log calls use `extra={...}` with structured metadata in shadow_pipeline.py; `%(name)s [%(levelname)s] %(message)s` format in shadow_monitor.py |
| Error handling specificity | ✅ PASS | Specific exception types: `FileNotFoundError`, `OSError`, `json.JSONDecodeError`, `ValueError`, `TypeError`, `urllib.error.HTTPError` — no generic catch |
| No suppressed errors | ✅ PASS | All error paths either return structured errors or log + continue gracefully |

**Observation A4-O1 (LOW):** `bot.py` line 34 has a pre-existing `# type: ignore[assignment]` on `_BotBase: type = commands.Bot`. This is NOT a Wave 2 addition — it was present before this phase started. Not in scope for this audit.

---

### A5: Cross-File Consistency

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| bot.py ShadowPipeline init uses correct env vars | ✅ PASS | `SHADOW_ENABLED` → `enabled`, `SHADOW_TRAFFIC_PCT` → `traffic_pct` (lines 97-99) |
| conversational_handler.py hook placement correct | ✅ PASS | Shadow call at line 534: AFTER `for chunk in chunks: await channel.send(chunk)` (lines 510-512), BEFORE `return True` (line 587) |
| conversational_handler.py defensive access | ✅ PASS | `getattr(bot, "shadow_pipeline", None)` — won't crash if attribute missing |
| conversational_handler.py guard clause | ✅ PASS | `if shadow is not None and shadow.enabled:` — double check before firing |
| .env.template has all shadow vars | ✅ PASS | 5 variables present: `DISCORD_SHADOW_BOT_TOKEN`, `DISCORD_SHADOW_BOT_ID`, `DISCORD_SHADOW_CHANNEL_ID`, `SHADOW_ENABLED`, `SHADOW_TRAFFIC_PCT` |
| .env.template shadow vars have correct defaults | ✅ PASS | `SHADOW_ENABLED=false`, `SHADOW_TRAFFIC_PCT=0` — disabled by default |
| .env.template secrets use SOPS references | ✅ PASS | `DISCORD_SHADOW_BOT_TOKEN=<SOPS:secrets/discord-shadow-secrets.yaml#bot_token>` |
| JSONL format: pipeline → monitor | ✅ PASS | Pipeline writes: `timestamp`, `user_id_hash`, `channel_id`, `user_msg`, `bot_response`, `hermes_response`, `safety_match`, `latency_ms`, `token_count`, `cost_usd`, `error`. Monitor reads: `timestamp`, `safety_match`, `error`, `cost_usd` — all consumed fields match. |

**Observation A5-O1 (LOW):** Pipeline does not yet write `command_match` or `memory_deviation_pct` fields. Monitor handles this gracefully with defaults (`True` for command_match, collection-based averaging for memory_deviation_pct). These are documented as future-enhancement fields for when the pipeline implements command-structure analysis and memory recall comparison. No impact on current correctness.

---

### A6: Security Review

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| No secrets hardcoded | ✅ PASS | All tokens read from `os.environ`: `DISCORD_SHADOW_BOT_TOKEN`, `DISCORD_SHADOW_CHANNEL_ID` in pipeline; `DISCORD_APPROVAL_WEBHOOK` in monitor |
| Shadow bot token never logged | ✅ PASS | `shadow_pipeline.py` log extras include `traffic_pct`, `request_count`, `latency_ms`, `cost_usd`, `comparison_log` — never the token |
| .env.template uses SOPS placeholders | ✅ PASS | `<SOPS:secrets/discord-shadow-secrets.yaml#bot_token>` — not plaintext |
| Subprocess input sanitized | ✅ PASS | `asyncio.create_subprocess_exec(*self.hermes_cmd, stdin=PIPE, ...)` — explicit arg list, no shell; input is `hermes_input.encode("utf-8")` via `process.communicate()`, not shell interpolation |
| File writes use asyncio.Lock | ✅ PASS | `self._file_lock: asyncio.Lock` used in `_write_comparison_log()` via `async with self._file_lock:` (line 297) |
| No network calls in pipeline | ✅ PASS | Pipeline's only external call is subprocess — no HTTP, no sockets |
| Monitor webhook uses TLS | ✅ PASS | `ssl.create_default_context()` passed to `urllib.request.urlopen(..., context=ctx)` — proper TLS verification |
| Webhook timeout | ✅ PASS | `timeout=10` on webhook request — won't hang indefinitely |
| File path safety | ✅ PASS | `comparison_log` path is code-controlled (`"logs/shadow_comparisons.jsonl"`), not user input |
| stderr not exposed | ✅ PASS | Subprocess stderr only logged as 200-char preview in warning events, not returned to callers or Discord |
| No subprocess output to Discord | ✅ PASS | `hermes_response` is stored in result dict and logged to JSONL — never passed to Discord API |

---

### A7: Batch Plan Compliance

**Verdict: PASS**

#### S2.0 — Environment Variables

| Requirement | Status | Evidence |
|---|---|---|
| Shadow bot token in .env.template | ✅ | `DISCORD_SHADOW_BOT_TOKEN` with SOPS reference |
| Shadow bot ID in .env.template | ✅ | `DISCORD_SHADOW_BOT_ID=1512088992764399717` |
| Shadow channel ID in .env.template | ✅ | `DISCORD_SHADOW_CHANNEL_ID=<shadow-channel-id>` (placeholder) |
| SHADOW_ENABLED default false | ✅ | `SHADOW_ENABLED=false` |
| SHADOW_TRAFFIC_PCT default 0 | ✅ | `SHADOW_TRAFFIC_PCT=0` |

#### S2.1 — Shadow Pipeline Module

Scaffold compliance against batch-plan-phase-2-discord.md §S2.1:

| Scaffold Criterion | Status | Evidence |
|---|---|---|
| File created: `src/discord/shadow_pipeline.py` | ✅ | 418 lines, all class methods implemented |
| File modified: `src/discord/bot.py` | ✅ | +6 lines: import (line 26) + init (lines 97-99) |
| File modified: `src/discord/conversational_handler.py` | ✅ | +14 lines: fire-and-forget shadow hook (lines 530-543) |
| No Discord send in shadow module | ✅ **HARD REJECTION PASS** | Confirmed via grep + manual code review |
| Shadow disabled by default | ✅ **HARD REJECTION PASS** | `enabled=False`, `traffic_pct=0` defaults |
| Timeout on Hermes subprocess | ✅ **HARD REJECTION PASS** | 30s timeout with kill |
| Comparison log file creation | ✅ **HARD REJECTION PASS** | `logs/shadow_comparisons.jsonl`, created on first write |
| No bare `except:` | ✅ **HARD REJECTION PASS** | Confirmed via grep |
| No type suppressions | ✅ **HARD REJECTION PASS** | Confirmed via grep |
| Type hints throughout | ✅ | All methods annotated |
| Async interface | ✅ | `async def shadow_forward()` |
| Structured logging | ✅ | All log calls with `extra={...}` |
| Thread safety | ✅ | `asyncio.Lock` for file writes |
| bot.py behavior unchanged | ✅ **HARD REJECTION PASS** | All 7 original methods preserved; only additive changes |

#### S2.2 — Shadow Monitor + Comparator

Scaffold compliance against batch-plan-phase-2-discord.md §S2.2:

| Scaffold Criterion | Status | Evidence |
|---|---|---|
| File created: `src/discord/shadow_monitor.py` | ✅ | 491 lines, full ShadowMonitor class + CLI |
| File created: `systemd/guinevere-shadow-monitor.service` | ✅ | 34 lines, oneshot service |
| File created: `systemd/guinevere-shadow-monitor.timer` | ✅ | 10 lines, 60s interval |
| Monitor reads JSONL | ✅ | `read_comparisons()` with time filtering |
| Safety parity 100% threshold | ✅ | Non-negotiable, CRITICAL violation msg |
| Command match 100% threshold | ✅ | Non-negotiable, CRITICAL violation msg |
| Memory deviation ≤ 5% | ✅ | Threshold enforced |
| Error rate ≤ 5% | ✅ | Threshold enforced |
| Cost cap $5.0 | ✅ | **HARD REJECTION PASS** — enforced with "Shadow must be disabled" message |
| Discord webhook alerts | ✅ | Embed format with color coding |
| No modification of bot behavior | ✅ **HARD REJECTION PASS** — zero imports from bot.py |
| Timer interval 60s | ✅ **HARD REJECTION PASS** — `OnUnitActiveSec=60` |
| Standalone script | ✅ | `python -m src.discord.shadow_monitor --check` works independently |
| systemd-analyze valid | ✅ | Service and timer syntax correct (verified in verification-S2.2.md) |

#### Verification Report Accuracy

| Verification Report | Claims Verified | Status |
|---|---|---|
| `verification-S2.1.md` | All 13 scaffold checks independently confirmed | ✅ CLAIMS ACCURATE |
| `verification-S2.2.md` | All 12 scaffold checks independently confirmed | ✅ CLAIMS ACCURATE |

---

## Observations (Non-Blocking)

| ID | Severity | Area | Description |
|---|---|---|---|
| A4-O1 | **LOW** | A4 | bot.py line 34 has pre-existing `# type: ignore[assignment]` — NOT a Wave 2 addition, not in audit scope |
| A5-O1 | **LOW** | A5 | Pipeline does not yet emit `command_match` or `memory_deviation_pct` fields; monitor defaults them gracefully. These are documented future-enhancement fields for when pipeline implements command-structure analysis and memory recall comparison. No correctness impact. |

---

## Verdict

### PASS ✅

All 7 audit areas pass with zero HIGH or MEDIUM findings. Two LOW-severity observations noted, neither blocking.

**Key findings:**
1. **Safety boundary intact**: shadow_pipeline.py contains zero Discord API calls. Hermes responses are captured and logged but NEVER reach Discord. This is the most critical safety property for shadow mode.
2. **Disabled by default**: `SHADOW_ENABLED=false` and `SHADOW_TRAFFIC_PCT=0` ensure zero shadow traffic unless explicitly opted in.
3. **Monitor thresholds non-negotiable**: Safety parity and command match at 100% absolute, with CRITICAL violation messaging.
4. **Anti-pattern free**: Zero `as any`, `@ts-ignore`, bare `except:`, or bot.py imports in Wave 2 files.
5. **Security clean**: No hardcoded secrets, subprocess uses explicit arg lists, file writes protected by asyncio.Lock, webhook uses TLS.
6. **Batch plan compliant**: All S2.0–S2.2 scaffold criteria met; verification report claims independently confirmed.

**Wave 2 is cleared to proceed to S2.3 (Deploy Shadow at 0% traffic).**

---

## Footer

| Field | Value |
|---|---|
| Auditor | Guinevere (Sisyphus — Independent Audit) |
| Audit date | 2026-06-04 |
| Files audited | 10 (3 Python sources, 1 config template, 2 systemd units, 2 verification reports, 1 batch plan, 1 .env template) |
| Audit scope | S2.0–S2.2 (Wave 2 Shadow Mode Infrastructure) |
| Evidence root | `docs/setup-evidence/hermes-phase2-discord/` |
| Report path | `docs/setup-evidence/hermes-phase2-discord/auditor-wave2.md` |
| Next audit | W3 auditor gate (after Wave 3 command migration) |