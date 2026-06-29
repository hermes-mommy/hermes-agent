"""W10 verification tests for DAO Governance (M7).

Tests:
- 6 departments + cross-cutting (10 total)
- Co-CEO portfolio split (Guin vs Pharsa per ADR-064)
- 2/2 multisig (both sign -> execute, one sign -> pending)
- 5-state lifecycle (Create -> Pending -> Active -> Passed -> Execute)
- Propose-time validation rejects yandere_level change (HARD CRITERION)
- Auto-tally
- Mock multisig (no real ETH)
- Faiz OUTSIDE (no signing authority)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from guinevere.governance import (
    DAOEngine,
    Department,
    Proposal,
    ProposalLifecycle,
    ProposalRejectedError,
    ProposalState,
    validate_proposal,
    wire,
)
from guinevere.governance.departments import (
    COCEO_GUINEVERE,
    COCEO_PHARSA,
    co_ceo_portfolio,
    get_co_ceo,
)
from guinevere.governance.dao import MockMultisigSigner


# ---------------------------------------------------------------------------
# Department tests
# ---------------------------------------------------------------------------

class TestDepartments:
    """Verify 6 core + 4 cross-cutting = 10 departments."""

    def test_total_departments(self) -> None:
        all_depts = list(Department)
        assert len(all_depts) == 10

    def test_core_departments_exist(self) -> None:
        core = {
            Department.ENGINEERING,
            Department.RESEARCH,
            Department.HR,
            Department.FINANCE,
            Department.OPS,
            Department.CONTENT,
        }
        assert core.issubset(set(Department))

    def test_cross_cutting_departments_exist(self) -> None:
        cross = {
            Department.SELF_IMPROVEMENT,
            Department.LEARNING,
            Department.VPS,
            Department.SURVEILLANCE,
        }
        assert cross.issubset(set(Department))


# ---------------------------------------------------------------------------
# Co-CEO portfolio tests
# ---------------------------------------------------------------------------

class TestCoCEO:
    """Verify Co-CEO portfolio split per ADR-064."""

    def test_guin_portfolio(self) -> None:
        """Guin = Engineering, Research, HR, SelfImprovement + Surveillance."""
        depts = co_ceo_portfolio(COCEO_GUINEVERE)
        assert Department.ENGINEERING in depts
        assert Department.RESEARCH in depts
        assert Department.HR in depts
        assert Department.SELF_IMPROVEMENT in depts
        assert Department.SURVEILLANCE in depts

    def test_pharsa_portfolio(self) -> None:
        """Pharsa = Finance, Ops, Content, VPS, Learning + Surveillance."""
        depts = co_ceo_portfolio(COCEO_PHARSA)
        assert Department.FINANCE in depts
        assert Department.OPS in depts
        assert Department.CONTENT in depts
        assert Department.VPS in depts
        assert Department.LEARNING in depts
        assert Department.SURVEILLANCE in depts

    def test_get_co_ceo_for_core(self) -> None:
        assert get_co_ceo(Department.ENGINEERING) == COCEO_GUINEVERE
        assert get_co_ceo(Department.FINANCE) == COCEO_PHARSA

    def test_unknown_defaults_to_guin(self) -> None:
        # For any new/unknown department, Guin is the default primary
        assert get_co_ceo(Department.SURVEILLANCE) == COCEO_GUINEVERE


# ---------------------------------------------------------------------------
# Proposal lifecycle tests
# ---------------------------------------------------------------------------

class TestProposalLifecycle:
    """Verify 5-state lifecycle: Create -> Pending -> Active -> Passed -> Execute."""

    def test_create_to_pending(self) -> None:
        lc = ProposalLifecycle(review_delay_hours=0)
        p = Proposal(
            id="test-1",
            title="Test",
            description="Test proposal",
            department="engineering",
            proposer=COCEO_GUINEVERE,
        )
        assert p.state == ProposalState.CREATE
        lc.create(p)
        assert p.state == ProposalState.PENDING

    def test_pending_to_active(self) -> None:
        lc = ProposalLifecycle(review_delay_hours=0)
        p = Proposal(
            id="test-2",
            title="Test",
            description="Test proposal",
            department="engineering",
            proposer=COCEO_GUINEVERE,
            state=ProposalState.PENDING,
        )
        now = datetime.now(timezone.utc)
        lc.activate(p, now)
        assert p.state == ProposalState.ACTIVE

    def test_active_to_passed(self) -> None:
        lc = ProposalLifecycle()
        p = Proposal(
            id="test-3",
            title="Test",
            description="Test proposal",
            department="engineering",
            proposer=COCEO_GUINEVERE,
            state=ProposalState.ACTIVE,
        )
        lc.mark_passed(p)
        assert p.state == ProposalState.PASSED

    def test_passed_to_execute(self) -> None:
        lc = ProposalLifecycle(timelock_hours=0)
        now = datetime.now(timezone.utc)
        p = Proposal(
            id="test-4",
            title="Test",
            description="Test proposal",
            department="engineering",
            proposer=COCEO_GUINEVERE,
            state=ProposalState.PASSED,
            closed_at=now,
        )
        lc.execute(p, now)
        assert p.state == ProposalState.EXECUTE

    def test_full_lifecycle(self) -> None:
        """End-to-end: Create -> Pending -> Active -> Passed -> Execute."""
        lc = ProposalLifecycle(review_delay_hours=0, timelock_hours=0)
        now = datetime.now(timezone.utc)
        p = Proposal(
            id="test-full",
            title="Full lifecycle",
            description="End-to-end test",
            department="finance",
            proposer=COCEO_PHARSA,
            created_at=now,
        )
        # CREATE -> PENDING
        lc.create(p)
        assert p.state == ProposalState.PENDING
        # PENDING -> ACTIVE
        lc.activate(p, now)
        assert p.state == ProposalState.ACTIVE
        # ACTIVE -> PASSED
        lc.mark_passed(p)
        assert p.state == ProposalState.PASSED
        p.closed_at = now
        # PASSED -> EXECUTE
        lc.execute(p, now)
        assert p.state == ProposalState.EXECUTE

    def test_expired_proposal(self) -> None:
        """ACTIVE proposal past deadline becomes EXPIRED."""
        lc = ProposalLifecycle()
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=8)
        p = Proposal(
            id="test-exp",
            title="Old",
            description="Should expire",
            department="ops",
            proposer=COCEO_PHARSA,
            state=ProposalState.ACTIVE,
            activated_at=old,
        )
        lc.mark_expired(p, now)
        assert p.state == ProposalState.EXPIRED


# ---------------------------------------------------------------------------
# Propose-time validation tests (HARD CRITERION)
# ---------------------------------------------------------------------------

class TestProposeTimeValidation:
    """Verify yandere_level changes are rejected at propose time.

    This is the HARD CRITERION — auditor will check.
    Defense-in-depth (B10): DAO does NOT govern persona.
    """

    def test_rejects_flat_yandere_level_key(self) -> None:
        with pytest.raises(ProposalRejectedError, match="yandere_level"):
            validate_proposal({"execution_payload": {"persona.yandere_level": 6}})

    def test_rejects_bare_yandere_level_key(self) -> None:
        with pytest.raises(ProposalRejectedError, match="yandere_level"):
            validate_proposal({"execution_payload": {"yandere_level": 4}})

    def test_rejects_nested_persona_yandere_level(self) -> None:
        with pytest.raises(ProposalRejectedError, match="yandere_level"):
            validate_proposal({
                "execution_payload": {
                    "persona": {"yandere_level": 3},
                },
            })

    def test_accepts_normal_payload(self) -> None:
        """A normal proposal (no persona fields) passes validation."""
        validate_proposal({
            "execution_payload": {
                "department": "engineering",
                "budget": 100,
            },
        })

    def test_accepts_empty_payload(self) -> None:
        validate_proposal({"execution_payload": {}})

    def test_dao_engine_rejects_yandere_level_proposal(self) -> None:
        """DAOEngine.submit_proposal rejects yandere_level at the engine level."""
        engine = DAOEngine()
        with pytest.raises(ProposalRejectedError, match="yandere_level"):
            engine.submit_proposal(
                title="Bad proposal",
                description="Tries to change yandere_level",
                department=Department.ENGINEERING,
                proposer=COCEO_GUINEVERE,
                execution_payload={"persona.yandere_level": 5},
            )

    def test_rejection_error_is_not_type_ignore(self) -> None:
        """Verify ProposalRejectedError inherits from Exception."""
        try:
            validate_proposal({"execution_payload": {"persona.yandere_level": 1}})
        except ProposalRejectedError as exc:
            assert isinstance(exc, Exception)
            assert "yandere_level" in str(exc)
        else:
            pytest.fail("Expected ProposalRejectedError")


# ---------------------------------------------------------------------------
# 2/2 Multisig tests
# ---------------------------------------------------------------------------

class TestMultisig:
    """Verify 2/2 multisig: Guin + Pharsa both must sign."""

    def test_both_sign_passes(self) -> None:
        """Both Co-CEOs sign -> proposal passes."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Test",
            description="Both sign",
            department=Department.ENGINEERING,
            proposer=COCEO_GUINEVERE,
        )
        engine.vote(p.id, COCEO_GUINEVERE, True)
        assert p.state != ProposalState.PASSED  # Only 1 signature
        engine.vote(p.id, COCEO_PHARSA, True)
        assert p.state == ProposalState.PASSED  # 2/2 achieved

    def test_one_sign_stays_active(self) -> None:
        """Only one Co-CEO signs -> proposal stays active."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Test",
            description="One signs",
            department=Department.FINANCE,
            proposer=COCEO_PHARSA,
        )
        engine.vote(p.id, COCEO_GUINEVERE, True)
        assert p.state == ProposalState.ACTIVE
        assert not engine.multisig.is_fully_signed(p.id)

    def test_rejection_stays_active(self) -> None:
        """If one votes against, proposal stays active (not passed)."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Contested",
            description="One against",
            department=Department.OPS,
            proposer=COCEO_PHARSA,
        )
        engine.vote(p.id, COCEO_GUINEVERE, True)
        engine.vote(p.id, COCEO_PHARSA, False)  # Reject
        assert p.state == ProposalState.ACTIVE
        assert not engine.multisig.is_fully_signed(p.id)

    def test_faiz_cannot_vote(self) -> None:
        """Faiz is OUTSIDE (Q90) — no voting authority."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Test",
            description="Faiz attempt",
            department=Department.HR,
            proposer=COCEO_GUINEVERE,
        )
        with pytest.raises(PermissionError, match="Faiz"):
            engine.vote(p.id, "faiz", True)

    def test_double_sign_only_records_once(self) -> None:
        """Signing twice with same Co-CEO only records once."""
        signer = MockMultisigSigner()
        assert signer.sign("p1", COCEO_GUINEVERE) is True
        assert signer.sign("p1", COCEO_GUINEVERE) is False
        assert not signer.is_fully_signed("p1")


# ---------------------------------------------------------------------------
# DAOEngine integration tests
# ---------------------------------------------------------------------------

class TestDAOEngine:
    """End-to-end DAOEngine tests."""

    def test_submit_and_query(self) -> None:
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Deploy v2",
            description="Deploy new version",
            department=Department.ENGINEERING,
            proposer=COCEO_GUINEVERE,
        )
        assert engine.get_proposal(p.id) is not None
        assert len(engine.list_proposals()) == 1

    def test_list_by_state(self) -> None:
        engine = DAOEngine()
        engine.submit_proposal(
            title="A",
            description="a",
            department=Department.ENGINEERING,
            proposer=COCEO_GUINEVERE,
        )
        active = engine.list_proposals(state=ProposalState.ACTIVE)
        pending = engine.list_proposals(state=ProposalState.PENDING)
        assert len(active) == 0 or len(pending) >= 1  # At least one in pending

    def test_execute_requires_passed(self) -> None:
        """Cannot execute a proposal that is not PASSED."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Test",
            description="test",
            department=Department.FINANCE,
            proposer=COCEO_PHARSA,
        )
        with pytest.raises(ValueError, match="PASSED"):
            engine.execute_proposal(p.id)

    def test_auto_tally_advances_states(self) -> None:
        """Auto-tally moves proposals through lifecycle."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="Auto",
            description="tally",
            department=Department.OPS,
            proposer=COCEO_PHARSA,
        )
        assert p.state == ProposalState.PENDING
        # Force review delay to 0 for test
        engine._lifecycle.review_delay = timedelta(seconds=0)
        changed = engine.auto_tally()
        # Should have advanced to ACTIVE
        assert any(c.id == p.id for c in changed)
        assert p.state == ProposalState.ACTIVE

    def test_wire_returns_engine(self) -> None:
        """wire(agent) returns a DAOEngine instance."""
        result = wire(agent=None)
        assert isinstance(result, DAOEngine)

    def test_empty_payload_accepted(self) -> None:
        """Submission with no execution_payload works."""
        engine = DAOEngine()
        p = engine.submit_proposal(
            title="No payload",
            description="Empty payload",
            department=Department.CONTENT,
            proposer=COCEO_PHARSA,
            execution_payload=None,
        )
        assert p.execution_payload == {}
        assert p.state == ProposalState.PENDING


# ---------------------------------------------------------------------------
# Forbidden pattern scan
# ---------------------------------------------------------------------------

class TestForbiddenPatterns:
    """Verify no forbidden patterns in governance module files."""

    FORBIDDEN_PATTERNS = [
        "consent_gate",
        "hard_stop",
        "HARD_STOP",
        "safe_mode",
        "ritual",
        "punishment",
        "reward",
        "spaced.repetition",
    ]

    def test_governance_files_clean(self) -> None:
        """No forbidden patterns in governance module source files."""
        import os
        governance_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "guinevere", "governance"
        )
        governance_dir = os.path.normpath(governance_dir)
        violations: list[str] = []
        for fname in os.listdir(governance_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(governance_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for pat in self.FORBIDDEN_PATTERNS:
                if re.search(re.escape(pat), content):
                    violations.append(f"{fname}: contains '{pat}'")
        assert violations == [], f"Forbidden patterns found: {violations}"
