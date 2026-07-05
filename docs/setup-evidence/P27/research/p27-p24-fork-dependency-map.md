# P24 → P27 Dependency Map: Hermes Fork vs Hermes Society Foundation

**Research Date:** 2026-06-28
**Author:** Buffy (codebase search specialist, sub-agent for Guinevere)
**Scope:** Map P24 Hermes Fork-First Full Convergence deliverables onto P27 Hermes Society Foundation requirements; partition definitional vs implementational concerns; assess multi-instance support; identify extension points, risks, and handoff contract.
**Sources:** 11 P24 docs (1 plan, 3 evidence, 7 research) — all parent-read.

---

## 1. P24 Mission and Direction

**Mission (verbatim, plan §1):** "Determine and design how to make Guinevere truly Hermes-native through an owned Hermes fork OR hybrid fork+plugin. All legacy capabilities (P1-P18) and new capabilities (P20/P21/P22/P23) must have an integration path into Hermes built-in/runtime — not just side modules."

**Final verdict (plan §15):** **FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION READY**.

**Operator source of truth (2026-06-25 verdict correction):**
- Mission is **ownership and convergence**, not gap-patching.
- Fork chosen even though research consensus (13/14 files) shows extension-only is *technically* viable.
- Rationale: reproducible, pinned, forked, auditable, deployable, roadmap-controlled runtime.
- "Plugin sufficient" reinterpreted as "fork delta can be small; plugins become internal extension modules inside the owned fork distribution" — NOT a reason to avoid forking.

**Three options + final choice:**

| Option | Description | Status |
|---|---|---|
| A: No Fork | Extension-only via upstream hooks/plugins/MCP | RECOMMEND by research; REJECTED by operator (forfeits ownership) |
| B: Hybrid Fork | Minimal fork delta + plugins-as-extensions | ACCEPTED as transition path only |
| C: Full Fork | Entire hermes-agent repo forked + Guinevere plugins internal | **FINAL ARCHITECTURE TARGET** under ownership mission |

**Hard constraints preserved:**
- `.venv/site-packages` edit FORBIDDEN (§9).
- §0.1 autonomy-first governance (V-003/V-007/V-008) preserved.
- No P20 production soak disruption.
- No secrets/commit/intimate-data exposure.

---

## 2. P24 Current Status

### 2.1 Phase Status (verbatim from evidence)

| Metric | Value |
|---|---|
| Phase | P24 — Hermes Fork-First Full Convergence |
| Category | DEFINITION / PLANNING ONLY — NO runtime implementation |
| P24 files | 41 (exact) |
| P24 lines | 13,426 (exact `wc -l`) |
| Research files | 14 (all COMPLETE) |
| Audit round 1 | 13 auditors |
| Audit round 2 | 3 re-audits (all PASS) |
| Plan sections | 44 |
| Implementation waves | 20 (P24-001 → P24-020, ALL HELD) |
| Implementation status | **HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL** |
| Secret scan | CLEAN (zero secrets) |
| Runtime code | NONE (definition only) |
| Deploy/restart | NONE |

**Verdict string (verbatim):** `"P24 PLAN FIXED — FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL"`.

### 2.2 Is the Fork Done?

**NO.** The fork is **planned to the implementation-ready state** but **not yet created**. Specifically:
- ❌ No fork repo created on `github.com/fazulfim/hermes-agent`.
- ❌ No source acquisition from `github.com/NousResearch/hermes-agent`.
- ❌ No Hermes upstream source inspection (P24-002 first patch scope verification is part of implementation hold).
- ❌ No `.venv/site-packages` edit (forbidden).
- ❌ No fork pin in `pyproject.toml` (current pin: `hermes-agent>=0.15` line 31).

### 2.3 Implementation Hold Blockers (by design — not defects)

1. **P20 axis** satisfied by operator accepted-risk waiver (before touching P20/LOCKED runtime files, run fresh runtime incident preflight).
2. **P19 definition exists**; P24 implementation depends on current P19 namespace contract readiness.
3. **P24-002** scopes the first internal patch (P20 heartbeat) — does NOT gate the fork decision (fork chosen on ownership grounds).

P24's own future 24h soak (wave P24-020) is separate and remains valid.

### 2.4 Discrepancy Caller Must Understand

Research file `p24-installed-runtime-surface-inventory.md` (§388-399) flags an **ADR-035 status vs runtime discrepancy**:
- ADR-035 status = "Implemented".
- Runtime evidence = hybrid adapter pattern, not full Hermes gateway replacement.
- Discord standalone bot masked; Hermes Gateway Discord active for turn-core; P20 uses REST publisher for dashboard/logs.

This affects P27 (Hermes Society = multi-Hermes instance architecture) because if the single Hermes Gateway is not fully deployed, the multi-instance pattern cannot be cleanly derived from runtime evidence yet.

---
## 3. What P24 Provides That P27 Needs

### 3.1 Fork Ownership (MVP deliverable when P24 implemented)

| Deliverable | When P24 implemented | Useful to P27? |
|---|---|---|
| Private fork repo `github.com/fazulfim/hermes-agent` | P24-005 | YES — P27 needs canonical, owned runtime to run multiple instances (Societies) per Guinevere roadmap. |
| MIT license preserved + NOTICE file | P24-005 | YES — required for any onward distribution / cloning to per-society instances. |
| `main` ↔ upstream `main` branch policy | P24-005/P24-013 | YES — rebase discipline applies to each Society-specific patch. |
| `guinevere` branch with fork additions | P24-005/P24-006 | YES — Guinevere-specific code lives only here. |
| Tags: `v0.15.2-guinevere.N` | P24-005, P24-018, P24-019, P24-020 | YES — pinning per-society Hermes fork versions. |
| Rollback tag `v0.15.2-upstream` (vanilla upstream) | P24-005 | YES — emergency fallback if Society instance corrupts. |
| `pyproject.toml` pin via `git+https@tag` | P24-005, P24-019 | YES — per-society pinning mechanism. |

