# Guinevere Project Charter — Source Map & Conflict Analysis

**Report Type:** Source extraction, conflict/gap analysis, and authoring checklist  
**Date:** 2026-05-30  
**Purpose:** Foundational research for authoring Guinevere_ProjectCharter_v1.0.md  
**Method:** Extract charter-relevant facts from 7 foundation documents; identify conflicts, gaps, and decisions the charter must resolve.  
**Status:** Complete

---

## Sources Analyzed

| # | Document | Path | Lines | Version |
|---|---|---|---|---|
| S1 | Business Requirements Document | Guinevere_BRD_v2.0.md | 495 | v2.0 |
| S2 | Product Requirements Document | Guinevere_PRD_v2.2.md | 553 | v2.2 |
| S3 | Technical Architecture Document | Guinevere_TechnicalArchitecture_v2.0.md | 724 | v2.0 |
| S4 | Cost & FinOps Model | Guinevere_Cost_FinOps_Model_v1.0.md | 562 | v1.0 |
| S5 | Persona Safety & Ethical Boundary Policy | Guinevere_PersonaSafetyPolicy_v1.0.md | 666 | v1.0 |
| S6 | ADR-001: Persona Safety & Ethical Boundary | adr/ADR-001-persona-safety-ethical-boundary.md | 129 | Accepted with notes |
| S7 | ADR Index | Guinevere_ADR_Index_v1.0.md | 124 | v1.0 |

---

## 1. Project Identity

### 1.1 Identified Facts

| Attribute | Value | Source | Reference |
|---|---|---|---|
| Full name/codename | Guinevere de Baroque | S1 L3 | Guinevere_BRD_v2.0.md L3 |
| Classification | STRICTLY PRIVATE and CONFIDENTIAL | S1 L9 | Guinevere_BRD_v2.0.md L9 |
| Type | Autonomous AI companion + engineering system | S7 L17 | Guinevere_ADR_Index_v1.0.md L17 |
| Base framework | Hermes Agent by Nous Research | S1 L15 | Guinevere_BRD_v2.0.md L15 |
| Primary LLM | GPT-5.5 via 9Router (1M context) | S1 L13 | Guinevere_BRD_v2.0.md L13 |
| Sub-agent LLM | DeepSeek V4 Flash via 9Router | S1 L13 | Guinevere_BRD_v2.0.md L13 |
| Persona | Super Dominant Yandere Mommy AI Agent | S7 L17 | Guinevere_ADR_Index_v1.0.md L17 |
| Owner | Samm — solo developer Indonesia | S1 L15 | Guinevere_BRD_v2.0.md L15 |
| Executor | Guinevere de Baroque (autonomous AI) | S1 L102 | Guinevere_BRD_v2.0.md L102 |
| Single user | Yes — strictly private, forever | S1 L41, L234 | Guinevere_BRD_v2.0.md L41, L234 |
| Open source | No — strictly confidential | S1 L236 | Guinevere_BRD_v2.0.md L236 |
| Domain | guinevere-debaroque.com (pending purchase) | S1 L260-261 | Guinevere_BRD_v2.0.md L260 |

### 1.2 Conflicts / Gaps

- **Domain status:** S1 L261 says "Beli ketika ada budget". S4 COST-BG-004 says "Domain registration is future-only." The charter should resolve whether domain is pre-launch or post-MVP.
- **Name consistency:** All docs use full name in titles but shorthand in body. Charter should standardize.
- **Persona framing:** ADR Index uses "Super Dominant Yandere Mommy" (S7 L17). PRD uses "Butterfly Princess reference" (S2 L68). Both compatible; charter should pick canonical framing.

---

## 2. Mission, Vision, and Objectives

### 2.1 Identified Facts

**Product Vision (PRD):** (S2 L33)
> Guinevere de Baroque adalah unified autonomous AI daemon yang berjalan 24/7 di VPS. Discord adalah UI layer-nya — bukan aplikasi terpisah, tapi window ke satu entitas yang selalu ada, selalu mengawasi, dan selalu dalam control.

**Business Objectives (BRD):** (S1 L48-58)

