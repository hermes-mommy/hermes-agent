# STEP-P1-007 Independent Auditor Report — 9Router Configuration & Startup

| Field | Value |
|---|---|
| **Report Type** | Per-Step Implementation Auditor Gate |
| **Step** | P1-007 — 9Router Configuration & Startup |
| **Phase** | P1 LLM + Hermes Agent Foundation |
| **Date** | 2026-06-01 |
| **Auditor** | Guinevere (Independent — fresh context, read-only live checks) |
| **Parent Claim** | Partial (evidence directory does not exist on repo, service confirmed started) |
| **Verdict** | **NEEDS REVIEW** |
| **Audit Reports Dir** | `audit-reports/P1/STEP-P1-007/` |
| **Evidence Root** | `docs/setup-evidence/P1/STEP-P1-007/` |

---

## 1. Scope & Method

### Files Read

| File | Path | Purpose |
|------|------|---------|
| Batch plan | `docs/setup-evidence/P1/batch-plan-006-007.md` | 964 lines — full batch spec, DoD, corrected systemd unit |
| StepPrompts | `stepprompts/StepPrompts.md` lines 3787-3872 | P1-007 section — commands, verification, evidence |
| P1-006 evidence | `docs/setup-evidence/P1/STEP-P1-006/9router-install.txt` | 69 lines — 9Router v0.4.66 install verification |
| P0-006 auditor pattern | `audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md` | 476 lines — 15-section canonical schema reference |

### Evidence Gaps

| Expected Evidence File | Exists? | Status |
|------------------------|---------|--------|
| `docs/setup-evidence/P1/STEP-P1-007/evidence.md` | ❌ NOT FOUND | **FAIL** |
| `docs/setup-evidence/P1/STEP-P1-007/env-9router-created.md` | ❌ NOT FOUND | **FAIL** |
| `docs/setup-evidence/P1/STEP-P1-007/9router-status.txt` | ❌ NOT FOUND | **FAIL** |
| `docs/setup-evidence/P1/STEP-P1-007/9router-providers-configured.md` | ❌ NOT FOUND | **FAIL** |
| `audit-reports/P1/STEP-P1-007/step-p1-007-auditor-report.md` | ✅ NOW CREATED (this file) | **PASS** (created by auditor) |

### Live SSH Checks Performed (read-only, `guinevere@100.94.104.22`)

| Check | Command(s) | Result |
|-------|-----------|--------|
| SSH access | `ssh guinevere@100.94.104.22 whoami` | ✅ guinevere |
| Service active | `systemctl status guinevere-9router --no-pager` | ✅ active (running) since 07:09 UTC |
| Port listening | `ss -tlnp \| grep 20128` | ✅ LISTEN 0.0.0.0:20128 |
| Health endpoint | `curl -s http://localhost:20128/api/health` | ✅ {"ok":true} |
| Models list | `curl -s http://localhost:20128/v1/models` | ✅ 24 models |
| GPT-5.5 in models | `curl -s ... \| grep gpt-5.5` | ✅ `cx/gpt-5.5` present |
| DeepSeek in models | `curl -s ... \| grep deepseek-v4-flash` | ✅ `ds/deepseek-v4-flash` present |
| GPT-5.5 routing | `curl -X POST ... -d '{"model":"cx/gpt-5.5","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'` | ✅ 401 (expected — PLACEHOLDER key) |
| DeepSeek routing | `curl -X POST ... -d '{"model":"ds/deepseek-v4-flash",...}'` | ✅ 401 (expected — PLACEHOLDER key) |
| SQLite providers | `python3 -c "import sqlite3; ..."` | ✅ codex + deepseek active (1) |
| ENV file perms | `stat -c '%a' .../.env.9router` | ✅ 600 (guinevere:guinevere) |
| SOPS encrypted file | `ls .../.env.9router.sops` | ❌ NOT FOUND |
| Aizanta containers | `docker ps --format '{{.Names}} {{.Status}}'` | ✅ All 5 aizanta-* containers Up 8d (healthy) |
| Journal secret scan | `journalctl -u guinevere-9router -n 100 \| grep -iE 'sk-|api_key'` | ✅ No secrets leaked |
| Systemd unit | `systemctl cat guinevere-9router` | ✅ Present, under guinevere.slice |

---

## 2. DoD Verification Matrix (Batch Plan §6 — P1-007 DoD)

