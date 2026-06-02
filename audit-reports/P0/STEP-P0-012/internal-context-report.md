# STEP-P0-012 Internal Context Report -- age Key Generation and Backup

**Step:** P0-012 -- age Key Generation and Backup
**Phase:** P0 Infrastructure Foundation
**Type:** Security
**Risk:** HIGH (key compromise = total secrets loss)
**Date:** 2026-05-31
**Scope:** Internal repo/doc context audit -- read-only, no VPS changes, no SSH, no key exposure
**Auditor:** Internal context collector (pre-implementation)

---

## 1. Meta

| Field | Value |
|-------|-------|
| Step ID | P0-012 |
| Git Commit | `chore(P0): pending` |
| Estimated Time | 1 hour |
| Cost Impact | $0/month |
| Executor | Guinevere (parent orchestrator) |
| Operator | Faiz (Darling) |

---

## 2. Source of Truth: StepPrompts.md (P0-012)

**File:** `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md` -- Lines 1221-1304

| Field | Value |
|-------|-------|
| Type | Security |
| Status | Not Started |
| Risk | High |
| Dependencies | P0-011 (SOPS installed), P0-003 (secrets directory exists) |
| Cost Impact | $0/month |
| ADR References | ADR-015 |
| Acceptance Criteria | AC-SEC-003, AC-SEC-006 |
| Estimated Time | 1 hour |

### Goal

Generate age encryption key pair for SOPS and create a secure backup. The age key pair is the master encryption key for all Guinevere secrets. Loss of this key means inability to decrypt secrets. The key must be generated, backed up securely, and never committed to the repository.

### Required Commands (from StepPrompts)

```bash
# 1. Install age
sudo apt install -y age

# 2. Verify age installation
age --version
age-keygen --version

# 3. Generate age key pair
age-keygen -o /home/guinevere/secrets/age-key.txt 2>&1 | tee /home/guinevere/secrets/age-pubkey.txt

# 4. Set strict permissions
chmod 600 /home/guinevere/secrets/age-key.txt
chmod 644 /home/guinevere/secrets/age-pubkey.txt

# 5. Extract public key
AGE_PUBKEY=$(grep "public key:" /home/guinevere/secrets/age-key.txt | awk "{print $4}")
echo "Public key: $AGE_PUBKEY"

# 6. CRITICAL: Display key for manual backup
echo "=== BACKUP THIS KEY MANUALLY ==="
cat /home/guinevere/secrets/age-key.txt
echo "=== Store in password manager, safe, or offline ==="

# 7. Verify round-trip encrypt/decrypt
echo "test" | age -r "$AGE_PUBKEY" | age -d -i /home/guinevere/secrets/age-key.txt
```

### Verification Checklist

- [ ] age installed -> `age --version` returns version
- [ ] Key generated -> `/home/guinevere/secrets/age-key.txt` exists
- [ ] Permissions correct -> `ls -la` shows 600
- [ ] Encrypt/decrypt works -> test returns "test"
- [ ] Public key extracted -> `cat age-pubkey.txt` shows key

### Evidence Paths (from StepPrompts)

| Path | Contains |
|------|----------|
| `docs/setup-evidence/P0/STEP-P0-012/age-pubkey.txt` | Public key only |
| `docs/setup-evidence/P0/STEP-P0-012/age-test.txt` | Round-trip result |

### Rollback

```bash
# WARNING: Only rollback if backup exists!
# rm /home/guinevere/secrets/age-key.txt
# rm /home/guinevere/secrets/age-pubkey.txt
```

---

## 3. Tracker State

### PROGRESS.md
- **[ ] P0-012** age key generation + backup -- NOT checked
- **Completed so far:** 11 / 257 steps (4.3%)
- P0-011 (SOPS installation) also unchecked

### CHECKLIST.md (Line 111)
- **[ ] P0-012** -- NOT checked
- Uses `~/.config/sops/age/key.txt` but StepPrompts uses `/home/guinevere/secrets/age-key.txt`
- **Path discrepancy** -- see Finding F1 below

---

## 4. ADR-015 Constraints

**Status:** Accepted | **Risk:** CRITICAL

| Constraint | Impact on P0-012 |
|------------|-------------------|
| SOPS + age baseline | P0-012 generates the key SOPS will use |
| Plaintext secrets forbidden | Private key NEVER in evidence/logs/git |
| Requires key backup | Backup to password manager is MANDATORY |
| Lost key blocks recovery | Without backup, all secrets unrecoverable |
| Rotation compat (P10-014) | Key uses standard age format |
| ADR-025 DR integration | Evidence usable for DR planning |

---

## 5. AC-SEC-003: Secrets Storage

