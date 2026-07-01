# P26 Final Runtime Proof After Repair

- Timestamp: 2026-06-27T18:26:54+07:00

## PM2
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 43086    │ 2m     │ 5    │ online    │ 0%       │ 175.2mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 43093    │ 2m     │ 5    │ online    │ 0%       │ 218.5mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
[
  {
    "pm_id": 0,
    "pid": 43086,
    "status": "online",
    "instances": 2,
    "exec_mode": "cluster_mode",
    "restart_time": 5,
    "unstable_restarts": 0,
    "memory_mb": 175.2
  },
  {
    "pm_id": 1,
    "pid": 43093,
    "status": "online",
    "instances": 2,
    "exec_mode": "cluster_mode",
    "restart_time": 5,
    "unstable_restarts": 0,
    "memory_mb": 218.5
  }
]

## SQLite
ok
wal
1000
apiKeys|3
providerConnections|979
usageHistory|5497
requestDetails|1000

## Endpoint
local_http_code=200 time_total=0.018286
models_count=45
first_model_ids=orcestrator,subagent,tester,router9,minimax

## Marker Error Scan
    100 200
error0 old=27544 new=27544
0
error1 old=47211 new=47211
0
out0 old=2789180 new=2789180
0
out1 old=5769337 new=5769337
0

## Network Boundary
active
LISTEN 0      128          0.0.0.0:64527      0.0.0.0:*    users:(("tailscaled",pid=33592,fd=14))                 
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=11675,fd=3),("systemd",pid=1,fd=37))
LISTEN 0      511          0.0.0.0:20128      0.0.0.0:*    users:(("PM2 v7.0.1: God",pid=24174,fd=3))             
LISTEN 0      128             [::]:22            [::]:*    users:(("sshd",pid=11675,fd=4),("systemd",pid=1,fd=42))
-P INPUT ACCEPT
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
-P INPUT ACCEPT

## Operator Host Checks

operator_tailscale_http_code=200 time_total=0.434586
curl.exe : curl: (7) Failed to connect to 49.12.82.34 port 20128 after 3200 ms: Could not connect to server
At line:50 char:9
+ $public=curl.exe -sS -o NUL -w "operator_public_ipv4_http_code=%{http ...
+         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (curl: (7) Faile...nnect to server:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
operator_public_ipv4_http_code=000 exit=7 time_total=3.200701
