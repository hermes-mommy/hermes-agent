# P24 → P28 Dependency Research: Hermes Fork-First Full Convergence as P28 Prerequisite

**Research Date:** 2026-06-28
**Author:** Buffy (codebase search specialist, sub-agent for Guinevere)
**Purpose:** Inform P28-P36 masterplan + prompt-pack prerequisite gates for P24 (Hermes Fork-First Full Convergence).
**Status:** READY — feeds dependency-gate spec into masterplan author + prompt-pack writer.
**Scope:** All P24 artifacts in `docs/setup-evidence/P24/` + P27 references to P24 + ADR-054 + PROGRESS.md/CHECKLIST.md.

---

## 0. Headline — User Premise Corrected

**Original user premise:** "P24 (full-owned Hermes fork) is a hard dependency before P28 implementation."

**Repository truth (multiple authoritative sources, all aligned):**

> **P24 is NOT a hard dependency for P28. P28 implementation may proceed without P24 fork.**
> P24 is documented as a **preferred optimization**, deferred to **P32** (P24 Fork Integration phase).
> P28 proceeds on a **fork-agnostic, config-driven multi-instance** interim path.

| Source | Verbatim |
|---|---|
| `PROGRESS.md` (2026-06-28) | "P24 fork NOT required for P28; P23 executors NOT required for P28 minimum target" |
| `adr/ADR-054-p27-hermes-society-foundation.md` §Positive | "P28 may proceed without P24 fork. P24 fork is documented as a preferred optimization (P32) but NOT a prerequisite for P28 minimum target." |
| `adr/ADR-054-p27-hermes-society-foundation.md` Plan §14.10 | "P24 fork is a preferred optimization, not a prerequisite" |
| `P27/plan/p27-hermes-society-foundation-plan.md` §14.8 L3294 | "P28 minimum target does NOT require P24 fork" |
| `P27/plan/p27-hermes-society-foundation-plan.md` §14.3 L3206 | "P27 is fork-agnostic" (~70% definitional, ~30% implementational) |
| `P27/plan/p28-dual-autonomous-hermes-blueprint.md` §1.2 L65 / §2.1 L97 | "fork = preferred optimization, not prerequisite" / "[P24 Hermes Fork] NOT NEEDED — P28 uses hybrid adapter + per-instance config" |
| `P27/plan/p27-p28-p36-master-roadmap.md` §7 L480-545 | "P32 implements native multi-Hermes via P24 fork. Until P32, P28+P29+P30+P31 implement per-instance via HermesBrainConfig + shadow/independent bot pattern" |
| `P27/evidence/audits/round-1/07-p24-dependency.md` (PASS) | "P28 blueprint is fork-free"; "P32 handoff point is explicit, with graceful degradation if fork is delayed" |
| `P27/evidence/audits/round-1/14-hard-rejection-criteria.md` (Crit 20 PASS) | "FAIL if Society onboarding depends on P24 fork or P23 executors" |
| `P27/evidence/audits/round-1/08-p22-p23-dep.md` | P28 §2.1: P23, P24, P21 all explicitly `NOT NEEDED` |
| `CHECKLIST.md` L56 | "P24 PLAN FIXED — FULL OWNED FORK PREFERRED — IMPL HOLD UNTIL MAMA AUDIT" (impl hold does NOT block P28) |

**Implication for masterplan writer:** The P28 prompt-pack prerequisite gates should NOT block on P24 status. Either remove the P24 gate entirely OR reframe it as informational (P24 is a future optimization, status tracked but not gating). The `lanjut N` autopilot must not halt P28 planning on P24 impl-hold. The correct production-pass gate for P28 is the **24h dual-bot peer-to-peer soak**, not P24-020 soak.

---

## 1. P24 — Mission, Status, and Verdict

### 1.1 Mission (verbatim, plan §1)

> "Determine and design how to make Guinevere truly Hermes-native through an owned Hermes fork OR hybrid fork+plugin. All legacy capabilities (P1-P18) and new capabilities (P20/P21/P22/P23) must have an integration path into Hermes built-in/runtime — not just side modules."

### 1.2 Recommended Verdict (operator source of truth, 2026-06-25)

**`FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION READY`** (hybrid = transition path only; final target = full owned fork for ownership/convergence mission).

### 1.3 Phase Status (DEFINITION / PLANNING ONLY — no runtime implementation)

