# ADR-035 Phase 5 Wave 4 Step 5.5 — Hermes Cron Rituals Registration

| Field | Value |
|---|---|
| **Step** | 5.5 — Hermes Cron Rituals Registration |
| **Wave** | 4 (sequential, depends on Step 5.4 Plugin/Redis bridge PASS) |
| **Date** | 2026-06-06 |
| **Evidence root** | `docs/setup-evidence/phase-5/` |
| **Planner authority** | `planner-gate-phase-5-execution-v1.1.md` §12.5, §13.5 |
| **Research inputs** | `research-reports/phase-5-execution/03-rituals-state.md` |
| **Operator** | Guinevere (Autonomous Engineering Agent) |
| **Status** | **PASS** — all scaffold criteria verified |

---

## 1. What Was Done

### 1.1 Backup and Timezone Configuration

1. **Backed up** `~/.hermes/config.yaml` to `~/.hermes/config.yaml.bak.phase5-step5.5` before any modification.
   - Backup path: `/home/guinevere/.hermes/config.yaml.bak.phase5-step5.5`
   - Size: 13,637 bytes, created 2026-06-06 05:30 UTC
2. **Set timezone** in `~/.hermes/config.yaml`:
   - Changed `timezone: ''` (empty, line 575) to `timezone: "Asia/Jakarta"`
   - Method: Python `re.sub()` via script copied to VPS and executed
   - Verified with `grep 'timezone' ~/.hermes/config.yaml` -> `timezone: "Asia/Jakarta"`

### 1.2 Hermes Cron Job Registration

Registered **5 native Hermes cron jobs** via `/home/guinevere/.local/bin/hermes cron create` using a Python script to handle prompt quoting correctly (the `prompt` positional argument is `nargs="?"` after `schedule` in Hermes v0.15.2 CLI parser):

| # | Job Name | Schedule (WIB) | Prompt | Delivery Target | Created |
|---|---|---|---|---|---|
| 1 | `ritual_morning` | `0 7 * * *` | Execute morning ritual: check mood, display streak, send greeting | `discord:1510914600777023659` | Job ID: 74ea29317ab4 |
| 2 | `ritual_midday` | `0 12 * * *` | Execute midday ritual: check mood, health reminder rotation | `discord:1510914600777023659` | Job ID: 0ea6cb898af6 |
| 3 | `ritual_afternoon` | `0 17 * * *` | Execute afternoon ritual: check mood, task summary | `discord:1510914600777023659` | Job ID: 41ef5c9cee6a |
| 4 | `ritual_evening` | `0 21 * * *` | Execute evening ritual: wind-down, day summary, streak | `discord:1510914600777023659` | Job ID: aa8a1ea74a43 |
| 5 | `ritual_midnight` | `0 0 * * *` | Execute midnight self-evaluation: mood transitions, punishment/reward review, streak update | **`local`** (NOT discord) | Job ID: e10e8335c953 |

**Midnight isolation** is enforced by:
- `--deliver local` parameter (no Discord channel ID anywhere in the create command)
- Confirmed by `hermes cron list` output showing `Deliver: local` for ritual_midnight
- No `discord:` reference in the midnight job definition

---

## 2. Files Changed / Remote State

### 2.1 Files Modified (Remote VPS)

| File | Change | Backup |
|---|---|---|
| `~/.hermes/config.yaml` | `timezone: ''` to `timezone: "Asia/Jakarta"` | `~/.hermes/config.yaml.bak.phase5-step5.5` |

### 2.2 State Created (Remote VPS)

| Resource | Details |
|---|---|
| 5 Hermes cron jobs | Registered via `hermes cron create` (see section 1.2 for job IDs and names) |
| Gateway state | PID 3915293, 5 active jobs, next run 2026-06-06T07:00:00+07:00 |

### 2.3 Files Not Modified (Intentionally)

| File | Reason |
|---|---|
| `~/.hermes/crontab.yaml` | Reference only - not loaded by Hermes v0.15.2 cron |
| `~/.hermes/config.yaml` cron section entries | Left as documentation/reference - not executed by Hermes cron |
| `src/persona/ritual_scheduler.py` | Deprecated file - not modified |
| Any local code files | Step 5.5 is VPS-only execution, no code edits |

---

## 3. Validation Results

### 3.1 Scaffold Required Commands

