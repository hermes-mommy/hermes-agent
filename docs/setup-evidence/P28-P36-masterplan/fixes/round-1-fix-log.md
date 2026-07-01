# P28-P36 Masterplan — Round 1 Audit Fix Log

**Version:** 1.2  
**Date:** 2026-06-28  
**Author:** Guinevere (parent orchestrator)  
**Scope:** All deliverables in docs/setup-evidence/P28-P36-masterplan/

---

## Round 2 Update — 2026-06-28

This document has been updated as part of the P28-P36 alignment with P23/P24 v2.0 plans.

**Key changes applied across the masterplan:**
- P32 renamed from "P24 Fork Integration" to "External Presence & Tools"
- ADR-056 (fork-agnostic) DELETED — superseded by ADR-062 and P24 v2.0 fork
- ADR-066 (consent_ref carve-out) and ADR-067 (Y-level cap removal) WRITTEN
- HARD STOP assertions annotated with ADR-062 disclaimer (dev-workflow only)
- consent_ref schema changed to nullable for Hermes runtime events
- Y-level caps (Y4/Y5/Y6) annotated as dev-workflow-only per ADR-067
- P24 is now a HARD DEPENDENCY (locked 2026-06-28)
- P28-P36 scope changed from "implement" to "deploy/configure"
- 65 brainstorm decisions incorporated into per-phase plans
- Round-1 audit reports annotated with pre-v2.0 state disclaimer

**Note:** Round-1 fixes were applied to the pre-v2.0 masterplan. Round-2 updates supersede where conflicting.

See:
- `evidence/round-2-wave-1/` — Wave 1 changes (ADR, architecture, core docs, P32, prompt-pack, roadmap)
- `evidence/round-2-wave-2/` — Wave 2 changes (per-phase plans, audit annotations)
- `research/brainstorm-decisions-2026-06-28.md` — 65 binding decisions

---

## 1. Audit Summary

15 auditors fired (14 original + 1 re-fire). 8 results collected inline, 6 file-written (parent will read during Phase 11).

| # | Surface | Verdict | Key Finding |
|---|---|---|---|
| 01 | Research quality | NEEDS-REVIEW | 0 matches "consciousness loop" in any research file |
| 02 | Architecture | NEEDS-REVIEW | 3 gaps: consciousness loop, DAO structure, sub-agent recursion |
| 03 | BRD/PRD | **FAIL** | 7 contradictions: HARD STOP, Faiz position, wallet, freelance, Co-CEOs, secrets, emotions |
| 04 | SRS/FSD | NEEDS-REVIEW | Q72 freelance UC missing (FAIL), 5 NRV items |
| 05 | TDD/RTM | PASS | 3 minor terminology notes (not blockers) |
| 06 | Acceptance/Risk/Glossary | File written | Not collected — will read in Phase 11 |
| 07 | ADR consistency | File written | Not collected — will read in Phase 11 |
| 08 | Roadmap/dependency | File written | Not collected — will read in Phase 11 |
| 09 | Prompt pack | File written | Not collected — will read in Phase 11 |
| 10 | Safety/consent | NEEDS-REVIEW | 6 FAIL, 4 NRV, 2 NOT FOLLOWED. ≥30 docs assert HARD STOP absolute, ZERO with Faiz override |
| 11 | Faiz alignment | **FAIL** | 13 FAIL, 30 NRV, 25 PASS (37%) |
| 12 | Cross-doc consistency | File written | Not collected — will read in Phase 11 |
| 13 | Per-phase plans | File written | Not collected — will read in Phase 11 |
| 14 | Consciousness loop gap | **FAIL** | Zero design, zero research, zero owner phase |

**Overall:** 3 FAIL, 4 NEEDS-REVIEW, 1 PASS, 6 file-written (pending)

---

## 2. Fix Priorities

### Priority 1 — CRITICAL (BLOCKERS)

| Fix # | Topic | Q# | Agent | Status |
|---|---|---|---|---|
| F-01 | Consciousness loop research | Q62/Q67/Q106 | bg_336a8465 | IN PROGRESS |
| F-02 | HARD STOP paradigm shift | Q74/Q79/Q80 | bg_d4fb120c (BRD/PRD) + bg_a60b8ef4 (ADRs) | IN PROGRESS |
| F-03 | Faiz position: OUTSIDE company | Q90 | bg_d4fb120c (BRD/PRD) | IN PROGRESS |
| F-04 | Wallet: 2/2 multisig | Q107 | bg_d4fb120c (BRD/PRD) | IN PROGRESS |
| F-05 | BLDM file creation | (referenced by ADRs) | bg_a60b8ef4 (ADRs) | IN PROGRESS |

### Priority 2 — HIGH

