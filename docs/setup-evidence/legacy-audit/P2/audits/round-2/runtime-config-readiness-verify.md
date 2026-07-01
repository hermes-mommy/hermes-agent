# P2 Round-2 Adversarial Verification: Runtime/Config Readiness

**Verifier:** Subagent (read-only, adversarial)
**Date:** 2026-06-25
**Premise:** Independently verify each finding from round-1 (runtime-config-readiness). Try to refute. Then run a miss-hunt for bugs round-1 missed.

---

## Part A: R1 Finding Re-Verification

### P2-RC-R1-001 [CRITICAL] — systemd/guinevere-discord.service references non-existent PLAINTEXT .env.discord

| Field | Value |
|-------|-------|
| Claim | `systemd/guinevere-discord.service` line 13 `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord` — file does not exist |
| Evidence | Read systemd/guinevere-discord.service:13 confirms the path. Glob for `**/.env.discord*` returns 0. |
| My attempt to refute | Tried all glob variants. File does not exist anywhere in repo. |
| **Verdict** | **CONFIRMED** |
| Severity | CRITICAL — service unit references a file that does not exist |
| Correction to R1 | Actually WORSE than reported: `systemd/guinevere-shadow-monitor.service` line 13 references THE SAME non-existent `.env.discord`. R1 missed this second victim. |

### P2-RC-R1-002 [CRITICAL] — deploy/discord/guinevere-discord.service references non-existent .env.discord.sops

| Field | Value |
|-------|-------|
| Claim | `deploy/discord/guinevere-discord.service` line 14 references `secrets/.env.discord.sops`, which does not exist. `--input-type dotenv` flag would fail against the actual YAML file. |
| Evidence | Read deploy/discord/guinevere-discord.service:13-15 confirms the path and flags. Glob for `.env.discord*` returns 0. Actual file is `secrets/discord-secrets.enc.yaml` (YAML format with `ENC[AES256_GCM...` prefix). |
| My attempt to refute | Looked for any `.discord.sops` variant, any `.discord.env.sops`. None exist. |
| **Verdict** | **CONFIRMED** |
| Severity | CRITICAL — deploy-ready unit is broken by design |

### P2-RC-R1-003 [CRITICAL] — Secrets age key stored in PLAINTEXT in repo

| Field | Value |
|-------|-------|
| Claim | `secrets/new-age-key.txt` contains the AGE-SECRET-KEY in plaintext "in the repository" |
| Evidence | File exists at `secrets/new-age-key.txt`, contains `AGE-SECRET-KEY-[REDACTED]`. Verified via read of first 3 lines. |
| My attempt to refute | The key question: is this file actually **git-tracked**? Ran `git ls-files secrets/` → empty (no tracked files). Ran `git check-ignore -v secrets/new-age-key.txt` → returns `.gitignore:24:secrets/` — the file IS git-ignored. It exists on the filesystem but is NOT committed to git history. |
| **Verdict** | **PARTIALLY-REFUTED** — The CLAIM says "stored in the repository" which is ambiguous. The file EXISTS on disk in the repo working tree but is NOT git-tracked (`.gitignore` rule `secrets/` covers it). The risk of co-location with encrypted files is real (the private key is in the same directory as `discord-secrets.enc.yaml`). However, R1's framing "stored in the repo" overstates the severity: it is not in git history and cannot be cloned. The `.gitignore` explicitly prevents plaintext secret commits per its comment. |
| Severity (re-assessment) | HIGH (not CRITICAL) — the private key is on disk but not in git. Operator laziness or `git add -f` could commit it; the co-location risk remains. |
| Correction to R1 | R1 should have verified git tracking status before claiming it is "in the repository". Recommend downgrading to HIGH and clarifying. |

### P2-RC-R1-004 [HIGH] — systemd/guinevere-discord.service uses plaintext EnvironmentFile with no shred (insecure by design)

