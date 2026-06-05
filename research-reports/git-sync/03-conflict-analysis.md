# B3: Git Conflict Analysis — VPS vs Windows

**Agent:** B3 (parent analysis)
**Date:** 2026-06-04
**Status:** COMPLETE
**Inputs:** `01-vps-git-state.md`, `02-windows-git-state.md`, live Windows git queries

---

## 1. Commit Topology

```
92fee59 (common ancestor — "chore: add repository secret safeguards")
   ├── 0497210 (VPS: "feat: P0-P6 implementation")       ← VPS HEAD, NOT pushed
   └── f6912b2 → ecfa0eb (Windows/origin)                 ← origin/main
                         ecfa0eb = current origin/main
```

| Metric | VPS | Windows |
|--------|-----|---------|
| HEAD | `0497210` | `ecfa0eb` |
| Commits ahead of common base | 1 | 2 |
| Tracked files modified in commits | 24 | ~400+ (full P0-P6 codebase) |
| Untracked files | 220 | 115 |
| Remote sync | ❌ SSH broken | ✅ HTTPS (fully synced) |

**Key insight:** Windows/origin contains the complete P0-P6 implementation as committed, tracked files. VPS has a partial divergent commit plus large untracked work.

---

## 2. Overlap Matrix

### 2.1 Directories with OVERLAPPING content

| Directory | VPS Status | Windows Status | Verdict |
|-----------|-----------|----------------|---------|
| `src/discord/` | ~40+ untracked files | 47 tracked (origin) + 3 untracked | **WINDOWS-AUTHORITATIVE** — tracked origin is complete P0-P6 implementation |
| `src/hermes/` | ~5 untracked files | 3 tracked (origin) + 1 untracked | **WINDOWS-AUTHORITATIVE** for tracked; **BOTH-NEEDED** for untracked `safety_plugin.py` |
| `src/hermes_plugins/` | ~10+ untracked files | 32 untracked (7 category dirs) | **WINDOWS-AUTHORITATIVE** — Windows has comprehensive, organized plugin suite; NOT in tracked origin |
| `systemd/` | 6 untracked service files | 7 tracked (origin) + 2 untracked | **WINDOWS-AUTHORITATIVE** for tracked core; **BOTH-NEEDED** for shadow-monitor services & VPS-specific monitoring service |
| `tests/hermes/` | ~5 untracked test files | 2 tracked (origin) + 1 untracked | **WINDOWS-AUTHORITATIVE** for tracked; **BOTH-NEEDED** for `test_safety_plugin.py` |
| `docs/setup-evidence/` | P0-P7 evidence (~150+ files) | Phase 1-3, P3, P8 evidence (~33 files) | **BOTH-NEEDED** — different phase evidence, no file-level collisions detected |
| `scripts/` | 4 new utility scripts + 4 modified tracked | 1 untracked (`_wp.py`) | **WINDOWS-AUTHORITATIVE** for tracked; **WINDOWS-AUTHORITATIVE** for `_wp.py` (VPS may have own scripts) |

### 2.2 Tracked File Conflicts (critical — git merge between divergent histories)

Both branches modified tracked files from common base `92fee59`. The Windows/origin branch modified more files comprehensively. VPS modified 24 files in its single commit. Direct file-level conflicts exist for:

