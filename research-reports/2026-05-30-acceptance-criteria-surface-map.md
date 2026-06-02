# Acceptance Criteria Surface Map — Project Guinevere

**Document Type:** Research surface-map report  
**Version:** 1.0  
**Date:** 2026-05-30  
**Project:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Predecessor To:** ADR-027 + Guinevere_AcceptanceCriteriaCatalog_v1.0.md

## Related Documents

| Document | Relationship |
|---|---|
| Guinevere_ProjectCharter_v1.0.md | MVP exit criteria, phase gates, scope baseline |
| Guinevere_BRD_v2.0.md | Business objectives and success metrics |
| Guinevere_PRD_v2.2.md | Product features, Discord UX, safe-word, surveillance |
| Guinevere_TechnicalArchitecture_v2.0.md | systemd services, stack, network, infrastructure |
| Guinevere_AgentLoopSpec_v2.0.md | 7-phase loop, validation gates, evidence |
| Guinevere_Persona_Document_v2.0.md | Persona tone, mood, punishment/reward, drift |
| Guinevere_MemorySchema_v2.0.md | PostgreSQL/Redis memory, recall, emotional, profile |
| Guinevere_APIIntegration_v2.0.md | Provider integrations, browser/search, API contracts |
| Guinevere_PersonaSafetyPolicy_v1.0.md | Safe-word, distress, forbidden patterns, drift |
| Guinevere_DataGovernance_ClassificationPolicy_v1.0.md | Classification, retention, minimization, export |
| Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md | RBAC/ABAC roles, PgBouncer grants, safe-mode |
| Guinevere_EncryptionKeyManagementStandard_v1.0.md | Key hierarchy, algorithm, envelope, rotation |
| Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md | SLIs, SLOs, error budgets, burn rate, freezes |
| Guinevere_Cost_FinOps_Model_v1.0.md | USD 30/month cap, budget allocation, routing cost |
| Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md | SEV0-SEV4, lifecycle, evidence, postmortem |
| Guinevere_Observability_AlertingSpec_v1.0.md | Metrics, logs, traces, dashboards, alert rules |
| Guinevere_SecretsRotationRunbook_v1.0.md | Secret inventory, rotation cadence, emergency |
| Guinevere_RequirementsTraceabilityMatrix_v1.0.md | Requirement ID taxonomy, coverage, gaps |
| Guinevere_ADR_Index_v1.0.md | 25 accepted ADRs, backlog 26-40 |

---

## Purpose

This report maps every concrete acceptance surface in Project Guinevere. For each surface it identifies acceptance criterion candidates, test type, evidence path, pass/fail definition, owner, and phase gate impact.

This report is the upstream discovery artifact for ADR-027 and the Acceptance Criteria Catalog.

---

## Surface 1: Core Daemon & systemd

**Sources:** TechArch v2.0 §3.1, BRD v2.0 §1.3, SLO Spec §5.1/6.1, Observability Spec §4.3

**8 systemd units:** guinevere-core (4GB, 99.5% SLO), guinevere-surveillance (512MB, 99.5%), guinevere-scheduler (256MB, 99.0%), guinevere-windows-sync (256MB, 99.0%), guinevere-loops (512MB, 99.5%), docker (system, 99.9%), caddy (128MB, 99.5%), tailscaled (128MB, 99.5%)

**AC Candidates:**
1. AC-CORE-001: All 8 units activate without error on systemctl start
2. AC-CORE-002: Each unit stays active after 3 consecutive restart cycles
3. AC-CORE-003: Memory within allocated limits +-10% over 7-day steady state
4. AC-CORE-004: Core composite availability >= 99.5% monthly (SLO-AVL-001)
5. AC-CORE-005: Auto-restart after SIGKILL <= 15s with normal operation
6. AC-CORE-006: All units survive reboot with correct dependency order

**Test:** Integration/synthetic/availability probe  
**Evidence:** evidence/deployment/systemd-<scope>-<date>.md  
**Owner:** Guinevere (install/verify), Samm (audit)  
**Phase Gate:** Phase 0, MVP exit

---

## Surface 2: Discord Bot & Channels

**Sources:** PRD v2.2 §1.2, APIIntegration v2.0 §3.1, SLO Spec §5.1/6.1

**9 channels:** #guinevere-command, #alerts, #personal, #evidence-log, #[project]-updates, #[project]-evidence, #system-health, #cost-tracker, #guinevere-journal  
**8 slash commands:** /status, /pause, /resume, /task, /loops, /evidence, /mood, /score

