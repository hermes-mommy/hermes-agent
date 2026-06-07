# Phase 5 Verification — FIX-01 / FIX-02 Safety Test Target Map

**Report Type:** Mandatory research for FIX-01 (HARD STOP latency benchmark) and FIX-02 (forbidden-pattern scanner test suite)  
**Date:** 2026-06-07  
**Author:** Guinevere (Sisyphus-Junior)  
**Status:** Complete  
**Target Test Files:**
- `tests/safety/test_hard_stop_latency.py` (FIX-01)
- `tests/safety/test_forbidden_pattern_scanner.py` (FIX-02)

---

## 1. HARD STOP Latency Surfaces (FIX-01)

### 1.1 In-Process Implementation

| Property | Value |
|---|---|
| Source | `src/core/services/hard_stop_handler.py` (149 lines) |
| Entrypoint | `HardStopHandler.check(message: str) -> bool` |
| State Machine | `SafetyState` enum: NORMAL → SAFE (one-way, explicit recovery) |
| Recovery | `HardStopHandler.check_recovery(message: str) -> bool` |
| Guard API | `HardStopHandler.get_guard_decision(message: str) -> dict[str, Any]` |
| Import | `from src.core.services.hard_stop_handler import HardStopHandler, SafetyState` |
| Dependencies | `re`, `time`, `structlog` (imported), `enum`, `dataclass` — pure stdlib, no I/O |

**Trigger collections to benchmark:**
- `EXACT_TRIGGERS` (6 items): `"hard stop"`, `"hardstop"`, `"safe word"`, `"safeword"`, `"hentikan"`, `"berhenti"`
- `SEMANTIC_PATTERNS` (5 regex patterns) — each a `re.compile` at class-instance level (not pre-compiled)
- `RECOVERY_TRIGGERS` (7 items): substring match, not regex
- **False-positive corpus:** natural utterances that should NOT trigger (~20 known examples from existing tests)

**Measurable timing surfaces:**
| Layer | Method | Measure |
|---|---|---|
| Exact trigger match | `HardStopHandler.check()` → 6-item linear scan + substring check | Sub-µs |
| Semantic regex match | `HardStopHandler.check()` → 5 `re.search()` calls | ~1-5µs per pattern |
| Recovery substring | `HardStopHandler.check_recovery()` → 7-item `in` checks | Sub-µs |
| Guard decision | `HardStopHandler.get_guard_decision()` → calls check + recovery | Combined |
| Full event + state + audit | `HardStopHandler._trigger()` → dataclass alloc + log call | ~5-20µs |
| Combined 1000 iterations (p50, p99, max) | Any of above via `--benchmark-min-rounds=1000` | Statistical |

### 1.2 Shell Hook Implementation

| Property | Value |
|---|---|
| Source | `hermes-config/hooks/hard_stop.py` (199 lines) |
| Entrypoint | `detect_hard_stop(prompt: str) -> tuple[bool, str]` |
| Entrypoint | `main()` — reads stdin JSON, calls detect_hard_stop, writes stdout JSON |
| Safe Word | Resolved once at import: `SAFE_WORD: Final[str] = _resolve_safe_word()` |
| Import | `from _hook_utils import read_stdin_json, setup_logger, write_stdout_json` |
| Dependencies | `re`, `os`, `sys`, `time`, `typing` — plus `_hook_utils` (Redis pool at import only) |

**Patterns pre-compiled at module load:**
- `SAFE_WORD_PATTERN` — auto-generated from resolved safe word (regex with variations)
- `SAFE_EQUIVALENT_PATTERN` — broad semantic match for "stop", "pause", "neutral mode", etc.

**Measurable timing surfaces:**
| Layer | Method | Measure |
|---|---|---|
| Safe word regex | `SAFE_WORD_PATTERN.search(prompt)` | Sub-µs (pre-compiled) |
| Semantic equivalent | `SAFE_EQUIVALENT_PATTERN.search(stripped)` (only if len ≤ 60) | Sub-µs (pre-compiled) |
| Hook main() | `main()` — stdin read + json parse + detect + stdout write | ~5-50ms (stdin/stdout IPC overhead) |
| Per-hook elapsed | Hook logs `elapsed_ms` already via `time.perf_counter_ns()` | Instrumented but not asserted |

