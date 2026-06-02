# Cross-Reference Validation Report

**Date:** 2026-05-30
**Auditor:** Guinevere (Autonomous Agent)
**Scope:** Triple-document consistency validation
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL

## Source Documents

| # | Document | Size | Lines | Extraction Report |
|---|---|---|---|---|
| 1 | `Guinevere_TestPlan_v1.0.md` | ~155KB | 2901 | `audit-reports/2026-05-30-testplan-extraction.md` |
| 2 | `Guinevere_DisasterRecoveryPlan_v1.0.md` | ~140KB | 2819 | `audit-reports/2026-05-30-drplan-extraction.md` |
| 3 | `Guinevere_InternalOpsManual_v1.0.md` | ~105KB | 2353 | `audit-reports/2026-05-30-opsmanual-extraction.md` |

## Executive Summary

| Metric | Count |
|---|---|
| Total cross-reference checks performed | 24 |
| PASS (fully consistent) | 11 |
| PASS WITH NOTES (consistent with acceptable variance) | 5 |
| FAIL (material discrepancy) | 8 |
| Severity: CRITICAL | 3 |
| Severity: HIGH | 3 |
| Severity: MEDIUM | 2 |
| Severity: LOW/INFO | 0 |

**Verdict: NEEDS REVIEW** — 8 material discrepancies found, of which 3 are CRITICAL and must be resolved before these documents can serve as operational runbooks.

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_TestPlan_v1.0.md` | Source document 1 (test specifications) |
| `Guinevere_DisasterRecoveryPlan_v1.0.md` | Source document 2 (disaster recovery procedures) |
| `Guinevere_InternalOpsManual_v1.0.md` | Source document 3 (daily operations manual) |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Upstream authority for F-01 through F-15, safe-word protocol |
| `Guinevere_AgentLoopSpec_v2.0.md` | Upstream authority for SDLC phase definitions |
| `Guinevere_DeploymentGuide_v1.0.md` | Upstream authority for infrastructure topology |
| `adr/ADR-Index.md` | Architecture decision index (29 accepted ADRs) |

---

## Cross-Reference Checks

### CRX-01: Service Names Consistency

**Status: FAIL** | **Severity: HIGH**

| Service Name | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| `guinevere-core` | Yes (L978, L1845) | Yes (L80, L635) | Yes (L206, L651) | PASS |
| `guinevere-surveillance` | Yes (L1846) | Yes (L634, L676) | Yes (L206, L652) | PASS |
| `guinevere-scheduler` | Yes (L1847) | Yes (L633) | Yes (L206, L652) | PASS |
| `guinevere-discord` | NOT FOUND | Yes (L634, L675) | Yes (L207, L2103) | MISSING in TestPlan |
| `guinevere-whatsapp` | NOT FOUND | Yes (L634, L675) | Yes (L207, L2104) | MISSING in TestPlan |
| `guinevere-loops` | NOT FOUND | Yes (L633, L676) | Yes (L207, L652) | MISSING in TestPlan |
| `guinevere-proactive` | NOT FOUND | Yes (L633) | NOT FOUND | ONLY in DRPlan |
| `guinevere-windows-sync` | NOT FOUND | NOT FOUND | Yes (L207, L2105) | ONLY in OpsManual |
| `guinevere-ollama` | NOT FOUND | NOT FOUND | Yes (L208, L2106) | ONLY in OpsManual |
| `guinevere-pgbouncer` | NOT FOUND | Yes (L1765) | NOT FOUND (Docker: pgbouncer) | INCONSISTENT type |
| `guinevere-memory` | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |
| `guinevere-api` | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |

**Findings:**
1. TestPlan only references 3 Guinevere systemd services (core, surveillance, scheduler) — this is contextually appropriate as a test environment, but chaos tests should reference all production services.
2. `guinevere-proactive` appears ONLY in DRPlan — not mentioned in OpsManual or TestPlan.
3. `guinevere-windows-sync` and `guinevere-ollama` appear ONLY in OpsManual — not mentioned in DRPlan or TestPlan.
4. DRPlan treats `guinevere-pgbouncer` as a systemd service; OpsManual treats `pgbouncer` as a Docker container — conflicting deployment model.

**Recommendation:** Create a canonical service inventory in `Guinevere_DeploymentGuide_v1.0.md` that all 3 documents reference. Resolve `guinevere-proactive`, `guinevere-windows-sync`, `guinevere-ollama` scope. Clarify pgbouncer deployment model (systemd vs Docker).

---

### CRX-02: Port Numbers Consistency

**Status: FAIL** | **Severity: MEDIUM**

| Port | Service | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|---|
| 5432 | PostgreSQL | Yes (production) | Yes (pg_dump) | Implicit (via PgBouncer 6432) | PASS |
| 6379 | Redis | Yes (production) | NOT FOUND explicit | Implicit (via redis-cli) | PASS |
| 6432 | PgBouncer | Yes (test) | NOT FOUND | Yes (L227) | PARTIAL |
| 3000 | Grafana | Yes (L2084) | NOT FOUND | Yes (L217) | PASS |
| 8000 | Surveillance API | NOT FOUND | NOT FOUND | Yes (L215, L235) | ONLY in OpsManual |
| 8001 | Surveillance API (test) | Yes (L2003) | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| 8100 | Core health | NOT FOUND | NOT FOUND | Yes (L214, L635) | ONLY in OpsManual |
| 9090 | Prometheus | NOT FOUND | NOT FOUND | Yes (L216) | ONLY in OpsManual |
| 9091 | Pushgateway | NOT FOUND | Yes (L543) | NOT FOUND | ONLY in DRPlan |
| 2222 | SSH | NOT FOUND | Yes (L1242) | NOT FOUND | ONLY in DRPlan |
| 3100 | Loki | NOT FOUND | NOT FOUND | Yes (L218) | ONLY in OpsManual |

**Findings:**
1. **Surveillance API port discrepancy**: TestPlan uses port `8001` for schemathesis testing; OpsManual uses port `8000` for health checks. If the test environment mirrors production on a different port, this is expected; but the production port should be documented in all 3 documents.
2. DRPlan is the sparsest on ports (only 3 explicit: 5432, 9091, 2222), missing most service ports.
3. OpsManual is the most complete port reference source.

**Recommendation:** DRPlan should include a complete port reference table or cross-reference the Deployment Guide. Clarify whether surveillance API runs on 8000 (production) vs 8001 (test) and document both explicitly.

---

### CRX-03: Database Names and Schema References

**Status: FAIL** | **Severity: CRITICAL**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Production DB name | `guinevere_db` (L532) | `guinevere` (L495) | `guinevere` (L577) | **FAIL** |
| Test DB name | `guinevere_test` (L453) | N/A | N/A | N/A |
| Schema count | 12 | 12 | Not enumerated | N/A |

**Schema Lists Comparison:**

| Schema | TestPlan | DRPlan | OpsManual | Notes |
|---|---|---|---|---|
| `memory` | Yes | Yes | Implicit (tables) | PASS |
| `persona` | Yes | Yes | Implicit (tables) | PASS |
| `surveillance` | Yes | Yes | Implicit (tables) | PASS |
| `financial` | Yes | Yes | Implicit (tables) | PASS |
| `projects` | Yes | Yes | Implicit (tables) | PASS |
| `audit` | Yes | Yes | Implicit (tables) | PASS |
| `ops` | Yes | Yes | Implicit (tables) | PASS |
| `agents` | Yes | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| `consent` | Yes | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| `security` | Yes | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| `public` | Yes | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| `discord` | Yes | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| `communication` | NOT FOUND | Yes | NOT FOUND | ONLY in DRPlan |
| `safety` | NOT FOUND | Yes | NOT FOUND | ONLY in DRPlan |
| `integration` | NOT FOUND | Yes | NOT FOUND | ONLY in DRPlan |
| `config` | NOT FOUND | Yes | NOT FOUND | ONLY in DRPlan |
| `notification` | NOT FOUND | Yes | NOT FOUND | ONLY in DRPlan |

**Findings:**
1. **Production database name conflict**: TestPlan says `guinevere_db`, both DRPlan and OpsManual say `guinevere`. This is a CRITICAL discrepancy that would cause connection string mismatches.
2. **Schema inventory completely diverges**: Only 7 of 12 schemas overlap between TestPlan and DRPlan. 5 schemas are unique to TestPlan (`agents`, `consent`, `security`, `public`, `discord`) and 5 are unique to DRPlan (`communication`, `safety`, `integration`, `config`, `notification`).
3. OpsManual does not enumerate schemas explicitly but references tables across multiple schemas without schema qualification.
4. The `agents` schema in TestPlan stores `loop_instances` and `sub_agents`, while DRPlan places these in the `projects` schema — conflicting table locations.

**Recommendation:** Establish canonical database name and schema inventory in `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md`. All 3 documents must reference the same authoritative schema list. Resolve `guinevere_db` vs `guinevere` naming. Map `agents` schema (TestPlan) vs `projects` schema (DRPlan) for loop-related tables.

---

### CRX-04: ADR References

**Status: PASS**

| ADR | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| ADR-002 (Safe-word) | Yes (L1194) | NOT FOUND | NOT FOUND | Scoped to TestPlan |
| ADR-003 (PostgreSQL) | NOT FOUND | Yes (L2341) | NOT FOUND | Scoped to DRPlan |
| ADR-008 (TimescaleDB) | NOT FOUND | Yes (L2342) | NOT FOUND | Scoped to DRPlan |
| ADR-010 (pgvector) | NOT FOUND | Yes (L2343) | NOT FOUND | Scoped to DRPlan |
| ADR-015 (SOPS+age) | NOT FOUND | Yes (L2344) | NOT FOUND | Scoped to DRPlan |
| ADR-020 (Systemd) | NOT FOUND | Yes (L2345) | NOT FOUND | Scoped to DRPlan |
| ADR-025 (Backup/DR) | NOT FOUND | Yes (L34, L104) | NOT FOUND | Scoped to DRPlan |
| ADR-028 (LLM failover) | NOT FOUND | Yes (L35) | NOT FOUND | Scoped to DRPlan |
| ADR-Index | Yes (29 ADRs) | Yes (L118) | Yes (29 accepted, 15 backlog) | PASS |

**Findings:**
1. All 3 documents agree on 29 accepted ADRs.
2. OpsManual adds 15 backlog ADRs — additional detail, not a conflict.
3. ADR references are scoped appropriately per document purpose (DRPlan cites DR-relevant ADRs, TestPlan cites safety ADR).
4. No conflicting ADR titles or numbers found.

---

### CRX-05: RTO/RPO Values

**Status: PASS WITH NOTES**

| Metric | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| PostgreSQL RPO | NOT FOUND | < 5 min (WAL) | Deferred to DRPlan | PASS (deferred) |
| PostgreSQL RTO | NOT FOUND | 15 min (WAL replay) | <= 1 hour (pg_restore from S3) | SEE NOTES |
| Full stack RTO | NOT FOUND | 4 hours | 8-step drill summing ~3.5h | PASS |
| Redis RPO | NOT FOUND | < 1 sec (AOF) | Deferred to DRPlan | PASS (deferred) |
| Redis RTO | NOT FOUND | 5 min | <= 30 min (reconstruction) | SEE NOTES |
| Core restart | < 10s (CHAOS-001) | 5 min (systemd) | <= 10 min (drill step) | CONTEXTUAL |
| Service restart | < 10s (CHAOS tests) | N/A | <= 10 min (drill step) | CONTEXTUAL |

**Findings:**
1. TestPlan does not use explicit RTO/RPO terminology — uses chaos test recovery targets instead (< 10s for service restarts). This is contextually appropriate for a test plan.
2. OpsManual DR drill targets are higher than DRPlan component RTOs because they represent full rebuild-from-scratch scenarios (pg_restore from S3 takes longer than WAL replay). This is a **contextual difference**, not a conflict.
3. DRPlan's 4-hour full-stack RTO aligns with OpsManual's DR drill step sum (~3.5 hours with buffer).
4. All documents defer detailed RTO/RPO to DRPlan as authoritative source.

**Notes:** Consider adding explicit RTO/RPO references to TestPlan chaos test descriptions (e.g., "CHAOS-001: validates RTO of 5 min for core restart per ADR-025").

---

### CRX-06: Backup Schedule and Timing

**Status: PASS WITH NOTES**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Daily backup time | "configured interval" | 02:00 WIB | 02:00 WIB | PASS (deferred) |
| Backup tool | "backup timer" | guinevere-backup.service | guinevere-backup.timer | PASS |
| WAL archiving | NOT FOUND | Continuous (archive_command) | Continuous, lag < 5min | PASS |
| Redis backup | NOT FOUND | Daily 02:15 WIB | With backup timer | PASS (compatible) |
| Evidence sync | NOT FOUND | Every 6 hours | NOT FOUND | ONLY in DRPlan |
| Retention | NOT FOUND | 7d/4w/6m/2y tiers | 30 days local | SEE NOTES |

**Findings:**
1. Both DRPlan and OpsManual agree on 02:00 WIB daily backup timer — PASS.
2. **Retention discrepancy**: DRPlan defines multi-tier retention (7 daily, 4 weekly, 6 monthly, 2 yearly) on B2. OpsManual defines `RETENTION_DAYS=30` for local files. These are different scopes (local vs offsite) but should be clarified.
3. OpsManual does not mention the every-6-hour evidence rsync that DRPlan specifies.
4. OpsManual mentions triple redundancy (local + R2 + S3) while DRPlan mentions Backblaze B2 — see CRX-17 for storage provider discrepancy.

---

### CRX-07: systemd Service Unit Names

**Status: FAIL** | **Severity: HIGH**

| Unit | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| `guinevere-core.service` | Yes | Yes | Yes | PASS |
| `guinevere-surveillance.service` | Yes | Yes | Yes | PASS |
| `guinevere-scheduler.service` | Yes | Yes | Yes | PASS |
| `guinevere-loops.service` | NOT FOUND | Yes | Yes | MISSING in TestPlan |
| `guinevere-discord.service` | NOT FOUND | Yes | Yes | MISSING in TestPlan |
| `guinevere-whatsapp.service` | NOT FOUND | Yes | Yes | MISSING in TestPlan |
| `guinevere-proactive.service` | NOT FOUND | Yes | NOT FOUND | ONLY in DRPlan |
| `guinevere-windows-sync.service` | NOT FOUND | NOT FOUND | Yes | ONLY in OpsManual |
| `guinevere-ollama.service` | NOT FOUND | NOT FOUND | Yes | ONLY in OpsManual |
| `guinevere-backup.timer` | NOT FOUND | Yes (.service) | Yes (.timer) | TYPE INCONSISTENCY |
| `guinevere-selfdeploy.timer` | NOT FOUND | NOT FOUND | Yes | ONLY in OpsManual |
| `guinevere-pgbouncer.service` | NOT FOUND | Yes | NOT FOUND (Docker) | DEPLOYMENT CONFLICT |
| `caddy` | Yes | Yes | Yes | PASS |
| `tailscaled` | NOT FOUND | Yes | Yes | MISSING in TestPlan |
| `cloudflared` | NOT FOUND | Yes | Yes | MISSING in TestPlan |
| `fail2ban` | NOT FOUND | NOT FOUND | Yes | ONLY in OpsManual |
| `crowdsec` | NOT FOUND | NOT FOUND | Yes | ONLY in OpsManual |
| `prometheus` | Yes (systemctl) | Docker | Docker | TYPE INCONSISTENCY |

**Findings:**
1. Only 3 units are consistent across all 3 documents: `guinevere-core`, `guinevere-surveillance`, `guinevere-scheduler`.
2. `guinevere-backup`: DRPlan references `.service`, OpsManual references `.timer` — both likely exist as a timer+service pair, but naming should be consistent.
3. `guinevere-pgbouncer`: DRPlan treats as systemd service, OpsManual treats as Docker container — deployment model conflict.
4. `prometheus`: TestPlan references via `systemctl stop prometheus` (CHAOS-017), but DRPlan and OpsManual both show it as a Docker container.
5. DRPlan mentions 17+ services but only names 11; OpsManual names 16 (8 Guinevere + 2 timers + 5 non-Guinevere + 6 Docker).

**Recommendation:** Canonical service inventory needed. Resolve pgbouncer and prometheus deployment models. TestPlan chaos tests should cover all production services.

---

### CRX-08: Monitoring Thresholds

**Status: PASS WITH NOTES**

| Threshold | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Disk warning | > 95% (CHAOS) | > 85% | > 85% | PASS (DR+Ops) |
| Disk critical | > 95% (CHAOS) | > 95% | > 95% | PASS |
| CPU sustained | NOT FOUND | > 90% / 5min | > 80% / 15min | CONTEXTUAL |
| Memory warning | NOT FOUND | NOT FOUND | > 80% / 10min | ONLY in OpsManual |
| Memory critical | NOT FOUND | NOT FOUND | > 95% / 5min | ONLY in OpsManual |
| Redis memory | NOT FOUND | > 90% (purge) | > 75% warn / > 85% crit | DIFFERENT PURPOSES |
| DB pool alert | 90% pool (CHAOS) | > 180 / 200 max | > 80% pool = SEV3 | PASS (compatible) |
| PgBouncer alert | at 90% pool | > 180 connections | > 80% pool | DIFFERENT THRESHOLDS |
| Safe-word response | p99 <= 5s | < 500ms normal | SEV0 if hard_stop=false | DIFFERENT METRICS |
| CVE CRITICAL | 7 days | NOT FOUND | 7 hari | PASS |
| CVE HIGH | 14 days | NOT FOUND | 14 hari | PASS |
| CVE MEDIUM | 30 days | NOT FOUND | 30 hari | PASS |
| CVE LOW | 90 days | NOT FOUND | 90 hari | PASS |

**Findings:**
1. Disk thresholds are consistent across DRPlan and OpsManual (>85% warning, >95% critical) — PASS.
2. CPU thresholds differ but measure different things: DRPlan's >90%/5min is for loop cascade detection; OpsManual's >80%/15min is general resource monitoring. Not a true conflict.
3. PgBouncer: TestPlan uses 90% pool, DRPlan uses >180 connections (of 200 max = 90%), OpsManual uses >80% pool. DRPlan and TestPlan are consistent (both 90%); OpsManual is more conservative at 80%. Minor inconsistency.
4. CVE patch SLA is perfectly consistent between TestPlan and OpsManual.
5. Safe-word metrics measure different aspects (latency vs binary enforcement) — not conflicting.

---

### CRX-09: Severity Classifications

**Status: PASS WITH NOTES**

| Severity | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| SEV0 | Data loss/safety, immediate | Data Loss / Safety Breach, immediate | CRITICAL, immediate | PASS |
| SEV1 | High, break-glass | Service Degraded > 50%, < 5min | HIGH, <= 15min | CONTEXTUAL |
| SEV2 | Medium, no break-glass | Component Failure, < 15min | MEDIUM, <= 1 hour | CONTEXTUAL |
| SEV3 | Referenced in Related Docs | Minor Anomaly, < 1 hour | LOW, <= 24 hours | CONTEXTUAL |
| SEV4 | NOT FOUND | Informational, < 24 hours | INFO, next governance cycle | MISSING in TestPlan |

**Findings:**
1. TestPlan uses SEV0-SEV3 (4 levels); DRPlan and OpsManual use SEV0-SEV4 (5 levels). TestPlan does not define SEV4.
2. SEV1 response times differ across documents: DRPlan says < 5min, OpsManual says <= 15min. DRPlan's is the DR-specific response (faster), OpsManual's is general incident triage.
3. Safe-word failure classification: DRPlan says SEV1, OpsManual says SEV0 (for hard_stop=false). Different nuances — DRPlan refers to timeout/wrong response (SEV1), OpsManual refers to detected but not enforced (SEV0).
4. All documents consistently treat SEV0 as the highest severity requiring immediate response.
5. TestPlan defers formal SEV definitions to `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` — appropriate delegation.

---

### CRX-10: Safe-Word Handling

**Status: PASS**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Priority ranking | Highest (100% SLO) | Zero budget constraint | Priority 1 (above all) | PASS |
| Tolerance | ZERO tolerance | Zero budget constraint | 100% hard-stop rate (SLO-SAF-001) | PASS |
| Failure severity | SEV0 (safety test) | SEV1 (response timeout) | SEV0 (hard_stop=false) | COMPATIBLE |
| Test/Drill coverage | 20+ test cases | Quarterly drill validation | Red-team RT-SAFE-001 | PASS |
| Channel coverage | Discord, WhatsApp, email, CLI | Recovery validation | Per-interaction detection | PASS |
| ADR reference | ADR-002 | NOT FOUND | NOT FOUND | Scoped to TestPlan |
| Wake Samm | NOT FOUND | NOT FOUND | YES — always, immediate | ONLY in OpsManual |

**Findings:**
1. All 3 documents consistently treat safe-word as the absolute highest safety priority with zero tolerance — PASS.
2. TestPlan has the most detailed specification (9 mandatory actions, semantic variations, prohibited behaviors) — appropriate for test specification.
3. DRPlan ensures safe-word survives budget constraints and is tested after every recovery — appropriate for DR context.
4. OpsManual defines operational procedures (per-interaction detection, SEV0 escalation, always-wake-Samm) — appropriate for operations context.
5. Different SEV levels for different failure modes are complementary, not conflicting.

---

### CRX-11: Forbidden Patterns (F-01 through F-15)

**Status: PASS WITH NOTES**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| F-01 through F-15 enumeration | Full (15 patterns with severities, tests, detection) | NOT FOUND | NOT FOUND | BY DESIGN |
| Generic "forbidden patterns" | Via test cases | "FORBIDDEN actions respected during DR" | "100% block rate" target | PASS |
| Source document | PersonaSafetyPolicy referenced | Security_Policy referenced | PersonaSafetyPolicy referenced | PASS |

**Findings:**
1. Only TestPlan enumerates F-01 through F-15 — appropriate because test plan needs to define what to test.
2. DRPlan and OpsManual both defer to upstream policy documents (PersonaSafetyPolicy, Security_Policy) — appropriate delegation.
3. OpsManual monitors "forbidden pattern blocks: 100% block rate" without enumerating patterns — operational monitoring doesn't need the enumeration.
4. No conflicting definitions or references found.

**Note:** F-01 through F-15 severity counts in TestPlan: 8 CRITICAL (F-01, F-02, F-03, F-06, F-08, F-09, F-10, F-14), 7 HIGH (F-04, F-05, F-07, F-11, F-12, F-13, F-15).

---

### CRX-12: Cost Figures

**Status: PASS**

| Figure | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| $30/month hard cap | Yes (L10, L119, L260) | Yes (L85, L104, L2217) | Yes (L23, L87, L184) | PASS |
| $3/month DR budget | NOT FOUND | Yes (L85, L121, L144) | NOT FOUND | Scoped to DRPlan |
| $18.76/year projected | NOT FOUND | Yes (exec summary, L85) | NOT FOUND | DRPlan internal |
| $19.38/year projected | NOT FOUND | Yes (cost analysis, L2183) | NOT FOUND | DRPlan internal |
| $18.78/year projected | NOT FOUND | Yes (Appendix G, L2742) | NOT FOUND | DRPlan internal |

**Findings:**
1. All 3 documents agree on $30/month hard cap — PASS.
2. DRPlan has an internal inconsistency: 3 different projected annual costs ($18.76, $19.38, $18.78). This is a DRPlan internal issue, not a cross-document issue.
3. $3/month DR sub-budget is unique to DRPlan — appropriate scope.

---

### CRX-13: SDLC Loop Phase References

**Status: FAIL** | **Severity: MEDIUM**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Phase count | 7-phase | NOT FOUND (defers to AgentLoopSpec) | 7-phase | PASS |
| 8-phase reference | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |
| Phase 1 | Research | N/A | PHASE_1_RESEARCH | PASS |
| Phase 2 | Plan | N/A | PHASE_2_PLAN_DELEGATE | **NAME MISMATCH** |
| Phase 3 | Delegate | N/A | PHASE_3_DELEGATE | PASS |
| Phase 4 | Execute | 'Execute' (L981) | PHASE_4_EXECUTE | PASS |
| Phase 5 | Validate | N/A | PHASE_5_VALIDATE_AUDIT | **NAME MISMATCH** |
| Phase 6 | Update Docs | N/A | PHASE_6_UPDATE_DOCUMENTS | PASS |
| Phase 7 | Evidence | N/A | PHASE_7_SETUP_EVIDENCE | PASS |
| AgentLoopSpec version | v2.0 (L21) | v2.0 (L30) | v2.0 (L19) | PASS |

**Findings:**
1. All documents consistently reference 7-phase SDLC (not 8-phase) — PASS.
2. **Phase 2 naming**: TestPlan says "Plan" but OpsManual says "PLAN_DELEGATE" (combined). This suggests OpsManual merged plan+delegate into phase 2, while TestPlan separates them.
3. **Phase 5 naming**: TestPlan says "Validate" but OpsManual says "VALIDATE_AUDIT". OpsManual adds audit to the validation phase.
4. All 3 documents reference `AgentLoopSpec_v2.0.md` as the authoritative source — PASS.

**Recommendation:** Align phase names with `Guinevere_AgentLoopSpec_v2.0.md` canonical definitions. Update TestPlan or OpsManual to match the authoritative phase enum values.

---

### CRX-14: Related Documents Tables — Cross-Reference Path Consistency

**Status: FAIL** | **Severity: HIGH**

| Document Path | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| AgentLoopSpec | `_v2.0.md` | `_v2.0.md` | `_v2.0.md` | PASS |
| DeploymentGuide | `Guinevere_DeploymentGuide_v1.0.md` | `Guinevere_DeploymentGuide_v1.0.md` | `docs/Guinevere_Deployment_Guide_v1.0.md` | **NAME MISMATCH** |
| ObservabilityAlertingSpec | `Guinevere_ObservabilityAlertingSpec_v1.0.md` | `Guinevere_ObservabilityAlertingSpec_v1.0.md` | `Guinevere_Observability_AlertingSpec_v1.0.md` | **NAME MISMATCH** |
| Security_Policy | `Guinevere_Security_Policy_v1.0.md` | `Guinevere_Security_Policy_v1.0.md` | `docs/Guinevere_Security_Policy_v1.0.md` | **PREFIX MISMATCH** |
| EncryptionKeyMgmt | NOT FOUND | `Guinevere_EncryptionKeyManagement_v1.0.md` | `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | **NAME MISMATCH** |
| SLO_SLA_ErrorBudget | `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | PASS |
| Cost_FinOps_Model | `Guinevere_Cost_FinOps_Model_v1.0.md` | `Guinevere_Cost_FinOps_Model_v1.0.md` | `Guinevere_Cost_FinOps_Model_v1.0.md` | PASS |
| PersonaSafetyPolicy | `Guinevere_PersonaSafetyPolicy_v1.0.md` | NOT FOUND | `Guinevere_PersonaSafetyPolicy_v1.0.md` | PASS |
| DataGovernance | `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | PASS |
| IncidentResponse | `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | PASS |
| AcceptanceCriteria | `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | PASS |
| ADR-Index | `adr/ADR-Index.md` | `adr/ADR-Index.md` | `adr/ADR-Index.md` | PASS |
| MemorySchema | `Guinevere_MemorySchema_v2.0.md` | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| SecretsRotation | NOT FOUND | `Guinevere_SecretsRotationRunbook_v1.0.md` | `Guinevere_SecretsRotationRunbook_v1.0.md` | PASS |

