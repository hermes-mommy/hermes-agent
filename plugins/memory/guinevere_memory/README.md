# Guinevere Memory Plugin for Hermes Agent

> Phase 3 Memory Bridge — PostgreSQL episodic memory wrapped as a Hermes
> `MemoryProvider` plugin.

## Overview

This plugin bridges Hermes Agent's conversational memory system with
Guinevere's PostgreSQL-backed episodic memory pipelines.  It provides:

- **Transparent recall** — relevant memories are injected as context before
  every API call via the `prefetch` hook.
- **Fire-and-forget writes** — conversation turns are persisted in a daemon
  thread via `sync_turn`, never blocking the agent loop.
- **Consent gate** — all reads and writes are blocked when consent is
  revoked (fail-closed).
- **Safe-word detection** — writes are skipped when distress reaches D4
  (crisis).

## Prerequisites

1. **PostgreSQL** with `pgvector` extension enabled.
2. **Redis** (DB5) for consent and safety state checks.
3. Python packages: `sqlalchemy>=2.0`, `pgvector>=0.2`, `redis`.

## Configuration

### Environment Variables

Set the PostgreSQL connection string:

```bash
export GUINEVERE_PG_DSN="postgresql+asyncpg://user:pass@localhost:5432/guinevere"
```

### Config Schema (hermes memory setup wizard)

| Field | Description | Secret | Default |
|-------|-------------|--------|---------|
| `pg_dsn` | PostgreSQL connection string | ✅ | — |
| `embedding_model` | Embedding model name | — | `text-embedding-3-small` |
| `recall_limit` | Max memories per recall | — | `5` |
| `token_budget` | Max token budget for recall | — | `800` |

Secrets are written to `$HERMES_HOME/.env`. Non-secret config is written
to `$HERMES_HOME/guinevere-memory.json`.

## Hooks

| Hook | Description |
|------|-------------|
| `prefetch` | Recalls relevant episodic context before each turn |
| `sync_turn` | Persists conversation turns (non-blocking daemon thread) |
| `on_session_end` | Flushes pending writes at session end |
| `on_pre_compress` | Extracts key facts before context compression |
| `system_prompt_block` | Injects memory capabilities description into system prompt |
| `shutdown` | Closes connections and joins pending threads |

## Consent Model

The plugin checks Redis DB5 for the `guinevere:consent:surveillance` key
before any read or write operation.

- **Consent granted** → normal operation.
- **Consent revoked** → operation blocked, log event emitted.
- **Redis unavailable** → fail-closed, operation blocked.

This is the same consent pattern used by the `guinevere_safety` state
manager.  The `surveillance` category is used as the closest consent gate
for memory operations.

## Threading Contract

`sync_turn` **MUST** be non-blocking.  The plugin uses:

1. A `threading.Thread(daemon=True)` to wrap async PostgreSQL writes.
2. A **join-before-new-thread guard**: if a previous sync thread is still
   running, it is joined (with a 10-second timeout) before starting a new
   one.
3. `asyncio.run()` to execute the async write pipeline in the daemon thread.

This ensures the agent's conversation loop is never blocked by memory
storage latency.

## Development

When Hermes Agent is not installed, the plugin falls back to a local stub
`MemoryProvider` base class defined in `base.py`.  The conditional import
in `__init__.py` handles both cases:

```python
try:
    from agent.memory_provider import MemoryProvider
except ImportError:
    from .base import MemoryProvider  # local stub
```

### Registration

```python
from plugins.memory.guinevere_memory import register
register(ctx)
```

### Manual Instantiation

```python
from plugins.memory.guinevere_memory import GuinevereMemoryProvider

provider = GuinevereMemoryProvider()
assert provider.name == "guinevere-memory"
assert provider.is_available()  # True if GUINEVERE_PG_DSN is set

provider.initialize("session-1", hermes_home="/home/faiz/.hermes")

# Recall context
context = provider.prefetch("kopi hitam tanpa gula")

# Store a turn (non-blocking)
provider.sync_turn("Halo Mommy", "Halo Darling!", session_id="session-1")

# Cleanup
provider.shutdown()
```