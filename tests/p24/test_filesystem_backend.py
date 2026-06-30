"""P6 filesystem backend TDD tests — real I/O, no mock returns.

Each action must perform REAL filesystem I/O via pathlib, not return a
canned empty dict. Tests use a tmp_path fixture for isolation.
"""
from __future__ import annotations

import asyncio
import os
import pytest

from guinvere.tools.backends.filesystem import FilesystemBackend


@pytest.fixture
def backend():
    return FilesystemBackend()


@pytest.mark.asyncio
async def test_read_returns_real_file_content(backend, tmp_path):
    """read() returns the actual file content, not empty string."""
    f = tmp_path / "hello.txt"
    f.write_text("hello world", encoding="utf-8")

    result = await backend.dispatch("read", {"path": str(f)})

    assert result["ok"] is True
    assert result["content"] == "hello world"
    assert result["path"] == str(f)


@pytest.mark.asyncio
async def test_list_returns_real_directory_entries(backend, tmp_path):
    """list() returns actual directory entries, not empty list."""
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "subdir").mkdir()

    result = await backend.dispatch("list", {"path": str(tmp_path)})

    assert result["ok"] is True
    names = result["entries"]
    assert "a.txt" in names
    assert "b.txt" in names
    assert "subdir" in names


@pytest.mark.asyncio
async def test_glob_returns_real_matches(backend, tmp_path):
    """glob() returns actual matched paths, not empty list."""
    (tmp_path / "x.py").write_text("1")
    (tmp_path / "y.py").write_text("2")
    (tmp_path / "z.txt").write_text("3")

    result = await backend.dispatch("glob", {"path": str(tmp_path), "pattern": "*.py"})

    assert result["ok"] is True
    matches = result["matches"]
    assert any(m.endswith("x.py") for m in matches)
    assert any(m.endswith("y.py") for m in matches)
    assert not any(m.endswith("z.txt") for m in matches)


@pytest.mark.asyncio
async def test_grep_returns_real_matches(backend, tmp_path):
    """grep() returns actual line matches, not empty list."""
    f = tmp_path / "code.py"
    f.write_text("def foo():\n    return 'bar'\n\ndef baz():\n    pass\n", encoding="utf-8")

    result = await backend.dispatch("grep", {"path": str(f), "query": "def"})

    assert result["ok"] is True
    matches = result["matches"]
    # Should find 2 lines with "def"
    assert len(matches) == 2


@pytest.mark.asyncio
async def test_write_creates_real_file(backend, tmp_path):
    """write() creates a real file with the content."""
    f = tmp_path / "out.txt"

    result = await backend.dispatch("write", {"path": str(f), "content": "written!"})

    assert result["ok"] is True
    assert result["bytes_written"] == len("written!")
    assert f.read_text(encoding="utf-8") == "written!"


@pytest.mark.asyncio
async def test_append_appends_to_real_file(backend, tmp_path):
    """append() appends content to an existing file."""
    f = tmp_path / "log.txt"
    f.write_text("line1\n", encoding="utf-8")

    result = await backend.dispatch("append", {"path": str(f), "content": "line2\n"})

    assert result["ok"] is True
    assert f.read_text(encoding="utf-8") == "line1\nline2\n"


@pytest.mark.asyncio
async def test_copy_copies_real_file(backend, tmp_path):
    """copy() creates a real copy."""
    src = tmp_path / "orig.txt"
    src.write_text("copy me", encoding="utf-8")
    dest = tmp_path / "copy.txt"

    result = await backend.dispatch("copy", {"path": str(src), "dest": str(dest)})

    assert result["ok"] is True
    assert dest.read_text(encoding="utf-8") == "copy me"
    assert src.read_text(encoding="utf-8") == "copy me"  # original preserved


@pytest.mark.asyncio
async def test_move_moves_real_file(backend, tmp_path):
    """move() relocates the file (original gone)."""
    src = tmp_path / "mover.txt"
    src.write_text("move me", encoding="utf-8")
    dest = tmp_path / "moved.txt"

    result = await backend.dispatch("move", {"path": str(src), "dest": str(dest)})

    assert result["ok"] is True
    assert dest.read_text(encoding="utf-8") == "move me"
    assert not src.exists()  # original gone


@pytest.mark.asyncio
async def test_delete_deletes_real_file(backend, tmp_path):
    """delete() removes the file."""
    f = tmp_path / "doomed.txt"
    f.write_text("delete me", encoding="utf-8")

    result = await backend.dispatch("delete", {"path": str(f)})

    assert result["ok"] is True
    assert result["deleted"] is True
    assert not f.exists()
