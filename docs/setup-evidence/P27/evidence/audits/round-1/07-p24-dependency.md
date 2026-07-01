# Audit 07: P24 Dependency Map — Fork-Agnosticism Verification

**Auditor:** Buffy (P27 plan auditor)
**Date:** 2026-06-28
**Scope:** P27 plan §14 (L3175–3315), §16 (L3445–3570), §17 (L3572–3690); P28 blueprint §4 (L2028–2093); P24 dependency research file (first 100 lines)
**Verdict:** ✅ **PASS**

---

## Summary

P27 plan correctly maps P24 dependencies and explicitly maintains fork-agnosticism. P24 fork is documented as a **preferred optimization, not a prerequisite** throughout all audited sections. The ~70%/~30% definitional/implementational split, config-driven multi-instance interim path, extension-point inventory, single-instance refactor plan, and P24 handoff contract are all present, internally consistent, and correctly scoped. P28 blueprint §4 confirms P28 operates on the interim path (no fork required). P32 is correctly identified as the fork-integration phase.

---

## Findings

### F1. P27 Explicitly Fork-Agnostic — VERIFIED ✅

- **§14.3 L3206:** `"P27 is **fork-agnostic**"` — explicit statement.
- **§14.3 L3208–3209:** ~70% definitional (Society ontology, instance architecture schema, peer protocol envelope, 3-scope memory schema, 7-rail life-loop, 4-domain privacy split, dual-bot topology, identity anchors, anti-sycophancy mechanisms, audit/governance patterns, HARD STOP cascade) and ~30% implementational (native multi-instance inside Hermes gateway, hermes-lifecycle-persistent-tasks integration, hermes-gateway-cli multi-config mode — explicitly noted as P24-dependent but NOT implemented by P27).
- **No finding.** Correctly partitioned.

### F2. P24 Fork Preferred but NOT Blocking — VERIFIED ✅

- **§14.10 L3313:** `"P24 fork is a **preferred optimization**, not a prerequisite."`
- **§14.9 L3305–3309:** Five forbidden patterns explicitly block P24 as a dependency: P27 must NOT block on P24 fork, must NOT promise fork-based multi-instance to P28, must NOT skip Section 17 refactor even with fork available.
- **§14.8 L3294:** `"P28 minimum target does NOT require P24 fork."`
- **No finding.** Fork-agnosticism is enforced via forbidden patterns, not just stated.

### F3. ~70% / ~30% Split — VERIFIED ✅

- **§14.3 L3208:** "~70% definitional" with enumerated list of 11 definitional concerns.
- **§14.3 L3209:** "~30% implementational" with 3 implementational concerns, all correctly attributed to P24-dependency with explicit note: "**P27 does NOT implement them.**"
- **No finding.** Split is clear and correctly scoped.

### F4. Config-Driven Multi-Instance as Interim Path — VERIFIED ✅

- **§14.8 L3296–3300:** P28 operates on current hybrid adapter, per-instance config, per-instance HermesBrain via `agent_factory`, and ~40 extension points.
- **§14.8 L3301:** `"P32 implements native multi-Hermes via P24 fork. Until P32, P28+P29+P30+P31 implement per-instance via HermesBrainConfig + shadow/independent bot pattern."`
- **P28 §4.3 L2055–2066:** Module-level singletons refactored to per-instance factories. §4.4 L2068–2078: `app.state.hermes_brains: dict[str, HermesBrain]` with single-process single-instance default.
- **No finding.** Interim path is well-defined, and P32 handoff point is explicit.

### F5. HermesBrainConfig + agent_factory as Multi-Instance Seams — VERIFIED ✅

- **§16.3 L3483–3497:** `HermesBrainConfig` frozen dataclass with 5 fields. `"ONE config → ONE instance. Creating a second HermesBrainConfig with different model/provider/api_key creates a second brain. No source code changes required."`
- **§16.4 L3499–3508:** `agent_factory: Callable[[dict], Any] | None` injection point. `"The same signature accepts any AIAgent subclass/wrapper — multi-instance customization is a 1-line constructor change away."`
- **P28 §4.1 L2041–2043:** `HermesBrainConfig.from_yaml()` loads per-instance config. §4.2 L2045–2053: `agent_factory` injection used with `_default_agent_factory`; no source modification to `hermes_brain.py` required.
- **No finding.** Both seams are correctly identified and documented with concrete constructor signatures.

### F6. Single-Instance Anchors Identified — VERIFIED ✅

- **§14.7 L3270–3289:** 13 anchors enumerated with file paths, line numbers, and refactor targets:
  - **4 singletons:** `_memory_bridge`, `_cost_tracker`, `_embedding_service`, `_rate_limit_redis`
  - **2 constants:** `GUILD_ID`, `GUINEVERE_CHAT_CHANNEL_ID`
  - **1 brain on app.state:** `app.state.hermes_brain`
  - **6 additional:** `LoopManager`, `LoopGuardian`, `HardStopHandler`, Redis client, PostgreSQL checkpointer, `life_mind_graph`
- **§17.2 L3578–3614:** Full refactor inventory expands to 15+ anchors including `BackgroundCognition`, `DashboardWriter`, `DiscordRestClient`.
- **No finding.** Anchor inventory is comprehensive with exact source locations.

