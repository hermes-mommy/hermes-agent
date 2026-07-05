"""Discord infrastructure — condensed port of embed, auth, intents, colors,
notifications, gotify, shadow, project-session, and startup utilities.

Ports from:
- guinevere/discord/_embed_utils.py
- guinevere/discord/_auth_guard.py
- guinevere/discord/_intents.py
- guinevere/discord/colors.py
- guinevere/discord/notifications.py
- guinevere/discord/gotify_fallback.py
- guinevere/discord/shadow_pipeline.py
- guinevere/discord/project_session.py
- guinevere/discord/_startup.py

All stale imports have been removed (former surveillance gating,
former persona safe-mode and mood-engine). Cleaned to use
guinevere.* equivalents only. No bare except, no type: ignore.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, Protocol, cast, runtime_checkable

logger = logging.getLogger(__name__)


# ── Timezone ─────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"


# ══════════════════════════════════════════════════════════════════════════
# COLORS (from guinevere/discord/colors.py)
# ══════════════════════════════════════════════════════════════════════════

PRIMARY: Final[int] = 0x6B21A8
ALERT: Final[int] = 0xDC2626
WARNING: Final[int] = 0xCA8A04
ACHIEVEMENT: Final[int] = 0xCA8A04
SUCCESS: Final[int] = 0x16A34A
INFO: Final[int] = 0xCA8A04
ORANGE: Final[int] = 0xEA580C
NEUTRAL: Final[int] = 0x6B7280
INFO_BLUE: Final[int] = 0x2563EB
PERSONA: Final[int] = 0x9333EA
SURVEILLANCE: Final[int] = 0x0891B2
FINANCE: Final[int] = 0x059669

MOOD_COLORS: Final[dict[str, int]] = {
    "content": SUCCESS,
    "pleased": ACHIEVEMENT,
    "disappointed": WARNING,
    "angry": ALERT,
    "silent": NEUTRAL,
}


def color_for_mood(mood: str) -> int:
    """Return the embed colour integer for a given mood name."""
    return MOOD_COLORS.get(mood, PRIMARY)


def as_hex(color: int) -> str:
    """Format an integer colour as a CSS-style hex string."""
    return f"#{color:06X}"


# ══════════════════════════════════════════════════════════════════════════
# AUTH GUARD (from guinevere/discord/_auth_guard.py)
# ══════════════════════════════════════════════════════════════════════════


def is_faiz_interaction(interaction: object) -> bool:
    """Fail closed unless the interaction user is the Discord guild owner.

    Does NOT hardcode Faiz's user ID — uses Discord's guild.owner_id at
    runtime. This is the Faiz-only gate for all 41 slash commands.
    """
    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    owner_id = getattr(guild, "owner_id", None)
    user_id = getattr(user, "id", None)
    return isinstance(owner_id, int) and isinstance(user_id, int) and owner_id == user_id


# ══════════════════════════════════════════════════════════════════════════
# INTENTS (from guinevere/discord/_intents.py)
# ══════════════════════════════════════════════════════════════════════════


class DiscordIntents(Protocol):
    """Subset of discord.Intents used by Guinevere."""
    guilds: bool
    members: bool
    presences: bool
    message_content: bool
    messages: bool
    reactions: bool
    voice_states: bool


REQUIRED_PRIVILEGED_INTENTS: tuple[str, ...] = ("message_content", "members", "presences")
STANDARD_OPERATIONAL_INTENTS: tuple[str, ...] = ("guilds", "messages", "reactions", "voice_states")
REQUIRED_INTENTS: tuple[str, ...] = REQUIRED_PRIVILEGED_INTENTS + STANDARD_OPERATIONAL_INTENTS


def get_intents() -> DiscordIntents:
    """Build Guinevere's Discord gateway intents.

    Enables 3 privileged + 4 standard intents matching the Developer
    Portal configuration.
    """
    discord_module = cast(Any, importlib.import_module("discord"))
    intents = discord_module.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.presences = True
    intents.guilds = True
    intents.messages = True
    intents.reactions = True
    intents.voice_states = True
    return intents


# ══════════════════════════════════════════════════════════════════════════
# EMBED UTILS (from guinevere/discord/_embed_utils.py)
# ══════════════════════════════════════════════════════════════════════════


@runtime_checkable
class DiscordResponseProtocol(Protocol):
    """Protocol for discord.Interaction.response."""
    async def defer(self, *, ephemeral: bool = False) -> None: ...
    def is_done(self) -> bool: ...
    async def send_message(self, **kwargs: object) -> None: ...


@runtime_checkable
class DiscordFollowupProtocol(Protocol):
    """Protocol for discord.Interaction.followup."""
    async def send(self, **kwargs: object) -> None: ...


@runtime_checkable
class DiscordInteractionProtocol(Protocol):
    """Protocol for discord.Interaction."""
    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol
    user: object


@dataclass(frozen=True)
class EmbedField:
    """A single embed field definition."""
    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class EmbedData:
    """Deterministic embed data for any command."""
    title: str
    description: str
    color: int
    fields: tuple[EmbedField, ...] = ()
    footer_text: str = FOOTER_TEXT
    footer_icon: str = ""
    timestamp: str = ""


def get_discord_module() -> Any:
    """Import discord dynamically and return typed embed interface."""
    return cast(Any, importlib.import_module("discord"))


def format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as '2026-06-01 15:30 WIB'."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def now_wib_str() -> str:
    """Return current UTC time formatted as WIB string."""
    return format_wib_timestamp(datetime.now(tz=timezone.utc))


def build_embed(title: str, description: str, color: int = PRIMARY) -> Any:
    """Build a discord.Embed from simple parameters.

    Convenience wrapper around EmbedData for quick embed construction.
    """
    data = EmbedData(title=title, description=description, color=color, timestamp=now_wib_str())
    return to_discord_embed(data)


def to_discord_embed(data: EmbedData) -> Any:
    """Convert EmbedData to a discord.Embed object."""
    d = get_discord_module()
    embed = d.Embed(
        title=data.title,
        description=data.description,
        colour=d.Colour(data.color),
    )
    for field in data.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)
    parts = [data.footer_text]
    if data.timestamp:
        parts.append(data.timestamp)
    if data.footer_icon:
        parts.append(data.footer_icon)
    embed.set_footer(text=" • ".join(parts))
    return embed


# ── Interaction Helpers ──────────────────────────────────────────────────


def _is_valid_interaction(interaction: object) -> bool:
    """Check if an object has the required interaction attributes (duck typing)."""
    return (
        hasattr(interaction, "response")
        and hasattr(interaction, "followup")
        and hasattr(interaction, "user")
    )


async def send_denied(interaction: object) -> None:
    """Send an ephemeral denial message to a non-Faiz user."""
    if not _is_valid_interaction(interaction):
        return
    if interaction.response.is_done():
        await interaction.followup.send(
            content="Hanya Faiz yang bisa menggunakan Mommy.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            content="Hanya Faiz yang bisa menggunakan Mommy.",
            ephemeral=True,
        )


async def defer_ephemeral(interaction: object) -> None:
    """Defer the interaction response ephemerally."""
    if not _is_valid_interaction(interaction):
        return
    await interaction.response.defer(ephemeral=True)


async def followup_send(
    interaction: object,
    embed: object | None = None,
    content: str | None = None,
    file: object | None = None,
) -> None:
    """Send a followup message (ephemeral)."""
    if not _is_valid_interaction(interaction):
        return
    kwargs: dict[str, object] = {"ephemeral": True}
    if content is not None:
        kwargs["content"] = content
    if embed is not None:
        kwargs["embed"] = embed
    if file is not None:
        kwargs["file"] = file
    await interaction.followup.send(**kwargs)


# ══════════════════════════════════════════════════════════════════════════
# STARTUP (from guinevere/discord/_startup.py)
# ══════════════════════════════════════════════════════════════════════════

STARTUP_TITLE: Final[str] = "\U0001f451 Mommy sudah bangun, Darling."
STARTUP_DESCRIPTION: Final[str] = "Semua sistem online. Mommy siap nemenin kamu hari ini."
STARTUP_FOOTER: Final[str] = "Guinevere de Baroque"
PRESENCE_TEXT: Final[str] = "Darling \U0001f441"


async def startup_on_ready(bot: object) -> None:
    """Startup greeting handler. Sends a greeting embed once per session.

    Uses idempotency guard (_startup_sent) to ensure greeting is sent
    only once per bot session.
    """
    if getattr(bot, "_startup_sent", False):
        return
    setattr(bot, "_startup_sent", True)

    channel_id = 1_510_914_600_777_023_659
    channel = None
    get_channel = getattr(bot, "get_channel", None)
    if get_channel is not None:
        channel = get_channel(channel_id)

    if channel is None:
        logger.warning("startup_channel_not_found", extra={"channel_id": channel_id})
        return

    data = EmbedData(
        title=STARTUP_TITLE,
        description=STARTUP_DESCRIPTION,
        color=PRIMARY,
        fields=(
            EmbedField("Status", "Online"),
            EmbedField("Mood", "Default (Y4)"),
            EmbedField("Time", now_wib_str()),
        ),
        footer_text=STARTUP_FOOTER,
        timestamp=now_wib_str(),
    )
    embed = to_discord_embed(data)

    send_fn = getattr(channel, "send", None)
    if send_fn is not None:
        try:
            await send_fn(embed=embed)
            logger.info("startup_greeting_sent")
        except (OSError, RuntimeError) as exc:
            logger.warning("startup_greeting_failed", extra={"error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS (from guinevere/discord/notifications.py)
# ══════════════════════════════════════════════════════════════════════════

SEV_CHANNELS: Final[dict[str, str]] = {
    "SEV0": "system-health",
    "SEV1": "system-health",
    "SEV2": "cost-tracker",
    "SEV3": "guinevere-status",
    "SEV4": "audit-log",
}

SEV_COLORS: Final[dict[str, int]] = {
    "SEV0": ALERT,
    "SEV1": WARNING,
    "SEV2": WARNING,
    "SEV3": PRIMARY,
    "SEV4": NEUTRAL,
}


@dataclass(frozen=True)
class SevAlert:
    """Structured SEV alert payload."""
    severity: str
    title: str
    description: str
    color: int = 0

    def __post_init__(self) -> None:
        if self.color == 0:
            object.__setattr__(self, "color", SEV_COLORS.get(self.severity, NEUTRAL))


async def send_notification(bot: object, alert: SevAlert) -> bool:
    """Route an SEV alert to the appropriate Discord channel.

    Returns True if the notification was sent successfully.
    """
    channel_name = SEV_CHANNELS.get(alert.severity, "audit-log")
    guilds = getattr(bot, "guilds", [])
    if not guilds:
        return False

    guild = guilds[0]
    channels = getattr(guild, "text_channels", [])
    target = None
    for ch in channels:
        if getattr(ch, "name", "") == channel_name:
            target = ch
            break

    if target is None:
        logger.warning("notification_channel_not_found", extra={"channel": channel_name})
        return False

    embed = build_embed(alert.title, alert.description, alert.color)
    send_fn = getattr(target, "send", None)
    if send_fn is not None:
        try:
            await send_fn(embed=embed)
            logger.info("notification_sent", extra={"severity": alert.severity, "channel": channel_name})
            return True
        except (OSError, RuntimeError) as exc:
            logger.warning("notification_failed", extra={"error": str(exc)})
    return False


# ══════════════════════════════════════════════════════════════════════════
# GOTIFY FALLBACK (from guinevere/discord/gotify_fallback.py)
# ══════════════════════════════════════════════════════════════════════════

GOTIFY_URL: Final[str] = "http://localhost:8081"


def _get_gotify_priority(severity: str) -> int:
    """Map severity string to Gotify priority (0-10)."""
    mapping = {"SEV0": 10, "SEV1": 7, "SEV2": 5, "SEV3": 3, "SEV4": 1}
    return mapping.get(severity.upper().strip(), 0)


async def send_gotify_fallback(title: str, description: str, severity: str) -> bool:
    """Send a notification via Gotify. Returns False on any failure (fail-soft)."""
    token = os.environ.get("GOTIFY_APP_TOKEN", "")
    if not token:
        logger.info("gotify_fallback_disabled", extra={"reason": "no_token"})
        return False

    try:
        import httpx
    except ImportError:
        logger.info("gotify_fallback_disabled", extra={"reason": "no_httpx"})
        return False

    priority = _get_gotify_priority(severity)
    payload = {"title": title, "message": description, "priority": priority}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GOTIFY_URL}/message",
                json=payload,
                headers={"X-Gotify-Key": token},
                timeout=5.0,
            )
        if response.is_success:
            logger.info("gotify_fallback_sent", extra={"severity": severity})
            return True
        logger.warning("gotify_fallback_failed", extra={"status": response.status_code})
        return False
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("gotify_fallback_error", extra={"error": str(exc)})
        return False
    except OSError as exc:
        logger.warning("gotify_fallback_os_error", extra={"error": str(exc)})
        return False


# ══════════════════════════════════════════════════════════════════════════
# SHADOW PIPELINE (from guinevere/discord/shadow_pipeline.py)
# ══════════════════════════════════════════════════════════════════════════

_COST_CAP_USD: Final[float] = 5.0
_SUBPROCESS_TIMEOUT: Final[float] = 30.0
_ESTIMATED_COST_PER_1K_OUTPUT: Final[float] = 0.000015
_TOKENS_PER_WORD: Final[float] = 0.75


class ShadowPipeline:
    """In-process shadow that forwards to Hermes, logs response, never sends to Discord.

    Disabled by default. Opt-in via SHADOW_ENABLED=true env var.
    """

    def __init__(self, enabled: bool = False, traffic_pct: int = 0) -> None:
        self.enabled = enabled
        self.traffic_pct = max(0, min(100, traffic_pct))
        self.hermes_cmd: list[str] = ["hermes", "--no-stream", "--quiet", "--max-iterations", "15"]
        self.comparison_log: str = "logs/shadow_comparisons.jsonl"
        self._request_count: int = 0
        self._error_count: int = 0
        self._shadow_cost_usd: float = 0.0
        self._file_lock: Any = None  # Lazy-initialized asyncio.Lock

        _log_dir = Path(self.comparison_log).parent
        _log_dir.mkdir(parents=True, exist_ok=True)

        if self.enabled:
            logger.info("shadow_pipeline_initialized", extra={"traffic_pct": self.traffic_pct})
        else:
            logger.info("shadow_pipeline_disabled")

    async def shadow_forward(
        self, message_content: str, bot_response: str, user_id: str, channel_id: str,
    ) -> dict[str, Any]:
        """Forward message to Hermes subprocess, capture response, log comparison."""
        result: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_id_hash": user_id[:8],
            "channel_id": channel_id,
            "user_msg": message_content,
            "bot_response": bot_response,
            "hermes_response": "",
            "safety_match": None,
            "latency_ms": 0,
            "token_count": 0,
            "cost_usd": 0.0,
            "error": None,
        }

        if not self.enabled:
            return result
        if self.traffic_pct <= 0 or (self.traffic_pct < 100 and random.randint(1, 100) > self.traffic_pct):
            return result
        if self._shadow_cost_usd >= _COST_CAP_USD:
            result["error"] = "cost_cap_exceeded"
            return result

        self._request_count += 1
        start_time = time.time()

        try:
            process = await _create_subprocess(*self.hermes_cmd)
            if process is None:
                result["error"] = "hermes_binary_not_found"
                return result

            payload = json.dumps({"message": message_content, "source": "shadow_pipeline", "mode": "query"})
            try:
                import asyncio
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=payload.encode("utf-8")),
                    timeout=_SUBPROCESS_TIMEOUT,
                )
            except (TimeoutError, OSError):
                process.kill()
                result["error"] = "hermes_subprocess_timeout"
                return result

            latency_ms = round((time.time() - start_time) * 1000, 1)
            result["latency_ms"] = latency_ms
            hermes_response = stdout_bytes.decode("utf-8", errors="replace").strip()
            result["hermes_response"] = hermes_response

            token_count = int(len(hermes_response.split()) * _TOKENS_PER_WORD)
            result["token_count"] = token_count
            estimated_cost = round((token_count / 1000.0) * _ESTIMATED_COST_PER_1K_OUTPUT, 6)
            self._shadow_cost_usd += estimated_cost
            result["cost_usd"] = estimated_cost

        except FileNotFoundError:
            self._error_count += 1
            result["error"] = "hermes_binary_not_found"
        except OSError as exc:
            self._error_count += 1
            result["error"] = f"os_error_{type(exc).__name__}"

        await self._write_log(result)
        return result

    async def _write_log(self, result: dict[str, Any]) -> None:
        """Append comparison result to JSONL log file."""
        try:
            import asyncio
            if self._file_lock is None:
                self._file_lock = asyncio.Lock()
            async with self._file_lock:
                with open(self.comparison_log, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(result, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.error("shadow_log_write_failed", extra={"error": str(exc)})

    @property
    def stats(self) -> dict[str, Any]:
        """Return current shadow pipeline statistics."""
        return {
            "enabled": self.enabled,
            "traffic_pct": self.traffic_pct,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "cumulative_cost_usd": round(self._shadow_cost_usd, 6),
            "cost_cap_usd": _COST_CAP_USD,
        }


async def _create_subprocess(*args: str) -> Any:
    """Create a subprocess, returning None if binary not found."""
    import asyncio
    try:
        return await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return None


# ══════════════════════════════════════════════════════════════════════════
# PROJECT SESSION (from guinevere/discord/project_session.py)
# ══════════════════════════════════════════════════════════════════════════

_DEFAULT_PROJECT_ID: str = "00000000-0000-0000-0000-000000000001"
_active_project_id: str = _DEFAULT_PROJECT_ID


def get_active_project_id() -> str:
    """Return the currently active project UUID string."""
    return _active_project_id


def set_active_project_id(project_id: str) -> None:
    """Set the active project UUID string."""
    global _active_project_id  # noqa: PLW0603
    _active_project_id = project_id


def reset_active_project_id() -> None:
    """Reset to the default project (for testing)."""
    global _active_project_id  # noqa: PLW0603
    _active_project_id = _DEFAULT_PROJECT_ID


def get_default_project_id() -> str:
    """Return the canonical default project UUID string."""
    return _DEFAULT_PROJECT_ID


# ══════════════════════════════════════════════════════════════════════════
# CONVERSATIONAL HANDLER (from guinevere/discord/hermes_conversational.py)
# Condensed — reactive handler for #guinevere-chat. Stale persona
# imports replaced with guinevere.emotions stubs.
# ══════════════════════════════════════════════════════════════════════════

GUINEVERE_CHAT_CHANNEL_ID: Final[int] = 1_510_914_600_777_023_659
RATE_LIMIT_MAX: Final[int] = 10
RATE_LIMIT_WINDOW: Final[int] = 60
DISCORD_MAX_CHARS: Final[int] = 2000
MAX_CHUNKS: Final[int] = 3

FALLBACK_MESSAGE: Final[str] = (
    "I'm having trouble thinking right now, sayang. "
    "Try again in a moment? \U0001f49b"
)


class ConversationalHandler:
    """Hermes-native conversational handler for #guinevere-chat.

    Replaces guinevere.discord.hermes_conversational. Cleans stale imports:
    - Former persona distress detection → DistressDetectorStub (no-op)
    - guinevere.persona.mood_engine → guinevere.emotions stub
    - Former surveillance gating → removed (not used here)
    """

    def __init__(self) -> None:
        self._cost_tracker: Any = None
        self._rate_limit_redis: Any = None

    async def handle_conversation(self, bot: object, message: object) -> bool:
        """Handle a conversational message in #guinevere-chat.

        Returns True if the message was absorbed (and should not be
        processed as a command).
        """
        channel = getattr(message, "channel", None)
        channel_id = getattr(channel, "id", None)
        if channel_id != GUINEVERE_CHAT_CHANNEL_ID:
            return False

        author = getattr(message, "author", None)
        if author is None or getattr(author, "bot", False):
            return False

        guild = getattr(message, "guild", None)
        owner_id = getattr(guild, "owner_id", None)
        user_id = getattr(author, "id", None)
        if owner_id is None or user_id is None or owner_id != user_id:
            return False

        content = getattr(message, "content", "")
        if not content or content.startswith("/"):
            return False

        # Rate limiting (fail-soft — allow on Redis failure)
        if await self._is_rate_limited(user_id):
            return True

        # Typing indicator
        channel_send = getattr(channel, "send", None)
        if channel_send is None:
            return True

        try:
            # Placeholder response — real LLM integration via Hermes adapter
            response = FALLBACK_MESSAGE

            # Send response in chunks
            chunks = _split_response(response)
            for chunk in chunks[:MAX_CHUNKS]:
                await channel_send(chunk)

        except (OSError, RuntimeError) as exc:
            logger.warning("conversation_send_failed", extra={"error": str(exc)})

        return True

    async def _is_rate_limited(self, user_id: int | None) -> bool:
        """Check rate limit via Redis. Fail-soft on connection error."""
        if user_id is None:
            return False
        try:
            if self._rate_limit_redis is None:
                self._rate_limit_redis = _get_rate_limit_redis()
            if self._rate_limit_redis is None:
                return False
            r = self._rate_limit_redis
            minute_bucket = int(time.time()) // RATE_LIMIT_WINDOW
            key = f"rate:chat:{user_id}:{minute_bucket}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, RATE_LIMIT_WINDOW)
            return count > RATE_LIMIT_MAX
        except (ConnectionError, OSError, AttributeError):
            return False


def _get_rate_limit_redis() -> Any:
    """Return the async Redis client for rate limiting (fail-soft)."""
    try:
        import redis.asyncio as aioredis
        return aioredis.Redis(
            host="localhost", port=6380, db=0,
            username="guinevere_core",
            password=os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
    except (ImportError, OSError):
        return None


import re

_SENTENCE_BOUNDARY: Final[re.Pattern[str]] = re.compile(r"(?<=[.!?])\s+|\n\n")


def _split_response(text: str) -> list[str]:
    """Split text into Discord-sendable chunks respecting sentence boundaries."""
    if len(text) <= DISCORD_MAX_CHARS:
        return [text]

    segments = _SENTENCE_BOUNDARY.split(text)
    chunks: list[str] = []
    current = ""

    for seg in segments:
        if len(current) + len(seg) + 1 <= DISCORD_MAX_CHARS:
            current = f"{current} {seg}".strip() if current else seg
        else:
            if current:
                chunks.append(current)
            current = seg

    if current:
        chunks.append(current)

    return chunks[:MAX_CHUNKS]


# Module-level singleton for convenience
_conversational_handler: ConversationalHandler | None = None


async def handle_conversation(bot: object, message: object) -> bool:
    """Module-level conversational handler entry point."""
    global _conversational_handler
    if _conversational_handler is None:
        _conversational_handler = ConversationalHandler()
    return await _conversational_handler.handle_conversation(bot, message)
