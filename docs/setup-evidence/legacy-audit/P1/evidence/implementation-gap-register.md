# P1 Implementation Gap Register

**Consolidated from:** Round-1 (D1, D2, D3, D4) + Round-2 (D1-V, D2-V, D3-V, D4-V, Completeness Critic)
**Date:** 2026-06-25
**Method:** READ-ONLY audit, no VPS access, no secret decryption
**Total gaps:** 40 (6 Critical, 10 High, 14 Medium, 7 Low, 3 Cosmetic)

---

## Classification Key

- **Critical** -- Blocks downstream phases or creates active safety risk
- **High** -- Significant architectural debt or safety-critical code gap
- **Medium** -- Confirmed drift, stale evidence, or latent bug
- **Low** -- Documentation gap, cosmetic defect, minor inconsistency
- **Cosmetic** -- Style, naming, or report artifact with no operational impact

---

## 1. ARCHITECTURAL GAPS

### GAP-01: 6/6 LLMRouter.chat() Callers Bypass P20/HermesBrain Safety Kernel
- **Severity:** Critical
- **P1 Step:** P1-015 (LLM routing)
- **Files:**
  - `src/loops/conversation.py:223`
  - `src/loops/phases/base.py:164`
  - `src/loops/reflection.py:83`
  - `src/loops/review_fork.py:213`
  - `src/memory/compaction.py:280`
  - `src/self_improve/optimizer.py:213`
- **Description:** All 6 active `LLMRouter.chat()` callers operate outside the P20 HermesBrain autonomy kernel. They bypass the consent gate (G10), tool-call auth matrix, iteration budget enforcement, and safe-mode controller. The D1 round-1 audit incorrectly classified these as "HERMESBRAIN-WIRED"; the D4 and Completeness Critic correctly reclassified them as "UNGATED." Defense-in-depth mitigations exist (fail-closed CostTracker, LoopGuardian HARD STOP, 9Router-only routing) but are not equivalent to HermesBrain gating.
- **Downstream phases:** P19 (cognition registry), P20 (life kernel), P23 (embodied operations)
- **Remediation:** Design a common LLM call gate that all loop/memory/self-improve callers must pass through. At minimum, add iteration budget enforcement to `LLMRouter.chat()` itself so that even standalone callers get rate limiting. Document the intentional separation between pipeline-stage LLM calls (bounded, operator-initiated) and autonomous kernel LLM calls (P20-gated).

### GAP-02: 5 Independent HardStopHandler Instances Create Fragmented State
- **Severity:** Critical
- **P1 Step:** P1-021 (HARD STOP handler)
- **Files:**
  - `src/core/main.py:101`
  - `src/discord/cmd_safeword.py:301`
  - `src/hermes/safety_plugin.py:440`
  - `src/channels/whatsapp/hard_stop.py:24`
  - `src/hermes_plugins/commands_high/safeword.py:52`
- **Description:** Each component creates its own `HardStopHandler()`. They do NOT share state. When a user triggers HARD STOP via Discord safeword, only the Discord handler enters SAFE state. The main app LoopGuardian, safety plugin, WhatsApp handler, and Hermes plugins handler each remain in NORMAL state. This means HARD STOP does not propagate across channels.
- **Downstream phases:** P20 (life kernel safe-mode), P23 (embodied operations)
- **Remediation:** Consolidate into a single shared `HardStopHandler` singleton. `main.py` already stores the handler on `app.state.hard_stop_handler`; all other components should receive this instance via injection, not create their own.

### GAP-03: Single Shared NINEROUTER_API_KEY Across All 3 Provider Tiers
- **Severity:** High
- **P1 Step:** P1-007 (9Router config)
- **File:** `hermes-config/config.yaml:57,67,71`
- **Description:** All three LLM provider entries (primary, fallback 1, fallback 2) use the same `key_env: NINEROUTER_API_KEY`. Compromise of this single key grants access to all model tiers through 9Router. There is no tier-level access isolation.
- **Downstream phases:** All phases using LLM routing
- **Remediation:** Evaluate whether 9Router supports per-provider API keys. If not, document the accepted risk. Consider rotating the key periodically and monitoring for unauthorized usage via CostTracker anomaly detection.

### GAP-04: Standalone LLMRouter() Instantiation With No Access Control
- **Severity:** High
- **P1 Step:** P1-015 (LLM routing)
- **File:** `src/memory/compaction.py:80`
- **Description:** `compaction.py` creates its own `LLMRouter()` instance at line 80, bypassing dependency injection. This creates a second httpx AsyncClient independent of the main app lifecycle. The `close()` method at line 295 is never called anywhere in the codebase (`grep` returns 0 matches for `compactor.(compact|close)`). If ever instantiated, this would be a resource leak. The constructor has no access control -- any module can create a standalone LLMRouter.
- **Downstream phases:** P19 (cognition registry), P23 (embodied operations)
- **Remediation:** Either make `LLMRouter.__init__` require an injection token/context, or pass LLMRouter instances via dependency injection everywhere. Remove standalone `LLMRouter()` instantiation patterns.

