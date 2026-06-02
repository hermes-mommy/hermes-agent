# STEP-P0-011 — Internal Context Report (Pre-Implementation)

| Field | Value |
|---|---|
| **Report Type** | Pre-implementation context synthesis |
| **Step** | P0-011 — SOPS Installation |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (parent orchestrator, research wave) |
| **Status** | READY — all context gathered, no blockers |
| **Downstream Use** | Plan implementation, execute SSH commands, capture evidence, pass auditor gate |
| **Sources** | 20+ files across 7 category roots |

---

## 1. Exact Scope Extraction

**Source**: stepprompts/StepPrompts.md lines 1159-1218

### 1.1 Metadata

| Field | Value |
|---|---|
| Type | Security |
| Status | Not Started |
| Risk | Medium |
| Git Commit | chore(P0): pending |
| Goal | Install SOPS (Secrets OPerationS) for encrypted secrets management |
| Dependencies | P0-003 (directory structure) -- COMPLETE |
| Cost Impact | $0/month |
| ADR References | ADR-015 (Secrets Management Strategy) |
| Acceptance Criteria | AC-SEC-003 |
| Estimated Time | 1 hour |

### 1.2 Context (verbatim)

> All secrets (API keys, database passwords, tokens) are encrypted at rest using SOPS + age. SOPS encrypts values while keeping keys readable, enabling safe version control of configuration files.

### 1.3 Pre-flight Checks

| # | Check | Command | Status |
|---|---|---|---|
| 1 | Architecture identified | uname -m | Run at implementation |
| 2 | Internet access for download | curl -s https://api.github.com | Run at implementation |

NOTE: StepPrompts does NOT list Docker as a pre-flight dependency. CHECKLIST.md line 110 uses sops --version as verification -- SOPS is a binary, not Docker. Docker is NOT required for P0-011.

### 1.4 Commands (4 blocks verbatim from StepPrompts)

```bash
# BLOCK 1: Download SOPS latest release
SOPS_VERSION=$(curl -s https://api.github.com/repos/getsops/sops/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')
curl -LO "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"

# BLOCK 2: Install
sudo mv "sops-v${SOPS_VERSION}.linux.amd64" /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops

# BLOCK 3: Verify installation
sops --version

# BLOCK 4: Clean up
rm -f "sops-v${SOPS_VERSION}.linux.amd64"
```

IMPORTANT: The curl URL uses linux.amd64 hardcoded. If uname -m returns aarch64, the binary would fail. Pre-flight check #1 is critical.

### 1.5 Definition of Done

| # | Criterion | Verification Command | Expected |
|---|---|---|---|
| 1 | SOPS installed | sops --version | Version >= 3.8 |
| 2 | Executable in PATH | which sops | /usr/local/bin/sops |

### 1.6 Evidence (Single)

- docs/setup-evidence/P0/STEP-P0-011/sops-version.txt

StepPrompts does NOT explicitly require: verification.md, p0-011-summary.md, or aizanta-post-check.md.

However: Every completed P0 step (P0-001 through P0-010) produced these additional files.

Recommendation: Follow the convention, produce all 4 evidence files.

### 1.7 Rollback

```bash
sudo rm /usr/local/bin/sops
```

Idempotency: Re-running installation is safe. sudo mv will overwrite. Cleanup rm -f is safe if repeated.

### 1.8 Troubleshooting

| Issue | Cause | Resolution |
|---|---|---|
| curl download fails | GitHub API rate limit | Download manually from getsops/sops releases |
| sops --version not found | /usr/local/bin not in PATH | Check PATH for /usr/local/bin |

### 1.9 Notes (verbatim)

- SOPS version 3.8+ required for age encryption support.
- SOPS is used in conjunction with age keys (next step -- P0-012).

---

## 2. Current State (PROGRESS.md)

Source: PROGRESS.md lines 41-73

### 2.1 Phase 0 Progress

| Metric | Value |
|---|---|
| P0 total steps | 29 |
| Completed | 11 / 29 (37.9%) |
| Last completed | P0-010 (Docker network isolation) |
| P0-011 status | Unchecked -- NOT STARTED |
| Completed count overall | 11/257 (4.3%) |

### 2.2 Relevant Completed Dependencies

| Step | Status | Relevance to P0-011 |
|---|---|---|
| P0-000 (VPS Audit) | Complete | OS Ubuntu 24.04, arch expected amd64. Gap: no uname -m. |
| P0-001 (guinevere user) | Complete | User exists, SSH works. SOPS installs to system path. |
| P0-003 (Directory structure) | Complete | Explicit dependency. /home/guinevere/ tree ready. |
| P0-008 (NTP + timezone) | Complete | Host in stable state. |
| P0-010 (Docker network) | Complete | Independent -- no shared resources with P0-011. |

