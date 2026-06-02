# STEP-P2-009 Verification — Bot Invite and Permission-Scope / Administrator Review

**Step:** P2-009 — Bot permission-scope and least-privilege assessment  
**Date:** 2026-06-01  
**Verdict:** PASS — Administrator confirmed; documented as not justified long-term; controlled transition path defined  
**Guild:** `Guinevere's Domain`  
**Guild ID:** `1510876414671323206`  
**Bot App ID:** `1510873134981582858`  

---

## 1. What Was Done

Executed the permission-scope review verifier `tmp/verify-p2-009-bot-permissions-rest.py` on the VPS via the SOPS secure wrapper (`scripts/run-discord-verify.sh`). The verifier:

1. **Discovered guild context** at runtime via Discord REST API (`/users/@me`, `/users/@me/guilds`, `/guilds/{id}`, `/guilds/{id}/members/{bot_id}`).
2. **Fetched all guild roles** via `/guilds/{id}/roles`.
3. **Accumulated bot permission bitfield** by scanning all roles assigned to the bot and OR-ing their permission values.
4. **Checked Administrator status** by testing bit 3 (`1 << 3 = 8`).
5. **Computed least-privilege invite URL** with permissions set to `2147599472` (`0x8000F870`).
6. **Generated security decision** based on whether Administrator is present.

**Sanitized verifier output:**

| Field | Value |
|---|---|
| `guild_id` | `1510876414671323206` |
| `guild_name` | `Guinevere's Domain` |
| `bot_id` | `1510873134981582858` |
| `administrator` | `true` |
| `permissions_bitfield` | `8` (ADMINISTRATOR bit) |
| `least_privilege_permissions` | `2147599472` (`0x8000F870`) |
| `least_privilege_invite_url` | `https://discord.com/oauth2/authorize?client_id=1510873134981582858&permissions=2147599472&scope=bot%20applications.commands` |
| `decision` | `Administrator is not justified long-term; managed role/OAuth reauthorization required for safe reduction` |
| `result` | `PASS` |

---

## 2. Files Changed

| Path | Change | Notes |
|---|---|---|
| `tmp/verify-p2-009-bot-permissions-rest.py` | New verifier script | Created by P2-009 implementation |
| `src/discord/permissions.py` | Added `AdminReview`, `review_admin_scope`, `format_admin_review`, `fetch_roles`, `LEAST_PRIVILEGE_PERMISSIONS`, `LEAST_PRIVILEGE_PERMISSIONS_HEX` | Created by P2-009 implementation |
| `scripts/run-discord-verify.sh` | Allowlisted `tmp/verify-p2-009-bot-permissions-rest.py` | Enables secure wrapper execution |
| `docs/setup-evidence/P2/STEP-P2-009/verification.md` | This evidence file | Current document |

---

## 3. Validation Results

### Verifier Execution (VPS via SOPS wrapper)

```
guild_id=1510876414671323206
guild_name=Guinevere's Domain
bot_id=1510873134981582858
administrator=true
permissions_bitfield=8
least_privilege_permissions=2147599472
least_privilege_permissions_hex=0x8000F870
least_privilege_invite_url=https://discord.com/oauth2/authorize?client_id=1510873134981582858&permissions=2147599472&scope=bot%20applications.commands
decision=Administrator is not justified long-term; managed role/OAuth reauthorization required for safe reduction
result=PASS
```

**Status:** `result=PASS` — verifier completed without error.

### Local LSP Diagnostics

- `src/discord/permissions.py` — Clean (no errors, no warnings)
- `tmp/verify-p2-009-bot-permissions-rest.py` — Clean (no errors, no warnings)
- `docs/setup-evidence/P2/STEP-P2-009/verification.md` — N/A (markdown)

### Token-Shaped Regex Scan

Scanned all changed files for token-shaped patterns (`[A-Za-z0-9_-]{23,26}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}`):

- `tmp/verify-p2-009-bot-permissions-rest.py` — No token leaks found
- `src/discord/permissions.py` — No token leaks found
- `docs/setup-evidence/P2/STEP-P2-009/verification.md` — No token leaks found

### Pre-existing vs Introduced Issues

| Category | Count | Details |
|---|---|---|
| Pre-existing issues | 0 | Module was newly created for P2-009 |
| Introduced issues | 0 | All diagnostics clean |

---

