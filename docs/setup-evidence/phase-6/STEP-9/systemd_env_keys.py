#!/usr/bin/env python3
"""List systemd environment keys without values."""
from __future__ import annotations

import shlex
import subprocess

for unit in ["guinevere-core", "hermes-gateway"]:
    out = subprocess.check_output(["systemctl", "show", unit, "-p", "Environment"], text=True)
    raw = out.split("=", 1)[1].strip()
    keys = []
    for item in shlex.split(raw):
        if "=" not in item:
            continue
        key = item.split("=", 1)[0]
        if "REDIS" in key or "PASSWORD" in key:
            keys.append(key)
    print(unit, sorted(keys))
