#!/usr/bin/env python3
"""Inspect REDIS_URL shape without printing credentials."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

for line in Path('/home/guinevere/.hermes/.env').read_text(encoding='utf-8', errors='replace').splitlines():
    if line.startswith('REDIS_URL='):
        value = line.split('=', 1)[1].strip().strip('"').strip("'")
        parsed = urlparse(value)
        print('scheme', parsed.scheme)
        print('username_present', parsed.username is not None)
        print('username', parsed.username or '<none>')
        print('password_present', parsed.password is not None)
        print('host', parsed.hostname)
        print('port', parsed.port)
        print('path', parsed.path)
        break
