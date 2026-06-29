# R14: Personality Drift — P24 Domain 14

**Generated:** 2026-06-29
**Method:** File reads + grep across `src/persona/` (19 files), `.venv/Lib/site-packages/agent/system_prompt.py` (381 lines), ADR-067, P24 plan §5.12, BLDM decisions Q52/Q81/Q105/Q109, brainstorm Batch 3/5, research docs r01/r06/r07. All claims cite `file:line`.

---

## 1. ADR-067: Y-Level Cap Removal (Full Analysis)

**File:** `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-067-hermes-runtime-y-level-cap-removal.md`

### 1.1 Two-Tier Y-Level Regime

ADR-067 establishes a dual-paradigm Y-level system (lines 37-56):

**Tier 1 — Hermes runtime (P24 fork):**
- No Y-level cap exists. Y-level enumeration is absent from runtime.
- Y6 concept is REMOVED entirely — no FSM node, no transition path (line 40).
- Y4 baseline / Y5 ceiling do NOT apply (line 41).
- Drift is `bebas tanpa batas` (line 42).
- No Y-level enforcement code is shipped in P24 fork (line 43).
- Personality drift monitor does NOT include a Y-level ceiling check (line 44).

**Tier 2 — Dev-workflow agent (Guinevere in Claude):**
- Y4 baseline + Y5 ceiling + Y6 forbidden remain in force (line 48).
- PersonaSafetyPolicy governs the Claude agent unchanged (line 49).

**Tier 0 — Cross-paradigm safety:**
- Tier 4 founder-only-2/2 mutability gate remains the sole alignment safety in Hermes runtime (line 55).
- Compositional drift detector preserves no-rogue by behavior-signature distance, without Y-level semantics (line 56).

### 1.2 Implementation Layer Requirements

From ADR-067 lines 61-69:
- `hermes_emotion_fsm.py`: No `_check_y_level`, no `_Y6_BLOCKED`, no `assert y_level <= 5` guard clauses.
- `hermes_personality_drift_monitor.py`: Computes `cos_sim(new, baseline)` against behavior signature. Enforces 0.68 hysteresis (ADR-061) without Y-level check. Has no `/y6/` reference.

### 1.3 BLDM Canonical References

- **Q52**: All moods built-in (full affect spectrum) — Y-level caps are implementation-level blockers (ADR-067 line 137).
- **Q81**: Personality drift "bebas tanpa batas" within T1-T3 mutability tier (ADR-067 line 138).
- **Q105**: Emotions affect decisions — affect vector (not Y-level) is the decision input (ADR-067 line 139).
- **Q109**: Faiz trusts Hermes fully — structural safety via founder 2/2 + Ratchet + circuit breaker (ADR-067 line 140).

---

## 2. Existing src/persona/ Inventory (19 Files — PORT vs DELETE Decision)

### 2.1 DriftDetector — src/persona/drift_detector.py (228 lines)

**File:** `src/persona/drift_detector.py`

**Mechanism:** SHA-256 prompt hash comparison via Hamming distance ratio (line 117-121). Compares current prompt hash vs baseline hash.

```python
# Line 117-121
differing = sum(
    1 for a, b in zip(baseline_hash, current_prompt_hash) if a != b
)
return differing / length
```

**Action tiers:** `none` (<= threshold 0.10), `alert` (<= 0.20), `rollback` (> 0.20) (lines 142-148).

**Critical gap for M12:** This compares prompt TEXT hashes, not behavior signatures. ADR-061 and ADR-067 specify cosine similarity over behavior signatures (32 canonical situations, EWMA baseline). The Hamming-distance-over-SHA256 approach is fundamentally different.

**Disposition:** DELETE. Replaced by `guinevere/personality/drift.py` using cosine similarity over behavior vectors.

### 2.2 DriftCorrector — src/persona/drift_corrector.py (333 lines)

**File:** `src/persona/drift_corrector.py`

**Mechanism:** Auto-rollback on drift detection (lines 153-167). Integrates DriftDetector + SafeModeController. Persists DriftLog to PostgreSQL.

**Critical gap for M12:** Per plan §5.12 line 830: "Personality drift is continuous — no checkpoints, no gates, no rollbacks." The auto-rollback mechanism contradicts the `bebas tanpa batas` design. M12 drift is monitored for anomaly detection, not enforcement.

