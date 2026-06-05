# Windows Git State Report — Guinevere Project

**Date**: 2026-06-05  
**Machine**: Windows (PowerShell 5.1)  
**Repository**: C:\Users\faizz\guinevere  
**Remote**: https://github.com/fazulfi/guinevere.git

---

## 1. Current Branch

```
main
```

---

## 2. `git status`

```
On branch main
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   stepprompts/StepPrompts.md

Untracked files:
  (use "git add <file>..." to include in what will be committed)
        docs/setup-evidence/phase-3/audit-architecture-v1.1.md
        docs/setup-evidence/phase-3/audit-safety-v1.1.md
        research-reports/git-sync/
        research-reports/stepprompts-audit/
        scripts/_wp.py

no changes added to commit (use "git add" and/or "git commit -a")
```

---

## 3. Last 20 Commits (Local HEAD)

```
66abd4d docs: Hermes migration evidence + research reports
3110f2a feat: Hermes config (SOUL.md, hooks, safety plugin, env template)
871b72a feat: Hermes Phase 1 safety plugin + shadow pipeline + 35 Hermes plugins
ecfa0eb docs: Hermes migration planning complete
f6912b2 refactor(phases): restructure P9-P22
92fee59 chore: add repository secret safeguards
6a793e6 chore: initial repo structure
```

Local HEAD has **7 total commits** (all 7 shown above).

---

## 4. All Branches (Local + Remote)

### Local

```
* main
```

### Remote (`remotes/origin/`)

```
HEAD -> origin/main
main
feat/guinevere/broadcast
feat/guinevere/database
feat/guinevere/docker
feat/guinevere/hermes-backup
feat/guinevere/hermes-cutover
feat/guinevere/hermes-external-watch
feat/guinevere/hermes-hardening
feat/guinevere/hermes-incident-digest
feat/guinevere/hermes-memory
feat/guinevere/hermes-monitoring-tools
feat/guinevere/hermes-ops-tools
feat/guinevere/hermes-production-activation-start
feat/guinevere/hermes-report-files
feat/guinevere/hermes-runtime
feat/guinevere/hermes-safety
feat/guinevere/hermes-schedules
feat/guinevere/hermes-security-scanner
feat/guinevere/hermes-soul
feat/guinevere/hermes-telegram
feat/guinevere/monitoring-tools
feat/guinevere/proactive
feat/guinevere/react-engine
feat/guinevere/server-tools
feat/guinevere/telegram
test/guinevere-hermes-audit
test/guinevere-natural-behavior
```

**Total**: 1 local branch, 28 remote branches.

---

## 5. Remote Configuration

```
origin  https://github.com/fazulfi/guinevere.git (fetch)
origin  https://github.com/fazulfi/guinevere.git (push)
```

Single remote `origin` using HTTPS.

---

## 6. Divergence Analysis

### `git fetch origin`

No output — already up to date. Fetch completed silently (no new data from remote).

### `git log --oneline HEAD...origin/main --left-right`

```
< 66abd4d docs: Hermes migration evidence + research reports
< 3110f2a feat: Hermes config (SOUL.md, hooks, safety plugin, env template)
< 871b72a feat: Hermes Phase 1 safety plugin + shadow pipeline + 35 Hermes plugins
```