### 3.2 Hermes Runtime Surface (Already Inventory in P24)

From `p24-installed-runtime-surface-inventory.md` and `p24-hermes-upstream-identity-research.md`:

| Surface | Count | Source of Truth |
|---|---|---|
| Direct imports | 1 (`from run_agent import AIAgent`) | `src/hermes/_session_adapter.py:30` |
| Local adapters (`src/hermes/`) | 7 | `adapter.py`, `_session_adapter.py`, `_memory_bridge.py`, `safety_plugin.py`, `plugins/persona_plugin.py`, `plugins/__init__.py`, `__init__.py` |
| In-process plugins (`hermes-config/plugins/`) | 3 | `auth_overlay`, `guinevere_persona`, `guinevere_safety` |
| Command plugins (`src/hermes_plugins/`) | 44 | 7 categories: admin, finance, high, loop, memory, surveillance, system |
| Shell hooks (`hermes-config/hooks/`) | 12 | hard_stop, consent_gate, dnr_filter, safety_scan, budget_check, drift_check, error_classifier, finance_hook, hybrid_guards, budget_lua, budget_lua_extended, _hook_utils |
| Config file | 1 | `hermes-config/config.yaml` (394 lines) |
| SOUL file | 1 | `hermes-config/SOUL.md` |
| MCP servers (Hermes config) | 2 | `fastmcp_full` (enabled), `fastmcp_custom` (disabled) |
| Cron jobs | 8 | 5 persona rituals + 3 maintenance |
| Plugin manifests | 3 | `plugin.yaml` ×2, `manifest.yaml` ×1 |

**P27 implication:** the existing runtime surface assumes ONE shared `hermes-config/` directory. P27 multi-society requires per-society isolation (config dir, venv, systemd units). This is NOT yet designed in the P24 fork.

### 3.3 Extension Points (the Mechanism P27 Will Use)

From `p24-extension-points-hooks-plugins-research.md`, ~40 official extension points:

| Mechanism | Count | Examples |
|---|---|---|
| Config sections | 9+ | discord, model, memory, hooks, mcp_servers, cron, observability, approval, agent |
| Lifecycle hook events | 17 | pre_llm_call, post_llm_call, pre_tool_call, post_tool_call, transform_llm_output, on_session_start/end, pre_gateway_dispatch, pre/post_api_request, pre_approval_request, post_approval_response, on_session_finalize/reset, subagent_stop, transform_terminal_output, transform_tool_result |
| Shell hook scripts | 9 | finance, budget, consent, DNR, drift, hard_stop, hybrid_guards, error_classifier (+ _hook_utils) |
| In-process plugins | 3+ | auth_overlay, guinevere_persona, guinevere_safety |
| MCP servers | 2+ | fastmcp_full (enabled), fastmcp_custom (disabled) — extensible |
| Cron jobs | 8+ | extensible |
| Plugin manifests | 3+ | plugin.yaml ×2, manifest.yaml ×1 — extensible |
| **Total extension points** | **~40** | confirmed stable in Hermes v0.15.2 |

**Per P24 §18.1 contract-gating:** future-phase convergence claims must not be "final" until each runtime contract is runtime-proven. P27 is in this category (contract-gated).

### 3.4 Native Runtime Components P24 Will Add (Target)

From `p19-p20-life-kernel-convergence-map.md` and plan §19-22:

| Component | Hermes-native equivalent | Fork addition? |
|---|---|---|
| Heartbeat (1s persistent) | `on_startup(task_factory)` + `on_shutdown(task_canceller)` | **YES** — first internal fork patch (`hermes_lifecycle/persistent_tasks.py`, <200 LOC) |
| Heartbeat (5m, 1h) | Hermes cron jobs | NO |
| LangGraph StateGraph | BaseSaver adapter | NO |
| Checkpoint (Redis) | Hermes state store adapter | NO |
| World model (PostgreSQL) | Keep PostgreSQL | NO |
| HARD STOP (Redis key) | Hermes global flag OR keep Redis | NO |
| Discord REST client | Hermes Gateway Discord adapter | NO |
| Dashboard writer | Hermes Gateway edit-message | NO |
| Log channel | Hermes Gateway send-message | NO |
| HermesBrain | AIAgent wrapper (already native) | NO |
| BackgroundCognition (6 observer loops) | Hermes lifecycle hooks | NO (lifecycle hook exists upstream) |
| Sensor registry | Hermes input hook registry | NO |
| Domain minds | Hermes-aware modules | NO |
| Audit journal | Keep PostgreSQL | NO |

**P27 implication:** for societies to run as autonomous 24/7 instances, P27 design must **anticipate** the `on_startup(task_factory)` lifecycle patch from P24 (P24-006). However, P27 can be designed now without waiting — see §4.

---

## 4. What P27 Can DEFINE Now (Without P24 Implementation)

These are **definitional** artifacts — they describe WHAT P27 is, not HOW it's implemented. They depend only on P24's research/planning outputs (which ARE complete), not on the fork being implemented.

### 4.1 Society Identity & Membership

**Definable now** (no fork code required):

