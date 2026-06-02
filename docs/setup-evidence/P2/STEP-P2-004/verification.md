# STEP-P2-004 Verification — Discord Server Name Resolution

## 1. What Was Done

Resolved the Discord server-name mismatch for Guinevere P2.

- Previous live server name: `Guinevere Lab`
- Canonical server name after P2-004: `Guinevere's Domain`
- Stable guild ID: `1510876414671323206`
- Bot identity: `Guinevere` / application ID `1510873134981582858`

The existing private server was renamed in place. No new server was created.

## 2. Files Changed

Created or updated local implementation/support files:

- `src/discord/guild_setup.py`
- `scripts/setup-guild.sh`
- `scripts/run-discord-verify.sh`
- `tmp/setup-discord-guild.py`
- `tmp/verify-p2-004-guild-name.py`
- `docs/setup-evidence/P2/STEP-P2-004/verification.md`

Live Discord state changed:

- Guild name changed from `Guinevere Lab` to `Guinevere's Domain`.

## 3. Validation Results

### Local static validation

- `lsp_diagnostics` clean for `src/discord/guild_setup.py`.
- `lsp_diagnostics` clean for `tmp/setup-discord-guild.py`.
- `lsp_diagnostics` clean for `tmp/verify-p2-004-guild-name.py`.
- Local `py_compile` passed for all Discord guild setup scripts.
- VPS `py_compile` passed for all deployed Discord guild setup scripts.
- Discord-token shape grep found zero token-shaped secrets in new source and temp scripts.

### Live P2-004 execution

Command executed on VPS through SOPS-only token wrapper:

```text
cd /home/guinevere/code/guinevere && bash scripts/setup-guild.sh --step p2-004
```

Sanitized output:

```text
connected_guild=Guinevere Lab
connected_guild_id=1510876414671323206
name,status,detail,id
Guinevere's Domain,renamed,renamed from Guinevere Lab,1510876414671323206
```

### Live P2-004 verification

Command executed on VPS through SOPS-only verifier wrapper:

```text
cd /home/guinevere/code/guinevere && bash scripts/run-discord-verify.sh tmp/verify-p2-004-guild-name.py
```

Sanitized output:

```text
guild_id=1510876414671323206
guild_name=Guinevere's Domain
cached_guild_id=1510876414671323206
expected_name=Guinevere's Domain
id_matches=true
name_matches=true
result=PASS
```

### Live P2-004 audit-log verification

Command executed on VPS through SOPS-only verifier wrapper:

```text
cd /home/guinevere/code/guinevere && bash scripts/run-discord-verify.sh tmp/verify-p2-004-audit-log.py
```

Sanitized output:

```text
guild_id=1510876414671323206
guild_name=Guinevere's Domain
expected_name=Guinevere's Domain
audit_entries_checked=1
audit_reason_found=true
result=PASS
```

## 4. Evidence Artifacts

- Planner: `docs/setup-evidence/P2/batch-plan-004-006.md`
- Research: `research-reports/P2/discord-server-setup-best-practices.md`
- Research: `research-reports/P2/vps-discord-guild-state-pre-p2-004.md`
- Research: `research-reports/P2/internal-discord-structure-spec.md`
- Implementation module: `src/discord/guild_setup.py`
- Setup wrapper: `scripts/setup-guild.sh`
- Verification wrapper: `scripts/run-discord-verify.sh`
- Verifier: `tmp/verify-p2-004-guild-name.py`
- Audit-log verifier: `tmp/verify-p2-004-audit-log.py`
- Step evidence: `docs/setup-evidence/P2/STEP-P2-004/verification.md`
- Auditor report: `audit-reports/P2/STEP-P2-004/step-p2-004-auditor-report.md`

## 5. Doc-Sync Impact

Pending until P2-004, P2-005, and P2-006 all pass auditor gates:

- `PROGRESS.md`: P2 count will update from `3/21` to `6/21` after all three steps pass.
- `CHECKLIST.md`: P2-004/P2-005/P2-006 will be marked complete after all three steps pass.

This avoids tracker claims before the batch is fully verified.

## 6. Boundary Compliance

- No Discord bot token was printed, stored in evidence, or passed through command argv.
- Token access used `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt` and encrypted file `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`.
- Temporary decrypted YAML was created under `/tmp`, chmod `600`, and shredded by wrapper trap.
- Aizanta services and ports were not modified.
- No persona, surveillance, or safety-policy behavior changed.
- Existing default Discord channels/categories were not deleted.

## 7. Rollback / Re-run Safety

Rollback command if needed:

```text
cd /home/guinevere/code/guinevere && bash scripts/setup-guild.sh --step p2-004
```

The normal setup script is idempotent for the target name. To roll back manually, use a one-off version of `rename_guild()` with `ROLLBACK_GUILD_NAME = "Guinevere Lab"`, or rename in the Discord dashboard.

Re-run safety:

- If the guild is already named `Guinevere's Domain`, P2-004 returns `skipped` instead of creating or mutating anything else.
- Guild ID verification ensures the original private server remains the target.

## 8. Design Decisions / Caveats

- Chose rename-in-place instead of creating a new server, preserving guild ID `1510876414671323206`, bot membership, and invite state.
- The server-name mismatch was resolved in favor of `Guinevere's Domain` because it is the canonical spec name and this step's explicit DoD.
- Pre-existing default Discord objects (`Text Channels`, `Voice Channels`, `#general`, `General`) are intentionally left untouched. Destructive cleanup is not part of P2-004 and would require explicit approval.

## 9. Auditor Gate

Status: initial auditor returned NEEDS REVIEW for missing explicit audit-log proof; live audit-log verification now PASS and is ready for re-audit.

Expected report path:

- `audit-reports/P2/STEP-P2-004/step-p2-004-auditor-report.md`

## 10. Security Scan

- Token-shape regex scan: no token-shaped Discord credentials found in new source/temp scripts.
- Evidence contains only public IDs, server names, and sanitized command outputs.
- No decrypted secret content is stored in repository artifacts.

## 11. Acceptance Criteria Mapping

| Criterion | Result | Evidence |
|---|---:|---|
| Server name resolved | PASS | `guild_name=Guinevere's Domain` |
| Guild ID stable | PASS | `guild_id=1510876414671323206` |
| Existing server renamed, not recreated | PASS | Same guild ID before/after |
| Discord audit-log reason verified | PASS | `audit_reason_found=true` |
| Bot can access guild | PASS | Setup/verify wrappers connected to guild |
| Token not exposed | PASS | Sanitized outputs only |
| Defaults not destructively removed | PASS | No delete calls in P2-004 |

## 12. Footer

- Source task: P2-004 Discord server creation / canonical server-name resolution
- Date: 2026-06-01
- Implementer: Hephaestus / Guinevere
- Validation method: local static checks, VPS py_compile, live Discord rename, live Discord verification, live Discord audit-log verification, auditor gate