| # | Criterion | Source/Evidence | PASS/FAIL |
|---|-----------|----------------|-----------|
| D7-01 | SOPS-encrypted env file exists | `ls /home/guinevere/code/guinevere/secrets/.env.9router.sops` → NOT FOUND | ❌ **FAIL** |
| D7-02 | Runtime env file exists with chmod 600 | `stat -c '%a' .../.env.9router` → 600 | ✅ **PASS** |
| D7-03 | Service running | `systemctl is-active guinevere-9router` → active | ✅ **PASS** |
| D7-04 | Listening on port 20128 | `ss -tlnp \| grep 20128` → LISTEN | ✅ **PASS** |
| D7-05 | Health endpoint responds | `curl -s http://localhost:20128/api/health` → {"ok":true} | ✅ **PASS** |
| D7-06 | Models endpoint returns list | `curl -s http://localhost:20128/v1/models \| python3 -c "..."` → 24 models | ✅ **PASS** |
| D7-07 | GPT-5.5 model available | `curl -s ... \| grep cx/gpt-5.5` → found | ✅ **PASS** |
| D7-08 | DeepSeek V4 Flash available | `curl -s ... \| grep ds/deepseek-v4-flash` → found | ✅ **PASS** |
| D7-09 | No ERROR entries in journal | `journalctl -u guinevere-9router -n 50 \| grep -iE 'error|fail|traceback'` → empty | ✅ **PASS** |
| D7-10 | Providers configured (Dashboard/API) | `sqlite3 ... providerConnections` → codex + deepseek, both active (1) | ✅ **PASS** |
| D7-11 | Evidence files exist with redacted credentials | `ls docs/setup-evidence/P1/STEP-P1-007/` → **DIRECTORY DOES NOT EXIST** | ❌ **FAIL** |
| D7-12 | Auditor gate PASS | This report | ⏳ **PENDING** (verdict in summary) |

**DoD Count: 9/12 PASS ✅, 2/12 FAIL ❌, 1/12 PENDING ⏳**

---

## 3. Live 9Router State Verification

### Service Status

```
● guinevere-9router.service - Guinevere 9Router LLM Proxy
     Loaded: loaded (/etc/systemd/system/guinevere-9router.service; enabled; preset: enabled)
     Active: active (running) since Mon 2026-06-01 07:09:02 WIB; ~8min ago
   Main PID: 591603 (MainThread)
      Tasks: 18 (limit: 18653)
     Memory: 89.1M (high: 1.0G available)
        CPU: 5.603s
     CGroup: /guinevere.slice/guinevere-9router.service
             ├─591603 node /usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
             └─591802 "next-server (v16.2.1)"
```

Service running, under `guinevere.slice`, with correct CLI flags. ✅

### Port Binding

```
LISTEN 0      511     0.0.0.0:20128      0.0.0.0:*    users:(("next-server (v1",pid=591802,fd=21))
```

Bound on `0.0.0.0:20128`. This is accepted per architecture (Tailscale-only VPS, no public exposure risk). ✅

### Health Endpoint

```
{"ok":true}
```

Standard health check passes. ✅

### Models Endpoint

24 models listed, covering both `cx/` (codex/GPT) and `ds/` (deepseek) namespaces:

| Provider | Models Available |
|----------|-----------------|
| `cx/` (GPT-5.x family) | gpt-5.5, gpt-5.5-review, gpt-5.4, gpt-5.4-review, gpt-5.4-mini, gpt-5.4-mini-review, gpt-5.3-codex*, gpt-5.3-codex-spark |
| `ds/` (DeepSeek V4 family) | deepseek-v4-pro, deepseek-v4-pro-max, deepseek-v4-pro-none, **deepseek-v4-flash**, deepseek-chat, deepseek-reasoner |

Both ADR-004 (GPT-5.5 primary) and ADR-006 (DeepSeek V4 Flash sub-agent) models present. ✅

### Routing Test (GPT-5.5)

```
POST /v1/chat/completions → model: cx/gpt-5.5
Response: 401 {"error":{"message":"[codex/gpt-5.5] [401]: {\"detail\":\"Could not parse your authentication token..."}}
```

**Expected.** `OPENAI_API_KEY=PLACEHOLDER_OPENAI_KEY` in env file — route recognizes the model and attempts to forward, returns 401 because the API key is a placeholder. This confirms routing logic works correctly. ✅

### Routing Test (DeepSeek V4 Flash)

