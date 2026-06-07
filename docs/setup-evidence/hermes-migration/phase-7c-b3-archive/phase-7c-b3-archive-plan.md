# Phase 7c B3 Archive Plan — Deprecated Import Migration

Status: PLANNED
Date: 2026-06-06
Scope: B3 deprecated Discord/Hermes archive only
Authority: AGENTS.md, ADR-035 Phase 7, fix-imports research wave

## 1. Intent

Migrate active imports away from the 10 deprecated files and archive those files only after import scans and tests prove the archive is safe.

This plan is not a final Phase 7 completion claim. ADR-035 remains NOT IMPLEMENTED until all Phase 7 gates pass.

## 2. Research Inputs

- `fix-imports/01-embed-helpers.md`
- `fix-imports/02-commands-usage.md`
- `fix-imports/03-other-deps.md`
- `research-reports/phase-7c-b3-b8/01-remaining-imports.md`
- `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/AUDIT-archive-integrity.md`

## 3. Binding Decisions

1. Archive is allowed only with `git mv` into `src/_deprecated/hermes-migration-phase-7/`.
2. No file may be deleted.
3. No Aizanta file/container/service may be touched.
4. No secret values may be read into evidence or committed.
5. No new `Any`, type suppression, bare `except:`, empty catch, or `except Exception` may be introduced.
6. Tests must pass before archive and after archive.
7. Active import scan must be zero before archive, excluding `src/_deprecated/`.
8. If any active deprecated import remains, archive is blocked and evidence must say blocked.

## 4. Deprecated Files Target List

These 10 files are the only archive targets:

1. `src/discord/bot.py`
2. `src/discord/conversational_handler.py`
3. `src/discord/commands.py`
4. `src/discord/permissions.py`
5. `src/discord/guild_setup.py`
6. `src/discord/startup.py`
7. `src/discord/_embed_helpers.py`
8. `src/discord/intents.py`
9. `src/hermes/session_adapter.py`
10. `src/hermes/memory_bridge.py`

`src/core/services/llm_router.py` is explicitly retained and not part of this archive.

## 5. Dependency Map

| Step | Dependency | Purpose |
|---|---|---|
| A1 Embed utils extraction | none | Move `_embed_helpers.py` symbols to `src/discord/_embed_utils.py` and update 22 `cmd_*.py` imports |
| A2 Command auth/catalog extraction | A1 | Move `is_faiz_interaction` to `src/discord/_auth_guard.py`, move Discord command registry to `src/discord/_command_registry.py`, redirect catalog/count users |
| A3 Bot/startup/intents/memory migration | A2 | Remove remaining production imports from `bot.py`, `startup.py`, `intents.py`, `conversational_handler.py`, `memory_bridge.py`, `session_adapter.py` |
| A4 Test migration | A3 | Update/archive deprecated tests without silently deleting coverage |
| A5 Pre-archive verification | A4 | Run tests and active import scan |
| A6 Archive via git mv | A5 PASS only | Move exactly 10 deprecated files and add README |
| A7 Post-archive verification | A6 | Re-run tests, imports, diagnostics, evidence |
| A8 Auditors | A7 | Import migration and archive integrity auditors |

## 6. Collision Scan

- A1 and A2 both touch many `src/discord/cmd_*.py` files, so they are sequential, not parallel.
- A2 and A3 both touch `src/discord/bot.py` and tests, so A3 waits for A2.
- A6 is blocked until A5 proves zero active deprecated imports.
- Parent owns evidence and commit/push.

## 7. Per-Step Verification Scaffolds

### A1 — Embed Utils Extraction

Expected files:
- Create `src/discord/_embed_utils.py`
- Modify the 22 `src/discord/cmd_*.py` files that import `._embed_helpers`
- Create `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A1-embed-utils/verification.md`

Forbidden patterns:
- `from \._embed_helpers import` outside `src/_deprecated/`
- New `# type: ignore`, `@ts-ignore`, `@ts-expect-error`, `as any`
- New `except:` or `except Exception`
- New avoidable `Any`

Required commands:
- `python -m pytest tests/discord/test_cmd_mood.py -q --tb=short` exits 0
- `python -m pytest tests/phase7/ -q --tb=short` exits 0
- active grep for `from \._embed_helpers import` excluding `_deprecated` returns zero
- `lsp_diagnostics` on changed files has no new errors

Hard rejection:
- Any command module still imports `._embed_helpers`
- Runtime tests fail due the extraction

### A2 — Command Auth and Registry Extraction

Expected files:
- Create `src/discord/_auth_guard.py`
- Create `src/discord/_command_registry.py`
- Modify 31 command callback files from `.commands import is_faiz_interaction` to `._auth_guard`
- Modify `src/discord/cmd_help.py` catalog import to `src.hermes_plugins.command_catalog`
- Modify `src/discord/bot.py` to import command specs from `_command_registry`
- Modify `tests/discord/test_bot.py` and `tests/discord/test_cmd_mood.py` imports/count assertions
- Create `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A2-command-registry/verification.md`

