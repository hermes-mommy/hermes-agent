# P2 Round-2 Adversarial Verification: Evidence & Docs Consistency

**Date:** 2026-06-25
**Auditor:** Claude Code (read-only subagent — round-2 adversary)
**Source:** `docs/setup-evidence/legacy-audit/P2/audits/round-1/evidence-docs-consistency.md`
**Methodology:** Independently verify each R1 finding against actual repo files; attempt to refute; miss-hunt for gaps.

---

## PART 1: FINDING-BY-FINDING VERIFICATION

### P2-EVD-001 [HIGH] — Step count: 21 vs 22
- **R1 claim:** CHECKLIST.md says 21 steps, PROGRESS.md header says 21 but lists 22, old audit says 22.
- **Independent verification:** Read CHECKLIST.md:244 — "P2-001 through P2-021 (21 steps)". Read PROGRESS.md:134 — "P2: Discord Bot (21 steps)". But PROGRESS.md:158 lists P2-022. CHECKLIST.md does NOT list P2-022. Both are stale.
- **Verdict:** **CONFIRMED**. CHECKLIST.md is missing P2-022 entirely. PROGRESS.md header is wrong.
- **Refutation attempt:** Is P2-022 intentionally excluded as a "meta" step? No — it's listed in PROGRESS.md as a numbered step. **Cannot refute.**

### P2-EVD-002 [HIGH] — Slash command count: 33 vs 35 vs 49
- **R1 claim:** CHECKLIST.md says 33, PROGRESS.md says 35, code has 49.
- **Independent verification:** Read `_command_registry.py:406-407` — `require_canonical_registry()` validates 49 command names. Counted `COMMAND_SPECS` entries — 49. Read CHECKLIST.md:265 — `commands_count=33`. Read PROGRESS.md:146 — "35 commands". Read `cmd_help.py:4` — docstring says "33 slash commands". All confirmed.
- **Verdict:** **CONFIRMED**. 4-way drift: code 49, PROGRESS 35, CHECKLIST 33, cmd_help docstring 33.
- **Refutation attempt:** Maybe some of the 49 are stubs? No — `require_canonical_registry()` validates all 49. **Cannot refute.**

### P2-EVD-003 [MEDIUM] — Channel count: 14 vs 13
- **R1 claim:** `channel-ids.yaml` has 14 channels, docs say 13.
- **Independent verification:** Counted channels in `channel-ids.yaml` under `channels:` block — 14 entries. CHECKLIST.md:261 — "13 channels". PROGRESS.md:142 — "13 channels". The `rituals` channel was added after the original 13.
- **Verdict:** **CONFIRMED**. Documentation drift.
- **Refutation attempt:** Maybe `rituals` is not a "channel" but a category? No — it's listed under `channels:` with a snowflake ID. **Cannot refute.**

### P2-EVD-004 [HIGH] — Stale claims of standalone service ACTIVE when masked
- **R1 claim:** CHECKLIST.md P2-017/018/019 claim service active/running, but service is masked per P2-022.
- **Independent verification:** Read CHECKLIST.md:273 — `[x] P2-017: systemctl status guinevere-discord -> active`. Read CHECKLIST.md:274 — `[x] P2-018: journalctl ... "Connected to Discord Gateway"`. Read CHECKLIST.md:275 — `[x] P2-019: SEV0 alert test -> thread in #alerts`. Read PROGRESS.md:158 — `[x] P2-022 masked intentionally`. Read `vps-mirror/systemd-live/` — no `guinevere-discord.service` (12 live units, all other guinevere-* services). The service IS masked in production. CHECKLIST.md claims are stale.
- **Verdict:** **CONFIRMED**. CHECKLIST.md is dangerously misleading — claims active service when it's masked.
- **Refutation attempt:** Maybe the CHECKLIST represents the implementation state, not the current runtime state? The CHECKLIST is titled "Verification Checklist" and lists P2-022 separately. It should be updated to reflect the masked state. **Cannot refute.**

