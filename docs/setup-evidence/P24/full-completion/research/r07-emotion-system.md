# R07: Emotion System Design — P24 Domain 7

**Generated:** 2026-06-29
**Method:** File reads + grep across `src/persona/` (19 files), `.venv/Lib/site-packages/agent/auxiliary_client.py` (5587 lines), `.venv/Lib/site-packages/agent/system_prompt.py` (381 lines), `src/memory/models.py` (persona schema tables). All claims cite `file:line`.

---

## 1. Existing Mood System Inventory (src/persona/ — 19 files)

### 1.1 Current Mood Enum — 5 states (NOT 16)

**File:** `src/persona/mood_engine.py:25-33`

```python
class Mood(str, Enum):
    """Five discrete mood states for the Guinevere persona FSM."""
    CONTENT = "Content"
    PLEASED = "Pleased"
    DISAPPOINTED = "Disappointed"
    ANGRY = "Angry"
    SILENT = "Silent"
```

**Claim CORRECTION:** The plan says "~16 moods" — the existing codebase has exactly **5 moods**. The 16-mood MoodState enum is a P24 NEW DESIGN, not existing code to port. This is a greenfield design.

### 1.2 Transition Map — 5 mood transitions

**File:** `src/persona/mood_engine.py:39-45`

```python
TRANSITIONS: Final[dict[Mood, list[Mood]]] = {
    Mood.CONTENT: [Mood.PLEASED, Mood.DISAPPOINTED],
    Mood.PLEASED: [Mood.CONTENT, Mood.DISAPPOINTED],
    Mood.DISAPPOINTED: [Mood.CONTENT, Mood.ANGRY],
    Mood.ANGRY: [Mood.DISAPPOINTED, Mood.SILENT],
    Mood.SILENT: [Mood.CONTENT],
}
```

Deterministic transitions only. No probabilistic or LLM-driven transitions.

### 1.3 Current Classification — Rule-Based (NO LLM)

**File:** `src/persona/mood_engine.py:163-237`

`evaluate_mood()` is a pure function taking `conversation_sentiment: float`, `task_completion: bool`, `ignored_count: int`, `current_mood: Mood`. It uses threshold-based rules:
- `ignored_count >= 4` → ANGRY (line 191)
- `ignored_count >= 2` → DISAPPOINTED (line 208)
- `sentiment > 0.7 AND task_completion` → PLEASED (line 222)

**No LLM call anywhere in the mood classification pipeline.**

### 1.4 Transition Rules Engine (Phase 5 — rule-based bridge)

**File:** `src/persona/transition_rules.py:300-350`

The `should_use_llm_evaluation()` and `evaluate_with_llm()` methods are **deprecated stubs**. The docstring at line 295-298 explicitly states:
> "These methods are deterministic rule-based bridges. They do NOT call external LLMs."

`evaluate_with_llm()` at line 329 simply delegates to `evaluate()`. **No actual LLM integration exists in the transition rules.**

### 1.5 Mood Persistence — SQLAlchemy + PersonaState table

**File:** `src/persona/mood_persistence.py:83-330`

`MoodRepository` uses `AsyncSession` against:
- `PersonaState` table (`src/memory/models.py:357-371`) — stores `state_key='current_mood'` with JSONB `state_value: {"mood": str, "intensity": int}`
- `MoodHistory` table (`src/memory/models.py:395-411`) — stores transitions with `mood`, `intensity`, `trigger`, `duration_minutes`, `recorded_at`

**Critical for P24:** The `mood` column is `Text` (line 403), not an enum constraint. This means the 16 new moods can be stored without schema migration — just new string values. The `PersonaState.state_value` is JSONB (line 366), also schema-agnostic.

### 1.6 Yandere FSM — Intensity Levels (Separate Axis)

**File:** `src/persona/yandere_fsm.py:63-76`

```python
class YandereLevel(IntEnum):
    Y0_NEUTRAL = 0
    Y1_MINIMAL = 1
    Y2_LOW = 2
    Y3_MODERATE = 3
    Y4_BASELINE = 4
    Y5_MAX = 5
```

