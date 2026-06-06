# Auditor Gate 5 (v2) — ADR/Docs/Evidence Refresh for ADR-035 Phase 5 Post-Implementation

| Field | Value |
|---|---|
| **Auditor** | Sisyphus-Junior (Independent Auditor 5 — ADR/Docs/Evidence) |
| **Scope** | Planner §16 Auditor 5: ADR-035 compliance, evidence files, doc sync, risk level, stale references |
| **Evidence Root** | `docs/setup-evidence/phase-5/` |
| **Date** | 2026-06-06 |
| **VPS Host** | `guinevere-vps` (Tailscale) |
| **Predecessor Auditors** | `auditor-gate-5-adr.md` (PASS, 2026-06-05), `auditor-gate-5-adr035-post.md` (CONDITIONAL PASS, 2026-06-06 01:47 — **now stale**) |
| **Sibling v2 Auditors** | `auditor-gate-5-persona-integrity-post-v2.md` (✅ PASS, 2026-06-06); Auditor 2/3/4 v2 outputs are still running/pending |
| **Verdict** | ⚠️ **NEEDS REVIEW** — 7 genuine findings require parent action before final signoff |

---

## Important: v1 Staleness

The previous ADR auditor (`auditor-gate-5-adr035-post.md`, 2026-06-06 01:47) is **stale**:
- Referenced v1 evidence paths (`verification-5-6.md` not `-v2.md`)
- Evaluated against pre-v2 state (463-line SOUL, old drift hash `7904fec...`, old cron/crontab assumptions)
- Claimed CONDITIONAL PASS based on evidence that no longer reflects current state
- Did not detect stale `evidence-phase-5.md`, PROGRESS.md overclaims, or G-17/G-15 actual status

**This v2 audit re-verifies every finding against current live VPS and v2 evidence files (created 04:23–06:18 on 2026-06-06).**

---

## PART A: IMPLEMENTATION EVIDENCE AUDIT

### A.1 V2 Verification File Set — Complete

| Step | v2 File | Status | Current? |
|---|---|---|---|
| 5.1 | `verification-5-1-v2.md` | ✅ PASS (508-line SOUL, 11 scaffold checks) | ✅ Current (2026-06-06 04:23) |
| 5.2 | `verification-5-2-v2.md` | ✅ PASS (triple hash match `b8d55fe...9740`) | ✅ Current (2026-06-06 04:52) |
| 5.3 | `verification-5-3-content-reconciliation.md` | ✅ PASS (5 skills content-verified) | ✅ Current (2026-06-06 04:42) |
| 5.4 | `verification-5-4-v2.md` | ✅ PASS (10 Redis DB5 keys seeded, plugin loads) | ✅ Current (2026-06-06 05:28) |
| 5.5 | `verification-5-5-v2.md` | ✅ PASS (5 cron jobs via `hermes cron create`) | ✅ Current (2026-06-06 06:08) |
| 5.6 | `verification-5-6-v2.md` | ✅ PASS (midnight triple-isolated, 5 jobs verified) | ✅ Current (2026-06-06 06:18) |
| 5.7 | `verification-5-7-v2.md` | ✅ PASS (persona migration, 0 LSP errors, 251 tests) | ✅ Current (2026-06-06 04:32) |
| 5.8 | `verification-5-8-v2.md` | ✅ PASS (18-gate refresh, staleness documented) | ✅ Current (2026-06-06 06:42) |

**Verdict: ✅ PASS** — All 8 v2 verification files exist and are current. This is the authoritative evidence set.

### A.2 Supporting Artifacts

| Artifact | Status |
|---|---|
| `verification-5-3-preflight.md` (CI-2 smoke test) | ✅ Present |
| `security-incident-5-2-redis-transcript.md` | ✅ Present |
| Research reports (`research-reports/phase-5-execution/`) | ✅ Present (7 reports confirmed via planner references) |
| `auditor-gate-5-persona-integrity-post-v2.md` (Auditor 1 v2) | ✅ Present, PASS |
| Auditor 2 v2 (Skills/Runtime) | ⏳ Pending/running |
| Auditor 3 v2 (Rituals/Cron) | ⏳ Pending/running |
| Auditor 4 v2 (Plugin/Redis) | ⏳ Pending/running |
| `batch-plan-phase-5.md` | ❌ Stale (10+ `hermes run --internal` refs) |
| `planner-gate-phase-5-execution.md` v1.0 | ❌ Stale (superseded by v1.1) |

