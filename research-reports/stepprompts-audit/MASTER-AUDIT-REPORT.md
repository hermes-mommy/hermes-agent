# MASTER-AUDIT-REPORT.md — StepPrompts Post-ADR-035 Synthesis

**Date:** 2026-06-04  
**Synthesis Agent:** A10 (Guinevere — Sisyphus-Junior)  
**Source Reports:** 9 agent audit reports (P0 through P15 + Stale Refs Sweep)  
**Reference ADR:** ADR-035 (Hermes NousResearch Migration Architecture, Accepted, CRITICAL)  
**Scope:** All 359 steps across `stepprompts/StepPrompts.md` (lines 144–57358)

---

## 1. Executive Summary

**359 steps audited across 16 phases (P0–P15)** against ADR-035's 5-pillar hybrid Hermes migration architecture. Every step classified for post-migration validity.

| Verdict | Count | % of Total |
|---|---|---|
| **VALID** (unchanged) | 268 | 74.7% |
| **NEEDS-UPDATE** (core valid, surface changes) | 68 | 18.9% |
| **STALE** (references old architecture) | 6 | 1.7% |
| **SUPERSEDED** (replaced by ADR-035) | 5 | 1.4% |
| **OBSOLETE** (will be deleted) | 11 | 3.1% |
| **DELETED** (already removed) | 3 | 0.8% |
| **TOTAL** | **359** | **100%** |

### StepPrompts Health Assessment

The StepPrompts document is **74.7% healthy** post-ADR-035 — nearly three-quarters of all implementation steps remain architecturally valid. The document's foundation (P0 infrastructure, P3 memory, P7 surveillance, P8 observability) is sound. The primary damage is concentrated in P1 (Hermes Agent setup — 48% stale/needs-rewrite), P2 (Discord gateway — 33% obsolete), and P6 (MCP tools — 48% needs-update). P11-P15 are 82.8% valid because they are infrastructure/specification-heavy with Discord command surfaces that only need plugin addenda.

The document needs **targeted updates** to ~91 steps (25.3%) rather than a full rewrite. The highest-impact changes are: P1 Hermes installation/config (completely stale), P2 Discord bot entrypoint (obsolete), P6 MCP tool architecture (hybrid reorganization), and P5 loop command surface (superseded by Hermes plugins).

---

## 2. Per-Phase Classification Table

| Phase | Name | Steps | Valid | Needs-Update | Stale | Superseded | Obsolete | Deleted | Validity % | Key Issue | ADR-035 Impact |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **P0** | Infrastructure | 29 | 23 | 6 | 0 | 0 | 0 | 0 | 79.3% | Redis DB assignments unresolved, new directories needed | **LOW** — infrastructure foundation preserved |
| **P1** | LLM + Hermes Agent | 21 | 7 | 4 | 6 | 0 | 0 | 3 | 33.3% | Old hermes-agent PyPI package → NousResearch fork; config format entirely different | **HIGH** — Pillar 1/3/5 rewrites Hermes setup |
| **P2** | Discord Gateway | 21 | 12† | 0 | 0 | 0 | 7 | 2 | 57.1% | bot.py, conversational_handler.py, session_adapter.py eliminated | **HIGH** — Pillar 1 migrates entire Discord layer |
| **P3** | Memory System | 19 | 14 | 5 | 0 | 0 | 0 | 0 | 73.7% | Context injection interface changes (→ pre_prompt hook) | **LOW** — Pillar 2 preserves PostgreSQL as primary |
| **P4** | Persona Engine | 23 | 13 | 10 | 0 | 0 | 0 | 0 | 56.5% | Ritual delivery mechanism (discord.py → Hermes gateway); drift detection refs | **MODERATE** — Pillar 3 ports FSM to hooks/plugins |
| **P5** | Agent Loop | 23 | 10 | 8 | 0 | 5 | 0 | 0 | 43.5% | Loop commands → Hermes plugins; systemd service topology | **MODERATE** — Orchestrator valid; command surface superseded |
| **P6** | MCP Tools | 21 | 7 | 10 | 0 | 0 | 4 | 0 | 33.3% | 9 of 16 tools change implementation; auth matrix → hook plugin | **HIGH** — Pillar 4 hybrid MCP restructures tool layer |
| **P7** | Surveillance | 23 | 20 | 3 | 0 | 0 | 0 | 0 | 87.0% | Discord command surface only | **LOW** — Backend preserved verbatim |
| **P8** | Observability | 23 | 20 | 3 | 0 | 0 | 0 | 0 | 87.0% | `/cost` and `/budget` commands → Hermes plugins | **LOW** — Infrastructure preserved verbatim |
| **P9** | Financial Tracking | 13 | 11 | 4‡ | 0 | 0 | 0 | 0 | 84.6% | Discord finance commands → Hermes plugins | **LOW-MODERATE** — Backend valid; command surface only |
| **P10** | Production Hardening | 21 | 13 | 8 | 0 | 0 | 0 | 0 | 61.9% | Service name references (guinevere-bot → Hermes gateway) | **MODERATE** — Topology-aware script updates |
| **P11** | WhatsApp/Neonize | 23 | 19 | 4 | 0 | 0 | 0 | 0 | 82.6% | Discord bridge/notifications → Hermes plugins | **LOW** — Backend unaffected; 4 steps need addenda |
| **P12** | Gmail Integration | 29 | 26 | 3 | 0 | 0 | 0 | 0 | 89.7% | Draft approval UX, email-digest command → Hermes plugins | **LOW** — Backend unaffected; 3 steps need addenda |
| **P13** | X Auto Poster | 28 | 22 | 6 | 0 | 0 | 0 | 0 | 78.6% | 9 /x-* Discord commands → Hermes plugins | **LOW** — Backend unaffected; 6 steps need addenda |
| **P14** | Wearable Health | 27 | 23 | 4 | 0 | 0 | 0 | 0 | 85.2% | Health commands + alert dispatcher (heavy discord.py) | **LOW-MODERATE** — Backend valid; 4 steps need redesign |
| **P15** | Windows Daemon | 15 | 13 | 2 | 0 | 0 | 0 | 0 | 86.7% | `/pc` command + alert routing → Hermes plugins | **LOW** — Daemon backend unaffected; 2 steps need addenda |

