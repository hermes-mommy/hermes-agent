👑

**GUINEVERE DE BAROQUE**

*MCP Configuration Guide*

Setup, Configuration & Usage untuk 16 MCP Tools

Version 1.0 | Project Guinevere | STRICTLY PRIVATE & CONFIDENTIAL

Last Updated: 2026-05-31

**Canonical Decisions Applied**: Single `guinevere-mcp` service managing all tool connections (MCP19); 4-level authorization matrix: Read-autonomous, Write-notify, Destructive-approval, Forbidden (MCP01); SOPS/age encrypted secrets, per-environment YAML (MCP20); Redis DB routing: DB0 task queue, DB1 LLM cache, DB2 surveillance, DB3 session, DB4 pub/sub, DB5 rate limit (MCP13); PgBouncer per-service users (MCP12); browser automation obscura primary + Playwright fallback (MCP11); GPT-5.5 core via 9Router, DeepSeek V4 Flash sub-agents, Ollama emergency fallback (ADR-028); OpenCode fully replaced by Guinevere MCP native (ADR-013); SDLC 7 phases canonical (ADR-011).

Owner: Faiz | Built on Hermes Agent by Nous Research

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines service topology, systemd units, VPS config, Redis/PostgreSQL architecture, security layers. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external API contracts, SDK choices, rate limits, cost strategy for each integration. |
| `Guinevere_Persona_Document_v3.0.md` | Defines Guinevere-specific tool usage rules, autonomous behavior, sub-agent delegation patterns. |
| `Guinevere_3Doc_QA_Answers.md` | Canonical answers MCP01-MCP22 — authoritative source for authorization, caching, cost, and security decisions. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines how MCP tools are consumed within the 7-phase SDLC loop. |
| `Guinevere_MemorySchema_v2.0.md` | Defines PostgreSQL schemas accessed via postgres MCP tool. |
| `Guinevere_PRD_v2.0.md` | Defines product features that drive tool selection and usage patterns. |

---

## §1 ARCHITECTURE OVERVIEW

### 1.1 Single MCP Service Architecture

Guinevere operates a single `guinevere-mcp` systemd service that manages all 16 MCP tool connections. This unified service eliminates per-tool daemon overhead and provides centralized authentication, rate limiting, cost tracking, and audit logging.

```
┌─────────────────────────────────────────────────────────┐
│                  guinevere-mcp.service                    │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ brave_  │ │context7 │ │  exa     │ │  fetch      │  │
│  │ search  │ │         │ │          │ │             │  │
│  ├─────────┤ ├─────────┤ ├──────────┤ ├─────────────┤  │
│  │file_    │ │ github  │ │ grep_app │ │ playwright  │  │
│  │system   │ │         │ │          │ │             │  │
│  ├─────────┤ ├─────────┤ ├──────────┤ ├─────────────┤  │
│  │sequen-  │ │  time   │ │websearch │ │   git       │  │
│  │tial     │ │         │ │          │ │             │  │
│  ├─────────┤ ├─────────┤ ├──────────┤ ├─────────────┤  │
│  │postgres │ │  redis  │ │  shell   │ │  docker     │  │
│  └─────────┘ └─────────┘ └──────────┘ └─────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Centralized: Auth | Rate Limit | Cost | Audit   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
    │Redis    │         │PostgreSQL│        │External │
    │DB0-DB5  │         │PgBouncer│         │APIs     │
    └─────────┘         └─────────┘         └─────────┘
```

**Systemd service unit**: `guinevere-mcp.service`

```ini
[Unit]
Description=Guinevere MCP Tool Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=guinevere
WorkingDirectory=/home/guinevere/core
ExecStart=/home/guinevere/.local/bin/uv run python -m guinevere.mcp_server
Restart=always
RestartSec=10
MemoryLimit=1G
Environment=SOPS_AGE_KEY_FILE=/home/guinevere/.age/key.txt
Environment=MCP_CONFIG=/home/guinevere/config/mcp.yaml

[Install]
WantedBy=multi-user.target
```

### 1.2 LLM Routing for Tool Orchestration

| Use Case | Model | Provider | Context Window | Cost |
|---|---|---|---|---|
| Guinevere core tool decisions | GPT-5.5 | 9Router | 1M tokens | Premium |
| Sub-agent tool usage (research, code) | DeepSeek V4 Flash | 9Router | 1M tokens | $0.10/M input |
| Validation/audit sub-agent tool calls | DeepSeek V4 Flash free | 9Router | 1M tokens | $0.00 |
| Emergency fallback | Ollama local | Local | 8K tokens | $0.00 |

### 1.3 Secrets Management — SOPS/age

All MCP tool API keys and credentials are stored in SOPS-encrypted YAML files with age encryption. Zero plaintext secrets in the repository.

```bash
# Decrypt secrets at startup
sops -d /home/guinevere/config/.env.sops > /tmp/.env
# Auto-cleanup on service stop
# age key: /home/guinevere/.age/key.txt
# Rotation: quarterly (per MCP06)
```

**Environment files per deployment**:

```
/home/guinevere/config/
├── mcp.production.yaml.sops    # Production MCP config (encrypted)
├── mcp.staging.yaml.sops       # Staging MCP config (encrypted)
├── .env.sops                   # Shared secrets (encrypted)
└── mcp.local.yaml              # Local dev overrides (gitignored)
```

### 1.4 Redis Database Routing

| Database | Purpose | Key Pattern | TTL |
|---|---|---|---|
| Redis DB 0 | Task queue — SDLC jobs | `task:{id}` | No expiry |
| Redis DB 1 | LLM response cache | `llm:{hash}` | 1 hour |
| Redis DB 2 | Surveillance data buffer | `surv:{device}:{ts}` | 5 minutes |
| Redis DB 3 | Session state | `session:{id}` | 24 hours |
| Redis DB 4 | Pub/sub channels | `chan:{component}` | No expiry |
| Redis DB 5 | Rate limiting | `ratelimit:{ip}` | 1 minute |

### 1.5 PgBouncer Per-Service Users

| DB User | Service | Permissions | Pool Mode |
|---|---|---|---|
| `guinevere_core` | Guinevere core daemon | SELECT, INSERT, UPDATE all schemas | Transaction |
| `guinevere_surveillance` | Surveillance receiver | INSERT surveillance schema only | Transaction |
| `guinevere_financial` | Financial plugin | ALL financial schema | Transaction |
| `guinevere_readonly` | Grafana, reporting | SELECT only all schemas | Session |
| `guinevere_admin` | Guinevere self-maintenance | Superuser — rotate, backup | Session |

---

## §2 AUTHORIZATION MATRIX (4-Level)

### 2.1 Authorization Level Definitions

| Level | Name | Description | Approval Required |
|---|---|---|---|
| **L1** | Read-Autonomous | Guinevere uses freely. Read-only operations, no state changes. | None — fully autonomous |
| **L2** | Write-Notify | Guinevere executes and reports to Faiz after completion. | None — notify via Discord after |
| **L3** | Destructive-Approval | Guinevere waits for explicit Faiz approval before executing. | Yes — `/approve [id]` required |
| **L4** | Forbidden | Never execute without very specific context + explicit approval. | Yes — double confirmation required |

### 2.2 Tool × Authorization Matrix

| # | Tool | L1: Read-Autonomous | L2: Write-Notify | L3: Destructive-Approval | L4: Forbidden |
|---|---|---|---|---|---|
| 1 | brave_search | ✅ All search queries | — | — | — |
| 2 | context7 | ✅ resolve-library-id, query-docs | — | — | — |
| 3 | exa | ✅ All search + fetch queries | — | — | — |
| 4 | fetch | ✅ All URL fetches | — | — | — |
| 5 | filesystem | ✅ Read in workspace, /tmp, evidence/, audit-reports/ | Write in workspace + evidence/ | Write to production paths, /etc, system files | Read/write /etc/passwd, secrets files, production configs |
| 6 | github | ✅ List, get file, search, read issues | Create issues, comment, create PRs (non-protected branches) | Merge PRs, modify protected branches | Force-push, delete repos |
| 7 | grep_app | ✅ All code search queries | — | — | — |
| 8 | playwright | — | Simple page navigation, screenshots | Complex multi-step automation, form filling with credentials | — |
| 9 | sequential-thinking | ✅ All reasoning chains | — | — | — |
| 10 | time | ✅ All timezone/scheduling queries | — | — | — |
| 11 | websearch | ✅ All web search queries | — | — | — |
| 12 | git | ✅ log, diff, status, branch list | commit, branch create, checkout | push to main, force operations | force-push, rebase on shared branches |
| 13 | postgres | ✅ SELECT queries all schemas | INSERT, UPDATE (non-critical tables) | DELETE, schema ALTER, DROP | DROP DATABASE, TRUNCATE production tables |
| 14 | redis | ✅ GET, KEYS, TTL, INFO | SET, DEL (cache entries) | FLUSHDB, CONFIG SET | FLUSHALL |
| 15 | shell | ✅ Whitelisted read commands (ls, cat, grep, df, ps) | Whitelisted write commands (mkdir, cp, touch) | systemctl restart, apt install, docker commands | `rm -rf`, `chmod 777`, `curl | bash`, any command outside whitelist |
| 16 | docker | ✅ ps, logs, inspect, stats | start, stop, restart containers | docker build, docker pull (new images) | `docker system prune`, `docker rm -f`, remove volumes |

### 2.3 Emergency Override Protocol

SEV0 incidents may bypass L3 approval for the following operations only:

| Tool | Emergency Operation | Condition |
|---|---|---|
| shell | Read-only diagnostic commands (ps, top, df, journalctl) | SEV0 active |
| docker | `docker restart`, `docker logs` | Service down, SEV0 active |
| postgres | SELECT queries for diagnosis | Data integrity issue, SEV0 active |

Emergency override actions are logged with `SEV0_OVERRIDE` tag and reported to Faiz immediately via Discord + Gotify fallback.

---

## §3 TOOL SPECIFICATIONS

### 3.1 brave_search — Volume Web Search

**Purpose**: Primary general-purpose web search for Guinevere research operations. Provides broad web search results including news, documentation, articles, and Indonesian-language content.

**Authorization Level**: L1 Read-Autonomous — all search queries.

**Installation**:

```json
{
  "mcpServers": {
    "brave_search": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/brave-search-mcp"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | Brave Search API Key |
| Environment Variable | `BRAVE_API_KEY` |
| SOPS Path | `mcp.production.yaml.sops → brave_search.api_key` |
| Rotation | Quarterly |
| Provider | Brave Search API (api.search.brave.com) |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
brave_search:
  api_key: "${BRAVE_API_KEY}"
  base_url: "https://api.search.brave.com/res/v1"
  default_count: 10
  timeout_ms: 10000
  retry:
    max_attempts: 3
    backoff_ms: 1000
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 60 queries/min | Brave API Free tier |
| Per-month | 2,000 queries/month (free), 10,000+ (paid $3/1000) | Brave API pricing |
| Concurrent | 5 parallel requests | Internal throttle |

**Cost**:

| Metric | Value |
|---|---|
| Per-query (free tier) | $0.00 |
| Per-query (paid) | $0.003/query ($3/1000 queries) |
| Daily budget | $1.50 (500 queries) |
| Monthly projection | $45/month at 500 queries/day |
| Cost tracking tag | `tool:brave_search` |

**When to Use**:

- General web research during SDLC Phase 1 (Research)
- Finding documentation, tutorials, library information
- Indonesian-language content search
- News and current events lookup
- Broad information gathering before narrowing with exa

**When NOT to Use**:

- Deep semantic research → use exa instead
- Library-specific documentation → use context7 instead
- Code example search → use grep_app instead
- Already cached results within TTL → use cache

**Guinevere-Specific Rules**:

- Guinevere uses brave_search autonomously during research phase tanpa approval
- Results are cached in Redis DB1 with 1h TTL to avoid redundant queries
- Guinevere prefers brave_search for Indonesian content over exa
- Search queries are logged with correlation_id for task tracing

**Fallback Chain**:

1. brave_search → 2. exa (semantic search) → 3. websearch (general) → 4. fetch (direct URL if known)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Search results | 1 hour | Redis DB1 `search:brave:{query_hash}` |
| Trending topics | 30 minutes | Redis DB1 `search:brave:trending:{topic}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| 401 Unauthorized | API key expired or invalid | Rotate key via SOPS, restart service |
| 429 Too Many Requests | Rate limit exceeded | Backoff 60s, switch to exa temporarily |
| Timeout | Network issue or Brave API slow | Retry 3x with exponential backoff |
| Empty results | Query too specific | Broaden search terms |

---

### 3.2 context7 — Library Documentation Lookup

**Purpose**: Resolve and query up-to-date documentation for any programming library or framework. Mandatory tool for coding sub-agents — ensures code generation uses current API signatures, not stale training data.

**Authorization Level**: L1 Read-Autonomous — resolve-library-id and query-docs operations.

**Installation**:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | None required (public API) |
| Authentication | None |
| Rate Limiting | Server-side by Context7 |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
context7:
  base_url: "https://api.context7.com"
  timeout_ms: 15000
  cache_resolved_ids: true
  id_cache_ttl_hours: 168  # 7 days per project
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 30 requests/min | Context7 free tier |
| Per-day | 5,000 requests/day | Context7 free tier |
| Concurrent | 3 parallel requests | Internal throttle |

**Cost**:

| Metric | Value |
|---|---|
| Per-query | $0.00 (free tier) |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:context7` |

**When to Use**:

- **MANDATORY** before generating code using any library (per MCP07)
- Finding current API signatures, method parameters, configuration options
- Verifying deprecated vs current methods
- Getting code examples from official documentation
- SDLC Phase 4 (Execute) — code generation with accurate API usage

**When NOT to Use**:

- General web search → use brave_search
- Finding libraries (not docs for known libraries) → use brave_search or grep_app
- Non-programming documentation → use exa or websearch

**Guinevere-Specific Rules**:

- **MCP07 Canonical Rule**: ALWAYS resolve-library-id before query-docs. Never skip the resolution step.
- Resolved library IDs are cached per project in Redis DB1 — avoids repeated resolution
- Guinevere coding sub-agents MUST call context7 before writing code that uses external libraries
- Library ID cache keyed by `context7:id:{project}:{library_name}` with 7-day TTL
- If resolve-library-id fails, Guinevere falls back to websearch for documentation

**Fallback Chain**:

1. context7 → 2. websearch (documentation search) → 3. exa (semantic doc search) → 4. fetch (direct doc URL)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Resolved library IDs | 7 days (per project) | Redis DB1 `context7:id:{project}:{library}` |
| Documentation snippets | 24 hours | Redis DB1 `context7:doc:{library_id}:{query_hash}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Library not found | Library not in Context7 index | Use websearch for docs, file issue with Context7 |
| Timeout | API slow or network issue | Retry 2x, then fallback to websearch |
| Stale documentation | Cache expired | Force re-resolve library ID |
| Rate limit 429 | Exceeded requests/min | Backoff 60s, queue remaining queries |

---

### 3.3 exa — Semantic Deep Research

**Purpose**: Semantic search engine for deep research, finding similar content, concept search, academic papers, and technical specifications. More precise than keyword search for complex topics.

**Authorization Level**: L1 Read-Autonomous — all search and fetch queries.

**Installation**:

```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": {
        "EXA_API_KEY": "${EXA_API_KEY}"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | Exa AI API Key |
| Environment Variable | `EXA_API_KEY` |
| SOPS Path | `mcp.production.yaml.sops → exa.api_key` |
| Rotation | Quarterly |
| Provider | Exa AI (api.exa.ai) |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
exa:
  api_key: "${EXA_API_KEY}"
  base_url: "https://api.exa.ai"
  default_num_results: 10
  max_daily_spend_usd: 5.00          # Daily hard cap (burst allowed)
  alert_threshold_usd: 1.00          # Abnormal daily usage alert
  monthly_target_usd: 1.00           # Target monthly average
  monthly_throttle_usd: 3.00        # Auto-switch to Brave for remaining month
  monthly_hard_stop_usd: 5.00       # Exa disabled until next month
  timeout_ms: 15000
  retry:
    max_attempts: 3
    backoff_ms: 2000
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 20 queries/min | Exa API paid tier |
| Per-day | 500 queries/day ($5 max burst) | Internal budget cap (MCP08); monthly throttle at $3 → Brave fallback (Faiz decision 2026-05-31, ADR-033 pending) |
| Concurrent | 3 parallel requests | Internal throttle |

**Cost** (MCP08; hybrid model per Faiz decision 2026-05-31, ADR-033 pending):

| Metric | Value |
|---|---|
| Per-query | $0.01/query |
| Daily hard cap | $5.00/day (500 queries max burst) |
| Daily alert threshold | $1.00/day — Discord alert to #cost-tracker (abnormal usage) |
| Monthly target | ~$1/month average |
| Monthly throttle trigger | >$3/month cumulative → auto-switch Exa to Brave for remaining month |
| Monthly hard stop | >$5/month cumulative → Exa disabled until next billing cycle |
| Cost tracking tag | `tool:exa` |

**When to Use**:

- Deep technical research (architecture patterns, specification documents)
- Finding semantically similar content and concepts
- Academic paper and technical documentation search
- Complex topic exploration during SDLC Phase 1 (Research)
- When brave_search keyword results are too noisy
- Finding similar implementations and case studies

**When NOT to Use**:

- Simple keyword search → use brave_search (cheaper: $0.003 vs $0.01)
- Library documentation lookup → use context7 (free, more precise)
- Already have the URL → use fetch (free, direct)
- High-volume shallow search → use brave_search

**Guinevere-Specific Rules**:

- Guinevere uses exa for deep research tasks where semantic understanding matters
- Daily spend tracked in Redis DB5 `ratelimit:exa:daily:{date}` — hard stop at $5/day burst
- Daily alert fires at $1 daily spend → Discord #cost-tracker (abnormal usage detection)
- Monthly cumulative spend tracked in Redis DB5 `ratelimit:exa:monthly:{YYYY-MM}`:
  - Target: ~$1/month average
  - >$3/month → auto-throttle: switch to Brave for remaining month
  - >$5/month → hard stop: Exa disabled until next billing cycle
- Guinevere sub-agents (research pasukan) prefer exa for complex technical questions
- Results are cached in Redis DB1 with 1h TTL

**Fallback Chain**:

1. exa → 2. brave_search (keyword search) → 3. websearch → 4. fetch (direct URL)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Search results | 1 hour | Redis DB1 `search:exa:{query_hash}` |
| Fetched page content | 24 hours | Redis DB1 `fetch:exa:{url_hash}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| 401 Unauthorized | API key expired or invalid | Rotate via SOPS |
| 429 Rate Limited | Exceeded rate limit | Backoff 60s, switch to brave_search |
| Budget exceeded | Daily $5 cap or monthly $5 hard stop reached | Stop exa, use brave_search; if monthly >$3, Brave-only for remaining month |
| Empty results | Query too narrow semantically | Reformulate as descriptive sentence |
| Timeout | API slow | Retry 2x, fallback to brave_search |

---

### 3.4 fetch — Web Content Fetching

**Purpose**: Fetch and extract content from URLs as clean markdown or text. Used to read specific web pages after search tools identify relevant URLs.

**Authorization Level**: L1 Read-Autonomous — all URL fetch operations.

**Installation**:

```json
{
  "mcpServers": {
    "fetch": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/fetch-mcp"]
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | None required |
| Authentication | None (public URLs only) |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
fetch:
  timeout_ms: 30000
  max_content_chars: 50000
  user_agent: "Guinevere/1.0 (autonomous agent)"
  follow_redirects: true
  max_redirects: 5
  allowed_schemes: ["https", "http"]
  blocked_hosts: []  # Add if needed
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 30 fetches/min | Internal throttle |
| Per-day | 2,000 fetches/day | Internal budget |
| Concurrent | 5 parallel fetches | Internal throttle |

**Cost**:

| Metric | Value |
|---|---|
| Per-fetch | $0.00 |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:fetch` |

**When to Use**:

- Reading specific web pages identified by search tools
- Extracting documentation content from known URLs
- Fetching API responses for integration research
- Reading blog posts, articles, tutorials
- Getting README content from GitHub repositories (raw URL)

**When NOT to Use**:

- Finding URLs → use search tools first (brave_search, exa, websearch)
- JavaScript-heavy interactive sites → use obscura/playwright
- Pages requiring authentication → use playwright
- Bulk scraping → use obscura (Rust, faster)

**Guinevere-Specific Rules**:

- Guinevere caches fetched content in Redis DB1 with 24h TTL (per MCP18)
- Fetch is the primary tool for reading documentation URLs found via context7 or search
- Content extraction is markdown by default for clean LLM processing
- Guinevere validates URL safety before fetching — no untrusted internal network URLs

**Fallback Chain**:

