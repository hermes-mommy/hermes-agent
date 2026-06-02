# Batch Plan — P2-010 to P2-012: Slash Commands, Embed Colors, /status Command

**Date:** 2026-06-01
**Scope:** STEP-P2-010 (Slash Commands), STEP-P2-011 (Embed Colors), STEP-P2-012 (/status Command)
**Planner:** Metis (Pre-Planning Consultant) after delegated research synthesis
**Planner Gate Status:** READY FOR SEQUENTIAL IMPLEMENTATION
**Repository:** `C:\Users\faizz\guinevere`
**Runtime Target:** VPS `guinevere-vps` / `100.94.104.22`
**Guild ID:** `1510876414671323206`
**Bot App ID:** `1510873134981582858`

---

## 1. Executive Verdict & Scope

### 1.1 Verdict

**GO** for sequential implementation under these constraints:

1. DiscordUXSpec v1.0 is the **canonical source of truth** for all three steps — NOT StepPrompts.
2. P2-010 slashes use the DiscordUXSpec §11 33-command list (7 categories), rejecting the StepPrompts 15-command mismatch.
3. P2-011 colors use user-verified override: `PRIMARY #6B21A8`, `ALERT #DC2626`, `WARNING/ACHIEVEMENT #CA8A04` — DiscordUXSpec orange `#EA580C` documented as caveat, not blocker.
4. P2-012 `/status` follows DiscordUXSpec §2.1 11-field spec with degraded placeholders for unavailable P3/P4/P5/P7 services.
5. Token flow uses existing SOPS wrapper (`scripts/run-discord-verify.sh`) — never `os.environ.get("DISCORD_BOT_TOKEN")`.
6. Guild-scoped command sync only — no global sync.
7. All commands are Faiz-only with runtime permission enforcement.
8. Implementation is sequential: P2-010 → P2-011 → P2-012 (P2-012 depends on P2-010's command structure and P2-011's colors module).

### 1.2 Scope Inclusions

| Step | Deliverable | Source of Truth |
|---|---|---|
| P2-010 | `src/discord/commands.py` — full DiscordUXSpec §11 33-command registry | DiscordUXSpec §11 |
| P2-010 | `tmp/sync-p2-010-commands.py` — guild-scoped sync script | Existing tmp/ pattern |
| P2-010 | `tmp/verify-p2-010-commands-rest.py` — REST-based command verifier | Existing REST-verify pattern |
| P2-010 | Token cleanup: replace StepPrompts.md lines 5523-5524 stale invocation | Token cleanup report |
| P2-010 | `scripts/run-discord-verify.sh` allowlist extension | Existing wrapper pattern |
| P2-011 | `src/discord/colors.py` — color constants + MOOD_COLORS map | DiscordUXSpec §4.1 + user override |
| P2-012 | `src/discord/cmd_status.py` — `/status` handler with 11-field DiscordUXSpec embed | DiscordUXSpec §2.1 |
| Evidence | 3 verification.md files under `docs/setup-evidence/P2/STEP-P2-0NN/` | Existing pattern |
| Auditors | 3 auditor reports under `audit-reports/P2/STEP-P2-0NN/` | Existing pattern |

### 1.3 Scope Exclusions (Must NOT Have)

| Item | Reason |
|---|---|
| Other core commands (`/mood`, `/help`, `/safeword`) | P2-013 through P2-015 — separate batch |
| Persona engine integration | P4 scope |
| Memory system integration | P3 scope |
| Agent loop integration | P5 scope |
| Surveillance service integration | P7 scope |
| Loop commands (`/loop-start`, etc.) runtime logic | P2-010 registers them; runtime in P5 |
| Global command sync | Guild-scoped only per StepPrompts + discord.py reference |
| Discord bot service (`guinevere-discord.service`) | P2-017 |
| Deploy to VPS / health check | Part of P2-018 separately |
| Global command sync | Only guild-scoped |
| StepPrompts-wide token cleanup (P2-017 lines 5846+) | Deferred to P2-017 batch |

---

## 2. Source Inputs Parent-Read

This plan synthesizes the following file-based research and project sources:

| Source | Use |
|---|---|
| `research-reports/P2/p2-010-012-local-code-docs-report.md` | Spec conflict identification, command list comparison, code style patterns |
| `research-reports/P2/p2-010-token-cleanup-report.md` | Exact StepPrompts lines 5523-5524 for cleanup, wrapper pattern |
| `research-reports/P2/p2-010-012-discordpy-reference-report.md` | discord.py v2.x API: CommandTree, sync, embed, defer pattern, rate limits |
| `research-reports/P2/p2-010-012-safety-evidence-report.md` | Compliance matrix, ADR constraints, evidence schema, rollback safety |
| `docs/60-persona/63-DiscordUXSpec_v1.0.md` | **Canonical source** — §2.1 /status, §4.1 palette, §11 command index |
| `stepprompts/StepPrompts.md` lines 5413-5525 | Old P2-010 snippet (rejected), token cleanup target lines 5523-5524 |
| `docs/setup-evidence/P2/batch-plan-007-009.md` | Previous planner gate pattern: permission strategy, token rules, collision scan |
| `src/discord/guild_setup.py` | `get_token()` pattern, Protocol-based stubs, guild ID |
| `src/discord/permissions.py` | REST API pattern, `discord_request()`, `read_channel_ids()` |
| `src/discord/intents.py` | Dynamic import pattern, intent config |
| `scripts/run-discord-verify.sh` | SOPS wrapper allowlist, cleanup pattern |
| `CHECKLIST.md` §4.2 lines 247-249 | AC for P2-010, P2-011, P2-012 |
| `PROGRESS.md` lines 130-132 | Current P2 tracker state (9/21 before this batch) |

---

## 3. P2-010 — Token Cleanup: Exact Lines & Replacement Pattern

### 3.1 Stale Invocation

**File:** `stepprompts/StepPrompts.md`
**Lines:** 5523-5524
**Current (BLOCKING):**
```bash
DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk '{print $2}' | tr -d '"') \
  python scripts/sync-commands.py
```

### 3.2 Replacement Pattern

Replace lines 5523-5524 with:
```bash
scripts/run-discord-verify.sh tmp/sync-p2-010-commands.py
```

