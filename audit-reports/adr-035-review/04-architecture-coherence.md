# ADR-035 Architecture Coherence Review

> **Reviewer**: REVIEWER 4 — Architecture Coherence  
> **Date**: 2026-06-04  
> **Status**: Complete  
> **Sources Read**: ADR-035 (full), ADR-001, ADR-003, ADR-004, ADR-005, ADR-007, ADR-013, ADR-022, ADR-024, ADR-025, ADR-030, ADR-032, ADR-033, adr/README.md, research-reports/adr-035-prep/02-architecture-validation.md, research-reports/adr-035-prep/07-alternatives-analysis.md

---

## Summary

ADR-035 is an architecturally coherent, thoroughly-evidenced migration proposal. The 5-pillar structure is internally consistent, phase ordering is logical with zero circular dependencies, and all 4 considered options are fairly evaluated. Cross-reference analysis against 12 existing ADRs reveals 11 are fully consistent and 1 (ADR-030) has a documented but unresolved Redis DB assignment conflict. The architecture validation research report (Report 02) found critical hook-name errors in the earlier MASTER-RESTRUCTURE-PLAN; ADR-035 has **fully corrected** these errors with verified hook names (`pre_prompt`, `post_prompt`, `pre_tool_call`, `post_tool_call`, `pre_response`, `post_response`, `on_error`).

## Verdict: CONDITIONAL

ADR-035 is **conditionally approved** pending one required action: resolution of the ADR-030 Redis DB assignment conflict. All other cross-reference checks pass and the architecture is internally coherent.

---

## ADR Cross-Reference Matrix

