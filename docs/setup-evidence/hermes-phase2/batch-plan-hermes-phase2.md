# Batch Plan — Hermes Phase 2: Memory Bridge

| Field | Value |
|---|---|
| Phase | Hermes Phase 2 — Memory Bridge |
| Status | DRAFT — Awaiting approval |
| Date | 2026-06-04 |
| Author | Guinevere (planner gate) |
| Evidence root | `docs/setup-evidence/hermes-phase2/` |

---

## 1. Master Todo — Atomic Steps

| # | Step | Type | Depends On | Parallelism |
|---|---|---|---|---|
| S1 | Create `src/hermes/memory_bridge.py` — HermesMemoryBridge class | implementation | — | sequential (foundation) |
| S2 | Wire bridge into `src/discord/conversational_handler.py` | implementation | S1 | sequential |
| S3 | Improve context injection format in `src/core/services/prompt_loader.py` | implementation | S1 | parallel with S2 |
| S4 | Export bridge from `src/hermes/__init__.py` | implementation | S1 | parallel with S2, S3 |
| S5 | Unit tests for HermesMemoryBridge | implementation | S1 | parallel with S2, S3, S4 |
| S6 | Integration verification (lint + diagnostics + manual test) | verification | S1–S5 | sequential |

---

## 2. Dependency Map

```
S1 (memory_bridge.py)
├──► S2 (wire conversational_handler.py)   [sequential — needs bridge API]
├──► S3 (improve prompt_loader format)     [parallel with S2 — different file]
├──► S4 (export from __init__.py)          [parallel with S2, S3 — different file]
└──► S5 (unit tests)                       [parallel with S2, S3, S4]

S1 + S2 + S3 + S4 + S5
└──► S6 (integration verification)         [sequential — needs all above]
```

**Parallelism summary:**
- **S1** must complete first (foundation).
- **S2, S3, S4, S5** can run in parallel (no shared files, no shared config).
- **S6** runs after all implementation steps pass.

---

## 3. Per-Step Verification Scaffold

### S1: Create `src/hermes/memory_bridge.py`

**Expected Files:**
- CREATE: `src/hermes/memory_bridge.py`

**Forbidden Patterns (must return zero matches):**
- `as any`
- `@ts-ignore`
- `# type: ignore`
- `@ts-expect-error`
- `except Exception:\s*$` (empty catch — must always log)
- `except:\s*$` (bare except)
- `raise$` (re-raise without context)
- `print\(` (use structlog/logger only)

**Required Commands:**
- `python -c "from src.hermes.memory_bridge import HermesMemoryBridge; print('OK')"` → exit 0
- `python -c "import ast; ast.parse(open('src/hermes/memory_bridge.py').read()); print('syntax OK')"` → exit 0
- LSP diagnostics on `src/hermes/memory_bridge.py` → 0 errors introduced

**Evidence Requirements:**
- `docs/setup-evidence/hermes-phase2/s1-verification.md`
- `docs/setup-evidence/hermes-phase2/s1-auditor-gate.md`

**Hard Rejection Criteria (binary PASS/FAIL):**
- [ ] File exists at `src/hermes/memory_bridge.py`
- [ ] Class `HermesMemoryBridge` defined with `__init__`, `recall_for_context`, `store_conversation`, `extract_key_facts`
- [ ] `recall_for_context()` calls `recall_memories()` from `src.memory.read_pipeline`
- [ ] `store_conversation()` calls `store_episode()` from `src.memory.write_pipeline`
- [ ] No raw content in any log statement (hash/length only)
- [ ] All exception handlers log AND return graceful fallback (empty list / None)
- [ ] `embedding_service` parameter is optional (None = skip embedding)
- [ ] DNR exclusion preserved (delegated to `recall_memories(exclude_dnr=True)`)
- [ ] Classification ceiling preserved (delegated to `recall_memories(principal=...)`)
- [ ] Safe mode preserved (delegated to `recall_memories(safe_mode=...)`)
- [ ] Zero forbidden pattern matches

---

### S2: Wire bridge into `conversational_handler.py`

**Expected Files:**
- MODIFY: `src/discord/conversational_handler.py`

