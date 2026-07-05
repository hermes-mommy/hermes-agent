# Task 1 Review: Filesystem Backend

## Spec Compliance

- [x] **23 actions implemented** - PARTIAL PASS. The implementation has exactly 23 actions with correct L1/L2/L3 tier assignments. However, the action names diverge significantly from the plan. The plan specifies: `read_file, write_file, list_dir, mkdir, rmdir, delete, rename, copy, move, stat, chmod, chown, find, grep, tar, untar, zip, unzip, symlink, hardlink, read_json, write_json, watch_file`. The implementation uses: `read, list, glob, grep, exists, stat, read_bytes, read_lines, read_json, readlink, write, append, copy, move, mkdir, write_bytes, write_json, archive, extract, symlink, delete, rm_tree, chmod`. **Five plan-required actions are missing: `rename`, `chown`, `hardlink`, `watch_file`, `find`.** The tar/untar/zip/unzip are consolidated into `archive`/`extract` (acceptable consolidation, not a defect).

- [x] **Actions are async functions** - PASS. `dispatch()` is `async def`. Test `test_all_actions_are_async` confirms via `asyncio.iscoroutinefunction()`.

- [x] **Uses pathlib, shutil, tarfile, zipfile from stdlib** - PASS. All four imported at `filesystem.py:79` (pathlib), `:76` (shutil), `:78` (tarfile), `:79` (zipfile). `os` and `json` also used (stdlib). No third-party dependencies.

