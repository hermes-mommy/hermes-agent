# Internal Spec Audit — P2-007, P2-008, P2-009

| Field | Value |
|---|---|
| **Report version** | 1.0 |
| **Date** | 2026-06-01 |
| **Author** | Guinevere (parent, spec auditor) |
| **Scope** | P2-007 (permissions), P2-008 (topics), P2-009 (bot verification) |
| **Output path** | `research-reports/P2/internal-p2-007-009-spec-audit.md` |
| **Sources read** | 15 (StepPrompts, CHECKLIST, DiscordUXSpec §1.4, channel-ids.yaml, batch-plan-004-006, batch-plan-001-003, guild_setup.py, intents.py, 3 auditor reports (P2-001/003/006), internal-discord-structure-spec, discord-permissions-model, PROGRESS.md, research-reports/stepprompts-audit) |

---

## Table of Contents

1. [P2-007 Requirements Matrix](#1-p2-007-requirements-matrix)
2. [P2-008 Requirements Matrix](#2-p2-008-requirements-matrix)
3. [P2-009 Requirements Matrix](#3-p2-009-requirements-matrix)
4. [Exact Channel List + IDs + Source Lines](#4-exact-channel-list--ids--source-lines)
5. [Required Permission Matrix (per DiscordUXSpec)](#5-required-permission-matrix-per-discorduxspec)
6. [Administrator Caveat — Full Trace](#6-administrator-caveat--full-trace)
7. [Unsafe StepPrompts Token Patterns to Replace](#7-unsafe-stepprompts-token-patterns-to-replace)
8. [Prior P2-003/P2-006 Caveats for P2-007/008/009](#8-prior-p2-003p2-006-caveats-for-p2-007008009)
9. [Current Code Patterns (guild_setup.py)](#9-current-code-patterns-guild_setuppy)
10. [Contradictions and Conflicts](#10-contradictions-and-conflicts)
11. [Implementation Recommendations](#11-implementation-recommendations)
12. [Evidence and Auditor Paths](#12-evidence-and-auditor-paths)
13. [Footer](#13-footer)

---

## 1. P2-007 Requirements Matrix

### From StepPrompts (lines 5358–5409)

| Field | Value |
|---|---|
| **Type** | Security |
| **Status** | ⬜ Not Started |
| **Risk** | Medium |
| **Goal** | Set per-channel permissions: Faiz full access, bot write, evidence write-only |
| **Dependencies** | P2-006 |
| **ADR** | ADR-022 |
| **AC** | AC-SEC-001 |
| **Time** | 1h |
| **Evidence path** | `docs/setup-evidence/P2/STEP-P2-007/permissions-test.txt` |

### From CHECKLIST.md (line 244)

> `P2-007: Permissions: Faiz=read-all, bot=write-all, evidence-role=write-only`

### From PROGRESS.md (line 127)

> `[ ] P2-007 Channel permissions (Faiz read, bot write, evidence write-only)`

### From Implementation Synthesis (audit-reports/2026-05-31, line 197)

> `P2-007: Channel permissions (Samm read all, bot write all, evidence write-only)`

### From discord-permissions-model.md §9

> **Risk**: If removing ADMINISTRATOR, bot needs explicit MANAGE_CHANNELS + MANAGE_ROLES
> **Risk**: Invite link should request manage_channels + manage_roles + view_channel + send_messages
> **Scope creep warning**: Do not conflate P2-007 hardening with P2-005/P2-006 creation

### From batch-plan-004-006.md §16 (lines 993–997)

> P2-007 should read channel-ids.yaml instead of making fresh API calls

### Current StepPrompts code (lines 5373–5403) — PROBLEMATIC

The StepPrompts code:
- Only sets bot permissions (`read_messages`, `send_messages`, `embed_links`, `attach_files`, `read_message_history`)
- Does NOT implement evidence write-only pattern (deny `send_messages` for bot, deny `read_messages` for @everyone)
- Does NOT implement Faiz read-only for evidence/audit channels
- Does NOT implement @everyone deny (private channel hardening)
- Does NOT implement write-only enforcement for evidence-log (deny DELETE_MESSAGES, MANAGE_MESSAGES)
- Uses UNSAFE token extraction via `$(sops -d ... | grep ... | awk ...)`
- Uses `DISCORD_BOT_TOKEN` env var instead of `DISCORD_SECRETS_PATH` (already established in P2-004..006)

---

## 2. P2-008 Requirements Matrix

### From StepPrompts (lines 5413–5478)

| Field | Value |
|---|---|
| **Type** | Integration |
| **Status** | ⬜ Not Started |
| **Risk** | Low |
| **Goal** | Set persona-flavored channel topics |
| **Dependencies** | P2-007 |
| **ADR** | ADR-022 |
| **AC** | AC-DISCORD-001 |
| **Time** | 1h |
| **Evidence path** | `docs/setup-evidence/P2/STEP-P2-008/topics.txt` |

### From CHECKLIST.md (line 245)

> `P2-008: Channel topics contain persona-flavored descriptions`

### From PROGRESS.md (line 128)

> `[ ] P2-008 Channel topics (persona-flavored)`

### From Implementation Synthesis (line 198)

> `P2-008: Channel topics/descriptions (persona-flavored)`

### CRITICAL: Current StepPrompts P2-008 code (lines 5421–5429)

The StepPrompts code has **only comments** — no actual implementation:

```bash
# Set channel topics with persona flavor (manual or via script)
# Example topics:
# guinevere-chat: "💬 Tempat ngobrol sama Mommy. Aku selalu dengerin kamu, Darling."
# guinevere-status: "📊 Status sistem Guinevere. Kalau ada yang merah, mommy langsung beresin."
# system-health: "🔔 Alert dan metrik sistem. SEV0-SEV4 routing aktif."
# Use the same Discord API pattern as P2-006 to update channel topics.
```

This was flagged in stepprompts-audit D6-012 (lines 140–142):
> `P2-008 and P2-009 have placeholder commands. P2-008 commands are comments with no actual script. Fix: Provide actual commands for P2-008.`

### P2-006 already set topics

The `src/discord/guild_setup.py` `CHANNELS` tuple already sets topics from DiscordUXSpec exact text. P2-008 needs to decide:
- **Option A**: Do nothing (topics already match DiscordUXSpec)
- **Option B**: Overwrite with extended persona-flavored versions (per StepPrompts example comments)
- **Option C**: Minor refinement (e.g. add emoji prefixes)

### Pre-mapped topics from internal-discord-structure-spec.md §5

Topics are pre-mapped from DiscordUXSpec§1.4 — same as what P2-006 already set.

### Unsafe token pattern

Line 5470: `DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk '{print $2}' | tr -d '"') \`

---

## 3. P2-009 Requirements Matrix

### From StepPrompts (lines 5413–5478)

| Field | Value |
|---|---|
| **Type** | Integration |
| **Status** | ⬜ Not Started |
| **Risk** | Low |
| **Goal** | Set persona-flavored topics + verify bot invite + permissions |
| **Dependencies** | P2-007 |
| **ADR** | ADR-022 |
| **AC** | AC-DISCORD-001 |
| **Time** | 1h |
| **Evidence path** | `docs/setup-evidence/P2/STEP-P2-009/bot-verify.txt` |

### From CHECKLIST.md (line 246)

> `P2-009: Bot online in server (green dot visible)`

### From PROGRESS.md (line 129)

> `[ ] P2-009 Bot invite + permission verification`

### From Implementation Synthesis (line 199)

> `P2-009: Bot invite + permission verification`

### Current StepPrompts code (lines 5431–5471)

The verify script:
- Connects to gateway, prints guild info
- Tests posting to all 13 channels with `ch.send("✅ Bot connectivity test")` then deletes
- Fast fail: test message is sent to ALL channels including evidence-log and audit-log which should be bot write-only (append-only) — this approach is acceptable for verification as long as the message is immediately deleted, but it's a one-time smoke test, not regular behavior
- Uses UNSAFE token extraction

### P2-003 auditor caveat (lines 195–205)

> **Should be revisited in P2-009**: Privileged intents exceed slash-only minimum.

### P2-001 auditor caveat (line 126)

> **Administrator permission**: Must be revisited during P2-009 permission verification.

---

## 4. Exact Channel List + IDs + Source Lines

### Category IDs

| Category | Position | ID | Source |
|---|---|---|---|
| `👑 Throne` | 0 | `1510913571226259456` | channel-ids.yaml line 2 |
| `📊 Surveillance` | 1 | `1510913575097598012` | channel-ids.yaml line 3 |
| `🔧 Projects` | 2 | `1510913578792915094` | channel-ids.yaml line 4 |
| `🗡️ Archive` | 3 | `1510913582315999333` | channel-ids.yaml line 5 |

### Channel IDs

| # | Channel Name | Category | ID | Source |
|---|---|---|---|---|
| 1 | `guinevere-chat` | 👑 Throne | `1510914600777023659` | channel-ids.yaml line 10 |
| 2 | `guinevere-status` | 👑 Throne | `1510914604291588237` | channel-ids.yaml line 15 |
| 3 | `guinevere-planning` | 👑 Throne | `1510914608263598122` | channel-ids.yaml line 14 |
| 4 | `system-health` | 📊 Surveillance | `1510914612038471720` | channel-ids.yaml line 19 |
| 5 | `cost-tracker` | 📊 Surveillance | `1510914615654092900` | channel-ids.yaml line 8 |
| 6 | `guinevere-evidence` | 📊 Surveillance | `1510914619357532200` | channel-ids.yaml line 13 |
| 7 | `guinevere-dev` | 🔧 Projects | `1510914623367413850` | channel-ids.yaml line 11 |
| 8 | `guinevere-docs` | 🔧 Projects | `1510914627444408421` | channel-ids.yaml line 12 |
| 9 | `project-alpha-dev` | 🔧 Projects | `1510914630770233426` | channel-ids.yaml line 16 |
| 10 | `project-alpha-docs` | 🔧 Projects | `1510914634788638813` | channel-ids.yaml line 17 |
| 11 | `project-beta-dev` | 🔧 Projects | `1510914639163162657` | channel-ids.yaml line 18 |
| 12 | `evidence-log` | 🗡️ Archive | `1510914643823034449` | channel-ids.yaml line 9 |
| 13 | `audit-log` | 🗡️ Archive | `1510914647602106408` | channel-ids.yaml line 7 |

**Total: 4 categories, 13 channels**

---

## 5. Required Permission Matrix (per DiscordUXSpec)

### From DiscordUXSpec §1.4 — per-channel permission requirements

| Channel | Faiz | Bot | Notes |
|---|---|---|---|
| `guinevere-chat` | read + write | read + write | Sub-agents: no access |
| `guinevere-status` | read + write | read + write | |
| `guinevere-planning` | read + write | read + write | |
| `system-health` | read + write | read + write | |
| `cost-tracker` | read + write | read + write | |
| `guinevere-evidence` | **read-only** | **write-only** | Bot cannot edit/delete — immutable record |
| `guinevere-dev` | read + write | read + write | |
| `guinevere-docs` | read + write | read + write | |
| `project-alpha-dev` | read + write | read + write | |
| `project-alpha-docs` | read + write | read + write | |
| `project-beta-dev` | read + write | read + write | |
| `evidence-log` | **read-only** (cannot post/delete) | **write-only** (append-only) | Bot cannot edit or delete — canonical audit trail |
| `audit-log` | **read-only** | **write-only** (append-only) | |

### Write-only enforcement mechanism (from DiscordUXSpec §1.4.10, lines 323–324)

For evidence-log and audit-log:
```
Faiz: deny SEND_MESSAGES, deny MANAGE_MESSAGES, deny DELETE_MESSAGES
Bot: deny MANAGE_MESSAGES, deny DELETE_MESSAGES — allow SEND_MESSAGES, allow READ_MESSAGE_HISTORY
```

For guinevere-evidence:
```
Faiz: deny SEND_MESSAGES
Bot: deny MANAGE_MESSAGES, deny DELETE_MESSAGES — allow SEND_MESSAGES
```

### @everyone default (private server hardening)

All channels should have:
```
@everyone: deny VIEW_CHANNEL
```

This makes the server truly private. Currently channels were created without permission overwrites, so @everyone inherits guild-level defaults.

### CHECKLIST.md vs DiscordUXSpec conflict

| Source | Statement |
|---|---|
| CHECKLIST.md line 244 | `evidence-role=write-only` |
| DiscordUXSpec §1.4 | Faiz read-only + bot write-only for evidence channels |
| Resolution | DiscordUXSpec is authoritative. No "evidence-role" exists. The permission split is **Faiz vs Bot**, not a dedicated role. |

---

## 6. Administrator Caveat — Full Trace

The bot currently has ADMINISTRATOR permission. This is flag in 6+ sources:

### Source 1: P2-001 auditor (step-p2-001-auditor-report.md, line 126)

> **Caveat**: "Administrator permission is documented as a Faiz-approved private-server choice. It conflicts with some older minimal-permission security checklist language and must be revisited during P2-009 permission verification."

### Source 2: P2-002 auditor (step-p2-002-auditor-report.md, line 218)

> **E5**: "Administrator permission vs security docs minimal-permission principle — LOW — Faiz-approved for private server; tracking for P2-009"

### Source 3: P2-003 auditor (step-p2-003-auditor-report.md, lines 195–205)

> **Caveat**: "Privileged intents exceed slash-only minimum... should be reviewed again during P2-009 permission verification."

### Source 4: P2-001 verification.md §8 item 2

> "Must be revisited during P2-009 permission verification"

### Source 5: batch-plan-001-003.md (line 451)

> "Permission review should be part of P2-009"

### Source 6: discord-permissions-model.md §9 (lines 256–264)

> Risk: If removing ADMINISTRATOR, bot needs explicit MANAGE_CHANNELS + MANAGE_ROLES
> Verification: After removing admin, test `guild.me.guild_permissions` before any create/edit

### Implication for P2-007/P2-009

**Two paths exist** and must be explicitly chosen before implementation:

| Path | Action | Risk |
|---|---|---|
| **Keep Administrator** | P2-007 permission overwrites still work but bot bypasses all channel restrictions | Security docs non-compliant, but functional |
| **Remove Administrator** | Must grant exact OAuth2 scopes (manage_channels, manage_roles, view_channel, send_messages); P2-007 overwrites become meaningful | Bot may lose abilities if scopes are wrong; must test thoroughly |

---

## 7. Unsafe StepPrompts Token Patterns to Replace

### Pattern 1: P2-007 StepPrompts (line 5402)

```bash
DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk '{print $2}' | tr -d '"') \
  python scripts/setup-permissions.py
```

**Problems:**
1. Token leaked via argv — visible in `ps aux` process listing
2. Shell YAML parsing: `grep awk tr` is not robust YAML parsing; multi-line values, quotes, or special characters will break
3. Token set as shell env var before Python start — visible in procfs environment
4. Alternative already exists: `DISCORD_SECRETS_PATH` pattern from P2-004..006

### Pattern 2: P2-008/P2-009 StepPrompts (line 5470)

```bash
DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk '{print $2}' | tr -d '"') \
  python scripts/verify-bot.py
```

**Same problems as Pattern 1.**

### Replacement Pattern (already established in P2-004..006 via batch-plan-004-006.md §15)

```bash
# SOPS+age token flow (safe)
SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt
TEMP_SECRETS=$(mktemp /tmp/guinevere-secrets-XXXXXX.yaml)
trap "rm -f $TEMP_SECRETS" EXIT
sops --decrypt /home/guinevere/code/guinevere/secrets/discord-secrets.yaml > $TEMP_SECRETS
export DISCORD_SECRETS_PATH=$TEMP_SECRETS

cd /home/guinevere/code/guinevere
source .venv/bin/activate
python scripts/setup-permissions.py  # reads DISCORD_SECRETS_PATH internally

# Cleanup handled by trap
unset DISCORD_SECRETS_PATH
```

### All locations in StepPrompts.md with unsafe patterns

| Line | Step | Pattern |
|---|---|---|
| 5228 | P2-003 (history) | `sops -d ... \| grep ... \| head -c 20` |
| 5402 | P2-007 | `DISCORD_BOT_TOKEN=$(sops ...)` via argv |
| 5470 | P2-008/P2-009 | `DISCORD_BOT_TOKEN=$(sops ...)` via argv |
| 5592 | P2-010 | `DISCORD_BOT_TOKEN=$(sops ...)` via argv |
| 5915 | Multiple (batch) | `BOT_TOKEN=$(sops ...)` via argv |
| 5917 | Multiple | `DISCORD_BOT_TOKEN=PLACEHOLDER` hardcoded |

---

## 8. Prior P2-003/P2-006 Caveats for P2-007/008/009

### From P2-003 auditor (step-p2-003-auditor-report.md)

| Caveat | Details | Applies to |
|---|---|---|
| Privileged intents (message_content, members, presences) exceed slash-only minimum | Faiz-approved for companion behavior; revisit in P2-009 | P2-009 |
| Evidence documents cast() usage for dynamic import | Not a type bypass; necessary for local `src.discord` package collision | P2-007 (if implementing permissions code) |

### From P2-006 auditor (step-p2-006-auditor-report.md)

| Caveat | Details | Applies to |
|---|---|---|
| channel-ids.yaml ready for P2-007 consumption | Machine-parseable YAML, all 4 category IDs + 13 channel IDs | P2-007 |
| Pre-existing extras preserved | Default Discord objects intentionally not deleted | P2-007 (permissions should account for extras) |

### From P2-006 verification.md §8 — Gateway→REST migration

The REST verifier was used instead of gateway verifier because gateway hung (timeout). P2-007 and P2-009 scripts should use the **REST-based pattern** (via `fetch` guild/channel endpoints) rather than gateway-dependent `on_ready()` pattern where possible.

### From batch-plan-004-006.md §16 (P2-007 note, lines 993–998)

> P2-007 should read `channel-ids.yaml` instead of making fresh API calls.

### From batch-plan-004-006.md §16 (P2-008 note, lines 1000–1003)

> Basic topics already set in P2-006 via CHANNEL_TOPICS dict. P2-008 can overwrite topics with extended versions.

### From batch-plan-004-006.md §16 (P2-009 note, lines 1006–1009)

> P2-009 will implement gateway connection, event handlers, slash commands. Channel IDs from P2-006 evidence will be useful for command routing.

---

## 9. Current Code Patterns (guild_setup.py)

### Token handling pattern (safe)

```python
def get_token() -> str:
    secrets_path_raw = os.environ.get("DISCORD_SECRETS_PATH")
    # ... validates, reads YAML key "discord_bot_token"
    return token
```

This is the established safe pattern. Any new P2-007/008/009 scripts should reuse `get_token()` from `guild_setup.py` or follow the same `DISCORD_SECRETS_PATH` env var + YAML read pattern.

### Client creation pattern

```python
def create_client() -> DiscordClient:
    discord_module = get_discord_module()
    intents = discord_module.Intents.default()
    intents.guilds = True
    return discord_module.Client(intents=intents)
```

This creates a minimal guilds-only client. P2-007 permission edits need `MANAGE_CHANNELS` and `MANAGE_ROLES` (bot already has ADMINISTRATOR). P2-009 verification needs `message_content` for sending test messages.

### Data flow: Constants → Operations → Results

The module uses typed Dataclasses (`CategorySpec`, `ChannelSpec`, `OperationResult`) and Protocols for Discord types. P2-007 should follow the same pattern.

### channel-ids.yaml output pattern

The `capture_ids()` function generates the machine-parseable YAML that P2-007 should consume. P2-007 implementation should read this file rather than making fresh API calls.

---

## 10. Contradictions and Conflicts

### C1: CHECKLIST.md says "evidence-role=write-only" — no such role exists

| Source | Statement |
|---|---|
| CHECKLIST.md line 244 | `evidence-role=write-only` |
| DiscordUXSpec §1.4 | Faiz read-only + bot write-only for evidence channels |
| **Resolution** | DiscordUXSpec is authoritative. Permission split is Faiz vs Bot, not a dedicated role. No "evidence-role" exists in the current setup. |

### C2: StepPrompts P2-007 code does not implement DiscordUXSpec matrix

The StepPrompts code at lines 5373–5403 only sets bot permissions on ALL channels uniformly (`read_messages=True, send_messages=True, embed_links=True, attach_files=True, read_message_history=True`). It does not:
- Implement Faiz read-only for evidence-log/audit-log/guinevere-evidence
- Implement bot write-only for evidence channels (deny MANAGE_MESSAGES, deny DELETE_MESSAGES)
- Implement @everyone deny VIEW_CHANNEL (private server hardening)

### C3: P2-008 topics may be redundant with P2-006

P2-006 already set canonical topics from DiscordUXSpec. P2-008's stated goal "persona-flavored descriptions" could mean:
- **A**: Topics are already correct (P2-008 is a no-op)
- **B**: Topics need extended persona flavor (e.g. adding emoji prefixes)

If Option A, P2-008 step should be marked as completed by P2-006 with a note. If Option B, clear new topic strings must be defined.

### C4: P2-009 test message conflicts with write-only channels

The verification pattern sends "✅ Bot connectivity test" to ALL 13 channels, including evidence-log and audit-log. On these channels:
- If bot write-only is enforced (after P2-007): the post will be PERMITTED (bot has send_messages), but the evidence channels get artificial test messages
- If P2-007 hasn't run yet: no issue, but the test creates messages that must be cleaned up

**Recommendation**: P2-009 verification should NOT test post to evidence-log and audit-log, OR should be designed to never leave artifacts (send → delete immediately, as the code already does).

### C5: ADMINISTRATOR permission makes P2-007 overwrites meaningless

While the bot has ADMINISTRATOR, all permission overwrites set in P2-007 are short-circuited — the bot bypasses all channel restrictions. P2-007 will set the correct overwrites, but they will only take effect AFTER ADMINISTRATOR is removed (deferred to P2-009).

This is actually **the correct order**: set overwrites first (P2-007), then verify and remove admin (P2-009). But it must be documented that P2-007 effects are latent until P2-009.

---

## 11. Implementation Recommendations

### P2-007 Implementation

1. **Read channel-ids.yaml** for channel IDs — do not make fresh API calls
2. **Reuse `get_token()` + `DISCORD_SECRETS_PATH`** pattern from `guild_setup.py` — do NOT use the StepPrompts unsafe shell pattern
3. **Create `src/discord/permissions.py`** module with permission constants and functions
4. **Permission overwrite matrix** per DiscordUXSpec:

```python
# Channel-specific overwrites
EVERYONE_DENY = discord.PermissionOverwrite(read_messages=False)
BOT_FULL = discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True)
BOT_WRITE_ONLY = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
FAIZ_FULL = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
FAIZ_READ_ONLY = discord.PermissionOverwrite(read_messages=True, send_messages=False)
```

5. **Write evidence** to `docs/setup-evidence/P2/STEP-P2-007/permissions-test.txt`
6. **Insert auditor gate** at `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md`
7. **Document the Administrator latency caveat** ("Permissions set but latent until P2-009 admin removal")

### P2-008 Implementation (if needed)

1. **Check if topics already match**: `guild_setup.py` lines 202–214 already set DiscordUXSpec canonical topics
2. **If YES**: Mark P2-008 as completed by P2-006, update evidence
3. **If NO**: Create topic update script using `DISCORD_SECRETS_PATH` pattern, update individual channel topics
4. **Write evidence** to `docs/setup-evidence/P2/STEP-P2-008/topics.txt`
5. **Insert auditor gate** at `audit-reports/P2/STEP-P2-008/step-p2-008-auditor-report.md`

### P2-009 Implementation

1. **Reuse `get_token()` + `DISCORD_SECRETS_PATH`** pattern — do NOT use unsafe shell pattern
2. **Create `tmp/verify-p2-009-bot.py`** script that:
   - Connects to gateway
   - Prints guild name, member count, channel count
   - Prints `guild.me.guild_permissions` (for Administrator check)
   - Tests posting to non-evidence channels only (skip evidence-log, audit-log, guinevere-evidence)
   - Verifies bot is online (green dot)
3. **Address P2-001/P2-003 caveats**: Document current Administrator status and recommend review
4. **Document privileged intents rationale** per P2-003 auditor recommendation
5. **Write evidence** to `docs/setup-evidence/P2/STEP-P2-009/bot-verify.txt`
6. **Insert auditor gate** at `audit-reports/P2/STEP-P2-009/step-p2-009-auditor-report.md`

---

## 12. Evidence and Auditor Paths

| Step | Evidence Path | Auditor Report Path |
|---|---|---|
| P2-007 | `docs/setup-evidence/P2/STEP-P2-007/permissions-test.txt` | `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md` |
| P2-008 | `docs/setup-evidence/P2/STEP-P2-008/topics.txt` | `audit-reports/P2/STEP-P2-008/step-p2-008-auditor-report.md` |
| P2-009 | `docs/setup-evidence/P2/STEP-P2-009/bot-verify.txt` | `audit-reports/P2/STEP-P2-009/step-p2-009-auditor-report.md` |

---

## 13. Footer

| Field | Value |
|---|---|
| **Source task** | P2-007, P2-008, P2-009 internal spec audit |
| **Date** | 2026-06-01 |
| **Author** | Guinevere (parent, spec auditor) |
| **Documents read** | 15 (see sources) |
| **Conflicts identified** | 5 (C1 through C5) |
| **Unsafe patterns** | 6 locations in StepPrompts (lines 5228, 5402, 5470, 5592, 5915, 5917) |
| **Contradictions** | CHECKLIST vs DiscordUXSpec (evidence-role), P2-007 code vs spec, P2-006 vs P2-008 topic overlap, P2-009 test vs write-only channels, Administrator latency |
| **Ready for** | Implementation planning for P2-007+ |