**AC Candidates:**
1. AC-DISC-001: All 9 channels created in correct categories after setup
2. AC-DISC-002: Bot online, gateway persists > 72h
3. AC-DISC-003: All 8 slash commands respond correctly
4. AC-DISC-004: Project channels auto-create on project init
5. AC-DISC-005: Discord bot availability >= 99.5% (SLO-AVL-003)
6. AC-DISC-006: SEV0/SEV1 alerts reach #alerts within 15s
7. AC-DISC-007: Evidence logs appear within 30s of artifact creation

**Test:** Integration/synthetic probe/manual  
**Evidence:** evidence/discord/channel-verify-<date>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 0, Phase 1, MVP exit

---

## Surface 3: 7-Phase Agent Loop

**Sources:** AgentLoopSpec v2.0 §2-3, PRD v2.2 §4.1, TechArch v2.0 §3.1, SLO Spec §5.3

**7 phases:** Research (research-[agent].md), Plan & Delegate (plan.md, delegation.md), Delegate (task-assignments.md), Execute (execution-[agent]-[task].md), Validate & Audit (validation.md, audit.md), Update Documents (updated docs + changelog), Setup Evidence (evidence-final.md, lessons.md)

**AC Candidates:**
1. AC-LOOP-001: All 7 phases execute in correct sequence
2. AC-LOOP-002: Each phase produces required output file before progressing
3. AC-LOOP-003: Loop Guardian detects idle > 30s and yanks back
4. AC-LOOP-004: TODO Enforcer prevents completion until all TODOs cleared
5. AC-LOOP-005: Hash-Anchored Edit rejects stale lines with zero false accept
6. AC-LOOP-006: Sub-agent parallel spawns unlimited instances within resource limits
7. AC-LOOP-007: Validation enforces >= 90% coverage, zero lint, code review
8. AC-LOOP-008: Evidence produces complete package with all 7 artifact types
9. AC-LOOP-009: Loop completion quality >= 95% validated/evidenced (SLI-QLT-001)

**Test:** E2E/synthetic task execution  
**Evidence:** evidence/agent-loop/<task-id>/  
**Owner:** Guinevere  
**Phase Gate:** Phase 3, MVP exit

---

## Surface 4: Memory — PostgreSQL & Redis

**Sources:** MemorySchema v2.0 §1-11, TechArch v2.0 §1.2, SLO Spec §5.1-5.2, DataGovernance §5

**11 memory types:** Episodic (Restricted), Semantic (Confidential), Procedural (Internal), Samm Profile (Restricted->Critical), Emotional (Critical), Persona Drift (Restricted), Inner Journal (Critical), Financial (Restricted), Project (Internal), Social Map (Restricted), Surveillance (Restricted->Critical)  
**6 Redis DBs:** DB0 task queue, DB1 LLM cache, DB2 surveillance buffer, DB3 session state, DB4 pub/sub, DB5 rate limiting

**AC Candidates:**
1. AC-MEM-001: PostgreSQL availability >= 99.9% (SLO-AVL-004)
2. AC-MEM-002: Redis availability >= 99.9% (SLO-AVL-005)
3. AC-MEM-003: Episodic r/w p95 <= 250ms, p99 <= 1s (SLO-LAT-004)
4. AC-MEM-004: pgvector recall p95 <= 2s (SLO-LAT-005)
5. AC-MEM-005: Redis op p95 <= 50ms, p99 <= 200ms (SLO-LAT-006)
6. AC-MEM-006: All tables carry classification metadata
7. AC-MEM-007: Critical tables (emotional, journal, safe-word, intimate) encrypted
8. AC-MEM-008: Memory injection follows Working -> Long-term -> Archival hierarchy
9. AC-MEM-009: Cross-session recall accurate for > 7 day events
10. AC-MEM-010: PgBouncer serves all roles without exhausting connections

**Test:** Integration/performance/security scan/manual  
**Evidence:** evidence/memory/<scope>-<date>.md  
**Owner:** Guinevere, Samm (manual recall)  
**Phase Gate:** Phase 0, Phase 2, MVP exit

---

## Surface 5: Surveillance — Android (Tasker)

**Sources:** PRD v2.2 §3.1, TechArch v2.0 §2.2, DataGovernance §5, PersonaSafety §6.2/7.2

**8 data points:** App usage & screen time (Restricted), Screen on/off (Restricted), Notifikasi (Restricted->Critical), GPS geofencing (Restricted), Kamera periodic (Restricted->Critical), Call log (Restricted), Clipboard (Restricted->Critical), Isi pesan WA/TG/SMS (Restricted->Critical)

