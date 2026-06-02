# 9Router API Endpoints Research

**Date**: 2026-06-01
**Source**: [github.com/decolua/9router](https://github.com/decolua/9router) (master, ~674 commits)
**Default Port**: 20128
**Base URL**: `http://localhost:20128`

---

## 1. OpenAI-Compatible Endpoints (`/v1`)

These are the primary endpoints — 9Router acts as an OpenAI-compatible proxy. Set `OPENAI_BASE_URL=http://localhost:20128/v1` in any OpenAI SDK.

### Chat & Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/chat/completions` | Standard OpenAI Chat Completions (primary) |
| `POST` | `/v1/messages` | Anthropic Messages API format |
| `POST` | `/v1/messages/count_tokens` | Token counting |
| `POST` | `/v1/responses` | OpenAI Responses API (Codex CLI format) |
| `POST` | `/codex/responses` | Codex-specific responses alias |
| `POST` | `/v1/api/chat` | Ollama-style transform path |

**Evidence**: [README API Reference](https://github.com/decolua/9router/blob/master/README.md) (search for "Chat Completions"), [skills/9router-chat/SKILL.md](https://github.com/decolua/9router/blob/master/skills/9router-chat/SKILL.md), [source: src/app/api/v1/](https://github.com/decolua/9router/tree/master/src/app/api/v1/)

### Models Discovery

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/models` | All LLM/chat models + combos (OpenAI format) |
| `GET` | `/v1/models/image` | Image generation models |
| `GET` | `/v1/models/tts` | Text-to-speech models |
| `GET` | `/v1/models/embedding` | Embedding models |
| `GET` | `/v1/models/web` | Web search + fetch models |
| `GET` | `/v1/models/stt` | Speech-to-text models |
| `GET` | `/v1/models/image-to-text` | Vision models |
| `GET` | `/v1/models/info` | Model info details |

**Evidence**: [skills/9router/SKILL.md](https://github.com/decolua/9router/blob/master/skills/9router/SKILL.md), [source: src/app/api/v1/models/](https://github.com/decolua/9router/tree/master/src/app/api/v1/models/)

### Embeddings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/embeddings` | OpenAI-compatible embeddings |

**Evidence**: [source: src/app/api/v1/embeddings/](https://github.com/decolua/9router/tree/master/src/app/api/v1/embeddings/)

### Image Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/images/generations` | Image generation |
| `POST` | `/v1/images/edits` | Image editing |

**Evidence**: [source: src/app/api/v1/images/](https://github.com/decolua/9router/tree/master/src/app/api/v1/images/), [PR #1286](https://github.com/decolua/9router/pull/1286) (xAI images/video endpoints)

### Audio (TTS/STT)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/audio/speech` | Text-to-speech |
| `POST` | `/v1/audio/transcriptions` | Speech-to-text |

**Evidence**: [source: src/app/api/v1/audio/](https://github.com/decolua/9router/tree/master/src/app/api/v1/audio/)

### Web Search & Fetch

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/web/search` | Web search via Tavily/other providers |
| `POST` | `/v1/web/fetch` | URL → clean markdown content |

**Evidence**: [source: src/app/api/v1/web/](https://github.com/decolua/9router/tree/master/src/app/api/v1/web/)

### Videos (xAI Grok)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/videos/generations` | Video generation |
| `POST` | `/v1/videos/edits` | Video editing |
| `POST` | `/v1/videos/extensions` | Video extensions |
| `POST` | `/v1/videos/{id}` | Video by ID |

**Evidence**: [PR #1286](https://github.com/decolua/9router/pull/1286) (xAI provider PR)

---

## 2. Gemini-Compatible Endpoints (`/v1beta`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1beta/models` | Gemini-style model listing |
| `POST` | `/v1beta/models/{path}:generateContent` | Gemini-style content generation |

**Evidence**: [source: src/app/api/v1beta/](https://github.com/decolua/9router/tree/master/src/app/api/v1beta/)

---

## 3. Health Check Endpoint

| Method | Endpoint | Response |
|--------|----------|----------|
| `GET` | `/api/health` | `{"ok": true}` with CORS headers |

```bash
curl http://localhost:20128/api/health
# → {"ok": true}
```

**Evidence**: [source: src/app/api/health/route.js](https://github.com/decolua/9router/blob/master/src/app/api/health/route.js)

```javascript
export async function GET() {
  return NextResponse.json({ ok: true }, { headers: CORS_HEADERS });
}
```

---

## 4. Dashboard

| URL | Description |
|-----|-------------|
| `http://localhost:20128/dashboard` | Web dashboard (React/Next.js) |
| `http://localhost:20128/` | Root; redirects to dashboard |

**Evidence**: [README](https://github.com/decolua/9router/blob/master/README.md)

---

## 5. Management API Routes

These are used by the dashboard itself and are not part of the OpenAI-compatible surface.

| Category | Endpoints |
|----------|-----------|
| **Auth** | `/api/auth/login`, `/api/auth/logout` |
| **Settings** | `/api/settings`, `/api/settings/require-login` |
| **Providers** | `/api/providers`, `/api/providers/[id]`, `/api/providers/[id]/test`, `/api/providers/[id]/models`, `/api/providers/validate` |
| **Provider Nodes** | `/api/provider-nodes*` |
| **Media Providers** | `/api/media-providers/[kind]/[id]` |
| **Keys** | `/api/keys*` |
| **Combos** | `/api/combos*` |
| **Models (management)** | `/api/models/alias` |
| **Pricing** | `/api/pricing` |
| **Usage & Logs** | `/api/usage/history`, `/api/usage/logs`, `/api/usage/request-logs`, `/api/usage/[connectionId]` |
| **OAuth** | `/api/oauth/[provider]/[action]` |
| **Cloud Sync** | `/api/sync/cloud`, `/api/sync/initialize`, `/api/cloud/*` |
| **CLI Tool Settings** | `/api/cli-tools/claude-settings`, `/api/cli-tools/codex-settings`, etc. |
| **Translator** | `/api/translator` |
| **Tunnel** | `/api/tunnel` |
| **Tags** | `/api/tags` |
| **MCP** | `/api/mcp` |
| **Version** | `/api/version` |
| **Init** | `/api/init` |
| **Shutdown** | `/api/shutdown` |
| **Locale** | `/api/locale` |

**Evidence**: [source: src/app/api/ directory listing](https://github.com/decolua/9router/tree/master/src/app/api/)

---

## 6. Configuration File Format

Configuration is via **environment variables** (`.env` file), **not** YAML/JSON.

**File**: `.env` (template: `.env.example`)

**Key variables**:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `JWT_SECRET` | — | **Yes** | JWT signing secret |
| `INITIAL_PASSWORD` | — | **Yes** | First-run admin password |
| `DATA_DIR` | `/var/lib/9router` | **Yes** | Data persistence directory |
| `PORT` | `20128` | No | HTTP listen port |
| `NODE_ENV` | `production` | No | Runtime mode |
| `API_KEY_SECRET` | — | Recommended | Secret for generating endpoint API keys |
| `MACHINE_ID_SALT` | — | Recommended | Salt for machine identity |
| `REQUIRE_API_KEY` | `false` | No | Whether to require `Authorization: Bearer` on API calls |
| `ENABLE_REQUEST_LOGS` | `false` | No | Enable debug request logging |
| `OBSERVABILITY_ENABLED` | `true` | No | Enable observability/metrics |
| `AUTH_COOKIE_SECURE` | `false` | No | Set secure flag on auth cookies |
| `BASE_URL` | `http://localhost:20128` | No | Server-side base URL for internal callback |
| `CLOUD_URL` | `https://9router.com` | No | Cloud sync endpoint base |
| `HTTP_PROXY` | — | No | Outbound HTTP proxy for upstream provider calls |

**Evidence**: [.env.example](https://github.com/decolua/9router/blob/master/.env.example)

---

## 7. API Key & Authentication

### Default: No auth required
By default (`REQUIRE_API_KEY=false`), the `/v1/*` endpoints accept requests **without** any API key — just point your tool to `http://localhost:20128/v1` and it works.

### With auth enabled
When `REQUIRE_API_KEY=true`:

```bash
# In .env
REQUIRE_API_KEY=true
API_KEY_SECRET=your-secret-here
```

Generate keys from **Dashboard → Keys**, then use:

```bash
curl http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer sk-9router-xxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-5","messages":[{"role":"user","content":"Hi"}]}'
```

**Evidence**: [.env.example](https://github.com/decolua/9router/blob/master/.env.example), [skills/9router/SKILL.md](https://github.com/decolua/9router/blob/master/skills/9router/SKILL.md)

---

## 8. Provider Model Prefix Format

9Router uses provider-prefixed model names: `{provider_alias}/{model_name}`

| Prefix | Provider | Auth Type | Wire Format |
|--------|----------|-----------|-------------|
| `cc/` | Claude (Anthropic) | OAuth | Claude |
| `cx/` | Codex (OpenAI) | OAuth | Responses API |
| `ag/` | Antigravity (Google) | OAuth | Antigravity |
| `gh/` | GitHub Copilot | OAuth | OpenAI |
| `kr/` | Kiro (AWS) | OAuth | Kiro |
| `if/` | iFlow | OAuth | OpenAI |
| `qw/` | Qwen | OAuth | OpenAI |
| `gc/` | Gemini CLI | OAuth | Gemini CLI |
| `openai/` | OpenAI | API Key | OpenAI |
| `anthropic/` | Anthropic | API Key | Claude |
| `gemini/` | Gemini | API Key | Gemini |
| `openrouter/` | OpenRouter | API Key | OpenAI |

Custom combo names (created in Dashboard → Combos) appear directly as model IDs without a prefix.

**Evidence**: [README](https://github.com/decolua/9router/blob/master/README.md), [fork docs](https://github.com/xuan2261/9router)

---

## 9. Verification Cheat Sheet

```bash
# Health check
curl http://localhost:20128/api/health

# List models
curl http://localhost:20128/v1/models

# List image models
curl http://localhost:20128/v1/models/image

# Chat completion (non-streaming)
curl http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-5","messages":[{"role":"user","content":"Hello"}],"stream":false}'

# Anthropic format
curl http://localhost:20128/v1/messages \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"cc/claude-opus-4-7","max_tokens":1024,"messages":[{"role":"user","content":"Hi"}]}'

# Embeddings
curl http://localhost:20128/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/text-embedding-3-small","input":"Hello world"}'
```

---

## Sources

| Source | URL |
|--------|-----|
| GitHub repo | https://github.com/decolua/9router |
| README | https://github.com/decolua/9router/blob/master/README.md |
| 9Router skill doc | https://github.com/decolua/9router/blob/master/skills/9router/SKILL.md |
| Chat skill doc | https://github.com/decolua/9router/blob/master/skills/9router-chat/SKILL.md |
| .env.example | https://github.com/decolua/9router/blob/master/.env.example |
| API routes (source) | https://github.com/decolua/9router/tree/master/src/app/api |
| v1 routes (source) | https://github.com/decolua/9router/tree/master/src/app/api/v1 |
| Health route (source) | https://github.com/decolua/9router/blob/master/src/app/api/health/route.js |
| xAI PR (videos/images) | https://github.com/decolua/9router/pull/1286 |