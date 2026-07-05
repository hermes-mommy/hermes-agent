# P23 Research — Official Docs + Tooling

> Status: RESEARCH
> Date: 2026-06-25
> Scope: P23 "Embodied Operations / Personal OS Action Layer" — official documentation and local tooling reuse map
> Retrieval date for all citations below: 2026-06-25

---

## 1. Objective

This document provides the official citation index and local tooling reuse map for P23. For each tool in the P23 ground-truth stack, it records:

- Official documentation URL (verified)
- Pinning/version recommendation
- P23 use case
- Key API / CLI surface
- License and cost
- Whether the tool has an official, programmatic API

It also maps which existing local MCP/Hermes executors can be reused versus which surfaces P23 must build from scratch.

---

## 2. Sources Consulted

- Web searches against official documentation domains
- Direct verification of documentation URLs (Brave Search / Firecrawl)
- Local code search of `src/mcp/`, `src/hermes_plugins/`, and `plugins/`
- Project ADRs and P23 policy research files already present in `docs/setup-evidence/P23/research/`

All documentation links were retrieved and verified on 2026-06-25.

---

## 3. Tool Citation Table

| Tool | Official Doc URL | Version (pin target) | P23 Use | Key API / CLI Surface | License / Cost | Verified? | Retrieval Date |
|---|---|---|---|---|---|---|---|
| Playwright (Python) | https://playwright.dev/python/docs/intro | 1.60.0 (latest stable, May 2026) | Browser automation, agentic web actions, DOM/snapshot extraction | `sync_api`, `async_api`, `BrowserContext`, `Page`, `Locator`, `expect`, CDP attach, `playwright install` | Apache-2.0, free | Yes | 2026-06-25 |
| Playwright MCP | https://playwright.dev/mcp/ | MCP server bundled with Playwright | Optional structured browser control via MCP | `browser_navigate`, `browser_click`, `browser_fill`, `browser_type`, `browser_scroll`, `browser_snapshot` | Apache-2.0, free | Yes | 2026-06-25 |
| GitHub CLI `gh` | https://cli.github.com/manual/ | 2.93.0+ (immutable releases) | PR/issue/repo management, automation, CI/CD triggers | `gh auth`, `gh repo`, `gh pr`, `gh issue`, `gh run`, `gh workflow`, `gh api` (REST/GraphQL passthrough) | MIT, free | Yes | 2026-06-25 |
| GitHub REST API | https://docs.github.com/en/rest | 2022-11-28 (latest stable) | Programmatic repository, issue, PR, workflow, code search operations | `/repos`, `/issues`, `/pulls`, `/actions/runs`, `/search/code`, OAuth/PAT auth | Proprietary (GitHub Terms), free tier + paid quotas | Yes | 2026-06-25 |
| GitHub GraphQL API | https://docs.github.com/en/graphql | v4 (schema-driven) | Precise data fetch, bulk issue/PR metadata, project automation | `api.github.com/graphql`, queries/mutations, Node IDs, rate-limit cost model | Proprietary, free tier + paid quotas | Yes | 2026-06-25 |
| PowerShell | https://learn.microsoft.com/en-us/powershell/ | 7.6.3 LTS (current LTS as of June 2026) | Windows automation, registry, service control, cross-platform scripting | Cmdlets, `Invoke-Command`, `Start-Process`, modules, `Get-`, `Set-`, `New-` verbs | MIT (PowerShell 7.x), free | Yes | 2026-06-25 |
| Windows Task Scheduler | https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page | Windows 10/11 / Server 2016+ | Periodic job scheduling, wake/lock hooks | Task Scheduler 2.0 COM API, XML task definitions, `schtasks.exe` | Proprietary (Windows), cost included with Windows license | Yes | 2026-06-25 |
| OpenSSH (ssh/scp) | https://man.openbsd.org/ssh.1 and https://man.openbsd.org/scp.1 | 10.2 / 10.3 (latest stable) | Secure remote shell, file transfer, tunneling to VPS | `ssh`, `scp`, `sftp`, `ssh_config`, `sshd_config`, key-based auth, `ProxyJump` | OpenBSD-style (BSD/MIT), free | Yes | 2026-06-25 |
| systemd | https://www.freedesktop.org/software/systemd/man/latest/systemctl.html | 257 (stable); 258-rc2, 260 released | Service lifecycle, unit files, timers, journal | `systemctl`, `.service`, `.timer`, `.socket`, `journalctl`, `systemd-analyze` | LGPL-2.1+, free | Yes | 2026-06-25 |
| PostgreSQL pg_dump/restore | https://www.postgresql.org/docs/current/app-pgdump.html / app-pgrestore.html | 18.x (current), 19 beta (GA Sept 2026) | Backup, restore, migration, archival | `pg_dump`, `pg_restore`, `pg_dumpall`, custom/directory/archive formats, parallel restore | PostgreSQL License (MIT-like), free | Yes | 2026-06-25 |
| rclone | https://rclone.org/docs/ / commands | 1.74.3 (latest stable, June 2026) | Cloud/sync backup, S3/SFTP/OneDrive/Drive remotes | `rclone sync`, `rclone copy`, `rclone mount`, config file, filters | MIT, free | Yes | 2026-06-25 |
| AWS CLI | https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html | 2.27.41+ (latest) | S3 operations, RDS/ECR interactions when AWS is used | `aws s3`, `aws ec2`, `aws configure`, SSO/Credential profiles | Apache-2.0, free (AWS usage billed separately) | Yes | 2026-06-25 |
| Redis | https://redis.io/docs/latest/ | 8.8 (latest); note license change from 7.4+ | Durable queue, job processing, pub/sub, session cache | `BRPOPLPUSH`/`BLMOVE`, `LPUSH`/`RPOP`, `KEYS`/`SCAN`, `HSET`/`HGETALL`, `EXPIRE`, streams | Redis 7.2 and prior: BSD-3-Clause; 7.4+ RSALv2/SSPLv1; 8.0+ tri-license (RSALv2/SSPLv1/AGPLv3) | Yes | 2026-06-25 |
| Android ADB | https://developer.android.com/tools/adb | Platform Tools 36.x (latest) | Remote Android device control, app/intent testing | `adb shell`, `adb shell am start`, `adb shell input`, `adb push`/`pull`, `logcat` | Apache-2.0 (ADB), free | Yes | 2026-06-25 |
| Android Intent (am) | https://developer.android.com/guide/components/intents-common / https://developer.android.com/tools/adb | API level 36 / Android 16 | Triggering app actions, deep links, automation | `am start -a ACTION -d URI -n COMPONENT`, `am broadcast`, extras with `-e` | Apache-2.0 (AOSP), free | Yes | 2026-06-25 |
| OpenTelemetry | https://opentelemetry.io/docs/ | 1.x SDK / Collector 0.x (latest) | Instrumentation, traces, metrics, logs standardization | OTel API, SDK, Collector processors/exporters, OTLP | Apache-2.0, free | Yes | 2026-06-25 |
| Prometheus | https://prometheus.io/docs/ | 3.12+ / LTS 3.5.x | Metrics scraping, storage, alerting | PromQL, `scrape_configs`, `/metrics`, `prometheus.yml`, alert rules | Apache-2.0, free | Yes | 2026-06-25 |
| Grafana | https://grafana.com/docs/grafana/latest/ | 13.x (latest) | Metrics/visualization dashboards | Dashboard JSON, data sources (Prometheus, Postgres), alerting, API keys | AGPL-3.0 (Grafana OSS), paid Enterprise available | Yes | 2026-06-25 |

