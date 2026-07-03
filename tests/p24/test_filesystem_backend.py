"""P24 filesystem backend TDD tests — 23 actions, real I/O, no mock returns.

Each action must perform REAL filesystem I/O via pathlib.  Tests use
``tmp_path`` for isolation.  All actions are async.

Actions (23):
  L1 READ (10):  read, list, glob, grep, exists, stat, read_bytes,
                 read_lines, read_json, readlink
  L2 WRITE (10): write, append, copy, move, mkdir, write_bytes,
                 write_json, archive, extract, symlink
  L3 DESTRUCTIVE (3): delete, rm_tree, chmod
"""

from __future__ import annotations

import json
import os
import platform
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from guinvere.tools.backends.filesystem import FilesystemBackend

# Import ActionTier from the SAME module the backend uses to avoid
# cross-module enum identity issues.
from guinevere.tools.tool_backend import ActionTier

_IS_WINDOWS = platform.system() == "Windows"


@pytest.fixture
def backend() -> FilesystemBackend:
    return FilesystemBackend()


# ===================================================================
# 0.  Meta / registration
# ===================================================================


def test_backend_name(backend: FilesystemBackend) -> None:
    assert backend.name == "filesystem"


def test_is_available(backend: FilesystemBackend) -> None:
    assert backend.is_available() is True


def test_actions_count_is_23(backend: FilesystemBackend) -> None:
    """The plan requires exactly 23 actions."""
    assert len(backend.actions()) == 23


def test_all_actions_are_async(backend: FilesystemBackend) -> None:
    """dispatch() is async (required by plan)."""
    import asyncio

    assert asyncio.iscoroutinefunction(backend.dispatch)


def test_action_names_unique(backend: FilesystemBackend) -> None:
    names = [a.name for a in backend.actions()]
    assert len(names) == len(set(names))


def test_action_tiers_valid(backend: FilesystemBackend) -> None:
    valid = {ActionTier.L1_READ, ActionTier.L2_WRITE, ActionTier.L3_DESTRUCTIVE}
    for a in backend.actions():
        assert a.label in valid


# ===================================================================
# 1.  read  (L1 READ)
# ===================================================================


