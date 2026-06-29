"""YAML-backed config loader for Guinevere instances.

Loads the instance YAML with PyYAML, then feeds the resulting dict into
the ``GuinevereConfig`` constructor so that pydantic validates and applies
defaults.  Missing files are non-fatal (D2 — local defaults).
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from guinevere.config.models import GuinevereConfig

_logger = logging.getLogger(__name__)


def load_settings(yaml_path: str) -> GuinevereConfig:
    """Load a Guinevere instance config from *yaml_path*.

    Priority:
        constructor init (YAML data)  >  env vars  >  .env  >  defaults

    If *yaml_path* does not exist the loader falls back to built-in
    defaults so that the system boots without real secrets.
    """
    resolved = Path(yaml_path)
    if not resolved.is_file():
        _logger.warning(
            "YAML config %s not found — using built-in defaults", yaml_path,
        )
        return GuinevereConfig()

    with resolved.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # pydantic-settings: env vars still override constructor values when
    # the corresponding env vars are set.  Extra keys are silently ignored.
    return GuinevereConfig(**data)
