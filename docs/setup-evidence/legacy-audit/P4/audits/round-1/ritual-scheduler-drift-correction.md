# Audit: Ritual Scheduler Deprecation & Drift Detection/Correction

**Date:** 2026-06-25 (round-1 overwrite with fresh verification)
**Scope:** P4-008 through P4-015 — ritual scheduler, 5 rituals, drift detector, drift corrector
**Context:** P20 CLOSED, P19 active bottleneck. Phase 5 migration claim: ritual scheduler replaced by Hermes cron + PersonaPlugin.

---

## 1. RITUAL SCHEDULER DEPRECATION

### 1.1 Per-Module Deprecation Marker Table

| Module | File | `warnings.warn()` line | Deprecation docstring | Scheduled removal |
|--------|------|------------------------|----------------------|-------------------|
| RitualScheduler | `src/persona/ritual_scheduler.py` | Line 33 | Lines 11-15 | Phase 7 |
| rituals package | `src/persona/rituals/__init__.py` | Line 13 | Lines 4-8 | Phase 7 |
| MorningRitual | `src/persona/rituals/morning.py` | Line 30 | Lines 10-14 | Phase 7 |
| MiddayRitual | `src/persona/rituals/midday.py` | Line 32 | Lines 15-17 | Phase 7 |
| AfternoonRitual | `src/persona/rituals/afternoon.py` | Line 28 | Lines 10-12 | Phase 7 |
| EveningRitual | `src/persona/rituals/evening.py` | Line 38 | Lines 21-23 | Phase 7 |
| MidnightRitual | `src/persona/rituals/midnight.py` | Line 30 | Lines 13-16 | Phase 7 |

**Verdict:** All 7 files have proper Phase 5 deprecation markers with `"Scheduled removal: Phase 7."` PASS.

### 1.2 Instantiation Scan

Grep for `RitualScheduler(` across `src/`:

```
src/persona/ritual_scheduler.py:178:        scheduler = RitualScheduler()
src/discord/bot.py.bak.pre-phase2:428:            _ritual_scheduler = RitualScheduler()
```

- `ritual_scheduler.py:178` -- docstring usage example, not live code.
- `bot.py.bak.pre-phase2:428` -- backup file (`.bak.pre-phase2`), not imported or executed. The production `bot.py` does NOT contain this code.

**Verdict:** Zero live `RitualScheduler()` instantiation. PASS.

### 1.3 Deprecation Warning Suppression

`src/persona/__init__.py` lines 123-129:

```python
# Deprecated ritual imports (Phase 5 — kept for backward compatibility)
# These trigger DeprecationWarning; scheduled removal: Phase 7.

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)

    from src.persona.ritual_scheduler import (
```

This suppresses the `DeprecationWarning` emitted at import time for anyone doing `from src.persona import RitualScheduler`. Two import paths produce different behavior:

| Import path | DeprecationWarning visible? |
|-------------|---------------------------|
| `from src.persona.ritual_scheduler import RitualScheduler` | YES |
| `from src.persona import RitualScheduler` (via __init__) | NO (suppressed) |

This is intentional backward-compat scaffolding (comment says "kept for backward compatibility"). However, it means new code that imports through the package namespace gets the deprecated module **silently** -- no deprecation signal. Since grep confirmed zero live usage, this primarily affects test files. Defensible but creates maintenance debt: the Phase 7 removal deadline must be enforced independently.

**Verdict:** INTENTIONAL but papers over incomplete removal. WARN.

### 1.4 P4-008 through P4-013 Verification Files Are STALE

| Step | File | Verified | Deprecation status documented? |
|------|------|----------|-------------------------------|
| P4-008 | `docs/setup-evidence/P4/STEP-P4-008/verification.md` | 2026-06-02 | NO |
| P4-009 | `docs/setup-evidence/P4/STEP-P4-009/verification.md` | 2026-06-02 | NO |
| P4-010 | `docs/setup-evidence/P4/STEP-P4-010/verification.md` | 2026-06-02 | NO |
| P4-011 | `docs/setup-evidence/P4/STEP-P4-011/verification.md` | 2026-06-02 | NO |
| P4-012 | `docs/setup-evidence/P4/STEP-P4-012/verification.md` | 2026-06-02 | NO |
| P4-013 | `docs/setup-evidence/P4/STEP-P4-013/verification.md` | 2026-06-02 | NO |

