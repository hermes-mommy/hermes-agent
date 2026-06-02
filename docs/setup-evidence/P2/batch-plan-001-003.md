# P2 Batch Implementation Plan — P2-001 → P2-002 → P2-003

| Field | Value |
|-------|-------|
| **Plan ID** | BATCH-P2-001-003 |
| **Date** | 2026-06-01 |
| **Author** | Guinevere (parent, planner) |
| **Status** | PLAN — ready for parent read and sequential execution |
| **Scope** | P2-001 (Discord application verification), P2-002 (bot token SOPS verification), P2-003 (bot intents code + pyproject.toml) |

---

## 1. Task Overview

Create the first three P2 steps for Guinevere's Discord bot foundation. P2-001 and P2-002 are **already materially completed** by P2 precondition C3 resolution — the Discord app exists, token is SOPS-encrypted, and API-validated. Implementation for those steps is **verify/formalize**, not recreate. P2-003 is the first actual code step: add `discord.py>=2.4` to `pyproject.toml` and create `src/discord/intents.py` with typed intents configuration.

### Execution Order

**Sequential only** — no parallel implementation:
1. P2-001 → Verify Discord application, create evidence
2. P2-002 → Verify token SOPS storage, create evidence
3. P2-003 → Add discord.py dependency, create intents.py, verify

Each step requires:
- Evidence file at per-step path (12-section schema per AGENTS.md Appendix B)
- Auditor report at per-step path
- Verification / lsp_diagnostics
- Tracker sync (PROGRESS.md + CHECKLIST.md owned by parent after all 3 steps pass audit)

---

## 2. Research Inputs (Cited by Path)

All reports were read and synthesized by the parent before writing this plan:

| # | Report | Key Findings Used |
|---|--------|-------------------|
| 1 | `research-reports/P2/discord-py-2-app-commands.md` | Application ID auto-resolution, `setup_hook` sync pattern, `Client(application_id=...)` in v2.4, guild sync strategy |
| 2 | `research-reports/P2/discord-intents-token-security.md` | Privileged intents (MESSAGE_CONTENT, GUILD_MEMBERS, PRESENCES), SOPS+age pattern, logging redaction, fail-fast token validation |
| 3 | `research-reports/P2/discord-py-cogs-slash-examples.md` | `commands.Bot` subclass + `setup_hook` canon pattern, extension loading, sync decision matrix |
| 4 | `research-reports/P2/local-discord-state-pre-p2.md` | Discord app identity (app ID, public key, intents), two-secrets-file warning, "% mismatch, PROGRESS.md state, Hermes config intent names |
| 5 | `research-reports/P2/source-structure-discord-pre-p2.md` | `src/discord/` is empty stub, code conventions (structlog, typed, async), discord.py missing from pyproject.toml but installed in VPS venv |
| 6 | `research-reports/P2/vps-discord-readiness-pre-p2.md` | VPS GREEN (all services healthy), SOPS decrypt PASS, token API validated, canonical ports verified, Aizanta isolated |

---

## 3. Known State (Exact Values)

| Field | Value |
|-------|-------|
| Application name | Guinevere |
| Application ID | `1510873134981582858` |
| Public key | `79b547efa507dbc38b6cb03a7ce8ea089ee4646bace5231ceace1c7ca07cd430` |
| Bot username | Guinevere |
| Server | Guinevere Lab |
| Gateway intents (Portal) | Presence, Server Members, Message Content |
| OAuth scopes | `bot`, `applications.commands` |
| Permissions | Administrator (private server, Faiz-approved) |
| VPS secret file | `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` (1792B, chmod 600, SOPS-encrypted) |
| VPS age key | `/home/guinevere/secrets/age-key.txt` (189B, chmod 600) |
| SOPS version | 3.9.4 |
| age version | 1.1.1 |
| Discord Python status | NOT in `pyproject.toml` but installed in VPS `.venv` as `discord-py==2.4.0` |
| Aizanta isolation | Ports verified: PostgreSQL=5433, PgBouncer=5434, Redis=6380, 9Router=20128 — all canonical, no Aizanta collision |
| Server name mismatch | Actual: "Guinevere Lab", DiscordUXSpec v1.0 says "Guinevere's Domain" — deferred to P2-004 |

