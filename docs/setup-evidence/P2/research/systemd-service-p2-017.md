# Systemd Service Design — Python discord.py Bot

**Task**: P2-017 — Research systemd service unit fields for a Python discord.py bot.
**Date**: 2026-06-01
**Scope**: Non-root user, WorkingDirectory, ExecStart, Environment/EnvironmentFile, Restart policy, logs/journal, graceful shutdown, SOPS secret handling, local-development caveats.

---

## 1. Production System Service Unit (Template)

```ini
# /etc/systemd/system/guinevere-bot.service
[Unit]
Description=Guinevere Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple

# ── Non-Root User ──────────────────────────────────
User=guinevere
Group=guinevere

# ── Working Directory ──────────────────────────────
WorkingDirectory=/opt/guinevere

# ── ExecStart (venv absolute path) ─────────────────
ExecStart=/opt/guinevere/.venv/bin/python -m bot

# ── Secrets via EnvironmentFile ────────────────────
EnvironmentFile=/run/guinevere/secrets.env
Environment=PYTHONUNBUFFERED=1

# ── SOPS Decrypt Before Start ──────────────────────
ExecStartPre=/usr/bin/mkdir -p /run/guinevere
ExecStartPre=/usr/bin/sops --decrypt \
  --input-type dotenv --output-type dotenv \
  /opt/guinevere/secrets/prod.env.sops \
  > /run/guinevere/secrets.env
ExecStartPre=/usr/bin/chmod 600 /run/guinevere/secrets.env

# ── Restart Policy ─────────────────────────────────
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=300
StartLimitBurst=5

# ── Graceful Shutdown ──────────────────────────────
KillSignal=SIGTERM
TimeoutStopSec=30
ExecStopPost=/usr/bin/rm -f /run/guinevere/secrets.env

# ── Logging ────────────────────────────────────────
StandardOutput=journal
StandardError=journal

# ── Security Hardening ─────────────────────────────
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/guinevere /var/lib/guinevere

[Install]
WantedBy=multi-user.target
```

---

## 2. Key Field Design Decisions

### 2.1 Non-Root User (`User=` / `Group=`)

- Create a dedicated system user with no login shell:
  ```bash
  sudo useradd -r -s /bin/false -m -d /opt/guinevere guinevere
  ```
- The `User=` directive drops privileges before `ExecStart`; the process **cannot** escalate back to root.
- **Alternative**: `DynamicUser=yes` creates an ephemeral user at runtime (stateless services only — not recommended for bots needing persistent file ownership).

### 2.2 WorkingDirectory

- **Must be an absolute path**. systemd does not expand `~` or relative paths.
- All relative paths in the bot code (e.g., config file loading, SQLite DB paths) resolve from here.
- Use `ReadWritePaths=` alongside to ensure the service can write to its data directory under `ProtectSystem=strict`.

### 2.3 ExecStart — Virtual Environment

- **Never use `source activate`** — systemd does not understand shell activation.
- Point directly at the venv Python binary:
  ```ini
  ExecStart=/opt/guinevare/.venv/bin/python -m bot
  ```
- This works because the venv's Python binary hardcodes its `sys.path` to include venv site-packages.
- **Test manually first**:
  ```bash
  sudo -u guinevare /opt/guinevare/.venv/bin/python -m bot
  ```

### 2.4 Environment & EnvironmentFile

| Directive | Use Case |
|---|---|
| `Environment=KEY=val` | Non-secret tuning vars (e.g. `PYTHONUNBUFFERED=1`) |
| `EnvironmentFile=/path` | Secrets & config — one `KEY=VALUE` per line |
| `EnvironmentFile=-/optional/path` | Leading `-` means silently skip if missing (useful for dev overrides) |

- **Never hardcode secrets in unit files** — unit files are world-readable (`644`).
- Environment files should be `chmod 600` root-owned, loaded via `EnvironmentFile=`.