Forbidden patterns:
- `from .commands import` outside `src/_deprecated/`
- `from . import commands as cmds` outside `src/_deprecated/`
- `import src.discord.commands` outside `src/_deprecated/`
- new type suppressions, empty catches, avoidable `Any`

Required commands:
- `python -m pytest tests/discord/test_cmd_mood.py tests/discord/test_bot.py -q --tb=short` exits 0 or documents pre-existing unrelated failures with direct proof
- `python -m pytest tests/phase7/ -q --tb=short` exits 0
- active grep for `src.discord.commands|from .commands import|from . import commands as cmds` excluding `_deprecated` returns zero

Hard rejection:
- Any active import from `commands.py` remains
- Command count/categorization drifts from 35 commands

### A3 — Bot/Startup/Intents/Memory Migration

Expected files:
- Remove `bot.py` imports from `intents.py`, `startup.py`, and `conversational_handler.py` by extracting/inlining safe non-deprecated replacements
- Remove `src.hermes.memory_bridge` production imports from `src/discord/hermes_conversational.py`
- Remove or replace active lazy dependency on `src/hermes/session_adapter.py` in `src/hermes/adapter.py`
- Create `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A3-other-deps/verification.md`

Forbidden patterns:
- `from .intents import get_intents`
- `from .startup import on_ready`
- `from .conversational_handler import handle_conversation`
- `from src.hermes.memory_bridge import`
- `from .session_adapter import`
- New type suppressions, empty catches, avoidable `Any`

Required commands:
- `python -m pytest tests/discord/test_bot.py tests/discord/test_startup.py tests/hermes/test_memory_bridge.py -q --tb=short` exits 0 or deprecated tests are migrated/archived with evidence
- `python -m pytest tests/phase7/ -q --tb=short` exits 0
- active import grep for the forbidden patterns returns zero

Hard rejection:
- Non-deprecated production code still imports archive targets

### A4 — Test Migration

Expected files:
- Update tests that import deprecated modules to new homes, or move deprecated-only tests under the archive evidence path with rationale
- No test deletion to pass silently
- Create `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A4-test-migration/verification.md`

Required commands:
- `python -m pytest tests/discord/ tests/hermes/ tests/phase7/ -q --tb=short` exits 0 or only documented pre-existing unrelated failures remain
- active test grep for deprecated imports excluding `_deprecated` returns zero

### A5 — Pre-Archive Gate

Expected evidence:
- `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A5-pre-archive/verification.md`

Required commands:
- Active source/test grep for `from src.discord|import src.discord|from .commands import|from ._embed_helpers import|src.hermes.memory_bridge|src.hermes.session_adapter` excluding `_deprecated` returns zero for archive-target imports only
- `python -m pytest tests/ -q --tb=short` exits 0 or documented pre-existing unrelated failures are isolated and accepted by auditor

Hard rejection:
- Any active import from the 10 archive targets remains

### A6 — Archive

Expected files:
- Create `src/_deprecated/hermes-migration-phase-7/README.md`
- Move exactly the 10 target files via `git mv`
- Create `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A6-archive/verification.md`

Forbidden:
- `Remove-Item`, delete, copy-without-git-mv, destructive shell deletion

Required commands:
- `git status --short` shows renames for the 10 files
- target files no longer exist at original locations
- archive directory contains exactly the moved targets plus README

### A7 — Post-Archive Gate

Expected evidence:
- `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A7-post-archive/verification.md`

Required commands:
- `python -m pytest tests/ -q --tb=short` exits 0 or auditor-approved pre-existing failures only
- active import scan remains zero
- LSP diagnostics clean on changed files

### A8 — Auditors

Auditors:
- Import Migration auditor → `AUDIT-import-migration.md`
- Archive Integrity auditor → `AUDIT-archive-integrity.md`

Both must PASS before commit/push.

## 8. Rollback Plan

- Before archive, rollback by reverting edits in changed source/test files.
- After archive, rollback with `git mv` from `src/_deprecated/hermes-migration-phase-7/` back to original paths.
- Never delete archive files.

## 9. Execution Checklist

- [ ] A1 PASS
- [ ] A2 PASS
- [ ] A3 PASS
- [ ] A4 PASS
- [ ] A5 PASS
- [ ] A6 PASS
- [ ] A7 PASS
- [ ] A8 auditors PASS
- [ ] Commit/push only after all gates PASS

## 10. Footer

Generated by Sisyphus. File-based planner gate for B3 archive work. No implementation has been performed by this plan file itself.