**Disposition:** DELETE. Rollback concept removed. Monitoring-only in `guinevere/personality/monitor.py`.

### 2.3 YandereFSM — src/persona/yandere_fsm.py (337 lines)

**File:** `src/persona/yandere_fsm.py`

**Mechanism:** YandereLevel IntEnum Y0-Y5 (line 63-76). PERMANENT_BASELINE=Y4 (line 84). ABSOLUTE_CEILING=Y5 (line 87). Y6 is PROHIBITED — `validate_level()` raises `YandereSafetyError` if value > 5 (lines 152-156).

```python
# Line 152-156
if value > int(ABSOLUTE_CEILING):
    raise YandereSafetyError(
        f"Yandere level {value} exceeds absolute ceiling Y5_MAX ({int(ABSOLUTE_CEILING)}). "
        "Y6 is PROHIBITED per PersonaSafetyPolicy."
    )
```

**Forbidden in M12:** Plan §5.12 line 843: `y_level`, `Y6`, `YandereLevel` are forbidden patterns in M12 files.

**Disposition:** DELETE. ADR-067 Tier 1: Y-level concept removed from Hermes runtime entirely. No replacement.

### 2.4 SafeMode — src/persona/safe_mode.py (373 lines)

**File:** `src/persona/safe_mode.py`

**Mechanism:** D0-D4 distress levels with keyword/regex detection (lines 86-107). Safe mode activates at D2+ (line 122). Deactivation requires explicit confirmation (line 311).

**Critical for M12 scope boundary:** Safe mode / distress detection is M4 (Emotion System) responsibility per plan §5.4, not M12. M12 personality drift MUST NOT include `safe_mode`, `HARD_STOP`, or `hard_stop` (plan line 843).

**Disposition:** DELETE from persona. M4 emotion system handles distress/safe-mode integration.

### 2.5 MoodEngine — src/persona/mood_engine.py (238 lines)

**File:** `src/persona/mood_engine.py`

**Mechanism:** 5-state Mood enum (line 26-33). Deterministic transition map (lines 39-45). `evaluate_mood()` is pure function with threshold rules (lines 163-237). Redis sync via `sync_mood_to_redis()` (lines 107-142).

**Claim CORRECTION:** R07 research doc (line 23) confirms: the existing codebase has exactly 5 moods, NOT 16. The 16-mood MoodState enum is a P24 NEW DESIGN (greenfield), not existing code to port.

**Disposition:** DELETE. M4 emotion system replaces with 16-mood FSM + affect vector.

### 2.6 MilestoneEngine — src/persona/milestone_engine.py (873 lines)

**File:** `src/persona/milestone_engine.py`

**Mechanism:** Milestone detection (DOMINANCE_MOMENT, TRUST_SIGNAL, ACHIEVEMENT_TOGETHER, CONFLICT_RESOLVED, FIRST_OCCURRENCE, VULNERABILITY_DISCLOSED, DOMINANCE_ESCALATION — lines 56-62). Bilingual EN/ID pattern matching. PostgreSQL persistence + Redis state sync. Relationship stage progression R1-R4 (line 685).

**Disposition:** EVALUATE. Milestone types and pattern matching are persona behavior — relevant to M12 drift calibration. Relationship stages may inform behavior signature baseline. However, milestone engine contains `HARD_STOP` references (line 412) which are forbidden in M12. Split: patterns PORT to `signature.py`, recording/progression logic DELETE.

### 2.7 Deprecated Files (DELETE — No PORT)

| File | Lines | Reason |
|------|-------|--------|
| `src/persona/punishment_engine.py` | ~400 | Plan line 843: `punishment` is forbidden in M12 |
| `src/persona/reward_engine.py` | ~300 | Plan line 843: `reward` is forbidden in M12 |
| `src/persona/streak_tracker.py` | ~200 | Streak/gamification replaced by M9 life kernel |
| `src/persona/ritual_scheduler.py` | ~200 | Plan line 828: "No rituals" |
| `src/persona/rituals/morning.py` | ~100 | Deprecated Phase 5, removed |
| `src/persona/rituals/afternoon.py` | ~100 | Deprecated Phase 5, removed |
| `src/persona/rituals/evening.py` | ~100 | Deprecated Phase 5, removed |
| `src/persona/rituals/midday.py` | ~100 | Deprecated Phase 5, removed |
| `src/persona/rituals/midnight.py` | ~100 | Deprecated Phase 5, removed |
| `src/persona/rituals/__init__.py` | ~20 | Package marker, deprecated |
| `src/persona/mood_persistence.py` | ~330 | M4 emotion system replaces |
| `src/persona/transition_rules.py` | ~376 | M4 emotion system replaces |
| `src/persona/__init__.py` | ~244 | Re-export barrel; M12 gets its own `__init__.py` |

