# P2 Round-1 Audit: Evidence & Docs Consistency

**Auditor:** Claude Code (read-only subagent)
**Date:** 2026-06-25
**Scope:** Evidence-docs-consistency dimension for Phase P2 (Discord)
**Method:** Static file inspection, grep, count verification, cross-doc reconciliation. No runtime/VPS access.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total findings | 16 |
| CRITICAL | 1 |
| HIGH | 5 |
| MEDIUM | 5 |
| LOW | 4 |
| COSMETIC | 1 |

Prior audit (P2-AUDIT-COMPLETE.md, 2026-06-08) found 2 CRITICAL+FAIL items. Current status of both: one is PARTIALLY RESOLVED (P2-002 encrypted file now exists), one is STALE-ERRONEOUS (P2-010: code now has 49 commands, not 35). Eight old findings have drifted. The 33-vs-35-vs-49 command count has grown from a 2-value mismatch to a 3-value mismatch.

---

## Detailed Findings

### P2-EVD-001 [HIGH] Step count: 21 vs 22 mismatch persists

**Files:** CHECKLIST.md:244, PROGRESS.md:134, docs/audit/P2-AUDIT-COMPLETE.md:5

| Document | Stated count | Steps listed |
|----------|-------------|--------------|
| CHECKLIST.md P2 header | "P2-001 through P2-021 (21 steps)" (line 244) | P2-001 through P2-021 — does NOT include P2-022 |
| PROGRESS.md P2 header | "21 steps" (line 134) | P2-001 through P2-022 — 22 steps listed |
| Old audit P2-AUDIT-COMPLETE.md | "Full P2 (22 steps)" (line 5) | Includes P2-022 |

**Description:** CHECKLIST.md says 21 steps (P2-001 through P2-021) but never mentions P2-022 (service masked). PROGRESS.md header says "21 steps" but actually lists 22 steps including P2-022. The old audit correctly documents 22 steps. The CHECKLIST.md has not been updated to include P2-022 or correct its header count.

**Impact:** Implementers following CHECKLIST.md miss P2-022 entirely. New developers get conflicting answers when reconciling step counts.

**Verification:** CONFIRMED

---

### P2-EVD-002 [HIGH] Slash command count: three-way mismatch (33 vs 35 vs 49)

**Files:** CHECKLIST.md:243,265; PROGRESS.md:146; src/discord/_command_registry.py:406-407; src/discord/cmd_help.py:4; docs/audit/P2-AUDIT-COMPLETE.md:63

| Source | Claim | Actual |
|--------|-------|--------|
| CHECKLIST.md line 243 (goal) | "33 slash commands" | Stale |
| CHECKLIST.md line 265 (P2-010) | "33 slash commands" | Stale |
| PROGRESS.md line 146 (P2-010) | "35 commands" | Stale |
| src/discord/_command_registry.py:407 | `require_canonical_registry()` expects **49** commands | Current truth |
| src/discord/cmd_help.py:4 docstring | "lists all 33 slash commands" | Stale |
| Old audit P2-AUDIT-COMPLETE.md | "Code validates expected 35 commands" | Stale — was accurate at old audit time |

**Description:** The command registry (`_command_registry.py`) now has 49 `CommandSpec` entries (13 original + 20 batch D + hermes phase 1 + P12 gmail + P14 health + P18 advanced memory + P5 loop monitoring). The `require_canonical_registry()` function validates `len(names) != 49`. Three different numbers appear across documents:
- CHECKLIST.md still says 33 (last updated during P2 implementation, never revised for later additions)
- PROGRESS.md says 35 (updated from 33 per old audit direction, but never updated again when more commands were added)
- Code has 49 (the only current truth)

Additionally, `cmd_help.py` docstring says "lists all 33 slash commands" which is both incorrect and would generate a wrong /help output.

**Impact:** New developers work from stale numbers. The /help command docstring is misleading. Slash-command onboarding is inaccurate.

