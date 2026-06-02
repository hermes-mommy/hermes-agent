# STEP-P2-010 Verification — Slash Commands Registration

## 1. What Was Done

Implemented the P2-010 slash-command registry and SOPS-safe command sync flow for the Guinevere Discord guild.

- Added a canonical 33-command registry from `docs/60-persona/63-DiscordUXSpec_v1.0.md`.
- Added guild-scoped Discord REST sync and verification scripts.
- Extended `scripts/run-discord-verify.sh` allowlist so both P2-010 scripts run through the SOPS temp-file wrapper.
- Cleaned the P2-010 `StepPrompts.md` token snippet from inline `DISCORD_BOT_TOKEN=$(sops -d ... | grep ... | awk ...)` to wrapper invocations.
- Preserved the command-surface-only scope: command behavior is intentionally implemented in later P2 steps.

## 2. Files Changed

| Path | Change |
|---|---|
| `src/discord/commands.py` | Added canonical 33 slash-command specs and REST payload builder. |
| `src/discord/permissions.py` | Allowed the shared Discord REST helper to send list payloads for bulk command overwrite. |
| `tmp/sync-p2-010-commands.py` | Added SOPS-wrapper-compatible guild command sync script. |
| `tmp/verify-p2-010-commands-rest.py` | Added SOPS-wrapper-compatible guild command REST verifier. |
| `scripts/run-discord-verify.sh` | Added P2-010 sync/verify scripts to the allowlist. |
| `stepprompts/StepPrompts.md` | Replaced unsafe P2-010 token snippet with wrapper commands. |
| `docs/setup-evidence/P2/STEP-P2-010/verification.md` | Added this evidence file. |

## 3. Validation Results (exact output)

### 3.1 Static Validation (Local)

All static checks passed on local machine before deployment:

| Check | Result |
|---|---|
| `py_compile src/discord/commands.py src/discord/permissions.py tmp/sync-p2-010-commands.py tmp/verify-p2-010-commands-rest.py` | ✅ Exit 0 |
| `lsp_diagnostics` on all 4 Python files (all severity levels) | ✅ Clean — zero errors, zero warnings |
| `python -c "from src.discord.commands import ..."` command count | ✅ `command_count=33` |
| `grep` for `DISCORD_BOT_TOKEN` in `src/discord/` and `tmp/` | ✅ No matches |
| `grep` for `os.environ.get("DISCORD_BOT_TOKEN")` in P2-010 scripts | ✅ No matches |

### 3.2 Static Validation (VPS)

```text
$ .venv/bin/python -m py_compile src/discord/commands.py src/discord/permissions.py tmp/sync-p2-010-commands.py tmp/verify-p2-010-commands-rest.py
[exit 0, no output]

$ .venv/bin/python tmp/p2-010-registry-check.py
command_count=33
canonical_names=status,mood,help,safeword,loop-start,loop-stop,loop-pause,loop-resume,loops,evidence,loop-priority,memory-search,memory-add,memory-forget,memory-export,surveillance-status,surveillance-pause,surveillance-resume,cost,budget,cost-alert,approve,deny,approve-all,focus,casual,consent,punishment,reward,restart-service,backup-now,health-check,clear-cache
```

### 3.3 Runtime Sync — Wrapper Output

```text
$ cd /home/guinevere/code/guinevere && scripts/run-discord-verify.sh tmp/sync-p2-010-commands.py
Synced 33 commands to guild 1510876414671323206
expected_commands=33
category=core count=4 names=status,mood,help,safeword
category=loop count=7 names=loop-start,loop-stop,loop-pause,loop-resume,loops,evidence,loop-priority
category=memory count=4 names=memory-search,memory-add,memory-forget,memory-export
category=surveillance count=3 names=surveillance-status,surveillance-pause,surveillance-resume
category=finance count=3 names=cost,budget,cost-alert
category=system count=8 names=approve,deny,approve-all,focus,casual,consent,punishment,reward
category=admin count=4 names=restart-service,backup-now,health-check,clear-cache
result=PASS
```

### 3.4 Runtime REST Verification — Wrapper Output

```text
$ cd /home/guinevere/code/guinevere && scripts/run-discord-verify.sh tmp/verify-p2-010-commands-rest.py
commands_count=33
expected_commands=33
all_names_match=true
missing=none
unknown=none
category=core present=4/4 names=status,mood,help,safeword
category=loop present=7/7 names=loop-start,loop-stop,loop-pause,loop-resume,loops,evidence,loop-priority
category=memory present=4/4 names=memory-search,memory-add,memory-forget,memory-export
category=surveillance present=3/3 names=surveillance-status,surveillance-pause,surveillance-resume
category=finance present=3/3 names=cost,budget,cost-alert
category=system present=8/8 names=approve,deny,approve-all,focus,casual,consent,punishment,reward
category=admin present=4/4 names=restart-service,backup-now,health-check,clear-cache
canonical_names=surveillance-status,status,loop-start,punishment,backup-now,memory-forget,budget,consent,loops,memory-search,memory-export,evidence,loop-resume,mood,safeword,clear-cache,restart-service,casual,health-check,approve-all,reward,loop-stop,deny,loop-priority,focus,help,loop-pause,cost,cost-alert,approve,memory-add,surveillance-resume,surveillance-pause
result=PASS
```

## 4. Evidence Artifacts

