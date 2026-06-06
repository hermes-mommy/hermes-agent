"""P6-002 / P6-003 — LLM Router cost tracking, pricing, SSE strip, fail-closed.

Covers:
 - Successful cost recording (CostTracker.record_cost called with correct args).
 - Cost tracking failure raises ``RuntimeError("LLM cost tracking failed")``.
 - Cost failure is **not** swallowed by provider fallback chain.
 - Pricing constants (PRICING dict) match Phase 6 values.
 - SSE strip: ``data: [DONE]``, ``data:[DONE]``, no-strip for normal JSON.
 - Primary model is ``ds/deepseek-v4-flash`` via localhost 9Router.
 - Provider-fallback chain still works for HTTP/JSON errors.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Module under test
from src.core.services.llm_router import (
    LLMRouter,
    ModelConfig,
    MODELS,
    PRICING,
    TaskType,
    _strip_sse_done,
)

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def mock_cost_tracker() -> MagicMock:
    """Return a fully-mocked CostTracker with a synchronous `record_cost`."""
    mock = MagicMock()
    mock.record_cost = MagicMock()
    return mock


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Return a mock ``httpx.AsyncClient``.

    The caller sets ``post.return_value`` on the returned mock.
    """
    mock = AsyncMock(spec=httpx.AsyncClient)
    return mock