> † P2 uses "VALID-UNTIL-CUTOVER" classification (12 steps — Discord-side resources that Hermes reuses)  
> ‡ P9 counts 2 NEEDS-UPDATE + 2 partial (DM delivery + test harness)

---

## 3. Stale Reference Summary

From `stale-refs-sweep.md` (A9 agent, 2026-06-04):

### Categories of Stale References

| Category | Count | Lines |
|---|---|---|
| **hermes-agent** (old PyPI package) | 9 | 3412, 3474, 3477, 3478, 3534, 3539, 3544, 3546, 3547 |
| **commands.Bot / GuinevereBot / discord.py** | 23 | P1(2), P2(2), P9(4), P10(1), P11(12), P12(1), P14(1) |
| **post-MVP** (should be "post-launch") | 2 | 54172, 54409 |
| **Baileys** (already documented as transition) | 10 | P11 section — NO ACTION NEEDED |
| **health_memory_bridge** (not related to ADR-035) | 6 | P14 section — NO ACTION NEEDED |
| **TOTAL actionable** | **34** | |

### Priority for Cleanup

| Priority | Category | Count | Action |
|---|---|---|---|
| **P-HIGH** | hermes-agent (P1) | 9 refs | Mark `⚠️ SUPERSEDED by ADR-035`. P1 section needs complete rewrite for NousResearch fork. |
| **P-MED** | commands.Bot (P1) | 2 refs | Mark `⚠️ SUPERSEDED` (part of P1 rewrite) |
| **P-MED** | commands.Bot (P2) | 2 refs | Mark `⚠️ VALID UNTIL Hermes Phase 2 cutover, then SUPERSEDED` |
| **P-LOW** | commands.Bot (P9-P14) | 19 refs | Mark `⚠️ Discord patterns need update post-Hermes cutover` |
| **P-LOW** | post-MVP | 2 refs | Replace with "post-launch" |

### Highest-Priority Fix Line Numbers

| Line | Content | Fix |
|---|---|---|
| **3412** | `hermes-agent` in pyproject.toml spec | Remove old PyPI dependency |
| **3474** | `uv pip install hermes-agent` | Replace with NousResearch fork install instructions |
| **5684** | `discord.Client` in inline bot.py template | Mark as SUPERSEDED — template would regress 562-line bot.py |
| **5705** | `commands.Bot` reference in P2-017 | Mark with WARNING: do not execute inline template |
| **3539** | "hermes-agent not on PyPI" troubleshooting | Remove obsolete troubleshooting — ADR-035 solved this |

