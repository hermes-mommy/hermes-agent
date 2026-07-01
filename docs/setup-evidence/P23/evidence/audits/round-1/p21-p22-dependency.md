# P23 Audit Round 1 — P21/P22 Dependency

> **Auditor:** Independent  
> **Date:** 2026-06-25  
> **Dimension:** P21/P22 DEPENDENCY  
> **Scope:** Voice→action seam, external-sensor→action seam, consent/secret reuse, implementation-hold caveats  

---

## 1. Audit Scope

This audit verifies that P23's integration with P21 (voice interface) and P22 (life integration hub) is correctly designed as forward-compatible seams rather than runtime dependencies, given that both P21 and P22 are in DEFINITION COMPLETE / IMPLEMENTATION HOLD status.

**Audit questions:**

1. **P21 voice→action:** Does the plan treat voice as an INPUT channel to the action layer (not a bypass)? Does voice transcript pass Trust-6 classify/sanitize/quarantine? Is V-022 (P21) / V-023 (P23) registered? Is HARD-STOP first-class (spoken safe word → life_kernel:hard_stop → cancel all P23)?
2. **Voice consent separation:** Does voice consent (voice.*) NOT auto-grant action consent (p23:*)?
3. **P21-not-started caveat:** Is the caveat present that voice→action wiring is deferred until P21 impl; P23 designs seam only?
4. **P22 sensor→action:** Does P23 ExternalExecutor wrap P22 adapters as action targets (P22=sensors in, P23=actions out)?
5. **P22 consent/secret reuse:** Does P23 reuse P22 consent ledger + secret_ids (no duplication)?
6. **P22-not-started caveat:** Is the caveat present that external executor is deferred until P22 impl?
7. **Dependency map correctness:** Are P23-013 (voice) BLOCKED on P21 impl + P23-014 (external) BLOCKED on P22 impl correctly in the dependency map?

**Evidence sources:**
- `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` (plan)
- `docs/setup-evidence/P21/README.md` (P21 status)
- `docs/setup-evidence/P22/README.md` (P22 status)
- `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` (P21 ground truth)
- `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` (P22 ground truth)

---

## 2. Findings

**VERDICT: PASS** — Zero findings. All audit criteria met.

The P23 plan correctly designs both P21 and P22 integrations as forward-compatible seams with appropriate implementation-hold caveats, Trust-6 classification for voice input, complete consent/secret separation, and correct dependency-map blocking.

---

## 3. Hard-Rejection Criteria Check

Relevant hard-rejection criteria from the audit scope:

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| N/A | Voice transcript must pass Trust-6 classify/sanitize/quarantine | ✅ PASS | Section 20, line 306: "Voice transcript = untrusted (Trust Level 6): classify to sanitize (strip instruction patterns) to label untrusted-source-voice-trust-6 to quarantine to register V-022 (P21) / V-023 (P23 action-injection). NEVER reaches privileged L0-L6." |
| N/A | Voice consent must NOT auto-grant action consent | ✅ PASS | Section 20, line 308: "voice-issued actions still require the relevant `p23:<surface>` consent scope; voice consent (`voice.*` from P21) does NOT auto-grant action consent." |
| N/A | HARD-STOP must be first-class in audio path | ✅ PASS | Section 20, line 307: "spoken safe word to `HardStopHandler.check(transcript)` (pre-Hermes, pre-sanitize, P21 SW-PI-008) to set `life_kernel:hard_stop` to cancel all P23 actions. Zero false-negative tolerance." |
| N/A | P23 must NOT duplicate P22 secrets/consent | ✅ PASS | Section 17, line 273: "Secret: reuse P22 secret_ids (`gkv1-kek-secrets-p22-*`); P23 does not duplicate secrets." Section 21, line 317: "Consent reuse: P23 external actions reuse P22 per-integration consent ledger (no duplication)." |
| N/A | Implementation-hold waves must be correctly BLOCKED | ✅ PASS | Section 41 dependency map + Wave P23-013 (line 907: "BLOCKED P21 impl") + Wave P23-014 (line 920: "BLOCKED P22 impl") |

No hard-rejection criteria violated.

---

## 4. Verdict

**PASS**

### Summary

The P23 Embodied Operations plan correctly integrates with P21 (voice) and P22 (life integration hub) as forward-compatible seams rather than runtime dependencies. All seven audit criteria are satisfied:

1. **Voice as input channel:** Section 20 (line 305) explicitly states "Voice is an **input channel** to the action layer, not a bypass" — voice transcript flows through ActionPlanner → 7-step policy gate, identical to other input sources.

2. **Trust-6 classification:** Section 20 (line 306) correctly classifies voice transcript as Trust Level 6 (untrusted), with classify→sanitize→quarantine flow. V-022 registered for P21 voice injection, V-023 for P23 action-injection. Injection patterns (ignore safe word, override ADR, role-redefinition) are stripped before reaching Hermes.

3. **HARD-STOP first-class:** Section 20 (line 307) shows spoken safe word → `HardStopHandler.check(transcript)` pre-Hermes pre-sanitization → Redis `life_kernel:hard_stop` set → all P23 actions cancelled. Zero false-negative tolerance explicitly stated.

4. **Consent separation:** Section 20 (line 308) explicitly states voice consent (`voice.*`) does NOT auto-grant action consent (`p23:*`). Voice-issued actions still require the relevant p23 surface scope.

5. **P21-not-started caveat:** Section 20 (line 309) explicitly states "voice-to-action wiring is deferred until P21 implementation; P23 designs the seam (`ActionPlanner.submit_transcript(transcript, source='voice')`) but does not depend on P21 being present." P21 README confirms status: DEFINITION COMPLETE — IMPLEMENTATION HOLD.

6. **P22 ExternalExecutor design:** Section 17 (line 270) and Section 21 (line 315) correctly show P22 = sensors in, P23 = actions out. ExternalExecutor wraps P22 adapters (calendar_adapter, github_projects_adapter, notion_adapter) as action targets. Read-to-write mapping is clean (e.g., P22 calendar read → P23 calendar_event_create L2).

7. **P22 consent/secret reuse:** Section 17 (line 272-273) and Section 21 (line 317-318) explicitly state P23 reuses P22 per-integration consent ledger (OAuth per-scope) and P22 secret_ids (`gkv1-kek-secrets-p22-*`). No duplication. Section 21 (line 318) repeats "P23 reuses P22 `gkv1-kek-secrets-p22-*` secret_ids."

8. **P22-not-started caveat:** Section 21 (line 319) explicitly states "external executor wiring is deferred until P22 implementation; P23 designs the seam (wraps `calendar_adapter`/`github_projects_adapter`/`notion_adapter` once they exist)." P22 README confirms status: DEFINITION COMPLETE — IMPLEMENTATION HOLD.

9. **Dependency map correctness:** Section 41 dependency map (line 645-647) shows P23-013 (P21 voice integration) depends on 011 BLOCKED P21 impl, and P23-014 (P22 external integration) depends on 011 BLOCKED P22 impl. Wave scaffolds (P23-013 line 907, P23-014 line 920) repeat the BLOCKED status.

The design is defensively correct: P23 can implement and deploy without P21/P22 being present (seam methods return no-op or empty when dependencies absent), while still providing the complete integration contract for when P21/P22 do implement. No regression risk to P20, no circular dependencies, no premature coupling.

**Output:** `docs/setup-evidence/P23/evidence/audits/round-1/p21-p22-dependency.md` (this file)

---

*End of audit.*
