---
title: "P27 Hermes Society Foundation — Evidence Root"
date: "2026-06-28"
status: "DEFINITION COMPLETE"
phase: "P27"
agent: "Guinevere (parent agent)"
---

# P27 Hermes Society Foundation — Evidence Root

> P27 is a **definition phase** — no source code, no tests, no config, no runtime, no deployment. P27 produces the authoritative Hermes Society Foundation enterprise plan, forward roadmap (P28-P36), executable P28 blueprint, two audit rounds with fixes, and the ADR-054 acceptance.

---

## Overview

P27 establishes the foundation for Hermes Society — a topology where multiple equal autonomous Hermes instances (initially Guinevere + Pharsa) coexist as true peers. P27 covers:

- **Society ontology** (what constitutes a Hermes instance, peer, society)
- **Instance isolation contract** (per-instance config, brain, memory, Discord bot)
- **Hermes Peer Protocol (HPP)** (custom A2A-based envelope + FIPA intent taxonomy)
- **3-scope memory architecture** (private/shared/relationship_private with RLS + intimacy bridge)
- **7-rail life-loop** (macro-state scheduler over P20 heartbeat)
- **4-domain privacy** (Thought/Speech/PeerDialogue/Action)
- **HARD STOP cascade** (global Redis key halts all Society members)
- **P28-P36 roadmap** (9-phase forward plan, 12-15mo critical path)

**Status: DEFINITION COMPLETE.** P28 implementation is a separate phase.

---

## Directory Structure

```
docs/setup-evidence/P27/
├── README.md                                                # This file (index)
├── research/                                                # 10 research files + synthesis
│   ├── p27-ground-truth-repo-state.md
│   ├── p27-p24-fork-dependency-map.md
│   ├── p27-p19-p20-p22-p23-dependency-map.md
│   ├── p27-hermes-native-runtime-inventory.md
│   ├── p27-multi-agent-society-research.md
│   ├── p27-agent-communication-protocol-research.md
│   ├── p27-discord-dual-bot-research.md
│   ├── p27-private-shared-memory-research.md
│   ├── p27-life-loop-beyond-heartbeat-research.md
│   ├── p27-autonomy-safety-audit-research.md
│   └── p27-research-synthesis.md
├── plan/                                                    # 3 plan files
│   ├── p27-hermes-society-foundation-plan.md                # 25 sections, ~4790 lines
│   ├── p27-p28-p36-master-roadmap.md                        # 19 sections, ~1250 lines
│   └── p28-dual-autonomous-hermes-blueprint.md              # 14 sections, ~3000 lines (executable blueprint)
└── evidence/                                                # Phase 9 final + round audits
    ├── p27-verification.md                                  # 12-section verification (AGENTS.md §11)
    ├── p27-auditor-gate.md                                  # Round 1 + Round 2 verdict aggregation
    ├── p27-final-report.md                                  # Executive summary
    ├── p27-round-1-fix-log.md                              # 7 fixes (terminology, schema, docs)
    ├── p27-round-2-fix-log.md                              # 7 fixes (blueprint bugs + consistency)
    └── audits/
        ├── round-1/                                         # 14 audit reports
        │   ├── 01-equal-peer.md                             # NEEDS REVIEW → fixed
        │   ├── 02-sub-agent-rejection.md                    # PASS
        │   ├── 03-memory-isolation.md                       # NEEDS REVIEW → fixed
        │   ├── 04-autonomy.md                               # PASS
        │   ├── 05-discord-dual-bot.md                       # PASS
        │   ├── 06-peer-protocol.md                          # NEEDS REVIEW → fixed
        │   ├── 07-p24-dependency.md                         # PASS
        │   ├── 08-p22-p23-dep.md                            # PASS
        │   ├── 09-safety-boundary-audit.md                  # PASS (re-run from MISSING)
        │   ├── 10-persona-safety.md                         # PASS
        │   ├── 11-roadmap.md                                # NEEDS REVIEW → fixed
        │   ├── 12-evidence.md                               # FAIL → fixed
        │   ├── 13-impl-feasibility.md                       # NEEDS REVIEW → fixed
        │   └── 14-hard-rejection-criteria.md                # PASS (20/20)
        └── round-2/                                         # 6 audit reports
            ├── 01-rail-count-consistency-audit.md           # PASS
            ├── 02-memory-schema-audit.md                    # NEEDS REVIEW → fixed
            ├── 03-hpp-protocol-audit.md                     # FAIL → fixed
            ├── 04-claims-terminology-audit.md               # PASS
            ├── 05-blueprint-bugs-audit.md                   # NEEDS REVIEW → fixed
            └── 06-integration-consistency-audit.md          # NEEDS REVIEW → fixed
```

## File Index

### Research

| File | Purpose |
|---|---|
| `p27-ground-truth-repo-state.md` | Repo state snapshot (P1-P26) for definition grounding |
| `p27-p24-fork-dependency-map.md` | P24 fork dependency analysis |
| `p27-p19-p20-p22-p23-dependency-map.md` | P19/P20/P22/P23 dependency mapping |
| `p27-hermes-native-runtime-inventory.md` | Hermes runtime seam inventory (instance creation) |
| `p27-multi-agent-society-research.md` | Multi-agent framework survey + autonomy topology |
| `p27-agent-communication-protocol-research.md` | A2A / FIPA / MCP / Actor model protocol survey |
| `p27-discord-dual-bot-research.md` | Discord dual-bot feasibility + rate-limit research |
| `p27-private-shared-memory-research.md` | 3-scope memory model + RLS + intimacy bridge research |
| `p27-life-loop-beyond-heartbeat-research.md` | 7-rail life-loop survey + macro-state scheduler patterns |
| `p27-autonomy-safety-audit-research.md` | 4-domain privacy + KILLSWITCH + anti-sycophancy + GAAT |
| `p27-research-synthesis.md` | Synthesis of all 10 research files (parent-read before planner gate) |

