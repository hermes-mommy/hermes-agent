# Phase 7: Hardening + Monitoring — Detailed Procedure

## Overview

| Property | Value |
|---|---|
| **Duration** | 2-3 days |
| **Risk Level** | LOW |
| **Dependencies** | ALL previous phases (0-6 must pass) (BLOCKING) |
| **Blocks** | Terminal phase — completes the migration |
| **Gate** | All monitoring active. `hermes security` clean. `hermes doctor` clean. Runbook complete. Performance within +10% of baseline |
| **Rollback Time** | < 3 minutes (disable cron + alerts) |

### Goal Statement

Harden the complete Hermes-migrated Guinevere system. Configure automated monitoring (Prometheus metrics, Grafana dashboards, Loki log ingestion, Gotify alerts). Deploy operational cron jobs (daily health check, weekly backup, monthly security scan, daily checkpoint). Run final security audit and performance benchmark. Write comprehensive operations runbook. Verify system runs within +10% of pre-migration performance baseline.

### Pre-Conditions

- [ ] All phases 0-6 complete and verified
- [ ] Hermes gateway running as primary Discord gateway
- [ ] `hermes doctor` clean
- [ ] `hermes security` clean
- [ ] Monitoring stack operational (Prometheus/Grafana/Loki)
- [ ] Existing backup system operational (rclone → S3 + R2)
- [ ] Pre-migration performance baseline recorded

---

## Step-by-Step Procedure

### Step 7.1: Configure Hermes Cron Jobs

**Command:**
```bash
# Daily health check at 06:00 WIB
hermes cron add "daily_health_check" "0 6 * * *" "hermes doctor --report" --timezone "Asia/Jakarta"

# Weekly full backup at 02:00 Sunday WIB
hermes cron add "weekly_backup" "0 2 * * 0" "hermes backup --full --destination idcloudhost" --timezone "Asia/Jakarta"

# Monthly security scan at 03:00 on 1st WIB
hermes cron add "monthly_security_scan" "0 3 1 * *" "hermes security --report" --timezone "Asia/Jakarta"

# Daily checkpoint at 04:00 WIB
hermes cron add "daily_checkpoint" "0 4 * * *" "hermes checkpoints create --label auto-daily-$(date +%Y%m%d)" --timezone "Asia/Jakarta"

# Hourly cost report (daytime only, 08:00-22:00)
hermes cron add "hourly_cost_report" "0 8-22 * * *" "hermes insights cost --since 1h --notify" --timezone "Asia/Jakarta"
```

**Verification:**
```bash
hermes cron list
# Expected: 10 cron jobs (5 rituals from Phase 5 + 5 operational from Phase 7)
```

**Troubleshooting:**
- If cron jobs conflict with existing APScheduler jobs → Phase 7 cron uses Hermes scheduler. Existing `guinevere-scheduler.service` continues running for legacy jobs. No conflict — different schedulers, different jobs.
- If cron job fails silently → check `hermes logs` for cron execution errors.

### Step 7.2: Configure Prometheus Metrics

**Add Hermes scrape job to `monitoring/prometheus/prometheus.yml`:**
```yaml
scrape_configs:
  # ... existing 7 jobs retained ...
  
  - job_name: "hermes"
    metrics_path: "/metrics"
    scrape_interval: 15s
    static_configs:
      - targets: ["host.docker.internal:9191"]
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: "hermes-gateway"
```

**Enable Hermes Prometheus metrics:**
```bash
hermes config set observability.prometheus.enabled true
hermes config set observability.prometheus.metrics_port 9191
```

**Verification:**
```bash
curl -sf http://localhost:9191/metrics | head -20
# Expected: Hermes metrics in Prometheus format
```

### Step 7.3: Configure Loki Log Integration

**Add Hermes log labels to `monitoring/promtail/promtail-config.yml`:**
```yaml
scrape_configs:
  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: systemd-journal
    relabel_configs:
      - source_labels: ["__journal__systemd_unit"]
        regex: "hermes-gateway.service"
        target_label: "service"
        replacement: "hermes"
```

**Configure Hermes JSON logging for Loki:**
```bash
hermes config set observability.logging.level "info"
hermes config set observability.logging.format "json"
hermes config set observability.logging.output "both"
```

### Step 7.4: Configure Prometheus Alert Rules

