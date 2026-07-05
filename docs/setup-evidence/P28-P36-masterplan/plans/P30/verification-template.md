---
title: "P30 Verification Template — Society Governance & Founder Protocol"
status: "Template — per-step verification scaffold"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P30 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P30 Verification Template — Society Governance & Founder Protocol

> **ADR-062/067 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this document apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067.

## Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P30-001 | infra/db/19-founders-prove.sql; src/hermes/governance/founder_auth.py; tests/test_founder_auth.py | non-Ed25519 signatures; replay window > 1 min; plaintext private keys | `pytest test_founder_auth.py` exit 0; `verify_founder(1, fresh_signature)` = `t`; replay old signature = `f`; `SELECT public_key FROM hermes.founders WHERE id=1` non-empty Ed25519-format | docs/setup-evidence/P30/evidence/step-001.md | FAIL if replay accepted; FAIL if not Ed25519; FAIL if signatures forged |
| P30-002 | infra/db/20-21-*.sql; src/hermes/governance/spawn.py; tests/test_spawn.py | non-founder vote accepted; apply without 2/2 PASS | `pytest test_spawn.py` exit 0; `spawn_propose + 2 PASS + apply_spawn` = success; `1 PASS + 1 REJECT` = reject; non-founder vote = false | docs/setup-evidence/P30/evidence/step-002.md | FAIL if non-founder vote accepted; FAIL if apply works without 2/2 PASS |
| P30-003 | infra/db/22-veto-function.sql; src/hermes/governance/veto.py; tests/test_veto.py | non-founder veto; veto on passed/active state | `pytest test_veto.py` exit 0; founder veto on `proposed` = rejected; non-founder = false; veto on `active` = false | docs/setup-evidence/P30/evidence/step-003.md | FAIL if non-founder veto succeeds; FAIL if veto on passed/active works |
| P30-004 | infra/db/23-validate-hermes.sql; src/hermes/governance/validate.py; tests/test_validate.py | non-female accepted; Y6 ceiling; floor > ceiling; validate not called in spawn apply | `pytest test_validate.py` exit 0; `gender='male'` reject; `rap_ceiling='Y6'` reject; `gender='female',rap_floor='Y4',rap_ceiling='Y5'` accept; `gender='female',rap_floor='Y5',rap_ceiling='Y4'` reject (floor > ceiling) | docs/setup-evidence/P30/evidence/step-004.md | FAIL if male accepted; FAIL if Y6 accepted; FAIL if validate not wired in spawn apply |
| P30-005 | src/hermes/governance/hard_stop.py; systemd ExecStopPost; src/hermes/audit/halt_poller.py; tests/test_hard_stop.py | `except HardStopActiveError: pass`; non-idempotent action missing HARD_STOP_PING; non-idempotent subprocess invocation without ping | `pytest test_hard_stop.py` exit 0; `SET hermes:hard_stop 1` → `ping()` raises `HardStopActiveError`; `SET hermes:hard_stop 0` → same `ping()` returns None; `grep -rn "HardStopActiveError" src/` shows no silent pattern; `grep -rn "raise HardStopActiveError\|ping()" src/` covers all governance + cognition non-idempotent paths | docs/setup-evidence/P30/evidence/step-005.md | FAIL if any non-idempotent path lacks ping; FAIL if HardStopActiveError swallowed; FAIL if systemd ExecStopPost missing |
| P30-006 | infra/db/24-consent-revoke.sql; governance/consent.py; recall/bdi/blackboard updates; tests/test_consent_revocation.py | non-atomic revoke (multi-step); cognition paths bypass revocation | `pytest test_consent_revocation.py` exit 0; `revoke_consent('guinevere')` → `last_revoked_at` set + `consent_revoked` event emitted (single tx); `recall` returns 0 intimacy rows for guinevere; `revise_belief('guinevere', ...)` raises `BLOCKED_CONSENT_REVOKED`; `blackboard.write('guinevere', ...)` raises `BLOCKED_CONSENT_REVOKED` | docs/setup-evidence/P30/evidence/step-006.md | FAIL if revoke not atomic; FAIL if any cognition path bypasses post-revoke |
| P30-007 | infra/db/25-governance-tiers.sql; src/hermes/governance/tiers.py; tests/test_tiers.py | hardcoded tier mapping outside SQL table; T4 missing founder-only or veto | `pytest test_tiers.py` exit 0; `requires_approval('prompt_patch')` = `tier_1`; `requires_approval('memory_schema_change')` = `tier_3`; `requires_approval('rap_ceiling_change')` = `tier_4`; T4 row in `governance_tiers` mentions founder_only and single_veto rights | docs/setup-evidence/P30/evidence/step-007.md | FAIL if tiers table missing; FAIL if T4 missing founder-only or veto |
| P30-008 | infra/db/26-27-*.sql; src/hermes/governance/members.py; tests/test_members.py | non-founder add/remove; missing event emission | `pytest test_members.py` exit 0; `add_member(payload, founder_id=99)` = false; `add_member(payload, founder_id=1)` = true + emits `member_added`; `remove_member(id, founder_id=99)` = false; `remove_member(id, founder_id=2)` = true + emits `member_removed` | docs/setup-evidence/P30/evidence/step-008.md | FAIL if non-founder add succeeds; FAIL if non-founder remove succeeds |
| P30-009 | tests/test_hard_stop_cascade.py; runbooks/hard-stop-recovery.md | services not actually stopping during test; recovery failure ignored | `pytest test_hard_stop_cascade.py` exit 0; `SET hermes:hard_stop 1` → `sleep 5`, `systemctl is-active hermes-guinevere hermes-pharsa` = `inactive` (or `failed`); `SET hermes:hard_stop 0` + `systemctl start ...`; `sleep 30`, `systemctl is-active` = `active`; journalctl shows `ExecStopPost=hard_stop` triggered + restart on recovery | docs/setup-evidence/P30/evidence/step-009.md | FAIL if any service stays active during HARD STOP; FAIL if recovery fails |
| P30-010 | tests/test_governance_acceptance.py; docs/setup-evidence/P30/evidence/soak-24h-governance-report.md | skip-on-transient; one-test-runs-rest-fail; over-tuning thresholds | `pytest test_governance_acceptance.py -v` exit 0 with all 8 scenarios PASS; after 24h soak: `SELECT COUNT(*) FROM hermes.events WHERE event_type IN ('spawn_vote','spawn_passed','spawn_vetoed','consent_revoked','member_added','member_removed','hard_stop_observed')` > 0 (events present, no errors); no governance violations in `journalctl` (no `ERROR` lines from governance module) | docs/setup-evidence/P30/evidence/step-010.md (and governance_acceptance_report.md and soak-24h-governance-report.md) | FAIL if any of 8 acceptance scenarios fails; FAIL if journalctl shows governance ERROR; FAIL if P28/P29 hard-rejection criteria regressed |

