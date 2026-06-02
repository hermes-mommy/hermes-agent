# Evidence Pattern Recap — P0-014/015/016 for P0-017/018/019 Fidelity

| Field | Value |
|---|---|
| **Author** | Guinevere (parent orchestrator) |
| **Date** | 2026-05-31 |
| **Purpose** | Document exact evidence patterns from P0-014/015/016 so P0-017/018/019 evidence is indistinguishable |
| **Source steps** | P0-014, P0-015, P0-016 (verified, auditor PASS) |
| **Target steps** | P0-017, P0-018, P0-019 |
| **Total P0 complete** | 17/257 overall, P0 17/29 |

---

## 1. Evidence File Inventory — P0-014/015/016

### 1.1 STEP-P0-014 (PostgreSQL 16 Deployment)

| File | Purpose |
|---|---|
| `postgres-status.txt` | Container status, connectivity, config SHOW, volume, rollback |
| `aizanta-post-check.md` | Aizanta 5/5 healthy, protected ports, Docker networks, SSH |
| `p0-014-summary.md` | Human-readable: what was done, runtime changes, validation table, rollback, caveats |
| `verification.md` | Full verification matrix: DoD, evidence artifacts, ADR compliance, AC reference, evidence gate, footer |

**Total**: 4 evidence files + 3 tracker files (PROGRESS, CHECKLIST, StepPrompts)

### 1.2 STEP-P0-015 (pgvector Extension)

| File | Purpose |
|---|---|
| `pgvector-install.txt` | Package version, \dx, extension verification, image ID |
| `pgvector-test.txt` | Cosine distance test with SQL + results, binary location, pg_isready |
| `aizanta-post-check.md` | Aizanta 5/5 healthy, protected ports unchanged |
| `p0-015-summary.md` | Human-readable summary, design decisions, rollback, caveats |
| `verification.md` | Full verification matrix |

**Total**: 5 evidence files + 3 tracker files

### 1.3 STEP-P0-016 (TimescaleDB Extension)

| File | Purpose |
|---|---|
| `timescaledb-install.txt` | Package info, shared_preload, extensions list, hypertable test summary, rollback |
| `timescaledb-test.txt` | Raw psql output: CREATE EXTENSION, hypertable CREATE/INSERT/SELECT/DROP |
| `aizanta-post-check.md` | Aizanta 5/5 healthy, protected ports post-restart |
| `p0-016-summary.md` | Human-readable summary, validation table, rollback, caveats |
| `verification.md` | Full verification matrix |

**Total**: 5 evidence files + 3 tracker files

### 1.4 Pattern Summary

| Category | P0-014 | P0-015 | P0-016 |
|---|---|---|---|
| Raw command output `.txt` | 1 (postgres-status) | 2 (install + test) | 2 (install + test) |
| Aizanta check `.md` | 1 | 1 | 1 |
| Summary `.md` | 1 | 1 | 1 |
| Verification `.md` | 1 | 1 | 1 |
| **Evidence total** | **4** | **5** | **5** |
| Tracker files | 3 | 3 | 3 |

Pattern: 4-5 evidence files per step. P0-014 (container creation) has 1 .txt. Extension steps (P0-015, P0-016) split into install + test logs.

---

## 2. verification.md Template (12 Sections)

Every verification.md follows this exact structure:

### 2.1 Frontmatter
```
# STEP-P0-NNN -- <Title> Verification

| Field | Value |
|---|---|
| **Step** | P0-NNN |
| **Type** | Infrastructure / Database / Security |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |
```

### 2.2 What Was Done
One paragraph describing deployment/installation/configuration.

### 2.3 Files Changed
Two subsections: **Remote (VPS)** and **Local (repo)**. Local always ends with:
```
| `PROGRESS.md` | Updated counters |
| `CHECKLIST.md` | Checked P0-NNN line |
| `stepprompts/StepPrompts.md` | Updated status |
```

### 2.4 Validation Results
Raw command output blocks with inline verdicts. Minimum: version, functional test, connectivity, Aizanta health, ports.

### 2.5 Evidence Artifacts
Table: File | Description.

### 2.6 Shared VPS Impact / Aizanta Health
Paragraph/table on Aizanta containers, ports, networks.

### 2.7 ADR Compliance
Table: ADR | Requirement | Status.

### 2.8 AC Reference
Table: AC ID | Description | Status.

### 2.9 Rollback / Re-run Safety
Code block with commands. Note on idempotency.

### 2.10 Design Decisions / Caveats
Numbered list.

### 2.11 Evidence Gate
```
| Gate | Status |
|---|---|
| Parent verification | PASS -- [summary] |
| Evidence files | N created |
| Diagnostics | Clean |
| Secret scan | No matches |
| Tracker sync | PROGRESS, CHECKLIST, StepPrompts synced |
| Independent auditor gate | PASS -- audit-reports/P0/STEP-P0-NNN/step-p0-NNN-auditor-report.md |
```

