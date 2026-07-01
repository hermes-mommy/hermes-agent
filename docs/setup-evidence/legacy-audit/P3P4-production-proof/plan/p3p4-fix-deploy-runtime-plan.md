# P3P4 Fix-Deploy-Runtime Plan

**Date:** 2026-06-27
**Author:** Guinevere (orchestrator)
**Status:** READY FOR IMPLEMENTATION

---

## Current State Assessment

### What's Already Done (from previous session)

| Item | Status | Notes |
|------|--------|-------|
| B1: SemanticFacts ORM project_id/project_scope | ✅ DONE | columns added to model |
| B2: consolidation project_id extraction | ✅ DONE | falls back to DEFAULT_PROJECT_ID |
| B3: store_episode_batch project forwarding | ✅ DONE | _opt_uuid_field helper added |
| B4: EmbeddingService wired in life-kernel | ✅ DONE | src/core/main.py |
| B5: embedding_backfill.py created | ✅ DONE | idempotent batch job |
| C1: PersonaPlugin consent check | ✅ DONE | fail-closed |
| C2: PersonaPlugin HARD STOP check | ✅ DONE | fail-closed via defense-in-depth |
| C4: prompt_loader live mood | ✅ DONE | _get_live_mood() from Redis DB5 |
| C9: YandereEngine persist() | ✅ DONE | write_yandere_state helper |

### What Still Needs Fixing (from audit round 1)

| # | ID | Severity | Description | Lane |
|---|---|----------|-------------|------|
| 1 | F-CC-03/F-CC-01 | **CRITICAL** | Consent revoke only publishes to pub/sub — no subscriber reacts | C |
| 2 | F-SP-08 | **HIGH** | G10 doesn't trigger on consent revocation (only on SafeModeController) | C |
| 3 | F-SM-03 | MEDIUM | DistressDetector not wired to Discord on_message | C |
| 4 | KI-04 | MEDIUM | StreakTracker not wired — must be wired or formally deprecated | C |
| 5 | F-01 | MEDIUM | ORM nullable=True vs DB NOT NULL (cosmetic — write pipeline already guards) | B |
| 6 | F-10 | MEDIUM | No index on project_id columns (performance, not blocking) | B |
| 7 | F-05 | LOW | O(N²) fact dedup (performance, not blocking) | B |

---

## Atomic Steps

### Step 1: Consent Revocation Subscriber (CRITICAL — Lane C)
**Goal:** When `/consent action:revoke` fires, all running persona/surveillance consumers must react deterministically within one event cycle.
**Approach:** Implement a `ConsentRevocationHandler` that:
- Reads `consent:grants` from Redis on every relevant check (already done by PersonaPlugin)
- Provides a shared `_consent_revoked_at` timestamp in Redis that consumers check
- Writes a PostgreSQL audit row on revoke
- Activates SafeModeController on persona consent revoke (satisfying F-SP-08)
**Files to modify:**
- `src/discord/cmd_consent.py` — add SafeModeController activation + PG audit
- NEW: `src/consent/revocation_handler.py` — shared consent state
- `src/hermes/plugins/persona_plugin.py` — check revocation timestamp
**Tests to add:**
- `test_consent_revoke_activates_safe_mode`
- `test_consent_revoke_writes_pg_audit`
- `test_consent_revoke_blocks_persona_plugin`
**Forbidden patterns:** bare `except: pass`, no audit trail

### Step 2: Wire DistressDetector to Discord (MEDIUM — Lane C)
**Goal:** Distress detection happens on every incoming message.
**Approach:** In the Hermes message handler (or safety_plugin pre_llm_call), run DistressDetector on user input and activate SafeModeController on D2+.
**Note:** The safety_plugin.py ALREADY does distress detection in G03 (lines 728-742 of safety_plugin.py). The `DistressDetector` in `src/persona/safe_mode.py` is a SEPARATE implementation. The safety_plugin is the authoritative runtime path. The `DistressDetector` class is the standalone unit-test-friendly version. The wiring gap is that `DistressDetector` is not used as a separate path because `safety_plugin` already handles it.
**Resolution:** Document that distress detection IS already wired via `safety_plugin.pre_llm_call` G03. Formally deprecate the standalone `DistressDetector` as a test-only utility. Add explicit documentation.
**Files to modify:**
- `src/persona/safe_mode.py` — add deprecation docstring to DistressDetector class
- `src/persona/__init__.py` — update docstring noting safety_plugin is the runtime path
**Forbidden:** Do not add a second distress detection path (would create double-detection)

