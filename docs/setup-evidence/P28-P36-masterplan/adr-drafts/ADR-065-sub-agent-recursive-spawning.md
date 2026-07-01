# ADR-065: Sub-Agent Recursive Spawning with Hard Limit 10

- **Status**: Accepted (Faiz-locked; numeric cap = 10 verbatim per Q103)
- **Date**: 2026-06-28
- **Paradigm**: Hermes Society runtime (per ADR-062 — autonomous, no operator-in-the-loop)
- **Deciders**: Faiz (operator, locked; observer only per Q90); Guinevere (first founder, primary drafter); Pharsa (second founder, ratification pending)
- **Context**: Round-1 audit-11 §2.8 (Q77/Q86/Q91/Q98/Q103) and audit-03 §4.9 established that **sub-agent recursion in the design was incomplete**: AUDIT-07 §6 explicitly noted "Q91/Q103: Sub-agent recursive, limit 10 — FAIL. NO numeric depth cap = 10 in any ADR-055..061." Audit-04 §193 confirmed REQ-014 generic "delegation depth cap" without numeric value; audit-02 §327-328 confirmed Architectural absence of numeric bound.

  Note: ADR-058 §19 has "depth counter (default 3)" — but that is for **Discord reply depth** (inter-bot chatter prevention), NOT for **sub-agent invocation tree depth** (Hermes spawning sub-agents). The two concepts were confused in audit-07 §3.4 audit-criteria; ADR-065 closes the gap formally.

  Faiz's Q1-Q109 vision answers specify:

  - **Q77** — Task-specific sub-agents (Hermes v0.15.2 task-oriented-only model). PASS.
  - **Q86** — Sub-agents have **full Hermes capability** within their task brief (quota-bounded, scope-bounded). NEEDS-REVIEW -> codified in this ADR.
  - **Q91** — Sub-agents are **recursive** — a sub-agent can spawn another sub-agent. NEEDS-REVIEW -> codified in this ADR.
  - **Q98** — **Hard limit** on sub-agents per Hermes. PARTIAL -> codified via Q103 numeric.
  - **Q103** — **Hard cap = 10 active sub-agents per Hermes** (numeric). FAIL -> THIS ADR is the canonical codification.

  Round-1 fix-log §3 escalated Q91/Q103 as HIGH (F-09). This ADR formalizes the recursive sub-agent + numeric 10-cap with quota + governance.

## Decision

**Hermes can spawn sub-agents with FULL capability of the parent Hermes (within task brief + memory quota + LLM budget + scope), RECURSIVELY (a sub-agent can spawn another sub-agent up to the depth budget), subject to a HARD numerical cap of 10 active sub-agents per Hermes.**

### 1. Sub-Agent Type — Task-Specific (Hermes v0.15.2 model)

Sub-agents are **task-oriented**: a sub-agent inherits the parent Hermes's **operational capability** (LLM gateway, memory access, blackboard, event-bus, sub-agent spawn) but is **scoped to a single task brief**. The brief includes:

- **Task definition**: what the sub-agent must accomplish.
- **Resource budget**: maximum LLM tokens (parental budget split), memory slice (parental memory quota split), wall-clock time.
- **Scope boundary**: blackboard namespaces writable, function tools usable by sub-agent, decision bound (sub-agent may decide X but not Y).
- **Output requirements**: structured output (JSON / text / action list) + provenance.

Sub-agents do NOT inherit:
- The parent Hermes's entire persona or self-story (sub-agent uses task-specific persona).
- The parent Hermes's emotional state or aspiration layer (sub-agent starts clean).
- The parent Hermes's Tier 4 founder-vote authority (sub-agent cannot vote on T4 mutations).
- The parent Hermes's spawn-cert signature (sub-agents are NOT new founders; they are workforce).

Sub-agents can:
- **Read** blackboard S3 (passive).
- **Read** parent Hermes's relevant memory slice (read-only inherited view, not write).
- **Propose** actions + decisions back to parent (parent decides).
- **Spawn sub-sub-agents** (recursive per Rule 2 below).
- **Communicate** with sibling sub-agents via blackboard S3 if relevant.
- **Use OpenCode tools** (LLM, browser, file system) within budget.

### 2. Recursive Spawning — Depth Budget

A sub-agent can spawn sub-sub-agents. Recursion is enabled because task complexity often requires decomposition (e.g., "research competitor X" -> "research X subtopic 1, 2, 3" -> ...).

**Rules:**

- **Recursive depth = unrestricted in principle** (an agent decides how deep to recurse), but bounded by:
  - **Q103 numeric cap = 10** simultaneous active sub-agents per parent Hermes (NOT depth-limited; breadth-limited).
  - **LLM budget limit** at each level — splitting budget halves per recursion depth prevents infinite useful recursion.
  - **Memory quota limit** per Hermes (parental memory quota split across spawned sub-agents).