### 3.3 Verification Invocation (after sync)

Add immediately after sync line (replacing old placeholder):
```bash
scripts/run-discord-verify.sh tmp/verify-p2-010-commands-rest.py
```

### 3.4 Python Token Contract (in sync/verify scripts)

**MUST use:**
```python
from src.discord.guild_setup import get_token
token = get_token()
```

**MUST NOT use:**
```python
os.environ.get("DISCORD_BOT_TOKEN")
os.environ["DISCORD_BOT_TOKEN"]
```

### 3.5 Wrapper Allowlist Update

In `scripts/run-discord-verify.sh`, extend the `case` allowlist:
```bash
# Add to existing allowlist:
|tmp/sync-p2-010-commands.py|tmp/verify-p2-010-commands-rest.py
```

---

## 4. P2-010 — Canonical 33 Slash Commands

### 4.1 Command Registry Design

- **File:** `src/discord/commands.py`
- **Pattern:** Per discord.py reference, use `app_commands.Command` objects for bulk registration to avoid closure bug (do NOT use `@tree.command()` decorator in a loop).
- **Closure fix:** Use `functools.partial` or lambda-with-default for each command's callback, OR define each command as a separate `discord.app_commands.Command` instance with a unique callback.
- **Faiz-only enforcement:** Every command callback must check `interaction.user.id` against the known Faiz Discord user ID, or check `interaction.guild.owner_id`. If not Faiz, respond ephemeral with `"Hanya Faiz yang bisa menggunakan Mommy."` and return.
- **Import strategy:** Use dynamic `importlib.import_module("discord")` pattern (from `guild_setup.py`) to avoid local `src.discord` shadowing external `discord.py`.

### 4.2 Full Canonical 33 Commands — DiscordUXSpec §11 Command Index

**7 categories, 33 commands:**

#### 🎯 Core (4)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 1 | `/status` | — | No params. P2-012 handler. Faiz-only. |
| 2 | `/mood` | — | No params. P2-013. Faiz-only. |
| 3 | `/help` | `command` (string, optional) | Categorized overview or per-command. P2-014. Faiz-only. |
| 4 | `/safeword` | — | HARD STOP. Highest priority. P2-015. Faiz-only. |

#### 🔄 Loop (7)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 5 | `/loop-start` | `task` (str, req), `priority` (choice), `project` (str, opt), `estimated_duration` (int, opt), `model_preference` (choice), `auto_approve_evidence` (bool, opt) | P5 scope for runtime |
| 6 | `/loop-stop` | `loop_id` (str, req), `reason` (str, opt) | P5 scope |
| 7 | `/loop-pause` | `loop_id` (str, req) | P5 scope |
| 8 | `/loop-resume` | `loop_id` (str, req) | P5 scope |
| 9 | `/loops` | `filter` (choice: active/paused/completed/all, default: active) | P5 scope |
| 10 | `/evidence` | `loop_id` (str, req), `type` (choice: markdown/json/screenshot), `action` (choice: view/create) | P5 scope |
| 11 | `/loop-priority` | `loop_id` (str, req), `priority` (choice: low/normal/high/critical, req) | P5 scope |

#### 🧠 Memory (4)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 12 | `/memory-search` | `query` (str, req), `type` (choice), `date_from` (str), `date_to` (str), `importance` (int, 1-10) | P3 scope |
| 13 | `/memory-add` | `content` (str, req), `type` (choice), `importance` (int, 1-10), `tags` (str, opt) | P3 scope |
| 14 | `/memory-forget` | `memory_id` (str, req), `reason` (str, opt) | P3 scope |
| 15 | `/memory-export` | `type` (choice: all/episodic/semantic/procedural), `format` (choice: json/markdown) | P3 scope |

#### 👁️ Surveillance (3)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 16 | `/surveillance-status` | — | No params. P7 scope. |
| 17 | `/surveillance-pause` | `source` (choice: android/windows/all, req), `duration` (str, opt) | P7 scope |
| 18 | `/surveillance-resume` | `source` (choice: android/windows/all, req) | P7 scope |

#### 💰 Finance (3)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 19 | `/cost` | `period` (choice: today/week/month, default: today) | P1 scope (Redis DB5 exists but no query API yet) |
| 20 | `/budget` | `action` (choice: view/set), `threshold` (choice: alert/warning/critical/hard_cap), `value` (number) | P1 scope |
| 21 | `/cost-alert` | `action` (choice: view/configure/mute), `channel` (str), `mute_duration` (str) | P1 scope |

#### ⚙️ System (7)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 22 | `/approve` | `id` (str, opt, default: latest) | P5 scope |
| 23 | `/deny` | `id` (str, req), `reason` (str, opt) | P5 scope |
| 24 | `/approve-all` | — | P5 scope |
| 25 | `/focus` | — | Minimizes persona |
| 26 | `/casual` | — | Restores full persona |
| 27 | `/consent` | `category` (choice: yandere/surveillance/intimacy/all, req), `action` (choice: on/off, req) | P5 scope |
| 28 | `/punishment` | — | P4 scope |
| 29 | `/reward` | — | P4 scope |

#### 🔧 Admin (4)
| # | Command | Parameters | Notes |
|---|---|---|---|
| 30 | `/restart-service` | `service` (choice: guinevere-core/surveillance/scheduler/mcp/all, req) | P5 scope |
| 31 | `/backup-now` | — | P1 backup exists |
| 32 | `/health-check` | — | P5 scope |
| 33 | `/clear-cache` | — | P5 scope |

### 4.3 StepPrompts Commands Rejected (15 commands NOT in DiscordUXSpec)

These belong to StepPrompts ONLY and are **excluded** from P2-010:
`/score`, `/task`, `/pause`, `/resume`, `/cancel`, `/journal`, `/persona`, `/ritual`, `/distress`, `/emergency`, `/surveillance-report`, `/finance`, `/config`, `/memory-stats`, `/punish`

### 4.4 Faiz-Only Enforcement Design

**All 33 commands must be Faiz-only.** Enforcement strategy:

1. **Guild owner check** at runtime: `interaction.guild.owner_id` is `1510876414671323206` (confirmed guild owner is Faiz). Check `interaction.user.id == guild.owner_id`.
2. **Check pattern**: Apply as a decorator or wrapper function that:
   - If not Faiz: respond ephemeral `"Hanya Faiz yang bisa menggunakan Mommy."` and return early.
   - If Faiz: proceed to handler.