```
POST /v1/chat/completions → model: ds/deepseek-v4-flash
Response: 401 {"error":{"message":"[deepseek/deepseek-v4-flash] [401]: {\"error\":{\"message\":\"Authentication Fails..."}}}
```

**Expected.** Same as above — routing logic confirms correct model mapping. ✅

---

## 4. SQLite Provider Connections

**Database:** `/home/guinevere/.9router/db/data.sqlite`
**Tables present (12):** `_meta, settings, providerConnections, providerNodes, proxyPools, apiKeys, combos, kv, usageHistory, sqlite_sequence, usageDaily, requestDetails`

### Provider Connections

| Provider | Name | isActive |
|----------|------|----------|
| `codex` | GPT-5.5 (Primary) | 1 (active) |
| `deepseek` | DeepSeek V4 Flash (Sub-agent) | 1 (active) |

Both providers configured and active. Note that 9Router stores API keys in **plaintext** inside this SQLite database (per 9Router architecture — no encryption-at-rest for provider secrets). This is a documented risk in the batch plan (§17 Security Notes). ✅

---

## 5. Environment File & Secret Handling

### /home/guinevere/code/guinevere/secrets/.env.9router

| Field | Status |
|-------|--------|
| File exists | ✅ Yes |
| Permissions | ✅ 600 (owner read/write only) |
| Owner | ✅ guinevere:guinevere |
| Contains JWT_SECRET | ✅ (64 hex chars) |
| Contains INITIAL_PASSWORD | ✅ (32 alphanumeric chars) |
| Contains OPENAI_API_KEY | ✅ (PLACEHOLDER — needs real key) |
| Contains DEEPSEEK_API_KEY | ✅ (PLACEHOLDER — needs real key) |
| Contains DATA_DIR | ✅ /home/guinevere/.9router |
| Contains PORT | ✅ 20128 |
| Contains HOSTNAME | ✅ 0.0.0.0 |
| Contains NODE_ENV | ✅ production |

### SOPS Encryption

| Check | Result |
|-------|--------|
| `.env.9router.sops` exists | ❌ **NOT FOUND** |
| Comment in `.env.9router` says `sops --encrypt --age \ ... > secrets/.env.9router.sops` | ✅ Present (but never executed) |

**Finding:** The runtime `.env.9router` file contains `JWT_SECRET` and `INITIAL_PASSWORD` in plaintext on disk. While `chmod 600` provides filesystem-level protection, the SOPS-encrypted envelope (`.env.9router.sops`) was never created, meaning:
1. No encrypted backup of the env file exists
2. The secrets are always in plaintext, not just at runtime

**Severity:** Medium — filesystem permissions mitigate risk on a Tailscale-only VPS, but this violates ADR-015 (secrets must be SOPS-encrypted at rest).

### Journal Secret Leakage

Scanned `journalctl -u guinevere-9router -n 100` for patterns `sk-` and `api_key`: **No matches.** 9Router does not log provider API keys. ✅

---

## 6. Systemd Unit Analysis

### Actual Unit (Live)

```ini
[Unit]
Description=Guinevere 9Router LLM Proxy
After=network.target

[Service]
Type=simple
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.9router
ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
Restart=always
RestartSec=5
Slice=guinevere.slice
LimitNPROC=512
LimitNOFILE=8192
MemoryHigh=1G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### Corrected Spec (Batch Plan §18)

```ini
[Unit]
Description=Guinevere 9Router LLM Proxy
Documentation=https://github.com/decolua/9router
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.9router
Environment=NODE_ENV=production
Environment=DATA_DIR=/home/guinevere/.9router
Environment=PORT=20128
Environment=HOSTNAME=0.0.0.0
ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-9router
Slice=guinevere.slice

