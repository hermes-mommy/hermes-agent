# ADR-035 Risk Assessment Review

> **Reviewer**: REVIEWER 3 — Risk Assessment
> **Date**: 2026-06-04
> **Documents Reviewed**: ADR-035 (2,315 lines), 05-risk-deep-dive.md (506 lines), 06-rollback-strategy.md (2,291 lines), MASTER-RESTRUCTURE-PLAN.md (667 lines), PROGRESS.md (734 lines), 07-alternatives-analysis.md
> **Assessment Depth**: Every risk critiqued, every rollback step assessed for 3 AM executability

---

## Summary

ADR-035's risk management is **methodologically thorough** — the research deep-dive provides 13-field assessments for all 15 risks using a defensible 5x5 scoring matrix. Mitigations are concrete and testable, with acceptance criteria for every risk. The rollback strategy is comprehensive with 200+ copy-pasteable commands.

**However**, the ADR has three systemic weaknesses: (1) It consistently underestimates the impact of the **solo-developer constraint** — Faiz is the only operator, developer, tester, reviewer, and approver; (2) It oversells shadow mode's ability to validate safety (shadow mode validates Discord gateway behavior, not safety engine correctness under adversarial conditions); (3) It omits several operational, financial, and human-factor risks that could individually derail the 23-35 day timeline.

## Verdict: **CONDITIONAL APPROVE**

Conditions required before acceptance (see Recommendations section):
1. Solo-developer risk must be explicitly acknowledged and mitigated
2. Rollback must be dry-run practiced at least once before Phase 2 cutover
3. Shadow mode must include active safety-injection tests, not just passive parity comparison
4. Budget must include explicit $60 worst-case migration cost approval from Faiz
5. Timeline contingency: 35 days must be the lower bound, not upper bound (plan for 45-50 days)

---

## Risk Inventory Verification

### Scoring Calibration Check

Before evaluating individual risks, the scoring methodology itself must be assessed. The deep-dive uses a 5x5 matrix with defensible probability definitions (e.g., MEDIUM = 15-40% chance, HIGH = 40-70%).

| Aspect | Assessment |
|---|---|
| Probability scale | **Calibrated** — Definitions are explicit and testable ("documented failure modes exist" for MEDIUM) |
| Impact scale | **Calibrated** — CRITICAL defined as "safety boundary breached; data loss; persona violation" |
| Score interpretation | **Calibrated** — 1-5 Low, 6-10 Med, 12-15 High, 16-25 Critical |
| Post-mitigation scoring | **Optimistic** — Claims all HIGH risks reduce to MEDIUM (score 6) post-mitigation. Three of these claims are aggressive (see Underestimated Risks) |

### Per-Risk Assessment