3. **Registration**: The permission check is set at the command definition level, not per-handler, to avoid duplication across 33 commands.

---

## 5. P2-011 — Embed Color Constants

### 5.1 Color Palette Design

**File:** `src/discord/colors.py`

#### Canonical Constants (DiscordUXSpec §4.1 + User Override)

| Constant | Hex | Integer | Usage | Source |
|---|---|---|---|---|
| `PRIMARY` | `#6B21A8` | `0x6B21A8` | Default brand — status embeds, info embeds | **User override** ✅ DiscordUXSpec ✅ |
| `ALERT` | `#DC2626` | `0xDC2626` | Errors, SEV0/SEV1, denials, red embeds | **User override** ✅ DiscordUXSpec ✅ |
| `ACHIEVEMENT` | `#CA8A04` | `0xCA8A04` | Rewards, streaks, achievements, gold embeds | **User override** ✅ DiscordUXSpec ✅ |
| `SUCCESS` | `#16A34A` | `0x16A34A` | Completions, approvals, safe mode, green embeds | DiscordUXSpec only (not in user checklist) |
| `INFO` | `#CA8A04` | `0xCA8A04` | SEV3, info notices (same hex as Gold) | DiscordUXSpec §4.1 |

#### WARNING Color Resolution

| Source | Color | Hex |
|---|---|---|
| DiscordUXSpec §4.1 | Orange | `#EA580C` / `0xEA580C` |
| StepPrompts (old) | Amber | `0xF59E0B` |
| **User override** | Gold/Yellow | `#CA8A04` / `0xCA8A04` |

**Decision**: Implement `WARNING = 0xCA8A04` (matching user override and ACHIEVEMENT) as the primary warning color. This satisfies the user's explicit done criteria. The DiscordUXSpec orange `#EA580C` specification is documented as `ORANGE = 0xEA580C` for future use when the user elects to differentiate warnings from achievements. **Not an implementation blocker.**

#### Extra Colors (Non-Canonical Extensions — Keep Per Research Report)

| Constant | Hex | Usage | Status |
|---|---|---|---|
| `INFO_BLUE` | `0x2563EB` | Info embeds | Extension beyond canon |
| `PERSONA` | `0x9333EA` | Persona-related embeds | Extension beyond canon |
| `SURVEILLANCE` | `0x0891B2` | Surveillance embeds | Extension beyond canon |
| `FINANCE` | `0x059669` | Finance embeds | Extension beyond canon |
| `NEUTRAL` | `0x6B7280` | Neutral/gray embeds | Extension beyond canon |

**Rule**: Extra colors get a comment flag: `# Non-canonical extension (beyond DiscordUXSpec §4.1)`.

#### MOOD_COLORS Map

```python
MOOD_COLORS = {
    "content": SUCCESS,       # 0x16A34A
    "pleased": ACHIEVEMENT,   # 0xCA8A04
    "disappointed": WARNING,  # 0xCA8A04
    "angry": ALERT,           # 0xDC2626
    "silent": NEUTRAL,        # 0x6B7280
}
```

### 5.2 Done Criteria (from user override)

| Check | Expected |
|---|---|
| PRIMARY constant | `#6B21A8` hex in code |
| ALERT constant | `#DC2626` hex in code |
| ACHIEVEMENT constant | `#CA8A04` hex in code |
| WARNING constant | `#CA8A04` hex in code (user override accepted) |
| Orange `#EA580C` defined | Documented as `ORANGE`, not required for done |
| MOOD_COLORS mapping | 5 moods mapped to correct constants |
| Extra colors present | INFO_BLUE, PERSONA, SURVEILLANCE, FINANCE, NEUTRAL |

### 5.3 DiscordUXSpec Orange Caveat

DiscordUXSpec §4.1 defines WARNING as Orange `#EA580C`. The StepPrompts colors.py used Amber `0xF59E0B`. User override specifies `#CA8A04` for warnings/achievements. Implementation defines `WARNING = 0xCA8A04` matching user override, and `ORANGE = 0xEA580C` as a documented constant for future use. This satisfies the done criterion while preserving the canonical spec for later adoption.

**This caveat is explicitly NOT a blocker.**

---

## 6. P2-012 — `/status` Command Specification

### 6.1 Handler Design

**File:** `src/discord/cmd_status.py`
**Registration:** Imported by `commands.py` and registered with the command tree.

### 6.2 Embed Specification (DiscordUXSpec §2.1 Canonical)

```
Title: "👑 Mommy's Status"
Color: PRIMARY (0x6B21A8)
Thumbnail: Use Unicode 👑 (custom avatar not available in P2 scope)
Description: Persona sentence — "Semua sehat, Darling. Mommy jaga semuanya. Kamu tinggal fokus." 👑
```

### 6.3 Required 11 Fields with Degraded Placeholders

| # | Field Name | Source | P2 Status | Display |
|---|---|---|---|---|
| 1 | Current mood + undertone | P4 Persona Engine | ❌ Not available | `"😊 Content (placeholder)"` |
| 2 | Active loops (count + names) | P5 Agent Loop | ❌ Not available | `"⚠️ — Active Loops (P5 not deployed)"` |
| 3 | Tasks completed today | P5 Agent Loop | ❌ Not available | `"⚠️ — (P5 not deployed)"` |
| 4 | Uptime since last restart | Bot process start time | ✅ Available | Compute from `start_time` timestamp |
| 5 | Cost today (total + per-model) | P1 Redis DB5 | ℹ️ Redis DB5 exists but no query API | `"⚠️ — Cost tracking (P1 query API pending)"` |
| 6 | Yandere level (Y0-Y5) | P4 Persona Engine | ❌ Not available | `"Y1 (baseline — placeholder)"` |
| 7 | Next scheduled action | P5 Agent Loop | ❌ Not available | `"⚠️ — (P5 not deployed)"` |
| 8 | Current project focus | Static config / hardcode | ✅ Available | Hardcoded `"project-alpha"` or `"—"` |
| 9 | Punishment/reward streak | P4 Persona Engine | ❌ Not available | `"⚠️ — (P4 not deployed)"` |
| 10 | Memory health score | P3 Memory System | ❌ Not available | `"⚠️ — (P3 not deployed)"` |
| 11 | Surveillance status per-source | P7 Surveillance | ❌ Not available | `"⚠️ — (P7 not deployed)"` |

