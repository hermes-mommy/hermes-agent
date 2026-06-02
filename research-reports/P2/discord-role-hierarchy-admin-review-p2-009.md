# P2-009: Discord Bot Administrator Permission Review — Least-Privilege Strategy

**Date**: 2026-06-01
**Scope**: Security review of Guinevere bot's Administrator (`0x8`) permission assignment
**Reviewer**: The Librarian (Research Agent)
**Status**: DRAFT for P2 review

---

## Executive Summary

Guinevere bot currently has **Administrator permission** (`0x0000000000000008`, bit `1 << 3`) on Faiz's private Discord server. This report evaluates whether Administrator is justified or should be reduced to a minimal permission set following Discord's documented best practices and the principle of least privilege.

**Verdict**: Administrator is **not technically justified** for Guinevere's current and planned feature set. A transition to least-privilege permissions is recommended with a phased plan, while acknowledging the **private single-user server caveat** as a risk-mitigating factor.

---

## 1. Official Discord Documentation: Permissions Model

### 1.1 Administrator Permission Definition

Per Discord's official [Permissions documentation](https://docs.discord.com/developers/topics/permissions):

| Permission | Value | Description |
|---|---|---|
| ADMINISTRATOR * | `0x0000000000000008` `(1 << 3)` | Allows all permissions and bypasses channel permission overwrites |

