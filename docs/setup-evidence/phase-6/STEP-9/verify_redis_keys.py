#!/usr/bin/env python3
"""Read Phase 6 Redis DB5 cost keys without printing secrets."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, unquote

import redis


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


env = load_env(Path("/home/guinevere/.hermes/.env"))
redis_url = env.get("REDIS_URL")
if not redis_url:
    raise RuntimeError("missing REDIS_URL")
parsed = urlparse(redis_url)
password = unquote(parsed.password or "")
username = unquote(parsed.username or "guinevere_core")
port = parsed.port or 6380
r = redis.Redis(
    host=parsed.hostname or "localhost",
    port=port,
    db=5,
    username=username,
    password=password,
    decode_responses=True,
)
keys = [
    "cost:current_month",
    "cost:current_day",
    "cost:monthly:2026-06",
    "cost:daily:2026-06-06",
    "budget:monthly_cap",
    "cost:by_model:ds/deepseek-v4-flash",
]
for item in keys:
    print(item, r.get(item))
print("by_model_keys", sorted(r.keys("cost:by_model:*")))
