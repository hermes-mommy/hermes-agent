# Discord State — Pre-P2 Local Repo & VPS-Facing Assessment

| Field | Value |
|-------|-------|
| **Task** | Pre-P2-001→P2-003 reconnaissance |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (parent) |
| **Context** | P2-001 (Discord app creation), P2-002 (token SOPS storage), P2-003 (bot intents) |

---

## 1. Discord Application Identity

### Registered Application (from evidence & scripts)

| Field | Value | Source |
|-------|-------|--------|
| Application name | Guinevere | `p2-preconditions-resolved.md` L95 |
| Application ID | `1510873134981582858` | `p2-preconditions-resolved.md` L96, `capture-discord-token.sh` L8, `verify-discord-secret.sh` L7 |
| Public key | `79b547efa507dbc38b6cb03a7ce8ea089ee4646bace5231ceace1c7ca07cd430` | `p2-preconditions-resolved.md` L97, `capture-discord-token.sh` L9 |
| Bot username | Guinevere | `p2-preconditions-resolved.md` L99 |
| Server name (evidence) | Guinevere Lab | `p2-preconditions-resolved.md` L98, `capture-discord-token.sh` L10 |
| Server name (spec) | Guinevere's Domain | `DiscordUXSpec_v1.0.md` L13 (DIS01), L43 |
| Gateway intents | Presence, Server Members, Message Content | `p2-preconditions-resolved.md` L100 |
| OAuth scopes | `bot`, `applications.commands` | `p2-preconditions-resolved.md` L101 |
| Permissions | Administrator | `p2-preconditions-resolved.md` L102 |

### ⚠️ MISMATCH: Server Name

- **DiscordUXSpec v1.0** (canonical spec, L43): `Server Name | **Guinevere's Domain**`
- **Evidence file** (`p2-preconditions-resolved.md` L98): `Server | Guinevere Lab`
- **Capture script** (`capture-discord-token.sh` L10): `GUILD_NAME="Guinevere Lab"`

**Impact**: The DiscordUXSpec defines the server as "Guinevere's Domain" (per DIS01 Q&A). The actual server created during pre-condition C3 was named "Guinevere Lab". This mismatch must be resolved before P2-004 (Discord server creation) — either the spec or the actual server should be renamed for consistency.

---

## 2. Discord Secrets Storage

### 2.1 Local Repo: `secrets/guinevere-secrets.yaml`

**Path**: `C:\Users\faizz\guinevere\secrets\guinevere-secrets.yaml`
**Status**: ✅ Present and SOPS-encrypted
**Discord entries** (line 9-12):
```yaml
discord:
    bot_token: ENC[AES256_GCM,...]
    application_id: ENC[AES256_GCM,...]
```
**SOPS age key**: `age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj`
**Last modified**: 2026-05-31T07:45:47Z

### 2.2 VPS-Only: `secrets/discord-secrets.yaml`

**Path**: `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`
**Status**: ✅ Present, SOPS-encrypted, chmod 600
**Created**: 2026-06-01 13:06 (during P2 pre-conditions C3 resolution)
**File size**: 1792 bytes
**Keys stored**: `discord_bot_token`, `discord_application_id`, `discord_public_key`, `discord_guild_name`
**Decrypt test**: PASS (257 bytes plaintext, verify-discord-secret.sh confirmed token valid)
**API verification**: `curl https://discord.com/api/v10/users/@me` → `discord_api=ok`, `bot_id=1510873134981582858`, `bot_username=Guinevere`, `matches_application_id=yes`

### 2.3 Key Observation: Two Secrets Files

| File | Location | Contents | Created |
|------|----------|----------|---------|
| `guinevere-secrets.yaml` | Local + VPS repo | `discord.bot_token` + `discord.application_id` | 2026-05-31 (P0-013) |
| `discord-secrets.yaml` | VPS only (not in repo) | `discord_bot_token` + `discord_application_id` + `discord_public_key` + `discord_guild_name` | 2026-06-01 (P2 pre-conditions C3) |

