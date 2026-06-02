# STEP-P0-002 — Internal Context Report (Phase 0 Research Synthesis)

**Step:** P0-002 — SSH Config Update (alias + key-based auth for easy VPS access)
**Phase:** P0 Infrastructure Foundation (29 steps, step 2 of 29)
**Date:** 2026-05-31
**Status:** ⬜ Not Started (P0-000 and P0-001 complete)
**Scope:** Internal repo/doc/ADR context audit + SSH safety research synthesis — read-only, no VPS changes
**Report type:** Pre-implementation internal research (research wave output)
**Source files read:**
- `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md` (lines 358–441)
- `C:\Users\faizz\guinevere\PROGRESS.md` (line 46)
- `C:\Users\faizz\guinevere\CHECKLIST.md` (line 100, lines 61–65)
- `C:\Users\faizz\guinevere\docs\IMPLEMENTATION_GUIDE.md`
- `C:\Users\faizz\guinevere\docs\10-governance\17-ADR_Index_v1.0.md`
- `C:\Users\faizz\guinevere\adr\ADR-019-access-control-vpn-mesh-strategy.md`
- `C:\Users\faizz\guinevere\audit-reports\P0\STEP-P0-002-ssh-safety-research.md`
- `C:\Users\faizz\guinevere\audit-reports\P0\STEP-P0-002-internal-context.md` (prior version)
- `C:\Users\faizz\guinevere\docs\20-security\20-SecurityPolicy_v1.0.md`
- `C:\Users\faizz\guinevere\docs\20-security\21-AccessControl_RBAC_ABAC_v1.0.md`
- `C:\Users\faizz\guinevere\docs\10-governance\16-AcceptanceCriteriaCatalog_v1.0.md` (AC-SEC-001)

---

## 1. Step Definition (from StepPrompts.md lines 358–441)

| Field | Value |
|-------|-------|
| **Step ID** | P0-002 |
| **Type** | Security |
| **Risk** | High — SSH misconfiguration can cause VPS lockout |
| **Status** | ⬜ Not Started |
| **Goal** | Configure SSH alias and key-based authentication for easy VPS access |
| **Dependencies** | P0-001 (guinevere user created) — ✅ Complete |
| **Cost Impact** | $0/month |
| **ADR References** | ADR-019 (Access Control & VPN Mesh Strategy) |
| **Acceptance Criteria** | AC-SEC-001 |
| **Estimated Time** | 30 minutes |
| **Git Commit** | `chore(P0): pending` |

### 1.1 Commands (from StepPrompts)

1. Generate SSH key: `test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -C "samm@guinevere" -f ~/.ssh/id_ed25519 -N ""`
2. Copy key to root: `ssh-copy-id root@<vps-ip>`
3. Copy key to guinevere: `ssh-copy-id guinevere@<vps-ip>`
4. Add SSH alias to `~/.ssh/config`:
   ```
   Host guinevere-vps
       HostName <vps-ip>
       User guinevere
       IdentityFile ~/.ssh/id_ed25519
       ServerAliveInterval 60
       ServerAliveCountMax 3
   ```
5. Set permissions: `chmod 600 ~/.ssh/config`
6. Harden SSH server (VPS-side):
   - `PermitRootLogin no`
   - `PasswordAuthentication no`
7. Test: `ssh guinevere-vps "whoami && hostname"`

### 1.2 Evidence Paths (from StepPrompts)

| Evidence Item | Path |
|--------------|------|
| SSH test log | `docs/setup-evidence/P0/STEP-P0-002/ssh-test.log` |
| SSH config file | `docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt` |

### 1.3 Verification (from StepPrompts)

- SSH key auth works → `ssh guinevere-vps "whoami"` returns `guinevere`
- No password prompt → connection is key-based
- SSH config file exists → `cat ~/.ssh/config` shows guinevere-vps entry

### 1.4 Rollback

```bash
# Remove SSH alias
sed -i '/Host guinevere-vps/,/^$/d' ~/.ssh/config

# Remove authorized key on VPS (run as guinevere on VPS)
# rm ~/.ssh/authorized_keys
```

---

## 2. Current Tracker State

### 2.1 PROGRESS.md (line 46)

```
- [ ] **P0-002** SSH config update (alias for easy access)
```

Status: **NOT checked** — ready for execution. Overall progress: 2/257 steps complete.

### 2.2 CHECKLIST.md

