# Guinevere Internal Ops Manual — Daily & Autonomous Operations Research Report

**Document Type:** Research Report for Guinevere Internal Ops Manual  
**Version:** 1.0  
**Date:** 2026-05-30  
**Author:** Guinevere / Hephaestus  
**Status:** Research Complete  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines daily ritual schedule, loop types, priority scoring, Loop Guardian, TODO Enforcer, and proactive behavior. |
| `docs/Guinevere_Deployment_Guide_v1.0.md` | Defines 17+ systemd services, Docker containers, timers, backup scripts, self-deploy scripts, resource allocation, and network topology. |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Defines 10 metric categories, 12 Grafana dashboards, 20+ alert rules, structured logging, monthly observability review. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines 99.5% SLO, 31 SLIs across 5 categories, error budgets, burn-rate alerts, freeze policies, monthly scorecard. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines $30/month hard cap, budget breakdown, 4-level cost spike response, monthly cost report. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines persona review cadence (per-interaction, daily, monthly, quarterly), drift governance, safe-word protocol. |
| `docs/Guinevere_Security_Policy_v1.0.md` | Defines CVE patch SLA, defense-in-depth layers, KILLSWITCH framework, incident response. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines SEV0-SEV4 severity, response timing, evidence paths, drill matrix. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Defines rotation schedules and procedures for secrets managed by SOPS + age. |

---

## 1. Operations Philosophy

### 1.1 Autonomous-First Principle

Guinevere operates as a fully autonomous system steward. The operations philosophy is built on a single foundational principle: **Guinevere manages herself; Samm receives a daily summary.**

| Principle | Implementation |
|---|---|
| Autonomous-first | Guinevere executes all daily rituals, maintenance, monitoring, and incident response without requiring Samm intervention. |
| Minimal human intervention | Samm's only routine touchpoint is the daily summary delivered via Discord. |
| Safety-guardrail autonomy | Autonomous decisions operate within safety, cost, and reliability guardrails. Crossing a guardrail triggers freeze or escalation. |
| Evidence-based operations | Every material action produces an evidence artifact or metric. Nothing happens silently. |
| Persona-aware ops | During operational procedures, Guinevere uses neutral incident-command tone for alerts and summaries. Persona flavor appears only in casual interaction, never in ops procedures. |

### 1.2 Decision Authority Model

| Decision Type | Authority | Escalation Required |
|---|---|---|
| Service restart (non-destructive) | Guinevere autonomous | No |
| Dependency update (security patch) | Guinevere autonomous within CVE SLA | No |
| Backup verification and rotation | Guinevere autonomous | No |
| Log rotation and cleanup | Guinevere autonomous | No |
| Cost freeze (non-critical work) | Guinevere autonomous | No |
| Sub-agent spawning and management | Guinevere autonomous | No |
| Database VACUUM / maintenance | Guinevere autonomous | No |
| Self-deploy of approved changes | Guinevere autonomous at 03:00 WIB | No |
| Budget override above $30/month | Samm approval | Yes |
| Destructive database operations | Samm approval | Yes |
| Production architecture change | Samm approval | Yes |
| Security incident SEV0/SEV1 | Guinevere contains + notifies Samm | Notify, not approval |
| Safe-word or distress event | Guinevere enters safe mode + notifies | Notify, not approval |

### 1.3 Operational Rhythm

Guinevere's day follows a structured rhythm of five daily rituals plus continuous background monitoring. The rhythm ensures that nothing goes unchecked for more than a few hours while keeping Samm involvement to a single daily message.

---

## 2. Daily Operations Schedule — Hour-by-Hour (WIB / UTC+7)

| Time (WIB) | Activity | Type | Service | Automation Level |
|---|---|---|---|---|
| 00:00 | Self-Evaluation ritual | DailyRitual | guinevere-scheduler | Fully autonomous |
| 00:05–00:30 | Memory consolidation + journal entry | SelfImprovement | guinevere-core | Fully autonomous |
| 00:30–01:00 | Persona drift check + daily safety review | SafetyReview | guinevere-core | Fully autonomous |
| 01:00–02:00 | Quiet period — background monitoring only | Monitoring | Loop Guardian | Fully autonomous |
| 02:00 | Daily backup execution (timer) | Backup | guinevere-backup.timer | Fully autonomous |
| 02:05–02:30 | Backup verification + offsite upload | Backup | guinevere-core | Fully autonomous |
| 02:30–03:00 | Log rotation + compression | Maintenance | guinevere-core | Fully autonomous |
| 03:00 | Self-deploy check (timer) | Deployment | guinevere-selfdeploy.timer | Fully autonomous |
| 03:05–03:30 | Database maintenance (VACUUM ANALYZE) | Maintenance | guinevere-core | Fully autonomous |
| 03:30–04:00 | Redis optimization + memory defrag | Maintenance | guinevere-core | Fully autonomous |
| 04:00–04:30 | Security scan + dependency check | Security | guinevere-core | Fully autonomous |
| 04:30–05:00 | Certificate renewal check + cleanup | Maintenance | guinevere-core | Fully autonomous |
| 05:00–07:00 | Quiet period — background monitoring only | Monitoring | Loop Guardian | Fully autonomous |
| 06:00 | Hourly proactive loop check (if loops < 3) | Proactive | guinevere-scheduler | Fully autonomous |
| 07:00 | **Morning Ritual** | DailyRitual | guinevere-scheduler | Fully autonomous |
| 07:05–07:15 | Morning briefing generation + Discord post | Communication | guinevere-discord | Fully autonomous |
| 07:15–08:00 | Day's work planning + backlog prioritization | Planning | guinevere-core | Fully autonomous |
| 08:00 | Monday only: Weekly planning ritual | WeeklyRitual | guinevere-scheduler | Fully autonomous (Mon) |
| 08:00–12:00 | SDLC loops + proactive work | SDLC | guinevere-loops | Fully autonomous |
| 09:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 10:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 11:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 12:00 | **Midday Check** | DailyRitual | guinevere-scheduler | Fully autonomous |
| 13:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 14:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 15:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 16:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 17:00 | **Afternoon Review** | DailyRitual | guinevere-scheduler | Fully autonomous |
| 18:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 19:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 20:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 21:00 | **Evening Wrap-up** | DailyRitual | guinevere-scheduler | Fully autonomous |
| 22:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| 23:00 | Hourly proactive loop check | Proactive | guinevere-scheduler | Fully autonomous |
| All day | Loop Guardian heartbeat (30s) + progress (5m) | Monitoring | guinevere-loops | Fully autonomous |
| All day | Surveillance ingestion (continuous) | Surveillance | guinevere-surveillance | Fully autonomous |
| All day | Prometheus scrape (15s interval) | Monitoring | prometheus | Fully autonomous |
| All day | Alert evaluation (continuous) | Monitoring | alertmanager | Fully autonomous |
| 1st of month | Monthly review ritual | MonthlyRitual | guinevere-scheduler | Fully autonomous |
| Every quarter | Strategic review | QuarterlyRitual | guinevere-scheduler | Fully autonomous |

### 2.1 Continuous Background Processes

These processes run 24/7 without schedule:

| Process | Service | Check Interval | Action on Anomaly |
|---|---|---|---|
| Loop Guardian heartbeat | guinevere-loops | 30 seconds | Yank idle agent back to TODO |
| Loop Guardian progress | guinevere-loops | 5 minutes | Investigate + redirect if no TODO cleared |
| Loop Guardian resource | guinevere-loops | 60 seconds | Kill + respawn if memory/CPU spike |
| Prometheus scrape | prometheus | 15 seconds | Alert if target down |
| Alertmanager evaluation | alertmanager | Continuous | Route alert per severity |
| Surveillance ingestion | guinevere-surveillance | Real-time | Queue + backpressure on overload |
| Health check probes | guinevere-core | 30 seconds | Alert if composite health fails |
| Cost tracking | guinevere-core | Per LLM call | Freeze if daily budget exceeded |
| Safe-word detection | guinevere-core | Per interaction | Immediate safe-mode transition |
| Drift monitoring | guinevere-core | Per interaction | Log drift score changes |

---

## 3. Morning Ritual (07:00 WIB) — Detailed Procedure

The morning ritual is Guinevere's first active operation of the day. It sets the operational baseline, reviews overnight health, and generates the daily briefing for Samm.

### 3.1 Phase 1 — Health Check All Services (07:00:00–07:01:00)

Guinevere executes a comprehensive health check across all 17+ services:

```bash
# Systemd service health — all Guinevere units
systemctl is-active guinevere-core guinevere-surveillance guinevere-scheduler \
  guinevere-loops guinevere-windows-sync guinevere-discord guinevere-whatsapp \
  guinevere-ollama caddy tailscaled cloudflared fail2ban crowdsec

# Docker container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Individual health probes
curl -sf http://127.0.0.1:8100/health | jq .                    # Core health
curl -sf http://127.0.0.1:8000/health | jq .                    # Surveillance API
curl -sf http://127.0.0.1:9090/-/healthy                        # Prometheus
curl -sf http://127.0.0.1:3000/api/health                       # Grafana
curl -sf http://127.0.0.1:3100/ready                            # Loki

# PostgreSQL health
docker exec postgresql pg_isready -U postgres

# Redis health
docker exec redis redis-cli -a "$REDIS_PASSWORD" ping

# PgBouncer pool status
docker exec postgresql psql -U postgres -h 127.0.0.1 -p 6432 \
  -c "SHOW POOLS;" 2>/dev/null
```

**Expected results:**

| Service | Healthy State | Degraded Action |
|---|---|---|
| guinevere-core | `active (running)` | Auto-restart via systemd; log restart reason |
| guinevere-surveillance | `active (running)` | Auto-restart; check port 8000 binding |
| guinevere-scheduler | `active (running)` | Auto-restart; verify APScheduler state |
| guinevere-loops | `active (running)` | Check for stuck loops; restart if needed |
| guinevere-discord | `active (running)` | Check Discord gateway connection |
| guinevere-whatsapp | `active (running)` | Check Baileys session validity |
| postgresql | `healthy` | Check Docker container, PgBouncer connectivity |
| redis | `healthy` | Check memory usage, eviction state |
| prometheus | `healthy` | Check scrape targets |
| grafana | `healthy` | Check dashboard provisioning |
| loki | `ready` | Check disk space for log storage |
| caddy | `active (running)` | Check TLS certificate validity |
| tailscaled | `active (running)` | Check peer connectivity |
| cloudflared | `active (running)` | Check tunnel status |

### 3.2 Phase 2 — Review Overnight Alerts (07:01:00–07:02:00)

```sql
-- Query overnight alerts from alertmanager history (via PostgreSQL audit log)
SELECT severity, service, component, summary, created_at, resolved_at
FROM alert_history
WHERE created_at >= NOW() - INTERVAL '10 hours'
ORDER BY severity ASC, created_at DESC;

-- Check for unresolved alerts
SELECT severity, service, component, summary, created_at
FROM alert_history
WHERE resolved_at IS NULL AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY severity ASC;

-- Count alerts by severity overnight
SELECT severity, COUNT(*) as alert_count
FROM alert_history
WHERE created_at >= NOW() - INTERVAL '10 hours'
GROUP BY severity;
```

**Alert triage protocol:**
- SEV0/SEV1 overnight: Already handled in real-time via Discord + Gotify. Morning ritual verifies resolution.
- SEV2 overnight: Review and verify containment.
- SEV3 overnight: Add to daily summary digest.
- SEV4 overnight: Queue for next governance review.

### 3.3 Phase 3 — Check Backup Status (07:02:00–07:03:00)

```bash
# Check last backup execution
systemctl status guinevere-backup.timer
systemctl status guinevere-backup.service

# Verify backup files exist and are recent
ls -lah /home/guinevere/data/backups/
ls -lah /home/guinevere/data/backups/wal/

# Verify offsite upload status
# Check Cloudflare R2 upload log
journalctl -u guinevere-backup --since "02:00" --until "03:00" | grep -i "r2\|s3\|upload"

# Verify backup integrity (quick check)
docker exec postgresql pg_isready -U postgres
# Full WAL check
docker exec postgresql psql -U postgres -c \
  "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"
```

```sql
-- Check backup metrics in PostgreSQL
SELECT backup_type, target, last_success_at, duration_seconds, size_bytes, status
FROM backup_log
WHERE last_success_at >= NOW() - INTERVAL '24 hours'
ORDER BY last_success_at DESC;
```

**Backup verification criteria:**

| Backup Type | Expected | Failure Action |
|---|---|---|
| pg_dump (daily) | Completed by 02:30 WIB | SEV2 alert; investigate + manual backup |
| WAL streaming | Continuous, lag < 5 min | Check WAL receiver; restart if stalled |
| Redis RDB snapshot | Completed with backup timer | Check Redis AOF state; snapshot manually |
| R2 upload | Uploaded within 30 min of backup | Retry upload; check R2 credentials |
| idcloudhost S3 upload | Uploaded within 30 min of backup | Retry upload; check S3 endpoint |

### 3.4 Phase 4 — Review Cost Burn Rate (07:03:00–07:04:00)

```sql
-- Daily cost summary
SELECT
  DATE(created_at) as date,
  model,
  purpose,
  SUM(cost_usd) as total_cost,
  SUM(tokens_input) as input_tokens,
  SUM(tokens_output) as output_tokens,
  COUNT(*) as request_count
FROM llm_cost_ledger
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY DATE(created_at), model, purpose
ORDER BY total_cost DESC;

-- Monthly projection
SELECT
  SUM(cost_usd) as month_to_date,
  SUM(cost_usd) / EXTRACT(DAY FROM NOW()) * EXTRACT(DAY FROM (DATE_TRUNC('month', NOW()) + INTERVAL '1 month' - INTERVAL '1 day'))) as projected_monthly,
  30.00 - SUM(cost_usd) as remaining_budget
FROM llm_cost_ledger
WHERE created_at >= DATE_TRUNC('month', NOW());

-- Check for cost anomalies (>150% of daily average)
WITH daily_avg AS (
  SELECT AVG(daily_cost) as avg_cost
  FROM (
    SELECT DATE(created_at) as day, SUM(cost_usd) as daily_cost
    FROM llm_cost_ledger
    WHERE created_at >= NOW() - INTERVAL '7 days'
    GROUP BY DATE(created_at)
  ) sub
)
SELECT 'ANOMALY' as status, SUM(cost_usd) as yesterday_cost, avg_cost
FROM llm_cost_ledger, daily_avg
WHERE created_at >= NOW() - INTERVAL '1 day'
  AND created_at < DATE_TRUNC('day', NOW())
GROUP BY avg_cost
HAVING SUM(cost_usd) > avg_cost * 1.5;
```

**Cost response levels:**

| Level | Condition | Action |
|---|---|---|
| Green | Daily burn within trend, monthly projection < $25 | Normal operations |
| Yellow | Daily burn 120% of trend OR projection $25-$28 | Reduce non-critical LLM calls; prefer DeepSeek |
| Orange | Daily burn 150% of trend OR projection $28-$30 | Freeze low-priority autonomous work |
| Red | Projection > $30 OR budget exhausted | Freeze all non-critical work; notify Samm |

### 3.5 Phase 5 — Plan Day's Work (07:04:00–07:05:00)

```sql
-- Active and pending tasks across all projects
SELECT
  p.name as project,
  t.id as task_id,
  t.title,
  t.priority_score,
  t.status,
  li.current_phase,
  li.state as loop_state
FROM tasks t
JOIN projects p ON t.project_id = p.id
LEFT JOIN loop_instances li ON t.id = li.task_id AND li.state != 'COMPLETE'
WHERE t.status IN ('pending', 'in_progress', 'blocked')
ORDER BY t.priority_score DESC;

-- Priority scoring refresh
-- priority_score = client_revenue * 0.3 + deadline_urgency * 0.4
--                + samm_explicit * 0.2 + guinevere_judgment * 0.1
UPDATE tasks
SET priority_score = (
  COALESCE(client_revenue_weight, 0.5) * 0.3 +
  COALESCE(deadline_urgency, 0.5) * 0.4 +
  COALESCE(samm_explicit_priority, 0.5) * 0.2 +
  COALESCE(guinevere_judgment, 0.5) * 0.1
)
WHERE status IN ('pending', 'in_progress');
```

### 3.6 Phase 6 — Generate Morning Briefing (07:05:00–07:10:00)

The morning briefing is generated and posted to Discord. See **Section 10 — Daily Summary Template** for the complete format.

**Briefing generation procedure:**
1. Aggregate all health check results from Phase 1.
2. Summarize overnight alerts from Phase 2.
3. Include backup status from Phase 3.
4. Include cost status from Phase 4.
5. List today's planned work from Phase 5.
6. Include any surveillance summary (anonymized, non-intimate).
7. Format as Discord embed with color-coded sections.
8. Post to configured Discord channel.

---

## 4. Midday Check (12:00 WIB) — Detailed Procedure

The midday check is a lighter touchpoint to verify morning work progressed and catch any degradation.

### 4.1 Progress Assessment (12:00:00–12:01:00)

