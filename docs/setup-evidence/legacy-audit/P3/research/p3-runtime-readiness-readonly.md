# P3 (Memory Foundation) Runtime Readiness Assessment

## Audit Metadata

- **Date:** 2026-06-25
- **Agent:** Claude Code (subagent), read-only
- **Read-only affirmation:** YES. No runtime code, DB, secrets, or deployment touched.
- **Scope:** Scheduler wiring for consolidation/decay jobs; DB introspection; test reality (FakeSession vs live DB); Discord command wiring; systemd verification.

---

## Findings

### [CRITICAL] 1. Consolidation and Decay Schedulers Are Code-Complete But NOT Running

**Summary:** Both `register_consolidation_job` (P3-015, daily 03:00 ICT) and `register_decay_job` (P18-002, 6-hourly) are fully implemented in `src/memory/consolidation.py` and exported via `src/memory/__init__.py`, but **neither is ever called at runtime**. The sole application entrypoint (`src/core/main.py`) contains only a **commented-out comment block** (lines 22-38) explaining how to wire them. No other `main.py`, entrypoint, or startup module in the entire `src/` tree calls either function.

**Evidence:**
- `src/core/main.py:22-38`: Entirely commented block — "To activate the daily consolidation scheduler at runtime, inject ...". No active code.
- `grep -r register_consolidation_job src/` — hits only in `src/core/main.py` (comments), `src/memory/consolidation.py` (definition), and `src/memory/__init__.py` (export).
- `grep -r register_decay_job src/` — hits only in `src/memory/consolidation.py` (definition), `src/memory/__init__.py` (export). Zero call sites outside `tests/`.
- **All 8 subdirectories checked:** `src/gmail/`, `src/x_poster/`, `src/persona/`, `src/loops/`, `src/discord/`, `src/life_kernel/`, `src/hermes/`, `src/knowledge_graph/ingestion/` — none import or call `register_consolidation_job` or `register_decay_job`.
- P16-002 KG ingestion (lines 167-201 of `main.py`) IS wired with a real `AsyncIOScheduler` — this proves the pattern works, yet consolidation was deliberately left out.
- The docstring at `src/memory/consolidation.py:855` states the job is "An active APScheduler v3 AsyncIOScheduler instance", but this describes what the parameter *should be*, not what the runtime provides.
- Unit tests exist: `tests/memory/test_consolidation.py::TestSchedulerRegistration` (lines 491-549) verify `register_consolidation_job` against a fake scheduler. But these test only the registration logic, not the cron execution.

**Impact:** Episodic-to-semantic consolidation never runs in production. Episodes accumulate in `memory.episodes` but are never distilled into `memory.semantic_facts`. The KG ingestion pipeline (P16, which reads from `semantic_facts`) receives zero input on a production system unless someone has manually wired it or runs it via an external cron.

---

### [HIGH] 2. All 235 Memory Tests Use FakeSession / AsyncMock — No Real DB E2E

**Summary:** Every memory test (235 collected) uses `FakeSession` (in-memory dict) and `AsyncMock`. There are zero tests against a live PostgreSQL database. The E2E test file `tests/memory/test_memory_e2e.py` explicitly states on line 10: *"All tests use FakeSession + AsyncMock -- no live DB or network required."*

**Evidence:**
- `tests/memory/test_memory_e2e.py:136-171`: `FakeSession` class — stores episodes in `self.episodes: dict[object, object]`, fake `execute()` inspects SQL string for `"do_not_recall IS false"`.
- `tests/memory/test_memory_e2e.py:191-193`: `fake_session` fixture returns `FakeSession()`.
- `tests/memory/test_consolidation.py`: All async fixtures return `FakeSession` objects.
- `tests/memory/test_dnr.py`: Also uses `FakeSession`.
- `tests/memory/test_safe_mode_memory.py`: Uses `FakeSession`.
- `tests/memory/test_prompt_context_injection.py`: Uses mock session.

**Impact:** There is no regression safety net for real PostgreSQL behavior (serialization, constraint violations, concurrent access, index performance, TSVECTOR compute, GIN index usage). A migration that breaks the schema would pass all 235 tests.

---

### [MEDIUM] 3. DB Introspection: Alembic Heads at p19_002, DATABASE_URL Not Set in Environment

**Summary:** Alembic migration chain is complete (heads: `p19_002_project_id_not_null`). All 13 migrations from baseline through P19 are present. However, `DATABASE_URL` is not set in the current shell environment, so `alembic current` (to check which revision the actual database is on) cannot be run. This is a Windows development shell, not the production VPS.

**Evidence:**
- `alembic heads` shows: `p19_002_project_id_not_null`
- Migration chain: `2bed93fd1dd0 (baseline)` -> `e401bb5fd274 (47 tables)` -> `65f863220922 (search vector + DNR)` -> `7239fd4b3b5a` -> `3d41deeca703 (P18 tiers/FSRS)` -> `p6_gamification_schema` -> `p5_*` -> `p20_001_life_kernel_schema` -> `p19_001_project_namespaces` -> `p19_002_project_id_not_null (STUB)`
- `printenv DATABASE_URL` returns empty.
- The `p19_002` migration is documented as "STUB for P19-003 chain continuity" — it is a no-op that defers NOT NULL enforcement.

**Needs verification on VPS:** `alembic current` against the actual PostgreSQL database to confirm the production DB is at the expected head revision, and that all P3 migrations (especially `65f863220922` for TSVECTOR/DNR) have been applied.