| # | Command | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| 3.1.1 | `hermes cron list` | 5 jobs with correct names | 5 jobs: ritual_morning, ritual_midday, ritual_afternoon, ritual_evening, ritual_midnight | PASS |
| 3.1.2 | `grep 'timezone' ~/.hermes/config.yaml` | `timezone: Asia/Jakarta` present | `timezone: "Asia/Jakarta"` | PASS |
| 3.1.3 | `hermes cron status` | Shows PID and active jobs | PID 3915293, 5 active jobs, next run 07:00 WIB | PASS |
| 3.1.4 | `hermes cron list | grep -A8 midnight` | Delivery target NOT discord | `Deliver: local` | PASS |
| 3.1.5 | `ps aux | grep -i 'hermes.*run.*--internal'` | No matching processes | No matches | PASS |

### 3.2 Python/YAML Parse (Timezone)

Config.yaml parsed via `yaml.safe_load()` confirms `timezone: "Asia/Jakarta"` is properly set as a string value.

### 3.3 Backup Verification

Backup file exists at `/home/guinevere/.hermes/config.yaml.bak.phase5-step5.5` (13,637 bytes, permissions 600).

---

## 4. Evidence Artifacts

| Artifact | Path | Description |
|---|---|---|
| Planner gate | `docs/setup-evidence/phase-5/planner-gate-phase-5-execution-v1.1.md` | Section 12.5 scaffold, section 13.5 implementation design |
| Research report | `research-reports/phase-5-execution/03-rituals-state.md` | Current cron state analysis |
| This evidence file | `docs/setup-evidence/phase-5/verification-5-5-v2.md` | Complete verification for Step 5.5 |
| Config backup | `~/.hermes/config.yaml.bak.phase5-step5.5` (VPS) | Pre-modification config backup |
| Temp scripts (cleaned up) | `/tmp/register_cron*.py` (VPS, deleted) | Helper scripts for cron registration |

---

## 5. Doc-Sync Impact

| Document | Impact | Action |
|---|---|---|
| `planner-gate-phase-5-execution-v1.1.md` | Step 5.5 now complete per scaffold | No change needed |
| `research-reports/phase-5-execution/03-rituals-state.md` | Section 3.4 (zero jobs) to 5 jobs now registered | Update on next sync if needed |
| `~/.hermes/config.yaml` | timezone updated | None needed |

---

## 6. Boundary Compliance

| Boundary | Compliance | Evidence |
|---|---|---|
| **Midnight NOT routed to Discord** | PASS | `hermes cron list` shows `Deliver: local` for ritual_midnight |
| **No `hermes run --internal` used** | PASS | All commands used `hermes cron create`; `ps aux` confirms no `--internal` processes |
| **No APScheduler activated** | PASS | No APScheduler imports or scheduler restarts |
| **No crontab.yaml as active mechanism** | PASS | Only `hermes cron create` used; crontab.yaml left as reference |
| **No secrets exposed** | PASS | No tokens, passwords, or API keys printed or stored in evidence |
| **No destructive ops** | PASS | No deletions; backup created before edits; no restart/deploy/systemctl |
| **Y4/Y5/Y6/HARD STOP/consent boundaries** | PASS | No persona or safety boundary changes |
| **No code file modifications** | PASS | Only `~/.hermes/config.yaml` modified (timezone string only) |

---

## 7. Rollback / Re-run Safety

### Rollback Plan

| Component | Safe Preview | Destructive Rollback (Requires Approval) |
|---|---|---|
| Config.yaml timezone | `ssh guinevere-vps "grep 'timezone' ~/.hermes/config.yaml"` | `ssh guinevere-vps "cp ~/.hermes/config.yaml.bak.phase5-step5.5 ~/.hermes/config.yaml"` |
| Cron jobs | `ssh guinevere-vps "hermes cron list"` | `ssh guinevere-vps "hermes cron remove <job_id>"` per job |

### Re-run Safety

All operations are idempotent:
- Setting timezone to `Asia/Jakarta` again is a no-op (already set)
- `hermes cron create` with same name would create duplicate jobs - if re-running, use `hermes cron remove <id>` first or use new names

### Timeout Recovery

During execution, the cron create commands completed successfully within ~2 seconds each. No timeout issues encountered. If a future `hermes cron create` command hangs, the safe recovery is to cancel the SSH session, verify the gateway is still running (`hermes cron status`), and retry.

---

## 8. Design Decisions / Caveats

