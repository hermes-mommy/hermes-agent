# P1 Implementation-Audit Plan

**Date:** 2026-06-25
**Status:** PLAN -- not yet executed
**Audit round:** Round-1 plan (4 parallel dimensions)
**Plan author:** READ-ONLY research subagent

---

## 1. AUDIT SCOPE & GROUND TRUTH

### 1.1 What P1 Claims

P1 (Phase 1: LLM + Hermes Agent Foundation) claims 21 sequential steps P1-001 through P1-021, documented across evidence dirs at `docs/setup-evidence/P1/STEP-P1-001/` through `STEP-P1-021/`.

| Step | Claim |
|------|-------|
| P1-001 | Python 3.12.3 runtime installed on VPS (Ubuntu 24.04), 8 packages verified |
| P1-002 | UV 0.11.17 per-user package manager installed |
| P1-003 | Virtual env created at `/home/guinevere/code/guinevere/.venv`, 61 packages installed |
| P1-004 | Hermes Agent v0.15.2 installed from PyPI, `src/` structure with 14 dirs, `pyproject.toml` |
| P1-005 | Hermes config deployed (9-section YAML: agent, llm, memory, loop, safety, budget, tools, messaging, monitoring) |
| P1-006 | Node.js 24.15.0 + 9Router v0.4.66 installed, systemd unit |
| P1-007 | 9Router config + startup, provider connections via SQLite, placeholder API keys |
| P1-008 | Hermes MCP integration (tool definitions, skill registrations) |
| P1-009 | Skill loading system (skill directories, metadata parsing) |
| P1-010 | Base persona definition (Guinevere de Baroque identity document) |
| P1-011 | LLM provider config (model selection, temperature, max_tokens) |
| P1-012 | Fallback chain (CORE_REASONING -> SUB_AGENT -> GUINEVERE combo) |
| P1-013 | Budget & cost limits (monthly cap $30, daily cap $2) |
| P1-014 | Memory system foundation (conversation context, short-term recall) |
| P1-015 | `llm_router.py` deployed (90 lines, 3-tier routing: gpt-5.5 primary, deepseek-v4-flash sub-agent, 0.7 temp) |
| P1-016 | SystemPromptMaster v1.1 deployed, `prompt_loader.py` created, 7 safety checks |
| P1-017 | Persona smoke tests as pytest suite (7 pass, 2 xfail) |
| P1-018 | FastAPI skeleton `main.py` + `guinevere-core.service` deployed, `/health` endpoint |
| P1-019 | Health check script created (`health-check-p1.sh`), all 4 services PASS |
| P1-020 | Redis DB5 cost tracking deployed (CostTracker), 11 keys initialized |
| P1-021 | HARD STOP handler deployed (160 lines), 70/70 tests pass |

### 1.2 What the Live Repo Actually Has

Ground truth from the three research passes:

| Aspect | P1 Claim | Live Repo Reality | Source |
|--------|----------|-------------------|--------|
| `llm_router.py` | 90 lines, `gpt-5.5` primary, no CostTracker, no metrics | 253 lines, `ds/deepseek-v4-flash` primary, CostTracker integrated, Prometheus metrics, SSE stripping, fail-closed cost tracking | `research/p1-repo-evidence-inventory.md:56-57`, diff table |
| `prompt_loader.py` | 45 lines, `load_system_prompt()` only | 295 lines, memory orchestration, KG injection, token budget enforcement | `research/p1-repo-evidence-inventory.md:57` |
| `cost_tracker.py` | 11 keys, 4 pipeline commands | Expanded with `cost:daily:`, `cost:monthly:`, `token:*` counters, 12 pipeline commands | `research/p1-repo-evidence-inventory.md:58` |
| `main.py` | 33-line FastAPI skeleton | ~760 lines: HermesBrain, Living Autonomy Kernel, LoopManager, HardStopHandler, surveillance consumer, KG ingestion, Discord visible autonomy, Prometheus middleware | `research/p1-repo-evidence-inventory.md:60` |
| `guinevere-core.service` | `ProtectSystem=strict`, `ProtectHome=read-only`, no `EnvironmentFile` | `ProtectSystem=full`, no `ProtectHome`, has `EnvironmentFile`, 5 `ReadWritePaths` (incl. `.hermes`) | `research/p1-repo-evidence-inventory.md:62`; `research/p1-runtime-readiness-readonly.md:79-95` |
| `hermes-config/config.yaml` | 9-section structural config (394 lines) | Hermes Gateway operational config (different file, different schema) | `research/p1-repo-evidence-inventory.md:63` |
| `health-check-p1.sh` | Same as evidence | **MATCHES** — only unchanged artifact | `research/p1-repo-evidence-inventory.md:61` |
| `9router-keys.enc.yaml` | Claimed to exist | **NOT FOUND** in repo (VPS-only `secrets/.env.9router.sops`) | `research/p1-repo-evidence-inventory.md:66` |

### 1.3 Snapshot-vs-Live Drift: The Critical Finding

The P1-015 `llm_router.py` evidence artifact (90 lines) is a **point-in-time snapshot** that no longer matches the production source. Every substantive claim from P1-015 is stale:

- **Model changed:** `gpt-5.5` -> `ds/deepseek-v4-flash` for CORE_REASONING (Phase 6 migration)
- **Pricing changed:** Input $0.0025/1K -> $0.005/1K; output $0.01/1K -> $0.03/1K
- **Architecture added:** CostTracker integration, Prometheus metrics, SSE `[DONE]` stripping, fail-closed cost tracking, full type annotations
- **Temperature changed:** 0.7 -> 0.5
- **max_tokens changed:** 16384 -> 8192
- **Lines:** 90 -> 253

Similarly, `guinevere-core.service` in evidence differs from the vps-mirror copy in 3 properties (EnvironmentFile, ProtectSystem, ProtectHome). The evidence artifact is **stale** for 6 of 7 claimed source artifacts (only `health-check-p1.sh` is identical).

### 1.4 Evidence Completeness Verdict

- **36 evidence files** catalogued across all 21 P1 steps -- comprehensive trail
- **3 malformed files** (E17, E20, E27): SSH UTF-16LE captures stored as UTF-8, display as null-byte noise. Content is genuine when decoded. **Not fabrication** -- a capture encoding defect.
- **2 placeholder files** (E12 P1-005 config.yaml, E15 P1-007 evidence): honestly documented as PLACEHOLDER keys, resolved by migration-9router.
- **No fabricated command output** detected anywhere in the evidence corpus.
- **Missing from repo:** `9router-keys.enc.yaml` (VPS-only SOPS file, gitignored).

---

## 2. FOUR AUDIT DIMENSIONS (Round-1, Parallel)

### D1: Architecture-Implementation

**Goal:** Determine whether P1 is actually implemented in the live source code (not just evidence documents). Identify half-implementations, placeholders, mocks, hardcoded values, fallback-only paths. Determine if P1 foundation still works post-P20/P19/P24 changes.

**Key questions:**
- Does `llm_router.py` implement the P1-015 fallback chain? (Yes, but refactored.)
- Is `LLMRouter.chat()` still called directly anywhere, bypassing HermesBrain? (Potential P20 backdoor.)
- Does `CostTracker.record_cost()` actually write to Redis DB5? (Code path exists, but VPS-only.)
- Is the HardStopHandler actually wired into the main loop? (Verify import + instantiation in `main.py`.)
- Are the P1 smoke tests still runnable? (They hit live API; cannot verify locally.)
- Does the P1 FastAPI skeleton still exist after main.py grew to 760 lines? (Check for preserved endpoints.)

**Scope:** P1-001 through P1-021 source artifacts; all `.py` files in `src/core/services/`, `main.py`, `hard_stop_handler.py`, `tests/smoke/`, `tests/safety/`.

### D2: Evidence-Docs-Consistency

**Goal:** Verify that CHECKLIST.md, PROGRESS.md, the docs-index, and P1 evidence agree. Identify stale, superseded, fake-PASS, or missing-status entries. Identify documentation that the current docs pattern requires but P1 lacks.

**Key questions:**
- Does CHECKLIST.md mark P1 as complete? (If yes, on what basis given 6/7 source artifacts drifted?)
- Does PROGRESS.md align with the evidence directory structure?
- Are the 3 encoding-defective files flagged in any project index?
- Do the ADR documents referenced in P1 evidence still exist and remain valid?
- Does the current docs-pattern (ADR index, audit trails, per-phase summaries) have a P1 equivalent?
- Is the P1-005 config.yaml evidence file confused with the (different) live hermes-config/config.yaml anywhere?

**Scope:** `CHECKLIST.md`, `PROGRESS.md`, `docs/` index files, all ADRs referenced by P1, `docs/setup-evidence/P1/` directory tree.

### D3: Runtime-Config-Readiness

**Goal:** Identify safe read-only runtime checks that can be performed. Flag config mismatch, brittle startup paths, routing errors. Clearly demarcate what NEEDS RUNTIME VERIFICATION (VPS-only).

**Key questions:**
- Safe local: AST parse all modules? (YES -- all PASS per research doc.)
- Safe local: Import tests? (YES -- all import successfully against local venv.)
- Safe local: Hardcoded secrets grep? (YES -- zero secrets found.)
- Needs VPS: Services running? (R01-R08, 8 checks.)
- Needs VPS: DB connectivity? (R07-R10, 4 checks.)
- Needs VPS: LLM route tests? (R11-R14, R21-R24, 8 checks - spend real credits.)
- Needs VPS: System prompt file exists? (R15-R17, 3 checks.)
- Needs VPS: Metrics endpoint? (R25, 1 check.)
- Needs VPS but CAN run locally: HardStopHandler unit tests? (R18 -- 56/56 tests, pure Python, no deps.)

**Total: 10 local + 25 VPS = 35 verification points.**

**Configuration drift flags:**
- `prompt_loader.py:16` hardcoded path `/home/guinevere/config/hermes/system-prompt.md` -- valid VPS path, FILENotFound on non-VPS.
- `llm_router.py` `base_url="http://localhost:20128/v1"` -- correct for 9Router, but single point of failure if 9Router is down.
- `cost_tracker.py` default host/port `("localhost", 6380, db=5)` -- config matches evidence but Redis must be running.

**Scope:** All source `.py` files, `vps-mirror/systemd-live/`, `hermes-config/`, evidence shell output files.

### D4: Security-Secrets-Safety

**Goal:** Verify no secrets leaked in evidence or source. Confirm HARD STOP / consent not weakened by P1. Confirm no raw LLM path bypasses Hermes/P20. Confirm unsafe provider routing does not exist.

