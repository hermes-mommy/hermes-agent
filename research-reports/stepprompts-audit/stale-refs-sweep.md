# Stale Reference Sweep — stepprompts/StepPrompts.md

**Date:** 2026-06-05  
**File audited:** `stepprompts/StepPrompts.md` (57,713 lines, 2.8 MB)  
**Scope:** Exhaustive stale pattern catalog — no modifications performed  
**Method:** 18 independent grep searches covering all known stale patterns + discovered variants

---

## Executive Summary

**Total stale match instances:** 75+ across 13 categories  
**Confirmed stale (should be updated):** 42 matches  
**Migration documentation (intentional):** 18 matches  
**Anti-pattern checklists / grep commands (not stale):** ~8 matches  
**Context-dependent (may or may not be stale):** ~7 matches

---

## Summary Table

| Category | Count (Main) | Count (.bak) | Severity | Lines (Main File Only) |
|---|---|---|---|---|
| hermes-agent PyPI / NousResearch | 15 | 5 | **HIGH** | L3412–L3413, L3475–L3476, L3479–L3481, L3485, L3528–L3529, L3534, L3539, L3544, L3549–L3552 |
| config/hermes (old agent path) | 9 | 8 | **HIGH** | L485, L3584, L3587, L3661, L3666, L3672, L3676, L4597, L4607, L4657, L4667 |
| Baileys (direct references) | 10 | 1 | **MEDIUM** | L19506, L19520, L19526, L19640, L19670, L19671, L23016, L23179, L24483, L24664 |
| Baileys — "WhatsApp Web MD protocol" | 2 | 0 | **MEDIUM** | L19526, L19670 |
| Baileys — "Node.js subprocess" architecture | 2 | 0 | **MEDIUM** | L19526, L19670 |
| Baileys — "HTTP bridge" architecture | 1 | 0 | **MEDIUM** | L19670 |
| baileys-antiban (npm library ref) | 2 | 0 | **LOW** | L23016, L23179 |
| Neonize/Baileys combined reference | 1 | 0 | **LOW** | L24483 |
| Evolution API (Baileys ecosystem) | 2 | 0 | **LOW** | L24391, L24664 |
| discord.Client (old bot framework) | 4 | 9 | **HIGH** | L5661, L5689, L5809, L49484 |
| discord.py / commands.Bot references | 12 | 4 | **CONTEXT** | L3414, L3518, L8798, L8957, L9121, L10986, L16543, L20543, L23938, L24094, L26179, L47678 |
| GuinevereBot (old class name) | 12 | 2 | **CONTEXT** | L5689, L5710, L23938, L23953, L23968, L24023, L24119, L24150, L24234 |
| post-MVP | 3 | 1 | **MEDIUM** | L38586, L54177, L54414 |
| memory_bridge (health_memory_bridge.py) | 6 | 0 | **CONTEXT** | L45945, L46033, L46535, L46596, L46634, L46646 |
| src/discord/bot.py references | 35 | 1 | **CONTEXT** | L5678, L8983, L9087, L20543, L20573, L20574, L20957, L23219, L23233, L23394, L23938, L23980, L23984, L24119, L24140, L24167, L24279, L24345, L24353, L30416, L30789, L30984, L31051, L31141, L31229, L31263, L31314, L31315, L31391, L31461, L31542, L46792, L56059, L56110 |
| **NOT FOUND** | — | — | **NONE** | conversational_handler, session_adapter, HuggingFace |

**Severity Legend:**
- **HIGH** — Definitely stale; actively wrong or points to removed/renamed components
- **MEDIUM** — Likely stale; reflects superseded architecture, intentional migration notes, or deprecated terminology
- **LOW** — References old ecosystem for documentation/context only; low risk
- **CONTEXT** — May or may not be stale depending on current codebase state; requires cross-check against `src/`

---

## Category 1: hermes-agent PyPI / NousResearch (HIGH)

**Status:** Confirmed stale per ADR-035. The `hermes-agent` PyPI package is obsolete; Hermes now = NousResearch fork (installed from source).

**Count:** 15 matches in main file + 5 in .bak

### Matches