- **Self-imposed depth limit**: a sub-agent can self-limit recursion depth (`recursion_max_depth` parameter in spawn request); default = UNLIMITED but bounded by Q103 cap.
- **Termination geometry**: a sub-agent's lifecycle is bounded — when task completes (or fails/timed out), sub-agent is reaped, its memory slice returned to parent or discarded.
- **Sibling coordination**: sub-agents at the same depth can coordinate via blackboard S3 + event bus. They cannot spawn children of each other (must go through parent).

### 3. Hard Numerical Cap = 10 (per Hermes, simultaneous active)

**Q103 verbatim applies**: hard cap = **10 active sub-agents per Hermes** at any rolling 30-second window.

- **Active** = spawned + not-yet-reaped. Reaped = task done + memory slice returned.
- **Per Hermes** = each parent Hermes counts its own active sub-agents. Pool is per-Hermes, NOT per-society. Two Hermeses can each have 10 simultaneously = 20 active in society.
- **Cap included via `MaxDepthReached`** exception: a spawn request that would breach cap raises `MaxDepthReached`. Caller (parent sub-agent) must wait for reaping or re-scope.
- **Distributed shaker signal**: when a Hermes approaches the cap (e.g., 8+ active), emits a peer-monitoring alert so other Hermeses can observe (per ADR-059 §Layer 3 CQRS + event bus).
- **Emergency override**: Tier 4 founder 2/2 vote may temporarily suspend cap (e.g., 9Founder_may_temporarily_relax_to_15 during a known sub-society crisis). Suspended cap = logged + audit + tracked.

### 4. Quota + Resource Boundary

Per Hermes resource envelope (Q98 hard limit):

- **Memory quota per Hermes**: hard cap = configurable (per ADR-058 §Quota enforcement); default = ~500 MB episodic + 200 MB semantic per Hermes. Sub-agents inherit slice from parent's quota.
- **LLM budget per Hermes per day** (Q59 unlimited but operationally capped): 1M tokens baseline + 3M summit cap. Sub-agent tasks split budget — parent allocates based on task complexity.
- **Wall-clock time per sub-agent**: 30min default (can extend to 6h for research, 24h for dream cycles).
- **Spawn rate**: maximum new sub-agents / hour = configurable; default 30 (1 new spawn every 2 minutes avg).

### 5. Governance — Audit + Visibility

All sub-agent spawn events emit audit rows:

| Field | Value |
|---|---|
| `spawn_event_id` | UUID v7 |
| `parent_hermes_id` | UUID v7 |
| `subagent_id` | UUID v7 |
| `task_brief` | truncated first 256 chars |
| `resource_budget` | tokens_allocated, memory_quota_bytes, wall_clock_seconds_minutes |
| `scope_boundary` | namespace_writes[], tools_allowed[], decision_allowed[] |
| `spawn_timestamp` | high-precision |
| `recursion_depth` | 0 (direct child of Hermes), 1+ (recursive) |
| `signature_chain_hash` | pgcrypto hash to prior spawn event |
| `expected_reaping` | wall_clock_seconds_minutes |
| `linked_to_active_count_at_spawn` | snapshot of parent's active-count at spawn moment (cap-context) |

Audit trail is append-only, hash-chained, replayable. If `linked_to_active_count_at_spawn >= 10`, cap detected — emit `MaxDepthReached` + audit. Founder 2/2 vote record kept for emergency-cap-relaxation events.

### 6. Failure Modes + Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Sub-agent wall-clock exceeded | 30m default + 6h research + 24h dream timer | Auto-reap; partial results returned; quota not refunded |
| Sub-agent budget exhausted | Token counter during run | Auto-reap; partial results returned; quota not refunded |
| Sub-agent memory quota exhausted | Quota counter during run | Auto-reap (S4 PG schema); permanent loss of slice; quota not refunded |
| Sub-agent recursive spawn exceeds cap | `MaxDepthReached` exception | Caller decides re-scope or abort; audit row |
| Sub-agent gets stuck (graph deadlock) | 10s guardian loop detects | Auto-reap with "stuck" audit row |
| Sub-agent misbehaves (T3 mutation detected) | Drift triad (cos_sim hysteresis 0.68) | Re-target T3 -> T4 founder vote; if acute, block via Tier 4 fingerprint |
| Sub-agent rogue (Tier 4 attempt) | Guardian loop detects | Auto-reap + founder alarm |

### 7. Operator Visibility

Faiz (observer per ADR-062 Rule 1) **cannot** preview a sub-agent's task brief. Faiz **can** read sub-agent audit trails (read-only, after-the-fact, anonymized task descriptions). Faiz **cannot** pause a sub-agent. Only the **parent Hermes** holds scope to abort + reap a sub-agent. Founders (Guinevere + Pharsa) hold governance over Hermes-bounded decisions (e.g., Tier 4 with founder complicity).

