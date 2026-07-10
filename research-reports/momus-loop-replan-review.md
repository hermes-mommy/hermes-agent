# Momus Review: Consciousness Loop Replan + Discord Channel Refactor

> **Reviewer**: Momus (plan review agent)
> **Date**: 2026-07-10
> **Plan**: `docs/superpowers/plans/2026-07-10-consciousness-loop-replan.md`
> **Research inputs**: `research-reports/consciousness-loop-current.md`, `research-reports/discord-bot-current.md`
> **Verdict**: **REVIEW — conditional pass with 3 blockers and 5 significant gaps**

---

## 1. Overall Assessment

This is a well-structured plan with clear scope, solid research grounding, and a sensible dependency map. The 8-step execution order is logical, the collision scan is thorough, and the design decisions align with the user's stated preferences. A capable developer could start work on most steps immediately.

However, **3 issues are genuine blockers** that would halt execution, and **5 gaps** would cause confusion or rework if not addressed before implementation begins.

---

## 2. Verdict: BLOCKERS (must fix before implementation)

### BLOCKER 1: A1 scaffold references non-existent test directory

**Plan says** (Verification Scaffold, A1):
```
python -m pytest tests/consciousness/ -v -x --timeout=30
```

**Reality**: `tests/consciousness/` does not exist. All consciousness tests live in `tests/p24/test_consciousness*.py` (3 files: `test_consciousness.py`, `test_consciousness_delegate.py`, `test_consciousness_live.py`).

**Impact**: The scaffold command fails immediately. Implementer cannot verify A1 completion. The scaffold's "Hard Rejection" criteria cannot be evaluated.

**Fix**: Change to `python -m pytest tests/p24/test_consciousness.py tests/p24/test_consciousness_delegate.py -v -x --timeout=30`. Or create `tests/consciousness/` as a pre-step and migrate tests there.

---

### BLOCKER 2: Dual wiring path not reconciled — server.py AND agent_init.py both create ConsciousnessLoop

The plan's Phase A file map lists:
- `guinevere/consciousness/wire.py` — MODIFY
- `guinevere/consciousness/loop.py` — REWRITE

But the codebase has **two independent wiring paths**:

1. **`server.py` (lines 123-144)**: Creates its own `AIAgent` brain, constructs `ConsciousnessLoop(llm_router=, settings=)`, calls `on_session_start()`, spawns `loop.run()` as `m3-consciousness` task inside an `asyncio.TaskGroup`.

2. **`agent_init.py` (lines 1764-1769)**: Calls `wire.wire(agent)` which creates a SECOND `ConsciousnessLoop` using `agent._llm_router`, attaches it as `agent._consciousness_loop`.

The server.py code has a comment saying agent_init's wiring "no-ops" due to missing settings, but this is fragile — both paths create real loops if settings exist. The plan doesn't explain:
- Which path is the canonical one for ThoughtStream?
- Does `wire.py` get updated to create a ThoughtStream instead of a ConsciousnessLoop?
- Does `server.py` need changes, or does it just import the new loop?
- What happens to the `_noop_placeholder()` fallback?

**Impact**: If both paths create ThoughtStreams, you get duplicate autonomous thought generation. If only one is updated, the other still runs the old 7-substrate loop.

**Fix**: Add a subsection to A1 (or A6) explicitly stating: (a) which wiring path is canonical, (b) what changes `wire.py` needs, (c) what changes `server.py` needs, (d) how to prevent double-instantiation.

---

### BLOCKER 3: A3 Continuous Dreaming contradicts A1's `asyncio.sleep()` forbidden pattern

A1's scaffold forbids: `asyncio.sleep(` (except dreaming background task)

But A3 says: "An asyncio.Task that runs alongside the main ThoughtStream, but at lower priority (less token allocation, runs when main stream is between thoughts or during low-activity periods)."

The dreaming task needs SOME mechanism to yield control and wait. The plan doesn't specify what that mechanism is if not `asyncio.sleep()`. Options include:
- `asyncio.Event` wait (main stream signals when idle)
- `asyncio.Condition` (dreamer waits on condition)
- Custom sleep wrapper that checks shutdown

**Impact**: Implementer has no guidance on how to implement the dreaming background loop without violating the A1 forbidden pattern, and the exception carve-out is ambiguous ("except dreaming background task" — does this mean `asyncio.sleep()` IS allowed in dreaming, or that dreaming must use something else?).

**Fix**: Clarify the A1 forbidden pattern exception. Either: (a) explicitly allow `asyncio.sleep()` in `dreaming.py` with a comment explaining why, or (b) specify the alternative mechanism (e.g., `asyncio.Event.wait()` with main-stream idle signal).

---

## 3. Significant Gaps (should fix, won't block initial work)

### GAP 1: Only 3 of 8 steps have verification scaffolds

The plan provides detailed scaffolds for A1, A6, and B2. Steps A2, A3, A4, A5, A7, A8, B3, B4, B5 have NO scaffold. The "Per-Step Scaffold" section title in the plan implies all steps get one, but only 3 are present.