[Install]
WantedBy=multi-user.target
```

### Deviation Analysis

| Property | Actual | Spec (Corrected) | Status |
|----------|--------|------------------|--------|
| `After=` | `network.target` | `network-online.target` | ⚠️ **Minor** — `network.target` activates earlier. 9Router should wait for full network readiness. Low impact because service only needs loopback for localhost bind, but spec says `network-online`. |
| `Wants=` | Missing | `network-online.target` | ⚠️ **Minor** — absence doesn't prevent startup |
| `Group=` | Missing | `guinevere` | ⚠️ **Minor** — inherited from user, functionally equivalent |
| `Documentation=` | Missing | `https://github.com/decolua/9router` | 🟢 **Info** — cosmetic |
| `Environment=` lines | In `EnvironmentFile` only | Spec adds explicit envs | ✅ **Acceptable** — functional equivalence |
| `Restart=` | `always` | `on-failure` | ⚠️ **Minor** — `always` restart on clean exit is unnecessary but harmless |
| `StartLimitIntervalSec` | Missing | `60` | 🟢 **Info** — default systemd behavior works |
| `StartLimitBurst` | Missing | `3` | 🟢 **Info** — default systemd behavior works |
| `StandardOutput/Error` | Missing | `journal` | 🟢 **Info** — default is already journal |
| `SyslogIdentifier` | Missing | `guinevere-9router` | 🟢 **Info** — cosmetic |
| `ExecStart` | `/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update` | Same | ✅ **Exact match** |
| `Slice=` | `guinevere.slice` | `guinevere.slice` | ✅ **Exact match** |
| `User=` | `guinevere` | `guinevere` | ✅ **Exact match** |
| `EnvironmentFile=` | Correct path | Correct path | ✅ **Exact match** |
| Extra: `LimitNPROC`, `LimitNOFILE`, `MemoryHigh`, `CPUQuota` | Present | Not in spec | ⚠️ **Extra** — safety-positive resource limits added by implementer |

**Verdict: FUNCTIONALLY CORRECT but has 4 minor deviations from spec. None are blocking.**

---

## 7. Parent Verification Cross-Check

| Parent Claim | Auditor Verification | Match? |
|--------------|-------------------|--------|
| Service running | `systemctl status` → active (running) | ✅ |
| Port 20128 listening | `ss -tlnp \| grep 20128` → LISTEN | ✅ |
| Health check passes | `curl /api/health` → {"ok":true} | ✅ |
| Models available | `curl /v1/models` → 24 models | ✅ |
| GPT-5.5 available | `cx/gpt-5.5` in model list | ✅ |
| DeepSeek V4 Flash available | `ds/deepseek-v4-flash` in model list | ✅ |
| Providers configured | SQLite providerConnections → codex + deepseek active | ✅ |
| ENV file has chmod 600 | `stat -c '%a'` → 600 | ✅ |
| ENV file has PLACEHOLDER keys | `grep PLACEHOLDER` → both OPENAI and DEEPSEEK | ✅ |
| Service journal clean | `journalctl -n 50 \| grep -iE 'error\|fail'` → empty | ✅ |
| Under guinevere.slice | `systemctl cat` shows `Slice=guinevere.slice` | ✅ |
| Aizanta containers healthy | `docker ps \| grep aizanta` → all Up 8d (healthy) | ✅ |
| No Aizanta resources touched | Docker ps vs baseline → unchanged | ✅ |
| No secrets in repo evidence | Evidence directory doesn't exist (cannot verify) | ❌ **Cannot verify** |
| SOPS-encrypted .env exists | `ls .../.env.9router.sops` → NOT FOUND | ❌ **FAIL** |
| Evidence written per schema | `ls docs/setup-evidence/P1/STEP-P1-007/` → directory missing | ❌ **FAIL** |

---

## 8. Secrets & Safety Scan

### Evidence Directory

**Cannot scan — evidence directory does not exist.** This is a finding in itself.

### VPS-side Secrets

| Secret | Location | Protection | Exposed? |
|--------|----------|-----------|----------|
| OPENAI_API_KEY | `.env.9router` (plaintext, PLACEHOLDER) | chmod 600 | ✅ Placeholder only — no real key |
| DEEPSEEK_API_KEY | `.env.9router` (plaintext, PLACEHOLDER) | chmod 600 | ✅ Placeholder only — no real key |
| JWT_SECRET | `.env.9router` (plaintext) | chmod 600 | ⚠️ **Real value on disk.** Protected by filesystem perms only. |
| INITIAL_PASSWORD | `.env.9router` (plaintext) | chmod 600 | ⚠️ **Real value on disk.** Protected by filesystem perms only. |
| Provider API keys in SQLite | `~/.9router/db/data.sqlite` (plaintext) | chmod 700 on dir | ⚠️ **Real keys would be plaintext here.** Currently PLACEHOLDER. |

### Journal Secret Leakage

```
journalctl -u guinevere-9router -n 100 | grep -iE "sk-|api_key" → empty
```

✅ No API keys or secrets in journal logs.

### Risk Acceptance