**Verdict: ✅ PASS** (evidence artifacts present). Stale plan docs noted as doc-sync debt (see Part C).

### A.3 Stale `evidence-phase-5.md` — ⚠️ **STALE DRAFT — 9 Issues Identified**

The existing `evidence-phase-5.md` (419 lines, created 2026-06-06 01:47, by Sisyphus-Junior) is a **stale synthesis** written before the v2 verification wave. It contains the following stale/incorrect facts:

| # | Section | Stale Claim | Current Truth | Severity |
|---|---|---|---|---|
| S-01 | G-1 | SOUL.md = 463 lines | **508 lines** (v2 Step 5.1 expanded it) | HIGH |
| S-02 | G-6 | Drift hash `7904fec...8966d` | `b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740` | HIGH |
| S-03 | G-3 | References `crontab.yaml` as active cron mechanism | Cron uses `hermes cron create` — 5 native Hermes jobs; crontab.yaml is reference only | HIGH |
| S-04 | G-4 | "CONDITIONAL PASS — explicit BLOCKED runtime Redis DB5 readback" (citing security guardrails) | **PASS** — 10 persona keys seeded, readback verified via env-sourced password (never printed) | HIGH |
| S-05 | Rollback §7 | Ungated destructive commands (`rm -rf`, `redis-cli DEL`, `cp` overwrite) | All rollback commands need explicit approval per AGENTS.md §7 and planner §15 | MEDIUM |
| S-06 | G-15 | Claims PROGRESS.md SYNCED as PASS | **NEEDS REVIEW** — overclaims "Complete", references stale evidence path | MEDIUM |
| S-07 | G-16 | Claims 5 auditors all PASS/CONDITIONAL | **STALE** — 4 of 5 auditors reference v1 evidence; only v2 persona-integrity-auditor is current | HIGH |
| S-08 | G-17 | Claims "Phase 1 hooks operational" without caveat | **2 hooks exist, not 7** — as-written 7-hook gate criterion FAILS; needs rescope | MEDIUM |
| S-09 | G-15/PROGRESS | Claims PROGRESS.md references current evidence | PROGRESS.md links to stale `evidence-phase-5.md`, not v2 evidence set | MEDIUM |

**Verdict: ⚠️ NEEDS REVIEW** — File must be **rewritten from scratch** using v2 evidence as authoritative source. Patch/edits insufficient given the pervasiveness of stale facts. Parent owns this action.

---

## PART B: PROGRESS.MD AUDIT

### B.1 PROGRESS.md Status

| Check | Finding | Result |
|---|---|---|
| Phase 5 entry exists | ✅ Yes | ✅ PASS |
| Last updated date | 2026-06-06 | ✅ Current |
| ADR-035 Phase 5 sub-steps 5.1-5.8 documented | ✅ Yes | ✅ PASS |
| "Complete" claim | "✅ P0+P1+P2+P3+P4+P5+P5.5+P6+P7+P7.5+P8 Complete — MVP Infrastructure Complete" | ⚠️ **OVERCLAIM** |
| Remaining closure gates | "post-implementation auditor wave, Redis transcript incident disposition by Faiz, deployment/restart, commit/push" | ⚠️ **INCOMPLETE** — missing OG-4 (risk level), OG-6 (deploy), G-17 (hooks) |
| Evidence path referenced | `docs/setup-evidence/phase-5/evidence-phase-5.md` (stale) | ❌ **Stale path** — should reference v2 set |
| 5.8 status | ⚠️ "13 PASS / 2 conditional / 2 blocked / 1 fail before this PROGRESS sync" | ❌ **Incorrect** — actual 5.8 v2 gate count: 16 PASS / 4 NEEDS REVIEW / 2 FAIL / 1 BLOCKED |