| ADR | Title | Relationship to ADR-035 | Conflict? | Resolution | Status |
|-----|-------|------------------------|-----------|------------|--------|
| ADR-001 | Persona Safety & Ethical Boundary Policy | ADR-035 enforces "safety > persona flavor" with 4 defense-in-depth layers. All 15+ safety features ported. | None | Consistent — ADR-001 §Decision Outcome: "safety first, persona second" is architecturalized in ADR-035's Pillar 3 (Safety = HOOKS + PLUGINS) | ✅ PASS |
| ADR-003 | Persona Drift Control & Validation | ADR-035 implements SHA-256 drift detector as `post_prompt` hook with configurable thresholds (10% warn, 20% rollback). | None | Consistent — ADR-003 mandates drift logs, validation checks, rollback/safe-mode rules. ADR-035 provides all three with deterministic SHA-256 comparison. | ✅ PASS |
| ADR-004 | Primary LLM Model Selection | **Note**: Task referenced ADR-004 as "Hermes Original Adoption" — no such ADR exists. ADR-004 selects GPT-5.5 via 9Router. ADR-035 preserves this: Pillar 5 = RETAIN 9Router. | None | N/A — ADR-004 and ADR-035 operate at different layers (model selection vs agent framework). ADR-035 does not supersede ADR-004. | ✅ PASS |
| ADR-005 | LLM Router & Failover Strategy | ADR-035 preserves "9Router only, no OpenRouter fallback." Hermes configured as custom provider at `localhost:20128/v1`. | None | Consistent — ADR-005 §Decision Outcome: "9Router only with queue/retry/degrade behavior." ADR-035 Pillar 5: LLM = RETAIN 9Router. Fallback chain (GPT-5.5 → DeepSeek V4 Flash) is model-level, not router-level. | ✅ PASS |
| ADR-007 | Memory Storage Backend Selection | ADR-035 preserves PostgreSQL+pgvector as primary write authority. Hermes SQLite scoped to transient session state and FTS5 search — not canonical memory. | None (documented gray area) | Consistent — ADR-007 §Decision Outcome: "Do not use SQLite for canonical Guinevere memory." ADR-035 §Pillar 2: "Hermes SQLite stores ONLY transient session state and FTS5 search indexes." Gray area acknowledged with explicit rationale. | ✅ PASS |
| ADR-013 | Guinevere MCP Native OpenCode Replacement | **Note**: Task referenced ADR-013 for "Data Classification" — ADR-013 is actually about MCP replacing OpenCode. Classification is ADR-024. ADR-035 operates at agent framework layer, not coding substrate. | None | Consistent — ADR-013 §Decision Outcome: MCP native replaces OpenCode as coding substrate. ADR-035 replaces Hermes Agent's stateless wrapper, not the MCP coding layer. No layer collision. | ✅ PASS |
| ADR-022 | Communication Channel Strategy (revised 2026-06-03) | ADR-022 rev. mandates Neonize (pure Python, whatsmeow CGo) for WhatsApp. ADR-035 correctly states Hermes BAW is NOT adopted. | Minor: D9 mentions "BAW (Baileys WebSocket)" as Hermes capability | Not a true conflict — D9 explicitly states "This is future capability, not immediate migration driver." ADR-035 §Context §8: "Hermes native WhatsApp capability is documented but NOT adopted for Guinevere." | ✅ PASS |
| ADR-024 | Data Governance & Classification Policy | ADR-035 preserves 5-level classification (Internal→Critical) in Pillar 2 (Memory = HYBRID). `classify_event()` preserved, unknown → Confidential (fail-closed). | None | Consistent — ADR-024 mandates explicit multi-class governance. ADR-035 Pillar 2 table: "Classification: 5-level — **Unchanged**." | ✅ PASS |
| ADR-025 | Backup & Disaster Recovery Strategy | ADR-035 provides comprehensive rollback plan with per-phase procedures, `hermes checkpoints`, PostgreSQL dumps, git tags, and rclone offsite backups. | None | Consistent — ADR-025 requires formal backup/DR policy with restore validation. ADR-035's rollback plan (8 phases, per-phase exact commands, pre-migration safety net) satisfies ADR-025's requirements. | ✅ PASS |
| ADR-030 | Redis DB Assignments (DB0–DB5) | **CONFLICT**: ADR-030 canonically assigns DB2=Surveillance buffer, DB3=Sessions, DB4=Pub/Sub, DB5=Rate limiting. ADR-035: consent gate uses DB2, session cache uses DB4, safety plugin uses DB5. | **YES — unresolved** | ADR-035 §Context acknowledges this: "This pre-existing runtime-vs-ADR discrepancy is documented but not resolved by this ADR. ADR-030 should be updated... or Hermes-specific uses should migrate to DB6+." But the ADR proceeds without resolving. | ⚠️ CONDITIONAL |
| ADR-032 | Backup Storage Strategy (idcloudhost S3 + Cloudflare R2) | ADR-035 rollback plan uses rclone to `idcloudhost:guinevere-dr-backups` and `r2:guinevere-dr-backups`. | None | Consistent — ADR-032 establishes dual-provider backup. ADR-035's pre-migration safety net (`rclone copy` to both destinations) aligns. Phase 7 backup pipeline explicitly references ADR-032. | ✅ PASS |
| ADR-033 | Browser Automation — Obscura CDP | ADR-035 keeps `obscura_cdp` as a custom MCP tool (Pillar 4: 7 Keep Custom). | None | Consistent — ADR-033 refines ADR-020 (obscura primary + Playwright fallback). ADR-035 keeps obscura_cdp custom with DESTRUCTIVE_APPROVAL auth level. No Hermes native equivalent exists. | ✅ PASS |

### Summary

| Status | Count | ADRs |
|--------|-------|------|
| ✅ PASS | 11 | 001, 003, 004, 005, 007, 013, 022, 024, 025, 032, 033 |
| ⚠️ CONDITIONAL | 1 | 030 |
| ❌ FAIL | 0 | — |

---

## 5-Pillar Internal Consistency

### Pillar Coherence Analysis

The 5 pillars (Discord=Migrate, Memory=Hybrid, Safety=Hooks+Plugins, MCP=Hybrid, LLM=Retain) form a **mutually reinforcing architecture**:

| Pillar | Supports | Supported By |
|--------|----------|--------------|
| **P1: Discord = MIGRATE** | Eliminates ~4,381 lines of custom infrastructure; provides streaming/threading/circuit breaker that P3 safety hooks can intercept | P3: Safety hooks validate all Discord messages before LLM processing; P5: LLM routing serves Discord gateway |
| **P2: Memory = HYBRID** | PostgreSQL primary ensures data sovereignty (enables P1 safety, P3 DNR, P4 auth matrix) | P3: DNR and classification enforced by memory plugin; P4: PostgreSQL tools remain custom for memory operations |
| **P3: Safety = HOOKS + PLUGINS** | Provides 4-layer defense-in-depth that protects P1 (Discord), P2 (memory recall), P4 (tool calls), P5 (LLM calls) | P1: Discord messages feed into pre_prompt hook; P2: Memory plugin enforces DNR/classification; P4: pre_tool_call hook enforces auth matrix; P5: Response hooks scan LLM output |
| **P4: MCP = HYBRID** | 5 native tools reduce custom maintenance; 7 custom tools preserve safety-critical capabilities | P3: Auth overlay plugin enforces 4-level matrix on ALL tools (native + custom); P5: LLM powers tool-use reasoning |
| **P5: LLM = RETAIN** | Preserves 9Router investment, cost tracking, fallback chain | P1: Discord gateway calls LLM through 9Router; P3: post_prompt hook validates assembled prompts before LLM call; P4: Tool calls are LLM-orchestrated |

### Contradiction Check

I checked every pillar pair for mutual contradiction. **None found.** Specific stress tests:

1. **P1 (Discord=Migrate) vs P3 (Safety=Hooks)**: Does migrating Discord to Hermes weaken safety? No — the hook system provides equivalent interception points. HARD STOP fires in `pre_prompt` before LLM call, functionally equivalent to current `_on_message_listener`.

2. **P2 (Memory=Hybrid) vs P4 (MCP=Hybrid)**: Does dual memory conflict with dual MCP? No — PostgreSQL remains sole write authority for memory, and auth overlay plugin applies uniformly to both Hermes native and custom MCP tools.

3. **P3 (Safety=Hooks) vs P5 (LLM=Retain)**: Do safety hooks interfere with 9Router latency? No — total hook latency budget is ~450ms; LLM inference dominates at 2-30s.

4. **P2 (PostgreSQL primary) vs P2 (Hermes SQLite supplementary)**: Does Hermes SQLite violate ADR-007? Documented gray area — SQLite is for transient session state, not canonical memory. Mirrors never become authoritative over PostgreSQL. This is the closest to a contradiction but is explicitly scoped and justified.

**Verdict**: The 5 pillars are **internally consistent and mutually reinforcing**. No pillar contradicts another.

---

## Phase Ordering Logic

### Dependency Graph

```
Phase 0 (Security Remediation) ──┐
                                  ├──> Phase 1 (Safety Foundation) ──> Phase 2 (Discord Gateway) ──┐
                                  │                                                                    │
                                  └──> Phase 3 (Memory Bridge) ────────────────────────────────────────┤
                                       Phase 4 (MCP + Tools) ──────────────────────────────────────────┤
                                       Phase 5 (Skills + Persona) ─────────────────────────────────────┤
                                       Phase 6 (LLM Routing) ──────────────────────────────────────────┤
                                                                                                       │
                                                                                                       ▼
                                                                                              Phase 7 (Hardening)
```

### Dependency Validation

| Phase | Depends On | Dependency Valid? |
|-------|-----------|-------------------|
| Phase 0 | Nothing | ✅ Correct — security must come first |
| Phase 1 | Phase 0 only | ✅ Correct — safety hooks need Hermes installed but not Discord-active |
| Phase 2 | Phase 1 (all 10 safety gates) | ✅ Correct — Discord cutover MUST wait for safety verification |
| Phase 3 | Phase 2 (cutover complete) | ✅ Correct — memory bridge needs live Discord to test recall |
| Phase 4 | Phase 2 (cutover complete) | ✅ Correct — MCP tools need live agent to test auth overlay |
| Phase 5 | Phase 1 (safety foundation) | ✅ Correct — persona plugins build on safety FSM |
| Phase 6 | Phase 1 (consent gate infra) + Phase 2 | ✅ Correct — LLM routing needs Discord operational |
| Phase 7 | All preceding phases | ✅ Correct — hardening gates everything |

### Critical Path

**Phase 0 → Phase 1 → Phase 2 → Phase 7** = serialized, ~11-17 days (realistic).

Phases 3-6 can overlap if independent surfaces are respected (documented in ADR-035 §Migration Phases).

### Circular Dependency Check