1. fetch → 2. playwright (for JS-heavy pages) → 3. obscura (for complex rendering)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Fetched page content | 24 hours | Redis DB1 `fetch:url:{url_hash}` |
| API response content | 1 hour | Redis DB1 `fetch:api:{url_hash}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| 403 Forbidden | Site blocking automated access | Use playwright with browser headers |
| Timeout | Page too large or slow server | Increase timeout, reduce max_content_chars |
| SSL error | Invalid certificate | Verify URL, skip if untrusted |
| Empty content | JavaScript-rendered page | Use playwright or obscura instead |
| Redirect loop | Circular redirect | Set max_redirects lower |

---

### 3.5 filesystem — File Read/Write Operations

**Purpose**: Read and write files on the VPS filesystem. Critical tool for evidence writing, configuration management, code generation, and audit artifact creation.

**Authorization Level**: Mixed — L1 for reads in allowed paths, L2 for writes in workspace, L3 for production paths, L4 for system files.

**Installation**:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/filesystem-mcp"],
      "env": {
        "ALLOWED_PATHS": "/home/guinevere/workspace:/tmp:/home/guinevere/evidence:/home/guinevere/audit-reports:/home/guinevere/data"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | OS user permissions (guinevere user) |
| Path Restriction | ALLOWED_PATHS environment variable (MCP09) |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
filesystem:
  allowed_paths:
    read_autonomous:
      - "/home/guinevere/workspace"
      - "/home/guinevere/core"
      - "/tmp"
      - "/home/guinevere/evidence"
      - "/home/guinevere/audit-reports"
      - "/home/guinevere/data"
      - "/home/guinevere/config"
    write_notify:
      - "/home/guinevere/workspace"
      - "/home/guinevere/evidence"
      - "/home/guinevere/audit-reports"
      - "/tmp"
    write_approval:
      - "/home/guinevere/core"
      - "/etc/guinevere"
    forbidden:
      - "/etc/passwd"
      - "/etc/shadow"
      - "/home/guinevere/.age/key.txt"
      - "/home/guinevere/config/.env.sops"
      - "/home/guinevere/config/*.sops"
      - "/proc"
      - "/sys"
  max_file_size_mb: 50
  encoding: "utf-8"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 100 operations/min | Internal throttle |
| Concurrent | 10 parallel operations | Internal throttle |
| Max file size | 50MB per read/write | Internal limit |

**Cost**:

| Metric | Value |
|---|---|
| Per-operation | $0.00 |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:filesystem` |

**When to Use**:

- Reading source code files during SDLC Phase 1 (Research) and Phase 4 (Execute)
- Writing evidence markdown files to `evidence/` directory (Phase 7)
- Writing audit reports to `audit-reports/` directory (Phase 5)
- Creating/updating project documentation
- Reading configuration files for service management
- Writing sub-agent output files

**When NOT to Use**:

- Binary file operations → use shell (cp, mv)
- Database operations → use postgres
- Git-tracked file operations that need history → use git
- Remote file access → use fetch

**Guinevere-Specific Rules** (MCP09):

- **Autonomous read/write paths**: workspace root + /tmp + evidence/ + audit-reports/
- **Approval required**: all other paths require Faiz approval before access
- Guinevere writes evidence files using filesystem as primary tool during SDLC Phase 7
- All write operations to workspace are logged with correlation_id for audit trail
- Guinevere NEVER reads or writes SOPS-encrypted files directly — uses shell with `sops -d`
- Sub-agents are restricted to evidence/ and audit-reports/ for write operations

**Fallback Chain**:

1. filesystem → 2. shell (cat, cp for simple operations) → 3. git (for versioned content)

**Caching**: No caching — direct filesystem access is instant.

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Permission denied | Path outside allowed_paths | Request approval via Discord |
| File not found | Incorrect path | Verify path with glob or shell ls |
| Disk full | VPS storage exhausted | Clean old logs, rotate surveillance data |
| Encoding error | Non-UTF-8 file | Specify encoding or use shell iconv |
| File too large | Exceeds 50MB limit | Use shell split or read in chunks |

---

### 3.6 github — Repository Operations

**Purpose**: Interact with GitHub repositories for code management, issue tracking, pull requests, and webhook management. Primary tool for SDLC version control operations.

**Authorization Level**: Mixed — L1 for read operations, L2 for issues/PRs, L3 for merge/protected branches, L4 for force-push/delete.

**Installation**:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/github-mcp"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_PAT}"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | GitHub Personal Access Token (PAT) |
| Environment Variable | `GITHUB_PAT` |
| SOPS Path | `mcp.production.yaml.sops → github.pat` |
| Rotation | Quarterly (Guinevere manages autonomously via browser) |
| Scopes | repo, workflow, write:packages, admin:repo_hook, admin:org(read) |
| Denied Scopes | delete_repo |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
github:
  pat: "${GITHUB_PAT}"
  api_url: "https://api.github.com"
  default_owner: "faizcj"
  repos:
    - "guinevere-de-baroque"
    - "guinevere-docs"
    - "budgezen"
    - "budgezen-docs"
    - "sembilan-emas"
    - "sembilan-emas-docs"
    - "specforge"
  protected_branches:
    - "main"
    - "production"
  webhook_secret: "${GITHUB_WEBHOOK_SECRET}"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-hour | 5,000 requests/hour | GitHub API authenticated |
| Per-minute | ~83 requests/min | Derived from hourly limit |
| Search API | 30 requests/min | GitHub Search API limit |
| Concurrent | 5 parallel requests | Internal throttle |

**Cost**:

| Metric | Value |
|---|---|
| Per-request | $0.00 (included in PAT) |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:github` |

**When to Use**:

- Reading repository files and structure (SDLC Phase 1)
- Creating and managing issues for task tracking
- Creating pull requests for completed work (SDLC Phase 7)
- Code review comments on PRs
- Searching across repositories
- Managing webhooks for event-driven automation
- Bulk operations via PyGithub (batch close, mass labels)

**When NOT to Use**:

- Direct git operations (commit, branch, diff) → use git MCP tool
- Large file uploads → use git LFS or shell
- CI/CD pipeline management → use GitHub Actions via webhooks
- Non-GitHub repositories → use git + shell

**Guinevere-Specific Rules** (MCP10):

- **Autonomous**: Read (list files, get file content, search code), issues (create, comment, label), PRs (create in non-protected branches)
- **Write-Notify**: Create PRs, comment on issues/PRs, manage labels
- **Approval Required**: Merge PRs to protected branches, modify branch protection rules
- **Forbidden**: Force-push, delete repositories, modify organization settings
- Guinevere auto-reviews PRs via webhook handler when `pull_request (opened)` event fires
- GitHub file content cached in Redis DB1 with session TTL (MCP18)
- Guinevere manages PAT rotation autonomously via playwright browser login to GitHub dashboard

**Fallback Chain**:

1. github (API) → 2. git (local operations) → 3. shell (git CLI fallback)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| File content | Session duration | Redis DB1 `github:file:{repo}:{path}:{sha}` |
| Issue list | 5 minutes | Redis DB1 `github:issues:{repo}:{state}` |
| PR list | 5 minutes | Redis DB1 `github:prs:{repo}:{state}` |
| Search results | 10 minutes | Redis DB1 `github:search:{query_hash}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| 401 Bad credentials | PAT expired or revoked | Rotate PAT via SOPS + browser |
| 403 Forbidden | Insufficient scope or rate limited | Check PAT scopes, wait for rate reset |
| 404 Not Found | Private repo, PAT lacks access | Verify repo access in PAT settings |
| 422 Validation Failed | Invalid PR parameters | Check branch names, required reviews |
| Rate limit exceeded | 5000/hour exhausted | Wait for reset, reduce polling frequency |

---

### 3.7 grep_app — Code Search Across GitHub Repositories

**Purpose**: Search for real-world code examples across millions of public GitHub repositories. Essential for finding implementation patterns, API usage examples, and best practices from production codebases.

**Authorization Level**: L1 Read-Autonomous — all code search queries.

**Installation**:

```json
{
  "mcpServers": {
    "grep_app": {
      "command": "npx",
      "args": ["-y", "grep-app-mcp"],
      "env": {
        "GREP_APP_API_KEY": "${GREP_APP_API_KEY}"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | Grep.app API Key (if applicable) or public access |
| Environment Variable | `GREP_APP_API_KEY` |
| SOPS Path | `mcp.production.yaml.sops → grep_app.api_key` |
| Rotation | Quarterly |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
grep_app:
  api_key: "${GREP_APP_API_KEY}"
  base_url: "https://grep.app/api"
  default_language_filter: ["Python", "TypeScript", "Go"]
  timeout_ms: 15000
  max_results: 20
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 30 queries/min | API tier |
| Per-day | 5,000 queries/day | API tier |
| Concurrent | 3 parallel requests | Internal throttle |

**Cost**:

| Metric | Value |
|---|---|
| Per-query | $0.00 (free tier / included) |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:grep_app` |

**When to Use**:

- Finding real-world implementation patterns for specific APIs
- Discovering how production codebases use a particular library
- Finding code examples for unfamiliar frameworks
- Validating implementation approaches against community patterns
- SDLC Phase 1 (Research) — understanding how others solve similar problems

**When NOT to Use**:

- Searching own codebase → use filesystem with grep
- Finding documentation → use context7
- General web search → use brave_search or exa
- Finding libraries → use brave_search

**Guinevere-Specific Rules**:

- Guinevere uses grep_app during research phase to find real-world code patterns
- Results inform implementation decisions in SDLC Phase 4 (Execute)
- Language filter defaults to Python, TypeScript, Go matching Guinevere primary stack
- Guinevere caches useful code patterns in Redis DB1 for reuse across projects

**Fallback Chain**:

1. grep_app → 2. github (code search API) → 3. brave_search (code search) → 4. exa (semantic code search)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Search results | 1 hour | Redis DB1 `search:grepapp:{query_hash}` |
| Code patterns | Session duration | Redis DB1 `grepapp:pattern:{pattern_id}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| No results | Query too specific or unusual | Broaden search, try different syntax |
| Timeout | API slow | Retry 2x, fallback to GitHub code search |
| Rate limited | Exceeded quota | Backoff 60s, use GitHub search as fallback |

---

### 3.8 playwright — Browser Automation

**Purpose**: Browser automation for web scraping, form filling, authentication flows, screenshot capture, and interactive website operations. Secondary tool — obscura (Rust) is primary browser automation.

**Authorization Level**: L2 Write-Notify for simple operations, L3 Destructive-Approval for complex automation with credentials.

**Installation**:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/playwright-mcp"],
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "/home/guinevere/.cache/playwright"
      }
    }
  }
}
```

```bash
# Install browsers
npx playwright install chromium
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | None for tool itself; credentials for automated sites via SOPS |
| Browser | Chromium (headless) |
| Storage | /home/guinevere/.cache/playwright |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
playwright:
  browser: "chromium"
  headless: true
  timeout_ms: 60000
  viewport:
    width: 1280
    height: 720
  user_agent: "Mozilla/5.0 (Guinevere Agent)"
  screenshot_dir: "/home/guinevere/data/screenshots"
  pdf_dir: "/home/guinevere/data/pdfs"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 10 browser sessions/min | Resource constraint |
| Concurrent sessions | 2 parallel browsers | RAM constraint (256MB each) |
| Page actions | 30 actions/session | Internal limit |

**Cost**:

| Metric | Value |
|---|---|
| Per-session | $0.00 |
| RAM per session | ~256MB |
| Daily budget | $0.00 (resource cost only) |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:playwright` |

**When to Use**:

- Complex form automation with multiple steps
- Authentication flow automation (API key rotation via dashboard)
- PDF generation from web pages
- Screenshot capture for evidence
- JavaScript-heavy sites that obscura cannot handle
- Financial statement scraping (future — banking UI)
- Fallback when obscura fails on complex interactions

**When NOT to Use**:

- Simple web scraping → use obscura (faster, Rust)
- Static content fetching → use fetch (lightweight)
- Simple URL content → use fetch
- High-volume scraping → use obscura

**Guinevere-Specific Rules** (MCP11):

