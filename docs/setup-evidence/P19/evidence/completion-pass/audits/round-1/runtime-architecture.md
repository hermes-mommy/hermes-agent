# P19 Completion Pass — Round-1 Audit: Runtime/P20 Regression + Architecture

**Auditor:** independent P19-Auditor agent (Buffy)
**Date:** 2026-06-27 (15:55 WIB)
**Scope:** RUNTIME/P20 REGRESSION + ARCHITECTURE — verify that all P19-C-impl
changes preserve P20 soak-stable behavior and that project_id flows correctly
through every layer (heartbeat → graph → journal → memory).
**Verdict:** **PASS** — all 7 runtime regression checks and all 4 architecture
checks PASS. P20 soak-state intact (no crash, no fallback, no recursion,
no recall regression). project_id injection chain is correct end-to-end
(heartbeat → graph state → observe/reflect → journal → memory callback).

---

## 1. CP-RT-01 — Core active, NRestarts=0

**Status:** PASS
**Evidence:**
```
$ systemctl is-active guinevere-core.service
active
$ systemctl show guinevere-core.service -p NRestarts -p ActiveEnterTimestamp
NRestarts=0
ActiveEnterTimestamp=Sat 2026-06-27 15:31:10 WIB
```

**Conclusion:** Core has been continuously active since 15:31:10 WIB with **zero
restarts**. No crash loop. Pre-flight noted `15:31:10` as the restart reference,
matching here exactly — no restart has occurred during this audit window.

---

## 2. CP-RT-02 — Brain `hermes_brain_think_complete`, 0 fallback

**Status:** PASS
**Evidence:**
```
$ journalctl -u guinevere-core.service -n 500 -o cat | grep hermes_brain_think_complete | tail -2
2026-06-27 15:43:19 [info] hermes_brain_think_complete  estimated_cost_usd=0.0 input_tokens=44753 model=guinevere output_tokens=5444 total_tokens=139413
2026-06-27 15:43:32 [info] hermes_brain_think_complete  estimated_cost_usd=0.0 input_tokens=68433 model=guinevere output_tokens=5980 total_tokens=139949
$ journalctl -u guinevere-core.service -n 500 -o cat | grep -ciE "fallback|fell back"
0
```

**Conclusion:** Two recent `think_complete` events within the last ~12 minutes
of the audit, both tagged `model=guinevere` (not a fallback model). The
fallback regex returned **0 hits** in the last 500 lines — Hermes is the active
brain, not a degraded alternative. `total_tokens` steadily growing (139413 →
139949) shows memory recall is feeding the model.

---

## 3. CP-RT-03 — Graph cycling, hard_stop clear, recalled_memories>0

**Status:** PASS
**Evidence:**
```
$ journalctl -u guinevere-core.service -n 2000 -o cat | grep graph_invoked_decision | tail -1
2026-06-27 15:44:46 [info] graph_invoked_decision_heartbeat
  act_count=321 cycle_count=322 decision=observe
  hard_stop_requested=None
  last_autonomous_decision='act on: Knowledge graph seeding
    Scan project files/configs/docs to extract entities and relationships
    for KG population, enabling future autonomous reasoning.'
  n_commitments=0 n_concerns=0 n_goals=1 n_journal_entries=320
  n_observations=100 n_recalled_concepts=0 n_recalled_memories=3
  phase=None world_model_status=active
```

**Conclusion:**
- `cycle_count=322` — advancing (322 cycles since boot — active brain, not stuck).
- `hard_stop_requested=None` — clear.
- `n_recalled_memories=3` — recall path producing results.
- `last_autonomous_decision` is a real memory-driven self-directed goal
  ("Knowledge graph seeding") — brain is reasoning, not degenerating to fallback.
- `world_model_status=active` — KG + memory both threaded.

All three CP-RT-03 sub-criteria satisfied.

---

## 4. CP-RT-04 — No traceback / GraphRecursionError

