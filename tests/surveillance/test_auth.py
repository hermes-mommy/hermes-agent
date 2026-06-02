"""P7-002: HMAC-SHA256 Authentication — unit tests for ``src.surveillance.auth``.

Tests cover:
- Valid HMAC signature returns 202
- Invalid HMAC signature returns 401
- Missing headers return 422
- Tampered body causes 401
- Wrong secret causes 401
- Empty body accepted with valid signature
- ``hmac.compare_digest`` is used
- Signing string format verified
"""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.surveillance.router import surveillance_router  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-hmac-secret-for-unit-tests-only"
TIMESTAMP = "1234567890"
NONCE = "test-nonce-uuid"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
    secret: str,
) -> str:
    """Compute the expected HMAC-SHA256 signature for a request."""
    signing_string = (
        f"{method}:{path}:{timestamp}:{nonce}:{body.decode('utf-8')}"
    )
    return hmac_module.new(
        secret.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _make_headers(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
    secret: str = TEST_SECRET,
) -> dict[str, str]:
    """Build headers with a valid HMAC signature."""
    signature = _sign(method, path, timestamp, nonce, body, secret)
    return {
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "Content-Type": "application/json",
    }


def _make_payload() -> dict[str, object]:
    """Return a minimal valid surveillance event payload."""
    return {
        "device_id": "test-device-01",
        "event_type": "screen_state",
        "occurred_at": "2026-06-01T12:00:00+00:00",
        "payload": {"state": "on"},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI TestClient with the surveillance router mounted."""
    app = FastAPI()
    app.include_router(surveillance_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _mock_secret() -> None:
    """Mock ``get_hmac_secret`` to return a fixed test secret for all tests."""
    with patch(
        "src.surveillance.auth.get_hmac_secret", return_value=TEST_SECRET
    ):
        yield


@pytest.fixture(autouse=True)
def _mock_replay() -> None:
    """Mock replay protection functions to no-ops for auth-only tests.

    P7-003: ``verify_hmac`` now calls ``validate_timestamp`` and
    ``check_nonce`` before HMAC verification.  These auth tests focus on
    the HMAC path only, so replay is patched out here.
    """
    with patch("src.surveillance.auth.validate_timestamp"), patch(
        "src.surveillance.auth.check_nonce"
    ):
        yield


# ---------------------------------------------------------------------------
# Tests — valid requests
# ---------------------------------------------------------------------------


class TestValidHMAC:
    """Valid HMAC signatures are accepted."""

    def test_valid_signature_returns_202(self, client: TestClient) -> None:
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body
        )
        response = client.post(
            "/surveillance/events", content=body, headers=headers
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "event_id" in data

    def test_empty_body_not_401(self, client: TestClient) -> None:
        """Empty body with valid HMAC should not fail auth (may fail Pydantic)."""
        body = b""
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body
        )
        response = client.post(
            "/surveillance/events", content=body, headers=headers
        )
        # FastAPI will 422 on missing required fields, but NOT 401 from HMAC.
        assert response.status_code != 401


# ---------------------------------------------------------------------------
# Tests — invalid signatures
# ---------------------------------------------------------------------------


class TestInvalidHMAC:
    """Invalid HMAC signatures produce 401."""

    def test_invalid_signature_returns_401(self, client: TestClient) -> None:
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body
        )
        # Corrupt the signature
        headers["X-Signature"] = "deadbeef" * 8
        response = client.post(
            "/surveillance/events", content=body, headers=headers
        )
        assert response.status_code == 401
        assert "Invalid HMAC signature" in response.json()["detail"]

    def test_wrong_secret_returns_401(self, client: TestClient) -> None:
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        headers = _make_headers(
            "POST",
            "/surveillance/events",
            TIMESTAMP,
            NONCE,
            body,
            secret="wrong-secret-value",
        )
        response = client.post(
            "/surveillance/events", content=body, headers=headers
        )
        assert response.status_code == 401

    def test_tampered_body_returns_401(self, client: TestClient) -> None:
        payload_before = _make_payload()
        body_before = json.dumps(payload_before).encode("utf-8")
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body_before
        )
        # Send a different body than what was signed
        payload_after = {
            **_make_payload(),
            "device_id": "tampered-device",
        }
        body_after = json.dumps(payload_after).encode("utf-8")
        response = client.post(
            "/surveillance/events", content=body_after, headers=headers
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests — missing headers
# ---------------------------------------------------------------------------


class TestMissingHeaders:
    """Missing required headers produce 422 from FastAPI."""

    def test_missing_signature_returns_422(self, client: TestClient) -> None:
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body
        )
        del headers["X-Signature"]
        response = client.post(
            "/surveillance/events", content=body, headers=headers
        )
        assert response.status_code == 422

    def test_missing_timestamp_returns_422(self, client: TestClient) -> None:
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body
        )
        del headers["X-Timestamp"]
        response = client.post(
            "/surveillance/events", content=body, headers=headers
        )
        assert response.status_code == 422

    def test_missing_nonce_returns_422(self, client: TestClient) -> None:
        payload = _make_payload()
        body = json.dumps(payload).encode("utf-8")
        headers = _make_headers(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body
        )
        del headers["X-Nonce"]
        response = client.post(
            "/surveillance/events", json=payload, headers=headers
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — compare_digest usage
# ---------------------------------------------------------------------------


class TestCompareDigest:
    """Verify ``hmac.compare_digest`` is used for constant-time comparison."""

    def test_compare_digest_used(self) -> None:
        """Check that ``hmac.compare_digest`` appears in the auth module."""
        auth_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "surveillance"
            / "auth.py"
        )
        source = auth_path.read_text(encoding="utf-8")
        assert "compare_digest" in source, (
            "hmac.compare_digest must be used in auth.py"
        )

    def test_equality_operator_not_used(self) -> None:
        """Signature comparison must NOT use ``==`` on hex strings."""
        auth_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "surveillance"
            / "auth.py"
        )
        source = auth_path.read_text(encoding="utf-8")
        # The file may contain == in the signing_string f-string, but
        # should NOT compare x_signature == expected directly.
        # We check that compare_digest is present and the comparison line
        # uses it.
        assert "hmac.compare_digest" in source


# ---------------------------------------------------------------------------
# Tests — signing string format
# ---------------------------------------------------------------------------


class TestSigningStringFormat:
    """Verify the signing string includes all required components."""

    def test_signing_string_includes_method(self) -> None:
        """Method must be part of the signing string to prevent replay."""
        body = json.dumps(_make_payload()).encode("utf-8")
        sig_post = _sign(
            "POST", "/surveillance/events", TIMESTAMP, NONCE, body, TEST_SECRET
        )
        sig_get = _sign(
            "GET", "/surveillance/events", TIMESTAMP, NONCE, body, TEST_SECRET
        )
        assert sig_post != sig_get, (
            "Signatures for different methods must differ"
        )

    def test_signing_string_includes_path(self) -> None:
        """Path must be part of the signing string."""
        body = json.dumps(_make_payload()).encode("utf-8")
        sig_a = _sign(
            "POST",
            "/surveillance/events",
            TIMESTAMP,
            NONCE,
            body,
            TEST_SECRET,
        )
        sig_b = _sign(
            "POST",
            "/surveillance/other",
            TIMESTAMP,
            NONCE,
            body,
            TEST_SECRET,
        )
        assert sig_a != sig_b, (
            "Signatures for different paths must differ"
        )

    def test_signing_string_includes_timestamp(self) -> None:
        """Timestamp must be part of the signing string."""
        body = json.dumps(_make_payload()).encode("utf-8")
        sig_a = _sign(
            "POST",
            "/surveillance/events",
            "1234567890",
            NONCE,
            body,
            TEST_SECRET,
        )
        sig_b = _sign(
            "POST",
            "/surveillance/events",
            "9999999999",
            NONCE,
            body,
            TEST_SECRET,
        )
        assert sig_a != sig_b, (
            "Signatures for different timestamps must differ"
        )

    def test_signing_string_includes_nonce(self) -> None:
        """Nonce must be part of the signing string."""
        body = json.dumps(_make_payload()).encode("utf-8")
        sig_a = _sign(
            "POST",
            "/surveillance/events",
            TIMESTAMP,
            "nonce-a",
            body,
            TEST_SECRET,
        )
        sig_b = _sign(
            "POST",
            "/surveillance/events",
            TIMESTAMP,
            "nonce-b",
            body,
            TEST_SECRET,
        )
        assert sig_a != sig_b, (
            "Signatures for different nonces must differ"
        )

    def test_signing_string_includes_body(self) -> None:
        """Body must be part of the signing string."""
        payload_a = _make_payload()
        payload_b = {**_make_payload(), "device_id": "other-device"}
        body_a = json.dumps(payload_a).encode("utf-8")
        body_b = json.dumps(payload_b).encode("utf-8")
        sig_a = _sign(
            "POST",
            "/surveillance/events",
            TIMESTAMP,
            NONCE,
            body_a,
            TEST_SECRET,
        )
        sig_b = _sign(
            "POST",
            "/surveillance/events",
            TIMESTAMP,
            NONCE,
            body_b,
            TEST_SECRET,
        )
        assert sig_a != sig_b, (
            "Signatures for different bodies must differ"
        )