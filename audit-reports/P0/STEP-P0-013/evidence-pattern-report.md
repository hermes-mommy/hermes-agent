# Evidence Pattern Reference Report — P0-013 & P0-014

| Field | Value |
|---|---|
| **Report Type** | Combined evidence pattern reference |
| **Source Steps** | P0-010, P0-011, P0-012 (canonical P0 evidence) |
| **Target Steps** | P0-013, P0-014 |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (parent orchestrator) |
| **Status** | Reference document — no changes to actual evidence or trackers |

---

## 1. Verification.md Schema (Canonical 10-12 Sections)

Extracted from P0-010 (verification.md — PASS), P0-011 (verification.md — NEEDS REVIEW), and P0-012 (verification.md — PASS after re-audit).

### 1.1 Section Inventory

| # | Section | Required | P0-010 | P0-011 | P0-012 | Notes |
|---|---|---|---|---|---|---|
| 1 | Header + metadata table | Yes | L1-9 | L1-9 | L1-9 | Step, Type, Date, Implementer, Status |
| 2 | What Was Done | Yes | L11-13 | L11-13 | L11-13 | 1-2 paragraph summary |
| 3 | Files Changed (Remote + Local) | Yes | L15-28 | L15-29 | L15-31 | Two tables: Remote (VPS), Local (repo). Includes tracker files. |
| 4 | Validation Results | Yes | L30-70 | L31-68 | L33-62 | Command outputs with PASS/FAIL labels; indented code blocks |
| 5 | Evidence Artifacts | Yes | L72-81 | L70-76 | L64-71 | Table: File + Description |
| 6 | Shared VPS Impact | Yes | L83-87 | L78-81 | L73-76 | Aizanta impact + resource notes |
| 7 | ADR Compliance | Yes | L89-94 | L84-88 | L78-83 | Table: ADR + Status |
| 8 | AC Reference | Yes | L96-100 | L90-94 | L85-89 | Table: AC + Status |
| 9 | Rollback / Re-run Safety | Yes | L102-108 | L96-99 | L91-95 | Bash commands or prose |
| 10 | Design Decisions / Caveats | Yes | L110-115 | L101-107 | L97-104 | Numbered items 1..N |
| 11 | Evidence Gate | Yes | L117-125 | L109-118 | L106-114 | Table: parent verification, evidence files, diagnostics, secret scan, tracker sync, auditor gate |
| 12 | Footer | Yes | L127-132 | L120-125 | L116-121 | Source task, Date, Implementer, Validation method |

### 1.2 Header Format

```markdown
# STEP-P0-NNN — <Step Title> Verification

| Field | Value |
|---|---|
| **Step** | P0-NNN |
| **Type** | Security / Infrastructure / Database |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |
```

- P0-011 initially had "PASS, pending independent auditor gate"
- P0-010, P0-012 have "PASS, independent auditor gate passed"
- Recommendation: start with "PASS, pending independent auditor gate" then update after audit

### 1.3 Files Changed Format

```markdown
### Remote (VPS)
| File | Action |
|---|---|
| /path/on/vps/file | Created (600, owner:group) |

### Local (repo)
| File | Action |
|---|---|
| docs/setup-evidence/P0/STEP-P0-NNN/evidence-file | Created |
| docs/setup-evidence/P0/STEP-P0-NNN/aizanta-post-check.md | Created |
| docs/setup-evidence/P0/STEP-P0-NNN/p0-NNN-summary.md | Created |
| docs/setup-evidence/P0/STEP-P0-NNN/verification.md | Created |
| PROGRESS.md | Updated |
| CHECKLIST.md | P0-NNN checked |
| stepprompts/StepPrompts.md | Updated |
```

### 1.4 Validation Results Format

Indented code fences (4-space indent) with command + output, followed by status label:

- ✅ for PASS
- ❌ for FAIL
- ⚠️ for partial/WEAK PASS
- ℹ️ for info

### 1.5 Evidence Gate Table

```markdown
## Evidence Gate

| Gate | Status |
|---|---|
| Parent verification | PASS |
| Evidence files | N files created |
| Diagnostics | Clean |
| Secret scan | No matches |
| Tracker sync | PROGRESS N/257, CHECKLIST P0-NNN checked, StepPrompts updated |
| Independent auditor gate | Pending |
```

---

## 2. Evidence File Naming Conventions

### 2.1 Required Convention Per Step

| File | Purpose | Status |
|---|---|---|
| verification.md | Main 12-section verification report | Required (all steps) |
| aizanta-post-check.md | Aizanta 5/5 health + ports + SSH | Required (all infra steps) |
| p0-NNN-summary.md | 1-page human-readable summary | Required (all steps) |
| (step-specific) | Raw command output / config content | Per StepPrompts spec |

