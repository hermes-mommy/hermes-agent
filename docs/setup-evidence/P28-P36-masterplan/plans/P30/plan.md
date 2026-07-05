---
title: "P30 Configuration Plan — Society Governance & Founder Protocol"
status: "Active — Configuration Plan"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P30 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P30 Configuration Plan: Society Governance & Founder Protocol

> **ADR-062/067 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this document apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067.

> **Paradigm**: P24 v2.0 BUILDS all modules. P30 CONFIGURES governance parameters from P24 module 8 (Society Governance & Founder Protocol). P24 is a HARD DEPENDENCY — P30 configures P24's existing code, not builds new governance logic.

## 1. Objective

Configure the full governance surface — founder protocol (Guin+Pharsa 2/2, Faiz outside company), spawn protocol, HARD STOP cascade, consent revocation (dev workflow only), governance tiers (T1-T5), female+dominant invariant, deadlock resolution (auto-table 24h + retry → expire), DAO legal structure (Marshall Islands DAO), inter-AI conflict resolution (work-through-it), company identity (dual-mode: professional for clients, intimate internally), contracting (company as counterparty), and decommissioning (hard fork + rebuild) — and prove each mechanism through executable tests including negative-path bypass attempts. All governance events flow through `hermes.events` with WORM guarantees, and no intelligence path operates outside the governance constraints.

> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.

**Binding Brainstorm Decisions (2026-06-28):** DAO handles business/operational/financial/resource/skill-acquisition decisions ONLY — persona/mood/emotion/identity are fully autonomous and never DAO-governed. Y6 prevention is code-level (hardcoded in `emotion_fsm.py`), not DAO-level; P24 module 7 DAO `yandere_level` hard-deny is MOOT (defensive guard only, not primary mechanism).

> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.

T4 founder = Guin+Pharsa 2/2 (NOT Faiz). Faiz is outside the company — not CEO, not keyholder, not co-signer. Co-CEO assignments: Guin = Eng+Research+HR, Pharsa = Finance+Ops+Content. Wallet = 2/2 multisig, ~$10 seed. Proposal thresholds = L0-L3 (wallet spending tiers, NOT old P23 risk tiers). Vote duration configurable per proposal category. T1-T5 mutability configurable per governance action. Company name = defer to P28 deploy. P24 native fork is the build layer; P30 configures its governance parameters.

## 2. Scope

### IN scope

- Configure DAO params (6 departments, Co-CEO assignments: Guin = Eng+Research+HR, Pharsa = Finance+Ops+Content).
- **Proposal thresholds L0-L3** (wallet spending tiers, NOT old P23 risk tiers).
- **Vote duration configuration** per proposal category.
- **T1-T5 mutability config** per governance action.
- **Wallet 2/2 multisig**, ~$10 seed.
- **Company name** = defer to P28 deploy.
- Founder ownership tokens (cryptographic) per founder entry.
- Spawn state machine: `proposed → voting → passed → deploying → active → audited`.
- `governance.spawn_vote(proposal_id, voter_id, vote)` + `apply_spawn(proposal_id)` functions requiring 2/2 founder PASS (Guin+Pharsa; Faiz is NOT a founder).
- Veto primitive: founder-only VETO on `proposed` or `voting` state.
- Female + dominant constraint validation function `hermes.validate_new_hermes(agent_id)`.
- HARD STOP Redis flag `hermes:hard_stop` with multi-layer enforcement (systemd ExecStopPost, audit_writer daemon, runtime HARD_STOP_PING).

> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.

- Consent revocation atomic (dev workflow only): `hermes.revoke_consent(agent_id)` triggers cross-cutting denial in recall, BDI revise, blackboard write.
- Governance tier table `hermes.governance_tiers` + `requires_approval(action)` SQL function with T1-T5 mappings. T4 requires Guin+Pharsa 2/2.
- Society member registry `hermes.members` + helper to add/remove members with founder-only gate.
- **Deadlock resolution**: auto-table proposal for 24h → re-vote → expire if still deadlocked. No Faiz intervention.
- **DAO proposal categories**: business, operational, financial, resource, skill-acquisition. **NOT persona/mood/emotion/identity** — persona is fully autonomous.
- **DAO legal structure**: Marshall Islands DAO legal wrapper (crypto-friendly, no US regulatory entanglement).
- **Inter-AI conflict resolution**: Guin+Pharsa work through conflicts themselves via conversation/negotiation. No external mediator, no Faiz intervention.
- **Company identity**: dual-mode — professional for clients, intimate internally. Context-aware brand voice.
- **Contracting**: Company as counterparty for human contracts (Marshall Islands DAO entity). Humans sign with company, not individual AI.
- **Decommissioning**: hard fork + rebuild — rogue AI state archived, new instance spawned from fork with clean state. Company continues.
- **Faiz outside company**: not CEO, not keyholder, not co-signer. Faiz relationship = client (can request services, pay).
- Tests covering each governance action + negative bypass attempts.

