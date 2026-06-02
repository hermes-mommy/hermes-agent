# Local Service/Run-Script Patterns — P2-017/018

**Date:** 2026-06-01
**Scope:** Extract reusable patterns from existing local files for P2-017 (discord bot service creation) and P2-018 (health check).
**Sources:** 10 local files examined — service units, run scripts, health checks, pyproject.toml, research reports, evidence files.

---

## 1. SOPS Token-Handling Patterns (Reusable)

### 1A. Wrapper Script Pattern — `run-discord-verify.sh` (Canonical)

**File:** `scripts/run-discord-verify.sh` — the most battle-tested, existing pattern.

```bash
set -euo pipefail
PROJECT_ROOT="/home/guinevere/code/guinevere"
SECRET_FILE="$PROJECT_ROOT/secrets/discord-secrets.yaml"
AGE_KEY_FILE="/home/guinevere/secrets/age-key.txt"
TEMP_SECRETS="$(mktemp /tmp/guinevere-discord-verify.XXXXXX.yaml)"

cleanup() {
  unset DISCORD_SECRETS_PATH || true
  shred -u "$TEMP_SECRETS" 2>/dev/null || rm -f "$TEMP_SECRETS"
}
trap cleanup EXIT

export SOPS_AGE_KEY_FILE="$AGE_KEY_FILE"
sops --decrypt "$SECRET_FILE" > "$TEMP_SECRETS"
chmod 600 "$TEMP_SECRETS"
export DISCORD_SECRETS_PATH="$TEMP_SECRETS"

cd "$PROJECT_ROOT"
"$PROJECT_ROOT/.venv/bin/python" "$VERIFY_SCRIPT"
```

**Key patterns:**
- `set -euo pipefail` — strict mode required
- `mktemp` + trap cleanup — no plaintext left behind
- `shred -u` — overwrite before delete (VPS only; `shred` is Linux)
- `chmod 600` — restrict read to owner
- `DISCORD_SECRETS_PATH` env var — Python reads via `guild_setup.get_token()`
- `.venv/bin/python` — direct path, no `source activate`

### 1B. `get_token()` Python Side

**File:** `src/discord/guild_setup.py:227`

```python
def get_token() -> str:
    secrets_path_raw = os.environ.get("DISCORD_SECRETS_PATH")
    token = read_scalar_yaml_value(secrets_path, "discord_bot_token")
    return token
```

Token path passed via env var, never hardcoded.

### 1C. Systemd ExecStartPre Decrypt — Two Approaches

**Approach 1: ExecStartPre to `/run/` tmpfs**
```ini
EnvironmentFile=-/run/guinevere-discord/.env
ExecStartPre=/usr/bin/mkdir -p /run/guinevere-discord
ExecStartPre=/usr/bin/sops --decrypt --input-type dotenv --output-type dotenv \
    /home/guinevere/code/guinevere/secrets/discord.env.sops \
    > /run/guinevere-discord/.env
ExecStartPre=/usr/bin/chmod 600 /run/guinevere-discord/.env
ExecStopPost=/bin/rm -rf /run/guinevere-discord
```

**Approach 2: `sops exec-env --same-process` (no disk write)**
```ini
ExecStart=/usr/bin/sops exec-env --same-process \
    /home/guinevere/code/guinevere/secrets/discord.env.sops \
    /home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
```

Caveat: `--same-process` required for correct SIGTERM delivery.

---

## 2. Systemd Unit Style (Existing Templates)

### 2A. `guinevere-core.service` (P1-018) — Production Reference

```ini
[Unit]
Description=Guinevere Core Daemon
After=docker.service network.target guinevere-9router.service
Requires=docker.service guinevere-9router.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/.../.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs

[Install]
WantedBy=multi-user.target
```