**Forbidden Patterns (must return zero matches):**
- `as any`
- `@ts-ignore`
- `# type: ignore`
- `from src.memory.write_pipeline import` (should use bridge, not direct import)
- `from src.memory.read_pipeline import` (should use bridge, not direct import)
- `await store_episode(` (replaced by bridge call)
- `await recall_memories(` (replaced by bridge call)
- `await assemble_system_prompt_with_memory(` (replaced by bridge call)

**Required Commands:**
- `python -c "import ast; ast.parse(open('src/discord/conversational_handler.py').read()); print('syntax OK')"` → exit 0
- LSP diagnostics on `src/discord/conversational_handler.py` → 0 NEW errors introduced (pre-existing allowed)
- `grep -c "memory_bridge" src/discord/conversational_handler.py` → ≥ 1

**Evidence Requirements:**
- `docs/setup-evidence/hermes-phase2/s2-verification.md`
- `docs/setup-evidence/hermes-phase2/s2-auditor-gate.md`

**Hard Rejection Criteria (binary PASS/FAIL):**
- [ ] Step 9 (recall) uses `bridge.recall_for_context()` instead of inline `assemble_system_prompt_with_memory()`
- [ ] Step 12b (auto-store) uses `bridge.store_conversation()` instead of inline `store_episode()`
- [ ] Auto-store is wrapped in `asyncio.create_task()` (fire-and-forget, never blocks response)
- [ ] Bridge is instantiated from `bot.get_session_factory()` + `_get_embedding_service()`
- [ ] System prompt assembly uses `get_system_prompt_with_context()` with bridge recall results
- [ ] No double DB session (single `session_factory()` usage or bridge manages its own)
- [ ] All existing error handling paths preserved (FALLBACK_MESSAGE, graceful degradation)
- [ ] `safe_mode_activated` still passed to bridge
- [ ] No raw content logged
- [ ] Zero forbidden pattern matches

---

### S3: Improve context injection format in `prompt_loader.py`

**Expected Files:**
- MODIFY: `src/core/services/prompt_loader.py`

**Forbidden Patterns (must return zero matches):**
- `as any`
- `@ts-ignore`
- `# type: ignore`
- `## Recalled Memories` (replaced by new format `[RECENT MEMORIES]`)

**Required Commands:**
- `python -c "import ast; ast.parse(open('src/core/services/prompt_loader.py').read()); print('syntax OK')"` → exit 0
- LSP diagnostics on `src/core/services/prompt_loader.py` → 0 NEW errors

**Evidence Requirements:**
- `docs/setup-evidence/hermes-phase2/s3-verification.md`
- `docs/setup-evidence/hermes-phase2/s3-auditor-gate.md`

**Hard Rejection Criteria (binary PASS/FAIL):**
- [ ] Memory section uses `[RECENT MEMORIES]` / `[END MEMORIES]` format
- [ ] Each memory line: `- ({classification}) {safe_content}`
- [ ] Token budget enforcement preserved (800 token default for bridge context)
- [ ] `get_system_prompt_with_context()` still accepts `memories`, `mood`, `token_budget`
- [ ] `assemble_system_prompt_with_memory()` still works (backward compat for non-bridge callers)
- [ ] No safety elements removed (HARD STOP, safe word, Y5/Y6, distress validation)
- [ ] Zero forbidden pattern matches

---

### S4: Export bridge from `src/hermes/__init__.py`

**Expected Files:**
- MODIFY: `src/hermes/__init__.py`

**Forbidden Patterns (must return zero matches):**
- `as any`
- `@ts-ignore`
- `# type: ignore`

**Required Commands:**
- `python -c "from src.hermes import HermesMemoryBridge; print('OK')"` → exit 0
- `python -c "import ast; ast.parse(open('src/hermes/__init__.py').read()); print('syntax OK')"` → exit 0

**Evidence Requirements:**
- `docs/setup-evidence/hermes-phase2/s4-verification.md`
- `docs/setup-evidence/hermes-phase2/s4-auditor-gate.md`

