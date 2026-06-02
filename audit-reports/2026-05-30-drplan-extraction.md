# DRPlan Cross-Reference Extraction Report

**Date:** 2026-05-30  
**Source Document:** `Guinevere_DisasterRecoveryPlan_v1.0.md` (2819 lines)  
**Purpose:** Exhaustive extraction of all cross-reference facts for cross-document validation  
**Extraction Method:** Full sequential read (lines 1-2819) plus targeted regex searches  

---

## 1. Service Names

### Unique Service Names Found

| # | Service Name | Context / Line References |
|---|---|---|
| 1 | `guinevere-core` | FastAPI + agent loop service (L80, L227, L249, L635, L674, L1312, L1471, L1673) |
| 2 | `guinevere-discord` | Discord bot service (L235, L250, L634, L675, L1471) |
| 3 | `guinevere-whatsapp` | WhatsApp bridge service (L236, L634, L675, L1471) |
| 4 | `guinevere-surveillance` | Surveillance ingestion service (L634, L676, L1472) |
| 5 | `guinevere-loops` | SDLC loop management service (L252, L547, L633, L676, L1472, L1547, L1567, L1793) |
| 6 | `guinevere-scheduler` | Background task scheduler (L254, L633) |
| 7 | `guinevere-proactive` | Proactive suggestions service (L254, L633) |
| 8 | `guinevere-backup.service` | Systemd timer for backup orchestration (L338, L490, L2544) |
| 9 | `guinevere-pgbouncer` | PgBouncer connection pooler service (L1765) |
| 10 | `cloudflared` | Cloudflare Tunnel daemon (L238, L1590, L1591, L1593, L1594, L1595) |
| 11 | `tailscaled` | Tailscale daemon (L1580) |
| 12 | `postgresql` | Docker container name (L393, L420, L503, L513, L636, L648, L650, L661, L662, L665, L1270) |
| 13 | `redis` | Docker container name (L687, L728, L768, L780, L1418) |

### Additional Infrastructure Components Referenced (not named as systemd services)
- **Prometheus** - monitoring (L231, L330, L1282, L1319)
- **Grafana** - dashboards (L231, L331, L1282, L1320)
- **Loki** - log aggregation (L231, L1321)
- **Caddy** - reverse proxy (L239)
- **PgBouncer** - connection pooler (L173, L1282, L1308)
- **Docker** - container runtime (L80, L248, L1245)

---

## 2. Port Numbers

| # | Port | Service / Context | Line Reference |
|---|---|---|---|
| 1 | **5432** | PostgreSQL (`-p 5432` in pg_dump command) | L514 |
| 2 | **9091** | Prometheus Pushgateway (`http://127.0.0.1:9091/metrics/job/backup`) | L543, L1922 |
| 3 | **2222** | Hardened SSH port (`Hardened sshd_config, port 2222`) | L1242, L1244, L1302, L1304, L2392 |

### Ports NOT explicitly mentioned in this document:
- 8080, 6379, 3000, 9090, 80, 443 - **NOT FOUND** in DRPlan. These may appear in other documents.
---

## 3. Database Names and Schemas

### Primary Database
| Attribute | Value | Line |
|---|---|---|
| Database name | `guinevere` | L495, L571, L2585 |
| Database user | `guinevere_admin` | L496, L420, L503, L508, L514 |
| PostgreSQL version | 16 (`timescale/timescaledb:latest-pg16`) | L394 |
| Extensions | pgvector, TimescaleDB | L1272, L1307 |

### 12 PostgreSQL Schemas (L81)
| # | Schema Name | Line |
|---|---|---|
| 1 | memory | L81, L221, L557, L578, L608, L613 |
| 2 | persona | L81, L234, L247, L1507, L1511, L1521 |
| 3 | surveillance | L81, L222, L517, L558, L585 |
| 4 | financial | L81, L223, L559 |
| 5 | audit | L81, L224, L560, L666, L917, L1384, L1394, L2591 |
| 6 | projects | L81, L230, L252, L949, L966, L973, L979, L1554, L1558 |
| 7 | ops | L81, L509, L539, L1817, L1821 |
| 8 | communication | L81 |
| 9 | safety | L81 |
| 10 | integration | L81 |
| 11 | config | L81 |
| 12 | notification | L81 |

### Tables Referenced

| # | Table (schema.table) | Type | Line References |
|---|---|---|---|
| 1 | `memory.episodes` | TimescaleDB hypertable | L221, L518, L557, L578, L608 |
| 2 | `memory.semantic_facts` | Table with HNSW index | L613 |
| 3 | `surveillance.events` | TimescaleDB hypertable | L222, L517, L558, L585 |
| 4 | `financial.transactions` | TimescaleDB hypertable | L223, L559 |
| 5 | `audit.audit_trail` | Merkle chain table | L224, L560, L666, L917, L1384, L1394, L2591 |
| 6 | `persona.mood_state` | Persona state table | L1507, L1511, L1513, L1518 |
| 7 | `persona.safety_config` | Safety configuration | L247, L1521 |
| 8 | `projects.loop_instances` | SDLC loop tracking | L252, L953, L966, L975, L979, L1555, L1795 |
| 9 | `projects.agent_tasks` | Sub-agent task queue | L954, L1558 |
| 10 | `projects.tasks` | Task registry | L955, L967 |
| 11 | `projects.evidence_artifacts` | Evidence file references | L956, L973 |
| 12 | `ops.backup_log` | Backup tracking | L509, L539, L602 |
| 13 | `ops.self_healing_log` | Self-healing audit log | L1817, L1821 |

### Redis Databases (L81, L225)
| DB | Purpose |
|---|---|
| DB0 | cache |
| DB1 | session |
| DB2 | queue (surveillance buffer) |
| DB3 | buffer |
| DB4 | rate-limit |
| DB5 | pubsub |

### HNSW Indexes Referenced
| Index Name | Table | Line |
|---|---|---|
| `ix_episodes_embedding_hnsw` | memory.episodes | L608 |
| `ix_semantic_facts_embedding_hnsw` | memory.semantic_facts | L613 |
| `ix_episodes_started_at` | memory.episodes | L1373 |
| `ix_events_occurred_at` | surveillance.events | L1374 |

### pgvector Embedding Dimension
- `vector(1536)` - L604
---

## 4. ADR References