### 2.2 Auditor-Identified Naming Deviations

| Step | Spec Name | Actual Name | Auditor | Fix |
|---|---|---|---|---|
| P0-011 | sops-version.txt | sops-status.txt | MEDIUM | Renamed during re-audit |
| P0-012 | age-pubkey.txt + age-test.txt | age-key-proof.txt (combined) | MEDIUM | Split during re-audit |

**Lesson**: Evidence filenames MUST match StepPrompts.md spec exactly. Deviations trigger MEDIUM findings.

### 2.3 StepPrompts Evidence Specs

**P0-013** (StepPrompts lines 1420-1422):
```
#### Evidence
- File: docs/setup-evidence/P0/STEP-P0-013/sops-config.txt
- Log:  docs/setup-evidence/P0/STEP-P0-013/sops-test.txt
```

**P0-014** (StepPrompts lines 1525-1527):
```
#### Evidence
- Log:  docs/setup-evidence/P0/STEP-P0-014/postgresql-status.txt
- File: docs/setup-evidence/P0/STEP-P0-014/postgresql-config.txt
```

**Convention override**: StepPrompts lists only 2 evidence files each, but P0 convention requires 5 total:
- verification.md (not in StepPrompts)
- aizanta-post-check.md (not in StepPrompts)
- p0-NNN-summary.md (not in StepPrompts)
- Step-specific file #1 (listed in StepPrompts)
- Step-specific file #2 (listed in StepPrompts)

---

## 3. Tracker Sync Patterns

### 3.1 PROGRESS.md Updates

| Counter | Location | Formula |
|---|---|---|
| Overall | Line 12: `Completed \| N / 257 (X.X%)` | Increment by 1 |
| Phase P0 | Line 27: `P0 \| ... \| N/29` | Increment by 1 |

**Current** (before P0-013): `13 / 257 (5.1%)` | P0 `13/29`
**After P0-013**: `14 / 257 (5.4%)` | P0 `14/29`
**After P0-014**: `15 / 257 (5.8%)` | P0 `15/29`

**Step line toggles**:
- P0-013: Line 57 → `[x] P0-013 Secrets file structure (.sops.yaml, encrypted credentials)`
- P0-014: Line 58 → `[x] P0-014 PostgreSQL 16 setup (per ADR-027)`

### 3.2 CHECKLIST.md Updates

| Step | Line | Toggle | Command |
|---|---|---|---|
| P0-013 | 112 | `[x]` | `cat .sops.yaml` -> creation_rules with path_regex present |
| P0-014 | 113 | `[x]` | `systemctl status postgresql` -> active; `sudo -u postgres psql -c 'SELECT version()'` -> PostgreSQL 16.x |

**Auditor lesson**: P0-012 CHECKLIST flagged LOW (FINDING-4) for testing wrong path. Ensure CHECKLIST commands use actual VPS paths, not defaults.

### 3.3 StepPrompts.md Updates — P0-013

| Change | Lines | Before | After |
|---|---|---|---|
| Status | 1310 | ⬜ Not Started | ✅ Completed |
| Pre-flight 1 | 1325 | [ ] | [x] |
| Pre-flight 2 | 1326 | [ ] | [x] |
| Pre-flight 3 | 1327 | [ ] | [x] |
| Verification 1-5 | 1414-1418 | 5x [ ] | 5x [x] |

### 3.4 StepPrompts.md Updates — P0-014

| Change | Lines | Before | After |
|---|---|---|---|
| Status | 1446 | ⬜ Not Started | ✅ Completed |
| Pre-flight 1-4 | 1461-1464 | 4x [ ] | 4x [x] |
| Verification 1-6 | 1518-1523 | 6x [ ] | 6x [x] |

**Auditor lesson**: P0-011 CRITICAL finding (FINDING-A) — StepPrompts.md NOT updated despite summary claiming it was. StepPrompts sync is CRITICAL, not optional.

---

## 4. Auditor Findings Patterns

### 4.1 P0-011 (Verdict: NEEDS REVIEW)

| Finding | Severity | Fixed? |
|---|---|---|
| StepPrompts.md not updated | CRITICAL | Yes (post-audit) |
| Evidence naming: sops-status.txt vs sops-version.txt | MEDIUM | Yes (renamed) |
| Docker health not reproducible (no docker group) | MEDIUM | Pre-existing, not fixed |
| SOPS version 3.9.4 vs latest 3.13.1 | LOW | Accepted as deferred |
| AC-SEC-003 gap documented | LOW | Accepted as expected |

