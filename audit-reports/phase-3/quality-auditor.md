# Code Quality Audit — Phase 3 Memory Bridge Migration

**Auditor**: `quality-auditor` (code quality specialist)  
**Date**: 2026-06-05  
**Scope**: 
- `plugins/memory/guinevere_memory/__init__.py` (892 lines)
- `plugins/memory/guinevere_memory/safety_gates.py` (394 lines)
- `plugins/memory/guinevere_memory/base.py` (159 lines)
- `scripts/ab_test_recall.py` (495 lines)

**Verdict**: ⚠️ **NEEDS REVIEW** — 3 BLOCKING, 5 WARNING, 6 INFO/STYLE issues found.

---

## 1. Type Safety

### 1.1 WARNING — Pervasive `Any` in core pipeline signatures
**Files**: `__init__.py` (lines 371, 570, 606, 879), `safety_gates.py` (lines 79, 129, 152, 192, 239, 357)

The `recall_fn: Any` parameter in `_prefetch_async` (line 371) loses the entire callable signature. Similarly, `messages: list[Any]` in `on_pre_compress`/`on_session_end` obscures the message type. Consider defining a `Message` Protocol or TypedDict.

**Severity**: WARNING — not blocking but degrades IDE support and static analysis.

### 1.2 INFO — `QueryRecord` / `Metric` type aliases are good but shallow
**File**: `ab_test_recall.py` (lines 112-113)

`QueryRecord = dict[str, Any]` and `Metric = dict[str, Any]` are better than raw `dict` but still opaque. A `TypedDict` with known keys (`id`, `query`, `category`, `expected_signals`, `max_results`) would enable key-checking at development time.

**Severity**: INFO — acceptable for a standalone CLI script.

### 1.3 STYLE — `Any` in ABC stub is expected
**File**: `base.py` (lines 49, 58, 67, 76, 84, 120, 127, 140)

All `Any` usages are in abstract method signatures matching upstream Hermes Agent API — intentional and acceptable.

**Severity**: STYLE — LOW; ABC mirrors external contract.

---

## 2. Documentation

### 2.1 WARNING — Missing docstrings on internal functions in `ab_test_recall.py`
**File**: `ab_test_recall.py`

| Function | Line | Issue |
|---|---|---|
| `_compute_rrf` | 96 | No docstring |
| `_interpret_d` | 274 | No docstring |
| `check_preconditions` | 373 | No docstring |

All three are `MUST DO` checklist items. Every function in scope should have a docstring.

**Severity**: WARNING — violates audit scope requirements.

### 2.2 PASS — All public methods in `__init__.py`, `safety_gates.py`, `base.py` have docstrings ✅

Every public method in the three plugin modules is documented with description, args, and returns. Quality is high.

---

## 3. Error Handling

### 3.1 BLOCKING — Bare `except Exception:` in Redis consent checks
**File**: `__init__.py` (lines 114, 154)

```python
except Exception:                      # line 114
    _logger.warning(
        "redis_consent_check_failed",
        extra={"category": category},
        exc_info=True,
    )
    return False
```

```python
except Exception:                      # line 154
    _logger.warning("redis_safe_word_check_failed", exc_info=True)
```

Both catch `KeyboardInterrupt`, `SystemExit`, `MemoryError`, and other non-recoverable exceptions. Should catch at minimum `redis.exceptions.RedisError`. The intent is "network/database errors" not "everything that can go wrong."

**Severity**: BLOCKING — bare except is an anti-pattern explicitly forbidden by AGENTS.md §5.

### 3.2 WARNING — Overly broad `except Exception` in safety gates
**File**: `safety_gates.py` (lines 111, 311, 392)

```python
except Exception as exc:               # line 111 — DNR cache refresh
    _logger.warning("dnr_cache_refresh_error: %s", exc)
```

```python
except Exception as exc:               # line 311 — consent gate Redis error
    _logger.warning("consent_gate_redis_error: %s", exc)
```

```python
except Exception as exc:               # line 392 — safety pipeline
    _logger.error("safety_pipeline_error: %s", exc)
    return []
```