---

## 4. Collision Scan & Shared Writers

### Files to CREATE (zero collision)

| File | Owner | Step |
|------|-------|------|
| `docs/setup-evidence/P2/STEP-P2-001/verification.md` | Parent | P2-001 |
| `docs/setup-evidence/P2/STEP-P2-002/verification.md` | Parent | P2-002 |
| `docs/setup-evidence/P2/STEP-P2-003/verification.md` | Parent | P2-003 |
| `src/discord/intents.py` | P2-003 implementer | P2-003 |
| `audit-reports/P2/STEP-P2-001/step-p2-001-auditor-report.md` | Auditor | After P2-001 |
| `audit-reports/P2/STEP-P2-002/step-p2-002-auditor-report.md` | Auditor | After P2-002 |
| `audit-reports/P2/STEP-P2-003/step-p2-003-auditor-report.md` | Auditor | After P2-003 |

### Files to MODIFY (parent-owned, sequenced)

| File | Change | Owner |
|------|--------|-------|
| `pyproject.toml` | Add `discord.py>=2.4` to `[project] dependencies` | P2-003 implementer |
| `PROGRESS.md` | P2 0/21 → 3/21, total 50/257 → 53/257 (20.6%) | Parent (after all 3 pass audit) |
| `CHECKLIST.md` | Mark P2-001, P2-002, P2-003 complete in §4.2 | Parent (after all 3 pass audit) |

### Collision Verdict

✅ **CLEAR** — No shared writers. All created files are independent. PROGRESS/CHECKLIST are parent-owned and sequenced after all 3 steps pass audit. No other agent is writing to `src/discord/`.

**No parallel implementation** — sequential execution required per step dependency: P2-001 evidence → P2-002 evidence → P2-003 code.

---

## 5. P2-001 — Discord Application Verification

### Status

**Already materially completed** by P2 precondition C3 resolution. The Discord application was manually created by Faiz at developer.discord.com, the token was captured via `/tmp/capture-discord-token.sh`, and API verification with `curl https://discord.com/api/v10/users/@me` confirmed `bot_id=1510873134981582858`, `bot_username=Guinevere`.

### Implementation Plan

No code changes. Create evidence file only.

**Step 1: Create evidence directory**
```
docs/setup-evidence/P2/STEP-P2-001/
```

**Step 2: Write evidence to `docs/setup-evidence/P2/STEP-P2-001/verification.md`**
12 sections per AGENTS.md Appendix B:
1. **What Was Done** — P2 precondition C3 already resolved Discord app existence. This step formalizes verification. Confirm app ID, public key, bot username, intents, scopes, permissions.
2. **Files Changed** — None (evidence only)
3. **Validation Results** — Check all known-state fields match:
   - `docs/setup-evidence/P1/p2-preconditions-resolved.md` confirms app ID, public key, server
   - VPS `verify-discord-secret.sh` confirmed API: `discord_api=ok`, `bot_id=1510873134981582858`, `matches_application_id=yes`
   - `ss -tlnp | grep -E '(5433|5434|6380|20128)'` confirms canonical ports (Aizanta isolation)
4. **Evidence Artifacts** — This file, plus referenced P1 preconditions evidence and VPS readiness report
5. **Doc-Sync Impact** — PROGRESS.md: P2 1/21; CHECKLIST.md: P2-001 [x]
6. **Boundary Compliance** — No persona drift, no consent violation, no surveillance overreach, no Y6, no HARD STOP bypass, no secrets in evidence
7. **Rollback / Re-run Safety** — Fully idempotent (read-only verification)
8. **Design Decisions** — Administrator permission conflicts with minimal-permission security docs but is Faiz-approved for private server
9. **Auditor Gate** — Report path noted
10. **Footer** — Source task, date, implementer, validation method

