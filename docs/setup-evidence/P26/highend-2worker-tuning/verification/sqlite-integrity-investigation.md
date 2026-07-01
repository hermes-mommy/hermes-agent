# P26 SQLite Integrity Investigation

- Timestamp: 2026-06-27T18:20:05+07:00
- Backup Root: /root/p26-highend-2worker-tuning-backups/integrity-investigation-20260627-182005
- Scope: stop only PM2 app 9router for cold integrity check; no firewall/Tailscale/SSH changes

## Pre-Stop PM2
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 39839    │ 8m     │ 5    │ online    │ 0%       │ 224.9mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 39852    │ 8m     │ 5    │ online    │ 0%       │ 189.5mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 60.9mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘

## Stop 9Router For Cold DB Check
[PM2] Applying action stopProcessId on app [9router](ids: [ 0, 1 ])
[PM2] [9router](0) ✓
[PM2] [9router](1) ✓
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 0        │ 0      │ 5    │ stopped   │ 0%       │ 0b       │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 0        │ 0      │ 5    │ stopped   │ 0%       │ 0b       │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 60.9mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 0        │ 0      │ 5    │ stopped   │ 0%       │ 0b       │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 0        │ 0      │ 5    │ stopped   │ 0%       │ 0b       │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 60.9mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘

## Current DB Backup Before Any Repair
total 1.8G
-rw-r--r-- 1 root root 920M Jun 27 18:20 data.sqlite.current-copy
-rw-r--r-- 1 root root 920M Jun 27 18:20 data.sqlite.sqlite-backup

## Cold Integrity Checks
### live file integrity_check
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
Page 15284: never used
Page 15285: never used
Page 15286: never used
Page 15287: never used
Page 15288: never used
Page 15289: never used
Page 15290: never used
Page 15291: never used
Page 15955: never used
Page 15956: never used
Page 15957: never used
Page 15958: never used
Page 15959: never used
Page 15960: never used
Page 15961: never used
Page 15962: never used
Page 15963: never used
Page 15964: never used
Page 15965: never used
Page 15966: never used
Page 15967: never used
Page 15968: never used
Page 15969: never used
Page 15970: never used
Page 15971: never used
Page 15972: never used
Page 15973: never used
Page 15974: never used
Page 15975: never used
Page 15976: never used
Page 15977: never used
Page 15978: never used
Page 15979: never used
Page 15980: never used
Page 15981: never used
Page 15982: never used
Page 15983: never used
Page 15984: never used
Page 15985: never used
Page 15986: never used
Page 15987: never used
Page 15988: never used
Page 15989: never used
Page 15991: never used
Page 15992: never used
Page 15993: never used
Page 15994: never used
Page 15995: never used
Page 15996: never used
Page 15997: never used
Page 15998: never used
Page 15999: never used
Page 16000: never used
Page 16001: never used
Page 16002: never used
Page 16003: never used
Page 16004: never used
Page 16005: never used
Page 16006: never used
Page 16007: never used
Page 16008: never used
Page 16009: never used
Page 16010: never used
Page 16012: never used
Page 16013: never used
Page 16014: never used
Page 16015: never used
Page 16016: never used
Page 16017: never used
Page 16018: never used
Page 16019: never used
Page 16020: never used
Page 16021: never used
Page 16022: never used
Page 16023: never used
Page 16024: never used
Page 16025: never used
Page 16026: never used
Page 16027: never used
Page 16028: never used
Page 16029: never used
### live file quick_check
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
Page 15284: never used
Page 15285: never used
Page 15286: never used
Page 15287: never used
Page 15288: never used
Page 15289: never used
Page 15290: never used
Page 15291: never used
Page 15955: never used
Page 15956: never used
Page 15957: never used
Page 15958: never used
Page 15959: never used
Page 15960: never used
Page 15961: never used
Page 15962: never used
Page 15963: never used
Page 15964: never used
Page 15965: never used
Page 15966: never used
Page 15967: never used
Page 15968: never used
Page 15969: never used
Page 15970: never used
Page 15971: never used
Page 15972: never used
Page 15973: never used
Page 15974: never used
Page 15975: never used
Page 15976: never used
Page 15977: never used
Page 15978: never used
Page 15979: never used
Page 15980: never used
Page 15981: never used
Page 15982: never used
Page 15983: never used
Page 15984: never used
Page 15985: never used
Page 15986: never used
Page 15987: never used
Page 15988: never used
Page 15989: never used
Page 15991: never used
Page 15992: never used
Page 15993: never used
Page 15994: never used
Page 15995: never used
Page 15996: never used
Page 15997: never used
Page 15998: never used
Page 15999: never used
Page 16000: never used
Page 16001: never used
Page 16002: never used
Page 16003: never used
Page 16004: never used
Page 16005: never used
Page 16006: never used
Page 16007: never used
Page 16008: never used
Page 16009: never used
Page 16010: never used
Page 16012: never used
Page 16013: never used
Page 16014: never used
Page 16015: never used
Page 16016: never used
Page 16017: never used
Page 16018: never used
Page 16019: never used
Page 16020: never used
Page 16021: never used
Page 16022: never used
Page 16023: never used
Page 16024: never used
Page 16025: never used
Page 16026: never used
Page 16027: never used
Page 16028: never used
Page 16029: never used
### sqlite backup integrity_check
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
Page 15284: never used
Page 15285: never used
Page 15286: never used
Page 15287: never used
Page 15288: never used
Page 15289: never used
Page 15290: never used
Page 15291: never used
Page 15955: never used
Page 15956: never used
Page 15957: never used
Page 15958: never used
Page 15959: never used
Page 15960: never used
Page 15961: never used
Page 15962: never used
Page 15963: never used
Page 15964: never used
Page 15965: never used
Page 15966: never used
Page 15967: never used
Page 15968: never used
Page 15969: never used
Page 15970: never used
Page 15971: never used
Page 15972: never used
Page 15973: never used
Page 15974: never used
Page 15975: never used
Page 15976: never used
Page 15977: never used
Page 15978: never used
Page 15979: never used
Page 15980: never used
Page 15981: never used
Page 15982: never used
Page 15983: never used
Page 15984: never used
Page 15985: never used
Page 15986: never used
Page 15987: never used
Page 15988: never used
Page 15989: never used
Page 15991: never used
Page 15992: never used
Page 15993: never used
Page 15994: never used
Page 15995: never used
Page 15996: never used
Page 15997: never used
Page 15998: never used
Page 15999: never used
Page 16000: never used
Page 16001: never used
Page 16002: never used
Page 16003: never used
Page 16004: never used
Page 16005: never used
Page 16006: never used
Page 16007: never used
Page 16008: never used
Page 16009: never used
Page 16010: never used
Page 16012: never used
Page 16013: never used
Page 16014: never used
Page 16015: never used
Page 16016: never used
Page 16017: never used
Page 16018: never used
Page 16019: never used
Page 16020: never used
Page 16021: never used
Page 16022: never used
Page 16023: never used
Page 16024: never used
Page 16025: never used
Page 16026: never used
Page 16027: never used
Page 16028: never used
Page 16029: never used