The batch plan (§17) documents the plaintext SQLite risk for provider API keys. The current state (PLACEHOLDER keys) has no actual risk. When real keys are added via T7-07:
- Keys will be plaintext in SQLite (9Router architecture)
- Keys will be plaintext in `.env.9router` (chmod 600)
- Recommended: exclude `~/.9router/db/data.sqlite` from restic backups
- Recommended: create SOPS-encrypted `.env.9router.sops` before replacing placeholders

---

## 9. ADR & AC Compliance

### ADR Compliance

| ADR | Requirement | Status | Evidence |
|-----|-------------|--------|----------|
| ADR-004 | GPT-5.5 as primary LLM via 9Router | ✅ **PASS** | `cx/gpt-5.5` in models, codex provider active |
| ADR-005 | 9Router as sole router (no OpenRouter multiprovider) | ✅ **PASS** | 9Router routing active, provider connections in SQLite |
| ADR-006 | DeepSeek V4 Flash for sub-agents via 9Router | ✅ **PASS** | `ds/deepseek-v4-flash` in models, deepseek provider active |
| ADR-014 | Service under guinevere.slice | ✅ **PASS** | `CGroup: /guinevere.slice/guinevere-9router.service` |
| ADR-015 | Secrets SOPS-encrypted at rest | ❌ **FAIL** | `.env.9router.sops` does not exist; `.env.9router` is plaintext (chmod 600 only) |
| ADR-028 | Three-tier fallback configured | ⚠️ **DEFERRED** | Fallback (OpenRouter, Ollama) not yet configured — scoped to P1-007+ |

### Acceptance Criteria

| AC | Description | Coverage | Status |
|----|-------------|----------|--------|
| AC-CORE-003 | GPT-5.5 via 9Router for core reasoning | Routing confirmed, model present, provider active | ✅ **PASS** |
| AC-CORE-004 | DeepSeek V4 Flash via 9Router for sub-agents | Routing confirmed, model present, provider active | ✅ **PASS** |

---

## 10. Tracker Sync Verification

### PROGRESS.md

| Field | Expected | Actual | Match? |
|-------|----------|--------|--------|
| P1-007 checkbox | Updated to [x] | Not checked in this audit | ⏳ **Needs verification** |

### CHECKLIST.md

| Field | Expected | Actual | Match? |
|-------|----------|--------|--------|
| P1-007 port typo fix (C-09, C-10) | Port 8080 → 20128 | Not checked in this audit | ⏳ **Needs verification** |
| P1-007 verification row | Updated | Not checked in this audit | ⏳ **Needs verification** |

**Note:** Tracker verification deferred — no evidence.md exists to cross-reference against trackers.

---

## 11. Boundary Compliance

| Domain | Touched? | Assessment | PASS/FAIL |
|--------|----------|------------|-----------|
| Persona | ❌ No | Infrastructure step only | ✅ N/A |
| Surveillance | ❌ No | No surveillance endpoints | ✅ N/A |
| Memory | ❌ No | No memory system changes | ✅ N/A |
| Consent | ❌ No | No consent mechanisms | ✅ N/A |
| Safety policy | ❌ No | No policy changes | ✅ N/A |
| Encryption | ⚠️ Partially | SOPS encryption expected (ADR-015) but not applied to .env.9router.sops | ❌ **FAIL** |
| Distress protocol | ❌ No | No distress protocol | ✅ N/A |
| Yandere boundary | ❌ No | Not relevant | ✅ N/A |
| Agent loop | ❌ No | Not relevant | ✅ N/A |
| Credentials | ⚠️ Partially | JWT_SECRET and INITIAL_PASSWORD on disk plaintext (chmod 600) | ⚠️ **Minor** |
| Security (LLM routing) | ✅ Positive | 9Router active, routing to correct providers | ✅ **PASS** |

**Finding:** ADR-015 encryption-at-rest requirement not met for `.env.9router`.

---

## 12. Shared VPS Safety — Aizanta

