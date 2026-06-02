# Discord Channel Permission Overwrites & Role Hierarchy — Research Report

**Task**: P2-007 — Research channel permission overwrites & role hierarchy best practices  
**Date**: 2026-06-01  
**Sources**: Official Discord API docs, discord.py docs, GitHub real-world examples, community knowledge  
**Scope**: Guinevere private guild (ID 1510876414671323206); bot currently has Administrator; P2-007 needs channel permissions for Faiz read access, bot write access, evidence-write-only channels.

---

## Table of Contents

1. [Permission Hierarchy (8-Layer Model)](#1-permission-hierarchy-8-layer-model)
2. [Permission Syncing (Category ↔ Child)](#2-permission-syncing-category--child)
3. [PermissionOverwrite in discord.py](#3-permissionoverwrite-in-discordpy)
4. [Setting Overwrites: API Methods](#4-setting-overwrites-api-methods)
5. [Category-Level Permission Patterns](#5-category-level-permission-patterns)
6. [Administrator Caveats](#6-administrator-caveats)
7. [Evidence Write-Only Channels — Feasibility & Pattern](#7-evidence-write-only-channels--feasibility--pattern)
8. [Manage Roles & Manage Channels Needs](#8-manage-roles--manage-channels-needs)
9. [Role Hierarchy & Bot Constraints](#9-role-hierarchy--bot-constraints)
10. [Verification Methods](#10-verification-methods)
11. [Recommended Pattern for P2-007](#11-recommended-pattern-for-p2-007)
12. [References](#12-references)

---

## 1. Permission Hierarchy (8-Layer Model)

Discord resolves a user's effective permissions in a channel through **exactly 8 layers**, applied strictly in this order:

| Layer | Scope | What Applies |
|-------|-------|-------------|
| 1 | Guild | `@everyone` base permissions (guild-level role) |
| 2 | Guild | Permissions **allowed** by all of user's roles (bitwise OR) |
| 3 | Channel | Overwrites that **deny** permissions for `@everyone` |
| 4 | Channel | Overwrites that **allow** permissions for `@everyone` |
| 5 | Channel | Overwrites that **deny** permissions for specific roles |
| 6 | Channel | Overwrites that **allow** permissions for specific roles |
| 7 | Channel | **Member-specific** overwrites that **deny** permissions |
| 8 | Channel | **Member-specific** overwrites that **allow** permissions |

**Critical rule**: Permissions do NOT obey role hierarchy for resolution. A `deny` on a higher-positioned role does NOT override an `allow` on a lower-positioned role. **Any allow at any layer wins over any deny at any lower layer** (except layer 3 `@everyone` deny which is overridden by layer 4 `@everyone` allow).

From [Discord Permissions docs](https://docs.discord.com/developers/topics/permissions):

> Otherwise, permissions do not obey the role hierarchy. For example, a user has two roles: A and B. A denies the `VIEW_CHANNEL` permission on a #coolstuff channel. B allows the `VIEW_CHANNEL` permission on the same #coolstuff channel. The user would ultimately be able to view the #coolstuff channel, regardless of the role positions.

**Implication for P2-007**: When setting overwrites, **deny `@everyone`** at the channel level first (layer 3), then **allow specific roles/members** (layers 6/8). This is the standard "deny-by-default, allow-by-exception" pattern.

---

## 2. Permission Syncing (Category ↔ Child)

From the [official Discord docs](https://docs.discord.com/developers/topics/permissions):

> If a child channel has the same permissions and overwrites (or lack thereof) as its parent category, the channel is considered "synced" to the category.
>
> - Any further changes to a **parent category** will be reflected in its synced child channels.
> - Any further changes to a **child channel** will cause it to become de-synced from its parent category, and its permissions will no longer change with changes to its parent category.

### discord.py API for Sync

| Method | Behavior |
|--------|----------|
| `channel.edit(sync_permissions=True)` | Syncs channel overwrites to match parent category |
| `channel.edit(category=new_category, lock_permissions=True)` | Move to category + sync |
| `category_chanel.create_text_channel(name, overwrites=dict)` | Creates desynced by default if `overwrites` provided |
| `category_chanel.create_text_channel(name)` | Creates synced by default (inherits category overwrites) |

**Key**: When you pass `overwrites=` to `create_text_channel`, the channel is created **de-synced** from the parent category. This is what P2-007 wants — explicit overwrites that differ from the category.

### Checking Sync State

- In discord.py: `channel.permissions_synced` (bool) — `True` if channel overwrites match the category.
- In API: Not directly exposed; compare `permission_overwrites` manually.

---

## 3. PermissionOverwrite in discord.py

### Class: `discord.PermissionOverwrite`

Docs: https://discordpy.readthedocs.io/en/stable/api.html#permissionoverwrite

A `PermissionOverwrite` represents channel-specific permissions. Unlike `Permissions`, **all values default to `None`** (inherit/neutral), not `False`.

```python
overwrite = discord.PermissionOverwrite()
overwrite.view_channel = True      # Explicitly allow
overwrite.send_messages = False    # Explicitly deny
# Unset fields remain None → inherit from guild/role level
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `PermissionOverwrite(**kwargs)` | Create with explicit True/False per permission |
| `PermissionOverwrite.from_pair(allow, deny)` | Create from two `Permissions` bitfields |
| `overwrite.pair()` | Returns `(allow, deny)` tuple of `Permissions` objects |
| `overwrite.is_empty()` | True if all values are None |
| `overwrite.update(**kwargs)` | Update multiple fields at once |

### All Supported Permission Flags (text-relevant)

| Flag | Hex | Type |
|------|-----|------|
| `view_channel` | `0x400` | T, V, S |
| `send_messages` | `0x800` | T, V, S |
| `send_tts_messages` | `0x1000` | T, V, S |
| `manage_messages` | `0x2000` | T, V, S |
| `embed_links` | `0x4000` | T, V, S |
| `attach_files` | `0x8000` | T, V, S |
| `read_message_history` | `0x10000` | T, V, S |
| `mention_everyone` | `0x20000` | T, V, S |
| `use_external_emojis` | `0x40000` | T, V, S |
| `manage_channels` | `0x10` | T, V, S |
| `manage_roles` | `0x10000000` | T, V, S |
| `manage_webhooks` | `0x20000000` | T, V, S |
| `read_messages` | `0x400` | Alias for `view_channel` |
| `send_messages_in_threads` | `0x400000000000` | T |
| `create_public_threads` | `0x80000000000` | T |
| `create_private_threads` | `0x100000000000` | T |

> **Note**: `read_messages` is an alias for `view_channel` in discord.py.

---

## 4. Setting Overwrites: API Methods

### Method A: `channel.set_permissions(target, overwrite=..., reason=...)`

Replaces the overwrite for a single target (role or member).

```python
# Allow a member to view and send
await channel.set_permissions(
    member,
    overwrite=discord.PermissionOverwrite(view_channel=True, send_messages=True),
    reason="P2-007: Faiz read access"
)

# Deny @everyone from viewing
await channel.set_permissions(
    guild.default_role,
    overwrite=discord.PermissionOverwrite(view_channel=False),
    reason="P2-007: Restrict evidence channel"
)

# Delete an overwrite entirely
await channel.set_permissions(role, overwrite=None)
```

**Keyword shortcut** (avoids creating PermissionOverwrite object):

```python
await channel.set_permissions(member, read_messages=True, send_messages=False)
```

### Method B: `channel.edit(overwrites=dict)`

Replaces **all** overwrites on the channel at once. Preferred when creating or bulk-setting.

```python
overwrites = {
    guild.default_role: discord.PermissionOverwrite(view_channel=False),
    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    faiz_member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    evidence_bot_role: discord.PermissionOverwrite(send_messages=True, view_channel=False),  # write-only attempt
}
await channel.edit(overwrites=overwrites, reason="P2-007: Channel permission setup")
```

### Method C: During channel creation

```python
category = discord.utils.get(guild.categories, name="Guinevere Evidence")
channel = await category.create_text_channel(
    "evidence-logs",
    overwrites={
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        faiz_member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    },
    reason="P2-007: Evidence channel"
)
```

> ⚠️ When using `overwrites=` during creation, the channel is **automatically desynced** from the category. No need to call `sync_permissions=False`.

---

## 5. Category-Level Permission Patterns

For P2-007, the recommended architecture is:

```
Category: "Guinevere Evidence" (private)
├── #evidence-read-write        (Faiz + bot: read+write)
├── #evidence-write-only        (bot only: write, no read)
└── #evidence-admin             (Faiz only: full access)
```

### Pattern: Set base denials at category level, overwrite at channel level

**Category overwrites** (deny-by-default):

```python
category_overwrites = {
    guild.default_role: discord.PermissionOverwrite(view_channel=False),
    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
}
category = await guild.create_category(
    "Guinevere Evidence",
    overwrites=category_overwrites,
    reason="P2-007: Evidence category"
)
```

Then create child channels with **additional** overwrites that layer on top:

```python
# Faiz-specific read channel
faiz_overwrites = dict(category_overwrites)  # copy base
faiz_overwrites[faiz_member] = discord.PermissionOverwrite(
    view_channel=True, send_messages=True, read_message_history=True
)
faiz_channel = await category.create_text_channel(
    "evidence-read-write",
    overwrites=faiz_overwrites
)
```

---

## 6. Administrator Caveats

### Administrator bypasses ALL overwrites

From the [Discord docs](https://docs.discord.com/developers/topics/permissions):

> `ADMINISTRATOR` (`0x8`): Allows all permissions and bypasses channel permission overwrites.

The `compute_overwrites` pseudocode shows:

```python
def compute_overwrites(base_permissions, member, channel):
    if base_permissions & ADMINISTRATOR == ADMINISTRATOR:
        return ALL  # ← short-circuits everything
```

### What this means for P2-007:

| Scenario | Outcome |
|----------|---------|
| Bot has Administrator | Bot **can** read all channels regardless of overwrites |
| Faiz has Administrator | Faiz **can** read all channels regardless of overwrites |
| Guild Owner has Administrator (always) | Guild Owner **always** sees everything |
| Member has no Administrator | Overwrites apply as expected |

**Caveat for evidence write-only channels**: Since the bot currently has Administrator, it will **always** be able to read evidence channels even if overwrites deny `view_channel`. The write-only pattern only works for **non-Administrator** roles/bots.

### Administrator vs Hierarchy

> Granting the `Administrator` permission does not skip any hierarchical check!

Administrator bypasses permission checks but does NOT bypass role hierarchy checks (kicking, banning, role management, etc.).

---

## 7. Evidence Write-Only Channels — Feasibility & Pattern

### The Problem

A "true write-only" channel (can send messages but cannot read any messages) is **not fully possible** in Discord due to implicit permissions:

- If `VIEW_CHANNEL` is `False`, the channel is **invisible** and **cannot send messages** (implicit denial).
- If `VIEW_CHANNEL` is `True` but `READ_MESSAGE_HISTORY` is `False`, users can:
  - ✅ Send messages
  - ✅ See messages sent **while they are online and viewing the channel**
  - ❌ Read message history (messages sent before they opened Discord)
  - This is the **closest approximation** to "write-only"

From Discord community discussions ([source](https://support.discord.com/hc/en-us/community/posts/360031881552-Write-only-channel)):

> Read messages: true (if false you can NOT see channel)  
> Read message history: false  
> That is best way to set it up w/out a bot  
> Unfortunately anyone w/ permissions to channel will be able to see any message posted while they are connected until they fully close discord.

### Feasibility Matrix for "Write-Only"

| Permission Set | Behavior | Works for Evidence? |
|---------------|----------|-------------------|
| `view_channel=False, send_messages=True` | ❌ Cannot see channel, cannot send — API denies send | No |
| `view_channel=True, read_message_history=True` | Full read+write | No (not write-only) |
| `view_channel=True, read_message_history=False` | Can send, can see live messages but NOT history | **Partial — best available** |
| `view_channel=True, read_message_history=False, send_messages=True` | **Best approximation** of write-only | **Yes, with caveats** |

### Write-Only Caveats

1. **Administrator bypasses everything** — if bot has Admin (current state), it reads everything.
2. **Users online when message is sent can see it** in real-time.
3. **Users who open Discord after messages are sent cannot see them** (read_message_history=False).
4. **Audit log still records channel activity** accessible to users with `VIEW_AUDIT_LOG`.
5. **Discord API always includes last message preview** in channel list for users with `VIEW_CHANNEL`.

### Code Pattern for Evidence Write-Only (bot-only, no read)

Since the bot currently has **Administrator**, a "true write-only" for the bot is impossible — it will always be able to read. The write-only pattern works for **non-Admin** users:

```python
# Evidence write-only channel for restricted bot/role (non-Administrator)
write_only_overwrites = {
    guild.default_role: discord.PermissionOverwrite(view_channel=False),
    # The bot role (non-Admin): can send but cannot read history
    bot_role: discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=False,  # ← key: no history
        embed_links=True,
        attach_files=True,
    ),
    # Faiz (non-Admin): full read access to see what bot wrote
    faiz_member: discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
    ),
}
```

> ⚠️ **Recommendation**: For P2-007, if the bot needs to write evidence but not read it back via Discord, use **webhooks** instead (bot posts via webhook URL, does not need `view_channel`). Or accept that with Administrator, the bot can read but the **code** should simply not fetch/display channel content to users.

---

## 8. Manage Roles & Manage Channels Needs

### Permission Requirements for Channel Operations

From [Discord Channel docs](https://docs.discord.com/developers/resources/channel):

| Operation | Required Permission |
|-----------|-------------------|
| Create channel | `MANAGE_CHANNELS` |
| Edit channel (name, topic, position) | `MANAGE_CHANNELS` |
| Edit **permission overwrites** | `MANAGE_ROLES` |
| Delete channel | `MANAGE_CHANNELS` |
| Delete permission overwrite | `MANAGE_ROLES` |
| Move channel between categories | `MANAGE_CHANNELS` |

### Key Distinction

> If modifying permission overwrites, the `MANAGE_ROLES` permission is required. Only permissions your bot has in the guild or parent channel (if applicable) can be allowed/denied (unless your bot has a `MANAGE_ROLES` overwrite in the channel).

So:

- **`MANAGE_CHANNELS`** = create/edit/delete channels themselves
- **`MANAGE_ROLES`** = edit permission overwrites on channels

Since the bot currently has **Administrator** (which includes both), this is not a practical limitation for P2-007. However, if Administrator is removed later:

```python
# Minimal permission set for channel management
required_permissions = discord.Permissions(
    manage_channels=True,    # create/edit/delete channels
    manage_roles=True,       # edit permission overwrites
    view_channel=True,       # see channels
    send_messages=True,      # post messages
    read_message_history=True,
)
```

### Bot cannot grant permissions it doesn't have

> A bot can edit roles of a lower position than its highest role, but it can only grant permissions it has to those roles.

If the bot does NOT have `MANAGE_ROLES` in its **base** permissions but has it as a **channel overwrite**, it can still manage overwrites in that specific channel. This is the exception noted in the docs.

---

## 9. Role Hierarchy & Bot Constraints

### Role Position Rules

From [Discord Permissions docs](https://docs.discord.com/developers/topics/permissions):

- A bot can **grant roles** to other users that are **lower position** than its own highest role.
- A bot can **edit roles** of a **lower position** than its highest role, but can only grant permissions it has.
- A bot can **only sort roles** lower than its highest role.
- A bot can only **kick, ban, and edit nicknames** for users whose highest role is **lower** than the bot's highest role.

### Bot Role Positioning Strategy

For Guinevere, create a **bot role** positioned at the top of the role list (below the owner's roles but above all member roles):

```
Role Hierarchy (highest → lowest):
  1. @everyone (position 0)
  2. Guinevere Bot Role ← bot's highest role
  3. Faiz Role (if needed)
  4. Member Role
  5. Guest Role
```

The bot's highest role determines what it can manage. Since the bot currently has **Administrator**, role position isn't limiting, but for future non-Admin operation:

```python
# Set bot role position
bot_role = guild.get_role(BOT_ROLE_ID)
await bot_role.edit(position=len(guild.roles) - 2)  # second from top
```

### Permission Overwrite Management Regardless of Hierarchy

> A bot can manage overwrites for roles or users with higher roles than its own highest role.

This is an important exception: even if a user/role has a higher position than the bot's highest role, the bot can still **create/edit/delete overwrites** for them in a channel (as long as the bot has `MANAGE_ROLES`).

---

## 10. Verification Methods

### A. Check Channel Permissions Programmatically

```python
# Get computed permissions for a member in a channel
perms = channel.permissions_for(member)
print(f"Can view: {perms.view_channel}")
print(f"Can send: {perms.send_messages}")
print(f"Can read history: {perms.read_message_history}")
```

**Note from discord.py docs**: `permissions_for()` does NOT handle implicit permissions (e.g., denying `view_channel` implicitly denies `send_messages`). You must check `view_channel` first:

```python
# Proper verification pattern
perms = channel.permissions_for(member)
if not perms.view_channel:
    print("Member cannot access this channel at all")
    return
if perms.send_messages:
    print("Member can send messages")
```

### B. Check Current Overwrites

```python
# List all current overwrites
for target, overwrite in channel.overwrites.items():
    allow, deny = overwrite.pair()
    print(f"Target: {target.name} ({type(target).__name__})")
    print(f"  Allow: {allow.value}")
    print(f"  Deny: {deny.value}")
```

### C. Check Sync State

```python
print(f"Synced to category: {channel.permissions_synced}")
```

### D. API: Audit Log Verification

After making permission changes, you can verify via audit log:

```python
async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.overwrite_update):
    print(f"{entry.user} changed permissions on {entry.target}")
```

### E. Manual Verification (Discord Client)

1. Right-click channel → "Edit Channel" → "Permissions" tab
2. Check each role/member has expected green check (✓) or red X
3. Use "View As Role" feature to test from different perspectives

---

## 11. Recommended Pattern for P2-007

### Architecture

Based on the research, the recommended permission architecture for P2-007:

```
Category: "Guinevere Evidence" (hidden from @everyone)
├── #evidence-all              (Faiz + bot: read+write+history)
├── #bot-evidence              (bot: write-only w/ no history; Faiz: full read)
├── #faiz-private              (Faiz only: full access; bot: manage)
└── #evidence-admin            (Faiz only: all perms; bot: manage only)
```

### Category Setup

```python
async def setup_evidence_category(guild: discord.Guild, faiz: discord.Member):
    """Create or update evidence category with correct permissions."""
    
    bot_member = guild.me
    
    # Base: deny @everyone, allow bot
    category_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_roles=True,
            attach_files=True,
            embed_links=True,
        ),
    }
    
    category = await guild.create_category(
        "Guinevere Evidence",
        overwrites=category_overwrites,
        reason="P2-007: Evidence category setup"
    )
    
    # 1. Evidence All — Faiz + bot full access
    ch_all = await category.create_text_channel(
        "evidence-all",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True, embed_links=True,
            ),
            faiz: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True, embed_links=True,
            ),
        },
        topic="Full-access evidence channel for bot operations and Faiz review",
    )
    
    # 2. Bot Evidence — bot write-only (no history), Faiz full read
    ch_bot = await category.create_text_channel(
        "bot-evidence",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=False,  # ← write-only pattern
                attach_files=True,
                embed_links=True,
            ),
            faiz: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,  # Faiz can read everything
            ),
        },
        topic="Write-only evidence channel (bot posts, Faiz reads)",
    )
    
    # 3. Faiz Private — only Faiz reads/writes
    ch_faiz = await category.create_text_channel(
        "faiz-private",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                manage_channels=True,
                manage_roles=True,
            ),
            faiz: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_messages=True,
                attach_files=True, embed_links=True,
            ),
        },
        topic="Private channel for Faiz",
    )
    
    # 4. Evidence Admin — Faiz admin, bot manage only
    ch_admin = await category.create_text_channel(
        "evidence-admin",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                manage_channels=True,
                manage_roles=True,
                send_messages=True,
            ),
            faiz: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_messages=True,
                manage_channels=True, manage_roles=True,
                mention_everyone=True,
            ),
        },
        topic="Administrative evidence channel",
    )
    
    return {"category": category, "all": ch_all, "bot": ch_bot, "faiz": ch_faiz, "admin": ch_admin}