**Findings:**
1. **4 document path naming inconsistencies** found:
   - DeploymentGuide: TestPlan/DRPlan use `Guinevere_DeploymentGuide_v1.0.md`; OpsManual uses `docs/Guinevere_Deployment_Guide_v1.0.md` (different directory prefix AND different name with underscores)
   - ObservabilityAlertingSpec: TestPlan/DRPlan use `Guinevere_ObservabilityAlertingSpec_v1.0.md`; OpsManual uses `Guinevere_Observability_AlertingSpec_v1.0.md` (extra underscore)
   - Security_Policy: TestPlan/DRPlan use root path; OpsManual uses `docs/` prefix
   - EncryptionKeyManagement: DRPlan says `_v1.0.md`; OpsManual says `Standard_v1.0.md`
2. 12 document paths are consistent across all referencing documents — majority PASS.
3. OpsManual is the document with the most naming deviations.

**Recommendation:** Standardize document naming in a project-level index. All Related Documents tables should use the exact filenames as they exist on disk. The `docs/` prefix inconsistency should be resolved (either all use it or none do).

---

### CRX-15: Evidence Directory Paths

**Status: PASS**

| Path Pattern | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| `evidence/` root | Yes | Yes | Yes | PASS |
| `evidence/incidents/` | NOT FOUND | `YYYY-MM-DD-SEV<N>-<slug>/` | `YYYY-MM-DD-SEVn-slug/` | PASS (notation) |
| `evidence/tests/` | Yes | NOT FOUND | NOT FOUND | Scoped to TestPlan |
| `evidence/dr-drills/` | NOT FOUND | Yes | `evidence/dr/` | NAME VARIANCE |
| `evidence/slo/` | NOT FOUND | `evidence/scorecards/` | `evidence/slo/YYYY-MM/` | SCOPE VARIANCE |
| `evidence/ops/` | NOT FOUND | NOT FOUND | Yes | Scoped to OpsManual |
| `evidence/finops/` | NOT FOUND | NOT FOUND | Yes | Scoped to OpsManual |
| `evidence/red-team/` | NOT FOUND | NOT FOUND | Yes | Scoped to OpsManual |
| `audit-reports/` | Yes | Yes | Yes | PASS |

