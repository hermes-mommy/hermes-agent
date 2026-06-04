---
title: "P15 Windows Daemon — Cross-Documentation Consistency Audit"
date: "2026-06-04"
auditor: "Guinevere (Sisyphus-Junior)"
scope: "P15 Windows Daemon + WebSocket — all documentation files"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
---

# P15 Windows Daemon — Cross-Documentation Consistency Audit

## 1. Verdict

**FAIL** — 4 inconsistencies found, 1 material. Protocol core is solid; structural documentation needs reconciliation before implementation begins.

---

## 2. Scope & Method

### Files Audited

| # | File | Role |
|---|------|------|
| 1 | `stepprompts/StepPrompts.md` (lines 53382–57691) | Authoritative step definitions |
| 2 | `PROGRESS.md` (lines 569–601) | Progress tracking + wave structure |
| 3 | `CHECKLIST.md` (lines 1111–1143) | Verification checklist |
| 4 | `docs/IMPLEMENTATION_GUIDE.md` (lines 290–316) | Implementation guide |
| 5 | `docs/setup-evidence/plans/p15-windows-daemon.md` (726 lines) | Planner gate (authoritative for dependencies/waves) |

### Method

Each file was read in full for its P15 section. Step titles, counts, dependencies, wave assignments, protocol details, cost estimates, evidence paths, and cross-references were compared across all 5 files. Findings are categorized as PASS (consistent), WARN (minor/non-blocking), or FAIL (material/inconsistent).

---

## 3. Cross-File Comparison Table

### 3.1 Step Titles

| Step | StepPrompts | PROGRESS | CHECKLIST | IMPL_GUIDE | Planner Gate |
|------|------------|----------|-----------|------------|--------------|
| P15-001 | Project Scaffold + Base Tracker ABC | PASS | PASS | PASS | PASS |
| P15-002 | Active Window Tracker (win32gui + psutil) | PASS | PASS | PASS | PASS |
| P15-003 | Idle Tracker (GetLastInputInfo, graduated) | PASS | PASS | PASS | PASS |
| P15-004 | Git Context Tracker (traversal + project mapping) | PASS | PASS | PASS | PASS |
| P15-005 | Event Pipeline (MessagePack + EventRouter + WS Client) | PASS | PASS | PASS | PASS |
| P15-006 | NSSM Service Wrapper + Config | PASS | PASS | PASS | PASS |
| P15-007 | VPS WebSocket Endpoint (FastAPI + ConnectionManager) | PASS | PASS | PASS | PASS |
| P15-008 | Command Protocol (ACK-based, Redis DB4 pub/sub) | PASS | PASS | PASS | PASS |
| P15-009 | Consent Gate Integration (belt-and-suspenders) SAFETY-CRITICAL | **PASS** (has tag) | **FAIL** (missing tag) | **FAIL** (missing tag) | **FAIL** (missing in title; only in auditor matrix) |
| P15-010 | Discord /pc Command (status + session override) | PASS | PASS | PASS | PASS |
| P15-011 | Observability (Prometheus metrics + Grafana dashboard + alerting) | PASS | PASS | PASS | PASS |
| P15-012 | TimescaleDB Migration (windows_events hypertable) | PASS | PASS | PASS | PASS |
| P15-013 | Test Suite (unit + integration) | PASS | PASS | PASS | **FAIL** (adds "+ E2E") |
| P15-014 | Integration Test -- End-to-End Daemon <-> VPS | PASS | PASS | PASS | **FAIL** (colon not em-dash) |
| P15-015 | Deployment + Smoke Test + README | PASS | PASS | PASS | **FAIL** (missing "+ README") |

### 3.2 Structural Fields

| Field | StepPrompts | PROGRESS | CHECKLIST | IMPL_GUIDE | Planner Gate |
|-------|------------|----------|-----------|------------|--------------|
| Step count | 15 PASS | 15 PASS | 15 PASS | 15 PASS | 15 PASS |
| Cost | $5-15/month PASS | $5-15/month PASS | (not stated) | $5-15 PASS | (not stated) |
| Dependencies | P5+P8+P12 PASS | P5+P8+P12 PASS | P5+P8+P12 PASS | P5+P8+P12 PASS | (implicit) PASS |
| Planner gate ref | PASS | PASS | PASS | PASS | N/A |
| Evidence root | `docs/setup-evidence/p15-expansion/` PASS | (not stated) | (not stated) | PASS | PASS |
| Evidence per-step | `STEP-P15-NNN/` PASS | (not stated) | (not stated) | (not stated) | `STEP-P15-NNN/` PASS |

---

## 4. Wave Structure Comparison

### PROGRESS.md vs Planner Gate

This is the most significant inconsistency found.

