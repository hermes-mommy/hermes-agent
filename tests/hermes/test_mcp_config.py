"""Tests for P4-001: Hermes MCP config baseline.

Validates ``hermes-config/config.yaml`` follows the documented Hermes
``mcp_servers`` shape, implements native exposure gating per BD-008,
declares Python ``src/mcp/auth_matrix.py`` as the sole runtime auth source
per BD-006, and avoids forbidden patterns.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import cast

import pytest
import yaml

CONFIG_PATH = Path("hermes-config/config.yaml")
AUTH_MATRIX_PY_PATH = Path("src/mcp/auth_matrix.py")

ConfigValue = None | bool | int | float | str | list["ConfigValue"] | dict[str, "ConfigValue"]
ConfigMap = dict[str, ConfigValue]

FORBIDDEN_REDIS_PORT = re.compile(r"redis://localhost:6379")
FORBIDDEN_PG_PORT = re.compile(r"localhost:5432")
FORBIDDEN_CRITICAL = re.compile(r"critical:\s*true")
PLAINTEXT_SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|discord(app)?\.com/api/webhooks/[^\s]{10,})")


def load_config() -> ConfigMap:
    """Load the Hermes config as a typed mapping."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        loaded = cast(object, yaml.safe_load(f))
    assert isinstance(loaded, dict)
    loaded_map = cast(dict[object, object], loaded)
    assert all(isinstance(key, str) for key in loaded_map)
    return cast(ConfigMap, loaded_map)


def as_mapping(value: ConfigValue, label: str) -> ConfigMap:
    """Assert and return a config value as a mapping."""
    assert isinstance(value, dict), f"{label} must be a mapping"
    return value


def as_list(value: ConfigValue, label: str) -> list[ConfigValue]:
    """Assert and return a config value as a list."""
    assert isinstance(value, list), f"{label} must be a list"
    return value


def get_raw_text() -> str:
    """Return raw config text for regex-based checks."""
    return CONFIG_PATH.read_text(encoding="utf-8")


def mcp_servers() -> ConfigMap:
    """Return the mcp_servers mapping."""
    cfg = load_config()
    assert "mcp_servers" in cfg, "mcp_servers section missing"
    return as_mapping(cfg["mcp_servers"], "mcp_servers")


class TestMcpServersShape:
    """Validate that ``mcp_servers`` follows documented Hermes shape."""

    def test_mcp_servers_exists(self) -> None:
        cfg = load_config()
        assert "mcp_servers" in cfg, "mcp_servers section missing"

    def test_mcp_servers_is_dict(self) -> None:
        servers = mcp_servers()
        assert servers, "mcp_servers must not be empty"

    def test_each_server_has_enabled(self) -> None:
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            assert "enabled" in server_map, f"server '{name}' missing 'enabled'"
            assert isinstance(server_map["enabled"], bool), f"server '{name}' enabled must be bool"

    def test_stdio_server_shape(self) -> None:
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            if "command" in server_map:
                assert isinstance(server_map["command"], str), f"server '{name}' command must be string"
                if "args" in server_map:
                    _ = as_list(server_map["args"], f"server '{name}' args")
                if "timeout" in server_map:
                    assert isinstance(server_map["timeout"], int | float), f"server '{name}' timeout must be numeric"

    def test_tools_section_shape(self) -> None:
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            if "tools" not in server_map:
                continue
            tools = as_mapping(server_map["tools"], f"server '{name}' tools")
            if "include" in tools:
                _ = as_list(tools["include"], f"server '{name}' tools.include")
            if "exclude" in tools:
                _ = as_list(tools["exclude"], f"server '{name}' tools.exclude")
            if "resources" in tools:
                assert isinstance(tools["resources"], bool), f"server '{name}' tools.resources must be bool"
            if "prompts" in tools:
                assert isinstance(tools["prompts"], bool), f"server '{name}' tools.prompts must be bool"

    def test_supports_parallel_tool_calls_is_bool(self) -> None:
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            if "supports_parallel_tool_calls" in server_map:
                assert isinstance(server_map["supports_parallel_tool_calls"], bool), (
                    f"server '{name}' supports_parallel_tool_calls must be bool"
                )

    def test_no_old_native_section_keys(self) -> None:
        forbidden_keys = {
            "root_path",
            "allowed_paths",
            "blocked_paths",
            "allowed_commands",
            "blocked_commands",
            "allowed_operations",
            "blocked_operations",
            "max_response_size_mb",
            "timeout_seconds",
        }
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            for key in forbidden_keys:
                assert key not in server_map, f"server '{name}' contains old native key '{key}'"


