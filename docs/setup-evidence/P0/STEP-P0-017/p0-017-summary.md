# P0-017 Summary — Database Users and Least Privilege

**Date**: 2026-05-31
**Step**: P0-017
**ADR**: ADR-027 (PostgreSQL), ADR-031 (Database Naming)

## What Was Done
Created 5 PostgreSQL roles with SCRAM-SHA-256 authentication, 7 application schemas, and least-privilege grants for the Guinevere database.

## Runtime Changes (VPS)
- 5 roles created in PostgreSQL: guinevere_core, guinevere_surveillance, guinevere_scheduler, guinevere_readonly, guinevere_backup
- 7 schemas created: memory, persona, surveillance, loops, financial, config, audit
- PUBLIC revoked from all schemas, schema-level USAGE grants assigned per user
- ALTER DEFAULT PRIVILEGES set for ROLE guinevere (object creator)
- `/home/guinevere/secrets/db-passwords.yaml` — SOPS encrypted with age key

## Files Created (Local)
- `secrets/db-passwords.yaml` — SOPS encrypted (2004 bytes, 600, age17cyg...)

## ADR Compliance
- ADR-027: PostgreSQL 16 on guinevere-net, SCRAM-SHA-256, least privilege
- ADR-031: Database name `guinevere`, schema isolation
- ADR-015: Secrets encrypted with SOPS+age, never plaintext in repo

## Caveats
- Connection limits at -1 (unlimited) — tighten in P0-018
- No schema-level CREATE grants yet — users cannot create own tables
- Backup user has SELECT only, needs pg_dump privileges for actual backups