# STEP-P2-003 Verification — Discord Gateway Intents

| Field | Value |
|---|---|
| Step | P2-003 |
| Title | Discord gateway intents configuration |
| Date | 2026-06-01 |
| Status | Implemented — evidence formalized, auditor pending |
| Evidence path | `docs/setup-evidence/P2/STEP-P2-003/verification.md` |

---

## 1. What Was Done

Implemented Guinevere's Discord gateway intent configuration in source code and aligned project dependencies with the already-installed VPS runtime package.

Changes:

- Added `discord.py>=2.4` to `pyproject.toml`.
- Created `src/discord/intents.py` with:
  - `get_intents()` — builds Guinevere's Discord gateway intents.
  - `validate_intents()` — fail-fast validation for required gateway flags.
  - `IntentValidationResult` — typed validation result.
- Deployed both changed files to the VPS and verified with the VPS `.venv`.

Required privileged intents enabled in code:

- `message_content=True`
- `members=True`
- `presences=True`

Operational standard intents explicitly enabled:

- `guilds=True`
- `messages=True`
- `reactions=True`
- `voice_states=True`

---

## 2. Files Changed

Created:

- `src/discord/intents.py`
- `docs/setup-evidence/P2/STEP-P2-003/verification.md`
- `tmp/verify-p2-003-intents.py`

Modified:

- `pyproject.toml`

Deployed to VPS:

- `/home/guinevere/code/guinevere/src/discord/intents.py`
- `/home/guinevere/code/guinevere/pyproject.toml`

---

## 3. Validation Results

### Local static validation

| Check | Result |
|---|---|
| `lsp_diagnostics` on `src/discord/intents.py` | PASS — no diagnostics |
| `pyproject.toml` dependency grep | PASS — `discord.py>=2.4` present |
| Source grep for privileged intents | PASS — `message_content`, `members`, `presences` present and set true |

Important fix applied during validation:

- Because the repository has a local package at `src/discord`, plain `import discord` caused basedpyright to treat the external `discord.py` import as an implicit relative import. The module now loads the external package with `importlib.import_module("discord")` and a typed Protocol boundary, with no type-ignore or suppression.

### VPS runtime validation

Verifier deployed to `/tmp/verify-p2-003-intents.py` and executed with the project virtualenv:

```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere && .venv/bin/python /tmp/verify-p2-003-intents.py"
```

Sanitized output:

```text
valid=True
enabled=message_content,members,presences,guilds,messages,reactions,voice_states
missing=
message_content=True
members=True
presences=True
```

Result: PASS — code-level intents match the P2-003 required Developer Portal privileged intents.

---

## 4. Evidence Artifacts

| Artifact | Path / Source | Purpose |
|---|---|---|
| Intents module | `src/discord/intents.py` | Source implementation |
| Dependency declaration | `pyproject.toml` | Reproducible discord.py dependency |
| VPS verifier | `tmp/verify-p2-003-intents.py` and VPS `/tmp/verify-p2-003-intents.py` | Runtime validation |
| Discord app command research | `research-reports/P2/discord-py-2-app-commands.md` | Confirms discord.py 2.x requires explicit intents |
| Intents/token research | `research-reports/P2/discord-intents-token-security.md` | Intent API and privileged-intent security context |
| Source structure scan | `research-reports/P2/source-structure-discord-pre-p2.md` | Confirms `src/discord/` was empty and pyproject lacked discord.py |
| Planner gate | `docs/setup-evidence/P2/batch-plan-001-003.md` | Approved P2-003 implementation plan |
| This evidence | `docs/setup-evidence/P2/STEP-P2-003/verification.md` | Formal P2-003 verification artifact |

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
| Discord token secrecy | PASS — no token handling in `src/discord/intents.py` |
| Privileged intents | PASS — Presence, Server Members, and Message Content intentionally enabled per Faiz/P2 StepPrompt |
| Minimal intent caveat | DOCUMENTED — three privileged intents exceed slash-only minimum and are accepted for Guinevere's planned companion behavior |
| Aizanta isolation | PASS — no Aizanta service, secret, container, or port touched |
| Resource limit | PASS — validation is import-only and does not start a gateway session |
| Consent / surveillance boundary | PASS — no surveillance behavior implemented |
| Persona safety | PASS — no persona prompt or HARD STOP behavior changed |
| Unsafe shortcuts | PASS — no type suppression, no empty catches, no test deletion |

---

## 7. Rollback / Re-run Safety

Rollback source changes:

1. Remove `src/discord/intents.py`.
2. Remove `discord.py>=2.4` from `pyproject.toml`.
3. Delete this evidence file if regenerating.

Re-run validation:

```bash
scp "src/discord/intents.py" guinevere-vps:/home/guinevere/code/guinevere/src/discord/intents.py
scp "pyproject.toml" guinevere-vps:/home/guinevere/code/guinevere/pyproject.toml
scp "tmp/verify-p2-003-intents.py" guinevere-vps:/tmp/verify-p2-003-intents.py
ssh guinevere-vps "cd /home/guinevere/code/guinevere && .venv/bin/python /tmp/verify-p2-003-intents.py"
```

No runtime service restart is required because P2-003 only defines configuration code and does not run a Discord gateway client yet.

---

## 8. Design Decisions / Caveats

1. **Privileged intents are broader than slash-only minimum.** Research recommends disabling `message_content` and `presences` for slash-only bots, but P2-003 and Faiz's portal setup explicitly require Presence, Server Members, and Message Content. This is accepted for Guinevere's planned companion behavior and should be reviewed again during P2-009 permission verification.
2. **Dynamic external import avoids local package collision.** The repo package is named `src/discord`, which collides with external `discord.py` for static analysis. `importlib.import_module("discord")` avoids implicit relative import diagnostics while preserving runtime behavior.
3. **No gateway connection yet.** This step validates intent construction only; connecting the bot is a later P2 step.
4. **Local Windows Python lacks discord.py.** Local runtime import failed before dependency sync; VPS `.venv` validation passed. The dependency is now declared in `pyproject.toml` for reproducibility.

---

## 9. Auditor Gate

Auditor gate required before P2-003 can be marked complete.

Planned auditor report path:

- `audit-reports/P2/STEP-P2-003/step-p2-003-auditor-report.md`

Auditor must verify:

- `pyproject.toml` declares `discord.py>=2.4`.
- `src/discord/intents.py` enables required privileged intents and operational standard intents.
- LSP diagnostics are clean.
- VPS runtime verifier passes.
- No token handling or token leakage exists in the step.
- Caveats are documented and appropriately deferred.

---

## 10. Security Scan

This step contains no token loading and no secret file access.

Security-relevant checks:

| Check | Result |
|---|---|
| No `DISCORD_TOKEN` usage | PASS |
| No token-shaped strings | PASS |
| No SOPS decrypt | PASS — not needed for intents-only step |
| No gateway connect / token login | PASS |
| Privileged intents documented | PASS |

---

## 11. Acceptance Criteria Mapping

| P2-003 Acceptance Item | Status |
|---|---|
| Message Content intent enabled | PASS |
| Server Members intent enabled | PASS |
| Presence intent enabled | PASS |
| `src/discord/intents.py` exists | PASS |
| Runtime validation passes on VPS | PASS |
| Dependency declared in project metadata | PASS |
| Evidence created at required path | PASS |
| No token exposure | PASS |

---

## 12. Footer

- Source task: P2-003 — Discord bot gateway intents configuration
- Date: 2026-06-01
- Implementer: Hephaestus / Guinevere parent orchestration
- Validation method: LSP diagnostics, source grep, VPS `.venv` runtime verification, no-secret evidence review
