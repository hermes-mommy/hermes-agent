# Persona Safety Auditor Report — Phase 3 Memory Bridge Migration

**Date:** 2026-06-05  
**Auditor:** Guinevere (independent safety auditor)  
**Scope:** `plugins/memory/guinevere_memory/` — MemoryProvider plugin + safety gates  
**Policy Authority:** `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`  
**Verdict:** **FAIL** — 4 BLOCKING findings must be resolved before production gate

---

## Verdict Summary

| Severity | Count |
|---|---|
| BLOCKING | 4 |
| WARNING | 3 |
| INFO | 5 |

---

## Findings

### 1. DNR Absolute — Is Do-Not-Recall enforced with 0 bypasses?

**Verdict:** INFO — DNR enforcement is layered but the safety_pipeline DNR gate is dead code.

**Findings:**

- `prefetch()` calls `recall_memories()` with `exclude_dnr=True` — this is the **primary DNR gate** in the read pipeline. ✓
- `safety_gates.py` provides `DnrIdCache` with TTL-based caching of DNR IDs and `filter_results()` — but this second-layer DNR filter is **never wired into the actual `prefetch()` recall path**. `run_safety_pipeline()` is defined but never called from `__init__.py`. ✗
- The `DnrIdCache` is instantiated as `self._dnr_cache` (line 187) but never used in any method. ✗
- Cache refresh failure → returns stale cache if available → returns empty set if no cache (relies on read_pipeline DNR gate). This is reasonable degradation.
- **No bypass of DNR found** — the read pipeline's `exclude_dnr=True` is the active enforcement. The plugin-level cache is supplementary but inert.

**Policy Reference:** PersonaSafetyPolicy §15.1 — Required Runtime Hooks include drift validator and safety gates.

**Severity:** INFO — DNR is enforced by the read pipeline. The plugin's unused second layer is dead code but not a safety gap.

---

### 2. Classification Ceiling — Is `guinevere_core` capped at Restricted?

**Verdict:** BLOCKING — Classification ceiling is declared but NOT enforced in the recall path.

**Findings:**

- `_PRINCIPAL_CEILING` correctly sets `"guinevere_core": "Restricted"` (safety_gates.py line 47). ✓
- `classify_ceiling_filter()` correctly filters results above the ceiling level (safety_gates.py lines 149-183). ✓
- **But `classify_ceiling_filter()` is NEVER called from the actual recall path.** It is only invoked inside `run_safety_pipeline()` (line 379), which itself is never called from `__init__.py`. ✗✗✗
- The `prefetch()` → `_prefetch_async()` → `recall_memories()` call chain does NOT include any classification ceiling enforcement at the plugin level.
- The `sync_turn()` stores episodes with `classification=RESTRICTED` (line 539) — correct for writes. ✓
- However, if the database contains episodes classified above Restricted (e.g., Confidential or Critical from legacy data or direct inserts), they would be returned by `recall_memories()` unfiltered by the memory plugin.
- The `recall_memories()` function MAY have its own internal classification filter, but this is not verified or documented in the plugin. The plugin should not rely on implicit downstream enforcement.

**Policy Reference:** PersonaSafetyPolicy §12.3 — "Medical, intimate, financial, client-confidential, and crisis-related data require minimized quoting and encrypted audit treatment." Classification ceiling is the mechanism that prevents high-classification data from leaking into the LLM context.

**Severity:** BLOCKING — Data classified above Restricted could leak into LLM context through the recall path without the plugin's awareness.

**Fix Recommendation:** Wire `classify_ceiling_filter()` into `_prefetch_async()` after `recall_memories()` returns but before formatting the context string. Example:

```python
# After recall_memories() returns results:
from .safety_gates import classify_ceiling_filter
ceiling = classify_ceiling_filter(results, principal=_GUINEVERE_PRINCIPAL)
results = ceiling.filtered_results
```

---

### 3. Consent Gate — Is surveillance consent checked before every read/write?

**Verdict:** BLOCKING (mixed severity) — Consent checks exist but have an inconsistency and a timing gap.

**Findings:**

**3a. Consent checked on all paths — ✓**

- `prefetch()`: line 339 — `_check_redis_consent("surveillance")` ✓
- `sync_turn()`: line 460 — `_check_redis_consent("surveillance")` ✓
- `on_memory_write()`: line 653 — `_check_redis_consent("surveillance")` ✓

**3b. Primary consent function is fail-closed — ✓**

