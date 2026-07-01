# P18 — Advanced Memory Implementation Plan

**Status:** 📋 PLANNING
**Date:** 2026-06-18
**Strategy:** Merge P18 into P3 (Memory System)
**Scope:** MVP (4 steps) → Phase 2 (2 steps) → Phase 3 (evaluate)

---

## §1 Executive Summary

P18 extends the production-ready P3 Memory System with:
- **FSRS-6** spaced repetition algorithm (replaces simple decay)
- **3-tier memory hierarchy** (Working / Episodic / Semantic)
- **6h consolidation cycle** (from daily 03:00)
- **Active forgetting** with threshold 0.1 + salience floor
- **Reconsolidation-on-retrieval** hook
- **Discord memory commands** for operator control

**Decision:** Merge into P3 (`src/memory/`) rather than create separate `src/memory/advanced/`. P3 already has 35% of P18 features; the remaining 65% extends existing modules.

---

## §2 Decisions Locked (from benchmark research)

| Decision | Choice | Rationale |
|---|---|---|
| Spaced repetition algorithm | **FSRS-6** | 99.6% win rate vs SM-2, 41% lower log loss, `pip install fsrs` v6.3.1, MIT, 22.8kB |
| Memory tiers | **3 tiers** (Working/Episodic/Semantic) | CoALA-aligned, HMAT +14-22%, TierMem saves 54% tokens |
| Consolidation interval | **6 hours** | $0.08/mo vs $0.48/mo hourly, Letta warns hourly has diminishing returns |
| Active forgetting threshold | **0.1 + salience floor + 90-day grace** | Conservative, YourMemory uses 0.05 but 0.1 safer for production |
| Scope | **4-step MVP first** | P18-001, P18-002, P18-004, P18-008 |

---

## §3 MVP Steps (4 steps)

### P18-001: Memory Tier Schema + FSRS Migration

**Goal:** Add tier classification and FSRS state to Episodes table.

**Files to modify:**
- `src/memory/models.py` — Add columns to Episodes model
- `migrations/versions/p18_tier_fsrs_schema.py` — Alembic migration (NEW)

**Columns to add to `episodes` table:**
```python
# Tier classification
tier = Column(String(20), default='episodic', index=True)  # working/episodic/semantic

# FSRS-6 state
fsrs_state = Column(JSONB, nullable=True)  # Full FSRS state dict
last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
next_review_at = Column(DateTime(timezone=True), nullable=True, index=True)
retrievability = Column(Float, nullable=True)  # 0.0 - 1.0
stability = Column(Float, nullable=True)  # days
difficulty = Column(Float, nullable=True)  # 0.0 - 10.0

# Forgetting
salience_score = Column(Float, default=1.0)  # Multi-factor importance
last_accessed_at = Column(DateTime(timezone=True), nullable=True)
access_count = Column(Integer, default=0)
```

**New module:**
- `src/memory/tiers.py` — TierManager class with tier transition rules

**Tier transition rules:**
| From | To | Trigger |
|---|---|---|
| working | episodic | After 24h + importance >= 5 |
| episodic | semantic | After 3+ retrievals + FSRS stability > 30 days |
| semantic | (archived) | After 90 days no access + retrievability < 0.1 |
| working | (deleted) | After 24h + importance < 3 + no retrieval |

**Dependencies:** None (first step)
**Estimated effort:** 2-3 hours

---

### P18-002: Decay & Consolidation Scheduler (6h cycle + FSRS)

**Goal:** Replace daily 03:00 consolidation with 6h cycle + FSRS-based decay + active forgetting.

**Files to modify:**
- `src/memory/consolidation.py` — Change schedule, add FSRS integration
- `src/memory/spaced_repetition.py` — NEW module wrapping FSRS library

**Changes to consolidation.py:**
1. Change APScheduler from `cron(hour=3)` to `interval(hours=6)`
2. Add FSRS review step: for each memory with `next_review_at <= now`, run FSRS review
3. Add active forgetting: prune memories with `retrievability < 0.1` AND `salience_score < 0.1` AND `last_accessed_at > 90 days ago`
4. Add tier transition step: promote working→episodic, episodic→semantic per rules

**New module: `src/memory/spaced_repetition.py`:**
```python
from fsrs import FSRS, Rating

class SpacedRepetitionService:
    def __init__(self):
        self.fsrs = FSRS()
    
    async def review(self, episode: Episode, rating: Rating) -> dict:
        """Run FSRS review, return updated state."""
        
    async def get_retrievability(self, episode: Episode) -> float:
        """Calculate current retrievability without review."""
        
    async def schedule_next_review(self, episode: Episode) -> datetime:
        """Calculate next review date from FSRS state."""
```