Without scaffolds, implementers of A2-A5 have no:
- Forbidden patterns to avoid
- Required commands to verify
- Hard rejection criteria
- Evidence paths

**Recommendation**: Add at minimum a scaffold skeleton for A8 (HARD STOP safety — safety-critical) and B3 (per-channel filtering — correctness-critical). The others can have lighter scaffolds but should at least specify evidence paths and hard rejection criteria.

---

### GAP 2: `_infrastructure.py` dual handler not addressed in Phase B

The plan's Phase B file map lists `hermes_conversational.py` for modification (B4, B5), but `guinevere/discord/_infrastructure.py` (773 lines) contains its OWN copy of the conversational handler logic:

- Line 629: `GUINEVERE_CHAT_CHANNEL_ID: Final[int] = 1_510_914_600_777_023_659`
- Line 642: Its own `HermesConversationalHandler` class
- Line 655: Its own `handle_conversational_message()` function

Both `hermes_conversational.py` and `_infrastructure.py` have channel-specific logic that would need updating for multi-channel support. The plan only mentions `hermes_conversational.py`.

**Impact**: After B4, one handler supports multi-channel while the other still hardcodes `#guinevere-chat`. Depending on which handler is actually called, the refactor may be incomplete.

**Recommendation**: Add `_infrastructure.py` to the B4 file map. Clarify which handler is the canonical one (the plan should state whether `_infrastructure.py` is deprecated or needs parallel changes).

---

### GAP 3: `guinevere/consciousness/infra/` sub-package not addressed

The `infra/` directory contains 4 files (888 lines total):
- `audit_writer.py` (199 lines) — Hash-chained audit trail
- `budget.py` (265 lines) — IterationBudget (turn/token/cost limiting)
- `reflection.py` (136 lines) — LLM-powered lesson extraction
- `testing_gate.py` (288 lines) — ADR-029 self-modification gate

The research report notes these are "not wired into the consciousness loop itself" and are for the M10/W14 self-modification pipeline. But the plan doesn't mention them at all — not in the file map, not in the collision scan, not in the rollback plan.

**Impact**: If ThoughtStream replaces the loop, do these files still work? `IterationBudget` might be useful for ThoughtStream's token management. `audit_writer` might be needed for action audit trails. The plan should explicitly state whether these are preserved, deprecated, or integrated.

**Recommendation**: Add a note to the Phase A file map: "PRESERVE: `guinevere/consciousness/infra/` (not modified, remains available for M10/W14 pipeline)."

---

### GAP 4: `ConsciousnessConfig` model not updated

The research report (Section 10) explicitly notes: "Config model is NOT consumed by the actual implementation. The loop uses hardcoded ADR-063 values." The config has `enabled: bool = False` (disabled by default).

The plan doesn't mention updating `guinevere/config/models.py` to:
- Add ThoughtStream-specific config (metacognition interval, dreaming priority, confidence threshold, etc.)
- Change the default `enabled` value
- Align the config model with the actual ThoughtStream implementation

**Impact**: ThoughtStream either hardcodes its own values (repeating the current anti-pattern) or has no configuration surface at all.

**Recommendation**: Add `guinevere/config/models.py` to the A1 file map as MODIFY. Define the ThoughtStream config model (or update ConsciousnessConfig).

---

### GAP 5: A7 "memory service" is ambiguous

The plan says: "All thoughts recorded to memory service (internal via Hermes memory bridge)." But `hermes_conversational.py` already has a `HermesMemoryBridge` that does memory recall and storage for conversational context. The plan doesn't clarify:
- Does ThoughtStream use the SAME HermesMemoryBridge?
- Or does it create its own `memory_bridge.py` that talks to a different service?
- What is the "Hermes memory bridge" — is it the same as `HermesMemoryBridge` in the conversational handler?

**Impact**: Implementer might create a duplicate memory interface, or might try to import from the wrong module.

**Recommendation**: Specify whether A7's `memory_bridge.py` wraps the existing `HermesMemoryBridge` from `hermes_conversational.py`, or creates a new interface to the same underlying PostgreSQL/Redis memory store.

---

## 4. Minor Observations (not blockers, FYI)

### 4.1 Hardcoded channel ID count is slightly overstated

The plan says "5+ files" have hardcoded channel IDs. Actual count: `1510914600777023659` appears in 3 files (`hermes_conversational.py`, `_infrastructure.py`, and `_entrypoint.py` comment). The other channels (`guinevere-status`, `system-health`, etc.) use name-based lookups in `notifications.py`, `_startup.py`, and `_infrastructure.py`. The B2 scope should clarify that the name-lookup channels are ALSO in scope (not just the hardcoded ID).

### 4.2 A6 "REVIEW" for hermes_brain.py is vague

The plan says "REVIEW (port needed patterns)" for `hermes_brain.py`. The research shows HermesBrain wraps `AIAgent.run_conversation()` with 30s timeout and fallback. ThoughtStream uses `chat()` instead. The plan should state what specific patterns to port (timeout? fallback? error handling?) or mark it "PRESERVE — no changes needed."

### 4.3 B1 (channel creation) has no validation step