| Metric | Value | Source |
|---|---|---|
| Phase | P24 — Hermes Fork-First Full Convergence | `P24/README.md` |
| Category | **DEFINITION / PLANNING ONLY** — NO runtime code, deploy, restart, secrets edit, `.venv/site-packages` edit, P20 soak disruption | `P24/README.md` §Implementation Hold |
| P24 files | 41 (exact `wc -l` count) | `P24/evidence/final-p24-planning-report.md` |
| P24 lines | 13,426 (exact `wc -l`) | same |
| Research files | 14 (all COMPLETE) | `P24/research/` |
| Audit round 1 | 13 auditors (7 PASS, 6 CONDITIONAL) | `P24/evidence/auditor-gate.md` |
| Audit round 2 | 3 re-audits (all PASS — F-001 verdict contradiction + F-002 unverified trigger fixed via §15.1) | same |
| Plan sections | 44 (plan §1-§44) | `P24/plan/p24-hermes-fork-first-full-convergence-plan.md` |
| Implementation waves | **20 (P24-001 → P24-020, ALL HELD)** | plan §43 |
| Codex parent audit | 5 implementability blockers — ALL FIXED (plan + tracker docs only) | `P24/evidence/p24-plan-fix-verification.md` |
| Mama round-3 audit | 3 additional blockers — ALL FIXED | `P24/evidence/plan-fix-audits/plan-fix-audit-mama-round3.md` |
| Critical findings fixed | F-001 verdict contradiction + F-002 unverified trigger + docs-consistency | plan §15.1 |
| Implementation gate status | **HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL** | `P24/README.md` |
| Secret scan | CLEAN (zero secrets; exact grep `sk-/ghp_/AKIA/xox-/BEGIN.*PRIVATE KEY`) | `P24/evidence/cleanup-verification-audit.md` |
| Runtime code / deploy / secrets edit | **NONE** | verified by `find docs/setup-evidence/P24 -name "*.py" \| wc -l` → 0 |
| Fork repo created | **NO** (no fork on `github.com/fazulfim/hermes-agent`) | plan §28 + §43 P24-003 |
| Upstream source cloned | **NO** (P24-002 first-patch scope is part of hold) | plan §43 P24-002 |

**Final allowed status (verbatim):** `P24 PLAN FIXED — FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL`.

---

## 2. Hermes Native Runtime — What Already Exists (No Fork Required)

### 2.1 Upstream Identity (Pinned Today, No Fork)

| Aspect | Value | Source |
|---|---|---|
| Package | `hermes-agent` (PyPI, hyphenated) | `P24/research/p24-hermes-upstream-identity-research.md` |
| Version INSTALLED | `0.15.2` (also `>=0.15` in `pyproject.toml` line 31) | same |
| Author | Nous Research | same |
| License | **MIT** (Copyright (c) 2025 Nous Research) | same |
| Forkability | **FORKABLE** (MIT permits modifications; no copyleft) | same |
| Upstream repo | `https://github.com/NousResearch/hermes-agent` | same |

### 2.2 Installed Runtime Surface (Today — No Fork Change Needed)

From `P24/research/p24-installed-runtime-surface-inventory.md` and verified against `src/`:

| Surface | Count | Location |
|---|---|---|
| Direct imports of `run_agent` | 1 | `src/life_kernel/hermes_brain.py` |
| Local adapters | 7 | `src/hermes/`: `adapter.py`, `_session_adapter.py`, `_memory_bridge.py`, `safety_plugin.py`, `plugins/persona_plugin.py`, `plugins/__init__.py`, `__init__.py` |
| In-process plugins (Hermes config) | 3 | `hermes-config/plugins/`: `auth_overlay`, `guinevere_persona`, `guinevere_safety` |
| Command plugins | 44 | `src/hermes_plugins/`: `commands_high`, `commands_loop`, `commands_memory`, `commands_surveillance`, `commands_system`, `commands_finance`, `commands_admin` |
| Shell hooks | 12 | `hermes-config/hooks/`: `hard_stop`, `consent_gate`, `dnr_filter`, `safety_scan`, `budget_check`, `drift_check`, `error_classifier`, `finance_hook`, `hybrid_guards`, `budget_lua`, `budget_lua_extended`, `_hook_utils` |
| Config | 1 | `hermes-config/config.yaml` (394 lines: discord, model, memory, hooks, mcp_servers, cron, observability, approval, agent) |
| SOUL file | 1 | `hermes-config/SOUL.md` |
| MCP servers (Hermes config) | 2 | `fastmcp_full` (enabled), `fastmcp_custom` (disabled) |
| Cron jobs | 8 | 5 persona rituals + 3 maintenance |
| Plugin manifests | 3 | `plugin.yaml` ×2, `manifest.yaml` ×1 |

**Note for P28:** This runtime surface is the substrate that P28 builds on. ADR-035 already implements a hybrid adapter pattern (status: "Implemented"); P28 extends it with per-instance config + per-instance `HermesBrainConfig` — without forking Hermes.

### 2.3 Extension Points that P28 Can Use Today (No Fork)

From `P24/research/p24-extension-points-hooks-plugins-research.md`: **~40 official extension points** in Hermes v0.15.2 are sufficient for P28's interim multi-instance path.

| Category | Count | Examples (P28-relevant) |
|---|---|---|
| Config sections | 9+ | `discord:`, `model:`, `memory:`, `hooks:`, `mcp_servers:`, `cron:`, `observability:`, `approval:`, `agent:` |
| Lifecycle hook events | 17 (Hermes v0.15.2) | `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_start`, `on_session_end`, `pre_gateway_dispatch`, `pre_api_request`, `post_api_request`, `pre_approval_request`, `post_approval_response`, `on_session_finalize`, `on_session_reset`, `subagent_stop`, `transform_terminal_output`, `transform_tool_result` |
| Shell hook scripts | 9 | finance, budget, consent, dnr, drift, hard_stop, hybrid_guards, error_classifier (+ `_hook_utils`) |
| In-process plugins | 3+ (extensible) | `auth_overlay`, `guinevere_persona`, `guinevere_safety` + P28's `society_router`, `society_audit`, `society_consent`, `pharsa_persona` etc. |
| MCP servers | 2+ (extensible via env) | `fastmcp_full` + per-society MCP via env vars |
| Cron jobs | 8+ | per-society ritual cron entries |
| Plugin manifests | 2+ shapes | standard P28 instance manifest |

