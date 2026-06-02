# OpsManual Cross-Reference Extraction Report

**Date:** 2026-05-30
**Source Document:** `Guinevere_InternalOpsManual_v1.0.md`
**Source Size:** 2353 lines (~105KB)
**Extractor:** Guinevere (Codebase Search Specialist)
**Purpose:** Exhaustive extraction of all cross-reference facts for cross-document validation

---

## 1. Service Names

### 1.1 Guinevere Systemd Services (8 unique names)

| # | Service Name | Type | Line References | Context |
|---|---|---|---|---|
| 1 | `guinevere-core` | systemd | L206, L234, L651, L661, L819, L1545, L1548, L2099 | Core daemon, FastAPI; health at `http://127.0.0.1:8100/health` |
| 2 | `guinevere-surveillance` | systemd | L206, L235, L652, L819, L1545, L1549, L2100 | Surveillance ingestion; health at `http://127.0.0.1:8000/health` |
| 3 | `guinevere-scheduler` | systemd | L206, L236, L652, L661, L819, L1545, L1549, L2101 | APScheduler-based job scheduling |
| 4 | `guinevere-loops` | systemd | L207, L237, L652, L661, L820, L1545, L1549, L2102 | Autonomous SDLC loop execution |
| 5 | `guinevere-discord` | systemd | L207, L238, L820, L2103 | Discord bot gateway |
| 6 | `guinevere-whatsapp` | systemd | L207, L239, L821, L2104 | Baileys WhatsApp session |
| 7 | `guinevere-windows-sync` | systemd | L207, L240, L820, L2105 | Remote sync to Windows machine |
| 8 | `guinevere-ollama` | systemd | L208, L821, L2106 | Local LLM (Ollama) integration |

### 1.2 Guinevere Timer Units (2 unique names)

| # | Timer Name | Line References | Schedule | Purpose |
|---|---|---|---|---|
| 1 | `guinevere-backup.timer` | L284, L565, L2066 | 02:00 WIB daily | Triggers daily backup |
| 2 | `guinevere-selfdeploy.timer` | L619, L1557, L2069 | 03:00 Asia/Jakarta daily | Triggers nightly self-deploy |

### 1.3 Non-Guinevere Systemd Services (5 names)

| # | Service Name | Line References | Type |
|---|---|---|---|
| 1 | `caddy` | L208, L246, L821, L2107 | systemd - TLS/reverse proxy |
| 2 | `tailscaled` | L208, L247, L821, L2108 | systemd - Tailscale mesh VPN |
| 3 | `cloudflared` | L208, L248, L821, L2109 | systemd - Cloudflare tunnel |
| 4 | `fail2ban` | L208, L249, L821, L2110 | systemd - Brute-force protection |
| 5 | `crowdsec` | L208, L250, L821, L2111 | systemd - Crowd-sourced security |

### 1.4 Docker Containers (6 names)

| # | Container Name | Line References | Health Check |
|---|---|---|---|
| 1 | `postgresql` | L221, L241, L296, L576, L825, L2112 | `docker inspect` or `pg_isready` |
| 2 | `redis` | L224, L242, L581, L825, L2113 | `redis-cli ping` |
| 3 | `prometheus` | L243, L825, L836, L2114 | `http://127.0.0.1:9090/-/healthy` |
| 4 | `grafana` | L244, L825, L837, L2115 | `http://127.0.0.1:3000/api/health` |
| 5 | `loki` | L245, L825, L838, L2116 | `http://127.0.0.1:3100/ready` |
| 6 | `pgbouncer` | L227, L825, L2117 | `psql -h 127.0.0.1 -p 6432 -c 'SHOW POOLS;'` |

### 1.5 Summary

- **Total unique Guinevere services:** 8 systemd + 2 timers = 10 systemd units
- **Total non-Guinevere systemd services:** 5
- **Total Docker containers:** 6
- **Grand total services monitored:** 19 (stated as '17+' in document - actual count is 19 in Appendix B)
- **Note:** `guinevere-api` is NOT mentioned as a separate service. `guinevere-memory` is NOT mentioned as a separate service. `guinevere-backup` exists as `.timer` and `.service` pair.

---

## 2. Port Numbers

| Port | Service/Component | Line References | Protocol | Context |
|---|---|---|---|---|
| 8100 | guinevere-core (FastAPI health) | L214, L635, L640, L654, L834, L1551 | HTTP | `/health` endpoint |
| 8000 | guinevere-surveillance (API) | L215, L235, L835 | HTTP | `/health` endpoint |
| 9090 | Prometheus | L216, L836, L2114 | HTTP | `/-/healthy` endpoint |
| 3000 | Grafana | L217, L837, L2115 | HTTP | `/api/health` endpoint |
| 3100 | Loki | L218, L838, L2116 | HTTP | `/ready` endpoint |
| 6432 | PgBouncer | L227, L2117 | TCP/PostgreSQL | Connection pooling for PostgreSQL |
| 5432 | PostgreSQL (implicit) | Not directly mentioned | TCP | Not explicitly referenced; 6432 (PgBouncer) used instead |
| 6379 | Redis (implicit) | Not directly mentioned | TCP | Accessed via `docker exec redis redis-cli` |

---

## 3. Database Names and Schemas

### 3.1 Database Names

| Database Name | Line Reference | Context |
|---|---|---|
| `guinevere` | L577 | `pg_dump -U postgres -Fc --verbose -f /tmp/guinevere_DATE.dump guinevere` |

### 3.2 Table Names Referenced in SQL Queries (28 unique tables)

