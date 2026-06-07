# STEP B3-A3 — Memory Bridge Extraction Verification

**Date**: 2026-06-06
**Step**: A3 (sub-step) — Extract `memory_bridge.py` to `_memory_bridge.py` and update active production import

## What Was Done

### 1. Created `src/hermes/_memory_bridge.py`

Non-deprecated home for `HermesMemoryBridge`, preserving all class/API behavior from `memory_bridge.py`:

- Same `AsyncSessionFactory` protocol
- Same `HermesMemoryBridge` class with `__init__`, `recall_for_context`, `store_conversation`, `extract_key_facts`
- Removed the `warnings.warn()` deprecation call
- Removed deprecated docstring references
- Preserved all safe-delegation patterns (DNR exclusion, classification ceiling, safe-mode, token budget)
- Documented inherited `Any`/broad-exception debt as inherited from deprecated implementation

### 2. Updated `src/discord/hermes_conversational.py`

Changed lazy import in `_get_or_create_bridge()` (line 132):
- **Before**: `from src.hermes.memory_bridge import HermesMemoryBridge`
- **After**: `from src.hermes._memory_bridge import HermesMemoryBridge`

### 3. Documented `conversational_handler.py` as internal-to-deprecated

`src/discord/conversational_handler.py` is itself an archive target (listed in the B3 archive plan). Its import from `src.hermes.memory_bridge` (line 155) is internal to a deprecated file and is not an active blocker.

## Files Changed

| File | Action | Notes |
|---|---|---|
| `src/hermes/_memory_bridge.py` | **CREATE** | Non-deprecated extraction of `HermesMemoryBridge` |
| `src/discord/hermes_conversational.py` | **EDIT** | Changed import to `src.hermes._memory_bridge` |

## Files NOT Changed (Intentionally)

| File | Why |
|---|---|
| `src/hermes/memory_bridge.py` | Untouched — will be archived in a later step |
| `src/discord/conversational_handler.py` | Is itself a deprecated archive target; internal import is not a blocker |
| `tests/hermes/test_memory_bridge.py` | Test migration deferred to A4 |

## Verification Scans

### Active Import Scan — Production Code

Pattern: `from src\.hermes\.memory_bridge import` in `src/`

```
→ 1 match in src/discord/conversational_handler.py (DEPRECATED — archive target)
→ 0 matches in non-deprecated production code
```

Pattern: `src\.hermes\.memory_bridge` in `src/`

```
→ 1 match in src/discord/conversational_handler.py (DEPRECATED — archive target)
→ 0 matches in non-deprecated production code
```

**Result**: Zero active production imports from `src.hermes.memory_bridge` outside deprecated archive targets. ✅

### Active Import Scan — Tests

```
→ 1 match in tests/hermes/test_memory_bridge.py (A4 migration target)
```

### LSP Diagnostics — `src/hermes/_memory_bridge.py`

```
All warnings are reportAny/reportExplicitAny inherited from the deprecated
implementation (AsyncSessionFactory protocol return type, session/embedding
service type annotations).  Zero new warnings introduced.  No errors.
```

### LSP Diagnostics — `src/discord/hermes_conversational.py`

```
All warnings are pre-existing reportAny/reportExplicitAny from the existing
Discord type annotations (structlog, discord.py types).  One false-positive
reportMissingImports for "src.hermes._memory_bridge" (basedpyright issue with
underscore-prefixed modules; runtime import verified working).

=== BEFORE vs AFTER ===
- Before:  0 errors, ~90 warnings
- After:   1 false-positive error (import resolution — works at runtime)
- Net new: 0 real errors introduced
```

## Command Results

### Phase 7 tests

```text
$ python -m pytest tests/phase7/ -q --tb=short
139 passed, 1 warning in 3.90s
```

### Deprecated memory bridge tests (A4 target — still uses `memory_bridge.py`)

```text
$ python -m pytest tests/hermes/test_memory_bridge.py -q --tb=short
17 passed, 155 warnings in 1.05s
```

## Architectural Compliance

| Requirement | Status | Evidence |
|---|---|---|
| `memory_bridge.py` untouched | ✅ | File unchanged at original path |
| Non-deprecated module created | ✅ | `src/hermes/_memory_bridge.py` |
| Active production import updated | ✅ | `hermes_conversational.py` imports from `_memory_bridge` |
| No new type suppressions/empty catches | ✅ | Only inherited Any debt documented |
| No Aizanta/VPS/git touched | ✅ | Local operations only |
| Phase 7 / B3 completion not claimed | ✅ | Single sub-step evidence only |

## Caveats

1. The LSP's `reportMissingImports` error for `src.hermes._memory_bridge` is a basedpyright false-positive with underscore-prefixed modules. Runtime `python -c "from src.hermes._memory_bridge import HermesMemoryBridge"` succeeds.
2. `conversational_handler.py` still imports from deprecated `memory_bridge.py` — this is acceptable as it is itself an archive target.
3. `tests/hermes/test_memory_bridge.py` still imports from deprecated `memory_bridge.py` — deferred to A4 test migration.
4. All `reportAny`/`reportExplicitAny` warnings in `_memory_bridge.py` are inherited from the original `memory_bridge.py` and are documented as such.
5. B3 is not complete; A4 (test migration), A5 (pre-archive gate), A6 (archive), A7 (post-archive), and A8 (auditors) remain.

## Footer

Authored by Sisyphus-Junior executor for Phase 7c B3 Archive — A3 Memory Bridge sub-step.
