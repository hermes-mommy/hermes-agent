# D4: Security-Secrets-Safety Audit Report

**Auditor:** READ-ONLY D4 subagent  
**Date:** 2026-06-25  
**Plan Reference:** `docs/setup-evidence/legacy-audit/P1/plan/p1-implementation-audit-plan.md`, Section 3.4  
**Status:** COMPLETE (local only; 0 VPS checks required for D4)  
**Output Path:** `docs/setup-evidence/legacy-audit/P1/audits/round-1/d4-security-secrets-safety.md`

---

## Per-Check Results Table

| Check ID | Command / Description | Actual Output | PASS/FAIL | Notes |
|----------|----------------------|---------------|-----------|-------|
| D4-01 | Secret scan on all `docs/setup-evidence/P1/` files: `sk-*`, `AIza*`, `gh[opuab]_*`, `-----BEGIN.*KEY-----` | 0 matches (exit 1) | **PASS** | No secrets in evidence corpus |
| D4-02 | Secret scan on `src/core/services/*.py` | 0 matches (exit 1) | **PASS** | No secrets in service modules |
| D4-03 | Secret scan on `hermes-config/config.yaml` | 0 matches (exit 1); all 3 providers use `key_env:` (lines 57, 67, 71) | **PASS** | No inline `key:` values; env-var references only |
| D4-04 | Secret scan on `vps-mirror/systemd-live/*.service` | 0 matches (exit 1) | **PASS** | No secrets in systemd unit files |
| D4-05 | `LLMRouter.chat()` caller enumeration | 6 active callers across `src/loops/`, `src/memory/`, `src/self_improve/` | **NEEDS-REVIEW** | See detailed classification below |
| D4-06 | Provider endpoint check in `llm_router.py` | All 3 `base_url` = `http://localhost:20128/v1`; no direct provider URLs | **PASS** | 9Router-only architecture confirmed |
| D4-07 | HARD STOP status in P1-021 evidence | HardStopHandler is ACTIVE: 56/56 unit tests + 14/14 model tests, model-independent pre-LLM guard | **PASS** | No disabled/mocked status found |
| D4-08 | Audit-suppression comments in security-critical files | Only `noqa: BLE001` (broad-except, fail-soft pattern) and `noqa: PLW0603`/`PLC0415` (lint); no security-related suppressions | **PASS** | Zero `type: ignore` or security `noqa` in core services |
| D4-09 | Safety-bypass options in `hermes-config/config.yaml` | 0 matches for `unsafe`, `bypass_safety`, `disable_safety`, `ignore_security` | **PASS** | No bypass options enabled |

---

## Secret Scan Results (All Grips)

### D4-01: Evidence Files (docs/setup-evidence/P1/)

```
Command: grep -rnE 'sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{35}|gh[opuab]_[a-zA-Z0-9]{36,}|-----BEGIN.*KEY-----' docs/setup-evidence/P1/ --include="*"
Result: 0 matches (exit code 1)
Verdict: PASS
```

No API keys, private keys, or access tokens found in any P1 evidence files. This includes all 36 evidence files across STEP-P1-001 through STEP-P1-021, batch plans, migration evidence, and ADR references.

### D4-02: Source Service Modules (src/core/services/)

```
Command: grep -rnE 'sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{35}|gh[opuab]_[a-zA-Z0-9]{36,}|-----BEGIN.*KEY-----' src/core/services/ --include="*.py"
Result: 0 matches (exit code 1)
Verdict: PASS
```

Zero secrets in `llm_router.py`, `cost_tracker.py`, `llm_metrics.py`, `prompt_loader.py`, `monthly_report.py`, or `hard_stop_handler.py`.

### D4-03: Config File (hermes-config/config.yaml)

**API key patterns:**
```
Command: grep -rnE 'sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{35}|gh[opuab]_[a-zA-Z0-9]{36,}' hermes-config/config.yaml
Result: 0 matches (exit code 1)
Verdict: PASS
```

**key_env verification:**
```
Providers:
  ninerouter:  key_env: NINEROUTER_API_KEY  (line 57) — primary
  fallback 1:  key_env: NINEROUTER_API_KEY  (line 67) — cx/gpt-5.5 via 9Router
  fallback 2:  key_env: NINEROUTER_API_KEY  (line 71) — guinevere combo via 9Router
```

All three provider entries use `key_env:` (environment variable reference), NOT inline `key:` values. No plaintext secrets in config. **PASS.**

### D4-04: Systemd Unit Files (vps-mirror/systemd-live/)

```
Command: grep -rnE 'sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{35}|gh[opuab]_[a-zA-Z0-9]{36,}|-----BEGIN.*KEY-----' vps-mirror/systemd-live/
Result: 0 matches (exit code 1)
Verdict: PASS
```

