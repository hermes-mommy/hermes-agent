"""Discord /project and /projects commands for Guinevere (P19-007).

Project switching with HARD STOP guard, project list/create/archive/info.

Every switch writes an audit row via the ProjectRegistry audit writer.
If ``life_kernel:hard_stop`` is active in Redis, the switch is refused
with a neutral ack message.

Usage:
    /project <name>          — switch active project
    /projects list           — list all projects
    /projects create <name>  — create a new project (audited)
    /projects archive <name> — archive a project (audited)
    /projects info           — show current project info
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import redis
import structlog

from .colors import ALERT, INFO, NEUTRAL, PRIMARY, SUCCESS
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    get_option_value,
    now_wib_str,
    send_denied,
    to_discord_embed,
)
from .project_session import get_active_project_id, set_active_project_id

logger = structlog.get_logger()

TITLE: str = "\U0001f4c2 Project Manager"
FOOTER_ICON: str = "\U0001f4c1 Projects"

HARD_STOP_KEY: str = "life_kernel:hard_stop"
DASHBOARD_MESSAGE_ID_KEY: str = "life_kernel:dashboard_message_id"
DASHBOARD_TOP_N: int = 3


# ── Redis ───────────────────────────────────────────────────────────────────


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for hard-stop state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


def _is_hard_stop_active(r: redis.Redis) -> bool:
    """Check if the life_kernel HARD STOP flag is set in Redis."""
    value = r.get(HARD_STOP_KEY)
    return bool(value)


# ── Audit helper ────────────────────────────────────────────────────────────


async def _write_audit_event(
    registry: Any,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Write an audit event through the registry's audit writer."""
    if registry._audit_writer is not None:
        await registry._audit_writer.write_event(
            event_type=event_type,
            loop_id="projects",
            data=data,
        )


# ── Dashboard key helper ────────────────────────────────────────────────────


def dashboard_message_key(project_id: uuid.UUID) -> str:
    """Return the per-project dashboard message-id Redis key.

    Args:
        project_id: UUID of the project.

    Returns:
        The Redis key ``life_kernel:dashboard_message_id:{project_id}``.
    """
    return f"{DASHBOARD_MESSAGE_ID_KEY}:{project_id}"


async def enforce_dashboard_cap(
    r: redis.Redis,
    project_id: uuid.UUID,
    new_message_id: str,
) -> None:
    """Set the dashboard message id for a project and enforce top-N cap.

    If more than ``DASHBOARD_TOP_N`` per-project dashboard keys exist,
    the oldest (by TTL / insertion order) is evicted (LRU).

    Args:
        r: Redis client.
        project_id: The project whose dashboard is being updated.
        new_message_id: The Discord message id to store.
    """
    key = dashboard_message_key(project_id)
    r.set(key, new_message_id)

    pattern = f"{DASHBOARD_MESSAGE_ID_KEY}:*"
    all_keys = r.keys(pattern)
    if len(all_keys) > DASHBOARD_TOP_N:
        # Evict oldest keys to maintain cap (LRU: evict keys without recent TTL).
        sorted_keys = sorted(all_keys)
        excess = sorted_keys[: len(sorted_keys) - DASHBOARD_TOP_N]
        for evict_key in excess:
            r.delete(evict_key)
            logger.info("dashboard_key_evicted", key=evict_key)


# ── /project callback ───────────────────────────────────────────────────────


