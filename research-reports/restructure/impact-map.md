# Phase Restructure Impact Map

**Date:** 2026-06-03  
**Author:** Guinevere (parent synthesis from 5 explore agents)  
**Status:** Research synthesis complete  
**Evidence Root:** `research-reports/restructure/`

---

## 1. Target Phase Structure (from Faiz)

### MVP (P0-P8) — UNCHANGED
| Phase | Name | Steps |
|---|---|---|
| P0 | Infrastructure Setup | 29 |
| P1 | LLM + Hermes Agent | 21 |
| P2 | Discord Bot | 21 |
| P3 | Memory System | 19 |
| P4 | Persona Engine | 23 |
| P5 | Agent Loop | 23 |
| P6 | MCP Tools | 21 |
| P7 | Surveillance | 22 |
| P8 | Observability + MVP Gate | 23 |
| **Total** | | **202** |

### Stabilization (P9-P10)
| Phase | Name | Steps | Deps |
|---|---|---|---|
| P9 | Financial Tracking | 12 | P8 |
| P10 | Production Hardening | 19 | P8 |
| **Total** | | **31** | |

### Expansion (P11-P22)
| Phase | Name | Steps | Deps |
|---|---|---|---|
| P11 | WhatsApp | TBD | P5+P8 |
| P12 | Gmail/Email | TBD | P5+P8 |
| P13 | X Auto Poster | TBD | P5+P6+P7+P8 |
| P14 | Wearable/Xiaomi Watch | TBD | P7+P8 |
| P15 | Windows Daemon + WebSocket | TBD | P5+P8 |
| P16 | Knowledge Graph | TBD | P3+P5+P8 |
| P17 | Cross-Device Sync | TBD | P15+P8 |
| P18 | Advanced Memory | TBD | P3+P8 |
| P19 | Multi-Project Context | TBD | P3+P5+P8 |
| P20 | Self-Improvement Loop | TBD | P5+P8 |
| P21 | Voice Interface | TBD | P2+P8 |
| P22 | Additional Integrations TBD | TBD | P8 |

---

## 2. Old P11 → New P11-P22 Redistribution Map

| Old Step | Old Description | New Phase | New Step ID |
|---|---|---|---|
| P11-001 | Windows Daemon Architecture | P15 | P15-001 |
| P11-002 | Windows Active Window Tracking | P15 | P15-002 |
| P11-003 | Windows Idle State Detection | P15 | P15-003 |
| P11-004 | Windows Browser History Capture | P15 | P15-004 |
| P11-005 | Windows Screenshot Capture | P15 | P15-005 |
| P11-006 | Windows Clipboard Monitoring | P15 | P15-006 |
| P11-007 | Windows Daemon Installer | P15 | P15-007 |
| P11-008 | WebSocket Connection to VPS | P15 | P15-008 |
| P11-009 | WhatsApp Baileys Service | P11 | P11-001 |
| P11-010 | WhatsApp QR Authentication | P11 | P11-002 |
| P11-011 | WhatsApp Message Routing | P11 | P11-003 |
| P11-012 | Gmail OAuth Integration | P12 | P12-001 |
| P11-013 | Gmail Notification Forwarding | P12 | P12-002 |
| P11-014 | Gmail Draft Assistance | P12 | P12-003 |
| P11-015 | Wearable Setup | P14 | P14-001 |
| P11-016 | Wearable Health Data | P14 | P14-002 |
| P11-017 | Wearable Alert Forwarding | P14 | P14-003 |
| P11-018 | Multi-Project Context | P19 | P19-001 |
| P11-019 | Project Context Switching | P19 | P19-002 |
| P11-020 | Knowledge Graph Foundation | P16 | P16-001 |
| P11-021 | Knowledge Graph Queries | P16 | P16-002 |
| P11-022 | Advanced Memory Consolidation | P18 | P18-001 |
| P11-023 | Memory Importance Scoring | P18 | P18-002 |
| P11-024 | Cross-Platform Event Correlation | P17 | P17-001 |
| P11-025 | Integration E2E Test | (distribute per phase) | TBD |

### Brand New Phases (no old steps)
| Phase | Name | Notes |
|---|---|---|
| P13 | X Auto Poster | Detailed spec provided by Faiz — Obscura CDP, S3 queue, LLM captions, 3h heartbeat, Discord notifications, PostgreSQL state |
| P20 | Self-Improvement Loop | No detail yet — placeholder |
| P21 | Voice Interface | Deps: P2+P8 — placeholder |
| P22 | Additional Integrations TBD | Catch-all — placeholder |

---

## 3. Known Discrepancies (Pre-Existing)

