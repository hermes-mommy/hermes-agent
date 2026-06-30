from __future__ import annotations

"""P13 X Auto Poster — Autonomous X/Twitter scheduling via Hermes + Twikit."""

__version__ = "1.0.0"

# Re-export key public symbols with lazy imports to avoid circular deps
__all__ = ["XPosterSettings", "get_xposter_settings", "__version__"]


def __getattr__(name: str) -> object:
    if name == "XPosterSettings":
        from .config import XPosterSettings

        return XPosterSettings
    if name == "get_xposter_settings":
        from .config import get_xposter_settings

        return get_xposter_settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