async def project_callback(interaction: Any) -> None:
    """Handle a ``/project <name>`` interaction (switch active project).

    Steps:
    1. Auth gate (Faiz only).
    2. Defer ephemeral.
    3. Check HARD STOP — refuse with neutral ack if active.
    4. Resolve target project from registry.
    5. Write ``project_switched`` audit row.
    6. Update active project session.
    7. Send confirmation embed.
    """
    from ._auth_guard import is_faiz_interaction
    from guinvere.projects.registry import InMemoryProjectStore, ProjectRegistry
    from guinvere.projects.exceptions import ProjectNotFoundError, InvalidProjectSlugError

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        name_raw = get_option_value(interaction, "name")
        ts = now_wib_str()

        # If no name given, show current project info
        if not name_raw:
            active_pid = get_active_project_id()
            fields = (
                EmbedField(name="Active Project", value=f"`{active_pid}`", inline=True),
            )
            data = EmbedData(
                title=TITLE,
                description="Gunakan `/project <name>` untuk switch project.",
                color=INFO,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            return

        # HARD STOP guard
        r = _get_redis_client()
        if _is_hard_stop_active(r):
            logger.warning("project_switch_blocked_hard_stop", target=name_raw)
            data = EmbedData(
                title=TITLE,
                description=(
                    "Project switch ditolak. HARD STOP sedang aktif — "
                    "semua perubahan project ditangguhkan."
                ),
                color=ALERT,
                fields=(
                    EmbedField(name="Requested", value=f"`{name_raw}`", inline=True),
                    EmbedField(name="Status", value="HARD STOP active", inline=True),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            return

        # Resolve target project
        store = InMemoryProjectStore()
        registry = ProjectRegistry(store=store)
        try:
            project = await registry.resolve(name_raw)
        except (ProjectNotFoundError, InvalidProjectSlugError):
            data = EmbedData(
                title=TITLE,
                description=f"Project ``{name_raw}`` tidak ditemukan.",
                color=ALERT,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            return

        # Build audit data
        from_project = get_active_project_id()
        to_project = str(project.project_id)
        user = getattr(interaction, "user", None)
        actor = str(getattr(user, "id", "unknown"))
        channel_obj = getattr(interaction, "channel", None)
        channel_id = str(getattr(channel_obj, "id", getattr(interaction, "channel_id", "unknown")))

        # Write audit row
        await _write_audit_event(
            registry,
            "project_switched",
            {
                "actor": actor,
                "from_project": from_project,
                "to_project": to_project,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel_id": channel_id,
            },
        )

        # Update session
        set_active_project_id(to_project)

        logger.info(
            "project_switched",
            actor=actor,
            from_project=from_project,
            to_project=to_project,
        )

        data = EmbedData(
            title=TITLE,
            description=f"Berhasil switch ke project ``{project.slug}``.",
            color=SUCCESS,
            fields=(
                EmbedField(name="Slug", value=f"`{project.slug}`", inline=True),
                EmbedField(name="Name", value=project.name, inline=True),
                EmbedField(name="Status", value=project.status, inline=True),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("project_callback_failed")
        await followup_send(
            interaction,
            content="⚠️ Project switch failed — try again later.",
        )


# ── /projects callback ──────────────────────────────────────────────────────


async def projects_callback(interaction: Any) -> None:
    """Handle ``/projects list|create|archive|info`` interactions.

    Dispatches to the appropriate handler based on the ``action`` option.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        action_raw = get_option_value(interaction, "action")
        action = action_raw if action_raw else "list"
        ts = now_wib_str()

        if action == "list":
            await _handle_projects_list(interaction, ts)
        elif action == "create":
            await _handle_projects_create(interaction, ts)
        elif action == "archive":
            await _handle_projects_archive(interaction, ts)
        elif action == "info":
            await _handle_projects_info(interaction, ts)
        else:
            data = EmbedData(
                title=TITLE,
                description="Action tidak dikenali. Gunakan: list, create, archive, info.",
                color=ALERT,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("projects_callback_failed")
        await followup_send(
            interaction,
            content="⚠️ Project manager is temporarily unavailable.",
        )


async def _handle_projects_list(interaction: Any, ts: str) -> None:
    """List all projects from the registry."""
    from guinvere.projects.registry import InMemoryProjectStore, ProjectRegistry

    store = InMemoryProjectStore()
    registry = ProjectRegistry(store=store)
    projects = await registry.list()

    if not projects:
        data = EmbedData(
            title=TITLE,
            description="Tidak ada project yang terdaftar.",
            color=NEUTRAL,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
    else:
        lines = []
        for p in sorted(projects, key=lambda x: x.slug):
            status_emoji = {"active": "✅", "paused": "⏸️", "archived": "\U0001f4e6"}.get(
                p.status, "❓"
            )
            lines.append(f"{status_emoji} **{p.slug}** — {p.name} (`{p.status}`)")
        fields = (
            EmbedField(
                name="\U0001f4cb Projects",
                value="\n".join(lines),
                inline=False,
            ),
        )
        data = EmbedData(
            title=TITLE,
            description=f"Ditemukan {len(projects)} project.",
            color=PRIMARY,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


async def _handle_projects_create(interaction: Any, ts: str) -> None:
    """Create a new project (audited)."""
    from guinvere.projects.registry import InMemoryProjectStore, ProjectRegistry
    from guinvere.projects.exceptions import ProjectAlreadyExistsError, InvalidProjectSlugError

    name = get_option_value(interaction, "name")
    if not name:
        await followup_send(
            interaction,
            content="⚠️ Parameter ``name`` diperlukan untuk create.",
        )
        return

    store = InMemoryProjectStore()
    registry = ProjectRegistry(store=store)

    user = getattr(interaction, "user", None)
    actor = str(getattr(user, "id", "unknown"))

    try:
        project = await registry.create(name, name=name)

        await _write_audit_event(
            registry,
            "project.created",
            {"project_id": str(project.project_id), "slug": name, "actor": actor},
        )

        data = EmbedData(
            title=TITLE,
            description=f"Project ``{name}`` berhasil dibuat.",
            color=SUCCESS,
            fields=(
                EmbedField(name="Slug", value=f"`{project.slug}`", inline=True),
                EmbedField(name="Name", value=project.name, inline=True),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except ProjectAlreadyExistsError:
        await followup_send(
            interaction,
            content=f"⚠️ Project ``{name}`` sudah ada.",
        )
    except InvalidProjectSlugError:
        await followup_send(
            interaction,
            content=f"⚠️ Slug ``{name}`` tidak valid. Gunakan lowercase alphanumeric.",
        )
    except Exception:
        logger.exception("project_create_failed", slug=name)
        await followup_send(
            interaction,
            content="⚠️ Gagal membuat project.",
        )


async def _handle_projects_archive(interaction: Any, ts: str) -> None:
    """Archive a project (audited)."""
    from guinvere.projects.registry import InMemoryProjectStore, ProjectRegistry
    from guinvere.projects.exceptions import (
        ProjectNotFoundError,
        ProjectArchivedError,
        InvalidProjectSlugError,
    )

    name = get_option_value(interaction, "name")
    if not name:
        await followup_send(
            interaction,
            content="⚠️ Parameter ``name`` diperlukan untuk archive.",
        )
        return

    store = InMemoryProjectStore()
    registry = ProjectRegistry(store=store)

    user = getattr(interaction, "user", None)
    actor = str(getattr(user, "id", "unknown"))
    channel_obj = getattr(interaction, "channel", None)
    channel_id = str(getattr(channel_obj, "id", getattr(interaction, "channel_id", "unknown")))

    try:
        project = await registry.resolve(name)
        archived = await registry.archive(project.project_id)

        await _write_audit_event(
            registry,
            "project_archived",
            {
                "project_id": str(project.project_id),
                "slug": name,
                "actor": actor,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel_id": channel_id,
            },
        )

        data = EmbedData(
            title=TITLE,
            description=f"Project ``{name}`` berhasil di-archive.",
            color=SUCCESS,
            fields=(
                EmbedField(name="Slug", value=f"`{archived.slug}`", inline=True),
                EmbedField(name="Status", value="archived", inline=True),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except ProjectNotFoundError:
        await followup_send(
            interaction,
            content=f"⚠️ Project ``{name}`` tidak ditemukan.",
        )
    except ProjectArchivedError:
        await followup_send(
            interaction,
            content=f"⚠️ Project ``{name}`` sudah di-archive.",
        )
    except InvalidProjectSlugError:
        await followup_send(
            interaction,
            content=f"⚠️ Slug ``{name}`` tidak valid.",
        )
    except Exception:
        logger.exception("project_archive_failed", slug=name)
        await followup_send(
            interaction,
            content="⚠️ Gagal meng-archive project.",
        )


async def _handle_projects_info(interaction: Any, ts: str) -> None:
    """Show current active project info."""
    from guinvere.projects.registry import InMemoryProjectStore, ProjectRegistry

    active_pid = get_active_project_id()

    store = InMemoryProjectStore()
    registry = ProjectRegistry(store=store)

    try:
        project = await registry.get(uuid.UUID(active_pid))

        data = EmbedData(
            title=TITLE,
            description="Info project yang sedang aktif.",
            color=PRIMARY,
            fields=(
                EmbedField(name="Slug", value=f"`{project.slug}`", inline=True),
                EmbedField(name="Name", value=project.name, inline=True),
                EmbedField(name="Status", value=project.status, inline=True),
                EmbedField(name="Scope", value=project.project_scope, inline=True),
                EmbedField(name="ID", value=f"`{project.project_id}`", inline=False),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("project_info_failed", project_id=active_pid)
        data = EmbedData(
            title=TITLE,
            description=f"Active project: ``{active_pid}``",
            color=NEUTRAL,
            fields=(
                EmbedField(name="Project ID", value=f"`{active_pid}`", inline=True),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)


__all__ = [
    "project_callback",
    "projects_callback",
    "dashboard_message_key",
    "enforce_dashboard_cap",
    "DASHBOARD_TOP_N",
    "DASHBOARD_MESSAGE_ID_KEY",
]
