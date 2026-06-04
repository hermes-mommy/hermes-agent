# D11 — Known Issues and Risk Assessment

> **Audit**: P6 Final — Dimension 11
> **Date**: 2026-06-03
> **Scope**: All 24 MCP source files, 1 test file, research reports
> **Methodology**: File-by-file read + ruff/lint scan + grep analysis + dependency tracing

---

## Verdict: **NEEDS REVIEW**

No blocking issues for P7/P8 progression, but 2 HIGH items require resolution before autonomous agent loop reaches full write-access capability.

---

## 1. Known Issues Catalog

### 1.1 Severity Summary

| Severity | Count | Description |
|---|---|---|
| CRITICAL | 0 | No immediate operational blockers |
| HIGH | 2 | Git bypass vectors, Obscura CDP instability |
| MEDIUM | 6 | Stub tests, Brave key leak, grep.app API, except Exception, dead cost code |
| LOW | 3 | Acceptable except Exception ×3, admissible ruff errors |
| ADVISORY | 2 | Missing Obscura features (screenshot, playwright-core pypi) |

### 1.2 Full Issue Table

| # | Issue | Severity | File(s) | Lines | State | Risk if Unaddressed |
|---|---|---|---|---|---|---|
| **I-01** | **Git force-push bypass: `HEAD:refs/heads/main` refspec** | HIGH | `git_tool.py` | 73-107 | `_is_forbidden` does exact string match — `HEAD:refs/heads/main` ≠ `main` | Agent force-pushes to main using refspec syntax, bypassing FORBIDDEN gate |
| **I-02** | **Git force-push bypass: `--force-with-lease` flag** | HIGH | `git_tool.py` | 84, 268 | Only checks `--force` and `-f`; `--force-with-lease` not matched | Agent force-pushes to main using `--force-with-lease` (safer variant but still destructive to main) |
| **I-03** | **Git force-push bypass: case-sensitive branch names** | HIGH | `git_tool.py` | 102-106 | `protected = {"main", "master"}` — `Main`, `MASTER`, `mAin` all bypass | Agent force-pushes with case-variant branch names |
| **I-04** | **Obscura CDP v0.1.6 pre-1.0 instability** | HIGH | `obscura_cdp.py` | — | v0.1.6, 9/40 CDP domains, known issue #62 (heavy JS hangs control plane) | Browser automation unreliable; control plane hangs on JS-heavy pages; no screenshot capability |
| **I-05** | **5 stub tests — empty test bodies** | MEDIUM | `test_git_tool.py` | 213-232 | `TestAuthLevels` has 5 tests with `pass`-only bodies | Auth level bugs undetected for `git_log`, `git_diff`, `git_commit`, `git_push`, `git_push_force` |
| **I-06** | **Brave cost keys — no expireat/TTL** | MEDIUM | `brave_search.py` | 76-83 | `_record_cost` calls `incrbyfloat` but never `expireat` | Redis DB5 grows unbounded; per-day keys never cleaned up |
| **I-07** | **grep.app undocumented public API** | MEDIUM | `grep_app.py` | — | No SLA, no docs, could change/break without notice | grep_app_search tool fails silently without warning |
| **I-08** | **except Exception silent swallow ×2** | MEDIUM | `obscura_cdp.py` | 128, 151 | `obscura_navigate` and `obscura_get_markdown` catch all exceptions silently | Unexpected errors (not just timeouts) lost; diagnosis impossible |
| **I-09** | **Cost tracking dead code** | MEDIUM | `cost.py`, `budget.py` | All | `ToolCostTracker` and `BudgetEnforcer` fully implemented but never imported by any consumer | No budget enforcement; cost tracking limited to per-tool ad-hoc methods (brave, exa only) |
| **I-10** | **except Exception acceptable ×3** | LOW | `obscura_cdp.py` | 99, 178, 201 | Reraised as typed exception (ObscuraNotRunning, ElementNotFoundError) | Low — properly wrapped in domain exceptions |
| **I-11** | **except Exception acceptable ×2** | LOW | `websearch.py` | 95, 141 | Fallback orchestration — logged + fallback triggered | Low — intentional catch-all in fallback path |
| **I-12** | **Ruff E402 ×2** | LOW | `manager.py:36`, `test_postgres_tool.py:19` | 33-36, 19 | sys.path manipulation to avoid mcp package shadowing | None — justified pattern, documented |
| **I-13** | **Ruff E741 ×1** | LOW | `test_budget.py:540` | 540 | Ambiguous variable name `l` | None — cosmetic, test-only |
| **I-14** | **Ruff F841 ×2** | LOW | `test_cost.py:131,133` | 131, 133 | Unused `tool_key` and `mock_pipe` variables | None — test-only dead code, harmless |
| **I-15** | **39 LSP errors — reportMissingImports** | LOW | All files | — | Packages (`httpx`, `redis`, `playwright`, etc.) not installed in local venv | None — pre-existing, resolved at deployment (pip install) |
| **I-16** | **No `page.screenshot()` in Obscura** | ADVISORY | `obscura_cdp.py` | — | Obscura CDP has no pixel rendering; `page.screenshot()` unavailable | Visual verification tools cannot use screenshot; markdown-based extraction only |
| **I-17** | **No playwright-core PyPI for Python** | ADVISORY | `obscura_cdp.py` | — | Playwright used as full package, not lightweight core | Minor — affects potential future Python-native CDP without Node dependency |