No secrets in `guinevere-core.service` or `guinevere-9router.service`.

---

## LLMRouter.chat() Caller Security Classification

### Active .chat() Callers (non-deprecated code)

| # | File | Line | Code | Caller Object | WIRED / UNGATED | Risk |
|---|------|------|------|---------------|-----------------|------|
| 1 | `src/loops/conversation.py` | 223 | `await self._llm_router.chat(...)` | Conversation handler | **UNGATED** | Makes LLM calls via LLMRouter directly, not through HermesBrain. P20 autonomy kernel is bypassed. |
| 2 | `src/loops/phases/base.py` | 164 | `await self._llm_router.chat(...)` | Phase base class | **UNGATED** | Base class for all loop phases (research, execute, etc.) — all phases call LLM outside P20 kernel. |
| 3 | `src/loops/reflection.py` | 83 | `await self._llm_router.chat(...)` | Reflection service | **UNGATED** | Reflection LLM calls bypass HermesBrain. |
| 4 | `src/loops/review_fork.py` | 213 | `await self._llm_router.chat(...)` | Fork review | **UNGATED** | Code review fork analysis calls LLM directly. |
| 5 | `src/memory/compaction.py` | 280 | `await self.llm_router.chat(...)` | Memory compaction | **UNGATED** | Creates its own `LLMRouter()` instance (line 80) — standalone, not injected. |
| 6 | `src/self_improve/optimizer.py` | 213 | `await self._llm_router.chat(...)` | Self-improve optimizer | **UNGATED** | Injected via constructor, calls LLM directly. |

### Key Classification Finding

**All 6 active callers are UNGATED** — they call `LLMRouter.chat()` directly without going through the HermesBrain/P20 autonomy kernel. However, this requires nuanced interpretation:

**Defense-in-depth measures still active on all paths:**
- All calls route through 9Router (`localhost:20128`) — no direct provider bypass
- `llm_router.py` `chat()` method has **fail-closed CostTracker** (lines 221-235): if cost tracking fails, it raises `RuntimeError("LLM cost tracking failed")` which is NOT swallowed by fallback
- **LoopGuardian** monitors all loops and checks `HardStopHandler.is_safe` on every tick
- `src/loops/safety_integration.py` provides `LoopSafetyGate` bridging HardStopHandler into the loop system
- `src/loops/circuit_breaker.py` uses `SafetyGate(hard_stop_checker=lambda: handler.is_safe)` (line 9)

**Missing HermesBrain safety layers on these paths:**
- No consent gate (G10) via HermesBrain AIAgent
- No tool-call auth matrix via HermesBrain
- No P20 autonomy kernel iteration budget enforcement
- No P20 safe-mode controller

**Verdict: NEEDS-REVIEW.** The architecture intentionally separates loop infrastructure (P5/P8/P11) from the P20 life kernel. Loops use LLMRouter directly because they aren't autonomous agents — they are deterministic pipeline stages. The CostTracker (fail-closed) + LoopGuardian (HardStop-aware) + CircuitBreaker provide layered safety. However, a motivated bypass would only need to create a plain `LLMRouter()` instance (as `compaction.py` already does on line 80) to make unsupervised LLM calls without HermesBrain oversight.

### Deprecated (No Longer Active)

| File | Line | Status |
|------|------|--------|
| `src/_deprecated/hermes-migration-phase-7/conversational_handler.py` | 83-108 | Deprecated (Phase 7 migrated); not in active code paths |

---

## Provider Endpoint Audit

**File:** `src/core/services/llm_router.py`

All three model configs use the same base URL:

```
TaskType.CORE_REASONING: base_url="http://localhost:20128/v1"  (line 89)
TaskType.SUB_AGENT:      base_url="http://localhost:20128/v1"  (line 100)
TaskType.FALLBACK:       base_url="http://localhost:20128/v1"  (line 108)
```

The actual request is constructed at line 172:
```python
f"{config.base_url}/chat/completions"
```

**Full URL used:** `http://localhost:20128/v1/chat/completions`

**Direct provider URL scan:** Zero results for `api.openai.com`, `api.deepseek.com`, `api.anthropic.com`, `api.google.com`, `api.together.xyz`, `api.cohere.com` across the entire `src/` tree.

**Verdict: PASS.** All LLM traffic routes exclusively through 9Router on localhost:20128. No direct provider endpoints exist.

---

## HardStopHandler Active/Disabled Status

**Evidence file:** `docs/setup-evidence/P1/STEP-P1-021/evidence.md`

**Confirmed active status:**
- "An **app-level HARD STOP handler** was implemented as a pre-LLM safety guard"
- "56/56 handler unit tests PASS (deterministic, no LLM)"
- "14/14 GPT-5.5 model compliance tests PASS"
- "Handler is model-independent — works with any model"
- "App-level guard, not model-dependent"
- "Zero token cost: when HARD STOP triggers, no LLM call is made"

