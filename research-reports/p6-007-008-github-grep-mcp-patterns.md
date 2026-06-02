# Research Report: GitHub MCP Server & grep.app Code Search Patterns
**Date**: 2026-06-02
**Purpose**: P6-007 (github MCP — Write-Notify auth) & P6-008 (grep_app — Read-Auto auth)
**Status**: Complete

---

## 1. GitHub MCP Server Implementations (Python)

### 1.1 Most Relevant: `shreeyanshi25/github-mcp-server` ⭐ RECOMMENDED REFERENCE

**URL**: https://github.com/shreeyanshi25/github-mcp-server

**Architecture**:
```
├── server.py                  ← FastAPI + FastMCP (SSE + Streamable HTTP)
├── stdio_server.py            ← Claude Desktop entry point (GitHub tools)
├── github_client.py           ← Async GitHub REST API wrapper (httpx)
├── auth.py                    ← X-MCP-API-Key middleware (timing-safe)
├── tools/
│   ├── repos.py               ← list_repos, get_repo_info, create_branch, search_code
│   ├── issues.py              ← list_issues, get_issue, create_issue, add_comment
│   └── prs.py                 ← list_prs, get_pr, merge_pr
```

**Key features matching Guinevere needs**:
- FastMCP framework (Python MCP SDK)
- httpx-based async client
- Auth middleware with API key (timing-safe)
- Separate tool files per domain
- Dockerfile + render.yaml for deployment
- Production-grade

**11 Tools**: `list_repos`, `get_repo_info`, `create_branch`, `search_code`, `list_issues`, `get_issue`, `create_issue`, `add_comment`, `list_prs`, `get_pr`, `merge_pr`

---

### 1.2 Most Comprehensive: `software-engineer-mj/github-mcp`

**URL**: https://github.com/software-engineer-mj/github-mcp

**87 tools across 25 categories** — the largest known Python GitHub MCP server. Categories:
| Category | Tools | Description |
|---|---|---|
| **Repositories** | 7 | List, get, create, fork; list commits; get commit; get file contents |
| **Issues** | 6 | List, get, create, update, list comments, create comment |
| **Pull Requests** | 8 | List, get, create, update, merge; view files/commits; update branch |
| **Search** | 4 | Search repos, code, issues, users |
| **Files** | 2 | Create/update and delete files |
| **Git** | Push files (multi-file commits) |

**Scopes per domain**:
- `repo` → repos, issues, PRs, branches, files, tags
- `read:org` → orgs, members, projects
- `workflow` → Actions
- `read:discussion` → discussions
- `project` → Projects V2

Tool file structure: `tools/repositories.py`, `tools/issues.py`, `tools/pull_requests.py`, `tools/files.py`, `tools/search.py`, etc.

---

### 1.3 Official GitHub MCP Server (Go, not Python)

**URL**: https://github.com/github/github-mcp-server

Official by GitHub. Written in **Go**. Key design patterns:
- **Toolsets**: `repos`, `issues`, `pull_requests`, `actions`, `code_security`, `discussions`, `gists`, `git`, `labels`, `notifications`, `orgs`, `projects`, `users`, `stargazers`, `copilot`, `dependabot`
- **Tool granularity**: `issue_read` + `issue_write` (separate read/write)
- **CLI flags**: `--toolsets` + `--tools` for fine-grained control; `--read-only` for safety
- **OAuth 2.0**: Uses OAuth device flow (not PAT) — `repo`, `read:org`, `workflow` scopes

Not directly reusable for Python, but the toolsets/read-only pattern is worth adopting.

---

### 1.4 Other Python Implementations

| Repo | Framework | Notable |
|---|---|---|
| `nhevers/mcp-github` | custom (`mcpgithub`) | Simple: `list_repos`, `get_file`, `create_issue`, `search_code`, `create_pr` |
| `SyedAli9135/Github-MCP-Server` | FastMCP | Production-ready, full search syntax |
| `fleXRPL/github-mcp` | stdio | Lightweight, good parameter schemas |
| `mcpnexus-registry/pygithub-mcp-server` | PyGithub | Uses PyGithub SDK, not httpx |
| `saiadupa/personalized-mcp-server` | custom HTTP | Linear + GitHub, context_pack, on-demand clone |

