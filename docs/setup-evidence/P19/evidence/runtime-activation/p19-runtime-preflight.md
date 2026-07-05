# P19 Runtime Activation — Preflight

**Date:** 2026-06-27 10:50 WIB
**Author:** Guinevere (parent)
**Phase:** RA-1 — Runtime Preflight

---

## 1. Live VPS Service State

| Service | ActiveState | NRestarts | ActiveEnterTimestamp |
|---|---|---|---|
| guinevere-core | active | 0 | Thu 2026-06-25 08:26:43 WIB |
| guinevere-discord | active | 0 | Thu 2026-06-25 19:45:01 WIB |
| guinevere-mcp | active | 0 | Thu 2026-06-25 09:08:27 WIB |
| guinevere-9router | active | 0 | Thu 2026-06-25 16:36 WIB (approx) |
| guinevere-gateway | inactive | — | Tue 2026-06-23 09:55:08 WIB (expected inactive) |

## 2. P20 Baseline Health (Pre-Activation)

| Metric | Value |
|---|---|
| Service | active |
| NRestarts | 0 |
| Brain think_complete | active (10:48:34, model=guinevere) |
| Brain fallback | 0 |
| hard_stop_requested | False |
| Blockers | 0 |

**P20 is healthy. Baseline captured before activation.**

## 3. Live DB State

| Check | Value |
|---|---|
| Alembic stamps | `p19_001_project_namespaces`, `p19_002_project_id_not_null`, `p19_003_audit_chain_version`, `p20_001_life_kernel_schema` |
| projects.project_registry default project | id=00000000-0000-0000-0000-000000000001, slug=default, status=active |
| project_id columns | 20 (across all schemas — P19 scope + financial.transactions pre-existing) |
| chain_version columns | 1 (audit.audit_trail) |
| memory.semantic_facts | 6 rows |
| memory.kg_entities | 6 rows |
| consent.consent_ledger | 7 rows |
| life_kernel.audit_journal | 5,144 rows |

**No missing P19 schema. All schema gates PASS.**

## 4. Live Redis State

| DB | Key | Value | Rollback |
|---|---|---|---|
| db0 | feature:projects:enabled | None (OFF) | `DEL feature:projects:enabled` or `SET feature:projects:enabled false` |
| db6 | feature:projects:enabled | None (OFF) | same |

life_kernel keys live in db0 + db6 (REDIS_URL points to db5 but life_kernel:* keys are in db0/db6 — same-conn set/get). Flag must be set in the DB the runtime reads. Runtime reads via `_is_projects_flag_on(redis_client)` — the redis_client used by cognition/heartbeat connects to the DB where life_kernel keys live.

## 5. Runtime Code-Load Gap — CRITICAL FINDING

### 5.1 File mtimes vs Service ActiveEnter