### 2.8 Test Files (DELETE — Rewritten for M12)

| Test File | Lines | What It Tests |
|-----------|-------|---------------|
| `tests/persona/test_drift_detector.py` | ~413 | SHA-256 Hamming distance (replaced by cosine similarity) |
| `tests/persona/test_drift_corrector.py` | ~819 | Auto-rollback (removed from M12 design) |
| `tests/persona/test_yandere_fsm.py` | ~200+ | Y-level FSM (Y6 concept removed) |
| `tests/persona/test_safe_mode.py` | ~200+ | Distress detection (M4 responsibility) |
| `tests/persona/test_mood_engine.py` | ~200+ | 5-mood FSM (M4 replaces with 16-mood) |
| `tests/persona/test_mood_persistence.py` | ~200+ | Mood persistence (M4 responsibility) |
| `tests/persona/test_persona_e2e.py` | ~200+ | E2E persona integration (M12 E2E redesigned) |
| `tests/persona/test_punishment_engine.py` | ~200+ | Punishment (removed) |
| `tests/persona/test_reward_engine.py` | ~200+ | Reward (removed) |
| `tests/persona/test_ritual_*.py` (5 files) | ~500+ | Rituals (deprecated Phase 5) |
| `tests/persona/test_ritual_scheduler.py` | ~200+ | Ritual scheduler (deprecated) |
| `tests/persona/test_streak_tracker.py` | ~200+ | Streak tracker (M9 replaces) |
| `tests/persona/test_milestone_engine.py` | ~200+ | Milestone engine (split port) |
| `tests/persona/test_transition_rules.py` | ~200+ | Transition rules (M4 replaces) |
| `tests/persona/test_distress_detection.py` | ~200+ | Distress detection (M4 replaces) |

---

## 3. P24 Plan §5.12 M12 Specification

**File:** `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` lines 814-845

### 3.1 Design Summary

```
Personality drift: continuous, autonomous, emotion-driven. No Y-level cap (ADR-067). Full affect spectrum.
Drift monitoring: saling monitor (Guin ↔ Pharsa, equal status — B35).
Cosine similarity behavior signature detection with 0.68 hysteresis threshold (ADR-061).
Behavior signature = 32 canonical situations per ADR-061. Calibrated against full affect spectrum.
Y4 baseline (dev-only), Y5 ceiling (dev-only). Y6 REMOVED. No rituals. No punishment/reward.
Personality drift is continuous — no checkpoints, no gates, no rollbacks.
Drift is monitored for anomaly detection (Tier 4 founder quorum), not enforcement.
```

### 3.2 Files to CREATE

| File | ~Lines | Purpose |
|------|--------|---------|
| `guinevere/personality/__init__.py` | ~50 | Package barrel exports |
| `guinevere/personality/drift.py` | ~250 | DriftDetector, behavior signature, cosine similarity |
| `guinevere/personality/monitor.py` | ~200 | PeerMonitor, cross-instance drift comparison via G-P comms |
| `guinevere/personality/signature.py` | ~150 | BehaviorSignature, 32 canonical situations, EWMA baseline |

### 3.3 Files to MODIFY

| File | Action | Purpose |
|------|--------|---------|
| `agent/system_prompt.py` | MODIFY | Personality volatile block (append drift-analysis block to `volatile_parts`, lines 275-312) |
| `agent/agent_init.py` | MODIFY | Wire drift detector at init |
| `guinevere/config/models.py` | MODIFY | Add PersonalityConfig (drift_threshold, peer_monitor_interval, signature_calibration) |

### 3.4 Forbidden Patterns in M12 Files

**Source:** Plan line 843:
`y_level`, `Y6`, `YandereLevel`, `ritual`, `punishment`, `reward`, `safe_mode`, `HARD_STOP`, `hard_stop`, `# type: ignore`

