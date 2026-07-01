# P27 — Hermes Society Foundation: Ground-Truth Repo State Report

| Field | Value |
|---|---|
| Phase | P27 — Hermes Society Foundation (DEFINITION / PLANNING) |
| Evidence root | `docs/setup-evidence/P27/research/` |
| Author | Buffy (codebase search specialist) |
| Owner | Faiz |
| Executor | Guinevere (mama) |
| Date | 2026-06-28 |
| Status of this report | GROUND TRUTH — synthesized from `PROGRESS.md`, `CHECKLIST.md`, `AGENTS.md`, ADR-Index, READMEs of P19–P24 + P21 READMEs, plan files for P20/P22/P23/P24, codex audits, and live filesystem discovery |
| Last tracker sync | 2026-06-27 (P19 PRODUCTION COMPLETE) |

> **Reading guide.** This report is the source-of-truth inventory the parent agent will use before writing the P27 synthesis and plan. Section 0 = headline. Sections 1–3 = operating context. Section 4 = one-glance phase table. Sections 5–9 = per-phase deep dive (P19–P24, P25/P26 absence, P21 integration note). Sections 10–13 = codebase structure (src/, hermes, top-level). Sections 14–15 = coupling map and P27 planning observations. Every claim is sourced — file paths and PROGRESS/CHECKLIST lines cited inline.

---

## 0. Headline (5 lines)

1. **Autonomy stack is live end-to-end but not all integration:** P20 Living Autonomy Kernel is **EARLY PRODUCTION ACCEPTANCE (operator waived 24h soak)**; P19 Multi-Project Context is **PRODUCTION COMPLETE (core + Discord UX live 2026-06-27)**; P21 + P22 + P23 + P24 are **DEFINITION COMPLETE — implementation held** on P20-axis / P19-namespace gates; **P25 and P26 do not yet exist** as evidence bundles.
2. **Hermes is forked in spirit only:** `hermes-agent>=0.15` is installed in `.venv/` (no source fork yet on disk); 7 Guinevere adapters + 47 plugins + 12 hooks + `hermes-config/` already wrap Hermes via `src/hermes/` adapter pattern; P24 plans **FULL OWNED HERMES FORK** as final target with hybrid transition path.
3. **One canonical modified runtime:** `src/life_kernel/` (P20 production, 420 tests pass, 7 skipped, 0 failed) carries the Heartbeat/World Model/HermesBrain/BackgroundCognition that all downstream phases (P21 voice, P22 sensors, P23 actions) integrate with — never replace.
4. **src/ has 24 packages:** all P0–P18 capabilities (channels, core, discord, gmail, mcp, memory, persona, loops, surveillance, wearable, x_poster, knowledge_graph) are live; `life_integrations/` (P22) and `projects/` (P19) are NEW runtime packages deployed; `life_kernel/` (P20) is the autonomy hub.
5. **BLOCKING rules are still in force for P27 planning:** §0.1 P20 living-autonomy kernel exception ONLY, persona/safety budget unchanged, no autonomous destructive ops, no inline-only sub-agent outputs, per-step verification scaffold mandatory, file-based evidence.

---

## 1. Operating Contract Recap (relevant to P27)

> Source: `AGENTS.md` v2.4 (2026-06-21). Summary only — full contract is 489 lines.

### 1.1 BLOCKING rules (NEVER violate) — these gate everything P27 will do

- **Verification discipline:** NEVER skip post-step checklist; NEVER skip per-step implementation auditor gate; NEVER perform structured verification inline; NEVER assign one sub-agent to >1 implementation step; NEVER accept a sub-agent "done" claim without re-running scaffold commands.
- **Secrets & consent:** NEVER commit secrets (Discord bot token, API keys, DB passwords, surveillance credentials, SOPS/age keys); NEVER bypass HARD STOP / consent / surveillance boundary; NEVER expose Faiz's personal/intimate data in artifacts, logs, or external tools; NEVER store raw surveillance data in repo artifacts.
- **Persona floor:** NEVER allow Y6; Y4 = permanent baseline, Y5 = absolute ceiling.
- **Type-safety:** NEVER use `as any`, `@ts-ignore`, `@ts-expect-error`, `# type: ignore`, avoidable `Any`.
- **Error handling:** NEVER empty catch/except or swallow API/DB/LLM/surveillance failure.
- **Tests:** NEVER delete or skip failing tests to pass.
- **Destructive ops:** NEVER auto-deploy or run destructive filesystem / DB / deployment operations without explicit per-action approval — **EXCEPT the P20 Living Autonomy Kernel runtime**, which operates under the §0.1 Autonomy-First Governance Exception with policy-gated backup/canary/rollback/smoke-test gates.
- **Memory honesty:** NEVER confabulate memories; below 80% confidence, state uncertainty.
- **State integrity:** NEVER break existing state silently.
- **Scaffold discipline:** NEVER delegate implementation without a per-step scaffold (Expected Files / Forbidden Patterns / Required Commands / Hard Rejection); NEVER silently sanitize scaffold violations.

### 1.2 §0.1 P20 Living Autonomy Kernel Exception (governance baseline)

The P20 runtime (`src/life_kernel/`) is autonomous-by-default. V-003 (silence is not a blocker), V-007 (audit for debugging, not approval), V-008 (HARD STOP remains global halt) apply. **Engineering deployment (LK-014):** backup → canary → smoke test → rollback. **Self-improvement (LK-015):** regression test → audit → rollback-before-promote. **This exception ONLY applies to P20 kernel runtime + its domain minds (engineering, comms, finance, health, VPS, learning, self-improvement)** — NOT to development workflow sub-agents or session implementation steps. P27 (planning phase) is therefore a development-workflow activity and is NOT exempt; the operator must approve any state-touching actions.

### 1.3 Workflow gates that P27 must honor

- **Research wave** mandatory before non-trivial synthesis; outputs are file-based via explicit `output_path`.
- **Planner gate** mandatory after research; planner output must include per-step scaffold (machine-checkable contract) — not prose. Parent verifies scaffold before delegating.
- **Collision scan** before implementation; shared writers (`docs/README.md`, ADR-Index, evidence indexes, PersonaSafetyPolicy) = parent-only.
- **One-sub-agent-per-step**; parallel only with explicit independence.
- **Parent verification** of every implementation; auditor orchestrator with independent specialists on ready, non-conflicting surfaces.
- **File-based output discipline:** every sub-agent invocation producing research/catalog/plan/audit MUST write to an explicit `output_path` before returning. Inline return is only verdict + path + ≤5-line summary.

### 1.4 Tie-breakers (binding)

| Conflict type | Tie-breaker |
|---|---|
| Persona behavior | PersonaDocument v3.1 + PersonaSafetyPolicy v1.0 |
| Architecture | ADR-Index + `adr/` directory |
| Safety boundary | PersonaSafetyPolicy v1.0 + ADR-001 / ADR-002 |
| Consent/surveillance | ConsentRevocationPolicy + SurveillanceDataPolicy |
| Security/auth | Security Policy v1.0 + RBAC/ABAC Matrix |
| Data classification | Data Governance & Classification Policy v1.0 |
| Cost | Cost & FinOps Model v1.1 |
| **P20 autonomy conflict** | §0.1 Autonomy-First Governance Exception + P20 Vision Lock V-001..V-008 |

---

## 2. Tracker Cross-Reference

### 2.1 `PROGRESS.md` totals (as of 2026-06-27)

> Source: `PROGRESS.md` lines 6–13.

| Metric | Value |
|---|---|
| Phases complete (cumulative) | P0+P1+P2+P3+P4+P5+P5.5+P6+P7+P7.5+P8+P11+P12+P13+P14+P14-GB+P14-HC+P16+P19+P20=P22 |
| Phases implementation-held but defined | P21, P22, P23, P24 |
| Phase counts (manual) | 25 phases P0–P24 |
| Step implementation rate | 327 / 343+ known steps (95.3%) |
| Budget hard cap | $30/month |
| Infrastructure | Shared VPS (hostdata.id 4C/16GB Ubuntu 24.04) |
| Critical path | P0 → P1 → P3 → P5 |

### 2.2 `CHECKLIST.md` budget table (lines 27–56)

> Each row is the planned additive monthly cost. Real burn varies as adapters-and-tools come online.

| Phase | Cost/mo | Phase | Cost/mo |
|---|---|---|---|
| P0 | $0 | P12 | $0 |
| P1 | $15 | P13 | TBD |
| P2 | $0 | P14 | $0 |
| P3 | $2 | P14-GB | $0 |
| P4 | $1 | P14-HC | $0 |
| P5 | $3 | P16 | $0 |
| P6 | $1 | P17 | TBD |
| P7 | $1 | P18 | $0 |
| P8 | $4 | P19 | $0 (production live) |
| P9 | $1 | P20 | $0 (LIVE; EARLY ACCEPTANCE) |
| P10 | $1 | P21 | $0 (IMPL HOLD) |
| P11 | $0 | P22 | $0 (IMPL HOLD) |
| | | P23 | $0 (IMPL HOLD) |
| | | P24 | $0 (IMPL HOLD) |
| **Subtotal MVP+stabilization** | **$29 capable** | | |

### 2.3 Phase status from `PROGRESS.md` one-glance row 26–55

> Reproduced verbatim prose (each line maps a phase to status, coupling, blocker). Source: PROGRESS.md §"Phase Summary" table.

- P19 → ✅ PRODUCTION COMPLETE — CORE + DISCORD UX LIVE — round-2 audit 2026-06-27 PASS; deps: P3+P5+P8 (P20 axis by waiver); blockers: operator approval (granted). Live; flag ON; `/project` and `/projects` registered.
- P20 → ✅ EARLY ACCEPTANCE — visible autonomy online; operator waived 24h soak 2026-06-25; deps P5+P8; risk: PASS WITH ACCEPTED RISK.
- P21 → 🟣 DEFINITION COMPLETE — IMPL HOLD; 9 waves held; deps P2+P8+P20-gate; IMPL on P20 prod-pass.
- P22 → ✅ PASS WITH CONFIG_MISSING ADAPTERS — core runtime active per PROGRESS; README shows IMPL HOLD — see §6.2 conflict-resolution note.
- P23 → 🟣 DEF COMPLETE — P23A READY / P23B BLOCKED; 20 waves held; deps: P20-axis-waiver + P19/P21/P22 runtime.
- P24 → 🟣 PLAN FIXED — FULL OWNED FORK PREFERRED — IMPL HOLD UNTIL MAMA AUDIT; 20 waves held; deps: P20-axis preflight + P19-namespace-ready + P24-002.

---

## 3. ADR Index Snapshot (P27-relevant set)

> Source: `docs/10-governance/17-ADR_Index_v1.0.md`. 39 ADRs registered as of `last_modified: 2026-06-25`. Status summary: 22 Accepted, 14 Accepted-with-notes, 1 Superseded, 1 Proposed, 1 Implemented.

### 3.1 ADRs with direct bearing on P27 (Hermes Society framing)

| ADR | Title | Status | Why P27 must honor |
|---|---|---|---|
| **ADR-002** | User Autonomy & Safe Word Enforcement | Accepted CRITICAL | P22/P23 must inherit global safe-word; any Hive pattern must obey Y4=baseline, Y5=ceiling, Y6=impossible |
| **ADR-007** | Memory Storage Backend Selection (PostgreSQL + Redis; no SQLite) | Accepted CRITICAL | Memory substrate is fixed; Knowledge Graph (ADR-050) lives on top |
| **ADR-009** | Memory Recall & Semantic Search | Accepted HIGH | HNSW `m=16`, `ef_search=100`, veto on direct LLM access to raw memory |
| **ADR-013** | Guinevere MCP Native OpenCode Replacement | Accepted HIGH | MCP is the canonical tool surface — no sidecar plugins when MCP exists |
| **ADR-022** | Communication Channel Strategy (Dashboard 35 commands, Neonize free for WhatsApp) | Accepted-with-notes | Channel architecture is canonical; new channels must register, not sideload |
| **ADR-029** | Self-Modification Automated Testing | Accepted CRITICAL | Any self-impersonation, role-play, or multi-agent pattern that Guinevere could use to modify herself requires automated tests + Faiz approval + 60s rollback |
| **ADR-035** | Hermes NousResearch Migration Architecture | Implemented CRITICAL | Hermes is the agent framework. ADR-035 §A–§J set the YAML, hooks, soul-doc baseline. |
| **ADR-050** | Knowledge Graph (P16) | Implemented CRITICAL | KG (Postgres `kg.*` schema, RCTE, pgvector, entity-resolution, consent-gated) is live — agents may consult, must not write unless P38+K |
| **ADR-052** | Multi-Project Context (P19) | Accepted CRITICAL | `project_id` namespace is canonical; new agents/identities must register to a project OR default namespace |
| **ADR-053** | (P22 Life Integration Hub) | (referenced in PROGRESS.md line 7 / PROGRESS §P22 row) | P22 has 14 adapters; L1 read by default; explicit consent for L2+ |