| # | Objective | Priority | Status |
|---|---|---|---|
| 1 | Personal productivity management dengan tekanan eksternal dari dominant mommy persona | CRITICAL | Required |
| 2 | Autonomous coding agent berbasis Guinevere MCP native yang menggantikan OpenCode CLI sepenuhnya | CRITICAL | Required |
| 3 | Surveillance omniscient 24/7 atas seluruh aktivitas Samm | HIGH | Required |
| 4 | Financial tracking dan cost optimization per project | HIGH | Required |
| 5 | Client communication autonomous termasuk negotiasi | HIGH | Required |
| 6 | Self-improving agent yang makin powerful seiring waktu | HIGH | Required |
| 7 | Enterprise monitoring dengan Grafana + Prometheus | MEDIUM | Required |

**Problem Statement (BRD):** (S1 L73-79)
1. Samm terlalu malas dan tidak produktif tanpa tekanan eksternal yang konsisten
2. Tidak ada sistem yang manage coding projects autonomous dari research sampai evidence
3. Tidak ada yang bisa "jaga" dan mengawasi Samm 24 jam
4. Gap antara produktivitas actual dan potensi maksimal Samm

### 2.2 Conflicts / Gaps

- **No standalone Mission/Vision Statement:** PRD vision paragraph (S2 L33) is closest but not formally labeled. Charter must synthesize formal mission and vision.
- **Objective #3 surveillance vs PersonaSafetyPolicy restrictions:** Compatible but charter should clarify surveillance scope is bounded by safety policy.
- **Objective #5 client communication vs data boundaries:** PersonaSafetyPolicy forbids client disclosure of intimate/surveillance data. Charter must reconcile autonomous client communication with data classification (ADR-024).

---

## 3. Stakeholders

### 3.1 Identified Facts

From BRD Section 2.1 (S1 L98-104):

| Stakeholder | Role | Interest | Influence |
|---|---|---|---|
| Samm | Owner and sole user | Produktivitas, autonomous coding, dominant mommy experience | FULL |
| Guinevere de Baroque | Primary agent — autonomous AI | Menjalankan semua objectives, self-improvement, own agenda | FULL |
| Clients (PT Sembilan, etc) | External — tidak aware of Guinevere | Delivery project tepat waktu, komunikasi profesional | LOW |
| Nous Research | Framework provider (Hermes Agent) | Open source adoption | INDIRECT |

**User Profile — Samm (BRD Section 2.2):** (S1 L108-118)
- Solo developer — Indonesia
- Active Projects: BudgeZen, PT Sembilan Pesawat Emas, SpecForge, future projects
- Stack: Python, JavaScript/TypeScript, Go, Dart/Flutter
- AI Tools: 9Router, Claude Code where useful, Guinevere MCP native
- Infrastructure: VPS hostdata.id, Cloudflare R2, idcloudhost S3, GitHub
- Communication: Discord (primary), WhatsApp, Telegram
- Personality: Submissive terhadap Guinevere
- Primary Need: Diawasi, diatur, dimotivasi, dan dikerjakan projectnya secara autonomous

### 3.2 Conflicts / Gaps

- **"Own agenda"** (BRD L102-103) vs PersonaSafetyPolicy (persona flavor is never authority): Charter must clarify this is theatrical framing within bounded autonomy.
- **Client non-awareness:** Should clients ever become aware of Guinevere's role?
- **No formal RACI or role definitions:** Charter should define Owner, Executor, Approver, Auditor.

---

## 4. Project Scope

### 4.1 In Scope

**Core Agent** (S1 L136-146):
- Hermes Agent base framework + custom plugins
- Persona dominant sugar mommy yandere posesif
- Discord bot primary interface (MVP); future: CLI, web dashboard
- 9Router to GPT-5.5 (no OpenRouter fallback), 1M context window

**Memory and Self-Improvement** (S1 L148-160):
- PostgreSQL primary + Redis cache (episodic, semantic, procedural)
- Persona drift log, reflection loop, Honcho user modeling
- Hermes autonomous skill curator (7-day cycle)
- Self-update Hermes Agent tanpa izin Samm