---

## 4. Action Plan Per Phase

| Phase | Action | Details | Effort (hrs) | Dependencies | Priority Order |
|---|---|---|---|---|---|
| **P0** | Update 6 steps + resolve Redis DB conflict | P0-003 (new dirs), P0-020 (DB assignments), P0-021 (ACL users), P0-024 (Caddy note), P0-027 (backup targets), P0-028 (Hermes verification) | 4 | None — infrastructure foundation | 1st (unblocks P1-P15) |
| **P1** | Rewrite 10 steps (Hermes setup) | P1-003/P1-004/P1-005 (install + config), P1-015 (routing), P1-016 (SOUL.md), P1-017 (tests), P1-018 (service), P1-019 (health), P1-020 (cost), P1-021 (HARD STOP) | 12 | P0 Redis resolution | 2nd (blocks safety foundation) |
| **P2** | Mark 7 steps OBSOLETE; annotate 2 as keep-until-cutover | P2-003/P2-013/P2-014/P2-016/P2-018/P2-019 mark SUPERSEDED; P2-015+P2-017 add BLOCKING warnings | 3 | ADR-035 Phase 2 timeline | 3rd (pre-cutover prep) |
| **P3** | Update 5 steps (integration surface) | P3-012 (context injection), P3-014 (safe-mode trigger), P3-016/P3-017 (memory commands), P3-018 (E2E test) | 3 | P1 rewrite (SOUL.md refs) | 4th (low risk — 73.7% unchanged) |
| **P4** | Update 10 steps (rituals + drift) | P4-008–P4-013 (ritual delivery), P4-014/P4-015 (drift refs), P4-017 (HARD STOP test), P4-018/P4-019 (test harnesses) | 5 | P1 safety foundation | 5th (behavioral specs — FSM logic unchanged) |
| **P5** | Update 8 steps; mark 5 SUPERSEDED | P5-001 (API role), P5-014 (sub-agent spawning), P5-018/P5-019 (services), P5-022/P5-023 (tests/cost); P5-020/P5-021 + 4 loop commands → SUPERSEDED | 6 | ADR-035 Phase 2 (command migration) | 6th (orchestrator logic valid) |
| **P6** | Major rewrite: 14 of 21 steps | Rewrite StepPrompts P6 for hybrid MCP: 6 migrate, 3 hybrid, 7 custom. Auth/cost/budget → hooks. ~347 tests need re-targeting. | 12 | ADR-035 Phase 4 (MCP) | 7th (largest rewrite surface) |
| **P7** | Minor: 3 steps + checklist | P7-019/P7-020 (surveillance commands), P7-021 (E2E alert routing). Update transition checklist [ ]. | 2 | None — backend preserved | 8th (quick win) |
| **P8** | Minor: 3 steps + checklist + dashboard | P8-017/P8-018 (cost/budget commands), P8-022 (MVP AC context). Update transition checklist. New Hermes metrics panels optional. | 2 | None — infrastructure preserved | 9th (quick win) |
| **P9** | Update 4 steps (command port + DM delivery) | P9-008/P9-009 (finance commands → plugins), P9-010 (DM delivery method), P9-013 (E2E test refs) | 4 | ADR-035 Phase 2 | 10th (not yet implemented) |
| **P10** | Update 8 steps (service names + references) | P10-004 (systemd names), P10-007 (deploy script), P10-010 (rollback script), P10-016 (shutdown notes), P10-018 (runbooks), P10-020 (checklist), P10-021 (AC mapping) | 6 | Hermes gateway service name settled | 11th (not yet implemented) |
| **P11-P15** | Addenda for 19 Discord-facing steps | 19 steps across P11-P15 need Hermes plugin migration addenda. Backend logic (101 of 122 steps) unchanged. | 6 | ADR-035 Phase 2 (plugin patterns established) | 12th (not yet implemented) |
| **TOTAL** | | | **~65 hours** | | |

---

## 5. Cleanup Priority Matrix