| Field | Value |
|-------|-------|
| Claim | `systemd/` copy lacks SOPS decrypt, PrivateTmp, shred; has plaintext `EnvironmentFile=.env.discord`. `deploy/discord/` copy has SOPS+shred. |
| Evidence | Read both units and compared. systemd/: no ExecStartPre, no shred, plaintext env. deploy/discord/: `ExecStartPre=sops --decrypt...`, `ExecStopPost=shred -u`, `PrivateTmp=true`. |
| **Verdict** | **CONFIRMED** |
| Severity | HIGH |
| Correction to R1 | None needed. Accurate finding. |

### P2-RC-R1-005 [HIGH] — Two conflicting hermes-gateway.service units

| Field | Value |
|-------|-------|
| Claim | THREE variants: systemd/ (hermes --config ... gateway, .env.hermes), scripts/ (hermes gateway run --accept-hooks, ~/.hermes/.env), vps-mirror/systemd-live/ (gateway run, .env.hermes, Wants= not Requires=) |
| Evidence | Read all three. Confirmed all differences as stated. VPS live: `ExecStart=...hermes gateway run --accept-hooks`, `EnvironmentFile=.env.hermes`, `Wants=guinevere-core.service` + `Wants=redis.service` (no Requires). |
| **Verdict** | **CONFIRMED** |
| Severity | HIGH |
| Correction to R1 | None. Accurate. |

### P2-RC-R1-006 [HIGH] — systemd/guinevere-discord.service marked as "intentionally masked" but is different from deploy version

| Field | Value |
|-------|-------|
| Claim | Service is masked. No unit in vps-mirror/systemd-live/. Two drastically different copies exist in systemd/ vs deploy/discord/. |
| Evidence | ls of vps-mirror/systemd-live/ shows NO guinevere-discord.service. Both copies in repo confirmed. |
| **Verdict** | **CONFIRMED** |
| Severity | HIGH |
| Correction to R1 | None. Accurate. |

### P2-RC-R1-007 [HIGH (round 1 downgraded from CRITICAL)] — secrets/backup/ directory has no .gitkeep

| Field | Value |
|-------|-------|
| Claim | "No .gitkeep was found." Section says "empty backup directories are invisible in the repo." |
| Evidence | Read the backup directory contents. It is NOT empty: `restic-password-plaintext.env`, `idcloudhost-s3-plaintext.env`, `cloudflare-r2-plaintext.env`, `README.md` all exist on disk. However, since `secrets/` is git-ignored, NONE of these files are tracked. |
| My attempt to refute | Checked `git ls-files secrets/backup/` → empty. All files exist only on local filesystem. The README.md claims the directory contains SOPS-encrypted files but the *-plaintext.env files are the opposite of encrypted — they contain LIVE credentials in plaintext. |
| **Verdict** | **PARTIALLY-REFUTED** — The directory is NOT empty (R1 claimed it was, looking for a .gitkeep). The real problem is different: (a) none of the backup files are git-tracked, so a fresh clone has no backup config at all; (b) the *-plaintext.env files contain REAL restic/S3 credentials in plaintext on disk (R1 missed this entirely). The `.gitignore` rule `secrets/` blocks all tracking including README.md. |
| Severity (re-assessment) | LOW for the .gitkeep claim; HIGH for the undiscovered plaintext credentials issue (see new finding R2-RC-NEW-002 below) |
| Correction to R1 | The finding should have focused on the fact that backup secrets are UNTRACKED (not just the missing .gitkeep) and that plaintext credential files exist. |

### P2-RC-R1-008 [MEDIUM] — notifications.py bare `import discord` at module level (line 240) contradicts lazy-import design

| Field | Value |
|-------|-------|
| Claim | Line 240 has bare `import discord  # noqa: E402  # isort: skip` that is never referenced after, contradicts lazy import design. |
| Evidence | Read notifications.py:240. Grep for `import discord` confirmed line 208 (`import discord as discord_module` inside send_alert) and line 240. Lines after 240: just end of file. The imported name `discord` is unused. |
| **Verdict** | **CONFIRMED** |
| Severity | MEDIUM |
| Correction to R1 | None. Accurate. Dead code with misleading suppression comment. |

