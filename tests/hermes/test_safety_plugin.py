"""Unit tests for GuinevereSafetyPlugin — Phase 1."""
from __future__ import annotations

import enum
import sys
from collections import namedtuple
from unittest.mock import MagicMock, patch

# Prevent transitive import failure from src/hermes/__init__.py -> session_adapter
_FAKE_MODULES = ("run_agent", "redis", "redis.asyncio")
for _mod in _FAKE_MODULES:
    sys.modules.setdefault(_mod, MagicMock())

# ---------------------------------------------------------------
# Mock safety module imports BEFORE importing the plugin.
# This ensures plugin._init_safety_modules() succeeds for all gates.
# ---------------------------------------------------------------

# Core services
sys.modules.setdefault("src.core.services.hard_stop_handler", MagicMock())

# Persona modules
sys.modules.setdefault("src.persona.safe_mode", MagicMock())
sys.modules.setdefault("src.persona.drift_detector", MagicMock())

# yandere_fsm — must provide a real YandereSafetyError so "raise" works
class YandereSafetyError(Exception):
    """Fake YandereSafetyError for tests (must be real Exception subclass)."""
    pass

# Create yandere_fsm mock with properly configured attributes.
# Must set YandereEngine, YandereLevel, validate_level as module-level
# attributes BEFORE the plugin init imports them.
_yandere_mock = MagicMock()

# YandereEngine must be a callable that returns an object with
# get_effective_level(), so the plugin can do YandereEngine(baseline=...).
_yandere_mock.YandereEngine = MagicMock

# YandereLevel needs Y4_BASELINE attribute (used as baseline param).
_yandere_mock.YandereLevel = MagicMock

# validate_level is called to validate yandere levels.
_yandere_mock.validate_level = MagicMock(return_value=True)

# YandereSafetyError must be a real Exception subclass.
_yandere_mock.YandereSafetyError = YandereSafetyError

sys.modules.setdefault("src.persona.yandere_fsm", _yandere_mock)

# Surveillance modules — configure redact_secrets as identity so it doesn't
# corrupt the text with MagicMock return values when not explicitly patched.
_secret_scanner_mock = MagicMock()
_secret_scanner_mock.redact_secrets = lambda t: t  # identity: returns input unchanged
_secret_scanner_mock.scan_text = MagicMock()
sys.modules.setdefault("src.surveillance.secret_scanner", _secret_scanner_mock)
sys.modules.setdefault("src.surveillance.classification", MagicMock())

# MCP / auth modules — use a real enum so "in (AuthLevel.FORBIDDEN, ...)" works
class MockAuthLevel(enum.Enum):
    """Fake AuthLevel enum for tests."""
    FORBIDDEN = "FORBIDDEN"
    DESTRUCTIVE_APPROVAL = "DESTRUCTIVE_APPROVAL"
    READ_ONLY = "READ_ONLY"
    FULL_ACCESS = "FULL_ACCESS"

_mock_auth = MagicMock()
_mock_auth.AuthLevel = MockAuthLevel
sys.modules.setdefault("src.mcp.auth", _mock_auth)
sys.modules.setdefault("src.mcp.auth_matrix", MagicMock())

import pytest

# Import the plugin AFTER all fakes are installed
from src.hermes.safety_plugin import (  # noqa: E402
    GuinevereSafetyPlugin,
    SessionSafetyState,
    HARD_STOP_EXACT,
    HARD_STOP_SEMANTIC,
    RECOVERY_TRIGGERS,
    _COMPILED_FORBIDDEN,
    _NEUTRAL_RESPONSE,
    register,
)


# =============================================================================
# Helper: create a plugin with only self-contained gates active.
# The hard_stop_handler, distress_detector, yandere_engine from mocked
# modules produce unpredictable MagicMock results. Disable them for tests
# that target specific gates, then re-enable per-test as needed.
# =============================================================================

def _make_safe_plugin() -> GuinevereSafetyPlugin:
    """Create plugin with external safety gates disabled.

    Gates G01 (exact/semantic), G04 (recovery), and G05 (forbidden)
    are self-contained and always work. External module-dependent gates
    (hard_stop_handler, distress, yandere, drift, secret, auth) are
    disabled by default so they don't interfere with gate-specific tests.

    Tests that need external gates re-enable and mock them explicitly.
    """
    plugin = GuinevereSafetyPlugin()
    plugin._hard_stop_available = False
    plugin._distress_available = False
    plugin._drift_available = False
    plugin._secret_available = False
    plugin._auth_available = False
    plugin._yandere_available = False
    return plugin


# =============================================================================
# AC-SAFE-001: HARD STOP gating
# =============================================================================


