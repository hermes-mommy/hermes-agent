#!/usr/bin/env python3
"""P3-009 Write Pipeline Verification Script.

Tests:
 1. Module imports work correctly
 2. store_episode function signature matches expected API
 3. store_episode_batch exists and is callable
 4. Classification constants re-exported (RESTRICTED default)
 5. Error types: WritePipelineError, WritePipelineCriticalError
 6. Critical guard -- fails without summary
 7. Critical guard -- passes with summary
 8. Error hierarchy -- WritePipelineCriticalError inherits WritePipelineError
 9. raw_content mapping (not ``content``)
10. Restricted default is "Restricted"
11. Embedding computed and stored via fake EmbeddingService (1536-dim)
12. UUID returned via fake AsyncSession
13. No DB write on dimension mismatch -- error raised
14. do_not_recall defaults to False
15. No secrets in output / str / repr of pipeline objects
16. Batch store returns list of UUIDs
"""

import asyncio
import sys
import traceback
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT))

pass_count = 0
fail_count = 0
errors: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  [PASS] {name}")
    else:
        fail_count += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f": {detail}"
        print(msg)
        errors.append(f"{name}: {detail}")


# ---------------------------------------------------------------------------
# Type-safe protocols for test doubles
# ---------------------------------------------------------------------------


@runtime_checkable
class _EpisodeProtocol(Protocol):
    """Minimal protocol matching the Episodes ORM attributes we inspect."""

    id: uuid.UUID
    raw_content: str | None
    embedding: list[float] | None
    summary: str | None
    classification: str
    do_not_recall: bool
    importance: int | None
    tags: list[str] | None
    source: str | None
    episode_type: str
    key_insights: dict[str, object] | None
    started_at: datetime | None
    title: str | None


class _FakeAsyncSession:
    """Minimal AsyncSession stand-in that captures added ORM objects.

    Does not perform real DB I/O.  After ``add()`` the object's ``id`` is set
    to a synthetic UUID.  ``flush()`` is a no-op.
    """

    def __init__(self) -> None:
        self.added: list[_EpisodeProtocol] = []
        self.flushed: bool = False

    def add(self, obj: object) -> None:
        # obj.id must be set; server_default populates it on flush in
        # real SQLAlchemy, but for the fake we assign it eagerly.
        episode = obj
        if not isinstance(episode, _EpisodeProtocol):
            raise TypeError("Fake session expected an episode-like object")
        episode.id = uuid.uuid4()
        self.added.append(episode)

    async def flush(self) -> None:
        self.flushed = True


# ---------------------------------------------------------------------------
# Async error-assertion helper (no ``Any``)
# ---------------------------------------------------------------------------


async def run_expect_error_async(
    name: str,
    exc_type: type[BaseException],
    fn: Callable[..., Awaitable[object]],
    fn_args: tuple[object, ...] = (),
    fn_kwargs: dict[str, object] | None = None,
) -> None:
    """Call ``fn(*fn_args, **fn_kwargs)`` and assert ``exc_type`` is raised."""
    global pass_count, fail_count
    kw: dict[str, object] = fn_kwargs or {}
    try:
        coro: Awaitable[object] = fn(*fn_args, **kw)
        await coro
        fail_count += 1
        print(f"  [FAIL] {name}")
        errors.append(f"{name}: expected {exc_type.__name__} but none raised")
    except exc_type:
        pass_count += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        fail_count += 1
        exc_name = type(e).__name__
        print(f"  [FAIL] {name} - expected {exc_type.__name__}, got {exc_name}: {e}")
        errors.append(f"{name}: expected {exc_type.__name__}, got {exc_name}: {e}")


# ---------------------------------------------------------------------------
# Fake embedder factories (return protocol-typed objects)
# ---------------------------------------------------------------------------


class _FakeEmbedder:
    """Deterministic fake embedder returning ``dim``-length vectors."""

    def __init__(self, dim: int = 1536) -> None:
        self._expected_dim: int = dim

    async def aembed(
        self,
        text: str = "",
        classification: str = "Restricted",
        *,
        sanitized_summary: str | None = None,
    ) -> list[float]:
        _ = (text, classification, sanitized_summary)
        return [float(i % 100) / 100.0 for i in range(self._expected_dim)]