### B.2 Specific Overclaims

1. **"P5+P5.5+P6+P7+P7.5+P8 Complete"** — Phase 5 (ADR-035) has unresolved gates: OG-4 (risk MEDIUM not updated), OG-6 (PersonaPlugin not deployed), G-17 (2 vs 7 hooks). Claiming "Complete" is misleading.

2. **"MVP Infrastructure Complete"** — If ADR-035 Phase 5 gates are unresolved, MVP infrastructure cannot be claimed as complete.

3. **References stale `evidence-phase-5.md`** — The only evidence path in the PROGRESS.md Phase 5 table links to the stale synthesis. All v2 verification files are ignored.

**Verdict: ⚠️ NEEDS REVIEW** — Parent must:
- Correct "Complete" claim to "In Progress — Gates Pending" or enumerate actual unresolved gates
- Update evidence path to reference `verification-5-8-v2.md` or a fresh synthesis
- Fix 5.8 status counts
- Include OG-4, OG-6, G-17 in remaining closure gates

---

## PART C: ADR-035 RISK LEVEL AUDIT

### C.1 Risk Level Assessment

| Check | Finding | Verdict |
|---|---|---|
| ADR-035 document-level risk | CRITICAL (correct — migration of safety-critical system) | ✅ PASS |
| Phase 5 specific risk in phase table | **LOW** | ❌ **FAIL (OG-4)** |
| Oracle RF-4 requirement | Phase 5 touches `punishment_engine.py` (L6 boundary), `transition_rules.py`, `mood_persistence.py` → should be MEDIUM | ⚠️ **Not updated** |

The ADR-035 phase table at approximately line 1188 shows:

```
| **Phase 5** | Skills + Persona | 2-3 days | LOW | ...
```

Oracle RF-4 explicitly requires this to be MEDIUM because Phase 5 touches safety-critical FSM boundaries:
- `punishment_engine.py` L6 guard
- `transition_rules.py` cooldown via Redis TTL
- `mood_persistence.py` async session support

**Verdict: ❌ FAIL** — ADR-035 Phase 5 risk level still LOW. Parent must update to MEDIUM with addendum or direct edit.

### C.2 ADR-035 Phase Table — Other Phase 5 References

| Section | Current Claim | Current Truth | Impact |
|---|---|---|---|
| Phase 5 duration | "2-3 days" | 5 days (2026-06-04 to 2026-06-06) | LOW — actual duration exceeds estimate, but ADR is architectural not scheduling |
| Phase 5 scope | "Skills + Persona" | Skills + Persona + SOUL.md + Cron/Rituals + Plugin/Redis Bridge | LOW — scope matches; execution verified |
| Rollback | Per-phase <5 min | All sub-steps <2 min | ✅ Actual rollback faster than ADR estimate |

**Verdict**: Duration discrepancy is informational only. Risk level is the binding finding.

---

## PART D: ROLLBACK GATING AUDIT

### D.1 Rollback Command Safety

The stale `evidence-phase-5.md` §7 contains rollback commands **without explicit approval gates**:

| Component | Command in evidence-phase-5.md | Gated? | Fix Required |
|---|---|---|---|
| SOUL.md | `ssh guinevere-vps "cp ... SOUL.md.bak.pre-phase5 SOUL.md"` | ❌ No | Add `REQUIRES EXPLICIT PER-ACTION APPROVAL` |
| Skills | `ssh guinevere-vps "rm -rf ~/.hermes/skills/guinevere-*"` | ❌ No | Add `REQUIRES EXPLICIT PER-ACTION APPROVAL` |
| Cron | `ssh guinevere-vps "rm ~/.hermes/crontab.yaml && cp ..."` | ❌ No | Add `REQUIRES EXPLICIT PER-ACTION APPROVAL` |
| PersonaPlugin | `rm -rf src/hermes/plugins/` | ❌ No | Add `REQUIRES EXPLICIT PER-ACTION APPROVAL` |

### D.2 Comparison with Planner v1.1 §15

