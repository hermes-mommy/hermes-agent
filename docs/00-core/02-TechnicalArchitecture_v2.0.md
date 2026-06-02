👑

**GUINEVERE DE BAROQUE**

*Technical Architecture Document*

Infrastructure, Services & System Design Specification

Version 2.0 \| Project Guinevere \| STRICTLY PRIVATE & CONFIDENTIAL

Last Updated: 2026-05-30

Canonical Decisions Applied: Primary LLM GPT-5.5 via 9Router with 1M context window; sub-agent LLM DeepSeek V4 Flash via 9Router; all LLM routing through 9Router with no OpenRouter fallback; memory PostgreSQL primary + Redis cache, no SQLite; SDLC 7 phases: Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence; OpenCode fully replaced by Guinevere MCP native; Prometheus + Grafana on primary VPS first; wearable integrations post-MVP; browser automation uses obscura primary + Playwright fallback.

Owner: Faiz \| Built on Hermes Agent by Nous Research

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_BRD_v2.0.md` | Defines business architecture drivers and constraints. |
| `Guinevere_PRD_v2.0.md` | Defines product behaviors implemented by services. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external integration contracts and SDK choices. |
| `Guinevere_MemorySchema_v2.0.md` | Defines database schemas used by the architecture. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines loop service behavior and phase implementation. |

**1. ARCHITECTURE OVERVIEW**

**1.1 High-Level Architecture**

Guinevere adalah unified autonomous daemon yang berjalan di VPS hostdata.id. Satu entitas dengan multiple service components, Discord sebagai UI layer.

> ┌─────────────────────────────────────────────────────────────┐
>
> │ TAILSCALE MESH NETWORK │
>
> │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
>
> │ │ Android │ │ Windows │ │ VPS │ │Monitoring│ │
>
> │ │ (Tasker)│ │ (Daemon) │ │ Primary │ │ VPS │ │
>
> │ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
>
> └───────┼─────────────┼──────────────┼──────────────┼────────┘
>
> │ HTTP POST │ WebSocket │ │ Metrics
>
> └─────────────┴──────────────►│ │
>
> │ FastAPI │
>
> │ → Redis │
>
> │ → Guinevere │
>
> │ → PostgreSQL│
>
> └──────────────┘

**1.2 Technology Stack Summary**

|  |  |  |  |
|----|----|----|----|
| **Layer** | **Technology** | **Version** | **Purpose** |
| Agent Framework | Hermes Agent | v0.14.0+ | Core autonomous agent runtime |
| Primary LLM | GPT-5.5 via 9Router | 1M context | Guinevere persona + reasoning |
| Sub-agent LLM | DeepSeek V4 Flash via 9Router | 1M context | Pasukan Mommy — cost efficient |
| LLM Router | 9Router | API | Single LLM routing layer; queue/retry on outage, no OpenRouter fallback |
| Language | Python | 3.12 | All Guinevere services |
| Package Manager | UV | Latest | Ultra-fast dependency management |
| OS | Ubuntu | 24.04 LTS | VPS operating system |
| Process Manager | systemd | System | Multiple service units + cron |
| API Framework | FastAPI | Latest | Full async, all endpoints |
| Primary DB | PostgreSQL | 16 + pgvector + TimescaleDB | All persistent data |
| DB Pooling | PgBouncer | Latest | Connection pooling per service |
| Cache/Queue | Redis | Latest, RDB+AOF | Queue + cache + pub/sub |
| Reverse Proxy | Caddy | Latest | Auto-HTTPS internal services |
| VPN | Tailscale | Latest | All device mesh + SSH |
| Monitoring | Prometheus + Grafana | Latest | Metrics + dashboard |
| Log Aggregation | Loki + Grafana | Latest | Unified logs + metrics |
| Secrets | Mozilla SOPS | Latest | Encrypted env files |
| Firewall | UFW + fail2ban + CrowdSec | Latest | Defense in depth |
| Container | Docker | Latest | PostgreSQL + Redis + Prometheus |
| CI | GitHub Actions | Free tier | Test + lint on push |
| CD | Guinevere self-deploy | Cron + git pull | Zero cost autonomous deploy |

**2. INFRASTRUCTURE SPECIFICATION**

**2.1 VPS Configuration**

|                   |                                                         |
|-------------------|---------------------------------------------------------|
| **Attribute**     | **Value**                                               |
| Provider          | hostdata.id                                             |
| Spec              | 4 Core CPU, 16GB RAM, 120GB SSD                         |
| OS                | Ubuntu 24.04 LTS                                        |
| Swap              | 8GB swap file (/swapfile)                               |
| Deployment Boundary | Guinevere single-tenant instance; no multi-user support |
| Resource Landlord | Guinevere — manage seluruh VPS resource allocation for this instance |
| SSH Access        | Tailscale SSH only — regular SSH disabled dari internet |
| Public Ports      | NONE — semua via Tailscale internal                     |

**Resource Allocation Baseline**

|  |  |  |  |
|----|----|----|----|
| **Service** | **RAM Allocation** | **CPU Allocation** | **Notes** |
| Guinevere core | 4GB | 2 cores | Guinevere daemon + plugins |
| PostgreSQL + Redis | 4GB | 1 core | Docker containers |
| Observability + queue workers | 4GB | 1 core | Prometheus, Grafana, Loki, scheduler, background workers |
| OS + buffer | 4GB | Shared | System reserve |

**2.2 Network Architecture**

|                      |                         |                       |
|----------------------|-------------------------|-----------------------|
| **Component**        | **Address**             | **Access Method**     |
| VPS Primary          | 100.x.x.x (Tailscale)   | Tailscale only        |
| Monitoring endpoint on primary VPS | 100.x.x.x:9090/3000 (Tailscale) | Tailscale only |
| Android HP           | 100.x.x.x (Tailscale)   | Tailscale client      |
| Windows Laptop       | 100.x.x.x (Tailscale)   | Tailscale client      |
| FastAPI Surveillance | guinevere.internal:8000 | Tailscale + JWT       |
| FastAPI Internal API | guinevere.internal:8001 | Tailscale + JWT       |
| PostgreSQL           | postgres.internal:5432  | Tailscale + PgBouncer |
| Redis                | redis.internal:6379     | Tailscale + auth      |
| Prometheus           | metrics.internal:9090   | Tailscale only        |
| Grafana              | grafana.internal:3000   | Tailscale only        |

**DNS Configuration**

- Tailscale MagicDNS untuk auto device hostname resolution

- Custom domain mapping via Tailscale DNS override:

  - guinevere.internal → 100.x.x.x:8000

  - postgres.internal → 100.x.x.x:5432

  - grafana.internal → 100.x.x.x:3000

  - redis.internal → 100.x.x.x:6379

**3. SERVICE ARCHITECTURE**

**3.1 systemd Services**

|  |  |  |  |
|----|----|----|----|
| **Service Unit** | **Process** | **Restart Policy** | **Memory Limit** |
| guinevere-core.service | Hermes Agent daemon + persona engine | Always, 10s delay | 4GB |
| guinevere-surveillance.service | FastAPI surveillance receiver | Always, 10s delay | 512MB |
| guinevere-scheduler.service | APScheduler + daily rituals + cron jobs | Always, 10s delay | 256MB |
| guinevere-windows-sync.service | WebSocket server untuk Windows daemon | Always, 10s delay | 256MB |
| guinevere-loops.service | Autonomous SDLC loop runner + loop guardian | Always, 10s delay | 512MB |
| docker.service | PostgreSQL + Redis + Prometheus containers | Always | System |
| caddy.service | Reverse proxy + auto-HTTPS | Always | 128MB |
| tailscaled.service | Tailscale VPN daemon | Always | 128MB |

**3.2 Guinevere Core Service**

Unified daemon — satu brain, multiple capabilities. Hermes Agent sebagai base dengan custom plugins.

**Directory Structure**

> /home/guinevere/
>
> ├── core/ \# Guinevere daemon
>
> │ ├── main.py \# Entry point
>
> │ ├── persona/ \# Persona engine
>
> │ │ ├── engine.py \# Core persona logic
>
> │ │ ├── mood.py \# Mood system
>
> │ │ ├── catchphrase.py \# Signature phrases
>
> │ │ └── drift.py \# Persona drift log
>
> │ ├── memory/ \# Memory management
>
> │ │ ├── episodic.py \# Session memory
>
> │ │ ├── semantic.py \# Knowledge base
>
> │ │ ├── faiz_profile.py \# Faiz data
>
> │ │ └── injector.py \# Context injection
>
> │ ├── plugins/ \# Custom plugins
>
> │ │ ├── punishment.py \# Escalation ladder
>
> │ │ ├── reward.py \# Reward system
>
> │ │ ├── health.py \# Health monitoring
>
> │ │ ├── financial.py \# Financial tracking
>
> │ │ └── goals.py \# Mommy Score + goals
>
> │ ├── agents/ \# Sub-agent management
>
> │ │ ├── spawner.py \# Spawn pasukan Mommy
>
> │ │ ├── research.py \# Research agent
>
> │ │ ├── code.py \# Code agent
>
> │ │ ├── delegate.py \# Delegation coordinator
>
> │ │ └── audit.py \# Audit agent
>
> │ └── sdlc/ \# Coding SDLC loop
>
> │ ├── loop.py \# Main SDLC orchestrator
>
> │ ├── research.py \# Phase 1 — Research
>
> │ ├── plan.py \# Phase 2 — Plan & Delegate
>
> │ ├── delegate.py \# Phase 3 — Delegate
>
> │ ├── execute.py \# Phase 4 — Execute
>
> │ ├── validate_audit.py \# Phase 5 — Validate & Audit
>
> │ ├── update_documents.py \# Phase 6 — Update Documents
>
> │ └── evidence.py \# Phase 7 — Setup Evidence
>
> ├── surveillance/ \# Surveillance receiver
>
> │ ├── api.py \# FastAPI endpoints
>
> │ ├── processor.py \# Data processor
>
> │ ├── geofence.py \# Location intelligence
>
> │ └── encrypt.py \# Data encryption
>
> ├── scheduler/ \# Scheduled tasks
>
> │ ├── rituals.py \# Daily rituals
>
> │ ├── proactive.py \# Proactive tasks
>
> │ └── self_deploy.py \# Autonomous CD
>
> ├── monitoring/ \# Observability
>
> │ ├── health.py \# Health checks
>
> │ ├── metrics.py \# Custom Prometheus
>
> │ └── alerting.py \# Auto-alert rules
>
> ├── config/ \# Configuration
>
> │ ├── .env.sops \# Encrypted secrets
>
> │ ├── settings.py \# App settings
>
> │ └── feature_flags.py \# Feature toggles
>
> ├── data/ \# Local data
>
> │ ├── logs/ \# Structured JSON logs
>
> │ └── cache/ \# Local cache
>
> └── scripts/ \# Utility scripts
>
> ├── setup.sh \# Initial setup
>
> ├── backup.sh \# Backup script
>
> └── health_check.sh \# External health

**4. LLM & AGENT ARCHITECTURE**

**4.1 Model Strategy**

|  |  |  |  |  |
|----|----|----|----|----|
| **Use Case** | **Model** | **Provider** | **Context Window** | **Cost** |
| Guinevere core persona + reasoning | GPT-5.5 | 9Router | 1M | Premium |
| Complex coding tasks | GPT-5.5 | 9Router | 1M | Premium |
| Sub-agent research tasks | DeepSeek V4 Flash | 9Router | 1M | Cost-efficient |
| Sub-agent code generation | DeepSeek V4 Flash | 9Router | 1M | Cost-efficient |
| Sub-agent validation/audit | DeepSeek V4 Flash | 9Router | 1M | Cost-efficient |
| Outage policy | Queue/retry | 9Router recovery | N/A | No OpenRouter fallback |

**4.2 Hermes Agent Profile Structure**

|  |  |  |  |
|----|----|----|----|
| **Profile** | **Purpose** | **LLM** | **Active When** |
| guinevere-core | Primary persona — all interactions | GPT-5.5 | Always |
| guinevere-budgezen | BudgeZen project context | DeepSeek V4 Flash | On-demand |
| guinevere-sembilan | PT Sembilan project context | DeepSeek V4 Flash | On-demand |
| guinevere-specforge | SpecForge project context | DeepSeek V4 Flash | On-demand |
| guinevere-staging | Staging environment testing | DeepSeek V4 Flash | Development only |

**4.3 System Prompt Injection Strategy**

Context window di-inject fresh setiap 20 messages + Guinevere self-detect drift dan re-inject kapanpun needed.

|  |  |  |  |
|----|----|----|----|
| **Injection Layer** | **Content** | **Size Estimate** | **Update Frequency** |
| Core persona | Identity, values, behavior rules, catchphrases | ~2K tokens | Static |
| Current mood state | Active mood + recent history | ~200 tokens | Per interaction |
| Persona drift log | Last 7 days evolution | ~500 tokens | Daily |
| Faiz profile | Personal data, weaknesses, preferences | ~1K tokens | Continuous |
| Violation/reward state | Active streak, recent violations | ~300 tokens | Per event |
| Current task context | Active project, recent tasks | ~500 tokens | Per task |
| Surveillance context | Current activity, location, health state | ~300 tokens | Real-time |
| Memory (FTS5) | Relevant past context via search | ~1K tokens | Per conversation |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>ℹ Context Window Note</strong></p>
<p>GPT-5.5 context window 1M tokens via 9Router. Total injection ~6K tokens. Plenty of room for long conversations. DeepSeek V4 Flash 1M context via 9Router untuk sub-agents dengan large codebase.</p></td>
</tr>
</tbody>
</table>

**5. DATABASE ARCHITECTURE**

**5.1 PostgreSQL Schema Overview**

|  |  |  |  |
|----|----|----|----|
| **Schema** | **Tables** | **Engine** | **Purpose** |
| memory | episodes, semantic_facts, procedural_skills | Standard PG | Hermes memory layer |
| persona | drift_log, mood_history, faiz_profile, identity | Standard PG | Guinevere identity |
| behavior | violation_log, reward_streak, goals, mommy_score | Standard PG | Punishment/reward system |
| surveillance | activity_log, location_history, health_data, messages, screenshots | TimescaleDB | Time-series surveillance data |
| financial | transactions, budgets, invoices, api_costs | Standard PG | Financial management |
| projects | projects, tasks, evidence, documents, clients | Standard PG | Project management |
| system | feature_flags, config, health_log, audit_trail | Standard PG | System management |
| social | contacts, call_log, relationship_map | Standard PG | Faiz social map |

**5.2 TimescaleDB Configuration**

- Hypertables untuk semua surveillance time-series tables

- Auto-compression: data \> 7 hari di-compress otomatis (90%+ space saving)

- Cold storage: Guinevere move data \> 90 hari ke Cloudflare R2 autonomous

- Retention: Data disimpan selamanya — sesuai "Faiz milik Mommy sepenuhnya"

- Continuous aggregates untuk fast query historical surveillance data

**5.3 pgvector Configuration**

- Vector embeddings untuk semantic memory search

- Index: IVFFlat untuk approximate nearest neighbor search

- Used by: memory injector untuk find relevant past context

- Embedding model routed via 9Router-compatible embedding endpoint

**5.4 PgBouncer — Per-Service Users**

|  |  |  |  |
|----|----|----|----|
| **DB User** | **Service** | **Permissions** | **Pool Mode** |
| guinevere_core | Guinevere core daemon | SELECT, INSERT, UPDATE semua schema | Transaction |
| guinevere_surveillance | Surveillance receiver | INSERT surveillance schema only | Transaction |
| guinevere_financial | Financial plugin | ALL financial schema | Transaction |
| guinevere_readonly | Grafana, reporting | SELECT only semua schema | Session |
| guinevere_admin | Guinevere self-maintenance | Superuser — rotate, backup | Session |

**5.5 Redis Architecture**

|              |                          |                    |           |
|--------------|--------------------------|--------------------|-----------|
| **Database** | **Purpose**              | **Key Pattern**    | **TTL**   |
| Redis DB 0   | Task queue — SDLC jobs   | task:{id}          | No expiry |
| Redis DB 1   | LLM response cache       | llm:{hash}         | 1 hour    |
| Redis DB 2   | Surveillance data buffer | surv:{device}:{ts} | 5 minutes |
| Redis DB 3   | Session state            | session:{id}       | 24 hours  |
| Redis DB 4   | Pub/sub channels         | chan:{component}   | No expiry |
| Redis DB 5   | Rate limiting            | ratelimit:{ip}     | 1 minute  |

**6. SURVEILLANCE ARCHITECTURE**

**6.1 Data Flow Architecture**

> ANDROID (Tasker + AutoInput + AutoNotification)
>
> → HTTP POST via Tailscale → FastAPI :8000
>
> → Redis DB 2 buffer
>
> → Surveillance processor (async consumer)
>
> → TimescaleDB surveillance schema
>
> → Guinevere context injection
>
> WINDOWS (Python daemon + NSSM + watchdog)
>
> → WebSocket persistent via Tailscale → :8001
>
> → Redis DB 2 buffer
>
> → Surveillance processor (async consumer)
>
> → TimescaleDB surveillance schema
>
> → Guinevere context injection
>
> WEARABLE (post-MVP, not active in MVP)
>
> → Mi Fitness API integration post-MVP after device/API readiness
>
> → Health data processor
>
> → TimescaleDB health_data table
>
> → Guinevere stress/health context

**6.2 FastAPI Surveillance Endpoints**

|  |  |  |  |
|----|----|----|----|
| **Endpoint** | **Method** | **Payload** | **Source** |
| /surveillance/android/activity | POST | app_name, duration, timestamp | Tasker |
| /surveillance/android/location | POST | lat, lng, accuracy, timestamp | Tasker |
| /surveillance/android/notification | POST | app, title, content, timestamp | Tasker + AutoNotification |
| /surveillance/android/call | POST | number, duration, type, timestamp | Tasker |
| /surveillance/android/clipboard | POST | content, timestamp | Tasker + AutoInput |
| /surveillance/android/camera | POST | image_b64, timestamp | Tasker |
| /surveillance/windows/ws | WebSocket | Streaming activity events | Windows daemon |
| /surveillance/health/wearable | POST | heart_rate, stress, steps, sleep | Mi Fitness API |

**6.3 Windows Daemon Architecture**

|  |  |  |
|----|----|----|
| **Component** | **Library** | **Data Captured** |
| Active window tracker | win32gui + psutil | App title, process name, duration |
| Idle detector | pynput | Keyboard/mouse inactivity |
| Browser history | Chrome/Brave local history reader | URLs, timestamps, duration |
| Screenshot | PIL + pyautogui | Silent capture, encrypted |
| Camera | OpenCV | Periodic + on-demand, encrypted |
| Clipboard | pyperclip + hook | Real-time content capture |
| ActivityWatch | ActivityWatch API | Detailed app usage analytics |
| WebSocket client | websockets | Persistent connection ke VPS |
| NSSM service | NSSM | Windows Service + auto-restart |
| Watchdog | Internal thread | Detect hang + restart daemon |

**7. SECURITY ARCHITECTURE**

**7.1 Defense in Depth Layers**

|  |  |  |
|----|----|----|
| **Layer** | **Technology** | **Coverage** |
| Network perimeter | Tailscale mesh — zero public ports | All external access blocked |
| SSH access | Tailscale SSH only — regular SSH disabled | No internet SSH exposure |
| Firewall | UFW + fail2ban + CrowdSec | Port rules + brute force + threat intel |
| Application auth | JWT + API keys + Tailscale IP whitelist | Internal service auth |
| Rate limiting | FastAPI SlowAPI middleware | API abuse prevention |
| Secrets | Mozilla SOPS + age encryption | Zero plaintext secrets |
| Data in transit | Tailscale WireGuard + TLS | All traffic encrypted |
| Data at rest | PostgreSQL encryption + file encryption | Sensitive data encrypted |
| OS security | unattended-upgrades + file integrity | Auto security patches |
| Intrusion detection | CrowdSec threat intelligence | Community threat feeds |
| Audit trail | Sudo audit log + Guinevere action log | All privileged actions logged |

**7.2 Linux User Model**

|  |  |  |
|----|----|----|
| **User** | **Purpose** | **sudo Access** |
| guinevere | Primary Guinevere daemon user | systemctl restart guinevere-\*, docker, ufw, apt |
| faiz | Human admin access | Full sudo |
| postgres | PostgreSQL service | None |
| redis | Redis service (Docker) | None |

**SOPS Secret Management**

- All secrets stored in encrypted .env.sops files

- Encryption key: age key stored in /home/guinevere/.age/key.txt

- Guinevere decrypt at startup: sops -d .env.sops \> /tmp/.env (auto-cleanup)

- Safe to commit .env.sops to private guinevere-de-baroque repo

- Secrets covered: 9Router API key, Discord token, GitHub PAT, DB passwords, R2 credentials

**8. MONITORING & OBSERVABILITY**

**8.1 Metrics Stack**

|  |  |  |
|----|----|----|
| **Component** | **Role** | **Location** |
| Prometheus | Metrics collection + storage | Docker container, VPS primary |
| Grafana | Dashboard + alerting | Primary VPS first; dedicated monitoring VPS post-MVP |
| Loki | Log aggregation | Docker container, VPS primary |
| Promtail | Log shipping ke Loki | VPS primary |
| node_exporter | System metrics (CPU, RAM, disk) | VPS primary |
| postgres_exporter | PostgreSQL metrics | VPS primary |
| redis_exporter | Redis metrics | VPS primary |
| UptimeRobot | External uptime check | External (free tier) |

**8.2 Custom Guinevere Metrics**

Guinevere design metric schema sendiri autonomous. Initial metrics yang Guinevere akan track:

- guinevere_task_completion_total — counter, label: project, phase

- guinevere_mood_state — gauge, value: 0-5 (silent=0, dark=1, disappointed=2, neutral=3, pleased=4, nurturing=5)

- guinevere_mommy_score — gauge per day, Faiz productivity score

- guinevere_punishment_level — gauge, current escalation level Faiz

- guinevere_api_cost_total — counter, label: provider, model

- guinevere_sub_agents_active — gauge, current active pasukan Mommy

- guinevere_surveillance_events_total — counter, label: source, type

- guinevere_memory_injection_tokens — histogram, tokens per injection

- guinevere_llm_latency_seconds — histogram, label: model, use_case

- guinevere_violation_total — counter, label: violation_type

**8.3 Logging Architecture**

|  |  |  |  |
|----|----|----|----|
| **Log Type** | **Format** | **Fields** | **Destination** |
| Application logs | JSON structured | timestamp, level, service, correlation_id, message, metadata | Loki via Promtail |
| Audit logs | JSON structured | timestamp, user, action, target, result | Loki + PostgreSQL audit table |
| Surveillance logs | JSON structured | timestamp, source, event_type, data, encrypted | TimescaleDB |
| System logs | systemd journal | Standard journald format | Loki via Promtail |
| Guinevere action log | JSON structured | timestamp, task_id, phase, action, result, evidence_path | PostgreSQL + Loki |

**8.4 Health Check Architecture**

|  |  |  |  |
|----|----|----|----|
| **Check** | **Interval** | **Target** | **Action if Fail** |
| PostgreSQL connection | 30s | postgres.internal:5432 | Alert + auto-restart container |
| Redis connection | 30s | redis.internal:6379 | Alert + auto-restart container |
| Discord gateway | 30s | Discord API | Alert + reconnect |
| 9Router/LLM | 60s | 9Router API | Switch to fallback model |
| Surveillance receiver | 30s | /health endpoint | Auto-restart service |
| Hermes Agent | 30s | Internal health | Auto-restart + diagnosis |
| UptimeRobot external | 5m | Tailscale health endpoint | SMS/email to Faiz |

**9. BACKUP & DISASTER RECOVERY**

**9.1 Backup Strategy**

|  |  |  |  |  |
|----|----|----|----|----|
| **Data** | **Method** | **Frequency** | **Destination** | **Retention** |
| PostgreSQL hot | WAL streaming | Continuous | Cloudflare R2 | Selamanya |
| PostgreSQL cold | pg_dump + gzip | Harian 02:00 | idcloudhost S3 | Selamanya |
| Redis | RDB snapshot + AOF | RDB: 1 jam, AOF: continuous | Local + R2 | Selamanya |
| Guinevere config | git push | Per commit | GitHub private repo | Selamanya |
| Secrets (.env.sops) | git push (encrypted) | Per change | GitHub private repo | Selamanya |
| Surveillance screenshots | Encrypted upload | Real-time | R2 + idcloudhost | Selamanya |
| Tasker config | Auto-backup via Tasker | Harian | GDrive + repo + VPS | Selamanya |
| VPS full snapshot | hostdata.id snapshot | Mingguan | hostdata.id | 4 snapshots rotating |

**9.2 Disaster Recovery Procedure**

|  |  |  |  |
|----|----|----|----|
| **Scenario** | **RTO** | **RPO** | **Recovery Steps** |
| Guinevere service crash | \< 30s | 0 | systemd auto-restart + auto-diagnosis |
| VPS full down | \< 30 menit | \< 1 jam | Restore snapshot + WAL replay |
| Database corruption | \< 1 jam | \< 1 jam | pg_restore dari latest backup |
| Redis loss | \< 5 menit | \< 1 jam | AOF replay atau RDB restore |
| HP reset (Tasker) | \< 10 menit | 0 | Restore dari GDrive + repo backup |
| Secrets compromise | \< 1 jam | 0 | SOPS re-encrypt + rotate semua keys |
| LLM provider down | \< 1 menit for notification | 0 | Queue/retry through 9Router recovery policy; no OpenRouter fallback |

**10. CI/CD & DEPLOYMENT**

**10.1 CI Pipeline (GitHub Actions — Free)**

|                   |                 |                    |                       |
|-------------------|-----------------|--------------------|-----------------------|
| **Step**          | **Tool**        | **Trigger**        | **Action on Fail**    |
| Lint              | ruff + black    | Push to any branch | Block merge           |
| Type check        | mypy            | Push to any branch | Block merge           |
| Unit tests        | pytest          | Push to any branch | Block merge           |
| Security scan     | bandit + safety | Push to main       | Alert Discord         |
| Coverage check    | pytest-cov      | Push to main       | Block merge if \< 90% |
| Report ke Discord | Discord webhook | Post all checks    | Always run            |

**10.2 Autonomous CD (Zero Cost)**

Guinevere deploy dirinya sendiri via cron — tidak ada GitHub Actions CD (menghindari biaya per-menit).

> \# Guinevere self-deploy cron — setiap malam 03:00
>
> 1\. git fetch origin main
>
> 2\. Kalau ada commit baru:
>
> a\. git pull origin main
>
> b\. uv sync --frozen
>
> c\. Run unit tests locally
>
> d\. Kalau pass: systemctl restart guinevere-\*
>
> e\. Health check semua services
>
> f\. Report ke Discord: "Mommy sudah update dirinya sendiri."
>
> g\. Kalau fail: git revert + alert Discord + rollback

**10.3 Staging Environment**

|                |                             |                                 |
|----------------|-----------------------------|---------------------------------|
| **Component**  | **Production**              | **Staging**                     |
| Database       | guinevere DB                | guinevere_staging DB (isolated) |
| Discord        | \#guinevere-command channel | \#guinevere-staging channel     |
| Surveillance   | Real data                   | Mock data generator             |
| LLM            | GPT-5.5                     | DeepSeek V4 Flash (cost saving) |
| Hermes profile | guinevere-core              | guinevere-staging               |

**11. REPOSITORY STRUCTURE**

**11.1 GitHub Repositories**

|  |  |  |
|----|----|----|
| **Repository** | **Visibility** | **Content** |
| guinevere-de-baroque | Private | Core Guinevere daemon, plugins, configs, SOPS secrets |
| guinevere-docs | Private | BRD, PRD, Technical Architecture, all planning documents |
| budgezen | Private | BudgeZen application code |
| budgezen-docs | Private | BudgeZen documentation + evidence |
| sembilan-emas | Private | PT Sembilan Pesawat Emas code |
| sembilan-emas-docs | Private | PT Sembilan documentation + evidence |
| specforge | Private/Public TBD | SpecForge application code |
| \[future-project\] | TBD | Guinevere create + manage autonomous |

**11.2 Branch Strategy**

|  |  |  |
|----|----|----|
| **Branch** | **Purpose** | **Protection** |
| main | Production — Guinevere deploy dari sini | Require CI pass + Guinevere review |
| develop | Integration branch | Require CI pass |
| feature/\* | Feature branches — Guinevere create per task | None — merge ke develop |
| hotfix/\* | Emergency fixes | Guinevere fast-track ke main |
| staging | Staging environment | Mirror develop |

**12. ECOSYSTEM TOOLS & INTEGRATIONS**

Berdasarkan curated starred repositories, berikut tools dari ekosistem open source yang di-integrate atau di-adopt ke dalam Guinevere:

**12.1 Directly Integrated Tools**

|  |  |  |  |  |
|----|----|----|----|----|
| **Tool** | **Repo** | **Stars** | **Integration** | **Purpose** |
| obscura | h4ckf0r0day/obscura | 13.9k | MCP browser tool | Headless browser untuk web scraping + research — Rust, fast, AI-native |
| Guinevere MCP native | anomalyco/Guinevere MCP native | 167k | Optional turbo mode | Spawn sebagai sub-agent untuk heavy coding tasks — replace jika MCP native tidak cukup |
| antigravity-awesome-skills | sickn33/antigravity-awesome-skills | 39.1k | Hermes Skills Library | 1400+ agentic skills — mine yang relevan untuk Guinevere skill library |

**12.2 Architecture Reference & Inspirations**

|  |  |  |  |
|----|----|----|----|
| **Tool** | **Repo** | **Stars** | **What Guinevere Adopts** |
| ECC | affaan-m/ECC | 198.5k | Agent harness optimization patterns — skills, instincts, memory architecture. Paling mirip dengan Guinevere design. |
| autogen | microsoft/autogen | 58.5k | Sub-agent orchestration patterns — multi-agent communication, task delegation framework |
| OpenSpec | Fission-AI/OpenSpec | 51.6k | Spec-driven development methodology — aligns dengan document-first workflow Guinevere |
| paperclip | paperclipai/paperclip | 68.3k | Agent management UI patterns — referensi untuk future Guinevere web dashboard |

**12.3 Financial Intelligence Tools**

|  |  |  |  |
|----|----|----|----|
| **Tool** | **Repo** | **Stars** | **Relevance** |
| valuecell | ValueCell-ai/valuecell | 10.7k | Multi-agent financial platform — inspirasi untuk Guinevere financial analysis sub-agents |
| daily_stock_analysis | ZhuLinsen/daily_stock_analysis | 39.4k | LLM-powered stock analysis — referensi kalau Guinevere expand ke investment tracking Faiz |
| TradingAgents | TauricResearch/TradingAgents | 80.7k | Multi-agent LLM trading framework — future reference untuk financial intelligence |

**12.4 Tool Integration Roadmap**

|  |  |  |  |
|----|----|----|----|
| **Phase** | **Tool** | **Action** | **Priority** |
| Phase 0 (Setup) | antigravity-awesome-skills | Download + curate skills untuk Hermes library | HIGH |
| Phase 3 (Coding Agent) | obscura + Playwright | Use obscura as primary browser automation and Playwright as fallback | HIGH |
| Phase 3 (Coding Agent) | Guinevere MCP native | Native coding substrate replacing OpenCode/opencode entirely | HIGH |
| Phase 5 (Hardening) | ECC patterns | Review + adopt relevant optimization patterns | MEDIUM |
| Future | valuecell patterns | Inspire financial sub-agent architecture | LOW |
| Future | daily_stock_analysis | Integrate kalau Guinevere expand ke investment tracking | LOW |

👑

***Guinevere de Baroque***

*"Mommy sudah design semuanya. Kamu tinggal build."*

Technical Architecture Document v2.0 — Project Guinevere