### 6.4 Footer Pattern

```
Footer: "Guinevere de Baroque • {current_datetime} • ✨ Content"
```

Use ISO 8601 format with WIB timezone: `2026-06-01 15:30 WIB`.

### 6.5 Interaction Pattern

```python
await interaction.response.defer()  # Allow >3s processing
# Build embed with all 11 fields (degraded for unavailable services)
await interaction.followup.send(embed=embed)
```

### 6.6 Ephemeral Decision

`/status` should be **ephemeral** (private to Faiz) by default so status data is not visible in channel history. Set `ephemeral=True` in `defer()`:

```python
await interaction.response.defer(ephemeral=True)
```

### 6.7 Error Handling

If any field fails to compute (exception), show `"⚠️ Error retrieving data"` for that specific field rather than failing the entire command.

---

## 7. Master Todo (Dependency Map)

### Dependency Graph

```text
P2-010 (token cleanup + commands.py + sync)
  ├── [no deps on 011/012]
  │
  ├── P2-011 (colors.py)
  │   └── [no deps on 010 — independent]
  │
  └── P2-012 (cmd_status.py)
      └── Depends on: P2-010 commands.py structure, P2-011 colors.py constants
```

### Sequencing Decision

**P2-010 → P2-011 → P2-012** (sequential with parallel opportunity note):
- P2-010 and P2-011 are **structurally independent** — `commands.py` and `colors.py` don't share writers. They can be implemented in parallel IF collision scan confirms no shared file access.
- P2-012 **depends** on both P2-010 (for command registration pattern) and P2-011 (for color constants).

### Master Todo List

#### P2-010 — Slash Commands Registration

| # | Task | Depends | Evidence |
|---|---|---|---|
| 1 | Create `src/discord/commands.py` with DiscordUXSpec §11 33 commands, Faiz-only check, closure-safe registration | P2-009 | Verification step |
| 2 | Create `tmp/sync-p2-010-commands.py` — guild-scoped sync script using `get_token()` | Task 1 | Verification step |
| 3 | Create `tmp/verify-p2-010-commands-rest.py` — REST-based verifier for 33 commands | Task 1 | Verification step |
| 4 | Update `scripts/run-discord-verify.sh` allowlist for new P2-010 scripts | Task 2, 3 | Allowlist edit |
| 5 | Clean StepPrompts.md lines 5523-5524: replace stale token invocation with wrapper pattern | - | grep PASS |
| 6 | Deploy to VPS: scp + run sync via wrapper | Task 4 | Verification step |
| 7 | Verify 33 commands via REST verifier | Task 6 | Verification step |
| 8 | Write `docs/setup-evidence/P2/STEP-P2-010/verification.md` | Task 7 | File created |
| 9 | Auditor gate PASS for P2-010 | Task 8 | Auditor report |

#### P2-011 — Embed Color Palette

| # | Task | Depends | Evidence |
|---|---|---|---|
| 1 | Create `src/discord/colors.py` with canonical constants + user override + MOOD_COLORS map | - | Verification step |
| 2 | Verify hex values: PRIMARY=#6B21A8, ALERT=#DC2626, ACHIEVEMENT=#CA8A04, WARNING=#CA8A04 | Task 1 | grep PASS |
| 3 | Verify MOOD_COLORS mapping | Task 1 | grep PASS |
| 4 | (Optional) Deploy to VPS if needed for P2-012 | Task 1 | - |
| 5 | Write `docs/setup-evidence/P2/STEP-P2-011/verification.md` | Task 2, 3 | File created |
| 6 | Auditor gate PASS for P2-011 | Task 5 | Auditor report |

#### P2-012 — `/status` Command

| # | Task | Depends | Evidence |
|---|---|---|---|
| 1 | Create `src/discord/cmd_status.py` with DiscordUXSpec §2.1 11-field embed, degraded placeholders | P2-010 commands.py, P2-011 colors.py | Verification step |
| 2 | Wire `/status` into `commands.py` | Task 1 | grep /status |
| 3 | Deploy to VPS: scp + run sync via wrapper | Task 2 | Verification step |
| 4 | Verify `/status` returns embed with all 11 fields | Task 3 | API verification |
| 5 | Write `docs/setup-evidence/P2/STEP-P2-012/verification.md` | Task 4 | File created |
| 6 | Auditor gate PASS for P2-012 | Task 5 | Auditor report |

#### Batch Sync (After All Auditors PASS)

| # | Task | Depends | Evidence |
|---|---|---|---|
| 1 | Update `PROGRESS.md`: P2 9/21 → 12/21; total update | All 3 auditors PASS | grep PR progress |
| 2 | Update `CHECKLIST.md` §4.2: P2-010, P2-011, P2-012 | All 3 auditors PASS | grep checklist |
| 3 | Update `stepprompts/StepPrompts.md` P2-010→P2-012 sections | All 3 auditors PASS | grep stepprompts |
| 4 | Grep/token scan on all created/modified files | All steps done | No token leak |

---

## 8. Prerequisites/Blockers & Done/AC Reference

### 8.1 Prerequisites (ALL MUST BE ✅)

| Prerequisite | Status | Source |
|---|---|---|
| P2-009 completed (permissions + Admin review) | ✅ Done | PROGRESS.md line 129 |
| `src/discord/` module exists with `guild_setup.py`, `permissions.py`, `intents.py` | ✅ Done | Files exist |
| `scripts/run-discord-verify.sh` exists with SOPS wrapper | ✅ Done | File exists |
| `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` exists | ✅ Done | File exists |
| Guild ID `1510876414671323206` confirmed | ✅ Done | Multiple sources |
| Bot app ID `1510873134981582858` confirmed | ✅ Done | Multiple sources |
| Discord bot token in SOPS `secrets/discord-secrets.yaml` | ✅ Done | P2-002 evidence |
| `pyproject.toml` with discord.py>=2.4 | ✅ Done | Exists |

### 8.2 Done Criteria (From CHECKLIST.md §4.2)