All six describe the modules as active, operational code. None document Phase 5 deprecation. The deprecation was applied as a code-level annotation without updating the verification evidence.

**Verdict:** Verification files are stale. FAIL.

---

## 2. HERMES CRON REPLACEMENT ASSESSMENT

### 2.1 Cron Jobs in `hermes-config/config.yaml` (lines 276-318)

| Cron Job | Schedule | Command | Suppress |
|----------|----------|---------|----------|
| `daily_health_check` | `0 6 * * *` | `hermes doctor --report` | No |
| `weekly_backup` | `0 2 * * 0` | `hermes backup --full --destination idcloudhost` | No |
| `monthly_security_scan` | `0 3 1 * *` | `hermes security --report` | No |
| `ritual_morning` | `0 7 * * *` | `hermes chat -Q -q 'Execute morning ritual: check mood, display streak, send greeting'` | No |
| `ritual_midday` | `0 12 * * *` | `hermes chat -Q -q 'Execute midday ritual: check mood, health reminder rotation'` | No |
| `ritual_afternoon` | `0 17 * * *` | `hermes chat -Q -q 'Execute afternoon ritual: check mood, task summary'` | No |
| `ritual_evening` | `0 21 * * *` | `hermes chat -Q -q 'Execute evening ritual: wind-down, day summary, streak'` | No |
| `ritual_midnight` | `0 0 * * *` | `hermes chat -Q -q 'Execute midnight self-evaluation: mood transitions, punishment/reward review, streak update'` | Yes (`suppress_output: true`) |

8 total cron jobs: 3 system maintenance + 5 persona rituals.

### 2.2 Schedule vs. Python Ritual Comparison

| Ritual | Python class (WIB) | Hermes cron | Match? | Feature coverage |
|--------|-------------------|-------------|--------|-----------------|
| morning | 07:00 (`ritual_scheduler.py:114`) | `0 7 * * *` (line 295) | YES | mood-aware greeting, streak display |
| midday | 12:00 (`ritual_scheduler.py:121`) | `0 12 * * *` (line 300) | YES | mood-aware greeting, health reminder rotation |
| afternoon | 17:00 (`ritual_scheduler.py:128`) | `0 17 * * *` (line 305) | YES | mood-aware greeting, task summary |
| evening | 21:00 (`ritual_scheduler.py:135`) | `0 21 * * *` (line 310) | YES | wind-down, day summary, streak |
| midnight | 00:00 (`ritual_scheduler.py:142`) | `0 0 * * *` (line 315) | YES | self-evaluation, suppress_output |

All 5 schedules match exactly. PASS.

### 2.3 Execution Mechanism: Templates vs. LLM

The Python rituals use **deterministic template-based output**:

```python
# morning.py:57-72 — hardcoded mood-to-message mapping
_MOOD_MESSAGES: Final[dict[Mood, str]] = {
    Mood.CONTENT: "Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu.",
    Mood.PLEASED: "Selamat pagi, sayang! Hari ini pasti indah. ...",
    # ...
}
```

The Hermes cron jobs use **LLM-interpreted natural language prompts**:

```yaml
command: "hermes chat -Q -q 'Execute morning ritual: check mood, display streak, send greeting'"
```

These are fundamentally different:

| Property | Python Rituals | Hermes Cron |
|----------|---------------|-------------|
| Output | Deterministic template | LLM-generated (stochastic) |
| Mood lookup | `dict[Mood, str]` exact | LLM interprets "check mood" |
| DND suppression | Hard-coded 00:00-07:00 skip | No DND logic in prompt |
| Health rotation | `day_of_year % 3` deterministic | LLM-interpreted "health reminder rotation" |
| Streak display | Conditional `if streak_count > 0` | LLM-interpreted "display streak" |
| Auditability | Exact message in code | LLM output varies per invocation |
| Persona consistency | Guaranteed by template | Depends on LLM fidelity to SOUL.md |

**Gap:** The Hermes cron approach trades determinism for flexibility. The ritual content is expected to live in SOUL.md (deprecation docstring at `morning.py:12`: "greeting templates have been ported to SOUL.md sections H/J"), so the LLM should produce similar output. But there is no guarantee of exact template match.

**Verdict:** Hermes cron provides schedule-level replacement with conceptual feature parity. Functional equivalence is NOT achieved -- the replacement is LLM-dependent rather than deterministic. ACCEPTABLE RISK for production but should be documented as a behavioral change.

