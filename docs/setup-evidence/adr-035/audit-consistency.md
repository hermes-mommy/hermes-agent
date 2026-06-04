# ADR-035 Cross-Reference Consistency Audit

> **Auditor**: Cross-Reference Consistency Auditor (Sisyphus Sub-Agent)
> **Audited Document**: `adr/ADR-035-hermes-migration.md` (2,315 lines, Proposed)
> **Date**: 2026-06-04
> **Scope**: ADR consistency against existing ADRs, project docs, MASTER-RESTRUCTURE-PLAN

---

## 1. Executive Summary

**VERDICT: NEEDS REVIEW** — 2 HIGH findings, 2 MEDIUM findings, 1 LOW advisory. No CRITICAL blockers to acceptance, but HIGH findings require resolution before ADR-035 can be marked Accepted.

Strong baseline: ADR-035 is internally consistent, well-researched, correctly applies corrected data from the architecture validation, and does NOT violate the three most binding ADRs (ADR-005, ADR-007, ADR-013). The two HIGH findings are cross-reference issues with existing ADRs that should be resolved.

---

## 2. Binding ADR Consistency Checks

### 2.1 ADR-005 — LLM Routing via 9Router

| Criterion | Expected | ADR-035 State | Verdict |
|---|---|---|---|
| 9Router retained | All LLM calls via `localhost:20128` | Pillar 5 "LLM = RETAIN 9Router at localhost:20128" | ✅ PASS |
| No OpenRouter fallback | Never fall back to OpenRouter | Fallback chain: GPT-5.5 → DeepSeek V4 Flash, both via 9Router | ✅ PASS |
| Custom provider config | Hermes configured as custom provider | `base_url: http://localhost:20128/v1`, provider: custom | ✅ PASS |

**Verdict: PASS** — No contradiction. ADR-035 explicitly commits to retaining 9Router unchanged. Fallback logic preserved. Budget enforcement added via custom hook.

---

### 2.2 ADR-007 — PostgreSQL Primary Memory

| Criterion | Expected | ADR-035 State | Verdict |
|---|---|---|---|
| PostgreSQL primary | All canonical memory via PostgreSQL+pgvector | Pillar 2: PostgreSQL+pgvector primary write authority unchanged | ✅ PASS |
| No SQLite for canonical memory | SQLite excluded from durable storage | Hermes SQLite only for transient session state + FTS5 indexes | ✅ PASS |
| 47 tables, 12 schemas preserved | All existing schemas maintained | "47 tables, 12 schemas, 5 classification levels — unchanged (0 lines)" | ✅ PASS |
| DNR pipeline preserved | Consent-critical enforcement | "DNR enforcement unchanged" via `memory_plugin.py` pre-injection gate | ✅ PASS |
| Encrypted profiles preserved | faiz_profile encryption | "Encrypted profiles unchanged" | ✅ PASS |

**Gray area documented**: ADR-035 §Pillar 2 explicitly acknowledges the Hermes SQLite gray area and argues consistency. The justification (SQLite for transient session state ≠ canonical Guinevere memory) is reasonable and aligned with ADR-007's intent.

**Verdict: PASS** — No violation. Gray area transparently documented.

---

### 2.3 ADR-013 — MCP Native Replaces OpenCode

| Criterion | Expected | ADR-035 State | Verdict |
|---|---|---|---|
| Guinevere MCP native is coding substrate | No replacement of MCP native by Hermes | "Hermes operates at agent framework layer, not coding substrate — no conflict" | ✅ PASS |
| Hermes does not replace OpenCode/opencode | Clear separation of concerns | Hermes = agent runtime, MCP native = coding substrate | ✅ PASS |

**Verdict: PASS** — ADR-035 correctly identifies the layering: Hermes is the agent framework (replacing discord.py), not the coding substrate (MCP native per ADR-013). No conflict.

---

### 2.4 ADR-022 — Communication Channel Strategy

