"""P7-019: ``/surveillance-status`` Discord command — unit tests.

Tests ``surveillance_status_callback``, ``_build_status_embed``, and
``is_faiz_interaction`` with mocked Discord interactions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.discord.cmd_surveillance_status import (
    _build_status_embed,
    is_faiz_interaction,
    surveillance_status_callback,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def consent_status_active() -> dict[str, str]:
    """Return consent status with all scopes ACTIVE."""
    return {
        "surveillance.app_usage": "ACTIVE",
        "surveillance.location": "ACTIVE",
        "surveillance.notifications": "ACTIVE",
        "surveillance.clipboard": "ACTIVE",
    }


@pytest.fixture
def consent_status_mixed() -> dict[str, str]:
    """Return consent status with mixed states."""
    return {
        "surveillance.app_usage": "ACTIVE",
        "surveillance.location": "WITHDRAWN",
        "surveillance.notifications": "PAUSED",
        "surveillance.clipboard": "ACTIVE",
    }


@pytest.fixture
def mock_faiz_interaction() -> MagicMock:
    """Return a mock interaction where user == guild owner (Faiz)."""
    interaction = MagicMock()
    interaction.guild.owner_id = 1510876414671323206
    interaction.user.id = 1510876414671323206
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_non_faiz_interaction() -> MagicMock:
    """Return a mock interaction where user != guild owner."""
    interaction = MagicMock()
    interaction.guild.owner_id = 1510876414671323206
    interaction.user.id = 999999999999999999
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_interaction_no_guild() -> MagicMock:
    """Return a mock interaction with no guild attribute."""
    interaction = MagicMock(spec=[])
    return interaction


# ---------------------------------------------------------------------------
# Tests: is_faiz_interaction
# ---------------------------------------------------------------------------


def test_is_faiz_interaction_returns_true_for_owner(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Owner ID matches user ID → True."""
    assert is_faiz_interaction(mock_faiz_interaction) is True


def test_is_faiz_interaction_returns_false_for_non_owner(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """Owner ID does not match user ID → False."""
    assert is_faiz_interaction(mock_non_faiz_interaction) is False


def test_is_faiz_interaction_returns_false_when_guild_none() -> None:
    """No guild attribute → False (fail-safe)."""
    interaction = MagicMock()
    interaction.guild = None
    interaction.user = MagicMock(id=12345)
    assert is_faiz_interaction(interaction) is False


def test_is_faiz_interaction_returns_false_when_user_none() -> None:
    """No user attribute → False (fail-safe)."""
    interaction = MagicMock()
    interaction.guild = MagicMock(owner_id=12345)
    interaction.user = None
    assert is_faiz_interaction(interaction) is False


def test_is_faiz_interaction_with_missing_attrs() -> None:
    """No guild or user attrs → False."""
    interaction = MagicMock(spec=[])
    assert is_faiz_interaction(interaction) is False


# ---------------------------------------------------------------------------
# Tests: surveillance_status_callback — non-Faiz rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_rejects_non_faiz(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """Non-Faiz → ephemeral denial message, no further processing."""
    await surveillance_status_callback(mock_non_faiz_interaction)

    mock_non_faiz_interaction.response.send_message.assert_awaited_once()
    call_args = mock_non_faiz_interaction.response.send_message.call_args
    assert call_args.kwargs.get("ephemeral") is True
    # Content is passed as positional arg by discord.py's send_message
    all_text = str(call_args.args) + str(call_args.kwargs)
    assert "restricted" in all_text.lower()
    # Defer should NOT be called for non-Faiz
    mock_non_faiz_interaction.response.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_callback_message_is_ephemeral(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """The denial message uses ephemeral=True."""
    await surveillance_status_callback(mock_non_faiz_interaction)

    call_kwargs = mock_non_faiz_interaction.response.send_message.call_args
    assert call_kwargs.kwargs["ephemeral"] is True


# ---------------------------------------------------------------------------
# Tests: surveillance_status_callback — defer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_defers_ephemerally(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Faiz → deferred with ephemeral=True, thinking=True."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=3),
        _get_last_event_timestamp=AsyncMock(return_value="2026-06-03T12:00:00Z"),
        _get_buffer_size=AsyncMock(return_value="42"),
        _get_consumer_health=AsyncMock(return_value="OK"),
    )

    mock_faiz_interaction.response.defer.assert_awaited_once_with(
        ephemeral=True, thinking=True
    )


# ---------------------------------------------------------------------------
# Tests: surveillance_status_callback — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_sends_embed_on_success(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Happy path: embed sent with ephemeral=True."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=3),
        _get_last_event_timestamp=AsyncMock(return_value="2026-06-03T12:00:00Z"),
        _get_buffer_size=AsyncMock(return_value="42"),
        _get_consumer_health=AsyncMock(return_value="Healthy"),
    )

    mock_faiz_interaction.followup.send.assert_awaited_once()
    call_kwargs = mock_faiz_interaction.followup.send.call_args
    assert call_kwargs.kwargs["ephemeral"] is True
    assert "embed" in call_kwargs.kwargs


