"""FastAPI routes for Guinevere internal API — loop management + P22 integrations.

Two surface areas, both mounted via the same ``router`` instance:

- **Loop manager endpoints** (``/api/v1/loops``): create/list/get/cancel loops.
- **P22 integration endpoints** (``/api/v1/integrations``): B1 contract surface
  for the Life Integration hub — status, capabilities, health-probe, missing,
  consent, dry-run.

Auth: ``Depends(get_api_key)`` (header ``X-Guinevere-API-Key``). Reads are
unauthenticated (so the dashboard / monitoring can poll); mutations require
the API key.

Dependency injection: every integration endpoint reads the integration-aware
singleton from ``app.state.p22_*`` (graceful fail-open — read endpoints
return ``p22_active=False`` when the singleton is absent; mutation endpoints
that need it for execution return 503).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.core.api.auth import get_api_key

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Loop manager — request/response models + helper
# ---------------------------------------------------------------------------


class LoopRequest(BaseModel):
    """Request body for creating a new loop."""

    task: str = Field(..., description="Human-readable task description")
    priority: str = Field(default="normal", description="Loop priority level")
    max_phases: int = Field(default=7, description="Maximum SDLC phases")
    goal: Optional[str] = Field(default=None, description="Optional loop goal")


class LoopResponse(BaseModel):
    """Response shape for loop endpoints."""

    loop_id: str
    status: str
    current_phase: int
    task: str
    goal: Optional[str] = None


def _get_loop_manager(request: Request):
    """Extract LoopManager from app state."""
    manager = getattr(request.app.state, "loop_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Loop manager not initialized",
        )
    return manager


# ---------------------------------------------------------------------------
# P22 integration endpoints — pydantic request models
# ---------------------------------------------------------------------------


class IntegrationsTestRequest(BaseModel):
    """POST /integrations/test — health probe body."""

    integration_id: str = Field(..., description="Adapter integration_id")


class IntegrationsConsentRequest(BaseModel):
    """POST /integrations/consent — grant/revoke consent scope body."""

    scope: str = Field(..., description="Canonical P22 consent scope")
    action: str = Field(
        ..., description='Either "grant" or "revoke"'
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional revocation reason (used on revoke)",
    )
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional project UUID scoping the consent row",
    )


class IntegrationsDryRunRequest(BaseModel):
    """POST /integrations/dry-run — preview an action without executing."""

    integration_id: str = Field(..., description="Adapter integration_id")
    action: str = Field(..., description="Action name")
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Action kwargs (forwarded to ActionRouter.dry_run)",
    )


# ---------------------------------------------------------------------------
# P22 helpers — singleton accessors (graceful fail-open)
# ---------------------------------------------------------------------------


def _get_p22_registry(request: Request):
    """Return ``app.state.p22_registry`` or ``None`` (tolerant fail-open).

    Read endpoints tolerate ``None`` (returns ``p22_active: false``); the
    health-probe / dry-run endpoints do their own null check + 503 raise.
    Never raises a 503 here — it is a getter, not a precondition gate.
    """
    return getattr(request.app.state, "p22_registry", None)


def _get_p22_router(request: Request):
    """Return ``app.state.p22_router`` or ``None``.

    The dry-run endpoint uses this; when it is ``None`` dry-run returns 503.
    """
    return getattr(request.app.state, "p22_router", None)


def _get_p22_session_factory(request: Request):
    """Return ``app.state.p22_session_factory`` or ``None``."""
    return getattr(request.app.state, "p22_session_factory", None)


def _get_p22_audit_writer(request: Request):
    """Return ``app.state.p22_audit_writer`` or ``None``."""
    return getattr(request.app.state, "p22_audit_writer", None)


# ---------------------------------------------------------------------------
# Loop endpoints
# ---------------------------------------------------------------------------


@router.get("/loops")
async def list_loops(request: Request) -> dict[str, Any]:
    """List all loops with summary counts."""
    manager = _get_loop_manager(request)
    try:
        loops = await manager.list_loops()
    except Exception:
        logger.exception("routes.list_loops_failed")
        raise HTTPException(status_code=500, detail="Failed to list loops")
    active = sum(1 for l in loops if l.get("status") == "running")
    completed = sum(1 for l in loops if l.get("status") == "complete")
    logger.info("list_loops_requested", count=len(loops))
    return {"loops": loops, "active": active, "completed": completed}


@router.post("/loops", response_model=LoopResponse, status_code=201)
async def create_loop(
    request: LoopRequest,
    req: Request,
    _api_key: str = Depends(get_api_key),
) -> LoopResponse:
    """Create a new loop instance."""
    manager = _get_loop_manager(req)
    try:
        loop_id = await manager.start_loop(
            task=request.task,
            goal=request.goal or request.task,
            priority=request.priority,
        )
    except Exception:
        logger.exception("routes.create_loop_failed")
        raise HTTPException(status_code=500, detail="Failed to create loop")
    logger.info("loop_created", loop_id=loop_id, task=request.task)
    return LoopResponse(
        loop_id=loop_id,
        status="running",
        current_phase=1,
        task=request.task,
        goal=request.goal,
    )


@router.get("/loops/{loop_id}")
async def get_loop(loop_id: str, request: Request) -> dict[str, Any]:
    """Get details of a specific loop."""
    manager = _get_loop_manager(request)
    try:
        status = await manager.get_loop_status(loop_id)
    except Exception:
        logger.exception("routes.get_loop_failed", loop_id=loop_id)
        raise HTTPException(status_code=500, detail="Failed to get loop status")
    if status is None:
        raise HTTPException(status_code=404, detail=f"Loop {loop_id} not found")
    logger.info("get_loop_requested", loop_id=loop_id)
    return status


@router.post("/loops/{loop_id}/cancel")
async def cancel_loop(
    loop_id: str,
    request: Request,
    _api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Cancel a running loop."""
    manager = _get_loop_manager(request)
    try:
        result = await manager.stop_loop(loop_id)
    except Exception:
        logger.exception("routes.cancel_loop_failed", loop_id=loop_id)
        raise HTTPException(status_code=500, detail="Failed to cancel loop")
    logger.info("cancel_loop_requested", loop_id=loop_id)
    return result