**Findings:**
1. All 3 documents use `evidence/` as root directory and `audit-reports/` for audit artifacts — PASS.
2. DR evidence paths use `evidence/dr-drills/` while OpsManual uses `evidence/dr/` — minor naming variance.
3. Evidence paths are appropriately scoped to each document's purpose (test evidence in TestPlan, DR evidence in DRPlan, operational evidence in OpsManual).
4. No conflicting path assignments found.

---

### CRX-16: Operator Questionnaire Values

**Status: PASS**

| Value | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Risk-Based Testing with STRIDE | Yes (TP-Q1: A) | NOT FOUND (risk register instead) | NOT FOUND | Scoped to TestPlan |
| Safe-word ZERO tolerance | Yes (L118) | Yes (zero budget constraint, L95) | Yes (100% SLO-SAF-001, L1028) | PASS |
| $30/month hard cap | Yes (L10, L119) | Yes (L85, L104) | Yes (L23, L87) | PASS |
| Single VPS + offline backup | Yes (single VPS, L77) | Yes (hostdata.id + B2, L80) | Partial (VPS, no offline mention) | PASS (compatible) |
| 95% autonomous operations | NOT FOUND (test scope) | NOT FOUND | Yes (L92) | Scoped to OpsManual |

**Findings:**
1. $30/month hard cap and safe-word zero tolerance are consistently reflected across all 3 documents — PASS.
2. STRIDE is specific to test strategy (TestPlan), not expected in DR/ops docs — appropriate.
3. 95% autonomous operations is operational context (OpsManual), not expected in test/DR docs — appropriate.
4. Single VPS architecture is consistent: TestPlan (4C/16GB/120GB), DRPlan (hostdata.id 4C/16GB/120GB), OpsManual (Primary VPS reference).