DFS traversal of all phase dependencies: **zero cycles**. No phase depends on any later phase.

**Verdict**: Phase ordering is **logical, well-documented, and free of circular dependencies**.

---

## Architecture Diagram Accuracy

ADR-035 does not contain inline ASCII architecture diagrams. It uses a table-based 5-pillar description (§Decision Outcome) which is **clear and unambiguous**.

The research report 07-alternatives-analysis contains an ASCII architecture diagram (Report 07 §3.1) that uses the **pre-correction hook names** (`pre_gateway_dispatch`, `pre_llm_call`, `transform_llm_output`) from the MASTER-RESTRUCTURE-PLAN. This diagram is **outdated** — the ADR itself uses corrected hook names throughout.

**Finding**: The ADR's text-based pillar description is accurate. The research report's diagram is stale but the research report is evidence, not governance. No action required on the ADR itself.

---

## Considered Options Fairness

The 4 candidate architectures (Option A: Full Hermes, Option B: Status Quo, Option C: Sidecar, Option D: Hybrid/Chosen) were evaluated for fairness:

### Option A: Full Hermes (All-In)

| Assessment | Finding |
|------------|---------|
| Pros fairly presented? | ✅ Yes — maximum code reduction (75%), simplest post-migration architecture, full ecosystem access |
| Cons fairly presented? | ✅ Yes — 5 independently sufficient rejection reasons tied to binding ADRs |
| Straw-man? | **No** — Option A is a legitimate architecture that would be appropriate for a greenfield project without ADR-007 constraints |
| Rejection rationale valid? | ✅ Yes — ADR-007 violation, classification/DNR/encryption loss, 12-schema loss, auth matrix loss, data sovereignty |

### Option B: Status Quo (Keep Current)

| Assessment | Finding |
|------------|---------|
| Pros fairly presented? | ✅ Yes — zero migration risk, all safety proven, full architectural control |
| Cons fairly presented? | ✅ Yes — ~9,400 lines of custom infrastructure, no streaming/compression/threading/circuit breaker, technical debt trajectory |
| Straw-man? | **No** — acknowledged as "legitimate advantages" with a real maintenance burden argument |
| Rejection rationale valid? | ✅ Yes — "The custom infrastructure provides zero competitive advantage over Hermes's production-grade equivalents while lacking streaming, compression, threading, circuit breaker, and skills" |

### Option C: Hermes as Sidecar (Parallel)

| Assessment | Finding |
|------------|---------|
| Pros fairly presented? | ✅ Yes — lowest migration risk, gradual adoption, per-feature rollback, learning curve spread |
| Cons fairly presented? | ✅ Yes — dual Discord bots in one guild (critical), session sync unsolvable, unclear authority |
| Straw-man? | **No** — sidecar is a common migration pattern; ADR-035 correctly identifies why it fails for THIS specific use case (two Discord bots in one guild) |
| Rejection rationale valid? | ✅ Yes — "Two Discord bots in one guild is architecturally unsound. Session synchronization is unsolvable without bridge code" |

### Option D: Hybrid Hermes Migration (Chosen)

| Assessment | Finding |
|------------|---------|
| Pros fairly presented? | ✅ Yes — code reduction (31.2% corrected), streaming, compression, skills, all safety preserved |
| Cons honestly listed? | ✅ Yes — 7 cons with explicit mitigations (dual memory complexity, dual MCP backends, Hermes API dependency, timeline uncertainty, safety migration risk, skill quality, learning curve) |
| Self-serving? | **No** — ADR-035 is transparent about the 7 negatives and does not minimize them |

**Verdict**: All 4 options are **fairly and completely evaluated**. No straw-men. Rejection rationales for Options A, B, and C are each independently sufficient.

---

## Decision Driver → Outcome Traceability

Every decision driver maps to a concrete architectural feature in Option D:

| Driver | Weight | Mapping to Chosen Option | Traceability Quality |
|--------|--------|--------------------------|---------------------|
| D1: Safety preservation | CRITICAL (5) | Pillar 3: All 15+ features ported to hooks+plugins with 4 defense-in-depth layers; 10 Phase 1 safety gates | **Strong** — safety is Pillar 3, Phase 1, and the critical barrier |
| D2: Code complexity reduction | HIGH (4) | Pillar 1: Discord infrastructure eliminated (4,381 lines); MCP tools reduced from 16→7 custom | **Strong** — 31.2% net reduction, explicitly tabulated |
| D3: Production-grade Discord | HIGH (4) | Pillar 1: Streaming, auto-threading, circuit breaker, RBAC — all net-new capabilities | **Strong** — each capability mapped to specific Hermes features |
| D4: Memory architecture preservation | HIGH (4) | Pillar 2: PostgreSQL+pgvector unchanged; compression/session_search read-only supplements | **Strong** — zero lines changed, zero data migration |
| D5: MCP tool ecosystem | MEDIUM (3) | Pillar 4: 5 native + 7 custom + 4 hybrid; auth overlay plugin wraps all | **Strong** — explicit migration table for all 16 tools |
| D6: LLM routing continuity | MEDIUM (3) | Pillar 5: 9Router unchanged, custom provider config, fallback chain preserved | **Strong** — configuration is a 5-line YAML change |
| D7: Persona enforcement | HIGH (4) | Pillar 3: SOUL.md + GuinevereSafetyPlugin with full FSM port | **Strong** — 1,036-line plugin code included verbatim in ADR |
| D8: Operational simplification | MEDIUM (3) | Pillar 1: Unified CLI, `hermes backup/checkpoints/doctor/security/insights` | **Strong** — 6 operational tools gained |
| D9: Multi-channel readiness | LOW (2) | Pillar 1: Hermes multi-platform gateway (future P11 capability) | **Adequate** — explicitly marked as future, not driver |
| D10: Budget constraint | HIGH (4) | Pillar 5: Budget enforcement via pre_tool_call hook; shadow mode capped at $5 | **Strong** — 80% alert, 100% block, explicit thresholds |
| D11: Shared VPS compatibility | MEDIUM (3) | Pillar 1: Hermes replaces bot.py process (no net increase); cgroup limits unchanged | **Adequate** — neutral impact, correctly scored as "0" |
| D12: Rollback safety | CRITICAL (5) | 7-phase plan with per-phase rollback; universal kill-switch; PostgreSQL unchanged | **Strong** — per-phase rollback table with exact commands and <5 min downtime |

**Verdict**: Decision drivers **flow logically to the chosen option**. Every weighted driver has a concrete, traceable architectural response. No driver is ignored or weakly addressed.

---

## Inconsistencies Found

### 1. ADR-030 Redis DB Assignment Conflict (CONDITIONAL — resolves to PASS if actioned)

**Nature**: Explicit, documented conflict between ADR-030 canonical assignments and ADR-035's inherited runtime Redis usage.

| Redis DB | ADR-030 Canonical | ADR-035/Current Runtime Usage | Conflict |
|----------|-------------------|-------------------------------|----------|
| DB2 | Surveillance buffer | Consent cache (`consent_gate.py`, `pre_tool_call` hook) | **YES** |
| DB3 | Sessions / working memory | (not explicitly used by ADR-035) | None |
| DB4 | Pub/Sub | Session cache (`session_adapter.py`) | **YES** |
| DB5 | Rate limiting | Safety plugin state (`GuinevereSafetyPlugin`) | **YES** |

**ADR-035's handling**: Acknowledged in §Context under "ADR Cross-Reference Notes (Audit Findings Addressed)" with the statement: "This pre-existing runtime-vs-ADR discrepancy is documented but not resolved by this ADR. ADR-030 should be updated (via superseding ADR or addendum) to reflect actual runtime Redis assignments, or Hermes-specific uses should migrate to DB6+ if available."

**Severity**: MEDIUM. This is a pre-existing discrepancy (pre-dates ADR-035), not a new one introduced by ADR-035. ADR-035 correctly documents it but defers resolution.

**Recommended Action**: Before ADR-035 is marked Accepted, either:
- (a) Create a brief ADR-030 addendum or superseding ADR that realigns Redis DB assignments with actual runtime usage, OR
- (b) Add a concrete tracking item in ADR-035's Phase 0 or Phase 7 steps stating "Resolve ADR-030 Redis DB assignments" with a deadline.

### 2. Research Report 07 Uses Pre-Correction Data (MINOR — informational only)

