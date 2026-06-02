# P6-004 & P6-003: Exa Search API + Context7 Documentation Lookup — Research Report

> **Research scope**: API endpoints, auth methods, response schemas, pricing, existing MCP implementations
> **Date**: 2026-06-02
> **Researcher**: Librarian sub-agent
> **Downstream**: Guinevere P6-004 (exa-mcp with $5/day cap), P6-003 (context7-mcp free)
> **Auth level**: Read-Auto for both

---

## 1. Exa AI Search API (P6-004)

### 1.1 API Overview

| Field | Value |
|---|---|
| Base URL | `https://api.exa.ai` |
| Primary endpoint | `POST /search` |
| Content retrieval | `POST /contents` |
| Similar links | `POST /findSimilar` |
| Answer endpoint | `POST /answer` |
| OpenAPI spec | [exa-labs/openapi-spec](https://github.com/exa-labs/openapi-spec/blob/master/exa-openapi-spec.yaml) |
| Official docs | [exa.ai/docs/reference/search](https://exa.ai/docs/reference/search) |

### 1.2 Authentication

Two auth methods supported (mutually equivalent):

```
# Method 1: x-api-key header
x-api-key: YOUR_EXA_API_KEY

# Method 2: Bearer token
Authorization: Bearer YOUR_EXA_API_KEY
```

- API key obtained from: [dashboard.exa.ai/api-keys](https://dashboard.exa.ai/api-keys)
- Also supports x402 on-chain payment (USDC) for keyless access

### 1.3 Request Parameters (POST /search)

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | **Yes** | — | Natural language search query |
| `type` | string | No | `"auto"` | `auto`, `fast`, `instant`, `deep-lite`, `deep`, `deep-reasoning` |
| `numResults` | integer | No | `10` | Number of results (1–100) |
| `category` | string | No | — | `company`, `people`, `research paper`, `news`, `personal site`, `financial report` |
| `includeDomains` | string[] | No | — | Only results from these domains |
| `excludeDomains` | string[] | No | — | Exclude these domains |
| `startPublishedDate` | string | No | — | ISO 8601 date filter |
| `endPublishedDate` | string | No | — | ISO 8601 date filter |
| `contents.text` | bool/obj | No | — | Full page text as markdown |
| `contents.highlights` | bool/obj | No | — | Key excerpts relevant to query |
| `contents.summary` | bool/obj | No | — | LLM-generated summary |
| `outputSchema` | object | No | — | JSON schema for structured output |
| `stream` | boolean | No | `false` | SSE streaming |

### 1.4 Response Schema

```json
{
  "requestId": "b5947044c4b78efa9552a7c89b306d95",
  "searchType": "auto",
  "results": [
    {
      "title": "Page Title",
      "url": "https://example.com/page",
      "id": "https://example.com/page",
      "publishedDate": "2024-01-15T00:00:00.000Z",
      "author": "Author Name",
      "image": "https://example.com/image.png",
      "favicon": "https://example.com/favicon.ico",
      "text": "Full page content as markdown...",
      "highlights": ["Key excerpt from the page..."],
      "highlightScores": [0.46],
      "summary": "LLM-generated summary..."
    }
  ],
  "output": {
    "content": "Synthesized answer or structured object",
    "grounding": [
      { "field": "content", "citations": [{"url": "...", "title": "..."}], "confidence": "high" }
    ]
  },
  "costDollars": {
    "total": 0.007
  }
}
```

### 1.5 Pricing (Updated March 2026)

| Search Type | Base price (up to 10 results) | Per result beyond 10 |
|---|---|---|
| `instant`, `auto`, `fast` | **$0.007 / request** | N/A (capped at 10 for x402) |
| `deep-lite` | $0.012 / request | N/A (capped at 10) |
| `deep` | $0.012 / request | N/A (capped at 10) |
| `deep-reasoning` | $0.015 / request | N/A (capped at 10) |

**Bulk pricing** (per 1,000 requests):

| Endpoint | Price per 1k |
|---|---|
| Search (auto/fast/instant) with contents | $7 |
| Additional results beyond 10 | $1/1k |
| Deep Search | $12 |
| Deep-Reasoning Search | $15 |
| Contents (dedicated) | $1/1k pages |
| AI Summaries | $1/1k |

**Free tier**: 1,000 searches/month, no credit card required.

**$5/day cap calculation**:
- At $0.007/search (auto): $5 / $0.007 = **~714 searches/day**
- At $0.012/search (deep): $5 / $0.012 = **~416 searches/day**
- With summaries ($0.001/summary): $5 / ($0.007 + $0.001) = **~625 searches/day**
- **Recommended cap**: 700 auto searches/day to stay under $5

### 1.6 Existing MCP Implementations

#### Official: exa-labs/exa-mcp-server

- **Repo**: [github.com/exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server)
- **SHA**: `ad888a188cdefbe832c9feed2c3a97d1cb93cb35`
- **Package**: `exa-mcp-server` v3.2.1
- **Language**: TypeScript (Node 20+)
- **Transport**: stdio (CLI) + Vercel serverless (HTTP)
- **Dependencies**: `@modelcontextprotocol/sdk`, `exa-js`, `zod`, `jose`
- **Tools exposed**:
  - `web_search_exa` — basic web search with highlights
  - `web_fetch_exa` — content retrieval by URL
  - `web_search_advanced_exa` — advanced search with filters
  - `deep_search_exa` — deep search with synthesis
  - `company_research_exa` — company-focused search
  - `people_search_exa` / `linkedin_search_exa` — people/LinkedIn search
  - `exa_code_search` — code search
  - `deep_research_check_exa` / `deep_research_start_exa` — research tasks
- **Auth pattern**: API key from `EXA_API_KEY` env var, or OAuth JWT via `x-api-key` header
- **Key file**: `src/tools/webSearch.ts` — uses `Exa` client from `exa-js` SDK
- **License**: MIT

#### Community: egoist/exa-mcp

- **Repo**: [github.com/egoist/exa-mcp](https://github.com/egoist/exa-mcp)
- **Description**: Lightweight MCP server for Exa Search API
- **Language**: TypeScript

#### Community: spences10/mcp-omnisearch

- **Repo**: [github.com/spences10/mcp-omnisearch](https://github.com/spences10/mcp-omnisearch)
- **Description**: Unified MCP for Tavily, Brave, Kagi, Exa

---

## 2. Context7 Documentation Lookup API (P6-003)

### 2.1 API Overview

| Field | Value |
|---|---|
| Base URL | `https://context7.com/api` |
| Library search | `GET /v2/libs/search` |
| Get context | `GET /v2/context` |
| Refresh library | `POST /v1/refresh` (auth required) |
| Add library | `POST /v2/add/repo/{provider}` (auth required) |
| OpenAPI spec | [context7.com/openapi.json](https://context7.com/openapi.json) |
| Official docs | [context7.com/docs/api-guide](https://context7.com/docs/api-guide) |
| Parent company | Upstash Inc. |

### 2.2 Authentication

- **Optional**: `Authorization: Bearer <key>` or `context7-api-key` header
- **Free tier**: No auth required (works without API key)
- **API key prefix**: `ctx7sk`
- **API keys obtained from**: [context7.com/dashboard](https://context7.com/dashboard)

### 2.3 Endpoints

#### GET /v2/libs/search — Search Libraries

```bash
curl "https://context7.com/api/v2/libs/search?libraryName=react&query=I%20need%20to%20manage%20state" \
  -H "Authorization: Bearer CONTEXT7_API_KEY"
```

**Parameters**:
| Parameter | Type | Required | Description |
|---|---|---|---|
| `libraryName` | string | Yes | Library name to search for |
| `query` | string | Yes | User's question — used for relevance ranking |

**Response**:
```json
{
  "results": [
    {
      "id": "/facebook/react",
      "title": "React",
      "description": "The library for web and native user interfaces",
      "branch": "main",
      "lastUpdateDate": "2026-01-15T10:30:00.000Z",
      "state": "finalized",
      "totalTokens": 607822,
      "totalSnippets": 3629,
      "stars": 131745,
      "trustScore": 10,
      "benchmarkScore": 95.5,
      "versions": ["v19.0.0", "v18.3.1"]
    }
  ]
}
```

#### GET /v2/context — Get Documentation Context

```bash
curl "https://context7.com/api/v2/context?libraryId=/vercel/next.js&query=How%20to%20implement%20auth" \
  -H "Authorization: Bearer CONTEXT7_API_KEY"
```

**Parameters**:
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `libraryId` | string | Yes | — | Context7-compatible library ID (`/owner/repo`) |
| `query` | string | Yes | — | Natural language question |
| `type` | string | No | `"txt"` | `"json"` or `"txt"` |
| `fast` | string | No | `"false"` | Skip LLM reranking for lower latency |

**Response (JSON)**:
```json
{
  "codeSnippets": [
    {
      "codeTitle": "Middleware Authentication Example",
      "codeDescription": "Shows how to implement authentication in middleware",
      "codeLanguage": "typescript",
      "codeTokens": 150,
      "codeId": "https://github.com/vercel/next.js/blob/canary/docs/middleware.mdx#_snippet_0",
      "pageTitle": "Middleware",
      "codeList": [
        { "language": "typescript", "code": "import { NextResponse } from 'next/server'\n..." }
      ]
    }
  ],
  "infoSnippets": [
    {
      "pageId": "https://github.com/vercel/next.js/blob/canary/docs/middleware.mdx",
      "breadcrumb": "Routing > Middleware",
      "content": "Middleware allows you to run code before a request...",
      "contentTokens": 200
    }
  ]
}
```

### 2.4 Library ID Format

| Format | Example | Description |
|---|---|---|
| `/owner/repo` | `/vercel/next.js` | GitHub repository |
| `/websites/domain` | `/websites/uploadcare_com` | Website source |
| `/llmstxt/name` | `/llmstxt/example` | llms.txt source |
| `/owner/repo/version` | `/vercel/next.js/v15.1.8` | Version-pinned (slash) |
| `/owner/repo@version` | `/vercel/next.js@v15.1.8` | Version-pinned (@) |

### 2.5 Pricing

| Plan | Price | Included API Calls | Additional Calls |
|---|---|---|---|
| **Free** | $0 | 1,000/month | Blocked (+ 20 bonus/day) |
| **Pro** | $10/seat/month | 5,000/seat/month | $10/1,000 |
| **Enterprise** | Custom ($2.50–$30/user) | 5,000/seat/month | $10/1,000 |

**For Guinevere P6-003 (free tier)**:
- 1,000 API calls/month = ~33 calls/day
- When blocked: 20 bonus calls/day
- No credit card required
- For typical MCP usage (library lookup + context query): each user question uses 2 API calls → ~16 questions/day on free tier

### 2.6 Existing MCP Implementations

#### Official: upstash/context7

- **Repo**: [github.com/upstash/context7](https://github.com/upstash/context7)
- **SHA**: `c436700959bf0c277aa02c57195b5a24778cf8aa`
- **MCP package**: `packages/mcp/`
- **Language**: TypeScript monorepo (pnpm workspaces)
- **Transport**: stdio + HTTP (Express + StreamableHTTPServerTransport)
- **Tools exposed**:
  - `resolve-library-id` — search for libraries, return Context7-compatible IDs
  - `query-docs` — fetch documentation context for a library
- **Auth pattern**: 
  - stdio: `--api-key` flag or `CONTEXT7_API_KEY` env var
  - HTTP: `Authorization: Bearer`, `context7-api-key` header, `x-api-key` header
  - Anonymous access also supported (no auth)
- **License**: MIT
- **Key implementation detail**: The MCP server at `packages/mcp/src/index.ts` uses `@modelcontextprotocol/sdk` and registers two tools via `server.registerTool()`. The API calls go to `https://context7.com/api/v2/libs/search` and `https://context7.com/api/v2/context` using native `fetch()`.

#### Community alternatives:
- `lrstanley/context7-http` — HTTP SSE + Streamable Context7 MCP
- `quiint/c7-mcp-server` — Unofficial Context7 MCP
- `arabold/docs-mcp-server` — Open-source alternative to Context7
- `akbxr/zed-mcp-server-context7` — Context7 for Zed editor

---

## 3. Implementation Recommendations for Guinevere

### 3.1 P6-004: exa-mcp (with $5/day cap)

**Approach**: Build custom lightweight MCP wrapping Exa Search API directly (no exa-js SDK dependency).

**Rationale**:
- The official `exa-mcp-server` is feature-rich but heavy (12 tools, OAuth, deep research)
- For Guinevere's needs, we only need: `web_search` + `web_fetch` (2 tools max)
- Direct HTTP `fetch()` to `https://api.exa.ai/search` is simpler
- The `costDollars.total` field in responses lets us track spend per request

**Daily budget enforcement**:
```
MAX_DAILY_SPEND = 5.00  // $5/day
Track running total from costDollars.total in each response
Reject requests when daily cap reached
Reset counter at midnight UTC
```

**Suggested tool design**:
```typescript
// Tool 1: web_search_exa
Input: { query: string, numResults?: number }
Output: { results: [{title, url, highlights}], costDollars: {total, daily} }

// Tool 2: web_fetch_exa  
Input: { urls: string[] }
Output: { results: [{url, text}], costDollars: {total, daily} }
```

**Auth**: `EXA_API_KEY` from env, pass as `x-api-key` header.

### 3.2 P6-003: context7-mcp (free)

**Approach**: Build custom lightweight MCP wrapping Context7 API directly.

**Rationale**:
- The official `upstash/context7` monorepo is large (CLI, SDK, MCP, plugins)
- For Guinevere, we only need the 2 core tools
- Direct `fetch()` to `https://context7.com/api/v2/*` is trivial
- No auth required for free tier (anonymous access works)

**Suggested tool design**:
```typescript
// Tool 1: resolve-library-id
Input: { query: string, libraryName: string }
Output: { results: [{id, title, description, totalSnippets, trustScore, benchmarkScore}] }

// Tool 2: query-docs
Input: { libraryId: string, query: string }
Output: { codeSnippets: [...], infoSnippets: [...] }
```

**Auth**: Optional `CONTEXT7_API_KEY` from env (for higher limits), works without it.

### 3.3 Shared MCP Server Pattern

Both tools can live in a single MCP server:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({ name: "guinevere-search", version: "1.0.0" });

// Register exa tools (P6-004)
server.registerTool("web_search_exa", { ... });
server.registerTool("web_fetch_exa", { ... });

// Register context7 tools (P6-003)  
server.registerTool("resolve-library-id", { ... });
server.registerTool("query-docs", { ... });

const transport = new StdioServerTransport();
await server.connect(transport);
```

**Dependencies needed**:
- `@modelcontextprotocol/sdk` (^1.12.1)
- `zod` (^3.22.4) — for input validation

**No SDK dependencies needed** — both APIs are simple REST with native `fetch()`.

---

## 4. Source Evidence & Permalinks

### Exa
- Official MCP server: [exa-labs/exa-mcp-server @ `ad888a1`](https://github.com/exa-labs/exa-mcp-server/tree/ad888a188cdefbe832c9feed2c3a97d1cb93cb35)
  - Config: [src/tools/config.ts](https://github.com/exa-labs/exa-mcp-server/blob/ad888a188cdefbe832c9feed2c3a97d1cb93cb35/src/tools/config.ts)
  - Web search tool: [src/tools/webSearch.ts](https://github.com/exa-labs/exa-mcp-server/blob/ad888a188cdefbe832c9feed2c3a97d1cb93cb35/src/tools/webSearch.ts)
  - Auth util: [src/utils/auth.ts](https://github.com/exa-labs/exa-mcp-server/blob/ad888a188cdefbe832c9feed2c3a97d1cb93cb35/src/utils/auth.ts)
- API docs: [exa.ai/docs/reference/search](https://exa.ai/docs/reference/search)
- Pricing: [exa.ai/pricing](https://exa.ai/pricing?tab=api)
- OpenAPI spec: [github.com/exa-labs/openapi-spec](https://github.com/exa-labs/openapi-spec/blob/master/exa-openapi-spec.yaml)

### Context7
- Official MCP server: [upstash/context7 @ `c436700`](https://github.com/upstash/context7/tree/c436700959bf0c277aa02c57195b5a24778cf8aa)
  - MCP server entry: [packages/mcp/src/index.ts](https://github.com/upstash/context7/blob/c436700959bf0c277aa02c57195b5a24778cf8aa/packages/mcp/src/index.ts)
  - API client: [packages/mcp/src/lib/api.ts](https://github.com/upstash/context7/blob/c436700959bf0c277aa02c57195b5a24778cf8aa/packages/mcp/src/lib/api.ts)
  - Constants: [packages/mcp/src/lib/constants.ts](https://github.com/upstash/context7/blob/c436700959bf0c277aa02c57195b5a24778cf8aa/packages/mcp/src/lib/constants.ts)
- API docs: [context7.com/docs/api-guide](https://context7.com/docs/api-guide)
- Pricing: [context7.com/plans](https://context7.com/plans)
- OpenAPI spec: [context7.com/openapi.json](https://context7.com/openapi.json)

---

## 5. Cost Summary Comparison

| Metric | Exa (P6-004) | Context7 (P6-003) |
|---|---|---|
| Free tier | 1,000 searches/month | 1,000 API calls/month |
| Paid base | $0.007/search (auto) | $10/1k calls |
| $5/day capacity | ~714 auto searches | ~5,000 calls (Pro) |
| Auth required | Yes (API key) | Optional (works without) |
| Auth method | `x-api-key` header | `Authorization: Bearer` |
| Streaming | SSE supported | N/A |
| MCP SDK needed | `@modelcontextprotocol/sdk` | `@modelcontextprotocol/sdk` |
| Response tracking | `costDollars.total` per response | No built-in cost tracking |
| Daily cap mechanism | Sum `costDollars.total` responses | Track call count |