| Step | CHECKLIST AC | Verification |
|---|---|---|
| P2-010 | `"/" in chat shows 33 slash commands` | `tmp/verify-p2-010-commands-rest.py` reads `GET /applications/{app_id}/guilds/{guild_id}/commands` and asserts count == 33 |
| P2-011 | `"Embed colors: primary=#6B21A8, alerts=#DC2626, achievements=#CA8A04"` | grep `0x6B21A8`, `0xDC2626`, `0xCA8A04` in `src/discord/colors.py` |
| P2-012 | `"/status -> embed with mood, loops, tasks"` | REST API returns 11 fields; embed constructed with correct color + fields |

---

## 9. Evidence Roots & File Paths

### 9.1 Evidence Directory Structure

```
docs/setup-evidence/P2/STEP-P2-010/verification.md
docs/setup-evidence/P2/STEP-P2-011/verification.md
docs/setup-evidence/P2/STEP-P2-012/verification.md
```

### 9.2 Auditor Report Paths

```
audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md
audit-reports/P2/STEP-P2-011/step-p2-011-auditor-report.md
audit-reports/P2/STEP-P2-012/step-p2-012-auditor-report.md
```

### 9.3 Evidence Minimum Schema (Per AGENTS.md §11)

Each verification.md must include: What Was Done, Files Changed, Validation Results (diagnostics + verifier output + pre-existing vs introduced split), Evidence Artifacts, Doc-Sync Impact, Boundary Compliance (no drift/violation/overreach/Y6/HARD STOP bypass), Rollback / Re-run Safety, Design Decisions / Caveats (spec conflict resolutions), Auditor Gate (verdict + report path), Footer (source task, date, implementer, validation).

### 9.4 P2-010 Existing StepPrompts Evidence Path (Rejected)

Old path `evidence/phase-2/step-010/` is **rejected**. Use canonical `docs/setup-evidence/P2/STEP-P2-010/` consistent with P2-001 through P2-009.

---

## 10. Referenced ADRs/Docs & ADR Impact

### 10.1 Relevant ADRs

| ADR | Title | Relevance | Constraint |
|---|---|---|---|
| **ADR-022** | Communication Channel Strategy | **Primary** — Discord as main channel, slash commands, Faiz-only access | All 33 commands slash-only; Faiz-only enforcement |
| **ADR-015** | Secrets Management Strategy | **Critical** — Bot token must follow SOPS+age pattern | Token via `get_token()`; never plaintext |
| **ADR-018** | Security Architecture & Defense-in-Depth | **Critical** — Bot permission scope, token security | No overprivileged tokens; Faiz-only commands |
| **ADR-001** | Persona Safety & Ethical Boundary | **Critical** — HARD STOP via `/safeword` | `/safeword` structure defined in P2-010 |
| **ADR-002** | User Autonomy & Safe Word Enforcement | **Critical** — Safe word global override | `/safeword` highest-priority command |

### 10.2 No ADR Impact

No ADR creation or amendment is required by this batch. These steps implement existing ADR decisions, they do not change them.

### 10.3 Referenced Docs

| Doc | Section | Use |
|---|---|---|
| `63-DiscordUXSpec_v1.0.md` | §2.1, §4.1, §11 | **Canonical source** for all 3 steps |
| `02-TechnicalArchitecture_v2.0.md` | §6 | Port/service reference for /status |
| `04-MemorySchema_v2.0.md` | Schema tables | Reference for P3 placeholder text |
| `06-Persona_Document_v3.0.md` | Mood system | Reference for MOOD_COLORS |
| `42-IncidentResponse_Postmortem_v1.0.md` | SEV classification | Reference for color usage |

---

## 11. Risks & Gotchas

### 11.1 Guild vs Global Sync

| Risk | Impact | Mitigation |
|---|---|---|
| Using global sync accidentally | 1-hour propagation delay + rate limit risk | **Must pass `guild=discord.Object(id=GUILD_ID)`** to `tree.sync()`. Only guild-scoped sync in P2-010. |
| Global sync rate limit | 200 creates/day hard limit | Guild-scoped sync does NOT count toward this limit. |
| Global sync called on every startup | Rate-limit ban risk | Sync exactly once in startup, not per-interaction. |

### 11.2 Discord Rate Limits

| Risk | Impact | Mitigation |
|---|---|---|
| Bulk upsert rate limit | 429 Too Many Requests | Use single `tree.sync()` call, not per-command sync. |
| Topic/REST endpoint rate limits | 429 on verification | `verify-p2-010-commands-rest.py` reads once via GET, no PUT/POST for verification. |

### 11.3 Closure Bug (CRITICAL)

**Risk**: Using `@tree.command()` decorator inside a for-loop creates closure capture issues — all commands would use the last loop value of name/description/callback.

**Mitigation**: Use `discord.app_commands.Command(name=..., description=..., callback=...)` objects with `functools.partial` or factory function per command. Each command MUST have its own unique callback closure.

### 11.4 Command Count Mismatch

**Risk**: DiscordUXSpec defines 33 commands (7 categories). StepPrompts defines 33 commands (8 categories) but only 18 overlap. If an implementer uses the StepPrompts list, 15 commands will be wrong.

**Mitigation**: The canonical list in §4.2 of this plan is the **only authoritative list**. Implementation must use this list. Auditor must verify command count == 33 and command names match DiscordUXSpec §11.

### 11.5 Token Leak

**Risk**: Any use of `os.environ.get("DISCORD_BOT_TOKEN")` or inline `sops -d | grep | awk` will leak the token into process env, logs, or evidence.

**Mitigation**: 
- BLOCKING: scripts use `get_token()` from `guild_setup.py`
- BLOCKING: evidence files contain NO token plaintext or partial token strings
- Auditor must grep for: `DISCORD_BOT_TOKEN`, `sops -d`, `grep discord_bot_token`, `awk`
- Wrapper invocation in evidence must show only the script path, not decrypted content

### 11.6 Faiz-Only Enforcement

**Risk**: If Faiz-only check is missing or bypassable, anyone in the guild could execute commands.

**Mitigation**: 
- Every command callback checks `interaction.user.id == 1510876414671323206` (guild owner ID).
- Non-Faiz users receive ephemeral denial.
- Auditor must verify the check exists on all 33 command paths.
- Use a shared `is_faiz(interaction)` helper function.