### GAP-05: Gmail Service HardStopHandler Is Optional
- **Severity:** Medium
- **P1 Step:** P1-021 (HARD STOP handler)
- **File:** `src/gmail/service.py:78,291-304`
- **Description:** Gmail service accepts `hard_stop_handler: HardStopHandler | None = None`. When None, it logs `gmail.service.hard_stop_disabled` and skips EmailHardStopChecker creation. Email processing can run without HARD STOP protection if the handler is not injected. The code does not verify that main.py actually injects the handler.
- **Downstream phases:** P20 (life kernel safety)
- **Remediation:** Make HardStopHandler a required dependency for Gmail service. If intentionally optional, add a startup-time assertion or warning.

### GAP-06: LLM Callers Use String task_type Instead of TaskType Enum
- **Severity:** High (latent; currently dead code)
- **P1 Step:** P1-015 (LLM routing)
- **Files:**
  - `src/loops/phases/base.py:143` -- `task_type: str = "CORE_REASONING"`
  - `src/loops/conversation.py:225`
  - `src/loops/review_fork.py:218`
  - `src/loops/reflection.py:85`
  - `src/loops/phases/research.py:109`
  - `src/loops/phases/plan_delegate.py:97`
  - `src/loops/phases/update_docs.py:126`
  - `src/loops/phases/setup_evidence.py:135`
  - `src/loops/phases/validate_audit.py:125`
- **Description:** All callers pass `task_type="CORE_REASONING"` as a string. `LLMRouter.chat()` compares against `TaskType.SUB_AGENT` (enum). The string never matches, causing every call to silently fall through to the SUB_AGENT tier via KeyError in the fallback chain. Currently dormant because `LoopManager.__init__` passes `llm_router=None` (main.py:97). If an LLM router is ever injected, all callers would: (a) use wrong tier, (b) generate false error metrics, (c) produce log spam.
- **Downstream phases:** P19 (cognition registry), P24 (Hermes fork)
- **Remediation:** Change `task_type: str` to `task_type: TaskType` and use `TaskType.CORE_REASONING` enum everywhere. Add type checking to `LLMRouter.chat()` to reject string arguments.

### GAP-07: Response Content Extraction Uses Wrong Key Path
- **Severity:** High (latent; currently dead code)
- **P1 Step:** P1-015 (LLM routing)
- **Files:**
  - `src/loops/conversation.py:247` -- `result.get("content", "")`
  - `src/loops/reflection.py:89` -- `result.get("content", "")`
  - `src/loops/review_fork.py:221` -- `response.get("content", "")`
  - `src/loops/phases/research.py:126` -- `result.get("content", "")`
  - `src/loops/phases/base.py:174` -- `usage.get("input_tokens", 0)` (should be `prompt_tokens`)
  - `src/loops/phases/validate_audit.py:130`
  - `src/loops/phases/plan_delegate.py:102`
  - `src/loops/phases/delegate.py:221`
  - `src/loops/phases/update_docs.py:143`
  - `src/loops/phases/execute.py:222`
  - `src/loops/phases/setup_evidence.py:152`
- **Description:** `LLMRouter.chat()` returns raw OpenAI-compatible JSON: `{"choices":[{"message":{"content":"..."}}],"usage":{"prompt_tokens":...}}`. Callers use `result.get("content", "")` which returns `""` (no top-level "content" key). Similarly, `usage.get("input_tokens", 0)` returns 0 (key is `prompt_tokens`). Only `src/memory/compaction.py:285` uses the correct pattern. Currently dormant due to `llm_router=None`.
- **Downstream phases:** P19 (cognition registry), P24 (Hermes fork)
- **Remediation:** Fix all callers to extract content via `result["choices"][0]["message"]["content"]` and usage via `prompt_tokens`/`completion_tokens`. Add a shared response-parsing utility to avoid repeated raw-dict access.

---

## 2. SECURITY HARDENING REGRESSIONS

### GAP-08: guinevere-core.service Lost NoNewPrivileges and ProtectHome
- **Severity:** Critical
- **P1 Step:** P1-018 (FastAPI skeleton + systemd)
- **Files:**
  - `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` (evidence snapshot)
  - `vps-mirror/systemd-live/guinevere-core.service` (live)
- **Description:** 5 property divergences between evidence and live:
  1. `NoNewPrivileges=true` -- REMOVED from live
  2. `ProtectHome=read-only` -- REMOVED from live
  3. `ProtectSystem` changed from `strict` to `full`
  4. `EnvironmentFile` added (required, not a regression)
  5. `ReadWritePaths` expanded with `.hermes` (required, not a regression)
  The removal of NoNewPrivileges and ProtectHome is a security hardening regression.
- **Downstream phases:** All phases running on VPS
- **Remediation:** Restore `NoNewPrivileges=true` and `ProtectHome=read-only` in the live service unit. If `ProtectHome=read-only` conflicts with write needs, use `ReadWritePaths` for specific directories instead of removing ProtectHome entirely.