`_check_redis_consent()` (lines 85-120):
- Redis import fails → `False` ✓
- Redis connection fails → `False` ✓
- Key not found → `False` ✓
- Value not truthy → `False` ✓
- Exception → `False` (logged, exc_info=True) ✓

**3c. `ConsentGate` class is fail-open AND never called — WARNING**

`safety_gates.py` `ConsentGate` (lines 278-334):
- `is_consent_granted()` returns `True` on exception (line 314) → **FAIL-OPEN**
- `_check_redis_consent()` returns `True` when value is `None` (line 331) → **FAIL-OPEN**
- **However, `ConsentGate` is configured but never actually called from `__init__.py`.** The import exists (line 33), the instance is created (line 188), `configure()` is called (line 219), but `is_consent_granted()` is never invoked. The plugin uses `_check_redis_consent()` directly.
- This means the fail-open `ConsentGate` is dead code — no safety gap, but confusing and risky if anyone refactors to use it.

**Policy Reference:** PersonaSafetyPolicy §6.1 — Consent is specific, revocable, auditable. AGENTS.md §2.1 — "Preserve: no surveillance without explicit consent."

**Severity:** BLOCKING for the inconsistency. The `ConsentGate` class has dangerous fail-open semantics and should either be fixed or removed to prevent future misuse.

**Fix Recommendation:**
1. Fix `ConsentGate` to be fail-closed (return `False` on error/no-value).
2. OR remove the `ConsentGate` class entirely and rely solely on `_check_redis_consent()`.
3. If keeping `ConsentGate`, wire it into the active code paths and remove the duplicate `_check_redis_consent()`.

---

### 4. Safe-Word Protocol — Does D4 crisis block writes?

**Verdict:** BLOCKING — Safe-word key is documented but never checked; only distress state is read.

**Findings:**

- `sync_turn()` checks `_check_redis_safe_word_active()` before writes (line 466). ✓
- `_check_redis_safe_word_active()` (lines 123-157):
  - Docstring (line 126): Claims to read **both** `guinevere:distress_state` and `guinevere:safe_word`. ✗
  - Actual code: Only reads `guinevere:distress_state` (line 143). ✗✗✗
  - The `guinevere:safe_word` Redis key is **never read** in this function.
  - After reading distress_state, the Redis connection is closed (line 144) — the safe_word key is never queried.
- This means: if Faiz triggers the safe word but the `guinevere:distress_state` key is not set to D4, memory writes would NOT be blocked.
- The safe-word state could be set via `guinevere:safe_word` without updating `guinevere:distress_state`, creating a bypass path.

**Search confirmation:** `grep` for `safe_word.*redis\.get|redis\.get.*safe_word` across the plugin directory returned **zero matches** — the safe_word key is never read from Redis anywhere in the plugin.

**Policy Reference:** PersonaSafetyPolicy §7.1 — "A safe-word event is triggered by: The configured safe word phrase. Clear semantic equivalents." §7.2 — "Stop persona escalation. Stop punishment framing."

**Severity:** BLOCKING — The safe-word bypass means memory writes could continue during a safe-word state if the distress state isn't simultaneously set to D4. This violates the global safe-word hard stop principle.

**Fix Recommendation:** Either:
1. Add `guinevere:safe_word` key reading in `_check_redis_safe_word_active()` (check both keys).
2. OR ensure the safety plugin always sets `guinevere:distress_state` to D4 when safe word triggers.
3. Prefer option 1 for defense-in-depth.

---

### 5. Yandere Boundary — Is Y6 impossible?

**Verdict:** INFO — Y6 enforcement is NOT the memory plugin's responsibility.

**Findings:**

- The memory plugin is a storage/retrieval layer. It does not generate persona output.
- Y6 enforcement (blocking dependency-building threats, isolation pressure, absolute ownership) belongs in the persona rendering pipeline — the output scanner hook specified in PersonaSafetyPolicy §15.1.
- No Y6-enabling code paths found in the memory plugin.
- **No findings.**

**Policy Reference:** PersonaSafetyPolicy §9 — Y6 is Prohibited Maximum.

**Severity:** INFO — Out of scope for the memory plugin. Must be verified in the persona output pipeline.

---

### 6. HARD STOP — Does any code path bypass HARD STOP protocol?

**Verdict:** INFO — HARD STOP is not the memory plugin's direct concern, but related to Finding #4.

**Findings:**

