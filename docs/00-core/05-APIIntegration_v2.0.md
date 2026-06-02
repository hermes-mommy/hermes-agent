👑

**GUINEVERE DE BAROQUE**

*API Integration Document*

Complete External Services, SDKs & Library Specification

Version 2.0 \| Project Guinevere \| STRICTLY PRIVATE & CONFIDENTIAL

Last Updated: 2026-05-30

Canonical Decisions Applied: Primary LLM GPT-5.5 via 9Router with 1M context window; sub-agent LLM DeepSeek V4 Flash via 9Router; all LLM routing through 9Router with no OpenRouter fallback; memory PostgreSQL primary + Redis cache, no SQLite; SDLC 7 phases: Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence; OpenCode fully replaced by Guinevere MCP native; Prometheus + Grafana on primary VPS first; wearable integrations post-MVP; browser automation uses obscura primary + Playwright fallback.

Owner: Faiz \| Built on Hermes Agent by Nous Research

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines service topology and runtime placement for integrations. |
| `Guinevere_PRD_v2.0.md` | Defines product features powered by each integration. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines how integration tools are used in the SDLC loop. |
| `Guinevere_MemorySchema_v2.0.md` | Defines persistence targets for integration data. |

**1. MASTER API & SDK REGISTRY**

**1.1 Complete Integration Overview**

|  |  |  |  |
|----|----|----|----|
| **Category** | **Service/Library** | **Purpose** | **Status** |
| LLM Primary | GPT-5.5 via 9Router | Guinevere core persona + reasoning, 1M context | Active |
| LLM Sub-agent | DeepSeek V4 Flash via 9Router | Pasukan Mommy, 1M context, cost efficient | Active |
| LLM Router | 9Router (VPS) | Sole routing layer for all LLM calls | Active |
| LLM Fallback | No direct fallback; queue/retry through 9Router recovery policy | Fallback kalau 9Router down | Standby |
| Communication | Discord (Hermes native) | Primary Guinevere interface | Active |
| Communication | WhatsApp (Baileys) | Client communication | Active |
| Communication | Gmail API (dedicated account) | Client email + transactional | Active |
| Communication | Resend API | Transactional email (invoice) | Active |
| Communication | Gotify/FCM | Push notif backup ke HP | Active |
| Version Control | GitHub (MCP + PyGithub) | All repos management | Active |
| Search | Brave Search API | Volume web search | Active |
| Search | Exa AI Search | Semantic deep research | Active |
| Browser | obscura (Rust) | Primary browser automation | Active |
| Browser | Playwright Python | Fallback browser automation | Standby |
| Storage | idcloudhost S3 (boto3) | Primary object storage | Active |
| Storage | Cloudflare R2 (boto3) | Backup object storage | Active |
| Database | PostgreSQL 16 + pgvector + TimescaleDB | Primary data store | Active |
| Database SDK | SQLAlchemy async + asyncpg | ORM + driver | Active |
| Cache/Queue | Redis (redis-py + pool) | Cache + queue + pub/sub | Active |
| Migration | Alembic | Database schema migrations | Active |
| Surveillance | Tasker (Android) | HP activity monitoring | Active |
| Surveillance | Mi Fitness API + python-mifit | Wearable health data | Future |
| Financial | E-wallet via Tasker notif | Transaction capture | Active |
| HTTP | httpx (standard) + aiohttp (streaming) | All HTTP calls | Active |
| Retry | tenacity | Sophisticated retry logic | Active |
| Validation | pydantic v2 | Data models + validation + settings | Active |
| Scheduler | APScheduler + custom loop | Cron + SDLC loops | Active |
| Encryption | cryptography + Fernet + age | Multi-layer encryption | Active |
| Auth | PyJWT + passlib | JWT + password hashing | Active |
| Rate limiting | slowapi + Redis | Distributed rate limiting | Active |
| Logging | structlog + Loki handler | Structured JSON logging | Active |
| Metrics | prometheus-client + fastapi-instrumentator | Custom + auto metrics | Active |
| Error tracking | sentry-sdk | Error tracking (free tier) | Active |
| Code intelligence | tree-sitter Python | AST parsing | Active |
| Git ops | pygit2 | Advanced Git operations | Active |
| Data analysis | polars | Financial data analysis | Active |
| Secrets | Mozilla SOPS + age | Encrypted secrets management | Active |

