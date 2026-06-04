# Hermes Phase 1 — Batch Implementation Plan

> **Date:** 2026-06-03
> **Scope:** Phase 1 Hermes Session Adapter integration
> **Evidence Root:** `docs/setup-evidence/hermes-phase1/`
> **Research Inputs:** `research-reports/hermes-phase1/01-04`, `research-reports/hermes-integration/MASTER-HERMES-INTEGRATION-REPORT.md`

---

## Master Todo

| # | Step | Files | Dependency | Parallel | Audit |
|---|---|---|---|---|---|
| 1 | Create `src/hermes/__init__.py` | new | none | can run with 2-3 | audit-batch-A |
| 2 | Create `src/hermes/session_adapter.py` | new | 1 | can run with 3 | audit-batch-A |
| 3 | Safety guard audit | read-only | none | can run with 1-2 | n/a (auditor) |
| 4 | Wire conversational_handler.py | modify | 2 | sequential (after 2) | audit-batch-B |
| 5 | Create `/new` slash command | new + modify bot.py | none | can run with 6 | audit-batch-C |
| 6 | Create `/history` slash command | new + modify bot.py | none | can run with 5 | audit-batch-C |
| 7 | Auto-store to memory | modify conversational_handler.py | 4 | sequential (after 4) | audit-batch-B |
| 8 | Deploy + verify on VPS | VPS | ALL | sequential | audit-batch-D |

---

## Research Synthesis

### Confirmed Findings

| Finding | Source |
|---|---|
| `from run_agent import AIAgent` is correct import | VPS test m0018 |
| AIAgent works with `provider='9router'`, `api_key='sk-local'` | VPS test m0018 |
| `skip_memory=True` disables all Hermes native memory | bg_ed20f91f |
| `run_conversation()` returns dict: `final_response`, `messages`, token counts, cost | VPS test m0018 |
| Conversation history NOT auto-maintained — must pass `conversation_history` explicitly | VPS test m0018, 03-session-isolation.md |
| DB4 is unused — safe for Hermes sessions | bg_a28146d7 |
| Redis connection: `localhost:6380`, user `guinevere_core`, password `REDIS_PASSWORD` env | bg_a28146d7 |
| Key naming convention: `{domain}:{subdomain}:{id}` | bg_a28146d7 |

### AIAgent Initialization Template

```python
from run_agent import AIAgent

agent = AIAgent(
    base_url="http://localhost:20128/v1",
    model="ds/deepseek-v4-flash",
    provider="9router",
    api_key="sk-local",           # dummy key for local 9Router
    quiet_mode=True,               # suppress CLI output
    skip_memory=True,              # DISABLE Hermes native memory
    skip_context_files=True,       # stateless mode
    enabled_toolsets=[],           # no tools needed
    disabled_toolsets=["*"],       # disable all tools
    max_iterations=1,              # single-turn only
)
```

### Session Storage Design

```
Redis DB4 — Key: hermes:session:{user_id}
Value: JSON { "history": [...], "created_at": ISO8601, "last_used": ISO8601, "turn_count": int }
TTL: 7200 (2h idle timeout)
Max history: 20 turns
```

---

## Collision Scan

| Collision | Resolved |
|---|---|
| conversational_handler.py → Step 4 + Step 7 both modify | Sequenced: Step 4 first, Step 7 after |
| bot.py → Step 5 + Step 6 both modify | Can be sequential or single owner; parent owns bot.py |
| Redis DB4 → No existing code uses it | No collision |
| Safety guard order → conversational_handler.py guard order | Parent verifies guard order post-Step 4 |
| Shared docs → None in this phase | No collision |

---

## Step 1: Create `src/hermes/__init__.py`

### Scaffold

| Field | Value |
|---|---|
| Expected Files | `src/hermes/__init__.py` (new) |
| Forbidden Patterns | `as any`, `# type: ignore`, `Any` type, empty except |
| Required Commands | `python -c "from src.hermes import HermesSessionAdapter"` → exit 0 (after Step 2) |
| Hard Rejection | File not created, import fails |

### Content Spec

```python
"""Hermes Session Adapter — Phase 1.

Handles per-user AIAgent session management with Redis DB4 storage.
All safety guards remain in conversational_handler.py — NEVER inside Hermes.
"""
from .session_adapter import HermesSessionAdapter

__all__ = ["HermesSessionAdapter"]
```

---