## Start 9Router Back
[PM2] Applying action restartProcessId on app [9router](ids: [ 0, 1 ])
[PM2] [9router](0) ✓
[PM2] [9router](1) ✓
[PM2] Process successfully started
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 42743    │ 0s     │ 5    │ online    │ 0%       │ 55.7mb   │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 42750    │ 0s     │ 5    │ online    │ 0%       │ 43.3mb   │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 56.4mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
┌────┬──────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│ id │ name             │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
├────┼──────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
│ 0  │ 9router          │ default     │ 0.5.8   │ cluster │ 42743    │ 8s     │ 5    │ online    │ 0%       │ 137.6mb  │ root     │ disabled │
│ 1  │ 9router          │ default     │ 0.5.8   │ cluster │ 42750    │ 8s     │ 5    │ online    │ 0%       │ 126.4mb  │ root     │ disabled │
└────┴──────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
Module
┌────┬──────────────────────────────┬───────────────┬──────────┬──────────┬──────┬──────────┬──────────┬──────────┐
│ id │ module                       │ version       │ pid      │ status   │ ↺    │ cpu      │ mem      │ user     │
├────┼──────────────────────────────┼───────────────┼──────────┼──────────┼──────┼──────────┼──────────┼──────────┤
│ 2  │ pm2-logrotate                │ 3.0.0         │ 28823    │ online   │ 3    │ 0%       │ 56.4mb   │ root     │
└────┴──────────────────────────────┴───────────────┴──────────┴──────────┴──────┴──────────┴──────────┴──────────┘
local_models_after_restart=PASS

## Boundary Compliance
- Stopped/started only PM2 app 9router for cold DB check.
- Current DB was backed up before any repair attempt.
- No repair, restore, delete, schema change, firewall/Tailscale/SSH mutation was performed.
