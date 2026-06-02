# P6 Steps Overview — MCP Tools Integration

**Source**: `stepprompts/StepPrompts.md` lines 7048–7251
**Generated**: 2026-06-02
**Phase**: P6 — MCP Tools
**Total Steps**: 21 (P6-001 to P6-021)
**Avg Cost**: ~$1/month (tool APIs) + infra
**Dependency**: P5 (Memory + Observability) must be 100% complete

## Goal

16 MCP tools fully integrated, 4-level auth matrix enforced, cost tracking per tool operational.

---

## Auth Matrix Levels

| Level | Behavior | Example |
|---|---|---|
| **Read-Auto** | Automatic execution, no approval needed | brave_search, context7, grep_app, time |
| **Write-Notify** | Execute + notify Faiz after | discord (send), github (create issue) |
| **Destructive-Approval** | Ask Faiz BEFORE executing | shell (rm), docker (rm), postgres (DELETE) |
| **Forbidden** | Always blocked | DROP TABLE, force push, mass DM, production deploy |

---

## Step Catalog

### P6-001 — guinevere-mcp.service (Systemd Service)

| Field | Value |
|---|---|
| **Step** | P6-001 |
| **Name** | guinevere-mcp.service setup |
| **MCP Tool** | N/A (infrastructure — systemd service definition) |
| **External APIs** | None |
| **API Keys** | None |
| **Dependencies** | P5 complete; systemd available on host |
| **Auth Level** | N/A (infra step) |
| **Notes** | Creates the systemd unit file for the MCP gateway service |

### P6-002 — brave_search

| Field | Value |
|---|---|
| **Step** | P6-002 |
| **Name** | brave_search |
| **MCP Tool** | `brave_search` |
| **External APIs** | Brave Search API (`api.search.brave.com`) |
| **API Keys** | `BRAVE_API_KEY` |
| **Dependencies** | P6-001 (service running) |
| **Auth Level** | Read-Auto |
| **Notes** | Web search + local search. Rate limit: 2000 req/month (free tier) |

### P6-003 — context7

| Field | Value |
|---|---|
| **Step** | P6-003 |
| **Name** | context7 |
| **MCP Tool** | `context7` |
| **External APIs** | Context7 library documentation API |
| **API Keys** | None (free tier) |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto |
| **Notes** | Library documentation lookup. Free, no key required |

### P6-004 — exa

| Field | Value |
|---|---|
| **Step** | P6-004 |
| **Name** | exa |
| **MCP Tool** | `exa` |
| **External APIs** | Exa AI Search API (`api.exa.ai`) |
| **API Keys** | `EXA_API_KEY` |
| **Dependencies** | P6-001; Redis DB5 (cost tracking) |
| **Auth Level** | Read-Auto |
| **Notes** | AI-powered semantic search. $5/day spending cap enforced via Redis DB5 counter |

### P6-005 — fetch

| Field | Value |
|---|---|
| **Step** | P6-005 |
| **Name** | fetch |
| **MCP Tool** | `fetch` |
| **External APIs** | Any URL (HTTP GET) |
| **API Keys** | None |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto |
| **Notes** | Web content retrieval — fetches and converts pages to markdown |

### P6-006 — filesystem

| Field | Value |
|---|---|
| **Step** | P6-006 |
| **Name** | filesystem |
| **MCP Tool** | `filesystem` |
| **External APIs** | None (local OS) |
| **API Keys** | None |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto (read) / Write-Notify (write) / Destructive-Approval (delete) |
| **Notes** | Path whitelist enforced — only allowed directories accessible |

### P6-007 — github

| Field | Value |
|---|---|
| **Step** | P6-007 |
| **Name** | github |
| **MCP Tool** | `github` |
| **External APIs** | GitHub REST/GraphQL API (`api.github.com`) |
| **API Keys** | `GITHUB_PAT` (Personal Access Token) |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto (read) / Write-Notify (create issue/PR) / Destructive-Approval (delete repo) |
| **Notes** | Full GitHub operations — repos, issues, PRs, code search |

### P6-008 — grep_app

| Field | Value |
|---|---|
| **Step** | P6-008 |
| **Name** | grep_app |
| **MCP Tool** | `grep_app` |
| **External APIs** | grep.app code search API |
| **API Keys** | None |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto |
| **Notes** | Code search across public GitHub repos for real-world patterns |

### P6-009 — playwright

