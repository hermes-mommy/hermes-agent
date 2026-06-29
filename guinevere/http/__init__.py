"""Guinevere HTTP server — FastAPI app with lifespan-managed TaskGroup."""

from guinevere.http.server import app, create_app

__all__ = ["app", "create_app"]