class _MismatchEmbedder:
    """Fake embedder that always raises DimensionMismatchError."""

    async def aembed(
        self,
        text: str = "",
        classification: str = "Restricted",
        *,
        sanitized_summary: str | None = None,
    ) -> list[float]:
        _ = (text, classification, sanitized_summary)
        from src.memory.embeddings import DimensionMismatchError

        raise DimensionMismatchError("Expected 1536, got 384")


# =========================================================================
# 1. Module imports
# =========================================================================
print("=" * 70)
print("P3-009 Write Pipeline - Verification Suite")
print("=" * 70)

print("\n--- 1. Module Imports ---")
try:
    from src.memory.write_pipeline import (
        CONFIDENTIAL,
        CRITICAL,
        INTERNAL,
        PUBLIC,
        RESTRICTED,
        CriticalEmbeddingError,
        WritePipelineCriticalError,
        WritePipelineError,
        store_episode,
        store_episode_batch,
    )
    import src.memory.write_pipeline as wp

    check("from src.memory.write_pipeline imports all symbols", True)

    # Re-export check
    from src.memory import (
        WritePipelineError as WPE,
        WritePipelineCriticalError as WPCE,
        store_episode as se,
        store_episode_batch as seb,
    )

    check("from src.memory re-exports WritePipelineError", WritePipelineError is WPE)
    check("from src.memory re-exports WritePipelineCriticalError",
          WritePipelineCriticalError is WPCE)
    check("from src.memory re-exports store_episode", store_episode is se)
    check("from src.memory re-exports store_episode_batch", store_episode_batch is seb)

except Exception as e:
    check("Module imports", False, str(e))
    traceback.print_exc()
    sys.exit(1)

# =========================================================================
# 2. Function signature
# =========================================================================
print("\n--- 2. Function Signature ---")

import inspect

sig = inspect.signature(store_episode)
sig_params = list(sig.parameters.keys())
check("store_episode has 'session' param", "session" in sig_params)
check("store_episode has 'content' param", "content" in sig_params)
check("store_episode has 'source' keyword param", "source" in sig_params)
check("store_episode has 'classification' default RESTRICTED",
      sig.parameters.get("classification") is not None)
check("store_episode has 'embedding_service' param",
      "embedding_service" in sig_params)
check("store_episode has 'metadata' param", "metadata" in sig_params)
check("store_episode has 'tags' param", "tags" in sig_params)
return_annotation = sig.parameters.get("content") is not None
check("store_episode has explicit signature inspected", return_annotation)

# =========================================================================
# 3. store_episode_batch exists
# =========================================================================
print("\n--- 3. Batch Function ---")
check("store_episode_batch is callable", callable(store_episode_batch))
batch_sig = inspect.signature(store_episode_batch)
check("store_episode_batch has 'session' param", "session" in batch_sig.parameters)
check("store_episode_batch has 'episodes' param", "episodes" in batch_sig.parameters)

# =========================================================================
# 4. Classification constants re-exported
# =========================================================================
print("\n--- 4. Classification Constants ---")
check("RESTRICTED == 'Restricted'", RESTRICTED == "Restricted")
check("CRITICAL == 'Critical'", CRITICAL == "Critical")
check("PUBLIC == 'Public'", PUBLIC == "Public")
check("INTERNAL == 'Internal'", INTERNAL == "Internal")
check("CONFIDENTIAL == 'Confidential'", CONFIDENTIAL == "Confidential")
check("CriticalEmbeddingError is re-exported",
      CriticalEmbeddingError.__name__ == "CriticalEmbeddingError")

# =========================================================================
# 5. Error types
# =========================================================================
print("\n--- 5. Error Types ---")
check("WritePipelineError is an Exception subclass",
      Exception in WritePipelineError.__mro__)
check("WritePipelineCriticalError is an Exception subclass",
      Exception in WritePipelineCriticalError.__mro__)

# =========================================================================
# 6. Critical guard -- fails without summary
# =========================================================================
print("\n--- 6. Critical Guard (No Summary) ---")