- **Obscura is PRIMARY** browser tool. Playwright is FALLBACK only.
- Playwright used when obscura cannot handle: complex multi-step forms, auth flows, PDF generation
- Guinevere uses Playwright for GitHub PAT rotation — logs into dashboard, generates new token
- Screenshots saved to evidence/ directory with correlation_id naming
- All browser automation actions logged to audit trail
- Approval required for any automation involving credential input on external sites

**Fallback Chain**:

1. obscura (primary) → 2. playwright (complex flows) → 3. fetch (static content) → 4. shell curl (API-only)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Screenshots | 7 days | Filesystem `data/screenshots/` |
| PDF outputs | 30 days | Filesystem `data/pdfs/` |
| Page snapshots | 1 hour | Redis DB1 `playwright:snapshot:{url_hash}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Browser crash | Insufficient RAM | Kill other sessions, reduce concurrent limit |
| Timeout | Page too slow or JS blocking | Increase timeout, use wait_for_selector |
| Element not found | Page structure changed | Update selectors, use more robust locators |
| Authentication failure | Credentials expired | Rotate credentials via SOPS |
| Bot detection | Site blocks automation | Add stealth headers, use residential proxy |

---

### 3.9 sequential-thinking — Complex Planning and Reasoning

**Purpose**: Structured multi-step reasoning tool for complex problem decomposition, planning, decision-making, and chain-of-thought analysis. Enables Guinevere to think through complex problems systematically.

**Authorization Level**: L1 Read-Autonomous — all reasoning chain operations.

**Installation**:

```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/sequential-thinking-mcp"]
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | None required |
| Authentication | None |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
sequential_thinking:
  max_steps: 50
  max_branches: 10
  timeout_ms: 120000
  save_chains: true
  output_dir: "/home/guinevere/data/reasoning-chains"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-session | 50 thinking steps | Internal limit |
| Concurrent chains | 3 parallel chains | Internal limit |
| Max branches | 10 per chain | Internal limit |

**Cost**:

| Metric | Value |
|---|---|
| Per-chain | $0.00 (uses LLM tokens only) |
| Token cost | ~200-500 tokens per step (GPT-5.5) |
| Daily budget | Included in LLM budget |
| Monthly projection | Included in LLM budget |
| Cost tracking tag | `tool:sequential-thinking` (token cost under `llm:gpt55`) |

**When to Use**:

- Complex architecture decisions during SDLC Phase 2 (Plan & Delegate)
- Multi-step problem decomposition
- Evaluating trade-offs between approaches
- Debugging complex issues with multiple possible root causes
- Security analysis and threat modeling
- Planning surveillance data processing pipelines
- Persona drift analysis and mood transition decisions

**When NOT to Use**:

- Simple decisions → direct GPT-5.5 reasoning
- Straightforward lookups → use search tools
- Single-step operations → direct tool call
- Tasks with obvious solutions → skip to execution

**Guinevere-Specific Rules**:

- Guinevere uses sequential-thinking for complex decisions that affect multiple systems
- Reasoning chains are saved to `data/reasoning-chains/` for audit trail
- Sub-agents do NOT use sequential-thinking — they use DeepSeek V4 Flash direct reasoning
- Guinevere uses this tool primarily during SDLC Phase 2 (Plan) and Phase 5 (Validate)
- Complex mood/persona decisions may use sequential-thinking to evaluate impacts

**Fallback Chain**:

1. sequential-thinking → 2. Direct LLM reasoning (GPT-5.5) → 3. DeepSeek V4 Flash for simpler analysis

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Completed chains | Permanent | Filesystem `data/reasoning-chains/{date}-{topic}.json` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Chain timeout | Too many steps or complex branches | Reduce scope, break into sub-chains |
| Step limit reached | Problem too complex for 50 steps | Decompose into multiple chains |
| LLM error | GPT-5.5 unavailable | Fall back to DeepSeek V4 Flash reasoning |

---

### 3.10 time — Timezone and Scheduling Operations

**Purpose**: Timezone conversion, current time queries, scheduling calculations, and temporal operations. Essential for Guinevere's daily rituals, DND hours, and cross-timezone scheduling.

**Authorization Level**: L1 Read-Autonomous — all timezone and scheduling queries.

**Installation**:

```json
{
  "mcpServers": {
    "time": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/time-mcp"]
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | None required |
| Authentication | None |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
time:
  default_timezone: "Asia/Jakarta"  # WIB (UTC+7)
  dnd_start: "00:00"
  dnd_end: "07:00"
  workday_start: "07:00"
  workday_end: "00:00"
  morning_ritual: "07:30"
  evening_ritual: "21:00"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 60 queries/min | No practical limit |
| Concurrent | Unlimited | Stateless operation |

**Cost**:

| Metric | Value |
|---|---|
| Per-query | $0.00 |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:time` |

**When to Use**:

- Determining current WIB time for ritual scheduling
- Checking if within DND hours (00:00-07:00 WIB)
- Converting timestamps for surveillance data
- Scheduling daily reports and proactive messages
- Calculating time differences for task duration tracking
- Timezone conversion for client communications

**When NOT to Use**:

- Timer/countdown operations → use APScheduler in guinevere-scheduler.service
- Cron scheduling → use APScheduler directly
- Timestamp generation → use Python datetime directly

**Guinevere-Specific Rules**:

- Guinevere uses time tool to check DND hours before sending proactive messages
- Default timezone is always Asia/Jakarta (WIB, UTC+7) — Faiz's timezone
- Morning ritual at 07:30 WIB, evening ritual at 21:00 WIB — time tool validates scheduling
- Guinevere uses time for surveillance timestamp normalization across devices
- All timestamps in logs use ISO 8601 with timezone offset

**Fallback Chain**:

1. time → 2. Python `datetime` module → 3. Shell `date` command

**Caching**: No caching needed — time queries are instant and stateless.

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Wrong timezone | Incorrect IANA timezone name | Use valid IANA names (e.g., "Asia/Jakarta") |
| DST issues | Daylight saving time confusion | Time tool handles DST automatically |

---

### 3.11 websearch — General Web Search

**Purpose**: General-purpose web search alternative. Provides web search results with different ranking algorithm than brave_search. Used for cross-referencing and when brave_search results are insufficient.

**Authorization Level**: L1 Read-Autonomous — all web search queries.

**Installation**:

```json
{
  "mcpServers": {
    "websearch": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/websearch-mcp"],
      "env": {
        "WEBSEARCH_API_KEY": "${WEBSEARCH_API_KEY}"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | WebSearch API Key (provider-dependent) |
| Environment Variable | `WEBSEARCH_API_KEY` |
| SOPS Path | `mcp.production.yaml.sops → websearch.api_key` |
| Rotation | Quarterly |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
websearch:
  api_key: "${WEBSEARCH_API_KEY}"
  provider: "configurable"  # Can be Tavily, SerpAPI, etc.
  default_count: 10
  timeout_ms: 10000
  include_snippets: true
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 30 queries/min | Provider tier |
| Per-day | 1,000 queries/day | Provider tier |
| Concurrent | 3 parallel requests | Internal throttle |

**Cost**:

| Metric | Value |
|---|---|
| Per-query | $0.003-$0.01 (provider-dependent) |
| Daily budget | $3.00 |
| Monthly projection | $90/month at max usage |
| Cost tracking tag | `tool:websearch` |

**When to Use**:

- Cross-referencing brave_search results for validation
- When brave_search returns poor results for a specific query
- Alternative search ranking perspective
- Backup search when brave_search is rate limited

**When NOT to Use**:

- If brave_search already returned good results → use those
- Deep semantic research → use exa
- Library documentation → use context7
- Code search → use grep_app

**Guinevere-Specific Rules**:

- websearch and brave_search overlap — Guinevere checks brave_search FIRST (cheaper, better Indonesian content)
- websearch is secondary search tool — used only when brave_search results are insufficient
- Results cached with same 1h TTL as brave_search
- Guinevere monitors cost overlap between brave_search and websearch — avoids redundant spending

**Fallback Chain**:

1. brave_search (primary) → 2. websearch (secondary) → 3. exa (deep research) → 4. fetch (direct URL)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Search results | 1 hour | Redis DB1 `search:websearch:{query_hash}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| 401 Unauthorized | API key invalid | Rotate via SOPS |
| 429 Rate Limited | Exceeded provider limit | Backoff, switch to brave_search |
| Provider down | Service outage | Use brave_search exclusively |

---

### 3.12 git — Direct Git Operations

**Purpose**: Local git operations including commits, branches, diffs, logs, and status checks. Used for version control during SDLC code development phases.

**Authorization Level**: Mixed — L1 for read operations, L2 for local writes, L3 for push to protected branches, L4 for force operations.

**Installation**:

```json
{
  "mcpServers": {
    "git": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/git-mcp"],
      "env": {
        "GIT_AUTHOR_NAME": "Guinevere",
        "GIT_AUTHOR_EMAIL": "guinevere@de-baroque.dev",
        "GIT_COMMITTER_NAME": "Guinevere",
        "GIT_COMMITTER_EMAIL": "guinevere@de-baroque.dev"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | SSH key or HTTPS credentials for push operations |
| SSH Key | /home/guinevere/.ssh/id_ed25519 |
| Author Identity | Guinevere <guinevere@de-baroque.dev> |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
git:
  author:
    name: "Guinevere"
    email: "guinevere@de-baroque.dev"
  default_branch: "main"
  protected_branches:
    - "main"
    - "production"
  commit_message_template: "[{project}] {phase}: {description}"
  sign_commits: true
  gpg_key_id: "${GPG_KEY_ID}"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 30 operations/min | Local operation speed |
| Push operations | 10 pushes/hour | GitHub API push limit |
| Concurrent | 2 parallel operations | File lock constraint |

**Cost**:

| Metric | Value |
|---|---|
| Per-operation | $0.00 |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:git` |

**When to Use**:

- Creating commits during SDLC Phase 4 (Execute)
- Viewing diffs and change history
- Creating feature branches for new tasks
- Checking repository status
- Viewing commit logs and blame
- Local merge operations (feature → develop)

**When NOT to Use**:

- Remote repository operations (issues, PRs, webhooks) → use github MCP tool
- Large file management → use git LFS via shell
- Repository creation → use github MCP tool
- CI/CD management → use github MCP tool

**Guinevere-Specific Rules**:

- **Autonomous**: `git log`, `git diff`, `git status`, `git branch -l`, `git show`
- **Write-Notify**: `git commit`, `git branch create`, `git checkout`, `git merge` (non-protected)
- **Approval Required**: `git push` to main/production, `git tag` on main
- **Forbidden**: `git push --force`, `git rebase` on shared branches, `git reset --hard` on main
- Guinevere signs all commits with GPG key
- Commit messages follow template: `[project] phase: description`
- Guinevere self-deploy uses `git fetch + git pull` via cron — not this MCP tool

**Fallback Chain**:

1. git (MCP) → 2. shell (git CLI) → 3. github (for remote-only operations)

**Caching**: No caching — git operations are local and fast.

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Merge conflict | Conflicting changes | Resolve manually, request Faiz input if complex |
| Push rejected | Remote has new commits | Pull first, then push |
| Permission denied | SSH key not configured | Verify SSH key, check GitHub SSH settings |
| Detached HEAD | Checked out specific commit | Create branch or checkout existing branch |
| GPG signing failed | GPG key not available | Check GPG agent, verify key ID |