**Reusable for P2-017:** `Type=exec`, `User=guinevere`, `WorkingDirectory`, `PYTHONPATH`, `PYTHONDONTWRITEBYTECODE`, `Slice`, `RestartSec=10`, `MemoryHigh/Max`, `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, journal logging.

### 2B. Template Unit Pattern — `guinevere-backup@.service`

Security hardening block (reusable verbatim):
```ini
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
UMask=0077
```

---

## 3. Local vs VPS Caveats

| Aspect | VPS Production | Local (Windows) Dev |
|--------|---------------|---------------------|
| SOPS age key | `/home/guinevere/secrets/age-key.txt` | `$env:USERPROFILE\.config\sops\age\keys.txt` |
| shred command | `shred -u` available | Not available — use `Remove-Item` |
| tmpfs `/run/` | RAM-backed | Use temp dir |
| systemd | System units | Direct `python -m` or WSL |
| .venv path | `.venv/bin/python` | `venv\Scripts\python.exe` |
| mktemp | `/tmp/guinevere-*.XXXXXX.yaml` | Python tempfile or `[System.IO.Path]::GetTempFileName()` |

### Local Dev Command (Windows equivalent)
```powershell
$env:SOPS_AGE_KEY_FILE = "$env:USERPROFILE\.config\sops\age\keys.txt"
$env:DISCORD_SECRETS_PATH = "$env:TEMP\discord-secrets.yaml"
sops --decrypt secrets\discord-secrets.yaml > $env:DISCORD_SECRETS_PATH
.venv\Scripts\python.exe tmp\verify-p2-004-guild-name.py
Remove-Item $env:DISCORD_SECRETS_PATH
Remove-Item Env:DISCORD_SECRETS_PATH
```

---

## 4. Health Check Patterns (P2-018)

### 4A. `health-check-p1.sh` — Curl Endpoint + PASS/FAIL Counter

```bash
FAILS=0
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[PASS] check"
else
    echo "[FAIL] check"
    FAILS=$((FAILS + 1))
fi
if [ "$FAILS" -eq 0 ]; then exit 0; else exit 1; fi
```

### 4B. `preflight-check.sh` — `check_systemctl()` Helper

```bash
check_systemctl() {
    local svc="$1"; local name="$2"
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log_pass "$name"; ((PASS++))
    else
        state=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
        log_fail "$name (state: $state)"; ((FAIL++)); OVERALL_EXIT=1
    fi
}
```

### 4C. P2-018 Health Check Matrix

| Check | Method | Expected |
|-------|--------|----------|
| Service running | `systemctl status` | `active (running)` |
| Gateway connected | `journalctl | grep bot_ready` | Log line present |
| Commands synced | `journalctl | grep commands_synced` | Log line present |
| No crash loops | `journalctl | grep -c Error|Traceback` | 0 or low |
| Startup sent | `journalctl | grep startup_greeting_sent` | Log line present |
| Aizanta unaffected | `docker ps --filter name=aizanta` | Containers running |

---

## 5. pyproject.toml — No Entry Points

Hatchling build, **no `[project.scripts]` defined**. Bot runs via `python -m src.discord.bot`. No changes needed.

---

## 6. Summary — Pattern Sources

| Pattern | Source File(s) | P2-017 Use | P2-018 Use |
|---------|---------------|-----------|-----------|
| SOPS wrapper + trap cleanup | `run-discord-verify.sh`, `setup-guild.sh` | Service wrapper | Health script |
| `get_token()` via env var | `guild_setup.py:227` | bot.py startup | N/A |
| ExecStartPre to /run/ tmpfs | Research reports | Service unit | N/A |
| `sops exec-env --same-process` | Research reports | Alt service unit | N/A |
| Production unit template | `guinevere-core.service` | Full unit template | N/A |
| `check_systemctl()` helper | `preflight-check.sh` | N/A | Health check |
| curl health PASS/FAIL | `health-check-p1.sh` | N/A | Health script |
| No entry points | `pyproject.toml` | Use `python -m` | N/A |
| `Restart=on-failure` + limits | Research reports | Service unit | N/A |
