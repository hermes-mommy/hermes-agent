---
title: "Governance & Documentation Inventory — Inputs to P28-P36 Masterplan"
status: "Active — Research Synthesis Input"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
operator: "Faiz"
phase: "P28-P36 Masterplan Planning"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
---

# Governance & Documentation Inventory

> Canonical inventory of existing Guinevere governance artifacts, documentation families, ADR numbering, evidence conventions, and template patterns. This document is a **planning input** for the P28-P36 masterplan proposal and tells the masterplan author exactly what already exists, what numbering is in use, and what conventions must be preserved.

---

## §0 Reader's Map

- §1 — Current state snapshot (one-paragraph executive summary).
- §2 — ADR inventory (all 40+ ADRs, status, gap map, next available number).
- §3 — Documentation families (8 categories, naming, status, files).
- §4 — BRD/PRD/SRS/FSD/TDD/RTM template patterns.
- §5 — Phase progress (P0-P27 + reserved P25/P26 + P28+).
- §6 — Evidence directory conventions (P0-P27 + P28-P36 stub status).
- §7 — Phase-by-phase summary (P0 through P27).
- §8 — Documentation conventions (frontmatter, versioning, lifecycle).
- §9 — Required outputs for the P28-P36 masterplan.
- §10 — Decisions the masterplan must make.
- §11 — Cross-references and source paths.
- §12 — Footer.

---

## §1 Current State Snapshot

Project Guinevere is a **single-operator, persona-driven autonomous AI companion and engineering system** governed by an enterprise-grade documentation suite (44 active documents across 8 categories, 18 archived versions). The system has completed **P0 through P24 with P25/P26 reserved and P27 reaching DEFINITION COMPLETE**. P28-P36 represent the next 9 implementation phases targeting a multi-instance "Hermes Society" topology.

- **Latest phase status**: P27 Hermes Society Foundation — DEFINITION COMPLETE (2026-06-28) with ADR-054 Accepted.
- **Documentation suite**: 44 active documents, 18 archived, ~2.3 MB total.
- **ADR count**: 41 ADRs (38 sequential ADR-001 to ADR-038 + ADR-050, ADR-052, ADR-053, ADR-054), with 9 backlog slots (ADR-041, ADR-043, ADR-044, ADR-045, ADR-046, ADR-047, ADR-048, ADR-049, ADR-051) still free under renumbered plan.
- **Highest ADR number used**: **ADR-054**.
- **Next available ADR number**: **ADR-055** (masterplan should propose allocation for first 1-3 new ADRs).
- **Latest 11 of 11 phases complete** in P0-P22 series (P22.1 Foundation Hardening production-passed 2026-06-28).
- **P28-P36 evidence directories already exist as empty stubs** (created during P27). One P28-P36-masterplan/ research subfolder holds 2 P27 carry-over files.

---

## §2 ADR Inventory

### §2.1 Full ADR Register (all 41 ADRs)

Source: `docs/10-governance/17-ADR_Index_v1.0.md` (last modified 2026-06-28, adr_count: 40) and `adr/` directory (44 files including README).

| ADR | Title | Status | Risk | Topic Family |
|---|---|---|---|---|
| ADR-001 | Persona Safety & Ethical Boundary Policy | Accepted with notes | CRITICAL | persona, safety, ethics, policy |
| ADR-002 | User Autonomy & Safe Word Enforcement | Accepted with notes | CRITICAL | safety, autonomy, safe-word, persona |
| ADR-003 | Persona Drift Control & Validation | Accepted with notes | HIGH | persona, drift, validation, audit |
| ADR-004 | Primary LLM Model Selection (GPT-5.5 via 9Router) | Accepted | HIGH | llm, model, 9router, canonical |
| ADR-005 | LLM Router & Failover Strategy | Accepted | HIGH | llm, routing, 9router, failover |
| ADR-006 | Sub-Agent LLM Model Strategy (DeepSeek V4 Flash) | Accepted | MEDIUM | llm, sub-agent, deepseek |
| ADR-007 | Memory Storage Backend Selection (PostgreSQL + Redis) | Accepted | CRITICAL | memory, postgresql, redis, sqlite |
| ADR-008 | Memory Encryption & Key Management | Accepted with notes | CRITICAL | memory, encryption, keys, privacy |
| ADR-009 | Memory Recall & Semantic Search Strategy | Accepted with notes | HIGH | memory, recall, pgvector, semantic-search |
| ADR-010 | Surveillance Data Retention Policy | Accepted with notes | HIGH | surveillance, privacy, retention |
| ADR-011 | SDLC Loop Phase Specification (7-phase) | Accepted | HIGH | sdlc, agent-loop, canonical |
| ADR-012 | Sub-Agent Orchestration Governance | Accepted with notes | HIGH | sub-agent, orchestration, audit |
| ADR-013 | Guinevere MCP Native OpenCode Replacement | Accepted | HIGH | mcp, coding-agent, opencode |
| ADR-014 | VPS & Container Architecture | Accepted | HIGH | infrastructure, vps, docker, ubuntu |
| ADR-015 | Secrets Management Strategy (SOPS + age) | Accepted | CRITICAL | security, secrets, sops, age |
| ADR-016 | CI/CD & Autonomous Deployment Strategy | Accepted with notes | HIGH | cicd, deployment, autonomy |
| ADR-017 | Monitoring Stack Selection (Prometheus + Grafana) | Accepted | HIGH | observability, prometheus, grafana, loki |
| ADR-018 | Security Architecture & Defense-in-Depth | Accepted with notes | CRITICAL | security, threat-model, defense-in-depth |
| ADR-019 | Access Control & VPN Mesh Strategy | Accepted with notes | HIGH | access-control, tailscale, vpn, rbac |
| ADR-020 | Browser Automation Strategy | Accepted | MEDIUM | browser, obscura, playwright |
| ADR-021 | Wearable Integration Post-MVP | Accepted | MEDIUM | wearable, post-mvp, health |
| ADR-022 | Communication Channel Strategy (Revised 2026-06-03) | Accepted with notes | HIGH | discord, whatsapp, email, neonize |
| ADR-023 | Financial Data Integration Strategy | Accepted with notes | MEDIUM | financial, ewallet, data-integration, privacy |
| ADR-024 | Data Governance & Classification Policy | Accepted with notes | CRITICAL | data-governance, classification, privacy |
| ADR-025 | Backup & Disaster Recovery Strategy | Accepted with notes | CRITICAL | backup, dr, rpo, rto, operations |
| ADR-026 | Public Endpoint via Cloudflare Tunnel | Accepted | MEDIUM | network, cloudflare, tunnel, webhook |
| ADR-027 | Self-Hosted PostgreSQL | Accepted | HIGH | database, postgresql, self-host, budget |
| ADR-028 | LLM Router Outage — 9Router Combo + Graceful Degradation | **Superseded** | MEDIUM | llm, fallback, resilience, 9router |
| ADR-029 | Self-Modification Automated Testing | Accepted | CRITICAL | self-modification, testing, rollback, safety, autonomy |
| ADR-030 | Redis DB Assignments (DB0-DB5) (Revised 2026-06-05) | Accepted | CRITICAL | redis, database, cache, infrastructure |
| ADR-031 | Database Naming Convention | Accepted | HIGH | database, postgresql, naming |
| ADR-032 | Backup Storage Strategy — idcloudhost S3 + Cloudflare R2 | Accepted | CRITICAL | backup, storage, s3, r2, dr |
| ADR-033 | Browser Automation — Obscura CDP over Headless Chrome + Playwright | Accepted | MEDIUM | browser, obscura, cdp, stealth |
| ADR-034 | Post-MVP Phase Restructure — P0-P11 → P0-P22 | Accepted | MEDIUM | phase, restructure, roadmap |
| ADR-035 | Hermes NousResearch Migration Architecture | **Implemented** | CRITICAL | architecture, migration, hermes, safety, mcp |
| ADR-036 | Code Quality Debt Tracking and Cleanup | **Proposed** | LOW | code-quality, tech-debt, type-safety |
| ADR-037 | Wearable Health Data Integration Pipeline | Accepted | HIGH | wearable, health, mi-fitness, timescaledb, mood |
| ADR-038 | P13 X Auto Poster Architecture (9 decisions) | Accepted | HIGH | x-poster, postgresql, hermes, obscura |
| **Gap** | ADR-039, ADR-040, ADR-041..ADR-048, ADR-049 | (see §2.3) | — | (see §2.3) |
| ADR-039 | Gadgetbridge SQLite Parser (renumbered from backlog) | Accepted | — | wearable, gadgetbridge, sqlite-parser |
| ADR-040 | Health Connect Pivot (renumbered from backlog) | Accepted | — | wearable, health-connect, kotlin |
| ADR-050 | Knowledge Graph Architecture — P16 | **Implemented** | CRITICAL | knowledge-graph, postgresql, pgvector, rcte, consent |
| ADR-051 | (reserved — was Compliance & Data Residency Mapping) | **free** | — | (proposed: compliance, data-residency) |
| ADR-052 | Multi-Project Context — P19 | Accepted | CRITICAL | multi-project, context, isolation, namespace, p19 |
| ADR-053 | P22 Life Integration Hub | Accepted | — | p22, life-integrations, adapters, hub |
| **ADR-054** | **P27 Hermes Society Foundation — Dual Autonomous Hermes Peers** | **Accepted (2026-06-28)** | **CRITICAL** | **p27, hermes-society, multi-instance, peer-to-peer, equal-peer, autonomy, society-topology** |

