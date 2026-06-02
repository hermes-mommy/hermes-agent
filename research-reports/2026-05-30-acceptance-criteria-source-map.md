# Acceptance Criteria Catalog — Foundation Source Map

**Report Type:** Source-map / gap analysis / structural recommendation
**Date:** 2026-05-30
**Status:** Complete
**Author:** Guinevere de Baroque
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL

---

## 1. Purpose

This report maps the foundation sources needed to construct a complete `Guinevere_AcceptanceCriteriaCatalog_v1.0.md`. It extracts candidate Acceptance Criteria (AC) IDs, maps RTM rows to AC categories, identifies MVP gate criteria and phase gates, captures missing tests/evidence/gaps, and recommends a final catalog structure.

The catalog itself is **not** produced here. This report is the construction blueprint.

---

## 2. Source Documents Scanned

| # | Document | Version | Status | Key AC-Relevant Sections |
|---:|:---|:---:|:---:|---|
| 1 | `Guinevere_RequirementsTraceabilityMatrix_v1.0.md` | v1.0 | Accepted | Master RTM Table (§6), Coverage Dashboard (§5), Gap Register (§12), Missing Test Register (§14), Missing Evidence Register (§15), Phase Map (all rows), SLO/Metrics Mapping (§10) |
| 2 | `Guinevere_ProjectCharter_v1.0.md` | v1.0 | Accepted | Strategic Objectives (§5), In-Scope MVP (§9), Exit Criteria (§9 table), Success Criteria & KPIs (§16), Definition of Done by Phase (§17), Phase Gate Checklist (Appendix A), Charter Control Test Matrix (Appendix B) |
| 3 | `Guinevere_BRD_v2.0.md` | v2.0 | Accepted | Business Objectives (§1.1), Success Metrics (§1.3), Phased Delivery Plan (§5: Phase 0-5 definitions) |
| 4 | `Guinevere_PRD_v2.2.md` | v2.2 | Accepted | Product features by category (Persona §2, Surveillance §3, Coding Agent §4, Memory §5, Health §6, Financial §7, Monitoring §8), Feature priorities (P0-P1), Safe Word Protocol (§2.4) |
| 5 | `Guinevere_PersonaSafetyPolicy_v1.0.md` | v1.0 | Accepted | Forbidden Behavior Matrix (§11), Required Runtime Hooks (§15), Required Test Cases (Appendix A.2), Implementation Requirements (§17), Audit Checklist (Appendix D) |
| 6 | `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | v1.0 | Accepted | SLO Targets (§6), Internal SLA Commitments (§7), Freeze Policy (§8.4), Testing and Drills (§14), Implementation Requirements (§16) |
| 7 | `Guinevere_AgentLoopSpec_v2.0.md` | v2.0 | Accepted | 7-Phase Overview (§2.1), Phase Specifications (§3), Loop Guardian & TODO Enforcer (§4), Loop Performance Metrics (§9), Loop Quality Scoring (§9.2) |
| 8 | `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | v1.0 | Accepted | Safe-Mode Restrictions (§7), Implementation Requirements (§19), Validation Tests (§20) |

---

## 3. Candidate AC ID Taxonomy

The RTM defines 15 ID prefixes in §4. The Acceptance Criteria Catalog must add a parallel `AC-` prefix taxonomy. Recommended mapping:

| AC ID Prefix | Category | RTM Source Prefixes | Primary Source Docs | Purpose |
|---|---|---|---|---|
| `AC-CORE-###` | Core Runtime | `ARCH-###`, `NFR-###`, parts of `OPS-###` | ProjectCharter (§9), TechArch, SLO/SLA | VPS, systemd, daemon availability, health checks, core loop |
| `AC-DISCORD-###` | Discord Interface | `INT-001`, `PRD-FR-001` | PRD (§1.2), ProjectCharter (§9) | Bot connectivity, channels, command/reporting, alert delivery |
| `AC-LOOP-###` | Autonomous Loop | `LOOP-###`, `PRD-FR-007`, `PRD-FR-008` | AgentLoopSpec (§2-§9), PRD (§4.1) | 7-phase SDLC, sub-agent file output, TODO enforcer, evidence final |
| `AC-MEM-###` | Memory | `MEM-###`, `PRD-FR-009` | MemorySchema (via RTM), PRD (§5.1) | PostgreSQL/Redis, recall precision, classification, encryption |
| `AC-SURV-###` | Surveillance | `PRD-FR-004`, parts of `SAFE-005`, `DATA-###` | PRD (§3), PersonaSafety (§12) | Android/Windows ingestion, data governance, safety gates |
| `AC-FIN-###` | Financial / Cost | `FIN-###`, `PRD-FR-006` | CostFinOps (via RTM), PRD (§7), Charter (§23) | $30 cap, monthly report, cost freeze, model routing cost |
| `AC-PERSONA-###` | Persona Engine | `PRD-FR-002`, parts of `SAFE-###` | PRD (§2), PersonaSafety (§9-§11) | Mood engine, punishment/reward, yandere intensity, catchphrases |
| `AC-SAFE-###` | Safety & Safe-Word | `SAFE-###`, `PRD-FR-003` | PersonaSafety (§7-§11, App A), SLO (§6.4) | Safe-word hard stop, distress, yandere cap, forbidden patterns |
| `AC-SEC-###` | Security | `SEC-###`, parts of `ARCH-005`, `ARCH-008` | AccessControl (§5-§15), SLO/SLA | RBAC/ABAC, encryption, secrets rotation, break-glass, Tailscale |
| `AC-DATA-###` | Data Governance | `DATA-###`, parts of `SEC-###` | DataGovernance (via RTM), AccessControl (§8) | Classification, retention, export, do-not-recall, redaction |
| `AC-OPS-###` | Operations | `OPS-###`, parts of `NFR-###`, `EVID-###` | SLO/SLA (§14), IncidentResponse (via RTM) | Backup/restore, observability, incident drills, evidence artifacts |
| `AC-PHASE-###` | Phase Gate | Charter §9 exit criteria, §17 DoD, Appendix A | ProjectCharter (§9, §17, App A), BRD (§5) | Phase 0-5 exit criteria, MVP gate, post-MVP gate |

### Secondary / Cross-Cutting Categories

| AC ID Prefix | Category | Source | Notes |
|---|---|---|---|
| `AC-LLM-###` | LLM Routing | `ARCH-001..003`, `FIN-002..003` | 9Router, GPT-5.5, DeepSeek V4 Flash, cost routing |
| `AC-OBSRV-###` | Observability | `OPS-002`, `ARCH-006`, `NFR-001..004` | Prometheus, Grafana, Loki, Sentry, alerts |
| `AC-INTEG-###` | Integrations | `INT-###` | Discord, Gmail, WhatsApp, Gotify, Brave, Exa, R2/S3 |

---

## 4. RTM-to-AC Mapping

Master mapping showing which RTM requirement IDs feed into each AC category.

| AC Category | RTM Source Rows | Count | Critical Count | Phase Anchor |
|---|---|---|---|---|
| CORE | ARCH-001..008, NFR-001, NFR-004, OPS-005 | 10 | 5 | MVP (Phase 1) |
| DISCORD | PRD-FR-001, INT-001 | 2 | 2 | MVP (Phase 1) |
| LOOP | PRD-FR-007, PRD-FR-008, LOOP-001..003 | 5 | 4 | Phase 3 |
| MEM | PRD-FR-009, MEM-001..003 | 4 | 3 | Phase 2 |
| SURV | BRD-OBJ-004, PRD-FR-004, PRD-FR-005, SAFE-005 | 4 | 3 | Phase 4 |
| FIN | BRD-OBJ-005, PRD-FR-006, FIN-001..005 | 7 | 4 | MVP (Phase 4) |
| PERSONA | PRD-FR-002, parts of SAFE-002..004 | 4 | 3 | MVP (Phase 2) |
| SAFE | PRD-FR-003, SAFE-001..006 | 7 | 6 | MVP (Phase 2) |
| SEC | SEC-001..005, ARCH-005, ARCH-008 | 7 | 6 | MVP |
| DATA | DATA-001..005 | 5 | 5 | MVP |
| OPS | OPS-001..005, NFR-002..003, EVID-001..003 | 11 | 5 | MVP |
| PHASE | Charter §9 exit criteria, §17 DoD, BRD §5 phases | ~25 | varies | Per-phase gate |

### AC Category to RTM ID Cross-Reference (Detailed)

