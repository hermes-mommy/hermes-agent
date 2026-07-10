#!/usr/bin/env python3
"""Create Discord channels for Phase B — simplified, one at a time."""

import os
import sys
import discord
import asyncio

env_path = "/home/guinevere/p24-port/.env.discord"
token = None
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("DISCORD_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip()
            break

intents = discord.Intents.default()
intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    for guild in client.guilds:
        print(f"Connected to guild: {guild.name} (ID: {guild.id})")
        existing = {ch.name: ch for ch in guild.channels}

        # Map categories
        categories = {cat.name: cat for cat in guild.categories}
        print(f"Available categories: {list(categories.keys())}")

        channels_to_create = [
            ("general", "👑 Throne", "General conversation and casual chat"),
            ("commands-hq", "👑 Throne", "Slash command center"),
            ("media-gallery", "👑 Throne", "Share images, art, and media"),
            ("notifications", "📊 Surveillance", "System alerts and notifications"),
            ("admin-internal", "🔧 Projects", "Faiz-only admin panel"),
        ]

        for name, cat_name, topic in channels_to_create:
            if name in existing:
                ch = existing[name]
                print(f"SKIP: #{name} (ID: {ch.id}) already exists")
                continue

            category = categories.get(cat_name)
            if category:
                print(f"Creating #{name} in category '{cat_name}'...")
            else:
                print(f"Creating #{name} (no category '{cat_name}' found)...")

            try:
                ch = await guild.create_text_channel(
                    name=name,
                    category=category,
                    topic=topic,
                    reason="Phase B channel refactor"
                )
                print(f"OK: #{name} (ID: {ch.id})")
            except Exception as e:
                print(f"ERROR: #{name}: {e}")

        # Print env vars for .env.discord
        print("\n=== Channel IDs for .env.discord ===")
        existing = {ch.name: ch for ch in guild.channels}
        for name, _, _ in channels_to_create:
            ch = existing.get(name)
            if ch:
                env_key = f"DISCORD_CHANNEL_{name.upper().replace('-', '_')}"
                print(f"{env_key}={ch.id}")

    await client.close()

print("Starting Discord client...")
sys.stdout.flush()
asyncio.run(client.start(token))
print("Done.")