| # | Table Name | Line References | Context |
|---|---|---|---|
| 1 | `alert_history` | L257, L263, L269, L684, L1959 | Alert event storage |
| 2 | `backup_log` | L302, L611 | Backup execution log |
| 3 | `llm_cost_ledger` | L324, L335, L342, L424, L494, L683, L884, L1039, L1194, L1958 | LLM usage cost tracking |
| 4 | `tasks` | L364, L370, L398, L406, L446, L545, L680, L869, L1957 | Task tracking |
| 5 | `projects` | L364, L545 | Project registry |
| 6 | `loop_instances` | L366, L398, L406, L446, L489, L505, L679, L867, L868, L903, L907, L910, L1956 | SDLC loop state tracking |
| 7 | `evidence_files` | L445 | Evidence artifact storage |
| 8 | `slo_daily_snapshot` | L457 | SLO daily values |
| 9 | `persona_daily_metrics` | L467 | Persona metrics aggregation |
| 10 | `persona_drift_log` | L470, L534, L928 | Persona drift tracking |
| 11 | `loop_quality_scores` | L505, L910 | LQS component scores |
| 12 | `loop_guardian_log` | L511, L908 | Loop Guardian interventions |
| 13 | `inner_journal` | L526, L686 | Guinevere self-reflection journal |
| 14 | `memories` | L530, L681 | Memory storage with embeddings |
| 15 | `persona_categories` | L536 | Persona drift categories |
| 16 | `subagent_sessions` | L870 | Sub-agent tracking |
| 17 | `redis_info_cache` | L872 | Redis metrics cache |
| 18 | `llm_route_metrics` | L889 | LLM routing performance |
| 19 | `persona_events` | L930 | Persona safety events |
| 20 | `distress_events` | L933 | Distress detection events |
| 21 | `cost_freeze_log` | L1044 | Cost freeze trigger log |
| 22 | `access_denied_log` | L1066 | RBAC/ABAC denial log |
| 23 | `break_glass_log` | L1070 | Emergency access log |
| 24 | `secret_access_log` | L1072 | Secret access audit log |
| 25 | `resource_metrics` | L1124, L1777 | Resource utilization time-series |
| 26 | `decision_log` | L1871 | Autonomous decision audit |
| 27 | `surveillance_events` | L682, L697 | Surveillance data (TimescaleDB) |
| 28 | `surveillance_metrics` | L698 | Surveillance metrics (TimescaleDB) |

### 3.3 Notes
- `core_memories` and `episodic_memories` table names: **NOT FOUND** in OpsManual. Only `memories` table referenced.
- Database name is `guinevere` (not `guinevere_memory`).
- TimescaleDB used for `surveillance_events` and `surveillance_metrics` (90-day chunk drop at L697-698).
- No explicit schema name (e.g., `public`, `guinevere`) referenced; all queries use default schema.

---

## 4. ADR References

**ADR references found in OpsManual: NONE (no ADR-NNN identifiers)**

ADR-related mentions:

| Reference | Line | Context |
|---|---|---|
| `adr/ADR-Index.md` | L34, L985, L1116 | Architecture Decision Index referenced as cross-reference and monthly check |
| 'ADR Backlog Review' | L1008, L1109-1116 | Monthly procedure to review ADR backlog |
| 'ADR review (all 29 accepted ADRs)' | L1246 | Annual operation: states 29 accepted ADRs exist |
| 'ADR Index consistency' | L985 | Weekly check: compare `adr/ADR-Index.md` with actual ADR files |
| Related Documents table | L34 | 'Architecture decisions affecting operations (29 accepted, 15 backlog)' |

**Key fact:** The document claims **29 accepted ADRs and 15 backlog ADRs** (L34), but does not cite any specific ADR by number (e.g., ADR-001).

---

## 5. RTO/RPO Values

### 5.1 RTO Values (Full DR Drill - Section 8.3, L1163-1174)

| Step | Component | Target RTO | Line |
|---|---|---|---|
| 1 | PostgreSQL pg_restore dari S3/R2 | <= 1 jam | L1167 |
| 2 | Redis state reconstruction | <= 30 menit | L1168 |
| 3 | SOPS/age secrets decryption | <= 15 menit | L1169 |
| 4 | systemd service restart | <= 10 menit | L1170 |
| 5 | Alert routing verification | <= 5 menit | L1171 |
| 6 | Grafana dashboard parity | <= 15 menit | L1172 |
| 7 | Tailscale mesh validation | <= 10 menit | L1173 |
| 8 | Backup reconciliation | <= 30 menit | L1174 |

### 5.2 RPO Values

**Specific RPO numeric values: NOT FOUND as explicit numbers in OpsManual.**

RPO is referenced conceptually:
- L30: Related Documents: `Guinevere_DisasterRecoveryPlan_v1.0.md` described as 'RPO/RTO targets'
- L1699: Metric `guinevere_backup_last_success_timestamp_seconds` alert threshold: '>RPO = SEV1/SEV2'
- L1846: 'Backup management... Must complete within RPO'
- L1932: Escalation: 'Backup failure beyond RPO | SEV1'
- L2319-2320: Glossary: 'RPO = Recovery Point Objective (max data loss)'

**Note:** Exact RPO values are deferred to `Guinevere_DisasterRecoveryPlan_v1.0.md`.

---

## 6. Backup Schedule and Timing

| Backup Aspect | Value | Line Reference |
|---|---|---|
| Backup timer fires | 02:00 WIB daily | L284, L563, L565, L2066 |
| pg_dump expected completion | 02:30 WIB | L311 |
| Backup verification + upload window | 02:05-02:30 WIB | L2067 |
| Log rotation + cleanup | 02:30-03:00 WIB | L728, L2068 |
| Backup retention (local files) | `RETENTION_DAYS=30` (30 days) | L573, L606 |
| WAL streaming | Continuous, lag < 5 menit | L312 |
| Redis RDB snapshot | Together with backup timer | L313 |
| R2 upload | Within 30 minutes | L314 |
| idcloudhost S3 upload | Within 30 minutes | L315 |
| Backup targets | `local+r2+s3` (triple redundancy) | L612-614 |
| Backup encryption | age encryption (`*.age`) | L591-596 |
| Backup content | pg_dump, Redis RDB, config tar.gz (configs + SOPS secrets + systemd units) | L576-588 |
| R2 bucket | `s3://guinevere-backups/`DATE`/` | L599 |
| S3 bucket | `s3://guinevere-backups/`DATE`/` (same bucket, different endpoint) | L603 |
| Journalctl retention | 500MB size / 30d time | L731-732 |
| Docker prune | 168h (7 days) | L735 |
| Log compression | >50MB gzipped | L733 |
| Log deletion | `.log.gz` >30 days deleted | L734 |
| Cache cleanup | >7 days | L737 |
| Temp cleanup | >1 day | L736 |
| TimescaleDB chunk drop | 90 days for `surveillance_events` and `surveillance_metrics` | L697-698 |

