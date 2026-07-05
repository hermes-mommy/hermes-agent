# P1 Implementation Audit -- Final Report

**Date:** 2026-06-25
**Audit Phases Covered:** P1 (Phase 1: LLM + Hermes Agent Foundation), 21 steps P1-001 through P1-021
**Audit Method:** READ-ONLY (no VPS SSH, no secret decryption, no service restarts, no file edits beyond this report)
**Reports Consumed:** 4 round-1 + 5 round-2 + 3 research + 1 plan + 2 evidence registers = 15 documents
**Total Findings:** 40 implementation gaps + 25 documentation gaps = 65 findings (6 Critical, 12 High, 21 Medium, 18 Low, 8 Cosmetic)

---

## 1. Executive Summary

P1 (LLM + Hermes Agent Foundation) was implemented in May-June 2026 across 21 sequential steps. The audit confirms that all P1 source artifacts exist in the live codebase with real implementations -- no mocks, no placeholders, no stubs. The P1 architecture (TaskType enum, 3-tier fallback chain, 9Router-only routing, CostTracker, HardStopHandler) is preserved in the live code. However, 6 of 7 key source artifacts have drifted significantly from their P1 evidence snapshots due to Phase 3/5/6/7 enhancements (most notably `llm_router.py` growing from 90 to 253 lines and `main.py` from 33 to 760 lines). The audit uncovered 6 Critical findings including 6/6 loop/memory LLM callers that bypass the P20 safety kernel (dormant because `LoopManager(llm_router=None)`), 5 independent HardStopHandler instances that do not share state, and zero dedicated tests for the 295-line safety-critical `prompt_loader.py`. Security posture is strong (zero secrets leaked, all LLM traffic through localhost 9Router, no safety-bypass options) but two security hardening regressions were found in systemd service units. Of 25 runtime verification items (R01-R25), 24 require VPS SSH access and remain unverified. The overall P1 verdict is **IMPLEMENTED WITH BUGS** -- the foundation is real, functional, and preserved through later phases, but latent code bugs and safety-critical test gaps must be addressed before loop autonomy activates.

---

## 2. Audit Methodology

### 2.1 What Was Checked

- All 36 evidence files under `docs/setup-evidence/P1/` (structure, encoding, content)
- All P1 source artifacts: `llm_router.py`, `cost_tracker.py`, `llm_metrics.py`, `prompt_loader.py`, `hard_stop_handler.py`, `main.py`, `health-check-p1.sh`
- Service unit files: `guinevere-core.service`, `guinevere-9router.service` (vps-mirror copies)
- Config files: `hermes-config/config.yaml`, P1-005 evidence `config.yaml`
- Test suites: `test_hard_stop_handler.py` (56/56 executed locally), test file inventory
- Cross-references: `CHECKLIST.md`, `PROGRESS.md`, `docs/README.md`, ADR index, all ADRs referenced by P1
- All 6 active `LLMRouter.chat()` callers across `src/loops/`, `src/memory/`, `src/self_improve/`
- Secret scans: evidence files, source modules, config, systemd units, hermes-config
- Downstream compatibility: P19, P20, P22, P23, P24 roadmap impact

### 2.2 How

- **Round 1:** 4 parallel dimensions (D1 Architecture, D2 Docs, D3 Runtime, D4 Security)
- **Round 2:** 5 adversarial verifications (D1-V, D2-V, D3-V, D4-V + Completeness Critic)
- **Research:** 3 pre-audit research passes (repo evidence inventory, runtime readiness, downstream impact)
- **Registers:** 2 consolidated evidence registers (implementation gaps, missing docs)

### 2.3 Constraints

- No VPS SSH access. 24 of 25 runtime verification items remain unverified.
- No secret decryption (SOPS/age). VPS-only encrypted files not inspected.
- No service restarts or deployment actions.
- No test execution beyond `test_hard_stop_handler.py` (56 deterministic tests).
- Local Windows environment only (repo mirror on `C:/Users/faizz/guinevere`).

---

## 3. Overall P1 Verdict

**IMPLEMENTED WITH BUGS**