| # | ADR | Title / Topic | Context | Line References |
|---|---|---|---|---|
| 1 | **ADR-025** | Backup and Disaster Recovery Strategy | Normative parent ADR; CRITICAL-risk; defines RPO/RTO targets, backup methods, restore validation | L34, L104, L118, L145, L220, L2335, L2339, L2347, L2818 |
| 2 | **ADR-028** | LLM Router Outage Graceful Degradation | 4-tier LLM failover chain; reduces LLM-related DR events | L35, L1641, L2340, L2818 |
| 3 | **ADR-003** | PostgreSQL as Primary Database | Drives PG-specific backup architecture | L2341, L2818 |
| 4 | **ADR-008** | TimescaleDB for Time-Series Data | Chunk-aware backup strategy | L2342, L2818 |
| 5 | **ADR-010** | pgvector for Semantic Search | HNSW index rebuild strategy | L2343, L2818 |
| 6 | **ADR-015** | SOPS+age for Secrets Management | Key escrow and rotation procedures | L2344, L2818 |
| 7 | **ADR-020** | Systemd for Service Management | Service restart self-healing patterns | L2345, L2818 |

### ADR File Paths Referenced
- `adr/ADR-025-backup-disaster-recovery-strategy.md` (L34, L104, L118)
- `adr/ADR-028-llm-router-outage-graceful-degradation.md` (L35)
- `adr/ADR-Index.md` (L118)

### ADR-025 Decision Record (L2347-2358)
| Aspect | Decision | Status |
|---|---|---|
| Backup storage | Backblaze B2 (S3-compatible) | Accepted |
| Encryption | age encryption for all offsite backups | Accepted |
| Retention | 7 daily, 4 weekly, 6 monthly, 2 yearly | Accepted |
| RTO target | 4 hours for full stack | Accepted |
| RPO target | 5 minutes for PostgreSQL (WAL) | Accepted |
| DR testing | Quarterly full, monthly partial | Accepted |
| Budget | Max 3 USD/month for DR | Accepted |
| Self-healing | Autonomous for service restart, DB pool, Redis, loops | Accepted |

---

## 5. RTO/RPO Values

### Complete RTO/RPO Matrix (Section 3.1, L218-239)

| # | Service / Data Component | RPO | RTO | Source |
|---|---|---|---|---|
| 1 | PostgreSQL (all 12 schemas) | < 5 min (WAL continuous) | 15 min (WAL replay + dump restore) | DR-Q13, Q14, ADR-025 |
| 2 | memory.episodes (TimescaleDB) | < 5 min (WAL) | 15 min (included in PG RTO) | DR-Q28 |
| 3 | surveillance.events (TimescaleDB) | < 5 min (WAL) | 15 min (included in PG RTO) | DR-Q28, Q46 |
| 4 | financial.transactions (TimescaleDB) | < 5 min (WAL) | 15 min (included in PG RTO) | DR-Q28, Q47 |
| 5 | audit.audit_trail (Merkle chain) | < 5 min (WAL) | 15 min (included in PG RTO) | DR-Q29, Q43 |
| 6 | Redis (DB0-DB5) | < 1 sec (AOF everysec) | 5 min (RDB + AOF restore) | DR-Q15, Q16 |
| 7 | Redis (cache warming fallback) | N/A (reconstructible from PG) | 15-30 min (cache warming) | DR-Q35 |
| 8 | guinevere-core (FastAPI + agent loop) | N/A (stateless) | 5 min (systemd auto-restart) | DR-Q17 |
| 9 | Full VPS loss (all 17+ services) | Per data RPO above | **4 hours total** | DR-Q18, AC-OPS-003 |
| 10 | Evidence artifacts (evidence/ directory) | < 6 hours (rsync to B2 every 6h) | 30 min (restore from B2) | DR-Q19, Q42 |
| 11 | Agent loop state (SDLC projects schema) | < 15 min (PG phase transition) | 15 min (included in PG RTO) | DR-Q20 |
| 12 | Observability stack (Prometheus/Grafana/Loki) | < 24 hours | 30 min (Docker Compose + config) | DR-Q21 |
| 13 | Surveillance ingestion pipeline | < 5 min (Redis DB2 buffer) | 10 min (API restart + queue drain) | DR-Q22 |
| 14 | SOPS+age secrets (.env.sops files) | Real-time (Git-tracked encrypted) | 5 min (re-encrypt + redeploy) | DR-Q36 |
| 15 | Persona state / mood FSM (persona schema) | < 5 min (WAL) | 15 min (included in PG RTO) | DR-Q44 |
| 16 | Discord bot (guinevere-discord) | N/A (stateless) | 10 min (restart + gateway connect) | DR-Q17 |
| 17 | WhatsApp bridge (guinevere-whatsapp) | N/A (stateless) | 10 min (restart + session restore) | DR-Q17 |
| 18 | Financial 7-year archive (cold storage) | Monthly archive cycle | 2 hours (cold storage retrieval) | DR-Q47 |
| 19 | Cloudflare Tunnel | N/A | 10 min (tunnel restart + re-auth) | Infrastructure |
| 20 | Caddy reverse proxy | N/A | 1 min (systemd restart) | Infrastructure |

### Additional RTO/RPO Context
- **AC-OPS-003** reference: `RTO <= 4h, RPO <= 24h` (L216) from Acceptance Criteria Catalog
- **archive_timeout = 900s** (15 min) as RPO guarantee (L360, L405, L431)
- **WAL RPO < 5 minutes** stated as maximum data loss (L114)
- **Full stack RTO: 4 hours** (L109, L114, L228, L2354)
- **Risk Acceptance:** maximum data loss 5 menit (WAL RPO) and maximum downtime 4 jam (full stack RTO) (L114)
---

## 6. Backup Schedule/Timing

### Backup Timing Table

| Frequency | What | When | Line |
|---|---|---|---|
| **Continuous** | PostgreSQL WAL archiving | Ongoing via archive_command | L337, L349 |
| **Every 1 second** | Redis AOF fsync | appendfsync everysec | L340, L709 |
| **Every 15 minutes** | Redis RDB snapshot trigger | save 900 1 | L339, L694 |
| **Every 5 minutes** | Redis RDB trigger (100 writes) | save 300 100 | L339, L695 |
| **Every 1 minute** | Redis RDB burst protection | save 60 10000 | L339, L696 |
| **Daily at 02:00 WIB** | pg_dump custom format (full) | Via guinevere-backup.service | L309, L338, L490, L2549 |
| **Daily at 02:15 WIB** | Redis RDB+AOF backup | Via redis_backup.sh | L2557 |
| **Daily at 02:20 WIB** | SOPS secrets backup | Via backup_sops.sh | L2560 |
| **Daily at 02:25 WIB** | Evidence sync | Via backup_evidence.sh | L2563 |
| **Daily at 02:30 WIB** | Audit trail export | Via audit_trail_export.sh | L2566 |
| **Daily at 02:35 WIB** | Retention rotation | Via retention_rotate.sh | L2569 |
| **Daily at 04:00 WIB** | Checksum verification | Via verify_daily.sh | L343, L1845 |
| **Every 6 hours** | Evidence rsync to B2 | Via systemd timer | L229, L871, L876 |
| **Weekly (Sunday 03:30 WIB)** | TimescaleDB chunk backup | Via timescale_chunk_backup.sh | L565 |
| **Weekly** | Partial restore test (rotating) | Section 8.2 | L343, L1933 |
| **Monthly** | Full DR drill | Section 8.3 | L343, L1944 |
| **Quarterly** | Full DR drill (formal, 4-hour target) | Section 9.3 | L84, L2006 |
| **Annually** | Tabletop exercise | Section 9.4 | L2027 |