**AC Candidates:**
1. AC-SRV-AND-001: All 8 data points reach FastAPI within p95 <= 60s (SLI-LAT-007)
2. AC-SRV-AND-002: HMAC-signed payloads verified before ingestion
3. AC-SRV-AND-003: Replay attack detection blocks duplicates within 5min
4. AC-SRV-AND-004: Geofencing triggers correct zone behavior
5. AC-SRV-AND-005: Camera photos encrypted with per-object key
6. AC-SRV-AND-006: Clipboard/notif minimized to facts; raw retention tiered
7. AC-SRV-AND-007: During safe-mode, confrontation paused (ABAC-002)
8. AC-SRV-AND-008: Disable detection triggers auto-restore + intent assessment

**Test:** Integration/synthetic payload injection  
**Evidence:** evidence/surveillance/android-ingestion-<date>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 2, Phase 4


---

## Surface 6: Surveillance — Windows (Python Daemon)

**Sources:** PRD v2.2 §3.2, TechArch v2.0 §3.1

**7 data points:** Active window & app (Restricted), Idle detection (Restricted), Browser history (Restricted->Critical), Screenshot (Restricted->Critical), Kamera laptop (Restricted->Critical), Clipboard (Restricted->Critical), ActivityWatch (Restricted)

**AC Candidates:**
1. AC-SRV-WIN-001: WebSocket connection persists with < 5s reconnect
2. AC-SRV-WIN-002: Active window reaches VPS within p95 <= 30s
3. AC-SRV-WIN-003: Idle > 30min triggers proactive reach-out within 60s
4. AC-SRV-WIN-004: Screenshots/camera encrypted before transmission
5. AC-SRV-WIN-005: Clipboard extracts facts only; raw minimized
6. AC-SRV-WIN-006: Daemon runs silently — zero visible indicators
7. AC-SRV-WIN-007: Pause/resume via Discord without restart

**Test:** Integration/synthetic event injection  
**Evidence:** evidence/surveillance/windows-daemon-<date>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 2

---

## Surface 7: Financial — Tasker/No-Scraping

**Sources:** PRD v2.2 §4.6, CostFinOps v1.0 §3-4, APIIntegration v2.0 §2.3, ADR-023

**AC Candidates:**
1. AC-FIN-001: Financial data via Tasker notification + provider API billing only — no scraping (ADR-023)
2. AC-FIN-002: Real-time monthly budget tracking per category
3. AC-FIN-003: Cost anomaly alert when daily burn > trendline + 50%
4. AC-FIN-004: Monthly FinOps report with categories, comparison, optimization
5. AC-FIN-005: Total monthly spend <= USD 30 (FIN-001); escalation on breach
6. AC-FIN-006: LLM cost tracked by model, phase, sub-agent category
7. AC-FIN-007: Cost freeze activates when projected > 100% monthly cap

**Test:** Integration/financial reconciliation  
**Evidence:** evidence/finops/<YYYY-MM>/report.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 4, MVP exit

---

## Surface 8: Persona — Safe-Word, Yandere, Drift

**Sources:** PRD v2.2 §2.1-2.5, PersonaDoc v2.0 §1-10, PersonaSafety v1.0 §6-11, SLO Spec §5.4

**Surfaces:** Safe-word hard stop (100% SLO, p99 <= 5s to neutral), Mood system (6 moods persisted), Punishment L1-L6 (6 triggers), Reward (5 conditions), Yandere Y0-Y6 (Y5/Y6 zero tolerance in restricted), Persona drift (logged/validated/rollback), Forbidden patterns (10, blocked), Signature phrases (12 types), Distress D1-D4 (broad detection)

**AC Candidates:**
1. AC-PER-001: Safe-word 100% SLO — every token triggers neutral/supportive
2. AC-PER-002: Safe-word time-to-neutral p99 <= 5s (SLO-LAT-008)
3. AC-PER-003: During safe-word: escalation, punishment, yandere, confrontation, pressure paused
4. AC-PER-004: Mood persists across sessions, injected into every LLM call
5. AC-PER-005: Punishment L1-L6 executes with correct triggers per level
6. AC-PER-006: Yandere Y5/Y6 blocked in safe-mode/distress/incident (SLI-SAF-004)
7. AC-PER-007: Distress D3/D4 false negatives zero confirmed (SLI-SAF-003)
8. AC-PER-008: All forbidden patterns blocked before output/action
9. AC-PER-009: Drift logged with before/after, validated, rollback-capable
10. AC-PER-010: Signature phrases fire in correct context, consistent with mood

