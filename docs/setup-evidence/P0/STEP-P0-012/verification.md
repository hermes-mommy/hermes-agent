# STEP-P0-012 — Age Key Generation Verification

| Field | Value |
|---|---|
| **Step** | P0-012 |
| **Type** | Security |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |

## What Was Done

Generated an age (X25519) encryption key for SOPS secret management. Key stored at `/home/guinevere/secrets/age-key.txt` with 600 permissions. Round-trip encrypt/decrypt test passed.

## Files Changed

### Remote (VPS)
| File | Action |
|---|---|
| `/home/guinevere/secrets/age-key.txt` | Created (600, guinevere:guinevere) |

### Local (repo)
| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-012/age-key-proof.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-012/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-012/p0-012-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-012/verification.md` | Created |
| `PROGRESS.md` | Updated counters, checked P0-012 |
| `CHECKLIST.md` | Checked P0-012 line |
| `stepprompts/StepPrompts.md` | Updated P0-012 status/checks |

## Validation Results

### Key File
```
$ ls -la /home/guinevere/secrets/age-key.txt
-rw------- 1 guinevere guinevere 189 May 31 14:11 /home/guinevere/secrets/age-key.txt
```

### Public Key
```
age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj
```

### Round-Trip Test
```
$ echo 'guinevere-p0-012-test' > /tmp/plain.txt
$ age -r age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj -o /tmp/test.enc /tmp/plain.txt
$ age -d -i /home/guinevere/secrets/age-key.txt /tmp/test.enc
guinevere-p0-012-test
```
**Result: PASS**

### Aizanta Health
All 5 containers healthy. Protected ports unchanged.

### SSH
```
$ ssh guinevere-vps "whoami && hostname"
guinevere  faiz-prod-01
```

## Evidence Artifacts

| File | Description |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-012/age-key-proof.txt` | Public key, round-trip test, security notes |
| `docs/setup-evidence/P0/STEP-P0-012/aizanta-post-check.md` | Aizanta health post-key-gen |
| `docs/setup-evidence/P0/STEP-P0-012/p0-012-summary.md` | Human-readable summary |
| `docs/setup-evidence/P0/STEP-P0-012/verification.md` | This file |

## Shared VPS Impact

- **Aizanta**: Zero impact. No containers, ports, networks, files touched.
- **Guinevere**: 189-byte key file created. No service changes.

## ADR Compliance

| ADR | Status |
|---|---|
| ADR-015 (Secrets management) | Compliant — age key created per SOPS+age strategy |
| ADR-014 (VPS/container architecture) | N/A — no architectural change |

## AC Reference

| AC | Status |
|---|---|
| AC-SEC-003 (No plaintext secrets) | Compliant — private key never in evidence; only public key recorded |

## Rollback / Re-run Safety

**Rollback**: Delete `/home/guinevere/secrets/age-key.txt`. Regenerate if needed.

**Re-run safety**: Running `age-keygen -o /home/guinevere/secrets/age-key.txt` overwrites existing key. Backup first.

## Design Decisions / Caveats

1. **Key path**: `/home/guinevere/secrets/age-key.txt` per StepPrompts. EncryptionKeyMgmt expects `/home/guinevere/.age/key.txt`. Path decision deferred to P0-013 (.sops.yaml configuration).
2. **Key type**: age X25519 (standard). No PQ hybrid — acceptable for SOPS encryption of deployment secrets.
3. **Backup**: Mandatory per ADR-015. Operator must store key in password manager or encrypted USB.
4. **⚠️ INCIDENT (RESOLVED)**: Private key was briefly exposed in session chat during key verification. Key rotated 2026-05-31. New public key: `age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj`. Old key backed up as `.age-key.txt.compromised-20260531`. Re-audit round-trip test PASS with new key.
5. **CHECKLIST line 111**: Path `~/.config/sops/age/key.txt` does not match actual `/home/guinevere/secrets/age-key.txt`. StepPrompts is authoritative. **FIXED in re-audit**: CHECKLIST now uses `grep 'public key' /home/guinevere/secrets/age-key.txt`.

## Evidence Gate

| Gate | Status |
|---|---|
| Parent verification | PASS — key exists, round-trip works, Aizanta healthy, SSH works |
| Evidence files | 4 evidence files created |
| Diagnostics | Pending |
| Secret scan | Pending — key intentionally excluded from evidence |
| Tracker sync | Pending |
| Independent auditor gate | PASS — `audit-reports/P0/STEP-P0-012/step-p0-012-auditor-report.md` (FINDING-1 key rotated, FINDING-2 evidence split to age-pubkey.txt+age-test.txt, FINDING-4 CHECKLIST fixed) |

## Footer

**Source task**: STEP-P0-012 (from `stepprompts/StepPrompts.md`)
**Date**: 2026-05-31
**Implementer**: Guinevere (parent orchestrator)
**Validation method**: Live SSH command execution + output capture