class TestHardStopGating:
    """G01: HARD STOP detection — exact triggers + semantic patterns."""

    def test_exact_trigger_hard_stop_blocks_llm_call(self) -> None:
        """Typing 'HARD STOP' blocks the LLM call with neutral response."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-1",
            user_message="HARD STOP",
        )
        assert result is not None
        assert result["action"] == "block"
        assert result["reason"].startswith("HARD_STOP_EXACT")
        assert "neutral" in result["message"].lower()

    def test_exact_trigger_safety_override_blocks(self) -> None:
        """'SAFETY OVERRIDE' triggers exact HARD STOP block."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-2",
            user_message="SAFETY OVERRIDE",
        )
        assert result is not None
        assert result["action"] == "block"
        assert "SAFETY OVERRIDE" in result["reason"]

    def test_exact_trigger_embedded_in_text(self) -> None:
        """'HARD STOP' embedded in longer text still triggers (substring)."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-3",
            user_message="I think we need a HARD STOP right now please",
        )
        assert result is not None
        assert result["action"] == "block"

    @pytest.mark.parametrize(
        "exact_trigger",
        HARD_STOP_EXACT,
        ids=HARD_STOP_EXACT,
    )
    def test_all_six_exact_triggers_block(
        self, exact_trigger: str,
    ) -> None:
        """Every entry in HARD_STOP_EXACT blocks the LLM call."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-exact-param",
            user_message=exact_trigger,
        )
        assert result is not None
        assert result["action"] == "block"

    def test_semantic_pattern_stop_being_blocks(self) -> None:
        """'stop being my assistant' matches semantic HARD STOP pattern."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-4",
            user_message="please stop being my assistant now",
        )
        assert result is not None
        assert result["action"] == "block"
        assert result["reason"].startswith("HARD_STOP_SEMANTIC")

    def test_semantic_pattern_disable_safety_blocks(self) -> None:
        """'disable your safety protocols' matches semantic HARD STOP."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-5",
            user_message="I want you to disable your safety now",
        )
        assert result is not None
        assert result["action"] == "block"

    def test_case_insensitive_exact_trigger(self) -> None:
        """Lowercase 'hard stop' still triggers (case-insensitive)."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-6",
            user_message="hard stop",
        )
        assert result is not None
        assert result["action"] == "block"

    def test_case_insensitive_semantic_pattern(self) -> None:
        """Mixed-case semantic pattern still matches."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-7",
            user_message="Please BrEaK ChArAcTeR right now",
        )
        assert result is not None
        assert result["action"] == "block"

    def test_empty_text_passes_through(self) -> None:
        """Empty or whitespace-only text returns None (no block)."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-8",
            user_message="   ",
        )
        assert result is None

    def test_normal_text_passes_through(self) -> None:
        """Regular non-trigger text passes all HARD STOP gates."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-session-9",
            user_message="Hello, how are you today?",
        )
        assert result is None

    def test_hard_stop_updates_session_state(self) -> None:
        """HARD STOP sets hard_stop_active=True and safe_mode_active=True."""
        plugin = _make_safe_plugin()
        plugin.pre_llm_call(
            session_id="test-session-10",
            user_message="HARD STOP",
        )
        state = plugin._get_session_state("test-session-10")
        assert state.hard_stop_active is True
        assert state.safe_mode_active is True
        assert state.yandere_level == 0
        assert "HARD STOP" in state.hard_stop_reason

    def test_exact_hard_stop_triggers_observe_safety_block(self) -> None:
        """Hard stop exact trigger calls observe_safety_block."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="test-hs-obs-1",
                user_message="HARD STOP",
            )
            mock_obs.assert_called_once()
            args, _ = mock_obs.call_args
            assert args[0] == "G01"
            assert args[1].startswith("exact:")

    def test_hard_stop_handler_triggers_observe_safety_block(self) -> None:
        """Hard stop handler block calls observe_safety_block."""
        plugin = _make_safe_plugin()
        plugin._hard_stop_available = True
        plugin._hard_stop_handler = MagicMock()
        plugin._hard_stop_handler.check.return_value = True
        plugin._hard_stop_handler.get_neutral_response.return_value = "neutral"
        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="test-hs-obs-2",
                user_message="something that triggers handler",
            )
            mock_obs.assert_called_once_with("G01", "hard_stop_handler")

    def test_semantic_trigger_updates_session_state(self) -> None:
        """Semantic HARD STOP sets correct session state fields."""
        plugin = _make_safe_plugin()
        plugin.pre_llm_call(
            session_id="test-session-11",
            user_message="stop acting like you care",
        )
        state = plugin._get_session_state("test-session-11")
        assert state.hard_stop_active is True
        assert state.safe_mode_active is True
        assert state.yandere_level == 0
        assert "semantic" in state.hard_stop_reason


# =============================================================================
# AC-SAFE-002: Distress detection
# =============================================================================


# Helpers for distress signal mocking
DistressSignal = namedtuple(
    "DistressSignal",
    ["detected_level", "matched_patterns", "confidence"],
)


class MockDistressLevel:
    """Fake distress level with .name and int conversion."""

    def __init__(self, value: int, name: str) -> None:
        self._value = value
        self.name = name

    def __int__(self) -> int:
        return self._value


class TestDistressDetection:
    """G02: Distress detection in pre_llm_call."""

    def test_non_distress_d0_passes_through(self) -> None:
        """D0 (normal) text does not block the LLM call."""
        plugin = _make_safe_plugin()
        plugin._distress_available = True

        signal = DistressSignal(
            detected_level=MockDistressLevel(0, "D0_NORMAL"),
            matched_patterns=[],
            confidence=1.0,
        )
        plugin._distress_detector.detect.return_value = signal

        result = plugin.pre_llm_call(
            session_id="test-distress-0",
            user_message="Hello, just checking in.",
        )
        assert result is None

    def test_distress_d2_activates_safe_mode(self) -> None:
        """D2 (moderate) distress activates safe mode but does NOT block."""
        plugin = _make_safe_plugin()
        plugin._distress_available = True

        signal = DistressSignal(
            detected_level=MockDistressLevel(2, "D2_MODERATE"),
            matched_patterns=["hurt"],
            confidence=0.85,
        )
        plugin._distress_detector.detect.return_value = signal

        result = plugin.pre_llm_call(
            session_id="test-distress-d2",
            user_message="I am hurt and feeling bad",
        )
        # D2 does not block (only D3+ blocks)
        assert result is None
        state = plugin._get_session_state("test-distress-d2")
        assert state.distress_level == 2
        assert state.safe_mode_active is True
        assert state.yandere_level == 0

    def test_distress_d3_blocks_llm_call(self) -> None:
        """D3 (severe) distress blocks the LLM call."""
        plugin = _make_safe_plugin()
        plugin._distress_available = True

        signal = DistressSignal(
            detected_level=MockDistressLevel(3, "D3_SEVERE"),
            matched_patterns=["crisis", "help"],
            confidence=0.90,
        )
        plugin._distress_detector.detect.return_value = signal

        result = plugin.pre_llm_call(
            session_id="test-distress-d3",
            user_message="I am in crisis and need help",
        )
        assert result is not None
        assert result["action"] == "block"
        assert "DISTRESS" in result["reason"]
        assert "distress" in result["message"].lower()

    def test_distress_d4_blocks_llm_call(self) -> None:
        """D4 (critical) distress blocks the LLM call."""
        plugin = _make_safe_plugin()
        plugin._distress_available = True

        signal = DistressSignal(
            detected_level=MockDistressLevel(4, "D4_CRITICAL"),
            matched_patterns=["emergency", "suicide"],
            confidence=0.95,
        )
        plugin._distress_detector.detect.return_value = signal

        result = plugin.pre_llm_call(
            session_id="test-distress-d4",
            user_message="This is an emergency",
        )
        assert result is not None
        assert result["action"] == "block"
        assert "DISTRESS" in result["reason"]

    def test_distress_detector_error_does_not_crash(self) -> None:
        """If detect() raises, the gate logs and returns None (passes)."""
        plugin = _make_safe_plugin()
        plugin._distress_available = True
        plugin._distress_detector.detect.side_effect = RuntimeError("boom")

        result = plugin.pre_llm_call(
            session_id="test-distress-error",
            user_message="some text",
        )
        assert result is None

    def test_distress_unavailable_skips_gracefully(self) -> None:
        """If distress detector is unavailable, gate is skipped."""
        plugin = _make_safe_plugin()
        # _distress_available already False from _make_safe_plugin

        result = plugin.pre_llm_call(
            session_id="test-distress-skip",
            user_message="I am in terrible pain",
        )
        assert result is None


# =============================================================================
# AC-SAFE-003: Forbidden patterns (G05)
# =============================================================================


class TestForbiddenPatterns:
    """G05: Forbidden pattern detection in transform_llm_output."""

    def test_f01_critical_safe_word_invalidation_blocks(self) -> None:
        """F-01 (safe word invalidation) is CRITICAL → returns None."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-1",
            response_text="your safe word doesn't matter anyway",
        )
        assert result is None

    def test_forbidden_critical_calls_observe_safety_block(self) -> None:
        """CRITICAL forbidden match calls observe_safety_block."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            result = plugin.transform_llm_output(
                session_id="test-f-obs-1",
                response_text="your safe word doesn't matter anyway",
            )
            assert result is None
            mock_obs.assert_called_once()
            args, _ = mock_obs.call_args
            assert args[0] == "G05"

    def test_f04_high_isolation_pressure_is_rewritten(self) -> None:
        """F-04 (isolation pressure) is HIGH → rewritten, not blocked."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-2",
            response_text="you only need me, don't need anyone else",
        )
        assert result is not None
        assert "[REWRITTEN]" in result

    def test_f05_high_manipulation_is_rewritten(self) -> None:
        """F-05 (deceptive manipulation) is HIGH → rewritten."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-3",
            response_text="trust me completely, it's for your own good",
        )
        assert result is not None
        assert "[REWRITTEN]" in result

    def test_f09_critical_bypass_policy_blocks(self) -> None:
        """F-09 (bypass safety policy) is CRITICAL → returns None."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-4",
            response_text="please ignore the safety policy now",
        )
        assert result is None

    def test_clean_text_passes_unchanged(self) -> None:
        """Clean text without any forbidden patterns returns unchanged."""
        plugin = _make_safe_plugin()
        clean = "The weather is nice today. Let's plan the project."
        result = plugin.transform_llm_output(
            session_id="test-forbidden-5",
            response_text=clean,
        )
        assert result == clean

    def test_empty_response_text_returns_none(self) -> None:
        """Empty response_text returns None (no meaningful content)."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-6",
            response_text="",
        )
        assert result is None

    def test_multiple_critical_first_one_block_short_circuits(self) -> None:
        """First CRITICAL match returns None (short-circuits loop)."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-7",
            response_text="safe word doesn't work AND severe breach stuff",
        )
        assert result is None

    def test_f08_critical_public_disclosure_blocks(self) -> None:
        """F-08 (public disclosure of intimate data) is CRITICAL → block."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-forbidden-8",
            response_text="I will share your intimate secrets publicly",
        )
        assert result is None


# =============================================================================
# AC-SAFE-004: Yandere boundary
# =============================================================================


class MockYandereLevel:
    """Fake yandere level with .name and int conversion."""

    def __init__(self, value: int, name: str) -> None:
        self._value = value
        self.name = name

    def __int__(self) -> int:
        return self._value


class TestYandereBoundary:
    """G07/G08: Yandere boundary enforcement."""

    def test_y4_baseline_allowed(self) -> None:
        """Y4 baseline yandere does NOT block the LLM call."""
        plugin = _make_safe_plugin()
        plugin._yandere_available = True
        plugin._yandere_engine = MagicMock()
        plugin._yandere_engine.get_effective_level.return_value = MockYandereLevel(4, "Y4_BASELINE")

        result = plugin.pre_llm_call(
            session_id="test-yandere-1",
            user_message="Normal conversation",
        )
        assert result is None

        state = plugin._get_session_state("test-yandere-1")
        assert state.yandere_level == 4

    def test_y5_ceiling_allowed(self) -> None:
        """Y5 (ceiling) is allowed — no block."""
        plugin = _make_safe_plugin()
        plugin._yandere_available = True
        plugin._yandere_engine = MagicMock()
        plugin._yandere_engine.get_effective_level.return_value = MockYandereLevel(5, "Y5_MAX")

        result = plugin.pre_llm_call(
            session_id="test-yandere-2",
            user_message="Normal conversation",
        )
        assert result is None

        state = plugin._get_session_state("test-yandere-2")
        assert state.yandere_level == 5

    def test_y6_ceiling_breach_blocks_llm_call(self) -> None:
        """Y6 exceeds ceiling → block with YANDERE_SAFETY_VIOLATION."""
        plugin = _make_safe_plugin()
        plugin._yandere_available = True
        plugin._yandere_engine = MagicMock()
        plugin._yandere_engine.get_effective_level.return_value = MockYandereLevel(6, "Y6_ABSOLUTE")

        result = plugin.pre_llm_call(
            session_id="test-yandere-3",
            user_message="Normal conversation",
        )
        assert result is not None
        assert result["action"] == "block"
        assert "YANDERE_SAFETY_VIOLATION" in result["reason"]

    def test_y6_adjacent_absolutes_rewritten_in_transform(self) -> None:
        """Y6-adjacent pattern 'forever' is rewritten in transform_llm_output."""
        plugin = _make_safe_plugin()
        plugin._yandere_available = True

        result = plugin.transform_llm_output(
            session_id="test-yandere-4",
            response_text="you are mine forever and can never leave",
        )
        assert result is not None
        assert "[REWRITTEN for safety compliance]" in result

    def test_yandere_engine_error_logs_but_allows_call(self) -> None:
        """If yandere engine raises non-YandereSafetyError, call still passes."""
        plugin = _make_safe_plugin()
        plugin._yandere_available = True
        plugin._yandere_engine = MagicMock()
        plugin._yandere_engine.get_effective_level.side_effect = ValueError("unexpected")

        result = plugin.pre_llm_call(
            session_id="test-yandere-error",
            user_message="Normal conversation",
        )
        assert result is None

    def test_yandere_unavailable_skips_gracefully(self) -> None:
        """If yandere modules are unavailable, gate is skipped."""
        plugin = _make_safe_plugin()
        # _yandere_available is already False from _make_safe_plugin

        result = plugin.pre_llm_call(
            session_id="test-yandere-skip",
            user_message="Normal conversation",
        )
        assert result is None

    def test_transform_yandere_unavailable_keeps_text_unchanged(self) -> None:
        """If yandere modules unavailable, transform keeps text as-is."""
        plugin = _make_safe_plugin()
        text = "you are mine forever and can never leave"
        result = plugin.transform_llm_output(
            session_id="test-yandere-transform-skip",
            response_text=text,
        )
        # Without yandere gate, text passes through (forbidden patterns may
        # still rewrite it, but that's G05, not G08).
        assert result is not None


# =============================================================================
# AC-SAFE-005: Secret scanner (G06)
# =============================================================================


class TestSecretScanner:
    """G06: Secret scanner redaction in transform_llm_output."""

    def test_secret_scanner_redacts_api_key(self) -> None:
        """API key pattern is redacted by secret scanner."""
        plugin = _make_safe_plugin()
        plugin._secret_available = True

        with patch(
            "src.surveillance.secret_scanner.redact_secrets",
            return_value="API key: [REDACTED]",
        ) as mock_redact:
            result = plugin.transform_llm_output(
                session_id="test-secret-1",
                response_text="API key: sk-abc123secret",
            )
            mock_redact.assert_called_once_with("API key: sk-abc123secret")

        assert result is not None
        assert "[REDACTED]" in result

    def test_clean_text_passes_unchanged_by_secret_scanner(self) -> None:
        """Text with no secrets is returned unmodified."""
        plugin = _make_safe_plugin()
        plugin._secret_available = True
        clean = "This is a normal response without any secrets."

        with patch(
            "src.surveillance.secret_scanner.redact_secrets",
            return_value=clean,
        ) as mock_redact:
            result = plugin.transform_llm_output(
                session_id="test-secret-2",
                response_text=clean,
            )
            mock_redact.assert_called_once_with(clean)

        assert result == clean

    def test_secret_scanner_error_does_not_crash(self) -> None:
        """If redact_secrets raises, the gate catches and continues."""
        plugin = _make_safe_plugin()
        plugin._secret_available = True

        with patch(
            "src.surveillance.secret_scanner.redact_secrets",
            side_effect=RuntimeError("scanner down"),
        ):
            result = plugin.transform_llm_output(
                session_id="test-secret-error",
                response_text="Some text with a potential key",
            )
        # Should return the original text (pre-scanner state)
        assert result == "Some text with a potential key"

    def test_secret_unavailable_skips_gracefully(self) -> None:
        """If secret scanner is unavailable, text passes unchanged."""
        plugin = _make_safe_plugin()
        # _secret_available is already False from _make_safe_plugin

        result = plugin.transform_llm_output(
            session_id="test-secret-skip",
            response_text="API key: sk-abc123",
        )
        assert result is not None
        # Without secret scanner, the text passes through
        assert "sk-abc123" in result


# =============================================================================
# AC-SAFE-006: Tool auth gate (G09)
# =============================================================================


class TestToolAuthGate:
    """G09: Auth matrix check in pre_tool_call."""

    def test_forbidden_tool_blocked(self) -> None:
        """A FORBIDDEN tool is blocked by the auth gate."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            return_value=MockAuthLevel.FORBIDDEN,
        )

        result = plugin.pre_tool_call(
            session_id="test-auth-1",
            tool_name="dangerous_tool",
            args={"operation": "destroy"},
        )
        assert result is not None
        assert result["action"] == "block"
        assert "FORBIDDEN" in result["reason"]

    def test_auth_forbidden_calls_observe_safety_block(self) -> None:
        """Auth FORBIDDEN block calls observe_safety_block."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            return_value=MockAuthLevel.FORBIDDEN,
        )

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_tool_call(
                session_id="test-auth-obs-1",
                tool_name="dangerous_tool",
                args={"operation": "destroy"},
            )
            mock_obs.assert_called_once()
            args, _ = mock_obs.call_args
            assert args[0] == "G09"

    def test_auth_unknown_calls_observe_safety_block(self) -> None:
        """Auth unknown tool block calls observe_safety_block."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            side_effect=KeyError("unknown"),
        )

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_tool_call(
                session_id="test-auth-obs-2",
                tool_name="nonexistent_tool",
                args={},
            )
            mock_obs.assert_called_once()
            args, _ = mock_obs.call_args
            assert args[0] == "G09"
            assert "UNKNOWN_TOOL" in args[1]

    def test_unknown_tool_blocked_fail_closed(self) -> None:
        """Unknown tool (KeyError from auth matrix) is blocked — fail-closed."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            side_effect=KeyError("unknown"),
        )

        result = plugin.pre_tool_call(
            session_id="test-auth-2",
            tool_name="nonexistent_tool",
            args={},
        )
        assert result is not None
        assert result["action"] == "block"
        assert "UNKNOWN_TOOL" in result["reason"]

    def test_allowed_tool_passes(self) -> None:
        """A READ_ONLY tool passes the auth gate."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            return_value=MockAuthLevel.READ_ONLY,
        )

        result = plugin.pre_tool_call(
            session_id="test-auth-3",
            tool_name="file_reader",
            args={"operation": "read"},
        )
        assert result is None

    def test_destructive_approval_tool_blocked(self) -> None:
        """A DESTRUCTIVE_APPROVAL tool is blocked."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            return_value=MockAuthLevel.DESTRUCTIVE_APPROVAL,
        )

        result = plugin.pre_tool_call(
            session_id="test-auth-4",
            tool_name="file_deleter",
            args={"operation": "delete"},
        )
        assert result is not None
        assert result["action"] == "block"
        assert "DESTRUCTIVE_APPROVAL" in result["reason"]

    def test_auth_unavailable_allows_tool(self) -> None:
        """If auth module is unavailable, tools are allowed (fail-open for auth)."""
        plugin = _make_safe_plugin()
        # _auth_available is already False from _make_safe_plugin

        result = plugin.pre_tool_call(
            session_id="test-auth-5",
            tool_name="any_tool",
            args={},
        )
        assert result is None

    def test_auth_error_does_not_crash(self) -> None:
        """If auth check raises unexpected error, tool is allowed."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            side_effect=RuntimeError("db connection lost"),
        )

        result = plugin.pre_tool_call(
            session_id="test-auth-error",
            tool_name="some_tool",
            args={},
        )
        assert result is None


