"""Guinevere Safety Plugin — hermes-agent plugin entry point.

This __init__.py is the hermes-agent plugin entry point. It imports the
full GuinevereSafetyPlugin from the project source tree and re-exports
the register() function for hermes-agent's plugin loader.

Directory structure:
    .hermes/plugins/guinevere-safety/
        plugin.yaml     — manifest
        __init__.py     — this file (entry point)

Project source:
    src/hermes/safety_plugin.py — full plugin implementation
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project src/ is on sys.path so `from src.hermes.safety_plugin` works.
_project_root = Path(__file__).resolve().parent.parent.parent.parent  # .hermes/plugins/guinevere-safety -> .hermes -> plugins -> project_root
_src_path = str(_project_root / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
# Also ensure the project root itself is on sys.path for `src.xxx` imports.
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

from src.hermes.safety_plugin import register  # noqa: E402, F401
