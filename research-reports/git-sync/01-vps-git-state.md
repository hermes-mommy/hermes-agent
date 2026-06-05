# VPS Git State Analysis

**Date**: 2026-06-05
**Analyst**: Guinevere (Sisyphus-Junior)
**VPS**: `guinevere-vps` | `/home/guinevere/code/guinevere`
**Remote**: `git@github.com:fazulfi/guinevere.git`

---

## 1. Executive Summary

| Metric | Value |
|---|---|
| VPS HEAD | `0497210` — feat: P0-P6 implementation |
| VPS commit count | 3 |
| VPS ahead of origin/main | **1 commit** |
| VPS behind origin/main | 0 (cannot verify — SSH key broken) |
| Uncommitted modified files | 24 files (1,730 insertions, 120 deletions) |
| Untracked files | 220 files |
| SSH access to GitHub | **BROKEN** (`Permission denied (publickey)`) |
| Stash | Empty |

**Critical finding**: VPS cannot `git fetch` or `git push` to GitHub. The SSH key is missing or invalid. This blocks any sync with remote.

---

## 2. Complete Git Status

```
On branch main
Your branch is ahead of 'origin/main' by 1 commit.
  (use "git push" to publish your local commits)

Changes not staged for commit:
  modified:   pyproject.toml
  modified:   scripts/guinevere-backup.sh
  modified:   scripts/preflight-check.sh
  modified:   scripts/run-discord-verify.sh
  modified:   scripts/setup-guild.sh
  modified:   src/__init__.py
  modified:   src/core/__init__.py
  modified:   src/core/api/__init__.py
  modified:   src/core/config/__init__.py
  modified:   src/core/main.py
  modified:   src/core/models/__init__.py
  modified:   src/core/services/__init__.py
  modified:   src/core/services/llm_router.py
  modified:   src/core/services/prompt_loader.py
  modified:   src/discord/__init__.py
  modified:   src/discord/commands.py
  modified:   src/financial/__init__.py
  modified:   src/loops/__init__.py
  modified:   src/mcp/__init__.py
  modified:   src/memory/__init__.py
  modified:   src/memory/models.py
  modified:   src/observability/__init__.py
  modified:   src/persona/__init__.py
  modified:   src/surveillance/__init__.py

Untracked files:
  .hermes/
  docs/setup-evidence/phase-1/
  monitoring/
  scripts/bench_memory.py
  scripts/setup-service-envs.sh
  scripts/test_alert_routing.sh
  scripts/test_log_pipeline.sh
  src/core/api/auth.py
  src/core/api/routes.py
  src/core/services/monthly_report.py
  src/discord/_embed_helpers.py
  src/discord/bot.py
  src/discord/bot.py.bak.pre-phase2
  ... (88 Hermes command modules)
  ... (40+ new source modules across hermes, loops, mcp, memory, persona, surveillance)
  systemd/ (6 service files)
  tests/hermes/
```

---

## 3. Commit History (VPS)

### All 3 commits on VPS `main`

```
0497210 2026-06-03 02:03:15 +0700 Guinevere: feat: P0-P6 implementation
92fee59 2026-05-31 20:29:12 +0700 Guinevere: chore: add repository secret safeguards
6a793e6 2026-05-31 19:40:27 +0700 Guinevere: chore: initial repo structure
```

### Commit 0497210 Detail (UNPUSHED)

- **Author**: Guinevere `<faiz@guinevere.local>`
- **Date**: Wed Jun 3 02:03:15 2026 +0700
- **Files changed**: 80 files, **20,024 insertions**, 80 deletions
- **Key contents**:
  - Full project scaffold: `src/`, `tests/`, `scripts/`, `secrets/`
  - Alembic migrations (3 versions, including `initial_schema_47_tables.py` — 1,116 lines)
  - P1-P3 setup evidence (auditor-gate, verification, migration checkpoints)
  - Core services: `cost_tracker.py`, `hard_stop_handler.py`, `llm_router.py`, `prompt_loader.py`
  - Discord: `commands.py` (291 lines), `guild_setup.py` (445 lines), `intents.py`, `permissions.py` (526 lines)
  - Memory models: `models.py` (1,207 lines)
  - Safety tests: `test_hard_stop_handler.py`, `test_hard_stop_model.py`
  - Smoke tests: `test_persona_basic.py`, `test_safe_word.py`, `test_yandere_boundary.py`
  - `stepprompts/StepPrompts.md` (8,010 lines)
  - `uv.lock` (2,207 lines)
  - Backup scripts: `guinevere-backup.sh`, `guinevere-backup-docker.sh`, systemd timers
  - Restic backup configs: `cloudflare-r2.env`, `idcloudhost-s3.env`
  - Discord secrets: `secrets/discord-secrets.yaml`