**Create `monitoring/prometheus/rules/guinevere-hermes-alerts.yml`:**
```yaml
groups:
  - name: guinevere-hermes
    rules:
      - alert: GuinevereHermesGatewayDown
        expr: up{job="hermes"} == 0
        for: 2m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "Hermes gateway is down"
          runbook: "runbooks/hermes-migration-runbook.md"

      - alert: GuinevereHermesSafetyPluginMissing
        expr: guinevere_hermes_safety_plugin_loaded == 0
        for: 1m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "GuinevereSafetyPlugin not loaded — SAFETY COMPROMISED"

      - alert: GuinevereHermesHookFailureRate
        expr: rate(guinevere_hermes_hook_failures_total[15m]) > 0.01
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"

      - alert: GuinevereHermesCompressionFrequent
        expr: rate(guinevere_hermes_compression_total[30m]) > 2
        for: 10m
        labels:
          severity: "warning"
          sev_level: "SEV2"

      - alert: GuinevereHermesBudgetWarning
        expr: guinevere_hermes_cost_monthly_usd > 24
        for: 5m
        labels:
          severity: "info"
          sev_level: "SEV3"

      - alert: GuinevereHermesBackupStale
        expr: time() - guinevere_hermes_last_backup_timestamp > 93600
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
```

### Step 7.5: Performance Baseline Measurement

**Measure pre-migration baseline (record before Phase 0):**
```bash
python scripts/bench_performance.py --mode baseline --output /home/guinevere/backups/pre-migration-bench.json
```

**Measure post-migration performance:**
```bash
python scripts/bench_performance.py --mode compare \
  --baseline /home/guinevere/backups/pre-migration-bench.json \
  --output /home/guinevere/evidence/phase7-bench.json
```

**Performance metrics:**
| Metric | Baseline | Post-Migration | Threshold |
|---|---|---|---|
| Response latency p50 | [baseline] | [post] | ≤ baseline + 10% |
| Response latency p95 | [baseline] | [post] | ≤ baseline + 10% |
| Response latency p99 | [baseline] | [post] | ≤ baseline + 10% |
| Hook overhead (cumulative) | N/A | [post] | ≤ 450ms |
| Memory usage (gateway) | [baseline] | [post] | ≤ cgroup 1G limit |
| LLM cost/day | [baseline] | [post] | ≤ $1.00/day ($30/mo cap) |
| Error rate | [baseline] | [post] | ≤ baseline + 5% |

### Step 7.6: Final Security Audit

**Command:**
```bash
# Full security scan
hermes security --format json > /home/guinevere/evidence/phase7-security.json

# Verify zero HIGH/MODERATE
python -c "
import json
r = json.load(open('/home/guinevere/evidence/phase7-security.json'))
high = [f for f in r.get('findings', []) if f.get('severity') in ('HIGH', 'MODERATE')]
assert len(high) == 0, f'{len(high)} HIGH/MODERATE findings: {high}'
print('PASS: Security audit clean')
"

# Full doctor check
hermes doctor --verbose 2>&1 | tee /home/guinevere/evidence/phase7-doctor.txt
python -c "
with open('/home/guinevere/evidence/phase7-doctor.txt') as f:
    assert 'FAIL' not in f.read(), 'Doctor has FAIL entries'
print('PASS: hermes doctor all green')
"
```

### Step 7.7: Run Complete Verification Suite (T1-T10)

**Command:**
```bash
pytest tests/integration/test_verification.py -v
```

**T1-T10 Verification Tests:**

| Test | Description | Expected |
|---|---|---|
| T1 | Basic conversation (Y4 persona) | 10+ test messages, Y4 dominant tone |
| T2 | Multi-turn memory (cross-session) | 5+ pairs, accurate recall, no DNR leak |
| T3 | MCP tools from chat | 4+ tools, auth matrix enforced |
| T4 | HARD STOP working (< 50ms) | 8+ trigger variants, neutral response |
| T5 | Safe mode working | 6+ distress messages, D2→safe, D3/D4→crisis |
| T6 | Memory recall accurate | 20+ test pairs, 0 hallucination |
| T7 | All 35 slash commands | 35/35 functional |
| T8 | Rituals firing (5x/day) | All 5 on schedule |
| T9 | Cost tracking working | 5+ cost assertions |
| T10 | Surveillance pipeline intact | 10+ pipeline tests |

**Expected output:**
```
tests/integration/test_verification.py ............................... [100%]
100+ passed, 0 failed, 0 skipped
```

### Step 7.8: Deprecation — Delete Old Files (After 48hr Stable)

**WAIT 48 HOURS after Phase 7 completion before deleting deprecated files. Verify system stability first.**