| Concept | What can be defined now | Source in P24 |
|---|---|---|
| Society ID convention | UUID v7 or slug+hash, with version pinning per ADR pattern | Plan §31 versioning template |
| Society role taxonomy | Operator, observer, contributor, auditor, lifetime-member, prospect | Define via PersonaDocument v3.1 permission roles (exists in repo) |
| Society registry schema | PostgreSQL `society_registry` table (id, name, charter_url, parent_fork_version, status) | Plan §28 fork repo versioning |
| Society charter format | Markdown with header pattern, signers, consent record | PersonaSafetyPolicy v1.0 §2.1 authority order |
| Society-to-Project mapping | project_id ↔ society_id binding (compatible with P19 namespace contract) | `p24-p19-p21-p22-p23-forward-compatibility-map.md` §2.1 (P19 = `project_id` namespace) |
| Society tier (founder/active/prospect) | Charter-defined governance rules | ADR-035 boundary pattern |

### 4.2 Society Architecture Pattern

**Definable now:**

| Concept | What can be defined now |
|---|---|
| Society = bounded Hermes runtime + bounded knowledge graph + bounded memory partition | Compatible with P16 KG `path_id`/`entity_id` + P3 memory `project_id` partition patterns |
| Each Society owns one Hermes fork install (one venv, one systemd unit) | Compatible with P24 fork repo (one fork = N installs, one install = one process) |
| Society boundary types | Hard (separate venv) / Soft (shared venv, separate config dir) |
| Society identifier routing | Pre-LLM hook injects society context into system prompt (existing pattern from `PersonaPlugin`) |
| Society consensus protocol | Discord thread per society + heartbeat publication |
| Society observability contract | Per-society Prometheus labels + Loki log stream prefix |

### 4.3 Society Governance & Compliance

**Definable now** (using existing safety/persona/docs):

| Concept | Where it lives (already exists) |
|---|---|
| HARD STOP propagation across Societies | `AGENTS.md §0.1 + V-008` + P24 §22 HARD STOP integration (already defined) |
| HARD STOP <50ms invariant (cross-Society) | `PersonaSafetyPolicy v1.0 §7.2` (already exists) |
| Consent revocation per Society + global | `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` (exists) |
| Y6 architectural prohibition across Societies | `PersonaSafetyPolicy v1.0` + `src/persona/yandere_fsm.py` (already exists) |
| §0.1 autonomy-first across Societies | `AGENTS.md §0.1` (exists) |
| Audit journal per Society | Compatible with `src/life_kernel/journal.py` PostgreSQL audit |
| Surveillance policy per Society | `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` (exists) |
| PII/intimate data isolation per Society | `docs/30-data/30-DataGovernance_Classification_v1.0.md` (exists) |
| Tier-based confidentiality (Public/Internal/Restricted/Confidential/Critical) | Already enforced in `src/memory/read_pipeline.py` |

### 4.4 Society Interface Contract

**Definable now** — describe the contract surface P27 will publish to Society instances (independent of fork implementation):

```yaml
society_contract_v1:
  identity:
    society_id_format: "{slug}-v{epoch}-{short_hash}"
    charter_uri: "/society/{society_id}/charter.md"
    parent_doctrine: "AGENTS.md §0 + PersonaSafetyPolicy v1.0"
  runtime:
    hermes_fork_min_version: "v0.15.2-guinevere.1"   # placeholder until P24 implemented
    extension_points_required: ["pre_llm_call", "pre_tool_call", "on_session_start", "on_session_end"]
    expected_plugins: ["society_router", "society_audit", "society_consent"]
  governance:
    hard_stop_propagation: "global_only_v8"        # requires P24 fork V-008 enforcement
    consent_revocation: "society_scoped + global"
    audit_journal: "postgresql:/society/{society_id}/audit/"
  isolation:
    config_dir: "/etc/guinevere/society-{society_id}/"  # or hermes-config/
    venv_path: "/home/guinevere/code/guinevere/.venv-society-{society_id}/"
    systemd_unit_pattern: "guinevere-society-{society_id}.service"
  p27_incompatibility_signals:
    - society_id missing from messages
    - parent_fork_version < minimum
    - audit_journal unwritable
```

### 4.5 Society Templates & Scaffolding

**Definable now** (docs + scaffolding, not runtime):

| Template | Type | Notes |
|---|---|---|
| `docs/setup-evidence/P27/society-template/charter.md` | Markdown | Charter format with signers + effective date |
| `docs/setup-evidence/P27/society-template/society_config.yaml` | YAML | Hermes-config per society (matches existing format) |
| `docs/setup-evidence/P27/society-template/plugin_manifest.yaml` | YAML | Uses same `plugin.yaml`/`manifest.yaml` pattern |
| `docs/setup-evidence/P27/society-template/audit_schema.sql` | SQL | PostgreSQL tables for society-specific audit |
| `docs/setup-evidence/P27/society-template/consent_schema.sql` | SQL | Society-scoped consent + revocation |
| `docs/setup-evidence/P27/society-template/README.md` | Markdown | How-to-fork-a-society guide (defines the ceremony, not the code) |

---

## 5. What P27/P28 IMPLEMENTATION Requires from P24

These are **implementation blockers** — they require runtime code or rewrite from P24 fork work to manifest.

### 5.1 Hard Implementation Dependencies

