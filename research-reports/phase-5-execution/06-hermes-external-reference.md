# Hermes Agent External Reference — Phase 5

> **Goal:** Validate conventions for installing 5 Guinevere skills, creating/registering `PersonaPlugin`, and configuring Hermes cron.
> **Source:** [Hermes Agent Official Docs](https://hermes-agent.nousresearch.com/docs/) + [GitHub: NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (main branch, v2026.4.13).
> **Date researched:** 2026-06-06
> **Confidence:** High for documented APIs, Medium for internal cron/SQLite details (cross-referenced docs + source).

---

## 1. Skill Directory Structure

### Primary path: `~/.hermes/skills/`

All skills live in `~/.hermes/skills/` — the single source of truth. Hermes copies bundled skills here on install; hub-installed and agent-created skills also go here.

```
~/.hermes/skills/
├── <category>/
│   ├── <skill-name>/
│   │   ├── SKILL.md          # Required: main instructions (frontmatter + body)
│   │   ├── references/       # Optional: additional docs
│   │   ├── templates/        # Optional: output format templates
│   │   ├── scripts/          # Optional: helper scripts
│   │   └── assets/           # Optional: supplementary files
│   └── ...
├── .hub/                     # Skills Hub state
│   ├── lock.json
│   ├── quarantine/
│   └── audit.log
└── .bundled_manifest         # Tracks seeded bundled skills
```

**Source:** https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

### SKILL.md Format (Frontmatter)

```yaml
---
name: my-skill
description: Brief description of what this skill does
version: 1.0.0
metadata:
  hermes:
    tags: [my-tag, automation]
    category: my-category
---
# My Skill
## When to Use
...
## Procedure
...
## Pitfalls
...
## Verification Checklist
...
```

**Frontmatter rules:**
- `name` ≤ 64 chars, lowercase + hyphens
- `description` ≤ 1024 chars, should start with "Use when ..."
- Total file ≤ 100,000 chars (aim 8-15k)
- Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`

**Source:** https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills

### In-repo alternative (for bundled/official skills)

Bundled skills live in the repo under `skills/<category>/<skill-name>/SKILL.md`. This is for skills shipped with the Hermes package. For Phase 5, we use the `~/.hermes/skills/` path since we are installing user skills, not modifying the Hermes repo.

### Plugin-provided skills (namespaced)

Plugins can bundle skills that are loaded via `skill_view("plugin:skill")`:

```
~/.hermes/plugins/my-plugin/
├── __init__.py
├── plugin.yaml
└── skills/
    ├── my-workflow/
    │   └── SKILL.md
    └── my-checklist/
        └── SKILL.md
```

Registered in `register(ctx)`:

```python
from pathlib import Path
def register(ctx):
    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)
```

Loaded with namespace: `skill_view("my-plugin:my-workflow")`. Plugin skills are read-only, opt-in, and don't collide with built-in names.

---

## 2. CLI Commands — `hermes skills`

| Command | Purpose |
|---------|---------|
| `hermes skills list` | List installed skills |
| `hermes skills search <query>` | Search skills hub |
| `hermes skills inspect <id>` | Preview before installing |
| `hermes skills install <id>` | Install skill (hub ID or direct `https://…/SKILL.md` URL) |
| `hermes skills install <url> --name my-skill` | Override name when frontmatter has none |
| `hermes skills browse` | Browse all hub skills |
| `hermes skills browse --source official` | Browse only official optional skills |
| `hermes skills check` | Validate installed skills |
| `hermes skills update` | Sync bundled skills |
| `hermes skills publish <path>` | Publish to registry |
| `hermes skills tap add <repo>` | Add GitHub repo as skill source |
| `hermes skills reset <name>` | Reset skill to bundled version |
| `hermes skills config` | Configure skill settings |
| `hermes skills opt-in <name>` | Opt in to skill updates |

**Slash commands (in-session):**
- `/skills` — search/install
- `/skill <name>` — load a skill into session
- `/reload-skills` — re-scan `~/.hermes/skills/`

