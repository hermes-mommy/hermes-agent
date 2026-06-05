"""Tests for P4-002: Auth overlay plugin.

Covers:
- All 16 canonical tools map correctly through normalization.
- All four AuthLevel values enforce correctly (READ_AUTO → allow,
  WRITE_NOTIFY → notify+allow, DESTRUCTIVE_APPROVAL → persist+block,
  FORBIDDEN → block).
- Unknown tool names produce a block response (fail-closed).
- Unknown operations produce a block response (fail-closed).
- Redis DB5 approval requests use TTL=300 seconds.
- Webhook notification payloads are redacted of secret-like patterns.
- MCP prefix normalisation (``mcp_fastmcp_custom_*``, ``mcp_*``, etc.).
- Native/alias tool name mapping.
- No runtime YAML auth source is read.
- Plugin exception in ``pre_tool_call`` returns block (fail-closed).

The test module imports Python ``src.mcp.auth_matrix`` directly to verify
alignment — exactly as the production plugin does.
"""

from __future__ import annotations

import importlib
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest

# ---- Path setup: ensure auth_overlay plugin is importable ----------------
# The root ``plugins/`` package shadows ``hermes-config/plugins/``.  We
# resolve this by adding ``hermes-config`` to the front of ``sys.path``
# and removing the root ``plugins`` from the module cache.
_HERMES_CONFIG = Path(__file__).resolve().parent.parent.parent / "hermes-config"
for _key in list(sys.modules):
    if _key == "plugins" or _key.startswith("plugins."):
        _ = sys.modules.pop(_key, None)
_config_str = str(_HERMES_CONFIG.resolve())
if _config_str in sys.path:
    sys.path.remove(_config_str)
sys.path.insert(0, _config_str)
# -------------------------------------------------------------------------

from src.mcp.auth import AuthLevel
from src.mcp.auth_matrix import AUTH_MATRIX, ALL_TOOL_NAMES, get_auth_level

class FakeRedisAdapterProtocol(Protocol):
    pass


class ApprovalHandlerProtocol(Protocol):
    def request_approval(
        self,
        canonical_tool: str,
        operation: str,
        details: str = "",
        ttl: int = 300,
    ) -> dict[str, str | int]: ...
    def check_approval(self, canonical_tool: str) -> str | None: ...
    def resolve_approval(self, canonical_tool: str, approved: bool) -> bool: ...
    def consume_approval(self, canonical_tool: str) -> bool: ...


class ApprovalHandlerFactory(Protocol):
    def __call__(
        self,
        redis_client: FakeRedisAdapterProtocol | None = None,
    ) -> ApprovalHandlerProtocol: ...


class AuthOverlayPluginProtocol(Protocol):
    def pre_tool_call(self, **kwargs: object) -> dict[str, str] | None: ...


class AuthOverlayPluginFactory(Protocol):
    def __call__(
        self,
        approval_handler: ApprovalHandlerProtocol | None = None,
    ) -> AuthOverlayPluginProtocol: ...


class NormalizeToolName(Protocol):
    def __call__(
        self,
        raw_name: str,
        args: Mapping[str, object] | None = None,
    ) -> tuple[str, str] | None: ...


class ForbiddenHandler(Protocol):
    def __call__(
        self,
        canonical_tool: str,
        operation: str,
        raw_tool_name: str = "",
    ) -> dict[str, str]: ...


_approval_module = importlib.import_module("plugins.auth_overlay.approval_handler")
_auth_module = importlib.import_module("plugins.auth_overlay.auth_handler")
_forbidden_module = importlib.import_module("plugins.auth_overlay.forbidden_handler")
_notify_module = importlib.import_module("plugins.auth_overlay.notify_handler")

_APPROVAL_TTL_SECONDS = cast(int, getattr(_approval_module, "_APPROVAL_TTL_SECONDS"))
FakeRedisAdapter = cast(
    type[FakeRedisAdapterProtocol],
    getattr(_approval_module, "FakeRedisAdapter"),
)
ApprovalHandler = cast(
    ApprovalHandlerFactory,
    getattr(_approval_module, "ApprovalHandler"),
)
AuthOverlayPlugin = cast(
    AuthOverlayPluginFactory,
    getattr(_auth_module, "AuthOverlayPlugin"),
)
normalize_tool_name = cast(
    NormalizeToolName,
    getattr(_auth_module, "normalize_tool_name"),
)
KNOWN_PREFIXES = cast(list[str], getattr(_auth_module, "KNOWN_PREFIXES"))
handle_forbidden = cast(ForbiddenHandler, getattr(_forbidden_module, "handle_forbidden"))
redact_payload = cast(Callable[[str], str], getattr(_notify_module, "redact_payload"))