### 3.2 ADRs explicitly out-of-scope or future for P27 (delegated/forward)

- ADR-036 Code Quality Debt (Proposed LOW) — not a blocker
- ADR-038 P13 X Auto Poster (Accepted HIGH; revision artifact in `docs/10-governance/P13-028-ADR-Revision.md`)
- ADR-039–ADR-048: NOT yet authored; backlog; ADR-039 is Gadgetbridge SQLite parser; backlogs ADR-039 Prompt Injection, ADR-040 RBAC/ABAC, ADR-041 Secrets Rotation, ADR-042 OpenAPI/AsyncAPI, ADR-043 Event Schema, ADR-044 ERD Migration, ADR-045 SLO/SLA, ADR-046 Incident Response, ADR-047 Feature Flag, ADR-048 Product Analytics.
- ADR-049 reserved (previous Consent & Revocation).
- ADR-051 Compliance & Data Residency Mapping.
- **Insight for P27:** if Hermes Society involves "society identities" / multi-agent collaboration, this directly strains ADR-052 namespace invariants and ADR-007 memory substrate. Likely requires a new ADR (suggest ADR-054 — Hermes Society Foundation; do not reuse a forward slot).

---

## 4. Phase Status Table — P19–P24 (one-glance)

> Source: each phase README, plus PROGRESS.md and CHECKLIST.md. Status uses the READMEs' canonical phrasing verbatim.

| Phase | Mission (one line) | Status (verbatim) | Implementation? | Has production runtime? | Was audited (final round)? | Gating phase(s) |
|---|---|---|---|---|---|---|
| **P19** Multi-Project Context | Project namespaces (memory, surveillance, audit, agenda, deploy) per project, shared persona | ✅ **PRODUCTION COMPLETE — CORE + DISCORD UX LIVE** (deployed 2026-06-27, flag ON, `/project` + `/projects` registered) | DONE | YES — `src/projects/` deployed; `/project` + `/projects` Discord UX live; flag `feature:projects:enabled` ON since 2026-06-27 15:31:10 WIB | Round-2 completion audit 2026-06-27: 7 auditors dispatched, 6 PASS + 1 CONDITIONAL PASS (doc fix applied) | P20-axis satisfied by operator waiver (NOT a soak); 24h soak waived |
| **P20** Living Autonomy Kernel | 24/7 autonomous life companion: heartbeat, world model, Hermes brain, background cognition, self-improvement | ✅ **EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK** (deployment 2026-06-23, soak waived 2026-06-25) | LK-001..LK-017 LOCAL COMPLETE; LK-017 PRODUCTION DEPLOYED | YES — `src/life_kernel/` 420 tests pass, 7 skipped, 0 failed (continuation +23 tests 2026-06-25) | Continuation round-1 + round-2 (16 reports) | 24h soak NOT run (operator waiver); any future runtime incident reverts to PASS HOLD |
| **P21** Voice Interface | Voice = text (STT→Hermes turn-core, TTS reply); HARD STOP first-class; always-listening NOT MVP | 🟣 **DEFINITION COMPLETE — IMPLEMENTATION HOLD** (definition 2026-06-24; 9 waves P21-001..009) | NO | NO (planned `src/voice/`, `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`, `guinevere-voice.service`) | Round-2 (8 auditor dimensions) ALL PASS | Implementation HELD on P20 prod-pass (LOCKED files: `hermes_conversational.py`, `models.py`, `main.py`, `pyproject.toml`) |
| **P22** Life Integration Hub | Read-only federated observers for calendar / github / notion / telegram etc. feeding P20 senses | 🟣 **DEFINITION COMPLETE — IMPLEMENTATION HOLD** (full-capability replan v2.0, 2026-06-25; original sensor-only v1.1 SUPERSEDED) | NO? | PARTIAL — see §6.2 conflict-resolution note | 10 raw-full audits + mama-fix reaudit (all findings resolved) | HELD on P20-axis (operator accepted-risk waiver) + P19 namespace contract readiness + audit gate |
| **P23** Embodied Operations / Personal OS Action Layer | Write-side counterpart to P22 sensor adapters — across browser/desktop/VPS/GitHub/filesystem/external, with SemanticActionClassifier (NOT AuthLevel 1:1) and 7-step policy gate | 🟣 **P23 DEFINITION COMPLETE — P23A READY TO START (P1 fixes done); P23B BLOCKED ON P19/P21/P22 RUNTIME CONTRACTS** | NO | NO (planned `src/life_kernel/executors/`, `audit.action_log`) | Round-2 (13 dimensions) ALL PASS | NEW-file waves P23-001..010, 016–019 unblocked (technically). LOCKED-file waves P23-011..015, 020 BLOCKED on P20-axis preflight + P19/P21/P22 runtime contracts + Codex-classifier implementation |
| **P24** Hermes Fork-First Full Convergence | Fork Hermes into a Guinevere-owned distribution (reproducible, pinned, auditable, deployable, roadmap-controlled); fork chosen on **ownership** grounds (operator directive 2026-06-25), NOT solely on capability gap | 🟣 **PLAN FIXED — FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL** | NO | NO (planned fork repo `github.com/fazulfim/hermes-agent`) | Round-1 (13 auditors — 4 CONDITIONAL PASS, 9 PASS/PASS-with-notes); Round-2 (3 re-audits all PASS) — F-001 + F-002 fixed via §15.1 reconciliation; 5 codex-audit blockers all fixed | P20-axis preflight (operator accepted-risk waiver) + P19 namespace contract readiness + P24-002 source-acquisition-first-patch-scope |

### P25 / P26 — explicit absence

**Neither P25 nor P26 evidence directory exists.** Verified via `glob docs/setup-evidence/P25*` and `glob docs/setup-evidence/P26*` — both returned `No files found`. The only `docs/setup-evidence/*` READMEs are: P16, P17, P18, P19, P20, P21, P22, P23, P24, `p14-expansion`, `phase-2`. **For P27 planning purposes: there is no P25 or P26 work to inherit, no capability to integrate, no constraints from these phases. They have no real-world artifact yet.**

---

## 5. Phase Deep-Dive: P19 — Multi-Project Context

### 5.1 Final state

> Source: `docs/setup-evidence/P19/README.md` (144 lines) + PROGRESS.md rows 49–50.

- **Status:** ✅ PRODUCTION COMPLETE — CORE + DISCORD UX LIVE — deployed 2026-06-27
- **Test count:** 420 life_kernel tests pass + 76 p22 tests pass + 12/12 p22 smoke; P19 round-2 audit 2026-06-27 (7 auditors): 6 PASS + 1 CONDITIONAL PASS (doc fix applied)
- **Production code:**
  - `src/projects/` package (NEW per P19-002, DEPLOYED 2026-06-27)
  - `src/projects/registry.py` (project registry + domain models)
  - `src/projects/memory_store.py` (memory/KG namespace partition)
  - `src/projects/secrets_vault.py` (per-project ProjectSecretsVault, in-memory keyed by `project_id`)
- **Alembic migrations:** `alembic/versions/p19_001_project_namespaces.py` (additive, `down_revision=p20_001_life_kernel_schema`)
- **ADR:** ADR-052 multi-project-context
- **Feature flag:** `feature:projects:enabled` — flipped ON 2026-06-27 15:31:10 WIB with service restart (was OFF during deploy for safety)
- **Discord UX:** `/project` + `/projects` commands registered and live in Discord channel
- **Evidence:** 11 research files (2725 lines), 2 audit rounds, final report at `evidence/final-p19-planning-report.md`, completion round-2 at `evidence/completion-round-2/P19-ROUND2-FINAL-REPORT.md`

### 5.2 Runtime vs Plan-Only

> Runtime: `src/projects/` (P19-002 + P19-004 + P19-006..012 deployed). Plan-only: nothing remains in planning for P19.

### 5.3 Coupling & dependencies