**Live code confirmation:**
- `class HardStopHandler` in `src/core/services/hard_stop_handler.py:34` — class exists and is functional
- `src/core/main.py:63`: `from src.core.services.hard_stop_handler import HardStopHandler`
- `src/core/main.py:101`: `hard_stop_handler = HardStopHandler()` — instantiated
- `src/core/main.py:103-104`: `loop_manager.guardian.set_hard_stop_handler(hard_stop_handler)` — wired to LoopGuardian
- `src/loops/guardian.py:182-200`: Guardian checks `is_hard_stop_active` on every tick and cancels all loops on HARD STOP

**No disabled/mocked patterns found.** Grep for `HARD_STOP.*disabled`, `HARD_STOP.*false`, `hard_stop.*off` returned zero results in the evidence file.

**Verdict: PASS.** HardStopHandler is ACTIVE in both evidence and live code.

---

## Audit-Suppression Comment Scan

**Critical files scanned:** `src/core/services/*.py`, `src/core/main.py`, `src/life_kernel/graph.py`

**Found noqa comments (none are security-related):**

| File | Line | Pattern | Type | Security Impact |
|------|------|---------|------|-----------------|
| `src/core/services/llm_metrics.py` | 85 | `noqa: PLW0603` | Lint (global statement) | None |
| `src/core/services/prompt_loader.py` | 150-172 | `noqa: PLC0415` × 7 | Lint (import order) | None |
| `src/core/main.py` | 424 | `noqa: BLE001` | Broad exception (fail-soft) | None (documented as "fail-soft startup, logged") |
| `src/core/main.py` | 479 | `noqa: BLE001` | Broad exception (fail-soft) | None (documented as "fail-soft shutdown, logged") |
| `src/core/main.py` | 542 | `noqa: BLE001` | Broad exception (fail-soft) | None (documented as "fail-soft shutdown") |
| `src/life_kernel/graph.py` | 182, 257, 266, 611 | `noqa: BLE001` | Broad exception (fail-soft) | None (documented as "brain must never crash the kernel") |

**Patterns with zero results:** `noqa.*SEC`, `noqa.*SAFE`, `noqa.*AUDIT`, `noqa.*S301`, `noqa.*S101`, `# skip.*safety`, `# safety.*skip`, `type: ignore` in core services.

**Verdict: PASS.** Zero security-related audit suppressions found. All noqa comments are lint-related (import ordering, global statements) or documented fail-soft broad-exception patterns which are intentional by design.

---

## Safety-Bypass Option Scan

**File scanned:** `hermes-config/config.yaml`

**Patterns searched (case-insensitive):**
- `unsafe` — 0 matches
- `bypass.*safety` — 0 matches
- `disable.*safety` — 0 matches
- `ignore.*security` — 0 matches
- `insecure` — 0 matches
- `allow.*unsafe` — 0 matches

**Config safety posture:** All safety enforcement is through:
1. Python plugin (`guinevere-safety`) handling all 10 safety gates in-process
2. Shell hooks (defense-in-depth): finance hook, budget check, consent gate, DNR filter, drift check
3. All hooks have `on_failure: block` (fail-closed) except finance (`allow`) and drift check (`warn`)
4. Hooks cover: pre_llm_call, pre_tool_call, post_tool_call, transform_llm_output

**Verdict: PASS.** No safety-bypass options enabled.

---

## P20 Backdoor Risk Assessment

### Scenario: LLMRouter.chat() as an invisible backdoor

**Risk description:** LLMRouter.chat() makes LLM calls through 9Router without going through the P20 HermesBrain autonomy kernel. If an attacker (or buggy code) gains the ability to instantiate LLMRouter and call `.chat()`, they can make unsupervised LLM calls.

**Evidence in code:**
- `src/memory/compaction.py:80`: `self.llm_router = LLMRouter()` — creates its own standalone instance (no injection, no HermesBrain)
- All loop subsystems call `.chat()` directly on injected `_llm_router` instances

**Mitigations in place:**

| Mitigation | Where | Effective? |
|------------|-------|------------|
| 9Router-only routing | `llm_router.py:89,100,108` | Yes — all traffic through localhost proxy |
| CostTracker fail-closed | `llm_router.py:221-235` | Yes — cost tracking failure = hard error, not swallowed |
| LoopGuardian HARD STOP check | `guardian.py:182-200` | Yes — cancels all loops on HARD STOP |
| CircuitBreaker SafetyGate | `circuit_breaker.py:9` | Partial — only blocks tool calls, not LLM calls |
| LoopSafetyGate | `safety_integration.py` | Yes — HardStopHandler bridge into loop system |