| Need | Why required | P24 wave that delivers | P27 readiness |
|---|---|---|---|
| Owned Hermes fork repo with MIT + NOTICE | Per-society install must be reproducible + auditable | P24-005 | NOT YET (impl hold) |
| `pyproject.toml` git+https pin (`v0.15.2-guinevere.N`) | Automated deploy + rollback per society | P24-019 | NOT YET |
| Isolated canary `.venv-hermes-canary` + canary unit | Required before shared-`.venv` promotion (mama round-3 fix) | P24-018 | NOT YET |
| Parity test that fork = upstream behavior + Guinevere tests | Refactor safety; societies must pass identical test suite | P24-009 + P24-020 | NOT YET |
| `hermes_lifecycle/persistent_tasks.py` (<200 LOC) for 1s heartbeat | Society instance must run 24/7 like P20 kernel | P24-002 + P24-006 | NOT YET |
| `on_startup(task_factory)` lifecycle hook registration | Same as above; first internal patch | P24-006 | NOT YET |
| Section 36 VPS deployment strategy accepted (post round-3 fix) | Per-society VPS deploy needs hardened pipeline | P24-019 + P24-020 | NOT YET |
| Section 35 rollback-to-upstream <5min verified by drill | Society corruption must be quickly reversible | P24-019 | NOT YET |
| 24h soak P24-020 pass (autonomy invariants + HARD STOP latency) | Production-readiness gate | P24-020 | NOT YET |

### 5.2 Soft Implementation Dependencies (Degradable)

These can be worked around with adapters if P24 fork is delayed, but clean implementation requires fork.

| Need | Workaround if P24 delayed | Better path after P24 done |
|---|---|---|
| Per-society plugin isolation | Use separate `hermes-config/` directory per society, shared `.venv` (soft isolation only) | Fork delivers true plugin-as-internal-module isolation per society install |
| Per-society Forge registry | Currently use Discord threads + PostgreSQL `society_registry` table | Fork supports Hermes-aware society metadata |
| Per-society HARD STOP propagation | Hand-rolled Redis pub/sub keyed by `society_id` | Fork's HARD STOP global flag (V-008) threaded through fork lifecycle |
| Per-society state persistence | Use separate Redis DB number per society | Fork `BaseSaver` adapter (planned for P23) supports society-scoped state |
| Per-society MCP tools | Each society has its own FastMCP server config | Fork supports MCP servers per society natively |

### 5.3 What P27 Cannot Define Until P24 Implementation Completes

| Topic | Why must wait |
|---|---|
| Society-specific internal patch strategy | Cannot know fork branching strategy until P24-005 + P24-013 executed |
| Society-specific HARD STOP <50ms enforcement | Cannot verify latency until P24-020 soak runs in production |
| Society plugin distribution / GitHub Packages / pull policy | Cannot lock distribution model until P24-019 VPS deploy proven |
| Society instance parity test suite | Requires P24-009 parity test framework |
| Per-society rollback drill (P24 runbook) | Requires P24-019 rollback tested |

---
## 6. Fork Strategy: Single Fork → Multi-Instance

### 6.1 What P24 Documents Explicitly

From `p24-hermes-fork-first-full-convergence-plan.md` §28 (`Fork Repo Strategy`), §30 (`Upstream Sync`), and the Research files:

- **ONE fork repo:** `github.com/fazulfim/hermes-agent` (private).
- **ONE fork delta today:** `<200 LOC` for `hermes_lifecycle/persistent_tasks.py` + registration.
- **Distribution model:** `pyproject.toml` pins via `git+https@tag` per install.
- **Branching:** `main` tracks upstream; `guinevere` carries fork additions.
- **Tag schema:** `v0.15.2-guinevere.N` (N = Guinevere fork iteration), with `v0.15.2-upstream` as rollback alias.

**The plan does NOT explicitly discuss multi-instance deployment.** It assumes ONE fork installed per environment per pin version (one VPS = one Guinevere instance = one fork install).

### 6.2 What This Means for Multi-Society

Two interpretations of "multi-instance":

| Interpretation | P24 support level | P27 work needed |
|---|---|---|
| **Multi-VPS, single fork** (e.g., one VPS per Society, each installs same fork) | PARTIAL — supported by current plan §36 (VPS deploy). Each VPS install = separate venv, separate systemd unit, separate `hermes-config/`. | P27 just standardizes the install/upgrade ceremony. No fork changes needed. |
| **Multi-Society on single VPS** (e.g., one VPS runs 5 Societies concurrently) | NOT EXPLICITLY DESIGNED. Plan §36 VPS strategy is per-install. | P27 likely needs new design: per-Society venv + per-Society systemd unit + per-Society config dir on ONE VPS. P24 does not preclude this; P24 deployment strategy applies to each instance independently. |

### 6.3 Recommended Fork Strategy for P27

**Recommendation:** Start with multi-VPS (one Society = one VPS = one fork install). Migrate to single-VPS multi-Society only after fork is proven stable and per-Society isolation contract is established.

| Phase | Strategy | Reason |
|---|---|---|
| P27 alpha | One Society per VPS install of the fork. Society boundary = VPS boundary (simplest audit + strongest isolation). | Existing P24 plan addresses this directly. |
| P27 beta | Multiple Societies on one VPS via per-Society venv + per-Society systemd + per-Society `hermes-config/` directory. | Implementable today via config-level isolation (no fork code change). |
| P27 production | Hybrid: founders on dedicated VPS, general Societies on shared VPS. | Requires confirmation that shared `.venv` is acceptable per Society boundary; better to validate slowly. |

---

## 7. Does P24 Fork Direction Support Multiple Hermes Instances?

### 7.1 Native Support (Out of the Box)