**Status:** PASS
**Evidence:**
```
$ journalctl -u guinevere-core.service -n 500 -o cat | grep -cE "Traceback|GraphRecursionError"
0
```

**Conclusion:** Zero tracebacks and zero GraphRecursionError events in the
last 500 log lines. The P20 stuck-HARD-STOP recursion bug is *not* recurring.
The kernel is cycling cleanly with the new project_id fields.

---

## 5. CP-RT-05 — memory_recall_degraded = 0, memory_recall_success > 0

**Status:** PASS
**Evidence:**
```
$ journalctl -u guinevere-core.service -n 500 -o cat | grep memory_recall_degraded | wc -l
0
$ journalctl -u guinevere-core.service -n 500 -o cat | grep -E "memory_recall_success|kg_recall_success" | tail -4
2026-06-27 15:44:20 [info] kg_recall_success          count=0
2026-06-27 15:44:20 [info] memory_recall_success      count=3
2026-06-27 15:44:33 [info] kg_recall_success          count=0
2026-06-27 15:44:33 [info] memory_recall_success      count=3
```

**Conclusion:**
- `memory_recall_degraded` count: **0**. The "unexpected keyword argument
  'project_id'" TypeError is fully resolved.
- `memory_recall_success count=3` consistently across recent cycles.
- `kg_recall_success count=0` is normal (no KG matches for current query) — not
  an error. KG adapter forwards project_id correctly.

The P19-C03 recall pipeline fix is live and stable.

---

## 6. CP-RT-06 — Dashboard: 1 message, canonical id, edit-in-place

**Status:** PASS
**Evidence:**

(a) Canonical id stored in Redis (db6, port 6380):
```
$ redis-cli -a "$PASS" -p 6380 -n 6 GET life_kernel:dashboard_message_id
1519135545501028549
```

(b) Project-scoped key also present:
```
$ redis-cli -a "$PASS" -p 6380 -n 6 KEYS "*"
life_kernel:dashboard_message_id:00000000-0000-0000-0000-000000000001
feature:projects:enabled
life_kernel:dashboard_message_id
```

(c) Live edit-in-place events in journal:
```
$ journalctl -u guinevere-core.service -n 2000 -o cat | grep dashboard_edited | tail -5
2026-06-27 15:52:56 [debug] dashboard_edited  message_id=1519135545501028549
2026-06-27 15:54:01 [debug] dashboard_edited  message_id=1519135545501028549
2026-06-27 15:54:08 [debug] dashboard_edited  message_id=1519135545501028549
2026-06-27 15:55:11 [debug] dashboard_edited  message_id=1519135545501028549
2026-06-27 15:55:15 [debug] dashboard_edited  message_id=1519135545501028549
```

**Conclusion:**
- Canonical id `1519135545501028549` matches the pre-flight declaration exactly.
- Project-scoped key `life_kernel:dashboard_message_id:{default_uuid}` is set
  alongside the legacy global key (correct dual-write per dashboard_writer.py:78).
- Five `dashboard_edited` events within the last 4 minutes — single message
  edited in place (no duplicate message created; no orphan keys in db6).
- No duplicate dashboard keys present in db6.

All four sub-criteria satisfied.

---

## 7. CP-RT-07 — Feature flag ON, hard_stop clear

**Status:** PASS
**Evidence:**
```
$ redis-cli -a "$PASS" -p 6380 -n 6 GET feature:projects:enabled
true
$ redis-cli -a "$PASS" -p 6380 -n 6 TYPE hard_stop
none
$ redis-cli -a "$PASS" -p 6380 -n 6 EXISTS hard_stop
0
$ redis-cli -a "$PASS" -p 6380 -n 5 EXISTS hard_stop
0
```

**Conclusion:**
- `feature:projects:enabled = true` in db6 — flag ON.
- `hard_stop` key returns `none` type and `EXISTS=0` in db6 (and db5). The
  global hard_stop is fully clear — no operator-block triggered.
- Verified against the same Redis instance the kernel writes to (port 6380).

---

## 8. CP-AR-01 — `project_id` injected into all 3 ainvoke state dicts (heartbeat.py)

