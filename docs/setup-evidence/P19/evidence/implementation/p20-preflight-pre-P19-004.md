# P20 Fresh Runtime Incident Preflight — Pre-P19-004 (LOCKED-file edit gate)

**Date:** 2026-06-25 (pre-P19-004)
**Operator instruction:** Before touching P20/LOCKED runtime files, run a fresh runtime incident preflight. If clean, continue. If incident exists, stop and report.
**Trigger:** P19-004 modifies `src/life_kernel/p16_adapter.py` + `p18_adapter.py` (LOCKED P20 files). Per `p20-waiver-gate-sync.md` §6, the operator lifted the implementation hold but retained the fresh-preflight requirement before any LOCKED-file edit.

## 1. Verdict

**CLEAN — proceed with P19-004 (strictly additive `project_id=None` defaults).**

## 2. Signals (read-only, no production touch)

| Signal | Value | Status |
|---|---|---|
| `guinevere-core` service | `active (running)`, SubState=running, Result=success | ✅ |
| NRestarts | 0 (since 08:26:43 WIB privacy-fix restart `03f84b5`) | ✅ stable |
| ActiveEnter | 2026-06-25 08:26:43 WIB | ✅ |
| Memory current / peak | ~1.0 GB / ~1.0 GB (vs 4 GB cap) | ✅ no OOM |
| Journal errors (last 5 min) | 0 ("-- No entries --" at err priority) | ✅ |
| `hard_stop_requested` (kernel state field, journal) | **False** | ✅ HARD STOP CLEAR |
| `is_active` / `world_model_status` | True / active | ✅ |
| `decision` | `observe` (healthy loop, not stuck at END) | ✅ |
| `cycle_count` | 197986 and climbing (steady 1s heartbeat) | ✅ not frozen, no END-spin |
| `heartbeat_completed` | interval_type=1s, latency_ms≈12 | ✅ |
| `think_complete` (last 5 min) | 7 | ✅ brain thinking |
| `fallback_used` (last 5 min) | 0 | ✅ no fallback storm |
| `n_recalled_memories` | 3 (real P16/P18 recall active — the adapters P19-004 touches are functioning) | ✅ |
| GraphRecursionError / traceback / OOM / killed (30 min) | 0 | ✅ |
| Other services | `hermes-gateway` active (undisturbed) | ✅ |

## 3. Redis hard_stop key note

Direct Redis `GET life_kernel:hard_stop` could not be queried because the `guinevere` unix user lacks the Redis ACL password and the password is SOPS/ACL-managed (not extractable without the core's ACL credential). This is **not** a gap: the kernel's own journal field `hard_stop_requested=False` is the authoritative in-process signal (it is set from the same Redis key by the heartbeat recovery logic per the P20 stuck-HARD-STOP fix), and it reads False. The dashboard embed (`#guinevere-status`) independently shows "HARD STOP ✅ CLEAR" per the P20 waiver evidence. Three independent signals agree: HARD STOP is clear.

## 4. Baseline snapshot (for post-P19-004 comparison)

Captured so that if P20 degrades after P19-004's additive edits, there is a clean "before" to diff against:
- cycle_count ≈ 197986, act_count ≈ 834, n_journal_entries ≈ 783, n_observations=100, n_recalled_memories=3
- memory ~1.0 GB, 0 restarts, 0 errors, 0 fallbacks, hard_stop_requested=False

## 5. Scope of LOCKED-file edits authorized by this preflight

P19-004 may edit (strictly additive, `project_id: Optional[UUID] = None` defaults — flag OFF = legacy behavior):
- `src/hermes/_memory_bridge.py` — add `project_id` to `recall_for_context` + `store_conversation`
- `src/life_kernel/p16_adapter.py` — add `project_id`
- `src/life_kernel/p18_adapter.py` — add `project_id`, remove hardcoded `principal="guinevere_core"` in favor of project-aware principal
- `src/knowledge_graph/query/{context,engine,rrf_fusion,ppr}.py` — add `project_id` filter
- NEW: `src/projects/memory_store.py` (`ProjectScopedMemoryStore` wrapper)
- NEW tests: `tests/projects/test_memory_isolation.py`, `test_kg_isolation.py`

**Forbidden (preserved invariants):**
- HARD STOP scoped per project → FAIL
- `thread_id` hardcoded unconditionally → FAIL (belongs to P19-005, not 004)
- P20 semantics altered when `feature:projects:enabled` is OFF → FAIL
- `_ADAPTERS` global mutated unsafely across projects → FAIL
- recall query without `project_id`/`project_scope` filter → FAIL
- KG entity resolution without `project_id` filter (DATA-04) → FAIL

## 6. Footer

| Field | Value |
|---|---|
| Preflight result | CLEAN |
| Decision | Proceed with P19-004 (additive only) |
| Next preflight required | Before P19-005 (heartbeat/graph — deeper LOCKED edits) and P19-012 (deploy) |
| Author | Guinevere (parent) |