| Aspect | Native support in P24 fork | Source |
|---|---|---|
| Multiple installs of same fork version | YES — pip/git+https installs `v0.15.2-guinevere.1` into any venv | Plan §28, §29 |
| Per-install config isolation | YES — `hermes-config/config.yaml` per install; no sharing assumed | Inventory §3 |
| Per-install systemd unit | YES — `hermes-gateway.service` is per-install; new units per Society | Plan §36 |
| Per-install plugin loading | YES — Hermes config + plugin manifest per install | Extension research §4 |
| Per-install HARD STOP | UNCERTAIN — current pattern uses single Redis key `life_kernel:hard_stop_requested`; multi-instance = need namespace | Plan §22 + §20 |
| Per-install 24/7 heartbeat | YES via `on_startup(task_factory)` once P24-006 completes | Plan §20 |
| Per-install Discord channels | YES — Discord config and `send_message` are per-install | Inventory §3 |

### 7.2 Missing Pieces for Multi-Society from P24

| Gap | Required for multi-Society | P24 status |
|---|---|---|
| Society ID propagation through hooks | Per-society HARD STOP, per-society audit, per-society session routing | NOT DESIGNED — current model is monolithic |
| Multi-society HARD STOP semantics | Per-society isolated OR global cascade? Prerequisite for governance charter | NOT DESIGNED — Redis key currently single |
| Per-society namespace contract for memory/KG | Distinct from P19 `project_id` namespace | NOT DESIGNED — overlaps with P19 |
| Per-society plugin loader config | Loading N society-specific plugins from M directories | POSSIBLE — currently each install loads from one `hermes-config/plugins/` |
| Per-society MCP server naming | `fastmcp_full` would conflict across installs only if shared-VPS | NOT ADDRESSED — each install has one MCP namespace, but shared VPS lacks convention |
| Per-society fork branch / per-society patch delta | Different Societies may need different fork deltas over time | NOT DESIGNED — single Guinevere branch |
| Per-society currency/audit/observability prefix | Prometheus labels, Loki labels, audit schema keys | NOT DESIGNED |
| Per-society FAIL-SOFT on cross-society HARD STOP | If one Society HARD STOPS, must not affect others | NOT DESIGNED |

### 7.3 What Changes Are Needed for Multi-Society

Three options (in order of effort):

| Option | Description | When to choose |
|---|---|---|
| Isolation via per-Society VPS install | Each Society = different VPS install = different fork pin (maybe same Git tag, different `hermes-config/` directory) | First multi-Society deployment. P24 unchanged. |
| Isolation via per-Society venv on shared VPS | Each Society = different venv, different config directory, different systemd unit. Fork repo unchanged. | When VPS economics force consolidation |
| Fork-level isolation | Per-Society fork branches per `github.com/fazulfim/hermes-agent`; each Society installs its own fork tag | Only when Societies need divergent patches |

**Recommendation:** P27 must define which isolation strategy is REQUIRED (e.g., "separate VPS for founders, shared venv for fine Societies") and feed that into the P24 fork design as a forward-compatibility note. Default to isolation-via-VPS-install for alpha.

---

## 8. Extension Points in the Fork That P27/P28 Can Use

### 8.1 Direct Usable Extensions (no fork change needed)

From `p24-extension-points-hooks-plugins-research.md` and inventory:

| Extension Point | How P27 uses it |
|---|---|
| `pre_llm_call` hook | Inject `society_id`, society charter summary, society-specific allowed_users |
| `post_llm_call` hook | Society-specific drift check (cross-society drift allowed if charter permits) |
| `pre_tool_call` hook | Society-scoped auth matrix + consent gate |
| `post_tool_call` hook | Society-specific DNR + audit publication |
| `transform_llm_output` hook | Society-specific forbidden pattern filter |
| `on_session_start` hook | Inject society state into session, register society-specific observers |
| `on_session_end` hook | Society audit finalization |
| `pre_gateway_dispatch` hook | Society → Discord channel routing decision |
| `pre_approval_request` / `post_approval_response` | Society-specific approval channel (Discord thread per society) |
| `subagent_stop` hook | Stop society-specific sub-agent loops |
| `transform_terminal_output` / `transform_tool_result` | Society-specific output sanitization |
| Config `discord:` section | Per-society `allowed_users`, `allowed_channels`, channel mappings |
| Config `model:` section | Per-society model routing (different model budget per Society tier) |
| Config `mcp_servers:` section | Per-society MCP tools (fine Societies get less, founders get full) |
| Config `cron:` section | Per-society rituals (e.g., nightly audit publication per Society) |
| Config `observability:` section | Per-society Prometheus port + log prefix |
| Config `hooks:` section | Per-society shell hook activations (e.g., finance_hook only on finance-Society) |
| Plugin system `register(ctx)` | Per-society custom plugins (`society_router`, `society_audit`, `society_consent`) |
| `plugin.yaml` / `manifest.yaml` | Per-society plugin manifest with hooks + commands + dependencies |
| MCP servers | Custom FastMCP per Society or shared FastMCP with society context |

### 8.2 Extensions P27 Should Plan But Need Fork Changes

| Desired Extension | Plan now? | Requires fork change |
|---|---|---|
| Per-Society HARD STOP with global propagator | YES (define semantics) | The `PersistentTaskRegistry` (§20) would need a `society_id` namespace argument |
| Per-Society 24/7 heartbeat declaration | YES | `on_startup(task_factory)` per Society — possible if each Society is a separate install. Single-VPS multi-Society needs additional fork logic |
| Society-aware `BaseSaver` (state persistence) | YES | Conceptually extends P24 §17 adapter pattern with society_id |
| Society-aware MCP tool namespace | YES (define naming convention) | Hermes MCP config supports this already via env vars; minor |

