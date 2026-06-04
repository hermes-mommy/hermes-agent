# MASTER HERMES INTEGRATION REPORT

> **Date**: 2026-06-03  
> **Scope**: Guinevere ↔ Hermes Agent integration gap analysis  
> **Status**: RESEARCH COMPLETE — No implementation started  
> **Method**: 5 parallel sub-agents + direct file reads

---

## SECTION 1: HERMES CAPABILITIES CONFIRMED

### 1.1 Package Status

| Attribute | Value |
|---|---|
| **Package** | `hermes-agent` v0.15.2 (PyPI) |
| **Installed on VPS** | ❌ NOT currently installed in VPS venv |
| **In pyproject.toml** | ✅ `"hermes-agent>=0.15"` |
| **Config on VPS** | ✅ `/home/guinevere/config/hermes/config.yaml` (1.8KB) |
| **System prompt on VPS** | ✅ `/home/guinevere/config/hermes/system-prompt.md` (24KB) |
| **P1 install evidence** | ✅ `hermes-install.txt` proves v0.15.2 was installed during P1-004 |
| **Import path** | `import agent` (82 modules in `agent/` package) |

> **Key finding**: Hermes was installed once, config/system-prompt files remain, but the package was lost during a venv recreation or reimage. Current runtime is 100% custom and never calls Hermes.

### 1.2 Agent Runtime API (`agent/agent_init.py`)

Hermes provides the AIAgent class — the primary way to use it programmatically:

```python
from agent.agent_init import AIAgent

agent = AIAgent(
    base_url="http://localhost:20128/v1",  # 9Router endpoint
    model="cx/gpt-5.5",
    # Additional config via HermesSettings / config injection
)

# Single chat call
response = agent.chat("Hello!")
# Returns OpenAI-compatible response dict

# Multi-turn conversation
result = agent.run_conversation("Tell me about Python")
# Handles context, tool calls, memory automatically
```

**Key modules in `agent/` package:**

| Module | Purpose |
|---|---|
| `agent_init.py` | AIAgent class — main entrypoint for Hermes |
| `conversation_loop.py` | Multi-turn conversation state machine |
| `chat_completion_helpers.py` | OpenAI-compatible LLM call formatting |
| `memory_manager.py` | Persistent memory storage and recall |
| `memory_provider.py` | Memory backend abstraction |
| `tool_executor.py` | Tool/function calling executor |
| `tool_dispatch_helpers.py` | Tool dispatch and routing |
| `prompt_builder.py` | System prompt assembly |
| `system_prompt.py` | System prompt loading |
| `context_compressor.py` | Context window management |
| `context_engine.py` | Context state management |

### 1.3 Transport Layer (`agent/transports/`)

**IMPORTANT CORRECTION**: The `agent/transports/` directory is NOT the Discord/gateway adapter layer. It is the **LLM provider API transport normalization** layer. Files found:

| File | Purpose |
|---|---|
| `base.py` | Abstract `ProviderTransport` base class |
| `chat_completions.py` | `ChatCompletionsTransport` — OpenAI-compatible providers |
| `anthropic.py` | `AnthropicTransport` — Anthropic Messages API |
| `bedrock.py` | `BedrockTransport` — AWS Bedrock Converse API |
| `codex.py` | `ResponsesApiTransport` — OpenAI Responses/Codex API |
| `types.py` | `NormalizedResponse`, `ToolCall`, `Usage` dataclasses |

All transport classes normalize provider-specific responses into a shared Hermes format for the agent loop.

### 1.4 Discord Gateway

Hermes Discord support exists as a **separate messaging gateway process** (not via Python import):

```bash
# CLI commands
hermes gateway setup       # Interactive: select Discord, provide token
hermes gateway run         # Run gateway process
hermes gateway install     # Install as systemd service
hermes gateway start       # Start installed service
```

**Configuration** (via `.env` or `~/.hermes/.env`):
```env
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_ALLOWED_USERS=284102345871466496
DISCORD_REQUIRE_MENTION=false
DISCORD_FREE_RESPONSE_CHANNELS=1510914600777023659
```

**Session behavior**:
- Each DM = isolated session
- Each server thread = isolated session
- Each user in shared channel = isolated session (controlled by `group_sessions_per_user: true`)
- Built-in support for streaming, slash commands, skills, reactions, threads, tool calls