**⚠️ Potential drift risk**: If tokens are rotated, both files must be updated. The `discord-secrets.yaml` on VPS has more fields (public key, guild name) not present in `guinevere-secrets.yaml`.

### 2.4 `.sops.yaml` Coverage

**Path**: `C:\Users\faizz\guinevere\.sops.yaml`
**Rules** (lines 1-11):
- `secrets/backup/.*\.env$` → dotenv input/output
- `secrets/.*\.yaml$` → YAML (matches both secret files)
- `secrets/.*\.env$` → dotenv
- `secrets/.*\.json$` → JSON

Both secret files match `secrets/.*\.yaml$` rule. ✅

---

## 3. P1 Precondition Evidence

### 3.1 Precondition File

**Path**: `docs/setup-evidence/P1/p2-preconditions-resolved.md` (197 lines)
**Verdict**: ✅ PASS — All 3 pre-conditions resolved
**Last updated**: 2026-06-01

| Condition | Description | Resolution | Source Lines |
|-----------|-------------|------------|--------------|
| C1 | Shred plaintext secrets (S-01/B1) | False positive — all backup files already SOPS-encrypted | L31-51 |
| C2a | Fix README.md stale OpenRouter/Ollama refs | ✅ Clean — zero matches in README.md | L53-71 |
| C2b | SOPS encrypt .env.9router | ✅ Already existed from migration, decrypt test PASS | L73-87 |
| C3 | Discord application verification + token storage | ✅ App verified, token encrypted, API validation PASS | L89-125 |

### 3.2 Independent Auditor Report

**Path**: `audit-reports/P1/P1-PRECONDITIONS/p2-preconditions-auditor-report.md` (149 lines)
**Verdict**: ✅ PASS — All 3 pre-conditions independently verified resolved
**Auditor**: Sisyphus-Junior (fresh context, no prior P1 involvement)

Key note from auditor: C3 (Discord app verification) is a manual step at developer.discord.com and was NOT verified via SSH — only the token decryption and API validation were confirmed. Full app portal verification is deferred to P2-003.

---

## 4. Current P2 Progress State

### 4.1 PROGRESS.md (lines 118-141)

| Item | Status |
|------|--------|
| P2 total steps | 21 |
| Completed | 0 / 21 |
| Phase status | ⏳ Not Started |
| ADR | ADR-022 (Communication Channel Strategy) |
| Cost | $0/month |
| Dependencies | P0 (parallel w/ P1) |

### 4.2 P2 Steps Listed (PROGRESS.md L121-141)

| Step | Description | Status |
|------|-------------|--------|
| P2-001 | Discord application creation | ⏳ Not Started |
| P2-002 | Bot token generation + SOPS storage | ⏳ Not Started |
| P2-003 | Bot intents (MESSAGE_CONTENT, GUILD_MEMBERS) | ⏳ Not Started |
| P2-004 | Discord server creation ("Guinevere's Domain") | ⏳ Not Started |
| P2-005 | 4 categories setup | ⏳ Not Started |
| P2-006 | 13 channels creation | ⏳ Not Started |
| P2-007 | Channel permissions | ⏳ Not Started |
| P2-008 | Channel topics (persona-flavored) | ⏳ Not Started |
| P2-009 | Bot invite + permission verification | ⏳ Not Started |
| P2-010 | Slash commands registration (33 commands) | ⏳ Not Started |
| P2-011 | Embed color palette | ⏳ Not Started |
| P2-012–P2-016 | Individual slash commands + tests | ⏳ Not Started |
| P2-017 | `guinevere-discord.service` creation | ⏳ Not Started |
| P2-018 | Discord health check | ⏳ Not Started |
| P2-019 | Notification routing test (SEV0-SEV4) | ⏳ Not Started |
| P2-020 | Gotify installation + test | ⏳ Not Started |
| P2-021 | Discord → Gotify fallback test | ⏳ Not Started |

### 4.3 CHECKLIST.md Section 4 (Phase 2: Discord Bot)