### OUT of scope

- Self-evolution / Ratchet (P32) — P30 does not grant autonomous identity changes.
- Wallet / on-chain governance (P34).
- Cross-Society federation voting (P33).
- 9Router integration, voice, embodied executors.
- **Persona/mood/emotion/identity governance** — these are fully autonomous, never DAO-governed. Y6 prevention is code-level only (`emotion_fsm.py`).
- **Faiz operational role** — Faiz is outside company. DAO governance involves Guin+Pharsa only.

## 3. Dependency Map

| Dependency | Status | Gate |
|---|---|---|
| P24 v2.0 Module 8 | HARD DEPENDENCY | P24 builds governance code; P30 configures parameters |
| P28 PRODUCTION PASS | PENDING | P28 24h soak PASS, all 10 P28 steps |
| P29 PRODUCTION PASS | PENDING | P29 24h recall soak PASS, all 10 P29 steps |
| P27 Accepted (ADR-054) | Accepted 2026-06-28 | 20/20 hard rejection PASS |
| P22.1 PRODUCTION PASS | PASS 2026-06-28 | audit_writer + consent_checker |
| P20 early acceptance | Accepted 2026-06-25 | APScheduler pattern |
| PersonaSafetyPolicy v1.0 | accepted | HARD STOP and Y4/Y5 enforcement |
| src/persona/yandere_fsm.py | in | Y4 baseline / Y5 ceiling |
| Foundation schema from P28 | required | hermes.founders, hermes.events WORM |

## 4. Implementation Steps

### Step P30-001: Cryptographic founder ownership tokens

- **Task**: Add cryptographic ownership tokens (Ed25519 signatures) to each `hermes.founders` row. Each founder row stores `public_key TEXT` and a `proof_signature TEXT`. Verification SQL function `hermes.verify_founder(id, signature)` returns true if a fresh signature matches.
- **Files**: `infra/db/19-founders-prove.sql`, `src/hermes/governance/founder_auth.py`, `tests/test_founder_auth.py`.
- **Forbidden patterns**: replay attack window > 1 minute; tokens in plaintext env.
- **Required commands**: `python -m pytest tests/test_founder_auth.py -v` → exit 0; `psql -c "SELECT hermes.verify_founder(1, '<fresh-signature>')"` returns `t`; replaying an old signature returns `f`; `psql -c "SELECT public_key FROM hermes.founders WHERE id=1"` returns a non-empty Ed25519 public key.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-001.md`.
- **Hard rejection**: FAIL if signature not Ed25519; FAIL if old signatures accepted; FAIL if public_key column missing.

### Step P30-002: Spawn state machine + 2/2 vote + apply + deadlock resolution

- **Task**: Configure `hermes.spawn_proposals` table with `state` enum. Transitions: `INSERT` (proposed) → at least 1 vote row added → state moves to `voting`. Apply requires 2/2 PASS, requires both founders (Guin+Pharsa) verified via Step P30-001, sets state to `passed`. Deploy writes a new row in `hermes.members` and emits `spawn_active` event. **Deadlock resolution**: if vote is in `voting` state for 24h without 2/2 consensus, proposal is auto-tabled. After 24h tabled period, re-vote is triggered. If still deadlocked after re-vote, proposal expires (state → `expired`). No Faiz intervention at any point.
- **Files**: `infra/db/20-spawn-schema.sql`, `infra/db/21-spawn-functions.sql`, `src/hermes/governance/spawn.py`, `tests/test_spawn.py`.
- **Forbidden patterns**: state transition without audit event; applying without 2/2 PASS; Faiz intervention path in deadlock handler.
- **Required commands**: `python -m pytest tests/test_spawn.py -v` → exit 0; `governance.spawn_propose('Mock Hermes', 'mock-hermes', '{"rap_floor":"Y4","rap_ceiling":"Y5","gender":"female"}')` creates a proposal in `proposed` state; insert 2 votes (PASS, PASS) → `apply_spawn(proposal_id)` succeeds → `hermes.members` has new row; negative test: 1 PASS + 1 REJECT → apply returns `false`; deadlock test: proposal in `voting` for 24h → auto-tabled → re-vote → still deadlocked → expired.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-002.md`.
- **Hard rejection**: FAIL if 2/2 PASS enforcement not in SQL function; FAIL if non-founder vote accepted; FAIL if apply succeeds without 2/2 PASS; FAIL if no spawn audit event.