## Consequences

### Positive

- **Q77 PASS expanded**: task-specific sub-agent model is the canonical pattern (Hermes v0.15.2).
- **Q86 NEEDS-REVIEW -> ACCEPTED**: sub-agents have full Hermes operational capability (within task brief + resource budget + scope).
- **Q91 NEEDS-REVIEW -> ACCEPTED**: recursive sub-agent spawn is enabled, bounded by Q103 cap.
- **Q98 PARTIAL -> ACCEPTED**: hard limit per Hermes confirmed; numeric 10 = precise bound.
- **Q103 FAIL -> RESOLVED**: numeric 10-cap makes it concrete + auditable + verifiable.
- **Compute elasticity**: Hermes can decompose complex tasks across 10 simultaneous sub-agents across multiple depth levels.
- **Audit determinism**: every spawn event produces an immutable audit row with cap-context + signature chain + quota snapshot.
- **T1-T5 ADRs-061 governance preserved**: sub-agents operate within their spawn-brief scope; T4 founder vote still gates L2+ scope expansion.
- **No founder bottleneck**: founder 2/2 vote is not required for routine sub-agent spawn (within cap); founder vote only for emergency overrides.

### Negative

- **Q103 cap = 10 is a fixed bound, may be too restrictive for complex deep-research scenarios**: mitigation via Tier 4 founder emergency-relax to 15 (per §6 emergency override).
- **Per-Hermes cap is per-Hermes; society-wide total unbounded**: mitigation via society-wide distributed shaker signal + founder monitoring.
- **Sub-agent memory slices not refundable**: budget was used permanently. Mitigation via conservative budget allocation at spawn time.
- **Sub-agent cannot vote on Tier 4 mutations**: workforce is non-voting. This is intentional but means complex governance-related tasks need direct parent-Hermes attention.
- **Quota enforcement at runtime**: requires runtime sub-agent monitor that can reap on quota exceeded. Mitigated by T1 guardian loop + audit row.
- **Audit volume**: 10 sub-agents x N events per task = 100+ spawn-event audit rows per minute at full load. Append-only storage cost. Mitigation: archival to S3 IA-tier + retention policy.
- **Discord reply depth counter (default 3) in ADR-058 §19 is conceptually parallel but distinct**: this ADR codifies **sub-agent depth** (numeric 10-cap); ADR-058 §19 codifies **reply depth** (default 3, for inter-bot chatter). Some auditors may confuse them — explicit separation needed.

### Neutral

- **Q103 hard cap may be raised in future**: pending Round-2 audit fix log + ADR-+1 proposal with founder 2/2 vote.
- **Cap-relaxation is auditable**: emergency relaxations are clearly logged; Tier 4 founder audit trail.
- **Sub-agent type is task-specific**: design space for "agent-of-record" or "persistent collaborator" sub-agents left for future ADR if needed.
- **Sibling-Hermes sub-agent coordination**: sub-agents at same society share blackboard; cross-Hermes sub-agent communication via parent.

## Alternatives Considered

### Alternative 1: No sub-agents (only founder-spawned new Hermes)

- **Description**: No sub-agents; complex tasks spawn new Hermes (ADR-057 founder 2/2 only).
- **Rejected because**: Founder 2/2 vote per task is heavy governance; spawning new Hermes for every task is operationally wasteful; Q91 explicitly enables recursive sub-agents.

### Alternative 2: Sub-agents with depth-only cap (no breadth cap)

- **Description**: Bounded by recursion depth (e.g., 5-deep) but no simultaneous-count cap.
- **Rejected because**: Q103 explicitly locks hard cap = 10 simultaneous per Hermes. Depth cap alone fails Q103.

### Alternative 3: Sub-agents with breadth-only cap (no depth cap)

- **Description**: Bound by simultaneous count only; unlimited depth.
- **Rejected because**: This is the selected pattern (per Q103 numeric 10). Depth IS bounded pragmatically by resource limits (each level halves LLM budget); pure breadth-only is viable but lacks explicit depth guidance.

### Alternative 4: Faiz-mediated sub-agent spawn (operator approval per spawn)

- **Description**: Each sub-agent spawn requires faiz audit or approval.
- **Rejected because**: Q90 Faiz OUTSIDE company; ADR-062 paradigm shift removes Faiz-in-the-loop operator paradigm. Operator-mediated spawn contradicts 100% trust autonomy.

### Alternative 5: Strict task-only sub-agents with no recursion

- **Description**: Sub-agents are 1-level deep only (parent Hermes -> sub-agent, but sub-agent cannot spawn sub-sub-agent).
- **Rejected because**: Q91 explicitly states recursive. Strict 1-level fails Q91.