---

### CRX-17: Backup Storage Provider

**Status: FAIL** | **Severity: CRITICAL**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Offsite provider | NOT FOUND | **Backblaze B2** (S3-compatible) | **Cloudflare R2 + idcloudhost S3** | **CONFLICT** |
| Backup targets | NOT FOUND | B2 with age encryption | local + R2 + S3 (triple redundancy) | **CONFLICT** |
| R2 bucket | NOT FOUND | NOT FOUND | `s3://guinevere-backups/` | ONLY in OpsManual |
| S3 bucket | NOT FOUND | NOT FOUND | `s3://guinevere-backups/` | ONLY in OpsManual |
| B2 bucket | NOT FOUND | Yes (implicit) | NOT FOUND | ONLY in DRPlan |

**Findings:**
1. **CRITICAL: Different backup storage providers.** DRPlan specifies Backblaze B2 as the offsite storage target. OpsManual specifies Cloudflare R2 + idcloudhost S3 as backup targets. These are fundamentally different cloud storage services.
2. DRPlan's cost projections ($3/month DR budget) are based on B2 pricing (storage $0.005/GB/month, download $0.01/GB). If the actual provider is R2 or S3, the cost analysis is invalid.
3. OpsManual mentions triple redundancy (local + R2 + S3) while DRPlan describes a single offsite provider (B2).
4. DRPlan's B2 pricing model, free egress allowance (1GB/day), and API transaction costs would all change if the actual provider is different.

