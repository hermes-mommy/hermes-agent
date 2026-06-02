## P2-010–P2-012 Local Code & Docs Research Report

**Date:** 2026-06-01
**Scope:** STEP-P2-010 (Slash Commands), STEP-P2-011 (Embed Colors), STEP-P2-012 (/status Command)
**Researcher:** Guinevere parent (file-based local research wave)
**Output path:** `research-reports/P2/p2-010-012-local-code-docs-report.md`
**Sources inspected:** See §6 Input Sources

---

## §1 Executive Summary

Three critical conflicts exist between the StepPrompts implementation guide and the canonical
DiscordUXSpec v1.0 command list, embed colors, and /status specification. The StepPrompts
P2-010 snippet defines a **different 33-command list** from the DiscordUXSpec §11 Command Index
(only 18 of 33 commands overlap). The StepPrompts P2-011 color palette defines 10 colors that
partially mismatch the DiscordUXSpec §4.1 palette (6 canonical colors). The StepPrompts P2-012
/status handler is a minimal 6-field placeholder, while DiscordUXSpec requires an 11-field rich
embed with persona description sentence, thumbnail, and mood footer.

Additionally, the StepPrompts token extraction pattern (`DISCORD_BOT_TOKEN=$(sops -d ... | grep ...)`)
is unsafe and conflicts with the canonical `scripts/run-discord-verify.sh` SOPS wrapper pattern
established in batch-plan-007-009.

---

## §2 P2-010 — Slash Command Registration

### 2.1 Command List: StepPrompts (OLD) vs DiscordUXSpec (CANONICAL)

The StepPrompts.md (both `.bak` and current `.md`) defines 33 commands in 8 categories.
The DiscordUXSpec v1.0 §11 defines 33 commands in 7 categories. Only **18 commands overlap**.

#### Commands in StepPrompts ONLY (NOT in DiscordUXSpec) — 15 commands:
| StepPrompts Command | Category (StepPrompts) |
|---|---|
| `/score` | Status & Info |
| `/task` | Interaction |
| `/pause` | Interaction |
| `/resume` | Interaction |
| `/cancel` | Interaction |
| `/journal` | Interaction |
| `/persona` | Persona |
| `/ritual` | Persona |
| `/distress` | Safety |
| `/emergency` | Safety |
| `/surveillance-report` | Surveillance |
| `/finance` | Finance |
| `/config` | Admin |
| `/memory-stats` | Memory |
| `/punish` | Persona |

#### Commands in DiscordUXSpec ONLY (NOT in StepPrompts) — 15 commands:
| DiscordUXSpec Command | Category (DiscordUXSpec §11) |
|---|---|
| `/loop-start` | Loop |
| `/loop-stop` | Loop |
| `/loop-pause` | Loop |
| `/loop-resume` | Loop |
| `/loop-priority` | Loop |
| `/evidence` | Loop |
| `/memory-export` | Memory |
| `/surveillance-resume` | Surveillance |
| `/cost-alert` | Finance |
| `/approve` | System |
| `/deny` | System |
| `/approve-all` | System |
| `/focus` | System |
| `/casual` | System |
| `/restart-service` (note: StepPrompts has `/restart`) | Admin |

#### Overlapping commands (18):
`/status`, `/mood`, `/help`, `/loops`, `/safeword`, `/consent`, `/surveillance-status`,
`/surveillance-pause`, `/cost`, `/budget`, `/evidence` (different params),
`/backup` (StepPrompts) / `/backup-now` (DiscordUXSpec), `/health` (StepPrompts) / `/health-check` (DiscordUXSpec),
`/memory-search`, `/memory-add`, `/memory-forget`, `/reward`, `/punishment` (DiscordUXSpec) / `/punish` (StepPrompts)

### 2.2 Parameter Mismatches