### 4.2 P0-012 (Verdict: NEEDS REVIEW → PASS after re-audit)

| Finding | Severity | Fixed? |
|---|---|---|
| Private key exposed in session chat | HIGH | Yes (key rotated) |
| Evidence naming: age-key-proof.txt vs age-pubkey.txt + age-test.txt | MEDIUM | Yes (split) |
| Docker health not reproducible (pre-existing) | MEDIUM | Pre-existing, same as P0-011 |
| CHECKLIST command tests wrong path | LOW | Yes (path fixed) |
| Port 8080 undocumented | LOW | Accepted as info |

### 4.3 Recurring Patterns

| Pattern | P0-010 | P0-011 | P0-012 | Expectation for P0-013/014 |
|---|---|---|---|---|
| Evidence naming matches spec | ✅ | ❌ | ❌ | Must match spec exactly |
| StepPrompts.md synced | ✅ | ❌ (CRITICAL) | ✅ | Must sync before claiming done |
| Tracker counters correct | ✅ | ✅ | ✅ | Increment by 1 |
| Docker reproducible | ✅ | ❌ | ❌ | Will still fail (pre-existing) |
| Secret scan clean | ✅ | ✅ | ✅ | Must maintain |
| AC/ADR references correct | ✅ | ✅ | ✅ | P0-013: AC-SEC-003, ADR-015; P0-014: AC-MEM-001, AC-CORE-001, ADR-027, ADR-031 |

### 4.4 P0-010 (Verdict: PASS — cleanest audit)

Passed first audit with 0 blockers, 4 info observations. Key differentiators:
- Evidence matched StepPrompts spec exactly
- StepPrompts fully synced
- All tracker counts correct
- Docker access available (reproducible)

---

## 5. Counter Math Reference

| Metric | Current | After P0-013 | After P0-014 |
|---|---|---|---|
| PROGRESS overall | 13/257 (5.1%) | 14/257 (5.4%) | 15/257 (5.8%) |
| PROGRESS P0 phase | 13/29 | 14/29 | 15/29 |
| PROGRESS P0-013 line 57 | [ ] | [x] | [x] |
| PROGRESS P0-014 line 58 | [ ] | [ ] | [x] |
| CHECKLIST P0-013 line 112 | [ ] | [x] | [x] |
| CHECKLIST P0-014 line 113 | [ ] | [ ] | [x] |
| StepPrompts P0-013 status | ⬜ Not Started | ✅ Completed | ✅ Completed |
| StepPrompts P0-014 status | ⬜ Not Started | ⬜ Not Started | ✅ Completed |

---

## 6. Recommended Evidence Files — P0-013 (SOPS Secrets File Structure)

### 6.1 File Inventory

| # | File | Content Summary |
|---|---|---|
| 1 | verification.md | 12-section verification report |
| 2 | sops-config.txt | .sops.yaml creation_rules + age pubkey + encrypted file header |
| 3 | sops-test.txt | Round-trip encrypt/decrypt test + permissions check |
| 4 | aizanta-post-check.md | Aizanta 5/5 health + ports + SSH |
| 5 | p0-013-summary.md | 1-page summary |

### 6.2 sops-config.txt Expected Content

- `.sops.yaml` with creation_rules for `secrets/.*\.yaml$`, `.*\.env$`, `.*\.json$`
- Age public key: `age: <PUBKEY>`
- `secrets/guinevere-secrets.yaml` first 5 lines showing `ENC[AES256_GCM,` prefix
- `secrets/.gitignore` content excluding *.yaml, *.env, *.json (except *.sops.yaml)

### 6.3 sops-test.txt Expected Content

- `sops --version` output
- Encrypt test: echo → sops --encrypt → verify ENC prefix
- Decrypt test: sops --decrypt → verify plaintext match
- Permissions: `ls -la secrets/guinevere-secrets.yaml` → 600
- SOPS_AGE_KEY_FILE env var set

### 6.4 ADR/AC References

| ADR/AC | Status |
|---|---|
| ADR-015 (Secrets management) | Compliant — .sops.yaml created with age key |
| AC-SEC-003 (No plaintext secrets) | Compliant — SOPS+age encrypts all secrets |

### 6.5 Rollback

```bash
rm -f /home/guinevere/code/guinevere/secrets/guinevere-secrets.yaml
rm -f /home/guinevere/code/guinevere/.sops.yaml
```

---

## 7. Recommended Evidence Files — P0-014 (PostgreSQL 16 Setup)