### GAP-09: guinevere-9router.service Has Zero Security Hardening
- **Severity:** High
- **P1 Step:** P1-006/P1-007 (9Router install/config)
- **File:** `vps-mirror/systemd-live/guinevere-9router.service`
- **Description:** The 9Router service unit has NO `NoNewPrivileges`, NO `ProtectSystem`, NO `ProtectHome`, NO `ProtectKernelModules`, NO `ProtectKernelTunables`, NO `RestrictAddressFamilies`. Every other service in the fleet (core, scheduler, mcp, loops, obscura, surveillance, monitoring) has at least `ProtectSystem=full`. The 9Router has nothing.
- **Downstream phases:** All phases using 9Router for LLM routing
- **Remediation:** Add at minimum: `NoNewPrivileges=true`, `ProtectSystem=full`, `ProtectHome=read-only`. The round-1 D3-06 PASS verdict ("security posture is reasonable") was incorrect; this should have been flagged.

---

## 3. STALE ARTIFACT DRIFT

### GAP-10: P1-015 llm_router.py Evidence Snapshot Is 90 Lines; Live Is 253 Lines
- **Severity:** Medium
- **P1 Step:** P1-015 (LLM routing)
- **Files:**
  - `docs/setup-evidence/P1/STEP-P1-015/llm_router.py` (90-line snapshot)
  - `src/core/services/llm_router.py` (253 lines, live)
- **Description:** The evidence snapshot captured the original P1 implementation (90 lines, `gpt-5.5` primary, temperature 0.7, max_tokens 16384). The live file has been rewritten by Phase 6 (253 lines, `deepseek-v4-flash` primary, temperature 0.5, max_tokens 8192, CostTracker integrated, Prometheus metrics added, SSE stripping added). The P1 architecture (TaskType enum, fallback chain, 9Router-only routing) is preserved.
- **Downstream phases:** N/A (evidence integrity only)
- **Remediation:** Add a note to the P1-015 evidence directory explaining the drift and referencing the Phase 6 rewrite commit (`e2eb279`).

### GAP-11: P1-018 guinevere-core.service Evidence Differs From Live (Beyond Hardening)
- **Severity:** Medium
- **P1 Step:** P1-018 (FastAPI skeleton + systemd)
- **File:** `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`
- **Description:** The evidence snapshot shows a different security posture and configuration than the live unit. Beyond the hardening regression (GAP-08), the live unit adds `EnvironmentFile` and expands `ReadWritePaths`. The evidence snapshot is stale for audit purposes.
- **Downstream phases:** N/A (evidence integrity only)
- **Remediation:** Update the evidence snapshot or add a drift note explaining all 5 divergences.

### GAP-12: P1-020 Redis Key Snapshot Is Stale (11 Keys vs 13+ Live Patterns)
- **Severity:** Medium
- **P1 Step:** P1-020 (Redis cost tracking)
- **Files:**
  - `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` (11 keys)
  - `src/core/services/cost_tracker.py:34-49` (13+ key patterns)
- **Description:** P1-020 evidence captured 11 Redis keys. Current `cost_tracker.py` `record_cost()` writes 15 Redis pipeline commands creating ~13 unique base key patterns (5 cost + 8 token tracking), plus dynamically-created daily/monthly keys. The evidence was accurate for the P1 epoch but is stale for current state. Git log shows only one commit for this file (`f6912b2 refactor(phases): restructure P9-P22`).
- **Downstream phases:** P20 (life kernel cost monitoring)
- **Remediation:** Add a note to the P1-020 evidence directory documenting the key pattern expansion. Optionally re-capture current Redis state.

### GAP-13: Prometheus Port Drift (9091 in Evidence vs 9191 Live)
- **Severity:** Low
- **P1 Step:** P1-005 (config)
- **Files:**
  - `docs/setup-evidence/P1/STEP-P1-005/config.yaml:77` (port 9091)
  - `hermes-config/config.yaml` (metrics_port 9191)
  - `src/core/services/llm_metrics.py:88` (binds to 9191)
- **Description:** P1 evidence config declares `port: 9091` for Prometheus metrics. The live config and code both use 9191. The evidence snapshot captured an older config that predates the final metrics port decision.
- **Downstream phases:** N/A (evidence accuracy only)
- **Remediation:** Add a drift note to the P1-005 evidence directory.

### GAP-14: 3 Evidence Files Have UTF-16LE Encoding Defect
- **Severity:** Low
- **P1 Step:** P1-015, P1-016, P1-019
- **Files:**
  - `docs/setup-evidence/P1/STEP-P1-015/import-test.txt` (496 bytes, UTF-16LE)
  - `docs/setup-evidence/P1/STEP-P1-016/system-prompt-loaded.txt` (1206 bytes, UTF-16LE)
  - `docs/setup-evidence/P1/STEP-P1-019/health-check.txt` (962 bytes, UTF-16LE)