**Source:** https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md

---

## 3. Plugin Registration Conventions

### Directory layout

```
~/.hermes/plugins/<plugin-name>/
├── plugin.yaml          # Required: manifest
├── __init__.py          # Required: register(ctx) function
├── schemas.py           # Optional: tool schemas (what LLM reads)
├── tools.py             # Optional: tool handlers (what runs)
└── skills/              # Optional: bundled skills
    └── <skill-name>/
        └── SKILL.md
```

### plugin.yaml

```yaml
name: calculator
version: 1.0.0
description: Math calculator — evaluate expressions and convert units
provides_tools:
  - calculate
  - unit_convert
provides_hooks:
  - post_tool_call
# Optional:
author: Your Name
requires_env:
  - SOME_API_KEY       # Simple format
  - name: OTHER_KEY    # Rich format
    description: "Key for the Other service"
    url: "https://other.com/keys"
    secret: true
```

### `register(ctx)` API

| Method | Purpose |
|--------|---------|
| `ctx.register_tool(name, toolset, schema, handler, ...)` | Add tool the LLM can call |
| `ctx.register_hook(event, callback)` | Subscribe to lifecycle events |
| `ctx.register_command(name, handler, description)` | Register `/name` slash command |
| `ctx.register_cli_command(name, help, setup_fn, handler_fn)` | Register `hermes <name>` subcommand |
| `ctx.register_skill(name, skill_md_path)` | Register bundled skill |
| `ctx.register_platform(name, label, adapter_factory, ...)` | Register gateway adapter |
| `ctx.register_memory_provider(cls)` | Register memory backend |
| `ctx.register_context_engine(engine)` | Register context compressor |
| `ctx.register_image_gen_provider(cls)` | Register image gen backend |
| `ctx.dispatch_tool(name, args)` | Call a tool programmatically |
| `ctx.inject_message(content, role)` | Inject message into active session |
| `ctx.llm.complete(messages, ...)` | Make LLM call from plugin |

### Lazy-install optional deps

```python
from tools.lazy_deps import ensure, FeatureUnavailable
def my_handler(args, **kwargs):
    try:
        ensure("my-plugin.my-backend")
    except FeatureUnavailable as exc:
        return {"error": str(exc)}
    import my_backend_sdk
    ...
```

### Built-in tool override

```python
ctx.register_tool(
    name="browser_navigate",
    toolset="plugin_my_browser",
    schema={...},
    handler=my_custom_navigate,
    override=True,
)
```

**Source:** https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin

---

## 4. Pre-LLM Middleware / Plugin Hooks

### Available lifecycle hooks

| Hook | Fires when | Effect / Returns |
|------|-----------|------------------|
| `pre_tool_call` | Before any tool executes | `{"action": "block", "message": str}` to veto |
| `post_tool_call` | After any tool returns | ignored (observer) |
| `transform_terminal_output` | Before terminal output returned | Transform string |
| `transform_tool_result` | Before tool result to LLM | Transform string |
| `transform_llm_output` | Before LLM output to user | Replace response text |
| `pre_llm_call` | Once per turn, before LLM loop | `{"context": "..."}` to inject context |
| `post_llm_call` | Once per turn, after LLM loop (success) | ignored |
| `pre_api_request` | Before API call | ignored |
| `post_api_request` | After API call | ignored |
| `on_session_start` | New session created (first turn only) | ignored |
| `on_session_end` | End of every `run_conversation` call | ignored |
| `on_session_finalize` | CLI/gateway tears down active session | ignored |
| `on_session_reset` | Gateway swaps in new session key | ignored |
| `subagent_stop` | Once per child after `delegate_task` finishes | ignored |
| `pre_gateway_dispatch` | Gateway received message, before auth+dispatch | `{"action": "skip"|"rewrite"|"allow"}` |
| `pre_approval_request` | Before dangerous command approval prompt | Observer only |
| `post_approval_response` | After approval response | Observer only |