### 2.5 Restart Policy

| Value | Behavior | When to Use |
|---|---|---|
| `on-failure` | Restart only on non-zero exit / signal | General production — clean `systemctl stop` won't restart |
| `always` | Restart regardless of exit code | Critical services that must never be down |
| `unless-stopped` | Like `always` but respects manual `systemctl stop` | Best balance for production bots |

- **`RestartSec=5`** — Wait 5s between attempts to prevent crash loops.
- **`StartLimitIntervalSec=300` + `StartLimitBurst=5`** — If the bot crashes >5 times in 5 minutes, systemd stops trying and marks the service as `failed`. This prevents infinite restart loops on persistent errors.

### 2.6 Logs & Journal

- `StandardOutput=journal` and `StandardError=journal` route all stdout/stderr to journald.
- View live logs:
  ```bash
  sudo journalctl -u guinevere-bot -f
  ```
- View logs since last boot:
  ```bash
  sudo journalctl -u guinevere-bot --since today
  ```
- **Log rotation**: journald rotates automatically. Limit disk usage:
  ```ini
  # /etc/systemd/journald.conf
  SystemMaxUse=500M
  MaxRetentionSec=7day
  ```
- For structured logging, the `systemd.journal` Python module (`python-systemd`) can write directly with log levels, but stdout capture is sufficient.

### 2.7 Graceful Shutdown

**Critical context for discord.py** — The library's `Client.run()` already registers signal handlers internally ([source](https://github.com/Rapptz/discord.py/blob/v2.3.2/discord/client.py)):

```python
# discord/client.py — Client.run()
loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
```

This means:
- `SIGTERM` → `loop.stop()` → `bot.close()` is called in the runner cleanup.
- No custom signal handler is **required** for basic shutdown.
- However, pending asyncio tasks may trigger `"Task was destroyed but it is pending!"`. For custom cleanup (DB flush, file writes), override `bot.close()`:

```python
class GuinevereBot(commands.Bot):
    async def close(self):
        # custom cleanup here
        await self.flush_state()
        await super().close()  # calls http.close(), ws.close(1000)
```

**Alternative approach**: Set `KillSignal=SIGINT` in the unit to trigger Python's `KeyboardInterrupt` path. This is simpler but less precise than the SIGTERM handler approach.

**Voice client caveat**: During shutdown, `voice_client.disconnect()` can hang for ~10s. Use `force=True`:
```python
await voice_client.disconnect(force=True)
```

---

## 3. SOPS + Age Secret Handling

### 3.1 Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Git Repo     │     │  VPS Filesystem  │     │  /run tmpfs    │
│              │     │                  │     │  (RAM, ephemeral)│
│ secrets/     │     │  /opt/guinevare/ │     │                │
│  prod.env    │────>│   secrets/       │────>│  secrets.env   │
│   .sops      │     │   prod.env.sops  │     │  (decrypted)   │
│              │     │                  │     │                │
│ .sops.yaml   │     │  /etc/sops/age/  │     │  EnvFile=      │
│ (recipient)  │     │   keys.txt       │     │  points here   │
└──────────────┘     └──────────────────┘     └────────────────┘
```

### 3.2 Setup Summary

1. Install `age` + `sops` on the VPS.
2. Generate age keypair on the VPS:
   ```bash
   age-keygen -o /etc/sops/age/keys.txt
   chmod 600 /etc/sops/age/keys.txt
   ```
3. Add the public key to `.sops.yaml` in the repo:
   ```yaml
   creation_rules:
     - path_regex: secrets/.*\.env\.sops$
       age: "age1publickey..."
   ```
4. Encrypt secrets on workstation:
   ```bash
   sops --encrypt --input-type dotenv --output-type dotenv \
     secrets/prod.env > secrets/prod.env.sops
   ```
5. Commit only `.sops` files. Never commit `.env` plaintext.

### 3.3 Systemd Integration (via ExecStartPre)

The unit template decrypts to `/run/` (tmpfs, RAM-backed, wiped on reboot) using `ExecStartPre`:

```ini
ExecStartPre=/usr/bin/mkdir -p /run/guinevere
ExecStartPre=/usr/bin/bash -c 'SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt /usr/bin/sops --decrypt --input-type dotenv --output-type dotenv /opt/guinevare/secrets/prod.env.sops > /run/guinevare/secrets.env'
ExecStartPre=/usr/bin/chmod 600 /run/guinevare/secrets.env
```

### 3.4 Auto-Reload on Secret Rotation (Path Unit)

Create a path unit that watches the encrypted file and triggers a re-decrypt oneshot on change:

```ini
# /etc/systemd/system/guinevere-secrets.path
[Unit]
Description=Watch encrypted secrets

