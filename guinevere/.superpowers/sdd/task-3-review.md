# Task 3 Review: Memory Backend — 18 Actions

**Commit:** `6f6d7d0` — `feat(tools): implement memory backend — 18 PostgreSQL+pgvector actions`
**Date:** 2026-07-03
**Reviewer:** automated
**Result:** FAIL

---

## Checklist Results

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | All 18 actions implemented as async | PASS | 18 async methods in `MemoryBackend`, all in `_HANDLERS` dispatch map |
| 2 | SQLAlchemy async (AsyncSession) | PASS | Uses `AsyncSession` via `async_sessionmaker`; all DB ops are `await` |
| 3 | Type annotations | PASS | All 18 action handlers fully annotated `(self, action: str, args: dict[str, Any]) -> dict[str, Any]`; models use `Mapped[T]` |
| 4 | No `# type: ignore` | PASS | Zero occurrences in all 3 files |
| 5 | Error handling: SQLAlchemyError (no broad except) | **FAIL** | `dispatch()` line 171 has `except Exception as exc:` (broad catch) after the `SQLAlchemyError` catch. Checklist requires no broad except. |
| 6 | Returns `{"ok": bool, "action": str, ...}` | PASS | Every action returns dict with `ok` and `action` keys |
| 7 | Embeddings as JSON arrays | PASS | `embedding_json` column is `JSON` type; `_parse_embedding()` normalizes to `list[float]` |
| 8 | Tests use in-memory SQLite via aiosqlite | PASS | `create_async_engine("sqlite+aiosqlite:///:memory:")` in `db_engine` fixture |
| 9 | At least 3 tests per action | PASS | All 18 actions have 3-5 tests; 68 async + 3 sync = 71 test methods total |
| 10 | MemoryType enum, to_dict() | PASS | `MemoryType(str, Enum)` with 6 values; `Memory.to_dict()` and `MemoryCollection.to_dict()` both present |

---

## mypy Results

**models.py:** 0 errors (clean)

**memory.py:** 19 errors

```
guinevere\tools\backends\memory.py:39:  error: Function is missing a return type annotation  [no-untyped-def]
guinevere\tools\backends\memory.py:164: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
guinevere\tools\backends\memory.py:208,225,253,287,327,351,392,432,470,533,561,599,647,671,694,726,757:
    error: Call to untyped function (unknown) in typed context  [no-untyped-call]  (x17)
```

Root cause: `_create_session_factory()` (line 39) has no return type annotation and imports `get_async_session` from `guinvere.memory.db` which is untyped. This cascades as 17 `[no-untyped-call]` errors in every action handler that calls `_get_session()`.

---

## pytest Results

```
78 passed, 613 warnings in 3.69s
```

All 78 tests pass (71 test methods + 7 cross-cutting). No failures.

---

## Issues

### MUST FIX (blocks PASS)

1. **Broad `except Exception` in `dispatch()` (line 171)**
   The checklist explicitly requires "Error handling: SQLAlchemyError (no broad except)". The `dispatch()` method catches `SQLAlchemyError` first (good) but then has a catch-all `except Exception` as a second handler. This should be removed or narrowed to specific expected exceptions (e.g., `ValueError`, `KeyError`).

   ```python
   # Current (line 167-174):
   except SQLAlchemyError as exc:
       ...
       return {"ok": False, "action": action, "error": f"db error: {exc}"}
   except Exception as exc:        # <-- broad catch, violates checklist
       ...
       return {"ok": False, "action": action, "error": str(exc)}
   ```

2. **mypy: `_create_session_factory` missing return type (line 39)**
   Add return type annotation. The function returns `get_async_session` from `guinvere.memory.db`. Even if that upstream function is untyped, the factory itself should declare its return type (e.g., `-> Callable[..., AsyncContextManager[AsyncSession]]`) to suppress the 17 downstream `[no-untyped-call]` errors.

### SHOULD FIX

3. **mypy: `Returning Any` at line 164**
   `dispatch()` returns the result of `await handler(self, action, args)` where `handler` is typed as `Any` (from `_HANDLERS: dict[str, Any]`). Narrow the `_HANDLERS` value type to a proper callable signature to fix this.

4. **Redundant `onupdate` on `Memory.updated_at` (models.py line 128)**
   `onupdate=lambda: datetime.now(timezone.utc)` only fires on SQL UPDATE statements with SET clauses, not on ORM attribute mutation. The action handlers correctly set `memory.updated_at = _now()` explicitly, making the `onupdate` dead code. Either remove it or document that it only covers raw SQL UPDATEs.

---

## Positive Notes

- Clean architecture: `MemoryBackend(ToolBackend)` class with dispatch pattern consistent with other backends
- Proper use of `flag_modified()` for JSON column mutation in `set_memory_metadata`
- Pure-Python cosine similarity fallback for SQLite test compatibility
- Good error messages with action name in every error return
- `consolidate_memories` correctly averages embeddings and merges metadata
- Test fixtures use `monkeypatch` to isolate the session factory — clean test isolation
- `MemoryType(str, Enum)` with 6 cognitive-science-inspired types
- Cross-cutting tests: `TestActionCatalogue`, `TestFailSoft`, `TestMemoryType`

---

## Files Reviewed

- `guinevere/memory/models.py` (194 lines) — models clean
- `guinevere/tools/backends/memory.py` (798 lines) — 2 must-fix issues
- `tests/p24/test_memory_backend.py` (848 lines) — all 78 tests pass
