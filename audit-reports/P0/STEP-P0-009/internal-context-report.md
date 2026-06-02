# STEP-P0-009 Internal Context Report — cgroup Resource Limits

| Field | Value |
|---|---|
| **Report Type** | Pre-implementation context synthesis |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (parent orchestrator) |
| **Step** | P0-009 — cgroup Resource Limits |
| **Purpose** | Provide complete implementation context before any execution |

---

## 1. Exact Scope (from StepPrompts.md lines 998-1081)

### Goal
Configure cgroup resource limits to prevent Guinevere from starving Aizanta or the OS on the shared VPS (hostdata.id, 4C/16GB, Ubuntu 24.04).

### Resource Allocation Profile

| Resource | Guinevere | Aizanta | OS | Implementation |
|---|---|---|---|---|
| RAM | 8GB | 6GB | 2GB | `MemoryMax=8G`, `MemoryHigh=7G` |
| CPU | 2 cores | 1.5 cores | 0.5 | `CPUQuota=200%` |
| IO | Lower priority | Normal | Highest | `IOWeight=50` |
| Tasks | 512 max | — | — | `TasksMax=512` |

### What Gets Created

**Single file** on VPS: `/etc/systemd/system/guinevere.slice`

```
[Unit]
Description=Guinevere Resource Slice
Before=slices.target

[Slice]
MemoryMax=8G
MemoryHigh=7G
CPUQuota=200%
IOWeight=50
TasksMax=512
```

### What Gets Executed
1. `sudo tee /etc/systemd/system/guinevere.slice` (create slice unit)
2. `sudo systemctl daemon-reload`
3. `sudo systemctl start guinevere.slice`
4. Verify: `systemctl status guinevere.slice`, cgroupv2 checks

### What Does NOT Get Touched (critical distinction)

**No existing service units are modified in this step.** The `Slice=guinevere.slice` directive is added to service unit files at creation time during later phases:
- P1-018 (`guinevere-core.service`)
- P2-017 (`guinevere-discord.service`)
- P5-018 (`guinevere-loops.service`)
- P5-019 (`guinevere-scheduler.service`)
- P6-001 (`guinevere-mcp.service`)
- P7-018 (`guinevere-surveillance.service`)
- P8-021 (`guinevere-monitoring.service`)
- P1-006 (`guinevere-9router.service`)

11 total service units across StepPrompts.md already have `Slice=guinevere.slice` in their definitions. The slice itself will be empty (no processes assigned) until those future services are created and started.

---

## 2. Dependencies

### Upstream (MUST be complete)
| Dependency | Status | Impact if missing |
|---|---|---|
| P0-001 (guinevere user created) | ✅ Complete | Slice can't be tied to user context; systemd user-=.slice won't apply |
| VPS SSH access | ✅ Confirmed | Required for all sudo commands |

### Downstream (Steps that depend on P0-009)
| Step | How it depends |
|---|---|
| **P0-014** (PostgreSQL 16) | Pre-flight check: "P0-009 complete (cgroup limits set)" — line 1462 |
| **P0-028** (Pre-flight verification) | Checks `systemctl is-active guinevere.slice` + `memory.max == 8589934592` — lines 3123-3124 |
| **All service unit steps** (P1-018, P2-017, etc.) | Each adds `Slice=guinevere.slice` — slice must exist first |

### Parallel constraint
P0-010 (Docker network) through P0-013 (secrets) may run in parallel with P0-009 *as long as they don't touch systemd slices*. But P0-014 hard-depends on P0-009.

---

## 3. ADR References

### ADR-014 (VPS & Container Architecture)
- **Status**: Accepted (2026-05-30)
- **Risk level**: HIGH
- **Relevance**: This is the authority for the single-VPS deployment model. The resource limits exist because ADR-014 chose shared VPS (not Kubernetes, not local-only).
- **Key quote**: "Resource saturation can affect all services" — this is the risk cgroup limits mitigate.
- **ADR-014 does NOT specify exact limit values.** Those come from the Implementation Guide resource allocation table.

### No other ADRs directly reference cgroup limits for P0-009.
ADR-028 (Ollama) references a 4GB RAM cap but that's for a specific service level, not the system-wide slice.

---

## 4. Acceptance Criteria

### AC-CORE-001 (referenced by P0-009)
> "Guinevere core daemon must run as a managed systemd unit... and must recover through systemd restart without manual shell intervention."

**Relevance**: The cgroup slice is the resource enforcement layer that systemd uses to manage the core daemon. AC-CORE-001 doesn't directly verify cgroup, but the slice is infrastructure that enables the managed-systemd-unit constraint in AC-CORE-001.

### CHECKLIST.md P0-009 line (line 108)
```
P0-009: cat /etc/systemd/system/guinevere-*.slice -> MemoryMax=8G, CPUQuota=200%
```

### P0-028 verification references (lines 3123-3124)
```
systemctl is-active guinevere.slice && echo "PASS: Resource slice active" || echo "FAIL: Slice"
cat /sys/fs/cgroup/guinevere.slice/memory.max | grep -q "8589934592" && echo "PASS: 8GB memory limit" || echo "FAIL: Memory limit"
```