All P2 verification items are unchecked (lines 237-286). Section 4.1 Prerequisites:
- Phase 0 complete — ✅ (P0: 29/29)
- Can run parallel with Phase 1 — ✅
- Discord developer account available — ⏳ Unverified status

### 4.4 P2 Readiness Report

**Path**: `audit-reports/P1/P1-FINAL/07-p2-readiness.md` (147 lines)
**Verdict**: GO with 3 conditions (all now resolved)

| Condition | Severity | Status | Resolution |
|-----------|----------|--------|------------|
| C1: P1 Final Audit must complete | MEDIUM | ✅ RESOLVED | P1-FINAL complete |
| C2: Discord app created at developer.discord.com | HIGH | ✅ RESOLVED | Manual step, confirmed via API token verify |
| C3: src/discord/ only has __init__.py | LOW | ✅ BY DESIGN | Bot modules created in P2 scope |

---

## 5. Hermes Config — Discord Section

### 5.1 Deployed Config

**Path** (VPS): `/home/guinevere/config/hermes/config.yaml`
**Local evidence**: `docs/setup-evidence/P1/STEP-P1-005/config.yaml` (lines 68-72)
**Mirror**: `tmp/hermes-config-y4.yaml` (lines 68-72)

```yaml
messaging:
  discord:
    enabled: true
    prefix: "!"
    intents: ["messages","guilds","members","message_content"]
```

**Note**: The intents `"messages"`, `"guilds"`, `"members"` correspond to Discord gateway intents, but these names don't exactly match the discord.py `Intents` API. The intent names in config use lowercase shorthand rather than the Python API names. P2-003 should verify these resolve correctly.

---

## 6. VPS-Facing Scripts

### 6.1 `capture-discord-token.sh`

**Path** (VPS): `/tmp/capture-discord-token.sh` (74 lines)
**Purpose**: Secure Discord bot token capture — hidden input → SOPS encrypt → shred plaintext
**Key security features**:
- `history -c; history -w` before and after input
- Hidden `read -rs` for token input
- Temp file under `secrets/.discord-secrets.*.yaml` to match `.sops.yaml` creation rules
- `shred -u` on temp files
- Unset token variable after use
- `umask 077` for the session
- Verifies age key and public key before encryption

### 6.2 `verify-discord-secret.sh`

**Path** (VPS): `/tmp/verify-discord-secret.sh` (45 lines)
**Purpose**: Verify Discord token decrypt + API validation
**What it checks**:
1. `ls -l` on secret file (size, mode)
2. Decrypt via SOPS + grep for `discord_bot_token`, `discord_application_id`, `discord_public_key`
3. Report decrypt byte count
4. `curl` to Discord API `/users/@me` with Bot token → validations:
   - `discord_api=ok`
   - `bot_id=1510873134981582858`
   - `bot_username=Guinevere`
   - `matches_application_id=yes`

**Evidence from precondition resolution**:
```text
token_key=present
app_id=ok
public_key=present
decrypt_bytes=257
discord_api=ok
bot_id=1510873134981582858
bot_username=Guinevere
matches_application_id=yes
```

---

## 7. Discord Documentation Status

### 7.1 DiscordUXSpec v1.0

**Path**: `docs/60-persona/63-DiscordUXSpec_v1.0.md` (2056 lines)
**Audit**: `audit-reports/2026-05-31-persona-prompt-mcp-discord-audit.md`
**Audit verdict**: NEEDS REVIEW — CONDITIONAL PASS

**Blocking findings applicable to P2**:
| ID | Finding | Severity | Impact on P2 |
|----|---------|----------|-------------|
| B1 | ADR-029 cited instead of ADR-011 for SDLC | BLOCKING | Low — metadata only |
| B2 | Authority order conflicts with PersonaSafetyPolicy | BLOCKING | Low — doesn't affect Discord implementation |
| NB8 | Command count: §2 says 34, §11 says 33 | NON-BLOCKING | Should reconcile before P2-010 command registration |

