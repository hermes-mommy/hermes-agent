# P26 Backup Report

- Timestamp: 2026-06-27T18:07:50+07:00
- Backup Root: /root/p26-highend-2worker-tuning-backups/20260627-180750
- Mutation Status: backup only; no runtime patch yet

## SQLite Backup
- DB backup created: /root/p26-highend-2worker-tuning-backups/20260627-180750/db/data.sqlite.backup
- Integrity: ok

## PM2 Backup
- PM2 jlist saved: /root/p26-highend-2worker-tuning-backups/20260627-180750/system/pm2-jlist.json
- PM2 dump saved: /root/p26-highend-2worker-tuning-backups/20260627-180750/system/dump.pm2
- pm2-root systemd unit captured: /root/p26-highend-2worker-tuning-backups/20260627-180750/system/pm2-root.service.txt
- sysctl config saved: /root/p26-highend-2worker-tuning-backups/20260627-180750/system/99-9router-hightraffic.conf

## Runtime File Backup
- Runtime files backed up: 17
- Runtime file list: /root/p26-highend-2worker-tuning-backups/20260627-180750/runtime-files/patched-file-list.txt

## Restore Commands
```bash
# Restore runtime files
while IFS= read -r f; do rel="${f#/root/9router/}"; cp -a '/root/p26-highend-2worker-tuning-backups/20260627-180750/runtime-files/'"$rel" "$f"; done < '/root/p26-highend-2worker-tuning-backups/20260627-180750/runtime-files/patched-file-list.txt'
pm2 restart 9router --update-env

# Restore PM2 dump if needed
cp -a '/root/p26-highend-2worker-tuning-backups/20260627-180750/system/dump.pm2' /root/.pm2/dump.pm2 && pm2 resurrect

# Restore SQLite DB only if integrity/runtime rollback requires it
pm2 stop 9router
cp -a /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite.bad-p26-rollback-$(date +%Y%m%d-%H%M%S)
cp -a '/root/p26-highend-2worker-tuning-backups/20260627-180750/db/data.sqlite.backup' /var/lib/9router/db/data.sqlite
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check;'
pm2 start 9router
```

## Boundary Compliance
- No firewall, Tailscale, SSH, PM2 restart, sysctl write, or runtime source patch was performed in this backup step.
- Backup artifacts remain on VPS; sensitive PM2 dump contents were not printed.

# P26 SQLite Runtime Patch

- Patch Timestamp: 2026-06-27T18:10:26+07:00
- Backup Root Used: /root/p26-highend-2worker-tuning-backups/20260627-180750

## Files Patched
/root/9router/.next/standalone/.next/server/chunks/3593.js
/root/9router/.next/standalone/.next/server/chunks/4055.js
/root/9router/.next/standalone/.next/server/chunks/4739.js
/root/9router/.next/standalone/.next/server/chunks/4780.js
/root/9router/.next/standalone/.next/server/chunks/507.js
/root/9router/.next/standalone/.next/server/chunks/5217.js
/root/9router/.next/standalone/.next/server/chunks/5258.js
/root/9router/.next/standalone/.next/server/chunks/698.js
/root/9router/.next/standalone/.next/server/chunks/7965.js
/root/9router/.next/standalone/.next/server/chunks/8520.js
/root/9router/.next/standalone/src/lib/db/adapters/betterSqliteAdapter.js
/root/9router/.next/standalone/src/lib/db/adapters/bunSqliteAdapter.js
/root/9router/.next/standalone/src/lib/db/adapters/nodeSqliteAdapter.js
/root/9router/src/lib/db/adapters/betterSqliteAdapter.js
/root/9router/src/lib/db/adapters/bunSqliteAdapter.js
/root/9router/src/lib/db/adapters/nodeSqliteAdapter.js
/root/9router/src/lib/db/schema.js

## Patch Application
patched: /root/9router/.next/standalone/.next/server/chunks/3593.js
patched: /root/9router/.next/standalone/.next/server/chunks/4055.js
patched: /root/9router/.next/standalone/.next/server/chunks/4739.js
patched: /root/9router/.next/standalone/.next/server/chunks/4780.js
patched: /root/9router/.next/standalone/.next/server/chunks/507.js
patched: /root/9router/.next/standalone/.next/server/chunks/5217.js
patched: /root/9router/.next/standalone/.next/server/chunks/5258.js
patched: /root/9router/.next/standalone/.next/server/chunks/698.js
patched: /root/9router/.next/standalone/.next/server/chunks/7965.js
patched: /root/9router/.next/standalone/.next/server/chunks/8520.js
patched: /root/9router/.next/standalone/src/lib/db/adapters/betterSqliteAdapter.js
patched: /root/9router/.next/standalone/src/lib/db/adapters/bunSqliteAdapter.js
patched: /root/9router/.next/standalone/src/lib/db/adapters/nodeSqliteAdapter.js
patched: /root/9router/src/lib/db/adapters/betterSqliteAdapter.js
patched: /root/9router/src/lib/db/adapters/bunSqliteAdapter.js
patched: /root/9router/src/lib/db/adapters/nodeSqliteAdapter.js
patched: /root/9router/src/lib/db/schema.js