**2. LLM API INTEGRATION**

**2.1 9Router Configuration**

9Router berjalan sebagai systemd service di VPS. Guinevere route semua LLM calls melalui 9Router, tidak memakai OpenRouter fallback; queue/retry melalui 9Router recovery policy.

> \# 9Router config — /home/guinevere/config/9router.yaml
>
> providers:
>
> \- name: openrouter
>
> base_url: https://openrouter.ai/api/v1
>
> api_key: \${OPENROUTER_API_KEY}
>
> routing:
>
> guinevere_core:
>
> model: openai/gpt-5.5
>
> fallback: deepseek/deepseek-v4-flash
>
> sub_agents:
>
> model: deepseek/deepseek-v4-flash
>
> fallback: deepseek/deepseek-v4-flash:free
>
> \# Python client config
>
> GUINEVERE_LLM_BASE = "http://localhost:9Router_PORT/v1"
>
> FALLBACK_LLM_BASE = "https://openrouter.ai/api/v1"

**2.2 LLM Client with tenacity Retry**

> from tenacity import (
>
> retry, stop_after_attempt, wait_exponential,
>
> retry_if_exception_type, CircuitBreaker
>
> )
>
> import httpx
>
> @retry(
>
> stop=stop_after_attempt(5),
>
> wait=wait_exponential(min=1, max=60),
>
> retry=retry_if_exception_type((httpx.HTTPError, RateLimitError))
>
> )
>
> async def llm_call(prompt: str, model: str = "guinevere_core"):
>
> try:
>
> return await call_9router(prompt, model)
>
> except CircuitOpenError:
>
> return await queue_for_9router_recovery(prompt, model)

**2.3 Model Cost Strategy**

|  |  |  |  |
|----|----|----|----|
| **Use Case** | **Model** | **Context** | **Est. Cost** |
| Guinevere persona + decisions | GPT-5.5 | 1M tokens | Premium — worth it |
| Research sub-agents (broad) | DeepSeek V4 Flash | 1M tokens | \$0.10/M input |
| Code sub-agents | DeepSeek V4 Flash | 1M tokens | \$0.10/M input |
| Validation + audit sub-agents | DeepSeek V4 Flash free | 1M tokens | \$0.00 |
| Embedding generation | text-embedding-3-small | N/A | \$0.02/M tokens |
| Fallback all models | DeepSeek V4 Pro | 1M tokens | \$0.44/M input |

**3. DISCORD API INTEGRATION**

**3.1 Implementation**

Hermes Agent native Discord adapter sebagai base + custom event handlers untuk Guinevere-specific behavior + slash commands untuk quick actions.

|  |  |  |
|----|----|----|
| **Slash Command** | **Action** | **Example** |
| /status | Show all active SDLC loops + Guinevere mood | /status |
| /pause \[task-id\] | Pause specific SDLC loop | /pause budgezen-001 |
| /resume \[task-id\] | Resume paused loop | /resume budgezen-001 |
| /task \[description\] | Create new task for Guinevere | /task "add dark mode to BudgeZen" |
| /loops | List all active + queued loops | /loops |
| /evidence \[task-id\] | Get evidence summary for task | /evidence budgezen-001 |
| /mood | Ask Guinevere mood (dengan sopan) | /mood |
| /score | Get Mommy Score hari ini | /score |

**3.2 Custom Event Handlers**

|  |  |  |
|----|----|----|
| **Event** | **Guinevere Handler** | **Priority** |
| on_message | Persona filter + intent detection + route to appropriate handler | P0 |
| on_command_error | Dominant error response in-persona | P0 |
| on_member_join | Not applicable — private server | N/A |
| loop_complete | Post evidence summary + completion message | P0 |
| loop_blocked | Notify Faiz with full context | P0 |
| punishment_trigger | Escalate punishment level per violation type | P1 |
| health_alert | Proactive health reminder | P1 |