**Line 100** — Step Verification:
```
- [ ] P0-002: `ssh guinevere@vps` -> connects without password prompt (key-based)
```

**Section 1.3 Security Readiness (line 61)**:
```
- [ ] SSH key-based authentication enforced (no password login)
```

Both **NOT checked**. P0-002 will satisfy Section 1.3 pre-flight item.

### 2.3 StepPrompts.md status

Line 361: `**Status:** ⬜ Not Started` — must be updated to ✅ after execution.

### 2.4 Evidence directory

`docs/setup-evidence/P0/STEP-P0-002/` — **exists but empty** (no prior attempt).

---

## 3. ADR-019 Constraints (Access Control & VPN Mesh Strategy)

**Status:** Accepted with notes | **Risk:** HIGH
**File:** `adr/ADR-019-access-control-vpn-mesh-strategy.md`

| Constraint | Detail | Impact on P0-002 |
|------------|--------|------------------|
| **Zero public ports** | SSH is emergency/management access; all admin surfaces are Tailscale-internal | SSH is allowed as the one public port (port 22) for initial setup. After Tailscale (P0-022), SSH can be locked to Tailscale-only. |
| **Tailscale mesh** | All devices (Samm workstations, mobile, VPS) join the tailnet. Internal services accessed via Tailscale-internal addresses only. | Post-P0-022, SSH will be accessed via Tailscale SSH. P0-002 sets up initial key-based auth. |
| **Auth key expiry** | Device keys expire after 180 days by default. Headless nodes require auth key with appropriate expiry settings. | Document renewal procedure: SecurityPolicy.md lines 2534-2581 specify annual SSH key rotation. |
| **Lockout recovery** | Emergency access: VPS console (cloud provider), Tailscale recovery auth key offline, DERP relay fallback. | **CRITICAL**: Before disabling password/root login, ensure VPS console access is known. |
| **Missing from StepPrompts** | ADR-019 mandates Tailscale mesh, but P0-002 StepPrompts hardens SSH on the public interface. This is correct — Tailscale comes later (P0-022). | P0-002 is interim hardening until Tailscale VPN mesh is deployed. |

### ADR-019 Implementation Notes (Excerpts)

- **Zero public ports:** All VPS admin surfaces are Tailscale-internal only. Public integrations use outbound channels. No public VPS ingress permitted. (ADR-019 lines 92-94)
- **Tailscale ACL:** Document ACL policy file structure with device tags (e.g., `tag:admin`, `tag:service`).
- **Subnet routing:** Tailscale does not bypass cloud security groups or host firewalls.
- **Overlapping CIDRs:** Plan non-overlapping subnets across all tailnet members.

---

## 4. SSH Safety Research Synthesis

**Source:** `audit-reports/P0/STEP-P0-002-ssh-safety-research.md` (full 377-line research report)

### 4.1 Ubuntu 24.04 Critical Differences

**Socket activation (breaking change from 22.04):**
- Ubuntu 24.04 manages sshd via systemd socket activation: `ssh.socket` triggers `ssh.service` on-demand.
- Service is called `ssh` (not `sshd`) on Debian/Ubuntu systems.
- `sshd -t` may fail with `/run/sshd missing` — fix: `sudo mkdir -p /run/sshd` before validation.

| Aspect | Ubuntu 22.04 | Ubuntu 24.04 |
|--------|-------------|-------------|
| Unit to enable | `sshd.service` | `ssh.socket` |
| Reload command | `systemctl reload sshd` | `systemctl reload ssh` (still works) |
| Status check | `systemctl is-active sshd` | `systemctl is-active ssh.socket` |

### 4.2 Drop-in Config Pattern (Recommended)

Ubuntu 24.04 has `Include /etc/ssh/sshd_config.d/*.conf`. Create `50-hardening.conf` instead of editing main `sshd_config`:
- Survives package upgrades
- Makes diffs readable
- Keeps changes explicit

### 4.3 Safe Reload vs Restart

| Action | Command | Existing Sessions | Risk |
|--------|---------|-----------------|------|
| **Reload** | `sudo systemctl reload ssh` | **Preserved** — SIGHUP sent | Low |
| **Restart** | `sudo systemctl restart ssh` | **Dropped** | **High** — lockout risk |

**Rule:** Always use `sudo sshd -t && sudo systemctl reload ssh`.

### 4.4 Session Preservation Strategy

