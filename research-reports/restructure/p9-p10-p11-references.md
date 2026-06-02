# P9, P10, P11 Reference Impact Map

> **Generated:** 2026-06-03
> **Purpose:** Exhaustive catalog of every P9/P10/P11 reference for phase restructuring
> **Old structure:** P9=Financial Tracking, P10=Production Hardening, P11=Integrations (mixed bag)
> **New structure:** P9=Financial Tracking, P10=Production Hardening, P11=WhatsApp, P12=Gmail, P13=X Auto Poster, P14=Wearable, P15=Windows Daemon, P16=Knowledge Graph, P17=Cross-Device Sync, P18=Advanced Memory, P19=Multi-Project, P20=Self-Improvement, P21=Voice, P22=Additional Integrations

---

## Summary Statistics

| Metric | Count |
|---|---|
| Total files with TRUE phase references | 28 |
| Total P9 references (true phase) | ~107 |
| Total P10 references (true phase) | ~134 |
| Total P11 references (true phase) | ~172 |
| Files with FALSE POSITIVE P9-P22 | 4 |
| "12 phases" / "252 steps" references | 8 files |

---

## SECTION A: TRUE PHASE REFERENCES (Must Update)

### A1. Core Planning Files (HIGHEST IMPACT)

#### File: `CHECKLIST.md`
**Path:** `C:\Users\faizz\guinevere\CHECKLIST.md`

| Line | Content | Phase Context |
|---|---|---|
| 36 | `| P9 \| $1 \| $28 \| $2 |` | P9 budget row |
| 37 | `| P10 \| $1 \| $29 \| $1 |` | P10 budget row |
| 38 | `| P11 \| $1 \| $30 \| $0 |` | P11 budget row |
| 708 | `## 11. Phase 9: Financial Tracking Verification` | P9 section header |
| 711 | `**Steps:** P9-001 through P9-015 (15 steps)` | P9 step range |
| 723 | `- [ ] P9-001: psql -d guinevere...tables exist` | P9 verification |
| 724 | `- [ ] P9-002: Tasker bank SMS -> classified` | P9 verification |
| 725 | `- [ ] P9-003: classify("Gojek Rp50000")` | P9 verification |
| 726 | `- [ ] P9-004: budget.status()` | P9 verification |
| 727 | `- [ ] P9-005: /finance summary in Discord` | P9 verification |
| 728 | `- [ ] P9-006: /finance add "Coffee Rp35000"` | P9 verification |
| 729 | `- [ ] P9-007: /finance report` | P9 verification |
| 730 | `- [ ] P9-008: python -m guinevere.finance.report` | P9 verification |
| 731 | `- [ ] P9-009: FinOps Grafana dashboard exists` | P9 verification |
| 732 | `- [ ] P9-010: No e-wallet scraping (AC-FIN-005)` | P9 verification |
| 733 | `- [ ] P9-011: provider_cost.summary()` | P9 verification |
| 734 | `- [ ] P9-012: Budget freeze simulation` | P9 verification |
| 735 | `- [ ] P9-013: Freeze does NOT affect safe-word` | P9 verification |
| 736 | `- [ ] P9-014: Evidence path for monthly report` | P9 verification |
| 737 | `- [ ] P9-015: Faiz reviews monthly report` | P9 verification |
| 743 | `- [ ] Evidence: evidence/phase-9/financial-setup-<date>.md` | P9 evidence path |
| 747 | `## 12. Phase 10: Production Hardening Verification` | P10 section header |
| 750 | `**Steps:** P10-001 through P10-020 (20 steps)` | P10 step range |
| 756 | `- [ ] Phase 9 complete` | P9 prerequisite |
| 762 | `- [ ] P10-001: ls audit-reports/security-audit` | P10 verification |
| 763 | `- [ ] P10-002: sudo apt list --upgradable` | P10 verification |
| 764 | `- [ ] P10-003: sudo nmap -sS localhost` | P10 verification |
| 765 | `- [ ] P10-004: pg_stat_activity count` | P10 verification |
| 766 | `- [ ] P10-005: pg_stat_user_tables vacuum` | P10 verification |
| 767 | `- [ ] P10-006: redis-cli CONFIG GET maxmemory` | P10 verification |
| 768 | `- [ ] P10-007: systemctl show resource limits` | P10 verification |
| 769 | `- [ ] P10-008: pg_dump + sops + s3 backup` | P10 verification |
| 770 | `- [ ] P10-009: Restore from backup` | P10 verification |
| 771 | `- [ ] P10-010: RTO <= 4h; RPO <= 24h` | P10 verification |
| 772 | `- [ ] P10-012: DR drill simulate VPS failure` | P10 verification |
| 773 | `- [ ] P10-013: Evidence backup restore drill` | P10 verification |
| 774 | `- [ ] P10-014: CI pipeline push test` | P10 verification |
| 775 | `- [ ] P10-017: git revert auto-redeploy` | P10 verification |
| 776 | `- [ ] P10-020: Rotate SOPS age key` | P10 verification |
| 786 | `## 13. Phase 11: Advanced Integrations Verification` | P11 section header |
| 789 | `**Steps:** P11-001 through P11-025 (25 steps)` | P11 step range |
| 795 | `- [ ] Phase 10 complete` | P10 prerequisite |
| 802 | `- [ ] P11-001: Windows daemon installed` | P11 verification |
| 803 | `- [ ] P11-003: Active window, idle detection` | P11 verification |
| 804 | `- [ ] P11-006: WhatsApp systemctl status` | P11 verification |
| 805 | `- [ ] P11-009: Gmail OAuth authenticated` | P11 verification |
| 806 | `- [ ] P11-011: Wearable paired + connected` | P11 verification |
| 807 | `- [ ] P11-013: Multi-project namespaces` | P11 verification |
| 808 | `- [ ] P11-015: Knowledge graph entity search` | P11 verification |
| 809 | `- [ ] P11-016: Memory consolidation daily job` | P11 verification |
| 810 | `- [ ] P11-018: HARD STOP across WhatsApp/Gmail` | P11 verification |
| 811 | `- [ ] P11-020: Total spend <= $30` | P11 verification |
| 812 | `- [ ] P11-021: Evidence phase-11 integrations-setup` | P11 evidence path |
| 813 | `- [ ] P11-022: Evidence wearable deferral` | P11 verification |
| 814 | `- [ ] P11-023: Evidence expansion review` | P11 verification |
| 815 | `- [ ] P11-024: Faiz approved expansion` | P11 verification |
| 816 | `- [ ] P11-025: Cost $30 cumulative hard cap` | P11 verification |