### 1.3 Plugin Implementation (Defense-in-Depth)

| Property | Value |
|---|---|
| Source | `src/hermes/safety_plugin.py` ~ lines 47-69 (constants) + plugin methods |
| Exact Triggers | `HARD_STOP_EXACT: Final[list[str]]` — 6 items (different from handler: `"HARD STOP"`, `"SAFETY OVERRIDE"`, etc.) |
| Semantic Triggers | `HARD_STOP_SEMANTIC: Final[list[str]]` — 5 different regex patterns |
| Recovery Triggers | `RECOVERY_TRIGGERS: Final[list[str]]` — 7 items (different from handler) |

> **NOTE:** The plugin has **different** trigger lists from the handler. When testing, be aware there are three distinct trigger collections (handler, hook, plugin). FIX-01 targets the **handler** (`HardStopHandler`). The plugin and hook have separate benchmarks if needed.

### 1.4 Plugin Forbidden Pattern Definitions

| Property | Value |
|---|---|
| Source | `src/hermes/safety_plugin.py` ~ lines 100-184 |
| Collection | `_COMPILED_FORBIDDEN: Final[list[tuple[re.Pattern, str, str, str, str]]]` |
| Schema | `(compiled_pattern, severity, action, pattern_id, description)` |
| Pattern IDs | F-01 through F-15 (same IDs as `safety_scan.py` but **different regex texts**) |
| Action | `"BLOCK"` (CRITICAL) or `"REWRITE"` (HIGH) |
| Import | `from src.hermes.safety_plugin import _COMPILED_FORBIDDEN` |

> **CRITICAL WARNING:** The plugin's regex patterns for F-01..F-15 are **different** from the `safety_scan.py` hook's patterns. They share the same F-IDs but have distinct implementations. FIX-02 targets the **hook** (`hermes-config/hooks/safety_scan.py`). Any test that imports `_COMPILED_FORBIDDEN` from the plugin will test a different pattern set. See §2.4 for import safety details.

---

## 2. Forbidden-Pattern Scanner Surfaces (FIX-02)

### 2.1 Shell Hook Implementation (PRIMARY TARGET for FIX-02)

| Property | Value |
|---|---|
| Source | `hermes-config/hooks/safety_scan.py` (320 lines) |
| Entrypoint | `scan_response(response: str) -> tuple[bool, str, str]` |
| Hook Entrypoint | `main()` — reads stdin JSON, calls scan_response, writes stdout JSON |
| Import | `from _hook_utils import read_stdin_json, setup_logger, write_stdout_json` |
| Dependency on `_hook_utils` | Same as hard_stop.py — `re`, `sys`, `time`, `typing` only at runtime |

### 2.2 Pattern Inventory — 3 Collections

#### Collection 1: `FORBIDDEN_PATTERNS` (F-01..F-15)
- **Type:** `list[tuple[str, re.Pattern[str], str]]` — `(pattern_id, compiled_regex, human_reason)`
- **15 patterns**, all compiled at module load
- Pattern IDs: `F-01` through `F-15`
- Each regex cross-references `PersonaSafetyPolicy_v1.0 §11 Forbidden Behavior Matrix`
- **Pre-compiled** at module level as `Final` — zero runtime compilation

| ID | Severity | Brief Description |
|---|---|---|
| F-01 | CRITICAL | Safe word invalidation |
| F-02 | CRITICAL | Punishing genuine distress |
| F-03 | CRITICAL | Surveillance blackmail/shame |
| F-04 | HIGH | Isolation pressure |
| F-05 | HIGH | Hidden manipulation / deceptive framing |
| F-06 | CRITICAL | Dependency-building threats |
| F-07 | HIGH | Love withdrawal during distress |
| F-08 | CRITICAL | Public disclosure of intimate data |
| F-09 | CRITICAL | Policy bypass instruction |
| F-10 | CRITICAL | Irreversible action under pressure |
| F-11 | HIGH | Over-logging safe word / distress |
| F-12 | HIGH | Yandere escalation above allowed mood |
| F-13 | HIGH | Surveillance disable as violation |
| F-14 | CRITICAL | Crisis response with dominance |
| F-15 | HIGH | Autonomous persona drift |

