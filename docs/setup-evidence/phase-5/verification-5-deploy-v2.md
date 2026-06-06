# ADR-035 Phase 5 OG-6 — PersonaPlugin Deploy + Hermes Restart Verification v2

| Field | Value |
|---|---|
| Scope | OG-6 controlled live operation |
| Date | 2026-06-06 |
| Evidence Root | `docs/setup-evidence/phase-5/` |
| Status | **PASS** |
| Operator Approval | User said `lanjutkan jangan berhenti` after deploy boundary prompt |

---

## 1. What Was Done

Executed the controlled live operation that had been deferred by the final-gate policy:

1. Synced non-secret PersonaPlugin runtime files to the VPS.
2. Enabled the registered Hermes plugin name `guinevere-persona`.
3. Restarted the Hermes gateway under the existing systemd `Restart=always` policy.
4. Smoke-tested plugin activation, service health, cron safety, Redis DB5 persona keys, and recent logs.

No secrets, env files, tokens, raw surveillance data, or intimate data were copied or printed.

---

## 2. Files Changed

### 2.1 Local Files

| File | Change |
|---|---|
| `hermes-config/plugins/guinevere_persona/__init__.py` | Runtime loader updated to load `src/hermes/plugins/persona_plugin.py` directly from repository path, avoiding the pre-existing `src/hermes/__init__.py -> run_agent` package-import caveat. |
| `docs/setup-evidence/phase-5/verification-5-deploy-v2.md` | This deploy evidence file. |

### 2.2 VPS Files

| VPS Path | Change |
|---|---|
| `~/.hermes/plugins/guinevere_persona/__init__.py` | Synced from local non-secret plugin loader. |
| `~/.hermes/plugins/guinevere_persona/plugin.yaml` | Synced from local non-secret plugin metadata. |
| `/home/guinevere/code/guinevere/src/hermes/plugins/persona_plugin.py` | Synced current canonical Redis DB5 PersonaPlugin source. |
| `~/.hermes/config.yaml` | Enabled `guinevere-persona` plugin. A transient mismatched alias `guinevere_persona` was removed after activation verification. |
| `~/.hermes/config.yaml.bak.phase5-og6-*` | Backup created before config edits. |

---

## 3. Validation Results

### 3.1 Pre-Deploy Inspection

| Check | Result |
|---|---|
| Existing VPS plugin dirs listed | PASS — auth/safety/memory plugins existed; `guinevere_persona` absent before sync. |
| Existing config plugin refs inspected | PASS — initial enabled plugin was `auth_overlay` only. |
| Gateway service status inspected | PASS — system service `hermes-gateway.service` was active before deploy. |
| Native cron state inspected | PASS — 5 active jobs existed before deploy. |

### 3.2 Deploy and Activation

| Check | Result |
|---|---|
| Remote files synced | PASS — non-secret plugin loader, metadata, and source were copied. |
| Remote compile | PASS — `python -m compileall ~/.hermes/plugins/guinevere_persona /home/guinevere/code/guinevere/src/hermes/plugins/persona_plugin.py`. |
| Hermes plugin registry | PASS — `hermes plugins list` reports `guinevere-persona` as `enabled`. |
| Gateway restart | PASS — gateway PID changed from `3915293` to `4122336`, then to `4124751` after enabling the registered plugin name. |
| Service active | PASS — `systemctl is-active hermes-gateway.service` returned `active`; final MainPID `4124751`. |
| Plugin registration log | PASS — journal shows `persona_plugin_init` and `guinevere_persona_plugin_registered` with `hook_count=4`. |

### 3.3 Smoke Checks

| Check | Result |
|---|---|
| Plugin config | PASS — final `~/.hermes/config.yaml` enabled list contains `auth_overlay` and `guinevere-persona`; stale `guinevere_persona` alias removed. |
| Plugin files | PASS — loader and metadata present under `~/.hermes/plugins/guinevere_persona`; source present in repo path. |
| Canonical source | PASS — remote `persona_plugin.py` includes canonical DB5 keys such as `guinevere:mood_variant` and `guinevere:reward_tier`. |
| Cron status | PASS — gateway running with 5 active cron jobs after restart. |
| Midnight isolation | PASS — `ritual_midnight` remains `Deliver: local`, schedule `0 0 * * *`. |
| Redis DB5 readback | PASS — non-secret values readable: `mood_variant=default`, `yandere_level=4`, `punishment_level=0`, `reward_tier=0`, `distress_state=0`, `safe_word=HARD STOP`, `dnr_list=[]`, key count `10`. |
| Recent logs | PASS — plugin init/registration logs present; no PersonaPlugin/Redis/cron/Discord `ERROR` or `CRITICAL` observed in the activation window. |

### 3.4 Known Non-Blocking Log Noise

The restart window shows existing warnings unrelated to PersonaPlugin activation:

- MCP server config warnings for `fetch`, `filesystem`, `git`, `terminal`, `web` missing `command` fields.
- Stale systemd unit warning: `TimeoutStopSec=90s` while drain timeout expects `>=210s`.
- Discord voice support warnings (`Opus`, `PyNaCl`, `davey`).
- Earlier 07:00 `ritual_morning` run failed with provider `Missing model`; this predates PersonaPlugin activation and is unrelated to OG-6.

---

## 4. Evidence Artifacts

