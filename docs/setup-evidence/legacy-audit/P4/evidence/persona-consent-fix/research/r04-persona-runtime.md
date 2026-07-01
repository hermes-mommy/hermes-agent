# R04 — PersonaPlugin Runtime Activation Audit

**Auditor:** Guinevere (orchestrator)
**Date:** 2026-06-27
**Status:** COMPLETE
**Source:** Direct inspection of `src/hermes/plugins/persona_plugin.py` (785 lines), `src/hermes/safety_plugin.py`, `src/core/services/prompt_loader.py`

---

## 1. Verdict

| Check | Verdict |
|-------|---------|
| PersonaPlugin exists and is complete | ✅ PASS — 785 lines, 4 hooks, stateless design |
| PersonaPlugin is registered with Hermes | ✅ PASS — `register(ctx)` function, hooks: pre_llm_call, post_llm_call, pre_tool_call, on_session_start |
| PersonaPlugin reads persona state from Redis DB5 | ✅ PASS — 14 keys read via pipeline, graceful degradation |
| Consent check before persona injection | ❌ FAIL — **Zero consent checks** |
| HARD STOP / safety check before injection | ❌ FAIL — **Zero safety checks** |
| PersonaPlugin injects into prompts | ✅ PASS — `pre_llm_call` appends `[PERSONA STATE]` block to system messages |
| Runtime proof of injection | ⚠️ UNKNOWN — No production log evidence reviewed |

---

## 2. Consent Gap — Critical

### 2.1 What PersonaPlugin Does

`pre_llm_call()` (line 536-611):
1. Reads persona state from Redis DB5 (`_read_persona_state()`)
2. Formats `[PERSONA STATE]` block (`_format_persona_block()`)
3. Injects into last system message in conversation
4. Returns `None` (always allow — non-blocking enrichment)

### 2.2 What It Does NOT Do

- Does NOT check `consent:grants` Redis key
- Does NOT check `consent.consent_ledger` DB table
- Does NOT check if consent has been revoked
- Does NOT check `HardStopHandler.is_safe`
- Does NOT check `SafeModeController.is_active`
- Does NOT check `guinevere:hard_stop` Redis key

### 2.3 The Consent Bypass

Scenario:
1. Faiz runs `/consent action:revoke category:persona`
2. `cmd_consent.py` removes `persona` from `consent:grants` Redis set
3. On next message, PersonaPlugin reads Redis DB5, formats persona block, injects it
4. **Persona behavior continues as if consent was never revoked**

This makes consent revocation **source-false** for the persona path.

---

## 3. Safety Gap — PersonaPlugin Ignores HARD STOP

### 3.1 Current state

The plugin docstring says (line 16-17):
> "Safety-compatible: Does NOT override or weaken safety_plugin.py."

This is true — it doesn't override safety. But it also doesn't RESPECT safety:
- During HARD STOP, persona injection should be neutral/empty
- During distress (D2+), persona injection should be suppressed
- The plugin unconditionally injects whatever Redis DB5 contains

### 3.2 Fix Required

Add to `pre_llm_call()`:
```python
# Check consent before injection
if not _consent_active("persona"):
    return None  # Skip persona injection

# Check HARD STOP before injection
if _hard_stop_active():
    return None  # Skip persona injection

# Check safe mode before injection
if _safe_mode_active():
    # Inject neutral/minimal state only
    state = _get_neutral_state()
```

---

## 4. PersonaPlugin Architecture

### 4.1 Redis DB5 Keys Read

| Key | Purpose |
|-----|---------|
| `guinevere:mood_variant` | Current mood variant |
| `guinevere:yandere_level` | Yandere level Y0-Y5 |
| `guinevere:punishment_level` | Punishment level L0-L5 |
| `guinevere:punishment_reason` | Reason for active punishment |
| `guinevere:reward_tier` | Reward tier T0-T5 |
| `guinevere:distress_state` | Distress state D0-D4 |
| `guinevere:last_interaction` | Last interaction timestamp |
| `guinevere:interaction_count` | Daily interaction counter |
| `guinevere:safe_word` | Configured safe word |
| `guinevere:relationship_stage` | R1-R4 stage |
| `guinevere:emotional_residue` | Emotional residue |
| `guinevere:residue_decays_at` | Residue decay timestamp |
| `guinevere:recent_milestones` | Last 5 milestones |
| `guinevere:corruption_mode` | Corruption mode |

### 4.2 Injection Format

```
[PERSONA STATE]
Mood Variant: {mood_variant}
Yandere Level: Y{level}
Punishment Active: L{level} - {reason}
Reward Tier: T{tier}
Distress State: D{state}
Safe Word: {safe_word}
Interactions Today: {count}
Last Interaction: {timestamp}
Time Band: {time_band}
Relationship: {stage} {stage_name}
Emotional Residue: {residue}
Recent Milestones: {milestones}
Corruption Mode: {corruption_mode}
[END PERSONA STATE]
```

---

## 5. Fixes Required

### 5.1 Add consent check function
```python
def _check_consent(scope: str = "persona") -> bool:
    """Check if consent is granted for the given scope."""
    try:
        redis_mod = importlib.import_module("redis")
        r = redis_mod.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, ...)
        grants_raw = r.get("consent:grants")
        r.close()
        if grants_raw is None:
            return True  # No consent data = default allow
        grants = json.loads(grants_raw)
        return scope in grants
    except Exception:
        return True  # Fail-open: if Redis is down, allow (graceful degradation)
```

### 5.2 Add HARD STOP check
```python
def _check_hard_stop() -> bool:
    """Check if HARD STOP is active."""
    try:
        redis_mod = importlib.import_module("redis")
        r = redis_mod.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, ...)
        val = r.get("guinevere:hard_stop")
        r.close()
        return val == "1"
    except Exception:
        return False
```

### 5.3 Modify pre_llm_call to gate on consent + safety
```python
def pre_llm_call(self, **kwargs):
    if not _check_consent("persona"):
        logger.info("persona_plugin_consent_revoked_skipping")
        return None
    if _check_hard_stop():
        logger.info("persona_plugin_hard_stop_active_skipping")
        return None
    # ... existing injection logic
```

---

## 6. Test Requirements

1. `test_persona_plugin_consent_revoked_skips_injection`
2. `test_persona_plugin_hard_stop_skips_injection`
3. `test_persona_plugin_safe_mode_neutral_injection`
4. `test_persona_plugin_consent_granted_injects_normally`