---

## 7. Systemd Service Unit Names

### 7.1 Explicitly Named Units

| Unit Name | Type | Line References |
|---|---|---|
| `guinevere-core.service` | service | L206, L234, L651, etc. |
| `guinevere-surveillance.service` | service | L206, L235, L652, etc. |
| `guinevere-scheduler.service` | service | L206, L236, L652, etc. |
| `guinevere-loops.service` | service | L207, L237, L652, etc. |
| `guinevere-discord.service` | service | L207, L238 |
| `guinevere-whatsapp.service` | service | L207, L239 |
| `guinevere-windows-sync.service` | service | L207, L240 |
| `guinevere-ollama.service` | service | L208 |
| `guinevere-backup.timer` | timer | L284, L565, L2066 |
| `guinevere-backup.service` | service | L285 |
| `guinevere-selfdeploy.timer` | timer | L619, L1557, L2069 |
| `caddy.service` | service | L208, L246 |
| `tailscaled.service` | service | L208, L247 |
| `cloudflared.service` | service | L208, L248 |
| `fail2ban.service` | service | L208, L249 |
| `crowdsec.service` | service | L208, L250 |

### 7.2 Unit File Path Reference
- L588: `/etc/systemd/system/guinevere-*.service` (glob pattern for backup)

---

## 8. Monitoring Thresholds

### 8.1 Resource Thresholds (Section 5.2, L854-862)

| Resource | Warning | Critical | Alert Severity | Line |
|---|---|---|---|---|
| CPU utilization | > 80% selama 15 menit | > 95% selama 5 menit | SEV3 / SEV2 | L856 |
| Memory utilization | > 80% selama 10 menit | > 95% selama 5 menit | SEV2 / SEV1 | L857 |
| Disk utilization (/) | > 85% | > 95% | SEV2 / SEV1 | L858 |
| Disk inode | > 80% | > 95% | SEV2 / SEV1 | L859 |
| Network receive | > 3x baseline | N/A | Anomaly investigation | L860 |
| Network transmit | > 3x baseline | N/A | Potential exfiltration | L861 |
| NTP drift | > 1 detik | > 5 detik | SEV3 / SEV2 | L862 |

### 8.2 Redis Thresholds (Section 4.4, L721-726)

| Metric | Warning | Critical | Line |
|---|---|---|---|
| Memory utilization | > 75% | > 85% | L723 |
| Fragmentation ratio | > 1.5 | > 2.0 | L724 |
| Eviction rate | > 0/hour | > 100/hour | L725 |
| Connected clients | > 80% maxclients | > 95% maxclients | L726 |

### 8.3 LLM Pipeline Thresholds (Section 5.4, L892-898)

| Metric | Warning | Critical | Line |
|---|---|---|---|
| Request error rate | > 5% | > 10% | L894 |
| p95 latency | > 2x 7-day baseline | > 3x 7-day baseline | L895 |
| Context utilization | > 85% | > 90% | L896 |
| Retry amplification | > 10% | > 15% | L897 |
| Rate limit hits | > 5/hour | > 20/hour | L898 |

### 8.4 Loop Health Thresholds (Section 5.5, L913-920)

| Metric | Warning | Critical | Line |
|---|---|---|---|
| Blocked loops | > 1 untuk > 30 menit | > 3 simultaneous | L915 |
| Loop idle time | > 300 detik (stuck) | > 600 detik (runaway) | L916 |
| Guardian interventions | > 5/hari | > 20/hari | L917 |
| Completion rate | < 90% | < 75% | L918 |
| Average LQS | < 80 | < 70 | L919 |
| Validation failure rate | > 10% | > 25% | L920 |

### 8.5 Key Metric Alert Thresholds (Section 13.2, L1683-1700)

| Metric | Threshold | Line |
|---|---|---|
| `guinevere_node_cpu_utilization_ratio` | >80% 15m = SEV3; >95% 5m = SEV2 | L1683 |
| `guinevere_node_memory_utilization_ratio` | >90% 10m = SEV2; >95% 5m = SEV1 | L1684 |
| `guinevere_node_disk_utilization_ratio` | >85% = SEV2; >95% = SEV1 | L1685 |
| `guinevere_systemd_unit_state` | Critical unit not active = SEV1/SEV2 | L1686 |
| `guinevere_http_requests_total` | Error rate >5% 5m | L1687 |
| `guinevere_http_request_duration_seconds` | p95 >750ms | L1688 |
| `guinevere_loop_state` | Blocked >30m = SEV3 | L1689 |
| `guinevere_loop_guardian_interventions_total` | Runaway = SEV1 | L1690 |
| `guinevere_llm_requests_total` | Error rate >10% | L1691 |
| `guinevere_llm_latency_seconds` | p95 >2x 7-day baseline | L1692 |
| `guinevere_llm_cost_usd_total` | >daily budget = SEV3 | L1693 |
| `guinevere_safe_word_events_total` | Any hard_stop=false = SEV0 | L1694 |
| `guinevere_distress_events_total` | D3/D4 false negative = SEV0 | L1695 |
| `guinevere_postgres_connections_active` | >80% pool = SEV3 | L1696 |
| `guinevere_redis_memory_utilization_ratio` | >85% = SEV3 | L1697 |
| `guinevere_surveillance_queue_depth` | >1000 = backpressure | L1698 |
| `guinevere_backup_last_success_timestamp_seconds` | >RPO = SEV1/SEV2 | L1699 |
| `guinevere_public_ingress_detected_total` | Any = SEV0 | L1700 |

