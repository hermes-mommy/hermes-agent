# P26 Repair Candidate Inspection

- Timestamp: 2026-06-27T18:23:30+07:00
- Candidate: /root/p26-highend-2worker-tuning-backups/repair-20260627-182226/data.sqlite.repaired
total 1.8G
-rw-r--r-- 1 root root 920M Jun 27 18:20 data.sqlite.corrupt-before-repair
-rw-r--r-- 1 root root 920M Jun 27 18:22 data.sqlite.repaired
## Integrity
ok
## Counts
tables|12
apiKeys|3
providerConnections|979
providerNodes|5
usageHistory|5485
requestDetails|1000
usageDaily|2
## Live DB Current Integrity First Lines
*** in database main ***
Tree 36 page 94470 cell 1: 2nd reference to page 33575
Tree 36 page 32885 cell 2: 2nd reference to page 32833
Tree 36 page 16963 cell 1: overflow list length is 27 but should be 320
Page 504: never used
Page 7787: never used
Page 15268: never used
Page 15270: never used
Page 15271: never used
Page 15273: never used
Page 15274: never used
Page 15275: never used
Page 15276: never used
Page 15277: never used
Page 15278: never used
Page 15279: never used
Page 15280: never used
Page 15281: never used
Page 15282: never used
Page 15283: never used
## PM2
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 42962    │ 36s    │ 5    │ online    │ 0%       │ 137.1mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 42969    │ 36s    │ 5    │ online    │ 0%       │ 164.5mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 54.3mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