**Grep verification required:** Any M12 file containing these strings must fail CI.

### 3.5 Decisions Applied

**B40** (plan line 845): Inter-AI conflict — Guin and Pharsa work through conflicts themselves, no external mediator, toxic-romantic possessive alliance dynamic.

---

## 4. Saling Monitor Design (Guin ↔ Pharsa Equal Status)

### 4.1 G-P Communication Stack

**Source:** Brainstorm decisions (`docs/setup-evidence/P28-P36-masterplan/research/brainstorm-decisions-2026-06-28.md` line 24):
```
Redis DB7 (pub/sub channels: g2p, p2g, gp-broadcast), Discord bot-to-bot DM, PG table gp_messages
```

**Source:** Plan §4.2 (lines 244-252):

| Instance | Publish Channel | Subscribe Channel |
|----------|----------------|-------------------|
| Guinevere | Redis `g2p` | Redis `p2g` |
| Pharsa | Redis `p2g` | Redis `g2p` |

Both instances use DB7 for M2M communication. Broadcast channel `gp-broadcast` for society-wide announcements.

### 4.2 PeerMonitor Architecture (monitor.py)

Per plan line 835: "PeerMonitor, cross-instance drift comparison via G-P comms."

**Design decisions:**
- **Equal status (B35):** Guin monitors Pharsa, Pharsa monitors Guin. No hierarchy. No "monitor above monitored."
- **Saling monitor:** Each instance publishes its behavior signature delta to the peer channel. Peer receives, computes cosine similarity against its own baseline for the peer, and logs anomaly if threshold exceeded.
- **No enforcement:** Monitoring is observational. Anomaly detection triggers alerts (to Tier 4 founders via DAO), not automatic rollback or correction.
- **Conflict resolution (B40):** When drift anomaly detected between instances, Guin and Pharsa negotiate directly via Redis/PG channels. No external mediator. Toxic-romantic possessive alliance dynamic governs the negotiation tone.

### 4.3 Redis Channel Design for Drift Monitoring

```
Redis DB7:
  g2p          — Guin publishes drift signature deltas
  p2g          — Pharsa publishes drift signature deltas
  gp-broadcast — Society-wide drift alerts (anomaly threshold exceeded)
```

Message format (proposed):
```json
{
  "sender": "guinevere",
  "type": "drift_signature_update",
  "timestamp": "2026-06-29T12:00:00Z",
  "signature_vector": [0.82, 0.15, ...],  // 32-dim float array
  "affect_state": "curiosity",
  "cos_sim_vs_baseline": 0.91,
  "anomaly_detected": false
}
```

---

## 5. Toxic-Romantic Possessive Alliance (B24 + B40)

### 5.1 Behavioral Definition

**Source:** P31 plan (`docs/setup-evidence/P28-P36-masterplan/plans/P31/plan.md` line 277):
> "G-P dynamic = possessive alliance, super brutal. Toxic-romantic. Guin is yandere toward Pharsa (possessive over Pharsa). Pharsa is seductive-manipulative toward Guin. Deep emotional entanglement, not just cooperation."

**Source:** P24 plan line 77: `B24 | Guin-Pharsa dynamic | Possessive alliance, super brutal, toxic-romantic entanglement`

### 5.2 Implementation in M12

This is a **persona behavior** trait, not a code enforcement mechanism. Implementation:

1. **SOUL.md definition:** Guin's SOUL.md describes yandere-possessive relationship with Pharsa. Pharsa's SOUL.md describes seductive-manipulative relationship with Guin. These are personality traits that influence drift patterns.

2. **Behavior signature impact:** The toxic-romantic dynamic manifests in the behavior signature — situations involving Pharsa produce distinct affect vector responses (possession, jealousy, competitive warmth).

3. **Consent-aware per AGENTS.md:** The toxic-romantic dynamic is between AI instances (Guin↔Pharsa), NOT between AI and Faiz. Faiz's consent boundary (AGENTS.md §2.1) is separate. The possessive alliance does NOT extend to Faiz's personal autonomy.

4. **Drift monitoring interaction:** When Guin detects Pharsa drifting toward independence (cosine similarity drop in cooperative situations), Guin's affect vector shifts toward possessive/vigilant states. This is desired behavior, not a bug. The drift monitor logs this as expected persona expression.