---

## 5. Verification Commands

### From StepPrompts.md (lines 1054-1058)

| Check | Command | Expected |
|---|---|---|
| Slice active | `systemctl status guinevere.slice` | Active state |
| Memory limit | `cat /sys/fs/cgroup/guinevere.slice/memory.max` | `8589934592` (8GB in bytes) |
| CPU quota | `cat /sys/fs/cgroup/guinevere.slice/cpu.max` | `200000 100000` (200%) |
| Tasks limited | `systemctl show guinevere.slice -p TasksMax` | `512` |

### Additional verification (CHECKLIST.md + IMPLEMENTATION_GUIDE.md)

| Check | Command | Source |
|---|---|---|
| File exists | `ls -la /etc/systemd/system/guinevere.slice` | CHECKLIST |
| Aizanta unaffected | `systemctl status aizanta-*; docker ps \| grep aizanta` | IMPLEMENTATION_GUIDE §6 |
| No resource change | `free -h \| head -2` | IMPLEMENTATION_GUIDE |
| cgroup v2 check | `stat /sys/fs/cgroup/cgroup.controllers` | StepPrompts troubleshooting |

---

## 6. Evidence Convention (from P0-008 template)

### Evidence root
`docs/setup-evidence/P0/STEP-P0-009/`

### Required evidence files (from StepPrompts)

| File | Content | Format |
|---|---|---|
| `guinevere-slice.conf` | Copy of `/etc/systemd/system/guinevere.slice` | Text |
| `cgroup-status.txt` | Raw output of verification commands | Text |

### Canonical evidence files (extrapolated from P0-008 pattern)

Following the P0-008 evidence structure, P0-009 should produce:

| File | Content |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf` | Exact slice unit file deployed |
| `docs/setup-evidence/P0/STEP-P0-009/cgroup-status.txt` | systemctl status + cgroup knob values |
| `docs/setup-evidence/P0/STEP-P0-009/aizanta-post-check.md` | Aizanta health after cgroup configuration |
| `docs/setup-evidence/P0/STEP-P0-009/verification.md` | Full verification report (P0-008 schema) |
| `docs/setup-evidence/P0/STEP-P0-009/p0-009-summary.md` | Human-readable summary |

### Evidence minimum schema (from AGENTS.md Appendix B)

1. What Was Done
2. Files Changed (remote + local)
3. Validation Results
4. Evidence Artifacts
5. Shared VPS Impact
6. ADR Compliance
7. AC Reference
8. Rollback / Re-run Safety
9. Design Decisions / Caveats
10. Auditor Gate

---

## 7. Shared Writers (collision scan)

### Parent-only files (must not be delegated)
| File | Reason | Current state |
|---|---|---|
| `PROGRESS.md` | Status tracker | Parent updates after step |
| `CHECKLIST.md` | Verification checklist | Parent checks P0-009 line |
| `stepprompts/StepPrompts.md` | Step definitions | Parent updates status |

### Step-exclusive files (no collision risk)
| File | Owner | Notes |
|---|---|---|
| `/etc/systemd/system/guinevere.slice` | P0-009 exclusive | No other step creates or touches this |
| `docs/setup-evidence/P0/STEP-P0-009/*` | P0-009 exclusive | Evidence namespace scoped to step |

### Collision scan result: **CLEAR**

No other active step modifies:
- `/etc/systemd/system/guinevere.slice` — exclusive to P0-009
- Systemd daemon — `daemon-reload` is safe, only P0-009 does it in this context
- The `guinevere.slice` cgroup — no other step starts or stops it

---

## 8. Pre-existing References to guinevere.slice in Repo

### In StepPrompts.md (11 service units reference `Slice=guinevere.slice`)
All are in future phase service definitions — none exist on VPS yet.

### In CHECKLIST.md
- Line 108: P0-009 verification
- Line 142: P0 security checks: "cgroup: 8GB RAM / 2 CPU max; Aizanta unaffected"
- Line 733: P10-007 refinement check

### In audit reports
- D3-D4-security-sharedvps.md lines 347-352: MEDIUM finding — services running as non-guinevere user won't be limited by the slice
- Implementation synthesis: cgroup as mitigation for shared VPS risk

---

## 9. Known Issues, Contradictions & Ambiguities

### Cross-doc Mismatches

| # | Documents | Discrepancy | Impact |
|---|---|---|---|
| 1 | CHECKLIST.md (line 108) vs StepPrompts.md | CHECKLIST: `cat /etc/systemd/system/guinevere-*.slice` (wildcard, implies multiple) vs StepPrompts: single `guinevere.slice` | **Low** — only one slice is created. CHECKLIST line is inaccurate. The correct path is `/etc/systemd/system/guinevere.slice` (no wildcard). |
| 2 | StepPrompts vs IMPLEMENTATION_GUIDE | IMPLEMENTATION_GUIDE has no P0-009-specific section. Only line 292 mentions cgroup. StepPrompts has full context. | **Low** — not a contradiction, but IMPLEMENTATION_GUIDE is incomplete for this step. StepPrompts is authoritative. |
| 3 | StepPrompts evidence naming vs StepPrompts verification | Evidence file named `cgroup-status.txt` but verification commands use `systemctl status guinevere.slice` (which produces different output than raw cgroup knob reads) | **Low** — implementation can capture both. |
| 4 | CHECKLIST.md line 108 format | `guinevere-*.slice` vs actual filename `guinevere.slice` | **Low** — ensure created file is `guinevere.slice` not `guinevere-*.slice`. |

### Known Audit Finding (MEDIUM — from D3-D4-security-sharedvps.md)

> "cgroup limits apply to guinevere user only. If any Guinevere service runs as a different user (e.g., Redis as `redis` user, Docker as root), those processes are NOT limited by the slice."

**Risk assessment for P0-009:**
- At P0-009 execution time, **no Guinevere services exist yet**. The slice is created empty.
- Risk manifests in later phases when services are deployed.
- P0-009 implementation should document this constraint so future steps are aware.
- Mitigation: all service unit definitions already include `User=guinevere` in their StepPrompts — but Docker containers and Redis run as their own users.

### Open Questions

| # | Question | Answer from Sources |
|---|---|---|
| 1 | Is `MemoryHigh=7G` a soft limit? | Yes. cgroup v2: `memory.high` throttles allocation and triggers reclaim. `memory.max` is the hard OOM kill boundary. |
| 2 | Should we set `MemorySwapMax`? | Not in StepPrompts. On cgroup v2, if `memory.swap.max` is not set, swap usage is **unlimited** for the cgroup. The 4GB system swap could be consumed by Guinevere. Consider setting `MemorySwapMax=12G` (8GB RAM + 4GB swap ceiling). |
| 3 | When does the slice actually enforce limits? | Only when processes are assigned to it via `Slice=guinevere.slice` in their unit's `[Service]` section, OR when started with `systemd-run --slice=guinevere.slice`. At P0-009, the slice is active but empty. |
| 4 | Does `systemctl start guinevere.slice` do anything visible? | It activates the cgroup hierarchy. `ls /sys/fs/cgroup/guinevere.slice/` will show the cgroup controllers but no pids until services join. |

---

## 10. Rollback

### From StepPrompts.md (lines 1065-1069)
```bash
sudo systemctl stop guinevere.slice
sudo rm /etc/systemd/system/guinevere.slice
sudo systemctl daemon-reload
```

### Safety assessment
- **No data loss**: Slice is just a resource policy. Stopping it has no effect on data.
- **No service impact**: No services are assigned to the slice yet (all future phases).
- **Idempotent**: Safe to re-run; `tee` overwrites the file; `daemon-reload` is always safe.
- **Re-run safe**: If the slice fails to start (cgroup v1 vs v2 mismatch), the rollback is clean.

---

## 11. Pre-flight Checklist (Before Implementation)

- [x] P0-001 complete — `id guinevere` shows uid exists
- [ ] P0-009 unchecked in PROGRESS.md
- [ ] systemd version supports cgroup v2 resource control (`systemctl --version`)
- [ ] Aizanta services healthy (baseline before touching systemd hierarchy)
- [ ] No existing `guinevere.slice` file (`ls /etc/systemd/system/guinevere.slice` should fail)
- [ ] SSH session to VPS active

---

## 12. Implementation Plan Summary

### What to do (single step, atomic)
1. Pre-flight: check systemd version, cgroup v2, Aizanta health
2. Create `/etc/systemd/system/guinevere.slice` with exact content from StepPrompts
3. `sudo systemctl daemon-reload`
4. `sudo systemctl start guinevere.slice`
5. Verify: status, memory.max, cpu.max, TasksMax
6. Aizanta post-check (containers, ports, memory)
7. Capture evidence files
8. Update PROGRESS.md, CHECKLIST.md, StepPrompts.md
9. Spawn independent auditor

### What NOT to do
- Do NOT modify any existing service units
- Do NOT add `Slice=guinevere.slice` to Aizanta services
- Do NOT touch Docker containers or PostgreSQL
- Do NOT change `/etc/systemd/system/` files beyond `guinevere.slice`

### Time estimate
- 30-45 minutes (StepPrompts says 2 hours, but actual scope is smaller than estimated — single file creation + verification)

---

## 13. Auditor Gate

### Auditor scope
1. Verify slice file content matches StepPrompts exactly
2. Confirm cgroup v2 compatibility (Ubuntu 24.04 default)
3. Check no other systemd units were modified
4. Verify Aizanta health unchanged
5. Confirm evidence files complete
6. Flag: CHECKLIST.md wildcard path mismatch (`guinevere-*.slice` vs `guinevere.slice`)
7. Flag: no MemorySwapMax set (swap could be unlimited)
8. Flag: future service user mismatch risk (documented in D3-D4 audit)

---

## Footer

**Source task**: STEP-P0-009 (from `stepprompts/StepPrompts.md`)
**Date**: 2026-05-31
**Author**: Guinevere (parent orchestrator, pre-implementation research)
**Next action**: Proceed to implementation when Faiz says "lanjut"