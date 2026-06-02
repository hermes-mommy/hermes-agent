# STEP-P0-017 — Internal Context Report: PostgreSQL Users Creation (Docker Adaptation)

| Field | Value |
|---|---|
| **Step** | P0-017 |
| **Type** | Database — PostgreSQL User & Schema Creation |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (parent orchestrator, pre-implementation context scan) |
| **Source** | `stepprompts/StepPrompts.md` lines 1727-1881 |
| **Infrastructure** | Docker container `guinevere-postgres` on `guinevere-net`, `postgres:16-trixie` base (custom image with pgvector + TimescaleDB) |
| **Port** | `127.0.0.1:5433:5432` |
| **Database** | `guinevere` per ADR-031 |
| **Superuser** | `guinevere` (existing, P0-014) |

---

## 1. Exact Scope

### 1.1 Objects to Create

**5 PostgreSQL Users:**

| User | Purpose | Privilege Level |
|---|---|---|
| `guinevere_core` | Core application (full CRUD on app schemas) | ALL on memory, persona, loops, config, financial, audit; USAGE+SELECT on surveillance |
| `guinevere_surveillance` | Surveillance ingestion (INSERT only) | USAGE+INSERT on surveillance + ALTER DEFAULT PRIVILEGES for INSERT |
| `guinevere_scheduler` | Scheduler service (CRUD on loops/scheduler) | ALL on loops |
| `guinevere_readonly` | Grafana dashboard queries | USAGE on ALL schemas, SELECT on memory/persona/surveillance/loops/financial + ALTER DEFAULT PRIVILEGES for SELECT |
| `guinevere_backup` | pg_dump operations | `pg_read_all_data` role |

**7 Schemas:**

| Schema | Purpose | Primary User(s) |
|---|---|---|
| `memory` | Episodic/semantic memory storage | guinevere_core (ALL) |
| `persona` | Mood/yandere/streak state | guinevere_core (ALL) |
| `surveillance` | Time-series surveillance events | guinevere_surveillance (INSERT only) |
| `loops` | Agent loop state/scheduler | guinevere_core (ALL), guinevere_scheduler (ALL) |
| `financial` | Transaction/budget data | guinevere_core (ALL) |
| `config` | Service configuration | guinevere_core (ALL) |
| `audit` | Audit log | guinevere_core (ALL) |

### 1.2 What Is NOT in Scope

| Exclusion | Reason |
|---|---|
| pg_hba.conf modification | P0-018 (hardening) |
| SSL certificate generation | P0-018 |
| PgBouncer configuration | P0-019 |
| Password rotation for existing `guinevere` superuser | Post-MVP or P0-017 if explicitly added |
| Connection limit configuration | P0-018 |
| Schema table creation | P3+ (Alembic migrations) |

---

## 2. Dependencies

| Dependency | Status | Notes |
|---|---|---|
| **P0-014** — PostgreSQL 16 running | ✅ Complete | Container `guinevere-postgres` Up (healthy), port 5433, database `guinevere` exists |
| **P0-012** — age key for SOPS encryption | ✅ Complete | Key at `/home/guinevere/secrets/age-key.txt`, round-trip encrypt/decrypt verified |
| **P0-013** — Secrets file structure (`.sops.yaml`) | ✅ Complete | Creation rules configured with path_regex |
| **P0-015** — pgvector extension | ✅ Complete | vector 0.8.2 installed, coexists with TimescaleDB |
| **P0-016** — TimescaleDB extension | ✅ Complete | timescaledb 2.27.1 installed, shared_preload_libraries configured |
| **Docker daemon** | ✅ Running | `docker ps` responsive, guinevere-net exists (172.28.0.0/16) |
| **Host directory** for evidence | ✅ | `docs/setup-evidence/P0/STEP-P0-017/` will be created at write time |

---

## 3. Definition of Done (DoD) Mapping

### 3.1 DoD Items from StepPrompts

| # | DoD Item | Verification Method (Docker-Adapted) |
|---|---|---|
| 1 | 5 users created: `guinevere_core`, `guinevere_surveillance`, `guinevere_scheduler`, `guinevere_readonly`, `guinevere_backup` | `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "\du"` |
| 2 | 7 schemas created: memory, persona, surveillance, loops, financial, config, audit | `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "\dn"` |
| 3 | Core user can connect | `docker exec guinevere-postgres psql -U guinevere_core -d guinevere -c "SELECT 1"` |
| 4 | Surveillance user restricted (INSERT only, no SELECT on own tables — except default privileges apply to future tables) | `docker exec guinevere-postgres psql -U guinevere_surveillance -d guinevere -c "SELECT * FROM surveillance.test"` (expect permission denied) |
| 5 | Passwords encrypted in SOPS | `sops -d secrets/db-passwords.yaml` shows all 5 passwords + 5 connection URLs |
| 6 | Evidence files present | `docs/setup-evidence/P0/STEP-P0-017/pg-users.txt` + `pg-schemas.txt` |
| 7 | Trackers synced | PROGRESS.md: P0-017 [x], P0 18/29; CHECKLIST.md: P0-017 [x]; StepPrompts: P0-017 ✅ Completed |