**Key P27 §16.9 L3554-3568 finding (PASSED in Audit 04):**
> "Hermes v0.15.2 + Guinevere's adapter layer exposes approximately 40 extension points usable for P28 multi-instance implementation WITHOUT P24 fork. This is the **central reason** P28 can be defined now without P24 fork. The infrastructure already supports multi-instance."

**P28 limitations that DO require fork (deferred to P32/P33):**
- Cannot add 18th hook without forking (cannot extend AIAgent constructor signature upstream)
- Cannot have per-Society `PersistentTaskRegistry(task_factory, society_id=...)` namespace inline
- Cannot enforce §0.1 V-008 HARD STOP via fork lifecycle registry (only via app-level handler today)

---

## 3. What P24 Will Provide WHEN Implemented (Future Capabilities)

The 20 waves P24-001 → P24-020 are HELD. The deliverables below are the **target architecture**, not the current state. The "production-pass" criteria map onto these.

### 3.1 Fork Ownership Deliverables (P24-005 → P24-005-PASS)

| Deliverable | P24 wave | P28 relevance today | After P24-PROD-PASS |
|---|---|---|---|
| Private fork repo `github.com/fazulfim/hermes-agent` (MIT + NOTICE preserved) | P24-005 | Not needed (P28 uses upstream `>=0.15`) | Provides canonical, owned runtime for any future Society installation |
| `main` ↔ upstream `main` branch policy; `guinevere` branch with fork additions | P24-005 / P24-013 | Not needed | Rebase discipline + Guinevere-specific code lives only here |
| Tags `v0.15.2-guinevere.N` + rollback tag `v0.15.2-upstream` | P24-005, P24-018, P24-019, P24-020 | Not needed | Per-society pinning + emergency fallback |
| `pyproject.toml` `git+https@tag` pin | P24-005, P24-019 | Today: `hermes-agent>=0.15` | Reproducible installs per Society |

### 3.2 The First Internal Fork Patch — `hermes_lifecycle/persistent_tasks.py` (P24-006 — FORK CORE)

`<200 LOC` adds:
```python
# In forked hermes-agent: hermes_lifecycle/persistent_tasks.py (NEW)
class PersistentTaskRegistry:
    """Register background asyncio tasks that survive session end (§0.1 V-003/V-008)."""
    def on_startup(self, name: str, task_factory: Callable[[], asyncio.Task])
    def on_shutdown(self, name: str, canceller: Callable)
    def trigger_hard_stop(self)  # global HARD STOP cascades
```

**Current state (no fork):** P20 1s heartbeat runs under APScheduler in systemd (`src/life_kernel/heartbeat.py`); survives session end via systemd cgroup, not Hermes lifecycle. P28 can reuse this pattern per Society instance — does NOT need the fork lifecycle hook to start.

**Critical note:** Plan §17 + Audit 07 F10 confirm P28's **minimum target** (dual Guinevere+Pharsa 24/7 peer instances) is achievable with the existing APScheduler pattern. The lifecycle patch is a **convergence improvement** (one-shot V-008 enforcement), not a P28 blocker.

### 3.3 Other Internal Convergence Patches P24 Plans

| Fork target | P24 wave | Fork addition? | Status today |
|---|---|---|---|
| Memory/KG native provider | P24-007 | NO — plugin/hook only | Extension sufficient (`src/hermes/_memory_bridge.py` works) |
| Persona/safety/HARD STOP hook | P24-008 | NO — plugin/hooks only | Extension sufficient (`guinevere_safety` plugin already wires HARD STOP) |
| MCP/tool/action runtime | P24-009 | NO — config/hooks only | Extension sufficient (Hermes `fastmcp_full` loads 16 MCP tools natively) |
| Discord/comms convergence | P24-010 | NO — gateway | Extension sufficient (Hermes Gateway Discord handles turn-core; P20 dashboard via REST publisher today, migrate to Gateway in P24) |
| P1-P8 / P9-P14 / P16-P18 verification against fork | P24-011/012/013 | NO | Existing tests pass against upstream `>=0.15` |
| P20 life-kernel migration to fork lifecycle | P24-014 | YES (uses fork `on_startup`) | Today APScheduler; post-fork uses `on_startup` |

**Bottom line:** Only **2 fork additions** are planned: (1) `PersistentTaskRegistry` (~200 LOC) for §0.1 V-008 enforcement; (2) P20 migration that uses it. Everything else is configuration / hooks / plugins (no fork code change).

---

## 4. P24 Implementation Waves — What's Not Done Yet