---

## 2. grep.app API & MCP Patterns

### 2.1 grep.app REST API

**Base URL**: `https://grep.app/api/search`
**Method**: GET
**Parameters**:

| Param | Type | Description |
|---|---|---|
| `q` | string | Search query (literal code pattern) |
| `page` | integer | Page number for pagination |
| `regexp` | boolean | Treat query as regex (`regexp=true`) |
| `words` | boolean | Whole word matching (`words=true`) |
| `f.lang` | string | Language filter (e.g., "Python", "TypeScript") |
| `f.repo` | string | Repo filter "owner/repo" |
| `f.path` | string | Path filter (e.g., "src/") |
| `format` | string | Format hint (some clients use `format=e`) |

**Response structure**:
```json
{
  "hits": {
    "total": 12345,
    "hits": [
      {
        "repo": "owner/repo",
        "path": "src/main.py",
        "line": "async def main():",
        "content": "```python\nasync def main():\n    ...\n```",
        "language": "Python",
        "branch": "main"
      }
    ]
  },
  "facets": { "lang": [...], "repo": [...] }
}
```

**Rate limits**: Returns 429 on rate limit. Clients implement `time.sleep(1)` between pages.

### 2.2 Official Vercel Grep MCP Server

**URL**: `https://mcp.grep.app` (streamable HTTP MCP)
**Transport**: HTTP (no local server needed)
**Tool exposed**: `searchGitHub` (this is the tool name Vercel uses!)

```json
{
  "mcpServers": {
    "grep": {
      "url": "https://mcp.grep.app"
    }
  }
}
```

Built in "an afternoon" using `mcp-handler` package. The tool signature:
- `query` (required): Literal code pattern
- `language`: Programming language filter (array)
- `repo`: Repository filter
- `path`: File path filter
- `useRegexp`: Boolean for regex mode
- `matchCase`: Boolean for case sensitivity
- `matchWholeWords`: Boolean

### 2.3 Python grep.app MCP Server: `galprz/grep-mcp` ⭐ RECOMMENDED

**URL**: https://github.com/galprz/grep-mcp
**PyPI**: `grep-mcp` v1.0.3
**Framework**: FastMCP + aiohttp + starlette + uvicorn

**Tool**: `grep_query(query, language=None, repo=None, path=None)`

**Architecture**:
```python
@mcp.tool()
async def grep_query(
    query: str, 
    language: Optional[str] = None,
    repo: Optional[str] = None,
    path: Optional[str] = None
) -> str:
    # Build params
    params = {"q": query}
    if language: params["f.lang"] = language
    if repo: params["f.repo"] = repo
    if path: params["f.path"] = path

    # Async call to grep.app API
    async with aiohttp.ClientSession(timeout=...) as session:
        async with session.get("https://grep.app/api/search", params=params) as response:
            if response.status == 429:
                raise GrepAPIRateLimitError(...)
            data = await response.json()
    
    # Format structured response
    return formatted_results  # Markdown-style with code blocks
```

**Transport modes**: Both stdio (`python -m grep_mcp`) and SSE (`python -m grep_mcp --transport sse --port 8080`).

**Key lesson**: If Guinevere already has an `httpx` client for GitHub, grep.app calls can use the same `httpx.AsyncClient` for consistency (instead of aiohttp).

### 2.4 Node.js grep.app MCP Server: `ai-tools-all/grep_app_mcp`

**URL**: https://github.com/ai-tools-all/grep_app_mcp
**npm**: `@iflow-mcp/ai-tools-all-grep_app_mcp`

**4 Tools**:
1. `searchCode` — Primary search
2. `github_file` — Fetch single file from GitHub
3. `github_batch_files` — Parallel multi-file fetch
4. `batch_retrieve_files` — Cached results retrieval

**searchCode parameters**: `query`, `jsonOutput`, `numberedOutput`, `caseSensitive`, `useRegex`, `wholeWords`, `repoFilter`, `pathFilter`, `langFilter`

---

## 3. `searchGitHub` Tool Name — Current Guinevere Usage