---

#### File: `PROGRESS.md`
**Path:** `C:\Users\faizz\guinevere\PROGRESS.md`

| Line | Content | Phase Context |
|---|---|---|
| 20 | `4. P9-P11 are post-MVP -- defer if budget pressure emerges.` | P9-P11 grouping |
| 36 | `| P9 | Financial | ... 0/12 ...` | P9 progress row |
| 37 | `| P10 | Hardening | ... 0/19 ...` | P10 progress row |
| 38 | `| P11 | Integrations | ... 0/25 ...` | P11 progress row |
| 329 | `## P9: Financial Tracking -- Post-MVP (12 steps)` | P9 section header |
| 332-343 | P9-001 through P9-012 step items | P9 step list |
| 345 | `## P10: Production Hardening -- Post-MVP (19 steps)` | P10 section header |
| 348-366 | P10-001 through P10-019 step items | P10 step list |
| 368 | `## P11: Advanced Integrations -- Post-MVP (25 steps)` | P11 section header |
| 371-395 | P11-001 through P11-025 step items | P11 step list |
| 412 | `| P9 Financial | $1 | $28 | Critical |` | P9 budget |
| 413 | `| P10 Hardening | $1 | $29 | Critical |` | P10 budget |
| 414 | `| P11 Integrations | $1 | $30 | Hard Cap |` | P11 budget |
| 417 | `$25-29 (defer P9-P11)` | P9-P11 deferral |
| 427 | `P9-P11 require P8 (post-MVP)` | P9-P11 dependency |
| 431 | `Budget overrun ($30 cap) | Med | P9-P11 deferred` | P9-P11 risk |
| 452 | `| P9 | 12 | 1-2 | 12 | 24 | 3-6 |` | P9 timeline |
| 453 | `| P10 | 19 | 1-2 | 18 | 36 | 5-9 |` | P10 timeline |
| 454 | `| P11 | 25 | 1-2 | 25 | 50 | 7-13 |` | P11 timeline |
| 458 | `Post-MVP (P9-P11): +15-28 days | Total project: 72-142 days` | P9-P11 timeline |

---

#### File: `stepprompts/StepPrompts.md`
**Path:** `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md`