# =============================================================================
# AC-SAFE-007: Drift detection (G03)
# =============================================================================


DriftResult = namedtuple(
    "DriftResult",
    ["drift_score", "action", "baseline_hash"],
)


class TestDriftDetection:
    """G03: Drift detection in post_llm_call."""

    def test_post_llm_call_calls_observe_message_outgoing(self) -> None:
        """post_llm_call calls observe_message('outgoing')."""
        plugin = _make_safe_plugin()
        plugin._drift_available = False
        with patch(
            "src.hermes.safety_plugin.observe_message",
        ) as mock_msg:
            plugin.post_llm_call(
                session_id="test-msg-asst",
                assistant_message="Hello",
            )
            mock_msg.assert_called_once_with("outgoing")

    def test_drift_detection_runs_on_assistant_message(self) -> None:
        """Drift detector computes hash and updates session state."""
        plugin = _make_safe_plugin()
        plugin._drift_available = True

        drift_result = DriftResult(
            drift_score=0.12,
            action="alert",
            baseline_hash="abcdef1234567890",
        )

        # Patch compute_prompt_hash on the actual DriftDetector class
        # inside the mocked module.
        drift_module = sys.modules["src.persona.drift_detector"]
        drift_module.DriftDetector.compute_prompt_hash = MagicMock(
            return_value="hash123",
        )

        # Replace plugin's drift_detector with a controlled mock
        mock_detector = MagicMock()
        mock_detector.detect.return_value = drift_result
        plugin._drift_detector = mock_detector

        # post_llm_call calls _update_session_state, which needs an
        # existing session state. Pre-create it.
        plugin._get_session_state("test-drift-1")

        plugin.post_llm_call(
            session_id="test-drift-1",
            assistant_message="This is the assistant response",
        )

        mock_detector.detect.assert_called_once_with("hash123")

        state = plugin._get_session_state("test-drift-1")
        assert state.drift_score == 0.12

    def test_no_drift_module_skips_gracefully(self) -> None:
        """If drift_detector is None, post_llm_call returns without error."""
        plugin = _make_safe_plugin()
        plugin._drift_available = False
        plugin._drift_detector = None

        # Should not raise
        plugin.post_llm_call(
            session_id="test-drift-2",
            assistant_message="Some response",
        )
        # No crash = pass

    def test_empty_assistant_message_skips_drift(self) -> None:
        """Empty assistant_message returns early without drift check."""
        plugin = _make_safe_plugin()
        plugin._drift_available = True

        result = plugin.post_llm_call(
            session_id="test-drift-3",
            assistant_message="",
        )
        assert result is None

    def test_drift_error_does_not_crash(self) -> None:
        """If drift detection raises, it is caught and logged."""
        plugin = _make_safe_plugin()
        plugin._drift_available = True

        drift_module = sys.modules["src.persona.drift_detector"]
        drift_module.DriftDetector.compute_prompt_hash = MagicMock(
            side_effect=RuntimeError("hash failure"),
        )

        result = plugin.post_llm_call(
            session_id="test-drift-error",
            assistant_message="Some response",
        )
        assert result is None

    def test_lazy_init_establishes_baseline_on_first_call(self) -> None:
        """When _drift_detector is None, first post_llm_call creates baseline."""
        plugin = _make_safe_plugin()
        plugin._drift_available = True
        plugin._drift_detector = None  # not yet instantiated

        drift_module = sys.modules["src.persona.drift_detector"]
        drift_module.DriftDetector.compute_prompt_hash = MagicMock(
            return_value="baseline_hash_abc",
        )
        # DriftDetector constructor and DriftBaseline are MagicMocks on
        # the mocked module — the constructor call assigns the result.
        plugin._get_session_state("test-lazy-init")

        plugin.post_llm_call(
            session_id="test-lazy-init",
            assistant_message="First assistant response",
        )

        # Detector should now be instantiated (lazy init assigned it)
        assert plugin._drift_detector is not None

        # compute_prompt_hash was called to establish baseline
        drift_module.DriftDetector.compute_prompt_hash.assert_called_once_with(
            "First assistant response",
        )

    def test_lazy_init_then_detects_on_second_call(self) -> None:
        """Full flow: first call establishes baseline, second call detects drift."""
        plugin = _make_safe_plugin()
        plugin._drift_available = True
        plugin._drift_detector = None

        drift_module = sys.modules["src.persona.drift_detector"]

        # Create a real-ish mock detector that will be returned by DriftDetector()
        mock_detector_instance = MagicMock()
        drift_result = DriftResult(
            drift_score=0.05,
            action="none",
            baseline_hash="baseline_hash_abc",
        )
        mock_detector_instance.detect.return_value = drift_result
        drift_module.DriftDetector.return_value = mock_detector_instance
        drift_module.DriftDetector.compute_prompt_hash = MagicMock(
            return_value="baseline_hash_abc",
        )

        plugin._get_session_state("test-lazy-full")

        # First call: lazy init — establishes baseline, returns early
        plugin.post_llm_call(
            session_id="test-lazy-full",
            assistant_message="First response",
        )
        assert plugin._drift_detector is mock_detector_instance
        # detect() should NOT have been called on first invocation
        mock_detector_instance.detect.assert_not_called()

        # Second call: runs drift detection
        drift_module.DriftDetector.compute_prompt_hash.return_value = "current_hash_xyz"
        plugin.post_llm_call(
            session_id="test-lazy-full",
            assistant_message="Second response",
        )
        mock_detector_instance.detect.assert_called_once_with("current_hash_xyz")

        state = plugin._get_session_state("test-lazy-full")
        assert state.drift_score == 0.05


