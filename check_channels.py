#!/usr/bin/env python3
"""Check if target channels exist on Discord."""

import os
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
        existing = {ch.name: ch for ch in guild.channels}
        targets = ["general", "commands-hq", "media-gallery", "notifications", "admin-internal"]
        for t in targets:
            if t in existing:
                print(f"EXISTS: #{t} (ID: {existing[t].id})")
            else:
                print(f"MISSING: #{t}")
    await client.close()

asyncio.run(client.start(token))
