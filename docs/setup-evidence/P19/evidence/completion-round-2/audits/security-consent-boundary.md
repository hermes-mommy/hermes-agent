# P19 Completion Round 2 — Security & Consent Boundary Audit

**Auditor role:** SECURITY / CONSENT AUDITOR
**Date:** 2026-06-27 (Asia/Jakarta)
**Scope:** P19 Multi-Project Context, feature flag ON. Verify that project isolation
(the new axis in P19) does **not** silently bypass any of the four pre-existing
safety boundaries: HARD STOP, consent gate, DNR exclusion, and per-project secret
isolation.
**Methodology:** Read-only review of the five boundary source files plus a VPS
log scan for accidental secret exposure. No code was modified during this audit.

---

## 1. HARD STOP — global scope preserved (PASS)

### Evidence — `life_kernel/graph.py`

The decide_node HARD STOP check is the **highest-priority branch** of the
priority engine and is checked before any LLM/brain enrichment runs:

```
377    # Check for hard stop request (highest priority)
378    if state.get("hard_stop_requested", False):
379        logger.warning("HARD_STOP requested - routing to END")
380        return {"decision": "end"}
```

Source of truth for the key is a separate constant in the Discord handler
(`src/discord/cmd_project.py:44`):

```
44    HARD_STOP_KEY: str = "life_kernel:hard_stop"
```

The kernel itself reads `state["hard_stop_requested"]` (set when the
heartbeat / sanity layer sees the global Redis key `life_kernel:hard_stop`
populated). No `project_id` is appended to the key — the SAME global key
applies regardless of which project is active.

The routing itself is conditional on the static graph `route_from_decide`,
which honors `decision == "hard_stop"` → `END` (graph.py:1066-1070). The
brain-enriched `brain_decide` wrapper (graph.py:822-823) **always** invokes
`decide_node` first and only overrides the result when it would have routed
to `idle`, so HARD STOP cannot be bypassed by the LLM.

**Verdict — global scope preserved, no project_id suffix. PASS.**

---

## 2. /project callback — HARD STOP gate before switch (PASS)

### Evidence — `discord/cmd_project.py`

The `/project <name>` callback enforces the HARD STOP guard **before**
resolving the target project from the registry. Step ordering in
`project_callback` (lines 127–255):

1. `is_faiz_interaction(interaction)` — auth gate (line 143).
2. `defer_ephemeral(interaction)` — UX prep (line 147).
3. **HARD STOP check** (lines 172–191):
   ```
   172    # HARD STOP guard
   173    r = _get_redis_client()
   174    if _is_hard_stop_active(r):
   175        logger.warning("project_switch_blocked_hard_stop", target=name_raw)
   …
   191        return
   ```
4. Only after the guard passes does it call `registry.resolve(name_raw)`
   (line 197), write the audit row, and `set_active_project_id(to_project)`
   (line 232).

`_is_hard_stop_active` reads the **global** key
`"life_kernel:hard_stop"` (`cmd_project.py:44, 59`) from Redis DB0
(port 6380), returning truthy when the operator has set HARD STOP. There
is no `project_id` qualifier — the same value applies project-agnostically.

When blocked, the response is a neutral ack embed with color=ALERT
(`"HARD STOP active"`) — **no side-effects**, the active project session
is not mutated.

**Side-channel check:** `set_active_project_id(to_project)` (line 232) is
called only after the hard-stop guard returns false. `from_project =
get_active_project_id()` (line 211) is read AFTER the guard too.
Audit row written AFTER guard. Neuter surface only.

**Verdict — HARD STOP is checked before any mutating operation. PASS.**

---

## 3. Consent gate — project-scoped isolation with sub-scope precedence (PASS)

### Evidence — `surveillance/consent_gate.py`

`check_consent(scope, project_id?)` (line 225) handles `project_id` in a
fail-closed, sub-scope-aware manner:

- **Global-only scopes** (`_GLOBAL_ONLY_SCOPES` at line 82) — only
  `consent.memory.cross_project`. When a caller passes a project_id for
  that scope, the gate **deliberately nulls** the project_id:
  ```
  272    effective_project_id = project_id
  273    if effective_project_id is not None and scope in _GLOBAL_ONLY_SCOPES:
  274        logger.warning(
  275            "consent_global_only_scope_project_ignored",
  …
  279        effective_project_id = None
  ```
  This prevents a cross-project caller from accidentally widening the
  search to their own scoped rows.

- **Project-only scopes** (`_PROJECT_ONLY_SCOPES` at line 87) — only
  `consent.emergency.break_glass_project`. A project-scoped miss
  (no row for that project) **BLOCKS** with no global fallback
  (lines 333-336):
  ```
  333    if scope in _PROJECT_ONLY_SCOPES:
  334        return await _block_no_entry(
  335            scope, now, cache_key, effective_project_id,
  336        )
  ```