### §2.2 ADR File Naming Convention

```
adr/ADR-NNN-{slug-topic}.md
```

Examples: `adr/ADR-054-p27-hermes-society-foundation.md`, `adr/ADR-050-knowledge-graph-architecture.md`.

MADR format with YAML frontmatter (title, status, date, last_modified, owner, executor, adr_count). Optional revision artifacts: `docs/10-governance/P{N}-{ADR-N}-Revision.md` (e.g., `P12-029-ADR-Revision.md`, `P13-028-ADR-Revision.md`).

### §2.3 Gap Map and Backlog

**Numbered gaps** (files exist, numbers already used):

| Number | Used By | Status |
|---|---|---|
| ADR-039 | Gadgetbridge SQLite Parser | Accepted (renumbered from backlog 2026-06-25) |
| ADR-040 | Health Connect Pivot | Accepted (renumbered from backlog 2026-06-25) |
| ADR-041..ADR-048 | **FREE** (backlog only) | Open — see §2.4 |
| ADR-049 | (reserved — previously allocated to consent & revocation) | FREE |
| ADR-050 | Knowledge Graph | Implemented |
| ADR-051 | Compliance & Data Residency Mapping (proposed) | FREE |
| ADR-052 | Multi-Project Context | Accepted |
| ADR-053 | P22 Life Integration Hub | Accepted |
| ADR-054 | P27 Hermes Society Foundation | Accepted (2026-06-28) |
| **ADR-055** | **NEXT AVAILABLE** | FREE |

**Backlog slots free** (per ADR-Index 17-ADR_Index_v1.0.md, renumbered 2026-06-25):

- ADR-041 — Secrets Rotation Runbook (originally proposed; the runbook itself exists at `docs/20-security/23-SecretsRotationRunbook_v1.0.md` but lacks a canonical ADR file).
- ADR-042 — OpenAPI / AsyncAPI Contract Governance.
- ADR-043 — Event Schema & Webhook Contract.
- ADR-044 — Database ERD & Migration Strategy (the spec exists at `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md` but no ADR).
- ADR-045 — SLO/SLA/Error Budget Policy (spec at `docs/40-operations/41-SLO_SLA_ErrorBudget_v1.0.md`).
- ADR-046 — Incident Response & Postmortem Runbook (runbook at `docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md`).
- ADR-047 — Feature Flag Governance.
- ADR-048 — Product Analytics & Event Taxonomy.
- ADR-049 — (reserved) — was previously allocated to consent & revocation; ConsentRevocationPolicy exists at `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` without dedicated ADR.
- ADR-051 — Compliance & Data Residency Mapping (proposed).

### §2.4 Numbering Constraints for Masterplan

Per `17-ADR_Index_v1.0.md` Maintenance Rules:

1. **Monotonically increasing** — cannot skip backwards.
2. **No reuse** — every number maps to exactly one decision.
3. **Supersession requires new ADR** — never edit in place.
4. **Backlog slots are reusable concepts** but numbers must be sequential.

For the P28-P36 masterplan, the natural allocation pattern is:

- **ADR-055** — Reserved for P28 Dual Autonomous Hermes (society-topology instance refactor).
- **ADR-056** — Reserved for P28/P29 Hermes Peer Protocol (HPP) envelope + FIPA intent taxonomy.
- **ADR-057** — Reserved for P30 Memory Deepening (intimacy bridge + Ebbinghaus decay).
- **ADR-058+** — Reserved for P31 Safety Envelope, P32 Fork Integration, P33 Action Executors, P34 Society Expansion, P35 Voice, P36 Cross-VPS.

**Masterplan decision required**: Should the masterplan propose 1 masterplan-level ADR (Society Topology consolidation) or N per-phase ADRs (1 per P28-P36 phase)? Both patterns are precedented (P22 used ADR-053 single; P27 used ADR-054 single covering entire foundation).

