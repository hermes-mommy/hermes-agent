# Phase 6 — LLM Routing & Budget Enforcement Planner Gate

**Date:** 2026-06-06  
**Status:** PLANNER GATE / implementation not started  
**Evidence root:** `docs/setup-evidence/phase-6/`  
**Governing ADR:** `adr/ADR-035-hermes-migration.md` Phase 6 / Pillar 5  
**User authorization:** Deploy/restart `hermes-gateway`, verify runtime, `git add -A`, commit, tag `v1.0-post-phase6-llm-routing`, push `origin main` after gates pass.

## 0. Binding Decisions and Conflict Resolution

| Conflict | Binding Decision | Evidence / Reason |
|---|---|---|
| ADR-035 says GPT-5.5 primary; user requires DeepSeek primary | Use `ds/deepseek-v4-flash` as Phase 6 primary through provider `ninerouter` at `http://localhost:20128/v1` | User hard constraint overrides; `cx/gpt-5.5` has expired Codex credential per `research-reports/phase-6-execution/03-fallback-verify.md` |
| User mentions `ninerouter/balance` fallback | Do not use exact `ninerouter/balance` unless runtime proves it exists. Prefer `guinevere` VPS 9Router combo as operational fallback; register `cx/gpt-5.5` only as known-degraded if CLI/config supports it without breaking startup | `ninerouter/balance` is not a valid model ID in research; VPS `guinevere` exists and is the known combo |
| User asked `src/hermes/plugins/budget_hook.py` + `plugins.enabled`; existing runtime uses shell hooks | Use actual Hermes-supported `hooks.pre_tool_call` shell hook registration for existing `hermes-config/hooks/budget_check.py`; do not invent unsupported plugin architecture. Keep `plugins.enabled` unchanged unless runtime docs/CLI prove `budget_hook` plugin exists | `research-reports/phase-6-execution/04-budget-state.md`; VPS config has `plugins.enabled: [auth_overlay, guinevere-persona]`, hooks consent/DNR only |
| Budget hook old plan says fail-open in a caveat | Fail-closed is mandatory. Redis/Lua/config failures block with reason including `budget_check_failed` where applicable | User hard constraint |
| Prometheus metrics required; Hermes lacks native `/metrics` | Add project exporter/metrics integration sufficient to expose `localhost:9191/metrics` and add Prometheus scrape job | `research-reports/phase-6-7-planning/02-fallback-chain.md` says no native Prometheus |
| Research report contains secret-like bearer token | Sanitize before any commit/push and run secret scan | AGENTS.md hard block: never commit secrets |

## 1. Research Inputs Read and Applied

- `docs/setup-evidence/hermes-migration/batch-plan-phase-6.md`
- `adr/ADR-035-hermes-migration.md`
- `research-reports/phase-6-execution/01-llm-state.md`
- `research-reports/phase-6-execution/02-costtracker-state.md`
- `research-reports/phase-6-execution/03-fallback-verify.md`
- `research-reports/phase-6-execution/04-budget-state.md`
- `research-reports/phase-6-7-planning/01-llm-state.md`
- `research-reports/phase-6-7-planning/02-fallback-chain.md`
- `research-reports/phase-6-7-planning/08-token-cost.md`
- `src/core/services/llm_router.py`
- `src/core/services/cost_tracker.py`
- `hermes-config/config.yaml`

## 2. Known State

- VPS Hermes is v0.15.2, `hermes-gateway.service` active, 9Router active at `localhost:20128`.
- VPS `/home/guinevere/.hermes/config.yaml` currently uses provider `ninerouter`, base URL `http://localhost:20128/v1`, model `ds/deepseek-v4-flash`, empty `fallback_providers`, plugins `auth_overlay` and `guinevere-persona`, and no budget hook.
- Local `hermes-config/config.yaml` uses older template style and has consent/DNR shell hooks only; budget section is informational.
- Existing budget hook implementation exists under `hermes-config/hooks/`: `budget_check.py`, `budget_lua.py`, `budget_lua_extended.py`, `_hook_utils.py`. It is not registered.
- `src/core/services/llm_router.py` has stale pricing, no `CostTracker`, fallback chain, and a narrow SSE `[DONE]` strip.
- `src/core/services/cost_tracker.py` writes Redis DB5 keys and propagates failures.
- Redis DB5 runtime verification must happen through SSH/VPS; do not expose Redis password.