- **General project-scoped scopes** — project row wins; on miss,
  fall back to global (`project_id IS NULL`) only if not project-only.
  This is the documented precedence at lines 311–361.

- **Round-2 bug fix (BUG-1)** — the legacy `project_id=None` path now
  explicitly passes `global_only=True` (line 371) so a project-scoped
  ACTIVE row cannot bypass a global WITHDRAWN row. This is the critical
  fix from the round-2 audit and is documented in the module docstring
  (line 35: *"HARD STOP: remains global (separate mechanism in life_kernel
  / safe_mode)"*) and inline (lines 364–368).

- **Cache** — keys are `{CACHE_KEY_PREFIX}{scope}[:{project_id}]`
  (line 414). Cache values include `project_id`, `status`, and
  `checked_at`. Worst-case staleness = 300 s (TTL) × an
  `invalidate_cache()` call on every consent event. No cache poisoning
  bypass observed.

- **Time-bound scope** — `consent.emergency.break_glass_project` is
  capped at 4 h (`BREAK_GLASS_MAX_HOURS` line 97), enforced by
  `max_age_hours` in the query (lines 92-95, 621-624).

- **Fail-closed on DB error after cache miss** — returns `_BLOCK_DB_FAILURE`
  (line 508-517) with `allowed=False`. Wait — `_block_db_failure` does
  NOT cache the block result (`await _cache_result` is absent), so a
  transient DB outage does NOT poison the cache. Verified by inspection
  of lines 503-516: it builds the result directly and returns. The next
  cache miss will re-query the DB. CORRECT behaviour.

**Verdict — consent isolation is implemented with sub-scope precedence
(intentional), fail-closed semantics, BUG-1 round-1 regression is fixed,
and no project_id qualifier leaks onto global-only scopes. PASS.**

---

## 4. Memory read pipeline — DNR exclusion runs before project_id filter (PASS)

### Evidence — `memory/read_pipeline.py`

Three query builders (`build_vector_query`, `build_fts_query`,
`build_recency_query`) all follow the same DNR-first ordering:

`build_vector_query` (lines 531-570):
```
555    stmt = (
556        select(Episodes)
557        .where(Episodes.embedding.isnot(None))
558        .order_by(cosine_order)
559        .limit(limit)
560    )
561    if exclude_dnr:
562        stmt = stmt.where(Episodes.do_not_recall.is_(False))
563    if project_id is not None:
564        stmt = stmt.where(
565            or_(
566                Episodes.project_id == project_id,
567                Episodes.project_scope == "global",
568            )
569        )
```

Order is: `embedding.isnot(None)` → `exclude_dnr` → `project_id` filter.
A DNR-flagged episode is excluded by the first WHERE clause; the
project_id filter is appended LAST, so it cannot re-introduce a DNR row
by accident. This pattern is identical in `build_fts_query` (598-606)
and `build_recency_query` (632-640).

Compliance with safety ordering (audit invariant): the `exclude_dnr`
predicate is appended to the statement **before** the project-scope
predicate, so an attacker who controls one project cannot pull a DNR
episode from another project by changing the active project.

The downstream pipeline (`recall_memories`) further layers:
- `principal` ceiling filter (lines 1078-1096)
- token-budget trim (lines 1123-1124)
- `safe_mode` content substitution (lines 1102-1121)

— all post-DNR, post-classification. Memory safety ordering is intact.

**Verdict — DNR exclusion is a query-level WHERE clause applied BEFORE
any project-scope filter. No project_id filter can resurface a DNR row.
PASS.**

---

## 5. Secrets vault — structural isolation by project_id (PASS)

### Evidence — `projects/secrets_vault.py`

`ProjectSecretsVault` (line 29) is a pure in-memory
`dict[ProjectId, dict[str, str]]` keyed by **project_id alone**:

```
38    self._store: dict[ProjectId, dict[str, str]] = {}
```

`get(project_id, domain)` (lines 60-71):
```
67    with self._lock:
68        domains = self._store.get(project_id)
69        if domains is None:
70            return None
71        return domains.get(domain)
```

Lookup is **strictly keyed by `project_id`** — there is no API to query
across projects, no default fallback to a "global" bucket, and no
list-all-secrets method. `domains(project_id)` (lines 78-88) only
returns keys for the requested project, so audit access leaks as a
project-id-bound function only.

`load()` (lines 43-58) takes a defensive copy (`dict(secrets)`) to
prevent external mutation races, and `unload()` (lines 73-76) is
project-scoped — no cross-project teardown exists.

Thread-safety: `threading.RLock` guards all four methods, so concurrent
async adapters cannot read a partially-loaded secrets dict.