| File | mtime | vs core ActiveEnter (08:26:43 06-25) |
|---|---|---|
| src/core/main.py | 2026-06-25 20:30:37 | AFTER start (running process has OLD main.py) |
| src/life_kernel/cognition.py | 2026-06-25 20:30:25 | AFTER start |
| src/life_kernel/redis_client.py | 2026-06-25 20:30:29 | AFTER start |
| src/life_kernel/graph.py | 2026-06-25 20:30:34 | AFTER start |
| src/life_kernel/dashboard_writer.py | 2026-06-25 20:30:27 | AFTER start |
| src/life_kernel/heartbeat.py | 2026-06-25 19:42:43 | AFTER start |
| src/projects/* (most) | 2026-06-25 16:36 | AFTER start |
| src/projects/secrets_vault.py | 2026-06-27 08:42:38 | AFTER start |
| src/discord/cmd_project.py | 2026-06-27 08:42:36 | AFTER start (discord started 19:45 06-25) |
| src/discord/project_session.py | 2026-06-27 08:42:36 | AFTER start |

### 5.2 Running Process Verification

- `MainPID=806559` started 2026-06-25 08:26:43 WIB.
- Startup log at 08:26 shows `heartbeat_service_started` but **NO `cognition_registry_initialized` log** — the post-P19 main.py line 434 (`logger.info("cognition_registry_initialized", max_active=3)`) was NOT emitted at startup because the running process loaded the PRE-P19 main.py.
- `cognition_registry_initialized` does not appear ANYWHERE in core logs since 08:26 start.
- `ProjectAwareCognitionRegistry` / `project_id` do not appear in core runtime logs.

### 5.3 Conclusion

**The running `guinevere-core` process does NOT have the P19 runtime activation code loaded.** The P19 life_kernel files (flag-read paths, ProjectAwareCognitionRegistry, project_id wiring in heartbeat/graph/cognition) were scp'd to the VPS at 20:30 on 2026-06-25 — ~12 hours AFTER the core process started at 08:26.

**A restart of `guinevere-core` is REQUIRED** to load the P19 runtime activation code. Flipping the flag alone is insufficient — the running code doesn't read it.

⚠️ **This means touching the P20-closed `guinevere-core` service.** Per AGENTS.md §0.1, the P20 Living Autonomy Kernel runtime is autonomous-by-default with policy gates (backup → canary → smoke test → rollback). A controlled restart with backup+rollback+smoke-test gates satisfies this. P20 is CLOSED under operator waiver — the waiver is voided only by a runtime incident (crash/recursion/fallback-storm/OOM/dashboard-fail/privacy-leak). A clean restart that comes back healthy does NOT void the waiver; it resets the soak clock (new ActiveEnter + 24h target) but that is an accepted consequence of activating P19.

## 6. Discord `/project` Gap

### 6.1 Registration Status

- `cmd_project.py` and `project_session.py` exist on VPS (scp'd 2026-06-27 08:42) and import cleanly.
- **BUT** they are NOT referenced in `_entrypoint.py`, `_command_registry.py`, or `_startup.py`.
- The active discord bot's slash command tree has "13 wired + 20 stubs" registered in `setup_hook` — `/project` is NOT among them.
- `guinevere-discord.service` started 2026-06-25 19:45 — before cmd_project.py was scp'd (08:42 06-27), so even if it were referenced, the running bot wouldn't have it.

### 6.2 Conclusion

**Discord `/project` UX is NOT activatable by flag-flip or restart alone.** It requires:
1. Code wiring: register `cmd_project` in the bot's command tree (in `_entrypoint.py` setup_hook or a cog loader).
2. Bot restart.

This is a **code change + bot restart**, beyond a pure flag activation. Per the operator's allowed statuses, this points toward **"P19 RUNTIME ACTIVATED — UX DEFERRED"**: activate the core runtime (flag + core restart + project_id proof) now, defer Discord `/project` UX until the command is wired into the bot (separate work item).

## 7. Project Behavior Proof Design

### 7.1 Concrete Runtime Action (must produce/use project_id)
- After flag ON + core restart, the `ProjectAwareCognitionRegistry` initializes and `heartbeat` resolves a `thread_id` using the project namespace when flag is ON.
- The `observe_node` / `decide_node` path should carry a `project_id` in the graph state when flag is ON.
- Audit journal writes (`life_kernel.audit_journal`) should carry project_id in the entry metadata when flag is ON.

### 7.2 Concrete Memory/Query/Task/Audit Proof
- **Memory**: a project-scoped query via `ProjectScopedMemoryStore` returns only default-project facts (6 facts, all default).
- **Audit**: `life_kernel.audit_journal` new rows after activation include `project_id` in the JSONB entry (chain_version=2 semantics).
- **Graph state**: heartbeat logs show `project_id` field populated (not None) when flag is ON.

### 7.3 Expected DB Rows/Log Lines After Activation
- Core startup log: `cognition_registry_initialized max_active=3`
- Heartbeat logs: `project_id=00000000-0000-0000-0000-000000000001` (or the resolved default)
- New `life_kernel.audit_journal` rows with project_id in metadata
- No new errors, no traceback, no recursion

### 7.4 No-Regression Proof for P20
- NRestarts stable after the controlled restart (0 after restart).
- Brain think_complete active, 0 fallback.
- Dashboard editing canonical id.
- hard_stop_requested=False.
- No GraphRecursionError, no traceback.
- Memory healthy (no OOM).

## 8. Preflight Verdict

| Gate | Status |
|---|---|
| Service state captured | ✅ |
| DB state verified (no schema gap) | ✅ PASS — no redeploy needed |
| Redis flag state (OFF, rollback ready) | ✅ |
| Code-load gap identified | ⚠️ core restart REQUIRED (running process has pre-P19 code) |
| Discord /project gap identified | ⚠️ UX DEFERRED (not wired into bot command tree) |
| Project behavior proof designed | ✅ |
| P20 baseline captured | ✅ healthy |

**Deployable: YES, with controlled core restart. Discord UX deferred.**

## 9. Footer

| Field | Value |
|---|---|
| Preflight status | PASS (with 2 gaps documented: core-restart-required, discord-UX-deferred) |
| Next step | Write activation plan |