| Line | Content | Phase Context |
|---|---|---|
| 11 | `**Total Phases:** 12 (P0-P11)` | Phase count -- MUST CHANGE |
| 28 | `> Code-only steps (P3-P7, P9-P11) have minimal shared VPS impact.` | P9-P11 grouping |
| 116 | `P9 Financial (12 steps, $1/mo)       }` | P9 in ASCII diagram |
| 117 | `P10 Hardening (18 steps, $1/mo)       } Post-MVP` | P10 in ASCII diagram |
| 118 | `P11 Advanced Integrations (25 steps, $1/mo) }` | P11 in ASCII diagram |
| 7597 | `## Phase 9: Financial Tracking (Post-MVP)` | P9 section header |
| 7608 | `### Steps P9-001 to P9-012` | P9 steps header |
| 7613 | `**Git Commit:** feat(P9): pending` | P9 git commit |
| 7615-7626 | P9-001 through P9-012 descriptions | P9 step definitions |
| 7629 | `# P9-005: /finance summary command` | P9 code example |
| 7643 | `**Evidence:** docs/setup-evidence/P9/STEP-P9-001/ through .../P9/STEP-P9-012/` | P9 evidence paths |
| 7648 | `## Phase 10: Production Hardening (Post-MVP)` | P10 section header |
| 7654 | `### Steps P10-001 to P10-018` | P10 steps header |
| 7659 | `**Git Commit:** feat(P10): pending` | P10 git commit |
| 7661-7678 | P10-001 through P10-018 descriptions | P10 step definitions |
| 7681 | `# P10-008: GitHub Actions CI` | P10 code example |
| 7702 | `**Evidence:** docs/setup-evidence/P10/STEP-P10-001/ through .../P10/STEP-P10-018/` | P10 evidence paths |
| 7707 | `### Step P10-018b: MVP Acceptance Gate (AC-PHASE-006)` | P10 MVP gate step |
| 7709 | `**Phase:** P10 -- MVP Preparation` | P10 phase label |
| 7713 | `**Dependencies:** P10-018, ALL P0-P10 steps` | P10 dependencies |
| 7718 | `**Gate Type:** BLOCKING -- Phase 11 (Post-MVP) cannot begin` | P11 gate reference |
| 7754 | `**Evidence:** docs/setup-evidence/P10/STEP-P10-018b/mvp-acceptance-report.md` | P10 evidence |
| 7769 | `## Phase 11: Advanced Integrations (Post-MVP)` | P11 section header |
| 7775 | `### Steps P11-001 to P11-025` | P11 steps header |
| 7780 | `**Git Commit:** feat(P11): pending` | P11 git commit |
| 7782-7806 | P11-001 through P11-025 descriptions (25 steps) | P11 step definitions |
| 7809 | `# P11-001: Windows daemon skeleton` | P11 code example |
| 7832 | `**Evidence:** docs/setup-evidence/P11/STEP-P11-001/ through .../P11/STEP-P11-025/` | P11 evidence paths |
| 7857 | `### Before P8 -> P9 (Post-MVP Gate)` | P9 transition checklist |
| 7860 | `### Before P9 -> P10 -> P11` | P9-P10-P11 transition |
| 7872 | `| P9 (Finance) | P10 (Hardening) | Partial | database schemas | Medium |` | P9-P10 collision |
| 7873 | `| P10 (Hardening) | P11 (Integrations) | No | systemd services | High |` | P10-P11 collision |
| 7977 | `| P9 | $1 | $22-23 | Financial tracking |` | P9 cost table |
| 7978 | `| P10 | $1 | $23-24 | Hardening overhead |` | P10 cost table |
| 7979 | `| P11 | $1 | $24-25 | Advanced integrations |` | P11 cost table |
| 7994 | `The MVP gate (Step P10-018b) is a BLOCKING checkpoint. Phase 11 (Post-MVP) cannot begin until:` | P10-P11 gate |
| 8020 | `| AC-PHASE-006 | Phase | P10-018b (MVP gate) | Covered |` | P10 acceptance criteria |

---

#### File: `stepprompts/StepPrompts.md.bak`
**Path:** `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md.bak`

> Archive/backup file. Same structure as StepPrompts.md. Lines 10, 74-76, 7046-7176, 7224-7240, 7344-7346. Update or skip.

---

#### File: `docs/IMPLEMENTATION_GUIDE.md`
**Path:** `C:\Users\faizz\guinevere\docs\IMPLEMENTATION_GUIDE.md`

