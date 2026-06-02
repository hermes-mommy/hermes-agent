# STEP-P0-010 — Internal Context Report (Pre-Implementation)

| Field | Value |
|---|---|
| **Report Type** | Pre-implementation context synthesis |
| **Step** | P0-010 — Docker Network Creation |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (parent orchestrator, research wave) |
| **Status** | READY — all context gathered, no blockers |
| **Downstream Use** | Plan implementation, verify no subnet overlap, structure evidence |
| **Sources** | 12 files across 5 category roots |

---

## 1. Exact Scope Extraction

**Source**: `stepprompts/StepPrompts.md` lines 1083-1157

### 1.1 Metadata

| Field | Value |
|---|---|
| Type | Infrastructure |
| Status | Not Started (`⬜`) |
| Risk | Low |
| Git Commit | `chore(P0): pending` |
| Goal | Create isolated Docker network `guinevere-net` for Guinevere containers, separate from Aizanta |
| Dependencies | P0-003 (directory structure) — **COMPLETE** ✅ |
| Cost | $0/month |
| ADR Refs | ADR-014 (VPS & Container Architecture) |
| AC Refs | AC-CORE-002 (Tailscale-internal, zero public admin ports) |
| Estimated Time | 30 minutes |

### 1.2 Context (verbatim)

> Guinevere uses Docker for Prometheus, Grafana, and Loki. An isolated network prevents accidental container communication between Guinevere and Aizanta services.

### 1.3 Pre-flight Checks

| # | Check | Command | Status |
|---|---|---|---|
| 1 | Docker installed | `docker --version` | ✅ Known active (docker.service running per P0-000 audit) |
| 2 | Existing Docker networks documented | `docker network ls` | ⚠️ **GAP** — P0-000 audit does NOT include `docker network ls` output |

### 1.4 Commands (4 blocks)

```bash
# BLOCK 1: Pre-flight — check existing networks
docker network ls

# BLOCK 2: Install Docker if missing (Docker CE + compose plugin)
# NOTE: Docker already present on VPS. Block is conditional-only.
docker --version || {
  sudo apt update
  sudo apt install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker guinevere
}

# BLOCK 3: Create Guinevere-specific Docker network
docker network create --driver bridge --subnet=172.28.0.0/16 guinevere-net

# BLOCK 4: Verify
docker network ls
docker network inspect guinevere-net

# BLOCK 4b: Ensure Aizanta network exists separately
docker network inspect aizanta-net 2>/dev/null || echo "No aizanta-net (may use default)"
```

### 1.5 Definition of Done

| # | Criterion | Verification Command |
|---|---|---|
| 1 | guinevere-net exists | `docker network ls` shows `guinevere-net` |
| 2 | Subnet correct | `docker network inspect guinevere-net` shows `172.28.0.0/16` |
| 3 | No overlap with Aizanta | Subnet does not conflict with Aizanta network(s) |
| 4 | Docker running | `docker info` shows no errors |

### 1.6 Evidence (Single)

- `docs/setup-evidence/P0/STEP-P0-010/docker-network.txt`
- StepPrompts does **not** explicitly require `verification.md`, `p0-010-summary.md`, or `aizanta-post-check.md`.
- **However**: Every completed P0 step (P0-001 through P0-008) produced these additional files:
  - `verification.md` — structured 10-section evidence report
  - `p0-NNN-summary.md` — human-readable summary
  - `aizanta-post-check.md` — Aizanta health verification after change

### 1.7 Rollback

```bash
docker network rm guinevere-net
```

### 1.8 Troubleshooting

| Issue | Cause | Resolution |
|---|---|---|
| `docker network create` fails with "pool overlaps" | Subnet conflict with existing Docker network | Choose different subnet. Check all: `docker network ls -q \| xargs docker network inspect --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'` |
| `guinevere` user can't run docker | User not in `docker` group | `sudo usermod -aG docker guinevere` then `newgrp docker` |

### 1.9 Notes (verbatim)

- ⚠️ **Shared VPS:** Aizanta containers must NOT be on guinevere-net.
- All Guinevere Docker services use `networks: [guinevere-net]` in docker-compose.yml.

---

## 2. Current State (PROGRESS.md)

**Source**: `PROGRESS.md` lines 41-73