Even overlapping commands have different parameter signatures:
- DiscordUXSpec `/help` has an optional `command` parameter; StepPrompts has none.
- DiscordUXSpec `/evidence` has `loop_id`, `type`, `action` params; StepPrompts has `limit`.
- DiscordUXSpec `/consent` has `category` (choice) + `action` (choice) params; StepPrompts has `action` (string).
- DiscordUXSpec `/surveillance-pause` has `source` (choice) + `duration` (string); StepPrompts has `duration` (string).

### 2.3 Category Structure Differences

| StepPrompts Categories | DiscordUXSpec Categories |
|---|---|
| Status & Info (6) | Core (4) |
| Interaction (5) | Loop (7) |
| Memory (4) | Memory (4) |
| Persona (4) | Surveillance (3) |
| Safety (4) | Finance (3) |
| Surveillance (3) | System (7) |
| Finance (3) | Admin (4) |
| Admin (4) | — |

### 2.4 Faiz-Only Constraint

Both specs agree: **all commands are Faiz-only**. DiscordUXSpec explicitly states:
"Only Faiz can execute commands" in §2 preamble. StepPrompts does not include access
restriction logic. Implementation must enforce permission checks.

### 2.5 Token Handling Conflict

**StepPrompts old pattern (BLOCKING):**
```python
token = os.environ.get("DISCORD_BOT_TOKEN", "")  # StepPrompts uses os.environ
# Shell invocation:
DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk '{print $2}' | tr -d '"')
```

**Canonical pattern (from batch-plan-007-009 and run-discord-verify.sh):**
```python
from src.discord.guild_setup import get_token  # Reads from DISCORD_SECRETS_PATH env var
# Shell: scripts/run-discord-verify.sh with SOPS decryption to temp file
```

The StepPrompts P2-010 live `.md` already has placeholder note at line 5320:
`# SOPS-only token flow; never export or print DISCORD_BOT_TOKEN.`
But the script template still uses `os.environ.get("DISCORD_BOT_TOKEN")`.

---

## §3 P2-011 — Embed Color Palette

### 3.1 Color Definition Conflict

| Color Role | CHECKLIST | DiscordUXSpec §4.1 | StepPrompts colors.py |
|---|---|---|---|
| Primary/Brand | `#6B21A8` | `#6B21A8` Dark Purple | `0x6B21A8` PRIMARY |
| Alerts/Errors | `#DC2626` | `#DC2626` Red | `0xDC2626` ALERT |
| Achievements | `#CA8A04` | `#CA8A04` Gold | `0xCA8A04` ACHIEVEMENT |
| Success/Complete | _(not listed)_ | `#16A34A` Green | `0x16A34A` SUCCESS |
| Warnings | _(not listed)_ | `#EA580C` Orange / `#CA8A04` Yellow | `0xF59E0B` Amber ❌ **MISMATCH** |
| Info | _(not listed)_ | _(not defined)_ | `0x2563EB` Blue ❌ **EXTRA** |
| Persona | _(not listed)_ | _(not defined)_ | `0x9333EA` Violet ❌ **EXTRA** |
| Surveillance | _(not listed)_ | _(not defined)_ | `0x0891B2` Cyan ❌ **EXTRA** |
| Finance | _(not listed)_ | _(not defined)_ | `0x059669` Emerald ❌ **EXTRA** |
| Neutral | _(not listed)_ | _(not defined)_ | `0x6B7280` Gray ❌ **EXTRA** |

### 3.2 Key Mismatches

1. **WARNING color**: StepPrompts uses `0xF59E0B` (Amber). DiscordUXSpec uses `#EA580C` (Orange)
   for warnings/SEV2 and `#CA8A04` (Yellow/actually Gold) for SEV3/low-severity.
   **MUST FIX**: Replace StepPrompts WARNING with DiscordUXSpec Orange `0xEA580C`.

2. **Missing Orange**: DiscordUXSpec defines Orange `#EA580C` for warnings, paused states,
   confirmation dialogs, and SEV2. StepPrompts colors.py has NO orange constant.