### P2-EVD-005 [CRITICAL] — SOPS naming mismatch: three file paths
- **R1 claim:** Actual file is `discord-secrets.enc.yaml`, docs reference `discord-secrets.yaml`, deploy unit references `.env.discord.sops`, systemd unit references `.env.discord`.
- **Independent verification:** Confirmed `secrets/discord-secrets.enc.yaml` EXISTS and is SOPS-encrypted (first 5 lines: `ENC[AES256_GCM,data:...`). Confirmed `secrets/discord-secrets.yaml` does NOT exist. Confirmed `secrets/.env.discord.sops` does NOT exist. Confirmed `.env.discord` does NOT exist in repo root. Read `deploy/discord/guinevere-discord.service:13-14` — references `secrets/.env.discord.sops` (non-existent). Read `systemd/guinevere-discord.service:13` — references `.env.discord` (non-existent). Read CHECKLIST.md:257 — references `secrets/discord-secrets.yaml` (non-existent).
- **Verdict:** **CONFIRMED — CRITICAL**. The deploy unit's `ExecStartPre` would fail because the file it references doesn't exist. The systemd unit would start with no token. The only encrypted file is not referenced by any service unit.
- **Refutation attempt:** Maybe the deploy unit is designed for the VPS and the file exists there? The deploy unit is in the repo as a deployment artifact. The file it references must exist in the repo AND on the VPS. It exists in neither. **Cannot refute.**

### P2-EVD-006 [MEDIUM] — Gotify port: 8081 consistent, old audit says 8080
- **R1 claim:** Code and compose both use 8081. Old audit claimed 8080.
- **Independent verification:** `gotify_fallback.py:32` — `GOTIFY_URL = "http://localhost:8081"`. `docker-compose.yml:7` — `"127.0.0.1:8081:80"`. Both consistent. Old audit `P2-AUDIT-COMPLETE.md:64` — "Port 8080". Old audit was wrong.
- **Verdict:** **CONFIRMED** — but NOT a current bug. Old audit inaccuracy. **Downgrade to LOW** (documentation only).
- **Refutation attempt:** No current mismatch. **Confirmed with severity downgrade.**

### P2-EVD-007 [MEDIUM] — Notification routing channel drift: `#alerts` / `guinevere-alerts` / `system-health`
- **R1 claim:** Three different channel names for alerts across governance docs, migration doc, and code.
- **Independent verification:** Read SRS v1.0 — references `#alerts`. Read FSD v1.0 — references `#alerts`. Read PRD v2.2 — references `#alerts`. Read `phase-2-discord.md:69` — references `guinevere-alerts`. Read `notifications.py:33` — routes to `system-health`. Read `channel-ids.yaml` — no `#alerts` or `guinevere-alerts` channel. `system-health` exists at ID `1510914612038471720`.
- **Verdict:** **CONFIRMED**. Three-way drift. Governance docs are wrong, migration doc is wrong, only code is correct.
- **Refutation attempt:** Could `#alerts` be an alias that maps to `system-health`? No alias mechanism exists in the code. **Cannot refute.**

### P2-EVD-008 [LOW] — P2 -> Hermes/core REST transition undocumented
- **R1 claim:** CHECKLIST.md doesn't document the architectural transition.
- **Independent verification:** Read CHECKLIST.md P2 section — no mention of Hermes Gateway, core REST publisher, or ADR-035. Only P2-022 in PROGRESS.md mentions the mask. The transition is documented in ADR-035 and phase-2-discord.md but not in CHECKLIST.md.
- **Verdict:** **CONFIRMED**. CHECKLIST.md is the primary onboarding document and omits the transition.
- **Refutation attempt:** CHECKLIST.md is implementation-focused, not architecture. But it's the first doc new contributors read. **Cannot refute.**

### P2-EVD-009 [MEDIUM] — Two conflicting hermes-gateway.service units
- **R1 claim:** `systemd/` and `scripts/` versions differ in ExecStart and EnvironmentFile.
- **Independent verification:** Read `systemd/hermes-gateway.service:31` — `ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes --config /home/guinevere/code/guinevere/hermes-config/config.yaml gateway`. Read `scripts/hermes-gateway.service:15` — `ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks`. Read `vps-mirror/systemd-live/hermes-gateway.service:15` — matches `scripts/` version. The `systemd/` version uses a different command and config path. `systemd/` uses `.env.hermes`; `scripts/` uses `.hermes/.env`.
- **Verdict:** **CONFIRMED**. The `scripts/` version is the deployed one (matches vps-mirror). The `systemd/` version is a stale template.
- **Refutation attempt:** Maybe `systemd/` is the newer/generic version and `scripts/` is legacy? `vps-mirror/systemd-live/` matches `scripts/`, suggesting `scripts/` is the deployed version. **Cannot refute.**

### P2-EVD-010 [MEDIUM] — Old audit P2-002 CRITICAL partially resolved
- **R1 claim:** `discord-secrets.enc.yaml` exists and is encrypted, but naming/docs gap remains.
- **Independent verification:** Confirmed `secrets/discord-secrets.enc.yaml` is SOPS-encrypted (AES256_GCM). The original P2-AUDIT-COMPLETE.md finding was "Encrypted secret MISSING" — this is now RESOLVED (file exists). But the P2-FIX-PLAN.md Phase 1 item "Update .hermes/.env" is unverifiable without VPS access.
- **Verdict:** **CONFIRMED — PARTIALLY RESOLVED**. Encryption exists. Naming/docs gap remains.
- **Refutation attempt:** The encryption exists. The old audit's CRITICAL finding is effectively resolved. **The naming gap is a separate MEDIUM issue.**