**Old audit finding status:** P2-AUDIT-COMPLETE.md P2-010 finding ("PROGRESS.md claims 33 commands. Code has 35.") was PARTIALLY FIXED (PROGRESS.md updated to 35) but is NOW ALSO STALE because code has grown to 49. P2-FIX-PLAN Phase 2 ("Update PROGRESS.md: 33 -> 35 commands") was done but insufficient.

**Verification:** CONFIRMED

---

### P2-EVD-003 [MEDIUM] Channel count: 14 in YAML vs 13 documented

**Files:** docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml; CHECKLIST.md:261; PROGRESS.md:142; P2-AUDIT-COMPLETE.md:33

**Description:** `channel-ids.yaml` lists **14 channels** (4 categories + 14 channels including `rituals` + 3 project ghost channels: `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`). All official documents say 13 channels. The `rituals` channel (ID `1513496377324339262`) was added after the original 13-channel creation. The 3 project ghost channels were flagged in the old audit for cleanup but remain.

Additionally, `#guinevere-dev` (ID `1510914623367413850`) is listed in channel-ids.yaml under that name, but P20 evidence references it as `#guinevere-logs` — the P20 log channel IS channel `1510914623367413850`, which means `guinevere-dev` is now used as `guinevere-logs`. This channel is NOT separately listed in channel-ids.yaml under its active name.

**Impact:** Channel inventory is inaccurate. The 3 ghost channels should be cleaned up or documented as intentional. The `guinevere-dev` / `guinevere-logs` rename is not reflected.

**Verification:** CONFIRMED

---

### P2-EVD-004 [HIGH] Stale claims of standalone service ACTIVE when current design says MASKED

**Files:**
- CHECKLIST.md:273 — `[x] P2-017: systemctl status guinevere-discord -> active`
- CHECKLIST.md:274 — `[x] P2-018: journalctl -u guinevere-discord -n 5 -> "Connected to Discord Gateway"`
- CHECKLIST.md:275 — `[x] P2-019: SEV0 alert test -> thread in #alerts within 15s (AC-DISCORD-003)`
- PROGRESS.md:153 — `[x] **P2-017** guinevere-discord.service creation`
- PROGRESS.md:158 — `[x] **P2-022** guinevere-discord.service masked intentionally`
- docs/setup-evidence/P2/STEP-P2-017/verification.md:144 — "33 commands registered"
- docs/setup-evidence/P2/STEP-P2-018/verification.md:32 — VPS checks all "PENDING"

**Description:** CHECKLIST.md P2-017 and P2-018 claim the `guinevere-discord.service` is active and running. These claims were true during P2 implementation but are now stale — the service was intentionally masked per P2-022 (which IS listed in PROGRESS.md but NOT in CHECKLIST.md). The P2-017 verification.md still references "4 wired + 29 stubs = 33 commands" even though the registry now has 49 commands.

The P2-018 verification.md's VPS checks (V1-V12) are all marked "PENDING" and have never been updated.

P2-019 claims a thread in "#alerts" channel, but `#alerts` does not exist in channel-ids.yaml and is not mapped in `notifications.py`.

**Impact:** Anyone reading CHECKLIST.md as-is will believe the standalone Discord bot is running and active, when it is actually masked per the current architecture. This creates a dangerous operational misunderstanding.

**Verification:** CONFIRMED

---

### P2-EVD-005 [CRITICAL] SOPS naming mismatch: three different file paths in play

**Files:**
- `secrets/discord-secrets.enc.yaml` — actual repo file (SOPS-encrypted, confirmed)
- CHECKLIST.md:257 — references `secrets/discord-secrets.yaml`
- PROGRESS.md:138 — references `secrets/discord-secrets.yaml`
- docs/setup-evidence/P2/STEP-P2-002/verification.md:21 — references `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` (VPS path)
- systemd/guinevere-discord.service:13 — references `.env.discord` (plaintext)
- deploy/discord/guinevere-discord.service:13-14 — references `secrets/.env.discord.sops`
- docs/workflow/opencode-master-template-v3.md:230 — references `secrets/discord-secrets.yaml`