## Step 2: Create `src/hermes/session_adapter.py`

### Scaffold

| Field | Value |
|---|---|
| Expected Files | `src/hermes/session_adapter.py` (new) |
| Forbidden Patterns | `as any`, `# type: ignore`, `Any`, bare except, `exec()`, `eval()` |
| Required Commands | `python -c "from src.hermes import HermesSessionAdapter; print('OK')"` → exit 0, `lsp_diagnostics src/hermes/` → 0 errors |
| Hard Rejection | Redis connection not using DB4, AIAgent without skip_memory=True, memory enabled, empty error catch, secret in plaintext |

### API Spec

```python
class HermesSessionAdapter:
    """Per-user AIAgent manager with Redis DB4 session store."""

    def __init__(self, redis_client: "Redis", llm_config: dict):
        """Initialize with Redis connection and LLM config.
        
        llm_config must contain: base_url, model, provider, api_key
        """

    async def get_or_create_session(self, user_id: str) -> AIAgent:
        """Get existing AIAgent for user_id, or create new with stored history.
        
        Returns AIAgent with conversation_history loaded from Redis.
        Creates new AIAgent if no session exists.
        """

    async def send_message(self, user_id: str, content: str, system_prompt: str) -> str:
        """Send message via AIAgent and update session history.
        
        1. Get/create AIAgent session
        2. Call run_conversation(user_message=content, system_message=system_prompt)
        3. Extract final_response
        4. Store updated history in Redis
        5. Return final_response string
        """

    async def clear_session(self, user_id: str) -> None:
        """Delete AIAgent instance and Redis session data."""

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict]:
        """Retrieve last N turns from Redis session store."""
```

### Redis Key Design

```
Key: hermes:session:{user_id}
Value (JSON):
{
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    ...
  ],
  "created_at": "2026-06-03T10:00:00+07:00",
  "last_used": "2026-06-03T10:05:00+07:00",
  "turn_count": 5
}
TTL: 7200 seconds
```

### CRITICAL Rules

1. `skip_memory=True` MUST be set — never skip this
2. Conversation history loaded from Redis and passed as `conversation_history` to `run_conversation()`
3. `max_iterations=1` to prevent runaway loops
4. All send_message errors must log + return graceful fallback (never crash)
5. History limited to 20 turns (40 messages) — prune oldest when exceeded
6. No secrets in logs or errors

---

## Step 3: Safety Guard Order Audit (Read-Only)

### What to Verify

The 13-step pipeline in `conversational_handler.py` must maintain this order:

```
1. Channel check
2. Bot user check
3. Slash command check
4. Faiz-only check
5. HARD STOP check        ← SAFETY GATE 1 (BEFORE Hermes)
6. Rate limit check       ← SAFETY GATE 2 (BEFORE Hermes)
7. Typing indicator
8. Distress detection     ← SAFETY GATE 3 (BEFORE Hermes)
9. Mood detection
10. System prompt assembly (Y4 via SystemPromptMaster)
11. Memory recall (with DNR, classification ceiling, safe-mode gates)
12. → HERMES send_message()   ← THE ONLY CHANGE
13. Response processing (split, cost tracking, logging)
14. Memory auto-store     ← AFTER Hermes
```

### Audit Checklist

- [ ] HARD STOP check fires BEFORE Hermes call
- [ ] Rate limit check fires BEFORE Hermes call
- [ ] Distress detection fires BEFORE Hermes call
- [ ] System prompt uses Y4 baseline (SystemPromptMaster)
- [ ] Memory recall applies DNR + classification ceiling + safe-mode gates BEFORE Hermes
- [ ] Cost tracking fires AFTER Hermes response
- [ ] Memory auto-store fires AFTER Hermes response
- [ ] No safety logic moves inside HermesSessionAdapter

---

## Step 4: Wire `conversational_handler.py`

### Scaffold

| Field | Value |
|---|---|
| Expected Files | `src/discord/conversational_handler.py` (modify) |
| Forbidden Patterns | `as any`, `# type: ignore`, bare except, removing any existing guard |
| Required Commands | `python -m pytest tests/ -k "conversation" -v` → PASS, `lsp_diagnostics src/discord/conversational_handler.py` → 0 new errors |
| Hard Rejection | Guard order changed, HARD STOP bypassed, Hermes called without skip_memory, system prompt not Y4 |

### Exact Changes