| Criterion | Expected | ADR-035 State | Verdict |
|---|---|---|---|
| WhatsApp via Neonize (pure Python) | ADR-022 rev 1.1 (2026-06-03) explicitly chose Neonize over Baileys | ADR-035 line 113: "Native WhatsApp (BAW/Baileys WebSocket) support for future P11" | ❌ CONFLICT |
| No Node.js bridge for WhatsApp | ADR-022 rationale: "eliminates Node.js subprocess bridge, single Python process" | Hermes native WhatsApp support uses Baileys (Node.js-based protocol) | ❌ CONFLICT |

**Finding F1 (HIGH): WhatsApp strategy conflict with ADR-022**

ADR-022 was revised on 2026-06-03 specifically to switch from Baileys (Node.js) to Neonize (pure Python) with the explicit rationale of eliminating the Node.js bridge and maintaining a single Python process. ADR-035 (dated 2026-06-04) states Hermes natively supports WhatsApp via "BAW/Baileys WebSocket" — which would reintroduce the Node.js dependency that ADR-022 deliberately removed.

If Guinevere adopts Hermes's native WhatsApp support, it would use Baileys, directly contradicting ADR-022's revised decision. ADR-035 should:
- Acknowledge this tension explicitly
- Either clarify that Guinevere will use Neonize per ADR-022 even if Hermes has native Baileys support, OR
- Propose that Hermes's native WhatsApp capability supersedes ADR-022's Neonize decision (which would require updating ADR-022)

**Verdict: NEEDS REVIEW** — WhatsApp channel strategy must be reconciled.

---

### 2.5 ADR-029 — Self-Modification Automated Testing

| Criterion | Expected | ADR-035 State | Verdict |
|---|---|---|---|
| Automatic `git revert` within 60s | Failed self-modifications auto-revert | ADR-035 rollback is per-phase manual commands (< 5 min) | ⚠️ DIFFERENT CONTEXT |
| Safety-critical change classification | Persona/safety/surveillance/encryption files require Faiz review | 10 safety gates with Faiz approval gate | ⚠️ PARTIAL |
| Post-migration system must satisfy ADR-029 | Testing gate must still work | Not explicitly addressed | ⚠️ GAP |

**Finding F2 (MEDIUM): Post-migration ADR-029 compliance not addressed**

ADR-029 requires automatic `git revert` rollback within 60 seconds for failed self-modifications and classifies persona/safety files as safety-critical. ADR-035's rollback plan is about *migration phase* rollback (manual, per-phase, < 5 min), which is a different concern from ADR-029's *ongoing self-modification* rollback.

However, ADR-035 does not address whether the post-migration Hermes-based system will continue to satisfy ADR-029's automated testing requirements. Specific concerns:
- ADR-029 §lines 112-119 defines safety-critical files (persona, safety, surveillance, encryption) that must be classified — ADR-035 moves these to hooks/plugins but doesn't confirm the classification system still covers them
- ADR-029 §line 107 requires automatic `git revert` within 60 seconds — the Hermes-based system must still support this for ongoing development

**Mitigation**: This is a documentation gap, not an architectural violation. ADR-029's requirements are about *ongoing* self-modification; ADR-035 is about a *one-time migration*. Adding a brief statement that "post-migration, ADR-029's automated testing and rollback gates remain in effect for all future self-modifications" would close this.

**Verdict: NEEDS REVIEW** — Gap should be acknowledged with a commit to maintain ADR-029 compliance post-migration.

---

### 2.6 ADR-030 — Redis DB Assignments