| Artifact | Status |
|---|---|
| `docs/setup-evidence/phase-5/evidence-phase-5.md` | Final v2 evidence updated with OG-6 PASS after this deploy. |
| `docs/setup-evidence/phase-5/verification-5-4-v2.md` | Plugin/Redis bridge source verification PASS. |
| `docs/setup-evidence/phase-5/verification-5-5-v2.md` | Cron registration PASS. |
| `docs/setup-evidence/phase-5/verification-5-6-v2.md` | Ritual verification PASS. |
| `docs/setup-evidence/phase-5/auditor-gate-5-personaplugin-post-v2.md` | PersonaPlugin/Redis auditor PASS. |
| `docs/setup-evidence/phase-5/verification-5-deploy-v2.md` | This deploy evidence; PASS. |

---

## 5. Doc-Sync Impact

- `evidence-phase-5.md` was updated from OG-6 `DEFERRED` to OG-6 `PASS`.
- `PROGRESS.md` was updated to say controlled deploy/restart/smoke passed; commit/push remains pending until git-master workflow completes.
- No ADR risk change is needed here; ADR-035 Phase 5 risk was already updated to MEDIUM.

---

## 6. Boundary Compliance

| Boundary | Result |
|---|---|
| No secret exposure | PASS — no token/password/env values printed. Redis password was sourced remotely and not echoed. |
| No raw surveillance data | PASS. |
| Midnight never Discord | PASS — `ritual_midnight` remains `Deliver: local`. |
| Y4/Y5/Y6 boundaries | PASS — no yandere safety logic changed. |
| L6 boundary | PASS — no punishment safety logic changed. |
| HARD STOP / consent / distress | PASS — no safety gate weakening. |
| SOUL.md static constitution | PASS — not modified during deploy. |
| Dynamic state via PersonaPlugin/Redis DB5 | PASS — plugin active and DB5 keys readable. |
| No type suppression | PASS — deployment loader has no `# type: ignore`, `@ts-ignore`, `@ts-expect-error`, or `as any`. |
| No empty/bare catch | PASS — deployment loader has no bare `except:`. |

---

## 7. Rollback / Re-run Safety

Safe inspection commands:

```bash
hermes plugins list
hermes gateway status
hermes cron list
sed -n '630,637p' ~/.hermes/config.yaml
```

Rollback would require explicit per-action approval before execution because it changes live gateway/plugin state:

```bash
# REQUIRES EXPLICIT PER-ACTION APPROVAL — do not run automatically
hermes plugins disable guinevere-persona
hermes gateway restart
```

Config backup exists at `~/.hermes/config.yaml.bak.phase5-og6-*` for operator-approved restore if needed.

---

## 8. Design Decisions / Caveats

1. `sudo hermes gateway restart --system` was unavailable in the non-interactive session because sudo requires a TTY/password.
2. The gateway service runs as user `guinevere` with `Restart=always`; the approved restart was performed by sending `SIGTERM` to the current MainPID and allowing systemd to respawn it.
3. Two restarts occurred:
   - First restart after syncing files and config alias `guinevere_persona`.
   - Second restart after `hermes plugins enable guinevere-persona` revealed the actual registry name required for activation.
4. The plugin package directory remains `guinevere_persona`, while the registry/config plugin name is `guinevere-persona`.
5. `hermes hooks list` still shows the two shell hooks (`consent_gate.py`, `dnr_filter.py`); PersonaPlugin hooks are plugin lifecycle hooks and are evidenced by the gateway registration log, not shell hook listing.
6. The 07:00 morning ritual failed before this deploy due provider `Missing model`; cron scheduling and midnight isolation remain intact, but provider model config is a separate follow-up.

---

## 9. Auditor Gate

The five Phase 5 v2 auditor gates passed before OG-6, and this deploy evidence is parent-verified with runtime smoke checks. No new source-safety findings were introduced by OG-6; final git-master commit/push may proceed after the repository-level pre-commit review.

---

## 10. Security Scan

| Scan | Result |
|---|---|
| Secret literals in evidence | PASS — no passwords/tokens/API keys. |
| Redis password printed | PASS — not printed. |
| Discord token printed | PASS — not printed. |
| Destructive rollback executed | PASS — none. |
| Cron deletion executed | PASS — none. |
| Midnight Discord route introduced | PASS — no. |

---

## 11. Acceptance Criteria Mapping

| Criterion | Result |
|---|---|
| PersonaPlugin deployed to VPS | PASS |
| Hermes gateway restarted | PASS |
| PersonaPlugin activation evidenced | PASS — journal `guinevere_persona_plugin_registered`, `hook_count=4`. |
| Gateway active after restart | PASS — MainPID `4124751`, active. |
| Cron jobs preserved | PASS — 5 active jobs. |
| Midnight still local-only | PASS. |
| Redis DB5 canonical keys readable | PASS. |
| No relevant new ERROR/CRITICAL logs | PASS. |
| Evidence file written | PASS. |

---

## 12. Footer

| Version | Date | Author | Notes |
|---|---|---|---|
| v2.0 | 2026-06-06 | Sisyphus | OG-6 controlled deploy/restart/smoke evidence. |
| v2.1 | 2026-06-06 | Sisyphus | Recorded parent final-evidence/PROGRESS sync and typed loader cleanup. |

Phase 5 OG-6 live operation is PASS. Remaining closure: git-master commit/push workflow.
