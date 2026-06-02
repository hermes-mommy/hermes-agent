# STEP-P0-013 — Pre-Implementation Context Report

**Report Type:** Internal context report (pre-implementation)
**Step:** P0-013 — Secrets File Structure (.sops.yaml + encrypted secrets)
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Author:** Guinevere (parent orchestrator)
**Status:** Report complete — ready for implementation

---

## 1. Scope

### 1.1 Exact Deliverables

Based on stepprompts/StepPrompts.md lines 1307-1441, P0-013 produces:

| # | Deliverable | Location | Format |
|---|---|---|---|
| 1 | .sops.yaml configuration | /home/guinevere/code/guinevere/.sops.yaml (via VPS) | YAML |
| 2 | secrets/guinevere-secrets.yaml (encrypted) | /home/guinevere/code/guinevere/secrets/guinevere-secrets.yaml | YAML, SOPS-encrypted |
| 3 | secrets/.gitignore | /home/guinevere/code/guinevere/secrets/.gitignore | Gitignore |
| 4 | secrets/ directory | /home/guinevere/code/guinevere/secrets/ | Directory |

### 1.2 Exact Actions

1. Read age public key from /home/guinevere/secrets/age-key.txt
2. Create .sops.yaml with 3 creation_rules entries (.yaml, .env, .json)
3. Create secrets template YAML with all credential placeholders
4. Encrypt template via SOPS -> secrets/guinevere-secrets.yaml
5. Verify decrypt round-trip works
6. Set chmod 600 on encrypted file
7. Delete plaintext template from /tmp/
8. Create secrets/.gitignore with exclusion rules
9. Add export SOPS_AGE_KEY_FILE=... to ~/.bashrc

### 1.3 What Is NOT In Scope

- Actual credential values (all PLACEHOLDER) - Faiz provides real values later
- Key rotation (P10-014)
- Runtime secret injection (later steps)
- Secret inventory (deferred to EncryptionKeyMgmt runbook)
- GitHub PAT encryption specifically (P0-026 reuses P0-013 infrastructure)
- .env.sops.yaml or secrets.production.sops.yaml files per EncryptionKeyMgmt spec

---

## 2. Dependencies

### 2.1 Upstream (Must Be Complete)

| Dep | Step | Status | Evidence |
|-----|------|--------|----------|
| SOPS installed | P0-011 | Complete | docs/setup-evidence/P0/STEP-P0-011/ |
| age key generated + backed up | P0-012 | Complete | docs/setup-evidence/P0/STEP-P0-012/ |
| Directory structure | P0-003 | Complete | docs/setup-evidence/P0/STEP-P0-003/ |

### 2.2 Pre-flight Verification Commands

`ash
sops --version   # Expected: 3.9.4 >= 3.8
ls -la /home/guinevere/secrets/age-key.txt   # Expected: 600, guinevere:guinevere
grep "public key:" /home/guinevere/secrets/age-key.txt | awk '{print }'
# Expected: age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj
ls -la /home/guinevere/code/guinevere/   # Expected: directory exists
`

### 2.3 Downstream (Blocked by P0-013)

| Step | Dependency | Detail |
|------|-----------|--------|
| P0-026 | GitHub PAT + SOPS storage | Uses .sops.yaml + sops --encrypt pattern from P0-013 |
| P1-008 | 9Router key setup | Relies on SOPS-encrypted secrets file |
| P1-010 | DeepSeek key setup | Relies on SOPS-encrypted secrets file |
| P2-002 | Discord token SOPS storage | sops --encrypt into secrets file |
| P7-002 | HMAC secret storage | SOPS-encrypted |
| All later SOPS-dependent steps | Encryption infrastructure | Foundation for ALL encrypted secrets |

---

## 3. Definition of Done (DoD)

All items must pass before step can be marked complete:

- [ ] **DoD-1**: .sops.yaml exists at repo root with 3 creation_rules entries (.yaml, .env, .json) and correct public key
- [ ] **DoD-2**: secrets/guinevere-secrets.yaml encrypted with ENC[AES256_GCM,...] values visible
- [ ] **DoD-3**: sops -d secrets/guinevere-secrets.yaml returns plaintext with PLACEHOLDER values
- [ ] **DoD-4**: secrets/guinevere-secrets.yaml permissions = 600
- [ ] **DoD-5**: Plaintext template /tmp/guinevere-secrets.yaml deleted
- [ ] **DoD-6**: secrets/.gitignore blocks *.yaml, *.env, *.json but allows *.sops.yaml and .gitignore
- [ ] **DoD-7**: export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt added to ~/.bashrc
- [ ] **DoD-8**: CHECKLIST line 112 updated (P0-013: cat .sops.yaml -> creation_rules with path_regex)
- [ ] **DoD-9**: PROGRESS.md updated (P0-013 checked, counters updated)
- [ ] **DoD-10**: Evidence files created at docs/setup-evidence/P0/STEP-P0-013/
- [ ] **DoD-11**: Aizanta health verified post-step
- [ ] **DoD-12**: Independent auditor gate passed

---

## 4. ADR References

| ADR | Title | Relevance to P0-013 | Status |
|-----|-------|---------------------|--------|
| ADR-015 | Secrets Management Strategy | **Authority document.** Accepts SOPS + age with runtime injection. | Accepted |
| ADR-018 | Security Architecture & Defense-in-Depth | Data layer: SOPS+age. Config/Secrets STRIDE analysis. | Accepted with notes |
| ADR-008 | Memory Encryption & Key Management | Key hierarchy parent. SOPS age identity is Layer 1. | Accepted with notes |

### 4.1 ADR-015 Key Requirements

- **Plaintext secrets forbidden** in ADRs, docs, code, evidence, logs, sub-agent reports
- **SOPS + age** is the baseline secrets-management strategy
- **Runtime injection** for services (decrypt at startup)
- **Key backup mandatory** - lost key blocks recovery

### 4.2 ADR-018 Component 12 (Config/Secrets) Requirements

| Threat | Risk | Mitigation for P0-013 |
|--------|------|----------------------|
| Tampering (12.2) | Critical | Git-tracked encrypted files; age key access logged |
| Info Disclosure (12.4) | Critical | Secrets decrypted to tmpfs only; never logged |
| Spoofing (12.1) | High | age key 600 permissions; file integrity |
| DoS (12.5) | High | age key backup required; secrets in git |

---

## 5. Acceptance Criteria References

| AC | Description | How P0-013 Satisfies |
|----|-------------|---------------------|
| AC-SEC-003 | No plaintext secrets; SOPS+age installed and key available | Creates encrypted secrets infrastructure |
| AC-CORE-006 | Config fails closed on missing secrets | .sops.yaml + SOPS-encrypted secrets enable fail-closed |
| AC-PHASE-001 | Phase 0 completes without breaking Aizanta | Repo-only + config-only; no services affected |

---

## 6. Evidence Convention

### 6.1 Evidence Root

`
docs/setup-evidence/P0/STEP-P0-013/
`

### 6.2 Required Evidence Files (per StepPrompts)

| File | Content |
|------|---------|
| sops-config.txt | .sops.yaml content |
| sops-test.txt | Output of encrypt/decrypt round-trip test |

### 6.3 Recommended Additional Evidence (per P0-012 pattern)

| File | Content |
|------|---------|
| erification.md | Full verification report following P0-012 template |
| p0-013-summary.md | Human-readable summary |
| izanta-post-check.md | Aizanta health verification after step |

---

## 7. Shared Writers (Collision Scan)

### 7.1 Files Modified by P0-013

| File | Action | Conflict Risk |
|------|--------|--------------|
| .sops.yaml (repo root) | CREATE | Low - new file, no existing file |
| secrets/guinevere-secrets.yaml | CREATE | Low - new file |
| secrets/.gitignore | CREATE | Low - new file |
| secrets/ directory | CREATE | Low - new directory |
| ~/.bashrc (VPS) | APPEND | Low - single export line |

