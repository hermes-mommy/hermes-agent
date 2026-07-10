#!/usr/bin/env python3
"""Create Discord channels for Phase B layout.

Channels per plan:
  - #general — general conversation (👑 Throne)
  - #commands-hq — slash command center (👑 Throne)
  - #media-gallery — images, art, media (👑 Throne)
  - #notifications — system alerts (📊 Surveillance)
  - #admin-internal — Faiz-only admin (🔧 Projects)

Run: python3 setup_channels.py
"""

import os
import discord
import asyncio


# Channel definitions: (name, category_name, topic, is_nsfw, slowmode_delay)
CHANNEL_DEFS = [
    ("general", "👑 Throne", "General conversation and casual chat", False, 0),
    ("commands-hq", "👑 Throne", "Slash command center — all bot commands available here", False, 0),
    ("media-gallery", "👑 Throne", "Share images, art, and media", False, 0),
    ("notifications", "📊 Surveillance", "System alerts, SEV notifications, and automated status updates", False, 0),
    ("admin-internal", "🔧 Projects", "Faiz-only: administrative panel, system configuration, finance, and integration controls", False, 0),
]

# Category permission overwrites for private channels
PRIVATE_CHANNELS = {"admin-internal"}


def make_private_overwrites(guild, bot_member):
    """Create permission overwrites for private channels (admin-internal is Faiz-only)."""
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
    }
    # Also find Faiz (guild owner) and give access
    owner = guild.owner
    if owner:
        overwrites[owner] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True, manage_messages=True,
            manage_channels=True
        )
    return overwrites


async def setup_channels():
    env_path = "/home/guinevere/p24-port/.env.discord"
    token = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        print("ERROR: Could not find DISCORD_BOT_TOKEN")
        return

    intents = discord.Intents.default()
    intents.all()

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Bot: {client.user} (ID: {client.user.id})")

        for guild in client.guilds:
            print(f"\n=== Guild: {guild.name} (ID: {guild.id}) ===")

            # Index existing channels by name
            existing = {ch.name: ch for ch in guild.channels}

            # Index categories by name
            categories = {cat.name: cat for cat in guild.categories}

            bot_member = guild.get_member(client.user.id)

            created = []
            skipped = []

            for name, cat_name, topic, nsfw, slowmode in CHANNEL_DEFS:
                if name in existing:
                    ch = existing[name]
                    skipped.append(f"  #{name} (ID: {ch.id}) — already exists")
                    continue

                # Find or create category
                category = categories.get(cat_name)
                if not category:
                    print(f"  [WARN] Category '{cat_name}' not found, creating at guild top")
                
                overwrites = None
                if name in PRIVATE_CHANNELS:
                    overwrites = make_private_overwrites(guild, bot_member)

                try:
                    ch = await guild.create_text_channel(
                        name=name,
                        category=category,
                        topic=topic,
                        nsfw=nsfw,
                        slowmode_delay=slowmode,
                        overwrites=overwrites,
                        reason="Phase B — Discord channel refactor (consciousness loop replan)",
                    )
                    created.append(f"  #{name} (ID: {ch.id}) — created in '{cat_name}'")
                    print(f"  CREATED: #{name} (ID: {ch.id}) in {cat_name}")
                except discord.Forbidden:
                    print(f"  FORBIDDEN: Could not create #{name}")
                except discord.HTTPException as e:
                    print(f"  ERROR: Could not create #{name}: {e}")

            print(f"\n=== Summary ===")
            for s in skipped:
                print(s)
            for c in created:
                print(c)

            print(f"\n=== Channel IDs for .env.discord ===")
            for name, _, _, _, _ in CHANNEL_DEFS:
                ch = existing.get(name) or discord.utils.get(guild.text_channels, name=name)
                if ch:
                    env_key = f"DISCORD_CHANNEL_{name.upper().replace('-', '_')}"
                    print(f"{env_key}={ch.id}")

        await client.close()

    await client.start(token)


asyncio.run(setup_channels())