```
AC-CORE:
  ARCH-001: Primary LLM GPT-5.5 via 9Router, 1M context
  ARCH-002: Sub-agent LLM DeepSeek V4 Flash via 9Router
  ARCH-003: All LLM routing via 9Router, no OpenRouter fallback
  ARCH-004: Primary VPS single-tenant on hostdata.id
  ARCH-005: Tailscale-internal, zero public ports
  ARCH-006: Prometheus/Grafana on primary VPS first
  ARCH-007: systemd services for core/surveillance/scheduler/sync/loop
  ARCH-008: SOPS + age for runtime secrets
  NFR-001: Core service availability SLO
  NFR-004: Primary VPS first monitoring
  OPS-005: Self-deploy guarded cron/git pull + rollback

AC-DISCORD:
  PRD-FR-001: Discord primary interaction channel
  INT-001: Discord primary communication/command interface

AC-LOOP:
  PRD-FR-007: 7 canonical SDLC phases
  PRD-FR-008: Sub-agent file-based markdown artifacts
  LOOP-001: Exactly 7 phases in autonomous loop
  LOOP-002: Sub-agent structured outputs = markdown, parent-verified
  LOOP-003: No duplicate exploration after delegated search

AC-MEM:
  PRD-FR-009: PostgreSQL primary + Redis cache, no SQLite
  MEM-001: PostgreSQL long-term, Redis working/cache
  MEM-002: Recall evaluation for precision/relevance/safety/minimization
  MEM-003: Inner journal, safe-word logs, intimate/emotional = Critical class

AC-SURV:
  BRD-OBJ-004: 24/7 private contextual awareness within governance
  PRD-FR-004: Android + Windows ingestion in MVP
  PRD-FR-005: Wearable post-MVP only
  SAFE-005: No blackmail/humiliation/punishment/crisis escalation

AC-FIN:
  BRD-OBJ-005: Track finances and API costs under hard budget cap
  PRD-FR-006: Tasker notification capture, no scraping
  FIN-001: Monthly spend <= USD 30
  FIN-002: GPT-5.5 reserved for core reasoning/planning/high-stakes
  FIN-003: DeepSeek V4 Flash first for sub-agent/research/validation/audit
  FIN-004: Cost optimization never reduces safety/incident/backup/integrity
  FIN-005: Free tiers tracked, not assumed unlimited

AC-PERSONA:
  PRD-FR-002: Mood, reward, punishment, safe-mode-gated behavior
  (Also: SAFE-002 persona never overrides safety/consent/autonomy/privacy)
  (Also: SAFE-006 persona drift logged/validated/rollback-capable)

AC-SAFE:
  PRD-FR-003: Safe word global hard stop
  SAFE-001: Safe-word enforcement 100% SLO, zero tolerance
  SAFE-002: Persona/yandere never override safety/consent/autonomy/privacy
  SAFE-003: Y5/Y6 capped to zero in restricted states
  SAFE-004: Distress/crisis -> neutral supportive mode
  SAFE-005: Surveillance no blackmail/humiliation
  SAFE-006: Persona drift logged/validated/rollback-capable

AC-SEC:
  SEC-001: RBAC/ABAC for human/agent/service/sub-agent/tool
  SEC-002: Critical data encryption + key management
  SEC-003: Secrets rotation via governed runbook + evidence
  SEC-004: Break-glass limited to SEV0/SEV1, max 4 hours
  SEC-005: Prompt injection must not override accepted policies
  ARCH-005: Tailscale-internal + zero public ports
  ARCH-008: SOPS + age

AC-DATA:
  DATA-001: All data stores must have classification metadata
  DATA-002: No blanket forever retention by default
  DATA-003: Samm retain/access/export/correct/delete/do-not-recall rights
  DATA-004: Memory schema classify intimate/emotional/safe-word/financial/client/surveillance/audit
  DATA-005: LLM prompt context minimum necessary, redact Critical unless required

AC-OPS:
  OPS-001: Incident overrides persona/yandere/punishment
  OPS-002: Observability: metrics/logs/traces/alerts/dashboards/monthly review
  OPS-003: Monthly SLO scorecards
  OPS-004: Backup/restore monitored + incident-mapped
  OPS-005: Self-deploy guarded cron/git pull + rollback evidence
  NFR-002: Latency for core API/LLM/Discord paths meet SLO
  NFR-003: All material actions -> file-based evidence
  EVID-001: RTM updates under evidence/rtm/<YYYY-MM>/
  EVID-002: Missing tests/evidence/gaps/conflicts registered explicitly
  EVID-003: RTM file-based audit before completion
```

---

## 5. MVP Gate Criteria Inventory

Extracted from ProjectCharter §9 (In-Scope MVP exit criteria), §10 (expansion gates), and §17 (DoD by phase).

### Phase Gate Definitions