@pytest.mark.asyncio
async def test_callback_embed_has_correct_title(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Embed title is 'Surveillance Status'."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=1),
        _get_last_event_timestamp=AsyncMock(return_value="N/A"),
        _get_buffer_size=AsyncMock(return_value="0"),
        _get_consumer_health=AsyncMock(return_value="N/A"),
    )

    embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
    assert embed.title == "Surveillance Status"


@pytest.mark.asyncio
async def test_callback_embed_has_correct_color(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Embed color is 0x0891B2 (teal)."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=1),
        _get_last_event_timestamp=AsyncMock(return_value="N/A"),
        _get_buffer_size=AsyncMock(return_value="0"),
        _get_consumer_health=AsyncMock(return_value="N/A"),
    )

    embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
    assert embed.colour.value == 0x0891B2


@pytest.mark.asyncio
async def test_callback_embed_has_correct_footer(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Embed footer is 'Guinevere Surveillance Monitor'."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=1),
        _get_last_event_timestamp=AsyncMock(return_value="N/A"),
        _get_buffer_size=AsyncMock(return_value="0"),
        _get_consumer_health=AsyncMock(return_value="N/A"),
    )

    embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
    assert embed.footer.text == "Guinevere Surveillance Monitor"


# ---------------------------------------------------------------------------
# Tests: consent display in embed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_embed_shows_consent_status(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Embed fields include consent status values."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=2),
        _get_last_event_timestamp=AsyncMock(return_value="N/A"),
        _get_buffer_size=AsyncMock(return_value="10"),
        _get_consumer_health=AsyncMock(return_value="OK"),
    )

    embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
    fields_text = " ".join(f.name for f in embed.fields)
    assert "Consent Status" in fields_text
    # Check active status is present in Consent field
    consent_field = embed.fields[0]
    assert "ACTIVE" in consent_field.value


# ---------------------------------------------------------------------------
# Tests: query failure → "Unavailable"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_query_failure_shows_unavailable(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Failed data-gathering → 'Unavailable' in embed."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(side_effect=RuntimeError("DB down")),
        _get_device_count=AsyncMock(side_effect=RuntimeError("Redis down")),
        _get_last_event_timestamp=AsyncMock(side_effect=RuntimeError("Error")),
        _get_buffer_size=AsyncMock(side_effect=RuntimeError("Error")),
        _get_consumer_health=AsyncMock(side_effect=RuntimeError("Error")),
    )

    embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
    fields_text = " ".join(f.value for f in embed.fields)
    assert "Unavailable" in fields_text


# ---------------------------------------------------------------------------
# Tests: no raw surveillance data exposed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_embed_no_raw_surveillance_payload(
    mock_faiz_interaction: MagicMock,
    consent_status_active: dict[str, str],
) -> None:
    """Embed contains only metadata — no raw event data."""
    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(return_value=consent_status_active),
        _get_device_count=AsyncMock(return_value=3),
        _get_last_event_timestamp=AsyncMock(return_value="2026-06-03T12:00:00Z"),
        _get_buffer_size=AsyncMock(return_value="42"),
        _get_consumer_health=AsyncMock(return_value="Healthy"),
    )

    embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
    all_text = " ".join(
        [f.name for f in embed.fields] + [f.value for f in embed.fields]
    )
    # No raw payload fields
    assert "app_name" not in all_text
    assert "window_title" not in all_text
    assert "clipboard_text" not in all_text
    assert "latitude" not in all_text.lower()