| Wave | Title | Status | Why blocked |
|---|---|---|---|
| P24-001 | Governance/ADR record (proposed `ADR-051`) | HELD | Awaiting mama audit |
| P24-002 | Upstream source acquisition + P20 heartbeat source inspection (MANDATORY before P24-006) | HELD | MANDATORY gate: provides exact patch-point evidence + binary verdict |
| P24-003 | Fork repo creation + branch/tag policy | HELD | P24-005 dependency |
| P24-004 | Local install via `pyproject.toml` git+https pin | HELD | P24-005 dep; pyproject.toml remains `hermes-agent>=0.15` |
| P24-005 | Upstream parity baseline tests | HELD | P24-003 dep |
| P24-006 | Lifecycle/event bus core patch **(<200 LOC, FORK CORE)** | HELD | **BLOCKED UNTIL P24-002 PASS** |
| P24-007 | Memory/KG provider (NO FORK) | HELD — but NO FORK | Parallel OK after P24-006 |
| P24-008 | Persona/safety/HARD STOP hook (NO FORK) | HELD — but NO FORK | Parallel OK after P24-006 |
| P24-009 | MCP/tool/action patch (NO FORK) | HELD — but NO FORK | Parallel OK after P24-006 |
| P24-010 | Discord/comms convergence (NO FORK) | HELD — but NO FORK | Parallel OK after P24-006 |
| P24-011/012/013 | P1-P8 / P9-P14 / P16-P18 migration | HELD | After P24-006 |
| P24-014 | P20 life-kernel migration into fork runtime | HELD | Uses fork `on_startup` |
| P24-015 | P19/P21/P22/P23 compat (CONTRACT-GATED, internal-to-fork) | HELD | Per plan §18.1 contract-gating |
| P24-016 | Observability/audit/evidence migration | HELD | Parallel OK after P24-006 |
| P24-017 | Local full test + parity gate | HELD | After P24-006 |
| P24-018 | **VPS canary deploy (ISOLATED `.venv-hermes-canary` + canary-only unit)** | HELD | After P24-017; isolated canary (codex audit hardened) |
| P24-019 | Production rollout + rollback drill (<5min) | HELD | P24-018 PASS required; promotion to shared `.venv` only after canary + drill + service-impact proof |
| P24-020 | **24h soak + final PRODUCTION PASS gate** | HELD | After P24-019 |
| **P24-020 (production-pass criteria)** | **24h clean soak of fork install on VPS** | HELD | After all upstream waves |

---

## 5. "Production Pass" — Exact Criteria for P24

Per `P24/plan/p24-hermes-fork-first-full-convergence-plan.md` §37 (Soak Strategy) and §43 P24-020:

### 5.1 Soak Definition

- **Duration:** **24 hours** minimum (`P24-020`).
- **Stack under test:** The full Guinevere service stack running on the **forked** Hermes (`v0.15.2-guinevere.N`) on shared `.venv` (post canary promotion).
- **Starting trigger:** P24-019 production rollout complete + rollback drill PASS.

### 5.2 Production-Pass Criteria (Binary-Checkable)

A `P24 PRODUCTION PASS` verdict requires **all** of the following:

#### 5.2.1 P20 Heartbeat Persistence
- [ ] **Heartbeat persists across session end** for 24h uninterrupted.
- [ ] **Heartbeat latency <1s** (target 1s tick, max drift 100ms).
- [ ] `on_startup(task_factory)` registration verified to spawn persistent background asyncio tasks.
- [ ] `on_shutdown(task_canceller)` cancels tasks cleanly.

#### 5.2.2 §0.1 Autonomy Invariants Preserved (Hard Rejection if violated)
- [ ] **V-003 "Silence is not blocker":** P20 heartbeat continues unresponsive/inactive state without operator ack.
- [ ] **V-007 "Audit not approval bottleneck":** Policy-gated autonomy executes; per-action approval is NOT introduced for routine steps.
- [ ] **V-008 "HARD STOP global halt":** `life_kernel:hard_stop_requested` (Redis) halts ALL persistent tasks within **<50ms** trigger latency. Both BEFORE and AFTER P24 fork, this invariant must hold.

#### 5.2.3 HARD STOP Cascade
- [ ] **Cross-instance HARD STOP** (when P32 multi-society lands): HARD STOP halts all Society members simultaneously within <50ms.
- [ ] Boundary proof: HARD STOP bypass impossible (test that no fork code path can suppress HARD STOP).

#### 5.2.4 Parity Test Gate
- [ ] **Hermes upstream test suite** passes 100% against fork (`pytest hermes-agent/tests/ -v` exit 0).
- [ ] **Guinevere test suite (~395+ tests including P3/P4/P5/P6/P7/P8/P22 regression)** passes 100% (`pytest tests/ -v` exit 0).
- [ ] **Fork-specific test suite** (`hermes-agent/tests/test_persistent_tasks.py`) passes 100% — covers startup, shutdown, HARD STOP, persistence across session.

#### 5.2.5 No Regressions
- [ ] P1-P18 (Discord, memory, persona, agent loop, MCP, surveillance, observability) 100% pass.
- [ ] P22 Life Integration Hub runtime (after P22.1 hardening) unchanged.
- [ ] P20 visible autonomy unchanged.
- [ ] No `.venv/site-packages` edits discoverable.

#### 5.2.6 Operational Continuity
- [ ] **Discord Gateway stable** (P2 bot + Hermes Gateway messages exchanged without isolate).
- [ ] **9Router LLM routing stable** (no `cx/gpt-5.5` forced fallbacks; budget hook fail-closed).
- [ ] **Cost tracking accurate** (Redis DB5 keys match LLM call counts).
- [ ] **No public exposure** (`ss -tlnp` unchanged from pre-fork baseline).
- [ ] Aizanta isolation intact (no port conflicts, no DB leaks).