1. **Never close active session** until new config is verified.
2. **Open a second terminal** to test changes.
3. **Test key auth BEFORE disabling password auth.**
4. **Test as guinevere BEFORE disabling root login.**
5. Know VPS provider's out-of-band access (hostdata.id web console).

### 4.5 SSH Hardening Directives (from SSH research)

Ordered from safe to aggressive:

| Phase | Directives | Risk |
|-------|-----------|------|
| **Must apply** | `PermitRootLogin no`, `PasswordAuthentication no`, `PubkeyAuthentication yes` | Medium if key not verified first |
| **Stage 2** | `MaxAuthTries 3`, `MaxSessions 3`, `LoginGraceTime 30`, `AuthenticationMethods publickey` | Low |
| **Stage 3** | `AllowUsers guinevere aizanta`, `ClientAliveInterval 300`, `ClientAliveCountMax 2` | Medium — listing all users is critical |
| **Optional** | `X11Forwarding no`, `AllowAgentForwarding no`, `AllowTcpForwarding no`, `PermitTunnel no`, `PermitUserEnvironment no` | Low |
| **Future (P0-022+)** | Lock SSH to Tailscale interface only | Requires Tailscale operational |

### 4.6 AllowUsers Gotcha

**CRITICAL:** Forgetting to include existing users like `aizanta` will lock them out. Always list ALL users that need SSH access.

---

## 5. Security Policy SSH Requirements

**Source:** `docs/20-security/20-SecurityPolicy_v1.0.md`

### 5.1 SSH Key Management (Section 13.3, lines 2534-2547)

| Key | Purpose | Type | Rotation |
|-----|---------|------|----------|
| Operator SSH key | Tailscale SSH to VPS | Ed25519 | Annually |
| Guinevere deploy key | Git clone/pull from GitHub | Ed25519 | Annually |
| GitHub deploy key | CI/CD access | Ed25519 | Annually |

**Controls:**
- All SSH keys are Ed25519 (minimum 256-bit) — StepPrompts uses `id_ed25519`
- Keys stored with chmod 600 — Included in StepPrompts
- SSH keys rotated annually — documented in Key Rotation Schedule (SecurityPolicy.md line 2581)

### 5.2 MFA Requirements (Section 6.6, line 1597)

- SSH (Tailscale): Tailscale device identity + SSH key
- Tailscale ACL + SSH keypair

### 5.3 UFW Baseline (Section 9, line 1885)

```bash
ufw allow in on tailscale0 to any port 22     # SSH via Tailscale
ufw limit in on tailscale0 to any port 22     # SSH brute force protection
```

**Note:** P0-004 (UFW) will implement this. P0-002 should ensure key auth works before UFW lockdown.

### 5.4 Host Hardening (Section 2, line 172)

"Ubuntu 24.04 hardened, SSH key-only auth, fail2ban, unattended-upgrades, systemd service sandboxing"
- SSH key-only auth = **P0-002 deliverable**
- fail2ban = **P0-005**
- UFW = **P0-004**

### 5.5 Break-Glass Access (Section 2, line 200)

"samm (admin user): full system access via sudo, MFA via Discord 2FA + Tailscale SSH"

---

## 6. Acceptance Criteria Mapping

### AC-SEC-001 (from AcceptanceCriteriaCatalog_v1.0.md, line 205)

> "RBAC/ABAC must enforce default deny across human, agent, sub-agent, service, database, Redis, object storage, API, filesystem, systemd, Tailscale, crypto, backup, export, and break-glass surfaces."

**P0-002 contribution to AC-SEC-001:**
- Establishes SSH key-based auth (default deny for password auth)
- Restricts root login via SSH
- Sets up alias-based access for the `guinevere` user
- Partial fulfillment — AC-SEC-001 spans many surfaces

**Evidence path:** `evidence/security/rbac-abac-<date>.md` — NOT created by P0-002; deferred to full AC verification.

**Gap:** TEST-GAP-SEC-001 (RBAC/ABAC regression suite) and EVIDENCE-GAP-SEC-001 (no full RBAC/ABAC proof yet) are known gaps.

---

## 7. Cross-Doc Findings & Contradictions

### F1: CHECKLIST vs StepPrompts verification mismatch
- **CHECKLIST (line 100):** `ssh guinevere@vps` — tests direct user@host connection
- **StepPrompts (line 415):** `ssh guinevere-vps "whoami"` — tests alias connection
- **Issue:** CHECKLIST does not verify alias creation (which is the core deliverable).
- **Resolution:** Verify BOTH alias AND direct connection in the evidence.