### 7.2 ADR-022 (Communication Channel Strategy)

**Path**: `adr/ADR-022-communication-channel-strategy.md`
**Relevance**: Governs Discord as primary channel, Gotify as fallback, P2-020/021

---

## 8. Mismatch & Gap Summary

| # | Item | Severity | Description | Action Required |
|---|------|----------|-------------|-----------------|
| M1 | Server name: "Guinevere Lab" vs "Guinevere's Domain" | MEDIUM | Evidence says "Guinevere Lab", DiscordUXSpec says "Guinevere's Domain" | Reconcile before P2-004: update spec or rename server |
| M2 | Token has two SOPS files | LOW | `guinevere-secrets.yaml` (local) + `discord-secrets.yaml` (VPS-only) | Ensure both stay in sync during rotation |
| M3 | Config intents use shorthand names | LOW | `messages`, `guilds`, `members` in config.yaml may not match discord.py API | Verify at P2-003 |
| M4 | Command count inconsistency (34 vs 33) | LOW | DiscordUXSpec | Reconcile before P2-010 |
| M5 | `discord-secrets.yaml` not in repo | LOW | Created on VPS only during C3; not tracked in git | Consider adding to `.gitignore` or syncing to `secrets/` |
| M6 | Pre-condition C3 was manually done by Faiz | INFO | No direct evidence of developer portal visit | Confirm bot application settings match spec at P2-001 |
| M7 | `guinevere-secrets.yaml` missing `discord_public_key` | LOW | Only `discord-secrets.yaml` has public key | Add to `guinevere-secrets.yaml` if needed for verification |

---

## 9. Ready for P2-001 → P2-003

### Verdict: ✅ CLEAR TO START

All P1 pre-conditions verified and resolved. Discord app exists, token is SOPS-encrypted and API-validated, bot intents are pre-configured in Hermes config.

### Recommended P2-001 → P2-003 Order

1. **P2-001** — Verify Discord application at developer.discord.com matches evidence (app ID, public key, intents)
2. **P2-002** — Confirm `discord-secrets.yaml` is the canonical token source; update evidence with file path
3. **P2-003** — Validate config.yaml intents resolve correctly in Python/discord.py; register MESSAGE_CONTENT + GUILD_MEMBERS

### Known Mismatches to Fix During P2

- Rename server or update DiscordUXSpec (M1)
- Reconcile command count (M4)

---

## 10. Evidence Artifacts Referenced

| Artifact | Path |
|----------|------|
| P2 preconditions evidence | `docs/setup-evidence/P1/p2-preconditions-resolved.md` |
| P2 preconditions auditor | `audit-reports/P1/P1-PRECONDITIONS/p2-preconditions-auditor-report.md` |
| P2 readiness report | `audit-reports/P1/P1-FINAL/07-p2-readiness.md` |
| Discord UX spec | `docs/60-persona/63-DiscordUXSpec_v1.0.md` |
| Discord audit | `audit-reports/2026-05-31-persona-prompt-mcp-discord-audit.md` |
| PROGRESS tracker | `PROGRESS.md` (L118-141) |
| CHECKLIST | `CHECKLIST.md` (§4, L223-286) |
| Local secrets | `secrets/guinevere-secrets.yaml` (L9-12) |
| SOPS rules | `.sops.yaml` |
| Hermes config (evidence) | `docs/setup-evidence/P1/STEP-P1-005/config.yaml` (L68-72) |
| VPS capture script | `tmp/capture-discord-token.sh` (VPS) |
| VPS verify script | `tmp/verify-discord-secret.sh` (VPS) |
| ADR-022 | `adr/ADR-022-communication-channel-strategy.md` |

---

## Footer

- **Source task**: Pre-P2 local repo and VPS-facing Discord state assessment
- **Date**: 2026-06-01
- **Implementer**: Guinevere (parent)
- **Validation**: grep, glob, read across 15+ files
- **Next action**: Begin P2-001 Discord application verification