The `searchGitHub` name is **used by the Vercel official grep MCP** as its single tool name. The Guinevere `AGENTS.md` references `grep_app_searchGitHub` as a tool name pattern. This is the local `grep_app` tool wrapping grep.app's API.

**Parameter pattern from existing Guinevere usage** (found in librarian agent prompts):
```
grep_app_searchGitHub(query: "usage pattern", language: ["TypeScript"])
grep_app_searchGitHub(query: "function_name", repo: "owner/repo")
grep_app_searchGitHub(query: "(?s)pattern.*across.*lines", useRegexp: true)
grep_app_searchGitHub(query: "CORS(", matchCase: true, language: ["Python"])
```

This aligns with the Vercel Grep MCP tool schema.

---

## 4. httpx Async GitHub API Patterns

### 4.1 Canonical Pattern: Shared AsyncClient with Auth Headers

```python
import httpx

class GitHubClient:
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )
    
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        response = await self.client.request(method, path, **kwargs)
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
        if remaining < 10:
            reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
            wait = max(0, reset_at - time.time())
            await asyncio.sleep(wait + 1)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self.client.aclose()
```

### 4.2 Rate Limit Handling

- **Header fields**: `X-RateLimit-Remaining`, `X-RateLimit-Reset` (epoch seconds), `X-RateLimit-Limit`
- **Authenticated**: 5,000 req/hour (PAT)
- **Unauthenticated**: 60 req/hour
- **Search endpoints**: More restrictive (30 req/min for authenticated)
- **Response codes**: 403/429 on exceeded; check `x-ratelimit-remaining` header before it hits 0

### 4.3 Pagination

GitHub uses **Link headers** for pagination, not body fields:
```python
# Link: <https://api.github.com/repos/owner/repo/issues?page=2>; rel="next"
```

Guinevere pattern (from existing code):
```python
async for issue in github.rest.paginate(
    github.rest.issues.async_list_for_repo, owner="owner", repo="repo", state="open"
):
    ...
```

### 4.4 Python SDK Options

| Library | Async | Typed | Auth | Notes |
|---|---|---|---|---|
| **githubkit** | ✅ | ✅ (Pydantic) | PAT/OAuth/GitHub App | Modern, fully typed, pagination built-in |
| **PyGithub** | ❌ | Partial | PAT/OAuth | Sync-only, most popular |
| **httpx raw** | ✅ | ❌ | Manual | Most flexibility, manual pagination |
| **ghnova** | ✅ | ✅ | Token | New, less mature |

---

## 5. Tool Schema Patterns for P6-007 (GitHub MCP)

### 5.1 Common Tools Across All Implementations

**Core Read Tools** (every server has these):
- `list_repos` / `list_repositories` — list repos for user/org
- `get_repo` / `get_repository` — repo metadata
- `get_file_contents` / `read_file` — read file
- `list_issues` — list issues with filters
- `get_issue` — single issue details
- `list_prs` / `list_pull_requests` — list PRs
- `get_pr` / `get_pull_request` — PR details
- `search_code` — code search

**Core Write Tools** (P6-007 focus):
- `create_issue` — create issue
- `create_pr` / `create_pull_request` — create PR
- `create_or_update_file` — write file
- `add_comment` / `create_issue_comment` — add comment
- `merge_pr` / `merge_pull_request` — merge PR

### 5.2 Auth Patterns

**PAT (Personal Access Token)**: Simple, most common for MCP servers
```python
headers = {"Authorization": f"Bearer {token}"}
```

**API Key Header** (for server-to-server): Used by `shreeyanshi25/github-mcp-server`
```python
# auth.py — timing-safe comparison
@server.middleware("http")
async def api_key_middleware(request, call_next):
    api_key = request.headers.get("X-MCP-API-Key")
    if not secrets.compare_digest(api_key, expected_key):
        return JSONResponse(status_code=401, ...)
```

### 5.3 Write-Notify Pattern (P6-007 specific)

For P6-007 "Write-Notify auth", the pattern from existing servers:
1. **Read**: No API key needed for public repos; PAT for private
2. **Write**: PAT with `repo` scope OR API key validated server-side
3. **Notify**: Webhook callback after write operations (audit log)

---

## 6. Tool Schema Patterns for P6-008 (grep_app MCP)

### 6.1 Recommended Tool Design

