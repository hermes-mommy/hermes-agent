# Phase 7c — Archive Patterns Research Report

**Date**: 2026-06-06  
**Scope**: Safe Python deprecated-file archive patterns, import path validity, test migration strategy  
**Status**: Complete

---

## 1. Executive Verdict

**`src/_deprecated/hermes-migration-phase-7/` is NOT importable as a Python package/module via standard `import` statements.** Hyphens are invalid in Python identifiers, so any directory containing a hyphen cannot be a subpackage that `import` resolves. The proposed `git mv` into a hyphenated archive path will **break all test imports** that try to load archived code through normal Python import machinery.

---

## 2. Python Import Rules — Hyphenated Directory Names

### The Rule

Python's `import` statement requires module/package names to be valid Python **identifiers** ([PEP 8](https://peps.python.org/pep-0008/#package-and-module-names), [Python import system docs](https://docs.python.org/3/reference/import.html)):

- Allowed: `[A-Za-z_][A-Za-z0-9_]*`
- Hyphens (`-`) are **NOT** allowed — Python interprets `hermes-migration-phase-7` as `hermes - migration - phase - 7` (subtraction), causing `SyntaxError`

### What Fails

```python
# ALL of these raise SyntaxError:
import _deprecated.hermes-migration-phase-7
from _deprecated.hermes-migration-phase-7 import some_module
from _deprecated import hermes-migration-phase-7
```

### Workarounds (limited, not recommended for this context)

```python
# Workaround 1: importlib (dynamic, no static analysis support)
import importlib
mod = importlib.import_module("_deprecated.hermes-migration-phase-7.module_name")

# Workaround 2: importlib.util.spec_from_file_location
import importlib.util
spec = importlib.util.spec_from_file_location("module_name", "path/to/hermes-migration-phase-7/module.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

Both workarounds bypass Python's import system cache, break static analysis (mypy, pylint, type checkers), and require non-standard test harness modifications. **Not suitable as a primary strategy.**

### Industry Convention

The standard Python pattern for this exact problem (hyphenated names) is well-established:

| Distribution Name (PyPI) | Import Name | Example |
|---|---|---|
| `scikit-learn` | `sklearn` | `pip install scikit-learn` → `import sklearn` |
| `python-dateutil` | `dateutil` | `pip install python-dateutil` → `import dateutil` |
| `my-awesome-project` | `my_awesome_project` | `pip install my-awesome-project` → `import my_awesome_project` |

**Rule**: Hyphens in distribution/directory names → underscores in importable package names.

---

## 3. OSS Deprecated-File Archive Patterns

### Pattern A: In-Place Deprecation with Warnings (Django-style)

**Used by**: Django, CPython, pytest, many large frameworks  
**Mechanism**: Code stays in original location, marked with `@deprecated` decorator or `warnings.warn()`. Removed in a future major version.

```python
# django/utils/deprecation.py (simplified)
import warnings

class RemovedInNextVersionWarning(DeprecationWarning):
    pass

def warn_about_deprecated_feature(message):
    warnings.warn(message, RemovedInNextVersionWarning, stacklevel=2)
```

**Pros**: No import breakage, clean history, gradual migration  
**Cons**: Code stays in active tree, no semantic separation, can bloat

### Pattern B: `_deprecated/` Subdirectory with Underscore Names (elastic/detection-rules style)

**Used by**: [elastic/detection-rules](https://github.com/elastic/detection-rules/blob/main/detection_rules/packaging.py#L37) (rules → `rules/_deprecated/`), ClawBio (skills → `skills/_deprecated/`)  
**Mechanism**: `git mv` files into a `_deprecated/` subdir, using underscore-separated names so imports remain valid.

```
src/
  _deprecated/
    __init__.py
    hermes_migration_phase_7/    # ← underscores, importable
        __init__.py
        cmd_approve.py
        cmd_deny.py
```

**Pros**: Clear semantic boundary, git history preserved via `git mv`, imports work  
**Cons**: Requires renaming directory to underscores

### Pattern C: Stub Forwarding + Deprecation Warning (housekeeping style)

**Used by**: [beanbaginc/housekeeping](https://github.com/beanbaginc/housekeeping)  
**Mechanism**: Original module path kept as a forwarding stub that imports from the new location and emits a deprecation warning.

```python
# Original location: src/discord/cmd_approve.py  
# After move → becomes a forwarding stub:
import warnings
from _deprecated.hermes_migration_phase_7.cmd_approve import *  # noqa: F401, F403

