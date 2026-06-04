# P15 Windows Daemon — StepPrompts Expansion Evidence

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon + WebSocket (Expansion) |
| **Task** | Generate 15 Tier 1 step prompts and integrate into all project documentation |
| **Date** | 2026-06-04 |
| **Status** | ✅ COMPLETE — All auditors PASS after remediation |

---

## 1. What Was Done

Generated 15 complete Tier 1 step prompts (P15-001 through P15-015) for the Windows Daemon expansion phase, following the exact format of P14-001 (250+ lines per step with 13 required sections each).

### Steps Generated

| Step | Title | Wave | Category |
|---|---|---|---|
| P15-001 | Project Scaffold + Base Tracker ABC | 1 | Infrastructure |
| P15-002 | Active Window Tracker (win32gui + psutil) | 2 | Implementation |
| P15-003 | Idle Tracker (GetLastInputInfo, graduated) | 2 | Implementation |
| P15-004 | Git Context Tracker (traversal + project mapping) | 2 | Implementation |
| P15-005 | Event Pipeline (MessagePack + EventRouter + WS Client) | 3 | Implementation |
| P15-006 | NSSM Service Wrapper + Config | 4 | Infrastructure |
| P15-007 | VPS WebSocket Endpoint (FastAPI + ConnectionManager) | 1 | Implementation |
| P15-008 | Command Protocol (ACK-based, Redis DB4 pub/sub) | 3 | Implementation |
| P15-009 | Consent Gate Integration (belt-and-suspenders) ⚠️ | 4 | Safety-Critical |
| P15-010 | Discord `/pc` Command (status + session override) | 5 | UX |
| P15-011 | Observability (Prometheus metrics + Grafana dashboard + alerting) | 5 | Observability |
| P15-012 | TimescaleDB Migration (windows_events hypertable) | 1 | Database |
| P15-013 | Test Suite (unit + integration) | 6 | Testing |
| P15-014 | Integration Test — End-to-End Daemon ↔ VPS | 6 | Testing |
| P15-015 | Deployment + Smoke Test + README | 7 | Deployment |

### Wave Structure (matches planner gate exactly)

| Wave | Steps | Rationale |
|---|---|---|
| 1 | P15-001, P15-007, P15-012 | Independent scaffolds (parallel) |
| 2 | P15-002, P15-003, P15-004 | All 3 trackers depend only on P15-001 |
| 3 | P15-005, P15-008 | Event pipeline + command protocol (parallel) |
| 4 | P15-006, P15-009 | NSSM wrapper + consent gate (parallel) |
| 5 | P15-010, P15-011 | Discord command + observability (parallel) |
| 6 | P15-013, P15-014 | Test suite + E2E (sequential within wave) |
| 7 | P15-015 | Deployment (depends on all tests pass) |

---

## 2. Files Changed

### Created
| File | Lines | Description |
|---|---|---|
| `docs/setup-evidence/p15-expansion/steps-batch-a.md` | 1403 | P15-001 through P15-005 (source) |
| `docs/setup-evidence/p15-expansion/steps-batch-b.md` | 1326 | P15-006 through P15-010 (source) |
| `docs/setup-evidence/p15-expansion/steps-batch-c.md` | 1197 | P15-011 through P15-015 (source) |
| `docs/setup-evidence/p15-expansion/audit-completeness.md` | ~200 | Completeness audit report |
| `docs/setup-evidence/p15-expansion/audit-consistency.md` | 241 | Consistency audit report |
| `docs/setup-evidence/p15-expansion/audit-forbidden-patterns.md` | 269 | Forbidden patterns audit report |

### Modified
| File | Change |
|---|---|
| `stepprompts/StepPrompts.md` | Replaced P15 placeholder (lines 53382-53401) with full 15-step content (~3960 lines). File now 47,345+ lines. Fixed 3 forbidden pattern violations. Added wave labels to P15-006..P15-015. |
| `PROGRESS.md` | Replaced P15 TBD placeholder with 15 steps organized in 7 waves (matching planner gate) |
| `CHECKLIST.md` | Replaced P15 TBD with 15 verification steps + 8 completion criteria. Added ⚠️ SAFETY-CRITICAL to P15-009. |
| `docs/IMPLEMENTATION_GUIDE.md` | Updated P15 row in summary table (15 steps, $5-15), expanded Phase 15 section with full step table, updated header counts, added ⚠️ SAFETY-CRITICAL to P15-009 |

---

## 3. Validation Results

### Audit 1: Completeness — PASS (after remediation)
- All 15 steps present with 13 required sections each
- All dependencies match planner gate exactly
- All evidence paths follow `STEP-P15-NNN/` convention
- **Remediated:** Wave labels added to P15-006..P15-015 Phase fields

### Audit 2: Consistency — PASS (after remediation)
- Step count: 15 across all 4 files ✓
- Cost: $5-15/month consistent ✓
- Dependencies: P5+P8+P12 consistent ✓
- Protocol specs: MessagePack/JSON, WS auth, Redis DB2/DB4, idle thresholds, exponential backoff, consent fail-closed — all consistent ✓
- **Remediated:** PROGRESS.md waves 3-7 aligned with planner gate
- **Remediated:** ⚠️ SAFETY-CRITICAL added to CHECKLIST.md and IMPLEMENTATION_GUIDE.md for P15-009
- **Note:** Minor title divergences between planner gate and canonical docs (P15-013 "+ E2E", P15-014 colon vs em-dash, P15-015 "+ README") — canonical docs (StepPrompts/PROGRESS/CHECKLIST/IMPL_GUIDE) are self-consistent and authoritative

