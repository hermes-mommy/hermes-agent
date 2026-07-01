# P23 Embodied Operations / Personal OS Action Layer — Final Planning Report

**Phase:** P23 — RESEARCH + PLANNING ONLY (NO implementation/deploy/restart)
**Date:** 2026-06-25
**Author:** Guinevere (parent) for Faiz
**Status:** **P23 DEFINITION COMPLETE — P23A READY TO START (P1 fixes done); P23B BLOCKED ON P19/P21/P22 RUNTIME CONTRACTS**

---

## 1. Executive Summary

Phase 23 defined Guinevere's operational "hands and feet" end-to-end — **without writing any runtime code, deploying, or restarting production.** The definition gives Guinevere a 24/7 autonomous, durable, auditable, policy-gated action layer that executes real digital actions across browser, Windows desktop, VPS, GitHub/CLI, file system, mobile (deferred), and external integrations — with risk classification (L1–L4), consent boundary, HARD STOP global cancellation, safe-mode/distress freeze, rollback, and P19 project namespace on every action — using the P20 life kernel (`HermesBrain`) as the brain, never raw `LLMRouter`.

The central architectural insight: **P23 is the write-side counterpart to `src/life_kernel/sensor_adapters/`.** A new `BaseExecutorAdapter` + `ExecutorRegistry` register executors that are **thin wrappers** over existing battle-tested MCP tools (`src/mcp/tools/{git_tool,github,obscura_cdp,...}.py`) whose `AuthLevel` (`READ_AUTO`/`WRITE_NOTIFY`/`DESTRUCTIVE_APPROVAL`/`FORBIDDEN` via `src/mcp/auth.py`) is an **INPUT** to P23 risk classification — NOT a 1:1 map to L1–L4 (Codex P1-2 fix). A `SemanticActionClassifier` decides the final tier by parsed intent + subcommand + real side-effect risk: `shell_exec` is `READ_AUTO` yet allows `python`/`pip`/`git` which can mutate state, so those classify L2/L3 by semantics, never L1. P23 reuses MCP tools but classifies above them — yielding safety-by-construction (force-push-to-main already FORBIDDEN by `git_tool.py`) and satisfying the hard-rejection rule against a planner-only design.

Implementation waves P23-001..020 are fully defined and scaffolded (each with 10 verification-scaffold fields) with acceptance split into **P23A** (core action runtime, default namespace, voice/external disabled — ready to start after the 2 P1 fixes done 2026-06-25) and **P23B** (full integration — blocked on P19 runtime namespace registry, P21 impl, P22 impl). See §7.

---

## 2. What Was Done (this phase)

| Deliverable | Path | Status |
|---|---|---|
| 13 specialist research files | `research/p23-*.md` (13 files, 5,221 lines) | ✅ |
| Enterprise plan (planner gate) | `plan/p23-embodied-operations-enterprise-plan.md` (1,075 lines, 46 sections + 20 waves + round-1 amendments) | ✅ |
| Audit round 1 (13 dimensions) | `evidence/audits/round-1/*.md` (2,328 lines) | ✅ |
| Round-1 amendments (9 findings R1-1..R1-9) | folded into plan wave scaffolds + "Round-1 Audit Amendments" section | ✅ |
| Audit round 2 (13 dimensions, all PASS) | `evidence/audits/round-2/*.md` (449 lines) | ✅ |
| Definition verification | `evidence/p23-definition-verification.md` | ✅ |
| Auditor gate | `evidence/auditor-gate.md` | ✅ |
| This final report | `evidence/final-p23-planning-report.md` | ✅ |
| README | `README.md` | ✅ |

**Total: 1 plan + 13 research + 26 audit (13×2 rounds) + 9 final-evidence/audit (incl. p23-doc-gate-cleanup, p23-recount-ground-truth, codex audit, 3 codex-fix audits) + 1 README = 51 files / 10,306 lines under `docs/setup-evidence/P23/`.**

> Provenance: 2 research files (github, observability) + all 13 round-2 audit files are parent-authored with documented provenance per AGENTS.md §14 (subagent API timeouts / dispatch interruption; parent-authored replacements accepted and parent-read, mirroring P21 §2 precedent). All other files are subagent-authored with file-based output.

