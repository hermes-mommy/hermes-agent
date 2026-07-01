# P19-012 Production Deploy Audit: Security / Secrets

**Audit ID:** P19-012-AUDIT-SEC-ROUND1
**Date:** 2026-06-27
**Auditor:** Independent (automated + manual)
**Scope:** Security, secrets exposure, secrets-vault architecture, HARD STOP integrity
**Standard:** Zero-tolerance for secret leaks in evidence; hard-rejection for scoped HARD STOP

---

## 1. Audit Scope and Methodology

This audit covers the P19-012 production deploy wave: backup, schema migration, service deploy, and smoke tests. All evidence files under `docs/setup-evidence/P19/evidence/production-deploy/` were scanned. Deploy scripts (`scripts/p19_*.py`) and the `ProjectSecretsVault` source (`src/projects/secrets_vault.py`) were reviewed. VPS file permissions were verified via SSH. Redis was checked for project-scoped HARD STOP violations.

**Files audited:**
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-backup-evidence.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-schema-migration-evidence.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-service-deploy-evidence.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-runtime-preflight.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-deploy-plan.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-012-smoke-test.md`
- `docs/setup-evidence/P19/evidence/production-deploy/p19-surgical-ddl.sql`
- `scripts/p19_001_deploy.py`
- `scripts/p19_002_003_deploy.py`
- `scripts/p19_smoke_test.py`
- `src/projects/secrets_vault.py`
- `adr/ADR-052-multi-project-context.md` (Per-project secrets isolation section)
- `src/discord/cmd_project.py` (HARD STOP guard)
- `src/knowledge_graph/consent/audit.py` (global safety event enforcement)
- `src/gmail/router.py` (HARD STOP check)

**Scan patterns used:**
- Discord bot tokens (regex: 24.6.27 char pattern)
- `password=`, `PGPASSWORD`, `REDIS_PASSWORD`, `passwd=`, `secret_key`, `API_KEY`, `api_key`
- `SOPS`, `age_key`, `private_key`
- GitHub tokens (`ghp_`), OpenAI keys (`sk-`), GitLab tokens (`glpat-`), Slack tokens (`xox[bpors]-`)
- AWS keys (`AKIA`)
- JWT tokens (`eyJ`)
- RSA/PGP/SSH private key headers
- `DATABASE_URL`, `REDIS_URL`, `postgres://`, `postgresql://` (credential-bearing URLs)

---

## 2. Individual Check Results

### SEC-01: No secrets in evidence files

**Verdict: PASS**

All 7 evidence files under `docs/setup-evidence/P19/evidence/production-deploy/` were scanned with 12 distinct secret-pattern regexes. Zero matches found for any secret-bearing pattern.

Observations:
- `p19-012-runtime-preflight.md` references `DATABASE_URL` by name only ("points to `guinevere` DB"), not by value.
- `p19-012-smoke-test.md` includes Discord message ID `1519135545501028549` -- this is a public Discord snowflake for the dashboard message, not a secret.
- `p19-012-backup-evidence.md` references backup path `/tmp/p19_backup_20260626_2145.dump` and connection parameters (host, port, user) -- no credentials.
- `p19-surgical-ddl.sql` contains only DDL and the default project UUID -- no credentials.

No bot tokens, database passwords, Redis passwords, API keys, SOPS/age keys, private keys, AWS keys, JWTs, or PATs found in any evidence artifact.

---

### SEC-02: No hardcoded secrets in deploy scripts

**Verdict: PASS**

All three deploy scripts (`p19_001_deploy.py`, `p19_002_003_deploy.py`, `p19_smoke_test.py`) follow the same pattern:

```python
from dotenv import load_dotenv
load_dotenv('/home/guinevere/code/guinevere/.env.core')
```

- Scripts load credentials from `.env.core` at runtime via `dotenv`.
- The `DATABASE_URL` and `REDIS_URL` are read from environment via `os.environ`.
- No hardcoded connection strings, passwords, tokens, or keys anywhere in the scripts.
- The default project UUID `00000000-0000-0000-0000-000000000001` is a public identifier, not a secret.

---

### SEC-03: .env.core permissions 600

**Verdict: PASS**

VPS verification (SSH):
```
-rw------- 1 guinevere guinevere 739 Jun 23 19:24 /home/guinevere/code/guinevere/.env.core
```

Mode `-rw-------` = `600`. Owner (`guinevere`) read/write only. Group and others have zero access. This matches the smoke test's own check (`oct(st.st_mode)[-3:] == '600'`).

---

### SEC-04: Backup file not world-readable, no plaintext secrets

**Verdict: FAIL (MEDIUM)**

**Finding 1 -- Backup file is world-readable (MEDIUM):**

