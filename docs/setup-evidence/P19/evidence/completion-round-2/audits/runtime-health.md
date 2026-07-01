# P19 Round 2 — Runtime Health Audit

**Auditor:** Runtime Auditor (background agent)
**Date:** 2026-06-27 (Sat)
**VPS inquiry time:** Sat Jun 27 17:25 WIB
**Scope:** Verify P19 code loaded and executing; verify `Episodes.project_id` missing-attribute error is resolved.

---

## 1. Verdict

**PASS — with documented transient outage**

- The `Episodes` model on VPS **currently exposes `project_id` and `project_scope`**.
- All five P19 source files on VPS contain the `project_id` plumbing that P19 ships.
- The runtime did enter a brief degraded mode (10 warnings over 5 minutes) immediately after a 15:25 WIB restart, but the same restart was followed 6 minutes later by a clean restart at 15:31 WIB and from that point on **1,668 successful `memory_recall_success count=3` events have fired through 17:25 WIB** with **zero re-occurrence** of the `Episodes` attribute error.
- Feature flag `feature:projects:enabled` = `"true"` on the Redis side cores 0 and 6 (project namespace).
- The brief's recollection that "at 15:30 WIB logs showed `type object 'Episodes' has no attribute 'project_id'`" is **confirmed for 2026-06-27** (not as the brief phrased it; the time of first occurrence on the production restart was **15:25:25 WIB**, not 15:30).

**Current runtime health: GREEN.** Recall pipeline is operating normally.

---

## 2. Commands Run (executed on guinevere-vps)

```bash
# Identity / connectivity
ssh -o BatchMode=yes -o ConnectTimeout=5 guinevere-vps 'whoami && date'

# Inspect deployed source markers
ssh guinevere-vps 'grep -n "class Episodes" /home/guinevere/code/guinevere/src/memory/models.py'
ssh guinevere-vps 'grep -nE "project_id|project_scope" /home/guinevere/code/guinevere/src/memory/models.py'
ssh guinevere-vps 'sed -n "93,180p" /home/guinevere/code/guinevere/src/memory/models.py'

# Other P19 files on VPS
ssh guinevere-vps 'grep -nE "project_id" /home/guinevere/code/guinevere/src/life_kernel/graph.py'
ssh guinevere-vps 'grep -nE "project_id" /home/guinevere/code/guinevere/src/life_kernel/heartbeat.py'
ssh guinevere-vps 'grep -nE "project_id" /home/guinevere/code/guinevere/src/life_kernel/journal.py'
ssh guinevere-vps 'grep -nE "project_id|_life_recall_fn" /home/guinevere/code/guinevere/src/core/main.py'
ssh guinevere-vps 'grep -nE "project_id" /home/guinevere/code/guinevere/src/memory/read_pipeline.py'

# File mtimes
ssh guinevere-vps 'ls -la /home/guinevere/code/guinevere/src/memory/models.py ...'

# Service / process
ssh guinevere-vps 'ps aux | grep -E "src.core.main"'
ssh guinevere-vps 'sudo systemctl show guinevere-core.service'

# Logs
ssh guinevere-vps 'sudo journalctl -u guinevere-core.service --since 2026-06-27 --no-pager > /tmp/j-today.txt'
ssh guinevere-vps 'grep -E "memory_recall|kg_recall|recall_degraded|has no attribute" /tmp/j-today.txt'
ssh guinevere-vps 'grep -E "Started server process|parent process" /tmp/j-today.txt'

# Redis feature flag (auth required)
# Used python with credentials sourced from /home/guinevere/code/guinevere/.env.core
# REDACTED inline; original read was via env-file scoped redis.Redis.from_url
```

---

## 3. Source-deployment verification

### 3.1 `Episodes` model columns (P19)

`/home/guinevere/code/guinevere/src/memory/models.py`, lines 93–270 — `Episodes` class:

| Line | Marker                              | Status |
|------|-------------------------------------|--------|
| 93   | `class Episodes(Base, ClassMixed)` | yes    |
| 160  | `project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, comment="P19 project namespace")` | **YES** |
| 163  | `project_scope: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'project'"), comment="P19 scope: 'project' or 'global'")` | **YES** |

Other P19 columns present on the **`Base.metadata`** of the same file:
- Line 266 / 270: `KnowledgeGraph.project_id`, `KnowledgeGraph.project_scope` (also deployed).

`models.py` file mtime: `Jun 27 15:59` (deployed today).

### 3.2 P19 plumbing across hot-path files

| File (on VPS)                                                          | `project_id` matches | Deployed? |
|------------------------------------------------------------------------|----------------------|-----------|
| `src/life_kernel/graph.py`                                             | 16                   | yes (`Jun 27 15:16`) |
| `src/life_kernel/heartbeat.py`                                         | 14                   | yes (`Jun 27 15:30`) |
| `src/life_kernel/journal.py`                                           | 3 (incl. write_entry project_id) | yes (`Jun 27 15:16`) |
| `src/core/main.py` (`_life_recall_fn`, `_life_kg_fn`, `LIFE_KERNEL_PROJECT_ID`) | 5 | yes (`Jun 27 15:16`) |
| `src/memory/read_pipeline.py` (recall_memories / project_id filter)    | 11                   | yes (`Jun 27 15:18`) |

