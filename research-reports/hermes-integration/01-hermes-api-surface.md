# Hermes Agent API Surface Research

Source scope:
- Official docs: https://hermes-agent.nousresearch.com/docs/
- Python guide: https://hermes-agent.nousresearch.com/docs/guides/python-library
- Sessions doc: https://hermes-agent.nousresearch.com/docs/user-guide/sessions
- MCP doc: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- MCP guide: https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes
- Discord doc: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord
- PyPI: https://pypi.org/project/hermes-agent/
- Web search results: Hermes Agent Discord integration, Hermes Agent session management

## 1) Hermes Python API surface from the official docs

### Primary import / entry point
The Python guide says Hermes can be used programmatically by importing `AIAgent` from `run_agent`.

```python
from run_agent import AIAgent
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Programmatic agent creation
The guide shows the minimal constructor pattern:

```python
from run_agent import AIAgent

agent = AIAgent(
    model="anthropic/claude-sonnet-4.6",
    quiet_mode=True,
)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Exposed methods explicitly documented
The guide explicitly documents these instance methods:

- `chat(message)`
- `run_conversation(user_message=..., task_id=..., system_message=..., conversation_history=...)`

#### `chat()`
The guide says `chat()` “handles the full conversation loop internally — tool calls, retries, everything — and returns just the final text response.”

```python
response = agent.chat("What is the capital of France?")
print(response)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

#### `run_conversation()`
The guide says `run_conversation()` returns a dictionary with `final_response` and `messages`.

```python
result = agent.run_conversation(
    user_message="Search for recent Python 3.13 features",
    task_id="my-task-1",
)
print(result["final_response"])
print(f"Messages exchanged: {len(result['messages'])}")
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

The guide also shows `system_message` support:

```python
result = agent.run_conversation(
    user_message="Explain quicksort",
    system_message="You are a computer science tutor. Use simple analogies.",
)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Key constructor parameters documented in the Python guide
The guide provides a parameter table for `AIAgent(...)`.

```text
model
quiet_mode
enabled_toolsets
disabled_toolsets
save_trajectories
ephemeral_system_prompt
max_iterations
skip_context_files
skip_memory
api_key
base_url
platform
```

Exact descriptions from the doc:

- `model`: Model in OpenRouter format (defaults to empty; resolved from your hermes config at runtime)
- `quiet_mode`: Suppress CLI output
- `enabled_toolsets`: Whitelist specific toolsets
- `disabled_toolsets`: Blacklist specific toolsets
- `save_trajectories`: Save conversations to JSONL
- `ephemeral_system_prompt`: Custom system prompt (not saved to trajectories)
- `max_iterations`: Max tool-calling iterations per conversation, default `90`
- `skip_context_files`: Skip loading AGENTS.md files
- `skip_memory`: Disable persistent memory read/write
- `api_key`: API key, falls back to env vars
- `base_url`: Custom API endpoint URL
- `platform`: Platform hint such as `"discord"` or `"telegram"`

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Important runtime behavior explicitly documented for Python use
- Always set `quiet_mode=True` when embedding Hermes in your own code.
- Create a new `AIAgent` instance per thread or task.
- The agent automatically cleans up resources when a conversation ends.

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

---

## 2) How to create an agent programmatically in Python

### Minimal creation
```python
from run_agent import AIAgent

agent = AIAgent(
    model="anthropic/claude-sonnet-4.6",
    quiet_mode=True,
)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Stateless API-style creation
```python
agent = AIAgent(
    model=request.model,
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
)
response = agent.chat(request.message)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Locked-down tool surface creation
```python
agent = AIAgent(
    model="anthropic/claude-sonnet-4.6",
    enabled_toolsets=["web"],
    quiet_mode=True,
)
```

Or:

```python
agent = AIAgent(
    model="anthropic/claude-sonnet-4.6",
    disabled_toolsets=["terminal"],
    quiet_mode=True,
)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

---

## 3) Session management API

### Session persistence model
The Sessions page says every conversation is stored as a session.

Storage:
- SQLite database: `~/.hermes/state.db`
- `sessions.json` routing index: `~/.hermes/sessions/sessions.json`

The SQLite database stores:
- session ID
- source platform
- user ID
- session title
- model name and configuration
- system prompt snapshot
- full message history (role, content, tool calls, tool results)
- token counts
- timestamps
- parent session ID