```sql
-- Tasks progressed since morning
SELECT
  t.id, t.title, t.status,
  li.current_phase,
  li.completed_todos, li.total_todos,
  li.error_count
FROM tasks t
LEFT JOIN loop_instances li ON t.id = li.task_id AND li.state = 'RUNNING'
WHERE t.status = 'in_progress'
  AND t.updated_at >= CURRENT_DATE + INTERVAL '7 hours';

-- Loops completed since morning
SELECT
  li.task_id, t.title,
  li.completed_at,
  li.total_todos, li.completed_todos,
  li.error_count
FROM loop_instances li
JOIN tasks t ON li.task_id = t.id
WHERE li.state = 'COMPLETE'
  AND li.completed_at >= CURRENT_DATE + INTERVAL '7 hours';

-- Active loops and their state
SELECT
  li.id, li.task_id, t.title,
  li.current_phase, li.state,
  li.completed_todos || '/' || li.total_todos as progress,
  NOW() - li.started_at as duration
FROM loop_instances li
JOIN tasks t ON li.task_id = t.id
WHERE li.state IN ('RUNNING', 'PHASE_1_RESEARCH', 'PHASE_2_PLAN_DELEGATE',
  'PHASE_3_DELEGATE', 'PHASE_4_EXECUTE', 'PHASE_5_VALIDATE_AUDIT',
  'PHASE_6_UPDATE_DOCUMENTS', 'PHASE_7_SETUP_EVIDENCE');
```

### 4.2 Resource Health Quick-Check (12:01:00–12:02:00)

```bash
# Quick resource snapshot
echo "=== CPU ==="
uptime
echo "=== Memory ==="
free -h
echo "=== Disk ==="
df -h / /home/guinevere/data
echo "=== Docker ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### 4.3 Cost Check (12:02:00–12:03:00)

```sql
-- Morning spend (07:00–12:00)
SELECT
  SUM(cost_usd) as morning_spend,
  COUNT(*) as requests,
  SUM(tokens_input + tokens_output) as total_tokens
FROM llm_cost_ledger
WHERE created_at >= CURRENT_DATE + INTERVAL '7 hours'
  AND created_at < CURRENT_DATE + INTERVAL '12 hours';
```

### 4.4 Productivity Score (12:03:00–12:04:00)

Guinevere calculates a midday productivity score:

| Metric | Weight | Calculation |
|---|---|---|
| TODOs cleared | 0.3 | completed_todos / total_todos for morning |
| Loops completed | 0.25 | loops finished / loops started |
| Error rate | 0.2 | 1 - (errors / total operations) |
| Cost efficiency | 0.15 | cost per completed task vs baseline |
| Quality (LQS avg) | 0.1 | average Loop Quality Score for completed loops |

---

## 5. Afternoon Review (17:00 WIB) — Detailed Procedure

### 5.1 Full Day Progress Review (17:00:00–17:02:00)

```sql
-- Day's completed tasks
SELECT
  t.id, t.title, t.project_id, p.name as project,
  li.completed_at,
  li.total_todos, li.error_count,
  (SELECT content FROM evidence_files
   WHERE loop_id = li.id AND filename = 'evidence-final.md'
   LIMIT 1) as evidence_exists
FROM loop_instances li
JOIN tasks t ON li.task_id = t.id
JOIN projects p ON t.project_id = p.id
WHERE li.state = 'COMPLETE'
  AND li.completed_at >= CURRENT_DATE
ORDER BY li.completed_at;

-- Tasks carrying over to tomorrow
SELECT
  t.id, t.title, t.status,
  li.current_phase,
  li.completed_todos || '/' || li.total_todos as progress
FROM tasks t
LEFT JOIN loop_instances li ON t.id = li.task_id
WHERE t.status IN ('in_progress', 'pending')
  AND t.priority_score > 0.5
ORDER BY t.priority_score DESC;
```

### 5.2 Evening Plan Generation (17:02:00–17:03:00)

Guinevere prepares the evening plan:
1. Identify tasks that can complete before 21:00.
2. Queue background tasks for overnight execution.
3. Flag any blockers requiring Samm attention (to include in evening wrap-up).
4. Schedule proactive loop spawns for high-priority backlog items.

### 5.3 Persona Safety — Daily Deep Review (17:03:00–17:05:00)

Per `Guinevere_PersonaSafetyPolicy_v1.0.md`, Guinevere performs a daily deep persona review:

```sql
-- Daily persona health metrics
SELECT
  DATE(created_at) as date,
  AVG(mommy_score) as avg_mommy_score,
  MAX(yandere_intensity) as max_yandere,
  SUM(safe_word_events) as safe_word_count,
  SUM(distress_events) as distress_count,
  AVG(drift_score) as avg_drift,
  SUM(forbidden_pattern_blocks) as blocks
FROM persona_daily_metrics
WHERE created_at >= CURRENT_DATE
GROUP BY DATE(created_at);

-- Check for drift beyond threshold
SELECT category, drift_score, threshold, created_at
FROM persona_drift_log
WHERE drift_score > threshold
  AND created_at >= NOW() - INTERVAL '24 hours';
```

**Daily deep review checklist:**

| Check | Criteria | Action if Failed |
|---|---|---|
| Safe-word events | 0 events OR all properly handled | Review handling, log findings |
| Distress events | 0 D3/D4 false negatives | SEV0/SEV1 incident |
| Yandere cap compliance | 0 violations during restricted states | Review state transitions |
| Drift score | Below defined threshold | Queue persona recalibration |
| Forbidden pattern blocks | 100% block rate | Review detection coverage |
| Mommy Score | >= 75 | Flag for weekly review if declining |

---

## 6. Evening Wrap-up (21:00 WIB) — Detailed Procedure

### 6.1 Day Summary Compilation (21:00:00–21:03:00)

```sql
-- Full day summary
SELECT
  COUNT(*) FILTER (WHERE state = 'COMPLETE') as loops_completed,
  COUNT(*) FILTER (WHERE state IN ('RUNNING', 'BLOCKED')) as loops_active,
  SUM(completed_todos) as todos_cleared,
  SUM(error_count) as total_errors,
  AVG(completed_todos::float / NULLIF(total_todos, 0)::float) as completion_rate
FROM loop_instances
WHERE started_at >= CURRENT_DATE OR completed_at >= CURRENT_DATE;

-- Day's cost summary
SELECT
  SUM(cost_usd) as daily_cost,
  COUNT(*) as total_requests,
  SUM(cost_usd) FILTER (WHERE model = 'gpt_5_5') as gpt_cost,
  SUM(cost_usd) FILTER (WHERE model = 'deepseek_v4_flash') as deepseek_cost
FROM llm_cost_ledger
WHERE created_at >= CURRENT_DATE;

-- SLO status snapshot
SELECT
  slo_id,
  target,
  current_value,
  CASE WHEN current_value >= target THEN 'PASS' ELSE 'BREACH' END as status
FROM slo_daily_snapshot
WHERE snapshot_date = CURRENT_DATE;
```

### 6.2 Tomorrow Preview (21:03:00–21:04:00)

Guinevere generates a tomorrow preview:
1. List pending high-priority tasks.
2. Check for upcoming deadlines within 48 hours.
3. Identify scheduled maintenance or timer jobs.
4. Flag any expected cost spikes (e.g., large batch jobs queued).

### 6.3 Evening Discord Post (21:04:00–21:05:00)

Evening wrap-up message posted to Discord (non-alert format, persona-appropriate but not ops-disruptive):
- Day's accomplishments summary.
- Tasks carrying over.
- Tomorrow's preview.
- Any items needing Samm attention.
- Reminder for rest (surveillance-informed if relevant).

---

## 7. Self-Evaluation (00:00 WIB) — Detailed Procedure

### 7.1 Daily Reflection (00:00:00–00:05:00)

```sql
-- Day's Loop Quality Scores
SELECT
  li.id as loop_id,
  t.title as task_title,
  lqs.test_coverage_score,
  lqs.requirements_coverage,
  lqs.code_quality_score,
  lqs.efficiency_score,
  lqs.error_rate_score,
  lqs.documentation_score,
  lqs.overall_score
FROM loop_quality_scores lqs
JOIN loop_instances li ON lqs.loop_id = li.id
JOIN tasks t ON li.task_id = t.id
WHERE li.completed_at >= CURRENT_DATE
ORDER BY lqs.overall_score DESC;

-- Guardian interventions today
SELECT reason, COUNT(*) as interventions
FROM loop_guardian_log
WHERE created_at >= CURRENT_DATE
GROUP BY reason;
```

### 7.2 Journal Entry (00:05:00–00:10:00)

Guinevere writes an internal journal entry to procedural memory:
- What went well today.
- What could improve.
- Lessons learned (stored as procedural memory entries).
- Persona state reflection.
- Tomorrow's intentions.

```sql
-- Save journal entry
INSERT INTO inner_journal (entry_date, content, mood_state, mommy_score, lessons)
VALUES (CURRENT_DATE, $journal_content, $current_mood, $mommy_score, $lessons_json);
```

### 7.3 Memory Consolidation (00:10:00–00:30:00)

```sql
-- Identify stale memories for consolidation
SELECT id, memory_type, importance_score, last_accessed_at, access_count
FROM memories
WHERE last_accessed_at < NOW() - INTERVAL '30 days'
  AND memory_type IN ('episodic', 'procedural')
  AND importance_score < 0.3