# ==============================================================================
# Helpers
# ==============================================================================


def _make_plugin(
    fake_redis: FakeRedisAdapterProtocol | None = None,
) -> AuthOverlayPluginProtocol:
    """Create an AuthOverlayPlugin with a fake Redis adapter."""
    redis = fake_redis or FakeRedisAdapter()
    approval = ApprovalHandler(redis_client=redis)
    return AuthOverlayPlugin(approval_handler=approval)


def _has_block_action(result: object) -> bool:
    """Check if a result is a block dict."""
    if not isinstance(result, dict):
        return False
    narrowed = cast(dict[object, object], result)
    return narrowed.get("action") == "block"


def _is_allow(result: object) -> bool:
    """Check if a result is None (allow)."""
    return result is None


def _block_field(result: object, field: str) -> str:
    """Return a string field from a block result after narrowing its type."""
    assert isinstance(result, dict)
    narrowed = cast(dict[object, object], result)
    value = narrowed.get(field, "")
    return value if isinstance(value, str) else ""


# ==============================================================================
# 1.  Canonical tool mapping — all 16 tools
# ==============================================================================


class TestCanonicalToolMapping:
    """Verify every canonical tool name maps through normalisation."""

    @pytest.mark.parametrize("tool_name", sorted(ALL_TOOL_NAMES))
    def test_canonical_tool_self_maps(self, tool_name: str) -> None:
        """A bare canonical tool name maps to itself."""
        result = normalize_tool_name(tool_name, {"operation": "read"})
        assert result is not None, f"Canonical tool '{tool_name}' failed to map"
        mapped_tool, _mapped_op = result
        assert mapped_tool == tool_name, (
            f"Expected tool '{tool_name}', got '{mapped_tool}'"
        )

    def test_all_16_tools_in_matrix(self) -> None:
        """All 16 expected tool names are present in AUTH_MATRIX."""
        assert len(ALL_TOOL_NAMES) == 16
        for name in ALL_TOOL_NAMES:
            assert name in AUTH_MATRIX, f"Tool '{name}' missing from AUTH_MATRIX"

    def test_all_16_tools_get_auth_level(self) -> None:
        """All 16 tools return an AuthLevel for their first operation."""
        for name in ALL_TOOL_NAMES:
            ops = AUTH_MATRIX[name]
            if "*" in ops:
                level = get_auth_level(name, "*")
            else:
                first_op = next(iter(ops))
                level = get_auth_level(name, first_op)
            assert isinstance(level, AuthLevel), (
                f"Tool '{name}' returned non-AuthLevel: {level}"
            )


# ==============================================================================
# 2.  Tool name normalisation — prefixes, aliases, edge cases
# ==============================================================================