Source: https://hermes-agent.nousresearch.com/docs/user-guide/sessions

### CLI session management commands documented
The Sessions page documents these commands:

```bash
hermes --continue
hermes -c
hermes chat --continue
hermes chat -c
hermes -c "my project"
hermes --resume 20250305_091523_a1b2c3d4
hermes -r 20250305_091523_a1b2c3d4
hermes sessions list
hermes sessions export backup.jsonl
hermes sessions delete <session_id>
hermes sessions rename <session_id> "debugging auth flow"
hermes sessions prune
hermes sessions stats
```

Source: https://hermes-agent.nousresearch.com/docs/user-guide/sessions

### Session search tool
The doc says Hermes has a built-in `session_search` tool. It supports three calling shapes:

1. Discovery:
```python
session_search(query="auth refactor", limit=3)
```

2. Scroll:
```python
session_search(session_id="20260510_174648_805cc2", around_message_id=590803, window=10)
```

3. Browse:
```python
session_search()
```

The doc also states the discovery result includes:
- `session_id`
- `title`
- `when`
- `source`
- `snippet`
- `bookend_start`
- `messages`
- `bookend_end`
- `match_message_id`
- `messages_before`
- `messages_after`

Source: https://hermes-agent.nousresearch.com/docs/user-guide/sessions

### Session reset and cleanup behavior
The sessions page says gateway sessions can auto-reset on policies:
- idle
- daily
- both
- none

It also says before a reset the agent is given a turn to save memories and skills.

Source: https://hermes-agent.nousresearch.com/docs/user-guide/sessions

### Python-side session history use
The Python guide demonstrates passing `conversation_history=history` into `run_conversation()`.

```python
result1 = agent.run_conversation("My name is Alice")
history = result1["messages"]

result2 = agent.run_conversation(
    "What's my name?",
    conversation_history=history,
)
print(result2["final_response"])
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

---

## 4) Conversation history API

### Exact documented history return value
`run_conversation()` returns:
- `final_response`
- `messages`

The guide says `messages` is the complete message history, including:
- system
- user
- assistant
- tool calls
- tool results

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Conversation history reuse
The guide explicitly says the `conversation_history` parameter accepts the `messages` list from a previous result, and the agent copies it internally so the original list is never mutated.

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

### Example code
```python
result1 = agent.run_conversation("My name is Alice")
history = result1["messages"]
result2 = agent.run_conversation(
    "What's my name?",
    conversation_history=history,
)
```

Source: https://hermes-agent.nousresearch.com/docs/guides/python-library

---

## 5) MCP tool calling API

### MCP as Hermes integration
The MCP feature page says Hermes can connect to external tool servers and automatically discover/register tools at startup.

Key MCP config keys documented:
- `command`
- `args`
- `env`
- `url`
- `headers`
- `timeout`
- `connect_timeout`
- `enabled`
- `supports_parallel_tool_calls`
- `tools`

Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### MCP tool naming pattern
Hermes prefixes MCP tools as:

```text
mcp_<server_name>_<tool_name>
```

Examples from the doc:
- `mcp_filesystem_read_file`
- `mcp_github_create_issue`
- `mcp_my_api_query_data`

Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### MCP utility wrappers
Hermes can also register utility tools when supported:
- `list_resources`
- `read_resource`
- `list_prompts`
- `get_prompt`

With the same prefix pattern, e.g. `mcp_github_list_resources`.

Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### Per-server filtering API
The docs show `tools.include`, `tools.exclude`, `tools.prompts`, and `tools.resources`.

Example:
```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    tools:
      include: [list_issues, create_issue, search_code]
      prompts: false
      resources: false
```

Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### Parallel MCP tool calls
The docs say `supports_parallel_tool_calls: true` opts into concurrent execution of safe MCP tools from that server.

Example:
```yaml
mcp_servers:
  docs:
    command: "docs-server"
    supports_parallel_tool_calls: true
```

Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### Hermes as an MCP server
The docs also state Hermes can itself act as an MCP server:

```bash
hermes mcp serve
```

Available tools in that MCP server:
- `conversations_list`
- `conversation_get`
- `messages_read`
- `attachments_fetch`
- `events_poll`
- `events_wait`
- `messages_send`
- `channels_list`
- `permissions_list_open`
- `permissions_respond`

Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

### MCP guide examples
The MCP guide gives the canonical config examples:

```yaml
mcp_servers:
  project_fs:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/my-project"]