warnings.warn(
    "src.discord.cmd_approve is deprecated, use "
    "_deprecated.hermes_migration_phase_7.cmd_approve",
    DeprecationWarning,
    stacklevel=2,
)
```

**Pros**: Backward-compatible imports, graceful degradation  
**Cons**: Forwarding stubs clutter the original location, two code paths must coexist

### Pattern D: Test-Level Deprecation (magma style)

**Used by**: [phanrahan/magma](https://github.com/phanrahan/magma/tree/master/tests/test_deprecated)  
**Mechanism**: Deprecated tests moved to `tests/test_deprecated/` with the code left in-place. Tests import from original location but are grouped separately.

**Pros**: Tests clearly marked, no code movement risk  
**Cons**: Doesn't solve the code archival problem

---

## 4. Git History Preservation

### `git mv` is Sufficient

Contrary to common fear, **`git mv` preserves history**. Git tracks content by hash, not by filename. After a move:

```bash
git mv src/discord/cmd_approve.py src/_deprecated/hermes_migration_phase_7/
git commit -m "archive: move cmd_approve to _deprecated"
```

History is accessible via:

```bash
git log --follow src/_deprecated/hermes_migration_phase_7/cmd_approve.py
```

This will show the **full commit history** from before the move. No special flags, no `filter-branch`, no `filter-repo` needed. The `--follow` flag tells Git to detect renames.

### What `git mv` Actually Does

```
git mv A B  ≡  mv A B  +  git add A B  +  git rm A
```

It stages a rename record that Git's rename detection (enabled by default) recognizes. The commit records it as a rename, preserving the content history chain.

### When You'd Need More

- **Rewriting history** (making files appear in the new location in ALL past commits): Use `git filter-repo --path-rename old/:new/`. Only needed if you want `git log` without `--follow`, which is not necessary here.

---

## 5. Test Migration Strategy

### Current Test Import Patterns

The project has two test import patterns:

**Pattern 1 — Absolute imports from `src.*`** (used by most tests):
```python
# tests/discord/test_cmd_mood.py
from src.discord.colors import PRIMARY
from src.discord.cmd_mood import mood_callback
from src.discord.commands import command_count
```

**Pattern 2 — Relative intra-package imports** (used within `src/discord/`):
```python
# src/discord/cmd_approve.py
from .colors import SUCCESS
from ._embed_helpers import ...
from .commands import is_faiz_interaction
```

### The Critical Problem: Relative Imports in Archived Files

If you `git mv` a `cmd_*.py` file out of `src/discord/` into `_deprecated/...`, the **file's relative imports will break**:

```python
# After move to src/_deprecated/hermes_migration_phase_7/cmd_approve.py
from .colors import SUCCESS          # ❌ BROKEN: no 'colors' in _deprecated package
from ._embed_helpers import ...      # ❌ BROKEN: no '_embed_helpers' in _deprecated
from .commands import is_faiz_interaction  # ❌ BROKEN: no 'commands' in _deprecated
```

These relative imports reference siblings in `src/discord/`, which is a **different package tree** after the move.

### Recommended Approach: Hybrid Strategy

#### Step 1: Use underscores, not hyphens

```bash
# RENAME the target directory BEFORE the mv:
# From: hermes-migration-phase-7 (hyphenated, not importable)
# To:   hermes_migration_phase_7 (underscores, importable)

mkdir -p src/_deprecated/hermes_migration_phase_7
```

This makes the archive path importable:
```python
from _deprecated.hermes_migration_phase_7.cmd_approve import ...
```

> **Exception**: If the directory name `hermes-migration-phase-7` is **not intended to be importable** and archived code will never be imported again (true archival/deletion), then the hyphen is fine — it just serves as a visual tombstone. However, if any test or code reference needs to import it, use underscores.

#### Step 2: Freeze relative imports before moving

Before `git mv` of any `cmd_*.py` file that uses relative imports, **convert its intra-package relative imports to absolute imports** pointing to `src.discord`:

```python
# BEFORE (relative - will break after move):
from .colors import SUCCESS
from ._embed_helpers import embed_template
from .commands import is_faiz_interaction

# AFTER (absolute - works from any location):
from src.discord.colors import SUCCESS
from src.discord._embed_helpers import embed_template
from src.discord.commands import is_faiz_interaction
```

This is a mechanical, safe transformation for any file being archived.

#### Step 3: Test import strategy — Three Options

**Option A — Update test import paths (RECOMMENDED for tests that must continue running)**

If the archived code is still needed by tests (e.g., integration tests or regression coverage):

```python
# tests/discord/test_cmd_approve.py  → update import
from _deprecated.hermes_migration_phase_7.cmd_approve import approve_callback
```

This requires the `_deprecated` directory to be importable (underscore-named).

**Option B — Move tests alongside archived code (RECOMMENDED for deprecated test suites)**

```
tests/
  _deprecated/
    hermes_migration_phase_7/
      test_cmd_approve.py
      test_cmd_deny.py
