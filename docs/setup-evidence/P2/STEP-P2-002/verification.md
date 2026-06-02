# STEP-P2-002 Verification — Discord Bot Token Generation + SOPS Storage

| Field | Value |
|---|---|
| Step | P2-002 |
| Title | Discord bot token secure storage verification |
| Date | 2026-06-01 |
| Status | Implemented — evidence formalized, auditor pending |
| Evidence path | `docs/setup-evidence/P2/STEP-P2-002/verification.md` |

---

## 1. What Was Done

P2-002 was formalized from the already-completed secure Discord token capture flow. The bot token was generated/reset in Discord Developer Portal before this step and captured only through a hidden VPS prompt, then encrypted with SOPS+age.

This step did **not** regenerate, print, partially print, or copy the Discord bot token. It verified that the encrypted secret exists, decrypts with the correct age identity, contains the expected metadata keys, and authenticates to Discord API as the expected bot ID.

Runtime secret path:

- `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`

Age identity path:

- `/home/guinevere/secrets/age-key.txt`

---

## 2. Files Changed

Created:

- `docs/setup-evidence/P2/STEP-P2-002/verification.md`

No token, source code, encrypted secret, or runtime service was modified during this step.

---

## 3. Validation Results

Live VPS verifier command executed:

```bash
ssh guinevere-vps "bash /tmp/verify-discord-secret.sh"
```

Sanitized verifier output:

```text
-rw------- 1 guinevere guinevere 1792 Jun  1 13:06 secrets/discord-secrets.yaml
token_key=present
app_id=ok
public_key=present
decrypt_bytes=257
discord_api=ok
bot_id=1510873134981582858
bot_username=Guinevere
matches_application_id=yes
```

| Check | Result |
|---|---|
| Encrypted secret exists | PASS — `secrets/discord-secrets.yaml` exists on VPS |
| File permissions | PASS — `-rw-------` / chmod 600 |
| SOPS decrypt with age key | PASS — decrypt succeeded without printing token |
| Required token key exists | PASS — `token_key=present` |
| Application ID metadata | PASS — `app_id=ok` |
| Public key metadata | PASS — `public_key=present` |
| Discord API auth | PASS — `discord_api=ok` |
| Bot ID matches expected app ID | PASS — `matches_application_id=yes` |
| Bot username | PASS — `Guinevere` |

---

## 4. Evidence Artifacts

| Artifact | Path / Source | Purpose |
|---|---|---|
| Secure capture helper | VPS: `/tmp/capture-discord-token.sh` | Hidden prompt + SOPS encryption workflow |
| Safe verification helper | Local source: `tmp/verify-discord-secret.sh`; executed on VPS | Decrypt/API validation without printing token |
| SOPS rules | `.sops.yaml` | Confirms `secrets/*.yaml` encrypts with age recipient |
| P2 precondition evidence | `docs/setup-evidence/P1/p2-preconditions-resolved.md` | Historical token capture and API verification record |
| Token security research | `research-reports/P2/discord-intents-token-security.md` | Best-practice reference for token storage and redaction |
| VPS readiness research | `research-reports/P2/vps-discord-readiness-pre-p2.md` | Independent confirmation of secret file, age key, API identity, and canonical ports |
| Planner gate | `docs/setup-evidence/P2/batch-plan-001-003.md` | Approved P2-002 formalization plan |
| This evidence | `docs/setup-evidence/P2/STEP-P2-002/verification.md` | Formal P2-002 verification artifact |

---

## 5. Doc-Sync Impact

Required after P2-001, P2-002, and P2-003 all pass auditor gates:

- `PROGRESS.md`: P2 `0/21` → `3/21`; total `50/257` → `53/257 (20.6%)`.
- `CHECKLIST.md`: mark P2-001, P2-002, and P2-003 complete.

This step intentionally defers tracker mutation until all three requested steps pass their auditor gates.

---

## 6. Boundary Compliance

| Boundary | Result |
|---|---|
| Discord token secrecy | PASS — token value, prefix, suffix, and partial token are never printed |
| Temporary plaintext handling | PASS — verifier writes decrypt output only to `/tmp` and shreds it via trap |
| SOPS/age encryption | PASS — `.sops.yaml` includes `secrets/.*\.yaml$` rule with age recipient |
| No secret committed | PASS — only encrypted VPS file is used; evidence contains sanitized status only |
| Aizanta isolation | PASS — no Aizanta service, container, secret, network, or port touched |
| Consent / surveillance boundary | PASS — no surveillance behavior changed |
| Persona safety | PASS — no prompt or persona boundary changed |
| Destructive operations | PASS — none performed against production secrets; verification is read-only |

---

## 7. Rollback / Re-run Safety

P2-002 formalization is read-only except for this evidence file.

Re-run verification safely:

```bash
ssh guinevere-vps "bash /tmp/verify-discord-secret.sh"
```

Rollback for evidence only:

1. Delete `docs/setup-evidence/P2/STEP-P2-002/verification.md`.
2. Re-run the verifier.
3. Regenerate sanitized evidence without printing token material.

If token compromise is suspected, reset the bot token in Discord Developer Portal and re-run `/tmp/capture-discord-token.sh`; all tokens pasted into chat or screenshots must be considered compromised.

---

## 8. Design Decisions / Caveats

1. **Unsafe StepPrompts P2-002 shell-token pattern was not used.** The original prompt pattern assigns token values to shell variables and prints partial token prefixes; this implementation uses hidden prompt + SOPS + sanitized verifier only.
2. **Discord secret is VPS-only.** `secrets/discord-secrets.yaml` is intentionally present on VPS and not copied into local repo artifacts.
3. **The verifier uses temporary plaintext only under `/tmp`.** The script shreds temp files on exit and unsets the token variable after Discord API validation.
4. **SOPS version is older but functional.** Decrypt/encrypt workflows pass with the current age identity.

---

## 9. Auditor Gate

Auditor gate required before P2-002 can be marked complete.

Planned auditor report path:

- `audit-reports/P2/STEP-P2-002/step-p2-002-auditor-report.md`

Auditor must verify:

- Evidence does not expose Discord token material.
- SOPS path and `.sops.yaml` rule are correct.
- Verifier output proves decrypt/API success without leaking token.
- Temporary plaintext is handled safely.
- Aizanta isolation remains intact.

---

## 10. Security Scan

This evidence intentionally includes only sanitized verifier output. The following public values are safe to document:

- Bot/Application ID: `1510873134981582858`
- Bot username: `Guinevere`

This evidence does **not** include:

- Discord bot token
- Token prefix or suffix
- Token length beyond sanitized decrypt byte count
- Authorization header value
- Raw SOPS plaintext

---

## 11. Acceptance Criteria Mapping

| P2-002 Acceptance Item | Status |
|---|---|
| Bot token generated/reset | PASS — completed during C3 secure capture flow |
| Token stored with SOPS | PASS — `secrets/discord-secrets.yaml` exists and decrypts |
| Secret file permissions locked down | PASS — chmod 600 |
| Token/API validates as expected bot | PASS — Discord API returns expected bot ID and username |
| No plaintext token in repo evidence | PASS |
| Evidence created at required path | PASS |

---

## 12. Footer

- Source task: P2-002 — Discord bot token generation + SOPS storage
- Date: 2026-06-01
- Implementer: Hephaestus / Guinevere parent orchestration
- Validation method: SOPS decrypt check, Discord API identity check, `.sops.yaml` inspection, no-secret evidence review