- [x] **No type suppression (# type: ignore)** - PASS. Grep of the implementation finds zero `# type: ignore` comments. The mypy fix commit (0d9a99a) resolved all strict-mode errors through proper variable renaming and type annotations.

- [x] **No empty catches** - PASS. All except clauses have bodies that return structured error dicts:
  - `FileNotFoundError` at line 455: returns `{"ok": False, "error": f"not found: {e}"}`
  - `PermissionError` at line 457: returns `{"ok": False, "error": f"permission denied: {e}"}`
  - `OSError` at line 463: returns `{"ok": False, "error": f"os error: {e}"}`
  - `JSONDecodeError/ValueError` at line 465: returns `{"ok": False, "error": f"parse error: {e}"}`
  The grep action has a `try/except (OSError, UnicodeDecodeError): continue` at line 145-146, which is an intentional skip of unreadable files during directory traversal -- acceptable.

- [x] **Tests follow TDD (70+ tests passing)** - PASS. Commit message states 75 tests (70 passed, 5 skipped on Windows). Actual file contains 74 test functions (68 async + 6 sync). Windows skips are platform-aware for symlink/chmod tests using `@pytest.mark.skipif`. No tests were deleted; the old 8-test file was expanded.

- [ ] **Coverage >= 80%** - UNVERIFIABLE. Commit message claims 93.45% coverage but no coverage report artifact is available in the repo. The tests cover all 23 actions plus error cases and edge cases, so coverage is likely met, but cannot be independently confirmed.

## Code Quality

- [x] **Proper error handling with specific exceptions** - PASS. Four specific exception types caught (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError/ValueError). All return structured `{"ok": False, ...}` dicts. The base class `ToolBackend.dispatch()` contract says "MUST return a dict; never raise to caller" -- this is satisfied.

- [x] **Consistent naming (snake_case for functions/vars)** - PASS. All variables use snake_case: `action_lower`, `path_str`, `grep_matches`, `glob_matches`, `file_count`, `hex_content`, `json_data`, `mode_str`. Class name is PascalCase (`FilesystemBackend`).

- [x] **Type annotations present and correct** - PASS. Key annotations: `def name(self) -> str`, `def actions(self) -> list[Action]`, `async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]`, `def is_available(self) -> bool`. The mypy fix commit added `json_data: Any` and `target_path: Path` annotations. Test file has full return type annotations on all fixtures and test functions.

- [x] **Docstrings for public functions** - PASS. Module docstring (line 1-7), class docstring (line 20-28), `dispatch()` docstring (line 68-73) all present and descriptive.

- [x] **No code duplication** - PASS. Each action handler is unique logic. Shared patterns (like `p.parent.mkdir(parents=True, exist_ok=True)`) are repeated only where contextually necessary across different write actions.

- [x] **Tests use tmp_path fixture for isolation** - PASS. Every test that does I/O uses `tmp_path: Path` parameter. No tests touch the real filesystem.

- [x] **Edge cases covered** - PASS. Tests cover:
  - Nonexistent files: `test_read_nonexistent_file`, `test_list_nonexistent`, `test_stat_nonexistent`, etc.
  - Empty inputs: `test_list_empty_directory`, `test_read_bytes_empty_file`, `test_glob_no_matches`
  - Encoding: `test_read_utf8_bom`
  - Invalid data: `test_read_json_invalid`
  - Overwrite: `test_write_overwrites_existing`
  - Parent dir creation: `test_write_creates_parent_dirs`, `test_mkdir_nested`
  - Platform-aware: `_can_symlink()` helper, `@pytest.mark.skipif(_IS_WINDOWS, ...)`

## Critical Issues (must fix)

1. **Missing 5 required actions: rename, chown, hardlink, watch_file, find.** The plan explicitly lists these 5 actions in the required 23. The implementation substitutes them with `read_bytes`, `read_lines`, `exists`, `glob`, `readlink` (also useful, but not spec'd). This is a spec violation. File: `guinvere/tools/backends/filesystem.py` lines 35-62 (action list).

2. **`archive` tar branch double-iterates files.** At lines 360-365, `tf.add(str(src), arcname=src.name)` recursively adds ALL contents of `src` to the tar. Then lines 362-365 iterate `src.rglob("*")` again just to count files. This produces a correct `files_count` for the return value, but the tar file itself contains redundant entries: the top-level directory is added once by `tf.add()`, then each file is added again because `tf.add()` on a directory is recursive. In practice `tarfile` deduplicates, but the counting loop is wasteful. File: `guinvere/tools/backends/filesystem.py` lines 358-365.

3. **`extract` uses `extractall()` without path traversal protection (Python 3.12+ security).** Both `zipfile.extractall()` (line 384) and `tarfile.extractall()` (line 388) can extract files outside the destination if archive entries contain `../` paths. Python 3.12 added `filter` parameter to `tarfile.extractall()` to mitigate this. No `filter` parameter is passed. File: `guinvere/tools/backends/filesystem.py` lines 382-389.

## Important Issues (should fix)

1. **Test file path diverges from plan.** Plan specifies `tests/guinvere/tools/test_filesystem_backend.py`; actual file is `tests/p24/test_filesystem_backend.py`. This is a minor organizational mismatch but makes the test location non-discoverable if someone follows the plan. File: `tests/p24/test_filesystem_backend.py`.

2. **Duplicate import path confusion.** The commit modifies both `guinevere/tools/backends/filesystem.py` (correct repo path) AND `guinvere/tools/backends/filesystem.py` (the P24 port path). The test imports from `guinvere.tools.backends.filesystem` (line 26 of test file) but also imports `ActionTier` from `guinevere.tools.tool_backend` (line 30). This creates a fragile cross-module dependency. File: `tests/p24/test_filesystem_backend.py` lines 26, 30.

3. **Plan specified standalone async functions; implementation uses dispatch() method.** The plan shows `async def read_file(path: str) -> str:` style functions. The implementation correctly uses the `ToolBackend.dispatch()` pattern instead, which is the right architecture. However, this divergence should be noted as an intentional improvement over the plan's sketch.

## Minor Issues (nice to have)

1. **`grep` action does substring matching, not regex.** The action description says "Search in files" and uses `if query in line` (substring). The old stub description was "Regex search in files". The current behavior is simpler and less powerful but also less error-prone. Document the intended behavior explicitly.

2. **No test for `grep` on binary/unreadable files in a directory.** The `grep` action has a `try/except (OSError, UnicodeDecodeError): continue` handler for unreadable files (line 145-146), but no test exercises this path.

3. **No test for `write_bytes` with invalid hex input.** `bytes.fromhex(hex_content)` will raise `ValueError` on invalid hex, which is caught by the outer handler, but no test verifies this.

## Verdict

**Spec Compliance:** NEEDS_REVISION

**Task Quality:** APPROVED

**Rationale:** The implementation is well-engineered: clean code, comprehensive tests (74 tests), proper error handling, type annotations, platform-aware Windows skips, and correct ToolBackend integration. However, 5 of the 23 plan-required actions are missing (rename, chown, hardlink, watch_file, find), replaced by equally useful but unspec'd alternatives. The code quality itself is excellent, but spec compliance requires either implementing the missing 5 actions or formally updating the plan to reflect the revised action list.
