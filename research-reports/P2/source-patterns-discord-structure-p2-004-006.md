# Source Patterns & Script Shape — P2-004/P2-005/P2-006 (Guild Setup)

| Field | Value |
|---|---|
| **Task** | Source tree inspection + proposed patterns for P2-004/005/006 |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (parent) |
| **Context** | P2-003 created src/discord/intents.py; P2-004..006 need a deterministic setup script |
| **Scope** | Read-only: candidate files, module shape, SOPS token pattern, validation approach, collision risks |

---

## 1. Current State Summary

### Pre-existing Discord state (from pre-condition C3)

| Property | Value | Source |
|---|---|---|
| Application name | Guinevere | P2-001 evidence |
| Application ID / Bot ID | 1510873134981582858 | P2-001 evidence |
| Bot username | Guinevere | P2-002 API call |
| Actual server name | Guinevere Lab | P2-001 evidence |
| Spec server name | Guinevere's Domain | DiscordUXSpec v1.0 L43 |
| Gateway intents | Presence, Server Members, Message Content | Portal + src/discord/intents.py |
| Bot permission | Administrator | Faiz-approved; flagged for P2-009 |
| Secrets file | secrets/discord-secrets.yaml (encrypted) | VPS, matches .sops.yaml rule |
| Bot OAuth2 scopes | bot, applications.commands | Verified |
| Bot joined guild? | Yes -- bot already in "Guinevere Lab" | Pre-condition C3 |

### Server Name Mismatch

The server name mismatch is deferred to P2-004 across all three audit reports and batch plan C2. P2-004 should **rename** the existing guild via Guild.edit(name=...), not recreate it. The canonical name per DiscordUXSpec v1.0 L43 is "Guinevere's Domain".

---

## 2. Existing Module Inventory

### src/discord/ package (2 files)

| File | Purpose | Status |
|---|---|---|
| src/discord/__init__.py | Package marker | Created by P2-003 |
| src/discord/intents.py | get_intents(), validate_intents(), DiscordIntents Protocol | Created by P2-003, PASS audit |

### tmp/ verifiers (relevant patterns)

| File | Pattern | Relevance |
|---|---|---|
| tmp/verify-discord-secret.sh | SOPS decrypt + API call + token lifetime | Token handling for bash wrapper |
| tmp/verify-p2-003-intents.py | from src.discord.intents import get_intents | Import pattern for verifier scripts |

### Existing research reports (highly relevant)

- research-reports/P2/discord-server-setup-best-practices.md -- Full guild setup blueprint with rename, categories, channels, idempotency, rollback
- research-reports/P2/discord-category-channel-api.md -- Complete idempotent bootstrap, emoji support, rate limit guidance
- research-reports/P2/discord-permissions-model.md -- Permission overwrite behavior for channel creation

### Issues with current StepPrompts P2-004/005/006

1. **Non-idempotent** -- Creates without checking existence (duplicate risk on re-run)
2. **Unsafe token** -- P2-004 shows open("secrets/discord-secrets.yaml").read() which reads encrypted blob
3. **Separate scripts** -- 3 login/disconnect cycles, 3x token injection, slower
4. **No reason=** -- Audit log entries empty
5. **No rate limit delay** -- Missing asyncio.sleep() between creates

---

## 3. Proposed Script/Module Architecture

`
src/discord/
  __init__.py        # Existing
  intents.py         # Existing (P2-003)
  guild_setup.py     # PROPOSED: reusable bootstrap functions

tmp/
  setup-discord-guild.py          # PROPOSED: unified entry point (P2-004+005+006)
  verify-p2-004-guild-name.py     # NEW: P2-004 verification only
  verify-p2-005-categories.py     # NEW: P2-005 verification only
  verify-p2-006-channels.py       # NEW: P2-006 verification only

scripts/
  setup-guild.sh                  # PROPOSED: shell wrapper with SOPS token injection
`

### Benefits

- Single login, token in memory once (faster: ~20s vs ~60s for 3 separate scripts)
- Coherent rollback across all 3 steps (category must exist before channels)
- Module logic independently testable via import
- Verify scripts can run independently after bootstrap

---

## 4. Task Definitions with Exact Code Patterns

### 4.1 P2-004: Server Rename

Python: wait guild.edit(name="Guinevere's Domain", reason="P2-004: Server rename")
API: PATCH /guilds/{guild.id}
Permission: MANAGE_GUILD (covered by Administrator)
Idempotent: skip if guild.name already equals "Guinevere's Domain"
Verify: fresh = await guild.fetch(); assert fresh.name == "Guinevere's Domain"

### 4.2 P2-005: 4 Categories

| Name | Position |
|---|---|
| Mommy's Throne | 0 |
| Surveillance Room | 1 |
| Projects | 2 |
| Archive | 3 |

Python: guild.create_category(name, position=pos, reason="P2-005: Category setup")
Idempotent: discord.utils.get(guild.categories, name=...) then skip; edit position if wrong
Delays: await asyncio.sleep(0.5) between each create

### 4.3 P2-006: 13 Channels

Category structure with channel names:

| Category | Channels |
|---|---|
| Mommy's Throne | announcements, general-chat, task-board |
| Surveillance Room | status, finops, audit-log |
| Projects | dev-logs, bug-reports, deployments |
| Archive | alerts, security, surveillance, persona-logs |

(All channels prefixed with emoji: announcements, general-chat, task-board, etc.)

Python: guild.create_text_channel(name, category=cat, topic=desc, reason="P2-006: Channel setup")
Idempotent: discord.utils.get(guild.text_channels, name=...) then skip
Delays: await asyncio.sleep(0.5) between each create

