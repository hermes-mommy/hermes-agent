"""Discord slash commands for P22 Life Integration Hub.

Six command callbacks that proxy to the guinevere-core FastAPI on
``127.0.0.1:8000`` via the canonical ``/api/v1/integrations/*`` endpoint
family.  The Discord bot process cannot reach ``app.state.p22_router``
directly because the bot is a separate process; it speaks HTTP through
the documented endpoints (B1) and reads ``X-Guinevere-API-Key`` from the
environment (matching ``cmd_evidence.py`` / ``cmd_loops.py`` pattern).

Commands:

* ``/integration-status``      — GET  ``/api/v1/integrations/status``
* ``/integration-capabilities`` — GET  ``/api/v1/integrations/capabilities``
* ``/integration-test``       — POST ``/api/v1/integrations/test``
* ``/integration-missing``    — GET  ``/api/v1/integrations/missing``
* ``/integration-consent``    — GET/POST ``/api/v1/integrations/consent``
* ``/integration-dry-run``    — POST ``/api/v1/integrations/dry-run``

All responses are ephemeral, Faiz-only, and read the API key from
``$GUINEVERE_API_KEY`` (never hardcoded).  Embed colors are sourced from
``src.discord.colors`` (SUCCESS/WARNING/ALERT/INFO_BLUE).
"""

from __future__ import annotations

import os
from typing import Any, Final

import httpx
import json
import structlog

from .colors import ALERT, INFO_BLUE, SUCCESS, WARNING
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

logger = structlog.get_logger(__name__)

_TITLE: Final[str] = "\U0001f517 P22 Integrations"
"""Default title for integration command embeds (chain emoji)."""

_FOOTER_ICON: Final[str] = "\U0001f517 Integrations"
"""Right-side footer icon label."""

_API_BASE_URL: Final[str] = "http://127.0.0.1:8000"
"""guinevere-core FastAPI base URL on the VPS."""

_INTEGRATIONS_PREFIX: Final[str] = "/api/v1/integrations"
"""Canonical integrations endpoint prefix."""

_TIMEOUT: Final[float] = 15.0
"""HTTP request timeout in seconds."""


# ── Health→Color Mapping ────────────────────────────────────────────────────


_STATUS_TO_COLOR: Final[dict[str, int]] = {
    "HEALTHY": SUCCESS,
    "OK": SUCCESS,
    "CONFIG_MISSING": WARNING,
    "DEGRADED": ALERT,
    "HARD_STOP": ALERT,
}
"""Lower-case priority of status strings → embed color."""


def _color_for_status(status: str) -> int:
    """Map an adapter status string to an embed color (defaults to INFO_BLUE)."""
    return _STATUS_TO_COLOR.get(status.upper(), INFO_BLUE)


# ── HTTP Helper ─────────────────────────────────────────────────────────────