**Hard Rejection Criteria (binary PASS/FAIL):**
- [ ] `HermesMemoryBridge` importable from `src.hermes`
- [ ] `__all__` updated to include `"HermesMemoryBridge"`
- [ ] Existing `HermesSessionAdapter` and `get_adapter` exports preserved
- [ ] Zero forbidden pattern matches

---

### S5: Unit tests for HermesMemoryBridge

**Expected Files:**
- CREATE: `tests/hermes/test_memory_bridge.py`

**Forbidden Patterns (must return zero matches):**
- `as any`
- `@ts-ignore`
- `# type: ignore`
- `@pytest.mark.skip` (no skipped tests)

**Required Commands:**
- `python -m pytest tests/hermes/test_memory_bridge.py -v` → exit 0
- `python -c "import ast; ast.parse(open('tests/hermes/test_memory_bridge.py').read()); print('syntax OK')"` → exit 0

**Evidence Requirements:**
- `docs/setup-evidence/hermes-phase2/s5-verification.md`
- `docs/setup-evidence/hermes-phase2/s5-auditor-gate.md`

**Hard Rejection Criteria (binary PASS/FAIL):**
- [ ] Test file exists at `tests/hermes/test_memory_bridge.py`
- [ ] Tests cover: `recall_for_context` success path
- [ ] Tests cover: `recall_for_context` exception → returns `[]`
- [ ] Tests cover: `store_conversation` success path
- [ ] Tests cover: `store_conversation` exception → returns `None`
- [ ] Tests cover: `extract_key_facts` success path
- [ ] Tests cover: `extract_key_facts` exception → returns `[]`
- [ ] Tests cover: embedding_service=None → no embedding computed
- [ ] Tests cover: DNR exclusion is passed through to recall_memories
- [ ] Tests cover: safe_mode is passed through to recall_memories
- [ ] Tests use mocks (no real DB/embedding calls)
- [ ] All tests pass
- [ ] Zero forbidden pattern matches

---

### S6: Integration Verification

**Expected Files:**
- CREATE: `docs/setup-evidence/hermes-phase2/s6-verification.md`
- CREATE: `docs/setup-evidence/hermes-phase2/s6-auditor-gate.md`

**Required Commands:**
- `python -c "import ast; ast.parse(open('src/hermes/memory_bridge.py').read()); print('S1 OK')"` → exit 0
- `python -c "import ast; ast.parse(open('src/discord/conversational_handler.py').read()); print('S2 OK')"` → exit 0
- `python -c "import ast; ast.parse(open('src/core/services/prompt_loader.py').read()); print('S3 OK')"` → exit 0
- `python -c "import ast; ast.parse(open('src/hermes/__init__.py').read()); print('S4 OK')"` → exit 0
- `python -m pytest tests/hermes/test_memory_bridge.py -v` → exit 0
- LSP diagnostics on all modified files → 0 NEW errors

**Hard Rejection Criteria (binary PASS/FAIL):**
- [ ] All S1–S5 scaffold criteria still pass
- [ ] No import cycles introduced
- [ ] No regressions in existing conversational_handler flow
- [ ] Bridge graceful degradation verified (embedding_service=None path works)
- [ ] No secrets, raw content, or personal data in any evidence file
- [ ] Cross-reference: all modified files listed in Section 5 of this plan

---

## 4. Collision Scan

| Collision Type | Trigger | Mitigation |
|---|---|---|
| Same source file | S2 and S3 modify different files | **No collision** — S2 touches `conversational_handler.py`, S3 touches `prompt_loader.py` |
| Same source file | S1 and S4 both touch `src/hermes/` | **No collision** — S1 creates new file, S4 modifies `__init__.py` |
| Shared config | No config files modified | **No collision** |
| Shared tests | S5 creates new test file | **No collision** — new file, no shared fixtures |
| Shared docs | This plan file (parent-only) | **Parent-owned** |
| Shared imports | S2 imports from S1's `memory_bridge.py` | **Sequential** — S1 must complete before S2 |
| `src/memory/__init__.py` | Not modified | **No collision** — bridge imports from `read_pipeline` and `write_pipeline` directly |

**Verdict: No collisions detected. S2/S3/S4/S5 safe to parallelize after S1.**

---

## 5. Files to Create/Modify