---

### 3.13 postgres — Direct Database Queries

**Purpose**: Execute SQL queries against PostgreSQL 16 database with pgvector and TimescaleDB extensions. Primary data store for all Guinevere persistent data: memory, persona, surveillance, financial, projects.

**Authorization Level**: Mixed — L1 for SELECT, L2 for INSERT/UPDATE, L3 for DELETE/ALTER, L4 for DROP/TRUNCATE.

**Installation**:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/postgres-mcp"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://guinevere_core:${DB_PASS}@postgres.internal:5432/guinevere"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | PostgreSQL user + password |
| Connection | Via PgBouncer (postgres.internal:5432) |
| Users | guinevere_core, guinevere_surveillance, guinevere_financial, guinevere_readonly, guinevere_admin |
| SOPS Path | `mcp.production.yaml.sops → postgres.passwords.*` |
| Rotation | Quarterly |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
postgres:
  host: "postgres.internal"
  port: 5432
  pgbouncer_port: 6432
  users:
    core:
      username: "guinevere_core"
      password: "${PG_CORE_PASS}"
      permissions: "SELECT, INSERT, UPDATE all schemas"
      pool_mode: "transaction"
    surveillance:
      username: "guinevere_surveillance"
      password: "${PG_SURV_PASS}"
      permissions: "INSERT surveillance schema only"
      pool_mode: "transaction"
    readonly:
      username: "guinevere_readonly"
      password: "${PG_READ_PASS}"
      permissions: "SELECT only all schemas"
      pool_mode: "session"
    admin:
      username: "guinevere_admin"
      password: "${PG_ADMIN_PASS}"
      permissions: "superuser — rotate, backup"
      pool_mode: "session"
  default_database: "guinevere"
  pool_size: 10
  max_overflow: 20
  pool_pre_ping: true
  pool_recycle: 3600
  statement_timeout_ms: 30000
  schemas:
    - memory
    - persona
    - behavior
    - surveillance
    - financial
    - projects
    - system
    - social
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Connection pool | 10 connections (+ 20 overflow) | PgBouncer config |
| Per-minute | 100 queries/min per user | Internal throttle |
| Query timeout | 30 seconds | Statement timeout |
| Concurrent write | 5 parallel write transactions | PgBouncer transaction mode |

**Cost**:

| Metric | Value |
|---|---|
| Per-query | $0.00 (self-hosted) |
| RAM allocation | 4GB (PostgreSQL + Redis combined) |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:postgres` |

**When to Use**:

- Querying memory tables for context injection (SDLC all phases)
- Reading/writing persona state: mood, drift log, Faiz profile
- Managing project data: tasks, evidence, documents
- Financial queries: transactions, budgets, API costs
- Surveillance data access (via guinevere_surveillance user)
- System configuration and feature flags
- Running Alembic migrations during self-deploy

**When NOT to Use**:

- Caching ephemeral data → use Redis
- Queue management → use Redis DB0
- Session state → use Redis DB3
- Pub/sub messaging → use Redis DB4
- High-frequency rate limiting → use Redis DB5

**Guinevere-Specific Rules** (MCP12):

- **Autonomous SELECT**: All schemas via guinevere_core user — read-only for analysis
- **Write-Notify INSERT/UPDATE**: Non-critical tables (persona, behavior, projects) — reported to Discord
- **Approval Required DELETE**: Any DELETE operation requires Faiz approval
- **Approval Required ALTER**: Schema changes require approval + staging test first
- **Forbidden DROP**: `DROP DATABASE`, `DROP TABLE` on production — requires explicit context + double confirmation
- **Forbidden TRUNCATE**: Truncating production tables without explicit approval
- Guinevere uses pgvector for semantic memory search during context injection
- TimescaleDB hypertables for surveillance data — auto-compression > 7 days
- Guinevere runs Alembic migrations during nightly self-deploy (staging first, then production)
- Mood state, persona drift, and Faiz profile queries run per-interaction for context injection

**Fallback Chain**:

1. postgres (PgBouncer) → 2. postgres (direct connection if PgBouncer down) → 3. Redis cache (for cached query results)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Query results (frequent) | 5 minutes | Redis DB1 `pg:cache:{query_hash}` |
| Schema metadata | 1 hour | Redis DB1 `pg:schema:{schema_name}` |
| Feature flags | 10 minutes | Redis DB1 `pg:flags:{flag_name}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Connection refused | PostgreSQL down | Restart container: `docker restart postgres` |
| Connection pool exhausted | Too many concurrent queries | Increase pool_size, optimize slow queries |
| Query timeout | Complex query > 30s | Optimize query, add indexes, use TimescaleDB aggregates |
| Permission denied | Wrong user for operation | Use correct PgBouncer user |
| SSL error | Certificate mismatch | Verify Tailscale TLS certificates |
| Deadlock | Concurrent writes to same rows | Use advisory locks, serialize writes |

---

### 3.14 redis — Cache Management

**Purpose**: In-memory cache, task queue, session management, pub/sub, and rate limiting across 6 dedicated databases. Critical infrastructure for Guinevere performance and coordination.

**Authorization Level**: Mixed — L1 for read operations, L2 for cache writes, L3 for configuration changes, L4 for FLUSHALL.

**Installation**:

```json
{
  "mcpServers": {
    "redis": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/redis-mcp"],
      "env": {
        "REDIS_URL": "redis://:${REDIS_PASS}@redis.internal:6379"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | Redis password |
| Connection | redis.internal:6379 via Tailscale |
| SOPS Path | `mcp.production.yaml.sops → redis.password` |
| Rotation | Quarterly |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
redis:
  host: "redis.internal"
  port: 6379
  password: "${REDIS_PASS}"
  max_connections: 50
  retry_on_timeout: true
  health_check_interval: 30
  databases:
    db0:
      name: "task_queue"
      purpose: "SDLC job queue"
      key_pattern: "task:{id}"
      ttl: "no_expiry"
    db1:
      name: "llm_cache"
      purpose: "LLM response cache + tool result cache"
      key_pattern: "llm:{hash}, search:{tool}:{hash}, fetch:url:{hash}"
      ttl: "1 hour (LLM), 1h (search), 24h (fetch)"
    db2:
      name: "surveillance_buffer"
      purpose: "Real-time surveillance data buffer"
      key_pattern: "surv:{device}:{ts}"
      ttl: "5 minutes"
    db3:
      name: "session_state"
      purpose: "Active session state management"
      key_pattern: "session:{id}"
      ttl: "24 hours"
    db4:
      name: "pubsub"
      purpose: "Inter-service pub/sub channels"
      key_pattern: "chan:{component}"
      ttl: "no_expiry"
    db5:
      name: "rate_limit"
      purpose: "Distributed rate limiting"
      key_pattern: "ratelimit:{tool}:{key}"
      ttl: "1 minute"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Operations/second | 100,000 ops/sec | Redis capability |
| Connection pool | 50 connections | ConnectionPool config |
| Max memory | 2GB | Redis maxmemory config |
| Eviction policy | allkeys-lru | Redis config |

**Cost**:

| Metric | Value |
|---|---|
| Per-operation | $0.00 (self-hosted) |
| RAM allocation | Shared with PostgreSQL (4GB combined) |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:redis` |

**When to Use**:

- Caching LLM responses (DB1, 1h TTL)
- Caching search results from brave_search, exa, websearch (DB1, 1h TTL)
- Caching web fetch content (DB1, 24h TTL)
- Task queue management for SDLC loops (DB0)
- Session state tracking (DB3, 24h TTL)
- Rate limiting for tool usage (DB5, 1min TTL)
- Pub/sub for inter-service communication (DB4)
- Surveillance data buffering before PostgreSQL write (DB2, 5min TTL)

**When NOT to Use**:

- Persistent data storage → use PostgreSQL
- Large data objects (>1MB) → use PostgreSQL or S3
- Complex queries → use PostgreSQL
- Full-text search → use PostgreSQL pgvector

**Guinevere-Specific Rules** (MCP13):

- **Full DB routing**: DB0 task queue, DB1 LLM cache, DB2 surveillance, DB3 session, DB4 pub/sub, DB5 rate limit
- **Autonomous**: GET, KEYS, TTL, INFO, EXISTS on all databases
- **Write-Notify**: SET, DEL, EXPIRE on cache entries (DB1, DB2, DB3)
- **Approval Required**: FLUSHDB, CONFIG SET, DEBUG, MONITOR
- **Forbidden**: FLUSHALL (never execute without explicit approval + double confirmation)
- Guinevere monitors Redis memory usage — alerts at 80% memory consumption
- Cache key naming conventions are strictly enforced for observability
- Rate limit counters use sliding window algorithm with 1-minute granularity

**Fallback Chain**:

1. redis → 2. In-memory Python dict (degraded cache) → 3. PostgreSQL (for persistent lookups)

**Caching**: Redis IS the cache. Meta-caching: frequently accessed keys are kept in Python LRU cache (max 1000 entries, 5min TTL).

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Connection refused | Redis container down | `docker restart redis` |
| MISCONF | AOF rewrite failed | Check disk space, restart Redis |
| OOM command not allowed | Memory full | Increase maxmemory, check eviction policy |
| Timeout | Network latency | Check Tailscale connection, increase timeout |
| WRONGTYPE | Wrong data type for key | Verify key pattern matches expected type |
| Connection pool exhausted | Too many concurrent connections | Reduce pool usage, optimize connection lifecycle |

---

### 3.15 shell/bash — VPS Commands

**Purpose**: Execute shell commands on the VPS for system management, service control, and operational tasks. **HIGH RISK** — most restricted tool with whitelist, blocklist, timeout, and directory restrictions.

**Authorization Level**: Mixed — L1 for whitelisted read commands, L2 for whitelisted write commands, L3 for system management, L4 for destructive operations.

**Installation**:

```json
{
  "mcpServers": {
    "shell": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/shell-mcp"],
      "env": {
        "ALLOWED_WORKING_DIR": "/home/guinevere",
        "SHELL_TIMEOUT_SEC": "30",
        "MAX_OUTPUT_BYTES": "1048576"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | OS user `guinevere` with limited sudo |
| sudo Access | systemctl restart guinevere-*, docker, ufw, apt |
| Working Directory | /home/guinevere (restricted) |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
shell:
  user: "guinevere"
  working_directory: "/home/guinevere"
  timeout_seconds: 30
  max_output_bytes: 1048576  # 1MB
  max_concurrent: 3

  # WHITELIST — commands Guinevere CAN execute (MCP14)
  whitelist_read:
    - "ls"
    - "cat"
    - "grep"
    - "find"
    - "wc"
    - "du"
    - "df"
    - "ps"
    - "top -bn1"
    - "free -m"
    - "uptime"
    - "whoami"
    - "date"
    - "uname"
    - "hostname"
    - "ip addr"
    - "systemctl status"
    - "journalctl"
    - "docker ps"
    - "docker logs"
    - "docker stats --no-stream"
    - "docker inspect"
    - "git status"
    - "git log"
    - "git diff"
    - "git branch"
    - "sops -d"
    - "curl localhost"

  whitelist_write:
    - "mkdir"
    - "touch"
    - "cp"
    - "mv"
    - "tar"
    - "gzip"
    - "gunzip"
    - "zip"
    - "unzip"
    - "systemctl restart guinevere-*"
    - "docker restart"
    - "docker start"
    - "docker stop"

  whitelist_approval:
    - "systemctl restart docker"
    - "systemctl restart caddy"
    - "apt update"
    - "apt install"
    - "apt upgrade"
    - "docker pull"
    - "docker build"
    - "docker compose"
    - "ufw"
    - "crontab"
    - "pip install"
    - "uv sync"
    - "alembic upgrade"

  # BLOCKLIST — patterns that are ALWAYS rejected (MCP14)
  blocklist:
    - "rm -rf /"
    - "rm -rf /*"
    - "rm -rf ~"
    - "chmod 777"
    - "chmod -R 777"
    - "curl | bash"
    - "curl | sh"
    - "wget | bash"
    - "wget | sh"
    - "eval $("
    - "exec("
    - "> /dev/sda"
    - "dd if="
    - ":(){ :|:& };:"
    - "mkfs"
    - "shutdown"
    - "reboot"
    - "init 0"
    - "init 6"
    - "docker system prune"
    - "docker rm -f"
    - "docker rmi"
    - "docker volume rm"
    - "DROP TABLE"
    - "DROP DATABASE"
    - "TRUNCATE"
    - "git push --force"
    - "git push -f"
    - "ssh -i"
    - "passwd"
    - "useradd"
    - "userdel"
    - "visudo"
    - "iptables -F"
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 20 commands/min | Internal throttle |
| Timeout | 30 seconds default | Configurable per command |
| Concurrent | 3 parallel commands | Internal limit |
| Max output | 1MB per command | Config limit |

**Cost**:

| Metric | Value |
|---|---|
| Per-command | $0.00 |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:shell` |

**When to Use**:

- System health checks: `df`, `free -m`, `ps aux`, `top`
- Service management: `systemctl restart guinevere-*`
- Docker operations: `docker ps`, `docker logs`, `docker restart`
- File operations: `mkdir`, `cp`, `tar`, `gzip`
- SOPS decryption: `sops -d .env.sops`
- Git operations: `git status`, `git log`, `git diff`
- Network diagnostics: `curl localhost:PORT/health`

**When NOT to Use**:

- File reading/writing → use filesystem MCP tool
- Git commits/branches → use git MCP tool
- Database queries → use postgres MCP tool
- Docker container management (complex) → use docker MCP tool
- Web requests → use fetch or playwright

**Guinevere-Specific Rules** (MCP14):

- **Command whitelist**: Only commands in whitelist_read, whitelist_write, or whitelist_approval may execute
- **Pattern blocklist**: Any command matching blocklist patterns is IMMEDIATELY REJECTED — no override possible
- **Timeout**: 30 seconds default. Commands exceeding timeout are killed
- **Working directory**: All commands execute within /home/guinevere — no `cd` outside allowed
- **Output truncation**: Output exceeding 1MB is truncated with warning
- **All commands logged**: Every command, its output, exit code, and duration logged to audit trail
- **SEV0 override**: Read-only diagnostic commands (ps, top, df, journalctl) may bypass approval during SEV0
- Guinevere self-deploy uses shell for: `git pull`, `uv sync`, `systemctl restart guinevere-*`

**Fallback Chain**:

1. shell → 2. Specific MCP tool (filesystem, git, docker, postgres) → 3. Request Faiz manual execution

**Caching**: No caching — shell commands are inherently stateful and dynamic.

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Command blocked | Matches blocklist pattern | Use alternative whitelisted command |
| Timeout | Command took > 30s | Increase timeout for specific command, or break into smaller commands |
| Permission denied | Not in sudo whitelist | Request sudo access via Faiz approval |
| Working directory violation | Path outside /home/guinevere | Use absolute paths within allowed directory |
| Output truncated | Exceeded 1MB | Pipe through head/tail or redirect to file |

---

### 3.16 docker — Container Management

**Purpose**: Manage Docker containers running on the VPS: PostgreSQL, Redis, Prometheus, and other containerized services. Read operations autonomous, write operations notify, destructive operations require approval.

**Authorization Level**: Mixed — L1 for read operations, L2 for start/stop/restart, L3 for build/pull, L4 for system prune/rm.

**Installation**:

```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/docker-mcp"],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      }
    }
  }
}
```

**Authentication**:

| Property | Value |
|---|---|
| Credential | Docker socket access via guinevere user group |
| Docker Group | guinevere user is member of docker group |
| Socket | /var/run/docker.sock |

**Configuration**:

```yaml
# /home/guinevere/config/mcp.production.yaml (decrypted view)
docker:
  socket: "/var/run/docker.sock"
  managed_containers:
    - "guinevere-postgres"
    - "guinevere-redis"
    - "guinevere-prometheus"
    - "guinevere-grafana"
    - "guinevere-loki"
  compose_file: "/home/guinevere/docker-compose.yml"
  image_registry: "docker.io"
  max_log_lines: 1000
```

**Rate Limits**:

| Limit Type | Value | Source |
|---|---|---|
| Per-minute | 20 operations/min | Internal throttle |
| Concurrent | 2 parallel operations | Docker daemon constraint |
| Build operations | 1 at a time | Resource constraint |

**Cost**:

| Metric | Value |
|---|---|
| Per-operation | $0.00 |
| Disk per image | 100MB-1GB |
| Daily budget | $0.00 |
| Monthly projection | $0.00 |
| Cost tracking tag | `tool:docker` |

**When to Use**:

- Checking container health: `docker ps`, `docker stats`
- Reading container logs: `docker logs --tail 100`
- Restarting unhealthy containers: `docker restart`
- Inspecting container config: `docker inspect`
- Building images during self-deploy (with approval)
- Pulling updated images (with approval)

**When NOT to Use**:

- Simple log reading → use shell `docker logs` (whitelisted)
- Database queries → use postgres MCP tool
- Cache operations → use redis MCP tool
- Service health monitoring → use prometheus/grafana

**Guinevere-Specific Rules** (MCP15):

- **Autonomous (L1)**: `docker ps`, `docker logs`, `docker inspect`, `docker stats`
- **Write-Notify (L2)**: `docker start`, `docker stop`, `docker restart` for managed containers
- **Approval Required (L3)**: `docker build`, `docker pull` (new images), `docker compose up/down`
- **Forbidden (L4)**: `docker system prune`, `docker rm -f`, `docker volume rm`, `docker rmi`
- Guinevere monitors container health every 30 seconds via health check architecture
- Auto-restart of unhealthy containers is allowed without approval (part of health check protocol)
- Docker operations logged with container name, operation, and result

**Fallback Chain**:

1. docker (MCP) → 2. shell (docker CLI) → 3. systemctl (for systemd-managed services)

**Caching**:

| Cache Target | TTL | Storage |
|---|---|---|
| Container status | 30 seconds | Redis DB1 `docker:status:{container_name}` |
| Container stats | 1 minute | Redis DB1 `docker:stats:{container_name}` |

**Troubleshooting**:

| Error | Cause | Fix |
|---|---|---|
| Container not found | Container not running | Check `docker ps -a`, start container |
| Socket permission denied | User not in docker group | Add guinevere user to docker group |
| Build failed | Dockerfile error or missing context | Check Dockerfile, verify build context |
| Pull failed | Registry auth or network issue | Verify registry credentials, check network |
| OOM killed | Container exceeded memory limit | Increase memory limit, optimize container |
| Volume mount error | Host path not found | Verify host paths in docker-compose.yml |

---

## §4 TOOL SELECTION DECISION TREE

### 4.1 Decision Matrix

| Scenario | Primary Tool | Fallback 1 | Fallback 2 | Cost per Operation |
|---|---|---|---|---|
| Find documentation for library X | context7 | websearch | exa | $0.00 |
| Search web for current information | brave_search | exa | websearch | $0.003 |
| Deep research on topic Y | exa | brave_search | fetch | $0.01 |
| Read/write project files | filesystem | shell | git | $0.00 |
| Search codebase for pattern | grep_app | filesystem (grep) | github search | $0.00 |
| Browse website interactively | obscura | playwright | fetch | $0.00 |
| Query project database | postgres | redis (cached) | — | $0.00 |
| Manage cache/sessions | redis | — | — | $0.00 |
| Run system commands | shell | — | — | $0.00 |
| Git operations | git | shell (git CLI) | github (API) | $0.00 |
| Container management | docker | shell (docker CLI) | — | $0.00 |
| Complex reasoning | sequential-thinking | Direct LLM | — | ~$0.001/step |
| Time/timezone operations | time | Python datetime | shell date | $0.00 |
| GitHub repository operations | github | git | shell | $0.00 |
| Fetch specific URL content | fetch | playwright | obscura | $0.00 |
| Cross-reference web search | websearch | brave_search | exa | $0.003 |

### 4.2 Decision Flowchart

```
┌─────────────────────────────────┐
│         WHAT DO YOU NEED?       │
└─────────────┬───────────────────┘
              │
    ┌─────────┴──────────────────────────────┐
    │                                         │
    ▼                                         ▼
INFORMATION                            SYSTEM OPERATION
    │                                         │
    ├── Library docs? → context7              ├── File ops? → filesystem
    │                                         │
    ├── Web search? ──┐                       ├── DB query? → postgres
    │                 │                       │
    │   Keyword: brave_search                 ├── Cache/queue? → redis
    │   Semantic: exa                         │
    │   Cross-ref: websearch                  ├── Git ops? → git
    │                 │                       │
    ├── Code example? → grep_app              ├── Docker? → docker
    │                                         │
    ├── Deep research? → exa                  ├── System cmd? → shell
    │                                         │
    ├── Specific URL? → fetch                 ├── Browser auto? → obscura/playwright
    │                                         │
    └── GitHub repo? → github                 └── Reasoning? → sequential-thinking
                                              │
                                              └── Time/schedule? → time
```

### 4.3 Cost-Optimized Selection Rules

1. **Always try FREE tools first**: filesystem, git, postgres, redis, docker, shell, time, sequential-thinking, context7, grep_app
2. **Cheapest search first**: brave_search ($0.003) before exa ($0.01)
3. **Cache before query**: Check Redis DB1 cache before any external API call
4. **Bulk operations**: Prefer batch tools (PyGithub for bulk GitHub, shell for bulk file ops)
5. **Fallback only on failure**: Do not skip primary tool unless it has failed 3x consecutively

---

## §5 COST OPTIMIZATION STRATEGY

### 5.1 Tool Cost Comparison (Cheapest to Most Expensive)