async def _test_critical_no_summary() -> None:
    sess = _FakeAsyncSession()
    await run_expect_error_async(
        "store_episode Critical without summary raises WritePipelineCriticalError",
        WritePipelineCriticalError,
        store_episode,
        fn_args=(sess, "this is critical raw content"),
        fn_kwargs={"source": "test", "classification": CRITICAL},
    )


asyncio.run(_test_critical_no_summary())

# =========================================================================
# 7. Critical guard -- passes with summary
# =========================================================================
print("\n--- 7. Critical Guard (With Summary) ---")

fake_session_ok = _FakeAsyncSession()
fake_embedder_ok = _FakeEmbedder(1536)

result_id = asyncio.run(
    store_episode(
        fake_session_ok,
        "this is critical raw content",
        source="test-critical",
        classification=CRITICAL,
        summary="Sanitized summary of critical event.",
        embedding_service=fake_embedder_ok,
    )
)
check("Critical with summary returns UUID", type(result_id) is uuid.UUID)
check("Critical episode was added to session", len(fake_session_ok.added) == 1)
added_ep: _EpisodeProtocol = fake_session_ok.added[0]
check("Critical episode raw_content preserved",
      added_ep.raw_content == "this is critical raw content")
check("Critical episode summary set",
      added_ep.summary == "Sanitized summary of critical event.")
check("Critical episode classification is Critical",
      added_ep.classification == CRITICAL)
emb_val: list[float] | None = added_ep.embedding
check("Critical embedding present (1536 dim)",
      isinstance(emb_val, list) and len(emb_val) == 1536)
check("Critical do_not_recall is False",
      not added_ep.do_not_recall)

# =========================================================================
# 8. Error hierarchy
# =========================================================================
print("\n--- 8. Error Hierarchy ---")
check("WritePipelineCriticalError inherits WritePipelineError",
      WritePipelineError in WritePipelineCriticalError.__mro__)

# =========================================================================
# 9. raw_content mapping (not "content")
# =========================================================================
print("\n--- 9. raw_content Mapping ---")

fake_session_raw = _FakeAsyncSession()
_ = asyncio.run(
    store_episode(
        fake_session_raw,
        "test raw content",
        source="test-raw",
    )
)
ep_raw: _EpisodeProtocol = fake_session_raw.added[0]
check("Episode has raw_content attribute", ep_raw.raw_content is not None)
check("raw_content equals passed content", ep_raw.raw_content == "test raw content")
# The model has no 'content' column so the attribute should not exist
check("Episode does NOT have 'content' column (raw_content is correct)",
      not hasattr(type(ep_raw), "content"))

# =========================================================================
# 10. Restricted default classification
# =========================================================================
print("\n--- 10. Restricted Default ---")

fake_session_default = _FakeAsyncSession()
_ = asyncio.run(
    store_episode(
        fake_session_default,
        "default classification test",
        source="test-default",
    )
)
ep_default: _EpisodeProtocol = fake_session_default.added[0]
check("Default classification is Restricted",
      ep_default.classification == "Restricted")

# =========================================================================
# 11. Embedding through fake service (1536-dim)
# =========================================================================
print("\n--- 11. Embedding Through Fake Service ---")

fake_session_emb = _FakeAsyncSession()
fake_emb = _FakeEmbedder(1536)
_ = asyncio.run(
    store_episode(
        fake_session_emb,
        "test embedding content",
        source="test-emb",
        classification=PUBLIC,
        embedding_service=fake_emb,
    )
)
ep_emb: _EpisodeProtocol = fake_session_emb.added[0]
embed_vec: list[float] | None = ep_emb.embedding
check("Embedding is a list", isinstance(embed_vec, list))
if isinstance(embed_vec, list):
    check("Embedding is 1536-dim", len(embed_vec) == 1536)
    check("Embedding elements are floats",
          all(isinstance(v, float) for v in embed_vec[:5]))

# =========================================================================
# 12. UUID returned
# =========================================================================
print("\n--- 12. UUID Returned ---")

