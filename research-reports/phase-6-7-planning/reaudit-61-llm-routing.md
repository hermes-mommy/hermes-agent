# Re-Audit 6-1 Report — LLM Routing Correctness (Post-Fix)

**Re-Audit ID:** REAUDIT-61-LLM-ROUTING
**Phase:** Phase 6 — LLM Routing & Budget Enforcement
**Batch Plan:** docs/setup-evidence/hermes-migration/batch-plan-phase-6.md
**Re-Auditor:** Sisyphus-Junior (Post-Fix Verification)
**Prior Audit:** research-reports/phase-6-7-planning/audit-61-llm-routing.md
**Date:** 2026-06-05
**Status:** ✅ **PASS** — All blocking issues resolved
**Plan Status:** PLANNING ONLY — Zero Implementation (confirmed)

---

## Prior Audit Summary

| Item | Prior Verdict | Prior Evidence |
|------|--------------|----------------|
| 1. 9Router Config | ✅ PASS (1 minor) | llm_router.py missing auth (documented gap) |
| 2. Fallback Chain | ✅ PASS (1 minor) | Missing fallback activation test |
| 3. Budget Enforced | ❌ **FAIL (1 critical)** | Empty `except Exception: pass` |
| 4. No Direct Calls | ✅ PASS (1 minor) | Missing explicit grep (clean today) |
| **FINAL** | ⚠️ **NEEDS REVIEW** | **Cannot PASS until Item 3a fixed** |

---

## Re-Audit Checklist

### 1. Empty Exception Handler — CRITICAL BLOCKER Verification

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **1a. Old pattern `except Exception:` without body** | ✅ **FIXED** | `grep -rn "except Exception:"` across batch-plan-phase-6.md returns **zero matches**. The old empty handler has been removed. |
| **1b. Replacement code is logged + fail-closed** | ✅ **PASS** | Lines 666-678 now use `except Exception as exc:` → `_LOG.warning(...)` → `return {'action': 'block', ...}`. Budget counter increment failure now fails **closed** (block the call + log), not silently pass. |
| **1c. Outer handler non-empty** | ✅ **PASS** | Lines 720-728: outer `except Exception as exc:` → `_LOG.error(...)` → returns `{'action': 'pass'}`. Logged, not empty. Prior audit noted fail-open is acceptable for non-safety-critical budget hook. |
| **1d. Self-violation removed** | ✅ **FIXED** | Step 6.3 scaffold (line 256) forbids empty `except`. The plan no longer contains this forbidden pattern. Scaffold-as-contract (AGENTS.md §2.5) is no longer violated. |

**1. Summary: ✅ CRITICAL BLOCKER RESOLVED**

---

### 2. Step 6.6A CostTracker Wiring — Prior Recommendation #2

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **2a. Step 6.6A exists** | ✅ **PASS** | Line 1474: `## 11A. Step 6.6A: Wire CostTracker to LLMRouter` — inserted as a new step. |
| **2b. Wiring contract specified** | ✅ **PASS** | Lines 1496-1542: exact design contract with `import CostTracker`, `self.cost_tracker = CostTracker()`, `record_cost()` call with prompt/completion token extraction, and `raise RuntimeError` on failure. |
| **2c. Cost tracking failure is fail-closed** | ✅ **PASS** | Lines 1526-1534: `except Exception as exc:` → `logger.error(...)` → `raise RuntimeError("LLM cost tracking failed; refusing untracked spend")` — fail-closed with explicit refusal. |
| **2d. Verification scaffold for 6.6A** | ✅ **PASS** | V-6.6A.1 through V-6.6A.6 (lines 1560-1609) cover: CostTracker import, record_cost signature, pricing constants, direct-provider grep, empty handler check, fallback activation test. |

**2. Summary: ✅ ALL CHECKS PASS**

---

### 3. Fallback Activation Test — Prior Minor Finding #2

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **3a. Test requirement specified** | ✅ **PASS** | V-6.6A.6 (line 1606): "fallback activation path has an explicit test" — expects grep for fallback references in tests. |
| **3b. On-failure remediation** | ✅ **PASS** | Line 1621 On Failure: "Fallback activation not tested → Add a mocked 429/5xx/401 response test and verify the next model in the chain is attempted." |
| **3c. Evidence path** | ✅ **PASS** | Line 1626: evidence includes "fallback activation test output." |

**3. Summary: ✅ PRIOR FINDING RESOLVED**

---

### 4. Direct-Provider Bypass Grep — Prior Minor Finding #4

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **4a. grep in Step 6.6A** | ✅ **PASS** | V-6.6A.4 (line 1582): `grep -nE 'api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com' src/core/services/llm_router.py` — must return zero. |
| **4b. grep in Step 6.7** | ✅ **PASS** | Step 6.7 command 1 (line 1654-1657): broader grep across `llm_router.py`, `hermes-config/config.yaml`, `~/.hermes/config.yaml` — must return zero. |
| **4c. On-failure action** | ✅ **PASS** | Line 1620: "Remove bypass. ADR-035 requires all LLM traffic through 9Router." |

**4. Summary: ✅ PRIOR FINDING RESOLVED**

---