### 1.5 Memory System

Hermes has its own memory system (`agent/memory_manager.py`, `agent/memory_provider.py`):
- Supports persistent storage backends
- Memory recall across sessions
- Memory storage during conversations

**Does NOT replicate Guinevere's custom safety controls**:
- No classification ceiling enforcement
- No DNR (Do Not Recall) exclusion
- No safe-mode content redaction
- No principal-based access control
- No evidence/audit logging

### 1.6 MCP / Tool Integration

Hermes has:
- `tool_executor.py` — Executes tool/function calls from LLM
- `tool_dispatch_helpers.py` — Routes tool calls to handlers
- MCP transport at `agent/transports/hermes_tools_mcp_server.py`

Our platform: custom `FastMCP` server at `src/mcp/manager.py` with project-specific tool registry.

---

## SECTION 2: GAP LIST (PRIORITIZED)

### GAP-01: Session Management — CRITICAL

| Field | Value |
|---|---|
| **Current state** | **No session management.** Each message in `conversational_handler.py` is a stateless single-turn LLM call. No conversation history, no context carry-over, no user session isolation. |
| **Ideal state (via Hermes)** | Hermes AIAgent provides `run_conversation()` with per-user isolated sessions, conversation history, context persistence. Discord gateway has built-in per-user session isolation. |
| **Effort to fix** | **2-3 days.** Create `HermesConversationAdapter` that wraps AIAgent per user. Add session store (Redis). Wire into `_process_and_respond()`. |
| **Dependencies** | GAP-04 (Hermes reinstall), GAP-05 (memory bridge) |
| **Why CRITICAL** | Without sessions, every message is a fresh context with no memory of previous turns. This is the root cause of many hallucination/consistency issues. |

### GAP-02: Conversation History — HIGH

| Field | Value |
|---|---|
| **Current state** | **Single LLM call with system prompt + current message only.** No message history array building. The `messages_list` in `_process_and_respond()` always contains exactly 2 items: system + user. |
| **Ideal state** | AIAgent maintains conversation history internally. Hermes tracks messages, tool calls, and context across turns. Session-aware context management via `context_compressor`. |
| **Effort to fix** | **1 day.** Part of GAP-01 implementation. AIAgent handles history automatically when you use `run_conversation()` instead of raw `chat()`. |
| **Dependencies** | GAP-01 |

### GAP-03: /new Command — LOW

| Field | Value |
|---|---|
| **Current state** | **Does not exist.** No way to reset conversation context. |
| **Ideal state** | Hermes Discord gateway has `/new` built-in to reset session. Or implement as a custom slash command that clears session state. |
| **Effort to fix** | **2-4 hours.** Either enable Hermes gateway `/new` or implement as a simple Redis session delete. |
| **Dependencies** | GAP-01 |

### GAP-04: MCP Tool Calling in Conversations — HIGH

| Field | Value |
|---|---|
| **Current state** | **Not wired.** `conversational_handler.py` never calls MCP tools. It's a pure text-in/text-out pipeline. The MCP server at `src/mcp/manager.py` exists independently and is never integrated with the conversational flow. |
| **Ideal state** | Hermes AIAgent has built-in tool calling. When the LLM decides to use a tool, Hermes routes through `tool_executor` → tool handler → response. Our FastMCP tools need to be registered with Hermes. |
| **Effort to fix** | **1-2 days.** Register our MCP tools with Hermes tool registry. Hermes would need access to the tool definitions (which we have via `register_all_tools`). |
| **Dependencies** | GAP-01, Hermes reinstall |

### GAP-05: Memory Auto-Store — HIGH

| Field | Value |
|---|---|
| **Current state** | **Read-only memory recall only.** `read_pipeline.py` only does retrieval. No automatic memory storage happens during conversations. `cmd_memory_add.py` exists for manual writes but no auto-store. |
| **Ideal state** | Hermes `memory_manager` automatically stores relevant information during conversations, extracting facts, preferences, and context for later retrieval. |
| **Effort to fix** | **1-2 days.** Create a memory bridge that wraps our `read_pipeline.py` (for reads with safety enforcement) and Hermes `memory_manager` (for auto-store). Or: implement our own auto-classify + store pipeline. |
| **Dependencies** | GAP-01, Hermes reinstall. Safety-critical: any auto-store must respect classification boundaries. |

