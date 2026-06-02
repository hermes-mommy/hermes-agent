# P7 Research: Discord Command Patterns for Surveillance

**Source**: Explore agent analysis of src/discord/
**Purpose**: P7-019 (/surveillance-status), P7-020 (/surveillance-pause) implementation

## Current State

### Command Registration (`src/discord/commands.py`)
- 33 `CommandSpec` frozen dataclasses registered
- Surveillance stubs: `surveillance-status`, `surveillance-pause`, `surveillance-resume`
- All stubs use `_make_stub_callback()` returning "not yet implemented"
- Pattern: `CommandSpec(category, name, description, options)` where options are dicts

### Bot (`src/discord/bot.py`, 348 lines)
- `GuinevereBot(commands.Bot)` extends discord.ext.commands.Bot
- `setup_hook()` registers stubs dynamically from `COMMAND_SPECS`
- HARD STOP listener via `on_message` intercepting all messages
- Session factory: `async_sessionmaker` from `DATABASE_URL` env var
- `get_session_factory()` method available on bot instance
- Guild ID: `1_510_876_414_671_323_206`
- `is_faiz_interaction()` checks `interaction.guild.owner_id == interaction.user.id`

### Wired Command Pattern (from `cmd_mood.py`, `cmd_loop_stop.py`)
```python
import discord
import structlog

logger = structlog.get_logger()

SURVEILLANCE_COLOR = 0x0891B2  # Cyan — surveillance category

async def cmd_surveillance_status(interaction: discord.Interaction) -> None:
    """Show active surveillance sources and their status."""
    if not is_faiz_interaction(interaction):
        await interaction.response.send_message(
            "Access denied.", ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # DB query via session factory
    session_factory = interaction.client.get_session_factory()
    async with session_factory() as session:
        # Query surveillance.device_registry WHERE is_active = true
        # Query consent.consent_ledger WHERE scope LIKE 'surveillance.%'
        pass
    
    embed = discord.Embed(
        title="Surveillance Status",
        color=SURVEILLANCE_COLOR,
    )
    # Add fields for each active source
    
    await interaction.followup.send(embed=embed, ephemeral=True)


async def cmd_surveillance_pause(interaction: discord.Interaction) -> None:
    """Temporarily pause surveillance ingestion."""
    if not is_faiz_interaction(interaction):
        await interaction.response.send_message(
            "Access denied.", ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Set Redis flag: surveillance:paused = true, EX 3600
    # Update consent ledger: PAUSE surveillance.* scopes
    
    embed = discord.Embed(
        title="Surveillance Paused",
        description="All surveillance ingestion paused for 1 hour.",
        color=SURVEILLANCE_COLOR,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
```

### Wiring Pattern (in `bot.py` `setup_hook()`)
```python
# Replace stub with real handler
from src.discord.commands.surveillance import (
    cmd_surveillance_status,
    cmd_surveillance_pause,
)

# In setup_hook, after registering stubs:
self.tree.command(name="surveillance-status", guild=discord.Object(id=GUILD_ID))(
    cmd_surveillance_status
)
# Add to core_names tuple for canonical registry validation
```

### Key Implementation Notes

1. **Ephemeral responses**: All surveillance commands MUST be ephemeral (only Faiz sees them)
2. **is_faiz_interaction()**: Guard check before any surveillance action
3. **Redis for pause state**: `surveillance:paused` key with TTL (1 hour default)
4. **Consent ledger integration**: Pause = CONSENT_PAUSED event in consent.ledger table
5. **Embed colors**: Use `SURVEILLANCE_COLOR = 0x0891B2` (cyan)
6. **Error handling**: Try/except with user-friendly error messages, log via structlog
7. **No raw surveillance data in embeds**: Summarize counts and status only

### Redis Integration for Commands
```python
import redis.asyncio as aioredis

async def get_redis() -> aioredis.Redis:
    return aioredis.Redis(
        host="localhost", port=6380, db=2,
        username="guinevere_core",
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
    )

# Pause check in consumer:
paused = await redis.get("surveillance:paused")
if paused:
    logger.info("surveillance_paused", reason="user_request")
    return  # Skip ingestion, keep buffering
```

### API Integration (if commands call core API)
```python
import httpx

async def call_core_api(endpoint: str, method: str = "GET", **kwargs) -> dict:
    api_key = os.environ.get("GUINEVERE_API_KEY", "")
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.request(
            method, endpoint,
            headers={"X-Guinevere-API-Key": api_key},
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()
```