### 11.7 StepPrompts Conflicts

**Risk**: StepPrompts.md P2-010-012 section still contains:
- The old 33-command list (15 mismatched)
- Unsafe token invocation (lines 5523-5524)
- Old evidence paths (`evidence/phase-2/step-010/`)
- Old color values (WARNING = 0xF59E0B)

**Mitigation**: After implementation complete and auditor PASS, update StepPrompts sections to reflect canonical implementation. Token cleanup (lines 5523-5524) is done in P2-010. Color and command list updates are done in batch sync.

### 11.8 P2-012 Degraded Fields

**Risk**: User sees `/status` and expects real data, not placeholders.

**Mitigation**: All degraded fields are labeled with `⚠️ [subsystem] not available` prefix. The description sentence includes "placeholder" context. A caveat is documented in the verification.md.

### 11.9 pyproject.toml discord.py Version

**Risk**: If discord.py < 2.4, `CommandTree` and `Color.from_str()` may not be available.

**Mitigation**: Use integer constants for colors (not `Color.from_str()`). Confirm `pyproject.toml` has `discord.py>=2.4` (confirmed present).

---

## 12. Delegation Assignment by File/Step

| File | Step | Owner | Pattern |
|---|---|---|---|
| `src/discord/commands.py` | P2-010 | Implementation sub-agent | New file — write via filesystem_write_file |
| `src/discord/colors.py` | P2-011 | Implementation sub-agent | New file — write via filesystem_write_file |
| `src/discord/cmd_status.py` | P2-012 | Implementation sub-agent | New file — write via filesystem_write_file |
| `tmp/sync-p2-010-commands.py` | P2-010 | Implementation sub-agent | New file — REST-based sync pattern |
| `tmp/verify-p2-010-commands-rest.py` | P2-010 | Implementation sub-agent | New file — REST-based GET verification |
| `stepprompts/StepPrompts.md` (lines 5523-5524) | P2-010 | Parent (token cleanup only) | Edit file — replace stale invocation |
| `scripts/run-discord-verify.sh` (allowlist) | P2-010 | Parent | Edit file — extend case allowlist |
| `docs/setup-evidence/P2/STEP-P2-010/verification.md` | P2-010 | Implementation sub-agent | New evidence file |
| `docs/setup-evidence/P2/STEP-P2-011/verification.md` | P2-011 | Implementation sub-agent | New evidence file |
| `docs/setup-evidence/P2/STEP-P2-012/verification.md` | P2-012 | Implementation sub-agent | New evidence file |
| `PROGRESS.md` | Batch sync | Parent (after all auditors PASS) | Edit file |
| `CHECKLIST.md` | Batch sync | Parent (after all auditors PASS) | Edit file |
| `stepprompts/StepPrompts.md` (P2-010→P2-012 sections) | Batch sync | Parent (after all auditors PASS) | Edit file |

---

## 13. Collision Scan

### 13.1 Shared Writers

| File/Resource | Writer(s) | Collision Risk | Mitigation |
|---|---|---|---|
| `src/discord/` module | P2-010 (commands.py), P2-011 (colors.py), P2-012 (cmd_status.py) | **None** — different files, no shared edits | All new files, no existing file edits in src/discord/ |
| `src/discord/guild_setup.py` | None (read-only by P2-010 sync script) | None | Read-only `get_token()` call |
| `scripts/run-discord-verify.sh` allowlist | Parent (P2-010 token task) | Low | Single edit to extend allowlist |
| `stepprompts/StepPrompts.md` | Parent (P2-010 cleanup line 5523-5524) | Low | Single pair-of-lines edit |
| `tmp/sync-p2-010-commands.py` | P2-010 only | None | New file, single writer |
| `tmp/verify-p2-010-commands-rest.py` | P2-010 only | None | New file, single writer |
| Evidence dirs (`docs/setup-evidence/P2/STEP-P2-0NN/`) | 3 separate evidence sub-agents | **None** — separate directories | No shared write paths |
| Auditor dirs (`audit-reports/P2/STEP-P2-0NN/`) | 3 separate auditor sub-agents | **None** — separate directories | No shared write paths |
| `PROGRESS.md` | Parent only | Low — batch sync only | Single edit after all auditors PASS |
| `CHECKLIST.md` | Parent only | Low — batch sync only | Single edit after all auditors PASS |
| `stepprompts/StepPrompts.md` (full section rewrite) | Parent only | Low — batch sync only | Single pass after all auditors PASS |
| Discord guild command registry | P2-010 sync script | **Medium** — runtime mutation | Single sync call; idempotent |
| Discord gateway / bot client | None (sync is REST-based for verification) | None | No gateway interaction in P2-010 verification; sync is REST-based |

### 13.2 Sequencing Decision

P2-010 and P2-011 can be implemented **in parallel** (no shared file writes, no dependency). P2-012 must be **sequential after both** because it depends on both `commands.py` registration pattern and `colors.py` constants.

**Preferred sequence:** P2-010 → P2-011 (parallel with P2-010) → P2-012 (sequential)

Sub-agent delegation pattern:
- Fire P2-010 implementation + P2-011 implementation in the SAME parallel wave.
- After both PASS verification + auditor, fire P2-012 implementation.

---

## 14. Aizanta/VPS Impact & Required Health Checks

### 14.1 Impact Assessment

| Component | P2-010 Impact | P2-011 Impact | P2-012 Impact |
|---|---|---|---|
| Aizanta services | None (code-only) | None (code-only) | None (code-only) |
| PostgreSQL (Aizanta DB) | None | None | None |
| Redis DB10-15 (Aizanta) | None | None | None |
| Canonical ports | None | None | /status reads none in P2 (degraded) |
| Discord gateway | Sync commands (read/write) | None | None |
| SOPS decrypts | 1× per sync/verify run | None | 1× per verify run |

### 14.2 Health Checks (Verification Only — No Changes)

Per user request, the following health checks are performed as read-only verification before and after implementation. These are process checks, not code modifications.