- **Description:** All 3 files are genuine VPS command output captured with wrong encoding (UTF-16LE BOM, `ff fe`). Content is fully recoverable via UTF-16 decode. Not fabrication.
- **Downstream phases:** N/A (evidence integrity only)
- **Remediation:** Re-capture during maintenance cycle with explicit `script` encoding control. Or convert in-place to UTF-8.

### GAP-15: P1-005 config.yaml Is a Structural Reference, Not Deployed Runtime Config
- **Severity:** Low
- **P1 Step:** P1-005 (config)
- **File:** `docs/setup-evidence/P1/STEP-P1-005/config.yaml` (81 lines)
- **Description:** This file has a clean 9-section schema (agent, llm, memory, loop, safety, budget, tools, messaging, monitoring) with `version: "0.1.0"`. The live `hermes-config/config.yaml` (393 lines) has a completely different schema (Gateway config). No document conflates them, but the evidence snapshot documents an early structural design, not the deployed runtime configuration.
- **Downstream phases:** N/A (documentation clarity only)
- **Remediation:** Add a note to the P1-005 evidence directory clarifying this is a structural reference config, not the live runtime config.

---

## 4. MISSING TESTS

### GAP-16: prompt_loader.py Has Zero Dedicated Tests (295 Lines, Safety-Critical)
- **Severity:** Critical
- **P1 Step:** P1-016 (SystemPromptMaster)
- **File:** `src/core/services/prompt_loader.py` (295 lines)
- **Description:** This is a safety-critical module that validates HARD STOP, safe word, Y5/Y6, and distress in system prompts (lines 26-34). It also handles memory orchestration via `get_system_prompt_with_context()` and KG injection via `_append_kg_context()`. It has ZERO dedicated unit tests. Only indirect coverage exists via smoke tests (`tests/smoke/`) which require a live VPS with 9Router. No round-1 auditor flagged this gap.
- **Downstream phases:** P4 (persona engine), P5 (loop guardian), P19 (cognition registry)
- **Remediation:** Create `tests/services/test_prompt_loader.py` with deterministic tests for all 7 safety check functions. Tests should verify: (a) system prompt file loading, (b) HARD STOP keyword detection, (c) safe word detection, (d) Y5/Y6 boundary detection, (e) distress signal detection, (f) memory context injection, (g) KG context appending.

### GAP-17: cost_tracker.py Has Zero Dedicated Tests (78 Lines)
- **Severity:** Medium
- **P1 Step:** P1-020 (Redis cost tracking)
- **File:** `src/core/services/cost_tracker.py` (78 lines)
- **Description:** Covered indirectly by `tests/hermes/test_llm_router_cost.py` (mocks CostTracker). No test verifies actual Redis pipeline writes. The `record_cost()` method has 15 Redis pipeline commands -- none are integration-tested against a real or mock Redis instance.
- **Downstream phases:** P20 (life kernel cost monitoring)
- **Remediation:** Create `tests/services/test_cost_tracker.py` with a mock Redis client that verifies pipeline commands match expected key patterns and values.

### GAP-18: 14 Model Compliance Tests Unverified (VPS-Only)
- **Severity:** Medium
- **P1 Step:** P1-021 (HARD STOP handler)
- **Files:**
  - `tests/safety/test_hard_stop_model.py` (14 tests, VPS-only)
- **Description:** P1-021 claims 70/70 tests (56 deterministic + 14 model). The 56 deterministic tests are confirmed passing locally. The 14 model compliance tests require live LLM credits through 9Router and cannot be verified locally. These tests verify that the LLM respects HARD STOP directives at the model level.
- **Downstream phases:** P4 (persona engine safety)
- **Remediation:** Verify on VPS. Consider adding a mock-LLM variant of these tests that can run locally.

### GAP-19: Smoke Tests Cannot Run Locally
- **Severity:** Medium
- **P1 Step:** P1-017 (persona smoke tests)
- **Files:**
  - `tests/smoke/test_persona_basic.py`
  - `tests/smoke/test_safe_word.py`
  - `tests/smoke/test_yandere_boundary.py`
  - `tests/smoke/conftest.py` (hits `http://localhost:20128/v1`)
- **Description:** All smoke tests require a live 9Router instance. conftest.py hardcodes `http://localhost:20128/v1` with model `ds/deepseek-v4-flash`. Cannot run on developer machines or CI without VPS tunneling.
- **Downstream phases:** All phases requiring smoke test verification
- **Remediation:** Add mock-LLM smoke test variants that verify persona behavior without requiring live 9Router. Keep VPS-only tests as integration tests.

### GAP-20: No Round-1 Auditor Ran Full Test Suite Locally
- **Severity:** High (audit process gap)
- **P1 Step:** All
- **Description:** All 4 round-1 dimensions verified test existence by reading files or running only `test_hard_stop_handler.py`. No auditor ran: `test_llm_router_cost.py`, `test_llm_metrics.py`, `test_hard_stop_comprehensive.py`, `test_hard_stop_latency.py`, or any test with `--tb=short` to verify no import errors. Only 1 of 7+ P1-related test files was actually executed.
- **Downstream phases:** N/A (audit quality)
- **Remediation:** Run all P1-related test files locally and report pass/fail counts in a follow-up verification pass.

