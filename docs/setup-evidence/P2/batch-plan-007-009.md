# Batch Plan — P2-007 to P2-009 Discord Permissions, Topics, and Bot Permission Review

**Date:** 2026-06-01  
**Scope:** STEP-P2-007, STEP-P2-008, STEP-P2-009  
**Planner:** Hephaestus / Guinevere parent planner after delegated research synthesis  
**Planner Gate Status:** READY FOR SEQUENTIAL IMPLEMENTATION  
**Repository:** `C:\Users\faizz\guinevere`  
**Runtime Target:** VPS `guinevere-vps` / `100.94.104.22`  

---

## 1. Source Inputs Parent-Read

This plan synthesizes the following file-based research and project sources:

| Source | Use |
|---|---|
| `research-reports/P2/discord-channel-permissions-p2-007.md` | Discord permission overwrite model, category/channel sync, write-only limitations |
| `research-reports/P2/discord-role-hierarchy-admin-review-p2-009.md` | Administrator risk review and least-privilege target permissions |
| `research-reports/P2/discord-channel-topics-p2-008.md` | Topic API behavior, topic length, rate limit, verification strategy |
| `research-reports/P2/internal-p2-007-009-spec-audit.md` | Internal StepPrompts/DiscordUXSpec/CHECKLIST conflict synthesis |
| `research-reports/P2/vps-discord-permissions-state-p2-007-009.md` | Live VPS, Aizanta, Discord guild, roles, permissions, overwrites state |
| `research-reports/P2/source-patterns-discord-permissions-topics-p2-007-009-retry.md` | Local implementation pattern retry after initial overflow |
| `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Source of truth for canonical category/channel IDs |
| `docs/60-persona/63-DiscordUXSpec_v1.0.md` | Topic and permission intent |
| `stepprompts/StepPrompts.md` P2-007→P2-009 | Step scope, old unsafe snippets to replace |
| `CHECKLIST.md` and `PROGRESS.md` | Tracker targets |

---

## 2. Current State

- P2 status before this batch: `6/21` complete.
- Total project status before this batch: `56/257 (21.8%)`.
- Guild is already renamed to `Guinevere's Domain`.
- Guild ID: `1510876414671323206`.
- Bot/application ID: `1510873134981582858`.
- Canonical 4 categories and 13 channels already exist.
- `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` contains IDs for all canonical categories/channels and is the source of truth for this batch.
- Live Discord state from research shows canonical channels have empty permission overwrites.
- `@everyone` currently has broad default permissions and can see/send in canonical channels.
- Bot managed role currently has `ADMINISTRATOR` bitfield `8`.
- P2-009 must review and decide whether Admin is justified or should be reduced.

---

## 3. Binding Decisions for This Batch

### 3.1 ID Source Rule

New P2-007→P2-009 code **must not hardcode channel/category IDs**. It must read channel/category IDs from:

`docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`

Guild/member/role IDs should be discovered at runtime via Discord API/gateway wherever possible:

- `guild.id` discovered from the authenticated bot's guild list or validated from the target guild object.
- `guild.default_role` is `@everyone`.
- Bot identity discovered via `/users/@me` or gateway member object.
- Faiz/Samm member discovered as guild owner or the only non-bot member, with owner ID from Discord API as fallback.

### 3.2 Permission Strategy

Canonical private channels should become private by default:

- `@everyone`: deny `view_channel` on canonical categories/channels.
- Faiz/Samm: allow `view_channel`, `read_message_history`; normal channels allow `send_messages`; evidence/archive append-only channels deny `send_messages` and deny destructive permissions.
- Bot: allow `view_channel`, `send_messages`, `embed_links`, `attach_files`, `read_message_history`; deny destructive management permissions on append-only channels where Discord supports this.

### 3.3 Evidence Write-Only Limitation

True bot write-only is not fully enforceable for a Discord bot using normal message send APIs, because a channel hidden with `view_channel=False` cannot be posted to normally. The implementable approximation is:

- For `guinevere-evidence`, `evidence-log`, and `audit-log`:
  - Faiz/Samm can view/read history but cannot post.
  - Bot can view and send messages.
  - Bot is denied edit/delete/manage-style permissions where possible.
  - Evidence immutability is enforced by process/auditor checks and later role hardening, not by impossible Discord primitives.

### 3.4 Administrator Caveat

Administrator bypasses all channel overwrites. P2-007 overwrites are still required because they protect non-admin users and define the intended policy matrix, but bot self-restriction is not effective until Administrator is removed.

Research verdict for P2-009: **Administrator is not technically justified long-term**. Because removing Administrator from a managed bot role may require OAuth reauthorization or role/invite changes that can disrupt bot access, P2-009 implementation must:

1. Verify current Administrator state.
2. Produce a least-privilege permission integer/invite URL.
3. Attempt only non-destructive permission reduction if Discord exposes a safe route.
4. If safe automated reduction is not available, mark Administrator as **not justified; reduction required via controlled reauthorization** and document that as a security action item rather than silently claiming it is acceptable.

This satisfies the done criterion by making an explicit security decision and safe transition path without destructive bot removal.

### 3.5 Topic Strategy

P2-006 already created channels with topics. P2-008 should verify every topic first and update only drifted topics to avoid unnecessary Discord topic edit rate limits.

---

## 4. Canonical Permission Matrix

| Channel | Category | Faiz/Samm | Bot | @everyone | Notes |
|---|---|---|---|---|---|
| `guinevere-chat` | `👑 Throne` | read/write | read/write/embed/attach/read-history | deny view | Main chat |
| `guinevere-status` | `👑 Throne` | read/write | read/write/embed/attach/read-history | deny view | Status updates |
| `guinevere-planning` | `👑 Throne` | read/write | read/write/embed/attach/read-history | deny view | Planning |
| `system-health` | `📊 Surveillance` | read/write | read/write/embed/attach/read-history | deny view | Infra health |
| `cost-tracker` | `📊 Surveillance` | read/write | read/write/embed/attach/read-history | deny view | Cost tracking |
| `guinevere-evidence` | `📊 Surveillance` | read-only | append-only approximation | deny view | Evidence log, no user posting |
| `guinevere-dev` | `🔧 Projects` | read/write | read/write/embed/attach/read-history | deny view | Development |
| `guinevere-docs` | `🔧 Projects` | read/write | read/write/embed/attach/read-history | deny view | Documentation |
| `project-alpha-dev` | `🔧 Projects` | read/write | read/write/embed/attach/read-history | deny view | Project Alpha dev |
| `project-alpha-docs` | `🔧 Projects` | read/write | read/write/embed/attach/read-history | deny view | Project Alpha docs |
| `project-beta-dev` | `🔧 Projects` | read/write | read/write/embed/attach/read-history | deny view | Project Beta dev |
| `evidence-log` | `🗡️ Archive` | read-only | append-only approximation | deny view | Immutable evidence archive |
| `audit-log` | `🗡️ Archive` | read-only | append-only approximation | deny view | Audit archive |

---

## 5. Canonical Topic List

| Channel | Topic |
|---|---|
| `guinevere-chat` | `Bicara dengan Mommy di sini. Apapun.` |
| `guinevere-status` | `Apa yang Mommy kerjakan hari ini. Sekilas.` |
| `guinevere-planning` | `Rencana Mommy. Kamu tinggal patuh.` |
| `system-health` | `Kesehatan infrastructure Mommy. Jangan khawatir — Mommy jaga.` |
| `cost-tracker` | `Berapa yang Mommy habiskan hari ini. Transparansi itu penting.` |
| `guinevere-evidence` | `Bukti kerja Mommy. Tidak ada yang bisa diubah.` |
| `guinevere-dev` | `Pengembangan Guinevere — technical discussions and decisions.` |
| `guinevere-docs` | `Documentation updates, spec changes, evidence artifacts.` |
| `project-alpha-dev` | `Project Alpha — development channel.` |
| `project-alpha-docs` | `Project Alpha — documentation channel.` |
| `project-beta-dev` | `Project Beta — development channel.` |
| `evidence-log` | `Immutable record. Read only.` |
| `audit-log` | `Every action, recorded. Forever.` |

