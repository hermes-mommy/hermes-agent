"""P6 Desktop backend TDD tests — mocked pyautogui, no live external API calls.

pyautogui is NOT available on headless VPS, so all tests inject a
``FakePyautogui`` module into ``sys.modules`` before importing the
backend.  Each test then swaps individual function fakes to assert
correct call routing and argument passing.
"""
from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_fake_pyautogui():
    """Build a fresh fake pyautogui module with sensible defaults."""
    m = types.ModuleType("pyautogui")
    m.screenshot = MagicMock(return_value=MagicMock)
    m.click = MagicMock()
    m.typewrite = MagicMock()
    m.scroll = MagicMock()
    m.press = MagicMock()
    m.moveTo = MagicMock()
    m.hotkey = MagicMock()
    m.size = MagicMock(return_value=(1920, 1080))
    m.getActiveWindow = MagicMock(return_value=None)
    return m


def _get_backend(monkeypatch):
    """Import (or reimport) DesktopBackend with a fresh fake pyautogui."""
    fake = _make_fake_pyautogui()
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    # Clear cached module so reimport picks up the new fake.
    sys.modules.pop("guinevere.tools.backends.desktop", None)
    from guinevere.tools.backends.desktop import DesktopBackend
    return DesktopBackend(), fake


# ---------------------------------------------------------------------------
# Parametrised fixture: yields (backend, fake_pyautogui) per test
# ---------------------------------------------------------------------------

@pytest.fixture
def bg(monkeypatch):
    """Return (backend, fake_pyautogui) with a clean mock per test."""
    return _get_backend(monkeypatch)


# ===================================================================
# 1. is_available
# ===================================================================

class TestIsAvailable:
    def test_returns_true_when_pyautogui_present(self, bg):
        backend, _ = bg
        assert backend.is_available() is True

    def test_returns_false_when_pyautogui_missing(self, monkeypatch):
        """If pyautogui cannot be imported, is_available() is False."""
        # Remove pyautogui from sys.modules entirely.
        monkeypatch.delitem(sys.modules, "pyautogui", raising=False)
        sys.modules.pop("guinevere.tools.backends.desktop", None)
        from guinevere.tools.backends.desktop import DesktopBackend
        backend = DesktopBackend()
        assert backend.is_available() is False


# ===================================================================
# 2. Metadata
# ===================================================================

class TestMetadata:
    def test_name_is_desktop(self, bg):
        backend, _ = bg
        assert backend.name == "desktop"

    def test_actions_count(self, bg):
        backend, _ = bg
        assert len(backend.actions()) == 9

    def test_action_names(self, bg):
        backend, _ = bg
        names = {a.name for a in backend.actions()}
        expected = {"screenshot", "click", "type_text", "scroll",
                    "key_press", "move_mouse", "get_active_window",
                    "get_screen_size", "hotkey"}
        assert names == expected

    def test_action_tiers(self, bg):
        from guinevere.tools.tool_backend import ActionTier
        backend, _ = bg
        tier_map = {a.name: a.label for a in backend.actions()}
        assert tier_map["screenshot"] == ActionTier.L1_READ
        assert tier_map["get_active_window"] == ActionTier.L1_READ
        assert tier_map["get_screen_size"] == ActionTier.L1_READ
        assert tier_map["click"] == ActionTier.L2_WRITE
        assert tier_map["type_text"] == ActionTier.L2_WRITE
        assert tier_map["scroll"] == ActionTier.L2_WRITE
        assert tier_map["key_press"] == ActionTier.L2_WRITE
        assert tier_map["move_mouse"] == ActionTier.L2_WRITE
        assert tier_map["hotkey"] == ActionTier.L2_WRITE


# ===================================================================
# 3. Unknown action
# ===================================================================

class TestUnknownAction:
    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self, bg):
        backend, _ = bg
        result = await backend.dispatch("nonexistent", {})
        assert result["ok"] is False
        assert "unknown" in result["error"].lower()


# ===================================================================
# 4. screenshot
# ===================================================================

class TestScreenshot:
    @pytest.mark.asyncio
    async def test_screenshot_calls_pyautogui_screenshot(self, bg):
        backend, fake = bg
        mock_img = MagicMock()
        fake.screenshot = MagicMock(return_value=mock_img)

        result = await backend.dispatch("screenshot", {"path": "/tmp/test.png"})

        assert result["ok"] is True
        assert result["path"] == "/tmp/test.png"
        fake.screenshot.assert_called_once_with("/tmp/test.png")

    @pytest.mark.asyncio
    async def test_screenshot_without_path(self, bg):
        backend, fake = bg
        mock_img = MagicMock()
        fake.screenshot = MagicMock(return_value=mock_img)

        result = await backend.dispatch("screenshot", {})

        assert result["ok"] is True
        fake.screenshot.assert_called_once_with(None)


# ===================================================================
# 5. click
# ===================================================================