### 2.1 Phase 0 Progress

| Metric | Value |
|---|---|
| P0 total steps | 29 |
| Completed | 9 / 29 (31%) |
| Last completed | P0-008 (NTP + timezone) |
| Next incomplete | P0-009 (cgroup resource limits) |
| P0-010 status | ⬜ Unchecked — **NOT STARTED** |

### 2.2 Relevant Completed Dependencies

| Step | Status | Relevance to P0-010 |
|---|---|---|
| P0-000 (VPS Audit) | ✅ Complete | Documents Docker present, Aizanta containers running. **Gap**: no `docker network ls` in audit output. |
| P0-001 (guinevere user) | ✅ Complete | User exists (`guinevere:guinevere`) |
| P0-003 (Directory structure) | ✅ Complete | Explicit dependency per StepPrompts — `/home/guinevere/` tree ready |
| P0-008 (NTP + timezone) | ✅ Complete | Host in stable state, services healthy |

### 2.3 P0-009 (cgroup limits) — Not a dependency

StepPrompts lists only P0-003 as a dependency for P0-010. P0-009 is **not** a prerequisite. However, P0-009 logically runs before P0-010 in sequential order and is currently unchecked. Decision: P0-010 can run before or after P0-009 — they are independent. No shared state.

---

## 3. Verification Line (CHECKLIST.md)

**Source**: `CHECKLIST.md` line 109

```markdown
- [ ] P0-010: `docker network ls | grep guinevere-net` -> exists, bridge;
  `docker network inspect` -> different subnet from aizanta-net
```

**CHECKLIST also references P0-010 in**:

| Line | Context |
|---|---|
| 109 | Step verification (unchecked) |
| 134 | Integration test: "Docker guinevere-net isolated from aizanta-net; SOPS decrypts correctly" |
| 150-155 | Phase 0 complete criteria (all 29 steps verified) |

---

## 4. ADR-014 — Docker Network Isolation Constraints

**Source**: `adr/ADR-014-vps-container-architecture.md` (121 lines)

### 4.1 ADR Summary

| Field | Value |
|---|---|
| Status | Accepted |
| Risk Level | HIGH |
| Date | 2026-05-30 |
| Decision | Single primary VPS with systemd and selective containers |
| Deciders | Faiz (Owner) + Guinevere (Executor) |

### 4.2 What ADR-014 Says About Docker Networks

ADR-014 does **not** explicitly prescribe specific Docker network subnets or naming. It establishes the architecture:

- Selective containerization for supporting services (Prometheus, Grafana, Loki)
- Systemd-managed core services (Python/FastAPI)
- Single VPS deployment with isolation from unrelated tenants

### 4.3 What ADR-014 Delegates to StepPrompts

The actual Docker network configuration (`guinevere-net`, `172.28.0.0/16`, bridge driver) is defined in StepPrompts.md and the IMPLEMENTATION_GUIDE.md isolation matrix. ADR-014 provides the architectural authorization for containerization; StepPrompts provides the implementation detail.

### 4.4 ADR-014 Implementation Notes

- Must not be edited in-place for material changes — create superseding ADR
- Proposed ADRs require Faiz approval
- Evidence must be file-based

---

## 5. IMPLEMENTATION_GUIDE.md Guidance

**Source**: `docs/IMPLEMENTATION_GUIDE.md` lines 265-303, 420-426

### 5.1 Shared VPS Isolation Matrix

| Resource | Guinevere | Aizanta | Rule |
|---|---|---|---|
| Docker network | `guinevere-net` | `aizanta-net` | No cross-network |

### 5.2 Resource Allocation

| Resource | Guinevere | Aizanta | OS | Total |
|---|---|---|---|---|
| CPU | 2 cores | 1.5 cores | 0.5 | 4 cores |
| RAM | 8GB | 6GB | 2GB | 16GB |

### 5.3 Post-Step Aizanta Verification

```bash
systemctl status aizanta-*                          # services running
docker ps --filter "name=aizanta"                   # containers up
psql -U aizanta -d aizanta -c "SELECT 1"           # DB accessible
redis-cli -n 10 PING                                # Redis responding
```

### 5.4 Shared VPS Conflict Verification

```bash
docker network inspect guinevere-net | grep -i aizanta    # Expected: no results
```