### 2.12 Footer
```
**Source task**: STEP-P0-NNN (from stepprompts/StepPrompts.md)
**Date**: 2026-05-31
**Implementer**: Guinevere (parent orchestrator, via ...)
**Validation method**: Live SSH command execution + output capture
```

---

## 3. lsp_diagnostics Proof

All auditor reports confirm 0 errors, 0 warnings on all tracker files:

| File | P0-014 | P0-015 | P0-016 |
|---|---|---|---|
| PROGRESS.md | Clean | Clean | Clean |
| CHECKLIST.md | Clean | Clean | Clean |
| stepprompts/StepPrompts.md | Clean | Clean | Clean |

Run lsp_diagnostics on all 3 tracker files after edit. Report in both verification.md (Evidence Gate) and auditor report (dedicated section).

---

## 4. Tracker Sync Patterns

### 4.1 PROGRESS.md Counter Math

| Step | Before Total | After Total | Before P0 | After P0 |
|---|---|---|---|---|
| P0-014 | 14/257 | 15/257 | 14/29 | 15/29 |
| P0-015 | 15/257 | 16/257 | 15/29 | 16/29 |
| P0-016 | 16/257 | 17/257 | 16/29 | 17/29 |

Rule: Both counters increment by **exactly +1**. Denominators are fixed.

**Fields to update**:
- Line 12: `| **Completed** | NN / 257 (X.X%) |`
- Line 27: `| P0 | Infrastructure | ... | NN/29 | ... |`

**Target values for next steps**:

| Step | Total | P0 | Percentage |
|---|---|---|---|
| P0-017 | 18/257 | 18/29 | 7.0% |
| P0-018 | 19/257 | 19/29 | 7.4% |
| P0-019 | 20/257 | 20/29 | 7.8% |

### 4.2 CHECKLIST.md Lines (Current: 114-119)

```
114: - [x] P0-014: Docker guinevere-postgres on guinevere-net:5433 ...
115: - [x] P0-015: ... vector ...
116: - [ ] P0-017: ... users: guinevere_core, surveillance, scheduler, readonly
117: - [ ] P0-017: ... SELECT 1 ...
118: - [ ] P0-018: pg_hba.conf -> local + SSL only; SHOW ssl -> on
119: - [ ] P0-019: systemctl status pgbouncer -> active; pooler test -> OK
```

**Update pattern**: Change `[ ]` to `[x]` on the step's line(s). For P0-017: both lines 116 AND 117. Note: line 116 currently lists 4 users -- update to include `guinevere_backup` (5 users total).

### 4.3 StepPrompts.md Status

Each step header has:
```
**Status:** ⬜ Not Started  -->  **Status:** ✅ Completed
```

Change the status line only. Do not change git commit line (remains `chore(P0): pending`).

| Step | StepPrompts line |
|---|---|
| P0-017 | ~line 1730 |
| P0-018 | ~line 1886 |
| P0-019 | ~line 1990 |

---

## 5. Evidence Manifest -- P0-017 (PostgreSQL Users)

### 5.1 Files to Create (6 files)

| # | Path | Content |
|---|---|---|
| 1 | `docs/setup-evidence/P0/STEP-P0-017/pg-users.txt` | Raw \du output + role verification queries |
| 2 | `docs/setup-evidence/P0/STEP-P0-017/pg-schemas.txt` | Raw \dn output + schema privilege queries |
| 3 | `docs/setup-evidence/P0/STEP-P0-017/pg-connection-test.txt` | Connection tests as each user (SELECT 1), privilege restriction tests |
| 4 | `docs/setup-evidence/P0/STEP-P0-017/p0-017-summary.md` | Summary: users, schemas, password encryption, rollback |
| 5 | `docs/setup-evidence/P0/STEP-P0-017/verification.md` | Full 12-section verification matrix |
| 6 | `docs/setup-evidence/P0/STEP-P0-017/aizanta-post-check.md` | Aizanta health (no containers touched -- SQL-only step) |

Also creates: `secrets/db-passwords.yaml` (SOPS-encrypted, NOT evidence)

### 5.2 Docker Adaptation
- All `sudo -u postgres psql` becomes `docker exec guinevere-postgres psql -U guinevere -d guinevere`
- Passwords generated on host with `openssl rand -base64 32`
- SOPS operations on host

### 5.3 Verification
- \du shows 5 users: guinevere_core, guinevere_surveillance, guinevere_scheduler, guinevere_readonly, guinevere_backup
- \dn shows 7 schemas: memory, persona, surveillance, loops, financial, config, audit
- guinevere_core SELECT 1 works, has ALL on app schemas
- guinevere_surveillance can INSERT but NOT SELECT
- `sops -d secrets/db-passwords.yaml` decrypts all 5 passwords
- Aizanta 5/5 healthy

---

## 6. Evidence Manifest -- P0-018 (pg_hba.conf Hardening)

### 6.1 Files to Create (6 files)