class TestClick:
    @pytest.mark.asyncio
    async def test_click_calls_pyautogui_click_with_coords(self, bg):
        backend, fake = bg

        result = await backend.dispatch("click", {"x": 100, "y": 200})

        assert result["ok"] is True
        assert result["x"] == 100
        assert result["y"] == 200
        fake.click.assert_called_once_with(100, 200, 1)

    @pytest.mark.asyncio
    async def test_click_with_custom_button_and_clicks(self, bg):
        backend, fake = bg

        result = await backend.dispatch("click", {
            "x": 50, "y": 75, "clicks": 2, "button": "right",
        })

        assert result["ok"] is True
        fake.click.assert_called_once_with(50, 75, 2, button="right")

    @pytest.mark.asyncio
    async def test_click_default_coords(self, bg):
        backend, fake = bg

        result = await backend.dispatch("click", {})

        assert result["ok"] is True
        fake.click.assert_called_once_with(None, None, 1)


# ===================================================================
# 6. type_text
# ===================================================================

class TestTypeText:
    @pytest.mark.asyncio
    async def test_type_text_calls_pyautogui_typewrite(self, bg):
        backend, fake = bg

        result = await backend.dispatch("type_text", {"text": "hello world"})

        assert result["ok"] is True
        assert result["text"] == "hello world"
        fake.typewrite.assert_called_once_with("hello world", interval=0.05)

    @pytest.mark.asyncio
    async def test_type_text_with_custom_interval(self, bg):
        backend, fake = bg

        result = await backend.dispatch("type_text", {
            "text": "fast", "interval": 0.01,
        })

        assert result["ok"] is True
        fake.typewrite.assert_called_once_with("fast", interval=0.01)

    @pytest.mark.asyncio
    async def test_type_text_requires_text(self, bg):
        backend, _ = bg

        result = await backend.dispatch("type_text", {})

        assert result["ok"] is False
        assert "text" in result["error"].lower()


# ===================================================================
# 7. scroll
# ===================================================================

class TestScroll:
    @pytest.mark.asyncio
    async def test_scroll_up(self, bg):
        backend, fake = bg

        result = await backend.dispatch("scroll", {"amount": 5})

        assert result["ok"] is True
        assert result["amount"] == 5
        fake.scroll.assert_called_once_with(5, x=None, y=None)

    @pytest.mark.asyncio
    async def test_scroll_down(self, bg):
        backend, fake = bg

        result = await backend.dispatch("scroll", {"amount": -3})

        assert result["ok"] is True
        fake.scroll.assert_called_once_with(-3, x=None, y=None)

    @pytest.mark.asyncio
    async def test_scroll_at_position(self, bg):
        backend, fake = bg

        result = await backend.dispatch("scroll", {"amount": 2, "x": 100, "y": 200})

        assert result["ok"] is True
        fake.scroll.assert_called_once_with(2, x=100, y=200)

    @pytest.mark.asyncio
    async def test_scroll_default_amount(self, bg):
        backend, fake = bg

        result = await backend.dispatch("scroll", {})

        assert result["ok"] is True
        fake.scroll.assert_called_once_with(3, x=None, y=None)


# ===================================================================
# 8. key_press
# ===================================================================

class TestKeyPress:
    @pytest.mark.asyncio
    async def test_key_press_calls_pyautogui_press(self, bg):
        backend, fake = bg

        result = await backend.dispatch("key_press", {"key": "enter"})

        assert result["ok"] is True
        assert result["key"] == "enter"
        fake.press.assert_called_once_with("enter")

    @pytest.mark.asyncio
    async def test_key_press_requires_key(self, bg):
        backend, _ = bg

        result = await backend.dispatch("key_press", {})

        assert result["ok"] is False
        assert "key" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_key_press_with_presses(self, bg):
        backend, fake = bg

        result = await backend.dispatch("key_press", {"key": "space", "presses": 3})

        assert result["ok"] is True
        assert fake.press.call_count == 3


# ===================================================================
# 9. move_mouse
# ===================================================================

class TestMoveMouse:
    @pytest.mark.asyncio
    async def test_move_mouse_calls_pyautogui_moveTo(self, bg):
        backend, fake = bg

        result = await backend.dispatch("move_mouse", {"x": 500, "y": 300})

        assert result["ok"] is True
        assert result["x"] == 500
        assert result["y"] == 300
        fake.moveTo.assert_called_once_with(500, 300, duration=0.25)

    @pytest.mark.asyncio
    async def test_move_mouse_with_duration(self, bg):
        backend, fake = bg

        result = await backend.dispatch("move_mouse", {
            "x": 100, "y": 200, "duration": 1.0,
        })

        assert result["ok"] is True
        fake.moveTo.assert_called_once_with(100, 200, duration=1.0)

    @pytest.mark.asyncio
    async def test_move_mouse_default_coords(self, bg):
        backend, fake = bg

        result = await backend.dispatch("move_mouse", {})

        assert result["ok"] is True
        fake.moveTo.assert_called_once_with(None, None, duration=0.25)


