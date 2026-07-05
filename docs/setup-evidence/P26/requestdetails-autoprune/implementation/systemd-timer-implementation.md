# P26 RequestDetails Autoprune — systemd Timer Backstop Implementation

**Output Path:** `docs/setup-evidence/P26/requestdetails-autoprune/implementation/systemd-timer-implementation.md`  
**Scope:** Implementation evidence for the root-owned oneshot service and timer backstop that will live on the VPS at `/etc/systemd/system/9router-prune-requestdetails.service` and `/etc/systemd/system/9router-prune-requestdetails.timer`.  
**Boundary:** No payloads, no secrets, no env dumps, and no unrelated tables.

## Rationale

The pruning script is the primary enforcement point because it owns the SQLite-safe delete logic and can run immediately when invoked. The systemd timer is only a backstop: it re-applies the same retention policy on a schedule if the app-side retention path regresses, is disabled, or misses a run after reboot. That keeps the app logic authoritative while adding a small, auditable safety net.

## Unit Files

### `/etc/systemd/system/9router-prune-requestdetails.service`

```ini
[Unit]
Description=Prune 9Router requestDetails rows
RequiresMountsFor=/var/lib/9router/db
ConditionPathExists=/var/lib/9router/db/data.sqlite

[Service]
Type=oneshot
User=root
Group=root
ExecStart=/usr/local/sbin/9router-prune-requestdetails.sh
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/9router/db
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
LockPersonality=true
MemoryDenyWriteExecute=true
SystemCallArchitectures=native
RestrictAddressFamilies=AF_UNIX
RestrictSUIDSGID=true
UMask=0077
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=120
```

### `/etc/systemd/system/9router-prune-requestdetails.timer`

```ini
[Unit]
Description=Run 9Router requestDetails prune every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true
Unit=9router-prune-requestdetails.service

[Install]
WantedBy=timers.target
```

## Deployment Commands

```bash
cat <<'EOF' >/etc/systemd/system/9router-prune-requestdetails.service
[Unit]
Description=Prune 9Router requestDetails rows
RequiresMountsFor=/var/lib/9router/db
ConditionPathExists=/var/lib/9router/db/data.sqlite

[Service]
Type=oneshot
User=root
Group=root
ExecStart=/usr/local/sbin/9router-prune-requestdetails.sh
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/9router/db
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
LockPersonality=true
MemoryDenyWriteExecute=true
SystemCallArchitectures=native
RestrictAddressFamilies=AF_UNIX
RestrictSUIDSGID=true
UMask=0077
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=120
EOF

cat <<'EOF' >/etc/systemd/system/9router-prune-requestdetails.timer
[Unit]
Description=Run 9Router requestDetails prune every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true
Unit=9router-prune-requestdetails.service

[Install]
WantedBy=timers.target
EOF

chown root:root /etc/systemd/system/9router-prune-requestdetails.service /etc/systemd/system/9router-prune-requestdetails.timer
chmod 0644 /etc/systemd/system/9router-prune-requestdetails.service /etc/systemd/system/9router-prune-requestdetails.timer

systemd-analyze verify /etc/systemd/system/9router-prune-requestdetails.service /etc/systemd/system/9router-prune-requestdetails.timer
systemctl daemon-reload
systemctl enable --now 9router-prune-requestdetails.timer
systemctl status 9router-prune-requestdetails.timer --no-pager
systemctl list-timers 9router-prune-requestdetails.timer --all --no-pager
```

## Notes

- The service is root-owned and runs as a oneshot because the job is a bounded maintenance action, not a long-lived daemon.
- `ProtectSystem=strict` is safe here because the only writable location the prune job needs is the canonical SQLite directory under `/var/lib/9router/db`.
- The timer is intentionally a backstop, not a replacement for the pruning script or any app-side retention setting.