---

### [MEDIUM] 4. Discord Memory Commands ARE Wired to Live Pipeline (Conditional on DB)

**Summary:** `/memory-search` and `/memory-add` are registered in `src/discord/_entrypoint.py` (lines 268-277) and call `recall_memories` / `store_episode` respectively through a lazy `get_session_factory()` on the bot client. If `DATABASE_URL` is set, the session factory creates a real `async_sessionmaker` backed by a real engine. If `DATABASE_URL` is absent, the commands return a "Database not configured" warning.

**Evidence:**
- `src/discord/_entrypoint.py:268-277`: `self.tree.command(name="memory-search", ...)(memory_search_callback)` and same for `memory-add`.
- `src/discord/_entrypoint.py:573-604`: `GuinevereBot.get_session_factory()` — lazily creates `create_async_engine(DATABASE_URL)` -> `async_sessionmaker(engine)`.
- `src/discord/cmd_memory_search.py:376-416`: Fetches `session_factory_fn` from `client.get_session_factory`, imports `recall_memories`, calls it with `safe_mode=False, principal="guinevere_core"`.
- `src/discord/cmd_memory_add.py:356-396`: Same pattern, imports `store_episode`, writes with `classification="Restricted"`.
- P18 commands also wired: `cmd_memory_decay`, `cmd_memory_forget`, `cmd_memory_export`, `cmd_memory_review`, `cmd_memory_schedule`, `cmd_memory_stats` — all registered at lines 229-233 of `_entrypoint.py`.

**Impact:** These commands work at runtime IF and only IF `DATABASE_URL` is set and the PostgreSQL database is reachable from the Discord bot process. No production verification was possible from this read-only audit.

---

### [MEDIUM] 5. `recall_memories` Is Also Wired into Life Kernel and Hermes Plugins

**Summary:** Beyond Discord commands, `recall_memories` is consumed by the life kernel's `MemoryRecallAdapter` (at `src/life_kernel/p18_adapter.py`) and by the Hermes plugin system (`src/hermes_plugins/commands_memory/memory_search.py` and `src/hermes/_memory_bridge.py`). The `prompt_loader` service (`src/core/services/prompt_loader.py:257`) also calls `recall_memories` to inject memory context into system prompts.

**Evidence:**
- `src/core/main.py:257`: `from src.memory.read_pipeline import recall_memories as _recall_memories`
- `src/core/main.py:274-283`: Life kernel wraps `_recall_memories` with a per-call session and wires it into `MemoryRecallAdapter`.
- `src/hermes/_memory_bridge.py:147-153`: Imports and calls `recall_memories` in the Hermes bridge.
- `src/hermes_plugins/commands_memory/memory_search.py:103-108`: Plugin import and call.
- `src/core/services/prompt_loader.py:257`: System prompt assembly calls `recall_memories`.

**Impact:** `recall_memories` is a critical-path function for three runtime subsystems. Its correctness directly affects brain autonomy (life kernel), Hermes agent responses, and system prompt quality. Despite this, there is no live-DB test coverage.

---

### [LOW] 6. Systemd / service verification: Not possible on Windows

**Summary:** The audit environment is Windows 11 (bash shell via Git Bash). `systemctl` is not available. Verification of `guinevere-core.service` or `guinevere-discord.service` status requires the production VPS (Ubuntu 24.04).

**Needs VPS verification:**
```bash
systemctl status guinevere-core
systemctl status guinevere-discord  # expected masked (P2-022)
journalctl -u guinevere-core --no-pager -n 50
# Check logs for "consolidation" or "daily_consolidation" — should find nothing
# Check logs for "decay_sweep" — should find nothing
# Check logs for "kg_ingestion" — should find entries (P16 IS wired)
```

---

## Status Verdict

**PARTIALLY IMPLEMENTED**

The P3 Memory Foundation code is complete, well-structured, and exported through `src/memory/`. The Discord `/memory-search` and `/memory-add` commands are wired and functional. `recall_memories` is consumed by three active runtime subsystems (life kernel, Hermes plugins, prompt loader). However, the **daily consolidation cron (P3-015) and 6-hourly decay sweep (P18-002) are code-complete but never registered at startup** — they exist only as dead code. Without consolidation, semantic facts are never produced from episodes, and the KG ingestion pipeline (P16, which IS wired) receives no input. All 235 memory tests use FakeSession with no live-DB regression coverage.

---

## Recommendations (for mama — NO fixes from this agent)

1. **Wire consolidation into `src/core/main.py` lifespan:** Uncomment the block at lines 22-38 (or add the `AsyncIOScheduler` registration alongside the existing KG scheduler at lines 167-201). The KG ingestion already demonstrates the pattern — consolidation should join it. Both jobs run at different times (03:00 ICT vs 03:30 ICT) and can share one `AsyncIOScheduler` instance.

2. **Add at least one integration-style test** that runs against a test PostgreSQL (e.g., `testcontainers-postgres` or a CI service DB) for the critical `recall_memories` + `store_episode` round trip and the consolidation `consolidate_episodes_to_facts` function. The current 235 FakeSession tests provide no confidence in real SQL behavior.

3. **On the VPS, verify `alembic current`** matches `p19_002_project_id_not_null` and confirm no P3 migrations are pending.

4. **Verify log evidence** on the VPS: search journald logs for `daily_consolidation`, `decay_sweep`, and `consolidation_job_registered` — all should be absent unless consolidation was wired via an alternative mechanism not visible in this repo.
