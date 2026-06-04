# Technical Accuracy Audit — ADR-035 Hermes Migration

> **Audit Type**: Technical Accuracy  
> **Target**: `adr/ADR-035-hermes-migration.md`  
> **Date**: 2026-06-04  
> **Auditor**: Guinevere (Sisyphus-Junior)  
> **Sources**: Research reports (`research-reports/adr-035-prep/02-architecture-validation.md`, `04-code-reduction-analysis.md`), ADR-030  

---

## Verdict: NEEDS REVIEW

**6 PASS, 0 FAIL, 1 NEEDS REVIEW** — Redis DB assignments conflict with ADR-030.

---

## Finding 1: Hook Names — PASS

**Criterion**: Hook names must match Hermes actual API (7 lifecycle hooks).

**Research ground truth** (Report 02 §5, line 228-229):
```
pre_prompt → post_prompt → pre_tool_call → post_tool_call → pre_response → post_response → on_error
```

**ADR-035 uses** (lines 345-356):

| Safety Feature | ADR-035 Hook | Hermes Actual |
|---|---|---|
| HARD STOP + distress | `pre_prompt` | ✅ `pre_prompt` |
| Persona drift | `post_prompt` | ✅ `post_prompt` |
| Consent gate | `pre_tool_call` | ✅ `pre_tool_call` |
| Yandere + secret scanner | `post_response` | ✅ `post_response` |
| Output sanitization | `post_tool_call` | ✅ `post_tool_call` |
| Final safety check | `pre_response` | ✅ `pre_response` |
| Error classification | `on_error` | ✅ `on_error` |

**Additionally**, ADR-035 explicitly calls out the correction on lines 354-356:
> The MASTER-RESTRUCTURE-PLAN.md referenced hook names (pre_gateway_dispatch, pre_llm_call, transform_llm_output) that do not exist in the Hermes hook system.

All 7 hook configurations (lines 380-558) use the correct names. The hook execution order table (lines 560-573) matches the documented lifecycle.

**Verdict: PASS** — All hook names are correct. Incorrect MASTER plan names are explicitly identified and corrected.

---

## Finding 2: Line Counts — PASS

**Criterion**: File line counts must match actual source files.

| File | Research Report (actual) | ADR-035 | Match |
|---|---|---|---|
| `bot.py` | 512 | 512 (line 93) | ✅ |
| `conversational_handler.py` | 496 | 496 (line 93) | ✅ |
| `session_adapter.py` | 302 | 302 (line 94) | ✅ |
| `memory_bridge.py` | 251 | 251 (line 589) | ✅ |

**Evidence**: Research Report 02 §2 (lines 56-62) measured these files via `Measure-Object -Line`. ADR-035 uses the corrected values throughout.

**Comparison to MASTER plan inflated counts**:

| File | MASTER Plan (wrong) | ADR-035 (correct) | Delta |
|---|---|---|---|
| bot.py | 603 | 512 | -91 |
| conversational_handler.py | 614 | 496 | -118 |
| session_adapter.py | 366 | 302 | -64 |
| memory_bridge.py | 295 | 251 | -44 |

**Verdict: PASS** — All line counts match actual source files.

---

## Finding 3: Code Reduction Claim — PASS

**Criterion**: Verify "31.2% net / 44.2% of affected (NOT 59%)".

**ADR-035 claims** (lines 148, 1108):
- Net reduction: 8,057 lines (31.2% of 25,796 total)
- Reduction on affected code: 44.2% (8,057 of 18,238 affected lines)

**Verification** (from Research Report 04, §4.1, lines 316-322):

| Classification | Files | Current | Post | Net Delta |
|---|---|---|---|---|
| DELETE | 20 | 4,381 | 0 | **-4,381** |
| KEEP | 27 | 7,558 | 7,558 | 0 |
| REFACTOR | 66 | 13,857 | ~8,536 | **-5,321** |
| CREATE | 7 | 0 | ~1,645 | **+1,645** |
| **TOTAL** | **120** | **25,796** | **~17,739** | **-8,057** |

**Math checks**:
- **31.2% net**: 8,057 / 25,796 = 31.23% ✅
- **44.2% of affected**: 8,057 / 18,238 = 44.18% ✅
  - (where affected = DELETE + REFACTOR = 4,381 + 13,857 = 18,238)

