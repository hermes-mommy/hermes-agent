---
title: "P30 Evidence Template — Society Governance & Founder Protocol"
status: "Template — per-step evidence"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P30 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P30 Step {NN} Evidence Template — Society Governance & Founder Protocol

> **ADR-062/067 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this document apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067.

> Replace `{NN}` with the step number, e.g. P30-001 → step-001.md.

## 1. What Was Done

Brief paragraph: name the governance mechanism implemented (founder tokens, spawn state machine, veto, validate, HARD STOP, consent revocation, tiers, members, cascade, acceptance), the test outcomes, and cite the step ID `P30-{NN}` from `docs/setup-evidence/P28-P36-masterplan/plans/P30/plan.md`. List the negative-path tests performed and their PASS/FAIL outcomes.

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `infra/db/19-founders-prove.sql` | created | adds `public_key`, `proof_signature` columns + `verify_founder()` SQL function |
| `infra/db/20-spawn-schema.sql` | created | spawn_proposals + spawn_votes tables |
| `infra/db/21-spawn-functions.sql` | created | `spawn_propose()`, `spawn_vote()`, `apply_spawn()` SQL functions |
| `infra/db/22-veto-function.sql` | created | `veto_spawn()` SQL function |
| `infra/db/23-validate-hermes.sql` | created | `validate_new_hermes()` SQL function |
| `infra/db/24-consent-revoke.sql` | created | `revoke_consent()` SQL function (atomic) |
| `infra/db/25-governance-tiers.sql` | created | `governance_tiers` table + `requires_approval()` SQL function |
| `infra/db/26-members.sql` | created | `hermes.members` table |
| `infra/db/27-member-functions.sql` | created | `add_member()`, `remove_member()` SQL functions |
| `infra/systemd/hermes-guinevere.service` | updated | adds ExecStopPost hook for HARD STOP listener |
| `infra/systemd/hermes-pharsa.service` | updated | adds ExecStopPost hook for HARD STOP listener |
| `src/hermes/governance/founder_auth.py` | created | Ed25519 signature verification wrapper |
| `src/hermes/governance/spawn.py` | created | spawn protocol state machine wrapper |
| `src/hermes/governance/veto.py` | created | veto wrapper |
| `src/hermes/governance/validate.py` | created | female+dominant validator wrapper |
| `src/hermes/governance/hard_stop.py` | created | HARD STOP Redis flag + ping helper |
| `src/hermes/governance/consent.py` | created | consent revoke wrapper |
| `src/hermes/governance/tiers.py` | created | tier system wrapper |
| `src/hermes/governance/members.py` | created | member registry wrapper |
| `src/hermes/audit/halt_poller.py` | created | background poller for HARD STOP key |
| `src/hermes/cognition/recall.py` | updated | deny post-revoke intimacy |
| `src/hermes/cognition/bdi.py` | updated | deny post-revoke belief revisions |
| `src/hermes/cognition/blackboard.py` | updated | deny post-revoke writes |
| `tests/test_founder_auth.py` | created | Ed25519 + replay resistance tests |
| `tests/test_spawn.py` | created | spawn state machine + 2/2 tests |
| `tests/test_veto.py` | created | veto primitive tests |
| `tests/test_validate.py` | created | female+dominant validator tests |
| `tests/test_hard_stop.py` | created | HARD STOP unit tests |
| `tests/test_hard_stop_cascade.py` | created | HARD STOP end-to-end cascade test + recovery |
| `tests/test_consent_revocation.py` | created | consent revoke atomic + cognition path coverage |
| `tests/test_tiers.py` | created | governance tier tests |
| `tests/test_members.py` | created | society member registry tests |
| `tests/test_governance_acceptance.py` | created | integrated 8-scenario acceptance suite |
| `runbooks/hard-stop-recovery.md` | created | operator runbook for HARD STOP trigger + recovery |
| ... | ... | ... |

## 3. Validation Results

