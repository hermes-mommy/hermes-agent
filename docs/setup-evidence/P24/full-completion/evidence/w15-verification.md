# W15 Discord Gateway — Verification Evidence

**Wave**: W15 (M13 Discord Gateway)
**Date**: 2026-06-29
**Status**: PASS

---

## Files Created

```
guinevere/discord/__init__.py         —  27 lines — re-exports GuinevereBot, CommandRegistry
guinevere/discord/bots.py             — 339 lines — 3 bot identities, GuinevereBot, AutonomousInitiator
guinevere/discord/commands.py         — 726 lines — 41 COMMAND_SPECS, callbacks, CommandRegistry
guinevere/discord/gateway_patch.py    — 138 lines — wire(agent), register_platform
guinevere/discord/_infrastructure.py  — 773 lines — colors, auth, intents, embed, notifications, shadow, project-session, conversational
tests/p24/test_discord.py             — 543 lines — 52 tests
```

## Files Modified

```
src/x_poster/discord/commands.py      — updated imports from src.discord → guinevere.discord._infrastructure
src/x_poster/discord/upload_handler.py — updated imports from src.discord → guinevere.discord._infrastructure
```

## Files Deleted

```
src/discord/ (62 .py files) — fully deleted after porting
```

---

## Verification Commands

### 1. Basic import
```
$ .venv/Scripts/python.exe -c "from guinevere.discord import GuinevereBot, CommandRegistry; print('OK')"
OK
```

### 2. Command count (>= 41)
```
$ .venv/Scripts/python.exe -c "from guinevere.discord.commands import COMMAND_SPECS; print('commands:', len(COMMAND_SPECS))"
commands: 41
```

### 3. Bot identities (3)
```
$ .venv/Scripts/python.exe -c "from guinevere.discord.bots import BOT_IDENTITIES; print('bots:', len(BOT_IDENTITIES))"
bots: 3
```

### 4. pytest (0 failures)
```
$ .venv/Scripts/python.exe -m pytest tests/p24/test_discord.py -q
....................................................                     [100%]
52 passed, 14 warnings in 0.99s
```

### 5. src/discord/ deleted
```
$ ls src/discord/ 2>&1
ls: cannot access 'src/discord/': No such file or directory
```

### 6. No forbidden strings
```
$ grep -rn 'consent_gate\|hard_stop\|safe_mode' guinevere/discord/
(exit code 1 — 0 matches)
```

### 7. gateway.run not broken
```
$ .venv/Scripts/python.exe -c "import gateway.run; print('gateway.run OK')"
gateway.run OK
```

---

## Stale Import Cleanup

| Old Import | Replacement |
|---|---|
| `src.surveillance.consent_gate` | Removed — no-op, direct response |
| `src.persona.safe_mode` | Removed — DistressDetectorStub |
| `src.persona.mood_engine` | `guinevere.emotions` (stub fallback) |
| `src.loops.manager` | `guinevere.consciousness.infra` |
| `src.discord.colors` | `guinevere.discord._infrastructure` |
| `src.discord._embed_utils` | `guinevere.discord._infrastructure` |
| `src.discord._auth_guard` | `guinevere.discord._infrastructure` |

## Key Design Decisions

1. **Only 1 bot exists** (GuinevereBot). Pharsa and Company are identity dataclasses (BotIdentity) for future expansion, not separate bot implementations.
2. **No autonomous initiation existed** — AutonomousInitiator is new code tied to M3 consciousness via AUTONOMOUS_CHAT env var.
3. **consent_gate is NOT a command gate** — it's a surveillance-scoping module. Removed cleanly from all callbacks.
4. **gateway_patch.py** uses platform_registry to register Discord as a plugin adapter. `wire(agent)` is a parent-owned append function.
5. **D2 compliance** — no live Discord tokens; all tests use mock discord.py interactions.