## 3. Master Todo and Dependency Map

| Step | Task | Mode | Depends On | Evidence |
|---|---|---|---|---|
| 0 | Sanitize leaked bearer token in `research-reports/phase-6-execution/03-fallback-verify.md` | sequential | none | `STEP-0/verification.md` |
| 1 | Inspect plugin/hook and metrics patterns immediately before implementation | sequential | none | `STEP-1/verification.md` |
| 2 | Wire `CostTracker` and metrics hooks into `src/core/services/llm_router.py`; update pricing; robust SSE strip | sequential | 1 | `STEP-2/verification.md` |
| 3 | Update or create tests for LLM router cost tracking, fail-closed behavior, pricing, SSE stripping, and metrics | sequential | 2 | `STEP-3/verification.md` |
| 4 | Update budget hook to return/emit `budget_check_failed` on Redis/Lua cost-check failure, without fail-open behavior | sequential | 1 | `STEP-4/verification.md` |
| 5 | Register budget hook in local `hermes-config/config.yaml` and sync/deploy hook files/config to VPS `~/.hermes/` | sequential | 4 | `STEP-5/verification.md` |
| 6 | Configure/verifiably reconcile fallback chain through Hermes/9Router without direct provider calls | sequential | 1 | `STEP-6/verification.md` |
| 7 | Add Prometheus scrape job and exporter/runtime exposure for required LLM metrics on `localhost:9191` | sequential | 2 | `STEP-7/verification.md` |
| 8 | Restart `hermes-gateway`; verify service, logs, 9Router health, and hook loading | sequential | 5,6,7 | `STEP-8/verification.md` |
| 9 | Run 100-prompt VPS integration test through 9Router and verify no direct provider calls or SSE artifacts | sequential | 8 | `STEP-9/verification.md` |
| 10 | Verify Redis DB5 cost keys and budget fail-closed block behavior | sequential | 9 | `STEP-10/verification.md` |
| 11 | Update `PROGRESS.md` and final evidence index | sequential | 10 | `STEP-11/verification.md` |
| 12 | Run three independent auditors: routing correctness, cost accuracy, ADR-035 compliance | parallel audit batch | 11 | `STEP-12/*/auditor-gate.md` |
| 13 | Git workflow: status/diff/log, secret scan, stage intended files, commit, tag, push | sequential | 12 PASS | `STEP-13/verification.md` |

Planner parallelism decision: implementation is sequential because shared config, runtime service, Redis budget state, and git/evidence writers collide. Audit wave is parallel after parent verification.

## 4. Collision Scan

| Resource | Steps | Risk | Mitigation |
|---|---|---|---|
| `research-reports/phase-6-execution/03-fallback-verify.md` | 0 | Secret leakage | Sanitize first; scan before commit |
| `src/core/services/llm_router.py` | 2,3 | Single source file | One implementation owner; tests follow same step sequence |
| `hermes-config/hooks/*` | 4,5 | Runtime hook behavior | One hook owner; deploy only after tests |
| `hermes-config/config.yaml` and VPS `~/.hermes/config.yaml` | 5,6,8 | Shared config | Backup before edit; parent verifies YAML and service startup |
| Redis DB5 | 9,10 | Budget mutation | Record pre/post; restore cap to `$30` after fail-closed test |
| `monitoring/prometheus/prometheus.yml` | 7 | YAML scrape config | YAML parse check |
| Evidence root | all | Multi-writer docs | Parent-owned evidence writes unless verifier/auditor has explicit path |
| Git tree | 13 | Secrets/unintended files | status/diff/log/secret scan before staging |

## 5. Files to Create or Modify

### Expected local modifications

- `research-reports/phase-6-execution/03-fallback-verify.md` — redact leaked token only.
- `src/core/services/llm_router.py` — CostTracker, pricing, fail-closed, SSE, metrics.
- `hermes-config/hooks/budget_check.py` — exact `budget_check_failed` reason on Redis/Lua cost-check failure if not already present.
- `hermes-config/config.yaml` — register budget shell hook and fallback config if local template is source of truth.
- `monitoring/prometheus/prometheus.yml` — add scrape job `hermes-llm-routing` target `localhost:9191`.
- Tests under `tests/hermes/` as needed for router, budget hook, and metrics.
- `PROGRESS.md`.
- Evidence files under `docs/setup-evidence/phase-6/`.