def _make_success_response(
    text: str = (
        '{"id":"r1","choices":[{"message":{"content":"ok"}}],'
        '"usage":{"prompt_tokens":42,"completion_tokens":7,"total_tokens":49}}'
    ),
) -> MagicMock:
    """Build a mock ``httpx.Response`` with a 200 status and given text."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


# =========================================================================
# 1. Successful cost recording
# =========================================================================


class TestCostRecording:
    """``CostTracker.record_cost`` is called with correct args."""

    @pytest.mark.asyncio
    async def test_record_cost_called_with_model_token_counts(self, mock_cost_tracker: MagicMock) -> None:
        """After a successful HTTP response the router calls ``record_cost`` with parsed tokens."""
        router = LLMRouter(cost_tracker=mock_cost_tracker)
        router.client = httpx.AsyncClient()  # replaced below

        mock_resp = _make_success_response(
            '{"id":"r1","choices":[{}],"usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30}}',
        )

        with patch.object(router, "client") as mock_cli:
            mock_cli.post = AsyncMock(return_value=mock_resp)

            result = await router.chat([{"role": "user", "content": "hi"}])

        usage = result.get("usage", {})
        assert isinstance(usage, dict)
        assert usage.get("prompt_tokens") == 10
        assert usage.get("completion_tokens") == 20

        mock_cost_tracker.record_cost.assert_called_once_with(
            model="ds/deepseek-v4-flash",
            input_tokens=10,
            output_tokens=20,
            cost_per_1k_input=0.00014,
            cost_per_1k_output=0.00028,
        )

    @pytest.mark.asyncio
    async def test_record_cost_defaults_missing_usage(self, mock_cost_tracker: MagicMock) -> None:
        """When ``usage`` is missing entirely, tokens default to 0."""
        router = LLMRouter(cost_tracker=mock_cost_tracker)
        mock_resp = _make_success_response('{"id":"r1","choices":[{}]}')  # no usage key

        with patch.object(router, "client") as mock_cli:
            mock_cli.post = AsyncMock(return_value=mock_resp)

            _ = await router.chat([{"role": "user", "content": "hi"}])

        mock_cost_tracker.record_cost.assert_called_once_with(
            model="ds/deepseek-v4-flash",
            input_tokens=0,
            output_tokens=0,
            cost_per_1k_input=0.00014,
            cost_per_1k_output=0.00028,
        )

    @pytest.mark.asyncio
    async def test_record_cost_defaults_null_usage_fields(self, mock_cost_tracker: MagicMock) -> None:
        """When ``usage.prompt_tokens`` is null, defaults to 0."""
        router = LLMRouter(cost_tracker=mock_cost_tracker)
        # usage present but individual fields are null
        mock_resp = _make_success_response(
            '{"id":"r1","choices":[{}],"usage":{"prompt_tokens":null,"completion_tokens":null}}',
        )

        with patch.object(router, "client") as mock_cli:
            mock_cli.post = AsyncMock(return_value=mock_resp)

            _ = await router.chat([{"role": "user", "content": "hi"}])

        mock_cost_tracker.record_cost.assert_called_once_with(
            model="ds/deepseek-v4-flash",
            input_tokens=0,
            output_tokens=0,
            cost_per_1k_input=0.00014,
            cost_per_1k_output=0.00028,
        )


# =========================================================================
# 2. Cost tracking failure → fail-closed
# =========================================================================


class TestCostTrackingFailClosed:
    """A cost-tracking error must raise ``RuntimeError("LLM cost tracking failed")``
    and must NOT be caught by the provider-fallback chain."""

    @pytest.mark.asyncio
    async def test_cost_failure_raises_runtime_error(self, mock_cost_tracker: MagicMock) -> None:
        """When ``record_cost`` raises, the router re-raises as RuntimeError with exact message."""
        mock_cost_tracker.record_cost.side_effect = RuntimeError("Redis unreachable")

        router = LLMRouter(cost_tracker=mock_cost_tracker)
        mock_resp = _make_success_response()

        with (
            patch.object(router, "client") as mock_cli,
            pytest.raises(RuntimeError) as exc_info,
        ):
            mock_cli.post = AsyncMock(return_value=mock_resp)
            _ = await router.chat([{"role": "user", "content": "hi"}])

        assert str(exc_info.value) == "LLM cost tracking failed"

    @pytest.mark.asyncio
    async def test_cost_failure_not_swallowed_by_fallback(self, mock_cost_tracker: MagicMock) -> None:
        """A cost-tracking error must NOT trigger fallback to the next provider.

        This test verifies that only one HTTP POST is made (to the primary),
        and the error re-raises immediately without attempting a fallback.
        """
        mock_cost_tracker.record_cost.side_effect = RuntimeError("Redis unreachable")

        router = LLMRouter(cost_tracker=mock_cost_tracker)
        mock_resp = _make_success_response()

        with (
            patch.object(router, "client") as mock_cli,
            pytest.raises(RuntimeError) as exc_info,
        ):
            mock_cli.post = AsyncMock(return_value=mock_resp)
            _ = await router.chat([{"role": "user", "content": "hi"}])

        assert str(exc_info.value) == "LLM cost tracking failed"
        # Exactly one HTTP attempt — no fallback
        assert mock_cli.post.call_count == 1


# =========================================================================
# 3. Pricing constants
# =========================================================================


class TestPricingConstants:
    """PRICING dict must match Phase 6 values per planner."""

    def test_cx_gpt_5_5_pricing(self) -> None:
        assert "cx/gpt-5.5" in PRICING
        assert PRICING["cx/gpt-5.5"]["input_per_1k"] == 0.005
        assert PRICING["cx/gpt-5.5"]["output_per_1k"] == 0.03

    def test_ds_deepseek_v4_flash_pricing(self) -> None:
        assert "ds/deepseek-v4-flash" in PRICING
        assert PRICING["ds/deepseek-v4-flash"]["input_per_1k"] == 0.00014
        assert PRICING["ds/deepseek-v4-flash"]["output_per_1k"] == 0.00028

    def test_guinevere_pricing(self) -> None:
        assert "guinevere" in PRICING
        assert PRICING["guinevere"]["input_per_1k"] == 0.00014
        assert PRICING["guinevere"]["output_per_1k"] == 0.00028


# =========================================================================
# 4. SSE strip variants
# =========================================================================


class TestSseStrip:
    """``_strip_sse_done`` must handle both ``data: [DONE]`` and ``data:[DONE]``."""

    def test_strips_data_space_done(self) -> None:
        raw = '{"id":"r1"}\ndata: [DONE]'
        assert _strip_sse_done(raw) == '{"id":"r1"}'

    def test_strips_data_no_space_done(self) -> None:
        raw = '{"id":"r1"}\ndata:[DONE]'
        assert _strip_sse_done(raw) == '{"id":"r1"}'

    def test_strips_trailing_whitespace(self) -> None:
        """Strips trailing whitespace after the marker is removed."""
        raw = '{"id":"r1"}\ndata: [DONE]  \t  '
        assert _strip_sse_done(raw) == '{"id":"r1"}'

    def test_leaves_normal_json_untouched(self) -> None:
        """A valid JSON response without SSE marker must not be modified."""
        raw = '{"id":"r1","choices":[{"text":"hello"}]}'
        assert _strip_sse_done(raw) == raw

    def test_strips_marker_mid_content_not_possible(self) -> None:
        """The regex is anchored to end-of-string, so ``[DONE]`` mid-content is safe."""
        raw = '{"text":"data: [DONE] here"}'
        assert _strip_sse_done(raw) == raw


# =========================================================================
# 5. Primary model is DeepSeek via localhost 9Router
# =========================================================================


class TestPrimaryModel:
    """``CORE_REASONING`` must use ``ds/deepseek-v4-flash`` as Phase 6 primary."""

    def test_core_reasoning_is_deepseek(self) -> None:
        cfg = MODELS[TaskType.CORE_REASONING]
        assert cfg.name == "ds/deepseek-v4-flash"
        assert cfg.base_url == "http://localhost:20128/v1"

    def test_core_reasoning_has_deepseek_pricing(self) -> None:
        cfg = MODELS[TaskType.CORE_REASONING]
        assert cfg.cost_per_1k_input == 0.00014
        assert cfg.cost_per_1k_output == 0.00028

    def test_all_routes_through_localhost_9router(self) -> None:
        """Every model must use ``http://localhost:20128/v1`` — no direct providers."""
        for task_type in TaskType:
            cfg = MODELS[task_type]
            assert cfg.base_url == "http://localhost:20128/v1", (
                f"{task_type.value} uses {cfg.base_url} instead of localhost:20128"
            )


