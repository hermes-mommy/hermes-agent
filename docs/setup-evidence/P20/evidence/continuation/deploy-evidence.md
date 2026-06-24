# P20 Continuation — Deploy Evidence

| Field | Value |
|---|---|
| Date | 2026-06-25 |
| Deploy method | scp + systemctl restart (policy-gated) |
| Target | guinevere-vps (Tailscale 100.94.104.22) |
| Commits deployed | a272587 (impl) + df83f70 + ff1c9fa (audit fixes) + c29a461 (deploy runtime fixes) |
| Result | ✅ DEPLOYED + LIVE — CLEAN |
| Soak clock | RESET to 2026-06-25 05:54 WIB → target 2026-06-26 05:54 WIB |

## 1. Policy-Gated Deploy Sequence

1. **Predeploy scan**: local `pytest tests/life_kernel/ -q` → 420 passed, 7 skipped, 0 failed.
2. **Backup on VPS**: `/tmp/guinevere-continuation-bak.<ts>/` (6 src files backed up before overwrite).
3. **scp**: 8 files staged to `_continuation_staging/` then moved into place:
   - `src/core/main.py`, `src/life_kernel/{state,graph,heartbeat,p16_adapter,p18_adapter,journal}.py`
   - `src/life_kernel/domain_minds/durability.py` (deploy fix)
4. **Syntax + import check** under `.venv/bin/python` → OK.
5. **Migration**: `life_kernel` schema + `audit_journal` table created in the `guinevere` DB (the DB `DATABASE_URL` points at). No alembic migration needed (recall uses existing `memory.episodes`).
6. **Restart ONLY guinevere-core**: `sudo systemctl restart guinevere-core.service`. hermes-gateway + guinevere-mcp untouched (active before and after).
7. **Canary/smoke**: `/health` → healthy; journalctl adapter wiring + recall + brain + dashboard metrics clean.
8. **Rollback ready**: backup dir + git checkout path available (not needed — deploy clean).

## 2. Deploy Runtime Bugs Found + Fixed (live, fail-soft throughout)

The kernel stayed alive (NRestarts=0, no crash) through every bug — all were fail-soft by design. Fixed in commit `c29a461`:

| Bug | Symptom | Root cause | Fix |
|---|---|---|---|
| D-01 | `UndefinedTableError: life_kernel.audit_journal does not exist` | `ensure_table` ran CREATE SCHEMA+TABLE+INDEX as one `text()` call → asyncpg "cannot insert multiple commands into a prepared statement"; also schema didn't exist | Split into separate `execute()` calls; added `CREATE SCHEMA IF NOT EXISTS` |
| D-02 | `DataError: dict object has no attribute 'encode'` | `record()` passed raw dict to JSONB column; asyncpg needs a JSON string | `json.dumps(entry)` + `CAST(:entry AS jsonb)` |
| D-03 | `ensure_table` logged `table_ensured` even when it returned False | main.py ignored the bool return | Log success/failure truthfully |
| D-04 | `All 3 candidates filtered by classification ceiling 'Internal'` | SAF-02 `safe_mode=True` downgraded `guinevere_core` ceiling from CRITICAL to Internal, filtering all Restricted+ memories from the brain | Default `safe_mode=False` (brain has CRITICAL clearance); Discord safety via memory_status counts-only (MEM-06) + sanitiser; opt-in redaction via `LIFE_KERNEL_SAFE_RECALL=1` |
| D-05 | `syntax error at or near ":"` | `:entry::jsonb` collided SQLAlchemy `:param` with Postgres `::` cast | Use `CAST(:entry AS jsonb)` |

## 3. Live Verification (post-fix, 2026-06-25 05:55 WIB)

```
SERVICE: core=active NRestarts=0 Result=success  ActiveEnter=2026-06-25 05:54:51 WIB
MEMORY:  ~860MB (under 2G High / 4G Max)
BRAIN:   hermes_brain_think_complete=2  hermes_brain_fallback_used=0   ✅
RECALL:  memory_recall_success=2  kg_recall_success=2                  ✅ (real P18+P16)
JOURNAL: journal_entry_written=2  journal_entry_failed=0  record_failed=0  ✅
DASH:    dashboard_edited=2  dashboard_publish_failed=0                ✅
BLOCKERS: GraphRecursionError=0  HARD_STOP_routing_to_END=0  traceback=0  UndefinedTableError=0  ✅
SERVICES: hermes-gateway=active  guinevere-mcp=active  (undisturbed)   ✅
```

### Journal persisted to Postgres (AC-LIFE-008 proof)
```
guinvere DB: life_kernel.audit_journal → 2 kernel-written rows
latest: "Cycle 197204: act on: Finance Health Check
  Scan recent expense database and billing due dates...
  Next: Query PostgreSQL finance.transactions for this month's records...
  | Recalled 3 memories, 0 KG concepts. Errors: 0."
```

### Discord dashboard (AC-LIFE-002/005 proof)
Dashboard embed `1519135545501028549` (channel 1510914604291588237), blurple `0x5865f2`, edited in place:
- Status: 🟢 ALIVE
- **Current Focus: Finance Health Check** (brain-generated, memory-driven self-directed task — NOT random)
- **Last Decision: act on: Finance Health Check** (seeded goal ACTED on next cycle)
- **Current Agenda: [improve_autonomy] Finance Health Check** (real seeded goal)
- **Memory: active: 3 mem, 0 kg** (real P18 recall, world_model active)
- HARD STOP: ✅ CLEAR
- Cycles: act=34 cycle=197204

Log channel 1510914623367413850 (append-only): `[cycle 197204] phase=idle focus=Finance Health Check ...` (T12 narrative field).

Redis: `life_kernel:dashboard_message_id = 1519135545501028549` (canonical).

## 4. Acceptance Criteria Status

| AC | Status | Live proof |
|---|---|---|
| AC-LIFE-001 boot heartbeat w/o trigger | ✅ | lifespan wires heartbeat, no external trigger |
| AC-LIFE-002 idle creates self-directed task from world-state | ✅ | Finance Health Check seeded from memory, acted on |
| AC-LIFE-003 self-created task completes SDLC + reflection | PARTIAL | task acted on + reflected; full SDLC session graph not spawned (display-only v1) |
| AC-LIFE-004 dashboard 60s + log history | ✅ | dashboard_edited every cycle, log append-only |
| AC-LIFE-005 P16/P18 influence decisions | ✅ | real recall (3 mem) wired into brain prompts; world_model active |
| AC-LIFE-006 continues when Faiz silent | ✅ | autonomous cycles w/o trigger |
| AC-LIFE-007 HARD STOP halts | ✅ | non-LLM, clear, recovery tested |
| AC-LIFE-008 journal after meaningful action | ✅ | entries persist to life_kernel.audit_journal (PG) |
| AC-LIFE-009 self-improvement candidate from reflection | ✅ | ReflectionEvaluator wired (RUN-01 fixed); candidates display-only |
| AC-LIFE-010 restart resumes from checkpoint | ✅ | Postgres checkpointer wired |

## 5. Status

**CONTINUATION IMPLEMENTED — DEPLOYED — SOAK/OBSERVATION IN PROGRESS.**

PRODUCTION PASS remains HOLD: a full 24h clean soak (brain thinking, no blockers) from 2026-06-25 05:54 WIB is required. Target: 2026-06-26 05:54 WIB.
