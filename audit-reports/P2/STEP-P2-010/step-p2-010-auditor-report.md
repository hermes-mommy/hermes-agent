# Auditor Report — STEP-P2-010: Discord Slash Command Registration

**Date:** 2026-06-01
**Auditor:** Independent gate (Sisyphus-Junior)
**Scope:** P2-010 guild-scoped 33-command registry, sync/verify scripts, token flow, evidence, docs
**Verdict:** **PASS** ✅

---

## 1. Verdict Summary

| Dimension | Result |
|---|---|
| Technical Correctness | ✅ PASS |
| Security/Token Handling | ✅ PASS |
| Compliance/Spec Traceability | ✅ PASS |
| Evidence Truthfulness | ✅ PASS |
| VPS/Runtime Impact | ✅ PASS |
| Docs/Traceability | ✅ PASS |
| Boundary Compliance | ✅ PASS |
| **Overall Verdict** | **✅ PASS** |

No blocking issues found. Three non-blocking findings documented below.

---

## 2. Technical Correctness

### 2.1 33 Canonical Commands — Verified

`command_count()` returns **33**. Category breakdown matches DiscordUXSpec §11:

| Category | Count | Commands | Status |
|---|---|---|---|
| core | 4 | status, mood, help, safeword | ✅ |
| loop | 7 | loop-start, loop-stop, loop-pause, loop-resume, loops, evidence, loop-priority | ✅ |
| memory | 4 | memory-search, memory-add, memory-forget, memory-export | ✅ |
| surveillance | 3 | surveillance-status, surveillance-pause, surveillance-resume | ✅ |
| finance | 3 | cost, budget, cost-alert | ✅ |
| system | 8 | approve, deny, approve-all, focus, casual, consent, punishment, reward | ✅ |
| admin | 4 | restart-service, backup-now, health-check, clear-cache | ✅ |
| **Total** | **33** | — | **✅** |

No extra commands found. No missing commands. `require_canonical_registry()` validates count=33, no duplicates, name length ≤ 32, description length ≤ 100. Verified via Python import + runtime execution.

### 2.2 Guild-Scoped Endpoints — Verified

Both sync and verify scripts use guild-scoped REST endpoints exclusively:

- **Sync script** (`tmp/sync-p2-010-commands.py`): `SYNC_PATH = f"/applications/{APPLICATION_ID}/guilds/{GUILD_ID}/commands"` (PUT bulk overwrite)
- **Verify script** (`tmp/verify-p2-010-commands-rest.py`): `COMMANDS_PATH = f"/applications/{APPLICATION_ID}/guilds/{GUILD_ID}/commands"` (GET read)

No global endpoint (`/applications/{id}/commands`) is used. ✅

### 2.3 Type Safety — No Violations

- `# type: ignore`: **0** occurrences in all P2-010 files
- `as any`: **0** occurrences (N/A for Python)
- `@ts-ignore`: **0** occurrences (N/A for Python)
- Empty `except:` blocks: **0** occurrences
- All error handling uses explicit `raise RuntimeError(...)` with context messages

### 2.4 `is_faiz_interaction()` — Fails Closed

```python
def is_faiz_interaction(interaction: object) -> bool:
    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    owner_id = getattr(guild, "owner_id", None)
    user_id = getattr(user, "id", None)
    return isinstance(owner_id, int) and isinstance(user_id, int) and owner_id == user_id
```

- Uses runtime `guild.owner_id` — no hardcoded user ID ✅
- Returns `False` (fail-closed) if any attribute is missing (`isinstance` guards) ✅
- Compatible with runtime Discord interaction objects ✅

### 2.5 Registry Validation — Comprehensive

`require_canonical_registry()` validates:
- **Count**: exactly 33 ✅
- **Duplicates**: no duplicate names ✅
- **Name length**: all ≤ 32 chars ✅
- **Description**: all non-empty and ≤ 100 chars ✅

---

## 3. Security/Token Handling

### 3.1 Token Source — Clean

| File | Token Source | Status |
|---|---|---|
| `src/discord/commands.py` | No token access (registry only) | ✅ |
| `tmp/sync-p2-010-commands.py` | `token_from_environment()` → `get_token()` | ✅ |
| `tmp/verify-p2-010-commands-rest.py` | `token_from_environment()` → `get_token()` | ✅ |
| `src/discord/permissions.py` | `token_from_environment()` → `get_token()` | ✅ (shared helper) |

### 3.2 No Unsafe Token Patterns

Pattern searched across all P2-010 Python files:

| Pattern | Found? |
|---|---|
| `os.environ.get("DISCORD_BOT_TOKEN")` | ❌ No |
| `os.environ\["DISCORD_BOT_TOKEN"\]` | ❌ No |
| `import os` + token access | ❌ No |
| Hardcoded token string | ❌ No |
| Inline `sops -d \| grep` token leak | ❌ No |

### 3.3 Token Lifecycle

Both sync and verify scripts clear the token in `finally`:
```python
try:
    # ... work with token ...
finally:
    token = ""
```
✅ Token cleared after use.

### 3.4 SOPS Wrapper Pattern