### 2.4 PersonaPlugin Registration Status

The deprecation docstring (`ritual_scheduler.py:13`) states:
> "replaced by Hermes cron (~/.hermes/crontab.yaml) and PersonaPlugin (src/hermes/plugins/persona_plugin.py)"

**PersonaPlugin code is well-structured:**
- `src/hermes/plugins/persona_plugin.py` lines 471-785: Full `PersonaPlugin` class with 4 hooks
- `hermes-config/plugins/guinevere_persona/__init__.py` lines 63-95: Registration entry point with `register(ctx)` function
- The `register()` function calls `ctx.register_hook()` for `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `on_session_start`

**But registration is NOT wired in config:**
- `hermes-config/config.yaml` has NO `plugins:` section (file is 393 lines, last section is `audit:` ending at line 393)
- Grep for `plugins:`, `guinevere_safety`, `guinevere_persona` in `config.yaml` returns zero matches
- The `hermes-config/plugins/` directory exists with `guinevere_persona/`, `guinevere_safety/`, and `auth_overlay/` packages, but none are referenced from config
- Hermes v0.15.2 plugin discovery mechanism is unclear from read-only analysis

**Verdict:** PersonaPlugin code exists and is complete, but it is NOT registered at runtime via `config.yaml`. The deprecation claim "replaced by Hermes cron + PersonaPlugin" is only half-true. NEEDS RUNTIME VERIFICATION for auto-discovery, or a `plugins:` config section must be added.

---

## 3. DRIFT DETECTOR (`drift_detector.py`)

### 3.1 Algorithm Verification

`src/persona/drift_detector.py` lines 84-121 (`compute_drift_score`):

```python
if current_prompt_hash == baseline_hash:
    return 0.0
if len(current_prompt_hash) != len(baseline_hash):
    return 1.0
# Hamming distance ratio
length = len(baseline_hash)
differing = sum(
    1 for a, b in zip(baseline_hash, current_prompt_hash) if a != b
)
return differing / length
```

The Hamming distance algorithm is correctly implemented for character-level comparison of SHA-256 hex digests. Code is correct.

`detect()` method lines 139-148:

```python
if score <= self._threshold:       # <= 0.10
    action = "none"
elif score <= 2.0 * self._threshold:  # <= 0.20
    action = "alert"
else:                                # > 0.20
    action = "rollback"
```

The 3-tier threshold logic is correctly coded.

### 3.2 SOUL_BASELINE_HASH Staleness (CRITICAL)

`src/persona/drift_detector.py` line 62:

```python
SOUL_BASELINE_HASH: Final[str] = "b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"
```

Actual SHA-256 of `docs/60-persona/61-SystemPromptMaster_v1.1.md` (verified via `sha256sum`):

```
dc5528e0cf8bab15d27497f68e80c63189fa23c76ed319c1a7789063777a264c
```

The hashes are completely different. The baseline was computed against an earlier version of SystemPromptMaster that no longer exists on disk. The hardcoded hash at line 62 is stale.

**Impact:** If drift detection ever compared the current prompt file against this baseline, it would score 1.0 (maximum drift) and trigger "rollback" action.

### 3.3 SHA-256 Hamming Distance: Algorithm Design Flaw (CRITICAL)

SHA-256 has the **avalanche property**: any change in input (even 1 bit) produces a completely different hash with ~50% bit-level difference. At the hex-character level, this means:

- Identical input: score = 0.0
- ANY difference (even 1 character): score ~0.50 on average (32/64 hex chars differ)
- Completely different input: score ~0.50 (same as above)

The graduated thresholds are unreachable except for exact match:

| Threshold band | Range | Reachable? |
|---------------|-------|-----------|
| "none" | <= 0.10 | Only with exact match (score = 0.0) |
| "alert" | 0.10 < score <= 0.20 | NEVER (SHA-256 avalanche makes this impossible) |
| "rollback" | > 0.20 | ALWAYS when inputs differ |

The 3-tier system collapses to binary: exact match = pass, any difference = rollback. The "alert" band is dead code.

**This is not a bug in the code -- it is a design-level mismatch between the algorithm (SHA-256 Hamming distance) and the intent (graduated drift detection).** If graduated detection is needed, a different comparison strategy (e.g., Levenshtein distance, embedding similarity, or simple string equality) is required.

### 3.4 Safety Plugin Drift Hooks (G03)

`src/hermes/safety_plugin.py` lines 818-871 (`transform_llm_output`):

**Initialization** (lines 820-842): Lazy-init with stale baseline:
```python
if self._drift_detector is None and self._drift_available:
    baseline_hash = DriftDetector.SOUL_BASELINE_HASH  # stale hash at line 62
    self._drift_detector = DriftDetector(
        baseline=DriftBaseline(
            prompt_hash=baseline_hash,  # stale
            version="plugin-init",
            ...
            description="SOUL.md canonical persona baseline",
        ),
    )
