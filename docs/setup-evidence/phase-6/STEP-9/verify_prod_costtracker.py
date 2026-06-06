#!/usr/bin/env python3
"""Verify production CostTracker can read Redis DB5 without printing secrets."""
from __future__ import annotations

import os

from src.core.services.cost_tracker import CostTracker

print("redis_password_present", bool(os.environ.get("REDIS_PASSWORD")))
tracker = CostTracker()
print("redis_ping", tracker.redis.ping())
budget = tracker.check_budget()
print("current_month", budget["current_month"])
print("monthly_cap", budget["monthly_cap"])
print("status", budget["status"])
print("by_model_keys", sorted(tracker.redis.keys("cost:by_model:*")))