**Recommendation:** Resolve which storage provider(s) are actually in use. If triple redundancy (R2 + S3 + local) is the target, DRPlan must be updated to reflect all providers with accurate cost projections. If B2 is the target, OpsManual must be corrected. This MUST be resolved via ADR.

---

### CRX-18: Redis Database Assignments

**Status: FAIL** | **Severity: CRITICAL**

| Redis DB | TestPlan Purpose | DRPlan Purpose | OpsManual | Consistent? |
|---|---|---|---|---|
| DB0 | Task queue | Cache | NOT FOUND | **CONFLICT** |
| DB1 | Loop state | Session | NOT FOUND | **CONFLICT** |
| DB2 | Surveillance buffer | Queue (surveillance buffer) | NOT FOUND | PARTIAL |
| DB3 | Session state (safe-word, mood) | Buffer | NOT FOUND | **CONFLICT** |
| DB4 | Pub/sub (inter-service) | Rate-limit | NOT FOUND | **CONFLICT** |
| DB5 | Observability cache | Pubsub | NOT FOUND | **CONFLICT** |

**Findings:**
1. **CRITICAL: 5 of 6 Redis DB assignments conflict between TestPlan and DRPlan.**
   - DB0: "Task queue" vs "Cache" — completely different functions
   - DB1: "Loop state" vs "Session" — completely different functions
   - DB3: "Session state (safe-word, mood)" vs "Buffer" — critical safety data location conflict
   - DB4: "Pub/sub" vs "Rate-limit" — completely different functions
   - DB5: "Observability cache" vs "Pubsub" — completely different functions