---
## 9. Risk Assessment: What If P24 Is Delayed

### 9.1 P24 Delay Scenarios

| Scenario | Probability (operator judgment) | Impact on P27 |
|---|---|---|
| P24 implementation never starts (decision reversal) | LOW (operator verdict is firm) | P27 must use upstream Hermes + adapter pattern per P24 research finding |
| P24 implementation delayed 1-3 months (P20 preflight + P19 namespace + P24-002 source check) | MEDIUM (3 explicit hold blockers) | P27 can define now; implementation waits for P24 |
| P24 implementation partial (fork repo created but no first patch) | MEDIUM | P27 can run as standalone Hermes install with same config dir isolation; no fork code needed |
| P24 implementation succeeds | CURRENT TARGET | P27 implementation can proceed in full |

### 9.2 Hybrid / Interim Paths for P27 if P24 Delayed

P27 CAN PROCEED with these interim strategies:

#### Interim A — Upstream Hermes + Adapter Pattern (Best Interim Path)

**Compatible with research consensus from P24:** 13/14 files conclude extension-only is feasible. P27 can build on this:

- Use upstream `hermes-agent>=0.15` from PyPI (NO fork).
- Society boundary = per-Society `hermes-config/` directory on shared OR separate VPS.
- Society plugins live in `hermes-config/plugins/society-{society_id}/` (per-society directory).
- Society routing via `pre_llm_call` hook that injects `society_id` based on Discord channel/user.
- Society HARD STOP via dedicated Redis key per society: `guinevere:society:{society_id}:hard_stop` + global cascade via pub/sub.
- Society heartbeat per society in APScheduler (P20 pattern, but inside fork bootstrap later).

**Caveat:** loses the "owned runtime" benefit. P27 documents this as interim and lists the fork migration path.

#### Interim B — Minimal Fork with Approved-Risk Waiver (Bridge Path)

If operator accepts-risk for fork creation without full lifecycle patch:

- Create empty fork repo, pin upstream.
- No internal patches yet.
- Use fork pin mechanism (`pyproject.toml` git+https@tag) but with vanilla upstream == upstream `v0.15.2`.
- This gives reproducibility without fork code.
- Society boundary = per-install venv + per-install `hermes-config/`.

#### Interim C — Fork Repo only (P24-005) without Patches

Implement fork repo creation only (P24-005 in plan). Stop before P24-006 (lifecycle patch). Societies each install same fork tag. No internal patches needed for Society boundary.

### 9.3 Recommendation for P27

**P27 should not block definitions on P24 implementation.** P27 definitional artifacts (§4) are independent of P24. Implementation should wait for P24 to enable fork-grade ownership; P27 interim paths are documented for risk mitigation.

Critical concern: **P24-006 `on_startup(task_factory)` hook for 24/7 heartbeat** is the only piece of fork code referenced by P20 (and indirectly by any always-on Society). If P24-006 never lands, P27 must design Society to be request-driven (no 24/7 mandate) OR inherit the existing APScheduler pattern from P20.

---

## 10. P24 → P27 Handoff Contract

P27 implementation must wait for these P24 deliverables before P28 (Society instance deployment) can begin.

### 10.1 Mandatory Handoff (P24 cannot ship P28 without)

| Contract Item | P24 wave | Validation | Hard-blocking? |
|---|---|---|---|
| Fork repo `github.com/fazulfim/hermes-agent` exists + private + MIT preserved + NOTICE | P24-005 | `git ls-remote` + LICENSE + NOTICE presence | YES |
| `pyproject.toml` supports `git+https@tag` pinning | P24-005 + P24-019 | `uv pip install` test on clean venv | YES |
| Tag `v0.15.2-guinevere.1-rc.1` released (canary) | P24-018 | Tag exists + reproducible install | YES |
| Canary isolated to `.venv-hermes-canary` + canary-only systemd unit | P24-018 | `.venv-hermes-canary` exists + unit file present | YES |
| Shared `.venv` promotion only after canary + drill | P24-019 | Promotion procedure documented + audit | YES (safety) |
| Parity test framework (100% upstream + 100% fork-specific + 100% Guinevere) | P24-009 | All test suites pass | YES |
| 24h soak P24-020 PASS (autonomy invariants + HARD STOP latency + 1s heartbeat) | P24-020 | Soak report shows zero invariant violations | YES |
| Rollback-to-upstream drill <5min verified | P24-019 | Drill evidence | YES |
| §0.1 invariant verification post-promotion (V-003 silence-continues, V-007 audit-not-approval-bottleneck, V-008 HARD STOP global halt) | P24-020 | Invariant test suite | YES |
| `on_startup(task_factory)` lifecycle hook proven to support persistent background tasks | P24-006 | Source inspection + 1s heartbeat test in soak | YES |

### 10.2 Soft Handoff (P27 can proceed without, but quality degrades)

| Contract Item | If absent, P27 mitigation |
|---|---|
| Per-society plugin namespace convention in fork | P27 uses prefix-based naming convention (`society_<id>_*`) in own plugins |
| Per-society HARD STOP namespace | P27 hand-rolls Redis pub/sub keyed by `society_id` |
| Per-society 24/7 guarantee via `on_startup` | P27 falls back to APScheduler pattern (same as P20 today) |
| Per-society fork branch support | P27 must run all Societies on same fork tag; OK for v1 |

### 10.3 Forbidden / Anti-Patterns P27 Must NOT Carry Forward

From P24 §9 + AGENTS.md §5 (anti-pattern catalog):