**Rating mapping:**
| User action | FSRS Rating |
|---|---|
| Memory recalled successfully | Rating.Good (3) |
| Memory recalled with difficulty | Rating.Hard (2) |
| Memory not recalled | Rating.Again (1) |
| Memory recalled easily | Rating.Easy (4) |

**Dependencies:** P18-001 (needs tier + FSRS columns)
**Estimated effort:** 3-4 hours

---

### P18-004: Memory Review/Edit Discord Commands

**Goal:** Operator-facing memory control via Discord slash commands.

**Files to create:**
- `src/discord/commands/memory.py` — NEW file with memory commands

**Commands:**
| Command | Description |
|---|---|
| `/memory list [tier] [limit]` | List recent memories, filterable by tier |
| `/memory view <id>` | View full memory details + FSRS state |
| `/memory edit <id> <field> <value>` | Edit memory field (summary, importance, tags) |
| `/memory delete <id>` | Soft-delete memory (set do_not_recall=True) |
| `/memory purge --older-than <days>` | Bulk archive old memories |
| `/memory stats` | Show tier distribution, FSRS health, decay stats |
| `/memory review` | Show memories due for review (next_review_at <= now) |

**Integration:** Register in `src/discord/bot.py` command tree.

**Dependencies:** P18-001 (needs tier + FSRS columns to query)
**Estimated effort:** 3-4 hours

---

### P18-008: Reconsolidation-on-Retrieval Hook

**Goal:** When a memory is retrieved, update its FSRS state and potentially reconsolidate.

**Files to modify:**
- `src/memory/read_pipeline.py` — Add post-retrieval hook
- `src/memory/spaced_repetition.py` — Add reconsolidation logic

**Logic:**
```python
# After recall_memories() returns results:
for episode in retrieved_episodes:
    # Update access metadata
    episode.last_accessed_at = datetime.now()
    episode.access_count += 1
    
    # Run FSRS review with implicit "Good" rating
    sr_service = SpacedRepetitionService()
    await sr_service.review(episode, Rating.Good)
    
    # Update retrievability
    episode.retrievability = await sr_service.get_retrievability(episode)
    
    # If high importance + high retrieval count, consider tier promotion
    if episode.access_count >= 3 and episode.stability > 30:
        await tier_manager.consider_promotion(episode)
```

**Dependencies:** P18-001 + P18-002 (needs SR service + columns)
**Estimated effort:** 2-3 hours

---

## §4 Phase 2 Steps (deferred)

### P18-003: Proactive Recall Hook into Agent Loop
**Goal:** Trigger memory recall based on context signals (location, time, topic).
**Status:** Deferred to Phase 2

### P18-005: Recall Precision + Latency Evaluation
**Goal:** Evaluation harness for recall quality metrics.
**Status:** Deferred to Phase 2

---

## §5 Phase 3 Steps (evaluate after Phase 2)

### P18-006: Meta-Memory Self-Reflection
**Goal:** Memory system that reflects on its own memory patterns.
**Status:** Evaluate after Phase 2

### P18-007: Context Window Budget Manager
**Goal:** Dynamic context allocation based on task importance.
**Status:** Evaluate after Phase 2

---

## §6 Execution Order

```
P18-001 (schema + migration)
    ↓
P18-002 (consolidation + SR)
    ↓
┌─────────────┬─────────────┐
│  P18-004    │  P18-008    │
│  (Discord)  │  (reconsolidation) │
└─────────────┴─────────────┘
```

**Collision scan:**
- `src/memory/models.py` — modified by P18-001 only ✓
- `src/memory/consolidation.py` — modified by P18-002 only ✓
- `src/memory/read_pipeline.py` — modified by P18-008 only ✓
- `migrations/versions/` — P18-001 creates migration file ✓
- New files (tiers.py, spaced_repetition.py, memory.py) — no collision ✓

**Parallel opportunities:** P18-004 and P18-008 can run in parallel after P18-002.

---

## §7 Dependencies & Prerequisites

### External Dependencies
```toml
# Add to pyproject.toml
[project.dependencies]
fsrs = "^6.3.1"  # FSRS-6 spaced repetition
```

### Database Prerequisites
- PostgreSQL with `pgvector` extension (already installed)
- Alembic migration framework (already configured)
- Existing `episodes` table from P3

### Runtime Prerequisites
- P3 Memory System fully operational ✓
- P8 Observability baseline ✓
- P16 Knowledge Graph (optional integration) ✓

---

## §8 Verification Scaffold

### Per-Step Verification Commands

