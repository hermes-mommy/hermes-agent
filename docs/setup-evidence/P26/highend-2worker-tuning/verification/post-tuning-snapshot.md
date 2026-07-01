# P26 Post-Tuning Snapshot

- Captured At: 2026-06-27T18:12:27+07:00
- Hostname: ninerouter-vps
- Snapshot Type: post SQLite runtime patch and PM2 restart

## PM2 Status
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 39839    │ 65s    │ 5    │ online    │ 0%       │ 159.0mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 39852    │ 65s    │ 5    │ online    │ 0%       │ 197.0mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 71.0mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘

## PM2 JSON Summary
[
  {
    "pm_id": 0,
    "pid": 39839,
    "status": "online",
    "exec_mode": "cluster_mode",
    "instances": 2,
    "restart_time": 5,
    "unstable_restarts": 0,
    "node_args": [
      "--max-old-space-size=1843"
    ],
    "max_memory_restart": 1992294400,
    "memory_mb": 159,
    "cpu": 0
  },
  {
    "pm_id": 1,
    "pid": 39852,
    "status": "online",
    "exec_mode": "cluster_mode",
    "instances": 2,
    "restart_time": 5,
    "unstable_restarts": 0,
    "node_args": [
      "--max-old-space-size=1843"
    ],
    "max_memory_restart": 1992294400,
    "memory_mb": 197,
    "cpu": 0
  }
]

## Endpoint Checks
local_models_http_code=200 time_total=0.022519
models_count=45
first_model_ids=orcestrator,subagent,tester,router9,minimax

## SQLite Checks
ok
wal
1000
4096
235280

## Runtime Pattern Checks
runtime_old_patterns=PASS
busy_timeout_30000=11
wal_autocheckpoint_10000=11
checkpoint_passive=24

## Logs Since Restart Approximation
Worker log mtimes:
/root/.pm2/logs/9router-error-0.log 2026-06-27 18:08:42.306525841 +0700
/root/.pm2/logs/9router-error-1.log 2026-06-27 18:08:41.238493447 +0700
/root/.pm2/logs/9router-out-0.log 2026-06-27 18:12:25.216289662 +0700
/root/.pm2/logs/9router-out-1.log 2026-06-27 18:12:25.081285558 +0700
Filtered hard error counts in last 120 log lines; may include pre-restart lines if files retained old tail:
6
Recent restart marker lines:
1|9router  | TOKEN_REFRESH Codex refresh token already used or invalid. Re-auth required. { status: 401, code: 'refresh_token_invalidated' }
0|9router  | You have triggered an unhandledRejection, you may have forgotten to catch a Promise rejection:
0|9router  | SqliteError: database is locked
0|9router  |     at sqliteTransaction (/root/9router/.next/standalone/node_modules/better-sqlite3/lib/methods/transaction.js:65:24)
0|9router  | SqliteError: database is locked
0|9router  |   code: 'SQLITE_BUSY'
0|9router  | ⨯ unhandledRejection:  SqliteError: database is locked
0|9router  |   code: 'SQLITE_BUSY'

## Resource Checks
               total        used        free      shared  buff/cache   available
Mem:            4000         400         629           0        2970        3599
Swap:              0           0           0
0.07 0.07 0.10 1/76 40049
Total: 51427
TCP:   6341 (estab 16, closed 6317, orphaned 6, timewait 1677)

Transport Total     IP        IPv6
RAW	  0         0         0        
UDP	  4         3         1        
TCP	  24        18        6        
INET	  28        21        7        
FRAG	  0         0         0        


## Network Boundary Checks
active
100.104.210.75  vps-9router  userid:4959529179634517  linux  -  
LISTEN 0      128          0.0.0.0:64527      0.0.0.0:*    users:(("tailscaled",pid=33592,fd=14))                 
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=11675,fd=3),("systemd",pid=1,fd=37))
LISTEN 0      511          0.0.0.0:20128      0.0.0.0:*    users:(("PM2 v7.0.1: God",pid=24174,fd=23))            
LISTEN 0      128             [::]:22            [::]:*    users:(("sshd",pid=11675,fd=4),("systemd",pid=1,fd=42))
-P INPUT ACCEPT
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
-P INPUT ACCEPT

## Boundary Compliance
- SSH session alive during snapshot.
- Tailscale active.
- Firewall commands read-only.
- Worker count exactly 2.

## Operator Host Checks

operator_tailscale_models_http_code=200 time_total=0.429988
curl.exe : curl: (7) Failed to connect to 49.12.82.34 port 20128 after 3176 ms: Could not connect to server
At line:72 char:11
+ $public = curl.exe -sS -o NUL -w "operator_public_ipv4_http_code=%{ht ...
+           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (curl: (7) Faile...nnect to server:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
operator_public_ipv4_http_code=000 exit=7 time_total=3.176991