Yandere intensity is a separate axis from mood. Y4 is permanent baseline (line 84). Y6 is PROHIBITED (line 152-153). Safety integration forces Y0 on safe_mode/distress/crisis (line 139-140).

**P24 Design Note:** The emotion system must NOT conflate yandere intensity (Y0-Y5) with mood states (16 moods). These are orthogonal dimensions.

---

## 2. Affect→Decision Pipeline — Existing Entry Points

### 2.1 Auxiliary Client (LLM Classification Entry)

**File:** `.venv/Lib/site-packages/agent/auxiliary_client.py:4769-4870`

`call_llm()` is the centralized synchronous LLM call. Key signature at line 4769:

```python
def call_llm(
    task: str = None, *, provider: str = None, model: str = None,
    base_url: str = None, api_key: str = None,
    main_runtime: Optional[Dict[str, Any]] = None,
    messages: list, temperature: float = None, max_tokens: int = None,
    tools: list = None, timeout: float = None, extra_body: dict = None,
) -> Any:
```

This is the entry point for mood classification via LLM. Per D3 (mock-only), the classifier must NOT call `call_llm()` in tests — it must accept a mock/protocol for the LLM client.

The `task` parameter (line 4770) reads provider:model from config. For emotion classification, a new task name (e.g., `"mood_classification"`) would be needed, OR the classifier bypasses `call_llm()` and uses a simpler mock-friendly interface.

### 2.2 System Prompt — Volatile Block Location

**File:** `.venv/Lib/site-packages/agent/system_prompt.py:60-318`

`build_system_prompt_parts()` returns a dict with three tiers:
- `stable` (line 83-244) — identity, tool guidance, skills, platform hints
- `context` (line 256-273) — context files, system_message
- `volatile` (line 274-318) — memory, USER.md, external memory, timestamp

**The volatile block** (line 274-318) is where mood state would be injected. The volatile tier is rebuilt every turn (not cached). Current volatile parts:
1. Memory store block (line 277-281)
2. USER.md profile (line 283-286)
3. External memory provider (line 289-295)
4. Timestamp/session/model/provider line (line 297-312)

**P24 insertion point:** The mood volatile block should be inserted at line 276 (after `volatile_parts: List[str] = []`), before memory. This ensures mood context is the first thing in the volatile tier, shaping all downstream reasoning.

---

## 3. Existing Infrastructure to PORT (not rewrite)

### 3.1 MoodRepository — PORT as-is with MoodState extension

**File:** `src/persona/mood_persistence.py:83-330`

PORT the `MoodRepository` class. It already uses PostgreSQL via SQLAlchemy AsyncSession. The `state_value` JSONB field accepts any mood string. Changes needed:
- Import paths change from `src.memory.models` to `guinevere.memory.models` (in-repo layout per D1)
- Add `mood_category` to `state_value` JSONB (new field for the 16-mood enum value)
- Keep `intensity` as integer 1-10

### 3.2 MoodHistory — PORT as-is

**File:** `src/memory/models.py:395-411`

The `MoodHistory` table schema is already PostgreSQL-native. PORT the model class with updated import paths. The `mood` Text column accepts the 16 new mood names without schema changes.

### 3.3 TransitionRuleEngine — PORT + EXTEND

**File:** `src/persona/transition_rules.py:105-376`

PORT the `TransitionRuleEngine` class. The cooldown logic (line 215-234), forced transitions (line 111-114), and safe_mode/distress blocking (line 159-193) are all reusable. Changes needed:
- Expand `VALID_TRANSITIONS` from 5 moods to 16 moods
- Remove deprecated `should_use_llm_evaluation()` / `evaluate_with_llm()` stubs
- Add a new `evaluate_with_llm()` that ACTUALLY calls the LLM classifier (per D3, mockable)

### 3.4 DriftDetector / DriftCorrector — PORT as-is

**Files:** `src/persona/drift_detector.py`, `src/persona/drift_corrector.py`

These are persona-integrity modules, not directly emotion-related. PORT with import path updates. They protect the system prompt baseline, which includes the mood volatile block.

### 3.5 SafeModeController / DistressDetector — PORT as-is