| Criterion | Assessment |
|-----------|-----------|
| Source code exists for all 21 steps | YES -- all artifacts present |
| No mocks/placeholders/stubs in P1 source | CORRECT -- zero forbidden patterns found |
| Evidence trail complete | 36 files, 14/21 STEP dirs (7 missing with partial justification) |
| Latent code bugs found | YES -- 2 latent bugs in loop callers (N1, N2), dormant until router injection |
| Active code bugs found | YES -- missing `import re` in sandbox.py, fragmented HardStop state |
| Safety-critical test gaps | YES -- prompt_loader.py (295 lines, 7 safety checks) has zero dedicated tests |
| Security regressions in service units | YES -- NoNewPrivileges + ProtectHome removed from guinevere-core.service; 9Router has zero hardening |
| Secrets leaked | NO -- zero plaintext secrets across entire scanned corpus |
| Runtime verified | NO -- 24/25 items need VPS |

**Allowed status selected:** IMPLEMENTED WITH BUGS
**Runner-up statuses:** IMPLEMENTED WITH DOC GAPS (evidence stale for 6/7 artifacts), NEEDS RUNTIME VERIFICATION (24/25 VPS items)

---

## 4. Per-Step Status Table

Reconciliation rule: lowest status across D1 (Architecture), D2 (Docs), D3 (Runtime), D4 (Security) governs.

| Step | Claim | Status | Reason |
|------|-------|--------|--------|
| P1-001 | Python 3.12.3 installed | **VERIFIED IMPLEMENTED** | Evidence files exist, version.txt matches claim, clean |
| P1-002 | UV 0.11.17 installed | **VERIFIED IMPLEMENTED** | Evidence files exist, version.txt matches claim |
| P1-003 | Virtual env + 61 packages | **VERIFIED IMPLEMENTED** | venv-packages.txt exists with full freeze listing |
| P1-004 | Hermes Agent v0.15.2 | **VERIFIED IMPLEMENTED** | 4 evidence files, pyproject.toml, install log all present |
| P1-005 | Hermes config deployed | **IMPLEMENTED WITH DOC GAPS** | Evidence config.yaml is structural reference (81 lines), not live runtime config (393 lines). Prometheus port drift (9091 vs 9191) |
| P1-006 | Node.js 24.15.0 + 9Router v0.4.66 | **IMPLEMENTED WITH DOC GAPS** | Evidence thinner than plan (2/5 files). 9Router service has zero security hardening (GAP-09) |
| P1-007 | 9Router config + providers | **IMPLEMENTED WITH DOC GAPS** | Evidence thinner than plan (1/4 files). Single shared NINEROUTER_API_KEY (GAP-03) |
| P1-008 | GPT-5.5 provider setup | **IMPLEMENTED WITH DOC GAPS** | No dedicated STEP dir. Evidence in migration-9router/evidence.md |
| P1-009 | GPT-5.5 connectivity | **IMPLEMENTED WITH DOC GAPS** | No STEP dir. Evidence in migration-9router lines 56-60 (REAL RESPONSE). Omitted from doc-sync line 92 |
| P1-010 | DeepSeek V4 Flash setup | **IMPLEMENTED WITH DOC GAPS** | No STEP dir. Evidence in migration-9router/evidence.md |
| P1-011 | DeepSeek connectivity | **IMPLEMENTED WITH DOC GAPS** | No STEP dir. Evidence in migration-9router/evidence.md |
| P1-012 | Ollama install | **SUPERSEDED BY LATER PHASE** | SKIPPED per Faiz directive. ADR-028 thoroughly documents: 10 validation checks, auditor gate with 3 findings, rollback safety |
| P1-013 | Ollama model pull | **SUPERSEDED BY LATER PHASE** | SKIPPED per ADR-028. DeepSeek V4 Flash serves as low-cost primary |
| P1-014 | Ollama fallback test | **SUPERSEDED BY LATER PHASE** | SKIPPED per ADR-028. Graceful degradation replaces Ollama fallback |
| P1-015 | llm_router.py deployed | **IMPLEMENTED WITH BUGS + DOC GAPS** | Live: 253 lines, Phase 6 rewrite. Evidence: 90-line stale snapshot. Latent bugs: N1 (string task_type), N2 (wrong content extraction). Dormant (llm_router=None). NEEDS RUNTIME VERIFICATION for live model routing |
| P1-016 | SystemPromptMaster + prompt_loader | **IMPLEMENTED WITH BUGS + DOC GAPS** | Live: 295 lines (6x growth). Zero dedicated tests for 7 safety-critical checks (GAP-16). UTF-16 encoding defect in evidence file |
| P1-017 | Persona smoke tests (7 pass, 2 xfail) | **NEEDS RUNTIME VERIFICATION** | Smoke tests require live 9Router (localhost:20128). Cannot run locally. conftest.py hardcodes ds/deepseek-v4-flash |
| P1-018 | FastAPI skeleton + systemd | **IMPLEMENTED WITH BUGS + DOC GAPS** | Security regressions: NoNewPrivileges + ProtectHome removed from live service unit (GAP-08). Evidence stale (5 divergences). main.py grew from 33 to 760 lines |
| P1-019 | Health check script | **NEEDS RUNTIME VERIFICATION** | 100% VPS commands (SOPS decrypt, Docker exec, curl). UTF-16 encoding defect in evidence file |
| P1-020 | Redis DB5 cost tracking | **IMPLEMENTED WITH DOC GAPS** | Source code exists, 13+ key patterns (was 11 in evidence). Zero dedicated tests (GAP-17). Redis state is VPS-only. Empty-password default (GAP-34) |
| P1-021 | HARD STOP handler (70/70 tests) | **IMPLEMENTED WITH BUGS + DOC GAPS** | 56/56 deterministic tests PASS locally. 14 model tests VPS-only. 5 independent HardStopHandler instances (GAP-02). PROGRESS.md inflates count to 142 (GAP-28). Gmail handler optional (GAP-05) |

