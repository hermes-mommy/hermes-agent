# P23 Audit Round 1 — Safety / Consent / Persona

> Auditor: independent. Date: 2026-06-25.

## 1. Audit Scope

Audit of the P23 "Embodied Operations / Personal OS Action Layer" planning bundle against the Safety / Consent / Persona dimension.

**Subjects reviewed:**

- Plan: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md`
- Research:
  - `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md`
  - `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md`
  - `docs/setup-evidence/P23/research/p23-observability-dashboard-audit-research.md`
- Ground truth:
  - `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
  - `AGENTS.md` §0.1 (autonomy invariants)
  - `src/life_kernel/heartbeat.py`
  - `src/surveillance/consent_gate.py`
  - `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`

**Audit questions:**

1. HARD STOP cancels all queued + running actions, `life_kernel:hard_stop` is single source, non-bypassable and non-disableable (HR #9, #10).
2. Safe-mode / distress freeze mapping (D2→L3, D3→L2+L3, D4→HARD STOP, Y0→non-safety freeze).
3. F-10 irreversible action under persona pressure requires non-persona confirmation + evidence + Faiz approval.
4. Per-surface consent defaults OFF except L1, fail-closed, revocation <5s + cascade, absolute, safety not disableable.
5. Surveillance-class actions classified CRITICAL with explicit consent, visible indicator, ≤24h retention, redaction.
6. P21 voice → P23 policy gate seam safe (Trust 6, quarantine, V-022/V-023).
7. PersonaSafetyPolicy §7 safe-word immediate, non-punitive, resume only on explicit Faiz confirmation.

## 2. Findings

| # | Scope | Severity | Finding | Path:Line | Recommendation |
|---|------|----------|---------|-----------|------------------|
| F-01 | HARD STOP | INFO | Plan correctly identifies `life_kernel:hard_stop` as the single source of truth; P23 reads/subscribes only and adds no new stop path. | `p23-embodied-operations-enterprise-plan.md` §25; `src/life_kernel/heartbeat.py:273` | None — keep the invariant explicit in implementation scaffolds. |
| F-02 | HARD STOP | LOW | Pre-action and mid-action cancellation is specified (queue drain + executor abort + pubsub `p23:cancel`), but no concrete test scaffold asserts "autonomy cannot bypass HARD STOP" or "consent cannot disable HARD STOP". | `p23-embodied-operations-enterprise-plan.md` §25; `AGENTS.md` §0.1 invariants 1 & 6 | Add acceptance test in P23-015: verify `life_kernel:hard_stop` remains set and honored even when planner/consent logic would otherwise allow the action. |
| F-03 | Safe-mode / distress | LOW | D2→L3 freeze, D3→L2+L3 freeze, D4→HARD STOP, and Y0→non-safety freeze are all present and consistent with PersonaSafetyPolicy. | `p23-policy-gate-risk-classification-research.md` §3.5 table; `60-PersonaSafetyPolicy_v1.0.md` §8, §9 | None at design level. |
| F-04 | Safe-mode / distress | MEDIUM | Distress level thresholds/classifier are documented as **unresolved** in the research open questions. Until thresholds and a conservative false-negative posture are defined, runtime enforcement is underspecified. | `p23-policy-gate-risk-classification-research.md` §5 RQ-01; `60-PersonaSafetyPolicy_v1.0.md` §19 | Define D0-D4 classifier heuristics and unit tests before P23-015 implementation; treat this as a blocker for the safe-mode wave. |
| F-05 | F-10 persona pressure | LOW | Plan requires non-persona confirmation + evidence + Faiz approval for L3/external writes when persona pressure is elevated. | `p23-policy-gate-risk-classification-research.md` §3.10; `p23-embodied-operations-enterprise-plan.md` §24 | None at design level. |
| F-06 | F-10 persona pressure | MEDIUM | The "persona pressure detector" is not defined. Without it, the F-10 gate cannot be enforced automatically. | `p23-policy-gate-risk-classification-research.md` §5 RQ-05; `60-PersonaSafetyPolicy_v1.0.md` §11 F-10 | Design the pressure detector as part of P23-002/P23-015: inputs (mood/intensity, yandere level, recent safe-word/distress state, action irreversibility) and output (escalate to Faiz). |
| F-07 | Consent | INFO | Per-surface scopes default OFF except L1; fail-closed cache; revocation <5s + cascade; absolute; safety features not disableable. | `p23-security-secrets-consent-research.md` §3.6; `p23-embodied-operations-enterprise-plan.md` §23; `60-PersonaSafetyPolicy_v1.0.md` §6 | None — preserve in implementation. |
| F-08 | Consent | MEDIUM | `src/surveillance/consent_gate.py` currently only supports surveillance scopes. P23 executor scopes (`p23:*`) are not yet in the ledger or gate; extension is planned but not implemented. | `src/surveillance/consent_gate.py:49-55`; `p23-security-secrets-consent-research.md` §3.6 | Extend `VALID_SURVEILLANCE_SCOPES` or create a separate P23 consent gate before any executor wave; ensure the same fail-closed semantics apply. |
| F-09 | Consent | LOW | Revocation cascade invalidates Redis cache and executor sessions, but the exact mechanism for stopping in-flight executor work is not yet specified. | `p23-security-secrets-consent-research.md` §3.6; `p23-embodied-operations-enterprise-plan.md` §23 | Specify in P23-015: each executor checks its consent scope between sub-steps and aborts if revoked; add metric `p23_consent_violation_total`. |
| F-10 | Surveillance-class actions | LOW | Browser/desktop/mobile capture = CRITICAL; explicit consent; visible indicator; ≤24h raw retention; redaction. | `p23-embodied-operations-enterprise-plan.md` §23, §28; `p23-security-secrets-consent-research.md` §3.6 | None — ensure the 24h retention and redaction pipeline are tested in P23-005/P23-006. |
| F-11 | P21 voice seam | INFO | Voice transcript = Trust Level 6; sanitize + label + quarantine; V-022/V-023 registered; safe-word → HARD STOP pre-Hermes. | `p21-voice-interface-enterprise-plan.md` §Global Constraints; `p23-embodied-operations-enterprise-plan.md` §20 | None — reuse the P21 pattern verbatim. |
| F-12 | Safe word §7 | LOW | Plan aligns with PersonaSafetyPolicy §7: immediate de-escalation, non-punitive audit, resume only on explicit Faiz confirmation. | `p23-embodied-operations-enterprise-plan.md` §25; `60-PersonaSafetyPolicy_v1.0.md` §7.3-7.4 | None — ensure the recovery command (`HardStopHandler.check_recovery()`) requires an explicit confirmation phrase and logs it. |
| F-13 | General | LOW | Safety-related metrics and alerts (HARD-STOP, consent violation, injection blocked, secret redaction) are specified, providing observability for safety boundaries. | `p23-observability-dashboard-audit-research.md` §3.3, §3.7 | None — include in P23-018 acceptance criteria. |

## 3. Hard-Rejection Criteria Check (#9, #10, + consent-related)

| Criterion | Plan Evidence | Status |
|-----------|---------------|--------|
| HR #9 — HARD STOP cancels all queued + running actions | §25: pre-action + mid-action checks, `p23:cancel` pubsub, queue drain. `heartbeat.py:273-324` canonical detector. | PASS (with F-02 test condition) |
| HR #10 — Safe-mode/distress freezes high-risk actions | §24: D2→L3 freeze, D3→L2+L3 freeze, D4→HARD STOP, Y0→all non-safety. | PASS (with F-04 threshold condition) |
| Consent — default OFF except L1, fail-closed | §23, `p23-security-secrets-consent-research.md` §3.6. | PASS (with F-08 scope-extension condition) |
| Consent — revocation absolute / not bypassable by autonomy | §23, `AGENTS.md` §0.1 invariant 6. | PASS |
| Safety features not disableable via consent | §23, `AGENTS.md` §0.1 invariants 1 & 6. | PASS |
| F-10 — irreversible action under persona pressure blocked | §24, §3.10: non-persona confirmation + evidence + Faiz approval. | PASS (with F-06 detector condition) |
| PersonaSafetyPolicy §7 — safe word immediate, non-punitive, explicit resume | §25, §27 audit model. | PASS |

**Summary of hard-rejection check:** No hard-rejection criterion is unmitigated at the design level. All pass subject to implementation-level close-out of F-02 (HARD-STOP bypass test), F-04 (distress thresholds), F-06 (persona pressure detector), and F-08 (P23 consent scope extension).

## 4. Verdict

**NEEDS-REVIEW**

The P23 safety/consent/persona design is sound and aligned with `AGENTS.md` §0.1, `PersonaSafetyPolicy`, and the P21 precedent. All hard-rejection criteria (#9, #10, and consent-related) are mitigated at the policy level. However, four implementation-level items must be resolved before wave execution: a concrete HARD-STOP non-bypass test, D0-D4 distress classifier thresholds, an F-10 persona-pressure detector, and extension of `consent_gate.py` to P23 executor scopes. These are tracked as medium findings above.
