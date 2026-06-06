"""P6-007 — LLM Routing Metrics (Phase 6, Step 7).

Verifies that all four required Prometheus metric families exist, produce
the expected names/labels, and can be incremented/observed correctly.

Required families:
  - hermes_llm_calls_total{model,status}
  - hermes_llm_latency_seconds
  - hermes_llm_cost_usd_total
  - hermes_fallback_activations_total
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from prometheus_client import generate_latest
from prometheus_client.parser import text_string_to_metric_families

# Module under test
from src.core.services.llm_metrics import (
    observe_call,
    observe_cost,
    observe_fallback,
    observe_latency,
    start_llm_metrics_server,
)

# =========================================================================
# 1. Metric family names and labels
# =========================================================================


class TestMetricFamilyDefinitions:
    """Verify that all four metric families exist with correct names."""

    def test_llm_calls_total_definition(self) -> None:
        output = generate_latest().decode("utf-8")
        assert "# HELP hermes_llm_calls_total" in output
        assert "# TYPE hermes_llm_calls_total counter" in output

    def test_llm_latency_seconds_definition(self) -> None:
        output = generate_latest().decode("utf-8")
        assert "# HELP hermes_llm_latency_seconds" in output
        assert "# TYPE hermes_llm_latency_seconds histogram" in output

    def test_llm_cost_usd_total_definition(self) -> None:
        output = generate_latest().decode("utf-8")
        assert "# HELP hermes_llm_cost_usd_total" in output
        assert "# TYPE hermes_llm_cost_usd_total counter" in output

    def test_fallback_activations_total_definition(self) -> None:
        output = generate_latest().decode("utf-8")
        assert "# HELP hermes_fallback_activations_total" in output
        assert "# TYPE hermes_fallback_activations_total counter" in output


# =========================================================================
# 2. Observer functions produce expected metric output
# =========================================================================


class TestObserversProduceOutput:
    """Call each observer and verify the metric name appears in ``generate_latest()``."""

    def test_observe_call_success(self) -> None:
        observe_call("ds/deepseek-v4-flash", "success")
        output = generate_latest().decode("utf-8")
        assert 'hermes_llm_calls_total{model="ds/deepseek-v4-flash",status="success"}' in output

    def test_observe_call_error(self) -> None:
        observe_call("guinevere", "error")
        output = generate_latest().decode("utf-8")
        assert 'hermes_llm_calls_total{model="guinevere",status="error"}' in output

    def test_observe_latency(self) -> None:
        observe_latency("ds/deepseek-v4-flash", 1.5)
        output = generate_latest().decode("utf-8")
        # Histogram shows _bucket, _count, _sum, _created suffixes
        assert "hermes_llm_latency_seconds_count" in output

    def test_observe_cost(self) -> None:
        observe_cost("ds/deepseek-v4-flash", 0.00123)
        output = generate_latest().decode("utf-8")
        assert 'hermes_llm_cost_usd_total' in output

    def test_observe_fallback(self) -> None:
        observe_fallback("ds/deepseek-v4-flash", "guinevere")
        output = generate_latest().decode("utf-8")
        assert 'hermes_fallback_activations_total{from_model="ds/deepseek-v4-flash",to_model="guinevere"}' in output


class TestObserverValues:
    """Verify that observer calls actually change metric values."""

    def test_observe_call_increments_counter(self) -> None:
        model = "test-model-a"
        observe_call(model, "success")
        observe_call(model, "success")

        output = generate_latest().decode("utf-8")
        families = list(text_string_to_metric_families(output))

        # Parser returns base name without _total
        calls = [f for f in families if f.name == "hermes_llm_calls"]
        assert len(calls) == 1

        samples = list(calls[0].samples)
        matching = [s for s in samples if s.labels == {"model": model, "status": "success"}]
        assert len(matching) >= 1
        # Sum sample values for this label combination
        observed = sum(s.value for s in matching)
        assert observed >= 2.0

    def test_observe_cost_increments_counter(self) -> None:
        model = "test-model-b"
        observe_cost(model, 0.01)
        observe_cost(model, 0.02)

        output = generate_latest().decode("utf-8")
        families = list(text_string_to_metric_families(output))

        cost_families = [f for f in families if f.name == "hermes_llm_cost_usd"]
        assert len(cost_families) == 1

        samples = list(cost_families[0].samples)
        matching = [s for s in samples if s.labels == {"model": model}]
        assert len(matching) >= 1
        observed = sum(s.value for s in matching)
        assert observed >= 0.03  # 0.01 + 0.02

    def test_observe_fallback_increments_counter(self) -> None:
        observe_fallback("model-a", "model-b")
        observe_fallback("model-a", "model-b")

        output = generate_latest().decode("utf-8")
        families = list(text_string_to_metric_families(output))

        fallback_families = [f for f in families if f.name == "hermes_fallback_activations"]
        assert len(fallback_families) == 1

        samples = list(fallback_families[0].samples)
        matching = [s for s in samples if s.labels == {"from_model": "model-a", "to_model": "model-b"}]
        assert len(matching) >= 1
        observed = sum(s.value for s in matching)
        assert observed >= 2.0


# =========================================================================
# 3. start_llm_metrics_server is idempotent
# =========================================================================


class TestMetricsServer:
    """``start_llm_metrics_server`` is idempotent (safe to call multiple times)."""

    def test_double_start_does_not_raise(self) -> None:
        """Calling ``start_llm_metrics_server`` twice should not raise."""
        start_llm_metrics_server(port=9192)  # different port for test
        start_llm_metrics_server(port=9192)  # second call is no-op


# =========================================================================
# 4. Integration with LLMRouter: metrics are called on success/error/fallback
# =========================================================================


class TestLLMRouterMetricsIntegration:
    """Verify that ``llm_router.chat()`` calls the correct metric observers."""

    @pytest.mark.asyncio
    async def test_success_calls_observe_call_and_latency_and_cost(self) -> None:
        """On success, all three success-path observers are invoked."""
        from src.core.services.llm_router import LLMRouter

        router = LLMRouter(cost_tracker=MagicMock())
        mock_resp_text = (
            '{"id":"r1","choices":[{}],"usage":{"prompt_tokens":10,"completion_tokens":20}}'
        )

        with (
            patch("src.core.services.llm_router.observe_call") as mock_call,
            patch("src.core.services.llm_router.observe_latency") as mock_latency,
            patch("src.core.services.llm_router.observe_cost") as mock_cost,
            patch.object(router, "client") as mock_cli,
        ):
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.text = mock_resp_text
            mock_resp.raise_for_status = MagicMock()
            mock_cli.post = AsyncMock(return_value=mock_resp)

            _ = await router.chat([{"role": "user", "content": "hi"}])

        mock_call.assert_called_once_with("ds/deepseek-v4-flash", "success")
        mock_latency.assert_called_once()
        args, _ = mock_latency.call_args
        assert args[0] == "ds/deepseek-v4-flash"
        assert isinstance(args[1], float)
        mock_cost.assert_called_once()
        cost_args, _ = mock_cost.call_args
        assert cost_args[0] == "ds/deepseek-v4-flash"
        assert cost_args[1] > 0

    @pytest.mark.asyncio
    async def test_failure_calls_observe_call_error(self) -> None:
        """On HTTP error, observe_call is called with status='error'."""
        from src.core.services.llm_router import LLMRouter

        router = LLMRouter(cost_tracker=MagicMock())
        http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

        with (
            patch("src.core.services.llm_router.observe_call") as mock_call,
            patch("src.core.services.llm_router.observe_latency"),
            patch("src.core.services.llm_router.observe_cost"),
            patch("src.core.services.llm_router.observe_fallback"),
            patch.object(router, "client") as mock_cli,
        ):
            mock_cli.post = AsyncMock(side_effect=http_error)

            with pytest.raises(RuntimeError, match="All LLM providers failed"):
                _ = await router.chat([{"role": "user", "content": "hi"}])

        # Each failed attempt should record an error call
        assert mock_call.call_count >= 1
        call_args_list = mock_call.call_args_list
        # At least one error call for the primary model
        error_calls = [
            args for args in call_args_list if args[0][1] == "error"
        ]
        assert len(error_calls) >= 1

    @pytest.mark.asyncio
    async def test_fallback_calls_observe_fallback(self) -> None:
        """When primary fails and fallback succeeds, observe_fallback is called."""
        from src.core.services.llm_router import LLMRouter

        router = LLMRouter(cost_tracker=MagicMock())

        with (
            patch("src.core.services.llm_router.observe_call"),
            patch("src.core.services.llm_router.observe_latency"),
            patch("src.core.services.llm_router.observe_cost"),
            patch("src.core.services.llm_router.observe_fallback") as mock_fallback,
            patch.object(router, "client") as mock_cli,
        ):
            http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

            call_counter = [0]

            def _fail_then_succeed(*_args: object, **_kwargs: object) -> MagicMock:
                call_counter[0] += 1
                if call_counter[0] == 1:
                    raise http_error
                resp = MagicMock(spec=httpx.Response)
                resp.status_code = 200
                resp.text = (
                    '{"id":"r2","choices":[{}],"usage":{"prompt_tokens":1,"completion_tokens":2}}'
                )
                resp.raise_for_status = MagicMock()
                return resp

            mock_cli.post = AsyncMock(side_effect=_fail_then_succeed)

            _ = await router.chat([{"role": "user", "content": "hi"}])

        # Fallback should be recorded at least once
        assert mock_fallback.call_count >= 1
        # The fallback should be from the primary model to a fallback model
        first_call_args = mock_fallback.call_args_list[0][0]
        # CORE_REASONING chain: CORE_REASONING → SUB_AGENT → FALLBACK
        # After CORE_REASONING fails, fallback is from ds/deepseek-v4-flash to ds/deepseek-v4-flash (SUB_AGENT)
        assert first_call_args[0] == "ds/deepseek-v4-flash"