**Status distribution:**
- VERIFIED IMPLEMENTED: 4 steps (P1-001 through P1-004)
- IMPLEMENTED WITH DOC GAPS: 8 steps (P1-005 through P1-011, P1-020)
- IMPLEMENTED WITH BUGS + DOC GAPS: 4 steps (P1-015, P1-016, P1-018, P1-021)
- SUPERSEDED BY LATER PHASE: 3 steps (P1-012 through P1-014)
- NEEDS RUNTIME VERIFICATION: 2 steps (P1-017, P1-019)

---

## 5. Bug Summary

**Total bugs across all registers:** 40 implementation gaps + 25 documentation gaps = 65

| Severity | Count | Description |
|----------|-------|-------------|
| Critical | 6 | P20 bypass (6 UNGATED callers), fragmented HardStop (5 instances), service hardening regression (NoNewPrivileges removed), 9Router zero hardening, prompt_loader zero tests, .chat() classification error |
| High | 12 | Standalone LLMRouter instantiation, shared API key, string task_type bug, wrong content extraction, 7 missing STEP dirs, D1 classification error, PROGRESS.md test inflation, no full test suite run |
| Medium | 21 | Stale evidence snapshots (llm_router, service, Redis keys), CostTracker tests missing, model tests VPS-only, smoke tests VPS-only, LoopManager llm_router=None, ContextCompactor dead code, bandit suppressions |
| Low | 18 | UTF-16 encoding (3 files), hardcoded VPS path, health-check SOPS-only, Prometheus port drift, P1-009 doc-sync omission, CostTracker empty password, docs/README missing P1 |
| Cosmetic | 8 | Dead model reference, CHECKLIST "20 steps", unchecked criteria, phantom typo, auth matrix "REFERENCE ONLY" label, type: ignore in safety_plugin |

### Top 5 Bugs

1. **GAP-01 (Critical):** 6/6 LLMRouter.chat() callers bypass P20/HermesBrain safety kernel. `src/loops/conversation.py:223`, `src/loops/phases/base.py:164`, `src/loops/reflection.py:83`, `src/loops/review_fork.py:213`, `src/memory/compaction.py:280`, `src/self_improve/optimizer.py:213`. Defense-in-depth mitigations exist (fail-closed CostTracker, LoopGuardian HARD STOP, 9Router-only) but callers lack consent gate, tool-call auth, and iteration budget enforcement. Currently dormant because `LoopManager(llm_router=None)` at `src/core/main.py:97`.

