# AUDIT REPORT — Technical Accuracy (Auditor 3 of 4)

> **Document**: `audit-technical.md`
> **Date**: 2026-06-04
> **Auditor**: Guinevere (Auditor 3 — Technical Accuracy)
> **Subject**: Hermes Migration Plan — batch-plan-migration.md + 8 phase files
> **Verdict**: **FAIL** — BLOCKING: wrong service names

---

## Checklist Results

| # | Check | Verdict | Evidence / Notes |
|---|---|---|---|
| 1 | Service names match systemd files | **FAIL** | See §Findings below (BLOCKING) |
| 2 | Port numbers correct | **PASS** | All 8 ports verified against source files |
| 3 | File paths correct | **PASS** | All paths match repo structure |
| 4 | Hermes CLI commands valid | **PASS** | Commands match ADR-035 §Context (7 CLI tools documented) |
| 5 | Systemd commands correct | **PASS** | Standard `systemctl` syntax verified |
| 6 | SOPS commands correct | **PASS** | `sops exec-env` is valid SOPS subcommand |
| 7 | pytest commands correct | **PASS** | `-v` flag and test paths consistent |
| 8 | Hook names correct | **PASS** | All 7 match ADR-035 line 110 |
| 9 | Code reduction numbers match | **PASS** | 31.2% / 44.2% / 8,057 / 25,796 all consistent |
| 10 | 35 slash commands | **PASS** | Referenced 20+ times across all files |
| 11 | 113 Python files, 25,796 lines | **PASS** | Batch plan §1.4 + ADR-035 line 92 |
| 12 | Redis DB assignments | **PASS** | DB2→consent, DB5→surveillance match plan usage |
| 13 | Commands copy-paste ready | **PASS** | No "configure appropriately" or TODO placeholders |
| 14 | No type-safety suppression | **PASS** | No `as any` / `@ts-ignore` in code examples |
| 15 | Timeline 35-50 days | **PASS** | Batch plan line 63; Phase 7 line 559 |

**Score: 14/15 PASS — but verdict is FAIL due to BLOCKING item #1**

---

## Detailed Findings

### §1 — Service Names (Item 1): FAIL — BLOCKING

#### 1.1: `guinevere-bot` (WRONG) vs `guinevere-discord` (CORRECT)

**Actual systemd files in `systemd/` directory:**

| File | Service Name |
|---|---|
| `systemd/guinevere-discord.service` | `guinevere-discord` |
| `systemd/guinevere-loops.service` | `guinevere-loops` |
| `systemd/guinevere-mcp.service` | `guinevere-mcp` |
| `systemd/guinevere-monitoring.service` | `guinevere-monitoring` |
| `systemd/guinevere-obscura.service` | `guinevere-obscura` |
| `systemd/guinevere-scheduler.service` | `guinevere-scheduler` |
| `systemd/guinevere-surveillance.service` | `guinevere-surveillance` |

**No `guinevere-bot.service` file exists.**

**`phase-2-discord.md` uses `guinevere-bot` 15 times** — this is an incorrect service name. The correct name is `guinevere-discord`. Every one of these commands would fail at runtime:

| Line | Wrong Command | Should Be |
|---|---|---|
| 13 | `sudo systemctl start guinevere-bot` | `sudo systemctl start guinevere-discord` |
| 215 | `sudo systemctl is-active guinevere-bot` | `sudo systemctl is-active guinevere-discord` |
| 266 | `sudo systemctl stop guinevere-bot` | `sudo systemctl stop guinevere-discord` |
| 268 | `sudo systemctl is-active --quiet guinevere-bot` | `sudo systemctl is-active --quiet guinevere-discord` |
| 281 | `sudo systemctl start guinevere-bot` | `sudo systemctl start guinevere-discord` |
| 284 | `sudo systemctl disable guinevere-bot` | `sudo systemctl disable guinevere-discord` |
| 291 | `sudo systemctl start guinevere-bot` | `sudo systemctl start guinevere-discord` |
| 294 | `sudo systemctl enable guinevere-bot && sudo systemctl start guinevere-bot` | `sudo systemctl enable guinevere-discord && sudo systemctl start guinevere-discord` |
| 385 | `guinevere-bot` | `guinevere-discord` |
| 392 | `sudo systemctl stop guinevere-bot` | `sudo systemctl stop guinevere-discord` |
| 394 | `sudo systemctl disable guinevere-bot` | `sudo systemctl disable guinevere-discord` |
| 419 | `sudo systemctl status guinevere-bot` | `sudo systemctl status guinevere-discord` |
| 425 | `sudo systemctl start guinevere-bot` | `sudo systemctl start guinevere-discord` |
| 426 | `sudo systemctl enable guinevere-bot` | `sudo systemctl enable guinevere-discord` |
| 427 | `sudo systemctl status guinevere-bot` | `sudo systemctl status guinevere-discord` |

**Impact**: CRITICAL — the Phase 2 cutover and rollback procedures (the highest-risk phase of the migration) would completely fail because `guinevere-bot.service` doesn't exist. The emergency rollback would not work.

#### 1.2: `guinevere-core` (UNVERIFIED)

`guinevere-core` is referenced in:
- `batch-plan-migration.md` lines 129, 1583
- `phase-0-security.md` lines 293, 344
- `phase-3-memory.md` line 298
- `phase-7-hardening.md` line 571