### GAP-21: Missing `import re` in sandbox.py (Latent NameError)
- **Severity:** Medium
- **P1 Step:** P1-015 (LLM routing, broad code quality)
- **File:** `src/loops/sandbox.py:345,351`
- **Description:** `_parse_pytest_output()` uses `re.search()` and `re.finditer()` but the module has no `import re` statement. This would cause a `NameError` at runtime when the method is called after successful pytest execution. Latent bug -- not security-related.
- **Downstream phases:** P23 (embodied operations, sandbox execution)
- **Remediation:** Add `import re` to `src/loops/sandbox.py`.

---

## 5. VPS-ONLY VERIFICATION GAPS

### GAP-22: 24 Runtime Verification Items Require VPS Access (R01-R25)
- **Severity:** High
- **P1 Step:** P1-001 through P1-021
- **Description:** 24 of 25 runtime verification items (R01-R25, excluding R18 which is local) require VPS SSH access and cannot be confirmed during this read-only audit. These include:
  - Service status checks (guinevere-core, guinevere-9router)
  - Docker container status (PostgreSQL, Redis)
  - Port binding verification (8000, 5433, 6380)
  - Database connectivity (PostgreSQL SELECT 1, Redis PING)
  - LLM routing end-to-end (core reasoning, sub-agent, fallback)
  - System prompt presence and content verification
  - Redis cost tracking key verification
  - Prometheus metrics endpoint verification
- **Downstream phases:** All
- **Remediation:** Schedule a VPS verification pass with an operator who has SSH access. Document results in a supplementary evidence file.

### GAP-23: health-check-p1.sh Requires SOPS Decryption (VPS-Only)
- **Severity:** Low
- **P1 Step:** P1-019 (health checks)
- **File:** `scripts/health-check-p1.sh:36-48`
- **Description:** Health check script requires SOPS-encrypted Redis password decryption via `SOPS_AGE_KEY_FILE` and `sops -d`. Cannot run locally. No evidence artifact (.sh) preserved in the P1 evidence directory -- only the output (`health-check.txt`) and `evidence.md`.
- **Downstream phases:** N/A (infrastructure verification)
- **Remediation:** Preserve the .sh script in the evidence directory. Consider a local-friendly version that uses mock credentials.

### GAP-24: prompt_loader.py Hardcoded VPS Path
- **Severity:** Low
- **P1 Step:** P1-016 (SystemPromptMaster)
- **File:** `src/core/services/prompt_loader.py:16`
- **Description:** `SYSTEM_PROMPT_PATH = Path("/home/guinevere/config/hermes/system-prompt.md")`. Raises `FileNotFoundError` on any non-VPS machine. Smoke test conftest has a fallback (`REPO_SYSTEM_PROMPT_PATH`), but prompt_loader.py does not.
- **Downstream phases:** P4 (persona engine), all local development
- **Remediation:** Make the path configurable via environment variable with VPS path as default. Or add a fallback to a repo-relative path.

---

## 6. EVIDENCE STRUCTURE GAPS

### GAP-25: 7 of 21 STEP Directories Missing (33% Structural Gap)
- **Severity:** High
- **P1 Step:** P1-008 through P1-014
- **Description:** 14 of 21 STEP directories exist. The 7 missing are:
  - P1-008 (GPT-5.5 provider setup) -- evidence in migration-9router/evidence.md
  - P1-009 (GPT-5.5 connectivity) -- evidence in migration-9router/evidence.md (but not listed in doc-sync line)
  - P1-010 (DeepSeek V4 Flash setup) -- evidence in migration-9router/evidence.md
  - P1-011 (DeepSeek connectivity) -- evidence in migration-9router/evidence.md
  - P1-012 (Ollama install) -- SKIPPED per Faiz directive, ADR-028
  - P1-013 (Ollama model pull) -- SKIPPED per Faiz directive, ADR-028
  - P1-014 (Ollama fallback test) -- SKIPPED per Faiz directive, ADR-028
  P1-008/009/010/011 have NO dedicated evidence directories. Their evidence exists only in `migration-9router/evidence.md`, a different file in a different format.
- **Downstream phases:** N/A (audit evidence integrity)
- **Remediation:** Create stub STEP directories (P1-008 through P1-011) with at minimum a reference note bridging to migration-9router/evidence.md. The Completeness Critic verified that batch-plan-006-007 does NOT cover P1-008/009/010/011 (it only covers P1-006/007).

