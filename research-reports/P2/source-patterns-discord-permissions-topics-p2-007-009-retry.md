# Implementation Design: P2-007 → P2-009 (Permissions, Topics, Admin Review)

**Source:** Research report for parent planning  
**Date:** 2026-06-01  
**Scope:** Local artifact inspection only; no Discord mutation, no decryption, no external web

---

## Existing Patterns

### 1. SOPS Token Wrapper
Two proven scripts: `scripts/setup-guild.sh` and `scripts/run-discord-verify.sh`.

```
sops --decrypt "$SECRET_FILE" > "$TEMP_SECRETS"    # decrypt to temp
export DISCORD_SECRETS_PATH="$TEMP_SECRETS"          # env var for Python
# cleanup: shred temp file on EXIT via trap
```

Python side: `guild_setup.get_token()` reads `discord_bot_token` from `DISCORD_SECRETS_PATH` YAML via line-scan (`read_scalar_yaml_value`). No PyYAML dependency.

**→ P2-007/008/009 should reuse `get_token()` or duplicate the `read_scalar_yaml_value` pattern.**

### 2. Two API Approaches

| Approach | File | Use case |
|---|---|---|
| **Gateway (discord.py)** | `guild_setup.py` `ensure_text_channel()` | Mutations: `channel.edit(topic=...)`, `channel.set_permissions(...)` |
| **REST API (http.client)** | `verify-p2-006-channels-rest.py` | Read-only verification, YAML output |

**→ P2-007/008 mutations** (set_permissions, topic edit) **must use gateway.**  
**→ P2-009 verification** (bot test post, permission audit) can use gateway or REST.

### 3. Channel ID Discovery
`channel-ids.yaml` stores static channel/category snowflakes from P2-006:

```yaml
channels:
  'guinevere-chat': 1510914600777023659
  'evidence-log': 1510914643823034449
  ...
```

**→ P2-007/008 SHOULD read from this file** instead of hardcoding IDs.  
**→ Guild/member/role IDs MUST be discovered at runtime** via `guild.me` / `guild.get_member()` / `guild.default_role`.

### 4. Current Guild Setup Module (`guild_setup.py`)
- `GUILD_ID` is hardcoded (1510876414671323206) — canonical.
- `DiscordTextChannel` protocol includes `topic` field and `edit()` with `topic=` param.
- No `set_permissions` yet in any protocol — needs to be added.
- No role-based overwrite support yet — `@everyone` deny not covered.

---

## Proposed Designs

### P2-007 — Channel Permissions Configuration

**File:** `scripts/setup-permissions.py` (new), reusing `guild_setup.py` patterns.

**Design:**
```python
# 1. Import get_token() from guild_setup (or inline read_scalar_yaml_value)
# 2. Create client with guilds intents only (same as create_client())
# 3. On ready:
#    a. guild = client.get_guild(GUILD_ID)
#    b. bot_member = guild.me
#    c. everyone_role = guild.default_role
#    d. faiz_member = guild.get_member(FAIZ_DISCORD_ID)  # discovered at runtime
#    e. For each channel in guild.text_channels:
#       - await channel.set_permissions(everyone_role, read_messages=False)
#       - await channel.set_permissions(faiz_member, read_messages=True, send_messages=True, ...)
#       - await channel.set_permissions(bot_member, read_messages=True, send_messages=True,
#                                        embed_links=True, attach_files=True)
#    f. For evidence/archive channels (detected by name: evidence-log, audit-log):
#       - Bot: read_messages=False, send_messages=True (write-only)
# 4. Output: write verification results to docs/setup-evidence/P2/STEP-P2-007/permissions-test.txt
```

**Key decisions:**
- **No hardcoded member/role IDs** — discover `guild.me` (bot), `guild.default_role` (@everyone), `guild.get_member(operator_id)`.
- **Read category/channel IDs from `channel-ids.yaml`** only for the canonical names list; runtime channel objects already have correct IDs.
- **Protocol extension required**: Add `set_permissions` to `DiscordTextChannel` or a new `DiscordGuildChannel` protocol in `guild_setup.py`.
- **Evidence channels** = `evidence-log` and `audit-log` — bot gets write-only (`send_messages=True`, `read_messages=False`).

**Evidence path:** `docs/setup-evidence/P2/STEP-P2-007/permissions-test.txt`

### P2-008 — Channel Topics Update

**Approach A (preferred):** Extend `ensure_text_channel` in `guild_setup.py` to accept a topic-update-only mode, or write a new standalone script.

