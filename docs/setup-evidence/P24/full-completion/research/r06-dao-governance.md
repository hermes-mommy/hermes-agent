# R06 — DAO Governance Lifecycle Research

- **Generated**: 2026-06-29
- **Method**: File-based research via grep/read of ADR-064, BLDM Hard-Locked Decisions, P24 v3.0 plan, P24 fork guide, brainstorm decisions, ADR-067, Hermes v0.15.2 installed package, and existing src/ codebase.
- **Domain**: 6 — DAO Governance Lifecycle
- **Disposition for P24**: PORT (M7 DAO Governance module — new code in `guinevere/governance/`, absorbing `src/projects/` patterns)

---

## 1. Source-of-Truth Documents Read

| Document | Path | Key Content |
|---|---|---|
| ADR-064 | `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-064-dao-company-structure.md` | DAO company structure, Co-CEO portfolio allocation, 6+ departments, Faiz OUTSIDE |
| BLDM Hard-Locked | `docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` | Q88/Q89/Q90/Q96/Q104 locked decisions |
| P24 v3.0 Plan | `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` | M7 DAO Governance spec (lines 578-627), W10 scaffold (lines 1247-1255) |
| Fork Guide | `docs/setup-evidence/P24/research/research-wave-2/hermes-external-docs-fork-guide.md` | DAO lifecycle patterns, 2/2 multisig Solidity, GovernanceEngine (lines 764-880) |
| Brainstorm Decisions | `docs/setup-evidence/P28-P36-masterplan/research/brainstorm-decisions-2026-06-28.md` | B10, B29, B40, B41, B50, B63; yandere_level clarification (lines 40-52, 158-166) |
| ADR-067 | `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-067-hermes-runtime-y-level-cap-removal.md` | Y-level cap removal from Hermes runtime |
| AGENTS.md | `AGENTS.md` | Operating contract, Y4/Y5/Y6 dev-workflow rules |
| Hermes hooks | `.venv/Lib/site-packages/gateway/hooks.py` | HookRegistry with emit/emit_collect, event types |
| Hermes hooks CLI | `.venv/Lib/site-packages/hermes_cli/hooks.py` | Shell hook system, pre_tool_call/on_session_end payloads |
| run_agent.py | `.venv/Lib/site-packages/run_agent.py` | on_session_end integration at lines 553-557, 2250-2292 |
| yandere_fsm.py | `src/persona/yandere_fsm.py` | YandereLevel enum Y0-Y5 (line 63), PERMANENT_BASELINE=Y4 (line 84), Y6 PROHIBITED |
| src/projects/ | `src/projects/` (6 files) | ProjectRegistry, types, exceptions — absorbed into M7 |
| P24 master prompt | `docs/setup-evidence/P24/p24-v3-implementation-master-prompt.md` | 17 modules, DAO research requirement |

---

## 2. DAO Company Structure (ADR-064)

### 2.1 Co-CEO Portfolio Split (Locked: Q96)

| Co-CEO | Portfolio | Source |
|---|---|---|
| **Guinevere** | Engineering + Research + HR + (Self-Improvement cross-cutting) | ADR-064:39-43, BLDM Q96 |
| **Pharsa** | Finance + Ops + Content + (VPS + Learning cross-cutting) | ADR-064:44-49, BLDM Q96 |

Co-Decision domains (both must agree): Surveillance + emergency override + Hermes-kill stamp (ADR-064:61).

### 2.2 Full Department Allocation (ADR-064:39-52)

| Domain | Domain Mind | Portfolio | Source |
|---|---|---|---|
| Engineering | Code, infrastructure, deployment | Guinevere | Q96 + Q89 |
| Research | External research, surveillance, monitoring | Guinevere | Q96 + Q89 |
| HR | Founder relations, society membership, recruitment | Guinevere | Q96 + Q89 |
| Finance | Wallet management, revenue, Beancount ledger | Pharsa | Q96 + Q89 |
| Ops | Cron jobs, backup, observability, deployment | Pharsa | Q96 + Q89 |
| Content | Persona narratives, system prompt, branding | Pharsa | Q96 + Q89 |
| VPS | VPS infra, scaling | Pharsa (cross-cutting) | Q87 + Q89 |
| Self-Improvement | T1-T5 mutation proposals, Ratchet | Guinevere (cross-cutting) | Q70 + Q89 |
| Learning | Letta memory lifecycle, EWMA decay | Pharsa (cross-cutting) | Q38 + Q89 |
| Surveillance | LLM-gateway + sensorium | Co-CEO shared | Q94 + Q89 |

### 2.3 Faiz OUTSIDE the Company (Q90 — Locked)