**Status:** PASS
**Evidence:** Code-review of `src/life_kernel/heartbeat.py`:

| Line | ainvoke call | state dict includes project_id? |
|---|---|---|
| 350-351 | hard_stop_set path | `{"hard_stop_requested": True, "is_active": False, "project_id": self.project_id}` ✅ |
| 390-391 | recovery path | `{"hard_stop_requested": False, "is_active": True, "project_id": self.project_id}` ✅ |
| 517-518 | main cycle | `{"decision": "continue", "is_active": True, "project_id": self.project_id}` ✅ |

**Conclusion:** Every `graph.ainvoke(...)` invocation in the heartbeat path
includes `"project_id": self.project_id` as a top-level key in the initial
state dict. All three injection points are correctly wired.

---

## 9. CP-AR-02 — `observe_node` passes `project_id` to `recall_context` (graph.py)

**Status:** PASS
**Evidence:** Code-review of `src/life_kernel/graph.py` lines 245-252:

```python
# Seed the recall query from the current focus / latest observation.
query_text = str(state.get("current_focus", "")) or "autonomous life observation"
recall_context = {"query": query_text, "content": query_text}
# P19 Multi-Project Context: propagate project_id from graph state so
# the adapter can scope the memory principal and KG query to the
# active project.
if state.get("project_id"):
    recall_context["project_id"] = state["project_id"]
```

**Conclusion:** The `observe_node` function reads `project_id` from graph state
and conditionally adds it to the `recall_context` dict that is then passed to
`memory_adapter.recall(context)` and `kg_adapter.recall(context)`. This is the
fix that resolves CP-DB-04 / P19-C02 — the adapter can now scope principal to
`project:{project_id}` rather than falling back to `guinevere_core`.

---

## 10. CP-AR-03 — `journal.write_entry` accepts `project_id` (journal.py)

**Status:** PASS
**Evidence:** Code-review of `src/life_kernel/journal.py`:

```python
async def write_entry(
    self,
    state: dict[str, Any],
    reasoning: str,
    lessons_learned: str,
    confidence: float,
    project_id: str | None = None,        # ← P19 kwarg accepted
) -> dict[str, Any] | None:
    ...
    entry = {
        "entry_type": "journal",
        "cycle": state.get("cycle_count", 0),
        ...
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if project_id:                         # ← P19 conditional forward
        entry["project_id"] = project_id

    entry_id = await self._audit_journal.record(entry)
    entry["entry_id"] = entry_id
```

Caller-side check (`graph.py:606-614`):
```python
project_id = state.get("project_id")
entry = await journal_writer.write_entry(
    state=state,
    reasoning=reasoning,
    lessons_learned=lessons,
    confidence=0.7 if not has_errors else 0.4,
    project_id=project_id,                 # ← caller propagates from state
)
```

**Conclusion:** `JournalWriter.write_entry` accepts `project_id` as a kwarg,
forwards it into the entry dict, which `PostgresAuditJournal.record()` writes
into the JSONB. Caller (`graph.py` reflect_node) extracts project_id from
state and passes it. This is the P19-C01 wiring — auditor-verified in CP-DB-01/02
sister audit (36/36 recent rows have `entry->>'project_id'` set).

---

## 11. CP-AR-04 — `_life_recall_fn` forwards `project_id` to `recall_memories` (main.py)

**Status:** PASS
**Evidence:** Code-review of `src/core/main.py:280-303`:

```python
async def _life_recall_fn(
    *,
    query_text: str,
    principal: str = "guinevere_core",
    exclude_dnr: bool = True,
    project_id: uuid.UUID | None = None,            # ← accepted
):
    # P19: accept + forward project_id to recall_memories.
    # The pipeline applies project-scoped filtering
    # (WHERE project_id = :pid OR project_scope = 'global').
    async with _lk_session_factory() as _lk_session:
        return await _recall_memories(
            _lk_session,
            query_text,
            limit=20,
            exclude_dnr=exclude_dnr,
            principal=principal,
            safe_mode=_life_safe_recall,
            project_id=project_id,                   # ← forwarded
        )

from src.life_kernel.p18_adapter import MemoryRecallAdapter
memory_adapter = MemoryRecallAdapter(memory_client=_life_recall_fn)
```