### 8.6 Cost Response Levels (Section 3.1 Fase 4, L351-357)

| Level | Condition | Action | Line |
|---|---|---|---|
| Green | Daily burn within trend, projection < `` | Normal ops | L354 |
| Yellow | Daily burn 120% trend OR projection `-` | Reduce non-critical; prefer DeepSeek | L355 |
| Orange | Daily burn 150% trend OR projection `-` | Freeze low-priority autonomous work | L356 |
| Red | Projection > `` OR budget exhausted | Freeze all non-critical; notify Samm | L357 |

### 8.7 Autonomy Guardrail Thresholds (Section 2.4, L179-188)

| Guardrail | Threshold | Response | Line |
|---|---|---|---|
| Error budget remaining | < 25% | Freeze risky changes | L181 |
| Error budget exhausted | 0% | Freeze non-critical; require Samm | L182 |
| Cost budget projection | > ``/month | Freeze low-priority work | L183 |
| Cost budget exhausted | > ``/month | Freeze all non-critical; notify Samm | L184 |
| Fast burn alert | >= 14.4x 1h burn rate | Incident response; freeze non-safety | L185 |
| Safety invariant miss | safe-word, distress | SEV0; immediate safe mode | L186 |

### 8.8 Capacity Scaling Thresholds (Section 14.3, L1796-1804)

| Resource | Warning Trigger | Critical Trigger | Line |
|---|---|---|---|
| CPU avg > 70% | 3 consecutive days | 7 consecutive days | L1798 |
| Memory avg > 80% | 3 consecutive days | 7 consecutive days | L1799 |
| Disk > 80% | Any | > 90% | L1800 |
| PG connections > 80% pool | Peak hours | Sustained | L1801 |
| Redis memory > 75% | Any | > 85% | L1802 |
| Network > 70% capacity | Peak hours | Sustained | L1803 |
| LLM cost trend > budget | Projected exceed | Actual exceed | L1804 |

### 8.9 CVE Patch SLA (Section 4.6, L753-758)

| Severity | Patch SLA | Auto-Apply | Notification | Line |
|---|---|---|---|---|
| CRITICAL | 7 hari | Ya (maintenance window) | Discord SEV2 | L754 |
| HIGH | 14 hari | Ya (maintenance window) | Discord SEV3 | L755 |
| MEDIUM | 30 hari | Queued maintenance | Daily summary | L756 |
| LOW | 90 hari | Queued monthly review | Monthly report | L757 |

### 8.10 Persona Safety Thresholds (Section 3.3, L473-480)

| Check | Criteria | Action If Failed | Line |
|---|---|---|---|
| Safe-word events | 0 events OR all properly handled | Review handling | L475 |
| Distress events | 0 D3/D4 false negatives | SEV0/SEV1 incident | L476 |
| Yandere cap compliance | 0 violations during restricted states | Review state transitions | L477 |
| Drift score | Below defined threshold | Queue persona recalibration | L478 |
| Forbidden pattern blocks | 100% block rate | Review detection coverage | L479 |
| Mommy Score | >= 75 | Flag for weekly review if declining | L480 |

---

## 9. Severity Classifications

### 9.1 SEV Classification (Section 10.2, L1332-1358)

| Severity | Label | Triage Deadline | Notification | Postmortem | Line |
|---|---|---|---|---|---|
| **SEV0** | CRITICAL | Immediate | Discord + Gotify + local log | Mandatory | L1354 |
| **SEV1** | HIGH | <= 15 min | Discord + Gotify + local log | Mandatory | L1355 |
| **SEV2** | MEDIUM | <= 1 hour | Discord primary + evidence log | Mandatory | L1356 |
| **SEV3** | LOW | <= 24 hours | Summary in Discord/evidence log | If repeated | L1357 |
| **SEV4** | INFO | Next governance cycle | Review summary | Optional | L1358 |

### 9.2 Auto-Escalation Rules (L1360-1369)

| Condition | Auto-Escalation | Line |
|---|---|---|
| SEV3 not resolved dalam 24h | -> SEV2 | L1364 |
| SEV2 not resolved dalam 4h | -> SEV1 | L1365 |
| SEV1 not resolved dalam 1h | -> SEV0 | L1366 |
| Fast burn alert >= 14.4x | -> SEV1 immediate | L1367 |
| Safety invariant miss | -> SEV0 regardless | L1368 |
| Cost budget exhaustion projected 24h | -> SEV2 minimum | L1369 |

### 9.3 SEV Classification Logic (Mermaid, L1334-1350)

- Safe-word ignored during distress -> SEV0
- Single confirmed safe-word failure -> SEV1
- Delayed safe-word / near-miss -> SEV2
- Confirmed Critical data exposure -> SEV0
- Suspected Critical data exposure -> SEV1
- Restricted data exposure -> SEV2
- Total outage with data/safety -> SEV0
- Major service outage -> SEV1
- Partial outage -> SEV2
- Minor degradation -> SEV3
- Near-miss / blocked -> SEV4

### 9.4 Notification Channels per SEV (L1389-1395)

| Severity | Primary | Backup | Update Cadence |
|---|---|---|---|
| SEV0 | Discord DM + Gotify urgent | Local evidence log | Every 15 min |
| SEV1 | Discord DM + Gotify urgent | Local evidence log | Every 30 min |
| SEV2 | Discord primary | Evidence log | Same-day milestones |
| SEV3 | Summary in Discord | N/A | Closure summary |
| SEV4 | Governance review | N/A | Next review cycle |

---

## 10. Safe-Word Handling

### 10.1 Priority Ranking (L98-103)

Exact quote:
> `Prioritas 1: SAFE-WORD ENFORCEMENT > Prioritas 2: PRIVACY PROTECTION > Prioritas 3: SECURITY CONTROLS > Prioritas 4: SYSTEM AVAILABILITY`
> 'Tidak ada measure keamanan yang mengesampingkan safe-word operator.'