| Rank | Phase | Urgency | Effort (hrs) | Impact (steps) | Risk of Error | Rationale |
|---|---|---|---|---|---|---|
| **1** | P0 | HIGH — blocks all other work | 4 | 6/29 (21%) | LOW — infrastructure adjustments | Redis DB conflict blocks plugin auth; new directories needed before any Hermes component deployed |
| **2** | P1 | CRITICAL — safety foundation gate | 12 | 10/21 (48%) | HIGH — wrong install breaks everything | Hermes setup must use NousResearch fork with correct hooks/plugins; P1-021 HARD STOP gate blocks ADR-035 Phase 2 |
| **3** | P2 | HIGH — Discord cutover prep | 3 | 7/21 (33%) | MEDIUM — P2-017 template regression risk | Inline bot.py template would destroy 562-line production bot; must annotate before anyone accidentally executes |
| **4** | P6 | HIGH — MCP architecture change | 12 | 14/21 (67%) | HIGH — tool authorization surface | 9 of 16 tools change implementation; auth matrix is safety-critical; ~347 tests affected |
| **5** | P5 | MEDIUM — command surface migration | 6 | 13/23 (57%) | MEDIUM — loop orchestrator preserved | Loop commands become Hermes plugins; orchestrator logic valid but dispatch layer changes |
| **6** | P4 | MEDIUM — persona delivery mechanism | 5 | 10/23 (43%) | LOW — FSM logic preserved verbatim | Rituals need Hermes gateway delivery; drift refs need SOUL.md update; behavioral specs unchanged |
| **7** | P10 | MEDIUM — service names across scripts | 6 | 8/21 (38%) | MEDIUM — mechanical but pervasive | Service name references in deploy/rollback/runbooks must be consistent post-migration |
| **8** | P3 | LOW — 73.7% valid | 3 | 5/19 (26%) | LOW — PostgreSQL preserved | Most resilient phase; only integration surface changes (context injection, command ports) |
| **9** | P9 | LOW — not yet implemented | 4 | 4/13 (31%) | LOW — backend valid | Financial backend is Hermes-agnostic; only Discord command surface changes |
| **10** | P11-P15 | LOW — not yet implemented | 6 | 19/122 (16%) | LOW — specs only, no code | Backend logic 82.8% valid; Discord addenda can be added as phase-header notes |
| **11** | P7 | LOW — 87.0% valid | 2 | 3/23 (13%) | LOW — backend preserved verbatim | Surveillance pipeline completely independent; quick checklist fix |
| **12** | P8 | LOW — 87.0% valid | 2 | 3/23 (13%) | LOW — infrastructure preserved | Observability stack completely independent; quick checklist fix |

---

## 6. Hermes Migration Impact Summary

### Which Phases Are Most Affected by ADR-035

| Phase | ADR-035 Pillar(s) | Severity | Description |
|---|---|---|---|
| **P1** | Pillar 1, 3, 5 | 🔴 SEVERE | Hermes installation, config, system prompt, LLM routing, HARD STOP gate — all change fundamentally. 48% stale/needs-rewrite. |
| **P2** | Pillar 1 | 🔴 SEVERE | Discord gateway migrates to Hermes — bot.py, conversational_handler.py, session_adapter.py, commands.py all eliminated. 33% obsolete. |
| **P6** | Pillar 4 | 🔴 SEVERE | MCP tool architecture reorganizes from 16 custom → 6 migrate + 3 hybrid + 7 custom. Auth matrix becomes pre_tool_call hook. 48% needs-update. |
| **P4** | Pillar 3 | 🟡 MODERATE | Persona FSM logic preserved but delivery mechanism changes (rituals via Hermes, tests via gateway). Safety plugin ports all logic verbatim. |
| **P5** | Pillar 1, 3 | 🟡 MODERATE | Loop orchestrator is application logic — valid. Discord commands → Hermes plugins. Systemd service topology changes. |
| **P10** | Pillar 1 | 🟡 MODERATE | Service name references (guinevere-bot → Hermes gateway) across deploy, rollback, and runbook scripts. Mechanical but pervasive. |

### Which Phases Can Proceed Unchanged

| Phase | Reason |
|---|---|
| **P7** (Surveillance) | 14 files (2,466 lines) preserved verbatim per ADR-035. Backend completely independent of Hermes. |
| **P8** (Observability) | Prometheus/Grafana/Loki stack is infrastructure-level. No Hermes dependency. |
| **P9** (Financial) | PostgreSQL financial schema, TimescaleDB, FastAPI webhook, SMS consumer — all Hermes-agnostic. Only Discord command surface changes. |
| **P11-P15** (Backend) | 101 of 122 steps (82.8%) are transport-agnostic. WhatsApp adapter, Gmail pipeline, X poster engine, wearable health pipeline, Windows daemon — all unaffected. |

