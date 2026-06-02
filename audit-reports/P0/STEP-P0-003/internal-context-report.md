# STEP-P0-003 — Internal Context Report (Phase 0 Research Synthesis)

**Step:** P0-003 — Directory Structure Creation (canonical `/home/guinevere/` layout)
**Phase:** P0 Infrastructure Foundation (29 steps, step 3 of 29)
**Date:** 2026-05-31
**Status:** ⬜ Not Started (P0-000, P0-001, P0-002 complete)
**Scope:** Internal repo/doc/ADR context audit + execution planning — read-only, no VPS changes
**Report type:** Pre-implementation internal research (research wave output)
**Source files read:**
- `stepprompts/StepPrompts.md` (lines 444–515)
- `PROGRESS.md` (line 47)
- `CHECKLIST.md` (line 101)
- `docs/IMPLEMENTATION_GUIDE.md`
- `docs/10-governance/17-ADR_Index_v1.0.md`
- `adr/ADR-014-vps-container-architecture.md`
- `docs/00-core/02-TechnicalArchitecture_v2.0.md` (section 3.2, lines 166–280)
- `docs/setup-evidence/P0/STEP-P0-002/*` (P0-002 evidence for pattern reference)
- `audit-reports/P0/STEP-P0-002/internal-context-report.md` (P0-002 pattern)
- `audit-reports/P0/STEP-P0-001-auditor-report.md` (P0-001 auditor pattern)

---

## 1. Step Definition (from StepPrompts.md lines 444–515)

| Field | Value |
|-------|-------|
| **Step ID** | P0-003 |
| **Type** | Infrastructure |
| **Risk** | Low |
| **Status** | ⬜ Not Started |
| **Goal** | Create canonical directory structure for all Guinevere code, config, data, logs, and backups |
| **Dependencies** | P0-001 (guinevere user created) — ✅ Complete |
| **Cost Impact** | $0/month |
| **ADR References** | ADR-014 (VPS & Container Architecture) |
| **Acceptance Criteria** | AC-CORE-001, AC-DATA-001 |
| **Estimated Time** | 1 hour |
| **Git Commit** | `chore(P0): pending` |

### 1.1 Context (from StepPrompts)

> A consistent directory layout prevents confusion, simplifies backups, and enables predictable systemd unit configurations. All paths in subsequent steps reference this structure.

### 1.2 Commands (from StepPrompts lines 465–489)

```bash
sudo su - guinevere
mkdir -p /home/guinevere/{code/guinevere,config/{hermes,9router,mcp,caddy,sops},data/{postgres,redis,prometheus,grafana,loki,backups,uploads},logs/{guinevere,surveillance,loops},backups/{local,s3,r2},evidence,secrets,scripts,tmp}
sudo mkdir -p /etc/systemd/system/guinevere-*.service.d
chmod 750 /home/guinevere
chmod -R 750 /home/guinevere/code
chmod -R 750 /home/guinevere/config
chmod 700 /home/guinevere/secrets
chmod 750 /home/guinevere/data
chmod 750 /home/guinevere/logs
chmod 750 /home/guinevere/backups
chmod 750 /home/guinevere/evidence
chmod 700 /home/guinevere/scripts
find /home/guinevere -type d | sort
```

### 1.3 Verification (from StepPrompts)

| Check | Command | Expected |
|-------|---------|----------|
| Directory count | `find /home/guinevere -type d \| wc -l` | >= 25 |
| Secrets perms | `ls -la /home/guinevere/secrets` | 700 |
| Code dir ready | `ls -la /home/guinevere/code/guinevere` | Empty dir |
| Owner | `stat -c '%U' /home/guinevere/code` | `guinevere` |

### 1.4 Evidence Path (from StepPrompts)

| Evidence Item | Path |
|--------------|------|
| Directory tree | `docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt` |

P0-002 evidence pattern also includes `verification.md`, `p0-003-summary.md`, `aizanta-post-check.md`. Follow same convention.

### 1.5 Rollback

```bash
sudo rm -rf /home/guinevere/{code,config,data,logs,backups,evidence,secrets,scripts,tmp}
```

---

## 2. Current Tracker State

### 2.1 PROGRESS.md (line 47)

```
- [ ] **P0-003** Directory structure: /home/guinevere/{code,config,data,logs,backups}
```

Status: **NOT checked** — ready for execution. Overall: 3/257 steps complete.

### 2.2 CHECKLIST.md (line 101)

```
- [ ] P0-003: `ls -la /home/guinevere/` -> dirs: code/, config/, data/, logs/, backups/ (owner=guinevere, perms=700)
```

Status: **NOT checked**. CHECKLIST verification is shallow (5 top-level dirs) vs StepPrompts (25+ dirs). Must verify both.

### 2.3 StepPrompts.md status

