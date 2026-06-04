"""Guinevere Observability — metrics, logging, error tracking."""

from .sentry_integration import init_sentry

__all__ = ["init_sentry"]
