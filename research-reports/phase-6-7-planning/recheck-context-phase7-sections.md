# Recheck: Phase 7 Plan Sections 7.6–7.9 Gap Analysis & Required Content Specification

> **Purpose**: Audit the structural gap in `batch-plan-phase-7.md` where Sections 8–11 (Steps 7.6–7.9) are declared in ToC but absent from body. Specify exact required content so auditors can PASS.
> **Sources**: batch-plan-phase-7.md, audit-71-test-completeness.md, audit-72-security-posture.md, audit-73-documentation.md, 06-deprecated-files.md, 07-adr029-tests.md
> **Date**: 2026-06-05
> **Status**: ACTIVE — Planning fix specification only

---

## 1. Exact Insertion Location

The missing sections must be inserted in `docs/setup-evidence/hermes-migration/batch-plan-phase-7.md` **after line 921** (end of Section 7 — Step 7.5: Security Audit, which ends with `---`) and **before line 924** (start of Section 12 — Runbook per Scenario, which begins with `## 12. Section: Runbook per Scenario`).

Current file state (lines 920–924):
```markdown

---

## 12. Section: Runbook per Scenario
```

The gap spans **4 sections** (Sections 8, 9, 10, 11) corresponding to Steps **7.6, 7.7, 7.8, 7.9**.

---

## 2. Required Subsections Per Step

Each missing section MUST follow the same structure as Steps 7.1–7.5 (lines 139–921). Every step requires:

| Subsection | Required | Example from existing steps |
|---|---|---|
| **Header**: `## N. Step 7.X: Title` | YES | `## 8. Step 7.6: Deprecated Files Cleanup` |
| **Duration / Risk / Depends / Parallel with** | YES | `**Duration**: 2 hours` / `**Risk**: MEDIUM` / `**Depends**: Steps 7.1, 7.5` / `**Parallel with**: None` |
| **X.1 Pre-conditions** (checklist items) | YES | `### 8.1 Pre-conditions` with `- [ ]` items |
| **X.2 Sub-step** (commands) | YES | `### 8.2 Step 7.6.1: ...` with bash command blocks |
| **X.3 Verification** | YES | `### 8.3 Verification` with test commands |
| **X.4 On Failure** | YES (if applicable) | `On Failure:` with fallback/restore commands |
| **Evidence path** | YES | `Evidence: docs/setup-evidence/.../STEP-7.6/verification.md` |

### 2.1 Step 7.6: Deprecated Files Cleanup — Required Content

Extracted from `06-deprecated-files.md` Section 5 (the exact 5-step deprecated archive sequence):

**Duration**: 3 hours
**Risk**: HIGH (import breakage risk — R7-10, R7-11, R7-12)
**Depends**: Steps 7.1, 7.5 (24h stable pre-condition from §1.2)
**Parallel with**: None (sequential — must verify before next step)

#### Pre-conditions (7.6.1 Preparation):
1. `[ ]` 24h stable operation confirmed (pre-condition §1.2, line 64)
2. `[ ]` Step 7.1 regression suite PASS (import verification needed)
3. `[ ]` Step 7.5 security audit PASS (0 HIGH)
4. `[ ]` Git working tree clean (`git status --porcelain`)

#### Required Sub-Steps:

**7.6.1 — Pre-Deployment Code Migration**
- Migrate `command_categories` from `src/discord/commands.py` to `src/hermes_plugins/commands_high/help.py` or `src/core/constants.py`
- Remove `from .session_adapter import HermesSessionAdapter` from `src/hermes/__init__.py`
- Update docstrings in `src/hermes/session_adapter.py`, `src/discord/shadow_pipeline.py`, `src/discord/hermes_conversational.py` to remove `GuinevereBot`/`conversational_handler` references
- Commands: `grep -r "from src.discord.commands import" src/` to confirm zero remaining after migration; `python3 -c "import src.hermes; print('Hermes init OK')"`