| DB | ADR-030 Purpose | ADR-035 Usage | Conflict? |
|---|---|---|---|
| DB0 | Task queue | Not used by ADR-035 | No conflict |
| DB1 | LLM cache | Not used by ADR-035 | No conflict |
| DB2 | **Surveillance buffer** (allkeys-lfu, AOF) | **Consent cache** (60s TTL, Redis DB2) | ❌ CONFLICT |
| DB3 | **Sessions / working memory** (noeviction, AOF+RDB) | Not explicitly assigned in ADR-035 | No conflict |
| DB4 | **Pub/Sub** (no persistence) | **Session cache** (current: 2hr TTL, 20-turn limit) | ❌ CONFLICT |
| DB5 | **Rate limiting** (allkeys-lru, RDB only) | **Safety plugin state** (persisted every 60s) | ❌ CONFLICT |

**Finding F3 (HIGH): Redis DB assignments conflict with ADR-030**

ADR-030 is the binding canonical authority for Redis DB0-DB5 assignments. ADR-035's Redis usage creates three direct conflicts:

1. **DB2**: ADR-030 assigns DB2 to "Surveillance buffer" with `allkeys-lfu` eviction and AOF persistence. ADR-035 uses DB2 for consent state cache with 60s TTL. These are incompatible — consent cache needs different eviction/persistence than surveillance buffer.

2. **DB4**: ADR-030 assigns DB4 to "Pub/Sub" with NO persistence. ADR-035 describes the current system using DB4 for session cache with 2hr TTL. Per ADR-030, sessions belong in DB3, not DB4.

3. **DB5**: ADR-030 assigns DB5 to "Rate limiting" with `allkeys-lru` eviction (disposable on restart). ADR-035 uses DB5 for safety plugin state that must survive crashes (persisted every 60s with Redis checkpoint). Rate limiting's `allkeys-lru` eviction would evict safety state under memory pressure.

**Impact**: These conflicts create operational ambiguity. If another system component follows ADR-030's assignments, it could collide with ADR-035's Redis keys. Safety-critical state (consent, plugin state) on DBs with wrong eviction policies could be silently lost.

**Resolution options**:
- Option A: Propose new DB assignments (DB6, DB7, DB8) for Hermes-specific state and update ADR-030
- Option B: Reassign ADR-030 DBs to match ADR-035's needs (requires superseding ADR-030)
- Option C: Map ADR-035 needs to unused Redis keys within existing ADR-030 DBs (e.g., consent cache under DB3 with proper key prefix)

**Verdict: NEEDS REVIEW** — Redis DB assignments must be reconciled with ADR-030.

---

## 3. Document Path Verification

### 3.1 YAML Frontmatter `related_documents`

| Path in ADR-035 | Exists? | Notes |
|---|---|---|
| `docs/00-core/03-TechArchitecture_v2.0.md` | ❌ NOT FOUND | Actual file is `docs/00-core/02-TechnicalArchitecture_v2.0.md` |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | ✅ Exists | Correct |
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | ✅ Exists | Correct |
| `research-reports/hermes-restructure/MASTER-RESTRUCTURE-PLAN.md` | ✅ Exists | Correct |
| `research-reports/adr-035-prep/00-PLANNER-GATE.md` | ✅ Exists | Correct |
| ADR-001 through ADR-033 (all referenced) | ✅ All exist | Correct paths in adr/ directory |

**Finding F4 (MEDIUM): Wrong document path — TechArchitecture**

The YAML frontmatter and `## Links` section reference `docs/00-core/03-TechArchitecture_v2.0.md` which does not exist. The actual Technical Architecture document is at `docs/00-core/02-TechnicalArchitecture_v2.0.md`. The numbering in the docs suite is:
- 00 = BRD
- 01 = PRD
- 02 = Technical Architecture
- 03 = Agent Loop Spec

ADR-035 uses "03" for Technical Architecture and doesn't reference Agent Loop Spec separately. This may be a numbering error — the correct reference for Technical Architecture is `02`, not `03`.

**Verdict: NEEDS REVIEW** — Path should be corrected to `docs/00-core/02-TechnicalArchitecture_v2.0.md`.

---

## 4. Timeline Realism Check

