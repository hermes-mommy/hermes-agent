# Auditor 6-1 Report — LLM Routing Correctness

**Audit ID:** AUDIT-61-LLM-ROUTING
**Phase:** Phase 6 — LLM Routing & Budget Enforcement
**Batch Plan:** docs/setup-evidence/hermes-migration/batch-plan-phase-6.md
**Auditor:** 6-1 (LLM Routing Specialist)
**Date:** 2026-06-05
**Status:** ⚠️ NEEDS REVIEW — CANNOT PASS
**Plan Status:** PLANNING ONLY — Zero Implementation

---

## Sources Read

| # | File | Lines | Role |
|---|---|---|---|
| 1 | docs/setup-evidence/hermes-migration/batch-plan-phase-6.md | 2,235 | **Primary audit target** — Phase 6 batch plan |
| 2 | esearch-reports/phase-6-7-planning/01-llm-state.md | 153 | Current LLM state audit |
| 3 | esearch-reports/phase-6-7-planning/02-fallback-chain.md | 218 | Hermes CLI fallback feature research |
| 4 | esearch-reports/phase-6-7-planning/08-token-cost.md | 118 | Model pricing and cost methodology |
| 5 | hermes-config/config.yaml | 334 | Current deployed Hermes configuration |
| 6 | src/core/services/llm_router.py | 104 | Current LLM router implementation |

---

## Checklist Results

### 1. 9Router Config Correct?

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **1a. All LLM calls through localhost:20128/v1** | ✅ **PASS** | config.yaml: model.base_url and ninerouter.base_url both = localhost:20128/v1; llm_router.py: ALL 3 ModelConfigs use same base_url; Step 6.5: API_URL = localhost:20128/v1/chat/completions |
| **1b. NINEROUTER_API_KEY used (no hardcoded keys)** | ⚠️ **NEEDS REVIEW** | ✅ config.yaml: key_env: NINEROUTER_API_KEY (not hardcoded); Step 6.5 test uses env var. ⚠️ **llm_router.py (lines 75-84) sends requests WITHOUT Authorization header** — no Bearer  in httpx calls. Plan acknowledges (llm_router.py is deprecated) but has no step verifying Hermes native path correctly injects auth via config.yaml. |
| **1c. ninerouter provider configured correctly** | ✅ **PASS** | config.yaml lines 52-56: complete provider block matching Hermes format per 02-fallback-chain.md sect6. |

**1. Summary: ✅ PASS with 1 NEEDS REVIEW (llm_router.py missing auth — documented gap)**

---

### 2. Fallback Chain Tested?

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **2a. Primary model tested (ds/deepseek-v4-flash)** | ✅ **PASS** | Step 6.1: LLM call test; P6-PRE-11: basic call; Step 6.5: 100 prompts; V-6.2.4: post-config test. |
| **2b. Fallback activation tested** | ⚠️ **NEEDS REVIEW** | Plan configures fallback but does NOT test ACTIVATION (simulating primary failure). V-6.2.4 only proves primary works post-config. Step 6.5 targets only primary model. Recommendation: Add sub-step with invalid model name to trigger fallback. |
| **2c. gpt-5.5 401 handled** | ✅ **PASS** | Step 6.2 On Failure: "Expected behavior — document this gap." Step 6.5 test handles 401 gracefully. 01-llm-state.md documents explicitly. |
| **2d. Fallback realistic given token state** | ✅ **PASS** | Plan is honest: "effectively single-model until token refreshed." guinevere combo fallback is for routing failures — realistic. |

**2. Summary: ✅ PASS with 1 NEEDS REVIEW (missing fallback activation test)**

---

### 3. Budget Enforced?

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **3a. hooks/budget.py code correctness** | ❌ **FAIL — MUST FIX** | Hook code (lines 566-758) structurally correct EXCEPT: **Lines 664-667: Empty except Exception: pass**. Violates AGENTS.md BLOCKING Rule ("NEVER use empty catch/except") AND Step 6.3's OWN verification scaffold (forbidden pattern: empty except). This is a **self-violation** of the scaffold-as-contract model (AGENTS.md sect2.5). Fix: Replace with logged except. |
| **3b. pre_tool_call before LLM calls** | ✅ **PASS** | Step 6.4: registered under pre_tool_call with priority 100 (runs BEFORE consent_gate at 90). Catches all tool calls including LLM. |
| **3c. Thresholds correct** | ✅ **PASS** | config.yaml: 30.00/0.80/1.00. budget.py: MONTHLY_LIMIT=30.00, ALERT_THRESHOLD=0.80, BLOCK_THRESHOLD=1.00. |
| **3d. Hook registered in config.yaml** | ✅ **PASS** | Step 6.4 inserts hook entry; V-6.4.1 through V-6.4.3 verify presence, priority, YAML validity. |

**3. Summary: ❌ FAIL — 1 CRITICAL (empty except violation blocks PASS)**

---

### 4. No Direct Provider Calls?

