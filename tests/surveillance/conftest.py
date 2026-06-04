"""Pytest configuration for surveillance test modules that import from src.discord.

Ensures the real ``discord`` library (not the project-local ``src/discord/``
package) is cached before any test is collected. Without this, ``importlib.import_module("discord")``
inside ``cmd_surveillance_status.py`` resolves to the project ``src/discord/``
package instead of the actual ``py-cord`` installation.
"""

from __future__ import annotations

import os
import sys


def _cache_real_discord() -> None:
    """Pre-import the real ``discord`` module before ``src/`` shadows it."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(root, "src")

    normalised_src = os.path.normcase(os.path.normpath(src_path))

    to_remove: list[int] = []
    for idx, p in enumerate(sys.path):
        try:
            if os.path.normcase(os.path.normpath(p)) == normalised_src:
                to_remove.append(idx)
        except (ValueError, OSError):
            pass

    removed_paths: list[str] = []
    for idx in sorted(to_remove, reverse=True):
        removed_paths.append(sys.path.pop(idx))

    try:
        import discord  # noqa: F401  # cached for test isolation
    except ModuleNotFoundError:
        return
    finally:
        for p in reversed(removed_paths):
            sys.path.insert(0, p)


_cache_real_discord()