### 3.1 Detailed Tool-by-Tool Notes

#### 3.1.1 Playwright

- **Official URL**: https://playwright.dev/python/docs/intro
- **Verified**: Page resolves and describes Python installation, sync/async APIs, and supported browsers.
- **Version to pin**: `1.60.0` (latest stable on PyPI as of 2026-06-25).
- **P23 use**: Browser automation for embodied operations — agent-driven navigation, form filling, clicking, and DOM snapshot extraction. Replaces or augments the existing `obscura_cdp.py` MCP tool.
- **Key API surface**: `sync_playwright()`, `BrowserType.launch()`, `Browser.new_context()`, `Page.goto()`, `Page.fill()`, `Page.click()`, `Locator`, `expect`, `BrowserContext.route()`, `Page.screenshot()`.
- **License / cost**: Apache-2.0, free. Browser binaries are downloaded automatically.

#### 3.1.2 GitHub CLI (`gh`)

- **Official URL**: https://cli.github.com/manual/
- **Verified**: The manual covers authentication, repositories, issues, PRs, runs, workflows, and the `gh api` passthrough.
- **Version to pin**: `2.93.0` or later (immutable releases starting at v2.93.0).
- **P23 use**: Repository operations, issue/PR automation, CI trigger, and as a fallback for GitHub REST/GraphQL calls.
- **Key CLI surface**: `gh auth login`, `gh repo clone`, `gh pr create`, `gh issue create`, `gh run watch`, `gh workflow run`, `gh api graphql ...`.
- **License / cost**: MIT, free. Subject to GitHub API rate limits.