Line 447: `**Status:** ⬜ Not Started` — update to ✅ after execution.

### 2.4 Evidence directory

`docs/setup-evidence/P0/STEP-P0-003/` — **exists in project but empty** (no prior evidence).

---

## 3. ADR-014 Constraints (VPS & Container Architecture)

**Status:** Accepted | **Risk:** HIGH

| Constraint | Detail | Impact on P0-003 |
|------------|--------|------------------|
| Single primary VPS | Ubuntu 24.04 with systemd + selective containers | Directory structure is canonical for all subsequent steps |
| User isolation | `guinevere` user owns all paths | P0-003 must set `guinevere:guinevere` ownership |
| Secrets separation | SOPS + age at `/home/guinevere/secrets/` | P0-003 creates `secrets/` with `chmod 700` |
| Code directory | Code under `/home/guinevere/code/guinevere/` | P0-003 creates this for git clone (P0-025) |
| Config isolation | Config under `/home/guinevere/config/` | Subdirs for hermes, 9router, mcp, caddy, sops |
| Data separation | Data under `/home/guinevere/data/` | Subdirs for postgres, redis, prometheus, grafana, loki |
| Log isolation | Logs under `/home/guinevere/logs/` | Subdirs for guinevere, surveillance, loops |
| Backup isolation | Backups under `/home/guinevere/backups/` | Subdirs for local, s3, r2 |

### ADR-014 Key Point

Tech Arch v2.0 (section 3.2) documents an *app-level* directory structure under `core/` (not `code/guinevere/`). P0-003 creates the *operational* structure. The app structure will be created during code implementation (P0-025+). These are complementary — P0-003 creates the container, later steps create the contents.

---

## 4. Technical Architecture Directory Context (docs/00-core/02-TechnicalArchitecture_v2.0.md)

### Section 3.2 (lines 166–280) — App Code Layout

The Tech Arch shows:
```
/home/guinevere/
├── core/          (persona, memory, plugins, agents, sdlc)
├── surveillance/  (api, processor, geofence, encrypt)
├── scheduler/     (rituals, proactive, self_deploy)
├── monitoring/    (health, metrics, alerting)
├── config/        (.env.sops, settings, feature_flags)
├── data/          (logs, cache)
└── scripts/       (setup, backup, health_check)
```

**Contradiction (F2):** Tech Arch lists `config/`, `data/`, `scripts/` as peers of `core/` under `/home/guinevere/`. P0-003 instead creates `code/guinevere/` as the code root, with `config/`, `data/`, `scripts/` as peers of `code/`. Resolution: Tech Arch describes the app layout *inside* the repo; P0-003 creates the repo parent. The app will organize itself inside `code/guinevere/` per Tech Arch.

---

## 5. Prerequisites Status

| Prerequisite | Status | Notes |
|-------------|--------|-------|
| P0-001 complete | ✅ Yes | guinevere user exists, home dir ready |
| P0-002 complete | ✅ Yes | SSH access confirmed, evidence exists |
| Disk space >= 60GB at /home | ⚠️ Check before exec | `df -h /home` on VPS |

---

## 6. Cross-Doc Findings & Contradictions

### F1: CHECKLIST vs StepPrompts verification depth mismatch
- **CHECKLIST (line 101):** Verifies only 5 top-level dirs (700 perms)
- **StepPrompts (lines 491–495):** Verifies >= 25 dirs, secrets/ = 700 scripts/ = 700, owner = guinevere
- **Resolution:** Verify BOTH. Update CHECKLIST to match full depth.

### F2: Tech Arch path mismatch
- Tech Arch uses `core/` as code root under `/home/guinevere/`
- P0-003 uses `code/guinevere/`
- **Severity:** Low — Tech Arch describes app layout inside repo; P0-003 creates repo parent.

### F3: StepPrompts systemd wildcard dir
- `sudo mkdir -p /etc/systemd/system/guinevere-*.service.d` creates a literal `*` directory
- **Severity:** Low — template dir only, proper override dirs created in later steps.

### F4: `sudo su - guinevere` interactive in automated context
- StepPrompts uses interactive shell switch; for scripted exec prefer `sudo -u guinevere`
- **Severity:** Informational — interactive via SSH is fine.

### F5: StepPrompts status for P0-001/P0-002 still ⬜
- P0-001 auditor flagged; regression will be caught per-step
- **Resolution:** Fix all completed statuses when updating P0-003.

### F6: Evidence convention consistency
- Pattern: `docs/setup-evidence/P0/STEP-P0-{MMM}/` matches P0-001/P0-002
- IMPLEMENTATION_GUIDE says `evidence/phase-N/step-MMM/` but not followed
- Stay with StepPrompts pattern.

---

## 7. Shared Writers & Collision Scan

