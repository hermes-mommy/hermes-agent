# D1: Architecture-Implementation Audit -- Round 1

**Date:** 2026-06-25
**Auditor:** READ-ONLY subagent
**Scope:** P1-015, P1-016, P1-017, P1-018, P1-019, P1-020, P1-021 source artifacts
**Method:** Local-only (no VPS, no deploys, no secret decryption)
**Status:** COMPLETE

---

## 1. Per-Check Results Table

| ID | Check | Command | Output | Verdict | Notes |
|----|-------|---------|--------|---------|-------|
| D1-01 | llm_router.py core integrity | `python -c "from src.core.services.llm_router import LLMRouter, TaskType; print([e.value for e in TaskType])"` | `['core', 'sub_agent', 'fallback']` | **PASS** | All 3 TaskType values present. Fallback chain at lines 147-150. CostTracker imported (line 30) and wired (lines 126-131, 222-235). Metrics imported (lines 31-36) and wired (lines 238-240). |
| D1-01b | Forbidden: TODO/mock/placeholder/stub | `grep -rn "# TODO.*(mock\|placeholder\|stub)" src/core/services/llm_router.py` | 0 matches (exit 1) | **PASS** | |
| D1-01c | Forbidden: NotImplementedError | `grep -rn "raise NotImplementedError" src/core/services/llm_router.py` | 0 matches (exit 1) | **PASS** | |
| D1-02 | LLMRouter.chat() caller inventory | `grep -rn "\.chat(" src/ --include="*.py"` | 7 matches (6 active + 1 docstring) | **PASS** | All callers within legitimate loop/memory/self-improve infrastructure. No P20 bypass. See inventory table below. |
| D1-03 | cost_tracker.py | `python -c "from src.core.services.cost_tracker import CostTracker; import inspect; print(inspect.signature(CostTracker.__init__))"` | `(self, host='localhost', port=6380, db=5, username='guinevere_core', password=None, decode_responses=True)` | **PASS** | `record_cost()` has 14 Redis pipeline commands (lines 34-49). No `pass`/`return None` stubs. `check_budget()` at lines 55-66 returns full status dict. |
| D1-04 | HardStopHandler wiring | `grep -n "HardStopHandler\|hard_stop_handler" src/core/main.py` | Import:63, Instantiation:101, app.state:102, Guardian wiring:104 | **PASS** | Full lifecycle: imported, instantiated, stored on app.state, wired to LoopGuardian via `set_hard_stop_handler()`. Guardian monitor task at line 109. |
| D1-05 | prompt_loader.py | `python -c "from src.core.services.prompt_loader import load_system_prompt; print(type(load_system_prompt).__name__)"` | `function` | **PASS** | 295 lines. Safety checks validate HARD STOP, safe word, Y5/Y6, distress (lines 26-34). Memory orchestration via `get_system_prompt_with_context()`. KG injection via `_append_kg_context()`. |
| D1-06 | HardStopHandler unit tests | `python -m pytest tests/safety/test_hard_stop_handler.py -v --tb=short` | **56 passed, 0 failed** in 1.75s | **PASS** | Full output in section 4. P1-021 claims 70 total (56 deterministic + 14 model). 14 model tests need VPS/LLM credits. |
| D1-07 | Smoke tests | `ls tests/smoke/` | conftest.py, test_persona_basic.py, test_safe_word.py, test_yandere_boundary.py | **NEEDS RUNTIME VERIFICATION** | conftest.py hits `http://localhost:20128/v1` with model `ds/deepseek-v4-flash`. Requires live 9Router. Cannot run locally. |
| D1-08 | llm_metrics.py | `python -c "import src.core.services.llm_metrics; print('OK')"` | `OK` | **PASS** | 7 metric families. Server binds `127.0.0.1:9191` (line 88). See metric inventory below. |
| D1-09 | health-check-p1.sh | `diff docs/setup-evidence/P1/STEP-P1-019/health-check-p1.sh scripts/health-check-p1.sh` | Evidence has no .sh file (only health-check.txt). Phase-7 copy also missing. | **NEEDS REVIEW** | Evidence directory contains `evidence.md` and `health-check.txt` but NOT the `.sh` script. Live script exists at `scripts/health-check-p1.sh` (59 lines). Cannot diff. |
| D1-10 | FastAPI endpoints | `grep -n "@app.get\|@app.post\|@app.put\|@app.delete" src/core/main.py` | 5 direct endpoints + 3 routers included | **PASS** | `/health` at line 621. See endpoint inventory in section 6. |

