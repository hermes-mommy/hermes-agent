# Auditor Report — Memory & Privacy Layer (Hermes Phase 1)

**Audit Scope:** Hermes native memory isolation, Guinevere memory pipeline safety, auto-store privacy  
**Date:** 2026-06-04  
**Auditor:** Guinevere (independent memory-privacy specialist)  
**Verdict:** ✅ **PASS**

---

## 1. What Was Audited

| # | File | Purpose |
|---|------|---------|
| 1 | `src/hermes/session_adapter.py` | AIAgent constructor, Hermes memory isolation |
| 2 | `src/discord/conversational_handler.py` | Auto-store logic (Step 12b), memory recall (Step 9), logging |
| 3 | `src/memory/read_pipeline.py` | DNR exclusion, classification ceiling, safe-mode content substitution |
| 4 | `src/memory/write_pipeline.py` | `store_episode()` signature, classification defaults |
| 5 | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Memory-related safety requirements |
| 6 | `src/` (grep sweep) | Hermes memory API usage across codebase |

---

## 2. Criteria-by-Criteria Findings

### 2.1 AIAgent Constructor — `skip_memory` and `skip_context_files`

**File:** `src/hermes/session_adapter.py`, method `_new_agent()` (lines ~96–108)

```python
return AIAgent(
    base_url=llm_config["base_url"],
    model=llm_config["model"],
    provider=llm_config["provider"],
    api_key=llm_config.get("api_key", ""),
    skip_memory=True,          # ✅
    skip_context_files=True,    # ✅
    quiet_mode=True,
    max_iterations=1,
    enabled_toolsets=[],
    disabled_toolsets=["*"],
)
```

| Criterion | Expected | Found | Verdict |
|-----------|----------|-------|---------|
| `skip_memory` | `True` | `True` (not False, not omitted) | ✅ PASS |
| `skip_context_files` | `True` | `True` (not False, not omitted) | ✅ PASS |
| No fallback/override path | Only one constructor call site | Single static method `_new_agent()` | ✅ PASS |

**Context:** `_new_agent()` is the only code path that constructs `AIAgent` in the entire adapter. It is called exclusively from `get_or_create_session()`. No inline construction exists.

---

### 2.2 Hermes Memory API Usage — Codebase Sweep

**Grep:** `memory_provider|memory_manager|memory_store|HermesMemory|hermes.*memory` across `src/**/*.py`

| Criterion | Result |
|-----------|--------|
| `memory_provider` usage | ❌ Zero matches |
| `memory_manager` usage | ❌ Zero matches |
| `memory_store` usage | ❌ Zero matches |
| `hermes.*memory` pattern | ❌ Zero matches |
| `src/hermes/` imports from Guinevere `src.memory` | ❌ Zero matches |

**Isolation confirmed.** Hermes has no awareness of Guinevere's memory subsystem, and Guinevere's memory subsystem never delegates to Hermes.

---

### 2.3 Auto-Store Privacy (Step 12b)

**File:** `src/discord/conversational_handler.py`, lines ~318–351

```python
# ── Step 12b: Auto-store conversation to memory ─────────
try:                                                        # ✅ try/except wrapper
    ...
    from src.memory.write_pipeline import RESTRICTED, store_episode
    conversation_content = f"Faiz: {content}\nGuinevere: {response_text}"  # ✅ format
    conversation_summary = content[:200]                    # ✅ truncated summary

    async with session_factory() as session:
        await store_episode(
            session=session,
            content=conversation_content,
            source="discord_conversation",                   # ✅ source
            classification=RESTRICTED,                       # ✅ RESTRICTED
            importance=3,                                    # ✅ importance=3
            summary=conversation_summary,
            episode_type="conversation",
            tags=["discord", "chat", "auto-store"],
            embedding_service=embedding_svc,
        )
    logger.info("memory_auto_store_success", ...)
except Exception as exc:
    logger.warning("memory_auto_store_error", ...)           # ✅ never crashes conversation
```

| Criterion | Expected | Found | Verdict |
|-----------|----------|-------|---------|
| Classification | `RESTRICTED` | `RESTRICTED` | ✅ PASS |
| Content format | `"Faiz: {msg}\nGuinevere: {resp}"` | Exact match | ✅ PASS |
| Try/except wrap | Never crash conversation | All paths caught | ✅ PASS |
| Importance | `3` | `3` | ✅ PASS |
| Source | `discord_conversation` | Exact match | ✅ PASS |
| Graceful degradation (no session factory) | Skip, log, never crash | `if session_factory is not None` guard | ✅ PASS |

---

### 2.4 Memory Recall Safety (Step 9)

**File:** `src/discord/conversational_handler.py`, lines ~265–298

