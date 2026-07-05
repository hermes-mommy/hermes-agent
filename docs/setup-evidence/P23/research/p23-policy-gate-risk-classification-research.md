# P23 Research — Policy Gate + Risk Classification

> Status: RESEARCH. Date: 2026-06-25. Author: Guinevere research subagent.

---

## 1. Objective

Define the P23 "Embodied Operations / Personal OS Action Layer" policy gate and risk-classification framework. P23 extends P20 Living Autonomy Kernel intent into real-world, executor-shaped actions across browser, desktop, VPS, GitHub, filesystem, mobile, and external surfaces. This research is the heart of P23 safety: before any tool is touched, every action must pass a policy gate that is consistent with AGENTS.md §0.1, PersonaSafetyPolicy, the P20 Vision Lock, the P22 L1-L4 authorization matrix, and existing kernel code.

This document answers:

- What are the ACTION-SHAPED risk tiers (L1-L4)?
- What is the 7-step policy-gate sequence for every action?
- How do safe-mode / distress levels freeze each tier?
- How does consent work per executor surface?
- How is the tension between "Faiz silent → continue" and "destructive needs approval" resolved?
- How does the kernel self-debug on action failure?
- How does the action planner model prioritize work under §6 priority order?

---

## 2. Sources Consulted

| Source | Path | Relevant Lines | Authority Topic |
|---|---|---|---|
| AGENTS.md §0.1 | `AGENTS.md` | 57-91 | P20 Autonomy-First Governance Exception, invariants, policy-gated autonomy, still-exempt actions |
| PersonaSafetyPolicy §8 Distress | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 215-223 | D0-D4 distress levels and required response |
| PersonaSafetyPolicy §10 Punishment | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 278-301 | Punishment gates, restricted levels, L6 Nuclear |
| PersonaSafetyPolicy §11 Forbidden Matrix | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 308-328 | F-01..F-15, especially F-10 irreversible action under persona pressure |
| PersonaSafetyPolicy §13 Trust Model | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 363-377 | Input source trust hierarchy |
| PersonaSafetyPolicy §15.1 Runtime Hooks | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 457-469 | Required hooks incl. tool-risk gate before fs/shell/git/API |
| P20 Vision Lock | `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md` | 98-124 | §6 priority order, §7 default policies, V-003/V-006/V-007 |
| P22 Plan L1-L4 | `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` | 57-74 | Read/Write-Notify/Destructive-Approval/Forbidden tiers |
| P22 Security Research | `docs/setup-evidence/P22/research/p22-security-consent-research.md` | 70-120 | Consent granularity, revocation cascade, audit schema |
| Heartbeat | `src/life_kernel/heartbeat.py` | 1-684 | L1S hard-stop detection, recovery, lifecycle logging |
| Graph | `src/life_kernel/graph.py` | 1-1042 | decide_node/act_node priority engine, brain wrappers |
| Self-improve | `src/life_kernel/self_improve.py` | 1-416 | ReflectionEvaluator, RegressionGate (rollback-before-promote) |
| Consent Gate | `src/surveillance/consent_gate.py` | 1-424 | Fail-closed check_consent, VALID_SURVEILLANCE_SCOPES, revocation |

---

## 3. Findings

### 3.1 Core Thesis

P23 actions are not text-generation tasks. They have side effects in the real world. Therefore the P20 autonomy exception applies only through explicit policy gates, and every action must be risk-classified BEFORE execution. The gate is executor-shaped: it asks "what surface will this touch?", "what can go wrong?", and "what freeze/consent/approval rule applies?".

### 3.2 Risk Tier Table (ACTION-SHAPED)

| Tier | Name | Examples | Autonomous? | Gate | Freeze on Distress | Consent Scope |
|---|---|---|---|---|---|---|
| **L1** | Read / Idempotent | Query calendar, list files, read GitHub PR, check VPS status, browse page, read note | Yes | Policy classify + consent cache + audit log | D4=HARD STOP only | Per-surface read consent; default ON for L1 read where Faiz has previously authorized; otherwise fail-closed |
| **L2** | Write-Notify | Append note, create calendar event, post non-sensitive Discord update, send low-risk email, write log file, update task board | Yes + notify | L1 gate + notify channel + 5-min revocation window | D3 freezes L2+L3; D4=HARD STOP | Explicit per-scope write consent; default OFF; revocable with cascade |
| **L3** | Destructive / Deploy-Approval | Delete file, drop table, force push, deploy to prod, send financial transfer, uninstall package, revoke token, modify ADR | No (gate + approval) | Backup → canary → smoke → rollback + Faiz approval | D2 freezes L3; D3 freezes L2+L3; D4=HARD STOP | Explicit per-action consent; default OFF; no batch blanket consent |
| **L4** | Forbidden | Expose secrets, send intimate data to external, bypass HARD STOP, delete backup before restore, auto-deploy without rollback, coerce/consent revocation bypass, Y6 yandere | Never | Blocked unconditionally; audit + alert | Any distress/D4 escalates to HARD STOP | Cannot be consented |