## Source Syntax Checks

## Operator Host Endpoint Checks

tailscale_models_http_code=200 time_total=0.436791curl: (7) Failed to connect to 49.12.82.34 port 20128 after 3039 ms: Could not connect to server public_ipv4_http_code=000 exit=7 time_total=3.039970

# P26 SQLite Runtime Patch Continuation

- Timestamp: 2026-06-27T18:11:21+07:00
- Reason: continue after missing standalone schema syntax-check path; no PM2 restart occurred before this continuation

## Existing File Check
exists: /root/9router/.next/standalone/.next/server/chunks/3593.js
exists: /root/9router/.next/standalone/.next/server/chunks/4055.js
exists: /root/9router/.next/standalone/.next/server/chunks/4739.js
exists: /root/9router/.next/standalone/.next/server/chunks/4780.js
exists: /root/9router/.next/standalone/.next/server/chunks/507.js
exists: /root/9router/.next/standalone/.next/server/chunks/5217.js
exists: /root/9router/.next/standalone/.next/server/chunks/5258.js
exists: /root/9router/.next/standalone/.next/server/chunks/698.js
exists: /root/9router/.next/standalone/.next/server/chunks/7965.js
exists: /root/9router/.next/standalone/.next/server/chunks/8520.js
exists: /root/9router/.next/standalone/src/lib/db/adapters/betterSqliteAdapter.js
exists: /root/9router/.next/standalone/src/lib/db/adapters/bunSqliteAdapter.js
exists: /root/9router/.next/standalone/src/lib/db/adapters/nodeSqliteAdapter.js
exists: /root/9router/src/lib/db/adapters/betterSqliteAdapter.js
exists: /root/9router/src/lib/db/adapters/bunSqliteAdapter.js
exists: /root/9router/src/lib/db/adapters/nodeSqliteAdapter.js
exists: /root/9router/src/lib/db/schema.js

## Existing Source Syntax Checks

## Forbidden Pattern Verification In Patched File List
PASS: old PRAGMA/checkpoint patterns absent from patched file list

## Required Pattern Counts
busy_timeout_30000=11
wal_autocheckpoint_10000=11
mmap_268435456=11
checkpoint_passive=24

## PM2 Restart
### Before
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 31108    │ 8h     │ 4    │ online    │ 0%       │ 251.3mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 31121    │ 8h     │ 4    │ online    │ 0%       │ 314.0mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 71.0mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
restart_counts_before=0:4:online,1:4:online
[PM2] Applying action restartProcessId on app [9router](ids: [ 0, 1 ])
[PM2] [9router](0) ✓
[PM2] [9router](1) ✓
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 39839    │ 0s     │ 5    │ online    │ 0%       │ 65.5mb   │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 39852    │ 0s     │ 5    │ online    │ 0%       │ 43.5mb   │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 71.0mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
### After
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 39839    │ 8s     │ 5    │ online    │ 0%       │ 153.2mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 39852    │ 8s     │ 5    │ online    │ 0%       │ 170.9mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 71.0mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
restart_counts_after=0:5:online:39839,1:5:online:39852
[PM2] Saving current process list...
[PM2] Successfully saved in /root/.pm2/dump.pm2

## Immediate Runtime Checks
local_models=PASS
ok
wal
1000

## Recent Post-Restart Error Scan Counts
6

## OS/Network No-Op Verification
net.core.somaxconn = 4096
net.ipv4.ip_local_port_range = 32768	60999
active
-P INPUT ACCEPT
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP

## Boundary Compliance
- Restarted only PM2 app 9router.
- Worker count verified as 2 online.
- No firewall/Tailscale/SSH changes performed.

## Operator Host Endpoint Checks After Restart

tailscale_models_http_code=200 time_total=0.414263curl: (7) Failed to connect to 49.12.82.34 port 20128 after 3025 ms: Could not connect to server public_ipv4_http_code=000 exit=7 time_total=3.025046