### P2-RC-R1-009 [MEDIUM] — .env.hermes does not exist in repo; scripts/ service references ~/.hermes/.env which also does not exist

| Field | Value |
|-------|-------|
| Claim | `.env.hermes` at root not found. `.hermes/.env` not found. |
| Evidence | Glob for `**/.env.hermes*` and `**/.env*` in `.hermes/` both returned 0 results. |
| **Verdict** | **CONFIRMED** |
| Severity | MEDIUM |
| Correction to R1 | None. Accurate. These .env files exist only on VPS. |

### P2-RC-R1-010 [MEDIUM] — CHECKLIST.md still claims 33 slash commands (stale), PROGRESS.md says 35 (also stale), code has 49

| Field | Value |
|-------|-------|
| Claim | CHECKLIST.md 33, PROGRESS.md 35, code has 49 (validated by `_command_registry.py` requiring len==49). |
| Evidence | `_command_registry.py:406` confirms `len(names) != 49` raises RuntimeError. |
| **Verdict** | **CONFIRMED** |
| Severity | MEDIUM |
| Correction to R1 | None. Accurate. |

### P2-RC-R1-011 [MEDIUM] — 14 channels in channel-ids.yaml vs 13 documented in CHECKLIST.md

| Field | Value |
|-------|-------|
| Claim | 14 entries in channel-ids.yaml (including `rituals`), CHECKLIST.md has 13. |
| Evidence | Read channel-ids.yaml: count is 14. CHECKLIST.md said 13. `rituals` channel (1513496377324339262) is the 14th. Also note: `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev` are present but likely ghost channels from earlier prototyping. |
| **Verdict** | **CONFIRMED** |
| Severity | MEDIUM |
| Correction to R1 | R1 only flagged `rituals` as the 14th channel. The PROJECT ghost channels (project-alpha-dev, project-alpha-docs, project-beta-dev = 3 more) are also undocumented. So it's not 13-vs-14 but rather 10 legit + 4 undocumented/ghost. R1 should have enumerated which 4 are the extras. |

### P2-RC-R1-012 [LOW] — GOTIFY_URL port 8081 vs old audit mention of 8080 (now resolved)

| Field | Value |
|-------|-------|
| Claim | Code uses 8081, docker-compose uses 8081, old audit said 8080. Resolved. |
| Evidence | gotify_fallback.py:32 = 8081. STEP-P2-020/docker-compose.yml:7 = 8081. Old audit P2-AUDIT-COMPLETE.md said 8080. |
| **Verdict** | **CONFIRMED RESOLVED** |
| Severity | LOW |
| Correction to R1 | None. Accurate but minor. |

### P2-RC-R1-013 [LOW] — PRD v2.2 references #alerts channel that does not exist

| Field | Value |
|-------|-------|
| Claim | PRD line 55 has `#alerts`, not in channel-ids.yaml. |
| Evidence | Read 01-PRD_v2.2.md:55 shows `#alerts`. Not in channel-ids.yaml. |
| **Verdict** | **CONFIRMED** |
| Severity | LOW |
| Correction to R1 | None. Accurate. |

### P2-RC-R1-014 [LOW] — cmd_safeword.py sync version docstring says "No bot.py listener exists yet"

| Field | Value |
|-------|-------|
| Claim | Sync version docstring says inactive, but async version IS wired in _entrypoint.py _on_message_listener. |
| Evidence | cmd_safeword.py:598-601 docstring. _entrypoint.py:155 imports `handle_safeword_message_async` and calls it in listener. |
| **Verdict** | **CONFIRMED** |
| Severity | LOW |
| Correction to R1 | None. Accurate. |

### P2-RC-R1-015 [LOW] — notifications.py imports discord.utils at module level (lines 20-22) with silent try/except

| Field | Value |
|-------|-------|
| Claim | Lines 20-22 catch ALL exceptions, PEP 8 recommends `except ImportError`. |
| Evidence | Read notifications.py:20-22 confirms `except Exception:`. |
| **Verdict** | **CONFIRMED** |
| Severity | LOW |
| Correction to R1 | None. Accurate. |