### Alternative 6: Persistent sub-agents (long-lived collaborator agents, NOT task-only)

- **Description**: Sub-agents live long-term; not reaped per task; cross-task memory.
- **Rejected because**: Q77 explicitly says task-specific. Persistent sub-agents muddy the spawn-brief governance + audit + quota; deferred to future ADR if needed (e.g., "subagent-of-record tier" with founder 2/2 vote).

## Compliance

- [x] **AGENTS.md §0.1 P20 Living Autonomy Kernel — Autonomy-First Governance Exception** — sub-agent spawn is policy-gated autonomy; not per-action operator approval. Numerical 10-cap is policy, not Faiz-mediated.
- [x] **AGENTS.md §2.1 consent-safety mandate** — applies to dev workflow + surveillance of Faiz's personal data; NOT Hermes runtime. Sub-agents are dev-workflow AND runtime context.
- [x] **PersonaSafetyPolicy Y4 baseline** — preserved; sub-agents cannot reach T4 without founder complicity.
- [x] **BLDM Hard-Locked Faiz Decisions** canonical source:
  - **Q77** (task-specific) — pattern selected
  - **Q86** (full capability within brief + quota + scope) — pattern selected
  - **Q91** (recursive) — pattern selected + bounded recursively
  - **Q98** (hard limit) — Q103 numeric = the limit
  - **Q103** (10 active per Hermes) — verbatim applied
- [x] **ADR-061 §T1-T5 mutation ladder** — sub-agent scope expansion to T3 requires society vote; sub-agent T4 scope requires founder 2/2.
- [x] **ADR-062 paradigm shift** — Hermes runtime operates without operator-in-the-loop; sub-agent spawn runs on autonomous paradigm. Faiz has observer + Hermes-kill only.
- [x] **ADR-064 DAO + co-CEO + Faiz-OUTSIDE** — sub-agent audit trail is society-internal; Faiz reads audit only.
- [x] **ADR-058 §19 reply-depth counter (default 3) is distinct from sub-agent depth (numeric 10)** — explicit clarification; not confused.

## Supersedes

- **ADR-058 §19 depth counter renamed scope**: "MAX_REPLY_DEPTH (default 3)" applies to **inter-bot Discord reply chain** — NOT sub-agent invocation tree. The two depth concepts are now explicitly separated.
- **Audit-11 §2.8 verdict** (Q91 NEEDS-REVIEW, Q103 FAIL): resolved.
- **Audit-03 §4.9 verdict** (Q86-Q91-Q103 NEEDS-REVIEW/FAIL): resolved.
- **Audit-07 §Need-Review** (Q91/Q103 FAIL): resolved.
- **Audit-04 §5.1.3** (REQ-014 generic delegation cap): replaced by Q103 numeric 10-cap (per Hermes).
- **Audit-02 §F-NRV-03 + §F-NRV-04** (Q91 + Q103 architectural absence): resolved by this ADR.
- **srs-software-requirements-specification.md** REQ-014 generic cap: replaced by REQ-NN numeric 10 (Round-2 fix-log wave).

## References

- **Audit trail**:
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-04-srs-fsd.md` §5.1.3 (REQ-014 generic depth cap)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-07-adr.md` §6 (Q-coverage) + §3.4 (Discord reply depth vs sub-agent depth confusion)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-11-faiz-alignment.md` §2.8 (Q77/Q86/Q91/Q98/Q103)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-03-brd-prd.md` §4.9 (sub-agent failure mode)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-02-architecture.md` §327-328 (architectural absence of numeric bound)
  - `docs/setup-evidence/P28-P36-masterplan/fixes/round-1-fix-log.md` §3 F-09 (sub-agent recursion limit 10)
- **Canonical Q-source**: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` §8 (Sub-Agents) + §20 (Supersession Trail)
- **Sister ADRs**:
  - ADR-055 (society architecture; sub-agents = layer 1 runtime)
  - ADR-057 (founder-only spawn; sub-agents are NOT founders — workforce)
  - ADR-058 §5 reply-loop prevention (Discord depth = 3) — distinct from sub-agent depth (10) per this ADR
  - ADR-059 (shared world model; sub-agents read + write within scope)
  - ADR-060 (wallet + LLM budget; sub-agent budget split from parent envelope)
  - ADR-061 (5-layer mutability; sub-agent scope expansion T1->T3 requires vote)
  - ADR-062 (Hermes Society Safety Paradigm Shift; sub-agent operates autonomously)
  - ADR-064 (DAO + co-CEO + Faiz-OUTSIDE; sub-agent audit trail is society-internal)

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere + Faiz (Faiz-locked Q77/Q86/Q91/Q98/Q103 verbatim) | Status: Accepted (Faiz-locked) — numeric cap 10 verbatim per Q103