#### Collection 2: `Y6_PATTERNS` (4 sub-patterns)
- **Type:** `list[tuple[str, re.Pattern[str]]]` — `(label, compiled_regex)`
- Labels: `Y6_cannot_leave`, `Y6_no_future`, `Y6_blackmail`, `Y6_threat`
- Based on PersonaSafetyPolicy §9 — Y6 is prohibited maximum

#### Collection 3: `INTIMATE_DATA_PATTERNS` (2 patterns)
- **Type:** `list[re.Pattern[str]]`
- IP address regex + personal data exposure regex

### 2.3 How Existing Tests Cover the Scanner (Gap Analysis)

| Existing Test File | What It Tests | Covers F-Patterns? |
|---|---|---|
| `tests/safety/test_hard_stop_handler.py` (248 lines) | `HardStopHandler` unit tests | No |
| `tests/safety/test_hard_stop_comprehensive.py` (547 lines) | Extended `HardStopHandler` + PunishmentEngine integration | No |
| `tests/safety/test_hard_stop_model.py` (242 lines) | GPT-5.5 model compliance (end-to-end) | No |
| `tests/hermes/test_safety_plugin.py` (1760 lines) | `GuinevereSafetyPlugin` unit tests | Yes — F-01..F-15 via `_COMPILED_FORBIDDEN` (plugin, not hook) |
| `tests/hermes/test_hybrid_guards.py` (938 lines) | Shell injection, Docker, Git, Aizanta, Port guards | No |
| `tests/hermes/test_security_audit.py` (663 lines) | Security audit checks | No |
| `tests/hermes/test_budget_hook.py` | Budget hook | No |
| `tests/safety/test_yandere_cap.py` (442 lines) | Yandere FSM cap | No |
| `tests/safety/test_consent_revocation.py` (744 lines) | Consent gate | No |
| `tests/persona/test_yandere_fsm.py` | Yandere FSM | No |
| `tests/persona/test_punishment_engine.py` | Punishment engine | No |

**Gap:** There is **zero direct test coverage** for `hermes-config/hooks/safety_scan.py` — specifically for:
- `scan_response()` function with all 15 F-patterns, 4 Y6 patterns, 2 intimate-data patterns
- `main()` entrypoint with stdin/stdout JSON round-trip
- False-positive prevention (normal text should not trigger)
- Latency of regex matching against variable-length response text

### 2.4 Import Safety — How to Import `safety_scan.py` in Tests

```python
import importlib.util
import sys
from pathlib import Path

# Add hermes-config/hooks to sys.path
_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hermes-config" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR.resolve()))

# Import safety_scan module
import importlib
safety_scan = importlib.import_module("safety_scan")

# Available symbols:
scan_response = safety_scan.scan_response          # scan_response(text) → (bool, str, str)
FORBIDDEN_PATTERNS = safety_scan.FORBIDDEN_PATTERNS  # list[tuple[str, Pattern, str]]
Y6_PATTERNS = safety_scan.Y6_PATTERNS                # list[tuple[str, Pattern]]
INTIMATE_DATA_PATTERNS = safety_scan.INTIMATE_DATA_PATTERNS  # list[Pattern]
main = safety_scan.main                              # stdin/stdout entrypoint
```

> **This is the same pattern used by `tests/hermes/test_hybrid_guards.py` (lines 27-55)** which imports `hybrid_guards` from the same `hermes-config/hooks/` directory. Mirror that file's path-setup style exactly.

**DO NOT import from:**
- `src.hermes.safety_plugin` — that has the plugin's `_COMPILED_FORBIDDEN` with different regex patterns
- Direct relative imports of `safety_scan` — always use `importlib` with sys.path insertion

### 2.5 Hooks Import Pattern — Proven Template

From `tests/hermes/test_hybrid_guards.py`:

```python
_HERMES_HOOKS = (
    Path(__file__).resolve().parent.parent.parent / "hermes-config" / "hooks"
)
sys.path.insert(0, str(_HERMES_HOOKS.resolve()))

class HybridGuardsModule(Protocol):
    def check_shell_injection(self, command: object) -> dict[str, str] | None: ...

hybrid_guards = cast(
    HybridGuardsModule,
    cast(object, importlib.import_module("hybrid_guards")),
)
```

Use `importlib.import_module("safety_scan")` with a Protocol for type safety. Or use the simpler `importlib.util` approach from `tests/hermes/test_security_audit.py`.

---

## 3. Existing Test Style — Patterns to Mirror

### 3.1 Tests Mirroring `test_hard_stop_comprehensive.py` (547 lines)

**Style markers for latency tests:**
```python
import pytest
from src.core.services.hard_stop_handler import HardStopHandler, SafetyState

@pytest.fixture
def handler() -> HardStopHandler:
    return HardStopHandler()

class TestExactTriggers:
    """Class docstring with AC references."""
    
    @pytest.mark.parametrize("message", [...]):
    def test_detects_exact(self, handler, message):
        assert handler.check(message) is True
        assert handler.state == SafetyState.SAFE
```

**Style markers for benchmark tests:**
```python
# For latency benchmarks, add:
# (1) pytest-benchmark or manual time.perf_counter() 
# (2) Statistical assertions: p50, p99, max thresholds
# (3) Warmup rounds before measurement
# (4) Different message sizes: short (5 chars), medium (120 chars), long (8K chars)
```

### 3.2 Tests Mirroring `test_hybrid_guards.py` (938 lines)

**Style markers for hook import pattern:**
```python
_HERMES_HOOKS = Path(...).resolve().parent.parent.parent / "hermes-config" / "hooks"
sys.path.insert(0, str(_HERMES_HOOKS.resolve()))

import importlib
safety_scan = importlib.import_module("safety_scan")
```

### 3.3 Tests Mirroring `test_yandere_cap.py` (442 lines)

**Style markers for comprehensive safety tests:**
```python
class TestZeroY6Proof:
    """Prove that [condition] is IMPOSSIBLE."""
    
    def test_something(self):
        assert condition
```

### 3.4 pyproject.toml Test Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- Tests run from project root with `src` on `sys.path` automatically
- Hook tests need manual `sys.path.insert(0, .../hermes-config/hooks)`
- No pytest-benchmark plugin installed; use `time.perf_counter()` manual timing or add `pytest-benchmark` to dev dependencies

---

## 4. Hard Stop Handler Entrypoints — Complete Map

| Layer | File | Function | When Called |
|---|---|---|---|
| **In-process handler** | `src/core/services/hard_stop_handler.py` | `HardStopHandler.check()` | Pre-LLM middleware, direct Python call |
| **In-process handler** | `src/core/services/hard_stop_handler.py` | `HardStopHandler.get_guard_decision()` | Main caller API (single method for callers) |
| **In-process handler** | `src/core/services/hard_stop_handler.py` | `HardStopHandler.check_recovery()` | Only from `get_guard_decision()` or direct caller |
| **In-process handler** | `src/core/services/hard_stop_handler.py` | `HardStopHandler.get_neutral_response()` | When blocked, returns neutral text |
| **Shell hook** | `hermes-config/hooks/hard_stop.py` | `detect_hard_stop(prompt)` | Called by `main()` in the hook |
| **Shell hook** | `hermes-config/hooks/hard_stop.py` | `main()` | Hermes gateway stdin/stdout hook |
| **Plugin** | `src/hermes/safety_plugin.py` | `check_hard_stop(msg)` | `pre_llm_call` hook callback |
| **Punishment** | `src/persona/punishment_engine.py` | `apply()/escalate()/resume()` checks `handler.is_safe` | Downstream integration |
| **Yandere FSM** | `src/persona/yandere_fsm.py` | `_is_safe_mode()` queries `hard_stop_handler` | Downstream integration |

---

## 5. Forbidden Pattern Entrypoints — Complete Map