| File | VPS (0497210) | Windows/origin (ecfa0eb) | Verdict |
|------|---------------|--------------------------|---------|
| `pyproject.toml` | Modified (+deps) | Modified (+full deps) | **WINDOWS-AUTHORITATIVE** — origin has complete dependency set |
| `src/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/api/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/config/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/main.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/models/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/services/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/services/llm_router.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/core/services/prompt_loader.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/discord/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/discord/commands.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/financial/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/loops/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/mcp/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/memory/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/memory/models.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/observability/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/persona/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `src/surveillance/__init__.py` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `scripts/guinevere-backup.sh` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `scripts/preflight-check.sh` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `scripts/run-discord-verify.sh` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |
| `scripts/setup-guild.sh` | Modified | Modified | **WINDOWS-AUTHORITATIVE** |

All 24 VPS-modified tracked files → **WINDOWS-AUTHORITATIVE** (Windows/origin contains the complete, pushed implementation).

**Windows-only tracked modifications** (uncommitted, working tree):

| File | Change | Impact | Verdict |
|------|--------|--------|---------|
| `src/discord/bot.py` | +57 / -49 lines | Hermes migration refactor | **WINDOWS-AUTHORITATIVE** — these are incremental Hermes Phase 1-2 improvements; VPS likely has base version |
| `src/discord/conversational_handler.py` | +17 lines | Hermes conversational enhancements | **WINDOWS-AUTHORITATIVE** |

### 2.3 VPS-ONLY assets (no conflict — must be captured)

| Directory/File | Description | Estimated Size | Priority |
|----------------|-------------|---------------|----------|
| `monitoring/` | Full monitoring stack (Alertmanager, Grafana, Loki, Prometheus, Promtail, exporters) | ~50+ files | **CRITICAL** |
| `.hermes/plugins/` | Hermes runtime plugin files | ~35 files | **HIGH** |
| `src/core/` (untracked VPS versions) | Core infrastructure — may differ from tracked origin | ~15+ files | **MEDIUM** — origin already has tracked versions; VPS may have runtime tweaks |
| Untracked scripts | Additional utility scripts on VPS | 4 files | **MEDIUM** |
| `docs/setup-evidence/P0/` through `P7/` | VPS evidence — broader than Windows evidence | ~150+ files | **LOW** — evidence, not source code |
| `audit-reports/P0-P7/` | VPS audit reports | ~70+ files | **LOW** — evidence |

### 2.4 Windows-ONLY assets (no conflict — must be synced to VPS)

| Directory/File | Description | Priority |
|----------------|-------------|----------|
| `hermes-config/` | Hermes SOUL.md, hooks, plugins config, env template, config.yaml | **CRITICAL** |
| `research-reports/phase-1-execution/` | Phase 1 execution research | **LOW** |
| `research-reports/phase-2/` | Phase 2 research | **LOW** |
| `research-reports/phase-3-planning/` | Phase 3 planning research | **LOW** |
| `evidence/phase-1-safety-migration/` | Safety migration evidence | **LOW** |
| `evidence/phase0-security-remediation/` | Security remediation evidence | **LOW** |
| `scripts/_wp.py` | Windows utility script | **LOW** |
| `src/hermes_plugins/` (32 files) | Comprehensive Hermes plugin suite | **HIGH** |
| `src/discord/hermes_conversational.py` | Hermes conversational Discord integration | **HIGH** |
| `src/discord/shadow_monitor.py` | Shadow monitoring for Discord | **HIGH** |
| `src/discord/shadow_pipeline.py` | Shadow pipeline | **HIGH** |
| `src/hermes/safety_plugin.py` | Core safety plugin | **CRITICAL** |
| `systemd/guinevere-shadow-monitor.service` | Shadow monitor systemd unit | **HIGH** |
| `systemd/guinevere-shadow-monitor.timer` | Shadow monitor timer | **HIGH** |
| `tests/hermes/test_safety_plugin.py` | Safety plugin tests | **HIGH** |

---

## 3. Critical Conflicts Requiring Manual Resolution

### 3.1 `src/hermes/safety_plugin.py` — **CRITICAL**

- **VPS**: Has version in ~5 untracked `src/hermes/` files (likely includes safety_plugin)
- **Windows**: Has untracked `src/hermes/safety_plugin.py` (Phase 1-2 Hermes migration)
- **Risk**: Different implementations — one from P0-P6 implementation, one from dedicated Hermes migration
- **Recommendation**: Compare both. Likely **WINDOWS version is newer** (dedicated Hermes migration Phase 1-2). Retain VPS version as archival reference.

### 3.2 `src/hermes_plugins/` — directory merger — **CRITICAL**

- **VPS**: ~10+ files (likely flat or differently organized)
- **Windows**: 32 files organized into 7 category subdirectories:
  - `commands_admin/` (backup_now, health_check, restart_service)
  - `commands_finance/` (budget, cost, cost_alert)
  - `commands_high/` (casual, focus, help, history, mood, new_session, safeword, status)
  - `commands_loop/` (evidence, loop_pause, loop_priority, loop_resume, loop_start, loop_stop, loops)
  - `commands_memory/` (memory_add, memory_export, memory_forget, memory_search)
  - `commands_surveillance/` (clear_cache, surveillance_pause, surveillance_resume, surveillance_status)
  - `commands_system/` (approve, approve_all, consent, deny, punishment, reward)
- **Risk**: Different file organization and possibly different implementations per plugin
- **Recommendation**: Use **WINDOWS version as primary** (organized, comprehensive). Merge any unique VPS plugins not present in Windows.

### 3.3 Tracked `bot.py` and `conversational_handler.py` — **HIGH**

- **VPS**: Base version from origin (no uncommitted changes detected)
- **Windows**: Uncommitted modifications: +57/-49 in `bot.py`, +17 in `conversational_handler.py`
- **Risk**: Windows modifications are Hermes Phase 1-2 work that MUST be committed before any VPS sync
- **Recommendation**: Windows changes must be committed FIRST. Then VPS syncs from updated origin. No merge needed if VPS base matches.

### 3.4 `systemd/` service file overlap — **MEDIUM**

- **Tracked origin**: 7 service files (guinevere-discord, guinevere-loops, guinevere-mcp, guinevere-monitoring, guinevere-obscura, guinevere-scheduler, guinevere-surveillance)
- **Windows untracked**: guinevere-shadow-monitor.service, guinevere-shadow-monitor.timer
- **VPS untracked**: 6 service files (guinevere-loops, guinevere-mcp, guinevere-obscura, guinevere-scheduler, guinevere-surveillance + 1 unknown)
- **Risk**: VPS services may have production-specific paths/configuration not reflected in tracked origin
- **Recommendation**: Tracked origin services are authoritative. VPS services should be compared for production-specific config (paths, env vars, user). Windows shadow-monitor services are new additions.

### 3.5 `docs/setup-evidence/` — path collisions possible — **LOW**

- **VPS**: P0, P1, P2, P3, P4, P5.5, P6, P7, decisions, agents-md-refactor, agents-md-update, persona-calibration, restructure, workflow — ~150+ files
- **Windows**: hermes-phase2-discord, phase-1, phase-3, P3, P8 — ~33 files
- **Risk**: P3 directory exists on both sides; other phases appear non-overlapping
- **Recommendation**: Merge both sets. P3 collision is minor (both are evidence files for same phase from different sessions).

---

## 4. Safe Auto-Resolvable Conflicts

### 4.1 Untracked files that DON'T overlap

All of these can be auto-merged (simply copy from one side to the other):

| Category | Source → Target | Files |
|----------|----------------|-------|
| VPS monitoring stack | VPS → Windows | `monitoring/*` (50+ files) |
| VPS .hermes runtime plugins | VPS → Windows | `.hermes/plugins/*` (35+ files) |
| Windows hermes-config | Windows → VPS | `hermes-config/*` (SOUL.md, config, hooks, plugins) |
| Windows research-reports | Windows → VPS | `research-reports/phase-*/*` |
| Windows evidence | Windows → VPS | `evidence/phase-*/*` |
| Windows shadow systemd | Windows → VPS | `systemd/guinevere-shadow-monitor.*` |

### 4.2 Identical files (no conflict)

Files that are IDENTICAL between Windows committed state and VPS untracked state. These are already in origin; VPS just can't see them. After VPS fetches from origin, these become no-op:

- `src/core/` — all tracked in origin with full implementation
- `src/loops/` — all tracked in origin
- `src/mcp/` — all tracked in origin
- `src/memory/` — all tracked in origin
- `src/observability/` — all tracked in origin
- `src/persona/` — all tracked in origin
- `src/surveillance/` — all tracked in origin
- `tests/` (non-hermes) — all tracked in origin
- `scripts/` (backup, preflight, etc.) — all tracked in origin

> **Note:** VPS may have runtime modifications to these files (config paths, env-specific settings). These are classified as VPS-ONLY assets for capture, not as conflicts.

---

## 5. Recommended Resolution Strategy

### Phase A: Prepare Windows Side (current session)

| Step | Action | Priority |
|------|--------|----------|
| A1 | **Commit Windows uncommitted changes** (`bot.py` +57/-49, `conversational_handler.py` +17) as `"feat(hermes): Phase 1-2 bot refactor and conversational handler"` | **CRITICAL** |
| A2 | **Commit Windows untracked Hermes files**: `src/hermes/safety_plugin.py`, `src/hermes_plugins/*`, `src/discord/hermes_conversational.py`, `src/discord/shadow_monitor.py`, `src/discord/shadow_pipeline.py`, `hermes-config/*`, `systemd/guinevere-shadow-monitor.*`, `tests/hermes/test_safety_plugin.py` | **CRITICAL** |
| A3 | Tag the Windows state as `"windows-sync-2026-06-04"` | HIGH |
| A4 | Push to origin/main | **CRITICAL** |

### Phase B: Fix VPS SSH + Fetch

| Step | Action | Priority |
|------|--------|----------|
| B1 | Fix VPS SSH key or add new deploy key via GitHub | **CRITICAL** |
| B2 | `git fetch origin` to get current origin state | **CRITICAL** |
| B3 | `git stash` or backup VPS working tree (220 untracked + 24 modified) | **CRITICAL** |

### Phase C: Sync VPS to Origin (reset or merge)

| Step | Action | Priority |
|------|--------|----------|
| C1 | **Option: Reset VPS to origin** — `git reset --hard origin/main` (discards VPS divergent commit `0497210`) | HIGH |
| C2 | **OR Option: Merge** — `git merge origin/main` (preserves `0497210` but risks complex conflicts) | HIGH |
| C3 | Restore VPS-ONLY untracked assets from backup: `monitoring/`, `.hermes/plugins/`, VPS-specific scripts | HIGH |

### Phase D: Restore VPS-Unique Content

| Step | Action | Priority |
|------|--------|----------|
| D1 | Copy `monitoring/` back to working tree | **CRITICAL** |
| D2 | Copy `.hermes/plugins/` back to working tree | HIGH |
| D3 | Compare VPS `src/hermes/safety_plugin.py` with Windows version; merge if VPS has unique logic | HIGH |
| D4 | Compare VPS `src/hermes_plugins/` (~10 files) with Windows version (32 files); merge unique VPS plugins | HIGH |
| D5 | Copy `docs/setup-evidence/P0/` through `P7/` back (evidence) | LOW |
| D6 | Copy `audit-reports/P0-P7/` back (evidence) | LOW |

### Phase E: Commit VPS-Unique Content

| Step | Action | Priority |
|------|--------|----------|
| E1 | Git add `monitoring/`, `.hermes/plugins/`, and any unique merged content | **CRITICAL** |
| E2 | Commit as `"feat: add VPS monitoring stack and runtime plugins"` | **CRITICAL** |
| E3 | Push to origin | **CRITICAL** |
| E4 | Verify both sides are at same commit | HIGH |

---

## 6. Recommendation Summary

| Verdict | Count | Description |
|---------|-------|-------------|
| **WINDOWS-AUTHORITATIVE** | 26 tracked files + 7 directories | Origin/main is the canonical source for all P0-P6 implementation code |
| **BOTH-NEEDED** | 5 directories/files | Manual merge: hermes_plugins, safety_plugin, systemd services, tests, setup-evidence |
| **VPS-ONLY** | 4 directories | monitoring/, .hermes/plugins/, VPS scripts, VPS evidence — must be captured and synced |
| **Windows-ONLY** | 8 directories/files | hermes-config/, research-reports, evidence, shadow-monitor — must be synced to VPS |
| **IDENTICAL** | 8 directories | src/core/, src/loops/, src/mcp/, src/memory/, src/observability/, src/persona/, src/surveillance/, tests/ — already in origin |

### Final Verdict

**Windows/origin is the authoritative source** for all tracked source code. The recommended approach is:

1. ✅ Commit Windows uncommitted work → push to origin
2. ✅ Reset VPS to origin/main (discard divergent commit `0497210`)
3. ✅ Restore VPS-unique assets (monitoring stack, runtime plugins) from backup
4. ✅ Commit VPS-unique assets → push to origin
5. ✅ Both sides converge at same origin/main HEAD

This minimizes conflict surface: only VPS-unique `monitoring/` and `.hermes/plugins/` need to be preserved from VPS. The divergent commit `0497210` can be safely discarded since its content exists in more complete form in origin.

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| VPS has production-only config changes not in origin | **Medium** | VPS won't run after sync | Compare VPS src files before reset; capture any production-specific configs |
| `safety_plugin.py` implementations are incompatible | **Medium** | Safety system breaks | Compare both versions; prefer Windows but review VPS for production fixes |
| VPS `hermes_plugins` has plugins missing from Windows | **Low** | Missing Discord commands | Compare file lists before finalizing |
| Monitoring stack configs contain VPS-specific paths | **High** | Monitoring won't start | Capture VPS monitoring configs AS-IS; paths are expected to be VPS-specific |
| SSH key fix takes time | **Medium** | Blocked sync | Prepare all Windows work first; VPS sync is independent phase |

---

## 8. Evidence & Next Steps

| Item | Path | Status |
|------|------|--------|
| VPS state analysis | `research-reports/git-sync/01-vps-git-state.md` | ✅ Complete |
| Windows state analysis | `research-reports/git-sync/02-windows-git-state.md` | ✅ Complete |
| Conflict analysis | `research-reports/git-sync/03-conflict-analysis.md` | ✅ Complete (this file) |
| Resolution plan | `research-reports/git-sync/04-resolution-plan.md` | ⬜ Pending |
| Windows commit + push | Phase A | ⬜ Pending |
| VPS SSH fix + sync | Phase B | ⬜ Pending |
| Post-sync verification | Phase F | ⬜ Pending |

### Immediate Next Action

Commit Windows uncommitted changes and untracked Hermes files to origin. This is the prerequisite for all subsequent sync steps. See `04-resolution-plan.md` (next report) for detailed execution instructions.