| Document | P9 Steps | P10 Steps | P11 Steps | Notes |
|---|---|---|---|---|
| **PROGRESS.md** | 12 | 19 | 25 | Considered canonical |
| **CHECKLIST.md** | 15 | 20 | 25 | 3 extra P9, 1 extra P10 |
| **StepPrompts.md** | 12 | 18 + 1 gate | 25 | P10-018b = MVP gate step |
| **IMPLEMENTATION_GUIDE.md** | "252 steps across 12 phases" | — | — | Header count |

**Decision for restructure:** Use PROGRESS.md as canonical source of truth. Reconcile CHECKLIST.md and StepPrompts.md to match PROGRESS.md counts during this restructure.

---

## 4. Files Requiring Changes

### Priority 1 — Direct Phase Tracker Files (MUST CHANGE)

| # | File | Changes Required | Scope |
|---|---|---|---|
| 1 | `PROGRESS.md` | Rewrite P9/P10/P11 sections → P9/P10 + P11-P22; update header step/phase counts; update Phase Summary table; update Quick Start text; update Cost Tracking table; update "post-MVP" language to "Stabilization" + "Expansion" | ~200 lines |
| 2 | `CHECKLIST.md` | Rewrite sections 11/12/13; reconcile step count discrepancies; add sections for P11-P22; update MVP Gate section | ~300 lines |
| 3 | `stepprompts/StepPrompts.md` | Rewrite Phase 9/10/11 sections; add Phases 11-22; update header "12 phases" → "23 phases"; update dependency table; update cost table; add P13 detailed spec | ~500 lines |
| 4 | `IMPLEMENTATION_GUIDE.md` | Update "252 steps across 12 phases" count; update phase table; update post-MVP references | ~50 lines |

### Priority 2 — Governance/Core Docs (Targeted Changes)