The planner v1.1 §15 correctly labels all destructive rollback commands with:
- Safe preview commands (non-destructive)
- Destructive commands labeled `REQUIRES EXPLICIT PER-ACTION APPROVAL — DO NOT RUN AUTOMATICALLY`

**The stale evidence-phase-5.md lacks this critical safety labeling.** The v2 verification files (5.1-v2 through 5.8-v2) follow the planner's gating pattern correctly, each with explicit approval markers in their §7/Rollback sections.

**Verdict: ⚠️ NEEDS REVIEW** — The stale `evidence-phase-5.md` has ungated rollback commands. The v2 verification files are correctly gated. When parent rewrites `evidence-phase-5.md`, rollback sections must follow the v2/planner gating pattern.

---

## PART E: STALE `hermes run --internal` REFERENCES

### E.1 Active Configs — Clean

| Config | `hermes run` count | Status |
|---|---|---|
| VPS `~/.hermes/config.yaml` | 0 | ✅ Clean |
| VPS `~/.hermes/crontab.yaml` | 0 | ✅ Clean |
| VPS `~/.hermes/SOUL.md` | 0 | ✅ Clean |
| Local `hermes-config/config.yaml` | 0 | ✅ Clean |

### E.2 Stale References in Plan/Evidence Docs

| Document | `hermes run --internal` Count | Status |
|---|---|---|
| `batch-plan-phase-5.md` | **10+** (lines 461, 465, 469, 473, 477, 529, 538, 539, 673, 717) | ❌ STALE |
| `planner-gate-phase-5-execution.md` (v1.0) | Multiple scaffold references | ❌ STALE |
| `planner-gate-phase-5-execution-v1.1.md` | **0** (v1.1 corrected all) | ✅ Clean |
| `evidence-phase-5.md` (stale) | 1 (historical reference documenting vulnerability find-and-fix) | ⚠️ Historical context only |
| `verification-5-6.md` (v1) | 1 (historical reference documenting issue) | ⚠️ Historical context only |
| All v2 verification files | 0 | ✅ Clean |

**Verdict: ⚠️ NEEDS REVIEW** — Active configs are clean. Stale references in `batch-plan-phase-5.md` and `planner-gate-phase-5-execution.md` v1.0 are documentation-only issues. The v1.0 planner is superseded by v1.1. Parent should either clean up `batch-plan-phase-5.md` or accept as historical/deferred.

---

## PART F: V2 AUDITOR COMPLETENESS

### F.1 Current Auditor State

| Auditor | v1 (Stale) | v2 |
|---|---|---|
| A1: Persona Safety | `auditor-gate-5-persona-integrity-post.md` (01:49, v1 paths) | ✅ **`auditor-gate-5-persona-integrity-post-v2.md`** (PASS, current) |
| A2: Skills/Runtime | `auditor-gate-5-skills-post.md` (01:49, v1 paths) | ⏳ Still running/pending |
| A3: Rituals/Cron | `auditor-gate-5-cron-rituals-post.md` (01:49, v1 paths) | ⏳ Still running/pending |
| A4: Plugin/Redis | `auditor-gate-5-personaplugin-post.md` (01:48, v1 paths) | ⏳ Still running/pending |
| A5: ADR/Docs/Evidence | `auditor-gate-5-adr035-post.md` (01:47, v1 paths) | ✅ **This file** (v2, current) |

### F.2 Assessment

- **Auditor 1 (Persona Safety)**: ✅ v2 exists, PASS — no action needed
- **Auditor 5 (ADR/Docs/Evidence)**: ✅ This v2 file — NEEDS REVIEW (7 findings)
- **Auditors 2, 3, 4**: ⏳ Pending — cannot claim G-16 (5 auditors PASS) until these complete and parent verifies

**Verdict: ⚠️ NEEDS REVIEW** — G-16 cannot clear until v2 auditors 2, 3, 4 are completed and verified.

---

## PART G: G-17 HOOK COUNT FINDING

### G.1 Current VPS State

```
ssh guinevere-vps "hermes hooks list"
# Result: 2 hooks
# - pre_tool_call: consent_gate.py (timeout=60s, approved 2026-06-05)
# - post_tool_call: dnr_filter.py (timeout=60s, approved 2026-06-05)
```