### Origin/Main State (ON REMOTE, NOT on VPS HEAD)

```
92fee59 chore: add repository secret safeguards
6a793e6 chore: initial repo structure
```

The VPS origin/main pointer is at `92fee59`. The `0497210` commit exists only on the VPS and has never been pushed.

---

## 4. Branch Configuration

| Type | Name |
|---|---|
| Local | `main` (only branch) |
| Remote | `origin/main` |
| Remote URL | `git@github.com:fazulfi/guinevere.git` (fetch & push) |

**Note**: The VPS only sees `origin/main`. The local machine sees 26 remote branches (`feat/guinevere/*`, `test/guinevere-*`). This is consistent — the VPS has a stale remote view since it cannot fetch.

---

## 5. Divergence Analysis

### 5.1 VPS → Remote (what VPS has that remote doesn't)

| Commit | Description | Lines |
|---|---|---|
| `0497210` | feat: P0-P6 implementation | +20,024 / -80 |

This is the entire P0-P6 phase implementation that was committed on the VPS on June 3 at 2 AM. **Never pushed.**

### 5.2 Remote → VPS (what remote has that VPS doesn't)

**UNKNOWN** — `git fetch origin` failed with `Permission denied (publickey)`. The VPS cannot reach GitHub to check if origin/main has advanced.

### 5.3 VPS vs Local Machine

The VPS and local machine are on **completely divergent commit chains** after the common ancestor:

| | VPS | Local (Windows) |
|---|---|---|
| HEAD | `0497210` (P0-P6) | `66abd4d` (Hermes migration docs) |
| Total commits | 3 | 5 |
| Shared ancestor | `92fee59`? | Unknown |
| Remote branches visible | 1 (`origin/main`) | 26 |
| Uncommitted changes | 24 modified + 220 untracked | 1 modified + few untracked |

**VPS commit chain**:
```
6a793e6 → 92fee59 → 0497210 (P0-P6 implementation)
```

**Local commit chain**:
```
f6912b2 → ecfa0eb → 871b72a → 3110f2a → 66abd4d (Hermes migration)
```

The local machine's commits are all Hermes-migration related and do not appear on the VPS. The VPS's P0-P6 commit does not appear on the local machine. They share the same remote (`github.com:fazulfi/guinevere.git`) but have **completely different histories** on their respective `main` branches.

---

## 6. Uncommitted Changes

### 6.1 Modified Files (24 files, 1,730 insertions, 120 deletions)

| File | Lines Changed |
|---|---|
| `scripts/guinevere-backup.sh` | +686/-120 (backup script rewrite) |
| `src/core/main.py` | +274/-? (major extension) |
| `src/persona/__init__.py` | +235 (persona module init) |
| `src/memory/__init__.py` | +210 (memory module init) |
| `src/core/services/prompt_loader.py` | +169/-? (extended) |
| `src/surveillance/__init__.py` | +86 (surveillance module init) |
| `src/discord/commands.py` | +47/-? |
| `src/loops/__init__.py` | +39 (loops module init) |
| `src/memory/models.py` | +34/-? |
| `src/mcp/__init__.py` | +23 (MCP module init) |
| `src/core/services/llm_router.py` | +19/-? |
| `src/core/services/__init__.py` | +13 |
| `src/observability/__init__.py` | +5 |
| `pyproject.toml` | +3 |
| `src/__init__.py` | +1 |
| `src/core/__init__.py` | +1 |
| `src/core/api/__init__.py` | +1 |
| `src/core/config/__init__.py` | +1 |
| `src/core/models/__init__.py` | +1 |
| `src/discord/__init__.py` | +1 |
| `src/financial/__init__.py` | +1 |
| `scripts/preflight-check.sh` | 0 (mode change?) |
| `scripts/run-discord-verify.sh` | 0 (mode change?) |
| `scripts/setup-guild.sh` | 0 (mode change?) |