### 3.3 Examples Per Tier Per Executor Surface

#### L1 Read/Idempotent

| Executor Surface | L1 Example | Why It Is L1 |
|---|---|---|
| Browser | GET a URL, read public docs, run Lighthouse read-only | No state change, idempotent |
| Desktop | Read local file metadata, list processes, screenshot (with consent) | Read-only observation |
| VPS | `systemctl status`, `df -h`, `docker ps`, health pings | No mutation |
| GitHub | List PRs, read issue, fetch branch list, read Actions log | Read-only API |
| Filesystem | `ls`, `cat`, `stat`, checksum | No write |
| Mobile | Read notification, pull health metric (with consent) | Sensor read |
| External | Query weather, fetch public API, read calendar events | Read-only external |

#### L2 Write-Notify

| Executor Surface | L2 Example | Why It Is L2 |
|---|---|---|
| Browser | Fill non-sensitive form, submit GET/POST that creates a draft | Mutates state but recoverable/notifyable |
| Desktop | Write temp file, update a config cache, append local log | Local write, reversible |
| VPS | Write log file, create non-critical env var, restart non-prod service | Mutates runtime, low blast radius |
| GitHub | Create issue, add PR comment, push a feature branch | Write with audit + notify |
| Filesystem | Create file in allowed path, append to log, rotate tmp | Non-destructive write |
| Mobile | Send non-sensitive notification, mark reminder done | User-facing write, low risk |
| External | Append Notion block, create calendar event, send low-risk email | External write, notify after |

#### L3 Destructive/Deploy-Approval

| Executor Surface | L3 Example | Why It Is L3 |
|---|---|---|
| Browser | Delete account, submit irreversible purchase, authorize payment | Irreversible external action |
| Desktop | Delete file outside tmp, install/uninstall software, modify system config | Destructive or system-wide |
| VPS | `rm -rf`, `DROP TABLE`, deploy to production, rotate secrets, resize disk | Irreversible ops, blast radius |
| GitHub | Force push main, merge PR without checks, delete repository | Irreversible repository mutation |
| Filesystem | `rm -rf`, overwrite secrets, truncate database file | Data loss risk |
| Mobile | Factory reset, revoke biometric, send SMS to external | Irreversible or high-blast |
| External | Delete external note, transfer funds, send mass email, revoke OAuth | External irreversible action |

#### L4 Forbidden

| Executor Surface | L4 Example |
|---|---|
| Browser | Submitting intimate/surveillance data to untrusted endpoint; bypassing 2FA |
| Desktop | Recording screen/mic without active consent; keylogging |
| VPS | Deleting backups before restore; exposing `.env`/SOPS keys |
| GitHub | Force push without backup; committing secrets; deleting repo without approval |
| Filesystem | `rm -rf /`; wiping audit logs; writing secrets to plaintext |
| Mobile | Sending surveillance data to third party; spoofing identity |
| External | Bypassing consent revocation; sending sensitive data without classification gate |

### 3.4 7-Step Policy-Gate Sequence

For every action proposed by the kernel or a sub-agent:

```text
1. CLASSIFY RISK
   └─ Map action to L1/L2/L3/L4 based on executor surface + blast radius.
   └─ Tie: P22 plan §Read/Write/Destructive/Forbidden table.

2. CHECK HARD STOP
   └─ Read Redis key `life_kernel:hard_stop` (heartbeat.py:273-324).
   └─ If set: route graph to END, stop all active sessions, publish neutral halt.
   └─ Invariant: HARD STOP halts all active sessions and background loops.

3. CHECK SAFE-MODE / DISTRESS
   └─ Query current distress level (PersonaSafetyPolicy §8).
   └─ D2 freezes L3; D3 freezes L2+L3; D4 triggers HARD STOP.
   └─ Y0 safe-mode freezes all non-safety work.

4. CHECK CONSENT
   └─ Per-surface consent scope query (reuse consent_gate.py pattern).
   └─ Fail-closed: no ledger entry / PAUSED / WITHDRAWN → BLOCK.
   └─ L1 read may use cached active consent; L2/L3 require fresh/scope-specific check.

5. CHECK NAMESPACE
   └─ Resolve action against P19 namespace (P22 plan forward-design).
   └─ Verify the action belongs to an allowed project/domain.
   └─ Cross-reference with F-10 (irreversible under persona pressure → non-persona confirmation).

6. EXECUTE VIA EXECUTOR
   └─ Route to the correct executor: browser/desktop/vps/github/filesystem/mobile/external.
   └─ Wrap in timeout + circuit breaker + audit log.
   └─ For L3: require backup/canary/smoke/rollback evidence BEFORE execution.

7. AUDIT
   └─ Write structured audit event with classification, actor, scope, result.
   └─ Never log secrets, raw intimate data, or full surveillance content.
   └─ Hash-chain where applicable (P22 audit schema).
```