```

### Verification After Setup

```python
async def verify_channel_perms(channel: discord.TextChannel, label: str):
    """Print computed permissions for bot and key members."""
    print(f"\n=== {label} (synced: {channel.permissions_synced}) ===")
    for member in [channel.guild.me, faiz_member]:
        perms = channel.permissions_for(member)
        print(f"  {member.display_name}:")
        print(f"    view_channel={perms.view_channel}")
        print(f"    send_messages={perms.send_messages}")
        print(f"    read_message_history={perms.read_message_history}")
```

---

## 12. References

| Source | URL |
|--------|-----|
| Discord Permissions Docs | https://docs.discord.com/developers/topics/permissions |
| Discord Channel Resource | https://docs.discord.com/developers/resources/channel |
| Discord Server & Channel Mgmt | https://docs.discord.com/developers/platform/server-and-channel-management |
| discord.py PermissionOverwrite | https://discordpy.readthedocs.io/en/stable/api.html#permissionoverwrite |
| discord.py set_permissions | https://discordpy.readthedocs.io/en/stable/api.html#discord.abc.GuildChannel.set_permissions |
| discord.py GuildChannel.edit | https://discordpy.readthedocs.io/en/stable/api.html#discord.GuildChannel.edit |
| discord.py Channel.create_text_channel | https://discordpy.readthedocs.io/en/stable/api.html#discord.CategoryChannel.create_text_channel |
| discord.py permissions_for | https://discordpy.readthedocs.io/en/stable/api.html#discord.abc.GuildChannel.permissions_for |
| Discord Permissions (GitHub source) | https://github.com/discord/discord-api-docs/blob/master/docs/topics/permissions.md |
| Secret Channel Example (discord.py) | https://github.com/Rapptz/discord.py/blob/master/examples/secret.py |
| PermissionOverwrite in perm source | https://github.com/Rapptz/discord.py/blob/master/discord/permissions.py |
| Write-Only Channel (Discord Support) | https://support.discord.com/hc/en-us/community/posts/360031881552-Write-only-channel |

---

*Report prepared for P2-007 implementation. Parent will synthesize with local reports for final implementation.*