### G.2 Planner Expectation vs Reality

| Source | Expected Hooks | Actual |
|---|---|---|
| Planner §12.8 (G-17) | 7 hooks | **2 hooks** |
| Planner §13.8 | 7 hooks via `hermes hooks list` | Not met |

The 7-hook expectation was aspirational from ADR-035 architectural planning. At the current Phase 5 state (pre-bot.py cutover, pre-auth-overlay deployment), exactly 2 hooks is correct for the Phase 1 safety layer that is deployed.

### G.3 Recommendation

- **Pre-go-live (current state)**: Rescope G-17 to "Phase 1 hooks operational: consent_gate + dnr_filter confirmed" (2 hooks). Both are core safety hooks (consent gate fail-closed, DNR filter).
- **Post-cutover target**: 7 hooks remains the architectural target after Hermes gateway cutover (Phase 2), auth overlay deploy (Phase 4), and full safety migration.

**Verdict: ⚠️ FAIL** — As scoped in planner, G-17 fails. As rescoped to current deployment state, it passes. Parent must decide rescope vs. defer resolution.

---

## PART H: COMPLETE FINDING REGISTER

### H.1 Summary of All Findings

| # | Finding | Domain | Severity | Affected Artifact | Required Action |
|---|---|---|---|---|---|
| **F-01** | `evidence-phase-5.md` has 9 stale/incorrect sections (old SOUL line count, old drift hash, old cron assumptions, conditional DB5, ungated rollbacks, overclaimed PROGRESS/auditors/G-17) | Evidence | **HIGH** | `evidence-phase-5.md` | Parent rewrite from v2 evidence set |
| **F-02** | PROGRESS.md overclaims "Complete" status, references stale evidence path, has incorrect 5.8 gate counts | Docs | **MEDIUM** | `PROGRESS.md` | Correct status, update evidence path, fix gate counts |
| **F-03** | ADR-035 Phase 5 risk level still LOW, should be MEDIUM per Oracle RF-4 | ADR | **MEDIUM** | `adr/ADR-035-hermes-migration.md` | Update Phase 5 risk LOW→MEDIUM |
| **F-04** | Stale `evidence-phase-5.md` rollback commands lack approval gates (4 commands: SOUL.md restore, skills rm, cron rm, plugin rm) | Safety | **MEDIUM** | `evidence-phase-5.md` §7 | Use v2/planner gating pattern in rewrite |
| **F-05** | `batch-plan-phase-5.md` contains 10+ stale `hermes run --internal` references | Docs | **LOW** | `batch-plan-phase-5.md` | Clean up or accept as historical/documentation debt |
| **F-06** | G-16 cannot clear: v2 auditors 2/3/4 still pending; only A1 (persona) and A5 (this file) have current v2 reports | Evidence | **HIGH** | G-16 gate | Complete v2 auditor wave for A2/A3/A4; parent verify |
| **F-07** | G-17 as scoped (7 hooks) FAILS; only 2 hooks deployed (correct for current state) | Gate | **MEDIUM** | Planner §12.8 G-17 | Rescope to 2 hooks for pre-go-live or document as deferred |

### H.2 Severity Classification

| Severity | Count | Findings |
|---|---|---|
| **HIGH** | 2 | F-01 (stale evidence), F-06 (pending v2 auditors) |
| **MEDIUM** | 4 | F-02 (PROGRESS), F-03 (risk level), F-04 (ungated rollbacks), F-07 (hook rescope) |
| **LOW** | 1 | F-05 (stale plan docs) |

### H.3 Critical Path to Final Signoff