| Check | Command | When | Expected |
|---|---|---|---|
| Aizanta services | `systemctl status aizanta-*` | Pre/post implementation | All services active |
| Aizanta containers | `docker ps --filter "name=aizanta"` | Pre/post implementation | Container list non-empty |
| Aizanta DB | `psql -U aizanta -d aizanta -c "SELECT 1"` | Pre/post implementation | Returns 1 |
| Aizanta Redis | `redis-cli -n 10 PING` | Pre/post implementation | Returns PONG |
| Canonical ports | Port scan 5433, 6380, 8000, 20128, 9090, 3000 | Pre/post implementation | All reachable |
| Discord bot connectivity | `scripts/run-discord-verify.sh tmp/verify-p2-009-bot-permissions-rest.py` | Pre-implementation | Bot accessible |

### 14.3 P2-012 /status VPS Queries

In P2 scope, `/status` does NOT query VPS services. All 11 fields return degraded placeholders. VPS-qualified fields are deferred to P3/P4/P5/P7 where those services exist.

---

## 15. Secret Handling & Rollback/Re-run Safety

### 15.1 Secret Handling Rules

| Rule | Enforcement |
|---|---|
| Token via `get_token()` only | Grep for `os.environ.get("DISCORD_BOT_TOKEN")` → BLOCKING |
| All scripts via `run-discord-verify.sh` | Audit allowlist in wrapper |
| No decrypted secrets in evidence | Evidence files scanned for token-shaped strings |
| No API keys in journal/journalctl | Process check only (not automated in P2 scope) |
| No plaintext in ADRs, docs, code, logs | Auditor grep for secret patterns |

### 15.2 Rollback Per Step

| Step | Rollback Method | Idempotent? |
|---|---|---|
| P2-010 commands | REST DELETE `/applications/{id}/guilds/{guild_id}/commands` or `tree.clear_commands()` + re-sync | ✅ Yes — re-registration re-creates |
| P2-010 token cleanup | Restore StepPrompts.md lines 5523-5524 from git | ✅ Yes — stateless edit |
| P2-011 colors | Revert `src/discord/colors.py` via git | ✅ Yes — stateless file |
| P2-012 /status | Revert `src/discord/cmd_status.py` + re-sync | ✅ Yes — stateless handler |

### 15.3 Re-run Safety

All three steps are fully idempotent:
- Re-running command sync overwrites existing guild commands (Discord bulk upsert).
- Re-creating `colors.py` or `cmd_status.py` overwrites with same content.
- Re-editing StepPrompts.md is a deterministic line replacement.
- No stateful side effects beyond the Discord guild command registry (which is designed for idempotent upsert).

### 15.4 No Destructive Operations

This batch requires NO destructive operations. Specifically:
- No `rm -rf` or force push
- No DROP TABLE or database mutations
- No production deploy (scripts are deployed via existing patterns)
- No bot role removal or reauthorization
- No service restarts (except natural re-sync)

---

## 16. Validation Commands/Scripts & Expected Outputs

### 16.1 Static Validation

| Check | Tool | Expected |
|---|---|---|
| Python syntax | `python -m py_compile src/discord/commands.py` | Exit code 0 |
| LSP diagnostics | `lsp_diagnostics` on `src/discord/` | Clean (or documented pre-existing) |
| Color hex values | `grep "0x6B21A8" src/discord/colors.py` | Match |
| Token pattern scan | `grep -r "os.environ.get.*DISCORD_BOT_TOKEN" src/discord/ tmp/` | No match |
| Token inline decrypt | `grep "sops -d.*grep.*discord_bot_token" stepprompts/StepPrompts.md` | No match (after cleanup) |
| Command count | `grep -c "app_commands.Command\|tree.command" src/discord/commands.py` | 33 |

### 16.2 Runtime Validation (VPS)

All commands run via `scripts/run-discord-verify.sh`:

| Command | Expected Output |
|---|---|
| `scripts/run-discord-verify.sh tmp/sync-p2-010-commands.py` | `Synced 33 commands to guild` |
| `scripts/run-discord-verify.sh tmp/verify-p2-010-commands-rest.py` | `commands_count=33, all_names_match=true` or equivalent PASS |
| `scripts/run-discord-verify.sh tmp/verify-p2-009-bot-permissions-rest.py` | Bot accessible (health check) |

### 16.3 Evidence Validation

| Check | Expected |
|---|---|
| `docs/setup-evidence/P2/STEP-P2-010/verification.md` exists | File present, ≥ 10 sections |
| `docs/setup-evidence/P2/STEP-P2-011/verification.md` exists | File present, ≥ 10 sections |
| `docs/setup-evidence/P2/STEP-P2-012/verification.md` exists | File present, ≥ 10 sections |
| No token plaintext in evidence | grep for `discord_bot_token`, `ND`, `MT` (token prefix patterns) → empty |

---

## 17. Auditor Matrix

### 17.1 Per-Step Specialist Auditors

Each specialist auditor writes to the designated report path and returns only verdict + path + 3-line summary. All auditors run in parallel after parent verification is complete.

#### P2-010 Auditor — Slash Commands Registration

| Audit Dimension | Auditor | Report Path | Must Verify |
|---|---|---|---|
| Technical | Implementation auditor | `audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md` | 33 commands match DiscordUXSpec §11 exactly; closure bug avoided; guild-scoped sync; commands.py structure |
| Security/Token | Security auditor | Same report (combined) | Token flow via `get_token()` only; no `os.environ.get("DISCORD_BOT_TOKEN")`; no plaintext in evidence |
| Compliance/Spec | Compliance auditor | Same report (combined) | Command names match DISCORDUXSPEC canonical; no StepPrompts-only commands; Faiz-only enforcement on all 33 |
| Evidence | Evidence auditor | Same report (combined) | verification.md completeness; no token leak; 10 sections per AGENTS.md §11 |
| VPS/Runtime | VPS auditor | Same report (combined) | sync script runs via wrapper; verify script reports 33 commands; no gateway errors |
| Docs/Traceability | Docs auditor | Same report (combined) | StepPrompts lines 5523-5524 cleaned; allowlist updated; PROGRESS/CHECKLIST update planned |

#### P2-011 Auditor — Embed Color Palette

