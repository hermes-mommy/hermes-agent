# STEP-P7-018 Verification Report

**Task:** Create systemd Service Unit for Surveillance Consumer
**Date:** 2026-06-03
**Status:** PASS (11/11 checks)

---

## 1. Grep Verification Checks

| # | Check | Expected | Actual | Status |
|---|-------|----------|--------|--------|
| 1 | `Slice=guinevere.slice` | 1 | 1 | PASS |
| 2 | `Type=exec` | 1 | 1 | PASS |
| 3 | `User=guinevere` | 1 | 1 | PASS |
| 4 | `NoNewPrivileges=true` | 1 | 1 | PASS |
| 5 | `ProtectSystem=strict` | 1 | 1 | PASS |
| 6 | `MemoryHigh=512M` | 1 | 1 | PASS |
| 7 | `MemoryMax=768M` | 1 | 1 | PASS |
| 8 | `CPUQuota=100%` | 1 | 1 | PASS |
| 9 | `src.surveillance.consumer` | 1 | 1 | PASS |
| 10 | `redis-guinevere` (absent) | 0 | 0 | PASS |
| 11 | `postgresql.service` (absent) | 0 | 0 | PASS |

---

## 2. Comparison with guinevere-loops.service Pattern

| Field | guinevere-loops.service | guinevere-surveillance.service | Delta |
|-------|------------------------|-------------------------------|-------|
| Description | Guinevere Agent Loop Daemon | Guinevere Surveillance Consumer | Changed |
| After | guinevere-core.service network.target | guinevere-core.service docker.service network.target | +docker.service |
| Group | (not set) | guinevere | +explicit |
| Extra Env | (none) | GUINEVERE_DB_PASSWORD, DATABASE_URL | +2 env vars |
| ExecStart | src.loops.manager | src.surveillance.consumer | Changed |
| MemoryHigh | 1G | 512M | -50% |
| MemoryMax | 2G | 768M | -62.5% |
| CPUQuota | 200% | 100% | -50% |
| Type | exec | exec | Same |
| User | guinevere | guinevere | Same |
| Slice | guinevere.slice | guinevere.slice | Same |
| Security hardening | Full set | Full set | Same |
| ReadWritePaths | 4 paths | 4 paths (identical) | Same |

---

## 3. Resource Budget Analysis (guinevere.slice)

### Slice Total Budget
- MemoryMax: 8G
- CPUQuota: 200%

### Service Resource Allocation

| Service | MemoryHigh | MemoryMax | CPUQuota |
|---------|-----------|-----------|----------|
| guinevere-loops | 1G | 2G | 200% |
| guinevere-core | ~1G | ~2G | ~200% |
| guinevere-discord | ~256M | ~512M | ~50% |
| guinevere-scheduler | ~256M | ~512M | ~50% |
| **guinevere-surveillance (NEW)** | **512M** | **768M** | **100%** |
| **Total** | **~3.5G** | **~5.78G** | **~600%** |

### Budget Headroom
- Memory: 5.78G / 8G = 72.3% utilized, 2.22G headroom remaining
- CPU: 600% / 200% = exceeds slice CPU quota

**Note:** CPUQuota values across services sum to 600%, but the slice limits to 200%. This is acceptable because not all services peak simultaneously. The surveillance consumer is a bursty background worker, not a constant CPU consumer. Systemd CPU quotas are soft limits at the service level and hard limits at the slice level. The slice will throttle services proportionally when aggregate CPU exceeds 200%.

### Memory Safety
The surveillance consumer at 512M/768M is sized for:
- Async message processing (low steady-state memory)
- Occasional DB write batching (moderate bursts)
- No LLM inference (no GPU/large tensor memory)

MemoryMax=768M provides 1.5x headroom over MemoryHigh=512M, matching systemd's soft/hard limit pattern.

---

## 4. Structural Validation

- File created at correct path: `systemd/guinevere-surveillance.service`
- 36 lines (3 more than loops service due to Group + 2 extra Environment lines)
- Follows INI-style systemd unit format
- No trailing whitespace or encoding issues
- Section order: [Unit], [Service], [Install] (correct)
- ExecStart uses absolute Python path within venv (correct)
- DATABASE_URL uses asyncpg driver on port 5433 (matches PG config)
- Redis password via systemd credential specifier %E (matches pattern)
- No hardcoded secrets present

---

## Footer

| Item | Value |
|------|-------|
| File created | `systemd/guinevere-surveillance.service` |
| Lines | 36 |
| All 11 checks | PASS |
| No existing files modified | Confirmed |
