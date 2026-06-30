"""P22 integration wiring — builds the IntegrationRegistry + ActionRouter.

This module wires P22's own IntegrationRegistry (NOT life_kernel's
SensorRegistry) and provides an ActionRouter for domain minds to call.
It does NOT import or modify any P20 closed file — `grep -rn
"from guinvere.life_kernel" src/life_integrations/` returns 0 hits. The registry
is purely additive; P20 may optionally consume it via app.state.p22_registry.

V-002 (sensors-not-triggers) preserved: P22 adapters are queried on demand
for health (IntegrationScheduler) and write actions go through the
ActionRouter gate pipeline (classification → consent/HARD STOP → execute).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from guinvere.life_integrations.adapters import (
    BrowserIntegrationAdapter,
    CalendarIntegrationAdapter,
    DiscordIntegrationAdapter,
    DriveIntegrationAdapter,
    FilesystemIntegrationAdapter,
    FinanceIntegrationAdapter,
    GitHubIntegrationAdapter,
    GmailIntegrationAdapter,
    MemoryIntegrationAdapter,
    NotionIntegrationAdapter,
    TelegramIntegrationAdapter,
    VPSIntegrationAdapter,
    WhatsAppIntegrationAdapter,
)
from guinvere.life_integrations.audit import AuditLogger
from guinvere.life_integrations.consent import ConsentGate
from guinvere.life_integrations.project_context import ProjectContext
from guinvere.life_integrations.registry import IntegrationRegistry
from guinvere.life_integrations.router import ActionRouter
from guinvere.life_integrations.scheduler import IntegrationScheduler

logger = structlog.get_logger(__name__)


async def build_default_registry(
    discord_rest_client: Any | None = None,
    gmail_service: Any | None = None,
    github_client: Any | None = None,
    vps_docker_client: Any | None = None,
    vps_shell_client: Any | None = None,
    memory_write_pipeline: Any | None = None,
    memory_read_pipeline: Any | None = None,
    kg_engine: Any | None = None,
    workspace_root: str | None = None,
    finance_mind: Any | None = None,
    browser_search: Any | None = None,
    browser_fetch: Any | None = None,
    browser_cdp: Any | None = None,
    whatsapp_adapter: Any | None = None,
    calendar_client: Any | None = None,
    drive_client: Any | None = None,
    notion_client: Any | None = None,
    telegram_client: Any | None = None,
) -> IntegrationRegistry:
    """Build the default P22 integration registry with all 12 adapters.

    Adapters without credentials are registered with CONFIG_MISSING status
    (not fake success). Adapters with credentials are wired to real clients.

    Args:
        Various optional clients — None means CONFIG_MISSING for that adapter.

    Returns:
        IntegrationRegistry with all 12 adapters registered.

    Note:
        This function is async because adapter registration holds the
        asyncio.Lock inside ``IntegrationRegistry.register()`` to be safe
        under concurrent startup. Callers must ``await`` it.
    """
    registry = IntegrationRegistry()

    adapters = [
        DiscordIntegrationAdapter(rest_client=discord_rest_client),
        GmailIntegrationAdapter(gmail_service=gmail_service),
        GitHubIntegrationAdapter(github_client=github_client),
        CalendarIntegrationAdapter(calendar_client=calendar_client),
        DriveIntegrationAdapter(drive_client=drive_client),
        NotionIntegrationAdapter(notion_client=notion_client),
        TelegramIntegrationAdapter(telegram_client=telegram_client),
        WhatsAppIntegrationAdapter(whatsapp_adapter=whatsapp_adapter),
        VPSIntegrationAdapter(
            docker_client=vps_docker_client,
            shell_client=vps_shell_client,
        ),
        FinanceIntegrationAdapter(finance_mind=finance_mind),
        BrowserIntegrationAdapter(
            search_client=browser_search,
            fetch_client=browser_fetch,
            browser_client=browser_cdp,
        ),
        MemoryIntegrationAdapter(
            write_pipeline=memory_write_pipeline,
            read_pipeline=memory_read_pipeline,
            kg_engine=kg_engine,
        ),
        FilesystemIntegrationAdapter(workspace_root=workspace_root),
    ]

    for adapter in adapters:
        await registry.register(adapter)

    logger.info(
        "p22.registry_built",
        adapter_count=len(adapters),
    )

    return registry


async def build_action_router(
    registry: IntegrationRegistry | None = None,
    consent_checker: Any | None = None,
    hard_stop_checker: Any | None = None,
    audit_writer: Any | None = None,
    project_registry: Any | None = None,
) -> ActionRouter:
    """Build an ActionRouter with the full gate pipeline.

    Args:
        registry: Integration registry (auto-built if None).
        consent_checker: Consent ledger checker.
        hard_stop_checker: HARD STOP handler.
        audit_writer: Audit persistence writer.
        project_registry: P19 ProjectRegistry.

    Returns:
        Configured ActionRouter.
    """
    if registry is None:
        registry = await build_default_registry()

    consent_gate = ConsentGate(
        consent_checker=consent_checker,
        hard_stop_checker=hard_stop_checker,
    )
    # A3 fix (2026-06-29): seed the hash chain from the DB's last row so the
    # chain CONTINUES across process restarts instead of restarting from "".
    # Previously AuditLogger(writer=audit_writer) used the default
    # initial_hash="" → every restart started a fresh chain → the first
    # post-restart write's previous_hash="" broke the chain (tamper-evidence
    # compromised for the restart boundary). Now:
    # - If the writer has seed_last_hash() (IntegrationAuditWriter), call it
    #   and pass the returned hash as initial_hash (None → degraded mode per
    #   audit.py:220-226, refuses synthetic writes; "" → fresh chain OK).
    # - If the writer has no seed_last_hash (FileAuditWriter), skip seeding —
    #   a fresh "" chain is correct for a fresh file writer.
    # - If no writer (dev mode), AuditLogger defaults to "" (events logged,
    #   not persisted).
    _initial_hash: str | None = ""
    if audit_writer is not None and hasattr(audit_writer, "seed_last_hash"):
        try:
            _initial_hash = await audit_writer.seed_last_hash()
        except Exception as exc:  # noqa: BLE001 — fail-closed, never crash wiring
            logger.warning(
                "p22.audit_seed_failed_wiring_fail_closed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            _initial_hash = None  # degraded mode — refuse to extend a broken chain
    audit_logger = AuditLogger(writer=audit_writer, initial_hash=_initial_hash)
    project_context = ProjectContext(registry=project_registry)

    return ActionRouter(
        registry=registry,
        consent_gate=consent_gate,
        audit_logger=audit_logger,
        project_context=project_context,
    )


def build_scheduler(
    registry: IntegrationRegistry,
    interval_seconds: int = 30,
) -> IntegrationScheduler:
    """Build an IntegrationScheduler for background health polling.

    Args:
        registry: Integration registry.
        interval_seconds: Health check interval.

    Returns:
        IntegrationScheduler (call .start() to begin polling).
    """
    return IntegrationScheduler(
        registry=registry,
        interval_seconds=interval_seconds,
    )
