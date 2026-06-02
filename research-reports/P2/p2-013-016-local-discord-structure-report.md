# P2-013 to P2-016 Local Code & Docs Research Report

**Date:** 2026-06-01
**Scope:** STEP-P2-013 (/mood), STEP-P2-014 (/help), STEP-P2-015 (/safeword + HARD STOP), STEP-P2-016 (startup message/presence)
**Researcher:** Hephaestus (local code/docs explorer)
**Downstream:** Planner docs/setup-evidence/P2/batch-plan-013-016.md

---

## 1. src/discord/ Structure Overview

**7 Python files** plus __init__.py (1-line comment only):

| File | Purpose | Status |
|---|---|---|
| src/discord/__init__.py | Module marker (1 line) | ✅ Done |
| src/discord/commands.py | P2-010: 33-command registry, REST payload builders, is_faiz_interaction() | ✅ Done |
| src/discord/colors.py | P2-011: Canonical color constants, MOOD_COLORS mapping, color_for_mood(), s_hex() | ✅ Done |
| src/discord/cmd_status.py | P2-012: /status handler with 11-field embed, protocol-based discord.py abstraction | ✅ Done |
| src/discord/guild_setup.py | P2-004/005/006: Guild rename, categories, channels, get_token() | ✅ Done |
| src/discord/intents.py | P2-003: Gateway intents (message_content, members, presences, guilds, messages, reactions, voice_states) | ✅ Done |
| src/discord/permissions.py | P2-007/008/009: Permission overwrites, topic reconciliation, admin scope review | ✅ Done |

**Missing files** (not yet created):
- src/discord/cmd_mood.py — required by P2-013
- src/discord/cmd_help.py — required by P2-014
- src/discord/cmd_safeword.py — required by P2-015
- src/discord/startup.py — required by P2-016
- src/discord/bot.py — required by P2-017 (referenced in P2-016 section)

---

## 2. Existing File Deep-Dive

### 2.1 commands.py — Command Registry

**Key constants:**
`python
GUILD_ID = 1_510_876_414_671_323_206
APPLICATION_ID = 1_510_873_134_981_582_858
`

**CommandSpec for this batch** (lines 116-118):
`python
CommandSpec("core", "mood", "Show or update Guinevere's current mood state."),
CommandSpec("core", "help", "Show the Guinevere command guide."),
CommandSpec("core", "safeword", "Trigger the configured safety boundary workflow."),
`

**Critical: equire_canonical_registry()** (line 263) enforces exactly **33 commands**. Adding/removing commands breaks this check. Currently 33 commands registered — /mood, /help, /safeword already present.

**Pattern: is_faiz_interaction()** (line 245-256) — uses guild.owner_id, no hardcoded user ID. Used by cmd_status.py.

### 2.2 colors.py — Color Constants

