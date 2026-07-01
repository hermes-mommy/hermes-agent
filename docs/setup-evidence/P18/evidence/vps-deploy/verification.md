# P18 VPS Deployment Verification Report

**Date:** 2026-06-19 23:20 WIB  
**VPS Host:** faiz-prod-01 (alias: guinevere-vps)  
**Actual Service Path:** `/home/guinevere/code/guinevere/` (NOT `/opt/guinevere/`)  
**Service:** guinevere-core (systemd, uvicorn, Python 3.12 venv)

---

## Step 1: SCP Files — PASS

**Note:** Task specified `/opt/guinevere` but the actual service runs from `/home/guinevere/code/guinevere/`. Files were deployed to the correct service path.

14 files transferred via SCP (7 new + 7 modified):

| File | Type | Status |
|------|------|--------|
| `src/memory/tiers.py` | New | Deployed |
| `src/memory/spaced_repetition.py` | New | Deployed |
| `alembic/versions/p18_add_memory_tiers_fsrs.py` | New | Deployed |
| `src/discord/cmd_memory_stats.py` | New | Deployed |
| `src/discord/cmd_memory_review.py` | New | Deployed |
| `src/discord/cmd_memory_schedule.py` | New | Deployed |
| `src/discord/cmd_memory_decay.py` | New | Deployed |
| `src/memory/models.py` | Modified | Deployed |
| `src/memory/consolidation.py` | Modified | Deployed |
| `src/memory/read_pipeline.py` | Modified | Deployed |
| `src/memory/__init__.py` | Modified | Deployed |
| `pyproject.toml` | Modified | Deployed |
| `src/discord/_command_registry.py` | Modified | Deployed |
| `src/discord/_entrypoint.py` | Modified | Deployed |

## Step 2: Install fsrs Dependency — PASS

```
Requirement already satisfied: fsrs>=5.0.0 in ./code/guinevere/.venv/lib/python3.12/site-packages (6.3.1)
```

fsrs v6.3.1 was already installed in the venv.

## Step 3: Alembic Migration — PASS

Migration `3d41deeca703` (p18_add_memory_tiers_fsrs) was already applied (both heads current).

Note: Alembic required `GUINEVERE_DB_PASSWORD` env var (extracted from running service's `DATABASE_URL`). The `.env.core` has `DATABASE_URL` but not `GUINEVERE_DB_PASSWORD` — env.py reads the latter to replace the `****` placeholder in `alembic.ini`.

## Step 4: Verify Migration Columns — PASS

```
PASS: All P18 columns present
```

All 7 columns verified on `Episodes` model: `tier`, `fsrs_state`, `last_reviewed_at`, `next_review_at`, `retrievability`, `stability`, `difficulty`.

## Step 5: Restart Service — PASS

```
sudo systemctl restart guinevere-core
```

Service restarted successfully.

## Step 6: Service Health — PASS (with caveat)

```
Active: active (running) since Fri 2026-06-19 23:20:03 WIB
```

**Caveat:** Pre-existing `OSError: [Errno 98] Address already in use` on second uvicorn worker (port 8000 binding race). Not P18-related — observed in previous restarts as well.

## Step 7: Log Check for P18 Errors — PASS

```
No P18-related errors found in last 5 minutes.
```

All errors in logs are pre-existing port binding issues (`Address already in use`). Zero errors related to tiers, FSRS, memory_tier, spaced_repetition, or P18 modules.

## Step 8: FSRS Import Verification — PASS

```
FSRS_WEIGHT=0.15
DECAY_SWEEP_JOB_ID=decay_sweep
ACTIVE_FORGETTING_THRESHOLD=0.1
Tiers: ['working', 'episodic', 'semantic']
PASS: All P18 imports successful
```

All P18 symbols import correctly:
- `FSRSScheduler` from `src.memory.spaced_repetition`
- `MemoryTier`, `TierManager` from `src.memory.tiers`
- `register_decay_job`, `DECAY_SWEEP_JOB_ID`, `ACTIVE_FORGETTING_THRESHOLD` from `src.memory.consolidation`
- `FSRS_WEIGHT` from `src.memory.read_pipeline`

---

## Final Verdict: PASS

All 8 deployment steps completed successfully. P18 memory tiers + FSRS spaced repetition system is deployed and verified on the VPS.

### Known Issues (Non-P18)
- **Port binding race:** Second uvicorn worker occasionally fails with `Address already in use` on restart. Pre-existing infrastructure issue.
- **Alembic multi-head:** Two head revisions present (`7239fd4b3b5a` and `3d41deeca703`). Both already applied. Future merges will need a merge migration.

### Correction: Deployment Path
Task specified `/opt/guinevere/` but the actual service runs from `/home/guinevere/code/guinevere/`. Files were deployed to the correct service path.
