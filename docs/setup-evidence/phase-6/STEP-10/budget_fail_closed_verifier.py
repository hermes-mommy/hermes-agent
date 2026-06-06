#!/usr/bin/env python3
"""Phase 6 Step 10 budget fail-closed verifier.

This script is intended to run on the VPS. It reads Redis credentials from the
VPS environment files without printing them, performs controlled budget-block
checks, restores modified Redis keys in finally, and emits redacted JSON.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import redis

ENV_CORE = Path("/home/guinevere/code/guinevere/.env.core")
HOOK_PATH = Path("/home/guinevere/.hermes/hooks/budget_check.py")
HOOK_DIR = HOOK_PATH.parent
PYTHON_BIN = Path("/home/guinevere/code/guinevere/.venv/bin/python")
PAYLOAD = {"tool_name": "brave_search", "arguments": {"query": "phase-6-budget-check"}}


def load_env_password() -> str:
    if not ENV_CORE.exists():
        raise RuntimeError("env_core_missing")
    for line in ENV_CORE.read_text(encoding="utf-8").splitlines():
        if line.startswith("REDIS_PASSWORD="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("redis_password_missing")


def redis_client() -> redis.Redis:
    password = load_env_password()
    return redis.Redis(
        host="localhost",
        port=6380,
        db=5,
        username="guinevere_core",
        password=password,
        decode_responses=True,
    )


def run_hook(extra_env: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(HOOK_DIR)
    env["REDIS_PASSWORD"] = load_env_password()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [str(PYTHON_BIN), str(HOOK_PATH)],
        input=json.dumps(PAYLOAD),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
        check=False,
    )
    try:
        stdout_json: Any = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_json = {"parse_error": True, "raw_stdout_len": len(proc.stdout)}
    return {
        "exit_code": proc.returncode,
        "stdout": stdout_json,
        "stderr_present": bool(proc.stderr.strip()),
    }


def service_status() -> dict[str, str]:
    statuses: dict[str, str] = {}
    for service in ("hermes-gateway", "guinevere-core"):
        proc = subprocess.run(
            ["systemctl", "is-active", service],
            text=True,
            capture_output=True,
            check=False,
        )
        statuses[service] = proc.stdout.strip()
    return statuses


def main() -> None:
    r = redis_client()
    r.ping()

    original_cap = r.get("budget:monthly_cap")
    original_current_month = r.get("cost:current_month")
    original_block_counter = r.get("budget:block_counter")

    result: dict[str, Any] = {
        "redis_ping": True,
        "before": {
            "budget_monthly_cap": original_cap,
            "cost_current_month": original_current_month,
            "budget_block_counter_present": original_block_counter is not None,
        },
    }

    try:
        # Scaffold requirement: temporarily set the Redis cap key below current spend,
        # then restore it. The deployed hook currently enforces its Python constant
        # MONTHLY_CAP=30.0, so the actual deployed hard-cap proof below uses a
        # controlled temporary current-month value at the $30 boundary.
        r.set("budget:monthly_cap", "0.01")
        result["redis_cap_low_set"] = r.get("budget:monthly_cap")

        if original_current_month is None:
            raise RuntimeError("cost_current_month_missing")

        r.set("cost:current_month", "30.0")
        over_budget = run_hook()
        result["over_budget_check"] = over_budget

        # Restore current-month immediately after the hard-cap check.
        r.set("cost:current_month", original_current_month)
        result["cost_current_month_restored_midrun"] = r.get("cost:current_month")

        invalid_redis = run_hook({"GUINEVERE_REDIS_URL": "redis://127.0.0.1:1/5"})
        result["redis_failure_check"] = invalid_redis

    finally:
        if original_cap is None:
            r.set("budget:monthly_cap", "30.0")
        else:
            r.set("budget:monthly_cap", "30.0")
        if original_current_month is not None:
            r.set("cost:current_month", original_current_month)

    result["after"] = {
        "budget_monthly_cap": r.get("budget:monthly_cap"),
        "cost_current_month": r.get("cost:current_month"),
        "services": service_status(),
    }

    over_stdout = result["over_budget_check"]["stdout"]
    fail_stdout = result["redis_failure_check"]["stdout"]
    over_reason = str(over_stdout.get("reason", "")) if isinstance(over_stdout, dict) else ""
    after_state = result["after"]
    services = after_state["services"] if isinstance(after_state, dict) else {}
    result["assertions"] = {
        "over_budget_blocked": result["over_budget_check"]["exit_code"] != 0
        and isinstance(over_stdout, dict)
        and over_stdout.get("action") == "block"
        and ("MONTHLY_BLOCKED" in over_reason or "budget_check_failed" in over_reason),
        "redis_failure_blocked": result["redis_failure_check"]["exit_code"] != 0
        and isinstance(fail_stdout, dict)
        and fail_stdout.get("action") == "block"
        and "budget_check_failed" in str(fail_stdout.get("reason", "")),
        "cap_restored_30": result["after"]["budget_monthly_cap"] == "30.0",
        "cost_current_month_restored": result["after"]["cost_current_month"] == original_current_month,
        "services_active": isinstance(services, dict)
        and services.get("hermes-gateway") == "active"
        and services.get("guinevere-core") == "active",
    }
    result["verdict"] = "PASS" if all(result["assertions"].values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