#### 5.2.7 Boundary Compliance
- [ ] No persona drift (Y6 impossible preserved; Y4 baseline + Y5 ceiling enforced).
- [ ] No consent violation (consent revocation absolute).
- [ ] No surveillance overreach.
- [ ] No secret/intimate data exposure (secret scan CLEAN).
- [ ] No HARD STOP bypass.
- [ ] No consent-suppression.

#### 5.2.8 Rollback Drill
- [ ] **Rollback-to-upstream <5min** verified (stop services → revert `pyproject.toml` to `hermes-agent>=0.15` → `uv pip install --force-reinstall "hermes-agent==0.15.2"` → restore APScheduler/systemd heartbeat → restart services → verify upstream).
- [ ] **Rollback from `.venv-hermes-canary` is a no-op** (delete canary env, no shared env touched).
- [ ] **Post-rollback 24h soak re-verified** after a planned rollback drill (Week 1 of production).

### 5.3 Verification Commands (P24-020 Hard Gate)

```bash
# Version verification
python -c "import importlib.metadata as md; print(md.version('hermes-agent'))"  # expect "0.15.2+guinevere.N"
# FORBIDDEN: python -c "import hermes_agent; print(hermes_agent.__version__)"

# P20 heartbeat test
pytest tests/life_kernel/ -v  # expect 100% pass; covers heartbeat persistence
grep "$heartbeat" systemd/guinevere-scheduler.service  # confirm still active

# HARD STOP latency
python -c "from src.persona.hard_stop import HardStopHandler; h=HardStopHandler()..."  # <50ms assertion

# Parity
pytest hermes-agent/tests/ -v  # upstream tests against fork
pytest tests/ -v  # Guinevere 395+ tests

# Rollback drill
sudo systemctl stop guinevere-*
# revert pyproject.toml
uv pip install --force-reinstall "hermes-agent==0.15.2"
# restore APScheduler/systemd heartbeat (currently via systemd cgroup + APScheduler)
sudo systemctl start guinevere-*

# Cost + Discord
redis-cli -n 5 KEYS 'cost:*' | wc -l  # expected >= pre-fork count
curl http://localhost:20128/v1/models  # 9Router
```

### 5.4 Implementation Hold Reason (verbatim, plan + READMEs)

**Three explicit hold blockers (NOT defects; by design):**

1. **P20 axis** satisfied by operator accepted-risk waiver — before touching P20/LOCKED runtime files, run **fresh runtime incident preflight** (post the P20 EARLY ACCEPTANCE state — PROGRESS.md 2026-06-25).
2. **P19 definition exists** — P24 implementation depends on **current P19 namespace contract readiness** (project_id propagation proven live, P19 PRODUCTION COMPLETE 2026-06-27 per PROGRESS.md).
3. **P24-002 scopes the first internal patch** (P20 heartbeat `on_startup` check) — does **NOT** gate the fork/no-fork decision (fork chosen on ownership grounds per operator source of truth 2026-06-25).

**All three hold blockers are now clear or near-clear:**
- P20 axis: P20 is in EARLY ACCEPTANCE; preflight will run when implementation begins.
- P19 namespace: P19 PRODUCTION COMPLETE 2026-06-27 → ready.
- P24-002: first action once mama approves.

---

## 6. P24 vs P28 Dependency Matrix — Definitive

