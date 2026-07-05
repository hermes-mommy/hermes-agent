# P26 post Loadtest

- Captured At: 2026-06-27T18:25:19+07:00
- Endpoint: http://127.0.0.1:20128/v1/models
- Requests: 700
- Concurrency: 50
- Provider quota impact: none; models endpoint only

## Log Markers Before Load
error0=27544 error1=47211 out0=2789180 out1=5760167

## Pre-State
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 43086    │ 68s    │ 5    │ online    │ 0%       │ 170.4mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 43093    │ 68s    │ 5    │ online    │ 0%       │ 190.1mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
               total        used        free      shared  buff/cache   available
Mem:            4000         391         131           0        3478        3608
Swap:              0           0           0
1.12 0.47 0.29 1/79 43809
ok

## Load Command
seq 1 700 | xargs -P 50 -n1 curl -sS -o /dev/null -w '%{http_code} %{time_total}' --max-time 15 http://127.0.0.1:20128/v1/models

## Timing Summary
total=700
statuses=200:700
success_rate=100.00%
p50=0.391370s
p95=0.621673s
p99=0.660345s
min=0.011226s max=0.685152s mean=0.377228s

## Post-State
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 43086    │ 83s    │ 5    │ online    │ 0%       │ 176.8mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 43093    │ 83s    │ 5    │ online    │ 0%       │ 202.4mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
               total        used        free      shared  buff/cache   available
Mem:            4000         409         119           0        3472        3590
Swap:              0           0           0
1.76 0.64 0.34 1/79 45226
Total: 51894
TCP:   7367 (estab 11, closed 7348, orphaned 2, timewait 2222)

Transport Total     IP        IPv6
RAW	  0         0         0        
UDP	  4         3         1        
TCP	  19        13        6        
INET	  23        16        7        
FRAG	  0         0         0        

ok

## New Log Bytes Error Scan
### error0 old=27544 new=27544
0
### error1 old=47211 new=47211
0
### out0 old=2789180 new=2789180
0
### out1 old=5760167 new=5760290
0

## New Worker Prefix Counts
out1 
## Verdict
PASS: all requests returned HTTP 200; no provider quota used.
