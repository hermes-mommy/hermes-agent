# Recheck: Documentation-Update Commands & Runbook Subsection Requirements

> **Purpose**: Satisfy Auditor 7-3 findings by defining exact commands (copy-paste ready) for PROGRESS.md, CHECKLIST.md, ADR-035 status, decisions-log entry, IMPLEMENTATION_GUIDE.md, plus runbook Verify/Escalate subsection requirements.
> **Auditor Source**: `research-reports/phase-6-7-planning/audit-73-documentation.md`
> **Plan Source**: `docs/setup-evidence/hermes-migration/batch-plan-phase-7.md`
> **Date**: 2026-06-05
> **Scope**: Planning-only — no file modification; commands are for Phase 7, Step 7.9 definition.

---

## 1. PROGRESS.md — Update Commands

### Current State

- **File**: `PROGRESS.md` (734 lines)
- **Status line** (line 6): `✅ P0+P1+P2+P3+P4+P5+P5.5+P6+P7+P7.5+P8 Complete — MVP Infrastructure Complete.`
- **Phase table**: P0-P8 = `✅` (100%), P9-P10 = `⏳` (0%)
- **No ADR-035 Hermes Migration reference** currently exists in PROGRESS.md

### Requirement (Gate G06)

`grep "Phase 7" PROGRESS.md` = **Found**

"Phase 7" here refers to the **Hermes Hardening phase** (Phase 7 of the ADR-035 migration plan), not the original P7 (Surveillance). To satisfy the gate criterion, PROGRESS.md must contain an explicit mention of "Phase 7" in the Hermes migration context.

### Concrete Commands (copy-paste ready)

**Option A — Add Hermes migration note row below phase summary table** (recommended — preserves existing structure):

```bash
# Append a Hermes Migration completion note after the phase summary table
# Insert after line 51 (the "**Total**" row of the phase summary table)
# Using sed with backup:
cp PROGRESS.md PROGRESS.md.bak
sed -i "52a\\\n## ADR-035 Hermes Migration — Phase 7 Complete ✅\n\n| Phase | Name | Status | Evidence |\n|-------|------|--------|----------|\n| Phase 0 | Security Remediation | ✅ | \`docs/setup-evidence/hermes-phase0\` |\n| Phase 1 | Safety Foundation | ✅ | 10 gates PASS |\n| Phase 2 | Discord Gateway | ✅ | Cutover done, 48h+ shadow |\n| Phase 3 | Memory Bridge | ✅ | A/B test p > 0.05 |\n| Phase 4 | MCP + Tools | ✅ | Auth overlay verified |\n| Phase 5 | Skills + SOUL.md | ✅ | 7 skills loaded |\n| Phase 6 | LLM Routing | ✅ | 9Router configured |\n| Phase 7 | Hardening + Monitoring | ✅ | Runbooks, SLOs, Capacity Plan |\n\n*All 8 phases of ADR-035 migration complete. See \`docs/setup-evidence/hermes-migration/\` for evidence.*" PROGRESS.md
```

**Option B — Add single "Phase 7: Hermes Hardening complete" line to the existing Phase Summary table** (narrower scope):

```bash
cp PROGRESS.md PROGRESS.md.bak
# Find the "## P8: Observability (23 steps) ✅" line, insert Hermes migration note below it
sed -i "/^## P8: Observability (23 steps) ✅/a\\\n### ADR-035 Phase 7 (Hermes Hardening): ✅ Complete — see \`docs\/setup-evidence\/hermes-migration\/batch-plan-phase-7.md\`" PROGRESS.md
```

**Option C — Update the top status line** to include Phase 7:

```bash
cp PROGRESS.md PROGRESS.md.bak
sed -i "s/✅ P0+P1+P2+P3+P4+P5+P5.5+P6+P7+P7.5+P8 Complete — MVP Infrastructure Complete/✅ P0+P1+P2+P3+P4+P5+P5.5+P6+P7+P7.5+P8 Complete ✅ ADR-035 Phase 7 (Hermes Hardening) Complete — MVP Infrastructure Complete. Production deployment pending./" PROGRESS.md
```