```

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    tools:
      include: [list_issues, create_issue, search_code]
      prompts: false
      resources: false
```

Source: https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes

---

## 6) Discord gateway integration

### What Discord integration does
The Discord setup page says Hermes integrates with Discord as a bot and supports:
- direct messages
- server channels
- text
- voice messages
- file attachments
- slash commands

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Discord session behavior
The Discord page says:
- DMs respond to every message and each DM has its own session.
- Server channels require `@mention` by default.
- Free-response channels can be configured.
- Threads keep responding in the same thread.
- Shared channels default to per-user isolated sessions.

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Discord gateway flow
The doc says each incoming Discord message goes through:
1. authorization (`DISCORD_ALLOWED_USERS`)
2. mention / free-response checks
3. session lookup
4. session transcript loading
5. normal Hermes agent execution, including tools, memory, and slash commands
6. response delivery back to Discord

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Discord config variables documented
The page documents these env vars:
- `DISCORD_BOT_TOKEN`
- `DISCORD_ALLOWED_USERS`
- `DISCORD_ALLOWED_ROLES`
- `DISCORD_HOME_CHANNEL`
- `DISCORD_HOME_CHANNEL_NAME`
- `DISCORD_COMMAND_SYNC_POLICY`
- `DISCORD_REQUIRE_MENTION`
- `DISCORD_THREAD_REQUIRE_MENTION`
- `DISCORD_FREE_RESPONSE_CHANNELS`
- `DISCORD_IGNORE_NO_MENTION`
- `DISCORD_AUTO_THREAD`
- `DISCORD_ALLOW_BOTS`
- `DISCORD_REACTIONS`
- `DISCORD_IGNORED_CHANNELS`
- `DISCORD_ALLOWED_CHANNELS`
- `DISCORD_NO_THREAD_CHANNELS`
- `DISCORD_HISTORY_BACKFILL`
- `DISCORD_HISTORY_BACKFILL_LIMIT`
- `DISCORD_REPLY_TO_MODE`
- `DISCORD_ALLOW_MENTION_EVERYONE`
- `DISCORD_ALLOW_MENTION_ROLES`
- `DISCORD_ALLOW_MENTION_USERS`
- `DISCORD_ALLOW_MENTION_REPLIED_USER`
- `DISCORD_PROXY`
- `DISCORD_ALLOW_ANY_ATTACHMENT`
- `DISCORD_MAX_ATTACHMENT_BYTES`
- `HERMES_DISCORD_TEXT_BATCH_DELAY_SECONDS`
- `HERMES_DISCORD_TEXT_BATCH_SPLIT_DELAY_SECONDS`

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Discord config YAML keys documented
The page also documents the `discord:` config section, including:
- `require_mention`
- `thread_require_mention`
- `free_response_channels`
- `auto_thread`
- `reactions`
- `ignored_channels`
- `no_thread_channels`
- `history_backfill`
- `history_backfill_limit`
- `channel_prompts`
- `allow_mentions`

Plus the global gateway key:
- `group_sessions_per_user`

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Discord permissions and setup details
The guide says the bot needs at minimum:
- View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History

Recommended additional permissions:
- Send Messages in Threads
- Add Reactions

It also gives the invite URL pattern:

```text
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
```

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Discord example config
```bash
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_ALLOWED_USERS=284102345871466496
```

```bash
hermes gateway
```

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

---

## 7) PyPI facts

### Latest version
PyPI lists the current release as:
- `hermes-agent 0.15.2`
- released `May 29, 2026`

Source: https://pypi.org/project/hermes-agent/

### Package description
PyPI summary:
- “The self-improving AI agent — creates skills from experience, improves them during use, and runs anywhere”

PyPI long description starts with:
- “The self-improving AI agent built by Nous Research.”
- “It's the only agent with a built-in learning loop...”

Source: https://pypi.org/project/hermes-agent/

### Required Python version
PyPI says:
- `Requires: Python >=3.11`

Source: https://pypi.org/project/hermes-agent/

