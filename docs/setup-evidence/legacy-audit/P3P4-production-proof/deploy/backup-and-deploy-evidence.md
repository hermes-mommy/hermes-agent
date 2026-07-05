# Backup and Deploy Evidence (P3P4 Production Proof)

**Date:** 2026-06-27  
**Operator:** Guinevere (orchestrator)  
**VPS:** guinevere-vps (faiz-prod-01)

---

## Pre-Deploy State

- **VPS git HEAD:** `123a31a` (P11) — but 20 files SCP'd uncommitted (P19+P20 runtime state)
- **Pre-existing P19 deploy:** `models.py` already had project_id at line 266 (P19 deploy added it)
- **Lane B/C code NOT present** on VPS before this deploy:
  - `consolidation.py`: 0 `ProjectRegistry` references
  - `persona_plugin.py`: 0 `_check_consent` references
  - `src/consent/revocation_handler.py`: did not exist
  - `src/memory/embedding_backfill.py`: did not exist

## Backup

**Backup dir:** `/home/guinevere/backups/p3p4-pre-deploy-20260627-1858/`

**Source file backups (10 files):**
- `models.py`, `consolidation.py`, `write_pipeline.py`, `main.py`
- `persona_plugin.py`, `safety_plugin.py`, `cmd_consent.py`, `prompt_loader.py`
- `yandere_fsm.py`, `db.py`

**DB schema backup:** `guinevere-db-memory-persona-consent.sql` (107K)
- Dumped schemas: memory, persona, consent, audit (the schemas Lane B/C touch)
- Full DB dump blocked by `health` schema permissions (guinevere_core lacks ACCESS on health.* — not Lane B/C scope; health data is P14 wearable, separate ownership)
- **No new DB migration needed** — project_id columns already deployed in P19; Lane B/C are pure application-code fixes

## Deploy

**Method:** SCP to `/tmp/p3p4-deploy/` → `cp` into `src/` tree

**Files deployed (13):**
1. `src/memory/models.py` — SemanticFacts project_id/project_scope ORM
2. `src/memory/consolidation.py` — project-aware consolidation
3. `src/memory/write_pipeline.py` — store_episode_batch project forwarding + _opt_uuid_field
4. `src/core/main.py` — EmbeddingService wired into life-kernel recall
5. `src/memory/embedding_backfill.py` (NEW) — idempotent NULL embedding backfill
6. `src/consent/__init__.py` (NEW)
7. `src/consent/revocation_handler.py` (NEW) — ConsentRevocationHandler
8. `src/hermes/plugins/persona_plugin.py` — consent + HARD STOP gates + streak_count
9. `src/hermes/safety_plugin.py` — ConsentRevocationHandler → SafeModeController bridge
10. `src/discord/cmd_consent.py` — on_consent_revoked integration
11. `src/core/services/prompt_loader.py` — _get_live_mood()
12. `src/persona/yandere_fsm.py` — persist() method
13. `src/memory/db.py` — write_yandere_state() helper

**Syntax check (venv):** ALL 11 files parse OK (ast.parse)

## Restart

**Command:** `sudo systemctl restart guinevere-core`  
**Time:** 19:24:51 WIB  
**Post-restart:**
- `systemctl is-active` → active
- NRestarts=0, Result=success
- ActiveEnterTimestamp=Sat 2026-06-27 19:24:51 WIB
- `/health` → `{"status":"healthy","service":"guinevere-core"}`
- `/metrics` → 200 OK
- heartbeat_liveness_check running (latency ~10ms)

## Rollback Plan

```bash
# Restore from backup
BKDIR=/home/guinevere/backups/p3p4-pre-deploy-20260627-1858
cd /home/guinevere/code/guinevere
cp $BKDIR/models.py src/memory/models.py
cp $BKDIR/consolidation.py src/memory/consolidation.py
# ... (all 10 backed-up files)
rm -rf src/consent  # remove new module
rm src/memory/embedding_backfill.py
sudo systemctl restart guinevere-core
# DB restore (if needed):
# psql < $BKDIR/guinevere-db-memory-persona-consent.sql
```

## Soak Clock Reset (honest documentation)

The deploy restart reset the P20 soak clock:
- **Old clock:** 2026-06-27 15:31:10 WIB → target 2026-06-28 15:31:10 WIB
- **New clock:** 2026-06-27 19:24:51 WIB → target **2026-06-28 19:24:51 WIB**

This is documented honestly in `soak-monitoring.md`. P20 remains in EARLY PRODUCTION ACCEPTANCE (operator waived 24h soak). The deploy was necessary to fix CRITICAL safety bugs (consent revocation source-false, consolidation NOT NULL crash). P20 health is clean post-deploy (NRestarts=0, 0 fallback, 0 blockers).

**Per AGENTS.md §0.1:** the restart was a policy-gated engineering deployment (backup → patch → restart only touched service → smoke → runtime proof → rollback path). Only `guinevere-core` restarted; no other services touched.

## No Secrets Exposed

- Discord token: SOPS-encrypted, never printed (Discord REST check done via service logs confirming `message_id=1519135545501028549` edits)
- DB password: loaded from `.env.core` via `source`, never printed
- All redacted in evidence files