### Expected VPS modifications

- `~/.hermes/hooks/budget_check.py`
- `~/.hermes/hooks/budget_lua.py`
- `~/.hermes/hooks/budget_lua_extended.py`
- `~/.hermes/hooks/_hook_utils.py`
- `~/.hermes/config.yaml` with budget hook registration and fallback chain, after backup.

### Must not create unless runtime proves support

- `src/hermes/plugins/budget_hook.py`
- New `plugins.enabled` entry `budget_hook`

## 6. Implementation Design

### 6.1 LLM router

- Keep all model calls through `http://localhost:20128/v1`.
- Update pricing constants:
  - `cx/gpt-5.5`: input `0.005`, output `0.03` per 1K.
  - `ds/deepseek-v4-flash`: input `0.00014`, output `0.00028` per 1K.
  - `guinevere`: input `0.00014`, output `0.00028` per 1K.
- Initialize `CostTracker` in `LLMRouter.__init__`.
- After successful HTTP response, SSE strip, and JSON parse, extract `usage.prompt_tokens` and `usage.completion_tokens`.
- Call `CostTracker.record_cost()` before returning the result.
- If cost tracking raises, log `llm_cost_tracking_failed` and raise exactly `RuntimeError("LLM cost tracking failed")`; do not allow fallback loop to swallow this as a provider failure.
- Robust SSE strip must remove both trailing `data: [DONE]` and `data:[DONE]`.
- Metrics should record successful calls, failed provider attempts, latency, cost, and fallback activation.

### 6.2 Budget hook

- Use existing shell hook architecture.
- Budget cap: monthly `$30`, alert `$24`, hard block `$30`.
- Daily caps: preserve existing per-tool daily caps in `budget_lua_extended.py`.
- Redis/Lua/cost-check failures must block with reason including `budget_check_failed`.
- Register as `hooks.pre_tool_call` with `priority: 100`, `timeout_ms: 500`, `on_failure: block`, before existing consent hook priority 90.

### 6.3 Fallback chain

- Primary must remain `ds/deepseek-v4-flash`.
- Verify `cx/gpt-5.5` availability but treat expired credential as degraded, not a reason to switch away from DeepSeek primary.
- Prefer `guinevere` combo as operational fallback because `ninerouter/balance` is invalid and `balance` is local-only/broken in research.
- All fallback traffic still goes through 9Router localhost:20128.

### 6.4 Prometheus metrics

Expose these metric families:

- `hermes_llm_calls_total{model,status}`
- `hermes_llm_latency_seconds`
- `hermes_llm_cost_usd_total`
- `hermes_fallback_activations_total`

Add Prometheus scrape job:

```yaml
- job_name: hermes-llm-routing
  static_configs:
    - targets: ["localhost:9191"]
```

## 7. Token and Secret Handling

- Never print or commit `NINEROUTER_API_KEY`, Redis password, SOPS/age keys, OAuth tokens, or product keys.
- Replace the leaked bearer token in `research-reports/phase-6-execution/03-fallback-verify.md` with `[REDACTED_LOCAL_9ROUTER_API_KEY]` before any commit.
- Secret scan must run before staging and before commit.
- Evidence may include key names and env var names only, not values.

## 8. Rollback Plan

| Step | Rollback |
|---|---|
| 0 | Re-edit redaction only if marker is malformed; never restore token into committed content |
| 2,3 | `git checkout -- src/core/services/llm_router.py tests/hermes/` for local rollback before commit |
| 4 | `git checkout -- hermes-config/hooks/budget_check.py` |
| 5,6 | Restore VPS `~/.hermes/config.yaml` from pre-Phase 6 backup and restart `hermes-gateway` |
| 7 | Remove added scrape job/exporter files before commit |
| 10 | Restore `budget:monthly_cap` to `30.0` immediately after fail-closed test |
| 13 | If pushed/tagged incorrectly, stop and ask Faiz before destructive git rollback |