| Line | Content | Phase Context |
|---|---|---|
| 3 | `> User manual for ... 252 steps across 12 phases (P0-P11)` | Phase count -- MUST CHANGE |
| 13 | `...12 phases (P0-P11) with 252 atomic steps...` | Phase count -- MUST CHANGE |
| 42 | `| P9 | Financial | 12 | $1 | P8 |` | P9 table row |
| 43 | `| P10 | Hardening | 18 | $1 | P8 |` | P10 table row |
| 44 | `| P11 | Integrations | 25 | $1 | P8 |` | P11 table row |
| 254 | `6. P9-P11 are post-MVP and deferrable under budget pressure` | P9-P11 grouping |

---

### A2. ADR Files

#### File: `adr/ADR-033-browser-automation-obscura.md`
**Path:** `C:\Users\faizz\guinevere\adr\ADR-033-browser-automation-obscura.md`

| Line | Content | Phase Context |
|---|---|---|
| 73 | `Strategic value: Critical for future X auto-poster (P11) where stealth is required` | P11 = X auto-poster -> NOW P13 |
| 80 | `X auto-poster (P11) requires anti-detect capabilities` | P11 = X auto-poster -> NOW P13 |
| 152 | `Built-in anti-detect: Critical for X auto-poster (P11) stealth requirements` | P11 = X auto-poster -> NOW P13 |
| 212 | `[Post-MVP: X Auto-Poster (P11)](../docs/post-mvp/) (future)` | P11 = X auto-poster -> NOW P13 |

---

### A3. Fixes

#### File: `fixes/2026-05-31-stepprompts-fixes.md`
**Path:** `C:\Users\faizz\guinevere\fixes\2026-05-31-stepprompts-fixes.md`

| Line | Content | Phase Context |
|---|---|---|
| 258 | `- P9: Test (12 steps)` | P9 description |
| 259 | `- P10: Documentation + Test (18 steps)` | P10 description |
| 260 | `- P11: Code + Infrastructure (25 steps)` | P11 description |
| 359 | `**Add step:** New step between P10 and P11` | P10-P11 boundary |
| 361 | `### Step P10-NEW: MVP Go-Live Gate` | P10 new step |
| 365 | `**Prerequisites:** All P0-P10 steps complete` | P0-P10 range |
| 376 | `**Gate:** BLOCKING -- no P11 execution until this step passes` | P11 gate |
| 465 | `| H-23 | No MVP gate | Add MVP gate section between P10 and P11 |` | P10-P11 boundary |
| 466 | `| H-24 | P9-P11 grouped | Accept as design decision |` | P9-P11 grouping |

---

### A4. Audit Reports

#### File: `audit-reports/2026-05-31-implementation-synthesis.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\2026-05-31-implementation-synthesis.md`

| Line | Content | Phase Context |
|---|---|---|
| 71 | `P9-P11 Post-MVP (Financial, Hardening, Integrations)` | P9-P11 summary |
| 490 | `### P9-P11: Post-MVP (50-60 steps)` | P9-P11 section |
| 498 | `**P9: Financial (12-15 steps)**` | P9 subsection |
| 507 | `**P10: Production Hardening (15-20 steps)**` | P10 subsection |
| 517 | `**P11: Advanced Integrations (20-25 steps)**` | P11 subsection |
| 628 | `| P9 | $1 | $28 | Financial tracking |` | P9 cost |
| 629 | `| P10 | $1 | $29 | Hardening |` | P10 cost |
| 630 | `| P11 | $1 | $30 | Advanced integrations |` | P11 cost |
| 643 | `Post-MVP phases (P9-P11) can be deferred` | P9-P11 deferral |

#### File: `audit-reports/2026-05-31-stepprompts-full-audit.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\2026-05-31-stepprompts-full-audit.md`

| Line | Content | Phase Context |
|---|---|---|
| 66 | `| C-12 | P3-P11 (191 steps) | 191 of 252 steps lack individual prompts` | P3-P11 range |
| 123 | `| H-17 | P1-P11 | 223 of 252 steps missing Shared VPS Notes` | P1-P11 range |
| 134 | `| H-23 | No MVP gate section between P10 and P11 |` | P10-P11 boundary |
| 135 | `| H-24 | P9-P11 phases exist but with grouped/summary format only |` | P9-P11 format |
| 199 | `Topological ordering of 252 steps verified correct.` | 252 steps count |
| 220 | `- 252 steps counted` | 252 steps count |
| 222 | `- 191 grouped (76%) -- P3-P11` | P3-P11 range |