#### 3.1.3 GitHub REST API

- **Official URL**: https://docs.github.com/en/rest
- **Verified**: Docs enumerate all REST endpoints, authentication, and rate limits.
- **Version to pin**: `2022-11-28` (current REST API version header).
- **P23 use**: Programmatic GitHub operations where `gh` CLI is not ideal (bulk, parallel, precise error handling).
- **Key API surface**: `GET /repos/{owner}/{repo}`, `POST /repos/{owner}/{repo}/issues`, `GET /search/code`, `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun`, `Authorization: Bearer <token>`.
- **License / cost**: Proprietary GitHub API terms; free within rate limits, paid for higher limits/Enterprise.

#### 3.1.4 GitHub GraphQL API

- **Official URL**: https://docs.github.com/en/graphql
- **Verified**: Docs include schema introspection, query/mutation examples, and rate-limit cost model.
- **Version to pin**: v4 (no separate version header; schema evolves).
- **P23 use**: Bulk issue/PR metadata retrieval, project automation, precise field selection to reduce API calls.
- **Key API surface**: `POST https://api.github.com/graphql`, `query`, `mutation`, `viewer`, `repository`, `issues`, `pullRequests`, `projectV2`.
- **License / cost**: Proprietary GitHub API terms; free within rate limits.

#### 3.1.5 PowerShell

- **Official URL**: https://learn.microsoft.com/en-us/powershell/
- **Verified**: Microsoft Learn landing page links to installation, scripting, and reference docs.
- **Version to pin**: `7.6.3` LTS (current LTS as of June 2026).
- **P23 use**: Windows-side automation, Task Scheduler integration, service/registry inspection, cross-platform scripting where needed.
- **Key API surface**: Cmdlets (`Get-Process`, `Start-Process`, `Invoke-RestMethod`), modules (`Microsoft.PowerShell.Management`), remoting with `Invoke-Command`, `-Credential`.
- **License / cost**: MIT (PowerShell 7.x), free.

#### 3.1.6 Windows Task Scheduler

- **Official URL**: https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page
- **Verified**: Page covers Task Scheduler 1.0/2.0, triggers, actions, COM API, and XML schema.
- **Version to pin**: Task Scheduler 2.0 (Windows Vista/Server 2008+).
- **P23 use**: Schedule recurring P23 tasks on Windows hosts, wake-from-sleep hooks, lock-screen triggers.
- **Key API surface**: COM (`ITaskService`, `ITaskDefinition`), `schtasks.exe`, XML task definitions, triggers, actions, principals, settings.
- **License / cost**: Proprietary Windows component; included with Windows license.

#### 3.1.7 OpenSSH (ssh / scp)

- **Official URL**: https://man.openbsd.org/ssh.1 and https://man.openbsd.org/scp.1
- **Verified**: OpenBSD man pages for `ssh`, `scp`, `ssh_config`, and `sshd_config` resolve.
- **Version to pin**: `10.2` or `10.3` (latest stable releases).
- **P23 use**: Secure remote command execution on the VPS, file transfer, tunneling, `ssh -J` jump hosts.
- **Key CLI surface**: `ssh user@host command`, `scp file host:path`, `sftp`, `ssh -L`/`-R` port forwarding, `ProxyJump`, `~/.ssh/config`.
- **License / cost**: OpenBSD-style (BSD/MIT), free.

#### 3.1.8 systemd

- **Official URL**: https://www.freedesktop.org/software/systemd/man/latest/systemctl.html
- **Verified**: Freedesktop man pages for `systemctl`, `systemd.unit`, and `systemd.service` resolve.
- **Version to pin**: `257` (stable in major distros); test against `258`/`260` for future compatibility.
- **P23 use**: Manage Guinevere services on the Ubuntu 24.04 VPS (life_kernel, Hermes, Postgres, Redis), timers for backups/jobs.
- **Key CLI surface**: `systemctl start/stop/restart/status`, `systemctl enable/disable`, `systemctl daemon-reload`, `systemd-analyze`, `journalctl -u service`.
- **License / cost**: LGPL-2.1+, free.