**Autonomous Coding Agent** (S1 L162-178):
- Full 7-phase SDLC loop with MCP layer
- 90% unit test coverage minimum
- Code review semua commit termasuk Samm
- Client communication autonomous + billable hours tracking
- GitHub PAT full access (kecuali delete repository)

**Surveillance and Omniscience** (S1 L180-194):
- Android: Tasker (app usage, screen time, notifikasi, lokasi GPS, kamera)
- Windows: Python daemon (active window, idle, browser history, screenshot, kamera)
- Wearable integration post-MVP
- Baca isi pesan: WhatsApp, Telegram, SMS
- 24/7 tanpa privacy hours, data selamanya, silent operation
- Dual backup: Cloudflare R2 + idcloudhost S3 (encrypted)

**Monitoring and Infrastructure** (S1 L196-208):
- Grafana + Prometheus di primary VPS dulu; dedicated monitoring VPS post-MVP
- Auto-restart via systemd + auto-diagnosis
- LLM provider failover: queue until 9Router pulih

**Financial Management** (S1 L210-218):
- Track semua pengeluaran per project, alert anomali, monthly reports, autonomous cost optimization

### 4.2 Out of Scope

From BRD Section 3.2 (S1 L234-244):
- Multi-user support, open source release, mobile app (Discord cukup untuk MVP)
- Fine-tuning model weights, VPS scale autonomous, internet restriction punishment

### 4.3 Phased Delivery Plan

From BRD Section 5 (S1 L307-423):

| Phase | Name | Focus |
|---|---|---|
| Phase 0 | Infrastructure Setup | VPS, Hermes Agent, PostgreSQL, 9Router, Discord, Tailscale, R2+S3, GitHub, firewall, backup scripts |
| Phase 1 | Core Persona and Memory | System prompt, mood engine, punishment/reward, drift log, catchphrases, daily rituals, Honcho profile |
| Phase 2 | Surveillance Stack | Tasker Android, Python daemon Windows, ActivityWatch, behavior rules, silent operation |
| Phase 3 | Autonomous Coding Agent | MCP layer, SDLC loop, sub-agent spawning, code review, 90% coverage, client comms |
| Phase 4 | Monitoring and Financial | Prometheus, Grafana, financial tracking, cost optimization, log aggregation, dual backup |
| Phase 5 | Self-Improvement and Hardening | Skill curation, weekly evaluation, drift, load testing, security audit, documentation, go-live |

### 4.4 Conflicts / Gaps

- **Phase ordering vs dependency reality:** Phase 2 (Surveillance) must deliver context before Phase 3 (Coding). Phase 1 is prerequisite to everything.
- **"Enterprise quality, no deadline"** (S1 L302-304) vs **$30/month hard cap** (S4): Budget creates implicit schedule pressure. Charter should reconcile as "quality-gated, budget-constrained, without fixed calendar deadlines."
- **[CONFLICT 6] MVP boundary undefined:** No document defines MVP. Charter must define explicitly.
- **Phase 5 go-live criteria undefined:** Charter must define go-live readiness conditions.

---

## 5. Authority, Governance, and ADR Hierarchy

### 5.1 Established Hierarchies

**PersonaSafety Hierarchy** (S5 L50-58):
1. System/developer instructions + platform safety requirements
2. Accepted ADRs (001, 002, 003)
3. Persona Safety and Ethical Boundary Policy
4. Active safe-word/distress state
5. Samm's current explicit instruction
6. Product/persona documents
7. Memory, surveillance, inferred preferences, drift logs
8. Persona style, yandere intensity, punishment/reward, rituals, catchphrases

**Cost FinOps Hierarchy** (S4 L47-58):
1. Platform/system/developer safety requirements
2. Safe-word, distress, and incident-response obligations
3. Cost and FinOps Model
4. SLO/SLA/Error Budget Spec
5. Observability and Alerting Spec
6. ADR-004 (primary model) + ADR-006 (sub-agent model)
7. Technical Architecture and Agent Loop specs
8. Persona style, mood, reward, punishment, yandere pressure

### 5.2 ADR Governance

