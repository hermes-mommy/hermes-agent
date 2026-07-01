# P3 Audit D05: DNR / Safe-Mode / HARD STOP / Security

## Audit Metadata

- **Date**: 2026-06-25
- **Agent**: Claude Code (subagent, read-only)
- **Read-only affirmation**: YES. No files modified. No DB write. No secrets printed.
- **Scope**: DNR (do-not-recall) enforcement, safe-mode content substitution, HARD STOP protocol, classification-based access control, consolidation bypass risk, secrets/logging hygiene.

---

## Findings

### [CRITICAL] FINDING D05-001: `verify_recall_results_dnr_free()` is NEVER called at runtime

**Severity**: CRITICAL

**Description**: The function `verify_recall_results_dnr_free()` in `src/memory/dnr.py` (line 385) is designed as a post-recall, pre-injection defense-in-depth gate that must be called after `recall_memories()` and before memory content is injected into an LLM prompt. Every P3 audit report, ADR, and safety document claims this gate is wired. It is not.

- The function is **exported** from `src/memory/__init__.py` (line 81) and `src/memory/dnr.py` (line 38).
- It is **tested** in `tests/memory/test_dnr.py` (5 tests in `TestVerifyRecallResultsDNRFree` lines 496-530).
- But it is **ZERO times imported or called** anywhere in `src/` runtime code. The only `src/` references are the definitions and `__init__.py` re-exports.
- The planned `memory_plugin.py` that was supposed to call it (per ADR-035, safety-compliance-map, and multiple audit documents) **does not exist**.

**Evidence**:
- `grep -r "verify_recall_results_dnr_free" src/` returns only lines in `dnr.py` and `__init__.py` (no runtime call sites).
- ADR-035 line 618: "Port DNR enforcement (pre-injection gate) — `plugins/memory_plugin.py` (new) — `verify_recall_results_dnr_free()` pre-injection" — this file does not exist.
- `src/hermes/safety_plugin.py` does not call it. `src/core/services/prompt_loader.py` does not call it. `src/hermes/_memory_bridge.py` does not call it.

**Impact**: The primary DNR defense (SQL-level `WHERE do_not_recall IS FALSE`) is operational and strong, but the secondary defense-in-depth layer is entirely missing. If a code change ever removes the SQL WHERE clause (e.g. typo, refactor, `exclude_dnr=False` mode), there is no pre-injection barrier and DNR-marked content enters the LLM context silently. No error is raised, no alert is triggered.

---

### [MEDIUM] FINDING D05-002: No DNR remediation path exists for bypassed content

**Severity**: MEDIUM

**Description**: If DNR-marked content ever reaches the LLM context (due to a bug, missing WHERE clause, or cold-start SQLite path), there is no automated remediation. The `verify_recall_results_dnr_free()` function would catch it in the dict-level check — but that function is not wired (see D05-001). Without the pre-injection gate, DNR content passes through silently.

**Evidence**:
- All callers pass `exclude_dnr=True` — the SQL-level filter is the ONLY active defense.
- `recall_memories()` at `read_pipeline.py:794` defaults `exclude_dnr=True` which flows to all three query builders.
- The Hermes memory bridge (`_memory_bridge.py:157`) and prompt loader (`prompt_loader.py:261`) and Hermes plugins (`memory_search.py:112`) and life kernel adapter (`p18_adapter.py:95`) all pass `exclude_dnr=True`.

---

### [HIGH] FINDING D05-003: `verify_recall_results_dnr_free` cannot guard Hermes SQLite/external results

**Severity**: HIGH

**Description**: The function `verify_recall_results_dnr_free()` checks `entry.get("do_not_recall")` on result dicts. If Hermes returns results from its own SQLite FTS5 cache (`~/.hermes/state.db`), those result dicts will NOT contain a `do_not_recall` field. The function silently passes (missing key → `.get()` returns `None` → not `True` → no error). This was flagged in prior audits (audit-safety.md lines 67-69 from Phase 3 setup evidence) and remains unresolved. A `memory_plugin.py` was planned to bridge PostgreSQL DNR IDs into the Hermes result context, but it was never created.