### Retention Policy (Section 5.4, L1109-1133)

| Tier | Count | Scope | Storage | Cleanup |
|---|---|---|---|---|
| Daily | 7 | Last 7 days | VPS local + B2 daily/ | find -mtime +7 -delete |
| Weekly | 4 | Sunday backups for 4 weeks | B2 weekly/ | rclone --min-age 28d |
| Monthly | 6 | 1st-of-month for 6 months | B2 monthly/ | rclone --min-age 180d |
| Yearly | 2 | January backups for 2 years | B2 yearly/ | rclone --min-age 730d |
| Permanent | Unlimited | Audit trail, evidence, age keys, scorecards | B2 dedicated prefixes | Never deleted |

### Data-Specific Retention (L1119-1133)

| Data Type | Retention Highlights |
|---|---|
| memory.episodes | 10 years (L557) |
| surveillance.events | 180 days (L558) |
| financial.transactions | 7 years (L559) |
| audit.audit_trail | 1 year (L560), permanent exports |
| Evidence artifacts | Permanent (L1128) |
| Financial archive | 7-year regulatory compliance (L1131) |
| WAL segments | 7-day local + B2 (L1124) |
---

## 7. systemd Service Unit Names

| # | Unit Name | Context | Line |
|---|---|---|---|
| 1 | guinevere-core | Core FastAPI + agent loop | L635, L674, L1471 |
| 2 | guinevere-discord | Discord bot | L634, L675, L1471 |
| 3 | guinevere-whatsapp | WhatsApp bridge | L634, L675, L1471 |
| 4 | guinevere-surveillance | Surveillance ingestion | L634, L676, L1472 |
| 5 | guinevere-loops | SDLC loop management | L633, L676, L1472, L1547, L1567 |
| 6 | guinevere-scheduler | Background scheduler | L633 |
| 7 | guinevere-proactive | Proactive suggestions | L633 |
| 8 | guinevere-backup.service | Backup timer/service | L338, L490, L2544 |
| 9 | guinevere-pgbouncer | PgBouncer connection pooler | L1765 |
| 10 | cloudflared | Cloudflare Tunnel | L1591 |
| 11 | tailscaled | Tailscale daemon | L1580 |

### Wildcard References
- `guinevere-*` used in `systemctl stop guinevere-*` (L858, L1439)
- `guinevere-*` used in `systemctl restart guinevere-*` (L863)

### Notes
- `.service` extension explicitly mentioned only for `guinevere-backup.service` (L338, L490, L2544)
- Other units referenced via systemctl commands without explicit `.service` suffix
- The document mentions `17+ systemd services` (L80) but only explicitly names 11 unique units

---

## 8. Monitoring Thresholds

| # | Metric | Threshold | Context | Line |
|---|---|---|---|---|
| 1 | Backup freshness (age) | > 25 hours triggers SEV2 alert | Prometheus metric | L262, L1860, L1952 |
| 2 | Backup success rate | < 99% triggers review | Rolling metric | L265 |
| 3 | RTO compliance (rolling) | < 90% triggers procedure review | 4-quarter rolling | L266 |
| 4 | RPO compliance (rolling) | < 95% triggers architecture review | Rolling | L267 |
| 5 | Disk usage (warning) | > 85% triggers standard cleanup | Self-healing | L176, L1622, L1713, L1715 |
| 6 | Disk usage (critical) | > 95% triggers emergency cleanup | Self-healing | L176, L1612, L1714 |
| 7 | Disk usage (recovery target) | < 80% after cleanup | Self-healing success | L1716 |
| 8 | DB connection pool | > 180 (alert threshold) | PgBouncer | L173, L1694, L1750, L1755 |
| 9 | DB max connections | 200 | PostgreSQL config | L401, L1749 |
| 10 | Redis memory | > 90% triggers MEMORY PURGE | Self-healing | L1783 |
| 11 | Redis memory (escalation) | > 95% after purge | Escalation | L1783 |
| 12 | CPU sustained | > 90% for 5 minutes | Loop cascade detection | L1533 |
| 13 | Container RSS growth | > 100MB/hour | Loop cascade detection | L1536 |
| 14 | Persona drift score | > 0.5 (alert), normal 0.0-0.3 | Persona state corruption | L1496 |
| 15 | Safe-word response time | < 500ms normal, timeout = SEV1 | Persona safety | L1500 |
| 16 | Table bloat | > 10x expected bloat | PostgreSQL corruption detection | L1342 |
| 17 | Backup size anomaly | > 25% deviation from 7-day average | Cost tracking | L2218 |
| 18 | Monthly DR storage cost | > 2.50 USD warning, > 2.80 USD critical | Budget tracking | L2214 |
| 19 | Monthly DR download cost | > 0.30 USD | Budget tracking | L2215 |
| 20 | Storage growth rate (MoM) | > 20% triggers review | Budget tracking | L2216 |
| 21 | DR cost as pct of total budget | > 8% triggers planning | DR cost / 30 USD total | L2217 |
| 22 | Tailscale peer offline | > 5 min = SEV1, > 10 min = hard escalation | Network isolation | L184, L1209 |
| 23 | Network isolation | > 15 minutes (Tailscale + Cloudflare both down) | Hard escalation | L185 |
| 24 | Service crash frequency | 3 failures in 10 minutes | Escalation trigger | L172, L1736 |
| 25 | Hourly LLM spend | > 2x normal | Budget spike detection | L1534 |
| 26 | Tasks pending | > 30 min | Stale task detection | L1535 |
| 27 | Data completeness (restore) | Within 5% of source row count | Verification | L1956 |
| 28 | UptimeRobot check | 2 consecutive failures | Full VPS loss detection | L1208 |
| 29 | Data loss > 1 hour (Redis) | Escalation trigger | Redis recovery | L174 |
| 30 | OOM killer repeated | Repeated OOM within 30 minutes | Escalation trigger | L177 |