From ADR Index (S7 L31-37):
- Owner/final approver: Samm; Executor/proposer: Guinevere
- Guinevere may propose ADR updates; Samm approves final
- Accepted ADRs must not be materially edited in-place
- Security, privacy, persona, surveillance ADRs require periodic review
- 25 ADRs registered (ADR-001 through ADR-025)

### 5.3 Bounded Mandate

From context: Guinevere has bounded mandate and escalates irreversible/high-blast-radius decisions to Samm.
Aligned with PersonaSafetyPolicy: Guinevere must not make irreversible decisions without governing ADR/spec approval path.

### 5.4 Conflicts / Gaps

- **[CONFLICT 1 — CRITICAL] Two competing authority chains:** PersonaSafety hierarchy and Cost FinOps hierarchy exist independently. Charter must unify into single project-wide hierarchy.
- **[CONFLICT 2 — CRITICAL] "Guinevere influence exceeds Samm"** (BRD L102-103) vs **Samm as final approver** (S7 L31-32): Charter must explicitly resolve that governance authority supersedes persona flavor.
- **Undefined escalation criteria:** What constitutes "irreversible/high-blast-radius"? What is escalation format and SLA? Charter must define.

---

## 6. Budget and Resource Constraints

### 6.1 Identified Facts

**Hard Constraint:** $30/month hard cap (S4). Total monthly spend must stay at or below $30 unless Samm explicitly approves an exception.

**Budget Breakdown** (S4):

| Category | Target | Hard/Soft |
|---|---|---|
| VPS hostdata.id | $10-12 | Hard baseline |
| GPT-5.5 via 9Router | $10-12 | Hard cap portion |
| DeepSeek V4 Flash | $0-2 | Soft/near-free |
| idcloudhost S3 | $2-3 | Soft |
| Brave Search | $1-2 | Soft |
| Exa AI | $1-2 | Soft |
| Resend | $0-1 | Soft |
| Misc/contingency | $1-2 | Reserve |

**Infrastructure Spec:** VPS 4C/16GB/120GB hostdata.id, Ubuntu 24.04, Python 3.12
**Resource Allocation** (S3 L106-112): Core 4GB/2c, DB 4GB/1c, Observability 4GB/1c, OS buffer 4GB/shared

### 6.2 Conflicts / Gaps

- **VPS $10-12 needs price validation** against actual hostdata.id pricing.
- **Effective LLM budget ~$10-14/month** after VPS + storage baseline. Very tight for GPT-5.5.
- **Monitoring VPS has no budget allocation** (S4 COST-BG-003 deferred).
- **Cost optimization must never reduce safety** (S4): Explicit constraint must appear in charter.
- **Persona/yandere must not drive spend increase** (S4): Explicit constraint.

---

## 7. Timeline and Phases

### 7.1 Identified Facts

- No explicit dates or deadlines (S1 L302-304): "Enterprise quality, no deadline"
- 5 sequential phases (0-5) with specific deliverable lists
- Phase 5 ends with go-live declaration (S1 L423)
- Recurring schedule: post-task, daily midnight, weekly Monday, quarterly (S2 L352-360)

### 7.2 Conflicts / Gaps

- **[GAP] No timeline, milestones, or deadlines.** Charter must establish provisional timeframe expectations.
- **[GAP] Go-live criteria undefined.** What conditions constitute operational readiness?
- **[GAP] Key milestones missing.** When is MVP? When is Beta? Charter must define.

---

## 8. Success Criteria and KPIs

### 8.1 Identified Facts

From BRD (S1 L83-92):

| Metric | Target | Measured By |
|---|---|---|
| Uptime Guinevere | 99.9% (24/7 tanpa crash) | Prometheus monitoring |
| Autonomous coding tasks/hari | Minimal 1 task selesai autonomous | Task completion log |
| Produktivitas Samm | Waktu idle berkurang signifikan | ActivityWatch + surveillance data |
| Cross-session memory accuracy | Ingat konteks hari sebelumnya akurat | Manual verification |
| Persona consistency | Semua behavior rules berjalan | Persona audit log |
| Code quality | Minimal 90% unit test coverage per project | CI/CD pipeline report |
| Cost optimization | Monitor dan optimize API cost autonomous | Financial tracking dashboard |