```
1. [PARENT] Rewrite evidence-phase-5.md from v2 evidence set ─────────────────┐
2. [PARENT] Update ADR-035 Phase 5 risk LOW→MEDIUM ───────────────────────────┤
3. [AUDITOR] Complete v2 auditor wave for A2/A3/A4 ───────────────────────────┤
4. [PARENT] Verify all 5 v2 auditors PASS ────────────────────────────────────┤
5. [PARENT] Update PROGRESS.md (correct status, evidence path, gate counts) ───┤
6. [PARENT] Resolve G-17 hook count (rescope or accept FAIL) ─────────────────┤
7. [OPTIONAL] Clean up batch-plan-phase-5.md stale refs ──────────────────────┘
                                         │
                    [All v2 auditors PASS + evidence current + ADR updated]
                                         ▼
                              ╔══════════════════════╗
                              ║   FINAL SIGNOFF READY ║
                              ╚══════════════════════╝
                                         │
                    [Deploy PersonaPlugin + Hermes restart]
                    [Commit/push (requires Faiz approval)]
                    [Final report]
```

---

## PART I: BOUNDARY COMPLIANCE

| Domain | Status | Evidence |
|---|---|---|
| PersonaSafetyPolicy | ✅ Preserved | Y4 baseline, Y5 ceiling, Y6 PROHIBITED, HARD STOP 9-step, D0-D4, F-01-F-15 all intact |
| Consent/Surveillance | ✅ Preserved | `fallback_on_timeout: deny`, consent gate delegated to safety plugin |
| HARD STOP Protocol | ✅ Preserved | safe_mode.py KEEP VERBATIM, SOUL.md §D, hardstop skill |
| Secrets Exposure | ✅ Contained | Redis password sourced from `.env.surveillance`, never printed; incident documented and accepted |
| No Type Suppression | ✅ PASS | 0 `# type: ignore`, `@ts-ignore`, `as any` in any Phase 5 modified file |
| No Empty Catches | ✅ PASS | 0 bare `except:` in any Phase 5 modified file |
| Midnight Discord Isolation | ✅ PASS (CRITICAL) | `Deliver: local`, triple-layer suppression verified |
| KEEP VERBATIM Files | ✅ Preserved | yandere_fsm.py, safe_mode.py, drift_corrector.py — zero diff. drift_detector.py — hash-only change. |
| ADR-035 5 Pillars | ✅ Architecture compliant | Discord=not migrated yet (Phase 2), Memory=HYBRID preserved, Safety=HOOKS+PLUGINS, MCP=HYBRID, LLM=9Router unchanged |
| ADR Binding Constraints (9) | ✅ All satisfied | ADR-007, ADR-005, ADR-013, ADR-001, PersonaSafetyPolicy, ADR-002, FinOps, Infrastructure, Data Governance |

**No boundary violations found. All 15+ safety features preserved or enhanced.**

---

## PART J: ACCEPTANCE CRITERIA MAPPING

| Criterion | Verdict |
|---|---|
| Auditor ran independent assessment (not self-audit) | ✅ PASS — independent read-only verification |
| All 8 v2 verification files exist and are current | ✅ PASS |
| Stale `evidence-phase-5.md` audited, all stale sections identified | ✅ PASS — 9 stale sections (F-01) |
| PROGRESS.md overclaims identified | ✅ PASS — 3 overclaims (F-02) |
| ADR-035 risk level audited | ✅ PASS — identified as FAIL (OG-4) (F-03) |
| Rollback commands checked for approval gating | ✅ PASS — stale file ungated; v2 files correct (F-04) |
| `hermes run --internal` staleness checked across all artifacts | ✅ PASS — active configs clean; 2 stale plan docs (F-05) |
| V2 auditor completeness assessed | ✅ PASS — A1 v2 done; A2/A3/A4 pending (F-06) |
| G-17 hook count discrepancy identified | ✅ PASS — 2 vs 7 (F-07) |
| Clear fix list provided for parent | ✅ PASS — §H.3 critical path |
| No secrets exposed in this report | ✅ PASS |
| No false PASS claims | ✅ PASS — 7 findings honestly reported |

---

## PART K: FOOTER

### Verdict Chain

