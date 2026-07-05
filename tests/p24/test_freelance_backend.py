"""P6 Freelance backend TDD tests — all actions DEFERRED.

Fiverr: no public API. Upwork: ToS-banned for scraping. Freelancer.com: stale SDK.
Every dispatch returns {ok: False, deferred: True, error: "DEFERRED: ..."}.
No live external API calls. No mocks needed (all paths are pure-logic deferred).
"""
from __future__ import annotations

import asyncio
import pytest

from guinevere.tools.backends.freelance import FreelanceBackend


@pytest.fixture
def backend():
    return FreelanceBackend()


# ---------------------------------------------------------------------------
# is_available / name / actions catalogue
# ---------------------------------------------------------------------------


def test_backend_name(backend):
    assert backend.name == "freelance"


def test_actions_count(backend):
    """8 actions in the catalogue."""
    assert len(backend.actions()) == 8


def test_actions_have_deferred_in_description(backend):
    """Every action description should note DEFERRED."""
    for action in backend.actions():
        assert "DEFERRED" in action.description, (
            f"action {action.name!r} description missing DEFERRED marker"
        )


def test_is_available(backend):
    """Backend is structurally available (even though all actions are deferred)."""
    assert backend.is_available() is True


# ---------------------------------------------------------------------------
# dispatch: every action returns deferred=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_jobs_deferred(backend):
    result = await backend.dispatch("list_jobs", {"platform": "upwork"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]
    assert "upwork" in result["error"].lower() or "Upwork" in result["error"]


@pytest.mark.asyncio
async def test_list_jobs_deferred_fiverr(backend):
    result = await backend.dispatch("list_jobs", {"platform": "fiverr"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]


@pytest.mark.asyncio
async def test_get_messages_deferred(backend):
    result = await backend.dispatch("get_messages", {"platform": "upwork"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]


@pytest.mark.asyncio
async def test_send_message_deferred(backend):
    result = await backend.dispatch("send_message", {"platform": "fiverr", "to": "seller"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]


@pytest.mark.asyncio
async def test_submit_proposal_deferred(backend):
    result = await backend.dispatch("submit_proposal", {"job_id": "123"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]
    assert "upwork" in result["error"].lower() or "Upwork" in result["error"]


@pytest.mark.asyncio
async def test_place_bid_deferred(backend):
    result = await backend.dispatch("place_bid", {"project_id": "456", "amount": 100})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]
    assert "freelancer" in result["error"].lower() or "Freelancer" in result["error"]


@pytest.mark.asyncio
async def test_accept_contract_deferred(backend):
    result = await backend.dispatch("accept_contract", {"contract_id": "c-1"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]


@pytest.mark.asyncio
async def test_submit_milestone_deferred(backend):
    result = await backend.dispatch("submit_milestone", {"milestone_id": "m-1"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]


@pytest.mark.asyncio
async def test_submit_delivery_deferred(backend):
    result = await backend.dispatch("submit_delivery", {"order_id": "o-1"})
    assert result["ok"] is False
    assert result["deferred"] is True
    assert "DEFERRED" in result["error"]
    assert "fiverr" in result["error"].lower() or "Fiverr" in result["error"]


# ---------------------------------------------------------------------------
# dispatch: unknown action (fail-soft)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_action_fail_soft(backend):
    result = await backend.dispatch("nonexistent_action", {})
    assert result["ok"] is False
    assert "error" in result
    # dispatch must never raise (fail-soft contract)


# ---------------------------------------------------------------------------
# dispatch: never raises (fail-soft contract)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_never_raises(backend):
    """Every call must return a dict, never raise to caller."""
    for action in backend.actions():
        result = await backend.dispatch(action.name, {})
        assert isinstance(result, dict), f"{action.name} did not return dict"
        assert "ok" in result, f"{action.name} missing 'ok' key"