**Note on research report discrepancy**: Research Report 04 headline (line 22) states "53.2% reduction on affected code only." This is the **gross** reduction (9,702 / 18,238 = 53.2%) that excludes the CREATE additions (+1,645 lines). The ADR's 44.2% is the **net** reduction including CREATE files. Both are valid with different definitions — the ADR correctly uses the net figure.

**Comparison to rejected MASTER plan claim**:
- MASTER plan: "59% reduction" — based on inflated line counts and subset scope (~9,378 lines)
- ADR-035 corrected: "31.2% net / 44.2% affected" — based on verified counts across full 25,796-line codebase
- ADR-035 explicitly notes the correction on lines 1112-1113

**Verdict: PASS** — Both 31.2% net and 44.2% of affected are mathematically correct.

---

## Finding 4: Slash Command Count — PASS

**Criterion**: Verify 35 slash commands (NOT 33).

**Research ground truth** (Report 02 §2, line 64): "Actual slash command count: 35 (not 33). Source: `src/discord/commands.py:126-249`."

**ADR-035 states**:
- Line 93: "35 guild-scoped slash commands"
- Line 269: "35 slash commands → Hermes plugins"
- Line 273: "All 35 cmd_*.py files (6,893 lines total)"
- Line 335: Summary table totals 35 commands (8 + 15 + 12 = 35)

**MASTER plan incorrectly claimed 33** — ADR-035 corrects this.

**Verdict: PASS** — 35 slash commands is correct.

---

## Finding 5: 9Router localhost:20128 — PASS

**Criterion**: 9Router routing config is correctly described.

**Research ground truth** (Report 02 §6, lines 282-290): 9Router at `localhost:20128` with OpenAI-compatible `/v1` endpoint.

**ADR-035 describes**:
- Line 98: "9Router at localhost:20128 — GPT-5.5 primary, DeepSeek V4 Flash fallback"
- Line 132: "Hermes configured as custom provider pointing to localhost:20128"
- Lines 1084-1090: Config snippet:
  ```yaml
  model: gpt-5.5
  base_url: http://localhost:20128/v1
  api_key: ${NINEROUTER_API_KEY}
  provider: custom
  ```
- Line 1092: Fallback chain: GPT-5.5 → DeepSeek V4 Flash
- Line 1094: Budget enforcement via custom `pre_tool_call` hook

**Verdict: PASS** — 9Router routing config is correctly and consistently described.

---

## Finding 6: PostgreSQL Primary Data Source — PASS

**Criterion**: PostgreSQL remains primary write authority; Hermes never writes to it directly in hybrid mode.

**ADR-035 states** (throughout):
- Line 231 (Pillar 2): "PostgreSQL+pgvector primary write authority unchanged — 47 tables, 12 schemas; Hermes compression and session_search adopted as read-only supplements"
- Line 594: "Hermes compression and session_search operate as read-only supplements — they do not write to canonical memory"
- Line 596: "Hermes SQLite for session state is operational/transient, not canonical memory"
- Line 1308 (Implementation Notes): "PostgreSQL+pgvector is write authority for all canonical memory throughout migration"
- Phase 3 Gate (line 1357): "Zero PostgreSQL data modifications from Hermes path"

**Research Report 02 §3 (lines 124-155)** confirms hybrid memory architecture is the strongest part of the plan, with ADR-007 gray area (Hermes SQLite for transient session state) correctly scoped as non-canonical.

**Verdict: PASS** — PostgreSQL as primary write authority is consistently maintained.

---

## Finding 7: Redis DB Assignments vs ADR-030 — NEEDS REVIEW

**Criterion**: Redis DB assignments must be consistent with ADR-030 (accepted, CRITICAL).

### ADR-030 Canonical Assignments

| DB | Purpose |
|---|---|
| DB0 | Task queue |
| DB1 | LLM cache |
| DB2 | **Surveillance buffer** |
| DB3 | **Sessions / working memory** |
| DB4 | **Pub/Sub** |
| DB5 | **Rate limiting** |

### ADR-035 Redis DB Usage