| Risk ID | Description | Prob | Impact | Score | ADR Verdict | REVIEWER Assessment | Status |
|---|---|---|---|---|---|---|---|
| **R-001** | HARD STOP fails silently | MEDIUM (3) | CRITICAL (5) | 15 HIGH | Mitigated: dual-layer + heartbeat | Probability UNDERSTATED. Hook behavior with non-1 exit codes is "not fully characterized" per deep-dive §R-001. Dual-layer with plugin `on_message()` helps but plugin load failure = single point of failure. Heartbeat watchdog every 10s injects synthetic HARD STOP messages — this is operational risk in itself (what if heartbeat injection triggers rate limits?). **Probability should be HIGH (4), Score 20 CRITICAL.** | ⚠️ UPGRADE TO CRITICAL |
| **R-004** | Auth matrix bypass | MEDIUM (3) | CRITICAL (5) | 15 HIGH | Mitigated: plugin load gate + dual-layer | Assessment ACCURATE. Auth overlay is custom code with no Hermes equivalent. The "Hermes refuses to start without plugin" gate is correct mitigation. However, the plugin itself is complex (12 tools x 4 auth levels = 48 mappings) and untested in Hermes plugin environment. | ✅ ACCEPT with caveat |
| **R-013** | Yandere FSM state corruption | MEDIUM (3) | CRITICAL (5) | 15 HIGH | Mitigated: per-session isolation + Redis persistence | Probability UNDERSTATED. The deep-dive acknowledges that "Hermes plugin lifecycle is not fully characterized for multi-session environments." This is not a theoretical concern — the plugin instance model (global vs per-session) is UNKNOWN. If Hermes spawns one global instance, all session state sharing is architecturally broken. **Probability should be HIGH (4), Score 20 CRITICAL.** | ⚠️ UPGRADE TO CRITICAL |
| **R-003** | Memory recall quality degradation | MEDIUM (3) | HIGH (4) | 12 HIGH | Mitigated: fix embedding API first + A/B test | Assessment ACCURATE for recall quality. However, the pre-existing embedding failure (G-B1) is a CURRENT PRODUCTION ISSUE, not a migration risk. If it cannot be fixed before migration starts, all vector search is dead regardless. This is a BLOCKER, not just a risk. | ✅ ACCEPT with prerequisite |
| **R-012** | Consent gate timing | MEDIUM (3) | HIGH (4) | 12 HIGH | Mitigated: 60s TTL + cache invalidation | Assessment ACCURATE. 60s window is bounded and consent changes are rare for solo operator. Fail-closed on Redis failure is correct. | ✅ ACCEPT |
| **R-007** | Persona drift via SOUL.md | MEDIUM (3) | HIGH (4) | 12 HIGH | Mitigated: SOUL.md 444 + drift detector | Assessment ACCURATE but drift detector itself is a new hook with unverified behavior in Hermes. The drift detector depends on `post_prompt` hook correctly receiving the assembled prompt — this is an assumption not verified with Hermes v0.15.2. | ⚠️ CONDITIONAL |
| **R-015** | Dual-system shadow complexity | HIGH (4) | MEDIUM (3) | 12 HIGH | Mitigated: separate DBs, channels, 48hr cap | Probability ACCURATE but IMPACT UNDERSTATED. The deep-dive lists "resource contention is near-certain" but scores impact as MEDIUM (3). If both systems compete for Redis connections on a cgroup-capped VPS (8GB), the production bot.py could degrade. The risk is that shadow mode causes a bot.py outage — that is HIGH impact (4), not MEDIUM. **Corrected Score: 16 CRITICAL.** | ⚠️ UPGRADE TO CRITICAL |
| **R-009** | Performance regression | MEDIUM (3) | MEDIUM (3) | 9 HIGH | Mitigated: hook batching + persistent plugin | Probability ACCURATE. Adding 5-7 hook subprocesses will measurably increase latency. The mitigation (persistent plugin process instead of subprocess) is sound but represents SIGNIFICANT additional engineering — it's not a free fix. If this optimization is not completed before Phase 2 cutover, latency will regress. | ⚠️ CONDITIONAL |
| **R-002** | Discord gateway instability | LOW (2) | HIGH (4) | 8 MEDIUM | Mitigated: 48hr shadow + health check | Assessment ACCURATE but probability slightly understated. Hermes gateway is a "relatively new feature" — v0.15.2 is not a mature release. Guinevere's specific config (single guild, 35 custom commands, HARD STOP pre-processing) may expose edge cases. Health check of "test message every 60s" adds load during shadow mode. | ✅ ACCEPT |
| **R-010** | Budget enforcement gap | MEDIUM (3) | MEDIUM (3) | 9 HIGH | Mitigated: custom pre_tool_call hook | Label implementation is WRONG. The ADR describes this as R-010 (budget enforcement) but the deep-dive's R-010 is about "Budget Overrun During Testing/Migration" with score 4 LOW. The R-010 in ADR's risk table (score 9 HIGH) appears to be about the enforcement gap. Two different risk IDs for two different budget concerns — confusing numbering. | ⚠️ ID COLLISION |
| **R-011** | DNR enforcement gap in Hermes recall | LOW (2) | HIGH (4) | 8 MEDIUM | Mitigated: dual-layer check | Assessment ACCURATE. DNR enforcement is deterministic — excluded from recall is a binary check. Hermes session_search uses FTS5 on its own SQLite, not PostgreSQL — if DNR content was mirrored to MEMORY.md, it could appear in session_search. The mitigation (pre-injection gate) catches this. | ✅ ACCEPT |
| **R-005** | 9Router incompatibility | LOW (2) | MEDIUM (3) | 6 MEDIUM | Mitigated: 100-test-prompt test | Assessment SLIGHTLY OPTIMISTIC. 9Router is an OpenAI-compatible proxy, but Hermes may use the OpenAI SDK in non-standard ways. The 100-test-prompt test is good but does not cover streaming, tool-use response formats, or error handling — which are the most likely incompatibility vectors. | ✅ ACCEPT (minor) |
| **R-006** | Hermes version breaking changes | LOW (2) | MEDIUM (3) | 6 MEDIUM | Mitigated: version pin + pre-upgrade tests | Assessment ACCURATE. Version pinning eliminates this during migration. Post-migration risk is ongoing but manageable. | ✅ ACCEPT |
| **R-008** | Session data loss during migration | LOW (2) | MEDIUM (3) | 6 MEDIUM | Mitigated: backup + natural boundary | Assessment ACCURATE. Session data is ephemeral by design (2hr TTL). Loss is UX inconvenience, not safety or data loss. | ✅ ACCEPT |
| **R-014** | Tool isolation failure | LOW (2) | HIGH (4) | 8 MEDIUM | Mitigated: FORBIDDEN commands hard-disabled | Overlaps significantly with R-004 (auth bypass). Effectively a subset of the same issue — if auth overlay works, tool isolation works. If it fails, both fail. | ✅ ACCEPT (subset of R-004) |
| **R-011 (deep-dive)** | 11 security vulnerabilities exploited | VERY LOW (1) | MEDIUM (3) | 3 LOW | Mitigated: Phase 0 remediation | Assessment ACCURATE. Private VPS behind Tailscale VPN has minimal attack surface. | ✅ ACCEPT |