#### File: `audit-reports/2026-05-31-stepprompts-fixes-applied.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\2026-05-31-stepprompts-fixes-applied.md`

| Line | Content | Phase Context |
|---|---|---|
| 87 | `| F-12 | Type field added | All P0-P2 + P3-P11 group headers |` | P3-P11 range |
| 100 | `| F-20 | P10-018: MVP Acceptance Gate | AC-PHASE-006 |` | P10 step |
| 132 | `| H-24 | P9-P11 grouped rationale | Applied |` | P9-P11 grouping |
| 156 | `| P10-018 | P10 -- MVP Preparation | MVP Acceptance Gate |` | P10 step |

#### File: `audit-reports/stepprompts-audit/phase1-fixes-applied.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\phase1-fixes-applied.md`

| Line | Content | Phase Context |
|---|---|---|
| 73 | `| -- | Group headers for P3-P11 | 12 group header edits | DONE |` | P3-P11 range |
| 83 | `| F-20 | AC-PHASE-006: MVP acceptance gate (P10-018b) | before Phase 11 | DONE |` | P10-P11 boundary |
| 119 | `| P9 | $28 | $22-23 |` | P9 cost |
| 120 | `| P10 | $29 | $23-24 |` | P10 cost |
| 121 | `| P11 | $30 | $24-25 |` | P11 cost |
| 157 | `- Metadata added to all P0-P11 steps` | P0-P11 range |

#### File: `audit-reports/stepprompts-audit/phase2-fixes-applied.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\phase2-fixes-applied.md`

| Line | Content | Phase Context |
|---|---|---|
| 30 | `| H-23 | MVP gate section | APPLIED | Near end of file + P10-018b exists |` | P10 step |
| 31 | `| H-24 | P9-P11 grouped rationale | APPLIED | Start of Phase 9 |` | P9-P11 + Phase 9 |

#### File: `audit-reports/stepprompts-audit/D6-D7-completeness-acceptance.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D6-D7-completeness-acceptance.md`

| Line | Content | Phase Context |
|---|---|---|
| 4 | `Target: StepPrompts.md (7360 lines, 252 claimed steps, 12 phases)` | 12 phases |
| 14 | `252 steps across 12 phases (P0-P11)...29+20+21+19+19+23+21+22+23+12+18+25 = 252` | P0-P11 + 252 steps |
| 35 | `| P9 | 12 | 12 | 0 | 12 (in 1 group) |` | P9 step count |
| 36 | `| P10 | 18 | 18 | 0 | 18 (in 1 group) |` | P10 step count |
| 37 | `| P11 | 25 | 25 | 0 | 25 (in 1 group) |` | P11 step count |
| 48 | `Phase Transition Checklist "Before P8 -> P9" (line 7224)` | P9 transition |
| 55 | `P9 (Financial, 12 steps), P10 (Hardening, 18 steps), P11 (Integrations, 25 steps)` | P9-P11 summary |
| 70 | `P3-P11 Grouped (182)` | P3-P11 range |
| 97 | `Steps P2-008 through P11-025 are batched` | P11 end |
| 129 | `P9-P11 steps average 2-3 lines each.` | P9-P11 detail level |
| 136 | `[MEDIUM] D6-011: P9-P11 have no commands, verification, or troubleshooting.` | P9-P11 gap |
| 137 | `Steps P9-001 to P11-025 are one-line descriptions` | P9-P11 range |
| 177 | `AC-SURV-002 | Windows daemon | NONE (P11-001 to P11-008)` | P11 steps |
| 186 | `AC-FIN-005 | Tasker capture | NONE (P9-002 to P9-004)` | P9 steps |
| 227 | `AC-PHASE-008 | Post-MVP expansion | NONE (P11 section)` | P11 section |

#### File: `audit-reports/stepprompts-audit/D9-D10-D11-D12-evidence-persona-loop-memory.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D9-D10-D11-D12-evidence-persona-loop-memory.md`

| Line | Content | Phase Context |
|---|---|---|
| 4 | `StepPrompts.md (7360 lines, 252 steps, 12 phases P0-P11)` | P0-P11 range |
| 43 | `Steps P6-021, P7-022, P8-023, P9-015, P10-020, P11-025: Evidence sections present.` | P9/P10/P11 evidence |

#### File: `audit-reports/stepprompts-audit/D3-D4-security-sharedvps.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D3-D4-security-sharedvps.md`

