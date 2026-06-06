# Phase 7c Safe-Subset Plan — Deprecated Imports + Hermes CLI

**Date**: 2026-06-06  
**Scope**: ADR-035 Phase 7c safe fixes only  
**Status**: PLANNED — safe subset only; final Phase 7 remains BLOCKED  
**Authority**: AGENTS.md, ADR-035, Phase 7b completion report, Phase 7c research wave, Oracle safe-boundary verdict

---

## 1. Executive Gate

Oracle verdict: **SAFE-SUBSET ONLY**.

The requested full Phase 7c archive is **blocked** because the 24-hour stability gate failed, `guinevere-mcp` remains inactive, and active imports still depend on the deprecated files. This plan implements only low-risk pre-archive refactors and the zero-disruption Hermes CLI PATH fix.

### Allowed Now

1. Create a Hermes-native command catalog and remove `src/hermes_plugins/commands_high/help.py` dependency on `src.discord.commands`.
2. Clean `src/hermes/__init__.py` so importing `src.hermes` no longer imports deprecated `session_adapter.py` or `memory_bridge.py`.
3. Move the shared adapter accessor to a non-package-init module and update active callers to import it directly.
4. Fix Hermes CLI availability for non-interactive VPS SSH shells via a shell-profile PATH adjustment only if the exact condition is present.
5. Run read-only Hermes CLI checks (`hermes --version`, `hermes backup --help`, `hermes checkpoints status`) and avoid live backup writes unless a dry-run/help mode is used.
6. Update evidence and blocker status honestly.

### Blocked Now

1. No `git mv` archive of the 10 deprecated files yet.
2. No final Phase 7 deployment, tag, push, or ADR-035 IMPLEMENTED flip.
3. No `hermes backup` live write unless the command is explicitly non-writing.
4. No VPS service restarts, firewall changes, SSH daemon changes, or Aizanta changes.

---

## 2. Research Inputs

- `research-reports/phase-7c-execution/01-import-deps.md`: archive not safe; 73 active inbound imports across 60+ files.
- `research-reports/phase-7c-execution/02-hermes-cli-status.md`: CLI exists and works via full venv path and `~/.local/bin/hermes`; non-interactive PATH misses `~/.local/bin` due `.bashrc` early return.
- `research-reports/phase-7c-execution/03-stability-check.md`: 24-hour stability gate failed; `guinevere-mcp` inactive.
- `research-reports/phase-7c-execution/04-hermes-cli-docs.md`: CLI backup/checkpoints docs; backup writes zip by default.
- `research-reports/phase-7c-execution/05-archive-patterns.md`: hyphenated archive path is non-importable; use only for true tombstone archive, not for importable migrated tests.
- Oracle `bg_6f5b2c49`: safe subset only; block archive/deploy/commit until gates pass.

---

## 3. Binding Decisions

| Decision | Binding Outcome |
|---|---|
| Deprecated archive | BLOCKED until 24h stability, `guinevere-mcp` active, and all active imports migrated |
| Archive path | Keep user-requested hyphenated path only as a true tombstone after no imports reference archive; if tests must import archived code, use underscore path instead and document deviation |
| `src.hermes` package init | Must not import deprecated `session_adapter.py` or `memory_bridge.py` |
| Hermes help command | Must not import `src.discord.commands` |
| Hermes CLI PATH | May fix only shell profile/PATH; no service restart or systemd mutation |
| Backup | Read-only help/status checks only; live backup write is blocked unless dry-run is available and verified |
| Commit/push | Blocked until safe-subset verification and auditors pass; final Phase 7 commit/tag remains blocked |
| ADR-035 status | Remains NOT IMPLEMENTED |

---

## 4. Master Todo and Dependency Map

| Step | Task | Dependencies | Parallelism |
|---|---|---|---|
| 7C-S1 | Hermes-native command catalog + help.py cleanup | None | Parallel |
| 7C-S2 | Clean `src/hermes/__init__.py` deprecated imports via explicit adapter module | None | Parallel |
| 7C-S3 | VPS Hermes CLI non-interactive PATH fix and read-only verification | None | Parallel |
| 7C-S4 | Safe-subset evidence and blocker update | S1-S3 verification | Sequential |
| 7C-S5 | Auditor wave: Import cleanup, Archive integrity/blocker honesty, Hermes CLI | S4 | Parallel |