### P2-RC-R1-016 [COSMETIC] — deploy/env/ directory has only a WhatsApp template

| Field | Value |
|-------|-------|
| Claim | deploy/env/ has only `.env.whatsapp.template`. No Discord or Hermes templates. |
| Evidence | Glob for `deploy/env/*` returned only `.env.whatsapp.template`. |
| **Verdict** | **CONFIRMED** |
| Severity | COSMETIC |
| Correction to R1 | None. |

### P2-RC-R1-017 [COSMETIC] — .env.example contains DISCORD_BOT_TOKEN but no Gotify placeholder

| Field | Value |
|-------|-------|
| Claim | "No GOTIFY_URL, GOTIFY_APP_TOKEN, or GOTIFY_ADMIN_PASSWORD entries found in the file." |
| My attempt to refute | Grepped `.env.example` for `GOTIFY_APP_TOKEN`: found at line 214. So GOTIFY_APP_TOKEN IS present. R1's grep was incomplete. However, GOTIFY_URL and GOTIFY_ADMIN_PASSWORD are indeed missing. |
| **Verdict** | **PARTIALLY-REFUTED** — GOTIFY_APP_TOKEN IS in `.env.example` at line 214. R1 missed it. GOTIFY_URL and GOTIFY_ADMIN_PASSWORD remain missing. |
| Severity (re-assessment) | COSMETIC |
| Correction to R1 | The claim that GOTIFY_APP_TOKEN is missing is incorrect. Update to say "GOTIFY_URL and GOTIFY_ADMIN_PASSWORD are missing from .env.example." |

### P2-RC-R1-018 [COSMETIC] — systemd/ vs deploy/discord/ discrepancy documented nowhere

| Field | Value |
|-------|-------|
| Claim | No README explaining difference. |
| Evidence | Glob for `systemd/README*` and `deploy/discord/README*`: both returned 0 results. No README in either directory. |
| **Verdict** | **CONFIRMED** |
| Severity | COSMETIC |
| Correction to R1 | None. |

### P2-RC-R1-019 [COSMETIC] — Old P2-AUDIT-COMPLETE.md CRITICAL finding "encrypted secret MISSING" is now RESOLVED

| Field | Value |
|-------|-------|
| Claim | `secrets/discord-secrets.enc.yaml` EXISTS and is SOPS-encrypted. Old audit not updated. |
| Evidence | File exists, has `ENC[AES256_GCM...` prefix confirming SOPS encryption. |
| My attempt to refute | Checked git tracking status: `git ls-files secrets/discord-secrets.enc.yaml` returns empty. The file is git-ignored by `.gitignore:24:secrets/`. A fresh git clone would NOT include the encrypted secret — it only exists on this developer's local machine. The old audit's concern was "the encrypted file doesn't exist" — now it exists locally but is UNTRACKED. If this VPS were rebuilt from git, the encrypted file would still be missing. |
| **Verdict** | **PARTIALLY-REFUTED** — The encrypted file EXISTS on disk but is NOT git-tracked. R1 missed this critical detail. The resolution is incomplete: the file exists locally but `git clone` won't deploy it. Combined with R1-002 (deploy unit references wrong path), this is actually a HIGH issue in disguise. |
| Severity (re-assessment) | COSMETIC for old-audit-update claim, but reclassify as HIGH for the new sub-finding (encrypted secret untracked) |
| Correction to R1 | R1 should have checked git status before declaring "RESOLVED". The fix is incomplete. |

---

## Part A Summary: R1 Re-Verification