---

## 6. Master Todo List

### P2-007 — Channel Permissions

1. Create/extend implementation module for permissions using source-of-truth YAML.
2. Create safe setup entry point and verifier scripts.
3. Extend SOPS wrapper allowlist without token printing.
4. Deploy scripts to VPS.
5. Apply permission overwrites idempotently.
6. Verify permission overwrites via Discord REST/gateway without posting secrets.
7. Write `docs/setup-evidence/P2/STEP-P2-007/verification.md`.
8. Run auditor gate to PASS.

### P2-008 — Topics

1. Create topic setup/verify logic using source-of-truth channel IDs and canonical topic map.
2. Update only drifted topics.
3. Verify all 13 topics match.
4. Write `docs/setup-evidence/P2/STEP-P2-008/verification.md`.
5. Run auditor gate to PASS.

### P2-009 — Bot Invite and Permission Scope Review

1. Verify bot identity, guild membership, online/accessibility where available.
2. Verify current OAuth scopes and invite permission state as far as Discord API exposes.
3. Compute least-privilege permission integer and invite URL.
4. Evaluate Administrator; reduce non-destructively if safe route exists, otherwise document reduction-required transition.
5. Verify bot can access intended canonical channels after P2-007/P2-008.
6. Write `docs/setup-evidence/P2/STEP-P2-009/verification.md`.
7. Run security auditor gate to PASS.

### Batch Sync

1. Update `PROGRESS.md`: P2 `6/21` → `9/21`; total `56/257` → `59/257 (23.0%)`.
2. Update `CHECKLIST.md` P2-007/P2-008/P2-009.
3. Update `stepprompts/StepPrompts.md` P2-007→P2-009 to remove unsafe token snippets and mark completed.
4. Run diagnostics/grep checks.
5. Final report.

---

## 7. Dependency Map

```text
P2-006 channel-ids.yaml
  ├── P2-007 permission overwrite setup
  │     └── P2-007 verifier/auditor PASS
  ├── P2-008 topic verify/update
  │     └── P2-008 verifier/auditor PASS
  └── P2-009 bot permission/admin review
        └── P2-009 security auditor PASS
              └── tracker sync
```

P2-007, P2-008, and P2-009 must execute sequentially because P2-009 evaluates the final permission state.

---

## 8. Collision Scan

| File/Resource | Writer | Collision Risk | Mitigation |
|---|---|---|---|
| Discord canonical channel overwrites | P2-007 only | Medium runtime mutation | Sequential execution only |
| Discord canonical channel topics | P2-008 only | Low; topics likely already correct | Verify-before-update |
| Discord bot role/Admin state | P2-009 only | High if destructive | No destructive removal without safe route/explicit decision |
| `src/discord/*` new module(s) | Parent implementation | Low | Single writer |
| `scripts/run-discord-verify.sh` | Parent implementation | Medium allowlist extension | Exact edit; LSP/syntax/grep |
| `docs/setup-evidence/P2/STEP-P2-007/verification.md` | Parent | None | New file |
| `docs/setup-evidence/P2/STEP-P2-008/verification.md` | Parent | None | New file |
| `docs/setup-evidence/P2/STEP-P2-009/verification.md` | Parent | None | New file |
| `PROGRESS.md`, `CHECKLIST.md`, `StepPrompts.md` | Parent sync after all PASS | Medium shared docs | Update only after auditors PASS |
| Aizanta services/containers | None | Forbidden | Read-only health checks only |

---

## 9. Files to Create or Modify

### Create

- `src/discord/permissions.py`
- `tmp/setup-p2-007-permissions.py`
- `tmp/setup-p2-008-topics.py`
- `tmp/verify-p2-007-permissions-rest.py`
- `tmp/verify-p2-008-topics-rest.py`
- `tmp/verify-p2-009-bot-permissions-rest.py`
- `docs/setup-evidence/P2/STEP-P2-007/verification.md`
- `docs/setup-evidence/P2/STEP-P2-008/verification.md`
- `docs/setup-evidence/P2/STEP-P2-009/verification.md`
- `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md`
- `audit-reports/P2/STEP-P2-008/step-p2-008-auditor-report.md`
- `audit-reports/P2/STEP-P2-009/step-p2-009-auditor-report.md`