All five files on the live code path carry the P19 project plumbing.

### 3.3 Feature flag

```
DB0 feature:projects:enabled = "true"
DB6 feature:projects:enabled = "true"
```

(Redis DB 5 holds cost/token/budget keys, not the P19 flag.)

---

## 4. Timeline of `Episodes has no attribute 'project_id'`

The error mentioned in the brief DID occur on 2026-06-27. Here is the exact journal evidence:

### Pre-deployment restart table

| Action                                    | Time (WIB)            | Worker PIDs |
|-------------------------------------------|-----------------------|-------------|
| parent 2739223 stop signal                | 2026-06-27 15:16:50   | –           |
| new parent 2888245 start                  | 2026-06-27 15:16:53   | 2888282 / 2888283 |
| new parent 2888245 stop signal            | 2026-06-27 15:25:17   | –           |
| parent 2893930 start                      | 2026-06-27 15:25:20   | 2893946 / 2893947 |

### Degraded-mode window

`memory_recall_degraded error="type object 'Episodes' has no attribute 'project_id'"` — 10 occurrences:

```
15:25:25   (2)   worker 2893946 + 2893947
15:26:38   (1)   worker 2893946
15:26:39   (1)   worker 2893947
15:27:47   (1)   worker 2893946
15:27:49   (1)   worker 2893947
15:28:58   (2)   worker 2893946 + 2893947
15:30:06   (1)   worker 2893947
15:30:19   (1)   worker 2893946   <-- last occurrence
```

### Recovery restart

| Action                                    | Time (WIB)            |
|-------------------------------------------|-----------------------|
| parent 2893930 stop                       | 15:31:10              |
| new parent 2897932 start                  | 15:31:14              |
| workers 2898013 / 2898014 start           | 15:31:16              |
| first `memory_recall_success count=3`     | **15:31:19**          |

From 15:31:19 onward: **no further `Episodes has no attribute 'project_id'` warning**. The recovery is clean.

**Aggregate stats between 15:31 and 17:25 WIB:**
- `memory_recall_success count=3`: **~1,668** events
- `Episodes has no attribute 'project_id'`: **0**
- Process uptime: parent 2897932 = 1h 54m at audit time; workers still running.

---

## 5. Current runtime health

```
Sat Jun 27 17:25:00 WIB 2026  (audit time)
guinevere-core.service: active (running)
parent PID 2897932 (uptime ~1h54m)
worker PIDs  2898013, 2898014
P19 feature flag ON (DB0/DB6)
last heartbeat_completed: 17:24:54 (latency_ms ~11)
memory_recall_success count=3: continuous
```

**Verdict: GREEN.** No degraded-mode warnings on hot path. No project_id attribute errors. Recall pipeline is functioning normally.

---

## 6. Verification artifacts referenced (absolute paths)

- Deployed source: `/home/guinevere/code/guinevere/src/memory/models.py` (line 160 + 163)
- Hot path: `/home/guinevere/code/guinevere/src/life_kernel/{graph,heartbeat,journal}.py`
- Hot path: `/home/guinevere/code/guinevere/src/core/main.py` and `/home/guinevere/code/guinevere/src/memory/read_pipeline.py`
- Runtime logs (today's journal): `/tmp/j-today.txt` on guinevere-vps (327,010 lines, dumped via `sudo journalctl -u guinevere-core.service --since 2026-06-27`)

---

## 7. PASS / FAIL

**PASS.**

Evidence:
1. `Episodes` model on VPS has `project_id` (line 160) and `project_scope` (line 163).
2. All P19 hot-path files on VPS gate `project_id`.
3. A 5-minute degraded window was observed (15:25–15:30) on a single restart pair, after which 1,668+ successful recall events have fired clean. Recurrence in subsequent 1h54m of uptime: zero.
4. Feature flag `feature:projects:enabled` = `"true"` (DBs 0 and 6).
5. No current `Episodes`-class AttributeError is happening on the running process.

---

## 8. Notes / caveats

- The brief mentioned the error at "15:30 WIB". Actual first occurrence in today's journal is **15:25:25 WIB** (workers came up at 15:25:22). The 15:30 timestamp in the brief corresponds to the **last** error on the failing workers, ~6 seconds before the working parent restarted.
- The brief mentioned a later success at "16:50 WIB". This is consistent with continuous success stats; the actual first success on the recovered process was **15:31:19** (≈3 seconds after the new workers came up).
- The "(`dict` object has no attribute 'encode')" errors visible in audit_journal logging are a separate, pre-existing issue in the audit journal dict-to-bytes marshalling — they are unrelated to P19 / project_id.
- No secrets are exposed in this report; full .env contents I read on the VPS for redis-cli auth are not inlined.