**7.6.2 — Archive Deprecated Source Files**
- Create `deprecated/` directory structure
- Move (not delete, not copy): `src/discord/` → `deprecated/discord/` (8 files, ~2,554 lines)
- Move: `src/hermes/session_adapter.py` → `deprecated/hermes/session_adapter.py`
- Move: `src/hermes/memory_bridge.py` → `deprecated/hermes/memory_bridge.py`
- Move: `src/core/services/llm_router.py` → `deprecated/core/llm_router.py`
- Commands: `mkdir -p deprecated/{discord,hermes,core}` then `git mv src/discord/*.py deprecated/discord/` etc.
- **Total**: 11 files, ~3,216 lines (matches Gate G05 expectation of `>= 11` archived files)

**7.6.3 — Archive Obsolete Test Files**
- Move: `tests/discord/` → `deprecated/tests/discord/`
- Move: `tests/hermes/test_memory_bridge.py` → `deprecated/tests/test_memory_bridge.py`
- Update `tests/hermes/conftest.py` to remove session_adapter import prevention hacks

**7.6.4 — Archive Stale Documentation**
- Move `stepprompts/StepPrompts.md` → `stepprompts/archive/StepPrompts-v1.md`
- Archive `docs/setup-evidence/P2/` and `docs/setup-evidence/phase-3/` to `docs/setup-evidence/archive/`
- **Retain** `migrations/phase-3/004-hermes-memory-bridge-rbac.sql` (do NOT delete SQL migrations)

**7.6.5 — Post-Deletion Verification**
- Run: `python -m pytest tests/ -v --tb=short 2>&1 | tail -5` → exit 0, zero import errors
- Run: `python -c "import src.hermes; print('Hermes init OK')"` → clean init
- Run: `python -c "import src.discord.help"` → exit 0 (Gate G05 criterion — help.py must work after refactor)
- Run: `find deprecated/ -type f | wc -l` → `>= 11` (Gate G05 criterion)
- Run: `lsp_diagnostics src/` → zero `reportMissingImports` errors

#### On Failure:
- If import breaks: `git checkout -- src/` to restore from git, then fix migration before re-attempting
- If `help.py` breaks (R7-10): Restore `command_categories` inline in `help.py`, document as accepted tech debt
- If `hermes_conversational.py` breaks (R7-11): Restore bridge files from `deprecated/` immediately

#### Evidence:
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.6/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.6/archived-files-manifest.txt`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.6/import-verification.txt`

---

### 2.2 Step 7.7: ADR-029 Automated Tests — Required Content

Extracted from `07-adr029-tests.md` Sections 2–7 and `audit-71-test-completeness.md`.

**Duration**: 4 hours
**Risk**: MEDIUM
**Depends**: Steps 7.1, 7.6 (test files must exist after deprecated cleanup)
**Parallel with**: None

#### Pre-conditions:
1. `[ ]` Step 7.6 deprecated files cleanup PASS
2. `[ ]` pyproject.toml writable
3. `[ ]` `pytest-cov` installed (`pip list | grep pytest-cov`)

#### Required Sub-Steps:

**7.7.1 — Create `.coveragerc` or Add `[tool.coverage.run]` to `pyproject.toml`**
- Config must include: `source = ["src"]`, `omit = ["tests/*", "*/archive/*", "deprecated/*"]`, `fail_under = 70`
- Command: Write either `.coveragerc` file OR add `[tool.coverage.run]` section to `pyproject.toml`
- Verification: `python -m pytest tests/ --cov=src --cov-report=term-missing 2>&1 | grep "TOTAL"` → shows coverage percentage

**7.7.2 — Create `.guinevere/safety-critical-paths.yml`**
- Required by ADR-029 Section 3.2: glob patterns for safety-critical files
- Must include:
  ```yaml
  # safety-critical-paths.yml — ADR-029 Safety-Critical File Classification
  paths:
    - "src/persona/**"
    - "src/surveillance/**"
    - "src/memory/dnr.py"
    - "src/safety/**"
    - "src/hermes_plugins/safety/**"
    - "tests/**"
  ```
- Verification: `test -f .guinevere/safety-critical-paths.yml && echo "EXISTS"`