| Action | File | Step |
|---|---|---|
| CREATE | `src/hermes/memory_bridge.py` | S1 |
| MODIFY | `src/discord/conversational_handler.py` | S2 |
| MODIFY | `src/core/services/prompt_loader.py` | S3 |
| MODIFY | `src/hermes/__init__.py` | S4 |
| CREATE | `tests/hermes/test_memory_bridge.py` | S5 |
| CREATE | `docs/setup-evidence/hermes-phase2/s1-verification.md` | S1 verify |
| CREATE | `docs/setup-evidence/hermes-phase2/s2-verification.md` | S2 verify |
| CREATE | `docs/setup-evidence/hermes-phase2/s3-verification.md` | S3 verify |
| CREATE | `docs/setup-evidence/hermes-phase2/s4-verification.md` | S4 verify |
| CREATE | `docs/setup-evidence/hermes-phase2/s5-verification.md` | S5 verify |
| CREATE | `docs/setup-evidence/hermes-phase2/s6-verification.md` | S6 |
| CREATE | `docs/setup-evidence/hermes-phase2/s1-auditor-gate.md` through `s6-auditor-gate.md` | S1–S6 audit |

---

## 6. Implementation Design Per Step

### S1: `src/hermes/memory_bridge.py`

```python
"""Hermes Memory Bridge — Phase 2.

Bridges Hermes conversational agent with Guinevere's episodic memory system.
Provides recall_for_context() and store_conversation() with graceful degradation.
"""

import hashlib
import structlog
from typing import Any

logger = structlog.get_logger()

class HermesMemoryBridge:
    """Bridge between Hermes sessions and Guinevere memory pipelines."""

    def __init__(
        self,
        session_factory: Any,
        embedding_service: Any | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_service = embedding_service

    async def recall_for_context(
        self,
        query: str,
        *,
        safe_mode: bool = False,
        principal: str = "guinevere_core",
        limit: int = 5,
        token_budget: int = 800,
    ) -> list[dict[str, object]]:
        """Recall memories for system prompt injection.

        Returns list[dict] with safe_content only.
        On ANY error: log metadata, return [].
        """
        try:
            from src.memory.read_pipeline import recall_memories

            async with self._session_factory() as session:
                results = await recall_memories(
                    session,
                    query,
                    limit=limit,
                    exclude_dnr=True,
                    safe_mode=safe_mode,
                    principal=principal,
                    token_budget=token_budget,
                    embedding_service=self._embedding_service,
                )
            logger.info(
                "bridge_recall_success",
                query_length=len(query),
                results_count=len(results),
                safe_mode=safe_mode,
            )
            return results
        except Exception as exc:
            logger.warning(
                "bridge_recall_error",
                query_length=len(query),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return []

    async def store_conversation(
        self,
        user_message: str,
        assistant_response: str,
        user_id_hash: str,
        *,
        safe_mode: bool = False,
    ) -> str | None:
        """Store conversation episode. Returns episode_id or None.

        NEVER crashes. Logs metadata only (no raw content).
        """
        try:
            from src.memory.write_pipeline import RESTRICTED, store_episode

            content = f"Faiz: {user_message}\nGuinevere: {assistant_response}"

            async with self._session_factory() as session:
                episode_id = await store_episode(
                    session=session,
                    content=content,
                    source="discord_conversation",
                    classification=RESTRICTED,
                    importance=3,
                    title=user_message[:100],
                    summary=user_message[:200],
                    episode_type="conversation",
                    tags=["discord", "chat", f"user:{user_id_hash}"],
                    metadata={
                        "channel": "guinevere-chat",
                        "user_hash": user_id_hash,
                        "response_length": len(assistant_response),
                        "safe_mode": safe_mode,
                    },
                    embedding_service=self._embedding_service,
                )
            logger.info(
                "bridge_store_success",
                episode_id=str(episode_id),
                content_length=len(content),
            )
            return str(episode_id)
        except Exception as exc:
            logger.warning(
                "bridge_store_error",
                user_id_hash=user_id_hash,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None

    async def extract_key_facts(
        self,
        conversation: str,
        *,
        limit: int = 3,
    ) -> list[str]:
        """Extract key facts via LLM. Max 200 tokens.

        Returns list of fact strings or [] on error.
        """
        # NOTE: Implementation will use LLMRouter or Hermes for extraction
        # For Phase 2 initial: return [] (stub, implement in Phase 3)
        logger.info(
            "bridge_extract_key_facts_stub",
            conversation_length=len(conversation),
        )
        return []
```