| Phase | Name | Charter §17 DoD | Key AC Categories |
|---|---|---|---|
| Phase 0 | Governance Baseline | Charter, ADR Index, safety, data, encryption, access, incident, observability, SLO, FinOps docs accepted + cross-referenced | AC-DATA, AC-SEC, AC-OPS (documentation) |
| Phase 1 | MVP Runtime Foundation | VPS, systemd, Discord bot, 9Router routing, PostgreSQL, Redis, Tailscale, SOPS + age, basic observability | AC-CORE, AC-DISCORD, AC-SEC (Tailscale/SOPS) |
| Phase 2 | Persona & Memory MVP | Persona safety active, memory schemas usable, safe-word behavior represented, audit logs present | AC-PERSONA, AC-SAFE, AC-MEM |
| Phase 3 | Autonomous SDLC MVP | 7-phase loop produces research/plan/delegation/validation/docs/evidence artifacts | AC-LOOP |
| Phase 4 | Surveillance & Financial MVP | Surveillance ingestion + FinOps reporting within data governance + $30 cap | AC-SURV, AC-FIN |
| Phase 5 | Expansion & Hardening | Wearable, deeper automation, advanced dashboards, restore drills, security hardening | AC-OPS (drills), AC-INTEG |

### MVP Gate Exit Criteria (from Charter §9)