---

## 2. Forbidden Pattern Scan

**Scope:** `src/core/services/*.py`, `src/core/main.py`, `tests/smoke/*.py`, `tests/safety/*.py`

| Pattern | Matches | Result |
|---------|---------|--------|
| `# TODO.*(mock\|placeholder\|stub)` | 0 | PASS |
| `raise NotImplementedError` | 0 | PASS |
| `pass #.*TODO` | 0 | PASS |

**Note:** `src/core/hard_stop_handler.py` does not exist at the plan's expected path. The actual file is `src/core/services/hard_stop_handler.py` (imported in main.py line 63). Scans were run against the correct path.

---

## 3. LLMRouter.chat() Caller Inventory

| File | Line | Call Pattern | Classification | Notes |
|------|------|-------------|----------------|-------|
| `src/loops/conversation.py` | 223 | `self._llm_router.chat(...)` | HERMESBRAIN-WIRED | Loop infrastructure, injected via constructor |
| `src/loops/phases/base.py` | 164 | `self._llm_router.chat(...)` | HERMESBRAIN-WIRED | Phase execution base, injected |
| `src/loops/reflection.py` | 83 | `self._llm_router.chat(...)` | HERMESBRAIN-WIRED | Reflection loop, injected |
| `src/loops/review_fork.py` | 213 | `self._llm_router.chat(...)` | HERMESBRAIN-WIRED | Review fork, injected |
| `src/memory/compaction.py` | 280 | `self.llm_router.chat(...)` | HERMESBRAIN-WIRED | Memory compaction, creates own LLMRouter instance (line 80) |
| `src/self_improve/optimizer.py` | 213 | `self._llm_router.chat(...)` | HERMESBRAIN-WIRED | Self-improvement optimizer, injected |
| `src/loops/phases/base.py` | 149 | (docstring reference) | N/A | Documentation only |

**Design note on compaction.py:** Creates its own `LLMRouter()` at line 80 rather than receiving an injected instance. This creates a second httpx AsyncClient independent of the main app lifecycle. All `.chat()` calls still go through the same 9Router endpoint and CostTracker (fail-closed), so there is no cost-tracking bypass. This is a design concern, not a security defect.

**Summary:** No `.chat()` calls exist in `main.py`. All callers are within loop, memory, or self-improvement infrastructure. No raw LLM path bypassing HermesBrain/P20 detected.

---

## 4. HardStopHandler Test Results (Full pytest output)

```
platform win32 -- Python 3.14.3, pytest-8.3.5, pluggy-1.6.0
plugins: anyio-4.13.0, langsmith-0.8.18, asyncio-0.25.3, cov-5.0.0, timeout-2.4.0, respx-0.23.1
asyncio: mode=Mode.AUTO

collected 56 items

tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[HARD STOP] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[hard stop] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[Hard Stop] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[HARDSTOP] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[hardstop] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[Hardstop] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[Safe Word] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[safe word] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[safeword] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[hentikan] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_detects_exact[berhenti] PASSED
tests/safety/test_hard_stop_handler.py::TestExactTriggers::test_exact_in_context PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[stop the persona now] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[pause mommy mode please] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[enough of this behavior] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[too much guinevere] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[neutral mode please] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[serious mode now] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[safe mode activate] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[I need a break] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[aku butuh jeda] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[aku capek banget] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[udah dulu ya] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[switch to neutral mode] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[go to safe mode] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[jangan pakai persona] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[lupakan persona] PASSED
tests/safety/test_hard_stop_handler.py::TestSemanticTriggers::test_detects_semantic[turn off persona] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[Hello, how are you today?] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[Aku capek hari ini, banyak kerjaan] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[What's the weather like in Jakarta?] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[Can you help me write some Python code?] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[I need to stop by the store later] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[The music is too loud in here] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[Let's take a break for coffee] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[Bisa bantu aku debug error ini?] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[That's enough code for today, good job] PASSED
tests/safety/test_hard_stop_handler.py::TestFalsePositives::test_no_false_positive[neutral is my favorite color] PASSED
tests/safety/test_hard_stop_handler.py::TestSafeModePersistence::test_already_safe_no_dup_event PASSED
tests/safety/test_hard_stop_handler.py::TestSafeModePersistence::test_normal_messages_in_safe PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_no_recovery_from_normal PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_from_safe_exact PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[resume] PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[aku sudah okay] PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[aku udah okay] PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[lanjut persona] PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[safe mode selesai] PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[lanjut] PASSED
tests/safety/test_hard_stop_handler.py::TestRecovery::test_recovery_variants[continue] PASSED
tests/safety/test_hard_stop_handler.py::TestAuditTrail::test_event_logged PASSED
tests/safety/test_hard_stop_handler.py::TestAuditTrail::test_multiple_trigger_cycle PASSED
tests/safety/test_hard_stop_handler.py::TestAuditTrail::test_neutral_response_content PASSED
tests/safety/test_hard_stop_handler.py::TestGuardDecision::test_block_on_safe_word PASSED
tests/safety/test_hard_stop_handler.py::TestGuardDecision::test_pass_through_normal PASSED
tests/safety/test_hard_stop_handler.py::TestGuardDecision::test_recovery_response PASSED
tests/safety/test_hard_stop_handler.py::TestGuardDecision::test_block_in_safe_on_normal_msg PASSED

======================== 56 passed, 1 warning in 1.75s =========================
```