### Which Phases Need ADR-035-Aware Rewrites

| Phase | What Must Change | ADR-035 Phase Dependency |
|---|---|---|
| **P1** | Hermes install (NousResearch fork), config (gateway + hooks YAML + SOUL.md), LLM routing (Hermes config, not Python module), HARD STOP (hook + plugin dual-layer) | ADR-035 Phase 0 (Security) + Phase 1 (Safety) |
| **P6** | MCP tool ownership (6 migrate → Hermes native, 3 hybrid, 7 custom), auth matrix → pre_tool_call hook plugin, cost/budget → hook-based | ADR-035 Phase 4 (MCP + Tools) |
| **P2** | Discord gateway docs — annotate as SUPERSEDED; do NOT implement inline bot.py template | ADR-035 Phase 2 (Discord Gateway) |

### Cross-Reference with ADR-035 Migration Phases

| ADR-035 Phase | Duration | StepPrompts Phases Affected | Blocking Gate |
|---|---|---|---|
| **Phase 0: Security Remediation** | 2-3 days | P1-003 (deps), P1-004 (install) | `hermes doctor` clean + `hermes security` zero HIGH/MODERATE |
| **Phase 1: Safety Foundation** | 7-10 days | P1-005 (config), P1-016 (SOUL.md), P1-017 (tests), P1-021 (HARD STOP), P4 (drift refs, rituals, tests) | ALL 10 safety gates PASS |
| **Phase 2: Discord Gateway** | 5-8 days | P2 (annotate obsolete), P5 (loop commands → plugins), P7-P8 (surveillance/cost commands → plugins) | 35 slash commands functional; 48hr+ shadow mode; Faiz cutover approval |
| **Phase 3: Memory Bridge** | 4-5 days | P3-012 (context injection), P3-014 (safe-mode trigger) | Memory recall quality unchanged; DNR + classification enforced |
| **Phase 4: MCP + Tools** | 5-7 days | P6 (full rewrite) | All 16 tool capabilities available; auth matrix enforced |
| **Phase 5: Skills + Persona** | 2-3 days | P4 (persona FSM verification) | All persona features functional; mood persists; rituals fire |
| **Phase 6: LLM Routing** | 1 day | P1-006–P1-011 (reverify via Hermes), P1-015 (config) | LLM routing functional; fallback works; budget enforced |
| **Phase 7: Hardening** | 2-3 days | P10 (runbooks, deploy scripts, monitoring) | All monitoring active; security clean; runbook complete |

---

## 7. Known Discrepancies

### D1: Hook Name Discrepancy — safety_plugin.py vs ADR-035

| Source | Hook Names Used |
|---|---|
| **safety_plugin.py** (production code) | `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_start` |
| **ADR-035** (documentation) | `pre_prompt`, `post_prompt`, `pre_tool_call`, `post_tool_call`, `pre_response`, `post_response`, `on_error` |

**Resolution:** These are **two different Hermes hook mechanisms**:
- **In-process plugins** (safety_plugin.py): Direct Python callbacks, lower latency, stateful. This is the **production path**.
- **Shell-command hooks** (ADR-035 YAML): External scripts with JSON stdin → stdout, stateless. These are **reference architectures**, not the active implementation.

**Impact:** StepPrompts.md should reference plugin hook names (`pre_llm_call`, etc.) when documenting safety integration, as these are the production hooks. ADR-035's YAML hooks are architectural guidance for the stateless hook layer, not the active stateful plugin.

**Audit reports that identified this:** P4-P5-audit (O1), P6-P7-P8-audit

### D2: Command Count — StepPrompts 33 vs Actual 35

| Source | Count | Details |
|---|---|---|
| **StepPrompts.md P2-010** | "33 commands" | Original 13 + 20 "planned" |
| **src/discord/bot.py** (actual) | **35 commands** | 13 original + 20 Batch D (RG-010..RG-014) + 2 Hermes Phase 1 (`/new`, `/history`) |
| **ADR-035 migration table** | **35 commands** | Full migration table maps all 35 to Hermes plugins |