**`VALID_HOOKS` from source** (`hermes_cli/plugins.py`):
```python
VALID_HOOKS: Set[str] = {
    "pre_tool_call",
    "post_tool_call",
    "transform_terminal_output",
    "transform_tool_result",
    "transform_llm_output",
    "pre_llm_call",
    "post_llm_call",
    "pre_api_request",
    "post_api_request",
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
    "subagent_stop",
    "pre_gateway_dispatch",
    "pre_approval_request",
    "post_approval_response",
}
```

### Registration pattern

```python
def register(ctx):
    ctx.register_hook("pre_tool_call", before_any_tool)
    ctx.register_hook("post_tool_call", after_any_tool)
    ctx.register_hook("pre_llm_call", inject_memory)
    ctx.register_hook("on_session_start", on_new_session)
    ctx.register_hook("on_session_end", on_session_end)
```

### `pre_llm_call` context injection

Only hook that can inject data into the LLM call:

```python
def recall_context(session_id, user_message, is_first_turn, **kwargs):
    try:
        resp = httpx.post(f"{MEMORY_API}/recall", json={
            "session_id": session_id,
            "query": user_message,
        }, timeout=3)
        memories = resp.json().get("results", [])
        if not memories:
            return None
        text = "Recalled context from previous sessions:\n"
        text += "\n".join(f"- {m['text']}" for m in memories)
        return {"context": text}
    except Exception:
        return None  # fail silently
```

**Key behavior:**
- Callbacks receive keyword arguments; always accept `**kwargs`
- If a callback crashes, it's logged and skipped — other hooks continue
- Multiple `pre_llm_call` returns are joined with double newlines
- Context is appended to the user message, NOT the system prompt (preserves prompt cache)

### Shell hooks (config-driven, no Python)

```yaml
hooks:
  post_tool_call:
    - matcher: ".*"
      command: "notify-send 'Tool ran: {tool_name}'"
      timeout: 30
```

**Source:** https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks

---

## 5. Cron Job Configuration

### CLI commands

| Command | Purpose |
|---------|---------|
| `hermes cron list --all` | List jobs (--all for disabled) |
| `hermes cron create <schedule>` | Create: `30m`, `every 2h`, `0 9 * * *` |
| `hermes cron edit <id>` | Edit schedule/prompt/delivery |
| `hermes cron pause/resume <id>` | Control job state |
| `hermes cron run <id>` | Trigger on next tick |
| `hermes cron remove <id>` | Delete job |
| `hermes cron status` | Scheduler status |

### Slash command: `/cron`

### cronjob tool (in-session, natural language)

The `cronjob` tool uses action-style operations: create, list, edit, pause, resume, trigger, remove jobs — all via a single tool the LLM calls.

### Cron job features

| Feature | Description |
|---------|-------------|
| Schedule formats | Relative (`30m`), interval (`every 2h`), cron (`0 9 * * *`), ISO timestamp |
| Skills attachment | Attach zero, one, or multiple skills to a job |
| Model/provider override | Per-job model/provider selection |
| `no_agent=True` mode | Script-only — stdout delivered verbatim, no LLM cost |
| `context_from` | Chain job A's output into job B |
| `workdir` | Run in specific dir with `AGENTS.md` loaded |
| Multi-platform delivery | Deliver to Telegram, Discord, Slack, local files, etc. |
| `conversational: true` | Injects output as synthetic user message (agent responds) |

### Cron execution details

- Runs in fresh agent sessions — no memory of previous runs
- Prompts must be self-contained
- Default: runs detached from any repo (no AGENTS.md loaded)
- Gateway ticks scheduler every 60 seconds
- Cron agent uses `cron` platform toolset (not CLI default)
- Results stored in `~/.hermes/cron/` and `~/.hermes/sessions/`

### Important constraints for Phase 5

> **Key constraint:** Cron jobs run in fresh agent sessions with no memory of your current chat. Prompts must be completely self-contained — include everything the agent needs to know.

> Natural language like "daily at 9am" is NOT supported — use `0 9 * * *` instead.