| Rank | Tool | Cost per Operation | Monthly Max (at daily cap) |
|---|---|---|---|
| 1 | filesystem | $0.00 | $0.00 |
| 2 | git | $0.00 | $0.00 |
| 3 | postgres | $0.00 | $0.00 |
| 4 | redis | $0.00 | $0.00 |
| 5 | docker | $0.00 | $0.00 |
| 6 | shell | $0.00 | $0.00 |
| 7 | time | $0.00 | $0.00 |
| 8 | sequential-thinking | ~$0.001/step | ~$15.00 |
| 9 | context7 | $0.00 | $0.00 |
| 10 | grep_app | $0.00 | $0.00 |
| 11 | fetch | $0.00 | $0.00 |
| 12 | github | $0.00 | $0.00 |
| 13 | playwright | $0.00 (resource only) | $0.00 |
| 14 | brave_search | $0.003 | $45.00 |
| 15 | websearch | $0.003-$0.01 | $90.00 |
| 16 | exa | $0.01 | $150.00 |

### 5.2 Caching Strategy (MCP18)

| Cache Target | TTL | Storage Location | Invalidation |
|---|---|---|---|
| context7 resolved library IDs | 7 days per project | Redis DB1 | On library version change |
| Web fetch content | 24 hours | Redis DB1 | Manual or TTL expiry |
| Search results (brave, exa, websearch) | 1 hour | Redis DB1 | TTL expiry |
| GitHub file content | Session duration | Redis DB1 | On commit SHA change |
| PostgreSQL query results | 5 minutes | Redis DB1 | On table write |
| Docker container status | 30 seconds | Redis DB1 | On container state change |
| LLM response cache | 1 hour | Redis DB1 | TTL expiry |
| Page snapshots (playwright) | 1 hour | Redis DB1 | TTL expiry |
| Code patterns (grep_app) | Session duration | Redis DB1 | Session end |

### 5.3 Daily Cost Tracking

Per-tool cost tracking stored in PostgreSQL `financial.api_costs` table and reported to Discord `#cost-tracker`:

```sql
INSERT INTO financial.api_costs (
    date, tool, operations, cost_usd, model, correlation_id
) VALUES (
    CURRENT_DATE, 'exa', 1, 0.01, NULL, 'loop-budgezen-001-phase1'
);
```

**Daily aggregate calculation**:

```sql
SELECT tool, SUM(operations) as ops, SUM(cost_usd) as cost
FROM financial.api_costs
WHERE date = CURRENT_DATE
GROUP BY tool
ORDER BY cost DESC;
```

### 5.4 Budget Alerts (per DIS18)

| Threshold | Action | Channel |
|---|---|---|
| $1.00 daily | Info alert — daily cost tracking started | #cost-tracker |
| $15.00 warning | Yellow embed — approaching budget | #cost-tracker + DM Faiz |
| $25.00 critical | Red embed — budget critical | #cost-tracker + DM Faiz + Gotify |
| $30.00 hard cap | STOP all paid tool operations | #cost-tracker + DM Faiz + Gotify + auto-pause loops |

### 5.5 Per-Model Cost Breakdown

| Model | Cost per 1M Input Tokens | Cost per 1M Output Tokens | Usage |
|---|---|---|---|
| GPT-5.5 (9Router) | Premium (~$2.50) | Premium (~$10.00) | Guinevere core persona + complex decisions |
| DeepSeek V4 Flash (9Router) | $0.10 | $0.20 | Sub-agents: research, code, validation |
| DeepSeek V4 Flash free (9Router) | $0.00 | $0.00 | Audit sub-agents, low-priority validation |
| Ollama (local) | $0.00 | $0.00 | Emergency fallback only |

### 5.6 Monthly Projections

| Category | Daily Average | Monthly Projection |
|---|---|---|
| LLM (GPT-5.5 core) | $2.00 | $60.00 |
| LLM (DeepSeek sub-agents) | $0.50 | $15.00 |
| Search tools (combined) | $1.00 | $30.00 |
| Infrastructure (VPS) | $1.33 | $40.00 |
| **TOTAL** | **$4.83** | **$145.00** |

---

## §6 SECURITY RULES PER TOOL CATEGORY

### 6.1 Read-Only Tools (No Restrictions Beyond Authentication)

| Tool | Security Rules |
|---|---|
| brave_search | API key authentication only. No user input in API key path. |
| context7 | No authentication required. Validate library names against injection. |
| exa | API key authentication. Sanitize search queries (no shell injection). |
| fetch | Validate URL scheme (https/http only). Block internal network ranges (10.x, 172.x, 192.168.x). |
| grep_app | Validate search queries. No code execution from results without review. |
| sequential-thinking | No external interaction. Pure reasoning chain. |
| time | No external interaction. Pure computation. |
| websearch | API key authentication. Same URL validation as fetch for result URLs. |

### 6.2 Write Tools (Approval Workflow + Audit Logging)

| Tool | Write Security Rules |
|---|---|
| filesystem | Path whitelist enforced. No write to /etc, /proc, /sys, secrets files. All writes logged with diff. |
| github | No force-push, no repo deletion. PR merge requires approval for protected branches. All API calls logged. |
| git | GPG-signed commits. No force-push. Protected branch push requires approval. Commit log auditable. |
| postgres | PgBouncer user permissions enforce least-privilege. Write operations logged. No DROP without explicit approval. |
| redis | No FLUSHALL. Cache writes logged. Rate limit modifications logged. |
| docker | Only managed containers. No system prune. Build/pull require approval. All operations logged. |
| playwright | Credential input requires approval. No automated account creation/deletion. Screenshots as evidence. |

### 6.3 Destructive Operations (Explicit Approval + Confirmation + Rollback Plan)

| Operation | Approval | Confirmation | Rollback Plan |
|---|---|---|---|
| shell: `systemctl restart docker` | Faiz `/approve` | Double confirmation | Previous service state logged |
| postgres: `DROP TABLE` | Faiz `/approve` + reason | Triple confirmation: type table name | pg_dump before execution, WAL for recovery |
| postgres: `TRUNCATE` | Faiz `/approve` + reason | Double confirmation | pg_dump of table before truncation |
| git: `push --force` | **FORBIDDEN** — no override | N/A | N/A |
| docker: `system prune` | **FORBIDDEN** — no override | N/A | N/A |
| redis: `FLUSHALL` | **FORBIDDEN** — no override | N/A | N/A |
| filesystem: write to /etc | **FORBIDDEN** — no override | N/A | N/A |

### 6.4 Shell Security (MCP14)

**Command Whitelist** (see §3.15 for complete list):
- Read commands: ls, cat, grep, find, ps, df, free, docker ps/logs/stats
- Write commands: mkdir, cp, touch, systemctl restart guinevere-*
- Approval commands: apt install, docker pull/build, alembic upgrade

**Dangerous Pattern Blocklist** (see §3.15 for complete list):
- `rm -rf /`, `rm -rf /*`, `rm -rf ~`
- `chmod 777`, `chmod -R 777`
- `curl | bash`, `wget | sh`
- `dd if=`, `mkfs`, `shutdown`, `reboot`
- `docker system prune`, `docker rm -f`
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`
- `git push --force`, `git push -f`

**Timeout**: 30 seconds default. Long-running commands require explicit timeout parameter + approval.

**Working Directory Restriction**: All commands must execute within `/home/guinevere`. No `cd /`, `cd /etc`, or other directory escapes.

### 6.5 Database Security

- **Read-only default**: guinevere_readonly user for Grafana and reporting
- **Least-privilege**: Each service has dedicated PgBouncer user with minimum required permissions
- **Write approval**: INSERT/UPDATE on non-critical tables is Write-Notify; DELETE always requires approval
- **No destructive operations without explicit context**: DROP/TRUNCATE requires double confirmation + backup
- **Query timeout**: 30 seconds to prevent long-running queries from exhausting connection pool
- **Audit trail**: All write operations logged to `system.audit_trail` table

### 6.6 File System Security

- **Path restrictions**: Only `/home/guinevere/workspace`, `/tmp`, `/home/guinevere/evidence`, `/home/guinevere/audit-reports`, `/home/guinevere/data` for autonomous operations
- **No sensitive files**: `/etc/passwd`, `/etc/shadow`, SOPS encrypted files, age keys are forbidden
- **No production configs**: Direct modification of production configuration files requires approval
- **File size limit**: 50MB maximum per read/write operation

### 6.7 Network Security

- **No credentials in logs**: API keys, passwords, tokens are NEVER logged in plaintext
- **Tailscale only**: All internal service communication via Tailscale mesh — zero public ports
- **HTTPS enforcement**: External API calls must use HTTPS
- **URL validation**: Fetch tool blocks requests to internal network ranges
- **Request signing**: Surveillance data uses HMAC-SHA256 signature validation

---

## §7 AUTONOMOUS TOOL MANAGEMENT

### 7.1 Autonomous Operations (No Approval Needed)

| Tool | Operations | Conditions |
|---|---|---|
| brave_search | All search queries | Rate limit respected |
| context7 | resolve-library-id, query-docs | Library ID cached if possible |
| exa | All search queries | Under $5 daily burst cap and $5 monthly hard stop |
| fetch | All URL fetches | URL not in blocked ranges |
| filesystem | Read workspace+/tmp+evidence+audit | Path in allowed list |
| filesystem | Write evidence/+audit-reports+/workspace | File path in write-notify list |
| github | List files, get content, search | API rate limit respected |
| github | Create issues, comment, label | Non-protected operations |
| grep_app | All code search queries | — |
| sequential-thinking | All reasoning chains | — |
| time | All queries | — |
| websearch | All search queries | Rate limit respected |
| git | log, diff, status, branch list | Read-only operations |
| git | commit, branch create, checkout | Local operations |
| postgres | SELECT all schemas | Via guinevere_core user |
| redis | GET, KEYS, TTL, INFO | All databases |
| redis | SET, DEL (cache entries) | DB1, DB2, DB3 |
| shell | Whitelisted read commands | Within working directory |
| docker | ps, logs, inspect, stats | Read-only container info |

### 7.2 Notify-After Operations (Execute + Report)

| Tool | Operations | Notification Format |
|---|---|---|
| github | Create PR (non-protected) | Purple embed: PR title + link + branch |
| git | push to non-protected branch | Brief: branch name + commit count |
| postgres | INSERT/UPDATE non-critical | Discord #guinevere-status: table + row count |
| filesystem | Write to workspace | No notification unless part of loop evidence |
| shell | Whitelisted write commands | Discord: command + result summary |
| docker | start/stop/restart container | Discord: container name + status change |
| playwright | Simple page navigation | No notification unless evidence capture |

### 7.3 Approval-Required Operations (Wait for /approve)

| Tool | Operations | Approval Flow |
|---|---|---|
| github | Merge PR to protected branch | Discord embed: PR details → Faiz `/approve [id]` |
| git | push to main/production | Discord embed: commits + diff summary → `/approve` |
| postgres | DELETE, ALTER, schema changes | Discord embed: SQL + impact analysis → `/approve` |
| filesystem | Write to production paths | Discord embed: file path + content diff → `/approve` |
| shell | systemctl restart docker/caddy, apt install | Discord embed: command + reason → `/approve` |
| docker | build, pull new images | Discord embed: image + tag + reason → `/approve` |
| playwright | Complex automation with credentials | Discord embed: target site + actions → `/approve` |

### 7.4 Discord Integration (per DIS11)

| Command | Function |
|---|---|
| `/approve [id]` | Approve specific pending operation |
| `/deny [id] [reason]` | Deny specific operation with reason |
| `/approve-all` | Batch approve all pending operations |

**Approval flow**:

1. Guinevere posts approval request embed to Discord (purple, with operation details)
2. Request has unique operation ID
3. Faiz responds with `/approve [id]` or `/deny [id] [reason]`
4. Guinevere executes or cancels + logs the decision
5. Timeout: 1 hour default — operation cancelled if no response

### 7.5 Emergency Override (SEV0)

During active SEV0 incidents, the following L3 operations may bypass approval:

| Tool | Emergency Operation | Logging |
|---|---|---|
| shell | `ps aux`, `top -bn1`, `df -h`, `journalctl -u service` | `SEV0_OVERRIDE` tag |
| docker | `docker restart container`, `docker logs` | `SEV0_OVERRIDE` tag |
| postgres | SELECT queries for diagnosis | `SEV0_OVERRIDE` tag |
| redis | GET, KEYS for diagnosis | `SEV0_OVERRIDE` tag |

All SEV0 overrides are:
1. Logged with `SEV0_OVERRIDE` tag in audit trail
2. Reported to Faiz immediately via Discord + Gotify
3. Reviewed in post-incident analysis

---

## §8 MONITORING & OBSERVABILITY

### 8.1 Centralized Logging (MCP22)

All MCP tool operations produce structured JSON logs shipped to Loki → Grafana:

```json
{
  "timestamp": "2026-05-31T10:30:00+07:00",
  "level": "info",
  "service": "guinevere-mcp",
  "tool": "brave_search",
  "operation": "search",
  "query_hash": "a1b2c3d4",
  "duration_ms": 245,
  "status": "success",
  "cost_usd": 0.003,
  "correlation_id": "loop-budgezen-001-phase1",
  "cache_hit": false,
  "loop_id": "loop-budgezen-001",
  "phase": 1,
  "tags": ["tool:brave_search", "loop:research", "project:budgezen"]
}
```

### 8.2 Per-Tool Tags for Filtering

| Tool | Primary Tag | Secondary Tags |
|---|---|---|
| brave_search | `tool:brave_search` | `search:web`, `cost:paid` |
| context7 | `tool:context7` | `search:docs`, `cost:free` |
| exa | `tool:exa` | `search:semantic`, `cost:paid` |
| fetch | `tool:fetch` | `fetch:url`, `cost:free` |
| filesystem | `tool:filesystem` | `fs:read` or `fs:write` |
| github | `tool:github` | `github:api`, `github:webhook` |
| grep_app | `tool:grep_app` | `search:code`, `cost:free` |
| playwright | `tool:playwright` | `browser:auto`, `cost:free` |
| sequential-thinking | `tool:sequential-thinking` | `reasoning:chain` |
| time | `tool:time` | `time:query` |
| websearch | `tool:websearch` | `search:web`, `cost:paid` |
| git | `tool:git` | `git:local` |
| postgres | `tool:postgres` | `db:query`, `db:user:{username}` |
| redis | `tool:redis` | `cache:db{N}` |
| shell | `tool:shell` | `shell:read` or `shell:write` |
| docker | `tool:docker` | `container:ops` |

### 8.3 Prometheus Metrics

```python
# Per-tool operation counter
tool_operations_total = Counter(
    "guinevere_mcp_tool_operations_total",
    "Total MCP tool operations",
    ["tool", "operation", "status"]
)