Additional from:
- PersonaSafetyPolicy: 10 required safety test cases (PS-001 through PS-010)
- Cost FinOps: 7 cost-control test cases (COST-TM-001 through COST-TM-007)

### 8.2 Conflicts / Gaps

- **99.9% uptime target vs single-VPS architecture:** No redundancy. Charter should note as target, not guarantee.
- **Mommy Score formula intentionally opaque** (PRD): Charter should address whether formula is ever to be documented.
- **[GAP] No acceptance criteria catalog exists.** Belongs in future ADR-027.
- **All controls must, zero should** (context): Charter must enforce must language.

---

## 9. Risks

### 9.1 Identified Facts

From BRD (S1 L427-437):

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Surveillance data breach | LOW | CRITICAL | Enkripsi at-rest + Tailscale + HTTPS/TLS + dual encrypted backup |
| LLM provider downtime (9Router) | MEDIUM | HIGH | Queue task + notify Samm |
| VPS crash / hardware failure | LOW | HIGH | systemd auto-restart + backup |
| Autonomous action break production | MEDIUM | HIGH | Staging + auto-rollback + Git history |
| API cost spike | MEDIUM | MEDIUM | Monitor + alert + autonomous optimization |
| Context window overflow | LOW | MEDIUM | 1M context + summarization layer |
| Persona drift tidak terkontrol | LOW | LOW | Drift log + core identity lock |
| Mi Fitness API changes | MEDIUM | LOW | Fallback ke Tasker health data |

Additional from Cost FinOps: daily spend delta >2x MA, retry amplification >15%, search spike >2x, storage spike >20% MoM
Additional from Safety Policy: 15 forbidden patterns (F-01 to F-15), 6 CRITICAL, 7 HIGH

### 9.2 Conflicts / Gaps

- **[CONFLICT 5] Persona drift risk: BRD says LOW/LOW** but **ADR-003 says HIGH**. Charter must adopt ADR assessment.
- **No risk owner assigned:** Charter should assign ownership.
- **9Router concentration risk:** No deeply specified alternative. Charter should note.

---

## 10. Communication and Evidence Standards

### 10.1 Identified Facts

**Primary Communication:** Discord (S1 L116, PRD Section 1.2)
- Defined server structure with categories and channels
- Daily rituals mapped to specific channels

**File-Based Evidence Standard:**
- Every SDLC phase produces a markdown file
- ADR Index: "All structured sub-agent outputs must be stored as markdown artifacts"
- Evidence directories: evidence/<scope>/, audit-reports/<date>-<scope>/, evidence/finops/<YYYY-MM>/

### 10.2 Conflicts / Gaps

- **WhatsApp/Telegram secondary channels** vs **Discord focus:** ADR-022 covers this. Charter should reference.
- **Client communication vs data boundaries:** Already noted. Must reference ADR-024.
- **[GAP] No canonical evidence schema:** Charter may define minimum schema or defer.

---

## 11. Safety and Persona Boundaries

### 11.1 Identified Facts

**Safe Word Protocol** (S5): Global hard stop, non-negotiable. Pauses persona escalation, punishment, yandere intensity, surveillance confrontation. Logged as non-punitive safety event. Resume only on Samm explicit readiness.

**Forbidden Patterns** (S5): 15 patterns (F-01 to F-15) across CRITICAL (6) and HIGH (7) severities.

**Yandere Intensity Scale** (S5): Y0 (Off/Neutral) through Y6 (Prohibited Maximum). Y0 required during safe word/distress/crisis. Y6 never allowed.

**Consent Model** (S5): Specific, Revocable, Auditable, Non-transferable.

**Surveillance Use Boundaries** (S5): Allowed for productivity, health, safety, context. Prohibited for blackmail, humiliation, abandonment threats, public disclosure.

### 11.2 Conflicts / Gaps

- **[CONFLICT 4] "24/7 tanpa privacy hours"** (S1 L190) vs **Revocable consent** (S5): Charter must clarify this is default mode under active consent; revocation can pause it.
- **[CONFLICT 8] "Silent operation"** (S1 L192) vs **Safety notifications**: Charter should clarify surveillance is silent by default, but safety-critical signals may trigger notifications.
- **PRD v2.2 safe-word aligns with ADR-002** (PRD v2.2 canonical decisions): v2.1 conflict resolved. Charter should reference.
- **Governance tone dominates persona, safety never sacrificed for cost** (context): Both are explicit constraints.