| Gate | Purpose | This Auditor's Verdict |
|---|---|---|
| G-14 | Evidence files created | ⚠️ NEEDS REVIEW — files exist but `evidence-phase-5.md` is stale (F-01) |
| G-15 | PROGRESS.md synced | ⚠️ NEEDS REVIEW — overclaims status, stale evidence path (F-02) |
| G-16 | 5 auditors PASS | ⚠️ NEEDS REVIEW — only A1 + A5 v2 done; A2/A3/A4 pending (F-06) |
| OG-4 | ADR-035 risk = MEDIUM | ❌ FAIL — still LOW (F-03) |
| **Overall ADR/Docs/Evidence** | All ADR/docs/evidence compliance | ⚠️ **NEEDS REVIEW** — 7 findings (2 HIGH, 4 MEDIUM, 1 LOW) |

### Fix List Summary (Parent)

| Priority | Action | Reference |
|---|---|---|
| 🔴 **HIGH** | Rewrite `evidence-phase-5.md` from v2 evidence set (9 stale sections) | F-01 |
| 🔴 **HIGH** | Complete/collect A2/A3/A4 v2 auditor outputs; verify all 5 PASS | F-06 |
| 🟡 **MEDIUM** | Update ADR-035 Phase 5 risk LOW→MEDIUM | F-03 |
| 🟡 **MEDIUM** | Update PROGRESS.md: correct status, evidence path, gate counts | F-02 |
| 🟡 **MEDIUM** | Ensure rollback commands in rewritten evidence have approval gates | F-04 |
| 🟡 **MEDIUM** | Rescope G-17 to 2 hooks for pre-go-live or document deferral | F-07 |
| 🟢 **LOW** | Clean up `batch-plan-phase-5.md` stale `hermes run` refs (10+) | F-05 |

### Key Evidence Paths

```
# Authoritative v2 evidence set (current):
docs/setup-evidence/phase-5/verification-5-1-v2.md                    — SOUL.md Oracle (508 lines)
docs/setup-evidence/phase-5/verification-5-2-v2.md                    — Drift baseline (b8d55fe...)
docs/setup-evidence/phase-5/verification-5-3-content-reconciliation.md  — Skills content verification
docs/setup-evidence/phase-5/verification-5-4-v2.md                    — Plugin/Redis bridge
docs/setup-evidence/phase-5/verification-5-5-v2.md                    — Hermes cron rituals
docs/setup-evidence/phase-5/verification-5-6-v2.md                    — Ritual verification
docs/setup-evidence/phase-5/verification-5-7-v2.md                    — Persona migration
docs/setup-evidence/phase-5/verification-5-8-v2.md                    — Final 18-gate refresh

# v2 auditor files (current):
docs/setup-evidence/phase-5/auditor-gate-5-persona-integrity-post-v2.md  — A1: Persona (PASS)
docs/setup-evidence/phase-5/auditor-gate-5-adr035-post-v2.md             — A5: ADR/Docs (THIS FILE, NEEDS REVIEW)

# Stale (do not trust):
docs/setup-evidence/phase-5/evidence-phase-5.md                          — 9 stale sections, needs rewrite
docs/setup-evidence/phase-5/auditor-gate-5-adr035-post.md                — Pre-v2, superseded by this v2
docs/setup-evidence/phase-5/auditor-gate-5-skills-post.md                — v1, pending v2
docs/setup-evidence/phase-5/auditor-gate-5-cron-rituals-post.md          — v1, pending v2
docs/setup-evidence/phase-5/auditor-gate-5-personaplugin-post.md         — v1, pending v2
docs/setup-evidence/phase-5/batch-plan-phase-5.md                        — 10+ stale hermes run refs
docs/setup-evidence/phase-5/planner-gate-phase-5-execution.md            — Superseded by v1.1
```

### Version

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-06 | Sisyphus-Junior | v2 ADR/Docs/Evidence auditor gate for ADR-035 Phase 5 — 7 findings: 2 HIGH, 4 MEDIUM, 1 LOW |

---

> **Auditor Gate 5 (v2): ADR/Docs/Evidence** | Guinevere Autonomous Engineering | 2026-06-06
> **Verdict: ⚠️ NEEDS REVIEW** — 7 genuine findings before final signoff. See §H.3 for critical path.
> **Overall Phase 5 status**: Implementation PASS (8/8 v2 verification files). Evidence/Docs/ADR cleanup required.
> **Next**: Parent to execute fix list, collect remaining v2 auditor outputs, then final signoff.
