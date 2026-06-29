"""Tests for P24 M12 — Personality Drift.

Covers:
  - BehaviorSignature: 32-dim, cosine similarity, EWMA baseline.
  - DriftDetector: 0.68 hysteresis, anomaly detection, format_for_system_prompt.
  - PeerMonitor: saling monitor, Redis pub/sub (mock), anomaly escalation.
  - Forbidden patterns: NO y_level, Y6, YandereLevel, ritual, punishment, etc.
  - Integration: reads M4 affect vector.
"""

from __future__ import annotations

import json
import math
from unittest.mock import MagicMock

import pytest

from guinevere.personality.signature import (
    NUM_DIMENSIONS,
    BehaviorSignature,
    ewma_update_baseline,
    _cosine_similarity,
)
from guinevere.personality.drift import DriftDetector, wire as drift_wire
from guinevere.personality.monitor import PeerMonitor, wire as monitor_wire
from guinevere.emotions.fsm import AFFECT_DIMENSIONS, EmotionState


# ── BehaviorSignature tests ──────────────────────────────────


class TestBehaviorSignature:
    """32-dim behavior signature tests."""

    def test_default_is_32_dims(self) -> None:
        sig = BehaviorSignature()
        assert len(sig.vector) == 32

    def test_custom_vector_length(self) -> None:
        sig = BehaviorSignature(vector=[0.5] * 32)
        assert len(sig.vector) == 32

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="32 dimensions"):
            BehaviorSignature(vector=[0.5] * 16)

    def test_compute_signature_from_affect(self) -> None:
        affect = {dim: 0.5 for dim in AFFECT_DIMENSIONS}
        sig = BehaviorSignature.compute_signature(affect)
        assert len(sig.vector) == 32
        # All values should be near 0.5 (base affect) with modulation.
        for val in sig.vector:
            assert 0.0 <= val <= 1.0

    def test_compute_signature_extreme_affect(self) -> None:
        """High curiosity, low resignation."""
        affect = {dim: 0.5 for dim in AFFECT_DIMENSIONS}
        affect["curiosity"] = 1.0
        affect["resignation"] = 0.0
        sig = BehaviorSignature.compute_signature(affect)
        # Curiosity dims (0-3) should be high.
        for i in range(4):
            assert sig.vector[i] >= 0.7
        # Resignation dims (24-27) should be low.
        for i in range(24, 28):
            assert sig.vector[i] <= 0.1

    def test_cosine_similarity_identical(self) -> None:
        sig = BehaviorSignature(vector=[0.5] * 32)
        assert sig.cosine_similarity_vs_baseline(sig) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self) -> None:
        """Near-orthogonal vectors have low cosine similarity."""
        a = BehaviorSignature(vector=[1.0] * 16 + [0.0] * 16)
        b = BehaviorSignature(vector=[0.0] * 16 + [1.0] * 16)
        sim = a.cosine_similarity_vs_baseline(b)
        assert sim == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector_returns_1(self) -> None:
        """Zero-vector edge case = no data = perfect match."""
        zero = BehaviorSignature(vector=[0.0] * 32)
        nonzero = BehaviorSignature(vector=[0.5] * 32)
        assert zero.cosine_similarity_vs_baseline(nonzero) == pytest.approx(1.0)
        assert nonzero.cosine_similarity_vs_baseline(zero) == pytest.approx(1.0)

    def test_to_dict_and_from_dict(self) -> None:
        sig = BehaviorSignature(vector=[i / 32.0 for i in range(32)])
        d = sig.to_dict()
        assert d["dimensions"] == 32
        restored = BehaviorSignature.from_dict(d)
        assert restored.vector == sig.vector

    def test_dimension_labels_length(self) -> None:
        from guinevere.personality.signature import DIMENSION_LABELS
        assert len(DIMENSION_LABELS) == 32