**Criterion:** Secrets stored with SOPS+age, decrypted only in approved runtime contexts, absent from code/docs/logs/evidence/sub-agent outputs. (Catalog line 207)

### Implications
1. **age-key.txt** is the most secret secret in the system
2. Private key NEVER in: git, evidence, logs, code, sub-agent outputs, Discord
3. Only **public key fingerprint** and **age-pubkey.txt** in evidence
4. `cat age-key.txt` is for OPERATOR backup ONLY -- NOT captured in evidence

---

## 6. AC-SEC-006: Encryption Key Hierarchy

**Criterion:** Encryption uses approved key hierarchy and audited metadata for Restricted/Critical data. (Catalog line 210)

### Implications
1. Establishes the **root key** in the encryption hierarchy
2. Hierarchy: `age private key` -> `SOPS encrypted files` -> `runtime decryption`
3. Track for quarterly verification: date, fingerprint, path, backup location, type (X25519), permissions

---

## 7. Dependencies

| Dependency | Step | Status | Type |
|------------|------|--------|------|
| SOPS installed | P0-011 | NOT STARTED | Blocking |
| Secrets dir exists | P0-003 | COMPLETE | Required |

P0-011 is a hard prereq, but P0-012 can execute standalone (age round-trip works without SOPS).
CHECKLIST verification (`sops -d`) will fail until P0-013 completes.

**Option A (sequential):** P0-011 -> P0-012 (recommended)
**Option B (parallel):** P0-011 and P0-012 simultaneously

---

## 8. Prior Evidence

| Path | Exists? |
|------|---------|
| `docs/setup-evidence/P0/STEP-P0-012/*` | No -- first execution |
| `evidence/phase-0/step-012/*` | No -- different convention |

Follow StepPrompts convention (all prior P0 steps).

---

## 9. Shared Writers & Collision Scan

| File | Action | Writer |
|------|--------|--------|
| `/home/guinevere/secrets/age-key.txt` | CREATE | EXCLUSIVE to P0-012 |
| `/home/guinevere/secrets/age-pubkey.txt` | CREATE | EXCLUSIVE to P0-012 |
| Evidence artifacts | CREATE | EXCLUSIVE to P0-012 |

**No shared writers.** All collision types: CLEAR.
Note: `/home/guinevere/secrets/` dir shared with P0-013/P0-026. Preserve 700 perms.

---

## 10. Secret Safety Protocol (CRITICAL)

### Private Key NEVER In
- Git repository
- Evidence files
- Logs (journalctl, shell history, debug output)
- Screenshots of terminal
- Discord/WebUI messages
- Sub-agent reports
- Documentation/ADRs
- External MCP tools

### Allowed in Evidence
- `age-pubkey.txt`: YES -- public key only
- `age-test.txt`: YES with caution -- test output, NOT key string
- Verification commands: YES -- existence, perms, version
- Public key fingerprint: YES

### Terminal History Cleanup
```bash
history -d $(history | grep "cat.*age-key" | awk "{print $1}")
history -c
```

---

## 11. Verification Commands Reference

### Pre-Flight
```bash
ls -la /home/guinevere/secrets/
age --version 2>/dev/null && echo "installed" || echo "NOT installed"
test -f /home/guinevere/secrets/age-key.txt && echo "EXISTS" || echo "no existing key"
```

### Key Verification
```bash
ls -la /home/guinevere/secrets/age-key.txt    # Expected: -rw-------
ls -la /home/guinevere/secrets/age-pubkey.txt  # Expected: -rw-r--r--
head -1 /home/guinevere/secrets/age-key.txt    # Expected: AGE-SECRET-KEY-1...
```

### Round-Trip Test
```bash
AGE_PUBKEY=$(grep "public key:" /home/guinevere/secrets/age-key.txt | awk "{print $4}")
echo "test" | age -r "$AGE_PUBKEY" | age -d -i /home/guinevere/secrets/age-key.txt
# Expected: "test"
```

---

## 12. Backup Procedure

**CRITICAL:** ADR-015: "Lost age key can block recovery."

1. Run `cat /home/guinevere/secrets/age-key.txt`
2. Operator copies ENTIRE output into password manager
3. Store in offline safe (physical paper backup)
4. Secondary copy on encrypted USB
5. Document backup location in evidence (NOT the key)

**Avoid:** Cloud storage, email, Discord, git, unencrypted screenshots.

---

## 13. Rollback Protocol

**WARNING:** Only rollback if backup is confirmed. Otherwise permanent loss.

```bash
# DO NOT RUN unless backup exists
# rm /home/guinevere/secrets/age-key.txt
# rm /home/guinevere/secrets/age-pubkey.txt
```

