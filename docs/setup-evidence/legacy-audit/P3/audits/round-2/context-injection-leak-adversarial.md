# Context Injection Leak Adversarial Audit (Wave-2)

**Date:** 2026-06-25
**Agent:** Wave-2 Adversarial Audit (Explore, read-only)
**Scope:** Hunt every path where private/Critical/Restricted/surveillance data can leak into LLM context via memory injection
**Read-only affirmation:** YES.

---

## Files Examined

- `src/memory/read_pipeline.py` — `build_safe_content`, `apply_token_budget`, `estimate_tokens`, `recall_memories`
- `src/memory/compaction.py` — `ContextCompactor`
- `src/core/services/prompt_loader.py` — `get_system_prompt_with_context`, `assemble_system_prompt_with_memory`
- `src/hermes/_memory_bridge.py` — `HermesMemoryBridge`
- `src/memory/embeddings.py` — all logging surfaces
- `src/discord/cmd_memory_search.py` — `memory_search_callback`
- `src/life_kernel/cognition.py` — `BackgroundCognition`
- `src/life_kernel/graph.py` — `observe_node`, `decide_node`, `_make_brain_idle`, `_make_brain_decide`
- `src/life_kernel/p18_adapter.py` — `MemoryRecallAdapter`
- `src/life_kernel/state.py` — `LifeMindState`
- `src/life_kernel/dashboard.py` — `DashboardRenderer._sanitize`
- `src/core/main.py` lines 250-290 — life-kernel memory wiring
- `src/discord/_auth_guard.py` — `is_faiz_interaction`

---

## (a) build_safe_content — Enumerate Every Branch

`src/memory/read_pipeline.py:419-475`

**Branch 1: safe_mode=False (Normal mode), line 447-451**
```python
if not safe_mode:
    if summary and raw and len(summary) < len(raw) * 0.8:
        return summary, True
    return raw, False
```
When safe_mode is OFF, raw_content is returned for ALL episodes regardless of classification. The ONLY protection is the classification ceiling filter applied earlier in `recall_memories` (lines 1078-1096). For `principal="guinevere_core"`, the ceiling is CRITICAL (line 165: `_CLASSIFICATION_CELING["guinevere_core"] = CRITICAL`), meaning nothing is filtered. All Restricted, Confidential, and Critical content is returned raw.

**Severity: [HIGH]** — When safe_mode is False (the default for the life-kernel path; see finding (f)), all classification levels are returned with raw content. The classification ceiling for `guinevere_core` permits everything.

**Branch 2: safe_mode=True, CRITICAL, line 456-457**
```python
if cls == CRITICAL:
    return SAFE_MODE_PLACEHOLDER, False
```
Raw Critical content is replaced with a fixed placeholder string. This is correct.

**Branch 3: safe_mode=True, RESTRICTED or CONFIDENTIAL, lines 459-462**
```python
if cls == RESTRICTED or cls == CONFIDENTIAL:
    if summary:
        return summary, True
    return SAFE_MODE_RESTRICTED_PLACEHOLDER, False
```
Returns summary (not raw) if available. If no summary exists, returns placeholder. Raw content is never returned. Correct.

**Branch 4: safe_mode=True, PUBLIC or INTERNAL, lines 465-472**
```python
if cls == PUBLIC or cls == INTERNAL:
    if _is_safe_mode_blocked_content(episode):
        return SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER, False
    if summary:
        return summary, True
    return raw, False
```
For Public/Internal episodes that match blocked-content tags, content is replaced. For non-blocked Public/Internal episodes, raw content IS returned. This is intentional — Public/Internal data is considered non-sensitive.

**Branch 5: safe_mode=True, unknown classification, line 474-475**
```python
return SAFE_MODE_PLACEHOLDER, False
```
Fail-closed. Correct.

**Additional finding in `_is_safe_mode_blocked_content` (lines 377-416): Tag matching bug [MEDIUM]**
At line 393-394, when `tags_raw` is a `list`, `tuple`, or `set`:
```python
tags_lower.add(f"{tags_raw}".lower())
```
This converts the entire collection to a single string (e.g., `"['emotional', 'chat']"`) rather than iterating over individual tags. The substring check `blocked in tag` then operates on the stringified collection. This works by accident for most cases, but creates a false-positive edge case: a tag `"not_emotional"` would match because `"emotional"` is a substring of `"not_emotional"`. This is a safe-direction bug (over-blocking) but indicates fragile logic.

---

## (b) Token-Budget Truncation — Order-of-Operations

`src/memory/read_pipeline.py:493-523` and `recall_memories` lines 1101-1124