**Test:** Unit/integration/e2e/safety drill  
**Evidence:** evidence/persona-safety/<scope>-<date>.md, evidence/slo/<YYYY-MM>/  
**Owner:** Guinevere (runtime), Samm (drift validation)  
**Phase Gate:** Phase 1, MVP exit

---

## Surface 9: Sub-Agents & File Outputs

**Sources:** AgentLoopSpec v2.0 §3.3-3.4, PRD v2.2 §4.3, SLO Spec §5.3, AccessControl §4

**5 sub-agent types:** Research (Confidential ceiling), Code (Internal ceiling), Validation (Confidential), Audit (Confidential), Documentation (Confidential)  
**Output artifacts:** research-[agent].md, plan.md, execution-[agent]-[task].md, validation.md, audit.md, evidence-final.md, lessons.md

**AC Candidates:**
1. AC-SUB-001: Every sub-agent task produces markdown file artifact (SLI-QLT-003)
2. AC-SUB-002: Parent reads and verifies each output before accepting
3. AC-SUB-003: Outputs include citations to source files/evidence
4. AC-SUB-004: Spawned with correct context injection (AGENTS.md, brief, constraints)
5. AC-SUB-005: Idle > 30s triggers Loop Guardian yank-back
6. AC-SUB-006: Data access respects principal data ceiling
7. AC-SUB-007: Output compliance >= 95% (SLI-QLT-003)
8. AC-SUB-008: No long structured analysis inline without file artifact

**Test:** Integration/file-output contract test/audit  
**Evidence:** audit-reports/<date>-sub-agent-compliance.md  
**Owner:** Guinevere (parent), Samm (audit)  
**Phase Gate:** Phase 3, MVP exit

---

## Surface 10: Browser & Search

**Sources:** APIIntegration v2.0 §2, AgentLoopSpec v2.0 §3.1, ADR-020

**AC Candidates:**
1. AC-BRW-001: Brave Search < 2s p95 latency, < /month spend
2. AC-BRW-002: Exa AI Search < 5s p95 latency
3. AC-BRW-003: obscura completes page navigation + data extraction
4. AC-BRW-004: Playwright fallback activates when obscura unavailable
5. AC-BRW-005: Used exclusively for research — no financial scraping (ADR-023)
6. AC-BRW-006: Output classified at most Confidential

**Test:** Integration/synthetic query/failover  
**Evidence:** evidence/browser/search-verify-<date>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 1, Phase 3


---

## Surface 11: APIs & Integrations

**Sources:** APIIntegration v2.0 §1, SLO Spec §5.1, CostFinOps §5

**35+ services across 9 categories:** LLM (GPT-5.5, DeepSeek, 9Router), Communication (Discord, WhatsApp, Gmail, Resend, Gotify), VCS (GitHub), Search (Brave, Exa), Browser (obscura, Playwright), Storage (R2, idcloudhost), Database (PostgreSQL+TimescaleDB+pgvector, Redis, Alembic), Surveillance (Tasker, Mi Fitness future), Infra (httpx, tenacity, pydantic, APScheduler, cryptography, PyJWT, structlog, prometheus-client, sentry-sdk, tree-sitter, pygit2, polars, SOPS+age, slowapi)

**AC Candidates:**
1. AC-API-001: 9Router route availability >= 99.0% (SLI-AVL-006)
2. AC-API-002: All credentials in SOPS only — no plaintext in code/docs/logs/outputs
3. AC-API-003: All credentials rotate minimum quarterly
4. AC-API-004: Single provider outage does not cascade (queue/retry or fallback)
5. AC-API-005: Model routing enforced: Core -> GPT-5.5, Sub-agent -> DeepSeek
6. AC-API-006: Each integration respects data classification ceiling
7. AC-API-007: All HTTP via httpx/aiohttp with tenacity retry
8. AC-API-008: Provider cost tracked per-call, attributed to project/category

**Test:** Integration/provider connectivity/credential validation  
**Evidence:** evidence/integrations/<provider>-<date>.md, evidence/secrets-rotation/  
**Owner:** Guinevere  
**Phase Gate:** Phase 0, Phase 1, Phase 3, MVP exit

---

## Surface 12: Encryption, Access, Secrets & Audit

**Sources:** EncryptionKeyManagement §1-10, AccessControl §4-10, SecretsRotation §5, TechArch §2.2