| Finding | R1 Verdict | R2 Verdict | Delta |
|---------|-----------|-----------|-------|
| P2-RC-R1-001 | CONFIRMED | CONFIRMED (worse: shadow-monitor also affected) | Acknowledged |
| P2-RC-R1-002 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-003 | CONFIRMED | PARTIALLY-REFUTED (git-ignored, not tracked) | Severity mismatch |
| P2-RC-R1-004 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-005 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-006 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-007 | CONFIRMED | PARTIALLY-REFUTED (dir not empty; real issue is plaintext creds and untracked files) | Finding was wrong |
| P2-RC-R1-008 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-009 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-010 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-011 | CONFIRMED | CONFIRMED (worse: 4 ghosts not 1) | Understated |
| P2-RC-R1-012 | CONFIRMED RESOLVED | CONFIRMED RESOLVED | None |
| P2-RC-R1-013 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-014 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-015 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-016 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-017 | CONFIRMED | PARTIALLY-REFUTED (GOTIFY_APP_TOKEN IS present) | Claim was wrong |
| P2-RC-R1-018 | CONFIRMED | CONFIRMED | None |
| P2-RC-R1-019 | CONFIRMED RESOLVED | PARTIALLY-REFUTED (untracked, not resolved for git clone scenario) | Resolution overstated |

**R1 Verification Totals:**
- CONFIRMED (unchanged): 12
- PARTIALLY-REFUTED: 4 (R1-003, R1-007, R1-017, R1-019)
- CONFIRMED RESOLVED: 1 (R1-012)

---

## Part B: Miss-Hunt — New Findings R1 Did Not Report

### P2-RC-R2-NEW-001 [HIGH] — `systemd/guinevere-shadow-monitor.service` also references non-existent `.env.discord`

- **File:** `systemd/guinevere-shadow-monitor.service` line 13
- **Evidence:** `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord`
- **Verification:** CONFIRMED
- **Verdict:** The shadow monitor service unit has the exact same broken reference as R1-001. The `.env.discord` file does not exist anywhere in the repo. If this oneshot service is triggered by its timer, it would fail immediately with a missing file error. R1 cited the main discord service but missed this second victim.
- **Impact:** HIGH. The systemd timer `guinevere-shadow-monitor.timer` would trigger this unit, which crashes on start. Shadow monitoring is non-functional even if enabled.
- **Note:** The unit also has `After=guinevere-discord.service`, which is itself masked. So there are two separate failure modes.

### P2-RC-R2-NEW-002 [HIGH] — `secrets/backup/` contains LIVE cloud credentials in plaintext on disk

- **Files:**
  - `secrets/backup/restic-password-plaintext.env` — contains `RESTIC_PASSWORD=...` (real 64-char password)
  - `secrets/backup/idcloudhost-s3-plaintext.env` — contains `AWS_ACCESS_KEY_ID=[REDACTED]`, `AWS_SECRET_ACCESS_KEY=[REDACTED]`, `RESTIC_REPOSITORY=s3:https://is3.cloudhost.id/s3-guinevere`
  - `secrets/backup/cloudflare-r2-plaintext.env` — contains `AWS_ACCESS_KEY_ID=...`, `AWS_SECRET_ACCESS_KEY=...`
- **Verification:** CONFIRMED. All three files exist and contain real credentials. Verified via Read.
- **Verdict:** The `secrets/backup/README.md` explicitly says to "shred the plaintext files" after re-encrypting with SOPS. These files should not exist on disk. While git-ignored by `secrets/`, they are accessible to anyone with local filesystem access.
- **Impact:** HIGH. Compromise of this machine exposes: (a) restic repository password (data-at-rest decryption), (b) idcloudhost S3 credentials (primary backup target), (c) Cloudflare R2 credentials (secondary backup target). All three backup secrets in plaintext.
- **DO NOT print the secret values.** Paths and variable names are sufficient.

### P2-RC-R2-NEW-003 [MEDIUM] — `secrets/` directory entirely git-ignored; SOPS-encrypted production secrets are NOT tracked

