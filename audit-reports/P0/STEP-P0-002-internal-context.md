# STEP-P0-002 Internal Context Report

**Step:** P0-002 — SSH Config Update (alias for easy access)
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Scope:** Internal repo/doc context audit — read-only, no VPS changes
**Auditor:** Internal context collector (pre-implementation)

---

## 1. Source of Truth: StepPrompts.md (P0-002)

**File:** `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md` — Lines 358–441

| Field | Value |
|-------|-------|
| Type | Security |
| Status | ⬜ Not Started |
| Risk | High |
| Dependencies | P0-001 (guinevere user created) |
| Cost Impact | $0/month |
| ADR References | ADR-019 |
| Acceptance Criteria | AC-SEC-001 |
| Estimated Time | 30 minutes |

### Required Commands (from StepPrompts)

1. **Generate SSH key**: `test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -C "samm@guinevere" -f ~/.ssh/id_ed25519 -N ""`
2. **Copy key to root**: `ssh-copy-id root@<vps-ip>`
3. **Copy key to guinevere**: `ssh-copy-id guinevere@<vps-ip>`
4. **Add SSH alias** to `~/.ssh/config` (Host: guinevere-vps, with ServerAliveInterval 60)
5. **Set permissions**: `chmod 600 ~/.ssh/config`
6. **Harden SSH server** (VPS side): `PermitRootLogin no` + `PasswordAuthentication no` via sed/sshd_config
7. **Test**: `ssh guinevere-vps "whoami && hostname"`

### Evidence Paths (from StepPrompts)

- `docs/setup-evidence/P0/STEP-P0-002/ssh-test.log`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt`

---

## 2. Tracker State

### PROGRESS.md (Line 46)

- **Status:** `- [ ] **P0-002**` — NOT checked
- P0-000 and P0-001 are complete (2/257 steps)

### CHECKLIST.md (Line 100)

- **Status:** `- [ ] P0-002` — NOT checked
- Pre-Flight item 1.3 (SSH key-based auth): NOT checked

---

## 3. ADR-019 Constraints

**Status:** Accepted with notes | **Risk:** HIGH

| Constraint | Detail |
|------------|--------|
| Zero public ports | SSH is emergency/management access; all admin surfaces Tailscale-internal |
| Tailscale mesh | All devices join tailnet |
| Auth key expiry | 180-day default; document renewal |
| Lockout recovery | VPS console, offline recovery key, DERP relay documented |

---

## 4. Existing Evidence

| Path | Exists? |
|------|---------|
| `docs/setup-evidence/P0/STEP-P0-002/*` | No (no prior attempt) |
| `evidence/phase-0/step-002/*` | No (other path convention) |

---

## 5. Cross-Doc Findings

### F1: CHECKLIST vs StepPrompts verification mismatch
- CHECKLIST (line 100): `ssh guinevere@vps` — tests raw user@host
- StepPrompts (line 415): `ssh guinevere-vps "whoami"` — tests alias
- **Issue:** CHECKLIST does not verify alias creation (core deliverable). Verify BOTH.

### F2: SSH hardening commands in comments, not executable (H-12)
- StepPrompts lines 405-408 show `PermitRootLogin no` + `PasswordAuthentication no` as comments
- Must be converted to sed/echo commands for automated/scripted execution
- Sequence is correct: root enabled → copy keys → disable root

### F3: Evidence path inconsistency
- StepPrompts: `docs/setup-evidence/P0/STEP-P0-002/`
- IMPLEMENTATION_GUIDE: `evidence/phase-0/step-002/`
- P0-001 followed StepPrompts pattern. Follow the same.

### F4: P0-001 StepPrompts status not updated
- P0-001 auditor report flagged StepPrompts line 282 status still ⬜. Fix when working P0-002.

### F5: Pre-flight item 1.3 will be satisfied by P0-002
- CHECKLIST Section 1.3 line 61: SSH key-based auth enforced — currently unchecked

---

## 6. Prerequisites Status

| Prerequisite | Status |
|--------------|--------|
| P0-001 complete | yes |
| SSH key pair exists locally | check on local machine |
| VPS IP known | from P0-000 audit / operator |
| Root password known | yes (set during VPS provisioning) |

---

## 7. Execution Checklist for Downstream

- [ ] Verify local SSH key pair exists
- [ ] Confirm VPS IP + have console backup access
- [ ] Run step commands in sequence (root enabled → key copy → disable root)
- [ ] Test BOTH alias (`ssh guinevere-vps`) and direct (`ssh guinevere@<ip>`)
- [ ] Create evidence at `docs/setup-evidence/P0/STEP-P0-002/` + aizanta-post-check.md + summary
- [ ] Update PROGRESS.md, CHECKLIST.md, StepPrompts.md status

---

## 8. Verdict

**Blocking issues:** 0
**Process findings:** 5 (F1-F5, all non-blocking)
**Ready for execution:** yes