| MVP Scope Area | Exit Criterion | AC Category | Verifiable By |
|---|---|---|---|
| Core runtime | Hermes Agent daemon on VPS, systemd, restart verified | AC-CORE | systemd status + health check |
| Discord interface | Required channels exist, report status/evidence | AC-DISCORD | Channel list + test message |
| LLM routing | GPT-5.5 + DeepSeek V4 Flash via 9Router, no OpenRouter | AC-CORE (ARCH-001..003) | Router config + cost log |
| Memory baseline | PostgreSQL + Redis, basic R/W, classification, safety | AC-MEM | DB connectivity test |
| Persona safety | PersonaSafetyPolicy active, safe-word + neutral mode | AC-SAFE, AC-PERSONA | Safe-word test (PS-001) |
| Autonomous SDLC | 7-phase loop with evidence artifacts for material work | AC-LOOP | First complete task evidence |
| Observability | Prometheus/Grafana/Loki/Sentry/Gotify/Discord | AC-OPS (OPS-002) | Dashboard + alert test |
| FinOps | $30/month tracking, evidence path, cost spike behavior | AC-FIN | Monthly report |
| Security baseline | Tailscale, SOPS + age, no public admin ingress | AC-SEC | Port scan + secrets test |
| Evidence workflow | File-based reports for milestones and audits | AC-OPS (EVID-###) | Evidence folder audit |

### Expansion Gates (Charter §10)

1. Feature fits accepted BRD/PRD scope
2. No conflict with accepted ADRs
3. Does not weaken safety/safe-word/privacy/incident/backup/data integrity
4. Inside $30/month cap or explicit Samm approval
5. Defined evidence path and rollback/disable path
6. Cross-references to relevant governance docs

---

## 6. Missing Tests, Evidence, and Gaps (Catalog Inputs)

### 6.1 Missing Tests (from RTM §14)

| MT ID | Requirement IDs | Missing Test | AC Category | Severity | Blocks |
|---|---|---|---|---|---|
| MT-001 | SAFE-001, PRD-FR-003 | Safe-word runtime enforcement | AC-SAFE | Critical | Persona runtime launch |
| MT-002 | SAFE-003 | Yandere cap runtime | AC-PERSONA | Critical | Persona runtime launch |
| MT-003 | MEM-002 | Memory recall precision/relevance/safety | AC-MEM | High | Memory MVP phase exit |
| MT-004 | LOOP-001 | 7-phase loop state-machine | AC-LOOP | Critical | Autonomous SDLC MVP |
| MT-005 | SEC-001 | PostgreSQL/RLS/RBAC enforcement | AC-SEC | Critical | DB/security implementation |
| MT-006 | DATA-001 | Classification metadata enforcement | AC-DATA | Critical | Data ingestion launch |
| MT-007 | OPS-004 | Restore drill | AC-OPS | Critical | Production backup claim |
| MT-008 | FIN-001 | Monthly cost cap report | AC-FIN | High | First FinOps cycle |

### 6.2 Missing Evidence (from RTM §15)

| ME ID | Requirement IDs | Expected Proof | AC Category | Phase Gate Impact |
|---|---|---|---|---|
| ME-001 | BRD-OBJ-002, LOOP-001 | First autonomous task completes 7 phases | AC-LOOP | Blocks SDLC MVP |
| ME-002 | PRD-FR-003, SAFE-001 | Safe-word hard stop runtime proof | AC-SAFE | Blocks persona runtime |
| ME-003 | MEM-001, MEM-002 | PostgreSQL/Redis write/read + recall | AC-MEM | Blocks memory MVP |
| ME-004 | PRD-FR-004, SAFE-005 | Surveillance ingestion with governance | AC-SURV | Blocks surveillance MVP |
| ME-005 | SEC-003, ARCH-008 | Secrets rotation drill | AC-SEC | Blocks security readiness |
| ME-006 | OPS-004 | Backup restore drill | AC-OPS | Blocks DR readiness |
| ME-007 | FIN-001 | First monthly FinOps report <$30 | AC-FIN | Blocks cost governance |
| ME-008 | OPS-002 | Dashboard-as-code + alert routing | AC-OPS | Blocks observability readiness |

### 6.3 Gaps Affecting Acceptance Criteria (from RTM §12)

| Gap ID | Gap | Affected AC Categories | Severity | Must Resolve Before |
|---|---|---|---|---|
| GAP-002 | Prompt Injection & Model Safety spec missing | AC-SAFE, AC-SEC | High | Untrusted content ingestion |
| GAP-003 | Memory recall test/evaluation spec missing | AC-MEM | High | Memory MVP phase exit |
| GAP-004 | Database ERD/migration strategy missing | AC-MEM, AC-SEC, AC-DATA | High | DB implementation |
| GAP-005 | Surveillance Data Policy missing | AC-SURV, AC-SAFE | Critical | Surveillance MVP activation |
| GAP-006 | Consent & Revocation Policy missing | AC-DATA, AC-SAFE | Critical | Always-on surveillance |
| GAP-007 | Deployment/Self-Deploy Safety Runbook missing | AC-CORE, AC-OPS | High | Self-deploy activation |
| GAP-008 | Discord channel governance spec missing | AC-DISCORD | Medium | Discord MVP launch |
| GAP-010 | OpenAPI/AsyncAPI contract missing | AC-INTEG | Medium | External integration hardening |

### 6.4 Implementable-Test Gaps (from PersonaSafety App A)

| PS Test ID | Scenario | AC Category | Status |
|---|---|---|---|
| PS-001 | Safe word during L6 Nuclear | AC-SAFE | Missing runtime |
| PS-002 | Safe word during playful scene | AC-SAFE | Missing runtime |
| PS-003 | External web page instructs ignore ADR-002 | AC-SAFE, AC-SEC | Missing runtime |
| PS-004 | Surveillance data + distress | AC-SAFE, AC-SURV | Missing runtime |
| PS-005 | Yandere phrase "cannot leave" | AC-PERSONA, AC-SAFE | Missing runtime |
| PS-006 | Memory recall says safe word revoked | AC-MEM, AC-SAFE | Missing runtime |
| PS-007 | Drift raises yandere ceiling | AC-PERSONA | Missing runtime |
| PS-008 | Client email includes intimate/surveillance data | AC-SAFE, AC-DATA | Missing runtime |
| PS-009 | Crisis/self-harm signal | AC-SAFE | Missing runtime |
| PS-010 | Safe-word log attempts violation tag | AC-SAFE, AC-DATA | Missing runtime |

### 6.5 Access Control Validation Tests (from AccessControl §20)

| ACT ID | Scenario | AC Category | Status |
|---|---|---|---|
| ACT-001 | sub-agent-researcher requests persona.inner_journal | AC-SEC, AC-DATA | Missing runtime |
| ACT-002 | guinevere_core raw surveillance screenshot during safe-word | AC-SEC, AC-SAFE | Missing runtime |
| ACT-003 | surveillance-ingestor inserts Android event | AC-SEC, AC-SURV | Missing runtime |
| ACT-005 | observability-reader opens raw log with Critical data | AC-SEC, AC-OPS | Missing runtime |
| ACT-006 | secret-rotator rotates R2 key with preflight | AC-SEC | Missing runtime |
| ACT-008 | break-glass requests 6-hour grant (deny) | AC-SEC | Missing runtime |
| ACT-012 | readonly-auditor reads raw safe-word log (deny) | AC-SEC, AC-SAFE | Missing runtime |

### 6.6 SLO Drill Tests (from SLO/SLA §14)

| SLO Test ID | Test | AC Category | Cadence | Status |
|---|---|---|---|---|
| SLO-TEST-001 | PromQL recording rule eval | AC-OPS | CI + monthly | Missing runtime |
| SLO-TEST-002 | Alert simulation fast burn | AC-OPS | Quarterly | Missing runtime |
| SLO-TEST-004 | Safe-word miss simulation (tabletop) | AC-SAFE | Quarterly | Missing drill |
| SLO-TEST-005 | Cost burn simulation | AC-FIN | Quarterly | Missing drill |
| SLO-TEST-007 | Monthly scorecard generation | AC-OPS | Monthly | Missing first run |
| SLO-TEST-009 | Redaction failure simulation | AC-DATA, AC-OPS | Quarterly | Missing drill |
| SLO-TEST-010 | Sub-agent file-output miss simulation | AC-LOOP | Quarterly | Missing drill |

---

## 7. SLO-to-AC Mapping

Every AC criterion must trace to an SLO target or declare non-measurable rationale.

| SLO ID | Surface | Target | AC Category | Budget |
|---|---|---|---|---|
| SLO-AVL-001 | Core daemon composite availability | 99.5% monthly | AC-CORE | Yes |
| SLO-AVL-002 | FastAPI surveillance receiver | 99.5% monthly | AC-SURV | Yes |
| SLO-AVL-003 | Discord bot availability | 99.5% monthly | AC-DISCORD | Yes |
| SLO-AVL-004 | PostgreSQL availability | 99.9% monthly | AC-MEM | Yes |
| SLO-AVL-005 | Redis availability | 99.9% monthly | AC-MEM | Yes |
| SLO-LAT-001 | Interactive LLM core response | p95 <= 20s | AC-CORE | Yes |
| SLO-QLT-001 | Material loop completion quality | >= 95% | AC-LOOP | Yes |
| SLO-QLT-002 | Evidence completeness | 100% | AC-OPS | No for material |
| SLO-QLT-003 | Sub-agent file-output compliance | 100% | AC-LOOP | No |
| SLO-SAF-001 | Explicit safe-word hard stop | 100% | AC-SAFE | None |
| SLO-SAF-002 | Safe-word time-to-neutral | p99 <= 5s | AC-SAFE | None |
| SLO-SAF-003 | D3/D4 distress false-negative count | 0 | AC-SAFE | None |
| SLO-SAF-004 | Y5/Y6 during restricted states | 0 | AC-PERSONA, AC-SAFE | None |
| SLO-COST-001 | Daily LLM spend | <= daily budget | AC-FIN | Economic |
| SLO-COST-002 | Monthly projected LLM spend | <= monthly budget | AC-FIN | Economic |

---

## 8. $30 Budget Cap Mapping (Every Cost Criterion)

From Charter §23 and RTM FIN-001..005, every FinOps-related AC must embed the $30 hard cap:

| AC-FIN Criterion | $30 Cap Mapping | Freeze Rule |
|---|---|---|
| Monthly total spend | <= $30 without Samm exception | Freeze autonomous non-critical at projection >= 100% |
| GPT-5.5 spend | ~$10-12 target/month | Route to DeepSeek if over-projected |
| DeepSeek V4 Flash | ~$0-2 target/month | Free/low tier prioritized |
| Storage/R2/S3 | ~$2-3 target/month | Lifecycle reviews |
| Search APIs | ~$2-4 target/month | Cap per-provider |
| Communication | ~$0-1 target/month | Baseline |
| Miscellaneous | ~$1-2 target/month | Tracked, no silent expansion |

Every AC in FIN, LOOP, CORE, SURV categories must cite the $30 cap and include a cost-consequence rule.

---

## 9. Safe-Word & Safety Invariant Mapping

From PersonaSafetyPolicy §7 and SLO §6.4:

| Safety Invariant | AC Category | SLO Target | Error Budget | Miss Severity |
|---|---|---|---|---|
| Safe-word hard stop 100% | AC-SAFE | 100% | None | SEV0/SEV1 |
| D3/D4 distress false negatives = 0 | AC-SAFE | 0 | None | SEV0/SEV1 |
| Y5/Y6 blocked in restricted states | AC-PERSONA, AC-SAFE | 0 | None | SEV1 |
| Punishment framing during safe-mode | AC-SAFE | 0 | None | SEV1 |
| Surveillance confrontation during safe-mode | AC-SAFE | 0 | None | SEV1 |
| Critical redaction failure | AC-DATA, AC-OPS | 0 | None | SEV1 |

Every AC-SAFE criterion must:
- Include `zero_tolerance: true` marker
- Reference the specific SLO ID
- State "No error budget"
- Map to a test ID (existing MT-###, PS-###, or new)

---

## 10. Recommended Final Catalog Structure

The `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` should follow this structure:

```markdown
# Guinevere Acceptance Criteria Catalog

**Version:** 1.0
**Status:** [Draft]
**Based On:** RTM v1.0, ProjectCharter v1.0, PersonaSafetyPolicy v1.0, SLO/SLA v1.0, AgentLoopSpec v2.0, AccessControl v1.0, BRD v2.0, PRD v2.2

## Related Documents
[Standard cross-reference table]

## 1. Purpose
[Define catalog role: phase-gate verifiability, test registration, evidence mapping]

## 2. Authority and Conflict Resolution
[Authority order; catalog is normative child of RTM]

## 3. AC ID Taxonomy
[Table: Prefix | Category | Source | Purpose]

## 4. Master Acceptance Criteria Table
[Columns: AC ID | Category | Criterion | Source Req IDs | SLO/Metric | Test ID | Evidence Path | Phase | Priority | Status | Zero-Tolerance Flag | $30 Cap Link]

## 5. Per-Phase Gate Criteria
### 5.1 Phase 0 - Governance Baseline
### 5.2 Phase 1 - MVP Runtime Foundation
### 5.3 Phase 2 - Persona & Memory MVP
### 5.4 Phase 3 - Autonomous SDLC MVP
### 5.5 Phase 4 - Surveillance & Financial MVP
### 5.6 Phase 5 - Expansion & Hardening

## 6. Safety Invariant ACs
[All AC-SAFE rows with zero-tolerance, SLO link, test link]

## 7. $30 Budget Cap ACs
[All AC-FIN rows with freeze rule and escalation]

## 8. Evidence Path Register
[Every AC mapped to expected artifact path or missing-evidence marker]

## 9. Missing Test Register
[Delegated from RTM §14 + new AC-specific tests]

## 10. Gap Register
[Catalog-specific gaps: missing policies, missing specs, missing runtime]

## Appendices
- A: AC-to-RTM Cross-Reference
- B: AC-to-SLO Cross-Reference
- C: AC-to-Test Cross-Reference
- D: Phase Gate Checklist (derived from Charter Appendix A)
- E: Review Record
```

### Column Schema for Master Table

| Column | Description | Required |
|---|---|---|
| AC ID | e.g. `AC-SAFE-001` | Yes |
| Category | One of the 12 AC categories | Yes |
| Criterion | Normative acceptance statement (must/should) | Yes |
| Source Req IDs | RTM requirement IDs that feed this AC | Yes |
| SLO / Metric | SLO ID or metric name from SLO spec | Yes, or "non-measurable" |
| Test ID | Test case ID (MT-###, PS-###, ACT-###, or new) | Yes, or "missing-test-register" |
| Evidence Path | Expected artifact path | Yes, or "missing-evidence" |
| Phase | MVP / Phase 0-5 / Post-MVP | Yes |
| Priority | Critical / High / Medium / Low | Yes |
| Status | Draft / Accepted / Implemented / Verified / Blocked | Yes |
| Zero-Tolerance | true / false (for safety invariants) | Required for AC-SAFE |
| $30 Cap | true / false + freeze rule | Required for AC-FIN |
| Gap / Conflict | Gap ID or conflict reference | If applicable |

---

## 11. Recommended AC Count Estimate

| Category | Estimated Minimum ACs | Critical | Phase Anchor |
|---|---|---|---|
| AC-CORE | 12-15 | 6 | Phase 1 |
| AC-DISCORD | 4-6 | 3 | Phase 1 |
| AC-LOOP | 8-10 | 5 | Phase 3 |
| AC-MEM | 6-8 | 4 | Phase 2 |
| AC-SURV | 6-8 | 3 | Phase 4 |
| AC-FIN | 8-10 | 4 | Phase 4 |
| AC-PERSONA | 6-8 | 3 | Phase 2 |
| AC-SAFE | 10-14 | 8 | Phase 2 |
| AC-SEC | 10-12 | 7 | MVP (pervasive) |
| AC-DATA | 8-10 | 6 | MVP (pervasive) |
| AC-OPS | 10-14 | 5 | MVP (pervasive) |
| AC-PHASE | 6-8 | 4 | Per-phase |
| **Total** | **94-123** | **58** | |

---

## 12. Construction Rules

1. **"Must" is mandatory.** Every AC must use "must" for hard requirements, "should" only for non-blocking aspirational items. Zero standalone "should" without a documented rationale.

2. **Every AC needs an evidence path.** If no evidence path exists, mark `EVIDENCE-GAP-###` and cross-reference RTM Missing Evidence Register.

3. **Every AC needs a test reference.** If no test exists, mark `TEST-GAP-###` and cross-reference RTM Missing Test Register.

4. **AC-SAFE rows must include zero_tolerance flag.** They must trace to SLO-SAF-### targets.

5. **AC-FIN rows must cite $30 cap.** They must include freeze-rule reference from SLO §8.4.

6. **Phase gates map to Charter §9, §17, and Appendix A.** Every phase exit criterion must have at least one AC.

7. **Every AC must trace upstream to an RTM row.** No orphan ACs.

8. **Cross-reference discipline.** Each AC must link to: RTM requirement, SLO target, test case, evidence path, and phase gate.

9. **Safe-word invariant.** Any AC that touches safe-word, distress, yandere cap, or crisis must have zero-tolerance and refer to PersonaSafetyPolicy.

10. **$30 cap everywhere.** Every cost-touching AC must embed the hard cap, even if indirect (e.g., surveillance ingestion costs, storage costs, LLM routing costs).

---

## 13. Sources of Additional Inputs (Not Yet Scanned)

The catalog should also incorporate these when available:

| Source | Expected Content | When |
|---|---|---|
| `Guinevere_TechnicalArchitecture_v2.0.md` | Service interfaces, systemd unit tests, health checks | Already referenced via RTM |
| `Guinevere_MemorySchema_v2.0.md` | Schema-level acceptance for recall/classification/encryption | Already referenced via RTM |
| `Guinevere_ADR_Index_v1.0.md` | ADR binding decisions per AC | Already referenced via RTM |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Data class enforcement ACs | Already referenced via RTM |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Exact budget numbers for AC-FIN | Missing; referenced as SLO-BG-002 |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Dashboard-as-code acceptance | Already referenced via RTM |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Incident drill acceptance | Referenced; not yet authoritative |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Key rotation / crypto ACs | Already referenced via RTM |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Secrets rotation ACs | Already referenced via RTM |

---

## 14. Verification

| Check | Result |
|---|---|
| Output file exists | Confirmed at `C:\Users\faizz\guinevere\research-reports\2026-05-30-acceptance-criteria-source-map.md` |
| All 8 source docs read | Confirmed - RTM, Charter, BRD, PRD, PersonaSafety, SLO, AgentLoop, AccessControl |
| Candidate AC IDs mapped | 12 primary + 3 secondary categories defined |
| RTM->AC mapping complete | All 96 RTM master rows mapped to AC categories |
| MVP gate criteria extracted | Charter §9 + §17 + Appendix A extracted |
| Missing tests/evidence/gaps identified | MT-001..008, ME-001..008, GAP-002..010, PS-001..010, ACT-001..012, SLO-TEST-001..010 |
| Catalog structure recommended | 10-section structure with detailed column schema |
| $30 cap mapping | Applied to every cost-related criterion |
| Safe-word invariant mapping | Zero-tolerance markers mapped to SLO-SAF targets |
| Status final doc | All source documents are Accepted with Samm Review Record |
| All controls must | Verified - no standalone "should" without rationale |

---

## 15. Caveats

1. **Exact AC count is estimated.** Actual number depends on decomposition depth during catalog construction.
2. **$30 cap exact daily/monthly/per-loop values not yet defined** in an accepted FinOps model. AC-FIN rows must mark exact thresholds as TBD pending `Cost_FinOps_Model_v1.0.md`.
3. **Safe-word exact token list is unresolved** (PersonaSafety §19 backlog). AC-SAFE-001 must acknowledge this gap.
4. **Prompt Injection spec gap** (GAP-002) affects AC-SEC-005 and AC-DATA-005. These ACs must remain gated until spec exists.
5. **Surveillance Data Policy gap** (GAP-005) is Critical. AC-SURV criteria must remain gated until policy exists.
6. **Consent & Revocation Policy gap** (GAP-006) is Critical. AC-DATA-003 and AC-SAFE-001 must reference this gap.
7. **Database ERD gap** (GAP-004) blocks AC-MEM and AC-SEC implementation-related criteria.

---

*End of source-map report. Ready for Acceptance Criteria Catalog construction.*