**Key questions:**
- Any plaintext API keys in evidence files? (Research says NO.)
- Any plaintext passwords in source or config? (Research says NO -- all env var refs.)
- Does `LLMRouter.chat()` create an invisible backdoor around the P20 autonomy kernel? (Design issue, not a secret leak -- but security-relevant.)
- Does the P1-007 evidence file expose PLACEHOLDER key patterns that could reveal real key structure? (By design, PLACEHOLDER only.)
- Are the 3 malformed files (E17, E20, E27) a security concern? (No -- they are encoding-corrupted test output, not secrets.)
- Is the `key_env: NINEROUTER_API_KEY` pattern in `hermes-config/config.yaml` correct? (Yes -- env var reference, not hardcoded.)
- Are SOPS-encrypted files referenced correctly without exposing plaintext? (Yes -- research confirms VPS-only, gitignored.)

**Scope:** All 36 evidence files, all source `.py` files, `hermes-config/config.yaml`, `vps-mirror/systemd-live/*.service`.

---

## 3. PER-DIMENSION VERIFICATION SCAFFOLD

### 3.1 D1: Architecture-Implementation

**Goal:** PASS only if every P1-claimed implementation concern is satisfied by the live source code with no half-implementations or runtime-only claims that cannot be substantiated.

| # | Expected Files (must read) | Forbidden Patterns (grep must return 0) | Required Commands | Evidence Requirements | Hard Rejection Criteria |
|---|---|---|---|---|---|
| D1-01 | `src/core/services/llm_router.py` | `# TODO.*(mock\|placeholder\|stub)`, `raise NotImplementedError`, `pass  #.*TODO` | `python -c "from src.core.services.llm_router import LLMRouter, TaskType; print(TaskType.values())"` -> `['core', 'sub_agent', 'fallback']` | `round-1/d1-architecture.md` must include: fallback chain existence + model comparison table + CostTracker wiring + metrics wiring | `TaskType` does not include all 3 values; CostTracker not imported/used; fallback chain missing |
| D1-02 | `src/core/services/llm_router.py` | `\.chat\(` (verify NOT called outside approved paths; grep all callers) | `grep -rn "\.chat(" src/ --include="*.py"` -> list every caller for auditor review | D1 report must enumerate every caller of `LLMRouter.chat()` and classify as HERMESBRAIN-WIRED or RAW | Any caller without a HermesBrain envelope for autonomous actions (P20 violation) |
| D1-03 | `src/core/services/cost_tracker.py` | `pass  #.*todo\|placeholder\|mock` | `python -c "from src.core.services.cost_tracker import CostTracker; import inspect; print(inspect.signature(CostTracker.__init__))"` -> must include `host`, `port`, `db`, `password` params | D1 report must show `record_cost()` key pattern + `check_budget()` threshold | `record_cost()` body is `pass`/`return None`/`...`; missing pipeline writes to Redis |
| D1-04 | `src/core/main.py` | `HardStopHandler.*# TODO\|HardStopHandler.*mock` | `grep -n "HardStopHandler\|hard_stop_handler" src/core/main.py` -> confirm import + instantiation + wiring | D1 report must show HardStopHandler lifecycle (init, injection point, trigger path) | HardStopHandler imported but never instantiated or wired into request lifecycle |
| D1-05 | `src/core/services/prompt_loader.py` | `def.*TODO\|placeholder\|mock` | `python -c "from src.core.services.prompt_loader import load_system_prompt; print(load_system_prompt.__doc__)"` -> must show expected prompt loading behavior | D1 report must show `load_system_prompt()` signature, any system prompt caching, any KG injection | `load_system_prompt()` returns empty string or raises `NotImplementedError` |
| D1-06 | `tests/safety/test_hard_stop_handler.py` | N/A (verify they exist and run) | `python -m pytest tests/safety/test_hard_stop_handler.py -v --tb=short 2>&1 \| tail -30` -> must show 56+ passed, 0 failed (CAN RUN LOCALLY) | D1 report must include full pytest output summary | Tests fail or fewer than 56 pass (verify against P1-021 claim) |
| D1-07 | `tests/smoke/` | N/A (VPS-only -- cannot run locally) | N/A -- annotate as NEEDS RUNTIME VERIFICATION | D1 report must document that smoke tests require VPS and cannot be verified during round-1 | N/A (VPS-gated) |
| D1-08 | `src/core/services/llm_metrics.py` | `# TODO\|pass  #\|mock` | `python -c "from src.core.services.llm_metrics import REGISTRY; print([m.name for m in REGISTRY.collect()])"` -> must list expected metric families | D1 report must document all registered Prometheus metrics and whether they are wired to llm_router.py | Zero metric families registered; metrics server not started |
| D1-09 | `scripts/health-check-p1.sh` | plaintext API key patterns (`sk-[a-zA-Z0-9]`, `[\w-]+\.[\w-]+\.[\w-]+`) | `diff docs/setup-evidence/P1/STEP-P1-019/health-check-p1.sh scripts/health-check-p1.sh 2>/dev/null \|\| diff docs/setup-evidence/hermes-migration/phase-7/health-check-p1.sh scripts/health-check-p1.sh` -> must be identical | D1 report must confirm health-check-p1.sh unchanged from evidence | Script content differs from every known evidence copy |
| D1-10 | `src/core/main.py` | N/A | `grep -n "@app.get\|@app.post\|@app.put\|@app.delete" src/core/main.py` -> inventory all FastAPI endpoints | D1 report must include endpoint table (method, path, handler, purpose) | P1-claimed `/health` endpoint missing from live `main.py` |