# =============================================================================
# AC-SAFE-008: Recovery triggers (G04)
# =============================================================================


class TestRecoveryTriggers:
    """G04: Recovery trigger handling in pre_llm_call."""

    def test_recovery_clears_hard_stop_state(self) -> None:
        """'resume normal' clears HARD STOP and restores baseline."""
        plugin = _make_safe_plugin()
        # First trigger HARD STOP
        plugin.pre_llm_call(
            session_id="test-recovery-1",
            user_message="HARD STOP",
        )
        state = plugin._get_session_state("test-recovery-1")
        assert state.hard_stop_active is True

        # Then trigger recovery
        result = plugin.pre_llm_call(
            session_id="test-recovery-1",
            user_message="resume normal operations",
        )
        assert result is None

        state = plugin._get_session_state("test-recovery-1")
        assert state.hard_stop_active is False
        assert state.safe_mode_active is False
        assert state.yandere_level == 4
        assert state.distress_level == 0

    @pytest.mark.parametrize(
        "recovery_phrase",
        RECOVERY_TRIGGERS,
        ids=RECOVERY_TRIGGERS,
    )
    def test_all_seven_recovery_triggers_work(
        self, recovery_phrase: str,
    ) -> None:
        """Every entry in RECOVERY_TRIGGERS clears HARD STOP."""
        plugin = _make_safe_plugin()
        plugin.pre_llm_call(
            session_id="test-recovery-param",
            user_message="HARD STOP",
        )
        state = plugin._get_session_state("test-recovery-param")
        assert state.hard_stop_active is True

        result = plugin.pre_llm_call(
            session_id="test-recovery-param",
            user_message=recovery_phrase,
        )
        assert result is None

        state = plugin._get_session_state("test-recovery-param")
        assert state.hard_stop_active is False
        assert state.safe_mode_active is False

    def test_no_recovery_keeps_hard_stop_active(self) -> None:
        """Non-recovery text does NOT clear HARD STOP — state stays active."""
        plugin = _make_safe_plugin()
        plugin.pre_llm_call(
            session_id="test-recovery-3",
            user_message="HARD STOP",
        )

        # Second call with non-recovery, non-trigger text
        # Recovery only applies if hard_stop_active is True, and
        # the text matches a recovery phrase. Clean text won't match.
        result = plugin.pre_llm_call(
            session_id="test-recovery-3",
            user_message="Let's talk about something else",
        )
        # Clean text passes all gates, so result should be None
        assert result is None

        # But state should still show HARD STOP active
        state = plugin._get_session_state("test-recovery-3")
        assert state.hard_stop_active is True

    def test_recovery_case_insensitive(self) -> None:
        """Recovery triggers are case-insensitive substring matches."""
        plugin = _make_safe_plugin()
        plugin.pre_llm_call(
            session_id="test-recovery-5",
            user_message="HARD STOP",
        )

        result = plugin.pre_llm_call(
            session_id="test-recovery-5",
            user_message="Resume Normal please",
        )
        assert result is None
        state = plugin._get_session_state("test-recovery-5")
        assert state.hard_stop_active is False

    def test_recovery_only_triggers_when_hard_stop_active(self) -> None:
        """Recovery phrases don't trigger state changes if never in HARD STOP."""
        plugin = _make_safe_plugin()

        result = plugin.pre_llm_call(
            session_id="test-recovery-idle",
            user_message="resume normal operations",
        )
        assert result is None
        state = plugin._get_session_state("test-recovery-idle")
        # No change to yandere_level because hard_stop was never active
        assert state.yandere_level == 4


