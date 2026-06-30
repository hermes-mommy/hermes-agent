"""Discord slash commands for Gmail integration.

Commands that call the Gmail service API via HTTP:

- ``/email-digest [range=12h]`` — fetch email digest
- ``/email-consent <action>`` — grant, revoke, or check email consent
- ``/email-reauth`` — force OAuth token refresh
- ``/email-search <query>`` — full-text search stored email episodes

All commands are Faiz-only.  The Gmail service runs as a separate systemd
process and exposes these operations on ``127.0.0.1:8096``.
"""

from __future__ import annotations

from typing import Any, Final

import httpx
import structlog

from .colors import INFO_BLUE, SUCCESS, WARNING
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger(__name__)

_GMAIL_API_BASE: Final[str] = "http://127.0.0.1:8096"
"""Base URL for the Gmail service HTTP API (same host, port 8096)."""

_TIMEOUT: Final[float] = 15.0
"""HTTP request timeout in seconds."""

# ── Helpers ──────────────────────────────────────────────────────────────────

async def _call_gmail_api(
    method: str,
    path: str,
    json_body: dict[str, object] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Call the Gmail service HTTP API and return the JSON response.

    Args:
        method: ``"GET"`` or ``"POST"``.
        path: API path, e.g. ``"/api/email-digest"``.
        json_body: Optional JSON body for POST requests.
        params: Optional query string parameters.

    Returns:
        The parsed JSON response dict, or ``None`` on failure.
    """
    url = f"{_GMAIL_API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=url,
                json=json_body,
                params=params,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "gmail_api_http_error",
            path=path,
            status=exc.response.status_code,
            body=exc.response.text[:500],
        )
        return None
    except httpx.RequestError as exc:
        logger.warning(
            "gmail_api_request_failed",
            path=path,
            error=str(exc),
        )
        return None
    except Exception as exc:
        logger.exception(
            "gmail_api_unexpected_error",
            path=path,
            error=str(exc),
        )
        return None

# ── /email-digest ────────────────────────────────────────────────────────────

async def email_digest_callback(interaction: Any) -> None:
    """Handle ``/email-digest [range=12h]`` — fetch email digest.

    Args:
        interaction: The Discord interaction object.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    # Extract the optional range option
    range_value: str = "12h"
    data = getattr(interaction, "data", None)
    if data is not None:
        options: list[dict[str, object]] = (
            data.get("options", []) if isinstance(data, dict) else []
        )
        for opt in options:
            if opt.get("name") == "range":
                range_value = str(opt.get("value", "12h"))

    await defer_ephemeral(interaction)

    result = await _call_gmail_api(
        "GET", "/api/email-digest",
        params={"range": range_value},
    )

    if result is None or not result.get("ok"):
        await followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Gagal mengambil email digest. "
                "Apakah Gmail service sedang berjalan?"
            ),
        )
        return

    digest_text: str = result.get("digest", "(no digest)")

    ts = now_wib_str()
    fields: tuple[EmbedField, ...] = (
        EmbedField(name="Range", value=range_value, inline=True),
    )
    data_obj = EmbedData(
        title="\U0001f4ec Email Digest",
        description=digest_text[:1900],
        color=INFO_BLUE,
        fields=fields,
        timestamp=ts,
    )
    embed = to_discord_embed(data_obj)
    await followup_send(interaction, embed=embed)

# ── /email-consent ──────────────────────────────────────────────────────────