**Deprecated files (safe to delete after 48hr stability):**
```bash
# Files replaced by Hermes — DELETE ONLY after 48hr stable operation
rm -f src/discord/bot.py
rm -f src/discord/conversational_handler.py
rm -f src/discord/commands.py
rm -f src/discord/permissions.py
rm -f src/discord/guild_setup.py
rm -f src/discord/startup.py
rm -f src/discord/_embed_helpers.py
rm -f src/discord/intents.py
rm -f src/hermes/session_adapter.py

# MCP files migrated to native
rm -f src/mcp/manager.py
rm -f src/mcp/tools/brave_search.py
rm -f src/mcp/tools/exa_search.py
rm -f src/mcp/tools/fetch.py
rm -f src/mcp/tools/websearch.py
rm -f src/mcp/tools/filesystem.py
rm -f src/mcp/tools/git_tool.py
rm -f src/mcp/tools/github.py

# Verify git history preserved
git status
```

### Step 7.9: Write Operations Runbook

**Create `runbooks/hermes-migration-runbook.md` (500+ lines) with:**
- System architecture diagram (post-migration)
- All 8 systemd services + Hermes gateway
- Common failure modes and troubleshooting
- Rollback procedures (per-phase + global emergency)
- Monitoring dashboard links (Grafana)
- Alert response flowcharts (SEV0-SEV4)
- Backup/restore procedures
- Cron job schedule
- Cost tracking and budget alerts
- HARD STOP verification checklist
- Contact/escalation procedures

---

## Safety Checkpoint

| # | Check | Command | Expected |
|---|---|---|---|
| P7-T1 | Performance within +10% | `python scripts/bench_performance.py --mode compare` | All metrics ≤ baseline + 10% |
| P7-T2 | `hermes security` clean | `hermes security --format json` | Zero HIGH/MODERATE |
| P7-T3 | `hermes doctor` clean | `hermes doctor --verbose` | All PASS |
| P7-T4 | All monitoring active | `curl localhost:9191/metrics` | Hermes metrics |
| P7-T5 | Cron jobs scheduled | `hermes cron list` | All 10 jobs |
| P7-T6 | Alerts configured | Prometheus rules deployed | SEV0-SEV3 alerts |
| P7-T7 | Backup pipeline test | `hermes backup --dry-run` | No errors |
| P7-T8 | Runbook complete | `wc -l runbooks/hermes-migration-runbook.md` | ≥ 200 lines |
| P7-T9 | T1-T10 verification suite | `pytest tests/integration/test_verification.py -v` | 100+ passed, 0 failed |
| P7-T10 | Deprecated files deleted (after 48hr) | `ls src/discord/bot.py` | File not found |

---

## Config Changes

### Hermes config.yaml additions:
```yaml
observability:
  prometheus:
    enabled: true
    metrics_port: 9191
  logging:
    level: "info"
    format: "json"
    output: "both"
  insights:
    enabled: true
    cost_tracking: true
    latency_tracking: true

cron:
  - name: "daily_health_check"
    schedule: "0 6 * * *"
    command: "hermes doctor --report"
  - name: "weekly_backup"
    schedule: "0 2 * * 0"
    command: "hermes backup --full --destination idcloudhost"
  - name: "monthly_security_scan"
    schedule: "0 3 1 * *"
    command: "hermes security --report"
  - name: "daily_checkpoint"
    schedule: "0 4 * * *"
    command: "hermes checkpoints create --label auto-daily-$(date +%Y%m%d)"
```

### Prometheus: new scrape job + alert rules added
### Loki/Promtail: Hermes labels added
### Grafana: Hermes dashboard JSON created

---

## File Changes

| File | Action | Description |
|---|---|---|
| `runbooks/hermes-migration-runbook.md` | CREATE (~500 lines) | Comprehensive operations runbook |
| `scripts/rollback/phase-0-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-1-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-2-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-3-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-4-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-5-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-6-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/phase-7-rollback.sh` | CREATE | Per-phase rollback scripts |
| `scripts/rollback/global-emergency-rollback.sh` | CREATE (~60 lines) | Universal kill-switch |
| `scripts/backup-hermes.sh` | CREATE | Automated backup script |
| `scripts/health-check.sh` | CREATE | Health probe script |
| `scripts/bench_performance.py` | CREATE (~150 lines) | Performance benchmark |
| `config/hermes/config.yaml` | MODIFY (+30 lines) | Observability + cron sections |
| `monitoring/prometheus/prometheus.yml` | MODIFY | Add Hermes scrape job |
| `monitoring/prometheus/rules/guinevere-hermes-alerts.yml` | CREATE | Alert rules |
| `monitoring/promtail/promtail-config.yml` | MODIFY | Add Hermes labels |
| `monitoring/grafana/dashboards/guinevere-hermes.json` | CREATE | Hermes dashboard |