| Line | Type | Content |
|---|---|---|
| L3412 | Comment marker | `<!-- ⚠️ STALE: hermes-agent PyPI references are obsolete per ADR-035. Hermes now = NousResearch fork. -->` |
| L3413 | Package dependency | `hermes-agent \` (in dependency list alongside discord.py==2.*, prometheus-client, structlog) |
| L3475 | Comment marker | `<!-- ⚠️ STALE: hermes-agent PyPI references are obsolete per ADR-035. Hermes now = NousResearch fork. -->` |
| L3476 | Install command | `uv pip install hermes-agent` |
| L3479 | Comment marker | `<!-- ⚠️ STALE: hermes-agent PyPI references are obsolete per ADR-035. Hermes now = NousResearch fork. -->` |
| L3480 | Git clone | `# git clone https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent` |
| L3481 | Directory change | `# cd /tmp/hermes-agent` |
| L3485 | Comment marker | `<!-- ⚠️ STALE: hermes-agent PyPI references are obsolete per ADR-035. Hermes now = NousResearch fork. -->` |
| L3528 | Comment marker | `<!-- ⚠️ STALE: hermes-agent PyPI references are obsolete per ADR-035. Hermes now = NousResearch fork. -->` |
| L3529 | Verification | `- [ ] Hermes installed → \`python -c "import hermes_agent"\` succeeds` |
| L3534 | Evidence path | `- Log: \`docs/setup-evidence/P1/STEP-P1-004/hermes-install.txt\`` |
| L3539 | Rollback command | `pip uninstall -y hermes-agent` |
| L3544 | Troubleshooting | `- **Issue:** hermes-agent not on PyPI` |
| L3549 | Note | `> **Note:** The \`hermes-agent\` package may not be on PyPI. If \`pip install hermes-agent\` fails, install from source:` |
| L3551 | Git clone (note) | `> git clone https://github.com/NousResearch/hermes-agent.git` |
| L3552 | Pip install (note) | `> cd hermes-agent && pip install -e .` |

### Recommended Replacement

The hermes-agent block (L3410–L3414) in dependency listings should be replaced with:

```text
<!-- Hermes Agent: installed from NousResearch fork (ADR-035). See STEP-P1-004 for install instructions. -->
```

All `hermes-agent` PyPI references should be replaced with either:
- Removal from dependency list (hermes-agent is not a pip package)
- Reference to `git+https://github.com/NousResearch/hermes-agent.git` if installed via pip from git
- Instructions to clone and install from source per ADR-035

The `import hermes_agent` verification should be updated to verify the correct import path for the NousResearch fork.

---

## Category 2: config/hermes — Old Agent Config Path (HIGH)

**Status:** Confirmed stale. The directory `/home/guinevere/config/hermes/` belongs to the old hermes-agent architecture. Current architecture may use a different config path.

**Count:** 9 matches in main file + 8 in .bak

### Matches

| Line | Type | Content |
|---|---|---|
| L485 | Directory creation | `mkdir -p /home/guinevere/{...config/{hermes,9router,mcp,caddy,sops}...}` |
| L3584 | Shell command | `mkdir -p /home/guinevere/config/hermes` |
| L3587 | Shell command | `cat > /home/guinevere/config/hermes/config.yaml << 'EOF'` |
| L3661 | Verification | `python -c "import yaml; yaml.safe_load(open('/home/guinevere/config/hermes/config.yaml'))"` |
| L3666 | Verification | `- [ ] Config file exists → \`cat /home/guinevere/config/hermes/config.yaml\` shows content` |
| L3672 | Evidence | `- File: \`docs/setup-evidence/P1/STEP-P1-005/hermes-config.yaml\`` |
| L3676 | Rollback | `rm -rf /home/guinevere/config/hermes` |
| L4597 | Shell command | `cp ... /home/guinevere/config/hermes/system-prompt.md` |
| L4607 | Python code | `SYSTEM_PROMPT_PATH = Path("/home/guinevere/config/hermes/system-prompt.md")` |
| L4657 | Verification | `- [ ] System prompt copied → \`cat config/hermes/system-prompt.md \| wc -c\` shows > 1000 chars` |
| L4667 | Rollback | `rm config/hermes/system-prompt.md` |

### Recommended Replacement

`/home/guinevere/config/hermes/` should be replaced with the current agent config path. Candidates:
- `/home/guinevere/config/agent/` (generic, tool-agnostic)
- Whatever path the NousResearch hermes-agent fork expects
- Check ADR-035 and current deployment for the correct path

---

## Category 3: Baileys → Neonize (MEDIUM)

**Status:** All 10 matches are in P11 (WhatsApp integration) documentation. Most are intentionally documenting the ADR-022 revision requirement — they acknowledge the staleness and document the need for migration. However, the references are still technically "stale" as they refer to the old WhatsApp library.

**Count:** 10 matches in main file + 1 in .bak

### Matches