---

## 9. Severity Classifications

### Severity Matrix (Section 2.4, L202-208)

| Severity | Label | Auto-Declare DR | Notification Channel | Response Time |
|---|---|---|---|---|
| **SEV0** | Data Loss / Safety Breach | Yes - containment only, escalate immediately | Discord + Gotify + SMS | Immediate |
| **SEV1** | Service Degraded > 50% | Yes - autonomous recovery attempt | Discord + Gotify | < 5 min |
| **SEV2** | Component Failure | Yes - self-healing attempt | Discord per cadence | < 15 min |
| **SEV3** | Minor Anomaly | No - standard incident handling | Discord daily summary | < 1 hour |
| **SEV4** | Informational | No - log and monitor | Weekly summary | < 24 hours |

### Status Update Cadence (Section 11.3, L2286-2292)

| Severity | Initial Alert | Update Frequency | Final Update |
|---|---|---|---|
| SEV0 | Immediate (all channels) | Every 5 minutes | Recovery complete + postmortem |
| SEV1 | < 5 min (Discord + Gotify) | Every 15 minutes | Recovery complete + summary |
| SEV2 | < 15 min (Discord) | Every 30 minutes | Recovery complete |
| SEV3 | Next daily summary | Daily summary inclusion | Weekly summary |
| SEV4 | Weekly summary | N/A | Included in weekly report |

### Message Template Labels (L2238-2282)
- SEV0: `[SEV0 DR ALERT]`
- SEV1: `[SEV1 DR ALERT]`
- SEV2: `[SEV2 DR NOTICE]`
- Recovery: `[DR RECOVERY COMPLETE]`
---

## 10. Safe-Word Handling

| # | Context | Exact Quote / Description | Line |
|---|---|---|---|
| 1 | Hard escalation boundary | `Safety system anomaly (safe-word response failure, persona drift > threshold, distress handling failure)` | L183 |
| 2 | Safety-first recovery priority | `Safety systems (persona.safety_config, safe-word enforcement, distress handling) - Jika safety compromised, tidak ada yang lain yang matter.` | L247 |
| 3 | Safety invariants not budget-constrained | `Safe-word enforcement, persona safety boundaries, distress handling, dan encryption integrity tidak pernah dikompromikan demi penghematan biaya. Item-item ini memiliki zero budget constraint.` | L95 |
| 4 | Full VPS loss safety risk | `Guinevere tidak bisa enforce safe-word, respond to distress, atau maintain persona safety boundaries.` | L1219 |
| 5 | Safe-word response time metric | Normal Range: < 500ms, Alert Threshold: Timeout or wrong response, Action: SEV1 immediate escalation | L1500 |
| 6 | Safety validation in quarterly drill | `Run safe-word, distress handling, yandere cap tests` | L2021 |
| 7 | Recovery confirmation step | `Safety validation: Safe-word test, persona bounds check, distress handling test` | L2299 |
| 8 | Full VPS recovery checklist | `Safe-word enforcement: tested and passing` | L1313 |
| 9 | Persona recovery SQL | `SELECT safeword, response_action, is_active FROM persona.safety_config WHERE is_active = true;` | L1521 |
| 10 | Escalation boundary | `Safety system anomaly - Safe-word response failure, persona drift > threshold` | L1806 |

### Safe-Word Summary
The DRPlan treats safe-word as a **zero-tolerance, zero-budget-constraint** safety invariant. Safe-word enforcement is:
- Priority 1 in recovery order (before database, before core service)
- Must be tested after every recovery event
- Failure triggers SEV1 immediate escalation
- Part of quarterly drill safety validation
- Protected from budget trade-offs

---

## 11. Forbidden Patterns (F-01 through F-15)

**NOT FOUND in DRPlan.**

The DRPlan does not contain any F-01 through F-15 forbidden pattern references. The document references `FORBIDDEN actions respected during DR` in the compliance alignment section (L2414: `Guinevere_Security_Policy_v1.0.md - No plaintext secrets in backup logs; SOPS+age encryption standard; FORBIDDEN actions respected during DR`), but does not enumerate or define F-01 through F-15 patterns. These are expected to be defined in the Security Policy document.

---

## 12. Cost Figures

### Budget Framework

| Figure | Context | Line |
|---|---|---|
| **30 USD/month** | Total hard cap budget | L85, L104, L2217, L2328 |
| **3 USD/month** | DR sub-budget cap | L85, L121, L144, L2180, L2184, L2214, L2328, L2357 |
| **36 USD/year** | Annual DR budget (3 x 12) | L2184, L2742 |
| **18.76 USD/year** | Projected annual DR cost (executive summary) | L85 |
| **1.56 USD/month** | Average monthly DR cost (executive summary) | L85 |
| **19.38 USD/year** | Total annual DR cost (cost analysis section) | L2183 |
| **1.62 USD/month** | Average monthly cost (cost analysis section) | L2183 |
| **18.78 USD/year** | Annual total from Appendix G projection table | L2742 |
| **1.57 USD/month** | Average from Appendix G (also in document footer) | L2744, L2819 |
| **0.61 USD/month** | Headroom at Month 12 (cost analysis) | L2185 |
| **0.69 USD/month** | Headroom at Month 12 (Appendix G) | L2744 |

### B2 Pricing Basis (Section 10.1, L2123-2131)

| Component | Rate |
|---|---|
| Storage | 0.005 USD/GB/month |
| Download (egress) | 0.01 USD/GB |
| Upload (ingress) | FREE |
| API transactions (Class B) | 0.004 USD per 10,000 |
| API transactions (Class C) | 0.004 USD per 1,000 |
| Early deletion | None |
| Free egress allowance | 1 GB/day (~30 GB/month) |

### Monthly Cost Projections

| Month | Total Cost | Budget | Headroom |
|---|---|---|---|
| Month 1 | 0.995 USD | 3.00 USD | 2.01 USD |
| Month 6 | 1.60 USD | 3.00 USD | 1.40 USD |
| Month 12 | 2.39 USD | 3.00 USD | 0.61 USD |
| M12 (optimized) | ~2.09 USD | 3.00 USD | 0.91 USD |

### Cost Optimization Strategies (Section 10.5, L2191-2198)

| Strategy | Estimated Savings |
|---|---|
| Retention reduction (monthly 6 to 4, weekly 4 to 3) | ~0.20 USD/month |
| Evidence archival (>90 days) | ~0.10 USD/month |
| WAL batching | ~0.05 USD/month |
| Incremental object storage | ~0.08 USD/month |
| Deduplication (restic/borg) | ~0.30 USD/month |

