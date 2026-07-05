# P26 baseline Loadtest

- Captured At: 2026-06-27T18:25:08+07:00
- Endpoint: http://127.0.0.1:20128/v1/models
- Requests: 300
- Concurrency: 20
- Provider quota impact: none; models endpoint only

## Log Markers Before Load
error0=27544 error1=47211 out0=2789180 out1=5757844

## Pre-State
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 43086    │ 57s    │ 5    │ online    │ 0%       │ 147.7mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 43093    │ 57s    │ 5    │ online    │ 0%       │ 142.2mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
               total        used        free      shared  buff/cache   available
Mem:            4000         307         223           0        3468        3692
Swap:              0           0           0
0.55 0.33 0.24 1/79 43155
ok

## Load Command
seq 1 300 | xargs -P 20 -n1 curl -sS -o /dev/null -w '%{http_code} %{time_total}' --max-time 15 http://127.0.0.1:20128/v1/models

## Timing Summary
total=300
statuses=200:300
success_rate=100.00%
p50=0.200833s
p95=0.349287s
p99=0.456575s
min=0.034582s max=0.555950s mean=0.204455s

## Post-State
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 43086    │ 67s    │ 5    │ online    │ 0%       │ 170.4mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 43093    │ 67s    │ 5    │ online    │ 0%       │ 190.1mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
               total        used        free      shared  buff/cache   available
Mem:            4000         390         133           0        3476        3609
Swap:              0           0           0
1.13 0.46 0.28 1/79 43772
Total: 51928
TCP:   6572 (estab 11, closed 6553, orphaned 2, timewait 1427)

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
### out1 old=5757844 new=5760167
0

## New Worker Prefix Counts
out1 
## Verdict
PASS: all requests returned HTTP 200; no provider quota used.