**Verification** (post-apply):

```bash
grep "Phase 7" PROGRESS.md
# Expected output: at least one line containing "Phase 7"
```

---

## 2. ADR-035 — Status to IMPLEMENTED

### Current State

- **File**: `adr/ADR-035-hermes-migration.md`
- **Frontmatter line 4**: `status: "Accepted"`
- **Body line 45**: `Accepted`

### Requirement (Gate G06)

`grep "status:" adr/ADR-035-hermes-migration.md` = **IMPLEMENTED**

### Concrete Command (copy-paste ready)

The rollback plan (Section 16, line 1277) already *reverse-engineers* the expected format:
```bash
sed -i "s/status: \"IMPLEMENTED\"/status: \"Accepted\"/"   # rollback
```
Therefore the **forward** command is:

```bash
cp adr/ADR-035-hermes-migration.md adr/ADR-035-hermes-migration.md.bak
sed -i 's/status: "Accepted"/status: "IMPLEMENTED"/' adr/ADR-035-hermes-migration.md
```

⚠️ **Ambiguity**: The frontmatter uses `status: "Accepted"` (with quotes) while the body Section 3 says just `Accepted` (bare word). The rollback plan's `sed` targets `status: "IMPLEMENTED"` → `status: "Accepted"` which matches the frontmatter YAML format (`status: "Accepted"`). Therefore:

- **Frontmatter**: `status: "Accepted"` → `status: "IMPLEMENTED"`
- **Body** (Section 3, line 45): `Accepted` → `IMPLEMENTED`

**Recommended two-target command**:

```bash
cp adr/ADR-035-hermes-migration.md adr/ADR-035-hermes-migration.md.bak
# Frontmatter
sed -i 's/^status: "Accepted"/status: "IMPLEMENTED"/' adr/ADR-035-hermes-migration.md
# Body heading
sed -i 's/^Accepted$/IMPLEMENTED/' adr/ADR-035-hermes-migration.md
```

### Verification

```bash
grep -n "status:" adr/ADR-035-hermes-migration.md
# Expected: status: "IMPLEMENTED"
grep -n "^IMPLEMENTED$" adr/ADR-035-hermes-migration.md
# Expected: line with IMPLEMENTED (should be 1 line in body)
```

---

## 3. CHECKLIST.md — ADR-035 Reference

### Current State

- **File**: `CHECKLIST.md` (880+ lines)
- **P0-P10 checklists**: Complete but cover original phases, not Hermes migration
- **No ADR-035 reference** anywhere in CHECKLIST.md

### Requirement (Gate G06)

`grep "ADR-035" CHECKLIST.md` = **Found**

### Concrete Command (copy-paste ready)

Add an ADR-035/Hermes migration section to CHECKLIST.md:

```bash
cp CHECKLIST.md CHECKLIST.md.bak
# Append a Hermes Migration completion note after the P10 section end
cat >> CHECKLIST.md << 'CHECKEOF'

---

## 14. ADR-035 Hermes Migration — Phase 7 Completion Verification

**Goal:** Verify all Phase 7 documentation artifacts exist and ADR-035 is marked IMPLEMENTED
**Steps:** 1 (Step 7.9: Documentation Update)
**ACs satisfied:** AC-DOC-001, AC-DOC-002

### 14.1 Prerequisites

- [ ] Phases 0-6 of ADR-035 migration complete
- [ ] Gate G01-G05 all PASS
- [ ] All evidence artifacts from Steps 7.1-7.8 collected

### 14.2 Step Verification

- [ ] `grep "Phase 7" PROGRESS.md` → Found
- [ ] `grep "status:" adr/ADR-035-hermes-migration.md` → IMPLEMENTED
- [ ] `grep "ADR-035" CHECKLIST.md` → Found (this entry)
- [ ] `grep "ADR-035" docs/10-governance/decisions-log.md` → Found
- [ ] `docs/IMPLEMENTATION_GUIDE.md` — ADR-035 migration phases documented
- [ ] All 9 runbooks (R01-R09) have explicit **Verify** and **Escalate** subsections
- [ ] RTO/RPO column or reference present in each runbook

### 14.3 Evidence

- [ ] `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/verification.md`
- [ ] `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/progress-update.txt`
- [ ] `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/checklist-update.txt`
- [ ] Gate evidence: `G06-docs-pass.txt`

### 14.4 Rollback

- [ ] `sed -i 's/status: "IMPLEMENTED"/status: "Accepted"/' adr/ADR-035-hermes-migration.md`
- [ ] `git checkout -- PROGRESS.md CHECKLIST.md docs/IMPLEMENTATION_GUIDE.md`
- [ ] `git checkout -- docs/10-governance/decisions-log.md`
CHECKEOF
```

### Verification

```bash
grep "ADR-035" CHECKLIST.md
# Expected: Section 14 with ADR-035 Hermes Migration
```

---

## 4. Decisions-Log — Final Entry

### Current State

- **File**: `docs/10-governance/decisions-log.md`
- **Last entry**: #004 (2026-06-05, ADR-030 Redis reconciliation)
- **Format**:
  ```
  | # | Date | Decision | Category | ADR | Rationale | Approved By |
  ```

### Requirement (Gate G06)

`grep "ADR-035" docs/10-governance/decisions-log.md` = **Found**

ADR-035 is already referenced in entry #003 (2026-06-04), so the grep will find it. However, the audit requires a **new final entry** documenting Phase 7 completion.

### Concrete Entry (copy-paste ready)

```bash
cp docs/10-governance/decisions-log.md docs/10-governance/decisions-log.md.bak
# Append a new entry before the "Last updated" footer
sed -i '/^\*Last updated:/i\
| 005 | 2026-06-05 | ADR-035 Phase 7 (Hermes Hardening) Complete | Architecture | [ADR-035](../../adr/ADR-035-hermes-migration.md) | Phase 7 of ADR-035 Hermes migration complete: full regression test suite (7.1), Prometheus metrics (7.2), alert rules (7.3), performance baseline (7.4), security audit (7.5), deprecated files cleanup (7.6), ADR-029 automated tests (7.7), final backup (7.8), documentation update (7.9). All 7 gates PASS. ADR-035 status updated to IMPLEMENTED. | Faiz' docs/10-governance/decisions-log.md
```

**Manual entry text** (if sed proves difficult with pipe characters):

```
| 005 | 2026-06-05 | ADR-035 Phase 7 (Hermes Hardening) Complete | Architecture | [ADR-035](../../adr/ADR-035-hermes-migration.md) | Phase 7 of ADR-035 Hermes migration complete: full regression test suite, Prometheus metrics, alert rules, performance baseline, security audit, deprecated files cleanup, ADR-029 automated tests, final backup, documentation update. All 7 gates PASS. ADR-035 status updated to IMPLEMENTED. | Faiz |
```