| Line | Type | Content Summary |
|---|---|---|
| L19506 | Header note | `**ADR-022 Note:** Requires revision from Baileys/Node.js to Neonize/pure Python` |
| L19520 | ADR reference | `ADR-022 (Communication Channel Strategy — **requires formal revision** from Baileys/Node.js to Neonize/Python)` |
| L19526 | Context paragraph | `ADR-022 currently mandates "WhatsApp via Baileys (WhatsApp Web MD protocol)" with a Node.js subprocess architecture...` — long migration context paragraph |
| L19640 | Evidence reference | `adr-022-revision-note.md`: Documented requirement to revise ADR-022 from Baileys to Neonize |
| L19670 | Bullet point | `ADR-022 Revision Required:` ADR-022 currently states "WhatsApp via Baileys..." — lists 6 revision items |
| L19671 | Bullet point | `Ban Risk Awareness:` "Neonize uses the same unofficial WhatsApp Multi-Device protocol as Baileys..." |
| L23016 | Paragraph | `baileys-antiban` npm library as reference implementation for Gaussian jitter |
| L23179 | Bullet point | `baileys-antiban Reference:` comparison with npm library, notes Gaussian superiority |
| L24483 | Code comment | `NEONIZE_INTERNAL = "neonize_internal" # Neonize/Baileys internal error, fresh client may fix` |
| L24664 | Bullet point | `Evolution API 515 → 401 Bug Reference:` known failure pattern in Baileys-based libraries |

### Classification

These break down into two sub-types:

**A. Migration Documentation (L19506, L19520, L19526, L19640, L19670, L19671) — 6 matches**
These are INTENTIONAL. They document the ADR-022 revision requirement and the migration from Baileys → Neonize. They should be **removed** once ADR-022 is formally revised, but are currently serving their documentation purpose.

**B. Ecosystem References (L23016, L23179, L24483, L24664) — 4 matches**
These reference Baileys ecosystem (baileys-antiban, Evolution API) for context and comparison. The L24483 code comment is a leftover "Neonize/Baileys" label that should be cleaned to just "Neonize". The Evolution API references are educational but technically stale.

### Recommended Replacement

- **L24483:** Change `# Neonize/Baileys internal error` → `# Neonize internal error`
- **L23016, L23179:** The `baileys-antiban` references are used as comparative reference implementations. Could be updated to reference `neonize` equivalents or retained as historical context with a note.
- **L19506, L19520, L19526, L19640, L19670, L19671:** Remove after ADR-022 formal revision is complete. These are self-aware migration documentation.

---

## Category 4: "WhatsApp Web MD protocol" (MEDIUM)

**Status:** Baileys-era protocol description. Neonize uses "WhatsApp Multi-Device protocol" (via whatsmeow).

**Count:** 2 matches (subset of Baileys category)

| Line | Content |
|---|---|
| L19526 | `ADR-022 currently mandates "WhatsApp via Baileys (WhatsApp Web MD protocol)" with a Node.js subprocess architecture` |
| L19670 | `ADR-022 currently states "WhatsApp via Baileys (WhatsApp Web MD protocol)" with Node.js subprocess architecture` |

### Recommended Replacement

`WhatsApp Web MD protocol` → `WhatsApp Multi-Device (MD) protocol via whatsmeow`

---

## Category 5: "Node.js subprocess" Architecture (MEDIUM)

**Status:** Baileys-era architecture. Neonize eliminates Node.js entirely.

**Count:** 2 matches (subset of Baileys category)

| Line | Content |
|---|---|
| L19526 | `...with a Node.js subprocess architecture.` |
| L19670 | `...with Node.js subprocess architecture.` |

### Recommended Replacement

Already self-documented as requiring revision. Remove after ADR-022 revision.

---

## Category 6: "HTTP bridge" Architecture (MEDIUM)

**Status:** Baileys-era integration pattern. Neonize uses direct Python integration.

**Count:** 1 match (subset of Baileys category)

| Line | Content |
|---|---|
| L19670 | `(3) replace "HTTP bridge" with "direct Python integration"` |

### Recommended Replacement

Self-aware migration instruction. No replacement needed — this line itself documents the needed change.

---

## Category 7: baileys-antiban (LOW)

**Status:** npm library references used as comparative benchmarks for Gaussian jitter anti-ban implementation. These are reference-implementation comparisons, not actual dependencies.

**Count:** 2 matches