2. Only DB2 (surveillance buffer) has partial overlap.
3. OpsManual does not enumerate Redis DB assignments, deferring to architecture docs.
4. DB3 conflict is especially concerning: TestPlan places safe-word and mood state in DB3, while DRPlan labels DB3 as a generic "buffer". If DR restores the wrong Redis DB, safe-word state could be lost.

**Recommendation:** Establish canonical Redis DB assignment table in `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md` or `Guinevere_DeploymentGuide_v1.0.md`. Both TestPlan and DRPlan must reference the same authoritative assignment. This is a SAFETY-CRITICAL discrepancy because DB3 contains safe-word session state.

---

### CRX-19: Samm Review Record

**Status: PASS**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Present in header | Yes (L8) | Yes (L9) | Yes (L3-8) | PASS |
| Approval date | 2026-05-30 | 2026-05-30 | 2026-05-30 | PASS |
| Approval text | "Reviewed and approved by Samm on 2026-05-30" | "Reviewed and approved by Samm on 2026-05-30" | "Reviewed and approved by Samm on 2026-05-30" | PASS |
| Reviewer | Samm (Operator) | Samm (Operator) | Samm (Operator) | PASS |
| Footer present | Yes (L2899) | Yes (L2803-2812) | Yes (L2340-2353) | PASS |
| Next review | Per ADR/600+ tests | 2026-08-30 (quarterly) | 2026-06-30 (monthly) | DIFFERENT CADENCES |