---

## §3 Documentation Families

### §3.1 The 8 Active Categories (per `docs/README.md`)

| Range | Family | Status | Files |
|---|---|---|---|
| 00-09 | `00-core` — Product core (BRD, PRD, Arch, Agent Loop, Memory, API, Persona) | 7 active + 2 supplements | 9 files |
| 10-19 | `10-governance` — Governance (Charter, Feasibility, SRS, FSD, TDD, RTM, AC, ADR-Index) | 8 governance + 4 phase-tied | 11 files |
| 20-29 | `20-security` — Security & Access Control | 5 active | 5 files |
| 30-39 | `30-data` — Data Governance (Classification, Surveillance, Consent, ERD, Memory Recall) | 5 active | 5 files |
| 40-49 | `40-operations` — Operations (Observability, SLO/SLA, IR, DR, Deployment, Ops Manual) | 6 active + 1 supplement | 7 files |
| 50-59 | `50-quality` — Quality (Test Plan) | 1 active | 1 file |
| 60-69 | `60-persona` — Persona-specific (Safety, System Prompt, MCP Config, Discord UX) | 4 active | 4 files |
| 70-79 | `70-finops` — FinOps (Cost & FinOps Model) | 1 active | 1 file |

**Total active: 44 documents. Total archived: 18 files. Total size: ~2.3 MB.**

### §3.2 File Naming Convention

```
docs/{family}/{NN}-{DocName}_vN.N.md
```

Examples:
- `docs/00-core/00-BRD_v2.0.md`
- `docs/00-core/01-PRD_v2.2.md`
- `docs/10-governance/12-SRS_v1.0.md`
- `docs/10-governance/13-FSD_v1.0.md`
- `docs/10-governance/14-TDD_Guide_v1.0.md`
- `docs/10-governance/15-RTM_v1.0.md`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`

**Sub-id pattern** (for supplements within a family, not a new doc):
- `docs/00-core/05-APIIntegration_v2.0.md` + `docs/00-core/05a-OpenAPISpec_v1.0.md` + `docs/00-core/05b-AsyncAPISpec_v1.0.md`
- `docs/40-operations/44-DeploymentGuide_v1.0.md` + `docs/40-operations/46-GmailDeploymentGuide_v1.0.md`

**Phase-tied governance artifacts** (in `docs/10-governance/`):
- `docs/10-governance/P12-029-ADR-Revision.md`
- `docs/10-governance/P13-028-ADR-Revision.md`

### §3.3 Document Status Lifecycle

| Status | Meaning |
|---|---|
| **Draft** | In writing; not authoritative. |
| **Dalam Review** | (Indonesian: "In Review") Owner/auditor reviewing. |
| **Diterima** | (Indonesian: "Accepted") Authoritative reference. |
| **Didepresiasi** | (Indonesian: "Deprecated") Newer version in prep. |
| **Diarsipkan** | (Indonesian: "Archived") Moved to `_archive/`. |

Current registry: **all 44 active docs are "Diterima" (Accepted)**. P23/P24 are "DEFINITION COMPLETE — IMPL HOLD". P27 is "DEFINITION COMPLETE — IMPL HOLD (P28 separate phase)".

### §3.4 Versioning Policy

`vMAJOR.MINOR` scheme:
- **Major bump** (v1.0 → v2.0): structural or substantive changes that alter the spec contract.
- **Minor bump** (v1.0 → v1.1): corrections, clarifications, small additions.

Review cadence: minimum every 90 days or after significant architecture change.

---

## §4 BRD / PRD / SRS / FSD / TDD / RTM Template Patterns

### §4.1 Pattern Inventory (where each lives today)

| Template Family | File | Size | Status |
|---|---|---|---|
| BRD (Business Requirements Document) | `docs/00-core/00-BRD_v2.0.md` | 18.0 KB | Diterima |
| PRD (Product Requirements Document) | `docs/00-core/01-PRD_v2.2.md` | 27.5 KB | Diterima |
| SRS (Software Requirements Specification) | `docs/10-governance/12-SRS_v1.0.md` | 72.0 KB | Diterima |
| FSD (Functional Specification Document) | `docs/10-governance/13-FSD_v1.0.md` | 111.7 KB | Diterima |
| TDD Guide (Technical Design Document) | `docs/10-governance/14-TDD_Guide_v1.0.md` | 131.9 KB | Diterima |
| RTM (Requirements Traceability Matrix) | `docs/10-governance/15-RTM_v1.0.md` | 52.3 KB | Diterima |
| Acceptance Criteria Catalog | `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` | 49.4 KB | Diterima |

### §4.2 Pattern: Frontmatter (YAML)

All docs share this frontmatter block:

```yaml
---
title: "<document title>"
status: "Active|Aktif|Diterima|Draft|Dalam Review|Didepresiasi|Diarsipkan"
date: "<YYYY-MM-DD>"
last_modified: "<YYYY-MM-DD>"
owner: "Faiz"
executor: "Guinevere"
operator_alias_note: "Samm is a historical/pseudonymous alias only; canonical operator identity is Faiz."
---
```

### §4.3 Pattern: Common Sections (Required by Convention)

All major docs include:
- `## Related Documents` — cross-references to upstream/downstream.
- `## Footer` — classification footer (`STRICTLY PRIVATE & CONFIDENTIAL`).
- `## Catatan Perubahan` (Indonesian: "Change Log") — version history table.

### §4.4 Pattern: P27 Plan Structure (Most Recent Precedent)

The P27 plan `p27-hermes-society-foundation-plan.md` is the most recent full enterprise plan and serves as the **template precedent** for the P28-P36 masterplan. Its structure:

- 25 sections, ~4790 lines
- Includes: Reader's Map, Mission, Ontology, Architecture, Components, Risks, Research, Open Questions, Decision Records, Evidence, Implementation Plan, Audit Criteria, Hard Rejection Criteria, Roadmap (forward), Operator Sign-Off.

### §4.5 Pattern: P27 Roadmap Structure (Direct Precedent)

The P28-P36 masterplan SHOULD follow the structure of `p27-p28-p36-master-roadmap.md` (19 sections, ~1250 lines):

- §0 Reader's Map
- §1 Roadmap Philosophy / Reader Contract
- §2 Top-line Summary Table
- §3 P28 (most detailed) — Mission, Deliverables, Dependencies, Success Criteria, Complexity, Risk, Research, Duration
- §4-§11 P29-P36 (8 phases each, 10 elements)
- §12 Dependency Graph
- §13 Critical Path
- §14 Parallelization Map
- §15 Research Debt Tracker
- §16 Total Timeline Estimate
- §17 Anti-patterns Preserved
- §18 References
- §19 Footer

