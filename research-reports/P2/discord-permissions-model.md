# Discord Permission Model — Category/Channel Setup for Private Single-User Bot Server

> **Purpose**: Informing P2-005, P2-006 (category/channel creation) and planning for P2-007 (permission hardening).
> **Context**: Bot currently has `Administrator` permission (by Faiz choice for private server). Future P2-009/P2-007 may remove admin.

---

## 1. Discord Permission Hierarchy (Official)

Permissions are calculated per-user via an 8-step precedence ladder:

| Step | Scope | Rule |
|------|-------|------|
| 1 | Guild | Base permissions given to `@everyone` |
| 2 | Guild | Permissions allowed by the user's roles (OR'd together) |
| 3 | Channel | Overwrites that **deny** permissions for `@everyone` |
| 4 | Channel | Overwrites that **allow** permissions for `@everyone` |
| 5 | Channel | Overwrites that **deny** permissions for specific roles |
| 6 | Channel | Overwrites that **allow** permissions for specific roles |
| 7 | Channel | Member-specific overwrites that **deny** |
| 8 | Channel | Member-specific overwrites that **allow** |

**Key insight**: Deny beats allow at the same level; allow at a higher step (#6) beats deny at a lower step (#5). The `ADMINISTRATOR` permission short-circuits all calculation and grants everything.

**Source**: [Discord Permissions Documentation](https://docs.discord.com/developers/topics/permissions)

---

## 2. Category ↔ Channel Permission Syncing

Discord does **not** use inheritance between categories and channels. Instead it uses **Permission Syncing**:

- **Synced**: A child channel whose permission overwrites are identical to its parent category is visually and technically "synced".
- **Desynced**: Any edit to a child channel's overwrites causes it to desync. It will no longer receive updates from the parent category.
- **Admin bypass**: `ADMINISTRATOR` skips all overwrite checks entirely. If the bot has admin, permission syncing is irrelevant — it can always see/manage.
- **Visual indicator**: Synced channels show a grey "sync" icon in the Discord UI; desynced ones show it as independent.

**Practical implication for P2-005/P2-006**: When creating a channel under a category with `overwrites`, the channel is automatically desynced (because its overwrites differ from the category). This is the correct behavior for private channels. If you create a channel WITHOUT passing `overwrites` but WITH a `category`, it will sync to the category's permissions.

**Source**: [Discord Permissions — Permission Syncing](https://docs.discord.com/developers/topics/permissions#permission-syncing)

---

## 3. Private Server Visibility (@everyone Defaults)

In a private single-user server:

- The `@everyone` role has guild-level permissions controlled by the server owner.
- By default, `@everyone` can see channels unless explicitly denied.
- To make a channel **private** (only visible to the bot/owner), you **deny** `VIEW_CHANNEL` (or `read_messages` equiv) for `@everyone` and allow it for specific roles/members.

**Common pattern** (from real codebases — Sir-Robin, Modmail, SevenBot, Pycord docs):

```python
overwrites = {
    guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Hide from everyone
    guild.me: discord.PermissionOverwrite(read_messages=True),             # Show to bot
}
```

**Source**: [discord.py API — create_text_channel](https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.create_text_channel)

---

## 4. Permission Requirements for Channel/Category Operations

### 4.1 Bot Permissions Needed

| Operation | Required Permission | Notes |
|-----------|-------------------|-------|
| Create text channel | `MANAGE_CHANNELS` | Also needs `VIEW_CHANNEL` for the category if under one |
| Create voice channel | `MANAGE_CHANNELS` | |
| Create category | `MANAGE_CHANNELS` | |
| Rename channel/category | `MANAGE_CHANNELS` | |
| Delete channel/category | `MANAGE_CHANNELS` | Category deletion also fires deletion of child channels |
| Edit channel position | `MANAGE_CHANNELS` | |
| Set permission overwrites | `MANAGE_ROLES` | Per-channel: requires `MANAGE_ROLES` |
| Modify role permissions | `MANAGE_ROLES` | Bot can only grant permissions it holds |
| Move channel to/from category | `MANAGE_CHANNELS` | |
| Sync permissions with category | `MANAGE_CHANNELS` | Via `channel.edit(sync_permissions=True)` |

**Source**: [Discord Server and Channel Management](https://docs.discord.com/developers/platform/server-and-channel-management)

### 4.2 Current Bot State (Administrator)

With `ADMINISTRATOR` permission:
- All operations above are **automatically granted**.
- Permission overwrites are **completely bypassed** — the bot sees all channels, can create/edit/delete anything.
- Role hierarchy still applies for role management (can only manage roles lower than its highest role).

**Caveat**: If doing P2-007 hardening that removes `ADMINISTRATOR`, the bot will need both `MANAGE_CHANNELS` and `MANAGE_ROLES` to create categories/channels with custom overwrites.

---

## 5. discord.py API for Permission Management

### 5.1 `PermissionOverwrite` Class

All attributes are `Optional[bool]` — `True` to allow, `False` to deny, `None` to inherit/no change.

Key attributes relevant to P2-005/P2-006:

| Attribute | Permission Flag | Effect |
|-----------|----------------|--------|
| `read_messages` | `VIEW_CHANNEL` | Can see channel / read messages |
| `send_messages` | `SEND_MESSAGES` | Can send messages |
| `manage_channels` | `MANAGE_CHANNELS` | Can edit/delete channel |
| `manage_roles` | `MANAGE_ROLES` | Can manage permissions |
| `manage_messages` | `MANAGE_MESSAGES` | Can delete others' messages |
| `read_message_history` | `READ_MESSAGE_HISTORY` | Can read history |
| `connect` | `CONNECT` | Can join voice channel |
| `speak` | `SPEAK` | Can speak in voice channel |
| `send_messages_in_threads` | `SEND_MESSAGES_IN_THREADS` | Can send in threads |

**Source**: [discord.py permissions.py — PermissionOverwrite](https://github.com/Rapptz/discord.py/blob/108e9abb/discord/permissions.py)

### 5.2 Creating Categories with Overwrites

```python
overwrites = {
    guild.default_role: discord.PermissionOverwrite(read_messages=False),
    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    some_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
}
category = await guild.create_category_channel("Category Name", overwrites=overwrites)
```

**Source**: [discord.py discussion #6888 — category overwrite example](https://github.com/Rapptz/discord.py/discussions/6888)

### 5.3 Creating Channels under Categories

```python
# Will sync to category permissions if no overwrites passed
channel = await guild.create_text_channel("general", category=category)

# Will desync from category due to custom overwrites
overwrites = {
    guild.default_role: discord.PermissionOverwrite(read_messages=False),
    guild.me: discord.PermissionOverwrite(read_messages=True),
    target_member: discord.PermissionOverwrite(read_messages=True),
}
channel = await guild.create_text_channel("private", category=category, overwrites=overwrites)
```

**Important note**: The keyword is `overwrites` (plural), NOT `overwrite` (singular). A common mistake in discord.py.

**Source**: [discord.py API — Guild.create_text_channel](https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.create_text_channel)

### 5.4 Editing Permissions on Existing Channels

```python
# Method 1: set_permissions (replaces existing overwrite for that target)
await channel.set_permissions(member, read_messages=True, send_messages=False)

# Method 2: Using PermissionOverwrite object
overwrite = discord.PermissionOverwrite()
overwrite.send_messages = False
overwrite.read_messages = True
await channel.set_permissions(member, overwrite=overwrite)

# Method 3: Delete overwrite (reset to inherit)
await channel.set_permissions(member, overwrite=None)

# Method 4: Edit channel's entire overwrite dict
overwrites = channel.overwrites  # Get current dict
overwrites[member] = discord.PermissionOverwrite(read_messages=True)
await channel.edit(overwrites=overwrites)

# Sync/unsync from category
await channel.edit(sync_permissions=True)   # Re-sync to category
await channel.edit(sync_permissions=False)  # Desync
```

**Source**: [discord.py API — GuildChannel.set_permissions](https://discordpy.readthedocs.io/en/stable/api.html#discord.GuildChannel.set_permissions)

---

## 6. Private Channel Pattern (for Single-User Bot Server)

For a private setup where only the bot and server owner (Faiz) can see channels:

```python
async def create_private_category(guild, name, additional_roles=None):
    """Create a category visible only to bot owner and specified roles."""
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True),
    }
    # If there's a known owner/user role, add it
    if additional_roles:
        for role in additional_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True)

    return await guild.create_category_channel(name, overwrites=overwrites)


async def create_private_channel(guild_or_category, name, category, target_member=None):
    """Create a channel under a private category."""
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if target_member:
        overwrites[target_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    return await category.create_text_channel(name, overwrites=overwrites)
```

---

## 7. Verification Strategy (Without Exposing Sensitive Data)

To verify permissions without leaking tokens or sensitive state:

1. **Check `guild.me.guild_permissions`** — query the bot's own permission set at the guild level.
   ```python
   perms = guild.me.guild_permissions
   can_create = perms.manage_channels       # True if bot can manage channels
   can_manage_roles = perms.manage_roles    # True if bot can set overwrites
   is_admin = perms.administrator           # True if bot has admin
   ```

2. **Check channel-level permissions** for the bot:
   ```python
   perms_in_channel = channel.permissions_for(guild.me)
   ```

3. **Check channel overwrites** (for audit/reporting):
   ```python
   overwrites = channel.overwrites          # dict mapping target → PermissionOverwrite
   target = guild.default_role
   ow = overwrites.get(target)              # PermissionOverwrite or None
   can_see = ow.read_messages if ow else None  # True/False/None
   ```

4. **Log only permission names, not tokens or IDs.** Never log the bot token, OAuth2 secret, or raw `guild.me` object dump.

5. **For CI/testing**: Use a non-destructive dry-run that reads `guild.me.guild_permissions` and `channel.overwrites` on target channels, writes to evidence file without mutating server state.

---

## 8. Recommendations for P2-005/P2-006 (Basic Creation)

| Aspect | Recommendation |
|--------|---------------|
| Bot permission | Use existing `Administrator` for P2-005/P2-006; no change needed |
| Category creation | Use `create_category_channel(name, overwrites=...)` with `@everyone` DENY `read_messages` |
| Channel creation | Use `category.create_text_channel(name, overwrites=...)` with bot + owner explicit ALLOW |
| Permission pattern | Mirror the proven `{@everyone: DENY read, bot: ALLOW read}` pattern |
| Sync behavior | Channels will be desynced from category by design (different overwrites) |
| Naming | Use lowercase-kebab or descriptive naming scheme |
| Error handling | Catch `discord.Forbidden` (insufficient permissions) and `discord.HTTPException` |
| Audit logging | Pass `reason="Guinevere setup"` for audit log visibility |

## 9. Future Considerations for P2-007 (Permission Hardening)

| Aspect | Risk / Change |
|--------|--------------|
| Remove `Administrator` | Bot must have explicit `MANAGE_CHANNELS` + `MANAGE_ROLES` |
| Scope creep | Do not conflate P2-007 hardening with P2-005/P2-006 creation |
| Role hierarchy | Bot's highest role must be above any roles it manages |
| Minimum permissions | Invite link in OAuth2 should request `manage_channels` + `manage_roles` + `view_channel` + `send_messages` |
| Verification | After removing admin, test `guild.me.guild_permissions` before any create/edit operation |
| Owner access | Ensure server owner (Faiz) has a role or member-specific overwrite for all private channels |

---

## References

1. [Discord Permissions — Official Docs](https://docs.discord.com/developers/topics/permissions) — Hierarchy, overwrites, syncing, bitwise flags
2. [Discord Server and Channel Management](https://docs.discord.com/developers/platform/server-and-channel-management) — Required permissions overview
3. [discord.py API Reference — Guild.create_text_channel](https://discordpy.readthedocs.io/en/stable/api.html#discord.Guild.create_text_channel) — Signature, overwrites, examples
4. [discord.py API Reference — GuildChannel.set_permissions](https://discordpy.readthedocs.io/en/stable/api.html#discord.GuildChannel.set_permissions) — Overwrite management
5. [discord.py permissions.py — PermissionOverwrite](https://github.com/Rapptz/discord.py/blob/108e9abb/discord/permissions.py) — All available attributes
6. [discord.py Guild.create_category_channel source](https://github.com/Rapptz/discord.py/blob/108e9abb/discord/guild.py) — Implementation details
7. [Real-world example: python-discord/sir-robin](https://github.com/python-discord/sir-robin/blob/main/bot/exts/code_jams/_creation_utils.py) — Category with `@everyone: DENY read_messages`
8. [Real-world example: SevenBot ticket system](https://github.com/SevenBot-dev/SevenBot/blob/main/cogs/ticket.py) — Category + channel creation with overwrites
9. [Real-world example: modmail-dev/Modmail](https://github.com/modmail-dev/Modmail/blob/master/cogs/modmail.py) — Private category with role-based access
10. [discord.py Discussion #6888](https://github.com/Rapptz/discord.py/discussions/6888) — Sync behavior, overwrite creation tips