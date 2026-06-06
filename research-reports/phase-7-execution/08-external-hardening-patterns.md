# External Hardening Patterns Research — Phase 7 Reference

> **Purpose**: Supplement ADR-035 Phase 7 hardening decisions with external best-practice references for systemd, Prometheus alerting, pytest coverage/rollback, and Hermes CLI security commands.
>
> **Date**: 2026-06-06
> **Status**: Complete
> **Confidence**: High (primary/official docs sourced for all sections)

---

## 1. systemd Hardening Directives

### 1.1 NoNewPrivileges

| Source | Verdict |
|---|---|
| [Big Iron deep-dive](https://www.bigiron.cc/guides/systemd-service-hardening-directives-a-deep-dive) (May 2026) | **"The single best line you can add to any service file."** Prevents privilege escalation via `setuid` binaries, file capabilities, or SELinux `exec` transitions. Default is `false`. |
| [DATAZONE](https://datazone.de/en/aktuelles/linux-systemd-securing-services/) (Apr 2026) | **"The single most important security directive"** — prevents process/children from ever gaining more privileges than at startup. |
| [ArchWiki Sandboxing](https://wiki.archlinux.org/title/Systemd/Sandboxing) | Impact: **High**. Breakage: **Low**. Best used with `RestrictSUIDSGID`. |
| [systemd.exec man page](https://freedesktop.org/software/systemd/man/latest/systemd.exec.html) | Implicitly enabled when `DynamicUser=` is set or when using `systemd.exec` sandboxing flags. |

**Recommendation**: Apply `NoNewPrivileges=true` to **every** production service unit unconditionally. Zero caveats for services that don't need `sudo`/`setuid`.

### 1.2 ProtectSystem

| Setting | Effect | Breakage Risk |
|---|---|---|
| `true` | `/usr`, `/boot`, `/efi` read-only | Medium |
| `full` | Adds `/etc` read-only | Medium |
| `strict` | **Entire filesystem** read-only (except `/dev`, `/proc`, `/sys`) | Very High (must pair with `ReadWritePaths=`) |

**Key caveats from all sources**:

- `ProtectSystem=strict` causes **EROFS** for any write outside declared `ReadWritePaths`. Services that write logs, PID files, databases, or caches **will fail** without explicit writable paths.
- Use `strace -e write` or `journalctl` to audit write paths before enabling `strict` ([systemshardening.com](https://www.systemshardening.com/articles/linux/systemd-unit-hardening/)).
- `DynamicUser=yes` **implies** `ProtectSystem=strict` and `ProtectHome=read-only` automatically ([Kicksecure Wiki](https://www.kicksecure.com/wiki/Systemd)).
- Multi-phase approach recommended: Phase 1 = `ProtectSystem=strict` + `ProtectHome=true` + `PrivateTmp=true`; add `ReadWritePaths` as needed ([DATAZONE](https://datazone.de/en/aktuelles/linux-systemd-securing-services/)).

**Recommendation**: Use `ProtectSystem=strict` with explicit `ReadWritePaths=` for any service that persists data. For log-only services, `ReadWritePaths=/var/log/<service>` suffices.

### 1.3 ProtectHome

| Setting | Effect |
|---|---|
| `yes` / `true` | `/home`, `/root`, `/run/user` appear **inaccessible/empty** |
| `read-only` | Directories visible but read-only |
| `tmpfs` | Directories mounted as empty tmpfs |

**Recommendation**: `ProtectHome=true` for all services that don't need user home access. `read-only` for backup services. Avoid `tmpfs` unless throwaway home is intentional.

### 1.4 MemoryMax / MemoryHigh / Slices

| Directive | Behavior | Source |
|---|---|---|
| `MemoryHigh=384M` | **Soft limit** — kernel throttles (reclaims/swaps) when exceeded. Processes are **slowed down**, not killed. | [Big Iron](https://www.bigiron.cc/guides/systemd-service-hardening-directives-a-deep-dive) |
| `MemoryMax=512M` | **Hard limit** — OOM killer invoked within cgroup. Service killed. | [Red Hat docs](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_monitoring_and_updating_the_kernel/using-systemd-to-manage-resources-used-by-applications) |
| `StartupMemoryHigh=` / `StartupMemoryMax=` | Separate limits for startup/shutdown phases | [systemd.resource-control](https://freedesktop.org/software/systemd/man/latest/systemd.resource-control.html) |

**Slice pattern** (from [iximiuz Labs](https://labs.iximiuz.com/tutorials/controlling-process-resources-with-cgroups)):

```ini
# /etc/systemd/system/guinevere.slice
[Slice]
MemoryMax=2G
MemoryHigh=1.6G
CPUQuota=200%
```

Assign services with `Slice=guinevere.slice` to group resource limits hierarchically.

**Caveats**:
- `MemoryMax` silently kills — symptoms: service logs stop mid-job, `Active: failed`. Check `journalctl -k | grep -i 'killed.*memory'`.
- Suffixes must be `K`, `M`, `G`, `T` (not `KB`, `MB`, `GB` — which silently become `infinity`).
- Use `systemd-cgtop` for live cgroup visibility.
- Recommended pattern: `MemoryHigh=80%` of expected peak, `MemoryMax=120%` of expected peak.

### 1.5 Recommended Hardening Stack (Tiered)

From consolidated multi-source analysis:

| Tier | Directives | Impact | Breakage |
|---|---|---|---|
| 1 (always) | `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`, `RestrictSUIDSGID=true`, `LockPersonality=true`, `RestrictRealtime=true` | High | Low-Medium |
| 2 (selective) | `PrivateDevices=true`, `ProtectKernelTunables=true`, `SystemCallArchitectures=native`, `CapabilityBoundingSet=`, `MemoryDenyWriteExecute=false` (no JIT) | Medium | Medium |
| 3 (resources) | `MemoryMax=`, `MemoryHigh=`, `CPUQuota=`, `TasksMax=`, `IOWeight=` | Medium | Low |

**Source**: [DATAZONE incremental approach](https://datazone.de/en/aktuelles/linux-systemd-securing-services/), [systemshardening.com](https://www.systemshardening.com/articles/linux/systemd-unit-hardening/), [devopsil.com](https://devopsil.com/articles/2026-03-29-linux-systemd-service-hardening)

---

## 2. Prometheus Alert Rule Conventions

### 2.1 Canonical References

| Source | Key Principles |
|---|---|
| [Prometheus Alerting Best Practices](https://prometheus.io/docs/practices/alerting/) | Alert on **symptoms** (end-user pain), not causes. Keep alerts minimal. Only page on latency at one stack level. |
| [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) | Multi-window, multi-burn-rate approach. Use short window = 1/12 of long window for fast reset. |
| [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) (official) | `for` clause required for pending → firing transition. `keep_firing_for` for hysteresis. |
| [Grafana Alerting Best Practices](https://grafana.com/docs/grafana/latest/alerting/guides/best-practices/) | Use multi-dimensional rules, set pending periods, graduate symptom alerts into SLOs. |

### 2.2 Service Down Alert

**Canonical pattern** ([official docs](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)):

```yaml
- alert: ServiceDown
  expr: up == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.job }} is down"
    description: "Instance {{ $labels.instance }} has been down for more than 2 minutes"
    runbook_url: "https://runbooks.internal/service-down"
    dashboard_url: "https://grafana.internal/d/service-overview"
```

**Variant with absence detection** ([Last9](https://last9.io/blog/prometheus-alerting-examples/)):

```yaml
- alert: ServiceDown
  expr: up == 0 or absent(up{job="guinevere"})
  for: 1m
  labels:
    severity: critical
```

### 2.3 Histogram P95/P99 Latency Alerts

**Canonical pattern** ([DevOpsil](https://devopsil.com/articles/2026-03-29-prometheus-alerting-rules-guide), [Last9](https://last9.io/blog/histogram-buckets-in-prometheus/)):

```yaml
- alert: HighP95Latency
  expr: |
    histogram_quantile(0.95,
      sum by (le, service) (
        rate(http_request_duration_seconds_bucket[5m])
      )
    ) > 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High latency on {{ $labels.service }}"
    description: "P95 latency above 500ms for {{ $labels.service }} over 10 minutes"

- alert: CriticalP99Latency
  expr: |
    histogram_quantile(0.99,
      sum by (le, service) (
        rate(http_request_duration_seconds_bucket[5m])
      )
    ) > 1.0
  for: 5m
  labels:
    severity: critical
```

**Key rules**:
- Always use histograms (not summaries) for percentile alerting — summaries can't aggregate across instances.
- Recommended bucket config for REST APIs: `[0.01, 0.05, 0.1, 0.5, 1, 5, 10]`.
- Warning fires slower (10m) at higher threshold, critical fires faster (5m) — intentional layering.

### 2.4 Spike / Anomaly Detection Alerts

**Z-score method** ([Prometheus anomaly detection guide](https://omarghader.github.io/prometheus-anomaly-detection-z-score-in-promql/)):

```yaml
- alert: HighRequestAnomaly
  expr: |
    (
      rate(http_requests_total[1m])
      -
      avg_over_time(rate(http_requests_total[1m])[15m:])
    )
    /
    stddev_over_time(rate(http_requests_total[1m])[15m:])
    > 3
  for: 2m
  labels:
    severity: warning
```

**Ratio-to-baseline method** ([BestHub recording rules guide](https://www.besthub.dev/articles/how-prometheus-recording-rules-can-reduce-alert-noise-by-70-fce150b0ac7e)):

```yaml
# Recording rules for baseline
- record: job:http_error_rate:baseline1h
  expr: avg_over_time(
    (sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
     /
     sum by (job) (rate(http_requests_total[5m])))[1h:]
  )

- alert: ServiceErrorRateSpike
  expr: |
    (
      sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
      /
      sum by (job) (rate(http_requests_total[5m]))
    )
    / on(job) job:http_error_rate:baseline1h
    > 3
  for: 5m
  labels:
    severity: warning
```

### 2.5 SLO / Budget / Cost Threshold Alerts

**Multi-window burn rate** ([Google SRE Workbook](https://sre.google/workbook/alerting-on-slos/), [DevOps Daily](https://devops-daily.com/posts/slos-slis-error-budgets-practical-guide)):

```yaml
# Fast burn: 14.4x over 1h AND 6x over 6h → page
- alert: HighErrorBudgetBurn
  expr: |
    (
      1 - (sum(rate(http_requests_total{status!~"5.."}[1h]))
           / sum(rate(http_requests_total[1h])))
    ) / (1 - 0.999) > 14.4
    and
    (
      1 - (sum(rate(http_requests_total{status!~"5.."}[6h]))
           / sum(rate(http_requests_total[6h])))
    ) / (1 - 0.999) > 6
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Budget burning at {{ $value | humanize }}x sustainable rate"

# Slow burn: 3x over 1d AND 1x over 3d → ticket
- alert: SlowErrorBudgetBurn
  expr: |
    (
      1 - (sum(rate(http_requests_total{status!~"5.."}[1d]))
           / sum(rate(http_requests_total[1d])))
    ) / (1 - 0.999) > 3
    and
    (
      1 - (sum(rate(http_requests_total{status!~"5.."}[3d]))
           / sum(rate(http_requests_total[3d])))
    ) / (1 - 0.999) > 1
  for: 30m
  labels:
    severity: warning
```

**Cost threshold alert** (synthesized from pattern):

```yaml
- alert: MonthlyCostThreshold
  expr: |
    sum by (service) (
      increase(llm_cost_dollars_total[24h])
    ) > 50
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Cost spike on {{ $labels.service }}"
    description: "{{ $labels.service }} spent >$50 in last 24h"
```

### 2.6 Conventions Summary for Phase 7

| Alert Type | `for` Duration | Severity | Annotation Requirements |
|---|---|---|---|
| Service Down | ≥1m | critical | runbook_url + dashboard_url |
| P95 Latency | ≥10m | warning | summary + description |
| P99 Latency | ≥5m | critical | summary + description |
| Error Rate Spike | ≥5m | warning/critical | ratio baseline or Z-score |
| Budget Burn (fast) | ≥5m | critical | burn rate, time-to-exhaustion |
| Budget Burn (slow) | ≥30m | warning | expected exhaustion date |
| Cost Spike | ≥1h | warning | dollar amount + service label |

---

## 3. pytest Coverage and Rollback Test Patterns

### 3.1 `--cov-fail-under` Patterns

**Source**: [pytest-cov v7.1.0 docs](https://pytest-cov.readthedocs.io/en/latest/config.html)

```bash
# Enforce minimum coverage (CI usage)
pytest --cov=src --cov-report=xml --cov-fail-under=80 -n auto

# Terminal missing report for quick feedback
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Branch coverage
pytest --cov=src --cov-branch --cov-fail-under=75
```

**Configuration in pyproject.toml** ([source](https://tech-insider.org/pytest-tutorial-python-testing-ci-cd-2026/)):

```toml
[tool.coverage.run]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 80
```

**CI integration pattern**:

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-fail-under=80 -n auto

- name: Upload coverage report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage.xml
```

**Key caveat**: `fail_under = 80` is a common practical minimum, but should be calibrated to project baseline. Start low (e.g., current coverage - 5%) and ratchet up per PR.

### 3.2 Rollback Test Patterns (Without Destructive Git)

**Pattern 1: Git-backed sandbox rollback (recommended for agent loops)**

From [DEV Community: Sandboxed Ralph Wiggum Loop](https://dev.to/kowshik_jallipalli_a7e0a5/the-sandboxed-ralph-wiggum-loop-securely-letting-agents-fix-code-until-tests-pass-30h5):

```python
# Pseudo-pattern for test rollback in CI
import subprocess, tempfile, shutil, os

# 1. Snapshot before test mutation
with tempfile.TemporaryDirectory() as sandbox:
    shutil.copytree(ORIGINAL_REPO, sandbox, symlinks=True)
    os.chdir(sandbox)

    # 2. Apply candidate changes
    # ... apply patches ...

    # 3. Run tests
    result = subprocess.run(["pytest", "--cov=src", "--cov-fail-under=80"],
                           capture_output=True, text=True)

    # 4. On failure — sandbox auto-cleaned by TemporaryDirectory
    # No destructive git operations needed
```

**Pattern 2: pytest-delta (smart test selection via content hashing)**

From [CemAlpturk/pytest-delta](https://github.com/CemAlpturk/pytest-delta):

```bash
# First run: builds dependency graph
pytest --delta

# Subsequent runs: only affected tests by SHA-256 content hash
pytest --delta

# Read-only (no snapshot update)
pytest --delta-readonly
```

**Key features**: No git history dependency, works with uncommitted changes, AST-based import tracking, transitive closure.

**Pattern 3: pytest-difftest (block-level change detection)**

From [PaulM5406/pytest-difftest](https://github.com/PaulM5406/pytest-difftest):

```bash
# Build baseline (first run)
pytest --diff-baseline

# Incremental: only tests touching changed code blocks
pytest --diff
```

Uses coverage data to map tests to code blocks, Rust-powered AST for function/class granularity.

### 3.3 Rollback Strategies for Agent Workflows

| Strategy | Destructive? | Git Required? | Use Case |
|---|---|---|---|
| `tempfile.TemporaryDirectory` | No (auto-cleanup) | No | CI sandbox, agent test loops |
| `pytest-delta` | No (read-only option) | No | Fast local re-runs |
| `git stash` / `git checkout` | Yes (needs reflog safety) | Yes | Interactive rollback |
| `git worktree` isolate | No (separate tree) | Yes | Parallel agent sessions |
| `h5i` intent-based rollback | Yes (with cascade warnings) | Yes | Complex multi-commit undo |

**Pattern from containerized recovery testing** ([arturdmt-alt/QA_Recovery_Testing](https://github.com/arturdmt-alt/QA_Recovery_Testing)):

```python
# Transaction rollback validation pattern
async def test_transaction_rollback_on_error():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Start transaction
        resp = await client.post("/transaction/start")
        tx_id = resp.json()["tx_id"]

        # Inject failure
        with pytest.raises(ConnectionError):
            await client.post("/transaction/commit", json={"tx_id": tx_id, "force_fail": True})

        # Verify rollback
        state = await client.get(f"/transaction/{tx_id}/state")
        assert state.json()["status"] == "rolled_back"
```

### 3.4 Recommendations for Phase 7

1. **Use `--cov-fail-under=80`** as default in CI, with `--cov-branch` for deeper coverage.
2. **Use `pytest-delta` or `pytest-difftest`** for fast change-selection in agent-in-the-loop scenarios — avoids full test suite re-runs.
3. **For rollback simulation**: use `tempfile.TemporaryDirectory` + `shutil.copytree` sandbox — zero destructive operations, auto-cleanup, works on all platforms.
4. **For Hermes-style checkpoints**: if implementing agent checkpoint/rollback, use a **shadow git store** (separate bare repo) — never operate on the real project `.git` directly.

---

## 4. Hermes CLI Security, Backup & Checkpoint Commands

### 4.1 Availability Status

**Hermes Agent documentation is publicly available** at [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/docs/). All security, backup, and checkpoint commands are documented. Repository: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (MIT License).

### 4.2 Backup Commands

```bash
# Full backup of ~/.hermes to zip
hermes backup                          # ~/hermes-backup-*.zip
hermes backup -o /tmp/hermes.zip       # Specific path
hermes backup --quick                  # Quick state-only snapshot
hermes backup --quick --label "pre-upgrade"  # Snapshot with label

# Restore
hermes import /path/to/backup.zip
```

**Source**: [CLI Commands Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)

### 4.3 Checkpoint & Rollback System

**Opt-in** (default: `disabled` in v2):

```bash
# Per session
hermes chat --checkpoints

# Global config (~/.hermes/config.yaml)
checkpoints:
  enabled: true
  max_snapshots: 20
  max_total_size_mb: 500
  max_file_size_mb: 10
  auto_prune: true
  retention_days: 7
  delete_orphans: true
  min_interval_hours: 24
```

**In-session slash commands**:

| Command | Action |
|---|---|
| `/rollback` | List checkpoints with change stats |
| `/rollback N` | Restore to checkpoint N |
| `/rollback diff N` | Preview diff since checkpoint N |
| `/rollback N <file>` | Single-file restore |

**CLI management**:

```bash
hermes checkpoints              # Show size, count, per-project breakdown
hermes checkpoints prune        # Force sweep + GC
hermes checkpoints clear        # Nuke entire store
hermes checkpoints clear-legacy # Remove v1 migration archives
```

**Architecture**: Single shared bare git repo at `~/.hermes/checkpoints/store/` — content-addressable deduplication across projects. Per-project refs (`refs/hermes/<hash>`). Never touches the real project `.git`.

**Source**: [Checkpoints & Rollback](https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback)

### 4.4 Security Architecture

**Multi-layer model** (7 layers documented):

| Layer | Feature |
|---|---|
| 1 | User authorization (allowlists, DM pairing) |
| 2 | Dangerous command approval (manual / smart / off) |
| 3 | Container isolation (Docker with `--cap-drop ALL`, no-new-privileges) |
| 4 | MCP credential filtering |
| 5 | Context file injection scanning (prompt injection detection) |
| 6 | Cross-session isolation |
| 7 | Input sanitization |

**Approval modes**:

| Mode | Behavior |
|---|---|
| `manual` (default) | Always prompt on dangerous commands |
| `smart` | Auxiliary LLM risk assessment; auto-approve low-risk, escalate uncertain |
| `off` | Disable all prompts (`--yolo` mode) |

**Hardline blocklist** (below `--yolo`, no override): `rm -rf /`, fork bombs, `mkfs.*` on mounted root, `dd if=/dev/zero of=/dev/sd*`, pipe untrusted URLs to `sh` at rootfs level.

**Docker security flags** (every container):
```
--cap-drop ALL
--cap-add DAC_OVERRIDE CHOWN FOWNER
--security-opt no-new-privileges
--pids-limit 256
--tmpfs /tmp:rw,nosuid,size=512m
--tmpfs /var/tmp:rw,noexec,nosuid,size=256m
--tmpfs /run:rw,noexec,nosuid,size=64m
```

**Source**: [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security), [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)

### 4.5 Key Takeaways for Phase 7

- Hermes' checkpoint system (shadow git store, never touches real `.git`) is a **proven reference implementation** for agent rollback.
- The tiered approval system (manual → smart → off) with a hardline blocklist floor is a **good pattern for command safety**.
- Container security flags (`--cap-drop ALL`, `no-new-privileges`, `tmpfs` mounts) align with **systemd hardening tier 1-2 recommendations**.
- Lazy dependency install with scoped venv, PyPI-by-name-only, allowlist control is a **good pattern for supply-chain safety**.

---

## 5. Phase 7 Planner Recommendations

### 5.1 systemd Unit Hardening

1. **Apply Tier 1 to ALL services**: `NoNewPrivileges=true`, `ProtectSystem=strict` (with explicit `ReadWritePaths=`), `ProtectHome=true`, `PrivateTmp=true`, `RestrictSUIDSGID=true`, `LockPersonality=true`.
2. **Use a `guinevere.slice`** for hierarchical resource control with `MemoryMax=2G`, `MemoryHigh=1.6G`, `CPUQuota=200%`.
3. **Add `ReadWritePaths=` for each service's writable paths** — audit with `strace -e write` first.
4. **Use `MemoryHigh` (soft) + `MemoryMax` (hard)** pairing — never `MemoryMax` alone.

### 5.2 Prometheus Alerting

1. **Use multi-dimensional rules** — one rule per alert type (not per-instance), grouped by `service` label.
2. **Minimum `for` durations**: 2m for service-down, 5-10m for latency, 5m for error spikes.
3. **Include `runbook_url` and `dashboard_url`** in every alert annotation.
4. **Implement multi-window burn rate alerts** (14.4x/6x for critical, 3x/1x for warning) adapted to available metrics.
5. **Use recording rules** for baseline computation to avoid expensive sub-queries in alert rules.

### 5.3 Coverage & Test Rollback

1. **Set `--cov-fail-under=80`** in CI with `--cov-branch`.
2. **Use `tempfile.TemporaryDirectory` sandbox** for agent rollback simulation — no destructive git ops.
3. **Adopt Hermes' shadow-git-store pattern** if implementing checkpoints: separate bare repo, per-project refs, size-bounded.

### 5.4 Hermes Security Patterns to Adopt

1. **Shadow git store for rollback** — proven deduplication across projects, non-destructive to real `.git`.
2. **Dangerous command approval with hardline blocklist** — if implementing command gates in Guinevere.
3. **Container hardening flags** — `--cap-drop ALL`, `no-new-privileges`, tmpfs isolation match systemd recommendations.

---

## Source Index

| Topic | URL | Confidence |
|---|---|---|
| systemd.exec man page | https://freedesktop.org/software/systemd/man/latest/systemd.exec.html | **Primary** |
| systemd.resource-control | https://freedesktop.org/software/systemd/man/latest/systemd.resource-control.html | **Primary** |
| systemd.slice | https://www.freedesktop.org/software/systemd/man/devel/systemd.slice.html | **Primary** |
| ArchWiki systemd sandboxing | https://wiki.archlinux.org/title/Systemd/Sandboxing | High |
| Big Iron systemd hardening | https://www.bigiron.cc/guides/systemd-service-hardening-directives-a-deep-dive | High |
| DATAZONE systemd hardening | https://datazone.de/en/aktuelles/linux-systemd-securing-services/ | High |
| Prometheus alerting practices | https://prometheus.io/docs/practices/alerting/ | **Primary** |
| Prometheus alerting rules | https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/ | **Primary** |
| Google SRE alerting on SLOs | https://sre.google/workbook/alerting-on-slos/ | High |
| Grafana alerting best practices | https://grafana.com/docs/grafana/latest/alerting/guides/best-practices/ | **Primary** |
| pytest-cov v7.1.0 docs | https://pytest-cov.readthedocs.io/en/latest/config.html | **Primary** |
| pytest-delta | https://github.com/CemAlpturk/pytest-delta | High (OSS) |
| pytest-difftest | https://github.com/PaulM5406/pytest-difftest | High (OSS) |
| Sandboxed agent loop pattern | https://dev.to/kowshik_jallipalli_a7e0a5/the-sandboxed-ralph-wiggum-loop-securely-letting-agents-fix-code-until-tests-pass-30h5 | Medium (blog) |
| Hermes CLI reference | https://hermes-agent.nousresearch.com/docs/reference/cli-commands | **Primary** |
| Hermes security | https://hermes-agent.nousresearch.com/docs/user-guide/security | **Primary** |
| Hermes checkpoints & rollback | https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback | **Primary** |
| Hermes GitHub (MIT) | https://github.com/NousResearch/hermes-agent | **Primary** |