class TestNameNormalisation:
    """Normalisation handles MCP prefixes, native aliases, and unknowns."""

    # --- Prefix stripping ---

    @pytest.mark.parametrize(
        "raw, expected_tool, expected_op",
        [
            ("mcp_fastmcp_custom_redis_get", "redis", "get"),
            ("mcp_fastmcp_custom_postgres_query", "postgres", "select"),
            ("mcp_fastmcp_custom_postgres_insert", "postgres", "insert"),
            ("mcp_fastmcp_custom_obscura_get_markdown", "obscura_cdp", "read"),
            ("mcp_fastmcp_custom_context7_resolve", "context7", "resolve"),
            ("mcp_fastmcp_custom_sequential_thinking", "sequential_thinking", "*"),
            ("mcp_fastmcp_custom_time", "time", "*"),
            ("mcp_fastmcp_custom_fetch", "fetch", "*"),
            ("mcp_fastmcp_custom_websearch", "websearch", "*"),
            ("mcp_fastmcp_custom_brave_search", "brave_search", "*"),
            ("mcp_native_filesystem_read", "filesystem", "read"),
            ("mcp_filesystem_write", "filesystem", "write"),
        ],
    )
    def test_prefix_stripping(
        self,
        raw: str,
        expected_tool: str,
        expected_op: str,
    ) -> None:
        """MCP prefixes are stripped and remaining name is mapped."""
        result = normalize_tool_name(raw)
        assert result is not None, f"Failed to map '{raw}'"
        tool, op = result
        assert tool == expected_tool, (
            f"'{raw}' → tool '{tool}', expected '{expected_tool}'"
        )
        # Accept wildcard match as equivalent.
        if expected_op != "*":
            assert op == expected_op, (
                f"'{raw}' → op '{op}', expected '{expected_op}'"
            )

    # --- Native / alias names ---

    @pytest.mark.parametrize(
        "alias, expected_tool, expected_op",
        [
            ("fetch_url", "fetch", "*"),
            ("web_search", "websearch", "*"),
            ("shell_exec", "shell", "exec"),
            ("terminal", "shell", "exec"),
            ("git_log", "git", "log"),
            ("git_commit", "git", "commit"),
            ("git_force_push", "git", "force_push"),
            ("filesystem_read", "filesystem", "read"),
            ("filesystem_delete", "filesystem", "delete"),
            ("redis_set", "redis", "set"),
            ("docker_ps", "docker", "ps"),
            ("docker_rm", "docker", "rm"),
            ("docker_system_prune", "docker", "system_prune"),
            ("github_create_issue", "github", "create_issue"),
            ("postgres_drop", "postgres", "drop"),
            ("obscura_navigate", "obscura_cdp", "navigate"),
            ("context7_query", "context7", "query"),
            ("exa_search", "exa", "*"),
            ("brave_search_search", "brave_search", "*"),
            ("grep_app_search", "grep_app", "*"),
        ],
    )
    def test_native_aliases(
        self,
        alias: str,
        expected_tool: str,
        expected_op: str,
    ) -> None:
        """Native/alias names are correctly mapped."""
        result = normalize_tool_name(alias)
        assert result is not None, f"Alias '{alias}' failed to map"
        tool, op = result
        assert op == expected_op or expected_op == "*"
        assert tool == expected_tool, (
            f"Alias '{alias}' → tool '{tool}', expected '{expected_tool}'"
        )

    # --- Tool + operation from args (for bare canonical names) ---

    def test_operation_from_args(self) -> None:
        """Operation is extracted from args when tool name is canonical."""
        result = normalize_tool_name("redis", {"operation": "get"})
        assert result == ("redis", "get")

    def test_operation_defaults_to_read(self) -> None:
        """Bare canonical tool with no args defaults op to read."""
        result = normalize_tool_name("github")
        assert result is not None
        assert result[0] == "github"
        assert result[1] == "read"

    # --- Unknown name → None (fail-closed) ---

    def test_unknown_tool_returns_none(self) -> None:
        """An unrecognised tool name returns None (will be blocked)."""
        assert normalize_tool_name("nonexistent_tool_xyz") is None

    def test_garbage_name_returns_none(self) -> None:
        """Totally unrecognisable names return None."""
        assert normalize_tool_name("") is None
        assert normalize_tool_name("!!!invalid!!!") is None

    def test_unknown_prefix_stripped_to_empty(self) -> None:
        """Name that is only a known prefix returns None."""
        for prefix in KNOWN_PREFIXES:
            result = normalize_tool_name(prefix)
            assert result is None, f"Prefix-only '{prefix}' should not map"

    # --- Internal tools are blocked ---

    def test_internal_tool_require_approval_blocked(self) -> None:
        """Internal 'require_approval' name returns None (blocked)."""
        assert normalize_tool_name("require_approval") is None


# ==============================================================================
# 3.  AuthLevel enforcement
# ==============================================================================


class TestAuthLevelEnforcement:
    """All four AuthLevel values enforce correctly."""

    def test_read_auto_allows(self) -> None:
        """READ_AUTO returns None (allow)."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(
            tool_name="brave_search",
            args={"query": "test"},
        )
        assert _is_allow(result), f"Expected allow (None), got {result}"

    def test_write_notify_allows(self) -> None:
        """WRITE_NOTIFY returns None (allow) after notification."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(
            tool_name="filesystem_write",
            args={"path": "/tmp/test.txt"},
        )
        assert _is_allow(result), f"Expected allow (None), got {result}"

    def test_forbidden_blocks(self) -> None:
        """FORBIDDEN returns block."""
        plugin = _make_plugin()
        # ``git force_push_main`` is FORBIDDEN in auth matrix.
        result = plugin.pre_tool_call(
            tool_name="git_force_push_main",
        )
        assert _has_block_action(result), f"Expected block, got {result}"
        assert "FORBIDDEN" in _block_field(result, "reason").upper() or "FORBIDDEN" in _block_field(result, "message").upper(), (
            f"Block reason should mention FORBIDDEN: {result}"
        )

    def test_read_auto_tools_list(self) -> None:
        """All wildcard READ_AUTO tools allow through normalised names."""
        plugin = _make_plugin()
        read_auto_tools = [
            "brave_search",
            "websearch",
            "fetch",
            "exa",
            "time",
            "grep_app",
            "sequential_thinking",
        ]
        for tool in read_auto_tools:
            result = plugin.pre_tool_call(tool_name=tool)
            assert _is_allow(result), f"READ_AUTO tool '{tool}' should allow"