---

## 5. SOPS Token Pattern

### Safe pattern (bash wrapper)

The token is decrypted by SOPS and passed as an environment variable to the Python script:

`ash
# In scripts/setup-guild.sh (VPS):
# Decrypt with SOPS age key
# Extract discord_bot_token from decrypted YAML
# Pass via DISCORD_BOT_TOKEN env var to Python entry point
`

### Security rules
- NEVER pass token via argv (visible in ps aux)
- NEVER write decrypted token to a file on disk
- Environment variable is the accepted pattern for discord.py
- Use .venv path from pyproject.toml

### Note: Two-secrets-file drift

secrets/guinevere-secrets.yaml uses dotted keys (discord.bot_token)
secrets/discord-secrets.yaml uses underscore keys (discord_bot_token)
Verify script must parse discord_bot_token to match what verify-discord-secret.sh uses.

---

## 6. Collision Risks

| Risk | Severity | Mitigation |
|---|---|---|
| src/discord/__init__.py concurrent edit | MEDIUM | Verify no other P2 task edits simultaneously |
| discord.py not in VPS .venv | HIGH | Verify import before running bootstrap |
| Key name mismatch (dotted vs underscore) | MEDIUM | Parse discord_bot_token from discord-secrets.yaml |
| P2-007 depends on channel IDs | HIGH | Capture IDs in P2-006 evidence, pass to P2-007 |
| P2-008 (topics) overlaps P2-006 | MEDIUM | Set basic topics in P2-006; overwrite in P2-008 |
| CHECKLIST/PROGRESS shared writer | LOW | Sequence tracker sync after all 3 pass audit |

---

## 7. Validation & LSP Commands

### LSP checks (offline, on Windows)
`
python -m mypy src/discord/guild_setup.py
python -m ruff check src/discord/guild_setup.py
python -c "import ast; ast.parse(open('src/discord/guild_setup.py').read()); print('Syntax OK')"
`

### VPS verification scripts (3 independent, one per step)
Each verify script connects, checks one aspect, prints PASS/FAIL, disconnects.

### Unit tests (offline-safe, no discord.py import needed)
`
from src.discord.guild_setup import CATEGORIES, CHANNELS, CATEGORY_COUNT, CHANNEL_COUNT
assert CATEGORY_COUNT == 4
assert CHANNEL_COUNT == 13
assert all(cat["name"] in CHANNELS for cat in CATEGORIES)
# No duplicate channel names
all_names = [ch[0] for chs in CHANNELS.values() for ch in chs]
assert len(all_names) == len(set(all_names))
`

---

## 8. Evidence Paths

| Step | Evidence File |
|---|---|
| P2-004 | docs/setup-evidence/P2/STEP-P2-004/verification.md |
| P2-005 | docs/setup-evidence/P2/STEP-P2-005/verification.md |
| P2-006 | docs/setup-evidence/P2/STEP-P2-006/verification.md |
| P2-006 IDs | docs/setup-evidence/P2/STEP-P2-006/channel-ids.txt |

### Evidence Schema (per AGENTS.md Appendix B)

Each verification.md must include: What Was Done, Files Changed, Validation Results, Evidence Artifacts, Doc-Sync Impact, Boundary Compliance, Rollback/Re-run Safety, Design Decisions/Caveats, Auditor Gate reference, Footer.

### Channel IDs for P2-007

The channel-ids.txt file must list category and channel IDs in machine-parseable format (YAML or JSON) so P2-007 can use them for permission overwrites without another API call.

`
channels:
  announcements: <id>
  general-chat: <id>
  task-board: <id>
  status: <id>
  finops: <id>
  audit-log: <id>
  dev-logs: <id>
  bug-reports: <id>
  deployments: <id>
  alerts: <id>
  security: <id>
  surveillance: <id>
  persona-logs: <id>

categories:
  mommys-throne: <id>
  surveillance-room: <id>
  projects: <id>
  archive: <id>
`

---

## 9. Files to Create (Implementation Wave)

| # | File | Type |
|---|---|---|
| 1 | src/discord/guild_setup.py | Python module with bootstrap functions |
| 2 | tmp/setup-discord-guild.py | Entry point script |
| 3 | scripts/setup-guild.sh | Bash wrapper with SOPS decrypt |
| 4 | tmp/verify-p2-004-guild-name.py | Verification (P2-004) |
| 5 | tmp/verify-p2-005-categories.py | Verification (P2-005) |
| 6 | tmp/verify-p2-006-channels.py | Verification (P2-006) |
| 7+8+9 | Evidence dirs + files | 3 verification.md + 1 channel-ids.txt |

---

## 10. Files NOT to Create (Anti-Pattern Check)

- Do NOT put token values in any Python source file
- Do NOT create src/discord/client.py or src/discord/bot.py (gateway = P2-009+)
- Do NOT modify src/discord/__init__.py exports yet
- Do NOT add Intents.default() outside intents.py
- Do NOT write secrets to tmp without trap+shred cleanup

---

## 11. Key Recommendations Summary

| Aspect | Recommendation |
|---|---|
| Architecture | Single src/discord/guild_setup.py module + unified entry point |
| Idempotency | Name-based existence check before every create |
| Token | SOPS-decrypted env var; never file/argv |
| Rate limits | 0.5s delay between API calls |
| Validation | 3 independent verifiers + mypy + ruff + unit tests |
| Rollback | delete_category_and_children() pattern; guild name reversible |
| Collision risk | LOW -- new files only; one shared writer (tracker sync) |

---

*End of report.*