async def test_read_returns_real_content(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "hello.txt"
    f.write_text("hello world", encoding="utf-8")

    result = await backend.dispatch("read", {"path": str(f)})

    assert result["ok"] is True
    assert result["content"] == "hello world"


async def test_read_nonexistent_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("read", {"path": str(tmp_path / "nope.txt")})

    assert result["ok"] is False
    assert "not found" in result["error"].lower() or "error" in result


async def test_read_utf8_bom(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "bom.txt"
    f.write_bytes(b"\xef\xbb\xbfhello")
    result = await backend.dispatch("read", {"path": str(f)})
    assert result["ok"] is True
    assert "hello" in result["content"]


# ===================================================================
# 2.  list  (L1 READ)
# ===================================================================


async def test_list_returns_real_entries(backend: FilesystemBackend, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "subdir").mkdir()

    result = await backend.dispatch("list", {"path": str(tmp_path)})

    assert result["ok"] is True
    names = result["entries"]
    assert "a.txt" in names
    assert "b.txt" in names
    assert "subdir" in names


async def test_list_empty_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    result = await backend.dispatch("list", {"path": str(empty)})

    assert result["ok"] is True
    assert result["entries"] == []


async def test_list_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("list", {"path": str(tmp_path / "nope")})
    assert result["ok"] is False


# ===================================================================
# 3.  glob  (L1 READ)
# ===================================================================


async def test_glob_returns_matches(backend: FilesystemBackend, tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("1")
    (tmp_path / "y.py").write_text("2")
    (tmp_path / "z.txt").write_text("3")

    result = await backend.dispatch("glob", {"path": str(tmp_path), "pattern": "*.py"})

    assert result["ok"] is True
    matches = result["matches"]
    assert any("x.py" in m for m in matches)
    assert any("y.py" in m for m in matches)
    assert not any("z.txt" in m for m in matches)


async def test_glob_recursive(backend: FilesystemBackend, tmp_path: Path) -> None:
    sub = tmp_path / "deep"
    sub.mkdir()
    (sub / "deep.py").write_text("x")

    result = await backend.dispatch("glob", {"path": str(tmp_path), "pattern": "**/*.py"})

    assert result["ok"] is True
    assert any("deep.py" in m for m in result["matches"])


async def test_glob_no_matches(backend: FilesystemBackend, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")

    result = await backend.dispatch("glob", {"path": str(tmp_path), "pattern": "*.py"})

    assert result["ok"] is True
    assert result["matches"] == []


# ===================================================================
# 4.  grep  (L1 READ)
# ===================================================================


async def test_grep_in_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "code.py"
    f.write_text("def foo():\n    return 'bar'\n\ndef baz():\n    pass\n")

    result = await backend.dispatch("grep", {"path": str(f), "query": "def"})

    assert result["ok"] is True
    assert len(result["matches"]) == 2


async def test_grep_in_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import os\nimport sys\n")
    (tmp_path / "b.py").write_text("import sys\nimport os\n")

    result = await backend.dispatch("grep", {"path": str(tmp_path), "query": "import os"})

    assert result["ok"] is True
    # 1 in a.py + 1 in b.py = 2 matches
    assert len(result["matches"]) == 2


async def test_grep_no_matches(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "empty.py"
    f.write_text("pass\n")

    result = await backend.dispatch("grep", {"path": str(f), "query": "ZZZZZ"})

    assert result["ok"] is True
    assert result["matches"] == []


# ===================================================================
# 5.  write  (L2 WRITE)
# ===================================================================


async def test_write_creates_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "out.txt"

    result = await backend.dispatch("write", {"path": str(f), "content": "written!"})

    assert result["ok"] is True
    assert f.read_text(encoding="utf-8") == "written!"


async def test_write_creates_parent_dirs(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "a" / "b" / "c.txt"

    result = await backend.dispatch("write", {"path": str(f), "content": "nested"})

    assert result["ok"] is True
    assert f.read_text(encoding="utf-8") == "nested"


async def test_write_overwrites_existing(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "overwrite.txt"
    f.write_text("old")

    result = await backend.dispatch("write", {"path": str(f), "content": "new"})

    assert result["ok"] is True
    assert f.read_text(encoding="utf-8") == "new"


# ===================================================================
# 6.  append  (L2 WRITE)
# ===================================================================


async def test_append_to_existing(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "log.txt"
    f.write_text("line1\n")

    result = await backend.dispatch("append", {"path": str(f), "content": "line2\n"})

    assert result["ok"] is True
    assert f.read_text(encoding="utf-8") == "line1\nline2\n"


async def test_append_creates_new_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "new.txt"

    result = await backend.dispatch("append", {"path": str(f), "content": "first"})

    assert result["ok"] is True
    assert f.read_text(encoding="utf-8") == "first"


# ===================================================================
# 7.  copy  (L2 WRITE)
# ===================================================================


async def test_copy_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    src = tmp_path / "orig.txt"
    src.write_text("copy me")
    dest = tmp_path / "copy.txt"

    result = await backend.dispatch("copy", {"path": str(src), "dest": str(dest)})

    assert result["ok"] is True
    assert dest.read_text(encoding="utf-8") == "copy me"
    assert src.read_text(encoding="utf-8") == "copy me"  # original preserved


async def test_copy_creates_parent_dirs(backend: FilesystemBackend, tmp_path: Path) -> None:
    src = tmp_path / "orig.txt"
    src.write_text("data")
    dest = tmp_path / "sub" / "deep" / "copy.txt"

    result = await backend.dispatch("copy", {"path": str(src), "dest": str(dest)})

    assert result["ok"] is True
    assert dest.read_text(encoding="utf-8") == "data"


async def test_copy_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch(
        "copy",
        {"path": str(tmp_path / "nope.txt"), "dest": str(tmp_path / "dest.txt")},
    )
    assert result["ok"] is False


# ===================================================================
# 8.  move  (L2 WRITE)
# ===================================================================


async def test_move_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    src = tmp_path / "mover.txt"
    src.write_text("move me")
    dest = tmp_path / "moved.txt"

    result = await backend.dispatch("move", {"path": str(src), "dest": str(dest)})

    assert result["ok"] is True
    assert dest.read_text(encoding="utf-8") == "move me"
    assert not src.exists()


async def test_move_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch(
        "move",
        {"path": str(tmp_path / "nope.txt"), "dest": str(tmp_path / "dest.txt")},
    )
    assert result["ok"] is False


# ===================================================================
# 9.  delete  (L3 DESTRUCTIVE)
# ===================================================================


async def test_delete_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "doomed.txt"
    f.write_text("bye")

    result = await backend.dispatch("delete", {"path": str(f)})

    assert result["ok"] is True
    assert result["deleted"] is True
    assert not f.exists()


async def test_delete_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "doomed_dir"
    d.mkdir()
    (d / "file.txt").write_text("inside")

    result = await backend.dispatch("delete", {"path": str(d)})

    assert result["ok"] is True
    assert not d.exists()


async def test_delete_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("delete", {"path": str(tmp_path / "ghost")})
    assert result["ok"] is False


# ===================================================================
# 10.  mkdir  (L2 WRITE)
# ===================================================================


async def test_mkdir_creates_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "newdir"

    result = await backend.dispatch("mkdir", {"path": str(d)})

    assert result["ok"] is True
    assert d.is_dir()


async def test_mkdir_nested(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "a" / "b" / "c"

    result = await backend.dispatch("mkdir", {"path": str(d)})

    assert result["ok"] is True
    assert d.is_dir()


async def test_mkdir_existing_is_ok(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "existing"
    d.mkdir()

    result = await backend.dispatch("mkdir", {"path": str(d)})

    assert result["ok"] is True


# ===================================================================
# 11.  exists  (L1 READ)
# ===================================================================


async def test_exists_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "real.txt"
    f.write_text("here")

    result = await backend.dispatch("exists", {"path": str(f)})

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["type"] == "file"


async def test_exists_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "real_dir"
    d.mkdir()

    result = await backend.dispatch("exists", {"path": str(d)})

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["type"] == "directory"


async def test_exists_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("exists", {"path": str(tmp_path / "ghost")})

    assert result["ok"] is True
    assert result["exists"] is False
    assert result["type"] == "none"


# ===================================================================
# 12.  stat  (L1 READ)
# ===================================================================


async def test_stat_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "statme.txt"
    f.write_text("hello world")

    result = await backend.dispatch("stat", {"path": str(f)})

    assert result["ok"] is True
    assert result["size"] == 11
    assert result["is_file"] is True
    assert result["is_dir"] is False
    assert "mtime" in result


async def test_stat_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "dir"
    d.mkdir()

    result = await backend.dispatch("stat", {"path": str(d)})

    assert result["ok"] is True
    assert result["is_dir"] is True
    assert result["is_file"] is False


async def test_stat_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("stat", {"path": str(tmp_path / "nope")})
    assert result["ok"] is False


# ===================================================================
# 13.  read_bytes  (L1 READ)
# ===================================================================


async def test_read_bytes_returns_binary(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "binary.dat"
    data = bytes(range(256))
    f.write_bytes(data)

    result = await backend.dispatch("read_bytes", {"path": str(f)})

    assert result["ok"] is True
    assert result["content"] == data.hex()
    assert result["size"] == 256


async def test_read_bytes_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("read_bytes", {"path": str(tmp_path / "nope.bin")})
    assert result["ok"] is False


async def test_read_bytes_empty_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")

    result = await backend.dispatch("read_bytes", {"path": str(f)})

    assert result["ok"] is True
    assert result["content"] == ""
    assert result["size"] == 0


# ===================================================================
# 14.  write_bytes  (L2 WRITE)
# ===================================================================


async def test_write_bytes_creates_binary(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "out.bin"
    data = bytes(range(10))

    result = await backend.dispatch("write_bytes", {"path": str(f), "content": data.hex()})

    assert result["ok"] is True
    assert f.read_bytes() == data


async def test_write_bytes_creates_parent_dirs(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "sub" / "deep" / "out.bin"

    result = await backend.dispatch("write_bytes", {"path": str(f), "content": "abcd"})

    assert result["ok"] is True
    assert f.exists()


# ===================================================================
# 15.  read_lines  (L1 READ)
# ===================================================================


async def test_read_lines_range(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "lines.txt"
    f.write_text("line1\nline2\nline3\nline4\nline5\n")

    result = await backend.dispatch("read_lines", {"path": str(f), "start": 2, "end": 4})

    assert result["ok"] is True
    assert len(result["lines"]) == 3  # lines 2, 3, 4
    assert result["lines"][0]["line"] == 2
    assert result["lines"][0]["text"] == "line2"


async def test_read_lines_entire_file(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "full.txt"
    f.write_text("a\nb\nc\n")

    result = await backend.dispatch("read_lines", {"path": str(f)})

    assert result["ok"] is True
    assert len(result["lines"]) == 3


async def test_read_lines_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("read_lines", {"path": str(tmp_path / "nope.txt")})
    assert result["ok"] is False


# ===================================================================
# 16.  read_json  (L1 READ)
# ===================================================================


async def test_read_json_parses(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text('{"name": "guinevere", "version": 42}')

    result = await backend.dispatch("read_json", {"path": str(f)})

    assert result["ok"] is True
    assert result["data"]["name"] == "guinevere"
    assert result["data"]["version"] == 42


async def test_read_json_array(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "arr.json"
    f.write_text("[1, 2, 3]")

    result = await backend.dispatch("read_json", {"path": str(f)})

    assert result["ok"] is True
    assert result["data"] == [1, 2, 3]


async def test_read_json_invalid(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "bad.json"
    f.write_text("not json {{{")

    result = await backend.dispatch("read_json", {"path": str(f)})

    assert result["ok"] is False
    assert "error" in result


async def test_read_json_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("read_json", {"path": str(tmp_path / "nope.json")})
    assert result["ok"] is False


# ===================================================================
# 17.  write_json  (L2 WRITE)
# ===================================================================


async def test_write_json_creates_formatted(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "out.json"

    result = await backend.dispatch(
        "write_json", {"path": str(f), "data": {"key": "value", "num": 7}}
    )

    assert result["ok"] is True
    loaded = json.loads(f.read_text(encoding="utf-8"))
    assert loaded["key"] == "value"
    assert loaded["num"] == 7


async def test_write_json_with_indent(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "pretty.json"

    result = await backend.dispatch("write_json", {"path": str(f), "data": {"a": 1}, "indent": 4})

    assert result["ok"] is True
    text = f.read_text(encoding="utf-8")
    assert "    " in text  # 4-space indent


async def test_write_json_creates_parent_dirs(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "sub" / "data.json"

    result = await backend.dispatch("write_json", {"path": str(f), "data": [1, 2]})

    assert result["ok"] is True
    assert json.loads(f.read_text(encoding="utf-8")) == [1, 2]


# ===================================================================
# 18.  rm_tree  (L3 DESTRUCTIVE)
# ===================================================================


async def test_rm_tree_removes_recursively(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "tree"
    d.mkdir()
    (d / "a.txt").write_text("a")
    sub = d / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("b")

    result = await backend.dispatch("rm_tree", {"path": str(d)})

    assert result["ok"] is True
    assert not d.exists()


async def test_rm_tree_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("rm_tree", {"path": str(tmp_path / "ghost")})
    assert result["ok"] is False


async def test_rm_tree_empty_dir(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "empty_tree"
    d.mkdir()

    result = await backend.dispatch("rm_tree", {"path": str(d)})

    assert result["ok"] is True
    assert not d.exists()


# ===================================================================
# 19.  archive  (L2 WRITE)
# ===================================================================


async def test_archive_creates_tar_gz(backend: FilesystemBackend, tmp_path: Path) -> None:
    src = tmp_path / "project"
    src.mkdir()
    (src / "file1.txt").write_text("content1")
    (src / "file2.txt").write_text("content2")
    dest = tmp_path / "project.tar.gz"

    result = await backend.dispatch(
        "archive", {"path": str(src), "dest": str(dest), "format": "tar.gz"}
    )

    assert result["ok"] is True
    assert dest.exists()
    assert result["files_count"] == 2

    # Verify the archive is valid
    with tarfile.open(dest, "r:gz") as tf:
        names = tf.getnames()
        assert any("file1.txt" in n for n in names)
        assert any("file2.txt" in n for n in names)


async def test_archive_creates_zip(backend: FilesystemBackend, tmp_path: Path) -> None:
    src = tmp_path / "zipsrc"
    src.mkdir()
    (src / "a.py").write_text("print('hi')")
    dest = tmp_path / "out.zip"

    result = await backend.dispatch(
        "archive", {"path": str(src), "dest": str(dest), "format": "zip"}
    )

    assert result["ok"] is True
    assert dest.exists()

    with zipfile.ZipFile(dest, "r") as zf:
        names = zf.namelist()
        assert any("a.py" in n for n in names)


async def test_archive_nonexistent_source(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch(
        "archive",
        {
            "path": str(tmp_path / "nope"),
            "dest": str(tmp_path / "out.tar.gz"),
            "format": "tar.gz",
        },
    )
    assert result["ok"] is False


# ===================================================================
# 20.  extract  (L2 WRITE)
# ===================================================================


async def test_extract_tar_gz(backend: FilesystemBackend, tmp_path: Path) -> None:
    # Create a tar.gz
    src = tmp_path / "to_archive"
    src.mkdir()
    (src / "data.txt").write_text("extracted!")
    archive_path = tmp_path / "test.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tf:
        tf.add(str(src), arcname="to_archive")

    dest = tmp_path / "extracted"
    dest.mkdir()

    result = await backend.dispatch("extract", {"path": str(archive_path), "dest": str(dest)})

    assert result["ok"] is True
    assert result["files_count"] >= 1


async def test_extract_zip(backend: FilesystemBackend, tmp_path: Path) -> None:
    # Create a zip
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("hello.txt", "world")

    dest = tmp_path / "unzipped"
    dest.mkdir()

    result = await backend.dispatch("extract", {"path": str(zip_path), "dest": str(dest)})

    assert result["ok"] is True
    assert (dest / "hello.txt").read_text() == "world"


async def test_extract_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch(
        "extract",
        {"path": str(tmp_path / "nope.tar.gz"), "dest": str(tmp_path / "out")},
    )
    assert result["ok"] is False


# ===================================================================
# 21.  chmod  (L3 DESTRUCTIVE)
# ===================================================================


@pytest.mark.skipif(_IS_WINDOWS, reason="chmod mode bits not fully supported on Windows")
async def test_chmod_sets_permissions(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "perms.txt"
    f.write_text("secure")

    result = await backend.dispatch("chmod", {"path": str(f), "mode": "0o600"})

    assert result["ok"] is True
    actual_mode = stat.S_IMODE(os.stat(str(f)).st_mode)
    assert actual_mode == 0o600


async def test_chmod_sets_readonly_on_windows(backend: FilesystemBackend, tmp_path: Path) -> None:
    """On Windows, chmod can toggle read-only. Verify the action succeeds."""
    f = tmp_path / "readonly.txt"
    f.write_text("locked")

    # On Windows, setting 0o444 makes read-only (no write permission bit)
    result = await backend.dispatch("chmod", {"path": str(f), "mode": "0o444"})

    assert result["ok"] is True

    # Restore write permission for cleanup
    await backend.dispatch("chmod", {"path": str(f), "mode": "0o644"})


async def test_chmod_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "dir_perms"
    d.mkdir()

    result = await backend.dispatch("chmod", {"path": str(d), "mode": "0o755"})

    assert result["ok"] is True


async def test_chmod_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("chmod", {"path": str(tmp_path / "nope"), "mode": "0o644"})
    assert result["ok"] is False


# ===================================================================
# 22.  symlink  (L2 WRITE)
# ===================================================================

# On Windows, creating symlinks requires either Developer Mode or
# elevated privileges.  We skip symlink tests when we lack the privilege.


def _can_symlink() -> bool:
    """Return True if the current process can create symlinks."""
    if not _IS_WINDOWS:
        return True
    # Try to create a test symlink; if it fails, we lack privileges.
    import tempfile

    try:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.write_text("x")
            link = Path(td) / "link"
            link.symlink_to(target)
            link.unlink()
            return True
    except OSError:
        return False


@pytest.mark.skipif(
    _IS_WINDOWS and not _can_symlink(),
    reason="Symlinks require elevated privileges or Developer Mode on Windows",
)
async def test_symlink_creates_link(backend: FilesystemBackend, tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("original")
    link = tmp_path / "link.txt"

    result = await backend.dispatch("symlink", {"path": str(link), "target": str(target)})

    assert result["ok"] is True
    assert link.is_symlink()
    assert link.resolve() == target.resolve()


@pytest.mark.skipif(
    _IS_WINDOWS and not _can_symlink(),
    reason="Symlinks require elevated privileges or Developer Mode on Windows",
)
async def test_symlink_nonexistent_target(backend: FilesystemBackend, tmp_path: Path) -> None:
    """Symlink to non-existent target should still succeed (dangling symlinks are valid)."""
    link = tmp_path / "dangle"

    result = await backend.dispatch(
        "symlink", {"path": str(link), "target": str(tmp_path / "ghost")}
    )

    assert result["ok"] is True
    assert link.is_symlink()


@pytest.mark.skipif(
    _IS_WINDOWS and not _can_symlink(),
    reason="Symlinks require elevated privileges or Developer Mode on Windows",
)
async def test_symlink_to_directory(backend: FilesystemBackend, tmp_path: Path) -> None:
    d = tmp_path / "real_dir"
    d.mkdir()
    link = tmp_path / "link_dir"

    result = await backend.dispatch("symlink", {"path": str(link), "target": str(d)})

    assert result["ok"] is True
    assert link.is_symlink()


# ===================================================================
# 23.  readlink  (L1 READ)
# ===================================================================


@pytest.mark.skipif(
    _IS_WINDOWS and not _can_symlink(),
    reason="Symlinks require elevated privileges or Developer Mode on Windows",
)
async def test_readlink_resolves(backend: FilesystemBackend, tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("data")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    result = await backend.dispatch("readlink", {"path": str(link)})

    assert result["ok"] is True
    assert result["target"] == str(target)


async def test_readlink_not_a_symlink(backend: FilesystemBackend, tmp_path: Path) -> None:
    f = tmp_path / "regular.txt"
    f.write_text("not a link")

    result = await backend.dispatch("readlink", {"path": str(f)})

    assert result["ok"] is False
    assert "not a symlink" in result["error"].lower() or "error" in result


async def test_readlink_nonexistent(backend: FilesystemBackend, tmp_path: Path) -> None:
    result = await backend.dispatch("readlink", {"path": str(tmp_path / "ghost")})
    assert result["ok"] is False


# ===================================================================
# 24.  Error handling: unknown action
# ===================================================================


async def test_unknown_action_returns_error(backend: FilesystemBackend) -> None:
    result = await backend.dispatch("nonexistent_action_xyz", {"path": "/tmp"})
    assert result["ok"] is False
    assert "unknown" in result["error"].lower()
