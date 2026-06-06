#!/usr/bin/env python3
"""100-prompt VPS integration test for Phase 6 Step 9.

Runs 100 prompts through the deployed LLMRouter, routes all calls through
http://localhost:20128/v1, and records success/failure/token-usage metrics.

Usage:
    cd /home/guinevere/code/guinevere
    /home/guinevere/code/guinevere/.venv/bin/python \\
        /tmp/phase6_100_prompt_test.py

Output: JSON lines to stdout, summary block at end.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback

# Add project root so we can import src.*
PROJECT_ROOT = "/home/guinevere/code/guinevere"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Must set the env var before importing src.core.services.cost_tracker
# because CostTracker reads REDIS_PASSWORD at import/init time.
# Use force-set (not setdefault) to ensure the value propagates even if
# the parent shell mangled the variable assignment.
_api_key = os.environ.get("NINEROUTER_API_KEY") or os.environ.get("GUINEVERE_9ROUTER_API_KEY") or ""
os.environ["NINEROUTER_API_KEY"] = _api_key
_rp = os.environ.get("REDIS_PASSWORD") or "[REDACTED_REDIS_PASSWORD]"
os.environ["REDIS_PASSWORD"] = _rp

from src.core.services.llm_router import LLMRouter, TaskType  # noqa: E402

SAMPLE_PROMPTS = [
    "Reply with exactly: prompt-ok-{n}",
    "What is 2+2? Reply with just the number.",
    "Say hello in one word.",
    "What color is the sky? One word answer.",
    "Is water wet? Reply yes or no.",
    "What is 5*3? Just the number.",
    "Name a primary color. One word.",
    "What day comes after Monday? One word.",
    "Is the sun hot? Reply yes or no.",
    "What is the capital of France? One word.",
]


async def run_one_prompt(
    router: LLMRouter,
    prompt: str,
    index: int,
) -> dict:
    """Run a single prompt and return result metadata."""
    messages = [{"role": "user", "content": prompt.format(n=index)}]
    start = time.monotonic()
    try:
        result = await router.chat(
            messages=messages,
            task_type=TaskType.CORE_REASONING,
        )
        elapsed = time.monotonic() - start

        # Extract usage info
        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))

        # Get content from the response
        choices = result.get("choices", [])
        content = ""
        if isinstance(choices, list) and len(choices) > 0:
            choice = choices[0]
            if isinstance(choice, dict):
                msg = choice.get("message", {})
                if isinstance(msg, dict):
                    content = str(msg.get("content", ""))

        # Verify no SSE artifacts in the parsed output
        has_sse_artifact = False
        if "[DONE]" in content:
            has_sse_artifact = True

        model_used = result.get("model", "unknown")
        if isinstance(model_used, dict):
            model_used = str(model_used.get("id", "unknown"))

        return {
            "index": index,
            "status": "success",
            "model": model_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "content_length": len(content),
            "content_preview": content[:100] if content else "",
            "latency_seconds": round(elapsed, 3),
            "has_sse_artifact": has_sse_artifact,
            "error": None,
        }
    except Exception as exc:
        elapsed = time.monotonic() - start
        return {
            "index": index,
            "status": "error",
            "model": "unknown",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "content_length": 0,
            "content_preview": "",
            "latency_seconds": round(elapsed, 3),
            "has_sse_artifact": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


async def main():
    print("[phase6-step9] Starting 100-prompt VPS integration test")
    print(f"[phase6-step9] Python: {sys.version}")
    print(f"[phase6-step9] Project root: {PROJECT_ROOT}")
    print(f"[phase6-step9] Time: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    print(f"[phase6-step9] NINEROUTER_API_KEY set: {bool(os.environ.get('NINEROUTER_API_KEY'))}")
    print(f"[phase6-step9] REDIS_PASSWORD set: {bool(os.environ.get('REDIS_PASSWORD'))}")
    print()

    router = LLMRouter()
    print("[phase6-step9] LLMRouter instantiated OK")
    print()

    # Run 100 prompts (10 prompts repeated 10 times each with varying index)
    tasks = []
    for i in range(100):
        prompt = SAMPLE_PROMPTS[i % len(SAMPLE_PROMPTS)]
        tasks.append(run_one_prompt(router, prompt, i))

    results = await asyncio.gather(*tasks)

    # Close the router client
    await router.close()
    print("[phase6-step9] Router client closed")

    # --- Summary ---
    successes = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]

    total_prompt_tokens = sum(r["prompt_tokens"] for r in successes)
    total_completion_tokens = sum(r["completion_tokens"] for r in successes)
    total_latency = sum(r["latency_seconds"] for r in successes)
    total_sse_artifacts = sum(1 for r in successes if r["has_sse_artifact"])

    # Model distribution
    model_counts = {}
    for r in successes:
        m = r["model"]
        model_counts[m] = model_counts.get(m, 0) + 1

    print()
    print("=" * 70)
    print("  PHASE 6 STEP 9 100-PROMPT INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"  Total prompts:     {len(results)}")
    print(f"  Successes:         {len(successes)}")
    print(f"  Failures:          {len(errors)}")
    print(f"  Success rate:      {len(successes)}/{len(results)} ({100 * len(successes) // len(results)}%)")
    print(f"  SSE artifacts:     {total_sse_artifacts}")
    print(f"  Total prompt tokens:    {total_prompt_tokens}")
    print(f"  Total completion tokens: {total_completion_tokens}")
    print(f"  Total latency (s):      {round(total_latency, 3)}")
    print(f"  Avg latency (s):        {round(total_latency / len(successes), 3) if successes else 'N/A'}")
    print(f"  Models used:            {model_counts}")
    print()

    if errors:
        print("  --- ERROR DETAILS ---")
        for e in errors[:10]:
            print(f"    [{e['index']}] {e['error']}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more errors")
        print()

    # Output full JSON results for verification
    print()
    print("=" * 70)
    print("  RAW RESULT (JSON)")
    print("=" * 70)
    print(json.dumps({"results": results, "summary": {
        "total": len(results),
        "successes": len(successes),
        "failures": len(errors),
        "success_rate_pct": round(100 * len(successes) / len(results), 1),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_latency_seconds": round(total_latency, 3),
        "avg_latency_seconds": round(total_latency / len(successes), 3) if successes else 0,
        "sse_artifacts": total_sse_artifacts,
        "models": model_counts,
    }}, indent=2))

    # Exit code
    if len(errors) > 5:
        print("[phase6-step9] FAIL: More than 5 errors", file=sys.stderr)
        sys.exit(1)
    print("[phase6-step9] PASS: 100-prompt test completed")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