### 5. Hermes Auth Verification — Prior Recommendation #3

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **5a. key_env reference verified** | ✅ **PASS** | All provider blocks use `key_env: NINEROUTER_API_KEY` (not hardcoded keys). Step 6.8/6.9 config validation (lines 1880-1884) checks `key_env` references are env var based. |
| **5b. End-to-end auth test** | ✅ **PASS** | Step 6.5 (100-prompt test) uses `os.environ.get('NINEROUTER_API_KEY')` at line 1024. If auth resolution failed, all 100 tests would fail. Implicitly verifies key_env works. |
| **5c. Step 6.1 direct key test** | ⚠️ **MINOR GAP** | No explicit `hermes model test` that exercises Hermes' own key_env resolution in Step 6.1. However, Step 6.5 end-to-end test covers this. Not a blocker. |

**5. Summary: ✅ PASS (1 minor gap — end-to-end test covers auth implicitly)**

---

### 6. Plan Status Verification

| Check | Result | Evidence |
|-------|--------|----------|
| Status header | ✅ **PLANNING ONLY** | Line 3: `**Status:** PLANNING ONLY — Zero Implementation` |
| Status footer | ✅ **PLANNING ONLY** | Line 2386: `| **Status** | PLANNING ONLY — Zero Implementation |` |
| No implementation commands | ✅ **PASS** | All commands are SSH-encapsulated bash snippets guarded by execution phase. No code has been applied. |

**6. Summary: ✅ PLAN REMAINS PLANNING ONLY**

---

### 7. Step 6.3 Budget Hook — Fail-Closed Verification

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **7a. Counter increment failure = block** | ✅ **PASS** | Lines 666-678: when `r.incr(KEY_COST_COUNTER)` raises, handler returns `{'action': 'block'}` with logged error. |
| **7b. Comment explicitly states fail-closed** | ✅ **PASS** | Lines 663-665: "Budget enforcement must fail closed: if Redis cannot record the block, the budget state cannot be verified and the tool call must remain blocked." |
| **7c. Pre-condition in Step 6.7** | ✅ **PASS** | Line 1644: "Budget hook Step 6.3 fail-closed behavior verified; no empty exception-handler patterns remain in planned Phase 6 code snippets." |
| **7d. Changelog confirms fix** | ✅ **PASS** | Line 2404: "v1.1 | 2026-06-05 | Sisyphus | Planning fix: fail-closed budget hook exception..." |

**7. Summary: ✅ FAIL-CLOSED ENFORCEMENT VERIFIED**

---

## Final Re-Audit Summary

| Prior Finding | Fix Required | Status | Evidence |
|---------------|-------------|--------|----------|
| **CRITICAL:** Empty `except Exception: pass` (lines 664-667) | Replace with logged exception handler | ✅ **FIXED** | Now `except Exception as exc:` with `_LOG.warning()` + `action: 'block'` (fail-closed) |
| Minor: Missing fallback activation test | Add test requirement in plan | ✅ **FIXED** | V-6.6A.6 with explicit verification and on-failure remediation |
| Minor: Missing direct-provider grep | Add grep-based verification | ✅ **FIXED** | V-6.6A.4 + Step 6.7 command 1 |
| Minor: Missing Hermes auth verification | Verify key_env resolution | ⚠️ **MINOR GAP** | End-to-end test covers implicitly; no explicit Step 6.1 check |
| Minor: Empty prompt logging | Log empty prompt case | ⚠️ **MINOR GAP** | Display shows "(empty)" but no explicit log (unchanged from prior) |

### Verdict Transition

| Stage | Prior Verdict | Current Verdict |
|-------|--------------|----------------|
| Before fix | ❌ **FAIL** (empty except blocker) | — |
| After fix | ⚠️ NEEDS REVIEW predicted | ✅ **PASS** |

### Final Verdict

| Dimension | Verdict | Condition |
|-----------|---------|-----------|
| Empty exception handler | ✅ **FIXED** | Replaced with logged, fail-closed handler |
| Step 6.6A wired CostTracker | ✅ **PASS** | Full contract specified with fail-closed cost recording |
| Fallback activation test | ✅ **PASS** | V-6.6A.6 requires explicit mocked 429/5xx/401 test |
| Direct-provider bypass grep | ✅ **PASS** | Two grep verification points (Steps 6.6A and 6.7) |
| Fail-closed budget enforcement | ✅ **PASS** | Counter failure → block; cost recording failure → raise |
| Minor gaps (auth, empty prompt) | ⚠️ **MINOR** | Not blockers — end-to-end test covers auth; empty prompt display adequate |
| Plan status | ✅ **PLANNING ONLY** | Confirmed at header and footer |
| **FINAL** | ✅ **PASS** | All blocking issues resolved. Plan is ready for implementation wave. |

> **The Phase 6 plan now resolves all prior blocking issues.** The empty `except Exception: pass` has been replaced with a logged, fail-closed exception handler. Step 6.6A CostTracker wiring has been added with fail-closed cost recording. Fallback activation, direct-provider bypass, and empty handler checks all have explicit verification steps. The plan remains PLANNING ONLY with zero implementation applied.

---

## Evidence Files Checked

| File | Status |
|------|--------|
| `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md` (2,404 lines, v1.1) | ✅ Read fully, verified all fix points |
| `research-reports/phase-6-7-planning/audit-61-llm-routing.md` | ✅ Prior audit compared point by point |

---

## Auditor Gate Metadata

| Field | Value |
|-------|-------|
| Re-Audit ID | REAUDIT-61-LLM-ROUTING |
| Focus | LLM Routing Correctness (post-fix verification) |
| Prior Blocking Count | 1 CRITICAL (empty except) |
| Remaining Blocking Count | **0** ✅ |
| Minor Gaps | 2 (auth verification not explicit in Step 6.1; empty prompt not separately logged) |
| Next Action | Ready for implementation wave. Ensure all scaffold criteria are met during execution. |