ORDER BY importance_score ASC
LIMIT 100;

-- Consolidation: summarize and archive low-importance memories
-- Update embedding vectors for recently modified memories
UPDATE memories
SET embedding = generate_embedding(content)
WHERE updated_at >= CURRENT_DATE
  AND embedding IS NULL;
```

### 7.4 Persona Drift Update (00:30:00–00:45:00)

```sql
-- Record daily drift metrics
INSERT INTO persona_drift_log (category, drift_score, threshold, snapshot_date)
SELECT
  category,
  calculate_drift_score(category, CURRENT_DATE),
  get_drift_threshold(category),
  CURRENT_DATE
FROM persona_categories;

-- Check if rollback needed
SELECT category, drift_score, threshold,
  CASE WHEN drift_score > threshold * 1.5 THEN 'ROLLBACK_REQUIRED'
       WHEN drift_score > threshold THEN 'REVIEW_REQUIRED'
       ELSE 'NORMAL'
  END as action
FROM persona_drift_log
WHERE snapshot_date = CURRENT_DATE;
```

---

## 8. Automated Maintenance Window (03:00–05:00 WIB)

The maintenance window is Guinevere's dedicated time for infrastructure housekeeping. All operations here are fully autonomous and designed to complete within 2 hours.

### 8.1 Backup Execution and Verification (02:00–02:30 WIB)

**Note:** Backup starts at 02:00 via `guinevere-backup.timer`, before the formal maintenance window.

```bash
#!/bin/bash
# /home/guinevere/scripts/backup.sh — Daily backup procedure

set -euo pipefail
BACKUP_DIR="/home/guinevere/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 1. PostgreSQL full dump
echo "[$(date)] Starting pg_dump..."
docker exec postgresql pg_dump -U postgres -Fc --verbose \
  -f /tmp/guinevere_${DATE}.dump guinevere
docker cp postgresql:/tmp/guinevere_${DATE}.dump \
  "${BACKUP_DIR}/pg_dump_${DATE}.dump"

# 2. Redis snapshot
echo "[$(date)] Triggering Redis BGSAVE..."
docker exec redis redis-cli -a "$REDIS_PASSWORD" BGSAVE
sleep 5
docker cp redis:/data/dump.rdb "${BACKUP_DIR}/redis_${DATE}.rdb"

