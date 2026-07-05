# P26 RequestDetails Autoprune DB Audit

| Field | Value |
|---|---|
| Task | P26 `requestDetails` autoprune DB audit |
| Output path | `docs/setup-evidence/P26/requestdetails-autoprune/research/db-audit.md` |
| Workspace | `C:\Users\faizz\guinevere` |
| SSH target | `root@49.12.82.34 -p 39999` |
| Captured at | 2026-06-27T19:27:49+07:00 |
| Hostname | `ninerouter-vps` |
| Mode | Read-only DB metadata research |
| Runtime mutation | None |
| Payload exposure | No request payload, response payload, row sample, secret, env value, or payload-column content included |

## Verdict

**NEEDS REVIEW before implementation.**

The live SQLite database is structurally healthy, but the current `requestDetails` retention surface is still large: 1,000 rows occupy about 574.44 MiB by `dbstat`, with about 570.50 MiB of aggregate payload-column byte length. `usageHistory` is much smaller at 6,005 rows and about 1.70 MiB by `dbstat`; `usageDaily` has 2 rows and about 0.12 MiB.

The database file itself is 920 MiB with about 87,121 free pages, roughly 340 MiB at 4 KiB/page. That means row pruning alone may bound future growth but may not immediately shrink the main SQLite file unless a separately approved compaction strategy is used.

## Scope

This audit covered only:

- `requestDetails` schema and indexes.
- `requestDetails` row count, timestamp range, aggregate byte sizes, and `dbstat` footprint.
- `usageHistory` and `usageDaily` row counts and timestamp/date ranges.
- SQLite file sizes, selected PRAGMA values, `integrity_check`, and `quick_check`.
- Risk analysis for a future autoprune implementation.

This audit did not:

- Delete, prune, vacuum, checkpoint, update, insert, or alter database state.
- Restart PM2, systemd units, SSH, Tailscale, firewall, or application processes.
- Read secrets, environment values, provider credentials, logs, shell history, or decrypted config.
- Print any payload-column content, JSON object content, request/response body, prompt, completion, message, or streaming chunk.

## Inputs Read

- `AGENTS.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/current-dashboard-db-ground-truth.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/pre-prune-snapshot.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/security-analysis.md`
- Remote SQLite metadata from `/var/lib/9router/db/data.sqlite`

## Read-Only Method

Remote DB checks used SQLite metadata-only statements through the SQLite CLI with read-only intent. The audit used schema inspection, aggregate counts, aggregate `length(...)` metrics, `dbstat`, and PRAGMA checks only.

One initial command shape failed with `Error: in prepare, incomplete input` before table inspection. It produced no table rows and no payload content. The command was retried with a simpler script form and completed successfully.

A trailing shell parsing warning appeared after successful output capture because of a Windows-to-SSH script encoding artifact. It did not affect the captured SQLite results and did not perform mutation.

## DB Files

| File | Size | Mtime |
|---|---:|---|
| `/var/lib/9router/db/data.sqlite` | 963,706,880 bytes | 2026-06-27 19:27:14.619875792 +0700 |
| `/var/lib/9router/db/data.sqlite-wal` | 36,429,072 bytes | 2026-06-27 19:27:37.283564734 +0700 |
| `/var/lib/9router/db/data.sqlite-shm` | 98,304 bytes | 2026-06-27 19:27:40.463661404 +0700 |

Human-readable sizes observed:

| File | Size |
|---|---:|
| `data.sqlite` | 920M |
| `data.sqlite-wal` | 35M |
| `data.sqlite-shm` | 96K |

## SQLite Version

`sqlite3` version:

```text
3.45.1 2024-01-30 16:01:20 e876e51a0ed5c5b3126f52e532044363a014bc594cfefa87ffb5b82257ccalt1 (64-bit)
```

## PRAGMA and Integrity

| Check | Value |
|---|---:|
| `journal_mode` | `wal` |
| `synchronous` | `2` |
| `page_size` | `4096` |
| `page_count` | `235280` |
| `freelist_count` | `87121` |
| `auto_vacuum` | `0` |
| `cache_size` | `-2000` |
| `integrity_check` | `ok` |
| `quick_check` | `ok` |

Interpretation:

- Integrity checks passed.
- WAL mode is active.
- `auto_vacuum=0`, so ordinary row deletion will not automatically shrink the main database file.
- `freelist_count=87121` indicates about 340.32 MiB of reusable pages inside the database file.

## requestDetails Schema

```sql
CREATE TABLE requestDetails (
  id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  provider TEXT,
  model TEXT,
  connectionId TEXT,
  status TEXT,
  data TEXT NOT NULL
);
```

Observed indexes:

| Index | Columns | Unique | Origin | Sort |
|---|---|---:|---|---|
| `idx_rd_conn` | `connectionId` | 0 | `c` | ASC |
| `idx_rd_model` | `model` | 0 | `c` | ASC |
| `idx_rd_provider` | `provider` | 0 | `c` | ASC |
| `idx_rd_ts` | `timestamp` | 0 | `c` | DESC |
| `sqlite_autoindex_requestDetails_1` | `id` | 1 | `pk` | ASC |

Index definitions:

```sql
CREATE INDEX idx_rd_conn ON requestDetails(connectionId);
CREATE INDEX idx_rd_model ON requestDetails(model);
CREATE INDEX idx_rd_provider ON requestDetails(provider);
CREATE INDEX idx_rd_ts ON requestDetails(timestamp DESC);
```

## requestDetails Counts and Size

| Metric | Value |
|---|---:|
| Row count | 1,000 |
| Minimum timestamp | 2026-06-27T10:17:03.793Z |
| Maximum timestamp | 2026-06-27T12:27:32.251Z |
| Average payload-column byte length | 598,208.32 |
| Maximum payload-column byte length | 2,081,882 |
| Total payload-column MiB | 570.50 |