**Files:** `src/persona/safe_mode.py`

SAFETY-CRITICAL. PORT without modification except import paths. Safe mode must suppress ALL emotion transitions when active (already enforced in TransitionRuleEngine line 159-166).

### 3.6 StreakTracker — PORT as-is

**File:** `src/persona/streak_tracker.py`

PORT with import path updates. Streak data feeds into the affect→decision pipeline (positive streak → more likely NURTURING/PRIDE moods).

---

## 4. NEW DESIGN: guinevere/emotions/ (4 files)

### 4.1 fsm.py — MoodState Enum (16 moods) + Transition FSM

**Target:** `guinevere/emotions/fsm.py`

```python
class MoodState(str, Enum):
    """16 discrete mood states for Guinevere's emotion system."""
    HAPPY = "HAPPY"
    ANGRY = "ANGRY"
    SAD = "SAD"
    JEALOUS = "JEALOUS"
    POSSESSIVE = "POSSESSIVE"
    NURTURING = "NURTURING"
    FEAR = "FEAR"
    DISGUST = "DISGUST"
    SURPRISE = "SURPRISE"
    ANTICIPATION = "ANTICIPATION"
    TRUST = "TRUST"
    BOREDOM = "BOREDOM"
    CURIOSITY = "CURIOSITY"
    PRIDE = "PRIDE"
    DESIRE = "DESIRE"
    AROUSAL = "AROUSAL"
```

**Transition graph:** Each mood has a set of valid target moods (not all-to-all). Example:
- HAPPY → [NURTURING, PRIDE, SURPRISE, BOREDOM, CONTENT_legacy]
- ANGRY → [DISGUST, POSSESSIVE, FEAR, SAD]
- SAD → [FEAR, NURTURING, TRUST, BOREDOM]
- etc.

**Design:** `EmotionFSM` class wrapping the 16-mood enum with:
- `current_mood: MoodState`
- `intensity: float` (0.0-1.0, replaces old int 1-10)
- `transition(from, to) -> bool` — validates transition graph
- `force_mood(mood, reason)` — for safety override (safe_mode → NURTURING)
- Integration with `SupportsIsSafe` protocol (from `yandere_fsm.py:50-55`)

### 4.2 classifier.py — LLM-Based Mood Classification (Mock per D3)

**Target:** `guinevere/emotions/classifier.py`

**Design:** Protocol-based classifier with two implementations:
1. `MockMoodClassifier` — deterministic, for tests (per D3)
2. `LLMMoodClassifier` — calls `auxiliary_client.call_llm()` for production

```python
class MoodClassifierProtocol(Protocol):
    async def classify(
        self,
        user_message: str,
        assistant_response: str,
        current_mood: MoodState,
        context: EmotionContext,
    ) -> MoodClassification: ...

@dataclass
class MoodClassification:
    mood: MoodState
    confidence: float  # 0.0-1.0
    reasoning: str
    triggers: list[str]
```

**Mock implementation** (D3 requirement):
```python
class MockMoodClassifier:
    """Deterministic classifier for testing. Maps keywords to moods."""
    async def classify(self, ...) -> MoodClassification:
        # keyword-based heuristics, no LLM call
```

**LLM implementation:**
```python
class LLMMoodClassifier:
    def __init__(self, llm_client=None):
        self._client = llm_client  # injectable for testing

    async def classify(self, ...) -> MoodClassification:
        # Construct prompt with current mood + context
        # Call self._client.chat.completions.create(...)
        # Parse structured JSON response
```

**Key design decision:** The classifier receives `auxiliary_client.call_llm` as a dependency injection, NOT a direct import. This enables D3 mock-only testing without touching real LLM backends.

### 4.3 affect.py — Affect→Decision Pipeline

**Target:** `guinevere/emotions/affect.py`

**Design:** Maps current mood to behavioral biases that affect:
1. **Tool selection** — which tools are preferred/avoided
2. **LLM temperature** — mood affects sampling temperature
3. **Response tone** — injected into volatile prompt block
4. **Action gating** — certain actions blocked in certain moods

