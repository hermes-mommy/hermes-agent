# STEP-P0-013 — .sops.yaml + Secrets Structure Verification

| Field | Value |
|---|---|
| **Step** | P0-013 |
| **Type** | Security |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |

## What Was Done

Created `.sops.yaml` in the repo root with 3 creation_rules (yaml/env/json) using the Guinevere age public key from P0-012. Created `secrets/guinevere-secrets.yaml` with placeholder values across 8 categories (discord, database, redis, llm, hermes, surveillance, observability, backup), encrypted with `sops --encrypt`. Created `secrets/.gitignore` to prevent accidental plaintext commits. Verified round-trip encrypt/decrypt works correctly.

## Files Changed

### Local (repo)
| File | Action | Description |
|---|---|---|
| `.sops.yaml` | Created | 3 creation_rules, age pubkey, encrypted_regex |
| `secrets/guinevere-secrets.yaml` | Created | SOPS-encrypted YAML, 8 categories, all PLACEHOLDER values |
| `secrets/.gitignore` | Created | Prevents plaintext *.yaml commits |
| `docs/setup-evidence/P0/STEP-P0-013/sops-config.txt` | Evidence | .sops.yaml content + file listing |
| `docs/setup-evidence/P0/STEP-P0-013/sops-test.txt` | Evidence | Encrypt + decrypt round-trip proof |
| `docs/setup-evidence/P0/STEP-P0-013/p0-013-summary.md` | Evidence | Human-readable summary |
| `docs/setup-evidence/P0/STEP-P0-013/verification.md` | Evidence | This file |
| `docs/setup-evidence/P0/STEP-P0-013/aizanta-post-check.md` | Evidence | Aizanta health check |
| `PROGRESS.md` | Updated | 13→14/257, P0 13→14/29, P0-013 checked |
| `CHECKLIST.md` | Updated | P0-013 line checked |
| `stepprompts/StepPrompts.md` | Updated | P0-013 status ✅, checks checked |

## Validation Results

### SOPS Configuration
```
$ head -5 .sops.yaml
creation_rules:
  - path_regex: secrets/.*\.ya?ml$
    # Plain YAML/JSON secrets files (SOPS YAML/JSON store)
    age: >-
      age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj
```

### SOPS Encryption
```
$ sops --encrypt secrets/guinevere-secrets.yaml | head -3
discord:
    bot_token: ENC[AES256_GCM,data:...]
```
All values encrypted as AES256_GCM. No plaintext values remain.

### SOPS Decryption (Round-Trip)
```
$ sops --decrypt secrets/guinevere-secrets.yaml | head -1
discord:
```
Decrypt produces valid YAML with PLACEHOLDER values. Round-trip verified.

### Aizanta Health
```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

### Protected Ports (unchanged)
```
127.0.0.1:6379    docker-proxy (Aizanta Redis)
100.94.104.22:80  docker-proxy (Aizanta nginx)
127.0.0.1:5432    docker-proxy (Aizanta PostgreSQL)
```

### SSH
```
$ ssh guinevere-vps "whoami && hostname"
guinevere  faiz-prod-01
```

## Evidence Artifacts

| File | Description |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-013/sops-config.txt` | .sops.yaml content, age pubkey, creation rules |
| `docs/setup-evidence/P0/STEP-P0-013/sops-test.txt` | Encrypt + decrypt round-trip output |
| `docs/setup-evidence/P0/STEP-P0-013/aizanta-post-check.md` | Aizanta health post-P0-013 |
| `docs/setup-evidence/P0/STEP-P0-013/p0-013-summary.md` | Human-readable summary |
| `docs/setup-evidence/P0/STEP-P0-013/verification.md` | This file |
| `audit-reports/P0/STEP-P0-013/step-p0-013-auditor-report.md` | Independent auditor report |

## Shared VPS Impact

- **No VPS changes**: P0-013 is entirely local — `.sops.yaml`, `secrets/guinevere-secrets.yaml`, and `secrets/.gitignore` are repo-only files. No VPS services, containers, networks, or ports were touched.
- **Aizanta**: Zero impact. All 5 containers healthy, protected ports unchanged.
- **SSH**: guinevere-vps alias works normally.

## ADR Compliance

| ADR | Status |
|---|---|
| ADR-015 (Secrets Management) | Compliant — SOPS+age encryption per strategy, .sops.yaml creation_rules, encrypted_regex |
| ADR-014 (VPS Architecture) | N/A — local-only step |
| ADR-018 (Defense-in-Depth) | Compliant — secrets encrypted at rest, .gitignore prevents plaintext commits |

## AC Reference

| AC | Status |
|---|---|
| AC-SEC-003 (No plaintext secrets) | Compliant — all secrets encrypted, .gitignore prevents plaintext commits |
| AC-SEC-001 (Security baseline) | Compliant — SOPS+age encryption infrastructure established |

## Rollback / Re-run Safety

```bash
# Remove local files only (no VPS changes to undo)
rm .sops.yaml
rm secrets/guinevere-secrets.yaml
rm secrets/.gitignore
```

**Re-run safety**: Re-creating `.sops.yaml` with the same age pubkey is idempotent. Re-running `sops --encrypt` on the same input produces deterministic encrypted output.

## Design Decisions / Caveats

1. **`.sops.yaml` in repo root**: SOPS auto-discovers this file from any subdirectory — no need for symlinks or per-directory copies.
2. **`SOPS_AGE_KEY_FILE` env var**: Set to `/home/guinevere/secrets/age-key.txt` on the VPS. Must be in Guinevere service unit `Environment=` directives in later phases.
3. **Placeholder values**: All secrets in `guinevere-secrets.yaml` are `PLACEHOLDER` strings. Real values will be filled via `sops set` or direct editing during service deployment (P1+).
4. **`encrypted_regex`**: Catches inline secrets like `password: ...`, `token: ...`, `api_key: ...` that might appear in future config files.
5. **Auditor fix**: Original verification.md was minimal (32 lines). Rewritten to full canonical schema matching P0-008 template.

## Evidence Gate

| Gate | Status |
|---|---|
| Parent verification | PASS — SOPS encrypt/decrypt works, Aizanta healthy, SSH works |
| Evidence files | 5 evidence files created |
| Diagnostics | LSP clean on PROGRESS, CHECKLIST, StepPrompts |
| Secret scan | No plaintext secrets in evidence (only public key + encrypted values) |
| Tracker sync | PROGRESS 14/257, P0 14/29, CHECKLIST P0-013 checked, StepPrompts ✅ |
| Independent auditor gate | PASS — `audit-reports/P0/STEP-P0-013/step-p0-013-auditor-report.md` |

## Footer

**Source task**: STEP-P0-013 (from `stepprompts/StepPrompts.md`)
**Date**: 2026-05-31
**Implementer**: Guinevere (parent orchestrator, local-only)
**Validation method**: Local SOPS commands + live SSH Aizanta health check