2. **GAP-02 (Critical):** 5 independent HardStopHandler instances do not share state. `src/core/main.py:101`, `src/discord/cmd_safeword.py:301`, `src/hermes/safety_plugin.py:440`, `src/channels/whatsapp/hard_stop.py:24`, `src/hermes_plugins/commands_high/safeword.py:52`. Triggering HARD STOP via Discord does not propagate to WhatsApp, safety plugin, or Hermes plugins.

3. **GAP-08 (Critical):** guinevere-core.service security hardening regression. `NoNewPrivileges=true` REMOVED from live unit. `ProtectHome=read-only` REMOVED. `ProtectSystem` relaxed from `strict` to `full`. Evidence: `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` vs `vps-mirror/systemd-live/guinevere-core.service`.

4. **GAP-16 (Critical):** `src/core/services/prompt_loader.py` (295 lines, 7 safety-critical checks for HARD STOP, safe word, Y5/Y6, distress) has ZERO dedicated unit tests. Only indirect coverage via smoke tests requiring VPS.

5. **GAP-09 (High):** `vps-mirror/systemd-live/guinevere-9router.service` has ZERO security hardening directives. No NoNewPrivileges, no ProtectSystem, no ProtectHome, no ProtectKernelModules. Every other service in the fleet has at least ProtectSystem=full.

---

## 6. Documentation Gaps Summary

**Total: 25 documentation defects** (0 Critical, 2 High, 7 Medium, 14 Low, 2 Cosmetic)

| Category | Count | Key Items |
|----------|-------|-----------|
| Missing STEP directories | 7 | P1-008 through P1-014 (3 SKIPPED with ADR-028, 4 with evidence only in migration-9router) |
| Stale evidence snapshots | 4 | llm_router.py (90 vs 253 lines), guinevere-core.service (5 divergences), Redis keys (11 vs 13+), Prometheus port (9091 vs 9191) |
| Encoding defects | 3 | UTF-16LE on import-test.txt, system-prompt-loaded.txt, health-check.txt (genuine captures, not fabrication) |
| Missing doc index entries | 2 | docs/README.md no P1 entry; PROGRESS.md 142 vs 70 test count |
| Inconsistent claims | 3 | PROGRESS.md vs evidence.md test count; CHECKLIST claims 21/21 but 7 dirs missing; D1 vs D4 caller classification |
| Stale config references | 3 | CHECKLIST "20 steps" (should be 21), unchecked criteria items, phantom typo in D3 report |
| Attribution gaps | 2 | migration-9router omits P1-009 from doc-sync; P1-006/007 evidence thinner than batch plan |
| Scaffold defects | 1 | D3-03 plan references non-existent REGISTRY export |

---

## 7. Implementation Gaps Summary

**Total: 40 implementation gaps** (6 Critical, 10 High, 14 Medium, 7 Low, 3 Cosmetic)

### Architectural Gaps (7)
- GAP-01: 6 UNGATED LLMRouter.chat() callers bypass P20 safety kernel (Critical)
- GAP-02: 5 independent HardStopHandler instances, fragmented state (Critical)
- GAP-03: Single shared NINEROUTER_API_KEY across all 3 provider tiers (High)
- GAP-04: Standalone LLMRouter() in compaction.py with no access control (High)
- GAP-05: Gmail service HardStopHandler is optional (Medium)
- GAP-06: String task_type vs TaskType enum in 9 callers (High, latent)
- GAP-07: Wrong response content extraction key path in 11 callers (High, latent)

### Security Hardening Regressions (2)
- GAP-08: guinevere-core.service lost NoNewPrivileges + ProtectHome (Critical)
- GAP-09: guinevere-9router.service has zero security hardening (High)

### Stale Artifact Drift (6)
- GAP-10 through GAP-15: Evidence snapshots stale for llm_router.py, guinevere-core.service, Redis keys, Prometheus port, config.yaml, 3 UTF-16 files (Medium/Low)

### Missing Tests (5)
- GAP-16: prompt_loader.py zero tests (Critical)
- GAP-17: cost_tracker.py zero dedicated tests (Medium)
- GAP-18: 14 model compliance tests VPS-only (Medium)
- GAP-19: Smoke tests VPS-only (Medium)
- GAP-20: No round-1 auditor ran full test suite (High, audit process)