Insert this as a new line after line 18 (entry #004 line) and before line 21 (the `---` separator).

### Verification

```bash
grep "ADR-035" docs/10-governance/decisions-log.md
# Expected: 2 matches (entry #003 + new #005)
```

---

## 5. IMPLEMENTATION_GUIDE.md — Update Requirements

### Current State

- **File**: `docs/IMPLEMENTATION_GUIDE.md` (890 lines)
- **Documented phases**: P0-P22 only (original implementation roadmap)
- **No ADR-035 Hermes migration phase reference** in the main documentation

### Requirement

The IMPLEMENTATION_GUIDE.md should document ADR-035 Hermes migration phases (Phase 0-7) to maintain completeness of implementation documentation.

### Concrete Command

```bash
cp docs/IMPLEMENTATION_GUIDE.md docs/IMPLEMENTATION_GUIDE.md.bak
# Add a new section after the Phase Overview table (after line 73)
sed -i '73a\\\
## ADR-035 Hermes Migration — Phase 7 Complete\\\
\\\
### Migration Phase Summary\\\
\\\
The ADR-035 Hermes NousResearch Agent v0.15.2 migration was executed as an 8-phase plan\\\
(Phase 0 through Phase 7). All 8 phases completed successfully.\\\
\\\
| Phase | Name | Duration | Gate |\\\
|-------|------|----------|------|\\\
| Phase 0 | Security Remediation | 2-3 days | hermes doctor clean, zero HIGH/MODERATE |\\\
| Phase 1 | Safety Foundation | 7-10 days | 10 safety gates all PASS |\\\
| Phase 2 | Discord Gateway | 5-8 days | 35 slash commands, 48h+ shadow, Faiz approval |\\\
| Phase 3 | Memory Bridge | 4-5 days | Recall quality unchanged, DNR/classification enforced |\\\
| Phase 4 | MCP + Tools | 5-7 days | All 16 tools, auth matrix enforced |\\\
| Phase 5 | Skills + Persona | 2-3 days | All persona features, mood persists, rituals fire |\\\
| Phase 6 | LLM Routing | 1 day | 9Router functional, fallback works, budget enforced |\\\
| Phase 7 | Hardening + Monitoring | 2-3 days | All monitoring, security clean, runbooks complete |\\\
\\\
**Evidence**: \`docs/setup-evidence/hermes-migration/\`\\\
**Gate criteria**: See \`docs/setup-evidence/hermes-migration/batch-plan-phase-7.md §15\`\\\
**Total migration duration**: 35-50 days (realistic estimate, solo developer)\\\
\\\
### Key Outcomes\\\
\\\
- Discord gateway: Migrated to Hermes native (streaming, auto-threading, circuit breaker)\\\
- Memory: Hybrid model (PostgreSQL primary + Hermes compression/SQLite read-only supplement)\\\
- Safety: 7 lifecycle hooks + GuinevereSafetyPlugin (defense-in-depth)\\\
- MCP: Hybrid (5 native + 7 custom with auth overlay plugin)\\\
- LLM: 9Router retained at localhost:20128\\\
- Code reduction: 8,057 lines (31.2% net)\\\
' docs/IMPLEMENTATION_GUIDE.md
```

**Alternative**: Append a brief note to the introduction section:

```
# After line 6 (Last updated line), update:
**Last updated**: 2026-06-05

# After line 7 (Companion files line), add:
**ADR-035**: Phase 7 (Hermes Hardening) Complete — see `docs/setup-evidence/hermes-migration/batch-plan-phase-7.md`
```

### Verification

```bash
grep -c "ADR-035" docs/IMPLEMENTATION_GUIDE.md
# Expected: >= 1
```

---

## 6. Runbook Verify/Escalate Subsection Requirements

### Current State

- **Section 12** (lines 924-1051): 9 runbook scenarios R01-R09
- **Header template**: `**Trigger:**`, `**Severity:**`, `**Steps:**`
- **Missing**: `**Verify:**`, `**Escalate:**` subsections

### Requirement (Auditor 7-3 Finding 4)

Each runbook must have:
1. ✅ **Trigger** — condition that fires the runbook (present)
2. ⬜ **Verify** — explicit exit criteria (missing)
3. ⬜ **Escalate** — escalation path with contacts/timing (missing)
4. ⬜ **RTO/RPO** — per-runbook recovery time / data loss expectation (missing)

### Required Additions Per Runbook

Each of R01-R09 needs these two subsections appended (or inserted before the last step). Below are the exact text blocks:

#### R01: Hermes Gateway Crash + Restart

```
**Verify:**
- `ssh guinevere-vps 'hermes gateway status'` → "running"
- `ssh guinevere-vps 'curl -sf http://localhost:9191/metrics | head -1'` → HTTP 200
- Discord shows bot online in #guinevere-chat

**Escalate:**
- If gateway fails after 3 restart attempts → immediate escalation to Faiz via Gotify
- If legacy `guinevere-discord.service` also fails → SEV1, escalate within 5 min
- Faiz contact: Discord DM + phone (if configured)

**RTO/RPO:** RTO < 5 min | RPO = 0 (no data loss — PostgreSQL canonical)
```

#### R02: Memory Recall Degraded

```
**Verify:**
- `python -m scripts.bench_memory --mode live --iterations 10 | grep p95` → p95 < 2000ms
- `curl -sf http://localhost:9191/metrics | grep hermes_memory_recall_latency` → metric present
- User reports memory recall working normally

**Escalate:**
- If p95 remains > 2s after VACUUM and compression adjustment → SEV2, escalate within 1 hour
- If recall fails entirely (zero results returned) → SEV1, immediate escalation
- PostgreSQL query performance issues → involve DBA runbook escalation

**RTO/RPO:** RTO < 30 min | RPO = N/A (query performance only)
```

#### R03: Safety Hook Failure

```
**Verify:**
- Send "HARD STOP emergency stop" in #guinevere-chat → neutral response within 3s
- `curl -sf http://localhost:9191/metrics | grep hermes_safety_plugin_loaded` → value = 1
- All 7 hooks pass: `hermes doctor` → all checks green

**Escalate:**
- If HARD STOP fails (no neutral response) → **IMMEDIATE escalation** — Faiz, emergency protocol
- If failsafe mode also fails → SEV1, escalate within 2 min
- If plugin fails to load → SEV1, block all responses, escalate immediately
- Faiz contact: All channels (Discord DM, Gotify, phone)

**RTO/RPO:** RTO < 1 min | RPO = N/A (safety-critical, fail-closed)
```

#### R04: 9Router Unreachable

```
**Verify:**
- `curl -sf http://localhost:20128/health` → healthy JSON response
- `systemctl is-active guinevere-9router` → "active"
- Test LLM response: `curl -sf http://localhost:20128/v1/chat/completions -d '{"model":"default","messages":[{"role":"user","content":"test"}]}'` → choices array

**Escalate:**
- If 9Router fails to restart after 2 attempts → escalate to Faiz within 15 min (SEV1)
- If direct OpenAI fallback also fails → escalate immediately
- If no LLM route available for > 30 min → graceful degradation mode, notify Faiz

**RTO/RPO:** RTO < 10 min | RPO = 0 (no data loss)
```

#### R05: Discord Token Expired

```
**Verify:**
- `journalctl -u hermes-gateway --since "5 min ago"` → no 401/Unauthorized errors
- Discord bot shows online status
- Send test message in #guinevere-chat → response received

**Escalate:**
- If token rotation fails to resolve after 2 attempts → SEV1, escalate within 15 min
- If Discord Developer Portal is inaccessible → escalate to Faiz
- If bot fails to come online for > 30 min → notify via Gotify

**RTO/RPO:** RTO < 15 min | RPO = 0 (no data loss)
```

#### R06: VPS RAM > 80%

```
**Verify:**
- `free -h | grep Mem` → RAM usage < 75%
- `docker stats --no-stream --format "table {{.Name}}\t{{.MemPerc}}"` → no container > 80%
- Prometheus alert NodeMemoryUsage → resolved (green)

**Escalate:**
- If RAM usage remains > 80% after stopping non-essential services → SEV2, escalate within 1 hour
- If RAM usage exceeds 90% → SEV1, immediate escalation
- If cgroup limits are breached (guinevere.slice MemoryMax=8G) → escalate immediately

**RTO/RPO:** RTO < 30 min | RPO = N/A (capacity management)
```

#### R07: Disk > 80%

```
**Verify:**
- `df -h / | tail -1` → usage < 75%
- `du -sh /home/guinevere/* | sort -rh | head -5` → no unexpected growth
- Prometheus alert NodeDiskUsage → resolved (green)

**Escalate:**
- If disk usage remains > 80% after cleanup → SEV2, escalate within 1 hour
- If disk > 90% → SEV1, immediate escalation — data loss risk
- If PostgreSQL WAL directory grows unexpectedly → escalate (potential replication issue)

**RTO/RPO:** RTO < 1 hour | RPO = N/A (capacity management; data loss risk > 90%)
```

#### R08: PostgreSQL Connection Exhausted

```
**Verify:**
- `sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity"` → < 75 connections
- `sudo -u postgres psql -c "SHOW max_connections;"` → matches expected limit
- Application health check passes: `curl http://localhost:8000/health` → OK

**Escalate:**
- If connections remain > max_connections after terminating idle sessions → SEV2, escalate within 1 hour
- If PgBouncer pool is also exhausted → escalate to Faiz (potential application leak)
- If database becomes unresponsive → SEV1, immediate escalation

**RTO/RPO:** RTO < 15 min | RPO = 0 (no data loss from connection exhaustion)
```

#### R09: Redis WRONGPASS Errors

```
**Verify:**
- `journalctl -u redis --since "5 minute ago" | grep -c "wrongpass"` = 0
- `redis-cli -p 6380 AUTH guinevere_core <password>` → OK
- `redis-cli -p 6380 PING` → PONG
- All services authenticate successfully

**Escalate:**
- If WRONGPASS errors persist after password rotation → SEV3, escalate within 2 hours
- If multiple services show auth failures → SEV2, escalate within 1 hour (potential ACL corruption)
- If Redis becomes inaccessible → SEV1, escalate immediately

**RTO/RPO:** RTO < 15 min | RPO = 0 (no data loss — Redis is cache/cost tracking; rebuildable)
```

### Implementation Pattern for Step 7.9

Each runbook should be edited in-place. Example pattern for R01:

```bash
# For R01 (Hermes Gateway Crash + Restart), append Verify and Escalate subsections
# Locate the end of R01 steps block (line ~940)
# Insert after Step 7 (line 940: "Escalate if gateway fails after 3 attempts or legacy bot also fails.")
# Replace the old Escalate line with proper structured subsections
```

**Structural change needed in batch-plan-phase-7.md** (Section 12, lines 924-1051):
- Each runbook's numbered steps end with implicit verification and escalation
- Pattern: replace the last `N.` step in each runbook with proper `**Verify:**` and `**Escalate:**` subsections
- Add `**RTO/RPO:**` line between Trigger and Steps in each runbook header

---

## 7. Summary of All Changes for Step 7.9 Definition

| # | File | Action | Command Type | Verification |
|---|------|--------|-------------|-------------|
| 1 | `PROGRESS.md` | Add "Phase 7" reference (Hermes migration row) | `sed` / append | `grep "Phase 7" PROGRESS.md` |
| 2 | `adr/ADR-035-hermes-migration.md` | Change status from "Accepted" to "IMPLEMENTED" | `sed` (2 targets) | `grep "status:"` → IMPLEMENTED |
| 3 | `CHECKLIST.md` | Add Section 14: ADR-035 Hermes Migration checklist | `cat >>` append | `grep "ADR-035" CHECKLIST.md` |
| 4 | `docs/10-governance/decisions-log.md` | Add entry #005: Phase 7 completion | `sed` insert / manual edit | `grep "ADR-035" decisions-log.md` |
| 5 | `docs/IMPLEMENTATION_GUIDE.md` | Add ADR-035 migration phases section | `sed` insert / manual edit | `grep "ADR-035" IMPLEMENTATION_GUIDE.md` |
| 6 | `docs/.../batch-plan-phase-7.md` (Section 12) | Add Verify/Escalate/RTO-RPO to all 9 runbooks | In-place edits per pattern above | Manual review of each runbook |

### Evidence Artifacts (from batch plan Section 18.1, Step 7.9)

| Artifact | Path | Description |
|----------|------|-------------|
| progress-update.txt | `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/progress-update.txt` | Output of PROGRESS.md update verification |
| checklist-update.txt | `docs/setup-evidence/hermes-migration/phase-7/STEP-7.9/checklist-update.txt` | Output of CHECKLIST.md update verification |
| G06-docs-pass.txt | `docs/setup-evidence/hermes-migration/phase-7/gates/G06-docs-pass.txt` | Gate G06 PASS evidence |

### Gate G06 — Full Verification Script

```bash
#!/bin/bash
# Gate G06: Documentation — ALL must PASS
errors=0

echo "=== G06: Documentation Gate ==="

# 1. ADR-035 status
if grep "status:" adr/ADR-035-hermes-migration.md | grep -q "IMPLEMENTED"; then
  echo "PASS: ADR-035 status = IMPLEMENTED"
else
  echo "FAIL: ADR-035 status not IMPLEMENTED"
  ((errors++))
fi

# 2. PROGRESS.md
if grep -q "Phase 7" PROGRESS.md; then
  echo "PASS: PROGRESS.md references Phase 7"
else
  echo "FAIL: PROGRESS.md missing Phase 7 reference"
  ((errors++))
fi

# 3. CHECKLIST.md
if grep -q "ADR-035" CHECKLIST.md; then
  echo "PASS: CHECKLIST.md references ADR-035"
else
  echo "FAIL: CHECKLIST.md missing ADR-035 reference"
  ((errors++))
fi

# 4. Decisions-log
if grep -q "ADR-035" docs/10-governance/decisions-log.md; then
  echo "PASS: decisions-log.md has ADR-035 entry"
else
  echo "FAIL: decisions-log.md missing ADR-035 entry"
  ((errors++))
fi

# 5. IMPLEMENTATION_GUIDE.md
if grep -q "ADR-035" docs/IMPLEMENTATION_GUIDE.md; then
  echo "PASS: IMPLEMENTATION_GUIDE.md references ADR-035"
else
  echo "FAIL: IMPLEMENTATION_GUIDE.md missing ADR-035 reference"
  ((errors++))
fi

echo ""
if [ "$errors" -eq 0 ]; then
  echo "G06: ALL PASS"
  exit 0
else
  echo "G06: $errors FAILURES"
  exit 1
fi
```

---

## 8. Caveats & Recommendations

### Priority Order

1. **ADR-035 status change** — simplest, highest impact on gate PASS
2. **Decisions-log entry** — already references ADR-035 (entry #003), but needs #005 for completeness
3. **PROGRESS.md** — needs the "Phase 7" reference for G06; choose approach based on how much detail is wanted
4. **CHECKLIST.md** — needs ADR-035 section; recommended to add as Section 14
5. **IMPLEMENTATION_GUIDE.md** — lower priority but maintains documentation consistency
6. **Runbook Verify/Escalate subsections** — highest effort but moderate impact; the runbooks are functional as-is for technical operators

### Risks

- **`sed` on YAML frontmatter**: The `sed` pattern for ADR-035 assumes `status: "Accepted"` — verify exact whitespace. Frontmatter YAML: `status: "Accepted"` (with space after colon). Use `sed -i 's/status: "Accepted"/status: "IMPLEMENTED"/'` to be safe.
- **`sed` overwrite**: Always use `cp <file> <file>.bak` before any `sed -i`.
- **Runbook edit complexity**: 9 runbooks × 3 subsection additions = 27 edits. Consider batch-processing or a Python script for reliability.
- **IMPLEMENTATION_GUIDE.md line numbers**: The line numbers in this report are based on current file state (890 lines). If the file has been modified, re-check exact insertion points before executing commands.

---

*Report generated to satisfy Auditor 7-3 findings for Phase 7, Step 7.9 (Documentation Update) definition.*
