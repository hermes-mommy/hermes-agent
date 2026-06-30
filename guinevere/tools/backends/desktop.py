"""M8 Desktop backend -- GUI automation via pyautogui.

Ported from: P23 desktop_executor (Section 4.2).

9 actions: 3 L1 READ, 6 L2 WRITE.

pyautogui is import-guarded: on headless servers (no display) the import
succeeds but runtime calls will raise; on systems where pyautogui is not
installed at all, ``is_available()`` returns False and every dispatch
returns ``{"ok": False, "error": "pyautogui not installed"}``.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional import guard -- pyautogui absent on headless / minimal installs.
# ---------------------------------------------------------------------------
try:
    import pyautogui as _pyautogui  # type: ignore[import-untyped]
    _HAS_PYAUTOGUI = True
except ImportError:
    _pyautogui = None  # type: ignore[assignment]
    _HAS_PYAUTOGUI = False


class DesktopBackend(ToolBackend):
    """Desktop automation backend (L1/L2/L3) powered by pyautogui.

    Actions: screenshot, click, type_text, scroll, key_press,
    move_mouse, get_active_window, get_screen_size, hotkey.
    """

    @property
    def name(self) -> str:
        return "desktop"

    def actions(self) -> list[Action]:
        return [
            Action("screenshot", ActionTier.L1_READ, description="Take screenshot"),
            Action("get_active_window", ActionTier.L1_READ, description="Get active window title"),
            Action("get_screen_size", ActionTier.L1_READ, description="Get screen dimensions"),
            Action("click", ActionTier.L2_WRITE, description="Click at coordinates"),
            Action("type_text", ActionTier.L2_WRITE, description="Type text string"),
            Action("scroll", ActionTier.L2_WRITE, description="Scroll up/down"),
            Action("key_press", ActionTier.L2_WRITE, description="Press a key"),
            Action("move_mouse", ActionTier.L2_WRITE, description="Move mouse cursor"),
            Action("hotkey", ActionTier.L2_WRITE, description="Press key combination"),
        ]

    def is_available(self) -> bool:
        """Return True only if pyautogui is importable."""
        try:
            import pyautogui  # noqa: F401
            return True
        except ImportError:
            return False

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a desktop GUI action via pyautogui.

        All actions perform real I/O.  Errors are caught and returned as
        ``{"ok": False, "error": ...}`` (fail-soft -- never raise to caller).
        """
        action_lower = action.lower()

        # Guard: pyautogui must be available.
        if not _HAS_PYAUTOGUI:
            return {"ok": False, "error": "pyautogui not installed", "action": action}

        try:
            # --- L1 READ actions ---------------------------------------------------

            if action_lower == "screenshot":
                path = args.get("path")
                img = _pyautogui.screenshot(path)
                return {"ok": True, "action": action, "path": path}

            if action_lower == "get_active_window":
                win = _pyautogui.getActiveWindow()
                if win is None:
                    return {"ok": False, "action": action,
                            "error": "no active window found"}
                return {"ok": True, "action": action, "title": win.title}

            if action_lower == "get_screen_size":
                w, h = _pyautogui.size()
                return {"ok": True, "action": action, "width": w, "height": h}

            # --- L2 WRITE actions --------------------------------------------------

            if action_lower == "click":
                x = args.get("x")
                y = args.get("y")
                clicks = args.get("clicks", 1)
                button = args.get("button")
                if button is not None:
                    _pyautogui.click(x, y, clicks, button=button)
                else:
                    _pyautogui.click(x, y, clicks)
                return {"ok": True, "action": action, "x": x, "y": y}

            if action_lower == "type_text":
                text = args.get("text")
                if text is None:
                    return {"ok": False, "action": action,
                            "error": "text is required"}
                interval = args.get("interval", 0.05)
                _pyautogui.typewrite(text, interval=interval)
                return {"ok": True, "action": action, "text": text}

            if action_lower == "scroll":
                amount = args.get("amount", 3)
                x = args.get("x")
                y = args.get("y")
                _pyautogui.scroll(amount, x=x, y=y)
                return {"ok": True, "action": action, "amount": amount}

            if action_lower == "key_press":
                key = args.get("key")
                if key is None:
                    return {"ok": False, "action": action,
                            "error": "key is required"}
                presses = args.get("presses", 1)
                for _ in range(presses):
                    _pyautogui.press(key)
                return {"ok": True, "action": action, "key": key}

            if action_lower == "move_mouse":
                x = args.get("x")
                y = args.get("y")
                duration = args.get("duration", 0.25)
                _pyautogui.moveTo(x, y, duration=duration)
                return {"ok": True, "action": action, "x": x, "y": y}

            if action_lower == "hotkey":
                keys = args.get("keys")
                if keys is None:
                    return {"ok": False, "action": action,
                            "error": "keys is required (list of keys)"}
                if not isinstance(keys, list):
                    return {"ok": False, "action": action,
                            "error": "keys must be a list"}
                if len(keys) < 2:
                    return {"ok": False, "action": action,
                            "error": "hotkey requires at least two keys"}
                _pyautogui.hotkey(*keys)
                return {"ok": True, "action": action, "keys": keys}

            return {"ok": False, "error": f"unknown desktop action: {action}"}

        except Exception as e:
            return {"ok": False, "action": action, "error": str(e)}