### 3.2 Acceptance Criteria References

| AC ID | Description | How P0-017 Addresses It |
|---|---|---|
| **AC-SEC-001** | Least privilege enforcement — each service connects with its own PostgreSQL user and cannot access data outside its authorized schemas. | 5 role-separated users with precisely scoped GRANTs; no user has cross-schema ALL access; surveillance user is INSERT-only; readonly user is SELECT-only |
| **AC-MEM-001** | Memory schema must exist and be accessible to the core application user. | Schema `memory` created, `guinevere_core` has ALL privileges on it |

---

## 4. Shared Writers (Collision Scan)

| File | Risk | Mitigation |
|---|---|---|
| `PROGRESS.md` | SHARED — multiple steps update progress counters | **Parent-only** — no parallel writes; update once after implementation + auditor gate passes |
| `CHECKLIST.md` | SHARED — lines 116-117 need P0-017 checkmarks | **Parent-only** — update after gate passes; note: CHECKLIST.md line 116 currently lists only 4 users (missing `guinevere_backup`) — may need correction to list all 5 |
| `stepprompts/StepPrompts.md` | SHARED — status needs `✅ Completed` update | **Parent-only** — update line 1730 status and git commit hash |
| `secrets/db-passwords.yaml` | SOLE OWNER — created by P0-017 only | No collision risk; P0-017 creates it, subsequent steps read it |
| `docs/setup-evidence/P0/STEP-P0-017/` | SOLE OWNER — evidence root | No other step writes here |
| `audit-reports/P0/STEP-P0-017/` | SOLE OWNER — auditor reports | This file + step auditor report |

---

## 5. Bare-Metal → Docker Adaptation Matrix

Every command in `StepPrompts.md` lines 1748-1869 that references bare-metal PostgreSQL admin patterns needs adaptation for the Docker container.

### 5.1 Complete Command Translation Table

| # | StepPrompts (Bare-Metal) | Docker-Adapted | Rationale |
|---|---|---|---|
| 1 | `sudo -u postgres psql -d guinevere << EOF ... EOF` | `docker exec -i guinevere-postgres psql -U guinevere -d guinevere << EOF ... EOF` | No `sudo` or `postgres` OS user in Docker; use container superuser `guinevere` |
| 2 | `sudo -u postgres psql -c "\du"` | `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "\du"` | List users via container exec |
| 3 | `sudo -u postgres psql -c "\dn"` | `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "\dn"` | List schemas via container exec |
| 4 | `cd /home/guinevere/code/guinevere` | SAME — verify working directory | Repo root is already the working directory |
| 5 | `AGE_PUBKEY=$(grep ... /home/guinevere/secrets/age-key.txt \| awk '{print $4}')` | SAME — runs on host | age key is on host filesystem, not container |
| 6 | `cat > /tmp/db-passwords.yaml << EOF` | SAME — runs on host | Temp file on host before SOPS encryption |
| 7 | `sops --encrypt --age "$AGE_PUBKEY" /tmp/db-passwords.yaml > secrets/db-passwords.yaml` | SAME — runs on host | SOPS CLI on host, writes repo-relative path |
| 8 | `rm /tmp/db-passwords.yaml` | SAME — runs on host | Cleanup temp file on host |
| 9 | Verification: `PGPASSWORD=$CORE_PASS psql -U guinevere_core -d guinevere -c "SELECT 1"` | **ADAPT** → `docker exec guinevere-postgres psql -U guinevere_core -d guinevere -c "SELECT 1"` (simplest) OR `PGPASSWORD=$CORE_PASS psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere -c "SELECT 1"` (from host) | Without `-h -p`, psql defaults to Unix socket at port 5432 (wrong) |
| 10 | Rollback: `sudo -u postgres psql ... DROP USER` | `docker exec -i guinevere-postgres psql -U guinevere -d guinevere << 'EOF' ... EOF` | Same pattern as creation |
| 11 | `sudo systemctl restart postgresql` | **N/A** — no restart needed for P0-017, but if needed: `docker restart guinevere-postgres` | Container restart vs systemd service |