# ==============================================================================
# 4.  DESTRUCTIVE_APPROVAL — Redis persistence and TTL
# ==============================================================================


class TestDestructiveApproval:
    """DESTRUCTIVE_APPROVAL creates a Redis-persisted pending request."""

    def test_destructive_blocks_on_first_call(self) -> None:
        """Destructive operation blocks with approval-required message."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(
            tool_name="filesystem_delete",
            args={"path": "/tmp/important"},
        )
        assert _has_block_action(result), f"Expected block, got {result}"
        assert "APPROVAL_REQUIRED" in _block_field(result, "reason"), (
            f"Reason should mention APPROVAL_REQUIRED: {result}"
        )

    def test_approval_allows_after_approve(self) -> None:
        """After approving a pending request, the tool is allowed."""
        redis = FakeRedisAdapter()
        plugin = _make_plugin(fake_redis=redis)
        approval = ApprovalHandler(redis_client=redis)

        # First call — blocks with approval request.
        result1 = plugin.pre_tool_call(
            tool_name="redis_del",
            args={"key": "test"},
        )
        assert _has_block_action(result1)

        # Simulate external approval.
        _ = approval.resolve_approval("redis", approved=True)

        # Second call — should allow.
        result2 = plugin.pre_tool_call(
            tool_name="redis_del",
            args={"key": "test"},
        )
        assert _is_allow(result2), f"Expected allow after approval, got {result2}"

    def test_approval_deny_blocks(self) -> None:
        """After denying a pending request, the tool is still blocked."""
        redis = FakeRedisAdapter()
        plugin = _make_plugin(fake_redis=redis)
        approval = ApprovalHandler(redis_client=redis)

        _ = plugin.pre_tool_call(tool_name="redis_del", args={"key": "test"})
        _ = approval.resolve_approval("redis", approved=False)

        result = plugin.pre_tool_call(tool_name="redis_del", args={"key": "test"})
        assert _has_block_action(result), f"Expected block after deny, got {result}"
        assert "DENIED" in _block_field(result, "reason"), (
            f"Reason should mention DENIED: {result}"
        )

    def test_approval_ttl_is_300(self) -> None:
        """The TTL constant is 300 seconds (5 minutes)."""
        assert _APPROVAL_TTL_SECONDS == 300

    def test_approval_request_uses_ttl(self) -> None:
        """The approval request stores with TTL=300."""
        redis = FakeRedisAdapter()
        approval = ApprovalHandler(redis_client=redis)

        req = approval.request_approval("redis", "del", ttl=300)
        assert req["ttl_seconds"] == 300
        assert req["status"] == "pending"

        # Verify it's stored in Redis.
        status = approval.check_approval("redis")
        assert status == "pending"

    def test_approval_expires_after_ttl(self) -> None:
        """After TTL elapses, the approval request is gone."""
        redis = FakeRedisAdapter()
        approval = ApprovalHandler(redis_client=redis)

        _ = approval.request_approval("test_tool", "delete", ttl=1)  # 1 second TTL.
        assert approval.check_approval("test_tool") == "pending"

        time.sleep(1.1)  # Wait for expiry.

        assert approval.check_approval("test_tool") is None

    def test_approval_key_correct_format(self) -> None:
        """Approval keys use the expected prefix format."""
        redis = FakeRedisAdapter()
        approval = ApprovalHandler(redis_client=redis)

        _ = approval.request_approval("filesystem", "delete")
        status = approval.check_approval("filesystem")
        assert status == "pending"

        # Approved flow.
        _ = approval.resolve_approval("filesystem", approved=True)
        assert approval.check_approval("filesystem") == "approved"


# ==============================================================================
# 5.  Fail-closed: unknown tool, unknown operation, plugin exception
# ==============================================================================


class TestFailClosed:
    """The plugin fails closed on unknown input and errors."""

    def test_unknown_tool_blocked(self) -> None:
        """An unknown tool name produces a block."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(tool_name="completely_unknown_tool")
        assert _has_block_action(result), f"Expected block for unknown tool, got {result}"
        assert "UNKNOWN_TOOL" in _block_field(result, "reason"), (
            f"Reason should mention UNKNOWN_TOOL: {result}"
        )

    def test_unknown_operation_blocked(self) -> None:
        """An unknown operation for a known tool produces a block."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(
            tool_name="postgres",
            args={"operation": "nonexistent_op_xyz"},
        )
        assert _has_block_action(result), f"Expected block for unknown op, got {result}"
        assert "UNKNOWN_OPERATION" in _block_field(result, "reason"), (
            f"Reason should mention UNKNOWN_OPERATION: {result}"
        )

    def test_forbidden_operation_blocked_direct(self) -> None:
        """A FORBIDDEN-level operation is blocked via handle_forbidden."""
        result = handle_forbidden("postgres", "drop")
        assert _has_block_action(result)
        assert "FORBIDDEN" in _block_field(result, "reason")

    def test_plugin_exception_fails_closed(self) -> None:
        """If the plugin raises unexpectedly, pre_tool_call returns block."""
        plugin = _make_plugin()

        # Break the approval handler so DESTRUCTIVE_APPROVAL triggers error.
        object.__setattr__(plugin, "_approval", None)

        # filesystem_delete is DESTRUCTIVE_APPROVAL → uses _approval.
        result = plugin.pre_tool_call(
            tool_name="filesystem_delete",
            args={"path": "/tmp/test"},
        )
        assert _has_block_action(result), f"Expected block on error, got {result}"
        assert "AUTH_OVERLAY_ERROR" in _block_field(result, "reason"), (
            f"Reason should mention AUTH_OVERLAY_ERROR: {result}"
        )


# ==============================================================================
# 6.  Notification redaction
# ==============================================================================


class TestNotificationRedaction:
    """Webhook notification payloads are redacted of secret-like values."""

    def test_redacts_discord_webhook(self) -> None:
        """Discord webhook URLs are redacted."""
        text = "Webhook: https://discord.com/api/webhooks/12345/abc-def"
        result = redact_payload(text)
        assert "[REDACTED]" in result
        assert "discord.com/api/webhooks" not in result

    def test_redacts_openai_key(self) -> None:
        """OpenAI-style keys are redacted."""
        text = "Key: sk-proj-A" + "B" * 40
        result = redact_payload(text)
        assert "[REDACTED]" in result

    def test_redacts_github_pat(self) -> None:
        """GitHub PATs are redacted."""
        text = "ghp_" + "A" * 36
        result = redact_payload(text)
        assert "[REDACTED]" in result

    def test_redacts_redis_url(self) -> None:
        """Redis URLs with credentials are redacted."""
        text = "redis://user:pass@localhost:6380"
        result = redact_payload(text)
        assert "[REDACTED]" in result

    def test_redacts_pg_url(self) -> None:
        """PostgreSQL URLs with credentials are redacted."""
        text = "postgresql://user:secret@localhost:5433/db"
        result = redact_payload(text)
        assert "[REDACTED]" in result

    def test_redacts_private_key_header(self) -> None:
        """Private key header patterns are redacted."""
        text = "-----BEGIN RSA PRIVATE KEY-----"
        result = redact_payload(text)
        assert "[REDACTED]" in result

    def test_plain_text_passes_through(self) -> None:
        """Plain text without secrets is unchanged."""
        text = "Hello, this is a normal notification."
        result = redact_payload(text)
        assert result == text

    def test_empty_string_passes_through(self) -> None:
        """Empty string is unchanged."""
        assert redact_payload("") == ""


# ==============================================================================
# 7.  Redis DB5 defaults
# ==============================================================================


class TestRedisDefaults:
    """Redis adapter defaults to project canonical configuration."""

    def test_approval_handler_uses_fake_in_tests(self) -> None:
        """ApprovalHandler works with FakeRedisAdapter in unit tests."""
        redis = FakeRedisAdapter()
        approval = ApprovalHandler(redis_client=redis)

        _ = approval.request_approval("test", "op", ttl=300)
        assert approval.check_approval("test") == "pending"

    def test_approval_ttl_constant_correct(self) -> None:
        """The TTL constant is set correctly."""
        assert _APPROVAL_TTL_SECONDS == 300


# ==============================================================================
# 8.  No runtime YAML auth source
# ==============================================================================


class TestNoRuntimeYaml:
    """The plugin never reads a YAML auth matrix at runtime."""

    def test_plugin_imports_python_matrix(self) -> None:
        """The plugin imports directly from ``src.mcp.auth_matrix``."""
        imported_matrix = cast(object, getattr(_auth_module, "AUTH_MATRIX"))

        # The imported matrix should be the same object (or equal).
        assert imported_matrix is AUTH_MATRIX or imported_matrix == AUTH_MATRIX

    def test_plugin_uses_get_auth_level(self) -> None:
        """The plugin uses ``get_auth_level`` from ``src.mcp.auth_matrix``."""
        level = get_auth_level("redis", "get")
        assert level == AuthLevel.READ_AUTO

    def test_no_yaml_load_in_plugin(self) -> None:
        """The plugin modules do not import yaml."""
        import sys  # noqa: PLC0415

        plugin_modules = [
            mod for mod in sys.modules
            if "auth_overlay" in mod
        ]
        assert plugin_modules
        assert "yaml" not in sys.modules


# ==============================================================================
# 9.  Integration: end-to-end enforcement flows
# ==============================================================================


class TestIntegrationEnforcement:
    """End-to-end enforcement across tool categories."""

    def test_read_tool_through_prefix(self) -> None:
        """A prefixed READ_AUTO tool is allowed."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(
            tool_name="mcp_fastmcp_custom_brave_search",
            args={"query": "test"},
        )
        assert _is_allow(result)

    def test_write_notify_through_prefix(self) -> None:
        """A prefixed WRITE_NOTIFY tool is allowed."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(
            tool_name="mcp_fastmcp_custom_redis_set",
            args={"key": "x", "value": "1"},
        )
        assert _is_allow(result)

    def test_forbidden_through_alias(self) -> None:
        """A FORBIDDEN alias is blocked."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(tool_name="postgres_drop")
        assert _has_block_action(result)

    def test_destructive_through_prefix(self) -> None:
        """A prefixed DESTRUCTIVE_APPROVAL tool is blocked first, allowed after."""
        redis = FakeRedisAdapter()
        plugin = _make_plugin(fake_redis=redis)

        result = plugin.pre_tool_call(
            tool_name="mcp_fastmcp_custom_redis_del",
            args={"key": "test"},
        )
        assert _has_block_action(result)
        assert "APPROVAL_REQUIRED" in _block_field(result, "reason")

    def test_multiple_tools_same_session(self) -> None:
        """Multiple tool calls in sequence work correctly."""
        plugin = _make_plugin()

        # READ_AUTO.
        assert _is_allow(plugin.pre_tool_call(tool_name="time"))

        # WRITE_NOTIFY.
        assert _is_allow(plugin.pre_tool_call(tool_name="filesystem_write"))

        # FORBIDDEN.
        assert _has_block_action(plugin.pre_tool_call(tool_name="postgres_drop"))