# ---------------------------------------------------------------------------
# P22 /api/v1/integrations endpoints — B1 contract
# ---------------------------------------------------------------------------


@router.get("/integrations/status")
async def integrations_status(request: Request) -> dict[str, Any]:
    """Snapshot of every registered adapter: status + health + aggregates.

    Reads ``registry.check_all_status()`` + ``registry.list_all()``.
    Returns 200 + ``p22_active: false`` + empty list when the registry
    singleton is absent (P22 inactive — fail-open for monitoring).
    """
    registry = _get_p22_registry(request)
    if registry is None:
        logger.info("p22.routes.status_inactive")
        return {
            "p22_active": False,
            "snapshot_at": datetime.now(tz=timezone.utc).isoformat(),
            "integrations": [],
            "totals": {},
        }

    try:
        statuses = await registry.check_all_status()
    except Exception:
        logger.exception("p22.routes.status_check_all_failed")
        statuses = {}

    integrations: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    for adapter in registry.list_all():
        try:
            health_obj = await adapter.health_check()
            health_value = (
                health_obj.value
                if hasattr(health_obj, "value")
                else str(health_obj)
            )
        except Exception:
            health_value = "unknown"

        status_obj = statuses.get(adapter.integration_id)
        status_value = (
            status_obj.value
            if hasattr(status_obj, "value")
            else (str(status_obj) if status_obj else "unknown")
        )

        totals[status_value] = totals.get(status_value, 0) + 1

        integrations.append(
            {
                "integration_id": adapter.integration_id,
                "name": adapter.config.name,
                "provider": adapter.config.provider,
                "status": status_value,
                "health": health_value,
                "default_tier": adapter.config.default_tier.name,
                "capabilities": [c.value for c in adapter.config.capabilities],
                "risk_tier": adapter.config.risk_tier,
            }
        )

    logger.info(
        "p22.routes.status_served",
        count=len(integrations),
        totals=totals,
    )
    return {
        "p22_active": True,
        "snapshot_at": datetime.now(tz=timezone.utc).isoformat(),
        "integrations": integrations,
        "totals": totals,
    }