---

## 2. Detailed Analysis — HIGH Issues

### 2.1 Git Bypass Vectors (I-01, I-02, I-03)

**Current `_is_forbidden` logic** (git_tool.py:73-107):
```python
is_push = args[0] == "push"
is_force = "--force" in args or "-f" in args
# ...
protected = {"main", "master"}
for cb in candidate_branches:
    if cb in protected:
        return True
```

**Bypass #1 — Refspec** (`HEAD:refs/heads/main`):
```bash
git push --force origin HEAD:refs/heads/main
```
Positional args: `["push", "--force", "origin", "HEAD:refs/heads/main"]`
→ `candidate_branches = ["HEAD:refs/heads/main"]`
→ `"HEAD:refs/heads/main" in {"main", "master"}` → **False** → NOT forbidden

**Bypass #2 — `--force-with-lease`**:
```bash
git push --force-with-lease origin main
```
→ `is_force = "--force" in args or "-f" in args` → `"--force-with-lease" != "--force"` → **False**
→ `is_push and is_force` → **False** → NOT forbidden

**Bypass #3 — Case sensitivity**:
```bash
git push --force origin Main
```
→ `candidate_branches = ["Main"]`
→ `"Main" in {"main", "master"}` → **False** → NOT forbidden

**Risk**: An autonomous agent could (deliberately or accidentally) craft these argument patterns to force-push to main/master. Combined impact: could destroy production branch.

### 2.2 Obscura CDP v0.1.6 Pre-1.0 (I-04)

**Facts** (from research wave):
- Version: v0.1.6 (pre-1.0)
- CDP coverage: 9 of 40+ domains implemented
- Known issue #62: heavy JavaScript pages may hang the control plane
- No `page.screenshot()` — no pixel rendering engine
- No `playwright-core` PyPI package for Python (CDP-only access)

**Current usage in Guinevere**: 4 tools (navigate, get_markdown, fill_form, click). All work via CDP protocol — no pixel rendering needed for markdown extraction or form interaction.

**Risk at deployment**:
- JS-heavy pages → control plane hangs → agent loop blocked
- Missing screenshot → no visual verification capability
- Pre-1.0 → API instability risk across upgrades

---

## 3. Detailed Analysis — MEDIUM Issues

### 3.1 Stub Tests (I-05)

`test_git_tool.py:TestAuthLevels` — 6 test methods, only 1 (test_git_status_is_read_auto) has assertions:
```python
class TestAuthLevels:
    def test_git_status_is_read_auto(self) -> None:
        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count == 6  # ← real assertion

    def test_git_log_is_read_auto(self) -> None:
        pass  # ← stub

    def test_git_diff_is_read_auto(self) -> None:
        pass  # ← stub

    def test_git_commit_is_write_notify(self) -> None:
        pass  # ← stub

    def test_git_push_is_write_notify(self) -> None:
        pass  # ← stub

    def test_git_push_force_is_destructive_approval(self) -> None:
        pass  # ← stub
```

No auth level verification exists for 5 of 6 tools. A decorator mismatch would be undetected.

### 3.2 Brave Cost Key Leak (I-06)