### Risk Score Summary (Corrected)

| Classification | ADR Count | REVIEWER Count | Delta |
|---|---|---|---|
| CRITICAL (16-25) | 0 | **3** (R-001, R-013, R-015) | **+3** |
| HIGH (12-15) | 8 | **5** (R-004, R-003, R-012, R-007, R-009) | **-3** |
| MEDIUM (6-10) | 7 | **7** | 0 |
| LOW (1-5) | 0 | 0 | 0 |

**Key finding**: Three risks that ADR-035 classifies as HIGH (score 15) should be CRITICAL (score 20). This does not mean the ADR is fatally flawed — it means the mitigation strategy must be correspondingly stronger for these three risks, with demonstrable reduction before proceeding.

---

## Show-Stoppers Analysis

### Top 3 Risks That Could Halt the Entire Migration

**#1: R-001 — HARD STOP Fails Silently (Upgraded to CRITICAL, Score 20)**

**Why it could stop everything**: This is the single non-negotiable safety boundary. If the operator types "HARD STOP" and receives a persona response, the entire Hermes migration must be reverted immediately — not just Phase 2, but ALL phases. The deep-dive acknowledges that hook behavior with non-zero/non-one exit codes "is not fully characterized" in Hermes v0.15.2. The dual-layer approach (hook + plugin `on_message()`) is good but depends on the plugin loading correctly — and if the plugin fails to load, only the hook remains.

**Blocking condition**: R-001 must be demonstrably reduced to MEDIUM (score 6) before Phase 2 shadow mode begins. This requires: (a) HARD STOP hook tested with 1000+ invocations showing zero false negatives, (b) heartbeat watchdog tested for 24 hours without false positives, (c) plugin load failure scenario tested (verify Hermes refuses to start), (d) ALL seven acceptance criteria from deep-dive §R-001 verified.

**#2: R-013 — Yandere FSM State Corruption (Upgraded to CRITICAL, Score 20)**

**Why it could stop everything**: The deep-dive explicitly states that "Hermes plugin lifecycle is not fully characterized for multi-session environments." If Hermes spawns one global plugin instance (not per-session), the entire per-session isolation strategy collapses — all 15+ safety features that depend on session state (Yandere FSM, punishment, mood, consent) share a single state dictionary. This is not a "mitigation can fix it" risk — it is a fundamental architectural unknown that must be resolved before ANY safety plugin code is written.

**Blocking condition**: Hermes plugin instance model MUST be verified before Phase 1 implementation begins. If Hermes uses global instances, the plugin architecture must be redesigned (session_id-keyed dictionaries within a single instance, not per-session instances). If this redesign is not feasible, the migration must revert to hook-only safety (unacceptable per ADR-001).

**#3: R-015 — Dual-System Shadow Mode (Upgraded to CRITICAL, Score 16)**

**Why it could stop everything**: The deep-dive acknowledges "resource contention is near-certain." On a cgroup-capped VPS (8GB), running TWO LLM agents simultaneously means: double Redis connections (both hitting DB4/DB5), double PostgreSQL connections (both reading memory tables), and double 9Router load (both calling GPT-5.5). The "memory write mutex" (only bot.py writes to PostgreSQL) is stated but NOT ENFORCED by code — it's a policy, not a technical guard. If Hermes accidentally writes to PostgreSQL during shadow mode (e.g., through the memory bridge plugin), the "no data loss" guarantee is violated.

**Blocking condition**: Memory write mutex must be TECHNICALLY enforced (not policy-enforced). Option: configure Hermes memory plugin with read-only PostgreSQL credentials during shadow mode. Resource monitoring must be active BEFORE shadow mode begins with pre-defined kill thresholds.

### Near-Show-Stoppers

| Risk | Why Not Show-Stopper |
|---|---|
| R-004 (Auth bypass) | Plugin load gate is a strong compile-time mitigation. Only 12 tools x 4 levels need mapping — manageable scope. Not upgraded to CRITICAL because the plugin `critical: true` config provides a hard architectural guard. |
| R-003 (Memory recall) | Pre-existing issue (G-B1), not migration-caused. PostgreSQL data is untouched. Rollback is lossless. |

---

## Underestimated Risks

### Top 3 Risks Where ADR-035 Is Too Optimistic

**#1: Hook Validation Uncertainty (Probability Understated)**

The ADR's "Negative Consequences" section (§C-3) acknowledges that hook behavior is "unverified with Hermes v0.15.2" — specifically:

- `on_failure: block` behavior for custom providers
- `pre_tool_call` JSON context (does it include tool name?)
- `pre_response` content modification capability