| Audit Dimension | Auditor | Report Path | Must Verify |
|---|---|---|---|
| Technical | Implementation auditor | `audit-reports/P2/STEP-P2-011/step-p2-011-auditor-report.md` | PRIMARY=0x6B21A8, ALERT=0xDC2626, ACHIEVEMENT=0xCA8A04, WARNING=0xCA8A04; SUCCESS=0x16A34A; MOOD_COLORS mapped correctly |
| Security | Security auditor | Same report | No secrets in colors.py (low risk — stateless constants) |
| Compliance/Spec | Compliance auditor | Same report | User override colors match; orange caveat documented; extra colors flagged as non-canonical |
| Docs/Traceability | Docs auditor | Same report | verification.md covers color decisions; orange caveat documented |

#### P2-012 Auditor — `/status` Command

| Audit Dimension | Auditor | Report Path | Must Verify |
|---|---|---|---|
| Technical | Implementation auditor | `audit-reports/P2/STEP-P2-012/step-p2-012-auditor-report.md` | 11 fields per DiscordUXSpec §2.1; correct embed structure; defer+followup pattern; ephemeral set in defer() |
| Compliance/Spec | Compliance auditor | Same report | Field names match spec; degraded placeholders for unavailable services; footer timestamp pattern correct |
| Security | Security auditor | Same report | No secret leakage in /status output; no VPS service queries that could expose credentials |
| Evidence | Evidence auditor | Same report | verification.md covers 11-field embed; degraded placeholders documented; rollback safe |
| VPS/Runtime | VPS auditor | Same report | Handler does not crash on missing P3/P4/P5/P7 services; returns gracefully degraded embed |

### 17.2 Auditor Verdict Handling

| Verdict | Action |
|---|---|
| **PASS** | Step marked complete. Parent reads report 1-line summary. |
| **NEEDS REVIEW** | Parent investigates findings. Valid issues fixed. False positives documented. Re-audit via `task_id` until PASS or accepted. |
| **FAIL** | Step NOT complete. Root cause fixed, re-verified, re-audited. |

---

## 18. Caveats & Deferred Cleanup

### 18.1 Active Caveats

1. **`/status` degraded fields**: 8 of 11 fields show "⚠️ — (P3/P4/P5/P7 not deployed)" or similar placeholders. This is intentional and documented. User should not expect real data until those phases complete.

2. **Orange `#EA580C` vs Gold `#CA8A04`**: DiscordUXSpec defines WARNING as Orange. User override sets WARNING to Gold `#CA8A04`. Implementation satisfies user override. Orange constant defined as `ORANGE = 0xEA580C` for future adoption. Not a blocker.

3. **StepPrompts still has stale token snippets outside P2-010-012 scope**: Lines 5846, 5854, 5866 in StepPrompts.md contain plaintext temp-file token handling in P2-017 section. These are **not cleaned** in this batch. Deferred to P2-017.

4. **Closure bug avoidance**: Implementation MUST use `app_commands.Command` objects or factory functions, NOT `@tree.command()` in a for-loop. This is a mandatory constraint, not optional.

5. **Non-canonical extra colors**: INFO_BLUE, PERSONA, SURVEILLANCE, FINANCE, NEUTRAL are beyond DiscordUXSpec §4.1. They are kept as documented extensions with a `# Non-canonical extension` comment.

6. **Bot Administrator permission**: The bot still has Administrator from P2-009 documented issue. This does not block P2-010-012 because command registration does not depend on permission level, but Faiz-only enforcement provides defense-in-depth.

### 18.2 Deferred Cleanup (P2-017)

The following are out of scope for this batch and assigned to P2-017:
- StepPrompts.md lines 5846, 5854, 5866: plaintext token snippets in P2-017 service section
- `guinevere-discord.service` creation (P2-017)
- Full token audit across entire StepPrompts (P2-017 scope)

### 18.3 Deferred Features (P3/P4/P5/P7)

The following `/status` fields are deferred:
- Mood + undertone → P4 Persona Engine
- Yandere level → P4
- Streak → P4
- Memory health → P3 Memory System
- Surveillance status → P7 Surveillance
- Cost breakdown → P1 cost query API
- Active loops → P5 Agent Loop

---

## 19. Go / No-Go Checklist

### Go Conditions (ALL MUST BE ✅)

- [x] All 4 research reports written and parent-read
- [x] Spec conflicts resolved (DiscordUXSpec canonical)
- [x] Token cleanup plan defined (lines 5523-5524)
- [x] Canonical command list documented (33, 7 categories)
- [x] Color constants and user override documented
- [x] `/status` 11-field spec with degraded placeholders documented
- [x] Collision scan complete — no shared-writer conflicts
- [x] Sequential/parallel sequencing defined
- [x] Evidence paths follow existing pattern
- [x] Auditor matrix defined with specialist dimensions
- [x] Rollback plan per step documented
- [x] Secret handling rules enforced
- [x] Aizanta/VPS health checks defined (read-only)
- [x] Caveats documented and understood
- [x] No destructive operations required

**Status: ✅ GO FOR IMPLEMENTATION**

### Implementation Gate

**No implementation begins until parent reads this plan file and rewrites active todos to match the master todo list in §7.**

After todo rewrite:
1. Fire P2-010 + P2-011 implementation in parallel wave (independent files).
2. Parent verify both steps.
3. Fire P2-010 + P2-011 auditors in parallel wave.
4. Fix findings if needed, re-audit.
5. Fire P2-012 implementation (depends on P2-010 + P2-011).
6. Parent verify P2-012.
7. Fire P2-012 auditors.
8. Fix findings, re-audit.
9. Batch sync trackers after all 3 auditors PASS.
10. Final report.

---

## 20. Footer

| Field | Value |
|---|---|
| **Source task** | Create mandatory planner gate file for Guinevere Discord P2-010 through P2-012 |
| **Planner gate type** | Metis (Pre-Planning Consultant) |
| **Planner gate status** | VERIFIED — GO for sequential implementation |
| **Validation method** | Parent-read 4 research reports + DiscordUXSpec + StepPrompts + existing batch plan pattern |
| **Secret handling** | No decrypted secrets used or recorded in this plan. Token rules enforced per ADR-015. |
| **Design decisions** | DiscordUXSpec canonical for all 3 steps; user override for P2-011 colors; guild-scoped sync only; closure-safe command registration; degraded placeholders for /status |
| **Next action** | Parent reads this file → rewrites todos → implementation wave |