**1. Add import at top:**
```python
from src.hermes import HermesSessionAdapter
```

**2. Add to `__init__`:**
```python
self._hermes = HermesSessionAdapter(
    redis_client=self._redis,  # reuse existing Redis (DB4 internally)
    llm_config={
        "base_url": "http://localhost:20128/v1",
        "model": "ds/deepseek-v4-flash",
        "provider": "9router",
        "api_key": "sk-local",
    }
)
```

**3. Replace LLM call (find the `self._call_llm()` or `self.router.chat()` call):**

BEFORE (current):
```python
response = await self._call_llm(system_prompt, message.content)
# or
response = await self.router.chat(messages_list)
```

AFTER:
```python
response = await self._hermes.send_message(
    user_id=str(message.author.id),
    content=message.content,
    system_prompt=system_prompt,
)
```

### VERIFICATION: Confirm guard position

Read conversational_handler.py and verify the Hermes call is AFTER:
1. HARD STOP check
2. Rate limit check
3. Distress detection
4. System prompt assembly

---

## Step 5: Create `/new` Slash Command

### Scaffold

| Field | Value |
|---|---|
| Expected Files | `src/discord/cmd_new_session.py` (new), `src/discord/bot.py` (modify) |
| Forbidden Patterns | `as any`, `# type: ignore`, bare except, non-Faiz guard missing |
| Required Commands | `python -m pytest tests/ -k "new_session" -v` → PASS, `lsp_diagnostics` clean |
| Hard Rejection | Missing Faiz-only guard, no confirmation embed |

### File: `src/discord/cmd_new_session.py`

```python
@app_commands.command(name="new", description="Start new conversation session (Faiz only)")
@app_commands.default_permissions()
async def cmd_new_session(interaction: discord.Interaction) -> None:
    """Clear Hermes session — Faiz-only."""
    # Faiz-only guard
    if interaction.user.id != FAIZ_USER_ID:
        await interaction.response.send_message("Command ini hanya untuk Faiz.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    await hermes.clear_session(str(interaction.user.id))

    embed = discord.Embed(
        title="✨ Session Baru",
        description="Conversation session telah di-reset. Guinevere memulai percakapan baru.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
```

### Bot.py change: Register in `setup_hook`

Follow existing pattern for command registration. Add import and register.

---

## Step 6: Create `/history` Slash Command

### Scaffold

| Field | Value |
|---|---|
| Expected Files | `src/discord/cmd_history.py` (new), `src/discord/bot.py` (modify) |
| Forbidden Patterns | `as any`, `# type: ignore`, bare except, non-Faiz guard missing |
| Required Commands | `python -m pytest tests/ -k "history" -v` → PASS, `lsp_diagnostics` clean |
| Hard Rejection | Missing Faiz-only guard, raw content leak in embed |

### File: `src/discord/cmd_history.py`

```python
@app_commands.command(name="history", description="Show last 10 conversation turns (Faiz only)")
@app_commands.default_permissions()
async def cmd_history(interaction: discord.Interaction) -> None:
    """Show Hermes session history — Faiz-only."""
    if interaction.user.id != FAIZ_USER_ID:
        await interaction.response.send_message("Command ini hanya untuk Faiz.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    history = await hermes.get_history(str(interaction.user.id), limit=10)

    if not history:
        await interaction.followup.send("Belum ada conversation history.", ephemeral=True)
        return

    embed = discord.Embed(title="📜 Conversation History", color=discord.Color.blue())
    for i, turn in enumerate(history, 1):
        # Truncate to 200 chars to fit Discord embed field limit
        content = turn.get("content", "")[:200]
        role = turn.get("role", "unknown")
        embed.add_field(name=f"{i}. {role}", value=content, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)
```

### Bot.py change: Register in setup_hook

---

## Step 7: Auto-Store to Memory

### Scaffold

| Field | Value |
|---|---|
| Expected Files | `src/discord/conversational_handler.py` (modify) |
| Forbidden Patterns | bare except (must log error), blocking call, missing classification |
| Required Commands | `python -m pytest tests/ -k "memory_store" -v` → PASS |
| Hard Rejection | store_episode called without classification, blocking I/O, crash on memory failure |

### Changes

After Hermes response (in conversational_handler.py), after cost tracking, add:

```python
# Auto-store conversation to memory (after response, never blocks)
if self.memory_enabled:
    try:
        await store_episode(
            content=f"Faiz: {message.content}\nGuinevere: {response}",
            source="discord_conversation",
            classification="Restricted",
            importance=3,
            summary=message.content[:200],  # first 200 chars as summary
        )
    except Exception as e:
        logger.warning(f"Memory auto-store failed (non-fatal): {e}")
        # NEVER crash — memory store is best-effort
```

---

## Step 8: Deploy + Verify on VPS

### Scaffold

| Field | Value |
|---|---|
| Expected Files | All new/modified files synced to VPS |
| Required Commands | `systemctl restart guinevere-discord` → exit 0, multi-turn test, /new test, /history test |
| Hard Rejection | Service fails to restart, multi-turn context lost, safety guard bypass |

### Verification Script (run on VPS)

```bash
# 1. Sync files
rsync -avz --exclude='.venv' --exclude='__pycache__' \
  src/ guinevere-vps:/home/guinevere/code/guinevere/src/

# 2. Restart
ssh guinevere-vps "sudo systemctl restart guinevere-discord"
sleep 5
ssh guinevere-vps "sudo systemctl status guinevere-discord --no-pager"

# 3. Test via Discord (manual):
# - Send "aku suka kopi" → expect reply
# - Send "aku tadi bilang apa?" → expect "kamu suka kopi"
# - /new → expect "Session baru dimulai"
# - Send "apa hobiku?" → expect NO memory of coffee
# - /history → expect shows turns
```

---

## Auditor Matrix

| Auditor | Check | Steps | Verdict |
|---|---|---|---|
| Safety Auditor | Guard order preserved, HARD STOP before Hermes, Y4 system prompt | 3, 4, 7 | PASS/FAIL |
| Integration Auditor | Hermes wired correctly, multi-turn works | 2, 4, 8 | PASS/FAIL |
| Memory Auditor | No privacy bypass, skip_memory=True, classification ceiling | 2, 4, 7 | PASS/FAIL |
| Functional Auditor | /new clears, /history shows, multi-turn context | 5, 6, 8 | PASS/FAIL |

---

## Rollback Plan

1. Revert `conversational_handler.py` to pre-Hermes state (restore `self._call_llm()` call)
2. Remove `src/hermes/` directory
3. Remove `/new` and `/history` from `bot.py` setup_hook
4. Delete `cmd_new_session.py` and `cmd_history.py`
5. Restart guinevere-discord

---

## Binding Decisions

1. **Hermes native memory DISABLED**: `skip_memory=True` — non-negotiable
2. **Provider/API key**: `provider="9router"`, `api_key="sk-local"` (local 9Router doesn't validate)
3. **Redis DB4**: Dedicated for Hermes sessions, no collision with existing
4. **History cap**: 20 turns (40 messages) to stay within context window
5. **Session TTL**: 2 hours idle → auto-expire in Redis
6. **Safety guards**: Stay in conversational_handler.py, NEVER in HermesSessionAdapter
7. **Memory auto-store**: Best-effort, never blocks, never crashes
8. **Faiz-only guards**: `/new` and `/history` require Faiz user ID

---

## Evidence Paths

| Step | Evidence File |
|---|---|
| 1-2 | `docs/setup-evidence/hermes-phase1/verification-step-1-2.md` |
| 3 | `docs/setup-evidence/hermes-phase1/safety-audit-step-3.md` |
| 4 | `docs/setup-evidence/hermes-phase1/verification-step-4.md` |
| 5-6 | `docs/setup-evidence/hermes-phase1/verification-step-5-6.md` |
| 7 | `docs/setup-evidence/hermes-phase1/verification-step-7.md` |
| 8 | `docs/setup-evidence/hermes-phase1/verification-step-8.md` |
| Auditors | `docs/setup-evidence/hermes-phase1/auditor-*.md` |

---

## Execution Checklist

- [ ] Step 1: `src/hermes/__init__.py` created
- [ ] Step 2: `src/hermes/session_adapter.py` created
- [ ] Step 3: Safety guard order audit completed
- [ ] Step 4: conversational_handler.py wired to Hermes
- [ ] Step 5: /new slash command created + registered
- [ ] Step 6: /history slash command created + registered
- [ ] Step 7: Auto-store to memory added
- [ ] Step 8: Deployed + verified on VPS
- [ ] All LSP diagnostics clean
- [ ] All tests pass
- [ ] Auditor gates: Safety, Integration, Memory, Functional — all PASS