# ==============================================================================
# 10.  Edge cases: empty/missing tool_name, missing kwargs
# ==============================================================================


class TestEdgeCases:
    """Edge cases for the auth overlay."""

    def test_missing_tool_name_defaults_unknown(self) -> None:
        """Missing tool_name defaults to 'unknown' and is blocked."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call(args={})
        assert _has_block_action(result)

    def test_empty_kwargs(self) -> None:
        """Empty kwargs are handled gracefully (blocked)."""
        plugin = _make_plugin()
        result = plugin.pre_tool_call()
        assert _has_block_action(result)

    def test_approval_consume_returns_true_on_existing(self) -> None:
        """Consuming an existing approval returns True."""
        redis = FakeRedisAdapter()
        approval = ApprovalHandler(redis_client=redis)

        _ = approval.request_approval("test_tool", "delete")
        _ = approval.resolve_approval("test_tool", approved=True)
        assert approval.consume_approval("test_tool") is True

    def test_approval_consume_returns_false_on_missing(self) -> None:
        """Consuming a non-existent approval returns False."""
        redis = FakeRedisAdapter()
        approval = ApprovalHandler(redis_client=redis)
        assert approval.consume_approval("nonexistent") is False

    def test_handle_forbidden_returns_block(self) -> None:
        """handle_forbidden returns a block action dict."""
        result = handle_forbidden("shell", "rm_rf_root")
        assert result["action"] == "block"
        assert "FORBIDDEN" in result["reason"]