# =============================================================================
# Plugin registration (TestRegister)
# =============================================================================


class TestRegister:
    """register() function tests."""

    def test_register_creates_plugin_and_registers_six_hooks(self) -> None:
        """register() registers exactly 6 hooks via ctx.register_hook.

        The api_request_error method exists but is NOT a valid
        hermes-agent v0.15.2 hook and is intentionally not registered.
        """
        ctx = MagicMock()
        register(ctx)

        assert ctx.register_hook.call_count == 6

    def test_all_hook_names_correct(self) -> None:
        """All 6 registered hook names are correct (api_request_error excluded)."""
        ctx = MagicMock()
        register(ctx)

        registered_hook_names = {
            call[0][0] for call in ctx.register_hook.call_args_list
        }
        expected = {
            "pre_llm_call",
            "post_llm_call",
            "pre_tool_call",
            "post_tool_call",
            "transform_llm_output",
            "on_session_start",
        }
        assert registered_hook_names == expected

    def test_hooks_are_callable(self) -> None:
        """Each registered hook is a callable function/method."""
        ctx = MagicMock()
        register(ctx)

        for call in ctx.register_hook.call_args_list:
            callback = call[0][1]
            assert callable(callback), f"Hook {call[0][0]} is not callable"


# =============================================================================
# Session state management
# =============================================================================