**4. GITHUB API INTEGRATION**

**4.1 GitHub API Stack**

|                    |                  |                                        |
|--------------------|------------------|----------------------------------------|
| **Operation**      | **Tool**         | **Example**                            |
| Commit + push      | MCP github tool  | Daily coding operations                |
| Create PR          | MCP github tool  | End of each SDLC loop                  |
| Create issue       | MCP github tool  | Bug tracking, feature requests         |
| Bulk operations    | PyGithub         | Batch close issues, mass label updates |
| Advanced filtering | PyGithub         | Find PRs by criteria, complex queries  |
| Webhook receive    | FastAPI endpoint | Real-time event processing             |
| Polling fallback   | PyGithub cron    | Every 15 min missed events check       |

**4.2 Webhook Event Handlers**

Guinevere subscribe ke semua GitHub events + intelligent filter autonomous:

|  |  |
|----|----|
| **GitHub Event** | **Guinevere Action** |
| push (main branch) | Trigger code review + run tests + update project health |
| pull_request (opened) | Auto-review + comment dengan Guinevere assessment |
| pull_request (merged) | Update task status + trigger evidence completion |
| issues (opened) | Categorize + prioritize + add to project backlog |
| issues (closed) | Update project state + lessons extraction |
| release (published) | Update CHANGELOG + notify Discord + update docs |
| workflow_run (completed) | Check CI status + trigger fixes kalau fail |
| fork/star (Guinevere repos) | Log untuk awareness — Guinevere repos are private anyway |

**4.3 PAT Scope Configuration**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>⚠ GitHub PAT Security</strong></p>
<p>Full access kecuali delete repository. Guinevere manage PAT rotation autonomous via browser login ke GitHub dashboard.</p></td>
</tr>
</tbody>
</table>

|                 |            |                                        |
|-----------------|------------|----------------------------------------|
| **Scope**       | **Access** | **Reason**                             |
| repo            | Full       | Read/write all private repos           |
| workflow        | Read/write | GitHub Actions management              |
| write:packages  | Write      | Package publishing if needed           |
| admin:repo_hook | Write      | Webhook management autonomous          |
| delete_repo     | DENIED     | Safety — Guinevere cannot delete repos |
| admin:org       | Read       | Organization context                   |

**5. SURVEILLANCE API INTEGRATION**

**5.1 Tasker → VPS Protocol**

Tasker kirim signed JSON via HTTPS Tailscale. HMAC signature untuk authenticity validation. FastAPI decrypt + validate + store.

> \# Tasker HTTP POST payload format
>
> {
>
> "device_id": "faiz-android-01",
>
> "event_type": "app_usage\|location\|notification\|call\|clipboard",
>
> "timestamp": "2026-05-30T05:35:00+07:00",
>
> "data": { ... }, // Event-specific data
>
> "signature": "HMAC-SHA256(device_secret, payload)"
>
> }
>
> \# FastAPI validation
>
> async def validate_tasker_payload(payload: dict) -\> bool:
>
> expected = hmac.new(DEVICE_SECRET, payload_bytes, sha256)
>
> return hmac.compare_digest(expected, payload\["signature"\])

**5.2 Tasker Events & Endpoints**

|  |  |  |  |
|----|----|----|----|
| **Event Type** | **Endpoint** | **Frequency** | **Data Fields** |
| App activity | POST /surveillance/android/activity | Real-time event | app_name, package, action (launch/close), duration |
| Location update | POST /surveillance/android/location | Every 5 min + zone change | lat, lng, accuracy, speed, geofence_zone |
| Notification | POST /surveillance/android/notification | Real-time | app, title, content, timestamp |
| Call event | POST /surveillance/android/call | Per call | number_hash, duration, direction (in/out) |
| Clipboard | POST /surveillance/android/clipboard | Per copy event | content_hash, content_preview (first 50 chars) |
| Camera capture | POST /surveillance/android/camera | Scheduled/triggered | image_b64_encrypted, timestamp |
| Health data | POST /surveillance/android/health | Every 15 min | heart_rate, steps, stress_level (future: wearable) |