- ❌ No `.venv/site-packages` edit (direct Hermes install edit forbidden).
- ❌ No claiming "P27 fork done" without evidence + double audit + parent verification.
- ❌ No inline-only sub-agent outputs (all P27 deliverables must be file-based).
- ❌ No secrets/API keys in evidence files (secret scan clean required).
- ❌ No HARD STOP bypass (V-008 preservation across Societies is mandatory).
- ❌ No Y6 path (preserved across all Society instances).
- ❌ No consent revocation bypass.
- ❌ No skipping per-step implementation auditor gate.
- ❌ No silent scaffold violations.
- ❌ No per-action approval bottleneck (replace with §0.1 policy gates).
- ❌ No parallel Society install on shared `.venv` without canary-equivalent isolation.

---

## 11. Verification Scaffold for P27/P28 (Future Use)

P27/P28 should adopt the same per-step verification scaffold from P24 plan §43 + AGENTS.md §2.5. The P27 planner MUST include for each atomic step:

| Scaffold Field | Application to P27 |
|---|---|
| Expected Files | Exact paths for Society templates, charter docs, society_config.yaml, plugin manifests |
| Forbidden Patterns | Regex matching `as any`, empty catch, `.venv edits`, `HARD STOP bypass`, missing audit |
| Required Commands | `python -m pytest tests/`, `uv pip install --dry-run`, `hermes doctor`, secret scan, schema diff |
| Evidence Requirements | `verification.md` (12-section), `auditor-gate.md`, every step |
| Hard Rejection Criteria | Charter signers missing? Per-society isolation broken? HARD STOP latency >50ms? Audit journal unwritable? |

P24 §43 wave scaffold is the template; P27 waves should mirror this discipline.

---

## 12. Open Questions / Caveats for P27 Planner

### 12.1 Open Questions P27 Must Resolve Before P28

| Question | Decision owner | Impact on P27 design |
|---|---|---|
| Society boundary strength? (Hard VPS install vs Soft shared-vps per-society venv) | Faiz | Determines whether P27 needs fork-level per-Society patch |
| Per-Society HARD STOP global cascade or isolated? | Faiz + Guinevere | Determines fork semantics needed |
| Society Discord channel allocation? (one channel per Society? thread per Society?) | Faiz | Determines `discord:` config complexity |
| Society model budget? (same fork budget per install OR per-Society budget) | Faiz + FinOps | Determines `model:` config complexity |
| Society MCP tool set? (same as default OR per-Society MCP allowlist) | Faiz + Security | Determines MCP security review surface |
| Society identity persistence? (Discord username ↔ society membership mapping) | Faiz | Determines session routing logic |
| Society audit retention? (same as opaque? OR distinct retention policy) | Faiz + Compliance | Determines PostgreSQL schema design |
| Society fork delta divergence allowance? | Faiz | Determines whether fork branch strategy is single-branch or per-Society-branch |

### 12.2 Open Questions P24 Must Resolve First / In Parallel

| Question | P24 wave that resolves | P27 implication |
|---|---|---|
| Does Hermes v0.15.2 actually have an `on_startup(task_factory)` hook (or near-equivalent for persistent background tasks) | P24-002 source inspection | If YES: P27 multi-Society 24/7 guaranteed; If NO: P27 falls back to APScheduler |
| Is P19 namespace contract (`project_id` partition in memory/KG) runtime-proven | P19 implementation | P27 can piggyback on P19 pattern for `society_id` |

### 12.3 Caveats Specific to This Report

1. **This report is descriptive, not authoritative.** P24 docs are research/plan-stage. Treat as mapping aid, not contract.
2. **No P24 code/runtime was executed to verify these findings.** All conclusions are derived from file reads.
3. **The 13/14 research-vs-operator verdict split** is real and acknowledged by P24 §15.1. P27 must decide whether to design as-if-fork or design as-if-extension-only. The partial-vs-deferrable dependency map above allows both.
4. **P27 multi-Society architecture does NOT exist as yet.** This report multi-Society fork strategy is a recommendation, not a derived fact.
5. **P24-006 <200 LOC** is approximate. Actual patch size depends on P24-002 source inspection outcome.
6. **Mama round-3 audit findings are fixed in plan** but implementation has not begun.
7. **AGENTS.md §0.1 autonomy governance applies equally to P27.** Society-level autonomy must respect per-action-approval = bottleneck rule.

---
## 13. Summary Table

| Aspect | P27 Can Define Now? | P27 Can Implement Now? | Requires P24? |
|---|---|---|---|
| Society ID convention | YES | YES | NO |
| Society registry schema (SQL) | YES | YES | NO |
| Society charter format (MD) | YES | YES | NO |
| Governance model (HARD STOP global vs per-Society) | YES | YES (interim pub/sub) | YES for true fork implementation |
| Boundary type decision (hard/soft isolation) | YES | YES (depends on VPS topology) | NO |
| Society config template (`society_config.yaml`) | YES | YES | NO |
| Society plugin manifest template (`plugin.yaml`) | YES | YES | NO |
| Society Discord routing config | YES | YES | NO |
| Society cron rituals | YES | YES | NO |
| Society MCP tool namespace | YES | YES | NO |
| Society observability prefix (Prometheus + Loki) | YES | YES | NO |
| Society audit schema (PostgreSQL) | YES | YES | NO |
| Society consent schema (PostgreSQL) | YES | YES | NO |
| Society FORK install roadmap | YES | YES (multi-VPS first) | YES for fork-grade install |
| Society HARD STOP fork-grade semantics | YES (define) | NO | YES (needs P24-006 lifecycle patch) |
| Society 24/7 heartbeat (real-time persistence) | YES (define) | NO (interim APScheduler) | YES (needs P24-006 lifecycle patch) |
| Society parity test suite | YES (define contract) | NO | YES (needs P24-009 parity framework) |
| Per-Society fork branch divergence | NO (P24 does not design per-Society fork branching) | NO | YES (needs P24 plan amendment or new wave) |
| Society VPS rollback drill | YES (define runbook) | NO | YES (needs P24-019 rollback drill verified) |
| Society production 24h soak | NO | NO | YES (parent soak or Society-specific soak after P24-020) |