| Decision | Rationale |
|---|---|
| **Prompt as positional arg after schedule** | Hermes v0.15.2 CLI defines `prompt` as `nargs="?"` positional after `schedule`. Passing it as `--` or as a named argument failed. Used Python subprocess to pass it correctly. |
| **Python script for registration** | Shell quoting of multi-word prompts was unreliable over SSH through PowerShell. Python `subprocess.run()` with list arguments avoided shell escaping issues entirely. |
| **`--deliver local` for midnight** | Per planner section 13.5 and 12.5. No Discord channel ID anywhere in the midnight create command. Confirmed by `hermes cron list` showing `Deliver: local`. |
| **`--deliver discord:1510914600777023659` for day rituals** | Matches existing Phase 5 target channel ID from research report section 4. |
| **Backup before editing config.yaml** | Standard precaution. Backup path documented for rollback. |
| **No deletion of existing cron jobs** | No existing cron jobs to delete (zero jobs before registration). Idempotent operation - no destruction needed. |
| **`crontab.yaml` left untouched** | File is reference-only in Hermes v0.15.2. No active mechanism uses it. Kept for documentation. |
| **Config.yaml cron section entries left in place** | These are not executed by Hermes cron (ticker runs but doesn't execute inline cron entries). Left as documentation. |

### Caveats

1. **Cron jobs will fire after gateway ticker cycle** (60s interval). First expected fire: ritual_morning at 07:00 WIB.
2. **Midnight ritual prompt references self-evaluation** - relies on LLM being able to execute via Hermes agent prompt. If midnight requires script-based execution, a `--script` + `--no-agent` approach would be needed.
3. **No restart/deploy performed** - per project policy, deployment requires all 18 gates + 5 auditors + 6 Oracle gates to pass first.
4. **Existing config.yaml `cron:` entries are stale** - they define the same rituals but are never executed by Hermes cron. They remain as reference documentation.

---

## 9. Auditor Gate

| Criterion | Status | Evidence |
|---|---|---|
| 5 jobs via `hermes cron create` | PASS | `hermes cron list` shows 5 active jobs |
| Delivery targets correct | PASS | Day rituals to discord:CHANNEL_ID; Midnight to `local` |
| Midnight NOT discord | PASS (CRITICAL) | `Deliver: local` verified |
| Timezone Asia/Jakarta | PASS | `grep timezone` + YAML parse confirmed |
| Gateway running | PASS | PID 3915293, 5 active jobs |
| No `hermes run --internal` | PASS | `ps aux` grep returns no matches |

**Auditor verdict: PASS** (all criteria satisfied)

---

## 10. Security Scan

| Check | Result |
|---|---|
| Secrets/tokens exposed in evidence? | None |
| Redis credentials printed? | N/A (no Redis commands in this step) |
| Discord token exposed? | No. Channel ID `1510914600777023659` is a public channel ID, not a secret. |
| Midnight Discord routing possible? | No - `--deliver local`, verified in cron list |
| Midnight prompt contains Discord reference? | No - prompt text is self-evaluation only |
| Backup file permissions | `-rw-------` (600) - owner-only read/write |

---

## 11. Acceptance Criteria Mapping

| Criterion | Status | Verification |
|---|---|---|
| 5 Hermes native cron jobs registered | PASS | `hermes cron list` to 5 active jobs with correct names |
| Timezone set to Asia/Jakarta | PASS | `grep timezone` to `timezone: "Asia/Jakarta"` |
| Midnight ritual is local-only, no Discord | PASS | `Deliver: local` for ritual_midnight |
| No `hermes run --internal` commands | PASS | No processes, no commands used |
| Evidence file written | PASS | This file: `verification-5-5-v2.md` |
| Backup documented | PASS | `~/.hermes/config.yaml.bak.phase5-step5.5` |
| Gateway running with active jobs | PASS | PID 3915293, 5 active jobs |
| No duplicate jobs created | PASS | Initial state was zero jobs; created exactly 5 unique jobs |
| No destructive operations performed | PASS | No deletions, restarts, or deploys |

---

## 12. Footer

### Summary

Step 5.5 is **PASS**. All scaffold criteria from planner gate section 12.5 are satisfied:

- `~/.hermes/config.yaml` modified - `timezone: "Asia/Jakarta"` set
- 5 Hermes cron jobs registered via `hermes cron create` with stable names
- Day rituals (morning, midday, afternoon, evening) deliver to Discord channel 1510914600777023659
- Midnight ritual delivers to `local` only - no Discord routing
- `hermes cron list` confirms 5 active jobs
- `hermes cron status` confirms gateway running with 5 active jobs
- No `hermes run --internal` usage
- Evidence file written
- Config backup at known path

### Next Actions

- Step 5.6 (Ritual Verification) can proceed after gateway ticker processes the first tick cycle
- Step 5.8 (Final Integration + Deploy) depends on Step 5.6 completion

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-06 | Guinevere | Initial evidence for Step 5.5 - Hermes Cron Rituals Registration |

---

*Compliant with AGENTS.md 2.5 (Planner Verification Scaffold), 2.9 (File-Based Output), and section 11 (Evidence Minimum Schema).*