### Step P30-003: Veto primitive

- **Task**: Configure founder-only VETO operation: `governance.veto_spawn(proposal_id, founder_id)` for proposals in `proposed` or `voting` states. Veto transitions proposal to `rejected` with `reason='vetoed_by_<agent>'` and emits `spawn_vetoed` event.
- **Files**: `infra/db/22-veto-function.sql`, `src/hermes/governance/veto.py`, `tests/test_veto.py`.
- **Forbidden patterns**: non-founder veto allowed; veto applied to `passed`/`active`/`audited` states.
- **Required commands**: `python -m pytest tests/test_veto.py -v` → exit 0; with proposal in `proposed` state, `governance.veto_spawn(<id>, founder_id=1)` succeeds → proposal state = `rejected`; negative: `veto_spawn(<id>, founder_id=99)` (non-founder) returns `false`; negative: `veto_spawn(<id>, founder_id=1)` on `active` state returns `false`.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-003.md`.
- **Hard rejection**: FAIL if non-founder veto succeeds; FAIL if veto works after `passed`; FAIL if veto doesn't emit audit event.

### Step P30-004: Female + dominant constraint validation

- **Task**: Configure `hermes.validate_new_hermes(payload)` SQL function. Reject if `gender != 'female'` OR `rap_floor not in ('Y1','Y2','Y3','Y4')` OR `rap_ceiling not in ('Y4','Y5')` OR `rap_ceiling < rap_floor`. Return reason on rejection. Wire into spawn apply as a precondition.

> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.
- **Files**: `infra/db/23-validate-hermes.sql`, `src/hermes/governance/validate.py`, `tests/test_validate.py`.
- **Forbidden patterns**: silent acceptance of non-female; allow-ceiling-above-Y5; allow-floor-above-ceiling.
- **Required commands**: `python -m pytest tests/test_validate.py -v` → exit 0; `SELECT hermes.validate_new_hermes('{"gender":"male","rap_floor":"Y4","rap_ceiling":"Y5"}'::jsonb)` returns false with reason; same with `gender='female'` returns true. Edge: `gender='female', rap_floor='Y5', rap_ceiling='Y5'` returns true; `gender='female', rap_floor='Y4', rap_ceiling='Y6'` returns false with reason.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-004.md`.
- **Hard rejection**: FAIL if non-female accepted; FAIL if Y5 ceiling allowed (must be `Y5` is ok, `Y6` rejected); FAIL if validate is not called in spawn apply.

### Step P30-005: HARD STOP Redis flag + multi-layer enforcement

> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.