# ---------------------------------------------------------------------------
# Tests: _build_status_embed
# ---------------------------------------------------------------------------


def test_build_status_embed_returns_embed() -> None:
    """_build_status_embed returns a discord.Embed."""
    data: dict[str, object] = {
        "consent_status": {
            "surveillance.app_usage": "ACTIVE",
            "surveillance.location": "ACTIVE",
            "surveillance.notifications": "ACTIVE",
            "surveillance.clipboard": "ACTIVE",
        },
        "active_devices": 5,
        "last_event": "2026-06-03T12:00:00Z",
        "buffer_size": "128",
        "consumer_status": "Healthy",
    }
    with patch("src.discord.cmd_surveillance_status.SURVEILLANCE", 0x0891B2):
        embed = _build_status_embed(data)
    assert embed.title == "Surveillance Status"
    assert embed.footer.text == "Guinevere Surveillance Monitor"
    assert len(embed.fields) == 5


def test_build_status_embed_empty_data() -> None:
    """_build_status_embed handles empty data dict gracefully."""
    data: dict[str, object] = {}
    embed = _build_status_embed(data)
    assert embed.title == "Surveillance Status"
    assert len(embed.fields) == 5
    # All fields should show Unavailable
    for field in embed.fields:
        assert "Unavailable" in field.value


def test_build_status_embed_partial_data() -> None:
    """_build_status_embed handles partial data with defaults."""
    data: dict[str, object] = {
        "consent_status": {},
        "buffer_size": "42",
    }
    embed = _build_status_embed(data)
    # Check buffer_size field shows "42"
    buffer_field = [f for f in embed.fields if f.name == "Buffer Size"]
    assert len(buffer_field) == 1
    assert "42" in buffer_field[0].value


def test_is_faiz_interaction_type_safety() -> None:
    """is_faiz_interaction returns bool, not None."""
    result = is_faiz_interaction(object())
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Tests: surveillance_status_callback — fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_fallback_on_embed_failure(
    mock_faiz_interaction: MagicMock,
) -> None:
    """If embed sending fails, a fallback text message is sent."""
    mock_faiz_interaction.followup.send = AsyncMock(
        side_effect=[RuntimeError("embed fail"), None]
    )

    await surveillance_status_callback(
        mock_faiz_interaction,
        _get_consent_status=AsyncMock(
            return_value={
                "surveillance.app_usage": "ACTIVE",
                "surveillance.location": "ACTIVE",
                "surveillance.notifications": "ACTIVE",
                "surveillance.clipboard": "ACTIVE",
            }
        ),
        _get_device_count=AsyncMock(return_value=1),
        _get_last_event_timestamp=AsyncMock(return_value="N/A"),
        _get_buffer_size=AsyncMock(return_value="0"),
        _get_consumer_health=AsyncMock(return_value="N/A"),
    )

    # followup.send was called twice: first failed, second fallback
    assert mock_faiz_interaction.followup.send.call_count >= 2
    fallback_kwargs = mock_faiz_interaction.followup.send.call_args_list[1].kwargs
    assert "unavailable" in str(fallback_kwargs.get("content", "")).lower()


# ===========================================================================
# P7-020: /surveillance-pause and /surveillance-resume tests
# ===========================================================================

from src.discord.cmd_surveillance_pause import (
    is_paused as is_paused_pause,
    surveillance_pause_callback,
    _set_paused_for_testing as _set_paused_pause,
)
from src.discord.cmd_surveillance_resume import (
    is_paused as is_paused_resume,
    surveillance_resume_callback,
    _set_paused_for_testing as _set_paused_resume,
)

