# B4: Git Sync Strategy — Divergent VPS & Windows Histories

**Agent:** B4 (strategy designer)
**Date:** 2026-06-04
**Status:** COMPLETE
**Inputs:** `01-vps-git-state.md`, `02-windows-git-state.md`, `03-conflict-analysis.md`

---

## 1. Strategy Options Analysis

### Strategy A: Force Push VPS → Origin → Pull Windows

**Description:** Fix VPS SSH, force push VPS `main` to origin (overwriting Windows's 2 commits), then pull on Windows.

| Aspect | Assessment |
|--------|-----------|
| **Pros** | Single push operation; VPS doesn't need reset |
| **Cons** | Destroys Windows's 2 committed commits (`f6912b2`, `ecfa0eb`) containing full P0-P6 tracked implementation; VPS commit `0497210` is partial and inferior; violates "Windows/origin authoritative" principle |
| **Data loss risk** | **HIGH** — loses full Hermes migration planning commit on origin, loses Windows's comprehensive `hermes_plugins/` organization |
| **Complexity** | Low (single force push) |
| **Recovery difficulty** | Difficult — origin's previous HEAD must be recovered from reflog or Windows local |
| **Verdict** | ❌ **REJECTED** — VPS commit is the inferior version; force-pushing destroys the more complete Windows/origin implementation |

### Strategy B: Windows Push → Origin → Reset VPS → Restore Unique Assets (RECOMMENDED ✅)

**Description:** Commit Windows uncommitted work, push to origin, hard-reset VPS to origin/main, restore VPS-unique assets (`monitoring/`, `.hermes/plugins/`), commit and push.

| Aspect | Assessment |
|--------|-----------|
| **Pros** | Windows/origin remains authoritative (correct); no destructive force-push; VPS divergent commit safely discarded; VPS-unique assets preserved via backup-and-restore; both sides converge at same HEAD; minimal conflict surface |
| **Cons** | 3-phase operation (Windows prep → SSH fix → VPS sync); requires SSH fix as prerequisite; VPS must be reset (discards divergent commit); multi-step restore required |
| **Data loss risk** | **LOW** — VPS backup created before any destructive operation; only the divergent commit `0497210` is discarded (its content exists more completely in origin) |
| **Complexity** | Medium (3 phases, ~15 atomic steps) |
| **Recovery difficulty** | Easy — backup tarball allows rollback; reflog preserves old HEAD |
| **Verdict** | ✅ **RECOMMENDED** — safest, preserves authoritative history, captures all unique assets |

### Strategy C: Cherry-Pick / Selective Merge

**Description:** Don't reset either side. Instead, cherry-pick or merge specific commits/files between the two divergent branches to create a unified history.

| Aspect | Assessment |
|--------|-----------|
| **Pros** | Preserves both commit histories; no history rewrite; may feel less "destructive" |
| **Cons** | All 24 tracked files would need conflict resolution (VPS modified same files as origin but with less complete versions); every file-level conflict requires manual review; cherry-picking `0497210` adds nothing — origin already has more complete versions of every file; creates a confusing merge commit that combines inferior + superior versions; 220 untracked VPS files still need separate handling |
| **Complexity** | **HIGH** — 24 file-level merge conflicts, manual resolution per file, high chance of human error |
| **Risk** | **MEDIUM** — merge conflicts in `bot.py`, `main.py`, `llm_router.py` could introduce partial code; production services could break from incomplete merges |
| **Effort** | 2-4 hours of manual conflict resolution for zero gain |
| **Verdict** | ❌ **REJECTED** — 100% of divergent commit content already exists in origin in more complete form. Cherry-picking wastes time and adds risk with no benefit. |

---

## 2. Recommended Strategy: Strategy B

### Exact Strategy

```
Phase 0 (Windows): Commit all uncommitted work → push to origin
Phase 1 (VPS):     Fix SSH access
Phase 2 (VPS):     Create full backup tarball
Phase 3 (VPS):     Hard reset to origin/main (discard divergent commit)
Phase 4 (VPS):     Restore VPS-unique assets from backup
Phase 5 (VPS):     Commit and push VPS-unique assets
Phase 6 (Windows): Pull to sync → verify both sides match
```

### Rationale

1. **Windows/origin is factually authoritative** — it contains the complete P0-P6 implementation as committed, tracked files. The B3 conflict analysis proved that all 24 files in VPS's divergent commit `0497210` have more complete versions in origin. Nothing is lost by discarding that commit.

2. **Single source of truth** — after sync, origin/main is the canonical state. Both environments track the same HEAD. No ambiguous "which side is correct?" questions remain.

3. **Minimal conflict surface** — only 4 directories need manual attention post-reset: `monitoring/`, `.hermes/plugins/`, VPS-specific scripts, and VPS evidence. Everything else comes from origin.

4. **VPS-unique assets are self-contained** — the monitoring stack and Hermes runtime plugins are directory-level additions, not file-level conflicts. They can be restored as whole directories without merge complexity.

5. **Backup-first approach** — a full `/home/guinevere/code/guinevere` tarball is created before any destructive operation. Rollback is a simple `tar -xzf` + `git reset --hard` away.

6. **Separable phases** — Phase 0 (Windows) can proceed immediately without waiting for SSH fix. Phase 1-5 (VPS) is independent and can be executed whenever SSH is fixed.

### Why Not Alternatives

| Concern | Why Strategy B Handles It |
|---------|---------------------------|
| "Don't we lose VPS work?" | No. The divergent commit's content exists more completely in origin. Untracked VPS assets are backed up and restored. |
| "What about production configs?" | Backup captures all files including configs. Post-restore, any VPS-specific config differences in `src/` files are identified via diff and can be manually re-applied. |
| "Isn't reset destructive?" | Yes, but the backup tarball + git reflog provide two independent rollback paths. |
| "Why not merge?" | Merging adds complexity for zero gain — every file in `0497210` has a better version in origin. |

---

## 3. Step-by-Step Execution Plan

### Phase 0: Windows Preparation (execute from Windows)

#### Step 0.1: Verify current state

```powershell
# Run from: C:\Users\faizz\guinevere
git status
git log --oneline -5
git remote -v
```

#### Step 0.2: Commit modified tracked files

```powershell
git add src/discord/bot.py src/discord/conversational_handler.py
git commit -m "feat(hermes): Phase 1-2 bot refactor and conversational handler enhancements"
```

#### Step 0.3: Commit untracked Hermes implementation files

```powershell
git add src/hermes/safety_plugin.py
git add src/hermes_plugins/
git add src/discord/hermes_conversational.py
git add src/discord/shadow_monitor.py
git add src/discord/shadow_pipeline.py
git add hermes-config/
git add systemd/guinevere-shadow-monitor.service
git add systemd/guinevere-shadow-monitor.timer
git add tests/hermes/test_safety_plugin.py
git commit -m "feat(hermes): Phase 1-2 safety plugin, conversational handler, shadow pipeline, and plugin suite"
```

#### Step 0.4: Commit remaining non-conflicting untracked files

```powershell
git add research-reports/phase-1-execution/
git add research-reports/phase-2/
git add research-reports/phase-3-planning/
git add evidence/phase-1-safety-migration/
git add evidence/phase0-security-remediation/
git add docs/setup-evidence/hermes-phase2-discord/
git add docs/setup-evidence/phase-1/
git add docs/setup-evidence/phase-3/
git add docs/setup-evidence/P3/
git add docs/setup-evidence/P8/
git add scripts/_wp.py
git commit -m "docs: Phase 1-3 research reports, evidence, and setup documentation"
```

#### Step 0.5: Tag pre-sync state

```powershell
git tag -a "windows-pre-sync-2026-06-04" -m "Windows state before divergent history sync"
```

#### Step 0.6: Push to origin

```powershell
git push origin main
git push origin windows-pre-sync-2026-06-04
```

#### Step 0.7: Verify push

```powershell
git log --oneline -5
git status
# Should show: clean working tree, HEAD = origin/main
```

---

### Phase 1: Fix SSH Access to VPS

The VPS currently has `git@github.com: Permission denied (publickey)`.

#### Option 1: Generate new SSH key on VPS (recommended)

```bash
# SSH into VPS (current method — password or existing session)
ssh guinevere@<VPS_IP>

# Generate new ED25519 key
ssh-keygen -t ed25519 -C "guinevere-vps-$(date +%Y%m%d)" -f ~/.ssh/id_ed25519_github -N ""

# Display public key
cat ~/.ssh/id_ed25519_github.pub
```

Then: Add the public key to GitHub → Settings → SSH and GPG keys → New SSH key.

```bash
# Test SSH connectivity
ssh -T git@github.com

# Expected: "Hi fazulfi! You've successfully authenticated..."
```

#### Option 2: Switch to HTTPS with Personal Access Token

```bash
# If SSH key addition isn't feasible
cd /home/guinevere/code/guinevere
git remote set-url origin https://github.com/fazulfi/guinevere.git

# Configure credential caching (optional, for PAT)
git config credential.helper 'cache --timeout=3600'
```

**Note:** Option 2 requires a GitHub Personal Access Token with `repo` scope. Prefer Option 1 (SSH key) for persistent access.

#### Option 3: Windows as SSH proxy (if direct SSH to VPS is broken too)

If you can't SSH into VPS at all:

1. Use existing open session on VPS (if available)
2. Or use VPS provider's web console/VNC
3. Once on VPS, run the Option 1 commands above

The `/home/guinevere/code/guinevere` directory is the sync target regardless of access method.

---

### Phase 2: Create VPS Backup

**CRITICAL — Do not skip.** This is the safety net for all subsequent operations.

```bash
# Run on VPS as guinevere user
cd /home/guinevere/code/guinevere

# Create timestamped backup
BACKUP_NAME="guinevere-pre-sync-$(date +%Y%m%d-%H%M%S)"
tar -czf "/home/guinevere/backups/${BACKUP_NAME}.tar.gz" \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='*.egg-info' \
  .

# Also capture git state separately
git log --oneline --all > "/home/guinevere/backups/${BACKUP_NAME}-git-log.txt"
git diff > "/home/guinevere/backups/${BACKUP_NAME}-git-diff.patch"
git status > "/home/guinevere/backups/${BACKUP_NAME}-git-status.txt"
git stash list > "/home/guinevere/backups/${BACKUP_NAME}-git-stash.txt"
cp -r .git "/home/guinevere/backups/${BACKUP_NAME}-git-dir" 2>/dev/null || echo "Git dir backup skipped (use reflog)"

# Verify backup
ls -lh "/home/guinevere/backups/${BACKUP_NAME}.tar.gz"
tar -tzf "/home/guinevere/backups/${BACKUP_NAME}.tar.gz" | head -50
echo "Backup size: $(du -sh /home/guinevere/backups/${BACKUP_NAME}.tar.gz | cut -f1)"
```

---

### Phase 3: Reset VPS to Origin/Main

```bash
# Run on VPS as guinevere user
cd /home/guinevere/code/guinevere

# Step 3.1: Save current HEAD for reflog reference
OLD_HEAD=$(git rev-parse HEAD)
echo "Pre-reset HEAD: $OLD_HEAD" > /home/guinevere/backups/pre-reset-head.txt

# Step 3.2: Fetch from origin (SSH must be fixed)
git fetch origin

# Step 3.3: Verify what we're about to reset to
echo "=== Current VPS HEAD ==="
git log --oneline -3
echo ""
echo "=== Origin HEAD ==="
git log --oneline -3 origin/main
echo ""
echo "=== Divergence ==="
echo "VPS is $(git rev-list --count origin/main..HEAD) commits ahead of origin"
echo "Origin is $(git rev-list --count HEAD..origin/main) commits ahead of VPS"

# Step 3.4: Hard reset to origin/main
git reset --hard origin/main

# Step 3.5: Clean untracked files EXCEPT directories we'll restore
# DO NOT delete monitoring/, .hermes/, or docs/setup-evidence/ — those are in the backup
git clean -fd -e monitoring/ -e .hermes/ -e docs/setup-evidence/ -e audit-reports/

# Step 3.6: Verify reset
git status
git log --oneline -5
# Should show: HEAD = origin/main, clean working tree
```

**⚠️ IMPORTANT:** The `git reset --hard` discards the divergent commit `0497210`. The `git clean -fd` removes untracked files that overlap with tracked origin content. The `-e` flags preserve `monitoring/`, `.hermes/`, `docs/setup-evidence/`, and `audit-reports/` because they contain unique VPS content.

**What gets removed by `git clean` (and WHY it's OK):**
- `src/discord/` untracked files → origin has tracked versions
- `src/hermes/` untracked files → origin has tracked versions + Windows committed safety_plugin.py
- `src/hermes_plugins/` untracked → Windows committed 32-file organized plugin suite
- `systemd/` untracked services → origin has 7 tracked services + Windows committed shadow-monitor
- `tests/hermes/` untracked tests → origin has 2 tracked + Windows committed test_safety_plugin.py
- `src/core/`, `src/loops/`, `src/mcp/` etc. → all tracked in origin with complete implementation

---

### Phase 4: Restore VPS-Unique Assets from Backup

```bash
# Run on VPS as guinevere user
cd /home/guinevere/code/guinevere
BACKUP_TARBALL=$(ls -t /home/guinevere/backups/guinevere-pre-sync-*.tar.gz | head -1)
echo "Restoring from: $BACKUP_TARBALL"

# Step 4.1: Restore monitoring/ — CRITICAL
tar -xzf "$BACKUP_TARBALL" monitoring/
echo "Restored monitoring/ ($(find monitoring/ -type f | wc -l) files)"

# Step 4.2: Restore .hermes/plugins/ — HIGH
tar -xzf "$BACKUP_TARBALL" .hermes/plugins/
echo "Restored .hermes/plugins/ ($(find .hermes/plugins/ -type f | wc -l) files)"

# Step 4.3: Restore VPS evidence directories — LOW
tar -xzf "$BACKUP_TARBALL" docs/setup-evidence/ --keep-newer-files
echo "Restored docs/setup-evidence/ (VPS evidence merged)"

# Step 4.4: Restore audit reports — LOW
tar -xzf "$BACKUP_TARBALL" audit-reports/ --keep-newer-files 2>/dev/null || echo "No audit-reports/ in backup (skipped)"

# Step 4.5: Check for VPS-unique scripts
tar -xzf "$BACKUP_TARBALL" scripts/ --keep-newer-files
echo "Restored scripts/ (merged, new files preserved)"

# Step 4.6: Compare VPS src/hermes/ with current (Windows) version
# The VPS hermes files were cleaned. Check backup for VPS-unique files.
echo "=== Checking for VPS-unique hermes files in backup ==="
tar -tzf "$BACKUP_TARBALL" | grep "^src/hermes/" | grep -v "/$"
# If VPS had safety_plugin.py and it differs from the Windows version now in tracked:
#   tar -xzf "$BACKUP_TARBALL" src/hermes/safety_plugin.py
#   mv src/hermes/safety_plugin.py src/hermes/safety_plugin_vps_backup.py
# Then manually diff and merge.

# Step 4.7: Restore any VPS-specific production configs
# Compare key config files that may have VPS-specific paths
echo "=== Production config files to check ==="
for config_file in pyproject.toml src/core/config/__init__.py src/core/main.py; do
  echo "--- Checking $config_file ---"
  tar -xzf "$BACKUP_TARBALL" "$config_file" -O 2>/dev/null | head -5
done
# Performed as dry-run comparison. If paths differ, extract and manually merge.

echo ""
echo "=== Restoration Complete ==="
git status
```

---

### Phase 5: Commit and Push VPS-Unique Assets

```bash
# Run on VPS as guinevere user
cd /home/guinevere/code/guinevere

# Step 5.1: Stage VPS-unique assets
git add monitoring/
git add .hermes/plugins/

# Step 5.2: Stage any VPS-specific configs (if modified during restore)
# Example: if VPS had different config paths
# git add src/core/config/__init__.py

# Step 5.3: Check what's staged
git diff --cached --stat

# Step 5.4: Commit
git commit -m "feat(ops): VPS monitoring stack, Hermes runtime plugins, and production configs

- Full monitoring stack (Prometheus, Grafana, Loki, Alertmanager, Promtail, exporters)
- Hermes runtime plugins (.hermes/plugins/)
- VPS-specific production configurations"

# Step 5.5: Push to origin
git push origin main

# Step 5.6: Verify push
git log --oneline -3
echo "VPS HEAD: $(git rev-parse HEAD)"
```

---

### Phase 6: Windows Pull and Final Verification

```bash
# Run from Windows (C:\Users\faizz\guinevere)
git fetch origin
git pull origin main

# Verify convergence
echo "=== Windows HEAD ==="
git rev-parse HEAD
git log --oneline -5
```

Then on VPS:

```bash
# Run on VPS
cd /home/guinevere/code/guinevere
echo "=== VPS HEAD ==="
git rev-parse HEAD
git log --oneline -5
```

**Both should show the same HEAD commit.**

---

## 4. Safety Checks

### 4.1 Pre-Operation Checklist

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Windows working tree clean before sync | `git status` | "nothing to commit, working tree clean" |
| 2 | Windows HEAD = origin/main | `git rev-parse HEAD && git rev-parse origin/main` | Same hash |
| 3 | VPS backup tarball exists and non-empty | `ls -lh /home/guinevere/backups/guinevere-pre-sync-*.tar.gz` | File > 1MB |
| 4 | VPS SSH to GitHub working | `ssh -T git@github.com` | "Hi fazulfi!" |
| 5 | VPS can fetch origin | `git fetch origin` | No errors |
| 6 | VPS services stopped (optional/safer) | `sudo systemctl stop guinevere-*` | Services stopped |
| 7 | Backup git-log.txt contains old HEAD | `grep "0497210" /home/guinevere/backups/*-git-log.txt` | Match found |
| 8 | Disk space for backup (2x working tree) | `df -h /home/guinevere` | >2GB free |

### 4.2 Backup Verification Commands

```bash
# On VPS
BACKUP_TARBALL=$(ls -t /home/guinevere/backups/guinevere-pre-sync-*.tar.gz | head -1)

# 1. Check tarball integrity
tar -tzf "$BACKUP_TARBALL" > /dev/null && echo "Tarball integrity: OK" || echo "Tarball integrity: CORRUPT!"

# 2. Check key directories exist in backup
echo "=== Key directories in backup ==="
tar -tzf "$BACKUP_TARBALL" | grep "^monitoring/" | head -5
tar -tzf "$BACKUP_TARBALL" | grep "^\.hermes/plugins/" | head -5

# 3. Check file counts
echo "monitoring files: $(tar -tzf "$BACKUP_TARBALL" | grep "^monitoring/" | grep -v "/$" | wc -l)"
echo ".hermes/plugins files: $(tar -tzf "$BACKUP_TARBALL" | grep "^\.hermes/plugins/" | grep -v "/$" | wc -l)"

# 4. Check backup size
echo "Backup size: $(du -sh "$BACKUP_TARBALL" | cut -f1)"
```

### 4.3 Rollback Procedure

If anything goes wrong during Phase 3 (reset) or Phase 4 (restore):

```bash
# On VPS — COMPLETE ROLLBACK
cd /home/guinevere/code/guinevere
BACKUP_TARBALL=$(ls -t /home/guinevere/backups/guinevere-pre-sync-*.tar.gz | head -1)

# 1. Restore git state to pre-reset HEAD
OLD_HEAD=$(cat /home/guinevere/backups/pre-reset-head.txt)
git reset --hard "$OLD_HEAD"

# 2. Restore all files from backup
tar -xzf "$BACKUP_TARBALL" --overwrite

# 3. Verify rollback
git log --oneline -3
git status
# Should match pre-sync state (divergent commit + untracked files present)
```

If after Phase 5 (push) something goes wrong but origin is still clean:

```bash
# On VPS — PARTIAL ROLLBACK (undo last commit only)
git reset --soft HEAD~1        # Undo commit, keep files staged
# OR
git reset --hard HEAD~1        # Undo commit, discard changes
# Then redo from Phase 4
```

If origin needs to be rolled back (last resort):

```bash
# On Windows (has direct push access)
git push origin +HEAD~1:main   # Force push previous commit
# Then redo VPS sync
```

### 4.4 Service Health Check Commands

After sync is complete, verify services on VPS:

```bash
# On VPS
# 1. Check systemd service status
systemctl status guinevere-discord guinevere-loops guinevere-mcp guinevere-monitoring guinevere-obscura guinevere-scheduler guinevere-surveillance guinevere-shadow-monitor

# 2. Check if services can start (if they were stopped)
sudo systemctl start guinevere-discord
systemctl is-active guinevere-discord

# 3. Check PostgreSQL
sudo -u postgres psql -c "SELECT 1;" && echo "PostgreSQL: OK"

# 4. Check Redis
redis-cli PING && echo "Redis: OK"

# 5. Check monitoring stack
curl -s http://localhost:9090/-/healthy && echo "Prometheus: OK" || echo "Prometheus: DOWN"
curl -s http://localhost:3000/api/health && echo "Grafana: OK" || echo "Grafana: DOWN"
curl -s http://localhost:3100/ready && echo "Loki: OK" || echo "Loki: DOWN"
curl -s http://localhost:9093/-/healthy && echo "Alertmanager: OK" || echo "Alertmanager: DOWN"

# 6. Check Discord bot (if running)
systemctl is-active guinevere-discord && echo "Discord bot: RUNNING" || echo "Discord bot: STOPPED"

# 7. Check hermes runtime
ls -la /home/guinevere/code/guinevere/.hermes/plugins/
# Verify plugin count matches expected
```

---

## 5. Risk Assessment

### 5.1 Data Loss Scenarios and Mitigations

| Scenario | Likelihood | Impact | Mitigation | Recovery |
|----------|-----------|--------|------------|----------|
| VPS backup tarball corrupted | Low | **CRITICAL** — no fallback for VPS unique assets | Run `tar -tzf` integrity check before reset | Re-create from running filesystem (files not yet deleted at that point) |
| `monitoring/` not fully restored | Low | **HIGH** — monitoring stack broken | Verify file count after restore against backup file count | Re-extract from tarball; tarball is verified pre-reset |
| `.hermes/plugins/` not fully restored | Low | **MEDIUM** — Hermes runtime degraded | Verify file count after restore | Re-extract from tarball |
| VPS production configs overwritten by origin | Medium | **MEDIUM** — services use wrong paths | Inspect `pyproject.toml`, `src/core/config/__init__.py`, `src/core/main.py` from backup vs current | Manual diff and re-apply VPS-specific config values |
| VPS `bot.py` had production-specific tokens/paths | Low | **HIGH** — Discord bot can't start | Compare backup `src/discord/bot.py` with origin version; extract token/path differences | Re-apply from backup diff |
| SSH key generation fails | Low | **MEDIUM** — blocked VPS sync | Fallback to HTTPS + PAT (Option 2); or use VPS console | Switch remote URL method |
| `git clean -fd` removes more than intended | Low | **HIGH** — lost files | `-e` flags protect key directories; backup exists | Re-extract from tarball |
| Windows push fails (network/auth) | Low | **LOW** — just retry | HTTPS remote is working; retry with `git push` | Retry; check GitHub token expiry |

### 5.2 Service Disruption Risks

| Service | Risk | Downtime Estimate | Mitigation |
|---------|------|-------------------|------------|
| Discord bot | **MEDIUM** — `bot.py` may need config adjustment post-sync | 5-15 minutes | Compare backup `bot.py` with origin before restart |
| Agent loop | **LOW** — core loop files are in tracked origin, identical | 0-5 minutes | Loop restarts cleanly from tracked files |
| Monitoring stack | **MEDIUM** — configs reference VPS paths; monitoring is VPS-unique | 10-30 minutes | Restore from backup; verify Prometheus targets, Grafana dashboards, Loki config |
| PostgreSQL | **NONE** — no schema changes, DB is external to git | 0 minutes | Not affected by git operations |
| Redis | **NONE** — no config changes | 0 minutes | Not affected by git operations |
| Hermes runtime | **MEDIUM** — plugin paths may shift | 5-15 minutes | Verify `.hermes/plugins/` count and structure after restore |

### 5.3 Estimated Downtime

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Windows commit + push | 2-3 minutes | 3 min |
| Phase 1: SSH fix | 5-10 minutes | 13 min |
| Phase 2: VPS backup | 1-3 minutes (depends on size) | 16 min |
| Phase 3: Git reset + clean | 30 seconds | 16.5 min |
| Phase 4: Restore assets | 1-2 minutes | 18.5 min |
| Phase 5: Commit + push | 1 minute | 19.5 min |
| Phase 6: Windows pull + verify | 1 minute | 20.5 min |
| Service restart + health check | 5-15 minutes | 35.5 min |

**Total estimated downtime: 20-35 minutes** (excluding SSH troubleshooting time)

### 5.4 What Could Go Wrong and Recovery

| Problem | Symptom | Root Cause | Recovery |
|---------|---------|------------|----------|
| Discord bot can't start | `systemctl status guinevere-discord` shows failed | `bot.py` had VPS-specific token path | Diff backup `bot.py` vs origin; re-apply path config |
| Monitoring dashboards empty | Grafana shows no data | Prometheus config paths changed | Check `monitoring/prometheus/prometheus.yml` targets; verify exporters running |
| Hermes plugin not found | Hermes error log | Plugin directory path mismatch | Check `.hermes/plugins/` file count vs expected; verify `hermes-config/config.yaml` paths |
| Windows pull has merge conflict | `git pull` fails | Local Windows changes not committed before pulling VPS updates | `git stash` → `git pull` → `git stash pop`; resolve conflicts |
| VPS can't push to origin | `git push` fails | SSH key not fully configured | Verify `ssh -T git@github.com`; retry `git push` |
| Services fail to restart | `systemctl start` fails | Config files reference old paths | Compare backup configs with current; update paths; `systemctl daemon-reload` |

---

## 6. Post-Sync Verification

### 6.1 Git State Verification

**On VPS:**

```bash
cd /home/guinevere/code/guinevere

echo "=== VPS Git State ==="
echo "HEAD: $(git rev-parse HEAD)"
echo "Branch: $(git branch --show-current)"
echo ""
echo "=== Commit Log ==="
git log --oneline -7
echo ""
echo "=== Working Tree ==="
git status
echo ""
echo "=== Remote Status ==="
git remote -v
git fetch origin
echo "Ahead: $(git rev-list --count origin/main..HEAD)"
echo "Behind: $(git rev-list --count HEAD..origin/main)"
```

**On Windows:**

```powershell
cd C:\Users\faizz\guinevere

Write-Host "=== Windows Git State ==="
Write-Host "HEAD: $(git rev-parse HEAD)"
Write-Host "Branch: $(git branch --show-current)"
Write-Host ""
Write-Host "=== Commit Log ==="
git log --oneline -7
Write-Host ""
Write-Host "=== Working Tree ==="
git status
Write-Host ""
Write-Host "=== Remote Status ==="
git fetch origin
Write-Host "Ahead: $(git rev-list --count origin/main..HEAD)"
Write-Host "Behind: $(git rev-list --count HEAD..origin/main)"
```

**Convergence check — both sides MUST match:**

```bash
# VPS HEAD = Windows HEAD = origin/main
# Run on both and compare hashes
git rev-parse HEAD
```

### 6.2 Service Health Checks

```bash
# On VPS — full service health check
echo "=== Service Status ==="
systemctl is-active guinevere-discord
systemctl is-active guinevere-loops
systemctl is-active guinevere-mcp
systemctl is-active guinevere-monitoring
systemctl is-active guinevere-obscura
systemctl is-active guinevere-scheduler
systemctl is-active guinevere-surveillance
systemctl is-active guinevere-shadow-monitor

echo ""
echo "=== Database Connectivity ==="
sudo -u postgres psql -c "SELECT version();" | head -3
redis-cli PING

echo ""
echo "=== Monitoring Endpoints ==="
curl -s -o /dev/null -w "Prometheus: %{http_code}\n" http://localhost:9090/-/healthy
curl -s -o /dev/null -w "Grafana: %{http_code}\n" http://localhost:3000/api/health
curl -s -o /dev/null -w "Loki: %{http_code}\n" http://localhost:3100/ready
curl -s -o /dev/null -w "Alertmanager: %{http_code}\n" http://localhost:9093/-/healthy

echo ""
echo "=== Hermes Runtime ==="
ls -la /home/guinevere/code/guinevere/.hermes/plugins/ | head -10
echo "Plugin count: $(find /home/guinevere/code/guinevere/.hermes/plugins/ -type f | wc -l)"

echo ""
echo "=== Recent Service Logs ==="
journalctl -u guinevere-discord --since "5 minutes ago" --no-pager | tail -20
```

### 6.3 Smoke Test Commands

```bash
# On VPS — quick functional smoke tests
# 1. Verify Python imports work
cd /home/guinevere/code/guinevere
python3 -c "import sys; sys.path.insert(0, 'src'); from core.main import main; print('Core import: OK')"

# 2. Verify monitoring configs parse
python3 -c "import yaml; yaml.safe_load(open('monitoring/prometheus/prometheus.yml')); print('Prometheus config: OK')"

# 3. Verify Hermes config exists
test -f hermes-config/SOUL.md && echo "SOUL.md: OK" || echo "SOUL.md: MISSING"
test -f hermes-config/config.yaml && echo "config.yaml: OK" || echo "config.yaml: MISSING"

# 4. Verify safety plugin
test -f src/hermes/safety_plugin.py && echo "safety_plugin.py: OK" || echo "safety_plugin.py: MISSING"

# 5. Verify shadow pipeline files
test -f src/discord/shadow_monitor.py && echo "shadow_monitor.py: OK"
test -f src/discord/shadow_pipeline.py && echo "shadow_pipeline.py: OK"

# 6. Verify systemd units
systemctl list-unit-files | grep guinevere
```

### 6.4 Windows-Side Verification

```powershell
# On Windows
cd C:\Users\faizz\guinevere

# Verify all expected directories exist
$dirs = @("monitoring", ".hermes", "hermes-config", "src\hermes", "src\hermes_plugins")
foreach ($d in $dirs) {
    $exists = Test-Path $d
    Write-Host "$d : $(if ($exists) { 'OK' } else { 'MISSING' })"
}

# Verify key files
$files = @("hermes-config\SOUL.md", "hermes-config\config.yaml", "src\hermes\safety_plugin.py", "src\discord\shadow_pipeline.py")
foreach ($f in $files) {
    $exists = Test-Path $f
    Write-Host "$f : $(if ($exists) { 'OK' } else { 'MISSING' })"
}
```

---

## 7. Execution Checklist (Quick Reference)

### ☐ Phase 0 — Windows Preparation
- [ ] 0.1: Verify Windows git state (`git status`, `git log --oneline -5`)
- [ ] 0.2: Commit `bot.py` and `conversational_handler.py`
- [ ] 0.3: Commit Hermes implementation files
- [ ] 0.4: Commit remaining non-conflicting untracked files
- [ ] 0.5: Tag pre-sync state (`windows-pre-sync-2026-06-04`)
- [ ] 0.6: Push to origin (`git push origin main`)
- [ ] 0.7: Verify push (clean working tree, HEAD = origin/main)

### ☐ Phase 1 — Fix SSH
- [ ] 1.1: Generate new SSH key on VPS (`ssh-keygen -t ed25519`)
- [ ] 1.2: Add public key to GitHub SSH keys
- [ ] 1.3: Test connectivity (`ssh -T git@github.com`)
- [ ] 1.4: Test `git fetch origin` on VPS

### ☐ Phase 2 — VPS Backup
- [ ] 2.1: Create timestamped tarball (`tar -czf`)
- [ ] 2.2: Save git log, diff, status
- [ ] 2.3: Verify tarball integrity (`tar -tzf`)
- [ ] 2.4: Verify backup size and key directories

### ☐ Phase 3 — VPS Reset
- [ ] 3.1: Save pre-reset HEAD to file
- [ ] 3.2: Fetch from origin
- [ ] 3.3: Compare VPS vs origin divergence
- [ ] 3.4: Hard reset to origin/main
- [ ] 3.5: Clean untracked (except protected dirs)
- [ ] 3.6: Verify reset (HEAD = origin/main)

### ☐ Phase 4 — Restore VPS-Unique Assets
- [ ] 4.1: Restore `monitoring/`
- [ ] 4.2: Restore `.hermes/plugins/`
- [ ] 4.3: Restore evidence directories (merge)
- [ ] 4.4: Restore audit reports (merge)
- [ ] 4.5: Restore scripts (merge)
- [ ] 4.6: Compare VPS `src/hermes/` with current (file-level diff if needed)
- [ ] 4.7: Check for VPS-specific production configs

### ☐ Phase 5 — Commit and Push VPS Assets
- [ ] 5.1: Stage `monitoring/` and `.hermes/plugins/`
- [ ] 5.2: Stage any VPS-specific configs
- [ ] 5.3: Review staged changes (`git diff --cached --stat`)
- [ ] 5.4: Commit with descriptive message
- [ ] 5.5: Push to origin
- [ ] 5.6: Verify push

### ☐ Phase 6 — Windows Pull and Verify
- [ ] 6.1: Windows `git pull origin main`
- [ ] 6.2: Verify Windows HEAD matches VPS HEAD
- [ ] 6.3: Full post-sync verification (see Section 6)

### ☐ Post-Sync
- [ ] Restart VPS services (`sudo systemctl start guinevere-*`)
- [ ] Run service health checks (Section 6.2)
- [ ] Run smoke tests (Section 6.3)
- [ ] Windows-side verification (Section 6.4)
- [ ] Verify both HEAD hashes match

---

## 8. Appendices

### A. Expected Final Commit Structure After Sync

```
(origin/main)
│
├── <VPS assets commit>        "feat(ops): VPS monitoring stack, Hermes runtime plugins..."
│   └── Adds: monitoring/, .hermes/plugins/, VPS configs
│
├── <Windows evidence commit>  "docs: Phase 1-3 research reports..."
│   └── Adds: research-reports/phase-*, evidence/phase-*, docs/setup-evidence/*
│
├── <Windows hermes commit>    "feat(hermes): Phase 1-2 safety plugin..."
│   └── Adds: src/hermes/safety_plugin.py, hermes-config/, shadow pipeline, plugin suite
│
├── <Windows refactor commit>  "feat(hermes): Phase 1-2 bot refactor..."
│   └── Modifies: src/discord/bot.py, src/discord/conversational_handler.py
│
├── ecfa0eb                    "docs: Hermes migration planning complete"
├── f6912b2                    "refactor(phases): restructure P9-P22"
├── 92fee59                    "chore: add repository secret safeguards" (common ancestor)
└── 6a793e6                    "chore: initial repo structure"
```

### B. Directories Protected During `git clean`

| Directory | Reason | Protected By |
|-----------|--------|--------------|
| `monitoring/` | VPS-unique monitoring stack | `-e monitoring/` |
| `.hermes/` | VPS Hermes runtime plugins | `-e .hermes/` |
| `docs/setup-evidence/` | VPS evidence files | `-e docs/setup-evidence/` |
| `audit-reports/` | VPS audit reports | `-e audit-reports/` |

### C. Key Decision Log

| Decision | Rationale | Authority |
|----------|-----------|-----------|
| Windows/origin = authoritative | B3 proved all 24 VPS-modified files have more complete versions in origin | B3 report |
| Discard VPS commit `0497210` | Zero unique content; all files superseded by origin | B3 Section 2.2 |
| Hard reset over merge | Merge creates 24 conflicts with zero benefit | Strategy C analysis |
| Backup-first approach | Non-negotiable safety requirement | AGENTS.md BLOCKING rules |
| Separable phases | Windows prep can proceed immediately; VPS sync waits for SSH | Independence analysis |

---

## 9. Footer

| Field | Value |
|-------|-------|
| Strategy | Strategy B — Windows authoritative, VPS reset + restore |
| Estimated time | 20-35 minutes (excluding SSH troubleshooting) |
| Risk level | MEDIUM (well-mitigated by backup) |
| Rollback available | ✅ Yes — backup tarball + git reflog |
| Service disruption | 20-35 minutes (services stopped during sync) |
| Next step | Execute Phase 0 (Windows preparation) immediately |
| Blocking dependency | SSH fix required before Phase 1-5 (VPS work) |