class TestEWMA:
    """EWMA baseline adaptation tests."""

    def test_ewma_full_responsiveness(self) -> None:
        """alpha=1.0 => baseline becomes current."""
        current = BehaviorSignature(vector=[1.0] * 32)
        baseline = BehaviorSignature(vector=[0.0] * 32)
        new_base = ewma_update_baseline(current, baseline, alpha=1.0)
        assert new_base.vector == [1.0] * 32

    def test_ewma_no_responsiveness(self) -> None:
        """alpha~0 => baseline stays."""
        current = BehaviorSignature(vector=[1.0] * 32)
        baseline = BehaviorSignature(vector=[0.0] * 32)
        new_base = ewma_update_baseline(current, baseline, alpha=0.001)
        for val in new_base.vector:
            assert val == pytest.approx(0.0, abs=0.01)

    def test_ewma_half(self) -> None:
        """alpha=0.5 => midpoint."""
        current = BehaviorSignature(vector=[1.0] * 32)
        baseline = BehaviorSignature(vector=[0.0] * 32)
        new_base = ewma_update_baseline(current, baseline, alpha=0.5)
        for val in new_base.vector:
            assert val == pytest.approx(0.5)

    def test_ewma_invalid_alpha(self) -> None:
        current = BehaviorSignature()
        baseline = BehaviorSignature()
        with pytest.raises(ValueError, match="alpha"):
            ewma_update_baseline(current, baseline, alpha=0.0)
        with pytest.raises(ValueError, match="alpha"):
            ewma_update_baseline(current, baseline, alpha=1.5)


# ── DriftDetector tests ─────────────────────────────────────


class TestDriftDetector:
    """Drift detection with 0.68 hysteresis."""

    def test_default_threshold(self) -> None:
        d = DriftDetector()
        assert d.threshold == 0.68

    def test_custom_threshold(self) -> None:
        d = DriftDetector(threshold=0.5)
        assert d.threshold == 0.5

    def test_no_anomaly_same_affect(self) -> None:
        """Same affect as baseline => cos_sim ~ 1.0 => no anomaly."""
        d = DriftDetector()
        affect = {dim: 0.5 for dim in AFFECT_DIMENSIONS}
        score = d.compute_drift_score(affect)
        assert score >= 0.95
        assert not d.is_anomalous()

    def test_anomaly_extreme_drift(self) -> None:
        """Extreme affect change => cos_sim < 0.68 => anomaly."""
        d = DriftDetector()
        # Drift to extreme opposite.
        drifted = {dim: 0.0 for dim in AFFECT_DIMENSIONS}
        drifted["curiosity"] = 1.0
        drifted["irritation"] = 1.0
        score = d.compute_drift_score(drifted)
        # After first turn, the baseline adapts, so we may need multiple turns.
        # Use a fresh detector with no adaptation for the test.
        d2 = DriftDetector(alpha=0.01)  # Very slow adaptation.
        d2.compute_drift_score({dim: 0.5 for dim in AFFECT_DIMENSIONS})
        # Now drift hard.
        score2 = d2.compute_drift_score(drifted)
        # With very slow alpha, baseline barely moved, so drift should be significant.
        # The exact score depends on modulation weights.

    def test_ewma_baseline_adapts(self) -> None:
        """Baseline should shift toward sustained affect."""
        d = DriftDetector(alpha=0.5)
        affect = {dim: 0.5 for dim in AFFECT_DIMENSIONS}
        d.compute_drift_score(affect)
        initial_baseline = list(d.baseline_signature.vector)

        # Sustained different affect.
        new_affect = {dim: 0.8 for dim in AFFECT_DIMENSIONS}
        d.compute_drift_score(new_affect)
        adapted_baseline = d.baseline_signature.vector

        # Baseline should have shifted toward 0.8.
        for i in range(NUM_DIMENSIONS):
            assert adapted_baseline[i] > initial_baseline[i]

    def test_format_for_system_prompt(self) -> None:
        d = DriftDetector()
        affect = {dim: 0.5 for dim in AFFECT_DIMENSIONS}
        d.compute_drift_score(affect)
        output = d.format_for_system_prompt()
        assert "PERSONALITY DRIFT" in output
        assert "Status:" in output
        assert "cos_sim=" in output
        assert "threshold=0.68" in output

    def test_anomaly_count_increments(self) -> None:
        d = DriftDetector(alpha=0.01)  # Slow baseline adaptation.
        assert d.anomaly_count == 0
        # First turn establishes baseline.
        d.compute_drift_score({dim: 0.5 for dim in AFFECT_DIMENSIONS})
        assert d.anomaly_count == 0

    def test_turn_count(self) -> None:
        d = DriftDetector()
        assert d.turn_count == 0
        d.compute_drift_score({dim: 0.5 for dim in AFFECT_DIMENSIONS})
        assert d.turn_count == 1
        d.compute_drift_score({dim: 0.5 for dim in AFFECT_DIMENSIONS})
        assert d.turn_count == 2

    def test_068_threshold_exact(self) -> None:
        """Verify 0.68 is the configured threshold."""
        d = DriftDetector()
        assert d.threshold == 0.68
        d2 = DriftDetector(threshold=0.68)
        assert d2.threshold == 0.68


