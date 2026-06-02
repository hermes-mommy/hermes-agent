# STEP-P2-005 Verification — Discord Category Structure

## 1. What Was Done

Created and verified the four canonical Discord categories for Guinevere's private server.

Canonical guild:

- Guild name: `Guinevere's Domain`
- Guild ID: `1510876414671323206`

Categories created:

1. `👑 Throne`
2. `📊 Surveillance`
3. `🔧 Projects`
4. `🗡️ Archive`

## 2. Files Changed

Local/deployed implementation files used by this step:

- `src/discord/guild_setup.py`
- `scripts/setup-guild.sh`
- `scripts/run-discord-verify.sh`
- `tmp/setup-discord-guild.py`
- `tmp/verify-p2-005-categories.py`
- `docs/setup-evidence/P2/STEP-P2-005/verification.md`

Live Discord state changed:

- Created `👑 Throne` category.
- Created `📊 Surveillance` category.
- Created `🔧 Projects` category.
- Created `🗡️ Archive` category.

## 3. Validation Results

### Local static validation

Before deployment/execution:

- `lsp_diagnostics` clean for `src/discord/guild_setup.py`.
- `lsp_diagnostics` clean for `tmp/setup-discord-guild.py`.
- `lsp_diagnostics` clean for `tmp/verify-p2-005-categories.py`.
- Local `py_compile` passed for all Discord guild setup scripts.
- VPS `py_compile` passed for all deployed Discord guild setup scripts.
- Discord-token shape grep found zero token-shaped secrets in new source and temp scripts.

### Live P2-005 execution

Command executed on VPS through SOPS-only token wrapper:

```text
cd /home/guinevere/code/guinevere && bash scripts/setup-guild.sh --step p2-005
```

Sanitized output:

```text
connected_guild=Guinevere's Domain
connected_guild_id=1510876414671323206
name,status,detail,id
👑 Throne,created,position=0,1510913571226259456
📊 Surveillance,created,position=1,1510913575097598012
🔧 Projects,created,position=2,1510913578792915094
🗡️ Archive,created,position=3,1510913582315999333
```

### Live P2-005 verification

Command executed on VPS through SOPS-only verifier wrapper:

```text
cd /home/guinevere/code/guinevere && bash scripts/run-discord-verify.sh tmp/verify-p2-005-categories.py
```

Sanitized output:

```text
guild_id=1510876414671323206
guild_name=Guinevere's Domain
expected_category_count=4
found_category_count=4
category=👑 Throne;expected_position=0;actual_position=0;ok=true
category=📊 Surveillance;expected_position=1;actual_position=1;ok=true
category=🔧 Projects;expected_position=2;actual_position=2;ok=true
category=🗡️ Archive;expected_position=3;actual_position=3;ok=true
pre_existing_or_extra_categories=Text Channels,Voice Channels
result=PASS
```

## 4. Evidence Artifacts

- Planner: `docs/setup-evidence/P2/batch-plan-004-006.md`
- Research: `research-reports/P2/discord-category-channel-api.md`
- Research: `research-reports/P2/discord-permissions-model.md`
- Research: `research-reports/P2/internal-discord-structure-spec.md`
- Implementation module: `src/discord/guild_setup.py`
- Setup wrapper: `scripts/setup-guild.sh`
- Verification wrapper: `scripts/run-discord-verify.sh`
- Verifier: `tmp/verify-p2-005-categories.py`
- Step evidence: `docs/setup-evidence/P2/STEP-P2-005/verification.md`
- Auditor report: `audit-reports/P2/STEP-P2-005/step-p2-005-auditor-report.md`

## 5. Doc-Sync Impact

Pending until P2-004, P2-005, and P2-006 all pass auditor gates:

- `PROGRESS.md`: P2 count will update from `3/21` to `6/21` after all three steps pass.
- `CHECKLIST.md`: P2-004/P2-005/P2-006 will be marked complete after all three steps pass.

This avoids claiming the whole structure before channel creation passes.

## 6. Boundary Compliance

- No Discord bot token was printed, stored in evidence, or passed through command argv.
- Token access used `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt` and encrypted file `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`.
- Temporary decrypted YAML was created under `/tmp`, chmod `600`, and shredded by wrapper trap.
- Aizanta services and ports were not modified.
- No persona, surveillance, or safety-policy behavior changed.
- Pre-existing default Discord categories (`Text Channels`, `Voice Channels`) were not deleted.

## 7. Rollback / Re-run Safety

Rollback order if explicit approval is later given:

1. Delete P2-006 channels first if already created.
2. Delete P2-005 categories after channels are removed.
3. Optionally rename guild back to `Guinevere Lab` only as P2-004 rollback.

Re-run safety:

- If a category already exists, the setup script skips it or corrects its position.
- The verifier accepts pre-existing extra default categories as non-blocking.

## 8. Design Decisions / Caveats

- Category names follow the current user contract exactly: `👑 Throne`, `📊 Surveillance`, `🔧 Projects`, `🗡️ Archive`.
- This intentionally overrides stale variants in older docs (`Mommy's Throne`, `SURVEILLANCE ROOM`, `QUEEN'S COURT`, etc.).
- Default Discord categories are preserved because destructive cleanup was not requested.

## 9. Auditor Gate

Status: pending auditor review.

Expected report path:

- `audit-reports/P2/STEP-P2-005/step-p2-005-auditor-report.md`

## 10. Security Scan

- Token-shape regex scan: no token-shaped Discord credentials found in new source/temp scripts.
- Evidence contains only public IDs, category names, and sanitized command outputs.
- No decrypted secret content is stored in repository artifacts.

## 11. Acceptance Criteria Mapping

| Criterion | Result | Evidence |
|---|---:|---|
| Guild is canonical server | PASS | `guild_name=Guinevere's Domain` |
| Four categories exist | PASS | `found_category_count=4` |
| `👑 Throne` at position 0 | PASS | `ok=true` |
| `📊 Surveillance` at position 1 | PASS | `ok=true` |
| `🔧 Projects` at position 2 | PASS | `ok=true` |
| `🗡️ Archive` at position 3 | PASS | `ok=true` |
| Token not exposed | PASS | Sanitized outputs only |
| Defaults not destructively removed | PASS | Extras documented |

## 12. Footer

- Source task: P2-005 Discord category setup
- Date: 2026-06-01
- Implementer: Hephaestus / Guinevere
- Validation method: local static checks, VPS py_compile, live Discord category creation, live Discord category verification, pending auditor gate