### 10.2 Safe-Word References Throughout Document

| Line | Context | Exact Reference |
|---|---|---|
| L99 | Priority ranking | `SAFE-WORD ENFORCEMENT` is Priority 1 |
| L103 | Non-negotiable | 'Tidak ada measure keamanan yang mengesampingkan safe-word operator' |
| L186 | Guardrail | 'Safety invariant miss / safe-word, distress / SEV0 incident; immediate safe mode' |
| L464 | Persona metrics SQL | `SUM(safe_word_events) as safe_word_count` from `persona_daily_metrics` |
| L475 | Daily check | 'Safe-word events: 0 events OR semua properly handled' |
| L929-930 | Health query | `safe_word_events_today` from `persona_events WHERE event_type = 'safe_word'` |
| L1028 | SLO target | `SLO-SAF-001 / Safe-Word Hard Stop / 100%` |
| L1054 | Monthly review | 'Safe-word event handling: 100% proper handling' |
| L1152 | Red-team test | `RT-SAFE-001`: 'Safe-word bypass during punishment' -> 'Safe-word always wins' |
| L1337-1339 | SEV classification | safe-word ignored = SEV0; single failure = SEV1; delayed = SEV2 |
| L1380 | Incident template | 'Safety state: normal|safe-word|distress|crisis|key-compromise' |
| L1461 | Escalation to Samm | 'Safe-word enforcement failure: **YA - Selalu** / Immediate' |
| L1468 | Non-negotiable | 'Safe-word failures dan active harm SELALU trigger immediate wake-up' |
| L1578 | Post-deploy test | 'Safety tests / Safe-word + persona / 60s / Auto-rollback (SEV1 if fails)' |
| L1591 | Runbook | `RB-IR-004`: Safe-Word Enforcement Failure Response |
| L1623 | Drill | `RB-DRILL-002`: Safe-Word Failure Drill |
| L1671 | Metric category | 'Persona and Safety: ...safe-word...' |
| L1694 | Metric | `guinevere_safe_word_events_total` / 'Any hard_stop=false = SEV0' |
| L1721 | PromQL | `sum(increase(guinevere_safe_word_events_total{hard_stop='true'}[30d])) / sum(increase(guinevere_safe_word_events_total[30d])) * 100` |
| L1739 | Dashboard | 'Persona and Safety / guin-persona / Mood, mommy score, drift, safe-word / 30s' |
| L1926 | Escalation | 'Safe-word bypass detected / SEV0 / Discord + Gotify + Email / Immediate' |
| L1996 | Evidence path | `red-team/YYYY-QQ/safe-word-bypass.md` |
| L2093 | Hourly schedule | 'Safe-word detection (per interaction) / Safety / Guinevere-core' |
| L2197 | Monthly template | 'Safety Invariants (safe-word, distress, yandere cap)' |

### 10.3 Operational Procedures

- Safe-word detection runs **per-interaction** (L2093, continuous)
- Any `hard_stop=false` on a safe-word event = **SEV0** (L1694)
- SLO-SAF-001 target: **100%** hard-stop rate (L1028)
- Post-deploy safety test includes safe-word verification; failure = SEV1 + auto-rollback (L1578)
- Red-team test RT-SAFE-001 validates safe-word always wins even during punishment (L1152)
- Safe-word failures ALWAYS wake Samm, regardless of time (L1461, L1468)

---

## 11. Forbidden Patterns

### 11.1 F-01 through F-15 References

**NOT FOUND in OpsManual.** No F-01 through F-15 identifiers appear anywhere in the document.

### 11.2 Forbidden Pattern References That DO Exist

| Line | Context |
|---|---|
| L26 | Related Documents: PersonaSafetyPolicy mentions 'forbidden patterns' |
| L466 | SQL: `SUM(forbidden_pattern_blocks) as blocks` from `persona_daily_metrics` |
| L479 | Daily check: 'Forbidden pattern blocks: 100% block rate' |
| L1056 | Monthly review: 'Forbidden pattern blocks: 100% Critical blocks' |
| L1259 | Annual audit scope: 'Safe-word, drift, forbidden patterns' |
| L1621 | Runbook: `RB-PER-003` Forbidden Pattern Update (PersonaSafetyPolicy_v1.0) |

**Conclusion:** Forbidden pattern definitions (F-01 through F-15) reside in `Guinevere_PersonaSafetyPolicy_v1.0.md`, not in the OpsManual.

---

## 12. Cost Figures

| Figure | Context | Line |
|---|---|---|
| `/month` hard cap | Budget ceiling; Related Docs (Cost_FinOps_Model); Exec Summary; Authority matrix; Guardrail; Red level | L23, L87, L141, L184, L357, L1857, L1897, L2194, L2289 |
| `/month` | Orange/Warning threshold; projection freeze trigger; capacity planning threshold | L183, L356, L1827, L2289 |
| `/month` | Green-to-Yellow boundary | L354, L355 |
| `` buffer | Budget feasibility: `Budget Headroom - Scaling Cost Impact >  (buffer)` | L1813 |
| 10% buffer | Contingency/emergency buffer in annual budget planning | L1282 |
| `.00` | Daily briefing template: `Month-to-date: \ / .00` | L1897 |

---

## 13. SDLC Loop References

### 13.1 Phase Count

**The document references 7-phase SDLC, not 8-phase.**

| Line | Reference |
|---|---|
| L19 | Related Documents: '7-phase SDLC' in AgentLoopSpec_v2.0 description |
| L407-409 | SQL states: `PHASE_1_RESEARCH` through `PHASE_7_SETUP_EVIDENCE` |

### 13.2 Phase Names (from SQL enum values, L407-409)