**Description:** Three entirely different naming conventions exist:

| File path | Where used | Type |
|-----------|-----------|------|
| `secrets/discord-secrets.enc.yaml` | **Actual repo file** | SOPS-encrypted YAML |
| `secrets/discord-secrets.yaml` | CHECKLIST, PROGRESS, P2-002 evidence, StepPrompts, workflow docs | **Does NOT exist in repo** |
| `secrets/.env.discord.sops` | deploy/discord/guinevere-discord.service | **Does NOT exist in repo** |
| `.env.discord` | systemd/guinevere-discord.service | Expected plaintext dotenv — **does NOT exist in repo** |

The only actual encrypted secret file is `discord-secrets.enc.yaml` (SOPS-encrypted, confirmed via `head -5` which shows `ENC[AES256_GCM,...]` content). The `.sops.yaml` creation rules match `secrets/.*\.yaml$` (which would match `discord-secrets.enc.yaml`).

The deploy unit's `ExecStartPre` decrypts `secrets/.env.discord.sops` — but this file DOES NOT EXIST in the repo. The systemd unit uses `.env.discord` plaintext — also DOES NOT EXIST in the repo.

**Impact:** The deploy unit references a non-existent file, meaning `ExecStartPre` would fail if the unit were activated. The systemd unit would start with a missing environment file (no token). The only existing encrypted file (`discord-secrets.enc.yaml`) is not referenced by any service unit. There is a complete disconnect between what exists on disk and what the systemd units expect.

**Verification:** CONFIRMED

---

### P2-EVD-006 [MEDIUM] Gotify port mismatch: code says 8081, old audit says 8080

**Files:** src/discord/gotify_fallback.py:32; docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml:7; docs/audit/P2-AUDIT-COMPLETE.md:64

**Description:** `gotify_fallback.py` hardcodes `GOTIFY_URL = "http://localhost:8081"`. The docker-compose.yml maps `"127.0.0.1:8081:80"`. Both the code and Docker config consistently use port 8081.

However, the old audit (P2-AUDIT-COMPLETE.md:64) claims: "Port 8080 responds `{"status":"up"}` on `/health`". This 8080 reference in the old audit was either a misreading or the Gotify service was temporarily on 8080. The current evidence is consistent on 8081.

This is NOT a current bug (code and Docker both agree on 8081), but the old audit's port 8080 claim is stale/incorrect.

**Impact:** Low. No current mismatch. Old audit contains stale 8080 claim.

**Verification:** CONFIRMED — not a current bug, but old audit inaccuracy

---

### P2-EVD-007 [MEDIUM] Notification routing channel drift: `#alerts` referenced but does not exist

**Files:**
- CHECKLIST.md:275 — `[x] P2-019: SEV0 alert test -> thread in #alerts within 15s`
- src/discord/notifications.py:33-37 — `SEV0_CHANNEL = "system-health"`, `SEV1_CHANNEL = "system-health"`, `SEV2_CHANNEL = "cost-tracker"`, `SEV3_CHANNEL = "guinevere-status"`, `SEV4_CHANNEL = "audit-log"`
- docs/setup-evidence/hermes-migration/phase-2-discord.md:69 — `alerts: "guinevere-alerts"`
- docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml — no `#alerts` or `guinevere-alerts` channel listed

**Description:** Three different channel names for alerts exist across documents:
1. CHECKLIST.md claims SEV0 threads go to **`#alerts`**
2. The actual code (`notifications.py`) routes SEV0 to **`system-health`** (and creates threads there)
3. The Hermes migration doc references **`guinevere-alerts`** as the alerts channel

None of these three match each other. There is no `#alerts` or `guinevere-alerts` channel in channel-ids.yaml. Notifications.py routes SEV0/SEV1 to `system-health`, which is the only place alert messages actually go. The `#alerts` reference in CHECKLIST.md is stale from the original P2 design that was never implemented that way.