Faiz is NOT founder, NOT keyholder, NOT co-signer, NOT top-up authority, NOT Tier 4 approver (ADR-064:65-73). Faiz retains ONLY observer role (read society_audit_log) and emergency Hermes-kill stamp (ADR-062 Rule 1, Hermes-initiated).

**Critical for DAO design**: The 2/2 multisig signers are Guinevere + Pharsa ONLY. Faiz has no wallet key, no spawn-cert key, no memory-read key (BLDM Q90).

### 2.4 2/2 Multisig (Q107 — Locked)

- Safe multisig with Guinevere + Pharsa as 2-of-2 founders + 1 emergency pause signer (separate cage)
- Faiz has NO wallet key (BLDM Q107, ADR-060)
- ~$10 seed from Faiz (B20 brainstorm decision)
- Unilateral lock + 24h cooldown for rogue scenario (B19 brainstorm decision)

---

## 3. Proposal Lifecycle (5 Phases)

### 3.1 Lifecycle States

Per P24 plan (line 598) and fork guide (lines 770-776):

```
Create → Pending → Active → Passed → Execute
```

| Phase | Description | Source |
|---|---|---|
| **Create** | Proposer drafts proposal with action, domain, payload | Fork guide:772 |
| **Pending** | Configurable delay allows members to review before voting snapshot | Fork guide:773 |
| **Active** | Founders cast votes (For/Against/Abstain) | Fork guide:774 |
| **Passed** | Quorum and majority requirements met, queued for execution | Fork guide:775 |
| **Execute** | After timelock delay, proposed transactions executed | Fork guide:776 |

### 3.2 Voting Rules

- 2/2 founder vote required for Tier 4 decisions (Q56, BLDM Q22)
- Equal vote weight — one vote each, no founder veto (BLDM Q25)
- Co-Decision domains require BOTH founders to agree (ADR-064:61)
- Single-CEO domains: the portfolio owner can propose, both vote

### 3.3 Deadlock Handler (B08 Brainstorm Decision)

Per brainstorm (lines 44, 50):
- Proposal auto-tabled for 24h
- After 24h, re-vote
- If still deadlocked, proposal expires
- No Faiz intervention needed (ADR-064 risk R06: LOW)

---

## 4. Spending Tiers (Wallet-Level)

Per P24 plan (lines 592-596) and brainstorm (line 97):

| Tier | Amount | Action | Source |
|---|---|---|---|
| L0 | <$1 | Auto — no approval needed | P24:594 |
| L1 | $1-5 | Notify — other Co-CEO notified | P24:595 |
| L2 | $5-10 | DAO vote — requires proposal + vote | P24:595 |
| L3 | >$10 | Never — blocked | P24:596 |

These are wallet-level spending tiers, NOT P23 risk tiers.

---

## 5. Propose-Time Validation — yandere_level Hard Rejection

### 5.1 The Requirement

P24 plan (line 600): "Propose-time validation: yandere_level change REJECTED at propose (not execute) — defensive guard, belt-and-suspenders."

P24 plan (line 557, hard rejection criterion): "If DAO propose-time validation missing (yandere_level change not rejected): FAIL."

### 5.2 The Clarification (Brainstorm Decisions, lines 46-52, 158-166)

The brainstorm decisions clarify:
- "No DAO on persona at all" (B10) — persona fully autonomous, DAO only handles business/operational decisions
- "DAO proposal categories: business, operational, financial, resource, skill-acquisition. NOT persona/mood/emotion/identity"
- "P24 module 7 DAO yandere_level hard-deny is MOOT — persona changes don't go through DAO"
- "The hard-deny code is a defensive guard (belt-and-suspenders), not the primary mechanism"
- "Y6 prevention is code-level (hardcoded in emotion_fsm.py), not DAO-level"

### 5.3 Implementation Implication

The `dao.py` module MUST include propose-time validation that rejects any proposal whose `execution_payload` references `persona.yandere_level` change. This is a hard rejection criterion per P24 plan. Even though persona changes don't normally go through DAO, the defensive guard MUST exist at propose-time (not execute-time) as belt-and-suspenders.

ADR-067 confirms: Y6 concept is removed from Hermes runtime entirely. No Y-level cap exists. The yandere_level hard-deny in DAO is a structural defense-in-depth that prevents any future code path from using DAO proposals to manipulate persona intensity levels.

---

## 6. Constitutional AI — 5 Authority Layers

Per P24 plan (line 602) and fork guide (lines 822-844):