**No `guinevere-core.service` file exists** in the `systemd/` directory. However, `guinevere-core.service` IS referenced as a dependency in the Unit sections of 5 existing service files:
- `guinevere-discord.service`: `After=guinevere-core.service`, `Requires=guinevere-core.service`
- `guinevere-loops.service`: `After=guinevere-core.service`, `Requires=guinevere-core.service`
- `guinevere-mcp.service`: `After=guinevere-core.service`, `Requires=guinevere-core.service`
- `guinevere-monitoring.service`: `Wants=guinevere-core.service`
- `guinevere-surveillance.service`: `After=guinevere-core.service`, `Requires=guinevere-core.service`

This means `guinevere-core` is a real systemd unit on the VPS, but its definition file is not in this repository. The `systemctl` commands referencing `guinevere-core` may work on the VPS but cannot be verified from the repo alone.

**Verdict**: TECHNICAL DEBT — not blocking, but the service file should be checked into the repo. The pre-migration check at batch plan line 129 would loop over 8 service names including this one.

#### 1.3: Service Count Inconsistency

| File | Line | Claim | Actual |
|---|---|---|---|
| `batch-plan-migration.md` | 129 | "All 7 Guinevere systemd services" | Lists 8 names |
| `phase-0-security.md` | 22 | "All 8 Guinevere systemd services" | 7 .service files in repo |
| `phase-1-safety.md` | 24 | "All 8 Guinevere services" | 7 .service files in repo |
| `phase-7-hardening.md` | 284 | "All 8 systemd services" | 7 .service files in repo |

The batch plan says "7" while the phase files say "8". The actual repo has 7 `.service` files. On the VPS, `guinevere-core.service` likely makes 8.

### §2 to §15 — All PASS

All other 14 checks pass without issues:
- **Port numbers** (Item 2): PostgreSQL 5433, Redis 6380, API 8000, 9Router 20128, Obscura 9222, Hermes metrics 9191 — all verified against source files and service unit `ExecStart` lines.
- **File paths** (Item 3): `/home/guinevere/config/hermes/config.yaml`, `~/.hermes/SOUL.md`, `/home/guinevere/code/guinevere/.venv/` — all match repo structure.
- **Hermes CLI** (Item 4): `hermes security`, `hermes gateway`, `hermes config`, `hermes skills`, `hermes backup`, `hermes checkpoints`, `hermes doctor`, `hermes insights`, `hermes mcp`, `hermes cron`, `hermes model`, `hermes fallback` — all documented in ADR-035 §Context.
- **Systemd syntax** (Item 5): `systemctl start/stop/restart/status/enable/disable/is-active`, `daemon-reload` — standard.
- **SOPS** (Item 6): `sops exec-env` is valid.
- **pytest** (Item 7): All test paths use `-v` flag, file paths are consistent.
- **Hook names** (Item 8): pre_prompt, post_prompt, pre_tool_call, post_tool_call, pre_response, post_response, on_error — match ADR-035 line 110 exactly.
- **Code reduction** (Item 9): 31.2% (8,057/25,796), 44.2% of affected, consistent across batch plan and ADR-035.
- **35 slash commands** (Item 10): Referenced throughout.
- **Codebase stats** (Item 11): 113 Python files, 25,796 lines — batch plan §1.4, ADR-035 line 92.
- **Redis DBs** (Item 12): Plan uses DB2 for consent gate, DB5 for surveillance — consistent with ADR-030 runtime assignments.
- **Copy-paste** (Item 13): All commands use explicit values, env vars, or documented variables. No generic placeholders.
- **Type safety** (Item 14): No `as any`, `@ts-ignore`, or equivalent in code fragments.
- **Timeline** (Item 15): "35-50 days" explicit in batch plan line 63. Phase durations sum to 20-29 days core work + shadow mode + gate iterations = 35-50 days realistic.

---

## Verdict: FAIL

**Reason**: BLOCKING wrong service name — `guinevere-bot` used 15 times in `phase-2-discord.md` where the correct service name is `guinevere-discord`. This makes the Phase 2 cutover and ALL rollback procedures non-functional. Per verdict rules: "wrong service names, wrong port numbers, wrong hook names → automatic FAIL."

### Required Fixes

1. **`phase-2-discord.md`**: Replace ALL 15 instances of `guinevere-bot` with `guinevere-discord`.
2. **`batch-plan-migration.md` line 129**: Either remove `guinevere-core` from the loop (and change "7" to "6" for repo-tracked services) OR add `guinevere-core.service` to the repo.
3. **All 4 files**: Resolve service count inconsistency — either standardize all references to "7" (repo-tracked services) or "8" (including guinevere-core on VPS), and ensure the count in each file matches.

---

## Document Metadata

| Field | Value |
|---|---|
| **Auditor** | Guinevere — Auditor 3 (Technical Accuracy) |
| **Files Audited** | `batch-plan-migration.md` + `phase-0-security.md` through `phase-7-hardening.md` (9 files) |
| **Systemd Files Read** | 7 `.service` files in `systemd/` |
| **ADR Referenced** | `adr/ADR-035-hermes-migration.md` |
| **Total Lines Read** | ~7,500+ |
| **Verdict** | **FAIL** |
| **Blocking Issue** | Wrong service name: `guinevere-bot` → must be `guinevere-discord` |