| # | Path | Content |
|---|---|---|
| 1 | `docs/setup-evidence/P0/STEP-P0-018/pg-hba.conf` | The hardened pg_hba.conf content (for reference) |
| 2 | `docs/setup-evidence/P0/STEP-P0-018/pg-hba-verify.txt` | pg_hba_file_rules output, no errors, no trust entries |
| 3 | `docs/setup-evidence/P0/STEP-P0-018/pg-security.txt` | Connection limits, password_encryption, SSL status, connect test |
| 4 | `docs/setup-evidence/P0/STEP-P0-018/p0-018-summary.md` | Summary: pg_hba.conf changes, connection limits, audit logging |
| 5 | `docs/setup-evidence/P0/STEP-P0-018/verification.md` | Full 12-section verification matrix |
| 6 | `docs/setup-evidence/P0/STEP-P0-018/aizanta-post-check.md` | Aizanta health (only guinevere-postgres reloaded) |

### 6.2 Docker Adaptation
- pg_hba.conf inside container: `/var/lib/postgresql/data/pg_hba.conf`
- Method: docker cp hardened config, then `SELECT pg_reload_conf()`
- Connection limits via docker exec psql
- NO systemctl restart -- use pg_reload_conf()

### 6.3 Verification
- `pg_hba_file_rules WHERE error IS NOT NULL` = 0 rows
- `pg_hba_file_rules WHERE method = 'trust'` = 0 rows
- `SHOW password_encryption` = scram-sha-256
- Connection limits applied per role
- Reject rules catch non-local connections
- Aizanta 5/5 healthy

---

## 7. Evidence Manifest -- P0-019 (PgBouncer)

### 7.1 Files to Create (6 files)

| # | Path | Content |
|---|---|---|
| 1 | `docs/setup-evidence/P0/STEP-P0-019/pgbouncer-status.txt` | systemctl status, ss -tlnp | grep 5434, pool stats |
| 2 | `docs/setup-evidence/P0/STEP-P0-019/pgbouncer.ini` | Complete pgbouncer.ini configuration |
| 3 | `docs/setup-evidence/P0/STEP-P0-019/pgbouncer-test.txt` | Connection via 5434, SHOW POOLS, user auth test |
| 4 | `docs/setup-evidence/P0/STEP-P0-019/p0-019-summary.md` | Summary: install, config, userlist, pooling params |
| 5 | `docs/setup-evidence/P0/STEP-P0-019/verification.md` | Full 12-section verification matrix |
| 6 | `docs/setup-evidence/P0/STEP-P0-019/aizanta-post-check.md` | Aizanta health (new service, no containers touched) |

### 7.2 Docker Adaptation
- PgBouncer installed on **host** (not containerized) -- matches existing host-level service pattern
- Binds 127.0.0.1:5434 only
- userlist.txt uses SOPS-decrypted passwords

### 7.3 Verification
- systemctl status pgbouncer = active
- ss -tlnp | grep 5434 shows pgbouncer listening
- psql via port 5434 returns SELECT 1
- SHOW POOLS shows pool stats
- Direct PG on 5433 still works (PgBouncer is optional)
- Aizanta 5/5 healthy

---

## 8. Auditor Report Convention

Each step's independent auditor report at:
```
audit-reports/P0/STEP-P0-NNN/step-p0-NNN-auditor-report.md
```

Existing reports: step-p0-014-auditor-report.md, step-p0-015-auditor-report.md, step-p0-016-auditor-report.md

Pre-implementation reports already exist for P0-017 and P0-018:
- `audit-reports/P0/STEP-P0-017/internal-context-report.md`
- `audit-reports/P0/STEP-P0-017/external-pg-user-best-practices.md`
- `audit-reports/P0/STEP-P0-018/external-pg-hardening-report.md`

---

## 9. Evidence Gate Checklist

- [ ] verification.md follows the 12-section structure
- [ ] Frontmatter: Step, Type, Date, Implementer, Status
- [ ] Files Changed: Remote + Local including 3 trackers
- [ ] Validation: raw command output with inline verdicts
- [ ] Aizanta health: 5/5 containers, protected ports
- [ ] Evidence Artifacts table
- [ ] ADR Compliance table
- [ ] Rollback commands included and accurate
- [ ] Design Decisions / Caveats numbered
- [ ] Evidence Gate: all PASS
- [ ] Secret scan: zero plaintext secrets
- [ ] Footer: source task, date, implementer, method
- [ ] lsp_diagnostics clean on 3 tracker files
- [ ] PROGRESS counter math: +1 total, +1 P0
- [ ] CHECKLIST: [ ] to [x] on correct lines
- [ ] StepPrompts: Not Started to Completed
- [ ] Evidence files exist at claimed paths
- [ ] No plaintext secrets in evidence
- [ ] Auditor report path follows convention

---

*Generated from analysis of P0-014/P0-015/P0-016 evidence files, PROGRESS.md, CHECKLIST.md, stepprompts/StepPrompts.md, and auditor reports. Date: 2026-05-31.*