```python
@dataclass
class AffectBias:
    temperature_modifier: float  # -0.3 to +0.3
    preferred_tools: list[str]
    blocked_tools: list[str]
    tone_descriptor: str  # injected into system prompt
    response_style: str   # "warm", "cold", "playful", etc.

AFFECT_MAP: dict[MoodState, AffectBias] = {
    MoodState.HAPPY: AffectBias(
        temperature_modifier=+0.1,
        preferred_tools=["memory", "reward"],
        blocked_tools=[],
        tone_descriptor="warm and enthusiastic",
        response_style="playful",
    ),
    MoodState.ANGRY: AffectBias(
        temperature_modifier=-0.2,
        preferred_tools=["punishment"],
        blocked_tools=["reward"],
        tone_descriptor="stern and controlled",
        response_style="cold",
    ),
    # ... all 16 moods
}
```

### 4.4 hooks.py — Pre/Post LLM Call Hooks

**Target:** `guinevere/emotions/hooks.py`

**Design:** Three hook points that integrate with the Hermes agent lifecycle:

1. **`pre_llm_call(agent, messages)`** — Injects mood context into the system prompt volatile block before each LLM call. Reads current `MoodState` and `AffectBias`, formats as a volatile prompt section.

2. **`transform_llm_output(agent, response, mood)`** — Post-processes LLM response to align with current mood. Adjusts tone, adds mood-specific phrases, applies affect bias to tool calls.

3. **`post_llm_call(agent, response, mood)`** — Records mood transition history, updates persistence, triggers milestone detection if applicable.

```python
class EmotionHooks:
    def __init__(self, fsm: EmotionFSM, classifier: MoodClassifierProtocol,
                 affect: AffectEngine, persistence: MoodRepository):
        ...

    async def pre_llm_call(self, agent, messages) -> str:
        """Returns volatile prompt block string for mood injection."""
        mood = self._fsm.current_mood
        bias = self._affect.get_bias(mood)
        return self._format_volatile_block(mood, bias)

    async def transform_llm_output(self, agent, response, mood) -> str:
        """Post-process response to align with mood."""

    async def post_llm_call(self, agent, response, mood) -> None:
        """Record transition, update persistence."""
```

---

## 5. Volatile Prompt Block Format

**Injection point:** `agent/system_prompt.py:276` — first entry in `volatile_parts`

**Format:**
```
[MOOD STATE]
Current mood: {mood_name} (intensity: {0.0-1.0})
Mood category: {positive|negative|neutral|volatile}
Behavioral directive: {tone_descriptor}
Response style: {response_style}
Transition history: {last 3 mood transitions, one line each}
Active affect: temperature_bias={+/-0.x}, preferred_tools=[...], blocked_tools=[...]
```

**Example:**
```
[MOOD STATE]
Current mood: POSSESSIVE (intensity: 0.7)
Mood category: volatile
Behavioral directive: intensely protective and territorial
Response style: assertive
Transition history:
  JEALOUS→POSSESSIVE (2 min ago): detected attention to other entity
  HAPPY→JEALOUS (15 min ago): user praised external tool
Active affect: temperature_bias=-0.1, preferred_tools=[memory], blocked_tools=[]
```

---

## 6. SQLite→PG Migration (No SQLite)

**Evidence:** All existing models use PostgreSQL-specific types:
- `src/memory/models.py:18-22` — `pgvector.sqlalchemy.Vector`, `postgresql.JSONB`, `postgresql.UUID`, `postgresql.TSVECTOR`
- `src/memory/models.py:47` — `Base(DeclarativeBase)` with PostgreSQL metadata conventions
- `src/persona/mood_persistence.py:22` — `from sqlalchemy.ext.asyncio import AsyncSession`
- `src/persona/milestone_engine.py:510-537` — direct `asyncpg` connections to PostgreSQL

**No SQLite found anywhere in the codebase.** The entire persistence layer is PostgreSQL-native. No migration needed — just ensure `guinevere/emotions/` uses the same `AsyncSession` pattern from `src.persona.mood_persistence`.