```

Add a `conftest.py` or `__init__.py` that handles sys.path. Tests import from `_deprecated.hermes_migration_phase_7` directly. Run these tests separately (e.g., `pytest tests/_deprecated/ --deselect tests/discord/`).

**Option C — Refactor tests to test new implementation (BEST for truly deprecated code)**

Instead of importing archived code, refactor the tests to validate the replacement implementation. This is the end goal of deprecation anyway.

#### Step 4: Test runner considerations

The project currently uses absolute imports like `from src.discord.cmd_mood import ...`, which means tests rely on `src/` being on `sys.path`. Ensure `_deprecated/` is also importable:

- **pytest with `--import-mode=importlib`** (recommended by pytest docs) resolves this cleanly
- Or ensure `PYTHONPATH=src` in the test runner configuration

---

## 6. Implications for Partial Migration (`src/discord/`)

### What Happens When Some `cmd_*.py` Files Are Moved

The `src/discord/` package has:

```python
# bot.py — imports from sibling cmd_*.py files
from .cmd_safeword import ...
from .cmd_status import ...
from .cmd_mood import ...
from .cmd_help import ...
# ... 10+ more relative imports
```

**Scenario**: Move `cmd_approve.py`, `cmd_deny.py` to `_deprecated/hermes_migration_phase_7/` but leave `cmd_mood.py`, `cmd_status.py`, etc. in `src/discord/`.

**Effects**:
1. `bot.py` — If it no longer references the moved files, **no change needed**. If it does, remove the `from .cmd_approve import ...` line.
2. `commands.py` — If `is_faiz_interaction` is still defined here, it stays. Archived `cmd_*.py` files that reference it must use absolute `from src.discord.commands import ...`.
3. `colors.py`, `_embed_helpers.py` — Must NOT be moved (they're shared utilities). Archived files import them via absolute path.
4. Tests that import moved `cmd_*.py` files — Update import paths (Option A) or move tests (Option B).

### Safe Partial Migration Checklist

| Step | Action | Risk |
|---|---|---|
| 1 | Create `src/_deprecated/__init__.py` | None |
| 2 | Create `src/_deprecated/hermes_migration_phase_7/__init__.py` | None (if underscores) |
| 3 | Convert relative→absolute imports in files to be moved | Low — mechanical change |
| 4 | `git mv` file → `_deprecated/hermes_migration_phase_7/` | History preserved |
| 5 | Update `bot.py` to remove `from .cmd_xxx import` | Must verify no dangling refs |
| 6 | Update test imports or move test files | Must run test suite |
| 7 | Run full test suite | High — catch any missed import paths |

---

## 7. Recommendations Summary

| Decision | Recommendation | Rationale |
|---|---|---|
| **Directory name** | Use `hermes_migration_phase_7` (underscores) | Hyphens make directory non-importable, breaking test imports |
| **Archive mechanism** | `git mv` into `src/_deprecated/hermes_migration_phase_7/` | Preserves history, provides semantic boundary, follows OSS `_deprecated/` convention |
| **Relative imports in archived files** | Convert to absolute `from src.discord.X` before `git mv` | Required for moved files to continue accessing `src.discord` utilities |
| **Test imports** | Update to `from _deprecated.hermes_migration_phase_7.cmd_X import` | Direct import works if path uses underscores |
| **Test files for archived code** | Move to `tests/_deprecated/hermes_migration_phase_7/` | Keeps test organization parallel to source |
| **Backward-compat stubs** | Optional: leave `from .cmd_approve import *` + deprecation warning in original location | Graceful transition if other modules reference the old path |
| **Pytest mode** | Use `--import-mode=importlib` or ensure `src/` on `PYTHONPATH` | Clean import resolution for both `src.*` and `_deprecated.*` |

---

## 8. Key Risks

1. **Hyphenated directory = SyntaxError on import**. The single biggest risk. If the directory name contains hyphens, any test or code that tries `import _deprecated.hermes-migration-phase-7` will crash at import time with `SyntaxError`. **Mitigation**: Use underscores.

2. **Broken relative imports after `git mv`**. Every `cmd_*.py` file using `from .colors import ...` or `from .commands import ...` will break when moved to a different package. **Mitigation**: Convert to absolute imports before moving.

3. **Dangling references in `bot.py` and `commands.py`**. If `bot.py` still tries `from .cmd_approve import ...` after `cmd_approve.py` is moved. **Mitigation**: Scan and update all import references in non-archived files.

4. **Tests that silently lose coverage**. If test imports are updated to point to archived code, those tests are now testing deprecated code paths. **Mitigation**: Plan test refactoring timeline — archived code tests should eventually test replacement implementations.

5. **`src.discord` package integrity**. Moving files out of a package mid-stream is safe as long as `__init__.py` remains and no circular imports or dangling relative references are introduced.
