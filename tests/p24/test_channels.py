"""W16 — M14 Channels test suite.

Verifies:
- All 4 channels are importable.
- No banned patterns in guinevere/channels/ source.
- CONFIG_MISSING markers present (D2 pattern).
- Consent/hard_stop stripped.
- Send actions exposed via ChannelSender protocol.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


# ---- Import tests ----


class TestChannelImports:
    """All 4 channels must be importable from guinevere.channels."""

    def test_import_whatsapp(self) -> None:
        from guinevere.channels.whatsapp import WhatsAppAdapter

        assert WhatsAppAdapter is not None

    def test_import_gmail(self) -> None:
        from guinevere.channels.gmail import GmailAdapter

        assert GmailAdapter is not None

    def test_import_x(self) -> None:
        from guinevere.channels.x import XAdapter

        assert XAdapter is not None

    def test_import_telegram(self) -> None:
        from guinevere.channels.telegram import TelegramAdapter

        assert TelegramAdapter is not None

    def test_import_registry(self) -> None:
        from guinevere.channels import ChannelId, ChannelStatus

        assert ChannelId.WHATSAPP.value == "whatsapp"
        assert ChannelId.GMAIL.value == "gmail"
        assert ChannelId.X.value == "x"
        assert ChannelId.TELEGRAM.value == "telegram"
        assert ChannelStatus.CONFIG_MISSING.value == "config_missing"

    def test_import_bridge(self) -> None:
        from guinevere.channels._bridge import (
            ConsciousnessBridge,
            OutboundMessage,
            SendPriority,
            SendResult,
            wire,
        )

        assert ConsciousnessBridge is not None
        assert OutboundMessage is not None
        assert SendPriority is not None
        assert SendResult is not None
        assert callable(wire)


# ---- CONFIG_MISSING tests ----


class TestConfigMissing:
    """All channels must report CONFIG_MISSING in D2 (no real creds)."""

    def test_whatsapp_config_missing(self) -> None:
        from guinevere.channels.whatsapp import WhatsAppAdapter

        adapter = WhatsAppAdapter()
        # In D2 (no WHATSAPP_PHONE_NUMBER / REDIS_URL), should be config_missing.
        assert adapter.is_config_missing is True
        assert len(adapter.config_missing_reasons) > 0

    def test_gmail_config_missing(self) -> None:
        from guinevere.channels.gmail import GmailAdapter

        adapter = GmailAdapter()
        assert adapter.is_config_missing is True
        assert len(adapter.config_missing_reasons) > 0

    def test_x_config_missing(self) -> None:
        from guinevere.channels.x import XAdapter

        adapter = XAdapter()
        assert adapter.is_config_missing is True
        assert len(adapter.config_missing_reasons) > 0

    def test_telegram_config_missing(self) -> None:
        from guinevere.channels.telegram import TelegramAdapter

        adapter = TelegramAdapter()
        assert adapter.is_config_missing is True
        assert len(adapter.config_missing_reasons) > 0


# ---- ChannelSender protocol tests ----


class TestChannelSenderProtocol:
    """All adapters must implement the ChannelSender interface."""

    def test_whatsapp_channel_id(self) -> None:
        from guinevere.channels.whatsapp import WhatsAppAdapter

        adapter = WhatsAppAdapter()
        assert adapter.channel_id == "whatsapp"

    def test_gmail_channel_id(self) -> None:
        from guinevere.channels.gmail import GmailAdapter

        adapter = GmailAdapter()
        assert adapter.channel_id == "gmail"

    def test_x_channel_id(self) -> None:
        from guinevere.channels.x import XAdapter

        adapter = XAdapter()
        assert adapter.channel_id == "x"

    def test_telegram_channel_id(self) -> None:
        from guinevere.channels.telegram import TelegramAdapter

        adapter = TelegramAdapter()
        assert adapter.channel_id == "telegram"


# ---- Send action tests (L1/L2 exposed) ----


class TestSendActions:
    """Adapters must expose send_message and return SendResult on CONFIG_MISSING."""

    @pytest.mark.asyncio
    async def test_whatsapp_send_returns_config_missing(self) -> None:
        from guinevere.channels.whatsapp import WhatsAppAdapter

        adapter = WhatsAppAdapter()
        result = await adapter.send_message(target="+1234567890", body="hello")
        assert result.success is False
        assert result.error is not None and "CONFIG_MISSING" in result.error
        assert result.channel == "whatsapp"

    @pytest.mark.asyncio
    async def test_gmail_send_returns_config_missing(self) -> None:
        from guinevere.channels.gmail import GmailAdapter

        adapter = GmailAdapter()
        result = await adapter.send_message(target="test@example.com", body="hello")
        assert result.success is False
        assert result.error is not None and "CONFIG_MISSING" in result.error
        assert result.channel == "gmail"

    @pytest.mark.asyncio
    async def test_x_send_returns_config_missing(self) -> None:
        from guinevere.channels.x import XAdapter

        adapter = XAdapter()
        result = await adapter.send_message(target="", body="hello world")
        assert result.success is False
        assert result.error is not None and "CONFIG_MISSING" in result.error
        assert result.channel == "x"

    @pytest.mark.asyncio
    async def test_telegram_send_returns_config_missing(self) -> None:
        from guinevere.channels.telegram import TelegramAdapter

        adapter = TelegramAdapter()
        result = await adapter.send_message(target="123456", body="hello")
        assert result.success is False
        assert result.error is not None and "CONFIG_MISSING" in result.error
        assert result.channel == "telegram"


# ---- Envelope DTO tests ----


class TestEnvelopeDTOs:
    """Envelope DTOs must be available and validate correctly."""

    def test_whatsapp_envelope_validation(self) -> None:
        from datetime import UTC, datetime

        from guinevere.channels.whatsapp.adapter import WhatsAppMessageEnvelope

        envelope = WhatsAppMessageEnvelope(
            sender_jid_hash="abc123",
            sender_raw_jid="628123@s.whatsapp.net",
            message_id="msg-001",
            timestamp=datetime.now(UTC),
            body="Hello",
            chat_jid="628123@s.whatsapp.net",
            is_group=False,
        )
        envelope.validate()  # Should not raise.
        assert envelope.is_text is True

    def test_gmail_envelope_validation(self) -> None:
        from datetime import UTC, datetime

        from guinevere.channels.gmail.adapter import GmailMessageEnvelope

        envelope = GmailMessageEnvelope(
            message_id="msg-001",
            thread_id="thread-001",
            sender="test@example.com",
            recipients=["dest@example.com"],
            subject="Test",
            body_text="Hello",
            body_html="<p>Hello</p>",
            timestamp=datetime.now(UTC),
            labels=["INBOX"],
            snippet="Hello",
            has_attachments=False,
        )
        envelope.validate()  # Should not raise.
        assert envelope.is_reply is False

    def test_telegram_envelope_validation(self) -> None:
        from datetime import UTC, datetime

        from guinevere.channels.telegram.adapter import TelegramMessageEnvelope

        envelope = TelegramMessageEnvelope(
            message_id=12345,
            chat_id=67890,
            sender_id=111,
            sender_name="Test User",
            text="Hello",
            timestamp=datetime.now(UTC),
        )
        envelope.validate()  # Should not raise.
        assert envelope.is_text is True


# ---- Consciousness bridge tests ----


class TestConsciousnessBridge:
    """The bridge must wire senders and dispatch messages."""

    @pytest.mark.asyncio
    async def test_bridge_register_and_send(self) -> None:
        from guinevere.channels._bridge import (
            ConsciousnessBridge,
            OutboundMessage,
            SendResult,
        )

        bridge = ConsciousnessBridge()
        # No senders registered — send should return failure.
        msg = OutboundMessage(channel="nonexistent", target="x", body="test")
        result = await bridge.send(msg)
        assert result.success is False
        assert result.error is not None and "not registered" in result.error

    @pytest.mark.asyncio
    async def test_bridge_config_missing_sender(self) -> None:
        from guinevere.channels._bridge import (
            ConsciousnessBridge,
            OutboundMessage,
        )
        from guinevere.channels.whatsapp import WhatsAppAdapter

        bridge = ConsciousnessBridge()
        adapter = WhatsAppAdapter()
        # Register even though config is missing.
        bridge.register(adapter)
        assert "whatsapp" in bridge.all_channels
        # Should get config_missing on send.
        msg = OutboundMessage(channel="whatsapp", target="+123", body="test")
        result = await bridge.send(msg)
        assert result.success is False
        assert result.error is not None and "CONFIG_MISSING" in result.error

    def test_bridge_wire_function(self) -> None:
        from guinevere.channels._bridge import wire

        assert callable(wire)


# ---- Registry tests ----


class TestRegistry:
    """Channel registry must support register/list/get."""

    def test_register_and_list(self) -> None:
        from guinevere.channels import ChannelId, get_channel_class, list_channels, register_channel

        class FakeAdapter:
            pass

        register_channel(ChannelId.WHATSAPP, FakeAdapter)
        channels = list_channels()
        assert ChannelId.WHATSAPP in channels
        assert get_channel_class(ChannelId.WHATSAPP) is FakeAdapter


# ---- Negative tests (forbidden patterns) ----


class TestForbiddenPatterns:
    """Ensure forbidden patterns do NOT appear in channel source code.

    Only scans guinevere/channels/ source (NOT tests/).
    """

    @pytest.fixture
    def channels_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "guinevere" / "channels"

    def test_no_consent_gate_references(self, channels_dir: Path) -> None:
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "consent_gate" not in content, f"consent_gate found in {py_file}"

    def test_no_hard_stop_references(self, channels_dir: Path) -> None:
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "HardStopHandler" not in content, f"HardStopHandler found in {py_file}"
            assert "from .hard_stop" not in content, f"hard_stop import in {py_file}"

    def test_no_safe_mode_references(self, channels_dir: Path) -> None:
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "safe_mode" not in content, f"safe_mode found in {py_file}"

    def test_no_mcp_references(self, channels_dir: Path) -> None:
        """No MCP server references in channel source."""
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            lower = content.lower()
            assert "mcp" not in lower, f"MCP reference found in {py_file}"

    def test_no_src_imports(self, channels_dir: Path) -> None:
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "from src." not in content, f"'from src.' import found in {py_file}"

    def test_no_type_ignore(self, channels_dir: Path) -> None:
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "# type: ignore" not in content, f"'# type: ignore' found in {py_file}"

    def test_no_bare_except(self, channels_dir: Path) -> None:
        for py_file in channels_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                if stripped == "except:" or stripped.startswith("except:"):
                    pytest.fail(f"bare 'except:' at {py_file}:{i}")


# ---- Channel-specific feature tests ----


class TestWhatsAppFeatures:
    """WhatsApp-specific feature tests."""

    def test_formatter_basic(self) -> None:
        from guinevere.channels.whatsapp.adapter import WhatsAppFormatter

        fmt = WhatsAppFormatter()
        result = fmt.format("Hello **world**")
        assert len(result) == 1
        assert "*world*" in result[0]

    def test_formatter_chunking(self) -> None:
        from guinevere.channels.whatsapp.adapter import ChunkingConfig, WhatsAppFormatter

        config = ChunkingConfig(target_size=50, max_chunks=5)
        fmt = WhatsAppFormatter(config)
        long_text = "word " * 100  # 500 chars
        chunks = fmt.format(long_text)
        assert len(chunks) > 1
        # Each chunk (except possibly the last) should have sequence prefix.
        assert "(1/" in chunks[0]

    def test_rate_limiter(self) -> None:
        from guinevere.channels.whatsapp.adapter import RateLimiter

        limiter = RateLimiter()
        # First message should pass.
        result = limiter.check("hash1")
        assert result.allowed is True
        # Duplicate within 120s should be blocked.
        result = limiter.check("hash1")
        assert result.allowed is False
        assert result.reason == "duplicate_message"
        # Different message should pass.
        result = limiter.check("hash2")
        assert result.allowed is True

    def test_jid_helpers(self) -> None:
        from guinevere.channels.whatsapp.adapter import normalize_jid, to_jid

        assert normalize_jid("628123@s.whatsapp.net") == "628123"
        assert normalize_jid("628123:7@s.whatsapp.net") == "628123"
        assert to_jid("628123") == "628123@s.whatsapp.net"
        assert to_jid("628123@s.whatsapp.net") == "628123@s.whatsapp.net"


class TestGmailFeatures:
    """Gmail-specific feature tests."""

    def test_email_taxonomy(self) -> None:
        from guinevere.channels.gmail.adapter import (
            CATEGORY_ACTIONS,
            CATEGORY_PRIORITY,
            EmailCategory,
            EmailPriority,
        )

        assert EmailCategory.CLIENT_WORK in CATEGORY_PRIORITY
        assert CATEGORY_PRIORITY[EmailCategory.CLIENT_WORK] == EmailPriority.HIGH
        assert "notify" in CATEGORY_ACTIONS[EmailCategory.FINANCIAL]
        assert "archive" in CATEGORY_ACTIONS[EmailCategory.PROMOTION]

    def test_quota_tracker(self) -> None:
        from guinevere.channels.gmail.adapter import QuotaTracker

        tracker = QuotaTracker(limit_per_minute=100)
        assert tracker.current_usage() == 0
        assert tracker.check(50) is True
        tracker.record(50)
        assert tracker.current_usage() == 50
        assert tracker.check(60) is False  # 50 + 60 > 100
        tracker.reset_window()
        assert tracker.current_usage() == 0

    def test_settings_from_env(self) -> None:
        from guinevere.channels.gmail.adapter import GmailSettings

        settings = GmailSettings.from_env()
        assert settings.pubsub_project_id == "guinevere-gmail-prod"
        assert settings.api_quota_limit_per_minute == 6000


class TestXFeatures:
    """X/Twitter-specific feature tests."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions(self) -> None:
        from guinevere.channels.x.adapter import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=1)
        assert cb.state == CircuitState.CLOSED
        # Record failures up to threshold.
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert await cb.allow_request() is False

    def test_queue_manager(self) -> None:
        from guinevere.channels.x.adapter import QueueManager, QueuedPost

        qm = QueueManager(max_size=3)
        post = QueuedPost(post_id="p1", text="Hello")
        assert qm.enqueue(post) is True
        assert qm.size == 1
        dequeued = qm.dequeue()
        assert dequeued is not None
        assert dequeued.post_id == "p1"
        assert qm.size == 0
        assert qm.dequeue() is None

    def test_content_moderation(self) -> None:
        from guinevere.channels.x import XAdapter

        adapter = XAdapter()
        assert adapter._moderate_content("Normal tweet text") is True
        assert adapter._moderate_content("Buy now! Click here!") is False


class TestTelegramFeatures:
    """Telegram-specific feature tests."""

    def test_telegram_client_requires_token(self) -> None:
        from guinevere.channels.telegram.adapter import TelegramClient

        with pytest.raises(ValueError, match="CONFIG_MISSING"):
            TelegramClient(token="")

        with pytest.raises(ValueError, match="CONFIG_MISSING"):
            TelegramClient(token="   ")

    def test_envelope_group_detection(self) -> None:
        from datetime import UTC, datetime

        from guinevere.channels.telegram.adapter import TelegramMessageEnvelope

        private = TelegramMessageEnvelope(
            message_id=1, chat_id=100, sender_id=1, sender_name="User",
            text="Hello", timestamp=datetime.now(UTC), chat_type="private",
        )
        assert private.is_group is False

        group = TelegramMessageEnvelope(
            message_id=2, chat_id=-100, sender_id=2, sender_name="User",
            text="Hello", timestamp=datetime.now(UTC), chat_type="supergroup",
        )
        assert group.is_group is True