`scripts/run-discord-verify.sh`:
1. Decrypts `secrets/discord-secrets.yaml` via SOPS+age to temp file
2. Sets `DISCORD_SECRETS_PATH` env var pointing to temp file
3. Python `get_token()` reads from the temp file path
4. Trap+cleanup: `shred -u "$TEMP_SECRETS"` destroys temp file on exit

No token ever appears in argv, env (beyond the path variable), logs, or evidence. ✅

### 3.5 Allowlist — No Broad Wildcard

The `case` allowlist in `scripts/run-discord-verify.sh` uses exact file paths only:
```
tmp/sync-p2-010-commands.py|tmp/verify-p2-010-commands-rest.py
```
No `*` or `?` wildcard patterns. ✅

---

## 4. Compliance/Spec Traceability

### 4.1 Command Names vs DiscordUXSpec §11

All 33 command names match the canonical DiscordUXSpec §11 list as documented in the batch plan. The StepPrompts legacy 15-command mismatched list is explicitly rejected and excluded.

The 15 rejected StepPrompts-only commands (`/score`, `/task`, `/pause`, `/resume`, `/cancel`, `/journal`, `/persona`, `/ritual`, `/distress`, `/emergency`, `/surveillance-report`, `/finance`, `/config`, `/memory-stats`, `/punish`) are **not present** in the implementation. ✅

### 4.2 StepPrompts P2-010 Section — Clean

| Check | Result |
|---|---|
| Unsafe heredoc with `os.environ.get("DISCORD_BOT_TOKEN")` | ❌ Replaced with wrapper commands ✅ |
| Inline `DISCORD_BOT_TOKEN=$(sops -d ... grep ... awk ...)` | ❌ Replaced ✅ |
| Commands reference actual files | ✅ Documents `src/discord/commands.py` |
| Wrapper invocations | ✅ Both sync and verify use `scripts/run-discord-verify.sh` |

### 4.3 ADR Compliance

| ADR | Requirement | Compliance |
|---|---|---|
| ADR-015 | Token behind SOPS + `DISCORD_SECRETS_PATH`; no plaintext | ✅ All scripts via `get_token()` |
| ADR-018 | No broad token fallback; fail-closed enforcement | ✅ `is_faiz_interaction()` fails closed |
| ADR-022 | Discord slash commands as primary interface | ✅ 33-command surface from DiscordUXSpec |

---

## 5. Evidence Truthfulness

### 5.1 File Existence

| Evidence Artifact | Status |
|---|---|
| `docs/setup-evidence/P2/STEP-P2-010/verification.md` | ✅ Exists (12 sections) |
| `docs/setup-evidence/P2/STEP-P2-010/p2-010-implementation-summary.md` | ✅ Exists (12 sections) |
| `docs/setup-evidence/P2/batch-plan-010-012.md` | ✅ Exists (20 sections) |

### 5.2 Parent Claims — Internal Consistency

| Claim | Evidence Match | Status |
|---|---|---|
| Runtime sync: `Synced 33 commands to guild 1510876414671323206` | ✓ MATCH — verification.md §3.3 | ✅ |
| Runtime verify: `commands_count=33`, `all_names_match=true` | ✓ MATCH — verification.md §3.4 | ✅ |
| Runtime verify: `missing=none`, `unknown=none` | ✓ MATCH — verification.md §3.4 | ✅ |
| LSP clean all severity (4 files) | ✓ MATCH — verification.md §3.1 | ✅ |
| Token scan clean for `src/discord/` and `tmp/` | ✓ CONFIRMED — independent grep | ✅ |
| Aizanta health: 5 containers healthy unchanged | ✓ INTERNALLY CONSISTENT — verification.md §5 | ✅ (cannot VPS-verify independently) |
| P2-011/P2-012 tracker updates NOT performed | ✓ CONFIRMED — no PROGRESS.md/CHECKLIST.md changes | ✅ |

### 5.3 Evidence Schema Compliance

Both evidence files follow AGENTS.md §11 minimum schema:
- What Was Done ✅
- Files Changed ✅
- Validation Results (with pre-existing vs introduced split) ✅
- Evidence Artifacts ✅
- Doc-Sync Impact ✅
- Boundary Compliance ✅
- Rollback / Re-run Safety ✅
- Design Decisions / Caveats ✅
- Auditor Gate (pending) ✅
- Footer ✅

---

## 6. VPS/Runtime Impact

### 6.1 Impact Assessment

| Component | P2-010 Impact |
|---|---|
| Aizanta services | None (REST API only, no gateway/DB change) |
| PostgreSQL | None |
| Redis | None |
| Docker | None |
| Systemd services | None |
| Discord gateway | None (REST-only sync, no gateway connection) |

### 6.2 Idempotency

- Re-running sync: ✅ Idempotent — Discord bulk PUT replaces existing guild command set
- Re-running verify: ✅ Read-only GET, no side effects
- Rollback: ✅ Sync empty payload `[]` via guild-scoped PUT endpoint

---

## 7. Docs/Traceability

### 7.1 StepPrompts P2-010 Section — Clean