| # | File | Changes Required | Scope |
|---|---|---|---|
| 5 | `docs/10-governance/17-ADR_Index_v1.0.md` | Add new ADR entry for phase restructure decision | ~5 lines |
| 6 | `docs/00-core/00-BRD_v2.0.md` | Fix Phase naming conflict — align Phase 0-5 names with Charter/AcceptanceCriteria | ~20 lines |
| 7 | `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | Update cost allocation table for new phase structure (P9-P22 instead of P9-P11) | ~30 lines |
| 8 | `README.md` (root) | Add/update phase summary section if present | ~10 lines |
| 9 | `docs/README.md` | Update doc index category references if needed | ~5 lines |
| 10 | `adr/README.md` | Fix "first 25 ADRs" stale count → "first 33 ADRs" (or current actual count) | ~2 lines |

### Priority 3 — Files to Verify (May Need Changes)

| # | File | Risk | Action |
|---|---|---|---|
| 11 | `stepprompts/StepPrompts.md.bak` | Backup file — may cause confusion | Consider removing or clearly marking as deprecated |
| 12 | ADR files in `adr/` | ADR-021 filename contains "post-mvp"; ADR-033 refs P11 | Review ADR-021 title, ADR-033 references |
| 13 | `docs/00-core/06-Persona_Document_v3.0.md` | Surveillance phased rollout uses Phase 1-3 | Verify these are NOT delivery phases P1-P3 |
| 14 | `docs/10-governance/15-RTM_v1.0.md` | Maps requirements to delivery Phases 2-4 | Verify no P9/P10/P11 refs |

### Files NOT Requiring Changes

| Directory/File | Reason |
|---|---|
| `docs/10-governance/10-ProjectCharter_v1.0.md` | Phase 0-5 governance phases — separate concept |
| `docs/10-governance/11-FeasibilityStudy_v1.0.md` | SDLC loop phases only |
| `docs/10-governance/12-SRS_v1.0.md` | P0-P5 are priority levels, not phases |
| `docs/10-governance/13-FSD_v1.0.md` | SDLC loop Phase 1-7 only |
| `docs/10-governance/14-TDD_Guide_v1.0.md` | SDLC loop + priority levels only |
| `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` | Governance delivery phases + SDLC loop |
| `docs/00-core/01-PRD_v2.2.md` | SDLC loop + priority levels |
| `docs/00-core/02-TechnicalArchitecture_v2.0.md` | SDLC loop phases |
| `docs/00-core/03-AgentLoopSpec_v2.0.md` | SDLC loop Phase 1-7 |
| `docs/00-core/04-MemorySchema_v2.0.md` | Only boilerplate "7 phases" |
| `docs/00-core/05-APIIntegration_v2.0.md` | Priority levels + one loop ref |

---

## 5. Phase Naming Taxonomy — Disambiguation Required

The repo contains **FOUR distinct "phase" concepts** that must remain clearly separated:

| Concept | Values | Defined In | Must NOT Confuse With |
|---|---|---|---|
| **Step Phases** (P0-P22) | P0-P22 | PROGRESS.md, CHECKLIST.md, StepPrompts.md | All others |
| **Governance Delivery Phases** | Phase 0-5 | Charter §17, AcceptanceCriteria §5.12 | Step phases |
| **SDLC Loop Phases** | Phase 1-7 | AgentLoopSpec, FSD, TDD | All others |
| **FinOps Budget Phases** | Phase 1-3 | Cost & FinOps Model §4.1 | All others |
| **Priority Levels** | P0-P5 | SRS, TDD, PRD, API Integration | Step phases |

**Recommendation:** In all restructured docs, use explicit qualifiers:
- "Step Phase P9" or just "P9" (step phases)
- "Governance Phase 3" or "Delivery Phase 3" (governance)
- "SDLC Phase 4" or "Loop Phase 4" (agent loop)
- "Budget Phase 2" (FinOps)
- "Priority P0" (test/requirement priority)

---

## 6. P13 X Auto Poster — Detailed Spec

New phase P13 requires these components (from Faiz's specification):

| Component | Description |
|---|---|
| Obscura CDP | Browser automation via Chrome DevTools Protocol |
| S3 Queue | Image/content queue stored in S3-compatible storage |
| LLM Captions | AI-generated post captions using LLM |
| 3h Heartbeat | Health check every 3 hours |
| Discord Notifications | Status updates pushed to Discord |
| PostgreSQL State | Posting history, scheduling state in PostgreSQL |
| Dependencies | P5 (Agent Loop) + P6 (MCP Tools) + P7 (Surveillance) + P8 (Observability) |

Step count: TBD (to be defined during implementation planning)

---

## 7. Cost Impact Analysis

### Current Cost Model (PROGRESS.md)
| Phase | Monthly Cost | Cumulative |
|---|---|---|
| P9 | $1 | $28 |
| P10 | $1 | $29 |
| P11 | $1 | $30 |

### Proposed Cost Model
| Phase | Monthly Cost | Cumulative | Notes |
|---|---|---|---|
| P9 | $1 | $28 | Financial Tracking (unchanged) |
| P10 | $1 | $29 | Production Hardening (unchanged) |
| P11-P22 | $1 total TBD | $30 | Expansion phases share budget envelope |

**Note:** FinOps cost model §4.1 uses "Phase 1/2/3" for BUDGET phases (storage rollout timeline). These must be renamed to "Budget Phase 1/2/3" to avoid collision with step phases.

---

## 8. Verification Strategy

### Grep Checks (9 checks)
1. `grep -rn "P11" --include="*.md"` → Should return P11 = WhatsApp only (not old Advanced Integrations)
2. `grep -rn "P9.*P10.*P11" --include="*.md"` → All references show Stabilization/Expansion grouping
3. `grep -rn "post-MVP" --include="*.md"` → Replaced with "Stabilization" or "Expansion" (except ADR-021 filename)
4. `grep -rn "Post-MVP" --include="*.md"` → Same as above
5. `grep -rn "P10-019\|P10-020" --include="*.md"` → Reconciled step counts
6. `grep -rn "252 steps\|12 phases" --include="*.md"` → Updated counts
7. `grep -rn "Phase 11" --include="*.md"` → Should refer to WhatsApp, not old "Advanced Integrations"
8. `grep -rn "P13" --include="*.md"` → X Auto Poster references present
9. `grep -rn "first 25 ADRs\|first 25 technical" --include="*.md"` → Updated to current count

### Cross-Reference Validation
- PROGRESS.md phase counts match CHECKLIST.md section step counts
- StepPrompts.md phase counts match PROGRESS.md
- IMPLEMENTATION_GUIDE.md header count matches actual totals
- ADR-Index references are current
- FinOps cost model phase labels disambiguated

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Step count discrepancies propagate | High | Medium | Use PROGRESS.md as canonical; reconcile all others |
| "Phase" confusion increases with 4+ concepts | Medium | High | Add disambiguation qualifiers in all modified docs |
| .bak file causes stale references | Low | Low | Delete or clearly mark as deprecated |
| ADR-021 filename "post-mvp" becomes misleading | Low | Low | Keep filename (ADR immutability), update description |
| Governance docs (Charter/AcceptanceCriteria) reference old structure | Medium | Medium | Verify they use delivery Phase 0-5, not step phases |
| BRD phase naming conflict persists | Medium | High | Fix BRD Phase 0-5 names to match Charter |

---

## 10. Research Reports Referenced

| Report | Path | Agent |
|---|---|---|
| P9/P10/P11 References | `research-reports/restructure/p9-p10-p11-references.md` | bg_d4a43c0b |
| Post-MVP References | `research-reports/restructure/post-mvp-references.md` | bg_5abde10f |
| Governance Phase References | `research-reports/restructure/governance-phase-references.md` | bg_98cc27d6 |
| Feature Name References | `research-reports/restructure/feature-name-references.md` | bg_b09c90d1 |

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-03 | Guinevere | Initial impact map from 5 explore agents |
