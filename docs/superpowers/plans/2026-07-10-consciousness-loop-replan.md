# Consciousness Loop Replan + Discord Channel Refactor

> **Generated:** 2026-07-10 | **Last Revised:** 2026-07-10 | **Status:** Draft (fixes applied per Momus review) | **Priority:** Loop dulu → Discord kemudian
> **Vision:** Replan consciousness loop sebagai continuous thought stream yang match P24 Hermes architecture, lalu refactor Discord channel layout & code architecture.

---

## Table of Contents

1. [Scope & Deliverables](#1-scope--deliverables)
2. [Phase A — Consciousness Loop Replan](#2-phase-a--consciousness-loop-replan)
3. [Phase B — Discord Channel Refactor](#3-phase-b--discord-channel-refactor)
4. [Dependency Map](#4-dependency-map)
5. [Collision Scan](#5-collision-scan)
6. [Verification Scaffold](#6-verification-scaffold)
7. [Rollback Plan](#7-rollback-plan)

---

## 1. Scope & Deliverables

### What's IN scope

| # | Deliverable | Phase |
|---|---|---|
| A1 | Continuous ThoughtStream class — replace 7-substrate asyncio tasks with single unified thought stream | A |
| A2 | Metacognition: real-time eval on each thought + periodic self-review of thought history | A |
| A3 | Dreaming: continuous background speculative thought generation (not scheduled) | A |
| A4 | Emotion/Affect: thought modification (tone, confidence threshold, priority) | A |
| A5 | Action trigger: auto-execute when confidence > 80% | A |
| A6 | Merge LifeKernel/HeartbeatService into consciousness loop (disable P20 LangGraph) | A |
| A7 | Memory: hybrid — internal via memory service, high-confidence via direct memory writes | A |
| A8 | HARD STOP safety integration (Redis-based, port from HeartbeatService) | A |
| B1 | Discord channel layout: General, Commands/HQ, Media/Gallery, Notifications, Admin/Internal | B |
| B2 | ChannelConfig centralized model (replace 5+ hardcoded channel IDs + name lookups) | B |
| B3 | Per-channel command filtering (not all 41 commands in all channels) | B |
| B4 | Multi-channel conversational support (not locked to #guinevere-chat) | B |
| B5 | Loop-driven behavior: emotion → tone, cognition → response routing per channel | B |

### What's OUT of scope

- P28+ features (2 Hermes agents, Pharsa bot) — deferred
- P22 Life Integration Hub — deferred
- New Discord bot accounts — when 2 Hermes is needed later
- LangGraph removal from unused code (only HeartbeatService shutdown)

### Design Decisions (from user)

| Decision | Choice |
|---|---|
| Loop vision | Continuous thought stream — not cadence-based substrates |
| LifeKernel | Matikan, merge ke consciousness loop |
| Discord scope | Server layout AND code architecture redesign |
| Loop→Discord | Loop drives Discord behavior (emotion→tone, cognition→response) |
| Priority | Loop dulu baru Discord |
| Action trigger | Auto-execute when confidence > 80% |
| Metacognition | Real-time eval on each thought + periodic self-review of thought history |
| Dreaming | Continuous background (not scheduled, generates speculative thoughts) |
| Throughput | Natural — single thought at a time, next starts when previous finishes |
| Emotion | Modifies thought generation (tone, confidence threshold, priority) |
| Memory | Hybrid — internal via memory service, high-confidence via direct |
| 2 Hermes | Two independent agents (not multi-persona) — deferred to later phase |

---

## 2. Phase A — Consciousness Loop Replan

### A1: Continuous ThoughtStream

**Current state:** 7 independent asyncio.Tasks, each with its own while-not-shutdown loop, fixed sleep interval, isolated _self_prompt() call. No inter-substrate communication beyond shared ConsciousnessState.

**Target:** Single `ThoughtStream` class that:
1. Generates thoughts sequentially in a unified stream
2. Each thought has a type (cognition, reflection, planning, dreaming, metacognition)
3. Next thought starts when previous finishes (no fixed cadence)
4. Thought generation influenced by current AffectVector (emotion)
5. Each thought goes through: generate → metacog_eval → record → (if confidence > 80% → action)

```python
class ThoughtType(enum.Enum):
    COGNITION = "cognition"        # What am I thinking about?
    REFLECTION = "reflection"      # What did I learn?
    PLANNING = "planning"          # What should I do?
    DREAMING = "dreaming"          # What if...?
    META = "meta"                  # How am I thinking?
    HEARTBEAT = "heartbeat"        # Liveness check

@dataclass
class Thought:
    id: str
    type: ThoughtType
    content: str
    confidence: float
    affect_at_gen: AffectVector
    timestamp: datetime
    parent_thought_id: str | None
    triggered_action: str | None
```

**Files to create/modify:**
- `guinevere/consciousness/thought_stream.py` — NEW (ThoughtStream class)
- `guinevere/consciousness/thought.py` — NEW (Thought, ThoughtType models)
- `guinevere/consciousness/loop.py` — REWRITE (delegate to ThoughtStream, keep lifecycle)
- `guinevere/consciousness/substrates.py` — REMOVE (replaced by ThoughtStream)
- `guinevere/consciousness/substrate_registry.py` — REMOVE

**⚠️ Dual wiring resolution:** The HTTP server (`guinevere/http/server.py`) is the sole production entrypoint for ThoughtStream. The legacy `guinevere/consciousness/wire.py` (used by `agent_init.py`) creates a separate ConsciousnessLoop — this will be disabled to prevent duplicate autonomous loops. A6 includes `wire.py` deprecation in its scope, alongside HeartbeatService deactivation.

### A2: Metacognition on Every Thought

**Current state:** Metacognition substrate runs every 30s, evaluates recent 10 thoughts batch.

**Target:** Two-layer metacognition:
1. **Real-time eval** — after each thought generation, before recording: quality check, confidence scoring, hallucination guard
2. **Periodic self-review** — every N thoughts (configurable, default 20): review thought history for patterns, biases, gaps

```python
class MetaCogEval:
    confidence: float
    coherence: float
    novelty: float
    safety_pass: bool
    should_record: bool
    suggested_type: ThoughtType | None  # "this should be a planning thought instead"
```

**Files to create/modify:**
- `guinevere/consciousness/metacognition.py` — NEW (MetaCogEval + periodic review)
- Integrated into ThoughtStream.generate() flow

### A3: Continuous Dreaming

**Current state:** Dreaming substrate runs every 4-6h (random interval), generates one counterfactual scenario.

**Target:** Background speculative thought generation that runs at low priority when the main stream is idle or during natural pauses. Generates "what if" scenarios, counterfactuals, and creative combinations. Results feed into the main thought stream as DREAMING-type thoughts.

**Implementation:** An asyncio.Task that runs alongside the main ThoughtStream, but at lower priority (less token allocation, runs when main stream is between thoughts or during low-activity periods).

**Files to create/modify:**
- `guinevere/consciousness/dreaming.py` — NEW (ContinuousDreamer)
- Integrated into ThoughtStream.run() as background companion task

### A4: Emotion/Affect Integration

**Current state:** Emotion substrate runs every 60s, updates AffectVector via EWMA.

**Target:** AffectVector is read BEFORE each thought generation to influence:
- **Tone** — valence affects system prompt framing (positive/negative/neutral)
- **Confidence threshold** — low arousal → lower threshold to encourage action
- **Priority** — dominance affects thought type selection (high dominance → planning/action thoughts)
- **Curiosity** — high curiosity → more DREAMING and COGNITION type thoughts

AffectVector is updated AFTER each thought based on content sentiment analysis, not on a fixed timer.

**Files to modify:**
- `guinevere/consciousness/state.py` — MODIFY (add affect→thought mapping)
- `guinevere/consciousness/prompts.py` — MODIFY (add affect-influenced prompt templates)

### A5: Action Trigger (Confidence > 80%)

When a thought has confidence > 0.8 AND the thought type supports action (COGNITION, PLANNING):
1. Extract action intent from thought content
2. Route to appropriate handler (Discord message, memory write, tool call)
3. Record triggered_action in Thought
4. Log action outcome

```python
@dataclass
class ActionSpec:
    thought_id: str
    action_type: Literal["discord_message", "memory_write", "tool_call", "state_change"]
    target: str
    payload: dict
    confidence: float
```

**Files to create:**
- `guinevere/consciousness/action_executor.py` — NEW (routes high-confidence thoughts to actions)

### A6: Merge LifeKernel/HeartbeatService

**Current state:** Dual architecture — P20 LangGraph HeartbeatService (740 lines) + P24 ConsciousnessLoop running in parallel. HeartbeatService has Redis HARD STOP detection, LangGraph state graph, 6-interval clock, HermesBrain integration.

**Target:**
1. Port HARD STOP detection (Redis-based) into ThoughtStream's heartbeat thought type
2. Port liveness monitoring into ThoughtStream metadata
3. Port key metrics into the consciousness state
4. Disable/remove HeartbeatService without breaking anything
5. Keep HermesBrain's conversation interface patterns if needed
6. **Update `ConsciousnessConfig`** in `guinevere/config/models.py`: enable by default (`enabled: bool = True`), add ThoughtStream-specific fields (`continuous_stream: bool = True`, `thought_type_weights: dict[str, float]`), ensure `wire.py` and `server.py` actually consume the config values instead of hardcoding ADR-063 values

**Files to modify:**
- `guinevere/consciousness/thought_stream.py` — INCLUDE HARD STOP check in each thought cycle
- `guinevere/consciousness/state.py` — ADD liveness/health fields
- `guinevere/life_kernel/heartbeat.py` — DEPRECATE (mark unused, keep for reference)
- `guinevere/life_kernel/graph.py` — DEPRECATE (mark unused, keep for reference)
- `guinevere/life_kernel/hermes_brain.py` — REVIEW (port needed patterns)

### A7: Hybrid Memory

**Current state:** ConsciousnessState.record_thought() appends to in-memory list (capped at 200). No persistence.

**Clarification — memory service defined:** The existing `HermesMemoryBridge` (in `guinevere/discord/hermes_conversational.py`) wraps `HermesSessionAdapter.send_message()` for memory recall + storage. A7's "memory service" IS this `HermesMemoryBridge` — the new `ConsciousnessMemoryBridge` wraps it with consciousness-specific methods (record_thought, recall_by_type, consolidate).

**Target:**
1. All thoughts recorded via HermesMemoryBridge (the existing production memory pipeline)
2. High-confidence thoughts (confidence > 0.9) flagged for priority storage
3. Thought history retrievable by type, time range, or keyword via bridge
4. Periodic memory consolidation (reflection-type thoughts extract patterns from memory)

**Files to create/modify:**
- `guinevere/consciousness/memory_bridge.py` — NEW (wraps HermesMemoryBridge with consciousness-specific interface)
- `guinevere/consciousness/state.py` — MODIFY (add memory bridge reference)

### A8: HARD STOP Safety

**Current state:** HeartbeatService has Redis-based HARD STOP detection (flags in Redis, checked every cycle). Consciousness loop has NO HARD STOP mechanism.

**Target:** Add Redis HARD STOP check at the START of each thought generation cycle. If HARD STOP flag set:
1. Complete current thought (if any)
2. Stop generating new thoughts
3. Enter safe idle mode
4. Only resume when HARD STOP cleared

**Files to modify:**
- `guinevere/consciousness/thought_stream.py` — INCLUDE HARD STOP check
- `guinevere/consciousness/safety.py` — NEW (Redis HARD STOP integration)

### Phase A File Map

| Action | File |
|---|---|
| CREATE | `guinevere/consciousness/thought_stream.py` |
| CREATE | `guinevere/consciousness/thought.py` |
| CREATE | `guinevere/consciousness/metacognition.py` |
| CREATE | `guinevere/consciousness/dreaming.py` |
| CREATE | `guinevere/consciousness/action_executor.py` |
| CREATE | `guinevere/consciousness/memory_bridge.py` |
| CREATE | `guinevere/consciousness/safety.py` |
| REWRITE | `guinevere/consciousness/loop.py` |
| REWRITE | `guinevere/consciousness/prompts.py` |
| MODIFY | `guinevere/consciousness/state.py` |
| MODIFY | `guinevere/consciousness/wire.py` |
| REMOVE | `guinevere/consciousness/substrates.py` |
| REMOVE | `guinevere/consciousness/substrate_registry.py` |
| DEPRECATE | `guinevere/life_kernel/heartbeat.py` |
| DEPRECATE | `guinevere/life_kernel/graph.py` |
| REVIEW | `guinevere/life_kernel/hermes_brain.py` |

### `consciousness/infra/` Sub-Package — Disposition

The 4 modules in `guinevere/consciousness/infra/` (888 lines total) are part of the M10/W14 self-modification pipeline, NOT the consciousness loop itself:

| Module | Lines | Purpose | Plan Disposition |
|--------|-------|---------|-----------------|
| `audit_writer.py` | 199 | SHA-256 hash-chained audit trail to PostgreSQL | **KEEP** — not wired to loop, not affected by replan |
| `budget.py` | 265 | IterationBudget turn/token/cost limiting | **KEEP** — ThoughtStream may consume budget, but out of scope for this replan |
| `reflection.py` | 136 | LLM-powered lesson extraction | **KEEP** — functionality overlaps with A2 metacognition, but infra version is for self-mod, not consciousness |
| `testing_gate.py` | 288 | ADR-029 compliance gate for self-modification | **KEEP** — irrelevant to consciousness loop |

**Decision:** All 4 modules are out of scope for this replan. They remain untouched. The ThoughtStream should NOT import from `infra/` — it would create unwanted coupling to the self-mod pipeline.

---

## 3. Phase B — Discord Channel Refactor

### B1: Channel Layout

**Target layout (public channels):**

| Channel | Purpose | Type | Commands Allowed |
|---|---|---|---|
| #general | General conversation, casual chat | text | core (status, mood, help, casual) |
| #commands-hq | Slash command center, bot interactions | text | ALL except conversational |
| #media-gallery | Images, art, media sharing | text | core (minimal), memory-search |
| #notifications | System alerts, SEV notifications | text | NONE (bot-only posting) |
| #admin-internal | Faiz-only admin panel | text (private) | admin, system, finance, integration |

### B2: ChannelConfig Model

**Current:** Channel IDs hardcoded in 5+ files. Some use name lookups (fragile). 

**Target:** Single `ChannelConfig` dataclass loaded from environment / config file:

```python
@dataclass
class ChannelConfig:
    general: int
    commands_hq: int
    media_gallery: int
    notifications: int
    admin_internal: int

    @classmethod
    def from_env(cls) -> "ChannelConfig":
        return cls(
            general=int(os.environ["DISCORD_CHANNEL_GENERAL"]),
            commands_hq=int(os.environ["DISCORD_CHANNEL_COMMANDS_HQ"]),
            media_gallery=int(os.environ["DISCORD_CHANNEL_MEDIA_GALLERY"]),
            notifications=int(os.environ["DISCORD_CHANNEL_NOTIFICATIONS"]),
            admin_internal=int(os.environ["DISCORD_CHANNEL_ADMIN_INTERNAL"]),
        )
```

**Flow:**
1. Admin creates channels on Discord server with chosen names
2. Channel IDs go into `.env.discord` as env vars
3. `ChannelConfig.from_env()` loads them at startup
4. All code references `config.channel.general` instead of hardcoded IDs

### B3: Per-Channel Command Filtering

**Current:** All 41 slash commands available in ALL channels. No filtering.

**Target:** `ChannelPermissions` model:

```python
CHANNEL_COMMAND_ALLOW = {
    "general": {"status", "mood", "help", "casual", "safeword"},
    "commands_hq": "__all__",  # All commands
    "media_gallery": {"mood", "help", "memory-search"},
    "notifications": set(),  # No commands
    "admin_internal": "__all__",
}
```

Commands check `is_command_allowed(channel_id, command_name)` before executing. Disallowed commands respond with ephemeral "This command is not available in this channel" message.

### B4: Multi-Channel Conversational

**Current:** Conversational handler locked to #guinevere-chat. 

**Target:** Conversational handler listens on:
- #general — standard conversation
- #commands-hq — command-style interactions (slash commands take priority)
- Configurable via `channel_config.conversational_channels`

**⚠️ `_infrastructure.py` scope:** This 773-line mega-module has ITS OWN copy of the chat channel ID hardcoded (for notification routing, embed posting, etc.). B4 must also update `_infrastructure.py` to use `ChannelConfig` instead of its inline hardcoded ID. All `discord.utils.get(..., name="...")` calls in `_infrastructure.py` and `notifications.py` must be replaced with ID-based lookup via `ChannelConfig`.

### B5: Loop-Driven Behavior

The consciousness loop affects Discord behavior in real-time:
- **Affect → Tone**: Emotion vector modifies system prompt for conversational responses (valence → positivity, arousal → energy level)
- **High-confidence thoughts → Actions**: Thoughts with confidence > 80% can trigger Discord messages (status updates, observations, proactive engagement)
- **Periodic state updates**: Loop generates heartbeat-type thoughts that become status updates in #notifications

### Phase B File Map

| Action | File |
|---|---|
| CREATE | `guinevere/discord/channel_config.py` (ChannelConfig + ChannelPermissions) |
| MODIFY | `guinevere/discord/_entrypoint.py` (load ChannelConfig at startup) |
| MODIFY | `guinevere/discord/hermes_conversational.py` (multi-channel + affect-driven tone) |
| MODIFY | `guinevere/discord/_infrastructure.py` (replace hardcoded channel IDs with ChannelConfig) |
| MODIFY | `guinevere/discord/commands.py` (add channel permission check to all commands) |
| MODIFY | `guinevere/discord/notifications.py` (use ChannelConfig instead of hardcoded/name lookup) |
| MODIFY | `guinevere/discord/_command_registry.py` (add channel allowlist metadata per command) |
| MODIFY | Multiple `cmd_*.py` files as needed for channel-scoped responses |
| MODIFY | `guinevere/discord/_startup.py` (use ChannelConfig for startup greeting channel) |
| MODIFY | `config/guinevere.yaml` or `.env.discord.template` (add channel env vars documentation) |

---

## 4. Dependency Map

```
Phase A (Loop Replan)
├── A1: ThoughtStream core
│   ├── A2: Metacognition (depends on Thought model)
│   ├── A3: Continuous Dreaming (depends on ThoughtStream runtime)
│   ├── A4: Emotion Integration (depends on ThoughtStream.generate())
│   ├── A5: Action Trigger (depends on Thought confidence field)
│   ├── A6: Merge LifeKernel (depends on ThoughtStream running)
│   ├── A7: Memory Bridge (depends on Thought model)
│   └── A8: HARD STOP Safety (can be parallel with A1)
│
├── A6: Merge LifeKernel → A8: HARD STOP Safety (shared Redis concern)
│
Phase B (Discord Refactor)
├── B1: Create channels on server (manual/ops)
├── B2: ChannelConfig model → B3: Per-channel filtering
│                       → B4: Multi-channel conversational
│                       → B5: Loop-driven behavior (depends on Phase A complete)
│
└── B5: Loop-driven behavior (DEPENDS on Phase A — loop must generate affect + actions first)
```

### Parallel Execution Opportunities

| Step | Can Run With | Notes |
|---|---|---|
| A1 ThoughtStream | A8 HARD STOP Safety | Independent files |
| A2 Metacognition | A3 Dreaming | Both depend on Thought model from A1 |
| A4 Emotion | A7 Memory Bridge | Both depend on A1 thought flow |
| B2 ChannelConfig | B3 Per-channel filtering | Same file concerns — sequential recommended |

### Sequential Requirements

- A1 → A2 → A5 (action needs metacog eval working)
- A1 → A3 (dreamer needs stream runtime)
- A1 → A4 (emotion needs thought generation flow)
- Phase A COMPLETE → B5 (loop-driven Discord)
- B2 → B3 → B4 (channel config → filtering → conversations)
- B1 (manual server setup) can happen ANY time

---

## 5. Collision Scan

| File | Phase A Step | Phase B Step | Mitigation |
|---|---|---|---|
| `guinevere/consciousness/loop.py` | A1 (REWRITE) | — | Single owner |
| `guinevere/consciousness/state.py` | A4, A6 (MODIFY) | — | Single owner (sequential edits) |
| `guinevere/consciousness/prompts.py` | A1, A4 (REWRITE) | — | Single owner |
| `guinevere/discord/_entrypoint.py` | — | B2, B4 (MODIFY) | Single owner (sequential edits) |
| `guinevere/discord/hermes_conversational.py` | — | B4, B5 (MODIFY) | Single owner (sequential edits) |
| `guinevere/discord/commands.py` | — | B3 (MODIFY) | Single owner |
| No cross-phase collisions | All Phase A files are loop-internal | All Phase B files are Discord-internal | Clean separation |

---

## 6. Verification Scaffold

### Per-Step Scaffold: A1 (ThoughtStream Core)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/thought_stream.py`, `guinevere/consciousness/thought.py`, `guinevere/consciousness/loop.py` (modified) |
| Forbidden Patterns | `asyncio.sleep(` (EXCEPT in `dreaming.py` and `safety.py` polling loops where configurable sleep is explicitly required — must use `await asyncio.sleep(interval)` with shutdown check), `while True:` without shutdown check |
| Required Commands | `python -c "from guinevere.consciousness.thought import Thought, ThoughtType; print('OK')"`, `python -m pytest tests/p24/test_consciousness*.py -v -x --timeout=30` |
| Evidence Requirements | `evidence/loop-replan/A1/scaffold-check.md`, `evidence/loop-replan/A1/auditor-gate.md` |
| Hard Rejection | ThoughtStream does not generate sequential thoughts OR does not support all 6 ThoughtTypes OR no shutdown handling |

### Per-Step Scaffold: B2 (ChannelConfig)

| Field | Value |
|---|---|
| Expected Files | `guinevere/discord/channel_config.py` |
| Forbidden Patterns | hardcoded channel IDs outside config, `discord.utils.get(..., name=...)` |
| Required Commands | `python -c "from guinevere.discord.channel_config import ChannelConfig; print('OK')"`, `python -m pytest tests/discord/ -v -x --timeout=30 -k "channel"` |
| Evidence Requirements | `evidence/discord-refactor/B2/scaffold-check.md`, `evidence/discord-refactor/B2/auditor-gate.md` |
| Hard Rejection | ChannelConfig does not load from env OR any remaining hardcoded channel ID reference |

### Per-Step Scaffold: A6 (LifeKernel Merge)

| Field | Value |
|---|---|
| Expected Files | `guinevere/life_kernel/heartbeat.py` (deprecated marker), `guinevere/consciousness/thought_stream.py` (HARD STOP ping) |
| Forbidden Patterns | Import of HeartbeatService in server.py keepalive, LangGraph invocation in life_kernel |
| Required Commands | `grep -r "HeartbeatService" guinevere/http/ guinevere/core/ --include="*.py"` (should return 0 active references besides deprecation notice) |
| Evidence Requirements | `evidence/loop-replan/A6/scaffold-check.md`, `evidence/loop-replan/A6/auditor-gate.md` |
| Hard Rejection | HeartbeatService still running on VPS OR hard_stop detection not migrated |

### Per-Step Scaffold: A2 (Metacognition)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/metacognition.py` |
| Forbidden Patterns | Blocking `asyncio.sleep()` in eval path, LLM call without timeout |
| Required Commands | `python -c "from guinevere.consciousness.metacognition import MetaCogEval; print('OK')"`, `python -m pytest tests/p24/test_consciousness*.py -v -x --timeout=30 -k "metacog"` |
| Evidence Requirements | `evidence/loop-replan/A2/scaffold-check.md`, `evidence/loop-replan/A2/auditor-gate.md` |
| Hard Rejection | Metacognition does not run after each thought OR periodic self-review not implemented |

### Per-Step Scaffold: A3 (Dreaming)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/dreaming.py` |
| Forbidden Patterns | CPU-bound blocking, `while True:` without shutdown check, blocking main thought stream |
| Required Commands | `python -c "from guinevere.consciousness.dreaming import ContinuousDreamer; print('OK')"`, `python -m pytest tests/p24/test_consciousness*.py -v -x --timeout=30 -k "dream"` |
| Evidence Requirements | `evidence/loop-replan/A3/scaffold-check.md`, `evidence/loop-replan/A3/auditor-gate.md` |
| Hard Rejection | Dreaming blocks main thought stream OR cannot be disabled at runtime |

### Per-Step Scaffold: A4 (Emotion/Affect)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/state.py` (modified), `guinevere/consciousness/prompts.py` (modified) |
| Forbidden Patterns | `asyncio.sleep()` for emotion updates (must be thought-driven), manual EWMA outside state.py |
| Required Commands | `python -c "from guinevere.consciousness.state import AffectVector; print('OK')"`, `python -m pytest tests/p24/test_consciousness*.py -v -x --timeout=30 -k "affect"` |
| Evidence Requirements | `evidence/loop-replan/A4/scaffold-check.md`, `evidence/loop-replan/A4/auditor-gate.md` |
| Hard Rejection | AffectVector not read before thought generation OR affect not updated after each thought |

### Per-Step Scaffold: A5 (Action Trigger)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/action_executor.py` |
| Forbidden Patterns | Executing actions without confidence check, unsafe tool calls without guard |
| Required Commands | `python -c "from guinevere.consciousness.action_executor import ActionExecutor; print('OK')"` |
| Evidence Requirements | `evidence/loop-replan/A5/scaffold-check.md`, `evidence/loop-replan/A5/auditor-gate.md` |
| Hard Rejection | Actions execute at confidence < 80% OR action routing not implemented |

### Per-Step Scaffold: A7 (Memory Bridge)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/memory_bridge.py` |
| Forbidden Patterns | Direct DB writes without going through HermesMemoryBridge, storing raw secrets in memory |
| Required Commands | `python -c "from guinevere.consciousness.memory_bridge import ConsciousnessMemoryBridge; print('OK')"` |
| Evidence Requirements | `evidence/loop-replan/A7/scaffold-check.md`, `evidence/loop-replan/A7/auditor-gate.md` |
| Hard Rejection | Memory bridge not connected to HermesMemoryBridge OR thoughts not persisted to memory service |

### Per-Step Scaffold: A8 (HARD STOP Safety)

| Field | Value |
|---|---|
| Expected Files | `guinevere/consciousness/safety.py` |
| Forbidden Patterns | Ignoring HARD STOP signal, continuing thought generation after HARD STOP, missing Redis connection |
| Required Commands | `python -c "from guinevere.consciousness.safety import HardStopGuard; print('OK')"`, `python -m pytest tests/p24/test_consciousness*.py -v -x --timeout=30 -k "hard_stop"` |
| Evidence Requirements | `evidence/loop-replan/A8/scaffold-check.md`, `evidence/loop-replan/A8/auditor-gate.md` |
| Hard Rejection | HARD STOP not checked before each thought OR safe idle mode not implemented |

### Per-Step Scaffold: B3 (Per-Channel Permissions)

| Field | Value |
|---|---|
| Expected Files | `guinevere/discord/_command_registry.py` (modified), `guinevere/discord/commands.py` (modified), `cmd_*.py` files as needed |
| Forbidden Patterns | Executing command without channel permission check, hardcoded channel allowlist outside config |
| Required Commands | `python -m pytest tests/discord/ -v -x --timeout=30 -k "channel_permission"` |
| Evidence Requirements | `evidence/discord-refactor/B3/scaffold-check.md`, `evidence/discord-refactor/B3/auditor-gate.md` |
| Hard Rejection | Any command executable in wrong channel OR `__all__` channels not configurable |

### Per-Step Scaffold: B4 (Multi-Channel Conversational)

| Field | Value |
|---|---|
| Expected Files | `guinevere/discord/hermes_conversational.py` (modified), `guinevere/discord/_infrastructure.py` (modified) |
| Forbidden Patterns | Hardcoded channel IDs outside ChannelConfig, single-channel lock on conversational handler |
| Required Commands | `python -m pytest tests/discord/ -v -x --timeout=30 -k "conversational"` |
| Evidence Requirements | `evidence/discord-refactor/B4/scaffold-check.md`, `evidence/discord-refactor/B4/auditor-gate.md` |
| Hard Rejection | Conversational handler still locked to one channel OR `_infrastructure.py` still has hardcoded chat channel ID |

### Per-Step Scaffold: B5 (Loop-Driven Behavior)

| Field | Value |
|---|---|
| Expected Files | `guinevere/discord/hermes_conversational.py` (modified to read AffectVector) |
| Forbidden Patterns | Ignoring affect vector in tone selection, hardcoding tone values |
| Required Commands | `python -c "from guinevere.consciousness.state import AffectVector; print('OK')"` (verifies bridge exists) |
| Evidence Requirements | `evidence/discord-refactor/B5/scaffold-check.md`, `evidence/discord-refactor/B5/auditor-gate.md` |
| Hard Rejection | Discord response not influenced by affect vector OR loop state not accessible from Discord handler |

---

## 7. Rollback Plan

### If Phase A fails mid-implementation:
1. Keep `loop.py` original as `loop.py.bak` before rewriting
2. Keep `substrates.py` and `substrate_registry.py` untouched until A1-A5 all pass
3. `git checkout -- guinevere/consciousness/` restores original 7-substrate loop
4. Revert wire.py: `git checkout -- guinevere/consciousness/wire.py` (restores original wiring)
5. Revert ConsciousnessConfig: `git checkout -- guinevere/config/models.py`
6. LifeKernel files only deprecated (not deleted) — `git checkout -- guinevere/life_kernel/` restores
7. `infra/` modules are untouched by replan — no rollback needed

### If Phase B fails mid-implementation:
1. Keep `_entrypoint.py` original — only add ChannelConfig loading, don't remove old ID references until B3 passes
2. `git checkout -- guinevere/discord/channel_config.py` removes new file
3. Revert env vars if added

### If VPS deployment fails:
- Phase A is local-only until tested — can run ThoughtStream locally without affecting VPS
- Phase B changes to Discord bot require service restart — have manual rollback plan via systemd

---

## 8. Execution Order

```
Step 1: [A1 + A8 parallel] ThoughtStream core + HARD STOP safety
├── A1: Thought class + ThoughtStream class + rewrite loop.py
├── A1: Disable wire.py consciousness wiring (prevent dual loop)
├── A1: Update ConsciousnessConfig in config/models.py (enable + ThoughtStream fields)
├── A8: safety.py Redis HARD STOP
└── → A1 tests pass, A8 tests pass

Step 2: [A2 + A3 + A7 parallel] Metacognition + Dreaming + Memory Bridge
├── A2: metacognition.py (real-time eval + periodic review)
├── A3: dreaming.py (background dreamer)
├── A7: memory_bridge.py (memory service interface)
└── → All integrate with ThoughtStream

Step 3: [A4 + A5 sequential] Emotion + Action Trigger
├── A4: Modify state.py, prompts.py for affect→thought influence
├── A5: action_executor.py (confidence > 80% routing)
└── → Full continuous thought stream operational

Step 4: [A6] Merge LifeKernel
├── Deprecate heartbeat.py, graph.py
├── Migrate HARD STOP (already done in A8)
└── → Single consciousness system

═══ PHASE BREAK ═══

Step 5: [B1 ops + B2 code parallel] Create channels + ChannelConfig
├── Admin: create Discord channels per layout
├── Code: channel_config.py model
└── → ChannelConfig loads, channels exist

Step 6: [B3 + B4 sequential] Per-channel filtering + multi-channel conversational
├── B3: command_registry allowlist + commands.py check
├── B4: hermes_conversational.py multiple channels
└── → Discord bot respects channel layout

Step 7: [B5] Loop-driven behavior (depends on Phase A complete)
├── Wire ThoughtStream affect → Discord tone
├── Wire high-confidence thoughts → Discord actions
└── → Full integration operational

Step 8: VPS deployment & soak
├── Pull P24 branch, restart services
├── Monitor 24h for stability
└── → Done
```