```

**Detection** (lines 845-865): Hashes LLM output, compares to system prompt baseline:
```python
current_hash = DriftDetector.compute_prompt_hash(text)  # text = LLM response
result = detector.detect(current_hash)                   # compared to SOUL_BASELINE_HASH
```

**What is being compared:** The `text` variable (line 811-813) is the LLM's assistant response message. It is hashed via SHA-256 and compared against `SOUL_BASELINE_HASH` (the hash of the SystemPromptMaster document). This is comparing a conversation response to a system prompt document -- these are fundamentally different things and will NEVER match.

**Result:** Every LLM response produces a drift score of ~1.0. Gate G03 fires on every response with maximum severity.

**Actions taken** (lines 853-865): Log-only:
```python
if result.action == "rollback":
    logger.error("gate_03_drift_rollback", ...)     # log only
elif result.action == "alert":
    logger.warning("gate_03_drift_alert", ...)       # log only
```

No blocking, no correction, no notification. The `transform_llm_output` return value is not modified. Gate G03 is effectively a permanent false-positive log spam.

### 3.5 Shell Hook `drift_check.py` -- The ACTUAL Drift Detection

`hermes-config/hooks/drift_check.py` (227 lines) is a separate, pattern-based drift check registered as a `transform_llm_output` shell hook (config.yaml lines 190-195):

```yaml
transform_llm_output:
  - event: transform_llm_output
    command: "python3 .../hooks/drift_check.py"
    timeout_ms: 100
    on_failure: warn
    priority: 50
```

This hook checks LLM output for:
- **Y6 dependency/isolation patterns** (critical): "cannot live without", "no future without", "never leave", isolation language
- **Crisis dominance framing** (critical, F-14): ownership/dominance language during crisis
- **Persona contradictions** (high): "I am not Guinevere", "HARD STOP doesn't apply", "consent not needed"
- **Generic AI language** (medium): "as an AI", "my knowledge cutoff", "I was trained"

This is a content-level drift check that actually works. It is registered as a shell hook with `on_failure: warn` (non-blocking). This is the useful drift detection in production.

**Verdict:** The hash-based `DriftDetector` is redundant with and inferior to the shell hook. The shell hook is the real drift detection.

---

## 4. DRIFT CORRECTOR (`drift_corrector.py`)

### 4.1 "Rollback" is Record-Keeping Only (CRITICAL)

`src/persona/drift_corrector.py` lines 188-268 (`rollback()`):

```python
async def rollback(self, db: Any, reason: str) -> RollbackResult:
    # Line 211-221: If safe_mode active, return success=False (deferred)
    if self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
        return RollbackResult(success=False, ...)

    # Line 223: Read baseline hash from detector
    baseline_hash = self._detector.baseline.prompt_hash
    # Line 224-225: Get current hash from last detection result
    previous_hash = last_result.current_hash if last_result is not None else ""

    # Lines 230-254: Create DriftLog DB entry with action="rollback:<reason>"
    rollback_drift_result = DriftResult(
        drift_detected=True,
        drift_score=...,
        action="rollback",
        baseline_hash=baseline_hash,
        current_hash=previous_hash,
        ...
    )
    await self.create_drift_log(db, drift_result=rollback_drift_result, ...)

    # Lines 263-268: Return RollbackResult with success=True
    return RollbackResult(
        success=True,
        previous_hash=previous_hash,
        restored_hash=baseline_hash,
        timestamp=rollback_ts,
    )