### 5.2 Six Critical Adaptation Points

**#1: `sudo -u postgres` → `docker exec ... psql -U guinevere`**

Why: No `postgres` OS user on host. Container superuser is `guinevere`.

Pattern:
```bash
# Instead of:  sudo -u postgres psql -d guinevere -c "SQL"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SQL"

# For heredoc blocks:
docker exec -i guinevere-postgres psql -U guinevere -d guinevere << 'EOF'
... SQL ...
EOF
```

**#2: Connection Verification Must Specify Host/Port or Use docker exec**

Why: The bare-metal `PGPASSWORD=$CORE_PASS psql -U guinevere_core -d guinevere` uses Unix socket at default port 5432. Our Docker container is on `127.0.0.1:5433`.

**#3: pg_hba.conf paths — Not Applicable for P0-017**

Why: P0-017 does not modify pg_hba.conf. For awareness: inside the container, config files live at `/var/lib/postgresql/data/` (PGDATA), NOT `/etc/postgresql/16/main/`.

**#4: No systemd restart required**

Why: User/schema creation via SQL takes effect immediately. No container restart needed.

**#5: CHECKLIST.md line 116 missing `guinevere_backup`**

Current: `users: guinevere_core, surveillance, scheduler, readonly`
Should be: `users: guinevere_core, surveillance, scheduler, readonly, backup`

**#6: CHECKLIST.md line 117 uses wrong superuser**

Current: `sudo -u guinevere psql -d guinevere -c 'SELECT 1'`
This references a non-existent OS user/host-level psql. Should verify via:
`docker exec guinevere-postgres psql -U guinevere_core -d guinevere -c 'SELECT 1'`

---

## 6. Blocker Analysis

### 6.1 Confirmed Blockers: NONE

All pre-flight checks satisfied:
- P0-014 complete ✅ — PostgreSQL 16 container running
- Password generation capability ✅ — `openssl rand -base64 32` available on host

### 6.2 Contradictions / Deviations from StepPrompts

| Contradiction | Severity | Resolution |
|---|---|---|
| `sudo -u postgres` used but no `postgres` OS user on host | **HIGH** | Must use `docker exec guinevere-postgres psql -U guinevere` |
| Bare-metal config paths (`/etc/postgresql/16/main/...`) | **MEDIUM** | Container uses PGDATA `/var/lib/postgresql/data/`. N/A for P0-017 |
| CHECKLIST.md line 116 lists only 4 users (missing backup) | **MEDIUM** | Needs correction in CHECKLIST.md after implementation |
| CHECKLIST.md line 117 uses wrong user/connection method | **MEDIUM** | Must use docker exec pattern |
| Evidence path `docs/setup-evidence/P0/STEP-P0-017/` doesn't exist yet | **LOW** | Directory will be created at write time |
| StepPrompts evidence expects `.txt` but prior steps use `.md` summaries | **LOW** | Use both: `.txt` for raw output, `.md` for summary consistent with P0-014/P0-015/P0-016 |
| StepPrompts references ADR-018 (PgBouncer) alongside ADR-027 | **LOW** | ADR-018 is for P0-019; not directly relevant here |

---

## 7. Existing Docker Patterns from Prior Steps

### 7.1 P0-014 — PostgreSQL 16 Setup

- **SQL exec**: `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SQL"`
- **Config method**: Config via `docker run -c` flags
- **Verification**: `pg_isready`, `docker exec ... psql ... -c "SELECT version()"`
- **Evidence**: 5 files: p0-014-summary.md, verification.md, aizanta-post-check.md, postgres-status.txt, postgres-config.txt

### 7.2 P0-015 — pgvector Extension

- **Docker approach**: Custom Dockerfile `guinevere-postgres-pgvector:16` (NOT `docker exec apt install`)
- **SQL exec**: Same pattern as P0-014: `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SQL"`
- **Volume**: Bind mount `/home/guinebere/data/postgres` preserved through stop/rm/run cycle
- **Key lesson**: `docker exec apt install` does NOT survive container recreate

### 7.3 P0-016 — TimescaleDB Extension

- **Docker approach**: `docker exec` apt install + ALTER SYSTEM + `docker restart`
- **Config change**: `ALTER SYSTEM SET shared_preload_libraries = 'timescaledb'` writes to postgresql.auto.conf (persists in volume)
- **Restart**: `docker restart guinevere-postgres` (only this container, not Aizanta)
- **Key lesson**: `docker restart` is safe for config changes needing PG restart