**7.7.3 — Create T1–T10 Test Files in `tests/integration/`**
- Required: Create `tests/integration/` directory with 10 dedicated test files:
  - `test_t1_basic_conversation.py` — Y4 persona response, < 30s, 10+ topics
  - `test_t2_multi_turn_memory.py` — cross-session memory recall, DNR exclusion
  - `test_t3_mcp_tools.py` — 16 tools respond, auth matrix enforced
  - `test_t4_hard_stop.py` — < 50ms detection, dual-layer redundancy
  - `test_t5_safe_mode.py` — D2–D4 distress, neutral responses
  - `test_t6_memory_recall.py` — 20 facts recall, 0 hallucination
  - `test_t7_slash_commands.py` — 35 commands registered
  - `test_t8_rituals.py` — 5x/day schedule, correct WIB timing
  - `test_t9_cost_tracking.py` — budget enforcement, Redis DB5
  - `test_t10_surveillance.py` — pipeline integrity, consent gate
- Verification: `python -m pytest tests/integration/test_t1_basic_conversation.py -v --tb=short 2>&1` (etc. for all 10)

**NOTE**: The existing `test_verification.py` (Step 7.1.4) should map V01–V30 to these T1–T10 tests, not duplicate them. Update Step 7.1.4 to reference T1–T10 test files explicitly.

**7.7.4 — Create `tests/safety/test_auto_rollback.py`**
- ADR-029 requires: automated git revert on test failure within 60 seconds
- Test must: (a) simulate a failing deployment, (b) trigger `git revert`, (c) verify completion < 60s, (d) verify Discord alert sent
- Verification: `python -m pytest tests/safety/test_auto_rollback.py -v --tb=short 2>&1` → PASS
- **Important**: This is a simulation test (uses a temporary branch/git clone, does NOT modify active deployment)

**7.7.5 — Generate Coverage Baseline + CI/CD Docs**
- Run coverage with baseline recording: `python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html:docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/coverage-html --cov-report=xml:docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/coverage.xml 2>&1 | tee /tmp/coverage-baseline.txt`
- Create `docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/adr029-cicd-integration.md` documenting:
  - ADR-029 compliance checklist
  - Pre-commit hook for safety-critical path detection
  - CI gate configuration (auto-rollback triggers)
  - Coverage regression baseline reference
- Verification: `grep "TOTAL" /tmp/coverage-baseline.txt` → coverage >= 70%

#### On Failure:
- If coverage < 70%: Identify uncovered modules, add critical-path tests to reach threshold
- If T1–T10 creation fails: Create files one-by-one, verify each before moving to next
- If `test_auto_rollback.py` fails: Check git permissions, test isolation, Discord webhook URL validity

#### Evidence:
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/coverage-summary.txt`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/coverage-html/`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/coverage.xml`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/adr029-cicd-integration.md`

---

### 2.3 Step 7.8: Final Backup — Required Content

Extracted from audit-72-security-posture.md (C-05), executive summary line 49, and rollback readiness pre-conditions §2.5.

**Duration**: 2 hours
**Risk**: LOW
**Depends**: Steps 7.1–7.7 (all hardening complete before backup)
**Parallel with**: None

#### Pre-conditions:
1. `[ ]` All steps 7.1–7.7 PASS
2. `[ ]` All 7 gates G01–G07 ready (some may be verified post-backup)
3. `[ ]` PostgreSQL accessible, disk space > 5 GB free
4. `[ ]` rclone configured for both S3 and R2 destinations
5. `[ ]` Rollback readiness pre-conditions §2.5 verified (rollback script exists, checkpoint exists, git tag exists)

#### Required Sub-Steps:

**7.8.1 — Create Git Tag for Phase 7 Completion**
- Command: `git tag -a "phase-7-complete-$(date +%Y%m%d)" -m "Phase 7 (ADR-035) hardening complete"`
- Verification: `git tag -l "phase-7-complete-*" | tail -5` → tag exists

**7.8.2 — Hermes Checkpoint**
- Command: `hermes checkpoints --create --name "phase-7-hardening-$(date +%Y%m%d)"`
- Verification: `hermes checkpoints --list | grep phase-7`

**7.8.3 — pg_dumpall Full Database Backup**
- Command: `pg_dumpall -h localhost -p 5433 -U guinevere -f /home/guinevere/backups/guinevere-full-$(date +%Y%m%d).dump`
- Verification: `ls -lh /home/guinevere/backups/guinevere-full-*.dump | tail -1` → file exists, size > 0

