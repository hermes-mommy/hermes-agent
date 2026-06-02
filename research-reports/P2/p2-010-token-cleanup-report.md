# P2-010 Token Cleanup Report

**Date:** 2026-06-01
**Scope:** STEP-P2-010 StepPrompts token snippet cleanup
**Output path:** `research-reports/P2/p2-010-token-cleanup-report.md`
**Method:** Parent-verified from `stepprompts/StepPrompts.md` and `scripts/run-discord-verify.sh` after token-specialist output wrote the wrong report path.

---

## Verdict

**PASS WITH REQUIRED CLEANUP.** `stepprompts/StepPrompts.md` P2-010 contains a blocking stale token invocation that decrypts SOPS inline and exports `DISCORD_BOT_TOKEN` to a child process. This must be replaced with the existing SOPS temp-file wrapper pattern in `scripts/run-discord-verify.sh`.

---

## Exact Stale Lines

File: `stepprompts/StepPrompts.md`

```text
5523: DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk '{print $2}' | tr -d '"') \
5524:   python scripts/sync-commands.py
```

Blocking issues:

- Uses inline `sops -d ... | grep ... | awk ...` token extraction.
- Uses `DISCORD_BOT_TOKEN` instead of the project SOPS wrapper contract.
- Encourages the P2-010 sync script to read `os.environ.get("DISCORD_BOT_TOKEN")`.
- Bypasses the wrapper allowlist and temp-file cleanup discipline used by P2-004..P2-009.

---

## Required Replacement Pattern

Replace the stale snippet with:

```bash
# SOPS-only token flow: decrypts to a temporary YAML file, exports DISCORD_SECRETS_PATH,
# runs the allowlisted sync script, then shreds the temp file and unsets the env var.
scripts/run-discord-verify.sh tmp/sync-p2-010-commands.py
```

If a separate verification script is used after sync, invoke it the same way:

```bash
scripts/run-discord-verify.sh tmp/verify-p2-010-commands-rest.py
```

---

## Required Wrapper Allowlist Update

File: `scripts/run-discord-verify.sh`

Current allowlist ends at P2-009 scripts. P2-010 implementation must add only the exact new scripts required, for example:

```bash
tmp/sync-p2-010-commands.py|tmp/verify-p2-010-commands-rest.py
```

The wrapper must keep this existing flow unchanged:

1. `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt`
2. `sops --decrypt secrets/discord-secrets.yaml > "$TEMP_SECRETS"`
3. `chmod 600 "$TEMP_SECRETS"`
4. `export DISCORD_SECRETS_PATH="$TEMP_SECRETS"`
5. Python script calls `src.discord.guild_setup.get_token()`.
6. `trap cleanup EXIT` unsets `DISCORD_SECRETS_PATH`.
7. Cleanup uses `shred -u "$TEMP_SECRETS"` with `rm -f` fallback.

---

## Python Token Contract

P2-010 scripts must use:

```python
from src.discord.guild_setup import get_token

token = get_token()
```

They must not use:

```python
os.environ.get("DISCORD_BOT_TOKEN")
os.environ["DISCORD_BOT_TOKEN"]
```

---

## Related Stale Token Snippets Outside This Batch

`stepprompts/StepPrompts.md` also contains later P2-017 service examples around lines 5846, 5854, and 5866 that use plaintext temp/env-file token handling. They are outside P2-010..P2-012 implementation scope and should be flagged for the later P2-017 cleanup batch, not silently rewritten here unless the planner decides to update the StepPrompts shared block comprehensively.

---

## Planner Inputs

- P2-010 implementation must clean lines 5523-5524 before or during the step.
- `scripts/run-discord-verify.sh` must allowlist the new P2-010 sync/verify scripts.
- Evidence must show wrapper invocation command only; no decrypted token, token prefix, env dump, or raw secret content.
- Auditor must grep changed files/evidence for `DISCORD_BOT_TOKEN=$(sops`, `discord_bot_token | awk`, and any token-looking plaintext.

---

## Footer

Source task: P2-010 token cleanup research
Validation: Parent-read `StepPrompts.md` lines 5413-5525 and `scripts/run-discord-verify.sh` lines 1-32
Secret handling: No decrypted secrets read or recorded