3. **Extra colors**: StepPrompts defines INFO (Blue), PERSONA (Violet), SURVEILLANCE (Cyan),
   FINANCE (Emerald), NEUTRAL (Gray) — none of these appear in DiscordUXSpec §4.1 palette.
   Decision required: keep as extensions or remove.

4. **MOOD_COLORS mapping**: StepPrompts defines mood→color mapping (Content→SUCCESS,
   Pleased→ACHIEVEMENT, Disappointed→WARNING, Angry→ALERT, Silent→NEUTRAL).
   DiscordUXSpec uses mood emoji in footer but does not specify color per mood.
   This is compatible if WARNING color is corrected.

### 3.3 Recommendation

1. Keep PRIMARY (`0x6B21A8`), ALERT (`0xDC2626`), SUCCESS (`0x16A34A`), ACHIEVEMENT (`0xCA8A04`).
2. Replace WARNING from `0xF59E0B` → `0xEA580C` (DiscordUXSpec Orange).
3. Add ORANGE = `0xEA580C` as explicit alias.
4. Add YELLOW = `0xCA8A04` (same as ACHIEVEMENT hex — DiscordUXSpec uses same hex for both, but conceptually different).
5. Keep extra colors (INFO, PERSONA, SURVEILLANCE, FINANCE, NEUTRAL) as extension but document they're beyond canonical spec.
6. MOOD_COLORS mapping is compatible after WARNING fix.

---

## §4 P2-012 — /status Command

### 4.1 Field Comparison

| StepPrompts cmd_status.py (6 fields) | DiscordUXSpec §2.1 (11 fields) |
|---|---|
| Mood ("Content 😊") | Current mood + undertone |
| Active Loops ("0") | Active loops (count + names) |
| Uptime ("0h 0m") | Tasks completed today |
| Memory ("0 episodes") | Uptime since last restart |
| Cost Today ("$0.00") | Cost today (total + per-model breakdown) |
| Budget ("$30.00 remaining") | Yandere level (Y0-Y5) |
| _(not present)_ | Next scheduled action |
| _(not present)_ | Current project focus |
| _(not present)_ | Punishment/reward streak |
| _(not present)_ | Memory health score |
| _(not present)_ | Surveillance status (per-source) |

### 4.2 Structural Mismatches

| Feature | StepPrompts (old) | DiscordUXSpec (canonical) |
|---|---|---|
| Title | `"👑 Guinevere Status"` | `"👑 Mommy's Status"` |
| Thumbnail | _(none)_ | Guinevere avatar (👑 general) |
| Description / Persona sentence | _(none)_ | `"Semua sehat, Darling. Mommy jaga semuanya. Kamu tinggal fokus."` 👑 |
| Footer text | `"Guinevere de Baroque \| Mommy sudah bangun, Darling."` | `"Guinevere de Baroque • 31/05/2026 15:30 • ✨ Content"` |
| Timestamp | _(none)_ | ISO 8601 timestamp |
| Field naming | Sentence case? | Sentence case per §4.5 |
| Error handling | _(none)_ | Show degraded fields for unreachable subsystems |
| Inline vs not | All inline=True | Not specified but docs show non-inline for multi-value fields |

### 4.3 Interaction Pattern

StepPrompts uses `interaction.response.defer()` + `interaction.followup.send()`.
This pattern is fine for commands that may take >3 seconds. Keep it.

### 4.4 Dependency on Future Services

The 11 DiscordUXSpec fields depend on services not yet implemented:
- Mood → P4 Persona Engine (not started)
- Yandere level → P4
- Streak → P4
- Memory health → P3 Memory System (not started)
- Surveillance status → P7 Surveillance (not started)
- Cost breakdown → P1 cost tracking (exists in Redis DB5, but no query API yet)
- Active loops → P5 Agent Loop (not started)