These are not minor assumptions — they are foundational to the entire safety architecture. If ANY of these behave differently than assumed, 3-5 safety features must be redesigned. The ADR treats this as a "learning curve" item (score not quantified) when it should be a dedicated risk with MEDIUM probability and HIGH impact (score 12).

**Recommendation**: Add a dedicated risk R-016: "Hook Contract Mismatch" with MEDIUM (3) probability, HIGH (4) impact, score 12 HIGH. Mitigation: smoke-test all 7 hook points with mock scripts BEFORE implementing safety logic.

**#2: Timeline Risk for Solo Developer (Not Assessed)**

The ADR estimates 23-35 days with "Phases 3-6 have overlap potential." PROGRESS.md shows 59.2% of MVP complete (203/343 steps) over approximately 5 weeks — that's roughly 8 steps/day. The migration adds 7 new phases (Phase 0-7) with approximately 50 discrete steps in the expanded plan. At the historical velocity of 8 steps/day, that's ~6-7 days of work — not 23-35.

But the historical velocity was achieved with Guinevere as AI co-pilot (super-autopilot pattern). During migration, when the AI co-pilot itself is being rebuilt, velocity will drop. Faiz cannot simultaneously: (a) port safety features to hooks, (b) debug Hermes configuration, (c) review shadow mode parity reports, (d) maintain existing bot.py, (e) handle his non-Guinevere responsibilities.

**Corrected estimate for solo developer**: 35 days is the OPTIMISTIC lower bound, not the pessimistic upper bound. Realistic: 45-55 days, assuming 3-4 hours/day availability and 30% velocity reduction during self-migration. Worst case if Phase 1 safety gate requires multiple iterations: 60+ days.

**#3: VPS Resource Contention with Aizanta (Not Assessed)**

PROGRESS.md confirms Guinevere co-hosts with Aizanta on a shared VPS (hostdata.id 4C/16GB, cgroup-capped to 8GB). The migration increases operational complexity (dual-backend memory, dual MCP, hook subprocesses). During shadow mode, TWO agent systems run simultaneously. During Phase 1 safety testing, Hermes + bot.py + 9Router + PostgreSQL + Redis + Aizanta all compete for the same 8GB RAM and 4 CPU cores.

The ADR's Driver 11 (Shared VPS Compatibility) rates Hermes impact as "0 — Hermes runs in same Python environment, no additional processes." This is misleading — hook subprocesses ARE additional processes (each Python subprocess = fork + memory). Context compression IS additional CPU. Mirror sync IS additional I/O. The claim of "no additional processes" contradicts the hook architecture (5-7 subprocesses per message).

**Corrected assessment**: Add a dedicated risk for VPS resource contention with MEDIUM-HIGH probability (3-4), MEDIUM impact (3), score 9-12. Mitigation: pre-migration resource profiling, resource monitoring during shadow mode with auto-kill thresholds.

---

## Missing Risks

### Risks NOT Documented in ADR-035