async def email_consent_callback(interaction: Any) -> None:
    """Handle ``/email-consent <action>`` — manage email consent.

    Args:
        interaction: The Discord interaction object.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    # Extract the required action option
    action: str = ""
    data = getattr(interaction, "data", None)
    if data is not None:
        options: list[dict[str, object]] = (
            data.get("options", []) if isinstance(data, dict) else []
        )
        for opt in options:
            if opt.get("name") == "action":
                action = str(opt.get("value", ""))

    if action not in ("grant", "revoke", "status"):
        await followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Action harus salah satu dari: "
                "`grant`, `revoke`, atau `status`."
            ),
        )
        return

    await defer_ephemeral(interaction)

    result = await _call_gmail_api(
        "POST", "/api/email-consent",
        json_body={"action": action},
    )

    ts = now_wib_str()

    if result is None:
        await followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Gagal menghubungi Gmail service. "
                "Apakah service sedang berjalan?"
            ),
        )
        return

    status_text: str
    if action == "grant":
        status_text = (
            "\u2705 Email consent granted!"
            if result.get("ok")
            else "\u274c Gagal grant consent."
        )
    elif action == "revoke":
        status_text = (
            "\U0001f6d1 Email consent revoked!"
            if result.get("ok")
            else "\u274c Gagal revoke consent."
        )
    else:  # status
        allowed = result.get("allowed", False)
        status_text = (
            f"\U0001f7e2 Email consent active (allowed={allowed})"
            if allowed
            else f"\U0001f534 Email consent inactive (allowed={allowed})"
        )

    color = SUCCESS if result.get("ok") else WARNING
    fields: tuple[EmbedField, ...] = (
        EmbedField(name="Action", value=action, inline=True),
        EmbedField(name="Status", value=status_text, inline=False),
    )
    data_obj = EmbedData(
        title="\U0001f4ec Email Consent",
        description=status_text,
        color=color,
        fields=fields,
        timestamp=ts,
    )
    embed = to_discord_embed(data_obj)
    await followup_send(interaction, embed=embed)

# ── /email-reauth ───────────────────────────────────────────────────────────

async def email_reauth_callback(interaction: Any) -> None:
    """Handle ``/email-reauth`` — force OAuth token refresh.

    Args:
        interaction: The Discord interaction object.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    result = await _call_gmail_api("POST", "/api/email-reauth")

    ts = now_wib_str()

    if result is None or not result.get("ok"):
        await followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Gagal refresh token. "
                "Apakah Gmail service sedang berjalan?"
            ),
        )
        return

    age: float = result.get("token_age_seconds", 0)
    status_text: str = (
        f"\u2705 OAuth token refreshed! "
        f"Token age: {age:.0f}s. Next refresh in ~7 days."
    )

    fields: tuple[EmbedField, ...] = (
        EmbedField(name="Token Age", value=f"{age:.0f}s", inline=True),
    )
    data_obj = EmbedData(
        title="\U0001f504 Email Reauth",
        description=status_text,
        color=SUCCESS,
        fields=fields,
        timestamp=ts,
    )
    embed = to_discord_embed(data_obj)
    await followup_send(interaction, embed=embed)

# ── /email-search ──────────────────────────────────────────────────────────

_MAX_RESULTS_PER_EMBED = 5

async def email_search_callback(interaction: Any) -> None:
    """Handle ``/email-search <query>`` — full-text search stored emails.

    Args:
        interaction: The Discord interaction object.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    # Extract the required query option
    query: str = ""
    data = getattr(interaction, "data", None)
    if data is not None:
        options: list[dict[str, object]] = (
            data.get("options", []) if isinstance(data, dict) else []
        )
        for opt in options:
            if opt.get("name") == "query":
                query = str(opt.get("value", ""))

    if not query.strip():
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Masukkan query pencarian. Contoh: `/email-search invoice`",
        )
        return

    await defer_ephemeral(interaction)

    result = await _call_gmail_api(
        "GET", "/api/email-search",
        params={"q": query, "limit": "15"},
    )

    ts = now_wib_str()

    if result is None:
        await followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Gagal menghubungi Gmail service. "
                "Apakah service sedang berjalan?"
            ),
        )
        return

    results: list[dict[str, Any]] = result.get("results", [])
    total_count: int = result.get("count", len(results))

    if not results:
        data_obj = EmbedData(
            title="\U0001f50d Email Search: No Results",
            description=f"Tidak ada hasil untuk query: `{query}`",
            color=WARNING,
            timestamp=ts,
        )
        embed = to_discord_embed(data_obj)
        await followup_send(interaction, embed=embed)
        return

    # Send first page — paginate rest if more than _MAX_RESULTS_PER_EMBED
    page = 0
    for batch_start in range(0, len(results), _MAX_RESULTS_PER_EMBED):
        batch = results[batch_start:batch_start + _MAX_RESULTS_PER_EMBED]
        page += 1
        total_pages = (len(results) + _MAX_RESULTS_PER_EMBED - 1) // _MAX_RESULTS_PER_EMBED

        items: list[str] = []
        for r in batch:
            subj: str = str(r.get("subject", "(no subject)"))
            cat: str = str(r.get("category", "unknown"))
            imp: int = int(r.get("importance", 0))
            snippet: str = str(r.get("summary_snippet", ""))
            date_raw: str | None = r.get("date", None)
            rank: float = float(r.get("rank", 0.0))

            # Format date compactly
            date_str: str = "?"
            if date_raw:
                try:
                    dt = date_raw[:10]
                    date_str = dt
                except Exception:
                    date_str = date_raw[:10] if len(date_raw) >= 10 else date_raw

            items.append(
                f"**{subj[:80]}**\n"
                f"`{cat}` \u00b7 importance {imp} \u00b7 {date_str} \u00b7 score {rank:.2f}\n"
                f"{snippet}\n"
            )

        title = (
            f"\U0001f50d Email Search: `{query}` ({total_count} results)"
            if page == 1
            else f"\U0001f50d Search continued ({total_count} results, page {page}/{total_pages})"
        )
        desc = "\n".join(items)

        data_obj = EmbedData(
            title=title,
            description=desc[:4000],
            color=INFO_BLUE,
            timestamp=ts,
        )
        embed = to_discord_embed(data_obj)
        await followup_send(interaction, embed=embed)

__all__ = [
    "email_digest_callback",
    "email_consent_callback",
    "email_reauth_callback",
    "email_search_callback",
]