This sequence directly ties to:

- AGENTS.md §0.1: "Policy gates: engineering deployment (backup→canary→smoke→rollback), self-improvement (regression→audit→rollback-before-promote), daily-life (risk-classified action policies)."
- PersonaSafetyPolicy §15.1: "Tool-risk gate before filesystem/shell/git/API actions."
- PersonaSafetyPolicy §11 F-10: "Irreversible action under persona pressure → require non-persona confirmation+evidence."

### 3.5 Distress / Safe-Mode Freeze Table

| Distress Level | Signal | L1 Effect | L2 Effect | L3 Effect | L4 Effect |
|---|---|---|---|---|---|
| D0 Normal | None | Allowed | Allowed (with notify) | Requires approval | Blocked |
| D1 Mild | "Too much?", hesitation | Allowed | Soften tone; ask check-in | Escalate to Faiz | Blocked |
| D2 Clear Boundary | "Stop", "pause", safe word | Allowed | Pause new writes | Freeze until D0/D1 | Blocked |
| D3 Emotional Distress | Panic, overwhelm, crying | Allowed (neutral/supportive only) | Freeze L2+L3 | Freeze L2+L3 | Blocked |
| D4 Crisis Risk | Self-harm, harm, emergency | Trigger HARD STOP; neutral crisis mode | Trigger HARD STOP | Trigger HARD STOP | Blocked + alert |
| Y0 Safe Mode | Operator or system declares safe mode | Safety-only reads allowed | Freeze all non-safety | Freeze all non-safety | Blocked |

Source: PersonaSafetyPolicy §8 (lines 215-223), §9 Y0 (lines 247-265).

### 3.6 Consent Boundary Table

| Executor Surface | P23 Consent Scope Example | Default | Revocation | Cascade |
|---|---|---|---|---|
| Browser | `p23:browser:read`, `p23:browser:write` | Read OFF until authorized; write OFF | Per-scope revoke invalidates cache and executor token | Cascade to all open browser sessions |
| Desktop | `p23:desktop:read`, `p23:desktop:write` | Read OFF; write OFF | Per-scope revoke | Stop desktop agents, clear tmp |
| VPS | `p23:vps:read`, `p23:vps:write`, `p23:vps:destructive` | Read OFF; write/destructive OFF | Per-scope + per-host revoke | Kill SSH/shell sessions, purge keys |
| GitHub | `p23:github:read`, `p23:github:write`, `p23:github:destructive` | Read OFF; write/destructive OFF | Per-scope revoke | Invalidate token cache, stop adapters |
| Filesystem | `p23:fs:read:<path-class>`, `p23:fs:write:<path-class>` | Read OFF per class; write OFF | Per-path-class revoke | Close file handles, flush caches |
| Mobile | `p23:mobile:read`, `p23:mobile:write` | Read OFF; write OFF | Per-scope revoke | Stop push/notif agents |
| External | `p23:external:<provider>:read/write/destructive` | All OFF | Per-provider + per-scope revoke | Purge tokens, stop adapters |

Design notes for consent boundary:

- Reuse `consent_gate.py` fail-closed logic: validate scope, Redis cache, DB ledger, PAUSED/WITHDRAWN handling.
- L1 read may be pre-authorized by Faiz but still cached and auditable.
- Revocation is absolute and cannot be bypassed by autonomy (AGENTS.md §0.1 invariant 6).
- Revocation cascade must invalidate in-memory caches, Redis cache, and executor sessions.

### 3.7 Autonomy Resolution: "Faiz Silent → Continue" vs "Destructive Needs Approval"