| Metric | PROGRESS.md | ADR-035 | Assessment |
|---|---|---|---|
| Current completion | P0-P8 complete, 203/343+ steps (59.2%) | Correctly states "59.2% of roadmap complete" (line 100) | ✅ Match |
| Pending phases | P9 (Financial), P10 (Hardening), P11-P22 | Not directly affected — Hermes migration is a parallel infrastructure change | ✅ Compatible |
| Migration timeline | N/A | 23-35 days (updated from MASTER plan's 17-27) | ✅ Realistic |
| Critical path | P0 → P1 → P3 → P5 (original) | Phase 0 → 1 → 2 → 7 (migration-critical) | ✅ Independent |

**Verdict: PASS** — Timeline is realistic. The migration runs parallel to remaining product phases and the corrected 23-35 day estimate is appropriately more conservative than the MASTER plan's 17-27 days.

---

## 5. Budget Impact

| Component | Current | Post-Migration | Within $30 cap? |
|---|---|---|---|
| Infrastructure (VPS) | $0 (shared) | $0 (shared) | ✅ |
| LLM costs (monthly) | ~$25 | ~$25 | ✅ |
| Shadow mode (one-time) | N/A | ≤ $5 capped | ✅ |
| Total monthly | ~$25 | ~$25 | ✅ (25/30 = 83%) |
| Budget enforcement | Manual | Custom hook: alert at 80% ($24), block at 100% ($30) | ✅ Improved |

**Verdict: PASS** — No budget increase. Budget enforcement actually improves with automated hook.

---

## 6. MASTER-RESTRUCTURE-PLAN.md Superset Check

| MASTER Plan Data | MASTER Claim | ADR-035 Correction | Status |
|---|---|---|---|
| Hook names | `pre_gateway_dispatch`, `pre_llm_call`, `transform_llm_output` | `pre_prompt`, `post_prompt`, `pre_tool_call`, `post_tool_call`, `pre_response`, `post_response`, `on_error` | ✅ Corrected |
| bot.py lines | 603 | 512 | ✅ Corrected |
| conversational_handler.py lines | 614 | 496 | ✅ Corrected |
| session_adapter.py lines | 366 | 302 | ✅ Corrected |
| Code reduction | 59% (of ~9,378 lines) | 31.2% net (of 25,796 lines) | ✅ Corrected |
| Slash commands | 33 | 35 | ✅ Corrected |
| Timeline | 17-27 days | 23-35 days | ✅ Corrected |
| Shadow mode | Single channel | Separate channels | ✅ Corrected |

**Verdict: PASS** — ADR-035 is a proper superset of the MASTER plan with all corrections applied. It explicitly documents the discrepancies (lines 1112-1113, 1128, 1779-1784) and provides corrected data throughout.

---

## 7. ADR Index Consistency

| Index File | adr_count | ADR-035 Included |
|---|---|---|
| `docs/10-governance/17-ADR_Index_v1.0.md` (canonical) | 35 | ✅ Yes — "Proposed" in Canonical Decision Map (line 60) |
| `adr/README.md` (folder index) | 34 | ❌ No — Not in ADR Register table |

**Finding F5 (LOW): ADR-035 missing from `adr/README.md`**

The canonical ADR Index at `docs/10-governance/17-ADR_Index_v1.0.md` correctly lists ADR-035 as Proposed. However, `adr/README.md` still shows `adr_count: 34` and does not include ADR-035 in its ADR Register table. Per the maintenance rules in both index files ("Keep `adr/README.md` synchronized with this master index"), the folder-level index should be updated to include ADR-035.

**Verdict: ADVISORY** — Not a blocking issue but should be fixed for consistency.

---

## 8. Final Verdict Matrix

| Check | Result | Severity |
|---|---|---|
| ADR-005 (9Router) | PASS | — |
| ADR-007 (PostgreSQL primary) | PASS | — |
| ADR-013 (MCP native) | PASS | — |
| **ADR-022 (WhatsApp/Baileys vs Neonize)** | **NEEDS REVIEW** | **HIGH** |
| **ADR-030 (Redis DB conflicts)** | **NEEDS REVIEW** | **HIGH** |
| ADR-029 (self-modification testing) | NEEDS REVIEW | MEDIUM |
| Document path (03-TechArchitecture) | NEEDS REVIEW | MEDIUM |
| Timeline realism | PASS | — |
| Budget impact | PASS | — |
| MASTER-RESTRUCTURE-PLAN superset | PASS | — |
| Related documents existence | PASS (1 path error) | — |
| ADR Index sync | ADVISORY | LOW |

---

## 9. Recommendations

### Must Fix (blocking acceptance)

1. **F1 — Reconcil ADR-022 WhatsApp strategy**: Add explicit statement clarifying whether Hermes's native Baileys WhatsApp will be used (overriding ADR-022's Neonize decision) or whether Guinevere will continue using Neonize per ADR-022. If overriding, note that ADR-022 may need updating.

