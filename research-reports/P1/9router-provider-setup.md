# 9Router Provider Configuration Research Report

**Date**: 2026-06-01
**Scope**: Provider setup, API key storage, routing rules, DeepSeek & OpenAI compatibility
**Source**: [9Router GitHub (decolua/9router)](https://github.com/decolua/9router) — README, ARCHITECTURE.md, providers.js, pricing.js, model.js

---

## 1. Adding Providers — Dashboard UI

9Router's primary configuration interface is the **dashboard** at `http://localhost:20128/dashboard`.

### OAuth Providers (Subscription-tier)
Dashboard → Providers → Connect [Provider Name] → OAuth login

Works for: Claude Code, OpenAI Codex, Gemini CLI, Antigravity, GitHub Copilot, Qwen, iFlow, Kiro, Cursor

### API Key Providers
Dashboard → Providers → Add API Key → Select provider → Paste API key → Save

Works for 40+ providers including:
- OpenAI
- DeepSeek
- OpenRouter, GLM, Kimi, MiniMax, Anthropic, Gemini, Groq, xAI, Mistral, Perplexity, Together AI, Fireworks, Cerebras, Cohere, NVIDIA, SiliconFlow, etc.

**Model naming convention**: Models use `{prefix}/{model-id}` format (e.g., `openai/gpt-5.5`, `deepseek/deepseek-v4-flash`).

---

## 2. Adding Providers — REST API

Provider management is available via REST endpoints (dashboard uses these):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/providers` | GET | List all provider connections |
| `/api/providers` | POST | Create new API key connection |
| `/api/providers/{id}` | PUT | Update connection (toggle active, models, etc.) |
| `/api/providers/{id}` | DELETE | Remove connection |
| `/api/providers/{id}/test` | POST | Test provider credentials |
| `/api/providers/validate` | POST | Validate API key before saving |

### Example — Create OpenAI API Key connection (via API)
```http
POST /api/providers
Content-Type: application/json

{
  "provider": "openai",
  "authType": "apiKey",
  "name": "My OpenAI Key",
  "apiKey": "sk-...",
  "priority": 1,
  "isActive": true
}
```

### Example — Create DeepSeek API Key connection (via API)
```http
POST /api/providers
Content-Type: application/json

{
  "provider": "deepseek",
  "authType": "apiKey",
  "name": "My DeepSeek Key",
  "apiKey": "sk-...",
  "priority": 2,
  "isActive": true
}
```

Source: [`src/app/api/providers/route.js` — POST handler](https://github.com/decolua/9router/blob/master/src/app/api/providers/route.js) and [`src/app/(dashboard)/dashboard/providers/[id]/AddApiKeyModal.js` — validate + save flow](https://github.com/decolua/9router/blob/master/src/app/(dashboard)/dashboard/providers/%5Bid%5D/AddApiKeyModal.js)

---

## 3. OpenAI Support — Native

OpenAI is **natively supported** as an API Key provider.

```javascript
// open-sse/config/providers.js
openai: {
  baseUrl: "https://api.openai.com/v1/chat/completions",
  format: "openai"
}
```

- **Format**: OpenAI Chat Completions (native — no translation needed)
- **Auth**: Bearer API key (`sk-...`)
- **Model prefix**: `openai/` (or `cx/` for Codex OAuth)
- **Models**: `gpt-5.5`, `gpt-5.4`, `o4-mini`, etc. (auto-discovered via `/v1/models`)

---

## 4. DeepSeek Support — Native

DeepSeek is **natively supported** as an API Key provider.

```javascript
// open-sse/config/providers.js
deepseek: {
  baseUrl: "https://api.deepseek.com/chat/completions",
  format: "openai"
}
```

- **Format**: OpenAI-compatible — DeepSeek's own API uses the OpenAI chat completions format
- **Auth**: Bearer API key (`sk-...`)
- **Alias resolution**: `ds` and `deepseek` both map to the deepseek provider

### DeepSeek V4 Flash Model
Confirmed in pricing data:

```javascript
// open-sse/config/pricing.js
"deepseek-v4-flash": { input: 0.14, output: 0.28, cached: 0.0028, reasoning: 0.28, cache_creation: 0.14 }
```

Model ID to use: `deepseek/deepseek-v4-flash`

Note: In model resolution logic (`open-sse/services/model.js`), models starting with `deepseek-` are initially routed to `"openrouter"` for provider resolution, but this appears to be for the OpenRouter fallback routing — the actual DeepSeek API key provider uses the dedicated deepseek executor.

---

## 5. Routing Rules — Combos (Primary vs Sub-Agent Model Selection)

9Router implements **3-tier fallback routing** through a feature called **Combos**.

### What is a Combo?
A Combo is a **named, ordered sequence of models** that the router tries in order. When the first model fails (rate limit, auth error, etc.), it falls back to the next.

### Managing Combos

**Dashboard**: Dashboard → Combos → Create Combo → Add models in order

**API**:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/combos` | GET | List all combos |
| `/api/combos` | POST | Create combo (`{ name, models: ["model1", "model2", ...] }`) |
| `/api/combos/{id}` | PUT | Update combo |
| `/api/combos/{id}` | DELETE | Delete combo |

Source: [`src/app/api/combos/route.js`](https://github.com/decolua/9router/blob/master/src/app/api/combos/route.js)

### Combo Fallback Flow
```
Incoming model string → Is combo name?
  ├─ Yes → Load combo models sequence → Try model N
  └─ No  → Single model path
         ↓
Try model → Select account credentials → Execute request
  ├─ Success → Return response
  └─ Fail (fallback-eligible) → Mark account cooldown
         ↓
  Another account for same provider? → Retry
         ↓
  Next model in combo? → Try next model
         ↓
  All unavailable → Return error
```

Source: [`docs/ARCHITECTURE.md` — Combo + Account Fallback Flow](https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md)

### Sticky Round-Robin
Settings include `stickyRoundRobinLimit` — controls how many consecutive requests stick to one provider before rotating.

### For Primary vs Sub-Agent (within OpenCode/Hermes):
The routing decision (which model is "primary" vs "sub-agent") is **not a 9Router feature** — it's handled by the client (e.g., OpenCode). 9Router just provides the models. You configure:
- In OpenCode: `model: { primary: "9router/openai/gpt-5.5", subAgent: "9router/deepseek/deepseek-v4-flash" }`
- In 9Router, you just ensure both providers are connected and their models available.

---

## 6. Config File Location

9Router stores state in **SQLite/JSON files**, not a config file like `config.yaml`.

| File | Path (Linux/macOS) | Path (Windows) | Purpose |
|---|---|---|---|
| Main state DB | `~/.9router/db.json` | `%APPDATA%/9router/db.json` | Providers, combos, aliases, keys, settings |
| Usage history | `~/.9router/usage.json` | `%APPDATA%/9router/usage.json` | Request logs & token usage |
| Request log | `~/.9router/log.txt` | `%APPDATA%/9router/log.txt` | Textual status log |

**Data Dir override**: Set `DATA_DIR` env var (e.g., `DATA_DIR=/var/lib/9router`)

Source: [`docs/ARCHITECTURE.md` — Data Model and Storage Map](https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md) and `README.md`

### There is NO config.yaml — configuration is exclusively via:
1. **Dashboard UI** (primary method)
2. **REST API** (`/api/providers`, `/api/combos`, `/api/provider-nodes`, etc.)
3. **Environment variables** for server settings (port, auth, etc.)
4. Provider-specific **node config** via Dashboard → Provider Nodes (for custom OpenAI-compatible endpoints)

---

## 7. API Key Storage

### Storage Format
API keys are stored in **`db.json`** (SQLite via `localDb.js`) as part of the `providerConnections` entity:

```json
{
  "id": "uuid",
  "provider": "openai",       // or "deepseek"
  "authType": "apiKey",
  "name": "My Key",
  "priority": 1,
  "isActive": true,
  "apiKey": "sk-...",         // API key stored in plaintext
  "accessToken": "...",
  "refreshToken": "...",
  "expiresAt": "...",
  "testStatus": "valid",
  "lastError": null,
  "rateLimitedUntil": null,
  "providerSpecificData": {}
}
```

Source: [`docs/ARCHITECTURE.md` — Data Model ERD](https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md)

### Security Notes
- **API keys are NOT encrypted at rest** — they are stored as plaintext in `db.json`
- Protection is only at the **filesystem level** (file permissions)
- The `API_KEY_SECRET` environment variable is used for **generating local API keys** (the keys used by clients to talk to 9Router), not for encrypting provider secrets
- Provider secrets are persisted in `providerConnections` entries and "should be protected at filesystem level" per ARCHITECTURE.md
- **ENV variables** (`JWT_SECRET`, `INITIAL_PASSWORD`, `API_KEY_SECRET`, `MACHINE_ID_SALT`) are used for dashboard auth and API key generation, not for provider key encryption

Source: [`docs/ARCHITECTURE.md` — Security-Sensitive Boundaries](https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md)

---

## 8. Key Findings for P1-007 Configuration

### Summary
| Question | Answer |
|---|---|
| Dashboard UI for providers? | Yes — `http://localhost:20128/dashboard` → Providers |
| API for provider config? | Yes — `POST /api/providers` with `{ provider, apiKey, authType }` |
| OpenAI native support? | ✅ Native — API Key provider `openai`, format `openai` |
| DeepSeek native support? | ✅ Native — API Key provider `deepseek`, format `openai` |
| DeepSeek V4 Flash model ID? | `deepseek/deepseek-v4-flash` (confirmed in pricing.js) |
| GPT-5.5 model ID? | `openai/gpt-5.5` (or `cx/gpt-5.5` if using Codex OAuth) |
| Config file? | ❌ No config.yaml — uses SQLite `~/.9router/db.json` |
| API key storage? | Plaintext in `db.json` — no encryption at rest |
| Routing rules? | Via Combos (Dashboard → Combos or API `/api/combos`) |
| Browser setup needed? | **Recommended** — dashboard is the designed UX. API alternative exists. |

### Recommended Setup Steps for P1-007

1. **Start 9Router**: `9router` → opens dashboard at `http://localhost:20128/dashboard`
2. **Login**: password default `123456` (or `INITIAL_PASSWORD` env)
3. **Connect OpenAI**:
   - Dashboard → Providers → Add API Key → OpenAI
   - Paste OpenAI API key → Save
4. **Connect DeepSeek**:
   - Dashboard → Providers → Add API Key → DeepSeek
   - Paste DeepSeek API key → Save
5. **Verify models available**: `curl http://localhost:20128/v1/models`
6. **Configure routing** (in OpenCode/Hermes, not in 9Router):
   - Primary model: `openai/gpt-5.5`
   - Sub-agent model: `deepseek/deepseek-v4-flash`
7. **OR via API** (headless alternative):
   ```bash
   curl -X POST http://localhost:20128/api/providers \
     -H "Content-Type: application/json" \
     -d '{"provider":"openai","authType":"apiKey","name":"GPT-5.5","apiKey":"sk-...","priority":1,"isActive":true}'
   
   curl -X POST http://localhost:20128/api/providers \
     -H "Content-Type: application/json" \
     -d '{"provider":"deepseek","authType":"apiKey","name":"DeepSeek V4","apiKey":"sk-...","priority":2,"isActive":true}'
   ```

---

## References

- [9Router README](https://github.com/decolua/9router)
- [ARCHITECTURE.md](https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md)
- [providers.js — all 50+ provider configs](https://github.com/decolua/9router/blob/master/open-sse/config/providers.js)
- [pricing.js — model cost definitions](https://github.com/decolua/9router/blob/master/src/shared/constants/pricing.js)
- [model.js — model resolution logic](https://github.com/decolua/9router/blob/master/open-sse/services/model.js)
- [Providers API route](https://github.com/decolua/9router/blob/master/src/app/api/providers/route.js)
- [Combos API route](https://github.com/decolua/9router/blob/master/src/app/api/combos/route.js)