The 07-alternatives-analysis.md report (which ADR-035 cites as evidence) still uses the pre-correction 59%/-5,528 lines figure from the MASTER-RESTRUCTURE-PLAN. ADR-035 **has been corrected** to 31.2%/-8,057 lines, and the ADR explicitly calls out the correction (§Code Reduction — CORRECTED Data: "The MASTER plan's 59% estimate correctly reflected the high reduction rate on the files it DID count... but the full codebase is 2.75× larger due to preserved subsystems").

**Impact**: Low. The research report is evidence, not governance. The ADR (which IS governance) is internally consistent with the corrected 31.2% figure. No action required on the ADR itself. The research report could optionally be updated for documentary consistency.

### 3. D9 Mentions BAW (Baileys WebSocket) for WhatsApp (MINOR — informational only)

ADR-035 §Decision Drivers D9 states Hermes "natively supports WhatsApp via BAW (Baileys WebSocket)." ADR-022 (revised 2026-06-03) **mandates Neonize** (pure Python, whatsmeow CGo) and explicitly rejected the Baileys/Node.js approach. ADR-035 correctly clarifies in §Context §8: "Hermes native WhatsApp capability is documented but NOT adopted for Guinevere." D9 also states "This is future capability, not immediate migration driver."

**Impact**: None. ADR-035 explicitly defers to ADR-022. The BAW mention is purely informational about Hermes's capabilities. No conflict exists at the decision level.

### 4. Task Reference to Non-Existent ADRs (N/A — not an ADR-035 issue)

The review task referenced:
- "ADR-004 (Hermes Original Adoption)" — ADR-004 is actually about Primary LLM Model Selection; no "Hermes Original Adoption" ADR exists
- "ADR-005 (Surveillance Architecture)" — ADR-005 is actually about LLM Router & Failover Strategy
- "ADR-013 (Data Classification)" — ADR-013 is actually about Guinevere MCP Native OpenCode Replacement; classification is ADR-024

These are task-level mis-references, not ADR-035 inconsistencies. I verified the actual ADR content at each number and all checks pass.

---

## Recommendations

### Required (for CONDITIONAL → APPROVE)

1. **Resolve ADR-030 Redis DB assignment conflict before ADR-035 is marked Accepted.** Options:
   - **Preferred**: Create a brief ADR-036 or ADR-030 addendum realigning Redis DB assignments with runtime reality (DB2=Consent cache, DB4=Session cache, DB5=Safety plugin state, moving Surveillance/PubSub/RateLimit to DB6-8).
   - **Acceptable**: Add explicit Phase 0 step: "Reconcile Redis DB assignments with ADR-030. Audit all `redis.Redis(db=N)` calls. Update ADR-030 via addendum. Migrate non-canonical uses to DB6+."
   - **Minimal**: Add a firm tracking item in ADR-035 §Implementation Notes: "ADR-030 Redis DB assignments MUST be reconciled before Phase 1 begins. Resolution document linked in review record."

### Optional (quality improvements)

2. Update research report 07-alternatives-analysis.md executive summary to reference corrected 31.2% figure (currently at 59%).
3. Consider adding a brief note in D9 cross-referencing ADR-022's Neonize mandate to avoid future reader confusion about BAW vs Neonize.

---

## Reviewer Signature

| Field | Value |
|-------|-------|
| Reviewer | REVIEWER 4 — Architecture Coherence |
| Date | 2026-06-04 |
| ADR Reviewed | ADR-035-hermes-migration.md (full, 1,786+ lines) |
| Cross-references Read | ADR-001, 003, 004, 005, 007, 013, 022, 024, 025, 030, 032, 033 + adr/README.md |
| Evidence Read | research-reports/adr-035-prep/02-architecture-validation.md, 07-alternatives-analysis.md |
| Verdict | **CONDITIONAL** — 11/12 ADRs PASS, 1 CONDITIONAL (ADR-030 Redis DB), zero FAIL |
| Architecture Coherence | **PASS** — 5 pillars mutually consistent, phase ordering logical, zero circular dependencies, all options fairly evaluated |
| Conditional Item | ADR-030 Redis DB assignment conflict requires explicit resolution before Accepted status |