### 2.3 What Changes After P0-011

| Tracker | Change |
|---|---|
| PROGRESS.md | P0-011 checked; 12/257; P0 12/29 |
| CHECKLIST.md | P0-011 line 110 checked |
| stepprompts/StepPrompts.md | Status to Completed; pre-flight + verification boxes checked |

---

## 3. Verification Line (CHECKLIST.md)

Source: CHECKLIST.md line 110

```
- [ ] P0-011: `sops --version` -> sops 3.x installed
```

CHECKLIST also references SOPS in: line 63 (Pre-Flight Security Readiness), line 111 (P0-012 age key), line 134 (integration test), line 151 (phase criteria).

NOTE: CHECKLIST line 63 is a Pre-Flight item that references SOPS. Since P0-011 is the install step, this Pre-Flight item must be satisfied AFTER P0-011 completes. The Pre-Flight checklist is phase-level, not step-level.

---

## 4. ADR-015 -- Secrets Management Strategy Constraints

Source: adr/ADR-015-secrets-management-strategy.md (122 lines)

### 4.1 ADR Summary

| Field | Value |
|---|---|
| Status | Accepted |
| Risk Level | CRITICAL |
| Date | 2026-05-30 |
| Decision | SOPS + age with runtime injection |
| Deciders | Faiz (Owner) + Guinevere (Executor) |

### 4.2 Key Constraints from ADR-015

- SOPS + age is the baseline secrets-management strategy for repo-managed encrypted config
- Runtime injection: services decrypt at startup; plaintext secrets forbidden everywhere
- Key backup required (enforced in P0-012)
- Does not replace full secret rotation governance
- Evidence must be file-based
- Must not be edited in-place -- create superseding ADR for material changes

### 4.3 ADR-015 Links to P0-011

ADR-015 does NOT prescribe the exact installation method. It accepts the tool choice; StepPrompts provides the implementation detail. No contradiction.

---

## 5. IMPLEMENTATION_GUIDE.md Guidance

Source: docs/IMPLEMENTATION_GUIDE.md (560 lines)

### 5.1 Relevant Workflow Rules

- Section 3: 8-step workflow: Read -> Pre-flight -> Execute -> Verify -> Evidence -> Checklist -> PROGRESS -> Commit
- Section 4: Evidence root evidence/phase-N/step-MMM/. P0 uses docs/setup-evidence/P0/STEP-P0-NNN/ pattern (diverges from Section 4).
- Section 6: Shared VPS isolation matrix, post-step Aizanta verification
- Section 8: Troubleshooting

### 5.2 Post-Step Aizanta Verification (Required)

```bash
systemctl status aizanta-*
docker ps --filter "name=aizanta"
```

---

## 6. EncryptionKeyMgmt_v1.0.md -- SOPS-Specific Constraints

Source: docs/20-security/22-EncryptionKeyMgmt_v1.0.md

### 6.1 SOPS + age Standard (Section 10)

| Requirement | Detail |
|---|---|
| SOPS scope | All API keys, DB credentials, service tokens, config |
| SOPS path | /home/guinevere/config/.env.sops.yaml |
| age key path | /home/guinevere/.age/key.txt -- 0600, owner-only |

### 6.2 Key Path Divergence (IMPORTANT)

CONTRADICTION found: StepPrompts P0-012 stores age key at /home/guinevere/secrets/age-key.txt. EncryptionKeyMgmt specifies /home/guinevere/.age/key.txt.

Assessment: StepPrompts is implementation authority. No blocker for P0-011 -- affects P0-012. Flag in caveats.

---

## 7. SecurityPolicy_v1.0.md -- Additional Constraints

Source: docs/20-security/20-SecurityPolicy_v1.0.md

### 7.1 SOPS References

- Section 6.4: SOPS config example, secrets file mapping, rotation schedule
- Section 13.2: SOPS + age usage pattern with .sops.yaml
- Secrets table: llm.sops.yaml, database.sops.yaml, discord.sops.yaml, integrations.sops.yaml, surveillance.sops.yaml

### 7.2 Constraints

- All secrets in SOPS -- no hardcoded credentials
- age key must be chmod 600
- SOPS files can be committed (encrypted); age private key must NOT be committed

Not binding on P0-011 (binary install only) but enforced in P0-013.

---

## 8. AC-SEC-003 -- Acceptance Criteria Analysis

Source: docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md