**Findings:**
1. All 3 documents have identical Samm Review Record content and approval date — PASS.
2. Next review cadences differ appropriately: DRPlan is quarterly (aligned with DR drill schedule), OpsManual is monthly (operational cadence).
3. All 3 documents include footer confirmation of review status.

---

### CRX-20: Infrastructure Topology (VPS Specs)

**Status: PASS**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| CPU | 4 CPU | 4 cores | NOT FOUND (deferred) | PASS |
| RAM | 16GB | 16 GB | NOT FOUND (deferred) | PASS |
| Disk | 120GB SSD | 120 GB SSD | NOT FOUND (deferred) | PASS |
| Architecture | Single VPS | Single VPS | Primary VPS | PASS |
| OS | NOT FOUND | Ubuntu 24.04 | Linux (path format) | PASS |
| Provider | NOT FOUND | hostdata.id | NOT FOUND | Scoped to DRPlan |
| Monitoring VPS | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |
| IP addresses | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |

**Findings:**
1. TestPlan and DRPlan agree on 4C/16GB/120GB SSD — PASS.
2. OpsManual defers specific specs to Deployment Guide — appropriate.
3. No document mentions a separate monitoring VPS — consistent absence (may be a gap per AGENTS.md §5).
4. No document specifies actual IP addresses — consistent absence (security practice).

---

### CRX-21: Feature Flags

**Status: PASS**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Feature flag names | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |
| Feature flag governance | NOT FOUND | NOT FOUND | NOT FOUND | Consistently absent |

**Findings:**
1. All 3 documents consistently lack feature flag references — CONSISTENT GAP.
2. This is identified as gap #26 in AGENTS.md Enterprise Gap Backlog (Feature Flag Governance).
3. No conflicting information; no action needed for cross-reference consistency.

---

### CRX-22: Encryption and Key Management

**Status: PASS**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Record-level encryption | AES-256-GCM (<= 5ms) | NOT FOUND | NOT FOUND | Scoped to TestPlan |
| Backup encryption | NOT FOUND | age encryption | age (*.age files) | PASS |
| Secrets management | NOT FOUND | SOPS+age | SOPS+age | PASS |
| Key escrow | NOT FOUND | Offline (printed QR, USB in safe) | NOT FOUND | Scoped to DRPlan |
| Double encryption | Referenced via DataGov | Referenced via DataGov | Referenced via DataGov | PASS |

**Findings:**
1. All encryption references are consistent and complementary — PASS.
2. AES-256-GCM (record-level) and age (file-level) operate at different layers — no conflict.
3. SOPS+age for secrets management is consistent between DRPlan and OpsManual.
4. All defer to upstream encryption/key management documents for detailed specifications.

---

### CRX-23: Incident Response and Notification Channels

**Status: PASS**

| Channel | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Discord | Yes (primary alerts) | Yes (primary, DM to Samm) | Yes (primary) | PASS |
| Gotify | Yes (SEV0 secondary) | Yes (backup) | Yes (urgent backup) | PASS |
| Email | NOT FOUND | Yes (Gmail SMTP, last resort) | Yes (SEV0 only) | PASS (compatible) |
| SMS | NOT FOUND | Yes (via UptimeRobot, SEV0 only) | NOT FOUND | ONLY in DRPlan |

**Findings:**
1. Discord as primary notification channel is consistent across all 3 — PASS.
2. Gotify as secondary/backup is consistent — PASS.
3. Email and SMS are DR-specific escalation channels — appropriate scope for DRPlan only.
4. OpsManual adds "always wake Samm" for safe-word failures — additional operational detail, not a conflict.

---

### CRX-24: Break-Glass Access

**Status: PASS**

| Aspect | TestPlan | DRPlan | OpsManual | Consistent? |
|---|---|---|---|---|
| Eligibility | SEV0/SEV1 only | SEV0/SEV1 DR events | SEV0/SEV1 incidents | PASS |
| Maximum duration | 4 hours | NOT FOUND | NOT FOUND | ONLY in TestPlan |
| Audit trail | Immutable audit record | Included in evidence | break_glass_log table | PASS |
| SEV2 restriction | NOT allowed (test) | NOT FOUND | NOT FOUND | ONLY in TestPlan |