**Step 3: Verify with static checks**
- `glob` confirms evidence file exists
- Confirm no secrets in evidence file (grep for token patterns)
- Confirm no `as any` / `# type: ignore` / empty catch (N/A — no code change)

### Verification Commands
```bash
# Check evidence file exists
Test-Path -LiteralPath "docs/setup-evidence/P2/STEP-P2-001/verification.md"

# Check no secrets leaked in evidence
Select-String -Path "docs/setup-evidence/P2/STEP-P2-001/verification.md" `
  -Pattern "[MN][A-Za-z0-9_-]{23,25}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}"

# Check evidence has all 12 sections
Select-String -Path "docs/setup-evidence/P2/STEP-P2-001/verification.md" `
  -Pattern "^## " | ForEach-Object { $_.Line }
```

### Default DiscordUXSpec Mismatches (Document, Don't Fix)
- Server name: "Guinevere Lab" (actual) vs "Guinevere's Domain" (DiscordUXSpec v1.0 L43) — **deferred to P2-004**
- DiscordUXSpec stale Y1/Ollama references — **out of P2-001 scope**
- Command count: 33 (actual) vs 34 (DiscordUXSpec §2) — **deferred to P2-010**

### Evidence Output Path
`docs/setup-evidence/P2/STEP-P2-001/verification.md`

### Auditor Report Path
`audit-reports/P2/STEP-P2-001/step-p2-001-auditor-report.md`

---

## 6. P2-002 — Bot Token SOPS Storage Verification

### Status

**Already materially completed** by P2 precondition C3 resolution. The bot token was captured via `/tmp/capture-discord-token.sh` (hidden input, shred temp files), SOPS-encrypted to `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` (chmod 600), and verified via `verify-discord-secret.sh` (decrypt PASS, API validation PASS).

### Implementation Plan

No code changes. Create evidence file only.

**Step 1: Create evidence directory**
```
docs/setup-evidence/P2/STEP-P2-002/
```

**Step 2: Write evidence to `docs/setup-evidence/P2/STEP-P2-002/verification.md`**
12 sections:
1. **What Was Done** — Token captured via secure script (hidden read, shred, umask 077), SOPS-encrypted to VPS secrets file, verified with decrypt test and Discord API curl. This step formalizes verification.
2. **Files Changed** — None locally (VPS-only file attestation)
3. **Validation Results** — Confirm:
   - VPS secret file exists at `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` (1792B, chmod 600)
   - Age key exists at `/home/guinevere/secrets/age-key.txt` (189B, chmod 600)
   - SOPS decrypt exit code 0 with 257 bytes plaintext
   - All fields present: `discord_bot_token`, `discord_application_id`, `discord_public_key`, `discord_guild_name`
   - Discord API /users/@me returns 200, `bot_id=1510873134981582858`, `bot_username=Guinevere`
   - `.sops.yaml` rules match `secrets/.*\.yaml$`
   - Two-secrets-file drift risk documented (`guinevere-secrets.yaml` local vs `discord-secrets.yaml` VPS)
4. **Evidence Artifacts** — This file, VPS readiness report, P2 preconditions evidence
5. **Doc-Sync Impact** — PROGRESS.md: P2 2/21; CHECKLIST.md: P2-002 [x]
6. **Boundary Compliance** — No secrets in evidence (token value never written), no persona drift, no consent violation
7. **Rollback / Re-run Safety** — Fully idempotent (read-only verification). Token rotation documented in caveats.
8. **Design Decisions** — Shell scripts used by C3 are P2-specific temp tools; P2-017 will create proper systemd service with SOPS decrypt built in
9. **Auditor Gate** — Report path noted
10. **Footer** — Source task, date, implementer, validation method