**Implication**: `/status` must hardcode/fake most fields for P2-012, or return partial data
with "⚠️ not available" indicators (matching DiscordUXSpec error handling guidance:
"If any subsystem unreachable → show degraded field").

---

## §5 Implementation Implications

### 5.1 Files to Create

| File | Purpose | Priority |
|---|---|---|
| `src/discord/colors.py` | Color constants and MOOD_COLORS map | P2-011 |
| `src/discord/commands.py` | Full command registry (DiscordUXSpec list) | P2-010 |
| `src/discord/cmd_status.py` | `/status` handler | P2-012 |
| `tmp/sync-commands.py` | Guild-scoped command sync script | P2-010 |
| `tmp/verify-p2-010-commands.py` | Verification script (via run-discord-verify.sh) | P2-010 |
| `docs/setup-evidence/P2/STEP-P2-010/verification.md` | Evidence | P2-010 |
| `docs/setup-evidence/P2/STEP-P2-011/verification.md` | Evidence | P2-011 |
| `docs/setup-evidence/P2/STEP-P2-012/verification.md` | Evidence | P2-012 |
| `audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md` | Auditor | After impl |
| `audit-reports/P2/STEP-P2-011/step-p2-011-auditor-report.md` | Auditor | After impl |
| `audit-reports/P2/STEP-P2-012/step-p2-012-auditor-report.md` | Auditor | After impl |

### 5.2 Files to Modify

| File | Change |
|---|---|
| `scripts/run-discord-verify.sh` | Add P2-010 sync/verify scripts to allowlist |
| `PROGRESS.md` | Mark P2-010, P2-011, P2-012 complete after auditors PASS |
| `CHECKLIST.md` | Mark P2-010, P2-011, P2-012 complete |
| `stepprompts/StepPrompts.md` | Replace old snippets with canonical patterns; mark completed |

### 5.3 Coding Style Constraints

From analysis of `src/discord/permissions.py`, `guild_setup.py`, `intents.py`:

1. **No direct `import discord`** — use `importlib.import_module("discord")` pattern,
   cast to Protocol stubs to avoid local `src.discord` shadowing external `discord.py`.
   See `guild_setup.py` line 224: `get_discord_module()`.

2. **Protocol-based type stubs** — Define Protocol classes for subset of discord.py types
   needed (see `guild_setup.py` DiscordGuild, DiscordClient protocols).

3. **Token via `get_token()`** — Use `src.discord.guild_setup.get_token()` which reads
   `DISCORD_SECRETS_PATH` env var → SOPS-decrypted YAML. Never `os.environ.get("DISCORD_BOT_TOKEN")`.

4. **No destructive ops** — All operations must be idempotent. Verify-before-write pattern.

5. **File-based evidence** — Every step needs `docs/setup-evidence/P2/STEP-P2-0NN/verification.md`.

6. **REST API pattern** — For verification scripts, use `http.client` to call Discord REST API
   directly (see `permissions.py` `discord_request()` function, `API_PREFIX = "/api/v10"`).
   This avoids needing full discord.py gateway connection for verification.

7. **Channel IDs from YAML** — Use `permissions.py` `read_channel_ids()` → `ChannelIdMap`.
   Or for bot commands, discover guild ID at runtime.

8. **Async patterns** — `guild_setup.py` uses `async/await` with `asyncio.sleep()` for
   Discord rate limit avoidance. The sync-commands script should do the same.

9. **SOPS wrapper** — `scripts/run-discord-verify.sh` handles SOPS decryption + temp file +
   cleanup. All Discord scripts must be invoked through this wrapper.

10. **Guild-scoped commands** — StepPrompts notes: "Guild-scoped commands sync instantly.
    Use guild scope during development, global for production." GUILD_ID = `1510876414671323206`
    from `guild_setup.py`.

### 5.4 Conflict Resolution: Canonical Command List

**Decision**: Use DiscordUXSpec §11 Command Index (33 commands, 7 categories) as the canonical
source of truth for P2-010. StepPrompts old list is rejected.