| Sub-check | Verdict | Evidence |
|-----------|---------|----------|
| **4a. All calls through 9Router** | ✅ **PASS** | V-6.1.4: model config shows 9Router; Step 6.5: API_URL = localhost:20128; Executive summary: "route all traffic through 9Router." |
| **4b. Direct calls explicitly forbidden** | ⚠️ **NEEDS REVIEW** | ✅ Test script states "no direct provider calls" as goal. ⚠️ No explicit grep/check for alternative API endpoints (api.openai.com, api.deepseek.com). Note: grep across src/ found ZERO matches — codebase IS clean today. |
| **4c. Verification step exists** | ⚠️ **NEEDS REVIEW** | No grep-based verification step. Recommendation: Add grep -rE "api\.(openai|deepseek|anthropic)\.com" src/ hermes-config/ that must return zero. |

**4. Summary: ✅ PASS with 1 NEEDS REVIEW (missing explicit grep — codebase clean today)**

---

## Summary Table

| Checklist | Result | Key Issues |
|-----------|--------|------------|
| 1. 9Router Config | ✅ PASS (1 minor) | llm_router.py missing auth (documented gap) |
| 2. Fallback Chain | ✅ PASS (1 minor) | Missing fallback activation test |
| 3. Budget Enforced | ❌ **FAIL (1 critical)** | Empty except Exception: pass |
| 4. No Direct Calls | ✅ PASS (1 minor) | Missing explicit grep (clean today) |
| **FINAL VERDICT** | **⚠️ NEEDS REVIEW** | **Cannot PASS until Item 3a fixed** |

---

## Critical Finding: Scaffold Self-Violation

The empty except Exception: pass at batch-plan-phase-6.md lines 664-667 is a **self-violation** of the plan's own Step 6.3 verification scaffold:

> Step 6.3 scaffold (line 256): Forbidden patterns = s any, # type: ignore, **empty except**

The plan explicitly forbids empty except in Step 6.3's scaffold, then implements exactly that pattern in the Step 6.3 hook code. This violates AGENTS.md sect2.5 (scaffold-as-contract model) and sect5 (anti-pattern catalog — empty catch prohibition).

**Required pre-implementation fix:** Replace:
`python
try:
    r.incr(KEY_COST_COUNTER)
except Exception:
    pass
`
With:
`python
try:
    r.incr(KEY_COST_COUNTER)
except Exception as exc:
    _LOG.error("block_counter_failed", error=str(exc))
`

---

## Minor Findings (non-blocking)

1. **Cost tracking dual-write gap** (sect19.2 Caveat #5): If Hermes makes internal LLM calls bypassing llm_router.py, Redis cost keys won't reflect actual spend. Budget hook under-enforces. Note as Phase 7 action.

2. **Fail-open default** (lines 710-717): Hook defaults to ction: "pass" on error. Appropriate for non-safety-critical budget, but broken hook permits silent overspend.

3. **100-prompt empty prompt handling** (line 1135): Falls back to "hello" for empty prompts. Should explicitly log this case.

---

## Recommendations (pre-implementation)

1. **PRIORITY: Fix empty except** — Replace except Exception: pass with logged handler.
2. **Add fallback activation test** — After Step 6.5, sub-step with invalid model to trigger fallback.
3. **Add Hermes auth verification** — In Step 6.1, verify hermes model test resolves key_env correctly.
4. **Add direct-provider grep** — grep for alternate API endpoints, must return zero.

---

## FINAL VERDICT

| Stage | Verdict | Condition |
|-------|---------|-----------|
| Current | ❌ **FAIL** | Empty except violation blocks PASS under AGENTS.md sect2.5 and sect5 |
| After empty-except fix | ⚠️ **NEEDS REVIEW** | 3 minor items remain but do not block |
| All 4 recommendations applied | ✅ **PASS** | Ready for implementation wave |

> **Until the empty except Exception: pass at lines 664-667 is replaced with a logged exception handler, this plan CANNOT proceed to implementation.** This is a self-violation of the plan's own verification scaffold and a direct violation of AGENTS.md BLOCKING rules prohibiting empty catch/except.

---

## Evidence Files Checked

| File | Status |
|------|--------|
| docs/setup-evidence/hermes-migration/batch-plan-phase-6.md | ✅ Read fully (2,235 lines) |
| esearch-reports/phase-6-7-planning/01-llm-state.md | ✅ Read (153 lines) |
| esearch-reports/phase-6-7-planning/02-fallback-chain.md | ✅ Read (218 lines) |
| esearch-reports/phase-6-7-planning/08-token-cost.md | ✅ Read (118 lines) |
| hermes-config/config.yaml | ✅ Read (334 lines) |
| src/core/services/llm_router.py | ✅ Read (104 lines) |

---

## Auditor Gate Metadata

| Field | Value |
|-------|-------|
| Auditor ID | 6-1 |
| Focus | LLM Routing Correctness |
| Plan Status | PLANNING ONLY — Zero Implementation |
| Sub-checks | 16 total (4 checklists x 4 sub-checks each) |
| Blocking Count | 1 CRITICAL (empty except), 3 minor (NEEDS REVIEW) |
| Next Action | Fix empty except in batch-plan-phase-6.md, re-run audit before implementation wave |