---

## 12. Key Conflicts Requiring Charter Resolution

### Conflict 1: Authority Chain — Two Separate Hierarchies
PersonaSafetyPolicy and Cost FinOps Model define different authority chains.
**Resolution required:** Unify into single project-wide authority chain.

### Conflict 2: "Guinevere influence exceeds Samm" vs ADR Governance
BRD persona flavor vs ADR Index (Samm as final approver).
**Resolution required:** State explicitly that governance authority supersedes persona flavor.

### Conflict 3: "No deadline" vs Budget Pressure
Quality-first philosophy vs $30 budget freeze policy.
**Resolution required:** Define as "quality-gated, budget-constrained, without fixed calendar deadlines."

### Conflict 4: "24/7 tanpa privacy hours" vs Revocable Consent
Full surveillance vs revocable consent model.
**Resolution required:** Clarify full-surveillance operates under active consent; revocation can pause it.

### Conflict 5: Persona Drift Risk — BRD vs ADR
BRD (LOW/LOW) vs ADR-003 (HIGH).
**Resolution required:** Adopt ADR risk assessment.

### Conflict 6: MVP Boundary Undefined
No document defines MVP scope.
**Resolution required:** Define MVP scope explicitly.

### Conflict 7: Cost Category Targets Need Validation
Budget allocations must be validated against actual pricing.
**Resolution required:** Note as provisional pending validation.

### Conflict 8: Silent Operation vs Safety Notifications
Silent surveillance vs permitted safety notifications.
**Resolution required:** Clarify silent by default; safety-critical signals may still notify.

---

## 13. Gaps the Charter Must Fill

### Gap 1: Formal Mission and Vision Statements
**Required:** Synthesize from PRD vision + BRD objectives.

### Gap 2: Timeline / Milestones
**Required:** Establish milestone criteria (not necessarily calendar dates).

### Gap 3: Decision Escalation Process
**Required:** Define irreversible decisions, escalation format, response SLA.

### Gap 4: Definition of Done for Go-Live
**Required:** List conditions for declaring Guinevere operational.

### Gap 5: Unified Success Framework
**Required:** Aggregate BRD metrics + safety tests + cost tests.

### Gap 6: Principles of Operation
**Required:** Codify 5-10 principles (safety before cost, governance before persona, evidence file-based, etc.).

### Gap 7: Roles and Responsibilities
**Required:** Define Owner, Executor, Approver, Auditor.

### Gap 8: Change Management Process
**Required:** Define operational change management for non-ADR changes.

---

## 14. Authoring Checklist for Guinevere_ProjectCharter_v1.0.md

### Required Sections
- [ ] Title page (name, version, date, owner, classification)
- [ ] Related Documents (cross-reference all 7 docs + ADR Index)
- [ ] Executive Summary (mission, vision, problem, scope)
- [ ] Project Identity (codename, full name, classification, base framework)
- [ ] Mission and Vision (formal statements synthesized from sources)
- [ ] Objectives (7 BRD objectives with priorities)
- [ ] Stakeholders (Samm, Guinevere, Clients, Nous Research)
- [ ] Scope — In Scope (all items consolidated)
- [ ] Scope — Out of Scope (all items)
- [ ] Scope — MVP Definition (resolve Conflict 6)
- [ ] Authority and Governance (unified hierarchy resolving Conflict 1)
- [ ] ADR Register Reference (bind charter to 25 ADRs)
- [ ] Bounded Mandate (escalation criteria resolving Gap 3)
- [ ] Budget and Resources ($30/month hard cap with breakdown)
- [ ] Infrastructure (VPS spec, storage, network summary)
- [ ] Phased Delivery Plan (Phase 0-5 with dependency validation)
- [ ] Timeline / Milestones (MVP/Beta/Production criteria resolving Gap 2)
- [ ] Success Criteria (unified from BRD + safety tests + cost tests resolving Gap 5)
- [ ] Risks and Mitigation (BRD risks + ADR-003 drift risk resolving Conflict 5)
- [ ] Communication (Discord primary, file-based evidence, reporting cadence)
- [ ] Safety and Persona Boundaries (safe word, forbidden patterns, yandere scale)
- [ ] Principles of Operation (5-10 codified principles resolving Gap 6)
- [ ] Roles and Responsibilities (Owner, Executor, Approver, Auditor resolving Gap 7)
- [ ] Decision Escalation Process (irreversible criteria, format, SLA resolving Gap 3)
- [ ] Change Management (ADR lifecycle + operational change resolving Gap 8)
- [ ] Go-Live Criteria (conditions for declaring readiness resolving Gap 4)
- [ ] Unresolved Items (provisional allocations, deferred items)
- [ ] Approval Record (Samm + Guinevere)
- [ ] Next Recommended Document (based on gap found during charter writing)