# ---------------------------------------------------------------------------
# Pause tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_sets_paused_flag(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized pause → _PAUSED flag is set to True."""
    _set_paused_pause(False)  # Reset before test
    try:
        await surveillance_pause_callback(mock_faiz_interaction)
        assert is_paused_pause() is True
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_rejects_non_faiz(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """Non-Faiz pause → ephemeral denial, _PAUSED unchanged."""
    _set_paused_pause(False)
    try:
        await surveillance_pause_callback(mock_non_faiz_interaction)
        mock_non_faiz_interaction.response.send_message.assert_awaited_once()
        call_kwargs = mock_non_faiz_interaction.response.send_message.call_args
        assert call_kwargs.kwargs.get("ephemeral") is True
        assert is_paused_pause() is False
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_embed_has_correct_title(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized pause → embed title is 'Surveillance Paused'."""
    _set_paused_pause(False)
    try:
        await surveillance_pause_callback(mock_faiz_interaction)
        embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
        assert embed.title == "Surveillance Paused"
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_embed_has_correct_color(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized pause → embed color is SURVEILLANCE (0x0891B2)."""
    _set_paused_pause(False)
    try:
        await surveillance_pause_callback(mock_faiz_interaction)
        embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
        assert embed.colour.value == 0x0891B2
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_embed_has_required_fields(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized pause → embed contains Consent, Ingestion Pipeline, Safe Mode fields."""
    _set_paused_pause(False)
    try:
        await surveillance_pause_callback(mock_faiz_interaction)
        embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
        field_names = {f.name for f in embed.fields}
        assert "Consent" in field_names
        assert "Ingestion Pipeline" in field_names
        assert "Safe Mode" in field_names
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_response_is_ephemeral(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized pause → followup.send uses ephemeral=True."""
    _set_paused_pause(False)
    try:
        await surveillance_pause_callback(mock_faiz_interaction)
        call_kwargs = mock_faiz_interaction.followup.send.call_args
        assert call_kwargs.kwargs.get("ephemeral") is True
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_logs_audit_entry() -> None:
    """Authorized pause → structlog audit entry with action='surveillance_pause'."""
    _set_paused_pause(False)
    interaction = MagicMock()
    interaction.guild.owner_id = 1510876414671323206
    interaction.user.id = 1510876414671323206
    interaction.user.__str__ = lambda self: "TestUser#1234"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    with patch(
        "src.discord.cmd_surveillance_pause.logger.info"
    ) as mock_log_info:
        try:
            await surveillance_pause_callback(interaction)
            audit_calls = [
                c
                for c in mock_log_info.call_args_list
                if c.kwargs.get("action") == "surveillance_pause"
            ]
            assert len(audit_calls) >= 1
            assert "user" in audit_calls[0].kwargs
        finally:
            _set_paused_pause(False)


# ---------------------------------------------------------------------------
# Resume tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_clears_paused_flag(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized resume when paused → _PAUSED set to False."""
    _set_paused_resume(True)  # Simulate currently paused
    try:
        await surveillance_resume_callback(mock_faiz_interaction)
        assert is_paused_resume() is False
    finally:
        _set_paused_resume(False)


@pytest.mark.asyncio
async def test_resume_rejects_non_faiz(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """Non-Faiz resume → ephemeral denial, _PAUSED unchanged."""
    _set_paused_resume(True)
    try:
        await surveillance_resume_callback(mock_non_faiz_interaction)
        mock_non_faiz_interaction.response.send_message.assert_awaited_once()
        call_kwargs = mock_non_faiz_interaction.response.send_message.call_args
        assert call_kwargs.kwargs.get("ephemeral") is True
        assert is_paused_resume() is True
    finally:
        _set_paused_resume(False)


@pytest.mark.asyncio
async def test_resume_when_already_active(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Resume when NOT paused → 'already active' message, _PAUSED stays False."""
    _set_paused_resume(False)
    try:
        await surveillance_resume_callback(mock_faiz_interaction)
        call_kwargs = mock_faiz_interaction.followup.send.call_args
        content = str(call_kwargs.kwargs.get("content", ""))
        assert "already active" in content.lower()
        assert is_paused_resume() is False
    finally:
        _set_paused_resume(False)


@pytest.mark.asyncio
async def test_resume_embed_has_correct_title(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized resume → embed title is 'Surveillance Resumed'."""
    _set_paused_resume(True)
    try:
        await surveillance_resume_callback(mock_faiz_interaction)
        embed = mock_faiz_interaction.followup.send.call_args.kwargs["embed"]
        assert embed.title == "Surveillance Resumed"
    finally:
        _set_paused_resume(False)


@pytest.mark.asyncio
async def test_resume_response_is_ephemeral(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized resume → followup.send uses ephemeral=True."""
    _set_paused_resume(True)
    try:
        await surveillance_resume_callback(mock_faiz_interaction)
        call_kwargs = mock_faiz_interaction.followup.send.call_args
        assert call_kwargs.kwargs.get("ephemeral") is True
    finally:
        _set_paused_resume(False)


@pytest.mark.asyncio
async def test_resume_logs_audit_entry() -> None:
    """Authorized resume → structlog audit entry with action='surveillance_resume'."""
    _set_paused_resume(True)
    interaction = MagicMock()
    interaction.guild.owner_id = 1510876414671323206
    interaction.user.id = 1510876414671323206
    interaction.user.__str__ = lambda self: "TestUser#1234"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    with patch(
        "src.discord.cmd_surveillance_resume.logger.info"
    ) as mock_log_info:
        try:
            await surveillance_resume_callback(interaction)
            audit_calls = [
                c
                for c in mock_log_info.call_args_list
                if c.kwargs.get("action") == "surveillance_resume"
            ]
            assert len(audit_calls) >= 1
            assert "user" in audit_calls[0].kwargs
        finally:
            _set_paused_resume(False)


# ---------------------------------------------------------------------------
# Pause cache invalidation tests (C4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_invalidates_consent_cache_for_all_scopes(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Authorized pause calls invalidate_cache for every surveillance scope."""
    _set_paused_pause(False)
    mock_invalidate = AsyncMock()
    try:
        with patch(
            "src.surveillance.consent_gate.invalidate_cache",
            mock_invalidate,
        ):
            await surveillance_pause_callback(mock_faiz_interaction)

        called_scopes = {
            call.args[0] for call in mock_invalidate.call_args_list
        }
        expected_scopes = {
            "surveillance.app_usage",
            "surveillance.location",
            "surveillance.notifications",
            "surveillance.clipboard",
        }
        assert called_scopes == expected_scopes
    finally:
        _set_paused_pause(False)


@pytest.mark.asyncio
async def test_pause_succeeds_when_cache_invalidation_fails(
    mock_faiz_interaction: MagicMock,
) -> None:
    """Pause completes even if invalidate_cache raises for all scopes."""
    _set_paused_pause(False)
    mock_invalidate = AsyncMock(side_effect=RuntimeError("Redis down"))
    try:
        with patch(
            "src.surveillance.consent_gate.invalidate_cache",
            mock_invalidate,
        ):
            await surveillance_pause_callback(mock_faiz_interaction)

        # Pause still set the flag and sent the embed
        assert is_paused_pause() is True
        mock_faiz_interaction.followup.send.assert_awaited_once()
    finally:
        _set_paused_pause(False)


# ---------------------------------------------------------------------------
# Ephemeral response cross-checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_denial_is_ephemeral(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """Non-Faiz pause denial uses ephemeral=True."""
    await surveillance_pause_callback(mock_non_faiz_interaction)
    call_kwargs = mock_non_faiz_interaction.response.send_message.call_args
    assert call_kwargs.kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_resume_denial_is_ephemeral(
    mock_non_faiz_interaction: MagicMock,
) -> None:
    """Non-Faiz resume denial uses ephemeral=True."""
    _set_paused_resume(True)
    try:
        await surveillance_resume_callback(mock_non_faiz_interaction)
        call_kwargs = mock_non_faiz_interaction.response.send_message.call_args
        assert call_kwargs.kwargs.get("ephemeral") is True
    finally:
        _set_paused_resume(False)