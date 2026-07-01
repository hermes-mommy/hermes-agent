# P26 RequestDetails Autoprune Pre-Prune Snapshot

- Captured At: 2026-06-27T19:20:19+07:00
- Hostname: ninerouter-vps
- Scope: read-only; no prune/delete/timer mutation

## PM2 Status
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 43086    │ 56m    │ 5    │ online    │ 0%       │ 283.3mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 43093    │ 56m    │ 5    │ online    │ 0%       │ 231.1mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘

## Endpoint Health
local_models_http_code=200 time_total=0.019360
models_count=46
first_model_ids=orcestrator,subagent,tester,router9,minimax

## Tailscale Status
active
100.104.210.75  vps-9router  userid:4959529179634517  linux  -  

## Firewall Read-Only
-P INPUT ACCEPT
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
-P INPUT ACCEPT

## DB Files
-rw-r--r-- 1 root root 920M Jun 27 19:20 /var/lib/9router/db/data.sqlite
-rw-r--r-- 1 root root  96K Jun 27 19:20 /var/lib/9router/db/data.sqlite-shm
-rw-r--r-- 1 root root  35M Jun 27 19:20 /var/lib/9router/db/data.sqlite-wal
/var/lib/9router/db/data.sqlite size=963706880 mtime=2026-06-27 19:20:17.596199010 +0700
/var/lib/9router/db/data.sqlite-wal size=36429072 mtime=2026-06-27 19:20:18.686232141 +0700
/var/lib/9router/db/data.sqlite-shm size=98304 mtime=2026-06-27 19:20:17.809205485 +0700

## SQLite PRAGMA
ok
wal
1000
4096
235280
0
0
-2000

## Schema
CREATE TABLE requestDetails (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, status TEXT, data TEXT NOT NULL);
CREATE INDEX idx_rd_ts ON requestDetails(timestamp DESC);
CREATE INDEX idx_rd_provider ON requestDetails(provider);
CREATE INDEX idx_rd_model ON requestDetails(model);
CREATE INDEX idx_rd_conn ON requestDetails(connectionId);

## Counts And Sizes Without Payload Content
metric|value
requestDetails_count|1000
metric|value
usageHistory_count|5939
metric|value
usageDaily_count|2
metric|value
requestDetails_min_ts|2026-06-27T10:15:01.520Z
metric|value
requestDetails_max_ts|2026-06-27T12:20:17.345Z
metric|value
requestDetails_avg_data_len|630474.71
metric|value
requestDetails_max_data_len|2081882
metric|value
requestDetails_total_data_mb|601.27

## dbstat requestDetails MB
requestDetails|605.37|154975

## Dashboard Timing Probes
/dashboard/usage http_code=307 time_total=0.004080
/usage http_code=404 time_total=0.008542
/api/usage http_code=401 time_total=0.009944
/api/dashboard/usage http_code=401 time_total=0.004375

## Existing Autoprune Units/Scripts

## Boundary Compliance
- No requestDetails.data content printed.
- No DB mutation, PM2 restart, firewall change, Tailscale change, or endpoint change performed.

## Operator Host Checks

operator_tailscale_models_http_code=200 time_total=0.491219
curl.exe : curl: (7) Failed to connect to 49.12.82.34 port 20128 after 3196 ms: Could not connect to server
At line:81 char:9
+ $public=curl.exe -sS -o NUL -w "operator_public_ipv4_http_code=%{http ...
+         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (curl: (7) Faile...nnect to server:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
operator_public_ipv4_http_code=000 exit=7 time_total=3.196307
