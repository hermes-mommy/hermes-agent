"""P22 ActionRouter.dry_run() tests - safety net for L3 destructive actions.

Verifies the contract of dry_run:
1. Returns the documented shape: {tier, consent_scope, allowed, reason, would_execute: False}.
2. Does NOT call adapter.execute_action (proven by a mock that raises if called).
3. Does NOT write an audit row (proven by a mock audit_logger that raises if
   log_action is called).
4. For an L4 (forbidden) action -> allowed=False with reason containing L4_FORBIDDEN.
5. For an L2 (write) action with no consent -> allowed=False with reason
   containing "consent".

These tests use real SemanticActionClassifier and ConsentGate so the
classify + scope + gate path is the production code, not a stub.
"""

from __future__ import annotations

import uuid

import pytest

from src.life_integrations.audit import AuditLogger
from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.consent import ConsentGate
from src.life_integrations.permissions import SemanticActionClassifier
from src.life_integrations.project_context import ProjectContext
from src.life_integrations.registry import IntegrationRegistry
from src.life_integrations.router import ActionRouter
from src.life_integrations.types import (
    IntegrationConfig,
    IntegrationHealth,
    IntegrationStatus,
    PermissionTier,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _MockAdapter(BaseIntegrationAdapter):
    """Adapter that raises if execute_action is ever called.

    dry_run MUST NOT invoke this. Any call from the router is a contract
    violation and should fail the test loud and clear.

    config.provider is set to "mock/test" so we can also assert that
    classifier.classify uses integration_id ("mock_provider"), NOT provider.
    """

    def __init__(self, integration_id: str) -> None:
        # provider != integration_id on purpose to lock in the fix from
        # P22.2 (classifier must key by integration_id, not provider).
        config = IntegrationConfig(
            integration_id=integration_id,
            name=f"Mock {integration_id}",
            provider="mock/test",
            capabilities=frozenset(),
            consent_scopes=("consent.mock.mock.read", "consent.mock.mock.write"),
            secret_refs=(),
        )
        super().__init__(config)

    async def health_check(self) -> IntegrationHealth:
        return IntegrationHealth.OK

    async def check_status(self) -> IntegrationStatus:
        return IntegrationStatus.ACTIVE

    async def execute_action(self, action, tier, project_id=None, **kwargs):
        raise AssertionError(
            f"dry_run MUST NOT call adapter.execute_action "
            f"(action={action!r}, tier={tier!r})"
        )


class _RaisingAuditLogger(AuditLogger):
    """Audit logger that raises if log_action is ever called.

    dry_run MUST NOT write audit rows. Any call from the router is a
    contract violation.
    """

    async def log_action(self, **kwargs):
        raise AssertionError(
            f"dry_run MUST NOT write to audit log "
            f"(called with {sorted(kwargs.keys())})"
        )

    async def write_event(self, event):
        raise AssertionError(
            "dry_run MUST NOT write audit event "
            f"(event action={getattr(event, 'action', '?')!r})"
        )


class _NoConsentChecker:
    """Consent checker that always denies - useful for "no consent" paths."""

    async def check_consent(self, scope, project_id=None) -> bool:
        return False


class _AllowConsentChecker:
    """Consent checker that always grants - useful for "allowed" paths."""

    async def check_consent(self, scope, project_id=None) -> bool:
        return True


class _InactiveHardStopChecker:
    """HardStopChecker stub reporting clear (audit F03 alignment).

    Audit F03 makes `hard_stop_checker=None` fail-closed for L2+; tests that
    want to isolate consent/HARD STOP-active logic must wire a real (inactive)
    checker instead of None.
    """

    def is_hard_stop_active(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    return IntegrationRegistry()


@pytest.fixture
def audit_logger():
    return _RaisingAuditLogger()


@pytest.fixture
def project_context():
    return ProjectContext()


@pytest.fixture
def router(registry, audit_logger, project_context):
    """Router with raising audit logger and real classifier."""
    return ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(),  # no checkers -> L2+ fail-closed
        audit_logger=audit_logger,
        project_context=project_context,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dry_run_returns_required_keys(registry, audit_logger):
    """(1) dry_run returns {tier, consent_scope, allowed, reason, would_execute: False}."""
    await registry.register(_MockAdapter("mock_provider"))
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(),
        audit_logger=audit_logger,
    )
    result = await router.dry_run(
        integration_id="mock_provider",
        action="list_widgets",  # unknown -> F04 default L2_WRITE
    )
    required = {"tier", "consent_scope", "allowed", "reason", "would_execute"}
    assert required.issubset(result.keys()), (
        f"missing keys: {required - set(result.keys())}"
    )
    assert result["would_execute"] is False, (
        "dry_run MUST return would_execute=False"
    )
    # F04 fix: unknown actions no longer silently default to L1_READ;
    # an unknown action lands in L2_WRITE (consent gate applied).
    assert result["tier"] == PermissionTier.L2_WRITE.name


@pytest.mark.asyncio
async def test_dry_run_does_not_call_adapter_execute(router, registry):
    """(2) dry_run does NOT call adapter.execute_action.

    The mock adapter raises AssertionError if execute_action is invoked.
    If dry_run bypasses the gate (or accidentally executes), this test
    fails loud.
    """
    await registry.register(_MockAdapter("mock_provider"))
    # After F04 fix: unknown actions default to L2_WRITE (consent required).
    # ConsentGate has no checkers so L2+ fails-closed; allowed=False.
    # Either way, the router MUST NOT call adapter.execute_action.
    result = await router.dry_run(
        integration_id="mock_provider",
        action="list_widgets",
    )
    assert result["would_execute"] is False
    # F04: unknown action is L2 -> fail-closed without consent -> allowed=False.
    # Still proves the adapter was NOT called (the mock would have raised).


@pytest.mark.asyncio
async def test_dry_run_does_not_write_audit_row(router, registry):
    """(3) dry_run does NOT call audit_logger.log_action / write_event.

    The mock audit logger raises AssertionError on any write. Any
    audit write from dry_run fails the test loud.
    """
    await registry.register(_MockAdapter("mock_provider"))
    # Test BOTH unknown-action (L2 after F04) + L4 deny paths - neither
    # may touch audit. list_widgets now defaults to L2_WRITE which fails
    # closed without consent checkers — both paths must skip the audit log.
    deny_result = await router.dry_run(
        integration_id="mock_provider",
        action="list_widgets",
    )
    # F04: L2 without checker -> deny. Either way (allow or deny),
    # audit_logger MUST NOT have been called (the mock would have raised).
    assert deny_result["allowed"] is False

    deny_result2 = await router.dry_run(
        integration_id="mock_provider",  # unknown to L4 keyword mapping
        action="system_prune_db",  # L4 by keyword
    )
    assert deny_result2["allowed"] is False
    assert "L4_FORBIDDEN" in deny_result2["reason"]


@pytest.mark.asyncio
async def test_dry_run_l4_action_returns_l4_forbidden(registry, audit_logger):
    """(4) L4 action -> allowed=False, reason contains L4_FORBIDDEN."""
    await registry.register(_MockAdapter("mock_provider"))
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(
            consent_checker=_AllowConsentChecker(),
            hard_stop_checker=_InactiveHardStopChecker(),
        ),
        audit_logger=audit_logger,
    )
    result = await router.dry_run(
        integration_id="mock_provider",
        action="system_prune_db",  # L4 by semantic fallback keyword
    )
    assert result["allowed"] is False
    assert "L4_FORBIDDEN" in result["reason"], (
        f"expected L4_FORBIDDEN in reason, got: {result['reason']!r}"
    )
    assert result["would_execute"] is False


