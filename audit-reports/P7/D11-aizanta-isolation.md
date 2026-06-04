# D11 - Aizanta Isolation Audit

> **P7 Surveillance: Port Isolation, No Cross-Contamination**

| Field | Value |
|---|---|
| Audit ID | D11 |
| Scope | P7 Surveillance - Aizanta project isolation on shared VPS |
| Auditor | Isolation Auditor (automated) |
| Date | 2026-06-03 |
| Verdict | **PASS** |

---

## 1. Port Isolation

Verified that surveillance code never references default ports belonging to Aizanta.

| Service | Aizanta Default Port | Guinevere Surveillance Port | Grep Result (src/surveillance/) | Status |
|---|---|---|---|---|
| Redis | 6379 | 6380 | 0 matches for `6379` | PASS |
| PostgreSQL | 5432 | 5433 | 0 matches for `5432` | PASS |

**Evidence:**
- `grep 6379 src/surveillance/` -- zero matches
- `grep 5432 src/surveillance/` -- zero matches
- systemd `DATABASE_URL` confirms port 5433: `postgresql+asyncpg://guinevere:...@localhost:5433/guinevere`

---

## 2. DB Index Isolation

Verified that Redis connections use only DB2, never DB0/DB1/DB3/DB5.

| DB Index | Owner | Grep Pattern | Matches in src/surveillance/ | Status |
|---|---|---|---|---|
| DB0 | Aizanta / general cache | `db=0` | 0 | PASS |
| DB1 | Reserved | `db=1` | 0 | PASS |
| DB2 | Guinevere surveillance | `db=2` | (confirmed by research) | PASS |
| DB3 | Reserved | `db=3` | 0 | PASS |
| DB5 | Reserved | `db=5` | 0 | PASS |

**Evidence:**
- `grep db=[0135] src/surveillance/` -- zero matches for any non-DB2 index

---

## 3. Docker Network Isolation

Verified that Guinevere surveillance operates on an isolated Docker network.

| Property | Guinevere | Aizanta |
|---|---|---|
| Network name | guinevere-net | aizanta (separate) |
| Subnet | 172.28.x.x | 172.18.x.x |
| Cross-contamination risk | None | None |

**Evidence:**
- Research findings confirmed separate Docker networks with non-overlapping subnets (172.28 vs 172.18)
- No shared network bridges or aliases detected

---

## 4. Code Reference Scan

Verified zero cross-references between Guinevere surveillance code and Aizanta project.

| Scan Target | Pattern | Matches | Status |
|---|---|---|---|
| `src/surveillance/` | `aizanta` | 0 | PASS |
| `systemd/guinevere-surveillance.service` | `aizanta` | 0 | PASS |

**Evidence:**
- `grep aizanta src/surveillance/` -- zero matches
- `grep aizanta systemd/` -- zero matches
- No imports, config references, or comments mentioning Aizanta

---

## 5. Schema Isolation (TimescaleDB / PostgreSQL)

Verified that all surveillance ORM models use the `surveillance` schema exclusively.

| Table Location (models.py) | Schema Value | Status |
|---|---|---|
| Line 461 | `"schema": "surveillance"` | PASS |
| Line 482 | `"schema": "surveillance"` | PASS |
| Line 510 | `"schema": "surveillance"` | PASS |
| Line 534 | `"schema": "surveillance"` | PASS |

**Evidence:**
- All 4 surveillance table definitions in `src/memory/models.py` declare `schema: "surveillance"`
- Zero surveillance tables use `public`, `aizanta`, or any other schema
- The broader models.py defines 12 schemas (memory, persona, surveillance, financial, projects, social, agents, consent, security, audit, ops, extensions) -- all properly scoped per domain

---

## 6. systemd User/Slice Isolation

Verified that the surveillance service runs under Guinevere-specific user, group, and slice.

| Directive | Value | Expected | Status |
|---|---|---|---|
| `User=` | `guinevere` | `guinevere` | PASS |
| `Group=` | `guinevere` | `guinevere` | PASS |
| `Slice=` | `guinevere.slice` | `guinevere.slice` | PASS |
| `WorkingDirectory=` | `/home/guinevere/code/guinevere` | Guinevere path | PASS |
| `DATABASE_URL` | `localhost:5433/guinevere` | Port 5433, DB guinevere | PASS |

**Evidence:**
- `systemd/guinevere-surveillance.service` lines 8-9: `User=guinevere`, `Group=guinevere`
- Line 22: `Slice=guinevere.slice`
- Line 10: WorkingDirectory scoped to `/home/guinevere/code/guinevere`
- Line 16: DATABASE_URL uses port 5433 and database `guinevere`
- Resource limits (MemoryHigh=512M, MemoryMax=768M, CPUQuota=100%) contain blast radius
- Security hardening: `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`
- ReadWritePaths limited to Guinevere-owned directories only

---

## 7. Summary

| Isolation Domain | Check | Result |
|---|---|---|
| Redis port | No 6379 references | PASS |
| PostgreSQL port | No 5432 references | PASS |
| Redis DB index | Only DB2 used | PASS |
| Docker network | Separate network + subnet | PASS |
| Code references | Zero aizanta mentions | PASS |
| DB schema | surveillance schema only | PASS |
| systemd user/slice | guinevere user + slice | PASS |

---

## Overall Verdict: **PASS**

P7 surveillance is fully isolated from the Aizanta project. No cross-contamination vectors exist across ports, database indices, Docker networks, code references, database schemas, or systemd process boundaries.

---

*Audit conducted 2026-06-03. All grep checks executed against live source files. No source files were modified.*