**Evidence**:
- `dnr.py:406`: `dnr_flag = entry.get("do_not_recall")` — this is a dict `.get()` which silently returns `None` for missing keys.
- Prior audit flag (docs/setup-evidence/phase-3/audit-safety.md): lines 63-70 explicitly discuss the "silent no-op" risk for Hermes FTS5 results.

---

### [LOW] FINDING D05-004: Consolidation correctly excludes DNR episodes

**Severity**: LOW (finding is positive — confirming correct behavior)

**Description**: The consolidation pipeline (`consolidation.py`) correctly excludes DNR-marked episodes at two layers:
1. SQL-level WHERE clause at line 323: `stmt = select(Episodes).where(Episodes.do_not_recall.is_(False))`
2. Defensive per-row check at line 340-348: `if getattr(ep, "do_not_recall", False): skipped_dnr += 1; continue`

There is NO bypass path where a DNR episode can be consolidated into a `semantic_fact`. The `is_safe_word_record()` function (line 505-556) additionally blocks episodes tagged/typed with `hard_stop`, `crisis`, `safe_word`, `formal_hold`, or `distress`, preventing crisis content from entering the semantic fact layer.

Tests confirm: `test_skips_dnr_episodes` (line 579), `test_no_facts_from_dnr_only` (line 593), `test_dnr_episode_classification_not_in_facts` (line 796).

---

### [LOW] FINDING D05-005: HARD STOP / safe mode is multi-layered but inconsistently wired

**Severity**: LOW

**Description**: HARD STOP has three active enforcement layers:
1. `HardStopHandler` (`src/core/services/hard_stop_handler.py`): intercepts user messages before LLM, sets `is_safe` property. Wired via `loop_manager.guardian.set_hard_stop_handler()` at `core/main.py:103-104`. Callbacks trigger `SafeModeController.force_safe_mode()`.
2. `GuinevereSafetyPlugin` (`src/hermes/safety_plugin.py`): Gate G01 in Hermes, checks exact + semantic triggers, delegates to HardStopHandler, wires safe_mode_controller.
3. Life kernel heartbeat (`src/life_kernel/heartbeat.py`): polls Redis key `life_kernel:hard_stop`, stops cognition when active, announces to Discord.

However, the `safe_mode` parameter in memory recall is resolved inconsistently:
- `prompt_loader.py:252-254`: resolves from `hard_stop_handler.is_safe` (authoritative)
- `HermesMemoryBridge.recall_for_context()`: receives `safe_mode` as caller parameter but does NOT interrogate HardStopHandler internally
- Life kernel adapter (`core/main.py:272`): uses `LIFE_KERNEL_SAFE_RECALL` env var, NOT the HardStopHandler state

This means the safe_mode parameter reaching `recall_memories()` depends on which code path invokes it. The brain path (life kernel) does NOT enforce safe-mode redaction unless the env var is explicitly set — this is by design per the SAF-02 fix comment at `core/main.py:259-272`.

---

### [LOW] FINDING D05-006: Classification ceiling and safe-mode substitution are sound

**Severity**: LOW (finding is positive)

**Description**: The classification-based security model in `read_pipeline.py` is well-implemented:
- `_resolve_ceiling()` (line 177): correctly per-principal ceiling resolution with safe-mode downgrade
- `build_safe_content()` (line 419): handles all five classification levels with appropriate placeholders
- `_SAFE_MODE_BLOCKED_CONTENT_TAGS` (line 81-87): blocks emotional/surveillance/persona-escalation content
- `_CLASSIFICATION_CEILING` (line 164-168): `guinevere_core` → CRITICAL, `guinevere_subagent` → CONFIDENTIAL, default → RESTRICTED
- `_SAFE_MODE_CEILING` (line 94-98): `guinevere_core` → INTERNAL (downgraded), default → PUBLIC
- Classification ceiling filter at line 1078-1096: blocks results above the principal's ceiling

The ceiling filter operates on the ORM `episode.classification` field, not on the result dict's `classification` key — it correctly reads from the merged `EpisodeEntry` which holds the raw ORM object.

---

