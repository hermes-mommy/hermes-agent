# P1 Downstream Impact: P19-P24 Roadmap Compatibility Audit

**Audit Date:** 2026-06-25  
**Auditor:** READ-ONLY research agent (P1 legacy audit)  
**Scope:** P1 (LLM + Hermes Agent foundation) surfaces vs P19-P24 roadmap  
**Method:** Source inspection (Grep/Glob/Read/Bash), no runtime or VPS access  

---

## 1. Per-Component Verdict Table

| # | P1 Component | Verdict | Concrete Reason | Blocker-For | Severity |
|---|---|---|---|---|---|
| 1 | **LLMRouter** (`src/core/services/llm_router.py`) | **MUST-ADAPT** | (a) No project_id/namespace on cost keys. All costs tracked globally via CostTracker (Redis DB5). (b) `chat()` is a raw LLM path with no HermesBrain envelope, no AuthLevel gate, no SemanticActionClassifier — explicitly forbidden by P20 plan ("No raw LLMRouter.chat", `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md:38`). (c) Direct routing pre-empts P23 action classification. | P19, P20, P22, P23 | **BLOCKER** |
| 2 | **9Router** (external Node.js, port 20128) | **VALID** (+ P24 note) | External provider proxy is architecturally valid. Secret handling via SOPS/age is adequate (`9router-keys.enc.yaml`). P24 research classes it as "custom provider config" under Hermes (not requiring fork). However, it is an external-service dependency — P24 owned-fork subsumption question unresolved. | P24 | **MEDIUM** |
| 3 | **SystemPromptMaster** (`docs/60-persona/61-SystemPromptMaster_v1.1.md`) + **prompt_loader** (`src/core/services/prompt_loader.py`) | **MUST-ADAPT** | (a) Single global persona — no per-project persona variant injection mechanism. `prompt_loader.py` has no `project_id` parameter. (b) Prompt §F mentions "multi-project: max 3 active projects" at behavior level only — no architectural namespace support. (c) Memory context injection (memories param) has no project_id filter. (d) HARD STOP wording IS correctly global (must stay global per P20). | P19 | **HIGH** |
| 4 | **CostTracker** (`src/core/services/cost_tracker.py`) | **MUST-ADAPT** | All cost keys are global: `cost:current_month`, `cost:daily:{today}`, `cost:by_model:{model}` — zero project_id dimension. P19 per-project cost isolation impossible without key restructuring. Monthly cap is global $30. | P19 | **HIGH** |
| 5 | **guinevere-core.service** + **health-check-p1.sh** | **SUPERSEDED** | P20 Living Autonomy Kernel / HermesBrain is the canonical health surface now. `guinevere-core.service` (uvicorn on :8000) is P1-era and largely superseded by Hermes gateway. `health-check-p1.sh` covers P1-era services only — `hermes doctor` replaces it. | P20, P24 | **LOW** |
| 6 | **Hermes Agent** (hermes-agent v0.15.2, `hermes-config/`) | **MUST-ADAPT** *(for P24)* | For P19-P23 roadmaps (keeping hermes-agent as PyPI external dep): **VALID** — hooks/plugins infrastructure is already Guinevere-owned code in `hermes-config/`. For P24 owned-fork convergence: **MUST-ADAPT** — the external PyPI dependency must be internalized into the Guinevere codebase. | P24 | **HIGH** *(P24 only)* |

---

## 2. Top 3 Downstream Blocker Risks

### BLOCKER-1: LLMRouter.chat() as Ungated Raw LLM Path
**Source:** `src/core/services/llm_router.py:133-249` — `LLMRouter.chat()` method  
**Phase Impact:** P20 (autonomy kernel), P22 (raw access), P23 (action classification)

`LLMRouter.chat()` accepts arbitrary messages, routes to any TaskType model via 9Router, and returns the LLM response. It has:
- No AuthLevel gating
- No HermesBrain envelope
- No SemanticActionClassifier
- No project_id namespace isolation

The P20 plan (`docs/setup-evidence/P20/plan/p5-p20-vision-lock.md:38`) explicitly says: *"No raw LLMRouter.chat: All autonomous reasoning uses HermesBrain.think() with model='guinevere' provider='9router'."* Any residual caller of `LLMRouter.chat()` in the codebase creates an invisible backdoor around the entire P20/P22/P23 safety stack.

**Remediation:** Replace all callers of `LLMRouter.chat()` with `HermesBrain.think()`. Add a deprecation gate that raises RuntimeError if `chat()` is called outside approved migration paths. Add project_id parameter.

### BLOCKER-2: CostTracker Global Namespace Blocks P19 Per-Project Isolation
**Source:** `src/core/services/cost_tracker.py:35-48` — 11 global key writes per `record_cost()` call  
**Phase Impact:** P19 (multi-project context)