### 7.1 File Inventory

| # | File | Content Summary |
|---|---|---|
| 1 | verification.md | 12-section verification report |
| 2 | postgresql-status.txt | systemctl status, pg_isready, psql --version, data dir permissions, DB listing |
| 3 | postgresql-config.txt | guinevere.conf excerpt + SHOW commands output |
| 4 | aizanta-post-check.md | Aizanta 5/5 health + ports + SSH |
| 5 | p0-014-summary.md | 1-page summary |

### 7.2 postgresql-status.txt Expected Content

- `systemctl status postgresql` → active (running)
- `pg_isready` → accepting connections
- `psql --version` → psql (PostgreSQL) 16.x
- `SELECT version();` → PostgreSQL 16.x on x86_64
- `ls -la /var/lib/postgresql/16/main/` → 700 permissions
- `ss -tlnp | grep 5433` → PG listening on 5433 (not 5432 — avoids Aizanta conflict)
- `sudo -u postgres psql -l | grep guinevere` → database listed
- `SHOW max_connections;` → 100
- `SHOW shared_buffers;` → 1GB

### 7.3 postgresql-config.txt Expected Content

- `/etc/postgresql/16/main/conf.d/guinevere.conf` full content
- `SHOW timezone;` → Asia/Jakarta
- `SHOW listen_addresses;` → localhost
- `SHOW port;` → 5433

### 7.4 ADR/AC References

| ADR/AC | Status |
|---|---|
| ADR-027 (Database choice) | Compliant — PostgreSQL 16 as primary store |
| ADR-031 (Database naming) | Compliant — database named guinevere |
| AC-MEM-001 (PostgreSQL + Redis) | Partial — PG active; Redis pending P0-020 |
| AC-CORE-001 (Core daemon) | N/A — infrastructure, not core daemon |

### 7.5 Rollback

```bash
sudo systemctl stop postgresql
sudo apt purge -y postgresql-16
sudo rm -rf /etc/postgresql/16
sudo rm -rf /var/lib/postgresql/16
sudo userdel postgres 2>/dev/null
```

---

## 8. Anticipated Auditor Findings for P0-013/014

| # | Likely Finding | Severity | Mitigation |
|---|---|---|---|
| 1 | Evidence filenames must match StepPrompts spec | MEDIUM | Use exact names: sops-config.txt, sops-test.txt (P0-013); postgresql-status.txt, postgresql-config.txt (P0-014) |
| 2 | StepPrompts.md must be fully synced before claiming complete | CRITICAL | Update status + ALL pre-flight + ALL verification checkboxes; zero unchecked items |
| 3 | PROGRESS counters must be exact | LOW | 14/257 (5.4%) for P0-013; 15/257 (5.8%) for P0-014 |
| 4 | CHECKLIST commands must reference actual VPS paths | LOW | Verify paths match StepPrompts, not defaults |
| 5 | Docker health not reproducible (pre-existing) | MEDIUM | Accept; document in caveats; use port-level verification |
| 6 | Secret scan must pass | LOW | Verify no keys/tokens in evidence |
| 7 | AC-SEC-003 status update | LOW | P0-013 makes it FULL compliant |
| 8 | AC-MEM-001 partial (Redis pending) | LOW | Acknowledge as partial |

---

## 9. Key Rules Summary

1. **Evidence filenames**: Use EXACT names from StepPrompts Evidence section
2. **File count**: 5 per step — 2 StepPrompts-spec + 3 convention
3. **StepPrompts sync**: 100% complete — status + ALL pre-flight + ALL verification checkboxes
4. **PROGRESS math**: Increment overall BY 1 AND phase BY 1
5. **CHECKLIST checkbox**: Toggle line 112 (P0-013) or 113 (P0-014); verify path accuracy
6. **verification.md**: All 12 sections; Evidence Gate shows "Pending" initially
7. **Secret scan**: Mandatory before claiming complete; private keys NEVER in evidence
8. **Docker limitation**: Document in caveats; port-level verification is acceptable
9. **Re-audit**: If auditor finds issues, produce re-audit section with per-finding resolution table + live SSH verification
10. **Stale reference sweep**: After fixes, update ALL evidence files for consistency

---

## Footer

| Field | Value |
|---|---|
| **Source task** | Evidence pattern reference for P0-013 and P0-014 |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (parent orchestrator) |
| **Validation method** | Cross-read of P0-010, P0-011, P0-012 evidence + auditor reports + PROGRESS.md + CHECKLIST.md + StepPrompts.md |
| **Files reviewed** | 15 total |