### [LOW] FINDING D05-007: No raw memory content in logs or audit events

**Severity**: LOW (finding is positive — compliant)

**Description**: Audit trail and logging across memory modules consistently avoids raw content:
- DNR audit events at `dnr.py:149-171`: store only `episode_id`, `event_type`, `principal`, `reason_hash`, `reason_length`, `occurred_at`. No raw content or raw reason string.
- DNR logging at `dnr.py:248-255`: logs only `memory_id`, `principal`, truncated `reason_hash`. No raw reason.
- `recall_memories` logging at `read_pipeline.py:1132-1149`: logs `query_hash` (SHA-256 truncated), lengths, counts, flags. No query text, no embeddings, no raw content.
- Pipeline errors log only structured metadata (error type, length, count).
- Embedding service (`embeddings.py`): never logs input text, never logs vector values.
- Tests in `test_dnr.py:538-549` (`TestNoRawContentInLogsAndEvents`) explicitly audit this.

---

### [LOW] FINDING D05-008: Secret scanner and auth matrix operate correctly

**Severity**: LOW (finding is positive)

**Description**: The safety plugin has additional security layers:
- Gate G06: Secret scanner (`secret_scanner.py`) redacts secrets from LLM output. Verified operational in `safety_plugin.py:1070-1095`.
- Gate G09: Auth matrix (`auth_matrix.py`) blocks FORBIDDEN/DESTRUCTIVE_APPROVAL tool operations. Verified operational in `safety_plugin.py:906-982`.
- Gate G05: Forbidden pattern block/rewrite (15 patterns F-01 through F-15). Verified operational in `safety_plugin.py:1035-1068`.

These gates are all registered hooks in the Hermes plugin (`safety_plugin.py:1210-1236`).

---

### [LOW] FINDING D05-009: Decay sweep and active forgetting handle DNR correctly

**Severity**: LOW (finding is positive)

**Description**: The P18 decay sweep (`consolidation.py:928-1079`) queries only non-DNR episodes:
- Line 995: `stmt = select(Episodes).where(Episodes.do_not_recall.is_(False))`
- Active forgetting (`consolidation.py:1023-1058`) operates only within this filtered set, so DNR episodes are never auto-archived.

---

## Status Verdict

**VERIFIED IMPLEMENTED** (with a critical gap)

The core DNR mechanism (SQL-level exclusion, mark/unmark API, authorization, audit) is solid and tested. The consolidation pipeline correctly excludes DNR episodes. Classification-based safe-mode substitution is sound. HARD STOP has three active enforcement layers. No raw content leaks into logs.

However, the **defense-in-depth pre-injection gate** (`verify_recall_results_dnr_free()`) is defined and tested but **never wired into any runtime code path**. The planned `memory_plugin.py` does not exist. This is the single most important safety gap in the DNR implementation — removing the SQL WHERE clause (even accidentally) makes DNR a no-op with zero runtime detection.

---

## Recommendations (NO FIXES — for mama consideration)

1. **Wire `verify_recall_results_dnr_free()` into at least one runtime entry point**, such as `prompt_loader.py` after `recall_memories()` returns, or `HermesMemoryBridge.recall_for_context()`. This provides the secondary defense layer that P3-013 promised.

2. **Consider addressing the Hermes SQLite DNR bridge gap**: if Hermes search results ever flow from the local SQLite database (which lacks a `do_not_recall` column), the dict-level check silently passes. A pre-fetched DNR ID set from PostgreSQL could be cross-referenced. This was flagged in prior Phase 3 audits and remains unresolved.

3. **Unify safe-mode resolution**: the memory-safe recall path is inconsistently determined — prompt_loader uses HardStopHandler, Hermes bridge relies on caller parameter, life kernel uses an env var. Consider a single authoritative source-of-truth for safe mode across all consumers.

4. **Periodic audit of SQL-level DNR exclusion**: since the pre-injection gate is not wired, the SQL WHERE clause is the sole defense. A regression test that queries all three signal paths (`build_vector_query`, `build_fts_query`, `build_recency_query`) for the DNR WHERE clause would catch accidental removal.