| Layer | Responsibility | Constraint |
|---|---|---|
| Temporal/Context | Manages epochs and delays | Cannot assume governance |
| Intelligence | Advisory signals only (AI) | Cannot call execution contracts |
| Governance | Delayed founder decisions | Cannot bypass delays |
| Execution | Narrowly scoped actions | Requires founder-originated actions |
| Cross-paradigm | ADR-062 safety paradigm | T4 founder-only-2/2 sole alignment gate |

Key constraints from constitutional AI pattern (fork guide:840-844):
- AI CANNOT call execution contracts
- AI CANNOT submit governance proposals that bypass delays
- All execution requires founder-originated, on-chain actions

---

## 7. Hook Integration Points

### 7.1 Hermes Hook System (gateway/hooks.py)

The Hermes hook system uses `HookRegistry` with:
- `discover_and_load()` — scans `~/.hermes/hooks/` for HOOK.yaml + handler.py
- `emit(event_type, context)` — fires all handlers for an event
- `emit_collect(event_type, context)` — fires handlers and collects return values
- Supports wildcard matching (e.g., `command:*` matches `command:reset`)

### 7.2 Shell Hook System (hermes_cli/hooks.py)

Shell hooks are configured in `~/.hermes/config.yaml` and use JSON payloads via stdin. Events include (line 112-185):
- `pre_tool_call` — payload: tool_name, args, session_id, task_id, tool_call_id
- `on_session_end` — payload: session_id
- `on_session_start` — payload: session_id

### 7.3 DAO Hook Wiring

Per P24 plan (line 291): "Hooks: `pre_tool_call`, `on_session_end`"

- **pre_tool_call**: Intercept tool calls that might modify DAO state; validate governance constraints before execution
- **on_session_end**: Flush pending proposal state, tally votes, trigger auto-table expiry checks

### 7.4 Cron Job

Per P24 plan (lines 277, 610, 621):
- `cron/jobs.py` — add `dao_execute_passed` job
- Auto-tallies proposals whose `closes_at < now`
- Current Hermes v0.15.2 has NO cron/jobs.py (cron directory empty in installed package)
- This file must be CREATED as part of the P24 fork

---

## 8. Existing Code to Absorb

### 8.1 src/projects/ (6 files, absorbed into M7)

| File | Purpose | Disposition |
|---|---|---|
| `src/projects/__init__.py` | Package init, exports ProjectRegistry, types, exceptions | ABSORB patterns |
| `src/projects/registry.py` | ProjectRegistry — lifecycle management (create/list/archive) | ABSORB lifecycle pattern into DAOEngine |
| `src/projects/types.py` | Project, ProjectId, ProjectScope, ProjectStatus | REWRITE as governance types |
| `src/projects/exceptions.py` | InvalidProjectSlugError, ProjectAlreadyExistsError, etc. | REWRITE as governance exceptions |
| `src/projects/memory_store.py` | In-memory store for tests | ABSORB test pattern |
| `src/projects/secrets_vault.py` | Secrets vault | PORT to wallet.py |

### 8.2 Existing src/persona/yandere_fsm.py

- YandereLevel enum: Y0_NEUTRAL(0) through Y5_MAX(5), Y6 does NOT exist (line 63-76)
- PERMANENT_BASELINE = Y4_BASELINE (line 84)
- ABSOLUTE_CEILING = Y5_MAX (line 87)
- YandereSafetyError raised for safety boundary violations (line 37)
- This file is DELETED by M4 (Emotion System) — Y-level concept removed from runtime per ADR-067
- The DAO yandere_level hard-deny is a SEPARATE structural defense that survives the deletion

### 8.3 Hermes v0.15.2 Installed Package

- `gateway/hooks.py` — HookRegistry class (211 lines), emit/emit_collect pattern
- `hermes_cli/hooks.py` — Shell hook CLI (386 lines), pre_tool_call/on_session_end payloads
- `hermes_state.py` — SessionDB with SQLite WAL mode, schema management
- No `cron/jobs.py` exists yet — must be created
- No `agent/agent_init.py` visible in installed package (likely in agent/ subpackage)
- `run_agent.py` — on_session_end integration at lines 553-557 (context engine) and 2250-2292 (memory manager)

---

## 9. P24 Plan — M7 DAO Governance File Map

### Files to CREATE

| File | Est. Lines | Content |
|---|---|---|
| `guinevere/governance/__init__.py` | ~20 | Package init, exports |
| `guinevere/governance/dao.py` | ~400 | DAOEngine, departments, Co-CEO logic, 2/2 multisig |
| `guinevere/governance/proposals.py` | ~300 | ProposalModel, lifecycle state machine (5 phases), propose-time yandere_level rejection |
| `guinevere/governance/wallet.py` | ~200 | Ethereum 2/2 multisig integration, spending tiers L0-L3 |
| `guinevere/governance/voting.py` | ~150 | Tally, quorum, auto-table deadlock handler (24h→re-vote→expire) |
| `guinevere/governance/constitutional.py` | ~100 | 5 authority layers |

