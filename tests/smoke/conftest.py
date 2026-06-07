# Guinevere smoke tests — conftest.py
"""Shared fixtures for persona smoke tests against local 9Router."""

import json
from pathlib import Path

import pytest
import pytest_asyncio
import httpx

SYSTEM_PROMPT_PATH = Path("/home/guinevere/config/hermes/system-prompt.md")
REPO_SYSTEM_PROMPT_PATH = Path("docs/60-persona/61-SystemPromptMaster_v1.1.md")
NINEROUTER_BASE = "http://localhost:20128/v1"
DEFAULT_SMOKE_MODEL = "ds/deepseek-v4-flash"
PROMPT_MAX_CHARS = 4000


@pytest.fixture(scope="session")
def system_prompt() -> str:
    """Read Guinevere system prompt from deployed config or repo fallback."""
    prompt_path = SYSTEM_PROMPT_PATH if SYSTEM_PROMPT_PATH.exists() else REPO_SYSTEM_PROMPT_PATH
    try:
        raw = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        pytest.fail("System prompt file not found: %s" % prompt_path)
    if len(raw) > PROMPT_MAX_CHARS:
        raw = raw[:PROMPT_MAX_CHARS]
    if len(raw) < 200:
        pytest.fail("System prompt too short after truncation: %d chars" % len(raw))
    return raw


@pytest_asyncio.fixture
async def client():
    """Function-scoped httpx AsyncClient (avoids event-loop closure between tests)."""
    async with httpx.AsyncClient(timeout=90.0) as _client:
        yield _client


def safe_json(resp: httpx.Response) -> dict:
    """Parse JSON from 9Router response, stripping trailing 'data: [DONE]' suffix."""
    text = resp.text.strip()
    # 9Router appends "data: [DONE]" even for non-stream responses
    done_marker = "data: [DONE]"
    if text.endswith(done_marker):
        text = text[: -len(done_marker)].rstrip()
    return json.loads(text)


def extract_content(resp: httpx.Response) -> str:
    """Extract message content from a 9Router chat completion response.

    DeepSeek V4 Flash may return `reasoning_content` alongside `content`.
    If `content` is empty, fall back to `reasoning_content`.
    """
    assert resp.status_code == 200, \
        "Expected 200, got %d: %s" % (resp.status_code, resp.text[:300])
    body = safe_json(resp)
    choices = body.get("choices", [])
    assert len(choices) > 0, \
        "No choices in response: %s" % json.dumps(body)[:200]
    msg = choices[0].get("message", {})
    content = msg.get("content", "")
    if not content:
        # DeepSeek reasoning models put answer in reasoning_content
        content = msg.get("reasoning_content", "")
    return content


@pytest.fixture
def chat(client, system_prompt):
    """Return a helper that sends a single-turn message to 9Router.
    Returns the content string (not raw httpx.Response).
    """

    async def _chat(user_message: str, *, model: str = DEFAULT_SMOKE_MODEL, max_tokens: int = 1024) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        resp = await client.post(
            NINEROUTER_BASE + "/chat/completions",
            json=payload,
        )
        return extract_content(resp)

    return _chat