Based on official Vercel MCP + `galprz/grep-mcp` patterns:

```python
@mcp.tool()
async def searchGitHub(
    query: str,
    language: Optional[list[str]] = None,
    repo: Optional[str] = None,
    path: Optional[str] = None,
    useRegexp: bool = False,
    matchCase: bool = False,
    matchWholeWords: bool = False,
) -> str:
    """
    Find real-world code examples from public GitHub repositories.
    
    Searches for literal code patterns (like grep), not keywords.
    ✅ Good: 'useState(', 'async function', '(?s)pattern.*across'
    ❌ Bad: 'react tutorial', 'best practices'
    """
    params = {"q": query}
    if language: params["f.lang"] = ",".join(language)
    if repo: params["f.repo"] = repo
    if path: params["f.path"] = path
    if useRegexp: params["regexp"] = "true"
    if matchCase: params["case"] = "true"
    if matchWholeWords: params["words"] = "true"
    
    # Call grep.app API
    ...
```

### 6.2 Response Format

```json
{
  "query": "your search query",
  "summary": {
    "total_results": 12345,
    "results_shown": 10,
    "repositories_found": 4,
    "top_languages": [
      {"language": "Python", "count": 8500}
    ]
  },
  "results_by_repository": [
    {
      "repository": "owner/repo",
      "matches_count": 89,
      "files": [
        {
          "file_path": "src/main.py",
          "branch": "main",
          "total_matches": 5,
          "line_numbers": [10, 25, 30],
          "language": "python",
          "code_snippet": "```python\nasync def main():\n    ..."
        }
      ]
    }
  ]
}
```

### 6.3 Read-Auto Pattern (P6-008 specific)

For P6-008 "Read-Auto auth":
- **No auth required**: grep.app API is public (no API key)
- **Auto rate limiting**: Detect 429 responses, implement exponential backoff
- **Auto pagination**: Follow `page` parameter, stop at empty results
- **Auto formatting**: Structured markdown output with syntax highlights

---

## 7. Key Findings Summary

| Finding | Detail |
|---|---|
| **Best GitHub MCP Python reference** | `shreeyanshi25/github-mcp-server` — FastAPI + FastMCP + httpx + auth middleware |
| **Best grep.app MCP Python reference** | `galprz/grep-mcp` — FastMCP + aiohttp, single `grep_query` tool |
| **Official grep.app API** | `GET https://grep.app/api/search?q=...` — public, no auth, 429 rate limiting |
| **Official Grep MCP** | `https://mcp.grep.app` (HTTP streamable, Vercel-hosted) |
| **`searchGitHub` naming** | Used by Vercel's official Grep MCP + Guinevere's existing `grep_app` tool |
| **httpx patterns** | Shared `AsyncClient`, auth headers, `X-RateLimit-*` headers, `asyncio.gather` for concurrency |
| **GitHub auth scopes** | `repo` for all read/write; `read:org` for org repos; `workflow` for Actions |
| **Write tool naming** | `create_issue`, `create_pull_request`, `create_or_update_file`, `merge_pull_request` |

---

## 8. Recommendations for P6-007 + P6-008

### P6-007 (GitHub MCP — Write-Notify Auth)
1. Use `shreeyanshi25/github-mcp-server` as primary reference architecture
2. Reuse Guinevere's existing `httpx.AsyncClient` pattern
3. Implement API key middleware for write operations (`X-MCP-API-Key` header)
4. Tool naming: `list_repos`, `get_file`, `create_issue`, `create_pr`, `add_comment`
5. Scope: Start with repos + issues + PRs; expand to actions/discussions later

### P6-008 (grep_app — Read-Auto Auth)
1. Use `galprz/grep-mcp` or direct `httpx` calls to `grep.app/api/search`
2. Tool name: `searchGitHub` (matches Vercel official naming)
3. Parameters: `query`, `language`, `repo`, `path`, `useRegexp`, `matchCase`, `matchWholeWords`
4. Handle 429 rate limiting with exponential backoff
5. Format results as structured markdown

### Shared Pattern
Both can share a common `httpx.AsyncClient` base with different auth strategies:
- GitHub: Bearer token headers
- grep.app: No auth, but rate-limit-aware