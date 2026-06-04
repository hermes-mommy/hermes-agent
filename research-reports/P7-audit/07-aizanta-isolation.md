# P7 Surveillance — Aizanta Isolation Audit

**Date**: 2026-06-03
**Auditor**: Guinevere (parent)
**Scope**: `src/surveillance/`, `systemd/guinevere-surveillance.service`, Docker networks, DB schemas
**Verdict**: **PASS** — No Aizanta contamination detected across all 9 isolation checks.

---

## 1. Redis Port Audit (Expected: 6380, NOT 6379)

| File | Line | Value | Status |
|---|---|---|---|
| `src/surveillance/redis_buffer.py` | 186 | `port: int = 6380` | PASS |
| `src/surveillance/redis_buffer.py` | 201 | `port=port` (defaults to 6380) | PASS |
| `src/surveillance/replay.py` | 56 | `port=6380` | PASS |
| `src/surveillance/consent_gate.py` | 133 | `port=6380` | PASS |
| `src/surveillance/consumer.py` | 400 | `port=6380` | PASS |

**Zero uses of port 6379** in any `src/surveillance/` file. All Redis connections target the dedicated Guinevere Redis on port 6380.

---

## 2. PostgreSQL Port Audit (Expected: 5433, NOT 5432)

| File | Line | Value | Status |
|---|---|---|---|
| `systemd/guinevere-surveillance.service` | 16 | `DATABASE_URL=postgresql+asyncpg://guinevere:***@localhost:5433/guinevere` | PASS |

No other PostgreSQL port references exist in surveillance source files (consumer.py delegates DB session factory via environment injection).

**Zero uses of port 5432** in any `src/surveillance/` file (confirmed via grep: 0 matches).

---

## 3. Redis DB Index Audit (Expected: DB2)

| File | Line | Value | Status |
|---|---|---|---|
| `src/surveillance/redis_buffer.py` | 202 | `db=2` | PASS |
| `src/surveillance/replay.py` | 57 | `db=2` | PASS |
| `src/surveillance/consent_gate.py` | 134 | `db=2` | PASS |
| `src/surveillance/consumer.py` | 401 | `db=2` | PASS |

All four Redis connections explicitly use **DB2**, the dedicated surveillance namespace. The code comments confirm: "DB2 is the dedicated surveillance namespace (cost tracking uses DB5)" (redis_buffer.py:9). No file uses `db=0` or omits the `db` parameter.

---

## 4. Redis Key Namespace Isolation

| File | Key Prefix | Purpose | Status |
|---|---|---|---|
| `src/surveillance/redis_buffer.py` | `surveillance:buffer` | Event buffer list | PASS |
| `src/surveillance/replay.py` | `surveillance:nonce:` | Nonce dedup keys | PASS |
| `src/surveillance/consent_gate.py` | `consent:surveillance:` | Consent cache keys | PASS |

All Redis keys are namespaced with `surveillance:` or `consent:surveillance:` prefixes, preventing key collisions with other Guinevere subsystems or any potential Aizanta usage.

---

## 5. Systemd Service Isolation

| Check | Finding | Status |
|---|---|---|
| References to "aizanta" | Zero matches | PASS |
| References to aizanta containers | Zero matches | PASS |
| Service dependencies | `guinevere-core.service`, `docker.service`, `network.target` only | PASS |
| User isolation | `User=guinevere`, `Group=guinevere` | PASS |
| Slice isolation | `Slice=guinevere.slice` | PASS |
| Filesystem hardening | `ProtectSystem=strict`, `ProtectHome=read-only` with `ReadWritePaths` restricted to Guinevere paths | PASS |
| DATABASE_URL | `localhost:5433/guinevere` — separate port, guinevere database | PASS |

The systemd unit runs as `guinevere` user, depends only on Guinevere services, uses `guinevere.slice`, and restricts filesystem access to Guinevere paths only. No Aizanta-related environment variables, paths, or dependencies exist.

---

## 6. Docker Network Isolation