### Dependencies listed on PyPI
Top-level dependencies listed by PyPI:
- `openai==2.24.0`
- `python-dotenv==1.2.2`
- `fire==0.7.1`
- `httpx[socks]==0.28.1`
- `rich==14.3.3`
- `tenacity==9.1.4`
- `pyyaml==6.0.3`
- `ruamel.yaml==0.18.17`
- `requests==2.33.0`
- `jinja2==3.1.6`
- `pydantic==2.13.4`
- `prompt_toolkit==3.0.52`
- `croniter==6.0.0`
- `PyJWT[crypto]==2.12.1`
- `tzdata==2025.3; sys_platform == "win32"`
- `psutil==7.2.2`

Source: https://pypi.org/project/hermes-agent/

### Extras / optional dependencies listed on PyPI
PyPI lists these extras:
- `anthropic`
- `exa`
- `firecrawl`
- `parallel-web`
- `fal`
- `edge-tts`
- `modal`
- `daytona`
- `hindsight`
- `dev`
- `messaging`
- `cron`
- `slack`
- `matrix`
- `wecom`
- `cli`
- `tts-premium`
- `voice`
- `pty`
- `honcho`
- `mcp`
- `homeassistant`
- `sms`
- `computer-use`
- `acp`
- `bedrock`
- `azure-identity`
- `termux`
- `termux-all`
- `dingtalk`
- `feishu`
- `google`
- `youtube`
- `web`
- `all`

Source: https://pypi.org/project/hermes-agent/

### Messaging extra dependency relevant to Discord
PyPI lists:
- `discord.py[voice]==2.7.1; extra == "messaging"`

Source: https://pypi.org/project/hermes-agent/

---

## 8) Web search findings

### Discord integration search result
A web result for “Hermes Agent discord integration” points to the official Discord page and confirms:
- Hermes integrates with Discord as a bot
- it supports text, voice messages, file attachments, and slash commands
- the Discord gateway is session-aware, not stateless

Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord

### Session management search result
A web result for “Hermes Agent session management” points to the official sessions page and confirms:
- sessions are stored in SQLite `~/.hermes/state.db`
- sessions support resume, export, delete, rename, prune, stats
- `session_search` exists for FTS5 search and scrolling through old sessions

Source: https://hermes-agent.nousresearch.com/docs/user-guide/sessions

---

## 9) Exact code snippets and signatures collected

### Python
```python
from run_agent import AIAgent
```

```python
agent = AIAgent(
    model="anthropic/claude-sonnet-4.6",
    quiet_mode=True,
)
```

```python
response = agent.chat("What is the capital of France?")
```

```python
result = agent.run_conversation(
    user_message="Search for recent Python 3.13 features",
    task_id="my-task-1",
)
```

```python
result = agent.run_conversation(
    user_message="Explain quicksort",
    system_message="You are a computer science tutor. Use simple analogies.",
)
```

```python
result1 = agent.run_conversation("My name is Alice")
history = result1["messages"]
result2 = agent.run_conversation(
    "What's my name?",
    conversation_history=history,
)
```

### MCP YAML
```yaml
mcp_servers:
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
```

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    tools:
      include: [list_issues, create_issue, search_code]
      prompts: false
      resources: false
```

```yaml
mcp_servers:
  docs:
    command: "docs-server"
    supports_parallel_tool_calls: true
```

### Discord env/config examples
```bash
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_ALLOWED_USERS=284102345871466496
```

```bash
hermes gateway
```

```yaml
discord:
  require_mention: true
  thread_require_mention: false
  free_response_channels: ""
  auto_thread: true
  reactions: true
  ignored_channels: []
  no_thread_channels: []
  history_backfill: true
  history_backfill_limit: 50
  channel_prompts: {}
  allow_mentions:
    everyone: false
    roles: false
    users: true
    replied_user: true
group_sessions_per_user: true
```

---

## 10) Bottom line for Python callers

The official Python docs only explicitly document one Python class entry point: `AIAgent` from `run_agent`.

The documented usage patterns are:
- construct `AIAgent(...)`
- call `agent.chat(...)` for a simple string response
- call `agent.run_conversation(...)` for structured response + history
- pass `conversation_history=...` to continue a session
- use `skip_memory=True` and `skip_context_files=True` for stateless API use
- use `enabled_toolsets` / `disabled_toolsets` to constrain tool access
- use `platform="discord"` when embedding in Discord-adjacent flows

For session work, the documented session API is primarily:
- `hermes sessions ...` CLI
- `session_search(...)` tool
- `conversation_history` in Python programmatic usage

For Discord, Hermes is a full messaging gateway with session lookup, transcript loading, and mention/thread behavior, not a stateless bot wrapper.