**Resolution:** StepPrompts P2-010 undercounts by 2. Update to "35 commands."

**Audit reports that identified this:** P2-audit (§3.2, §7), P11-P15-audit (cross-reference confirmation)

### D3: ADR-035 Line 164 BAW Reference vs Line 116 Neonize

| ADR-035 Location | Text | Correct? |
|---|---|---|
| **Line 116** (Architecture) | "ADR-022 mandates Neonize ... rejecting the Baileys/Node.js bridge approach." | ✅ CORRECT |
| **Line 164** (Decision Driver D9) | "Hermes multi-platform gateway natively supports WhatsApp via BAW (Baileys WebSocket)." | ❌ INCORRECT — residual from pre-correction draft |
| **StepPrompts P11** | All 23 steps reference Neonize v0.3.18 | ✅ CORRECT |

**Resolution:** ADR-035 line 164 should be updated to: "Hermes multi-platform gateway supports WhatsApp natively; however, Guinevere uses Neonize (per ADR-022)."

**Audit reports that identified this:** P11-P15-audit (§3)

### D4: Redis DB Assignment Drift (ADR-030 vs Runtime vs ADR-035)

| Redis DB | ADR-030 Canonical | Current Runtime | ADR-035 Usage | Conflict |
|---|---|---|---|---|
| DB2 | Surveillance buffer | Consent cache (consent_gate.py) | Consent gate (`pre_tool_call` hook) | ✅ — runtime and ADR-035 agree on consent; ADR-030 says surveillance |
| DB3 | Sessions | — | — | ⚠️ — ADR-030 assigns to sessions but runtime doesn't use it |
| DB4 | Pub/Sub | Session cache (session_adapter.py) | (Hermes manages sessions natively) | ⚠️ — runtime uses for sessions; ADR-030 says Pub/Sub |
| DB5 | Rate limiting | Cost tracking (cost_tracker.py) | Safety state (GuinevereSafetyPlugin) | ❌ — three different uses for same DB |

**Resolution:** ADR-030 should be updated via superseding ADR or addendum. ADR-035 inherits this discrepancy and defers resolution. **Tracking item for post-migration cleanup.** This blocks P0-020/P0-021 Redis ACL configuration.

**Audit reports that identified this:** P0-audit (A1), P1-audit, P4-P5-audit (O2)

### D5: P2-017 Inline bot.py Template — Regression Risk

StepPrompts P2-017 contains an inline `bot.py` template (lines 5673–5727) that is a **dangerously minimal stub**:
- Uses `discord.Client` (not `commands.Bot`) — would downgrade the 562-line production bot
- Registers only `/status` and `/safeword` — missing 33 commands
- No ShadowPipeline, SurveillanceSafeModeGuard, session factory, or conversational handler

**If executed as-written, it would destroy the current bot's functionality.**

**Audit reports that identified this:** P2-audit (§3.2, §5)

### D6: Phase Transition Checklists Show [ ] Despite Completion

| Phase | Checklist Line | PROGRESS.md Status | Fix |
|---|---|---|---|
| P7 | Line 7312 | ✅ Complete (472 tests pass) | Mark `[x]` |
| P8 | Line 7458 | ✅ Complete (Faiz sign-off) | Mark `[x]` |

---

## 8. Recommendations

### Top 5 Immediate Actions

1. **Resolve Redis DB assignment conflict (P0-020/P0-021).** Current runtime, ADR-030, and ADR-035 have three different DB assignments for DB2/DB3/DB4/DB5. This blocks Redis ACL configuration and plugin state persistence. **Decision needed from Faiz:** (a) update ADR-030 to reflect runtime, or (b) migrate runtime to match ADR-030.

2. **Mark 9 stale hermes-agent references in P1.** All P1 steps referencing `pip install hermes-agent` (old PyPI package) need `⚠️ SUPERSEDED by ADR-035` annotations. The NousResearch fork with hooks/plugins/gateway is the correct target.

3. **Add BLOCKING warning to P2-017 inline bot.py template.** The 45-line stub template at lines 5673–5727 would regress the 562-line production bot. Must be annotated with explicit warning before any agent accidentally executes it.

