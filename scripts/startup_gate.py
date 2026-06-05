#!/usr/bin/env python3
"""P4-006 Startup Gate — fail-closed validation of critical Hermes plugins.

Validates that critical plugins (``auth_overlay``, ``guinevere_safety``) are
properly installed, configured, importable, and capable of registering their
hooks **before** Hermes Gateway is started.  Exits non-zero on any failure so
that systemd / the launcher never runs an unprotected gateway.

Design decisions:
  - Does not rely on unsupported Hermes mandatory-plugin manifest flags.
  - Avoids shell-mediated execution (uses ``os.execvp`` with list arguments).
  - Uses list-argument ``os.execvp`` for the valid-path Hermes start.
  - Validates plugin directories, manifests, Python imports AND the
    presence of the expected ``register(ctx)`` function (for
    ``register``-based plugins) or manifest-declared hook handlers
    (for manifest-declared plugins).
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Optional, cast

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HERMES_PLUGIN_DIRS: list[Path] = [
    Path("hermes-config/plugins").resolve(),
    Path.home() / ".hermes" / "plugins",
]

# Each entry describes one critical plugin.
# Fields:
#   name              — plugin directory name
#   expected_manifest — basename of the manifest file (plugin.yaml, manifest.yaml)
#   expects_register  — whether the plugin uses Python register(ctx)
#   expected_hooks    — list of expected hook/handler names to verify
CRITICAL_PLUGINS: list[dict[str, object]] = [
    {
        "name": "auth_overlay",
        "expected_manifest": "plugin.yaml",
        "expects_register": True,
        "expected_hooks": ["pre_tool_call"],
    },
    {
        "name": "guinevere_safety",
        "expected_manifest": "manifest.yaml",
        "expects_register": False,
        "expected_hooks": ["inject_dynamic_state", "update_state"],
    },
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stderr,
)
_log = logging.getLogger("startup_gate")


# ---------------------------------------------------------------------------
# Mock PluginContext
# ---------------------------------------------------------------------------


class _MockPluginContext:
    """Minimal mock of the Hermes ``PluginContext`` for pre-start validation.

    Records calls to ``register_hook()`` so the gate can verify that the
    plugin actually registered at least one hook.
    """

    def __init__(self) -> None:
        self.registered_hooks: list[tuple[str, object]] = []

    def register_hook(self, hook_name: str, callback: object) -> None:
        """Record the hook registration for later verification."""
        self.registered_hooks.append((hook_name, callback))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_plugin_dir(name: str) -> Optional[Path]:
    """Return the first directory where *name* is found, or ``None``."""
    for base in HERMES_PLUGIN_DIRS:
        candidate = base / name
        if candidate.is_dir():
            return candidate
    return None


def _find_plugin_class(module: object, expected_methods: list[str]) -> Optional[type]:
    """Find a class in *module* having all *expected_methods*.

    Considers both classes defined in *module* and classes imported into it
    (e.g. ``from .plugin import GuinevereSafetyPlugin``).
    Returns the first matching class or ``None``.
    """
    import inspect

    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if all(callable(getattr(obj, m, None)) for m in expected_methods):
            return obj
    return None


# ---------------------------------------------------------------------------
# Per-plugin validation
# ---------------------------------------------------------------------------


def _verify_register_hooks(
    name: str,
    register_fn: object,
    errors: list[str],
) -> None:
    """Try calling *register_fn* with a mock context to verify hook registration."""
    mock_ctx = _MockPluginContext()

    try:
        callable_register = cast(Callable[[_MockPluginContext], object], register_fn)
        callable_register(mock_ctx)
    except Exception as exc:
        errors.append(f"register() call failed for {name}: {exc}")
        return

    if not mock_ctx.registered_hooks:
        errors.append(
            f"register() for {name} did not register any hooks via "
            f"ctx.register_hook()"
        )


def _verify_manifest_handlers(
    name: str,
    module: object,
    expected_hooks: list[str],
    errors: list[str],
) -> None:
    """Verify that manifest-declared handler functions exist in the plugin.

    For plugins that use ``manifest.yaml`` to declare hooks (as opposed to
    Python ``register()``), we find the main plugin class and verify each
    handler name resolves to a callable method.
    """
    plugin_class = _find_plugin_class(module, expected_hooks)
    if plugin_class is None:
        errors.append(
            f"Could not find plugin class with handlers {expected_hooks} "
            f"in {name}"
        )
        return

    for handler_name in expected_hooks:
        handler = getattr(plugin_class, handler_name, None)
        if not callable(handler):
            errors.append(
                f"Handler '{handler_name}' declared in manifest "
                f"is not a callable method on {plugin_class.__name__} "
                f"in {name}"
            )


def _validate_manifest(manifest_path: Path, errors: list[str]) -> None:
    """Validate that *manifest_path* exists and contains valid YAML."""
    if not manifest_path.is_file():
        errors.append(f"Manifest file missing: {manifest_path}")
        return

    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"Cannot read manifest {manifest_path}: {exc}")
        return

    try:
        import yaml
    except ImportError:
        # PyYAML not installed — basic structural check only.
        if not manifest_text.strip():
            errors.append(f"Manifest {manifest_path} is empty")
        return

    try:
        parsed = yaml.safe_load(manifest_text)
    except yaml.YAMLError as exc:
        errors.append(f"Manifest YAML parse error in {manifest_path}: {exc}")
        return

    if not isinstance(parsed, dict):
        errors.append(
            f"Manifest {manifest_path} is not a valid YAML mapping "
            f"(got {type(parsed).__name__})"
        )


def _import_plugin_module(name: str, plugin_dir: Path) -> object:
    """Import a plugin's package and return the module.

    Adds the plugin's parent directory to ``sys.path``, then does a fresh
    ``importlib.import_module(name)`` so that relative imports in the
    plugin's ``__init__.py`` resolve correctly (``from .submodule import X``
    looks for ``{name}/submodule.py`` relative to the plugin base dir).
    Cleans up ``sys.modules`` afterwards so subsequent calls (e.g. from
    different temp directories during testing) get a fresh module.
    """
    plugin_base = str(plugin_dir.parent)
    # Remove any cached import to force a fresh load.
    sys.modules.pop(name, None)

    sys.path.insert(0, plugin_base)
    try:
        mod = importlib.import_module(name)
    finally:
        # Restore sys.path immediately.
        if sys.path and sys.path[0] == plugin_base:
            sys.path.pop(0)

    return mod


def _validate_plugin(plugin_cfg: dict[str, object]) -> list[str]:
    """Validate a single plugin, returning a list of error messages.

    Empty list means the plugin is valid.
    """
    errors: list[str] = []

    name_obj = plugin_cfg.get("name")
    manifest_name_obj = plugin_cfg.get("expected_manifest")
    expects_register_obj = plugin_cfg.get("expects_register")

    if not isinstance(name_obj, str):
        errors.append("Plugin config missing 'name' string")
        return errors
    if not isinstance(manifest_name_obj, str):
        errors.append(f"Plugin {name_obj} missing 'expected_manifest' string")
        return errors
    if not isinstance(expects_register_obj, bool):
        errors.append(f"Plugin {name_obj} missing 'expects_register' bool")
        return errors

    name: str = name_obj
    manifest_name: str = manifest_name_obj
    expects_register: bool = expects_register_obj

    # 1. Directory exists
    plugin_dir = _find_plugin_dir(name)
    if plugin_dir is None:
        errors.append(f"Plugin directory not found: {name}")
        return errors  # Cannot proceed further.

    # 2. Manifest exists and is valid YAML
    manifest_path = plugin_dir / manifest_name
    _validate_manifest(manifest_path, errors)

    # 3. __init__.py exists and is importable
    init_path = plugin_dir / "__init__.py"
    if not init_path.is_file():
        errors.append(f"__init__.py missing for {name}")
        return errors

    try:
        mod = _import_plugin_module(name, plugin_dir)
    except Exception as exc:
        errors.append(f"Import failed for {name}: {exc}")
        return errors

    # 4. Verify register/handler contracts
    if expects_register:
        register_fn = getattr(mod, "register", None)
        if not callable(register_fn):
            errors.append(
                f"Plugin {name} missing callable register(ctx) in __init__.py"
            )
        else:
            _verify_register_hooks(name, register_fn, errors)
    else:
        expected_hooks_raw = plugin_cfg.get("expected_hooks", [])
        if isinstance(expected_hooks_raw, list):
            expected_hooks = [str(h) for h in expected_hooks_raw]
        else:
            expected_hooks = []
        _verify_manifest_handlers(name, mod, expected_hooks, errors)

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_plugins() -> bool:
    """Validate ALL critical plugins.  Returns ``True`` if all pass."""
    all_errors: list[str] = []

    for cfg in CRITICAL_PLUGINS:
        name_obj = cfg.get("name")
        plugin_name = str(name_obj) if isinstance(name_obj, str) else "unknown"
        errors = _validate_plugin(cfg)
        if errors:
            all_errors.append(f"--- {plugin_name} FAILED ---")
            all_errors.extend(errors)

    if all_errors:
        for err in all_errors:
            _log.error("STARTUP_GATE: %s", err)
            sys.stderr.write(f"STARTUP_GATE: {err}\n")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    """Run the startup gate.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).

    Returns:
        0 on success, 1 on validation failure.
    """
    args = argv if argv is not None else sys.argv

    if "--validate-only" in args:
        return 0 if validate_plugins() else 1

    if not validate_plugins():
        sys.stderr.write("CRITICAL: Plugin validation FAILED. Hermes will NOT start.\n")
        return 1

    sys.stderr.write("STARTUP_GATE: All critical plugins validated. Starting Hermes...\n")
    os.execvp("hermes", ["hermes", "gateway", "run", "--accept-hooks"])
    # os.execvp does not return on success.
    return 0  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