class TestForbiddenPatterns:
    """No forbidden patterns in the config file."""

    def test_no_redis_6379_port(self) -> None:
        assert not FORBIDDEN_REDIS_PORT.search(get_raw_text()), "Found forbidden redis://localhost:6379"

    def test_no_postgres_5432_port(self) -> None:
        assert not FORBIDDEN_PG_PORT.search(get_raw_text()), "Found forbidden localhost:5432"

    def test_no_plugin_critical_flag_in_config(self) -> None:
        assert not FORBIDDEN_CRITICAL.search(get_raw_text()), "Found forbidden 'critical: true' in config.yaml"

    def test_no_plaintext_secrets(self) -> None:
        assert not PLAINTEXT_SECRET.search(get_raw_text()), "Found potential plaintext secret in config.yaml"


class TestCanonicalPorts:
    """Redis 6380, Postgres 5433, 9Router 20128 must be referenced."""

    def test_canonical_port_redis_6380(self) -> None:
        assert "6380" in get_raw_text(), "Redis port 6380 must be referenced"

    def test_canonical_port_postgres_5433(self) -> None:
        assert "5433" in get_raw_text(), "Postgres port 5433 must be referenced"

    def test_canonical_port_ninerouter_20128(self) -> None:
        assert "20128" in get_raw_text(), "9Router port 20128 must be referenced"


class TestNativeExposureGate:
    """No direct production native tool exposure per BD-008."""

    NATIVE_PRODUCTION_TOOLS: frozenset[str] = frozenset({
        "filesystem",
        "shell",
        "terminal",
        "git",
        "web",
        "fetch",
        "docker",
        "github",
    })

    def test_no_enabled_native_production_tools(self) -> None:
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            if server_map.get("enabled") is not True:
                continue
            tools = as_mapping(server_map.get("tools", {}), f"server '{name}' tools")
            include = as_list(tools.get("include", []), f"server '{name}' tools.include")
            include_names = {item for item in include if isinstance(item, str)}
            enabled_native = include_names & self.NATIVE_PRODUCTION_TOOLS
            assert not enabled_native, f"Server '{name}' is enabled with native tools: {enabled_native}"

    def test_exposure_gate_comment_present(self) -> None:
        text = get_raw_text()
        assert "NATIVE EXPOSURE GATE" in text or "BD-008" in text, (
            "Config must document native exposure gate"
        )

    def test_default_disabled(self) -> None:
        for name, server in mcp_servers().items():
            server_map = as_mapping(server, f"server '{name}'")
            assert server_map.get("enabled") is False, f"Server '{name}' must be disabled by default per BD-008"


class TestAuthSource:
    """Python auth_matrix.py is the sole runtime source."""

    def test_auth_matrix_section_present(self) -> None:
        cfg = load_config()
        assert "auth_matrix" in cfg, "auth_matrix YAML section must be present"

    def test_auth_matrix_is_reference_only(self) -> None:
        text = get_raw_text()
        assert "REFERENCE ONLY" in text or "runtime auth source" in text or "BD-006" in text, (
            "Config must declare auth_matrix YAML as reference-only"
        )

    def test_python_auth_matrix_exists(self) -> None:
        assert AUTH_MATRIX_PY_PATH.exists(), "Python auth_matrix.py does not exist"

    def test_python_auth_matrix_has_get_auth_level(self) -> None:
        content = AUTH_MATRIX_PY_PATH.read_text(encoding="utf-8")
        assert "def get_auth_level" in content, "Python auth_matrix.py must define get_auth_level()"

    def test_python_auth_matrix_raises_keyerror(self) -> None:
        from src.mcp.auth_matrix import get_auth_level

        with pytest.raises(KeyError, match="unknown_tool"):
            _ = get_auth_level("unknown_tool", "any_op")

    def test_python_auth_matrix_known_tool_returns_level(self) -> None:
        from src.mcp.auth import AuthLevel
        from src.mcp.auth_matrix import get_auth_level

        result = get_auth_level("brave_search", "search")
        assert result == AuthLevel.READ_AUTO


class TestYamlValidity:
    """Config must be valid YAML and round-trip cleanly."""

    def test_config_is_valid_yaml(self) -> None:
        cfg = load_config()
        assert cfg is not None, "Config is not valid YAML"

    def test_config_has_required_top_keys(self) -> None:
        required = {
            "discord",
            "model",
            "providers",
            "agent",
            "memory",
            "hooks",
            "mcp_servers",
            "cron",
            "observability",
            "auth_matrix",
            "approval",
            "audit",
        }
        cfg = load_config()
        missing = required - set(cfg.keys())
        assert not missing, f"Config is missing required top-level sections: {missing}"