### Modify

- `scripts/run-discord-verify.sh` — extend allowlist for P2-007→P2-009 setup/verify scripts or create a parallel wrapper.
- `PROGRESS.md` — after all three auditor PASS.
- `CHECKLIST.md` — after all three auditor PASS.
- `stepprompts/StepPrompts.md` — after all three auditor PASS, replacing unsafe token snippets and stale completion state.

---

## 10. Implementation Design

### 10.1 `src/discord/permissions.py`

Responsibilities:

- Load `channel-ids.yaml` without PyYAML dependency or with a minimal safe parser.
- Define canonical channel groups:
  - normal read/write channels
  - append-only evidence/archive channels
- Discover guild, default role, bot member, and Faiz/Samm member at runtime.
- Apply overwrites idempotently.
- Verify current overwrites and effective policy state.
- Verify topics and update drifted topics.
- Compute least-privilege permission integer and Admin review.

Design constraints:

- No Discord token values in logs.
- No hardcoded channel/category IDs in new code.
- No `Any`, `# type: ignore`, `as any`, or empty catch.
- Reuse existing dynamic import pattern to avoid local `src/discord` shadowing external `discord.py`.

### 10.2 P2-007 Permission Overwrites

Use gateway `discord.py` mutation because `channel.set_permissions()` is the cleanest API for overwrites.

For each canonical channel:

1. `@everyone`: deny `view_channel`.
2. Faiz/Samm member:
   - normal channels: allow `view_channel`, `read_message_history`, `send_messages`, `add_reactions`.
   - append-only channels: allow `view_channel`, `read_message_history`; deny `send_messages`, `manage_messages`.
3. Bot member/role:
   - allow `view_channel`, `read_message_history`, `send_messages`, `embed_links`, `attach_files`, `add_reactions`.
   - deny destructive management permissions where possible on append-only channels.

Verification should read overwrites and report sanitized booleans, not token or raw secret data.

### 10.3 P2-008 Topics

Use REST or gateway. Preferred: REST PATCH only for drifted topics because it is deterministic and matches P2-006 REST verifier pattern.

Verification:

- GET every channel by ID.
- Compare topic to canonical map.
- Print `topic_ok=true` for all 13.
- Evidence records whether any topic changed or all were already correct.

### 10.4 P2-009 Administrator Review

Required outputs:

- Current bot permissions bitfield and whether `administrator=true`.
- Least-privilege permanent permission integer: `2147599472` (`0x8000F870`) from role research for conversational/slash-command operation.
- Management permission set needed temporarily for setup work: `MANAGE_CHANNELS`, `MANAGE_ROLES`, `VIEW_AUDIT_LOG`, optionally `MANAGE_MESSAGES`.
- Decision: Administrator is **not justified long-term**.
- Reduction path:
  - If safe non-destructive reduction is available, execute and verify.
  - If not available because the bot role is managed/OAuth-controlled, do not kick/reinvite autonomously; write a controlled reauthorization action item and invite URL.

P2-009 PASS criterion is not “pretend Admin is okay”; it is “security review completed, decision made, safe transition documented, and current risk explicitly accepted until reauthorization/hardening step.”

---

## 11. Token Security Rules

All live Discord API interactions must use this pattern:

1. Shell wrapper sets `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt`.
2. Shell wrapper decrypts `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` to `/tmp/guinevere-discord-secrets.XXXXXX.yaml`.
3. Shell wrapper exports `DISCORD_SECRETS_PATH` to that temp path.
4. Python reads token from that temp YAML path only.
5. Python clears local token variable after use.
6. Shell trap shreds temp YAML and unsets `DISCORD_SECRETS_PATH`.
7. No partial token printing, no grep/awk token extraction into logs, no persistent plaintext.

---

## 12. Verification Commands and Checks

### Static