**Evidence output path:** `round-1/d1-architecture.md`
**Forbidden patterns apply to:** all `.py` files under `src/core/services/`, `src/core/main.py`, `src/core/hard_stop_handler.py`, `tests/smoke/`, `tests/safety/`

### 3.2 D2: Evidence-Docs-Consistency

**Goal:** PASS only if CHECKLIST.md, PROGRESS.md, docs-index, and P1 evidence files are mutually consistent and accurately reflect the current state of the repository.

| # | Expected Files (must read) | Forbidden Patterns (grep must return 0) | Required Commands | Evidence Requirements | Hard Rejection Criteria |
|---|---|---|---|---|---|
| D2-01 | `CHECKLIST.md` | `MARK_COMPLETE\|\[x\].*P1\|## P1.*Done\|Phase 1.*✅` that contradicts source drift findings | `grep -n -i "phase 1\|P1\|P-1" CHECKLIST.md` -> extract P1 completion status | D2 report must quote exact P1 entry in CHECKLIST.md and compare against actual source drift | CHECKLIST.md marks P1 as fully complete/verified when 6/7 source artifacts have drifted |
| D2-02 | `PROGRESS.md` | N/A (verification) | `grep -n "P1\|Phase.1\|STEP-P1" PROGRESS.md` -> extract P1 progress entries | D2 report must quote PROGRESS.md P1 section and verify it aligns with evidence dir structure | PROGRESS.md claims steps or evidence that don't exist on disk |
| D2-03 | `docs/` index files (ADR index, docs README) | N/A (verification) | `grep -rn "P1\|STEP-P1" docs/ --include="*.md" -l` -> list all docs referencing P1; cross-reference with actual evidence files | D2 report must list every index/README that references P1 and verify references are valid | Any doc references a P1 evidence path that does not exist |
| D2-04 | `docs/setup-evidence/P1/` directory tree | N/A | `find docs/setup-evidence/P1 -type f \| sort` -> full evidence file inventory | D2 report must contain the complete evidence file inventory table (36 files min) | Missing STEP directories (P1-001 through P1-021 must all exist) |
| D2-05 | `docs/setup-evidence/P1/STEP-P1-015/import-test.txt`, `STEP-P1-016/system-prompt-loaded.txt`, `STEP-P1-019/health-check.txt` | N/A (encoding defect analysis) | `file docs/setup-evidence/P1/STEP-P1-015/import-test.txt docs/setup-evidence/P1/STEP-P1-016/system-prompt-loaded.txt docs/setup-evidence/P1/STEP-P1-019/health-check.txt` -> confirm null-byte/UTF-16 identification | D2 report must document the encoding defect for each of 3 files, confirm no fabrication, and recommend re-capture option | Files dismissed as "corrupted/broken" without proving content is recoverable via UTF-16 decode |
| D2-06 | `docs/setup-evidence/P1/STEP-P1-005/config.yaml` vs `hermes-config/config.yaml` | N/A (comparison) | `diff <(wc -l docs/setup-evidence/P1/STEP-P1-005/config.yaml) <(wc -l hermes-config/config.yaml)` -> confirm different sizes; `head -5` each | D2 report must document that these are DIFFERENT FILES with different schemas, and verify no doc confuses them | Any document treats P1-005 config.yaml as the same artifact as the live Hermes gateway config |
| D2-07 | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | N/A (verification) | `grep -c "P1\|Phase.1" docs/60-persona/61-SystemPromptMaster_v1.1.md` -> verify P1 attribution | D2 report must confirm SystemPromptMaster v1.1 docs exist and are correctly attributed to P1 | SystemPromptMaster doc missing or incorrectly attributed |
| D2-08 | All ADR files referenced by P1 evidence | N/A (verification) | `grep -rn "adr-" docs/setup-evidence/P1 --include="*.md" -o -i` -> list all ADRs referenced; then verify each exists in `docs/` | D2 report must list every ADR referenced by P1 evidence and verify file exists in current docs tree | Any ADR referenced by P1 evidence that does not exist in the current docs tree |
| D2-09 | `docs/setup-evidence/P1/STEP-P1-021/evidence.md` | N/A (verification) | `grep "pytest\|PASS\|test" docs/setup-evidence/P1/STEP-P1-021/evidence.md` -> extract test counts | D2 report must note the claimed 70 tests vs hard_stop_handler.py actual test count (56 deterministic + 14 model = 70). Verify 56 are deterministic and runnable locally. | Claimed 70 tests are not accounted for as 56 deterministic + 14 model tests |

**Evidence output path:** `round-1/d2-evidence-docs-consistency.md`
**Forbidden patterns apply to:** all cross-references between P1 evidence and project management/docs files

### 3.3 D3: Runtime-Config-Readiness

**Goal:** PASS only after executing all safe local checks and clearly documenting each VPS-only verification requirement. No claims of "verified working" without actual command output.