**Execution order in recall_memories:**
1. Line 1101-1121: `build_safe_content` is called for every result, and `r["safe_content"]` is assigned the safe/placeholder value.
2. Line 1124: `apply_token_budget(results, token_budget)` trims results from the bottom.

**Can apply_token_budget strip away redaction wrappers?** No. The function (lines 493-523) discards entire result dictionaries from the end of the sorted list until the total estimated tokens fit the budget. It never truncates the `safe_content` string of any individual result. An item is either included whole or dropped whole.

**Severity: [LOW]** — No order-of-operations vulnerability. The redaction placeholder is applied before token budget trimming, and trimming operates on whole items, not individual text.

**However, there is a subtle side effect:** The placeholder strings (e.g., `SAFE_MODE_PLACEHOLDER` at ~58 chars / ~14 tokens) are much smaller than raw content. If the budget is tight, the greedy walk may include large raw-content items first (for Public/Internal) and then have no budget left for small placeholder-redacted items. This does NOT cause a leak, but it means the output skews toward larger (less-redacted) content, which is the opposite of what a safety-conscious design would prefer.

---

## (c) ContextCompactor — Does Compaction Bypass DNR/Classification?

`src/memory/compaction.py:52-296`

**Critical distinction:** The `ContextCompactor` operates on **conversation messages** (the chat history between user and assistant), NOT on episodic memory episodes. It is a conversation-history compressor, not a memory recall component.

**DNR bypass:** Not applicable in the traditional sense. The compactor does not consult the `memory.episodes` table or the DNR flag. It operates on an entirely different data structure (list of message dicts with `role` and `content` keys).

**Classification bypass:** Not applicable directly. However, if a conversation message previously contained memory content (already filtered by `build_safe_content`), the compactor's summarization step sends that content to an LLM:

Lines 268-271:
```python
for idx, msg in enumerate(messages, start=1):
    role = msg.get("role", "unknown")
    content = msg.get("content", "")
    prompt_parts.append(f"{idx}. [{role}]: {content}")
```

The raw middle messages are sent to the LLM for summarization. If those messages contained memory-sourced content that was already filtered through `safe_content`, this is not a bypass (the content was already redacted upstream). But if a message contained raw content that was never filtered (e.g., a direct user message quoting sensitive data), the summarization LLM sees it and could paraphrase it into the summary.

**Severity: [MEDIUM]** — The compactor does not bypass DNR or classification, but it sends raw message content to an external LLM for summarization without any additional redaction pass. The content was presumably already in the conversation context, so this is a content-expansion risk (the summary persists the sensitive content in a new form) rather than a fresh leak.

---

## (d) Logging — Raw Memory Text, Vector Values, or Secret-Derived Data

**read_pipeline.py:**
All log statements verified clean:
- Line 508-519 (`token_budget_trimmed`): logs budget, total_before (int), returned_after (int), discarded (int). No raw content.
- Lines 884-885: Query text is SHA-256 hashed before logging (`_query_hash = hashlib.sha256(...).hexdigest()[:16]`). The raw query is never logged.
- Lines 995-999 (`recall_no_results`): logs query_length (int) and query_hash only.
- Lines 1132-1149 (`recall_complete`): logs query_length, query_hash, candidates (int), filtered (int), returned (int), principal, safe_mode (bool), safe_mode_redacted (int), safe_mode_blocked (int), kg_enabled (bool), fsrs_enabled (bool), fsrs_updated (int). No raw content, no vectors.

**compaction.py:**
All log statements verified clean:
- Lines 162-168 (`context_compacted`): logs counts and tokens_saved (int). No message content.
- Lines 233-234 (`tiktoken_not_available_fallback_to_char_div4`): no data at all.
- Lines 238-243 (`tiktoken_count_error_fallback`): logs error string and text_length (int). No raw text.
- Lines 288-291 (`llm_summarization_failed`): logs error. No message content.

**embeddings.py:**
Docstring claim (lines 16-18): "Logs only metadata: model, dimensions, classification, redaction_applied, duration/error. Never logs raw text, vector values, or secrets."

Verification:
- Lines 537-542 (`embedding_success`): logs classification, redaction_applied (bool), char_count (int). No raw text, no vectors.
- Lines 552-558 (`embedding_batch_success`): logs batch_size, classification, redaction_applied. No raw text.
- Lines 616-620 (`aembedding_success`): logs classification, redaction_applied, char_count. No raw text.
- Line 323: logs env var NAMES (`env_vars=self.api_key_env_vars`), not values. Safe.
- Lines 647-654 (`_raise_on_http_error`): Raises exceptions with `response.text[:200]`. This is NOT a direct log but an exception message that propagates upward. The 200-char snippet of API error response could theoretically contain model/API metadata, but embedding APIs do not echo back input text in error responses.