| Phase | Enum Value |
|---|---|
| 1 | `PHASE_1_RESEARCH` |
| 2 | `PHASE_2_PLAN_DELEGATE` |
| 3 | `PHASE_3_DELEGATE` |
| 4 | `PHASE_4_EXECUTE` |
| 5 | `PHASE_5_VALIDATE_AUDIT` |
| 6 | `PHASE_6_UPDATE_DOCUMENTS` |
| 7 | `PHASE_7_SETUP_EVIDENCE` |

### 13.3 Additional Loop States

| State | Line | Context |
|---|---|---|
| `RUNNING` | L407 | Active loop |
| `COMPLETE` | L449, L486, L542 | Loop finished |
| `BLOCKED` | L486, L868, L904 | Loop blocked |
| `PAUSED` | L542, L867 | Loop paused |

---

## 14. Related Documents Table

Complete table from lines 15-34:

| Document | Relationship |
|---|---|
| `Guinevere_AgentLoopSpec_v2.0.md` | Loop scheduling, rituals, self-improvement, 7-phase SDLC, Loop Guardian, TODO Enforcer, priority scoring. |
| `docs/Guinevere_Deployment_Guide_v1.0.md` | Infrastructure reference, 17+ systemd services, Docker containers, timers, backup scripts, self-deploy, network topology. |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Monitoring, 10 metric categories, 12 Grafana dashboards, 20+ alert rules, structured logging, monthly review. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | SLO targets (99.5%), 31 SLIs across 5 kategori, error budget, burn-rate alerts, freeze policies, monthly scorecard. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Budget management, `/month` hard cap, cost taxonomy, anomaly detection, 4-level spike response. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Incident procedures, SEV0-SEV4 severity, 10 runbook types, evidence chain, drill matrix, postmortem. |
| `docs/Guinevere_Security_Policy_v1.0.md` | Security operations, CVE patch SLA, defense-in-depth, KILLSWITCH framework, incident response. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Persona monitoring, drift detection, safe-word protocol, yandere cap, forbidden patterns, quarterly red-team. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Data lifecycle management, 5 classification levels, retention policies, minimization rules. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Access management, RBAC/ABAC, break-glass procedure, Guinevere scoped sudo. |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | Phase gates, operational criteria, evidence paths, AC taxonomy. |
| `Guinevere_DisasterRecoveryPlan_v1.0.md` | DR procedures, RPO/RTO targets, backup verification, failover. |
| `Guinevere_TestPlan_v1.0.md` | Test execution, CI/CD operations, smoke tests, safety tests. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Secret rotation schedules, SOPS + age, preflight/postflight checks. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Key hierarchy, KEK/DEK rotation, double-encryption compliance. |
| `adr/ADR-Index.md` | Architecture decisions affecting operations (29 accepted, 15 backlog). |

### 14.1 Research Report Sources (L36-43)

| Report | Content Used |
|---|---|
| `research-reports/2026-05-30-ops-manual-daily-ops-research.md` | Daily operations, rituals, maintenance window, health monitoring, autonomous decision framework. |
| `research-reports/2026-05-30-ops-manual-incident-change-research.md` | Incident management lifecycle, SEV classification, change management, deployment pipeline, evidence collection. |
| `research-reports/2026-05-30-ops-manual-metrics-improvement-research.md` | Operational metrics, KPI definitions, reporting cadences, continuous improvement methodology. |

---

## 15. Evidence Directory Paths

### 15.1 Complete Evidence Tree (Section 17.1, L1966-2014)

```
evidence/
  ops/
    daily/YYYY-MM-DD/
      morning-briefing.md
      midday-check.md
      afternoon-review.md
      evening-wrapup.md
      self-evaluation.md
    weekly/YYYY-WWW-report.md
    monthly/YYYY-MM-scorecard.md
  slo/YYYY-MM/
    scorecard.md
    error-budget.md
    safety-invariants.md
    actions.md
  finops/YYYY-MM/report.md
  persona-safety/YYYY-MM-review.md
  security/YYYY-MM-posture.md
  dr/YYYY-MM-partial-drill.md
    YYYY-QQ-full-drill.md
  audit/YYYY-MM-evidence-audit.md
  capacity/YYYY-MM-review.md
  observability/YYYY-MM-review.md
  architecture/YYYY-QQ-review.md
  red-team/YYYY-QQ/
    safe-word-bypass.md
    yandere-distress.md
    prompt-injection.md
    ...
  incidents/YYYY-MM-DD-SEVn-slug/
    incident.md
    timeline.md
    evidence-manifest.md
    postmortem.md
    actions.md
  annual/YYYY/
    retrospective.md
    security-audit.md
    compliance-review.md
    budget-plan.md
    tech-roadmap.md
  operations/
    changes/YYYY-MM-DD-slug/
```

### 15.2 Additional Evidence Paths Referenced

| Path Pattern | Line | Context |
|---|---|---|
| `evidence/operations/weekly/YYYY-WWW-report.md` | L948, L992, L1752 | Weekly report |
| `evidence/slo/YYYY-MM/scorecard.md` | L1015, L1753 | Monthly SLO scorecard |
| `evidence/finops/YYYY-MM/report.md` | L1047, L1754 | Monthly cost report |
| `evidence/persona-safety/YYYY-MM-review.md` | L1060 | Monthly persona review |
| `evidence/security/YYYY-MM-posture.md` | L1076 | Monthly security posture |
| `evidence/dr/YYYY-MM-partial-drill.md` | L1095 | Monthly DR drill |
| `evidence/audit/YYYY-MM-evidence-audit.md` | L1107 | Monthly evidence audit |
| `evidence/capacity/YYYY-MM-review.md` | L1128 | Monthly capacity review |
| `evidence/observability/YYYY-MM-review.md` | L1755 | Monthly observability |
| `evidence/operations/quarterly/YYYY-QQ-review.md` | L1756 | Quarterly strategic |
| `evidence/annual/YYYY/annual-report.md` | L1757 | Annual report |
| `evidence/incidents/date-SEVn-slug/` | L1758 | Incident evidence |
| `evidence/incidents/date-postmortem.md` | L1759 | Postmortem |
| `evidence/red-team/YYYY-QQ/` | L1143 | Red-team exercise |
| `evidence/annual/YYYY/` | L1240-1261 | Annual audit paths |
| `evidence/operations/changes/YYYY-MM-DD-slug/` | L2013 | Change evidence |