---

## 3. Key Architectural Decisions

1. **Executor layer, not sidecar** — `BaseExecutorAdapter` (sibling to `BaseSensorAdapter`) + `ExecutorRegistry` (parallel to `SensorRegistry`); thin wrappers over MCP tools. (Hard-rejection #1, #7.)
2. **Brain path = HermesBrain (V-004), raw LLMRouter FORBIDDEN** — planner + self-debug via `think()`/`think_with_tools()`; P23-011 grep-enforced. (Hard-rejection #4, #5.)
3. **Risk tiers via SemanticActionClassifier (Codex P1-2 fix)** — `AuthLevel` is an INPUT, NOT a 1:1 map to L1–L4; the classifier inspects parsed intent + subcommand + real side-effect risk so `shell_exec` `python`/`pip`/`git` at `READ_AUTO` classify L2/L3, never L1. Force-push-to-main already FORBIDDEN by `git_tool.py`. (Hard-rejection #11.)
4. **7-step policy gate (non-skippable)** — classify→HARD-STOP→distress→consent→namespace→execute→audit; D0–D4 freeze + Y0 + F-10. (Hard-rejection #9, #10, #12.)
5. **HARD STOP cancels all** — `life_kernel:hard_stop` single source; pre+mid-action checks + `p23:cancel` pub/sub; queued drain-cancel. (Hard-rejection #9.)
6. **P19 namespace mandatory** — `project_namespace` on every action (default `'default'`); read-only P19 registry; impl hold until P19 namespace contract readiness. (Hard-rejection #6.)
7. **Durable + auditable** — PG `p23.action_queue` (idempotency `project_namespace+intent_hash`) + Redis BRPOPLPUSH; hash-chained WORM `audit.action_log` + reasoning `journal`; redacted artifacts. (Hard-rejection #2, #3, #8.)
8. **P20 non-interference** — additive-only; 1s HARD-STOP loop, 6-interval schedule, `hermes_brain.py`, `graph.py`, `src/hermes/safety_plugin.py`, `hard_stop_handler.py` core, `cognition.py` guardian untouched. (Hard-rejection #4, #19.)
9. **Reuse-heavy** — VPS executor reuses `deploy_backend.py`/`engineer_mind.py` DeployPolicy + adds Aizanta checks; browser executor refactors `obscura_cdp.py` singleton to per-action `BrowserContext`. (Hard-rejection #7, #12, #13.)
10. **Mobile DEFERRED** — P23-010 seam-only (no MVP impl); phone control = intimate surveillance. (Hard-rejection related.)

---

## 4. Implementation Waves (P23-001..020)

| Wave | Title | Blocked on |
|---|---|---|
| P23-001 | Governance/ADR/docs sync + action policy charter | — |
| P23-002 | Action domain model + risk classifier | 001 |
| P23-003 | Durable action queue (PG + Redis) | 002 |
| P23-004 | Executor registry + BaseExecutorAdapter | 002,003 |
| P23-005 | Browser executor (Playwright + Obscura CDP) | 004 |
| P23-006 | Windows desktop executor (PowerShell + process isolation) | 004 |
| P23-007 | VPS/SSH executor (backup/canary/smoke/rollback) | 004 |
| P23-008 | GitHub/repo executor (branch/PR/check policy) | 004 |
| P23-009 | File system executor (workspace boundary) | 004 |
| P23-010 | Mobile/Android executor (DEFERRED gate) | 004 |
| P23-011 | P20 life-kernel action planner integration | 005-009, **P20 axis satisfied by operator accepted-risk waiver; fresh runtime incident preflight required before LOCKED-file edits** |
| P23-012 | P19 project namespace integration | 011, **P19 namespace contract readiness** |
| P23-013 | P21 voice command integration | 011, **P21 impl** |
| P23-014 | P22 external integrations integration | 011, **P22 impl** |
| P23-015 | HARD STOP + safe-mode cancellation | 004,011 |
| P23-016 | Audit journal + artifacts + redaction | 003,004,015 |
| P23-017 | Discord dashboard/log UX | 016 |
| P23-018 | Observability/metrics/alerts | 016,017 |
| P23-019 | E2E test harness + scenario suite | 005-010,015,016 |
| P23-020 | Production deploy/canary/rollback/soak/final gate | 019, **P20 axis satisfied by operator accepted-risk waiver; fresh runtime incident preflight required before LOCKED-file edits + P19 namespace contract readiness** |

Each wave has 10 scaffold fields: Expected Files, Forbidden Patterns, Required Commands, Evidence Requirements, Hard Rejection Criteria, Rollback/Re-run Safety, Parent Verification Commands, Auditor Assignment, Runtime Proof Required, Deployment/Soak Requirement.

---

## 5. Audit Outcome

- **Round 1 (13 dimensions):** 8 PASS, 4 NEEDS-REVIEW, 1 PASS-with-minor. **0 FAIL.** No unmitigated hard-rejection criterion. All findings plan-level (col-name, path, scaffold-strengthening) or impl-enforcement (folded into scaffolds).
- **Fixes:** 9 findings (R1-1..R1-9) applied via `scripts/fix_plan_findings.py`.
- **Round 2 (13 dimensions):** **all PASS.** All findings CLOSED or accepted. No regression.

---

## 6. Hard-Rejection Criteria — All 19 Mitigated

All 19 mandated hard-rejection criteria mitigated (see plan §45 + `evidence/p23-definition-verification.md` §5). Key ones: #1 real executors (not planner-only) ✅; #4/#5 HermesBrain not raw LLMRouter ✅; #6 P19 namespace mandatory ✅; #7 executor isolation ✅; #8 secrets redacted ✅; #9 HARD STOP cancels all ✅; #10 distress freeze ✅; #11 risk tiers clear ✅; #12 L3 backup-canary-smoke-rollback ✅; #14 dashboard proves state ✅; #16 waves end-to-end ✅; #19 respects P20 axis / operator accepted-risk waiver ✅.

---

## 7. Blockers / Implementation Hold Reason + P23A/P23B Split

Per Codex implementability audit, P23 acceptance is split into two tracks because the dependency phases (P19/P21/P22) are not all runtime-ready:

### 7.1 P23A — Core Action Runtime (READY TO START after the 2 P1 fixes)

P23A is the core action layer with **default namespace** and **voice/external adapters disabled**. It does NOT require P19/P21/P22 runtime contracts.

- **Ready after P1 fixes (both done 2026-06-25):** P1-1 count recompute (✅), P1-2 semantic classifier (✅ §22b).
- **Waves:** P23-001 (governance/scaffold), P23-002 (typed action model + SemanticActionClassifier), P23-003 (durable queue + migration, DB role/WORM verification), P23-004 (executor interface + registry), P23-005..P23-010 (executor wrappers — provided P1-2 semantic classifier is implemented first), P23-016..P23-019 (audit/dashboard/metrics/E2E scaffolding).
- **P23A acceptance:** core action queue + executors + policy gate + audit + dashboard work end-to-end in `default` namespace; voice/external adapters stubbed/disabled; P23-020 runs a P23A-scoped soak (action queue live, HARD-STOP tested, no P20 regression, no Aizanta impact).
- **P23A does NOT claim "full Personal OS":** no multi-project isolation, no voice input, no external integration actions.

### 7.2 P23B — Full Integration (NOT READY; requires P19/P21/P22 runtime contracts)

P23B is the full multi-project Personal OS. It CANNOT honestly complete until dependency runtime contracts exist:

- **P23-011** (life-kernel planner wiring): requires fresh P20 runtime preflight before touching LOCKED files (P20 axis satisfied by operator accepted-risk waiver 2026-06-25, but LOCKED-file edits still need a runtime incident check).
- **P23-012** (namespace integration): requires **P19 runtime namespace registry** (P19 definition is complete, but the runtime contract is not yet enforced) OR feature-flagged default-only mode (P23A).
- **P23-013** (voice bridge): requires **P21 implementation** (P21 is definition-complete only).
- **P23-014** (external integrations): requires **P22 implementation** (P22 is definition-complete only).
- **P23-020** (full production deploy/soak/final gate): requires all dependency contracts + runtime proof.
- **P23B acceptance:** multi-project namespace isolation, voice→action, external integration actions, full production soak.

### 7.3 Honest implementation-readiness status

**P23 is NOT "fully implementation-ready".** P23A (core action runtime) is ready to start after the 2 P1 fixes (done). P23B (full integration) is blocked on P19/P21/P22 runtime contracts that do not all exist yet. Any claim that P23 is "100% implementation-ready" while P19/P21/P22 runtime dependencies are unresolved would be false (Codex P2 hard-rejection).

These are the hard blockers for P23B: P20 axis (satisfied by operator accepted-risk waiver; fresh runtime incident preflight before LOCKED-file edits); P23-012 needs P19 namespace contract readiness (runtime registry, not just definition); P23-013 needs P21 impl; P23-014 needs P22 impl.

---

## 8. Counts (as of 2026-06-25)

- **File count:** see `evidence/p23-recount-ground-truth.md` for the authoritative filesystem-recomputed count (recomputed via `scripts/p23_recount_guard.py`, not string-replaced).
- **Research files:** 13 · **Plan:** 1 · **Audit files:** 26 (13 round-1 + 13 round-2) · **Final evidence:** 4+ (definition-verification, auditor-gate, this report, p23-recount-ground-truth, p23-doc-gate-cleanup, codex audit) · **README:** 1.

---

## 9. Final Verdict

**P23 DEFINITION COMPLETE — P23A READY TO START IMPLEMENTATION (after P1 fixes); P23B BLOCKED ON P19/P21/P22 RUNTIME CONTRACTS.**

- ✅ 100% definition coverage (46 sections + 20 waves + §22b semantic classifier + §7 P23A/P23B split).
- ✅ Double audit (round-1 + round-2) — all 13 dimensions PASS.
- ✅ All 19 hard-rejection criteria mitigated + Codex P1-1 (counts) + P1-2 (semantic classifier) + P2 (P23A/P23B split) fixed.
- ✅ Parent verification (grep-verified + filesystem-recomputed counts).
- ✅ No runtime code/deploy/restart/secret-edit/service-disruption.
- ✅ P23A ready to start: P1-1 count recompute done, P1-2 SemanticActionClassifier added (§22b), default-namespace + disabled voice/external scope defined.
- ⏳ P23B NOT ready: P19 runtime namespace registry, P21 impl, P22 impl required (definition-complete only).

## 10. Next Action

1. **P23A:** begin P23-001 → P23-010, P23-016..P23-019 wave-by-wave via `superpowers:subagent-driven-development` (P1 fixes done; default namespace; voice/external disabled). Respect dependency map (§41) + parallelism (§42) + collision scan (§43).
2. **P23B (blocked):** await P19 runtime namespace contract readiness, P21 implementation, P22 implementation; then P23-011..P23-015, P23-020.
3. Update `PROGRESS.md` / `CHECKLIST.md` / `docs/IMPLEMENTATION_GUIDE.md` as each wave completes.

---

## 11. Footer

| Field | Value |
|---|---|
| Phase | P23 Embodied Operations / Personal OS Action Layer |
| Status | DEFINITION COMPLETE — P23A READY TO START; P23B BLOCKED ON P19/P21/P22 RUNTIME |
| Date | 2026-06-25 |
| Author | Guinevere (parent) for Faiz |
| Counts | see `evidence/p23-recount-ground-truth.md` (filesystem-recomputed) |
| Research | 13 files |
| Audit | 26 files (13 round-1 + 13 round-2) + Codex implementability audit |
| Final verdict | P23A READY TO START (P1 fixes done); P23B NOT READY (P19/P21/P22 runtime contracts unresolved) |
| Blockers (P23B) | P19 runtime namespace registry; P21 impl; P22 impl; P20 fresh runtime preflight before LOCKED-file edits |
| Hold reason | P23A can run default-namespace + disabled voice/external; P23B full integration needs P19/P21/P22 runtime |
| Next action | Start P23A (P23-001..010, 016..019); P23B waits on dependency runtime contracts |
