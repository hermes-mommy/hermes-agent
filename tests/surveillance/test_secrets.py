"""P7-NEW: SOPS Secrets Helper — unit tests for ``src.surveillance.secrets``.

Tests cover:
- Environment variable fallback (dev/CI override)
- SOPS subprocess decryption (mocked)
- Module-level caching behaviour
- Clear errors when secret is unavailable
- SOPS decryption failure modes
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.surveillance.secrets import (  # noqa: E402
    _SECRETS_FILE,
    _clear_cache,
    get_hmac_secret,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_SECRET = "test-hmac-secret-aabbccdd"
_SOPS_DECRYPTED_YAML = (
    "surveillance:\n"
    f"    hmac_secret: {_FAKE_SECRET}\n"
)


def _make_sops_result(
    *,
    returncode: int = 0,
    stdout: str = _SOPS_DECRYPTED_YAML,
    stderr: str = "",
) -> MagicMock:
    """Build a ``subprocess.CompletedProcess``-like mock."""
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache() -> Iterator[None]:
    """Clear the secrets cache before and after every test."""
    _clear_cache()
    yield
    _clear_cache()


# ---------------------------------------------------------------------------
# Tests — environment variable fallback
# ---------------------------------------------------------------------------


class TestEnvVarFallback:
    """SURVEILLANCE_HMAC_SECRET env var takes precedence over SOPS."""

    def test_returns_env_var_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", _FAKE_SECRET)
        assert get_hmac_secret() == _FAKE_SECRET

    def test_does_not_call_sops_when_env_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", _FAKE_SECRET)
        with patch("src.surveillance.secrets.subprocess.run") as mock_run:
            get_hmac_secret()
            mock_run.assert_not_called()

    def test_empty_env_var_falls_through_to_sops(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty string env var should be treated as unset."""
        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", "")
        sops_result = _make_sops_result()
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            result = get_hmac_secret()
            assert result == _FAKE_SECRET


# ---------------------------------------------------------------------------
# Tests — SOPS decryption
# ---------------------------------------------------------------------------


class TestSopsDecryption:
    """SOPS subprocess decryption when env var is absent."""

    def test_decrypts_via_sops(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result()
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ) as mock_run:
            result = get_hmac_secret()
            assert result == _FAKE_SECRET
            mock_run.assert_called_once()

    def test_sops_called_with_correct_args(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result()
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ) as mock_run:
            get_hmac_secret()
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "sops",
                "--decrypt",
                str(_SECRETS_FILE),
            ]
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["text"] is True
            assert call_args[1]["check"] is False

    def test_raises_on_sops_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result(
            returncode=1,
            stdout="",
            stderr="sops: could not decrypt: no matching key",
        )
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            with pytest.raises(RuntimeError, match="SOPS decryption failed"):
                get_hmac_secret()

    def test_raises_on_missing_secrets_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        bad_yaml = "surveillance:\n    other_key: value\n"
        sops_result = _make_sops_result(stdout=bad_yaml)
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            with pytest.raises(
                RuntimeError, match="hmac_secret.*missing"
            ):
                get_hmac_secret()

    def test_raises_on_malformed_yaml(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result(stdout="just a string\n")
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            with pytest.raises(RuntimeError, match="non-dict"):
                get_hmac_secret()

    def test_raises_on_missing_surveillance_section(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result(stdout="other_section:\n    key: val\n")
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            with pytest.raises(RuntimeError, match="surveillance.*missing"):
                get_hmac_secret()

    def test_raises_on_empty_hmac_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result(
            stdout="surveillance:\n    hmac_secret: ''\n"
        )
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            with pytest.raises(RuntimeError, match="missing or empty"):
                get_hmac_secret()

    def test_raises_when_secrets_file_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        fake_file = tmp_path / "nonexistent.yaml"
        with patch("src.surveillance.secrets._SECRETS_FILE", fake_file):
            with pytest.raises(FileNotFoundError, match="not found"):
                get_hmac_secret()


# ---------------------------------------------------------------------------
# Tests — caching
# ---------------------------------------------------------------------------


class TestCaching:
    """Module-level singleton cache behaviour."""

    def test_cached_value_returned_on_second_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", "first-value")
        first = get_hmac_secret()

        # Mutate env — cache should still return the original value.
        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", "changed-value")
        second = get_hmac_secret()

        assert first == "first-value"
        assert second == "first-value"

    def test_sops_called_only_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result()
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ) as mock_run:
            get_hmac_secret()
            get_hmac_secret()
            get_hmac_secret()
            assert mock_run.call_count == 1

    def test_clear_cache_forces_reload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", "original")
        assert get_hmac_secret() == "original"

        _clear_cache()

        monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", "reloaded")
        assert get_hmac_secret() == "reloaded"


# ---------------------------------------------------------------------------
# Tests — no-secret-available error
# ---------------------------------------------------------------------------


class TestNoSecretAvailable:
    """Clear error when neither env var nor SOPS is available."""

    def test_runtime_error_when_sops_binary_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        with patch(
            "src.surveillance.secrets.subprocess.run",
            side_effect=FileNotFoundError("sops not installed"),
        ):
            with pytest.raises(FileNotFoundError):
                get_hmac_secret()

    def test_runtime_error_when_sops_returns_nonzero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SURVEILLANCE_HMAC_SECRET", raising=False)
        sops_result = _make_sops_result(
            returncode=127,
            stdout="",
            stderr="command not found",
        )
        with patch(
            "src.surveillance.secrets.subprocess.run",
            return_value=sops_result,
        ):
            with pytest.raises(RuntimeError, match="SOPS decryption failed"):
                get_hmac_secret()
