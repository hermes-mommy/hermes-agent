# Auditor Report — STEP-P2-007 Discord Channel Permissions

**Step:** P2-007 — Channel permissions  
**Date:** 2026-06-01  
**Verdict:** PASS  
**Auditor:** Guinevere (independent per-step gate)  
**Report path:** `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md`

---

## 1. Scope and Approach

This auditor verifies the P2-007 channel permission overwrite implementation against the acceptance criteria defined in `docs/setup-evidence/P2/batch-plan-007-009.md` and the P2-007 step requirement. Verification is file-based: all source files, evidence artifacts, and runtime output are read and inspected.

**Read files:**

| File | Purpose |
|---|---|
| `docs/setup-evidence/P2/STEP-P2-007/verification.md` | P2-007 evidence file |
| `docs/setup-evidence/P2/batch-plan-007-009.md` | Planner gate and acceptance criteria |
| `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Source-of-truth channel IDs |
| `src/discord/permissions.py` | New implementation module |
| `src/discord/guild_setup.py` | Pre-existing helpers (token, CHANNELS) |
| `tmp/setup-p2-007-permissions.py` | Apply script |
| `tmp/verify-p2-007-permissions-rest.py` | Verify script |
| `scripts/run-discord-verify.sh` | SOPS temp decrypt wrapper |

**Not mutated:** Discord API, VPS, secrets, or evidence files.

---

## 2. Acceptance Criteria Verification

| # | Criterion | Result | Evidence |
|---|---|---|---|
| AC-1 | All 13 canonical channels verified PASS | ✅ PASS | verification.md §3: both apply and verify outputs show all 13 rows `ok=true` and `result=PASS` |
| AC-2 | @everyone visibility denied | ✅ PASS | `everyone_private=true` for all 13 channels in both outputs; code sets `EVERYONE_DENY = VIEW_CHANNEL` on guild_id/type=0 |
| AC-3 | Faiz/Samm owner read/write or read-only matrix correct | ✅ PASS | Normal channels (10): `owner_read=true`, `owner_send_expected=true`, `owner_send_actual=true`. Append-only channels (3): `owner_read=true`, `owner_send_expected=false`, `owner_send_actual=false` |
| AC-4 | Evidence/archive append-only approximation documented | ✅ PASS | verification.md §8 explicitly documents true write-only impossibility; batch-plan §3.3 documents approximation strategy |
| AC-5 | Bot access configured; Administrator bypass caveat documented for P2-009 | ✅ PASS | `bot_send=true` for all 13 channels. verification.md §8: "bot currently has Administrator... P2-009 must review." Batch-plan §3.4 details Administrator caveat |
| AC-6 | No hardcoded channel IDs in new code | ✅ PASS | `permissions.py` line 20 reads from `channel-ids.yaml`; `read_channel_ids()` function parses YAML at runtime; no Discord snowflakes in new code |
| AC-7 | Token handling uses SOPS temp wrapper; no token-shaped secrets | ✅ PASS | `run-discord-verify.sh`: SOPS decrypt to `mktemp`, shred on EXIT trap, `DISCORD_SECRETS_PATH` env. Scripts call `token_from_environment()` → `get_token()`. Token-shaped regex scan: only key name `discord_bot_token` in docstrings; no actual token values |
| AC-8 | No unsafe shortcuts | ✅ PASS | grep confirms zero `# type: ignore`, zero bare `except:`, zero `as any`/`@ts-ignore`. Python `cast()` usage follows runtime type guards (`isinstance` checks before cast); no type safety bypass |
| AC-9 | Evidence has all 12 requested sections | ✅ PASS | verification.md sections 1–12 confirmed via grep: `^## \d+\.` matches exactly 12 |
| AC-10 | No premature tracker sync | ✅ PASS | verification.md §5: "Pending until P2-007, P2-008, and P2-009 all pass" — explicitly does NOT mark PROGRESS/CHECKLIST/StepPrompts complete |
| AC-11 | SOPS wrapper allows P2-007 scripts | ✅ PASS | `run-discord-verify.sh` allowlist includes `tmp/setup-p2-007-permissions.py` and `tmp/verify-p2-007-permissions-rest.py` |
| AC-12 | Both runtime apply and verify agree | ✅ PASS | Apply output and verify output are byte-identical for all 13 channels across all 6 columns; both show `result=PASS` |