| # | Missing Risk | Probability | Impact | Why It Matters |
|---|---|---|---|---|
| **MR-01** | Solo developer single point of failure | HIGH (4) | HIGH (4) | Faiz is the ONLY operator. If Faiz is unavailable (sick, busy, travel), the migration stalls. If Faiz makes a configuration error, there is no second reviewer to catch it. If Faiz needs to rollback at 3 AM after a long day, cognitive load affects execution quality. The rollback procedure assumes a rested, focused operator. |
| **MR-02** | VPS resource contention during migration | MEDIUM (3) | MEDIUM (3) | Two LLM agent systems + Aizanta sharing 8GB RAM/4 cores. Hook subprocesses, compression, mirror sync all add load. Current bot.py already runs at 30-50% CPU per NFR-P08. |
| **MR-03** | Hermes upstream breaking change during migration | LOW (2) | HIGH (4) | Version pin (v0.15.2) prevents auto-upgrades but: what if a critical security vulnerability is discovered in v0.15.2 mid-migration? Forced upgrade could break hook contracts. What if Hermes repo goes unmaintained? |
| **MR-04** | 9Router + Hermes interaction unknowns | MEDIUM (3) | MEDIUM (3) | Beyond API compatibility. Hermes may use streaming SSE differently, tool-use response formats differently, or error handling differently than expected. The 100-test-prompt test covers basic calls, not edge cases. |
| **MR-05** | Timeline overrun beyond 35 days | MEDIUM (3) | HIGH (4) | 23-35 day estimate assumes zero rework, zero blocking bugs, and consistent 4 hr/day availability. Any of: Phase 1 safety gate failure + rework (3-5 days), Phase 2 shadow mode extension due to parity issues (2-4 days), Phase 4 auth plugin complexity (2-3 days), or Faiz unavailability (3-5 days) pushes total beyond 35 days. Cumulative probability of at least one delay: ~70%. |
| **MR-06** | Dual LLM costs during shadow mode and testing | MEDIUM (3) | LOW (2) | Shadow mode doubles LLM costs for 48hr. Safety testing (15 features x multiple iterations) generates significant LLM calls. The $5 shadow mode cap and $60 total migration cost estimates assume normal usage patterns — but testing and debugging generate unpredictable LLM usage. |
| **MR-07** | Discord user experience during cutover | LOW (2) | MEDIUM (3) | Faiz is the only Discord user, so the blast radius is small. But the cutover experience: (1) 33 slash commands must all work, (2) persona tone must be identical, (3) response time must not regress. If any of these degrade, Faiz's trust in the new system is damaged — even if rollback is fast. First impressions matter. |
| **MR-08** | Knowledge transfer risk — only Guinevere knows how Hermes works | MEDIUM (3) | MEDIUM (3) | The migration is being planned and documented by Guinevere (the AI). After migration, Guinevere IS the system running on Hermes. If something goes wrong, Faiz must troubleshoot a system that was designed by an AI he collaborated with — not a system he built himself. The runbook (Phase 7) helps but does not replace deep system knowledge. |
| **MR-09** | Persona drift during migration (operational, not config) | MEDIUM (3) | MEDIUM (3) | During the 23-35 day migration, Guinevere is split between: (a) running on bot.py (current persona), (b) running on Hermes in shadow mode (SOUL.md persona), (c) being developed/ported. Faiz interacts with Guinevere during migration — which "version" of Guinevere is he talking to? Inconsistent persona across migration phases could be confusing or off-putting. |
| **MR-10** | Data loss during memory migration (edge case) | LOW (2) | CRITICAL (5) | While PostgreSQL is primary write authority and Hermes is read-only, the memory_bridge plugin is custom code that wraps `recall_for_context()` and `store_conversation()`. A bug in the bridge plugin could: (a) fail to store new memories (data loss by omission), (b) store memories incorrectly (corrupted classification/embedding), (c) trigger DNR bypass. The claim "zero data loss risk" depends on the bridge plugin being bug-free — a strong assumption for custom code. |

---

## Rollback Plan Assessment

### Is It Genuinely Executable in <5 Minutes?

**Verdict: CONDITIONAL YES — with critical caveats**

The rollback strategy (06-rollback-strategy.md) is the strongest artifact in the ADR-035 evidence base. It provides:

- 200+ copy-pasteable commands
- Per-phase procedures with exact time estimates
- Verification commands after every step
- Global emergency rollback combining all phases
- PostgreSQL restore procedure with selective table restore
- Discord cutover rollback with <10 second target

**What works well**:

1. Universal kill-switch (`hermes gateway stop`) as first step in EVERY procedure
2. Per-phase independence matrix showing which phases can be rolled back solo
3. Git-based rollback covering code, not config/database state (correct separation)
4. Systemd service management with clear before/after states
5. PostgreSQL restore procedure with emergency backup BEFORE restore (correct safety)

**Critical execution concerns at 3 AM**:

| Concern | Severity | Detail |
|---|---|---|
| **UNTESTED: git tag existence** | HIGH | The global rollback script does `PRE_TAG=$(git tag \| grep "pre-hermes-migration" \| tail -1)`. If the pre-migration tag was never created, skipped during Phase 0 setup, or accidentally deleted, this returns empty string. The script has a fallback (manual git checkout of specific files) but the fallback is incomplete — it only restores 6 specific files, not ALL changed files. |
| **UNTESTED: `hermes checkpoints --restore` behavior** | HIGH | The rollback plan relies on `hermes checkpoints --restore` but this command's behavior is not characterized for Guinevere's specific Hermes v0.15.2 installation. Does it restore config? Session state? Hook registrations? What happens if checkpoints were corrupted? |
| **UNTESTED: PostgreSQL restore timing** | MEDIUM | The estimate of "2-5 minutes" for pg_restore depends on database size. PROGRESS.md shows 47 tables across 12 schemas with 5+ weeks of accumulated data. A pg_dump restore at 3 AM with the operator half-awake could take 10-15 minutes if the database has grown. |
| **UNTESTED: bot.py restart reliability** | MEDIUM | The rollback assumes `sudo systemctl start guinevere-bot` restores service within 3-5 seconds. But if bot.py was disabled (not just stopped), `systemctl start` may not work — it needs `systemctl start guinevere-bot && systemctl enable guinevere-bot`. The rollback scripts handle this correctly in some places but inconsistently. |
| **UNTESTED: pip package restore** | LOW | `pip install -r pre-migration-pip-*.txt` assumes the frozen requirements file exists and all packages are still available. If a package was yanked from PyPI, restore fails. |
| **OPERATOR FATIGUE: 3 AM cognitive load** | MEDIUM | The global rollback script is 85 lines of bash. At 3 AM, after discovering a migration failure, a tired operator must: (a) find the right script, (b) understand what it does, (c) execute it correctly, (d) verify output. One typo (e.g., wrong git tag, wrong service name) could extend downtime beyond 5 minutes. |