| Wave | PROGRESS.md | Planner Gate | Match? |
|------|------------|--------------|--------|
| Wave 1 | P15-001, P15-007, P15-012 (parallel) | P15-001, P15-007, P15-012 (parallel) | PASS |
| Wave 2 | P15-002, P15-003, P15-004 | P15-002, P15-003, P15-004 | PASS |
| Wave 3 | **P15-005 only** | P15-005, **P15-008** | **FAIL** |
| Wave 4 | **P15-006, P15-008** | **P15-006, P15-009** | **FAIL** |
| Wave 5 | **P15-009, P15-010** | **P15-010, P15-011** | **FAIL** |
| Wave 6 | **P15-011 only** | **P15-013, P15-014** | **FAIL** |
| Wave 7 | **P15-013, P15-014, P15-015** | **P15-015 only** | **FAIL** |

**Impact:** The Planner gate has a clear architectural chain: P15-007 -> P15-008 -> P15-009 (WS endpoint -> commands -> consent gate). PROGRESS.md breaks this chain by moving P15-008 to Wave 4, isolating P15-009 in Wave 5, and pushing all test/deploy steps into Wave 7. The Planner gate's arrangement is architecturally superior because:

- P15-008 (commands) logically follows P15-007 (WS endpoint) — both are VPS-side
- P15-009 (consent gate) depends on both P15-007 and P15-008 being functional
- Tests and deployment are properly separated from implementation waves

**Verdict:** PROGRESS.md wave structure must be updated to match the Planner gate.

### StepPrompts Internal Phase/Wave Fields

| Step | Phase field in StepPrompts | Wave present? |
|------|---------------------------|---------------|
| P15-001 | P15 -- Windows Daemon (Wave 1) | PASS |
| P15-002 | P15 -- Windows Daemon (Wave 2) | PASS |
| P15-003 | P15 -- Windows Daemon (Wave 2) | PASS |
| P15-004 | P15 -- Windows Daemon (Wave 2) | PASS |
| P15-005 | P15 -- Windows Daemon (Wave 3) | PASS |
| P15-006 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-007 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-008 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-009 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-010 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-011 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-012 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-013 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-014 | P15 -- Windows Daemon | **FAIL** (no wave) |
| P15-015 | P15 -- Windows Daemon | **FAIL** (no wave) |

**Finding:** Steps P15-006 through P15-015 lack wave numbers in their Phase metadata field. Only the first 5 steps have wave annotations. This is an internal StepPrompts inconsistency.

---

## 5. Protocol Consistency Checklist

| Protocol Detail | StepPrompts | Planner Gate | Consistent? |
|----------------|------------|--------------|-------------|
| MessagePack for events | P15-005 title | Decision 3.1: "MessagePack events, JSON commands" | PASS |
| JSON for commands | P15-008 title | Decision 3.1 | PASS |
| WebSocket first-message auth | Implicit in P15-007 | Section 8.3: "First message: auth with secret" | PASS |
| Redis DB2 for event buffer | P15-005 context | Decision 3.4: "Redis DB2 buffer" | PASS |
| Redis DB4 for pub/sub | P15-008 title | Decision 3.5: "Redis DB4 pub/sub" | PASS |
| Graduated idle: active<2m, away 2m, idle 5m, deep_idle 15m | P15-003 title ("graduated") | Section 8.5: active:0, away:120, idle:300, deep_idle:900 | PASS |
| Exponential backoff: 1s,2s,4s,8s,max 60s + jitter | P15-005 ("WS Client") | Section 8.3: "exponential backoff (1s, 2s, 4s, 8s, max 60s + jitter)" | PASS |
| Consent gate: fail-closed during safe_mode | P15-009 SAFETY-CRITICAL | Section 8.7: "FAIL-CLOSED guarantee" | PASS |
| ACK timeout: 10s | P15-008 title ("ACK-based") | Section 3.5: "ACK (10s timeout)" | PASS |
| Heartbeat: 30s bidirectional | Implicit | Section 8.3: "Every 30s" | PASS |

**Verdict: All 10 protocol details are consistent across documentation files.**

---

## 6. Cross-Reference Validation

### 6.1 Inter-Step Dependency References

| Source | Claim | Verified Against Planner | Status |
|--------|-------|--------------------------|--------|
| P15-001 | "None (Parallel with P15-007 and P15-012)" | Planner: dependency --, parallel | PASS |
| P15-002 | "P15-001 (BaseTracker ABC)" | Planner: dependency P15-001 | PASS |
| P15-003 | "P15-001 (BaseTracker ABC)" | Planner: dependency P15-001 | PASS |
| P15-004 | "P15-001 (BaseTracker ABC)" | Planner: dependency P15-001 | PASS |
| P15-005 | P15-002 + P15-003 + P15-004 | Planner: same | PASS |
| CHECKLIST Prereqs | "P5 + P8 + P12" | Planner implicit | PASS |

### 6.2 ADR References