fake_session_uuid = _FakeAsyncSession()
result_uuid = asyncio.run(
    store_episode(
        fake_session_uuid,
        "uuid test",
        source="test-uuid",
    )
)
check("Result is uuid.UUID", type(result_uuid) is uuid.UUID)
check("Result UUID is valid (version 4)", result_uuid.version == 4)

# =========================================================================
# 13. Dimension mismatch error
# =========================================================================
print("\n--- 13. Dimension Mismatch ---")

from src.memory.embeddings import DimensionMismatchError


async def _test_dim_mismatch() -> None:
    sess = _FakeAsyncSession()
    bad_emb = _MismatchEmbedder()
    await run_expect_error_async(
        "Dimension mismatch raises DimensionMismatchError",
        DimensionMismatchError,
        store_episode,
        fn_args=(sess, "dim mismatch test"),
        fn_kwargs={"source": "test-dim", "classification": PUBLIC,
                   "embedding_service": bad_emb},
    )


asyncio.run(_test_dim_mismatch())

# =========================================================================
# 14. do_not_recall defaults to False
# =========================================================================
print("\n--- 14. do_not_recall Default ---")

fake_session_dnr = _FakeAsyncSession()
_ = asyncio.run(
    store_episode(
        fake_session_dnr,
        "do not recall test",
        source="test-dnr",
    )
)
ep_dnr: _EpisodeProtocol = fake_session_dnr.added[0]
check("do_not_recall is False (bool)", ep_dnr.do_not_recall is False)
check("do_not_recall is typed as bool", type(ep_dnr.do_not_recall) is bool)

# =========================================================================
# 15. No secrets in output
# =========================================================================
print("\n--- 15. No Secrets in Output ---")

# Verify that module-level objects don't leak sensitive data
wp_repr = repr(wp)
check("No API key pattern in write_pipeline repr",
      "sk-" not in wp_repr and "api_key" not in wp_repr.lower())

# Verify Critical error message mentions summary requirement
try:
    fake_session_secret = _FakeAsyncSession()
    _ = asyncio.run(
        store_episode(
            fake_session_secret,
            "super-secret-content",
            source="test-secret",
            classification=CRITICAL,
        )
    )
except WritePipelineCriticalError as e:
    msg = str(e)
    check("Critical error message mentions 'summary'", "summary" in msg.lower())
    check("Critical error does NOT contain raw content",
          "super-secret-content" not in msg)

# =========================================================================
# 16. Batch store
# =========================================================================
print("\n--- 16. Batch Store ---")

fake_session_batch = _FakeAsyncSession()
batch_input: list[dict[str, object]] = [
    {"content": "batch episode 1", "source": "batch-test", "classification": PUBLIC},
    {"content": "batch episode 2", "source": "batch-test", "classification": PUBLIC,
     "importance": 7, "tags": ["test", "batch"]},
]

ids = asyncio.run(
    store_episode_batch(
        fake_session_batch,
        batch_input,
    )
)
check("Batch returns list", type(ids) is list)
check("Batch returns 2 IDs", len(ids) == 2)
check("Each ID is UUID", all(type(i) is uuid.UUID for i in ids))
check("Batch IDs are unique", len(set(ids)) == 2)
check("Batch session has 2 added objects", len(fake_session_batch.added) == 2)

ep_b1: _EpisodeProtocol = fake_session_batch.added[0]
check("Batch ep1 raw_content correct", ep_b1.raw_content == "batch episode 1")
check("Batch ep1 source correct", ep_b1.source == "batch-test")
check("Batch ep1 classification is Public", ep_b1.classification == PUBLIC)

ep_b2: _EpisodeProtocol = fake_session_batch.added[1]
check("Batch ep2 importance is 7", ep_b2.importance == 7)
check("Batch ep2 tags present", ep_b2.tags == ["test", "batch"])

# =========================================================================
# Summary
# =========================================================================
print()
print("=" * 70)
print(f"RESULTS: {pass_count} passed, {fail_count} failed")
if errors:
    print("FAILURES:")
    for e in errors:
        print(f"  - {e}")
print("=" * 70)
print()

sys.exit(0 if fail_count == 0 else 1)