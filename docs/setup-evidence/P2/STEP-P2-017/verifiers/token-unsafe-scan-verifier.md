# Token / Unsafe Pattern Scan — Verifier Report (P2-017)

**Verdict: PASS** ✅ — All 6 checks pass. No hardcoded tokens, no bare excepts, all `type: ignore` justified, no parallel safe-mode state, GUILD_ID is clean constant.

---

## 1. Token / Secret / Env Patterns — `src/discord/bot.py`

| Line | Match | Risk |
|------|-------|------|
| 7    | Docstring: `Token is read from \`\`os.environ["DISCORD_BOT_TOKEN"]\`\` — never hardcoded.` | ✅ Declarative |
| 266  | `"""Read the bot token from environment and start...` | ✅ Docstring |
| 269  | `RuntimeError: If \`\`DISCORD_BOT_TOKEN\`\` is not set...` | ✅ Docstring |
| 271  | `token = os.environ.get("DISCORD_BOT_TOKEN")` | ✅ Clean env read |
| 272  | `if not token:` | ✅ Guard clause |
| 274  | `"DISCORD_BOT_TOKEN environment variable is required"` | ✅ Error msg |
| 280  | `await bot.start(token)` | ✅ Uses variable (not hardcoded) |
| 284  | `await bot.start(token)` | ✅ Uses variable (not hardcoded) |

**Result: PASS** — Token is read **exclusively** from `os.environ.get("DISCORD_BOT_TOKEN")`. No hardcoded tokens, secrets, passwords, SOPS keys, or decrypt calls found.

Searched patterns with zero matches: `secret`, `password`, `SOPS`, `sops`, `decrypt`.

---

## 2. Type Safety Bypasses — `src/discord/bot.py`

| Line | Match | Justification | Verdict |
|------|-------|---------------|---------|
| 31   | `_BotBase: type = commands.Bot  # type: ignore[assignment]` | Dynamic importlib import makes `commands.Bot` type ambiguous to static analysis. Type `type` is the correct abstract base. | ✅ **Justified** |

## Type Safety Bypasses — `tests/discord/test_bot.py`

| Line | Match | Justification | Verdict |
|------|-------|---------------|---------|
| 41   | `bot.start = AsyncMock()  # type: ignore[method-assign]` | Overriding a method with a mock subclass requires `# type: ignore` because the assignment signature differs from the original method. Standard pytest pattern. | ✅ **Justified** |
| 42   | `bot.tree.sync = AsyncMock(return_value=[])  # type: ignore[method-assign]` | Same justification as above. | ✅ **Justified** |

**Result: PASS** — 3 `type: ignore` occurrences total, all justified. No `# type: ignore` without specific error code. No `as any` (TypeScript-only construct), no `@ts-ignore` or `@ts-expect-error` found.

---

## 3. Bare / Catch-All Except — `src/discord/bot.py`

**No matches for `except:` or `except Exception:`.**

## Bare / Catch-All Except — `tests/discord/test_bot.py`

**No matches for `except:` or `except Exception:`.**

**Result: PASS** — Zero bare or catch-all except clauses in both target files.

---

## 4. Hardcoded IDs — `src/discord/bot.py`

| Line | ID Value | Type | Verdict |
|------|----------|------|---------|
| 37   | `GUILD_ID: int = 1_510_876_414_671_323_206` | Guild — named constant with docstring | ✅ **Acceptable** |

Additional searches:
- `grep` for `\d{15,}` (15+ digit Discord IDs): **No matches** other than GUILD_ID
- `grep` for `channel_id` / `user_id` / hardcoded channel/user IDs: **No matches**
- `tests/discord/test_bot.py`: **No large numeric literals found**

**Result: PASS** — The only hardcoded Discord ID is `GUILD_ID`, a well-documented named constant referencing `guild_setup.py`. No hardcoded channel IDs, user IDs, or phantom guild IDs.

---

## 5. `_safe_mode_active` Across `src/discord/*.py`

| File | Content | Verdict |
|------|---------|---------|
| `cmd_safeword.py:8` | Docstring only: `"No parallel \`\`_safe_mode_active\`\` global exists in this module."` | ✅ **Reference only — no variable** |

**Result: PASS** — `_safe_mode_active` appears **only** in a docstring as a declaration that no such variable exists. No actual assignment, declaration, or usage found in any `src/discord/*.py` file.

---

## 6. `_get_handler()` as Sole Safety State Truth — `src/discord/cmd_safeword.py`

| Element | Line(s) | Role |
|---------|---------|------|
| `_handler: HardStopHandler \| None = None` | ~395 | Module-level singleton variable |
| `_get_handler()` | ~400-407 | Lazily creates & returns singleton. Called by `bot.py:on_message` and `cmd_safeword.py:safeword_callback`. |
| `_new_handler()` | ~410-416 | Factory for fresh handler (test support) |
| `set_handler(handler)` | ~419-424 | Override singleton (test support, no security bypass) |
| `get_safety_state()` | ~765-770 | Public accessor: delegates through `_get_handler()` |

**No other source of safety state exists.** `bot.py` (line 263) and `safeword_callback` (line 562) both call `_get_handler()`. There is no parallel state, no second handler instance, no global flag.

**Result: PASS**

---

## Summary

| # | Check | Result |
|---|-------|--------|
| 1 | Token read only from `os.environ`, never hardcoded | ✅ PASS |
| 2 | `type: ignore` occurrences all justified | ✅ PASS |
| 3 | No bare/catch-all except in bot.py or test_bot.py | ✅ PASS |
| 4 | No hardcoded channel/user IDs; GUILD_ID is clean constant | ✅ PASS |
| 5 | No parallel `_safe_mode_active` state in any src/discord/*.py | ✅ PASS |
| 6 | `_get_handler()` is sole source of safety state truth | ✅ PASS |

**Overall Verdict: PASS** ✅