---

## 5. Collision Scan

| File or Surface | Owner | Collision Risk | Mitigation |
|---|---|---|---|
| `src/hermes_plugins/commands_high/help.py` | 7C-S1 | Low | Single owner |
| `src/hermes_plugins/command_catalog.py` | 7C-S1 | Low, new file | Single owner |
| `src/hermes/__init__.py` | 7C-S2 | Medium | Single owner; no archive |
| `src/hermes/adapter.py` | 7C-S2 | Low, new file | Single owner |
| callers of `from src.hermes import get_adapter` | 7C-S2 | Medium | Update only direct imports to `src.hermes.adapter` |
| VPS `~/.bashrc` | 7C-S3 | Low but remote stateful | Backup before edit; only reorder/source PATH line; no restart |
| Evidence docs | 7C-S4 | Low | Parent-owned after implementation verification |
| Deprecated files | None | High | No movement in this safe subset |

---

## 6. Per-Step Verification Scaffolds

### Step 7C-S1 — Hermes Command Catalog and Help Cleanup

**Expected Files**

- `src/hermes_plugins/command_catalog.py` (new)
- `src/hermes_plugins/commands_high/help.py` (modified)
- `docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/auditor-gate.md`

**Forbidden Patterns**

- `from src.discord.commands import` in `src/hermes_plugins/commands_high/help.py`
- `\bAny\b` in `src/hermes_plugins/commands_high/help.py`
- `except Exception` in `src/hermes_plugins/commands_high/help.py`
- `# type: ignore`, `@ts-ignore`, `@ts-expect-error`

**Required Commands**

- `python -m pytest tests/phase7/test_T10_monitoring_health.py tests/discord/test_cmd_mood.py -q --tb=short` → exit 0 or document pre-existing unrelated failure
- `python -m pytest tests/phase7/ -q --tb=short` → exit 0
- `python -c "from src.hermes_plugins.command_catalog import command_categories, command_count; cats = command_categories(); assert command_count() == sum(len(v) for v in cats.values())"` → exit 0
- `grep "from src.discord.commands import" src/hermes_plugins/commands_high/help.py` → exit 1

**Hard Rejection Criteria**

- Help plugin still imports `src.discord.commands`.
- Help plugin keeps avoidable `Any` or broad `except Exception`.
- New catalog has inconsistent command count.
- Targeted tests fail due this change.

### Step 7C-S2 — Clean `src.hermes` Deprecated Imports

**Expected Files**

- `src/hermes/__init__.py` (modified)
- `src/hermes/adapter.py` (new)
- Active callers modified only where they import `get_adapter` from `src.hermes`
- `docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S2/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S2/auditor-gate.md`

**Forbidden Patterns**

- `from .session_adapter import` in `src/hermes/__init__.py`
- `from .memory_bridge import` in `src/hermes/__init__.py`
- `HermesSessionAdapter` or `HermesMemoryBridge` in `src/hermes/__all__`
- `from src.hermes import get_adapter` in active source files
- `# type: ignore`, avoidable `Any`, empty catch

**Required Commands**

- `python -c "import src.hermes; print(src.hermes.__all__)"` → exit 0 and no deprecated import warnings
- `grep "from src.hermes import get_adapter" src -n` → no active source matches except archived/deprecated paths if any
- `python -m pytest tests/phase7/ -q --tb=short` → exit 0
- `python -m pytest tests/hermes tests/discord/test_cmd_mood.py -q --tb=short` → exit 0 or document pre-existing unrelated failure

**Hard Rejection Criteria**

- Importing `src.hermes` imports deprecated adapter/bridge modules.
- Active source keeps `from src.hermes import get_adapter`.
- Targeted tests fail due this change.

### Step 7C-S3 — VPS Hermes CLI Non-Interactive PATH Fix

**Expected Evidence**

- `docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S3/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S3/auditor-gate.md`

**Allowed Remote Change**

- Only edit `/home/guinevere/.bashrc` or equivalent shell profile to ensure `~/.local/bin` is sourced/available before the non-interactive early return.
- Create a timestamped backup before edit.

**Forbidden Remote Changes**

- No service restart.
- No systemd edit.
- No SSH daemon/firewall/port changes.
- No Aizanta files/processes.
- No secrets printed.
- No live `hermes backup` write.

**Required Commands**

