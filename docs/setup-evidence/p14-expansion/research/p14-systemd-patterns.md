# p14-systemd-patterns

## Scope
Repository survey of Guinevere systemd units and timers to establish conventions for a new `guinevere-wearable` unit.

## Files Reviewed
### Canonical/primary systemd units under `systemd/`
- `systemd/guinevere-x-poster.service`
- `systemd/guinevere-gmail.service`
- `systemd/hermes-gateway.service`
- `systemd/guinevere-discord.service`
- `systemd/guinevere-surveillance.service`
- `systemd/guinevere-shadow-monitor.service`
- `systemd/guinevere-shadow-monitor.timer`
- `systemd/guinevere-scheduler.service`
- `systemd/guinevere-obscura.service`
- `systemd/guinevere-monitoring.service`
- `systemd/guinevere-mcp.service`
- `systemd/guinevere-loops.service`

### Additional relevant templates / deployment mirrors found during search
- `deploy/systemd/guinevere-whatsapp.service`
- `deploy/discord/guinevere-discord.service`
- `vps-mirror/systemd-live/*.service`
- `vps-mirror/systemd-live/*.timer`
- `scripts/guinevere-backup@.service`
- `scripts/guinevere-backup@.timer`
- `scripts/guinevere-prune-weekly@.service`
- `scripts/guinevere-prune-weekly@.timer`
- `scripts/guinevere-backup-weekly@.timer`

## Observed Service Patterns

### 1) Canonical Guinevere service shape
Most current services follow this baseline:
- `[Unit]` with `Description=Guinevere ...`
- `After=` often includes `network.target` or `network-online.target`
- optional `Requires=` for hard dependencies
- optional `Wants=` for soft dependencies
- `[Service]` with `Type=exec` for Python/process daemons
- `User=guinevere`
- `WorkingDirectory=/home/guinevere/code/guinevere`
- `Environment=PYTHONPATH=/home/guinevere/code/guinevere`
- `Environment=PYTHONDONTWRITEBYTECODE=1`
- `Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv`
- `EnvironmentFile=` points to a service-specific env file in the repo (`/home/guinevere/code/guinevere/.env.<service>`) or deploy path (`/opt/guinevere/.env.whatsapp`)
- `ExecStart=` uses the repo venv Python, e.g. `/home/guinevere/code/guinevere/.venv/bin/python -m src.<module>.main`
- restart policy is usually `Restart=on-failure` or `Restart=always`
- `RestartSec=10` is the dominant default
- output is sent to journald: `StandardOutput=journal`, `StandardError=journal`
- many units join `Slice=guinevere.slice`
- hardening commonly includes `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`
- write access is restricted via `ReadWritePaths=` to repo/data/logs/evidence and sometimes `.hermes`

### 2) Dependency conventions
Dependencies are modeled consistently:
- `After=` declares startup order
- `Requires=` is used when the service must not run without the dependency
- `Wants=` is used when the dependency is helpful but not mandatory
- recurring upstream dependencies:
  - `network.target` / `network-online.target`
  - `guinevere-core.service`
  - `docker.service` for container-backed stacks
  - `redis.service` or `postgresql.service` for data-dependent services
  - cross-service coordination such as `guinevere-loops.service` or `guinevere-discord.service`
- `PartOf=` appears in at least `guinevere-shadow-monitor.service` to couple lifecycle to `guinevere.slice`

### 3) Logging and resource control
Common conventions:
- logging goes to journald, then downstream tooling (Promtail/Loki) consumes it
- `SyslogIdentifier=` is used in some newer units (`guinevere-whatsapp`, `hermes-gateway`, `guinevere-monitoring`)
- memory/CPU caps are set per service, commonly within:
  - `MemoryHigh=128M..1G`
  - `MemoryMax=256M..2G`
  - `CPUQuota=50%..200%`
- service-specific resources reflect workload class:
  - light one-shots: 128M/256M, 50%
  - bot/gateway/loops: 512M/1G or 1G/2G, 100%/200%

### 4) Health and watchdog patterns
- No unit in the reviewed `systemd/` directory uses `WatchdogSec=`, `Type=notify`, `NotifyAccess=`, or `sd_notify`
- therefore there is no canonical watchdog/notify pattern to copy yet
- health checking is instead externalized via separate scripts, timers, or monitoring stack checks
- examples include `guinevere-shadow-monitor.service` as a `Type=oneshot` checker and `scripts/test_log_pipeline.sh`

## Timer Patterns
Only one timer exists directly under `systemd/`:
- `systemd/guinevere-shadow-monitor.timer`

Observed timer shape:
- `[Unit] Description=... Timer`
- `[Timer]`
- `OnBootSec=60`
- `OnUnitActiveSec=60`
- `AccuracySec=5`
- `Persistent=true`
- `[Install] WantedBy=timers.target`

Additional timer conventions found in scripts/
- `Persistent=true` is consistently used for recurring jobs to catch up missed runs after boot
- `WantedBy=timers.target` is the install target everywhere
- some timers use `OnCalendar=` in other parts of repo, but those are outside the core `systemd/` directory and were not the primary focus