| ADR-035 Reference | DB Used | Purpose | ADR-030 Says |
|---|---|---|---|
| Line 94, 215, 216, 285 | DB4 | Session cache (current state) | DB4 = Pub/Sub |
| Lines 348, 448, 606, 848-849 | DB2 | Consent cache | DB2 = Surveillance buffer |
| Lines 626, 708, 733 | DB5 | Safety plugin state | DB5 = Rate limiting |
| Lines 1166, 1188, 1343, 1455 | DB4/DB5 | Shadow mode separation | Both conflict |

### Conflicts

1. **DB2: Consent cache vs Surveillance buffer** — ADR-035 uses DB2 for consent caching (Redis DB2 cache with 60s TTL). ADR-030 canonically assigns DB2 to the surveillance buffer. These are different workloads that cannot safely share a DB.

2. **DB3: Not used by ADR-035** — ADR-030 assigns DB3 to sessions/working memory, but ADR-035 routes session management through DB4 instead.

3. **DB4: Session cache vs Pub/Sub** — ADR-035 describes current state as "Redis DB4 session cache" and maintains DB4 for session management. ADR-030 assigns DB4 to Pub/Sub. If runtime already diverges from ADR-030, this should be acknowledged.

4. **DB5: Safety state vs Rate limiting** — ADR-035 assigns DB5 to the GuinevereSafetyPlugin state persistence (every 60s snapshots). ADR-030 assigns DB5 to rate limiting.

### What's Missing

ADR-035 does **NOT** reference ADR-030 in its related documents (lines 21-35). ADR-030 is conspicuously absent from a list that includes ADR-025, ADR-032, and ADR-033. The ADR should either:

- **Option A**: Reference ADR-030 and justify each assignment change, noting that ADR-030 must be superseded or updated.
- **Option B**: Use Redis DB6+ for new Hermes-specific purposes (DB6 = consent cache, DB7 = safety state) to avoid conflicting with canonical ADR-030 assignments.
- **Option C**: Explicitly supersede ADR-030 with a note in the related documents section and a migration table showing old → new assignments.

**Verdict: NEEDS REVIEW** — Redis DB assignments in ADR-035 conflict with the accepted, CRITICAL-risk ADR-030 without acknowledgment or justification. This is not a blocking failure (the assignments can be justified) but the ADR is incomplete until this cross-reference is resolved.

---

## Summary Table

| # | Criterion | Source | Verdict |
|---|---|---|---|
| 1 | Hook names match Hermes API | Report 02 §5 | **PASS** |
| 2 | Line counts match actual files | Report 02 §2 | **PASS** |
| 3 | Code reduction: 31.2% net / 44.2% affected | Report 04 §4.1 | **PASS** |
| 4 | 35 slash commands (not 33) | Report 02 §2 | **PASS** |
| 5 | 9Router localhost:20128 routing | Report 02 §6 | **PASS** |
| 6 | PostgreSQL primary data source | Report 02 §3 | **PASS** |
| 7 | Redis DB assignments vs ADR-030 | ADR-030 | **NEEDS REVIEW** |

**Overall**: 6 PASS, 0 FAIL, 1 NEEDS REVIEW

---

## Recommended Action

Resolve Finding 7 by either:
1. Adding ADR-030 to the Related Documents table with a justification note for DB reassignments.
2. Migrating consent cache to DB6 and safety state to DB7 to avoid conflicting with existing ADR-030 assignments.
3. Adding a section to the ADR that explicitly supersedes ADR-030's DB2/DB4/DB5 assignments for the post-migration state, with a clear migration table.

---

## Footer

| Field | Value |
|---|---|
| Audit ID | AUDIT-TECH-ADR035-001 |
| Date | 2026-06-04 |
| Auditor | Guinevere (Sisyphus-Junior) |
| Scope | Technical accuracy only (hook names, line counts, code reduction, command count, routing, PostgreSQL authority, Redis DB) |
| Excluded | Safety compliance, structural completeness (handled by separate auditors) |
| Verdict | **NEEDS REVIEW** |
| Files Read | `adr/ADR-035-hermes-migration.md`, `research-reports/adr-035-prep/02-architecture-validation.md`, `research-reports/adr-035-prep/04-code-reduction-analysis.md`, `adr/ADR-030-redis-db-assignments.md` |
| Next Action | Resolve Redis DB assignment conflicts with ADR-030 |