> "The Administrator permission is a special permission on a Discord role in that it grants every Discord permission and allows users with that permission to bypass all channel-specific permissions. Because of this granting this role to any user or bot should be done with the utmost caution and on an as-needed basis."
> — [Discord Community: Permissions on Discord](https://discord.com/community/permissions-on-discord-discord)

### 1.2 How Permissions Are Computed

Discord's permission system (from the official [permissions pseudocode](https://docs.discord.com/developers/topics/permissions#permission-hierarchy)):

```python
def compute_base_permissions(member, guild):
    if guild.is_owner(member):
        return ALL
    role_everyone = guild.get_role(guild.id)
    permissions = role_everyone.permissions
    for role in member.roles:
        permissions |= role.permissions
    if permissions & ADMINISTRATOR == ADMINISTRATOR:
        return ALL  # <-- Administrator bypasses ALL checks
    return permissions
```

**Key implication**: With Administrator, Discord's permission system returns `ALL` at the base level, meaning **no channel overwrites, no role hierarchy checks, no implicit permission denials apply** — the bot can do everything everywhere.

### 1.3 Elevated Permissions (Require 2FA on 2FA-enabled servers)

Permissions marked with `*` in Discord's docs require the owner account to use 2FA when the guild has server-wide 2FA enabled:

- `KICK_MEMBERS`, `BAN_MEMBERS`, `ADMINISTRATOR`
- `MANAGE_CHANNELS`, `MANAGE_GUILD`
- `MANAGE_MESSAGES`, `MANAGE_ROLES`, `MANAGE_WEBHOOKS`
- `MANAGE_GUILD_EXPRESSIONS`, `MANAGE_THREADS`
- `VIEW_CREATOR_MONETIZATION_ANALYTICS`

---

## 2. Risks of Administrator Permission

### 2.1 Compromise Blast Radius

From [xoe.gg Discord Bot Security Risks (2026)](https://xoe.gg/blog/discord-bot-security-risks-protect-server):

> "Administrator: The nuclear option. A bot with Administrator permission can do anything — delete channels, ban members, change server settings, read all messages. If this bot is compromised, your entire server is compromised."

If Guinevere's bot token is leaked or the runtime is compromised, an attacker with Administrator can:
- **Delete all channels** instantly
- **Ban/kick all members** (relevant if the server expands)
- **Create malicious roles** with Administrator and assign them
- **Read all messages** in all channels (bypassing any channel-level restrictions)
- **Modify server settings** (name, icon, verification level, etc.)
- **Create/manage webhooks** for exfiltration
- **Grant itself to other servers** if the bot is public

### 2.2 Developer Policy Violation Potential

Discord's [Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy) states:

> "Do not enable your Application to bypass or circumvent Discord's privacy, safety, and/or security features."

While requesting Administrator isn't itself a violation, Discord's [OAuth2 docs](https://docs.discord.com/developers/platform/oauth2-and-permissions) explicitly advise:

> "Your app should request only the permissions it needs. Requesting excessive permissions reduces trust with users."

### 2.3 Industry Consensus

Multiple authoritative sources uniformly recommend against Administrator:

| Source | Position |
|---|---|
| [Discord Developer Docs](https://docs.discord.com/developers/platform/oauth2-and-permissions) | "Request only the permissions it needs" |
| [Discord Community Guide](https://discord.com/community/permissions-on-discord-discord) | "Utmost caution, on an as-needed basis" |
| [xoe.gg Bot Security Guide (2026)](https://xoe.gg/blog/discord-bot-security-risks-protect-server) | "Almost never. Administrator grants unrestricted access" |
| [GitHub Discussion #4864](https://github.com/discord/discord-api-docs/discussions/4864) | Community consensus: bots should not request Admin on invite |
| [TopServersDiscord (2026)](https://topserversdiscord.com/en/blog/discord-bot-privacy-what-to-know) | "Administrator overrides every permission and is almost never actually required" |
| [ClawdHost AI Bot Guide (2026)](https://clawdhost.net/blog/discord-ai-bot-complete-guide/) | "Never grant Administrator unless absolutely necessary" |

---

## 3. Guinevere Function Inventory & Minimal Permission Set

### 3.1 Guinevere Core Functions (from BRD/PRD v2.x)

| Function | Required Permissions | Notes |
|---|---|---|
| Slash command handling | `USE_APPLICATION_COMMANDS` (already granted by `applications.commands` scope) | No bot permission needed for command registration |
| Message sending (AI responses) | `SEND_MESSAGES`, `VIEW_CHANNEL` | Text channel operations |
| Embed responses | `EMBED_LINKS` (implied by `SEND_MESSAGES`) | Rich embed responses |
| Message history reading | `READ_MESSAGE_HISTORY` | For conversation context |
| File attachment handling | `ATTACH_FILES` | Image/file generation |
| Reaction handling | `ADD_REACTIONS`, `READ_MESSAGE_HISTORY` | UX interactions |
| Role management (P2-007) | `MANAGE_ROLES` | For permission overwrites and role assignments |
| Channel management (P2-007) | `MANAGE_CHANNELS` | For channel permission overwrites |
| Member timeout/moderation | `MODERATE_MEMBERS` | For moderation commands |
| Audit log monitoring | `VIEW_AUDIT_LOG` | For security monitoring |
| Voice channel (future) | `CONNECT`, `SPEAK` | Future voice features |

### 3.2 Minimal Permission Integer Calculation

Using Discord's bitwise flags:

| Permission | Hex Value | Decimal |
|---|---|---|
| `VIEW_CHANNEL` | `0x400` (1 << 10) | 1,024 |
| `SEND_MESSAGES` | `0x800` (1 << 11) | 2,048 |
| `MANAGE_MESSAGES` | `0x2000` (1 << 13) | 8,192 |
| `EMBED_LINKS` | `0x4000` (1 << 14) | 16,384 |
| `ATTACH_FILES` | `0x8000` (1 << 15) | 32,768 |
| `READ_MESSAGE_HISTORY` | `0x10000` (1 << 16) | 65,536 |
| `ADD_REACTIONS` | `0x40` (1 << 6) | 64 |
| `USE_APPLICATION_COMMANDS` | `0x80000000` (1 << 31) | 2,147,483,648 |
| `VIEW_AUDIT_LOG` | `0x80` (1 << 7) | 128 |
| `MANAGE_ROLES` | `0x10000000` (1 << 28) | 268,435,456 |
| `MANAGE_CHANNELS` | `0x10` (1 << 4) | 16 |
| `MODERATE_MEMBERS` | `0x10000000000` (1 << 40) | 1,099,511,627,776 |
| `CREATE_INSTANT_INVITE` | `0x1` (1 << 0) | 1 |

**Core permission integer** (conversational AI + slash commands):
```
1,024 + 2,048 + 16,384 + 32,768 + 65,536 + 64 + 2,147,483,648 = 2,147,599,472
```
**Hex**: `0x8000F870`

**Full permission integer** (core + moderation + management for P2-007):
```
1,024 + 2,048 + 8,192 + 16,384 + 32,768 + 65,536 + 64 + 2,147,483,648 + 128 + 268,435,456 + 16 + 1,099,511,627,776 + 1
```
**= 1,099,512,041,402,041** (approx)

> **Current**: Administrator = permission integer `8` (all-powerful, value `-1` / all bits set)
> **Recommended**: Minimal permission integer specifying only the required bits above.

### 3.3 OAuth2 Scopes Required

| Scope | Purpose |
|---|---|
| `bot` | Add bot to guild |
| `applications.commands` | Slash command registration |

No additional OAuth2 scopes are needed beyond these two.

---

## 4. Transition Plan: Administrator → Least Privilege

### Phase 1: Audit & Inventory (Immediate)

1. **Catalog all current bot commands and features** against the table in §3.1
2. **Identify any feature that genuinely requires Administrator** (see §4.1 for edge cases)
3. **Document any channel permission overwrites** the bot relies on

### Phase 2: Create Least-Privilege Role (Next)

1. Create a new role `Guinevere` (or modify the existing bot role) with only the permissions identified in §3.2
2. Ensure the bot's role is **positioned below the server owner** but above any roles it needs to manage (per Discord role hierarchy)
3. Do NOT remove Administrator yet — create the new role alongside it first

### Phase 3: Parallel Testing

1. With Administrator still active (as fallback), the bot runs under the new limited role
2. Test every command and feature
3. If any feature fails due to missing permissions, add that specific permission to the role (not Administrator)
4. Run for a **minimum of 7 days** of active use

### Phase 4: Remove Administrator

1. Once all features are verified under the least-privilege role, **remove Administrator from the bot's role**
2. Keep `MANAGE_ROLES` and `MANAGE_CHANNELS` if P2-007 requires it
3. Document the final permission integer in the project's ops manual

### Phase 5: Ongoing Auditing

1. **Monthly permission review**: Check that no permission drift has occurred
2. **Audit log monitoring**: Use `VIEW_AUDIT_LOG` to monitor for unexpected permission changes
3. **Token rotation**: Periodic bot token rotation (Developer Portal → Bot → Reset Token)

### 4.1 Potential Administrator Edge Cases

These are the rare cases where Administrator might be technically necessary, **none of which apply to Guinevere's current architecture**:

| Scenario | Does Guinevere need it? |
|---|---|
| Anti-nuke/raid protection bots (e.g., Wick) | No — Guinevere is a companion AI, not a security bot |
| Bots that need to manage other bot roles | No — no bot management features planned |
| Bots that create/manage categories with complex permission syncing | Possibly P2-007 — but `MANAGE_CHANNELS` + `MANAGE_ROLES` suffice |
| Bots that bypass all channel overwrites globally | No — Guinevere operates in specific channels |

---

## 5. Verification Commands & API

### 5.1 Verify Current Bot Permissions (Discord Client)

In any channel, right-click the bot → Roles → view assigned permissions.

### 5.2 Verify Permissions Programmatically (discord.py)

```python
# Check bot's computed permissions in a specific channel
channel = bot.get_channel(CHANNEL_ID)
me = channel.guild.me
perms = channel.permissions_for(me)

# Specific checks
print(f"send_messages={perms.send_messages}")
print(f"manage_roles={perms.manage_roles}")
print(f"administrator={perms.administrator}")
print(f"view_channel={perms.view_channel}")
```

**Source**: [ErrorMedic Discord API Troubleshooting Guide](https://errormedic.com/api/discord-api/discord-api-rate-limit-401-403-timeout-errors-complete-troubleshooting-guide)

### 5.3 Verify via Discord REST API

```http
GET /guilds/{guild.id}/members/{bot.user.id}
```

Response includes the `roles` array (role IDs) and `permissions` string.

To check current bot role permissions:

```http
GET /guilds/{guild.id}/roles
```

Find the bot's role and inspect the `permissions` field.

### 5.4 Verify Invite Link Permissions

The OAuth2 invite URL includes the `permissions` parameter:

```
https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&scope=bot%20applications.commands&permissions={INTEGER}
```

Generate a new invite link with the minimal permission integer to verify the invite flow.

### 5.5 Permission Calculator Tools

- [Discord Permissions Calculator](https://xgamingserver.com/tools/discord-bot/permissions) — Visual bit-mask builder
- [VibeCord Permission Calculator](https://vibecord.dev/tools/permission-calculator) — another UI-based calculator
- [Klartext Permission Calculator](https://klartext-tools.com/en/discord-tools/discord-permission-calculator/) — supports decode mode for existing integers

---

## 6. Audit Log Considerations

### 6.1 Audit Log API

Per [Discord Audit Log docs](https://docs.discord.com/developers/resources/audit-log):

- **Endpoint**: `GET /guilds/{guild.id}/audit-logs`
- **Required permission**: `VIEW_AUDIT_LOG` (`0x80`, bit 7)
- **Retention**: All audit log entries stored for **45 days**
- **Reason header**: `X-Audit-Log-Reason: {URL-encoded reason}` (512 chars max)

### 6.2 Relevant Audit Log Events After Transition

| Event | Action Type | When Triggered |
|---|---|---|
| `ROLE_UPDATE` | 31 | Bot role permissions changed |
| `ROLE_CREATE` | 30 | New role created for least-privilege |
| `MEMBER_ROLE_UPDATE` | 25 | Bot's assigned role changed |
| `CHANNEL_OVERWRITE_CREATE` | 112 | Channel permission overwrites for bot |
| `CHANNEL_OVERWRITE_UPDATE` | 113 | Bot's channel overwrites modified |
| `BOT_ADD` | 28 | Bot added to guild (re-invite) |

### 6.3 Monitoring Recommendations

1. **Weekly audit log review** for unexpected permission changes on the bot's role
2. **Alert on `ROLE_UPDATE`** where the target role name contains "Guinevere" or the bot's role
3. **Use `guildAuditLogEntryCreate` gateway event** (requires `GuildModeration` intent) for real-time monitoring

---

## 7. Private Single-User Server Caveat

### 7.1 Risk Mitigation Factors

Faiz's Discord server is a **private single-user server** — Faiz is the sole member. This fundamentally changes the risk profile:

| Risk | Multi-user server | Private single-user server |
|---|---|---|
| Server takeover via compromised bot | Catastrophic: all members affected | Annoying: only one user's single-server experience disrupted |
| Unauthorized member actions | High: many potential attackers | None: no other members exist |
| Data exposure via message reading | All members' messages affected | Only Faiz's own messages exposed |
| Reputation/social damage | High | Minimal — no community to damage |
| Recovery complexity | Complex: re-invite members, restore channels | Trivial: recreate one server |

### 7.2 When Administrator Is Less Risky

The private single-user context makes Administrator **less risky** but **still not best practice**:

- **Token compromise is the remaining threat**: If the bot's runtime environment is compromised, Administrator still grants full server access regardless of user count
- **Future-proofing**: If the server is ever opened to other users, Administrator becomes a critical vulnerability
- **Discipline**: Maintaining least-privilege even in low-risk environments builds security habits that transfer to higher-risk contexts

### 7.3 Discord's Position on Private Bots

From [Discord OAuth2 docs](https://docs.discord.com/developers/topics/oauth2#bot-users):

> "If your bot is super specific to your private clubhouse, or you just don't like sharing, you can leave the `Public Bot` option unchecked in your application's settings."

Discord's Developer Policy applies regardless of server size — the recommendation to request minimal permissions is unconditional.

---

## 8. Recommendation

### Decision: **REDUCE** — Transition from Administrator to least-privilege permissions

| Criterion | Verdict |
|---|---|
| Is Administrator technically justified? | **No** — no current or planned Guinevere function requires `ADMINISTRATOR` |
| Does the private single-user server mitigate risk? | **Partially** — reduces blast radius but does not eliminate token compromise risk |
| Is transition practical? | **Yes** — phased plan allows parallel testing before removal |
| Is there a timeline pressure? | **No** — can be done incrementally alongside P2-007 |
| Does P2-007 require elevated permissions? | **Possibly** — `MANAGE_ROLES` and `MANAGE_CHANNELS` may be needed; these are elevated but far narrower than Administrator |

### Recommended Permission Set for Implementation

For the initial least-privilege transition (core AI companion features):

| Permission | Value |
|---|---|
| `VIEW_CHANNEL` | 1,024 |
| `SEND_MESSAGES` | 2,048 |
| `EMBED_LINKS` | 16,384 |
| `ATTACH_FILES` | 32,768 |
| `READ_MESSAGE_HISTORY` | 65,536 |
| `ADD_REACTIONS` | 64 |
| `USE_APPLICATION_COMMANDS` | 2,147,483,648 |
| `VIEW_AUDIT_LOG` | 128 |
| **Core integer** | **2,147,599,472** |

Add per P2-007 requirements (as needed, not pre-emptively):

| Permission | Value | When |
|---|---|---|
| `MANAGE_ROLES` | 268,435,456 | If permission overwrites needed |
| `MANAGE_CHANNELS` | 16 | If channel creation/editing needed |
| `MODERATE_MEMBERS` | 1,099,511,627,776 | If timeout features added |
| `MANAGE_MESSAGES` | 8,192 | If message deletion needed |

### Risks of Keeping Administrator

Even in a private single-user server, retaining Administrator means:

1. **No defense-in-depth**: A single vulnerability in the bot process exposes the entire server
2. **No channel-level isolation**: Cannot restrict the bot to specific channels for testing
3. **Habit formation**: Normalizes over-privilege that will carry over if the server expands
4. **Token compromise = full server loss**: No layers of permission to slow down an attacker

---

## 9. References

### Official Discord Documentation
- [Permissions Reference](https://docs.discord.com/developers/topics/permissions) — Full bitwise permission flag table
- [OAuth2 & Permissions Guide](https://docs.discord.com/developers/platform/oauth2-and-permissions) — Scopes and permissions overview
- [OAuth2 Documentation](https://docs.discord.com/developers/topics/oauth2) — Bot authorization flow
- [Audit Log Resource](https://docs.discord.com/developers/resources/audit-log) — Audit log API
- [Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy) — Discord's developer rules
- [Community: Permissions on Discord](https://discord.com/community/permissions-on-discord-discord) — Community guidance on Administrator

### Security & Best Practices
- [Discord Bot Security Risks (2026)](https://xoe.gg/blog/discord-bot-security-risks-protect-server) — Industry security recommendations
- [Discord Bot Permission Questions (2026)](https://www.vecosys.com/questions-before-adding-discord-bot-2026/) — Permission audit checklist
- [Discord Security Checklist (2026)](https://xoe.gg/blog/discord-community-security-checklist) — Monthly audit recommendations
- [GitHub Discussion #4864](https://github.com/discord/discord-api-docs/discussions/4864) — Community debate on Administrator for bots

### Code & Tools
- [discord.py permission checking example](https://errormedic.com/api/discord-api/discord-api-rate-limit-401-403-timeout-errors-complete-troubleshooting-guide) — Programmatic verification
- [Discord Permission Calculator](https://xgamingserver.com/tools/discord-bot/permissions) — Bit-mask builder
- [discord-api-types PermissionFlagsBits](https://discord.js.org/docs/packages/discord-api-types/main/PermissionFlagsBits:Variable) — TypeScript constants

---

## Appendix A: Permission Integer Quick Reference

| Permission Set | Integer | Hex |
|---|---|---|
| Administrator | `8` | `0x8` |
| Core AI (chat + commands + reactions) | `2,147,599,472` | `0x8000F870` |
| Core + moderation (timeout) | `1,099,513,739,030,288` | `0x10000008000F870` |
| Core + roles + channels (P2-007) | `2,416,034,960` | `0x9000F870` |
| Full (all listed in §3.2) | `1,099,512,041,402,041` | `0x10000108010F871` |

---

*End of report. Next action: P2 reviewer to decide on APPROVE/REDUCE/DEFER for Administrator transition.*