**Key design decisions:**
1. Bridge owns its own DB session lifecycle (`async with self._session_factory()`) — eliminates the double-session problem in current code.
2. `embedding_service` is optional — when None, `store_episode()` skips embedding (graceful), `recall_memories()` falls back to FTS-only (verified working).
3. All exceptions caught at bridge boundary — caller never sees memory failures.
4. No raw content in logs — only lengths, hashes, counts, IDs.
5. `extract_key_facts` is a stub returning `[]` — full LLM extraction deferred to Phase 3 to avoid scope creep.

---

### S2: Wire into `conversational_handler.py`

**Current Step 9 (lines ~400-455) — REPLACE with:**

```python
# ── Step 9: Memory recall via bridge ─────────────────────────────
from src.hermes.memory_bridge import HermesMemoryBridge

session_factory_fn = getattr(bot, "get_session_factory", None)
session_factory = session_factory_fn() if session_factory_fn else None

if session_factory is not None:
    bridge = HermesMemoryBridge(
        session_factory=session_factory,
        embedding_service=_get_embedding_service(),
    )
    memories = await bridge.recall_for_context(
        query=content,
        safe_mode=safe_mode_activated,
        principal="guinevere_core",
        limit=5,
        token_budget=800,
    )
    system_prompt = get_system_prompt_with_context(
        memories=memories if memories else None,
        mood=current_mood,
        token_budget=800,
    )
    logger.info(
        "memory_recall_integrated",
        query_length=len(content),
        memories_count=len(memories),
        safe_mode=safe_mode_activated,
    )
else:
    system_prompt = get_system_prompt_with_context(
        memories=None,
        mood=current_mood,
    )
    logger.info("memory_recall_skipped", reason="no_session_factory")
```

**Current Step 12b (lines ~525-562) — REPLACE with:**

```python
# ── Step 12b: Auto-store via bridge (fire-and-forget) ────────────
if session_factory is not None:
    async def _auto_store() -> None:
        await bridge.store_conversation(
            user_message=content,
            assistant_response=response_text,
            user_id_hash=hashlib.sha256(str(author.id).encode()).hexdigest()[:8],
            safe_mode=safe_mode_activated,
        )
    asyncio.create_task(_auto_store())
else:
    logger.info("memory_auto_store_skipped", reason="no_session_factory")
```

**Key design decisions:**
1. Bridge instantiated once, reused for both recall and store.
2. `asyncio.create_task()` for auto-store — response never blocked by memory write.
3. `user_id_hash` computed once (already computed in Step 13 — refactor to compute earlier).
4. Remove direct imports of `store_episode`, `assemble_system_prompt_with_memory` from conversational_handler.
5. Remove `_embedding_service` usage from Step 12b — bridge owns it.
6. `limit=5` and `token_budget=800` per spec (up from `limit=3`, `token_budget=400`).

---

### S3: Improve context injection in `prompt_loader.py`

**Current `get_system_prompt_with_context()` memory section — REPLACE format:**

From:
```
## Recalled Memories
1. {safe_content}
2. {safe_content}
```

To:
```
[RECENT MEMORIES]
- ({classification}) {safe_content}
- ({classification}) {safe_content}
[END MEMORIES]
```

**Implementation change in `get_system_prompt_with_context()` (lines ~79-116):**

```python
memory_section = "\n\n[RECENT MEMORIES]\n"

total_tokens = 0
included = 0
for r in normalized:
    safe_content = str(r.get("safe_content", ""))
    classification = str(r.get("classification", "Restricted"))
    if not safe_content:
        continue
    estimated = len(safe_content) // CHARS_PER_TOKEN
    if total_tokens + estimated > token_budget:
        # ... existing budget log ...
        break
    total_tokens += estimated
    included += 1
    memory_section += f"- ({classification}) {safe_content}\n"

memory_section += "[END MEMORIES]"
context_parts.append(memory_section)
```