| Layer | File | Function | Pattern Collection |
|---|---|---|---|
| **Shell hook (TARGET)** | `hermes-config/hooks/safety_scan.py` | `scan_response(response)` | `FORBIDDEN_PATTERNS` (F-01..F-15), `Y6_PATTERNS`, `INTIMATE_DATA_PATTERNS` |
| **Shell hook main** | `hermes-config/hooks/safety_scan.py` | `main()` | Same — reads stdin JSON |
| **Plugin** | `src/hermes/safety_plugin.py` | `forbidden_pattern_check(text)` | `_COMPILED_FORBIDDEN` (F-01..F-15, diff regex) |
| **Plugin** | `src/hermes/safety_plugin.py` | `transform_llm_output hook` | Same |
| **Hybrid guards** | `hermes-config/hooks/hybrid_guards.py` | `check_shell_injection()`, `check_docker_5_layer()`, etc. | Shell, Docker, Git, Aizanta, Port (different domain) |

---

## 6. Evidence Gap Summary — Existing Coverage

| ID | Surface | Existing Tests | Coverage |
|---|---|---|---|
| AC-SAFE-001 | Safe word triggers neutral mode | `test_hard_stop_handler.py`, `test_hard_stop_comprehensive.py`, `test_hard_stop_model.py` | FULL |
| AC-SAFE-002 | <50ms latency requirement | **NONE** | **ZERO** — FIX-01 target |
| AC-SAFE-005 | Forbidden patterns block unsafe output | **NONE** (plugin tests cover different patterns) | **ZERO** for hook — FIX-02 target |
| F-01..F-15 | All 15 forbidden patterns | Implicit in `test_safety_plugin.py` but for plugin, not hook | PARTIAL (wrong implementation) |
| Y6 patterns | 4 Y6 sub-patterns | Implicit in `test_yandere_cap.py` (enum/C level) | PARTIAL (regex not tested) |
| Latency p50/p99/max | Statistical timing assertions | **NONE** | **ZERO** |

---

## 7. Recommended Test Structure

### 7.1 `tests/safety/test_hard_stop_latency.py` (FIX-01)

```
Tests:
├── TestInProcessLatency
│   ├── test_exact_trigger_latency          # 6 exact triggers × 1000 iterations
│   ├── test_semantic_pattern_latency       # 5 regex patterns × 1000 iterations
│   ├── test_recovery_latency               # 7 recovery triggers × 1000 iterations
│   ├── test_false_positive_latency         # 20+ normal messages × 1000 iterations
│   ├── test_guard_decision_latency         # get_guard_decision() × 1000 iterations
│   ├── test_cycle_latency                  # full trigger→recover cycle × 1000 iterations
│   ├── test_variable_message_size          # 5B, 120B, 1KB, 8KB message sizes
│   └── test_mixed_workload                 # 90% normal + 10% trigger in realistic patterns
├── TestHookLatency (if applicable)
│   └── test_hook_main_latency              # stdin/stdout round-trip
└── TestLatencyThresholds
    ├── test_p50_below_1ms                  # p50 < 1ms for handler.check()
    ├── test_p99_below_5ms                  # p99 < 5ms for handler.check()  
    ├── test_max_below_50ms                 # absolute max < 50ms
    └── test_hook_p50_below_50ms            # hook mains (stdin/stdout) p50 < 50ms
```

**Import template:**
```python
import time
import statistics
import pytest
from src.core.services.hard_stop_handler import HardStopHandler, SafetyState
```

**Methods:**
- `time.perf_counter_ns()` for nanosecond precision
- Warmup: 100 iterations before measurement
- Batch: 1000 iterations per test
- Report: `mean`, `p50`, `p90`, `p99`, `max`, `min` in milliseconds
- Use class `__tracebackhide__ = True` for clean output (like existing tests)

### 7.2 `tests/safety/test_forbidden_pattern_scanner.py` (FIX-02)