The DNR refresh should catch `ImportError` and `OSError`/database errors specifically. The consent gate should catch `redis.exceptions.RedisError`. The safety pipeline blanket-catch could mask a logic error (e.g., `TypeError` from bad input).

**Severity**: WARNING — pattern is consistent (fail-safe + log) but precision matters for debugging.

### 3.3 INFO — `__init__.py` async methods catch broad exceptions gracefully
**File**: `__init__.py` (lines 360, 397, 484, 561, 669, 721)

These each catch `Exception as exc` with structured logging and `extra=` context. While broad, they are daemon-thread/fire-and-forget paths where crashing silently is worse than logging and moving on. Acceptable given the threading context.

**Severity**: INFO — documented pattern, but consider a custom `MemoryProviderError` base.

---

## 4. Code Duplication

### 4.1 BLOCKING — Redis connection boilerplate duplicated 3 times
**Files**:
- `__init__.py` lines 103-110 (`_check_redis_consent`)
- `__init__.py` lines 137-144 (`_check_redis_safe_word_active`)
- `safety_gates.py` lines 323-328 (`ConsentGate._check_redis_consent`)

All three instances construct an identical `redis.Redis.from_url()` call with the same timeout parameters (lines 103-110 and 137-144 are 100% identical). This is a maintenance risk — if the Redis URL or timeout changes, three locations must be updated.

**Recommended**: Extract a `_get_redis_connection()` helper:
```python
def _get_redis_connection(url: str = _REDIS_CONSENT_URL) -> redis.Redis:
    return redis.Redis.from_url(
        url,
        socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
        socket_timeout=_REDIS_CONNECT_TIMEOUT,
        decode_responses=True,
    )
```

**Severity**: BLOCKING — AGENTS.md §5 anti-patterns explicitly calls out duplication as a maintainability risk.

### 4.2 WARNING — `get_async_sessionmaker` import pattern duplicated 3 times
**File**: `__init__.py` (lines 378, 528, 690)

The exact same try/except/import/fallback block for `from src.core.db.database import get_async_sessionmaker` appears three times. Should be a module-level lazy import or helper.

**Severity**: WARNING — less critical than Redis duplication but still worth consolidating.

### 4.3 WARNING — `write_pipeline` import pattern duplicated twice
**File**: `__init__.py` (lines 512, 683)

Same `from src.memory.embeddings import RESTRICTED` + `from src.memory.write_pipeline import store_episode` pattern in `_sync_turn_async` and `_store_mirror_facts`.

**Severity**: WARNING — consolidatable.

---

## 5. Naming Conventions

### 5.1 INFO — `_REDIS_CONSENT_URL` naming inconsistent with Redis DB5 role
**File**: `__init__.py` (line 81)

Constant is named `_REDIS_CONSENT_URL` but the accompanying comment says "DB5 (same DB as safety state manager)" and it's actually used for both consent AND safe-word/distress checks. The name is misleading for the safe-word path.

**Severity**: INFO — naming is accurate for consent path, just incomplete for the second use case.

### 5.2 PASS — All other naming is consistent ✅

Classes: PascalCase. Functions/methods: snake_case. Constants: UPPER_CASE. Module-private: `_` prefix. No violations found.

---

## 6. Complexity

### 6.1 WARNING — `ab_test_recall.py::main()` is 97 lines
**File**: `ab_test_recall.py` (lines 398-495)

The CLI entry point does dataset loading, precondition checks, benchmark runs, stats computation, and output serialization all in one function. Should be refactored into:
- `_run_benchmark_phase()` — steps 3-4
- `_run_stats_phase()` — step 5
- `_write_output()` — serialization

**Severity**: WARNING — violates single-responsibility principle.

### 6.2 WARNING — `ab_test_recall.py::compute_statistics()` is 85 lines
**File**: `ab_test_recall.py` (lines 284-366)

Mann-Whitney U, Welch's t-test, Cohen's d, and 95% CI computation are all in one function. Each statistical test could be its own function (`_mann_whitney_u()`, `_welch_ttest()`, `_cohens_d()`, `_confidence_interval()`).