**Step 3: Static verification**
- Evidence file exists
- No token pattern in evidence
- `.sops.yaml` rule coverage confirmed

### ⚠️ SECURITY CORRECTION — P2-002 StepPrompts Unsafe Pattern

The original StepPrompts for P2-002 contain unsafe shell token handling that **MUST NOT be used**:
- Partial token print to stdout during debugging
- Temp file with token value exposed longer than necessary

**Correct pattern for any token operations on VPS:**
```bash
# ✅ SAFE — Use SOPS decrypt only on VPS
export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt
# Parse fields without printing secret values
DISCORD_TOKEN=$(sops -d /home/guinevere/code/guinevere/secrets/discord-secrets.yaml \
  --extract '["discord_bot_token"]')
# Use token immediately, unset after use
unset DISCORD_TOKEN
# Shred any temp files immediately
shred -u /tmp/discord-token-* 2>/dev/null || true
```

**Rules for P2-002 and all future token operations:**
1. Never echo/print the token value (even partial, even to `/dev/null`)
2. Never write token to a file that persists beyond immediate use
3. Always `unset` token variables after use
4. Always `shred -u` temp files before deletion
5. Never log token length or first N characters

### Verification Commands
```bash
# Check evidence file exists
Test-Path -LiteralPath "docs/setup-evidence/P2/STEP-P2-002/verification.md"

# Check no token pattern leaked
Select-String -Path "docs/setup-evidence/P2/STEP-P2-002/verification.md" `
  -Pattern "[MN][A-Za-z0-9_-]{23,25}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}"

# Check evidence has all 12 sections
Select-String -Path "docs/setup-evidence/P2/STEP-P2-002/verification.md" `
  -Pattern "^## " | ForEach-Object { $_.Line }
```

### Evidence Output Path
`docs/setup-evidence/P2/STEP-P2-002/verification.md`

### Auditor Report Path
`audit-reports/P2/STEP-P2-002/step-p2-002-auditor-report.md`

---

## 7. P2-003 — Bot Intents Code + pyproject.toml

### Status

This is the **first actual code step** in P2. `discord.py>=2.4` is missing from `pyproject.toml` but IS installed in the VPS `.venv` (`discord-py==2.4.0`). `src/discord/` contains only a 1-line `__init__.py` stub. Hermes config at `/home/guinevere/config/hermes/config.yaml` already has intents shorthand: `['messages','guilds','members','message_content']`.

### Implementation Plan

**File A: Modify `pyproject.toml`** — Add `discord.py>=2.4` to dependencies

**Change:**
```toml
dependencies = [
    ...
    "discord.py>=2.4",
    ...
]
```

Insert after `"cryptography>=44",` (line 21) to maintain alphabetical order.

**File B: Create `src/discord/intents.py`**

```python
"""Discord bot gateway intents configuration for Guinevere.

Provides a typed get_intents() factory returning a discord.Intents object
with intents enabled per the Guinevere Discord integration requirements.

Requires discord.py >= 2.4.
"""
import discord
import structlog

logger = structlog.get_logger()


def get_intents() -> discord.Intents:
    """Return Guinevere's configured gateway intents.

    Enabled intents (matching Discord Developer Portal settings):
    - guilds, members, presences (privileged)
    - message_content (privileged)
    - messages, reactions, voice_states

    Returns:
        discord.Intents object with all required intents enabled.
    """
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.presences = True
    intents.messages = True
    intents.reactions = True
    intents.voice_states = True
    return intents


def validate_intents(intents: discord.Intents) -> bool:
    """Verify that all required intents are enabled.

    Checks the intents that Guinevere requires at minimum:
    guilds, members, message_content, messages, reactions.

    Args:
        intents: The discord.Intents object to validate.

    Returns:
        True if all required intents are present; False otherwise.
    """
    required = {
        "guilds": intents.guilds,
        "members": intents.members,
        "message_content": intents.message_content,
        "messages": intents.messages,
        "reactions": intents.reactions,
    }
    missing = [name for name, enabled in required.items() if not enabled]
    if missing:
        logger.warning("intents_validation_failed", missing=missing)
        return False
    logger.info("intents_validation_passed", enabled=list(required.keys()))
    return True
```