### 8.1 AC-SEC-003 Definition

| Field | Value |
|---|---|
| Statement | Secrets stored with SOPS+age, decrypted only in approved runtime contexts, absent from code/docs/logs/evidence/sub-agent outputs |
| Test | TEST-SEC-SECRET-001 |
| Evidence | evidence/secrets-rotation/secret-scan-<date>.md |
| Gate | MVP |
| Status | NOT-RUN |

### 8.2 Satisfaction Chain (Not Complete by P0-011 Alone)

P0-011 (SOPS binary) -> P0-012 (age key) -> P0-013 (.sops.yaml + secrets) -> runtime injection -> secret scan evidence.

P0-011 contributes tool availability. AC-SEC-003 gate status: PARTIAL until P0-013.

---

## 9. Dependency Chain Analysis

### 9.1 Upstream

P0-003 (Directory structure) --COMPLETE--> P0-011 (SOPS install) --> P0-012 (age key)

P0-011's only upstream dependency: P0-003 (complete). P0-011 writes to /usr/local/bin/sops only, not to /home/guinevere/ dirs.

### 9.2 Downstream Dependencies

| Step | Dependency | Status |
|---|---|---|
| P0-012 (age key) | P0-011 complete | Blocked until P0-011 |
| P0-013 (secrets file) | P0-011 + P0-012 | Blocked |
| P0-026 (GitHub PAT) | P0-013 complete | Blocked |
| P0-028 (pre-flight verify) | SOPS decrypts all secrets | Blocked |
| P2-002 (Discord token) | SOPS storage | Blocked |
| P10-014 (key rotation) | SOPS installed | Blocked |

Critical path: P0-011 is the gating step for ALL SOPS-encrypted secret storage.

---

## 10. Shared Writers (Collision Scan)

### 10.1 Parent-Only Tracker Updates

| File | Owner |
|---|---|
| PROGRESS.md (lines 12, 27, 55) | Parent-only |
| CHECKLIST.md (line 110) | Parent-only |
| stepprompts/StepPrompts.md (line 1162, 1177-1178, 1198-1199) | Parent-only |

### 10.2 Exclusive VPS File

/usr/local/bin/sops -- no other step writes here. No collision.

### 10.3 Parallel Execution Safety

Cannot run parallel with P0-012 (depends on P0-011) or P0-013 (depends on P0-012). Sequential required.

---

## 11. Evidence Root

### 11.1 Directory Structure (To Create)

```
docs/setup-evidence/P0/STEP-P0-011/
  sops-version.txt          (StepPrompts-required)
  verification.md           (convention)
  p0-011-summary.md         (convention)
  aizanta-post-check.md     (convention)
```

Plus:
```
audit-reports/P0/STEP-P0-011/
  internal-context-report.md   (this file)
  step-p0-011-auditor-report.md  (post-implementation)
```

### 11.2 Pre-existing: Both directories now exist.

### 11.3 Canonical 10-Section Template (from P0-010)

1. What Was Done | 2. Files Changed | 3. Validation Results | 4. Evidence Artifacts | 5. Shared VPS Impact | 6. ADR Compliance | 7. AC Reference | 8. Rollback / Re-run Safety | 9. Design Decisions / Caveats | 10. Evidence Gate + Footer

---

## 12. Pre-Flight Checklist

### 12.1 Environment Checks (SSH to VPS)
- [ ] uname -m (confirm x86_64)
- [ ] curl -sI https://api.github.com (GitHub reachable)
- [ ] /usr/local/bin/ exists
- [ ] which sops || echo "not installed"
- [ ] sudo -l (confirm sudo for guinevere)
- [ ] whoami (confirm guinevere)
- [ ] systemctl status aizanta-* (baseline)
- [ ] df -h / (disk space < 50MB needed)

### 12.2 Pre-Flight Data Collection
- [ ] uname -m > /tmp/p0-011-arch.txt
- [ ] which sops || echo "not-installed" > /tmp/p0-011-precheck.txt
- [ ] systemctl list-units | grep aizanta > /tmp/p0-011-aizanta-pre.txt

### 12.3 Pre-Flight Blockers
- No internet: manual download from GitHub releases
- Arch not x86_64: adjust URL to linux.arm64
- No sudo: ask Faiz

---

## 13. Verification Commands (Post-Implementation)

### 13.1 Core Verification

| Command | Expected |
|---|---|
| sops --version | sops 3.8.x+ (3.8+ required for age) |
| which sops | /usr/local/bin/sops |
| ls -la /usr/local/bin/sops | -rwxr-xr-x 1 root root |