### GAP-26: migration-9router/evidence.md Omits P1-009 From Doc-Sync Claim
- **Severity:** Low
- **P1 Step:** P1-009 (GPT-5.5 connectivity)
- **File:** `migration-9router/evidence.md:92`
- **Description:** The doc-sync line at line 92 lists P1-008 + P1-010 + P1-011 as "effectively satisfied" but omits P1-009. The actual GPT-5.5 connectivity evidence IS present at lines 56-60 ("GPT-5.5 -- REAL RESPONSE" with curl output). This is a documentation labeling error, not an evidence gap.
- **Downstream phases:** N/A
- **Remediation:** Fix line 92 to include P1-009.

### GAP-27: P1-006/P1-007 Evidence Thinner Than Planned
- **Severity:** Low
- **P1 Step:** P1-006, P1-007
- **Files:**
  - `docs/setup-evidence/P1/STEP-P1-006/` -- 2 files (evidence.md, 9router-install.txt); plan expected 5
  - `docs/setup-evidence/P1/STEP-P1-007/` -- 1 file (evidence.md); plan expected 4
- **Description:** 5 of 9 planned evidence files were not created. The batch plan (batch-plan-006-007.md) was more ambitious than execution delivered. Missing: nodejs-install.txt, 9router-systemd-unit.md, 9router-env-reference.md, env-9router-created.md, 9router-status.txt, 9router-providers-configured.md.
- **Downstream phases:** N/A (evidence completeness)
- **Remediation:** Either create the missing files or update the batch plan to reflect actual delivery.

---

## 7. DOCUMENTATION CONSISTENCY GAPS

### GAP-28: PROGRESS.md P1-021 Test Count Inflated by 103%
- **Severity:** Medium
- **P1 Step:** P1-021 (HARD STOP handler)
- **Files:**
  - `PROGRESS.md:132` -- "142/142 tests PASS (56 handler + 86 comprehensive)"
  - `docs/setup-evidence/P1/STEP-P1-021/evidence.md` -- "70/70 tests PASS (56 handler + 14 model)"
  - `CHECKLIST.md:218` -- "70/70 PASS"
- **Description:** PROGRESS.md claims 142/142 tests for P1-021. The P1 evidence snapshot claims 70/70. The 86 "comprehensive" tests were added in later phases (P4-017, P6-002/P6-003, P6-007). CHECKLIST.md is consistent with evidence (70/70). The PROGRESS.md figure inflates P1's test coverage claim by 103%.
- **Downstream phases:** N/A (documentation accuracy)
- **Remediation:** Change PROGRESS.md P1-021 to "70/70 PASS (56 handler + 14 model; 86 comprehensive added in P4/P6)" or reconcile with a footnote.

### GAP-29: docs/README.md Has No P1 Entry (But Has P13, P16)
- **Severity:** Low
- **P1 Step:** N/A (documentation index)
- **File:** `docs/README.md`
- **Description:** The main docs index has entries for P12, P13, P16 setup-evidence subdirectories but no P1 entry. The index selectively covers some setup-evidence directories but not others. Inconsistent coverage policy.
- **Downstream phases:** N/A
- **Remediation:** Add a P1 entry to docs/README.md for consistency.

### GAP-30: CHECKLIST P1 Section 3.6 Says "20 Steps" (Should Be 21)
- **Severity:** Cosmetic
- **P1 Step:** N/A (documentation)
- **File:** `CHECKLIST.md:232`
- **Description:** P1 "Phase Complete Criteria" lists "All 20 steps verified" but P1 has 21 steps. Off-by-one in completion criteria text.
- **Downstream phases:** N/A
- **Remediation:** Fix text to "All 21 steps verified."

### GAP-31: CHECKLIST Phase Complete Criteria Items Unchecked
- **Severity:** Cosmetic
- **P1 Step:** N/A (documentation)
- **File:** `CHECKLIST.md:232-238`
- **Description:** P1 Phase Complete Criteria has 5 unchecked items (`- [ ]`) despite P1 being marked 21/21 complete. Systemic pattern across all phases -- Phase Complete Criteria items are never checked off.
- **Downstream phases:** N/A
- **Remediation:** Check off the criteria items or add a note explaining the convention.

---

## 8. CODE QUALITY / LATENT BUGS

### GAP-32: LoopManager Initialized With llm_router=None
- **Severity:** Medium
- **P1 Step:** P1-015 (LLM routing)
- **File:** `src/core/main.py:97`
- **Description:** `LoopManager(llm_router=None)` -- the LoopManager is initialized with no LLM router. This means GAP-06 and GAP-07 (string task_type, wrong content extraction) are dormant. There is no comment or ADR explaining why the router is None. If an LLM router is ever injected, the latent bugs in all loop callers would activate.
- **Downstream phases:** P19 (cognition registry), P24 (Hermes fork)
- **Remediation:** Add a comment explaining the None router is intentional. Or wire the router and fix GAP-06/GAP-07 first.