VPS verification:
```
-rw-rw-r-- 1 guinevere guinevere 1235417322 Jun 26 21:57 /tmp/p19_backup_20260626_2145.dump
```

Mode `-rw-rw-r--` = `664`. The file is group-readable and **world-readable**. Any user on the VPS can read the 1.2 GB backup dump. While this is a PostgreSQL custom-format dump (not plaintext SQL), it contains the full database content including `consent.consent_ledger`, `surveillance.events`, and all memory tables. `pg_restore` can extract table data from this format.

**Remediation:** Run `chmod 600 /tmp/p19_backup_20260626_2145.dump` on the VPS, or better, move the backup to the guinevere user's home directory with proper permissions.

**Finding 2 -- Backup TOC is clean (PASS):**

`pg_restore -l` output shows only schema/table/index metadata. No env vars, no plaintext credentials, no secret-like data in the table of contents. The backup is a proper `pg_dump -F c` custom archive.

**Note:** The backup evidence file itself (`p19-012-backup-evidence.md`) does not document the file permissions. The smoke test (`p19_smoke_test.py`) checks `.env.core` permissions but does NOT check the backup file permissions. This is a gap.

---

### SEC-05: ProjectSecretsVault architecture sound

**Verdict: PASS**

`src/projects/secrets_vault.py` implements a clean in-memory vault:

| Property | Status |
|---|---|
| In-memory only (no disk I/O) | PASS -- `self._store: dict[ProjectId, dict[str, str]]` |
| Keyed by `project_id` | PASS -- `vault.get(project_id, domain)` lookup |
| Thread-safe | PASS -- `threading.RLock` guards all public methods |
| Refuses unknown project IDs | PASS -- `get()` returns `None` when `project_id` not in `_store` |
| No cross-project leak | PASS -- each project_id maps to its own dict; structurally impossible to leak |
| Defensive copy on load | PASS -- `dict(secrets)` copy prevents external mutation |
| Unload support | PASS -- `unload(project_id)` removes from memory |
| Audit support | PASS -- `domains(project_id)` lists loaded domains |
| No env var dependency | PASS -- vault is a pure container; callers provide decrypted secrets |
| Documented encrypted source | ADR-052 specifies `secrets/projects/{project_id}/*.enc.yaml` (SOPS/age) |

The vault does NOT load, decrypt, or persist anything itself. This is correct -- it is a pure isolation container. Decryption and loading are the responsibility of deploy-time wiring (not yet active since `feature:projects:enabled` is OFF).

**Note:** The `secrets/projects/` directory does not yet exist on the VPS. This is expected since the feature flag is OFF and no project has loaded secrets yet. The architecture is ready for future activation.

---

### SEC-06: HARD STOP global (not project-scoped)

**Verdict: PASS**

This is a **hard-rejection criterion** per ADR-052. Three independent verification paths:

**Path 1 -- src/projects/ module scan:**
Grep for `hard_stop` and `life_kernel:hard_stop` in `src/projects/` returned **zero matches**. The P19 projects module does not reference, scope, or partition HARD STOP in any way.

**Path 2 -- Cross-codebase scan:**
Grep for `hard_stop.*project` and `project.*hard_stop` patterns across all `src/` found only three references, all correct:

1. `src/discord/cmd_project.py:174` -- Reads the global `life_kernel:hard_stop` key and BLOCKS project switch if active. Correct behavior.
2. `src/knowledge_graph/consent/audit.py:127` -- Comment: "Global safety events (HARD_STOP, DNR) MUST pass project_id=None." Correct enforcement.
3. `src/gmail/router.py:248` -- Checks global hard_stop and blocks Gmail routing. Correct behavior.

None of these scope HARD STOP to a project. All read the single global key.

**Path 3 -- VPS Redis verification:**
```
redis-cli KEYS '*hard_stop*'  -->  (empty)
redis-cli GET 'life_kernel:hard_stop'  -->  (nil)
```

No project-scoped hard_stop keys exist. The global `life_kernel:hard_stop` is clear (not set). No `p19:*` keys that could indicate project-scoped hard_stop attempts.

**Conclusion:** HARD STOP remains a single global Redis key (`life_kernel:hard_stop`). No P19 code scopes, partitions, or duplicates it. Hard-rejection criterion: SATISFIED.

---

### SEC-07: No raw surveillance/personal data in artifacts

**Verdict: PASS**

Grep for `surveillance`, `raw_data`, `personal`, `PII`, `email`, `phone`, `address` across all evidence files returned only schema/table/column name references:

- `surveillance.events` -- table name referenced in migration context
- `consent.consent_ledger` -- table name referenced in migration context

No raw surveillance payloads, no personal data, no PII, no email addresses, no phone numbers, no physical addresses were found in any evidence artifact. The evidence files contain only schema metadata, service status, and test results.