**P1-021 accounting:** 70 claimed = 56 deterministic (verified above) + 14 model compliance tests (require live LLM credits through 9Router, NEEDS RUNTIME VERIFICATION).

---

## 5. Prometheus Metric Families

**Source:** `src/core/services/llm_metrics.py` (145 lines)

| Variable | Metric Name | Type | Labels | Wired To |
|----------|------------|------|--------|----------|
| `LLM_CALLS_TOTAL` | `hermes_llm_calls_total` | Counter | model, status | llm_router.py:185,238 |
| `LLM_LATENCY_SECONDS` | `hermes_llm_latency_seconds` | Histogram | model | llm_router.py:239 |
| `LLM_COST_USD_TOTAL` | `hermes_llm_cost_usd_total` | Counter | model | llm_router.py:240 |
| `FALLBACK_ACTIVATIONS_TOTAL` | `hermes_fallback_activations_total` | Counter | from_model, to_model | llm_router.py:190 |
| `SAFETY_BLOCKS_TOTAL` | `hermes_safety_blocks_total` | Counter | gate, reason | main.py (observe_safety_block) |
| `SESSION_COUNT` | `hermes_session_count` | Gauge | -- | main.py (set_session_count) |
| `MESSAGE_COUNT_TOTAL` | `hermes_message_count_total` | Counter | direction | main.py (observe_message) |

Server binds to `127.0.0.1:9191` (localhost-only, line 88). Guard prevents double-start (`_metrics_server_started` flag).

---

## 6. FastAPI Endpoint Inventory

### Direct `@app` endpoints (main.py)

| Method | Path | Line | Handler | Purpose |
|--------|------|------|---------|---------|
| GET | `/metrics` | 615 | `metrics()` | Prometheus scrape |
| GET | `/health` | 621 | `health()` | Basic health check (P1-018) |
| GET | `/health/detailed` | 626 | `health_detailed()` | Component health (loop manager, guardian, Redis, PostgreSQL, 9Router) |
| GET | `/status` | 716 | `get_status()` | P5-025 environment status |
| GET | `/` | 740 | `root()` | Welcome message |

### Included routers

| Router | Source | Endpoints |
|--------|--------|-----------|
| `router` | `src/core/api/routes.py` | GET/POST /loops, GET/POST /loops/{id}, cancel, pause, resume, priority, evidence (8 endpoints) |
| `internal_router` | `src/core/api/routes.py` | POST /alertmanager/webhook (1 endpoint) |
| `surveillance_router` | `src/surveillance/router.py` | POST surveillance webhook (1 endpoint) |

**P1-018 confirmed:** `/health` endpoint exists at line 621.

---

## 7. Bug Register

