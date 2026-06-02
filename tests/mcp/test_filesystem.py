"""Tests for MCP filesystem tool — path whitelist, symlink escape, null bytes."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.tools.filesystem import (  # noqa: E402
    FilesystemConfig,
    PathForbiddenError,
    fs_delete,
    fs_list,
    fs_read,
    fs_write,
    register_tools,
    validate_path,
)


# ============================================================================
# Helpers
# ============================================================================


def _config_for(path: Path) -> FilesystemConfig:
    """Build a ``FilesystemConfig`` that allows *path* only."""
    return FilesystemConfig(allowed_paths=frozenset([str(path)]))


# ============================================================================
# TestFilesystemConfig
# ============================================================================


class TestFilesystemConfig:
    """Tests for ``FilesystemConfig`` dataclass."""

    def test_default_allowed_paths(self) -> None:
        """Default config includes all four built-in paths."""
        expected = frozenset({
            "/home/guinevere/code",
            "/home/guinevere/data",
            "/home/guinevere/evidence",
            "/home/guinevere/logs",
        })
        # Patch env to ensure no override.
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("FILESYSTEM_ALLOWED_PATHS", raising=False)
            cfg = FilesystemConfig.from_env()
        assert cfg.allowed_paths == expected

    def test_env_override(self) -> None:
        """``FILESYSTEM_ALLOWED_PATHS`` env var overrides defaults."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("FILESYSTEM_ALLOWED_PATHS", "/a,/b,/c")
            cfg = FilesystemConfig.from_env()
        assert cfg.allowed_paths == frozenset({"/a", "/b", "/c"})

    def test_env_override_strips_spaces(self) -> None:
        """Trailing/leading spaces in env values are stripped."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("FILESYSTEM_ALLOWED_PATHS", "  /x , /y , /z  ")
            cfg = FilesystemConfig.from_env()
        assert cfg.allowed_paths == frozenset({"/x", "/y", "/z"})

    def test_frozen(self) -> None:
        """``FilesystemConfig`` is immutable (frozen)."""
        cfg = _config_for(Path("/tmp"))
        with pytest.raises(Exception):
            cfg.allowed_paths = frozenset()  # type: ignore[misc]


# ============================================================================
# TestNullByteRejection
# ============================================================================


class TestNullByteRejection:
    """Null-byte paths must be rejected before any filesystem operation."""

    def test_null_byte_in_validate_path(self, tmp_path: Path) -> None:
        """``validate_path`` raises ``ValueError`` for null-byte paths."""
        cfg = _config_for(tmp_path)
        with pytest.raises(ValueError, match="null byte"):
            validate_path(str(tmp_path) + "\x00extra", cfg.allowed_paths)

    def test_null_byte_in_fs_read(self, tmp_path: Path) -> None:
        """``fs_read`` rejects null-byte paths."""
        cfg = _config_for(tmp_path)
        with pytest.raises(ValueError, match="null byte"):
            import asyncio
            asyncio.run(fs_read(str(tmp_path) + "\x00", cfg))

    def test_null_byte_in_fs_write(self, tmp_path: Path) -> None:
        """``fs_write`` rejects null-byte paths."""
        cfg = _config_for(tmp_path)
        with pytest.raises(ValueError, match="null byte"):
            import asyncio
            asyncio.run(fs_write(str(tmp_path) + "\x00", "data", cfg))

    def test_null_byte_in_fs_delete(self, tmp_path: Path) -> None:
        """``fs_delete`` rejects null-byte paths."""
        cfg = _config_for(tmp_path)
        with pytest.raises(ValueError, match="null byte"):
            import asyncio
            asyncio.run(fs_delete(str(tmp_path) + "\x00", cfg))


# ============================================================================
# TestValidatePath — allowed paths
# ============================================================================


class TestValidatePathAllowed:
    """``validate_path`` returns resolved ``Path`` for whitelisted paths."""

    def test_exact_match(self, tmp_path: Path) -> None:
        """Exact match of an allowed base path passes."""
        cfg = _config_for(tmp_path)
        result = validate_path(str(tmp_path), cfg.allowed_paths)
        assert result == tmp_path.resolve()

    def test_file_inside_allowed_dir(self, tmp_path: Path) -> None:
        """A file inside an allowed directory passes."""
        cfg = _config_for(tmp_path)
        file_path = tmp_path / "subdir" / "file.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("hello", encoding="utf-8")
        result = validate_path(str(file_path), cfg.allowed_paths)
        assert result == file_path.resolve()

    def test_deeply_nested_path(self, tmp_path: Path) -> None:
        """Deeply nested path inside allowed directory passes."""
        cfg = _config_for(tmp_path)
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True, exist_ok=True)
        result = validate_path(str(deep), cfg.allowed_paths)
        assert result == deep.resolve()

    def test_multiple_allowed_paths(self, tmp_path: Path) -> None:
        """A path in any allowed base passes."""
        other = tmp_path / "other"
        other.mkdir(exist_ok=True)
        cfg = FilesystemConfig(
            allowed_paths=frozenset([str(tmp_path), str(other)])
        )
        result = validate_path(str(other / "x.txt"), cfg.allowed_paths)
        assert result == (other / "x.txt").resolve()


# ============================================================================
# TestValidatePath — forbidden
# ============================================================================


class TestValidatePathForbidden:
    """``validate_path`` raises ``PathForbiddenError`` for non-whitelisted paths."""

    def test_path_outside_whitelist(self, tmp_path: Path) -> None:
        """A path completely outside allowed dirs is rejected."""
        cfg = _config_for(tmp_path)
        with pytest.raises(PathForbiddenError):
            validate_path("/etc/passwd", cfg.allowed_paths)

    def test_etc_write_blocked(self, tmp_path: Path) -> None:
        """``/etc/`` paths are blocked (explicit scaffold requirement)."""
        cfg = _config_for(tmp_path)
        with pytest.raises(PathForbiddenError):
            validate_path("/etc/shadow", cfg.allowed_paths)

    def test_relative_dotdot_escape(self, tmp_path: Path) -> None:
        """``..`` traversal is blocked via resolve()."""
        cfg = _config_for(tmp_path)
        inside = tmp_path / "sub"
        inside.mkdir(exist_ok=True)
        with pytest.raises(PathForbiddenError):
            validate_path(str(inside / ".." / ".." / "etc" / "passwd"), cfg.allowed_paths)


# ============================================================================
# TestSeparatorPrefixMatching
# ============================================================================


class TestSeparatorPrefixMatching:
    """Prefix matching must use separator enforcement to avoid false matches."""

    def test_code_evil_does_not_match_code(self, tmp_path: Path) -> None:
        """``/base/code_evil`` must NOT match the whitelist entry ``/base/code``."""
        base = tmp_path / "code"
        base.mkdir(exist_ok=True)
        evil = tmp_path / "code_evil"
        evil.mkdir(exist_ok=True)

        # Only /base/code is allowed
        cfg = FilesystemConfig(allowed_paths=frozenset([str(base)]))

        # Path inside allowed dir passes
        (base / "legit.txt").write_text("ok", encoding="utf-8")
        validate_path(str(base / "legit.txt"), cfg.allowed_paths)

        # Path inside code_evil must fail
        (evil / "bad.txt").write_text("evil", encoding="utf-8")
        with pytest.raises(PathForbiddenError):
            validate_path(str(evil / "bad.txt"), cfg.allowed_paths)


# ============================================================================
# TestSymlinkEscape
# ============================================================================


class TestSymlinkEscape:
    """Symlinks targeting outside the whitelist must be blocked."""

    @pytest.mark.skipif(
        sys.platform == "win32" and not os.environ.get("CI"),
        reason="Symlink creation requires admin/developer-mode on Windows",
    )
    def test_symlink_outside_whitelist(self, tmp_path: Path) -> None:
        """A symlink inside allowed dir pointing outside is rejected."""
        cfg = _config_for(tmp_path)
        outside = tmp_path / "outside_target"
        outside.write_text("secret", encoding="utf-8")

        symlink = tmp_path / "link_to_outside"
        symlink.symlink_to(outside)

        with pytest.raises(PathForbiddenError):
            validate_path(str(symlink), cfg.allowed_paths)

    @pytest.mark.skipif(
        sys.platform == "win32" and not os.environ.get("CI"),
        reason="Symlink creation requires admin/developer-mode on Windows",
    )
    def test_symlink_inside_whitelist_passes(self, tmp_path: Path) -> None:
        """A symlink inside allowed dir pointing to another allowed path passes."""
        sub_a = tmp_path / "sub_a"
        sub_a.mkdir(exist_ok=True)
        sub_b = tmp_path / "sub_b"
        sub_b.mkdir(exist_ok=True)

        target = sub_a / "target.txt"
        target.write_text("data", encoding="utf-8")

        symlink = sub_b / "link.txt"
        symlink.symlink_to(target)

        cfg = FilesystemConfig(
            allowed_paths=frozenset([str(sub_a), str(sub_b)])
        )
        result = validate_path(str(symlink), cfg.allowed_paths)
        assert result == target.resolve()

    @pytest.mark.skipif(
        sys.platform == "win32" and not os.environ.get("CI"),
        reason="Symlink creation requires admin/developer-mode on Windows",
    )
    def test_symlink_chain_outside_blocked(self, tmp_path: Path) -> None:
        """A symlink → symlink → outside must be blocked."""
        cfg = _config_for(tmp_path)

        outside = tmp_path / "real_outside"
        outside.write_text("secret", encoding="utf-8")

        # Symlink chain: link2 → link1 → outside
        link1 = tmp_path / "jump1"
        link1.symlink_to(outside)
        link2 = tmp_path / "jump2"
        link2.symlink_to(link1)

        with pytest.raises(PathForbiddenError):
            validate_path(str(link2), cfg.allowed_paths)


# ============================================================================
# TestFsRead
# ============================================================================


class TestFsRead:
    """Tests for ``fs_read`` — read operations."""

    def test_read_allowed_file(self, tmp_path: Path) -> None:
        """Reading a file inside allowed path returns its content."""
        import asyncio

        cfg = _config_for(tmp_path)
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")

        result = asyncio.run(fs_read(str(f), cfg))
        assert result == "hello world"

    def test_read_forbidden_path(self, tmp_path: Path) -> None:
        """Reading outside whitelist raises ``PathForbiddenError``."""
        import asyncio

        cfg = _config_for(tmp_path)
        with pytest.raises(PathForbiddenError):
            asyncio.run(fs_read("/etc/hostname", cfg))

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        """Reading a non-existent file raises ``FileNotFoundError``."""
        import asyncio

        cfg = _config_for(tmp_path)
        with pytest.raises(FileNotFoundError):
            asyncio.run(fs_read(str(tmp_path / "nonexistent.txt"), cfg))


# ============================================================================
# TestFsWrite
# ============================================================================


class TestFsWrite:
    """Tests for ``fs_write`` — write operations."""

    def test_write_allowed_file(self, tmp_path: Path) -> None:
        """Writing to a file inside allowed path succeeds."""
        import asyncio

        cfg = _config_for(tmp_path)
        f = tmp_path / "output.txt"

        result = asyncio.run(fs_write(str(f), "new content", cfg))
        assert result == {"status": "ok", "path": str(f.resolve())}
        assert f.read_text(encoding="utf-8") == "new content"

    def test_write_overwrite_existing(self, tmp_path: Path) -> None:
        """Writing overwrites an existing file in allowed path."""
        import asyncio

        cfg = _config_for(tmp_path)
        f = tmp_path / "existing.txt"
        f.write_text("old", encoding="utf-8")

        asyncio.run(fs_write(str(f), "overwritten", cfg))
        assert f.read_text(encoding="utf-8") == "overwritten"

    def test_write_forbidden_path(self, tmp_path: Path) -> None:
        """Writing outside whitelist raises ``PathForbiddenError``."""
        import asyncio

        cfg = _config_for(tmp_path)
        with pytest.raises(PathForbiddenError):
            asyncio.run(fs_write("/etc/nope.txt", "bad", cfg))

    def test_write_to_subdir(self, tmp_path: Path) -> None:
        """Writing to a subdirectory inside allowed path succeeds."""
        import asyncio

        cfg = _config_for(tmp_path)
        sub = tmp_path / "nested" / "dir"
        sub.mkdir(parents=True, exist_ok=True)
        f = sub / "deep.txt"

        result = asyncio.run(fs_write(str(f), "deep data", cfg))
        assert result["status"] == "ok"
        assert f.read_text(encoding="utf-8") == "deep data"


# ============================================================================
# TestFsDelete
# ============================================================================


class TestFsDelete:
    """Tests for ``fs_delete`` — delete operations."""

    def test_delete_allowed_file(self, tmp_path: Path) -> None:
        """Deleting a file inside allowed path succeeds."""
        import asyncio

        cfg = _config_for(tmp_path)
        f = tmp_path / "to_delete.txt"
        f.write_text("temp", encoding="utf-8")

        result = asyncio.run(fs_delete(str(f), cfg))
        assert result == {"status": "deleted", "path": str(f.resolve())}
        assert not f.exists()

    def test_delete_nonexistent_file(self, tmp_path: Path) -> None:
        """Deleting a non-existent file raises ``FileNotFoundError``."""
        import asyncio

        cfg = _config_for(tmp_path)
        with pytest.raises(FileNotFoundError):
            asyncio.run(fs_delete(str(tmp_path / "ghost.txt"), cfg))

    def test_delete_forbidden_path(self, tmp_path: Path) -> None:
        """Deleting outside whitelist raises ``PathForbiddenError``."""
        import asyncio

        cfg = _config_for(tmp_path)
        with pytest.raises(PathForbiddenError):
            asyncio.run(fs_delete("/etc/critical.conf", cfg))


# ============================================================================
# TestFsList
# ============================================================================


class TestFsList:
    """Tests for ``fs_list`` — directory listing."""

    def test_list_allowed_dir(self, tmp_path: Path) -> None:
        """Listing an allowed directory returns sorted entry names."""
        import asyncio

        cfg = _config_for(tmp_path)
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")
        (tmp_path / "b.txt").write_text("b", encoding="utf-8")
        (tmp_path / "subdir").mkdir(exist_ok=True)

        result = asyncio.run(fs_list(str(tmp_path), cfg))
        assert result == ["a.txt", "b.txt", "subdir"]

    def test_list_empty_dir(self, tmp_path: Path) -> None:
        """Listing an empty directory returns empty list."""
        import asyncio

        sub = tmp_path / "empty"
        sub.mkdir(exist_ok=True)
        cfg = _config_for(sub)

        result = asyncio.run(fs_list(str(sub), cfg))
        assert result == []

    def test_list_forbidden_path(self, tmp_path: Path) -> None:
        """Listing outside whitelist raises ``PathForbiddenError``."""
        import asyncio

        cfg = _config_for(tmp_path)
        with pytest.raises(PathForbiddenError):
            asyncio.run(fs_list("/root", cfg))


# ============================================================================
# TestPathForbiddenError
# ============================================================================


class TestPathForbiddenError:
    """Tests for the ``PathForbiddenError`` exception."""

    def test_is_exception_subclass(self) -> None:
        """``PathForbiddenError`` is a subclass of ``Exception``."""
        assert issubclass(PathForbiddenError, Exception)

    def test_message_preserved(self) -> None:
        """Exception message is preserved."""
        msg = "Path not in whitelist: /etc/shadow"
        exc = PathForbiddenError(msg)
        assert str(exc) == msg


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Smoke test for ``register_tools`` entry-point."""

    def test_registers_four_tools(self) -> None:
        """``register_tools`` calls ``mcp.tool()`` exactly four times."""
        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count == 4

    def test_register_tools_returns_none(self) -> None:
        """``register_tools`` returns ``None``."""
        mock_mcp = MagicMock()
        result = register_tools(mock_mcp)
        assert result is None