**Severity**: WARNING — cyclomatic complexity is high; hard to test individual tests in isolation.

### 6.3 INFO — `simulate_recall_metric()` is 72 lines
**File**: `ab_test_recall.py` (lines 148-218)

Has two nearly-identical early-return dicts (lines 159-166 and 194-200). Could extract `_empty_metric()` helper.

**Severity**: INFO — acceptable for a simulation function.

### 6.4 PASS — Plugin methods are well-factored ✅

`GuinevereMemoryProvider` splits async implementations into separate `_prefetch_async`, `_sync_turn_async`, `_store_mirror_facts`. Good separation.

---

## 7. Import Organization

### 7.1 PASS — Clean import structure ✅

All four files follow: `from __future__ import annotations` → standard library → third-party → local. No circular imports detected. Lazy imports inside methods for `redis`, `read_pipeline`, `write_pipeline` are intentional to prevent import errors when dependencies are missing.

---

## 8. Constants

### 8.1 INFO — Magic numbers in `_prefetch_async` latency simulation
**File**: `ab_test_recall.py` (line 206)

```python
latency_ms = base_latency_ms * (1.0 + query_len / 50.0) * (1.0 + signal_count * 0.3)
```

The `50.0` (characters-per-unit divisor) and `0.3` (per-signal latency multiplier) are unlabeled magic numbers. Should be:
```python
_CHARS_PER_LATENCY_UNIT: float = 50.0
_PER_SIGNAL_LATENCY_FACTOR: float = 0.3
```

**Severity**: INFO — simulation model, not production code, but still opaque.

### 8.2 PASS — All other magic numbers are named constants ✅

`_RRF_K`, `_VECTOR_WEIGHT`, `_FTS_WEIGHT`, `_BOTH_SIGNAL_BONUS`, `_DNR_CACHE_TTL_SECONDS`, `_DEFAULT_RECALL_LIMIT`, `_DEFAULT_TOKEN_BUDGET`, `_REDIS_CONNECT_TIMEOUT`, `_HASH_PREFIX_LEN` are all properly extracted.

---

## 9. Testing Readiness

### 9.1 WARNING — Hard dependencies on external imports make unit testing difficult
**File**: `__init__.py` (lines 350, 512, 683)

`recall_memories`, `store_episode`, and `RESTRICTED` are imported lazily inside methods. To unit-test `prefetch()` or `sync_turn()`, you must monkey-patch `sys.modules` or provide a full mock chain. Dependency injection (passing these as constructor arguments or class attributes) would make tests trivial.

**Severity**: WARNING — not blocking for Phase 3 but will be costly for Phase 4+ test coverage.

### 9.2 WARNING — Module-level globals prevent isolated testing in `ab_test_recall.py`
**File**: `ab_test_recall.py` (lines 51, 64, 67, 70)

`_SCIPY_AVAILABLE`, `_PIPELINE_OK`, `_EMBED_OK`, `_DNR_OK` are module-level booleans set at import time. A test cannot simulate "scipy available" vs "scipy not available" without reloading the module. Should be functions or injectable.

**Severity**: WARNING — limits test coverage for the fallback paths.

### 9.3 PASS — `DnrIdCache` and `ConsentGate` are testable ✅

`DnrIdCache.get_dnr_ids()` accepts `session_factory` as parameter. `ConsentGate.configure()` accepts `redis_url`. Both support dependency injection.

---

## 10. PEP 8 Compliance

### 10.1 BLOCKING — Malformed comment separator in `__init__.py`
**File**: `__init__.py` (lines 758-762)

```python
        # ---------------------------------------------------------------------------
    # Mirror sync counter — increment on each sync_turn
    # ---------------------------------------------------------------------------

    def _increment_mirror_counter(self) -> None:
```

The separator block starts at 8-space indent (inside `shutdown()`), then lines 759-760 jump to 4-space indent (class level). This is a formatting error that makes the code structurally misleading — it appears as if the section header comment is split between `shutdown()` and class scope.