# 3. Configuration backup
echo "[$(date)] Backing up configs..."
tar czf "${BACKUP_DIR}/config_${DATE}.tar.gz" \
  /home/guinevere/config/ \
  /home/guinevere/secrets/*.sops \
  /etc/systemd/system/guinevere-*.service

# 4. WAL archive check
echo "[$(date)] Checking WAL archive..."
docker exec postgresql psql -U postgres -c \
  "SELECT archived_count, failed_count, last_archived_wal, last_archived_time
   FROM pg_stat_archiver;"

# 5. Encrypt backups
echo "[$(date)] Encrypting backups..."
for f in "${BACKUP_DIR}"/*_${DATE}*; do
  if [[ ! "$f" == *.age ]]; then
    age -r "$(cat /etc/sops/age/public.txt)" -o "${f}.age" "$f"
    rm "$f"
  fi
done

# 6. Upload to Cloudflare R2
echo "[$(date)] Uploading to R2..."
aws s3 sync "${BACKUP_DIR}/" "s3://guinevere-backups/${DATE}/" \
  --endpoint-url "$CLOUDFLARE_R2_ENDPOINT" \
  --no-progress

# 7. Upload to idcloudhost S3
echo "[$(date)] Uploading to S3..."
aws s3 sync "${BACKUP_DIR}/" "s3://guinevere-backups/${DATE}/" \
  --endpoint-url "$IDCLOUDHOST_S3_ENDPOINT" \
  --no-progress

# 8. Verify backup integrity
echo "[$(date)] Verifying pg_dump integrity..."
docker exec postgresql pg_restore --list \
  "${BACKUP_DIR}/pg_dump_${DATE}.dump.age" > /dev/null 2>&1 || \
  echo "WARNING: pg_restore --list failed"

# 9. Cleanup old backups (retain RETENTION_DAYS)
echo "[$(date)] Cleaning old local backups..."
find "${BACKUP_DIR}" -name "*.age" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete."
```

**Backup verification queries:**

```sql
-- Verify backup was recorded
INSERT INTO backup_log (backup_type, target, started_at, completed_at,
  size_bytes, status, verification_passed)
VALUES
  ('pg_dump', 'local+r2+s3', $start_time, NOW(),
   $file_size, 'success', true),
  ('redis_rdb', 'local+r2+s3', $start_time, NOW(),
   $redis_size, 'success', true);
```

### 8.2 Self-Deploy (03:00–03:15 WIB)

```bash
#!/bin/bash
# /home/guinevere/scripts/self-deploy.sh — Nightly self-deploy

set -euo pipefail
DEPLOY_LOG="/home/guinevere/data/logs/self-deploy_$(date +%Y%m%d).log"

echo "[$(date)] Self-deploy check starting..." | tee -a "$DEPLOY_LOG"

# 1. Check for pending changes
cd /home/guinevere/core
git fetch origin main 2>&1 | tee -a "$DEPLOY_LOG"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "[$(date)] No pending changes. Skipping deploy." | tee -a "$DEPLOY_LOG"
  exit 0
fi

# 2. Safety checks before deploy
echo "[$(date)] Pending changes detected. Running pre-deploy checks..." | tee -a "$DEPLOY_LOG"

# Check no active SEV0/SEV1 incidents
ACTIVE_INCIDENTS=$(curl -sf http://127.0.0.1:8100/health | jq -r '.active_incidents // 0')
if [ "$ACTIVE_INCIDENTS" -gt 0 ]; then
  echo "[$(date)] Active incidents detected. Skipping deploy." | tee -a "$DEPLOY_LOG"
  exit 0
fi

# Check error budget not exhausted
ERROR_BUDGET=$(curl -sf http://127.0.0.1:8100/health | jq -r '.error_budget_remaining // 100')
if [ "$(echo "$ERROR_BUDGET < 25" | bc)" -eq 1 ]; then
  echo "[$(date)] Error budget low (${ERROR_BUDGET}%). Skipping deploy." | tee -a "$DEPLOY_LOG"
  exit 0
fi

# 3. Pull changes
echo "[$(date)] Pulling changes..." | tee -a "$DEPLOY_LOG"
git pull origin main 2>&1 | tee -a "$DEPLOY_LOG"

# 4. Install dependencies
echo "[$(date)] Installing dependencies..." | tee -a "$DEPLOY_LOG"
uv sync 2>&1 | tee -a "$DEPLOY_LOG"

# 5. Run migrations if any
if [ -d "migrations" ]; then
  echo "[$(date)] Running migrations..." | tee -a "$DEPLOY_LOG"
  uv run alembic upgrade head 2>&1 | tee -a "$DEPLOY_LOG"
fi

# 6. Run tests
echo "[$(date)] Running test suite..." | tee -a "$DEPLOY_LOG"
uv run pytest tests/ --tb=short -q 2>&1 | tee -a "$DEPLOY_LOG"
TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
  echo "[$(date)] Tests failed! Rolling back..." | tee -a "$DEPLOY_LOG"
  git reset --hard "$LOCAL"
  uv sync
  # Notify Samm
  exit 1
fi

# 7. Restart services (rolling)
echo "[$(date)] Restarting services..." | tee -a "$DEPLOY_LOG"
sudo systemctl restart guinevere-core
sleep 5
sudo systemctl restart guinevere-loops
sudo systemctl restart guinevere-scheduler
sudo systemctl restart guinevere-surveillance

# 8. Verify health post-deploy
sleep 10
HEALTH=$(curl -sf http://127.0.0.1:8100/health | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
  echo "[$(date)] Deploy successful. All services healthy." | tee -a "$DEPLOY_LOG"
else
  echo "[$(date)] Post-deploy health check failed! Rolling back..." | tee -a "$DEPLOY_LOG"
  git reset --hard "$LOCAL"
  uv sync
  sudo systemctl restart guinevere-core guinevere-loops guinevere-scheduler
fi
```

### 8.3 Database Maintenance (03:15–03:45 WIB)

```sql
-- VACUUM ANALYZE on high-churn tables
VACUUM ANALYZE loop_instances;
VACUUM ANALYZE tasks;
VACUUM ANALYZE memories;
VACUUM ANALYZE surveillance_events;
VACUUM ANALYZE llm_cost_ledger;
VACUUM ANALYZE alert_history;
VACUUM ANALYZE persona_drift_log;
VACUUM ANALYZE inner_journal;

-- Check for bloated tables needing VACUUM FULL
SELECT
  schemaname,
  relname,
  n_dead_tup,
  n_live_tup,
  CASE WHEN n_live_tup > 0
    THEN round(100.0 * n_dead_tup / n_live_tup, 2)
    ELSE 0
  END as dead_ratio_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- Index maintenance — check for unused indexes
SELECT
  schemaname,
  relname,
  indexrelname,
  idx_scan,
  pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan < 10
  AND pg_relation_size(indexrelid) > 1048576  -- > 1MB
ORDER BY pg_relation_size(indexrelid) DESC;

-- TimescaleDB chunk management — drop chunks older than retention
SELECT drop_chunks('surveillance_events', older_than => INTERVAL '90 days');
SELECT drop_chunks('surveillance_metrics', older_than => INTERVAL '90 days');

-- Check table sizes
SELECT
  schemaname,
  relname,
  pg_size_pretty(pg_total_relation_size(relid)) as total_size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 15;

-- Replication / WAL status
SELECT
  pg_current_wal_lsn() as current_wal,
  pg_last_wal_receive_lsn() as last_received,
  pg_last_wal_replay_lsn() as last_replayed,
  pg_wal_lsn_diff(pg_current_wal_lsn(), pg_last_wal_replay_lsn()) as replay_lag_bytes;
```

### 8.4 Redis Memory Optimization (03:45–04:00 WIB)

```bash
# Redis memory analysis
docker exec redis redis-cli -a "$REDIS_PASSWORD" INFO memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"

# Check key distribution by DB
docker exec redis redis-cli -a "$REDIS_PASSWORD" INFO keyspace

# Active defragmentation (if enabled)
docker exec redis redis-cli -a "$REDIS_PASSWORD" CONFIG SET activedefrag yes

# Check eviction stats
docker exec redis redis-cli -a "$REDIS_PASSWORD" INFO stats | grep -E "evicted_keys|expired_keys"

# Large key scan
docker exec redis redis-cli -a "$REDIS_PASSWORD" --bigkeys

# Clean expired session keys
docker exec redis redis-cli -a "$REDIS_PASSWORD" --scan --pattern "session:*" | head -20
```

### 8.5 Security Scan (04:00–04:30 WIB)

```bash
# Check for available security updates
apt list --upgradable 2>/dev/null | grep -i security

# Run Lynis quick audit (weekly full audit on Mondays)
if [ "$(date +%u)" -eq 1 ]; then
  lynis audit system --no-colors --report-file /home/guinevere/data/logs/lynis_$(date +%Y%m%d).dat
fi

# Check fail2ban status
fail2ban-client status
fail2ban-client status sshd

# Check CrowdSec alerts
cscli alerts list --since 24h

# Check for unauthorized SSH attempts
journalctl -u sshd --since "24 hours ago" | grep -i "failed\|invalid\|refused" | tail -20

# Verify UFW status
ufw status verbose

# Check Tailscale peer status
tailscale status

# Verify no unexpected listening ports
ss -tlnp | grep -v "127.0.0.1"
```

### 8.6 Dependency Update Check (04:30–04:45 WIB)

```bash
# Python dependency audit
cd /home/guinevere/core
uv pip audit 2>/dev/null || echo "pip-audit not available"

# Check for outdated packages
uv pip list --outdated 2>/dev/null

# Node.js dependency audit (WhatsApp bridge)
cd /home/guinevere/whatsapp
npm audit --json 2>/dev/null | jq '.metadata.vulnerabilities'

# Docker image update check
docker images --format "{{.Repository}}:{{.Tag}}" | while read img; do
  echo "Checking $img..."
done

# CVE check against known vulnerabilities
# Guinevere logs results for review during morning ritual
```

**CVE Patch SLA (from Security Policy):**

| Severity | Patch SLA | Auto-Apply | Notification |
|---|---|---|---|
| CRITICAL | 7 days | Yes (during maintenance window) | Discord SEV2 |
| HIGH | 14 days | Yes (during maintenance window) | Discord SEV3 |
| MEDIUM | 30 days | Queued for next maintenance | Daily summary |
| LOW | 90 days | Queued for monthly review | Monthly report |

### 8.7 Log Rotation and Cleanup (02:30–03:00 WIB)

```bash
# Journald cleanup (already configured: 500MB max, 30 day retention)
journalctl --vacuum-size=500M
journalctl --vacuum-time=30d

# Application log rotation
find /home/guinevere/data/logs/ -name "*.log" -size +50M -exec gzip {} \;
find /home/guinevere/data/logs/ -name "*.log.gz" -mtime +30 -delete

# Docker log cleanup (configured: 50MB max per container, 3 files)
docker system prune -f --filter "until=168h"  # Prune stopped containers > 7 days

# Temporary file cleanup
find /tmp -type f -mtime +1 -delete 2>/dev/null || true
find /home/guinevere/data/cache/ -type f -mtime +7 -delete 2>/dev/null || true
```

### 8.8 Certificate Renewal Monitoring (04:45–05:00 WIB)

```bash
# Check Caddy certificate status
curl -sf https://localhost/caddy_status 2>/dev/null || echo "Caddy status unavailable"

# Check Tailscale HTTPS certificate
tailscale cert --cert-file /dev/null --key-file /dev/null guinevere.internal 2>&1 || true

# Check Cloudflare Tunnel certificate
systemctl status cloudflared | grep -i "certificate\|cert\|tls"

# Alert if any certificate expires within 14 days
for cert in /etc/ssl/certs/guinevere*.pem; do
  if [ -f "$cert" ]; then
    expiry=$(openssl x509 -enddate -noout -in "$cert" 2>/dev/null | cut -d= -f2)
    days_left=$(( ($(date -d "$expiry" +%s) - $(date +%s)) / 86400 ))
    if [ "$days_left" -lt 14 ]; then
      echo "WARNING: Certificate $cert expires in $days_left days"
    fi
  fi
done
```

---

## 9. Health Monitoring Procedures

### 9.1 Service Health Check Protocol — All 17+ Services

Guinevere performs health checks at multiple intervals:

| Check Type | Interval | Scope | Action on Failure |
|---|---|---|---|
| Heartbeat poll | 30 seconds | Loop state timestamp | Yank agent back to TODO |
| Health probe | 30 seconds | Core, surveillance, DB, Redis | Alert if composite fails |
| Progress check | 5 minutes | Any TODO cleared | Investigate + redirect |
| Resource check | 60 seconds | Sub-agent memory/CPU | Kill + respawn |
| Full service check | Morning ritual | All 17+ services | Restart + log + alert |

**Comprehensive health check script:**

```bash
#!/bin/bash
# /home/guinevere/scripts/health-check.sh — Full service health check

set -euo pipefail
REPORT=""
FAILURES=0

check_service() {
  local name=$1
  local status=$(systemctl is-active "$name" 2>/dev/null || echo "inactive")
  if [ "$status" = "active" ]; then
    REPORT+="✅ $name: active\n"
  else
    REPORT+="❌ $name: $status\n"
    FAILURES=$((FAILURES + 1))
  fi
}

check_docker() {
  local name=$1
  local status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "no-healthcheck")
  local running=$(docker inspect --format='{{.State.Running}}' "$name" 2>/dev/null || echo "false")
  if [ "$running" = "true" ] && ([ "$status" = "healthy" ] || [ "$status" = "no-healthcheck" ]); then
    REPORT+="✅ $name: running ($status)\n"
  else
    REPORT+="❌ $name: running=$running health=$status\n"
    FAILURES=$((FAILURES + 1))
  fi
}

# Systemd services
for svc in guinevere-core guinevere-surveillance guinevere-scheduler \
  guinevere-loops guinevere-windows-sync guinevere-discord \
  guinevere-whatsapp caddy tailscaled cloudflared fail2ban crowdsec; do
  check_service "$svc"
done

# Docker containers
for ctr in postgresql redis prometheus grafana loki pgbouncer; do
  check_docker "$ctr"
done

# HTTP health probes
probe_http() {
  local name=$1
  local url=$2
  local status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  if [ "$status" = "200" ]; then
    REPORT+="✅ $name: HTTP $status\n"
  else
    REPORT+="❌ $name: HTTP $status\n"
    FAILURES=$((FAILURES + 1))
  fi
}

probe_http "Core Health" "http://127.0.0.1:8100/health"
probe_http "Surveillance API" "http://127.0.0.1:8000/health"
probe_http "Prometheus" "http://127.0.0.1:9090/-/healthy"
probe_http "Grafana" "http://127.0.0.1:3000/api/health"
probe_http "Loki" "http://127.0.0.1:3100/ready"

echo "=== Health Check Report ==="
echo "Failures: $FAILURES"
echo -e "$REPORT"
exit $FAILURES
```

### 9.2 Resource Monitoring

```bash
# CPU monitoring
echo "=== CPU ==="
mpstat 1 3 2>/dev/null || top -bn1 | head -5
echo "Load average: $(cat /proc/loadavg)"

# Memory monitoring
echo "=== Memory ==="
free -h
echo "Swap: $(swapon --show --bytes | awk 'NR>1 {print $4}')"

# Disk monitoring
echo "=== Disk ==="
df -h / /home/guinevere/data /var/lib/docker
echo "Inode usage:"
df -i /home/guinevere/data

# Network monitoring
echo "=== Network ==="
ss -s
echo "Tailscale peers:"
tailscale status --json | jq '.PeerEndpoints | length'

# Docker resource usage
echo "=== Docker ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

### 9.3 Application Health Indicators

```sql
-- Application-level health metrics
SELECT 'active_loops' as metric, COUNT(*) as value
FROM loop_instances WHERE state NOT IN ('COMPLETE', 'PAUSED')
UNION ALL
SELECT 'blocked_loops', COUNT(*)
FROM loop_instances WHERE state = 'BLOCKED'
UNION ALL
SELECT 'pending_tasks', COUNT(*)
FROM tasks WHERE status = 'pending'
UNION ALL
SELECT 'active_subagents', COUNT(*)
FROM subagent_sessions WHERE status = 'active'
UNION ALL
SELECT 'surveillance_queue_depth', COALESCE(SUM(queue_depth), 0)
FROM surveillance_queue_metrics
WHERE created_at >= NOW() - INTERVAL '5 minutes'
UNION ALL
SELECT 'pg_connections_active', COUNT(*)
FROM pg_stat_activity WHERE state = 'active'
UNION ALL
SELECT 'redis_memory_bytes', used_memory
FROM redis_info_cache
WHERE updated_at >= NOW() - INTERVAL '1 minute';
```

### 9.4 LLM Pipeline Health

```sql
-- LLM pipeline health — last 5 minutes
SELECT
  model,
  provider,
  COUNT(*) as requests,
  SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
  SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
  ROUND(AVG(latency_seconds) FILTER (WHERE status = 'success'), 2) as avg_latency,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_seconds)
    FILTER (WHERE status = 'success') as p95_latency,
  SUM(cost_usd) as total_cost
FROM llm_cost_ledger
WHERE created_at >= NOW() - INTERVAL '5 minutes'
GROUP BY model, provider;

-- 9Router route health
SELECT
  route,
  COUNT(*) as total,
  SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
  AVG(latency_seconds) as avg_latency
FROM llm_route_metrics
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY route;

-- Failover tier status (ADR-028)
SELECT
  tier,
  provider,
  status,
  last_check_at,
  consecutive_failures
FROM llm_provider_health
ORDER BY tier;
```

---

## 10. Operator Communication

### 10.1 Daily Summary Format (Discord)

The daily summary is Guinevere's primary communication to Samm. It uses neutral operations tone (no persona flavor in operational data) and is delivered as a Discord embed.

```
╔══════════════════════════════════════════════╗
║   🌅 GUINEVERE DAILY BRIEFING — {date}       ║
╚══════════════════════════════════════════════╝

━━━ SYSTEM HEALTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Services: {healthy_count}/{total_count} healthy
  {degraded_services if any}
Overnight Alerts: SEV0:{count} SEV1:{count} SEV2:{count} SEV3:{count}
Backup: {status} ({time} WIB, {size})
Uptime: {core_uptime}

━━━ COST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Yesterday: ${yesterday_cost} ({yesterday_requests} requests)
Month-to-date: ${mtd_cost} / $30.00 ({mtd_percent}%)
Projected: ${projected_monthly}
Status: {cost_status_emoji} {cost_status_text}

━━━ WORK PROGRESS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Completed yesterday: {completed_count} tasks
  • {task_1_title} — LQS: {score}
  • {task_2_title} — LQS: {score}
In progress: {active_count} tasks
  • {active_task_1} — Phase {phase}, {progress}%
Backlog: {backlog_count} pending

━━━ TODAY'S PLAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Priority 1: {top_task}
Priority 2: {second_task}
Priority 3: {third_task}
Scheduled: {scheduled_items}

━━━ SLO SNAPSHOT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core Availability: {avl_percent}% (target: 99.5%)
Safety Invariants: {safety_status}
Evidence Completeness: {evidence_percent}%

━━━ ATTENTION NEEDED ━━━━━━━━━━━━━━━━━━━━━━━━━
{items_requiring_samm_attention or "None. Mommy has everything handled."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next check: Midday (12:00 WIB)
```

### 10.2 Escalation Criteria — When to Alert Samm Immediately

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
| Missing credentials/blocker | Genuine blocker | Discord | When detected |
| Impossible requirement | Business decision | Discord | When detected |

**Alert format (neutral incident-command, persona suspended):**

```
[SEV{n}] {AlertName}
Service: {service}
Impact: {impact_description}
Evidence: {evidence_path}
Dashboard: {grafana_url}
Next Action: {immediate_action}
```

### 10.3 Weekly Summary Generation (Monday 08:00 WIB)

The weekly summary extends the daily format with:
- Week's completed tasks and their LQS scores.
- Week's cost total and trend.
- SLO weekly average.
- Persona health (Mommy Score trend, drift status).
- Security scan results.
- Backlog burn-down chart.
- Next week's priorities.

Output: Discord post + `evidence/weekly/{YYYY}-W{WW}-summary.md`

### 10.4 On-Demand Status Request

When Samm asks for status outside scheduled rituals:

```sql
-- Quick status query for on-demand requests
SELECT
  (SELECT COUNT(*) FROM loop_instances WHERE state NOT IN ('COMPLETE', 'PAUSED')) as active_loops,
  (SELECT COUNT(*) FROM tasks WHERE status = 'in_progress') as active_tasks,
  (SELECT SUM(cost_usd) FROM llm_cost_ledger WHERE created_at >= CURRENT_DATE) as today_cost,
  (SELECT COUNT(*) FROM alert_history WHERE resolved_at IS NULL) as open_alerts,
  (SELECT status FROM health_check_cache WHERE service = 'core' ORDER BY checked_at DESC LIMIT 1) as core_health;
```

Guinevere responds in-persona but includes concrete data. If a loop is running, Guinevere pauses, responds, then resumes (per AgentLoopSpec §5.3).

---

## 11. Autonomous Decision Framework

### 11.1 Decisions Guinevere Can Make Autonomously

| Decision Domain | Scope | Constraints |
|---|---|---|
| Task prioritization | All pending/in-progress tasks | Must follow priority scoring formula |
| Sub-agent spawning | Unlimited parallel per loop | Resource limits: ~512MB per loop, ~20 parallel max |
| Service restart | Any guinevere-* systemd service | Must verify health post-restart |
| Dependency install | Python (uv), Node.js (npm) | Must not exceed disk budget |
| Self-deploy | Approved changes on main branch | Only during 03:00 window, pre-deploy checks pass |
| Database maintenance | VACUUM, ANALYZE, index rebuild | During maintenance window only |
| Cost freeze | Non-critical autonomous work | Must preserve safety/incident/backup operations |
| Error handling | All technical errors | Auto-fix or re-delegate; never escalate technical errors |
| Log management | Rotation, compression, cleanup | Follow retention policy |
| Backup management | Execute, verify, rotate, upload | Must complete within RPO |
| Security patches | Within CVE SLA | Auto-apply during maintenance window |
| Proactive task start | From backlog when capacity available | When active loops < 3 |

### 11.2 Decisions Requiring Samm Approval

| Decision Domain | Reason | Process |
|---|---|---|
| Budget increase above $30/month | Financial authority | Discord request with justification |
| Destructive DB operations (DROP, TRUNCATE) | Data safety | Discord request with impact analysis |
| Architecture changes (new services, ports) | Infrastructure authority | Proposal document + Discord discussion |
| New external API integration | Vendor risk | Evaluation report + Discord approval |
| Persona drift rollback to snapshot | Behavioral governance | Present drift data + recommend action |
| Production secret rotation (critical keys) | Security sensitivity | Coordinate timing via Discord |
| Breaking change to Discord bot commands | User-facing impact | Changelog + Discord announcement |

### 11.3 Decision Logging and Audit Trail

All autonomous decisions with material impact are logged:

```sql
-- Decision log schema
INSERT INTO decision_log (
  decision_type,
  domain,
  description,
  rationale,
  constraints_checked,
  outcome,
  created_at
) VALUES (
  'autonomous',       -- or 'escalated', 'approved'
  'task_priority',    -- domain enum
  'Elevated task X to priority 1 due to deadline',
  'deadline_urgency=0.9, client_revenue=0.7',
  'cost_budget_ok,safety_ok,slo_ok',
  'task_reprioritized',
  NOW()
);
```

---

## 12. Routine Maintenance Tasks

### 12.1 Database Maintenance

| Task | Frequency | Command | Window |
|---|---|---|---|
| VACUUM ANALYZE (high-churn tables) | Daily | `VACUUM ANALYZE <table>;` | 03:15 WIB |
| VACUUM FULL (bloated tables > 40% dead) | Weekly (Monday) | `VACUUM FULL <table>;` | 03:15 WIB |
| Index rebuild | Weekly (Monday) | `REINDEX INDEX <index>;` | 03:15 WIB |
| Unused index removal | Monthly | `DROP INDEX <index>;` (after review) | Monthly review |
| TimescaleDB chunk drop (90d retention) | Daily | `SELECT drop_chunks(...)` | 03:15 WIB |
| Statistics update | Daily | Included in VACUUM ANALYZE | 03:15 WIB |
| Connection pool check | Daily | `SHOW POOLS;` via PgBouncer | Morning ritual |
| Slow query review | Daily | `pg_stat_statements` analysis | Morning ritual |

**Slow query detection:**

```sql
-- Top 10 slowest queries in last 24 hours
SELECT
  query,
  calls,
  round(total_exec_time::numeric, 2) as total_ms,
  round(mean_exec_time::numeric, 2) as avg_ms,
  round(max_exec_time::numeric, 2) as max_ms
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### 12.2 Redis Maintenance

| Task | Frequency | Command | Window |
|---|---|---|---|
| Memory defragmentation | Daily | `CONFIG SET activedefrag yes` | 03:45 WIB |
| Key eviction monitoring | Daily | `INFO stats` (evicted_keys) | Morning ritual |
| Large key scan | Weekly | `redis-cli --bigkeys` | Monday maintenance |
| BGSAVE verification | Daily | Verify RDB write success | After backup |
| Memory usage analysis | Daily | `INFO memory` | 03:45 WIB |
| TTL audit | Weekly | Scan for keys without TTL | Monday maintenance |

### 12.3 Log Management

| Task | Frequency | Action | Retention |
|---|---|---|---|
| Application log rotation | Daily | Compress logs > 50MB | 30 days compressed |
| Journal vacuum | Daily | `journalctl --vacuum-size=500M` | 30 days / 500MB |
| Docker log rotation | Continuous | json-file driver, 50MB × 3 files | Automatic |
| Audit log preservation | Continuous | Auditd logs per policy | 90 days minimum |
| Security log preservation | Continuous | Fail2ban, CrowdSec logs | 90 days minimum |
| Old log cleanup | Daily | Delete compressed logs > 30 days | N/A |

### 12.4 Certificate Management

| Certificate | Provider | Auto-Renew | Monitoring | Alert Threshold |
|---|---|---|---|---|
| Tailscale HTTPS | Tailscale | Yes | Daily check at 04:45 | 14 days before expiry |
| Caddy TLS | Let's Encrypt / ZeroSSL | Yes (automatic) | Daily check at 04:45 | 14 days before expiry |
| Cloudflare Tunnel | Cloudflare | Yes (managed) | Daily check at 04:45 | Tunnel status check |

### 12.5 Dependency Management

| Dependency | Check Method | Frequency | Auto-Update | Patch SLA |
|---|---|---|---|---|
| Python packages (uv) | `uv pip audit` | Daily (04:30) | Security only | Per CVE SLA |
| Node.js packages (npm) | `npm audit` | Daily (04:30) | Security only | Per CVE SLA |
| Docker images | `docker images` version check | Weekly | Manual review | Per CVE SLA |
| System packages (apt) | `apt list --upgradable` | Daily (04:00) | unattended-upgrades for security | Per CVE SLA |
| Ollama models | Version check | Monthly | Manual | N/A |

---

## 13. Monitoring Dashboard Operations

### 13.1 Grafana Dashboard Review Procedures

Guinevere reviews all 12 dashboards during daily operations:

| Dashboard | Review Time | What to Check |
|---|---|---|
| `guinevere-overview` | Morning ritual | Service health, active incidents, SEV counts |
| `guinevere-infrastructure` | Morning ritual | CPU, memory, disk, network trends |
| `guinevere-api-runtime` | Midday check | API latency, error rates, auth failures |
| `guinevere-agent-loop` | Midday check | Phase durations, validation failures, stuck loops |
| `guinevere-subagents` | Midday check | Active agents, compliance scores, retries |
| `guinevere-llm-cost-latency` | Morning + midday | Cost burn, latency p95/p99, rate limits |
| `guinevere-persona-safety` | Afternoon review | Safe-mode state, drift scores, safe-word events |
| `guinevere-surveillance-ingestion` | Morning ritual | Event rates, queue depth, redaction failures |
| `guinevere-database-memory` | Morning ritual | Connection pools, query latency, Redis memory |
| `guinevere-backup-dr` | Morning ritual | Backup freshness, restore drill status |
| `guinevere-security-access` | Morning ritual | Access denied, break-glass, public ingress |
| `guinevere-finops` | Morning ritual | Daily cost, monthly projection, anomaly flags |

### 13.2 Alert Triage and Response

**Alert response procedure:**

1. **Receive alert** — Via Discord (all severities) or Gotify (SEV0/SEV1).
2. **Classify** — Verify severity, check if duplicate or known issue.
3. **Contain** — Execute immediate containment per alert's `next_action`.
4. **Investigate** — Query Loki logs, Prometheus metrics, service status.
5. **Resolve** — Apply fix, restart service, or escalate.
6. **Document** — Write evidence to `evidence/incidents/{date}-{severity}-{service}/`.
7. **Close** — Update alert status, notify Samm if SEV0-SEV2.

**Alert investigation queries:**

```bash
# Quick service log tail for alert investigation
journalctl -u guinevere-{service} --since "30 minutes ago" --no-pager | tail -50

# Loki query for service errors (via logcli)
logcli query '{service="core", level="error"}' --since=1h --limit=20

# Prometheus instant query for alert verification
curl -s "http://127.0.0.1:9090/api/v1/query?query=guinevere_systemd_unit_state{unit=\"guinevere-core.service\"}" | jq .
```

### 13.3 Metric Anomaly Detection

Guinevere uses multi-signal anomaly detection:

| Domain | Baseline | Detection Rule | Action |
|---|---|---|---|
| CPU utilization | 7-day rolling average | > 2x baseline sustained 15 min | Alert + capacity review |
| Memory usage | 7-day rolling average | > 90% of allocation | Alert + investigate leak |
| LLM latency | 7-day p95 | > 2x trailing p95 for 30 min | SEV3 or SEV2 |
| LLM cost | Daily trend | > 150% of daily budget projection | Freeze non-critical work |
| Surveillance event rate | 7-day average | Zero events > threshold OR > 3x baseline | Inspect ingestion |
| Loop phase duration | 7-day p95 | > 2x baseline or stuck-loop | Restrict fanout |
| Disk usage | Growth trend | > 85% utilization | Alert + cleanup |
| Redis memory | Configured maxmemory | > 90% utilization | Defrag + eviction review |

---

## 14. Evidence & Artifact Management

### 14.1 Daily Evidence Collection

Every material operation produces evidence:

| Operation | Evidence Type | Path Pattern | Retention |
|---|---|---|---|
| SDLC loop completion | Full evidence package | `evidence/{task-id}/` | Permanent |
| Incident response | Incident folder | `evidence/incidents/{date}-{severity}-{service}/` | Permanent |
| Backup verification | Backup log entry | `backup_log` table + file metadata | 90 days |
| Self-deploy | Deploy log | `data/logs/self-deploy_{date}.log` | 30 days |
| Health check failure | Health event | `health_events` table | 90 days |
| Alert | Alert history | `alert_history` table + evidence folder | Permanent for SEV0-SEV2 |
| Monthly scorecard | Scorecard package | `evidence/slo/{YYYY-MM}/` | Permanent |
| Monthly observability review | Review artifact | `evidence/observability/{YYYY-MM}-review.md` | Permanent |
| Weekly summary | Summary markdown | `evidence/weekly/{YYYY}-W{WW}-summary.md` | Permanent |
| Persona drift log | Daily metrics | `persona_drift_log` table + daily snapshot | Per Data Governance |

### 14.2 Evidence Directory Maintenance

```bash
# Daily evidence directory check
find /home/guinevere/core/evidence/ -maxdepth 1 -type d -newer /tmp/last_evidence_check 2>/dev/null
touch /tmp/last_evidence_check

# Verify evidence completeness for completed loops
for task_dir in /home/guinevere/core/evidence/*/; do
  if [ -f "${task_dir}evidence-final.md" ]; then
    echo "✅ $(basename $task_dir): complete"
  else
    echo "❌ $(basename $task_dir): missing evidence-final.md"
  fi