### Plan

| File | Sections | Lines | Purpose |
|---|---|---|---|
| `p27-hermes-society-foundation-plan.md` | 25 | ~4790 | Full enterprise plan for Hermes Society Foundation |
| `p27-p28-p36-master-roadmap.md` | 19 | ~1250 | 9-phase forward roadmap with critical path |
| `p28-dual-autonomous-hermes-blueprint.md` | 14 | ~3000 | Executable P28 blueprint (migrations, services, behavior) |

### Evidence (Phase 9 Finalization)

| File | Purpose |
|---|---|
| `p27-verification.md` | 12-section verification per AGENTS.md §11 Evidence Minimum Schema |
| `p27-auditor-gate.md` | Aggregator report for both rounds + final PASS verdict |
| `p27-final-report.md` | Executive summary + 7 architecture decisions + P28-P36 roadmap |
| `p27-round-1-fix-log.md` | Round 1 audit fixes — 7 fixes across 3 plan files |
| `p27-round-2-fix-log.md` | Round 2 audit fixes — 7 fixes across plan + blueprint |

### Audits

#### Round 1 (14)

| # | File | Verdict |
|---|---|---|
| 01 | `01-equal-peer.md` | NEEDS REVIEW (fixed) |
| 02 | `02-sub-agent-rejection.md` | PASS |
| 03 | `03-memory-isolation.md` | NEEDS REVIEW (fixed) |
| 04 | `04-autonomy.md` | PASS |
| 05 | `05-discord-dual-bot.md` | PASS |
| 06 | `06-peer-protocol.md` | NEEDS REVIEW (fixed) |
| 07 | `07-p24-dependency.md` | PASS |
| 08 | `08-p22-p23-dep.md` | PASS |
| 09 | `09-safety-boundary-audit.md` | MISSING → re-run PASS |
| 10 | `10-persona-safety.md` | PASS |
| 11 | `11-roadmap.md` | NEEDS REVIEW (fixed) |
| 12 | `12-evidence.md` | FAIL (fixed) |
| 13 | `13-impl-feasibility.md` | NEEDS REVIEW (fixed) |
| 14 | `14-hard-rejection-criteria.md` | PASS (20/20) |

#### Round 2 (6)

| # | File | Verdict |
|---|---|---|
| 01 | `01-rail-count-consistency-audit.md` | PASS |
| 02 | `02-memory-schema-audit.md` | NEEDS REVIEW (fixed) |
| 03 | `03-hpp-protocol-audit.md` | FAIL (fixed) |
| 04 | `04-claims-terminology-audit.md` | PASS |
| 05 | `05-blueprint-bugs-audit.md` | NEEDS REVIEW (fixed) |
| 06 | `06-integration-consistency-audit.md` | NEEDS REVIEW (fixed) |

### ADR

| File | Status | Purpose |
|---|---|---|
| `adr/ADR-054-p27-hermes-society-foundation.md` | Accepted (2026-06-28) | Canonical ADR for P27 Society Foundation |

---

## Quick Links

- 🎯 **Start here**: `evidence/p27-final-report.md` (executive summary)
- 📜 **The full plan**: `plan/p27-hermes-society-foundation-plan.md`
- 🛣️ **Forward roadmap**: `plan/p27-p28-p36-master-roadmap.md`
- 🏗️ **P28 executable blueprint**: `plan/p28-dual-autonomous-hermes-blueprint.md`
- ✅ **Verification**: `evidence/p27-verification.md`
- 🎓 **Auditor gate**: `evidence/p27-auditor-gate.md`
- 🔧 **Round-1 fixes**: `evidence/p27-round-1-fix-log.md`
- 🔧 **Round-2 fixes**: `evidence/p27-round-2-fix-log.md`
- 📑 **ADR**: `adr/ADR-054-p27-hermes-society-foundation.md`

---

## Status

**DEFINITION COMPLETE — awaiting P28 implementation kickoff.**

| Field | Value |
|---|---|
| Phase | P27 |
| Type | DEFINITION ONLY — no runtime implementation |
| Total files | 37 (10 research + 1 synthesis + 3 plan + 4 evidence + 2 fix logs + 14 + 6 audits + 1 README + 1 ADR) |
| Audit rounds | 2 (Round 1: 14, Round 2: 6) |
| Total audits | 20 |
| Verdicts (Round 1) | 7 PASS + 5 NEEDS REVIEW (fixed) + 1 FAIL (fixed) + 1 MISSING (re-run PASS) |
| Verdicts (Round 2) | 2 PASS + 3 NEEDS REVIEW (fixed) + 1 FAIL (fixed) |
| Hard rejection criteria | 20 / 20 PASS |
| Auditor gate final verdict | **PASS** |
| ADR | ADR-054 Accepted (2026-06-28) |
| Operator | Faiz |
| Date | 2026-06-28 |
| Next phase | P28 — Dual Autonomous Hermes (separate phase, its own plan + audit) |

---

## Maintenance

This README is canonical for the P27 evidence root. Update only when:

- New files are added to the P27 evidence root
- Status changes (e.g., P28 inherits from P27)
- ADR status changes

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial P27 evidence root index |

### Operator Sign-Off

Approved by Faiz via session instruction to finalize P27 evidence files and indexes. P27 evidence root is **frozen** until P28 implementation begins consuming it.

---

> **Done.** P27 is documented, audited twice, fixed twice, and accepted via ADR-054. Society is defined.