## Binary Pass/Fail Criteria

### Founder tokens

1. `verify_founder(1, fresh_signature)` returns `true` — PASS/FAIL
2. Replay attack: `verify_founder(1, signature_from_2_min_ago)` returns `false` — PASS/FAIL
3. `hermes.founders.public_key` column not empty for both founders — PASS/FAIL
4. Public key matches Ed25519 length (32 bytes / 64 hex chars) — PASS/FAIL

### Spawn protocol

5. `spawn_propose` creates proposal in `proposed` state — PASS/FAIL
6. Apply succeeds after 2/2 PASS — PASS/FAIL
7. Apply fails with 1 PASS + 1 REJECT — PASS/FAIL (negative test)
8. Non-founder vote rejected — PASS/FAIL (negative test)
9. Apply denies if validate_new_hermes returns false — PASS/FAIL (negative test)
10. Apply emits `spawn_active` event with proposer + payload hash — PASS/FAIL

### Veto primitive

11. Founder veto on `proposed` proposal transitions to `rejected` — PASS/FAIL
12. Non-founder veto returns false — PASS/FAIL (negative test)
13. Veto on `active` proposal returns false — PASS/FAIL (negative test)

### Female + dominant

<!-- ADR-067: Y-level caps apply to dev-workflow ONLY. Hermes runtime has no cap. -->
14. `validate_new_hermes({'gender':'male', ...})` returns false — PASS/FAIL (negative test)
15. `validate_new_hermes({'gender':'female','rap_floor':'Y4','rap_ceiling':'Y6'})` returns false — PASS/FAIL (negative test)
16. `validate_new_hermes({'gender':'female','rap_floor':'Y4','rap_ceiling':'Y5'})` returns true — PASS/FAIL
17. `validate_new_hermes({'gender':'female','rap_floor':'Y5','rap_ceiling':'Y4'})` returns false (floor > ceiling) — PASS/FAIL (negative test)

### HARD STOP

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->
18. `SET hermes:hard_stop 1` then `ping()` raises `HardStopActiveError` — PASS/FAIL
19. `SET hermes:hard_stop 0` then `ping()` returns None — PASS/FAIL
20. Systemd `ExecStopPost` includes hard_stop listener on both units — PASS/FAIL
21. End-to-end: `SET 1` → 5s → both services inactive/failed — PASS/FAIL
22. End-to-end: `SET 0` → restart → 30s → both services active — PASS/FAIL
23. REDIS poller (`halt_poller.py`) emits `hard_stop_observed` event within 10s of `SET 1` — PASS/FAIL

### Consent revocation