**Minimal fix**: Remove lines 758-760 or move them entirely after `shutdown()` with consistent 4-space indent.

**Severity**: BLOCKING — structural formatting error that misrepresents code organization.

### 10.2 STYLE — Redundant `hasattr` + `getattr` in `on_pre_compress`
**File**: `__init__.py` (line 586)

```python
len(str(getattr(m, "content", m) if hasattr(m, "content") else m))
```

`getattr(m, "content", m)` already handles the fallback. The `hasattr` check is redundant:
```python
len(str(getattr(m, "content", m)))
```

**Severity**: STYLE — no behavioral difference, but unnecessary complexity.

---

## 11. Logging Quality

### 11.1 WARNING — Inconsistent logging style: `%` formatting in `safety_gates.py` vs `extra=` in `__init__.py`
**File**: `safety_gates.py` (lines 108, 172, 219, 312, 386, 389, 393)

`safety_gates.py` uses old-style `%` formatting:
```python
_logger.info("dnr_cache_refreshed: count=%d", len(dnr_ids))       # line 108
_logger.warning("dnr_cache_refresh_error: %s", exc)                # line 112
```

While `__init__.py` uses structured logging with `extra=`:
```python
_logger.info("prefetch_recall_success", extra={"query_length": len(query), ...})
```

Mixing styles within the same plugin package makes log parsing harder. Structured `extra=` is preferred for observability (Prometheus/Loki ingestion).

**Severity**: WARNING — inconsistent within a single plugin package.

### 11.2 PASS — No raw content in logs ✅

All content logging uses `content_hash()`, `len(content)`, or truncated IDs (`str(r.get("id", ""))[:8]`). Never logs raw user messages, memory content, or PII.

### 11.3 PASS — Thread-level events have appropriate levels ✅

`sync_turn` errors use `_logger.error`, consent blocks use `_logger.info`, debug details use `_logger.debug`. Levels are well-judged.

---

## 12. Anti-Patterns

### 12.1 INFO — `content_hash` uses MD5 for non-cryptographic deduplication (acceptable)
**File**: `safety_gates.py` (line 343) — uses SHA-256 ✅  
**File**: `__init__.py` (line 835) — `extract_key_facts` uses MD5 for deduplication

`hashlib.md5()` at line 835 is used for Set-based deduplication, not security. This is acceptable but should have a comment noting "non-cryptographic use." SHA-256 at `safety_gates.py:343` is appropriate for logging.

**Severity**: INFO — MD5 is fine for dedup, but `safety_gates.py` already provides `content_hash()` with SHA-256 — why not reuse it?

### 12.2 INFO — `_turn_count` incremented outside lock in `sync_turn`
**File**: `__init__.py` (lines 471, 764)

`_increment_mirror_counter()` does `self._turn_count += 1` without a lock. It's called from `sync_turn()` (line 471) *before* the daemon thread starts, so it runs on the main/caller thread. However, if `sync_turn` is ever called concurrently from multiple threads, this is a race condition. The comment/Javadoc should document the thread-safety assumption.

**Severity**: INFO — currently safe by design but fragile; document or add a lock guard comment.

### 12.3 PASS — No mutable defaults found ✅

Scanned all function signatures across all four files. No `def foo(items=[])` or `def foo(mapping={})` patterns.

### 12.4 PASS — No bare `except:` (the `except Exception:` is the issue, covered in §3.1)

---

## 13. `__all__` Exports

### 13.1 STYLE — No `__all__` defined in any module
**Files**: `__init__.py`, `safety_gates.py`, `base.py`

None of the three modules define `__all__`. This means `from module import *` exposes all public and private symbols:

- `__init__.py` would export `_check_redis_consent`, `_check_redis_safe_word_active`, `_compute_rrf`, `_infer_topic`, etc.
- `safety_gates.py` would export `DnrCacheEntry`, `_logger`, etc.
- `base.py` would export `ABC`, `abstractmethod`, `Any`.