**Design decisions:**
- Use `discord.Intents.default()` as base (includes guilds, messages, reactions, voice_states already)
- Explicitly enable privileged intents: `message_content`, `members`, `presences`
- Include `validate_intents()` helper for runtime verification without overengineering — returns bool, logs result, caller decides whether to exit or warn
- Follow existing code conventions: `structlog.get_logger()` at module level, strict typing, no `if __name__`, no type ignores
- Caller pattern (future): `from src.discord.intents import get_intents, validate_intents`
- Uses discord.py >= 2.4 API; `Intents` attributes are stable since 2.0

### Verification Commands

```bash
# 1. LSP diagnostics on changed files
# (lsp_diagnostics on src/discord/intents.py — should be clean)

# 2. Check pyproject.toml has discord.py>=2.4
Select-String -Path "pyproject.toml" -Pattern "discord.py"

# 3. Python import test (if Python 3.12 + discord.py available locally)
# python -c "from src.discord.intents import get_intents, validate_intents; print('OK')"
```

### Evidence Output Path
`docs/setup-evidence/P2/STEP-P2-003/verification.md`

### Auditor Report Path
`audit-reports/P2/STEP-P2-003/step-p2-003-auditor-report.md`

---

## 8. Tracker Sync Plan (Parent-Owned, After All 3 Steps Pass Audit)

After all three steps pass their respective auditor gates:

### PROGRESS.md Changes

| Section | Before | After |
|---------|--------|-------|
| P2 total steps | 0/21 | **3/21** |
| Total completed | 50/257 (19.5%) | **53/257 (20.6%)** |
| P2-001 | ⏳ Not Started | ✅ Complete |
| P2-002 | ⏳ Not Started | ✅ Complete |
| P2-003 | ⏳ Not Started | ✅ Complete |
| Last Updated | P1-021 date | Current date |

### CHECKLIST.md Changes (§4.2 Step Verification)

| Item | Before | After |
|------|--------|-------|
| P2-001 | [ ] unchecked | [x] checked |
| P2-002 | [ ] unchecked | [x] checked |
| P2-003 | [ ] unchecked | [x] checked |

---

## 9. Security Constraints

### Token Handling (P2-002, all future steps)

| Rule | Enforced |
|------|----------|
| Token never hardcoded in Python files | ✅ Via SOPS + env var |
| Fail-fast on missing DISCORD_TOKEN | ✅ `os.environ["DISCORD_TOKEN"]` raises KeyError |
| No `.env` committed to Git | ✅ `.gitignore` verified |
| SOPS decrypt on VPS only | ✅ Age key is VPS-only (`/home/guinevere/secrets/age-key.txt`) |
| No token in logs | ✅ `SensitiveDataFilter` logging filter recommended |
| No partial token print | ✅ BLOCKING — never print even first N chars |
| Shred temp files | ✅ `shred -u` before deletion |
| Unset after use | ✅ `unset DISCORD_TOKEN` after `client.run()` |

### Logging Redaction

For P2-003 code, discording logging follows this pattern:
```python
# ✅ GOOD — log existence only, never value
logger.info("bot_token_loaded", status="ok")  # NOT "token=xxx"
logger.info("intents_configured", enabled=enabled_intent_list)
```

A `SensitiveDataFilter` class (pattern from `research-reports/P2/discord-intents-token-security.md` §6.2) should be considered for the Discord bot logger in P2-017.

### Two-Secrets-File Drift Risk

| File | Location | Keys | Last Updated |
|------|----------|------|-------------|
| `secrets/guinevere-secrets.yaml` | Local + VPS repo | `discord.bot_token`, `discord.application_id` | 2026-05-31 |
| `secrets/discord-secrets.yaml` | VPS only (not in repo) | `discord_bot_token`, `discord_application_id`, `discord_public_key`, `discord_guild_name` | 2026-06-01 |

