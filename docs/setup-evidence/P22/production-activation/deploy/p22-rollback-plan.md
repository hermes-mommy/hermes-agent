# P22 Production Activation — Rollback Plan

**Date:** 2026-06-27
**Commits to roll back:** `ec53f70` (P22 core), `fdf6f33` (Phase B wiring)
**Backup:** `/home/guinevere/data/backups/guinevere-p22-predeploy-20260627T150750Z.sql.gz` (1.38 GB, sha256 generated)
**Code snapshot:** `/home/guinevere/data/backups/guinevere-code-bak-20260627T150750Z`

## When to Roll Back

- P22 activation causes a P20 runtime incident (crash loop, recursion, fallback storm, OOM, dashboard failure, privacy leak).
- HARD STOP or consent gate is found bypassed (safety regression).
- A critical/high audit finding (round 1 or 2) cannot be fixed in-situ.

## Rollback Procedure

### Step 1: Code rollback (VPS)

```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && \
  git checkout HEAD~2 -- src/life_integrations src/core/main.py alembic/versions/p22_001_integration_schema.py alembic/versions/p19_003_audit_chain_version.py 2>/dev/null; \
  # OR restore from code snapshot: \
  # cp -a /home/guinevere/data/backups/guinevere-code-bak-20260627T150750Z/* . \
  # (snapshot has no .env, no .venv — preserves secrets/venv)'
```

Alternative (git-based, cleanest): on VPS, `git checkout` to the commit before `ec53f70`.

### Step 2: Migration rollback — WORM CAVEAT

**Hard rule:** If `audit.integration_api_log` has ANY rows, DO NOT downgrade
the migration (would destroy WORM audit chain). Roll back CODE ONLY, leave
schema, restart, investigate.

```bash
# Check if audit table has rows FIRST:
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs) && \
  .venv/bin/python -c "
import asyncio, asyncpg, os
async def m():
    c = await asyncpg.connect(os.environ[\"DATABASE_URL\"].replace(\"postgresql+asyncpg://\",\"postgresql://\"))
    print(\"integration_api_log rows:\", await c.fetchval(\"SELECT count(*) FROM audit.integration_api_log\"))
    await c.close()
asyncio.run(m())"'
```

- If rows = 0 AND p22.integration_registry rows = 0: `alembic downgrade p19_003_audit_chain_version` is safe (drops the 3 new tables).
- If rows > 0: **code-only rollback**, leave schema, document the state.

### Step 3: Restart guinevere-core ONLY

```bash
ssh guinevere-vps 'sudo systemctl restart guinevere-core && sleep 15 && systemctl is-active guinevere-core'
# Verify P22 is gone (no p22.* logs, app starts clean)
ssh guinevere-vps 'sudo journalctl -u guinevere-core --since "1 min ago" --no-pager | grep -c p22'
# Expect 0 (P22 not loaded after code rollback)
```

### Step 4: Verify P20 restored

```bash
ssh guinevere-vps 'systemctl is-active guinevere-core; \
  sudo journalctl -u guinevere-core --since "2 min ago" --no-pager | grep -c hermes_brain_think_complete; \
  redis-cli -a "$REDIS_PW" --no-auth-warning GET life_kernel:hard_stop'
# Expect: active, >0 think_complete, hard_stop empty
```

### Step 5: Verify other services undisturbed

```bash
ssh guinevere-vps 'for s in guinevere-9router 9router-proxy guinevere-discord guinevere-mcp guinevere-whatsapp guinevere-monitoring guinevere-obscura guinevere-x-poster cloudflared docker; do echo "$s: $(systemctl is-active $s)"; done'
# All must be active
```

## DB Restore (only if migration downgrade corrupted data)

```bash
ssh guinevere-vps 'docker exec -i guinevere-postgres psql -U guinevere < <(gunzip -c /home/guinevere/data/backups/guinevere-p22-predeploy-20260627T150750Z.sql.gz)'
# Note: continuous_agg circular FK may need --disable-triggers
```

## P22 Lifespan Fail-Open Guarantee

Even without rollback, P22 is designed to fail OPEN for the app: the lifespan
injection is wrapped in try/except — if `build_runtime_registry` raises,
guinevere-core continues with `app.state.p22_registry = None` (P22 inactive,
all adapters CONFIG_MISSING). P22 cannot take down guinevere-core.

## Footer

Rollback is code-only in the common case (WORM audit protection). Backup +
code snapshot exist. Procedure verified feasible.