### GAP-06: Y4 Persona Consistency — LOW

| Field | Value |
|---|---|
| **Current state** | SystemPromptMaster loaded at startup via `prompt_loader.load_system_prompt()`. The 24KB system-prompt.md contains full Y4 persona. Hermes config.yaml has identity fields. |
| **Ideal state** | Both Hermes config and system prompt file reference the same persona. Hermes config has `agent.identity: "Guinevere de Baroque"` — matches system prompt. |
| **Effort to fix** | **Minimal.** System prompt already deployed at Hermes path. Config already has correct identity. Only need to ensure Hermes uses the file-based prompt rather than overriding. |
| **Dependencies** | None |

### GAP-07: Discord-Specific Features — LOW

| Field | Value |
|---|---|
| **Current state** | Custom: typing indicator, auto-split response, rate limiting, Faiz-only guard, distress detection, safe mode. |
| **Ideal state** | Hermes gateway provides: reactions, streaming, threads, auto-thread, typing indicator, per-user sessions, slash commands, file attachments. But Hermes doesn't have: Guinevere-style HARD STOP, distress detection, safe mode, classification-based guard. |
| **Effort to fix** | **If using Hermes gateway**: reimplement all safety guards in Hermes layer (2-3 weeks). If keeping custom bot + Hermes library: minimal (keep existing features, add Hermes only as LLM backend). |
| **Dependencies** | Architecture decision (see Section 3) |

### GAP-08: Streaming Response — LOW

| Field | Value |
|---|---|
| **Current state** | **No streaming.** Full response is generated, then sent in chunks via `_split_response()`. User sees typing indicator for ~15s then gets full response. |
| **Ideal state** | Hermes gateway supports streaming responses to Discord. Messages appear progressively, improving UX. |
| **Effort to fix** | **2-4 hours.** Enable streaming in LLMRouter when Hermes is the backend. Discord supports streaming via edit + progressive update. |
| **Dependencies** | GAP-01 |

---

## SECTION 3: INTEGRATION ARCHITECTURE

### 3.1 Recommended Approach

```
┌─────────────────────────────────────────────────────────┐
│                    Custom Discord Bot                     │
│                  (bot.py + conversational_handler.py)     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Guard Layer (KEEP CUSTOM)            │   │
│  │  • HARD STOP / safe-word detection                │   │
│  │  • Channel filtering (only #guinevere-chat)       │   │
│  │  • Faiz-only authorization                        │   │
│  │  • Rate limiting (Redis)                          │   │
│  │  • Distress detection / safe mode                 │   │
│  │  • Consent / surveillance boundaries              │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│                         ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Hermes Conversation Adapter              │   │
│  │              (NEW — Python library mode)           │   │
│  │                                                    │   │
│  │  • AIAgent per user (session-aware)               │   │
│  │  • run_conversation() for multi-turn              │   │
│  │  • Tool registry bridge to FastMCP                │   │
│  │  • Memory bridge to read_pipeline.py              │   │
│  │  • Cost tracking passthrough                      │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
└─────────────────────────┼────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    9Router (localhost:20128)              │
│                    cx/gpt-5.5, ds/deepseek-v4-flash       │
│                    guinevere (combo)                      │
└─────────────────────────────────────────────────────────┘
```

**Decision: Use Hermes as Python library, NOT as Discord gateway replacement.**

Rationale:
1. **Safety-preserving**: All existing safety guards remain intact and non-bypassable
2. **Incremental adoption**: Replace one layer at a time (session → memory → tools → streaming)
3. **No rewrites**: bot.py stays, conversational_handler.py gets adapter, not replacement
4. **Hermes gateway complexity**: The Hermes gateway is a full process that would require reimplementing all our safety logic inside Hermes config/hooks. Risk of safety regression is high.

### 3.2 Session Flow (Proposed)

```
User sends message in #guinevere-chat
       │
       ▼
Custom guard checks (HARD STOP, channel, Faiz, rate limit)
       │
       ▼
Distress detection + mood evaluation
       │
       ▼
HermesConversationAdapter.start_or_resume(user_id)
       │
       ├─ Lookup session_id in Redis (per-user)
       ├─ Create AIAgent if new, resume if existing
       │
       ▼
HermesConversationAdapter.send(content)
       │
       ├─ AIAgent.run_conversation(content)
       │   ├─ auto-includes conversation history
       │   ├─ auto-manages context window
       │   ├─ calls tools if needed → routes to our MCP tools
       │   └─ auto-stores memories if configured
       │
       ├─ Token usage + cost tracking
       │
       ▼
Response split + send to Discord
```

