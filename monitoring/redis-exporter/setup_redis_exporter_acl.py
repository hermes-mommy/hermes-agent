#!/usr/bin/env python3
"""P8-004: Redis ACL setup for prometheus redis_exporter.

Creates a minimal-privilege ACL user for the redis_exporter to collect metrics.
Run on VPS: python3 monitoring/redis-exporter/setup_redis_exporter_acl.py

SECURITY: Password is read from SOPS-decrypted environment variable.
Never hardcode the actual password in this script.
"""

from __future__ import annotations

import os
import subprocess
import sys

# Redis connection config (canonical port)
REDIS_PORT = 6380
REDIS_CLI = "redis-cli"

# ACL user config
EXPORTER_USER = "exporter"

# Minimal ACL commands needed by redis_exporter:
# - info: INFO command (server info, clients, memory, stats, replication, cpu, keyspace)
# - config|get: CONFIG GET for configuration metrics
# - client|getname: CLIENT GETNAME for connection identification
# - slowlog|get: SLOWLOG GET for slow query metrics
# - latency|latest: LATENCY LATEST for latency metrics
# - memory|stats: MEMORY STATS for detailed memory breakdown
# - dbsize: DBSIZE for key count
# - command|count: COMMAND COUNT for command stats
# - cluster|info: CLUSTER INFO (no-op on standalone, but exporter checks)
EXPORTER_ACL_COMMANDS = (
    "+info",
    "+config|get",
    "+client|getname",
    "+slowlog|get",
    "+latency|latest",
    "+memory|stats",
    "+dbsize",
    "+command|count",
    "+cluster|info",
    "+ping",
)


def get_exporter_password() -> str:
    """Read exporter password from environment (SOPS-decrypted)."""
    password = os.environ.get("REDIS_EXPORTER_PASSWORD", "")
    if not password or password == "CHANGE_ME_VIA_SOPS":
        print(
            "ERROR: REDIS_EXPORTER_PASSWORD not set or is placeholder.",
            file=sys.stderr,
        )
        print(
            "Usage: source <(sops -d monitoring/.env.enc | grep REDIS_EXPORTER_PASSWORD)",
            file=sys.stderr,
        )
        print(
            "  then: python3 monitoring/redis-exporter/setup_redis_exporter_acl.py",
            file=sys.stderr,
        )
        sys.exit(1)
    return password


def run_redis_cli(args: list[str]) -> str:
    """Execute redis-cli command and return output."""
    cmd = [REDIS_CLI, "-p", str(REDIS_PORT), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        print(f"redis-cli error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def setup_acl() -> None:
    """Create the exporter ACL user with minimal permissions."""
    password = get_exporter_password()

    # Build ACL command string
    acl_commands = " ".join(EXPORTER_ACL_COMMANDS)
    acl_rule = f"on >{password} ~* {acl_commands}"

    # Check if user already exists
    existing_users = run_redis_cli(["ACL", "LIST"])
    user_exists = any(
        line.startswith(f"user {EXPORTER_USER}")
        for line in existing_users.splitlines()
    )

    if user_exists:
        print(f"ACL user '{EXPORTER_USER}' already exists, updating...")
        # Delete and recreate for clean state
        run_redis_cli(["ACL", "DELUSER", EXPORTER_USER])

    # Create the ACL user
    result = run_redis_cli(["ACL", "SETUSER", EXPORTER_USER, *acl_rule.split()])
    print(f"ACL SETUSER result: {result}")

    # Verify the user was created
    acl_list = run_redis_cli(["ACL", "LIST"])
    exporter_line = next(
        (
            line
            for line in acl_list.splitlines()
            if line.startswith(f"user {EXPORTER_USER}")
        ),
        None,
    )

    if exporter_line:
        print(f"SUCCESS: ACL user '{EXPORTER_USER}' created.")
        print(f"ACL entry: {exporter_line}")
    else:
        print(f"FAIL: ACL user '{EXPORTER_USER}' not found in ACL LIST.", file=sys.stderr)
        sys.exit(1)

    # Verify no overly-broad permissions
    if "+@all" in (exporter_line or ""):
        print("FAIL: ACL has +@all — overly permissive!", file=sys.stderr)
        sys.exit(1)

    print("ACL verification PASS: minimal read-only permissions granted.")


if __name__ == "__main__":
    setup_acl()