## 4. Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| P2-009 verifier script | `tmp/verify-p2-009-bot-permissions-rest.py` | Executed PASS |
| Permission review module | `src/discord/permissions.py` | Contains `review_admin_scope`, `AdminReview`, `LEAST_PRIVILEGE_PERMISSIONS` |
| Channel IDs (P2-006) | `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Referenced by verifier |
| This evidence file | `docs/setup-evidence/P2/STEP-P2-009/verification.md` | Current document |

---

## 5. Doc-Sync Impact

| Document | Impact | Rationale |
|---|---|---|
| `docs/README.md` | None | No structural doc changes; verification-only step |
| ADR-Index | None | No architecture decision changed |
| P2 scope docs | None | Evidence file is self-contained |

---

## 6. Boundary Compliance

| Boundary | Status | Evidence |
|---|---|---|
| **No persona drift** | ✅ PASS | Persona docs not touched |
| **No consent violation** | ✅ PASS | Read-only verification; no surveillance, no data mutation |
| **No surveillance overreach** | ✅ PASS | Guild ID, bot ID are public identifiers; no member data collected beyond bot identity |
| **No Y6 yandere level** | ✅ PASS | Y4 baseline preserved; no persona changes; Y6 remains prohibited |
| **No HARD STOP bypass** | ✅ PASS | No emergency protocols engaged |
| **No distress protocol suppression** | ✅ PASS | N/A — routine verification |
| **No token exposure** | ✅ PASS | Token handled via SOPS wrapper `DISCORD_SECRETS_PATH` env var; never printed |
| **No destructive operation** | ✅ PASS | Read-only REST calls; no DELETE/PUT/PATCH executed |
| **No bot re-invite/kick** | ✅ PASS | Bot state untouched |

---

## 7. Rollback / Re-run Safety

| Property | Status |
|---|---|
| **Idempotent** | ✅ Yes — verifier is read-only; re-running produces same result |
| **Rollback path** | N/A — no state mutated; no rollback required |
| **Re-run safety** | ✅ Safe to re-run any number of times |
| **Dependency on prior state** | Reads channel-ids.yaml from P2-006; requires guild + bot to exist |

---

## 8. Design Decisions / Caveats

### Decision: Administrator is NOT justified long-term

**Current state:** Bot role carries `permissions=8` which is the `ADMINISTRATOR` bit (`1 << 3`). This grants full guild access.

**Assessment:** Administrator is a convenience during initial P2 setup (channel creation, permission overwrites, role management). It is not justified for the bot's ongoing operational role, which only requires:

- `VIEW_CHANNEL` (1024)
- `SEND_MESSAGES` (2048)
- `EMBED_LINKS` (16384)
- `ATTACH_FILES` (32768)
- `READ_MESSAGE_HISTORY` (65536)
- `ADD_REACTIONS` (64)

Total least-privilege: `2147599472` (`0x8000F870`), which includes `applications.commands` scope but excludes Administrator.

### Controlled Transition Path

Administrator **must not** be removed by directly editing the bot's managed role — the Discord OAuth2 system created this role, and removal requires:

1. **Generate a new invite URL** with the least-privilege permission integer (`2147599472`).
2. **Re-authorize the bot** via OAuth2 flow — the guild owner (Faiz) clicks the invite link, Discord replaces the managed role's permission set.
3. **Verify** that the bot role now carries only the reduced permissions.
4. **Validate** that all audit-log, evidence-log, and operational channels remain accessible.

This transition is deferred from P2-009. P2-009's mandate is to **document and verify** the current state, not to mutate it.

### Deferred Items

| Item | Reason |
|---|---|
| Administrator reduction | Must be performed as controlled OAuth2 reauthorization, not destructive role edit |
| Post-reduction re-verification | Requires explicit step after reauthorization |
| Channel permission overwrite validation after reduction | Should be part of reduction follow-up |

---

## 9. Auditor Gate

**Status:** Deferred to parent per task mandate. The task explicitly states: "Do not call auditor; parent will run security auditor after verifying."

This evidence file is prepared for independent security auditor review. All required data (guild_id, bot_id, permissions bitfield, least-privilege integer, invite URL, decision) is documented above.

---

## 10. Security Scan

### Token Exposure Scan

| Pattern | Scope | Result |
|---|---|---|
| Discord bot token regex (`[A-Za-z0-9_-]{23,26}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}`) | All changed files | ✅ Clean |

### Secret Hygiene

| Practice | Status |
|---|---|
| Token passed via environment variable (`DISCORD_SECRETS_PATH`) | ✅ Used |
| Token decrypted by SOPS into temp file, shredded on exit | ✅ Via `run-discord-verify.sh` cleanup |
| Token never printed, logged, or committed | ✅ Verified |
| No credentials in evidence artifacts | ✅ Redacted |

### Permission Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Administrator grants unrestricted API access | High | Documented; controlled transition path defined; not destructively removed |
| Least-privilege invite URL available | Low | Ready to use when Faiz performs OAuth2 reauthorization |
| Bot identity public | None | Bot ID `1510873134981582858` is a public Discord identifier |

---

## 11. Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| Verifier executes without error on VPS | ✅ PASS | `result=PASS` in output |
| Sanitized output includes guild_id, bot_id, administrator status | ✅ PASS | All fields present in verifier output |
| Current permissions bitfield documented | ✅ PASS | `permissions_bitfield=8` (ADMINISTRATOR) |
| Least-privilege integer and hex documented | ✅ PASS | `2147599472` / `0x8000F870` |
| Reduced invite URL computed and documented | ✅ PASS | See section 1 |
| Decision: Administrator justified or not | ✅ PASS | **Not justified long-term** — see section 8 |
| Controlled transition path defined | ✅ PASS | OAuth2 reauthorization with least-privilege permissions |
| Token not exposed in output | ✅ PASS | Token handled via SOPS env var; no token in output |
| Bot accessible and identifiable | ✅ PASS | Bot returned valid response; ID `1510873134981582858` |
| Local validation clean | ✅ PASS | LSP diagnostics clean; token regex scan clean |

---

## 12. Footer

| Field | Value |
|---|---|
| **Source task** | STEP-P2-009 — Bot invite and permission-scope / Administrator review |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (Sisyphus-Junior) |
| **Validation method** | VPS SOPS wrapper execution + local LSP diagnostics + token regex scan |
| **Auditor gate** | Deferred — parent to run security auditor after verifying this evidence |
| **Evidence path** | `docs/setup-evidence/P2/STEP-P2-009/verification.md` |
| **Sanitized output source** | Remote VPS run via `ssh guinevere-vps "bash scripts/run-discord-verify.sh tmp/verify-p2-009-bot-permissions-rest.py"` |