**Design:**
```python
# 1. Read CHANNELS specs from guild_setup (already have canonical topics)
# 2. Read channel IDs from channel-ids.yaml
# 3. Use REST API PATCH /channels/{id} (simpler, no gateway overhead)
#    - Same pattern as verify-p2-006-channels-rest.py
#    - PATCH with body: {"topic": "<new-topic>"}
# 4. Verify: read back topics via GET /channels/{id} and assert match
```

**Channel topics from StepPrompts:**

| Channel | Proposed topic |
|---|---|
| guinevere-chat | "💬 Tempat ngobrol sama Mommy. Aku selalu dengerin kamu, Darling." |
| guinevere-status | "📊 Status sistem Guinevere. Kalau ada yang merah, mommy langsung beresin." |
| guinevere-planning | "Rencana Mommy. Kamu tinggal patuh." |
| system-health | "🔔 Alert dan metrik sistem. SEV0-SEV4 routing aktif." |
| cost-tracker | "Berapa yang Mommy habiskan hari ini. Transparansi itu penting." |
| guinevere-evidence | "Bukti kerja Mommy. Tidak ada yang bisa diubah." |
| guinevere-dev | "Pengembangan Guinevere — technical discussions and decisions." |
| guinevere-docs | "Documentation updates, spec changes, evidence artifacts." |
| project-alpha-dev | "Project Alpha — development channel." |
| project-alpha-docs | "Project Alpha — documentation channel." |
| project-beta-dev | "Project Beta — development channel." |
| evidence-log | "Immutable record. Read only." |
| audit-log | "Every action, recorded. Forever." |

**Note:** Topics may already be correct from P2-006 (guild_setup.py already has `ensure_text_channel` setting topic on create/fix). Verify first before updating.

**Evidence path:** `docs/setup-evidence/P2/STEP-P2-008/topics.txt`

### P2-009 — Permission-Scope / Admin Review

**File:** `scripts/verify-bot-permissions.py` (new)

**Design:**
```python
# PHASE 1: Audit current permissions
# 1. Connect via gateway (same pattern as guild_setup)
# 2. For each channel:
#    a. List permission overwrites via channel.overwrites or REST
#    b. Print effective permissions for @everyone, bot, Faiz
# 3. Print guild.me.guild_permissions (current bot guild-level perms)

# PHASE 2: Bot test post
# 4. Post + delete test message in each channel (same as StepPrompts P2-009)
# 5. Report success/failure per channel

# PHASE 3: Administrator reduction analysis
# 6. Check if bot currently has Administrator
# 7. If yes, document minimum required permissions:
#    - Manage Channels (for P2-007 setup, can revoke after)
#    - View Channels + Send Messages (permanent)
#    - Read Message History (permanent)
#    - Embed Links + Attach Files (permanent)
# 8. Recommend: keep Administrator until P2-010 (slash commands) is done,
#    then reduce to the specific set above.
# 9. Write audit report with safe transition plan.
```

**Evidence path:** `docs/setup-evidence/P2/STEP-P2-009/bot-verify.txt`  
**Audit output:** (can be appended to same file or `admin-review-report.txt`)

---

## File Structure Summary

| Step | File(s) | Pattern |
|---|---|---|
| P2-007 | `scripts/setup-permissions.py` | Gateway (discord.py) via `create_client()` + channel `set_permissions()` |
| P2-007 protocols | Extend `guild_setup.py` with `set_permissions` on `DiscordTextChannel` | Protocol addition |
| P2-008 | `scripts/setup-topics.py` or extend guild_setup | REST PATCH (preferred) or gateway edit |
| P2-009 | `scripts/verify-bot-permissions.py` | Gateway audit + test post + admin reduction analysis |
| All steps | Reuse `scripts/run-discord-verify.sh` pattern for shell wrapper | SOPS → env var → Python |

## Token Handling

All scripts MUST use the existing SOPS wrapper pattern:
1. Shell wrapper decrypts secrets → temp file → `DISCORD_SECRETS_PATH` env var.
2. Python reads `DISCORD_SECRETS_PATH` → `get_token()` → uses token → clears token var.
3. Shell trap cleans up temp file on exit.
4. Never print, log, or persist the token.

See `scripts/run-discord-verify.sh` for the exact wrapper template.

## Pre-Existing Constraint: Administrator

Current bot has `Administrator` (private guild). `@everyone` deny via `set_permissions` is **only advisory** — Administrator bypasses all overwrites. P2-007 permission overwrites ARE correct for non-admin users/roles, but the bot's own access will not be restricted until Administrator is removed in P2-009 (or post-P2-010).

**Recommendation:** Set overwrites in P2-007 (they work for Faiz/@everyone), defer bot Administrator reduction to P2-009 after verifying all slots/slash commands work without it.

---

## Verdict

**PASS** — Sufficient local artifact context exists to proceed with implementation. No external Discord mutation or decryption was performed. Full design above is ready for parent planning.