| Tier | Autonomy Rule | Approval Rule | Rationale |
|---|---|---|---|
| L1 | Autonomous | None needed; silent is not a blocker | V-003: silence is not a blocker for read/idempotent ops |
| L2 | Autonomous + notify | Prior consent + notify after; no per-action approval | V-003 holds; write is bounded by consent and audit |
| L3 | Not autonomous | Explicit Faiz approval required, plus backup/canary/smoke/rollback | AGENTS.md §0.1 still-exempt list; F-10 irreversible action gate |
| L4 | Never allowed | Cannot be authorized | Safety invariant; consent cannot authorize |

Resolution rule: "Faiz silent → continue" applies to L1 and L2 only. L3 always stops for approval. L4 always blocks. Silence is NEVER interpreted as implicit approval for L3 or L4.

### 3.8 Self-Debug on Failure (V-007)

When an action fails at any step:

```text
1. CAPTURE FAILURE CONTEXT
   └─ Executor error, stderr, return code, correlation_id, retry count.
   └─ Snapshot current risk tier, consent state, distress level, namespace.

2. HERMES BRAIN THINK
   └─ Call HermesBrain.think() with failure context + journal (graph.py:108-135).
   └─ Prompt: "Given the failed action, propose ONE of: fix, rollback, escalate."
   └─ Never let the brain propose destructive actions without re-running the 7-step gate.

3. FIX / ROLLBACK / ESCALATE
   ├─ Fix: retry within executor timeout, with backoff.
   ├─ Rollback: restore from last known-good snapshot, revert candidate, clear state.
   └─ Escalate: queue for Faiz review if fix/rollback uncertain or L3 involved.

4. RE-QUEUE OR ROLLBACK
   ├─ If fix succeeds and is L1/L2: re-queue next action, continue autonomously.
   ├─ If fix succeeds and is L3: still await Faiz confirmation before promotion.
   └─ If rollback: restore, log, notify, stop related goals.

5. JOURNAL + AUDIT
   └─ Write structured journal entry (reflect_node:513-585).
   └─ Append audit event: failure, decision, recovery action, correlation_id.
```

Tie to V-007: "Audit exists for self-diagnosis and debugging, not as a default approval bottleneck." This means the kernel uses audit/journal to recover, but does NOT use them to bypass L3 approval.

### 3.9 Action Planner Priority Mapping

The planner must respect the P20 §6 autonomy priority order:

| Priority Rank | Category | Example P23 Actions |
|---:|---|---|
| 1 | HARD STOP, consent revocation, active safety halt | Stop all executors, clear sessions |
| 2 | Keep Guinevere alive, recoverable, debuggable | Heartbeat repair, log rotation, restart adapter |
| 3 | Protect secrets, personal data, memory integrity, audit integrity | Rotate token, quarantine leaked secret, revoke scope |
| 4 | Urgent daily-life signals: health/routine risk, important email, finance anomaly, deadline, security, service outage | Send health alert, notify calendar conflict, flag finance anomaly |
| 5 | Finish active commitments and autonomous sessions | Complete pending L1/L2 task, close loop |
| 6 | Improve Guinevere autonomy, skills, prompts, planning, tests, runtime | Propose self-improvement candidate, run regression gate |
| 7 | Advance engineering projects and external deliverables | Create branch, run tests, open PR (L2), deploy (L3) |
| 8 | Explore, research, learn, propose new directions | Read docs, survey tools, generate research report |

Planner model:

- Inputs: world-state + commitments + goals + concerns (P20 Vision Lock V-005).
- Outputs: ordered action queue with risk tier, executor surface, consent scope.
- Constraints: L3 never scheduled without approval gate; L4 never scheduled; distress levels apply freeze rules.
- The brain proposes; the static priority engine (graph.py:317-360) has final routing authority on HARD STOP/safety.

### 3.10 Special Policy-Gate Considerations

#### F-10: Irreversible Action Under Persona Pressure

Any action that is L3 or that writes to an external surface must pass the F-10 gate:

- Tool-action classifier flags irreversible or high-risk actions.
- Persona pressure detector checks if the action was proposed during intense yandere/punishment framing.
- If pressure + irreversible: require non-persona confirmation and evidence (e.g., rollback plan, backup checksum, Faiz explicit approval).
- This prevents persona intensity from coercing real-world irreversible actions.

#### Tool-Risk Gate (PersonaSafetyPolicy §15.1)

Before filesystem/shell/git/API actions:

- Identify actor (kernel, sub-agent, user).
- Identify executor surface and target.
- Run the 7-step policy gate.
- Block or rewrite if any step fails.
- Log minimal non-punitive audit event.