---

### SEC-08: Consent/surveillance boundary preserved

**Verdict: PASS**

The P19 schema migration correctly implements the consent/surveillance boundary per ADR-052:

| Table | project_id | Scope | Correct? |
|---|---|---|---|
| `consent.consent_ledger` | Nullable (global rows use NULL) | Project-scoped consent gets project_id; safety scopes (persona, emergency, HARD STOP, safe-word) stay global with NULL | YES |
| `surveillance.events` | Nullable | Project-scoped surveillance gets project_id; global surveillance uses NULL | YES |
| `audit.audit_trail` | Nullable + chain_version | Safety audit events pass project_id=None | YES |

Code enforcement:
- `src/knowledge_graph/consent/audit.py:127` explicitly requires `project_id=None` for global safety events (HARD_STOP, DNR). This prevents project-scoped consent from leaking into global safety scope.
- The 6 nullable tables (`audit.audit_trail`, `consent.consent_ledger`, `surveillance.events`, `memory.kg_edges`, `memory.kg_episodes`, `memory.kg_consent_audit`) are correctly nullable per ADR-052's global-capable designation.

The boundary is structurally enforced: project-scoped consent gets a `project_id` FK, global safety scopes use `project_id = NULL`. No code path can scope a safety-critical consent entry to a project.

---

## 3. Summary Matrix

| Check | ID | Verdict | Severity |
|---|---|---|---|
| No secrets in evidence files | SEC-01 | **PASS** | -- |
| No hardcoded secrets in deploy scripts | SEC-02 | **PASS** | -- |
| .env.core permissions 600 | SEC-03 | **PASS** | -- |
| Backup file permissions + no plaintext secrets | SEC-04 | **FAIL** | MEDIUM |
| ProjectSecretsVault architecture sound | SEC-05 | **PASS** | -- |
| HARD STOP global (not project-scoped) | SEC-06 | **PASS** | -- |
| No raw surveillance/personal data in artifacts | SEC-07 | **PASS** | -- |
| Consent/surveillance boundary preserved | SEC-08 | **PASS** | -- |

**Overall: 7/8 PASS, 1 FAIL (SEC-04 -- MEDIUM)**

---

## 4. Findings Detail

### FINDING-01: Backup file world-readable (SEC-04)

| Field | Value |
|---|---|
| Severity | MEDIUM |
| Check | SEC-04 |
| File | `/tmp/p19_backup_20260626_2145.dump` (VPS) |
| Actual permission | `-rw-rw-r--` (664) |
| Required permission | `-rw-------` (600) |
| Risk | Any local user on the VPS can read the full database backup via `pg_restore`. The backup contains consent, surveillance, and memory data. |
| Remediation | `chmod 600 /tmp/p19_backup_20260626_2145.dump` |
| Recurrence prevention | Add backup permission check to `p19_smoke_test.py` or deploy runbook |

### FINDING-01b: No backup permission check in smoke tests (SEC-04)

| Field | Value |
|---|---|
| Severity | LOW |
| Check | SEC-04 (gap) |
| Issue | `p19_smoke_test.py` SMOKE 7 checks `.env.core` permissions but does NOT check backup file permissions |
| Remediation | Add `os.stat('/tmp/p19_backup_20260626_2145.dump').st_mode` check to smoke test |

---

## 5. Architectural Assessment: ProjectSecretsVault

The `ProjectSecretsVault` architecture is sound and correctly implements ADR-052's per-project secrets isolation contract:

**Design strengths:**
- Pure in-memory container with zero disk I/O -- no secret persistence risk
- Thread-safe via `threading.RLock` -- safe for concurrent async/sync access
- Structural isolation: `dict[ProjectId, dict[str, str]]` makes cross-project access impossible by construction
- Defensive copy on load prevents external mutation of the vault's internal state
- Explicit `unload()` for secret lifecycle management
- No env var dependency -- avoids the cross-project leak that `GUINEVERE_{PROJECT}_{KEY}` env vars would allow in a single process

**Forward-compliance notes:**
- The `secrets/projects/` directory does not exist on VPS yet. This is expected since the feature flag is OFF.
- When projects are activated, secrets MUST be stored as `secrets/projects/{project_id}/*.enc.yaml` encrypted with SOPS/age.
- The vault does NOT enforce encryption -- callers are responsible for providing decrypted secrets. This is acceptable given the architecture's separation of concerns but means the encryption guarantee lives in the loader, not the vault.

---

## 6. HARD STOP Integrity Verification

HARD STOP integrity is a **hard-rejection criterion** per ADR-052. This audit verified it through three independent paths:

1. **Source scan:** Zero references to `hard_stop` in `src/projects/`. The P19 module does not touch, scope, or partition HARD STOP.
2. **Cross-codebase scan:** Three references in other modules all read the global `life_kernel:hard_stop` key correctly. No project-scoped variants.
3. **VPS Redis:** No project-scoped hard_stop keys exist. The global key is clear.

The HARD STOP architecture is intact. The single Redis key `life_kernel:hard_stop` halts ALL projects. Project-local pause (`project:{project_id}:paused`) is a distinct, weaker mechanism that does not satisfy HARD STOP requirements.

---

## 7. Secrets Exposure Risk Assessment

| Vector | Risk | Status |
|---|---|---|
| Evidence files (.md) | Secret leak via copy-paste from terminal | MITIGATED -- zero secrets found |
| Deploy scripts (.py) | Hardcoded credentials | MITIGATED -- all use dotenv |
| Backup file (.dump) | Database content readable by local users | **EXPOSED** -- 664 permissions |
| .env.core | Credential file world-readable | MITIGATED -- 600 permissions |
| DDL scripts (.sql) | Schema metadata leak | MITIGATED -- DDL only, no data |
| Smoke test output | Credential echo to stdout | MITIGATED -- no secrets printed |
| Vault architecture | Cross-project secret leak | MITIGATED -- structural isolation |

---

## 8. Compliance with ADR-052 Security Requirements

| ADR-052 Requirement | Status | Evidence |
|---|---|---|
| Per-project secrets in-memory vault | IMPLEMENTED | `src/projects/secrets_vault.py` |
| Secrets stored as `*.enc.yaml` (SOPS/age) | ARCHITECTURE-READY (not yet deployed) | Directory does not exist; feature flag OFF |
| `vault.get(project_id, domain)` API | IMPLEMENTED | Returns None for unknown projects |
| HARD STOP global, single key | VERIFIED | Source scan + Redis verification |
| Project-scoped consent gets project_id | VERIFIED | Schema: nullable project_id on consent_ledger |
| Safety scopes stay global (project_id=NULL) | VERIFIED | Code: `audit.py:127` enforces None for safety events |
| Env vars only for single-project systemd | CORRECT | Scripts use .env.core, not project-prefixed vars |

---

## 9. Recommendations

1. **IMMEDIATE:** Fix backup file permissions on VPS: `chmod 600 /tmp/p19_backup_20260626_2145.dump`
2. **SHORT-TERM:** Add backup file permission check to `p19_smoke_test.py` SMOKE 7
3. **SHORT-TERM:** Add deploy runbook step to set backup permissions after `pg_dump`
4. **MEDIUM-TERM:** When `feature:projects:enabled` is turned ON, verify that secrets loader uses SOPS/age decryption (not plaintext YAML)
5. **MEDIUM-TERM:** Add integration test that verifies `vault.get(project_a, domain)` returns `None` when called with `project_b`'s domain

---

## 10. Audit Trail

| Step | Method | Result |
|---|---|---|
| Evidence file scan (7 files) | Grep with 12 secret patterns | 0 matches |
| Deploy script scan (3 files) | Grep + manual review | 0 hardcoded secrets |
| .env.core permission check | SSH `ls -la` | 600 PASS |
| Backup file permission check | SSH `ls -la` | 664 **FAIL** |
| Backup TOC check | SSH `pg_restore -l` | No plaintext secrets |
| SecretsVault source review | Manual code review | Sound architecture |
| HARD STOP source scan | Grep across src/ | No scoping violations |
| HARD STOP Redis check | SSH redis-cli | No project-scoped keys |
| Raw data scan | Grep for PII patterns | No personal data |
| Consent boundary review | Schema + code review | Correctly scoped |

---

## 11. Limitations

- This audit scanned the local repository files. VPS runtime state was verified via SSH for permissions and Redis keys only.
- The backup file contains the full database but was not decrypted/extracted to scan for embedded secrets -- only the TOC was inspected.
- The `secrets/projects/` directory does not exist on VPS, so the SOPS/age encryption at rest could not be verified.
- The feature flag is OFF, so the `ProjectSecretsVault` is not loaded at runtime. Runtime behavior under flag-ON was not tested.

---

## 12. Final Verdict

**VERDICT: NEEDS-REVIEW**

7 of 8 checks pass. One MEDIUM finding (SEC-04: backup file world-readable at 664 instead of 600). No CRITICAL findings. No secrets were exposed in evidence files or deploy scripts. The ProjectSecretsVault architecture is sound. HARD STOP remains global and unviolated.

**Blocking action before audit can be marked PASS:**
- Fix `/tmp/p19_backup_20260626_2145.dump` permissions to 600 on VPS.

**Non-blocking recommendations:**
- Add backup permission check to smoke test.
- Add backup permission step to deploy runbook.