- **File:** `.gitignore` line 24: `secrets/`
- **Evidence:** `git ls-files secrets/` returns empty (no tracked files). `git check-ignore secrets/discord-secrets.enc.yaml` confirms it is ignored.
- **Verification:** CONFIRMED. The entire `secrets/` tree is git-ignored. This includes `secrets/discord-secrets.enc.yaml` (the SOPS-encrypted bot token) and `secrets/backup/README.md` (the documentation).
- **Verdict:** R1-019 claimed the encrypted-secret finding was "RESOLVED" because the file exists. But the file is not in git. If the VPS is rebuilt from a fresh clone, `deploy/discord/guinevere-discord.service`'s `ExecStartPre` (which references `secrets/.env.discord.sops` — a double whammy since even the path is wrong) will fail because neither the YAML file nor any encrypted dotenv exists in the clone. The `.sops.yaml` creation rule `secrets/.*\.yaml$` implies intent to track YAML, but `.gitignore` blocks it.
- **Impact:** MEDIUM. Fresh provisioning from git clone would be missing all encrypted secrets, causing service start failures. Current VPS (with files on disk) is fine, but disaster recovery requires out-of-band secret distribution.
- **Note:** The `secrets/.gitignore` allows `*.sops.yaml` and `*.sops` — suggesting someone wanted to track SOPS files but the parent `.gitignore`'s `secrets/` rule overrides this (since `.gitignore` rules are additive, and the parent ignores the entire directory first).

### P2-RC-R2-NEW-004 [MEDIUM] — `GUINEVERE_API_KEY` env var handled inconsistently across command modules

- **Files:**
  - `cmd_loops.py:42`: `GUINEVERE_API_KEY` with empty default, no empty-check → **silent header** (request sends with empty key)
  - `cmd_evidence.py:118`: same pattern → silent empty auth header
  - `cmd_loop_start.py:344-349`: checks empty and sends warning embed → explicit error
  - `cmd_loop_stop.py:385-390`: checks empty → explicit error
  - `cmd_loop_pause.py:57-62`: checks empty → explicit error
  - `cmd_loop_resume.py:58-63`: checks empty → explicit error
  - `cmd_loop_priority.py:81-86`: checks empty → explicit error
- **Verification:** CONFIRMED. 2 modules (cmd_loops, cmd_evidence) pass an empty API key silently. 5 modules warn the user. Inconsistent.
- **Verdict:** The inconsistent handling means `/loops` and `/evidence` commands would call the internal API with an empty `X-Guinevere-API-Key` header. If the API rejects empty keys, these commands would silently fail with an opaque error.
- **Impact:** MEDIUM. User gets no feedback about why `/loops` or `/evidence` fail when GUINEVERE_API_KEY is not set.

### P2-RC-R2-NEW-005 [MEDIUM] — Hardcoded `localhost` references throughout cmd_* modules with no env-var override

- **Files (8 modules):**
  - `cmd_casual.py:38` `redis.Redis(host="localhost", port=6380)`
  - `cmd_clear_cache.py:40` `redis.Redis(host="localhost", port=6380)`
  - `cmd_consent.py:45` `redis.Redis(host="localhost", port=6380)`
  - `cmd_focus.py:45` `redis.Redis(host="localhost", port=6380)`
  - `cmd_punishment.py:60` `redis.Redis(host="localhost", port=6380)`
  - `cmd_reward.py:46` `redis.Redis(host="localhost", port=6380)`
  - `cmd_health_check.py:35` `HEALTH_URL: str = "http://localhost:8000/health/detailed"`
  - `gotify_fallback.py:32` `GOTIFY_URL: str = "http://localhost:8081"`
- **Verification:** CONFIRMED. At least 8 modules hardcode `localhost` and/or `6380`/`8000` with no env-var fallback for host or port.
- **Verdict:** R1 missed this pattern. Every module that connects to Redis or the internal API should allow host/port override via env vars. If any service moves to a different host or port (e.g., Redis to a separate machine, API behind a reverse proxy), all these commands break silently.
- **Impact:** MEDIUM. Not a current production risk since everything runs on localhost, but a significant architectural constraint that prevents scaling or reconfiguration without code changes.
- **Note:** `hermes_conversational.py:153` also has these values but at least reads `REDIS_PASSWORD` from env.

### P2-RC-R2-NEW-006 [LOW] — notifications.py SEV routing uses channel NAME lookup not ID