---

## 3. Detailed File Audit

### 3.1 `src/discord/permissions.py`

| Check | Result |
|---|---|
| No hardcoded channel IDs | ✅ Reads from `channel-ids.yaml` |
| No hardcoded guild IDs | ✅ Discovers guild via `/users/@me/guilds` + name match |
| No hardcoded user/member IDs | ✅ Owner from guild object; bot from `/users/@me` |
| Channel names consistent with YAML | ✅ `read_channel_ids()` validates against `CHANNELS` tuple (13 expected names) |
| Append-only channels match plan | ✅ `APPEND_ONLY_CHANNELS = frozenset({"guinevere-evidence", "evidence-log", "audit-log"})` — matches batch-plan §4 |
| Permission bit constants correct | ✅ `VIEW_CHANNEL=1<<10`, `SEND_MESSAGES=1<<11`, `READ_MESSAGE_HISTORY=1<<16`, etc. — standard Discord API values |
| `cast()` usage type-safe | ✅ All `cast()` calls are preceded by runtime `isinstance()` or structure checks in guard functions (`require_mapping`, `require_list`) |
| No token value in logs | ✅ `format_permission_results()` only outputs sanitized booleans; no raw IDs or token data |
| `discord_request()` handles errors | ✅ Raises `RuntimeError` with HTTP status + truncated body on non-2xx |
| Token cleanup | ✅ `token_from_environment()` delegates to `get_token()`; CLI scripts set `token = ""` in `finally` |
| No PyYAML dependency | ✅ Uses minimal line-based parser compatible with SOPS YAML format |

### 3.2 `tmp/setup-p2-007-permissions.py`

| Check | Result |
|---|---|
| Token lifecycle | ✅ Reads via `token_from_environment()`, clears to `""` in `finally` |
| Exit code on failure | ✅ `raise SystemExit(1)` after FAIL verdict |
| No unsafe patterns | ✅ No `# type: ignore`, no bare except, no `cast` abuse |
| Simple, single-purpose | ✅ 23 lines, one `main()` function |

### 3.3 `tmp/verify-p2-007-permissions-rest.py`

| Check | Result |
|---|---|
| Read-only verification | ✅ Calls `verify_permissions()` only — no mutation |
| Token lifecycle | ✅ Same safe pattern as setup script |
| Consistent format output | ✅ Same `format_permission_results()` + `result=` line |
| No unsafe patterns | ✅ Clean |

### 3.4 `scripts/run-discord-verify.sh`

| Check | Result |
|---|---|
| SOPS decrypt | ✅ `sops --decrypt` to temp file |
| Temp file cleanup | ✅ `trap cleanup EXIT` — shred + unset |
| Allowlist includes P2-007 | ✅ Both scripts in `case` pattern |
| No token echo/capture | ✅ No grep/awk extraction of token |
| No persistent plaintext | ✅ `mktemp` → `shred -u` on exit |

### 3.5 `docs/setup-evidence/P2/STEP-P2-007/verification.md`

| Check | Result |
|---|---|
| 12 sections present | ✅ Confirmed |
| No token exposure | ✅ No token values anywhere in document |
| No premature sync | ✅ §5: "Pending until all pass" |
| Caveats documented | ✅ §8 covers append-only limitation, Administrator bypass, ID source rule |
| Security scan reported | ✅ §10 documents token-shaped regex clean |
| Rollback safety | ✅ §7: idempotent re-run, option to remove overwrites |

---

## 4. Cross-Cut Checks

### 4.1 Batch-Plan §3.1 — ID Source Rule

**PASS.** New `permissions.py` code does not hardcode channel/category IDs. It reads them from `channel-ids.yaml` via `read_channel_ids()`. Guild context (guild_id, owner_id, bot_id) is discovered at runtime via Discord REST API.

### 4.2 Batch-Plan §3.2 — Permission Strategy

