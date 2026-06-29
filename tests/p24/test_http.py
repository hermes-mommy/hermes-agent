"""Tests for the guinevere.http package.

Uses ``fastapi.testclient.TestClient`` (sync wrapper around httpx).
PG/Redis are mocked — no live services required.

Ported/extended from the endpoints in ``src/core/main.py`` L847-1052.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a TestClient with a fresh app per test.

    The lifespan's PG/Redis connections are mocked so no live services
    are required.
    """
    import guinevere.http.server as server_mod

    server_mod._app = None

    mock_pg_pool = AsyncMock()
    mock_pg_pool.close = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with (
        patch("guinevere.config.load_settings") as mock_load,
        patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pg_pool),
        patch("redis.asyncio.from_url", return_value=mock_redis),
    ):
        mock_settings = MagicMock()
        mock_settings.database.pg_dsn = "postgresql://localhost:5432/test"
        mock_settings.redis.url = "redis://localhost:6379"
        mock_load.return_value = mock_settings

        app = server_mod.create_app()
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def client_no_config() -> Generator[TestClient, None, None]:
    """TestClient where config loading fails (fail-soft)."""
    import guinevere.http.server as server_mod

    server_mod._app = None

    with (
        patch("guinevere.config.load_settings", side_effect=RuntimeError("no config")),
        patch("asyncpg.create_pool", new_callable=AsyncMock, side_effect=RuntimeError("no pg")),
        patch("redis.asyncio.from_url", side_effect=RuntimeError("no redis")),
    ):
        app = server_mod.create_app()
        with TestClient(app) as c:
            yield c


class TestHealthLiveness:
    """Liveness probe (/health) must always return 200."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["service"] == "guinevere-core"

    def test_health_returns_200_no_config(self, client_no_config: TestClient) -> None:
        response = client_no_config.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestHealthReadiness:
    """Readiness probe (/health/ready) — fail-soft per D2."""

    def test_ready_with_mocked_infra(self, client: TestClient) -> None:
        response = client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] in ("ready", "degraded")
        assert "components" in body
        assert "config" in body["components"]

    def test_ready_degraded_no_config(self, client_no_config: TestClient) -> None:
        response = client_no_config.get("/health/ready")
        # D2: degraded (200), not hard 503.
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["components"]["config"]["status"] == "degraded"


class TestHealthAgent:
    """Agent state endpoint (/health/agent) — NEW per r11."""

    def test_agent_state_structure(self, client: TestClient) -> None:
        response = client.get("/health/agent")
        assert response.status_code == 200
        body = response.json()
        assert body["service"] == "guinevere-core"
        # M3 not wired yet — fields should be None.
        assert body["turn"] is None
        assert body["tokens_used"] is None
        assert body["emotion"] is None


class TestMetrics:
    """Prometheus /metrics endpoint."""

    def test_metrics_returns_200(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
        text = response.text
        assert "guinevere_" in text or "python_" in text or len(text) > 0

    def test_metrics_content_type(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")


class TestRoot:
    """Root endpoint (/)."""

    def test_root_returns_200(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "active"
        assert "Guinevere" in body["message"]


class TestRateLimiter:
    """Rate limiter — exempt paths bypass."""

    def test_health_exempt_from_rate_limit(self, client: TestClient) -> None:
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200

    def test_metrics_exempt_from_rate_limit(self, client: TestClient) -> None:
        for _ in range(50):
            response = client.get("/metrics")
            assert response.status_code == 200

    def test_root_exempt_from_rate_limit(self, client: TestClient) -> None:
        for _ in range(50):
            response = client.get("/")
            assert response.status_code == 200


class TestAppImport:
    """App must be importable and correctly typed."""

    def test_app_is_fastapi_instance(self) -> None:
        from guinevere.http.server import app

        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_create_app_returns_singleton(self) -> None:
        import guinevere.http.server as server_mod

        server_mod._app = None
        a = server_mod.create_app()
        b = server_mod.create_app()
        assert a is b

    def test_init_reexports(self) -> None:
        from guinevere.http import app, create_app

        from fastapi import FastAPI

        assert isinstance(app, FastAPI)
        assert callable(create_app)