**Residual risks:**

| Risk | Severity | Description |
|------|----------|-------------|
| R1: Standalone LLMRouter instantiation | **Medium** | `compaction.py:80` shows that any module can create `LLMRouter()` with default CostTracker, bypassing HermesBrain entirely. No access control on the constructor. |
| R2: No iteration budget outside HermesBrain | **Low** | LLMRouter has no max-iteration or rate-limiting. A runaway loop calling `.chat()` could exhaust budget if CostTracker is compromised. |
| R3: CostTracker Redis dependency | **Low** | If Redis is down, CostTracker fails closed — so this is a denial vector, not a secret bypass. |
| R4: 9Router key shared across providers | **Medium** | Single `NINEROUTER_API_KEY` controls access to all 3 model tiers through 9Router. Compromise of this key (e.g., via log leak or env var exposure) grants access to all models. |

**Verdict: MEDIUM RISK.** The architecture is intentional (loop infrastructure != autonomous kernel), but the absence of instantiation controls on LLMRouter and the single-shared-key pattern present genuine residual risks. These are architectural, not evidence of existing exploitation.

---

## Bug Register

| Severity | File:Line | Finding |
|----------|-----------|---------|
| **Medium** | `src/memory/compaction.py:80` | Standalone `LLMRouter()` instantiation with no injection control — any module can create an LLMRouter bypassing HermesBrain |
| **Medium** | `hermes-config/config.yaml:57,67,71` | Single `NINEROUTER_API_KEY` shared across all 3 provider tiers. Compromise grants access to all models through 9Router |
| **Low** | `src/loops/conversation.py:223` | Conversation LLM calls bypass P20 autonomy kernel (no consent/iteration-budget gates) |
| **Low** | `src/loops/phases/base.py:164` | All loop phase LLM calls bypass P20 autonomy kernel |
| **Low** | `src/core/main.py:424,479,542` | `noqa: BLE001` broad-exception suppression (accepted: fail-soft pattern, but masks all exceptions) |
| **Cosmetic** | `hermes-config/config.yaml:341-374` | Auth matrix section labeled "REFERENCE ONLY" — risk of drift between YAML reference and Python runtime source if not updated together |

---

## Overall D4 Verdict

### D4 Verdict: **NEEDS-REVIEW**

**Rationale:** All secret scans (D4-01 through D4-04) returned zero results. Provider endpoint audit (D4-06) confirms all traffic routes through 9Router localhost only. HardStopHandler is ACTIVE (D4-07). No safety-bypass options exist (D4-09). No security-related audit-suppression comments (D4-08).

The NEEDS-REVIEW verdict is driven by D4-05 (LLMRouter.chat() caller analysis) — the finding that **all 6 active callers are UNGATED** (bypassing HermesBrain/P20) combined with the discovery that LLMRouter can be instantiated without injection control (`compaction.py:80`). While defense-in-depth mitigations exist (fail-closed CostTracker, LoopGuardian with HARD STOP, CircuitBreaker), the architecture creates an intentional but review-worthy gap between loop infrastructure LLM calls and the P20 autonomy kernel.

**Key findings summary:**
1. Zero secrets in evidence, source, config, or unit files — **excellent secret hygiene**
2. All LLM traffic through 9Router localhost only — **no direct provider bypass**
3. HardStopHandler ACTIVE and deeply wired (main.py + LoopGuardian + safety_plugin) — **strong safety integration**
4. 6/6 LLMRouter.chat() callers UNGATED (not through HermesBrain) — **architectural gap needs review**
5. Single shared `NINEROUTER_API_KEY` for all 3 provider tiers — **medium risk if compromised**
6. Zero security-related audit-suppression comments — **good code quality**

---

## Appendix: File Paths Referenced

All paths relative to `C:/Users/faizz/guinevere/`:
- `docs/setup-evidence/legacy-audit/P1/plan/p1-implementation-audit-plan.md`
- `docs/setup-evidence/P1/STEP-P1-021/evidence.md`
- `src/core/services/llm_router.py`
- `src/core/services/cost_tracker.py`
- `src/core/services/hard_stop_handler.py`
- `src/core/main.py`
- `src/loops/conversation.py`
- `src/loops/guardian.py`
- `src/loops/phases/base.py`
- `src/loops/reflection.py`
- `src/loops/review_fork.py`
- `src/loops/circuit_breaker.py`
- `src/loops/safety_integration.py`
- `src/memory/compaction.py`
- `src/self_improve/optimizer.py`
- `hermes-config/config.yaml`
- `vps-mirror/systemd-live/guinevere-core.service`
- `vps-mirror/systemd-live/guinevere-9router.service`
