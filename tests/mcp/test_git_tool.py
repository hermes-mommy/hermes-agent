"""Tests for MCP git tool — subprocess, auth levels, forbidden ops."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.auth import AuthLevel, ForbiddenOperationError  # noqa: E402
from src.mcp.tools.git_tool import (  # noqa: E402
    ConfigurationError,
    GitCommandError,
    GitToolError,
    _is_forbidden,
    _run_git,
    git_commit,
    git_diff,
    git_log,
    git_push,
    git_push_force,
    git_status,
    register_tools,
)

# ============================================================================
# Fixtures
# ============================================================================


def _make_mock_process(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> MagicMock:
    """Build a mock asyncio subprocess process with given outputs."""
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(
        return_value=(stdout.encode(), stderr.encode()),
    )
    return process


# ============================================================================
# TestGitToolError / ConfigurationError / GitCommandError
# ============================================================================


class TestGitToolErrors:
    """Exception hierarchy tests."""

    def test_git_tool_error_is_exception(self) -> None:
        """``GitToolError`` is a subclass of ``Exception``."""
        assert issubclass(GitToolError, Exception)

    def test_configuration_error_hierarchy(self) -> None:
        """``ConfigurationError`` inherits from ``GitToolError``."""
        assert issubclass(ConfigurationError, GitToolError)

    def test_git_command_error_hierarchy(self) -> None:
        """``GitCommandError`` inherits from ``GitToolError``."""
        assert issubclass(GitCommandError, GitToolError)

    def test_configuration_error_message(self) -> None:
        """``ConfigurationError`` preserves the message."""
        exc = ConfigurationError("git not found")
        assert str(exc) == "git not found"

    def test_git_command_error_message(self) -> None:
        """``GitCommandError`` preserves the message."""
        exc = GitCommandError("git status failed (exit 1): error")
        assert str(exc) == "git status failed (exit 1): error"


# ============================================================================
# TestIsForbidden
# ============================================================================


class TestIsForbidden:
    """Unit tests for ``_is_forbidden`` forbidden-operation detection."""

    def test_force_push_main_is_forbidden(self) -> None:
        """Force push to main is forbidden."""
        assert _is_forbidden(["push", "--force", "origin", "main"], None)

    def test_force_push_master_is_forbidden(self) -> None:
        """Force push to master is forbidden."""
        assert _is_forbidden(["push", "--force", "origin", "master"], None)

    def test_force_push_short_flag_main_is_forbidden(self) -> None:
        """Force push with -f to main is forbidden."""
        assert _is_forbidden(["push", "-f", "origin", "main"], None)

    def test_force_push_short_flag_master_is_forbidden(self) -> None:
        """Force push with -f to master is forbidden."""
        assert _is_forbidden(["push", "-f", "origin", "master"], None)

    def test_force_push_branch_parameter_main(self) -> None:
        """Force push with branch='main' parameter is forbidden."""
        assert _is_forbidden(["push", "--force", "origin"], "main")

    def test_force_push_branch_parameter_master(self) -> None:
        """Force push with branch='master' parameter is forbidden."""
        assert _is_forbidden(["push", "--force", "origin"], "master")

    def test_normal_push_main_is_not_forbidden(self) -> None:
        """Normal push to main is NOT forbidden."""
        assert not _is_forbidden(["push", "origin", "main"], None)

    def test_normal_push_master_is_not_forbidden(self) -> None:
        """Normal push to master is NOT forbidden."""
        assert not _is_forbidden(["push", "origin", "master"], None)

    def test_force_push_feature_branch_is_not_forbidden(self) -> None:
        """Force push to a feature branch is NOT forbidden."""
        assert not _is_forbidden(
            ["push", "--force", "origin", "feature/x"], None
        )

    def test_status_is_not_push(self) -> None:
        """git status has nothing to do with push."""
        assert not _is_forbidden(["status"], None)

    def test_fewer_than_three_args_not_forbidden(self) -> None:
        """Commands with fewer than 3 args are never push-related."""
        assert not _is_forbidden(["diff"], None)


# ============================================================================
# TestRunGit — subprocess execution
# ============================================================================


class TestRunGit:
    """Tests for ``_run_git`` using mocked ``create_subprocess_exec``."""

    def test_successful_command(self) -> None:
        """A successful git command returns (0, stdout, stderr)."""
        mock_proc = _make_mock_process(
            returncode=0, stdout="output", stderr=""
        )
        with patch(
            "src.mcp.tools.git_tool.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            code, stdout, stderr = asyncio.run(_run_git("status", cwd="/repo"))
        assert code == 0
        assert stdout == "output"
        assert stderr == ""

    def test_failed_command(self) -> None:
        """A failed git command returns non-zero returncode."""
        mock_proc = _make_mock_process(
            returncode=128, stdout="", stderr="fatal: not a git repository"
        )
        with patch(
            "src.mcp.tools.git_tool.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            code, stdout, stderr = asyncio.run(
                _run_git("status", cwd="/not-repo")
            )
        assert code == 128
        assert stderr == "fatal: not a git repository"

    def test_stderr_captured(self) -> None:
        """stderr is captured even on success (warnings)."""
        mock_proc = _make_mock_process(
            returncode=0, stdout="ok", stderr="warning: something"
        )
        with patch(
            "src.mcp.tools.git_tool.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            _code, stdout, stderr = asyncio.run(
                _run_git("diff", cwd="/repo")
            )
        assert stderr == "warning: something"

    def test_unicode_in_output(self) -> None:
        """Unicode characters in git output are handled."""
        text = "r\u00e9sum\u00e9"
        mock_proc = _make_mock_process(
            returncode=0, stdout=text, stderr=""
        )
        with patch(
            "src.mcp.tools.git_tool.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            _code, stdout, _stderr = asyncio.run(
                _run_git("log", cwd="/repo")
            )
        assert stdout == text


# ============================================================================
# TestAuthLevels
# ============================================================================


class TestAuthLevels:
    """Verify correct auth levels on each registered tool function."""

    def test_git_status_is_read_auto(self) -> None:
        """``git_status`` → ``READ_AUTO``."""
        assert git_status._auth_level is AuthLevel.READ_AUTO  # type: ignore[attr-defined]

    def test_git_log_is_read_auto(self) -> None:
        """``git_log`` → ``READ_AUTO``."""
        assert git_log._auth_level is AuthLevel.READ_AUTO  # type: ignore[attr-defined]

    def test_git_diff_is_read_auto(self) -> None:
        """``git_diff`` → ``READ_AUTO``."""
        assert git_diff._auth_level is AuthLevel.READ_AUTO  # type: ignore[attr-defined]

    def test_git_commit_is_write_notify(self) -> None:
        """``git_commit`` → ``WRITE_NOTIFY``."""
        assert git_commit._auth_level is AuthLevel.WRITE_NOTIFY  # type: ignore[attr-defined]

    def test_git_push_is_write_notify(self) -> None:
        """``git_push`` (normal) → ``WRITE_NOTIFY``."""
        assert git_push._auth_level is AuthLevel.WRITE_NOTIFY  # type: ignore[attr-defined]

    def test_git_push_force_is_destructive_approval(self) -> None:
        """``git_push_force`` → ``DESTRUCTIVE_APPROVAL``."""
        assert git_push_force._auth_level is AuthLevel.DESTRUCTIVE_APPROVAL  # type: ignore[attr-defined]


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Smoke test for ``register_tools`` entry-point."""

    def test_registers_six_tools(self) -> None:
        """``register_tools`` calls ``mcp.tool()`` exactly six times."""
        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count == 6

    def test_register_tools_returns_none(self) -> None:
        """``register_tools`` returns ``None``."""
        mock_mcp = MagicMock()
        result = register_tools(mock_mcp)
        assert result is None


