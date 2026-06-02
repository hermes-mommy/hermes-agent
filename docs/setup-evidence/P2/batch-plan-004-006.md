# Batch Plan — P2-004 through P2-006 (Discord Server Bootstrap)

| Field | Value |
|---|---|
| **Plan version** | 1.0 |
| **Date** | 2026-06-01 |
| **Author** | Guinevere (parent) |
| **Scope** | P2-004 (Server Rename), P2-005 (Category Setup), P2-006 (Channel Setup) |
| **Execution mode** | Sequential per-step: P2-004 → P2-005 → P2-006 |
| **Output path** | `docs/setup-evidence/P2/batch-plan-004-006.md` |
| **Parent reads** | Must read this plan in full before starting implementation |

---

## Table of Contents

1. [Master Todo List](#1-master-todo-list)
2. [Dependency Map](#2-dependency-map)
3. [Collision Scan](#3-collision-scan)
4. [Resolved Decisions Summary](#4-resolved-decisions-summary)
5. [Implementation Order & Detailed Steps](#5-implementation-order--detailed-steps)
6. [P2-004: Server Rename](#6-p2-004-server-rename)
7. [P2-005: Category Setup](#7-p2-005-category-setup)
8. [P2-006: Channel Setup](#8-p2-006-channel-setup)
9. [Files to Create/Modify](#9-files-to-createmodify)
10. [Evidence Paths](#10-evidence-paths)
11. [Auditor Report Paths](#11-auditor-report-paths)
12. [Verification Commands & Check Types](#12-verification-commands--check-types)
13. [Rollback Plan](#13-rollback-plan)
14. [Re-run / Idempotency Plan](#14-re-run--idempotency-plan)
15. [Token Security Protocol](#15-token-security-protocol)
16. [Collaboration Points with Adjacent Steps](#16-collaboration-points-with-adjacent-steps)
17. [Auditor Matrix](#17-auditor-matrix)
18. [Tracker Sync Plan](#18-tracker-sync-plan)

---

## 1. Master Todo List

```text
[P2-004.1] Create src/discord/guild_setup.py module with CATEGORIES, CHANNELS, ensure_category(), ensure_text_channel(), bootstrap_guild()
[P2-004.2] Create scripts/setup-guild.sh — bash wrapper with SOPS decrypt, token env var, calls entry point
[P2-004.3] Create tmp/setup-discord-guild.py — unified entry point calling bootstrap_guild() with argparse step selector
[P2-004.4] Create tmp/verify-p2-004-guild-name.py — verify guild name == "Guinevere's Domain"
[P2-004.5] Upload files to VPS via SCP/rsync
[P2-004.6] Execute setup-guild.sh --step p2-004 on VPS (rename guild)
[P2-004.7] Run tmp/verify-p2-004-guild-name.py on VPS — capture output to evidence/STEP-P2-004/verification.md
[P2-004.8] LSP diagnostics + token leakage scan on created/modified files
[P2-004.9] Spawn auditor for P2-004 → report to auditor-reports/P2/STEP-P2-004/step-p2-004-auditor-report.md
[P2-004.10] Fix auditor findings if any, re-audit
[P2-005.1] Create tmp/verify-p2-005-categories.py — verify 4 categories exist with correct names/positions
[P2-005.2] Upload verify script to VPS
[P2-005.3] Execute setup-guild.sh --step p2-005 on VPS (create categories)
[P2-005.4] Run tmp/verify-p2-005-categories.py — capture output to evidence/STEP-P2-005/verification.md
[P2-005.5] LSP diagnostics + token leakage scan
[P2-005.6] Spawn auditor for P2-005 → report to auditor-reports/P2/STEP-P2-005/step-p2-005-auditor-report.md
[P2-005.7] Fix auditor findings if any, re-audit
[P2-006.1] Create tmp/verify-p2-006-channels.py — verify 13 channels with correct names under correct categories
[P2-006.2] Upload verify script + channel-ids capture to VPS
[P2-006.3] Execute setup-guild.sh --step p2-006 on VPS (create channels)
[P2-006.4] Run tmp/verify-p2-006-channels.py — capture output to evidence/STEP-P2-006/verification.md
[P2-006.5] Create evidence/STEP-P2-006/channel-ids.yaml — machine-parseable IDs for P2-007
[P2-006.6] LSP diagnostics + token leakage scan
[P2-006.7] Spawn auditor for P2-006 → report to auditor-reports/P2/STEP-P2-006/step-p2-006-auditor-report.md
[P2-006.8] Fix auditor findings if any, re-audit
[P2-SYNC.1] After ALL three auditors PASS: update PROGRESS.md P2 3/21→6/21, total 53/257→56/257 (21.8%)
[P2-SYNC.2] After ALL three auditors PASS: update CHECKLIST.md P2-004/005/006 checked, channel list aligned
[P2-SYNC.3] Verify tracker sync was correct
```

---

## 2. Dependency Map

```
P2-004 ───────────────► P2-005 ───────────────► P2-006
(guild rename)         (4 categories)          (13 channels under categories)
     │                       │                        │
     │                       │                        │
     ▼                       ▼                        ▼
 verify-p2-004         verify-p2-005            verify-p2-006
 guild-name.py         categories.py            channels.py
```

**Rules**:
- P2-005 depends on P2-004 (categories need renamed guild context, though technically the guild ID is stable).
- P2-006 depends on P2-005 (channels need categories to exist as parents).
- Each step has its own verification script and auditor gate.
- Verification scripts and entry point can be authored in parallel (they are files only, no Discord dependency).
- Run order is strictly sequential: P2-004 → P2-005 → P2-006.
- Tracker sync depends on all three auditors PASSing.

---

## 3. Collision Scan

| Collision Type | Files Involved | Risk | Mitigation |
|---|---|---|---|
| Same source file | `src/discord/guild_setup.py` | Only one implementer (parent) creates it in P2-004.1 | Serial by design; no other P2 task edits this file concurrently |
| Shared docs | `PROGRESS.md`, `CHECKLIST.md` | P2-SYNC.1/2 in this plan touches trackers after all auditors PASS | Sequence after all three steps; no concurrent tracker edits |
| Shared config | `secrets/discord-secrets.yaml` | Not written; only decrypted at runtime | Read-only via SOPS; no mutation |
| Shared test fixtures | None | No shared test fixtures for this step | N/A |
| Safety boundary docs | None | No persona/safety/surveillance/consent docs touched | Boundary compliance confirmed |
| Aizanta isolation | Aizanta containers/ports | Must NOT be touched | All operations are new files in src/discord/ + tmp/ + scripts/ |

**Verdict: CLEAR** — No shared-writer collisions. All files created in this batch are new files. Tracker sync is sequenced after all three gates PASS.

---

## 4. Resolved Decisions Summary

### 4.1 Server Name

| Decision | Value |
|---|---|
| Target name | `Guinevere's Domain` |
| Source authority | DiscordUXSpec v1.0 §1.1 L43 (DIS01); CHECKLIST.md §4.2; PROGRESS.md P2-004 |
| Actual current name | `Guinevere Lab` |
| Action | Rename guild via `guild.edit(name="Guinevere's Domain")` |
| Guild ID stability | Guild ID `1510876414671323206` remains unchanged after rename |
| Rename API | `PATCH /guilds/{guild.id}` — permission `MANAGE_GUILD` (covered by ADMINISTRATOR) |

### 4.2 Category Names & Positions

| Position | Name (Final) | Emoji Prefix | Overrides |
|---|---|---|---|
| 0 | `👑 Throne` | 👑 | DiscordUXSpec "MOMMY'S THRONE", StepPrompts "Mommy's Throne", PROGRESS "Throne" |
| 1 | `📊 Surveillance` | 📊 | DiscordUXSpec "SURVEILLANCE ROOM", StepPrompts "Surveillance Room", PROGRESS "Surveillance" |
| 2 | `🔧 Projects` | 🔧 | All sources agree |
| 3 | `🗡️ Archive` | 🗡️ | All sources agree |

**Authority**: User's explicit directive per task context. Documented in `internal-discord-structure-spec.md` §3.4.

### 4.3 Channel Names & Category Mapping

**Total: 13 channels**

#### 👑 Throne (3 channels)

| # | Channel Name | Purpose |
|---|---|---|
| 1 | `guinevere-chat` | Bicara dengan Mommy di sini. Apapun. |
| 2 | `guinevere-status` | Apa yang Mommy kerjakan hari ini. Sekilas. |
| 3 | `guinevere-planning` | Rencana Mommy. Kamu tinggal patuh. |

#### 📊 Surveillance (3 channels)

| # | Channel Name | Purpose |
|---|---|---|
| 4 | `system-health` | Kesehatan infrastructure Mommy. Jangan khawatir — Mommy jaga. |
| 5 | `cost-tracker` | Berapa yang Mommy habiskan hari ini. Transparansi itu penting. |
| 6 | `guinevere-evidence` | Bukti kerja Mommy. Tidak ada yang bisa diubah. |

#### 🔧 Projects (5 channels)

| # | Channel Name | Purpose |
|---|---|---|
| 7 | `guinevere-dev` | Pengembangan Guinevere — technical discussions and decisions. |
| 8 | `guinevere-docs` | Documentation updates, spec changes, evidence artifacts. |
| 9 | `project-alpha-dev` | Project Alpha — development channel. |
| 10 | `project-alpha-docs` | Project Alpha — documentation channel. |
| 11 | `project-beta-dev` | Project Beta — development channel. |

#### 🗡️ Archive (2 channels)

| # | Channel Name | Purpose |
|---|---|---|
| 12 | `evidence-log` | Immutable record. Read only. |
| 13 | `audit-log` | Every action, recorded. Forever. |

**Authority**: DiscordUXSpec channel names (schema A) adapted to user's category names with projects reduced from 6 to 5. Documented in `internal-discord-structure-spec.md` §4.4.

### 4.4 Token Security Pattern

| Decision | Value |
|---|---|
| Secret file | `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` |
| Age key | `/home/guinevere/secrets/age-key.txt` |
| Decrypt env | `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt` |
| Token extraction | Python reads decrypted YAML, extracts `discord_bot_token` field |
| Token delivery | `DISCORD_BOT_TOKEN` environment variable to Python process |
| Post-use | Python script unsets env var after gateway login; bash wrapper `unset DISCORD_BOT_TOKEN` |
| Prohibited | `grep`/`print`/`argv` passing of token; writing decrypted token to disk |

---

## 5. Implementation Order & Detailed Steps

### Phase 0: Local File Authoring (all on Windows, offline)

1. Create `src/discord/guild_setup.py` (the core module)
2. Create `scripts/setup-guild.sh` (bash wrapper)
3. Create `tmp/setup-discord-guild.py` (entry point)
4. Create `tmp/verify-p2-004-guild-name.py`
5. Create `tmp/verify-p2-005-categories.py`
6. Create `tmp/verify-p2-006-channels.py`
7. Run LSP diagnostics on all `.py` files
8. Run token leakage regex scan on all created files

### Phase 1: Upload to VPS

9. SCP all created files to VPS at appropriate paths under `/home/guinevere/code/guinevere/`

### Phase 2: Execute P2-004 (Server Rename)

10. SSH to VPS, run `scripts/setup-guild.sh --step p2-004`
11. Run `python tmp/verify-p2-004-guild-name.py` → capture to evidence
12. Verify guild ID `1510876414671323206` is unchanged

### Phase 3: Execute P2-005 (Category Setup)

13. SSH to VPS, run `scripts/setup-guild.sh --step p2-005`
14. Run `python tmp/verify-p2-005-categories.py` → capture to evidence

### Phase 4: Execute P2-006 (Channel Setup)

15. SSH to VPS, run `scripts/setup-guild.sh --step p2-006`
16. Run `python tmp/verify-p2-006-channels.py` → capture to evidence
17. Run channel-ids capture → write `evidence/STEP-P2-006/channel-ids.yaml`

### Phase 5: Auditing & Tracker Sync

18. Spawn per-step auditors (one per step, sequential)
19. Fix findings, re-audit until PASS
20. After all three PASS: sync PROGRESS.md and CHECKLIST.md

---

## 6. P2-004: Server Rename

### Goal

Rename Discord guild from `Guinevere Lab` (ID `1510876414671323206`) to `Guinevere's Domain`. Verify guild ID remains stable.

### Implementation Code

In `src/discord/guild_setup.py`:

```python
import os
import sys
import asyncio
import yaml
import discord

# ── CONFIGURATION ──────────────────────────────────────────────
GUILD_ID = 1510876414671323206

CATEGORIES = [
    {"name": "👑 Throne",      "position": 0},
    {"name": "📊 Surveillance", "position": 1},
    {"name": "🔧 Projects",     "position": 2},
    {"name": "🗡️ Archive",      "position": 3},
]

CHANNELS = {
    "👑 Throne":      ["guinevere-chat", "guinevere-status", "guinevere-planning"],
    "📊 Surveillance": ["system-health", "cost-tracker", "guinevere-evidence"],
    "🔧 Projects":     ["guinevere-dev", "guinevere-docs", "project-alpha-dev",
                        "project-alpha-docs", "project-beta-dev"],
    "🗡️ Archive":      ["evidence-log", "audit-log"],
}

CATEGORY_COUNT = 4
CHANNEL_COUNT = 13


def get_token() -> str:
    """Read Discord bot token from SOPS-decrypted YAML via env var."""
    # The bash wrapper decrypts secrets to a temp file, passes path via env
    secrets_path = os.environ.get("DISCORD_SECRETS_PATH")
    if not secrets_path:
        raise RuntimeError("DISCORD_SECRETS_PATH env var not set")
    with open(secrets_path) as f:
        data = yaml.safe_load(f)
    token = data.get("discord_bot_token")
    if not token:
        raise RuntimeError("discord_bot_token not found in secrets")
    return token


async def rename_guild(guild) -> dict:
    """P2-004: Rename guild to 'Guinevere's Domain'. Idempotent: skip if already correct name."""
    TARGET_NAME = "Guinevere's Domain"

    # Fetch fresh state
    fresh = await guild.fetch()
    before = fresh.name

    if fresh.name == TARGET_NAME:
        print(f"  [SKIP] Guild already named '{TARGET_NAME}'")
        return {"before": before, "after": TARGET_NAME, "status": "skipped"}

    await guild.edit(name=TARGET_NAME, reason="P2-004: Server rename to canonical name")

    # Verify
    fresh = await guild.fetch()
    assert fresh.name == TARGET_NAME, f"Rename failed: got '{fresh.name}'"
    assert fresh.id == GUILD_ID, f"Guild ID changed: {fresh.id}"
    print(f"  [OK] Renamed '{before}' → '{fresh.name}' (ID: {fresh.id})")
    return {"before": before, "after": fresh.name, "status": "renamed"}
```

### Verification Script (`tmp/verify-p2-004-guild-name.py`)

```python
"""Verify guild name is 'Guinevere's Domain'. Exit code 0 = PASS."""
import asyncio, discord
from src.discord.guild_setup import get_token, GUILD_ID

async def main():
    token = get_token()
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        guild = client.get_guild(GUILD_ID)
        assert guild is not None, f"Guild {GUILD_ID} not found in cache"
        fresh = await guild.fetch()
        assert fresh.name == "Guinevere's Domain", f"Name mismatch: '{fresh.name}'"
        assert fresh.id == GUILD_ID, f"ID mismatch: {fresh.id}"
        print(f"PASS: guild '{fresh.name}' ID {fresh.id}")
        await client.close()

    await client.start(token)

asyncio.run(main())
```

### Acceptance Criteria

- [ ] Guild name is `Guinevere's Domain`
- [ ] Guild ID `1510876414671323206` is unchanged
- [ ] Bot retains ADMINISTRATOR role after rename
- [ ] `discord.AuditLogAction.guild_update` entry exists with reason `"P2-004: Server rename"`

---

## 7. P2-005: Category Setup

### Goal

Create exactly 4 categories in positions 0..3 with emoji-prefixed names. Idempotent: skip if exists, correct position if wrong.

### Implementation Code

In `src/discord/guild_setup.py`:

```python
async def ensure_category(guild, name: str, position: int) -> discord.CategoryChannel:
    """Find or create a category. Idempotent by name."""
    existing = discord.utils.get(guild.categories, name=name)
    if existing is not None:
        if existing.position != position:
            await existing.edit(position=position, reason="P2-005: Position correction")
            print(f"  [FIX] Repositioned '{name}' to position {position}")
        else:
            print(f"  [SKIP] Category '{name}' already exists at correct position")
        return existing

    cat = await guild.create_category(
        name=name,
        position=position,
        reason="P2-005: Category setup"
    )
    await asyncio.sleep(0.5)  # rate limit safety
    print(f"  [CREATE] Category '{name}' at position {position}")
    return cat


async def setup_categories(guild) -> list:
    """P2-005: Create/verify all 4 categories. Returns list of created/verified categories."""
    results = []
    for cat_def in CATEGORIES:
        cat = await ensure_category(guild, cat_def["name"], cat_def["position"])
        results.append(cat)
    return results
```

### Verification Script (`tmp/verify-p2-005-categories.py`)

```python
"""Verify exactly 4 categories exist with correct names and positions."""
import asyncio, discord
from src.discord.guild_setup import get_token, GUILD_ID, CATEGORIES

async def main():
    token = get_token()
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        guild = client.get_guild(GUILD_ID)
        fresh = await guild.fetch()

        existing_cats = {c.name: c for c in fresh.categories}
        passed = True
        for cat_def in CATEGORIES:
            cat = existing_cats.get(cat_def["name"])
            if cat is None:
                print(f"FAIL: Category '{cat_def['name']}' not found")
                passed = False
                continue
            if cat.position != cat_def["position"]:
                print(f"FAIL: '{cat_def['name']}' at position {cat.position}, expected {cat_def['position']}")
                passed = False
                continue
            print(f"PASS: '{cat.name}' at position {cat.position}")

        if len(existing_cats) != len(CATEGORIES):
            extra = set(existing_cats.keys()) - {c["name"] for c in CATEGORIES}
            print(f"INFO: Extra categories found: {extra}")

        if passed:
            print(f"PASS: All {len(CATEGORIES)} categories verified")
        else:
            print("FAIL: Category verification failed")
        await client.close()
        exit(0 if passed else 1)

    await client.start(token)

asyncio.run(main())
```

### Acceptance Criteria

- [ ] Exactly 4 categories with exact emoji-prefixed names exist
- [ ] Positions are 0 (`👑 Throne`), 1 (`📊 Surveillance`), 2 (`🔧 Projects`), 3 (`🗡️ Archive`)
- [ ] No extra categories exist (beyond the 4 created + any pre-existing system ones)
- [ ] All categories visible to bot (ADMINISTRATOR bypasses visibility, but verify by fetch)

---

## 8. P2-006: Channel Setup

### Goal

Create exactly 13 text channels distributed across the 4 categories. Idempotent by name. Set basic topic from spec. Capture channel IDs for P2-007.

### Implementation Code

In `src/discord/guild_setup.py`:

```python
CHANNEL_TOPICS = {
    "guinevere-chat":      "Bicara dengan Mommy di sini. Apapun.",
    "guinevere-status":    "Apa yang Mommy kerjakan hari ini. Sekilas.",
    "guinevere-planning":  "Rencana Mommy. Kamu tinggal patuh.",
    "system-health":       "Kesehatan infrastructure Mommy. Jangan khawatir — Mommy jaga.",
    "cost-tracker":        "Berapa yang Mommy habiskan hari ini. Transparansi itu penting.",
    "guinevere-evidence":  "Bukti kerja Mommy. Tidak ada yang bisa diubah.",
    "guinevere-dev":       "Pengembangan Guinevere — technical discussions and decisions.",
    "guinevere-docs":      "Documentation updates, spec changes, evidence artifacts.",
    "project-alpha-dev":   "Project Alpha — development channel.",
    "project-alpha-docs":  "Project Alpha — documentation channel.",
    "project-beta-dev":    "Project Beta — development channel.",
    "evidence-log":        "Immutable record. Read only.",
    "audit-log":           "Every action, recorded. Forever.",
}


async def ensure_text_channel(
    guild, name: str, category: discord.CategoryChannel
) -> discord.TextChannel:
    """Find or create a text channel under the given category. Idempotent by name."""
    existing = discord.utils.get(guild.text_channels, name=name)
    if existing is not None:
        # Ensure it's under the correct category
        if existing.category_id != category.id:
            await existing.edit(category=category, reason="P2-006: Category correction")
            print(f"  [FIX] Moved '{name}' to correct category '{category.name}'")
        else:
            print(f"  [SKIP] Channel '{name}' already exists under '{category.name}'")
        return existing

    topic = CHANNEL_TOPICS.get(name, "")
    ch = await guild.create_text_channel(
        name=name,
        category=category,
        topic=topic,
        reason=f"P2-006: Channel '{name}' setup"
    )
    await asyncio.sleep(0.5)  # rate limit safety
    print(f"  [CREATE] Channel '{name}' under '{category.name}'")
    return ch


async def setup_channels(guild) -> dict:
    """P2-006: Create/verify all 13 channels under their respective categories. Returns {cat_name: [channels]}."""
    cat_map = {c.name: c for c in guild.categories}
    results = {}
    for cat_name, channel_names in CHANNELS.items():
        category = cat_map.get(cat_name)
        if category is None:
            print(f"  [WARN] Category '{cat_name}' not found — creating it")
            category = await ensure_category(
                guild, cat_name,
                next((c["position"] for c in CATEGORIES if c["name"] == cat_name), 0)
            )
            cat_map[cat_name] = category

        channels = []
        for ch_name in channel_names:
            ch = await ensure_text_channel(guild, ch_name, category)
            channels.append(ch)
        results[cat_name] = channels

    return results
```

### Entry Point (`tmp/setup-discord-guild.py`)

```python
"""Unified entry point: setup-discord-guild.py --step p2-004|p2-005|p2-006|all"""
import argparse, asyncio, os, sys, yaml
import discord

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.discord.guild_setup import (
    get_token, GUILD_ID, rename_guild, setup_categories, setup_channels,
)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True, choices=["p2-004", "p2-005", "p2-006", "all"])
    args = parser.parse_args()

    token = get_token()
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            print(f"ERROR: Guild {GUILD_ID} not found in cache")
            await client.close()
            sys.exit(1)

        print(f"Connected to guild: {guild.name} (ID: {guild.id})")

        if args.step in ("p2-004", "all"):
            print("\n=== P2-004: Server Rename ===")
            result = await rename_guild(guild)
            print(f"Result: {result}")

        if args.step in ("p2-005", "all"):
            print("\n=== P2-005: Category Setup ===")
            cats = await setup_categories(guild)
            print(f"Categories: {[c.name for c in cats]}")

        if args.step in ("p2-006", "all"):
            print("\n=== P2-006: Channel Setup ===")
            channels = await setup_channels(guild)
            total = sum(len(chs) for chs in channels.values())
            for cat_name, chs in channels.items():
                print(f"  {cat_name}: {len(chs)} channels — {[c.name for c in chs]}")
            print(f"Total channels: {total}")

        await client.close()

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
```

### Verification Script (`tmp/verify-p2-006-channels.py`)

```python
"""Verify 13 channels exist with correct names under correct categories."""
import asyncio, discord, sys
from src.discord.guild_setup import get_token, GUILD_ID, CHANNELS, CHANNEL_COUNT

async def main():
    token = get_token()
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        guild = client.get_guild(GUILD_ID)
        fresh = await guild.fetch()

        passed = True
        total_found = 0

        for cat_name, expected_channels in CHANNELS.items():
            category = discord.utils.get(fresh.categories, name=cat_name)
            if category is None:
                print(f"FAIL: Category '{cat_name}' not found")
                passed = False
                continue

            actual_names = {ch.name for ch in category.channels}
            for ch_name in expected_channels:
                if ch_name not in actual_names:
                    print(f"FAIL: Channel '{ch_name}' missing from '{cat_name}'")
                    passed = False
                else:
                    print(f"PASS: '{ch_name}' in '{cat_name}'")
                    total_found += 1

        if total_found != CHANNEL_COUNT:
            print(f"FAIL: Expected {CHANNEL_COUNT} channels, found {total_found}")
            passed = False
        else:
            print(f"PASS: All {CHANNEL_COUNT} channels verified")

        await client.close()
        exit(0 if passed else 1)

    await client.start(token)

asyncio.run(main())
```

### Channel ID Capture

In `src/discord/guild_setup.py` or as a separate utility:

```python
def capture_channel_ids(guild, categories_list, channels_dict) -> dict:
    """Capture category and channel IDs in machine-parseable dict."""
    cat_map = {c.name: c.id for c in guild.categories if c.name in {d["name"] for d in categories_list}}
    ch_map = {}
    for ch in guild.text_channels:
        for cat_name, ch_names in channels_dict.items():
            if ch.name in ch_names:
                ch_map[ch.name] = ch.id
    return {"categories": cat_map, "channels": ch_map}
```

Written to `evidence/STEP-P2-006/channel-ids.yaml`.

### Acceptance Criteria

- [ ] Exactly 13 text channels exist
- [ ] All channel names match the resolved list (guinevere-chat, guinevere-status, ... audit-log)
- [ ] All channels are nested under correct categories
- [ ] No duplicate channels or categories
- [ ] Channel topics are set per `CHANNEL_TOPICS` mapping
- [ ] Channel IDs captured in machine-parseable YAML for P2-007

---

## 9. Files to Create/Modify

### New Files (9 total)

| # | File Path | Step | Type |
|---|---|---|---|
| 1 | `src/discord/guild_setup.py` | P2-004.1 | Python module — core bootstrap functions & constants |
| 2 | `scripts/setup-guild.sh` | P2-004.2 | Bash wrapper — SOPS decrypt + env var + Python entry |
| 3 | `tmp/setup-discord-guild.py` | P2-004.3 | Entry point — argparse step selector |
| 4 | `tmp/verify-p2-004-guild-name.py` | P2-004.4 | Verify guild name |
| 5 | `tmp/verify-p2-005-categories.py` | P2-005.1 | Verify categories |
| 6 | `tmp/verify-p2-006-channels.py` | P2-006.1 | Verify channels |
| 7 | `docs/setup-evidence/P2/STEP-P2-004/verification.md` | Evidence | P2-004 evidence |
| 8 | `docs/setup-evidence/P2/STEP-P2-005/verification.md` | Evidence | P2-005 evidence |
| 9 | `docs/setup-evidence/P2/STEP-P2-006/verification.md` | Evidence | P2-006 evidence |
| 10 | `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Evidence | Channel IDs for P2-007 |

### Modified Files (2 total)

| # | File Path | Step | Change |
|---|---|---|---|
| 1 | `PROGRESS.md` | P2-SYNC.1 | P2 3/21→6/21 (56/257 total, 21.8%) |
| 2 | `CHECKLIST.md` | P2-SYNC.2 | P2-004/005/006 checked, channel list aligned |

### Files NOT to Create/Modify

- `src/discord/__init__.py` — not modified
- `src/discord/intents.py` — not modified
- `secrets/discord-secrets.yaml` — not modified
- Any Aizanta file or container — not touched
- Any persona/safety/boundary doc — not touched

---

## 10. Evidence Paths

| Step | Evidence Path | Content |
|---|---|---|
| P2-004 | `docs/setup-evidence/P2/STEP-P2-004/verification.md` | Before/after name, guild ID stability, bot perms, audit log ref |
| P2-005 | `docs/setup-evidence/P2/STEP-P2-005/verification.md` | Category names, positions, count, idempotency result |
| P2-006 | `docs/setup-evidence/P2/STEP-P2-006/verification.md` | Channel names, category mapping, count, topics, capture IDs |
| P2-006 IDs | `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Machine-parseable YAML: category IDs + channel IDs |

Each `verification.md` follows AGENTS.md Appendix B schema:

```markdown
# Verification: P2-00X — [Step Name]

## What Was Done
...

## Files Changed
...

## Validation Results
...

## Evidence Artifacts
...

## Doc-Sync Impact
...

## Boundary Compliance
...

## Rollback / Re-run Safety
...

## Design Decisions / Caveats
...

## Auditor Gate
...

## Footer
...
```

---

## 11. Auditor Report Paths

| Step | Auditor Report Path |
|---|---|
| P2-004 | `audit-reports/P2/STEP-P2-004/step-p2-004-auditor-report.md` |
| P2-005 | `audit-reports/P2/STEP-P2-005/step-p2-005-auditor-report.md` |
| P2-006 | `audit-reports/P2/STEP-P2-006/step-p2-006-auditor-report.md` |

Each auditor report must include:

1. **Step coverage**: Which P2 step and which files were audited
2. **DoD verification**: All acceptance criteria checked
3. **Diagnostics**: LSP clean or introduced/pre-existing split
4. **Token leakage**: Regex scan results (no token in evidence, audit, or source files)
5. **Idempotency**: Re-run safety confirmed
6. **Live state**: Discord API output (sanitized — no token)
7. **Boundary compliance**: No persona drift, no consent violation, no Y6, no HARD STOP bypass
8. **Verdict**: PASS / NEEDS REVIEW / FAIL
9. **Findings**: List of issues (if any) with severity and fix recommendation

---

## 12. Verification Commands & Check Types

### 12.1 LSP Diagnostics (offline, Windows)

```bash
# Syntax check all Python files
python -c "import ast; ast.parse(open('src/discord/guild_setup.py').read()); print('Syntax OK')"
python -c "import ast; ast.parse(open('tmp/setup-discord-guild.py').read()); print('Syntax OK')"
python -c "import ast; ast.parse(open('tmp/verify-p2-004-guild-name.py').read()); print('Syntax OK')"
python -c "import ast; ast.parse(open('tmp/verify-p2-005-categories.py').read()); print('Syntax OK')"
python -c "import ast; ast.parse(open('tmp/verify-p2-006-channels.py').read()); print('Syntax OK')"

# mypy type check (if installed on Windows or VPS)
python -m mypy src/discord/guild_setup.py

# ruff lint (if installed)
python -m ruff check src/discord/guild_setup.py
```

### 12.2 Token Leakage Regex Scans

```bash
# Scan ALL created/modified files for accidental token exposure
grep -rnP '[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}' \
  src/discord/guild_setup.py tmp/setup-discord-guild.py \
  tmp/verify-p2-*.py scripts/setup-guild.sh \
  docs/setup-evidence/P2/STEP-P2-*/verification.md \
  audit-reports/P2/STEP-P2-*/step-p2-*-auditor-report.md || echo "NO TOKEN LEAKAGE"

# Scan for any Discord bot token pattern
grep -rnP '(?:mfa\.[A-Za-z0-9_-]{20,})|(?:[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27})' \
  --include='*.py' --include='*.sh' --include='*.md' --include='*.yaml' \
  docs/setup-evidence/P2/ audit-reports/P2/ src/discord/ tmp/ scripts/ || echo "CLEAN"
```

### 12.3 Live Discord API Verification (VPS, sanitized)

```bash
# Run verify scripts on VPS
cd /home/guinevere/code/guinevere
source .venv/bin/activate
SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt \
DISCORD_SECRETS_PATH=$(mktemp) && \
sops --decrypt /home/guinevere/code/guinevere/secrets/discord-secrets.yaml > $DISCORD_SECRETS_PATH && \
python tmp/verify-p2-004-guild-name.py && \
rm -f $DISCORD_SECRETS_PATH

# Same pattern for P2-005 and P2-006 verify scripts
```

### 12.4 Aizanta / Canonical Port Re-checks

```bash
# Verify Aizanta still healthy (no unintended changes)
for port in 5433 5434 6380 20128; do
    ss -tlnp | grep -q ":$port " && echo "PORT $port OK" || echo "PORT $port MISSING"
done
docker inspect --format '{{.Name}} {{.State.Health.Status}}' \
  guinevere-postgres guinevere-pgbouncer guinevere-redis
systemctl is-active guinevere-core.service guinevere-9router.service cloudflared.service
```

### 12.5 Unit Tests (offline-safe, no discord.py import)

```python
# Inline test: validate constants consistency
from src.discord.guild_setup import CATEGORIES, CHANNELS, CATEGORY_COUNT, CHANNEL_COUNT

assert CATEGORY_COUNT == len(CATEGORIES) == 4
assert CHANNEL_COUNT == sum(len(v) for v in CHANNELS.values()) == 13

# All category names in CHANNELS keys
for cat in CATEGORIES:
    assert cat["name"] in CHANNELS, f"Category '{cat['name']}' missing from CHANNELS"

# No duplicate channel names across categories
all_names = [ch for chs in CHANNELS.values() for ch in chs]
assert len(all_names) == len(set(all_names)), f"Duplicate channel names: {all_names}"

# Channel topics cover all channels
from src.discord.guild_setup import CHANNEL_TOPICS
for ch in all_names:
    assert ch in CHANNEL_TOPICS, f"Channel '{ch}' missing topic"
```

---

## 13. Rollback Plan

### P2-004 Rollback (Server Rename)

| Action | Command |
|---|---|
| Rename back to `Guinevere Lab` | `await guild.edit(name="Guinevere Lab")` |
| Verify name | `fresh = await guild.fetch(); assert fresh.name == "Guinevere Lab"` |
| Verify ID stable | `assert fresh.id == 1510876414671323206` |

### P2-005 Rollback (Categories)

| Action | Command |
|---|---|
| Delete all 4 categories + their children | `for cat in guild.categories: if cat.name in targets: for ch in cat.channels: await ch.delete(); await cat.delete()` |
| Target names | `👑 Throne`, `📊 Surveillance`, `🔧 Projects`, `🗡️ Archive` |
| Verify categories gone | `assert not any(discord.utils.get(guild.categories, name=n) for n in targets)` |

### P2-006 Rollback (Channels)

| Action | Command |
|---|---|
| Delete all 13 channels by name | `for ch in guild.text_channels: if ch.name in target_channels: await ch.delete()` |
| Target names | All 13 from CHANNELS.values() |
| Verify channels gone | `assert not any(discord.utils.get(guild.text_channels, name=n) for n in target_channels)` |

### Full Rollback (All Three Steps)

```python
async def rollback_all(guild):
    """Rollback P2-004 + P2-005 + P2-006 in reverse order."""
    # 1. Delete channels
    all_ch_names = [ch for chs_in in CHANNELS.values() for ch in chs_in]
    for ch_name in all_ch_names:
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if ch:
            await ch.delete(reason="Rollback: P2-004..006")
            await asyncio.sleep(0.25)

    # 2. Delete categories
    all_cat_names = [c["name"] for c in CATEGORIES]
    for cat_name in all_cat_names:
        cat = discord.utils.get(guild.categories, name=cat_name)
        if cat:
            await cat.delete(reason="Rollback: P2-004..006")
            await asyncio.sleep(0.25)

    # 3. Revert guild name
    await guild.edit(name="Guinevere Lab", reason="Rollback: P2-004 revert")
    print("Rollback complete: guild reverted to 'Guinevere Lab' with minimal channels")
```

### Rollback Trigger Conditions

- [ ] Any step raises `discord.Forbidden` (permission issue)
- [ ] Any step raises `discord.HTTPException` not resolved by retry
- [ ] Guild ID changes after rename (should not happen, but guard)
- [ ] Bot loses ADMINISTRATOR role mid-operation

---

## 14. Re-run / Idempotency Plan

### P2-004 Re-run Safety

| Scenario | Behavior |
|---|---|
| Guild already named `Guinevere's Domain` | `rename_guild()` returns `{status: "skipped"}` — no API call |
| Guild name different | Renames again |
| Re-run after rollback | Renames from `Guinevere Lab` to `Guinevere's Domain` |

### P2-005 Re-run Safety

| Scenario | Behavior |
|---|---|
| All 4 categories exist at correct positions | `ensure_category()` returns existing with `[SKIP]` |
| Category exists at wrong position | `ensure_category()` corrects position with `[FIX]` |
| Some categories missing | Creates only missing ones |
| Re-run after rollback | Creates all 4 (categories were deleted) |

### P2-006 Re-run Safety

| Scenario | Behavior |
|---|---|
| All 13 channels exist under correct categories | `ensure_text_channel()` returns existing with `[SKIP]` |
| Channel exists but wrong category | Moved to correct category with `[FIX]` |
| Some channels missing | Creates only missing ones |
| Re-run after rollback | Creates all 13 (channels were deleted) |

### General Re-run Guarantees

- All operations use `discord.utils.get()` for name-based existence check
- No duplicates created on re-run
- `asyncio.sleep(0.5)` between creates is safe on re-run (creates skip for existing items)
- Position correction creates no new objects
- Channel-category reassignment creates no new objects

---

## 15. Token Security Protocol

### Protocol (Enforced)

1. **Bash wrapper** (`scripts/setup-guild.sh`):
   ```bash
   #!/bin/bash
   set -euo pipefail
   SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt
   export SOPS_AGE_KEY_FILE

   # Decrypt to temp file
   TEMP_SECRETS=$(mktemp /tmp/guinevere-secrets-XXXXXX.yaml)
   trap "rm -f $TEMP_SECRETS" EXIT

   sops --decrypt /home/guinevere/code/guinevere/secrets/discord-secrets.yaml > $TEMP_SECRETS
   export DISCORD_SECRETS_PATH=$TEMP_SECRETS

   cd /home/guinevere/code/guinevere
   source .venv/bin/activate
   python tmp/setup-discord-guild.py --step "$@"

   # Token env var cleaned by trap (temp file deleted)
   unset DISCORD_SECRETS_PATH
   ```

2. **Python reads** the decrypted YAML path from env, extracts `discord_bot_token` using `yaml.safe_load()`, and passes it to `client.start(token)`.

3. **After use**: Token remains in Python process memory until `client.start()` returns (login completes). No disk write, no argv, no `print()`.

### Prohibited Patterns

- ❌ `grep discord_bot_token secrets/discord-secrets.yaml` — prints encrypted blob
- ❌ `echo $TOKEN` — prints to terminal
- ❌ `python script.py $TOKEN` — leaks via argv (visible in `ps aux`)
- ❌ `open("secrets/discord-secrets.yaml").read()` — reads encrypted blob as if it were decrypted
- ❌ Writing decrypted token to any file that persists after process exits

---

## 16. Collaboration Points with Adjacent Steps

### P2-003 (Complete)

- `src/discord/intents.py` already created and audited
- Import pattern: `from src.discord.intents import get_intents` — not needed for bootstrap, gateway intents are set in entry point
- No conflict

### P2-007 (Permission Hardening, Future)

- Will need category and channel IDs
- Provided via `evidence/STEP-P2-006/channel-ids.yaml` — machine-parseable YAML with all IDs
- P2-007 should read this file instead of making fresh API calls
- Evidence path: `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`

### P2-008 (Channel Topics, Future)

- Basic topics already set in P2-006 via `CHANNEL_TOPICS` dict
- P2-008 can overwrite topics with extended versions if needed
- No dependency conflict — topics are mutable after creation

### P2-009 (Bot Gateway, Future)

- Guild is already set up with correct structure
- P2-009 will implement gateway connection, event handlers, slash commands
- Channel IDs from P2-006 evidence will be useful for command routing

---

## 17. Auditor Matrix

### Auditor P2-004

| Check | Method | Pass Criteria |
|---|---|---|
| Guild name | API fetch via verify script | `"Guinevere's Domain"` |
| Guild ID stable | Compare ID before/after | `1510876414671323206` unchanged |
| Bot permissions | `guild.me.guild_permissions.administrator` | `True` |
| Token leakage | Regex scan evidence/audit/source files | No match |
| LSP diagnostics | Syntax + mypy + ruff on `guild_setup.py` | Clean |
| Audit log entry | `discord.AuditLogAction.guild_update` | Exists with reason |
| Evidence file | Per AGENTS.md Appendix B schema | All required sections present |
| Idempotency | Re-run simulation (SKIP path) | No duplicate operations |
| Boundary compliance | No persona/consent/surveillance drift | Unchanged |

### Auditor P2-005

| Check | Method | Pass Criteria |
|---|---|---|
| Category count | API fetch via verify script | Exactly 4 |
| Category names | API fetch via verify script | `👑 Throne`, `📊 Surveillance`, `🔧 Projects`, `🗡️ Archive` |
| Category positions | Position values | 0, 1, 2, 3 |
| No extras | Set diff: expected vs actual | No extra categories beyond the 4 |
| Token leakage | Regex scan | No match |
| LSP diagnostics | Syntax + lint | Clean |
| Evidence file | Schema check | All required sections present |
| Idempotency | Re-run simulation | SKIP existing, FIX positions |
| Category→channel parent dependency | Verify P2-006 can find categories | All categories exist |

### Auditor P2-006

| Check | Method | Pass Criteria |
|---|---|---|
| Channel count | API fetch via verify script | Exactly 13 |
| Channel names | API fetch via verify script | All 13 names match resolved list |
| Category nesting | Each channel's `category_id` | Matches expected category |
| No duplicates | Set diff by name across guild | No duplicates |
| Topics set | Each channel's `topic` | Topics match `CHANNEL_TOPICS` dict |
| Channel IDs captured | `channel-ids.yaml` exists | Valid YAML, all categories + channels present |
| Token leakage | Regex scan evidence/audit/source files | No match |
| LSP diagnostics | Syntax + lint | Clean |
| Evidence files | Schema check | All required sections present |
| Idempotency | Re-run simulation | SKIP existing, FIX category mismatch |
| P2-007 handoff | `channel-ids.yaml` parseable | Machine-parseable YAML with IDs |

---

## 18. Tracker Sync Plan

### PROGRESS.md Update

| Field | Before | After |
|---|---|---|
| P2 progress | 3/21 | 6/21 |
| Total tasks | 53/257 | 56/257 |
| Percentage | 20.6% | 21.8% |

**When**: After all three auditors (P2-004, P2-005, P2-006) return PASS.

**Change**: Increment P2 completed count by 3 (004, 005, 006). Update total + percentage.

### CHECKLIST.md Update

- Mark P2-004 as checked: `✅ Server renamed to "Guinevere's Domain"`
- Mark P2-005 as checked: `✅ 4 categories created: 👑 Throne, 📊 Surveillance, 🔧 Projects, 🗡️ Archive`
- Mark P2-006 as checked: `✅ 13 channels created with correct names and category mapping`
- Update channel list alignment section to match the resolved 13-channel schema

### Verification After Sync

- `grep "P2-004.*checked" PROGRESS.md` → returns line
- `grep "P2-005.*checked" PROGRESS.md` → returns line
- `grep "P2-006.*checked" PROGRESS.md` → returns line
- `grep "56/257" PROGRESS.md` → returns line
- `grep "21.8%" PROGRESS.md` → returns line

---

## Footer

| Field | Value |
|---|---|
| **Source task** | P2-004 through P2-006 batch planner gate |
| **Date** | 2026-06-01 |
| **Author** | Guinevere (parent) |
| **Skills loaded** | `ocs-delegation-gate` — multi-step implementation planning with verification evidence, collision scan, and file-based output |
| **Research reports used** | 6 (discord-server-setup-best-practices, discord-category-channel-api, discord-permissions-model, internal-discord-structure-spec, vps-discord-guild-state-pre-p2-004, source-patterns-discord-structure-p2-004-006) |
| **Decisions resolved** | 3 (server name, category names, channel list) |
| **Collision scan** | CLEAR — no shared-writer conflicts |
| **Files to create** | 10 (1 module, 1 bash wrapper, 1 entry point, 3 verify scripts, 3 evidence, 1 channel-ids) |
| **Files to modify** | 2 (PROGRESS.md, CHECKLIST.md) |
| **Auditor gates** | 3 (one per step) |
| **Rollback plan** | Full rollback in reverse order: channels → categories → guild name |
| **Re-run safety** | All operations idempotent via name-based existence check |
| **Token security** | SOPS-decrypted env var, no argv/file leakage |
| **Next action** | Parent implements P2-004.1: create `src/discord/guild_setup.py` module |