**Impact:** Misleading documentation. An implementer looking for `#alerts` to wire notification routing would waste time looking for a channel that does not exist.

**Verification:** CONFIRMED

---

### P2-EVD-008 [LOW] P2 -> Hermes/core REST transition is undocumented in CHECKLIST.md

**Files:** CHECKLIST.md:276-277; PROGRESS.md:158; vps-mirror/systemd-live/ (no discord service)

**Description:** The architectural transition from standalone Discord bot (P2) -> Hermes Gateway (ADR-035) -> core REST publisher (P20) is not documented anywhere in CHECKLIST.md. The CHECKLIST.md still implies the standalone bot is the active Discord writer. PROGRESS.md mentions P2-022 (masked) but the transition path is scattered across ADR-035, P20 evidence, and various migration docs. A future implementer reading only CHECKLIST.md would believe the standalone bot is active.

The vps-mirror/systemd-live/ directory contains 12 unit files including hermes-gateway.service, but NO guinevere-discord.service — confirming the service is indeed not active on VPS.

**Impact:** Medium for new contributors; low for current operator (Faiz) who knows the architecture.

**Verification:** CONFIRMED

---

### P2-EVD-009 [MEDIUM] Two conflicting hermes-gateway.service units

**Files:**
- systemd/hermes-gateway.service
- scripts/hermes-gateway.service
- vps-mirror/systemd-live/hermes-gateway.service

| Property | systemd/hermes-gateway.service | scripts/hermes-gateway.service | vps-mirror/live |
|----------|------|------|------|
| ExecStart | `hermes --config .../hermes-config/config.yaml gateway` | `hermes gateway run --accept-hooks` | Same as `scripts/` |
| EnvironmentFile | `.env.hermes` | `.hermes/.env` | Same as `scripts/` |

**Description:** The `systemd/` version and `scripts/` version differ in both ExecStart and EnvironmentFile. The vps-mirror/systemd-live/ copy matches `scripts/` not `systemd/`, suggesting the `scripts/` version is the deployed one and `systemd/` may be the template.

**Impact:** Low to medium — if someone copies the wrong unit during deployment, the bot would either fail to find its config or fail to load environment variables.

**Verification:** CONFIRMED — vps-mirror matches `scripts/`, not `systemd/`

---

### P2-EVD-010 [MEDIUM] Prior audit P2-002 CRITICAL is PARTIALLY RESOLVED

**Files:** docs/audit/P2-AUDIT-COMPLETE.md:57; secrets/discord-secrets.enc.yaml

**Old finding (P2-AUDIT-COMPLETE.md, 2026-06-08):** "Encrypted secret MISSING. secrets/discord-secrets.yaml from evidence DOES NOT EXIST. Token is stored in plaintext in ~/.hermes/.env."

**Current state:** `secrets/discord-secrets.enc.yaml` DOES EXIST and IS SOPS-encrypted (confirmed via `head -5` showing `ENC[AES256_GCM,...]` content). The file is readable as ciphertext without decryption. However:
- The file is named `discord-secrets.enc.yaml` not `discord-secrets.yaml` (naming mismatch)
- No `.env.discord.sops` file exists for the deploy unit's `ExecStartPre`
- No `.env.discord` plaintext exists in the repo
- Whether `~/.hermes/.env` still contains a plaintext token is UNVERIFIABLE without VPS access

**Impact:** The encryption gap is closed. The naming/documentation gap remains open.

**Verification:** PARTIALLY RESOLVED — crypto gap closed, naming/docs gap open

---

### P2-EVD-011 [MEDIUM] Old audit P2-010 finding (33->35) now stale: code has 49 commands

**Files:** docs/audit/P2-AUDIT-COMPLETE.md:63; docs/audit/P2-FIX-PLAN.md:11; src/discord/_command_registry.py:406-407