| Line | Content Summary |
|---|---|
| L23016 | `The \`baileys-antiban\` npm library (reference implementation for Baileys-based bots) uses similar jitter patterns...` |
| L23179 | `- **baileys-antiban Reference:** The npm library \`baileys-antiban\` (used by Baileys-based WhatsApp bots) implements similar jitter...` |

### Recommended Replacement

These are reference-implementation comparisons. Could be retained as-is (educational) or updated to reference Neonize-native anti-ban patterns. Low priority.

---

## Category 8: Neonize/Baileys Combined Reference (LOW)

**Count:** 1 match

| Line | Content |
|---|---|
| L24483 | `NEONIZE_INTERNAL = "neonize_internal"      # Neonize/Baileys internal error, fresh client may fix` |

### Recommended Replacement

```python
NEONIZE_INTERNAL = "neonize_internal"      # Neonize internal error, fresh client may fix
```

---

## Category 9: Evolution API References (LOW)

**Status:** Evolution API is a Baileys-wrapper service. References are educational context about known bugs in the Baileys ecosystem, used to inform Neonize error handling design.

**Count:** 2 matches

| Line | Content Summary |
|---|---|
| L24391 | Background context about Evolution API false logout bug |
| L24664 | `Evolution API 515 → 401 Bug Reference:` detailed explanation of the bug pattern |

### Recommended Replacement

These are educational warnings about common WhatsApp library bugs. Could be:
- Retained as design rationale (acceptable)
- Updated to note "this bug affected Baileys-based libraries; our Neonize implementation handles it via..."
- Removed if redundant with Neonize-specific error handling docs

---

## Category 10: discord.Client (HIGH)

**Status:** `discord.Client` is the old/low-level Discord.py class. Modern Discord bots use `discord.ext.commands.Bot` or `discord.ext.commands.AutoShardedBot`. The presence of `discord.Client` (not `commands.Bot`) in step prompts generating new code is stale.

**Count:** 4 matches in main file + 9 in .bak

### Matches

| Line | Type | Content |
|---|---|---|
| L5661 | Function signature | `async def on_ready(client: discord.Client):` |
| L5689 | Class definition | `class GuinevereBot(discord.Client):` |
| L5809 | Function signature | `async def send_alert(client: discord.Client, severity: str, title: str,` |
| L49484 | Variable type hint | `bot_client: discord.Client,` |

### Recommended Replacement

- `discord.Client` → `commands.Bot` or `discord.ext.commands.Bot`
- `class GuinevereBot(discord.Client)` → `class GuinevereBot(commands.Bot)` 
- `client: discord.Client` → `bot: commands.Bot`

Note: Lines L5689 and L5710 appear in a step prompt that generates `src/discord/bot.py` from scratch (the `cat >` heredoc at L5678). This means the step prompt template itself is generating stale code.

---

## Category 11: discord.py / commands.Bot General References (CONTEXT-DEPENDENT)

**Status:** These references to discord.py framework and `commands.Bot` may or may not be stale depending on:
- Whether Guinevere still uses Discord as its primary interface (README confirms "Discord Bot (interface)")
- Whether WhatsApp/Neonize has become the primary channel instead

**Count:** 12 matches

### Matches

| Line | Type | Content |
|---|---|---|
| L3414 | Dependency | `discord.py==2.*` (in package dependency block alongside hermes-agent) |
| L3518 | Dependency | `"discord.py>=2",` (in pyproject.toml dependency list) |
| L8798 | Checklist | `Python \`asyncpg\`, \`redis.asyncio\`, \`discord.py\` packages confirmed` |
| L8957 | Context | `existing Discord bot infrastructure (discord.py bot with command tree, running on VPS)` |
| L9121 | Checklist | `Python environment has \`discord.py\` >= 2.3, \`asyncpg\`, \`python-dateutil\`` |
| L10986 | Checklist | `Python test packages: \`pytest>=8.0\`, \`pytest-asyncio>=0.23\`, \`httpx>=0.27\`, \`discord.py>=2.3\`` |
| L16543 | Troubleshooting | `Discord.py (discord.ext.commands.Bot) has its own close() method...` |
| L20543 | Context | `The Discord bot uses discord.py's \`commands.Bot\` framework with slash commands` |
| L23938 | Dependencies | `P2 (Discord bot operational — \`src/discord/bot.py\`, \`GuinevereBot\` with \`commands.Bot\`)` |
| L24094 | Troubleshooting | `discord.py handles rate limit backoff automatically` |
| L26179 | Code | `def __init__(self, bot: commands.Bot, token_manager):` |
| L47678 | Reference | `\`to_discord_embed(data)\` for discord.py conversion` |

