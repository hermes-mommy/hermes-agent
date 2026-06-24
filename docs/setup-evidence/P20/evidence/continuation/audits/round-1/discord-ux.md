# Discord UX Audit — P20 Living Autonomy Kernel Continuation (Round 1)

**Auditor:** Discord UX specialist (independent)  
**Scope:** `src/life_kernel/dashboard.py`, `dashboard_writer.py`, `heartbeat.py`, `graph.py`, `log_channel.py`, `state.py`; `src/core/main.py` wiring.  
**Date:** 2026-06-24  
**Commits reviewed:** `HEAD~2` (`a272587`) + `HEAD` (`df83f70`) cumulative diff.  
**Already-audited dimensions (do not redo):** security-secrets (PASS_WITH_NOTES), memory-worldmodel (PASS_WITH_NOTES).

---

## 1. Verdict

**PASS_WITH_NOTES**

The continuation satisfies the Discord-visible autonomy requirements for this wave: the dashboard embed now renders living-state fields (`memory_status`, `current_focus`, `next_planned_action`), edit-not-spam is preserved, lifecycle logging is throttled and includes `intent=`/`recall=`/`world_model=`, and the brain path is `HermesBrain.think` (not raw `LLMRouter.chat`). Two medium-severity UX issues were found: (a) the lifecycle log line can exceed Discord's 2000-character limit under extreme long-field conditions because truncation only applies per-field in the embed, not to the log string; and (b) `DashboardRenderer._truncate_field` silently caps at 1024 characters, which masks data silently and is not the Discord limit. No hard-rejection criteria are triggered.

---

## 2. Executive Summary

This audit focused exclusively on the Discord user-experience surface of the P20 Living Autonomy Kernel continuation. The implementation successfully:

- Wires real P16/P18 recall results into the dashboard via `memory_status` (`src/life_kernel/graph.py:228-232`).
- Renders `current_focus`, `next_planned_action`, and `memory_status` in the Discord embed (`src/life_kernel/dashboard.py:321-354`).
- Keeps the edit-not-spam invariant through `DashboardWriter.update_dashboard` (`src/life_kernel/dashboard_writer.py:126-182`).
- Adds a throttled, deduplicated lifecycle log line with autonomous intent narrative in `heartbeat.py:494-537`.
- Uses `HermesBrain.think` (not raw `LLMRouter.chat`) for brain-augmented decide/act/idle paths (`src/life_kernel/graph.py:104-130`, `724-856`).

Two real bugs remain at the **medium** level: the lifecycle log line is not length-capped before being sent to Discord, and the embed field truncate limit (1024) is arbitrary and not documented. No hard-rejection criteria are met.

---

## 3. Findings Table

| ID | Severity | Title | File:Line | Detail | Recommendation |
|---|---|---|---|---|---|
| DUX-01 | medium | Lifecycle log line can exceed Discord 2000-char limit | `src/life_kernel/heartbeat.py:517-521` | `_log_lifecycle_milestone` builds `line` from `next_action`/`decision`/`focus`/`world_model`/recall counts without truncating the final string. Although embed fields are truncated, this plain-text log is sent directly to `LogChannel.write`. With long `next_action` or `focus` values, the line can exceed 2000 characters and Discord will reject it. | Truncate `line` to ≤1900 chars before calling `_log_channel.write`, or split into multiple messages. |
| DUX-02 | medium | Embed field truncate limit is arbitrary (1024) and silent | `src/life_kernel/dashboard.py:279-283` | `_truncate_field` caps at 1024 characters. Discord's actual limits are 1024 for embed field values and 6000 for total embed length, but this magic number is undocumented and silently drops data. | Document the limit or derive it from a named constant; consider warning when truncation occurs. |
| DUX-03 | low | `render_embed` not covered for populated recall state in tests | `tests/life_kernel/test_dashboard.py:344-368` | `test_render_embed_fields` passes minimal values and does not assert that `memory_status`, `current_focus`, or `next_planned_action` appear in the generated embed fields when populated. | Add a test that populates recall-driven fields and asserts their values are rendered and sanitized. |
| DUX-04 | low | `_truncate_field` applied after `_sanitize`, but emoji-containing `status_display` is truncated first | `src/life_kernel/dashboard.py:301-314` | `status_display` is built with emoji and then truncated; under normal lengths this is fine, but the truncation logic does not distinguish between semantic content and formatting prefixes. | Minor; acceptable for current use. |
| DUX-05 | info | Lifecycle log dedup key uses raw string; long variable values can reduce dedup effectiveness | `src/life_kernel/heartbeat.py:528-533` | If `next_action`/`focus`/`world_model` vary slightly each cycle, dedup will miss; combined with 5-minute throttle this is acceptable but could be noisier than intended. | Consider normalizing the dedup key (e.g., hash of phase+decision only) if log noise is observed in production. |