- **File:** `src/discord/notifications.py` line 215
- **Evidence:** `channel = discord_utils_local.get(channels, name=data.channel_name)`. The `SEV_MATRIX` maps severity levels to channel names (`system-health`, `cost-tracker`, `guinevere-status`, `audit-log`), not IDs.
- **Verification:** CONFIRMED.
- **Verdict:** Discord channel names can be renamed by any user with Manage Channels permission. If a channel is renamed, all SEV alert routing breaks silently. The `channel-ids.yaml` file has the canonical numeric IDs, but the code does not use them.
- **Impact:** LOW for current production (names are stable). Would become a hard-to-diagnose symptom if a channel is ever renamed. Should use channel IDs instead of names for routing.

### P2-RC-R2-NEW-007 [LOW] — `cmd_health_check.py` calls internal health API without auth headers

- **File:** `src/discord/cmd_health_check.py` lines 45-49
- **Evidence:** `client.get(HEALTH_URL)` with no auth headers. Compare with `cmd_loops.py` which adds `X-Guinevere-API-Key` header.
- **Verification:** CONFIRMED.
- **Verdict:** If the internal API requires authentication (which it should, given other modules send API keys), the health check command would return a 401/403 error. Inconsistent API auth pattern across modules.
- **Impact:** LOW. Currently works if the API does not enforce auth on /health endpoints, which is reasonable for health checks. But inconsistent with the pattern used by other commands.

### P2-RC-R2-NEW-008 [LOW] — `listeners/gmail_reactions.py` has hardcoded fallback channel ID

- **File:** `src/discord/listeners/gmail_reactions.py` line 54
- **Evidence:** `return 1515062963705221130` as fallback when `GMAIL_TARGET_CHANNEL_ID` env var is not set.
- **Verification:** CONFIRMED. This hardcoded ID is not documented in channel-ids.yaml (which has 14 channels but none match this ID).
- **Verdict:** If the env var is absent and the hardcoded ID is wrong or refers to a different guild, the Gmail reaction listener silently ignores all reactions in the actual Gmail channel. Silent failure with no logging to indicate the misconfiguration.
- **Impact:** LOW. If the env var is properly set in production, this fallback is never reached. But it is undocumented and fragile.

### P2-RC-R2-NEW-009 [COSMETIC] — `_entrypoint.py` GUILD_ID hardcoded with no env-var override

- **File:** `src/discord/_entrypoint.py` line 48
- **Evidence:** `GUILD_ID: int = 1_510_876_414_671_323_206`
- **Verification:** CONFIRMED. All `self.tree.command(guild=discord.Object(id=GUILD_ID))` calls use this constant.
- **Verdict:** The bot can only operate in one guild. Deploying to a second guild or testing in a different guild requires code changes. The `.env.example` has `DISCORD_GUILD_ID` placeholder at line 77 which is never referenced by the entrypoint.
- **Impact:** COSMETIC. Intentional per P2 design, but wasteful: the `.env.example` documents a `DISCORD_GUILD_ID` that the code ignores. Documentation/code mismatch.

### P2-RC-R2-NEW-010 [COSMETIC] — `.env.example` contains placeholder values not commented out for sensitive fields

- **Files:** `.env.example` lines 51 (NINE_ROUTER_API_KEY), 74 (DISCORD_BOT_TOKEN), 577 (GUINEVERE_API_KEY), 148 (POSTGRES_PASSWORD), 177 (REDIS_PASSWORD), 214 (GOTIFY_APP_TOKEN)
- **Evidence:** All sensitive fields have placeholder values like `your-*-here` that are NOT prefixed with `#` to disable them.
- **Verification:** CONFIRMED.
- **Verdict:** `cp .env.example .env && source .env` would set these placeholders as active values. Downstream code reading `DISCORD_BOT_TOKEN` would get `your-discord-bot-token-here` instead of an empty string, potentially causing confusing error messages instead of clear "token not set" failures.
- **Impact:** COSMETIC. A `RuntimeError("DISCORD_BOT_TOKEN environment variable is required")` would trigger because the placeholder is non-empty — actually, the code checks `if not token:`, so a non-empty placeholder would PASS the check and then fail during gateway auth with a cryptic error from Discord's API. So this is slightly worse than cosmetic.