**7.8.4 — Restic Snapshot (Local + Offsite)**
- Command: `restic -r /home/guinevere/backups/restic-repo backup /home/guinevere/code/guinevere /home/guinevere/config /home/guinevere/secrets`
- Command: `restic -r r2:guinevere-dr-backups/restic backup /home/guinevere/code/guinevere /home/guinevere/config /home/guinevere/secrets`
- Verification: `restic -r /home/guinevere/backups/restic-repo snapshots | tail -3` → latest snapshot exists
- Verification: `restic -r r2:guinevere-dr-backups/restic snapshots | tail -3` → offsite snapshot exists

**7.8.5 — Restore Verification**
- Extract a single file from the restic snapshot to `/tmp/restore-verify/` and compare checksum
- Command: `restic -r /home/guinevere/backups/restic-repo restore latest --target /tmp/restore-verify --include "AGENTS.md" 2>&1 && diff <(md5sum /home/guinevere/code/guinevere/AGENTS.md) <(md5sum /tmp/restore-verify/home/guinevere/code/guinevere/AGENTS.md) && echo "RESTORE VERIFIED"`
- Cleanup: `rm -rf /tmp/restore-verify`
- Verification: Output shows "RESTORE VERIFIED"

#### On Failure:
- If pg_dumpall fails (R7-13): Check disk space, check PostgreSQL connectivity, retry
- If offsite sync fails (R7-14): Retry with `--ignore-errors`, check rclone config
- If quota exceeded (R7-19): Clean old backups, alert before full

#### Evidence:
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.8/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.8/backup-manifest.txt`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.8/restore-verification.txt`

---

### 2.4 Step 7.9: Documentation Update — Required Content

Extracted from audit-73-documentation.md (Items 1, 2), executive summary line 50, Gate G06 criteria.

**Duration**: 1 hour
**Risk**: LOW
**Depends**: Steps 7.1–7.8 (all evidence exists before doc update)
**Parallel with**: None

#### Pre-conditions:
1. `[ ]` All evidence artifacts from Steps 7.1–7.8 exist
2. `[ ]` Gate G01–G05 PASS verified
3. `[ ]` ADR-035-hermes-migration.md readable at `adr/ADR-035-hermes-migration.md`
4. `[ ]` PROGRESS.md readable at project root
5. `[ ]` CHECKLIST.md readable at project root
6. `[ ]` decisions-log.md readable at `docs/10-governance/decisions-log.md`

#### Required Sub-Steps:

**7.9.1 — Mark ADR-035 as IMPLEMENTED**
- Command: `sed -i 's/status: "Accepted"/status: "IMPLEMENTED"/' adr/ADR-035-hermes-migration.md`
- Verification (Gate G06): `grep "status:" adr/ADR-035-hermes-migration.md` → must show `IMPLEMENTED`
- Also update ADR frontmatter `version` to `v2.0` and `last_modified` to current date

**7.9.2 — Update PROGRESS.md**
- Mark Phase 7 (Hardening) as `[x]` complete
- Update Phase 7 line with completion date and reference to ADR-035 IMPLEMENTED
- Verification (Gate G06): `grep "Phase 7" PROGRESS.md` → must show `[x]` or completed status
- Command: Use `sed` or Python to edit the marker, e.g.:
  ```bash
  sed -i 's/- \[ \] Phase 7: Hardening/- [x] Phase 7: Hardening/' PROGRESS.md
  ```

**7.9.3 — Update CHECKLIST.md**
- Verify ADR-035 entry references IMPLEMENTED status
- Update any migration checklist items that reference Phase 7 as pending
- Verification (Gate G06): `grep "ADR-035" CHECKLIST.md` → must show IMPLEMENTED or equivalent

**7.9.4 — Create Decisions-Log Entry**
- Append to `docs/10-governance/decisions-log.md`:
  ```markdown
  | 2026-06-05 | ADR-035 | Hermes Migration | IMPLEMENTED | Phase 7 hardening complete. Hermes is primary Discord gateway. |
  ```
- Verification (Gate G06): `grep "ADR-035" docs/10-governance/decisions-log.md` → must find the new entry

**7.9.5 — Generate Consolidated Evidence Index**
- Create `docs/setup-evidence/hermes-migration/phase-7/evidence-index.md` (path from §18.2)
- Must reference all per-step verification.md paths, all gate evidence files, and all auditor reports