**Severity: [LOW]** — The docstring claim is substantively true. No log statement in any of the three files emits raw memory text, vector values, or secrets. The only minor concern is `response.text[:200]` in exception messages from `_raise_on_http_error`, which is API error response text, not user content.

---

## (e) Discord /memory-search — Restricted/Critical Content Exposure

`src/discord/cmd_memory_search.py:346-428`

**Auth gate:** Lines 358-361:
```python
from ._auth_guard import is_faiz_interaction
if not is_faiz_interaction(interaction):
    await _send_denied(interaction)
    return
```
`is_faiz_interaction` (`src/discord/_auth_guard.py:11-22`) checks that the interaction user's ID equals the guild owner's ID. Only the guild owner (Faiz) can use this command. Auth is enforced.

**However:** Lines 408-416:
```python
results = await recall_memories(
    session, query, limit=DEFAULT_LIMIT,
    exclude_dnr=True,
    safe_mode=False,          # <-- RAW content returned
    principal="guinevere_core", # <-- CRITICAL ceiling
    embedding_service=embedding_service,
)
```

The command uses `safe_mode=False` and `principal="guinevere_core"`, which means:
- Classification ceiling = CRITICAL (all levels permitted)
- No safe-mode substitution occurs
- Raw `raw_content` is returned for all episode classifications

The results are then displayed in a Discord embed (lines 282-290), truncated to 100 characters per result:
```python
content = str(result.get("safe_content", ""))
truncated = content[:100] + "..." if len(content) > 100 else content
```

Since `safe_mode=False`, `safe_content` IS the raw content (see finding (a), Branch 1). So 100-character snippets of Critical/Restricted content are displayed.

**Mitigations present:**
- Ephemeral response (line 469): only the invoking user sees the embed.
- Faiz-only auth gate.

**Severity: [MEDIUM]** — The guild owner can see 100-character snippets of Critical-classified memory content through the Discord /memory-search command. This is likely intentional (Faiz is the operator), but it creates a surface where raw sensitive content leaks into Discord's message storage. If the guild owner account is compromised, this becomes a data exfiltration vector. Consider adding `safe_mode=True` even for the owner, or at minimum masking Critical content.

---

## (f) HARD STOP safe_mode Never Reaches Memory Recall in the Life-Kernel Graph

**Severity: [CRITICAL]**

### This is the most critical finding.

**The wiring (src/core/main.py:254-287):**

Line 272:
```python
_life_safe_recall = os.environ.get("LIFE_KERNEL_SAFE_RECALL", "0") == "1"
```
Default: `False`. Unless the operator explicitly sets `LIFE_KERNEL_SAFE_RECALL=1` in the environment, all life-kernel memory recall is unredacted.

Lines 274-283 — the recall closure:
```python
async def _life_recall_fn(*, query_text, principal="guinevere_core", exclude_dnr=True):
    async with _lk_session_factory() as _lk_session:
        return await _recall_memories(
            _lk_session, query_text, limit=20, exclude_dnr=exclude_dnr,
            principal=principal, safe_mode=_life_safe_recall,  # False by default
        )
```

`safe_mode` is baked into the closure at construction time. It is NOT a runtime parameter and cannot be changed by HARD STOP detection.

**The adapter (src/life_kernel/p18_adapter.py:48-115):**

`MemoryRecallAdapter.recall()` calls `self.memory_client()` (the `_life_recall_fn` closure). The adapter does NOT accept or pass a `safe_mode` parameter. It has no awareness of safe_mode at all.

**The graph flow (src/life_kernel/graph.py):**

The graph topology is: `START -> observe -> decide -> act/reflect/idle -> END`

1. `observe_node` (lines 188-334) runs FIRST. At line 262-264:
```python
if memory_adapter is not None:
    try:
        mem_result = await memory_adapter.recall(recall_context)
```
This recalls memories with `safe_mode=False` (from the closure). Raw Critical content is stored in graph state as `recalled_memories` (line 278: `"memory_context": recalled_memories`).

2. `decide_node` (lines 337-415) runs SECOND. At line 373:
```python
if state.get("hard_stop_requested", False):
    logger.warning("HARD_STOP requested - routing to END")
    return {"decision": "end"}
```
The HARD STOP check happens AFTER observe_node has already populated the state with unredacted memories.

3. The `decide_node` does NOT purge `recalled_memories` from state when HARD STOP is detected. It simply returns `{"decision": "end"}`. The raw content persists in the checkpointed state.

4. The brain-enriched variants (`_make_brain_idle`, `_make_brain_decide`) receive memory metadata (relevance + date only, not raw content) in the LLM prompt. This is a mitigation for the brain path, but the raw `recalled_memories` still exist in graph state.