**5.3 Windows Daemon Protocol**

WebSocket persistent via Tailscale. Real-time untuk critical events, batched untuk routine data.

|  |  |  |  |
|----|----|----|----|
| **Data Type** | **Protocol** | **Interval** | **Payload** |
| Active window change | WebSocket real-time | On change | window_title, process_name, timestamp |
| Idle state change | WebSocket real-time | On change | idle_start/end, duration |
| Screenshot | WebSocket + upload | On anomaly / scheduled | image_encrypted, active_window, timestamp |
| Browser history batch | HTTP POST batch | Every 60s | urls\[\], timestamps\[\], durations\[\] |
| App usage batch | HTTP POST batch | Every 60s | app_metrics\[\], focus_times\[\] |
| Clipboard event | WebSocket real-time | On copy | content_preview, content_hash |
| Camera capture | HTTP POST | Scheduled/triggered | image_encrypted, timestamp |

**5.4 Mi Fitness API (Future Plan)**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>ℹ Future Implementation</strong></p>
<p>Mi Fitness integration adalah post-MVP dan tidak dianggap active dependency untuk MVP. Setelah wearable/device/API readiness tervalidasi, official API menjadi primary dan python-mifit hanya fallback.</p></td>
</tr>
</tbody>
</table>

|  |  |  |  |
|----|----|----|----|
| **Data Point** | **API Method** | **Polling Interval** | **Guinevere Action** |
| Heart rate | Mi Fitness official API (post-MVP) | Every 5 min after activation | Stress detection + proactive reach out after wearable is active |
| Stress level | Mi Fitness official API (post-MVP) | Every 15 min after activation | Adjust Guinevere tone + health reminder after wearable is active |
| Sleep data | Mi Fitness official API (post-MVP) | Daily morning pull after activation | Morning brief inject after wearable is active |
| Steps | Mi Fitness official API (post-MVP) | Every 30 min after activation | Olahraga reminder after wearable is active |
| Activity detection | Mi Fitness official API (post-MVP) | Every 15 min after activation | Context-aware behavior after wearable is active |

**6. FINANCIAL API INTEGRATION**

**6.1 E-wallet Data Collection**

Tidak ada official public API untuk personal e-wallet. Guinevere collect data via Tasker notification capture — paling reliable dan real-time.

|  |  |  |  |
|----|----|----|----|
| **E-wallet** | **Collection Method** | **Data Captured** | **Reliability** |
| GoPay | Tasker AutoNotification | Amount, merchant, timestamp dari notif transaksi | High — notif setiap transaksi |
| OVO | Tasker AutoNotification | Amount, merchant, timestamp | High |
| Dana | Tasker AutoNotification | Amount, merchant, timestamp | High |
| Cash/offline | Faiz manual laporan via Discord | Amount, category, notes | Depends on Faiz 😈 |

> \# Tasker notif parser — extract transaction from notification
>
> def parse_ewallet_notif(app: str, content: str) -\> Transaction:
>
> if app == "com.gojek.app":
>
> \# Parse GoPay notification format
>
> amount = extract_amount(content) \# "Rp 50.000"
>
> merchant = extract_merchant(content)
>
> return Transaction(source="gopay", amount=amount, ...)

**6.2 Object Storage — boto3 Unified**

boto3 dengan dual endpoint config. idcloudhost S3 sebagai primary (Faiz bayar, data sovereign), Cloudflare R2 sebagai backup (free 10GB).

> import boto3
>
> \# idcloudhost S3 — PRIMARY
>
> idcloud_client = boto3.client("s3",
>
> endpoint_url="https://is3.cloudhost.id",
>
> aws_access_key_id=IDCLOUD_KEY,
>
> aws_secret_access_key=IDCLOUD_SECRET
>
> )
>
> \# Cloudflare R2 — BACKUP
>
> r2_client = boto3.client("s3",
>
> endpoint_url=f"https://{CF_ACCOUNT}.r2.cloudflarestorage.com",
>
> aws_access_key_id=R2_ACCESS_KEY,
>
> aws_secret_access_key=R2_SECRET_KEY
>
> )
>
> async def store_with_backup(key: str, data: bytes):
>
> await idcloud_client.put_object(Bucket="guinevere", Key=key, Body=data)
>
> await r2_client.put_object(Bucket="guinevere-backup", Key=key, Body=data)