@router.get("/integrations/capabilities")
async def integrations_capabilities(request: Request) -> dict[str, Any]:
    """Per-adapter × per-action readiness matrix.

    Reads ``registry.capability_matrix()`` (A5). Returns 200 +
    ``p22_active: false`` + ``capabilities: {}`` when the registry singleton
    is absent.
    """
    registry = _get_p22_registry(request)
    if registry is None:
        logger.info("p22.routes.capabilities_inactive")
        return {"p22_active": False, "capabilities": {}}

    try:
        matrix = await registry.capability_matrix()
    except Exception:
        logger.exception("p22.routes.capabilities_failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to compute capability matrix",
        )

    # Reshape the (tier, status) tuple that capability_matrix returns into
    # the {action: {tier, status}} shape the contract expects.
    capabilities: dict[str, dict[str, dict[str, str]]] = {}
    for integration_id, actions_map in matrix.items():
        capabilities[integration_id] = {}
        for action, (tier, status) in actions_map.items():
            tier_name = tier.name if hasattr(tier, "name") else str(tier)
            status_value = (
                status.value if hasattr(status, "value") else str(status)
            )
            capabilities[integration_id][action] = {
                "tier": tier_name,
                "status": status_value,
            }

    logger.info(
        "p22.routes.capabilities_served",
        introspection_keys=list(capabilities.keys()),
    )
    return {"p22_active": True, "capabilities": capabilities}