### Audit 3: Forbidden Patterns — PASS (after remediation)
- 19 patterns searched across 15 steps (~5,000 lines)
- **Remediated:** 2 `TODO` comments in code blocks (P15-006 `__main__.py`, P15-007 `windows_ws.py`) replaced with actual implementation
- **Remediated:** 1 `pass` inside `except ValueError:` (P15-006 `__main__.py`) replaced with `logger.warning()`
- Zero remaining violations
- All 14 `except Exception as e:` handlers verified with proper logging

---

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| Planner Gate | `docs/setup-evidence/plans/p15-windows-daemon.md` |
| Batch A (P15-001..005) | `docs/setup-evidence/p15-expansion/steps-batch-a.md` |
| Batch B (P15-006..010) | `docs/setup-evidence/p15-expansion/steps-batch-b.md` |
| Batch C (P15-011..015) | `docs/setup-evidence/p15-expansion/steps-batch-c.md` |
| Completeness Audit | `docs/setup-evidence/p15-expansion/audit-completeness.md` |
| Consistency Audit | `docs/setup-evidence/p15-expansion/audit-consistency.md` |
| Forbidden Patterns Audit | `docs/setup-evidence/p15-expansion/audit-forbidden-patterns.md` |
| Assembled StepPrompts | `stepprompts/StepPrompts.md` (Phase 15 section) |

---

## 5. Doc-Sync Impact

All 4 project documentation files updated consistently:
- `stepprompts/StepPrompts.md` — canonical step reference
- `PROGRESS.md` — execution tracker with wave structure
- `CHECKLIST.md` — verification checklist
- `docs/IMPLEMENTATION_GUIDE.md` — user-facing guide with summary table

Step count updated: 343 → 358 total (+15 P15 steps)
Expansion total: 107 → 122 (+15 P15 steps)

---

## 6. Boundary Compliance

- No persona drift
- No consent violation
- No surveillance overreach
- Consent gate (P15-009) explicitly marked ⚠️ SAFETY-CRITICAL across all docs
- No secret/intimate data exposure
- No HARD STOP bypass

---

## 7. Rollback/Re-run Safety

- Batch source files are additive (no existing files overwritten)
- StepPrompts.md: P15 section replaced placeholder; P14 and P16 sections untouched
- PROGRESS.md, CHECKLIST.md, IMPLEMENTATION_GUIDE.md: P15 sections replaced placeholders only
- All changes are idempotent documentation updates

---

## 8. Design Decisions/Caveats

1. **Batch writing strategy**: Used 3 parallel writing agents (A: P15-001..005, B: P15-006..010, C: P15-011..015) to generate ~3,926 lines of step content efficiently
2. **Assembly approach**: Used a 4th agent to splice batch files into StepPrompts.md, replacing the 20-line placeholder with full content
3. **Wave structure authority**: Planner gate (`p15-windows-daemon.md`) is the authoritative source for wave assignments. PROGRESS.md was initially written with a more conservative wave structure and corrected during audit remediation.
4. **Title divergences**: Minor title differences between planner gate and canonical docs are acceptable — canonical docs (StepPrompts/CHECKLIST/PROGRESS/IMPL_GUIDE) are self-consistent and serve as the implementer-facing reference.
5. **Metadata table format**: P14-001 reference format does not include `Type`, `Risk`, `Git Commit` fields. Completeness auditor flagged this as a theoretical finding but it's a false positive since the established format was followed.

---

## 9. Auditor Gate

| Auditor | Initial Verdict | Post-Fix Verdict | Findings Fixed |
|---|---|---|---|
| Completeness | FAIL | PASS | Wave labels added to 10 steps |
| Consistency | FAIL | PASS | Waves 3-7 aligned; SAFETY-CRITICAL labels added |
| Forbidden Patterns | FAIL | PASS | 2 TODOs + 1 pass-in-except replaced with proper code |

---

## 10. Security Scan

- No secrets committed
- No API keys or credentials in step prompts
- Tailscale IP validation implemented (not just TODO)
- Consent gate fail-closed design preserved

---

## 11. Acceptance Criteria Mapping

| AC | Status | Evidence |
|---|---|---|
| 15 Tier 1 steps generated | ✅ PASS | 3 batch files, assembled into StepPrompts.md |
| Wave structure matches planner gate | ✅ PASS | All 15 Phase fields verified |
| All 4 docs updated consistently | ✅ PASS | Cross-file audit PASS |
| No forbidden patterns | ✅ PASS | 19-pattern scan, 0 violations after fix |
| Evidence documented | ✅ PASS | 6 evidence files in p15-expansion/ |
| Safety boundary preserved | ✅ PASS | P15-009 ⚠️ SAFETY-CRITICAL across all docs |

---

## 12. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Guinevere + Sisyphus | Initial P15 StepPrompts expansion: 15 steps, 3 audits, full remediation |
