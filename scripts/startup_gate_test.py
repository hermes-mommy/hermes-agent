"""Tests for P4-006 Startup Gate (``scripts/startup_gate.py``).

Test matrix:
    - Broken auth_overlay  → gate blocks (exit 1)
    - Broken guinevere_safety → gate blocks (exit 1)
    - Both valid           → gate passes (exit 0)
    - Missing manifest     → gate blocks
    - Missing register()   → gate blocks
    - Missing __init__.py  → gate blocks
    - Hermes process replacement is not called on validation failure
    - Hermes process replacement is called with list arguments on success
    - ``--validate-only`` flag works without exec
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts import startup_gate as gate


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def tmp_plugins(tmp_path: Path) -> Path:
    """Create a temporary plugin base directory."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    return plugins_dir


def _create_plugin(
    base: Path,
    name: str,
    manifest_name: str,
    manifest_content: str = "",
    init_content: str = "",
    extra_files: dict[str, str] | None = None,
) -> Path:
    """Create a plugin directory under *base* with the given files."""
    plugin_dir = base / name
    plugin_dir.mkdir(exist_ok=True)

    # Manifest
    (plugin_dir / manifest_name).write_text(manifest_content, encoding="utf-8")

    # __init__.py
    (plugin_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    # Extra files
    if extra_files:
        for fname, fcontent in extra_files.items():
            (plugin_dir / fname).write_text(fcontent, encoding="utf-8")

    return plugin_dir


def _valid_auth_overlay_init() -> str:
    """Return a minimal valid auth_overlay ``__init__.py`` with ``register()``."""
    return """\
def register(ctx):
    ctx.register_hook("pre_tool_call", lambda **kw: None)
"""


def _valid_guinevere_safety_init() -> str:
    """Return a minimal valid guinevere_safety ``__init__.py``."""
    return """\
from .plugin import GuinevereSafetyPlugin
"""


def _valid_guinevere_safety_plugin() -> str:
    """Return a minimal valid guinevere_safety ``plugin.py``."""
    return """\
class GuinevereSafetyPlugin:
    def inject_dynamic_state(self, context):
        return context
    def update_state(self, context):
        return context
"""


_VALID_AUTH_OVERLAY_MANIFEST = """\
name: auth_overlay
version: 1.0.0
hooks:
  - pre_tool_call
"""

_VALID_GUINEVERE_SAFETY_MANIFEST = """\
name: guinevere_safety
version: 1.0.0
hooks:
  - event: pre_llm_call
    handler: inject_dynamic_state
    priority: 95
  - event: post_llm_call
    handler: update_state
    priority: 55
"""

_INVALID_YAML = """\
name: broken
  - indented badly
 hooks: [unclosed
"""


# =========================================================================
# Helper: set plugin dirs and reimport
# =========================================================================


@pytest.fixture(autouse=True)
def _reset_global_state() -> Iterator[None]:
    """Reset global state after each test.

    Restores ``CRITICAL_PLUGINS``, ``HERMES_PLUGIN_DIRS``, and cleans up
    ``sys.modules`` entries created by the startup gate's import machinery.
    """
    orig_dirs = list(gate.HERMES_PLUGIN_DIRS)
    orig_plugins = list(gate.CRITICAL_PLUGINS)
    yield
    gate.HERMES_PLUGIN_DIRS = list(orig_dirs)
    gate.CRITICAL_PLUGINS = list(orig_plugins)
    # Remove any plugin-name-prefixed or _p4gate_ modules from sys.modules
    # to prevent caching conflicts between test cases.
    plugin_prefixes = ("auth_overlay", "guinevere_safety", "_p4gate_")
    stale_keys = [k for k in sys.modules if k.startswith(plugin_prefixes)]
    for k in stale_keys:
        sys.modules.pop(k, None)


# =========================================================================
# Tests: Broken plugins
# =========================================================================


class TestBrokenPlugins:
    """Scenarios where one or both critical plugins are broken."""

    def test_broken_auth_overlay_import_error_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """A broken auth_overlay import must cause validation to fail."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content="raise ImportError('cannot import name X')\n",
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_broken_auth_overlay_syntax_error_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """A syntax error in auth_overlay __init__.py must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content="def register(ctx  # missing paren\n",
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_broken_guinevere_safety_missing_dir_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """Missing guinevere_safety directory must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        # guinevere_safety intentionally not created
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_broken_guinevere_safety_import_error_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """Import failure in guinevere_safety must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content="from .nonexistent import Thing\n",
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_both_broken_blocks(self, tmp_plugins: Path) -> None:
        """Both plugins broken must still report validation failure."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content="raise RuntimeError('broken')\n",
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content="raise RuntimeError('broken')\n",
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False


# =========================================================================
# Tests: Valid plugins
# =========================================================================


class TestValidPlugins:
    """Scenarios where both plugins are valid and should pass."""

    def test_both_valid_pass(self, tmp_plugins: Path) -> None:
        """Both plugins correctly configured must pass validation."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is True

    def test_real_plugins_validate(self) -> None:
        """Test that the actual project plugins pass validation.

        This integration test runs against the real codebase plugins.
        It requires the project to be importable.
        """
        # Reset to the real plugin dirs by pointing HERMES_PLUGIN_DIRS
        # at the project's actual plugin location.
        gate.HERMES_PLUGIN_DIRS = [
            (Path(__file__).resolve().parent.parent / "hermes-config" / "plugins"),
        ]
        result = gate.validate_plugins()
        assert result is True, "Real project plugins must pass validation"


# =========================================================================
# Tests: Structural failures
# =========================================================================


class TestStructuralFailures:
    """Scenarios involving missing files or incomplete plugins."""

    def test_missing_manifest_blocks(self, tmp_plugins: Path) -> None:
        """Missing manifest must block startup."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content="",
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        # Delete the manifest
        (tmp_plugins / "guinevere_safety" / "manifest.yaml").unlink()
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_invalid_yaml_manifest_blocks(self, tmp_plugins: Path) -> None:
        """Invalid YAML manifest must block startup."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_INVALID_YAML,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_missing_register_blocks(self, tmp_plugins: Path) -> None:
        """Auth_overlay without register() must block.

        ``expects_register`` is True for auth_overlay, so a missing
        ``register()`` function must fail validation.
        """
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            # __init__.py with no register function
            init_content="# no register function\n",
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_register_does_not_register_hooks_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """register() that doesn't call ctx.register_hook() must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content="def register(ctx): pass  # no-op\n",
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_missing_init_py_blocks(self, tmp_plugins: Path) -> None:
        """Missing __init__.py must block startup."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        # Delete __init__.py for auth_overlay
        (tmp_plugins / "auth_overlay" / "__init__.py").unlink()
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_manifest_is_not_a_mapping_blocks(self, tmp_plugins: Path) -> None:
        """Manifest that parses to a list (not dict) must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content="- just a list\n- not a mapping\n",
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False


# =========================================================================
# Tests: main() and exec behavior
# =========================================================================


class TestMainFunction:
    """Tests for the ``main()`` entry point."""

    def test_main_validate_only_passes(self, tmp_plugins: Path) -> None:
        """``--validate-only`` must return 0 when plugins are valid."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        rc = gate.main(["--validate-only"])
        assert rc == 0

    def test_main_validate_only_fails(self, tmp_plugins: Path) -> None:
        """``--validate-only`` must return 1 when a plugin is broken."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        # guinevere_safety not created
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        rc = gate.main(["--validate-only"])
        assert rc == 1

    def test_exec_not_called_on_failure(
        self, tmp_plugins: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """os.execvp must NOT be called when validation fails."""
        exec_calls: list[tuple[str, list[str]]] = []

        def _fake_execvp(file: str, args: list[str]) -> None:
            exec_calls.append((file, args))

        monkeypatch.setattr(os, "execvp", _fake_execvp)

        # Only auth_overlay exists, guinevere_safety missing
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        rc = gate.main([])
        assert rc == 1
        assert len(exec_calls) == 0, "execvp must not be called on failure"

    def test_exec_called_with_list_args_on_success(
        self, tmp_plugins: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """os.execvp must be called with list arguments on success."""
        exec_calls: list[tuple[str, list[str]]] = []

        def _fake_execvp(file: str, args: list[str]) -> None:
            exec_calls.append((file, args))
            raise SystemExit(0)  # Simulate exec replacing the process

        monkeypatch.setattr(os, "execvp", _fake_execvp)

        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        try:
            _ = gate.main([])
        except SystemExit:
            pass

        assert len(exec_calls) == 1, "execvp must be called exactly once"
        called_file, called_args = exec_calls[0]
        assert called_file == "hermes"
        assert called_args == ["hermes", "gateway", "run", "--accept-hooks"]

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "hermes-config" / "plugins").exists(),
        reason="Real plugin directory not found",
    )
    def test_main_with_real_plugins_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() must return 0 when run against the real project plugins."""
        exec_calls: list[tuple[str, list[str]]] = []

        def _fake_execvp(file: str, args: list[str]) -> None:
            exec_calls.append((file, args))
            raise SystemExit(0)

        monkeypatch.setattr(os, "execvp", _fake_execvp)

        gate.HERMES_PLUGIN_DIRS = [
            Path(__file__).resolve().parent.parent / "hermes-config" / "plugins",
        ]
        try:
            _ = gate.main([])
        except SystemExit:
            pass

        assert len(exec_calls) == 1, "execvp must be called when real plugins are valid"


# =========================================================================
# Tests: Unit-level helpers
# =========================================================================


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_find_plugin_dir_found(self, tmp_plugins: Path) -> None:
        """_find_plugin_dir returns the directory when it exists."""
        _create_plugin(
            tmp_plugins,
            "test_plugin",
            manifest_name="plugin.yaml",
            manifest_content="name: test\n",
            init_content="# empty\n",
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        result = gate._find_plugin_dir("test_plugin")
        assert result is not None
        assert result.name == "test_plugin"

    def test_find_plugin_dir_not_found(self, tmp_plugins: Path) -> None:
        """_find_plugin_dir returns None when the directory does not exist."""
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate._find_plugin_dir("nonexistent") is None

    def test_find_plugin_class_found(self) -> None:
        """_find_plugin_class finds a class with expected methods."""
        import types

        mod = types.ModuleType("_test_mod")
        exec(
            "class MyPlugin:\n"
            "    def handler_a(self): pass\n"
            "    def handler_b(self): pass\n",
            mod.__dict__,
        )
        cls = gate._find_plugin_class(mod, ["handler_a", "handler_b"])
        assert cls is not None
        assert cls.__name__ == "MyPlugin"

    def test_find_plugin_class_not_found(self) -> None:
        """_find_plugin_class returns None for modules without matching class."""
        import types

        mod = types.ModuleType("_test_mod")
        exec(
            "class MyPlugin:\n"
            "    def handler_a(self): pass\n",
            mod.__dict__,
        )
        cls = gate._find_plugin_class(mod, ["handler_a", "handler_b"])
        assert cls is None

    def test_validate_manifest_empty(self, tmp_path: Path) -> None:
        """An empty manifest should produce an error."""
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("", encoding="utf-8")
        errors: list[str] = []
        gate._validate_manifest(manifest, errors)
        assert len(errors) >= 1

    def test_validate_manifest_valid(self, tmp_path: Path) -> None:
        """A valid YAML manifest should produce no errors."""
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("name: test\nversion: 1.0\n", encoding="utf-8")
        errors: list[str] = []
        gate._validate_manifest(manifest, errors)
        assert len(errors) == 0

    def test_validate_manifest_invalid_yaml(self, tmp_path: Path) -> None:
        """Invalid YAML should produce a parse error."""
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(": : invalid :\n", encoding="utf-8")
        errors: list[str] = []
        gate._validate_manifest(manifest, errors)
        assert len(errors) >= 1


# =========================================================================
# Tests: No forbidden patterns
# =========================================================================


class TestForbiddenPatterns:
    """Verify the startup gate itself conforms to the scaffold's forbidden rules."""

    def test_no_shell_mediated_process_call(self) -> None:
        """startup_gate.py must avoid shell-mediated process calls."""
        source = Path(gate.__file__).read_text(encoding="utf-8")
        forbidden_call = "os." + "system"
        assert forbidden_call not in source

    def test_no_shell_boolean_argument(self) -> None:
        """startup_gate.py must not request shell-mediated subprocess execution."""
        source = Path(gate.__file__).read_text(encoding="utf-8")
        forbidden_arg = "shell" + "=True"
        assert forbidden_arg not in source

    def test_no_return_zero_on_failure(self) -> None:
        """validate_plugins() must return False, not 0."""
        # validate_plugins() returns bool, so "return 0" would be a type error
        # Verify main() returns 1 on failure, not 0
        source = Path(gate.__file__).read_text(encoding="utf-8")
        # Check there's no "return 0" in failure paths
        lines = source.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "return 0":
                # Allow only the success path after execvp (pragma: no cover)
                ctx_before = "\n".join(lines[max(0, i - 3):i])
                assert "os.execvp" in ctx_before, (
                    f"Unexpected 'return 0' at line {i + 1}"
                )

    def test_no_type_suppression_comment(self) -> None:
        """startup_gate.py must not use type-suppression comments."""
        source = Path(gate.__file__).read_text(encoding="utf-8")
        forbidden_comment = "# type" + ": ignore"
        assert forbidden_comment not in source

    def test_no_broad_top_type_escape(self) -> None:
        """startup_gate.py must not use the broad top-type escape."""
        source = Path(gate.__file__).read_text(encoding="utf-8")
        forbidden_name = "A" + "ny"
        assert forbidden_name not in source


# =========================================================================
# Tests: Edge cases
# =========================================================================


class TestEdgeCases:
    """Edge-case scenarios for the startup gate."""

    def test_register_function_raises_exception_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """register() that raises an exception must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content="def register(ctx): raise RuntimeError('boom')\n",
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_guinevere_safety_missing_handlers_blocks(
        self, tmp_plugins: Path
    ) -> None:
        """Missing manifest-declared handlers must block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        # Create guinevere_safety but with a plugin that's missing the handlers
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={
                "plugin.py": """\
class GuinevereSafetyPlugin:
    def some_other_method(self):
        pass
"""
            },
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_manifest_is_not_a_mapping_not_list(self, tmp_plugins: Path) -> None:
        """Manifest that parses to a scalar must also block."""
        _create_plugin(
            tmp_plugins,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content="just a string scalar\n",
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            tmp_plugins,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )
        gate.HERMES_PLUGIN_DIRS = [tmp_plugins]
        assert gate.validate_plugins() is False

    def test_plugin_directory_in_multiple_locations(
        self, tmp_path: Path
    ) -> None:
        """Plugin found in second search directory should still validate."""
        dir1 = tmp_path / "dir1" / "plugins"
        dir2 = tmp_path / "dir2" / "plugins"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)

        # Only in dir2
        _create_plugin(
            dir2,
            "auth_overlay",
            manifest_name="plugin.yaml",
            manifest_content=_VALID_AUTH_OVERLAY_MANIFEST,
            init_content=_valid_auth_overlay_init(),
        )
        _create_plugin(
            dir2,
            "guinevere_safety",
            manifest_name="manifest.yaml",
            manifest_content=_VALID_GUINEVERE_SAFETY_MANIFEST,
            init_content=_valid_guinevere_safety_init(),
            extra_files={"plugin.py": _valid_guinevere_safety_plugin()},
        )

        gate.HERMES_PLUGIN_DIRS = [dir1, dir2]
        assert gate.validate_plugins() is True