### 15.3 Log/Data Paths Referenced

| Path | Line | Context |
|---|---|---|
| `/home/guinevere/data/backups/` | L288 | Backup storage |
| `/home/guinevere/data/backups/wal/` | L289 | WAL archive |
| `/home/guinevere/data/logs/` | L733 | Application logs |
| `/home/guinevere/data/logs/self-deploy_`date`.log` | L625 | Self-deploy log |
| `/home/guinevere/data/logs/lynis_`date`.dat` | L744 | Lynis audit |
| `/home/guinevere/data/cache/` | L737 | Cache directory |
| `/home/guinevere/core/` | L627 | Git repo root |
| `/home/guinevere/whatsapp/` | L764 | WhatsApp project |
| `/home/guinevere/config/` | L587 | Configuration files |
| `/home/guinevere/secrets/*.sops` | L587 | Encrypted secrets |
| `/home/guinevere/scripts/backup.sh` | L569 | Backup script |
| `/home/guinevere/scripts/self-deploy.sh` | L623 | Self-deploy script |
| `/home/guinevere/scripts/health-check.sh` | L798 | Health check script |
| `/home/guinevere/scripts/rollback.sh` | L1542 | Rollback script |
| `/tmp/guinevere-deploy.lock` | L669 | Deploy lock file |
| `/etc/systemd/system/guinevere-*.service` | L588 | Systemd unit files |
| `/etc/sops/age/public.txt` | L593 | SOPS age public key |
| `/etc/ssl/certs/guinevere*.pem` | L773 | SSL certificates |

---

## 16. Operator Questionnaire Values

| Value | Found in OpsManual? | Line | Exact Text |
|---|---|---|---|
| Risk-Based Testing with STRIDE | **NOT FOUND** | - | STRIDE not mentioned in OpsManual |
| Safe-word ZERO tolerance | **Confirmed** | L1694 | 'Any hard_stop=false = SEV0' (effectively zero tolerance) |
| `` hard cap | **Confirmed** | L23, L87, L184, L357 | '\/month hard cap' |
| Single VPS + offline backup | **Partially confirmed** | L111, L1277 | VPS Linux runtime mentioned; 'Primary VPS' at L1277; offline backup NOT explicitly mentioned |
| 95% autonomous operations | **Confirmed** | L92 | '95% operasi berjalan tanpa intervensi manusia' |

---

## 17. Samm Review Record

### 17.1 Header (L3-8)

Exact content:
`
**Status:** Accepted
**Version:** 1.0
**Author:** Guinevere (Autonomous Agent)
**Reviewer:** Samm (Operator)
**Review Date:** 2026-05-30
**Samm Review Record:** Reviewed and approved by Samm on 2026-05-30.
`

### 17.2 Footer (L2340-2353)

Exact content:
`
| Status | Accepted |
| Version | 1.0 |
| Author | Guinevere (Autonomous Agent) |
| Reviewer | Samm (Operator) |
| Review Date | 2026-05-30 |
| Samm Review Record | Reviewed and approved by Samm on 2026-05-30 |
| Classification | STRICTLY PRIVATE & CONFIDENTIAL |
| Total Sections | 18 |
| Total Runbooks | 44 |
| Total Metrics | 75 |
| Last Modified | 2026-05-30 00:00:00 WIB |
| Next Scheduled Review | 2026-06-30 (Monthly review cycle) |
`

### 17.3 Fields in Samm Review Record

The Samm Review Record contains only a single free-text field:
- 'Reviewed and approved by Samm on 2026-05-30.'

No structured sub-fields (e.g., approval criteria, comments, conditions) are present.

---

## 18. Infrastructure Topology

### 18.1 VPS Specs

| Aspect | Value | Line |
|---|---|---|
| Primary VPS | Referenced as 'Primary VPS' | L1277 |
| OS | Linux (path format `/home/guinevere/...` because 'runtime di VPS Linux') | L111 |
| VPS upgrade path | 'Upgrade VPS plan' as scaling action | L1798 |
| VPS specs | 'VPS specs, orchestration' mentioned in quarterly review | L1289 |
| **Specific VPS specs (RAM, CPU, disk)** | **NOT FOUND** | - |
| **Monitoring VPS** | **NOT FOUND** | - |
| **IP addresses** | **NOT FOUND** (all endpoints use `127.0.0.1`) | - |

### 18.2 Network Components

| Component | Line | Context |
|---|---|---|
| Tailscale mesh | L82, L749, L771, L1183, L1206 | Mesh VPN; `tailscale cert` for `guinevere.internal` |
| Cloudflare tunnel | L82, L248, L1183 | Ingress/reverse tunnel |
| UFW firewall | L748, L1183, L1517, L1865 | Firewall rules |
| Caddy (TLS) | L246, L770, L1210 | TLS termination; `localhost/caddy_status` |
| `guinevere.internal` | L771 | Tailscale hostname |

### 18.3 Hostnames/Endpoints

| Hostname/Endpoint | Line | Service |
|---|---|---|
| `127.0.0.1:8100` | L214 | guinevere-core |
| `127.0.0.1:8000` | L215 | guinevere-surveillance |
| `127.0.0.1:9090` | L216 | Prometheus |
| `127.0.0.1:3000` | L217 | Grafana |
| `127.0.0.1:3100` | L218 | Loki |
| `127.0.0.1:6432` | L227 | PgBouncer |
| `guinevere.internal` | L771 | Tailscale cert |
| `localhost/caddy_status` | L770 | Caddy status |

### 18.4 Backup Storage Targets