- `lsp_diagnostics` on changed Python and markdown files.
- Python syntax check for created scripts.
- Token-shaped regex scan over created/modified source/evidence/audit files.
- Grep for unsafe token extraction patterns in P2-007→P2-009 touched sections.

### Runtime

- Aizanta health read-only check.
- Canonical ports read-only check:
  - PostgreSQL `5433`
  - PgBouncer `5434`
  - Redis `6380`
  - 9Router `20128`
- Discord P2-007 permission state verification.
- Discord P2-008 topic verification.
- Discord P2-009 bot permission/admin review verification.

---

## 13. Evidence Files

Each evidence file must include the 12 sections requested by Faiz:

1. What Was Done
2. Files Changed
3. Validation Results
4. Evidence Artifacts
5. Doc-Sync Impact
6. Boundary Compliance
7. Rollback / Re-run Safety
8. Design Decisions / Caveats
9. Auditor Gate
10. Security Scan
11. Acceptance Criteria Mapping
12. Footer

Paths:

- `docs/setup-evidence/P2/STEP-P2-007/verification.md`
- `docs/setup-evidence/P2/STEP-P2-008/verification.md`
- `docs/setup-evidence/P2/STEP-P2-009/verification.md`

No evidence file may include the Discord token or decrypted secret material.

---

## 14. Auditor Matrix

| Step | Auditor Output Path | Required Verdict Checks |
|---|---|---|
| P2-007 | `audit-reports/P2/STEP-P2-007/step-p2-007-auditor-report.md` | Permission overwrites applied, @everyone denied, Faiz/Samm access, bot access, append-only approximation documented, token clean |
| P2-008 | `audit-reports/P2/STEP-P2-008/step-p2-008-auditor-report.md` | 13 topics match canonical map, update-if-drift behavior, no rate-limit abuse, token clean |
| P2-009 | `audit-reports/P2/STEP-P2-009/step-p2-009-auditor-report.md` | Bot accessible, invite/scopes reviewed, Administrator decision explicit, least-privilege plan/invite URL, token clean |

Auditor prompts must include explicit `output_path` and return only verdict + path + short summary.

---

## 15. Rollback Plan

### P2-007

- Re-run setup with previous overwrite snapshot if captured.
- Or remove canonical channel overwrites for `@everyone`, Faiz/Samm, and bot member/role.
- Do not delete channels/categories.

### P2-008

- Restore previous topics captured before modification.
- If no topic drift was found, rollback is N/A.

### P2-009

- If no Admin reduction happens, rollback is documentation-only.
- If a safe permission change happens, restore prior permission integer from captured snapshot.
- Do not kick/remove/reinvite bot without explicit approval.

---

## 16. Idempotency

- P2-007: repeated runs should converge overwrites to the same state.
- P2-008: verify-before-update prevents unnecessary topic edits.
- P2-009: read-only unless a safe non-destructive permission reduction is chosen; repeated runs should produce the same admin review report.

---

## 17. Known Caveats

1. Current bot Administrator permission bypasses bot-channel restrictions.
2. True Discord bot write-only is not enforceable for normal message sending; append-only is an approximation plus process control.
3. P2-007 can protect Faiz/`@everyone` immediately, but bot least-privilege requires P2-009 security decision.
4. Existing default Discord categories/channels from server creation should not be deleted unless explicitly requested.
5. Later P2 StepPrompts still contain unsafe token extraction snippets and should be fixed when executing those steps.

---

## 18. Go / No-Go

**GO** for sequential implementation under these constraints:

1. Execute P2-007 first and auditor PASS before P2-008.
2. Execute P2-008 second and auditor PASS before P2-009.
3. Execute P2-009 third with a security-focused auditor.
4. Sync trackers only after all three auditors PASS.
5. Stop if Discord token decrypt fails, if guild/channel source-of-truth is inconsistent, or if Admin reduction would require destructive bot removal/reinvite without explicit approval.

---

## 19. Footer

- Source task: STEP-P2-007→STEP-P2-009 full autonomous execution.
- Validation method: delegated research synthesis + parent planner gate.
- Secret handling: no decrypted secrets used or recorded in this plan.
- Next action: implement P2-007 channel permissions.