### GAP-33: ContextCompactor Is Dead Code With Resource Leak
- **Severity:** Medium
- **P1 Step:** P1-015 (LLM routing)
- **File:** `src/memory/compaction.py:52`
- **Description:** `ContextCompactor` is defined and exported (`src/memory/__init__.py:68`) but NEVER instantiated anywhere in the codebase. It creates its own `LLMRouter()` at line 80 (GAP-04) and has a `close()` method (line 295) that is never called. If ever instantiated without calling close(), it would leak an httpx AsyncClient.
- **Downstream phases:** P19 (cognition registry)
- **Remediation:** Either remove the dead code or add a deprecation notice. If planning to use it, fix the LLMRouter injection and ensure close() is called.

### GAP-34: CostTracker Redis Password Defaults to Empty String
- **Severity:** Low
- **P1 Step:** P1-020 (Redis cost tracking)
- **File:** `src/core/services/cost_tracker.py:21`
- **Description:** `password=password or os.environ.get("REDIS_PASSWORD", "")` -- if neither the constructor arg nor `REDIS_PASSWORD` env var is set, the password defaults to `""` (empty string). On a VPS with Redis ACL requiring password auth, this would cause a silent auth failure. The empty-string default masks misconfiguration. A `None` or explicit error would be safer.
- **Downstream phases:** P20 (life kernel cost monitoring)
- **Remediation:** Default to `None` and raise a configuration error if Redis ACL requires a password but none is provided.

### GAP-35: compaction.py _summarize Returns Empty String on LLM Failure
- **Severity:** Low
- **P1 Step:** P1-015 (LLM routing)
- **File:** `src/memory/compaction.py:293`
- **Description:** When LLM summarization fails, `_summarize` returns `""` (empty string). This means compacted conversation history gets an empty summary message, which could degrade conversation quality. Compaction is only triggered at 100k tokens, so this is low-frequency.
- **Downstream phases:** P19 (cognition registry, memory compaction)
- **Remediation:** Return a sentinel value or raise a non-fatal error that triggers a retry or fallback compaction strategy.

### GAP-36: LLMRouter PRICING Dict Has Dead Model Reference
- **Severity:** Cosmetic
- **P1 Step:** P1-015 (LLM routing)
- **File:** `src/core/services/llm_router.py:77`
- **Description:** PRICING dict includes `cx/gpt-5.5` as a dead reference for a non-primary model. Could cause maintenance confusion.
- **Downstream phases:** N/A
- **Remediation:** Remove dead model entries or add comments explaining they are historical references.

---

## 9. AUDIT PROCESS GAPS

### GAP-37: D1 Classified .chat() Callers as "HERMESBRAIN-WIRED" (Incorrect)
- **Severity:** High (audit correctness)
- **P1 Step:** N/A (audit quality)
- **Description:** The D1 round-1 audit classified all 6 `.chat()` callers as "HERMESBRAIN-WIRED" and assigned PASS. The Completeness Critic and D4 correctly identified these as "UNGATED" (bypassing P20 safety kernel). D1 conflated "uses dependency injection" with "routed through P20 safety kernel." This weakened D1's overall PASS verdict.
- **Downstream phases:** N/A
- **Remediation:** Re-classify D1-02 from PASS to NEEDS-REVIEW. D4's assessment is more accurate.

### GAP-38: D3-06 Assessed 9Router Service as PASS ("Reasonable Security Posture")
- **Severity:** Medium (audit correctness)
- **P1 Step:** N/A (audit quality)
- **Description:** Round-1 D3-06 assessed `guinevere-9router.service` as PASS with "security posture is reasonable." The service has ZERO security hardening directives. Round-2 correctly identified this as a Medium-severity finding (GAP-09). The round-1 PASS verdict was too lenient.
- **Downstream phases:** N/A
- **Remediation:** Retroactively correct D3-06 verdict from PASS to NEEDS-REVIEW.

### GAP-39: D1-BUG-07 Partially Refuted by Round-2
- **Severity:** Cosmetic (audit quality)
- **P1 Step:** N/A (audit quality)
- **Description:** Round-1 D1-BUG-07 claimed "Redis URL in health_detailed has unusual format with port 5433 (PostgreSQL port, not Redis)." Round-2 correctly refuted this: port 5433 IS the PostgreSQL port used throughout the codebase. The real bug is the literal `***` placeholder password and incorrect indentation, not the port number. Round-1 drew the wrong conclusion from correct data.
- **Downstream phases:** N/A
- **Remediation:** Document the correction.

### GAP-40: P1 Cost ($15) Is Unitemized
- **Severity:** Low (audit completeness)
- **P1 Step:** N/A
- **Description:** CHECKLIST.md and PROGRESS.md claim P1 cost was $15/mo. Based on actual API calls (2 curl tests with max_tokens 10/100, 14 model compliance tests, 9 smoke tests through GPT-5.5), the estimated actual API credit cost is $2-5. The $15 figure likely includes the 9Router migration provider tests (26 provider connections). No round-1 auditor verified cost accuracy.
- **Downstream phases:** N/A (budget tracking)
- **Remediation:** Add itemized cost breakdown or accept the $15 as an operator-reported estimate.

---

## 10. REMEDIATION PRIORITY MATRIX

### Immediate (Before P1 Closure)