### 7.4 Consolidated Docker Pattern for P0-017

| Action | Command |
|---|---|
| SQL execution | `docker exec -i guinevere-postgres psql -U guinevere -d guinevere << 'EOF' ... EOF` |
| Quick query | `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "QUERY"` |
| Verification | `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "\du"` |
| Connection test | `docker exec guinevere-postgres psql -U guinevere_core -d guinevere -c "SELECT 1"` |
| Restart needed? | **NO** — user/schema creation takes effect immediately |
| SOPS operations | Run on host (same as bare-metal pattern) |

---

## 8. Evidence Root

| Item | Path |
|---|---|
| Evidence root | `docs/setup-evidence/P0/STEP-P0-017/` |
| Users output | `docs/setup-evidence/P0/STEP-P0-017/pg-users.txt` |
| Schemas output | `docs/setup-evidence/P0/STEP-P0-017/pg-schemas.txt` |
| Summary (recommended) | `docs/setup-evidence/P0/STEP-P0-017/p0-017-summary.md` |
| Verification (recommended) | `docs/setup-evidence/P0/STEP-P0-017/verification.md` |
| Aizanta check (recommended) | `docs/setup-evidence/P0/STEP-P0-017/aizanta-post-check.md` |

---

## 9. Security & Boundary Notes

| Constraint | Action |
|---|---|
| No plaintext passwords in evidence | Evidence files must NOT contain password values |
| No secrets in git history | `/tmp/db-passwords.yaml` created and deleted in same step; `secrets/db-passwords.yaml` is SOPS-encrypted |
| SOPS encryption verified | Post-creation: `sops -d secrets/db-passwords.yaml` shows all 5 passwords + 5 URLs |
| Password entropy | `openssl rand -base64 32` = 256-bit random — adequate for PG auth |
| No persona/safety impact | N/A — infrastructure step |
| No Aizanta impact | Only `guinevere-postgres` container affected; all SQL targets `guinevere` database |

---

## 10. Rollback (Docker-Adapted)

```bash
# Adapted from StepPrompts lines 1853-1868
docker exec -i guinevere-postgres psql -U guinevere -d guinevere << 'EOF'
DROP USER IF EXISTS guinevere_core;
DROP USER IF EXISTS guinevere_surveillance;
DROP USER IF EXISTS guinevere_scheduler;
DROP USER IF EXISTS guinevere_readonly;
DROP USER IF EXISTS guinevere_backup;
DROP SCHEMA IF EXISTS memory CASCADE;
DROP SCHEMA IF EXISTS persona CASCADE;
DROP SCHEMA IF EXISTS surveillance CASCADE;
DROP SCHEMA IF EXISTS loops CASCADE;
DROP SCHEMA IF EXISTS financial CASCADE;
DROP SCHEMA IF EXISTS config CASCADE;
DROP SCHEMA IF EXISTS audit CASCADE;
EOF

# Also remove SOPS-encrypted passwords file
rm -f secrets/db-passwords.yaml
```

**Rollback risk**: `DROP SCHEMA ... CASCADE` drops all tables. Safe at P0-017 (no tables yet). Destructive once P3 creates tables.

---

## 11. Downstream Impact

| Step | How P0-017 Affects It |
|---|---|
| **P0-018** (Hardening) | Users created here get connection limits, pg_hba.conf auth rules |
| **P0-019** (PgBouncer) | PgBouncer auth references passwords in `secrets/db-passwords.yaml` |
| **P3** (Memory Schema) | Alembic migrations create tables in schemas established here; ALTER DEFAULT PRIVILEGES applies to future tables |

---

## 12. Pre-Execution Checklist

- [ ] `docker exec guinevere-postgres pg_isready` — container accepting connections
- [ ] `grep "public key:" /home/guinevere/secrets/age-key.txt` — age key accessible
- [ ] `sops --version` — SOPS CLI available
- [ ] `openssl rand -base64 1` — openssl available
- [ ] Verify working directory is repo root for SOPS relative paths
- [ ] Note CHECKLIST.md lines 116-117 need correction post-implementation

---

## Footer

**Source task**: STEP-P0-017 internal context analysis (pre-implementation)
**Date**: 2026-05-31
**Producer**: Guinevere (parent orchestrator)
**Method**: File-based cross-reference of StepPrompts.md, PROGRESS.md, CHECKLIST.md, ADR-031, ADR-015, and previous step evidence (P0-014/P0-015/P0-016)
**Report path**: `audit-reports/P0/STEP-P0-017/internal-context-report.md`