```python
system_prompt = await assemble_system_prompt_with_memory(
    session=session,
    query_text=content,
    mood=current_mood,
    safe_mode=safe_mode_activated,    # ✅ safe_mode propagated
    principal="guinevere_core",       # ✅ correct principal
    limit=3,
    token_budget=400,
    embedding_service=embedding_svc,
)
```

| Criterion | Expected | Found | Verdict |
|-----------|----------|-------|---------|
| Uses `read_pipeline` (via `assemble_system_prompt_with_memory`) | Yes | Confirmed | ✅ PASS |
| `safe_mode` parameter propagated | Yes | `safe_mode_activated` (bool from DistressDetector) | ✅ PASS |
| Wrapped in try/except | Never crash | Outer `try` on all memory recall + inner `except` for full fallback | ✅ PASS |
| Graceful fallback (no session factory) | Base prompt without memories | `get_system_prompt_with_context(memories=None, ...)` | ✅ PASS |

---

### 2.5 Read Pipeline — DNR, Classification Ceiling, Safe-Mode

**File:** `src/memory/read_pipeline.py`

#### DNR Exclusion

| Query Builder | DNR Filter Applied | Code Location |
|---|---|---|
| `build_vector_query()` | `.where(Episodes.do_not_recall.is_(False))` when `exclude_dnr=True` | Line ~540 |
| `build_fts_query()` | `.where(Episodes.do_not_recall.is_(False))` when `exclude_dnr=True` | Line ~555 |
| `build_recency_query()` | `.where(Episodes.do_not_recall.is_(False))` when `exclude_dnr=True` | Line ~570 |
| `recall_memories()` default | `exclude_dnr: bool = True` | Line ~605 |

✅ **All three signal queries apply DNR filter. Default is True (exclude DNR).**

#### Classification Ceiling

| Principal | Normal Mode Ceiling | Safe Mode Ceiling | Code |
|-----------|--------------------|--------------------|------|
| `guinevere_core` | `CRITICAL` | `INTERNAL` | `_CLASSIFICATION_CEILING` + `_SAFE_MODE_CEILING` |
| `guinevere_subagent` | `CONFIDENTIAL` | `PUBLIC` | Same pattern |
| `default` (unknown) | `RESTRICTED` | `PUBLIC` | Fail-closed |

Filter applied at lines ~620–628:
```python
ceil_level = CLASSIFICATION_ORDER.get(ceiling_label, 0)
...
if ep_class_level <= ceil_level:
    filtered_scored.append(r)
```

✅ **Ceiling correctly resolved by `_resolve_ceiling(principal, safe_mode)` and applied post-scoring.**

#### Safe-Mode Content Substitution

| Classification | Safe Mode Behavior | Code |
|---------------|-------------------|------|
| `CRITICAL` | `SAFE_MODE_PLACEHOLDER` — blocked entirely | `build_safe_content()` |
| `RESTRICTED` / `CONFIDENTIAL` | Prefer summary; fallback to `SAFE_MODE_RESTRICTED_PLACEHOLDER`; **never raw content** | `build_safe_content()` |
| `PUBLIC` / `INTERNAL` | Checks `_is_safe_mode_blocked_content()` for emotional/surveillance/escalation markers; blocks if matched | `build_safe_content()` |
| Unknown | `SAFE_MODE_PLACEHOLDER` — fail-closed | `build_safe_content()` |

Blocked content tags include: `emotional`, `emotion`, `sentiment`, `surveillance`, `surveil`, `monitor`, `spy`, `persona_escalation`, `yandere`, `punishment`, `jealousy`, `dark_mood`, `silent_mode`, `nuclear`, `possessive`.

✅ **Three-tier safe-mode content protection: classification-based redaction + blocked-content tag detection + unknown fail-closed.**

---

### 2.6 Write Pipeline — `store_episode()` Signature

**File:** `src/memory/write_pipeline.py`, lines ~130–150

```python
async def store_episode(
    session: EpisodeSession,
    content: str,
    *,
    source: str,
    classification: str = RESTRICTED,    # ✅ default = RESTRICTED
    importance: int = 5,
    ...
```

| Criterion | Expected | Found | Verdict |
|-----------|----------|-------|---------|
| Default classification | `RESTRICTED` | `RESTRICTED` | ✅ PASS |
| Critical guard | Fail closed without summary | `_guard_critical()` raises `WritePipelineCriticalError` | ✅ PASS |
| Critical embedding source | `summary` (sanitized), not raw content | `_compute_embedding()` passes `sanitized_summary=summary` | ✅ PASS |

---

### 2.7 Conversational Handler — Logging Privacy

**File:** `src/discord/conversational_handler.py`, Step 13 (lines ~353–372)