---

## 4. Hard-Rejection Check (against continuation plan §10)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Docs-only implementation? | NO | Real code changes in `graph.py`, `dashboard.py`, `heartbeat.py`, `main.py`, adapters. |
| 2 | Missing Discord proof? | N/A at audit time | Live proof is required for final `P20 PRODUCTION PASS`; this round is code-only. |
| 3 | Raw `LLMRouter.chat` as brain path? | NO | Brain path is `HermesBrain.think` (`graph.py:120-121`). |
| 4 | Only health-check loops without memory context? | NO | `observe_node` populates recall; `idle_node` is memory-driven (`graph.py:613-638`). |
| 5 | Sub-agent no output file? | N/A | This sub-agent will write its report to the assigned path. |
| 6 | Tests/audits skipped to pass? | NO | Test suite still expected to run; no skipped tests introduced by these files. |
| 7 | Secrets in output/evidence? | NO | `_sanitize` redacts API keys, Bearer tokens, and credential patterns; verified by tests. |
| 8 | `world_model_available = False` placeholder still present? | NO | Derived from adapter status (`graph.py:242`). |
| 9 | `idle_node` still uses `random.choice`? | NO | Removed; deterministic fallback uses `cycle_count % len(fallbacks)` (`graph.py:633-638`). |
| 10 | Adapters still return `_placeholder:True`? | NO | `p16_adapter.py` and `p18_adapter.py` now call real clients; `_degraded` is the only flag. |
| 11 | HARD STOP regression? | NO | Non-LLM safety path preserved (`graph.py:314-316`, `heartbeat.py:254-358`). |
| 12 | Other services disturbed? | N/A at audit time | Deployment audit required for final verdict. |

**Hard-rejection verdict:** NONE TRIGGERED.

---

## 5. What's GOOD

- **Living-state dashboard:** `DashboardRenderer.render_embed` now includes `Current Focus`, `Next Planned Action`, and `Memory` fields, populated by graph nodes (`dashboard.py:320-354`).
- **Sanitization preserved:** All rendered strings pass through `_sanitize`, which redates API keys, Bearer tokens, and credential patterns (`dashboard.py:27-69`; tests in `test_dashboard.py:146-184`).
- **Edit-not-spam preserved:** `DashboardWriter.update_dashboard` edits the existing message in place and recovers on deleted messages (`dashboard_writer.py:126-218`).
- **Throttled lifecycle log:** `_log_lifecycle_milestone` writes at most one line per 5 minutes and deduplicates identical lines (`heartbeat.py:494-537`).
- **Intent/recall/world_model in log line:** The lifecycle line now includes `focus=`, `decision=`, `intent=`, `recall=mem:X/kg:Y`, and `world_model=` (`heartbeat.py:517-521`).
- **Brain fallback badge is honest:** When `hermes_brain` is unavailable, static logic runs; when available, `HermesBrain.think` is used with a 30-second timeout and fail-soft fallback (`graph.py:104-130`).
- **No raw LLMRouter path:** `create_life_mind_graph` documents that only `HermesBrain.think` is used (`graph.py:872-874`).