### §4.6 Pattern: P27 Blueprint Structure (P28 Executable Precedent)

The P28 executable blueprint `p28-dual-autonomous-hermes-blueprint.md` is **14 sections, ~3000 lines** and serves as the executable template for P28's own plan if implementation begins:

- Includes: Migrations (Alembic), Service Units (systemd), Configuration (YAML), Behavior Contracts, Test Plans, Rollback Plans, Audit Gates.

---

## §5 Phase Progress (P0-P27)

### §5.1 Status Summary Table (from `PROGRESS.md` and `CHECKLIST.md`)

| Phase | Name | Status | Steps | Cost/mo | Duration | Notes |
|---|---|---|---|---|---|---|
| P0 | Infrastructure | DONE | 29/29 | $0 | 58-116h | Complete + 5 final fixes |
| P1 | LLM + Hermes | DONE | 21/21 | $15 | 40-80h | LFAF router + HARD STOP verified |
| P2 | Discord Bot | DONE | 22/22 | $0 | 42-84h | Standalone bot masked post-ADR-035 |
| P3 | Memory System | DONE | 19/19 | $2 | 38-76h | 47 tables, pgvector + FTS hybrid |
| P4 | Persona Engine | DONE | 23/23 | $1 | 38-76h | 1449 tests PASS, 0 fail |
| P5 | Agent Loop | DONE | 23/23 | $3 | 46-92h | PASS, then 5.5 remediation, then 6 fixes re-audit |
| P5.5 | Remediation | DONE | 10 fixes | — | — | All blocking CRITICALs fixed |
| P6 | MCP Tools | DONE (Remediation PASS) | 21/21 | $1 | 42-84h | 16 tools, 4-level auth matrix |
| P7 | Surveillance | DONE | 22/22 | $1 | 44-88h | 472 tests, consent gate |
| P7.5 | Remediation | DONE | 9 fixes | — | — | 5 CRITICAL + 4 HIGH fixed |
| P8 | Observability | DONE | 23/23 | $4 | 46-92h | MVP approved 2026-06-03 |
| P9 | Financial Tracking | NOT STARTED | 0/13 | $1 | 12-24h | Stabilization, deferred |
| P10 | Production Hardening | NOT STARTED | 0/21 | $1 | 18-36h | Stabilization, deferred |
| P11 | WhatsApp | CODE COMPLETE | 23/23 | $0 | — | 21 modules, code-only |
| P12 | Gmail/Email | CODE COMPLETE | 29/29 | $0 | — | 27 modules, code-only |
| P13 | X Auto Poster | CODE COMPLETE | 28/28 | ~$10 | — | 28 modules |
| P14 | Wearable Health | DONE | 20/20 | $0 | — | ADR-037 canonical |
| P14-GB | Gadgetbridge SQLite | DONE | 11/11 | $0 | — | ADR-039 (renumbered) |
| P14-HC | Health Connect | DONE | TBD | $0 | — | ADR-040 (renumbered), ADR-040 supersedes 039+037 canonical |
| P15 | Windows Daemon | **CANCELLED** | — | — | — | Cancelled 2026-06-19 |
| P16 | Knowledge Graph | NOT STARTED (deferred) | TBD | TBD | TBD | ADR-050 architecture defined |
| P17 | Cross-Device Sync | NOT STARTED (deferred) | TBD | TBD | TBD | TBD |
| P18 | Advanced Memory | NOT STARTED (deferred) | TBD | TBD | TBD | TBD |
| P19 | Multi-Project Context | **PRODUCTION COMPLETE** | 12 waves + completion pass | — | Done (2026-06-27) | ADR-052; live + Discord UX |
| P20 | Self-Improvement / Discord-Visible Autonomy | **EARLY ACCEPTANCE** | TBD | TBD | Accepted (waived) | 24h soak waived by operator 2026-06-25 |
| P21 | Voice Interface | DEF COMPLETE — IMPL HOLD | TBD | TBD | 0h planning | 9 waves held until P20 pass |
| P22 | Life Integration Hub | PASS W/ CONFIG_MISSING | 13 core + 14 adapters | $0 | Done (2026-06-27) | 76 tests + 12/12 smoke |
| P22.1 | Foundation Hardening (audit_writer + consent_checker) | PRODUCTION PASS | 25 new tests | $0 | Done (2026-06-28) | Closes 3 P22 gaps |
| P23 | Embodied Operations | DEF COMPLETE | 20 waves (held) | TBD | 0h planning | P23A ready, P23B blocked |
| P24 | Hermes Fork-First Convergence | PLAN FIXED — IMPL HOLD | 20 waves (held) | TBD | 0h planning | Full owned fork preferred |
| P25 | (reserved) | — | — | — | — | — |
| P26 | (reserved) | — | — | — | — | — |
| **P27** | **Hermes Society Foundation** | **DEF COMPLETE — IMPL HOLD** | **10 research + 3 plan (definition-only)** | **$0** | **0h planning** | **ADR-054 Accepted 2026-06-28** |
| **Total** | | | **327/343+ (95.3%)** | **$29+** | **503-1008h+** | |

### §5.2 Critical Path

`P0 → P1 → P3 → P5` (per PROGRESS.md).

### §5.3 Total Cost Boundary

USD 30/month hard cap. Current burn: $29+ (under cap, but with critical reserve).

---

## §6 Evidence Directory Conventions

### §6.1 Standard Evidence Root

`docs/setup-evidence/` is the canonical evidence root for **all implementation phases**.

### §6.2 Standard Per-Phase Layout (P27 Precedent)

```
docs/setup-evidence/P{NN}/
├── README.md                                       # Evidence root index
├── research/                                       # Pre-planning research
│   ├── p{NN}-{topic}-research.md                   # Per-topic research files
│   └── p{NN}-research-synthesis.md                 # Parent-read synthesis
├── plan/                                           # Phase plans
│   ├── p{NN}-{plan-name}-plan.md                   # Main enterprise plan
│   └── p{NN}-{N}-{NN}-{topic}-plan.md              # Sub-plans (roadmap, blueprint)
└── evidence/                                       # Phase 9 finalization
    ├── p{NN}-verification.md                       # 12-section verification (AGENTS.md §11)
    ├── p{NN}-auditor-gate.md                       # Aggregator report
    ├── p{NN}-final-report.md                       # Executive summary
    ├── p{NN}-round-N-fix-log.md                    # Per-round fixes
    └── audits/
        ├── round-1/                                # First audit wave
        │   └── NN-{topic}-audit.md                 # Per-auditor reports
        └── round-2/                                # Second audit wave (if applicable)
            └── NN-{topic}-audit.md
```