**Source:** https://hermes-agent.nousresearch.com/docs/user-guide/features/cron

---

## 6. Redis Config Patterns

### Environment variables

```bash
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=                # leave blank if no Redis auth
MEMORY_BACKEND=redis
EPISODIC_LOG_BACKEND=sqlite
SQLITE_PATH=~/.hermes/episodes.db
```

### Recommended Redis production config

```bash
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG SET appendfsync everysec
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG REWRITE
```

### Hermes-specific tuning

```bash
redis-cli CONFIG SET hz 20                    # Higher event loop frequency
redis-cli CONFIG SET activerehashing yes      # Reduce memory fragmentation
redis-cli CONFIG SET lazyfree-lazy-eviction yes  # Non-blocking eviction
```

### Redis key patterns (from community guides)

| Key pattern | Purpose | TTL |
|-------------|---------|-----|
| `hermes:msg:{session_id}` | Session message list | 86400s |
| `hermes:tool:{tool_call_id}` | Tool result cache | 3600s |
| `hermes:lock:{session_id}` | Distributed session lock | 30s |
| `vec:{hash}` | Vector/semantic cache | Configurable |

**Sources:**
- https://www.tencentcloud.com/techpedia/144037
- https://tools.yiteai.com/en/books/hermes-guide/ch49

---

## 7. Graceful Degradation Patterns

### 7.1 Provider fallback

Hermes automatically falls back when the main LLM provider fails with:
- Rate limits (HTTP 429) — after exhausting retries
- Server errors (HTTP 500, 502, 503) — after retries
- Auth failures (HTTP 401, 403) — immediately
- Not found (HTTP 404) — immediately
- Invalid/empty responses — after 3 retries

**Fallback is turn-scoped** — each new user message starts with the primary model restored.

### 7.2 Auxiliary provider failover

Layered chain for compression/session-search/memory tasks:
1. Primary aux provider (configured)
2. `auxiliary.<task>.fallback_chain` (per-task override list)
3. Main agent provider + model (safety net)
4. Warn + re-raise if all layers fail

### 7.3 Empty response handling

After 3 empty-content retries:
- Falls back to provider chain
- If fallback also empty → returns `(empty)` gracefully
- After tool calls with pending work → injects nudge and retries

### 7.4 Gateway platform circuit breaker

- 10 consecutive failures → platform paused (circuit breaker)
- Paused platforms visible via `/platform list`
- `/platform pause <name>` / `/platform resume <name>`
- Gateway stays alive when a single adapter fails (no infinite restart loop)

### 7.5 Plugin crash isolation

- If `register()` crashes → plugin is disabled, Hermes continues fine
- If hook callback crashes → logged and skipped, other hooks continue
- All three hook systems (plugin, gateway, shell) are non-blocking — errors never crash the agent

### 7.6 JSONDecodeError handling (fixed in v2026.4)

`json.JSONDecodeError` excluded from local-validation fast-fail so it can use normal retry/fallback flow.

### 7.7 Safety block detection

Provider safety/moderation blocks detected and classified as `provider_safety_block`; cron jobs with failed safety checks marked as `last_status: failed` or `degraded`.

### 7.8 Best practices for graceful degradation

- Keep at least one backup provider for rate limits/outages
- Pin auxiliary routes away from exhausted providers
- Use `no_agent=True` for watchdog/alert cron jobs (no LLM dependency)
- Test fallback behavior before scheduling critical jobs
- Use `fallback_on_empty: "continue"` for multi-step tasks (config option)

**Sources:**
- https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers
- https://hermes-agent.ai/blog/hermes-agent-provider-fallbacks

---

## 8. Directory Structure Summary (Single Source of Truth)