## Environment Variable Patterns

### Local repo env files
Current service env files are typically service-scoped and colocated with the repo:
- `/home/guinevere/code/guinevere/.env.discord`
- `/home/guinevere/code/guinevere/.env.gmail`
- `/home/guinevere/code/guinevere/.env.mcp`
- `/home/guinevere/code/guinevere/.env.loops`
- `/home/guinevere/code/guinevere/.env.scheduler`
- `/home/guinevere/code/guinevere/.env.surveillance`
- `/home/guinevere/code/guinevere/.env.x_poster`
- `/home/guinevere/code/guinevere/.env.hermes`

### Deployed env file exception
- WhatsApp uses `/opt/guinevere/.env.whatsapp` in the deploy template

### Common env keys
- `PYTHONPATH=/home/guinevere/code/guinevere`
- `PYTHONDONTWRITEBYTECODE=1`
- `VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv`
- some units add `PYTHONUNBUFFERED=1`

### SOPS / age patterns
- secrets are commonly generated from SOPS-encrypted files using an age key
- repository scripts expect `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt`
- `scripts/setup-service-envs.sh` explicitly mentions generating per-service env files from SOPS-encrypted secrets and then running `systemctl daemon-reload`
- backup scripts and health scripts also rely on the same age-key path

## Service Installation / Management Patterns

### Gmail install script is the clearest service-management precedent
`scripts/install_gmail_service.sh` shows the deployment flow:
1. copy/install service file
2. `sudo systemctl daemon-reload`
3. `sudo systemctl enable guinevere-gmail.service`
4. `sudo systemctl start guinevere-gmail.service`
5. verify with `sudo systemctl status ... --no-pager`
6. inspect logs with `sudo journalctl -u ... -f`

### Other management clues
- `scripts/setup-service-envs.sh` ends with `sudo systemctl daemon-reload` and a start command list for multiple services
- monitoring and preflight scripts use `systemctl is-active` and `journalctl` for runtime checks
- `systemctl list-timers` is used to verify recurring jobs

## Monitoring / Log Rotation / Observability

### Journald is the log sink
Every reviewed service uses journald (`StandardOutput=journal`, `StandardError=journal`) or at least one of them.

### Downstream log collection
The monitoring stack and comments indicate Promtail/Loki collect journald output. This means log retention/rotation is handled through journald/systemd + Loki rather than per-service file logs.

### No explicit logrotate config found
No repo-level logrotate config for these services was found in the searched surface.

## New `guinevere-wearable` Template

### Recommended `.service`
```ini
[Unit]
Description=Guinevere Wearable Sync Service
Documentation=https://github.com/faizz/guinevere
After=network-online.target guinevere-core.service
Requires=guinevere-core.service
Wants=network-online.target

[Service]
Type=exec
User=guinevere
Group=guinevere
Slice=guinevere.slice
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
EnvironmentFile=/home/guinevere/code/guinevere/.env.wearable
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.wearable.sync
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitIntervalSec=60
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-wearable
MemoryHigh=512M
MemoryMax=1G
CPUQuota=100%
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
```

### Recommended `.timer` if wearable sync should run periodically
```ini
[Unit]
Description=Guinevere Wearable Sync Timer

[Timer]
OnBootSec=60
OnUnitActiveSec=60
AccuracySec=5
Persistent=true

[Install]
WantedBy=timers.target
```

### If the wearable service is event-driven instead of periodic
- omit the timer
- keep the service shape above
- add external health/trigger checks instead of watchdog until a notify-based design is introduced

## Installation Procedure

1. Create or generate the env file at `/home/guinevere/code/guinevere/.env.wearable`
2. Ensure SOPS/age secret provisioning exists if the env contains secrets
3. Copy the `.service` (and `.timer` if used) into `/etc/systemd/system/`
4. Run `sudo systemctl daemon-reload`
5. If using the timer: `sudo systemctl enable --now guinevere-wearable.timer`
6. If using only the service: `sudo systemctl enable --now guinevere-wearable.service`
7. Verify with `sudo systemctl status guinevere-wearable.service --no-pager`
8. Inspect logs with `sudo journalctl -u guinevere-wearable.service -f`

## Monitoring Integration Points
- journald output is the primary log source
- Loki/Promtail should pick up the service logs automatically if configured for journald collection
- add service-specific metrics in the app, if any, to the existing monitoring stack
- if periodic, timer status can be inspected via `systemctl list-timers | grep guinevere-wearable`
- if the wearable touches surveillance data, ensure the corresponding privacy/consent handling aligns with the existing surveillance service conventions

## Practical Recommendation for `guinevere-wearable`
- match the common service baseline: `Type=exec`, `User=guinevere`, `WorkingDirectory`, `EnvironmentFile`, journald logging, `Restart=on-failure`
- include `Slice=guinevere.slice`
- add `After=network-online.target guinevere-core.service` and `Requires=guinevere-core.service` if it depends on core runtime
- use `Persistent=true` in the timer if missed intervals must run after reboot
- prefer `SyslogIdentifier=guinevere-wearable` for easier log filtering