---

## 14. Forward Compatibility Checklist for P27 ↔ P24 Alignment

P27 planner must include in its master plan:

- [ ] Society boundary strength defined (hard-VPS / soft-shared-vps / fork-branch).
- [ ] Per-Society HARD STOP semantics defined (global cascade / per-Society isolated / both).
- [ ] Society ID format locked (UUID v7 OR slug+hash).
- [ ] Society charter format published.
- [ ] Society registry schema published (PostgreSQL).
- [ ] Society config template published.
- [ ] Society plugin manifest template published.
- [ ] Society MCP namespace convention published.
- [ ] Society observability prefix convention published.
- [ ] Society audit retention policy published.
- [ ] Society consent policy published (society-scoped + global cascade).
- [ ] Interim P27 paths documented (Interim A/B/C from §9.2).
- [ ] P24 implementation watchpoint list documented (which P24 waves must land before P28 begins).
- [ ] Per-step verification scaffold adopted (from P24 plan §43).
- [ ] Cross-Society isolation test plan documented.
- [ ] HARD STOP global-vs-per-society test plan documented.
- [ ] Rollback-to-upstream-drill test plan documented.

---

## 15. References

### P24 Source Files (all parent-read)

| File | Topic | Verdict Reference |
|---|---|---|
| `docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md` | Plan (44 sections + 20 waves) | §15 final verdict, §15.1 reconciliation |
| `docs/setup-evidence/P24/evidence/final-p24-planning-report.md` | Final report | Metrics + status |
| `docs/setup-evidence/P24/evidence/p24-definition-verification.md` | Definition verification | Acceptance criteria mapping |
| `docs/setup-evidence/P24/evidence/auditor-gate.md` | Auditor gate summary | Round 1 + 2 + plan-fix + mama round-3 |
| `docs/setup-evidence/P24/research/p24-hermes-upstream-identity-research.md` | Hermes upstream ID | Forkable, MIT, v0.15.2 |
| `docs/setup-evidence/P24/research/p24-no-fork-vs-hybrid-vs-full-fork-benchmark.md` | Benchmark | Recommends A; reconciled via §15.1 |
| `docs/setup-evidence/P24/research/p24-installed-runtime-surface-inventory.md` | Runtime surface inventory | 1 import, 7 adapters, 47 plugins, 12 hooks |
| `docs/setup-evidence/P24/research/p24-extension-points-hooks-plugins-research.md` | Extension points | ~40 total extension points |
| `docs/setup-evidence/P24/research/p24-memory-kg-persona-safety-convergence-research.md` | Memory/KG/persona/safety convergence | Hybrid; persona/safety native already |
| `docs/setup-evidence/P24/research/p24-p20-life-kernel-convergence-map.md` | P20 convergence | Extension sufficient for most; first heartbeat patch is fork trigger |
| `docs/setup-evidence/P24/research/p24-p19-p21-p22-p23-forward-compatibility-map.md` | Future-phase compatibility | NO-FORK forward-compatible; P23 only if wrapper fails |

### Project-Wide References

| Reference | Topic |
|---|---|
| `AGENTS.md §0.1` | P20 autonomy-first governance exception |
| `AGENTS.md §2.5` | Planner verification scaffold |
| `AGENTS.md §5` | Anti-pattern catalog |
| `adr/ADR-035-hermes-migration.md` | Hermes migration architecture (IMPLEMENTED status) |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Persona safety boundaries |
| `docs/30-data/30-DataGovernance_Classification_v1.0.md` | Data classification (Public/Internal/Restricted/Confidential/Critical) |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | Consent revocation policy |

---

## Footer

**Report Date:** 2026-06-28
**Report Author:** Buffy (codebase search specialist sub-agent for Guinevere)
**Report Status:** READY FOR P27 SYNTHESIS — DEPENDENCY MAP COMPLETE

**Verdict:** P27 is **partitionable**. Definitional artifacts (~70% of P27 scope) are independent of P24 implementation hold and can be specified now. Implementation artifacts (~30%, particularly 24/7 heartbeat, fork-grade HARD STOP, parity tests, rollback drill, VPS deploy verification) require P24-005 → P24-020 to complete first.

**Critical Path:**
1. P27 synthesis & planning uses this map to mark each artifact as **definitional** (no P24 block) vs **implementational** (P24 dependency).
2. P27 implementation start waits for at minimum: P24-005 fork repo + P24-006 lifecycle patch + P24-020 soak pass.
3. P27 interim paths (A: adapter pattern, B: minimal fork-no-patch, C: fork P24-005 only) provide risk mitigation.

**Next Action (caller side — P27 synthesis):**
- Read this map as input.
- Mark each P27 deliverable as definitional/implementational.
- Build P27 planner that includes interim path selection.
- Coordinate with P24 planner on multi-Society fork design decisions (boundary strength, HARD STOP semantics, per-Society fork branching).

**No secrets/intimate data exposed. No runtime code executed. All findings derived from file reads. Markdown aligned with AGENTS.md persona operating contract.**

— Buffy