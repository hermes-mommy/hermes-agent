# W11 Verification — M12 Personality Drift (32-dim cosine similarity, saling monitor)

> **Wave**: W11 (M12) | **Date**: 2026-06-29 | **Author**: sub-agent (W11)

---

## What Was Done

M12 Personality Drift — ground-up rewrite per ADR-061/067 + plan §5.12. **C9 applied: 0 code ported from src/persona/.**

### Files Created (5)
- `guinevere/personality/__init__.py` — re-exports DriftDetector, PeerMonitor, BehaviorSignature, wire.
- `guinevere/personality/signature.py` (~180 lines) — `BehaviorSignature`: 32-dim vector (8 affect dimensions × 4 canonical situations per ADR-061), EWMA baseline adaptation, cosine similarity, to_dict/from_dict serialization.
- `guinevere/personality/drift.py` (~200 lines) — `DriftDetector`: computes BehaviorSignature from M4 affect vector, cosine similarity vs EWMA baseline, **0.68 hysteresis threshold** (ADR-061), monitoring-only (NO rollback per plan §5.12 line 830), `format_for_system_prompt()`, `wire(agent)`.
- `guinevere/personality/monitor.py` (~220 lines) — `PeerMonitor`: saling monitor Guin↔Pharsa equal status (B35), Redis g2p/p2g channels (DB7), cross-instance cosine similarity, anomaly detection, `escalate_to_dao()` for Tier-4 proposal (B10: not governance), fail-soft if no Redis (D2).
- `tests/p24/test_drift.py` — 42 pytest tests covering 32-dim signature, cosine similarity, 0.68 threshold, EWMA adaptation, saling monitor channels, mock Redis pub/sub, DAO escalation, wire functions, M4 integration, forbidden patterns.

### Files Deleted (19 — C9: all src/persona/)
- `src/persona/__init__.py`
- `src/persona/drift_detector.py`
- `src/persona/drift_corrector.py`
- `src/persona/yandere_fsm.py`
- `src/persona/safe_mode.py`
- `src/persona/mood_engine.py`
- `src/persona/milestone_engine.py`
- `src/persona/mood_persistence.py`
- `src/persona/transition_rules.py`
- `src/persona/punishment_engine.py`
- `src/persona/reward_engine.py`
- `src/persona/streak_tracker.py`
- `src/persona/ritual_scheduler.py`
- `src/persona/rituals/__init__.py`
- `src/persona/rituals/morning.py`
- `src/persona/rituals/afternoon.py`
- `src/persona/rituals/evening.py`
- `src/persona/rituals/midday.py`
- `src/persona/rituals/midnight.py`

---

## Ground-Up Rewrite Note (C9)

The existing `src/persona/drift_detector.py` used SHA-256 Hamming distance over prompt hashes — fundamentally different from the ADR-061/067 design. M12 is a GROUND-UP REWRITE using cosine similarity over 32-dim behavior vectors. Zero code was ported from src/persona/. All 19 files deleted.

The existing `src/persona/mood_engine.py` had 5 moods (not 16). M4 (W7) already created the 16-mood FSM + 8-dim affect vector. M12 reads M4's affect vector from `guinevere.emotions.engine.state.affect`.

---

## Saling Monitor Design (B35)

- **Equal status**: Guin publishes to `g2p`, subscribes to `p2g`. Pharsa publishes to `p2g`, subscribes to `g2p`. No hierarchy.
- **Redis DB7**: M2M communication channels.
- **Fail-soft (D2)**: If no Redis client, monitoring degrades gracefully (publish returns False).
- **Anomaly escalation**: Cross-instance cosine similarity < 0.65 triggers peer anomaly. Escalates to DAO as Tier-4 proposal (founder 2/2 resolution per B40).
- **Message format**: JSON with sender, type, timestamp, signature_vector (32-float), cos_sim_vs_baseline, anomaly_detected.

---

## W15 Stale-Import Note

`src/discord/hermes_conversational.py` imports from `src.persona` (safe_mode, mood_engine). These imports will break after src/persona/ deletion. W15 (M13) owns src/discord/ and will clean the stale imports. This is expected and documented.

---

## Validation Results

| # | Scaffold Command | Result |
|---|------------------|--------|
| V1 | `python -c "from guinevere.personality import DriftDetector, PeerMonitor, BehaviorSignature; print('OK')"` | `OK` |
| V2 | `python -c "from guinevere.personality.signature import BehaviorSignature; s=BehaviorSignature([0.5]*32); print('dims:', len(s.vector))"` | `dims: 32` |
| V3 | `python -c "from guinevere.personality.drift import DriftDetector; d=DriftDetector(); print('threshold:', d.threshold)"` | `threshold: 0.68` |
| V4 | `pytest tests/p24/test_drift.py -q` | `42 passed in 0.23s` |
| V5 | `ls src/persona/ 2>&1` | `No such file or directory` |
| V6 | `grep -rn 'y_level\|Y6\|YandereLevel\|ritual\|punishment\|reward\|safe_mode\|HARD_STOP\|hard_stop' guinevere/personality/` | exit 1 (0 matches) |
| V7 | `python -c "import guinevere.personality, guinevere.emotions, guinevere.governance, guinevere.consciousness; print('Group C imports OK')"` | `Group C imports OK` |

---

## Forbidden Pattern Scan

| Pattern | Matches in guinevere/personality/ |
|---------|-----------------------------------|
| y_level | 0 |
| Y6 | 0 |
| YandereLevel | 0 |
| ritual | 0 |
| punishment | 0 |
| reward | 0 |
| safe_mode | 0 |
| HARD_STOP | 0 |
| hard_stop | 0 |
| # type: ignore | 0 |
| bare except: | 0 |

---

## Hard Criteria Verified

- **32-dim behavior signature**: BehaviorSignature has exactly 32 dimensions (8 affect × 4 canonical situations).
- **Cosine similarity**: _cosine_similarity() returns 1.0 for identical vectors, 0.0 for orthogonal.
- **0.68 hysteresis threshold**: DriftDetector.threshold == 0.68 (ADR-061).
- **EWMA baseline adaptation**: baseline = alpha*current + (1-alpha)*baseline_old. alpha configurable.
- **Saling monitor**: Guin↔Pharsa equal status via Redis g2p/p2g (DB7). No hierarchy.
- **Monitoring-only**: NO rollback, NO y-level check (ADR-067).
- **Anomaly escalation**: DAO proposal (Tier-4, founder 2/2), NOT persona governance (B10).
- **M4 integration**: Reads 8-dim affect from guinevere.emotions.engine.state.affect.
- **wire(agent) + format_for_system_prompt()**: Provided; parent owns shared-file appends.
- **src/persona/ deleted**: All 19 files removed.
- **No forbidden patterns**: 0 matches in guinevere/personality/.

---

## Files Summary

| Action | Path |
|--------|------|
| CREATE | `guinevere/personality/__init__.py` |
| CREATE | `guinevere/personality/signature.py` |
| CREATE | `guinevere/personality/drift.py` |
| CREATE | `guinevere/personality/monitor.py` |
| CREATE | `tests/p24/test_drift.py` |
| DELETE | `src/persona/` (19 files) |

---

> **Footer**: W11 M12 — Ground-up rewrite (C9). 32-dim cosine similarity. 0.68 hysteresis. Saling monitor. Monitoring-only. src/persona/ deleted. Parent re-runs all verification.