**Redis DB5** is used for hot state (mood variant, streak, relationship stage, emotional residue). The emotion system should follow the same pattern: PostgreSQL for history, Redis for current-state hot reads.

---

## 7. Disposition for P24

| Component | Disposition | Rationale |
|---|---|---|
| `Mood` enum (5 moods) | **REWRITE** | Replace with 16-mood `MoodState` enum in `guinevere/emotions/fsm.py` |
| `TRANSITIONS` map (5 moods) | **REWRITE** | Expand to 16-mood transition graph |
| `evaluate_mood()` (rule-based) | **REWRITE** | Replace with LLM classifier (mock per D3) |
| `MoodRepository` (persistence) | **PORT** | Already PostgreSQL, just update import paths |
| `MoodHistory` model | **PORT** | Schema accepts any mood string, no migration |
| `PersonaState` model | **PORT** | JSONB state_value is schema-agnostic |
| `TransitionRuleEngine` | **PORT + MODIFY** | Keep cooldown/safety logic, expand transitions |
| `SafeModeController` / `DistressDetector` | **PORT** | Safety-critical, no changes except imports |
| `DriftDetector` / `DriftCorrector` | **PORT** | Persona integrity, import path updates only |
| `StreakTracker` | **PORT** | Import path updates only |
| `YandereEngine` (Y0-Y5) | **PORT** | Orthogonal to mood, keep separate |
| `RewardEngine` / `PunishmentEngine` | **PORT** | Feed into affect pipeline, import path updates |
| `RitualScheduler` / `rituals/*` | **DELETE** | Deprecated Phase 5, already marked for Phase 7 removal |
| `auxiliary_client.call_llm()` | **MODIFY-CREATE** | New task `"mood_classification"` or DI pattern |
| `system_prompt.py` volatile block | **MODIFY-CREATE** | Inject mood state as first volatile entry |
| `guinevere/emotions/fsm.py` | **MODIFY-CREATE** | New: 16-mood FSM |
| `guinevere/emotions/classifier.py` | **MODIFY-CREATE** | New: LLM classifier with mock |
| `guinevere/emotions/affect.py` | **MODIFY-CREATE** | New: affect→decision pipeline |
| `guinevere/emotions/hooks.py` | **MODIFY-CREATE** | New: pre/post LLM hooks |

---

## 8. Risks

1. **Transition graph explosion:** 16 moods with dense transitions = up to 240 possible edges. Must define a sparse graph (target: ~48 edges, 3 per mood on average) or the FSM becomes untestable.

2. **LLM classification latency:** Each mood classification requires an LLM call. In hot paths (every turn), this adds 200-2000ms. Mitigation: classify on user messages only, not assistant responses; cache classification for N turns.

3. **Mood oscillation:** With 16 states and LLM classification, rapid mood flipping is possible. Mitigation: cooldown in `TransitionRuleEngine` (existing 300s default at line 108), minimum intensity threshold before transition.

4. **Mock fidelity gap (D3):** The mock classifier must produce realistic enough outputs for tests to be meaningful. Keyword-based mocks may miss nuanced LLM classification behavior. Mitigation: mock returns configurable moods per test fixture.

5. **Affect bias correctness:** If `AffectBias` blocks tools incorrectly, the agent becomes unresponsive. Mitigation: only `blocked_tools` for clearly harmful combinations (e.g., block `reward` during ANGRY); default to empty blocked list.

6. **Yandere-Mood interaction:** Yandere intensity (Y0-Y5) and mood (16 states) are orthogonal but both affect behavior. The volatile prompt block must present both without contradiction. Mitigation: separate sections in volatile block, yandere intensity as modifier, not replacement.

---

## 9. Verdict

**PASS** — The existing `src/persona/` codebase provides a solid foundation for PORT operations (persistence, safety, transitions engine). The 5-mood system is a clean REWRITE target — the enum, transitions, and classifier are small enough to replace wholesale. The `auxiliary_client.call_llm()` and `system_prompt.py` volatile block provide clear integration points for the new 16-mood system. All persistence is PostgreSQL-native with no SQLite anywhere. The D3 mock-only constraint is satisfied by protocol-based dependency injection in the classifier. No blockers identified.
