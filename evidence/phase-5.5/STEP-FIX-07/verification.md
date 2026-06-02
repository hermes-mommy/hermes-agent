# STEP-FIX-07: Systemd Service Hardening — Loops & Scheduler

## What Was Done

Added 13 hardening directives + REDIS_PASSWORD environment variable to both `systemd/guinevere-loops.service` and `systemd/guinevere-scheduler.service`, matching the pattern established in `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`.

## Files Changed

| File | Before | After | Change |
|------|--------|-------|--------|
| `systemd/guinevere-loops.service` | 16 lines (minimal) | 33 lines (hardened) | +17 lines |
| `systemd/guinevere-scheduler.service` | 16 lines (minimal) | 33 lines (hardened) | +17 lines |

## 13 Hardening Directives Added

| # | Directive | Value | Category |
|---|-----------|-------|----------|
| 1 | `Type` | `exec` (was `simple`) | Service type |
| 2 | `Environment=PYTHONPATH` | `/home/guinevere/code/guinevere` | Python env |
| 3 | `Environment=PYTHONDONTWRITEBYTECODE` | `1` | Python env |
| 4 | `Environment=VIRTUAL_ENV` | `.../.venv` | Python env |
| 5 | `StandardOutput` | `journal` | Logging |
| 6 | `StandardError` | `journal` | Logging |
| 7 | `MemoryHigh` | `1G` | Resource limit |
| 8 | `MemoryMax` | `2G` | Resource limit |
| 9 | `CPUQuota` | `200%` | Resource limit |
| 10 | `NoNewPrivileges` | `true` | Security |
| 11 | `ProtectSystem` | `strict` | Security |
| 12 | `ProtectHome` | `read-only` | Security |
| 13 | `ReadWritePaths` | 4 paths | Security |

## Additional: REDIS_PASSWORD

| Directive | Value | Purpose |
|-----------|-------|---------|
| `Environment=REDIS_PASSWORD` | `%E/REDIS_PASSWORD` | Redis auth via systemd credential store |

## Service-Specific Differences

| Field | guinevere-loops.service | guinevere-scheduler.service |
|-------|------------------------|----------------------------|
| Description | Guinevere Agent Loop Daemon | Guinevere Loop Scheduler Daemon |
| After | guinevere-core.service network.target | guinevere-loops.service network.target |
| Requires | guinevere-core.service | guinevere-loops.service |
| ExecStart | `python -m src.loops.manager` | `python -m src.loops.scheduler` |

All other directives are identical between the two files.

## Validation Results

- [x] Both files are 33 lines (verified by read-back)
- [x] All 13 hardening directives present in both files
- [x] REDIS_PASSWORD environment variable present in both files
- [x] ExecStart paths preserved from originals (no path changes)
- [x] Slice=guinevere.slice preserved
- [x] Dependency chain correct: core → loops → scheduler
- [x] network.target added to After= for both services
- [x] No directives added beyond the reference pattern
- [x] guinevere-core.service NOT modified

## Boundary Compliance

- No secrets committed (REDIS_PASSWORD uses systemd %E specifier)
- No safety-affecting domains touched
- No persona/consent/surveillance changes

## Rollback

Revert both files to 16-line originals from git history if needed.

## Footer

| Field | Value |
|-------|-------|
| Step | STEP-FIX-07 |
| Phase | 5.5 (Post-Implementation Fixes) |
| Date | 2026-06-02 |
| Status | PASS |