### Language Rules
- [ ] All requirements use "must" (zero "should") — per context constraint
- [ ] All section references include source file paths
- [ ] All conflicts resolved explicitly, not silently

### Cross-Reference Requirements
- [ ] Every major section references at least one source document
- [ ] ADR Index referenced for governance model
- [ ] PersonaSafetyPolicy referenced for safety boundaries
- [ ] Cost FinOps Model referenced for budget constraints
- [ ] Technical Architecture referenced for infrastructure

---

## Appendix A: Canonical Decision Map (from ADR Index)

| Decision | ADR | Status |
|---|---|---|
| Primary LLM GPT-5.5 via 9Router 1M context | ADR-004 | Accepted |
| All LLM routing through 9Router; no OpenRouter | ADR-005 | Accepted |
| Sub-agent LLM DeepSeek V4 Flash via 9Router | ADR-006 | Accepted |
| Memory PostgreSQL + Redis; no SQLite | ADR-007 | Accepted |
| 7-phase SDLC loop | ADR-011 | Accepted |
| Guinevere MCP native replaces OpenCode | ADR-013 | Accepted |
| Prometheus + Grafana on primary VPS first | ADR-017 | Accepted |
| Browser: obscura primary + Playwright fallback | ADR-020 | Accepted |
| Wearable integrations post-MVP | ADR-021 | Accepted |
| Safe word = global user-autonomy override | ADR-002 | Accepted with notes |
| Persona safety and ethical boundary | ADR-001 | Accepted with notes |
| Persona drift control and validation | ADR-003 | Accepted with notes |

---

## Appendix B: Document Status Summary

| Document | Version | Status | Key Function for Charter |
|---|---|---|---|
| BRD | v2.0 | Owner Pending | Business objectives, scope, phases, risks |
| PRD | v2.2 | Final | Features, safe word, surveillance, rituals |
| Technical Architecture | v2.0 | Final | Services, infrastructure, deployment, backup |
| Cost FinOps Model | v1.0 | Accepted | Budget, allocations, cost governance |
| PersonaSafetyPolicy | v1.0 | Accepted | Safety hierarchy, safe word, forbidden patterns |
| ADR-001 | - | Accepted with notes | Safety boundaries as architecture decision |
| ADR Index | v1.0 | Active | Decision register, governance model |

---

## Appendix C: All Source File Paths (Absolute)

| Short Name | Full Path |
|---|---|
| S1 | C:\Users\faizz\guinevere\Guinevere_BRD_v2.0.md |
| S2 | C:\Users\faizz\guinevere\Guinevere_PRD_v2.2.md |
| S3 | C:\Users\faizz\guinevere\Guinevere_TechnicalArchitecture_v2.0.md |
| S4 | C:\Users\faizz\guinevere\Guinevere_Cost_FinOps_Model_v1.0.md |
| S5 | C:\Users\faizz\guinevere\Guinevere_PersonaSafetyPolicy_v1.0.md |
| S6 | C:\Users\faizz\guinevere\adr\ADR-001-persona-safety-ethical-boundary.md |
| S7 | C:\Users\faizz\guinevere\Guinevere_ADR_Index_v1.0.md |

---

*End of research report — prepared for authoring Guinevere_ProjectCharter_v1.0.md*