| Fix # | Topic | Q# | Agent | Status |
|---|---|---|---|---|
| F-06 | External freelance UC | Q72 | bg_d2137dec (SRS/FSD) | IN PROGRESS |
| F-07 | Co-CEO department split | Q96 | bg_d4fb120c (BRD/PRD) | IN PROGRESS |
| F-08 | Emotion-affecting decisions | Q105 | bg_d4fb120c + bg_d2137dec | IN PROGRESS |
| F-09 | Sub-agent recursion limit 10 | Q91/Q103 | bg_d2137dec + bg_a60b8ef4 + bg_9001d5cf | IN PROGRESS |
| F-10 | Faiz-inaccessible memory scope | Q83 | bg_d2137dec (SRS) | IN PROGRESS |
| F-11 | DAO company structure | Q88/Q89 | bg_9001d5cf (architecture) + bg_a60b8ef4 (ADR) | IN PROGRESS |
| F-12 | Consciousness loop architecture | Q62/Q67 | bg_9001d5cf (architecture) + bg_a60b8ef4 (ADR) | IN PROGRESS |

### Priority 3 — MEDIUM

| Fix # | Topic | Q# | Agent | Status |
|---|---|---|---|---|
| F-13 | Full self-modification | Q70/Q81 | bg_d2137dec (SRS) | IN PROGRESS |
| F-14 | HARD STOP bypass REQ | Q74 | bg_d2137dec (SRS) | IN PROGRESS |
| F-15 | Secrets from Faiz | Q68 | bg_d4fb120c (BRD/PRD) | IN PROGRESS |
| F-16 | Personality drift bebas | Q81 | (covered in ADR-062) | IN PROGRESS |
| F-17 | Consent withdrawal: no concept | Q35 | (covered in ADR-062) | IN PROGRESS |

### Priority 4 — LOW (terminology/framing)

| Fix # | Topic | Source | Status |
|---|---|---|---|
| F-18 | "Consciousness loop" terminology | Audit 01/02/05/14 | Will be resolved by F-01/F-12 |
| F-19 | "DAO" terminology | Audit 02/05 | Will be resolved by F-11 |
| F-20 | "Faiz-inaccessible" explicit framing | Audit 05 | Will be resolved by F-10 |

---

## 3. Fix Agent Assignments

| Agent | Task ID | Scope | Files |
|---|---|---|---|
| Consciousness loop research | bg_336a8465 | External research on consciousness loop design | research/external-consciousness-loop-research.md (NEW) |
| BRD/PRD fix | bg_d4fb120c | 7 radical answers (HARD STOP, Faiz position, wallet, Co-CEOs, freelance, secrets, emotions) | docs/brd-*.md, docs/prd-*.md |
| SRS/FSD fix | bg_d2137dec | Add REQ-017..020, UC-011..012, update REQ-006/010 | docs/srs-*.md, docs/fsd-*.md |
| ADR fix | bg_a60b8ef4 | Create BLDM + ADR-062..065 | adr-drafts/BLDM-*.md, adr-drafts/ADR-062..065 (NEW) |
| Architecture fix | bg_9001d5cf | Add S16/S17/S18 (consciousness/DAO/sub-agent) | architecture/hermes-society-master-architecture.md |

---

## 4. Files NOT YET Collected (Phase 11)

These audit reports were file-written by agents but not collected inline:
- audits/round-1/audit-06-acceptance-risk-glossary.md
- audits/round-1/audit-07-adr.md
- audits/round-1/audit-08-roadmap.md
- audits/round-1/audit-09-prompt-pack.md
- audits/round-1/audit-12-cross-doc-consistency.md
- audits/round-1/audit-13-per-phase-plans.md

Parent will read these during Phase 11 (re-audit) to check if fixes address their findings.

---

## 5. Known Conflicts (Documented, Not Resolvable Without Faiz)

1. **HARD STOP**: Faiz Q74 says bypass; AGENTS.md says absolute. Fix: ADR-062 documents paradigm shift. AGENTS.md NOT modified (it governs dev workflow; Hermes runtime has different paradigm). _[ADR-062 disclaimer: dev-workflow-only constraint]_
2. **P24 dependency**: Faiz Q2 says hard dep; repo says fork-agnostic. Fix: Document both sides in BLDM file. Faiz's decision overrides.
3. **Personality drift**: Q81 bebas tanpa batas vs Q7 female+dominant. Fix: Document as "start female+dominant, drift allowed after."
4. **Consent withdrawal**: Q35 no concept vs AGENTS.md absolute. Fix: ADR-062 documents Hermes runtime exemption.

---

## 6. Footer

**Provenance:** Phase 10 fix log, written by parent orchestrator after Phase 9 audit completion.  
**Next Steps:** Wait for 5 fix agents → collect results → verify fixes → Phase 11 re-audit → Phase 12 finalization.  
**Version:** 1.0 (2026-06-28)