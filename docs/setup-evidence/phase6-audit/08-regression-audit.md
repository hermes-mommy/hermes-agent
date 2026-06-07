# Phase 6 Audit — 08 Regression Audit

| Field | Value |
|---|---|
| Domain | Regression |
| ADR | ADR-035 v1.0 |
| Verdict | **FAIL (pre-existing)** |
| Evidence Root | `docs/setup-evidence/phase6-audit/` |
| Source Report | `research-reports/phase6-audit/08-regression-audit.md` |

## Test Results Summary

| Test Suite | Result | Count | Notes |
|---|---|---|---|
| Phase 7 integration tests | GREEN | 139/139 | phase7 + safety latency + scanner |
| Safety tests | GREEN | All pass | No safety regressions |
| Hermes async tests | FAIL | 28 tests | `ModuleNotFoundError: pytest_asyncio` |
| Memory async tests | FAIL | 104 tests | `ModuleNotFoundError: pytest_asyncio` |
| MCP async tests | FAIL | 241 tests | `ModuleNotFoundError: pytest_asyncio` |
| Persona async tests | FAIL | 148 tests | `ModuleNotFoundError: pytest_asyncio` |
| Surveillance async tests | FAIL | 148 tests | `ModuleNotFoundError: pytest_asyncio` |

## Root Cause Analysis

```
ModuleNotFoundError: No module named 'pytest_asyncio'
```

**Root cause**: `pytest-asyncio` is NOT declared in `pyproject.toml` under `[dependency-groups] test` or `[project.optional-dependencies]`.

**Verification**:
```powershell
grep "pytest-asyncio" pyproject.toml  # 0 matches
```

**Classification**: Pre-existing infrastructure gap. NOT introduced by ADR-035.

## Impact Assessment

- **Phase 7 tests**: All 139 tests pass — these use synchronous test patterns
- **Safety tests**: All pass — synchronous patterns
- **Async suites**: Fail on import — `pytest_asyncio` module not found
- **User mandate**: "audit only — zero code changes unless critical safety regression"
- **Conclusion**: This is NOT a critical safety regression. It's a pre-existing test dependency gap.

## Evidence Artifacts

- Source report: `research-reports/phase6-audit/08-regression-audit.md` (100 lines)
- pyproject.toml: Verified `pytest-asyncio` absent from test dependencies
- VCS verification:
  - `git rev-parse --abbrev-ref HEAD` → `dev`
  - `git log --oneline --no-merges | Measure-Object -Line` → 100 commits
  - `git diff-tree --no-commit-id --name-only -r 3ceb78f | Measure-Object -Line` → 62 files
  - `git diff-tree --no-commit-id --name-only -r 3ceb78f | Select-String "aizanta"` → 0 matches

## Recommendation

Add `pytest-asyncio` to `[dependency-groups] test` in `pyproject.toml`. This is a low-risk dependency addition that unblocks the async test suites. Can be done in a follow-up maintenance PR.