**Old finding (P2-AUDIT-COMPLETE.md):** "PROGRESS.md claims 33 commands. Code has 35." — P2-FIX-PLAN Phase 2 directed updating PROGRESS.md to 35.

**Current state:** PROGRESS.md was updated to say "35 commands" for P2-010. But the code has since grown to **49** commands (validated by `require_canonical_registry()` at line 407). The fix was applied but the target number moved. CHECKLIST.md was never updated (still says 33). Neither document reflects the current 49 commands.

**Impact:** All three documents (CHECKLIST 33, PROGRESS 35, code 49) disagree. The old FIX-PLAN item needs a more durable solution (e.g., a dynamic count reference rather than hardcoded numbers).

**Verification:** CONFIRMED — old fix applied but now stale

---

### P2-EVD-012 [LOW] Missing auditor-gate.md in P2 step evidence directories

**Files:** docs/setup-evidence/P2/STEP-P2-*/ (all 21 directories)

**Description:** Later phases (P3 onward) include an `auditor-gate.md` file in each step's evidence directory as a standard pattern. P2 step directories contain `verification.md` and optionally `verifiers/` subdirs, but NO `auditor-gate.md` files. The old audit reports exist at `audit-reports/P2/STEP-P2-*/` but not in the step evidence dirs.

**Impact:** Low — evidence is present but in a different location than later-phase conventions. Not an implementation issue.

**Verification:** CONFIRMED

---

### P2-EVD-013 [LOW] cmd_help.py docstring says "33 commands" but registry has 49

**File:** src/discord/cmd_help.py:4

**Description:** The module docstring says "The embed lists all 33 slash commands grouped by their 7 categories". The actual `build_help_embed_data()` function imports from `_command_registry.py` which now has 49 commands. The code would generate accurate output dynamically, but the docstring is misleading.

**Impact:** Low — cosmetic, code behavior is correct, only the docstring is wrong.

**Verification:** CONFIRMED

---

### P2-EVD-014 [LOW] Two guinevere-discord.service units conflict on token source

**Files:**
- systemd/guinevere-discord.service:13 — `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord`
- deploy/discord/guinevere-discord.service:13-15 — `ExecStartPre` decrypts `secrets/.env.discord.sops` -> `/run/guinevere-discord-token`, then `EnvironmentFile=/run/guinevere-discord-token`

**Description:** The `systemd/` unit uses a plaintext dotenv file (`.env.discord`). The `deploy/` unit uses SOPS-decrypted token in `/run/`. Only the `deploy/` version follows the security pattern (decrypt->shred on stop). The `systemd/` version would load a plaintext token.

Additionally, neither file references `secrets/discord-secrets.enc.yaml`, which is the ONLY encrypted Discord secret file in the repo.

**Impact:** If the `systemd/` unit were used for deployment and `.env.discord` existed in plaintext, a plaintext token would be readable on disk.

**Verification:** CONFIRMED

---

### P2-EVD-015 [HIGH] HARD STOP text detection IS wired in _entrypoint.py (seed fact was WRONG)

**File:** src/discord/_entrypoint.py:155-157; src/discord/cmd_safeword.py:591-643

**Seed fact claimed:** `cmd_safeword.py` docstring says "No bot.py listener exists yet. This function is callable and documented but inactive until P2-017 wires it." — implying HARD STOP text detection is UNWIRED.

**Actual state:** `_entrypoint.py` line 155 does `from .cmd_safeword import handle_safeword_message_async` and line 157 calls `consumed = await handle_safeword_message_async(message)` in the `_on_message_listener`. The HARD STOP text detection IS wired into the `_entrypoint.py` listener.

The docstring at line 21 still says "No bot.py listener exists yet..." which references the old `bot.py` (deprecated). The active `_entrypoint.py` DOES wire it.

**Impact:** The docstring is stale, referencing the old `bot.py` entrypoint. A reader checking whether HARD STOP detection is active would find conflicting information: the docstring says it's inactive, while the actual code shows it's wired.

**Verification:** CONFIRMED — seed fact was incorrect about wiring; docstring is stale