Every key written by `CostTracker.record_cost()` uses a global namespace:
```
cost:current_month
cost:current_day
cost:daily:{today}
cost:monthly:{month}
cost:by_model:{model}
token:daily:{today}:input
token:daily:{today}:output
token:current_day:input
token:current_day:output
token:current_month:input
token:current_month:output
token:by_model:{model}:input
token:by_model:{model}:output
```

P19 requires per-project cost tracking. Adding `project_id` to all 13 keys is a compatible change (existing keys remain for the default/global project), but it touches CostTracker, LLMRouter (which instantiates CostTracker at `llm_router.py:131`), and every service reading cost data.

**Remediation:** Add `project_id: str = "default"` parameter to `CostTracker.__init__()` and `record_cost()`. Prepend `project:{project_id}:` to all key patterns when project_id is not "default". The LLMRouter must accept and forward project_id.

### BLOCKER-3: 9Router External Dependency for P24 Owned-Fork Convergence
**Source:** `src/core/services/llm_router.py:89-113` — hardcoded `base_url="http://localhost:20128/v1"`; external Node.js process  
**Phase Impact:** P24 (owned-fork convergence)

9Router is a separate Node.js service not owned by the Guinevere codebase. Its:
- API endpoints are defined externally
- Provider routing logic is in Node.js (not Python)
- Configuration is via `9router-keys.enc.yaml` (SOPS)
- Health is checked independently (health-check-p1.sh:17, `:20128/api/health`)

In a P24 full-owned-fork scenario, this external dependency creates a foreign-code boundary. The P24 convergence research (`docs/setup-evidence/P24/research/p24-p1-p18-hermes-convergence-map.md:48`) classes this as "custom provider config" and says 0% needs fork — but this is the no-fork analysis. For the preferred OWNED FORK path, the 9Router routing logic must either be:
1. Internalized as Python-native LLM routing within the fork
2. Kept as a managed subprocess/bundled submodule
3. Replaced by direct provider calls (undoing the "no direct provider endpoints" rule at `llm_router.py:4-5`)

**Remediation:** During P24 fork work, internalize 9Router's provider routing and model selection into `src/core/routing/` as Python code. The LLMRouter becomes a thin Python-native router with provider fallback logic directly in the Guinevere-owned codebase.

---

## 3. Semantic Gate Analysis (P22/P23 Cross-Cut)

### P22: Full-Capability Raw Access / Life Integration Hub
P22 FORBIDS AuthLevel-only gating for L2/L3/L4 write/delete/admin operations. It requires SEMANTIC classification. The P1 LLMRouter has neither AuthLevel gating nor semantic classification — it is a flat routing layer. This means:

- **Current state:** LLMRouter provides zero P22-compatible gating
- **Blocker:** Any code path that calls `LLMRouter.chat()` and then uses the response to perform a L2+ action bypasses P22's semantic classification
- **Affected file:** `src/core/services/llm_router.py` line 133 (chat method) — the entire method is in the blast radius
- **Mitigation exists?** The P20 plan (`vision-lock.md:38`) already forbids raw LLMRouter.chat for autonomous actions, but this is a documentation prohibition, not a runtime gate. No runtime guard exists.

### P23: Embodied Operations / Action Layer
P23 requires `SemanticActionClassifier` (defined in `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:342-345`) to classify actions before they reach the 7-step policy gate. P1 LLMRouter:

- Has no action classification
- Routes directly to models without policy inspection
- Would pre-empt P23 classification if called for autonomous action generation
- P23 plan §22b specifies AuthLevel is an INPUT to SemanticActionClassifier, not a 1:1 map — LLMRouter has neither concept

**Verdict:** P1 LLMRouter must not be used as the LLM invocation path for P23-generated actions. All P23 action execution must route through P20 HermesBrain → P23 SemanticActionClassifier → policy gate → executor, never through raw `LLMRouter.chat()`.

---

## 4. P24 Fork-Convergence Verdict for P1 as a Whole

**Verdict: PARTIALLY SUPERSEDED under owned-fork scenario**

P1's role in the architecture shifts under P24 owned-fork convergence:

| Aspect | Current (P1) | P24 Owned-Fork Target | Delta |
|---|---|---|---|
| Agent runtime | `hermes-agent` v0.15.2 (PyPI external) | Internalized into Guinevere codebase (forked) | Must adapt |
| LLM routing | 9Router (external Node.js, port 20128) | Python-native LLM routing or bundled subprocess | Must adapt |
| Cost tracking | CostTracker (Guinevere code) | CostTracker (Guinevere code) — add project_id | Enhancement |
| System prompt | `prompt_loader.py` (Guinevere code) | Same — add project_id | Enhancement |
| Health surface | `guinevere-core.service` (superseded) | P20 HermesBrain health surface | Already superseded |
| Hooks/plugins | `hermes-config/` (Guinevere code) | Truly native (merged into fork root) | Adapt (merge path) |
| Auth gating | `src/mcp/auth.py` + `auth_matrix.py` | Same — survives fork unchanged | VALID |

