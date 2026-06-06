#!/usr/bin/env python3
"""Capture Redis DB5 cost state for Phase 6 Step 9."""
import os
import sys
import redis

label = sys.argv[1] if len(sys.argv) > 1 else "STATE"

pw = os.environ.get("REDIS_PASSWORD", "")
r = redis.Redis(
    host="localhost", port=6380, db=5,
    username="guinevere_core", password=pw,
    decode_responses=True,
)
print(f"{label} cost:current_month:", r.get("cost:current_month") or 0)
print(f"{label} cost:current_day:", r.get("cost:current_day") or 0)
print(f"{label} cost:monthly:2026-06:", r.get("cost:monthly:2026-06") or 0)
by_model = r.keys("cost:by_model:*")
print(f"{label} KEYS cost:by_model:*:", sorted(by_model) if by_model else "(none)")
for km in sorted(by_model or []):
    print(f"{label}   {km} =", r.get(km))
print(f"{label} budget:monthly_cap:", r.get("budget:monthly_cap") or 30)
print(f"{label} cost:current_month type:", type(r.get("cost:current_month")).__name__)