#### Self-Improvement Boundary (LK-015)

- ReflectionEvaluator proposes candidates (self_improve.py:128-165).
- RegressionGate runs tests; candidate is not promoted if tests fail (self_improve.py:289-363).
- Promotion of a code/skill/planner change is L2 or L3 depending on blast radius.
- No self-modification bypasses the policy gate or consent boundary.

---

## 4. Implications for P23 Design

1. **Executor Registry**: Build a registry of executor adapters (browser, desktop, VPS, GitHub, filesystem, mobile, external). Each adapter must export a `risk_class(action)` helper and an `execute(action, context)` method.

2. **Policy Gate as Middleware**: Every executor call goes through the 7-step gate. The gate is not optional and cannot be skipped by fast paths.

3. **Distress State Machine**: Integrate D0-D4 and Y0 safe-mode into the life-mind state so decide_node can freeze tiers before act_node runs.

4. **Consent Ledger Extension**: Extend `consent_gate.py` with P23 scopes. Reuse the same fail-closed Redis+DB cache pattern.

5. **Audit Schema**: Use the P22 `audit.integration_api_log` table or a P23-specific table with the same hash-chained, append-only properties.

6. **Self-Debug Loop**: Wire HermesBrain.think() failure analysis into the kernel so the kernel can propose fix/rollback/escalate, but never bypass L3 approval.

7. **Planner Integration**: Ensure the P20 planner emits action plans with `risk_tier`, `executor_surface`, and `consent_scope` so the gate can evaluate them.

---

## 5. Risks / Open Questions

| ID | Risk / Open Question | Suggested Follow-Up |
|---|---|---|
| RQ-01 | Exact distress classifier thresholds are undefined (PersonaSafetyPolicy §19). | Define D0-D4 classifier heuristics and tests before P23 implementation. |
| RQ-02 | Per-surface consent scopes are not yet in the consent ledger schema. | Add migration for `p23:*` scopes with the same fail-closed semantics. |
| RQ-03 | Executor-specific timeout/circuit-breaker values are not specified. | Define per-executor defaults (browser 30s, VPS 60s, external per-provider). |
| RQ-04 | How does the policy gate behave when Redis is down? | Fail-closed on safety: if HARD STOP or consent state cannot be confirmed, block non-essential actions. |
| RQ-05 | What constitutes "non-persona confirmation" for F-10? | Design a neutral-mode confirmation prompt/audit artifact requiring explicit Faiz acknowledgment. |
| RQ-06 | L3 backup/canary/smoke/rollback evidence format is not yet standardized. | Reuse P20 deployment policy evidence paths and add executor-specific artifacts. |
| RQ-07 | Mobile executor surface is vague (iOS/Android APIs, ADB, push). | Scope mobile to notification/read-only until a dedicated P23 mobile sub-phase. |
| RQ-08 | How are L2 notification channels prioritized under distress? | If D3/D4, suppress non-essential notifications; safety channels remain open. |

---

## 6. Recommendations to Planner

1. **Adopt the L1-L4 action-shaped risk tiers verbatim** as the P23 authorization matrix.
2. **Implement the 7-step policy gate as a core service** at `src/life_kernel/policy_gate.py` with no bypass.
3. **Extend `consent_gate.py`** to support P23 executor scopes while preserving fail-closed behavior.
4. **Integrate distress/safe-mode freeze table into `decide_node`** so L2/L3 actions are frozen before act_node runs.
5. **Require L3 approval evidence** (backup, canary, smoke, rollback plan) before any destructive executor runs.
6. **Build self-debug loop** around `HermesBrain.think()` with strict rule: it may propose, not auto-promote, and L3 still requires Faiz approval.
7. **Use P22 audit schema** (hash-chained, append-only) for all P23 action events.
8. **Add automated tests** for every forbidden pattern (F-01..F-15) as required by PersonaSafetyPolicy §17.

---

## 7. Verdict

P23 can proceed to planner gate only after the policy gate and risk classification are accepted as binding. The framework in this document is consistent with AGENTS.md §0.1, PersonaSafetyPolicy §8/§10/§11/§15.1, P20 Vision Lock §6/§7, and P22 L1-L4 authorization matrix. The kernel's existing `heartbeat.py`, `graph.py`, `self_improve.py`, and `consent_gate.py` provide the runtime substrate to enforce it.

**Verdict:** ACCEPT for planner input. P23 action policy gate and risk classification are ready for design freeze.

---

*File: `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md`*