`dbstat` footprint:

| Object | Pages | MiB | Payload Bytes | Unused Bytes | Max Payload |
|---|---:|---:|---:|---:|---:|
| `requestDetails` | 147,057 | 574.44 | 601,175,993 | 565,267 | 2,093,014 |
| `idx_rd_provider` | 20 | 0.08 | 65,000 | 13,684 | 65 |
| `idx_rd_ts` | 13 | 0.05 | 29,000 | 21,096 | 29 |
| `idx_rd_conn` | 14 | 0.05 | 41,000 | 13,180 | 41 |
| `sqlite_autoindex_requestDetails_1` | 10 | 0.04 | 28,106 | 9,738 | 74 |
| `idx_rd_model` | 11 | 0.04 | 27,567 | 14,361 | 41 |

Comparison with earlier P26 snapshot:

| Metric | Earlier snapshot | Current audit | Change |
|---|---:|---:|---:|
| `requestDetails` rows | 1,000 | 1,000 | 0 |
| Total payload-column MiB | 601.27 | 570.50 | -30.77 MiB |
| `dbstat` table MiB | 605.37 | 574.44 | -30.93 MiB |
| Minimum timestamp | 2026-06-27T10:15:01.520Z | 2026-06-27T10:17:03.793Z | Newer oldest row |
| Maximum timestamp | 2026-06-27T12:20:17.345Z | 2026-06-27T12:27:32.251Z | Newer newest row |

Interpretation:

- The built-in row cap appears to keep `requestDetails` at 1,000 rows.
- Row-count retention alone is not sufficient for disk safety because average retained row size is still about 584 KiB.
- The timestamp window is about 2 hours and 10 minutes, so at current activity the cap retains only a short high-volume window while still consuming hundreds of MiB.

## usageHistory and usageDaily

| Metric | Value |
|---|---:|
| `usageHistory` row count | 6,005 |
| `usageHistory` minimum timestamp | 2026-06-26T10:37:57.081Z |
| `usageHistory` maximum timestamp | 2026-06-27T12:27:32.251Z |
| `usageDaily` row count | 2 |
| `usageDaily` minimum date key | 2026-06-26 |
| `usageDaily` maximum date key | 2026-06-27 |

`dbstat` footprint:

| Object | Pages | MiB | Payload Bytes | Unused Bytes | Max Payload |
|---|---:|---:|---:|---:|---:|
| `usageHistory` | 435 | 1.70 | 1,662,135 | 76,781 | 356 |
| `usageDaily` | 31 | 0.12 | 117,377 | 9,433 | 111,605 |

Interpretation:

- `usageHistory` and `usageDaily` are not the immediate disk pressure source in this snapshot.
- `usageHistory` still grows over time and needs separate retention policy tracking, but its current footprint is tiny relative to `requestDetails`.
- `usageDaily` is aggregate data and currently negligible.

## Inventory Context

SQLite objects observed include the expected 9Router operational tables:

| Table | Present |
|---|---|
| `_meta` | Yes |
| `apiKeys` | Yes |
| `combos` | Yes |
| `kv` | Yes |
| `providerConnections` | Yes |
| `providerNodes` | Yes |
| `proxyPools` | Yes |
| `requestDetails` | Yes |
| `settings` | Yes |
| `sqlite_sequence` | Yes |
| `usageDaily` | Yes |
| `usageHistory` | Yes |

This audit did not inspect sensitive row values in these tables.

## Risks

| Risk | Severity | Evidence | Recommendation |
|---|---|---|---|
| `requestDetails` disk footprint remains high despite row cap | High | 1,000 rows consume 574.44 MiB by `dbstat` | Add an approved autoprune/retention control that bounds rows and/or aggregate bytes. |
| Database file does not shrink automatically after deletes | Medium | `auto_vacuum=0`, `freelist_count=87121`, file size 920M | Treat compaction as separate approval because it is operationally riskier than bounded pruning. |
| WAL can grow while app is active | Medium | WAL file observed at 35M | Monitor WAL size; any checkpoint/truncate action should be explicitly approved, not part of read-only research. |
| Payload-column content is sensitive | High | Schema stores large JSON text in `data`; average retained byte length is 598,208.32 | Evidence and automation must never log row content or JSON previews. |
| Built-in cap may only run on write/flush path | Medium | Rows are capped at 1,000, but large retained bytes persist | A timer/backstop can reduce risk if implemented with strict metadata-only logging. |
| `usageHistory` is not the current largest table but can grow unbounded | Medium | 6,005 rows, 1.70 MiB now | Track separately; do not conflate `usageHistory` pruning with this `requestDetails` task unless scope is expanded. |

## Autoprune Implications

For a future implementation, a safe plan should:

- Preserve newest rows deterministically.
- Avoid selecting or logging payload-column content.
- Report only row counts, aggregate byte lengths, timestamp range, `dbstat` totals, and integrity status.
- Avoid service restarts.
- Avoid firewall, Tailscale, SSH, provider, or environment changes.
- Avoid automatic compaction unless separately approved with backup/rollback evidence.
- Verify `integrity_check` after any future write operation.

## Boundary Compliance

| Boundary | Result |
|---|---|
| `AGENTS.md` read first | PASS |
| Evidence root read | PASS |
| Remote actions read-only | PASS |
| No prune/delete/update/insert/alter/vacuum/checkpoint | PASS |
| No service restart | PASS |
| No firewall/Tailscale changes | PASS |
| No secret/env dump | PASS |
| No payload-column content printed | PASS |
| Required output path used | PASS |

## Footer

P26 `requestDetails` autoprune DB audit generated 2026-06-27. This report is research-only and authorizes no database mutation or runtime change.