- `ssh guinevere-vps 'command -v hermes || true'` before and after fix, with before/after documented.
- `ssh guinevere-vps 'hermes --version'` after fix → exit 0.
- `ssh guinevere-vps 'hermes backup --help >/dev/null && hermes checkpoints status'` after fix → exit 0.
- `ssh guinevere-vps 'systemctl is-active hermes-gateway'` before and after fix → active.

**Hard Rejection Criteria**

- Any service status changes from active to inactive.
- Any command outputs secrets.
- Live backup zip is created unintentionally.
- PATH fix requires service restart or systemd mutation.

### Step 7C-S4 — Evidence and Blocker Update

**Expected Files**

- `docs/setup-evidence/hermes-migration/phase-7c/phase-7c-safe-subset-completion-report.md`
- `docs/20-security/hermes-phase-7-blocker-register.md` (modified only for B8/B9 status if justified)

**Forbidden Claims**

- No “Phase 7 complete”.
- No “ADR-035 IMPLEMENTED”.
- No “deprecated files archived” unless actual archive occurred, which this plan blocks.
- No “backup created” unless a live backup was intentionally created under approved command, which this plan blocks.

**Required Checks**

- Evidence paths for S1-S3 exist and are parent-read.
- Blocker register still lists unresolved blockers honestly.
- Phase 7c safe-subset report includes remaining blocker count and Phase 7 complete = NO.

**Hard Rejection Criteria**

- Any false final completion claim.
- Any hidden blocker or fake backup/stability proof.

---

## 7. Token, Secret, and Safety Handling

- Do not print or store Discord tokens, API keys, DB passwords, SOPS keys, Redis AUTH, or restic credentials.
- Do not send secrets to external tools.
- Remote SSH commands must avoid `env`, `.env`, `cat secrets`, or any secret-bearing path.
- Preserve consent/surveillance/HARD STOP boundaries; this safe subset does not modify persona or surveillance runtime logic.
- Aizanta must not be touched.

---

## 8. Rollback Plan

| Step | Rollback |
|---|---|
| S1 | Revert `help.py` and remove new catalog if tests fail |
| S2 | Revert `src/hermes/__init__.py`, `src/hermes/adapter.py`, and import changes if imports/tests fail |
| S3 | Restore `/home/guinevere/.bashrc` from timestamped backup |
| S4 | Revert evidence/blocker wording if inaccurate |

No destructive git cleanup, no force push, no deployment rollback needed because no deployment is planned.

---

## 9. Auditor Matrix

| Auditor | Scope | Report Path |
|---|---|---|
| Import cleanup auditor | S1/S2 source imports, tests, no forbidden patterns | `docs/setup-evidence/hermes-migration/phase-7c/AUDIT-import-cleanup.md` |
| Archive integrity/blocker honesty auditor | Confirms archive correctly blocked and blocker register honest | `docs/setup-evidence/hermes-migration/phase-7c/AUDIT-archive-integrity.md` |
| Hermes CLI auditor | S3 remote evidence, no service disruption, no live backup write | `docs/setup-evidence/hermes-migration/phase-7c/AUDIT-hermes-cli.md` |

---

## 10. Execution Checklist

- [ ] Step 7C-S1 implemented and parent-verified.
- [ ] Step 7C-S2 implemented and parent-verified.
- [ ] Step 7C-S3 implemented and parent-verified.
- [ ] Step 7C-S4 evidence updated and parent-read.
- [ ] Three auditors PASS or valid blocker documented.
- [ ] Final report says Phase 7 complete = NO unless all Phase 7 gates pass.
- [ ] No final ADR-035 IMPLEMENTED claim.

---

## 11. Deferred Phase 7c Gates

Actual deprecated archive may resume only when all are true:

1. 24-hour stable operation verified.
2. `guinevere-mcp` active/enabled/running or explicitly removed from required service matrix by approved ADR/update.
3. All active imports away from the 10 target deprecated files.
4. Tests pass before and after each archive move.
5. Archive target semantics decided: hyphenated tombstone only if no imports/tests reference archive; underscore path if importable archive needed.
6. Backup/DR command side effects are understood and documented.

## Footer

Generated by Sisyphus for Guinevere ADR-035 Phase 7c safe-subset execution. This plan does not authorize Phase 7 completion, ADR-035 IMPLEMENTED status, final deployment, final tag, or deprecated archive.