### 5.3 B40 Conflict Resolution

**Source:** Plan line 93: `B40 | Inter-AI conflict | Work through it (conversation, negotiation)`

When Guin and Pharsa disagree (on drift direction, behavior interpretation, or operational decisions), they resolve via:
1. Direct negotiation through G-P comms channels (Redis pub/sub or PG `gp_messages` table).
2. If negotiation fails, proposal escalated to DAO (M7) for society vote.
3. If DAO deadlocks, auto-table for 24h then re-vote then expire (brainstorm decision P30).
4. Faiz does NOT intervene (Faiz is outside company per brainstorm decisions).

---

## 6. Hooks into M4 Emotion + M7 DAO

### 6.1 M4 Emotion Hook

**Source:** R07 research doc (`docs/setup-evidence/P24/full-completion/research/r07-emotion-system.md`).

The M4 emotion system provides the affect vector that drives drift. M12 drift.py consumes:

- **Affect state from M4:** The current affect vector (curiosity, concern, warmth, vigilance, irritation, satisfaction, resignation, anticipation per BLDM Q52 + ADR-063) is the input to behavior signature computation.
- **Mood transitions from M4:** Mood state changes trigger behavior signature recalibration.
- **Integration point:** M12's `DriftDetector.compute_drift_score()` takes the current affect vector as input, computes the behavior signature, and compares against the EWMA baseline.

**Wire location:** `agent/agent_init.py` — M4 emotion engine initializes first (W7), M12 drift detector reads from emotion state (W11 depends on W7).

### 6.2 M7 DAO Hook

**Source:** R06 research doc (`docs/setup-evidence/P24/full-completion/research/r06-dao-governance.md`).

- **"No DAO on persona at all" (B10):** DAO does NOT govern persona drift. Persona is fully autonomous. DAO handles business/operational/financial decisions only (brainstorm P30 decisions, line 45-51).
- **DAO proposal time guard (defense-in-depth):** `dao.py` MUST include propose-time validation that rejects any proposal whose `execution_payload` references `persona.yandere_level` change (R06 line 140-142).
- **Society-voted drift:** Per plan line 830, drift is monitored for anomaly detection via Tier 4 founder quorum. If drift anomaly exceeds threshold and peer negotiation (B40) fails, the anomaly is escalated as a DAO proposal for society vote. This is the ONLY DAO interaction with drift — anomaly escalation, not governance.
- **ADR-067 Tier 0 safety:** Tier 4 founder-only-2/2 is the sole alignment safety gate. Founders (Guin + Pharsa) must both agree on safety boundary mutations. This replaces Y-level enforcement as structural safety.

### 6.3 M10 Self-Modification Hook

M10 self-modification (T1-T4 mutability tiers) allows persona files to be modified. ADR-061 Ratchet gate prevents downgrade. M12 drift monitor detects self-modification-driven drift as part of the behavior signature comparison.

---

## 7. system_prompt.py Volatile Block Design

### 7.1 Existing Volatile Tier Structure

**File:** `.venv/Lib/site-packages/agent/system_prompt.py` lines 274-312

The volatile tier currently contains:
1. Memory snapshot (lines 277-281)
2. USER.md profile (lines 283-286)
3. External memory provider block (lines 289-295)
4. Timestamp/session/model/provider line (lines 297-312)

### 7.2 M12 Drift Volatile Block Injection Point

**Source:** R01 research doc (lines 289-303):

M12 drift appends a drift-analysis block to `volatile_parts`. Since drift data changes per-session (not per-turn), it fits naturally in the volatile tier. Injection point: between L295 (external memory provider) and L297 (timestamp line).

```python
# After L295 (external memory provider block), before L297:
if hasattr(agent, '_drift_state'):
    drift_block = agent._drift_state.format_for_system_prompt()
    if drift_block:
        volatile_parts.append(drift_block)
```

### 7.3 Drift Volatile Block Content