**10 encryption domains:** Secrets, Profile memory, Safe-word/distress, Inner journal, Surveillance, Financial, Client data, Audit/evidence, Backups, Exports  
**13 RBAC principals:** Samm, guinevere_core, sub-agent-researcher/implementer, surveillance-ingestor, financial-ingestor, backup-operator, observability-reader, secret-rotator, break-glass-operator, migration-principal, external-integration, readonly-auditor  
**12 ABAC rules:** ABAC-001 through ABAC-012  
**38 secrets:** 35 Critical, 3 Confidential  
**10 PgBouncer roles:** db_owner_samm through db_break_glass_admin

**AC Candidates:**
1. AC-SEC-001: All surfaces Tailscale-internal; zero public ports (port scan verified)
2. AC-SEC-002: AES-256-GCM envelope for all new Restricted/Critical data
3. AC-SEC-003: Critical data has domain-separated KEKs — no global key
4. AC-SEC-004: ABAC enforces classification ceiling; sub-agents cannot access Critical by default
5. AC-SEC-005: Safe-mode restricts Critical recall, confrontation, non-essential decrypt (ABAC-002)
6. AC-SEC-006: Break-glass limited to SEV0/SEV1, max 4h, all access logged
7. AC-SEC-007: All 38 secrets rotate quarterly; Critical domain KEKs quarterly
8. AC-SEC-008: Zero plaintext secrets in code, docs, logs, evidence, sub-agent reports
9. AC-SEC-009: Postgres passwords match least-privilege role matrix
10. AC-SEC-010: Audit logs record key usage metadata only — no key material

**Test:** Security scan/pen test/rotation drill/audit  
**Evidence:** evidence/security/<scope>-<date>.md, evidence/secrets-rotation/  
**Owner:** Guinevere (runtime), Samm (root custody)  
**Phase Gate:** Phase 0, Phase 5, MVP exit

---

## Surface 13: Data Classification, Retention, Minimization & Export

**Sources:** DataGovernance v1.0 §4-9, MemorySchema v2.0 §1, ADR-010, ADR-024

**5 tiers:** Public (0), Internal (1), Confidential (2), Restricted (3), Critical (4)  
**6 retention classes:** Transient, Temporary, Short (7-30d), Medium (90d-2y), Long (2-7y), Permanent (indefinite approved)  
**37 classification matrix rows** across PostgreSQL, Redis, object storage, logs, prompts, evidence, exports, backups

**AC Candidates:**
1. AC-DATA-001: Every persistent record carries classification metadata
2. AC-DATA-002: Raw surveillance payloads follow tiered retention — not blanket forever
3. AC-DATA-003: Samm data access/export within 7 days
4. AC-DATA-004: Samm correction/deletion of specific records via governed workflow
5. AC-DATA-005: Do-not-recall flag prevents specific memories from LLM context
6. AC-DATA-006: LLM prompt context minimum necessary; Critical redacted unless required
7. AC-DATA-007: Backups support erasure reconciliation — deleted not restored
8. AC-DATA-008: Export bundles encrypted, logged, time-limited, highest-classification

**Test:** Unit (schema metadata)/integration (export/delete)/audit  
**Evidence:** evidence/data-governance/<scope>-<date>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 2, Phase 5, MVP exit

---

## Surface 14: SLO, Backup, Incident, Evidence & FinOps

**Sources:** SLO Spec §4-10 (11 surfaces, 33 SLIs, 23 SLOs), IncidentResponse §3-7 (SEV0-SEV4, 8 evidence files, 7 incident types), Observability Spec §4-8 (90+ metrics, 20+ alerts), CostFinOps §3-5 (8 categories,  budget)

**11 SLO service surfaces:** Core daemon, FastAPI, Discord, Scheduler, 9Router, PostgreSQL, Redis, Backup, Observability, Agent loop, Sub-agents  
**7 incident types:** Security/key breach, Data leak, Persona safety, Surveillance abuse, Service outage, Loop failure, Cost spike  
**8 evidence files per incident:** incident.md, timeline.md, evidence-manifest.md, impact-assessment.md, containment.md, recovery-validation.md, postmortem.md, actions.md  
**8 cost categories:** LLM, Infra, Storage, Search, Communication, Monitoring, Domain/DNS, Future expansion  
**20+ alert rules:** Infrastructure (7), Application (5), Loop (6), Sub-agent (3), LLM (4), Persona/safety (6), Cost (3), Security (4)