[Path]
PathChanged=/opt/guinevare/secrets/prod.env.sops
Unit=guinevere-secrets-reload.service

[Install]
WantedBy=multi-user.target
```

The oneshot service decrypts and signals the bot via `kill -s HUP`. Enable both to create a self-healing loop: rotated secrets in git → pull → systemd re-decrypts → bot reloads.

---

## 4. Local-Development Caveats

### 4.1 User-Level systemd Services

For development without root, use `systemd --user`:

```ini
# ~/.config/systemd/user/guinevere-dev.service
[Unit]
Description=Guinevere Bot (Development)

[Service]
Type=simple
WorkingDirectory=%h/guinevere
ExecStart=%h/guinevare/.venv/bin/python -m bot
EnvironmentFile=%h/guinevare/.env.dev
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

- `%h` expands to `$HOME` automatically.
- Manage with `systemctl --user` (no sudo).
- **Enable lingering** to keep service running after logout:
  ```bash
  sudo loginctl enable-linger $USER
  ```

### 4.2 Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Relative path in ExecStart | `Status=203/EXEC` | Absolute path to venv python |
| User doesn't exist | `Status=217/USER` | Create with `useradd -r -s /bin/false` |
| WorkingDirectory inaccessible | `Status=200/CHDIR` | Check permissions on dir |
| Missing `daemon-reload` | Changes ignored | Run after editing unit files |
| EnvironmentFile world-readable | Secrets exposed | `chmod 600`, root-owned |
| `source activate` in ExecStart | Shell not found | Point at venv/bin/python directly |
| Rapid restart loops | "start request repeated too quickly" | Add `StartLimitIntervalSec/Burst` |
| Discord token in `ps` output | Token visible | Use EnvironmentFile, never CLI args |
| SOPS decrypt fails silently | Bot starts without secrets | Test decrypt manually first |

### 4.3 Verification Checklist

```bash
# 1. Validate unit file syntax
sudo systemd-analyze verify /etc/systemd/system/guinevere-bot.service

# 2. Test ExecStart manually as service user
sudo -u guinevare /opt/guinevare/.venv/bin/python -m bot --dry-run

# 3. Test SOPS decrypt
sudo SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt \
  sops --decrypt /opt/guinevare/secrets/prod.env.sops

# 4. Start and monitor
sudo systemctl daemon-reload
sudo systemctl enable --now guinevere-bot
sudo journalctl -u guinevere-bot -f
```

---

## References

- `systemd.service(5)` — [man page](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- `systemd.exec(5)` — [Environment & security directives](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- `systemd.kill(5)` — [Signal & kill mode docs](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)
- discord.py `Client.run()` SIGTERM handling — [source](https://github.com/Rapptz/discord.py/blob/v2.3.2/discord/client.py)
- SOPS official docs — [getsops.io/docs](https://getsops.io/docs/)
- systemd-credentials (systemd ≥ 254) — [guide](https://www.systemshardening.com/articles/linux/systemd-credentials-hardening/)
- journald.conf — [log rotation config](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html)