```
~/.hermes/
├── config.yaml                    # Primary config (model, toolsets, hooks, etc.)
├── .env                           # Secrets (API keys, tokens)
├── SOUL.md                        # Agent personality/identity
├── skills/                        # Read-write skill tree (source of truth)
│   ├── <category>/
│   │   └── <name>/
│   │       └── SKILL.md
│   ├── .hub/                      # Skills Hub state
│   └── .bundled_manifest
├── plugins/                       # User plugins
│   └── <plugin-name>/
│       ├── plugin.yaml
│       ├── __init__.py
│       └── skills/                # Plugin-bundled skills (optional)
├── hooks/                         # Gateway event hooks (optional)
│   └── <hook-name>/
│       ├── HOOK.yaml
│       └── handler.py
├── memories/                      # Persistent memory (MEMORY.md, USER.md)
├── cron/                          # Scheduled job definitions
├── sessions/                      # Gateway session data
└── logs/                          # Agent logs
```

---

## 9. Phase 5 Relevance Map

| Phase 5 Task | Hermes Convention | Doc Section |
|-------------|-------------------|-------------|
| Install 5 Guinevere skills | Drop SKILL.md dirs into `~/.hermes/skills/<category>/<name>/` | §1 |
| Skill SKILL.md format | Frontmatter with name, description, version, metadata.hermes | §1 |
| PersonaPlugin creation | `~/.hermes/plugins/persona/` with plugin.yaml + __init__.py | §3 |
| Plugin tool registration | `ctx.register_tool(name, toolset, schema, handler)` | §3 |
| Plugin hook registration | `ctx.register_hook("pre_llm_call", callback)` for context injection | §4 |
| PersonaGuard via pre_llm_call | Return `{"context": "persona rules..."}` from hook | §4 |
| Cron job setup | `hermes cron create "0 9 * * *" "prompt..."` | §5 |
| Cron self-contained prompts | Include all context, model override if needed | §5 |
| Redis memory backend | `REDIS_URL=redis://localhost:6379` in .env | §6 |
| Graceful degradation | Plugin crash isolation, fallback providers, circuit breaker | §7 |

---

## 10. Confidence & Caveats

| Topic | Confidence | Caveat |
|-------|-----------|--------|
| Skill directory structure & SKILL.md | **High** | Officially documented with examples |
| Plugin registration | **High** | Complete guide with source code references |
| Hook lifecycle & signatures | **High** | Docs + source (`VALID_HOOKS`, `plugins.py`) |
| Cron CLI & tool | **High** | Officially documented with CLI ref |
| Cron internal scheduler | **Medium** | We have doc summaries; exact tick interval (60s) from docs |
| Redis env vars | **High** | Documented in deployment guides |
| Redis key patterns | **Medium** | Community/production guides, not official spec |
| Graceful degradation | **High** | Documented fallback and circuit breaker features |
| Internal cron SQLite schema | **Low** | Not documented; would require source code reading |
| Plugin LLM access (`ctx.llm`) | **High** | Documented developer guide |

### Key caveats for Phase 5:

1. **Skill auto-discovery**: Simply dropping SKILL.md directories into `~/.hermes/skills/` makes them live — no registration needed. This is the simplest path, but skills must have valid frontmatter.

2. **Plugin skills vs directory skills**: Plugin skills (via `ctx.register_skill()`) are namespaced and read-only. Directory skills (under `~/.hermes/skills/`) are editable by the agent. Choose based on whether the agent should be able to modify them.

3. **Cron prompt must be self-contained**: Cron jobs have no memory of previous runs. Include repo names, format preferences, delivery instructions directly in the prompt.

4. **Plugin crash safety**: If `register()` or any hook callback crashes, the plugin is disabled but Hermes continues. This means the PersonaPlugin must not crash during startup or the guardrails won't load.

5. **pre_llm_call context injection**: This is the correct hook for PersonaGuard — it injects context into every LLM turn. Multiple plugins can inject context simultaneously.

6. **No built-in "persona plugin" in Hermes**: There is no standard persona plugin pattern in Hermes. Phase 5 must create a custom plugin. The SOUL.md system provides global personality but no runtime hooks — our plugin fills that gap.

7. **Always accept `**kwargs`**: All hook callbacks and tool handlers must accept `**kwargs` for forward compatibility.

---

*End of Report. ADR/local plan remain binding if conflict with this reference.*