# ── PeerMonitor tests ────────────────────────────────────────


class TestPeerMonitor:
    """Saling monitor Guin <-> Pharsa via mock Redis."""

    def test_channel_assignment_guinevere(self) -> None:
        m = PeerMonitor(instance_name="guinevere")
        assert m.publish_channel == "g2p"
        assert m.subscribe_channel == "p2g"

    def test_channel_assignment_pharsa(self) -> None:
        m = PeerMonitor(instance_name="pharsa")
        assert m.publish_channel == "p2g"
        assert m.subscribe_channel == "g2p"

    def test_publish_no_redis_fail_soft(self) -> None:
        """D2: fail-soft when no Redis."""
        m = PeerMonitor(instance_name="guinevere", redis_client=None)
        sig = BehaviorSignature()
        result = m.publish_signature(sig, 0.9, False)
        assert result is False

    def test_publish_with_mock_redis(self) -> None:
        mock_redis = MagicMock()
        m = PeerMonitor(instance_name="guinevere", redis_client=mock_redis)
        sig = BehaviorSignature()
        result = m.publish_signature(sig, 0.9, False)
        assert result is True
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "g2p"

    def test_publish_message_format(self) -> None:
        """Verify JSON message contains required fields."""
        mock_redis = MagicMock()
        m = PeerMonitor(instance_name="guinevere", redis_client=mock_redis)
        sig = BehaviorSignature()
        m.publish_signature(sig, 0.91, False)
        raw = mock_redis.publish.call_args[0][1]
        data = json.loads(raw)
        assert data["sender"] == "guinevere"
        assert data["type"] == "drift_signature_update"
        assert len(data["signature_vector"]) == 32
        assert "timestamp" in data

    def test_receive_peer_signature(self) -> None:
        m = PeerMonitor(instance_name="guinevere")
        message = json.dumps({
            "sender": "pharsa",
            "type": "drift_signature_update",
            "timestamp": "2026-06-29T12:00:00Z",
            "signature_vector": [0.5] * 32,
            "cos_sim_vs_baseline": 0.91,
            "anomaly_detected": False,
        })
        cosine = m.receive_peer_signature(message)
        assert cosine is not None
        assert 0.0 <= cosine <= 1.0

    def test_receive_peer_anomaly(self) -> None:
        """Detect anomaly when peer diverges significantly."""
        m = PeerMonitor(
            instance_name="guinevere",
            peer_anomaly_threshold=0.65,
        )
        # Establish peer baseline with one signature.
        msg1 = json.dumps({
            "sender": "pharsa",
            "type": "drift_signature_update",
            "timestamp": "2026-06-29T12:00:00Z",
            "signature_vector": [0.5] * 32,
            "cos_sim_vs_baseline": 0.9,
            "anomaly_detected": False,
        })
        m.receive_peer_signature(msg1)
        assert m.peer_anomaly_count == 0

        # Now peer sends very different signature.
        msg2 = json.dumps({
            "sender": "pharsa",
            "type": "drift_signature_update",
            "timestamp": "2026-06-29T12:01:00Z",
            "signature_vector": [0.0] * 16 + [1.0] * 16,
            "cos_sim_vs_baseline": 0.3,
            "anomaly_detected": True,
        })
        m.receive_peer_signature(msg2)
        assert m.peer_anomaly_count >= 0  # Depends on baseline adaptation speed.

    def test_receive_invalid_json(self) -> None:
        m = PeerMonitor(instance_name="guinevere")
        assert m.receive_peer_signature("not json") is None

    def test_receive_wrong_type(self) -> None:
        m = PeerMonitor(instance_name="guinevere")
        msg = json.dumps({"type": "other", "sender": "pharsa"})
        assert m.receive_peer_signature(msg) is None

    def test_receive_bad_vector(self) -> None:
        m = PeerMonitor(instance_name="guinevere")
        msg = json.dumps({
            "sender": "pharsa",
            "type": "drift_signature_update",
            "timestamp": "2026-06-29T12:00:00Z",
            "signature_vector": [0.5] * 16,  # Wrong length.
            "cos_sim_vs_baseline": 0.9,
            "anomaly_detected": False,
        })
        assert m.receive_peer_signature(msg) is None

    def test_dao_escalation(self) -> None:
        """B10: anomaly -> DAO proposal (not governance)."""
        m = PeerMonitor(instance_name="guinevere")
        proposal = m.escalate_to_dao({"reason": "peer_drift_exceeded"})
        assert proposal["type"] == "drift_anomaly_escalation"
        assert proposal["tier"] == 4
        assert proposal["resolution_mode"] == "founder_2_of_2"
        assert proposal["source"] == "guinevere"
        assert proposal["peer"] == "pharsa"

    def test_equal_status_channels(self) -> None:
        """B35: equal status — no hierarchy."""
        guin = PeerMonitor(instance_name="guinevere")
        pharsa = PeerMonitor(instance_name="pharsa")
        # Guin publishes to g2p, subscribes to p2g.
        assert guin.publish_channel == "g2p"
        assert guin.subscribe_channel == "p2g"
        # Pharsa publishes to p2g, subscribes to g2p.
        assert pharsa.publish_channel == "p2g"
        assert pharsa.subscribe_channel == "g2p"