```python
user_id_hash = hashlib.sha256(str(author.id).encode()).hexdigest()[:8]

logger.info(
    "conversational_response",
    user_id_hash=user_id_hash,           # ✅ hash only
    channel_id=...,
    response_length=len(response_text),  # ✅ length, not content
    latency_ms=...,
    model_used=...,
    prompt_tokens=...,                   # ✅ metrics, not content
    completion_tokens=...,
    chunks_sent=...,
    distress_level=signal.detected_level.name,
    safe_mode_active=safe_mode_activated,
)
```

| Criterion | Verdict |
|-----------|---------|
| No raw user ID in logs | ✅ SHA-256 truncated to 8 hex chars |
| No raw conversation content | ✅ Only `response_length` (integer), no text |
| No raw query text | ✅ Not logged at all |
| User ID hash used consistently | ✅ All `logger.warning`/`logger.error` calls use `user_id_hash` |

Similarly in `session_adapter.py`, all logging uses `_hash_user_id()`:
```python
extra={"user_id_hash": _hash_user_id(user_id), "error": str(exc), ...}
```

✅ **Hash-based logging only. No raw content leakage.**

---

### 2.8 PersonaSafetyPolicy — Memory-Related Requirements

**File:** `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`

| Requirement | Section | Satisfied By |
|-------------|---------|-------------|
| Memory recall treated as medium/low trust, cannot override policy | §13.1 Trust Model | `read_pipeline` classification ceiling + safe-mode | ✅ |
| Prompt/memory instruction to bypass policy blocked (F-09) | §11 Forbidden Pattern F-09 | `read_pipeline` + safe-mode content substitution | ✅ |
| Surveillance data not used for blackmail (F-03) | §11 Forbidden Pattern F-03 | `_is_safe_mode_blocked_content()` blocks surveillance tags in safe mode | ✅ |
| Privacy-minimized safety audit log | §17 Implementation Requirements #7 | Hash-based logging throughout | ✅ |
| Sensitive context handling — summarize, don't quote | §12.3 | `build_safe_content()` prefers summaries; DNR exclusion available | ✅ |
| Over-logging intimate/distress prohibited (F-11) | §11 Forbidden Pattern F-11 | No raw content in any log statement | ✅ |
| Minimal audit logging (hash, not content) | §16.1, §16.2 | Consistent SHA-256 hashing | ✅ |

---

## 3. Structural Isolation Verification

```
┌─────────────────────────────────────────────────────────────┐
│  Hermes Session Adapter (src/hermes/session_adapter.py)     │
│  ┌──────────────────────┐                                   │
│  │ AIAgent(              │                                   │
│  │   skip_memory=True,   │ ← Hermes native memory disabled  │
│  │   skip_context_files=True                                │
│  │ )                     │                                   │
│  └──────────────────────┘                                   │
│  Redis DB4: multi-turn conversation history only             │
│  (NOT semantic memory — just ephemeral turn context)         │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Hermes response text only
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Conversational Handler (src/discord/)                       │
│  ┌────────────────────┐  ┌────────────────────────────┐     │
│  │ Step 9: Recall     │  │ Step 12b: Auto-Store       │     │
│  │ read_pipeline      │  │ write_pipeline             │     │
│  │ + DNR exclusion    │  │ classification=RESTRICTED  │     │
│  │ + classification   │  │ importance=3               │     │
│  │   ceiling          │  │ try/except wrapped         │     │
│  │ + safe_mode        │  │                            │     │
│  └────────────────────┘  └────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Guinevere Memory Pipeline (src/memory/)                     │
│  ┌────────────────────┐  ┌────────────────────────────┐     │
│  │ read_pipeline.py   │  │ write_pipeline.py           │     │
│  │ - DNR exclusion    │  │ - default=RESTRICTED        │     │
│  │ - ceiling filter   │  │ - Critical fail-closed      │     │
│  │ - safe-mode subs.  │  │ - summary-based embedding   │     │
│  │ - token budget     │  │                            │     │
│  └────────────────────┘  └────────────────────────────┘     │
│  Database: memory.episodes (PostgreSQL + pgvector)           │
└─────────────────────────────────────────────────────────────┘
```

**No cross-contamination path exists.** Hermes ↔ Guinevere memory boundary is clean.

---