### F7. Refactor Plan for Single-Instance Anchors — VERIFIED ✅

- **§17.4 L3629–3652:** 18 refactor steps across 4 parallel phases (A–R), each with expected effort of 1 step.
- **§17.5 L3654–3662:** Each step has per-step verification scaffold (Expected Files, Forbidden Patterns, Required Commands, Evidence Requirements, Hard Rejection Criteria).
- **§17.6 L3664–3672:** Forbidden patterns for refactor (no global singletons, no hardcoded IDs, no type suppression, no empty catches).
- **No finding.** Refactor plan is implementable, phased, and scaffolded.

### F8. P24 Handoff Contract — VERIFIED ✅

- **§14.4 L3222–3235:** 10 handoff items explicitly enumerated:
  1. Owned fork repo
  2. MIT license + NOTICE
  3. `main` ↔ upstream `main` branch policy
  4. `guinevere` branch with fork additions
  5. Tags `v0.15.2-guinevere.N`
  6. Rollback tag `v0.15.2-upstream`
  7. `pyproject.toml` pin via `git+https@tag`
  8. `_lifecycle/persistent_tasks.py` (<200 LOC) for heartbeat
  9. `on_startup`/`on_shutdown` lifecycle hook
  10. Canary template `.venv-hermes-canary`
- Cross-referenced with research file §3 (L89–99): deliverables match 1:1.
- **No finding.** Contract is complete and aligned with P24 deliverables.

### F9. Extension Points Inventory (~40) — VERIFIED ✅

- **§16.1 L3447–3463:** ~40 extension points enumerated by category:
  - 9+ config sections
  - 17 lifecycle hook events
  - 12 shell hook scripts
  - 3 in-process plugin manifests
  - 2 MCP server registrations
  - 8 cron entries
  - 2 plugin manifest shapes
  - **Total: ~40**
- **§14.6 L3250–3263:** Same inventory cross-referenced with P28 use cases.
- **§16.7 L3535–3543:** Limitations documented (cannot add 18th hook without fork, cannot modify AIAgent constructor).
- **§16.9 L3554–3568:** "This is the **central reason** P27 can be defined now without P24 fork."
- **No finding.** Inventory is complete, categorized, and correctly linked to fork-agnosticism rationale.

### F10. P28 Does NOT Require P24 Fork — VERIFIED ✅

- **§14.8 L3294:** Explicit statement: `"P28 minimum target does NOT require P24 fork."`
- **§14.8 L3296–3300:** P28 operates on: current hybrid adapter, per-instance config, per-instance HermesBrain via agent_factory, ~40 extension points.
- **P28 §4 L2028–2093:** Full config-driven multi-instance architecture for P28 with no P24 fork reference. §4.6 L2086–2093 forbidden patterns include `"No modifying AIAgent constructor signature (Hermes upstream)"` — confirming upstream is used, not fork.
- **No finding.** P28 blueprint is fork-free.

### F11. P32 is the Fork Integration Phase — VERIFIED ✅

- **§14.8 L3301:** `"P32 implements native multi-Hermes via P24 fork. Until P32, P28+P29+P30+P31 implement per-instance via HermesBrainConfig + shadow/independent bot pattern."`
- **§14.10 L3313:** `"P32 implements native fork integration IF P24 fork is ready. If P24 fork is delayed beyond P32, the architecture remains functional with hybrid adapter + per-instance config."`
- **§17.3 L3627:** `systemd/hermes-society-supervisor@.service` marked as `"Optional supervisor pattern (P32+)"`.
- **No finding.** P32 handoff point is explicit, with graceful degradation if fork is delayed.

---

## Cross-File Consistency Check

| Checkpoint | P27 §14 | P27 §16 | P27 §17 | P28 §4 | Research File | Result |
|---|---|---|---|---|---|---|
| Fork-agnostic statement | L3206 ✅ | — | — | — | L62–67 ✅ | CONSISTENT |
| ~70/30 split | L3208–3209 ✅ | — | — | — | — | PRESENT |
| Extension points count | L3252–3263 | L3447–3463 ✅ | — | — | — | CONSISTENT (~40 both) |
| HermesBrainConfig seam | — | L3483–3497 ✅ | — | L2041–2043 ✅ | — | CONSISTENT |
| agent_factory seam | — | L3499–3508 ✅ | — | L2045–2053 ✅ | — | CONSISTENT |
| Single-instance anchors | L3270–3289 ✅ | — | L3578–3614 ✅ | L2055–2078 ✅ | — | CONSISTENT |
| P24 handoff contract | L3222–3235 ✅ | — | — | — | L89–99 ✅ | CONSISTENT (10 items) |
| P32 fork integration | L3301, L3313 ✅ | — | L3627 ✅ | — | — | CONSISTENT |
| P28 fork-free | L3294 ✅ | — | — | L2086–2093 ✅ | — | CONSISTENT |

---

## Recommendations

**None.** All 11 audit criteria pass. The plan is fork-agnostic by design, with clear forbidden-pattern enforcement, comprehensive extension-point inventory, concrete refactor plan, and explicit P32 handoff point. P28 blueprint independently confirms the fork-free interim path.

---

**Auditor:** Buffy
**Audit round:** 1
**Report:** `docs/setup-evidence/P27/evidence/audits/round-1/07-p24-dependency.md`