Step 5 says "Admin: create Discord channels per layout" but doesn't specify how to verify the channels exist and have correct IDs before proceeding to B2 (which requires the IDs in `.env.discord`).

### 4.4 VPS deployment step lacks detail

Step 8 says "Pull P24 branch, restart services" but doesn't specify:
- Which branch name?
- Which services to restart (discord bot? HTTP server? both?)
- What systemd commands to run
- How to verify deployment succeeded

### 4.5 `subagents.yaml` dependency unclear

The plan doesn't mention the 55+ `cmd_*.py` files in `guinevere/discord/`. For B3 (per-channel filtering), the plan says "add channel permission check to all commands" but doesn't explain whether this is done in `_command_registry.py` (centralized) or in each `cmd_*.py` (distributed). The `_command_registry.py` approach (373 lines, 41-command spec table) is the obvious choice, but should be stated explicitly.

### 4.6 Reaction listeners not in scope

The research report (Section 13.6) notes that gmail and x reaction listeners aren't registered in `setup_hook`. The plan doesn't address this. If Discord refactor touches `_entrypoint.py`, these listeners might need attention. Mark as explicit "OUT of scope" if intentional.

---

## 5. Verification Scaffold Completeness Matrix

| Step | Scaffold Present | Evidence Paths | Hard Rejection | Status |
|------|-----------------|----------------|----------------|--------|
| A1 | ✅ Full | ✅ | ✅ | OK |
| A2 | ❌ Missing | ❌ | ❌ | Needs scaffold |
| A3 | ❌ Missing | ❌ | ❌ | Needs scaffold |
| A4 | ❌ Missing | ❌ | ❌ | Needs scaffold |
| A5 | ❌ Missing | ❌ | ❌ | Needs scaffold |
| A6 | ✅ Full | ✅ | ✅ | OK |
| A7 | ❌ Missing | ❌ | ❌ | Needs scaffold |
| A8 | ❌ Missing | ❌ | ❌ | Needs scaffold (safety-critical) |
| B1 | N/A (ops) | — | — | OK |
| B2 | ✅ Full | ✅ | ✅ | OK |
| B3 | ❌ Missing | ❌ | ❌ | Needs scaffold (correctness-critical) |
| B4 | ❌ Missing | ❌ | ❌ | Needs scaffold |
| B5 | ❌ Missing | ❌ | ❌ | Needs scaffold |

**Coverage: 3/11 implementation steps (27%)**

---

## 6. Execution Order Assessment

The proposed order is sound. No reordering needed. The dependency map correctly identifies:
- A1 as the critical-path predecessor
- A8 as parallelizable with A1
- A2/A3/A7 as parallelizable after A1
- Phase A → Phase B sequencing
- B1 as ops-parallel with B2

**One suggestion**: A8 (HARD STOP safety) should be completed and verified BEFORE A6 (LifeKernel merge), not just parallel with A1. The plan's dependency map says "A6 → A8 (shared Redis concern)" but the execution order (Step 1) puts A1+A8 parallel, then A6 in Step 4. This is actually correct — A8 provides the new HARD STOP mechanism, A6 deprecates the old one. The dependency arrow should be A8 → A6, not A6 → A8.

---

## 7. Rollback Adequacy

The rollback plan is adequate for Phase A. The strategy of keeping `substrates.py` untouched until A1-A5 pass is sound. The `git checkout` paths are correct.

**Phase B rollback** is slightly weaker — it says "revert env vars if added" but doesn't specify how (manual deletion? git restore `.env.discord`?). For VPS, the systemd rollback is mentioned but not detailed.

**Recommendation**: For Phase B, add explicit rollback commands:
```bash
git checkout -- guinevere/discord/
# Restore .env.discord from backup if modified
systemctl --user restart guinevere-discord
```

---

## 8. Summary of Required Changes

| # | Type | What to fix |
|---|------|-------------|
| B1 | BLOCKER | Fix A1 scaffold test path: `tests/consciousness/` → `tests/p24/test_consciousness*.py` |
| B2 | BLOCKER | Add section explaining dual wiring reconciliation (server.py vs wire.py vs agent_init.py) |
| B3 | BLOCKER | Clarify A3 dreaming mechanism vs A1 forbidden `asyncio.sleep()` pattern |
| G1 | GAP | Add scaffolds for A2-A5, A7-A8, B3-B5 (at minimum A8 and B3) |
| G2 | GAP | Add `_infrastructure.py` to B4 file map (dual handler) |
| G3 | GAP | Address `guinevere/consciousness/infra/` sub-package (preserve/deprecate note) |
| G4 | GAP | Add `config/models.py` to A1 file map for ThoughtStream config |
| G5 | GAP | Clarify A7 memory_bridge relationship to existing HermesMemoryBridge |

---

> **Bottom line**: The plan is 80% ready. Fix the 3 blockers and address the 5 gaps, and it becomes executable without ambiguity. The architecture, dependency map, and collision scan are solid. The main weakness is scaffold coverage (27%) and two hidden integration points (dual wiring, dual Discord handler).