```python
def _record_cost(client: redis.Redis) -> None:
    today = date.today().isoformat()
    key = f"{_REDIS_KEY_PREFIX}:{today}"
    client.incrbyfloat(key, _COST_PER_SEARCH)
    # ← NO expireat / TTL
```

Contrast with `ToolCostTracker.record_tool_cost()` (cost.py:116-131) which sets `expireat` at end-of-day + 7-day grace period. Brave keys will accumulate indefinitely in Redis DB5. Each key is a small float but the unbounded growth will eventually consume memory.

### 3.3 Cost Tracking Dead Code (I-09)

| Component | File | Lines | Consumers |
|---|---|---|---|
| `ToolCostTracker` | `cost.py` | 241 | **0** |
| `BudgetEnforcer` | `budget.py` | 364 | **0** |

Both are fully implemented, tested, but never instantiated or called. The only cost tracking that actually runs is ad-hoc:
- `brave_search.py:_record_cost()` — Brave only, no TTL
- `exa_search.py:_record_cost()` — Exa only, with TTL

No tool calls `BudgetEnforcer.record_and_check()`. No tool uses `ToolCostTracker.record_tool_cost()`. Budget caps ($3/day Brave, $5/day Exa, $10/day global, $30/month absolute) exist in code but are never enforced.

### 3.4 Silent except Exception ×2 (I-08)

```python
# obscura_cdp.py:128 — obscura_navigate
except Exception:
    logger.warning("obscura_navigate_timeout", url=url)
    return {"url": url, "title": "(timed out)", "warning": "..."}
```
Catches ALL exceptions (ConnectionError, ValueError, AttributeError, etc.) and labels them as "timed out." This masks non-timeout failures.

```python
# obscura_cdp.py:151 — obscura_get_markdown
except Exception:
    logger.warning("obscura_get_markdown_timeout", url=url)
# falls through to page.content()
```
Same issue — catches everything, labels it as timeout, then continues to `page.content()` which may also fail (or may succeed with stale content).

Both lose diagnostic tracebacks and mislabel errors.

---

## 4. Risk Matrix — Top 5

| # | Risk | Probability | Impact | Composite | Mitigation |
|---|---|---|---|---|---|
| **R1** | Git force-push to main via bypass vectors | Low (0.15) — agent unlikely to craft refspecs/force-with-lease/case-variants autonomously | Critical (0.90) — destroys main branch, requires force-push recovery | **0.135** | Add refspec parsing, case-insensitive check, `--force-with-lease` detection |
| **R2** | Obscura CDP control plane hang on JS-heavy pages | Medium (0.40) — known issue #62, common on modern SPAs | Medium (0.60) — browser tools blocked, agent loop may timeout | **0.240** | Add page-level timeout circuit breaker; document fallback to `fetch` for text-only |
| **R3** | grep.app API breaks silently | Medium (0.30) — undocumented API, no SLA | Medium (0.40) — grep_app_search tool returns empty/errors | **0.120** | Add health-check endpoint probe; consider fallback to GitHub code search |
| **R4** | Brave Redis keys unbounded growth | High (0.90) — definite, every search creates key | Low (0.15) — small keys (~50 bytes), cleanup possible anytime | **0.135** | Add `expireat` with 7-day grace (match cost.py pattern) |
| **R5** | Cost tracking not enforced | High (0.80) — dead code, no tool calls BudgetEnforcer | Low-Medium (0.35) — overspending possible but manually monitorable | **0.280** | Wire BudgetEnforcer into brave_search + exa_search; add to websearch |

**R2 (Obscura hang) and R5 (no cost enforcement) are the highest composite risks** due to probability.

---

## 5. Blocking Assessment — P7 / P8

### P7: Agent Loop / Scheduling

| Concern | Blocking? | Rationale |
|---|---|---|
| Git bypass vectors | **Not blocking** — agent loop P7 focuses on scheduling infrastructure, not git operations | Fix before agent loop gets WRITE_NOTIFY/DESTRUCTIVE_APPROVAL for git |
| Obscura CDP instability | **Not blocking** — browser tools are optional for scheduling | Fix before agent loop runs full autonomous browser sessions |
| Cost tracking dead code | **Not blocking** — no cost incurred during development/testing phase | Fix before production deployment |
| Stub tests | **Not blocking** — test-only quality issue | Fix during P7 maintenance cycle |