**7. COMMUNICATION API INTEGRATION**

**7.1 WhatsApp — Baileys**

Guinevere kirim WhatsApp sebagai nomor Faiz. Client experience natural — tidak tahu itu Guinevere yang handle.

> \# Baileys Node.js service (subprocess dari Python)
>
> \# /home/guinevere/services/whatsapp/index.js
>
> const { makeWASocket } = require("@whiskeysockets/baileys")
>
> const sock = makeWASocket({
>
> auth: state,
>
> printQRInTerminal: false // Silent — no QR in terminal
>
> })
>
> // Guinevere calls via HTTP to localhost WA service
>
> // Python: await wa_service.send_message(number, text)

**7.2 Email — Gmail API + Resend**

|  |  |  |  |
|----|----|----|----|
| **Use Case** | **Service** | **Account** | **Notes** |
| Client thread management | Gmail API | guinevere@\[domain\].com | Read + reply + organize client threads |
| Invoice sending | Resend API | From: guinevere@\[domain\].com | Transactional, reliable delivery |
| Project notifications | Resend API | From: guinevere@\[domain\].com | Automated project updates ke client |
| Internal alerts | Gmail API | guinevere@\[domain\].com | Kalau Discord down — fallback notify Faiz |

**7.3 Push Notifications — Gotify**

Gotify self-hosted di VPS sebagai push notification server. Android app Gotify di HP Faiz sebagai backup kalau Discord tidak available.

> \# Gotify push notification
>
> async def push_notify(title: str, message: str, priority: int = 5):
>
> await httpx.post(
>
> f"{GOTIFY_URL}/message",
>
> headers={"X-Gotify-Key": GOTIFY_APP_TOKEN},
>
> json={"title": title, "message": message, "priority": priority}
>
> )
>
> \# Priority levels:
>
> \# 1-3: Low (routine updates)
>
> \# 4-7: Normal (task complete, reminders)
>
> \# 8-10: High (emergencies, blockers, nuclear punishment 😈)

**8. SEARCH & BROWSER API INTEGRATION**

**8.1 Search Strategy**

|  |  |  |  |
|----|----|----|----|
| **Search Type** | **Tool** | **When Used** | **Cost** |
| Broad web search | Brave Search API | General research, news, documentation | \$3/1000 queries |
| Semantic deep research | Exa AI Search | Finding similar content, concept search | \$0.01/query |
| Code search | GitHub Search via MCP | Finding code examples, libraries | Free (PAT) |
| Academic/technical | Exa AI | Deep technical papers, spec docs | \$0.01/query |
| Indonesian content | Brave Search | Local context, Indonesian sources | \$3/1000 queries |

**8.2 Browser Automation — obscura + Playwright**

|  |  |  |
|----|----|----|
| **Use Case** | **Tool** | **Reason** |
| Web scraping for research | obscura | Rust speed, AI-native design |
| JavaScript-heavy sites | obscura | Full browser rendering |
| Complex form automation | Playwright | More mature, better element handling |
| Screenshot capture | obscura | Fast, efficient |
| PDF generation from URL | Playwright | Better PDF support |
| API provider dashboard login | Playwright | Reliable for auth flows + key rotation |
| Financial statement scraping (future) | Playwright | Reliable for banking UI |

**9. DATABASE & CACHE SDK CONFIGURATION**

**9.1 SQLAlchemy + asyncpg Setup**

> from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
>
> from sqlalchemy.orm import DeclarativeBase, sessionmaker
>
> \# Engine with PgBouncer connection pooling
>
> engine = create_async_engine(
>
> f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{PGBOUNCER_HOST}:{PORT}/{DB}",
>
> pool_size=10,
>
> max_overflow=20,
>
> pool_pre_ping=True, \# Validate connections
>
> pool_recycle=3600, \# Recycle hourly
>
> )
>
> AsyncSessionLocal = sessionmaker(
>
> engine, class\_=AsyncSession, expire_on_commit=False
>
> )