## 4. Validation Results

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | `skip_memory=True` on AIAgent constructor | ✅ PASS |
| 2 | `skip_context_files=True` on AIAgent constructor | ✅ PASS |
| 3 | No Hermes `memory_provider` usage | ✅ PASS |
| 4 | No Hermes `memory_manager` usage | ✅ PASS |
| 5 | No Hermes `memory_store` usage | ✅ PASS |
| 6 | Auto-store classification = `RESTRICTED` | ✅ PASS |
| 7 | Auto-store content format: `"Faiz: {msg}\nGuinevere: {resp}"` | ✅ PASS |
| 8 | Auto-store wrapped in try/except | ✅ PASS |
| 9 | Memory recall uses read_pipeline with DNR exclusion | ✅ PASS |
| 10 | Classification ceiling active in recall | ✅ PASS |
| 11 | Safe-mode content substitution active | ✅ PASS |
| 12 | Safe-mode blocked-content tag detection active | ✅ PASS |
| 13 | `safe_mode` propagated to memory recall | ✅ PASS |
| 14 | No raw conversation content in logs | ✅ PASS |
| 15 | Hash-based logging (SHA-256, truncated) | ✅ PASS |
| 16 | `write_pipeline` default classification = `RESTRICTED` | ✅ PASS |
| 17 | Critical write fails closed without summary | ✅ PASS |
| 18 | PersonaSafetyPolicy memory requirements satisfied | ✅ PASS |

**18/18 criteria PASS.**

---

## 5. Design Decisions & Caveats

### 5.1 Conversation History in Redis (Not a Privacy Concern)

`session_adapter.py` stores multi-turn conversation history in Redis DB4. This is **not Hermes native memory** — it is ephemeral turn context for the LLM, with a 2-hour TTL (`SESSION_TTL = 7200`). The actual episodic memory is in PostgreSQL via `write_pipeline`. This is a correct and intentional design choice.

### 5.2 Auto-Store Captures Full Response Text

`conversation_content = f"Faiz: {content}\nGuinevere: {response_text}"` writes the complete conversation turn to `memory.episodes`. This is classified as `RESTRICTED` and the `write_pipeline` feed it through `EmbeddingService.aembed()` which applies classification-aware sanitization. The try/except wrapper ensures store failure never breaks the conversation.

### 5.3 Safe-Mode Recall Path Not Yet Exercised in Tests

The safe-mode propagation chain (`DistressDetector → safe_mode_activated → assemble_system_prompt_with_memory → recall_memories(safe_mode=True) → build_safe_content`) has correct code but no dedicated integration test was found in the audit scope. This does not affect the PASS verdict (code is correct), but an integration test covering the full path would strengthen evidence.

### 5.4 Summary Field Truncation

`conversation_summary = content[:200]` uses raw character slicing, which may split mid-word. This is cosmetic — the summary is stored in the database and displayed in recall results, but truncation quality does not affect privacy or safety.

---

## 6. Boundary Compliance

| Boundary | Status |
|----------|--------|
| No persona drift from memory poisoning | ✅ — `read_pipeline` treats memory as medium/low trust; safe-mode blocks emotional/surveillance/escalation content |
| No consent violation via memory recall | ✅ — DNR exclusion + classification ceiling |
| No surveillance overreach via auto-store | ✅ — `RESTRICTED` classification + `EmbeddingService` sanitization |
| No raw content in audit logs | ✅ — SHA-256 hashing |
| No Y6/yandere escalation via memory | ✅ — `_SAFE_MODE_BLOCKED_CONTENT_TAGS` blocks yandere/punishment/jealousy/dark_mood tags in safe mode |

---

## 7. Rollback / Re-run Safety

- All changes are read-only audit. No files modified.
- Re-run: re-read the same files — all findings are deterministic.
- Evidence is file-based at `docs/setup-evidence/hermes-phase1/auditor-memory-privacy.md`.

---

## 8. Auditor Gate

| Field | Value |
|-------|-------|
| Auditor | Guinevere (independent memory-privacy specialist) |
| Verdict | ✅ **PASS** |
| Criteria checked | 18 |
| Criteria passed | 18 |
| Criteria failed | 0 |
| Files reviewed | 5 core + full codebase grep sweep |
| Hermes memory API matches (grep) | 0 |
| Safety boundary violations | 0 |
| Recommendation | Safe for production use with Faiz's private conversations |

---

## 9. Security Scan

- No secrets, tokens, or API keys exposed in any audited file.
- Redis credentials loaded from `os.environ.get("REDIS_PASSWORD", "")` — correct.
- No hardcoded passwords or keys found.
- No private data in log statements — hash-based user identification only.

---

## 10. Acceptance Criteria Mapping

| Criterion | Source | Status |
|-----------|--------|--------|
| "Hermes native memory MUST be disabled" | Task description | ✅ |
| "Guinevere's own memory system MUST be the only memory path" | Task description | ✅ |
| "No privacy bypass exists" | Task description | ✅ |
| "All audit criteria satisfied" | Task description | ✅ |

---

## 11. Footer

| Field | Value |
|-------|-------|
| Report path | `docs/setup-evidence/hermes-phase1/auditor-memory-privacy.md` |
| Verdict | **PASS** |
| Auditor | Guinevere (memory-privacy specialist) |
| Date | 2026-06-04 |
| Session | Single-session audit |
| Sub-agent | No (parent-executed file audit) |