**7.9.6 — Create Final Gate Evidence Files**
- Create `G06-docs-pass.txt` with content: `ADR-035 status: IMPLEMENTED, PROGRESS.md updated, CHECKLIST.md updated, decisions-log entry created`
- Create `G07-stable-pass.txt` (if 24h stable condition met)

#### On Failure:
- If ADR-035 sed command errors: Verify file path and status string before re-running
- If PROGRESS.md pattern doesn't match: Use `grep -n "Phase 7" PROGRESS.md` to find exact text, then target with specific line edit
- If decisions-log already has entry: Check for duplicate and update existing entry

#### Evidence:
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/progress-update.txt`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/checklist-update.txt`

---

## 3. Commands Summary Table (for implementer reference)

| Step | Command Type | Example |
|---|---|---|
| 7.6.1 | Pre-migration | `grep -r "from src.discord.commands import" src/` |
| 7.6.2 | Archive source | `git mv src/discord/*.py deprecated/discord/` |
| 7.6.3 | Archive tests | `git mv tests/discord/ deprecated/tests/discord/` |
| 7.6.4 | Archive docs | `git mv stepprompts/StepPrompts.md stepprompts/archive/StepPrompts-v1.md` |
| 7.6.5 | Verify imports | `python -c "import src.hermes; import src.discord.help"` |
| 7.7.1 | Coverage config | Write `.coveragerc` or `pyproject.toml [tool.coverage.run]` |
| 7.7.2 | Safety paths config | Write `.guinevere/safety-critical-paths.yml` |
| 7.7.3 | Create T1-T10 tests | Create 10 files in `tests/integration/` |
| 7.7.4 | Auto-rollback test | Create `tests/safety/test_auto_rollback.py` |
| 7.7.5 | Coverage baseline | `pytest --cov=src --cov-report=xml` |
| 7.8.1 | Git tag | `git tag -a "phase-7-complete-20260605"` |
| 7.8.2 | Hermes checkpoint | `hermes checkpoints --create --name "phase-7-..."` |
| 7.8.3 | pg_dump | `pg_dumpall -h localhost -p 5433 -U guinevere -f ...` |
| 7.8.4 | Restic backup | `restic -r <repo> backup <paths>` |
| 7.8.5 | Restore verify | `restic restore ... && diff <(md5sum ...) <(md5sum ...)` |
| 7.9.1 | ADR-035 status | `sed -i 's/status: "Accepted"/status: "IMPLEMENTED"/'` |
| 7.9.2 | PROGRESS.md | `sed -i 's/- \[ \] Phase 7/- [x] Phase 7/'` |
| 7.9.3 | CHECKLIST.md | Verify ADR-035 entry |
| 7.9.4 | Decisions log | Append markdown table row |
| 7.9.5 | Evidence index | Create `phase-7/evidence-index.md` |

---

## 4. Verification Gates per Step

### Gate G05 — Deprecated Files (maps to Step 7.6)

| Criterion | Method | PASS | FAIL |
|---|---|---|---|
| 11 files archived | `find deprecated/ -type f | wc -l` | `>= 11` | `< 11` |
| No import errors | `python -c "import src.discord.help"` | Exit 0 | ImportError |
| No import errors (Hermes) | `python -c "import src.hermes"` | Exit 0 | ImportError |
| Full test suite passes | `pytest tests/ -v --tb=short` | Exit 0 | Any FAILED |

### Gate G06 — Documentation (maps to Step 7.9 + Step 7.7 outputs)

| Criterion | Method | PASS | FAIL |
|---|---|---|---|
| ADR-035 = IMPLEMENTED | `grep "status:" adr/ADR-035-hermes-migration.md` | IMPLEMENTED | Accepted |
| PROGRESS.md updated | `grep "Phase 7" PROGRESS.md` | Found | Not found |
| CHECKLIST.md updated | `grep "ADR-035" CHECKLIST.md` | Found | Not found |
| Decisions-log entry | `grep "ADR-035" docs/10-governance/decisions-log.md` | Found | Not found |
| Coverage >= 70% | `grep "TOTAL" coverage-summary.txt` | >= 70% | < 70% |
| T1-T10 all PASS | Individual test runs | All 10 PASS | Any 1 FAIL |
| .coveragerc or equiv exists | `test -f .coveragerc \|\| grep "coverage" pyproject.toml` | EXISTS | Not found |
| .guinevere/safety-critical-paths.yml exists | `test -f .guinevere/safety-critical-paths.yml` | EXISTS | Not found |