| Condition | Rollback? |
|-----------|-----------|
| Wrong permissions | NO -- fix perms directly |
| Key corrupted | YES, if backup exists |
| Mistaken generation | YES -- no encrypted data yet |
| Key compromised | YES -- generate new key |
| Operator forgot backup | NO -- permanent loss |

---

## 14. Pre-Flight Checklist

- [ ] P0-003: `/home/guinevere/secrets/` exists (700 perms)
- [ ] P0-011: SOPS installed (or parallel plan)
- [ ] VPS SSH accessible (guinevere with sudo)
- [ ] Operator Faiz available for backup
- [ ] Password manager/safe accessible
- [ ] No existing key at target (re-run check)
- [ ] Aizanta unaffected check planned

---

## 15. Evidence Manifest

### Directory: `docs/setup-evidence/P0/STEP-P0-012/`

| File | Required |
|------|----------|
| `age-pubkey.txt` | YES |
| `age-test.txt` | YES |
| `verification.md` | YES |
| `p0-012-summary.md` | OPTIONAL |
| `aizanta-post-check.md` | YES |

### MUST NOT Be in Evidence
- `age-key.txt`: Private key -- NEVER commit
- Any file with private key content (AC-SEC-003 violation)

---

## 16. Cross-Doc Findings

### F1: CHECKLIST path mismatch (Non-blocking)
- CHECKLIST: `~/.config/sops/age/key.txt`
- StepPrompts: `/home/guinevere/secrets/age-key.txt`
- Fix: Set `SOPS_AGE_KEY_FILE` env var in P0-013

### F2: CHECKLIST expects SOPS integration
- Needs `sops -d secrets.enc.yaml` -- requires P0-013
- P0-012 passes on age round-trip test alone

### F3: Evidence path convention
- StepPrompts: `docs/setup-evidence/P0/STEP-P0-012/`
- Follow this (all prior P0 steps do)

### F4: StepPrompts status update needed
- Line 1225 shows Not Started -- update after execution

### F5: No personafication concern
- P0-012 is pure infrastructure, no persona boundaries

---

## 17. Implementation Notes

### Key Generation Behavior
- `age-keygen -o FILE 2>&1 | tee PUBFILE`
- Private key written to FILE, identity block to stderr -> tee -> PUBFILE
- age-key.txt: private key + comment header with public key
- age-pubkey.txt: comment with public key only

### Re-run Safety
- `age-keygen -o` OVERWRITES without warning. Check first.

### Aizanta Impact: Zero
- Only affects guinevere secrets directory

### Git Commit Guidance
```bash
git add docs/setup-evidence/P0/STEP-P0-012/
git add stepprompts/StepPrompts.md
git commit -m "P0-012: age key generation and backup complete"
```

---

## 18. Prerequisites Status

| Prerequisite | Status |
|--------------|--------|
| P0-003 (secrets dir) | COMPLETE |
| P0-011 (SOPS installed) | NOT STARTED |
| VPS accessible as guinevere | P0-001 confirmed |
| sudo for guinevere | P0-001 confirmed |
| Operator for backup | TBD |

---

## 19. Execution Checklist for Downstream

- [ ] Verify P0-011 status (or parallel plan)
- [ ] SSH into VPS as guinevere
- [ ] Run pre-flight checks
- [ ] Install age (`sudo apt install -y age`)
- [ ] Verify age + age-keygen versions
- [ ] Generate key pair
- [ ] Set permissions
- [ ] Extract public key
- [ ] Run round-trip test
- [ ] Display key for backup -- do NOT capture in evidence
- [ ] Clear terminal history
- [ ] Create evidence files
- [ ] Ensure NO private key in any evidence
- [ ] Update StepPrompts.md, PROGRESS.md, CHECKLIST.md
- [ ] Git commit
- [ ] Confirm with Faiz backup is complete

---

## 20. Verdict

| Dimension | Status |
|-----------|--------|
| Blocking issues | 1 -- P0-011 not resolved |
| Process findings | 5 (F1-F5, non-blocking) |
| Shared writers | None -- exclusive |
| Safety review needed | No |
| Operator action needed | YES -- key backup |
| Ready for execution | Yes (with parallel plan) |

### Key Warnings
1. **NEVER commit `age-key.txt`** to repo or evidence
2. **Operator MUST back up** before session ends
3. **Rollback only if backup exists** -- permanent loss otherwise
4. **CHECKLIST path mismatch** (F1) resolve before P0-013
5. **Clear terminal history** after displaying key

---

Generated from internal context review. Read-only -- no VPS changes, no SSH, no key exposure.
Sources: PROGRESS.md, StepPrompts.md (lines 1221-1304), CHECKLIST.md, IMPLEMENTATION_GUIDE.md, ADR-Index, ADR-015, Security Policy v1.0, Acceptance Criteria Catalog v1.0, P0-010 evidence.