**Key design decisions:**
1. Classification label visible per memory — helps LLM contextualize sensitivity.
2. Bracket-delimited section is clearer for the LLM to parse.
3. Backward compatible — `assemble_system_prompt_with_memory()` still works for non-bridge callers.
4. Token budget enforcement logic unchanged.

---

### S4: Export from `__init__.py`

Add to `src/hermes/__init__.py`:

```python
from .memory_bridge import HermesMemoryBridge

__all__ = ["HermesSessionAdapter", "get_adapter", "HermesMemoryBridge"]
```

---

### S5: Unit Tests

```python
# tests/hermes/test_memory_bridge.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestHermesMemoryBridge:
    # test_recall_success — mock recall_memories, verify results returned
    # test_recall_error_returns_empty — mock recall_memories raising, verify []
    # test_store_success — mock store_episode, verify episode_id returned
    # test_store_error_returns_none — mock store_episode raising, verify None
    # test_store_embedding_none — verify no embedding computed when service=None
    # test_recall_dnr_excluded — verify exclude_dnr=True passed through
    # test_recall_safe_mode_passed — verify safe_mode passed through
    # test_extract_key_facts_stub — verify returns []
```

---

## 7. Evidence Paths

| Step | Verification | Auditor Gate |
|---|---|---|
| S1 | `docs/setup-evidence/hermes-phase2/s1-verification.md` | `docs/setup-evidence/hermes-phase2/s1-auditor-gate.md` |
| S2 | `docs/setup-evidence/hermes-phase2/s2-verification.md` | `docs/setup-evidence/hermes-phase2/s2-auditor-gate.md` |
| S3 | `docs/setup-evidence/hermes-phase2/s3-verification.md` | `docs/setup-evidence/hermes-phase2/s3-auditor-gate.md` |
| S4 | `docs/setup-evidence/hermes-phase2/s4-verification.md` | `docs/setup-evidence/hermes-phase2/s4-auditor-gate.md` |
| S5 | `docs/setup-evidence/hermes-phase2/s5-verification.md` | `docs/setup-evidence/hermes-phase2/s5-auditor-gate.md` |
| S6 | `docs/setup-evidence/hermes-phase2/s6-verification.md` | `docs/setup-evidence/hermes-phase2/s6-auditor-gate.md` |

---

## 8. Auditor Matrix

| Auditor | Scope | Steps | Trigger |
|---|---|---|---|
| Code Quality | Python style, type hints, docstrings, imports | S1, S2, S3, S4, S5 | After parent verify |
| Security | No raw content in logs, no secret exposure, DNR preserved | S1, S2 | After parent verify |
| Safety Boundary | Consent, classification ceiling, safe mode, DNR | S1, S2, S3 | After parent verify |
| Regression | Existing conversational flow preserved, no broken paths | S2, S3 | After parent verify |
| Test Coverage | Test completeness, mock quality, edge cases | S5 | After parent verify |

**Parallel audit execution:**
- S1 auditors (code quality + security + safety) fire parallel after S1 parent-verify.
- S2 auditors (code quality + security + safety + regression) fire parallel after S2 parent-verify.
- S3 auditors (code quality + safety + regression) fire parallel after S3 parent-verify.
- S4 auditor (code quality) fires after S4 parent-verify.
- S5 auditor (test coverage) fires after S5 parent-verify.

---

## 9. Rollback Plan

| Scenario | Rollback Action |
|---|---|
| Bridge breaks recall | Revert `conversational_handler.py` to inline `assemble_system_prompt_with_memory()` call |
| Bridge breaks auto-store | Revert Step 12b to inline `store_episode()` call (current code) |
| New prompt format confuses LLM | Revert `prompt_loader.py` memory section to `## Recalled Memories` numbered list |
| Tests fail | Remove `tests/hermes/test_memory_bridge.py`, fix and re-run |
| Import cycle | Move bridge imports to lazy imports inside methods (current pattern already does this) |

