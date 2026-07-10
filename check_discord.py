#!/usr/bin/env python3
"""Check Discord guild channels and bot permissions."""

import os
import discord
import asyncio


async def check_guild():
    # Try to get token from env file
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

            # Bot member permissions
            member = guild.get_member(client.user.id)
            if member:
                guild_perms = member.guild_permissions
                print(f"Bot permissions:")
                print(f"  Administrator: {guild_perms.administrator}")
                print(f"  Manage Channels: {guild_perms.manage_channels}")
                print(f"  Manage Guild: {guild_perms.manage_guild}")

            # List current text channels
            print(f"\nCurrent text channels:")
            for ch in sorted(guild.text_channels, key=lambda c: c.position):
                print(f"  #{ch.name} (ID: {ch.id}, pos: {ch.position})")

            print(f"\nCurrent voice channels:")
            for ch in guild.voice_channels:
                print(f"  {ch.name} (ID: {ch.id})")

            print(f"\nCurrent categories:")
            for cat in guild.categories:
                print(f"  {cat.name} (ID: {cat.id})")

        await client.close()

    await client.start(token)


asyncio.run(check_guild())