### 3.3 Memory Flow (Proposed)

```
Hermes wants memory context
       │
       ▼
Memory Bridge (new adapter module)
       │
       ├─ WRITE path (auto-store):
       │   ├─ Extract key facts from conversation
       │   ├─ Classify (standard/restricted/confidential)
       │   ├─ Store via existing memory storage pipeline
       │   └─ Respect classification ceilings
       │
       ├─ READ path (recall):
       │   └─ Our custom read_pipeline.py (enforces DNR, classification, safe-mode)
       │
       ▼
Safe content returned to Hermes (or base prompt if blocked)
```

### 3.4 Tool Flow (Proposed)

```
Hermes decides to call a tool
       │
       ▼
HermesToolBridge (new adapter)
       │
       ├─ Translate Hermes tool call format → our tool handler
       ├─ Invoke via existing FastMCP tool registry
       ├─ Respect auth matrix (read=auto, write=notify, destructive=approval)
       │
       ▼
Tool result returned to Hermes
       │
       ▼
AIAgent continues conversation with tool result context
```

---

## SECTION 4: DISCORD COMMANDS IMPACT

### Hermes Built-in Commands (via `hermes gateway`)

If using Hermes gateway directly (NOT recommended for Phase 1):

| Command | Description |
|---|---|
| `/new` | Start new session |
| `/history` | Show conversation history |
| `/context` | Show current context |
| `/forget` | Clear session |
| `!hermes` or `!skills` | Skill management |
| model switching | Change current model |

### If using Library Mode (Recommended)

These commands DON'T exist from Hermes library mode. We implement them ourselves:

| Command | Current | With Hermes |
|---|---|---|
| `/new` | ❌ Doesn't exist | Can implement: clear AIAgent session |
| `/history` | ❌ Doesn't exist | Can implement: read via Hermes session data or our own store |
| `/context` | ❌ Doesn't exist | Can get from AIAgent if available |
| `/forget` | Partially via /memory-forget | Clear session + memory |

---

## SECTION 5: IMPLEMENTATION PLAN

### Phase 1: Foundation (3-5 days)

**Step 1: Reinstall Hermes + verify**
```bash
cd /home/guinevere/code/guinevere
source .venv/bin/activate
uv pip install hermes-agent>=0.15
python -c "import agent; print(agent.__version__)"
```

**Step 2: Create HermesSessionAdapter**
- `src/hermes/session_adapter.py`
- Manages AIAgent per user session via Redis store
- `start_or_resume(user_id)` → AIAgent
- `send(agent, content)` → response
- `close(user_id)` → cleanup
- Integration point: called from `_process_and_respond()` after safety checks

**Step 3: Session Redis store**
- Key: `hermes:session:{user_id}`
- Value: session_id or serialized state
- DB: DB3 (Hermes convention) or DB0 (rate limit proximity)

### Phase 2: Memory Bridge (2-3 days)

**Step 4: Create HermesMemoryBridge**
- `src/hermes/memory_bridge.py`
- READ: wraps `recall_memories()` — same safety enforcement
- WRITE: auto-classifies and stores conversation facts
- Token budget enforcement from prompt_loader

**Step 5: Integrate bridge with Hermes adapter**
- AIAgent gets memory provider via Hermes config
- Memory context injected into system prompt

### Phase 3: Tools (2-3 days)

**Step 6: Create HermesToolBridge**
- `src/hermes/tool_bridge.py`
- Register our FastMCP tools with Hermes
- Auth matrix enforcement before tool execution
- Tool result logging and evidence tracking

**Step 7: Wire tool bridge into session adapter**
- Hermes AIAgent configured with tool definitions
- Tool calls routed back to our handlers

### Phase 4: Polish (1-2 days)

**Step 8: Implement /new command**
- Slash command that clears Hermes session

**Step 9: Implement /history command**
- Show recent conversation history from Hermes session

**Step 10: Optional streaming**
- Enable streaming in Hermes adapter for progressive Discord responses

### Total Estimated Effort: 8-13 days

---

## SECTION 6: RISKS & CAVEATS