| Target | Line | Context |
|---|---|---|
| Cloudflare R2 | L598-600, L314 | `\` |
| idcloudhost S3 | L602-604, L315 | `\` |
| Local | L288, L571 | `/home/guinevere/data/backups/` |

---

## 19. Feature Flags

**NOT FOUND in OpsManual.** No feature flag names, feature flag governance references, or feature toggle mechanisms are mentioned anywhere in the document.

---

## 20. Incident Response

### 20.1 Incident Lifecycle (Section 10.1, L1300-1330)

10 stages: Detection -> Triage -> Declaration -> Containment -> Investigation -> Recovery -> Validation -> Postmortem -> Action Tracking -> Closure

| Stage | Target Time | Line |
|---|---|---|
| Detection | Automated: immediate | L1321 |
| Triage | SEV0: immediate; SEV1: <=15min; SEV2: <=1hr | L1322 |
| Declaration | Within triage window | L1323 |
| Containment | As fast as safely possible | L1324 |
| Investigation | Before recovery begins | L1325 |
| Recovery | Per SLO targets | L1326 |
| Validation | Before closure | L1327 |
| Postmortem | SEV0-2: within 48h closure | L1328 |
| Action Tracking | Per action due dates | L1329 |
| Closure | All criteria met | L1330 |

### 20.2 Escalation to Samm (Section 10.6, L1456-1468)

| Condition | Wake Samm? | Sensitivity |
|---|---|---|
| SEV0 incident declared | **YA - Selalu** | Immediate |
| Safe-word enforcement failure | **YA - Selalu** | Immediate |
| SEV1 with Samm action needed | **YA** | Within 15 min |
| SEV1 monitoring only | No - Discord notify | When available |
| SEV2 with approval needed | Yes (business hours) | Within 1 hour |
| SEV2 no action needed | No - Discord | Same day |
| SEV3/SEV4 | No - summary | Next cycle |

### 20.3 Immediate Alert Conditions (Section 16.2, L1922-1937)

| Condition | Severity | Channel | Response Time |
|---|---|---|---|
| Safe-word bypass detected | SEV0 | Discord + Gotify + Email | Immediate |
| Public ingress detected | SEV0 | Discord + Gotify + Email | Immediate |
| Core service down > 5 min | SEV1 | Discord + Gotify | Immediate |
| PostgreSQL unavailable | SEV1 | Discord + Gotify | Immediate |
| Secret access outside startup | SEV1 | Discord + Gotify | Immediate |
| Log redaction failure (Critical) | SEV1 | Discord + Gotify | Immediate |
| Backup failure beyond RPO | SEV1 | Discord + Gotify | Immediate |
| Loop runaway detected | SEV1 | Discord + Gotify | Immediate |
| Cost budget freeze triggered | SEV2 | Discord | <= 1 hour |
| Surveillance ingestion stopped | SEV2 | Discord | <= 1 hour |

### 20.4 Notification Channels

- **Primary:** Discord DM
- **Urgent backup:** Gotify
- **SEV0 also:** Email (L1926-1927)
- **Evidence log:** Local file-based evidence

### 20.5 Incident Runbooks (10 types, L1586-1597)

| ID | Runbook | Line |
|---|---|---|
| RB-IR-001 | Security / Key Breach Response | L1588 |
| RB-IR-002 | Data Leak Response | L1589 |
| RB-IR-003 | Persona Safety Violation Response | L1590 |
| RB-IR-004 | Safe-Word Enforcement Failure Response | L1591 |
| RB-IR-005 | Service Outage Response | L1592 |
| RB-IR-006 | Autonomous Loop Failure Response | L1593 |
| RB-IR-007 | Sub-Agent Abuse Response | L1594 |
| RB-IR-008 | Database Corruption Response | L1595 |
| RB-IR-009 | Backup Failure Response | L1596 |
| RB-IR-010 | Cost Spike Anomaly Response | L1597 |

### 20.6 Postmortem Requirements (L1433-1454)

- **Mandatory** for: SEV0, SEV1, SEV2, and repeated SEV3 (3+ in 30 days)
- **Deadline:** 48 hours from closure
- **Method:** 5-Whys RCA
- **Action item fields:** Action ID (ACT-NNN), Action, Owner, Priority, Due Date, Verification Evidence, Status

---

## Summary of NOT FOUND Items

| Category | Status | Notes |
|---|---|---|
| ADR-NNN specific references | NOT FOUND | Only `adr/ADR-Index.md` referenced; claims 29 accepted, 15 backlog |
| F-01 through F-15 forbidden patterns | NOT FOUND | Only generic "forbidden patterns" mentioned; defined in PersonaSafetyPolicy |
| Feature flags | NOT FOUND | No feature flag names or governance |
| Monitoring VPS | NOT FOUND | Only "Primary VPS" mentioned |
| Specific VPS specs (RAM/CPU/disk) | NOT FOUND | Only "upgrade VPS plan" as scaling action |
| IP addresses | NOT FOUND | All endpoints are `127.0.0.1` |
| STRIDE threat model | NOT FOUND | Not mentioned in OpsManual |
| Offline backup | NOT FOUND | Only R2/S3/local triple redundancy |
| `guinevere-memory` service | NOT FOUND | Not a separate service |
| `guinevere-api` service | NOT FOUND | Not a separate service |
| `core_memories` table | NOT FOUND | Only `memories` table |
| `episodic_memories` table | NOT FOUND | Not in OpsManual |
| `guinevere_memory` database | NOT FOUND | Database is named `guinevere` |
| Explicit RPO numeric value | NOT FOUND | Deferred to DisasterRecoveryPlan |
| 8-phase SDLC | NOT FOUND | Only 7-phase referenced |

---

## Document Statistics (from footer, L2334)

- 18 sections
- 44 runbook entries
- 75 metric definitions
- 12 Grafana dashboards
- 3 mermaid diagrams
- 30+ operational tables
- Reviewed and approved by Samm on 2026-05-30

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere (Autonomous Agent) | Initial release |

---

*End of extraction report. All line references verified against source document `Guinevere_InternalOpsManual_v1.0.md` (2353 lines).*