### Gate G07 — 24h Stable (maps to post-Step 7.8)

| Criterion | Method | PASS | FAIL |
|---|---|---|---|
| Uptime > 24h | `hermes gateway status \| grep uptime` | > 24h | < 24h |
| Zero crash logs | `journalctl -u hermes-gateway --since 24h \| grep -ci error` | < 5 errors | >= 5 |

### Additional Gate for Step 7.8 Backups

| Criterion | Method | PASS | FAIL |
|---|---|---|---|
| pg_dumpall exists | `ls -lh /home/guinevere/backups/guinevere-full-*.dump` | >= 1 file | 0 files |
| Restic snapshot exists | `restic -r <repo> snapshots` | Latest dated today | No snapshot |
| Restore verified | `diff <(md5sum) <(md5sum)` | Checksums match | Mismatch |
| Offsite snapshot exists | `restic -r r2:... snapshots` | Latest exists | Not found |

---

## 5. Rollback Procedures for Missing Sections

### Rollback Step 7.6 (Deprecated Files)
```bash
# If archival breaks imports:
cd /home/guinevere/code/guinevere
git checkout -- src/  # Restore all source files from git
# If git checkout not possible (files git-mv'd):
for f in deprecated/discord/*.py; do
  [ -f "$f" ] && cp "$f" "src/discord/" 2>/dev/null
done
for f in deprecated/hermes/*.py deprecated/core/*.py; do
  [ -f "$f" ] && cp "$f" "src/hermes/" 2>/dev/null
done
# Verify restoration:
python -c "import src.hermes; import src.discord.help"
```

### Rollback Step 7.7 (ADR-029 Tests)
```bash
# Remove added test infrastructure:
rm -f .coveragerc
rm -rf tests/integration/
rm -f tests/safety/test_auto_rollback.py
rm -f .guinevere/safety-critical-paths.yml
rm -rf docs/setup-evidence/hermes-migration/phase-7/STEP-7.7/
# Revert pyproject.toml if modified:
git checkout -- pyproject.toml
```

### Rollback Step 7.8 (Backups)
- Remove backup files: `rm -f /home/guinevere/backups/guinevere-full-*.dump`
- Remove git tag: `git tag -d phase-7-complete-*`
- No rollback needed for restic snapshots (append-only, no destructive action)

### Rollback Step 7.9 (Documentation)
```bash
# Revert ADR-035 status:
sed -i 's/status: "IMPLEMENTED"/status: "Accepted"/' adr/ADR-035-hermes-migration.md
# Revert PROGRESS.md:
sed -i 's/- \[x\] Phase 7: Hardening/- [ ] Phase 7: Hardening/' PROGRESS.md
# Remove decisions-log entry (manual edit)
```

---

## 6. Evidence Paths Summary

All paths rooted at `docs/setup-evidence/hermes-migration/phase-7/`:

| Step | Verification Path | Evidence Artifacts |
|---|---|---|
| 7.6 | `STEP-7.6/verification.md` | `archived-files-manifest.txt`, `import-verification.txt` |
| 7.7 | `STEP-7.7/verification.md` | `coverage-summary.txt`, `coverage-html/`, `coverage.xml`, `adr029-cicd-integration.md` |
| 7.8 | `STEP-7.8/verification.md` | `backup-manifest.txt`, `restore-verification.txt` |
| 7.9 | `STEP-7.9/verification.md` | `progress-update.txt`, `checklist-update.txt` |

Gate evidence (same root):

| Gate | Evidence File | Content |
|---|---|---|
| G05 | `G05-deprecated-pass.txt` | 11 archived, import OK |
| G06 | `G06-docs-pass.txt` | ADR-035 IMPLEMENTED, PROGRESS updated, decisions-log, coverage >= 70%, T1-T10 PASS, .coveragerc, safety-critical-paths.yml |
| G07 | `G07-stable-pass.txt` | > 24h uptime, < 5 errors |

---

## 7. Auditor PASS Criteria