### Risk 1: Safety Boundary Bypass (CRITICAL)

| Detail | Value |
|---|---|
| **Risk** | Hermes AIAgent, once invoked, has its own agent loop with tool calling. If not properly constrained, it could bypass Guinevere's safety boundaries (HARD STOP, consent, approval gates). |
| **Mitigation** | (1) Guard layer runs BEFORE Hermes invocation — never after. (2) Tool bridge enforces auth matrix server-side, not via LLM instruction. (3) Hermes must never receive critical/restricted memory without safe-mode filtering. (4) Separate Hermes sub-agent from main agent safety context. |

### Risk 2: Version Mismatch (MEDIUM)

| Detail | Value |
|---|---|
| **Risk** | `hermes-agent` evolves rapidly (16 releases in 3 months). v0.15.2 API may differ from latest. Package may have breaking changes. |
| **Mitigation** | Pin exact version in pyproject.toml. Document which API surface we use. Test upgrade in staging. Upstream 174K stars, 390 contributors — active but stable. |

### Risk 3: Memory Privacy Bypass (HIGH)

| Detail | Value |
|---|---|
| **Risk** | Hermes `memory_manager` may auto-store raw conversation content without respecting Guinevere's classification labels. Sensitive data could persist in Hermes's own store. |
| **Mitigation** | (1) Disable Hermes native memory auto-store. (2) Use only our read_pipeline.py as memory provider. (3) If using auto-store, classify content before storage. (4) Memory bridge must catch classification violations. |

### Risk 4: Context Window Bloat (MEDIUM)

| Detail | Value |
|---|---|
| **Risk** | Multi-turn session with Hermes AIAgent will accumulate conversation history. Without context management, token usage grows unbounded per session. |
| **Mitigation** | Hermes has `context_compressor.py` and `context_engine.py` — enable these. Set session max_tokens limit. Implement session timeout (e.g., expire after 1h idle). |

### Risk 5: Performance (LOW)

| Detail | Value |
|---|---|
| **Risk** | AIAgent adds overhead vs direct LLMRouter call. Session management, context tracking, tool dispatch all increase latency. |
| **Mitigation** | Measure baseline vs Hermes latency. Keep FALLBACK_MESSAGE at 30s. AIAgent overhead should be < 100ms vs direct 9Router call. |

### Risk 6: Hermes Gateway vs Library Confusion (LOW)

| Detail | Value |
|---|---|
| **Risk** | Team may confuse Hermes gateway mode (replaces our entire bot) with Hermes library mode (imports agent package). Wrong mode adopted = safety regression. |
| **Mitigation** | **Explicit decision documented**: Use Hermes as Python library only. Never deploy `hermes gateway` on production. Gateway replaces our bot; library extends it. Library is the safe path. |

---

## SECTION 7: IMMEDIATE NEXT STEPS

1. **✅ COMPLETE**: Master research report written to `research-reports/hermes-integration/MASTER-HERMES-INTEGRATION-REPORT.md`
2. **Faiz decision**: Review this report and decide whether to proceed with Phase 1 Implementation
3. **Phase 1 (if approved)**:
   - Reinstall `hermes-agent>=0.15` on VPS
   - Create `src/hermes/session_adapter.py`
   - Wire into `conversational_handler.py`
   - Test with single-turn → multi-turn → session persistence

---

## SECTION 8: APPENDIX — ALL RESEARCH FILES

| File | Agent | Size | Contents |
|---|---|---|---|
| `01-hermes-api-surface.md` | bg_734a9041 (librarian) | 19.9KB | AIAgent API, session management, Discord gateway config, Python library usage |
| `07-hermes-core-api.md` | bg_8212b34b (explore) | — | agent_init/conversation_loop analysis (SSH quoting issue, partial) |
| `08-hermes-transports-discord.md` | bg_39d184fe (explore) | — | Full transport analysis + Discord gateway architecture (read-only, content inline) |
| `06-p1-install-history.md` | bg_6a71cc05 (explore) | — | P1 Hermes install history, current VPS state, dependency analysis |
| `05-current-implementation-analysis.md` | bg_7a7adf03 (explore) | 20KB+ | Full 7-file component analysis with Hermes-replaceable boundaries |
| **MASTER-HERMES-INTEGRATION-REPORT.md** | **This file** | — | Synthesis of all above |