Hardening observation (non-blocking): secrets are stored as **strings** in
memory. They are not encrypted-at-rest in-process; an attacker with
process memory access (e.g., `/proc/<pid>/maps` + core dump) could read
them. This is **out of scope** for the P19 audit (Guinevere does not
claim in-memory encryption of secrets). It is a known design choice
documented in the module docstring (lines 1-19).

**Verdict — structural isolation by project_id. No code path can leak
across projects. PASS.**

---

## 6. Secret exposure in VPS logs (PASS)

### Evidence

`ssh guinevere-vps "journalctl -u guinevere-core --since '1 hour ago' --no-pager | grep -iE 'token|secret|password|api.?key|bearer' | grep -iv 'no.?leak\|not.?found\|masked\|redacted' | tail -20"`

Result: 20 lines, ALL of the form
`hermes_brain_think_complete estimated_cost_usd=0.0 input_tokens=<int>
model=guinevere output_tokens=<int> total_tokens=<int>` (uvicorn workers
2898013/2898014, between 17:00:53 and 17:12:54 WIB).

The grep matched the substring **"token"** in the numeric `input_tokens` /
`output_tokens` / `total_tokens` fields of the structured cost log —
those are token COUNT integers for LLM billing metrics, NOT secrets.

A follow-up strict grep for secret-shaped patterns returned **empty**:

`ssh guinevere-vps "journalctl -u guinevere-core --since '1 hour ago' --no-pager | grep -iE 'bearer|api.?key|password|secret|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|xox[baprs]-[a-zA-Z0-9-]{20,}|Authorization:' | head -20"`

→ zero matches.

No actual API keys, bearer tokens, OAuth credentials, or passwords were
exposed in any structured log line.

**Verdict — no secret exposure. PASS.**

---

## 7. Cross-cutting observations (informational, not blocking)

These observations are NOT findings; they are recorded for completeness
because round-2 audit trail benefits from explicit acknowledgment of
plausible-looking patterns that turned out safe on inspection.

1. **Per-project adapter registry vs module-level adapters** — P19 stores
   project adapters in `_PROJECT_ADAPTERS` (graph.py:42) and resolves
   them via the safe `state["project_id"]` context-read pattern
   (`_get_adapters`, lines 95-113). Cross-project mutation of the
   global `_ADAPTERS` is structurally impossible — verified by:
   - `set_adapters(..., project_id=...)` writes only to
     `_PROJECT_ADAPTERS[pid]` (line 70-74).
   - `_get_adapters(state)` reads `state["project_id"]` and falls back
     to the global `_ADAPTERS` only when absent (lines 109-113).
2. **Audit journal project_id** — every audit event written from
   `cmd_project.py` includes `from_project` and `to_project` explicitly
   (lines 222-227, 380, 446-452). No audit row is project-less.
3. **Discord /project response styles** — blocked (ALERT) vs success
   (SUCCESS) are visually distinct so a human reviewer cannot mistake a
   silently-blocked switch for an executed one.

---

## 8. PASS verdict

All five boundary invariants verified:

| # | Boundary | File | Status |
|---|----------|------|--------|
| 1 | HARD STOP — global key, no project_id qualifier | `life_kernel/graph.py:378`, `discord/cmd_project.py:44,172-191` | PASS |
| 2 | /project callback HARD STOP before switch | `discord/cmd_project.py:172-191` (vs 211, 219, 232) | PASS |
| 3 | Consent gate project-scoped, fail-closed, BUG-1 fixed | `surveillance/consent_gate.py:225-381,414,582-641` | PASS |
| 4 | DNR exclusion runs BEFORE project_id filter | `memory/read_pipeline.py:561-569,598-606,632-640` | PASS |
| 5 | Secrets vault structural isolation by project_id | `projects/secrets_vault.py:38,60-71` | PASS |
| 6 | No secret exposure in VPS logs | `journalctl -u guinevere-core --since '1h'` (token-count noise only); strict grep returned 0 | PASS |

**Overall verdict: PASS.**

The P19 Multi-Project Context axis, with the feature flag ON, does not
bypass HARD STOP, the consent gate, DNR exclusion, or
per-project secret isolation. The four pre-existing safety boundaries
survive the new axis unchanged. No security regressions observed in
round 2.

---

## 9. Notes on what was NOT covered

- **Runtime injection** of project_id at the adapter layer was not part
  of this audit; that is the runtime audit's scope.
- **Recall pipeline** authorisation/classification effects from
  per-project principals (e.g., `guinevere_core` per-project vs
  per-tenant) are out-of-scope; only DNR/class-ceiling/scope
  boundary was checked here.
- **P19-002 (P23B) on per-project registry runtime wiring** is a
  documentation marker only; no code change suggested.