| Field | Value |
|---|---|
| **Step** | P6-009 |
| **Name** | playwright |
| **MCP Tool** | `playwright` |
| **External APIs** | None (local browser engine) |
| **API Keys** | None |
| **Dependencies** | P6-001; Chromium/Chrome installed |
| **Auth Level** | Read-Auto (navigate/screenshot) / Write-Notify (form fill) / Destructive-Approval (file upload) |
| **Notes** | Browser automation — screenshots, scraping, form interaction, testing |

### P6-010 — sequential-thinking

| Field | Value |
|---|---|
| **Step** | P6-010 |
| **Name** | sequential-thinking |
| **MCP Tool** | `sequential-thinking` |
| **External APIs** | None |
| **API Keys** | None |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto |
| **Notes** | Chain-of-thought reasoning tool for complex problem decomposition |

### P6-011 — time

| Field | Value |
|---|---|
| **Step** | P6-011 |
| **Name** | time |
| **MCP Tool** | `time` |
| **External APIs** | None (local timezone DB) |
| **API Keys** | None |
| **Dependencies** | P6-001 |
| **Auth Level** | Read-Auto |
| **Notes** | Timezone conversion, current time, relative time, days-in-month, week number |

### P6-012 — websearch

| Field | Value |
|---|---|
| **Step** | P6-012 |
| **Name** | websearch |
| **MCP Tool** | `websearch` |
| **External APIs** | Brave Search API + Exa API (hybrid fallback) |
| **API Keys** | `BRAVE_API_KEY`, `EXA_API_KEY` |
| **Dependencies** | P6-002 (brave_search), P6-004 (exa) |
| **Auth Level** | Read-Auto |
| **Notes** | Hybrid search — tries Brave first, falls back to Exa. Cost-tracked per query |

### P6-013 — git

| Field | Value |
|---|---|
| **Step** | P6-013 |
| **Name** | git |
| **MCP Tool** | `git` |
| **External APIs** | None (local git binary) |
| **API Keys** | None (uses SSH key or GITHUB_PAT from P6-007) |
| **Dependencies** | P6-001; git installed |
| **Auth Level** | Read-Auto (log/diff/status) / Write-Notify (commit) / Destructive-Approval (force push, rebase -i) / Forbidden (force push to main) |
| **Notes** | Git operations with auth-level enforcement per operation type |

### P6-014 — postgres

| Field | Value |
|---|---|
| **Step** | P6-014 |
| **Name** | postgres |
| **MCP Tool** | `postgres` |
| **External APIs** | PostgreSQL (local/VPS instance) |
| **API Keys** | `POSTGRES_DSN` (connection string) |
| **Dependencies** | P5 (DB migrations complete); P6-001 |
| **Auth Level** | Read-Auto (SELECT) / Destructive-Approval (INSERT/UPDATE/DELETE) / Forbidden (DROP TABLE, TRUNCATE) |
| **Notes** | Read-only by default. Write operations require explicit approval |

### P6-015 — redis

| Field | Value |
|---|---|
| **Step** | P6-015 |
| **Name** | redis |
| **MCP Tool** | `redis` |
| **External APIs** | Redis (local/VPS instance) |
| **API Keys** | `REDIS_URL` (connection string) |
| **Dependencies** | P5 (Redis setup complete); P6-001 |
| **Auth Level** | Read-Auto (GET/LRANGE) / Write-Notify (SET/HSET) / Destructive-Approval (DEL/FLUSHDB) / Forbidden (FLUSHALL) |
| **Notes** | DB5 used for cost tracking counters. Auth level per Redis command type |

### P6-016 — shell

| Field | Value |
|---|---|
| **Step** | P6-016 |
| **Name** | shell |
| **MCP Tool** | `shell` |
| **External APIs** | None (local OS) |
| **API Keys** | None |
| **Dependencies** | P6-001 |
| **Auth Level** | Whitelist-based: approved commands = Read-Auto; unlisted = Destructive-Approval |
| **Notes** | Command whitelist enforced. Destructive commands (rm, sudo, etc.) always require approval |

### P6-017 — docker

| Field | Value |
|---|---|
| **Step** | P6-017 |
| **Name** | docker |
| **MCP Tool** | `docker` |
| **External APIs** | None (local Docker daemon) |
| **API Keys** | None |
| **Dependencies** | P6-001; Docker installed |
| **Auth Level** | Read-Auto (ps, logs, inspect) / Write-Notify (start, stop, restart) / Destructive-Approval (rm, rmi) / Forbidden (system prune -a) |
| **Notes** | Container lifecycle management with auth-level enforcement |