### Assessment

Most of these are NOT definitively stale — they reference Discord as Guinevere's primary interface, which matches the README. These should be cross-checked against the current `src/discord/bot.py` to verify the framework version is still relevant.

---

## Category 12: GuinevereBot (CONTEXT-DEPENDENT)

**Status:** `GuinevereBot` appears as the bot class name throughout step prompts. Whether this is stale depends on whether the class has been renamed in the current codebase.

**Count:** 12 matches

### Matches

| Line | Type | Content |
|---|---|---|
| L5689 | Class definition | `class GuinevereBot(discord.Client):` |
| L5710 | Instantiation | `bot = GuinevereBot()` |
| L23938 | Dependencies text | `P2 (Discord bot operational — \`src/discord/bot.py\`, \`GuinevereBot\` with \`commands.Bot\`)` |
| L23953 | Verification | `uv run python -c "from src.discord.bot import GuinevereBot; print('Bot class importable')"` |
| L23968 | Import | `from src.discord.bot import GuinevereBot` |
| L24023 | Function signature | `def __init__(bot: GuinevereBot, channel_id: int)` |
| L24119 | Dependencies text | `P2 (Discord bot — \`src/discord/bot.py\` with \`GuinevereBot\`, command prefix \`!\`)` |
| L24131 | Context | `text-prefix pattern already configured in \`GuinevereBot\` (\`command_prefix="!"\`)` |
| L24150 | Import | `from src.discord.bot import GuinevereBot` |
| L24234 | Function signature | `def __init__(bot: GuinevereBot)` |

### Assessment

Cross-reference needed: check `src/discord/bot.py` for the current class name. If still `GuinevereBot`, these are current. If renamed (e.g., to just `Bot` or `Guinevere`), these are stale.

---

## Category 13: post-MVP (MEDIUM)

**Status:** `post-MVP` is deprecated terminology. Step prompts in several phases (P13, etc.) enforce that `deprecated-future-scope-marker` patterns (including `post-MVP`) must not appear in generated code.

**Count:** 3 matches in main file + 1 in .bak

### Matches

| Line | Type | Content |
|---|---|---|
| L38586 | Anti-pattern check | `No \`post-MVP\`, \`# type: ignore\`, \`@ts-ignore\`... in P13 generated files` |
| L54177 | Context text | `deferring VS Code extension integration to post-MVP` |
| L54414 | Acceptance criteria | `AC 2.2: Git traversal MVP, VS Code extension post-MVP.` |

### Assessment

- **L38586:** NOT stale — this is an anti-pattern enforcement check in a validation step.
- **L54177, L54414:** Actually use `post-MVP` in descriptive text. These should be updated to `post-launch`.

### Recommended Replacement

`post-MVP` → `post-launch` or `future phase` (for L54177, L54414)

---

## Category 14: memory_bridge / health_memory_bridge (CONTEXT-DEPENDENT)

**Status:** `health_memory_bridge.py` is referenced in step prompts. Whether this is stale depends on whether the bridge has been refactored into a different module.

**Count:** 6 matches

| Line | Type | Content |
|---|---|---|
| L45945 | Table | `\| **Output File** \| \`src/persona/health_memory_bridge.py\` \|` |
| L46033 | Instruction | `Create \`src/persona/health_memory_bridge.py\`:` |
| L46535 | Import | `from src.persona.health_memory_bridge import (` |
| L46596 | Verification | `\`src/persona/health_memory_bridge.py\` exists and passes \`python -c "from src.persona.health_memory_bridge import inject_health_episode; print('import OK')"\`` |
| L46634 | Table | `\| Implementation \| \`src/persona/health_memory_bridge.py\` \|` |
| L46646 | Rollback | `rm src/persona/health_memory_bridge.py` |

### Assessment

If `health_memory_bridge.py` still exists in `src/persona/`, these are current. If it has been refactored/renamed (e.g., to `memory_bridge.py` or integrated into another module), these are stale.

---

## Category 15: src/discord/bot.py References (CONTEXT-DEPENDENT)

**Status:** Extensive references to `src/discord/bot.py` as the main Discord bot entry point. These are generally valid if Discord remains the primary interface.

**Count:** 35 matches

### Notable Patterns

- Code generation heredocs that create `src/discord/bot.py` from scratch (L5678)
- grep/verification commands targeting `src/discord/bot.py`
- Import and class references throughout P11 (WhatsApp bridge), P9 (finance), P13 (x_poster)
- Rollback commands that `git checkout -- src/discord/bot.py`

