#!/usr/bin/env python3
"""P3-005 Embedding Pipeline Verification Script.

Tests:
1. Module imports work correctly
2. Classification constants are accessible
3. Error hierarchy is correct
4. prepare_embedding_text privacy guards
5. EmbeddingService with mocked 1536-dim response
6. Dimension mismatch detection
7. Batch embedding
8. Convenience functions
9. Truncation at 8000 chars
10. No secrets in output / config repr

Does NOT make live API calls. Uses mocked httpx responses via unittest.mock.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Callable

import httpx

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


def make_mock_response(status: int = 200, dim: int = 1536, num_vectors: int = 1) -> httpx.Response:
    """Create a mocked httpx.Response with fake embedding vectors."""
    data: dict[str, object] = {
        "data": [
            {"embedding": [float(i % 100) / 100.0 for i in range(dim)], "index": idx}
            for idx in range(num_vectors)
        ],
        "model": "openai/text-embedding-3-small",
        "usage": {"total_tokens": 10},
    }
    return httpx.Response(status_code=status, json=data)


def make_mock_client(response: httpx.Response) -> httpx.Client:
    """Create an httpx.Client backed by MockTransport for deterministic tests."""

    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return response

    return httpx.Client(transport=httpx.MockTransport(handler))


def run_expect_error(
    name: str,
    exc_type: type[BaseException],
    fn: Callable[..., object],
    fn_args: tuple[object, ...],
    fn_kwargs: dict[str, object] | None = None,
) -> None:
    """Call fn(*fn_args, **fn_kwargs) and assert exc_type is raised."""
    global pass_count, fail_count
    kw = fn_kwargs or {}
    try:
        _ = fn(*fn_args, **kw)
        fail_count += 1
        print(f"  [FAIL] {name}")
        errors.append(f"{name}: expected {exc_type.__name__}")
    except exc_type:
        pass_count += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        fail_count += 1
        exc_name = type(e).__name__
        print(f"  [FAIL] {name} \u2014 expected {exc_type.__name__}, got {exc_name}: {e}")
        errors.append(f"{name}: expected {exc_type.__name__}, got {exc_name}: {e}")





print("=" * 70)
print("P3-005 Embedding Pipeline \u2014 Verification Suite")
print("=" * 70)

# =========================================================================
# 1. Module imports
# =========================================================================
print("\n--- 1. Module Imports ---")
try:
    from src.memory.embeddings import (
        CONFIDENTIAL,
        CRITICAL,
        INTERNAL,
        PUBLIC,
        RESTRICTED,
        CLASSIFICATION_ORDER,
        CriticalEmbeddingError,
        DimensionMismatchError,
        EmbeddingAPIError,
        EmbeddingConfigurationError,
        EmbeddingError,
        EmbeddingRateLimitError,
        EmbeddingServerError,
        RestrictedRedactionError,
        EmbeddingConfig,
        EmbeddingService,
        PreparedText,
        prepare_embedding_text,
    )
    import httpx

    check("from src.memory.embeddings imports all symbols", True)

    # Re-export check
    from src.memory import (
        EmbeddingService as ES,
        EmbeddingConfig as EC,
        EmbeddingError as EE,
    )

    check("from src.memory re-exports EmbeddingService", EmbeddingService is ES)
    check("from src.memory re-exports EmbeddingConfig", EmbeddingConfig is EC)
    check("from src.memory re-exports EmbeddingError", EmbeddingError is EE)

except Exception as e:
    check("Module imports", False, str(e))
    traceback.print_exc()
    sys.exit(1)

# =========================================================================
# 2. Classification constants
# =========================================================================
print("\n--- 2. Classification Constants ---")
check("PUBLIC == 'Public'", PUBLIC == "Public")
check("INTERNAL == 'Internal'", INTERNAL == "Internal")
check("RESTRICTED == 'Restricted'", RESTRICTED == "Restricted")
check("CONFIDENTIAL == 'Confidential'", CONFIDENTIAL == "Confidential")
check("CRITICAL == 'Critical'", CRITICAL == "Critical")
check("CLASSIFICATION_ORDER has 5 levels", len(CLASSIFICATION_ORDER) == 5)
check("CRITICAL is highest sensitivity (4)", CLASSIFICATION_ORDER[CRITICAL] == 4)

# =========================================================================
# 3. Error hierarchy
# =========================================================================
print("\n--- 3. Error Hierarchy ---")
check("EmbeddingError is Exception subclass", EmbeddingError in Exception.__subclasses__())
check("CriticalEmbeddingError inherits EmbeddingError",
      EmbeddingError in CriticalEmbeddingError.__mro__)
check("DimensionMismatchError inherits EmbeddingError",
      EmbeddingError in DimensionMismatchError.__mro__)
check("EmbeddingConfigurationError inherits EmbeddingError",
      EmbeddingError in EmbeddingConfigurationError.__mro__)
check("EmbeddingAPIError inherits EmbeddingError",
      EmbeddingError in EmbeddingAPIError.__mro__)
check("EmbeddingRateLimitError inherits EmbeddingError",
      EmbeddingError in EmbeddingRateLimitError.__mro__)
check("EmbeddingServerError inherits EmbeddingError",
      EmbeddingError in EmbeddingServerError.__mro__)
check("RestrictedRedactionError inherits EmbeddingError",
      EmbeddingError in RestrictedRedactionError.__mro__)

# =========================================================================
# 4. Privacy guards
# =========================================================================
print("\n--- 4. Privacy Guards (prepare_embedding_text) ---")

# 4a. Critical raw text rejection (fail closed)
run_expect_error(
    "Critical raw text rejected (fail closed)",
    CriticalEmbeddingError,
    prepare_embedding_text,
    ("This is a critical secret", CRITICAL),
)

# 4b. Critical with sanitized_summary
result = prepare_embedding_text(
    "This is a critical secret",
    CRITICAL,
    sanitized_summary="User had a difficult conversation.",
)
check("Critical with sanitized_summary returns PreparedText", type(result) is PreparedText)
check("Critical summary text equals provided summary",
      result.text == "User had a difficult conversation.")
check("Critical summary is_sanitized_summary=True", result.is_sanitized_summary is True)

# 4c. Critical with empty/whitespace sanitized_summary still raises
run_expect_error(
    "Critical with empty sanitized_summary still rejected",
    CriticalEmbeddingError,
    prepare_embedding_text,
    ("secret", CRITICAL),
    {"sanitized_summary": "   "},
)

# 4d. Restricted redaction of sensitive patterns
restricted_text = (
    "My email is user-test@example.com and my key is sk-proj-test-key-for-redaction-check"
)
result = prepare_embedding_text(restricted_text, RESTRICTED)
check("Restricted returns PreparedText", type(result) is PreparedText)
check("Email address redacted from Restricted text",
      "user-test@example.com" not in result.text)
check("API key redacted from Restricted text",
      "sk-proj-test-key-for-redaction-check" not in result.text)
check("Restricted redaction_applied is True", result.redaction_applied is True)

# 4e. Public — no redaction
result = prepare_embedding_text("Hello world, public info.", PUBLIC)
check("Public returns PreparedText", type(result) is PreparedText)
check("Public text unchanged", result.text == "Hello world, public info.")
check("Public redaction_applied is False", result.redaction_applied is False)

# 4f. Unknown classification raises ValueError
run_expect_error(
    "Unknown classification raises ValueError",
    ValueError,
    prepare_embedding_text,
    ("test", "UnknownLevel"),
)

# 4g. Confidential: same redaction as Restricted
conf_text = "Contact: user-2@company.com with token abc123def456ghi789jkl012mno345"
result = prepare_embedding_text(conf_text, CONFIDENTIAL)
check("Confidential email redacted", "user-2@company.com" not in result.text)
check("Confidential redaction_applied is True", result.redaction_applied is True)

# =========================================================================
# 5. EmbeddingService with mocked 1536-dim response
# =========================================================================
print("\n--- 5. EmbeddingService \u2014 Mocked 1536-dim Response ---")

os.environ["GUINEVERE_9ROUTER_API_KEY"] = "test-key-redacted"

config = EmbeddingConfig()

mock_resp_1536 = make_mock_response(200, 1536, 1)
mock_client = make_mock_client(mock_resp_1536)

service = EmbeddingService(config=config, http_client=mock_client)

vector = service.embed("Hello world", classification=PUBLIC)
check("EmbeddingService.embed returns list", type(vector) is list)
check("EmbeddingService.embed returns 1536-dim vector", len(vector) == 1536)
check("Vector elements are floats", all(type(v) is float for v in vector[:5]))

# =========================================================================
# 6. Dimension mismatch detection
# =========================================================================
print("\n--- 6. Dimension Mismatch Detection ---")

mock_resp_384 = make_mock_response(200, 384, 1)
mock_client_384 = make_mock_client(mock_resp_384)
service_384 = EmbeddingService(config=config, http_client=mock_client_384)

run_expect_error(
    "384-dim vector raises DimensionMismatchError",
    DimensionMismatchError,
    service_384.embed,
    ("test", PUBLIC),
)

# =========================================================================
# 7. Batch embedding
# =========================================================================
print("\n--- 7. Batch Embedding ---")

mock_resp_batch = make_mock_response(200, 1536, 3)
mock_client_batch = make_mock_client(mock_resp_batch)
service_batch = EmbeddingService(config=config, http_client=mock_client_batch)

vectors = service_batch.embed_batch(["a", "b", "c"], classification=PUBLIC)
check("Batch returns list", type(vectors) is list)
check("Batch returns 3 vectors", len(vectors) == 3)
check("Each vector is 1536-dim", all(len(v) == 1536 for v in vectors))

# =========================================================================
# 8. Convenience functions (exist and are callable)
# =========================================================================
print("\n--- 8. Convenience Functions ---")

from src.memory.embeddings import embed as emb_fn, embed_batch as emb_batch_fn

check("module-level embed() is callable", callable(emb_fn))
check("module-level embed_batch() is callable", callable(emb_batch_fn))

# =========================================================================
# 9. Text truncation
# =========================================================================
print("\n--- 9. Text Truncation (8000 chars) ---")

long_text = "a" * 10000
prepared = prepare_embedding_text(long_text, PUBLIC)
check("prepare_embedding_text truncates 10000 -> 8000", len(prepared.text) == 8000)

short_text = "hello"
prepared_short = prepare_embedding_text(short_text, PUBLIC)
check("prepare_embedding_text leaves short text unchanged", prepared_short.text == "hello")

# =========================================================================
# 10. No secrets leak in output
# =========================================================================
print("\n--- 10. No Secrets in Output / Config ---")

config_repr = repr(config)
check("API key value not in EmbeddingConfig repr",
      "test-key-redacted" not in config_repr)
check("API key value not leaked in str(config)",
      "test-key-redacted" not in str(config))

check("PreparedText fields accessible",
      hasattr(prepared, "classification") and hasattr(prepared, "redaction_applied"))

# Redaction patterns sanity: innocuous text not redacted
innocuous = "The quick brown fox jumps over the lazy dog."
result_clean = prepare_embedding_text(innocuous, RESTRICTED)
check("Innocuous text not redacted", result_clean.redaction_applied is False)
check("Innocuous text unchanged", result_clean.text == innocuous)

# =========================================================================
# Cleanup
# =========================================================================
del os.environ["GUINEVERE_9ROUTER_API_KEY"]

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