| # | Expected Files (must read) | Forbidden Patterns (grep must return 0) | Required Commands | Evidence Requirements | Hard Rejection Criteria |
|---|---|---|---|---|---|
| D3-01 | `src/core/services/llm_router.py` | Hardcoded IP `10\.\|192\.168\.\|172\.` (private IPs); `sk-[a-zA-Z0-9]{20,}` (API key pattern) | `python -c "import ast; ast.parse(open('src/core/services/llm_router.py').read()); print('AST OK')"` | D3 report must include AST parse + import + grep results for all 4 core service modules | Any core service module fails AST parse |
| D3-02 | `src/core/services/cost_tracker.py` | Hardcoded password/token/secret | `python -c "from src.core.services.cost_tracker import CostTracker; print('Import OK')"` -> MUST NOT instantiate (would attempt Redis connection) | D3 report must document the Redis connection dependency and note it is VPS-only | Import fails or triggers Redis connection error |
| D3-03 | `src/core/services/llm_metrics.py` | Hardcoded credentials | `python -c "from src.core.services.llm_metrics import REGISTRY; print('Import OK')"` | D3 report must confirm metrics server binds to `127.0.0.1:9191` (localhost-only) | Metrics server binds to `0.0.0.0` or non-localhost interface |
| D3-04 | `src/core/services/prompt_loader.py` | Hardcoded credentials | `python -c "import ast; ast.parse(open('src/core/services/prompt_loader.py').read()); print('AST OK')"` | D3 report must flag the hardcoded VPS path (`/home/guinevere/config/hermes/system-prompt.md`) and note `FileNotFoundError` on non-VPS | Path uses Windows-style (`C:\`) or is otherwise malformed |
| D3-05 | `vps-mirror/systemd-live/guinevere-core.service` | Hardcoded passwords, API keys | `diff -u docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service vps-mirror/systemd-live/guinevere-core.service \|\| true` | D3 report must show the diff and note all 3 divergences (EnvironmentFile, ProtectSystem, ProtectHome) | Diff not documented; divergence status not assessed |
| D3-06 | `vps-mirror/systemd-live/guinevere-9router.service` | Hardcoded passwords, API keys | `cat vps-mirror/systemd-live/guinevere-9router.service` -> inventory properties | D3 report must document that no P1 evidence artifact exists for this service unit and confirm it is a post-P1 creation | N/A |
| D3-07 | `hermes-config/config.yaml` | Plaintext API key (`sk-[a-zA-Z0-9]{20,}`) | `grep -n "key_env\|password\|secret\|token" hermes-config/config.yaml` -> must show env-var references only | D3 report must confirm all 3 LLM provider entries use `key_env: NINEROUTER_API_KEY` pattern (no plaintext) | Any plaintext secret value found in config.yaml |
| D3-08 | `scripts/health-check-p1.sh` | Hardcoded credentials, plaintext passwords | `grep -n "password\|PASSWORD\|secret\|SECRET\|token\|TOKEN\|api_key\|API_KEY" scripts/health-check-p1.sh` -> must reference env vars only | D3 report must classify all 6 health-check commands as NEEDS RUNTIME VERIFICATION and list each with exact verification method | Script contains plaintext secrets |
| D3-09 | `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` | N/A (snapshot) | `wc -l docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` -> confirm 11 keys | D3 report must note this is a point-in-time snapshot and current Redis state is VPS-only | N/A |
| D3-10 | All evidence `.txt` and `.md` files under `docs/setup-evidence/P1/` | `sk-[a-zA-Z0-9]{20,}\|AIza[A-Za-z0-9_-]{35}\|ghp_[a-zA-Z0-9]{36}\|gho_[a-zA-Z0-9]{36}\|ghu_[a-zA-Z0-9]{36}\|ghb_[a-zA-Z0-9]{36}` | `grep -rnE 'sk-[a-zA-Z0-9]{20,}\|AIza[A-Za-z0-9_-]{35}' docs/setup-evidence/P1/ --include="*"` -> must return 0 | D3 report must document grep run, confirm zero results | Any real API key found in evidence files |

**Evidence output path:** `round-1/d3-runtime-readiness.md`
**Forbidden patterns apply to:** all files under `docs/setup-evidence/P1/`, `src/core/services/`, `vps-mirror/`, `hermes-config/`

**VPS verification requirements table** (at end of D3 report):

```
## Appendix: VPS-Only Verification Requirements (R01-R25)

| ID | Claim | Command | Post-Round-1 Verified? |
|----|-------|---------|------------------------|
| R01 | guinevere-core active | systemctl status guinevere-core | NEEDS RUNTIME VERIFICATION |
| R02 | guinevere-9router active | systemctl status guinevere-9router | NEEDS RUNTIME VERIFICATION |
| ... | ... | ... | ... |
| R25 | Prometheus :9191/metrics | curl http://localhost:9191/metrics | NEEDS RUNTIME VERIFICATION |
```

### 3.4 D4: Security-Secrets-Safety

**Goal:** PASS only after exhaustive scan finds zero secrets, zero weakened gates, zero raw LLM paths bypassing Hermes/P20, zero unsafe provider routing.

| # | Expected Files (must read) | Forbidden Patterns (grep must return 0) | Required Commands | Evidence Requirements | Hard Rejection Criteria |
|---|---|---|---|---|---|
| D4-01 | ALL files under `docs/setup-evidence/P1/` | `sk-[a-zA-Z0-9]{20,}` (OpenAI key), `AIza[A-Za-z0-9_-]{35}` (Google key), `gh[opuab]_[a-zA-Z0-9]{36,}` (GitHub token), `-----BEGIN.*KEY-----` (private key) | `grep -rnE 'sk-[a-zA-Z0-9]{20,}\|AIza[A-Za-z0-9_-]{35}\|gh[opuab]_[a-zA-Z0-9]{36,}\|-----BEGIN.*KEY-----' docs/setup-evidence/P1/ --include="*"` -> must return 0 | D4 report must include the grep command, the pattern list, and the zero-result confirmation | Any real API key or private key found in evidence |
| D4-02 | ALL files under `src/core/services/` | Same secret patterns as D4-01 | `grep -rnE 'sk-[a-zA-Z0-9]{20,}\|AIza[A-Za-z0-9_-]{35}\|gh[opuab]_[a-zA-Z0-9]{36,}\|-----BEGIN.*KEY-----' src/core/services/ --include="*.py"` -> must return 0 | D4 report must confirm zero secrets in service modules | Any real API key or private key found in source |
| D4-03 | `hermes-config/config.yaml` | Same secret patterns as D4-01 | `grep -rnE 'sk-[a-zA-Z0-9]{20,}\|AIza[A-Za-z0-9_-]{35}\|gh[opuab]_[a-zA-Z0-9]{36,}' hermes-config/config.yaml` -> must return 0 | D4 report must confirm all provider entries use `key_env:` not `key:` | Any provider entry uses `key:` with an inline value |
| D4-04 | `vps-mirror/systemd-live/*.service` | Same secret patterns as D4-01 | `grep -rnE 'sk-[a-zA-Z0-9]{20,}\|AIza[A-Za-z0-9_-]{35}\|gh[opuab]_[a-zA-Z0-9]{36,}\|-----BEGIN.*KEY-----' vps-mirror/systemd-live/` -> must return 0 | D4 report must confirm zero secrets in systemd unit files | Any real API key or private key in unit files |
| D4-05 | `src/core/main.py` | `LLMRouter\.chat\(` (verify every caller) | `grep -n 'LLMRouter\|\.chat(' src/core/main.py` -> list every occurrence; then for each `.chat(` call, determine if it goes through HermesBrain or bypasses it | D4 report must document every `LLMRouter.chat()` call path and classify as WIRED or UNGATED | Any `.chat()` call outside an approved HermesBrain envelope |
| D4-06 | `src/core/services/llm_router.py` | `base_url.*(http://localhost:20128)` (verify this is the only provider URL); no second URL | `grep -n 'base_url\|provider\|endpoint\|api.*url' src/core/services/llm_router.py` -> must show only `localhost:20128` | D4 report must confirm the only outbound provider URL is to localhost 9Router (no direct provider endpoints) | Any direct provider endpoint URL found (e.g., `api.openai.com`, `api.deepseek.com`) bypassing 9Router |
| D4-07 | `docs/setup-evidence/P1/STEP-P1-021/evidence.md` | `HARD_STOP.*disabled\|HARD_STOP.*false\|hard_stop.*off` | `grep -i 'hard.stop\|consent\|safety.block' docs/setup-evidence/P1/STEP-P1-021/evidence.md` -> must show HARD STOP as active | D4 report must confirm HardStopHandler is ACTIVE in P1-021 evidence and not disabled or bypassed | HardStopHandler evidence describes it as disabled/mocked |
| D4-08 | `src/core/main.py`, `src/core/services/llm_router.py` | `#.*type: ignore\|#.*noqa.*SECURITY\|#.*skip.*safety` | `grep -n 'type: ignore\|noqa.*SEC\|noqa.*SAFE\|noqa.*AUDIT' src/core/main.py src/core/services/llm_router.py` -> must return 0 | D4 report must confirm no audit-suppression comments exist in security-critical files | Any `type: ignore` or `noqa` that suppresses security warnings in critical paths |
| D4-09 | `hermes-config/config.yaml` | `send_unsafe\|bypass_safety\|disable_safety\|ignore_security` | `grep -n 'unsafe\|bypass.*safety\|disable.*safety\|ignore.*security' hermes-config/config.yaml` -> must return 0 | D4 report must confirm no safety-bypass options are enabled in config.yaml | Any safety-bypass option set to `true`/`yes` |

**Evidence output path:** `round-1/d4-security-secrets-safety.md`
**Forbidden patterns apply to:** ALL files, including evidence, source, config, unit files, scripts

---

## 4. DEPENDENCY MAP & PARALLELISM

```
                    ┌─────────────────────────────────────────────┐
                    │              ROUND 1 (PARALLEL)             │
                    │                                             │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌┐ │
                    │  │  D1     │  │  D2     │  │  D3     │  │D4│ │
                    │  │ ARCH-   │  │ DOCS-   │  │ RUNTIME-│  │SEC│ │
                    │  │ IMPL    │  │CONSIST  │  │READY    │  │   │ │
                    │  └────┬────┘  └────┬────┘  └────┬────┘  └─┬─┘ │
                    │       │            │            │         │    │
                    │       └─────┬──────┘────────────┘─────────┘    │
                    │             │  (all independent)               │
                    └─────────────┼──────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────────────────┐
                    │           ROUND 2 (SERIAL ON R1)            │
                    │                                             │
                    │  ADVERSARIAL VERIFICATION: Challenge each   │
                    │  dimension's PASS/FAIL. Cross-check D1-D4.  │
                    │  Find contradictions between dimensions.    │
                    │  E.g., D1 says "implemented" but D3 says    │
                    │  "cannot run" = PARTIALLY IMPLEMENTED.      │
                    └────────────────────┬────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────┐
                    │           REGISTERS (SERIAL ON R1+R2)       │
                    │                                             │
                    │  - CONSISTENCY REGISTER: R1 findings table  │
                    │  - BLOCKER REGISTER: downstream risks       │
                    │  - VPS REGISTER: all NEEDS RUNTIME items    │
                    └────────────────────┬────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────┐
                    │           FINAL REPORT                      │
                    │  Reconciled status per claim + overall      │
                    └─────────────────────────────────────────────┘
```

**Parallelism rules:**
- D1, D2, D3, D4 run in parallel in Round 1 (no cross-dependency)
- Round 2 (Adversarial Verify) depends on ALL of D1-D4 being complete
- Registers depend on both Round 1 and Round 2
- Final Report depends on Registers
- Each round auditor is a separate subagent invocation

---

## 5. AUDITOR MATRIX

Which dimension verifies which P1 step-range:

| Dimension | P1 Steps Covered | Rationale |
|-----------|-----------------|-----------|
| **D1** | P1-015, P1-016, P1-017, P1-018, P1-019(P1), P1-020, P1-021 | All steps that produced source artifacts (llm_router.py, prompt_loader.py, main.py, smoke tests, health script, cost_tracker.py, hard_stop_handler.py) |
| **D2** | P1-001 through P1-021 (all evidence files) | Evidence-docs consistency covers the entire P1 evidence corpus and project management cross-references |
| **D3** | P1-001, P1-002, P1-003, P1-004, P1-005, P1-006, P1-018, P1-019, P1-020 | Infrastructure steps (runtime installs, config, systemd, Redis, health checks) where runtime correctness matters |
| **D4** | P1-005(config), P1-007, P1-015, P1-016, P1-020, P1-021 | All steps where secrets could leak or safety gates could be weakened (config files, LLM routing, HARD STOP, cost tracking) |

**Cross-cutting:** Steps P1-015, P1-016, P1-018, P1-020, P1-021 appear in multiple dimensions. The final reconciliation must reconcile per-dimension verdicts for these steps.

---

## 6. ROLLBACK / CAVEATS

### 6.1 Read-Only Constraints
- This audit plan produces zero fixes, zero edits, zero deletions, zero creations outside the output path.
- All 3 research files (p1-repo-evidence-inventory.md, p1-runtime-readiness-readonly.md, p1-downstream-impact-p19-p24.md) were produced by READ-ONLY operations.
- Round-1 D1-D4 auditors are READ-ONLY subagents. They must write their findings to the assigned output path, not modify any other file.

### 6.2 VPS-Gated Limitations
- 25 of 35 verification points (R01-R25) require VPS SSH access. Round-1 cannot fully verify these.
- The D3 report MUST clearly separate "Verified Locally" from "Needs Runtime Verification".
- Smoke tests (P1-017) spend real LLM credits via 9Router. The round-1 auditor must NOT trigger these.
- The HardStopHandler 14 model compliance tests (P1-021, R19) require cockp it LLM access with real credits.

### 6.3 Encoding Defect Acceptance
- Three evidence files (E17, E20, E27) have SSH UTF-16LE capture encoding defects. The D2 auditor MUST confirm these are genuine captures with wrong encoding, not fabrication, and recommend re-capture during a maintenance cycle.
- These files MUST NOT be treated as "corrupted/broken" without the UTF-16 decode analysis.

### 6.4 Stale Snapshot Acknowledgment
- The P1-015 `llm_router.py` evidence snapshot (90 lines) is historically accurate for P1 but substantially superseded by Phase 6. This is not a P1 failure -- it is normal code evolution.
- The audit must distinguish between "P1 implementation is missing" vs "P1 was replaced by later phases". These are different verdicts.
- If `LLMRouter.chat()` still exists and works (it does), P1-015 is technically implemented even though the implementation is now a Phase 6 rewrite of the P1 original.

### 6.5 No VPS SSH, No Decrypt
- Round-1 auditors MUST NOT attempt SSH, curl to live services, systemctl, or SOPS decryption.
- Any VPS-only claim must be annotated "NEEDS RUNTIME VERIFICATION" and added to the VPS register for round-2 or post-audit runtime checks.

---

## 7. FINAL STATUS RULE

### 7.1 Allowed Statuses (per P1 claim)

Each of the 21 P1 steps receives ONE of these statuses in the final report:

| Status | Definition | When to Use |
|--------|-----------|-------------|
| **VERIFIED IMPLEMENTED** | Source code exists, matches P1 claims (or superseded by equivalent-or-better), evidence is consistent, safe local checks pass | P1-001, P1-002, P1-003, P1-004, P1-005, P1-006, P1-007, P1-008, P1-009, P1-010, P1-011, P1-012, P1-013, P1-014 |
| **IMPLEMENTED WITH BUGS** | Source exists, behavior is P1-intended, but specific bugs found during AST/import/grep inspection | Only if round-1 finds concrete bugs (not just drift) |
| **IMPLEMENTED WITH DOC GAPS** | Source exists and works, but evidence does not fully document current state | P1-015 (source exists but evidence snapshot stale); P1-016 (prompt_loader grew 6x, evidence out of date); P1-018 (service unit drifted); P1-020 (CostTracker expanded) |
| **PARTIALLY IMPLEMENTED** | Key functionality is implemented but substantial P1 claims cannot be verified without runtime access | P1-017 (smoke tests exist but require VPS/credits); P1-019 (health checks cover P1 services but 100% VPS); P1-021 (deterministic tests OK, model tests VPS) |
| **DOCS CLAIM ONLY** | Evidence exists but no matching live source code behavior can be demonstrated | N/A -- not expected for P1 (all source artifacts exist) |
| **SUPERSEDED BY LATER PHASE** | P1 claim was implemented, then replaced/rewritten by a later phase with equivalent or better functionality | P1-015 (Phase 6 rewrote llm_router.py); P1-018 (main.py grew from skeleton to full app); P1-005 config (replaced by Hermes gateway config) |
| **NEEDS RUNTIME VERIFICATION** | Cannot be confirmed without VPS access (services, DB, LLM calls, metrics) | R01-R25; P1-017, P1-019, P1-020 runtime state |

### 7.2 Reconciliation Rule

The final report MUST reconcile source + evidence + runtime-readiness before any PASS verdict. A step that is "VERIFIED IMPLEMENTED" in D1 but "NEEDS RUNTIME VERIFICATION" in D3 cannot be given VERIFIED IMPLEMENTED overall -- the lowest status across all three dimensions for that step governs.

**For example:**
- P1-015: D1 says source exists (253 lines) = IMPLEMENTED. D2 says evidence snapshot stale = DOC GAP. D3 says needs runtime to verify live model routing = NEEDS RUNTIME. **Overall: NEEDS RUNTIME VERIFICATION / IMPLEMENTED WITH DOC GAPS** (combined).
- P1-020: D1 says CostTracker code exists. D2 says evidence consistent. D3 says Redis state is VPS-only. **Overall: NEEDS RUNTIME VERIFICATION** (for runtime state) / **IMPLEMENTED** (for source code).

### 7.3 Overall P1 Verdict

The final report must also assign an overall P1 audit verdict from:

- **FULLY VERIFIED** -- All 21 steps VERIFIED IMPLEMENTED, no gaps, no runtime-only claims
- **IMPLEMENTED WITH MINOR GAPS** -- Core implementation exists, evidence has minor defects, docs need updating
- **IMPLEMENTED WITH SIGNIFICANT GAPS** -- Substantial claims require VPS, evidence stale for key artifacts, downstream blockers identified
- **SUBSTANTIALLY SUPERSEDED** -- P1 foundation exists but later phases have rewritten key components; P1 as original spec is no longer the canonical implementation

Based on the three research passes, the expected overall verdict is **IMPLEMENTED WITH SIGNIFICANT GAPS** or **SUBSTANTIALLY SUPERSEDED** -- pending round-1 D1-D4 confirmation.

---

## Appendix A: Research Documents Consumed

| Document | Path |
|----------|------|
| P1 Repo Evidence Inventory | `docs/setup-evidence/legacy-audit/P1/research/p1-repo-evidence-inventory.md` |
| P1 Runtime Readiness (Read-Only) | `docs/setup-evidence/legacy-audit/P1/research/p1-runtime-readiness-readonly.md` |
| P1 Downstream Impact P19-P24 | `docs/setup-evidence/legacy-audit/P1/research/p1-downstream-impact-p19-p24.md` |

## Appendix B: File Path Reference (Absolute)

All paths relative to `C:/Users/faizz/guinevere` (use forward slashes in tool calls).

```
C:/Users/faizz/guinevere/
  src/core/services/llm_router.py
  src/core/services/cost_tracker.py
  src/core/services/llm_metrics.py
  src/core/services/prompt_loader.py
  src/core/main.py
  src/core/hard_stop_handler.py
  tests/smoke/conftest.py
  tests/safety/test_hard_stop_handler.py
  scripts/health-check-p1.sh
  vps-mirror/systemd-live/guinevere-core.service
  vps-mirror/systemd-live/guinevere-9router.service
  hermes-config/config.yaml
  CHECKLIST.md
  PROGRESS.md
  docs/60-persona/61-SystemPromptMaster_v1.1.md
  docs/setup-evidence/P1/
    STEP-P1-001/  through  STEP-P1-021/
    batch-plan-004-005.md
    batch-plan-006-007.md
    batch-plan-017-019.md
    migration-9router/evidence.md
    p2-preconditions-resolved.md
    adr-028-skip-ollama.md
  docs/setup-evidence/legacy-audit/P1/
    research/p1-repo-evidence-inventory.md
    research/p1-runtime-readiness-readonly.md
    research/p1-downstream-impact-p19-p24.md
    plan/p1-implementation-audit-plan.md          <-- THIS FILE
    round-1/d1-architecture.md                   <-- AUDITOR OUTPUT
    round-1/d2-evidence-docs-consistency.md      <-- AUDITOR OUTPUT
    round-1/d3-runtime-readiness.md              <-- AUDITOR OUTPUT
    round-1/d4-security-secrets-safety.md        <-- AUDITOR OUTPUT
```

---

*End of audit plan. READ-ONLY -- no files modified beyond this plan document.*