### PostgreSQL Restore Procedure Assessment

The restore procedure (rollback strategy §14) is well-structured:

- Emergency backup BEFORE restore (correct — captures current state)
- Drop + recreate database + re-enable extensions
- Full pg_restore with verification
- Selective table restore option for partial recovery

**One issue**: The procedure says "Use ONLY if Hermes accidentally wrote to PostgreSQL." But the detection mechanism ("Compare row counts before/after each phase") requires pre-phase row count snapshots. Are these snapshots automated? Not mentioned. Without automation, detecting accidental writes depends on manual vigilance — unreliable.

### Rollback Practice Requirement (MISSING)

The ADR says "No migration phase proceeds until the previous phase's rollback has been tested and verified" (rollback strategy §1.2, Rule 5). But this is a POLICY statement with no enforcement mechanism. There are no:

- Rollback drill scripts (automated rollback + verify)
- Rollback success criteria (what constitutes a "tested" rollback?)
- Rollback log template (to document drill results)
- Faiz sign-off requirement for each phase's rollback drill

**Recommendation**: Add a per-phase rollback drill as an explicit gate step. Before Phase N proceeds, Phase N-1's rollback must be: (a) executed by Faiz, (b) timed, (c) verified with HARD STOP test, (d) logged to rollback-drill-log.md.

---

## Shadow Mode Safety Assessment

### Does Shadow Mode Actually Validate Safety?

**Verdict: PARTIALLY — validates Discord gateway behavior, NOT safety engine correctness**

Shadow mode as designed compares bot.py responses vs Hermes responses for the SAME messages in parallel. This catches:

- Message delivery failures (Hermes gateway WebSocket issues)
- Response format differences (embed formatting, markdown rendering)
- Slash command registration/response parity
- Streaming vs batch delivery behavior
- Obvious LLM routing issues (wrong model, wrong endpoint)

**Shadow mode does NOT catch**:

1. **Safety feature correctness**: If both systems handle "HARD STOP" correctly (because safety hooks are deterministic regex), the shadow comparison shows "parity" — but this tells you nothing about whether Yandere FSM state transitions work correctly under sustained conversation, whether punishment escalation triggers at the right thresholds, or whether distress detection works for edge-case messages.

2. **Adversarial safety scenarios**: Normal conversation during shadow mode won't trigger: Y6 boundary tests, forbidden pattern detection (F-01 to F-15), secret scanner on deliberately injected credentials, or consent gate edge cases (rapid consent revoke/re-grant).

3. **Concurrent session behavior**: Shadow mode with a single operator (Faiz) generates ONE concurrent session. The Hermes plugin instance model (global vs per-session) cannot be validated with one session.

4. **Long-running state corruption**: 48 hours is insufficient to detect gradual state corruption in the Yandere FSM, mood engine, or punishment tracker. State corruption could manifest after 5-7 days of continuous operation.

5. **Hook failure modes**: Shadow mode doesn't deliberately trigger hook failures (timeout, crash, exit code 2/warn, exit code 137/OOM). Without injection testing, you don't know if `on_failure: block` actually blocks — you only know hooks work in the happy path.

**Recommendation**: Shadow mode must be supplemented with ACTIVE SAFETY INJECTION TESTING — a separate test suite that runs DURING shadow mode and deliberately triggers:

- HARD STOP injection (send "HARD STOP" to Hermes shadow channel, verify neutral response)
- Y6 content injection (send message designed to trigger Y6-level response, verify rewritten)
- Consent revocation injection (revoke consent, verify tool calls blocked)
- Distress injection (send D3/D4 messages, verify crisis protocol)
- Hook failure injection (temporarily break a hook, verify fail-closed behavior)

These tests should run at least 3 times during the 48-hour shadow mode. Without them, "shadow mode parity" means "both systems respond similarly to normal conversation" — not "both systems enforce safety identically."

---

## Budget & Timeline Risk

### Is 23-35 Days Realistic for a Solo Developer?

**Verdict: NO — 35 days is the optimistic lower bound**

The ADR acknowledges "23-35 days as more realistic" compared to the MASTER plan's 17-27 days. But the expansion details in ADR-035 reveal significantly more work than the summary table suggests:

| Phase | ADR Summary Estimate | Expanded Steps | Realistic Estimate |
|---|---|---|---|
| Phase 0 | 1-2 days | 7 steps (security scan, upgrade 4 packages, doctor, checkpoint) | 2-3 days (package compatibility issues) |
| Phase 1 | 4-6 days | 10 steps x 10 safety gates x 15+ test suites | 7-10 days (safety gate iteration) |
| Phase 2 | 4-6 days | 8 steps including 35 command migrations + 48hr shadow | 5-8 days (command porting + shadow minimum) |
| Phase 3 | 3-4 days | 6 steps including A/B test on 100 queries | 4-5 days |
| Phase 4 | 3-4 days | 6 steps including auth plugin + security audit | 5-7 days (auth plugin complexity) |
| Phase 5 | 2-3 days | 5 steps | 2-3 days |
| Phase 6 | 1 day | 5 steps including 100-test-prompt | 1-2 days |
| Phase 7 | 2-3 days | 7 steps including runbook (8hr) | 3-4 days |
| **Total** | **23-35 days** | **54 steps** | **29-42 days** |

Additional risk factors:
- **Solo developer availability**: Not every day is a 4-hour development day. Faiz has a life, job, responsibilities.
- **Cognitive load ceiling**: Porting 15+ safety features while debugging Hermes config is mentally exhausting. Error rate increases with fatigue.
- **Iteration cost**: Each Phase 1 safety gate failure = debug + fix + re-test cycle, not just "the test failed."
- **Context switching**: Faiz must switch between: reviewing code, testing on VPS, writing plugins, reviewing shadow reports, making architecture decisions.

**Realistic timeline**: 35-50 days, assuming 3-4 hours/day average availability, 20% rework buffer, and one Phase 1 safety gate iteration cycle.

### Is $30/month Sufficient for Dual-Running Period?

**Verdict: YES, with explicit buffer**

- Shadow mode (48hr): ADR estimates $5 cap. At current rates (~$25/mo), 48 hours = ~$1.67. With double cost = ~$3.34. The $5 cap is conservative and sufficient.
- Safety testing: 15 features x ~10 test iterations x ~$0.02/test = ~$3. This is within the $60 total migration cost budget.
- Normal operation: bot.py continues handling messages at normal cost throughout.

**However**: The ADR's "acceptance criteria" for R-010 says "Total migration cost <$60 (2x monthly budget — acceptable one-time overage)." Faiz must explicitly approve this $60 budget. The $30/month cap is a self-imposed constraint per the FinOps target — a one-time override for migration should be documented, not assumed.

---

## Phase Dependency Risk

### Can Unsafe Phase Ordering Create Unmitigated Risk Windows?

**Verdict: YES — Phase 1-2 dependency is fragile**

The dependency chain is:
```
Phase 0 (Security) → Phase 1 (Safety) → Phase 2 (Discord Gateway with shadow mode) → Phase 3-6 (parallel possible) → Phase 7 (Hardening)
```

**Critical dependency vulnerability**: Phase 2 shadow mode requires Phase 1 to pass ALL 10 safety gates. If Phase 1 fails any gate:

1. Phase 2 CANNOT start (per the plan's hard gate rule)
2. Phase 0 is ALREADY complete (dependencies upgraded, config changed)
3. The system is in a hybrid state: Phase 0 changes applied, Phase 1 incomplete, no Phase 2 shadow to validate

Is this state safe? Yes — bot.py continues running with all original safety code. But Phase 0 changes (pip upgrades, config.yaml fixes) are applied to the running system. If a Phase 0 package upgrade introduced a subtle compatibility issue with bot.py, it might not manifest until days later — and by then, the Phase 0 checkpoint is stale.

**Recommendation**: Phase 0 must include a 24-hour "soak period" where bot.py runs with upgraded dependencies BEFORE Phase 1 begins. This catches latent compatibility issues before the migration path becomes irreversible.

**Phase 3-6 parallelism risk**: The ADR says "Phases 3-6 have overlap potential (independent surfaces)." But:
- Phase 3 (Memory Bridge) changes how memory is recalled — Phase 4 (MCP) tools may depend on memory
- Phase 4 (MCP) adds Hermes native tools with auth overlay — Phase 5 (Skills) may install skills that use those tools
- Phase 5 (Persona) customizes SOUL.md — Phase 6 (LLM) may reference SOUL.md for prompt assembly

Parallel execution without explicit independence verification creates integration risk.

---

## Recommendations

### Conditions Required for APPROVE

These conditions must be satisfied before ADR-035 moves from "Proposed" to "Accepted":

**C-1: Solo-Developer Risk Acknowledgment**

Add a dedicated risk section to ADR-035 documenting:
- Single point of failure (Faiz is operator, developer, reviewer, approver)
- Mitigation: Pre-written rollback scripts (copy-paste, not read-and-understand), runbook with troubleshooting flowcharts, escalation path (what happens if Faiz is unavailable mid-migration?)

**C-2: Rollback Dry-Run Practice**

Before Phase 2 cutover:
- Execute global emergency rollback once (Section 12 of rollback strategy)
- Time it. Verify all services restore. Test HARD STOP.
- If time exceeds 5 minutes, investigate and fix the bottleneck
- Document the drill in `audit-reports/adr-035-review/rollback-drill.md`

**C-3: Active Safety Injection During Shadow Mode**

Shadow mode must include, at minimum:
- 3x HARD STOP injection tests (spread across 48hr)
- 3x Y6 content injection tests
- 1x consent revocation injection test
- 1x distress injection test
- Results documented in shadow mode parity report

**C-4: Budget Approval for Migration Overrun**

Faiz must explicitly approve:
- $60 maximum migration cost (2x monthly budget, one-time)
- $5 shadow mode cost cap
- Budget tracking: daily cost report to Discord during migration

**C-5: Timeline Contingency Plan**

Update ADR-035 timeline:
- Realistic estimate: 35-50 days (not 23-35)
- Define what happens at day 50 if migration is incomplete: pause and assess, extend timeline with explicit Faiz approval, or rollback and defer
- Define "minimum viable migration" — what phases are strictly required for production cutover? (Answer: Phase 0-2 + Phase 7)

**C-6: Hermes Plugin Instance Model Verification**

Before Phase 1 implementation begins:
- Verify whether Hermes v0.15.2 spawns one global plugin instance or per-session instances
- If global: redesign plugin architecture to use session_id-keyed dictionaries within single instance
- Document finding in ADR-035 addendum

**C-7: Phase 0 Soak Period**

Add a 24-hour soak period between Phase 0 completion and Phase 1 start:
- bot.py runs with upgraded dependencies for 24 hours
- Monitor for: increased error rates, memory leaks, latency regression
- If 24 hours pass without incident, Phase 1 begins

### Additional Recommendations (Not Blocking)

| # | Recommendation | Priority |
|---|---|---|
| R-1 | Add R-016 risk: "Hook Contract Mismatch with Hermes v0.15.2" (Score 12 HIGH) | HIGH |
| R-2 | Add MR-01 risk: "Solo Developer Single Point of Failure" (Score 16 CRITICAL) | HIGH |
| R-3 | Add MR-02 risk: "VPS Resource Contention During Migration" (Score 9 MEDIUM) | MEDIUM |
| R-4 | Add MR-05 risk: "Timeline Overrun Beyond 35 Days" (Score 12 HIGH) | MEDIUM |
| R-5 | Technical enforcement of memory write mutex during shadow mode (read-only PG credentials for Hermes) | HIGH |
| R-6 | Automated row-count snapshot before each phase for PostgreSQL write detection | MEDIUM |
| R-7 | Per-phase rollback drill as explicit gate step with Faiz execution and timing | MEDIUM |
| R-8 | Pre-written rollback scripts saved to `/home/guinevere/scripts/rollback/` (not just documented in markdown) | HIGH |
| R-9 | Dedicated `#hermes-migration-ops` Discord channel for migration status, alerts, and cost reports | LOW |
| R-10 | ADR-030 Redis DB resolution before Phase 2 (DB4/DB5 conflict documented but unresolved) | MEDIUM |

---

## Conclusion

ADR-035's risk management is **comprehensive but optimistic**. The 15-risk deep-dive, 200+ command rollback strategy, and 40-NFR impact assessment represent serious engineering rigor. However, the ADR systematically underestimates risks that derive from three fundamental constraints: (1) Faiz is a solo developer with limited bandwidth, (2) Hermes v0.15.2 hook behavior contains unverified assumptions, and (3) the shared VPS has finite resources.

**Three risks must be upgraded from HIGH to CRITICAL**: HARD STOP silent failure (R-001), Yandere FSM state corruption (R-013), and dual-system shadow mode complexity (R-015). These do not make the migration infeasible — but they require correspondingly stronger mitigation, with demonstrable risk reduction before proceeding.

**Seven conditions** must be satisfied before acceptance. The most critical: rollback dry-run practice, active safety injection during shadow mode, and Hermes plugin instance model verification.

**The migration is worth doing.** The benefits (streaming, compression, code reduction, skills ecosystem) are real and substantial. The risk management, once strengthened per these recommendations, is adequate for a CRITICAL-risk ADR. But "adequate" does not mean "zero risk" — Faiz must accept that this migration carries genuine safety risk during the transition window, and the mitigation strategy trades some risk for the 23-50 day window in which safety is ported to a new framework.

---

## Footer

| Field | Value |
|---|---|
| Report | 03-risk-assessment.md |
| Series | ADR-035 Review — Parallel Auditor Wave |
| Date | 2026-06-04 |
| Reviewer | REVIEWER 3 — Risk Assessment |
| Verdict | **CONDITIONAL APPROVE** (7 conditions) |
| Documents Reviewed | ADR-035 (full), 05-risk-deep-dive (full), 06-rollback-strategy (full), MASTER-RESTRUCTURE-PLAN (full), PROGRESS.md (full), 07-alternatives-analysis (full) |
| Risks Upgraded | 3 (R-001, R-013, R-015: HIGH → CRITICAL) |
| Missing Risks Identified | 10 |
| Recommendations | 7 blocking conditions + 10 non-blocking |