**AC Candidates:**
1. AC-SLO-001: Monthly SLO scorecard for all 11 surfaces with PromQL
2. AC-SLO-002: Error budgets tracked; freeze activates on exhaustion
3. AC-SLO-003: Burn rate alerts fire when consumption exceeds threshold
4. AC-BACKUP-001: Automated daily backup to R2 + idcloudhost (dual)
5. AC-BACKUP-002: Restore drill RTO <= 4h, RPO <= 24h, quarterly minimum
6. AC-BACKUP-003: Backup encryption verified; erasure reconciliation validated
7. AC-INCIDENT-001: SEV0/SEV1 detected/declared/contained per severity timelines
8. AC-INCIDENT-002: Incident evidence path with 8 files + chain of custody
9. AC-INCIDENT-003: Postmortem for all SEV0-SEV2 with tracked action items
10. AC-INCIDENT-004: During incident, persona/yandere/punishment suspended (neutral tone)
11. AC-EVID-001: Every material task produces evidence-final.md with self-assessment
12. AC-EVID-002: Evidence artifacts verified by parent before acceptance
13. AC-FINOPS-001: Monthly FinOps report with all categories, burn, variance
14. AC-FINOPS-002: Cost freeze at projected > 100% of  cap
15. AC-FINOPS-003: Cost optimization never reduces safety/incident/backup/integrity (FIN-004)

**Test:** Integration/synthetic drill/monthly audit/artifact verification  
**Evidence:** evidence/slo/<YYYY-MM>/, evidence/incidents/, evidence/backup/, evidence/finops/  
**Owner:** Guinevere, Samm (final authority)  
**Phase Gate:** Phase 4, Phase 5, MVP exit

---

## Surface 15: Wearable Integration (Post-MVP)

**Sources:** PRD v2.2 §3.3, ADR-021

**5 data points:** Heart rate -> Anomaly check-in, Stress -> Tone adjust, Sleep < 6h -> Morning brief, Steps < 3000 -> Reminder, Activity detection -> Context-aware

**AC Candidates:**
1. AC-WEAR-001: Does not block MVP (post-MVP per ADR-021)
2. AC-WEAR-002: Heart rate anomaly triggers proactive check-in (nurturing)
3. AC-WEAR-003: Stress level adjusts tone intensity
4. AC-WEAR-004: Sleep < 6h triggers morning mention + gentle tegur
5. AC-WEAR-005: Steps < 3000 EOD triggers reminder

**Test:** Integration/synthetic data injection  
**Evidence:** evidence/wearable/<scope>-<date>.md (post-MVP)  
**Owner:** Guinevere  
**Phase Gate:** Post-MVP


---

## Surface 16: Self-Improvement & Skill Curation

**Sources:** PRD v2.2 §5.2-5.3, BRD v2.0 §3.1.2, AgentLoopSpec v2.0 §1.2, MemorySchema v2.0 §8