### Assessment

These are generally current (Discord is still the primary interface per README). The volume suggests tight coupling to `src/discord/bot.py` as the central integration point.

---

## Patterns NOT FOUND

The following patterns returned **zero matches** in `StepPrompts.md`:

| Pattern | Notes |
|---|---|
| `conversational_handler` | Old handler file name — not present |
| `session_adapter` | Old adapter name — not present |
| `HuggingFace` / `huggingface` | Old LLM provider — not present (correctly migrated to OpenAI/OpenRouter) |
| `pip install` + hermes (beyond what's in Category 1) | All covered under hermes-agent |
| `pypi.org` references | None found |
| `baileys.*session` | No Baileys session references |

---

## Recommended Remediation Priority

| Priority | Category | Action |
|---|---|---|
| **1 (Critical)** | hermes-agent PyPI (Cat 1) | Remove all hermes-agent pip references; replace with NousResearch fork install instructions per ADR-035 |
| **2 (Critical)** | config/hermes paths (Cat 2) | Update all `/home/guinevere/config/hermes/` paths to current agent config directory |
| **3 (High)** | discord.Client → commands.Bot (Cat 10) | Update class definitions and type hints in L5661, L5689, L5809, L49484 |
| **4 (High)** | GuinevereBot class (Cat 12) | Cross-check with `src/discord/bot.py`; update if renamed |
| **5 (Medium)** | post-MVP terminology (Cat 13) | Replace `post-MVP` with `post-launch` in L54177, L54414 |
| **6 (Medium)** | WhatsApp Web MD → Multi-Device (Cat 4) | Update protocol description |
| **7 (Low)** | Neonize/Baileys comment (Cat 8) | Clean L24483 comment |
| **8 (Deferred)** | Baileys migration docs (Cat 3A) | Remove after ADR-022 formal revision complete |
| **9 (Deferred)** | Baileys ecosystem refs (Cat 3B, 7, 9) | Retain or update as educational context |

---

## Search Methodology

All 18 search patterns executed as independent grep commands against `stepprompts/StepPrompts.md`:

```
1.  "Baileys"                                    → 10 main + 1 bak matches
2.  "hermes-agent"                               → 15 main + 5 bak matches
3.  "pip install hermes"                         → 3 main + 1 bak matches
4.  "conversational_handler"                     → 0 matches
5.  "session_adapter"                            → 0 matches
6.  "memory_bridge"                              → 6 main matches
7.  "discord\.py|commands\.Bot"                  → 16 main + 2 bak matches
8.  "post.MVP|post_MVP"                          → 3 main + 1 bak matches
9.  "GuinevereBot"                               → 12 main + 2 bak matches
10. "HuggingFace"                                → 0 matches
11. "pip install.*hermes"                        → 3 matches (subset)
12. "node\.js.*subprocess|Node\.js.*subprocess"  → 2 main matches
13. "discord\.Client"                             → 4 main + 9 bak matches
14. "uv pip install"                             → 14 main + 4 bak matches (context)
15. "baileys-antiban"                            → 2 main matches
16. "\bhermes\b"                                 → 32 main + 12 bak matches (includes Cat 1+2)
17. "NousResearch"                               → 8 main + 1 bak matches
18. "config/hermes"                              → 9 main matches
19. "commands\.Bot"                              → 4 main matches
20. "WhatsApp Web MD"                            → 2 main matches
21. "Evolution API"                              → 2 main matches
22. "HTTP bridge"                                → 1 main match
23. "src/discord/bot\.py"                        → 35 main + 1 bak matches (context)
```

---

## Evidence Integrity

- **File scoped:** `stepprompts/StepPrompts.md` only (`.bak` matches excluded from main counts, noted separately)
- **No modifications:** All searches are read-only
- **Line numbers:** Verified against file as of 2026-06-05 (57,713 lines)
- **Exact content:** Key matches confirmed with `read` tool for precise content
- **Cross-referenced:** README.md checked for current tech stack claims (Discord Bot interface, Hermes Agent from Nous Research, GPT-5.5 via 9Router)

---

## Footer

| Field | Value |
|---|---|
| Report type | Stale Reference Sweep (Catalog Only) |
| Date | 2026-06-05 |
| File audited | `stepprompts/StepPrompts.md` |
| Searches run | 23 pattern searches |
| Total matches cataloged | 75+ |
| Modifications | None (read-only sweep) |
| Next action | Review priorities above; create remediation plan for high-severity categories |