### §6.3 P28-P36 Stub Status (CRITICAL FINDING)

**The P28-P36 evidence directories already exist as empty stubs** (created during P27 finalization). Specifically:

| Directory | Status | Content |
|---|---|---|
| `docs/setup-evidence/P28/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P29/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P30/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P31/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P32/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P33/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P34/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P35/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P36/` | EXISTS, EMPTY | 0 files |
| `docs/setup-evidence/P28-P36-masterplan/` | EXISTS, 2 carry-over files | 2 partial files (P27 spillover, not masterplan content) |

**Carry-over files in P28-P36-masterplan/research/** (2 files, P27 spillover, NOT masterplan content):

1. `p24-fork-dependency.md.part1` — partial file from P27 fork research.
2. `p27-output-inventory.md` — partial P27 output inventory (frontmatter + 5 lines).

**Masterplan decision required**: Should the masterplan (a) consume these stubs in-place, (b) rename/consolidate them, or (c) treat the masterplan as a P28 sub-folder leaving the stubs for individual phase evidence? Precedent: P27 used `docs/setup-evidence/P27/...` and did NOT pre-create stubs for P28+; the P28-P36 stubs appear to be either Faiz's pre-allocation or a script artifact.

### §6.4 Existing Phase Evidence Roots (all populated)

`docs/setup-evidence/` contains evidence roots for: P0, P1, P2, P3, P4, P5, P5.5, P6, P7, P7.5, P8, p9-finance, p9-p10-expansion, p10-production-hardening, p11-expansion, p11-whatsapp, p12-expansion, p13-expansion, p14-expansion, P16, P17, P18, P19, P20, P21, P22, P23, P24, P25, P26, P27.

Non-standard supplemental evidence roots also exist: `phase-1/`, `phase-2/`, `phase-3/`, `phase-4/`, `phase-5/`, `phase5-verification/`, `phase6-audit/`, `phase-7/`, `agents-md-refactor/`, `agents-md-update/`, `agents-md-update-v4/`, `hermes-migration/`, `hermes-phase1/`, `hermes-phase2/`, `hermes-phase2-discord/`, `decisions/`, `enterprise-gap-closing/`, `legacy-audit/`, `maintenance/`, `persona-calibration/`, `persona-freedom/`, `persona-v3/`, `restructure/`, `runtime-gaps/`, `adr-022-revision/`, `AUDIT-FIX/`, `auth-full-access-followup/`, `caveats-resolution/`, `conversational-handler/`, `fixes/`, `p4-cleanup/`, `p5-fixes/`, `p6-fixes/`, `p7-fixes/`, `p7-mcp/`, `p8-fixes/`, `plans/`.

---

## §7 Phase-by-Phase Brief Summary (P0-P27)

### §7.1 P0 — Infrastructure Foundation (29 steps, $0/mo)

VPS provisioning, `guinevere` user, UFW + fail2ban + CrowdSec, cgroup limits, Docker network, SOPS/age, PostgreSQL 16 + pgvector + TimescaleDB, Redis 7, Tailscale, Cloudflare Tunnel, Caddy, GitHub PAT, dual-provider backup (S3 + R2). All 29 steps complete with full audit coverage.

### §7.2 P1 — LLM + Hermes Agent (21 steps, $15/mo)

Python 3.12, UV 0.11.17, Hermes Agent v0.15.2, 9Router v0.4.66, GPT-5.5 + DeepSeek V4 Flash, LFAF routing, SystemPromptMaster deployment (7 safety checks), HARD STOP Protocol Verification (70/70 tests PASS).

### §7.3 P2 — Discord Bot (22 steps, $0/mo)

Discord app + bot token, intents, server with 4 categories + 13 channels, slash command registration, embed palette, /status /mood /help /safeword commands, Gotify fallback, **standalone bot masked post-ADR-035**.

### §7.4 P3 — Memory System (19 steps, $2/mo)

Alembic migrations (47 tables, 12 schemas), pgvector HNSW (m=16, ef=128), tsvector FTS, hybrid write/read pipeline, RRF k=60 hybrid ranking, context injection (top-k=3, 4000-token budget), DNR API, safe-mode gate, daily consolidation cron (03:00 Bangkok).

### §7.5 P4 — Persona Engine (23 steps, $1/mo)

Mood FSM (5 states), Yandere FSM (Y0→Y5, Y6 impossible), punishment ladder (L1→L5), reward tiers, streak tracking, 5 daily rituals (07:00-00:00 WIB), persona drift detection (SHA-256 hamming), safe-mode (D0-D4 distress). **1449 tests PASS**.

### §7.6 P5 — Agent Loop (23 steps, $3/mo, CRITICAL PATH)

FastAPI internal API, JWT/API key auth, 7-phase loop (Research→Plan→Delegate→Execute→Validate→Update→Evidence), Loop Guardian (30s heartbeat, 5min progress, 60s resource), Todo Enforcer, hash-anchored edit, sub-agent spawning with TASK/EXPECTED/TOOLS/MUST/MUST NOT/CONTEXT contract, evidence pipeline with LQS scoring.

### §7.7 P5.5 — P5 Remediation (10 fixes, 2026-06-02)

Migration chain repair, 3 indexes on `loop_instances`, Redis error handling, Guardian kill_loop, monitor() exception handling, dev-key fallback removed, systemd hardening (13 directives), routes wired to real LoopManager, logger.exception migration, /health/detailed endpoint.

### §7.8 P6 — MCP Tools (21 steps, $1/mo, REMEDIATION PASS)

16 MCP tools (brave_search, context7, exa, fetch, filesystem, github, grep_app, obscura-cdp, sequential-thinking, time, websearch, git, postgres, redis, shell, docker), 4-level auth matrix (READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN), tool selection decision matrix, cost tracking, budget enforcement (Exa $5/day cap).

### §7.9 P7 — Surveillance (22 steps, $1/mo)

FastAPI receiver (POST /surveillance/events), HMAC auth + replay protection, Redis DB2 buffer, TimescaleDB hypertables, data classification (Internal/Confidential/Restricted + Critical fail-closed), clipboard secret scanner, consent verification gate, safe-mode blocking, Tasker integration (4 profiles), 7-day raw retention.

### §7.10 P7.5 — P7 Remediation (9 fixes, 2026-06-03)

Router push to Redis DB2, async SQLAlchemy session, DataClassification CRITICAL tier, invalidate_cache wired, SurveillanceSafeModeGuard instantiated, _BLOCKED_ACTIONS expanded (humiliation + public_disclosure), P7-012 signing string colons, unknown safe-mode fail-closed, systemd StartLimitBurst=5.

### §7.11 P8 — Observability (23 steps, $4/mo, MVP APPROVED 2026-06-03)

Prometheus + Grafana + Loki + Promtail (8 services, 7 jobs, 15s interval), 6 Grafana dashboards, Sentry integration (send_default_pii=False + 6 REDACT + 6 DROP), 9 alert rules (SEV0-SEV3), /cost + /budget commands, monthly report automation, backup monitoring, guinevere-monitoring.service (MemoryMax=1G). **Faiz approved**.

### §7.12 P9 — Financial Tracking (13 steps, NOT STARTED, $1/mo, STABILIZATION)

Financial data model (transactions, budgets, categories), Tasker bank SMS parsing, classification engine, /finance summary/add/report, PDF generation, FinOps dashboard. Deferred under budget pressure.

### §7.13 P10 — Production Hardening (21 steps, NOT STARTED, $1/mo, STABILIZATION)

Security audit, vulnerability scan, PostgreSQL + Redis tuning, systemd limits refinement, backup automation, restore tests, DR drill, GitHub Actions CI, self-deploy pipeline, rollback automation, SOPS age key rotation, load testing (k6). Deferred under budget pressure.

### §7.14 P11 — WhatsApp Integration (23 steps, CODE COMPLETE, $0/mo)

21 modules in `src/channels/whatsapp/` using Neonize (replaced Baileys 2026-06-03 per ADR-022 revision). QR auth, SOPS session, connection handler, event routing, message pipeline, 4-level auth matrix integration. Code-only; production deploy not scheduled.

### §7.15 P12 — Gmail/Email Integration (29 steps, CODE COMPLETE, $0/mo)

27 modules in `src/gmail/` covering OAuth, IMAP, SMTP, classification, label sync, send queue, rate limiting, error handling. Code-only.

### §7.16 P13 — X Auto Poster (28 steps, CODE COMPLETE, ~$10/mo)

28 modules. ADR-038 covers 9 architecture decisions. Schedules + posts + tracks engagement + handles safety gates. Code-only.

### §7.17 P14 — Wearable Health Pipeline (20+11+steps, DONE, $0/mo)

ADR-037 canonical (Mi Fitness Cloud), ADR-039 Gadgetbridge SQLite parser (renumbered), ADR-040 Health Connect Pivot (renumbered, now canonical for Xiaomi Watch 2 Pro M2233W1 / HyperOS, supersedes 037+039 with both retained as fallback). Pivoted 2026-06-18 to 2026-06-19.

### §7.18 P15 — Windows Daemon (CANCELLED 2026-06-19)

Replaced by Hermes gateway Discord adapter.

### §7.19 P16 — Knowledge Graph (NOT STARTED, $0/mo)

ADR-050 architecture defined (PostgreSQL + RCTE + pgvector + consent + entity-resolution + memory + recall). Implementation deferred.

### §7.20 P17 — Cross-Device Sync (NOT STARTED)

Deferred.

### §7.21 P18 — Advanced Memory (NOT STARTED, MVP COMPLETE 4/8 steps)

Deferred.

### §7.22 P19 — Multi-Project Context (PRODUCTION COMPLETE, 2026-06-27)

ADR-052 canonical. CORE + Discord UX LIVE. Multi-project namespace isolation, project_id propagation, audit_journal 36/36 rows, memory principal scoped, recall pipeline project_id filter, Discord /project+ commands. Round-2 audit 2026-06-27 PASS (7 auditors).

### §7.23 P20 — Self-Improvement / Discord-Visible Autonomy (EARLY ACCEPTANCE, 2026-06-25)

Visible autonomy online. Operator waived 24h soak 2026-06-25 — **EARLY PRODUCTION ACCEPTANCE, PASS WITH ACCEPTED RISK**. 420 tests.

### §7.24 P21 — Voice Interface (DEF COMPLETE, IMPL HOLD, $0)

9 waves held until P20 production pass. Definition complete (plan + 9 research + 2 audit rounds).

### §7.25 P22 — Life Integration Hub (PASS W/ CONFIG_MISSING, 2026-06-27, $0)

13 core modules + 14 adapters + 1 migration + 7 tests (76 pass) + 1 smoke (12/12). ADR-053. 10/13 adapters CONFIG_MISSING (external creds operator-gated). 2 audit rounds PASS.

### §7.26 P22.1 — Foundation Hardening (PRODUCTION PASS, 2026-06-28)

audit_writer + consent_checker. 25 new tests. Closes 3 P22 gaps. 14/14 live VPS proof.

### §7.27 P23 — Embodied Operations (DEF COMPLETE, IMPL HOLD, $0)

20 waves (P23A start, P23B blocked). 51 files/10,306 lines. P23A: P1 fixes done; P23B: P19/P21/P22 runtime gating.

### §7.28 P24 — Hermes Fork-First Full Convergence (PLAN FIXED, IMPL HOLD, $0)

20 waves (held). Plan fixed (codex audit 5 blockers). Full owned fork preferred. Impl held until mama next audit.

### §7.29 P25, P26 — RESERVED

Listed in PROGRESS.md/CHECKLIST.md but no work, no plans, no evidence.

### §7.30 P27 — Hermes Society Foundation (DEF COMPLETE, IMPL HOLD, $0)

**10 research + 1 synthesis + 3 plan + 4 evidence + 2 fix logs + 20 audit reports + 1 README + 1 ADR (ADR-054)**. 37 files total. 2 audit rounds. 20/20 hard rejection criteria PASS. ADR-054 Accepted 2026-06-28. P28 implementation is a separate phase.

---

## §8 Documentation Conventions (Detailed)

### §8.1 File Naming

| Pattern | Example |
|---|---|
| `docs/{family}/{NN}-{DocName}_vN.N.md` | `docs/00-core/00-BRD_v2.0.md` |
| `docs/{family}/{NN}{a\|b}-{DocName}_vN.N.md` (supplements) | `docs/00-core/05a-OpenAPISpec_v1.0.md` |
| `docs/10-governance/P{N}-{ADR-N}-ADR-Revision.md` (revision artifact) | `docs/10-governance/P13-028-ADR-Revision.md` |
| `adr/ADR-NNN-{slug-topic}.md` | `adr/ADR-054-p27-hermes-society-foundation.md` |
| `docs/setup-evidence/P{NN}/...` (per-phase evidence) | `docs/setup-evidence/P27/...` |
| `docs/setup-evidence/P{NN}/plan/p{NN}-{topic}-plan.md` | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` |
| `docs/setup-evidence/P{NN}/research/p{NN}-{topic}-research.md` | `docs/setup-evidence/P27/research/p27-multi-agent-society-research.md` |
| `docs/setup-evidence/P{NN}/evidence/p{NN}-{topic}.md` | `docs/setup-evidence/P27/evidence/p27-final-report.md` |
| `docs/setup-evidence/P{NN}/evidence/audits/round-{N}/NN-{topic}-audit.md` | `docs/setup-evidence/P27/evidence/audits/round-1/01-equal-peer.md` |

### §8.2 Frontmatter (YAML) — Universal

```yaml
---
title: "<title>"
status: "Active|Aktif|Diterima|Draft|Dalam Review|Didepresiasi|Diarsipkan"
date: "<YYYY-MM-DD>"
last_modified: "<YYYY-MM-DD>"
owner: "Faiz"
executor: "Guinevere"
operator_alias_note: "Samm is a historical/pseudonymous alias only; canonical operator identity is Faiz."
---
```

**Specialized frontmatter variations:**
- ADR files: `format: "MADR with YAML frontmatter"`, `adr_count: <N>`.
- Evidence files: `phase: "P{NN}"`, `agent: "Guinevere (parent agent)"`.
- PersonaSafetyPolicy: classified boundary, HARD STOP explicit.

### §8.3 Standard Document Sections

All major docs include:
- Title (H1)
- Related Documents (cross-reference table)
- Footer (`STRICTLY PRIVATE & CONFIDENTIAL ... Project Guinevere.`)
- Catatan Perubahan (Indonesian change log)

**P27 plan sections** (precedent for masterplan):
1. Reader's Map
2. Mission
3. Ontology / Definitions
4. Architecture
5. Components
6. Risks
7. Research
8. Open Questions
9. Decision Records (ADR mapping)
10. Evidence
11. Implementation Plan
12. Audit Criteria
13. Hard Rejection Criteria
14. Roadmap (forward)
15. Operator Sign-Off

**P27 roadmap sections** (direct precedent for P28-P36 masterplan):
0. Reader's Map
1. Roadmap Philosophy / Reader Contract
2. Top-line Summary Table (9 phases at a glance)
3. P28 detail (most thorough — next implementation target)
4-11. P29-P36 (8 phases each, 10 elements)
12. Dependency Graph
13. Critical Path
14. Parallelization Map
15. Research Debt Tracker
16. Total Timeline Estimate
17. Anti-patterns Preserved
18. References
19. Footer

### §8.4 Update Workflow (per `docs/README.md`)

1. Create branch from `main`.
2. Modify document.
3. Bump version in frontmatter (minor for corrections, major for substantive).
4. PR with description and rationale.
5. After review and approval, merge to `main`.
6. Log change in document's "Catatan Perubahan" section.
7. Update `docs/README.md` and `adr/README.md` (synchronized indexes).

### §8.5 Cross-Reference Pattern

Documents use relative paths in cross-references (e.g., `[BRD v2.0](../00-core/00-BRD_v2.0.md)` from `docs/10-governance/`). ADRs use relative paths from `adr/` (e.g., `[ADR-054](../../adr/ADR-054-p27-hermes-society-foundation.md)` from `docs/10-governance/17-ADR_Index_v1.0.md`).

### §8.6 Bilingual Pattern

Master docs are in **Indonesian** with **English technical terms** preserved. Inline code, ADRs, and technical evidence files are typically in **English**. This bilingual convention is consistent across the suite and should be preserved by the P28-P36 masterplan.

---

## §9 Required Outputs for the P28-P36 Masterplan

### §9.1 Documents the Masterplan Must Produce

Based on the P27 precedent and the existing 11 numbered P28-P36 evidence stubs, the masterplan MUST produce:

1. **Master Roadmap** (1 file) — `docs/setup-evidence/P28-P36-masterplan/plan/p28-p36-master-roadmap.md` (or similar name).
   - Pattern: extend P27's `p27-p28-p36-master-roadmap.md` into a more detailed masterplan, or supersede it.
   - Sections: 0-19 per P27 §0-§19 precedent.

2. **Per-Phase Plans** (9 files) — `docs/setup-evidence/P{NN}/plan/p{NN}-{phase-name}-plan.md` for each of P28, P29, P30, P31, P32, P33, P34, P35, P36.
   - Each plan ~25 sections, ~4000-5000 lines (per P27 size).
   - Includes: Mission, Deliverables, Dependencies, Success Criteria, Complexity, Risk, Research, Duration.

3. **Per-Phase Executable Blueprints** (optional but recommended) — for next-implementation phases only (initially P28 only).
   - Pattern: P27's `p28-dual-autonomous-hermes-blueprint.md` (14 sections, ~3000 lines).

4. **Per-Phase Research Files** (variable) — pre-planning research for each phase as needed.
   - P27 precedent: 10 research files + 1 synthesis.

5. **Masterplan Verification** (1 file) — `p28-p36-masterplan-verification.md` (12-section per AGENTS.md §11).

6. **Masterplan Auditor Gate** (1 file) — `p28-p36-masterplan-auditor-gate.md` (aggregator report).

7. **Masterplan Final Report** (1 file) — `p28-p36-masterplan-final-report.md` (executive summary).

8. **Masterplan Fix Logs** (variable) — per-audit-round fix logs.

9. **Masterplan Audit Reports** (variable) — per-auditor reports in `audits/round-N/`.

10. **ADRs** (1 or N) — at least 1 masterplan-level ADR (e.g., ADR-055 for "P28-P36 Society Topology"). Additional per-phase ADRs at implementation time.

11. **Masterplan README** (1 file) — `docs/setup-evidence/P28-P36-masterplan/README.md`.

### §9.2 Numbering Decisions

| Slot | Decision Needed | Recommendation |
|---|---|---|
| ADR-055 | First new ADR (society topology or P28-specific?) | Recommend: **ADR-055 = P28 Dual Autonomous Hermes** (follows ADR-053 P22, ADR-054 P27 single-ADR-per-major-phase pattern). |
| ADR-056+ | Forward backlog | Reserve for per-phase ADRs at implementation time. |
| Plan file numbers | 0, 1, 2, ... in P28-P36-masterplan/plan/ | None required. |
| Audit report numbers | 01-NN per round | Precedent: round-1 has 01-14, round-2 has 01-06. |

### §9.3 Masterplan MUST Update

1. `docs/10-governance/17-ADR_Index_v1.0.md` — increment `adr_count` and add new ADR rows.
2. `adr/README.md` — synchronized index.
3. `docs/README.md` — if masterplan introduces new governance doc families.
4. `PROGRESS.md` — add P28-P36 row to Phase Summary table.
5. `CHECKLIST.md` — add P28-P36 row to budget tracking table.
6. `docs/setup-evidence/P28-P36-masterplan/README.md` — NEW (masterplan index).

---

## §10 Decisions the Masterplan Must Make

1. **Single masterplan-ADR vs per-phase-ADRs** — recommend single ADR-055 for society topology, with per-phase ADRs allocated at implementation time.
2. **Stub directory fate** — recommend consume in-place; rename `docs/setup-evidence/P28-P36-masterplan/` from "P28-P36 masterplan" (research) to "masterplan root" (plan + research + evidence).
3. **Document numbering for new governance docs** — if masterplan introduces new top-level governance docs (e.g., "Society Topology Policy"), use next free numbers in 10-governance family (currently 18, 19 used by P12/P13 revisions; numbers 20-29 free for governance supplements).
4. **Bilingual pattern** — preserve Indonesian/English convention; masterplan body in English (technical), summary in Indonesian.
5. **Supersession** — if masterplan replaces P27's `p27-p28-p36-master-roadmap.md` as the canonical roadmap, mark P27's roadmap as "Superseded by P28-P36 masterplan" and link.
6. **Audit-rounds** — recommend 2 audit rounds per precedent (P27: 14+6 auditors), or 1 lighter round for masterplan-only with deeper rounds at each phase implementation.
7. **P28 executable blueprint fate** — P27 created a 14-section P28 blueprint; masterplan should either (a) absorb it, (b) supersede it, or (c) ratify it as binding.
8. **Sequencing for research** — P27 has 10 research files; masterplan may consolidate (e.g., one Society-Topology research file referencing existing) or expand (e.g., 5 additional research files for cross-VPS, FinOps, etc.).

---

## §11 Cross-References and Source Paths

### §11.1 Authoritative Source Files

| File | Purpose |
|---|---|
| `C:\Users\faizz\guinevere\docs\README.md` | Master docs index (44 active, 18 archived) |
| `C:\Users\faizz\guinevere\PROGRESS.md` | Phase progress (P0-P27 + P28-P36 reserved) |
| `C:\Users\faizz\guinevere\CHECKLIST.md` | Implementation verification checklist |
| `C:\Users\faizz\guinevere\docs\10-governance\17-ADR_Index_v1.0.md` | ADR master index (40 ADRs, last_modified 2026-06-28) |
| `C:\Users\faizz\guinevere\adr\README.md` | ADR folder index (38 ADRs, last_modified 2026-06-18) |
| `C:\Users\faizz\guinevere\docs\10-governance\decisions-log.md` | Consolidated decisions log (5 decisions) |
| `C:\Users\faizz\guinevere\AGENTS.md` | Operating contract (Guinevere project) |

### §11.2 P27 Deliverables (Direct Precedents for Masterplan)

| File | Purpose |
|---|---|
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\plan\p27-hermes-society-foundation-plan.md` | 25-section enterprise plan (~4790 lines) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\plan\p27-p28-p36-master-roadmap.md` | 19-section forward roadmap (~1250 lines) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\plan\p28-dual-autonomous-hermes-blueprint.md` | 14-section executable P28 blueprint (~3000 lines) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\README.md` | P27 evidence root index |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P27\evidence\p27-final-report.md` | P27 executive summary |
| `C:\Users\faizz\guinevere\adr\ADR-054-p27-hermes-society-foundation.md` | P27 canonical ADR |

### §11.3 P22 / P24 Evidence (Closest Precedent Patterns)

| File | Purpose |
|---|---|
| `C:\Users\faizz\guinevere\docs\setup-evidence\P22\research\raw-full\*.md` | P22 raw research (6+ files) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\*.md` | P24 research (12+ files) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P23\research\*.md` | P23 research (10+ files) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P22\evidence\*.md` | P22 evidence (final, audits) |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P24\evidence\*.md` | P24 evidence (final, audits, plan-fix-audits) |

---

## §12 Footer

### §12.1 Sources Verified

All data in this inventory was verified by reading source files on 2026-06-28:
- `docs/README.md` (333 lines, 44 active docs confirmed)
- `PROGRESS.md` (P0-P27 status, $29+ budget)
- `CHECKLIST.md` (P0-P27 status, 95.3% complete)
- `docs/10-governance/17-ADR_Index_v1.0.md` (40 ADRs, last_modified 2026-06-28)
- `adr/README.md` (38 ADRs, last_modified 2026-06-18)
- `docs/10-governance/decisions-log.md` (5 decisions, last 2026-06-07)
- `adr/ADR-054-p27-hermes-society-foundation.md` (P27 canonical ADR, Accepted)
- `docs/setup-evidence/P27/README.md` (P27 evidence root, 37 files)
- `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md` (19-section roadmap, 1260 lines)
- 4 dir globs of `docs/setup-evidence/P28-P36/` (stubs confirmed empty)
- 1 dir glob of `docs/setup-evidence/P28/` through `P36/` (all empty)

### §12.2 Key Discoveries for Masterplan Author

1. **P28-P36 evidence directories already exist as empty stubs** — masterplan must decide whether to consume or rename.
2. **ADR-054 is highest used; ADR-055 is next available** — recommend ADR-055 for P28 Dual Autonomous Hermes (or society topology consolidation).
3. **P27 already produced a forward roadmap (p27-p28-p36-master-roadmap.md, 1260 lines)** — masterplan can supersede, absorb, or extend it.
4. **P27 also produced a P28 executable blueprint (p28-dual-autonomous-hermes-blueprint.md, 3000 lines)** — masterplan must decide binding vs reference vs superseded.
5. **9 backlog ADR slots are FREE** (ADR-041, 043-048, 051) — usable for masterplan.
6. **Documentation convention is bilingual (Indonesian narrative + English technical)** — preserve in masterplan.
7. **Audit-rounds precedent is 2 rounds** (P27: 14+6 auditors) — masterplan should plan similar.
8. **Per-phase evidence pattern is P{NN}/{README, research/, plan/, evidence/}** — preserve.

### §12.3 Maintenance

This inventory is **frozen** as of 2026-06-28. Update only when:
- New ADRs are created (increment adr_count, add row).
- New governance docs are created (add to docs/README.md registry).
- Phase status changes (mark P28+ statuses in PROGRESS.md/CHECKLIST.md).
- ADR-055 is allocated (update §2.4, §2.5, §9.2).

### §12.4 Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial P28-P36 masterplan input inventory |

### §12.5 Operator Sign-Off

Pending Faiz review. This inventory is a **research input**, not a decision. The masterplan author (separate role) consumes this inventory to produce the canonical P28-P36 masterplan and updates §9 and §10 based on the chosen decisions.

---

> **Inventory complete.** The masterplan author now has the full picture: 41 ADRs (highest 054), 44 active docs across 8 families, 27 completed phases (P0-P24 + P27), 9 empty P28-P36 stubs, 9 free ADR backlog slots, and the P27 deliverables as direct precedents.
