# STEP-P0-015 — pgvector Extension Summary

## What Was Done

Installed pgvector extension in the Guinevere PostgreSQL 16 Docker container using a custom Dockerfile approach: built a new image from `postgres:16-trixie` with `postgresql-16-pgvector` apt package, replaced the container while preserving the existing data volume.

## Runtime Changes (VPS)

| Change | Detail |
|---|---|
| Container stopped | `guinevere-postgres` (original postgres:16-trixie) |
| Image built | `guinevere-postgres-pgvector:16` from Dockerfile |
| Container started | Same volume `/home/guinevere/data/postgres`, same network `guinevere-net`, same port `127.0.0.1:5433:5432` |
| Extension | `CREATE EXTENSION vector;` → v0.8.2 |
| Data | Preserved (volume unchanged, stop/start only) |

## Local Changes

| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-015/pgvector-install.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-015/pgvector-test.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-015/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-015/p0-015-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-015/verification.md` | Created |
| `PROGRESS.md` | Updated: 15→16/257, P0 15→16/29 |
| `CHECKLIST.md` | P0-015 checked |
| `stepprompts/StepPrompts.md` | P0-015 status → ✅ Completed |

## Validation

- `SELECT extversion FROM pg_extension WHERE extname='vector'` → 0.8.2
- `\dx` → vector 0.8.2 public
- Cosine distance test → PASS
- `pg_isready` → accepting connections
- Aizanta 5/5 healthy, ports unchanged

## Design Decisions

1. **Custom Dockerfile over exec install**: Docker exec installs packages but they don't survive container restarts. Custom Dockerfile ensures pgvector is baked into the image.
2. **pgvector 0.8.2 over 0.7.0**: apt installs the latest available package (0.8.2). Version 0.8.2 ≥ 0.7.0 requirement — fully compatible.
3. **Volume preserved**: Data at `/home/guinevere/data/postgres` untouched through stop → rm → run cycle.
4. **No Aizanta impact**: Only `guinevere-postgres` container was cycled. Aizanta postgres:16-alpine running separately.

## Rollback

Replace container with original `postgres:16-trixie` image:
```bash
docker stop guinevere-postgres
docker rm guinevere-postgres
docker run -d --name guinevere-postgres \
  --network guinevere-net \
  -p 127.0.0.1:5433:5432 \
  -v /home/guinevere/data/postgres:/var/lib/postgresql/data \
  -e POSTGRES_USER=guinevere -e POSTGRES_DB=guinevere \
  -e POSTGRES_HOST_AUTH_METHOD=scram-sha-256 \
  postgres:16-trixie
```
Extension `vector` will be gone but data intact (pgvector is data type extension — no structural corruption from removal).

## Caveats

- P0-016 TimescaleDB should use the same image approach: build from `guinevere-postgres-pgvector:16` to preserve pgvector.
- `shared_preload_libraries` still empty — TimescaleDB needs this in P0-016.