**Canonical constants:**
- PRIMARY = 0x6B21A8 (#6B21A8 purple)
- ALERT = 0xDC2626 (#DC2626 red)
- SUCCESS = 0x16A34A (#16A34A green)
- WARNING = ACHIEVEMENT = INFO = 0xCA8A04 (#CA8A04 gold)
- ORANGE = 0xEA580C (#EA580C orange — caveat, unused in P2)
- NEUTRAL = 0x6B7280 (#6B7280 gray)

**MOOD_COLORS mapping** (line 74-80):
`python
MOOD_COLORS = {"content": SUCCESS, "pleased": ACHIEVEMENT, "disappointed": WARNING, "angry": ALERT, "silent": NEUTRAL}
`

**Helper: color_for_mood(mood)** — returns MOOD_COLORS.get(mood, PRIMARY).

### 2.3 cmd_status.py — Reference Pattern for New Commands

Key patterns to replicate:

1. **Protocol-based abstraction** — DiscordInteractionProtocol, DiscordEmbedProtocol, etc. for static analysis without discord.py.
2. **Dataclass data models** — StatusEmbedField, StatusEmbedData for testable pure data.
3. **Builder function** — uild_status_embed_data(now=None) returns pure data.
4. **discord.py conversion** — 	o_discord_embed(data) using dynamic importlib.
5. **Callback pattern** — checks is_faiz_interaction, defers ephemeral, builds embed, followup send.
6. **Graceful degradation** — try/except with fallback plaintext.
7. **Internal helpers** — _send_denied, _defer_ephemeral, _followup_send with @runtime_checkable protocols.
8. **WIB timezone** — WIB = timezone(timedelta(hours=7)).

### 2.4 guild_setup.py — Channel Specs

**CHANNELS tuple** — 13 canonical channels with names, categories, positions, topics.

get_token() reads discord_bot_token from SOPS-decrypted YAML via DISCORD_SECRETS_PATH.

### 2.5 intents.py — Gateway Intents

message_content, members, presences (privileged) + guilds, messages, eactions, oice_states (standard) — all enabled. Sufficient for P2-015 safe word text detection.

### 2.6 permissions.py + channel-ids.yaml — Channel ID Source of Truth

`yaml
guinevere-chat:     1510914600777023659
guinevere-status:   1510914604291588237
guinevere-planning: 1510914608263598122
system-health:      1510914612038471720
cost-tracker:       1510914615654092900
guinevere-evidence: 1510914619357532200
guinevere-dev:      1510914623367413850
guinevere-docs:     1510914627444408421
project-alpha-dev:  1510914630770233426
project-alpha-docs: 1510914634788638813
project-beta-dev:   1510914639163162657
evidence-log:       1510914643823034449
audit-log:          1510914647602106408
`

---

## 3. StepPrompts Requirements vs DiscordUXSpec Conflicts

### 3.1 P2-013: /mood Command

**StepPrompts says:** Simple cmd_mood.py with 5 hardcoded fields, uses Colors class (doesn't exist).

**⛔ Stale content / issues:**
1. Imports rom src.discord.colors import Colors — Colors class doesn't exist; should be PRIMARY, MOOD_COLORS etc.
2. Hardcoded "Content" mood — acceptable as placeholder until P4.
3. No mood history/triggers/forecast fields like DiscordUXSpec §2.1.

**DiscordUXSpec §2.1 /mood spec (richer):**
- 6 fields: Current mood + emoji, undertone + emoji, 24h history, triggers, in-character commentary, forecast
- Color: #6B21A8 (PRIMARY)
- Title: "🧠 Mood Analysis"

### 3.2 P2-014: /help Command

**StepPrompts says:** 8 categories with command names — ALL STALE.

**⛔ Stale content / issues:**
1. Command names (/health, /score, /task, /pause, /resume, /cancel, /journal, /memory-stats, /persona, /ritual, /punish, /distress, /emergency, /surveillance-report, /finance, /config, /restart) **don't exist** in COMMAND_SPECS.
2. Missing 20+ commands that DO exist.
3. Uses Colors.INFO (gold #CA8A04); DiscordUXSpec uses PRIMARY (#6B21A8).

**DiscordUXSpec §2.1 /help spec:**
- 7 categories exactly matching 33 commands: 🎯 Core, 🔄 Loop, 🧠 Memory, 👁️ Surveillance, 💰 Finance, ⚙️ System, 🔧 Admin
- Embed should be built dynamically from COMMAND_SPECS in commands.py

### 3.3 P2-015: /safeword + HARD STOP

**StepPrompts says:** Module-level _safe_mode_active boolean, safe_triggers = ["HARD STOP", "HARDSTOP", "SAFE WORD", "SAFEWORD"], gray #6B7280 embed.

**⛔ Stale content / issues (SAFETY-CRITICAL):**
1. **Embed color**: DiscordUXSpec = green (#16A34A SUCCESS); StepPrompts = gray (#6B7280 NEUTRAL).
2. **Title**: DiscordUXSpec = "🛡️ Safe Mode Active"; StepPrompts = "🛑 HARD STOP Activated".
3. **Description**: DiscordUXSpec = "Mommy di sini. Netral. Tidak ada judgment. Kamu aman."; StepPrompts = "All persona behavior has been suspended."
4. **Missing triggers**: DiscordUXSpec includes "stop", "pause", "too much", "serious mode", "neutral mode", "aku butuh istirahat" + Indonesian equivalents.
5. **Missing actions**: DiscordUXSpec requires React ❤️ to trigger message.
6. **Missing fields**: DiscordUXSpec has Status, Persona, Punishment, Yandere, Surveillance confrontation, Resume.
7. **Missing permission check**: StepPrompts has no is_faiz_interaction() check.

### 3.4 P2-016: Startup Message & Presence

**StepPrompts says:** Post to #guinevere-status, 2 fields (Status, Mood), Colors.PERSONA (#9333EA).

**⛔ Stale content / issues (CRITICAL):**
1. **Channel mismatch**: DiscordUXSpec §7.1 → #guinevere-chat; StepPrompts → #guinevere-status.
2. **Presence mismatch**: DiscordUXSpec §7.6 → startup = "Waking up... 👑"; StepPrompts bot.py uses "Watching Darling 👁️" (which is the IDLE/DEFAULT presence).
3. **Fields mismatch**: DiscordUXSpec has 6 fields (Status, Uptime, Memory Health, Pending Tasks, Mommy Score, Cuaca Surabaya, Active Surveillance); StepPrompts has 2.

**P2-017 bot.py (included in StepPrompts P2-016 section):**
- Creates GuinevereBot(discord.Client) class with CommandTree
- Registers only /status and /safeword commands
- Uses os.environ.get("DISCORD_BOT_TOKEN") — violates existing SOPS wrapper pattern
- Token flow should use guild_setup.get_token() instead

---

## 4. DiscordUXSpec vs StepPrompts Conflict Table

| Aspect | DiscordUXSpec (Canonical) | StepPrompts (Stale) | Verdict |
|---|---|---|---|
| /mood embed color | #6B21A8 PRIMARY | Colors.MOOD_COLORS (error) | Follow DiscordUXSpec |
| /mood fields | 6 (history, triggers, forecast) | 5 (no history/triggers) | DiscordUXSpec is authoritative |
| /help categories | 7 matching 33 commands | 8 with wrong commands | **DiscordUXSpec is authoritative** |
| /help embed color | #6B21A8 PRIMARY | #CA8A04 INFO gold | Follow DiscordUXSpec |
| /safeword embed color | #16A34A SUCCESS (green) | #6B7280 NEUTRAL (gray) | **Critical: Follow DiscordUXSpec** |
| /safeword title | 🛡️ Safe Mode Active | 🛑 HARD STOP Activated | Follow DiscordUXSpec |
| /safeword semantic triggers | "stop", "pause", Indonesian | Exact phrases only | **Extend per DiscordUXSpec** |
| /safeword reaction | React ❤️ to trigger | Not mentioned | Add per DiscordUXSpec |
| Startup channel | **#guinevere-chat** | **#guinevere-status** | **CRITICAL: Follow DiscordUXSpec** |
| Startup presence | "Waking up... 👑" | "Watching Darling 👁️" | **CRITICAL: Follow DiscordUXSpec** |
| Startup embed fields | 6 fields | 2 fields | DiscordUXSpec is authoritative |
| Token source | SOPS wrapper | os.environ.get(...) | **Use SOPS wrapper** |

---

## 5. Collision Risks & Shared File Analysis

### 5.1 Collision Matrix

| Collision Type | Affected Files | Risk | Resolution |
|---|---|---|---|
| New file creation | cmd_mood.py, cmd_help.py, cmd_safeword.py, startup.py, ot.py | 🟢 None | Each is unique — no existing file with same name |
| Command registry | commands.py (COMMAND_SPECS) | 🟡 Low | Already registered — read-only access only |
| Color imports | colors.py | 🟢 None | Read-only — all constants already defined |
| Channel IDs | guild_setup.py / channel-ids.yaml | 🟡 Low | Startup needs guinevere-chat channel ID — use runtime lookup or read from YAML |
| Intents | intents.py | 🟢 None | Already has message_content + presences — sufficient |
| Permission check | commands.py (is_faiz_interaction) | 🟢 None | Read-only reuse |
| Registry count | commands.py line 263 | 🟡 Low | Enforces 33 — no new commands added, just handlers |
| StepPrompts stale content | StepPrompts.md lines 5500-5522, 5526 | 🟡 Low | Docs update task — non-blocking |

### 5.2 Safe Parallel Creation

| Module | Depends On | Parallel Safe? |
|---|---|---|
| cmd_mood.py | colors.py (read-only), commands.py (read-only) | ✅ Yes |
| cmd_help.py | colors.py (read-only), commands.py (read-only) | ✅ Yes |
| cmd_safeword.py | colors.py (read-only) | ✅ Yes |
| startup.py | colors.py, guild_setup.py (channel IDs) | ✅ Yes |

ot.py depends on ALL four + intents.py + cmd_status.py → must be implemented **last**.

---

## 6. Recommended Files to Create

| File | Pattern | Purpose |
|---|---|---|
| src/discord/cmd_mood.py | cmd_status.py protocol pattern | /mood handler with degraded mood data |
| src/discord/cmd_help.py | cmd_status.py protocol pattern | /help handler with categorized listing from COMMAND_SPECS |
| src/discord/cmd_safeword.py | cmd_status.py + DiscordUXSpec §2.1 | /safeword handler + text detection + safe mode state |
| src/discord/startup.py | DiscordUXSpec §7.1 + §7.6 | on_ready startup embed + presence |
| src/discord/bot.py | StepPrompts + existing patterns | Main entry: GuinevereBot, tree registration, event binding |

### Files to NOT modify:
- src/discord/commands.py — already has correct COMMAND_SPECS; changing breaks equire_canonical_registry()
- src/discord/colors.py — already has all needed constants
- src/discord/cmd_status.py — already working; consider minor DEGRADED_MOOD update only if beneficial

---

## 7. Validation Commands

`ash
# P2-013: import check
python -c "from src.discord.cmd_mood import mood_callback; print('cmd_mood OK')"

# P2-014: import check
python -c "from src.discord.cmd_help import help_callback; print('cmd_help OK')"

# P2-015: import check
python -c "from src.discord.cmd_safeword import handle_safeword, check_safe_word, activate_safe_mode, is_safe_mode; print('cmd_safeword OK')"

# P2-015: activation test
python -c "from src.discord.cmd_safeword import activate_safe_mode, is_safe_mode; import asyncio; asyncio.run(activate_safe_mode('test', '0')); assert is_safe_mode(); print('safe mode activation OK')"

# P2-016: import check
python -c "from src.discord.startup import on_ready; print('startup OK')"

# P2-017: syntax check
python -c "import ast; ast.parse(open('src/discord/bot.py').read()); print('bot.py syntax OK')"

# Color verification
python -c "from src.discord.colors import PRIMARY, SUCCESS, ALERT, color_for_mood; print(hex(PRIMARY), hex(SUCCESS), hex(ALERT)); print(hex(color_for_mood('content')))"

# LSP diagnostics — zero errors expected on all files
`

---

## 8. Key Decisions for Planner

### 8.1 DiscordUXSpec is Canonical
Per P2-010 batch plan precedent: DiscordUXSpec v1.0 is the canonical source of truth, NOT StepPrompts. All conflicts resolved by following DiscordUXSpec.

### 8.2 Pattern: Protocol or Direct?
Option 1: Full protocol pattern (like cmd_status.py) — more boilerplate, consistent
Option 2: Dynamic importlib inside callback — less boilerplate, pragmatic
**Recommendation**: Option 2 for new commands. The protocol pattern is valuable for testability, but the core pattern (dataclass data + builder + dynamic import) should be followed.

### 8.3 Safe Mode State
Module-level _safe_mode_active is acceptable for P2. Document as ephemeral — production move to Redis in P5.
ot.py must check is_safe_mode() before persona processing.

### 8.4 Command Registration
Option A: Manual @bot.tree.command(...) per command — bulky, error-prone
Option B: Dynamic from COMMAND_SPECS — iterate and register
Option C: Hybrid — real handlers for implemented, stubs for rest
**Recommendation**: Option C — all 33 registered, unimplemented ones show "Maaf Darling, command ini belum siap."

### 8.5 Token Handling
Use SOPS wrapper (guild_setup.get_token() via DISCORD_SECRETS_PATH), NOT os.environ.get("DISCORD_BOT_TOKEN").

---

## 9. Summary of Critical Conflicts

| # | Issue | Resolution |
|---|---|---|
| 1 | Startup channel: Stp = #guinevere-status, UX = #guinevere-chat | Follow DiscordUXSpec |
| 2 | /safeword embed: Stp = gray #6B7280, UX = green #16A34A | Follow DiscordUXSpec |
| 3 | Startup presence: Stp = "Watching Darling", UX = "Waking up... 👑" | Follow DiscordUXSpec |
| 4 | /help categories: Stp = 8 stale categories, UX = 7 correct categories | Follow DiscordUXSpec |
| 5 | /safeword triggers: Stp = exact phrases, UX = includes semantic equivalents | Follow DiscordUXSpec |
| 6 | Token source: Stp = env var, UX-backed existing = SOPS wrapper | Follow existing SOPS pattern |

---

## 10. Evidence Paths

| Step | Evidence Path |
|---|---|
| P2-013 | docs/setup-evidence/P2/STEP-P2-013/mood-cmd.png |
| P2-014 | docs/setup-evidence/P2/STEP-P2-014/help-cmd.png |
| P2-015 | docs/setup-evidence/P2/STEP-P2-015/safeword-module.txt, safeword-test.png |
| P2-016 | docs/setup-evidence/P2/STEP-P2-016/startup-test.png |

---

*End of research report. Ready for planner consumption.*