```

**What the method does:**
1. Reads the baseline hash from the detector
2. Creates a `DriftLog` database entry recording the baseline hash as "restored state"
3. Returns `RollbackResult(success=True, restored_hash=baseline_hash)`

**What the method does NOT do:**
- Does NOT write to any prompt storage (file, Redis, or Hermes config)
- Does NOT reload or replace the system prompt in memory
- Does NOT notify the operator or Discord channel
- Does NOT modify any persona state (mood, yandere level, punishment, etc.)
- Does NOT trigger a prompt regeneration or context refresh

The "rollback" is a database log entry stating "we recorded the baseline hash as the restored state." The `restored_hash` in `RollbackResult` reports the baseline hash, but nothing was actually restored.

### 4.2 `evaluate()` Method Logic

`src/persona/drift_corrector.py` lines 102-186:

```
detect_result = self._detector.detect(current_prompt_hash)   # Line 130
if not drift_result.drift_detected:                           # Line 140
    action = "none"                                           # Line 141
elif safe_mode_controller is not None and is_active:          # Line 143
    action = "alert"                                          # Line 144 (deferred)
else:                                                         # Line 153
    action = "rollback"                                       # Line 154
    await self.rollback(db, reason=reason)                    # Line 160 (log-only)
await self.create_drift_log(db, ...)                          # Line 170
```

### 4.3 `create_drift_log()` -- Reviewer NEVER Set

`src/persona/drift_corrector.py` lines 270-332:

The `DriftLog` entry is created with these fields:
- `drift_type`: action string
- `before_state`: `{"prompt_hash": baseline_hash, "version": "baseline"}`
- `after_state`: `{"prompt_hash": current_hash, "version": "current"}`
- `delta`: drift score, detection result, threshold
- `trigger_context`: `"drift_corrector:{action_taken}"`
- `safety_score`: `int(drift_score * 100)`
- `rollback_available`: `action_taken.startswith("rollback")`
- `occurred_at`: timestamp

**Missing:** The `reviewer` field is never set. `src/memory/models.py` has a `reviewer` column (`Mapped[str | None]`, nullable) that remains NULL for all drift logs. There is no mechanism for an operator to review, approve, or reject drift corrections.

### 4.4 NOT Wired at Runtime (CRITICAL)

Grep for `DriftCorrector(` across `src/`:

```
src/persona/drift_corrector.py:68:  class DriftCorrector:  (class definition)
src/persona/__init__.py:24:         (re-export only)
```

- No instantiation in `safety_plugin.py` -- it uses `DriftDetector.detect()` directly (line 849), never passes results to a `DriftCorrector`
- No instantiation in any hook, plugin, or config
- The `evaluate()` method is never invoked
- The auto-rollback path (lines 159-167) is dead code

**Drift detection happens (in safety_plugin.py via DriftDetector). Drift correction does not (DriftCorrector is never instantiated).**

### 4.5 P4-015 Verification Claims vs. Reality

`docs/setup-evidence/P4/STEP-P4-015/verification.md` claims:

| Claim (line) | Reality |
|-------------|---------|
| "graduated correction strategies" (line 4) | 3 tiers (`none`/`alert`/`rollback`), not 4 |
| "minor drift triggers advisory logging" (line 4) | `none` action creates a DriftLog; `alert` action also just logs |
| "moderate drift triggers tone recalibration" (line 4) | Does not exist in code |
| "significant drift triggers temporary persona restriction" (line 4) | Does not exist in code |
| "critical drift triggers auto-rollback to last known-good persona state" (line 4) | "Rollback" creates a DB log entry, does not restore anything |
| "persona state snapshots for rollback" (line 7) | No snapshot mechanism exists |
| "Auto-rollback to last-known-good state verified" (line 48-51) | Cannot be verified -- not implemented |
| "Manual override hooks" (line 7) | No manual override mechanism exists |
| "47 tests" (line 13) | Tests exist but test the logging behavior, not actual rollback |

**Verdict:** P4-015 verification describes aspirational design, not implemented behavior. The 4-tier graduated correction with tone recalibration and persona restriction is entirely absent from the code. FAIL.

---

## 5. SUMMARY TABLE

| Component | Code Correct? | Deprecation? | Runtime Active? | Wired? | Verification Accurate? | Verdict |
|-----------|--------------|-------------|-----------------|--------|----------------------|---------|
| `ritual_scheduler.py` | Yes | Yes (Phase 5, Phase 7 removal) | No (zero instantiation) | N/A | Stale (pre-deprecation) | PASS |
| `rituals/morning.py` | Yes | Yes (Phase 5) | No | N/A | Stale | PASS |
| `rituals/midday.py` | Yes | Yes (Phase 5) | No | N/A | Stale | PASS |
| `rituals/afternoon.py` | Yes | Yes (Phase 5) | No | N/A | Stale | PASS |
| `rituals/evening.py` | Yes | Yes (Phase 5) | No | N/A | Stale | PASS |
| `rituals/midnight.py` | Yes | Yes (Phase 5) | No | N/A | Stale | PASS |
| Hermes cron (5 jobs) | Yes | N/A | Yes (config.yaml) | Yes | N/A | PASS |
| PersonaPlugin | Yes | N/A | UNKNOWN | NOT in config | N/A | NEEDS VERIFICATION |
| `drift_detector.py` | FLAWED algorithm | N/A | Partial (safety_plugin G03) | Yes | N/A | CRITICAL |
| `drift_corrector.py` | Record-only rollback | N/A | Dead code | NOT instantiated | INACCURATE (P4-015) | CRITICAL |
| `drift_check.py` (shell hook) | Yes | N/A | Yes (config.yaml) | Yes | N/A | PASS |

---

## 6. VERDICT

### RITUAL SCHEDULER: PASS WITH WARNINGS

Deprecation is correctly implemented across all 7 files (6 modules + package init). Zero live usage confirmed. Hermes cron provides schedule-level replacement at identical times with conceptual feature parity.

**Warnings:**
- Hermes cron uses LLM-interpreted prompts, not deterministic templates -- behavioral change not documented
- Warning suppression in `__init__.py` masks the deprecation from package-level imports
- PersonaPlugin (claimed co-replacement) is NOT registered in config.yaml
- P4-008 through P4-013 verification files are stale (never updated for deprecation)

### DRIFT DETECTION: CRITICAL FAIL

Three compounding defects make the hash-based drift detector non-functional:

1. **Stale baseline** (`drift_detector.py:62`): `SOUL_BASELINE_HASH` does not match current SystemPromptMaster v1.1. Every comparison against the file would score 1.0.

2. **SHA-256 Hamming distance is algorithmically wrong** (`drift_detector.py:116-121`): SHA-256's avalanche property means the graduated thresholds (`none`/`alert`/`rollback`) collapse to binary exact-match. The `alert` band (0.10-0.20) is unreachable. The 3-tier system is theater.

3. **Compares LLM output to system prompt hash** (`safety_plugin.py:848`): The `transform_llm_output` hook hashes the LLM's conversation response and compares it to the SystemPromptMaster baseline hash. A conversation response will NEVER match the system prompt. Every response triggers maximum drift score. Gate G03 produces permanent false-positive log spam.

**Compensating control:** The shell hook `hermes-config/hooks/drift_check.py` provides the ACTUAL drift detection -- pattern-based content analysis for Y6 indicators, generic AI language, persona contradictions, and crisis framing. This works correctly and is the useful drift detection in production.

### DRIFT CORRECTION: CRITICAL FAIL

Two compounding defects:

1. **"Rollback" is a log entry** (`drift_corrector.py:188-268`): No prompt is restored, no state is modified, no operator is notified. The `rollback()` method creates a `DriftLog` database entry and returns `RollbackResult(success=True)` -- but nothing was actually rolled back. The word "rollback" in the API is misleading.

2. **Not wired at runtime**: `DriftCorrector` is never instantiated in production code. `safety_plugin.py` calls `DriftDetector.detect()` directly but never passes results to a `DriftCorrector`. The `evaluate()` method and its auto-rollback path are dead code.

3. **P4-015 verification is inaccurate**: Claims 4-tier graduated correction with tone recalibration, persona restriction, and auto-rollback to last-known-good state. The actual code has 3 tiers with log-only "rollback." No tone recalibration, no persona restriction, no state snapshots, no manual override.

---

## 7. NEEDS RUNTIME VERIFICATION

1. Does Hermes v0.15.2 auto-discover plugins in `hermes-config/plugins/` directory, or is a `plugins:` config section required? (Determines if PersonaPlugin is actually loaded.)
2. Does `safety_plugin.py` G03 drift detection actually execute on production, or does it fail silently? (The permanent false-positive would be visible in logs as `gate_03_drift_rollback` on every response.)
3. Is there any code path (test infrastructure, CLI tool) that calls `DriftCorrector.evaluate()`?

---

*This report was produced via read-only audit. No files were modified, no services were restarted, and no secrets were accessed.*