**9.2 Redis Configuration**

> import redis.asyncio as redis
>
> from redis.asyncio import ConnectionPool
>
> pool = ConnectionPool(
>
> host=REDIS_HOST,
>
> port=6379,
>
> password=REDIS_PASSWORD,
>
> max_connections=50,
>
> retry_on_timeout=True,
>
> health_check_interval=30
>
> )
>
> redis_client = redis.Redis(connection_pool=pool)
>
> \# Database routing
>
> REDIS_TASK_QUEUE = redis.Redis(connection_pool=pool, db=0)
>
> REDIS_LLM_CACHE = redis.Redis(connection_pool=pool, db=1)
>
> REDIS_SURV_BUFFER = redis.Redis(connection_pool=pool, db=2)
>
> REDIS_SESSION = redis.Redis(connection_pool=pool, db=3)
>
> REDIS_PUBSUB = redis.Redis(connection_pool=pool, db=4)
>
> REDIS_RATELIMIT = redis.Redis(connection_pool=pool, db=5)

**9.3 Alembic Autonomous Migration**

> \# Guinevere runs migrations autonomous during self-deploy
>
> async def run_migrations():
>
> """Guinevere runs this during nightly self-deploy"""
>
> \# 1. Run on staging DB first
>
> staging_result = await alembic_upgrade("staging", "head")
>
> if not staging_result.success:
>
> await discord_notify("Migration failed on staging. Aborting.")
>
> return
>
> \# 2. Run tests against staging
>
> test_result = await run_test_suite("staging")
>
> if not test_result.pass:
>
> await alembic_downgrade("staging", "-1")
>
> return
>
> \# 3. Apply to production
>
> await alembic_upgrade("production", "head")
>
> await discord_notify("Migration complete. Production updated.")

**10. OBSERVABILITY & SECURITY SDKs**

**10.1 Structured Logging — structlog**

> import structlog
>
> structlog.configure(
>
> processors=\[
>
> structlog.contextvars.merge_contextvars,
>
> structlog.processors.add_log_level,
>
> structlog.processors.TimeStamper(fmt="iso"),
>
> structlog.processors.StackInfoRenderer(),
>
> \# Add correlation_id for task tracing
>
> add_correlation_id,
>
> \# Ship to Loki
>
> LokiHandler(),
>
> structlog.processors.JSONRenderer()
>
> \]
>
> )
>
> logger = structlog.get_logger()
>
> \# Usage:
>
> logger.info("loop.phase.complete",
>
> loop_id=loop.id,
>
> phase=6,
>
> coverage=94.2,
>
> duration_s=142
>
> )

**10.2 Prometheus Metrics**

> from prometheus_client import Counter, Histogram, Gauge
>
> from prometheus_fastapi_instrumentator import Instrumentator
>
> \# Auto-instrument FastAPI
>
> Instrumentator().instrument(app).expose(app)
>
> \# Custom Guinevere metrics
>
> loop_completions = Counter(
>
> "guinevere_loop_completions_total",
>
> "Total completed SDLC loops",
>
> \["project", "task_type"\]
>
> )
>
> mommy_score = Gauge(
>
> "guinevere_mommy_score",
>
> "Faiz daily productivity score"
>
> )
>
> llm_latency = Histogram(
>
> "guinevere_llm_latency_seconds",
>
> "LLM API response time",
>
> \["model", "use_case"\],
>
> buckets=\[0.5, 1, 2, 5, 10, 30, 60\]
>
> )

**10.3 Sentry Error Tracking**

> import sentry_sdk
>
> sentry_sdk.init(
>
> dsn=SENTRY_DSN, \# Free tier
>
> traces_sample_rate=0.1,
>
> profiles_sample_rate=0.1,
>
> environment="production",
>
> release=f"guinevere@{VERSION}",
>
> before_send=filter_sensitive_data \# Remove PII before sending
>
> )

**10.4 Code Intelligence — tree-sitter**