### F2: SSH hardening commands in comments, not executable
- **StepPrompts lines 405-408** show hardening changes as comments, not executable commands.
- `# PermitRootLogin no` and `# PasswordAuthentication no` must be applied via actual sed/echo or drop-in config.
- **Resolution:** The SSH safety research (Section 4) recommends drop-in config pattern: create `/etc/ssh/sshd_config.d/50-hardening.conf`.

### F3: Evidence path inconsistency
- **StepPrompts:** `docs/setup-evidence/P0/STEP-P0-002/`
- **IMPLEMENTATION_GUIDE (line 133):** `evidence/phase-0/step-002/`
- **Note:** P0-001 followed StepPrompts pattern (`docs/setup-evidence/P0/STEP-P0-001/`). Follow the same to stay consistent. Future migration to canonical paths is acceptable.

### F4: P0-001 StepPrompts status not updated
- P0-001 auditor report flagged StepPrompts line 282 status still ⬜ (should be ✅).
- **Resolution:** Fix when updating P0-002 status in StepPrompts.

### F5: Pre-flight item 1.3 (SSH key-based auth) satisfied by P0-002
- CHECKLIST Section 1.3 line 61 currently unchecked. P0-002 marks this complete.

### F6: MFA requirement not addressed
- Security Policy (line 1597) requires "Tailscale device identity + SSH key" for SSH.
- P0-002 only sets up SSH key auth. Tailscale SSH identity enforcement comes with P0-022.
- **Issue:** No mention in StepPrompts that P0-002 is interim until P0-022.
- **Severity:** Low — P0-022 explicitly handles Tailscale setup.

### F7: No existing sshd_config.d/ drop-in creation
- StepPrompts hardens via comments; SSH research recommends drop-in config.
- **Resolution:** Create `/etc/ssh/sshd_config.d/50-hardening.conf` with:
  ```
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  ChallengeResponseAuthentication no
  PubkeyAuthentication yes
  PermitRootLogin no
  ```

---

## 8. Prerequisites Status

| Prerequisite | Status | Verification |
|-------------|--------|-------------|
| P0-001 complete | ✅ Yes | PROGRESS.md line 45 checked |
| SSH key pair exists locally | ⚠️ Unknown | Must check `~/.ssh/id_ed25519.pub` on operator machine |
| VPS IP known | ✅ Yes | From P0-000 audit / operator knowledge |
| Root password known | ✅ Yes | Set during VPS provisioning |
| VPS console access method known | ⚠️ Unknown | Must confirm hostdata.id web console credentials |
| Aizanta user SSH access | ✅ Yes | Must verify after P0-002 to ensure Aizanta not locked out |

---

## 9. Shared VPS Constraints

### 9.1 Aizanta Isolation Rules

| Rule | Detail |
|------|--------|
| **SSH key access** | Aizanta user's SSH key must remain valid after P0-002 |
| **AllowUsers** | If implemented, must include `aizanta` user |
| **Password auth** | Never disable until key auth verified for ALL users |
| **Root login** | Never disable until sudo verified for ALL users |
| **Aizanta verification** | `systemctl status aizanta-*` must remain green after P0-002 |

### 9.2 Resource Constraints (Not Affected by P0-002)

| Resource | Limit | Impact |
|----------|-------|--------|
| CPU | 2 cores (200%) | No SSH CPU impact |
| RAM | 8GB | No SSH RAM impact |
| Disk | 60GB | Minimal (~100KB for ssh keys) |

---

## 10. Shared Writers & Collision Scan