#### 3.1.9 PostgreSQL (pg_dump / pg_restore)

- **Official URL**: https://www.postgresql.org/docs/current/app-pgdump.html and https://www.postgresql.org/docs/current/app-pgrestore.html
- **Verified**: Official docs detail formats, options, parallelism, and security warnings.
- **Version to pin**: Match server version; server is currently 18.x, with 19 GA in Sept 2026. Pin client tools to the same major.
- **P23 use**: Database backup/restore, archival to S3, migration, point-in-time recovery preparation.
- **Key CLI surface**: `pg_dump -Fc`, `pg_dump -Fd`, `pg_restore --list`, `pg_restore -d dbname`, `pg_dumpall --globals-only`.
- **License / cost**: PostgreSQL License (MIT-like), free.

#### 3.1.10 rclone

- **Official URL**: https://rclone.org/docs/ and https://rclone.org/commands/
- **Verified**: Docs cover configuration, remotes, sync/copy/mount, and command reference.
- **Version to pin**: `1.74.3` (latest stable as of June 2026).
- **P23 use**: Sync backups to cloud storage (S3, Backblaze B2, OneDrive, Google Drive), mount remotes, bandwidth-throttled transfers.
- **Key CLI surface**: `rclone config`, `rclone sync`, `rclone copy`, `rclone mount`, `rclone ls`, filters (`--include`, `--exclude`), `--transfers`, `--checkers`.
- **License / cost**: MIT, free.

#### 3.1.11 AWS CLI

- **Official URL**: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- **Verified**: AWS docs confirm v2 install, version checking, and configuration.
- **Version to pin**: `2.27.41` or later.
- **P23 use**: S3 object operations (when rclone is not used), ECR login, RDS snapshot interactions, AWS resource inspection.
- **Key CLI surface**: `aws configure`, `aws s3 cp/sync/ls`, `aws s3api`, `aws ecr get-login-password`, `aws rds`.
- **License / cost**: Apache-2.0, free; AWS resource usage billed separately.

#### 3.1.12 Redis

- **Official URL**: https://redis.io/docs/latest/commands/brpoplpush/ (queue pattern) and https://redis.io/docs/latest/develop/use-cases/job-queue/
- **Verified**: Official Redis docs cover list commands, queue patterns, and `BRPOPLPUSH`/`BLMOVE`.
- **Version to pin**: `7.2.x` (BSD-3-Clause, last fully permissive) or evaluate `8.8` (license change implications).
- **P23 use**: Durable job queue, processing lists, pub/sub for events, session/cache store.
- **Key API surface**: `LPUSH`, `RPOP`, `BLPOP`, `BRPOPLPUSH`, `BLMOVE`, `HSET`/`HGETALL`, `SET`/`GET`, `EXPIRE`, `SCAN`, Streams.
- **License / cost**: BSD-3-Clause for 7.2 and prior; 7.4+ RSALv2/SSPLv1; 8.0+ tri-license. Review before deployment.

#### 3.1.13 Android ADB + Intent

- **Official URL**: https://developer.android.com/tools/adb and https://developer.android.com/guide/components/intents-common
- **Verified**: Android developer docs cover ADB shell, activity manager (`am`), intent syntax, and common intents.
- **Version to pin**: Android Platform Tools 36.x (latest stable).
- **P23 use**: Remote Android device control, launching apps via intents, automating mobile actions, log capture.
- **Key CLI surface**: `adb devices`, `adb shell am start -a ACTION -d URI -n COMPONENT`, `adb shell input`, `adb logcat`, `adb push`/`pull`.
- **License / cost**: Apache-2.0 (Android Open Source Project), free.

#### 3.1.14 OpenTelemetry

- **Official URL**: https://opentelemetry.io/docs/
- **Verified**: Docs describe the open observability framework, APIs, SDKs, and Collector.
- **Version to pin**: Latest stable 1.x SDK/Collector.
- **P23 use**: Standardized traces/metrics/logs instrumentation across P23 operations.
- **Key API surface**: OTel API, SDK, exporters (OTLP), Collector receivers/processors/exporters.
- **License / cost**: Apache-2.0, free.