| Network | Subnet | Owner | Status |
|---|---|---|---|
| `guinevere-net` | 172.28.0.0/16 | Guinevere | PASS |
| `aizanta_aizanta-internal` | 172.18.0.0/16 | Aizanta | PASS |
| `bridge` | 172.17.0.0/16 | Docker default | PASS |

Source: `docs/setup-evidence/P0/STEP-P0-010/docker-network.txt`

**No subnet overlap.** Guinevere-net uses 172.28.0.0/16; Aizanta uses 172.18.0.0/16. Surveillance services connect via `localhost` (not Docker network) for Redis and PostgreSQL. The docker-compose.yml (`docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml`) uses `guinevere-net` (external: true) for the Gotify container only.

---

## 7. Aizanta Code Reference Check

| Search Pattern | Scope | Matches | Status |
|---|---|---|---|
| `aizanta\|Aizanta\|AIZANTA` (grep) | `src/surveillance/` | **0** | PASS |
| `import.*aizanta\|from.*aizanta` (grep) | `src/surveillance/` | **0** | PASS |

No surveillance file imports, references, or mentions Aizanta in any form. The `src/surveillance/__init__.py` exports are all internal Guinevere modules (`consent_gate`, `replay`, `timescale`, `redis_buffer`, etc.).

---

## 8. TimescaleDB Schema Isolation

| Table | SQLAlchemy Model | Schema | Usage |
|---|---|---|---|
| `surveillance.events` | `SurveillanceEvents` | `surveillance` | Writes via `TimescaleIngester.ingest_batch()` (timescale.py:126) |
| `surveillance.ingestion_log` | `IngestionLog` | `surveillance` | Writes via `_write_ingestion_log()` (timescale.py:357) |
| `surveillance.confrontation_block_log` | `ConfrontationBlockLog` | `surveillance` | Defined in models.py:533 |
| `consent.consent_ledger` | (raw query) | `consent` | Read-only via `_query_ledger()` (consent_gate.py:393) |

**Schema confirmation** (from `src/memory/models.py`):
- `SurveillanceEvents.__table_args__` = `{"schema": "surveillance"}` (line 482)
- `IngestionLog.__table_args__` = `{"schema": "surveillance"}` (line 510)
- `consent_ledger.__table_args__` = `{"schema": "consent"}` (line 895)

**No writes to `public` schema. No writes to `aizanta` schema.** Surveillance data is fully isolated to its own `surveillance` schema. The consent gate reads from the `consent` schema (also Guinevere-owned, defined alongside surveillance models).

---

## 9. Port Defaults Negative Confirmation

```
# grep for port 5432 or 6379 in ALL src/surveillance/ files
Pattern: (5432|6379)
Scope:   C:\Users\faizz\guinevere\src\surveillance\*
Result:  ZERO matches
```

Not a single file in the surveillance module references the default PostgreSQL port (5432) or default Redis port (6379). All connections explicitly specify 5433 and 6380 respectively.

---

## Summary

| # | Check | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | Redis port | 6380 (never 6379) | All 4 files: 6380 | PASS |
| 2 | PG port | 5433 (never 5432) | systemd: 5433; no source refs to 5432 | PASS |
| 3 | Redis DB | db=2 (never db=0) | All 4 files: db=2 | PASS |
| 4 | Redis DB2 for nonces | redis_buffer.py: db=2 | replay.py: db=2, key prefix `surveillance:nonce:` | PASS |
| 5 | Redis DB2 for cache | consent_gate.py: db=2 | consent_gate.py: db=2, key prefix `consent:surveillance:` | PASS |
| 6 | Default ports in surveillance | 0 matches | 0 matches for 5432\|6379 | PASS |
| 7 | Docker network | guinevere-net only | guinevere-net, separate subnet from aizanta | PASS |
| 8 | Aizanta imports/refs | 0 matches | 0 matches | PASS |
| 9 | TimescaleDB schema | surveillance schema only | `surveillance` schema for events/ingestion_log; `consent` schema for ledger reads | PASS |

**Overall Verdict: PASS — Surveillance is fully isolated from Aizanta across all boundaries (network, database, Redis namespaces, filesystem, and code-level references).**

No remediation needed.