### Code Quality (5)
- GAP-21: Missing `import re` in sandbox.py (Medium)
- GAP-32: LoopManager initialized with llm_router=None, no ADR (Medium)
- GAP-33: ContextCompactor dead code with resource leak (Medium)
- GAP-34: CostTracker Redis password defaults to empty string (Low)
- GAP-35: compaction.py _summarize returns empty string on failure (Low)

---

## 8. Downstream Compatibility Assessment

### P19 (Multi-Project Context) -- BLOCKER

| Component | Issue | Severity |
|-----------|-------|----------|
| CostTracker | All cost keys global (no project_id dimension). Per-project cost isolation impossible without key restructuring. | BLOCKER |
| LLMRouter | No project_id/namespace parameter. | BLOCKER |
| prompt_loader | No project_id parameter for per-project persona injection. | HIGH |

### P20 (Discord-Visible Autonomy / Life Kernel) -- BLOCKER

| Component | Issue | Severity |
|-----------|-------|----------|
| LLMRouter.chat() | Explicitly forbidden by P20 plan as raw LLM path. All autonomous reasoning must use HermesBrain.think(). | BLOCKER |
| HardStopHandler | 5 independent instances create fragmented HARD STOP state across channels. | HIGH |
| prompt_loader | Zero tests for safety-critical prompt validation. | HIGH |

### P22 (Full-Capability Raw Access) -- BLOCKER

| Component | Issue | Severity |
|-----------|-------|----------|
| LLMRouter | No AuthLevel gating, no semantic classification. Any L2+ action through LLMRouter bypasses P22 security. | BLOCKER |

### P23 (Embodied Operations) -- BLOCKER (deferred)

| Component | Issue | Severity |
|-----------|-------|----------|
| LLMRouter | Pre-empts P23 SemanticActionClassifier. Must not be used for autonomous action generation. | BLOCKER |
| HardStopHandler | Fragmented state blocks P23 safety integration. | HIGH |
| sandbox.py | Missing `import re` would crash sandbox execution. | MEDIUM |

P23 is BLOCKED on P19 runtime registry + P21 + P22 implementation per memory.

### P24 (Hermes Fork Convergence) -- ADAPTATION REQUIRED

| Component | Issue | Severity |
|-----------|-------|----------|
| 9Router | External Node.js dependency must be internalized into Python-native routing. | HIGH |
| hermes-agent | PyPI external dependency must be internalized via owned fork. | HIGH |
| Latent bugs N1/N2 | Would activate if LLMRouter injected into LoopManager before fork work fixes callers. | MEDIUM |

P24 verdict for P1: **PARTIALLY SUPERSEDED** under owned-fork scenario. CostTracker, prompt_loader, auth code are already Guinevere-owned. hermes-agent and 9Router are external dependencies requiring internalization.

---

## 9. Security Posture

### Secrets

| Surface | Scan Result |
|---------|-------------|
| All 36 P1 evidence files | ZERO secrets found (sk-*, AIza*, gh[opuab]_*, PEM keys) |
| All `src/core/services/*.py` | ZERO secrets found |
| `hermes-config/config.yaml` | All 3 providers use `key_env: NINEROUTER_API_KEY` (env var ref, no inline keys) |
| `vps-mirror/systemd-live/*.service` | ZERO secrets found |
| `scripts/health-check-p1.sh` | Uses SOPS decryption at runtime, no plaintext |
| Expanded scans (verify=False, shell=True, pickle, eval, unsafe yaml.load) | ZERO matches across entire src/ |

**Secret hygiene: EXCELLENT.** No plaintext API keys, passwords, or tokens found anywhere.

### HARD STOP

- HardStopHandler is ACTIVE in both evidence and live code
- Instantiated at `src/core/main.py:101`, wired to LoopGuardian at line 103-104
- Guardian checks `is_hard_stop_active` on every loop tick
- 56/56 deterministic tests PASS locally
- **Weakness:** 5 independent instances do not share state (GAP-02)
- **Weakness:** Gmail service handler is optional (GAP-05)

### Routing

