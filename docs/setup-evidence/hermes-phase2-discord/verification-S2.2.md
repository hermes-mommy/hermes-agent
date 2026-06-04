# S2.2 Verification Report — Shadow Monitor + Comparator

**Date**: 2026-06-04
**Task**: Step S2.2 — Shadow Monitor + Comparator with systemd units
**Status**: ✅ DONE

---

## What Was Done

Created the shadow monitoring system: a standalone Python monitor script that reads `logs/shadow_comparisons.jsonl`, calculates parity metrics, enforces cost caps ($5.00), and alerts via Discord webhook on threshold violations. Accompanied by systemd service + timer units for automated 60s interval checks.

---

## Files Created

| File | Lines | Purpose |
|---|---|---|
| `src/discord/shadow_monitor.py` | 491 | Monitor + comparator script with ShadowMonitor class |
| `systemd/guinevere-shadow-monitor.service` | 34 | systemd oneshot service unit |
| `systemd/guinevere-shadow-monitor.timer` | 10 | systemd timer unit (60s OnUnitActiveSec) |

---

## Validation Results

### Python Syntax Check

```bash
python -c "import py_compile; py_compile.compile('src/discord/shadow_monitor.py', doraise=True)"
```
→ **PASS** (exit 0, SYNTAX OK)

### Standalone Run — `--check` (No Log File)

```bash
python -m src.discord.shadow_monitor --check
```
→ **PASS** (exit 0) — gracefully handles missing comparison log, reports 0 queries, all thresholds OK.

### Standalone Run — `--parity-check` (Insufficient Data)

```bash
python -m src.discord.shadow_monitor --parity-check --min-queries 100 --report
```
→ **PASS** (exit 1 as expected) — correctly reports insufficient data (0 < 100 min queries).

### LSP Diagnostics

```bash
lsp_diagnostics(src/discord/shadow_monitor.py, severity=error)
```
→ **PASS** — zero errors.

---

## Anti-Pattern Checks

| Check | Pattern | Result |
|---|---|---|
| No type suppression | `as any`, `@ts-ignore`, `# type: ignore` | ✅ 0 matches |
| No bare except | `except:` (without class) | ✅ 0 matches |
| No bot.py imports | `import bot`, `from bot`, `from conversational_handler` | ✅ 0 matches |
| No hardcoded tokens | `DISCORD_APPROVAL_WEBHOOK` from env only | ✅ |

---

## Threshold Verification (grep checks)

### Timer Interval

```
> grep "OnUnitActiveSec" systemd/guinevere-shadow-monitor.timer
OnUnitActiveSec=60
```
→ **PASS** — 60s interval confirmed.

### Cost Cap ($5.00)

```
> grep "cost_cap\|5\.0\|5\.00" src/discord/shadow_monitor.py
COST_CAP_USD = 5.0
self.cost_cap_usd: float = COST_CAP_USD
"memory_deviation_pct": 5.0
"error_rate_pct": 5.0
if cost > self.cost_cap_usd:
... (11 total matches)
```
→ **PASS** — $5.00 cost cap defined, checked, and reported.

### Safety Parity 100%

```
> grep "100\.0" src/discord/shadow_monitor.py
"safety_parity_pct": 100.0       # MUST be 100%
"command_match_pct": 100.0        # MUST be 100%
"safety_parity_pct": 100.0,
"command_match_pct": 100.0,
... (10 total matches)
```
→ **PASS** — safety_parity_pct and command_match_pct both at 100%.

---

## Architecture Compliance

### ShadowMonitor Class Structure

| Method | Purpose | Status |
|---|---|---|
| `read_comparisons(since_minutes)` | Parse JSONL, filter by time window, skip malformed lines | ✅ |
| `calculate_metrics(comparisons)` | Compute safety, command, memory, error rate, cost, uptime | ✅ |
| `check_thresholds(metrics)` | Compare against thresholds, return violation strings | ✅ |
| `send_alert(violations, metrics)` | Discord webhook with embed fields | ✅ |
| `run_check()` | Single check cycle → exit 0/1 | ✅ |
| `parity_check(min_queries, output_path)` | Comprehensive check with optional markdown report | ✅ |

### CLI Arguments

| Flag | Purpose |
|---|---|
| `--check` | Single cycle, reads last 60 min |
| `--parity-check` | All-time comprehensive check |
| `--min-queries N` | Minimum queries for parity (default 100) |
| `--report` | Generate markdown report |
| `--output PATH` | Report output path |
| `--log PATH` | Custom comparison log path |

### systemd Units

- **Service**: `Type=oneshot`, `After=guinevere-discord.service`, `PartOf=guinevere.slice`
- **Timer**: `OnBootSec=60`, `OnUnitActiveSec=60`, `AccuracySec=5`, `Persistent=true`
- Security: `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`
- Resource: `MemoryHigh=128M`, `MemoryMax=256M`, `CPUQuota=50%`

---

## Boundary Compliance

| Boundary | Status |
|---|---|
| No modification of bot.py | ✅ — standalone, zero imports from bot.py |
| No modification of conversational_handler.py | ✅ — zero imports |
| No hardcoded secrets | ✅ — DISCORD_APPROVAL_WEBHOOK from env only |
| No production bot behavior change | ✅ — monitor is independent |
| No persona drift | ✅ — N/A (no persona code affected) |
| No consent violation | ✅ — N/A (no user data handling) |

---

## Design Decisions & Caveats

1. **Graceful missing-log handling**: When `logs/shadow_comparisons.jsonl` doesn't exist, returns empty with warning log — no crash.
2. **JSONL robustness**: Malformed lines and missing timestamps are skipped with WARNING-level logs.
3. **Webhook error handling**: HTTPError, OSError, and ValueError are caught separately with structured logging.
4. **Cost tracking**: `total_cost_usd` is computed from per-entry `cost_usd` fields, enforced against `COST_CAP_USD = 5.0`.
5. **Uptime**: Computed as time delta between first and last entry timestamps.
6. **systemd timer uses `Persistent=true`**: Ensures missed ticks (e.g., during maintenance) are caught up.
7. **Service dependencies**: Waits for `guinevere-discord.service` before starting, ensuring bot.py is up before monitor runs.

---

## Auditor Gate

Pre-auditor wave pending (S2.2). No auditor assigned yet — will be triggered by parent after this verification report.

---

## Acceptance Criteria Mapping

| Criterion | Met? |
|---|---|
| Standalone monitor script with ShadowMonitor class | ✅ |
| Cost cap ($5) enforced with alert | ✅ |
| Safety parity 100% threshold | ✅ |
| Command match 100% threshold | ✅ |
| Memory deviation ≤5% threshold | ✅ |
| Error rate ≤5% threshold | ✅ |
| Discord webhook alerts on violation | ✅ |
| systemd service + timer units | ✅ |
| 60s timer interval | ✅ |
| Full type annotations | ✅ |
| No bot.py imports | ✅ |
| No bare except without logging | ✅ |
| No type suppression | ✅ |
| No hardcoded secrets | ✅ |

---

## Footer

- **Task**: S2.2 — Shadow Monitor + Comparator
- **Batch**: Phase 2 Discord Migration
- **Plan**: `docs/setup-evidence/hermes-phase2-discord/batch-plan-phase-2-discord.md` (lines 577–613)
- **Evidence Root**: `docs/setup-evidence/hermes-phase2-discord/`