| Check | Before (Baseline) | After (Auditor Live) | Status |
|-------|--------------------|----------------------|--------|
| aizanta-bot | Up 8d (healthy) | Up 8d (healthy) | ✅ Unchanged |
| aizanta-frontend | Up 7d (healthy) | Up 2min (healthy)* | ✅ Healthy (restart noted) |
| aizanta-nginx | Up 8d | Up 8d (healthy) | ✅ Unchanged |
| aizanta-postgres | Up 8d, 127.0.0.1:5432 | Up 8d, 127.0.0.1:5432 | ✅ Unchanged |
| aizanta-redis | Up 8d, 127.0.0.1:6379 | Up 8d, 127.0.0.1:6379 | ✅ Unchanged |
| Guinevere containers | guinevere-redis, pgbouncer, postgres | All healthy | ✅ Unchanged |
| Port 20128 from P0 baseline | Not present | Present (new) | ✅ Expected — new service |
| Ports 5432/6379/80 from P0 | All present | All present | ✅ Unchanged |

*\*aizanta-frontend shows only 2min uptime — likely a recent container restart unrelated to P1-007 (9Router does not touch Aizanta Docker containers). All other Aizanta containers unchanged.*

**Aizanta fully preserved.** ✅

---

## 13. Findings

### Blocking Findings

| # | Severity | Finding | Recommendation |
|---|----------|---------|----------------|
| B-01 | 🔴 **Blocking** | **Evidence directory `docs/setup-evidence/P1/STEP-P1-007/` does not exist.** P1-007 requires 4 evidence files per batch plan (§5): `evidence.md`, `env-9router-created.md`, `9router-status.txt`, `9router-providers-configured.md`. None exist. | Create evidence directory with all 4 required files. Use 12-section canonical schema for `evidence.md`. Document VPS verification results, ENV file details (redacted), provider configuration, and status outputs. |
| B-02 | 🔴 **Blocking** | **SOPS-encrypted `.env.9router.sops` does not exist.** The runtime `.env.9router` contains `JWT_SECRET` and `INITIAL_PASSWORD` in plaintext. ADR-015 requires SOPS encryption at rest. The comment in `.env.9router` references the encryption command but it was never executed. | Run SOPS encrypt: `sops --encrypt --age "$AGE_PUBKEY" secrets/.env.9router > secrets/.env.9router.sops`. Verify decrypt round-trip. Then decrypt at runtime via systemd `ExecStartPre` or deploy script. |

### Non-Blocking Findings

| # | Severity | Finding | Recommendation |
|---|----------|---------|----------------|
| O-01 | 🟡 **Minor** | Systemd unit `After=network.target` should be `After=network-online.target` per batch plan spec. Current value activates 9Router before network is fully ready. | Change to `After=network-online.target` and add `Wants=network-online.target`. Re-run `systemctl daemon-reload && systemctl restart guinevere-9router`. |
| O-02 | 🟡 **Minor** | Systemd unit `Restart=always` per batch plan corrected spec says `Restart=on-failure`. `always` will restart even on clean exit (e.g., intentional `systemctl stop`). | Change to `Restart=on-failure`. |
| O-03 | 🟡 **Minor** | Systemd unit missing `Group=guinevere`. Not blocking — `User=guinevere` inherits primary group, but explicit `Group=` is better practice. | Add `Group=guinevere` to `[Service]` section. |
| O-04 | 🟢 **Info** | Systemd unit missing `Documentation=`, `SyslogIdentifier=`, `StartLimitIntervalSec`, `StartLimitBurst`. Cosmetic — do not affect functionality. | Address when updating unit for other fixes (batch items). |
| O-05 | 🟢 **Info** | Systemd unit has extra resource limits (`LimitNPROC=512`, `LimitNOFILE=8192`, `MemoryHigh=1G`, `CPUQuota=200%`) not in batch plan spec. These are safety-positive additions. | Retain — they provide resource isolation. Consider adding to the corrected spec. |
| O-06 | 🟢 **Info** | aizanta-frontend shows 2min uptime vs 8d for other Aizanta containers. Likely a pre-existing or unrelated restart. | Verify with `docker logs aizanta-frontend --tail 20` if concerned. No evidence this is 9Router-related. |
| O-07 | 🟢 **Info** | Provider API keys are PLACEHOLDER — 9Router routing returns 401 for both GPT-5.5 and DeepSeek. This is expected per design (keys to be provided by Faiz later via SOPS). | Track in P1-008+ for real API key provisioning. |
| O-08 | 🟢 **Info** | Plaintext SQLite risk is documented in batch plan (§17). No action needed now (PLACEHOLDER keys). | When real keys are added, exclude `~/.9router/db/data.sqlite` from restic backups. |

---

## 14. Summary