# ============================================================================
# TestGitStatus
# ============================================================================


class TestGitStatus:
    """Tests for ``_git_status`` subprocess-level behavior."""

    def test_status_returns_output(self, monkeypatch: Any) -> None:
        """git status returns porcelain output."""
        from src.mcp.tools.git_tool import _git_status

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "M modified.txt", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_status("."))
        assert result == "M modified.txt"

    def test_status_no_changes(self, monkeypatch: Any) -> None:
        """git status returns 'No changes.' when clean."""
        from src.mcp.tools.git_tool import _git_status

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_status("."))
        assert result == "No changes."

    def test_status_failure_raises(self, monkeypatch: Any) -> None:
        """git status non-zero exit raises GitCommandError."""
        from src.mcp.tools.git_tool import _git_status

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (128, "", "fatal: not a git repository")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        with pytest.raises(GitCommandError, match="git status failed"):
            asyncio.run(_git_status("/not-a-repo"))


# ============================================================================
# TestGitLog
# ============================================================================


class TestGitLog:
    """Tests for ``_git_log`` subprocess-level behavior."""

    def test_log_returns_commits(self, monkeypatch: Any) -> None:
        """git log returns one-line decorated output."""
        from src.mcp.tools.git_tool import _git_log

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "abc1234 feat: add git tool", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_log("."))
        assert "abc1234" in result

    def test_log_no_commits(self, monkeypatch: Any) -> None:
        """git log returns 'No commits.' when repo has no commits."""
        from src.mcp.tools.git_tool import _git_log

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_log("."))
        assert result == "No commits."

    def test_log_failure_raises(self, monkeypatch: Any) -> None:
        """git log non-zero exit raises GitCommandError."""
        from src.mcp.tools.git_tool import _git_log

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (128, "", "fatal: not a git repository")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        with pytest.raises(GitCommandError, match="git log failed"):
            asyncio.run(_git_log("/not-a-repo"))


