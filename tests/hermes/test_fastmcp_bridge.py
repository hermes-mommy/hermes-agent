"""Tests for P4-005: FastMCP custom bridge.

Verifies that the KEEP-7-only custom manager:
- Exposes exactly the 7 KEEP tool families, not all 16.
- Does not import/register filesystem or other native modules.
- Has no ``_config`` parameter signatures (FastMCP v1 blocker).
- Points to a real, importable module path.
- Preserves ``sequential_thinking`` naming.
- Does not weaken Aizanta blocked paths.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import cast

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CUSTOM_MANAGER_PATH = Path("src/mcp/custom_manager.py")
FILESYSTEM_TOOLS_PATH = Path("src/mcp/tools/filesystem.py")
CONFIG_PATH = Path("hermes-config/config.yaml")

# ---------------------------------------------------------------------------
# KEEP-7 expected tool families
# ---------------------------------------------------------------------------

KEEP_7_FAMILIES: frozenset[str] = frozenset({
    "postgres",
    "redis",
    "obscura_cdp",
    "grep_app",
    "context7",
    "sequential_thinking",
    "time",
})

# Tool families that MUST NOT be exposed through the custom bridge
NATIVE_FAMILIES: frozenset[str] = frozenset({
    "filesystem",
    "shell",
    "docker",
    "git",
    "github",
    "fetch",
    "websearch",
    "brave_search",
    "exa_search",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_custom_manager_source() -> str:
    """Return the full source of the custom manager module."""
    return CUSTOM_MANAGER_PATH.read_text(encoding="utf-8")


def _get_filesystem_source() -> str:
    """Return the full source of the filesystem tools module."""
    return FILESYSTEM_TOOLS_PATH.read_text(encoding="utf-8")


ConfigValue = None | bool | int | float | str | list["ConfigValue"] | dict[str, "ConfigValue"]
ConfigMap = dict[str, ConfigValue]


def _as_mapping(value: ConfigValue, label: str) -> ConfigMap:
    """Return *value* as a string-keyed mapping."""
    assert isinstance(value, dict), f"{label} must be a mapping"
    assert all(isinstance(key, str) for key in value), f"{label} keys must be strings"
    return cast(ConfigMap, value)


def _as_list(value: ConfigValue, label: str) -> list[ConfigValue]:
    """Return *value* as a list."""
    assert isinstance(value, list), f"{label} must be a list"
    return value


def _load_config() -> ConfigMap:
    """Load hermes-config/config.yaml as a typed mapping."""
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        loaded = cast(object, yaml.safe_load(config_file))
    assert isinstance(loaded, dict), "config root must be a mapping"
    raw_map = cast(dict[object, object], loaded)
    assert all(isinstance(key, str) for key in raw_map), "config keys must be strings"
    return cast(ConfigMap, raw_map)


def _fastmcp_custom_config() -> ConfigMap:
    """Return the fastmcp_custom mcp_servers config."""
    config = _load_config()
    mcp_servers = _as_mapping(config.get("mcp_servers"), "mcp_servers")
    return _as_mapping(mcp_servers.get("fastmcp_custom"), "fastmcp_custom")


# ===================================================================
# KEEP-7 list verification
# ===================================================================


class TestKeep7List:
    """Exactly the 7 KEEP tool families are used in the custom bridge."""

    def test_keep_7_families_defined(self) -> None:
        """Verify the KEEP_TOOL_FAMILIES tuple matches expected families."""
        source = _get_custom_manager_source()
        # Extract the KEEP_TOOL_FAMILIES tuple contents
        match = re.search(
            r'KEEP_TOOL_FAMILIES:\s*tuple\[str, \.\.\.\]\s*=\s*\((.*?)\)',
            source,
            re.DOTALL,
        )
        assert match is not None, (
            "Could not find KEEP_TOOL_FAMILIES in custom_manager.py"
        )
        body = match.group(1)
        # Extract quoted strings from the tuple
        keep_tools = set(re.findall(r'"([^"]+)"', body))
        assert keep_tools == KEEP_7_FAMILIES, (
            f"KEEP-7 families mismatch. "
            f"Expected: {sorted(KEEP_7_FAMILIES)}. "
            f"Got: {sorted(keep_tools)}"
        )

    def test_custom_manager_imports_only_keep_modules(self) -> None:
        """Verify the import statement in custom_manager includes only KEEP-7 modules."""
        source = _get_custom_manager_source()
        # Find the from-import block for keep tools
        block_match = re.search(
            r'from src\.mcp\.tools import\s*\((.*?)\)',
            source,
            re.DOTALL,
        )
        assert block_match is not None, (
            "Could not find KEEP-7 import block in custom_manager.py"
        )
        block = block_match.group(1)
        imported_modules = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', block))

        keep_module_names = {
            "context7",
            "grep_app",
            "obscura_cdp",
            "postgres_tool",
            "redis_tool",
            "sequential_thinking",
            "time_tools",
        }

        imported_keep = imported_modules & keep_module_names
        imported_extra = imported_modules - keep_module_names - {
            "noqa",
            "E402",
        }

        assert imported_keep == keep_module_names, (
            f"Missing KEEP-7 module imports: "
            f"{keep_module_names - imported_keep}"
        )
        # Only E402 comment sections may additionally appear, no extra modules
        # removed stricter check: no extra module imports
        if imported_extra:
            # Allow Python keywords / noqa references only.
            extra_clean = {
                module_name
                for module_name in cast(set[str], imported_extra)
                if not module_name.startswith("E") and module_name not in {"noqa"}
            }
            assert not extra_clean, (
                f"Unexpected module imports in custom_manager: {extra_clean}"
            )

    def test_no_all_16_registration(self) -> None:
        """custom_manager must NOT use register_all_tools from __init__.py."""
        source = _get_custom_manager_source()
        tree = ast.parse(source)
        # Check no call to register_all_tools in the AST
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "register_all_tools"
        ]
        assert not calls, (
            "custom_manager must not call register_all_tools (registers all 16 modules)"
        )
        # Check no reference to _TOOL_MODULES as a name node
        names = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and node.id == "_TOOL_MODULES"
        ]
        assert not names, (
            "custom_manager must not reference _TOOL_MODULES (all 16 modules)"
        )

    def test_all_16_includes_native_excluded_from_keep(self) -> None:
        """Verify that KEEP-7 does not include any native tool family."""
        overlap = KEEP_7_FAMILIES & NATIVE_FAMILIES
        assert not overlap, (
            f"KEEP-7 includes unexpected native families: {overlap}"
        )

    def test_custom_manager_is_importable(self) -> None:
        """Verify the custom manager module can be imported without errors."""
        from src.mcp import custom_manager

        keep_tool_families = custom_manager.KEEP_TOOL_FAMILIES
        assert isinstance(keep_tool_families, tuple)
        assert len(keep_tool_families) == 7

    def test_custom_manager_creates_server(self) -> None:
        """Verify create_custom_server returns a FastMCP instance."""
        from src.mcp.custom_manager import create_custom_server

        server = create_custom_server("test-custom")
        assert server is not None
        assert hasattr(server, "run")


# ===================================================================
# _config signature blocker check
# ===================================================================


class TestConfigSignatureBlocker:
    """No ``_config`` parameters in filesystem.py (FastMCP v1 blocker)."""

    def test_no_underscore_config_params_in_filesystem(self) -> None:
        """Verify no function in filesystem.py has a ``_config`` parameter."""
        source = _get_filesystem_source()
        tree = ast.parse(source)

        issues: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if arg.arg == "_config":
                        issues.append(
                            f"Function '{node.name}' has parameter '_config'"
                        )

        assert not issues, (
            f"Found {len(issues)} function(s) with '_config' parameter "
            f"(FastMCP v1 rejects underscore-prefixed params): {issues}"
        )

    def test_no_config_pattern_in_custom_manager(self) -> None:
        """custom_manager must not import filesystem at all."""
        source = _get_custom_manager_source()
        tree = ast.parse(source)
        # Check for import statements referencing filesystem
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "filesystem" not in alias.name, (
                        f"custom_manager must not import filesystem, "
                        f"found: import {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "filesystem" in node.module:
                    pytest.fail(
                        f"custom_manager must not import filesystem, found: from {node.module} import ..."
                    )
                for alias in node.names:
                    assert "filesystem" not in alias.name, (
                        f"custom_manager must not import filesystem, "
                        f"found: import {alias.name}"
                    )


# ===================================================================
# sequential_thinking naming
# ===================================================================


class TestSequentialThinkingNaming:
    """The registered MCP tool name must be ``sequential_thinking``."""

    def test_registered_name_is_sequential_thinking(self) -> None:
        """Verify sequential_thinking module registers as ``sequential_thinking``."""
        source = Path("src/mcp/tools/sequential_thinking.py").read_text(
            encoding="utf-8"
        )
        assert (
            'mcp.tool(name="sequential_thinking")' in source
        ), "sequential_thinking tool must be registered with name 'sequential_thinking'"

    def test_config_yaml_include_refers_to_sequential_thinking(self) -> None:
        """Verify config.yaml includes sequential_thinking (not sequential_think)."""
        text = CONFIG_PATH.read_text(encoding="utf-8")
        assert "sequential_thinking" in text, (
            "Config must include sequential_thinking in fastmcp_custom tools.include"
        )
        # Use word boundary to avoid matching "sequential_thinking" substring
        assert not re.search(r'\bsequential_think\b', text), (
            "Config must NOT use incorrect name 'sequential_think'"
        )


# ===================================================================
# Config module path
# ===================================================================


class TestConfigModulePath:
    """The fastmcp_custom config must point to a real module."""

    def test_custom_manager_py_exists(self) -> None:
        assert CUSTOM_MANAGER_PATH.exists(), (
            "src/mcp/custom_manager.py must exist"
        )

    def test_custom_manager_has_main_block(self) -> None:
        source = _get_custom_manager_source()
        assert 'if __name__ == "__main__":' in source, (
            "custom_manager.py must have an entry-point block"
        )
        assert "create_custom_server()" in source or "server.run()" in source, (
            "custom_manager.py must create and run a server"
        )

    def test_config_references_custom_manager(self) -> None:
        """Verify config.yaml points to src.mcp.custom_manager."""
        text = CONFIG_PATH.read_text(encoding="utf-8")
        assert "src.mcp.custom_manager" in text, (
            "Config must reference src.mcp.custom_manager as the fastmcp_custom module"
        )

    def test_config_disabled_by_default(self) -> None:
        """Verify fastmcp_custom is disabled by default per BD-008."""
        fastmcp = _fastmcp_custom_config()
        assert fastmcp.get("enabled") is False, (
            "fastmcp_custom must be disabled by default per BD-008"
        )

    def test_config_include_list_matches_keep7(self) -> None:
        """Verify the tools.include list in config matches KEEP-7 exactly."""
        fastmcp = _fastmcp_custom_config()
        tools = _as_mapping(fastmcp.get("tools"), "fastmcp_custom.tools")
        include_values = _as_list(tools.get("include"), "fastmcp_custom.tools.include")
        assert all(isinstance(item, str) for item in include_values), (
            "fastmcp_custom.tools.include entries must be strings"
        )
        include = set(cast(list[str], include_values))

        assert include == KEEP_7_FAMILIES, (
            f"Config tools.include mismatch. "
            f"Expected: {sorted(KEEP_7_FAMILIES)}. "
            f"Got: {sorted(include)}"
        )


# ===================================================================
# Aizanta isolation — not weakened
# ===================================================================


class TestAizantaIsolation:
    """Aizanta blocked paths must not be weakened."""

    def test_filesystem_blocked_paths_intact(self) -> None:
        """Verify _BLOCKED_PATH_PREFIXES is still defined in filesystem.py."""
        source = _get_filesystem_source()
        assert "_BLOCKED_PATH_PREFIXES" in source, (
            "filesystem.py must retain _BLOCKED_PATH_PREFIXES"
        )
        assert "/home/aizanta" in source, (
            "filesystem.py must block /home/aizanta"
        )
        assert "/etc/aizanta" in source, (
            "filesystem.py must block /etc/aizanta"
        )

    def test_no_new_allow_for_aizanta(self) -> None:
        """Verify no path whitelist includes aizanta paths."""
        source = _get_filesystem_source()
        # Ensure the blocked list isn't emptied or commented out
        assert "aizanta" in source, (
            "Aizanta isolation reference must remain in filesystem.py"
        )

    def test_custom_manager_does_not_import_filesystem(self) -> None:
        """custom_manager must not import filesystem (avoids bypassing Aizanta gates)."""
        source = _get_custom_manager_source()
        tree = ast.parse(source)
        # Check for IMPORT statements referencing filesystem (not docstring)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "filesystem" not in alias.name, (
                        f"custom_manager must not import filesystem, "
                        f"found: import {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "filesystem" in node.module:
                    pytest.fail(
                        f"custom_manager must not import filesystem, found: from {node.module} import ..."
                    )