---

## 6. Docker Network References (Repo-wide)

**Source**: `grep` across entire workspace for `guinevere-net|docker network|aizanta-net|docker-compose`

### 6.1 Files Referencing `guinevere-net` or Docker networks (24 files, 104 matches)

| File | Context |
|---|---|
| `stepprompts/StepPrompts.md` | Step P0-010 definition; docker-compose services for Gotify (P2-020), Prometheus (P8-001) |
| `stepprompts/StepPrompts.md.bak` | Backup — identical |
| `PROGRESS.md` (line 54) | P0-010 unchecked |
| `CHECKLIST.md` (lines 109, 134) | Verification commands |
| `docs/IMPLEMENTATION_GUIDE.md` (lines 277, 425) | Isolation matrix; conflict check |
| `audit-reports/stepprompts-audit/D3-D4-security-sharedvps.md` (line 340) | [MEDIUM] Subnet overlap not pre-checked |
| `audit-reports/stepprompts-audit/D2-D5-adr-dependency.md` (line 282) | Dependency ordering correct |
| `audit-reports/P0/STEP-P0-004/internal-context-report.md` (line 196) | Docker iptables bypass UFW note |
| `audit-reports/2026-05-31-implementation-synthesis.md` (lines 104, 484, 600) | Step definition |

### 6.2 Key Finding: `aizanta-net` Does NOT Exist — May Be Virtual

StepPrompts line 1130:
```bash
docker network inspect aizanta-net 2>/dev/null || echo "No aizanta-net (may use default)"
```

The fallback message **"may use default"** implies Aizanta may not use a custom Docker network at all — its containers might be on Docker's default bridge network. This is a critical assumption that must be verified at runtime via `docker network ls`.

### 6.3 All Consuming Services (future steps using guinevere-net)

| Step | Service | docker-compose ref |
|---|---|---|
| P2-020 | Gotify | `networks: [guinevere-net]` (line 6184-6190) |
| P8-001 | Prometheus | `networks: [guinevere-net]` (line 7787) |
| P8-001 | Grafana | `networks: [guinevere-net]` (line 7798) |
| P8-001 | Loki | `networks: [guinevere-net]` (line 7805) |

All future docker-compose.yml files declare `networks:` with `guinevere-net:` as external.

---

## 7. Evidence Schema (Canonical from P0-008)

**Source**: `docs/setup-evidence/P0/STEP-P0-008/verification.md` (163 lines)

### 7.1 Canonical 10-Section Template

| Section | Required? | Content |
|---|---|---|
| 1. What Was Done | Yes | High-level summary |
| 2. Files Changed | Yes | Remote (VPS) + Local (repo) tables |
| 3. Validation Results | Yes | Command output snippets with PASS/FAIL |
| 4. Evidence Artifacts | Yes | Table of all evidence files |
| 5. Shared VPS Impact | Yes | Aizanta health, container/port checks |
| 6. ADR Compliance | Yes | ADR-by-ADR status table |
| 7. AC Reference | Yes | AC-by-AC status table |
| 8. Rollback / Re-run Safety | Yes | Rollback commands + idempotency note |
| 9. Design Decisions / Caveats | Yes | Numbered list |
| 10. Evidence Gate + Footer | Yes | Parent verification, auditor gate, metadata |

### 7.2 P0-010 Evidence Files to Produce

| File | Content | Canonical? |
|---|---|---|
| `docs/setup-evidence/P0/STEP-P0-010/docker-network.txt` | Raw command output (docker network ls, inspect) | StepPrompts-required |
| `docs/setup-evidence/P0/STEP-P0-010/verification.md` | Structured 10-section report | Convention (P0-001–P0-008) |
| `docs/setup-evidence/P0/STEP-P0-010/p0-010-summary.md` | Human-readable summary | Convention |
| `docs/setup-evidence/P0/STEP-P0-010/aizanta-post-check.md` | Aizanta health after change | Convention (though Docker network creation has low Aizanta impact) |

---

## 8. Shared Writers (Collision Scan)

### 8.1 Files That Must Be Updated

