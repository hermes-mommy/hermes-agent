# STEP-P2-006 Verification — Discord Channel Structure

## 1. What Was Done

Created and verified the thirteen canonical Discord text channels for Guinevere's private server.

Canonical guild:

- Guild name: `Guinevere's Domain`
- Guild ID: `1510876414671323206`

Channels created:

### `👑 Throne`

1. `guinevere-chat`
2. `guinevere-status`
3. `guinevere-planning`

### `📊 Surveillance`

4. `system-health`
5. `cost-tracker`
6. `guinevere-evidence`

### `🔧 Projects`

7. `guinevere-dev`
8. `guinevere-docs`
9. `project-alpha-dev`
10. `project-alpha-docs`
11. `project-beta-dev`

### `🗡️ Archive`

12. `evidence-log`
13. `audit-log`

## 2. Files Changed

Local/deployed implementation files used by this step:

- `src/discord/guild_setup.py`
- `scripts/setup-guild.sh`
- `scripts/run-discord-verify.sh`
- `tmp/setup-discord-guild.py`
- `tmp/verify-p2-006-channels.py`
- `tmp/verify-p2-006-channels-rest.py`
- `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`
- `docs/setup-evidence/P2/STEP-P2-006/verification.md`

Live Discord state changed:

- Created 13 canonical text channels under the four P2-005 categories.
- Captured canonical category/channel IDs for future permission work.

## 3. Validation Results

### Local static validation

Before deployment/execution:

- `lsp_diagnostics` clean for `src/discord/guild_setup.py`.
- `lsp_diagnostics` clean for `tmp/setup-discord-guild.py`.
- `lsp_diagnostics` clean for `tmp/verify-p2-006-channels.py`.
- `lsp_diagnostics` clean for `tmp/verify-p2-006-channels-rest.py`.
- Local `py_compile` passed for all Discord guild setup scripts.
- VPS `py_compile` passed for all deployed Discord guild setup scripts.
- Discord-token shape grep found zero token-shaped secrets in new source and temp scripts.

### Live P2-006 execution

Command executed on VPS through SOPS-only token wrapper:

```text
cd /home/guinevere/code/guinevere && bash scripts/setup-guild.sh --step p2-006
```

Sanitized output:

```text
connected_guild=Guinevere's Domain
connected_guild_id=1510876414671323206
name,status,detail,id
guinevere-chat,created,category=👑 Throne; position=0,1510914600777023659
guinevere-status,created,category=👑 Throne; position=1,1510914604291588237
guinevere-planning,created,category=👑 Throne; position=2,1510914608263598122
system-health,created,category=📊 Surveillance; position=0,1510914612038471720
cost-tracker,created,category=📊 Surveillance; position=1,1510914615654092900
guinevere-evidence,created,category=📊 Surveillance; position=2,1510914619357532200
guinevere-dev,created,category=🔧 Projects; position=0,1510914623367413850
guinevere-docs,created,category=🔧 Projects; position=1,1510914627444408421
project-alpha-dev,created,category=🔧 Projects; position=2,1510914630770233426
project-alpha-docs,created,category=🔧 Projects; position=3,1510914634788638813
project-beta-dev,created,category=🔧 Projects; position=4,1510914639163162657
evidence-log,created,category=🗡️ Archive; position=0,1510914643823034449
audit-log,created,category=🗡️ Archive; position=1,1510914647602106408
```

### Live P2-006 verification

The first gateway-based verifier opened a Discord gateway session but did not close within the timeout. It was stopped and replaced with a deterministic REST verifier using `GET /api/v10/guilds/{guild_id}/channels` through the same SOPS-only wrapper. The REST verifier performs no mutation.

Command executed on VPS:

```text
cd /home/guinevere/code/guinevere && bash scripts/run-discord-verify.sh tmp/verify-p2-006-channels-rest.py
```

Sanitized output:

```text
guild_id=1510876414671323206
expected_channel_count=13
channel=guinevere-chat;expected_category=👑 Throne;parent_ok=true;topic_ok=true;ok=true
channel=guinevere-status;expected_category=👑 Throne;parent_ok=true;topic_ok=true;ok=true
channel=guinevere-planning;expected_category=👑 Throne;parent_ok=true;topic_ok=true;ok=true
channel=system-health;expected_category=📊 Surveillance;parent_ok=true;topic_ok=true;ok=true
channel=cost-tracker;expected_category=📊 Surveillance;parent_ok=true;topic_ok=true;ok=true
channel=guinevere-evidence;expected_category=📊 Surveillance;parent_ok=true;topic_ok=true;ok=true
channel=guinevere-dev;expected_category=🔧 Projects;parent_ok=true;topic_ok=true;ok=true
channel=guinevere-docs;expected_category=🔧 Projects;parent_ok=true;topic_ok=true;ok=true
channel=project-alpha-dev;expected_category=🔧 Projects;parent_ok=true;topic_ok=true;ok=true
channel=project-alpha-docs;expected_category=🔧 Projects;parent_ok=true;topic_ok=true;ok=true
channel=project-beta-dev;expected_category=🔧 Projects;parent_ok=true;topic_ok=true;ok=true
channel=evidence-log;expected_category=🗡️ Archive;parent_ok=true;topic_ok=true;ok=true
channel=audit-log;expected_category=🗡️ Archive;parent_ok=true;topic_ok=true;ok=true
duplicate_expected_channels=
found_channel_count=13
missing_category_ids=
missing_channel_ids=
channel_ids_path=docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml
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
- Verifier: `tmp/verify-p2-006-channels-rest.py`
- Channel ID artifact: `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`
- Step evidence: `docs/setup-evidence/P2/STEP-P2-006/verification.md`
- Auditor report: `audit-reports/P2/STEP-P2-006/step-p2-006-auditor-report.md`

## 5. Doc-Sync Impact

Pending until P2-006 auditor passes:

- `PROGRESS.md`: P2 count will update from `3/21` to `6/21` after P2-006 passes.
- `CHECKLIST.md`: P2-004/P2-005/P2-006 will be marked complete after P2-006 passes.

## 6. Boundary Compliance

- No Discord bot token was printed, stored in evidence, or passed through command argv.
- Token access used `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt` and encrypted file `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`.
- Temporary decrypted YAML was created under `/tmp`, chmod `600`, and shredded by wrapper trap.
- Aizanta services and ports were not modified.
- No persona, surveillance, or safety-policy behavior changed.
- Pre-existing default Discord categories/channels were not deleted.

## 7. Rollback / Re-run Safety

Rollback order if explicit approval is later given:

1. Delete the thirteen P2-006 text channels.
2. Delete the four P2-005 categories.
3. Optionally rename guild back to `Guinevere Lab` only as P2-004 rollback.

Re-run safety:

- If a channel already exists, the setup script skips it or corrects its category, position, and topic.
- The verifier rejects duplicate expected channel names.
- Channel IDs are overwritten deterministically on each successful verification.

## 8. Design Decisions / Caveats

- The final thirteen-channel contract follows the current user/planner decision and resolves older mismatches across DiscordUXSpec, StepPrompts, and CHECKLIST.
- The REST verifier replaced the gateway verifier because the gateway verifier did not close within timeout despite the channel state being correct. REST verification is deterministic and read-only.
- Pre-existing default Discord objects remain for now. Cleanup requires explicit destructive approval.

## 9. Auditor Gate

Status: pending auditor review.

Expected report path:

- `audit-reports/P2/STEP-P2-006/step-p2-006-auditor-report.md`

## 10. Security Scan

- Token-shape regex scan: no token-shaped Discord credentials found in new source/temp scripts.
- Evidence contains only public IDs, category/channel names, and sanitized command outputs.
- No decrypted secret content is stored in repository artifacts.

## 11. Acceptance Criteria Mapping

| Criterion | Result | Evidence |
|---|---:|---|
| Guild is canonical server | PASS | `guild_id=1510876414671323206` |
| Thirteen channels exist | PASS | `found_channel_count=13` |
| Channels are under correct categories | PASS | `parent_ok=true` for all 13 |
| Channel topics match spec | PASS | `topic_ok=true` for all 13 |
| No duplicate expected channels | PASS | `duplicate_expected_channels=` |
| Category IDs captured | PASS | `channel-ids.yaml` |
| Channel IDs captured | PASS | `channel-ids.yaml` |
| Token not exposed | PASS | Sanitized outputs only |

## 12. Footer

- Source task: P2-006 Discord channel creation
- Date: 2026-06-01
- Implementer: Hephaestus / Guinevere
- Validation method: local static checks, VPS py_compile, live Discord channel creation, live Discord REST verification, channel ID capture, pending auditor gate