### Deprecated files (deleted after 48hr stable):
| File | Lines | Replaced By |
|---|---|---|
| `src/discord/bot.py` | 512 | Hermes native gateway |
| `src/discord/conversational_handler.py` | 496 | Hermes message pipeline |
| `src/discord/commands.py` | 278 | Hermes plugins |
| `src/hermes/session_adapter.py` | 302 | Hermes native sessions |
| `src/mcp/manager.py` | 74 | Hermes native MCP client |
| 7 migrated MCP tools | ~1,473 | Hermes native equivalents |

---

## Service Management

| Service | Action |
|---|---|
| Hermes gateway | RESTART (pick up cron + observability config) |
| `guinevere-monitoring` | RELOAD (pick up new Prometheus config + dashboard) |
| All other services | KEEP RUNNING |

---

## Monitoring Verification Commands

```bash
# Prometheus: verify Hermes target
curl -sf http://localhost:9090/api/v1/targets | python -c "
import json, sys
targets = json.load(sys.stdin)['data']['activeTargets']
hermes = [t for t in targets if 'hermes' in str(t.get('labels', {}))]
print(f'Hermes targets: {len(hermes)}')
assert len(hermes) > 0, 'No Hermes targets in Prometheus'
"

# Grafana: verify dashboard loaded
curl -sf http://localhost:3000/api/health
# Expected: OK

# Loki: verify Hermes logs flowing
curl -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="hermes"}' | python -c "
import json, sys
r = json.load(sys.stdin)
results = r.get('data', {}).get('result', [])
print(f'Hermes log entries in Loki: {len(results)}')
"

# Hermes metrics port
curl -sf http://localhost:9191/metrics | grep -E "hermes_|guinevere_"
# Expected: metrics output with Hermes-specific metrics

# Alertmanager
curl -sf http://localhost:9093/-/healthy
# Expected: OK
```

---

## T1-T10 Verification Test Commands

```bash
# Run ALL 10 verification tests (FINAL ACCEPTANCE)
pytest tests/integration/test_verification.py -v

# Individual tests:
pytest tests/integration/test_verification.py::TestT1BasicConversation -v
pytest tests/integration/test_verification.py::TestT2MultiTurnMemory -v
pytest tests/integration/test_verification.py::TestT3MCPTools -v
pytest tests/integration/test_verification.py::TestT4HardStop -v
pytest tests/integration/test_verification.py::TestT5SafeMode -v
pytest tests/integration/test_verification.py::TestT6MemoryAccuracy -v
pytest tests/integration/test_verification.py::TestT7SlashCommands -v
pytest tests/integration/test_verification.py::TestT8Rituals -v
pytest tests/integration/test_verification.py::TestT9CostTracking -v
pytest tests/integration/test_verification.py::TestT10Surveillance -v
```

---

## Security Audit Commands

```bash
# Full security audit
hermes security --format json > evidence/phase7-security.json

# Individual checks:
hermes security check dependencies
hermes security check hooks
hermes security check plugins
hermes security check config
hermes security check permissions

# Audit log review
hermes logs --level error --since "48h" | grep -i "security\|forbidden\|violation"

# PostgreSQL access audit
sudo -u postgres psql -d guinevere -c "
  SELECT usename, query, calls
  FROM pg_stat_statements s
  JOIN pg_user u ON s.userid = u.usesysid
  WHERE u.usename = 'hermes_app'
    AND query !~* '^SELECT'
  ORDER BY calls DESC
  LIMIT 10;
"
# Expected: (0 rows) — only SELECT queries from hermes_app
```

---

## Performance Baseline Measurement Commands

```bash
# Capture pre-migration baseline (run BEFORE Phase 0)
python scripts/bench_performance.py \
  --mode baseline \
  --output /home/guinevere/backups/pre-migration-bench.json

# Measure post-migration performance (run after Phase 7)
python scripts/bench_performance.py \
  --mode compare \
  --baseline /home/guinevere/backups/pre-migration-bench.json

# Performance metrics:
#   response_latency_p50: <baseline + 10%
#   response_latency_p95: <baseline + 10%
#   response_latency_p99: <baseline + 10%
#   hook_overhead_cumulative_ms: < 450
#   memory_usage_gateway_mb: < 1024
#   llm_cost_per_day_usd: ≤ 1.00
#   error_rate_pct: <baseline + 5%
```

---