| Artifact | Status |
|---|---|
| `docs/setup-evidence/P2/batch-plan-010-012.md` | Parent-read planner gate. |
| `research-reports/P2/p2-010-token-cleanup-report.md` | Parent-read token cleanup report. |
| `research-reports/P2/p2-010-012-local-code-docs-report.md` | Parent-read local command research. |
| `research-reports/P2/p2-010-012-discordpy-reference-report.md` | Parent-read Discord.py reference report. |
| `research-reports/P2/p2-010-012-safety-evidence-report.md` | Parent-read safety/evidence report. |
| `audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md` | Pending auditor gate. |

## 5. Shared VPS Impact

No destructive VPS operation was introduced. The runtime sync scripts only call Discord's guild application-command REST endpoint (no gateway, no database, no Docker mutation).

### Aizanta Health Checks (Pre/Post — No Changes)

All Aizanta containers healthy before and after sync:

```text
$ docker ps --filter 'name=aizanta' --format '{{.Names}} {{.Status}}'
aizanta-bot        Up 8 days (healthy)
aizanta-nginx      Up 8 days (healthy)
aizanta-frontend   Up 11 hours (healthy)
aizanta-postgres   Up 9 days (healthy)
aizanta-redis      Up 9 days (healthy)

$ ss -tlnp | grep -E '5432|6379|80'
LISTEN 127.0.0.1:5432    (Aizanta PostgreSQL)
LISTEN 127.0.0.1:6379    (Aizanta Redis)
LISTEN 100.94.104.22:80  (Aizanta nginx)
```

Guinevere ports (6380 Redis, 8000 core) also present and unchanged.

## 6. ADR Compliance

| ADR | Compliance |
|---|---|
| ADR-015 Secrets Management | Token remains behind SOPS wrapper + `DISCORD_SECRETS_PATH`; no plaintext token in argv/code/evidence. |
| ADR-018 Security Defense-in-Depth | Fail-closed Faiz-only helper and no broad environment token fallback. |
| ADR-022 Communication Channel Strategy | Implements Discord slash-command surface from Discord UX spec. |
| ADR-001/ADR-002 Safety Boundaries | `/safeword` is registered as a canonical command; no safety policy behavior changed. |

No ADR modification is required for this step.

## 7. AC/DoD Reference

| Source | Requirement | Status |
|---|---|---|
| `CHECKLIST.md` P2-010 | `/` in chat shows 33 slash commands | ✅ **PASS** — REST verify confirms 33 commands in guild with all 7 categories. |
| `StepPrompts.md` P2-010 | 33 commands synced and visible in Discord | ✅ **PASS** — Sync output shows `Synced 33 commands to guild`. Verify output shows `commands_count=33`. |
| User instruction | Token snippet cleaned to SOPS wrapper pattern | ✅ **PASS** — Unsafe heredoc replaced in StepPrompts; no `os.environ.get("DISCORD_BOT_TOKEN")` in any P2-010 script. |
| Planner gate | Guild-scoped sync, no global sync, no hardcoded token | ✅ **PASS** — Sync path is guild-scoped (`/guilds/{id}/commands`); no global sync; token via `get_token()` only. |

## 8. Rollback/Re-run Safety

- Re-running `tmp/sync-p2-010-commands.py` is idempotent because Discord bulk overwrites the guild command set with the canonical 33-command payload.
- Rollback path: sync a previous command payload or delete guild commands through the Discord application-command REST endpoint.
- No database, Docker, Redis, or persistent local runtime state is modified by the code changes.

## 9. Design Decisions/Caveats

- Used Discord REST bulk overwrite instead of a long-running `discord.py` client to avoid token exposure and startup lifecycle risk in a verification step.
- Registered only the command surface. Full runtime behavior belongs to later P2 steps; P2-012 wires `/status` behavior.
- Faiz-only enforcement helper fails closed by comparing interaction user ID to runtime guild owner ID; it does not hardcode Faiz's user ID or confuse guild ID with owner ID.
- P2-017's separate stale token snippets are intentionally deferred outside this batch.

## 10. Evidence Gate

**PASS** — All verification steps completed:

| Check | Result |
|---|---|
| Local `py_compile` (all 4 Python files) | ✅ PASS |
| LSP diagnostics (all severity levels) | ✅ Clean |
| Registry validation (`command_count=33`, all names correct) | ✅ PASS |
| Token scan (no `DISCORD_BOT_TOKEN` in src/ or tmp/) | ✅ Clean |
| VPS `py_compile` | ✅ PASS |
| VPS registry validation | ✅ `command_count=33`, names match |
| SOPS wrapper sync (33 commands synced) | ✅ PASS — `result=PASS` |
| SOPS wrapper REST verification (33 verified) | ✅ PASS — `all_names_match=true` |
| Aizanta health (pre/post) | ✅ All 5 containers healthy, ports unchanged |

## 11. Auditor Gate

Pending independent auditor report at `audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md`.

## 12. Footer

- Source task: STEP-P2-010 Discord slash command registration.
- Date: 2026-06-01.
- Implementer: Sisyphus-Junior (implementation ownership) + Parent (typing fixes on tmp/ scripts).
- Validation method: Python compile + LSP diagnostics + VPS static validation + SOPS-wrapper REST sync + SOPS-wrapper REST verification against guild `1510876414671323206`. All P2-010 files LSP-clean at all severity levels.
- Status: **READY FOR INDEPENDENT AUDITOR GATE**.