**The `_safe_mode` grep confirmation:** A grep for `safe_mode` across `src/life_kernel/` returned zero matches. The life-kernel has no safe_mode awareness at all.

**Severity: [CRITICAL]** — The observe_node executes memory recall with safe_mode=False before decide_node can detect HARD STOP. When HARD STOP is activated (safe word, distress signal, consent revocation), the graph state already contains raw unredacted Critical/Restricted memory content. The content persists in the LangGraph checkpoint. There is no mechanism to retroactively redact the recalled memories after HARD STOP is detected.

---

## Additional Findings

**Finding (g): `prompt_loader.py` safe_mode override via hard_stop_handler [HIGH]**

`src/core/services/prompt_loader.py:251-254`:
```python
resolved_safe_mode = safe_mode
if hard_stop_handler is not None:
    resolved_safe_mode = bool(getattr(hard_stop_handler, "is_safe", False))
```

When `hard_stop_handler` is provided, `resolved_safe_mode` is set to `hard_stop_handler.is_safe`. If `is_safe` is `True`, safe_mode becomes `True`. But the semantics are inverted: `is_safe=True` means "the system is safe" (no hard stop active), which would set safe_mode to True (enabling redaction). If the hard stop IS active, `is_safe` would be `False`, meaning safe_mode becomes `False` — disabling redaction during a hard stop. This appears to be a semantic inversion.

**Severity: [HIGH]** — If the hard_stop_handler's `is_safe` property means "system is safe to operate," then `resolved_safe_mode = bool(getattr(hard_stop_handler, "is_safe", False))` sets safe_mode=True when the system is safe (normal operation), and safe_mode=False when the system is NOT safe (hard stop). This is backwards: redaction should be MORE strict during hard stop, not less.

However, this only affects the Hermes conversation path (prompt_loader), not the life-kernel graph path. The life-kernel does not use prompt_loader.

**Finding (h): KG enrichment bypasses safe_content in _memory_bridge.py [MEDIUM]**

`src/hermes/_memory_bridge.py:166-192`:
```python
if kg_enabled:
    ...
    for kg_item in kg_results:
        description = (
            getattr(kg_item, "description", None)
            or getattr(kg_item, "display_name", "")
        )
        results.append({
            "safe_content": str(description),
            "classification": "Internal",
            ...
        })
```

KG results are appended to the recall results with `classification="Internal"` hardcoded and `safe_content` set to the raw KG entity description. If a KG entity description contains sensitive information (e.g., a person's real name linked to a Critical episode), it bypasses the classification ceiling and safe-mode filtering entirely because it was never processed through `build_safe_content` or the classification ceiling filter.

**Severity: [MEDIUM]** — KG entity descriptions are injected into recall results without passing through the memory read pipeline's safety gates (classification ceiling, safe-mode, DNR). The hardcoded `classification="Internal"` means these entries would pass the classification ceiling filter for all principals and would not be blocked by safe-mode (Internal is below the safe-mode ceiling for `guinevere_core`).

---

## Status Verdict

**VERDICT: FAIL — 2 CRITICAL/HIGH issues confirmed with code evidence.**

**CRITICAL-1 (finding (f)):** The life-kernel graph's observe_node recalls memories with safe_mode=False before decide_node can detect HARD STOP. Raw Critical/Restricted content persists in checkpointed graph state after HARD STOP is triggered. The string `safe_mode` does not appear anywhere in `src/life_kernel/`. This is confirmed by:
- `src/core/main.py:272` — `_life_safe_recall` defaults to `False`
- `src/life_kernel/p18_adapter.py:92-97` — adapter does not accept or pass safe_mode
- `src/life_kernel/graph.py:262-264` — observe_node calls recall before decide_node runs
- `src/life_kernel/graph.py:373` — HARD STOP check in decide_node runs after observe

**HIGH-1 (finding (g)):** The `hard_stop_handler.is_safe` semantic in `prompt_loader.py:254` appears inverted — safe_mode is set to True when the system is safe (normal) and False when the system is unsafe (hard stop active), which is the opposite of the intended safety posture.

**MEDIUM findings:** KG enrichment bypasses safe_content pipeline (_memory_bridge.py:166-192); Discord /memory-search returns raw Critical content for guild owner (cmd_memory_search.py:413); tag matching bug in `_is_safe_mode_blocked_content` (read_pipeline.py:393-394); ContextCompactor sends raw messages to LLM without redaction (compaction.py:268-271).

**LOW findings:** Token-budget truncation order-of-operations is safe; embeddings.py docstring logging claim is verified true; exception messages in embeddings.py contain 200-char API response snippets (not user content).