---

## Part B Summary: Miss-Hunt New Findings

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| P2-RC-R2-NEW-001 | HIGH | shadow-monitor.service also references non-existent .env.discord | CONFIRMED |
| P2-RC-R2-NEW-002 | HIGH | secrets/backup/ plaintext credentials on disk | CONFIRMED |
| P2-RC-R2-NEW-003 | MEDIUM | Entire secrets/ directory git-ignored, encrypted files untracked | CONFIRMED |
| P2-RC-R2-NEW-004 | MEDIUM | GUINEVERE_API_KEY inconsistent across cmd_* modules | CONFIRMED |
| P2-RC-R2-NEW-005 | MEDIUM | 8+ modules hardcode localhost:port with no env override | CONFIRMED |
| P2-RC-R2-NEW-006 | LOW | notifications.py uses channel NAME not ID for routing | CONFIRMED |
| P2-RC-R2-NEW-007 | LOW | cmd_health_check.py calls API without auth headers | CONFIRMED |
| P2-RC-R2-NEW-008 | LOW | gmail_reactions.py hardcoded fallback channel ID | CONFIRMED |
| P2-RC-R2-NEW-009 | COSMETIC | GUILD_ID hardcoded, ignores DISCORD_GUILD_ID from .env.example | CONFIRMED |
| P2-RC-R2-NEW-010 | COSMETIC | .env.example placeholder values not commented out | CONFIRMED |

---

## Part C: Executive Summary

**Round-1 Findings Re-verification:**
- **CONFIRMED (unchanged):** 12
- **CONFIRMED RESOLVED:** 1 (R1-012)
- **PARTIALLY-REFUTED (R1 got it wrong):** 4 (R1-003, R1-007, R1-017, R1-019)
  - R1-003: Age key is on disk but git-ignored, not "in the repo"
  - R1-007: Backup dir is NOT empty; real issue is plaintext credentials R1 missed
  - R1-017: GOTIFY_APP_TOKEN IS in .env.example; R1's grep was incomplete
  - R1-019: Encrypted secret exists locally but is git-untracked; resolution overstated

**Round-2 Miss-Hunt New Findings:**
- HIGH: 2 (shadow-monitor duplicate ref, backup plaintext creds)
- MEDIUM: 3 (secrets/ untracked, GUINEVERE_API_KEY inconsistency, hardcoded localhost)
- LOW: 3 (channel-name routing, health-check auth, gmail hardcoded ID)
- COSMETIC: 2 (GUILD_ID vs .env.example, .env.example placeholder values)

**Key Adversarial Insights:**

1. The most impactful miss by R1 is **R2-NEW-002** (plaintext backup credentials in `secrets/backup/`). Three files contain live S3/restic credentials on disk. The README says to shred them, but they remain.

2. R1's finding R1-003 overstated the severity by claiming the age key is "stored in the repository" without checking git tracking status. The file IS git-ignored. The finding is still HIGH concern, but not CRITICAL as originally stated.

3. R1's finding R1-019 declared RESOLVED without verifying whether the encrypted file is actually git-tracked. It is not. Combined with R1-002 (wrong path in deploy unit), the deploy flow is doubly broken.

4. R1's finding R1-007 focused on a missing `.gitkeep` in a directory that is NOT EMPTY, missing the actual security issue (plaintext backup credentials).

5. R1 missed the hardcoded localhost pattern (8+ modules) which is a significant architectural constraint — R2-NEW-005.

**Dimensions requiring runtime/VPS verification (cannot confirm read-only):**
- Whether the `secrets/backup/*.env` SOPS-encrypted files exist on the VPS (the *-plaintext.env files should NOT be there)
- Whether the age private key is also stored at `/home/guinevere/secrets/age-key.txt` per the README
- Whether Hermes gateway actually starts with `hermes gateway run --accept-hooks` on the installed version
- Whether the VPS has a working `.env.hermes` at the correct path
- Whether channels in channel-ids.yaml match actual Discord channel names