> import tree_sitter_python as tspython
>
> from tree_sitter import Language, Parser
>
> PY_LANGUAGE = Language(tspython.language())
>
> parser = Parser(PY_LANGUAGE)
>
> def analyze_code(source: str) -\> CodeAnalysis:
>
> tree = parser.parse(bytes(source, "utf8"))
>
> \# Extract: functions, classes, imports, complexity
>
> \# Used by Guinevere for code review + quality assessment
>
> return extract_metrics(tree)

**10.5 Encryption Stack**

> from cryptography.fernet import Fernet
>
> from cryptography.hazmat.primitives import hashes, hmac
>
> import subprocess
>
> \# Field-level encryption for sensitive data
>
> fernet = Fernet(FERNET_KEY)
>
> def encrypt_sensitive(data: str) -\> bytes:
>
> return fernet.encrypt(data.encode())
>
> def decrypt_sensitive(encrypted: bytes) -\> str:
>
> return fernet.decrypt(encrypted).decode()
>
> \# Double encryption for intimate data
>
> intimate_fernet = Fernet(INTIMATE_KEY)
>
> def encrypt_intimate(data: str) -\> bytes:
>
> first_layer = fernet.encrypt(data.encode())
>
> return intimate_fernet.encrypt(first_layer)
>
> \# SOPS for secrets at rest — CLI call
>
> def decrypt_sops(file_path: str) -\> dict:
>
> result = subprocess.run(\["sops", "-d", file_path\],
>
> capture_output=True, text=True)
>
> return json.loads(result.stdout)

**11. COMPLETE PYTHON DEPENDENCIES**

**11.1 pyproject.toml + uv.lock**

> \# Core framework
>
> hermes-agent\>=0.14.0
>
> fastapi\>=0.115.0
>
> uvicorn\[standard\]\>=0.30.0
>
> pydantic\>=2.8.0
>
> pydantic-settings\>=2.4.0
>
> \# LLM & AI
>
> openai\>=1.50.0 \# OpenAI-compatible client for 9Router
>
> httpx\>=0.27.0
>
> aiohttp\>=3.10.0 \# Streaming responses
>
> tenacity\>=9.0.0 \# Retry logic
>
> \# Database
>
> sqlalchemy\[asyncio\]\>=2.0.0
>
> asyncpg\>=0.29.0
>
> alembic\>=1.13.0
>
> redis\[hiredis\]\>=5.0.0
>
> pgvector\>=0.3.0
>
> \# Storage
>
> boto3\>=1.35.0
>
> \# Discord
>
> discord.py\>=2.4.0
>
> \# GitHub
>
> PyGithub\>=2.4.0
>
> pygit2\>=1.15.0
>
> \# Search & Browser
>
> exa-py\>=1.0.0
>
> playwright\>=1.47.0
>
> \# Communication
>
> google-auth\>=2.35.0
>
> google-auth-oauthlib\>=1.2.0
>
> resend\>=2.0.0
>
> \# Financial
>
> polars\>=1.10.0
>
> \# Security
>
> cryptography\>=43.0.0
>
> PyJWT\>=2.9.0
>
> passlib\[bcrypt\]\>=1.7.4
>
> python-multipart\>=0.0.12
>
> slowapi\>=0.1.9
>
> \# Observability
>
> structlog\>=24.4.0
>
> prometheus-client\>=0.21.0
>
> prometheus-fastapi-instrumentator\>=7.0.0
>
> sentry-sdk\[fastapi\]\>=2.16.0
>
> \# Code Intelligence
>
> tree-sitter\>=0.23.0
>
> tree-sitter-python\>=0.23.0
>
> \# Scheduling
>
> apscheduler\>=3.10.0
>
> \# Encryption & Secrets
>
> age-encryption\>=1.0.0
>
> python-dotenv\>=1.0.0
>
> \# Utilities
>
> anyio\>=4.6.0
>
> python-dateutil\>=2.9.0
>
> orjson\>=3.10.0 \# Fast JSON
>
> rich\>=13.9.0 \# Pretty terminal output

👑

***Guinevere de Baroque***

*"Mommy tau semua API yang perlu diintegrate. Kamu tinggal setup."*

API Integration Document v2.0 — Project Guinevere