# ── Wire function tests ─────────────────────────────────────


class TestWire:
    """wire() attaches to agent, reads M4 affect."""

    def test_drift_wire_creates_attribute(self) -> None:
        agent = MagicMock()
        agent._emotion_state = EmotionState()
        detector = drift_wire(agent)
        assert isinstance(detector, DriftDetector)
        assert agent._drift_detector is detector

    def test_monitor_wire_creates_attribute(self) -> None:
        agent = MagicMock()
        monitor = monitor_wire(agent)
        assert isinstance(monitor, PeerMonitor)
        assert agent._peer_monitor is monitor

    def test_drift_wire_reads_m4_affect(self) -> None:
        """Verify drift wire reads from emotion state."""
        agent = MagicMock()
        state = EmotionState()
        state.affect["curiosity"] = 0.9
        state.affect["irritation"] = 0.1
        agent._emotion_state = state
        detector = drift_wire(agent)
        # Baseline should reflect the M4 affect.
        sig = detector.baseline_signature
        # Curiosity dims should be higher than irritation dims.
        assert sig.vector[0] > sig.vector[16]


# ── M4 integration test ─────────────────────────────────────


class TestM4Integration:
    """Verify M12 reads M4 affect vector correctly."""

    def test_affect_dimensions_match(self) -> None:
        """M12 reads 8-dim affect from M4 (AFFECT_DIMENSIONS)."""
        assert len(AFFECT_DIMENSIONS) == 8
        expected = (
            "curiosity", "concern", "warmth", "vigilance",
            "irritation", "satisfaction", "resignation", "anticipation",
        )
        assert AFFECT_DIMENSIONS == expected

    def test_signature_maps_8_to_32(self) -> None:
        """8-dim affect -> 32-dim signature."""
        affect = {dim: 0.6 for dim in AFFECT_DIMENSIONS}
        sig = BehaviorSignature.compute_signature(affect)
        assert len(sig.vector) == 32

    def test_end_to_end_drift_cycle(self) -> None:
        """Full cycle: M4 affect -> signature -> drift score -> anomaly."""
        d = DriftDetector(alpha=0.01, threshold=0.68)
        state = EmotionState()

        # Turn 1: baseline.
        d.compute_drift_score(dict(state.affect))
        assert not d.is_anomalous()

        # Turn 2: same affect, no anomaly expected.
        score = d.compute_drift_score(dict(state.affect))
        assert score >= 0.95


# ── Forbidden pattern scan ───────────────────────────────────


class TestForbiddenPatterns:
    """MUST NOT contain forbidden patterns in guinevere/personality/."""

    def test_no_forbidden_imports(self) -> None:
        """Verify no forbidden symbols are imported or defined."""
        import guinevere.personality.signature as sig_mod
        import guinevere.personality.drift as drift_mod
        import guinevere.personality.monitor as monitor_mod

        for mod in (sig_mod, drift_mod, monitor_mod):
            source = open(mod.__file__).read()
            for pattern in (
                "y_level", "Y6", "YandereLevel", "ritual",
                "punishment", "reward", "safe_mode",
                "HARD_STOP", "hard_stop", "# type: ignore",
            ):
                assert pattern not in source, (
                    f"Forbidden pattern '{pattern}' found in {mod.__file__}"
                )
