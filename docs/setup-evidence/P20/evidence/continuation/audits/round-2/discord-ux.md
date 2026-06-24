# Discord UX Audit — P20 Living Autonomy Kernel Continuation (Round 2)

**Auditor:** Discord UX specialist (independent)  
**Scope:** Wave-1 fix verification (DUX-01, AUTO-06) + new issue detection in `src/life_kernel/heartbeat.py`, `dashboard.py`, `dashboard_writer.py`  
**Date:** 2026-06-24  
**Commits reviewed:** HEAD~3..HEAD cumulative diff; wave-1 fixes in HEAD (ff1c9fa)  
**Round:** 2 (fix verification + regression hunting)

---

## 1. Verdict

**PASS_WITH_NOTES**

Both wave-1 fixes (DUX-01 lifecycle log truncation, AUTO-06 category logging) are correctly implemented. The dashboard rendering, sanitization, edit-not-spam pattern, and log throttling all remain intact. However, one medium-severity NEW issue was introduced: the DUX-01 fix only applied truncation to the lifecycle log line but missed the self-improvement candidate log line in the same file, creating an incomplete defense against Discord's 2000-char limit. No hard-rejection criteria are triggered.

---

## 2. Executive Summary

This round-2 audit verified that the wave-1 Discord UX fixes (DUX-01 and AUTO-06) are correctly implemented and looked for new issues introduced by those fixes. Key findings:

**Wave-1 fixes VERIFIED:**
- **DUX-01 (medium → FIXED):** Lifecycle log line is now truncated to ≤1900 chars before Discord write at `src/life_kernel/heartbeat.py:523-528`. The fix applies `_DISCORD_LOG_MAX = 1900` with explicit truncation and "..." suffix.
- **AUTO-06 (medium → FIXED):** Heartbeat now logs `candidate.category` instead of the non-existent `candidate_type` at `src/life_kernel/heartbeat.py:620-625`. The comment explicitly calls out AUTO-06 fix, and the code uses `str(getattr(c, "category", "?"))`.

**Other Discord UX aspects remain correct:**
- Dashboard `render_embed` still renders `memory_status`, `current_focus`, `next_planned_action` with `_sanitize()` and `_truncate_field()` applied (`dashboard.py:285-386`).
- Edit-not-spam pattern preserved with checksum-based skip and message recovery (`dashboard_writer.py:126-182`).
- Log throttled to 1 per 5 minutes with dedup (`heartbeat.py:529-537`; throttle constant at line 31).
- Brain/world-model status tracked as "unavailable"/"degraded"/"active" and rendered honestly.

**NEW issue found:**
- **DUX-06 (medium):** Self-improvement candidate log line at `heartbeat.py:635-638` does NOT have the same DUX-01 truncation applied. If many candidates with long category names are generated, this log line could exceed Discord's 2000-char limit. This is an incomplete fix — the DUX-01 defense was applied to the lifecycle log but missed another log line in the same method.

---

## 3. Wave-1 Fix Verification

### DUX-01: Lifecycle log line truncation — VERIFIED CORRECT

**Original finding (round-1):** `_log_lifecycle_milestone` built a log line from `next_action`/`decision`/`focus`/`world_model`/recall counts without truncating the final string. Long values could exceed Discord's 2000-char limit and cause rejection.

**Fix applied (HEAD ff1c9fa):** `src/life_kernel/heartbeat.py:523-528`
```python
# DUX-01 fix: Discord rejects plain-text messages over 2000 chars.
# Long intent/focus values could push this line past the limit, so
# cap it well below 2000 (1900 leaves headroom for any wrapper).
_DISCORD_LOG_MAX = 1900
if len(line) > _DISCORD_LOG_MAX:
    line = line[: _DISCORD_LOG_MAX - 3] + "..."
```

**Verification:** The fix is correctly placed immediately before the `_log_channel.write(line)` call at line 541. The 1900-char limit provides 100 chars of headroom below Discord's 2000-char plain-text limit. The truncation includes a "..." suffix to indicate clipping. This matches the round-1 recommendation exactly.

**Status:** ✅ FIXED

---

### AUTO-06: Log category instead of candidate_type — VERIFIED CORRECT

**Original finding (round-1):** `heartbeat.py:602,611` used `getattr(c, 'candidate_type', '?')` which logged '?' for every candidate because `ImprovementCandidate` exposes `.category` (a `CandidateCategory` enum), not `.candidate_type`.

**Fix applied (HEAD ff1c9fa):** `src/life_kernel/heartbeat.py:620-625`
```python
# ImprovementCandidate exposes `.category` (a
# CandidateCategory enum), not `candidate_type` (AUTO-06
# fix — the old getattr logged '?' for every candidate).
categories = [
    str(getattr(c, "category", "?")) for c in candidates
]
```

**Verification:** The code now uses `c.category` instead of `candidate_type`. The comment explicitly documents AUTO-06 fix. The grep confirmed no `candidate_type` usage remains except in this explanatory comment. The fallback to "?" is defensive but should never trigger if `ImprovementCandidate` always has a `.category` attribute.

**Status:** ✅ FIXED

---

## 4. NEW Findings Table