The P2-010 section (lines 5413-5443) is properly cleaned:
- ✅ No inline `os.environ.get("DISCORD_BOT_TOKEN")` 
- ✅ No heredoc with inline command definitions
- ✅ Uses wrapper invocations: `scripts/run-discord-verify.sh tmp/sync-p2-010-commands.py`
- ✅ References actual source files instead of inline code

### 7.2 Allowlist Updated

`scripts/run-discord-verify.sh` includes both P2-010 entries with exact paths:
- `tmp/sync-p2-010-commands.py` ✅
- `tmp/verify-p2-010-commands-rest.py` ✅

### 7.3 [NON-BLOCKING] Stale Token Patterns Outside P2-010

| Location | Issue | Scope |
|---|---|---|
| `StepPrompts.md` line 5732 | `token = os.environ.get("DISCORD_BOT_TOKEN", "")` in P2-016/P2-017 section | Outside P2-010 — acknowledged deferred cleanup |
| `StepPrompts.md` lines 5758-5762 | Inline `sops -d \| grep discord_bot_token` leak in P2-016/P2-017 section | Outside P2-010 — acknowledged deferred cleanup |
| `StepPrompts.md` lines 5447-5529 | Old heredoc patterns for P2-011 through P2-014 | Outside P2-010 — explicitly noted as out-of-scope |

These do not affect the P2-010 verdict. They are documented for the deferred P2-017 cleanup batch.

### 7.4 [NON-BLOCKING] Batch Plan Header Typo

The batch plan's §4.2 header says "⚙️ System (7)" but correctly lists 8 commands. This is a minor documentation error in the planner (the system category has 8 commands: approve, deny, approve-all, focus, casual, consent, punishment, reward). The implementation correctly has 8 system commands for a total of 33.

---

## 8. Boundary Compliance

| Boundary | Status | Notes |
|---|---|---|
| Persona drift | ✅ No change | Command-surface only; no persona behavior |
| Consent violation | ✅ No change | `/consent` registered only; runtime in P5 |
| Surveillance overreach | ✅ No change | `/surveillance-*` registered only; runtime in P7 |
| Y6 yandere level | ✅ Not introduced | `/safeword` registered; enforcement in P2-015 |
| HARD STOP bypass | ✅ Not bypassed | `/safeword` present in registry |
| Distress protocol suppression | ✅ No change | No distress protocol behavior introduced |
| Secret exposure | ✅ Clean | Token via SOPS wrapper only; no plaintext in evidence or code |

---

## 9. Findings Register

### 9.1 Blocking Findings (0)

None.

### 9.2 Non-Blocking Findings (3)

| # | Severity | Finding | Location | Remediation |
|---|---|---|---|---|
| F1 | 🟡 Low | Batch plan §4.2 header mismatch: "⚙️ System (7)" should be (8) | `docs/setup-evidence/P2/batch-plan-010-012.md` | Fix header to read "⚙️ System (8)" on next doc sync pass |
| F2 | 🟢 Info | Stale token patterns in P2-016/P2-017 section of StepPrompts.md | `StepPrompts.md` lines 5732, 5758-5762 | Deferred to P2-017 cleanup batch (already acknowledged) |
| F3 | 🟢 Info | Old heredoc patterns for P2-011 through P2-014 in StepPrompts.md | `StepPrompts.md` lines 5447-5529 | Deferred to batch sync after all auditors PASS (already acknowledged) |

---

## 10. Final Gate Verdict

| Check | Verdict |
|---|---|
| Technical — 33 commands, guild-scoped, no type bypasses | ✅ PASS |
| Security — Token via SOPS wrapper only, no env reads, cleared in finally | ✅ PASS |
| Compliance — Names match DiscordUXSpec, ADR-015/018/022 satisfied | ✅ PASS |
| Evidence — Files exist, claims consistent, schema-compliant | ✅ PASS |
| VPS — Idempotent, no destructive ops, Aizanta unaffected | ✅ PASS |
| Docs — StepPrompts P2-010 section cleaned, allowlist exact paths | ✅ PASS |
| Boundary — No drift, no consent violation, no Y6, HARD STOP present | ✅ PASS |

**FINAL VERDICT: ✅ PASS**

---

## 11. Footer

| Field | Value |
|---|---|
| **Source task** | STEP-P2-010 Discord slash command registration — Independent Auditor Gate |
| **Date** | 2026-06-01 |
| **Auditor** | Sisyphus-Junior (independent gate) |
| **Audit method** | Static code review, Python import/exec verification, grep token scan, evidence cross-reference, spec traceability analysis |
| **Files audited** | `src/discord/commands.py`, `src/discord/permissions.py`, `tmp/sync-p2-010-commands.py`, `tmp/verify-p2-010-commands-rest.py`, `scripts/run-discord-verify.sh`, `stepprompts/StepPrompts.md` (§5413-5443), `docs/setup-evidence/P2/STEP-P2-010/*.md`, `docs/setup-evidence/P2/batch-plan-010-012.md` |
| **Verdict** | **PASS** — All dimensions clear. 3 non-blocking informational findings documented. No blocking issues. |