| File | Owner | Rationale |
|---|---|---|
| `PROGRESS.md` (lines 53-54) | **Parent-only** | Check P0-010, update counters (9→10 completed) |
| `CHECKLIST.md` (line 109) | **Parent-only** | Check P0-010 line |
| `stepprompts/StepPrompts.md` (line 1086, 1100-1136) | **Parent-only** | Update status to ✅, check pre-flight and verification items |

### 8.2 Exclusive Ownership — No Conflicts

- P0-010 creates only Docker network `guinevere-net` on VPS → **no file collision with any other step**
- No other step creates Docker networks
- Docker engine is shared runtime with Aizanta but P0-010 only adds a network — does not modify Aizanta containers or their networks

### 8.3 Safe Parallel Execution

P0-010 can run in parallel with P0-009 (cgroup limits) — they touch different files and different VPS resources:
- P0-009: `/etc/systemd/system/guinevere.slice`, `MemoryMax=8G`, `CPUQuota=200%`
- P0-010: Docker network `guinevere-net`, no systemd or filesystem changes

---

## 9. Evidence Root

### 9.1 Directory Structure

```
docs/setup-evidence/P0/STEP-P0-010/   ← must be created
├── docker-network.txt                 ← StepPrompts-required
├── verification.md                    ← Convention
├── p0-010-summary.md                  ← Convention
├── aizanta-post-check.md             ← Convention
```

Also:
```
audit-reports/P0/STEP-P0-010/
└── internal-context-report.md         ← This file
└── step-p0-010-auditor-report.md      ← Post-implementation auditor gate
```

### 9.2 Pre-existing Evidence

- Directory `docs/setup-evidence/P0/STEP-P0-010/` — **does not exist yet** (must be created)
- Directory `audit-reports/P0/STEP-P0-010/` — **exists, contains this report only**

---

## 10. Cross-Doc Consistency Analysis

### 10.1 Consistent Across All Sources

| Aspect | Source | Value | Match? |
|---|---|---|---|
| Subnet | StepPrompts, CHECKLIST, all docker-compose refs | `172.28.0.0/16` | ✅ All consistent |
| Network name | StepPrompts, IMPLEMENTATION_GUIDE, docker-compose | `guinevere-net` | ✅ All consistent |
| Isolation rule | StepPrompts, IMPLEMENTATION_GUIDE, ADR checklists | No cross-network | ✅ All consistent |
| Dependencies | StepPrompts | P0-003 only | ✅ Single source of truth |
| ADR ref | StepPrompts | ADR-014 | ✅ Matches |
| AC ref | StepPrompts | AC-CORE-002 | ✅ Matches |

### 10.2 No Contradictions Found

All cross-references are consistent. No document prescribes a conflicting subnet, driver, or isolation policy.

---

## 11. Blocker Analysis

### 11.0 Dependency Check: P0-010 Depends on P0-003

P0-003 (directory structure) — **COMPLETE** ✅. No unmet dependencies.

### 11.1 Resolved: Docker Already Installed

Docker CE is already active on the VPS (per P0-000 audit: `docker.service loaded active running`). The conditional Docker installation block (Block 2) will not execute. `docker-compose-plugin` is already installed (per StepPrompts Docker install command line 1118 which includes it).

### 11.2 Resolved: No Cross-Doc Contradictions

Verified above (§10). All sources agree on subnet, network name, and isolation policy.

### 11.3 KNOWN GAP: Missing `docker network ls` in P0-000 Audit

**Severity: MEDIUM** (also flagged by D3-D4 security audit, line 340)

The P0-000 VPS audit captured `docker ps -a` but did **not** capture `docker network ls`. This means:
- We don't know what Docker networks exist on the VPS
- We can't pre-verify that `172.28.0.0/16` doesn't overlap

**Mitigation**: The first step of P0-010 execution must be `docker network ls` on the VPS to capture current state before creating `guinevere-net`. If there is a conflict, fall back to the troubleshooting subnet search command.

### 11.4 NON-ISSUE: aizanta-net May Not Exist

StepPrompts itself acknowledges this possibility with the fallback message `"No aizanta-net (may use default)"`. Aizanta containers may all be on Docker's default bridge (`172.17.0.0/16`), which does not conflict with our `172.28.0.0/16`.

### 11.5 NO BLOCKERS

All dependencies met. All cross-docs consistent. Known gap has mitigation. **Ready to implement.**

---