### 13.2 Cleanup Verification

ls sops-v*.linux.amd64 2>/dev/null -- should NOT exist (cleaned up)

### 13.3 Aizanta Health

systemctl status aizanta-* -- all running (unchanged)
docker ps --filter "name=aizanta" -- 5 containers UP

---

## 14. Safety Domain Analysis

### 14.1 Secrets Domain (CRITICAL)

P0-011 operates in the secrets safety domain per AGENTS.md BLOCKING rules. However, P0-011 only installs the SOPS binary -- it does NOT handle actual secrets.

| Risk | Impact | Mitigation |
|---|---|---|
| None | SOPS binary has no secrets | N/A |
| Evidence path references secrets/ | Low -- dir names not secrets | No secret values in evidence |
| SOPS version in evidence | None -- public info | Confirm no keys in output |

### 14.2 No Persona/Safety Impact

P0-011 does not touch persona, surveillance, memory, consent, or yandere domains.

### 14.3 AGENTS.md BLOCKING Rules

None apply directly. No code changes. No secret handling. Monitor evidence output.

---

## 15. Cross-Doc Consistency Analysis

### 15.1 Consistent Across All Sources

| Aspect | All Sources Agree? |
|---|---|
| Tool: SOPS | Yes (StepPrompts, ADR-015, SecurityPolicy, EncryptionKeyMgmt) |
| Version: 3.8+ | Yes (single source: StepPrompts) |
| Verification: sops --version | Yes (StepPrompts, CHECKLIST) |
| AC: AC-SEC-003 | Yes (StepPrompts, AC catalog) |
| ADR: ADR-015 | Yes (StepPrompts, ADR-Index) |
| Cost: $0/month | Yes (StepPrompts, PROGRESS) |
| Binary path: /usr/local/bin/sops | Yes (single source: StepPrompts) |

### 15.2 Contradictions Found

| # | Conflict | Severity | Impact on P0-011 |
|---|---|---|---|
| 1 | age key path: P0-012 says /home/guinevere/secrets/age-key.txt, EncryptionKeyMgmt says /home/guinevere/.age/key.txt | MEDIUM | Affects P0-012, not P0-011. Flag for downstream. |
| 2 | Evidence root: IMPLEMENTATION_GUIDE says evidence/phase-N/, P0 convention says docs/setup-evidence/P0/ | LOW | Follow P0 convention. |
| 3 | Pre-Flight ordering: CHECKLIST Pre-Flight says SOPS installed; P0-011 is the install step | LOW | Phase-level vs step-level. Resolved. |

### 15.3 Gaps

| Gap | Severity |
|---|---|
| P0-000 missing uname -m | MEDIUM -- must capture at pre-flight |
| StepPrompts missing sudo check | LOW -- confirmed by P0-001 |
| AC-SEC-003 evidence path mismatch | INFO -- AC evidence is MVP-level |

---

## 16. Rollback and Recovery

### 16.1 Standard Rollback

```bash
sudo rm /usr/local/bin/sops
```

Effect: P0-012 blocked (requires SOPS). P0-011 must be re-executed.

### 16.2 Alternative Rollback

```bash
sudo rm -f $(which sops)
```

### 16.3 Idempotency

Re-running is safe. sudo mv overwrites existing. rm -f on cleanup is idempotent. No persisted state beyond binary file.

### 16.4 Recovery After Failed Install

- sudo mv fails: check disk space, permissions, sudo access
- Download fails (rate limit): wait 1 hour or download manually from GitHub releases
- Retry after fix -- download artifact still exists in current directory

---

## 17. Implementation Checklist

### 17.1 Pre-flight
- [ ] whoami -- confirm guinevere
- [ ] uname -m -- confirm x86_64
- [ ] curl -sI https://api.github.com -- reachable
- [ ] sudo -l | grep /usr/local/bin -- sudo access
- [ ] which sops || echo "not installed"
- [ ] Capture: uname -m > /tmp/p0-011-arch.txt
- [ ] Capture: systemctl list-units | grep aizanta > /tmp/p0-011-aizanta-pre.txt