2. **F3 — Resolve Redis DB conflicts with ADR-030**: Either (a) propose new DB6+ assignments for Hermes-specific state and plan an ADR-030 update, or (b) remap ADR-035's Redis usage to fit within ADR-030's existing assignments. The consent cache (currently DB2) and safety plugin state (currently DB5) are the critical conflicts.

### Should Fix (before marking Accepted)

3. **F2 — Address ADR-029 post-migration compliance**: Add a statement confirming that ADR-029's automated testing and rollback requirements remain in effect post-migration, and describe how the Hermes-based system will satisfy them.

4. **F4 — Correct TechArchitecture path**: Change `docs/00-core/03-TechArchitecture_v2.0.md` to `docs/00-core/02-TechnicalArchitecture_v2.0.md` in both YAML frontmatter and `## Links` section.

### Nice to Have

5. **F5 — Update `adr/README.md`**: Add ADR-035 to the ADR Register table and update `adr_count` to 35.

---

## 10. Evidence Artifacts Reviewed

| Artifact | Path | Read |
|---|---|---|
| ADR-035 (full 2,315 lines) | `adr/ADR-035-hermes-migration.md` | ✅ |
| ADR Index (canonical) | `docs/10-governance/17-ADR_Index_v1.0.md` | ✅ |
| ADR Index (folder) | `adr/README.md` | ✅ |
| ADR-005 | `adr/ADR-005-llm-router-failover-strategy.md` | ✅ (first 80 lines) |
| ADR-007 | `adr/ADR-007-memory-storage-backend-selection.md` | ✅ (first 80 lines) |
| ADR-013 | `adr/ADR-013-guinevere-mcp-native-opencode-replacement.md` | ✅ (first 60 lines) |
| ADR-022 (full) | `adr/ADR-022-communication-channel-strategy.md` | ✅ (full 154 lines) |
| ADR-029 (full) | `adr/ADR-029-self-modification-automated-testing.md` | ✅ (full 181 lines) |
| ADR-030 (full) | `adr/ADR-030-redis-db-assignments.md` | ✅ (full 147 lines) |
| PROGRESS.md | `PROGRESS.md` | ✅ (first 100 lines) |
| MASTER-RESTRUCTURE-PLAN | `research-reports/hermes-restructure/MASTER-RESTRUCTURE-PLAN.md` | ✅ (full 667 lines) |
| File existence checks | Glob for document paths | ✅ |

---

## Footer

| Field | Value |
|---|---|
| Auditor | Cross-Reference Consistency Auditor (Sisyphus sub-agent) |
| Verdict | **NEEDS REVIEW** — 2 HIGH, 2 MEDIUM, 1 LOW |
| Date | 2026-06-04 |
| Scope | ADR consistency with existing ADRs, project docs, MASTER-RESTRUCTURE-PLAN |
| Exclusions | Safety compliance (separate auditor), hook name technical accuracy (separate auditor) |