**Risk**: If tokens are rotated, both files must be updated. The VPS-only `discord-secrets.yaml` has more fields. Consider adding `discord_public_key` to `guinevere-secrets.yaml` for parity in a future step.

---

## 10. Aizanta Isolation Verification

All Aizanta services are independent of Guinevere Discord work:

| Check | Expected | Status (from VPS readiness) |
|-------|----------|----------------------------|
| PostgreSQL port | `127.0.0.1:5433` (Guinevere) vs `127.0.0.1:5432` (Aizanta) | ✅ CLEAR |
| PgBouncer port | `127.0.0.1:5434` | ✅ CLEAR |
| Redis port | `127.0.0.1:6380` (Guinevere) vs `127.0.0.1:6379` (Aizanta) | ✅ CLEAR |
| 9Router LLM proxy | `0.0.0.0:20128` | ✅ CLEAR |
| Aizanta containers | All healthy (`aizanta-bot`, `aizanta-nginx`, `aizanta-frontend`, `aizanta-postgres`, `aizanta-redis`) | ✅ VERIFIED |
| No Aizanta touch | No Aizanta files modified, no Aizanta config changed, no Aizanta Docker network crossed | ✅ PLANNED |

**P2-003 code does not touch any Aizanta resource.** The `src/discord/` directory is a Guinevere-only module.

---

## 11. Caveats & Known Conflicts

### Caveat 1: Administrator Permission vs Security Docs

The Discord bot has **Administrator** permission, which conflicts with:
- `CHECKLIST.md` §4.4: "No ADMINISTRATOR permission on bot"
- Security docs recommending minimal permissions

**Rationale**: This was a conscious choice by Faiz for a private single-server bot. The checkmark in CHECKLIST.md will remain unchecked unless the security docs are updated to reflect this exception. Tracking note: Permission review should be part of P2-009.

### Caveat 2: Server Name Mismatch

`DiscordUXSpec_v1.0.md` L43 defines server name as "Guinevere's Domain" (per DIS01 Q&A). The actual server created during precondition C3 is named "Guinevere Lab". This mismatch must be resolved before P2-004 — either update the spec or rename the server. **Deferred; no action in P2-001/003.**

### Caveat 3: DiscordUXSpec Stale References

The DiscordUXSpec v1.0 contains stale references (Y1 baseline, Ollama references) that are out of scope for P2-001/002/003. These should be addressed during persona-sync or P2-004 preparations.

### Caveat 4: Command Count Inconsistency

DiscordUXSpec §2 says 34 commands, §11 says 33. Actual count will be determined at P2-010. **Deferred.**

### Caveat 5: Hermes Config Intent Names

Hermes config uses shorthand intent names: `['messages','guilds','members','message_content']`. These do NOT exactly match discord.py's `Intents` attribute names (e.g., `messages` maps to `intents.messages`, `guilds` maps to `intents.guilds`). The config intents may need normalization before P2-017 when the bot service is created. **Documented; not blocking P2-003.**

### Caveat 6: `discord-secrets.yaml` Not in Git Repo

The VPS secret file is created on-VPS-only during C3 and is not tracked in Git. This means:
- A `git clone` on a new VPS would not have the Discord token
- Recovery/DR must provision the token separately
- Consider adding `secrets/discord-secrets.yaml` to repo (SOPS-encrypted, safe to commit) or documenting manual provisioning in DR runbook

### Caveat 7: VPS SOPS Version (3.9.4 vs Latest 3.13.1)

Current SOPS v3.9.4 is functional but outdated. If compatibility issues arise during P2-017 service creation, upgrade to latest. Not blocking.

---

## 12. Rollback & Re-run Safety