**P18-001:**
```bash
# Migration runs successfully
alembic upgrade head

# New columns exist
psql -c "SELECT column_name FROM information_schema.columns WHERE table_name='episodes' AND column_name LIKE '%tier%' OR column_name LIKE '%fsrs%' OR column_name LIKE '%retrievability%';"

# Models import cleanly
python -c "from src.memory.models import Episodes; print(Episodes.__table__.columns.keys())"
```

**P18-002:**
```bash
# FSRS library imports
python -c "from fsrs import FSRS, Rating; print('FSRS OK')"

# Spaced repetition service instantiates
python -c "from src.memory.spaced_repetition import SpacedRepetitionService; s = SpacedRepetitionService(); print('SR OK')"

# Consolidation scheduler starts with new interval
python -c "from src.memory.consolidation import scheduler; print([j.trigger for j in scheduler.get_jobs()])"
```

**P18-004:**
```bash
# Discord commands register
python -c "from src.discord.commands.memory import setup_memory_commands; print('Commands OK')"

# Bot starts without errors
python -m src.discord.bot --dry-run
```

**P18-008:**
```bash
# Read pipeline imports hook
python -c "from src.memory.read_pipeline import recall_memories; print('Pipeline OK')"

# Full integration test
python -c "
import asyncio
from src.memory.read_pipeline import recall_memories
result = asyncio.run(recall_memories('test query', limit=1))
print(f'Retrieved: {len(result)} memories')
"
```

### Forbidden Patterns (must return zero matches)
```bash
grep -r "as any" src/memory/
grep -r "@ts-ignore" src/memory/
grep -r "# type: ignore" src/memory/
grep -r "except:" src/memory/  # bare except
grep -r "except Exception:" src/memory/  # catch-all without logging
```

---

## §9 Evidence Paths

| Step | Evidence Path |
|---|---|
| P18-001 | `docs/setup-evidence/P18/evidence/p18-001-schema-migration.md` |
| P18-002 | `docs/setup-evidence/P18/evidence/p18-002-consolidation-sr.md` |
| P18-004 | `docs/setup-evidence/P18/evidence/p18-004-discord-commands.md` |
| P18-008 | `docs/setup-evidence/P18/evidence/p18-008-reconsolidation.md` |
| Final | `docs/setup-evidence/P18/evidence/p18-final-verification.md` |

---

## §10 Auditor Matrix

| Auditor | Scope |
|---|---|
| Code Quality | Type safety, error handling, async patterns |
| Security | No secrets, proper access control on Discord commands |
| Performance | Query optimization, batch processing, index usage |
| Memory Safety | No data loss, proper transaction handling, rollback safety |
| Integration | P3 compatibility, P16 KG hook, P8 observability |

---

## §11 Rollback Plan

### Database Rollback
```bash
# If migration fails
alembic downgrade -1

# Full rollback
alembic downgrade base
```

### Code Rollback
- All changes in `src/memory/` — revert via git
- New files can be deleted without affecting existing code
- `src/discord/commands/memory.py` — delete file, remove import from bot.py

### Data Safety
- **No destructive deletes** — all "delete" operations are soft deletes (do_not_recall=True)
- **Migration is additive** — only adds columns, never drops
- **Backfill is optional** — new columns are nullable, existing data unaffected

---

## §12 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| FSRS library incompatible with async | Low | Medium | Wrapper layer isolates FSRS calls |
| Migration fails on production data | Low | High | Staging test first, rollback plan |
| Discord command conflicts | Low | Low | Unique command names, proper registration |
| Performance degradation on large datasets | Medium | Medium | Indexes on tier, next_review_at; batch processing |
| Memory tier transition logic bugs | Medium | Medium | Comprehensive unit tests, staging validation |

---

## §13 Success Criteria

### MVP Complete When:
- [ ] P18-001: Migration runs, models have new columns
- [ ] P18-002: Consolidation runs every 6h with FSRS + active forgetting
- [ ] P18-004: All 7 Discord commands work
- [ ] P18-008: Retrieved memories get FSRS updates
- [ ] All forbidden patterns return zero matches
- [ ] `lsp_diagnostics` clean on all modified files
- [ ] Evidence files created for each step
- [ ] Auditor gates pass

### Production Ready When:
- [ ] Deployed to VPS
- [ ] 6h consolidation cycle running
- [ ] Discord commands accessible to operator
- [ ] No errors in observability dashboards for 24h
- [ ] Documentation updated (P18 README, CHECKLIST, IMPLEMENTATION_GUIDE)

---

## §14 Footer

### Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-18 | Guinevere | Initial plan from benchmark research + P3 codebase analysis |

### Approval

Pending Faiz approval for implementation start.