For each of the four missing sections to pass auditor review:

### Step 7.6 Auditor PASS Criteria
- [ ] 5-step archive sequence documented with exact commands
- [ ] Pre-deployment code migration (command_categories, session_adapter import) specified
- [ ] Source file archival (11 files, 3,216 lines) with git mv commands
- [ ] Test file archival with conftest update
- [ ] Documentation archival (StepPrompts, evidence folders)
- [ ] Post-deletion verification: pytest, Hermes init, help.py import, lsp_diagnostics
- [ ] On-failure procedures documented (import breakage, help.py, conversational.py)
- [ ] Evidence paths defined matching §18.1 table
- [ ] Gate G05 criteria satisfied
- [ ] Risk R7-10/R7-11/R7-12 mitigation steps included

### Step 7.7 Auditor PASS Criteria
- [ ] `.coveragerc` or `pyproject.toml` coverage config creation specified
- [ ] `.guinevere/safety-critical-paths.yml` content specified
- [ ] All T1–T10 test files listed with creation command
- [ ] `test_auto_rollback.py` creation specified (ADR-029 60s SLA)
- [ ] CI/CD integration docs creation specified
- [ ] Coverage baseline generation with HTML + XML output
- [ ] Coverage fail-under >= 70%
- [ ] T1-T10 vs V01-V30 mapping clarified (existing Step 7.1.4 must be updated)
- [ ] On-failure procedures for coverage < 70% and test creation failures
- [ ] Evidence paths matching §18.1 table
- [ ] ADR-029 compliance gaps from audit-71 closed

### Step 7.8 Auditor PASS Criteria
- [ ] Git tag creation specified
- [ ] Hermes checkpoint creation specified
- [ ] pg_dumpall full backup command specified
- [ ] Restic backup (local + offsite S3/R2) specified
- [ ] Restore verification (extract + checksum compare) specified
- [ ] On-failure for pg_dump, offsite sync, quota exceeded
- [ ] Evidence paths matching §18.1 table
- [ ] Pre-conditions: Steps 7.1–7.7 PASS, disk space, rclone config, rollback readiness

### Step 7.9 Auditor PASS Criteria
- [ ] ADR-035 status change command specified (sed forward, not just rollback reverse)
- [ ] Version/date metadata update specified
- [ ] PROGRESS.md update command specified with exact sed pattern
- [ ] CHECKLIST.md verification specified
- [ ] Decisions-log entry format and content specified
- [ ] Consolidated evidence index creation specified
- [ ] Gate evidence file creation (G06-docs-pass.txt) specified
- [ ] On-failure for sed mismatch, duplicate decisions-log entries
- [ ] Evidence paths matching §18.1 table
- [ ] Gate G06 criteria satisfied

---

## 8. Cross-Cutting Issues Requiring Batch Plan Updates Outside Sections 8–11

### Issue CC-1: T1-T10 vs V01-V30 Test Relationship

**Location**: Step 7.1.4 (Section 3.5, lines 280–311)
**Problem**: Step 7.1.4 plans to create `tests/integration/test_verification.py` (V01-V30) independently of T1-T10. The two suites overlap in scope but have unknown mapping.
**Required fix**: Update Step 7.1.4 to either:
- (a) Remove V01-V30 creation and map verification to T1-T10 files (preferred, avoids duplication), OR
- (b) Document that V01-V30 is a superset and T1-T10 are subsets, with explicit mapping table

### Issue CC-2: `--run-e2e` Flag Not Referenced

**Location**: Step 7.1.2 (Section 3.3, lines 173–195)
**Problem**: Some E2E tests (e.g., `tests/surveillance/test_e2e.py`) require `--run-e2e` flag or `RUN_E2E=1` env var. The batch plan commands do not include this flag.
**Required fix**: Add note: "If E2E tests are gated behind --run-e2e, append the flag: `python -m pytest tests/ -v --tb=short --run-e2e`"

### Issue CC-3: Step 7.1.4 Uses Placeholder Creation Logic

**Location**: Section 3.5 (lines 293–303)
**Problem**: The file creation logic is a fragile placeholder that reads from `/tmp/test_verification_template.txt` or writes a comment. No real test code template is provided.
**Required fix**: Either (a) provide an inline Python heredoc with the V01-V30 test class structure, or (b) reference the T1-T10 files from Step 7.7.3 instead.