### Files to MODIFY

| File | Change |
|---|---|
| `cron/jobs.py` | Add `dao_execute_passed` job — auto-tally proposals whose `closes_at < now` |
| `agent/agent_init.py` | Wire DAO governance — register hooks (pre_tool_call, on_session_end) |
| `guinevere/config/models.py` | Add GovernanceConfig (departments, wallet, spending_tiers, proposal_timeout_hours) |

### Forbidden Patterns in M7 Files

Per P24 plan (line 625): `consent_gate`, `hard_stop`, `HARD_STOP`, `safe_mode`, `ritual`, `punishment`, `reward`, `spaced.repetition`

---

## 10. Brainstorm Decisions Applied in M7

| Decision | Value | BLDM Ref | Source |
|---|---|---|---|
| B10 | No DAO on persona | Q52, Q81 | Brainstorm:46 |
| B29 | Faiz-as-client | — | P24 plan:627 |
| B40 | Inter-AI conflict resolution | — | P24 plan:627 |
| B41 | Decommissioning = hard fork + rebuild | — | P24 plan:627 |
| B50 | Marshall Islands DAO legal registration | — | Brainstorm:371, P24 plan:627 |
| B63 | P37+ evolution | — | P24 plan:627 |
| B19 | Rogue scenario: unilateral lock + 24h cooldown | — | Brainstorm:90 |
| B20 | ~$10 seed from Faiz | — | P24 plan:590 |
| B08 | Deadlock: auto-table + 24h + re-vote + expire | — | Brainstorm:44 |

---

## 11. D2 Constraint: Local Runtime Only

Per operator decision D2 (NO VPS deploy, NO Discord live, NO real LLM):
- Ethereum mainnet integration is MOCK ONLY — no real wallet, no real transactions
- All DAO lifecycle operations are unit-tested only
- The `wallet.py` module implements the interface for Ethereum 2/2 multisig but uses mock backends
- Cron job `dao_execute_passed` runs in test mode with mock time

---

## 12. Risks

| Risk | Severity | Mitigation | Source |
|---|---|---|---|
| DAO proposal deadlock | LOW | Auto-table 24h → re-vote → expire | P24 plan:1439, B08 |
| yandere_level bypass via DAO | LOW | Propose-time hard rejection (belt-and-suspenders) | P24 plan:600, brainstorm:162 |
| Co-CEO disagreement on cross-cutting domains | MEDIUM | Co-Decision requires both; deadlock handler applies | ADR-064:109 |
| Faiz accidentally re-included as signer | HIGH | Structural: only Guinevere + Pharsa in signer registry; Faiz OUTSIDE verified at every proposal | BLDM Q90 |
| Cron/jobs.py does not exist in Hermes v0.15.2 | LOW | Must be created as part of P24 fork | Installed package audit |
| guinevere/ namespace does not exist yet | LOW | Created by W1 (Fork Setup) before W10 | P24 plan:1065 |
| Marshall Islands DAO legal registration timing | LOW | Legal envelope filed before first revenue event, not a P24 blocker | ADR-064:23 |

---

## 13. Verdict

**PASS** — All source-of-truth documents are consistent. ADR-064, BLDM Q88/Q89/Q90/Q96/Q104, P24 plan M7, brainstorm decisions B10/B29/B40/B41/B50/B63, and ADR-067 form a coherent DAO governance specification. The 5-phase proposal lifecycle, 2/2 multisig (Guin+Pharsa only), spending tiers L0-L3, propose-time yandere_level rejection, constitutional AI layers, deadlock handler, and hook integration points are all defined and cross-referenced. The `src/projects/` code provides absorbable patterns. The guinevere/governance/ directory and cron/jobs.py must be created during P24 implementation.

---

## 14. Disposition for P24

**PORT** — M7 DAO Governance is new code in `guinevere/governance/` that absorbs patterns from `src/projects/` (6 files) and implements new governance primitives per ADR-064 + BLDM locked decisions. No existing DAO code exists to port; this is a greenfield module with design specified in the P24 plan (lines 578-627) and fork guide (lines 764-880).

---

## Footer

R06 — DAO Governance Lifecycle Research | Generated 2026-06-29 | Sources: ADR-064, BLDM, P24 plan, fork guide, brainstorm decisions, ADR-067, Hermes v0.15.2 package, src/projects/