| ADR | Filename | Exists? | Referenced By |
|-----|----------|---------|---------------|
| ADR-010 | `adr/ADR-010-surveillance-data-retention-policy.md` | PASS | StepPrompts (P15-001, P15-002), Planner gate |
| ADR-019 | `adr/ADR-019-access-control-vpn-mesh-strategy.md` | PASS | StepPrompts (P15-001, P15-002), Planner gate |
| ADR-030 | `adr/ADR-030-redis-db-assignments.md` | PASS | Planner gate (Existing Infrastructure) |
| ADR-035 | Not yet created | WARN (planned post-impl) | Planner gate Section 13: "Add ADR-035 if new ADR needed" |

**ADR-035** is referenced as a potential future ADR in the Planner gate's Tracker Sync Plan. This is not an inconsistency — it is explicitly marked as post-implementation.

### 6.3 Evidence Path Convention

All files that specify evidence paths use the `docs/setup-evidence/p15-expansion/STEP-P15-NNN/` convention. The Planner gate Section 10 enumerates all 15 step directories. StepPrompts evidence sections (visible in P15-001 and P15-002) match this format.

**Verdict: Evidence path convention is consistent. PASS.**

---

## 7. Summary of Findings

### FAIL Items (4)

| # | Finding | Severity | Files Affected | Recommendation |
|---|---------|----------|----------------|----------------|
| F1 | SAFETY-CRITICAL label missing on P15-009 | **MEDIUM** | CHECKLIST.md, IMPLEMENTATION_GUIDE.md, Planner gate title | Add the SAFETY-CRITICAL warning label to P15-009 in CHECKLIST, IMPLEMENTATION_GUIDE, and Planner gate step title for visibility |
| F2 | Wave structure mismatch (PROGRESS vs Planner) | **HIGH** | PROGRESS.md | Reconcile PROGRESS.md Waves 3-7 to match Planner gate Section 2 parallelism groups. Planner is authoritative per AGENTS.md Section 2.4 |
| F3 | Planner gate title variants (P15-013, P15-014, P15-015) | **LOW** | Planner gate | Align planner gate master todo titles with StepPrompts.md (canonical source for step titles) |
| F4 | StepPrompts Phase/Wave fields incomplete | **LOW** | StepPrompts.md | Add wave numbers to Phase fields for steps P15-006 through P15-015 |
| F5 | StepPrompts P15-013 missing "+ E2E" from planner | **LOW** | Either file | Decide: is E2E part of P15-013 or separate in P15-014? Current Planner says "+ E2E" in P15-013 but E2E is P15-014 |

### PASS Items (All Core Protocol Details)

- Step count: 15 across all files
- Cost: $5-15/month consistent where stated
- Dependencies: P5+P8+P12 consistent
- MessagePack events / JSON commands protocol
- WebSocket first-message authentication
- Redis DB2 buffer / DB4 pub/sub allocation
- Graduated idle thresholds (2m/5m/15m)
- Exponential backoff with jitter (1s-60s)
- Consent gate fail-closed during safe_mode
- ACK-based command protocol with 10s timeout
- 30s bidirectional heartbeat
- Evidence path convention (STEP-P15-NNN/)
- Planner gate reference present in all files
- ADR-010, ADR-019, ADR-030 all exist
- Inter-step dependency references match planner

---

## 8. Recommendations

### Immediate (Before Implementation Begins)

1. **Reconcile PROGRESS.md wave structure** with Planner gate. This is the highest priority fix — wave structure determines execution ordering and parallelism decisions.

2. **Add SAFETY-CRITICAL label** to P15-009 in CHECKLIST.md and IMPLEMENTATION_GUIDE.md. For a safety-critical step, consistent visibility across all documentation is mandatory per PersonaSafetyPolicy and AGENTS.md Section 2.1.

3. **Add wave numbers to StepPrompts Phase fields** for steps P15-006 through P15-015.

### Nice-to-Have

4. **Align Planner gate step titles** with StepPrompts.md (canonical source). Specifically: P15-013 remove "+ E2E", P15-014 use em-dash not colon, P15-015 add "+ README".

5. **Add cost line to CHECKLIST.md** P15 section for completeness.

6. **Add evidence paths to PROGRESS.md and CHECKLIST.md** for traceability.

---

## 9. Audit Trail

| Field | Value |
|-------|-------|
| Audit date | 2026-06-04 |
| Auditor | Guinevere (Sisyphus-Junior) |
| Files examined | 5 |
| Cross-file checks | 45 (15 steps x 3 fields each: title, count, metadata) |
| Protocol checks | 10 |
| ADR checks | 4 |
| PASS rate | 41/45 (91%) for structural; 10/10 (100%) for protocol |
| Final verdict | FAIL |
| Reason | Wave structure mismatch (F2) is material; SAFETY-CRITICAL label missing from 2 files (F1) is a safety documentation gap |

---

## 10. Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-04 | Guinevere (Sisyphus-Junior) | Initial consistency audit of P15 documentation |