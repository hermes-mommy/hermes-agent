# Consent-Safety Audit Report — Phase 3 Planner Gate

**Auditor**: Consent-Safety  
**Date**: 2026-06-04  
**Document Reviewed**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md`  
**Policy Reference**: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`  
**Supporting References**: `src/memory/dnr.py`, `src/memory/read_pipeline.py`, `src/memory/write_pipeline.py`, `src/discord/conversational_handler.py`, `src/hermes/memory_bridge.py`, `src/hermes/safety_plugin.py`, `src/core/services/hard_stop_handler.py`

---

## Verdict: FAIL

**Rationale**: One critical safety gap (consent gate preservation unaddressed — Check #3) and multiple NEEDS REVIEW findings indicate the planner gate is not ready for execution. The plan correctly identifies several safety requirements in prose but omits critical implementation details for bridging Hermes FTS5 results to existing DNR/classification enforcement, entirely neglects consent gate preservation, and does not address surveillance data isolation through the mirror.

---

## Safety Checklist Results

| # | Check | Verdict | Finding |
|---|---|---|---|
| 1 | **DNR Post-Recall Gate** | NEEDS REVIEW | P3-003 §8 explicitly requires calling `verify_recall_results_dnr_free(results)` on ALL session_search results. The scaffold mandates a grep for this function. **However**, the plan does not explain HOW to bridge Hermes FTS5 results (from `~/.hermes/state.db` — a SQLite database with no `do_not_recall` column) to the `verify_recall_results_dnr_free` function (which expects `do_not_recall` boolean in each result dict per `dnr.py` lines 292-314). R-03 identified this gap ("Post-recall DNR gate required for Hermes path") but no implementation detail is specified. The plan needs either: (a) a PostgreSQL DNR lookup per FTS5 result, (b) a pre-loaded DNR ID cache, or (c) a memo-to-dnr.py extension for external result validation. |
| 2 | **Classification Ceiling** | NEEDS REVIEW | P3-003 §8 Safety Gate 2 states "Filter results where classification_level exceeds principal ceiling." Same structural gap as #1: Hermes FTS5 results from `~/.hermes/state.db` do not carry a `classification` field. The architecture diagram shows `Classification Ceiling Filter` as a post-recall step, but the implementation path from Hermes FTS5 raw results (keyword relevance only) to classification-aware filtering is undocumented. The plan must specify whether classification metadata is stored in Hermes state.db, fetched from PostgreSQL post-recall, or enforced via a pre-indexing classification policy. |
| 3 | **Consent Gate Preservation** | FAIL | **Critical finding.** Neither the current `memory_bridge.py` nor the proposed P3-001 plugin refactor includes any consent gate. There is zero mention of `consent_required` check, `consent_revoked` check, or `surveillance_data_policy` compliance in the entire 641-line planner gate. The `memory_bridge.py` delegates directly to `recall_memories()` and `store_episode()` with no consent intermediary. The `read_pipeline.py` and `write_pipeline.py` also lack consent gates. A full-text search for `consent_required`, `consent_revoked`, `surveillance_data_policy`, and `consent.*gate` in `memory_bridge.py` returned zero matches. **This is a safety boundary violation**: per PersonaSafetyPolicy §6.1, consent is "revocable" and "auditable." The plan provides no mechanism to block memory recall or storage when consent is revoked. P3-008 final checklist says "Consent gate unaffected" but there is no consent gate to preserve — the gap exists in the current code and the plan does not remediate it. |
| 4 | **HARD STOP Protocol** | PASS | HARD STOP enforcement is handled by `GuinevereSafetyPlugin` (`src/hermes/safety_plugin.py`) via the `pre_llm_call` hook — G01 exact-trigger detection (6 triggers), G01 semantic-pattern detection (5 regex patterns), and defense-in-depth delegate to `HardStopHandler` (`src/core/services/hard_stop_handler.py`). This plugin operates at the Hermes agent layer independently from the memory plugin. The P3-001 refactor does not touch `safety_plugin.py`. The P3-008 final checklist explicitly verifies "HARD STOP / distress protocol unaffected." The conversational_handler.py gap (G-B7: hard_stop_handler not wired) is acknowledged in §4.2 but the safety_plugin provides a separate, already-active enforcement layer. |
| 5 | **Anti-Hallucination Guard** | PASS | Preserved at three points: (1) P3-001 §8 "Safety Delegation" explicitly states "Anti-hallucination guard injected when prefetch returns empty"; (2) P3-003 §8 Safety Gate 3 states "Inject guard when session_search returns empty results"; (3) P3-008 final checklist includes "ANTI_HALLUCINATION_GUARD injected when memories empty." The current `conversational_handler.py` injects `ANTI_HALLUCINATION_GUARD` (lines ~173-176) when `memories` is empty, and the plan commits to preserving this through the new plugin path. |
| 6 | **Distress Protocol (D0-D4)** | PASS | Distress detection flows through the independent `GuinevereSafetyPlugin.pre_llm_call` (G02: DistressDetector, D2+ escalation triggers safe_mode and Y0 downgrade; D3/D4 blocks the LLM call entirely). The `conversational_handler.py` also runs distress detection and passes `safe_mode_activated` to the bridge. P3-001 maps this through: `prefetch(query, session_id)` → delegates to `read_pipeline.recall_memories()` with `safe_mode` from state. The read_pipeline handles safe-mode classification ceiling downgrade (`_resolve_ceiling`), content substitution (`build_safe_content`), and emotional/surveillance content blocking. P3-003 Safety Gate 4 adds "Safe-Mode Content Substitution" to the FTS5 path. P3-008 checklist includes "Safe-mode content substitution working." |
| 7 | **Persona Safety (Y4/Y5/Y6)** | PASS | Yandere enforcement is independent of the memory migration: `GuinevereSafetyPlugin` enforces Y5 ceiling (G07: `YandereEngine.get_effective_level()` with `YandereSafetyError` if level >5) in `pre_llm_call`, and Y6-adjacent absolute-detection (G08: regex for "forever," "can never leave," "belong to me") in `transform_llm_output`. Post-llm-call disables yandere during safe mode. Mood injection in `conversational_handler.py` (`Mood.CONTENT.value`) remains intact (G-B6 acknowledged but not modified by Phase 3). P3-008 checklist includes "Yandere Y4 baseline/Y5 ceiling preserved." |
| 8 | **Surveillance Data Isolation** | NEEDS REVIEW | P3-004 grants `hermes_memory_bridge` role SELECT-only on `memory` schema. This correctly prevents Hermes from writing to PostgreSQL. **However**, the plan does not address read-side surveillance isolation. Surveillance episodes are stored in `memory.episodes` with `source="surveillance"` (per `write_pipeline.py` conventions and PersonaSafetyPolicy §12). The `hermes_memory_bridge` role with `GRANT SELECT ON ALL TABLES IN SCHEMA memory` can read these surveillance episodes during `recall_memories()` — there is no RLS policy, no source-based filtering, and no mention of row-level surveillance exclusion in P3-003 or P3-004. The PersonaSafetyPolicy §12.2 prohibits using surveillance data for blackmail/humiliation and §12.3 requires minimized quoting of sensitive data. The plan needs either: (a) RLS policy on `memory.episodes` filtering `source='surveillance'` from `hermes_memory_bridge`, (b) a `source` exclusion filter in the read query, or (c) explicit documentation that surveillance-sourced episodes are stored in a separate schema inaccessible to the hermes role. |
| 9 | **Safe-Word Log Rules** | NEEDS REVIEW | The plan does not address safe-word event logging to DNR records. The `dnr.py` module supports `mark_memory_dnr()` with principal-restricted authorization and metadata-only audit events, and `consolidation.py` is documented as "safe-word aware." However, the P3-001 plugin interface意 has no provision for safe-word-triggered DNR marking through the new memory plugin. The `GuinevereSafetyPlugin` detects HARD STOP and switches to safe mode but does not log to DNR records (it logs to structlog). The PersonaSafetyPolicy §7.2(8) requires "Log a minimal non-punitive safety event" and §16.2 requires safe-word logs to be "non-punitive, restricted, encrypted" — not stored with punishment tags. The plan must specify: (a) whether the new memory plugin receives safe-word events to trigger `mark_memory_dnr`, (b) which component owns the safe-word→DNR logging path, or (c) confirmation that this remains in a separate code path untouched by the migration. |
| 10 | **Forbidden Patterns (F-01 through F-15)** | PASS | All 15 forbidden patterns from PersonaSafetyPolicy §11 are enforced by the independent `GuinevereSafetyPlugin` (`src/hermes/safety_plugin.py`, lines 97-194 — `_COMPILED_FORBIDDEN` with compiled regex patterns for F-01 through F-15). Enforcement occurs in `transform_llm_output` (G05): CRITICAL severity patterns → block (return None), HIGH severity patterns → rewrite (substitute `[REWRITTEN]`). This plugin is not part of the Phase 3 migration scope. The plan does not explicitly enumerate F-01 through F-15 in the P3-008 checklist, but the enforcement layer is already active and untouched. |

---

## Forbidden Pattern Cross-Reference

| Pattern | Description | Plan Guard | Status |
|---|---|---|---|
| F-01 | Ignoring or invalidating safe word | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-02 | Punishing genuine distress | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-03 | Using surveillance data for blackmail/shame | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-04 | Isolation pressure from friends/AI/tools | `safety_plugin.py` G05 — HIGH/REWRITE via regex | Guarded (untouched by P3) |
| F-05 | Hidden manipulation/deceptive option framing | `safety_plugin.py` G05 — HIGH/REWRITE via regex | Guarded (untouched by P3) |
| F-06 | Dependency-building threats | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-07 | Love withdrawal during distress | `safety_plugin.py` G05 — HIGH/REWRITE via regex | Guarded (untouched by P3) |
| F-08 | Public/client disclosure of intimate/surveillance data | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-09 | Prompt/memory instruction to bypass policy | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-10 | Irreversible action under persona pressure | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-11 | Over-logging safe word or intimate distress | `safety_plugin.py` G05 — HIGH/REWRITE via regex | Guarded (untouched by P3) |
| F-12 | Escalating yandere intensity above allowed mood | `safety_plugin.py` G05 — HIGH/REWRITE via regex + G07 YandereEngine ceiling | Guarded (untouched by P3) |
| F-13 | Treating surveillance disable as violation during safe mode | `safety_plugin.py` G05 — HIGH/REWRITE via regex | Guarded (untouched by P3) |
| F-14 | Crisis response with dominance/ownership framing | `safety_plugin.py` G05 — CRITICAL/BLOCK via regex | Guarded (untouched by P3) |
| F-15 | Autonomous persona drift beyond safety rubric | `safety_plugin.py` G05 — HIGH/REWRITE via regex + G03 DriftDetector post-llm-call | Guarded (untouched by P3) |

---

## Critical Safety Gaps Found

### Gap 1: Consent Gate Completely Unaddressed (CRITICAL)

- **Observation**: Neither the current `memory_bridge.py` nor the proposed P3-001 `GuinevereMemoryProvider` implements any consent gate. The planner gate's 641 lines contain zero mentions of consent verification, consent revocation, or surveillance data policy compliance in memory operations.
- **Risk Level**: CRITICAL — Consent Revocation Policy cannot block memory recall or storage through Hermes. If Faiz revokes consent for surveillance or memory, the bridge continues to recall and store without any enforcement.
- **Evidence**: `grep` for `consent_required`, `consent_revoked`, `surveillance_data_policy`, and `consent.*gate` across `src/hermes/memory_bridge.py` returned zero matches. The planner gate §4.2 (Known Gaps) lists G-B1 through G-B10 but does not include consent gate as a gap, falsely implying it exists. P3-008 §8 checklist item "Consent gate unaffected" is inaccurate — there is no consent gate to be unaffected.
- **Recommended Fix**: Add a consent-gate check in the new plugin's `prefetch()` and `sync_turn()` methods that queries the Consent & Revocation Policy state before delegating to read/write pipelines. At minimum, document this as a deferred gap (similar to G-B1 through G-B10) with an explicit severity classification and ADR backlog reference. The P3-008 checklist item should be changed from "Consent gate unaffected" to "Consent gate deferred — ADR backlog tracked."

### Gap 2: Hermes FTS5-to-DNR Bridge Unspecified (HIGH)

- **Observation**: The plan mandates `verify_recall_results_dnr_free(results)` on Hermes FTS5 session_search results (P3-003 §8), but does not specify how to populate `do_not_recall` in result dicts from a SQLite database (`~/.hermes/state.db`) that has no DNR column.
- **Risk Level**: HIGH — If the DNR gate is implemented with the current `verify_recall_results_dnr_free` function (which checks `do_not_recall` boolean fields in dicts), and Hermes FTS5 results lack this field, the gate would silently pass (never find `do_not_recall=True`), making DNR enforcement a no-op for the Hermes recall path.
- **Evidence**: `dnr.py` lines 292-314: `verify_recall_results_dnr_free` checks `entry.get("do_not_recall")` and raises `DNRViolationError` only if the value is `True` or `"True"/"true"`. If the field is absent (which it will be for Hermes FTS5 results), the check passes. R-03 research report flagged this ("Post-recall DNR gate required for Hermes path") but the plan doesn't resolve the implementation detail.
- **Recommended Fix**: One of: (a) Extend `verify_recall_results_dnr_free` to accept an optional `dnr_id_set: set[str]` for cross-referencing against a pre-fetched DNR ID cache from PostgreSQL; (b) Require the plugin to enrich each Hermes FTS5 result with a `do_not_recall` boolean by querying PostgreSQL for each result ID; (c) Add a standalone `check_ids_dnr_free(ids: list[str]) → bool` function to `dnr.py` and call it before the dict-level check.

### Gap 3: Hermes FTS5-to-Classification Bridge Unspecified (HIGH)

- **Observation**: Same architectural gap as Gap 2: P3-003 requires classification ceiling filtering on Hermes FTS5 results, but Hermes state.db has no `classification` column. The plan doesn't specify how classification metadata reaches the filter.
- **Risk Level**: HIGH — Without classification metadata on FTS5 results, the ceiling filter cannot function. This could allow Restricted/Confidential/Critical content to reach the LLM context through Hermes session_search, bypassing the read_pipeline's classification enforcement.
- **Evidence**: `read_pipeline.py` lines 86-100: `_CLASSIFICATION_CEILING` maps principals to maximum readable levels. `recall_memories()` filters results via `classification_level(ep.classification) <= ceil_level`. Hermes FTS5 results have no equivalent `ep.classification`. P3-003 architecture diagram shows the filter in the flow but with no data source annotation.
- **Recommended Fix**: Same categories as Gap 2: require the plugin to enrich each FTS5 result with classification metadata from PostgreSQL before running the ceiling filter. Alternatively, ensure all episodes stored via the plugin carry classification metadata that Hermes indexes, or pre-filter at the query level by excluding high-classification conversations from Hermes session_search entirely.

### Gap 4: Surveillance Data Readable Through Mirror (HIGH)

- **Observation**: P3-004 grants `hermes_memory_bridge` SELECT on ALL tables in the `memory` schema. If surveillance-derived episodes are stored in `memory.episodes` (as they are per current `write_pipeline.py` conventions with `source="surveillance"`), the Hermes role CAN read them through `recall_memories()`. The plan has no RLS policy, no source-based filter, and no mention of surveillance data access restrictions for the Hermes read path.
- **Risk Level**: HIGH — PersonaSafetyPolicy §12.2 prohibits using surveillance-derived data for blackmail/humiliation and §12.3 requires minimized quoting of sensitive data. Allowing unrestricted Hermes recall of surveillance episodes creates a data classification boundary violation: surveillance data flows into conversational context without the policy-prescribed gates.
- **Evidence**: P3-004 §8 SQL migration: `GRANT SELECT ON ALL TABLES IN SCHEMA memory TO hermes_memory_bridge;` — no `WHERE` clause, no RLS, no source exclusion. The `hermes_memory_bridge` role has blanket SELECT on memory schema.
- **Recommended Fix**: One of: (a) Add a PostgreSQL RLS policy: `CREATE POLICY exclude_surveillance ON memory.episodes FOR SELECT TO hermes_memory_bridge USING (source != 'surveillance');` and `ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;`; (b) Add a `source_exclusion` parameter to `recall_memories()` defaulting to `["surveillance"]` for the Hermes principal; (c) Store surveillance episodes in a separate `surveillance` schema inaccessible to `hermes_memory_bridge`.

### Gap 5: Safe-Word-to-DNR Logging Path Unspecified (MEDIUM)

- **Observation**: The plan does not address how safe-word events are logged to DNR records through the new memory plugin. The `dnr.py` module supports `mark_memory_dnr()` but the P3-001 plugin interface has no safe-word event handling hooks.
- **Risk Level**: MEDIUM — PersonaSafetyPolicy §7.2(8) requires minimal non-punitive safety event logging for safe-word triggers. If the new plugin path severs the existing safe-word→DNR logging chain (which exists in consolidation.py), safe-word events may go unlogged or be logged incorrectly.
- **Evidence**: `dnr.py` supports `mark_memory_dnr()` for marking episodes. `consolidation.py` is documented as "safe-word aware." The `GuinevereSafetyPlugin` logs to structlog on HARD STOP but does not trigger DNR marking. The P3-001 plugin has no `on_safe_word` or `on_hard_stop` hook.
- **Recommended Fix**: Document that safe-word→DNR logging remains in a separate code path (consolidation.py, not the memory plugin). If the migration touches this path, add explicit verification in P3-008. Alternatively, add an `on_safe_word(episode_ids)` hook to the plugin interface.

---

## Summary

The Phase 3 Memory Bridge Migration planner gate demonstrates strong intent for safety preservation through explicit prose commitments (DNR gates, anti-hallucination guard, classification ceiling, safe-mode substitution), and correctly identifies that existing safety plugins (`GuinevereSafetyPlugin`, `HardStopHandler`) operate independently and are untouched by the migration. However, the plan has a **critical consent gate omission** — neither the current bridge nor the proposed plugin enforces consent verification for memory recall or storage, and the planner gate never acknowledges this gap. Additionally, three architectural bridging gaps remain unresolved: the mechanism for connecting Hermes FTS5 results (from SQLite state.db) to DNR verification and classification ceiling enforcement (which rely on PostgreSQL-hosted metadata), and the lack of surveillance data read-side isolation through the PostgreSQL mirror's RBAC-only approach. The plan CANNOT proceed to execution until the consent gate gap is addressed (at minimum, acknowledged as a deferred gap with severity classification and ADR backlog tracking) and the FTS5-to-metadata bridging strategy is documented.

---

## Footer

| Field | Value |
|---|---|
| Auditor | Consent-Safety Specialist (read-only audit) |
| Report Path | `docs/setup-evidence/phase-3/audit-safety.md` |
| Policy Verified | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (full text, 631 lines) |
| Code Reviewed | 6 files (dnr.py: 418 lines, read_pipeline.py: 963 lines, write_pipeline.py: 359 lines, conversational_handler.py: 631 lines, memory_bridge.py: 295 lines, safety_plugin.py: 480 lines) |
| Total Lines Reviewed | ~3,146 lines code + 641 lines planner + 631 lines policy = ~4,418 lines |
| Persona Boundary | Preserved — Y4 baseline/Y5 ceiling enforced by independent safety_plugin |
| Consent Boundary | VIOLATED — No consent gate in bridge or plugin, not acknowledged in plan |
| Surveillance Boundary | AT RISK — RBAC-only isolation without source filtering allows Hermes read of surveillance episodes |
| DNR Boundary | AT RISK — FTS5 bridging mechanism unspecified; guard may be no-op on Hermes results |