## 9. Auditor Matrix

| Auditor | Output Path | Scope | Required Verdict |
|---|---|---|---|
| LLM routing correctness | `docs/setup-evidence/phase-6/STEP-12/routing/auditor-gate.md` | 9Router-only routing, DeepSeek primary, fallback chain, SSE strip, 100-prompt test, service logs | PASS |
| Cost accuracy | `docs/setup-evidence/phase-6/STEP-12/cost/auditor-gate.md` | CostTracker wire, pricing constants, Redis DB5 deltas, budget fail-closed | PASS |
| ADR-035 compliance | `docs/setup-evidence/phase-6/STEP-12/adr/auditor-gate.md` | ADR deviations documented, no direct providers, $30 cap, Phase 6 gate criteria | PASS |

## 10. Per-Step Verification Scaffolds

### Step 0 — Secret Sanitization

| Field | Concrete Requirement |
|---|---|
| Expected Files | `research-reports/phase-6-execution/03-fallback-verify.md` |
| Forbidden Patterns | Real `sk-` token values; regex `sk-[A-Za-z0-9_-]{20,}` except approved redaction marker; `NINEROUTER_API_KEY=` |
| Required Commands | `grep -nE "sk-[A-Za-z0-9_-]{20,}" research-reports/phase-6-execution/03-fallback-verify.md` → no real secret values; `grep -c "\[REDACTED_LOCAL_9ROUTER_API_KEY\]" research-reports/phase-6-execution/03-fallback-verify.md` → expected `2`; `git diff -- research-reports/phase-6-execution/03-fallback-verify.md` → redaction-only diff |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-0/verification.md` with command outputs and diff summary |
| Hard Rejection Criteria | Any unreplaced token; any extra content edits beyond redaction |

### Step 1 — Pre-Implementation Pattern Inspection

| Field | Concrete Requirement |
|---|---|
| Expected Files | Evidence only; no source modification |
| Forbidden Patterns | Inline assumptions about plugin/metrics architecture without file evidence |
| Required Commands | Read/list `src/hermes`, `src/hermes_plugins`, `hermes-config/hooks`, `monitoring/prometheus/prometheus.yml`; grep for existing `prometheus_client`, `Counter(`, `Histogram(`, `plugins.enabled`, `hooks.pre_tool_call` |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-1/verification.md` with inspected paths and chosen implementation pattern |
| Hard Rejection Criteria | Proceeding to Step 2/4/7 without confirming actual file layout |

### Step 2 — LLM Router Implementation

| Field | Concrete Requirement |
|---|---|
| Expected Files | `src/core/services/llm_router.py` |
| Forbidden Patterns | `as any`, `@ts-ignore`, `@ts-expect-error`, `# type: ignore`, `except Exception: pass`, empty catches, direct provider URLs other than `http://localhost:20128/v1` |
| Required Commands | grep `CostTracker` in router → import/use present; grep `record_cost` → called after successful response; grep `LLM cost tracking failed` → exact RuntimeError text present; grep pricing constants → required values present; grep SSE regex/test helper → handles `data:\s?\[DONE\]`; `lsp_diagnostics src/core/services/llm_router.py` → no errors |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-2/verification.md` with diff and diagnostics |
| Hard Rejection Criteria | Cost failure can be swallowed by fallback loop; stale pricing remains; direct provider URL introduced; type suppression introduced |

### Step 3 — LLM Router Tests

| Field | Concrete Requirement |
|---|---|
| Expected Files | `tests/hermes/test_llm_router_cost.py` or existing test file updated |
| Forbidden Patterns | `pytest.skip`, unreasoned `xfail`, fake assertions, network dependency in unit tests |
| Required Commands | `python -m pytest tests/hermes/test_llm_router_cost.py -v` → exit 0; test must cover success cost recording, cost failure RuntimeError, pricing constants, SSE strip variants, no fallback swallowing cost failure |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-3/verification.md` with pytest output |
| Hard Rejection Criteria | Missing any required test surface; tests require live 9Router for unit behavior |

### Step 4 — Budget Hook Fail-Closed Update

| Field | Concrete Requirement |
|---|---|
| Expected Files | `hermes-config/hooks/budget_check.py` and possibly hook tests |
| Forbidden Patterns | `except Exception: pass`, `on_failure: warn`, fail-open wording for Redis/Lua/cost-check failure |
| Required Commands | grep `budget_check_failed` → present; grep empty catch patterns → none; `python -m py_compile hermes-config/hooks/budget_check.py`; run existing budget hook tests if present (`python -m pytest tests/hermes/test_budget_hook.py -v`) → exit 0 |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-4/verification.md` with py_compile and pytest outputs |
| Hard Rejection Criteria | Redis/Lua failure returns allow/pass; `budget_check_failed` absent where cost-check failure is emitted |

### Step 5 — Config Registration and VPS Deploy

| Field | Concrete Requirement |
|---|---|
| Expected Files | `hermes-config/config.yaml`; VPS `~/.hermes/config.yaml`; VPS hook files |
| Forbidden Patterns | `on_failure: warn`, `timeout_ms` above `1000`, removing consent/DNR hooks, plaintext secrets in config |
| Required Commands | YAML parse local config; grep budget hook local config shows priority 100/on_failure block; SSH backup VPS config; SCP hook files; YAML parse VPS config; grep VPS config budget hook; list VPS hook files; py_compile VPS hook |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-5/verification.md` with backup path and command outputs |
| Hard Rejection Criteria | No VPS backup; YAML parse failure; existing consent/DNR hooks removed; secret value appears in config |

### Step 6 — Fallback Chain Verification

| Field | Concrete Requirement |
|---|---|
| Expected Files | `hermes-config/config.yaml` and/or VPS config only if fallback needs config update |
| Forbidden Patterns | Direct OpenAI/OpenRouter provider endpoints; `ninerouter/balance` unless runtime `/v1/models` proves it exists |
| Required Commands | SSH curl `http://localhost:20128/v1/models` → HTTP 200; verify primary `ds/deepseek-v4-flash`; verify fallback model(s) exist (`guinevere`, optionally `cx/gpt-5.5` as degraded); `hermes fallback list` on VPS if CLI supports it, or YAML grep if fallback is config-based |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-6/verification.md` with model list summary and fallback decision |
| Hard Rejection Criteria | Exact `ninerouter/balance` used without proof; direct provider URL; startup-breaking fallback config |

### Step 7 — Prometheus Metrics

| Field | Concrete Requirement |
|---|---|
| Expected Files | Metrics exporter/integration file(s), tests, `monitoring/prometheus/prometheus.yml` |
| Forbidden Patterns | Hardcoded secrets; direct provider calls; empty catches |
| Required Commands | Metrics tests pass; YAML parse `monitoring/prometheus/prometheus.yml`; grep scrape job `hermes-llm-routing`; curl `http://localhost:9191/metrics` on runtime → all four metric families present |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-7/verification.md` with metrics output sample |
| Hard Rejection Criteria | Any required metric absent; port not `9191`; scrape target not `localhost:9191` |

### Step 8 — Service Restart and Runtime Health

| Field | Concrete Requirement |
|---|---|
| Expected Files | Runtime logs only |
| Forbidden Patterns | `Traceback`, hook load errors, Redis connection errors causing allow/pass, direct provider logs |
| Required Commands | SSH `sudo systemctl restart hermes-gateway`; `systemctl is-active hermes-gateway` → `active`; journalctl recent logs show no tracebacks; curl 9Router health/models → HTTP 200 |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-8/verification.md` with status/log/HTTP outputs |
| Hard Rejection Criteria | Gateway inactive; hook startup failure; 9Router not reachable |

### Step 9 — 100-Prompt Integration

| Field | Concrete Requirement |
|---|---|
| Expected Files | Test harness/logs under evidence root or `/tmp` copied into evidence |
| Forbidden Patterns | HTTP 401/403/5xx; `data: [DONE]` artifacts in parsed output; direct provider URLs |
| Required Commands | Run 100 prompts via Hermes/9Router on VPS; success count >= 95; verify model/provider route is 9Router/DeepSeek primary; grep logs for direct provider calls → none |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-9/verification.md` with summary, sample prompts, counts |
| Hard Rejection Criteria | <95 successful prompts; any direct provider route; SSE artifacts remain |

### Step 10 — Redis DB5 Cost and Budget Fail-Closed

| Field | Concrete Requirement |
|---|---|
| Expected Files | Evidence only |
| Forbidden Patterns | Redis `FLUSHDB`; leaving budget cap below `$30`; printing Redis password |
| Required Commands | SSH Redis DB5 `GET cost:current_month` > 0; `KEYS cost:by_model:*` contains expected model; `GET cost:monthly:2026-06` > 0; temporarily set cap low, trigger budget block, verify block reason includes budget failure, restore cap `30.0`, confirm restored |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-10/verification.md` with redacted Redis command outputs and cap restore proof |
| Hard Rejection Criteria | Cost keys unchanged; budget fail-open; cap not restored |

### Step 11 — PROGRESS and Evidence Sync

| Field | Concrete Requirement |
|---|---|
| Expected Files | `PROGRESS.md`, `docs/setup-evidence/phase-6/*` |
| Forbidden Patterns | Secrets, raw credentials, intimate/personal data, false PASS claims |
| Required Commands | grep `Phase 6` in `PROGRESS.md`; list evidence directories; verify each step evidence file exists; markdown table sanity check if applicable |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-11/verification.md` |
| Hard Rejection Criteria | Missing evidence for any completed step; PROGRESS claims completion before auditors pass |

### Step 12 — Auditor Gates

| Field | Concrete Requirement |
|---|---|
| Expected Files | `docs/setup-evidence/phase-6/STEP-12/routing/auditor-gate.md`, `docs/setup-evidence/phase-6/STEP-12/cost/auditor-gate.md`, `docs/setup-evidence/phase-6/STEP-12/adr/auditor-gate.md` |
| Forbidden Patterns | Inline-only auditor reports; self-audit without file output |
| Required Commands | Parent reads all three auditor files; each file contains `VERDICT: PASS`; any NEEDS REVIEW/FAIL is fixed and re-audited via same `task_id` |
| Evidence Requirements | Three auditor gate files and parent verification note |
| Hard Rejection Criteria | Any auditor not PASS; auditor did not inspect actual changed files/evidence |

### Step 13 — Git Commit, Tag, Push

| Field | Concrete Requirement |
|---|---|
| Expected Files | Git commit and tag |
| Forbidden Patterns | Any secret regex in staged diff; unstaged intended changes; committing `.env`, key files, decrypted secrets |
| Required Commands | Load `git-master` skill; `git status`; `git diff`; `git log --oneline -10`; secret scan; `git add -A` only after scan; `git diff --cached`; `git commit -m "feat: Phase 6 LLM routing ..."`; `git tag v1.0-post-phase6-llm-routing`; `git push origin main`; `git push origin v1.0-post-phase6-llm-routing` |
| Evidence Requirements | `docs/setup-evidence/phase-6/STEP-13/verification.md` with commit SHA, tag, push outputs |
| Hard Rejection Criteria | Secret scan hit; unreviewed staged files; push failure; missing tag |

## 11. Final Done Criteria

Phase 6 is complete only when all are true:

- 9Router HTTP 200 at `localhost:20128`.
- Primary DeepSeek through provider `ninerouter` verified.
- Operational fallback chain documented and configured without invalid `ninerouter/balance`.
- Budget hook active and fail-closed.
- `CostTracker.record_cost()` called after every successful LLM response in `llm_router.py`.
- Redis DB5 cost keys updated after live traffic.
- No direct provider calls.
- `hermes-gateway` active after restart.
- 100-prompt test passes >= 95/100 via 9Router.
- Prometheus scrape job target `localhost:9191` configured and metrics exposed.
- No empty catch, type suppression, or committed secrets.
- Three auditor gates PASS.
- `PROGRESS.md` and evidence complete.
- Commit, tag, and push complete.

## 12. Final Report Required to Faiz

Final report must include:

- 9Router status.
- Fallback chain config.
- CostTracker wire result.
- Redis DB5 keys observed.
- Budget enforcement result.
- Prometheus scrape/metrics status.
- Three auditor verdicts.
- Commit SHA and tag.
- Phase 7 readiness: YES/NO with blockers.