### Step 3: Wire or Deprecate StreakTracker (MEDIUM — Lane C)
**Goal:** StreakTracker is either actively wired or formally deprecated.
**Current state:** StreakTracker exists in `src/persona/streak_tracker.py` but is not imported by any runtime consumer.
**Decision:** WIRE it to PersonaPlugin. The streak count is a persona state that should be injected into the `[PERSONA STATE]` block.
**Approach:** Read streak from Redis DB5 (key: `guinevere:streak_count`) in `_read_persona_state()`. Add to persona block format.
**Files to modify:**
- `src/hermes/plugins/persona_plugin.py` — add `_KEY_STREAK_COUNT`, read in pipeline, add to `_format_persona_block()`
**Tests to add:**
- `test_persona_block_includes_streak_count`

### Step 4: ORM Nullable Cleanup (MEDIUM — Lane B)
**Goal:** ORM matches live DB schema — `project_id` should be `nullable=False` after P19-002.
**NOTE:** This is risky — changing ORM to nullable=False would break any test that creates Episodes without project_id. The write_pipeline already auto-fills DEFAULT_PROJECT_ID, so all production writes are safe. The ORM nullable=True is DEFENSIVE — it allows tests and legacy code to work.
**Decision:** KEEP ORM nullable=True. The write pipeline guard (auto-fallback to DEFAULT_PROJECT_ID) is the enforcement layer. Adding a DB-level comment update via migration is better.
**Action:** Document the decision. No code change needed.

### Step 5: PostgreSQL Audit Log for Consent (HIGH — Lane C)
**Goal:** Consent grant/revoke writes to `consent.consent_ledger` table (authoritative).
**Approach:** In `cmd_consent.py`, after Redis write, also insert/update `consent.consent_ledger` via async session.
**Files to modify:**
- `src/discord/cmd_consent.py` — add PG write after Redis write
**Forbidden:** Blocking Redis write on PG failure (Redis is the hot path, PG is the audit trail)

### Step 6: Local Verification (GATE)
Run all tests:
- `python -m pytest tests/memory/ tests/persona/ tests/life_kernel/ -v`
- Expect: ≥1859 passed, ≤1 pre-existing failure
- Zero new failures

### Step 7: Deploy Plan (requires VPS access)
1. `scp` changed files to VPS
2. `sudo systemctl restart guinevere-core` (only if core files changed)
3. Verify `systemctl status guinevere-core` → active
4. Check journalctl for errors
5. Verify P20 heartbeat still alive (NRestarts=0)
6. Test consent revoke via Discord
7. Verify logs show consent check

### Step 8: Runtime Proof (requires VPS access)
- Lane B: Trigger consolidation dry-run, verify project_id in SemanticFacts
- Lane C: Revoke consent, verify PersonaPlugin stops injecting
- P20: Check dashboard, heartbeat, brain status

---

## Parallelism Map

```
Step 1 (consent subscriber) ──┐
Step 2 (distress docs)        ├── parallel (no file overlap)
Step 3 (streak wiring)  ──────┘
                              │
Step 5 (PG audit log) ────────┘  (depends on Step 1 for cmd_consent.py)
                              │
Step 4 (ORM docs) ────────────┘  (independent)
                              │
Step 6 (tests) ─────────────── ALL must pass before deploy
                              │
Step 7+8 (deploy+runtime) ──── VPS access required
```

## Collision Scan

| File | Steps | Collision |
|------|-------|-----------|
| `src/discord/cmd_consent.py` | 1, 5 | SEQUENTIAL (Step 1 first, then Step 5) |
| `src/hermes/plugins/persona_plugin.py` | 3 | Only Step 3 touches this |
| `src/persona/safe_mode.py` | 2 | Only Step 2 touches this |
| `src/persona/__init__.py` | 2 | Only Step 2 touches this |

## Rollback Plan

```bash
git diff --stat HEAD  # see what changed
git stash             # revert all
# Restart service to restore previous code
sudo systemctl restart guinevere-core
```

## Evidence Requirements

| Step | Evidence Path |
|------|---------------|
| 1 | `implementation/lane-c-consent-subscriber.md` |
| 2 | `implementation/lane-c-distress-docs.md` |
| 3 | `implementation/lane-c-streak-wiring.md` |
| 4 | `implementation/lane-b-orm-docs.md` |
| 5 | `implementation/lane-c-pg-audit-log.md` |
| 6 | `verification/local-verification.md` |
| 7 | `deploy/backup-and-deploy-evidence.md` |
| 8 | `runtime/lane-b-memory-runtime-proof.md`, `runtime/lane-c-persona-consent-runtime-proof.md` |