- All 3 model configs route through `http://localhost:20128/v1` (9Router only)
- Zero direct provider URLs (`api.openai.com`, `api.deepseek.com`, etc.) found in entire src/ tree
- Metrics server binds to `127.0.0.1:9191` (localhost-only)
- **Weakness:** All 3 provider entries share single NINEROUTER_API_KEY

### Backdoor Risk

- `LLMRouter()` can be instantiated without injection control (`compaction.py:80`)
- 6 callers bypass P20 HermesBrain, but all use 9Router + fail-closed CostTracker + LoopGuardian HARD STOP
- Currently dormant because `LoopManager(llm_router=None)` prevents loop callers from reaching LLMRouter
- **Assessment:** MEDIUM RISK. Architecture is intentional (loop infrastructure vs autonomy kernel) but instantiation controls are absent.

### Audit Suppressions

- Zero `type: ignore` or security-related `noqa` in core P1 services
- All 130+ noqa comments across src/ are lint/fail-soft patterns (BLE001, PLC0415, PLW0603)
- 4 bandit suppressions (S404, S603, S607, S310) outside P1 core scope -- all documented fail-soft

---

## 10. VPS Verification Requirements (R01-R25)

| ID | Claim | Command | Local? | Status |
|----|-------|---------|--------|--------|
| R01 | guinevere-core.service active | `systemctl status guinevere-core` | NO | NEEDS RUNTIME VERIFICATION |
| R02 | guinevere-9router.service active | `systemctl status guinevere-9router` | NO | NEEDS RUNTIME VERIFICATION |
| R03 | Docker daemon running | `docker ps` | NO | NEEDS RUNTIME VERIFICATION |
| R04 | guinevere-postgres container running | `docker ps \| grep postgres` | NO | NEEDS RUNTIME VERIFICATION |
| R05 | guinevere-redis container running | `docker ps \| grep redis` | NO | NEEDS RUNTIME VERIFICATION |
| R06 | Uvicorn listening on :8000 | `ss -tlnp \| grep 8000` | NO | NEEDS RUNTIME VERIFICATION |
| R07 | Postgres listening on :5433 | `ss -tlnp \| grep 5433` | NO | NEEDS RUNTIME VERIFICATION |
| R08 | Redis listening on :6380 | `ss -tlnp \| grep 6380` | NO | NEEDS RUNTIME VERIFICATION |
| R09 | Postgres SELECT 1 succeeds | `docker exec guinevere-postgres psql ... "SELECT 1;"` | NO | NEEDS RUNTIME VERIFICATION |
| R10 | Redis PING returns PONG | `docker exec guinevere-redis redis-cli ... PING` | NO | NEEDS RUNTIME VERIFICATION |
| R11 | Core reasoning model route works | `curl POST localhost:20128/v1/chat/completions` | NO | NEEDS RUNTIME VERIFICATION |
| R12 | Sub-agent model route works | Same, different task_type | NO | NEEDS RUNTIME VERIFICATION |
| R13 | Fallback on primary failure | Inject invalid model, verify fallback | NO | NEEDS RUNTIME VERIFICATION |
| R14 | LLM response has expected fields | Check choices, usage in response | NO | NEEDS RUNTIME VERIFICATION |
| R15 | System prompt file exists | `ls -la /home/guinevere/config/hermes/system-prompt.md` | NO | NEEDS RUNTIME VERIFICATION |
| R16 | System prompt has safety elements | `grep HARD STOP, safe word, Y5, Y6, distress` | NO | NEEDS RUNTIME VERIFICATION |
| R17 | System prompt readable | `cat ... > /dev/null && echo readable` | NO | NEEDS RUNTIME VERIFICATION |
| R18 | HardStopHandler deterministic tests | `pytest tests/safety/test_hard_stop_handler.py -v` | **YES** | **PASS** (56/56, 1.75s) |
| R19 | HardStopHandler model compliance (14 tests) | `pytest ... -k model` | NO | NEEDS RUNTIME VERIFICATION |
| R20 | Redis DB5 keys match expected | `redis-cli -n 5 KEYS '*'` | NO | NEEDS RUNTIME VERIFICATION |
| R21 | CostTracker writes to Redis | LLM call + check Redis counters | NO | NEEDS RUNTIME VERIFICATION |
| R22 | Fallback to sub-agent on HTTP error | Inject bad model | NO | NEEDS RUNTIME VERIFICATION |
| R23 | Fallback to guinevere combo on all failures | Unreachable base_url | NO | NEEDS RUNTIME VERIFICATION |
| R24 | SSE [DONE] stripping works | Non-streaming request, check no [DONE] | NO | NEEDS RUNTIME VERIFICATION |
| R25 | Prometheus :9191/metrics | `curl http://localhost:9191/metrics` | NO | NEEDS RUNTIME VERIFICATION |