| P28 requirement | P24 dependency? | Source authority |
|---|---|---|
| P28 needs `hermes-agent` runtime | NO — uses upstream `>=0.15` (installed today v0.15.2) | `pyproject.toml` L31 |
| P28 needs multi-instance setup | NO — uses **per-instance `hermes-config/` directory** + per-instance `HermesBrainConfig` (config-driven) | P27 plan §4.8 + §16; Audit 07 F4 |
| P28 needs Discord dual-bot | NO — uses Hermes Gateway Discord adapter + 2 bot tokens/cores (today's pattern, ADR-035) | ADR-035 + P27 §9 |
| P28 needs HPP envelope | NO — pure Guinevere-side Python code (no Hermes API needed) | P28 blueprint §5 |
| P28 needs 3-scope memory | NO — pure PostgreSQL (memory.kg_*, memory.shared_world, memory.private_agents tables) | P28 blueprint §6 |
| P28 needs HARD STOP cascade | PARTIAL — Redis key global already works; fork lifecycle registry adds ONLY §0.1 V-008 enforcement | P28 §3.2 + P24 §20 |
| P28 needs 24/7 peer peer-to-peer | NO — uses **APScheduler pattern from P20 today** (`src/life_kernel/heartbeat.py` survives via systemd cgroup) | P27 §14.3 L3206 |
| P28 needs anti-sycophancy, audit/governance | NO — already in AGENTS.md + PersonaSafetyPolicy + P27 §8 | P27 §8 + §10 |
| P28 needs Y4/Y5/Y6 invariant | NO — already enforced by ADR-001 + `src/persona/yandere_fsm.py` | ADR-001 |
| P28 needs to modify Hermes source | NO (P28 §4.6 forbids: "No modifying AIAgent constructor signature (Hermes upstream)") | P28 §4.6 L2086-2093 |
| P28 needs Hermes runtime 24/7 fork lifecycle | **YES (PREFERRED, deferred)** — P32 will integrate the fork lifecycle patch (P24-006) for cleaner §0.1 V-008 enforcement at the framework level | P27 §14.8 L3301; P27 §15.6 |
| P28 needs per-Society `PersistentTaskRegistry` | NO — P28 can use APScheduler instances per Society (`src/life_kernel/`) | P27 §6.5 ShadowPipeline precedent |
| P28 needs `v0.15.2-guinevere.N` reproducibility | NO (preferred optimization) — APScheduler pattern achieves functional reproducibility today | P32 handoff contract |

**Conclusion: P28 has zero hard dependencies on P24.** P24 is a future quality-of-life improvement.

---

## 7. Critical Insights for Masterplan + Prompt-Pack Author

### 7.1 Insight — P28 Production-Pass ≠ P24 Production-Pass

**Critical for downstream prompt-pack:** The P28 "production pass" gates are **independent** of P24-020 soak. They are:

- **P28 Soak:** 3+ consecutive 24h soak windows with both bots (Guinevere + Pharsa) online and peer-to-peer messages flowing (ADR-054 §Implementation Path, P28 blueprint acceptance).
- **P28 HARD STOP proven to halt both within 5 seconds** (cross-instance cascade via Redis `life_kernel:hard_stop_requested`).
- **P28 audit trail verified:** all HPP envelopes hash-chained; all peer dialog recorded under 4-domain privacy split.
- **P28 anti-sycophancy verified:** no convergence groupthink between Guinevere and Pharsa.

**The P24-020 soak is a SEPARATE gate** for P24 itself (fork-version of Hermes), and only matters if/when P32 (P24 Fork Integration) begins — not for P28 go-live.

### 7.2 Insight — P32 (P24 Fork Integration) Depends on P28 PRODUCTION PASS, not the Reverse

Per `P27/plan/p27-p28-p36-master-roadmap.md` §7 L488-503:
- P32 Wave prerequisites: **P24 implementation HOLD lifted (P24-005 → P24-020 PASS) AND P28 PRODUCTION PASS**.
- P32 Trigger: P28 verified stable; P24 lift approved by mama; VPS deploy proven for Society instances.
- P32 Wave steps (8-10): provenance verification, MIT/NOTICE confirmation, parity test, `hermes_lifecycle/persistent_tasks.py` integration (P24-006), per-Society `.venv-hermes-canary` smoke, VPS deploy strategy, rollback drill, etc.

**The P28 → P32 ordering is exactly the reverse of the user's premise** ("P24 → P28"). The actual dependency: **P28 first, then P32 (fork integration)**.

### 7.3 Insight — Fork-Agnostic Architecture Means Future PXX Can Also Stay Independent

P27 has **6 forbidden patterns** specifically blocking P24-dependence creep:
- ❌ P27 must NOT block on P24 fork (Audit 07 F2 PASS)
- ❌ P27 must NOT promise fork-based multi-instance to P28
- ❌ P27 must NOT skip Section 17 refactor even with fork available (`guinevere.slice` resource caps require per-process isolation regardless)
- ❌ P27 must NOT claim runtime-fork independence is impossible (PASS in Audit 02)
- ❌ P27 must NOT commit secrets to enable P24 paths
- ❌ P27 must NOT skip per-step audit

P28 must inherit this discipline: its acceptance gates must remain **fork-agnostic-verifiable** so the architecture doesn't silently break if P24 fork is delayed or never lands.

### 7.4 Insight — Implementation Hold Reasons Differ from "P24 Is Hard Dependency"

**P24's own implementation hold reasons** (P20 axis preflight + P19 namespace + P24-002 source inspection) are internal to P24. They do NOT block P28 because P28's runtime path is unchanged regardless of P24 status:

- **P20 axis:** P20 has EARLY ACCEPTANCE; preflight is a pre-implementation step for P24 only (P20 runtime is already live).
- **P19 namespace:** P19 is now PRODUCTION COMPLETE (2026-06-27) — readiness cleared.
- **P24-002 source inspection:** this is the gate for the **fork CREATION** step (does Hermes v0.15.2 actually need `on_startup(task_factory)` or is extension-only sufficient?). P28 won't fork Hermes regardless, so this is moot.

---

## 8. Recommended Masterplan + Prompt-Pack P28 Prerequisite Gates

### 8.1 Recommended Gates (REPLACE "P24 must pass before P28" with these)

For P28 to begin implementation:

| Gate | Source of truth | Binary-checkable? |
|---|---|---|
| **G1. P27 DEFINITION COMPLETE (accepted)** | `adr/ADR-054-p27-hermes-society-foundation.md` Accepted 2026-06-28; P27 evidence file PASS | YES — `grep "Status: Accepted" ADR-054-p27-*.md` |
| **G2. P19 PRODUCTION COMPLETE (project_id namespace live)** | `PROGRESS.md` P19 row: "PRODUCTION COMPLETE — CORE + DISCORD UX LIVE — round-2 audit 2026-06-27 PASS" | YES — `grep "P19.*PRODUCTION COMPLETE" PROGRESS.md` |
| **G3. P20 EARLY ACCEPTANCE (or 24h clean soak)** | `PROGRESS.md` P20 row: "EARLY ACCEPTANCE" (operator waived 24h soak 2026-06-25) | YES |
| **G4. P22.1 FOUNDATION HARDENING PRODUCTION PASS** | `CHECKLIST.md` P22.1 row: "✅ PRODUCTION PASS" (audit_writer + consent_checker + L2+ proof, 14/14 live VPS) | YES |
| **G5. P23B implementation deferrable (not required for P28)** | `P27/plan/p28-dual-autonomous-hermes-blueprint.md` §2.1 L97: "[P23 Embodied Operations] NOT NEEDED — P28 doesn't depend on executors" | YES |
| **G6. Fork-agnostic P28 blueprint accepted** | P28 blueprint §1.2 L65: "fork = preferred optimization, not prerequisite" | YES |
| **G7. P28 preflight (AGENTS.md §3 session-start, §1.1 documentation readiness)** | Standard Guinevere pre-flight | YES |
| **G8. PROGRESS.md P24 row reflects `IMPL HOLD` (informational only)** | `CHECKLIST.md` P24 row: "PLAN FIXED — IMPL HOLD UNTIL MAMA AUDIT" | YES — but does NOT block P28 |

### 8.2 Forbidden Prompt-Pack Patterns (P28 Author must NOT include)

- ❌ "BLOCK P28 impl until P24-020 production pass." — FALSE (P28 doesn't need fork).
- ❌ "Halt if P24 fork repo not created." — FALSE (P28 uses upstream).
- ❌ "Audit P24 status before kicking off P28 waves." — Wasting budget; P24 status is informational.
- ❌ "Validate Hermes is forked before starting P28 migrations." — FALSE.

### 8.3 Recommended Prompt-Pack Phrasing

**Recommended pre-flight check for P28:**
```yaml
p28_preflight:
  gates:
    - id: g1
      name: "P27 Plan Accepted"
      check: "grep -q 'Status: Accepted' adr/ADR-054-p27-hermes-society-foundation.md"
      severity: "BLOCKING"
    - id: g2
      name: "P19 Production Complete"
      check: "grep -q 'P19.*PRODUCTION COMPLETE' PROGRESS.md"
      severity: "BLOCKING"
    - id: g3
      name: "P20 Active (Early Acceptance or Soak)"
      check: "grep -qE 'P20.*(EARLY ACCEPTANCE|24h PASS)' PROGRESS.md"
      severity: "BLOCKING"
    - id: g4
      name: "P22.1 Foundation Hardening Pass"
      check: "grep -q 'P22.1.*PRODUCTION PASS' CHECKLIST.md"
      severity: "BLOCKING"
    - id: g5
      name: "P28 Blueprint Fork-Agnostic"
      check: "grep -q 'fork = preferred optimization, not prerequisite' docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md"
      severity: "BLOCKING"
    - id: i1
      name: "P24 Status (informational only)"
      check: "grep -q 'P24.*IMPL HOLD' CHECKLIST.md"
      severity: "INFO_ONLY"
      note: "P24 impl hold does NOT block P28; P32 (P24 Fork Integration) is deferred until P28 + P24-005 soak pass"
```

---

## 9. Open Questions for Masterplan Owner

| # | Question | Decision authority | Default (if no decision) |
|---|---|---|---|
| 1 | If P24 fork never lands, does the architecture remain complete? | Faiz | YES (P27 §14.10: "If P24 fork is delayed beyond P32, the architecture remains functional with hybrid adapter + per-instance config") |
| 2 | P32 timeline: parallel-launch-with-P28 vs after-P28-soak-pass? | Faiz | AFTER (P27 §7.3: "P24 IMPL HOLD must lift first. P28 §1.2 L65: 'fork = preferred optimization, not prerequisite'") |
| 3 | Does P28 Lite (single Guinevere) require the same gates as full P28 dual-bot? | Faiz + Guinevere | YES (P28 minimum target IS dual-bot) |
| 4 | Should PROGRESS.md be updated to clarify upstream runtime = P28 substrate? | Faiz | Optional; current wording already says "P24 fork NOT required for P28" |
| 5 | For `lanjut N` autopilot, should P28 waves auto-start when its gates pass, or queue behind P23B/P21 definitions? | Faiz | After P28 preflight PASS: auto-start |

---

## 10. File References — All Sources Parent-Read

### P24 Source Files (all read, absolute paths)

| File | Topic |
|---|---|
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\README.md` | P24 phase README (status, verdict, research summary, audit summary, plan-fix note) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\plan\p24-hermes-fork-first-full-convergence-plan.md` | Plan (44 sections, 20 waves, 1155 lines) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\evidence\final-p24-planning-report.md` | Final report (metrics, status, blockers) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\evidence\p24-definition-verification.md` | Definition verification (acceptance mapping) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\evidence\auditor-gate.md` | Auditor gate (round 1 + 2 + plan-fix + mama round 3) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\evidence\p24-plan-fix-verification.md` | Plan-fix verification (5 codex blockers) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\evidence\audits\round-1\*.md` | 13 round-1 auditor reports (condensed summary in `auditor-gate.md`) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\*.md` | 14 research files (referenced; not all re-read for this report) |

### P27 References to P24 (read, relevant)

| File | Topic |
|---|---|
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\research\p27-p24-fork-dependency-map.md` | **PRIMARY AUTHORITY** — 656-line dependency map (parent-read fully) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\plan\p27-hermes-society-foundation-plan.md` | §14 (P24 Dependency Map, L3175-3315); §17 Single-Instance Refactor Plan |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\plan\p27-p28-p36-master-roadmap.md` | §7 (P32 P24 Fork Integration, deferred) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\plan\p28-dual-autonomous-hermes-blueprint.md` | §1.2, §2.1, §4 (fork-free, config-driven) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\audits\round-1\07-p24-dependency.md` | **PASS verdict** (fork-agnosticism verified across 11 audit criteria) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\audits\round-1\14-hard-rejection-criteria.md` | Crit 20 (PASS): "FAIL if Society depends on P24 fork" |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\audits\round-1\11-roadmap.md` | Confirms P24 fork = P32, deferred |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\audits\round-1\13-impl-feasibility.md` | C14 PASS: "No step requires P24 fork" |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\audits\round-1\08-p22-p23-dep.md` | Confirms P28 §2.1: P24, P23, P21 NOT NEEDED |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\audits\round-1\05-discord-dual-bot.md` | P24 dependency properly handled |
| `C:\Users\faizz\guinevere\adr\ADR-054-p27-hermes-society-foundation.md` | Accepted ADR; §Positive: "P28 may proceed without P24 fork" |

### Repo-Level References (read)

| File | Topic |
|---|---|
| `C:\Users\faizz\guinevere\PROGRESS.md` | Phase status table; P24 row (IMPL HOLD); P27 row (DEFINITION COMPLETE); Last Updated 2026-06-28 |
| `C:\Users\faizz\guinevere\CHECKLIST.md` | Budget table; P24 row (PLAN FIXED — IMPL HOLD); P27 row (DEFINITION COMPLETE); P22.1 row (✅ PRODUCTION PASS) |

### NOT Re-Read (referenced but content known from prior summary)

- `src/life_kernel/hermes_brain.py` (verified by grep — sole `from run_agent import AIAgent` consumer)
- `src/hermes/adapter.py`, `src/hermes/_session_adapter.py`, etc. (7 adapters from P24 inventory)
- `src/hermes_plugins/commands_*` (44 command plugins)
- `hermes-config/config.yaml` (394 lines, deployed via ADR-035)
- All 14 P24 research files beyond `p24-hermes-upstream-identity-research.md` and `p24-extension-points-hooks-plugins-research.md` (referenced but not full-read for this report)
- All P24 round-1 audit reports (only `01-equal-peer.md` summary, others summarized in `auditor-gate.md`)

---

## 11. Summary Table

| Question | Answer |
|---|---|
| Is P24 required for P28? | **NO** (sources align: PROGRESS.md, ADR-054, P27 §14, P28 §1.2/§2.1, Audit 07 PASS, Audit 14 PASS, Audit 11 PASS, Audit 13 PASS) |
| Is P24 fork created? | **NO** (P24-003 HELD; no fork repo on `github.com/fazulfim/hermes-agent`) |
| Is P24 runtime code deployed? | **NO** (P24 is DEFINITION/PLANNING ONLY — 0 `.py` files in `docs/setup-evidence/P24/`) |
| What is P24's recommended verdict? | **FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION READY** (hybrid = transition; full owned fork = final) |
| What's blocking P24 implementation? | 3 hold blockers (P20-axis preflight + P19 namespace readiness [now cleared] + P24-002 first-patch scope). All by-design; not defects. |
| What is "production pass" for P24? | 24h soak (P24-020) with HARD STOP cascade + §0.1 autonomy invariants + parity tests + rollback drill verified |
| Does P28 require P24-020 soak? | **NO** — P28 production pass is a separate 24h dual-bot soak with peer-to-peer messages + HARD STOP cross-instance + anti-sycophancy verification |
| When does P24 production pass matter? | For **P32 (P24 Fork Integration)** — which happens AFTER P28 PRODUCTION PASS, not before |
| Is the user's premise ("P24 before P28") correct? | **NO** — the actual dependency is reversed: **P28 first, then P32** |

---

## 12. Verification

This research file was produced by:
- 9-file read (P24 README, plan, 3 evidence files, ADR-054, PROGRESS.md, CHECKLIST.md, P27 P24 dependency map)
- 41-file glob of P24 directory
- 8-file grep across P27 for P24 references
- 50+ file grep via `head_limit` for `hermes|Hermes` in `src/`
- 18-file grep for P27 P24 dependency references

**No secrets exposed. No runtime code executed. All findings derived from file reads and grep. Markdown aligned with AGENTS.md persona operating contract.**

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Buffy (codebase search specialist sub-agent for Guinevere) | Initial P24 → P28 dependency research; user premise corrected (P24 NOT a hard P28 dependency; P32 deferred) |

**Verdict:** P28 may proceed WITHOUT waiting for P24. The "P24 production pass" is a P32 requirement (fork integration phase, deferred to after P28 PRODUCTION PASS). Masterplan + prompt-pack should NOT include a P24 production-pass gate blocking P28.