### 6.2 Untracked Files (220 files)

Organized by module:

| Module | Count | Key Files |
|---|---|---|
| `src/discord/` | ~40 | Bot, 30+ command modules, shadow pipeline, Hermes conversational, notifications |
| `src/hermes_plugins/` | ~35 | Plugin commands organized by domain (admin, finance, high, loop, memory, surveillance, system) |
| `src/hermes/` | 4 | Core Hermes integration (memory bridge, safety plugin, session adapter) |
| `src/surveillance/` | 11 | Auth, classification, consent gate, consumer, models, redis buffer, replay, retention, router, safe mode, secret scanner, secrets, timescale |
| `src/persona/` | 13 | Drift detector/corrector, mood engine, punishment/reward engines, ritual scheduler + 5 rituals, safe mode, streak tracker, transition rules, yandere FSM |
| `src/memory/` | 5 | Consolidation, DNR, embeddings, read/write pipelines |
| `src/mcp/` | 17 | Auth, auth matrix, budget, cost, manager, tool selector, 13 tool implementations |
| `src/loops/` | 16 | Artifacts, contract, cost, enforcer, evidence, guardian, hash anchor, manager, 7 phase modules, scheduler, state machine, sub-agent, verify |
| `src/core/` | 3 | `api/auth.py`, `api/routes.py`, `services/monthly_report.py` |
| `monitoring/` | 27 | Grafana dashboards, Prometheus rules, Loki, Promtail, exporters, compose file |
| `systemd/` | 6 | Service files for loops, MCP, monitoring, obscura, scheduler, surveillance |
| `scripts/` | 4 | `bench_memory.py`, `setup-service-envs.sh`, test scripts |
| `.hermes/` | 3 | Safety plugin init + config |
| `tests/hermes/` | 1 | `test_safety_plugin.py` |

### 6.3 Backup Files (pre-Phase 2 state)

- `src/discord/bot.py.bak.pre-phase2`
- `src/discord/conversational_handler.py.bak.pre-phase2`

---

## 7. SSH Key Issue

```
$ ssh -T git@github.com
git@github.com: Permission denied (publickey).
```

The VPS cannot authenticate to GitHub. This means:
- Cannot `git fetch` to check if origin/main has advanced
- Cannot `git push` the 1 un-pushed commit
- Cannot sync uncommitted changes to any remote

**Root cause**: Either the SSH private key is missing from `~/.ssh/`, or the key on the VPS is not registered with GitHub as a deploy key.

---

## 8. Risk Assessment

| Risk | Severity | Detail |
|---|---|---|
| Data loss | **HIGH** | 220 untracked files + 24 uncommitted modifications exist only on VPS. If the VPS is destroyed, ALL Phase 2+ work is lost. |
| Divergent histories | **HIGH** | VPS and local have different commit chains on `main`. Any merge will be complex. |
| No push capability | **HIGH** | SSH key broken — cannot push the 1 existing commit or any future work. |
| Secret exposure risk | **MEDIUM** | `secrets/discord-secrets.yaml` and backup configs committed in `0497210`. Verify they should have been committed (or were they meant to be `.gitignore`d?). |
| Stale remote view | **LOW** | Since VPS can't fetch, the divergence between VPS and origin/main may be larger than reported. |

---

## 9. Recommendations

1. **Fix SSH key immediately** — Restore or regenerate the deploy key for `git@github.com` on the VPS.
2. **Commit untracked work** — The 220 untracked files represent Phase 2+ implementation. They should be committed as a checkpoint.
3. **Handle divergent histories** — After restoring SSH, coordinate between VPS `main` and local `main`. One will need to be rebased onto the other.
4. **Audit secrets in commits** — Review `0497210` to confirm `secrets/discord-secrets.yaml` and `secrets/backup/*.env` files contain only placeholders, not real credentials.
5. **Do NOT force-push** — Given the complex divergence, any force-push could destroy work on either side.

---

## 10. Raw Command Output Reference

All raw outputs are captured in full above. No additional files were generated on the VPS.