### Budget Alert Thresholds (Section 10.6, L2212-2219)

| Metric | Target | Warning | Critical |
|---|---|---|---|
| Monthly DR storage cost | <= 3.00 USD | > 2.50 USD | > 2.80 USD |
| Monthly DR download cost | <= 0.50 USD | > 0.30 USD | - |
| DR cost as pct of total | <= 10% | > 8% | - |
| M9 cost trigger for optimization | - | > 2.50 USD | - |
---

## 13. SDLC Loop References

| # | Reference | Context | Line |
|---|---|---|---|
| 1 | SDLC loop cascade failure | Listed as one of 9 failure scenarios | L82 |
| 2 | SDLC loop cascade | Autonomous recovery category: Mass terminate + resource cleanup + respawn | L175 |
| 3 | Agent loop state (SDLC projects schema) | RTO/RPO matrix entry | L230 |
| 4 | SDLC loops (guinevere-loops service) | Recovery priority 6 | L252 |
| 5 | SDLC Loop State Backup | Section 4.6 heading | L945 |
| 6 | Agent loop state persisted to projects schema every phase transition | References AgentLoopSpec_v2.0 | L949 |
| 7 | SDLC Loop Cascade Failure | Scenario 6 heading | L1524 |
| 8 | SDLC loops: test loop completes Phase 1 | Full VPS recovery checklist | L1318 |
| 9 | Loop Guardian | Component that monitors SDLC loop health | L1532, L1789, L2395, L2771 |
| 10 | Loop Guardian (per Guinevere_AgentLoopSpec_v2.0.md) | Referenced in self-healing section | L1789 |

### Phase References
- The document mentions `loop_phase` and `'Execute'` as a phase name (L981) but does NOT enumerate specific phase counts (7-phase or 8-phase)
- `Guinevere_AgentLoopSpec_v2.0.md` is referenced (L30, L949, L1789) as the authoritative source for loop phases
- Tables referenced: loop_instances, agent_tasks, tasks, evidence_artifacts (all in projects schema)

### 7-phase or 8-phase Explicit Mention
**NOT FOUND** in DRPlan. The document references phase transition and loop_phase = 'Execute' but does not state a specific number of SDLC phases. The AgentLoopSpec document is the authoritative source.

---

## 14. Related Documents Table

### Complete Related Documents Table (Section, L18-35)

| Document | Relationship |
|---|---|
| Guinevere_SRS_v1.0.md | Non-functional requirements for availability and recovery |
| Guinevere_DatabaseERD_MigrationStrategy_v1.0.md | 12 schemas, TimescaleDB hypertables, HNSW indexes, Merkle chain |
| Guinevere_DeploymentGuide_v1.0.md | Infrastructure reference, 17 services, backup timer |
| Guinevere_Security_Policy_v1.0.md | SOPS+age encryption, secrets management |
| Guinevere_DataGovernance_ClassificationPolicy_v1.0.md | Data classification, retention policies |
| Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md | Incident classification, 10 runbooks |
| Guinevere_ObservabilityAlertingSpec_v1.0.md | Monitoring and alerting for DR events |
| Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md | Availability SLOs, error budgets |
| Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md | Break-glass, backup-operator principal |
| Guinevere_Cost_FinOps_Model_v1.0.md | 30 USD/month budget, DR cost constraints |
| Guinevere_AgentLoopSpec_v2.0.md | Loop state recovery, self-healing |
| Guinevere_AcceptanceCriteriaCatalog_v1.0.md | AC-OPS-003 RTO/RPO requirements |
| Guinevere_EncryptionKeyManagement_v1.0.md | Key backup and rotation |
| Guinevere_SecretsRotationRunbook_v1.0.md | Secret recovery procedures |
| adr/ADR-025-backup-disaster-recovery-strategy.md | ADR-025 Backup and DR Strategy |
| adr/ADR-028-llm-router-outage-graceful-degradation.md | 4-tier LLM failover chain |

### Research Report Sources (L39-46)

| Report | Content Used |
|---|---|
| research-reports/2026-05-30-dr-plan-backup-architecture-research.md | Backup strategy, storage architecture, verification procedures |
| research-reports/2026-05-30-dr-plan-recovery-procedures-research.md | Recovery procedures, self-healing patterns, failure catalog |
| research-reports/2026-05-30-dr-plan-cost-governance-research.md | Cost analysis, testing schedule, governance framework |

### Additional Document References (in body text)

| Document | Context | Line |
|---|---|---|
| Guinevere_Cost_FinOps_Model_v1.0.md section 4.1 | 30 USD/month hard cap, dollar 2-3 S3 allocation | L85, L104, L144 |
| Guinevere_Cost_FinOps_Model_v1.0.md section 4.2 | Zero budget items (safety invariants) | L146 |
| Guinevere_DataGovernance_ClassificationPolicy_v1.0.md section 4.1 | 5 classification tiers | L139 |
| Guinevere_DataGovernance_ClassificationPolicy_v1.0.md section 4.2 | Highest classification wins | L99, L140 |
| Guinevere_DataGovernance_ClassificationPolicy_v1.0.md section 6.4 | Restore reconciliation mandatory | L141 |
| Guinevere_DataGovernance_ClassificationPolicy_v1.0.md section 8.1 | Encryption before upload | L138 |
| Guinevere_EncryptionKeyManagement_v1.0.md section 5.2 | Backup KEK domain, key isolation | L138, L142, L433, L1099 |
| Guinevere_EncryptionKeyManagement_v1.0.md section 8 | Classification drives encryption tier | L139 |
| Guinevere_Security_Policy_v1.0.md section 3 | No plaintext secrets in backup logs | L143 |
| Guinevere_ObservabilityAlertingSpec_v1.0.md section 5 | Audit trail for backup ops | L143 |
| Guinevere_DeploymentGuide_v1.0.md section 2.1.3 | Essential tools installation | L1240 |
| Guinevere_DeploymentGuide_v1.0.md section 2.2 | OS hardening (CIS) | L1243 |
| Guinevere_DeploymentGuide_v1.0.md section 2.4 | pyenv + Python 3.12 | L1246 |
| Guinevere_DeploymentGuide_v1.0.md section 3.5 | Backup 02:00, deploy 03:00 | L137 |
| Guinevere_AgentLoopSpec_v2.0.md | Loop state recovery, Loop Guardian | L30, L949, L1789 |
| Guinevere_AcceptanceCriteriaCatalog_v1.0.md (AC-OPS-003) | RTO <= 4h, RPO <= 24h | L31, L216, L228, L2008 |
| adr/ADR-Index.md | ADR-025 is CRITICAL-risk | L118 |
---