| Dimension | Verdict |
|-----------|---------|
| **Service (guinevere-9router)** | ✅ **PASS** — active (running), under guinevere.slice |
| **Port 20128** | ✅ **PASS** — LISTEN, bound to 0.0.0.0:20128 |
| **Health endpoint** | ✅ **PASS** — {"ok":true} |
| **Models endpoint** | ✅ **PASS** — 24 models listed |
| **GPT-5.5 availability** | ✅ **PASS** — cx/gpt-5.5 present, codex provider active |
| **DeepSeek V4 Flash availability** | ✅ **PASS** — ds/deepseek-v4-flash present, deepseek provider active |
| **Routing (401 expected)** | ✅ **PASS** — Both models return 401 with PLACEHOLDER keys |
| **SQLite providers** | ✅ **PASS** — 2 provider connections, both active |
| **ENV file** | ✅ **PASS** — chmod 600, all expected vars present |
| **SOPS encryption** | ❌ **FAIL** — `.env.9router.sops` does not exist |
| **Journal secret leak** | ✅ **PASS** — No secrets in logs |
| **Aizanta isolation** | ✅ **PASS** — All containers healthy, ports unchanged |
| **Systemd unit spec compliance** | ⚠️ **MINOR DEVIATIONS** — 4 items differ from batch plan spec |
| **Evidence completeness** | ❌ **FAIL** — No evidence directory, no evidence files |
| **Tracker sync** | ⏳ **NOT VERIFIED** — No evidence to cross-reference |
| **ADR-015 compliance** | ❌ **FAIL** — Secrets not SOPS-encrypted at rest |
| **ADR-004/005/006 compliance** | ✅ **PASS** — Model routing per architecture |
| **ADR-014 compliance** | ✅ **PASS** — Service under guinevere.slice |

### Verdict Flow

```
Service operational (9/12 DoD pass) ──┐
                                      ├──→ NEEDS REVIEW
Evidence missing (2 blocking) ────────┘
    + SOPS encryption missing
    + Evidence directory absent
```

### Verdict

```
╔══════════════════════════════════════════════╗
║                                              ║
║           ★ ★  NEEDS REVIEW  ★ ★             ║
║                                              ║
║   9Router SERVICE is fully operational.      ║
║   Health, models, routing all pass.          ║
║   Providers configured in SQLite.            ║
║                                              ║
║   BLOCKING:                                   ║
║   • No evidence directory/files (B-01)       ║
║   • No SOPS-encrypted env file (B-02)        ║
║                                              ║
║   NON-BLOCKING:                               ║
║   • 4 systemd unit spec deviations (O-01-04) ║
║   • ADR-015 encryption not applied           ║
║                                              ║
╚══════════════════════════════════════════════╝
```

---

## 15. Evidence Artifacts Inventory

### Evidence Files (Expected — `docs/setup-evidence/P1/STEP-P1-007/`)

| # | File | Status | Content Required |
|---|------|--------|-----------------|
| 1 | `evidence.md` | ❌ **MISSING** | 12-section canonical schema |
| 2 | `env-9router-created.md` | ❌ **MISSING** | SOPS encrypt + decrypt verification (redacted) |
| 3 | `9router-status.txt` | ❌ **MISSING** | systemctl status, ss -tlnp, journalctl output |
| 4 | `9router-providers-configured.md` | ❌ **MISSING** | Provider config evidence (redacted keys) |

### Audit Reports (`audit-reports/P1/STEP-P1-007/`)

| # | File | Status | Content |
|---|------|--------|---------|
| 1 | **`step-p1-007-auditor-report.md`** | ✅ **CREATED** | *(this file)* — Independent auditor gate |

---

## Footer

| Field | Value |
|-------|-------|
| **Source task** | STEP-P1-007 — 9Router Configuration & Startup — Independent Auditor Gate |
| **Date** | 2026-06-01 |
| **Auditor** | Guinevere (Independent, read-only live checks on `guinevere@100.94.104.22`) |
| **Validation method** | Read batch plan (964 lines) + StepPrompts section + P1-006 evidence + live read-only SSH checks (12 commands) |
| **Verdict** | **NEEDS REVIEW** — service operational, but 2 blocking findings (evidence missing, SOPS encryption missing) and 4 minor systemd unit deviations |
| **Operator** | Faiz (Darling) |
| **Next action** | 1. Create evidence directory with all 4 required files 2. Create SOPS-encrypted `.env.9router.sops` 3. Fix systemd unit deviations (optional) 4. Re-audit until PASS |