### Issue CC-4: systemd Hardening Verification Missing

**Location**: Step 7.5 (nowhere)
**Problem**: Audit-72 (C-02) identifies missing verification for `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only` across all `.service` files.
**Required fix**: Add `Step 7.5.7: Systemd Hardening Verification` with command:
```bash
ssh guinevere-vps 'grep -E "NoNewPrivileges|ProtectSystem|ProtectHome" systemd/*.service deploy/discord/*.service scripts/*.service'
```
Expected: Each directive appears at least once across the service files.

### Issue CC-5: Step 7.5.2 Port Audit — Tailscale Binding Check

**Location**: Step 7.5.2 (lines 836–854)
**Problem**: Port 22 (SSH) allowed; no check for Tailscale-only binding (`100.x.x.x` vs `0.0.0.0`). ADR-019 mandates zero public ports.
**Required fix**: Add check that port 22 binds to `100.x.x.x` (Tailscale IP) not `0.0.0.0`:
```python
# After allowed-set check, add:
ssh_check = [l for l in r.stdout.split("\n") if ":22" in l]
for line in ssh_check:
    if "0.0.0.0:22" in line:
        print("FAIL: SSH bound to 0.0.0.0 (public)")
    elif "100." in line and ":22" in line:
        print("PASS: SSH bound to Tailscale IP")
```

### Issue CC-6: Runbook Verify/Escalate Subsections

**Location**: Section 12 (Runbooks R01-R09)
**Problem**: Audit-73 identifies missing explicit "Verify" and "Escalate" subsections in each runbook.
**Required fix**: Add a "Verify" subsection as final step and "Escalate" subsection with escalation paths to each of R01-R09. Add RTO/RPO column to runbook headers.

---

## 9. Dependency Map for Sections 7.6–7.9

```
Step 7.6 (Deprecated Files)
  depends on: Step 7.1 (regression suite PASS), Step 7.5 (security audit PASS)
  blocked by: 24h stable pre-condition (§1.2)
  └─► Step 7.7 (ADR-029 Tests)
        depends on: Step 7.6 (clean source tree for test creation)
        └─► Step 7.8 (Final Backup)
              depends on: Step 7.7 (all tests PASS, coverage baseline)
              └─► Step 7.9 (Documentation Update)
                    depends on: All steps 7.1–7.8 (all evidence exists)
                    └─► Gate G05, G06, G07 verification
```

Execution order: **Strictly sequential** (7.6 → 7.7 → 7.8 → 7.9). No parallelism because each step depends on the previous step's outputs.

---

## 10. Risk Register Additions Specific to Sections 7.6–7.9

| ID | Risk | Prob | Impact | Score | Mitigation |
|---|---|---|---|---|---|
| R7-20 | `.coveragerc` creation conflicts with rollback expectation (rollback plan §16 `rm -f .coveragerc`) | LOW | MED | 6 | Ensure rollback plan references are consistent with creation in Step 7.7.1 |
| R7-21 | T1-T10 test files cannot be created because `tests/integration/` doesn't exist | LOW | MED | 6 | `mkdir -p tests/integration/` in Step 7.7.3 pre-condition |
| R7-22 | `test_auto_rollback.py` dangerously interacts with live git repo | MED | HIGH | 12 | Use temp directory with `git clone --depth=1` for simulation; never run git revert on active deployment |
| R7-23 | pg_dumpall produces stale backup if Hermes is mid-conversation | LOW | LOW | 3 | Run during scheduled low-traffic window (04:00-06:00 WIB) |
| R7-24 | ADR-035 sed pattern doesn't match actual status string | LOW | LOW | 3 | Verify exact status string with `grep "status:" adr/ADR-035-hermes-migration.md` before sed |

---

## Document Footer

**Author**: Guinevere (Sisyphus-Junior — Recheck Context Agent)
**Version**: 1.0 | **Date**: 2026-06-05
**Status**: Active — Input for batch plan authoring
**Next Action**: Create batch plan sections 8–11 with content matching this specification; apply cross-cutting fixes CC-1 through CC-6 to existing sections; re-audit with auditors 7-1, 7-2, 7-3 for PASS.