## 15. Evidence Directory Paths

### Evidence Path Structure (Section 13.1, L2427-2446)

- evidence/dr-drills/YYYY-MM/partial-<component>.md (Monthly partial drill reports)
- evidence/dr-drills/YYYY-MM/full-q<N>.md (Quarterly full drill reports)
- evidence/dr-drills/YYYY-MM/annual-tabletop-YYYY.md (Annual tabletop exercise)
- evidence/dr-drills/YYYY-MM/drill-scorecard-YYYY-MM-DD.md (Individual drill scorecards)
- evidence/dr-drills/README.md (DR drills index)
- evidence/incidents/YYYY-MM-DD-SEV<N>-<slug>/incident-report.md
- evidence/incidents/YYYY-MM-DD-SEV<N>-<slug>/recovery-evidence.md
- evidence/incidents/YYYY-MM-DD-SEV<N>-<slug>/root-cause-analysis.md
- evidence/incidents/YYYY-MM-DD-SEV<N>-<slug>/postmortem.md
- evidence/scorecards/YYYY-MM-scorecard.md (Monthly SLO scorecards)
- evidence/dr-plan/review-YYYY-MM-DD.md (DR Plan review records)

### Specific Scheduled Evidence Paths (12-Month Calendar, L1980-1991)

| Month | Path |
|---|---|
| Jun 2026 | evidence/dr-drills/2026-06/partial-pgdb.md |
| Jul 2026 | evidence/dr-drills/2026-07/partial-redis.md |
| Aug 2026 | evidence/dr-drills/2026-08/partial-evidence.md |
| Sep 2026 | evidence/dr-drills/2026-09/full-q3.md |
| Oct 2026 | evidence/dr-drills/2026-10/partial-config.md |
| Nov 2026 | evidence/dr-drills/2026-11/partial-objects.md |
| Dec 2026 | evidence/dr-drills/2026-12/full-q4.md |
| Jan 2027 | evidence/dr-drills/2027-01/partial-pitr.md |
| Feb 2027 | evidence/dr-drills/2027-02/partial-keyrotate.md |
| Mar 2027 | evidence/dr-drills/2027-03/full-q1.md |
| Apr 2027 | evidence/dr-drills/2027-04/partial-erasure.md |
| May 2027 | evidence/dr-drills/2027-05/partial-failover.md |

### Other Directory Paths Referenced

