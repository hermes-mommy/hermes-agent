# STEP-P7-018 Auditor Gate

**Task:** Create systemd Service Unit for Surveillance Consumer
**Date:** 2026-06-03
**Auditor:** Automated gate check
**Verdict:** PASS

---

## Gate Checklist

| # | Check | Criteria | Result |
|---|-------|----------|--------|
| 1 | File exists | `systemd/guinevere-surveillance.service` present | PASS |
| 2 | Type=exec | Service type is `exec` (not forking/simple) | PASS |
| 3 | User=guinevere | Runs as unprivileged `guinevere` user (not root) | PASS |
| 4 | Slice=guinevere.slice | Assigned to correct resource slice | PASS |
| 5 | Resource limits present | MemoryHigh=512M, MemoryMax=768M, CPUQuota=100% | PASS |
| 6 | Security hardening present | NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only | PASS |
| 7 | No references to non-existent services | No `redis-guinevere.service` or `postgresql.service` in After/Requires | PASS |
| 8 | ExecStart points to src.surveillance.consumer | `python -m src.surveillance.consumer` | PASS |

---

## Detailed Findings

### 1. File Exists
- Path: `systemd/guinevere-surveillance.service`
- Size: 36 lines
- Format: Valid systemd unit file (INI-style)
- **PASS**

### 2. Type=exec
- `Type=exec` on line 8
- Not `forking`, `simple`, `oneshot`, or `notify`
- Matches guinevere-loops.service pattern
- **PASS**

### 3. User=guinevere
- `User=guinevere` on line 9
- `Group=guinevere` on line 10 (explicit, tighter than loops service)
- Not root. No privilege escalation possible with NoNewPrivileges=true.
- **PASS**

### 4. Slice=guinevere.slice
- `Slice=guinevere.slice` on line 22
- Enables shared resource budgeting with other Guinevere services
- **PASS**

### 5. Resource Limits
- MemoryHigh=512M (soft limit, triggers reclaim pressure)
- MemoryMax=768M (hard limit, OOM kill if exceeded)
- CPUQuota=100% (one full CPU core equivalent)
- All three directives present and within specified bounds
- **PASS**

### 6. Security Hardening
- NoNewPrivileges=true: prevents privilege escalation via setuid/setgid
- ProtectSystem=strict: entire filesystem tree read-only except /dev, /proc, /sys
- ProtectHome=read-only: home directories readable but not writable
- ReadWritePaths: explicitly whitelists 4 paths for write access
- **PASS**

### 7. No Non-Existent Service References
- After= references: guinevere-core.service, docker.service, network.target
- Requires= references: guinevere-core.service
- No `redis-guinevere.service` (count=0)
- No `postgresql.service` (count=0)
- docker.service exists on the target VPS (TimescaleDB container dependency)
- **PASS**

### 8. ExecStart Module Path
- ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.surveillance.consumer
- Uses venv Python binary (absolute path)
- Module invocation via `-m` flag (correct Python packaging pattern)
- Consumer entry point at `src/surveillance/consumer.py`
- **PASS**

---

## Anti-Pattern Scan

| Anti-Pattern | Found | Status |
|---|---|---|
| Type=forking or Type=simple | No | CLEAN |
| User=root | No | CLEAN |
| Hardcoded secrets | No | CLEAN |
| Empty ExecStart | No | CLEAN |
| Missing Restart directive | No (Restart=always) | CLEAN |
| Missing Slice assignment | No | CLEAN |
| Resource limits exceed slice budget | No (768M < 8G) | CLEAN |
| Missing security hardening | No | CLEAN |

---

## Verdict

**PASS** — All 8 gate checks passed. No anti-patterns detected. File follows the established guinevere-loops.service pattern with appropriate modifications for the surveillance consumer workload.

---

## Footer

| Item | Value |
|------|-------|
| Auditor gate | PASS |
| Checks passed | 8/8 |
| Anti-patterns found | 0 |
| Evidence path | `docs/setup-evidence/P7/STEP-P7-018/` |