### 7.2 Shared Writers Requiring Parent-Only Access

| File | Change | Rule |
|------|--------|------|
| PROGRESS.md | Update P0-013 status + counters | Parent-only. Per AGENTS.md. |
| CHECKLIST.md | Check P0-013 line (line 112) | Parent-only. Per AGENTS.md. |
| stepprompts/StepPrompts.md | Update P0-013 status/checks | Parent-only. |

### 7.3 Collision Verdict

**No collision risk.** All file writes are to new paths or shared docs with exclusive parent access.

---

## 8. Cross-Doc Contradictions and Open Issues

### 8.1 Age Key Path Mismatch (Minor)

| Source | Expected Path |
|--------|--------------|
| StepPrompts P0-012/P0-013 | /home/guinevere/secrets/age-key.txt |
| EncryptionKeyMgmt section 10.3 | /home/guinevere/.age/key.txt |

**Resolution**: P0-013 sets SOPS_AGE_KEY_FILE in ~/.bashrc which resolves the mismatch at runtime. No additional action needed.

### 8.2 Secrets File Location Mismatch (Non-blocking)

| Source | Expected Location |
|--------|------------------|
| StepPrompts P0-013 | /home/guinevere/code/guinevere/secrets/guinevere-secrets.yaml |
| EncryptionKeyMgmt section 10.2 | /home/guinevere/config/.env.sops.yaml |

**Resolution**: StepPrompts is authoritative for P0-013. Track as future doc-sync item.

### 8.3 No encrypted_suffix Used

StepPrompts uses path_regex (full-file encryption), not encrypted_suffix (per-value encryption). This is correct for the initial implementation.

### 8.4 No .env.sops Test File

The .env creation rule in .sops.yaml exists for future use. P0-013 only creates .yaml test encryption.

---

## 9. Blockers

| Blocker | Status | Resolution |
|---------|--------|-----------|
| P0-012 incomplete | PASS - complete | Key exists, public key available |
| SOPS not installed | PASS - complete | sops --version returns 3.9.4 |
| VPS SSH access | PASS - complete | ssh guinevere-vps works |
| .sops.yaml already exists | PASS - no existing file | Fresh create |
| Age key permissions | PASS - 600 | Verified in P0-012 evidence |

**No blockers identified.**

---

## 10. Verification Commands

### 10.1 Post-Execution Verification

| # | Command | Expected Output |
|---|---------|----------------|
| 1 | cat /home/guinevere/code/guinevere/.sops.yaml | creation_rules with 3 path_regex entries + correct age public key |
| 2 | cat /home/guinevere/code/guinevere/secrets/guinevere-secrets.yaml | ENC[AES256_GCM,...] values (encrypted) |
| 3 | sops -d /home/guinevere/code/guinevere/secrets/guinevere-secrets.yaml | head -5 | Plaintext with PLACEHOLDER values |
| 4 | ls -la /home/guinevere/code/guinevere/secrets/guinevere-secrets.yaml | -rw------- (600) |
| 5 | 	est -f /tmp/guinevere-secrets.yaml && echo "EXISTS" || echo "DELETED" | DELETED |
| 6 | cat /home/guinevere/code/guinevere/secrets/.gitignore | Exclusion rules |
| 7 | grep SOPS_AGE_KEY_FILE ~/.bashrc | export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt |
| 8 | Aizanta health check | Services running |

### 10.2 CHECKLIST Line (line 112)

After P0-013, CHECKLIST line 112 should verify:
`ash
cat /home/guinevere/code/guinevere/.sops.yaml
# Shows creation_rules with path_regex present
`

---

## 11. Rollback Safety

### 11.1 Rollback Commands (from StepPrompts)

`ash
# Remove encrypted secrets file
# Remove .sops.yaml
`

### 11.2 Additional Rollback

`ash
# Remove secrets directory and .gitignore
# Remove SOPS_AGE_KEY_FILE from ~/.bashrc
`

### 11.3 Rollback Verdict