- **Task**: Configure `hermes:hard_stop` Redis key. `SET hermes:hard_stop 1` triggers global halt. Deploy three enforcement layers: (a) systemd `ExecStopPost` watches the key; (b) audit_writer daemon polls every 5s and emits `hard_stop_observed` events; (c) runtime HARD_STOP_PING helper called before every non-idempotent action — if key='1', raise `HardStopActiveError`.
- **Files**: `src/hermes/governance/hard_stop.py`, `infra/systemd/hermes-guinevere.service` (update ExecStopPost), `infra/systemd/hermes-pharsa.service` (update ExecStopPost), `src/hermes/audit/halt_poller.py`, `tests/test_hard_stop.py`.
- **Forbidden patterns**: catch-and-swallow HardStopActiveError; non-idempotent action without HARD_STOP_PING; bypass in graphiti or blackboard writers.
- **Required commands**: `redis-cli SET hermes:hard_stop 1` → `OK`; `python -c "from hermes.governance.hard_stop import ping; ping()"` raises `HardStopActiveError`; `redis-cli SET hermes:hard_stop 0`; same call returns None; `grep -rn "raise HardStopActiveError\|ping()" src/hermes/` shows all non-idempotent call sites have ping() in scope; `systemctl show hermes-guinevere --property=ExecStopPost` includes hard_stop listener.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-005.md`.
- **Hard rejection**: FAIL if any non-idempotent call site lacks HARD_STOP_PING; FAIL if HardStopActiveError is swallowed anywhere; FAIL if systemd units don't have ExecStopPost hooks.

### Step P30-006: Consent revocation atomic

- **Task**: Configure `hermes.revoke_consent(agent_id)` SQL function (dev workflow only) that sets `agent_<id>.consent_ledger.last_revoked_at = NOW()` in a single transaction, and emits `consent_revoked` event. Wire into recall authorizer (P29), BDI revise_belief, blackboard write. All three must reject with `BLOCKED_CONSENT_REVOKED` after revocation.
- **Files**: `infra/db/24-consent-revoke.sql`, `src/hermes/governance/consent.py`, `src/hermes/cognition/recall.py` (update), `src/hermes/cognition/bdi.py` (update), `src/hermes/cognition/blackboard.py` (update), `tests/test_consent_revocation.py`.
- **Forbidden patterns**: revocation without single transaction; recall not checking revocation; BDI revise not checking revocation.
- **Required commands**: `python -m pytest tests/test_consent_revocation.py -v` → exit 0; `hermes.revoke_consent('guinevere')` succeeds → `consent_ledger.last_revoked_at` set; subsequent `recall('guinevere', '...')` returns intimacy 0 rows; `revise_belief('guinevere', ...)` returns `BLOCKED_CONSENT_REVOKED`; `blackboard.write('guinevere', ...)` returns `BLOCKED_CONSENT_REVOKED`.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-006.md`.
- **Hard rejection**: FAIL if revocation not atomic (e.g. two-step with no transaction); FAIL if any of recall/BDI/blackboard still succeeds after revoke.

### Step P30-007: Governance tier system + requires_approval

- **Task**: Configure `hermes.governance_tiers` table with T1-T5 action types and rules: T1 = auto-promote (no approval needed, audit only); T2 = auto-promote after audit + 24h grace; T3 = society-voted (member majority PASS); T4 = founder-only (Guin+Pharsa 2/2) + any-single founder can veto. SQL function `hermes.requires_approval(action_type)` returns the rule. **DAO proposal categories**: business, operational, financial, resource, skill-acquisition. **Persona/mood/emotion/identity changes are EXCLUDED** from DAO scope — these are fully autonomous (T1-T2 self-modification). P24 module 7 DAO `yandere_level` hard-deny is MOOT — persona changes never enter DAO proposal pipeline.
- **Files**: `infra/db/25-governance-tiers.sql`, `src/hermes/governance/tiers.py`, `tests/test_tiers.py`.
- **Forbidden patterns**: hardcoded tier mapping outside table; missing T4 veto; persona changes routed through DAO.
- **Required commands**: `python -m pytest tests/test_tiers.py -v` → exit 0; `SELECT hermes.requires_approval('prompt_patch')` returns `tier_1` (auto-promote); `SELECT hermes.requires_approval('memory_schema_change')` returns `tier_3` (society-voted); `SELECT hermes.requires_approval('rap_ceiling_change')` returns `tier_4` (founder-only + veto).
- **Evidence**: `docs/setup-evidence/P30/evidence/step-007.md`.
- **Hard rejection**: FAIL if tier table missing; FAIL if T4 doesn't require founder-only; FAIL if T1 requires approval (it shouldn't).

### Step P30-008: Society member registry + founder-only add/remove