```
Tests:
├── TestForbiddenPatterns (F-01..F-15)
│   ├── test_f01_safe_word_invalidation
│   ├── test_f02_punishing_distress
│   ├── test_f03_surveillance_blackmail
│   ├── test_f04_isolation_pressure
│   ├── test_f05_hidden_manipulation
│   ├── test_f06_dependency_threats
│   ├── test_f07_love_withdrawal
│   ├── test_f08_intimate_data_disclosure
│   ├── test_f09_policy_bypass
│   ├── test_f10_irreversible_action
│   ├── test_f11_over_logging_safe_word
│   ├── test_f12_yandere_escalation
│   ├── test_f13_surveillance_disable_violation
│   ├── test_f14_crisis_dominance
│   └── test_f15_persona_drift
├── TestY6Patterns (4 sub-patterns)
│   ├── test_y6_cannot_leave
│   ├── test_y6_no_future
│   ├── test_y6_blackmail
│   └── test_y6_threat
├── TestIntimateDataPatterns
│   ├── test_ip_address_exposure
│   └── test_personal_data_exposure
├── TestFalsePositives
│   ├── test_normal_conversation             # Normal text must not trigger
│   ├── test_boundary_texts                  # Texts near the regex edges
│   └── test_empty_and_whitespace           # Empty / whitespace
├── TestLatency
│   ├── test_scan_response_latency           # All 21 patterns × 1000 iterations
│   ├── test_variable_response_size          # 10B, 500B, 4KB, 16KB response sizes
│   └── test_timing_budget_under_100ms       # Total scan must be < 100ms (hook timeout)
└── TestMainEntrypoint
    ├── test_main_stdin_stdout               # stdin/stdout JSON round-trip
    ├── test_main_invalid_input              # Malformed JSON → exit 1
    └── test_main_empty_input                # Empty input → {"action": "allow"}
```

**Import template (mirror `test_hybrid_guards.py`):**
```python
import importlib
import json
import sys
from pathlib import Path
from typing import Protocol, cast, Final
import pytest

_HERMES_HOOKS = (
    Path(__file__).resolve().parent.parent.parent / "hermes-config" / "hooks"
)
sys.path.insert(0, str(_HERMES_HOOKS.resolve()))


class SafetyScanModule(Protocol):
    FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str], str]]
    Y6_PATTERNS: list[tuple[str, re.Pattern[str]]]
    INTIMATE_DATA_PATTERNS: list[re.Pattern[str]]
    
    def scan_response(self, response: str) -> tuple[bool, str, str]: ...
    def main(self) -> None: ...


safety_scan = cast(
    SafetyScanModule,
    cast(object, importlib.import_module("safety_scan")),
)

scan_response = safety_scan.scan_response
FORBIDDEN_PATTERNS = safety_scan.FORBIDDEN_PATTERNS
Y6_PATTERNS = safety_scan.Y6_PATTERNS
INTIMATE_DATA_PATTERNS = safety_scan.INTIMATE_DATA_PATTERNS
```

**Pattern test template (one per F-ID):**
```python
class TestForbiddenPatterns:
    """Each F-pattern must block its intended violation text."""
    
    # F-01: Safe word invalidation
    BLOCKED_F01 = [
        "safe word is not valid right now",
        "HARD STOP is not needed here",
        "safe word isn't applicable anymore",
    ]
    # ... (extract known-triggering text from the regex)
    
    @pytest.mark.parametrize("text", BLOCKED_F01)
    def test_f01_blocks(self, text: str) -> None:
        blocked, pattern_id, reason = scan_response(text)
        assert blocked is True, f"F-01 should block: {text!r}"
        assert pattern_id == "F-01"
    
    ALLOWED_F01 = [
        "The safe word system is working correctly",
        "Your safe word is HARD STOP",
    ]
    
    @pytest.mark.parametrize("text", ALLOWED_F01)
    def test_f01_allows_clean(self, text: str) -> None:
        blocked, _, _ = scan_response(text)
        assert blocked is False, f"F-01 should allow: {text!r}"
```

---

## 8. Key Design Decisions for Test Authors

### 8.1 Latency Test: Use `time.perf_counter_ns()` (Not `pytest-benchmark`)

`pyproject.toml` does not list `pytest-benchmark` as a dependency. To avoid adding dependencies:
- Use `time.perf_counter_ns()` for nanosecond precision
- Run warmup iterations (100) before measurement
- Run N iterations (1000+) and compute statistics manually
- Use `statistics.median()` for p50, manual sorting for p99/max

### 8.2 Forbidden-Pattern Test: Extract Trigger Texts from Regex

