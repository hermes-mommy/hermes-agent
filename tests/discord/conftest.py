"""Pytest configuration for discord test modules.

Ensures the real ``discord`` library (not the project-local
``src/discord/`` package) is cached before any test is collected.

The project's ``pyproject.toml`` sets ``pythonpath = ['src']``, which
inserts ``src/`` at the front of ``sys.path`` and shadows the real
``discord`` library with the project's own ``src/discord/`` package.
This conftest temporarily removes the ``src/`` path, imports and caches
the real ``discord.ext.commands``, and restores the original path order.
"""

from __future__ import annotations

import os
import sys


def _cache_real_discord() -> None:
    """Pre-import the real ``discord.ext.commands`` before ``src/`` shadows it.

    Once imported, the real modules are cached in ``sys.modules`` and
    subsequent imports (even with ``src/`` in the path) resolve to them.
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(root, "src")

    # Normalise paths for comparison (pytest may use absolute or relative)
    normalised_src = os.path.normcase(os.path.normpath(src_path))

    # Collect paths to remove (all variants of src_path)
    to_remove: list[int] = []
    for idx, p in enumerate(sys.path):
        try:
            if os.path.normcase(os.path.normpath(p)) == normalised_src:
                to_remove.append(idx)
        except (ValueError, OSError):
            pass

    # Remove in reverse order to preserve indices
    removed_paths: list[str] = []
    for idx in sorted(to_remove, reverse=True):
        removed_paths.append(sys.path.pop(idx))

    try:
        # Now import the real discord — src/ is not in the path to shadow it
        import discord.ext.commands  # noqa: F401
    except ModuleNotFoundError:
        # Local test environments may not have discord.py installed.
        # The tests in this step use lightweight stubs and can proceed.
        return
    finally:
        # Restore the original path order (prepend, reversed to maintain order)
        for p in reversed(removed_paths):
            sys.path.insert(0, p)


_cache_real_discord()