@pytest.mark.asyncio
async def test_dry_run_l2_no_consent_returns_consent_reason(registry):
    """(5) L2 action with no consent -> allowed=False, reason contains 'consent'."""
    await registry.register(_MockAdapter("memory"))  # memory -> domain == id -> 3-seg scope
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(
            consent_checker=_NoConsentChecker(),
            hard_stop_checker=_InactiveHardStopChecker(),
        ),
        audit_logger=_RaisingAuditLogger(),
    )
    result = await router.dry_run(
        integration_id="memory",
        action="create_note",  # L2 by keyword "create"
    )
    assert result["tier"] == PermissionTier.L2_WRITE.name, (
        f"expected L2_WRITE, got tier={result['tier']!r}"
    )
    assert result["allowed"] is False
    assert "consent" in result["reason"].lower(), (
        f"expected 'consent' in reason, got: {result['reason']!r}"
    )
    assert result["would_execute"] is False
    # And critically: the canonical 3-seg scope (A1 fix) is honored.
    assert result["consent_scope"] == "consent.memory.write"


@pytest.mark.asyncio
async def test_dry_run_l2_with_consent_returns_allowed(registry):
    """Sanity: L2 with granted consent -> allowed=True (without executing)."""
    await registry.register(_MockAdapter("memory"))
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(
            consent_checker=_AllowConsentChecker(),
            hard_stop_checker=_InactiveHardStopChecker(),
        ),
        audit_logger=_RaisingAuditLogger(),
    )
    result = await router.dry_run(
        integration_id="memory",
        action="create_note",
    )
    assert result["allowed"] is True
    assert result["would_execute"] is False


@pytest.mark.asyncio
async def test_dry_run_returns_dict_not_raises_on_block(registry):
    """Hard rejection: dry_run MUST NOT raise on blocked; must return dict."""
    await registry.register(_MockAdapter("mock_provider"))
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(),
        audit_logger=_RaisingAuditLogger(),
    )
    # L2 without consent - dry_run must return a dict, NOT raise.
    result = await router.dry_run(
        integration_id="mock_provider",
        action="create_widget",
    )
    assert isinstance(result, dict), (
        f"dry_run MUST return dict on blocked, got {type(result).__name__}"
    )
    assert result["allowed"] is False


@pytest.mark.asyncio
async def test_dry_run_unknown_integration_returns_error_dict():
    """Unknown integration -> informed error dict (KeyError caught, not raised)."""
    registry = IntegrationRegistry()
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(),
        audit_logger=_RaisingAuditLogger(),
    )
    result = await router.dry_run(
        integration_id="ghost_integration",
        action="anything",
    )
    assert isinstance(result, dict)
    assert result["allowed"] is False
    assert result["would_execute"] is False
    assert "error" in result, "expected 'error' key on unknown integration"


@pytest.mark.asyncio
async def test_dry_run_signature_accepts_kwargs_but_ignores(registry):
    """dry_run accepts **kwargs for parity with execute() but ignores them."""
    await registry.register(_MockAdapter("mock_provider"))
    router = ActionRouter(
        registry=registry,
        classifier=SemanticActionClassifier(),
        consent_gate=ConsentGate(),
        audit_logger=_RaisingAuditLogger(),
    )
    # If kwargs were forwarded to execute_action, mock would raise.
    result = await router.dry_run(
        integration_id="mock_provider",
        action="list_widgets",
        some_random_kwarg="would_kill_us_if_executed",
        another="value",
    )
    assert result["would_execute"] is False