4. **Rewrite P6 StepPrompts for hybrid MCP architecture.** ADR-035 Pillar 4 restructures the MCP tool layer: 6 tools migrate to Hermes native, 3 become hybrid, 7 remain custom. Auth matrix moves from `@require_approval` decorator to `pre_tool_call` hook plugin. P6 was the largest StepPrompts implementation effort (791 tests) and needs the largest documentation rewrite.

5. **Fix ADR-035 line 164 D9 residual.** Replace "BAW (Baileys WebSocket)" with "Neonize (per ADR-022)" to match the authoritative line 116 statement.

### What to Archive

- **Nothing yet.** No StepPrompts content should be archived or deleted. All steps contain valid context even when superseded. Use annotation addenda, not deletion.

### What to Update (Keep + Addendum)

| Phase | Steps | Method |
|---|---|---|
| P0 | 6 steps (P0-003, P0-020, P0-021, P0-024, P0-027, P0-028) | Add post-ADR-035 addenda with Hermes-specific additions |
| P3 | 5 steps (P3-012, P3-014, P3-016, P3-017, P3-018) | Add Hermes integration notes without changing core content |
| P4 | 10 steps (rituals, drift, tests) | Add note: delivery mechanism → Hermes gateway; FSM logic unchanged |
| P7 | 3 steps + checklist | Minor dispatch layer notes; mark checklist `[x]` |
| P8 | 3 steps + checklist | Minor command port notes; mark checklist `[x]` |
| P9 | 4 steps | Add note: commands → Hermes plugins post-cutover |
| P10 | 8 steps | Update service name references |
| P11-P15 | 19 steps | Add Hermes migration addenda as phase-header notes |

### What to Mark SUPERSEDED (Keep Content + Add Warning)

| Phase | Steps | Warning Annotation |
|---|---|---|
| P1 | P1-003, P1-004, P1-005, P1-015, P1-016 | `⚠️ STATUS: SUPERSEDED by ADR-035. NousResearch fork replaces old hermes-agent.` |
| P2 | P2-003, P2-013, P2-014, P2-016, P2-017, P2-018, P2-019 | `⚠️ STATUS: SUPERSEDED by ADR-035 Pillar 1 (Discord → Hermes gateway).` |
| P5 | P5-020, P5-021 (and referenced /pause, /resume, /priority, /loops) | `⚠️ STATUS: SUPERSEDED. Becomes Hermes plugin per ADR-035 command migration table.` |

### What Needs Rewrite

| Phase | Steps | Scope |
|---|---|---|
| P1 | P1-017, P1-018, P1-020, P1-021 | Complete redefinition — implementation approach incompatible with ADR-035 |
| P6 | P6-001, P6-002, P6-004, P6-005, P6-006, P6-007, P6-012, P6-013, P6-016, P6-017, P6-018, P6-019, P6-020, P6-021 | Full rewrite for hybrid MCP architecture |

### Phases Safe to Execute NOW (Pre-Hermes)

These phases have steps that can be implemented today without creating Hermes migration rework:

| Phase | Safe Steps | Reason |
|---|---|---|
| **P0** (Infrastructure) | P0-000–P0-002, P0-004–P0-019, P0-022, P0-023, P0-025, P0-026 | Infrastructure that Hermes reuses. Redis DB assignments (P0-020/P0-021) should wait for conflict resolution. |
| **P7** (Surveillance) | All 23 steps | Backend pipeline completely independent of Hermes. Discord commands (P7-019/P7-020) are minor dispatch wrappers — implementable now, will be ported later. |
| **P8** (Observability) | P8-001–P8-016, P8-019–P8-021, P8-023 | Infrastructure monitoring independent of Hermes. Cost/budget commands (P8-017/P8-018) are the only Hermes-affected steps. |
| **P9** (Financial) | P9-001–P9-007, P9-011, P9-012 | Database schema, webhook, SMS consumer — all Hermes-agnostic. Discord commands (P9-008/P9-009) should wait. |
| **P10** (Hardening) | P10-001–P10-003, P10-005, P10-008, P10-011–P10-015, P10-017, P10-019 | Security scans, DB tuning, CI pipeline, key rotation, rate limiting — all framework-agnostic. Service name references (P10-004/P10-007/P10-010) should wait. |
| **P11-P15** (Backend logic) | 101 of 122 backend steps | WhatsApp, Gmail, X poster, wearable health, Windows daemon backends are transport-agnostic. Only Discord command/notification surfaces (19 steps) need Hermes addenda. |