**PASS.** @everyone denied `view_channel` on all canonical channels. Faiz/Samm: read/write on normal, read-only on evidence/archive. Bot: send/read/embed/attach on all channels, denied destructive management on append-only.

### 4.3 Batch-Plan §3.3 — Evidence Write-Only Limitation

**PASS.** The limitation is documented in both the batch-plan (§3.3) and verification.md (§8). The implementable approximation (bot can send, Faiz read-only, destructive permissions denied) is applied correctly.

### 4.4 Batch-Plan §3.4 — Administrator Caveat

**PASS.** verification.md §8 explicitly states Administrator bypasses bot overwrites and defers reduction decision to P2-009. Batch-plan §3.4 documents the Administrator review requirement.

### 4.5 Batch-Plan §11 — Token Security Rules

**PASS.** All 7 security rules are satisfied:
1. ✅ `SOPS_AGE_KEY_FILE` set in shell wrapper
2. ✅ SOPS decrypt to temp YAML
3. ✅ `DISCORD_SECRETS_PATH` exported
4. ✅ Python reads token from temp path
5. ✅ `token = ""` cleanup in `finally`
6. ✅ `shred -u` on temp file via EXIT trap
7. ✅ No partial token printing or extraction

### 4.6 Batch-Plan §12 — Static Verification Commands

**PASS.** Verification evidence reports:
- `lsp_diagnostics` clean on all 3 changed Python files
- Python compile passed (local + VPS)
- Token-shaped regex scan: clean

### 4.7 Batch-Plan §13 — Evidence 12-Section Schema

**PASS.** All 12 sections present in verification.md.

---

## 5. Findings

### 5.1 Passed Items (No Issues)

All acceptance criteria pass. Zero blocking issues, zero introduced diagnostics, zero token exposure, zero unsafe shortcuts.

### 5.2 Minor Observations (Non-Blocking, Documented for Awareness)

1. **`guild_setup.py` hardcodes GUILD_ID** — Line 22 of the pre-existing `guild_setup.py` hardcodes `GUILD_ID = 1510876414671323206`. This is *not* new P2-007 code; the new `permissions.py` correctly discovers guild at runtime via name matching. No action needed.

2. **Manual YAML parser is fragile** — `read_channel_ids()` uses a string-line parser rather than PyYAML. While functional for the narrow `channel-ids.yaml` format, it would break on quoted colons or multi-line values. Acceptable for this scope since the YAML file has a fixed, simple structure. Not a finding requiring change.

3. **`text_value()` silently returns `""` for missing fields** — This could mask data quality issues. However, critical fields (owner_id, bot_id, guild_id) have explicit emptiness checks that raise `RuntimeError`. Non-critical fallbacks defaulting to `""` or `0` are acceptable for Discord API consumption. Not a finding requiring change.

4. **Batch-plan warns about StepPrompts unsafe snippets** — §17.5 notes "Later P2 StepPrompts still contain unsafe token extraction snippets." P2-007 did not modify StepPrompts. This is correctly deferred to batch sync after P2-009 auditor PASS. No action needed.

---

## 6. Verdict

**PASS** — STEP-P2-007 Discord channel permissions implementation is complete and correct.

All 12 acceptance criteria pass. No unsafe shortcuts, no token exposure, no hardcoded IDs in new code, no premature tracker sync. Evidence has all 12 required sections. Permission overwrites match the canonical matrix for all 13 channels. Administrator caveat is properly documented for P2-009.

---

## 7. Recommendation

Proceed to P2-008 (channel topics) after this auditor PASS. Do not sync trackers (PROGRESS.md, CHECKLIST.md, StepPrompts.md) until P2-009 auditor also PASSes per batch-plan §6.

---

*Auditor gate satisfied. File-based, independent, zero mutations.*

| Field | Value |
|---|---|
| Auditor instance | Guinevere per-step gate (independent) |
| Audit method | File-based static + runtime output verification |
| Files checked | 7 files (4 source/script, 1 evidence, 1 plan, 1 YAML) |
| Criteria checked | 12 acceptance criteria + 7 cross-cut items |
| Verdict | PASS |
| Next step | P2-008 topic verification |