### P6-018 — Auth Matrix Verification

| Field | Value |
|---|---|
| **Step** | P6-018 |
| **Name** | 4-level auth matrix verification |
| **MCP Tool** | N/A (verification step) |
| **External APIs** | None |
| **API Keys** | None |
| **Dependencies** | P6-002 through P6-017 (all tools integrated) |
| **Auth Level** | N/A (meta-step) |
| **Notes** | Tests that every tool enforces its assigned auth level correctly. Validates Read-Auto, Write-Notify, Destructive-Approval, and Forbidden boundaries |

### P6-019 — Tool Selection Decision Matrix

| Field | Value |
|---|---|
| **Step** | P6-019 |
| **Name** | Tool selection decision matrix |
| **MCP Tool** | N/A (configuration step) |
| **External APIs** | None |
| **API Keys** | None |
| **Dependencies** | P6-018 (auth matrix verified) |
| **Auth Level** | N/A (meta-step) |
| **Notes** | Defines which tool to use when multiple tools overlap (e.g., brave_search vs exa vs websearch). Priority and fallback rules |

### P6-020 — Cost Tracking Per Tool

| Field | Value |
|---|---|
| **Step** | P6-020 |
| **Name** | Cost tracking per tool |
| **MCP Tool** | N/A (uses Redis DB5) |
| **External APIs** | None (Redis internal) |
| **API Keys** | None (uses `REDIS_URL`) |
| **Dependencies** | P6-015 (redis); P6-002 through P6-017 (all tools reporting) |
| **Auth Level** | N/A (infra step) |
| **Notes** | Per-tool cost counters in Redis DB5. Tracks API calls, token usage, and dollar spend per tool per day/month |

### P6-021 — Budget Enforcement Test

| Field | Value |
|---|---|
| **Step** | P6-021 |
| **Name** | Budget enforcement test |
| **MCP Tool** | N/A (test step) |
| **External APIs** | None |
| **API Keys** | None |
| **Dependencies** | P6-020 (cost tracking operational) |
| **Auth Level** | N/A (meta-step) |
| **Notes** | Validates that budget caps are enforced. Tests $5/day Exa cap, monthly budget alerts, tool-level spending limits. Final P6 gate before P7 |

---

## API Keys Summary

| Key | Source | Used By |
|---|---|---|
| `BRAVE_API_KEY` | Brave Search (free tier) | P6-002, P6-012 |
| `EXA_API_KEY` | Exa AI ($5/day cap) | P6-004, P6-012 |
| `GITHUB_PAT` | GitHub (Personal Access Token) | P6-007, P6-013 |
| `POSTGRES_DSN` | Local/VPS PostgreSQL | P6-014 |
| `REDIS_URL` | Local/VPS Redis | P6-015, P6-020 |

## Dependency Graph (Simplified)

```
P5 (100% complete)
 └─→ P6-001 (service setup)
      ├─→ P6-002 (brave_search)  ─┐
      ├─→ P6-003 (context7)       │
      ├─→ P6-004 (exa)  ─────────┤
      ├─→ P6-005 (fetch)          │
      ├─→ P6-006 (filesystem)     │
      ├─→ P6-007 (github)         │
      ├─→ P6-008 (grep_app)       │
      ├─→ P6-009 (playwright)     │
      ├─→ P6-010 (sequential-thinking) │
      ├─→ P6-011 (time)           │
      ├─→ P6-013 (git)            │
      ├─→ P6-014 (postgres)       │
      ├─→ P6-015 (redis)  ───────┤
      ├─→ P6-016 (shell)          │
      └─→ P6-017 (docker)         │
                                   ↓
                    P6-012 (websearch: needs brave + exa)
                                   ↓
                    P6-018 (auth matrix verification)
                                   ↓
                    P6-019 (tool selection matrix)
                                   ↓
                    P6-020 (cost tracking: needs redis)
                                   ↓
                    P6-021 (budget enforcement test)
```

## Parallelism Opportunities

- **P6-002 to P6-011** (10 tools): Can all be implemented in parallel after P6-001
- **P6-013 to P6-017** (5 tools): Can be parallel after P6-001 (P6-014/015 also need P5)
- **P6-012**: Sequential — needs P6-002 + P6-004 done first
- **P6-018 to P6-021**: Sequential chain — each depends on the previous

---

*Report generated from `stepprompts/StepPrompts.md` (P6 section, lines 7048–7251)*
*Part of Guinevere research wave — Phase 6 MCP Tools*