**Verdict: P7 can proceed.** Git bypasses should be fixed before the agent loop is granted autonomous git write access.

### P8: Monitoring / Dashboard

| Concern | Blocking? | Rationale |
|---|---|---|
| Brave key leak (no TTL) | **Not blocking** — Redis is local, monitorable | Fix before production — will accumulate over weeks |
| grep.app API risk | **Not blocking** — secondary search tool | Monitor; if API breaks, prioritize fix |
| 39 LSP errors | **Not blocking** — pre-existing | Resolve when venv is set up with all dependencies |

**Verdict: P8 can proceed.** No P8 monitoring dependency on these issues.

---

## 6. Priority-Ordered Fix List

| Priority | Issue | Fix | Effort | Blocks |
|---|---|---|---|---|
| **P1** | I-01,02,03: Git bypass vectors | Add refspec parsing (`HEAD:*`, `refs/heads/*`), `.lower()` on branch name, `--force-with-lease` detection in `_is_forbidden` | Short (1-2h) | Autonomous git write |
| **P2** | I-06: Brave key leak | Add `client.expireat(key, int((datetime.now() + timedelta(days=7)).timestamp()))` in `_record_cost` | Quick (<1h) | Production |
| **P3** | I-05: 5 stub tests | Write actual auth-level assertions: inspect decorator args or trigger ForbiddenOperationError for each auth level | Short (1-2h) | None |
| **P4** | I-08: except Exception silent swallow | Replace `except Exception` with `except (TimeoutError, Exception)`, log `exc_info=True` | Quick (<1h) | Production |
| **P5** | I-09: Wire cost tracking | Import and instantiate `BudgetEnforcer` in `brave_search.py` and `exa_search.py`; call `record_and_check` before API calls | Medium (1-2d) | Production |
| **P6** | I-07: grep.app API stability | Add health-check via `GET https://grep.app/api` probe on startup; log warning if unreachable | Quick (<1h) | None |
| **P7** | I-12,13,14: Ruff errors | Fix E741 (`l` → `line`), remove F841 unused vars, document E402 exceptions with `# noqa: E402` | Quick (<1h) | None |
| **P8** | I-04: Obscura CDP v0.1.6 | Monitor v0.2.0+ releases; add page timeout circuit breaker (`asyncio.wait_for`) around goto calls | Medium (1d) | Production |
| **P9** | I-16: No screenshot | Accept limitation; document in tool description; add explicit error: "Obscura CDP does not support screenshots" | Quick (<1h) | None |

---

## 7. Optional Future Considerations

1. **Externalize Redis config**: `localhost:6380` hardcoded in 6 files — consolidate to shared config module
2. **Move `BudgetExceeded`**: Currently in `exa_search.py`, used by `budget.py` and `websearch.py` — consider `src/mcp/exceptions.py`

---

## Appendix: Evidence Sources

| Source | What Was Checked |
|---|---|
| `src/mcp/tools/obscura_cdp.py` (247 lines) | All 5 `except Exception` — 3 acceptable (re-raised), 2 silent (I-08) |
| `src/mcp/tools/websearch.py` (164 lines) | Both `except Exception` — acceptable fallback pattern |
| `src/mcp/tools/git_tool.py` (362 lines) | `_is_forbidden` → 3 bypass vectors confirmed (I-01,02,03) |
| `tests/mcp/test_git_tool.py` (665 lines) | `TestAuthLevels` → 5 stub tests confirmed (I-05) |
| `src/mcp/tools/brave_search.py` (177 lines) | `_record_cost` → no expireat confirmed (I-06) |
| `src/mcp/cost.py` (241 lines) | `ToolCostTracker` → 0 consumers (I-09) |
| `src/mcp/budget.py` (364 lines) | `BudgetEnforcer` → 0 consumers (I-09) |
| `research-reports/P6-audit/module-map.md` | 24-file inventory, dependency map, forbidden patterns |
| `ruff check` (entire src + tests) | 5 errors (2 E402, 1 E741, 2 F841) — all LOW |
| LSP diagnostics | 39 reportMissingImports — pre-existing, venv issue |
| grep `ToolCostTracker|BudgetEnforcer` across `src/` | Only definition files — no imports |

---

*D11 audit completed 2026-06-03. Verdict: NEEDS REVIEW. No P7/P8 blockers. 2 HIGH items require fix before autonomous write access.*