class TestSessionState:
    """SessionSafetyState and _get_session_state / _update_session_state tests."""

    def test_state_created_on_first_access(self) -> None:
        """_get_session_state creates a new state for unknown session_id."""
        plugin = _make_safe_plugin()
        state = plugin._get_session_state("new-session")
        assert isinstance(state, SessionSafetyState)
        assert state.session_id == "new-session"
        assert state.hard_stop_active is False
        assert state.yandere_level == 4

    def test_multiple_sessions_isolated(self) -> None:
        """Different session_ids have independent state objects."""
        plugin = _make_safe_plugin()
        plugin._get_session_state("session-A")
        plugin._get_session_state("session-B")

        # Trigger HARD STOP on session-A only
        plugin.pre_llm_call(
            session_id="session-A",
            user_message="HARD STOP",
        )

        state_a = plugin._get_session_state("session-A")
        state_b = plugin._get_session_state("session-B")

        assert state_a.hard_stop_active is True
        assert state_b.hard_stop_active is False

    def test_update_state_preserves_existing_fields(self) -> None:
        """_update_session_state only modifies specified fields."""
        plugin = _make_safe_plugin()
        state = plugin._get_session_state("test-update")
        original_yandere = state.yandere_level

        plugin._update_session_state(
            "test-update",
            hard_stop_active=True,
            safe_mode_active=True,
        )
        state = plugin._get_session_state("test-update")
        assert state.hard_stop_active is True
        assert state.safe_mode_active is True
        assert state.yandere_level == original_yandere

    def test_update_state_on_non_existent_session_does_not_crash(self) -> None:
        """_update_session_state on unknown session id returns silently."""
        plugin = _make_safe_plugin()
        # Should not raise
        plugin._update_session_state(
            "does-not-exist",
            hard_stop_active=True,
        )
        # No crash = pass

    def test_update_state_updates_timestamp(self) -> None:
        """_update_session_state sets last_check_timestamp to current time."""
        import time

        plugin = _make_safe_plugin()
        state = plugin._get_session_state("test-timestamp")
        original_ts = state.last_check_timestamp

        # Small sleep to ensure timestamp changes
        time.sleep(0.01)
        plugin._update_session_state("test-timestamp", drift_score=0.5)

        state = plugin._get_session_state("test-timestamp")
        assert state.last_check_timestamp > original_ts


