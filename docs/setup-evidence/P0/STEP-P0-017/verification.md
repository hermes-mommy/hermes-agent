# STEP-P0-017 — Verification

**Step**: P0-017 — Database Users, Schemas, and Least Privilege
**Date**: 2026-05-31
**Status**: PASS, independent auditor gate passed

---

## 1. What Was Done
Created 5 PostgreSQL application roles (guinevere_core, guinevere_surveillance, guinevere_scheduler, guinevere_readonly, guinevere_backup) with SCRAM-SHA-256 passwords on the existing guinevere-postgres Docker container. Created 7 schemas (memory, persona, surveillance, loops, financial, config, audit). Applied least-privilege grants: REVOKE PUBLIC, schema-level USAGE per role, ALTER DEFAULT PRIVILEGES for ROLE guinevere (object creator). Passwords encrypted with SOPS+age to `/home/guinevere/secrets/db-passwords.yaml` (600, guinevere:guinevere).

## 2. Files Changed
**Local**:
- `secrets/db-passwords.yaml` — NEW (SOPS encrypted, not plaintext)

**Remote (VPS)**:
- `/home/guinevere/secrets/db-passwords.yaml` — SOPS encrypted (2004 bytes, 600, guinevere:guinevere)

No other files changed. Container NOT restarted (SQL-only operations).

## 3. Validation Results

### Roles
```
        rolname         | rolcanlogin | rolconnlimit
------------------------+-------------+--------------
 guinevere_backup       | t           |           -1
 guinevere_core         | t           |           -1
 guinevere_readonly     | t           |           -1
 guinevere_scheduler    | t           |           -1
 guinevere_surveillance | t           |           -1
(5 rows)
```

### Schemas
```
   nspname
--------------
 audit
 config
 financial
 loops
 memory
 persona
 surveillance
(7 rows)
```

### Connection Tests (5/5 PASS)
```
guinevere_core:          PASS (current_user=guinevere_core, current_database=guinevere)
guinevere_surveillance:  PASS (current_user=guinevere_surveillance)
guinevere_scheduler:     PASS (current_user=guinevere_scheduler)
guinevere_readonly:      PASS (current_user=guinevere_readonly)
guinevere_backup:        PASS (current_user=guinevere_backup)
```

### SOPS Encryption
```
File: /home/guinevere/secrets/db-passwords.yaml
Size: 2004 bytes
Owner: guinevere:guinevere (600)
SHA256: 952c5fd9e843545f03fa74baaa4dc81295441ceb21b32a44dd0c2fbb51b898da
Decrypt test: 5 keys present (structure valid)
```

No plaintext passwords in evidence.

## 4. Evidence Artifacts
- `db-users-list.txt` — roles, schemas, grants, SOPS metadata
- `db-users-test.txt` — connection test results
- `aizanta-post-check.md` — Aizanta health verification
- `p0-017-summary.md` — summary and caveats

## 5. Shared VPS Impact
- Aizanta 5/5 containers healthy: bot, nginx, frontend, postgres:16-alpine, redis
- Protected ports unchanged: 127.0.0.1:6379, 100.94.104.22:80, 127.0.0.1:5432
- No Aizanta Docker networks/containers/volumes touched
- `/home/aizanta/` untouched
- guinevere-postgres container NOT restarted

## 6. ADR Compliance
- ADR-027 (PostgreSQL): Docker deployment, SCRAM-SHA-256, least privilege
- ADR-031 (Database Naming): DB `guinevere`, schema isolation
- ADR-015 (Secrets): SOPS+age encryption, no plaintext in repo

## 7. AC Reference
- AC-CORE-001: Database `guinevere` accessible with proper auth
- AC-DATA-001: Persistent schemas for data classification
- AC-SEC-001: SCRAM-SHA-256 auth, no plaintext secrets

## 8. Rollback / Re-run Safety
- Roles: `DROP ROLE IF EXISTS guinevere_*` (destroys dependent objects)
- Schemas: `DROP SCHEMA IF EXISTS ... CASCADE`
- SOPS file: idempotent overwrite, `shred -u` plaintext temp files
- Re-run safe: DROP ROLE IF EXISTS before CREATE (idempotent)

## 9. Design Decisions / Caveats
- Connection limits at -1 (unlimited) — tighten in P0-018 hardening
- No schema-level CREATE grants — users cannot create own tables (intentional, guinevere owns all objects)
- Backup user has SELECT only — needs `pg_dump` privileges for actual backups
- All users have access to public schema USAGE (intentional, least surprise)

## 10. Evidence Gate
| Gate | Status |
|---|---|
| Parent verification | PASS |
| LSP diagnostics | Clean |
| Secret scan | No plaintext keys found |
| Aizanta guardrails | 5/5 healthy |
| Independent auditor gate | PASS — 10/10 DoD criteria, 0 blocking findings, Aizanta 5/5 healthy |

## 11. Footer
- Source task: STEP-P0-017
- Implementer: Guinevere (Sisyphus agent)
- Auditor: PASS (bg_a341ded9)
- Date: 2026-05-31