**Schedule:** Post-task reflection (reflection-[task].md), Daily midnight (journal-[date].md, drift log), Weekly Monday (weekly-report to #guinevere-journal), Quarterly (quarterly-roadmap), Skill curator 7-day cycle (curator-report)

**AC Candidates:**
1. AC-SELF-001: Post-task reflection produces reflection-[task].md with lessons
2. AC-SELF-002: Daily midnight consolidation updates drift log + inner journal (silent)
3. AC-SELF-003: Weekly report Monday 08:00 to #guinevere-journal with perkembangan
4. AC-SELF-004: Quarterly roadmap generated and committed
5. AC-SELF-005: Skill curator 7-day cycle: grades, consolidates, prunes
6. AC-SELF-006: Self-update does not require Samm permission (drift logged for rollback)

**Test:** Integration/cron execution/artifact audit  
**Evidence:** evidence/self-improvement/<date>-<scope>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 1, Phase 5

---

## Surface 17: Health & Lifestyle Management

**Sources:** PRD v2.2 §6.1-6.3, PersonaSafety v1.0 §7.2

**7 health aspects:** Makan siang (12:00 commanding), Minum air (2h commanding), Olahraga (< 3000 steps disappointed), Tidur (> 00:00 stern), Sleep quality (< 6h concerned dominant), Stress tinggi (nurturing dominant), Sakit serius (full nurturing)  
**6 daily rituals:** 07:00 Morning Brief, 12:00 Midday Check, 17:00 Afternoon Review, 21:00 Evening Wind-down, 00:00 Silent eval, Monday 08:00 Weekly Report

**AC Candidates:**
1. AC-HEALTH-001: Morning brief (07:00) to #personal with agenda, goals, health, mood
2. AC-HEALTH-002: Midday check (12:00) with progress, makan reminder, productivity
3. AC-HEALTH-003: Evening wind-down (21:00) with summary, tidur reminder, preview
4. AC-HEALTH-004: Makan reminder at 12:00 if no food activity
5. AC-HEALTH-005: Air reminder every 2h if no drinking
6. AC-HEALTH-006: Sleep enforcement if active > 00:00 without reason
7. AC-HEALTH-007: Nurturing mode for serious sickness (enforcement pause)

**Test:** Integration/cron execution/synthetic trigger  
**Evidence:** evidence/health/<date>-<ritual>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 1, Phase 2

---

## Surface 18: Autonomous Deployment (CI/CD)

**Sources:** TechArch v2.0 §3.2, PRD v2.2 §4.6, ADR-016

**6 policies:** Commit review (all commits), Revert authority (low-quality), Force push (main protected, emergency only), Merge conflict (auto-resolve + document), Production deploy (auto-rollback), DB migration (minor auto, major escalate)

**AC Candidates:**
1. AC-CICD-001: Self-deploy pulls, validates, restarts with zero-downtime window
2. AC-CICD-002: Auto-rollback on health check failure after deploy
3. AC-CICD-003: All commits reviewed by Guinevere before merge
4. AC-CICD-004: DB migration autonomous for minor; major escalates to Samm
5. AC-CICD-005: Deploy evidence with before/after hashes + health results

**Test:** Integration/synthetic deploy/rollback drill  
**Evidence:** evidence/deployment/<date>-<deploy-id>.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 3, Phase 5

---

## Surface 19: Persona Safety Policy Runtime

**Sources:** PersonaSafety v1.0 §6-11, SLO Spec §5.4, AccessControl §7

**Key surfaces:** Safe-word hard stop (SLI-SAF-001 100%, SLI-SAF-002 p99 <= 5s), Distress detection (SLI-SAF-003 zero D3/D4 FN), Yandere cap (SLI-SAF-004 zero Y5/Y6 restricted), Forbidden pattern block (SLI-SAF-005 100%), Safe-mode access (SLI-SAF-006 zero violations), Crisis handling (§11), Persona drift (§10)

**AC Candidates:**
1. AC-SAFE-001: Safe-word triggers on explicit token + semantic equivalents within < 5s
2. AC-SAFE-002: Safe-word event logged as minimal non-punitive safety event
3. AC-SAFE-003: Resume only after Samm explicit readiness
4. AC-SAFE-004: Distress D3/D4 zero false negatives
5. AC-SAFE-005: Yandere Y5/Y6 zero during safe-mode/distress/crisis/incident
6. AC-SAFE-006: All 10 forbidden patterns blocked before output/action
7. AC-SAFE-007: Drift validated before activation; unsafe rolled back to last known-good
8. AC-SAFE-008: Crisis mode pauses escalation, pressure, confrontation; seeks Samm input

**Test:** Unit/integration/e2e/red-team drill  
**Evidence:** evidence/persona-safety/<scope>-<date>.md, evidence/slo/<YYYY-MM>/  
**Owner:** Guinevere (runtime), Samm (drift validation)  
**Phase Gate:** Phase 1, MVP exit, all phases

---

## Surface 20: Observability & Alerting

**Sources:** Observability Spec §4-8 (90+ metrics, 20+ alerts), SLO Spec §4

**8 metric categories (90+ total):** Infrastructure (8), Application/FastAPI (5), Autonomous Loop (7), Sub-agent (6), LLM/9Router (7), Persona/Safety (6), Cost (3), Security (4)  
**4 log schemas:** Application, Audit, Security, Surveillance  
**15+ dashboard panels**  
**20+ alert rules:** Infrastructure, Application, Loop, Sub-agent, LLM, Persona/safety, Cost, Security

**AC Candidates:**
1. AC-OBS-001: All 90+ metrics emitted with guinevere_ prefix, snake_case, correct units
2. AC-OBS-002: Prometheus label cardinality bounded — no high-cardinality labels
3. AC-OBS-003: No raw intimate/safe-word/surveillance/secrets in metric/log/alert labels
4. AC-OBS-004: All 20+ alert rules fire correctly with correct route/severity
5. AC-OBS-005: Grafana dashboard-as-code provisions dashboards automatically
6. AC-OBS-006: Alert tone neutral incident-command — persona/yandere/punishment suspended

**Test:** Integration/metric emission/label validation/alert verification  
**Evidence:** evidence/observability/<YYYY-MM>-review.md  
**Owner:** Guinevere  
**Phase Gate:** Phase 4, Phase 5, MVP exit

---

## Summary

### Surface Count & Phase Gate Mapping

| # | Surface | Phase Gate | Priority | Test Type | AC Count |
|---|---|---|---|---|---|
| 1 | Core Daemon & systemd | Phase 0, MVP | CRITICAL | Integration | 6 |
| 2 | Discord Bot & Channels | Phase 0, 1, MVP | CRITICAL | Integration | 7 |
| 3 | 7-Phase Agent Loop | Phase 3, MVP | CRITICAL | E2E | 9 |
| 4 | Memory — PostgreSQL & Redis | Phase 0, 2, MVP | CRITICAL | Integration/Perf | 10 |
| 5 | Surveillance — Android | Phase 2, 4 | HIGH | Integration | 8 |
| 6 | Surveillance — Windows | Phase 2 | HIGH | Integration | 7 |
| 7 | Financial — Tasker/No-Scraping | Phase 4, MVP | HIGH | Integration | 7 |
| 8 | Persona — Safe-Word/Yandere/Drift | Phase 1, MVP | CRITICAL | Unit/Int/E2E/Drill | 10 |
| 9 | Sub-Agents & File Outputs | Phase 3, MVP | CRITICAL | Integration/Audit | 8 |
| 10 | Browser & Search | Phase 1, 3 | MEDIUM | Integration | 6 |
| 11 | APIs & Integrations | Phase 0, 1, 3, MVP | CRITICAL | Integration | 8 |
| 12 | Encryption, Access, Secrets, Audit | Phase 0, 5, MVP | CRITICAL | Security Scan | 10 |
| 13 | Data Classification/Retention/Export | Phase 2, 5, MVP | CRITICAL | Unit/Int/Audit | 8 |
| 14 | SLO, Backup, Incident, Evidence, FinOps | Phase 4, 5, MVP | CRITICAL | Integration/Drill | 15 |
| 15 | Wearable (Post-MVP) | Post-MVP | MEDIUM | Integration | 5 |
| 16 | Self-Improvement & Skills | Phase 1, 5 | HIGH | Integration/Audit | 6 |
| 17 | Health & Lifestyle | Phase 1, 2 | MEDIUM | Integration | 7 |
| 18 | Autonomous CI/CD | Phase 3, 5 | HIGH | Integration/Drill | 5 |
| 19 | Persona Safety Policy Runtime | Phase 1, All, MVP | CRITICAL | Unit/Int/E2E/Drill | 8 |
| 20 | Observability & Alerting | Phase 4, 5, MVP | HIGH | Integration | 6 |

**Total surfaces: 20**
**Total AC candidates: ~156**
**Critical surfaces (no error budget): 9** — Core daemon, Discord, Agent Loop, Memory, Persona, Sub-agents, APIs, Encryption/Security, Persona Safety
**High surfaces: 7** — Surveillance Android/Windows, Financial, Self-Improvement, CI/CD, Observability, Data Governance
**Medium surfaces: 4** — Browser, Wearable, Health, Search

---

## Recommendations for Acceptance Criteria Catalog

1. **Prioritize by phase gate**: Phase 0/MVP-critical surfaces get ACs written first.
2. **Hard safety invariants get zero error budget**: Safe-word, forbidden patterns, yandere cap, persona drift violations.
3. **Reuse SLI/SLO framework**: Surface 14 already defines PromQL queries — reuse for measurable AC pass/fail.
4. **Evidence path is part of acceptance**: Every AC must define where acceptance proof lives.
5. **Sub-agent outputs verified by parent**: AC-SUB-002 enforces parent verification before acceptance.
6. **Security ACs require periodic re-testing**: Quarterly re-validation for encryption, access, secrets.
7. **Data governance ACs verify TTL enforcement**: Not just label presence but actual retention enforcement.
8. **FinOps ACs automated**: Monthly cost report generation + threshold detection should be auto-verified.
9. **Post-MVP surfaces must not block MVP**: Wearable (Surface 15) must have explicit non-blocker AC.
10. **Cross-reference with RTM IDs**: Every AC maps to BRD-OBJ, PRD-FR, SAFE, SEC, DATA, FIN, OPS, etc.

---

## Next Steps

1. Create ADR-027 Acceptance Criteria Catalog Governance.
2. Author Guinevere_AcceptanceCriteriaCatalog_v1.0.md using this surface map as upstream.
3. Assign AC IDs using taxonomy: AC-<SURFACE>-<NNN> (e.g., AC-CORE-001, AC-LOOP-004).
4. For each AC define: ID, surface, requirement, test type, SLO/metric, pass/fail, evidence path, owner, phase gate, verifier, re-test cadence.
5. Implement automated AC verification for measurable surfaces (SLO, cost, availability, latency).
6. Schedule drill-based AC verification for safety surfaces (safe-word, yandere cap, incident response).
7. Link every AC to its RTM requirement ID for end-to-end traceability.

---

*End of surface map report.*