async def _call_integrations_api(
    method: str,
    path: str,
    json_body: dict[str, object] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Call the integrations endpoint family on guinevere-core.

    Args:
        method: ``"GET"`` or ``"POST"``.
        path: Path under ``/api/v1/integrations`` (e.g. ``"/status"``).
        json_body: Optional JSON body for POST requests.
        params: Optional query string parameters.

    Returns:
        Parsed JSON dict on success, ``None`` on any failure (network,
        status code, malformed JSON).  Failures are logged but never
        raised so the Discord callback can always render an embed.
    """
    url = f"{_API_BASE_URL}{_INTEGRATIONS_PREFIX}{path}"
    api_key = os.environ.get("GUINEVERE_API_KEY", "")
    headers = {"X-Guinevere-API-Key": api_key}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=url,
                json=json_body,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "integrations_api_http_error",
            path=path,
            status=exc.response.status_code,
        )
        return None
    except httpx.RequestError as exc:
        logger.warning(
            "integrations_api_request_failed",
            path=path,
            error=str(exc),
        )
        return None
    except json.JSONDecodeError as exc:
        logger.exception(
            "integrations_api_unexpected_error",
            path=path,
            error=str(exc),
        )
        return None
    except (KeyError, ValueError) as exc:
        logger.exception(
            "integrations_api_unexpected_error",
            path=path,
            error=str(exc),
        )
        return None


async def _send_unreachable_embed(interaction: Any) -> None:
    """Send a WARNING embed showing that guinevere-core is unreachable."""
    ts = now_wib_str()
    data = EmbedData(
        title=_TITLE,
        description=(
            "⚠️ guinevere-core tidak bisa dihubungi. "
            "Apakah service berjalan di ``127.0.0.1:8000``?"
        ),
        color=WARNING,
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


async def _send_p22_inactive_embed(interaction: Any) -> None:
    """Send an INFO_BLUE embed showing P22 is not currently active."""
    ts = now_wib_str()
    data = EmbedData(
        title=_TITLE,
        description=(
            "P22 Life Integration Hub belum diaktifkan di guinevere-core. "
            "Jalankan startup untuk memuat registry."
        ),
        color=INFO_BLUE,
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


# ── /integration-status ─────────────────────────────────────────────────────


async def status_callback(interaction: Any) -> None:
    """Handle ``/integration-status`` — show per-adapter rows + tier.

    Calls ``GET /api/v1/integrations/status``.  Color is:
    * SUCCESS if every adapter is HEALTHY,
    * WARNING on any mix,
    * ALERT if any adapter is DEGRADED or HARD_STOP.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    result = await _call_integrations_api("GET", "/status")
    ts = now_wib_str()

    if result is None:
        await _send_unreachable_embed(interaction)
        return

    if result.get("p22_active") is False:
        await _send_p22_inactive_embed(interaction)
        return

    adapters: list[dict[str, Any]] = list(result.get("adapters", []))
    if not adapters:
        data = EmbedData(
            title=_TITLE,
            description="Tidak ada integration adapter yang terdaftar.",
            color=INFO_BLUE,
            footer_icon=_FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)
        return

    statuses: list[str] = [str(a.get("status", "")).upper() for a in adapters]
    fields: list[EmbedField] = []
    for adapter in adapters[:13]:  # Discord embed field cap
        iid = str(adapter.get("integration_id", "?"))
        status = str(adapter.get("status", "unknown"))
        tier = str(adapter.get("tier", "L1"))
        fields.append(
            EmbedField(
                name=f"`{iid}`",
                value=f"Status: {status}\nTier: {tier}",
                inline=True,
            )
        )

    if any(s in ("DEGRADED", "HARD_STOP") for s in statuses):
        color = ALERT
    elif all(s == "HEALTHY" for s in statuses):
        color = SUCCESS
    else:
        color = WARNING

    data = EmbedData(
        title=_TITLE,
        description=f"{len(adapters)} adapter(s) terdaftar.",
        color=color,
        fields=tuple(fields),
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


# ── /integration-capabilities ───────────────────────────────────────────────


async def capabilities_callback(interaction: Any) -> None:
    """Handle ``/integration-capabilities`` — show 13×L1-L4 matrix.

    Calls ``GET /api/v1/integrations/capabilities`` and renders
    each adapter's declared capabilities.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    result = await _call_integrations_api("GET", "/capabilities")
    ts = now_wib_str()

    if result is None:
        await _send_unreachable_embed(interaction)
        return

    if result.get("p22_active") is False:
        await _send_p22_inactive_embed(interaction)
        return

    adapters: list[dict[str, Any]] = list(result.get("adapters", []))
    if not adapters:
        data = EmbedData(
            title=_TITLE,
            description="Tidak ada integration capabilities terdaftar.",
            color=INFO_BLUE,
            footer_icon=_FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)
        return

    fields: list[EmbedField] = []
    for adapter in adapters[:13]:  # 13-adapter cap
        iid = str(adapter.get("integration_id", "?"))
        caps: list[str] = [str(c) for c in adapter.get("capabilities", [])]
        tier = str(adapter.get("default_tier", "L1"))
        caps_line = ", ".join(caps) if caps else "(none)"
        fields.append(
            EmbedField(
                name=f"`{iid}`",
                value=f"Tier: {tier}\nCaps: {caps_line}",
                inline=True,
            )
        )

    data = EmbedData(
        title=_TITLE,
        description=f"{len(adapters)} adapter dengan capability matrix.",
        color=INFO_BLUE,
        fields=tuple(fields),
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


# ── /integration-test ───────────────────────────────────────────────────────


async def test_callback(interaction: Any) -> None:
    """Handle ``/integration-test adapter:str`` — POST /test.

    Required option:
        ``adapter``: integration_id to health-check.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    adapter = get_option_value(interaction, "adapter")
    ts = now_wib_str()

    if not adapter or not adapter.strip():
        await followup_send(
            interaction,
            content="⚠️ Option ``adapter`` diperlukan.",
        )
        return

    body: dict[str, object] = {"integration_id": adapter}
    result = await _call_integrations_api("POST", "/test", json_body=body)

    if result is None:
        await _send_unreachable_embed(interaction)
        return

    if result.get("p22_active") is False:
        await _send_p22_inactive_embed(interaction)
        return

    health = str(result.get("health", "unknown"))
    status = str(result.get("status", "unknown"))
    duration_ms = result.get("duration_ms", 0)
    color = _color_for_status(status)
    fields: tuple[EmbedField, ...] = (
        EmbedField(name="Integration", value=f"`{adapter}`", inline=True),
        EmbedField(name="Health", value=health, inline=True),
        EmbedField(name="Status", value=status, inline=True),
        EmbedField(name="Duration", value=f"{duration_ms} ms", inline=True),
    )
    data = EmbedData(
        title=_TITLE,
        description=f"Health check untuk ``{adapter}`` selesai.",
        color=color,
        fields=fields,
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


# ── /integration-missing ─────────────────────────────────────────────────────


async def missing_callback(interaction: Any) -> None:
    """Handle ``/integration-missing`` — show CONFIG_MISSING adapters.

    Calls ``GET /api/v1/integrations/missing`` and lists each adapter
    missing required setup along with the *credential NAMES only*
    (never values) and a short onboarding step.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    result = await _call_integrations_api("GET", "/missing")
    ts = now_wib_str()

    if result is None:
        await _send_unreachable_embed(interaction)
        return

    if result.get("p22_active") is False:
        await _send_p22_inactive_embed(interaction)
        return

    missing: list[dict[str, Any]] = list(result.get("missing", []))
    if not missing:
        data = EmbedData(
            title=_TITLE,
            description="✅ Semua integration adapter sudah lengkap setup-nya.",
            color=SUCCESS,
            footer_icon=_FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)
        return

    fields: list[EmbedField] = []
    for entry in missing[:13]:  # 13-adapter cap
        iid = str(entry.get("integration_id", "?"))
        creds: list[str] = [str(c) for c in entry.get("missing_credentials", [])]
        step = str(entry.get("onboarding_step", "(see docs)"))
        creds_line = ", ".join(creds) if creds else "(only config)"
        fields.append(
            EmbedField(
                name=f"⚠ `{iid}`",
                value=f"Needed: {creds_line}\nStep: {step}",
                inline=False,
            )
        )

    data = EmbedData(
        title=_TITLE,
        description=f"{len(missing)} adapter(s) butuh setup.",
        color=WARNING,
        fields=tuple(fields),
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


# ── /integration-consent ────────────────────────────────────────────────────


_CONSENT_ACTIONS: Final[tuple[str, ...]] = ("list", "grant", "revoke")
"""Accepted values for the ``consent_action`` option."""


async def integration_consent_callback(interaction: Any) -> None:
    """Handle ``/integration-consent consent_action:str [scope:str]``.

    Options:
        ``consent_action``: one of ``list``, ``grant``, ``revoke``.
        ``scope``: required for ``grant`` and ``revoke``.

    ``list``     → GET  ``/api/v1/integrations/consent``
    ``grant``    → POST ``/api/v1/integrations/consent``
    ``revoke``   → POST ``/api/v1/integrations/consent``
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    consent_action = get_option_value(interaction, "consent_action")
    scope = get_option_value(interaction, "scope")

    if not consent_action:
        consent_action = "list"

    if consent_action not in _CONSENT_ACTIONS:
        allowed = ", ".join(f"``{a}``" for a in _CONSENT_ACTIONS)
        await followup_send(
            interaction,
            content=(
                f"⚠️ ``consent_action`` harus salah satu: {allowed}."
            ),
        )
        return

    if consent_action in ("grant", "revoke") and not scope:
        await followup_send(
            interaction,
            content=(
                f"⚠️ ``scope`` diperlukan untuk ``{consent_action}``."
            ),
        )
        return

    await defer_ephemeral(interaction)
    ts = now_wib_str()

    if consent_action == "list":
        result = await _call_integrations_api("GET", "/consent")
    else:
        body: dict[str, object] = {
            "action": consent_action,
            "scope": scope,
        }
        result = await _call_integrations_api("POST", "/consent", json_body=body)

    if result is None:
        await _send_unreachable_embed(interaction)
        return

    if result.get("p22_active") is False:
        await _send_p22_inactive_embed(interaction)
        return

    ok = bool(result.get("ok", False))
    color = SUCCESS if ok else WARNING
    scopes: list[str] = [str(s) for s in result.get("scopes", [])]

    if consent_action == "list":
        description = "Daftar consent scopes saat ini."
        fields: list[EmbedField] = []
        if scopes:
            scope_lines = "\n".join(f"• {s}" for s in scopes)
            fields.append(
                EmbedField(
                    name="Scopes",
                    value=scope_lines,
                    inline=False,
                )
            )
        else:
            fields.append(
                EmbedField(
                    name="Scopes",
                    value="(tidak ada scope)",
                    inline=False,
                )
            )
    else:
        verb = "Granted" if consent_action == "grant" else "Revoked"
        description = f"{verb} scope ``{scope}``."
        fields = [
            EmbedField(
                name="Scope",
                value=f"``{scope}``",
                inline=True,
            ),
            EmbedField(
                name="Result",
                value="ok" if ok else "failed",
                inline=True,
            ),
        ]
        if "reason" in result:
            fields.append(
                EmbedField(
                    name="Reason",
                    value=str(result.get("reason", "")),
                    inline=False,
                )
            )

    data = EmbedData(
        title=_TITLE,
        description=description,
        color=color,
        fields=tuple(fields),
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


# ── /integration-dry-run ────────────────────────────────────────────────────


async def dry_run_callback(interaction: Any) -> None:
    """Handle ``/integration-dry-run adapter:str action:str``.

    Options:
        ``adapter``: integration_id.
        ``action``: action name (e.g. ``delete_invoice``).
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    adapter = get_option_value(interaction, "adapter")
    action = get_option_value(interaction, "action")
    ts = now_wib_str()

    if not adapter or not action:
        await followup_send(
            interaction,
            content="⚠️ Options ``adapter`` dan ``action`` keduanya diperlukan.",
        )
        return

    await defer_ephemeral(interaction)

    body: dict[str, object] = {
        "integration_id": adapter,
        "action": action,
        "kwargs": {},
    }
    result = await _call_integrations_api("POST", "/dry-run", json_body=body)

    if result is None:
        await _send_unreachable_embed(interaction)
        return

    if result.get("p22_active") is False:
        await _send_p22_inactive_embed(interaction)
        return

    tier = str(result.get("tier", "UNKNOWN"))
    consent_scope = str(result.get("consent_scope", ""))
    allowed = bool(result.get("allowed", False))
    reason = str(result.get("reason", ""))
    would_execute = bool(result.get("would_execute", False))

    color = SUCCESS if allowed else ALERT

    description = (
        "Dry-run lengkap: tidak ada efek samping. "
        f"would_execute = ``{would_execute}``"
    )
    fields: tuple[EmbedField, ...] = (
        EmbedField(name="Integration", value=f"`{adapter}`", inline=True),
        EmbedField(name="Action", value=f"`{action}`", inline=True),
        EmbedField(name="Tier", value=tier, inline=True),
        EmbedField(name="Consent Scope", value=f"`{consent_scope}`", inline=True),
        EmbedField(name="Allowed", value="yes" if allowed else "no", inline=True),
        EmbedField(name="Reason", value=reason or "(none)", inline=False),
    )

    data = EmbedData(
        title=_TITLE,
        description=description,
        color=color,
        fields=fields,
        footer_icon=_FOOTER_ICON,
        timestamp=ts,
    )
    embed = to_discord_embed(data)
    await followup_send(interaction, embed=embed)


__all__ = [
    "status_callback",
    "capabilities_callback",
    "test_callback",
    "missing_callback",
    "integration_consent_callback",
    "dry_run_callback",
]