**Safe.** P0-013 creates no running services, no database changes, no firewall rules, no container changes. Rollback is purely file deletion. Aizanta is unaffected.

### 11.4 Re-run Safety

**Idempotent.** All file creations are overwrite-safe. No stateful changes.

---

## 12. Directory Structure for Evidence

`
docs/setup-evidence/P0/STEP-P0-013/
|- sops-config.txt           # .sops.yaml content
|- sops-test.txt             # Encrypt/decrypt round-trip test output
|- verification.md           # Full verification report
|- p0-013-summary.md         # Human-readable summary
|- aizanta-post-check.md     # Aizanta health verification
`

---

## 13. Implementation Decomposition

### Step 1: Pre-flight Checks
- Verify P0-011, P0-012 complete
- Verify SSH access
- Extract age public key

### Step 2: Create .sops.yaml
- cat > /home/guinevere/code/guinevere/.sops.yaml

### Step 3: Create and Encrypt Secrets
- Create template at /tmp/guinevere-secrets.yaml
- sops --encrypt --age "" /tmp/guinevere-secrets.yaml > secrets/guinevere-secrets.yaml
- Verify decrypt
- Set 600 permissions
- Delete plaintext template

### Step 4: Create .gitignore
- cat > secrets/.gitignore

### Step 5: Configure Environment
- Add export SOPS_AGE_KEY_FILE=... to ~/.bashrc

### Step 6: Verify
- Run all 9 verification commands

### Step 7: Capture Evidence
- Create all evidence files

### Step 8: Sync Shared Docs
- Update PROGRESS.md
- Check CHECKLIST.md line 112
- Update stepprompts/StepPrompts.md P0-013 status

### Step 9: Aizanta Health Check
- Verify Aizanta containers/services still running

### Step 10: Auditor Gate
- Spawn independent auditor
- Fix findings
- Re-verify

---

## 14. Notes and Caveats

1. **Internet not required.** All operations are local to the VPS.
2. **No sudo required.** All commands run as guinevere user.
3. **Public key is safe to show** in .sops.yaml and evidence - it is the encryption recipient, not the secret.
4. **Template values are PLACEHOLDER.** Real credentials added in later steps (P0-026, P1-008, etc.).
5. **Private key never leaves /home/guinevere/secrets/age-key.txt** - per ADR-015.
6. **Budget impact: ** - local file operation, no API costs.
7. **Shared VPS impact: None** - no services, ports, containers, or databases affected.

---

## 15. Source Document Index

| Source | Section | Key Content |
|--------|---------|-------------|
| stepprompts/StepPrompts.md | Lines 1307-1441 | Full P0-013 stepprompt |
| PROGRESS.md | Line 57 | P0-013 unchecked |
| CHECKLIST.md | Line 112 | Verification: cat .sops.yaml |
| docs/IMPLEMENTATION_GUIDE.md | Sections 3-4 | Step execution + evidence workflow |
| dr/ADR-015-secrets-management-strategy.md | Full | Authority: SOPS+age strategy |
| docs/10-governance/17-ADR_Index_v1.0.md | Line 79 | ADR-015 entry |
| docs/setup-evidence/P0/STEP-P0-012/age-pubkey.txt | Full | Public key: age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj |
| docs/setup-evidence/P0/STEP-P0-012/verification.md | Full | P0-012 evidence template + path mismatch caveat |
| docs/20-security/20-SecurityPolicy_v1.0.md | Section 2.13 | Component 12: Config/Secrets STRIDE analysis |
| docs/20-security/22-EncryptionKeyMgmt_v1.0.md | Section 10 | SOPS + age standard, file naming, age identity controls |
| stepprompts/StepPrompts.md | Lines 2801-2890 | P0-026 depends on P0-013 |

---

*Report generated by Guinevere (parent orchestrator) for STEP-P0-013 implementation planning.*
*Date: 2026-05-31*
*Verdict: Ready for implementation - no blockers, no contradictions requiring escalation, all dependencies met.*