# ===================================================================
# 10. get_active_window
# ===================================================================

class TestGetActiveWindow:
    @pytest.mark.asyncio
    async def test_get_active_window_returns_title(self, bg):
        backend, fake = bg
        win = MagicMock()
        win.title = "Test Window"
        fake.getActiveWindow = MagicMock(return_value=win)

        result = await backend.dispatch("get_active_window", {})

        assert result["ok"] is True
        assert result["title"] == "Test Window"

    @pytest.mark.asyncio
    async def test_get_active_window_no_window(self, bg):
        backend, fake = bg
        fake.getActiveWindow = MagicMock(return_value=None)

        result = await backend.dispatch("get_active_window", {})

        assert result["ok"] is False
        assert "no active window" in result["error"].lower()


# ===================================================================
# 11. get_screen_size
# ===================================================================

class TestGetScreenSize:
    @pytest.mark.asyncio
    async def test_get_screen_size_returns_dimensions(self, bg):
        backend, fake = bg
        fake.size = MagicMock(return_value=(2560, 1440))

        result = await backend.dispatch("get_screen_size", {})

        assert result["ok"] is True
        assert result["width"] == 2560
        assert result["height"] == 1440

    @pytest.mark.asyncio
    async def test_get_screen_size_full_hd(self, bg):
        backend, fake = bg
        fake.size = MagicMock(return_value=(1920, 1080))

        result = await backend.dispatch("get_screen_size", {})

        assert result["ok"] is True
        assert result["width"] == 1920
        assert result["height"] == 1080


# ===================================================================
# 12. hotkey
# ===================================================================

class TestHotkey:
    @pytest.mark.asyncio
    async def test_hotkey_calls_pyautogui_hotkey(self, bg):
        backend, fake = bg

        result = await backend.dispatch("hotkey", {"keys": ["ctrl", "c"]})

        assert result["ok"] is True
        assert result["keys"] == ["ctrl", "c"]
        fake.hotkey.assert_called_once_with("ctrl", "c")

    @pytest.mark.asyncio
    async def test_hotkey_multiple_keys(self, bg):
        backend, fake = bg

        result = await backend.dispatch("hotkey", {"keys": ["ctrl", "shift", "esc"]})

        assert result["ok"] is True
        fake.hotkey.assert_called_once_with("ctrl", "shift", "esc")

    @pytest.mark.asyncio
    async def test_hotkey_requires_keys(self, bg):
        backend, _ = bg

        result = await backend.dispatch("hotkey", {})

        assert result["ok"] is False
        assert "keys" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_hotkey_requires_list(self, bg):
        backend, _ = bg

        result = await backend.dispatch("hotkey", {"keys": "not-a-list"})

        assert result["ok"] is False
        assert "list" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_hotkey_requires_at_least_two_keys(self, bg):
        backend, _ = bg

        result = await backend.dispatch("hotkey", {"keys": ["ctrl"]})

        assert result["ok"] is False
        assert "at least two" in result["error"].lower()


# ===================================================================
# 13. pyautogui not installed — dispatch graceful fallback
# ===================================================================

class TestPyautoguiNotInstalled:
    @pytest.mark.asyncio
    async def test_dispatch_returns_error_when_pyautogui_missing(self, monkeypatch):
        """dispatch() returns ok=False if pyautogui is absent."""
        monkeypatch.delitem(sys.modules, "pyautogui", raising=False)
        sys.modules.pop("guinevere.tools.backends.desktop", None)
        from guinevere.tools.backends.desktop import DesktopBackend
        backend = DesktopBackend()

        for action in ["screenshot", "click", "type_text", "scroll",
                        "key_press", "move_mouse", "get_active_window",
                        "get_screen_size", "hotkey"]:
            result = await backend.dispatch(action, {})
            assert result["ok"] is False, f"action={action} should fail"
            assert "pyautogui" in result["error"].lower(), f"action={action} missing pyautogui mention"


# ===================================================================
# 14. pyautogui exception — fail-soft
# ===================================================================

class TestFailSoft:
    @pytest.mark.asyncio
    async def test_dispatch_catches_pyautogui_exception(self, bg):
        backend, fake = bg
        fake.screenshot = MagicMock(side_effect=RuntimeError("display error"))

        result = await backend.dispatch("screenshot", {})

        assert result["ok"] is False
        assert "display error" in result["error"]

    @pytest.mark.asyncio
    async def test_click_catches_exception(self, bg):
        backend, fake = bg
        fake.click = MagicMock(side_effect=Exception("click failed"))

        result = await backend.dispatch("click", {"x": 0, "y": 0})

        assert result["ok"] is False
        assert "click failed" in result["error"]