### 17.2 Download and Install
- [ ] SOPS_VERSION=$(curl -s https://api.github.com/repos/getsops/sops/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')
- [ ] curl -LO "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"
- [ ] sudo mv "sops-v${SOPS_VERSION}.linux.amd64" /usr/local/bin/sops
- [ ] sudo chmod +x /usr/local/bin/sops

### 17.3 Verification
- [ ] sops --version shows >= 3.8
- [ ] which sops returns /usr/local/bin/sops
- [ ] ls -la /usr/local/bin/sops shows executable, owned by root
- [ ] rm -f "sops-v${SOPS_VERSION}.linux.amd64"
- [ ] Confirm cleanup: ls sops-v*.linux.amd64 2>/dev/null -- no file

### 17.4 Aizanta Health
- [ ] systemctl status aizanta-* -- all active
- [ ] docker ps --filter "name=aizanta" -- 5 containers UP

### 17.5 Evidence (Local)
- [ ] Create docs/setup-evidence/P0/STEP-P0-011/sops-version.txt
- [ ] Create docs/setup-evidence/P0/STEP-P0-011/verification.md
- [ ] Create docs/setup-evidence/P0/STEP-P0-011/p0-011-summary.md
- [ ] Create docs/setup-evidence/P0/STEP-P0-011/aizanta-post-check.md

### 17.6 Tracker Updates (Parent-Only)
- [ ] PROGRESS.md: check P0-011, 12/257, P0 12/29
- [ ] CHECKLIST.md: check P0-011 line 110
- [ ] stepprompts/StepPrompts.md: status to Completed, check boxes

### 17.7 Auditor Gate
- [ ] Spawn independent auditor after evidence: audit-reports/P0/STEP-P0-011/step-p0-011-auditor-report.md

### 17.8 Git Commit
- [ ] git add -A && git commit -m "P0-011: SOPS installation complete"

---

## 18. Source File Index

| # | File | What It Provides |
|---|---|---|
| 1 | stepprompts/StepPrompts.md (1159-1218) | Scope, commands, DoD, evidence, rollback, troubleshooting |
| 2 | PROGRESS.md (41-73, 55) | Current state: P0-011 unchecked |
| 3 | CHECKLIST.md (63, 110, 134, 151) | Verification command, integration test, phase criteria |
| 4 | adr/ADR-015-secrets-management-strategy.md | Architectural decision for SOPS + age |
| 5 | docs/IMPLEMENTATION_GUIDE.md | Isolation matrix, Aizanta verify commands |
| 6 | docs/20-security/22-EncryptionKeyMgmt_v1.0.md | SOPS standards, key paths, controls |
| 7 | docs/20-security/20-SecurityPolicy_v1.0.md | SOPS config expectation, rotation schedule |
| 8 | docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md | AC-SEC-003 definition |
| 9 | docs/setup-evidence/P0/STEP-P0-010/verification.md | Canonical 10-section evidence template |
| 10 | stepprompts/StepPrompts.md (1219-1305) | P0-012 downstream definition (depends on P0-011) |
| 11 | stepprompts/StepPrompts.md (1307-1437) | P0-013 downstream definition (depends on P0-011) |
| 12 | docs/20-security/23-SecretsRotationRunbook_v1.0.md | Key rotation procedures referencing SOPS |
| 13 | AGENTS.md (Sections 0, 5, 14) | Safety domain rules, BLOCKING anti-patterns |

---

## 19. Blocker Analysis

### 19.1 Dependencies Met
P0-003 (directory structure) -- COMPLETE. No unmet dependencies.

### 19.2 Cross-Doc Contradictions
All resolved. The one path contradiction (age key) affects P0-012, not P0-011.

### 19.3 No Pre-Existing SOPS
System is clean. No step before P0-011 installs SOPS.

### 19.4 KNOWN GAP: Missing uname -m in P0-000
Severity: MEDIUM. Mitigation: pre-flight check #1 captures this.

### 19.5 KNOWN GAP: Pre-flight Internet Access
Severity: LOW. Mitigation: manual download from GitHub releases.

### 19.6 NO BLOCKERS
All dependencies met. All cross-docs consistent. Known gaps have mitigations. Ready to implement.

---

## 20. Implementation Trade-offs and Recommendations

| Decision | Recommendation | Rationale |
|---|---|---|
| Evidence root | docs/setup-evidence/P0/STEP-P0-011/ | All prior P0 steps use this convention |
| Evidence files | Full set (4 files) | Consistent with P0-001 through P0-010 |
| Install user | guinevere with sudo | Follows StepPrompts exactly |
| Git commit | Per-step | Enables rollback |

---

## 21. Footer

Source task: STEP-P0-011 internal context research (pre-implementation)
Date: 2026-05-31
Author: Guinevere (parent orchestrator)
Method: 18 source files read, 7 grep/glob searches, cross-validation across 7 doc categories
Verdict: READY TO IMPLEMENT -- zero blockers, all dependencies met, known gaps have mitigations, safety domains identified, collision scan clear, evidence schema defined, pre-flight checklist complete.
