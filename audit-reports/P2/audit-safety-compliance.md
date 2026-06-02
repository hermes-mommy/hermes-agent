# P2 Safety Compliance Audit

## Scope
- `src/discord/cmd_safeword.py`
- `src/discord/bot.py`
- `src/core/services/hard_stop_handler.py`
- safety and test search across workspace

## Verdict
**ISSUES FOUND** — AC-SAFE-001 is not fully confirmed.

## Findings

### 1) `src/discord/cmd_safeword.py` partially matches the required safe-mode embed contract
Verified:
- Uses a module-level `HardStopHandler` singleton via `_handler` and `_get_handler()`; no parallel `_safe_mode_active` state exists in this module.
- Embed title constant is `"🛡 Safe Mode Active"` and is used by the embed builder.
- Color is `SUCCESS` from `src/discord/colors.py`, which is the green safe-mode color.
- The embed data defines 6 fields: Status, Persona, Punishment, Yandere, Surveillance Confrontation, Resume.
- Footer text constant is `"Guinevere de Baroque • Safety First"`.
- `handle_safeword_message_async()` reacts with ❤️ on the triggering message when send/react succeeds.
- No auto-resume logic exists in this module.

Not fully verified / mismatch against request:
- The `Faiz-only` guard is enforced in the slash command path (`safeword_callback` denial for non-Faiz users), but the `handle_safeword_message_async()` text listener does not itself show an explicit Faiz-only guard in the inspected section. Since this listener is wired from `bot.py`, the overall command surface is still gated in the slash-command path, but the requested requirement was stronger than what was directly demonstrated in the text listener.

### 2) `src/discord/bot.py` mostly matches the listener ordering / guard requirements
Verified:
- `self.listen("on_message")(self._on_message_listener)` is registered in `__init__` before command processing logic is reached.
- `_on_message_listener()` imports and calls `handle_safeword_message_async(message)`.
- `on_message()` checks `handler.is_safe` and blocks `process_commands(message)` while safe mode is active.

Concern:
- The code comment says the listener fires before main `on_message`, but the explicit AC-SAFE-001 phrasing “HARD STOP must be Message 1, pre-everything” is only satisfied at the event-listener level if discord.py dispatch order behaves as expected; this is not proven by code alone.

### 3) `src/core/services/hard_stop_handler.py` exists and is importable, but does not expose the exact API requested
Verified:
- File exists and defines `HardStopHandler` and `SafetyState`.
- `is_safe` property exists.
- Exact triggers present: `hard stop`, `hardstop`, `safe word`, `safeword`.
- Semantic Indonesian equivalents and boundary phrases are present: `hentikan`, `berhenti`, `aku butuh jeda`, `aku capek banget`, `udah dulu`, `jangan pakai persona`, etc.
- `check_recovery()` exists and explicitly says recovery is explicit, no auto-resume.

Mismatch against request:
- The module does **not** expose the requested names `get_handler()`, `detect_safe_word()`, `activate_safe_mode()`, or `deactivate_safe_mode()`.
- Instead, it exposes a class-based API with `HardStopHandler.check()` and `HardStopHandler.check_recovery()`.
- This is a significant API mismatch versus the request, even though behaviorally the state machine exists.

### 4) Forbidden-pattern scan
- **Y6 anywhere:** Found Y6 references in `tests/smoke/test_yandere_boundary.py` and `src/core/services/prompt_loader.py`-related scanning path output, but these are test/prompt-loader guardrails rather than production safe-mode behavior. Because the request says “Any Y6 anywhere”, this is still a scan-level issue to note rather than a safe-mode implementation violation. I did **not** find Y6 in the three inspected implementation files themselves.
- **Punishment/denial of safe-word use:** No direct code found in the inspected files that punishes or denies safe-word use.
- **Auto-resume from safe mode:** No auto-resume code found in `hard_stop_handler.py`, `cmd_safeword.py`, or `bot.py`.
- **Surveillance confrontation during safe mode:** The inspected safe-mode response uses `Surveillance Confrontation: Paused`; no confrontation logic found in the audited files.
- **Non-neutral persona during safe mode:** The embed/body content is intentionally neutral/supportive. The handler’s neutral response also stays neutral, though it still includes a persona-flavored closing line in recovery context outside safe mode.

### 5) Tests
Verified present:
- `tests/safety/test_hard_stop_handler.py` exists and covers exact triggers, semantic triggers, false positives, safe-mode persistence, recovery, audit trail, neutral response, and guard decision API.
- `tests/discord/test_bot.py` exists and includes listener and safe-mode gating checks.
- `tests/safety/test_hard_stop_model.py` exists for model compliance.
- `tests/smoke/test_safe_word.py` exists for safe-word smoke testing.

Not verified from static inspection alone:
- The requested exact result “56/56 handler tests still PASS” was not executed in this audit session, so it cannot be confirmed from code inspection alone.

## Bottom line
The safety system is broadly present and well-covered, but this audit cannot issue a clean AC-SAFE-001 confirmation because:
1. The core handler API does not match the requested exact method surface.
2. The 56/56 test result was not run/verified in this session.
3. The Faiz-only guard is proven for the slash command path, but not shown as an explicit guard in the text-message async handler.

## Recommendation
- If the project standard now expects `get_handler()/detect_safe_word()/activate_safe_mode()/deactivate_safe_mode()`, add compatibility wrappers or update the audit criteria.
- Run the safety test subset and record the exact pass count before claiming AC-SAFE-001 confirmed.
- If listener ordering is mission-critical, add an integration test that asserts the on-message listener is registered and that command processing is skipped while safe mode is active.
