# ADR-035 Planner Gate — Synthesis of 8 Prep Reports

> Generated: 2026-06-04 | Status: APPROVED FOR IMPLEMENTATION | Parent: Guinevere

## §1 Input Reports

| # | Report | Lines | Key Verdict |
|---|---|---|---|
| 01 | ADR Format Analysis | 1,040 | MADR template confirmed; 2,000-line target unprecedented (longest ADR = 224 lines) |
| 02 | Architecture Validation | 408 | 4 PASS, 3 WARNING, 2 FAIL — hook names WRONG, code reduction inflated |
| 03 | Safety Compliance Map | ~1,200 | All 8 AC-SAFE + 13 mechanisms mapped; 10 Phase 1 gates; NO BLOCKING GAPS |
| 04 | Code Reduction Analysis | ~400 | 113 files, 25,796→17,739 lines (31.2% net reduction) |
| 05 | Risk Deep Dive | 414 | 15 risks, 3 show-stoppers (R-001, R-004, R-013) |
| 06 | Rollback Strategy | 1,723 | Per-phase rollback with exact commands; < 5 min max downtime |
| 07 | Alternatives Analysis | 737 | 4 architectures compared; Hybrid Hermes Migration chosen |
| 08 | NFR Mapping | ~600 | 40 NFRs: 17 IMPROVES, 18 NEUTRAL, 4 DEGRADES (mitigated), 1 phased |

## §2 MANDATORY CORRECTIONS (from Report 02)

ADR-035 MUST use CORRECTED values. Do NOT copy inflated numbers from MASTER-RESTRUCTURE-PLAN.md.

### 2.1 Hook Name Corrections

| MASTER Plan (WRONG) | Actual Hermes Hook (CORRECT) | Safety Feature |
|---|---|---|
| `pre_gateway_dispatch` | `pre_prompt` | HARD STOP + distress detection |
| `transform_llm_output` | `post_response` | Yandere FSM enforcement, secret scanner |
| `pre_llm_call` | `post_prompt` | Persona drift injection |
| `pre_tool_call` | `pre_tool_call` (CORRECT) | Consent gate + auth matrix |
| `transform_tool_result` | `post_tool_call` | Output sanitization |
| N/A | `pre_response` | Final safety check before delivery |
| N/A | `on_error` | Error classification + audit |

### 2.2 Line Count Corrections

| File | MASTER Plan Claim | Actual Verified |
|---|---|---|
| bot.py | 603 | **512** |
| conversational_handler.py | 614 | **496** |
| session_adapter.py | 366 | **302** |
| memory_bridge.py | 295 | **251** |

### 2.3 Code Reduction Correction

| Metric | MASTER Plan Claim | Corrected Value |
|---|---|---|
| Total lines (affected) | ~9,378 | **18,238** (DELETE + REFACTOR) |
| Total lines (all codebase) | N/A | **25,796** (113 Python files) |
| Net reduction | 5,528 (59%) | **8,057 (31.2% of total, 44.2% of affected)** |
| Slash commands | 33 | **35** |

### 2.4 Additional Corrections

- ADR-034 file missing from filesystem (listed in index but doesn't exist)
- `hermes security`: 11 vulns (1 HIGH ecdsa, 4 MODERATE aiohttp/pip, 1 LOW pip, 4 UNKNOWN PyJWT)
- Shadow mode contradiction: Report 03 says "do not run both bots on same guild" but MASTER plan Phase 2.10 requires parallel operation — ADR-035 must address this

## §3 ADR-035 Structure (Target: 2,000+ lines)

### YAML Frontmatter
```yaml
adr: "ADR-035"
title: "Hermes NousResearch Migration Architecture"
status: "Proposed"
date: "2026-06-04"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - architecture
  - migration
  - hermes
  - discord
  - safety
  - mcp
  - memory
  - llm-routing
risk_level: "CRITICAL"
supersedes: null
related_documents:
  - "docs/00-core/03-TechArchitecture_v2.0.md"
  - "docs/60-persona/60-PersonaSafetyPolicy_v1.0.md"
  - "docs/60-persona/61-SystemPromptMaster_v1.1.md"
  - "research-reports/hermes-restructure/MASTER-RESTRUCTURE-PLAN.md"
  - "ADR-001"
  - "ADR-002"
  - "ADR-003"
  - "ADR-005"
  - "ADR-007"
  - "ADR-013"
  - "ADR-025"
  - "ADR-032"
  - "ADR-033"
```

### Section Allocation (Target 2,000+ lines)

| Section | Target Lines | Content |
|---|---|---|
| YAML + Metadata | 40 | Frontmatter, Status, Date, Deciders, Tags, Risk Level, Supersedes, Related Documents |
| Context | 200 | Current architecture, why Hermes, migration drivers, codebase state |
| Decision Drivers | 150 | 12+ drivers with priority weighting |
| Considered Options | 300 | 4 architectures from Report 07 with comparison tables |
| Decision Outcome | 400 | 5 pillars with corrected hook names, corrected line counts, migration matrix |
| Consequences | 300 | Positive (12+), Negative (8+), Risks (15 from Report 05), Mitigations |
| Rollback Plan | 200 | Per-phase from Report 06, condensed |
| Implementation Notes | 250 | 7-phase plan with gate criteria, safety gates, timeline |
| Safety Compliance Matrix | 150 | AC-SAFE mapping from Report 03, condensed |
| NFR Impact Assessment | 100 | 40 NFRs from Report 08, condensed |
| Links | 30 | Cross-references |
| Review Record | 20 | Initial review |
| Version History | 20 | v1.0 |
| **TOTAL** | **~2,160** | |

## §4 Binding Constraints

1. **ADR-007**: PostgreSQL primary, NO SQLite for canonical memory
2. **ADR-013**: Guinevere MCP native replaces OpenCode
3. **ADR-001/002**: Safety > persona flavor, ethical boundaries architectural
4. **PersonaSafetyPolicy**: Y6 architecturally impossible, HARD STOP non-negotiable
5. **Data sovereignty**: No cloud SaaS memory providers
6. **Budget**: $30/month total infrastructure
7. **Shared VPS**: Aizanta co-hosted, port conflicts must be managed

## §5 Evidence Requirements

- ADR-035 must reference all 16 research reports from `research-reports/hermes-restructure/`
- ADR-035 must reference all 8 prep reports from `research-reports/adr-035-prep/`
- All hook names must match §2.1 corrections
- All line counts must match §2.2 corrections
- Code reduction percentage must match §2.3 corrections

## §6 Approval

- Planner gate: APPROVED
- Ready for ADR-035 implementation agent
- Corrections MANDATORY — implementation agent must verify compliance