# =========================================================================
# 6. Provider-fallback chain preserved for HTTP errors
# =========================================================================


class TestProviderFallback:
    """HTTP/JSON provider errors still trigger fallback; cost failure is the
    **only** condition that bypasses the fallback chain."""

    @pytest.mark.asyncio
    async def test_http_error_falls_back(self, mock_cost_tracker: MagicMock) -> None:
        """When the primary returns HTTP 500, the router should fall back to SUB_AGENT."""
        router = LLMRouter(cost_tracker=mock_cost_tracker)

        http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

        call_counter = [0]

        def _fail_then_succeed(*_args: object, **_kwargs: object) -> MagicMock:
            # First call: fail → causes fallback; second call: succeed
            call_counter[0] += 1
            if call_counter[0] == 1:
                raise http_error
            return _make_success_response(
                '{"id":"r2","choices":[{}],"usage":{"prompt_tokens":1,"completion_tokens":2}}',
            )

        with patch.object(router, "client") as mock_cli:
            mock_cli.post = AsyncMock(side_effect=_fail_then_succeed)

            result = await router.chat([{"role": "user", "content": "hi"}])

        # Fallback to SUB_AGENT → result should be from the second call
        assert result["id"] == "r2"
        assert mock_cli.post.call_count == 2

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises(self, mock_cost_tracker: MagicMock) -> None:
        """When every provider in the chain fails, the router raises ``RuntimeError``."""
        router = LLMRouter(cost_tracker=mock_cost_tracker)
        http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

        with (
            patch.object(router, "client") as mock_cli,
            pytest.raises(RuntimeError) as exc_info,
        ):
            mock_cli.post = AsyncMock(side_effect=http_error)
            _ = await router.chat([{"role": "user", "content": "hi"}])

        assert "All LLM providers failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sub_agent_has_two_tier_fallback(self, mock_cost_tracker: MagicMock) -> None:
        """When ``task_type=SUB_AGENT``, the chain is
        SUB_AGENT → FALLBACK (no CORE_REASONING)."""
        router = LLMRouter(cost_tracker=mock_cost_tracker)
        http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

        call_counter = [0]

        def _fail_then_succeed(*_args: object, **_kwargs: object) -> MagicMock:
            call_counter[0] += 1
            if call_counter[0] <= 1:
                raise http_error
            return _make_success_response(
                '{"id":"r3","choices":[{}],"usage":{"prompt_tokens":0,"completion_tokens":0}}',
            )

        with patch.object(router, "client") as mock_cli:
            mock_cli.post = AsyncMock(side_effect=_fail_then_succeed)

            result = await router.chat(
                [{"role": "user", "content": "hi"}],
                task_type=TaskType.SUB_AGENT,
            )

        assert result["id"] == "r3"
        # SUB_AGENT → fails, FALLBACK → succeeds → 2 calls total
        assert mock_cli.post.call_count == 2


# =========================================================================
# 7. ModelConfig data class sanity
# =========================================================================


class TestModelConfigSanity:
    """Minimal sanity for the ``ModelConfig`` dataclass."""

    def test_model_config_construction(self) -> None:
        cfg = ModelConfig("test-model", "http://localhost:20128/v1", 512, 0.3, 0.1, 0.2)
        assert cfg.name == "test-model"
        assert cfg.base_url == "http://localhost:20128/v1"
        assert cfg.max_tokens == 512
        assert cfg.temperature == 0.3
        assert cfg.cost_per_1k_input == 0.1
        assert cfg.cost_per_1k_output == 0.2
