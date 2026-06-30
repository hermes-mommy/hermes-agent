from __future__ import annotations

"""Canonical X Poster Prometheus metrics surface."""

import structlog
from prometheus_client import Counter, Gauge, Histogram, start_http_server

_logger = structlog.get_logger(__name__)

# Queue
x_poster_queue_depth = Gauge(
    "x_poster_queue_depth",
    "Current number of posts in queue",
    ["state"],
)

x_poster_posts_total = Counter(
    "x_poster_posts_total",
    "Total posts processed",
    ["status"],
)

x_poster_post_duration_seconds = Histogram(
    "x_poster_post_duration_seconds",
    "Time from queue to published",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

# Schedule
x_poster_schedule_slots_total = Gauge(
    "x_poster_schedule_slots_total",
    "Total schedule slots per day",
)

x_poster_schedule_slots_used = Gauge(
    "x_poster_schedule_slots_used",
    "Currently occupied slots today",
)

# Caption
x_poster_captions_generated_total = Counter(
    "x_poster_captions_generated_total",
    "Captions generated via Hermes",
    ["status"],
)

# Moderation
x_poster_moderation_total = Counter(
    "x_poster_moderation_total",
    "Content moderation checks",
    ["result"],
)

# X API actions
x_poster_x_api_actions_total = Counter(
    "x_poster_x_api_actions_total",
    "X API actions performed",
    ["action", "status"],
)

# Circuit Breaker
x_poster_circuit_breaker_state = Gauge(
    "x_poster_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
)

# Session
x_poster_session_health = Gauge(
    "x_poster_session_health",
    "X session health (1=healthy, 0=expired)",
)

# Engagement
x_poster_engagement_impressions = Gauge(
    "x_poster_engagement_impressions",
    "Engagement impressions (rolling window)",
)
x_poster_engagement_likes = Gauge(
    "x_poster_engagement_likes",
    "Engagement likes (rolling window)",
)
x_poster_engagement_replies = Gauge(
    "x_poster_engagement_replies",
    "Engagement replies (rolling window)",
)
x_poster_engagement_retweets = Gauge(
    "x_poster_engagement_retweets",
    "Engagement retweets (rolling window)",
)
x_poster_engagement_quotes = Gauge(
    "x_poster_engagement_quotes",
    "Engagement quotes (rolling window)",
)
x_poster_engagement_bookmarks = Gauge(
    "x_poster_engagement_bookmarks",
    "Engagement bookmarks (rolling window)",
)
x_poster_engagement_posts_tracked = Gauge(
    "x_poster_engagement_posts_tracked",
    "Distinct posts with engagement records",
)


def set_queue_depth(state: str, count: int) -> None:
    x_poster_queue_depth.labels(state=state).set(count)


def record_post(status: str) -> None:
    x_poster_posts_total.labels(status=status).inc()


def observe_post_duration(seconds: float) -> None:
    x_poster_post_duration_seconds.observe(seconds)


def set_schedule_total(total: int) -> None:
    x_poster_schedule_slots_total.set(total)


def set_schedule_used(used: int) -> None:
    x_poster_schedule_slots_used.set(used)


def record_caption_generated(status: str) -> None:
    x_poster_captions_generated_total.labels(status=status).inc()


def record_moderation(result: str) -> None:
    x_poster_moderation_total.labels(result=result).inc()


def record_x_api_action(action: str, status: str) -> None:
    x_poster_x_api_actions_total.labels(action=action, status=status).inc()


def set_circuit_breaker_state(state_value: int) -> None:
    x_poster_circuit_breaker_state.set(state_value)


def set_session_health(healthy: bool) -> None:
    x_poster_session_health.set(1 if healthy else 0)


def set_engagement_totals(
    impressions: int,
    likes: int,
    replies: int,
    retweets: int,
    quotes: int,
    bookmarks: int,
    posts_tracked: int,
) -> None:
    x_poster_engagement_impressions.set(impressions)
    x_poster_engagement_likes.set(likes)
    x_poster_engagement_replies.set(replies)
    x_poster_engagement_retweets.set(retweets)
    x_poster_engagement_quotes.set(quotes)
    x_poster_engagement_bookmarks.set(bookmarks)
    x_poster_engagement_posts_tracked.set(posts_tracked)


def start_metrics_server(host: str = "127.0.0.1", port: int = 9102) -> None:
    _logger.info("Starting X Poster metrics server", host=host, port=port)
    start_http_server(port=port, addr=host)
