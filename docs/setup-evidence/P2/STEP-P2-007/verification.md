# STEP-P2-007 Verification — Discord Channel Permissions

**Step:** P2-007 — Channel permissions  
**Date:** 2026-06-01  
**Verdict:** IMPLEMENTED — Auditor pending  
**Guild:** `Guinevere's Domain`  

---

## 1. What Was Done

Configured canonical Discord channel permission overwrites for the 13 Guinevere channels created in P2-006.

The implementation:

- Reads channel IDs from `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`.
- Discovers guild, bot, owner/Faiz, and `@everyone` at runtime.
- Denies canonical channel visibility to `@everyone`.
- Grants Faiz/Samm read/write access on normal channels.
- Grants Faiz/Samm read-only access on evidence/archive channels.
- Grants the Guinevere bot send/read/embed/attach access on canonical channels.
- Applies append-only approximation for `guinevere-evidence`, `evidence-log`, and `audit-log`.

---

## 2. Files Changed

| Path | Change |
|---|---|
| `src/discord/permissions.py` | New helper module for permission, topic, and admin review operations. |
| `tmp/setup-p2-007-permissions.py` | New P2-007 apply script. |
| `tmp/verify-p2-007-permissions-rest.py` | New P2-007 verifier script. |
| `scripts/run-discord-verify.sh` | Allowlisted P2-007/P2-008/P2-009 scripts for SOPS temp execution. |
| `docs/setup-evidence/P2/STEP-P2-007/verification.md` | This evidence file. |

Runtime Discord mutations:

- Permission overwrites were applied to the 13 canonical text channels only.
- Existing default Discord categories/channels were not deleted or modified intentionally.

---

## 3. Validation Results

### Static validation

| Check | Result |
|---|---|
| `lsp_diagnostics src/discord/permissions.py` | PASS — no diagnostics |
| `lsp_diagnostics tmp/setup-p2-007-permissions.py` | PASS — no diagnostics |
| `lsp_diagnostics tmp/verify-p2-007-permissions-rest.py` | PASS — no diagnostics |
| Python compile locally | PASS |
| Python compile on VPS | PASS |
| Discord token-shaped regex scan | PASS — no token-shaped matches |

### Runtime apply output

```text
channel,everyone_private,owner_read,owner_send_expected,owner_send_actual,bot_send,append_only,ok
audit-log,true,true,false,false,true,true,true
cost-tracker,true,true,true,true,true,false,true
evidence-log,true,true,false,false,true,true,true
guinevere-chat,true,true,true,true,true,false,true
guinevere-dev,true,true,true,true,true,false,true
guinevere-docs,true,true,true,true,true,false,true
guinevere-evidence,true,true,false,false,true,true,true
guinevere-planning,true,true,true,true,true,false,true
guinevere-status,true,true,true,true,true,false,true
project-alpha-dev,true,true,true,true,true,false,true
project-alpha-docs,true,true,true,true,true,false,true
project-beta-dev,true,true,true,true,true,false,true
system-health,true,true,true,true,true,false,true
result=PASS
```

### Runtime verifier output

```text
channel,everyone_private,owner_read,owner_send_expected,owner_send_actual,bot_send,append_only,ok
audit-log,true,true,false,false,true,true,true
cost-tracker,true,true,true,true,true,false,true
evidence-log,true,true,false,false,true,true,true
guinevere-chat,true,true,true,true,true,false,true
guinevere-dev,true,true,true,true,true,false,true
guinevere-docs,true,true,true,true,true,false,true
guinevere-evidence,true,true,false,false,true,true,true
guinevere-planning,true,true,true,true,true,false,true
guinevere-status,true,true,true,true,true,false,true
project-alpha-dev,true,true,true,true,true,false,true
project-alpha-docs,true,true,true,true,true,false,true
project-beta-dev,true,true,true,true,true,false,true
system-health,true,true,true,true,true,false,true
result=PASS
```

---

## 4. Evidence Artifacts

| Artifact | Purpose |
|---|---|
| `docs/setup-evidence/P2/batch-plan-007-009.md` | Planner gate. |
| `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Source of truth for channel IDs. |
| `src/discord/permissions.py` | Permission implementation. |
| `tmp/setup-p2-007-permissions.py` | Apply script. |
| `tmp/verify-p2-007-permissions-rest.py` | Verification script. |
| `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md` | Auditor report target. |

---

## 5. Doc-Sync Impact

Pending until P2-007, P2-008, and P2-009 all pass auditor gates:

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`

This avoids claiming partial phase completion before the batch finishes.

---

## 6. Boundary Compliance

| Boundary | Result |
|---|---|
| Discord token exposure | PASS — no token printed or persisted. |
| SOPS handling | PASS — existing temp decrypt wrapper used. |
| Aizanta isolation | PASS — Discord-only mutation; no Aizanta writes. |
| Consent/surveillance scope | PASS — channel privacy tightened, no overreach. |
| Persona safety | PASS — no Y6/HARD STOP/persona prompt changes. |
| Destructive operations | PASS — no channel/category deletion. |

---

## 7. Rollback / Re-run Safety

The operation is idempotent: re-running the setup script converges the 13 canonical channel overwrites to the same state.

Rollback options:

1. Remove canonical overwrites from the 13 channels for `@everyone`, owner/Faiz, and bot.
2. Restore previous overwrites from a future snapshot if required.
3. Do not delete Discord channels or categories for rollback.

---

## 8. Design Decisions / Caveats

- `channel-ids.yaml` is the source of truth for channel IDs; new code does not hardcode channel IDs.
- Guild, owner/Faiz, bot, and `@everyone` identifiers are discovered at runtime.
- True Discord bot write-only is not possible for normal send APIs because hidden channels cannot be posted to normally.
- Evidence/archive channels use an append-only approximation: Faiz can read but not post; bot can post and is denied destructive management permissions.
- The bot currently has Administrator, which bypasses its own overwrites. P2-009 must review and reduce or document the controlled reauthorization path.

---

## 9. Auditor Gate

**Status:** Pending  
**Expected report:** `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md`

Auditor must verify:

- All 13 canonical channels passed permission verification.
- `@everyone` visibility denied.
- Faiz/Samm access matches normal vs append-only matrix.
- Bot access matches intended send/read capabilities.
- Administrator bypass caveat is documented and deferred to P2-009.
- No Discord token appears in evidence or source.

---

## 10. Security Scan

Token-shaped regex scan over changed `src/discord` and `tmp` files returned no Discord token values.

Safe key-name references such as `discord_bot_token` may appear in parser/helper code, but no secret value is stored in repo artifacts.

---

## 11. Acceptance Criteria Mapping

| Criterion | Result |
|---|---|
| Channel permissions configured | PASS |
| Bot has correct write access | PASS |
| Samm/Faiz read access configured | PASS |
| Evidence/archive read-only for Faiz | PASS |
| Evidence/archive bot append-only approximation configured | PASS |
| Evidence clean and no token exposure | PASS |
| Auditor PASS | Pending |

---

## 12. Footer

- Source task: STEP-P2-007 full autonomous implementation.
- Implementer: Hephaestus / Guinevere.
- Validation method: static diagnostics, Python compile, SOPS-wrapped Discord runtime apply and verify.
- Next step: P2-007 auditor gate.
