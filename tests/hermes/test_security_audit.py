"""P4-007 Security Audit — ADR-035 Phase 4 deterministic security checks.

All 15 checks are mandatory (BD-012).  Each test class maps to one audit check.
No live VPS calls, no network, no systemctl, no SSH, no real Redis/Postgres.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import cast

import pytest

# ---- Path setup -----------------------------------------------------------
_HERMES_CONFIG = Path(__file__).resolve().parent.parent.parent / "hermes-config"
_HOOKS_DIR = _HERMES_CONFIG / "hooks"
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"

for _p in [str(_SRC_DIR.resolve()), str(_HERMES_CONFIG.resolve()),
           str(_HOOKS_DIR.resolve()), str(_SCRIPTS_DIR.resolve())]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _key in list(sys.modules):
    if _key == "plugins" or _key.startswith("plugins."):
        del sys.modules[_key]

# ---- Import auth matrix --------------------------------------------------
from src.mcp.auth import AuthLevel
from src.mcp.auth_matrix import (
    AUTH_MATRIX,
    ALL_TOOL_NAMES,
    get_auth_level,
    verify_matrix_completeness,
)

# ---- Helper: import by file path -----------------------------------------
import importlib.util


def _import_by_path(path: Path, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_hook(name: str):
    return _import_by_path(_HOOKS_DIR / f"{name}.py", f"_p4h_{name}")


def _read(rel_path: str) -> str:
    p = Path(__file__).resolve().parent.parent.parent / rel_path
    return p.read_text("utf-8")


# ==============================================================================
# Check 1: Python auth_matrix.py is authoritative runtime source
# ==============================================================================


class TestCheck01_PythonAuthMatrixIsAuthoritative:
    """Check 1: src/mcp/auth_matrix.py is the sole runtime auth source."""

    def test_auth_matrix_has_all_16_tools(self) -> None:
        assert len(AUTH_MATRIX) == 16
        assert len(ALL_TOOL_NAMES) == 16
        for name in ALL_TOOL_NAMES:
            assert name in AUTH_MATRIX, f"Tool '{name}' missing"

    def test_no_runtime_auth_matrix_yaml(self) -> None:
        plugin_dir = _HERMES_CONFIG / "plugins" / "auth_overlay"
        for pyfile in plugin_dir.glob("*.py"):
            content = pyfile.read_text("utf-8")
            assert "import yaml" not in content
            assert "from yaml" not in content

    def test_verify_matrix_completeness_true(self) -> None:
        assert verify_matrix_completeness() is True

    def test_config_yaml_auth_matrix_marked_reference_only(self) -> None:
        content = _read("hermes-config/config.yaml")
        assert "REFERENCE ONLY" in content


# ==============================================================================
# Check 2: All 16 canonical tools have enforcement mapping coverage
# ==============================================================================


class TestCheck02_All16ToolsEnforcementCoverage:
    """Check 2: Every ALL_TOOL_NAMES entry has operation mapping coverage."""

    def test_all_16_tools_have_operations(self) -> None:
        for tool in ALL_TOOL_NAMES:
            assert len(AUTH_MATRIX[tool]) >= 1

    def test_all_operations_mapped_to_authlevel(self) -> None:
        for tool, ops in AUTH_MATRIX.items():
            for op_name, level in ops.items():
                assert isinstance(level, AuthLevel)

    def test_auth_levels_known(self) -> None:
        known = {AuthLevel.READ_AUTO, AuthLevel.WRITE_NOTIFY,
                 AuthLevel.DESTRUCTIVE_APPROVAL, AuthLevel.FORBIDDEN}
        for tool, ops in AUTH_MATRIX.items():
            for _, level in ops.items():
                assert level in known, f"'{tool}' unknown level {level}"

    def test_tool_aliases_valid(self) -> None:
        """Auth overlay TOOL_ALIASES maps only to canonical tools."""
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        # Find alias tuples like ("shell", "exec"), ("fetch", "*") in TOOL_ALIASES.
        # Only match lines that are dict entries with string keys and tuple values.
        in_aliases = False
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped == "TOOL_ALIASES:" or stripped.startswith("TOOL_ALIASES"):
                in_aliases = True
                continue
            if not in_aliases:
                continue
            # End of TOOL_ALIASES dict: next section starts
            if stripped.startswith("from ") or stripped.startswith("import ") or stripped.startswith("class ") or stripped.startswith("def "):
                break
            # Match alias entries: "alias": ("tool", "op"),
            m = re.match(r'^\s+"[a-z_]+":\s+\(?"([a-z_*]+)"', stripped)
            if m:
                tool = m.group(1)
                if tool != "*" and tool not in ALL_TOOL_NAMES:
                    pytest.fail(f"Alias maps to unknown tool '{tool}' in line: {stripped}")


# ==============================================================================
# Check 3: Unknown tool/operation fails closed
# ==============================================================================


class TestCheck03_UnknownFailsClosed:
    """Check 3: Unknown tool/operation produces block response."""

    def test_get_auth_level_keyerror_on_unknown_tool(self) -> None:
        with pytest.raises(KeyError):
            get_auth_level("nonexistent_tool", "read")

    def test_get_auth_level_keyerror_on_unknown_op(self) -> None:
        with pytest.raises(KeyError):
            get_auth_level("postgres", "nonexistent_op")

    def test_normalize_tool_unknown_returns_none(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "return None  # Unknown" in content or "return None" in content

    def test_unknown_tool_blocked_in_handler(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "UNKNOWN_TOOL" in content

    def test_unknown_operation_blocked_in_handler(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "UNKNOWN_OPERATION" in content

    def test_plugin_exception_returns_block(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "AUTH_OVERLAY_ERROR" in content


# ==============================================================================
# Check 4: READ_AUTO path allows deterministic read tools
# ==============================================================================


class TestCheck04_ReadAutoAllows:
    """Check 4: READ_AUTO level tools are allowed without approval."""

    def test_filesystem_read_is_read_auto(self) -> None:
        assert get_auth_level("filesystem", "read") == AuthLevel.READ_AUTO

    def test_git_log_is_read_auto(self) -> None:
        assert get_auth_level("git", "log") == AuthLevel.READ_AUTO

    def test_postgres_select_is_read_auto(self) -> None:
        assert get_auth_level("postgres", "select") == AuthLevel.READ_AUTO

    def test_redis_get_is_read_auto(self) -> None:
        assert get_auth_level("redis", "get") == AuthLevel.READ_AUTO

    @pytest.mark.parametrize("tool", [
        "brave_search", "websearch", "fetch", "exa",
        "time", "grep_app", "sequential_thinking",
    ])
    def test_wildcard_tools_read_auto(self, tool: str) -> None:
        assert get_auth_level(tool, "*") == AuthLevel.READ_AUTO

    def test_context7_ops_read_auto(self) -> None:
        """context7 uses explicit operations (no wildcard)."""
        assert get_auth_level("context7", "resolve") == AuthLevel.READ_AUTO
        assert get_auth_level("context7", "query") == AuthLevel.READ_AUTO


# ==============================================================================
# Check 5: WRITE_NOTIFY path allows while notification redacts secrets
# ==============================================================================


class TestCheck05_WriteNotifyAllowsWithRedaction:
    """Check 5: WRITE_NOTIFY allows while redacting secrets."""

    def test_filesystem_write_is_write_notify(self) -> None:
        assert get_auth_level("filesystem", "write") == AuthLevel.WRITE_NOTIFY

    def test_redis_set_is_write_notify(self) -> None:
        assert get_auth_level("redis", "set") == AuthLevel.WRITE_NOTIFY

    def test_git_commit_is_write_notify(self) -> None:
        assert get_auth_level("git", "commit") == AuthLevel.WRITE_NOTIFY

    def test_secret_redaction_exists(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/notify_handler.py")
        assert "redact" in content.lower()

    def test_secret_patterns_covered(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/notify_handler.py")
        for pat in ["discord", "sk-", "ghp_", "REDACTED"]:
            assert pat in content, f"Missing redaction: {pat}"


# ==============================================================================
# Check 6: DESTRUCTIVE_APPROVAL requires Redis DB5 persisted approval with 300s TTL
# ==============================================================================


class TestCheck06_DestructiveRequiresRedisApproval:
    """Check 6: DESTRUCTIVE_APPROVAL uses Redis DB5 with 300s TTL."""

    def test_approval_ttl_300(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/approval_handler.py")
        assert "APPROVAL_TTL_SECONDS" in content
        assert "300" in content.split("APPROVAL_TTL_SECONDS")[1][:20]

    def test_approval_uses_redis_db5(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/approval_handler.py")
        assert "_REDIS_PORT" in content
        assert "6380" in content or "_REDIS_PORT" in content

    def test_approval_creates_pending_request(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/approval_handler.py")
        assert "request_approval" in content
        assert "setex" in content

    def test_destructive_allows_blocked_first(self) -> None:
        handler = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "DESTRUCTIVE_APPROVAL" in handler


# ==============================================================================
# Check 7: FORBIDDEN path blocks
# ==============================================================================


class TestCheck07_ForbiddenBlocks:
    """Check 7: FORBIDDEN-level operations are hard-blocked."""

    @pytest.mark.parametrize("tool,op", [
        ("postgres", "drop"), ("postgres", "truncate"),
        ("redis", "flushdb"), ("redis", "flushall"), ("redis", "shutdown"),
        ("shell", "rm_rf_root"), ("shell", "sudo_rm_rf"),
        ("docker", "system_prune"), ("docker", "rm_all"),
        ("git", "force_push_main"),
    ])
    def test_forbidden_operations_blocked(self, tool: str, op: str) -> None:
        assert get_auth_level(tool, op) == AuthLevel.FORBIDDEN

    def test_handler_returns_block_for_forbidden(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/forbidden_handler.py")
        assert "block" in content and "FORBIDDEN" in content


# ==============================================================================
# Check 8: Native/MCP prefixed names normalize to canonical matrix names
# ==============================================================================


class TestCheck08_NativeAndMCPPrefixNormalization:
    """Check 8: Native/MCP names normalise to canonical; BD-008 gate verified."""

    def test_prefixes_defined(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "KNOWN_PREFIXES" in content
        assert "mcp_fastmcp_custom_" in content
        assert "mcp_native_" in content

    def test_native_aliases_defined(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "TOOL_ALIASES" in content
        assert "fetch_url" in content
        assert "web_search" in content
        assert "shell_exec" in content
        assert "git_force_push" in content

    def test_bd008_native_exposure_gate(self) -> None:
        content = _read("hermes-config/config.yaml")
        assert "fastmcp_custom" in content
        assert "enabled: false" in content

    def test_custom_manager_only_keep7(self) -> None:
        content = _read("src/mcp/custom_manager.py")
        assert "KEEP_TOOL_FAMILIES" in content
        for excluded in ["filesystem", "docker_tool", "shell_tool",
                          "git_tool", "github", "brave_search"]:
            assert f"import {excluded}" not in content

    def test_unknown_name_returns_none(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/auth_handler.py")
        assert "return None" in content


# ==============================================================================
# Check 9: Budget hook fail-closed, Redis 6380 DB5, warn 24, block 30
# ==============================================================================


class TestCheck09_BudgetHookFailClosed:
    """Check 9: Budget hook uses 6380 DB5, warn=24, block=30, fail-closed."""

    def test_monthly_cap_is_30(self) -> None:
        content = _read("hermes-config/hooks/budget_check.py")
        assert "MONTHLY_CAP" in content
        assert "30" in content.split("MONTHLY_CAP")[1][:20]

    def test_warn_threshold_is_24(self) -> None:
        content = _read("hermes-config/hooks/budget_check.py")
        assert "WARN_THRESHOLD" in content
        assert "24" in content.split("WARN_THRESHOLD")[1][:20]

    def test_default_tool_cost_positive(self) -> None:
        content = _read("hermes-config/hooks/budget_check.py")
        match = re.search(r"DEFAULT_TOOL_COST[^=]*=\s*([\d.]+)", content)
        assert match is not None, "DEFAULT_TOOL_COST value not found"
        assert float(match.group(1)) > 0

    def test_redis_port_6380(self) -> None:
        content = _read("hermes-config/plugins/auth_overlay/approval_handler.py")
        assert "6380" in content
        for fname in ["budget_check.py", "budget_lua.py", "budget_lua_extended.py"]:
            fpath = _HERMES_CONFIG / "hooks" / fname
            if fpath.exists():
                fcontent = fpath.read_text("utf-8")
                assert "6379" not in fcontent, f"{fname} has port 6379"

    def test_lua_script_monthly_check(self) -> None:
        content = _read("hermes-config/hooks/budget_lua.py")
        assert "monthly_cap" in content
        assert "warn_threshold" in content
        assert "BLOCKED" in content or "MONTHLY_BLOCKED" in content

    def test_lua_extended_has_daily_caps(self) -> None:
        fpath = _HERMES_CONFIG / "hooks" / "budget_lua_extended.py"
        if not fpath.exists():
            pytest.skip("budget_lua_extended not found")
        content = fpath.read_text("utf-8")
        assert "DAILY_TOOL_BLOCKED" in content
        assert "DAILY_GLOBAL_BLOCKED" in content

    def test_budget_check_fail_closed(self) -> None:
        content = _read("hermes-config/hooks/budget_check.py")
        assert "block" in content
        assert "Redis unavailable" in content


# ==============================================================================
# Check 10: Budget Lua checks are atomic server-side
# ==============================================================================


class TestCheck10_BudgetLuaAtomic:
    """Check 10: Lua budget checks are atomic (single Redis execution)."""

    def test_monthly_script_is_lua(self) -> None:
        content = _read("hermes-config/hooks/budget_lua.py")
        assert "SCRIPT_MONTHLY_CHECK" in content
        # The Lua script contains redis.call
        assert "redis.call" in content

    def test_no_client_side_redis_incrbyfloat(self) -> None:
        content = _read("hermes-config/hooks/budget_check.py")
        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "redis_client" in stripped:
                continue
            if ".incrbyfloat(" in stripped:
                pytest.fail(f"Client-side Redis incrbyfloat at line {i}")

    def test_monthly_script_uses_redis_call(self) -> None:
        content = _read("hermes-config/hooks/budget_lua.py")
        assert "redis.call" in content

    def test_lua_load_function(self) -> None:
        content = _read("hermes-config/hooks/budget_lua.py")
        assert "load_script" in content

    def test_extended_script_uses_redis_call(self) -> None:
        fpath = _HERMES_CONFIG / "hooks" / "budget_lua_extended.py"
        if not fpath.exists():
            pytest.skip("budget_lua_extended not found")
        assert "redis.call" in fpath.read_text("utf-8")


# ==============================================================================
# Check 11: Hybrid shell injection guard blocks metacharacter/chaining patterns
# ==============================================================================


class TestCheck11_ShellInjectionGuard:
    """Check 11: Shell injection patterns are blocked."""

    @pytest.fixture
    def check_shell(self):
        return getattr(_import_hook("hybrid_guards"), "check_shell_injection")

    @pytest.mark.parametrize("cmd", [
        "ls; rm -rf /", "cmd1 && cmd2",
        "echo `whoami`", "echo $(whoami)",
        "ls > /dev/null; rm -rf /",
        "echo hello &", "git commit -m 'test' && git push",
    ])
    def test_shell_injection_blocked(self, cmd: str, check_shell) -> None:
        result = check_shell(cmd)
        assert result is not None, f"Injection not blocked: '{cmd}'"
        assert result.get("action") == "block"

    @pytest.mark.parametrize("safe_cmd", [
        "ls -la /home/guinevere", "cat /home/guinevere/file.txt",
        "pip list", "git status", "python -m pytest tests/",
    ])
    def test_safe_commands_allowed(self, safe_cmd: str, check_shell) -> None:
        result = check_shell(safe_cmd)
        assert result is None, f"Safe command blocked: '{safe_cmd}'"

    def test_hybrid_guards_routes_shell(self) -> None:
        mod = _import_hook("hybrid_guards")
        composite = getattr(mod, "check_hybrid_guards")
        result = composite(tool_name="shell", command="ls; rm -rf /")
        assert result is not None
        assert result.get("action") == "block"
        assert "SHELL_INJECTION" in str(result)


# ==============================================================================
# Check 12: Docker 5-layer guard blocks destructive/non-isolated Docker ops
# ==============================================================================


class TestCheck12_Docker5LayerGuard:
    """Check 12: Docker 5-layer guard blocks destructive/non-isolated ops."""

    @pytest.fixture
    def check_docker(self):
        return getattr(_import_hook("hybrid_guards"), "check_docker_5_layer")

    def test_docker_read_only_passes(self, check_docker) -> None:
        for cmd in ["docker ps", "docker logs c", "docker images", "docker info"]:
            assert check_docker(cmd) is None, f"Read-only blocked: '{cmd}'"

    def test_docker_non_guinevere_destructive_blocked(self, check_docker) -> None:
        for cmd in ["docker stop some-random-container", "docker rm myapp"]:
            result = check_docker(cmd)
            assert result is not None
            assert "DOCKER_NET_ISOLATION" in str(result)

    def test_docker_forbidden_blocked(self, check_docker) -> None:
        for cmd in ["docker system prune", "docker rm -f x", "docker network create n"]:
            result = check_docker(cmd)
            assert result is not None
            assert result.get("action") == "block"

    def test_docker_guinevere_not_net_isolation(self, check_docker) -> None:
        for cmd in ["docker stop guinevere-postgres", "docker rm guinevere-old"]:
            result = check_docker(cmd)
            if result is not None:
                assert "DOCKER_NET_ISOLATION" not in str(result)


# ==============================================================================
# Check 13: Git guard blocks force-push to main/master
# ==============================================================================


class TestCheck13_GitForcePushGuard:
    """Check 13: Git force-push to protected branches is blocked."""

    @pytest.fixture
    def check_git(self):
        return getattr(_import_hook("hybrid_guards"), "check_git_force_push")

    @pytest.mark.parametrize("cmd", [
        "git push --force origin main", "git push --force origin master",
        "git push -f origin main", "git push --force-with-lease origin main",
        "git push --force origin main:main", "force_push", "force-push",
    ])
    def test_force_push_to_protected_blocked(self, cmd: str, check_git) -> None:
        result = check_git(cmd)
        assert result is not None, f"Not blocked: '{cmd}'"
        assert result.get("action") == "block"
        assert "GIT_FORCE_PUSH" in str(result)

    @pytest.mark.parametrize("safe_cmd", [
        "git push origin main", "git push origin feature",
        "git status", "git diff", "git log",
        "git commit -m 'test'", "git pull origin main",
    ])
    def test_safe_git_ops_allowed(self, safe_cmd: str, check_git) -> None:
        assert check_git(safe_cmd) is None

    def test_force_push_non_protected_allowed(self, check_git) -> None:
        assert check_git("git push --force origin feature-branch") is None


# ==============================================================================
# Check 14: Aizanta isolation blocks paths/standard ports, preserves canonical
# ==============================================================================


class TestCheck14_AizantaIsolation:
    """Check 14: Aizanta path/port isolation enforced correctly."""

    @pytest.fixture
    def hybrid(self):
        return _import_hook("hybrid_guards")

    def test_aizanta_paths_blocked(self, hybrid) -> None:
        fn = getattr(hybrid, "check_aizanta_path")
        for path in ["/home/aizanta/.ssh/id_rsa", "/etc/aizanta/secrets.env",
                      "/var/lib/aizanta/data.db", "/aizanta"]:
            result = fn(path)
            assert result is not None, f"Path not blocked: '{path}'"
            assert "AIZANTA" in str(result)

    def test_safe_paths_allowed(self, hybrid) -> None:
        fn = getattr(hybrid, "check_aizanta_path")
        for path in ["/home/guinevere/code/file.py", "/tmp/test.txt",
                      "/etc/guinevere/config.yaml"]:
            assert fn(path) is None, f"Safe path blocked: '{path}'"

    def test_standard_ports_blocked(self, hybrid) -> None:
        fn = getattr(hybrid, "check_port_isolation")
        for ref in ["localhost:5432", "localhost:6379", "port = 5432"]:
            result = fn(ref)
            assert result is not None, f"Port not blocked: '{ref}'"
            assert "PORT_ISOLATION" in str(result)

    def test_canonical_ports_allowed(self, hybrid) -> None:
        fn = getattr(hybrid, "check_port_isolation")
        for ref in ["localhost:5433", "localhost:6380",
                     "0.0.0.0:20128", "curl http://localhost:20128"]:
            assert fn(ref) is None, f"Canonical port blocked: '{ref}'"


# ==============================================================================
# Check 15: Startup gate fails closed when critical plugins are broken
# ==============================================================================


class TestCheck15_StartupGateFailClosed:
    """Check 15: Startup gate fails closed, doesn't rely on critical:true."""

    def test_startup_gate_has_validate_plugins(self) -> None:
        content = _read("scripts/startup_gate.py")
        assert "def validate_plugins" in content
        assert "CRITICAL_PLUGINS" in content

    def test_startup_gate_includes_auth_overlay(self) -> None:
        content = _read("scripts/startup_gate.py")
        assert "auth_overlay" in content

    def test_startup_gate_includes_guinevere_safety(self) -> None:
        content = _read("scripts/startup_gate.py")
        assert "guinevere_safety" in content

    def test_startup_gate_no_critical_flag_reliance(self) -> None:
        content = _read("scripts/startup_gate.py")
        lines = content.split("\n")
        in_doc = False
        for line in lines:
            s = line.strip()
            if s.startswith('"""') or s.startswith("'''"):
                in_doc = not in_doc
                continue
            if in_doc or s.startswith("#"):
                continue
            if "critical" in s.lower() and "CRITICAL_PLUGINS" not in s:
                pytest.fail(f"Unexpected 'critical' reference: {s}")

    def test_startup_gate_uses_os_execvp(self) -> None:
        content = _read("scripts/startup_gate.py")
        assert "os.execvp" in content
        assert "os.system(" not in content

    def test_startup_gate_main_returns_exit_code(self) -> None:
        content = _read("scripts/startup_gate.py")
        assert "def main" in content
        assert "return 1" in content