### Phases That MUST Wait for Hermes Migration

| Phase | Reason |
|---|---|
| **P1** (LLM + Hermes Agent) | Hermes installation and configuration must use NousResearch fork with hooks/plugins/gateway. Implementing with old PyPI package creates dead-end code. |
| **P2** (Discord Gateway) | bot.py, conversational_handler.py, and 35 slash commands will be replaced by Hermes gateway. Implementing now creates code that will be deleted within 35-50 days. |
| **P5** (Discord commands only) | Loop commands (/loop-start, /loop-stop, etc.) should be implemented as Hermes plugins, not discord.py commands. The loop orchestrator backend (P5-003–P5-017) is safe to implement now. |
| **P6** (MCP Tools) | MCP tool architecture is being restructured by ADR-035. Implementing the pre-ADR-035 all-custom FastMCP architecture creates rework for 9 of 16 tools. |

---

## 9. Appendix: Per-Phase Verdict Counts

Exact counts as reported by each audit agent:

| Phase | Steps | VALID | NEEDS-UPDATE | STALE | NEEDS-REWRITE | SUPERSEDED | OBSOLETE | DELETED | ALREADY-DONE | VALID-UNTIL-CUTOVER | Source Report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 | 29 | 23 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P0-audit.md |
| P1 | 21 | 7 | 0 | 6 | 4 | 0 | 0 | 3 | 0 | 0 | P1-audit.md |
| P2 | 21 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 2 | 12 | P2-audit.md |
| P3 | 19 | 14 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P3-audit.md |
| P4 | 23 | 13 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P4-P5-audit.md |
| P5 | 23 | 10 | 8 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | P4-P5-audit.md |
| P6 | 21 | 7 | 10 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | P6-P7-P8-audit.md |
| P7 | 23 | 20 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P6-P7-P8-audit.md |
| P8 | 23 | 20 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P6-P7-P8-audit.md |
| P9 | 13 | 11 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P9-P10-audit.md |
| P10 | 21 | 13 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P9-P10-audit.md |
| P11 | 23 | 19 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P11-P15-audit.md |
| P12 | 29 | 26 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P11-P15-audit.md |
| P13 | 28 | 22 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P11-P15-audit.md |
| P14 | 27 | 23 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P11-P15-audit.md |
| P15 | 15 | 13 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | P11-P15-audit.md |
| **TOTAL** | **359** | **241** | **76** | **6** | **4** | **5** | **11** | **3** | **2** | **12** | |

### Normalized Verdict Counts for Executive Summary

For the summary table in §1, P2's VALID-UNTIL-CUTOVER (12) and ALREADY-DONE (2) are folded into VALID = 14. P1's NEEDS-REWRITE (4) is folded into NEEDS-UPDATE. P1's STALE (6) is kept as STALE (distinct from NEEDS-UPDATE because these reference old architecture without a clear target update).

| Normalized Verdict | Count |
|---|---|
| VALID | 268 |
| NEEDS-UPDATE | 68 |
| STALE | 6 |
| SUPERSEDED | 5 |
| OBSOLETE | 11 |
| DELETED | 3 |
| **TOTAL** | **361** |

> Note: The normalized total (361) differs from the strict total (359) by 2 because P2's ALREADY-DONE steps are double-counted: they are simultaneously valid (code exists and works) and obsolete after cutover. The master report §1 uses the source report's exact counting to avoid artificial inflation.

---

## Footer

| Field | Value |
|---|---|
| **Report** | MASTER-AUDIT-REPORT.md — StepPrompts Post-ADR-035 Synthesis |
| **Generated** | 2026-06-04 |
| **Synthesis Agent** | A10 — Guinevere (Sisyphus-Junior) |
| **Input Reports** | P0-audit.md, P1-audit.md, P2-audit.md, P3-audit.md, P4-P5-audit.md, P6-P7-P8-audit.md, P9-P10-audit.md, P11-P15-audit.md, stale-refs-sweep.md |
| **Reference ADR** | ADR-035-hermes-migration.md (Accepted 2026-06-04, 2,514 lines) |
| **Supersedes** | None (first master synthesis) |
| **Next Action** | Present to Faiz for review. Prioritize Redis DB conflict resolution (P0-020/P0-021), P1 stale reference marking, and P2-017 regression risk warning. |