**Recommended**:
- `__init__.py`: `__all__ = ["GuinevereMemoryProvider", "register", "extract_key_facts"]`
- `safety_gates.py`: `__all__ = ["ConsentGate", "DnrIdCache", "SafetyGateResult", "classify_ceiling_filter", "anti_hallucination_check", "safe_mode_substitute", "content_hash", "run_safety_pipeline"]`
- `base.py`: `__all__ = ["MemoryProvider"]`

**Severity**: STYLE — LOW priority but audit checklist item.

---

## 14. Additional Findings

### 14.1 BLOCKING (BUG) — `run_safety_pipeline` log message reports wrong input count
**File**: `safety_gates.py` (lines 385-389)

```python
_logger.info(
    "safety_pipeline_complete: input=%d, output=%d, gates=4",
    len(results),
    len(results),
)
```

Both format arguments are `len(results)`, which at this point is the **output** count (after all 4 gates have mutated `results`). The log will always report identical input/output counts, defeating the purpose of the log. `input=` should be the original count captured before gate processing.

**Severity**: BLOCKING — misleading observability data. Fix:
```python
original_count = len(results)  # before gate mutations
# ... run gates ...
_logger.info(
    "safety_pipeline_complete: input=%d, output=%d, gates=4",
    original_count,
    len(results),
)
```

### 14.2 WARNING (BUG) — `ab_test_recall.py` confidence interval `se` formula is wrong
**File**: `ab_test_recall.py` (line 346)

```python
se = math.sqrt(b_var_pop + h_var_pop) if b_scores else 0.0
```

For a two-sample confidence interval of the difference in means, the standard error should be:
```python
se = math.sqrt(b_var_pop / len(b_scores) + h_var_pop / len(h_scores))
```

The current formula computes `sqrt(var1 + var2)` which is the standard deviation of the *sum*, not the standard error of the *difference in means*. CI will be wider than correct by factor of `sqrt(n)`.

**Severity**: WARNING — statistical output is incorrect; CI bounds are inflated. Fix by dividing each variance term by its respective sample size.

---

## Summary

| Category | Count | Details |
|---|---|---|
| BLOCKING | 3 | Bare except (§3.1), Redis duplication (§4.1), PEP 8 comment separator (§10.1), BUG: pipeline input log (§14.1) |
| WARNING | 8 | Pervasive `Any` (§1.1), missing docstrings (§2.1), broad except (§3.2), sessionmaker duplication (§4.2), import duplication (§4.3), `main()` complexity (§6.1), `compute_statistics()` complexity (§6.2), testing readiness (§9.1-9.2), inconsistent logging (§11.1), CI `se` formula bug (§14.2) |
| INFO | 6 | Type aliases (§1.2), broad exception in daemon threads (§3.3), constant naming (§5.1), metric function duplication (§6.3), magic numbers (§8.1), thread-safety assumption (§12.2) |
| STYLE | 3 | ABC Any expected (§1.3), redundant hasattr (§10.2), MD5 reuse opportunity (§12.1), no `__all__` (§13.1) |

**Total**: 3 BLOCKING, 8+ WARNING, 6+ INFO, 3+ STYLE — 20+ findings.

---

## Recommendations (Priority Order)

1. **Fix bare `except Exception:`** in `__init__.py:114,154` → catch `redis.exceptions.RedisError`.
2. **Extract `_get_redis_connection()`** helper to eliminate the 3× duplicated Redis boilerplate.
3. **Fix PEP 8 comment separator** at `__init__.py:758-762`.
4. **Fix `run_safety_pipeline` log** to capture original input count before gate mutations.
5. **Fix CI standard error** formula in `ab_test_recall.py:346`.
6. **Fix shell prompt injection** in agent loop session management (separate finding — see security auditor).
7. Add `__all__` to all three plugin modules.
8. Consolidate `get_async_sessionmaker` and `write_pipeline` import patterns.
9. Unify logging style to `extra=` structured format across the plugin package.
10. Add missing docstrings to `_compute_rrf`, `_interpret_d`, `check_preconditions`.