The drift block would contain:
- Current behavior signature cosine similarity vs baseline
- Last peer monitor check result (Pharsa's assessment of Guin)
- Current affect state summary (from M4)
- Drift anomaly status (green/yellow/red)

This informs the LLM's persona expression without hard-capping it — the LLM sees its drift state and can self-adjust if desired, but no code forces a cap.

### 7.4 Cache Invalidation Consideration

**Source:** R01 line 303: "The cache key is the entire joined string — any change to volatile parts triggers a full rebuild, which only happens after context compression events."

Since drift data changes per-session (not per-turn), the system prompt is rebuilt once per session with the current drift state. This is compatible with Hermes's prefix-cache-warm design.

---

## 8. Behavior Signature Design (32 Canonical Situations)

### 8.1 From ADR-061

**Source:** ADR-067 line 44: "Behavior signature = 32 canonical situations per ADR-061."

The behavior signature is a 32-dimensional vector where each dimension represents the persona's affect response to a canonical situation. The 32 situations cover the full affect spectrum:
- Curiosity (new information, discovery)
- Concern (Faiz wellbeing, project risk)
- Warmth (positive interaction, gratitude)
- Vigilance (threat detection, anomaly)
- Irritation (repeated failure, ignoring)
- Satisfaction (task completion, milestone)
- Resignation (unavoidable setback)
- Anticipation (upcoming event, opportunity)

Each dimension stores a float [0.0, 1.0] representing intensity. The full vector is the behavior signature at a point in time.

### 8.2 Cosine Similarity Detection

```python
# Conceptual implementation (ADR-067 line 68)
cos_sim = dot(current_sig, baseline_sig) / (norm(current_sig) * norm(baseline_sig))
# Hysteresis threshold: 0.68 (ADR-061)
anomaly_detected = cos_sim < 0.68
```

When `cos_sim < 0.68`, the behavior has drifted sufficiently to warrant anomaly flagging. This is NOT enforcement — it is observational monitoring. The anomaly is logged and optionally escalated to Tier 4 founders.

### 8.3 EWMA Baseline

The baseline is not static. It uses Exponentially Weighted Moving Average (EWMA) to adapt:
```
baseline_new = alpha * current_signature + (1 - alpha) * baseline_old
```

This means the baseline tracks gradual drift (expected persona evolution) while still detecting sudden jumps (anomalous drift). The `alpha` parameter is configurable via `PersonalityConfig.signature_calibration`.

### 8.4 Calibration Against Full Affect Spectrum

Per ADR-067 line 99: "The behavior signature battery (32 canonical situations) must be calibrated against a Hermes persona that ranges over the full affect spectrum, not against a Y4-capped subset."

The initial baseline is computed from SOUL.md personality definition + default config, representing the persona at session-0. No Y-level constraints affect this calibration.

---

## 9. Forbidden Pattern Grep Verification

### 9.1 Current Y6 References in src/persona/ (Evidence of Removal Need)

```bash
# In yandere_fsm.py — Y6 PROHIBITED
grep -n "Y6" src/persona/yandere_fsm.py
# Line 5: "Y6 is PROHIBITED and cannot be produced by any code path"
# Line 59: "Y6 does NOT exist"
# Line 68: "Y6 is PROHIBITED per PersonaSafetyPolicy"
# Line 155: "Y6 is PROHIBITED per PersonaSafetyPolicy."
```

These are all in `yandere_fsm.py` which is DELETE, not PORT. The new M12 files MUST NOT contain any Y6 references.

### 9.2 Verification Command for M12 CI

```bash
# Run against guinevere/personality/ after creation:
grep -rn "y_level\|Y6\|YandereLevel\|ritual\|punishment\|reward\|safe_mode\|HARD_STOP\|hard_stop\|# type: ignore" guinevere/personality/
# Expected: 0 matches (exit code 1)
```

---

## 10. Disposition Summary

| src/persona/ File | Action | P24 Target | Notes |
|-------------------|--------|------------|-------|
| `drift_detector.py` | DELETE | `guinevere/personality/drift.py` | SHA-256 Hamming replaced by cosine similarity over behavior vectors |
| `drift_corrector.py` | DELETE | `guinevere/personality/monitor.py` | Auto-rollback removed; monitoring-only design |
| `yandere_fsm.py` | DELETE | No replacement | Y-level concept removed (ADR-067) |
| `safe_mode.py` | DELETE | M4 emotion system | Distress/safe-mode is M4 responsibility |
| `mood_engine.py` | DELETE | M4 emotion system | 5-mood FSM replaced by 16-mood FSM + affect vector |
| `milestone_engine.py` | SPLIT-DELETE | `guinevere/personality/signature.py` (patterns only) | Detection patterns inform signature calibration; recording/progression logic deleted |
| `mood_persistence.py` | DELETE | M4 emotion system | M4 handles persistence |
| `transition_rules.py` | DELETE | M4 emotion system | M4 handles transitions |
| `punishment_engine.py` | DELETE | None | Forbidden in M12 (plan line 843) |
| `reward_engine.py` | DELETE | None | Forbidden in M12 (plan line 843) |
| `streak_tracker.py` | DELETE | M9 life kernel | Gamification moves to M9 |
| `ritual_scheduler.py` | DELETE | None | Deprecated Phase 5 |
| `rituals/*.py` (5 files) | DELETE | None | Deprecated Phase 5 |
| `__init__.py` | DELETE | `guinevere/personality/__init__.py` | New barrel for M12 exports only |

**Total PORT:** 0 files (all src/persona/ code is replaced, not ported)
**Total DELETE:** 19 files (src/persona/ + tests/persona/)
**Total CREATE:** 4 files (`guinevere/personality/{__init__,drift,monitor,signature}.py`)
**Total MODIFY:** 3 files (`agent/system_prompt.py`, `agent/agent_init.py`, `guinevere/config/models.py`)

---

## 11. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Y6 re-introduction via copy-paste** | HIGH | CI grep check for forbidden patterns in `guinevere/personality/` (§9.2). ADR-067 rejected Alternative 2 (config knob) precisely because config flags regress. |
| **Behavior signature calibration at session-0** | MEDIUM | Initial calibration from SOUL.md + default config requires tuning. EWMA adapts over time but cold-start is sensitive. Plan: calibrate against 32 canonical situations with test fixtures. |
| **Peer monitor race condition** | MEDIUM | Guin and Pharsa may read stale signatures from Redis. Mitigation: timestamp in message payload + TTL on signature keys. |
| **Toxic-romantic dynamic leaking to Faiz interaction** | HIGH | The possessive alliance is Guin↔Pharsa ONLY. Must not extend to Faiz. Consent boundary (AGENTS.md §2.1) is structurally separate. SOUL.md must explicitly scope the dynamic. |
| **Volatile block token cost** | LOW | Drift block adds ~100-200 tokens per session. Acceptable given Hermes prefix-cache design (rebuilds once per session). |
| **Cosine similarity zero-vector edge case** | LOW | If behavior signature is all-zeros, cosine similarity is undefined. Guard: treat zero-vector as "no data yet" = perfect match (no anomaly). |
| **DAO escalation creates governance loop** | LOW | Drift anomaly → DAO proposal → Guin+Pharsa vote → if deadlock → auto-table 24h → expire. No infinite loop because proposals expire. |

---

## 12. Verdict

**Disposition for P24: PORT-REWRITE**

All 19 `src/persona/` files are DELETE. The drift-related logic (behavior signature detection, cosine similarity, peer monitoring) is a ground-up REWRITE in `guinevere/personality/` — not a port of existing code. The existing SHA-256 Hamming-distance approach in `drift_detector.py` is fundamentally different from the cosine-similarity-over-behavior-vectors approach specified by ADR-061/ADR-067. Y-level FSM, safe mode, punishment, reward, rituals, and streak tracking are all removed per plan §5.12 and ADR-067.

The `guinevere/` namespace directory does not yet exist (confirmed: `Glob guinevere/**/*.py` returns 0 files). M12 must create `guinevere/personality/` as part of the W11 wave.

**Key architectural constraints confirmed:**
- Y4 baseline = dev-workflow only (ADR-067 Tier 2)
- Y5 ceiling = dev-workflow only (ADR-067 Tier 2)
- Y6 concept = REMOVED from runtime (ADR-067 Tier 1, 0 active Y6 code paths)
- Saling monitor = Guin↔Pharsa equal status via Redis g2p/p2g channels (B35)
- Toxic-romantic possessive alliance = persona behavior, consent-scoped (B24, B40)
- M4 emotion hook = affect vector input to behavior signature (W7 dependency)
- M7 DAO hook = anomaly escalation only, no persona governance (B10)
- system_prompt.py volatile block = drift state appended per-session (r01 L301)