@router.post("/integrations/test")
async def integrations_test(
    body: IntegrationsTestRequest,
    request: Request,
    _api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Health probe for one adapter — NEVER executes an action.

    Calls ``adapter.health_check()`` + ``adapter.check_status()``, returns
    a per-integration summary with ``duration_ms``. Returns 404 if the
    adapter is unknown.
    """
    registry = _get_p22_registry(request)
    if registry is None:
        logger.info(
            "p22.routes.test_inactive", integration_id=body.integration_id
        )
        return {
            "p22_active": False,
            "integration_id": body.integration_id,
            "health": "unknown",
            "status": "unavailable",
            "duration_ms": 0.0,
        }

    try:
        adapter = registry.get(body.integration_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Integration {body.integration_id!r} not registered",
        )

    start = time.perf_counter()
    try:
        health_obj = await adapter.health_check()
        health_value = (
            health_obj.value
            if hasattr(health_obj, "value")
            else str(health_obj)
        )
    except Exception:
        logger.exception(
            "p22.routes.test_health_failed", integration_id=body.integration_id
        )
        health_value = "error"

    try:
        status_obj = await adapter.check_status()
        status_value = (
            status_obj.value
            if hasattr(status_obj, "value")
            else str(status_obj)
        )
    except Exception:
        logger.exception(
            "p22.routes.test_status_failed", integration_id=body.integration_id
        )
        status_value = "error"

    duration_ms = (time.perf_counter() - start) * 1000.0

    logger.info(
        "p22.routes.test_served",
        integration_id=body.integration_id,
        health=health_value,
        status=status_value,
        duration_ms=duration_ms,
    )
    return {
        "p22_active": True,
        "integration_id": body.integration_id,
        "health": health_value,
        "status": status_value,
        "duration_ms": duration_ms,
    }


@router.get("/integrations/missing")
async def integrations_missing(request: Request) -> dict[str, Any]:
    """Onboarding manifest surface per P22.3 — NAMES only, never values.

    Reads the static ``ONBOARDING_MANIFEST`` (no env reads, no secret
    value materialization). Each entry exposes:

      - ``missing_credentials``: env-var NAMES + descriptions
      - ``onboarding_steps``: OAuth steps
      - ``consent_scopes``: scopes the adapter declares
      - ``pip_packages``: adapter-specific pip requires
      - ``docs_url``: human-facing docs
    """
    # Lazy import — keeps startup cost off the cold-path.
    from src.life_integrations.adapters import ONBOARDING_MANIFEST

    registry = _get_p22_registry(request)
    p22_active = registry is not None
    if not p22_active:
        logger.info("p22.routes.missing_inactive")

    # Pure static metadata — no os.environ reads.
    missing: list[dict[str, Any]] = []
    for integration_id, entry in ONBOARDING_MANIFEST.items():
        missing.append(
            {
                "integration_id": integration_id,
                "missing_credentials": [
                    {"name": v.name, "description": v.description}
                    for v in entry.env_vars
                ],
                "onboarding_steps": list(entry.oauth_steps),
                "consent_scopes": list(entry.consent_scopes),
                "pip_packages": list(entry.pip_packages),
                "docs_url": entry.docs_url,
            }
        )

    return {"p22_active": p22_active, "missing": missing}


@router.get("/integrations/consent")
async def integrations_consent_get(request: Request) -> dict[str, Any]:
    """Recent consent-ledger rows (per-scope newest-first).

    Constructs ``ConsentLedgerWriter`` from the per-request session factory
    + audit writer pulled from ``app.state``. Returns 200 +
    ``p22_active: false`` + empty list when the registry/audit-writer are
    absent.
    """
    session_factory = _get_p22_session_factory(request)
    registry = _get_p22_registry(request)
    audit_writer = _get_p22_audit_writer(request)

    if session_factory is None or registry is None:
        logger.info("p22.routes.consent_get_inactive")
        return {"p22_active": False, "scopes": []}

    # Lazy import — keep cold-path cheap.
    from src.life_integrations.consent_ledger_writer import ConsentLedgerWriter

    writer = ConsentLedgerWriter(
        session_factory=session_factory, audit_writer=audit_writer
    )
    try:
        scopes = await writer.list_scopes()
    except Exception:
        logger.exception("p22.routes.consent_get_failed")
        scopes = []

    return {"p22_active": True, "scopes": scopes}


@router.post("/integrations/consent")
async def integrations_consent_post(
    body: IntegrationsConsentRequest,
    request: Request,
    _api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Grant or revoke a consent scope. Translates ValueError → 400."""
    session_factory = _get_p22_session_factory(request)
    audit_writer = _get_p22_audit_writer(request)

    if session_factory is None:
        logger.info(
            "p22.routes.consent_post_inactive",
            scope=body.scope,
            action=body.action,
        )
        return {
            "p22_active": False,
            "scope": body.scope,
            "action": body.action,
            "status": "unavailable",
        }

    action_normalized = body.action.strip().lower()
    if action_normalized not in ("grant", "revoke"):
        # 400 — the contract says invalid action MUST be 400.
        raise HTTPException(
            status_code=400,
            detail=(
                f"action must be 'grant' or 'revoke', got {body.action!r}"
            ),
        )

    # Lazy import — keep cold-path cheap.
    from src.life_integrations.consent_ledger_writer import ConsentLedgerWriter

    writer = ConsentLedgerWriter(
        session_factory=session_factory, audit_writer=audit_writer
    )

    try:
        if action_normalized == "grant":
            row = await writer.grant(
                scope=body.scope, project_id=body.project_id
            )
        else:
            row = await writer.revoke(
                scope=body.scope,
                project_id=body.project_id,
                reason=body.reason,
            )
    except ValueError:
        # Non-canonical scope — translated to 400.
        raise HTTPException(
            status_code=400,
            detail=f"Invalid P22 consent scope: {body.scope!r}",
        )
    except Exception:
        logger.exception(
            "p22.routes.consent_write_failed",
            scope=body.scope,
            action=action_normalized,
        )
        raise HTTPException(
            status_code=500, detail="Failed to write consent ledger row"
        )

    logger.info(
        "p22.routes.consent_post_served",
        scope=body.scope,
        action=action_normalized,
    )

    return {
        "p22_active": True,
        "scope": row["scope"],
        "action": action_normalized,
        "status": row["status"],
        "granted_by": row.get("granted_by"),
        "granted_at": row.get("granted_at"),
        "revoked_at": row.get("revoked_at"),
        "project_id": row.get("project_id"),
        "audit_id": row.get("row_id"),
        "occurred_at": row.get("granted_at"),
    }


@router.post("/integrations/dry-run")
async def integrations_dry_run(
    body: IntegrationsDryRunRequest,
    request: Request,
    _api_key: str = Depends(get_api_key),
) -> dict[str, Any]:
    """Preview an adapter action through ActionRouter.dry_run.

    Returns the router's full classification + consent verdict. Critically,
    ``would_execute`` MUST always be ``False`` (the router enforces this;
    the route re-checks before returning). Returns 503 when the router
    singleton is absent — there's nothing to "preview through" otherwise.
    """
    router_obj = _get_p22_router(request)
    if router_obj is None:
        raise HTTPException(
            status_code=503,
            detail="P22 router not initialized — cannot dry-run",
        )

    try:
        # Spread body.kwargs so the router's ``**kwargs`` catches every
        # action kwarg verbatim (matches the test stub's signature parity,
        # not a single ``kwargs={...}``-wrapped dict).
        result = await router_obj.dry_run(
            integration_id=body.integration_id,
            action=body.action,
            **body.kwargs,
        )
    except Exception:
        logger.exception(
            "p22.routes.dry_run_failed",
            integration_id=body.integration_id,
            action=body.action,
        )
        raise HTTPException(
            status_code=500, detail="Failed to execute dry-run"
        )

    # Belt-and-braces guard: the route NEVER returns would_execute=True,
    # regardless of what the router returned. The router enforces this on
    # its own, but the route layer is the absolute last line of defense.
    result["would_execute"] = False

    logger.info(
        "p22.routes.dry_run_served",
        integration_id=body.integration_id,
        action=body.action,
        tier=result.get("tier"),
        allowed=result.get("allowed"),
    )
    return result