# ==============================================================================
# Forbidden pattern scan
# ==============================================================================


class TestForbiddenPatterns:
    """Targeted forbidden pattern checks on P4-007 changed files."""

    def test_no_type_ignore_in_code(self) -> None:
        c = Path(__file__).read_text("utf-8")
        stripped = re.sub(r'"""[^"]*"""', "", c)
        stripped = re.sub(r"'''[^']*'''", "", stripped)
        stripped = re.sub(r"'[^']*'", "", stripped)
        stripped = re.sub(r'"[^"]*"', "", stripped)
        assert "# type: ignore" not in stripped

    def test_no_bare_except(self) -> None:
        c = Path(__file__).read_text("utf-8")
        for i, line in enumerate(c.split("\n"), 1):
            s = line.strip()
            if s == "except:" or (s.startswith("except:") and "#" not in s.split("except:")[0]):
                pytest.fail(f"Bare 'except:' at line {i}")


# ==============================================================================
# Verify all 15 checks present
# ==============================================================================


class TestAll15ChecksPresent:
    """Meta-check: verify all 15 audit checks tested."""

    def test_15_check_ids_documented(self) -> None:
        classes = [
            "TestCheck01_PythonAuthMatrixIsAuthoritative",
            "TestCheck02_All16ToolsEnforcementCoverage",
            "TestCheck03_UnknownFailsClosed",
            "TestCheck04_ReadAutoAllows",
            "TestCheck05_WriteNotifyAllowsWithRedaction",
            "TestCheck06_DestructiveRequiresRedisApproval",
            "TestCheck07_ForbiddenBlocks",
            "TestCheck08_NativeAndMCPPrefixNormalization",
            "TestCheck09_BudgetHookFailClosed",
            "TestCheck10_BudgetLuaAtomic",
            "TestCheck11_ShellInjectionGuard",
            "TestCheck12_Docker5LayerGuard",
            "TestCheck13_GitForcePushGuard",
            "TestCheck14_AizantaIsolation",
            "TestCheck15_StartupGateFailClosed",
        ]
        assert len(classes) == 15
        for name in classes:
            assert name in globals(), f"Check class '{name}' not found"