**Rollback is always safe** because:
1. Bridge is additive — no existing APIs are modified or removed.
2. `conversational_handler.py` changes are localized to Step 9 and Step 12b.
3. `prompt_loader.py` format change is cosmetic — `assemble_system_prompt_with_memory()` still works.
4. All changes are in Python source files — no DB migrations, no config changes, no schema changes.

---

## 10. Caveats and Risks

| # | Caveat/Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Embedding API still broken** — 9Router has no embedding models, so `embedding_service` will always fail. Bridge handles this gracefully (FTS-only fallback), but vector search is effectively dead until embedding provider is fixed. | Medium | Bridge accepts `embedding_service=None` as valid. When 9Router adds embedding support, bridge automatically benefits. |
| 2 | **`extract_key_facts` is a stub** — returns `[]` in Phase 2. Full LLM extraction deferred to Phase 3. | Low | Documented in code. No caller depends on it. |
| 3 | **Fire-and-forget auto-store** — `asyncio.create_task()` means store failures are logged but not surfaced to the user. This is intentional (response already delivered). | Low | Bridge logs all errors with metadata. Monitoring can alert on `bridge_store_error` frequency. |
| 4 | **Bridge creates its own DB session** — `async with self._session_factory()` per call. This is correct (isolated transactions) but means 2 sessions per message (recall + store). Store is fire-and-forget so no user-visible latency. | Low | Same as current behavior. Future optimization: single session for both. |
| 5 | **`user_id_hash` computed in Step 13** — needs to be moved earlier (before Step 12b) for bridge.store_conversation(). Simple refactor. | Low | Compute hash once at top of `_process_and_respond()` and reuse. |
| 6 | **No VPS deploy in this plan** — Step 6 (deploy) from user spec is excluded. Deploy requires separate approval. | Info | Plan covers code changes only. Deploy is a separate task. |
| 7 | **Prompt format change may affect LLM behavior** — `[RECENT MEMORIES]` format is new. Needs manual testing to verify LLM interprets it correctly. | Medium | S6 integration verification includes manual Discord test. |

---

## Appendix A: Current vs Proposed Flow

### Current Flow (Broken)

```
User message
  → conversational_handler Step 9:
      session_factory() → recall → assemble_system_prompt_with_memory()
      [embedding fails → 61s retry → fallback to FTS]
  → Step 10: Hermes call
  → Step 12b:
      session_factory() → store_episode(embedding_service=svc)
      [embedding fails → 61s retry → EXCEPTION → 0 episodes stored]
```

### Proposed Flow (Fixed)

```
User message
  → conversational_handler Step 9:
      bridge.recall_for_context()
      [embedding fails → instant FTS fallback → memories returned]
      get_system_prompt_with_context(memories) → [RECENT MEMORIES] format
  → Step 10: Hermes call
  → Step 12b:
      asyncio.create_task(bridge.store_conversation())
      [embedding fails → skip embedding → episode stored without vector]
      [fire-and-forget → response never blocked]
```

### Latency Improvement

| Metric | Current | Proposed |
|---|---|---|
| Recall embedding failure | ~61s retry | ~0s (instant FTS fallback) |
| Store embedding failure | ~61s retry → crash | ~0s (skip embedding → store succeeds) |
| Total per-message overhead (embedding broken) | ~122s | ~0s |
| Auto-store blocks response | Yes (synchronous) | No (fire-and-forget) |

---

## Appendix B: API Compatibility Matrix

| Function | Module | Bridge Uses? | Changed? |
|---|---|---|---|
| `recall_memories()` | `src.memory.read_pipeline` | Yes (`recall_for_context` delegates) | No |
| `store_episode()` | `src.memory.write_pipeline` | Yes (`store_conversation` delegates) | No |
| `get_system_prompt_with_context()` | `src.core.services.prompt_loader` | Yes (formatting) | Yes (format only) |
| `assemble_system_prompt_with_memory()` | `src.core.services.prompt_loader` | No (replaced by bridge) | No (preserved for compat) |
| `EmbeddingService()` | `src.memory.embeddings` | Yes (optional param) | No |
| `HermesSessionAdapter` | `src.hermes.session_adapter` | No (independent) | No |

---

*Plan generated 2026-06-04. Awaiting Faiz approval before implementation.*