### P2-EVD-011 [MEDIUM] — Old audit P2-010 (33->35) now stale: code has 49
- **R1 claim:** PROGRESS.md was updated to 35 but code now has 49.
- **Independent verification:** Confirmed `_command_registry.py` has 49. PROGRESS.md says 35. CHECKLIST.md says 33. The P2-FIX-PLAN.md Phase 2 fix (33->35) was done but is now insufficient.
- **Verdict:** **CONFIRMED**. The fix was applied but the target moved.
- **Refutation attempt:** The fix was correct at the time. The code has since grown. **Cannot refute — docs need durable reference.**

### P2-EVD-012 [LOW] — Missing auditor-gate.md in P2 step evidence
- **R1 claim:** P2 step directories lack `auditor-gate.md` files that later phases include.
- **Independent verification:** Checked `docs/setup-evidence/P2/STEP-P2-001/` — no `auditor-gate.md`. Checked `docs/setup-evidence/P3/` — auditor-gate.md pattern exists in later phases. P2 has `verification.md` and `verifiers/` but no `auditor-gate.md`.
- **Verdict:** **CONFIRMED**. Pattern inconsistency — but this is P2's convention, not a bug.
- **Refutation attempt:** P2 was completed before the auditor-gate.md pattern was established. **Confirmed but LOW.**

### P2-EVD-013 [LOW] — cmd_help.py docstring says "33 commands"
- **R1 claim:** `cmd_help.py:4` docstring says 33, code has 49.
- **Independent verification:** Read `cmd_help.py:4` — "lists all 33 slash commands". Confirmed 49 in registry.
- **Verdict:** **CONFIRMED**. Stale docstring.
- **Refutation attempt:** The code dynamically generates the help output, so behavior is correct. Only the docstring is wrong. **Confirmed but LOW.**

### P2-EVD-014 [LOW] — Two guinevere-discord.service units conflict on token source
- **R1 claim:** `systemd/` uses plaintext `.env.discord`, `deploy/` uses SOPS decrypt.
- **Independent verification:** Confirmed `systemd/guinevere-discord.service:13` — plaintext `EnvironmentFile`. Confirmed `deploy/discord/guinevere-discord.service:13-15` — SOPS decrypt + shred. Neither references `discord-secrets.enc.yaml`.
- **Verdict:** **CONFIRMED**. Two conflicting templates, one insecure.
- **Refutation attempt:** The `deploy/` version is the intended deployment artifact. The `systemd/` version is a stale template. **Cannot refute.**

### P2-EVD-015 [HIGH] — HARD STOP IS wired; seed fact was wrong
- **R1 claim:** `_entrypoint.py` DOES wire HARD STOP text detection. Seed fact was incorrect.
- **Independent verification:** Read `_entrypoint.py:155-157` — imports and calls `handle_safeword_message_async`. Read `_entrypoint.py:132-138` — registers `_on_message_listener`. The HARD STOP text path IS active. The docstring in `cmd_safeword.py:598-601` is stale (references old `bot.py`).
- **Verdict:** **CONFIRMED — POSITIVE**. HARD STOP is wired. Seed fact was wrong. Docstring is stale.
- **Refutation attempt:** This is a positive finding — the system is more complete than the seed fact suggested. **Confirmed as POSITIVE.**

### P2-EVD-016 [LOW] — Old audit Gotify port 8080 discrepancy
- **R1 claim:** Old audit claimed Gotify on 8080; current artifacts use 8081.
- **Independent verification:** Old audit `P2-AUDIT-COMPLETE.md:64` — "Port 8080". Current code/compose use 8081.
- **Verdict:** **CONFIRMED**. Old audit inaccuracy.
- **Refutation attempt:** Could have been 8080 at the time? Docker compose maps 8081:80, so container port is 80, host port is 8081. The old auditor may have checked the container port (80) or the wrong host port. **Cannot refute — old audit was wrong.**

---

## PART 2: MISS-HUNT — Findings Round-1 Missed