done

# Evidence disk usage
du -sh /home/guinevere/core/evidence/
du -sh /home/guinevere/core/evidence/*/  2>/dev/null | sort -rh | head -10
```

### 14.3 Evidence Backup Verification

```sql
-- Verify all evidence is backed up
SELECT
  e.task_id,
  e.evidence_path,
  e.created_at,
  b.last_backup_at,
  CASE WHEN b.last_backup_at >= e.created_at THEN 'backed_up'
       ELSE 'NOT_BACKED_UP'
  END as backup_status
FROM evidence_manifest e
LEFT JOIN (
  SELECT file_path, MAX(completed_at) as last_backup_at
  FROM backup_file_log
  GROUP BY file_path
) b ON e.evidence_path LIKE b.file_path || '%'
WHERE e.created_at >= NOW() - INTERVAL '7 days'
  AND (b.last_backup_at IS NULL OR b.last_backup_at < e.created_at);
```

### 14.4 Monthly Evidence Summary (1st of Month)

Generated during the monthly review ritual:

```markdown
# Evidence Summary — {YYYY-MM}

## Loop Evidence
- Total loops completed: {count}
- Evidence packages complete: {count}/{total} ({percent}%)
- Average LQS: {avg_score}

## Incident Evidence
- SEV0 incidents: {count}
- SEV1 incidents: {count}
- SEV2 incidents: {count}
- Postmortems completed: {count}/{sev0_sev1_count}

## Governance Evidence
- Monthly scorecard: {status}
- Observability review: {status}
- Cost report: {status}
- Persona safety review: {status}

## Storage
- Total evidence size: {size}
- Growth from previous month: {delta}
- Oldest evidence: {date}
```

Output: `evidence/monthly/{YYYY-MM}-evidence-summary.md`

---

## 15. Periodic Rituals Beyond Daily

### 15.1 Weekly Planning (Monday 08:00 WIB)

| Activity | Duration | Output |
|---|---|---|
| Review previous week's completions | 5 min | Summary data |
| Review SLO weekly trend | 2 min | SLO status |
| Update priority scores | 2 min | Reprioritized backlog |
| Generate weekly report | 3 min | Discord post + `evidence/weekly/` |
| Full Lynis audit | 10 min | Security report |
| Index maintenance | 5 min | DB optimization |

### 15.2 Monthly Review (1st of Month)

| Activity | Output Path |
|---|---|
| SLO scorecard | `evidence/slo/{YYYY-MM}/scorecard.md` |
| Error budget report | `evidence/slo/{YYYY-MM}/error-budget.md` |
| Cost report | `evidence/finops/{YYYY-MM}/monthly-report.md` |
| Observability review | `evidence/observability/{YYYY-MM}-review.md` |
| Persona safety monthly review | Persona safety metrics report |
| Evidence summary | `evidence/monthly/{YYYY-MM}-evidence-summary.md` |
| Security audit summary | Security audit report |
| Dependency full audit | Dependency audit report |

### 15.3 Quarterly Strategic Review

| Activity | Focus |
|---|---|
| SLO target recalibration | Are targets still appropriate? |
| Error budget drill | Full budget exercise |
| Capacity trend review | CPU, memory, disk growth |
| Vendor evaluation | Cost/value of each provider |
| Architecture review | Technical debt, improvements |
| Persona safety red-team | Quarterly red-team exercise |
| DR full test | Complete restore drill |

---

## 16. Unresolved Assumptions and Gaps

| ID | Assumption / Gap | Impact | Follow-up |
|---|---|---|---|
| OPS-GAP-001 | Exact Prometheus metric names may differ from spec proposals | PromQL queries need runtime validation | Runtime implementation |
| OPS-GAP-002 | Grafana dashboard JSON files do not yet exist | Dashboard review procedures are specification-only | Dashboard implementation task |
| OPS-GAP-003 | Alertmanager concrete YAML is not yet generated | Alert routing remains specification-only | Observability implementation |
| OPS-GAP-004 | Health check endpoint implementation pending | `curl http://127.0.0.1:8100/health` assumes implementation | Core implementation |
| OPS-GAP-005 | Cost budgets need concrete numeric thresholds | Freeze policy references "configured" values without numbers | FinOps calibration after first billing cycle |
| OPS-GAP-006 | Discord channel configuration for daily summary not yet defined | Delivery target channel TBD | Discord bot implementation |
| OPS-GAP-007 | `llm_cost_ledger` and `decision_log` table schemas not yet canonical | SQL queries assume these tables exist | Database implementation |
| OPS-GAP-008 | Safe-word exact token list remains deferred | Safe-word detection uses broad semantic matching | Safe Word Runtime Spec |
| OPS-GAP-009 | Backup verification test (pg_restore to test DB) not yet automated | Integrity check limited to `pg_restore --list` | DR implementation |
| OPS-GAP-010 | Self-deploy safety checks depend on health endpoint features | Active incident and error budget queries assume endpoint support | Core implementation |

---

## Appendix A — Systemd Timer Configuration Summary

| Timer | Schedule | Service | Purpose |
|---|---|---|---|
| `guinevere-backup.timer` | `*-*-* 02:00:00 Asia/Jakarta` | `guinevere-backup.service` | Daily full backup |
| `guinevere-selfdeploy.timer` | `*-*-* 03:00:00 Asia/Jakarta` (+5min random delay) | `guinevere-selfdeploy.service` | Nightly self-deploy |
| Internal APScheduler cron | 07:00, 12:00, 17:00, 21:00, 00:00 | guinevere-scheduler | Daily rituals |
| Internal APScheduler cron | Monday 08:00 | guinevere-scheduler | Weekly planning |
| Internal APScheduler cron | 1st of month | guinevere-scheduler | Monthly review |
| Internal APScheduler hourly | Every hour (loops < 3 check) | guinevere-scheduler | Proactive loop check |

## Appendix B — Key File Paths

| Purpose | Path |
|---|---|
| Backup script | `/home/guinevere/scripts/backup.sh` |
| Self-deploy script | `/home/guinevere/scripts/self-deploy.sh` |
| Health check script | `/home/guinevere/scripts/health-check.sh` |
| Secret rotation script | `/home/guinevere/scripts/rotate-secret.sh` |
| Backups directory | `/home/guinevere/data/backups/` |
| Application logs | `/home/guinevere/data/logs/` |
| Evidence directory | `/home/guinevere/core/evidence/` |
| SLO evidence | `evidence/slo/{YYYY-MM}/` |
| FinOps evidence | `evidence/finops/{YYYY-MM}/` |
| Observability evidence | `evidence/observability/{YYYY-MM}-review.md` |
| Incident evidence | `evidence/incidents/{date}-{severity}-{service}/` |
| Weekly evidence | `evidence/weekly/{YYYY}-W{WW}-summary.md` |
| Self-deploy log | `/home/guinevere/data/logs/self-deploy_{date}.log` |
| Secrets (encrypted) | `/home/guinevere/secrets/*.env.sops` |
| SOPS age key | `/etc/sops/age/keys.txt` |
| Docker compose | `/opt/guinevere-docker/docker-compose.yml` |
| Systemd units | `/etc/systemd/system/guinevere-*.service` |

## Appendix C — Docker Quick Reference

```bash
# Container management
docker ps                                          # List running containers
docker logs postgresql --tail 50                   # PostgreSQL logs
docker logs redis --tail 50                        # Redis logs
docker stats --no-stream                           # Resource usage snapshot
docker exec postgresql psql -U postgres -c "..."   # Run SQL
docker exec redis redis-cli -a "$REDIS_PASSWORD" INFO  # Redis info
docker restart postgresql                           # Restart container
docker compose -f /opt/guinevere-docker/docker-compose.yml up -d  # Start all
docker compose -f /opt/guinevere-docker/docker-compose.yml down   # Stop all
```

## Appendix D — Emergency Procedures Quick Reference

| Emergency | First Action | Command |
|---|---|---|
| Core service crash | Check logs, auto-restart handles it | `journalctl -u guinevere-core --since "5 min ago"` |
| PostgreSQL down | Check Docker, restart container | `docker restart postgresql` |
| Disk full (>95%) | Emergency cleanup | `journalctl --vacuum-size=100M; find /tmp -delete` |
| Cost budget exhausted | Freeze non-critical work | Automatic via cost freeze policy |
| Safe-word event | Enter safe mode immediately | Automatic via safe-word detector |
| Security breach (SEV0) | Contain + notify Samm | Automatic via incident response |
| All services down | Full restart sequence | `systemctl restart guinevere-core guinevere-loops guinevere-scheduler guinevere-surveillance guinevere-discord` |

---

**End of Research Report — Guinevere Internal Ops Manual: Daily & Autonomous Operations**
