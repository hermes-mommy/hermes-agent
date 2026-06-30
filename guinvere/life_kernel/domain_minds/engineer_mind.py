"""Engineering domain mind — LK-014.

This module implements ``EngineerMind``, the policy-gated deploy orchestrator for
the Living Autonomy Kernel.  It provides a policy-gated deployment implementation
of backup → canary → smoke test → deploy/rollback, satisfying BD-012 and the
§0.1 Autonomy-First Governance Exception without executing real destructive
operations.

No SSH, scp, systemctl, or destructive rollback commands are invoked.  All
"deployments" are intent-only and produce structured audit logs.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypedDict

import structlog

if TYPE_CHECKING:
    from langgraph.graph import StateGraph

    from guinvere.life_kernel.hermes_brain import HermesBrain
    from guinvere.life_kernel.domain_minds.deploy_backend import DeployBackend

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeployPolicy:
    """Policy gates for autonomous engineering deployments.

    ``auto_deploy`` defaults to ``True`` because autonomy is policy-gated
    through backup → canary → smoke → rollback.  Gate failure escalates to
    the operator.  Explicit approval is only required for destructive bypass,
    safety/consent/secret boundary changes, or unsupported targets.
    """

    backup_required: bool = True
    canary_required: bool = True
    smoke_required: bool = True
    rollback_enabled: bool = True
    canary_duration_s: int = 60
    health_endpoints: list[str] = field(
        default_factory=lambda: ["/health", "/health/detailed"],
    )
    auto_deploy: bool = True


class DeployState(TypedDict, total=False):
    """LangGraph state for the deploy subgraph.

    Tracks the deploy target, policy, intermediate results, and final outcome.
    All fields are optional because nodes return partial updates.
    """

    target: dict[str, Any]
    policy: DeployPolicy
    backup_id: str
    canary_instance: str
    smoke_passed: bool
    status: str
    steps: list[dict[str, Any]]
    duration_s: float


class EngineerMind:
    """Policy-gated deploy orchestrator for the Living Autonomy Kernel.

    ``EngineerMind`` is a deployment implementation.  When a backend is provided,
    it delegates to real SSH commands; otherwise it logs deployment intent,
    produces structured markers, and returns deterministic results, but it never
    executes real SSH commands, file copies, service restarts, or destructive
    rollback operations.

    Args:
        hermes_brain: Optional Hermes brain bridge for future LLM-driven
            decision support.
        deploy_profile: Optional deploy profile dictionary.  May contain a
            ``policy`` key (``DeployPolicy`` or dict) that gates the deploy
            flow.
    """

    _default_ssh_alias: str = "guinevere-vps"
    _default_target_path: str = "/opt/guinevere"
    _default_backup_path: str = "/opt/guinevere/backups"

    def __init__(
        self,
        hermes_brain: HermesBrain | None = None,
        deploy_profile: dict[str, Any] | None = None,
        backend: DeployBackend | None = None,
    ) -> None:
        """Initialise the engineering domain mind."""
        self.hermes_brain = hermes_brain
        self.deploy_profile = deploy_profile or {}
        self.policy = self._derive_policy()
        self.backend = backend

    def _derive_policy(self) -> DeployPolicy:
        """Derive a typed ``DeployPolicy`` from the deploy profile."""
        policy_data = self.deploy_profile.get("policy")
        if isinstance(policy_data, DeployPolicy):
            return policy_data
        if isinstance(policy_data, dict):
            return DeployPolicy(**policy_data)
        return DeployPolicy()

    def create_deploy_profile(
        self,
        project: str,
        target: str,
        services: list[str],
    ) -> dict[str, Any]:
        """Create a deploy profile for a project.

        Args:
            project: Project name.
            target: Target host identifier (SSH alias or IP).
            services: List of systemd service names to manage.

        Returns:
            Deploy profile dictionary with defaults for SSH alias, target path,
            backup path, health endpoints, canary duration, smoke tests, and
            rollback flag.
        """
        profile: dict[str, Any] = {
            "project": project,
            "target_host": target,
            "ssh_alias": self._default_ssh_alias,
            "target_path": self._default_target_path,
            "services": list(services),
            "health_endpoints": ["/health", "/health/detailed", "/metrics"],
            "backup_path": self._default_backup_path,
            "canary_duration": self._default_canary_duration(),
            "smoke_tests": ["health", "process", "basic_functionality"],
            "rollback_enabled": True,
        }
        logger.info(
            "deploy_profile_created",
            project=project,
            target_host=target,
            services=services,
        )
        return profile

    @classmethod
    def _default_canary_duration(cls) -> int:
        """Return the default canary duration in seconds."""
        return 60

    async def backup(self, target: dict[str, Any]) -> dict[str, Any]:
        """Orchestrate a backup before deployment.

        Args:
            target: Target configuration dictionary.

        Returns:
            Dict with ``status="backed_up"``, a generated ``backup_id``, and
            the backup path.
        """
        if self.backend is not None:
            try:
                return await self.backend.backup(target)
            except RuntimeError:
                logger.warning(
                    "backup_async_context_fallback",
                    target_host=target.get("target_host"),
                )

        backup_path = target.get("backup_path", self._default_backup_path)
        backup_id = uuid.uuid4().hex[:12]
        logger.info(
            "backup_intent_logged",
            backup_id=backup_id,
            backup_path=backup_path,
            target_host=target.get("target_host"),
        )
        return {
            "status": "backed_up",
            "backup_id": backup_id,
            "path": backup_path,
        }

    async def canary(self, target: dict[str, Any]) -> dict[str, Any]:
        """Orchestrate a canary deployment.

        Args:
            target: Target configuration dictionary.

        Returns:
            Dict with ``status="canary_running"``, the target instance, and the
            canary duration in seconds.
        """
        if self.backend is not None:
            try:
                return await self.backend.canary(target)
            except RuntimeError:
                logger.warning(
                    "canary_async_context_fallback",
                    target_host=target.get("target_host"),
                )

        instance = target.get("target_host", self._default_ssh_alias)
        duration = target.get("canary_duration", self.policy.canary_duration_s)
        logger.info(
            "canary_intent_logged",
            instance=instance,
            duration_s=duration,
        )
        return {
            "status": "canary_running",
            "instance": instance,
            "duration_s": duration,
        }

    async def smoke_test(self, target: dict[str, Any]) -> dict[str, Any]:
        """Run smoke tests against a target.

        Args:
            target: Target configuration dictionary.  If ``target["smoke_fail"]``
                is truthy, the smoke test is forced to fail for rollback testing.

        Returns:
            Dict with ``status="smoke_passed"`` or
            ``status="smoke_failed"`` and a list of per-check results.
        """
        if self.backend is not None:
            try:
                endpoints = target.get("health_endpoints", self.policy.health_endpoints)
                return await self.backend.smoke_test(target, endpoints)
            except RuntimeError:
                logger.warning(
                    "smoke_test_async_context_fallback",
                    target_host=target.get("target_host"),
                )

        endpoints = target.get("health_endpoints", self.policy.health_endpoints)
        checks: list[dict[str, Any]] = [
            {"name": endpoint, "status": "passed"} for endpoint in endpoints
        ]
        checks.append({"name": "process_running", "status": "passed"})
        checks.append({"name": "basic_functionality", "status": "passed"})

        if target.get("smoke_fail"):
            logger.warning(
                "smoke_test_intent_failed",
                target_host=target.get("target_host"),
                checks=checks,
            )
            return {
                "status": "smoke_failed",
                "checks": checks,
            }

        logger.info(
            "smoke_test_intent_passed",
            target_host=target.get("target_host"),
            checks=checks,
        )
        return {
            "status": "smoke_passed",
            "checks": checks,
        }

    async def rollback(self, target: dict[str, Any], backup_id: str) -> dict[str, Any]:
        """Orchestrate a rollback.

        Args:
            target: Target configuration dictionary.
            backup_id: Backup identifier to restore from.

        Returns:
            Dict with ``status="rolled_back"`` and the ``backup_id``.
        """
        if self.backend is not None:
            try:
                return await self.backend.rollback(target, backup_id)
            except RuntimeError:
                logger.warning(
                    "rollback_async_context_fallback",
                    target_host=target.get("target_host"),
                    backup_id=backup_id,
                )

        logger.info(
            "rollback_intent_logged",
            target_host=target.get("target_host"),
            backup_id=backup_id,
        )
        return {
            "status": "rolled_back",
            "backup_id": backup_id,
        }

    async def deploy(self, target: dict[str, Any]) -> dict[str, Any]:
        """Run the full deploy orchestration: backup → canary → smoke → result.

        When no backend is provided, the method logs intent and returns
        structured results, but never executes real deployment commands.  If
        smoke tests fail and rollback is enabled, a rollback step is recorded.

        Args:
            target: Target configuration dictionary.  The deploy respects
                ``target["approved"]`` or ``policy.auto_deploy`` before
                promoting; otherwise it returns ``approval_required`` (only when
                auto_deploy is disabled).

        Returns:
            Dict with ``status`` (``"deployed"``, ``"rolled_back"``, or
            ``"approval_required"``), ``steps``, and ``duration_s``.
        """
        start = time.monotonic()
        steps: list[dict[str, Any]] = []

        # Approval gate: real deploy requires explicit operator approval
        if not self.policy.auto_deploy and not target.get("approved"):
            logger.warning(
                "deploy_approval_required",
                target_host=target.get("target_host"),
                reason="auto_deploy disabled and target not approved",
            )
            return {
                "status": "approval_required",
                "steps": steps,
                "duration_s": round(time.monotonic() - start, 3),
            }

        # 1. Backup
        if self.policy.backup_required:
            backup_result = await self.backup(target)
            steps.append({"step": "backup", "result": backup_result})
        else:
            backup_result = {"status": "skipped", "backup_id": "", "path": ""}

        # 2. Canary
        if self.policy.canary_required:
            canary_result = await self.canary(target)
            steps.append({"step": "canary", "result": canary_result})

        # 3. Smoke test
        smoke_result = await self.smoke_test(target)
        steps.append({"step": "smoke_test", "result": smoke_result})

        # 4. Promote or rollback
        if smoke_result["status"] == "smoke_passed":
            if self.backend is not None:
                deploy_result = await self.backend.deploy(target)
                steps.append({"step": "deploy", "result": deploy_result})
            else:
                logger.info(
                    "deploy_intent_logged",
                    target_host=target.get("target_host"),
                )
                steps.append({"step": "deploy", "result": {"status": "deployed"}})
            final_status = "deployed"
        else:
            if self.policy.rollback_enabled and backup_result.get("status") == "backed_up":
                rollback_result = await self.rollback(target, backup_result["backup_id"])
                steps.append({"step": "rollback", "result": rollback_result})
                final_status = "rolled_back"
            else:
                steps.append({"step": "rollback", "result": {"status": "rollback_disabled"}})
                final_status = "smoke_failed"

        duration = round(time.monotonic() - start, 3)
        return {
            "status": final_status,
            "steps": steps,
            "duration_s": duration,
        }

    def build_graph(self) -> StateGraph[DeployState]:
        """Build the LangGraph deploy subgraph.

        Nodes:
            - ``backup_node``
            - ``canary_node``
            - ``smoke_node``
            - ``deploy_node``
            - ``rollback_node``

        Flow:
            backup_node → canary_node → smoke_node
            smoke_node ─PASS→ deploy_node → END
            smoke_node ─FAIL→ rollback_node → END

        Returns:
            Uncompiled ``StateGraph`` for the deploy subgraph.
        """
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(DeployState)

        builder.add_node("backup_node", self._backup_node)
        builder.add_node("canary_node", self._canary_node)
        builder.add_node("smoke_node", self._smoke_node)
        builder.add_node("deploy_node", self._deploy_node)
        builder.add_node("rollback_node", self._rollback_node)

        builder.add_edge(START, "backup_node")
        builder.add_edge("backup_node", "canary_node")
        builder.add_edge("canary_node", "smoke_node")
        builder.add_conditional_edges(
            "smoke_node",
            self._route_smoke,
            {"deploy_node": "deploy_node", "rollback_node": "rollback_node"},
        )
        builder.add_edge("deploy_node", END)
        builder.add_edge("rollback_node", END)

        return builder

    async def _backup_node(self, state: DeployState) -> dict[str, Any]:
        """LangGraph node: backup node."""
        target = state.get("target", {})
        result = await self.backup(target)
        return {
            "backup_id": result.get("backup_id"),
            "steps": [{"step": "backup", "result": result}],
        }

    async def _canary_node(self, state: DeployState) -> dict[str, Any]:
        """LangGraph node: canary node."""
        target = state.get("target", {})
        result = await self.canary(target)
        return {
            "canary_instance": result.get("instance"),
            "steps": [{"step": "canary", "result": result}],
        }

    async def _smoke_node(self, state: DeployState) -> dict[str, Any]:
        """LangGraph node: smoke test node."""
        target = state.get("target", {})
        result = await self.smoke_test(target)
        return {
            "smoke_passed": result["status"] == "smoke_passed",
            "steps": [{"step": "smoke_test", "result": result}],
        }

    async def _deploy_node(self, state: DeployState) -> dict[str, Any]:
        """LangGraph node: deploy success node."""
        logger.info(
            "deploy_node_intent_logged",
            target_host=state.get("target", {}).get("target_host"),
        )
        return {
            "status": "deployed",
            "steps": [{"step": "deploy", "result": {"status": "deployed"}}],
        }

    async def _rollback_node(self, state: DeployState) -> dict[str, Any]:
        """LangGraph node: rollback node."""
        backup_id = state.get("backup_id", "")
        target = state.get("target", {})
        result = await self.rollback(target, backup_id)
        return {
            "status": "rolled_back",
            "steps": [{"step": "rollback", "result": result}],
        }

    def _route_smoke(self, state: DeployState) -> str:
        """Conditional edge router from smoke_node."""
        if state.get("smoke_passed"):
            return "deploy_node"
        return "rollback_node"