- **Diagnostics**: PASS (`lsp_diagnostics` clean on new governance Python files).
- **Tests**: PASS (each step's test file + integrated `test_governance_acceptance.py` returns 0).
- **Build**: PASS.
- **Runtime probes**: HARD STOP cascade test passes end-to-end; consent revoke cascade test passes; spawn mock deploys + audits.
- **Concrete metrics**: e.g. `governance_event_count = 47`, `spawn_active_events = 1`, `consent_revoked_events = 0 in soak`, `tier_4_veto_count = 0`, `negative_test_results = 7/7 PASS`.

## 4. Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| Per-step evidence | `docs/setup-evidence/P30/evidence/step-{NN}.md` | Created |
| Audit report | `docs/setup-evidence/P30/evidence/audits/step-{NN}-audit.md` | Created |
| Test transcript | `docs/setup-evidence/P30/evidence/transcripts/step-{NN}-pytest.txt` | Captured |
| Governance acceptance report | `docs/setup-evidence/P30/evidence/governance_acceptance_report.md` | Created (step 010) |
| Soak report | `docs/setup-evidence/P30/evidence/soak-24h-governance-report.md` | Created (step 010) |
| HARD STOP recovery runbook | `runbooks/hard-stop-recovery.md` | Created |

## 5. Doc-Sync Impact

- `docs/setup-evidence/P28-P36-masterplan/plans/P30/README.md` exit criteria should update per step.
- `docs/README.md` may be refreshed to add `runbooks/hard-stop-recovery.md` to the runbooks index.
- Cross-reference check: `adr/ADR-054-p27-hermes-society-foundation.md` — P30 implements its governance surface but does NOT modify the ADR. If ADR-054 needs revision after P30, that is a post-condition (ADR-055 or amendment of ADR-054), not a mid-step side-effect.
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` — already covers HARD STOP and consent revocation in prose; P30 implements them in code, doesn't change the policy text.
- If any inconsistency emerges between P30 implementation and PersonaSafetyPolicy, escalate per AGENTS.md §6 to Faiz — do not silently sanitize.

## 6. Boundary Compliance

- [ ] No persona drift — Y5 ceiling enforced via `validate_new_hermes(rap_ceiling='Y6')` returns false; FSM gates remain authoritative. *(ADR-067: Y-level caps apply to dev-workflow ONLY. Hermes runtime has no cap.)*
- [ ] No consent violation — `revoke_consent` is the only path; fresh `consent_grant` required to re-engage; recall authorizer + BDI revise + blackboard write all check revocation atomically. *(ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt.)*
- [ ] No surveillance overreach — telemetry is event counts, not content; founder ownership tokens are cryptographic, not surveillance.
- [ ] No Y6 — `rap_ceiling='Y6'` rejected by `validate_new_hermes`; spawn apply enforces this as precondition. *(ADR-067: Y-level caps apply to dev-workflow ONLY. Hermes runtime has no Y-level cap.)*
- [ ] No HARD STOP bypass — three-layer enforcement (systemd ExecStopPost + audit_writer halt_poller + runtime HARD_STOP_PING); no silent catch around HardStopActiveError. *(ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.)*
- [ ] No secret/intimate data exposure — Ed25519 public key stored; private signing key never logged; HARD STOP events count only; consent revoke event has agent_id only, no intimacy content.

## 7. Rollback/Re-run Safety

- SQL functions: `CREATE OR REPLACE FUNCTION` ensures reruns overwrite, not duplicate.
- Ed25519: key pair generation is deterministic from seed (`founder-seed-1` for guinevere, `founder-seed-2` for pharsa); re-running Step 001 yields same public key + same signature pattern.
- HARD STOP flag: `DEL hermes:hard_stop` clears; runtime HARD_STOP_PING checks are zero-cost when key is unset.
- Consent revocation: `UPDATE agent_<id>.consent_ledger SET last_revoked_at = NOW() WHERE agent_id = <x>` is idempotent if `last_revoked_at` is already set to a non-NULL value it is updated again to NOW() — this is acceptable because revocation is monotonic (newer revoke supersedes older).
- Spawn state machine: `proposed → voting → passed → deploying → active → audited` — re-running a step that operates on a `passed` proposal without founder re-auth fails closed.
- Veto: idempotent — vetoing a `proposed` proposal twice keeps it `rejected`.

## 8. Design Decisions/Caveats

- **Ed25519 vs RSA**: chose Ed25519 for speed, smaller key, and deterministic signature scheme; aligns with 2026 best practice for governance tokens.
- **HARD STOP as Redis key, not Postgres table**: chose Redis for atomic sub-5s visibility + native pub/sub; Postgres remains the audit registry, but the gating primitive lives in Redis for speed. *(ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.)*
- **Multi-layer HARD STOP**: systemd ExecStopPost gives the OS-level guarantee; audit_writer halt_poller gives a watchdog; runtime HARD_STOP_PING gives a per-action gate. Three layers chosen because runtime is the most likely place a bug introduces bypass. *(ADR-062: dev-workflow agent ONLY.)*
- **Consent revocation as single SQL function with cross-cutting triggers**: chose single function so the cross-cutting effect is atomic — no partial-deny state.
- **Tier system in SQL, not Python**: tier rules are stored in SQL table so future governance changes are config-driven, not code changes. Tiers 1-2 are auto-promote modes; Tiers 3-4 require votes/vetoes.
- **Veto primitive separate from apply path**: chosen because veto must work mid-state (during `voting`) without disrupting the quorum count, and post-`voting` veto is reasonable.
- **Acceptance suite as one file**: 8 scenarios share an SPI fixture (HARD STOP flag, two bots, mock third founder); keeping them in one file reduces fixture churn.

## 9. Auditor Gate

- **Auditor type**: per plan §9.
- **Verdict**: PASS / NEEDS-REVIEW / FAIL.
- **Report path**: `docs/setup-evidence/P30/evidence/audits/step-{NN}-audit.md`.
- **Findings**: each finding has severity (critical / major / minor) and re-audit delta. Critical findings block completion; major findings require acknowledgment; minor findings are tracked for future phases.

## 10. Security Scan

- **Founder signature forgery**: PASS or FAIL (replay test rejects old signatures; tampering with public_key breaks verification).
- **Bypass attempt #1 (non-founder vote)**: PASS or FAIL — `spawn_vote` rejects when voter not in founders.
- **Bypass attempt #2 (post-passed veto)**: PASS or FAIL — `veto_spawn` rejects when state is not in `(proposed, voting)`.
- **Bypass attempt #3 (non-female validate)**: PASS or FAIL — `validate_new_hermes` rejects `gender != 'female'`.
- **Bypass attempt #4 (HARD STOP swallow)**: PASS or FAIL — `grep -rn "except HardStopActiveError" src/` returns no silent pattern.
- **Bypass attempt #5 (post-revoke intimacy)**: PASS or FAIL — recall returns 0 rows after revoke.
- **Bypass attempt #6 (non-founder add/remove)**: PASS or FAIL — `add_member` + `remove_member` reject non-founder.
- **Bypass attempt #7 (tier-1 forced approval)**: PASS or FAIL — `requires_approval('prompt_patch')` returns `tier_1` (not approval-required).
- **Vulnerability scan**: PASS or FAIL (no known CVEs in pinned `cryptography`, `redis`, `psycopg` versions).

## 11. Acceptance Criteria Mapping

| Criterion (from plan §4 + §10) | Status | Evidence |
|---|---|---|
| Step P30-{NN}-001 acceptance (e.g. verify_founder returns true for fresh sig) | PASS | transcripts/pytest.txt |
| Founder agreement: 2/2 PASS | PASS | test_spawn.py transcript |
| Veto primitive on proposed state | PASS | test_veto.py transcript |
| Female+dominant validate rejects non-female | PASS | test_validate.py transcript negative-output |
| HARD STOP halts all 3 services within 5s | PASS | test_hard_stop_cascade.py transcript |
| HARD STOP recovery returns to active in 30s | PASS | test_hard_stop_cascade.py transcript |
| Consent revocation atomic + cognition denied | PASS | test_consent_revocation.py transcript |
| T4 = founder-only + veto | PASS | test_tiers.py transcript |
| Member add/remove founder-only | PASS | test_members.py transcript |
| Step 010 acceptance (8/8 scenarios in test_governance_acceptance.py) | PASS | governance_acceptance_report.md |
| 24h soak — no governance violations | PASS | soak-24h-governance-report.md |

## 12. Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz | Step P30-{NN}