| Line | Content | Phase Context |
|---|---|---|
| 5 | `StepPrompts.md (v1.0, 7360 lines, 252 steps across 12 phases)` | 12 phases |
| 12 | `223 of 252 steps` | 252 steps |
| 135 | `Fix: Add explicit step...or defer to P10` | P10 deferral |
| 263 | `[HIGH] P1-P11 (223 steps): Missing Shared VPS Notes` | P1-P11 range |
| 279 | `P9-P11: No Shared VPS notes in any of 62 steps` | P9-P11 range |
| 413 | `Fix: Add a CI step (P10-008 or P10-011)` | P10 steps |
| 441 | `3. Add Shared VPS Notes to P1-P11` | P1-P11 range |

#### File: `audit-reports/stepprompts-audit/D2-D5-adr-dependency.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D2-D5-adr-dependency.md`

| Line | Content | Phase Context |
|---|---|---|
| 3 | `StepPrompts.md (7360 lines, 252 steps, 12 phases)` | 12 phases |
| 132 | `StepPrompts has 12 phases (P0-P11)` | P0-P11 range |
| 145 | `P5-004 to P5-010 implement exactly 7 phases. The 12 P0-P11 phases are infrastructure` | P0-P11 |
| 151 | `ADR-029 | P5/P10 address testing` | P10 reference |
| 366 | `StepPrompts Part 4 catalog (P3-009 to P11-025)` | P11 range |
| 378 | `Later phases (P5-P11) use compressed range notation` | P5-P11 range |

#### File: `audit-reports/stepprompts-audit/D1-D8-technical-cost.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D1-D8-technical-cost.md`

| Line | Content | Phase Context |
|---|---|---|
| 5 | `StepPrompts.md (7360 lines, 252 steps, 12 phases)` | 12 phases |

#### File: `audit-reports/P3/P3-FINAL-AUDIT/D07-adr-compliance.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\P3\P3-FINAL-AUDIT\D07-adr-compliance.md`

| Line | Content | Phase Context |
|---|---|---|
| 186 | `ADR-009 (P9); ADR-015, ADR-016, ADR-032 (P10); ADR-022, ADR-023 (P11)` | P9/P10/P11 ADR mapping |

#### File: `audit-reports/P0/STEP-P0-001-auditor-report.md`
**Path:** `C:\Users\faizz\guinevere\audit-reports\P0\STEP-P0-001-auditor-report.md`

| Line | Content | Phase Context |
|---|---|---|
| 76 | `Full tracker intact: 257 total steps, 11 phases (P0-P11)` | P0-P11 range |
| 77 | `Not truncated: covers all phases through P11.` | P11 end |

---

### A5. P0 Internal Context Reports (P10 Deferral References)

#### File: `audit-reports/P0/STEP-P0-009/step-p0-009-auditor-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 195 | `Update CHECKLIST.md...at a future hardening phase (P10).` | P10 future deferral |

#### File: `audit-reports/P0/STEP-P0-009/internal-context-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 213 | `Line 733: P10-007 refinement check` | P10 step reference |

#### File: `audit-reports/P0/STEP-P0-022/internal-context-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 151 | `SSH lockdown...Future P10 step; not required now` | P10 future deferral |
| 304 | `Do not modify UFW SSH rules...that is P10` | P10 future deferral |
| 551 | `### What to Defer (P10 Hardening)` | P10 section header |

#### File: `audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 397 | `Consider DOCKER-USER chain integration in P10 (hardening).` | P10 future deferral |

#### File: `audit-reports/P0/STEP-P0-018/internal-context-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 395 | `Defer SSL setup to P0-022 (Tailscale) or P10 (Hardening).` | P10 future deferral |
| 555 | `Defer to P0-022 (Tailscale) or P10.` | P10 future deferral |

#### File: `audit-reports/P0/STEP-P0-013/internal-context-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 40 | `Key rotation (P10-014)` | P10 step reference |

#### File: `audit-reports/P0/STEP-P0-012/internal-context-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 124 | `| Rotation compat (P10-014) | Key uses standard age format |` | P10 step reference |

#### File: `audit-reports/P0/STEP-P0-011/internal-context-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 282 | `| P10-014 (key rotation) | SOPS installed | Blocked |` | P10 step reference |

#### File: `audit-reports/P0/STEP-P0-016/step-p0-016-auditor-report.md`
| Line | Content | Phase Context |
|---|---|---|
| 131 | `Production hypertables...created in later steps (P7-007, P9-002, etc.).` | P9 step reference |