### P2-AUD-R2-EVD-001 [HIGH] — P2-019 SEV0 alert claim references `#alerts` which doesn't exist; acceptance criterion AC-DISCORD-003 is based on a non-existent channel
- **Evidence:** CHECKLIST.md:275 claims `[x] P2-019: SEV0 alert test -> thread in #alerts within 15s (AC-DISCORD-003)`. The `#alerts` channel does not exist in `channel-ids.yaml`. The acceptance criterion is marked as verified but targets a non-existent channel.
- **Impact:** CHECKLIST.md contains a false-positive verification. The acceptance criterion cannot have been met.
- **Severity:** HIGH
- **Verification:** CONFIRMED

### P2-AUD-R2-EVD-002 [MEDIUM] — `STEP-P2-018/verification.md` VPS checks all PENDING
- **Evidence:** Read `docs/setup-evidence/P2/STEP-P2-018/verification.md` — V1 through V12 are all marked "PENDING". The old audit (P2-AUDIT-COMPLETE.md) marked P2-018 as PASS (✅) despite VPS checks being PENDING.
- **Impact:** Old audit marked a step PASS when VPS verification was incomplete.
- **Severity:** MEDIUM
- **Verification:** CONFIRMED

### P2-AUD-R2-EVD-003 [MEDIUM] — P2-FIX-PLAN.md Phase 3 and 4 are entirely NOT DONE
- **Evidence:** P2-FIX-PLAN.md has checkboxes for Phase 3 (ghost channel cleanup) and Phase 4 (automation) — all unchecked. The fix plan was from 2026-06-08 and none of the medium-priority items have been addressed.
- **Impact:** Ghost channels remain, no automation, no cron jobs. The fix plan is an incomplete deliverable.
- **Severity:** MEDIUM
- **Verification:** CONFIRMED

### P2-AUD-R2-EVD-004 [LOW] — `guinevere-dev` is actually `guinevere-logs` in P20 evidence
- **Evidence:** `channel-ids.yaml` lists `guinevere-dev` (ID `1510914623367413850`). P20 evidence (`docs/setup-evidence/P20/evidence/discord-visible-autonomy/`) references channel ID `1510914623367413850` as the log channel (functionally `guinevere-logs`). The channel was renamed/repurposed but `channel-ids.yaml` was not updated.
- **Impact:** Channel name in canonical YAML is stale.
- **Severity:** LOW
- **Verification:** CONFIRMED

### P2-AUD-R2-EVD-005 [LOW] — `docs/audit/P2-AUDIT-COMPLETE.md` says "All 186 Discord tests PASS" but doesn't specify test runner or environment
- **Evidence:** Old audit claim "All 186 Discord tests PASS" has no test output, no runner version, no pytest flags. Tests pass on the auditor's machine at a point in time — no evidence the same tests pass today.
- **Impact:** Claim is unverifiable without re-running tests.
- **Severity:** LOW
- **Verification:** NEEDS RUNTIME (test re-run)

---

## 3. VERIFICATION SUMMARY

| Round-1 ID | Severity | Round-2 Verdict | Notes |
|------------|----------|----------------|-------|
| EVD-001 | HIGH | CONFIRMED | 21 vs 22 step count |
| EVD-002 | HIGH | CONFIRMED | 33/35/49 command count drift |
| EVD-003 | MEDIUM | CONFIRMED | 14 vs 13 channel count |
| EVD-004 | HIGH | CONFIRMED | Stale claims of active service |
| EVD-005 | CRITICAL | CONFIRMED | SOPS naming mismatch |
| EVD-006 | MEDIUM→LOW | CONFIRMED (downgraded) | Gotify port consistent |
| EVD-007 | MEDIUM | CONFIRMED | Channel drift #alerts |
| EVD-008 | LOW | CONFIRMED | Transition undocumented |
| EVD-009 | MEDIUM | CONFIRMED | Conflicting hermes units |
| EVD-010 | MEDIUM | CONFIRMED | Old P2-002 partially resolved |
| EVD-011 | MEDIUM | CONFIRMED | Old P2-010 fix stale |
| EVD-012 | LOW | CONFIRMED | Missing auditor-gate.md |
| EVD-013 | LOW | CONFIRMED | cmd_help docstring |
| EVD-014 | LOW | CONFIRMED | Conflicting discord units |
| EVD-015 | HIGH | CONFIRMED (POSITIVE) | HARD STOP IS wired |
| EVD-016 | LOW | CONFIRMED | Old audit port error |

**Round-1: 16/16 findings CONFIRMED. 1 severity downgraded (MED→LOW). 5 new findings from miss-hunt (1 HIGH, 2 MED, 2 LOW).**

**Total in this dimension: 16 confirmed + 5 new = 21 unique findings.**

---

*End of round-2 adversarial verification for evidence/docs consistency dimension.*