| Path | Context | Line |
|---|---|---|
| audit-reports/*** | Included in evidence backup rsync | L888 |
| research-reports/*** | Included in evidence backup rsync | L889 |
| adr/*** | Included in evidence backup rsync | L890 |
| /home/guinevere/data/backups/ | Local backup staging | L289, L493, L994 |
| /home/guinevere/data/backups/staging/ | Age-encrypted staging | L293, L341 |
| /home/guinevere/data/backups/wal_staging/ | WAL staging directory | L452, L655 |
| /home/guinevere/data/backups/wal_archive/ | WAL archive directory | L288, L418 |
| /home/guinevere/data/backups/redis/ | Redis backup directory | L720, L1003 |
| /home/guinevere/data/backups/sops/ | SOPS backup directory | L832, L1006 |
| /home/guinevere/data/backups/evidence/ | Evidence backup directory | L880, L1008 |
| /home/guinevere/data/backups/chunks/ | TimescaleDB chunk backups | L568, L1010 |
| /home/guinevere/data/backups/audit_exports/ | Audit export directory | L1013, L2582 |
| /home/guinevere/data/backups/age_keys/ | Age key escrow directory | L807, L1015 |
| /home/guinevere/secrets/ | SOPS secrets directory | L831, L1453 |
| /home/guinevere/scripts/ | Script directory | L359, L417 |
| /var/lib/postgresql/wal_archive/ | PostgreSQL WAL archive mount | L288, L418 |
| /var/lib/postgresql/data/ | PostgreSQL data directory | L416, L654 |
| /etc/sops/age/keys.txt | Age key location | L454, L628, L795 |
---

## 16. Operator Questionnaire Values

| Questionnaire Item | Found in DRPlan? | Exact Value / Quote | Line |
|---|---|---|---|
| Risk-Based Testing with STRIDE | **NOT FOUND** | No explicit STRIDE reference in DRPlan | - |
| Safe-word ZERO tolerance | **Found (conceptual)** | `Safe-word enforcement... tidak pernah dikompromikan demi penghematan biaya. Item-item ini memiliki zero budget constraint.` (uses `zero budget constraint` language, not `ZERO tolerance` verbatim) | L95 |
| 30 USD hard cap | **Found** | `30 USD/bulan hard cap budget (per Guinevere_Cost_FinOps_Model_v1.0.md section 4.1)` | L85, L104 |
| Single VPS + offline backup | **Found** | `Single VPS hostdata.id (4C/16GB/120GB, Ubuntu 24.04)` + `Backblaze B2 dengan age encryption` + `age Key Escrow: Layer 0 - Samm Recovery Root - Offline (printed QR, USB drive in safe)` | L80, L112, L794 |
| 95% autonomous operations | **NOT FOUND** as explicit questionnaire value | The document mentions 6 autonomous recovery categories and `99.5% availability SLO` (L2415), `>= 95% RPO compliance` (L267), but does not state `95% autonomous operations` as an operator questionnaire response | - |

### DR Questionnaire References (DR-Q*)
The document references specific questionnaire items by ID without quoting the full questions:
- DR-Q13, Q14 (PostgreSQL RTO/RPO, L220)
- DR-Q15, Q16 (Redis, L225)
- DR-Q17 (Service restart, L227, L235, L236)
- DR-Q18 (Full VPS loss, L228)
- DR-Q19, Q42 (Evidence, L229)
- DR-Q20 (Loop state, L230)
- DR-Q21 (Observability, L231)
- DR-Q22 (Surveillance, L232)
- DR-Q28 (TimescaleDB hypertables, L221, L222, L223)
- DR-Q29, Q43 (Merkle chain, L224)
- DR-Q35 (Cache warming, L226)
- DR-Q36 (SOPS secrets, L233)
- DR-Q44 (Persona state, L234)
- DR-Q46 (Surveillance retention, L222)
- DR-Q47 (Financial retention, L223, L237)
- DR-Q61-68 (Verification over trust, L145)

---

## 17. Samm Review Record

### Present in Document Header? **YES**

**Exact text (L9):**
> `Samm Review Record: Reviewed and approved by Samm on 2026-05-30.`

### Fields in Review Record

| Field | Value | Line |
|---|---|---|
| Reviewer | Samm (Operator) | L7 |
| Review Date | 2026-05-30 | L8 |
| Samm Review Record | Reviewed and approved by Samm on 2026-05-30 | L9 |
| Document Owner | Guinevere (with Samm approval authority) | L10 |
| Review Cadence | Quarterly (aligned with DR drill schedule) | L11 |
| Next Review Due | 2026-08-30 | L12 |

### Footer Confirmation (L2803-2812)
| Field | Value |
|---|---|
| Reviewer | Samm (Operator) |
| Approved | 2026-05-30 |
| Next Review | 2026-08-30 |

### Revision History (L2777-2779)
| Version | Date | Author | Changes | Reviewer |
|---|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere (Autonomous Agent) | Initial comprehensive DR Plan: 14 sections, 9 recovery scenarios, self-healing architecture, cost analysis, 12-month testing calendar | Samm (Approved 2026-05-30) |
---

## 18. Infrastructure Topology

### Primary VPS

| Attribute | Value | Line |
|---|---|---|
| Provider | hostdata.id | L80, L150, L281, L1210, L1231, L1233, L2031 |
| OS | Ubuntu 24.04 | L80, L1231 |
| CPU | 4 cores (4C) | L80, L281, L1301 |
| RAM | 16 GB | L80, L281, L1301 |
| Disk | 120 GB SSD | L80, L281, L1031, L1301 |
| Services | 17+ systemd services + Docker containers, 24/7 | L80 |

### Docker Containers

| Container | Image | Key Config |
|---|---|---|
| postgresql | timescale/timescaledb:latest-pg16 | shared_buffers=2GB, effective_cache_size=6GB, max_connections=200 |
| redis | redis:7-alpine | maxmemory 1gb, allkeys-lru, dual persistence |

### External Services
| Service | Role | Line |
|---|---|---|
| Backblaze B2 | Offsite backup storage (S3-compatible) | L112, L296, L1036, L2121 |
| Cloudflare Tunnel | External access (guinevere-tunnel) | L238, L1590-1595 |
| Tailscale | Mesh networking (peers: android-hp, windows-laptop) | L184, L1209, L1254 |
| UptimeRobot | External uptime monitoring (5-min interval) | L184, L1208, L1807, L2234 |
| Discord | Primary communication channel | L332, L2231 |
| Gotify | Push notification backup channel | L204, L2232 |
| Gmail SMTP | Email last resort | L2233 |

### Cloudflare Tunnel Details
- Tunnel name: guinevere-tunnel (L1590)
- DNS route: guinevere.example.com (L1595) - Note: example.com is a placeholder

### Tailscale Peers
- android-hp (L1254)
- windows-laptop (L1254)

### GitHub Repository
- git@github.com:samm/guinevere-de-baroque.git (L1261)

### Monitoring VPS
**NOT FOUND** in DRPlan. No separate monitoring VPS is mentioned. The observability stack (Prometheus/Grafana/Loki) runs on the same primary VPS.

### IP Addresses
**NOT FOUND** in DRPlan. No specific IP addresses are given (new VPS IP referenced as NEW_IP placeholder at L1232).

### Network
- SSH: port 2222 (hardened)
- Firewall: UFW - only port 2222 SSH open
- 172.16.0.0/12 - Docker internal network allowed in pg_hba.conf (L384)
- 127.0.0.1/32 - localhost connections (L383, L387)

---

## 19. Feature Flags

**NOT FOUND in DRPlan.**

The document contains no references to feature flags, feature flag names, or feature flag governance. Feature flag governance is expected to be covered in a separate document per the AGENTS.md Enterprise Gap Backlog item 26 (Feature Flag Governance).

---

## 20. Incident Response

### Incident Classification (derived from SEV matrix, L202-208)

| Severity | Criteria | Response |
|---|---|---|
| SEV0 | Data Loss / Safety Breach | Immediate; containment only, escalate to Samm; Discord + Gotify + SMS |
| SEV1 | Service Degraded > 50% | < 5 min; autonomous recovery attempt; Discord + Gotify |
| SEV2 | Component Failure | < 15 min; self-healing attempt; Discord per cadence |
| SEV3 | Minor Anomaly | < 1 hour; standard incident handling; Discord daily summary |
| SEV4 | Informational | < 24 hours; log and monitor; Weekly summary |

### DR Declaration Authority (L192-198)

| Role | Responsibility | Actor |
|---|---|---|
| DR Coordinator | Approval for full recovery, DR drill declaration, budget approval | Samm |
| DR Executor | Autonomous P0 containment, backup retry, cache warming, self-healing | Guinevere |
| DR Auditor | Verification of recovery completeness, evidence validation, scorecard | Guinevere (Oracle sub-agent) |
| DR Communicator | Status updates via Discord/Gotify/Email per cadence | Guinevere |

### 9 Recovery Scenarios

| # | Scenario | Severity | RTO Target | Auto-Recovery | Section |
|---|---|---|---|---|---|
| 1 | Full VPS Loss | SEV0-SEV1 | 4 hours | No | 6.1 |
| 2 | PostgreSQL Corruption | SEV0-SEV1 | 15 min - 1 hour | No | 6.2 |
| 3 | Redis Data Loss | SEV2 | 5 min | Yes | 6.3 |
| 4 | SOPS/Age Key Compromise | SEV0 | 1 hour | No (always escalate) | 6.4 |
| 5 | Memory/Persona State Corruption | SEV1-SEV2 | 30 min | Semi-auto | 6.5 |
| 6 | SDLC Loop Cascade Failure | SEV1-SEV2 | 5 min | Yes | 6.6 |
| 7 | Network Isolation (Tailscale/Cloudflare) | SEV1-SEV2 | 15 min | Semi-auto | 6.7 |
| 8 | Disk Full / OOM Killer | SEV1-SEV2 | 5 min | Yes | 6.8 |
| 9 | External API Key Expiry | SEV2-SEV3 | 15 min per provider | Semi-auto | 6.9 |

### Communication Channels (Priority Order, L2229-2234)

| Priority | Channel | Use Case |
|---|---|---|
| 1 | Discord (DM to Samm) | Primary for all DR events |
| 2 | Gotify (push notification) | Backup if Discord unavailable |
| 3 | Email (Gmail SMTP) | Last resort for SEV0 |
| 4 | SMS (via UptimeRobot) | Only for SEV0 full VPS loss |

### Escalation Paths (L1800-1813)

Hard escalation to Samm (no exceptions):
1. PostgreSQL data corruption detected
2. age/SOPS key compromise suspected
3. Safety system anomaly (safe-word response failure, persona drift)
4. Full VPS unreachable
5. Network isolation > 15 minutes
6. Financial data integrity concern
7. Merkle chain breakage
8. Recovery action could cause data loss
9. Unknown failure mode
10. Self-healing fails after max attempts

### Postmortem Requirements
- Required for SEV0-SEV2 DR events (L2416)
- Evidence path: evidence/incidents/YYYY-MM-DD-SEV<N>-<slug>/ (L2456)
- Required artifacts: incident-report.md, recovery-evidence.md, root-cause-analysis.md, postmortem.md (L2438-2441)

### Risk Register (18 Risks, Section 12.4, L2385-2404)

| ID | Risk | Probability | Impact | Risk Level |
|---|---|---|---|---|
| DR-R01 | Full VPS loss | Low (5%/yr) | Critical | HIGH |
| DR-R02 | PostgreSQL data corruption | Medium (15%/yr) | Critical | HIGH |
| DR-R03 | age/SOPS key compromise | Low (2%/yr) | Critical | MEDIUM |
| DR-R04 | B2 storage provider outage | Low (1%/yr) | High | MEDIUM |
| DR-R05 | Backup job failure (silent) | Medium (10%/yr) | High | MEDIUM |
| DR-R06 | Network isolation | Medium (20%/yr) | High | MEDIUM |
| DR-R07 | Disk full / OOM killer | High (40%/yr) | Medium | MEDIUM |
| DR-R08 | Redis data loss | Medium (15%/yr) | Medium | MEDIUM |
| DR-R09 | SDLC loop cascade failure | Medium (25%/yr) | Medium | MEDIUM |
| DR-R10 | External API key expiry | High (60%/yr) | Low | LOW |
| DR-R11 | Persona state corruption | Low (5%/yr) | High | MEDIUM |
| DR-R12 | Merkle chain breakage | Low (3%/yr) | Critical | MEDIUM |
| DR-R13 | TimescaleDB chunk corruption | Low (8%/yr) | Medium | LOW |
| DR-R14 | pgvector HNSW index corruption | Low (5%/yr) | Medium | LOW |
| DR-R15 | DR drill failure (score < 80) | Low (10%/yr) | Medium | LOW |
| DR-R16 | Budget exceedance (>3 USD/month) | Medium (30%/yr at M12) | Low | LOW |
| DR-R17 | Evidence artifact loss | Low (5%/yr) | Medium | LOW |
| DR-R18 | Surveillance data buffer overflow | Medium (20%/yr) | Low | LOW |
---

## Cross-Validation Notes

### Potential Conflicts to Investigate in Other Documents

1. **Annual cost discrepancy**: Executive summary says 18.76 USD (average 1.56/bulan) (L85) but cost analysis section says ~19.38 USD (average 1.62/month) (L2183) and Appendix G says 18.78 USD (average 1.57/month) (L2742, L2744, L2819). Three different values for projected annual cost.

2. **Service count**: Document states 17+ systemd services (L80, L22, L228) but only explicitly names 11 unique systemd unit names. The remaining 6+ may be Docker containers or other services not named in this document.

3. **Agent Loop Spec version**: References Guinevere_AgentLoopSpec_v2.0.md (L30, L949, L1789) - this is v2.0, not v1.0 as listed in the original seed documents.

4. **Database name**: Uses `guinevere` (L495) as the single database name with 12 schemas. Other documents may reference `guinevere_memory` or different database names.

5. **Port coverage**: Only 3 ports mentioned (5432, 9091, 2222). Deployment Guide likely has more port assignments.

6. **SDLC phases**: References AgentLoopSpec_v2.0.md for loop phases but does not enumerate whether 7-phase or 8-phase. Only mentions `loop_phase = 'Execute'` as a specific phase name.

7. **Forbidden patterns (F-01 through F-15)**: Completely absent. References Security Policy for FORBIDDEN actions but does not enumerate them.

8. **Feature flags**: Completely absent. No mention of any feature flag governance.

9. **STRIDE**: Not mentioned. Risk register uses custom probability/impact matrix instead of STRIDE threat modeling.

10. **Monitoring VPS**: Not mentioned. All observability runs on primary VPS.

---

## Extraction Summary

| Category | Items Found | Status |
|---|---|---|
| 1. Service names | 13 unique services + 6 infrastructure components | COMPLETE |
| 2. Port numbers | 3 ports (5432, 9091, 2222) | COMPLETE |
| 3. Database names/schemas | 1 DB, 12 schemas, 13 tables, 6 Redis DBs, 4 HNSW indexes | COMPLETE |
| 4. ADR references | 7 ADRs (003, 008, 010, 015, 020, 025, 028) | COMPLETE |
| 5. RTO/RPO values | 20 components with RPO/RTO specifications | COMPLETE |
| 6. Backup schedule/timing | 17 timing entries, 5 retention tiers, 7 data-specific retentions | COMPLETE |
| 7. systemd unit names | 11 unique units + wildcard references | COMPLETE |
| 8. Monitoring thresholds | 30 numeric thresholds | COMPLETE |
| 9. Severity classifications | SEV0-SEV4 with full definitions | COMPLETE |
| 10. Safe-word handling | 10 references with procedures | COMPLETE |
| 11. Forbidden patterns | **NOT FOUND** in DRPlan | ABSENT |
| 12. Cost figures | 20+ dollar amounts with full projections | COMPLETE |
| 13. SDLC loop references | 10 references (no phase count) | COMPLETE |
| 14. Related Documents table | 16 documents + 3 research reports + 15+ inline references | COMPLETE |
| 15. Evidence directory paths | 10+ path patterns + 12 specific scheduled paths | COMPLETE |
| 16. Operator questionnaire | Partial (4/5 items found) | PARTIAL |
| 17. Samm Review Record | Present, approved 2026-05-30 | COMPLETE |
| 18. Infrastructure topology | VPS specs, Docker, external services; no IPs or monitoring VPS | PARTIAL |
| 19. Feature flags | **NOT FOUND** in DRPlan | ABSENT |
| 20. Incident response | 9 scenarios, 5 severity levels, 4 channels, 18 risks | COMPLETE |

---

| Field | Value |
|---|---|
| Report | DRPlan Cross-Reference Extraction |
| Source | Guinevere_DisasterRecoveryPlan_v1.0.md (2819 lines) |
| Date | 2026-05-30 |
| Extractor | Guinevere (Autonomous Agent) |
| Status | Complete - ready for cross-document validation |