---

## SECTION B: FALSE POSITIVES (Do NOT Update)

### B1. Package Priority Numbers
**File:** `C:\Users\faizz\guinevere\audit-reports\P1\STEP-P1-003\step-p1-003-auditor-report.md`
- Lines 72-80: P9 through P17 are package priority numbers (P9=python-dotenv, P10=python-jose, P11=passlib, P12=apscheduler, etc.)

### B2. Persona Audit Check IDs
**File:** `C:\Users\faizz\guinevere\audit-reports\2026-05-31-persona-prompt-mcp-discord-audit.md`
- Lines 54-67: P9 through P22 are persona audit check IDs (P9=DND schedule, P10=Punishment table, P11=Yandere levels, P12=Distress protocol, etc.)

### B3. Pitfall Numbers in Research
**File:** `C:\Users\faizz\guinevere\docs\setup-evidence\P2\research\discordpy-bot-architecture-p2-017-019.md`
- Line 759: `P9: Forgetting @bot.event Decorator` -- Pitfall #9
- Line 775: `P10: Not Using async with bot for Clean Shutdown` -- Pitfall #10

### B4. DR Drill Phases (Unrelated)
**File:** `C:\Users\faizz\guinevere\research-reports\2026-05-30-dr-plan-backup-architecture-research.md`
- Lines 1690, 1694, 1700: Phase 9/10/11 are DR drill sequence phases, not project phases

### B5. Auditor Gate Row IDs
**File:** `C:\Users\faizz\guinevere\docs\setup-evidence\P3\STEP-P3-001\auditor-gate.md`
- Lines 152-153: P9 and P10 are audit checklist row IDs, not project phases

---

## SECTION C: P11 CONTENT MAPPING TO NEW PHASES

Current P11 steps (StepPrompts.md) map to new phases:

| Old P11 Step(s) | Content | New Phase |
|---|---|---|
| P11-001 to P11-008 | Windows daemon (architecture, tracking, detection, installer, WebSocket) | **P15** Windows Daemon |
| P11-009 to P11-011 | WhatsApp Baileys (setup, QR auth, message routing) | **P11** WhatsApp (NEW) |
| P11-012 to P11-014 | Gmail OAuth (integration, notification, draft assistance) | **P12** Gmail (NEW) |
| P11-015 to P11-017 | Wearable (setup, health data, alert forwarding) | **P14** Wearable (NEW) |
| P11-018 to P11-019 | Multi-project context (namespaces, switching) | **P19** Multi-Project (NEW) |
| P11-020 to P11-021 | Knowledge graph (foundation, queries) | **P16** Knowledge Graph (NEW) |
| P11-022 to P11-023 | Memory consolidation (forgetting curves, importance scoring) | **P18** Advanced Memory (NEW) |
| P11-024 | Cross-platform event correlation | **P17** Cross-Device Sync (NEW) |
| P11-025 | Integration E2E test | Split across new phases |
| ADR-033 X auto-poster (labeled P11) | X Auto Poster | **P13** X Auto Poster (NEW) |

Missing from old P11 (new additions):
- **P20** Self-Improvement -- entirely new
- **P21** Voice -- entirely new
- **P22** Additional Integrations -- catch-all

---

## SECTION D: FILES REQUIRING UPDATES (Sorted by Priority)

### Priority 1 -- Core Planning (Must Update First)
1. `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md` -- 40+ references
2. `C:\Users\faizz\guinevere\PROGRESS.md` -- 30+ references
3. `C:\Users\faizz\guinevere\CHECKLIST.md` -- 50+ references
4. `C:\Users\faizz\guinevere\docs\IMPLEMENTATION_GUIDE.md` -- 6 references

### Priority 2 -- ADR Cross-References
5. `C:\Users\faizz\guinevere\adr\ADR-033-browser-automation-obscura.md` -- 4 references (P11 -> P13)