| Step | Rollback | Re-run Safety |
|------|----------|---------------|
| P2-001 | No files to revert (read-only verification) | Fully idempotent |
| P2-002 | No files to revert (read-only verification) | Fully idempotent |
| P2-003 (pyproject.toml) | `git checkout pyproject.toml` or revert `discord.py>=2.4` line | Idempotent — duplicate dep line handled by `uv sync`/`pip` |
| P2-003 (intents.py) | `rm src/discord/intents.py` | Idempotent — file is self-contained, no callers yet |
| PROGRESS.md/CHECKLIST.md | Revert tracker entries | N/A — sync only after audit passes |

### Re-run Safety Rules

1. All evidence file writes are idempotent (overwrite safe)
2. `pyproject.toml` — adding `discord.py>=2.4` multiple times is harmless; duplicate entries are deduplicated by package managers
3. `intents.py` — no callers exist yet, so safe to delete and recreate
4. Evidence directory creation: `New-Item -Force` handles existing directories

---

## 13. Evidence & Auditor Path Summary

### Evidence Files (12-section schema per AGENTS.md Appendix B)

| Step | Path |
|------|------|
| P2-001 | `docs/setup-evidence/P2/STEP-P2-001/verification.md` |
| P2-002 | `docs/setup-evidence/P2/STEP-P2-002/verification.md` |
| P2-003 | `docs/setup-evidence/P2/STEP-P2-003/verification.md` |

### Auditor Report Paths

| Step | Path |
|------|------|
| P2-001 | `audit-reports/P2/STEP-P2-001/step-p2-001-auditor-report.md` |
| P2-002 | `audit-reports/P2/STEP-P2-002/step-p2-002-auditor-report.md` |
| P2-003 | `audit-reports/P2/STEP-P2-003/step-p2-003-auditor-report.md` |

### Evidence Schema (12 sections, each evidence file)

1. What Was Done
2. Files Changed
3. Validation Results
4. Evidence Artifacts
5. Doc-Sync Impact
6. Boundary Compliance
7. Rollback / Re-run Safety
8. Design Decisions / Caveats
9. Auditor Gate
10. Footer (source task, date, implementer, validation method)

Footer convention:
```
- Source task: P2-00{N} — {step description}
- Date: 2026-06-01
- Implementer: {parent or sub-agent name}
- Validation method: {lsp, grep, glob, test, etc.}
```

---

## 14. Execution Checklist for Parent

When executing this plan, the parent must:

- [ ] Read this entire plan document
- [ ] Verify collision scan (§4) — no agents writing shared files
- [ ] Execute P2-001: Create evidence directory + write verification.md
- [ ] Verify P2-001: lsp N/A (no code), evidence file exists, no secrets in evidence
- [ ] Spawn P2-001 auditor → read report → fix findings or accept false positives
- [ ] Execute P2-002: Create evidence directory + write verification.md
- [ ] Verify P2-002: evidence file exists, no token pattern in evidence
- [ ] Spawn P2-002 auditor → read report → fix findings or accept false positives
- [ ] Execute P2-003: Modify pyproject.toml + create src/discord/intents.py
- [ ] Verify P2-003: lsp_diagnostics clean, pyproject.toml grep confirms discord.py>=2.4
- [ ] Spawn P2-003 auditor → read report → fix findings or accept false positives
- [ ] AFTER all 3 audits pass: Update PROGRESS.md (P2 3/21, total 53/257)
- [ ] AFTER all 3 audits pass: Update CHECKLIST.md (§4.2 P2-001/002/003 [x])
- [ ] Final report to Faiz: changed files, verification results, evidence paths, auditor paths, caveats

---

## Footer

| Field | Value |
|-------|-------|
| **Source task** | P2-001 → P2-003 batch planner gate |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (parent, planner) |
| **Research inputs** | 6 reports in `research-reports/P2/` |
| **Validation method** | Cross-reference 6 research reports + 5 project state files + P1 evidence |
| **Next action** | Parent read this plan → begin P2-001 execution |