**Key finding from P24 research:** The P24 convergence map (`p24-p1-p18-hermes-convergence-map.md:42`) classes P1 as "ALREADY HERMES-NATIVE" under the **no-fork scenario**. Under the **owned-fork scenario**, P1 is "ALREADY GUINEVERE-OWNED" for CostTracker, prompt_loader, and auth code, but "EXTERNAL-DEPENDENT" for hermes-agent and 9Router. The fork work is primarily: (a) internalizing hermes-agent's relevant code, and (b) either internalizing or cleanly bundling 9Router.

**Critical observation:** The P24 no-fork analysis (82% already native/hybrid, 18% standalone, 0% needs fork) and the P24 owned-fork preference (`docs/setup-evidence/P24/research/p24-p1-p18-capability-inventory.md:24`) are in tension. The available evidence on disk pre-dates the final fork decision. The P1 audit findings here provide the per-component delta to inform that decision.

---

## 5. Evidence Sourcing Index

| Claim | File(s) | Lines |
|---|---|---|
| LLMRouter global cost keys | `src/core/services/llm_router.py` | 216-235 |
| CostTracker no project_id | `src/core/services/cost_tracker.py` | 25-48 (all keys) |
| LLMRouter raw path (no auth, no semantic) | `src/core/services/llm_router.py` | 133-249 |
| P20 forbids raw LLMRouter.chat | `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md` | 38 |
| P23 SemanticActionClassifier definition | `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` | 342-345, 791 |
| P23 AuthLevel is INPUT not 1:1 | `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` | 791, 822, 1126 |
| SystemPromptMaster §F multi-project (behavior only) | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | 252 |
| prompt_loader no project_id | `src/core/services/prompt_loader.py` | 41-46, 208-294 |
| 9Router base_url hardcoded | `src/core/services/llm_router.py` | 89, 99, 108 |
| 9Router no-direct-provider rule | `src/core/services/llm_router.py` | 4-5 |
| health-check-p1.sh P1-era | `scripts/health-check-p1.sh` | 1-59 (entire file) |
| guinevere-core.service depends on 9Router | `vps-mirror/systemd-live/guinevere-core.service` | 3-4 |
| P24 convergence: P1 "ALREADY HERMES-NATIVE" | `docs/setup-evidence/P24/research/p24-p1-p18-hermes-convergence-map.md` | 42-58 |
| P24 forward-compat: no-fork compatible | `docs/setup-evidence/P24/research/p24-p19-p21-p22-p23-forward-compatibility-map.md` | 13-14 |
| P24 capability inventory: P1 pattern | `docs/setup-evidence/P24/research/p24-p1-p18-capability-inventory.md` | 17-31 |
| StateManager Redis DB5 (global state) | `hermes-config/plugins/guinevere_safety/state_manager.py` | 31, 78-86, 103-111 |
| hermes-agent config (9Router provider) | `hermes-config/config.yaml` | 48-71 |
| P24 preferred = FULL OWNED FORK | `MEMORY.md` (p24-hermes-fork-convergence) | full |

---

## 6. Per-Phase Impact Summary

| Phase | P1 Blockers | Severity | Action Required |
|---|---|---|---|
| **P19** (Multi-Project Context) | CostTracker global keys, prompt_loader no project_id, LLMRouter no namespace | **BLOCKER** | Add project_id to CostTracker + LLMRouter + prompt_loader |
| **P20** (Living Autonomy Kernel) | LLMRouter.chat() as ungated raw path; HARD STOP global (correct, preserve) | **HIGH** | Gate all autonomous LLM calls through HermesBrain.think(); keep HARD STOP global |
| **P22** (Full-Capability Raw Access) | LLMRouter has no AuthLevel or semantic classification; raw path bypasses P22 | **BLOCKER** | LLMRouter must not be used for L2+ autonomous actions without P23 SemanticActionClassifier |
| **P23** (Embodied Operations) | LLMRouter pre-empts P23 classification; no policy gate | **HIGH** | All P23 action LLM calls must route through P20 → P23, not through LLMRouter.chat() |
| **P24** (Hermes Fork Convergence) | 9Router external dep; hermes-agent PyPI dep; both must be internalized | **HIGH** | Internalize 9Router routing + hermes-agent runtime into owned codebase |

---

*End of research document. READ-ONLY audit — no files modified.*