### Priority 3 -- Audit Reports (Historical, Consider Addendum Instead of Edit)
6. `C:\Users\faizz\guinevere\audit-reports\2026-05-31-implementation-synthesis.md`
7. `C:\Users\faizz\guinevere\audit-reports\2026-05-31-stepprompts-full-audit.md`
8. `C:\Users\faizz\guinevere\audit-reports\2026-05-31-stepprompts-fixes-applied.md`
9. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D6-D7-completeness-acceptance.md`
10. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D2-D5-adr-dependency.md`
11. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D3-D4-security-sharedvps.md`
12. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D9-D10-D11-D12-evidence-persona-loop-memory.md`
13. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\phase1-fixes-applied.md`
14. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\phase2-fixes-applied.md`
15. `C:\Users\faizz\guinevere\audit-reports\stepprompts-audit\D1-D8-technical-cost.md`
16. `C:\Users\faizz\guinevere\audit-reports\P3\P3-FINAL-AUDIT\D07-adr-compliance.md`
17. `C:\Users\faizz\guinevere\audit-reports\P0\STEP-P0-001-auditor-report.md`

### Priority 4 -- P0 Internal Context Reports (Deferral References to P10)
18-27. Nine P0 audit/context reports referencing P10 as future deferral target

### Priority 5 -- Fixes (Historical)
28. `C:\Users\faizz\guinevere\fixes\2026-05-31-stepprompts-fixes.md`

### Archive Only
29. `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md.bak` -- update or skip

---

## SECTION E: COMPLETE FILE LIST

| # | File (relative) | P9 | P10 | P11 | 12ph | Priority |
|---|---|---|---|---|---|---|
| 1 | `CHECKLIST.md` | Y | Y | Y | | P1 |
| 2 | `PROGRESS.md` | Y | Y | Y | | P1 |
| 3 | `stepprompts/StepPrompts.md` | Y | Y | Y | Y | P1 |
| 4 | `docs/IMPLEMENTATION_GUIDE.md` | Y | Y | Y | Y | P1 |
| 5 | `adr/ADR-033-browser-automation-obscura.md` | | | Y | | P2 |
| 6 | `audit-reports/2026-05-31-implementation-synthesis.md` | Y | Y | Y | | P3 |
| 7 | `audit-reports/2026-05-31-stepprompts-full-audit.md` | Y | Y | Y | Y | P3 |
| 8 | `audit-reports/2026-05-31-stepprompts-fixes-applied.md` | Y | Y | | Y | P3 |
| 9 | `audit-reports/stepprompts-audit/D6-D7-completeness-acceptance.md` | Y | Y | Y | Y | P3 |
| 10 | `audit-reports/stepprompts-audit/D2-D5-adr-dependency.md` | | Y | Y | Y | P3 |
| 11 | `audit-reports/stepprompts-audit/D3-D4-security-sharedvps.md` | Y | Y | Y | Y | P3 |
| 12 | `audit-reports/stepprompts-audit/D9-D10-D11-D12-evidence-persona-loop-memory.md` | Y | Y | Y | Y | P3 |
| 13 | `audit-reports/stepprompts-audit/phase1-fixes-applied.md` | Y | Y | Y | | P3 |
| 14 | `audit-reports/stepprompts-audit/phase2-fixes-applied.md` | Y | Y | | | P3 |
| 15 | `audit-reports/stepprompts-audit/D1-D8-technical-cost.md` | | | | Y | P3 |
| 16 | `audit-reports/P3/P3-FINAL-AUDIT/D07-adr-compliance.md` | Y | Y | Y | | P3 |
| 17 | `audit-reports/P0/STEP-P0-001-auditor-report.md` | | | Y | Y | P3 |
| 18 | `audit-reports/P0/STEP-P0-009/step-p0-009-auditor-report.md` | | Y | | | P4 |
| 19 | `audit-reports/P0/STEP-P0-009/internal-context-report.md` | | Y | | | P4 |
| 20 | `audit-reports/P0/STEP-P0-022/internal-context-report.md` | | Y | | | P4 |
| 21 | `audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md` | | Y | | | P4 |
| 22 | `audit-reports/P0/STEP-P0-018/internal-context-report.md` | | Y | | | P4 |
| 23 | `audit-reports/P0/STEP-P0-013/internal-context-report.md` | | Y | | | P4 |
| 24 | `audit-reports/P0/STEP-P0-012/internal-context-report.md` | | Y | | | P4 |
| 25 | `audit-reports/P0/STEP-P0-011/internal-context-report.md` | | Y | | | P4 |
| 26 | `audit-reports/P0/STEP-P0-016/step-p0-016-auditor-report.md` | Y | | | | P4 |
| 27 | `fixes/2026-05-31-stepprompts-fixes.md` | Y | Y | Y | | P5 |
| 28 | `stepprompts/StepPrompts.md.bak` | Y | Y | Y | Y | Archive |

---

*End of report. Total: 28 files with true phase references, 5 files with false positives (excluded).*
