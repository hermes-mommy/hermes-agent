# P19 Runtime Activation — Flag Enable Evidence

**Date:** 2026-06-27 11:35 WIB
**Author:** Guinevere (parent)
**Phase:** RA-2 Step 3 — Turn Feature Flag ON

---

## 1. Flag Activation

| Step | Action | Result |
|---|---|---|
| 1 | `redis SET feature:projects:enabled true` in **db6** (heartbeat reads) | `b'true'` |
| 2 | `redis SET feature:projects:enabled true` in **db0** (consistency) | `b'true'` |
| 3 | Verify runtime reads it: `_is_projects_flag_on(db6)` | **True** ✅ |

## 2. Why db6?

`src/core/main.py:367` wires the heartbeat redis_client as `redis://guinevere_core:<pw>@localhost:6380/6` — **db6**. The runtime `_is_projects_flag_on(redis_client)` helper reads the flag from whichever client is passed. Heartbeat/cognition pass the db6 client. So the flag must be ON in db6 for the heartbeat path to see it. db0 set for consistency (where life_kernel:dashboard_message_id lives).

## 3. LIFE_KERNEL_PROJECT_ID Env Var

The flag alone activates project-aware code paths, but `thread_id` scoping requires a `project_id`. In main.py:410, `_project_id = os.environ.get("LIFE_KERNEL_PROJECT_ID") or None`. Without it, `_resolve_thread_id(None)` returns legacy `"heartbeat"` even with flag ON (safe default: flag ON + project_id None = byte-identical P20 thread_id).

To produce **real project_id runtime proof**, set `LIFE_KERNEL_PROJECT_ID=00000000-0000-0000-0000-000000000001` (default project UUID) in `.env.core` (systemd EnvironmentFile). Required a core restart to load the env var.

| Action | Result |
|---|---|
| Append `LIFE_KERNEL_PROJECT_ID=00000000-0000-0000-0000-000000000001` to `.env.core` | Done |
| Restart core (env var load) | active, NRestarts=0, ActiveEnter 11:27:57 WIB |
| Verify env loaded | systemd EnvironmentFile loads .env.core; runtime uses default project UUID |

## 4. Flag + Project Context Live Verification

| Check | Result |
|---|---|
| `feature:projects:enabled` in db6 | `b'true'` ✅ |
| `_is_projects_flag_on(db6)` (runtime helper) | **True** ✅ |
| `LIFE_KERNEL_PROJECT_ID` env | `00000000-0000-0000-0000-000000000001` ✅ |
| thread_id scoped to project | `heartbeat-00000000-0000-0000-0000-000000000001` ✅ (PROOF) |

## 5. Rollback Command (instant, no restart)

```bash
# Rollback flag to OFF:
redis-cli -p 6380 -a <pw> -n 6 DEL feature:projects:enabled
redis-cli -p 6380 -a <pw> -n 0 DEL feature:projects:enabled
# (runtime re-reads flag each heartbeat cycle → P19 transparent, P20 byte-identical)
```

For full rollback to legacy thread_id: also remove/comment `LIFE_KERNEL_PROJECT_ID` from `.env.core` + restart core.

## 6. Footer

| Field | Value |
|---|---|
| Flag status | ON (db6 + db0) |
| Runtime reads flag | True |
| Project context env | set (default UUID) |
| Rollback | instant `DEL` flag (no restart) |
| Next step | Step 4: project runtime proof |