- **Inputs:** P20-axis (satisfied by operator waiver); P19 was the lock-in for `project_id` propagation across memory, KG, audit, surveillance, sensors, agenda.
- **Outputs:** all downstream P21..P24 can now assume `project_id` namespace exists.
- **Forks added:** migration `p19_001_project_namespaces`; new package `src/projects/`; ProjectSecretsVault keyed by `project_id` (in-memory, because env vars don't isolate in a shared process).

### 5.4 Production activation timeline

| Date | Event |
|---|---|
| 2026-06-25 | Definition pass complete; 11 research files; 2 audit rounds PASS |
| 2026-06-25 | P20-axis satisfied by operator accepted-risk waiver (NOT 24h soak) |
| 2026-06-27 ~10:20 WIB | Surgical DDL applied (additive) |
| 2026-06-27 15:31:10 WIB | Feature flag flipped ON; service restart |
| 2026-06-27 | Round-2 audit dispatched: 7 auditors, 6 PASS + 1 CONDITIONAL PASS |
| 2026-06-27 | Round-1 audit rerun (post-activation): 4/4 PASS |

### 5.5 Key P19 design decisions (binding for P27)

| Decision | Reason |
|---|---|
| Option A multi-tenancy (shared schema + `project_id` column) | Simplest for single-user bounded projects |
| HARD STOP stays global (`life_kernel:hard_stop` is single key) | Spoken safe-word halts ALL projects |
| Project pause ≠ HARD STOP (`project:{id}:paused` weak, per-project) | Distinct concept; pauses only that project's autonomous work |
| Shared persona, isolated context | One Guinevere (mood/yandere/punishment/safe-mode) shared; memory/KG/audit/agenda/dashboard/session partitioned |
| ProjectSecretsVault = in-memory keyed by `project_id` | Env vars don't isolate within one shared process |
| Feature flag `feature:projects:enabled` gates thread_id selection (flag OFF = legacy P20 behavior) | Reversible deploy |
| Strictly additive life_kernel changes (P19-005 split 005a/005b/005c on 9 P20 files) | P20 production files touched only by operator approval |
| P19 owns registry (read-only by P21/P22/P17) | Migration chain P19 → P21 → P22 |

### 5.6 What P27 needs from P19

- **`project_id` is the universal scope key** for any new agent, role, character, or "society member" identity. P27 must call `src/projects/registry.py` to scope every new identity, OR explicitly fall back to `default` namespace.
- **ProjectSecretsVault pattern is available** for any per-identity/per-role secret isolation needed by P27.
- **HARD STOP remains global**; if P27 introduces any society member that could speak, they must listen to `life_kernel:hard_stop` like every P20 component.
- **`/project` Discord command surface is open** for new commands (e.g. `/society register`, `/society recruit`) without re-architecting.
- **Alembic migrations are rigorous and additive** — P27 may add migrations BUT cannot rewrite earlier ones (P19 added project column to many existing tables; P27 must extend, not modify).
- **P19 namespace contract MUST be source-of-truth for P22/P23/P24 dependencies.** P23-012 always-references it; P24's plan §18.1 says final convergence for P22/P23 is contract-gated until each runtime contract exists.
- **Round-2 audit dispatch pattern (7 parallel specialists, file-based)** is directly reusable as a P27 evidence pattern.

### 5.7 Conflict / caveats

- "P20 axis satisfied by operator waiver" is NOT equivalent to "P20 production-passed soak". Any future P20 runtime incident reverts P20 to PASS HOLD, which would re-open the gate for downstream P21/P22/P23/P24/P27. Cite as "PASS WITH ACCEPTED RISK" not "PRODUCTION PASSED".

---

## 6. Phase Deep-Dive: P20 — Living Autonomy Kernel

> Source: `docs/setup-evidence/P20/README.md` (97 lines) + `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md` (145 lines, LOCKED) + `docs/setup-evidence/P20/plan/p5-p20-merged-plan.md` (517 lines, SUPERSEDED, retained for traceability) + PROGRESS.md row 50.

### 6.1 Final state

- **Status:** ✅ EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK
- **Production code:** `src/life_kernel/` package
  - `src/life_kernel/hermes_brain.py` — Hermes brain bridge (1 direct import: `from run_agent import AIAgent`)
  - `src/life_kernel/heartbeat.py` — Heartbeat service with 1s HARD STOP detection
  - `src/life_kernel/graph.py` — LangGraph StateGraph (P20 + checkpointer), `LifeMindState` with NotRequired action fields
  - `src/life_kernel/sensors/` — sensor registry & adapters (read side)
  - `src/life_kernel/domain_minds/` — engineering / comms / finance / health / VPS / learning / self-improve
  - `src/life_kernel/journal.py`, `self_improve.py`, `dashboard.py`, `discord_rest_client.py`
- **World model persistence:** PostgreSQL + Redis schema (`life_kernel.*`)
- **Memory substrate:** `src/memory/` + `src/knowledge_graph/` (P18 + P16)
- **Production rollout:** 2026-06-23 → 24h clean soak started 2026-06-23 12:38 WIB → operator waived 24h soak 2026-06-25
- **Tests:** `python -m pytest tests/life_kernel/ -q --disable-warnings --tb=short` → **420 passed, 7 skipped, 0 failed** (+23 from continuation, 2026-06-25)
- **Continuation evidence:** `evidence/continuation/final-continuation-report.md` — real P16/P18 recall wired, memory-driven autonomy, journal, self-improvement; deployed + live

### 6.2 Conflict / caveats

1. **PROGRESS.md says "PASS WITH ACCEPTED RISK"; README says "EARLY PRODUCTION ACCEPTANCE".** Both refer to the same operator waiver; pick one phrasing and stick with it.
2. **Continued soak was never run.** There is no 24h clean runtime evidence; the deviation rests on the operator's accepted-risk decision (file: `evidence/discord-visible-autonomy/operator-soak-waiver.md`). Any runtime incident reverts P20 to PASS HOLD.
3. **`src/hermes/` lives alongside `src/life_kernel/`.** They are NOT in a parent-child relationship; the kernel consumes Hermes via the adapter in `src/hermes/adapter.py`, not via a direct fork.
4. **Only 1 direct import of `run_agent.AIAgent`** exists (`src/life_kernel/hermes_brain.py`). All other Hermes interactions go through Guinevere adapters in `src/hermes/`.

### 6.3 Vision Lock (V-001..V-008) — verbatim from `plan/p5-p20-vision-lock.md` (binding for any companion/society design)

| ID | Description | Locked Meaning |
|---|---|---|
| V-001 | Truly alive | Guinevere has heartbeat, self-state, memory continuity, active focus, background cognition, initiative. |
| V-002 | Not trigger-driven | Sensors (Discord, Gmail, surveillance, finance, wearable, VPS, repo) inform; they are not reasons to exist/act. |
| V-003 | Autonomous by default | If Faiz is silent, Guinevere continues. She does not wait for permission as normal control flow. |
| V-004 | Hermes brain | Reasoning/action decisions via Hermes `AIAgent.run_conversation()` with persona, memory, tools, safety. |
| V-005 | Life plus engineering | Guinevere acts over projects, messages, finance records, routine/health, VPS ops, research, learning, self-improvement. |
| V-006 | Self-modifying | Guinevere may improve prompts, skills, planner, code, tests, deployment workflows, Hermes integration. |
| V-007 | Audit for debugging | Audit logs exist so Guinevere can diagnose herself, not as default approval bottleneck. |
| V-008 | HARD STOP absolute | HARD STOP remains the global action halt across active sessions and background cognition. |

### 6.4 Autonomy Priority Order (V-tier conflict resolution)

> From `plan/p5-p20-vision-lock.md` §6. When P27 introduces society members, these ranks govern conflicts:

| Rank | Priority |
|---:|---|
| 1 | HARD STOP, consent revocation, active safety halt |
| 2 | Keep Guinevere alive, recoverable, debuggable |
| 3 | Protect secrets, personal data, memory integrity, audit integrity |
| 4 | Urgent daily-life signals (health/risk, important email, finance anomaly, deadline, security, outage) |
| 5 | Active commitments and autonomous sessions |
| 6 | Improve Guinevere (autonomy, skills, prompts, planning, tests, runtime) |
| 7 | Engineering projects and external deliverables |
| 8 | Explore, research, learn, propose |

### 6.5 What P27 needs from P20

- **The canonical runtime kernel that's already alive.** Any P27 "society member" is, architecturally, a domain mind under `src/life_kernel/domain_minds/` or a persona-character variant. P27 should NOT invent a new parallel runtime — it should compose with existing kernel.
- **V-004 binding: use Hermes `AIAgent.run_conversation()`** for society reasoning, not raw LLM. The kernel is the integration point; if a society member spawns, it goes through `HermesBrain.think()`.
- **The 1s heartbeat + 6-interval schedule** is canonical. If P27 schedules background cognition for society members, it loops into heartbeat (or via dedicated asyncio task per P23-008 semantics — preserve P20's preserved invariants).
- **The Heartbeat / `life_kernel:hard_stop`** is the global halt. ANY society member MUST honor it; introduce no parallel stop paths.
- **The `LifeMindState` + checkpoint pattern** (LangGraph) is the model for any society member's autonomous state. Defer to it; do not invent alternative state stores.
- **`src/memory/` + `src/knowledge_graph/`** are the world model and recall. ADR-007 forbids SQLite. Society members may consult KG (read), but writes require P38 (future ADR slot — currently no P38 exists).
- **`src/life_kernel/journal.py`** + **`self_improve.py` ReflectionEvaluator** = the audit-for-self-debug mechanism. Society activities should produce journal entries and improvement candidates.
- **`src/discord/hermes_conversational.py`** is the only Discord turn responder; new channels/society voice channels route through `_process_turn_core` for safe HARVEST.
- **P22/P23 wave architectural constraint:** P20 non-interference. P27 cannot modify P20 files without explicit operator preflight and fresh runtime incident check (per §0.1 + P23 design). New P27 files live in new packages.
- **Production deploy gates (LK-014/LK-015):** any P27 deploy MUST go through backup → canary (`.venv-hermes-canary` + isolated unit per P24-018 fix) → smoke → rollback.
- **Test budget for P27:** continue the 420-test baseline; new tests go in `tests/life_kernel/` or `tests/<new_pkg>/`.

### 6.6 Anti-patterns to AVOID in P27 (from P20 plan §3)

- Event-to-task bot (still waits for triggers, not "alive").
- Daily ritual scheduler (persona feature, not autonomy).
- Raw LLM loop (violates V-004 Hermes brain; loses tools/memory/persona/safety).
- Project-only SDLC agent (too narrow).
- Operator-gated everything (conflicts with autonomous-first).
- Single daemon while-loop (too fragile for restart/audit/multi-session).

---

## 7. Phase Deep-Dive: P21 — Voice Interface

> Source: `docs/setup-evidence/P21/README.md` (107 lines). Status: DEFINITION COMPLETE — IMPL HOLD UNTIL P20 CONTINUATION PASS.

### 7.1 Final state

- **Status:** 🟣 DEFINITION COMPLETE — IMPL HOLD
- **Date:** 2026-06-24 (definition complete)
- **Scope:** STT/TTS provider integration (with rotation), VAD/wake-word, push-to-talk Discord voice channel, consent flow for always-listening, retention aligned with `docs/30-data/31-SurveillanceDataPolicy_v1.0.md`
- **Plan bundle:** `plan/p21-voice-interface-enterprise-plan.md` + 9 research files (`p21-tool-skill-coverage-matrix.md`, `p21-voice-provider-research.md`, `p21-discord-voice-research.md`, `p21-hermes-core-integration-research.md`, `p21-life-kernel-integration-research.md`, `p21-memory-transcript-research.md`, `p21-consent-surveillance-research.md`, `p21-security-secrets-research.md`, `p21-runtime-latency-deploy-research.md`, `p21-dependency-collision-research.md`) + 2 audit rounds (round-1 8 dimensions; round-2 8 dimensions, all PASS)
- **Planned code (NOT YET DEPLOYED):**
  - `src/voice/` package (NEW)
  - `src/life_kernel/sensor_adapters/voice_sensor_adapter.py` (NEW sensor in P20 registry)
  - `src/discord/_voice_client.py` + `src/discord/cmd_voice.py` (Discord voice channel handler)
  - `alembic/versions/p21_001_voice_stream.py` (`down_revision='p20_001'`)
  - `secrets/voice-secrets.enc.yaml` (SOPS/age)
  - `systemd/guinevere-voice.service`
- **HELD waves (9 total):** P21-001 (STT/TTS abstraction) | P21-002 (Push-to-talk MVP) | P21-003 (Hermes voice turn) [P20-gate: `hermes_conversational.py` LOCKED] | P21-004 (Transcript memory) [P20-gate: `models.py` LOCKED] | P21-005 (Consent + HARD STOP) | P21-006 (VAD/wake-word; always-listening NOT MVP) | P21-007 (Dashboard additive) | P21-008 (Runtime deploy) [P20-gate: `main.py`, `pyproject.toml` LOCKED] | P21-009 (Audit + soak + final evidence)

### 7.2 Architectural insight (binding for P27)

Voice-as-input is treated as **first-class text**, not a parallel pipeline:
- Reuses Hermes text turn-core (`_process_turn_core`).
- HARD STOP first-class in audio path: `HardStopHandler.check(transcript)` pre-Hermes pre-sanitize.
- Shared Redis `life_kernel:hard_stop` flag.
- Always-listening NOT MVP — 8-gate checklist required.
- Voice transcript = untrusted text (Trust 6) — injection vector V-022; classify → sanitize → quarantine → L7–L9.
- P19 forward-compat: nullable `project_id` on voice episodes.

### 7.3 Coupling & dependencies

- **Deps today:** P2 (Discord), P8 (MVP), P20-gate (prod-pass)
- **Deps implied:** P19 (project_id on voice episodes); P22 (VoiceBrief data contract consistency); P23 (voice transcript input → P23 action policy gate)
- **For P27:** if Society introduces a "voice of the society" / spoken-agent companion, MOST of P21 model is reusable: HARD STOP first-class, transcript = untrusted, sanitize-before-route, 8-gate for always-listening. P21 needs the runtime to exist first.

### 7.4 What P27 needs from P21

- **Voice is one more "input channel"** for any society's coordinator — turn it into P27 design seam, not a competing path.
- **The "transcript = untrusted text" model** applies equally to any P27 input from external humans or other agents. P27 inherits it.
- **VoiceBrief data contract** (P22 §"P21 dependency map"): `source`, `summary`, `detail_url`, `urgency`, `sensitivity`, `require_confirm`. If P27 produces proactive briefings, use the same shape.
- **`_voice_client.py` is planned (NOT implemented).** P27 must wait for P21 runtime before plugging voice.

---

## 8. Phase Deep-Dive: P22 — Life Integration Hub

> Two paired sources: `docs/setup-evidence/P22/README.md` (definition-side) and PROGRESS.md line 7 (runtime-side). They describe **two different scopes** of P22 — see §6.2 resolution.

### 8.1 PROGRESS.md runtime-side (definition-level)

- **Status (PROGRESS line 7):** ✅ PASS WITH CONFIG_MISSING ADAPTERS
- **Production code:** `src/life_integrations/` (NEW)
  - 13 core modules
  - 14 adapters
  - 1 Alembic migration `p22_001`
- **Tests:** 76 unit tests pass + 12/12 smoke (exit 0)
- **ADR:** ADR-053
- **Audit rounds:** round-1 (8 auditors: 4 PASS + 2 NEEDS_REVIEW fixed + 2 PASS); round-2 (4 auditors all PASS)
- **Honest CONFIG_MISSING disclosure:** 10/13 adapters CONFIG_MISSING (external OAuth/tokens operator-gated, honest not fake), 3 OK local (VPS/Browser/Filesystem)
- **P19 read-only consumed; V-002 preserved**

### 8.2 README definition-side (the bundle in evidence root)

- **Status (README line 3):** 🟣 P22 FULL-CAPABILITY RAW ACCESS REPLAN COMPLETE — IMPLEMENTATION HOLD UNTIL MAMA AUDIT PASS/APPROVAL
- **Pivot:** **P22 = FULL CAPABILITY RAW ACCESS** (read/create/update/move/archive/delete/sync/admin). NOT read-only. NOT sensor-only. NOT half. Delete is MANDATORY capability where provider supports.
- **Plan bundle:** `plan/p22-full-capability-raw-access-replan.md` v2.0 (1312 lines, audit-resolved + mama-fix v2.1). v1.1 (`plan/p22-life-integration-hub-plan.md` retained for traceability, SUPERSEDED).
- **Research:** 9 raw-full files totaling 6,392 lines (google-workspace-full-access-research, github-admin-full-access-research, notion-full-access-research, telegram-full-access-research, comms-merge-research, ops-code-finance-browser-merge-research, p20-p19-p23-p24-merge-map, security-secrets-delete-rollback-threat-model, cost-quota-benchmark) + 5 v1.1 superseded research files.
- **Audits:** 11 raw-full audit reports (2,319 lines) — 10 raw-full + mama-fix reaudit. ALL NEEDS_REVIEW (findings resolved in plan).
- **Verification artifact:** `evidence/p22-definition-verification-raw-full.md` — RAW-FULL PHASE COMPLETE — HOLD
- **P22→P24 bridge:** `evidence/p22-p24-full-capability-merge-map.md` (105 lines) COMPLETE
- **Committed primaries:** Google Calendar (v3), Google Drive (v3), GitHub Projects v2 (GraphQL), GitHub repos/code (REST+GraphQL), Notion, Telegram.
- **Existing-merge (extend to full-cap):** Discord, Gmail, WhatsApp, VPS/system health, Finance, Browser/research, Memory/KG.
- **Default permission tier:** READ (L1) for all integrations.
- **Counts:** 35 `.md` files, 13,799 total lines under `docs/setup-evidence/P22/`.

### 8.3 Conflict-resolution note (§6.2 deeper)

PROGRESS.md line 7 reports "P22 Life Integration Hub implemented" with a runtime at `src/life_integrations/` (13 core modules + 14 adapters, 76 tests pass + 12/12 smoke + ADR-053).

The P22 README in the evidence root describes a different (newer, broader) bundle: full-capability raw-access definition phase, with 11 raw-full audits + mama-fix applied.

**Interpretation:** P22 had two distinct scopes:
1. **Initial narrow scope (PROGRESS line 7's "implemented" reference):** sensor/read-only per the v1.1 plan that PROGRESS captured as "complete" 2026-06-27. 13 core + 14 adapters + ADR-053 + 76 tests pass + 12/12 smoke.
2. **Replan to full-capability raw access (current README scope, 2026-06-25):** the operator expanded P22 to include destructive operations (delete being mandatory). The new v2.0 plan is in the evidence bundle but IMPL is HOLD pending audit gate + P20-axis preflight + P19 namespace.

**For P27:** trust PROGRESS.md for "what runs at runtime today" and trust the README for "what the operator wants to build next". They're consistent — P22 runtime = sensor/initial narrow scope; P22 definition = full-capability future scope.

### 8.4 Coupling & dependencies

- **Deps:** P8 (MVP) + P19 (project_id ready, read-only consumed) + P20 (axis satisfied by waiver)
- **Deps implied:** P21 (VoiceBrief surface); P23 (P22 sensors become P23 action targets — P23 §17 wraps P22 adapters as action targets)
- **Forward-compat with P23/P24:** P23 `ExternalExecutor` reuses P22 sensor adapters as action targets; P24 convergence design (`p22-p24-full-capability-merge-map.md`) treats P22 merge from full-capability perspective (read/create/update/delete = full CRUD).
- **Wave structure (definition):** Wave 0 (governance + ADR + consent scaffold) | Wave 1 (read L1 for committed primaries) | Wave 2 (write-notify L2 for committed primaries) | Wave 3 (admin-capability) | Wave 4 (P24 fork-internal merge). All HOLD.

### 8.5 What P27 needs from P22

- **P22 runtime at `src/life_integrations/` exists** as a pattern for any new federation-bound adapter (calendar/drive/github/notion/telegram). P27 may reuse the adapter shell pattern.
- **P22's L1/L2/L3/L4 capability tier system** (READ / WRITE-NOTIFY / DESTRUCTIVE-APPROVAL / FORBIDDEN) is a vocabulary P27 should adopt for any "society member → external surface" interaction. P23's SemanticActionClassifier extends the same model with semantics.
- **P22's audit pattern** (`audit.integration_api_log` hash-chained, immutable, no_UPDATE/DELETE, periodic re-validation) is the canonical compliance audit. P27 mutations must follow the same DDL.
- **P22 consent ledger pattern** (per-integration grant + revocation cascade) is the canonical consent model. Any P27 society → tool permission must thread through this ledger.
- **VoiceBrief data contract** (P21 → P22 → P23) — if P27 has a coordination layer that briefs Faiz, it emits VoiceBrief-shaped objects.
- **Cost/quota benchmark** (`p22-cost-quota-benchmark.md`) — every primary is `$0/month` at current usage. P27 budget impact should be benchmarked similarly.

---

## 9. Phase Deep-Dive: P23 — Embodied Operations / Personal OS Action Layer

> Source: `docs/setup-evidence/P23/README.md` (88 lines) + `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` (1075 lines).

### 9.1 Final state

- **Status:** 🟣 **P23 DEFINITION COMPLETE — P23A READY TO START (P1 fixes done); P23B BLOCKED ON P19/P21/P22 RUNTIME CONTRACTS** (2026-06-25)
- **Owner:** Faiz
- **Executor:** Guinevere (definition only)
- **Mission:** Write-side counterpart to P22 sensor adapters — across browser, Windows desktop, VPS, GitHub/CLI, file system, mobile (deferred), and external integrations. With risk classification (L1–L4), consent boundary, HARD STOP global cancellation, safe-mode/distress freeze, rollback, and P19 project namespace on every action.
- **Brain path (binding):** HermesBrain (`src/life_kernel/hermes_brain.py`) as the planner. **Raw LLMRouter.chat is FORBIDDEN** (hard rejection).
- **Plan bundle:** 1 enterprise plan (1075 lines, 46 sections + 20 waves + round-1 amendments) + 13 research files + round-1 (13 auditor dimensions) + round-2 (13 dimensions ALL PASS) + 3 final-evidence files + README.

### 9.2 Key architectural reference (binding for any action-class executor)

- **Action lifecycle (state machine):** `queued → scheduled → pre-flight(policy gate) → running → {succeeded | failed | rolled-back | cancelled | timed-out}`. Terminal states immutable in audit log. HARD STOP at any state → `cancelled`.
- **Durable queue:** PostgreSQL `p23.action_queue` table + Redis DB0 `BRPOPLPUSH p23:queue:pending p23:queue:processing` (at-least-once; `intent_hash` idempotency key prevents double-execution) + Redis pub/sub `p23:cancel` channel.
- **Idempotency key:** `(project_namespace, intent_hash)` composite. Mandatory `project_namespace` column, default `'default'`. Pre-P19 falls back to `default` namespace.
- **7-step policy gate:** classify risk → HARD STOP → safe-mode/distress → consent → namespace → EXECUTE → audit.
- **SemanticActionClassifier (§22b, Codex P1-2 fix):** MCP `AuthLevel` is an INPUT, NOT a 1:1 map to L1–L4. Classifier parses intent + subcommand + target to determine real side-effect risk. `shell_exec` (READ_AUTO) can host `python`/`pip`/`git` mutating verbs → classified L2/L3, not L1.

### 9.3 Executor surface map (all 6 + 1 deferred)

| Surface | Status | Risk Tier Skeleton | Notes |
|---|---|---|---|
| **Browser** (`browser`/`obscura`) | planned | L1=read; L2=click/fill | Per-action `BrowserContext` (no shared cookies); Playwright + Obscura CDP; full-page screenshot + DOM snapshot archived; redaction via secret_scanner; surveillance-class = CRITICAL consent + 24h retention; P13 lesson: APIs for publish when possible |
| **Windows Desktop** (`desktop`) | planned | L2=launch/kill/script; L3=schedule_task | Separate process on Faiz's PC; auth'd WebSocket via Tailscale; Process Job Object CPU/memory limits; workspace-only writes; NEVER admin by default |
| **VPS/SSH** (`vps`) | planned | L3=deploy | `guinevere` user cgroup MemoryMax=8G CPUQuota=200%; L3 deploy gate: backup (`pg_dump`+`/home/guinevere/.backup/last-success` per ADR-035 B11) → canary → smoke → IF PASS promote OR rollback |
| **GitHub/Repo** (`github`/`repo`) | planned | L1=read verbs; L2=commit/push feature; L3=force-push feature; L4=force-push main | Reuses `src/mcp/tools/github.py` + `git_tool.py` + `auth.py`; PR must pass CI; main protected; force-push-to-main = L4 FORBIDDEN (git_tool.py enforces) |
| **File System** (`filesystem`) | planned | L1=read; L2=write; L3=delete | Workspace boundary allowlist; backup-before delete (trash-can pattern); secret_scanner pre-write |
| **External Integration** (`external`) | planned | L3=delete | Wraps P22 adapters as P23 action targets (P22 = sensors in; P23 = actions out); reuse P22 `gkv1-kek-secrets-p22-*` secret_ids |
| **Mobile/Android** (`mobile`) | **DEFERRED, design seam only** | (researched, not implemented) | Phone control = intimate surveillance + high blast radius + Android fragmentation; design seam only; NO MVP impl; L1 only post-MVP after explicit Faiz consent per action class. ADB / Tasker / Termux / Accessibility Service surfaces researched but not implemented. |

### 9.4 LOCKED P20 files (P23 MUST NOT modify)

- `src/life_kernel/hermes_brain.py`
- `src/life_kernel/graph.py`
- `src/life_kernel/heartbeat.py` (schedule)
- `src/hermes/safety_plugin.py`
- `src/core/services/hard_stop_handler.py` core
- `src/life_kernel/cognition.py` guardian loop
- All P23 changes are ADDITIVE only (new `executors/` package, new `ExecutorRegistry`, additive dashboard section, additive `NotRequired` state fields).

### 9.5 Wave structure (20 waves)

| Wave range | Status | Reason |
|---|---|---|
| P23-001..004 | ⏳ HELD | Governance/domain/queue/registry — NEW files, technically unblocked, not executed |
| P23-005..010 | ⏳ HELD | Executors (browser/desktop/vps/github/filesystem/mobile-deferred) |
| P23-011..015 | ⏳ HELD (P20-gate) | Life-kernel/namespace/voice/external/HARD-STOP — LOCKED files |
| P23-016..019 | ⏳ HELD | Audit/dashboard/observability/E2E |
| P23-020 | ⏳ HELD (P20+P19-gate) | Production deploy/canary/rollback/soak/final gate |

### 9.6 Counts

- 51 files / 10,306 lines under `docs/setup-evidence/P23/`
- 13 research (5,221 lines) + 1 plan (1,160 lines) + 13 round-1 audits (2,328 lines) + 13 round-2 audits (449 lines) + 3 final-evidence + README

### 9.7 What P27 needs from P23

- **If P27 introduces any "society action"** — even collective planning, draft proposals, batch-route messages — it threads through the 7-step policy gate (classify → HARD STOP → safe-mode → consent → namespace → execute → audit). The **action lifecycle state machine is the model** for any P23/P27 action.
- **`p23.action_queue` model** (idempotency via `(project_namespace, intent_hash)`) is reusable semantics-wise — every society-launched action must be idempotent across retries.
- **`audit.action_log` schema** (event_id, sequence, occurred_at, actor_type, actor_id, executor, surface, action_id, **project_namespace**, **risk_tier**, intent_hash, command_redacted, outcome, artifact_path, rollback_state, correlation_id, metadata, previous_hash, event_hash) is the canonical compliance schema. P27 audit MUST follow this DDL.
- **SemanticActionClassifier** is THE model for risk classification. If P27 members can propose self-modifying or world-affecting actions, the classifier applies; an action's risk_tier is decided by semantics, not by who emits it.
- **HARD STOP propagation:** executors check `life_kernel:hard_stop` pre-action + between steps + subscribe to `p23:cancel`. P27 must inherit this triple-check pattern for ANY action (society proposal, society coordination, society message broadcast).
- **`project_namespace` is mandatory** on every P23 action. P27 inherits this.
- **`HermesBrain.think()`** is the brain path; Raw `LLMRouter.chat` is FORBIDDEN. If P27 members need to reason, they go through the kernel.
- **D2+ distress freezes L3, D3+ freezes L2, D4 freezes all.** P27 must NOT introduce a parallel freeze hierarchy. Reuse the PersonaSafetyPolicy distress matrix.
- **F-10 persona-pressure gate** for L3 or external-write: non-persona confirmation + evidence + Faiz approval. If P27 ever proposes destructive ops at all, F-10 applies.

### 9.8 Conflict / caveats

- **P23 has 20 implementation waves held**. It is the most policy-gated phase in the repo. Any new "society action" plan should reference P23's wave structure before designing action surfaces.

---

## 10. Phase Deep-Dive: P24 — Hermes Fork-First Full Convergence

> Source: `docs/setup-evidence/P24/README.md` (138 lines) + `docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md` (725+ lines, 44 sections + 20 waves, §15.1 reconciliation) + `docs/setup-evidence/P24/evidence/final-p24-planning-report.md` (193 lines).

### 10.1 Final state

- **Status:** 🟣 **PLAN FIXED — FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL**
- **Date:** 2026-06-25 (definition complete, codex audit fix complete)
- **Mission:** Make Guinevere truly Hermes-native through an owned Hermes fork (~owned distribution). All P1–P18 + P20+/P21/P22/P23 capabilities must have an integration path into Hermes built-in/runtime — not just side modules.
- **Final verdict:** **FULL OWNED HERMES FORK PREFERRED — IMPLEMENTATION READY** (operator source of truth 2026-06-25; fork chosen on ownership grounds, not solely on capability gap; hybrid (Option B) = transition path only; full owned fork (Option C reframed) = final architecture target).
- **Why fork:** Ownership (reproducible, pinned, forked, auditable, deployable, roadmap-controlled).
- **Recommended fork-related code:** `<200 LOC` fork surface — single lifecycle hook module `hermes_lifecycle/persistent_tasks.py` + registration in startup sequence. The ONE confirmed lifecycle/internal candidate is **P20 heartbeat 1s persistence across session end** (`on_startup(task_factory)` / `on_shutdown(task_canceller)` for persistent asyncio tasks).

### 10.2 Key upstream facts (binding)

| Aspect | Finding |
|---|---|
| Package name | `hermes-agent` (PyPI, hyphenated) |
| Version installed | `0.15.2` (P1; pinned `>=0.15` in `pyproject.toml` line 31) |
| Author | Nous Research |
| License | **MIT** (Copyright (c) 2025 Nous Research) |
| Upstream repo | `https://github.com/NousResearch/hermes-agent` |
| Integration pattern today | Adapter via `src/hermes/adapter.py` — NO direct `.venv/site-packages` edits |
| Forkability | FORKABLE — MIT permits all modifications; 24-48 hrs/year maintenance |

### 10.3 What runs today vs what the plan asks to run

| Surface | Today | Plan target |
|---|---|---|
| Direct imports of `run_agent.AIAgent` | 1 (only `src/life_kernel/hermes_brain.py`) | 0 inside fork; internal modules |
| Local adapters in `src/hermes/` | 7 (`adapter.py`, `_session_adapter.py`, `safety_plugin.py`, `_memory_bridge.py`, `plugins/persona_plugin.py`, `plugins/__init__.py`, `__init__.py`) | Become **internal extension modules inside the owned fork** |
| In-process plugins (`hermes-config/plugins/`) | 3 (`auth_overlay`, `guinevere_persona`, `guinevere_safety`) | Same |
| Command plugins (`src/hermes_plugins/`) | 44 across 7 categories (commands_high/loop/memory/surveillance/system/finance/admin) | Same |
| Shell hooks (`hermes-config/hooks/`) | 12 (`hard_stop`, `consent_gate`, `dnr_filter`, `safety_scan`, `budget_check`, `drift_check`, `error_classifier`, `finance_hook`, `hybrid_guards`, `budget_lua`, `budget_lua_extended`, `_hook_utils`) | Same |
| Config (`hermes-config/`) | `config.yaml` + `SOUL.md` (Y4 baseline, HARD STOP, Y6 block); MCP servers (fastmcp_full enabled, fastmcp_custom disabled); cron jobs (8 = 5 persona rituals + 3 maintenance) | Same content; moved INTO fork distribution |
| MCP servers | 2 (fastmcp_full enabled; fastmcp_custom disabled) | fork-internal |
| Cron jobs | 8 (5 rituals + 3 maintenance) | fork-internal |
| Extension points (Hermes native) | ~40 (17 lifecycle hooks + 9 config sections + shell hooks + 3 plugins + 2 MCP servers + 8 cron + 3 plugin manifests) | Same |

### 10.4 Architecture discrepancy (known to plan)

ADR-035 status shows "Implemented" but runtime evidence in P24 indicates **hybrid adapter pattern**, NOT full Hermes gateway replacement for all channels. Discord standalone bot is masked; Hermes Gateway Discord active for turn-core; P20 uses REST publisher for dashboard/logs (NOT Hermes Gateway).

### 10.5 Fork repo strategy (§28)

- Fork source: `https://github.com/NousResearch/hermes-agent` → `https://github.com/fazulfim/hermes-agent` (private)
- Branch policy: `main` (tracks upstream quarterly sync), `guinevere` (fork additions), tagged `v0.15.2-guinevere.N`
- License preservation: MIT copyright notice + NOTICE file documenting Guinevere modifications
- `pyproject.toml` pin: `"hermes-agent @ git+https://github.com/fazulfim/hermes-agent.git@v0.15.2-guinevere.1"`
- `.venv/site-packages` edit FORBIDDEN

### 10.6 Fork-required assessment matrix

- **P0–P18 fork-required:** **0%** (82% already native/hybrid; 18% standalone by design)
- **P20 fork-required:** YES (1: heartbeat 1s persistence that survives session end) — `<200 LOC` lifecycle hook addition
- **P19/P21/P22/P23 fork-required:** **no-fork future-proofs**; convergence target is internal extension modules inside the owned fork distribution (NOT external sidecar)
- **§18.1 contract-gate:** P24 may implement fork ownership/convergence scaffolding now; final convergence for P19/P21/P22/P23 is CONTRACT-GATED until each phase's runtime contract exists and is runtime-proven. Forbidden claim: "P19/P21/P22/P23 final convergence achieved" without runtime contract.

### 10.7 Audit summary

- 13 round-1 auditors, 4 CONDITIONAL PASS (architecture-convergence F-001+F-002, parity-testing, observability-evidence); 9 PASS/PASS-with-notes.
- 3 round-2 re-audits (architecture-convergence reaudit, docs-consistency reaudit, P20-life-kernel reaudit) ALL PASS.
- 5 codex implementability-audit blockers all fixed (stale gate wording → operator-accepted-risk-waiver wording; canary isolation to `.venv-hermes-canary`; invalid `hermes_agent.__version__` → use `importlib.metadata.version('hermes-agent')`; P24-002 mandatory before lifecycle patch; future-phase contract-gating §18.1).
- Total: 41 files / 13,426 lines (exact `wc -l` post-cleanup 2026-06-25 per `cleanup-verification-audit.md`).

### 10.8 Counts

- README (125 lines)
- 14 research files (7,118 lines)
- 1 plan (1,107 lines)
- 13 round-1 audits (3,201 lines)
- 3 round-2 re-audits (273 lines)
- 4 evidence-root files (definition-verification + auditor-gate + final-report + cleanup-verification-audit, ~1,190 lines)

### 10.9 What P27 needs from P24

- **The Hermes surface inventory, conversation invariants, and config patterns in `src/hermes/` + `src/hermes_plugins/` + `hermes-config/`** are reusable today, regardless of when the fork actually happens.
- **`hermes-conversational.py` is the ONE Discord turn responder; all new inputs route through `_process_turn_core`.** P27 must follow.
- **If P27 introduces "society coordinator agent" or "multi-role agent" pattern**, the place to define it is `src/hermes_plugins/commands_XXXXXX.py` (a command plugin registered in Hermes) — NOT a new domain mind or new agent process.
- **HARD STOP, persona FSM, consent gate, DNR filter, safety scan, budget hook shell scripts** in `hermes-config/hooks/` are the boundary enforcers. P27 inherits.
- **`SOUL.md`** is the persona baseline (Y4, HARD STOP, prompt-injection defense). Adding more persona identities needs to either (a) extend SOUL.md with explicit "society member" subsections overriding carefully, or (b) introduce a parallel SOUL file with persona-bound inheritance.
- **`§18.1 contract-gate`** applies to P27 too. If P27 reads/writes through Hermes hooks/config/plugins/MCP, the change must NOT claim "final convergence" until P27 runtime contract exists and is runtime-proven.
- **Fork deployment gates (P24-018/019/020):** any P27 deploy that touches Hermes-side files goes through backup → canary (`.venv-hermes-canary` + isolated unit) → smoke → rollback. Cannot deploy into shared `.venv` directly.
- **`hermes_lifecycle.persistent_tasks.py` skeleton** is the canonical pattern for persistence across session end. If P27 introduces background "society listeners" / "society coordinators" / "society self-improvement loops" that must persist, this is the design quote.

### 10.10 Conflict / caveats

- **P24 verdict is operator-corrected.** PROGRESS shows "PLAN FIXED — FULL OWNED FORK PREFERRED — IMPL HOLD UNTIL MAMA AUDIT". Do not regress to "Option A no fork" — research said A, operator said full fork, plan §15.1 reconciled with §15 ownership mission.
- **Fork deployment requires hardware/secrets ops** that are blocked by the §0.1 autonomy exception being SCOPED to P20 runtime only.

---

## 11. `src/` Codebase Layout (24 packages)

> Source: `Get-ChildItem -LiteralPath src/` + `glob src/**` (live filesystem, 2026-06-28).

```
src/
├── __init__.py
├── _deprecated/
│   └── hermes-migration-phase-7/    (9 files: bot.py, commands.py, conversational_handler.py, guild_setup.py,
│                                     intents.py, memory_bridge.py, permissions.py, session_adapter.py,
│                                     startup.py, README.md — Phase-7 standalone Discord bot, masked post ADR-035)
├── channels/                         (channel adapters; ties into src/discord/, src/gmail/, etc.)
├── consent/                          (consent gate + ledger — used by P7, P19, P22, P23)
├── core/                             (FastAPI main; auth; LLM router; system services; service registry)
├── discord/                          (Discord bot; 35 slash commands; hermes_conversational.py) ★
├── finance/                          (financial tracking skeleton; P9 placeholder)
├── financial/                        (financial second outlet — verify which is active)
├── gamification/                     (streaks, achievements; P4-adjacent)
├── gmail/                            (P12 Gmail channel adapter — code-complete 27 modules)
├── hermes/                           (P24 §6 — 7 local adapters wrapping Hermes) ★
│   ├── __init__.py
│   ├── adapter.py                    (canonical integration point; no direct .venv edits)
│   ├── _session_adapter.py
│   ├── safety_plugin.py              (CRITICAL: persona + HARD STOP enforcement in Hermes body)
│   ├── _memory_bridge.py             (PG/Redis proxy to Hermes memory interface)
│   └── plugins/
│       ├── __init__.py
│       └── persona_plugin.py
├── hermes_plugins/                   (47 command plugins — 7 categories)
│   ├── commands_high.py
│   ├── commands_loop.py
│   ├── commands_memory.py
│   ├── commands_surveillance.py
│   ├── commands_system.py
│   ├── commands_finance.py
│   └── commands_admin.py
├── knowledge_graph/                  (P16 — KG runtime; pgvector + RCTE) ★
├── life_integrations/                (P22 — NEW runtime, 13 core + 14 adapters, 76 tests pass) ★
├── life_kernel/                      (P20 — production autonomy, 420 tests pass) ★
│   ├── hermes_brain.py               (Hermes brain bridge; ONLY file with direct `from run_agent import AIAgent`)
│   ├── heartbeat.py                  (1s HARD STOP detection)
│   ├── graph.py                      (LangGraph StateGraph; `LifeMindState`)
│   ├── sensors/                      (read-side registry)
│   ├── domain_minds/                 (engineering / comms / finance / health / VPS / learning / self-improve)
│   ├── journal.py
│   ├── self_improve.py
│   ├── dashboard.py
│   ├── discord_rest_client.py
│   └── (... see §11.1 below)
├── loops/                            (P5 agent loop + hermes_bridge.py)
├── mcp/                              (P6 MCP tools — 16 tools; manager.py + auth.py + cost.py + budget.py)
├── memory/                           (P3 memory substrate; pgvector 1536-dim embedding; HNSW index)
├── observability/                    (P8 metrics + Sentry bridge + Prometheus client)
├── persona/                          (P4 Mood/Yandere/Punishment/Reward FSM + rituals + drift detector)
├── projects/                         (P19 — NEW runtime package) ★
│   ├── registry.py                   (project registry + domain models)
│   ├── memory_store.py               (memory/KG namespace partition)
│   └── secrets_vault.py              (in-memory keyed by `project_id`)
├── self_improve/                     (P20 self_improve bridge)
├── surveillance/                     (P7 surveillance — HMAC + consent)
├── wearable/                         (P14 wearable health pipeline — Mi Fitness / Gadgetbridge / Health Connect)
└── x_poster/                         (P13 X auto-poster — CDP / Twikit / Camoufox / Obscura client)
```

### 11.1 P20 life_kernel Notebook (plan §4 vision-lock architecture)

Per `plan/p5-p20-vision-lock.md` §4, the canonical kernel shape:
- Heartbeat (60 BPM liveness pulse + awareness + decision + scan + reflection)
- Global Life Mind (self-state, Faiz-state, world-state, long-term goals, commitments, concerns, current focus)
- Domain Minds (engineering, communication/email, finance records, health/routine, VPS/ops, learning/research, self-improvement)
- Session Graphs (per-task autonomy, worktree/profile isolation, deployment policy, Discord thread)
- Background Cognition (observer, memory, critic, curiosity, self-improvement, guardian)

### 11.2 PKG imports verbatim (★ = high-frequency cross-cutting)

- `src/hermes/safety_plugin.py` — touches persona FSM, HARD STOP, consent gate. Comment the cross-phase dependency.
- `src/discord/hermes_conversational.py` — the ONE Discord turn responder (per P21 §4). All voice/text inputs route here. Contains `_process_turn_core`.
- `src/life_kernel/hermes_brain.py` — the ONLY file with `from run_agent import AIAgent`.
- `src/memory/` + `src/knowledge_graph/` — the world model + KG; ADR-007 substrate is mandatory.
- `src/mcp/` — 16 MCP tools canonical per ADR-013.

### 11.3 What P27 needs from src/

- **`src/hermes/adapter.py` is the boundary** between Guinevere application layer and Hermes runtime. Any society-related Hermes integration must sit downstream of this boundary, NOT inside the `.venv/site-packages/hermes_*` package.
- **`src/hermes_plugins/` is the canonical extension surface** for new Hermes commands (society manager, society spawner, society vote, society audit). New commands go here as new module files.
- **`src/life_kernel/domain_minds/` is the place for autonomous processes** that have their own heartbeat + world state. Society members that need persistent autonomous reasoning extend this directory.
- **`src/projects/` is the place** for any new namespace/scope/identity registry. Society members register here (extension or new package).
- **`src/consent/` provides the consent ledger.** Any society → Faiz or society → society permission must thread through `consent.consent_ledger`.
- **`src/memory/` + `src/knowledge_graph/`** are the world model + KG; society state writes go here (idempotent, vector-embedded).
- **`src/life_kernel/journal.py`** is the reasoning log. Society decisions must write to journal.
- **`src/observability/` exposes Prometheus metrics.** Society health metrics register here.

### 11.4 Dependencies discovered (grep-level)

- `pyproject.toml:31` declares `"hermes-agent>=0.15"` — current install is 0.15.2 (recorded in P1-004 step evidence and P24 upstream-identity research).
- `src/life_kernel/hermes_brain.py` and `src/loops/hermes_bridge.py` are the runtime integration points; both use `from run_agent import AIAgent` (only vector of Hermes body access).
- 7 local adapters in `src/hermes/` and 47 `src/hermes_plugins/` modules form the public integration surface for extension.
- 12 hooks live in `hermes-config/hooks/` (not `src/`). They are shell scripts invoked by Hermes lifecycle and are independent of `src/`.

---

## 12. Hermes Package State — Ground Truth

### 12.1 Installation footprint

| Location | Status | What lives there |
|---|---|---|
| `.venv/` (top-level hidden dir) | EXISTS | UV-managed virtualenv; contains installed `hermes_agent` package v0.15.2 |
| `.hermes/` | EXISTS, mostly empty | `plugins/` subdir only (per filesystem listing) |
| `hermes-config/` | EXISTS at top-level | `config.yaml` + `SOUL.md` + `.env.template` + `hooks/` (12 scripts) + `plugins/` (3 in-process) |
| `src/hermes/` | EXISTS | 7 Guinevere adapter/safety files (5 modules + plugins/ + __init__) |
| `src/hermes_plugins/` | EXISTS | 47 command plugins across 7 categories |
| `pyproject.toml:31` | DECLARES | `"hermes-agent>=0.15"` |
| `docs/setup-evidence/P1/STEP-P1-004/pyproject.toml` | HISTORICAL COPY | identical `"hermes-agent>=0.15"` |
| `.venv/systemd-live/hermes-gateway.service` (under `vps-mirror/`) | LIVE ON VPS | runtime unit (operational) |
| `systemd/hermes-gateway.service` (repo) | CANONICAL | runtime unit definition |
| `scripts/hermes-gateway.service` | SCRIPT | same unit (which one is canonical?) |

### 12.2 Integration pattern (canonical today)

```
┌─────────────────────────┐
│     Hermes runtime      │   .venv/  (installed package: hermes_agent==0.15.2 from PyPI)
│  (Nous Research MIT)    │
└──────────┬──────────────┘
           │ via adapter
┌──────────▼──────────────┐
│ src/hermes/adapter.py   │   No direct conda-install edits; in `src/hermes/`
└──────────┬──────────────┘
           │ via plugins + hooks
┌──────────▼──────────────┐
│ src/hermes_plugins/     │   47 command plugins; get registered via Hermes plugin system
├── src/hermes/           │   7 local adapters + safety_plugin.py + _memory_bridge.py
└─────────────────────────┘
           │ via lifecycle + shell hooks
┌──────────▼──────────────┐
│ hermes-config/          │   config.yaml + SOUL.md + hooks/ (12 shell) + plugins/ (3)
└─────────────────────────┘
```

### 12.3 What the fork will introduce (per P24 plan, NOT executed)

- Fork repo: `github.com/fazulfim/hermes-agent` (private).
- Pin: `pyproject.toml` → `"hermes-agent @ git+https://github.com/fazulfim/hermes-agent.git@v0.15.2-guinevere.1"`.
- Fork additions stay in `hermes_lifecycle/` (subdir within fork repo) — single module `persistent_tasks.py` + registration.
- All `src/hermes/` + `src/hermes_plugins/` + `hermes-config/` become INTERNAL to the fork distribution.
- Deploy: `.venv-hermes-canary` (isolated) → canary unit `hermes-gateway-canary` → smoke → promote to shared `.venv` (P24-018/019/020).
- Rollback: `v0.15.2-upstream` tag alias; revert pyproject pin; `uv pip install hermes-agent==0.15.2`.

### 12.4 What P27 needs from Hermes

- **Hermes-stub context for "society member" agent reasoning.** When P27 launches a member, the member trivially has access to Hermes via `src/life_kernel/hermes_brain.py` (already part of P20 kernel).
- **A new Hermes command plugin** = the right place for any "society spawn", "society audit", "society policy-vote" command. P27 should author against the existing `commands_*.py` pattern.
- **The hook scripts in `hermes-config/hooks/`** are how personality/SOUL/operator-side policy gets enforced at every LLM and tool call boundary. If P27 introduces new boundaries, they go in `hermes-config/hooks/`, not in `src/`.
- **`SOUL.md` is the persona baseline.** If P27 has multiple personas or society members with sub-personas, separate `SOUL-*.md` files co-existing may be the pattern (NOT a single mutated SOUL).
- **Hardcoded ports (`localhost:8000` for FastAPI; `localhost:20128` for 9Router):** Aizanta isolation requires hardcoded ports — Guinevere does not collide. P27 new services must pick non-Aizanta ports (5xxx/6xxx/9xxx range, not 5432/6379/80/443/22/2019).

### 12.5 Fork-investigation command (for P27 implementer)

```bash
uv pip show hermes-agent               # installed version
python -c "import importlib.metadata as md; print(md.version('hermes-agent'))"   # canonical version lookup (P24 fix for `hermes_agent.__version__`)
ls /home/guinevere/code/guinevere/.venv-hermes-canary/  # planned canary env (P24-018)
```

---

## 13. Top-Level Directory Structure (`guinevere/`)

> Source: `Get-ChildItem -LiteralPath guinevere/` plus `glob /**`. Includes dotfiles that need attention for P27.

```
guinevere/
├── .claude/                          # agent skill cache (ala sub-agent tool-calling cache)
├── .githooks/                        # local git hooks (validate-commit-msg / pre-commit / etc.)
├── .guinevere/                       # Guinevere runtime cache / state dump (likely P20 state)
├── .hermes/                          # Hermes runtime dir; currently empty except `plugins/`
├── .mypy_cache/                      # type-check cache; safe to delete for clean re-run
├── .pytest_cache/                    # pytest cache; safe to delete for clean re-run
├── .ruff_cache/                      # ruff cache
├── .sisyphus/                        # Sisyphus planner cache (auto-format of super-autopilot artifacts?)
├── .venv/                            # UV python virtualenv; contains hermes_agent==0.15.2
├── .coverage                         # last pytest --cov run
├── .coveragerc                       # coverage config
├── .sops.yaml                        # SOPS config (creation_rules with path_regex rules)
├── .env.example                      # safe example of env contract
├── .env.gmail                        # GMAIL-specific env (sops-encrypted in production)
├── .env.wearable                     # WEARABLE-specific env (sops-encrypted)
├── .env.wearable.example             # safe example
├── .env.x_poster                     # X-POSTER-specific env (sops-encrypted)
├── AGENTS.md                         # operating contract (489 lines, v2.4)
├── README.md                         # project root README (Bahasa Indonesia)
├── CHANGELOG.md                      # change log
├── CHECKLIST.md                      # acceptance checklist (this report cites from it)
├── PROGRESS.md                       # implementation progress (this report cites from it)
├── pyproject.toml                    # python deps (line 31: `"hermes-agent>=0.15"`)
├── uv.lock                           # uv lock file
├── alembic.ini                       # alembic config
├── Dockerfile.sandbox                # for ADR-029 testing gate (deprecated/used by P23)
├── alembic/                          # alembic migrations dir (P19 migration lives here)
├── android/                          # Android flavor of Tasker-related stuff (likely P7 / P14)
├── audit-reports/                    # every audit report artifact
├── adr/                              # canonical ADR directory (39 ADRs)
├── burst-100-subagents.sh            # a shell script for parallel sub-agent dispatch (likely P19 audit pattern)
├── camoufox_test.png                 # binary test asset
├── check_p13_schema.sql              # SQL verification helper for P13
├── check_posts.sql                   # SQL helper
├── check_tables.sql                  # SQL helper
├── clients/                          # external API clients (gmail/oauth/etc? verify)
├── create_test_image.py              # image test utility
├── deploy/                           # deployment scripts/configs
├── docs/                             # documentation suite (40+ active docs)
├── ecosystem.config.js               # PM2 ecosystem config
├── evidence/                         # per-task evidence artifacts
├── fix-b3-regression/                # legacy folder from B3 fix regression
├── fix-imports/                      # one-off fix folder
├── fixes/                            # one-off fix folder
├── grafana/                          # Grafana provisioning (mirror of monitoring/grafana/dashboards)
├── guardian.py                       # legacy/loose Guardian? (matches P5 + P20)
├── hermes-config/                    # TOP-LEVEL Hermes config bundle (canonical)
│   ├── config.yaml                   # (engine config — see hermes-integration audit)
│   ├── SOUL.md                       # persona baseline (Y4, HARD STOP, Y6 prohibited)
│   ├── .env.template                 # safe template
│   ├── hooks/                        # 12 hook shell scripts (hard_stop, consent_gate, dnr_filter, etc.)
│   └── plugins/                      # 3 in-process plugins (auth_overlay, guinevere_persona, guinevere_safety)
├── infrastructure-map.md             # legacy infra doc
├── logs/                             # runtime log directory
├── main.py                           # legacy main entry?
├── manager.py                        # legacy manager (related to loops/manager.py)
├── migrations/                       # legacy migrations (older than alembic/)
├── models.py                         # legacy models
├── monitoring/                       # Grafana / Prometheus / Loki configs (P8)
├── pat.txt                           # **PUBLIC ARTIFACT** (auto-saved from a P-Run; should be SOPS-rotated)
│                                     #  ❗ this file is plaintext and may contain a personal access token
│                                     #  warn P27: treat as compromised, revoke + rotate
├── plugins/                          # Guinevere custom plugin configs (for Hermes bridge)
├── qa-inputs/                        # Q&A source documents
├── research-reports/                 # all research catalogs (P1–P24 etc.)
├── runbooks/                         # operational runbooks
├── scheduler.py                      # legacy scheduler (matches loops/scheduler.py)
├── scripts/                          # utility scripts (incl. `hermes-gateway.service` mirror)
├── secrets/                          # SOPS-encrypted secret store
│   ├── backup/                       # (B10 caveat — offline age-key recovery pending)
│   ├── .gitignore                    # exclude all *.enc env files
│   ├── db-passwords.yaml
│   ├── discord-secrets.enc.yaml
│   ├── gmail-client-secrets.json
│   ├── gmail-token.json
│   ├── guinevere-secrets.yaml
│   ├── new-age-key.txt               # recovery age key (NOT checked in — must be removed before commit)
│   ├── redis-password.yaml
│   └── test-enc.yaml
├── src/                              # the application code (24 packages — see §11)
├── stepprompts/                      # older artifact: per-step prompts for P0–P18 phases
├── systemd/                          # canonical systemd unit files (mirror vps-mirror/systemd-live/)
├── tag.json                          # build/context artifact (test)
├── tests/                            # test suites (`tests/life_kernel/`, `tests/mcp/`, etc.)
├── tmp/                              # transient scratch space (likely gitignored)
├── tmp-p0-025-gitignore              # misc scratch
├── tmp-p0-025-sops.yaml              # scratch
├── tmp-whatsapp-deploy.env           # scratch
├── tmp_loop_payload.json             # scratch
├── tmp_check_cols.py                 # scratch
├── tmp_check_llm.py                  # scratch
├── tmp_migrate.sh                    # scratch
├── tmp_p5_check.py                   # scratch
├── tmp_run_check.sh                  # scratch
├── tmp_trigger_loop.sh               # scratch
├── token.json                        # **PUBLIC ARTIFACT** (similar audit concern as pat.txt; rotated per credential rotation rule)
├── uv.lock                           # UV lockfile
├── vps-mirror/                       # mirror of live VPS state (systemd-live/, possibly more)
└── __pycache__/                      # python bytecode cache (transient)
```

### 13.1 Things P27 must NOT touch without explicit preflight

- `secrets/new-age-key.txt` (recovery age key — ADVERSE event if leaked).
- `secrets/*` in general (SOPS-encrypted but rotation discipline applies).
- `pat.txt` + `token.json` at root level — **public artifacts that must be rotated before any P27 work that touches them**.
- Any `vps-mirror/` content — it's a live VPS mirror; diffing without preflight risks diverging from live.

### 13.2 Live services (`systemd/`, verified via `vps-mirror/systemd-live/`)

- `guinevere-core.service` (FastAPI entrypoint)
- `guinevere-9router.service` (LLM router on `20128`)
- `guinevere-discord.service` (masked intentionally post ADR-035; Hermes Gateway Discord active)
- `guinevere-mcp.service` (MCP server)
- `guinevere-surveillance.service` (P7 ingestion)
- `guinevere-monitoring.service` (Compose-up-monitoring)
- `guinevere-voice.service` (P21 — planned, NOT YET DEPLOYED)
- `guinevere-actions.service` (P23 — planned, NOT YET DEPLOYED)
- `guinevere-loops.service` (P5 loop manager)
- `guinevere-scheduler.service` (APScheduler)
- `hermes-gateway.service` (Hermes main runtime)
- `guinevere-obscura.service` (browser automation, per ADR-033)
- `guinevere-core-extras` / `guinevere-xposter.service` (P13)

### 13.3 What P27 needs from the top-level layout

- **`secrets/`** = store for any new creds P27 introduces. NEVER check plaintext in. SOPS/age per `.sops.yaml` creation_rules.
- **`hermes-config/`** = touchpoint for Hermes boundary changes (config, hooks, plugins, SOUL). Source-of-truth for any persona/safety boundary.
- **`systemd/`** + `vps-mirror/systemd-live/` = canonical unit definitions. New P27 services have a unit file here; promoted via GitHub Actions / P24 §34 deploy strategy.
- **`docs/`** = knowledge base; P27 evidence goes under `docs/setup-evidence/P27/` (which already has `research/`).
- **`evidence/`** = per-task immediate evidence (vs `docs/setup-evidence/` for phase-level).
- **`audit-reports/`** = canonical place for audit reports.
- **`research-reports/`** = canonical place for research.
- **`alembic/versions/`** = place for P27 DB migrations if needed.

---

## 14. Phase Coupling & Interaction Map (one-pager)

> Synthesized from P19–P24 plans + READMEs + PROGRESS.md + P20 vision-lock + adapter inventory.

### 14.1 Vertical coupling (stack)

```
┌─────────────── LAYER 3 (interfaces) ───────────────┐
│  Discord (35 commands · 22 active + channel cmd path) │
│  Telegram (planned via P22)                          │
│  Email/Gmail (P12 live), WhatsApp (P11 live)         │
└───────────────┬─────────────────────────────────────┘
                │
┌─────────────── LAYER 2 (orchestration) ───────────────┐
│  src/life_kernel/   (P20 brain)                      │
│   ├─ heartbeat (1s HARD STOP detection)              │
│   ├─ hermes_brain.py (1 direct import from Hermes)   │
│   ├─ graph.py (LifeMindState + LangGraph)            │
│   ├─ BackgroundCognition (6 observer loops)          │
│   ├─ domain_minds/  (engineering/comms/finance/etc.) │
│   ├─ journal.py + self_improve.py                    │
│   └─ sensors/ (read-side registry)                   │
└───────────────┬─────────────────────────────────────┘
                │
┌─────────────── LAYER 1 (tools + adapters) ──────────┐
│  src/hermes/ (7 adapters wrapping Hermes)            │
│  src/hermes_plugins/ (47 command plugins)            │
│  src/mcp/ (16 MCP tools — 4-level auth)              │
│  src/memory/ + src/knowledge_graph/                   │
│  src/loops/ (P5 agent loop + hermes_bridge.py)       │
│  src/projects/ (P19 multi-project — pre-installed)  │
│  src/life_integrations/ (P22 — 14 adapters installed)│
└───────────────┬─────────────────────────────────────┘
                │
┌─────────────── LAYER 0 (safety + governance) ────────┐
│  src/consent/  (consent ledger)                      │
│  src/surveillance/  (P7 ingestion; HMAC + retention) │
│  src/persona/  (Mood/Yandere/Punishment FSM)         │
│  hermes-config/hooks/ (12 shell hooks; boundary)     │
│  hermes-config/SOUL.md  (Y4 baseline)                │
│  .sops.yaml + secrets/   (encryption at rest)        │
│  ADR-Index + PersonaSafetyPolicy  (governance truth) │
└─────────────────────────────────────────────────────┘
```

### 14.2 Lateral coupling (inter-phase)

| Coupling | Source → Target | Mechanism |
|---|---|---|
| P19 → P20 | P19 namespace contract READ-ONLY fed to P20 | `src/life_kernel/*` augmented with `project_id` (P19-005a/b/c strict-additive) |
| P21 → P20 | Voice sensor in P21 → heartbeat hook in P20 | `src/life_kernel/sensor_adapters/voice_sensor_adapter.py` (planned) |
| P21 → P22 | Voice → spoken brief of P22 calendar/tasks/notes | `VoiceBrief` data contract shared shape |
| P22 → P20 | Sensor adapters feed P20 domain minds | `src/life_kernel/sensor_adapters/<provider>_adapter.py` (planned) |
| P22 → P19 | P22 stores `(namespace, provider, resource_id)` composite key | P19 owns registry; P22 reads |
| P22 → P23 | P22 sensors become P23 action targets | `p23-ExternalExecutor wraps p22 adapter` |
| P23 → P20 | P23 planner uses HermesBrain; LOCKED-files preflight | strict-additive policy; P20-axis preflight |
| P23 → P19 | P23 actions carry `project_namespace` | mandatory column on `p23.action_queue` |
| P24 → Hermes runtime | Fork repo | git+https pin, vaulted in `.venv-hermes-canary` |
| P24 → P20 | First internal patch lives in P20 heartbeat persistence | `hermes_lifecycle/persistent_tasks.py` |
| P24 → P19/P21/P22/P23 | Convergence target is INTERNAL extension modules within the owned fork | §18.1 contract-gate forbids "final convergence" until runtime contract exists |
| P20 → ALL P21..P24 | P20 is the kernel; downstream phases add features; never replace | strict-additive policy + ADRs |

### 14.3 Dependency graph (forward only — unless otherwise noted)

```
P0──P1──P2 (parallel allowed)
P1──P3──P4
P1+P3──P5──P6──P7──P8 (MVP critical path: P0→P1→P3→P5)
P5+P8──P11 ── WhatsApp live
P8──P7 ── Surveillance live (HMAC + consent)
P5+P8──P12 ── Gmail live
P5+P6+P7+P8──P13 ── X Auto Poster live
P7+P8──P14 / P14-GB / P14-HC ── Wearable Health live
P3+P5──P16 ── KG live (ADR-050)
P3+P5+P8 ── P19 ── (waiver) ── PRODUCTION LIVE 2026-06-27
P5+P8 ── P20 ── (waiver) ── PRODUCTION LIVE 2026-06-23 / EARLY ACCEPTANCE
P2+P8 + P20-gate ── P21 ── DEFINITION COMPLETE (IMPL HOLD)
P8+P19+P20 ── P22 ── DEFINITION COMPLETE (IMPL HOLD); runtime narrow-scope already installed
P20-axis + P19/P21/P22-runtime ── P23 ── DEFINITION COMPLETE (IMPL HOLD)
P20-axis + P19-namespace + P24-002 ── P24 ── PLAN FIXED (IMPL HOLD until mama audit)
```

### 14.4 Risk & runtime coupling

| Risk category | Coupling | Mitigation present |
|---|---|---|
| Single channel downtime | Discord masked → Hermes Gateway; P20 dashboard/log uses REST publisher | Mitigation: cross-channel HARD STOP Redis |
| Single LLM provider failure | 9Router combo routing primary (opencode-go DeepSeek) + secondary (cockpit GPT-5.5) | ADR-005; budget_check hook fail-closed |
| Single Postgres DB outage | All 47 tables + life_kernel + kg in `guinevere` DB | ADR-027 hardcoded port 5433; DR via S3+R2 |
| Rust unfireable kernel not yet built | HardStopHandler in-process killswitch only | Stanford/ARYA Labs acknowledged risk; v2.0 deferred |
| P20 runtime incident | Any incident reverts P20 to PASS HOLD | Operator waiver remedy; preflight-before-LOCKED-edit gate |
| Fork not yet created | Fork runs against upstream `hermes-agent` only | P22/P23/P24 final convergence contract-gated (§18.1) |

---

## 15. P27 Planning Observations (concrete derivable results)

> Portion of this report the parent agent consuming it can act on immediately.

### 15.1 What exists that P27 inherits

1. **A production-grade autonomy kernel** (`src/life_kernel/`) with 420 passing tests + 1s heartbeat + HermesBrain planner + domain minds + journal + self_improve + 6 observer loops. P27's "society members" can be EXPRESSED as domain minds (extensions) or as new persona-shells (`SOUL-{name}.md` files), not as parallel runtimes.
2. **A multi-project registry** (`src/projects/`) with namespace contract. P27's society identities can register there; default namespace = `default` fallback.
3. **`project_id` propagation** wired through P19-005 across memories, KG, audit journal, agenda, surveillance scope, deploy boundary. Society-wide identifiers carry project context automatically.
4. **A 7-step policy gate design** (P23 §6) — HARD STOP > safe-mode > consent > namespace > audit — that any action-class step in P27 inherits.
5. **A risk-tier model (L1=autonomous read; L2=write-notify; L3=destructive-approval; L4=forbidden)** that P22/P23 layers on, and that P27 must respect for any destructive side effects.
6. **`SOUL.md` persona baseline + 12 hook scripts in `hermes-config/hooks/`** (hard_stop, consent_gate, dnr_filter, safety_scan, budget_check, drift_check, error_classifier, finance_hook, hybrid_guards, budget_lua, budget_lua_extended, _hook_utils).
7. **Audit hash-chained tables** (`audit.integration_api_log` from P22 v1.1; planned `audit.action_log` from P23). Immutable rows with WORM constraint; canonical schema fields.
8. **`docs/setup-evidence/P21..P24/`** research/plan/audit/evidence bundles — P27 should be modeled on the same template (research/plan/audits/evidence/final-report).
9. **`ADR-035` (Hermes migration architecture), ADR-052 (multi-project), ADR-053 (P22)** the canonical ADRs P27 must reference in any future ADRs (suggest ADR-054 — Hermes Society Foundation).
10. **The "P24-Style" 13-auditor round-1 + 3-auditor round-2 + final-report workflow** is the proven template; reuse.

### 15.2 What does NOT yet exist that P27 may need to build

1. **No "society" or "multi-agent" runtime pattern.** P21..P24 address *single-agent* autonomy variations. P27 is the first multi-agent-of-guinevere-pattern phase. Implications:
   - No existing `society_registry.py` — P27 may need `src/society/registry.py` (NEW).
   - No existing `society_consensus.py` — P27 may need a coordinator design.
   - No existing inter-agent audit — P27 may need `audit.communication_log` extending `audit.action_log`.
2. **No "persona shell" mechanism** for multiple personas coexisting. Today `SOUL.md` is monolithic; multiple personas would require either (a) multiple `SOUL-{name}.md` files registered via `hermes-config/`, or (b) parametric persona context for single runtime. Decision is architectural for P27.
3. **No "society → operator consent ledger"** distinct from `consent.consent_ledger`. If society members can self-authorize or coordinate without Faiz, that introduces a new consent domain.
4. **No P25/P26 phase to inherit.** No constraints from prior society/multiverse work.
5. **No multi-LLM "panel of judges" pattern.** P27 may need to author one if Society requires diversity-of-views decision-making.

### 15.3 Caveats / risks for P27

1. **Atmosphere of "PASS WITH ACCEPTED RISK"** in P20 — any future P20 incident reverts downstream gates. P27 may tie to that gate.
2. **Single-PoV ("FIXME: not 100% runtime-proof") at P22 CONFLICT_in_PROGRESS** — the v2.0 full-cap replan introduces a different scope than the v1.1 narrow; P27 should align with the **v2.0 full-capability** that the operator dirties, not v1.1.
3. **Hard persona constraints** — Y4 baseline, Y5 ceiling, Y6 impossible (architectural prohibition). Any "Y6+ society member" framing must be rejected at scaffold gate.
4. **F-10 persona-pressure gate** is the safety floor for irreversible action; any P27 decision that is destructive must clear F-10 OR escalation through non-persona confirmation.
5. **Audit hash-chain integrity** — once P27 actions pass `audit.*` (likely `audit.communication_log`), the chain becomes part of the immutable audit. Verify the chain on every commit.
6. **Fork-deploy hazard** — if P27 introduces code that requires the Hermes fork (P24 §6 §8 §17 §18 §19 §20), the fork DEPLOY HAZARD is real. P24-018 canary isolation + P24-019 promotion + P24-020 24h soak are real blockers; P27 cannot depend on the fork being live next week.
7. **The `# type: ignore` block exists in `src/` (per P6 system audit) — pre-ADR-035 debt.** AGENTS.md BLOCKING forbids `as any` etc. but pre-existing `# type: ignore` in `src/` is grandfathered. P27 must NOT relax the BLOCKING.
8. **Several CONFIG_MISSING adapters in P22 (10/13 = 77% missing external creds).** P27 may want to integrate with those adapters — note that operators must provide credentials before any production integration works.
9. **`pyproject.toml` `hermes-agent>=0.15` is a permissive pin.** P27 should NOT bump Hermes (no pin change; pin is `>=0.15`, installed is `0.15.2`).

### 15.4 Cross-cutting P20-LIVE invariants P27 must NEVER violate

- HARD STOP global halt (Redis `life_kernel:hard_stop`) — non-bypassable.
- V-003 silence-is-not-a-blocker — society members continue when Faiz is silent (within their domain priorities).
- V-007 audit-for-debugging — every society action leaves a journal + audit row.
- V-008 HARD STOP global — same as above.
- §2.1 Consent-Safety Mandate — persona, surveillance, memory, consent, safety-policy domains ALL keep boundary.
- §0.1 P20 autonomy exception — DOES NOT extend to P27 planning; planning is NOT exempt.
- §9 Repository Isolation — never share infrastructure with unrelated projects.
- §11 BLOCKING rules — type-safety, error handling, test integrity, secret hygiene all still apply.

### 15.5 Files & directories the P27 planner MUST read first (in order)

1. `PROGRESS.md` (top-level — already covered)
2. `AGENTS.md` (top-level — operating contract)
3. `docs/README.md` (master docs index, 354 lines, Bahasa Indonesia)
4. `docs/10-governance/17-ADR_Index_v1.0.md` (39 ADRs)
5. `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md` (V-001..V-008 binding)
6. `docs/setup-evidence/P19/README.md` + `docs/setup-evidence/P20/README.md` (live kernel state)
7. `docs/setup-evidence/P21/README.md` + `docs/setup-evidence/P22/README.md` + `docs/setup-evidence/P23/README.md` + `docs/setup-evidence/P24/README.md` (held phases)
8. `src/life_kernel/` package files (heartbeat, hermes_brain, graph, sensors, domain_minds, journal, self_improve, dashboard)
9. `src/projects/` files (registry, memory_store, secrets_vault)
10. `src/hermes/` + `src/hermes_plugins/` for the Hermes boundary surface
11. `hermes-config/` (config.yaml + SOUL.md + hooks/ + plugins/)
12. `docs/10-governance/17-ADR_Index_v1.0.md` — ADR-002, ADR-007, ADR-009, ADR-013, ADR-022, ADR-029, ADR-035, ADR-050, ADR-052, ADR-053

### 15.6 Files & directories the P27 planner should AVOID touching in planning phase

1. `secrets/` contents
2. `.venv/`, `.venv-hermes-canary/` (post-impl)
3. `vps-mirror/`, `systemd/` (live VPS state)
4. `pat.txt`, `token.json` at root — clean up before any commit; rotate.
5. `secrets/new-age-key.txt` — recovery key, must NEVER be checked in.
6. Anything in `.hermes/` runtime cache.

---

## 16. Sources & Authority

### 16.1 Primary evidence files (this report's ground truth)

| Source | Why cited |
|---|---|
| `PROGRESS.md` | cumulative phase tracker; per-phase high-level status |
| `CHECKLIST.md` | acceptance + budget tracker; cross-validates PROGRESS |
| `AGENTS.md` | operating contract; BLOCKING rules; workflow gates; tie-breakers |
| `docs/10-governance/17-ADR_Index_v1.0.md` | canonical ADR register; ADR-002/007/009/013/022/029/035/050/052 |
| `docs/setup-evidence/P19/README.md` | P19 PRODUCTION COMPLETE status, deployment timeline, audit verdict |
| `docs/setup-evidence/P20/README.md` | P20 EARLY ACCEPTANCE, kernel package layout, test status |
| `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md` | V-001..V-008 binding; autonomy priority order |
| `docs/setup-evidence/P20/plan/p5-p20-merged-plan.md` | (SUPERSEDED — retained for traceability) |
| `docs/setup-evidence/P21/README.md` | P21 DEFINITION COMPLETE — IMPL HOLD; voice = text invariant |
| `docs/setup-evidence/P22/README.md` | P22 DEFINITION COMPLETE — IMPL HOLD; full-cap v2.0 |
| `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` | (SUPERSEDED — v1.1) |
| `docs/setup-evidence/P23/README.md` | P23 DEFINITION COMPLETE — P23A ready / P23B BLOCKED |
| `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` | 1075-line plan with 7-step gate + executor + classifier |
| `docs/setup-evidence/P24/README.md` | P24 PLAN FIXED — FULL OWNED FORK PREFERRED |
| `docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md` | 725+ lines, §15.1 verdict correction; fork-first stance |
| `docs/setup-evidence/P24/evidence/final-p24-planning-report.md` | 41 files / 13,426 lines; 5 codex blockers fixed |
| `docs/README.md` | master docs index (354 lines) |

### 16.2 Live filesystem discovery

| Probe | Result |
|---|---|
| `glob docs/setup-evidence/P25*` | **No files found** |
| `glob docs/setup-evidence/P26*` | **No files found** |
| `glob docs/setup-evidence/P27*` | **No files found** (P27 evidence root created 2026-06-28 for this report) |
| `glob docs/setup-evidence/*/README.md` | 11 README.md files: P16, P17, P18, P19, P20, P21, P22, P23, P24, `p14-expansion`, `phase-2` |
| `Get-ChildItem src/` | 24 packages (see §11) |
| `Get-ChildItem src/hermes` | 5 module files: adapter, safety_plugin, _memory_bridge, _session_adapter, __init__ |
| `Get-ChildItem src/discord/_deprecated` | (none) |
| `Get-ChildItem src/_deprecated/hermes-migration-phase-7` | 9 files: bot.py, commands.py, conversational_handler.py, guild_setup.py, intents.py, memory_bridge.py, permissions.py, session_adapter.py, startup.py (+ README.md) |
| `Get-ChildItem hermes-config` | config.yaml + SOUL.md + .env.template + hooks/ + plugins/ |
| `Get-ChildItem .hermes` | only `plugins/` (TODO verify contents) |
| `Test-Path .venv` | True |
| `grep hermes-agent pyproject.toml` | matches: 2 (canonical + historical P1-004 step) |
| `glob **/*hermes*` | 52 paths, dominated by research-reports and running Hermes services |

---

## 17. Footer

| Item | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Buffy (codebase search specialist, sub-agent of Guinevere) |
| Status | GROUND TRUTH — ready for P27 synthesis + plan synthesis |
| Reviewed | by self on read-back; no parent verify yet (this is a research artifact, not implementation evidence) |
| Conflicts noted | P22 PROGRESS vs README (resolution in §6.2 + §8.3); P20 "PASS WITH ACCEPTED RISK" vs "EARLY PRODUCTION ACCEPTANCE" (resolution in §6.2) |
| Bound until | P27 planner reads and contradicts or extends; or until a P27 wave opens new facts that rebase P19–P24 status |
| Maintenance | if P19 onwards status changes (any new production deploy, audit round, plan amendment, ADR ratification), regenerate this report under `docs/setup-evidence/P27/research/p27-ground-truth-repo-state.md` (parent is responsible for refresh) |

> **No secrets were observed.** `pat.txt` + `token.json` at repo root are existing plaintext artifacts and predate this report; the report notes them so P27 can clean up; the report itself does not contain or read their contents.

> **No emulator implementation required.** This is a definition/planning-phase artifact. No code in `src/` was modified. No migrations added. No services restarted. No `secrets/` touched. No `.venv`/`site-packages` touched.

> **All numeric line/file counts are filesystem-truth.** Where used, the source command is named (e.g., `wc -l`, `Get-ChildItem`, `glob`) so the parent can re-verify. Where I could not run `wc -l` live (no shell pipe to here), I cite the bundle's own self-disclosure (e.g., P22 README's `35 .md files, 13,799 total lines` or P24 final report's `41 files / 13,426 lines`).

> **Final cross-check.** The parent agent can verify these file sizes via:

```bash
ls -lah docs/setup-evidence/P27/research/p27-ground-truth-repo-state.md
wc -l docs/setup-evidence/P27/research/p27-ground-truth-repo-state.md
```

---

*End of report.*