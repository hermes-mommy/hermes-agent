# Verification Report — S3.9: Cron/Ritual Migration

**Date**: 2026-06-04
**Task**: S3.9 — Migrate 5 ritual triggers + 3 system crons from bot.py to Hermes config
**Files**: `src/discord/bot.py` (modified), `hermes-config/config.yaml` (verified)
**Verifier**: Guinevere (parent)

## 1. What Was Done

Removed the ritual scheduler from `bot.py` — the `RitualScheduler` with its Discord callback that sent ritual messages to #guinevere-chat. All 8 cron entries (5 rituals + 3 system crons) are already present in `hermes-config/config.yaml` from Wave 1 Agent A deployment. Hermes now owns ritual scheduling.

## 2. Files Changed

| File | Action | Lines Removed |
|------|--------|---------------|
| `src/discord/bot.py` | **MODIFIED** | ~42 lines removed |

## 3. Changes Detail

### Removed from bot.py:
1. **Import** (line 25): `from src.persona.ritual_scheduler import RitualScheduler, RitualResult`
2. **Attribute** (line 96): `self._ritual_scheduler: RitualScheduler | None = None`
3. **Ritual scheduler block** (lines 433-469): Complete ritual scheduler setup including Discord callback, `RitualScheduler.setup()`, `.start()`, and error handling
4. **Close handler** (lines 476-482): Ritual scheduler stop logic in `close()`

### Preserved in bot.py:
- ✅ HARD STOP listener (`_register_hard_stop_listener`, `_on_message_listener`)
- ✅ Shadow pipeline initialization (`ShadowPipeline`)
- ✅ Surveillance safe mode guard (`SurveillanceSafeModeGuard`)
- ✅ All 35 slash commands (13 original + 20 Batch D + 2 Hermes)
- ✅ Command tree sync (`self.tree.sync`)
- ✅ Session factory (`get_session_factory`)
- ✅ `on_ready` handler
- ✅ `on_message` handler with conversational + command processing
- ✅ `main()` entrypoint

## 4. Validation Results

### AST Parse
```
python -c "import ast; ast.parse(open('src/discord/bot.py').read())" → OK
```

### Ritual/Scheduler Removal
```
grep "ritual|scheduler|tasks\.loop" src/discord/bot.py → ZERO matches ✅
```

### Hermes Config Cron Verification
All 8 entries confirmed present in `hermes-config/config.yaml`:

| Cron | Schedule | Command | Status |
|------|----------|---------|--------|
| `daily_health_check` | `0 6 * * *` | `hermes doctor --report` | ✅ |
| `weekly_backup` | `0 2 * * 0` | `hermes backup --full --destination idcloudhost` | ✅ |
| `monthly_security_scan` | `0 3 1 * *` | `hermes security --report` | ✅ |
| `ritual_morning` | `0 8 * * *` | `hermes plugin trigger guinevere_safety ritual morning` | ✅ |
| `ritual_midday` | `0 12 * * *` | `hermes plugin trigger guinevere_safety ritual midday` | ✅ |
| `ritual_afternoon` | `0 16 * * *` | `hermes plugin trigger guinevere_safety ritual afternoon` | ✅ |
| `ritual_evening` | `0 20 * * *` | `hermes plugin trigger guinevere_safety ritual evening` | ✅ |
| `ritual_midnight` | `0 0 * * *` | `hermes plugin trigger guinevere_safety ritual midnight` | ✅ |

### Schedule Verification (ADR-035)
| Ritual | Expected | Actual | Match |
|--------|----------|--------|-------|
| morning | 8:00 WIB (UTC+7) | `0 8 * * *` (8:00) | ✅ |
| midday | 12:00 WIB (UTC+7) | `0 12 * * *` (12:00) | ✅ |
| afternoon | 16:00 WIB (UTC+7) | `0 16 * * *` (16:00) | ✅ |
| evening | 20:00 WIB (UTC+7) | `0 20 * * *` (20:00) | ✅ |
| midnight | 0:00 WIB (UTC+7) | `0 0 * * *` (0:00) | ✅ |

### LSP Diagnostics
- All errors/warnings are pre-existing environment issues (discord.py not installed in dev environment)
- `reportImplicitRelativeImport`, `reportAttributeAccessIssue` for `discord` — pre-existing
- **No new code quality issues introduced.**

## 5. Evidence Artifacts

- `src/discord/bot.py` — 557 lines (was 610, -53 lines), AST-passing
- `hermes-config/config.yaml` — 351 lines, all 8 cron entries verified

## 6. Doc-Sync Impact

- None required. Ritual scheduling responsibility has been documented in ADR-035 and the batch plan already reflects Hermes as the cron owner.

## 7. Boundary Compliance

- ✅ No persona drift (rituals now triggered via `guinevere_safety` plugin in Hermes)
- ✅ No consent violation
- ✅ No surveillance overreach
- ✅ No Y6
- ✅ No HARD STOP bypass
- ✅ No secret exposure

## 8. Rollback/Re-run Safety

- The `RitualScheduler` class (`src/persona/ritual_scheduler.py`) still exists — it can be re-added to bot.py if needed
- Hermes cron config changes are additive (already present from Wave 1) — no destructive changes
- Bot.py removal is reversible via `git revert`

## 9. Auditor Gate

Ready for independent auditor review.

## 10. Security Scan

- No secrets, tokens, or credentials in modified code
- Cron commands in config.yaml use Hermes CLI — no secrets in command strings
- Hermes handles safe-mode/consent for ritual plugin triggers

## 11. Acceptance Criteria Mapping

| Criterion | Status |
|-----------|--------|
| Ritual scheduler removed from bot.py | PASS |
| Zero ritual/scheduler/tasks.loop references in bot.py | PASS |
| All 8 cron entries in Hermes config | PASS |
| Cron schedules match ADR-035 spec | PASS |
| All other bot.py functionality intact | PASS |
| HARD STOP listener preserved | PASS |
| Shadow pipeline preserved | PASS |
| AST parse clean | PASS |
| No new diagnostics | PASS |

## 12. Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-04 | Guinevere | Initial verification report for S3.9 |