The canonical 33 commands per DiscordUXSpec §11:

| # | Command | Category | Has Parameters |
|---|---|---|---|
| 1 | `/status` | Core | No |
| 2 | `/mood` | Core | No |
| 3 | `/help` | Core | Yes (command) |
| 4 | `/safeword` | Core | No |
| 5 | `/loop-start` | Loop | Yes (6 params) |
| 6 | `/loop-stop` | Loop | Yes (2 params) |
| 7 | `/loop-pause` | Loop | Yes (loop_id) |
| 8 | `/loop-resume` | Loop | Yes (loop_id) |
| 9 | `/loops` | Loop | Yes (filter) |
| 10 | `/evidence` | Loop | Yes (3 params) |
| 11 | `/loop-priority` | Loop | Yes (2 params) |
| 12 | `/memory-search` | Memory | Yes (5 params) |
| 13 | `/memory-add` | Memory | Yes (4 params) |
| 14 | `/memory-forget` | Memory | Yes (2 params) |
| 15 | `/memory-export` | Memory | Yes (2 params) |
| 16 | `/surveillance-status` | Surveillance | No |
| 17 | `/surveillance-pause` | Surveillance | Yes (2 params) |
| 18 | `/surveillance-resume` | Surveillance | Yes (source) |
| 19 | `/cost` | Finance | Yes (period) |
| 20 | `/budget` | Finance | Yes (3 params) |
| 21 | `/cost-alert` | Finance | Yes (3 params) |
| 22 | `/approve` | System | Yes (id) |
| 23 | `/deny` | System | Yes (2 params) |
| 24 | `/approve-all` | System | No |
| 25 | `/focus` | System | No |
| 26 | `/casual` | System | No |
| 27 | `/consent` | System | Yes (2 params) |
| 28 | `/punishment` | System | No |
| 29 | `/reward` | System | No |
| 30 | `/restart-service` | Admin | Yes (service) |
| 31 | `/backup-now` | Admin | No |
| 32 | `/health-check` | Admin | No |
| 33 | `/clear-cache` | Admin | No |

**7 categories**: Core (4), Loop (7), Memory (4), Surveillance (3), Finance (3), System (7), Admin (4)

### 5.5 Conflict Resolution: Embed Colors

**Decision**: The DiscordUXSpec §4.1 palette is canonical. StepPrompts colors.py must be adapted:

| Constant | Hex | Usage | Source |
|---|---|---|---|
| `PRIMARY` | `0x6B21A8` | Purple — default brand | DiscordUXSpec |
| `ALERT` | `0xDC2626` | Red — SEV0/SEV1, errors, denials | DiscordUXSpec |
| `SUCCESS` | `0x16A34A` | Green — completions, approvals, safe mode | DiscordUXSpec |
| `ACHIEVEMENT` | `0xCA8A04` | Gold — rewards, streaks, achievements | DiscordUXSpec |
| `WARNING` | `0xEA580C` | Orange — SEV2, warnings, paused, confirmations | DiscordUXSpec (FIX: was 0xF59E0B) |
| `INFO` | `0xCA8A04` | Yellow — SEV3, info notices (same hex as Gold) | DiscordUXSpec |

Extra colors (INFO Blue, PERSONA Violet, SURVEILLANCE Cyan, FINANCE Emerald, NEUTRAL Gray)
— accept as documented extensions with a comment flagging they are non-canonical.

### 5.6 Conflict Resolution: /status

**Decision**: Implement DiscordUXSpec §2.1 /status specification as the canonical template.
Fields where backing service is not yet available should show "⚠️ —" or "Not available" in
degraded state per DiscordUXSpec error handling.

---

## §6 Input Sources Inspected