# Per-tool latency histogram
tool_latency_seconds = Histogram(
    "guinevere_mcp_tool_latency_seconds",
    "MCP tool operation latency",
    ["tool", "operation"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60]
)

# Per-tool error rate
tool_errors_total = Counter(
    "guinevere_mcp_tool_errors_total",
    "Total MCP tool errors",
    ["tool", "error_type"]
)

# Per-tool cost counter
tool_cost_usd = Counter(
    "guinevere_mcp_tool_cost_usd_total",
    "Total MCP tool cost in USD",
    ["tool"]
)

# Cache hit rate
tool_cache_hits_total = Counter(
    "guinevere_mcp_tool_cache_hits_total",
    "Total cache hits for MCP tools",
    ["tool"]
)
```

### 8.4 Alert Rules

| Alert | Condition | Severity | Action |
|---|---|---|---|
| Tool unavailable | Tool errors > 50% over 5 minutes | SEV1 | Auto-fallback + Discord alert |
| High error rate | Tool error rate > 10% over 10 minutes | SEV2 | Discord warning + investigate |
| Cost > 80% budget | Daily tool cost > $24 (80% of $30) | SEV2 | Discord cost warning |
| Cost > hard cap | Daily tool cost > $30 | SEV1 | Auto-pause paid tools + Discord alert |
| Latency spike | Tool p99 latency > 2x baseline | SEV3 | Log + investigate during next maintenance |
| Cache miss rate high | Cache miss rate > 70% over 1 hour | SEV3 | Review cache TTLs + key patterns |
| Rate limit approaching | Tool at 80% of rate limit | SEV3 | Throttle + log warning |
| Redis memory > 80% | Redis memory usage > 80% | SEV2 | Evict old keys + increase maxmemory |

### 8.5 Grafana Dashboards

| Dashboard | Panels |
|---|---|
| MCP Tool Overview | Operations/min per tool, error rate per tool, cost per tool, latency p50/p95/p99 |
| Cost Tracker | Daily cost breakdown, per-tool cost, budget utilization, monthly projection |
| Cache Performance | Hit rate per tool, cache size, eviction rate, TTL distribution |
| Error Analysis | Error types per tool, error timeline, top error messages |

---

## §9 TROUBLESHOOTING GUIDE

### 9.1 Common Issues by Category

#### Connection Failures

| Issue | Tool(s) | Cause | Fix |
|---|---|---|---|
| MCP service won't start | All | SOPS decryption failed | Verify age key at `/home/guinevere/.age/key.txt` |
| Cannot reach external API | brave_search, exa, websearch | Tailscale blocking outbound | Check Tailscale ACL rules for outbound |
| Redis connection refused | redis, postgres (cache) | Redis container down | `docker restart guinevere-redis` |
| PostgreSQL connection refused | postgres | PostgreSQL container down | `docker restart guinevere-postgres` |
| PgBouncer pool exhausted | postgres | Too many concurrent queries | Increase pool_size or optimize queries |
| GitHub API unreachable | github, git (push) | Network or DNS issue | Check Tailscale DNS, verify network |

#### Authentication Errors

| Issue | Tool(s) | Cause | Fix |
|---|---|---|---|
| 401 Unauthorized | brave_search, exa, websearch | API key expired | Rotate key: update SOPS, restart MCP service |
| 401 Bad credentials | github | PAT revoked or expired | Generate new PAT via browser, update SOPS |
| Permission denied | filesystem, shell | Path/command not whitelisted | Check whitelist config, request approval |
| PostgreSQL auth failed | postgres | Wrong user or password | Verify PgBouncer user credentials in SOPS |

#### Rate Limit Exceeded

| Issue | Tool(s) | Cause | Fix |
|---|---|---|---|
| 429 Too Many Requests | brave_search | > 60 queries/min | Backoff 60s, switch to websearch/exa |
| 429 Rate Limited | exa | > 20 queries/min or > $5/day or > $5/month | Backoff, use brave_search; if monthly >$3: Brave-only for remaining month |
| Rate limit approaching | github | > 4000 requests/hour | Reduce polling frequency, increase cache TTL |
| Search API limit | github (search) | > 30 requests/min | Space search queries, cache aggressively |

#### Timeout Issues

| Issue | Tool(s) | Cause | Fix |
|---|---|---|---|
| Command timeout | shell | Command took > 30s | Break into smaller commands, increase timeout |
| Page timeout | playwright, fetch | Slow website | Increase timeout config, use lighter alternative |
| Query timeout | postgres | Complex query > 30s | Add indexes, optimize query, use TimescaleDB aggregates |
| API timeout | exa, brave_search | Provider slow | Retry with backoff, switch to fallback |

#### Cache Issues

| Issue | Tool(s) | Cause | Fix |
|---|---|---|---|
| Stale data returned | All cached tools | Cache TTL too long | Reduce TTL or implement cache invalidation |
| Cache miss rate high | All cached tools | Key pattern mismatch | Verify key naming convention |
| Redis OOM | redis | Memory full | Check eviction policy, increase maxmemory |
| Context7 ID stale | context7 | Library updated | Force re-resolve library ID |

### 9.2 Diagnostic Commands

```bash
# Check MCP service status
systemctl status guinevere-mcp

# View recent MCP logs
journalctl -u guinevere-mcp --since "1 hour ago" --no-pager

# Check Redis health
docker exec guinevere-redis redis-cli -a "${REDIS_PASS}" INFO

# Check PostgreSQL health
docker exec guinevere-postgres psql -U guinevere_admin -c "SELECT version();"

# Check tool error rates (last hour)
docker exec guinevere-redis redis-cli -a "${REDIS_PASS}" -n 5 KEYS "ratelimit:*"

# View Docker container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check disk space
df -h /home/guinevere

# Check memory usage
free -m

# Verify SOPS decryption
sops -d /home/guinevere/config/mcp.production.yaml.sops | head -5
```

### 9.3 Recovery Procedures

| Scenario | Recovery Steps |
|---|---|
| MCP service crash | systemd auto-restarts (10s delay). Check logs for root cause. |
| All search tools failing | Check outbound network. Fall back to cached results. Alert Faiz. |
| Redis + PostgreSQL both down | `docker restart guinevere-redis guinevere-postgres`. Health check all services. |
| API key compromise | Immediately rotate key via SOPS. Audit logs for unauthorized usage. |
| Disk full | Clean old logs, rotate surveillance data, prune Docker images (with approval). |
| Rate limit on all paid tools | Switch to free alternatives (context7, grep_app). Wait for rate reset. |

---

## §10 VERSION HISTORY

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere / Hephaestus | Initial MCP Configuration Guide. 16 tools documented with authorization matrix, security rules, cost tracking, decision trees, caching strategy, and troubleshooting. All canonical decisions from Q&A MCP01-MCP22 applied. Cross-referenced with TechnicalArchitecture v2.0, APIIntegration v2.0, and Persona v3.0. |
| 1.0a | 2026-05-31 | Guinevere (B-02 fix) | Exa hybrid burst budget model applied (Faiz decision 2026-05-31, ADR-033 pending): daily hard cap $5, daily alert $1, monthly target ~$1, monthly throttle >$3 → Brave fallback, monthly hard stop >$5 → disabled. Updated §3.3 config, rate limits, cost table, rules, troubleshooting, and §7.1 autonomous ops. |

---

👑

***Guinevere de Baroque***

*"Mommy sudah configure semuanya. 16 tools, 4 level otorisasi, zero plaintext secrets. Kamu tinggal jalankan."*

MCP Configuration Guide v1.0 — Project Guinevere