#### 3.1.15 Prometheus

- **Official URL**: https://prometheus.io/docs/
- **Verified**: Docs cover getting started, configuration, PromQL, and alerting.
- **Version to pin**: `3.12+` (latest) or LTS `3.5.x`.
- **P23 use**: Metrics scraping and storage for P23 operations; pairs with existing `windows_metrics.py`.
- **Key API surface**: `prometheus.yml` (`scrape_configs`, `global`), PromQL, `/metrics`, alert rules, recording rules.
- **License / cost**: Apache-2.0, free.

#### 3.1.16 Grafana

- **Official URL**: https://grafana.com/docs/grafana/latest/
- **Verified**: Docs cover installation, data sources, dashboards, and alerting.
- **Version to pin**: `13.x` (latest stable).
- **P23 use**: Dashboards for P23 operational metrics, alerts on queue depth/backup status/system health.
- **Key API surface**: Dashboard JSON, data source provisioning, Prometheus/Postgres queries, alerting rules, API keys.
- **License / cost**: AGPL-3.0 for Grafana OSS; Enterprise is paid.

---

## 4. Local Reuse Map

Searched directories: `src/mcp/`, `src/hermes_plugins/`, `plugins/`, and broader `src/` tree.

| Existing Executor / MCP | Reusable? | P23 Relation |
|---|---|---|
| `src/mcp/tools/obscura_cdp.py` | Partially — reuse for CDP attach, but Playwright is more capable | Browser automation; consider replacing or wrapping with Playwright |
| `src/mcp/tools/github.py` | Yes | GitHub REST/GraphQL operations, issue/PR/repo management |
| `src/mcp/tools/git_tool.py` | Yes | Local git operations, commit/push with auth gates |
| `src/mcp/tools/shell_tool.py` | Yes | Whitelisted shell execution for SSH/systemd commands, command safety |
| `src/mcp/tools/docker_tool.py` | Yes | VPS container lifecycle inspection/management |
| `src/mcp/tools/postgres_tool.py` | Yes | PostgreSQL queries and operations; extend with backup/restore wrappers |
| `src/mcp/tools/redis_tool.py` | Yes | Redis queue/list/hash operations; align with DB0-DB5 allocation |
| `src/mcp/tools/filesystem.py` | Yes | Path-whitelisted file I/O for P23 evidence/logs |
| `src/mcp/auth.py` + `auth_matrix.py` | Yes | 4-level authorization (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN) |
| `src/mcp/tool_selector.py` | Yes | Tool selection decision matrix with weighted scoring |
| `src/loops/tool_registry.py` | Yes | Unified tool registry for agent loops |
| `src/hermes_plugins/commands_admin/restart_service.py` | Yes | systemd service restart (Guinevere services whitelist) |
| `src/hermes_plugins/commands_admin/backup_now.py` | Yes | PostgreSQL backup trigger to S3 |
| `src/hermes_plugins/commands_admin/health_check.py` | Yes | Health probe pattern for Hermes/Postgres/Redis/router |
| `src/observability/windows_metrics.py` | Yes | Prometheus metrics for Windows daemon; extend for P23 metrics |
| Various `src/*/metrics.py` | Yes | Module-level Prometheus metrics; reuse instrumentation pattern |
| `src/life_kernel/sensor_adapters/browser_adapter.py` | Partially — placeholder | Browser sensor adapter; can be implemented with Playwright |
| **Android ADB** | **No** | No existing ADB executor; must build new or invoke `adb` via shell_tool |
| **PowerShell / Windows Task Scheduler** | **No** | No Windows-specific automation executor; must build new |
| **rclone** | **No** | No rclone wrapper; must build new or shell out via shell_tool |
| **OpenTelemetry SDK** | **No** | Only Prometheus metrics exist; OTel SDK integration is new work |

### 4.1 Reuse Verdict by Domain