| ID | Severity | Title | File:Line | Detail | Recommendation |
|---|---|---|---|---|---|
| DUX-06 | medium | Self-improvement log line not truncated (incomplete DUX-01 fix) | `src/life_kernel/heartbeat.py:635-638` | The 1h heartbeat's self-improvement candidate log line `f"[reflection] generated {len(candidates)} self-improvement candidate(s): {categories}"` does NOT apply the DUX-01 truncation. The `categories` list is built from `str(getattr(c, "category", "?"))` for each candidate. With many candidates (40+) and long category enum names (e.g., `"CandidateCategory.CODE_QUALITY_IMPROVEMENT"` ≈ 42 chars), the line could exceed Discord's 2000-char limit. Example: 50 candidates → 55 (base) + 2200 (categories) = 2255 chars (EXCEEDS). The DUX-01 fix only applied to the lifecycle log line at line 541, not to this log line. This is an incomplete fix — the same vulnerability exists in a different location. | Apply the same `_DISCORD_LOG_MAX` truncation to this log line before calling `_log_channel.write`. Alternatively, limit the `categories` list display (e.g., show first 10 + "... and N more"). |
| DUX-07 | low | UTF-8 slicing safety not documented | `src/life_kernel/heartbeat.py:526-528` | The DUX-01 fix uses `line[: _DISCORD_LOG_MAX - 3] + "..."` which slices a Python string. Python 3 strings are Unicode (not bytes), so slicing will never corrupt a character or produce invalid UTF-8 when later encoded. However, the fix doesn't document this assumption. This is not a real bug (Python's string handling makes it safe), but for auditing purposes it would be clearer if the code noted that Python string slicing is UTF-8-safe. | Add a comment noting that Python 3 string slicing is character-safe (no mid-codepoint corruption). |

---

## 5. Hard-Rejection Check (against continuation plan §10)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Docs-only implementation? | NO | Real code changes in `heartbeat.py` (DUX-01, AUTO-06 fixes). |
| 2 | Missing Discord proof? | N/A | Live proof required for final `P20 PRODUCTION PASS`; round-2 is code-only. |
| 3 | Raw `LLMRouter.chat` as brain path? | NO | Uses `HermesBrain.think` per round-1 audits. |
| 4 | Only health-check loops without memory context? | NO | Memory-driven per round-1 audits. |
| 5 | Sub-agent no output file? | NO | This audit writes to assigned path. |
| 6 | Tests/audits skipped to pass? | NO | No evidence of skipped tests in wave-1 fix commits. |
| 7 | Secrets in output/evidence? | NO | `_sanitize()` still redacts API keys, Bearer tokens, credentials. |
| 8 | `world_model_available = False` placeholder? | NO | Derived from adapter status (`graph.py:242`). |
| 9 | `idle_node` uses `random.choice`? | NO | Fixed per round-1 audits. |
| 10 | Adapters return `_placeholder:True`? | NO | Fixed per round-1 audits. |
| 11 | HARD STOP regression? | NO | No changes to HARD STOP logic in wave-1 fix commits. |
| 12 | Other services disturbed? | N/A | Requires deployment audit. |

**Hard-rejection verdict:** NONE TRIGGERED.

---

## 6. What's GOOD

- **DUX-01 fix correctly implemented:** Lifecycle log line is truncated to ≤1900 chars with a `_DISCORD_LOG_MAX` constant and explicit truncation logic. The 1900 limit provides sensible headroom below Discord's 2000-char limit.
- **AUTO-06 fix correctly implemented:** Heartbeat now logs `candidate.category` with an explicit comment documenting the fix. The old `candidate_type` attribute is gone.
- **Dashboard rendering preserved:** `render_embed` still renders all living-state fields (`memory_status`, `current_focus`, `next_planned_action`) with `_sanitize()` and `_truncate_field()` applied to prevent secret leakage and length overflows.
- **Edit-not-spam pattern preserved:** `DashboardWriter.update_dashboard` uses checksum-based skip to avoid redundant Discord round-trips, edits the existing message in place, and recovers gracefully when the message is deleted.
- **Log throttling preserved:** Lifecycle log is throttled to 1 per 5 minutes (`_LIFECYCLE_LOG_THROTTLE_SECONDS = 300`) with dedup on identical lines.
- **Sanitization preserved:** All user-controlled strings pass through `_sanitize()`, which redacts API keys (`sk-...`), Bearer tokens, and credential patterns.
- **Brain/world-model status honest:** `world_model_status` tracks "unavailable", "degraded", or "active" based on real adapter availability, not a static placeholder.
- **No UTF-8 corruption risk:** Python 3's Unicode string slicing is character-safe, so the DUX-01 truncation will never corrupt multi-byte characters (though this isn't documented in the code).
- **Fail-soft preserved:** Both log write calls have `except Exception` handlers to prevent Discord API errors from crashing the heartbeat.

---

## 7. Conclusion

The wave-1 Discord UX fixes (DUX-01 and AUTO-06) are correctly implemented and achieve their intended goals. The dashboard rendering, sanitization, edit-not-spam pattern, log throttling, and brain-fallback status all remain correct. However, the DUX-01 fix is incomplete: it truncated the lifecycle log line but missed the self-improvement candidate log line in the same method, leaving a similar vulnerability. This is a medium-severity issue (not critical) because the 1h heartbeat is less frequent and unlikely to generate 40+ candidates in practice, but it should be fixed for consistency and defense-in-depth. No hard-rejection criteria are triggered.

**Recommended next actions:**
1. Apply the same `_DISCORD_LOG_MAX` truncation to the self-improvement log line at `heartbeat.py:635-638` (DUX-06).
2. Optionally document that Python 3 string slicing is UTF-8-safe (DUX-07).