| Gap | Action | Effort |
|-----|--------|--------|
| GAP-08 | Restore NoNewPrivileges + ProtectHome in guinevere-core.service | Low |
| GAP-09 | Add security hardening to guinevere-9router.service | Low |
| GAP-16 | Create test_prompt_loader.py (safety-critical gap) | Medium |
| GAP-21 | Add `import re` to sandbox.py | Trivial |
| GAP-28 | Fix PROGRESS.md P1-021 test count | Trivial |

### Before Loop Autonomy Activates (P19/P24 Prerequisites)

| Gap | Action | Effort |
|-----|--------|--------|
| GAP-01 | Design LLM call gate for loop/memory callers | High |
| GAP-02 | Consolidate HardStopHandler into singleton | Medium |
| GAP-06 | Fix task_type string to TaskType enum | Low |
| GAP-07 | Fix content extraction key paths | Low |
| GAP-32 | Wire LLM router into LoopManager (or document why None) | Low |

### Architectural Debt (Any Phase)

| Gap | Action | Effort |
|-----|--------|--------|
| GAP-03 | Evaluate per-tier API keys in 9Router | Investigation |
| GAP-04 | Remove standalone LLMRouter() instantiation | Low |
| GAP-05 | Make Gmail HardStopHandler required | Low |
| GAP-17 | Create test_cost_tracker.py | Medium |
| GAP-22 | VPS runtime verification pass | Medium |
| GAP-33 | Remove or deprecate ContextCompactor dead code | Trivial |
| GAP-34 | Fix CostTracker empty-password default | Trivial |

### Documentation Cleanup (Any Phase)

| Gap | Action | Effort |
|-----|--------|--------|
| GAP-10 | Add drift note to P1-015 evidence | Trivial |
| GAP-11 | Update P1-018 evidence or add drift note | Trivial |
| GAP-12 | Add drift note to P1-020 evidence | Trivial |
| GAP-13 | Add drift note to P1-005 evidence | Trivial |
| GAP-14 | Re-encode or convert 3 UTF-16LE files | Trivial |
| GAP-15 | Clarify P1-005 config is structural reference | Trivial |
| GAP-25 | Create stub STEP dirs P1-008 through P1-011 | Low |
| GAP-26 | Fix migration-9router doc-sync line | Trivial |
| GAP-27 | Update batch plan or create missing evidence files | Low |
| GAP-29 | Add P1 entry to docs/README.md | Trivial |
| GAP-30 | Fix "20 steps" to "21 steps" in CHECKLIST | Trivial |
| GAP-31 | Check off Phase Complete Criteria items | Trivial |

---

## 11. CROSS-REFERENCE: FINDINGS BY P1 STEP

| P1 Step | Gaps | Highest Severity |
|---------|------|-----------------|
| P1-005 (config) | GAP-13, GAP-15 | Low |
| P1-006/007 (9Router) | GAP-09, GAP-27 | High |
| P1-008-011 (provider setup) | GAP-25, GAP-26 | High |
| P1-012-014 (Ollama skip) | GAP-25 (SKIPPED, justified) | Low |
| P1-015 (LLM routing) | GAP-01, GAP-04, GAP-06, GAP-07, GAP-10, GAP-21, GAP-32, GAP-33, GAP-35, GAP-36 | Critical |
| P1-016 (SystemPromptMaster) | GAP-16, GAP-24 | Critical |
| P1-017 (smoke tests) | GAP-19 | Medium |
| P1-018 (FastAPI + systemd) | GAP-08, GAP-11 | Critical |
| P1-019 (health checks) | GAP-14, GAP-23 | Low |
| P1-020 (Redis cost tracking) | GAP-12, GAP-17, GAP-34 | Medium |
| P1-021 (HARD STOP handler) | GAP-02, GAP-05, GAP-18, GAP-28 | Critical |

---

## 12. CROSS-REFERENCE: DOWNSTREAM PHASE IMPACT

| Downstream Phase | Blocking Gaps | Non-Blocking Gaps |
|-----------------|---------------|-------------------|
| P4 (Persona Engine) | GAP-16 (prompt_loader tests) | GAP-24 |
| P5 (Loop Guardian) | GAP-16 (prompt_loader tests) | -- |
| P19 (Multi-Project Context) | GAP-01 (UNGATED callers), GAP-06/GAP-07 (latent bugs) | GAP-04, GAP-32, GAP-33 |
| P20 (Discord-Visible Autonomy) | GAP-01 (UNGATED callers), GAP-02 (fragmented HardStop) | GAP-05, GAP-17 |
| P23 (Embodied Operations) | GAP-01 (UNGATED callers), GAP-02 (fragmented HardStop) | GAP-21 |
| P24 (Hermes Fork) | GAP-06/GAP-07 (latent bugs activate on router injection) | GAP-32 |

---

*Register compiled from 9 audit reports (round-1: D1, D2, D3, D4; round-2: D1-V, D2-V, D3-V, D4-V, completeness-critic). READ-ONLY audit -- no source files were modified.*