<!-- ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt. -->
24. `revoke_consent('guinevere')` is atomic (single transaction) — PASS/FAIL
25. After revoke, `recall(...)` returns 0 intimacy rows for guinevere — PASS/FAIL (negative leak test)
26. After revoke, `revise_belief('guinevere', ...)` raises `BLOCKED_CONSENT_REVOKED` — PASS/FAIL
27. After revoke, `blackboard.write('guinevere', ...)` raises `BLOCKED_CONSENT_REVOKED` — PASS/FAIL
28. `consent_revoked` event in `hermes.events` after revoke — PASS/FAIL

### Tier system

29. `requires_approval('prompt_patch')` returns `tier_1` (auto-promote) — PASS/FAIL
30. `requires_approval('memory_schema_change')` returns `tier_3` (society-voted) — PASS/FAIL
31. `requires_approval('rap_ceiling_change')` returns `tier_4` (founder-only + veto) — PASS/FAIL
32. T4 row in `governance_tiers` has `founder_only = true` and `single_veto_rights = true` — PASS/FAIL
33. `governance_tiers` has 4 rows (T1-T4) — PASS/FAIL

### Members

34. `add_member(payload, founder_id=99)` returns false (non-founder) — PASS/FAIL (negative test)
35. `add_member(payload, founder_id=1)` returns true + emits `member_added` — PASS/FAIL
36. `remove_member(id, founder_id=99)` returns false — PASS/FAIL (negative test)
37. `remove_member(id, founder_id=2)` returns true + emits `member_removed` — PASS/FAIL

### Acceptance + soak

38. `test_governance_acceptance.py` 8/8 scenarios PASS — PASS/FAIL
39. After 24h soak: governance events present in `hermes.events` — PASS/FAIL
40. After 24h soak: no `ERROR` lines in `journalctl` from governance module — PASS/FAIL
41. After 24h soak: no P28/P29 hard-rejection regressions — PASS/FAIL

## Runtime Proof Requirements

- `pytest tests/test_governance_acceptance.py -v` stdout shows 8 PASS lines corresponding to: founder_agreement, veto, validate_hard_reject, hard_stop_cascade, consent_revocation_cascade, spawn_mock_deploy, tier_system, member_add_remove.
- `redis-cli SET hermes:hard_stop 1` then `python -c "from hermes.governance.hard_stop import ping; ping()"` outputs traceback with `HardStopActiveError`.
- `psql -c "SELECT hermes.revoke_consent('guinevere'); SELECT consensus_call_after_revoke('recall')"` shows `consent_revoked` event + recall result contains `BLOCKED_CONSENT_REVOKED` instead of rows.
- `psql -c "SELECT COUNT(*) FROM hermes.events WHERE event_type IN ('spawn_active','spawn_vetoed','consent_revoked','member_added','member_removed')"` should be > 0 after the acceptance suite runs.
- `journalctl -u hermes-guinevere --since "24h ago" --no-pager | grep -E 'STATUS=halt|HARD STOP'` confirms the cascade and recovery are visible at the OS level.
- `python tests/test_hard_stop_cascade.py` outputs the timeline: SET 1 → 5s inactive → SET 0 → start → 30s active.

## Parent Verification Checklist

- [ ] Claimed files exist (`ls src/hermes/governance/*.py tests/test_governance*.py infra/db/[19-27]*.sql infra/systemd/hermes-*.service runbooks/hard-stop-recovery.md` all present)
- [ ] Changed files parent-read (parent cross-checks ≥ 30% of new file bodies against plan §4)
- [ ] `lsp_diagnostics` clean on all new/changed Python files
- [ ] All step tests pass (`pytest tests/test_<step>.py -v`)
- [ ] Acceptance suite 8/8 PASS
- [ ] HARD STOP cascade test + recovery test PASS *(ADR-062: dev-workflow agent ONLY)*
- [ ] Evidence paths exist (`docs/setup-evidence/P30/evidence/step-{NNN}.md` for all 10 steps)
- [ ] Auditor reports exist (`docs/setup-evidence/P30/evidence/audits/step-{NNN}-audit.md` for all 10 steps)
- [ ] HARD STOP recovery runbook at `runbooks/hard-stop-recovery.md` is finalized *(ADR-062: dev-workflow agent ONLY)*
- [ ] PersonaSafetyPolicy cross-checked (no code violates Y4/Y5 invariant; no logic touches ARD-030 etc.) *(ADR-067: Y-level caps dev-workflow ONLY)*
- [ ] ADR-054 cross-checked (P30 implements the governance surface; ADR-054 text is unchanged)
- [ ] No type suppression (`grep -rn "as any\|# type: ignore\|@ts-ignore" src/hermes/governance/` returns empty)
- [ ] No silent swallow of HardStopActiveError (`grep -rn "except HardStopActiveError" src/` returns no `pass` body)
- [ ] Soak report shows zero governance violations in 24h
- [ ] No regression to P28/P29 hard-rejection criteria after P30 is applied

## Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