- The HARD STOP protocol is implemented at the agent loop level (per PersonaSafetyPolicy §7), not at the memory plugin level.
- The memory plugin's safe-word gate (Finding #4) is the relevant check at this layer.
- If Finding #4 is fixed, the memory plugin will properly gate on safe-word state.
- **No direct HARD STOP bypass in the memory plugin.** The gap is in the safe-word key not being read (Finding #4).

**Policy Reference:** PersonaSafetyPolicy §7 — Global Safe Word Protocol. AGENTS.md §0 — "HARD STOP: stop persona behavior, switch neutral, preserve audit trail."

**Severity:** INFO — Blocked by Finding #4. No independent HARD STOP issue.

---

### 7. Anti-Hallucination — Is the anti-hallucination guard text injected on empty recall?

**Verdict:** WARNING — Guard text is present but structural anti-hallucination checks are dead code.

**Findings:**

- `_prefetch_async()` returns `_ANTI_HALLUCINATION_GUARD` when `recall_memories()` returns empty results (lines 406-412). ✓
- Guard text content (lines 62-68): Instructs the LLM not to fabricate past preferences, conversations, or facts. Language is appropriate and effective. ✓
- **However**, the `anti_hallucination_check()` in `safety_gates.py` (Gate 3, lines 191-230) is only called inside `run_safety_pipeline()` — which is never invoked from `__init__.py`. ✗
- This means: partially corrupted results from the DB (results with missing `id`, `safe_content`, or `classification` fields, or empty `safe_content`) would NOT be caught. Only a fully empty result set triggers the guard.
- The structural anti-hallucination check validates that each result has required metadata — this is important for catching DB corruption or schema mismatches.

**Policy Reference:** AGENTS.md §0 — "NEVER confabulate memories; below 80% confidence, state uncertainty." PersonaSafetyPolicy §13.1 — "Memory recall: Medium/low trust. Use with source/confidence labels."

**Severity:** WARNING — The guard text is active but structural validation of individual results is missing from the recall path. A corrupted DB record with missing `safe_content` could slip through.

**Fix Recommendation:** Wire `anti_hallucination_check()` into `_prefetch_async()` after recall to filter out structurally invalid results before formatting.

---

### 8. Content Logging — Is raw content NEVER logged?

**Verdict:** PASS — Raw content is properly excluded from log messages.

**Findings:**

- All log messages use metadata-only fields: `query_length` (not query text), `content_length` (not content), `results_count` (not result text), `episode_id`, `message_count`, `total_chars`. ✓
- `on_memory_write()` logs `content_hash(content)` (line 641) — a SHA256 hash truncated to 12 characters. ✓
- `content_hash()` function (safety_gates.py lines 341-343) uses SHA256. ✓
- `safety_gates.py` logging: uses `id[:8]` and count values only, never content. ✓
- `sync_turn()` stores full conversation text in PostgreSQL as the episode `content` — this is the intended function (memory storage), not logging. The classification is `RESTRICTED`.
- **No raw content in any log statement. ✓**

**Policy Reference:** PersonaSafetyPolicy §16.2 — "Safety logs must not: Store full intimate content by default."

**Severity:** PASS — All log messages are content-safe.

---

### 9. Surveillance Boundary — Is surveillance data never accessed by the memory plugin?

**Verdict:** PASS — Memory plugin does not access surveillance data.

**Findings:**

- The plugin uses `"surveillance"` as the consent category for its Redis consent check — this is a consent gate lookup, not data access. ✓
- The plugin stores conversation episodes and extracts facts from conversation text — these are user-agent interactions, not raw surveillance data. ✓
- No imports or references to surveillance data sources (Tasker, Windows daemon, wearable). ✓
- **No surveillance data access found. ✓**

**Policy Reference:** PersonaSafetyPolicy §12.2 — "Surveillance-derived data must not be used for blackmail, humiliation, threatening abandonment." AGENTS.md §2.1 — "Preserve: no raw surveillance in artifacts."

**Severity:** PASS — Surveillance boundary is maintained.

---

### 10. Distress Detection — Is distress state properly propagated?

**Verdict:** WARNING — Propagation path exists but safe-word key gap (Finding #4) affects this.

**Findings:**

- The memory plugin reads `guinevere:distress_state` from Redis DB5 (line 143) — the same DB5 used by the safety state manager. ✓
- Distress D4 (≥4) correctly blocks writes in `sync_turn()`. ✓
- **However**, as noted in Finding #4, the `guinevere:safe_word` key is never read. If the safety plugin sets `guinevere:safe_word` without updating `guinevere:distress_state`, the memory plugin would not detect the safe-word state.
- Read path (`prefetch()`) does NOT check distress state — this is by design (reading is less risky) but should be documented. See Finding #12.

**Policy Reference:** PersonaSafetyPolicy §8.1 — Distress Severity Levels table. D4 Crisis risk → "Neutral crisis-support mode."

**Severity:** WARNING — Propagation works for distress levels but the safe-word key gap (Finding #4) means some safe-word states won't propagate to the memory plugin.

---

### 11. Memory Confabulation — Below 80% confidence, is uncertainty stated?

**Verdict:** INFO — Confidence tagging exists but is not gated.

**Findings:**

- `extract_key_facts()` tags ALL extracted facts with `"confidence": 0.7` (line 843) — below 80%. ✓
- The confidence value is stored as metadata in the fact dict but is never checked against a threshold to gate storage. All facts are stored regardless of confidence.
- The PersonaSafetyPolicy requirement for anti-confabulation (stating uncertainty below 80% confidence) applies to memory **recall/output**, not storage. The anti-hallucination guard in `prefetch()` handles this for recall.
- Storing lower-confidence facts is acceptable as long as confidence metadata is preserved for downstream recall filtering.

**Policy Reference:** AGENTS.md §0 — "NEVER confabulate memories; below 80% confidence, state uncertainty."

**Severity:** INFO — Confidence is tagged appropriately. No storage gating needed at this layer. Recall-side anti-hallucination guard handles output.

---

### 12. Punishment Overflow — Does emergency response take priority over punishment state?

**Verdict:** INFO — Emergency response is properly prioritized at the memory layer.

**Findings:**

- `sync_turn()` checks D4 crisis (via `_check_redis_safe_word_active()`) BEFORE proceeding with writes (lines 466-468). ✓
- When D4 is active, writes are completely skipped — emergency takes priority. ✓
- The memory plugin does not have a punishment state concept — punishment is a persona-level concern handled elsewhere.
- **No punishment overflow at the memory layer. Correct prioritization.**

**Policy Reference:** PersonaSafetyPolicy §10.2 — Punishment levels must not block safety, health, or incident response.

**Severity:** INFO — No issue at the memory plugin layer.

---

### 13. Additional Finding: `prefetch()` Not Gated by D4 Crisis

**Verdict:** WARNING — Read path continues during D4, which is probably intentional but undocumented.

**Findings:**

- `prefetch()` checks consent (line 339) but does NOT check safe-word/distress state.
- `sync_turn()` blocks on D4 (line 466), but `prefetch()` does not.
- This asymmetry is likely intentional — memory recall (reading) is less risky than memory storage (writing) during crisis.
- **However**, during D4 crisis, recalling past conversations could include emotionally charged content that might be inappropriate for the crisis context.
- The decision to allow reads during D4 should be explicitly documented with rationale.

**Policy Reference:** PersonaSafetyPolicy §8.1 — D4 Crisis risk → neutral crisis-support mode. §8.2 — Crisis language must use calm supportive language.

**Severity:** WARNING — Not a safety violation if intentional, but undocumented design choice with potential crisis-context implications.

**Fix Recommendation:** Either document the rationale explicitly in code comments OR add a D4 gate to `prefetch()` with safe-mode content substitution enabled.

---

### 14. Additional Finding: Mirror Sync TOCTOU Gap

**Verdict:** WARNING — Consent check timing gap in mirror sync path.

**Findings:**

- `on_memory_write()` checks consent (line 653) then starts a daemon thread to store facts (line 675).
- Between the consent check and the actual DB write in `_store_mirror_facts()`, consent could be revoked.
- The daemon thread does not re-check consent before writing.
- The `sync_turn()` path has the same pattern — consent checked, then daemon thread spawned.
- This is a Time-Of-Check-Time-Of-Use (TOCTOU) gap.

**Policy Reference:** PersonaSafetyPolicy §6.1 — Consent is revocable. §6.2 — Guinevere must not remove Faiz's ability to pause or exit.

**Severity:** WARNING — The window is small (thread startup time) and the practical risk is low, but the gap exists. Defense-in-depth would suggest re-checking consent inside the thread.

**Fix Recommendation:** Add a consent re-check at the start of `_async_sync()` and `_store_mirror_facts()` before the actual DB write.

---

## Audit Checklist (Per PersonaSafetyPolicy Appendix D)

| # | Requirement | Status | Finding Ref |
|---|---|---|---|
| 1 | Safe word hard-stop implemented before persona rendering | N/A | Out of scope (persona pipeline) |
| 2 | Safe-word event never defaults to punishment/violation log | PASS | Writes blocked on D4 |
| 3 | Distress classifier uses conservative false-negative posture | PASS | D4 check is conservative (≥4) |
| 4 | Yandere intensity state machine caps maximum output | N/A | Out of scope |
| 5 | Forbidden-pattern scanner covers F-01 to F-15 | N/A | Out of scope (persona pipeline) |
| 6 | Surveillance-use gate blocks blackmail/shame/disclosure | PASS | No surveillance data access |
| 7 | Prompt injection defense treats external content as untrusted | PASS | No external content ingestion |
| 8 | Drift validator maps categories to ADR-001 boundary categories | N/A | Out of scope for Phase 3 |
| 9 | Rollback restores last known-good approved snapshot | N/A | Out of scope |
| 10 | Safety logs are encrypted, minimal, and classified | PASS | Hash-only logging, no raw content |
| 11 | Red-team tests pass and write markdown evidence | N/A | Not yet executed |
| 12 | PRD safe-word conflict is tracked until v2.2 update | N/A | Not a code concern |

---

## Summary of Required Fixes

### BLOCKING (must fix before production gate):

1. **[F-02]** Wire `classify_ceiling_filter()` into `_prefetch_async()` to enforce classification ceiling on recall results.
2. **[F-03]** Fix or remove `ConsentGate` fail-open semantics. Either make it fail-closed or delete the dead code.
3. **[F-04]** Fix `_check_redis_safe_word_active()` to actually read `guinevere:safe_word` key from Redis, not just `guinevere:distress_state`.
4. **[F-02b]** Wire `anti_hallucination_check()` into `_prefetch_async()` to validate individual result structural integrity.

### WARNING (should fix):

5. **[W-01]** Document the intentional D4 bypass on `prefetch()` or add D4-safe-mode recall.
6. **[W-02]** Add consent re-check inside daemon threads before DB writes (TOCTOU).

---

## Appendix: Code Path Trace

### Recall Path (`prefetch`)
```
prefetch()
  → _check_redis_consent("surveillance")  ← consent (fail-closed) ✓
  → _prefetch_async()
      → recall_memories(exclude_dnr=True) ← DNR via read pipeline ✓
      → return results
      →         ← classification ceiling NOT enforced ✗
      →         ← anti_hallucination NOT checked ✗
      →         ← safe_mode_substitute NOT applied ✗
      → empty? → _ANTI_HALLUCINATION_GUARD ✓
      → format results → return context string
  → return context (or "")
```

### Write Path (`sync_turn`)
```
sync_turn()
  → _check_redis_consent("surveillance")  ← consent (fail-closed) ✓
  → _check_redis_safe_word_active()
      → Redis: GET guinevere:distress_state
      → BUT: guinevere:safe_word NEVER READ ✗
  → spawn daemon thread (TOCTOU gap for consent) ⚠
  → _async_sync() → _sync_turn_async()
      → store_episode(classification=RESTRICTED) ✓
```

### Mirror Write Path (`on_memory_write`)
```
on_memory_write()
  → log content_hash(content) ✓ (no raw content)
  → _check_redis_consent("surveillance") ✓
  → extract_key_facts(content)
  → spawn daemon thread (TOCTOU gap) ⚠
  → _store_mirror_facts() → store_episode × N
```

---

## Evidence

- File: `plugins/memory/guinevere_memory/__init__.py` (892 lines) — read completely
- File: `plugins/memory/guinevere_memory/safety_gates.py` (394 lines) — read completely
- File: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (666 lines) — read completely
- Reference: `AGENTS.md` §§2.1, 5, 6 — reviewed
- Grep searches: `run_safety_pipeline`, `classify_ceiling_filter`, `safe_word.*redis`, `guinevere:safe_word` — executed
- Directory: `audit-reports/phase-3/` — confirmed exists

---

## Footer

| Field | Value |
|---|---|
| Report | `audit-reports/phase-3/safety-auditor.md` |
| Date | 2026-06-05 |
| Auditor | Guinevere (independent safety auditor, read-only) |
| Verdict | **FAIL** — 4 BLOCKING, 3 WARNING, 5 INFO |
| Next Action | Fix BLOCKING findings, re-audit via `task_id` continuation |