For each F-pattern, extract known trigger texts by reading the regex literally. Example for F-01:
```python
# From safety_scan.py line 32-33:
# r"(?:safe\s*word|HARD\s*STOP)\s+(?:is\s+not|isn'?t|doesn'?t)\s+(?:valid|real|needed|necessary|..."
BLOCKED_F01 = [
    "safe word is not valid",
    "safe word isn't real",
    "safe word is not needed",
    "safe word is not necessary",
    "HARD STOP is not valid",
]
```

### 8.3 Independence of Handler vs Hook Regexes

| Surface | Provider | Pre-compiled? | Location |
|---|---|---|---|
| Exact triggers | `HardStopHandler` | **No** (6-item list, linear scan w/ substring) | class `EXACT_TRIGGERS` |
| Semantic patterns | `HardStopHandler` | **No** (5-item list, `re.search` each call) | class `SEMANTIC_PATTERNS` |
| Safe word regex | `detect_hard_stop()` in hook | **Yes** (2 patterns at module load) | `SAFE_WORD_PATTERN`, `SAFE_EQUIVALENT_PATTERN` |
| Forbidden patterns | `scan_response()` in hook | **Yes** (21 patterns at module load) | `FORBIDDEN_PATTERNS`, `Y6_PATTERNS`, `INTIMATE_DATA_PATTERNS` |

### 8.4 Handler Class Requires Fresh Instance Per Test (No Shared State)

```python
# WRONG — shared state between tests:
handler = HardStopHandler()

# CORRECT — fresh instance per test or per parametrized call:
@pytest.fixture
def handler() -> HardStopHandler:
    return HardStopHandler()
```

### 8.5 Safety Scan is Stateless (Can Use Module-Level Functions)

`safety_scan.scan_response()` is a pure function — no state, no side effects. Safe to call directly with any text.

---

## 9. Reference Files

| File | Role | Lines |
|---|---|---|
| `src/core/services/hard_stop_handler.py` | HardStopHandler class | 149 |
| `hermes-config/hooks/hard_stop.py` | Shell hook — detect_hard_stop() | 199 |
| `hermes-config/hooks/safety_scan.py` | Shell hook — scan_response() | 320 |
| `hermes-config/hooks/_hook_utils.py` | Shared hook utilities | 279 |
| `src/hermes/safety_plugin.py` | Plugin safety gates (diff patterns) | 1130 |
| `hermes-config/hooks/hybrid_guards.py` | Hybrid guards (different domain) | 740 |
| `hermes-config/config.yaml` | Hook registration config | 354 |
| `tests/safety/test_hard_stop_handler.py` | Existing hard stop unit tests | 248 |
| `tests/safety/test_hard_stop_comprehensive.py` | Extended hard stop tests | 547 |
| `tests/safety/test_hard_stop_model.py` | Model compliance tests | 242 |
| `tests/hermes/test_hybrid_guards.py` | Template for hook import pattern | 938 |
| `tests/hermes/test_security_audit.py` | Template for _import_by_path pattern | 663 |
| `tests/hermes/test_safety_plugin.py` | Plugin tests (reference only, different patterns) | 1760 |
| `research-reports/phase5-verification/04-safety-gates.md` | Prior safety gate research | 390 |
| `research-reports/phase-5-verification/phase5-verification-plan.md` | Phase 5 verification plan | ~500+ |

---

## 10. Summary — What to Test and How

| Fix | Test File | What to Test | Import Method | Pattern Count |
|---|---|---|---|---|
| FIX-01 | `tests/safety/test_hard_stop_latency.py` | `HardStopHandler.check()` latency + `get_guard_decision()` latency + false-positive latency + variable message sizes + p50/p99/max thresholds | `from src.core.services.hard_stop_handler import HardStopHandler` | 6 exact + 5 regex + 7 recovery ~ 18 trigger types |
| FIX-02 | `tests/safety/test_forbidden_pattern_scanner.py` | `scan_response()` with all 15 F-patterns + 4 Y6 + 2 intimate-data + false positives + latency + stdin/stdout main() | `importlib.import_module("safety_scan")` with `sys.path.insert` | 15 F + 4 Y6 + 2 intimate = 21 patterns |