---

### P2-EVD-016 [LOW] prior old-audit P2-020 Gotify finding port discrepancy

**File:** docs/audit/P2-AUDIT-COMPLETE.md:64; docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml:7

**Old audit claim:** "Port 8080 responds `{"status":"up"}` on `/health`"

**Current state:** Both `gotify_fallback.py` and `docker-compose.yml` consistently use port **8081** (not 8080). The docker-compose.yml maps `"127.0.0.1:8081:80"`. The old audit's port 8080 reference is a minor error — either the Gotify service was temporarily on 8080 or the auditor misread the config.

**Impact:** Cosmetic inaccuracy in old audit. No current operational impact.

**Verification:** CONFIRMED — old audit contains 8080 error

---

## Old Audit Findings Recheck Summary

| Old Finding (P2-AUDIT-COMPLETE.md) | Severity | Status | Notes |
|-------------------------------------|----------|--------|-------|
| P2-002: CRITICAL — encrypted secret missing | CRITICAL | **PARTIALLY RESOLVED** | `discord-secrets.enc.yaml` exists (SOPS). But naming mismatch persists, deploy unit's `.env.discord.sops` missing, systemd unit references `.env.discord` plaintext. |
| P2-010: PROGRESS.md 33 vs code 35 | HIGH | **STALE** | PROGRESS.md updated to 35, but code now has 49. CHECKLIST.md still says 33. |
| P2-020: Gotify port 8080 vs code | LOW | **STALE** | Code and docker-compose both use 8081. Old audit's 8080 was wrong. |
| Channel cleanup (10/13 empty, 3 ghosts) | MEDIUM | **UNRESOLVED** | Ghost channels still in channel-ids.yaml. No cleanup performed. |
| Automation (cron for empty channels) | MEDIUM | **UNRESOLVED** | Not implemented per FIX-PLAN Phase 4 items. |

## P2-FIX-PLAN.md Status

| Phase | Action | Status |
|-------|--------|--------|
| 1: SOPS Encryption | Encrypt token -> discord-secrets.enc.yaml | **DONE** |
| 1: Update .hermes/.env | Update env loading | **NEEDS VPS VERIFICATION** |
| 1: Verify token works | Verify token after encryption | **NEEDS VPS VERIFICATION** |
| 2: PROGRESS.md 33->35 | Update command count | **PARTIALLY DONE** (now needs 35->49) |
| 3: Delete ghost channels | Clean up project-* channels | **NOT DONE** |
| 3: Rename guinevere-dev | Rename to guinevere-logs | **NOT DONE** |
| 4: Automation (cron) | Fill empty channels | **NOT DONE** |

## Recommendations

1. **Durable command count**: Replace hardcoded command counts in CHECKLIST.md and PROGRESS.md with a reference to `_command_registry.py:command_count()` or generate them dynamically. At minimum, update all three documents to say 49.

2. **CHECKLIST.md P2 rewrite**: The entire P2 section of CHECKLIST.md is outdated. It needs a comprehensive update reflecting: (a) P2-022 (service masked), (b) command count 49, (c) channel count including rituals, (d) current notification routing channels, (e) P2 -> Hermes -> REST publisher transition.

3. **Secret file naming**: Reconcile the three naming conventions. Either rename `discord-secrets.enc.yaml` to match docs, or update all references. Create the missing `secrets/.env.discord.sops` that the deploy unit expects, or update the deploy unit to reference the existing file.

4. **cmd_help.py docstring**: Update docstring from "33" to reflect dynamic count.

5. **Channel inventory**: Clean up ghost channels or document them. Add `guinevere-logs` alias or rename `guinevere-dev` in channel-ids.yaml.

6. **cmd_safeword.py docstring**: Update the stale "No bot.py listener exists yet" note to reflect that `_entrypoint.py` wires it.

7. **hermes-gateway.service reconciliation**: Decide which unit is canonical and document the difference. Update vps-mirror if needed.
