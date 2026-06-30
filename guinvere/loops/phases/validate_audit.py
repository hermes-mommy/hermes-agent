"""Phase 5 — Validate & Audit: verify sub-agent outputs against contracts.

Produces a ``validation-report.md`` artifact with LLM-powered verification
results covering acceptance criteria, security boundaries, integration
compatibility, and performance impact.

Class hierarchy
---------------
:class:`ValidateAuditHandler` extends :class:`BasePhaseHandler` and
implements the ``_execute()`` contract. The module-level ``run()``
function provides backward compatibility with the ``PHASE_REGISTRY`` in
``__init__.py``.

Fallback behaviour
------------------
When the LLM router is *not* injected (``_llm_router is None``), the
handler returns a static template with a clear ``_Audit pending — LLM
router not available._`` marker. This ensures the loop never crashes
during development or testing.
"""

from __future__ import annotations

import datetime as _dt

import structlog

from guinvere.loops.context import LoopContext
from guinvere.loops.phases.base import BasePhaseHandler, PhaseArtifact, TokenUsage
from guinvere.loops.prompts import build_system_prompt

logger = structlog.get_logger()


class ValidateAuditHandler(BasePhaseHandler):
    """Phase 5 — Validate & Audit handler.

    Uses the LLM router (injected via the parent constructor) to produce
    a comprehensive audit report covering:

    1. Acceptance criteria verification — pass/fail per criterion
    2. Security boundary check — secrets, type suppression, bare excepts
    3. Integration compatibility — import resolution, circular deps
    4. Performance impact assessment
    5. Overall verdict — PASS / NEEDS REVIEW / FAIL

    When ``_llm_router`` is ``None`` the handler falls back to a safe
    static template (no LLM call).
    """

    async def _execute(self, loop_id: str, task: str, goal: str) -> PhaseArtifact:
        """Produce a validation and audit artifact.

        Parameters
        ----------
        loop_id:
            Unique 12-character hex loop identifier.
        task:
            Human-readable task description.
        goal:
            Optional goal string used for plan-generation context.

        Returns
        -------
        PhaseArtifact
            Markdown audit report with token usage and metadata.
        """
        # ── Fallback: no LLM router available ───────────────────────
        if self._llm_router is None:
            logger.warning(
                "validate_audit_handler.no_llm_router",
                loop_id=loop_id,
                fallback="template",
            )
            content = (
                f"# Validation & Audit Report\n\n"
                f"**Loop:** `{loop_id}`\n"
                f"**Task:** {task}\n\n"
                f"_Audit pending — LLM router not available._"
            )
            return PhaseArtifact(
                content=content,
                phase=5,
                token_usage=None,
                metadata={"fallback": True},
            )

        # ── Build system prompt ────────────────────────────────────
        ctx = LoopContext(
            loop_id=loop_id,
            task=task,
            goal=goal,
            phase=5,
            created_at=_dt.datetime.now(_dt.timezone.utc),
        )
        system_prompt = build_system_prompt(ctx=ctx)

        # ── User message — shapes the audit report structure ───────
        user_msg = (
            "Validate all artifacts produced in previous phases and run "
            "audit checks.\n\n"
            f"**Task:** {task}\n\n"
            f"**Goal:** {goal}\n\n"
            "Produce an audit report covering:\n"
            "1. **Acceptance criteria verification** — pass/fail per "
            "criterion with evidence\n"
            "2. **Security boundary check** — no secrets in artifacts, "
            "no type suppression (``# type: ignore``, ``as any``), no "
            "bare ``except:``\n"
            "3. **Integration compatibility** — imports resolve, no "
            "circular dependencies, interface contracts satisfied\n"
            "4. **Performance impact assessment** — latency, throughput, "
            "resource usage estimates\n"
            "5. **Overall verdict** — PASS / NEEDS REVIEW / FAIL with "
            "rationale"
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        result = await self._call_llm(
            messages,
            task_type="CORE_REASONING",
            max_tokens=4096,
            loop_id=loop_id,
        )

        content: str = result.get("content", "")
        usage_raw: dict = result.get("usage", {})

        token_usage = TokenUsage(
            model=result.get("model", "unknown"),
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
            cost_usd=0.0,
        )

        logger.info(
            "validate_audit_handler.llm_complete",
            loop_id=loop_id,
            model=token_usage.model,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
            content_length=len(content),
        )

        return PhaseArtifact(
            content=content,
            phase=5,
            token_usage=token_usage,
            metadata={
                "model": token_usage.model,
                "input_tokens": token_usage.input_tokens,
                "output_tokens": token_usage.output_tokens,
                "total_tokens": token_usage.total_tokens,
            },
        )


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Backward-compatible entry point for the phase registry.

    Constructs a :class:`ValidateAuditHandler` with *no* LLM router
    (template fallback mode) and delegates to the handler's public
    :meth:`~BasePhaseHandler.execute` method.

    Production callers should instantiate :class:`ValidateAuditHandler`
    directly with the appropriate ``llm_router`` and ``cost_tracker``
    via constructor injection.

    Parameters
    ----------
    loop_id:
        Unique 12-character hex loop identifier.
    task:
        Human-readable task description.
    goal:
        Optional goal string for plan-generation context.

    Returns
    -------
    str
        Markdown audit report content.
    """
    handler = ValidateAuditHandler()
    return await handler.execute(loop_id, task, goal)