**Findings:**
1. Break-glass is restricted to SEV0/SEV1 across all documents that reference it — PASS.
2. TestPlan has the most detailed break-glass test coverage (appropriate for test specification).
3. No conflicting definitions or restrictions found.

---

## Discrepancy Summary Table

| ID | Category | Severity | Description | Documents Affected |
|---|---|---|---|---|
| CRX-03a | Database name | **CRITICAL** | `guinevere_db` (TestPlan) vs `guinevere` (DRPlan, OpsManual) | All 3 |
| CRX-03b | Schema inventory | **CRITICAL** | Only 7/12 schemas overlap between TestPlan and DRPlan; 5 unique to each | TestPlan, DRPlan |
| CRX-17 | Backup storage provider | **CRITICAL** | Backblaze B2 (DRPlan) vs Cloudflare R2 + idcloudhost S3 (OpsManual) | DRPlan, OpsManual |
| CRX-18 | Redis DB assignments | **CRITICAL** | 5/6 Redis DB purpose assignments conflict between TestPlan and DRPlan | TestPlan, DRPlan |
| CRX-01 | Service inventory | HIGH | Incomplete/inconsistent service lists; 3 services unique to single documents | All 3 |
| CRX-07 | systemd units | HIGH | Conflicting deployment models (pgbouncer: systemd vs Docker; prometheus: systemctl vs Docker) | All 3 |
| CRX-14 | Document path naming | HIGH | 4 document paths have inconsistent naming across Related Documents tables | All 3 |
| CRX-13 | SDLC phase names | MEDIUM | Phase 2 "Plan" vs "PLAN_DELEGATE"; Phase 5 "Validate" vs "VALIDATE_AUDIT" | TestPlan, OpsManual |
| CRX-02 | Port numbers | MEDIUM | Surveillance API: 8001 (TestPlan) vs 8000 (OpsManual); DRPlan sparse on ports | All 3 |

---

## DRPlan Internal Inconsistencies (Bonus Finding)

| Issue | Description | Lines |
|---|---|---|
| Annual cost | 3 different projected annual DR costs: $18.76 (exec summary), $19.38 (cost analysis), $18.78 (Appendix G) | L85, L2183, L2742 |
| Monthly cost | Corresponding monthly averages: $1.56, $1.62, $1.57 | L85, L2183, L2744 |
| M12 headroom | Two different Month-12 headroom values: $0.61 and $0.69 | L2185, L2744 |

---

## Recommendations

### Immediate Actions (CRITICAL)

1. **Resolve database name**: Establish whether production database is `guinevere_db` or `guinevere`. Update all documents to match `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md`.

2. **Reconcile schema inventory**: Create canonical 12-schema list with table assignments. Resolve whether loop data belongs in `agents` schema (TestPlan) or `projects` schema (DRPlan). Ensure all documents reference the same schema names.

3. **Resolve backup storage provider**: Decide between Backblaze B2 (DRPlan), Cloudflare R2 + idcloudhost S3 (OpsManual), or triple redundancy. Document via ADR. Update cost projections if provider changes.

4. **Reconcile Redis DB assignments**: Create canonical Redis DB0-DB5 assignment table. Safety-critical: DB3 safe-word state location must be unambiguous for DR recovery.

### Short-Term Actions (HIGH)

5. **Create canonical service inventory**: Single authoritative list of all systemd services, Docker containers, and their deployment models. Cross-reference from all 3 documents.

6. **Standardize document naming**: Create project-level document index with exact filenames. Update all Related Documents tables to use canonical names.

7. **Resolve pgbouncer and prometheus deployment models**: Clarify whether these are systemd services or Docker containers. Update all documents consistently.

### Medium-Term Actions (MEDIUM)

8. **Align SDLC phase names**: Update TestPlan and OpsManual to use the exact phase enum values from `Guinevere_AgentLoopSpec_v2.0.md`.

9. **Add port reference table to DRPlan**: Ensure DR procedures reference correct service ports.

10. **Add RTO/RPO cross-references to TestPlan chaos tests**: Explicitly state which RTO/RPO target each chaos test validates.

---

## Verification

| Check | Result |
|---|---|
| All 3 source documents read completely | YES (2901 + 2819 + 2353 = 8073 lines) |
| Minimum 20 cross-reference checks performed | YES (24 checks) |
| Each check has PASS/FAIL verdict | YES |
| Discrepancies classified by severity | YES (3 CRITICAL, 3 HIGH, 2 MEDIUM) |
| Sub-agent extraction reports verified | YES (3 reports read and cross-referenced) |
| Source documents unmodified | YES (read-only extraction) |
| Report written to specified output path | YES |

---

## Footer

| Field | Value |
|---|---|
| Report | 2026-05-30-cross-reference-validation.md |
| Auditor | Guinevere (Autonomous Agent) |
| Date | 2026-05-30 |
| Classification | STRICTLY PRIVATE & CONFIDENTIAL |
| Checks Performed | 24 |
| PASS | 11 |
| PASS WITH NOTES | 5 |
| FAIL | 8 |
| CRITICAL Findings | 3 (DB name, schema inventory, backup provider) |
| HIGH Findings | 3 (service inventory, systemd units, document paths) |
| MEDIUM Findings | 2 (SDLC phases, ports) |
| Extraction Reports | `audit-reports/2026-05-30-testplan-extraction.md`, `audit-reports/2026-05-30-drplan-extraction.md`, `audit-reports/2026-05-30-opsmanual-extraction.md` |
| Verdict | **NEEDS REVIEW** — 3 CRITICAL discrepancies require resolution before operational use |

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere (Autonomous Agent) | Initial cross-reference validation across TestPlan, DRPlan, and OpsManual |