| Resource | Writer | Conflict Risk |
|----------|--------|--------------|
| `~/.ssh/config` | LOCAL machine | No conflict — single operator machine |
| `~/.ssh/authorized_keys` | VPS: root + guinevere | No conflict — P0-002 is the only step touching SSH keys |
| `/etc/ssh/sshd_config` | VPS | P0-002 creates drop-in; P0-004 (UFW) and P0-022 (Tailscale) reference SSH config |
| `/etc/ssh/sshd_config.d/50-hardening.conf` | VPS | Exclusive to P0-002 |
| **PROGRESS.md** | **Parent-only** | Update after P0-002 completion |
| **CHECKLIST.md** | **Parent-only** | Update after P0-002 completion |
| **StepPrompts.md** | **Parent-only** | Update status + F4 fix |
| **docs/setup-evidence/P0/STEP-P0-002/** | P0-002 | Exclusive |

**Conclusion:** No collision with other in-flight steps. P0-002 is safe to execute standalone.

---

## 11. Recommended Execution Sequence (Synthesized)

Based on SSH safety research + StepPrompts + Security Policy:

```text
Phase 0: LOCAL PREPARATION (on operator machine)
  1. Verify SSH key exists: test -f ~/.ssh/id_ed25519.pub
  2. If not, generate: ssh-keygen -t ed25519 -C "samm@guinevere"

Phase 1: VPS — INSTALL KEY (on operator machine to VPS)
  3. BACKUP /etc/ssh on VPS: sudo cp -a /etc/ssh /etc/ssh.backup.$(date +%Y%m%d)
  4. ssh-copy-id root@<vps-ip>       (using root password)
  5. ssh-copy-id guinevere@<vps-ip>  (using guinevere password)
  6. TEST root key login in SECOND terminal (KEEP FIRST SESSION OPEN)
  7. TEST guinevere key login in SECOND terminal

Phase 2: VPS — HARDENING (on operator machine to VPS)
  8. Validate config: sudo mkdir -p /run/sshd && sudo sshd -t
  9. Create drop-in: /etc/ssh/sshd_config.d/50-hardening.conf
     (PasswordAuthentication no, PermitRootLogin no, PubkeyAuthentication yes)
  10. Validate again: sudo sshd -t
  11. RELOAD (not restart): sudo systemctl reload ssh

Phase 3: LOCAL — ALIAS (on operator machine)
  12. Add SSH alias to ~/.ssh/config (Host: guinevere-vps)
  13. Set permissions: chmod 600 ~/.ssh/config
  14. TEST alias: ssh guinevere-vps "whoami && hostname"

Phase 4: VERIFICATION
  15. Verify Aizanta: systemctl status aizanta-* (all still running)
  16. Test guinevere user exists, home accessible
  17. BOTH alias AND direct ssh guinevere@<vps-ip> work

Phase 5: EVIDENCE
  18. Capture ssh-test.log (verification output)
  19. Capture ssh-config.txt (alias config)
  20. Write aizanta-post-check.md (Aizanta unaffected proof)

Phase 6: DOCUMENTATION UPDATE
  21. Update StepPrompts.md: P0-002 status → ✅
  22. Fix F4: P0-001 StepPrompts status → ✅
  23. Update PROGRESS.md: P0-002 → [x]
  24. Update CHECKLIST.md: P0-002 checked, Section 1.3 line 61 checked
```

---

## 12. Blockers & Risks

### Blocking Issues: 0

### Non-Blocking Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| VPS lockout if config breaks | **HIGH** | Keep first session open; use `reload` not `restart`; know VPS console access |
| Aizanta user locked out if AllowUsers misconfigured | **HIGH** | Do NOT use `AllowUsers` in Phase 2; only apply PasswordAuthentication + PermitRootLogin |
| SSH key not existing on local machine | **LOW** | StepPrompts includes gen command; verify pre-flight |
| Ubuntu 24.04 socket activation trap | **MEDIUM** | Use `ssh` (not `sshd`), `ssh.socket` for status, `mkdir -p /run/sshd` before `sshd -t` |
| StepPrompts hardening comments not executable | **MEDIUM** | SSH research provides executable drop-in config pattern |
| P0-002 is interim until P0-022 (Tailscale locks SSH) | **LOW** | Post-P0-022, SSH can be locked to Tailscale interface; document in evidence |
| Evidence path inconsistency | **LOW** | Follow StepPrompts pattern (docs/setup-evidence/...) |
| AC-SEC-001 evidence not produced | **LOW** | AC-SEC-001 is broader than SSH; specific SSH evidence is sufficient for P0-002 |

---

## 13. Verdict Summary

| Dimension | Status |
|-----------|--------|
| **Blocking issues** | 0 |
| **Process findings** | 7 (F1-F7, all non-blocking) |
| **Prerequisites** | 6 of 6 (2 unknown — key existence, VPS console access) |
| **Shared writer conflicts** | None |
| **ADR compliance** | ADR-019 constraints documented (P0-002 is interim until P0-022) |
| **Safety boundaries** | SSH key auth, no secret exposure, Aizanta isolation preserved |
| **Security Policy alignment** | SSH key controls (Ed25519, chmod 600) aligned; MFA deferred to P0-022 |
| **Ready for implementation** | **YES** — with SSH safety research recommendations applied |