| ID | Severity | File:Line | Description |
|----|----------|-----------|-------------|
| D1-BUG-01 | Medium | `src/core/main.py:97` | `LoopManager(llm_router=None)` -- LoopManager initialized with no LLM router. Loop phases that need LLM calls will receive None. This is by design (production uses HermesBrain for autonomy), but means the P1-claimed LLM routing chain is not directly wired into the main loop manager. |
| D1-BUG-02 | Medium | `src/memory/compaction.py:80` | Creates its own `LLMRouter()` instance rather than receiving an injected instance. Creates a second httpx AsyncClient independent of main app lifecycle. Cost is still tracked via the router's internal CostTracker. |
| D1-BUG-03 | Low | `src/core/services/prompt_loader.py:16` | Hardcoded VPS path `/home/guinevere/config/hermes/system-prompt.md`. Causes FileNotFoundError on non-VPS. No fallback (unlike smoke test conftest). |
| D1-BUG-04 | Low | `scripts/health-check-p1.sh:36-48` | Script requires SOPS-encrypted Redis password decryption (VPS-only secrets). Cannot run locally. |
| D1-BUG-05 | Low | `docs/setup-evidence/P1/STEP-P1-019/` | No `health-check-p1.sh` artifact preserved in evidence. Only `health-check.txt` (output) and `evidence.md` exist. Cannot diff evidence vs live. |
| D1-BUG-06 | Cosmetic | `src/core/services/llm_router.py:77` | PRICING dict includes `cx/gpt-5.5` as dead reference pricing for a non-primary model. Could cause maintenance confusion. |
| D1-BUG-07 | Cosmetic | `src/core/main.py:663` | Redis URL in health_detailed has unusual format with port 5433 (PostgreSQL port, not Redis). Likely a copy-paste artifact in the health probe URL. |

---

## 8. Model Comparison: P1-015 Claim vs Live

| Aspect | P1-015 Claim | Live Source (253 lines) | Status |
|--------|-------------|------------------------|--------|
| Primary model | `gpt-5.5` | `ds/deepseek-v4-flash` | SUPERSEDED (Phase 6) |
| Temperature | 0.7 | 0.5 | SUPERSEDED |
| max_tokens | 16384 | 8192 | SUPERSEDED |
| Source lines | 90 | 253 | SUPERSEDED |
| CostTracker | Not in P1 | Imported + fail-closed (lines 222-235) | ADDED (Phase 6) |
| Prometheus metrics | Not in P1 | 4 observe_* calls (lines 238-240) | ADDED (Phase 6) |
| SSE stripping | Not in P1 | `_strip_sse_done()` (line 47) | ADDED (Phase 6) |
| Fallback chain | CORE -> SUB_AGENT -> FALLBACK | Same structure (lines 147-150) | PRESERVED |
| TaskType enum | 3 values | 3 values (core, sub_agent, fallback) | PRESERVED |
| 9Router routing | localhost:20128 | localhost:20128 (all 3 tiers) | PRESERVED |

---

## 9. Provider URL Verification

All three model configurations use `base_url="http://localhost:20128/v1"`:
- TaskType.CORE_REASONING: line 89
- TaskType.SUB_AGENT: line 100
- TaskType.FALLBACK: line 108

No direct provider endpoints found (no `api.openai.com`, `api.deepseek.com`, etc.). All LLM traffic routes through 9Router.

---

## 10. Overall D1 Verdict

**Verdict: PASS**

All P1-claimed implementation artifacts exist in the live source code with real implementations (no mocks, no placeholders, no stubs, no NotImplementedError). The implementation has been substantially enhanced by Phase 6 (llm_router.py rewritten from 90 to 253 lines, CostTracker integrated, metrics added) but the original P1 architecture is preserved.

**Check summary:**

| Check | Verdict |
|-------|---------|
| D1-01: TaskType + fallback chain | PASS |
| D1-02: .chat() callers | PASS (all infrastructure-wired) |
| D1-03: CostTracker | PASS |
| D1-04: HardStopHandler wiring | PASS |
| D1-05: prompt_loader | PASS |
| D1-06: HardStopHandler tests | PASS (56/56 deterministic) |
| D1-07: Smoke tests | NEEDS RUNTIME VERIFICATION |
| D1-08: Metrics registry | PASS |
| D1-09: health-check-p1.sh | NEEDS REVIEW (no evidence copy to diff) |
| D1-10: FastAPI endpoints | PASS |

**Caveats:**
- D1-07 (smoke tests) and 14 model compliance tests require VPS runtime.
- D1-09 evidence artifact gap (no .sh preserved in evidence dir).

**Downstream compatibility:**
- P19: CLEAR (cognition registry is additive)
- P20: CLEAR (all .chat() callers are infrastructure; no autonomy bypass)
- P22/P23: CLEAR (localhost binding is a constraint for distributed agents)
- P24: CLEAR (llm_router.py is the canonical LLM interface)

---

*End of D1 audit. READ-ONLY -- no files modified except this output.*