**Summary:** 1/25 verified locally (R18). 24/25 require VPS SSH access.

---

## 11. Recommendations (Priority Order)

### Immediate (Before P1 Closure)

| # | Action | Effort | Gap |
|---|--------|--------|-----|
| 1 | Restore `NoNewPrivileges=true` in guinevere-core.service | Trivial | GAP-08 |
| 2 | Add security hardening to guinevere-9router.service (NoNewPrivileges, ProtectSystem=full, ProtectHome=read-only) | Trivial | GAP-09 |
| 3 | Create `tests/services/test_prompt_loader.py` with deterministic tests for all 7 safety checks | Medium | GAP-16 |
| 4 | Add `import re` to `src/loops/sandbox.py` | Trivial | GAP-21 |
| 5 | Fix PROGRESS.md P1-021 to "70/70 PASS" with footnote explaining 86 comprehensive added post-P1 | Trivial | GAP-28 |

### Before Loop Autonomy Activates (P19/P24 Prerequisites)

| # | Action | Effort | Gap |
|---|--------|--------|-----|
| 6 | Design common LLM call gate for loop/memory/self-improve callers | High | GAP-01 |
| 7 | Consolidate HardStopHandler into single shared singleton via DI | Medium | GAP-02 |
| 8 | Fix task_type string to TaskType enum in all 9 callers | Low | GAP-06 |
| 9 | Fix content extraction key paths in all callers (choices[0].message.content) | Low | GAP-07 |
| 10 | Add comment or ADR explaining why LoopManager gets llm_router=None | Trivial | GAP-32 |
| 11 | Add project_id to CostTracker, LLMRouter, prompt_loader | Medium | P19 prep |

### Architectural Debt (Any Phase)

| # | Action | Effort | Gap |
|---|--------|--------|-----|
| 12 | Remove standalone LLMRouter() instantiation in compaction.py | Low | GAP-04 |
| 13 | Make Gmail HardStopHandler required (not optional) | Low | GAP-05 |
| 14 | Create test_cost_tracker.py with mock Redis | Medium | GAP-17 |
| 15 | Evaluate per-tier API keys in 9Router | Investigation | GAP-03 |
| 16 | Remove or deprecate ContextCompactor dead code | Trivial | GAP-33 |
| 17 | Fix CostTracker empty-password default to None + raise on misconfig | Trivial | GAP-34 |
| 18 | Run all P1-related test files locally (not just HardStopHandler) | Medium | GAP-20 |

### Documentation Cleanup (Any Phase)

| # | Action | Effort | Gap |
|---|--------|--------|-----|
| 19 | Create stub STEP directories P1-008 through P1-011 with pointer files | Low | GAP-25 |
| 20 | Add drift notes to P1-015, P1-018, P1-020, P1-005 evidence directories | Trivial | GAP-10/11/12/13 |
| 21 | Re-encode 3 UTF-16LE files or convert to UTF-8 | Trivial | GAP-14 |
| 22 | Fix migration-9router/evidence.md line 92 to include P1-009 | Trivial | GAP-26 |
| 23 | Add P1 entry to docs/README.md | Trivial | GAP-29 |
| 24 | Fix CHECKLIST "20 steps" to "21 steps" | Trivial | GAP-30 |
| 25 | Check off Phase Complete Criteria items or add convention note | Trivial | GAP-31 |

---

## 12. Caveats and Limitations

1. **No VPS access.** 24 of 25 runtime verification items (R01-R25, excluding R18) are unverified. Service status, database connectivity, LLM routing, Redis state, system prompt presence, and metrics endpoint could not be confirmed. A supplementary VPS verification pass is required for full closure.

