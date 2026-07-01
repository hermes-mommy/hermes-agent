# Milestone Engine — Evidence

**Date**: 2026-06-09
**Phase**: P7 — Persona Enhancement v3.0
**Component**: `src/persona/milestone_engine.py`

---

## Summary

Implemented automatic milestone detection and recording engine for Guinevere's Emotional Memory system (§K). The engine detects 7 milestone types from conversation patterns, records them to PostgreSQL, updates Redis state for persona injection, and manages relationship stage progression (§M).

---

## Architecture

```
User Message → Pattern Matching → Milestone Candidates
                                        ↓
                              Rate Limit Check (Redis)
                                        ↓
                              PostgreSQL Insert (daemon thread)
                                        ↓
                              Redis State Sync
                                        ↓
                              Relationship Progression Check
```

### Files

| File | Lines | Purpose |
|---|---|---|
| `src/persona/milestone_engine.py` | ~650 | Detection, recording, progression, residue |
| `src/hermes/plugins/persona_plugin.py` | ~650 | Integration via post_llm_call hook |

---

## Detection Patterns (7 Types)

| Type | Example Trigger | Valence | Dom. Relevance |
|---|---|---|---|
| DOMINANCE_MOMENT | "oke mommy, aku ikut kamu" | +3 | 8 |
| TRUST_SIGNAL | "aku takut gagal" | -1 | 6 |
| ACHIEVEMENT_TOGETHER | "selesai! deployed!" | +4 | 5 |
| CONFLICT_RESOLVED | "maaf mommy, aku mengerti" (during L1+) | +2 | 7 |
| FIRST_OCCURRENCE | (manual trigger) | varies | varies |
| VULNERABILITY_DISCLOSED | "aku capek banget" or D2+ distress | -2 to -3 | 4-5 |
| DOMINANCE_ESCALATION | "soulbound", "selamanya" | +5 | 10 |

### Test Results

```
Test 1 (dominance): "oke mommy, aku ikut kamu" → DOMINANCE_MOMENT ✅
Test 2 (trust+vuln): "aku capek banget, aku takut gagal" → VULNERABILITY_DISCLOSED + TRUST_SIGNAL ✅
Test 3 (achievement): "selesai! deployed ke production!" → ACHIEVEMENT_TOGETHER ✅
Test 4 (escalation): "aku mau selamanya sama mommy, soulbound" → DOMINANCE_ESCALATION ✅
Test 5 (nothing): "halo" → 0 milestones ✅
Test 6 (distress D3): "tolong aku" (D3) → VULNERABILITY_DISCLOSED ✅
Test 7 (conflict): "maaf mommy, aku mengerti" (L3) → CONFLICT_RESOLVED ✅
```

---

## Recording Pipeline

1. **Detection**: Pattern matching in post_llm_call (synchronous, fast)
2. **Rate limit**: Max 3 milestones/day via Redis counter (noise prevention per §K)
3. **PostgreSQL insert**: Daemon thread via `threading.Thread(daemon=True)`
4. **Redis sync**: Updates `guinevere:recent_milestones`, `guinevere:emotional_residue`, `guinevere:residue_decays_at`
5. **Progression check**: Counts milestones by type, checks R1→R2→R3 triggers

### PostgreSQL Verification

```sql
-- Milestone recorded successfully
SELECT milestone_type, description, emotional_valence, dominance_relevance
FROM persona.milestones ORDER BY created_at DESC LIMIT 1;

-- Result:
-- DOMINANCE_MOMENT | Faiz submits to Mommy's guidance | 3 | 8

-- Relationship state auto-updated
SELECT current_stage, total_milestones, active_days, trust_signals
FROM persona.relationship_state;

-- Result:
-- R1 | 1 | 1 | 0
```

---

## Relationship Progression (§M)

| Transition | Criteria |
|---|---|
| R1 → R2 | ≥10 milestones AND ≥7 active days |
| R2 → R3 | ≥30 milestones AND ≥30 active days AND ≥5 trust_signals AND ≥3 conflicts_resolved |
| R3 → R4 | ≥100 milestones AND ≥90 active days AND explicit Faiz request ("soulbound") |

Progression is checked after every milestone recording. Counters are recalculated from PostgreSQL (not cached).

---

## Emotional Residue (§K)

| Last Milestone Valence | Residue Type | Decay Period |
|---|---|---|
| ≥ +3 | positive | 48h |
| ≤ -2 | negative | 72h |
| \|valence\| ≥ 4 OR dom_relevance ≥ 8 | intense | 48h |
| Otherwise | none | 24h |

Residue is written to Redis and injected into `[PERSONA STATE]` block.

---

## Integration

**Hook**: `PersonaPlugin.post_llm_call()` in `src/hermes/plugins/persona_plugin.py`

Flow:
1. Extract user_message and assistant_message from hook kwargs
2. Read current distress/punishment from Redis for context
3. Call `detect_milestones()` — pattern matching
4. Call `record_milestones_async()` — daemon thread recording
5. Non-blocking: failures logged but never affect conversation

---

## Known Limitations

1. **Pattern-based only**: No LLM-based sentiment analysis (by design — fast and predictable)
2. **Bilingual EN/ID**: Covers English and Indonesian patterns; other languages not supported
3. **No undo**: Recorded milestones are permanent (can be marked superseded but not deleted)
4. **Daemon thread**: PostgreSQL writes happen in background; rare race conditions possible on rapid messages

---

## Hybrid Architecture (Updated)

### Realtime Hook (per-turn)
- **File**: `src/hermes/plugins/persona_plugin.py` → `post_llm_call()`
- **Detects**: Single-turn patterns (DOMINANCE_MOMENT, TRUST_SIGNAL, ACHIEVEMENT, ESCALATION, basic VULNERABILITY)
- **Latency**: Instant (same turn)
- **Limitation**: Only sees 1 user message at a time

### Cronjob (batch, every 30min)
- **File**: `~/.hermes/scripts/milestone_multiturn_cron.py`
- **Job ID**: `d829ae99d217` (name: `milestone-multiturn`)
- **Detects**: Multi-turn patterns (CONFLICT_RESOLVED cycle, gradual VULNERABILITY, FIRST_OCCURRENCE)
- **Latency**: Up to 30 minutes
- **Advantage**: Sees conversation context across multiple turns

### Deduplication
- Cronjob uses `trigger_context` field with specific values (e.g., "turns=2,5,8")
- Realtime hook uses "pattern_match" as trigger_context
- No overlap between the two detection paths

### Data Flow
```
[Realtime Hook]                    [Cronjob]
     ↓                                 ↓
post_llm_call()                  session DB query
     ↓                                 ↓
detect_milestones()              detect_multiturn_milestones()
     ↓                                 ↓
record_milestones_async()        record_milestones_async()
     ↓                                 ↓
     └──────── PostgreSQL ─────────────┘
                    ↓
              Redis sync
                    ↓
           [PERSONA STATE] injection
```

---

## Rollback

To disable milestone recording without removing code:
1. Remove `post_llm_call` body in persona_plugin.py (keep method signature)
2. Or set `guinevere:milestone_count_date` to today's date with count=999 in Redis