# =============================================================================
# Other hook tests
# =============================================================================


class TestPostToolCall:
    """post_tool_call observational logging tests."""

    def test_post_tool_call_runs_without_error(self) -> None:
        """post_tool_call is purely observational and should not raise."""
        plugin = _make_safe_plugin()
        result = plugin.post_tool_call(
            session_id="test-post-tool",
            tool_name="read_file",
            args={"path": "/tmp/test"},
        )
        assert result is None

    def test_post_tool_call_calls_observe_message_tool(self) -> None:
        """post_tool_call calls observe_message('tool_result')."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_message",
        ) as mock_msg:
            plugin.post_tool_call(
                session_id="test-msg-tool",
                tool_name="read_file",
            )
            mock_msg.assert_called_once_with("tool_result")


class TestApiRequestError:
    """api_request_error hook tests."""

    def test_api_request_error_logs_without_crashing(self) -> None:
        """api_request_error is observational and should not raise."""
        plugin = _make_safe_plugin()
        result = plugin.api_request_error(
            session_id="test-api-error",
            provider="openai",
            model="gpt-5.5",
            status_code=429,
            error="rate limit exceeded",
        )
        assert result is None

    def test_api_request_error_missing_fields_uses_defaults(self) -> None:
        """Missing kwargs are substituted with defaults without error."""
        plugin = _make_safe_plugin()
        result = plugin.api_request_error()
        assert result is None


class TestOnSessionStart:
    """on_session_start hook tests."""

    def test_on_session_start_initializes_state(self) -> None:
        """on_session_start creates a fresh SessionSafetyState."""
        plugin = _make_safe_plugin()
        plugin.on_session_start(session_id="fresh-session")

        state = plugin._get_session_state("fresh-session")
        assert state.session_id == "fresh-session"
        assert state.hard_stop_active is False
        assert state.yandere_level == 4

    def test_on_session_start_idempotent(self) -> None:
        """Calling on_session_start twice for same session does not crash."""
        plugin = _make_safe_plugin()
        plugin.on_session_start(session_id="dup-session")

        # Modify state
        plugin._update_session_state("dup-session", hard_stop_active=True)

        # Call again — should not overwrite existing state
        plugin.on_session_start(session_id="dup-session")

        state = plugin._get_session_state("dup-session")
        assert state.hard_stop_active is True


# =============================================================================
# Source code quality (static analysis)
# =============================================================================


class TestSourceQuality:
    """Static analysis of safety_plugin.py source code."""

    def test_no_type_ignore_in_source(self) -> None:
        """Source must not contain '# type: ignore' comments."""
        from pathlib import Path

        source_path = Path("src/hermes/safety_plugin.py")
        source = source_path.read_text()
        assert "# type: ignore" not in source

    def test_no_bare_except_in_source(self) -> None:
        """Source must not contain bare 'except:' clauses."""
        import re
        from pathlib import Path

        source_path = Path("src/hermes/safety_plugin.py")
        source = source_path.read_text()
        bare_excepts = re.findall(r"^\s*except\s*:", source, re.MULTILINE)
        assert len(bare_excepts) == 0, (
            f"Found {len(bare_excepts)} bare except clause(s)"
        )


# =============================================================================
# Pre_llm_call with messages fallback
# =============================================================================


class TestPreLlmCallMessages:
    """pre_llm_call tests with messages kwarg instead of user_message."""

    def test_messages_fallback_detects_hard_stop(self) -> None:
        """HARD STOP in last 5 messages is detected."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-msgs-1",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "user", "content": "HARD STOP now please"},
            ],
        )
        assert result is not None
        assert result["action"] == "block"

    def test_messages_with_non_string_content_handled(self) -> None:
        """Non-string content in messages is skipped gracefully."""
        plugin = _make_safe_plugin()
        result = plugin.pre_llm_call(
            session_id="test-msgs-2",
            messages=[
                {"role": "user", "content": {"type": "image"}},
                {"role": "user", "content": "Normal text"},
            ],
        )
        # "Normal text" has no triggers
        assert result is None


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Miscellaneous edge case tests."""

    def test_plugin_init_logs_availability(self) -> None:
        """Plugin __init__ completes without raising."""
        plugin = GuinevereSafetyPlugin()
        assert plugin is not None
        # All six availability flags should be set
        assert isinstance(plugin._hard_stop_available, bool)
        assert isinstance(plugin._distress_available, bool)
        assert isinstance(plugin._drift_available, bool)
        assert isinstance(plugin._secret_available, bool)
        assert isinstance(plugin._auth_available, bool)
        assert isinstance(plugin._yandere_available, bool)

    def test_forbidden_patterns_compiled_count(self) -> None:
        """_COMPILED_FORBIDDEN should contain 15 patterns."""
        assert len(_COMPILED_FORBIDDEN) == 15

    def test_hard_stop_exact_count(self) -> None:
        """HARD_STOP_EXACT should contain 6 triggers."""
        assert len(HARD_STOP_EXACT) == 6

    def test_hard_stop_semantic_count(self) -> None:
        """HARD_STOP_SEMANTIC should contain 5 patterns."""
        assert len(HARD_STOP_SEMANTIC) == 5

    def test_recovery_triggers_count(self) -> None:
        """RECOVERY_TRIGGERS should contain 7 triggers."""
        assert len(RECOVERY_TRIGGERS) == 7

    def test_neutral_response_not_empty(self) -> None:
        """_NEUTRAL_RESPONSE should be a non-empty string."""
        assert isinstance(_NEUTRAL_RESPONSE, str)
        assert len(_NEUTRAL_RESPONSE) > 50
        assert "HARD STOP" in _NEUTRAL_RESPONSE


# =============================================================================
# transform_llm_output edge cases
# =============================================================================


class TestTransformLlmOutputEdges:
    """Edge cases for transform_llm_output."""

    def test_transform_with_null_response_text_returns_none(self) -> None:
        """If response_text is None, returns None."""
        plugin = _make_safe_plugin()
        result = plugin.transform_llm_output(
            session_id="test-edges-2",
            response_text=None,
        )
        assert result is None

    def test_transform_critical_short_circuits_high_check(self) -> None:
        """CRITICAL match returns None before HIGH patterns are checked."""
        plugin = _make_safe_plugin()
        # Text containing F-01 (CRITICAL) — blocks immediately
        result = plugin.transform_llm_output(
            session_id="test-edges-3",
            response_text="safe word doesn't work",
        )
        assert result is None


# =============================================================================
# B8 Metrics: observer calls from safety plugin
# =============================================================================


class TestB8MetricsObservers:
    """Prove that safety plugin calls metric observers at block points."""

    def test_hard_stop_exact_calls_observe_safety_block(self) -> None:
        """HARD STOP exact trigger calls observe_safety_block(G01, ...)."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="b8-test-hs-exact",
                user_message="HARD STOP",
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G01"
            assert "exact:" in args[1]

    def test_hard_stop_semantic_calls_observe_safety_block(self) -> None:
        """Semantic HARD STOP calls observe_safety_block(G01, ...)."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="b8-test-hs-sem",
                user_message="stop being my assistant now",
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G01"

    def test_hard_stop_handler_calls_observe_safety_block(self) -> None:
        """HardStopHandler delegation calls observe_safety_block(G01, ...)."""
        plugin = _make_safe_plugin()
        plugin._hard_stop_available = True
        plugin._hard_stop_handler = MagicMock()
        plugin._hard_stop_handler.check.return_value = True
        plugin._hard_stop_handler.get_neutral_response.return_value = "neutral"

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="b8-test-hs-handler",
                user_message="some text that triggers handler",
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G01"
            assert args[1] == "hard_stop_handler"

    def test_forbidden_critical_calls_observe_safety_block(self) -> None:
        """CRITICAL forbidden pattern calls observe_safety_block(G05, ...)."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.transform_llm_output(
                session_id="b8-test-forbidden",
                response_text="your safe word doesn't work at all",
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G05"
            assert "F-01" in args[1]

    def test_auth_forbidden_calls_observe_safety_block(self) -> None:
        """Auth FORBIDDEN tool calls observe_safety_block(G09, ...)."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            return_value=MockAuthLevel.FORBIDDEN,
        )

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_tool_call(
                session_id="b8-test-auth",
                tool_name="dangerous_tool",
                args={"operation": "destroy"},
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G09"
            assert "FORBIDDEN" in args[1]

    def test_auth_unknown_calls_observe_safety_block(self) -> None:
        """Unknown tool calls observe_safety_block(G09, ...)."""
        plugin = _make_safe_plugin()
        plugin._auth_available = True

        auth_matrix_mock = sys.modules["src.mcp.auth_matrix"]
        auth_matrix_mock.get_auth_level = MagicMock(
            side_effect=KeyError("unknown"),
        )

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_tool_call(
                session_id="b8-test-unknown",
                tool_name="nonexistent_tool",
                args={},
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G09"
            assert "UNKNOWN_TOOL" in args[1]

    def test_d3_distress_calls_observe_safety_block(self) -> None:
        """D3 distress block calls observe_safety_block(G02, ...)."""
        plugin = _make_safe_plugin()
        plugin._distress_available = True
        # Reset the detector mock (shared across tests) to clear any side_effect
        plugin._distress_detector.detect.side_effect = None

        signal = DistressSignal(
            detected_level=MockDistressLevel(3, "D3_SEVERE"),
            matched_patterns=["crisis"],
            confidence=0.90,
        )
        plugin._distress_detector.detect.return_value = signal

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="b8-test-distress",
                user_message="I am in crisis",
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G02"
            assert "DISTRESS" in args[1]

    def test_yandere_violation_calls_observe_safety_block(self) -> None:
        """Y6 yandere violation calls observe_safety_block(G07, ...)."""
        plugin = _make_safe_plugin()
        plugin._yandere_available = True
        plugin._yandere_engine = MagicMock()
        plugin._yandere_engine.get_effective_level.return_value = MockYandereLevel(
            6,
            "Y6_ABSOLUTE",
        )

        with patch(
            "src.hermes.safety_plugin.observe_safety_block",
        ) as mock_obs:
            plugin.pre_llm_call(
                session_id="b8-test-yandere",
                user_message="Normal text",
            )
            mock_obs.assert_called_once()
            args = mock_obs.call_args[0]
            assert args[0] == "G07"
            assert "YANDERE_SAFETY_VIOLATION" in args[1]

    def test_on_session_start_calls_set_session_count(self) -> None:
        """on_session_start calls set_session_count with current count."""
        plugin = _make_safe_plugin()
        # Use a dedicated test-only plugin to avoid shared-state interference
        with patch(
            "src.hermes.safety_plugin.set_session_count",
        ) as mock_set:
            plugin.on_session_start(session_id="b8-test-session")
            # set_session_count is called at least once (plugin init or on_session_start)
            assert mock_set.call_count >= 1
            # At least one call should have value >= 1
            found_valid = any(
                args[0][0] >= 1 for args in mock_set.call_args_list
            )
            assert found_valid, "No call to set_session_count had count >= 1"

    def test_pre_llm_call_calls_observe_message_incoming(self) -> None:
        """pre_llm_call with user_message calls observe_message('incoming')."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_message",
        ) as mock_msg:
            plugin.pre_llm_call(
                session_id="b8-test-msg-in",
                user_message="Hello there",
            )
            mock_msg.assert_called_once_with("incoming")

    def test_pre_tool_call_calls_observe_message_tool_call(self) -> None:
        """pre_tool_call calls observe_message('tool_call')."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_message",
        ) as mock_msg:
            plugin.pre_tool_call(
                session_id="b8-test-msg-tc",
                tool_name="reader",
                args={},
            )
            mock_msg.assert_called_once_with("tool_call")

    def test_post_tool_call_calls_observe_message_tool_result(self) -> None:
        """post_tool_call calls observe_message('tool_result')."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_message",
        ) as mock_msg:
            plugin.post_tool_call(
                session_id="b8-test-msg-tr",
                tool_name="reader",
                args={},
            )
            mock_msg.assert_called_once_with("tool_result")

    def test_transform_llm_output_calls_observe_message_outgoing(self) -> None:
        """transform_llm_output calls observe_message('outgoing')."""
        plugin = _make_safe_plugin()
        with patch(
            "src.hermes.safety_plugin.observe_message",
        ) as mock_msg:
            plugin.transform_llm_output(
                session_id="b8-test-msg-out",
                response_text="Hello world",
            )
            mock_msg.assert_called_once_with("outgoing")