| Domain | Reuse Status |
|---|---|
| Browser automation | High reuse of `obscura_cdp.py` plumbing; recommend migrating core driver to Playwright while keeping MCP auth gates |
| GitHub operations | High reuse — `github.py` + `git_tool.py` cover most needs; extend for GraphQL bulk operations |
| SSH / systemd | Medium reuse — `shell_tool.py` + `restart_service.py` handle basics; add dedicated SSH executor for multi-hop/key management |
| PostgreSQL | High reuse — `postgres_tool.py` provides read/execute gates; add backup/restore executor |
| Redis queues | High reuse — `redis_tool.py` covers core commands; add durable queue abstraction |
| rclone / AWS | Low reuse — no existing wrappers; build new executor or constrained shell invocations |
| Android ADB | Low reuse — no existing ADB surface; build new executor with device allowlist |
| PowerShell / Task Scheduler | Low reuse — build Windows scheduler executor and PowerShell runner with command allowlist |
| Metrics / Observability | Medium reuse — `windows_metrics.py` and module metrics.py exist; build unified OTel/Prometheus/Grafana layer |

---

## 5. Risks / Open Questions

### 5.1 Tool-specific Risks

1. **Redis license change**: Redis 7.4+ switched from BSD-3-Clause to RSALv2/SSPLv1; 8.0+ adds AGPLv3 option. If P23 uses Redis as a service component, license compliance must be reviewed. Strongly consider pinning to **Redis 7.2.x** (last BSD release) unless a feature in 7.4+ is required.

2. **Playwright browser binaries**: Playwright downloads external browser binaries. On an air-gapped or restricted VPS, binary installation must be pre-staged or mirrored. This is a deployment risk, not a docs risk.

3. **GitHub API rate limits**: REST/GraphQL operations are subject to GitHub rate limits. P23 automation that creates/issues/bulk-fetches must implement backoff, caching, and token rotation.

4. **No official API for Windows Task Scheduler at a high level**: The COM API is official but Windows-specific and less documented than cross-platform alternatives. This is a moderate risk for automation reliability.

5. **ADB security**: `adb` over network is unencrypted by default. P23 must use USB or encrypted network ADB, and device authorization must be explicit.

6. **OpenSSH version drift**: Ubuntu 24.04 ships a specific OpenSSH version; P23 must pin or at least validate against that version to avoid config-option incompatibilities.

### 5.2 Open Questions

- Which Redis version will the P23 production environment target? (License vs. feature trade-off)
- Will P23 run Playwright on the VPS (headless) or on the Windows host?
- Is the Windows Task Scheduler the final scheduler, or will P23 also use `systemd` timers on the Ubuntu VPS?
- What is the backup retention/S3 target — rclone only, or aws-cli also required?
- Does P23 need real Android device control, or only emulator control?

---

## 6. Recommendations to Planner

1. **Pin versions in a single source of truth**: Create a `p23-tool-versions.yaml` or ADR amendment listing the pinning decisions (Playwright 1.60.0, Redis 7.2.x, rclone 1.74.3, AWS CLI 2.27.41+, gh 2.93.0+, PowerShell 7.6.3 LTS, systemd 257, PostgreSQL 18.x).

2. **Prefer reuse, build thin wrappers**: For every domain with existing MCP/Hermes tools, reuse the auth/consent gates rather than building new executors from scratch. New surfaces (ADB, PowerShell, rclone, Task Scheduler) should still route through the existing 4-level auth system.

3. **Address Redis licensing early**: If P23 plans to distribute or offer Redis as a managed component, legal review of RSALv2/SSPLv1/AGPLv3 is required. If only internal use, document the license choice.

4. **Add an ADR for Windows integration**: Because Windows Task Scheduler and PowerShell are proprietary, document why they were chosen and what the cross-platform fallback is.

5. **Verify ADR-013 and ADR-017 alignment**: Ensure the MCP-native and Prometheus+Grafana ADRs explicitly cover the new P23 executors and metrics.

6. **Security gates for high-risk tools**: SSH key management, ADB device authorization, PowerShell script execution policy, and Task Scheduler task creation should all require at least WRITE_NOTIFY or DESTRUCTIVE_APPROVAL per the P23 policy framework.

---

## 7. Verdict

All P23 ground-truth tools have official, verifiable documentation URLs. No tool is in the same high-risk category as P22 Obsidian (which lacks an official API). The highest-risk items are:

- **Redis** (license change at 7.4+)
- **Windows Task Scheduler** (proprietary, Windows-only, less portable)
- **ADB** (security model requires careful device authorization)

Existing local MCP/Hermes executors can cover approximately 60-70% of the P23 action layer. New executors are required for Android ADB, PowerShell/Windows Task Scheduler, and rclone, but they can reuse the established auth, consent, and registry infrastructure.

**Research complete.**