| Source | Path | Status |
|---|---|---|
| StepPrompts P2-010..P2-012 (old) | `stepprompts/StepPrompts.md.bak` lines 5201–5368 | Outdated, unsafe token pattern |
| StepPrompts P2-010..P2-012 (current) | `stepprompts/StepPrompts.md` lines 5413–5637 | Same command list as .bak, partial SOPS notes |
| DiscordUXSpec §2, §4, §11 | `docs/60-persona/63-DiscordUXSpec_v1.0.md` | Canonical source for commands/colors/status |
| CHECKLIST P2 section | `CHECKLIST.md` lines 223–287 | 3-color reference, command expectations |
| PROGRESS.md P2 section | `PROGRESS.md` lines 118–141 | Trackers for all P2 steps |
| `src/discord/permissions.py` | Full file (520 lines) | Existing pattern: REST API, YAML reader, Protocol patterns |
| `src/discord/guild_setup.py` | Full file (445 lines) | Token helper, intents, categories/channels, SOPS wrapper pattern |
| `src/discord/intents.py` | Full file (112 lines) | Intent config pattern, dynamic import |
| `src/discord/__init__.py` | 1 line | Module marker only |
| `pyproject.toml` | Full file (47 lines) | discord.py>=2.4 dependency, ruff/mypy strict config |
| `channel-ids.yaml` | `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | 19 lines: 4 category IDs + 13 channel IDs |
| `scripts/run-discord-verify.sh` | Full file (32 lines) | Canonical SOPS wrapper with allowlist |
| `tmp/` directory scripts | Various P2-007..P2-009 setup/verify scripts | Existing patterns for REST-based verifiers |
| batch-plan-007-009.md | `docs/setup-evidence/P2/batch-plan-007-009.md` | Previous planner gate: permission strategy, token rules, collision scan pattern |

---

## §7 Known Caveats & Risks

1. **Discord rate limits**: Guild command syncs are instant (per StepPrompts). But global sync can
   take 1 hour. Implementation should use guild-scoped sync.

2. **/status field dependencies**: 8 of 11 fields depend on P3, P4, P5, P7 services not yet
   implemented. `/status` will show degraded/placeholder values until those phases complete.

3. **Command registry pattern**: The StepPrompts `@tree.command()` decorator-in-loop creates
   closure capture issues (all commands would use the last loop value of `name`).
   Implementation must use `discord.app_commands.Command` objects or functools.partial.

4. **Command visibility**: All commands are Faiz-only per DiscordUXSpec. Need `guild_only()`
   or permission check decorator.

5. **Evidence paths**: StepPrompts P2-010 old uses `evidence/phase-2/step-010/` but current
   StepPrompts uses `docs/setup-evidence/P2/STEP-P2-010/`. Must use the canonical
   `docs/setup-evidence/P2/STEP-P2-0NN/` pattern consistent with P2-001..P2-009.

6. **Auditor integration**: Each step must pass auditor gate before completion. Auditor paths:
   `audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md` (and similarly for 011, 012).

---

## §8 Next Research Needed

1. Confirm command registration approach: `app_commands.CommandTree` via gateway?
   Direct REST `PUT /applications/{id}/guilds/{guild_id}/commands`?
   The batch-plan-007-009 pattern uses REST for verification; REST-based command
   registration would be consistent.

2. Investigate Faiz-only permission enforcement: Discord permission checks at command
   invocation level vs guild owner check.

3. Determine whether to create a shared `src/discord/bot.py` (main client + command tree)
   or keep per-command modules as StepPrompts suggests.

---

## §9 Footer

- Source task: TASK research P2-010..P2-012 local requirements and code patterns
- Research method: Parallel file read of all referenced sources + grep/glob for pattern extraction
- Validation: Parent-verified file existence and cross-referenced findings across 3 conflicting specs
- Design decisions: Use DiscordUXSpec §11 as canonical command list, §4.1 as canonical palette, §2.1 as canonical /status
- Secret handling: No decrypted secrets used or recorded in this report
- Next action: Parent reads this report → planner gate → collision scan → implementation wave