# ============================================================================
# TestGitDiff
# ============================================================================


class TestGitDiff:
    """Tests for ``_git_diff`` subprocess-level behavior."""

    def test_diff_returns_output(self, monkeypatch: Any) -> None:
        """git diff returns diff output."""
        from src.mcp.tools.git_tool import _git_diff

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "diff --git a/file b/file", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_diff("."))
        assert "diff --git" in result

    def test_diff_staged(self, monkeypatch: Any) -> None:
        """git diff --staged is passed correctly."""
        from src.mcp.tools.git_tool import _git_diff

        captured_args: list[str] = []

        async def mock_run(
            *args: str, **kwargs: Any
        ) -> tuple[int, str, str]:
            captured_args.extend(args)
            return (0, "staged changes", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_diff(".", staged=True))
        assert "--staged" in captured_args
        assert result == "staged changes"

    def test_diff_no_changes(self, monkeypatch: Any) -> None:
        """git diff returns 'No changes.' when clean."""
        from src.mcp.tools.git_tool import _git_diff

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_diff("."))
        assert result == "No changes."


# ============================================================================
# TestGitCommit
# ============================================================================


class TestGitCommit:
    """Tests for ``_git_commit`` subprocess-level behavior."""

    def test_commit_success(self, monkeypatch: Any) -> None:
        """git commit succeeds and returns output."""
        from src.mcp.tools.git_tool import _git_commit

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "[main abc1234] feat: new feature", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_commit(".", "feat: new feature"))
        assert "abc1234" in result

    def test_commit_auto_stages_files(self, monkeypatch: Any) -> None:
        """git commit with files auto-stages them via git add."""
        from src.mcp.tools.git_tool import _git_commit

        add_calls: list[list[str]] = []
        commit_called: list[bool] = [False]

        async def mock_run(
            *args: str, **kwargs: Any
        ) -> tuple[int, str, str]:
            add_calls.append(list(args))
            if args[0] == "add":
                return (0, "", "")
            commit_called[0] = True
            return (0, "[main xyz] test", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        asyncio.run(_git_commit(".", "test", files=["a.txt", "b.txt"]))
        assert commit_called[0] is True
        added_files = [
            a[1] for a in add_calls if len(a) >= 2 and a[0] == "add"
        ]
        assert "a.txt" in added_files
        assert "b.txt" in added_files

    def test_commit_without_files(self, monkeypatch: Any) -> None:
        """git commit without files only commits staged changes."""
        from src.mcp.tools.git_tool import _git_commit

        calls: list[tuple[str, ...]] = []

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            calls.append(args)
            return (0, "ok", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        asyncio.run(_git_commit(".", "commit staged"))
        assert len(calls) == 1
        assert calls[0][0] == "commit"

    def test_commit_failure_raises(self, monkeypatch: Any) -> None:
        """git commit non-zero exit raises GitCommandError."""
        from src.mcp.tools.git_tool import _git_commit

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (1, "", "nothing to commit")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        with pytest.raises(GitCommandError, match="git commit failed"):
            asyncio.run(_git_commit(".", "empty commit"))


# ============================================================================
# TestGitPush
# ============================================================================


class TestGitPush:
    """Tests for ``_git_push`` subprocess-level behavior."""

    def test_normal_push_success(self, monkeypatch: Any) -> None:
        """Normal push succeeds."""
        from src.mcp.tools.git_tool import _git_push

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "Everything up-to-date", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_push(".", force=False))
        assert result == "Everything up-to-date"

    def test_force_push_feature_branch_succeeds(
        self, monkeypatch: Any
    ) -> None:
        """Force push to feature branch succeeds."""
        from src.mcp.tools.git_tool import _git_push

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "Forced update", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(
            _git_push(".", force=True, branch="feature/x")
        )
        assert result == "Forced update"

    def test_force_push_main_is_forbidden(self) -> None:
        """Force push to main raises ForbiddenOperationError."""
        from src.mcp.tools.git_tool import _git_push

        with pytest.raises(
            ForbiddenOperationError,
            match="Force push to 'main' branch is forbidden",
        ):
            asyncio.run(_git_push(".", force=True, branch="main"))

    def test_force_push_master_is_forbidden(self) -> None:
        """Force push to master raises ForbiddenOperationError."""
        from src.mcp.tools.git_tool import _git_push

        with pytest.raises(
            ForbiddenOperationError,
            match="Force push to 'master' branch is forbidden",
        ):
            asyncio.run(_git_push(".", force=True, branch="master"))

    def test_push_failure_raises(self, monkeypatch: Any) -> None:
        """Normal push failure raises GitCommandError."""
        from src.mcp.tools.git_tool import _git_push

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (128, "", "fatal: remote not found")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        with pytest.raises(GitCommandError, match="git push failed"):
            asyncio.run(_git_push(".", force=False))

    def test_push_success_with_empty_stdout(
        self, monkeypatch: Any
    ) -> None:
        """Push success with empty stdout returns default message."""
        from src.mcp.tools.git_tool import _git_push

        async def mock_run(
            *args: Any, **kwargs: Any
        ) -> tuple[int, str, str]:
            return (0, "", "")

        monkeypatch.setattr("src.mcp.tools.git_tool._run_git", mock_run)
        result = asyncio.run(_git_push(".", force=False))
        assert result == "Push successful."


# ============================================================================
# TestAuthLevelEnforcement
# ============================================================================


class TestAuthLevelEnforcement:
    """Verify auth-level enforcement on the decorated tool functions."""

    def test_force_push_main_blocked_in_decorated(
        self, monkeypatch: Any
    ) -> None:
        """Force push to main is blocked even after DESTRUCTIVE_APPROVAL.

        The decorated ``git_push_force`` carries DESTRUCTIVE_APPROVAL,
        and the internal ``_git_push_impl`` raises
        ``ForbiddenOperationError`` when targeting main/master.
        We mock the approval to resolve instantly so the inner check fires.
        """
        assert git_push_force._auth_level is AuthLevel.DESTRUCTIVE_APPROVAL  # type: ignore[attr-defined]

        # Mock the approval to return True instantly (approved).
        async def mock_approval(*args: Any, **kwargs: Any) -> bool:
            return True

        monkeypatch.setattr("src.mcp.auth._wait_for_approval", mock_approval)
        monkeypatch.setattr(
            "src.mcp.auth._send_discord_notification",
            AsyncMock(),
        )

        with pytest.raises(
            ForbiddenOperationError,
            match="Force push to 'main' branch is forbidden",
        ):
            asyncio.run(git_push_force(repo_path=".", branch="main"))

    def test_forbidden_operation_error_is_auth_import(self) -> None:
        """ForbiddenOperationError is imported from src.mcp.auth."""
        from src.mcp.auth import ForbiddenOperationError as AuthFE

        assert AuthFE is ForbiddenOperationError


# ============================================================================
# TestEnvironment
# ============================================================================


class TestEnvironment:
    """Tests for environment / PAT handling."""

    def test_build_env_includes_pat(self, monkeypatch: Any) -> None:
        """_build_env includes GITHUB_PAT when set."""
        from src.mcp.tools.git_tool import _build_env

        monkeypatch.setenv("GITHUB_PAT", "ghp_test123")
        env = _build_env()
        assert env is not None
        assert env.get("GITHUB_PAT") == "ghp_test123"

    def test_build_env_warns_when_pat_missing(
        self, monkeypatch: Any
    ) -> None:
        """_build_env works even without GITHUB_PAT."""
        from src.mcp.tools.git_tool import _build_env

        monkeypatch.delenv("GITHUB_PAT", raising=False)
        env = _build_env()
        assert env is not None
        assert env.get("GITHUB_PAT", "") == ""


# ============================================================================
# TestAssertZero
# ============================================================================


class TestAssertZero:
    """Tests for ``_assert_zero`` helper."""

    def test_zero_code_no_error(self) -> None:
        """Exit code 0 does not raise."""
        from src.mcp.tools.git_tool import _assert_zero

        _assert_zero(0, "", "status")  # should not raise

    def test_nonzero_code_raises(self) -> None:
        """Non-zero exit code raises GitCommandError."""
        from src.mcp.tools.git_tool import _assert_zero

        with pytest.raises(GitCommandError, match="git push failed"):
            _assert_zero(128, "fatal: error", "push")


# ============================================================================
# TestForbiddenPatternsEdgeCases
# ============================================================================


class TestForbiddenPatternsEdgeCases:
    """Additional edge cases for forbidden operation detection."""

    def test_push_without_force_any_branch_ok(self) -> None:
        """Any branch push without force is allowed."""
        assert not _is_forbidden(["push", "origin", "main"], None)
        assert not _is_forbidden(["push", "origin", "master"], None)
        assert not _is_forbidden(["push", "origin", "dev"], None)

    def test_mixed_args_force_in_middle(self) -> None:
        """Force flag can appear in any position."""
        assert _is_forbidden(
            ["push", "origin", "--force", "main"], None
        )

    def test_non_push_command_with_force(self) -> None:
        """--force on non-push command is not caught."""
        assert not _is_forbidden(["fetch", "--force"], None)

    def test_force_with_lease_main_is_forbidden(self) -> None:
        """--force-with-lease to main is forbidden."""
        assert _is_forbidden(
            ["push", "--force-with-lease", "origin", "main"], None
        )

    def test_force_with_lease_feature_branch_ok(self) -> None:
        """--force-with-lease to feature branch is allowed."""
        assert not _is_forbidden(
            ["push", "--force-with-lease", "origin", "feature/x"], None
        )

    def test_case_insensitive_main_MAIN(self) -> None:
        """Uppercase MAIN is still detected as forbidden."""
        assert _is_forbidden(
            ["push", "--force", "origin", "MAIN"], None
        )

    def test_case_insensitive_master_Master(self) -> None:
        """Mixed-case Master is still detected as forbidden."""
        assert _is_forbidden(
            ["push", "-f", "origin", "Master"], None
        )

    def test_refspec_head_refs_heads_main(self) -> None:
        """HEAD:refs/heads/main refspec is forbidden."""
        assert _is_forbidden(
            ["push", "--force", "origin", "HEAD:refs/heads/main"], None
        )

    def test_refspec_feature_main(self) -> None:
        """feature:main refspec destination is forbidden."""
        assert _is_forbidden(
            ["push", "--force", "origin", "feature:main"], None
        )

    def test_refspec_feature_branch_ok(self) -> None:
        """feature:dev refspec destination is allowed."""
        assert not _is_forbidden(
            ["push", "--force", "origin", "feature:dev"], None
        )

    def test_branch_param_case_insensitive(self) -> None:
        """branch='MAIN' parameter is still forbidden."""
        assert _is_forbidden(
            ["push", "--force", "origin"], "MAIN"
        )