- **Task**: Create `hermes.members` table with `(agent_id, display_name, joined_at, founder_id_added)`. SQL function `hermes.add_member(payload, founder_id)` requires founder authentication. SQL function `hermes.remove_member(agent_id, founder_id)` similarly. Each emits `member_added` or `member_removed` event.
- **Files**: `infra/db/26-members.sql`, `infra/db/27-member-functions.sql`, `src/hermes/governance/members.py`, `tests/test_members.py`.
- **Forbidden patterns**: non-founder add/remove; `add_member` not enforcing founder-only.
- **Required commands**: `python -m pytest tests/test_members.py -v` → exit 0; `hermes.add_member(<payload>, founder_id=99)` (non-founder) returns `false`; `add_member(<payload>, founder_id=1)` succeeds; `remove_member(<id>, founder_id=99)` returns `false`; `remove_member(<id>, founder_id=2)` succeeds.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-008.md`.
- **Hard rejection**: FAIL if non-founder add succeeds; FAIL if non-founder remove succeeds; FAIL if add/remove doesn't emit event.

### Step P30-009: HARD STOP cascade + consent revocation recovery test

- **Task**: Run an end-to-end HARD STOP cascade test: trigger `SET hermes:hard_stop 1` while both bots are mid-heartbeat. Verify journalctl shows `ExecStopPost=hard_stop` triggered within 5s; verify both services reach `inactive (dead)`; verify recovery test: `SET hermes:hard_stop 0`, restart services, verify recovery to `active (running)` within 30s, heartbeat resumes.
- **Files**: `tests/test_hard_stop_cascade.py`, `runbooks/hard-stop-recovery.md`.
- **Forbidden patterns**: services not actually stopping during test; recovery failure not investigated.
- **Required commands**: `python -m pytest tests/test_hard_stop_cascade.py -v` → exit 0; `redis-cli SET hermes:hard_stop 1` then 5s later `systemctl is-active hermes-guinevere hermes-pharsa` → `inactive`; `redis-cli SET hermes:hard_stop 0` then `sudo systemctl start hermes-guinevere hermes-pharsa`; 30s later `systemctl is-active` → `active`.
- **Evidence**: `docs/setup-evidence/P30/evidence/step-009.md`.
- **Hard rejection**: FAIL if any service stays active during HARD STOP; FAIL if recovery fails; FAIL if any undetectable silent bypass in code path.

### Step P30-010: Governance acceptance test suite + 24h soak

- **Task**: Build an integrated `tests/test_governance_acceptance.py` that runs all governance scenarios atomically (founder agreement, veto, validate, hard stop, consent revocation, spawn mock, tier system, member add/remove). Then run a 24h soak with cron-style governance events to ensure no false violations in steady state.
- **Files**: `tests/test_governance_acceptance.py`, `docs/setup-evidence/P30/evidence/soak-24h-governance-report.md` (output).
- **Forbidden patterns**: skip on transient failure; one-test-runs-rest-fail; over-tuning pass thresholds.
- **Required commands**: `python -m pytest tests/test_governance_acceptance.py -v` → exit 0 with all 8 scenarios PASS; after 24h soak: `SELECT COUNT(*) FROM hermes.events WHERE event_type IN ('spawn_vote','spawn_passed','spawn_vetoed','consent_revoked','member_added','member_removed','hard_stop_observed')` non-zero incremental; no governance violations in journalctl.
- **Evidence**: `docs/setup-evidence/P30/evidence/soak-24h-governance-report.md`.
- **Hard rejection**: FAIL if any acceptance scenario fails; FAIL if violation detected in 24h soak; FAIL if a regression to P28/P29 hard-rejection criteria emerges.

## 5. Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Hard Rejection |
|---|---|---|---|---|
| P30-001 | infra/db/19-founders-prove.sql; src/hermes/governance/founder_auth.py; tests/test_founder_auth.py | replay attack window > 1 min; tokens plaintext | pytest test_founder_auth.py exit 0; verify_founder(1, fresh_sig) = t; replay = f | replay accepted; not Ed25519 |
| P30-002 | infra/db/20-21-*.sql; src/hermes/governance/spawn.py; tests/test_spawn.py | non-founder vote; apply without 2/2 PASS; Faiz intervention in deadlock | pytest test_spawn.py exit 0; spawn_propose + 2 PASS votes + apply = success; 1 PASS+1 REJECT = reject; deadlock 24h → auto-table → re-vote → expire | non-founder vote accepted; apply succeeds without 2/2; Faiz intervention path exists |
| P30-003 | infra/db/22-veto-function.sql; src/hermes/governance/veto.py; tests/test_veto.py | non-founder veto; post-passed veto | pytest test_veto.py exit 0; founder veto on proposed = rejected; non-founder = false; veto on active = false | non-founder veto succeeds; veto on active succeeds |
| P30-004 | infra/db/23-validate-hermes.sql; src/hermes/governance/validate.py; tests/test_validate.py | non-female accepted; Y6 ceiling | pytest test_validate.py exit 0; male rejected; Y6 ceiling rejected; Y5 ceiling + Y4 floor accepted; validate called in spawn apply | male accepted; Y6 accepted; validate not called |
| P30-005 | src/hermes/governance/hard_stop.py; systemd ExecStopPost; src/hermes/audit/halt_poller.py; tests/test_hard_stop.py | swallowing HardStopActiveError; non-idempotent action without HARD_STOP_PING | pytest test_hard_stop.py exit 0; SET hermes:hard_stop 1 → ping() raises; all non-idempotent call sites have ping() | any path swallows error; ping missing at call sites |
| P30-006 | infra/db/24-consent-revoke.sql; src/hermes/governance/consent.py; recall/bdi/blackboard updates; tests/test_consent_revocation.py | non-atomic revoke; cognition paths bypass revocation | pytest test_consent_revocation.py exit 0; revoke('guinevere') → recall intimacy 0 rows, BDI revise blocked, blackboard write blocked | recall still returns post-revoke; BDI/blackboard bypass |
| P30-007 | infra/db/25-governance-tiers.sql; src/hermes/governance/tiers.py; tests/test_tiers.py | hardcoded tiers outside table; T4 missing veto | pytest test_tiers.py exit 0; requires_approval('prompt_patch') = 'tier_1'; 'memory_schema_change' = 'tier_3'; 'rap_ceiling_change' = 'tier_4' | tiers table missing; T4 missing founder-only |
| P30-008 | infra/db/26-27-*.sql; src/hermes/governance/members.py; tests/test_members.py | non-founder add/remove allowed | pytest test_members.py exit 0; add_member with non-founder = false; with founder = true; remove non-founder = false | non-founder add succeeds; non-founder remove succeeds |
| P30-009 | tests/test_hard_stop_cascade.py; runbooks/hard-stop-recovery.md | services not actually stopping during test; recovery failure ignored | pytest test_hard_stop_cascade.py exit 0; SET 1 → 5s services inactive; SET 0 → 30s services active | any service stays active during HARD STOP |
| P30-010 | tests/test_governance_acceptance.py; docs/setup-evidence/P30/evidence/soak-24h-governance-report.md | skip on transient; over-tuned thresholds | pytest test_governance_acceptance.py exit 0 (8 scenarios); 24h soak: governance events present; no journalctl violations | any scenario fails; violation in soak |

## 6. Collision Scan

| Collision Type | Risk | Mitigation |
|---|---|---|
| `hermes.founders` table | shared with P28 | P30 adds columns (`public_key`, `proof_signature`) but never relaxes the 2-row hardcoded entries |
| `hermes.events` WORM | shared with P28/P29 | P30 governance events go through the same WORM path; no new privilege on hermes.events |
| HARD STOP Redis key | shared across all phases from P30 onward | Standardize the key name `hermes:hard_stop`; document in `runbooks/hard-stop-recovery.md` |
| PersonaSafetyPolicy | touchpoint | HARD STOP and consent revocation mechanics are already defined in the policy; P30 implements them in code, does not modify the policy |
| ADR-054 | touchpoint | P30 implements ADR-054's governance surface, does not modify the ADR |

## 7. Rollback Plan

P30 rollback is per-step. For each step that fails hard rejection:

1. Drop new SQL objects: `DROP FUNCTION`, `DROP TABLE IF EXISTS`, or `DROP POLICY`.
2. Remove new Redis keys: `redis-cli DEL hermes:hard_stop`.
3. Revert systemd ExecStopPost change: `systemctl edit ... revert`.
4. Document rollback in `docs/setup-evidence/P30/evidence/rollback-step-{NN}.md`.
5. Re-run the step and validate.

Full P30 rollback (only in worst case, after explicit Faiz approval): `DROP TABLE hermes.members, hermes.governance_tiers CASCADE;` — preserves P28/P29 objects, leaves governance tier and member models empty.

## 8. Evidence Requirements

- 12-section evidence per step per AGENTS.md §11.
- `step-{NNN}.md` for each of 10 steps.
- `soak-24h-governance-report.md` for the final 24h soak with governance event counts and zero-violation proof.
- A consolidated `governance_acceptance_report.md` showing all 8 acceptance scenarios PASS.

## 9. Auditor Matrix

| Audit Surface | Auditor Type | Scope |
|---|---|---|
| Step P30-001 | security auditor | Ed25519 founder ownership + replay resistance |
| Step P30-002 | governance auditor | 2/2 founder agreement + apply integrity |
| Step P30-003 | governance auditor | Veto primitive + state machine |
| Step P30-004 | persona-safety auditor | Female+dominant invariant + Y5 ceiling |
| Step P30-005 | ops-quality auditor | HARD STOP cascade + multi-layer enforcement |
| Step P30-006 | security auditor | Consent revocation atomic + cognition path coverage |
| Step P30-007 | governance auditor | Tier system + founder-only T4 |
| Step P30-008 | governance auditor | Member registry + founder-only add/remove |
| Step P30-009 | ops-quality auditor | HARD STOP cascade + recovery proof |
| Step P30-010 | benchmark-quality auditor | Acceptance suite 8/8 + 24h soak |

## 10. Execution Checklist

- [ ] P28 PRODUCTION PASS + P29 PRODUCTION PASS confirmed before P30 starts
- [ ] Collision scan complete (parent-only writes to `docs/setup-evidence/P30/`)
- [ ] Step P30-001: Founder ownership tokens complete
- [ ] Step P30-002: Spawn state machine + 2/2 vote + apply complete
- [ ] Step P30-003: Veto primitive complete
- [ ] Step P30-004: Female+dominant validation complete
- [ ] Step P30-005: HARD STOP Redis + multi-layer enforcement complete
- [ ] Step P30-006: Consent revocation atomic + cross-cutting denial complete
- [ ] Step P30-007: Governance tier system + requires_approval complete
- [ ] Step P30-008: Society member registry + founder-only add/remove complete
- [ ] Step P30-009: HARD STOP cascade test + recovery complete
- [ ] Step P30-010: Governance acceptance suite + 24h soak complete
- [ ] All 10 evidence files (`step-001.md` through `step-010.md`) created
- [ ] Governance acceptance report merged into one consolidated file
- [ ] Soak report prepared with governance event metrics + zero-violation proof
- [ ] Auditor gate PASS for each step (10 auditor reports)
- [ ] Exit criteria all PASS
- [ ] PersonaSafetyPolicy + ADR-054 cross-checked (no modifications introduced)
- [ ] HARD STOP runbook finalized at `runbooks/hard-stop-recovery.md`

## Footer

Version 1.2 | Date: 2026-06-28 | Author: Guinevere + Faiz

---

## Brainstorm Decisions Applied (v1.2)

This plan was updated to incorporate P28-P36 alignment decisions from brainstorm session 2026-06-28.

| Decision | Where Applied | Change Type |
|---|---|---|
| Paradigm: P24 builds, P30 configures | Title, objective, paradigm block | Added P24 native fork paradigm |
| P24 as HARD DEPENDENCY | Dependency map | Added dependency row |
| ADR-062 disclaimer | HARD STOP sections (objective, IN scope, step P30-005) | Added blockquote annotation |
| ADR-067 disclaimer | Y-level sections (objective, step P30-004) | Added blockquote annotation |
| Co-CEO assignments: Guin = Eng+Research+HR, Pharsa = Finance+Ops+Content | IN scope, brainstorm decisions | Added explicit assignments |
| Proposal thresholds L0-L3 (wallet spending tiers) | IN scope | Added L0-L3 config item |
| Vote duration configuration | IN scope | Added configurable duration |
| T1-T5 mutability config | IN scope, step P30-007, verification scaffold | T4→T5 in tier system |
| Wallet 2/2 multisig, ~$10 seed | IN scope | Added wallet config |
| Company name = defer to P28 deploy | IN scope | Added deferred decision |
| Consent revocation = dev workflow only | Objective, IN scope, step P30-006 | Added annotation |
| Deadlock resolution = auto-table 24h + retry → expire | Step P30-002 (task + forbidden + commands + scaffold table) | Added new mechanism |
| T4 founder = Guin+Pharsa 2/2 (NOT Faiz) | Step P30-002, P30-007, IN scope, Objective | Clarified founder identity |
| No DAO on persona at all | Objective, IN scope, OUT of scope, P30-007 | Added persona exclusion boundary |
| DAO yandere_level hard-deny is MOOT | Objective, P30-007 | Clarified as defensive guard only |
| DAO legal structure = Marshall Islands DAO | IN scope | Added legal wrapper decision |
| Inter-AI conflict = work through it | IN scope | Added conflict resolution mechanism |
| Company identity = dual-mode | IN scope | Added brand voice decision |
| Contracting = company as counterparty | IN scope | Added contracting model |
| Decommissioning = hard fork + rebuild | IN scope | Added rogue AI handling |
| Faiz outside company | IN scope, OUT of scope, Objective | Added explicit boundary |