**All `<` entries are local-only.** No `>` entries (remote has nothing local doesn't have).

### Commits on Local Not on Remote (`origin/main..HEAD`)

```
66abd4d docs: Hermes migration evidence + research reports
3110f2a feat: Hermes config (SOUL.md, hooks, safety plugin, env template)
871b72a feat: Hermes Phase 1 safety plugin + shadow pipeline + 35 Hermes plugins
```

### Commits on Remote Not on Local (`HEAD..origin/main`)

```
(empty — no commits)
```

### `origin/main` Last 20 Commits

```
ecfa0eb docs: Hermes migration planning complete
f6912b2 refactor(phases): restructure P9-P22
92fee59 chore: add repository secret safeguards
6a793e6 chore: initial repo structure
```

Only 4 commits exist on origin/main total.

### Divergence Verdict

| Metric | Value |
|---|---|
| **Local vs Remote** | **Local is AHEAD by 3 commits** |
| **Remote vs Local** | Remote is BEHIND — 0 commits ahead of local |
| **Common ancestor** | `ecfa0eb` |
| **Sync status** | Local main has 3 unpushed Hermes-related commits |

Windows is **not behind** the remote. It has work that has not been pushed:

1. `871b72a` — Hermes Phase 1 safety plugin + shadow pipeline + 35 Hermes plugins
2. `3110f2a` — Hermes config (SOUL.md, hooks, safety plugin, env template)
3. `66abd4d` — Hermes migration evidence + research reports

---

## 7. Uncommitted Changes

### Porcelain Status

```
 M stepprompts/StepPrompts.md
?? docs/setup-evidence/phase-3/audit-architecture-v1.1.md
?? docs/setup-evidence/phase-3/audit-safety-v1.1.md
?? research-reports/git-sync/
?? research-reports/stepprompts-audit/
?? scripts/_wp.py
```

| Status | File/Directory | Type |
|---|---|---|
| ` M` (modified, not staged) | `stepprompts/StepPrompts.md` | Modified tracked file |
| `??` (untracked) | `docs/setup-evidence/phase-3/audit-architecture-v1.1.md` | New file |
| `??` (untracked) | `docs/setup-evidence/phase-3/audit-safety-v1.1.md` | New file |
| `??` (untracked) | `research-reports/git-sync/` | New directory |
| `??` (untracked) | `research-reports/stepprompts-audit/` | New directory |
| `??` (untracked) | `scripts/_wp.py` | New file |

### Diff Stat vs HEAD

```
 stepprompts/StepPrompts.md | 5 +++++
 1 file changed, 5 insertions(+)
```

### Diff Content (`stepprompts/StepPrompts.md`)

Per the `git diff HEAD -- stepprompts/StepPrompts.md` output, the file has 5 additions across 5 separate lines, all of the form:

```
<!-- ⚠️ STALE: hermes-agent PyPI references are obsolete per ADR-035. Hermes now = NousResearch fork. -->
```

These are annotation comments inserted into the StepPrompts.md file marking outdated `hermes-agent` pip installation references. The annotations appear at lines:
- After `hermes-agent` in a `uv pip install` block
- Before `uv pip install hermes-agent` 
- Before `git clone https://github.com/NousResearch/hermes-agent.git`
- Before `python -c "import hermes_agent; print(hermes_agent.__version__)"`
- Before the Verification checklist

---

## 8. Stashes

```
(no output)
```

**No stashed changes.**

---

## 9. Reflog (Last 10)

```
66abd4d HEAD@{0}: commit: docs: Hermes migration evidence + research reports
3110f2a HEAD@{1}: commit: feat: Hermes config (SOUL.md, hooks, safety plugin, env template)
871b72a HEAD@{2}: commit: feat: Hermes Phase 1 safety plugin + shadow pipeline + 35 Hermes plugins
ecfa0eb HEAD@{3}: rebase (finish): returning to refs/heads/main
ecfa0eb HEAD@{4}: rebase (pick): docs: Hermes migration planning complete
f6912b2 HEAD@{5}: rebase (continue): refactor(phases): restructure P9-P22
92fee59 HEAD@{6}: pull --rebase origin main (start): checkout 92fee59d5cced04500bf27edb8cfccd9de0e050c
7fc188e HEAD@{7}: commit: docs: Hermes migration planning complete
1be7801 HEAD@{8}: Branch: renamed refs/heads/master to refs/heads/main
1be7801 HEAD@{10}: commit (initial): refactor(phases): restructure P9-P22
```

Notable reflog events:
- **HEAD@{6}**: A `pull --rebase origin main` operation was started from `92fee59`
- **HEAD@{5}-{3}**: Rebase operation that rewrote commits (including `f6912b2` and `ecfa0eb`)
- **HEAD@{8}**: Branch renamed from `master` to `main`
- **HEAD@{10}**: Initial commit `refactor(phases): restructure P9-P22`

---

## 10. Full Branch Graph (`--all --graph --oneline -30`)

```
* 66abd4d docs: Hermes migration evidence + research reports
* 3110f2a feat: Hermes config (SOUL.md, hooks, safety plugin, env template)
* 871b72a feat: Hermes Phase 1 safety plugin + shadow pipeline + 35 Hermes plugins
* ecfa0eb docs: Hermes migration planning complete
* f6912b2 refactor(phases): restructure P9-P22
* 92fee59 chore: add repository secret safeguards
* 6a793e6 chore: initial repo structure
* 24917bb test(guinevere): make Docker socket test portable
* 5cef9c9 feat(guinevere): add digest batching for proactive alerts
* 9414fc3 feat(guinevere): add incident timeline reconstruction
| * 824485d docs(guinevere): record Hermes external watch marker
| * 12682a2 feat(guinevere): schedule Hermes external watch
| * 7fe4bf1 feat(guinevere): add Hermes external watch tools
| * dfef32f feat(guinevere): schedule autonomous security scans
| * 8f7de49 docs(guinevere): record Hermes security scanner marker
| * 5593c0b test(guinevere): add security scanner coverage
| * b3947b5 feat(guinevere): add Hermes security scanner tools
| * 2d31e1e docs(guinevere): record Hermes backup restore marker
| * a0c0134 feat(guinevere): schedule Hermes backup drills
| * 92ad50c feat(guinevere): add Hermes backup tools
| | * efe69bf feat(guinevere): start Hermes production activation
| |/  
| * 4cac971 docs(guinevere): record Hermes security audit marker
| * 211a689 test(guinevere): complete Hermes security and integration audit
| * 9697d81 test(guinevere): add natural behavior regression suite
| * fb23f68 feat(guinevere): harden Hermes production runtime
|/  
| * 266b8d4 feat(guinevere): cut over Telegram ops to Hermes runtime
|/  
* fa0ccdc feat(guinevere): Hermes milestone complete — can act naturally
| * b6a2d7f feat(guinevere): schedule Hermes ops reports
| * 9794e07 feat(guinevere): configure persistent BudgeZen memory
| * 76383d4 feat(guinevere): enforce Hermes safety and approval policy
|/  
```

The graph reveals that commits on `main` below `6a793e6` (the initial commit as seen in the reflog) are reachable via the rebase but exist on feature branches. These commits (`24917bb`, `5cef9c9`, `9414fc3`, `fa0ccdc`) predate the branch rename/restructure and are part of the rebase-rewritten history.

Multiple feature branches exist on `origin` with unmerged work:
- `feat/guinevere/hermes-external-watch` (3 commits)
- `feat/guinevere/hermes-security-scanner` (4 commits)
- `feat/guinevere/hermes-backup` (3 commits)
- `feat/guinevere/hermes-production-activation-start` (1 commit, branched from hermes-hardening line)
- `test/guinevere-hermes-audit` (merges into hermes-hardening line)
- `test/guinevere-natural-behavior` (merges into hermes-hardening line)
- `feat/guinevere/hermes-hardening` (4 commits)
- `feat/guinevere/hermes-cutover` (1 commit)
- Various other Hermes feature branches

---

## 11. Local Git Config

```
core.repositoryformatversion=0
core.filemode=false
core.bare=false
core.logallrefupdates=true
core.symlinks=false
core.ignorecase=true
remote.origin.url=https://github.com/fazulfi/guinevere.git
remote.origin.fetch=+refs/heads/*:refs/remotes/origin/*
```

Note: `core.ignorecase=true` (Windows default), `core.filemode=false` (Windows), `core.symlinks=false` (Windows).

---

## 12. Summary — Windows State

| Aspect | Status |
|---|---|
| **Branch** | `main` |
| **Remote** | `origin` → `https://github.com/fazulfi/guinevere.git` |
| **Divergence** | **AHEAD of origin/main by 3 commits** (not behind) |
| **Unpushed commits** | 3 Hermes-related commits: safety plugin, SOUL config, migration evidence |
| **Uncommitted changes** | 1 modified file (`StepPrompts.md`), 5 untracked items |
| **Modified file** | `stepprompts/StepPrompts.md` — +5 lines (AD-035 stale annotations) |
| **Untracked files** | 3 files + 2 directories (audit evidence, git-sync report, stepprompts audit, `_wp.py`) |
| **Stashes** | None |
| **Feature branches** | 26 remote feature branches (all unmerged Hermes work) |
| **History** | 7 commits on `main`, rebase-rewritten from original `master` branch |
| **Rebase** | Yes — `pull --rebase origin main` at `HEAD@{6}`, branch renamed `master→main` at `HEAD@{8}` |

### Key Observations

1. **Windows is ahead, not behind.** The 3 unpushed commits represent the latest Hermes migration work done on Windows.

2. **Working tree has uncommitted changes.** The `StepPrompts.md` modifications are stale-reference annotations (`ADR-035`). The untracked files are audit reports, research outputs, and a Python script — none are git-ignored.

3. **Many unmerged feature branches on remote.** 26 feature branches exist on `origin` (all `feat/guinevere/*` and `test/guinevere-*`) that have not been merged into `main`. These represent various Hermes subsystem implementations.

4. **History underwent a rebase.** The reflog confirms the branch was rebased after pulling from origin, rewriting early commits. The master→main rename also occurred.

5. **CRLF warning.** Git warns that `stepprompts/StepPrompts.md` has LF line endings and will be converted to CRLF on next touch (Windows line-ending behavior).

---

## Appendix: Command Inventory

All commands executed read-only from `C:\Users\faizz\guinevere`:

| # | Command | Purpose |
|---|---|---|
| 1 | `git status` | Working tree status |
| 2 | `git log --oneline -20` | Last 20 commits on HEAD |
| 3 | `git branch -a` | All branches |
| 4 | `git remote -v` | Remote config |
| 5 | `git rev-parse --abbrev-ref HEAD` | Current branch |
| 6 | `git stash list` | Check stashes |
| 7 | `git reflog -10` | Recent reflog |
| 8 | `git fetch origin` | Fetch from remote |
| 9 | `git log --oneline HEAD...origin/main --left-right` | Divergence analysis |
| 10 | `git log --oneline origin/main..HEAD` | Local-only commits |
| 11 | `git log --oneline HEAD..origin/main` | Remote-only commits |
| 12 | `git status --porcelain` | Machine-readable status |
| 13 | `git diff --stat HEAD` | Diff summary |
| 14 | `git diff HEAD -- stepprompts/StepPrompts.md` | Detailed diff of modified file |
| 15 | `git log --oneline origin/main -20` | Remote main history |
| 16 | `git log --all --oneline --graph -30` | Full branch graph |
| 17 | `git config --local --list` | Local git config |

**No mutations performed.** All commands are read-only.