| Resource | Writer | Conflict Risk |
|----------|--------|--------------|
| `/home/guinevere/{code,config,data,logs,backups,...}` | VPS — P0-003 | **Exclusive** — no other step creates these |
| `/etc/systemd/system/guinevere-*.service.d` | VPS — P0-003 | Template dir only |
| `PROGRESS.md` | Parent-only | Update after completion |
| `CHECKLIST.md` | Parent-only | Update after completion |
| `StepPrompts.md` | Parent-only | Update status |
| `docs/setup-evidence/P0/STEP-P0-003/` | P0-003 | Exclusive |

**No collision risk.** P0-003 has exclusive ownership of its state.

### Downstream consumers (directories must exist with correct perms)

| Directory | Consumed By | Step |
|-----------|-------------|------|
| `code/guinevere/` | Git clone | P0-025 |
| `config/hermes/` | Hermes config | P1-005 |
| `config/9router/` | 9Router config | P1-007 |
| `config/mcp/` | MCP config | P6-001 |
| `config/caddy/` | Caddy config | P0-024 |
| `config/sops/` | SOPS config | P0-011/013 |
| `data/postgres/` | PostgreSQL data | P0-014 |
| `data/redis/` | Redis data | P0-020 |
| `data/prometheus/` | Prometheus data | P8-001 |
| `data/grafana/` | Grafana data | P8-006 |
| `data/loki/` | Loki data | P8-009 |
| `logs/guinevere/` | Core logging | P0-018+ |
| `logs/surveillance/` | Surveillance logging | P7-001+ |
| `logs/loops/` | Loop logging | P5-003+ |
| `backups/*` | Backup baseline | P0-027 |
| `evidence/` | All evidence | All steps |
| `secrets/` | Age keys + SOPS | P0-012, P0-013 |
| `scripts/` | Utility scripts | Various |

---

## 8. Blockers & Risks

### Blocking Issues: **0**

### Non-Blocking Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Directory ownership wrong | MEDIUM | Run as guinevere; verify with `stat -c '%U'` |
| Disk space insufficient | MEDIUM | Check `df -h /home` before exec |
| `secrets/` not 700 | MEDIUM | StepPrompts sets explicitly; verify post-exec |
| systemd literal `*` dir | LOW | Harmless; noted in evidence |
| `scripts/` not 700 | LOW | StepPrompts sets explicitly; verify post-exec |
| Evidence convention inconsistency | LOW | Stick with StepPrompts pattern |
| StepPrompts status not updated | LOW | Fix in batch |

---

## 9. Verification Commands (Synthesized for Execution)

```bash
# 1. Directory count (expect >= 25)
find /home/guinevere -type d | wc -l

# 2. Top-level listing
ls -la /home/guinevere/

# 3. Permission checks
ls -la /home/guinevere/secrets    # drwx------
ls -la /home/guinevere/scripts    # drwx------
ls -la /home/guinevere/code       # drwxr-x---
ls -la /home/guinevere/config     # drwxr-x---
ls -la /home/guinevere/data       # drwxr-x---
ls -la /home/guinevere/logs       # drwxr-x---
ls -la /home/guinevere/backups    # drwxr-x---
ls -la /home/guinevere/evidence   # drwxr-x---

# 4. Owner check
stat -c '%U' /home/guinevere/code    # guinevere
stat -c '%U' /home/guinevere/config  # guinevere

# 5. Code dir empty
ls -la /home/guinevere/code/guinevere  # . and .. only

# 6. Aizanta unaffected
systemctl status aizanta-*  # all running

# 7. Systemd config entry
ls -la /etc/systemd/system/ | grep guinevere
```

---

## 10. Recommended Evidence Manifest

| File | Content Source |
|------|---------------|
| `docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt` | `find /home/guinevere -type d \| sort` |
| `docs/setup-evidence/P0/STEP-P0-003/verification.md` | All verification command outputs |
| `docs/setup-evidence/P0/STEP-P0-003/p0-003-summary.md` | What/changed/security/rollback |
| `docs/setup-evidence/P0/STEP-P0-003/aizanta-post-check.md` | Aizanta health after change |

---

## 11. Verdict Summary

| Dimension | Status |
|-----------|--------|
| **Blocking issues** | 0 |
| **Process findings** | 6 (F1–F6, all non-blocking) |
| **Prerequisites** | 2 of 2 (1 unknown — disk space) |
| **Shared writer conflicts** | None |
| **ADR compliance** | ADR-014 aligned; Tech Arch sec 3.2 ambiguity noted |
| **Safety boundaries** | secrets/ = 700, scripts/ = 700, guinevere:guinevere |
| **Downstream dependency** | All subsequent steps depend on correct dirs |
| **Ready for implementation** | **YES** — verify disk space first |