## 12. Implementation Checklist (Verbatim from StepPrompts)

### Pre-flight (before any create command)
- [ ] `docker network ls` — capture existing networks
- [ ] `docker --version` — confirm Docker installed
- [ ] `docker info` — confirm daemon healthy
- [ ] `docker network inspect aizanta-net 2>/dev/null || echo "No aizanta-net (may use default)"` — check Aizanta network

### Creation
- [ ] `docker network create --driver bridge --subnet=172.28.0.0/16 guinevere-net`
- [ ] If "pool overlaps" error: run `docker network ls -q | xargs docker network inspect --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'` and pick non-conflicting subnet

### Verification (post-create)
- [ ] `docker network ls` confirms guinevere-net exists
- [ ] `docker network inspect guinevere-net` confirms subnet 172.28.0.0/16
- [ ] `docker network inspect guinevere-net` confirms driver is bridge
- [ ] No Aizanta container is on guinevere-net: `docker network inspect guinevere-net | grep -i aizanta` returns empty

### Aizanta Health (post-create)
- [ ] `docker ps --filter "name=aizanta"` — all 5 containers still running
- [ ] `systemctl status aizanta-*` — Aizanta systemd services still active
- [ ] No Aizanta container connected to guinevere-net

### Evidence (local repo)
- [ ] Create `docs/setup-evidence/P0/STEP-P0-010/docker-network.txt` (raw output)
- [ ] Create `docs/setup-evidence/P0/STEP-P0-010/verification.md` (structured report)
- [ ] Create `docs/setup-evidence/P0/STEP-P0-010/p0-010-summary.md`
- [ ] Create `docs/setup-evidence/P0/STEP-P0-010/aizanta-post-check.md`

### Parent-only Updates (do not attempt)
- [ ] Update `PROGRESS.md` — check P0-010, update counters
- [ ] Update `CHECKLIST.md` — check P0-010 line
- [ ] Update `stepprompts/StepPrompts.md` — status, pre-flight, verification check marks

### Auditor Gate
- [ ] Spawn independent auditor after evidence written: `audit-reports/P0/STEP-P0-010/step-p0-010-auditor-report.md`

---

## 13. Source File Index

| # | File | Lines/Scope | What It Provides |
|---|---|---|---|
| 1 | `stepprompts/StepPrompts.md` | 1083-1157 | Scope, commands, DoD, evidence, rollback, troubleshooting |
| 2 | `PROGRESS.md` | 41-73 | Current state: P0-010 unchecked, P0-003 ✅ |
| 3 | `CHECKLIST.md` | 108-109, 130-155 | Verification command, integration test, phase criteria |
| 4 | `adr/ADR-014-vps-container-architecture.md` | Full | Architecture authorization for containerization |
| 5 | `docs/IMPLEMENTATION_GUIDE.md` | 265-303, 420-426 | Isolation matrix, Aizanta verify commands |
| 6 | `docs/setup-evidence/P0/STEP-P0-000/vps-audit-2026-05-31.txt` | Full | Docker present, Aizanta containers running (no `docker network ls`) |
| 7 | `docs/setup-evidence/P0/STEP-P0-008/verification.md` | Full | Canonical 10-section evidence template |
| 8 | `docs/setup-evidence/P0/STEP-P0-003/verification.md` | Full | Dependency verification pattern, SSH access patterns |
| 9 | `audit-reports/stepprompts-audit/D3-D4-security-sharedvps.md` | 340-344 | [MEDIUM] Subnet overlap not pre-checked |
| 10 | `audit-reports/2026-05-31-implementation-synthesis.md` | 95-136 | P0 implementation overview |
| 11 | `audit-reports/P0/STEP-P0-004/internal-context-report.md` | 190-196 | Docker iptables bypass UFW note |
| 12 | `stepprompts/StepPrompts.md` | 1-37 | Shared VPS context, port assignments |

---

## 14. Footer

**Source task**: STEP-P0-010 internal context research (pre-implementation)
**Date**: 2026-05-31
**Author**: Guinevere (parent orchestrator)
**Method**: 12 source files read, 7 grep/glob searches, cross-validation across 5 doc categories
**Verdict**: READY TO IMPLEMENT — zero blockers, all dependencies met, known gaps have mitigations