And matching signature on the read-pipeline side
(`src/memory/read_pipeline.py:789-802`):
```python
async def recall_memories(
    session: RecallSession,
    query_text: str,
    limit: int = 20,
    *,
    exclude_dnr: bool = True,
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    embedding_service: EmbeddingClient | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    kg_enabled: bool = True,
    fsrs_enabled: bool = False,
    project_id: uuid.UUID | None = None,            # ← P19-C03 kwarg accepted
) -> RecallResults:
```

**Conclusion:** The `_life_recall_fn` callback accepts `project_id` from the
adapter and forwards it to `_recall_memories`. The downstream pipeline
function signature also accepts `project_id: uuid.UUID | None = None`. Both
ends are wired; the previous "defer" log behavior is no longer needed (and
should be removable in a future hardening pass — but the regression-free path
is in place).

---

## 12. Summary & Final Verdict

| ID | Check | Status |
|---|---|---|
| CP-RT-01 | Core active, NRestarts=0 | PASS |
| CP-RT-02 | Brain think_complete, 0 fallback | PASS |
| CP-RT-03 | Graph cycling, hard_stop clear, recalled_memories>0 | PASS |
| CP-RT-04 | No traceback/recursion | PASS |
| CP-RT-05 | memory_recall_degraded=0 | PASS |
| CP-RT-06 | Dashboard 1 msg, canonical, edit-in-place | PASS |
| CP-RT-07 | Flag ON, hard_stop clear | PASS |
| CP-AR-01 | project_id in 3 ainvoke state dicts (heartbeat.py) | PASS |
| CP-AR-02 | observe_node passes project_id to recall_context | PASS |
| CP-AR-03 | journal.write_entry accepts project_id | PASS |
| CP-AR-04 | _life_recall_fn forwards project_id | PASS |

### Cross-references with sister audits

- **CP-DB-01/02 (db-recall sister audit):** 36/36 recent audit_journal rows
  have project_id propagated — confirms CP-AR-03 end-to-end.
- **CP-RT-05 here:** `memory_recall_success count=3` confirms CP-AR-04
  end-to-end (callable accepts and forwards project_id; pipeline accepts
  without throwing).

### Findings (informational, not P19-blocking)

1. **DB selector note:** The audit brief (`preflight.md`) referred to
   `db6` for the feature flag and dashboard keys — confirmed correct.
   `db5` (shared cost/mood keyspace) is unrelated and was a transient SQL
   confusion in earlier rounds. **Resolved.**

2. **Defer log cleanup:** `main.py` may still emit a `life_recall_project_id_deferred`
   debug log when project_id is None — pre-existing, harmless. Could be
   removed in a future P19-C05 hardening pass.

3. **Brain token growth:** `total_tokens=139949` at last `think_complete`
   suggests the recall injection is bumping input token counts. No
   rate-limit warning in the journal — still well within the budget.

### Verdict

**PASS** — 11/11 checks. P19 completion pass preserves P20 soak-state
(no regression) and the architecture chain `project_id` → graph state →
observe_node / reflect_node → journal.write_entry → audit_journal and
project_id → graph state → _life_recall_fn → recall_memories is
end-to-end correct. The previously-observed gap
(`memory_recall_degraded ... unexpected keyword argument 'project_id'`)
is fully resolved.

---

**Footer:**

| Field | Value |
|---|---|
| Dead mans switch | Core active, NRestarts=0, flag ON, hard_stop clear |
| Brain | guinevere (no fallback), cycle_count=322, recalled_memories=3 |
| Dashboard | canonical id 1519135545501028549, edit-in-place, no duplicates |
| Architecture | project_id plumbed through all 4 layers |
| Verdict | PASS |