2. **No secret decryption.** SOPS-encrypted files (`.env.9router.sops`, `discord-secrets.yaml`, `redis-acl-passwords.yaml`) are VPS-only. The audit confirmed no plaintext secrets in the repo, but cannot verify the encrypted contents.

3. **Stale evidence snapshots.** 6 of 7 key P1 source artifacts have drifted from their evidence snapshots. This is normal code evolution (Phase 3/5/6/7 enhancements) but means P1 evidence does not represent the current production state. The P1 architecture is preserved; the implementation details have changed.

4. **Dormant bugs.** The N1 (string task_type) and N2 (wrong content extraction) bugs in loop callers are dormant because `LoopManager(llm_router=None)`. They would activate if an LLM router is ever injected. Currently no runtime impact.

5. **Incomplete test execution.** Only 1 of 7+ P1-related test files was executed (`test_hard_stop_handler.py`, 56/56 PASS). Tests for llm_router cost, llm_metrics, hard_stop_comprehensive, hard_stop_latency were not run. The completeness of P1's test suite is unverified.

6. **Encoding defect analysis.** The 3 UTF-16LE files were verified as genuine SSH captures with wrong encoding (content recoverable via UTF-16 decode). They are not fabrication, but the encoding defect means the evidence files are not directly readable without conversion.

7. **Cost accuracy.** The P1 cost claim ($15/mo) is unitemized. Based on actual API calls (2 curl tests + 14 model compliance tests + 9 smoke tests), estimated actual API credit cost is $2-5. The $15 figure likely includes 9Router migration provider tests.

8. **D1 classification correction.** Round-1 D1 classified all 6 `.chat()` callers as "HERMESBRAIN-WIRED" (PASS). Round-2 D4 and the Completeness Critic correctly reclassified them as "UNGATED." D1's PASS verdict on D1-02 is weakened but not overturned (other D1 checks hold). This report uses D4's assessment.

---

## 13. Appendix: All Report File Paths

### Audit Plan
- `docs/setup-evidence/legacy-audit/P1/plan/p1-implementation-audit-plan.md`

### Research Reports
- `docs/setup-evidence/legacy-audit/P1/research/p1-repo-evidence-inventory.md`
- `docs/setup-evidence/legacy-audit/P1/research/p1-runtime-readiness-readonly.md`
- `docs/setup-evidence/legacy-audit/P1/research/p1-downstream-impact-p19-p24.md`

### Round-1 Reports
- `docs/setup-evidence/legacy-audit/P1/audits/round-1/architecture-implementation.md` (D1)
- `docs/setup-evidence/legacy-audit/P1/audits/round-1/evidence-docs-consistency.md` (D2)
- `docs/setup-evidence/legacy-audit/P1/audits/round-1/runtime-config-readiness.md` (D3)
- `docs/setup-evidence/legacy-audit/P1/audits/round-1/d4-security-secrets-safety.md` (D4)

### Round-2 Reports
- `docs/setup-evidence/legacy-audit/P1/audits/round-2/d1-architecture-verify.md` (D1-V)
- `docs/setup-evidence/legacy-audit/P1/audits/round-2/d2-evidence-docs-verify.md` (D2-V)
- `docs/setup-evidence/legacy-audit/P1/audits/round-2/d3-runtime-config-verify.md` (D3-V)
- `docs/setup-evidence/legacy-audit/P1/audits/round-2/d4-security-verify.md` (D4-V)
- `docs/setup-evidence/legacy-audit/P1/audits/round-2/completeness-critic.md`

### Evidence Registers
- `docs/setup-evidence/legacy-audit/P1/evidence/implementation-gap-register.md` (40 gaps)
- `docs/setup-evidence/legacy-audit/P1/evidence/missing-docs-register.md` (25 doc defects)

### This Report
- `docs/setup-evidence/legacy-audit/P1/evidence/final-p1-implementation-audit-report.md`

---

*Final audit report compiled from 15 source documents (1 plan, 3 research, 4 round-1, 5 round-2, 2 evidence registers). READ-ONLY audit -- no source files, config files, or service units were modified.*