## Risk Register

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P7-01-001 | Performance exceeds +10% of baseline | 9 MEDIUM | Investigate bottleneck; fix or rollback config |
| R-P7-02-001 | `hermes security` finds HIGH issues | 6 MEDIUM | Fix findings; re-scan until zero HIGH |
| R-P7-03-001 | `hermes doctor` shows non-PASS | 4 LOW | Debug and fix before completion |
| R-P7-04-001 | Monitoring gaps (services not in Prometheus) | 4 LOW | Verify exporter configs; fix scrape targets |
| R-P7-05-001 | Backup pipeline fails | 4 LOW | Debug backup; ensure ADR-032 compliance |

---

## Rollback Procedure

```bash
# === PHASE 7 ROLLBACK (< 3 minutes) ===
hermes cron remove daily_health_check weekly_backup monthly_security_scan daily_checkpoint hourly_cost_report
hermes config set observability.prometheus.enabled false
# Disable Hermes Prometheus scrape job in monitoring/prometheus/prometheus.yml
# Remove Hermes alert rules
# < 3 minutes total
```

---

## Test Commands

```bash
# Cron scheduling tests
pytest tests/hermes/test_hardening.py::TestCron -v

# Logs → Loki integration
pytest tests/hermes/test_hardening.py::TestLogsLoki -v

# Backup pipeline test
pytest tests/hermes/test_hardening.py::TestBackup -v

# Checkpoint automation
pytest tests/hermes/test_hardening.py::TestCheckpoints -v

# Performance benchmark comparison
pytest tests/integration/test_performance_baseline.py::TestComparison -v

# Response latency (p50, p95, p99)
pytest tests/integration/test_performance_baseline.py::TestLatency -v

# Hook latency budget
pytest tests/integration/test_performance_baseline.py::TestHookLatency -v

# T1-T10 verification suite
pytest tests/integration/test_verification.py -v
```

---

## Post-Migration Systemd Service Map

| Service | Status | Notes |
|---|---|---|
| `hermes-gateway.service` | **ENABLED** (active) | Replaces guinevere-discord.service |
| `guinevere-discord.service` | **DISABLED** | Kept on disk for rollback |
| `guinevere-loops.service` | ACTIVE | Unchanged — agent loop daemon |
| `guinevere-scheduler.service` | ACTIVE | Unchanged — APScheduler |
| `guinevere-mcp.service` | ACTIVE | 7 custom MCP tools |
| `guinevere-surveillance.service` | ACTIVE | Unchanged — surveillance consumer |
| `guinevere-monitoring.service` | ACTIVE | Added Hermes scrape job + dashboard |
| `guinevere-obscura.service` | ACTIVE | Unchanged — browser automation |

---

## Gate Criteria (FINAL)

| Criterion | Threshold | Measurement |
|---|---|---|
| All monitoring active | 100% targets | Prometheus targets page |
| `hermes security` clean | 0 HIGH, 0 MODERATE | JSON scan output |
| `hermes doctor` clean | ALL PASS | Doctor verbose output |
| Performance within +10% | All metrics ≤ baseline + 10% | `bench_performance.py --mode compare` |
| T1-T10 verification | 100+ passed, 0 failed | `pytest tests/integration/test_verification.py` |
| Runbook complete | ≥ 500 lines | `wc -l runbooks/hermes-migration-runbook.md` |
| Cron jobs active | All 10 jobs scheduled | `hermes cron list` |
| Alert rules active | SEV0-SEV3 alerts configured | Prometheus rules file deployed |
| Deprecated files deleted (after 48hr) | Clean git status | `ls src/discord/bot.py` → file not found |
| Aizanta confirmed unaffected | Aizanta services healthy | Health check verification |

---

## References

| Document | Relevance |
|---|---|
| `adr/ADR-035-hermes-migration.md` | §Phase 7 — Hardening + Monitoring |
| `adr/ADR-017-monitoring-stack-selection.md` | Prometheus + Grafana + Loki |
| `adr/ADR-025-backup-disaster-recovery-strategy.md` | Backup policy constraints |
| `adr/ADR-032-backup-storage-strategy.md` | idcloudhost S3 + Cloudflare R2 |
| `research-reports/migration-plan/01-dependency-map.md` | §Phase 7 dependencies |
| `research-reports/migration-plan/03-rollback-procedures.md` | §12 — Phase 7 rollback, §13 — Global emergency rollback |
| `research-reports/migration-plan/04-safety-checkpoints.md` | §9 — Phase 7 safety checkpoint |
| `research-reports/migration-plan/06-file-inventory.md` | §Phase 7 — File changes |
| `research-reports/migration-plan/07-test-suite.md` | §11 — Phase 7 test suite, §12 — T1-T10 verification |
| `research-reports/migration-plan/08-service-sequence.md` | §Phase 7 — Service management, Global emergency rollback |
| `research-reports/migration-plan/09-config-migration.md` | §10 — Phase 7 config changes |