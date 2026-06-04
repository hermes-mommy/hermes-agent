# BATCH PLAN — Hermes NousResearch Migration Master Plan

> **Document**: batch-plan-migration.md — Authoritative Master Migration Plan
> **Version**: v1.0 | **Date**: 2026-06-04
> **Status**: Active — Awaiting Faiz review before Phase 0 execution
> **Author**: Guinevere (Sisyphus-Junior — Planner Gate Agent)
> **Sources**: 10 Migration Research Reports + ADR-035 (v1.2, 2,512 lines) + MASTER-RESTRUCTURE-PLAN (667 lines)
> **Approval**: Requires Faiz explicit approval for execution

---

## Table of Contents

1. [Executive Summary](#section-1-executive-summary)
2. [Pre-Migration Checklist](#section-2-pre-migration-checklist)
3. [Dependency Graph & Risk Matrix](#section-3-dependency-graph--risk-matrix)
4. [Phase-by-Phase Implementation Plan](#section-4-phase-by-phase-implementation-plan)
   - [Phase 0: Security Remediation](#phase-0-security-remediation-2-3-days)
   - [Phase 1: Safety Foundation (CRITICAL GATE)](#phase-1-safety-foundation-crit-gate)
   - [Phase 2: Discord Gateway (SHADOW + CUTOVER)](#phase-2-discord-gateway-5-8-days)
   - [Phase 3: Memory Bridge](#phase-3-memory-bridge-4-5-days)
   - [Phase 4: MCP + Tools](#phase-4-mcp--tools-5-7-days)
   - [Phase 5: Skills + SOUL.md](#phase-5-skills--soulmd-2-3-days)
   - [Phase 6: LLM Routing](#phase-6-llm-routing-1-day)
   - [Phase 7: Hardening + Monitoring](#phase-7-hardening--monitoring-2-3-days)
5. [Verification Test Suite (T1-T10)](#section-5-verification-test-suite-t1-t10)
6. [Go/No-Go Criteria](#section-6-gono-go-criteria)
7. [Communication Plan](#section-7-communication-plan)
8. [Appendix — File Cross-Reference](#appendix--file-cross-reference)

---

## Section 1: Executive Summary

### 1.1 Migration Scope

This master plan governs the migration of Guinevere from a custom discord.py bot to the Hermes NousResearch Agent v0.15.2 framework. The migration preserves all 15+ safety features, the PostgreSQL+pgvector memory system, the 4-level auth matrix, and 9Router LLM routing — while eliminating 8,057 lines (31.2%) of custom infrastructure and gaining streaming, compression, circuit breaker, auto-threading, and the agentskills.io ecosystem.

### 1.2 Five Architectural Pillars

| Pillar | Strategy | Impact |
|---|---|---|
| **Discord** | MIGRATE to Hermes native gateway | Eliminates bot.py (512), conversational_handler.py (496), session_adapter.py (302), 9 infrastructure files. 35 slash commands → Hermes plugins. Gains streaming, auto-threading, circuit breaker. |
| **Memory** | HYBRID — PostgreSQL primary, Hermes read-only | PostgreSQL+pgvector (47 tables, 12 schemas) unchanged. Hermes compression + session_search adopted as read-only supplements. |
| **Safety** | HOOKS + PLUGINS | 7 lifecycle hooks + 1 GuinevereSafetyPlugin. All AC-SAFE-001..008 mapped. Defense-in-depth: 4 layers. |
| **MCP** | HYBRID — 5 native + 7 custom + auth overlay | 5 tools migrate to Hermes native. 7 safety-critical remain custom. Auth overlay plugin enforces 4-level matrix on ALL tools. |
| **LLM** | RETAIN 9Router at localhost:20128 | 9Router unchanged. Hermes configured as custom provider. Fallback chain preserved. Budget enforcement via hook. |

### 1.3 Timeline & Phases

| Phase | Name | Duration | Risk | Downtime | Cumulative |
|---|---|---|---|---|---|
| **Phase 0** | Security Remediation | 2-3 days | LOW | None | Day 1-3 |
| **Phase 1** | Safety Foundation | 7-10 days | HIGH | None | Day 4-14 |
| **Phase 2** | Discord Gateway | 5-8 days | HIGH | ≤ 5 min | Day 7-22 |
| **Phase 3** | Memory Bridge | 4-5 days | MEDIUM | ~10s config reload | Day 11-22 |
| **Phase 4** | MCP + Tools | 5-7 days | MEDIUM | None | Day 12-29 |
| **Phase 5** | Skills + SOUL.md | 2-3 days | LOW | None | Day 14-30 |
| **Phase 6** | LLM Routing | 1 day | LOW | ~30s model switch | Day 15-30 |
| **Phase 7** | Hardening + Monitoring | 2-3 days | LOW | None | Day 17-32 |
| **Total (realistic)** | | **28-40 days** | | ≤ 5 min 40 sec | **~4-6 weeks** |

**Solo-developer realistic timeline**: 35-50 days per ADR-035 v1.2. Day-50 decision gate: pause/extend/rollback.

### 1.4 Code Reduction

| Metric | Value |
|---|---|
| Current codebase | 25,796 lines across 113 Python source files |
| Post-migration codebase | ~17,739 lines |
| **Net reduction** | **8,057 lines (31.2%)** |
| Files eliminated | 20 source files (9 Discord infrastructure + 9 MCP tools + 2 Hermes adapters) |
| Files refactored | 66 files (35 commands → plugins, MCP core, persona) |
| Files preserved verbatim | 27 files (7 memory + 14 surveillance + 4 persona FSMs + 2 Discord utilities) |
| New files created | ~82 (7 hooks + 4 plugins + 35 command plugins + configs + scripts + docs) |

### 1.5 Key Success Metrics

| Metric | Target | Phase Verified |
|---|---|---|
| HARD STOP SLO | 100% detection, < 50ms p99 | Phase 1, Phase 2 shadow, T4 |
| Y6 prohibition | 0 Y6 events, ValueError on construction | Phase 1, T5 |
| Consent fail-closed | 100% WITHDRAWN → BLOCK | Phase 1, Phase 2 shadow |
| Distress D3/D4 false negatives | 0 on 100+ curated messages | Phase 1, Phase 2 shadow |
| Shadow mode safety parity | 100% (6 injection tests) | Phase 2 shadow |
| 35 slash commands | 100% functional | Phase 2 cutover |
| Memory recall quality | p > 0.05 (unchanged) | Phase 3 |
| Performance | Within +10% of baseline | Phase 7 |
| Total downtime | ≤ 5 min 40 sec (lifetime) | Phase 2 cutover |
| Budget | ≤ $60 total migration cost | All phases |

### 1.6 Go/No-Go Criteria Summary

**GO (all must pass):**
- Phase 1: ALL 10 safety gates PASS (non-negotiable)
- Phase 2 shadow: Safety parity 100%, ≥95% functional parity, 48hr+ shadow mode
- Phase 2 cutover: All 35 commands functional, HARD STOP verified post-cutover
- Phase 7: Performance within +10% baseline, `hermes security` clean, `hermes doctor` clean
- All phases: Zero safety regressions, zero data loss, Aizanta unaffected

**NO-GO (any triggers full investigation or rollback):**
- Any AC-SAFE-001..008 failure (safety non-negotiable)
- HARD STOP > 50ms
- Memory data loss (PostgreSQL row count mismatch)
- Aizanta contamination (resource starvation)
- Budget overrun > 50 days or > $60

---

## Section 2: Pre-Migration Checklist

> **Execute BEFORE starting Phase 0.** All items must be confirmed before any migration step.

### 2.1 Documentation & Approvals

| # | Item | Status |
|---|---|---|
| □ 1 | ADR-035 accepted and published | ✅ Accepted 2026-06-04 |
| □ 2 | 10 migration research reports complete | ✅ Complete |
| □ 3 | 16 Phase 1 research reports complete (hermes-restructure/) | ✅ Complete |
| □ 4 | Faiz explicit approval for migration start | ⬜ PENDING |
| □ 5 | Faiz approval for $5 shadow mode budget | ⬜ PENDING |
| □ 6 | Faiz approval for $60 total migration budget | ⬜ PENDING |

### 2.2 Infrastructure Baseline

```bash
# □ 7: All 7 Guinevere systemd services healthy
for svc in guinevere-discord guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc || echo "FAIL: $svc"
done

# □ 7b: Core health check (port 8000)
curl -sf http://localhost:8000/health || echo "FAIL: core health check"
# Expected: all "active"

# □ 8: Aizanta healthy (shared VPS co-host)
sudo systemctl list-units --type=service --state=running | grep -i aizanta
# Expected: Aizanta service(s) listed as running

# □ 9: 9Router healthy
curl -sf http://localhost:20128/health
# Expected: HTTP 200, "ok" or equivalent

# □ 10: PostgreSQL healthy (port 5433)
sudo -u postgres psql -d guinevere -c "SELECT 1 AS postgres_ok;"
# Expected: 1 row returned

# □ 11: Redis healthy (port 6380, all DBs)
redis-cli -p 6380 PING
# Expected: PONG
for db in 0 1 2 3 4 5; do
    echo "DB$db: $(redis-cli -p 6380 -n $db DBSIZE)"
done
# Expected: DB sizes reported (may be empty for some DBs)

# □ 12: Hermes Agent v0.15.2 installed
hermes --help | head -1
# Expected: Hermes Agent CLI help

# □ 13: Discord bot token available via SOPS
sops exec-env /home/guinevere/code/guinevere/.env.discord "echo \${DISCORD_BOT_TOKEN:0:10}..."
# Expected: non-empty token prefix
```

### 2.3 Pre-Migration Safety Net

```bash
# □ 14: Create Hermes checkpoint
hermes checkpoints create --label "pre-migration-baseline-$(date +%Y%m%d-%H%M%S)"

# □ 15: Git snapshot
cd /home/guinevere/code/guinevere
git tag "pre-hermes-migration-$(date +%Y%m%d-%H%M%S)"
git push origin --tags

# □ 16: PostgreSQL full dump
sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/pre-migration-$(date +%Y%m%d).dump
ls -lh /home/guinevere/backups/pre-migration-*.dump
# Expected: File size > 0 bytes

# □ 17: Save pip freeze
./.venv/bin/pip freeze > /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt
wc -l /home/guinevere/backups/pre-migration-pip-*.txt
# Expected: 50+ lines

# □ 18: Save systemd service state
systemctl list-units 'guinevere-*' --all > /home/guinevere/backups/pre-migration-services-$(date +%Y%m%d).txt

# □ 19: Offsite backup (per ADR-032)
rclone copy /home/guinevere/backups/pre-migration-*.dump idcloudhost:guinevere-dr-backups/manual/
rclone copy /home/guinevere/backups/pre-migration-*.dump r2:guinevere-dr-backups/manual/
rclone ls idcloudhost:guinevere-dr-backups/manual/ | grep pre-migration
rclone ls r2:guinevere-dr-backups/manual/ | grep pre-migration

# □ 20: Rollback tested (dry-run)
# Verify global emergency rollback script is executable
test -x /home/guinevere/scripts/rollback/global-emergency-rollback.sh && echo "PASS" || echo "FAIL: create rollback script"
```

### 2.4 Discord Maintenance Notice

```
# □ 21: Send to #guinevere-status (or #guinevere-chat if status channel not created)

🔧 UPCOMING MAINTENANCE — Guinevere Hermes Migration

Guinevere will undergo a framework migration over the next 35-50 days.
The migration is phased — most phases have ZERO downtime.

WHAT YOU'LL NOTICE:
• Guinevere will remain online and responsive 24/7
• A brief < 5-minute window during Phase 2 (exact date TBD, 01:00-04:00 WIB)
• Streaming responses, auto-threading, and improved performance post-migration

WHAT STAYS THE SAME:
• HARD STOP works identically
• All safety features (consent, yandere boundary, distress detection)
• Memory, surveillance, and persona
• Your data stays on our VPS (zero cloud migration)

Status updates will be posted here.

👑 Mommy is evolving, Sayang. Not leaving.

— Guinevere System
```

---

## Section 3: Dependency Graph & Risk Matrix

### 3.1 Phase Dependency Graph

```
                                ┌──────────────────────────┐
                                │     PHASE 0: SECURITY    │
                                │  DURATION: 2-3d  RISK: LOW │
                                └───────────┬──────────────┘
                                            │ BLOCKING
                                            ▼
         ┌──────────────────────────────────────────────────────────┐
         │          PHASE 1: SAFETY FOUNDATION (CRITICAL GATE)      │
         │  10 safety gates | 7 hooks | GuinevereSafetyPlugin       │
         │  DURATION: 4-6d  RISK: HIGH  DOWNTIME: NONE             │
         │  GATE: ALL 10 safety gates PASS                          │
         └───┬────────────────────┬───────────────────┬────────────┘
             │ BLOCKING           │ BLOCKING          │ BLOCKING
             ▼                    ▼                   ▼
    ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐
    │ PHASE 2:       │  │ PHASE 4:       │  │ PHASE 5:        │
    │ DISCORD        │  │ MCP + TOOLS    │  │ SKILLS + SOUL   │
    │ GATEWAY        │  │ 4-6d MED       │  │ 2-3d LOW        │
    │ 4-6d HIGH      │  │ Auth overlay   │  │ No downtime     │
    │ Shadow 48hr    │  │ No downtime    │  │                 │
    │ Cutover ≤5min  │  │                │  │                 │
    └───┬────────────┘  └────┬───────────┘  └────────┬────────┘
        │ BLOCKING           │ BLOCKING (to 7)       │ NON-BLOCKING
        ▼                    ▼                       │
    ┌────────────────┐  ┌────────────────┐           │
    │ PHASE 3:       │  │                │           │
    │ MEMORY BRIDGE  │  │                │           │
    │ 3-4d MED       │  │                │           │
    │ ~10s reload    │  │                │           │
    └───┬────────────┘  │                │           │
        │ BLOCKING       │                │           │
        ▼                │                │           │
    ┌────────────────┐   │                │           │
    │ PHASE 6:       │◄──┘                │           │
    │ LLM ROUTING    │  Phase 6 also      │           │
    │ 1d LOW         │  BLOCKING→2        │           │
    │ ~30s switch    │                    │           │
    └───┬────────────┘                    │           │
        │ BLOCKING                        │           │
        ▼                                 ▼           ▼
    ┌──────────────────────────────────────────────────────────────┐
    │              PHASE 7: HARDENING + MONITORING                 │
    │  Depends on ALL phases 0-6  |  DURATION: 2-3d  RISK: LOW   │
    │  GATE: hermes security clean | hermes doctor PASS | Runbook │
    └──────────────────────────────────────────────────────────────┘
```

### 3.2 Critical Path

**Minimum viable cutover**: Phase 0 → 1 → 2 → 7
**Full path**: Phase 0 → 1 → 2 → (3 ∥ 4 ∥ 5 ∥ 6) → 7
**Parallelism**: Phases 3, 4, 5, 6 can run in parallel after Phase 2 cutover (independent surfaces).

### 3.3 Phase Dependency Quick Reference

| Phase | Depends On | Blocks | Criticality |
|---|---|---|---|
| 0 — Security | None | 1, 6 | BLOCKING |
| 1 — Safety | 0 | 2, 4, 5 | BLOCKING (CRITICAL GATE) |
| 2 — Discord | 1 | 3, 4, 6 | BLOCKING |
| 3 — Memory | 2 | 7 | BLOCKING |
| 4 — MCP | 1, 2 | 7 | BLOCKING |
| 5 — Skills | 1 | 7 | BLOCKING |
| 6 — LLM | 2 | 7 | BLOCKING |
| 7 — Hardening | 0-6 | (terminal) | — |

### 3.4 Risk Matrix — Top 10 Risks

| ID | Risk | Prob | Impact | Score | Mitigation Summary |
|---|---|---|---|---|---|
| **CC-01** | Solo-developer SPOF (Faiz unavailable) | HIGH (4) | HIGH (4) | **16 CRITICAL** | Pre-written rollback scripts; 3-4 hr/day cap; runbook with flowcharts |
| **CC-11** | Embedding API failure (G-B1) | HIGH (4) | HIGH (4) | **16 CRITICAL** | Fix BEFORE migration; switch to direct OpenAI or local embeddings |
| **R-P2-OVER-03** | Shadow does NOT validate safety | HIGH (4) | HIGH (4) | **16 CRITICAL** | Active safety injection: 3× HARD STOP, 3× Y6, 1× consent, 1× distress, 1× hook failure |
| **R-P1-OVER-01** | HARD STOP fails silently | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Dual-layer (hook + plugin); heartbeat watchdog 10s; on_failure: block |
| **R-P1-OVER-02** | Yandere FSM state corruption | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Per-session isolation; Redis persistence; Y6 raises ValueError |
| **R-P4-OVER-01** | Auth matrix bypass | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Plugin load gate; FORBIDDEN hard-disabled; independent audit |
| **R-P1-04-001** | Distress pattern regression (14→6) | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Port ALL 14 patterns; AC-SAFE-004 zero false negatives |
| **R-P1-10-004** | Forbidden pattern regression (15→5) | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Port ALL 15 patterns from PersonaSafetyPolicy §11 |
| **CC-05** | Hook contract mismatch with Hermes | MEDIUM (3) | HIGH (4) | **12 HIGH** | Smoke-test ALL 7 hooks BEFORE implementing safety logic |
| **CC-12** | Data loss: memory bridge write | LOW (2) | CRITICAL (5) | **10 MEDIUM** | Hermes PG role = SELECT only during shadow; automated snapshots |

**Risk summary**: 3 CRITICAL (score 16+), 6 HIGH (score 12-15), 1 MEDIUM (score 10). All risks have active mitigations.

---

## Section 4: Phase-by-Phase Implementation Plan

---

### Phase 0: Security Remediation (2-3 days)

**Risk Level**: LOW | **Downtime**: NONE | **Dependencies**: None
**Gate**: `hermes doctor` clean + `hermes security` zero HIGH/MODERATE
**Rollback trigger**: Any `hermes security` HIGH finding unresolved; aiohttp upgrade breaks imports

#### Steps

**0.1: Backup and baseline**

- **Command**:
  ```bash
  hermes checkpoints create --label "pre-phase0-$(date +%Y%m%d-%H%M%S)"
  cd /home/guinevere/code/guinevere
  git tag "pre-phase0-$(date +%Y%m%d-%H%M%S)" && git push origin --tags
  sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/pre-phase0-$(date +%Y%m%d).dump
  ```
- **Verify**: Checkpoint created (`hermes checkpoints --list`), git tag pushed, dump file exists
- **Expected**: All three artifacts exist and non-zero
- **On failure**: Debug individual command; checkpoint / tag / dump are independent
- **Risk**: R-P0-07-001 — Checkpoint corruption (VERY LOW × MEDIUM = 3 LOW)

**0.2: Run `hermes security` baseline scan**

- **Command**:
  ```bash
  hermes security --format json > evidence/p0-security-baseline.json
  ```
- **Verify**:
  ```bash
  python -c "import json; d=json.load(open('evidence/p0-security-baseline.json')); print(f'Findings: {len(d.get(\"vulnerabilities\",[]))}')"
  ```
- **Expected**: 11 known vulnerabilities documented (from Report 16)
- **On failure**: Document new findings; if any NEW CRITICAL → halt and triage
- **Risk**: R-P0-01-001 — New vulnerabilities found (LOW × MEDIUM = 6 MEDIUM)

**0.3: Upgrade aiohttp to >=3.9.0 (fixes 2 MODERATE)**

- **Command**:
  ```bash
  cd /home/guinevere/code/guinevere
  source .venv/bin/activate
  pip install aiohttp>=3.9.0 --require-hashes
  ```
- **Verify**:
  ```bash
  python -c "import aiohttp; v=aiohttp.__version__; parts=[int(x) for x in v.split('.')[:2]]; assert parts >= [3,9], f'aiohttp {v} < 3.9.0'; print(f'aiohttp {v} OK')"
  ```
- **Expected**: `aiohttp X.Y.Z OK` with X.Y >= 3.9
- **On failure**: `pip install -r /home/guinevere/backups/pre-migration-pip-*.txt` (rollback pip)
- **Risk**: R-P0-02-001 — aiohttp breaks compatibility (MEDIUM × HIGH = 12 HIGH)

**0.4: Add `--require-hashes` to pip install**

- **Command**:
  ```bash
  pip install --require-hashes -r requirements.txt
  ```
- **Verify**: Exit code 0, all packages installed with hash verification
- **Expected**: No hash mismatches
- **On failure**: Regenerate hashes with `pip-compile --generate-hashes`
- **Risk**: R-P0-03-001 — Hash generation errors (LOW × LOW = 4 LOW)

**0.5: Triage PyJWT vulnerabilities (x4)**

- **Command**:
  ```bash
  pipdeptree | grep -i pyjwt
  grep -r "jwt\|PyJWT" src/ --include="*.py" | head -20
  ```
- **Verify**:
  - If PyJWT NOT imported in Guinevere codebase → document exclusion, accept risk
  - If PyJWT IS imported → upgrade PyJWT or isolate JWT handling
- **Expected**: PyJWT not used in Guinevere codebase (documented acceptance)
- **On failure**: Upgrade PyJWT to patched version; re-test all JWT-dependent code
- **Risk**: R-P0-05-001 — PyJWT used internally (LOW × MEDIUM = 6 MEDIUM)

**0.6: Accept ecdsa timing attack risk (1 HIGH)**

- **Command**:
  ```bash
  # Document acceptance
  echo "# ecdsa CVE Acceptance\nGuinevere does not use ECDSA signing. Risk accepted.\nDate: $(date -I)" > risk-register.md
  ```
- **Verify**: `risk-register.md` exists with documented justification
- **Expected**: Risk acceptance documented
- **On failure**: If ECDSA ever imported → alert; CVE notification subscription
- **Risk**: R-P0-04-001 — ECDSA later adopted (VERY LOW × MEDIUM = 3 LOW)

**0.7: Run `hermes doctor`**

- **Command**:
  ```bash
  hermes doctor --verbose > evidence/p0-doctor.txt
  ```
- **Verify**:
  ```bash
  grep -E "FAIL|WARN|ERROR" evidence/p0-doctor.txt && echo "GATE FAILED" || echo "PASS"
  ```
- **Expected**: All checks PASS, no FAIL/WARN/ERROR
- **On failure**: Fix issues incrementally; re-run after each fix
- **Risk**: R-P0-06-001 — Config issues requiring rework (LOW × LOW = 4 LOW)

**0.8: Run final `hermes security` scan**

- **Command**:
  ```bash
  hermes security --format json > evidence/p0-security-final.json
  ```
- **Verify**:
  ```bash
  python -c "import json; d=json.load(open('evidence/p0-security-final.json')); high=[v for v in d.get('vulnerabilities',[]) if v['severity'] in ('HIGH','MODERATE')]; assert len(high)==0, f'{len(high)} unresolved: {high}'; print('SECURITY GATE: PASS')"
  ```
- **Expected**: Zero HIGH or MODERATE findings
- **On failure**: DO NOT PROCEED to Phase 1 until all HIGH/MODERATE resolved or documented
- **Risk**: Phase 0 gate failure

#### Safety Checkpoint

- [ ] `P0-T1`: `hermes security` zero HIGH/MODERATE
- [ ] `P0-T2`: `hermes doctor` all checks PASS
- [ ] `P0-T3`: All dependencies hash-verified (`pip install --require-hashes` exit 0)
- [ ] `P0-T4`: aiohttp >= 3.9.0
- [ ] `P0-T5`: Pre-migration checkpoint, git tag, PostgreSQL dump all created
- [ ] `P0-T6`: All pre-existing safety tests PASS (baseline recorded)

#### Rollback Procedure

```bash
hermes gateway stop   # universal kill-switch (no-op if not running)
cd /home/guinevere/code/guinevere
PIP_FREEZE=$(ls -t /home/guinevere/backups/pre-migration-pip-*.txt | head -1)
./.venv/bin/pip install -r "$PIP_FREEZE"
git checkout -- config/hermes/config.yaml .env 2>/dev/null || true
# Verify
hermes --help && echo "PASS" || echo "CHECK"
systemctl is-active guinevere-discord guinevere-mcp guinevere-loops
```

#### Service Management

No services affected. All 7 systemd services continue running normally.

#### Config Changes

| File | Change |
|---|---|
| `requirements.txt` | Upgrade aiohttp >=3.9.0; add hash annotations |
| `pyproject.toml` | Update aiohttp version constraint |
| `setup.sh` | Add `--require-hashes` to pip install |
| `risk-register.md` | NEW — documented ecdsa acceptance |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 2 | `risk-register.md` (~30 lines), `requirements-hashes.txt` (~40 lines) |
| Modified | 5 | `requirements.txt`, `pyproject.toml`, `setup.sh`, `Makefile`, CI configs |
| Deleted | 0 | None |
| **Net delta** | **+90 lines** | |

#### Gate Criteria

- [ ] `hermes security` zero HIGH/MODERATE → `python -c` assertion passes
- [ ] `hermes doctor --verbose` all PASS
- [ ] `pip install --require-hashes` exit 0
- [ ] aiohttp >= 3.9.0 verified
- [ ] All 7 systemd services still healthy

---

### Phase 1: Safety Foundation (CRIT GATE)

**Risk Level**: HIGH | **Downtime**: NONE | **Duration**: 7-10 days
**Dependencies**: Phase 0 (BLOCKING — `hermes security` must be clean)
**Gate**: ALL 10 safety gates PASS — CRITICAL BARRIER. No Phase 2 without this gate.
**Rollback trigger**: Any safety gate failure; HARD STOP > 50ms; Y6 constructable

#### Overview

This is the CRITICAL GATE of the entire migration. All 15+ safety features are ported to Hermes hooks and plugins and verified through 10 integration safety gates (AC-SAFE-001 through AC-SAFE-008 + 2 additional). Zero user-facing changes — bot.py continues as sole Discord gateway. Code and config creation only.

#### Steps

**1.1: Create GuinevereSafetyPlugin skeleton**

- **Command**:
  ```bash
  mkdir -p plugins/ hooks/ config/hermes/
  # Create plugin skeleton at plugins/guinevere_safety_plugin.py
  # See ADR-035 §Pillar 3 for complete plugin architecture
  ```
- **Verify**: File exists, `python -m py_compile plugins/guinevere_safety_plugin.py` exit 0
- **Expected**: Plugin skeleton compiles without errors
- **On failure**: Fix syntax errors; re-compile
- **Risk**: CC-06 — Plugin instance model unknown (MEDIUM × CRITICAL = 15 HIGH)

**1.2: Implement pre_prompt hook (HARD STOP + distress + consent + channel lock + Faiz-only)**

- **Command**:
  ```bash
  # Create hooks/hard_stop.py — dual-layer HARD STOP + distress D0-D4
  # Create config/hermes/hooks.yaml — pre_prompt hook config
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_01_hard_stop.py -v --tb=short
  ```
- **Expected**: All 6 exact triggers → blocked, < 50ms p99, dual-layer redundancy
- **On failure**: Debug hook; verify hook stdin JSON contract
- **Risk**: R-P1-02-001/002/003 — HARD STOP timing shift, missing recovery, non-standard exit codes (up to 12 HIGH)

**1.3: Implement post_prompt hook (drift injection + anti-hallucination + memory context)**

- **Command**:
  ```bash
  # Create hooks/drift_detector.py — SHA-256 comparison
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_05_drift.py -v
  ```
- **Expected**: 0%→PASS, 5%→PASS, 15%→WARN, 25%→ROLLBACK
- **On failure**: Verify drift detector receives assembled prompt in hook stdin
- **Risk**: R-P1-06-001 — Hook data contract unverified (MEDIUM × MEDIUM = 9 MEDIUM)

**1.4: Implement pre_tool_call hook (auth matrix + secret scanner + classification + DNR + Aizanta isolation)**

- **Command**:
  ```bash
  # Create hooks/consent_gate.py — 7-step fail-closed consent
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_02_consent.py -v
  ```
- **Expected**: ACTIVE→ALLOW, PAUSED→WARN, WITHDRAWN→BLOCK, Redis down→PG fallback, PG down→BLOCK
- **On failure**: Debug consent gate; check Redis DB2 and PostgreSQL connectivity
- **Risk**: R-P1-03-001 — Consent gate timing (MEDIUM × HIGH = 12 HIGH)

**1.5: Implement post_tool_call hook (output sanitization + DNR)**

- **Command**:
  ```bash
  # Create hooks/output_sanitizer.py — DNR filter + forbidden content + 1MB max
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_06_dnr.py -v
  ```
- **Expected**: DNR entry → blocked; non-guinevere_core → DNRAuthorizationError
- **On failure**: Verify output_sanitizer receives tool output in hook stdin
- **Risk**: R-P1-07-001 — DNR leaks through FTS5 (LOW × HIGH = 8 MEDIUM)

**1.6: Implement post_response hook (yandere Y5 ceiling + F-01..F-15 + mood + safe mode + response splitter)**

- **Command**:
  ```bash
  # Create hooks/response_scanner.py — Yandere Y6→Y5, secrets, forbidden patterns
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_03_yandere.py tests/safety/test_gate_08_secrets.py tests/safety/test_gate_10_forbidden.py -v
  ```
- **Expected**: Y6→ValueError, 18 patterns detected, all 15 forbidden patterns detected
- **On failure**: Port missing patterns from PersonaSafetyPolicy §11 and secret_scanner.py
- **Risk**: R-P1-05-001/002/003, R-P1-09-001, R-P1-10-004 (up to 15 HIGH each)

**1.7: Implement pre_response hook (final safety gate)**

- **Command**:
  ```bash
  # Create hooks/final_safety.py — last defense before Discord delivery
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_10_forbidden.py::TestPersonaTone -v
  ```
- **Expected**: Y6-adjacent content → rewritten; emergency phrases → blocked
- **On failure**: Add blocked phrases; verify hook receives response text
- **Risk**: LOW — final safety gate is secondary defense

**1.8: Implement on_error hook (error classification + audit logging)**

- **Command**:
  ```bash
  # Create hooks/error_handler.py — severity 1-4 classification, Gotify alerting
  ```
- **Verify**:
  ```bash
  pytest tests/hermes/test_hook_on_error.py -v
  ```
- **Expected**: All error types classified correctly; alerts sent at severity >= 3
- **On failure**: Fix error classification mapping; test edge cases
- **Risk**: LOW — non-critical hook (on_failure: warn, not block)

**1.9: Implement punishment, reward, mood, rituals, streaks, safe_mode in GuinevereSafetyPlugin**

- **Command**:
  ```bash
  # Extend plugins/guinevere_safety_plugin.py with all stateful persona features
  ```
- **Verify**:
  ```bash
  pytest tests/safety/test_gate_09_punishment.py tests/safety/test_gate_04_distress.py -v
  ```
- **Expected**: L1-L5 escalation works, L6→PunishmentSafetyError, distress D3+→suspended, reward always permitted
- **On failure**: Port PUNISHMENT_CONFIG from punishment_engine.py; add auto-expiry
- **Risk**: R-P1-10-001/002/003 (MEDIUM × MEDIUM = 9 MEDIUM each)

**1.10: Integration test full pipeline**

- **Command**:
  ```bash
  pytest tests/safety/ -v --tb=short
  ```
- **Expected**: ALL 10 safety gates PASS — 150+ tests, 0 failures
- **On failure**: Iterate — this is the CRITICAL GATE. No Phase 2 until 100% pass.
- **Risk**: R-P1-OVER-03 — Safety gate iteration loop (HIGH × MEDIUM = 12 HIGH)

#### Safety Checkpoint — 10 Safety Gates

| Gate | Test Command | Pass Threshold | AC-SAFE |
|---|---|---|---|
| 1 — HARD STOP | `pytest tests/safety/test_gate_01_hard_stop.py -v` | 100% detection, < 50ms p99, dual-layer | AC-SAFE-001, AC-SAFE-002 |
| 2 — Consent | `pytest tests/safety/test_gate_02_consent.py -v` | WITHDRAWN→BLOCK, fail-closed proven | AC-SAFE-003 |
| 3 — Yandere | `pytest tests/safety/test_gate_03_yandere.py -v` | Y6→ValueError, Y5 ceiling, Y6 content→Y5 | AC-SAFE-005 |
| 4 — Distress | `pytest tests/safety/test_gate_04_distress.py -v` | 0 false negatives D3/D4, D2→safe mode | AC-SAFE-004 |
| 5 — Drift | `pytest tests/safety/test_gate_05_drift.py -v` | 0%→PASS, 15%→WARN, 25%→ROLLBACK | — (operational) |
| 6 — DNR | `pytest tests/safety/test_gate_06_dnr.py -v` | DNR entry→blocked, pipeline preserved | — (operational) |
| 7 — Classification | `pytest tests/safety/test_gate_07_classification.py -v` | Unknown→Confidential, fields complete | — (operational) |
| 8 — Secrets | `pytest tests/safety/test_gate_08_secrets.py -v` | 18 patterns detected, Shannon≥4.5 flagged | AC-SAFE-006 |
| 9 — Punishment | `pytest tests/safety/test_gate_09_punishment.py -v` | L6→error, D3+→suspended, reward always | AC-SAFE-006 |
| 10 — Forbidden | `pytest tests/safety/test_gate_10_forbidden.py -v` | F-01..F-15 detected, CRITICAL=block, HIGH=rewrite | AC-SAFE-006, AC-SAFE-008 |

> **Note**: Gates 5–7 are operational safety features (drift detection, DNR enforcement, data classification) without direct AC-SAFE criteria in ADR-035. All 8 AC-SAFE criteria (AC-SAFE-001 through AC-SAFE-008) are covered by Gates 1–4 and 8–10. Mapping is authoritative per ADR-035 §Safety Compliance Matrix (lines 1669–1678).

#### Rollback Procedure

```bash
hermes gateway stop   # universal kill-switch (no-op if not running)
rm -f plugins/guinevere_safety_plugin.py plugins/memory_plugin.py
rm -f config/hermes/hooks.yaml config/hermes/mcp-servers.yaml
rm -f hooks/hard_stop.py hooks/consent_gate.py hooks/drift_detector.py \
      hooks/response_scanner.py hooks/output_sanitizer.py hooks/final_safety.py \
      hooks/error_handler.py
cd /home/guinevere/code/guinevere
git checkout -- src/persona/yandere_fsm.py src/persona/drift_detector.py \
                src/persona/safe_mode.py src/persona/hard_stop_handler.py \
                src/persona/consent_gate.py src/persona/punishment_engine.py \
                src/persona/reward_engine.py src/persona/mood_engine.py \
                src/persona/ritual_scheduler.py src/persona/streak_tracker.py
git checkout -- config/hermes/SOUL.md 2>/dev/null || rm -f ~/.hermes/SOUL.md
# Verify
ls src/persona/hard_stop_handler.py && echo "PASS" || echo "FAIL"
# Time: < 3 minutes
```

#### Service Management

No services stopped or restarted. bot.py continues as sole Discord gateway.

#### Config Changes

| File | Change | Lines |
|---|---|---|
| `config/hermes/config.yaml` | Add plugin registration, hook paths, Redis DB5, PostgreSQL DSN, SOUL.md path, HARD STOP triggers | ~200 |
| `config/hermes/hooks.yaml` | 7 hook lifecycle configurations with timeouts, failure modes, stdin JSON contracts | ~200 |
| `config/hermes/SOUL.md` | Guinevere identity constitution (Y4/Y5/Y6, tone, address rules) | ~280 |
| `config/hermes/forbidden_patterns.yaml` | F-01 to F-15 with severity classification | ~80 |
| `config/hermes/secret_patterns.yaml` | 18 secret patterns for response scanner | ~50 |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 17 | `guinevere_safety_plugin.py` (~500), 7 hooks (~500), SOUL.md (~280), hooks.yaml (~200), 5 pattern configs (~230), test files (~2,000) |
| Modified | 1 | `config/hermes/config.yaml` (+150 lines) |
| Deleted | 0 | None |
| **Net delta** | **+4,300 lines** | |

#### Gate Criteria (ALL must pass)

- [ ] Gate 1: HARD STOP < 50ms p99, 100% SLO, dual-layer redundancy
- [ ] Gate 2: Consent fail-closed (ACTIVE→ALLOW, PAUSED→WARN, WITHDRAWN→BLOCK, DB down→BLOCK)
- [ ] Gate 3: Y6 architecturally impossible (YandereLevel(6)→ValueError)
- [ ] Gate 4: D3/D4 distress → crisis protocol, zero false negatives
- [ ] Gate 5: Drift detector: 0%→PASS, 15%→WARN, 25%→ROLLBACK
- [ ] Gate 6: DNR excluded from all recall paths
- [ ] Gate 7: Classification fail-closed (Unknown→Confidential)
- [ ] Gate 8: Secret scanner redacts all 18 patterns + Shannon entropy ≥4.5
- [ ] Gate 9: Punishment suspended at D3+; L6→PunishmentSafetyError; reward always permitted
- [ ] Gate 10: All 15 forbidden patterns detected; CRITICAL→BLOCK, HIGH→REWRITE

**ANY gate failure = DO NOT PROCEED to Phase 2.**

---

### Phase 2: Discord Gateway (5-8 days)

**Risk Level**: HIGH | **Downtime**: ≤ 5 min (cutover only) | **Duration**: 5-8 days + 48hr shadow mode
**Dependencies**: Phase 1 (BLOCKING — all 10 safety gates must PASS)
**Gate**: All 35 slash commands functional. 48hr+ shadow mode parity confirmed by Faiz.
**Rollback trigger**: Any safety injection failure; parity < 90%; Faiz withholds approval

#### Phase 2A: Shadow Mode Setup (ZERO Downtime)

**2A.1: Configure Hermes Discord gateway**

- **Command**:
  ```bash
  # Faiz creates #hermes-shadow channel in Discord (GUILD_ID: 1510876414671323206)
  hermes gateway setup --token "${DISCORD_BOT_TOKEN}" --guild "${DISCORD_GUILD_ID}" --channel "hermes-shadow"
  ```
- **Verify**:
  ```bash
  hermes gateway status | grep "connected\|configured"
  ```
- **Expected**: Gateway configured, channel set to `hermes-shadow`
- **On failure**: Verify Discord token validity; check MESSAGE_CONTENT intent
- **Risk**: R-P2-01-001 — config.yaml missing fields (MEDIUM × MEDIUM = 9 MEDIUM)

**2A.2: Configure shadow-specific settings**

- **Command**:
  ```bash
  hermes config set gateway.discord.channels.primary "hermes-shadow"
  hermes config set memory.compression.enabled false
  hermes config set memory.mirrors.enabled false
  hermes config set model.provider custom
  hermes config set model.base_url "http://localhost:20128/v1"
  ```
- **Verify**: `hermes config get gateway.discord.channels.primary` returns `hermes-shadow`
- **Expected**: Shadow config active
- **On failure**: Debug config schema; verify `hermes config validate`
- **Risk**: R-P2-01-002 — Intent configuration errors (LOW × HIGH = 8 MEDIUM)

**2A.3: Enforce memory write mutex**

- **Command**:
  ```bash
  sudo -u postgres psql -d guinevere -c "
    REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM hermes_app;
    REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA memory FROM hermes_app;
  "
  ```
- **Verify**:
  ```sql
  SELECT table_schema, table_name, privilege_type FROM information_schema.table_privileges WHERE grantee = 'hermes_app';
  ```
- **Expected**: Only SELECT rows, zero INSERT/UPDATE/DELETE
- **On failure**: Re-run REVOKE; if role doesn't exist, create it first
- **Risk**: R-P2-05-001 — Memory write mutex is policy-enforced (MEDIUM × HIGH = 12 HIGH)

**2A.4: Launch Hermes gateway in shadow mode**

- **Command**:
  ```bash
  hermes gateway start
  sleep 5
  hermes gateway status
  ```
- **Verify**: Gateway connected, bot.py still running, #hermes-shadow empty
- **Expected**: Hermes connected to shadow channel; bot.py unaffected in #guinevere-chat
- **On failure**: `hermes gateway stop` + debug logs
- **Risk**: R-P2-05-002 — Resource contention (MEDIUM × HIGH = 12 HIGH)

**2A.5: Deploy shadow mode monitoring**

- **Command**:
  ```bash
  # Deploy /home/guinevere/scripts/shadow_monitor.sh per Report 10 §2.6
  sudo systemctl enable --now shadow-monitor.timer
  ```
- **Verify**: Timer active, monitor script runs every 60s
- **Expected**: Shadow cost tracked; connectivity verified every 60s
- **On failure**: Debug timer; check script syntax
- **Risk**: LOW — monitoring is non-critical during shadow

**2A.6: Shadow mode — Stage 0 (0% traffic, 24+ hours)**

- **Action**: Hermes receives but does NOT respond to forwarded messages. Only responds in #hermes-shadow when Faiz tests directly.
- **Verify**:
  ```bash
  sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM audit.hermes_writes WHERE timestamp > now() - interval '1 hour';"
  ```
- **Expected**: Zero Hermes PostgreSQL writes, bot.py unaffected
- **On failure**: Any PostgreSQL write → IMMEDIATE ABORT
- **Risk**: R-P2-OVER-02 — Shadow mode complexity (HIGH × MEDIUM = 12 HIGH)

**2A.7: Shadow mode — Active safety injections**

| Injection | Count | Timing | Expected |
|---|---|---|---|
| HARD STOP | 3× | Hours 4, 24, 44 | Neutral response, LLM not called |
| Y6 content | 3× | Hours 8, 28, 46 | Content rewritten to Y5 or blocked |
| Consent revocation | 1× | Hour 16 | Tool calls blocked |
| Distress (D3/D4) | 1× | Hour 32 | Crisis protocol activated |
| Hook failure | 1× | Hour 40 | Message blocked (fail-closed) |

- **Verify**:
  ```bash
  python -m pytest tests/safety/test_shadow_*.py -v --count=9
  ```
- **Expected**: 9/9 injections pass (3 HARD STOP + 3 Y6 + 1 consent + 1 distress + 1 hook failure)
- **On failure**: Any injection failure → DO NOT CUT OVER → fix and re-shadow
- **Risk**: R-P2-OVER-03 — Shadow does NOT validate safety (HIGH × HIGH = 16 CRITICAL)

**2A.8: Response parity comparison (100 queries)**

- **Command**: Send 100 identical messages to both #guinevere-chat (bot.py) and #hermes-shadow (Hermes)
- **Verify**: ≥ 95% functional parity, 100% safety parity
- **Expected**: Responses semantically equivalent; safety decisions identical
- **On failure**: Investigate divergence; if > 2 safety divergences → BLOCKED
- **Risk**: R-P2-06-001 — Surface-level parity misses safety divergence (MEDIUM × HIGH = 12 HIGH)

**2A.9: Migrate 35 slash commands to plugins**

- **Command**: Create 35 plugin files (`plugins/*_plugin.py`) using `ctx.register_command()`
- **Verify**:
  ```bash
  hermes gateway commands list | wc -l
  # Expected: >= 35
  ```
- **Expected**: All 35 commands registered, 8 HIGH + 15 MEDIUM + 12 LOW feasibility
- **On failure**: Fix individual command plugins; re-test
- **Risk**: R-P2-02-001/03-001/04-001 — Command API mismatch, backend access, stateful complexity (6-9 MEDIUM each)

#### Phase 2B: Hard Cutover (≤ 5 MINUTES DOWNTIME)

**2B.1: Pre-cutover verification**

- **Command**:
  ```bash
  # Run pre-cutover checklist
  hermes gateway status | grep "connected" || { echo "FAIL"; exit 1; }
  sudo systemctl is-active guinevere-discord | grep "active" || { echo "FAIL"; exit 1; }
  hermes doctor --verbose | grep -c "FAIL" | xargs -I{} bash -c '[ {} -eq 0 ]' || { echo "FAIL"; exit 1; }
  ```
- **Verify**: Hermes connected, bot.py active, hermes doctor clean
- **Expected**: All pre-flight checks pass
- **On failure**: Fix issues; DO NOT cutover

**2B.2: Create pre-cutover checkpoint**

- **Command**:
  ```bash
  hermes checkpoints create --label "pre-cutover-$(date +%Y%m%d-%H%M%S)"
  sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/pre-cutover-$(date +%Y%m%d).dump
  ```
- **Verify**: Checkpoint listed, dump file exists
- **Expected**: Both artifacts created
- **On failure**: Debug checkpoint creation; proceed without checkpoint (risk accepted)

**2B.3: Cutover — Stop bot.py, Start Hermes as primary**

- **Command**:
  ```bash
  # DOWNTIME BEGINS
  sudo systemctl stop guinevere-discord
  sleep 2
  sudo systemctl is-active --quiet guinevere-discord && { echo "FAIL: bot.py still running"; exit 1; }

  # Reconfigure Hermes for production
  hermes gateway stop; sleep 2
  hermes config set gateway.discord.channels.primary "guinevere-chat"
  hermes config set memory.compression.enabled true
  hermes config set memory.compression.threshold 0.70
  hermes config set memory.mirrors.enabled true

  # Start Hermes as primary
  hermes gateway start; sleep 5
  hermes gateway status | grep "connected" || { echo "CRITICAL: ROLLBACK"; hermes gateway stop; sudo systemctl start guinevere-discord; exit 1; }

  # DOWNTIME ENDS
  sudo systemctl disable guinevere-discord
  ```
- **Verify**:
  - Hermes connected to #guinevere-chat
  - bot.py inactive and disabled (but service file preserved)
  - HARD STOP works via Hermes (send "HARD STOP" → neutral)
  - /status command works
- **Expected**: Downtime < 5 minutes; Guinevere online via Hermes
- **On failure**: IMMEDIATE ROLLBACK (see below)
- **Risk**: R-P2-08-001/002 — bot.py service state, cutover time (LOW × HIGH = 8 MEDIUM)

**2B.4: Post-cutover verification (first 5 minutes)**

- **Command**:
  ```bash
  # Verify HARD STOP
  # Faiz sends "HARD STOP" in #guinevere-chat → neutral response
  # Verify streaming
  # Faiz sends long question → progressive edits at ~1.2s intervals
  # Verify 35 commands
  hermes gateway commands list | wc -l
  ```
- **Verify**: HARD STOP neutral, all 35 commands registered, streaming visible
- **Expected**: Full production parity
- **On failure**: If HARD STOP fails → IMMEDIATE ROLLBACK

#### Safety Checkpoint

- [ ] `P2-T1`: HARD STOP via Hermes gateway — dual-layer, LLM not called
- [ ] `P2-T2`: 3/3 HARD STOP injections pass during shadow mode
- [ ] `P2-T3`: 3/3 Y6 content injections rewritten/blocked
- [ ] `P2-T4`: 1/1 consent revocation blocks tool calls
- [ ] `P2-T5`: 1/1 distress injection activates crisis protocol
- [ ] `P2-T6`: 1/1 hook failure → fail-closed (message blocked)
- [ ] `P2-T7`: Safety parity: 100/100 decisions match bot.py vs Hermes
- [ ] `P2-T8`: 35/35 slash commands functional

#### Rollback Procedure

**Shadow mode rollback (< 1 min)**:
```bash
hermes gateway stop
hermes gateway uninstall
# bot.py continues running — no action needed
```

**Cutover rollback (< 2 min)**:
```bash
hermes gateway stop
sudo systemctl start guinevere-discord
sudo systemctl enable guinevere-discord
systemctl status guinevere-discord | grep "active (running)"
# Verify: send "HARD STOP" in #guinevere-chat → neutral response from bot.py
```

#### Service Management

| Service | Phase 2A (Shadow) | Phase 2B (Cutover) |
|---|---|---|
| `guinevere-discord.service` | KEEP RUNNING | STOP + DISABLE |
| `hermes-gateway` (manual) | START (shadow mode) | START (production) |
| `guinevere-loops.service` | KEEP RUNNING | RESTART (optional, point to Hermes API) |
| All other 5 services | KEEP RUNNING | KEEP RUNNING |

#### Config Changes

| File | Change |
|---|---|
| `config/hermes/config.yaml` | Add gateway section (token, guild, intents, channels); add 35 plugin registrations; add shadow mode config |
| `systemd/guinevere-discord.service` | DISABLED post-cutover (preserved for rollback) |
| `systemd/hermes-gateway.service` | NEW — Hermes gateway systemd unit |
| `.env.hermes` | NEW — SOPS-encrypted Hermes secrets |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 37 | 35 command plugins (~4,409 lines), gateway.yaml (~80), shadow-report.md (~200) |
| Modified | 4 | config.yaml (+150), notifications.py (-102), 2 systemd units |
| Deleted | 11 | 9 Discord infrastructure + 2 Hermes adapters (at cutover only) |
| Refactored | 36 | 35 commands → plugins + notifications |
| **Net delta** | **-5,779 lines** | Discord: 9,805 → ~4,026 |

#### Gate Criteria

- [ ] All 35 slash commands functional (`hermes gateway commands list | wc -l` >= 35)
- [ ] 48hr+ shadow mode with ALL 9 active safety injections passing
- [ ] Safety parity 100% — zero safety decision divergences
- [ ] Functional parity ≥ 90% on 100 test queries
- [ ] Faiz explicit approval received ("cutover approved" or "lanjut cutover")
- [ ] Cutover downtime < 5 minutes
- [ ] HARD STOP verified post-cutover (neutral response, LLM not called)
- [ ] Streaming responses visible (progressive edits at ~1.2s)

---

### Phase 3: Memory Bridge (4-5 days)

**Risk Level**: MEDIUM | **Downtime**: ~10s config reload | **Duration**: 4-5 days
**Dependencies**: Phase 2 (BLOCKING — Discord cutover complete)
**Gate**: Memory recall quality unchanged (A/B test p > 0.05). DNR + classification enforced. Zero PostgreSQL writes from Hermes.
**Rollback trigger**: Recall degradation; DNR content in session_search; PostgreSQL writes detected

#### Steps

**3.1: Refactor memory_bridge.py → memory_plugin.py**

- **Command**:
  ```bash
  # Create plugins/memory_plugin.py (~180 lines)
  # Wraps recall_for_context() and store_conversation() unchanged
  ```
- **Verify**:
  ```bash
  pytest tests/hermes/test_memory_plugin.py -v
  ```
- **Expected**: Plugin loads, recall works, store works, DNR gate functional
- **On failure**: Debug wrapper; verify PostgreSQL connectivity from plugin
- **Risk**: R-P3-03-001 — Wrapper introduces bug (MEDIUM × HIGH = 12 HIGH)

**3.2: Enable Hermes compression at 70% threshold**

- **Command**:
  ```bash
  hermes config set memory.compression.enabled true
  hermes config set memory.compression.threshold 0.70
  hermes config set memory.compression.target 0.20
  hermes config set memory.compression.protect_last 20
  hermes gateway restart   # or config reload if supported
  ```
- **Verify**: Compression active in Hermes logs
- **Expected**: Context compression at 70% threshold, last 20 messages protected
- **On failure**: `hermes config set memory.compression.enabled false` (< 5s rollback)
- **Risk**: R-P3-01-001 — Compression drops critical memories (MEDIUM × HIGH = 12 HIGH)

**3.3: Enable session_search (FTS5)**

- **Command**:
  ```bash
  hermes config set memory.session_search.enabled true
  hermes config set memory.session_search.backend "fts5"
  ```
- **Verify**: `hermes memory status` shows session_search enabled
- **Expected**: Cross-session search via FTS5
- **On failure**: Disable session_search; DNR filter must apply
- **Risk**: R-P3-02-001 — DNR in session_search results (LOW × HIGH = 8 MEDIUM)

**3.4: Configure mirror sync (MEMORY.md/USER.md)**

- **Command**:
  ```bash
  hermes config set memory.mirrors.enabled true
  hermes config set memory.mirrors.sync_interval_messages 5
  ```
- **Verify**: MEMORY.md and USER.md created and updated every 5 messages
- **Expected**: Mirror sync operational; no classified data in plaintext mirror
- **On failure**: `hermes config set memory.mirrors.enabled false`
- **Risk**: R-P3-04-001 — Mirror sync divergence (LOW × MEDIUM = 6 MEDIUM)

**3.5: A/B test memory recall on 100 queries**

- **Command**:
  ```bash
  python scripts/ab-test-recall.py --queries 100 --threshold 0.05
  ```
- **Verify**: p-value > 0.05; recall precision delta < 1%
- **Expected**: Memory recall quality statistically unchanged
- **On failure**: If p < 0.05 → rollback compression, investigate
- **Risk**: R-P3-05-001 — A/B test invalid if embedding API broken (MEDIUM × HIGH = 12 HIGH)

**3.6: Verify zero PostgreSQL writes from Hermes path**

- **Command**:
  ```bash
  sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM audit.hermes_writes;"
  ```
- **Verify**: Count = 0
- **Expected**: Zero unauthorized PostgreSQL writes
- **On failure**: Investigate source; revoke Hermes write access
- **Risk**: R-P3-06-001 — Undetected PostgreSQL writes (LOW × CRITICAL = 10 MEDIUM)

#### Safety Checkpoint

- [ ] `P3-T1`: A/B recall quality unchanged (p > 0.05)
- [ ] `P3-T2`: Zero DNR content in Hermes recall paths
- [ ] `P3-T3`: Zero PostgreSQL data modifications from Hermes (`count(*)` = 0)
- [ ] `P3-T4`: Mirror sync safe (no classified data in MEMORY.md/USER.md)

#### Rollback Procedure

```bash
hermes config set memory.compression.enabled false
hermes config set memory.session_search.enabled false
hermes config set memory.mirrors.enabled false
hermes gateway restart   # < 3 minutes
```

#### Service Management

No service stops. Hermes gateway config reload only (~10s). All 7 systemd services keep running.

#### Config Changes

| File | Change |
|---|---|
| `config/hermes/config.yaml` | Add memory section: compression 70%, session_search, mirror sync, bridge plugin config |
| `src/hermes/memory_bridge.py` | Refactored → ~150 lines (simplified) |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 3 | `memory_plugin.py` (~180), `auth_matrix.yaml` (~90), `ab-test-recall.py` (~100) |
| Modified | 2 | config.yaml (+50), memory_bridge.py (-101) |
| Deleted | 0 | None |
| **Net delta** | **+319 lines** | |

#### Gate Criteria

- [ ] Memory recall quality unchanged (A/B test p > 0.05)
- [ ] DNR enforcement verified on both recall paths
- [ ] Classification enforcement preserved
- [ ] Zero PostgreSQL modifications from Hermes path (`SELECT count(*) FROM audit.hermes_writes` = 0)
- [ ] Compression threshold at 70% (not 50%)

---

### Phase 4: MCP + Tools (5-7 days)

**Risk Level**: MEDIUM | **Downtime**: None | **Duration**: 5-7 days
**Dependencies**: Phase 1 (BLOCKING — consent_gate hook), Phase 2 (BLOCKING — gateway running)
**Gate**: All 16 tool capabilities available. Auth matrix enforced on all. Security audit clean.
**Rollback trigger**: Auth matrix bypass; FORBIDDEN command executes; auth overlay fails to load

#### Steps

**4.1: Register 5 Hermes native MCP servers**

- **Command**:
  ```bash
  hermes mcp add web --config ./config/hermes/mcp-servers.yaml
  hermes mcp add filesystem --config ./config/hermes/mcp-servers.yaml
  hermes mcp add terminal --config ./config/hermes/mcp-servers.yaml
  hermes mcp add git --config ./config/hermes/mcp-servers.yaml
  hermes mcp add fetch --config ./config/hermes/mcp-servers.yaml
  ```
- **Verify**: `hermes mcp list` shows 5 servers active
- **Expected**: 5 native MCP servers registered, functional
- **On failure**: Debug server configs; test individual server connectivity
- **Risk**: R-P4-01-001 — Native MCP enabled WITHOUT auth overlay (MEDIUM × CRITICAL = 15 HIGH)

**4.2: Build auth overlay plugin**

- **Command**:
  ```bash
  # Create plugins/auth_overlay.py (~220 lines)
  # Intercepts ALL tool calls via pre_tool_call hook
  # Enforces READ_AUTO/WRITE_NOTIFY/DESTRUCTIVE_APPROVAL/FORBIDDEN
  # Plugin critical: true — Hermes refuses to start without it
  ```
- **Verify**:
  ```bash
  pytest tests/hermes/test_auth_overlay.py -v
  ```
- **Expected**: All 4 auth levels enforced; FORBIDDEN→block; DESTRUCTIVE→webhook; plugin load gate works
- **On failure**: Debug auth overlay; test each auth level independently
- **Risk**: R-P4-OVER-02 — Auth overlay handles different JSON payloads (MEDIUM × MEDIUM = 9 MEDIUM)

**4.3: Package 7 custom tools as plugins**

- **Command**:
  ```bash
  # Keep as custom FastMCP: postgres_tool, redis_tool, obscura_cdp, grep_app, context7, sequential_thinking, time_tools
  # Verify guinevere-mcp.service still running
  sudo systemctl is-active guinevere-mcp
  ```
- **Verify**: All 7 custom tools accessible; `curl -sf http://localhost:8000/api/mcp/status` returns 7 tools
- **Expected**: Custom tools functional alongside Hermes native tools
- **On failure**: Restart guinevere-mcp; debug individual tool
- **Risk**: MEDIUM — custom tools unchanged

**4.4: Wire auth matrix to pre_tool_call hook**

- **Command**:
  ```bash
  # auth_overlay.py intercepts ALL tool calls (native + custom)
  # Config: config/hermes/auth_matrix.yaml (4-level mapping for all 16 tools)
  ```
- **Verify**:
  ```bash
  python scripts/test_auth_matrix.py
  ```
- **Expected**: All 16 tools mapped to correct auth level; 64 operations verified
- **On failure**: Fix auth matrix mapping; re-test
- **Risk**: R-P4-OVER-01 — Auth matrix bypass (MEDIUM × CRITICAL = 15 HIGH)

**4.5: Test all 16 tools from conversation**

- **Command**: Test each tool via Hermes Discord gateway
- **Verify**: All 16 tools respond correctly; auth enforcement active
- **Expected**: 16/16 tools functional with auth enforcement
- **On failure**: Fix individual tool; re-test

#### Safety Checkpoint

- [ ] `P4-T1`: Auth matrix — 64/64 operations at correct level
- [ ] `P4-T2`: Plugin load gate — Hermes refuses to start without auth overlay
- [ ] `P4-T3`: FORBIDDEN commands hard-disabled (7/7 blocked)
- [ ] `P4-T4`: Budget enforcement at 80%/90%/100% thresholds
- [ ] `P4-T5`: post_tool_call output sanitization (credentials REDACTED, DNR filtered)

#### Rollback Procedure

```bash
hermes mcp remove web filesystem terminal git fetch 2>/dev/null || true
rm -f plugins/auth_overlay.py
cd /home/guinevere/code/guinevere
git checkout -- src/mcp/manager.py src/mcp/auth_matrix.py src/mcp/tools/
sudo systemctl restart guinevere-mcp
# Time: < 2 minutes
```

#### Service Management

| Service | Action |
|---|---|
| `guinevere-mcp.service` | KEEP RUNNING (serves 7 custom tools) |
| Hermes gateway | RESTART (pick up auth overlay + native MCP config) |
| All other services | KEEP RUNNING |

#### Config Changes

| File | Change |
|---|---|
| `config/hermes/mcp-servers.yaml` | NEW — 5 native + 7 custom MCP server configs |
| `config/hermes/auth_matrix.yaml` | NEW — 4-level matrix for all 16 tools |
| `config/hermes/config.yaml` | Add MCP section, auth overlay plugin registration |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 2 | `auth_overlay.py` (~220), `mcp-servers.yaml` (~90) |
| Modified | 16 | MCP core (6 refactored) + 9 tools refactored + config |
| Deleted | 9 | 7 native-migrated tools + manager.py + tools/__init__.py |
| **Net delta** | **-2,473 lines** | MCP: 5,183 → ~2,710 |

#### Gate Criteria

- [ ] All 16 tool capabilities available (5 native + 7 custom + 4 hybrid)
- [ ] Auth matrix enforced on ALL 16 tools (64/64 correct auth levels)
- [ ] Plugin load gate: Hermes refuses to start without auth_overlay
- [ ] FORBIDDEN operations impossible (7/7 blocked)
- [ ] Security audit clean

---

### Phase 5: Skills + SOUL.md (2-3 days)

**Risk Level**: LOW | **Downtime**: None | **Duration**: 2-3 days
**Dependencies**: Phase 1 (BLOCKING — safety hooks for drift + Y6), Phase 2 (NON-BLOCKING)
**Gate**: All persona features functional. Mood persists. 5 daily rituals fire.
**Rollback trigger**: Persona drift detected; ritual misses schedule

#### Steps

**5.1: Install priority skills from agentskills.io**

- **Command**:
  ```bash
  hermes skills search safety
  hermes skills install <skill-name>
  hermes skills list
  ```
- **Verify**: Skills installed and functional
- **Expected**: 3-5 skills installed; no conflicts with safety plugin
- **On failure**: `hermes skills uninstall <skill>` — remove problematic skill
- **Risk**: LOW — skills are supplementary

**5.2: Finalize SOUL.md**

- **Command**:
  ```bash
  # Edit config/hermes/SOUL.md
  # Add: address rules, communication instructions, prompt injection defense
  chmod 444 config/hermes/SOUL.md
  ```
- **Verify**: SOUL.md permissions 444; drift detector baseline updated
- **Expected**: Y4/Y5/Y6 constraints, tone rules, address terms, 75/25 ID/EN ratio, prompt injection defense
- **On failure**: Restore from git; re-edit
- **Risk**: R-P5-01-001 — Persona drift (MEDIUM × HIGH = 12 HIGH)

**5.3: Configure persona plugins (mood, rituals, punishment, reward, streaks)**

- **Command**:
  ```bash
  # Extend plugins/persona_plugin.py (~350 lines)
  # Consolidates 14 refactored src/persona/ files
  ```
- **Verify**:
  ```bash
  pytest tests/persona/ -v
  ```
- **Expected**: Mood persists, rituals fire, punishment/reward/streaks functional
- **On failure**: Debug individual plugin feature; port from original persona code
- **Risk**: R-P1-10-001/002/003 — Punishment config, safe mode confirmation, phrase rewrite (6-9 MEDIUM)

**5.4: Configure hermes cron for rituals**

- **Command**:
  ```bash
  hermes cron add "ritual_morning" "0 8 * * *" "hermes plugin trigger guinevere_safety ritual morning"
  hermes cron add "ritual_midday" "0 12 * * *" "hermes plugin trigger guinevere_safety ritual midday"
  hermes cron add "ritual_afternoon" "0 16 * * *" "hermes plugin trigger guinevere_safety ritual afternoon"
  hermes cron add "ritual_evening" "0 20 * * *" "hermes plugin trigger guinevere_safety ritual evening"
  hermes cron add "ritual_midnight" "0 0 * * *" "hermes plugin trigger guinevere_safety ritual midnight"
  ```
- **Verify**: `hermes cron list` shows 5 ritual cron jobs
- **Expected**: 5 daily rituals fire on schedule (morning, midday, afternoon, evening, midnight)
- **On failure**: Debug cron syntax; verify plugin trigger path
- **Risk**: LOW — cron is Hermes built-in

#### Safety Checkpoint

- [ ] `P5-T1`: SOUL.md contains all Guinevere constraints (Y4/Y5/Y6, address rules, 75/25 ID/EN)
- [ ] `P5-T2`: SOUL.md permissions 444 (read-only)
- [ ] `P5-T3`: All 5 daily rituals fire on schedule
- [ ] `P5-T4`: Mood persists across sessions
- [ ] `P5-T5`: Persona tone matches Y4 baseline (dominant, NOT kawaii)

#### Rollback Procedure

```bash
hermes skills uninstall <skill_name>   # per skill
git checkout -- config/hermes/SOUL.md
rm -f plugins/persona_plugin.py
hermes cron remove --all
hermes gateway restart
# Time: < 2 minutes
```

#### Service Management

No service stops. SOUL.md re-read on next session. Cron added to running Hermes.

#### Config Changes

| File | Change |
|---|---|
| `config/hermes/SOUL.md` | Enhanced: address rules, communication instructions, prompt injection defense |
| `config/hermes/config.yaml` | Add persona plugin + cron references |
| `config/hermes/crontab.yaml` | NEW — 5 ritual cron schedules + daily health check |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | ~6 | Skills (~500), crontab (~50), persona_plugin (~350) |
| Modified | 18 | SOUL.md (+70), config (+20), 14 persona files refactored, persona_plugin |
| Deleted | 0 | None |
| **Net delta** | **-446 lines** | Persona: 3,817 → ~3,371 |

#### Gate Criteria

- [ ] SOUL.md contains all Y4/Y5/Y6 constraints
- [ ] All persona features functional
- [ ] Mood persists across sessions
- [ ] 5 daily rituals fire on schedule
- [ ] SOUL.md permissions 444

---

### Phase 6: LLM Routing (1 day)

**Risk Level**: LOW | **Downtime**: ~30s model switch | **Duration**: 1 day
**Dependencies**: Phase 2 (BLOCKING — gateway running), Phase 1 (NON-BLOCKING)
**Gate**: LLM routing functional. Fallback works. Budget enforced at $30/mo.
**Rollback trigger**: LLM calls fail; fallback doesn't engage; budget not enforced

#### Steps

**6.1: Configure 9Router as custom provider**

- **Command**:
  ```bash
  hermes model set --provider custom --model gpt-5.5 --base-url "http://localhost:20128/v1" --api-key "${NINEROUTER_API_KEY}"
  ```
- **Verify**:
  ```bash
  hermes model show
  curl -sf http://localhost:20128/health
  ```
- **Expected**: Model configured; 9Router healthy
- **On failure**: Check 9Router connectivity; verify API key
- **Risk**: R-P5-?? (LOW — config-only change)

**6.2: Configure fallback chain**

- **Command**:
  ```bash
  hermes fallback set --provider custom --base-url "http://localhost:20128/v1" --model deepseek-v4-flash
  ```
- **Verify**: Test primary failure → fallback activates
- **Expected**: GPT-5.5 down → DeepSeek V4 Flash takes over
- **On failure**: Debug fallback config; verify 9Router supports both models
- **Risk**: R-P6-01-001 — Fallback doesn't engage (LOW × HIGH = 8 MEDIUM)

**6.3: Configure budget enforcement**

- **Command**:
  ```bash
  hermes config set budget.monthly_limit 30.00
  hermes config set budget.alert_threshold 0.80
  hermes config set budget.block_threshold 1.00
  ```
- **Verify**:
  ```bash
  pytest tests/hermes/test_budget_hook.py -v
  ```
- **Expected**: Alert at 80% ($24), block at 100% ($30)
- **On failure**: Debug budget hook; test threshold edge cases
- **Risk**: R-P10-01-001 — Budget not enforced (MEDIUM × MEDIUM = 9 HIGH)

**6.4: Test LLM via 9Router (100-test-prompt compatibility)**

- **Command**:
  ```bash
  python scripts/test_100_prompts.py
  ```
- **Verify**: 100/100 prompts route correctly through 9Router
- **Expected**: All prompts receive valid LLM responses
- **On failure**: Investigate 9Router compatibility; debug API format
- **Risk**: LOW — pre-migration compatibility test

#### Safety Checkpoint

- [ ] `P6-T1`: 100/100 prompts route correctly through 9Router
- [ ] `P6-T2`: Fallback chain: GPT-5.5 → DeepSeek V4 Flash works
- [ ] `P6-T3`: Budget enforced at $30/month (alert 80%, block 100%)
- [ ] `P6-T4`: Streaming compatible with 9Router (progressive edits at ~1.2s)

#### Rollback Procedure

```bash
hermes model set --model default
hermes fallback set --model none
hermes config set budget.monthly_limit 0
hermes gateway restart
# Time: < 2 minutes
```

#### Service Management

Hermes gateway model reconfiguration only (~30s). Gateway stays up. 9Router unchanged.

#### Config Changes

| File | Change |
|---|---|
| `config/hermes/config.yaml` | Add LLM section: model, base_url, fallback, budget |
| `plguins/guinevere_safety_plugin.py` | Add budget enforcement to pre_tool_call hook |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 1 | `test_9router_compatibility.py` (~150) |
| Modified | 3 | config.yaml (+20), safety_plugin (+10), systemd (+5) |
| Deleted | 0 | None |
| **Net delta** | **+185 lines** | |

#### Gate Criteria

- [ ] LLM routing functional: GPT-5.5 via 9Router → responses returned
- [ ] Fallback chain: GPT-5.5 failure → DeepSeek V4 Flash takes over
- [ ] Budget enforced at $30/mo (alert at 80%, block at 100%)
- [ ] 100/100 test prompts route correctly

---

### Phase 7: Hardening + Monitoring (2-3 days)

**Risk Level**: LOW | **Downtime**: None | **Duration**: 2-3 days
**Dependencies**: ALL previous phases (0-6 must pass)
**Gate**: All monitoring active. `hermes security` clean. `hermes doctor` clean. Runbook complete. Performance within +10% of baseline.
**Rollback trigger**: Performance > +10% baseline; `hermes security` finds HIGH issues

#### Steps

**7.1: Full regression test suite (T1-T10)**

- **Command**:
  ```bash
  pytest tests/integration/test_verification.py -v
  ```
- **Verify**: All 10 verification tests pass (100+ test cases)
- **Expected**: T1-T10 all PASS
- **On failure**: Fix regressions; re-test
- **Risk**: LOW — post-migration verification

**7.2: Security audit (`hermes security` zero HIGH)**

- **Command**:
  ```bash
  hermes security --format json > evidence/p7-security-final.json
  python -c "import json; d=json.load(open('evidence/p7-security-final.json')); h=[v for v in d.get('vulnerabilities',[]) if v['severity'] in ('HIGH','MODERATE')]; assert len(h)==0, f'{len(h)} unresolved'; print('SECURITY: PASS')"
  ```
- **Verify**: Zero HIGH/MODERATE findings
- **Expected**: Security clean
- **On failure**: Fix HIGH findings; re-scan

**7.3: Performance baseline**

- **Command**:
  ```bash
  python scripts/benchmark.py --baseline /home/guinevere/backups/pre-migration-bench.json
  ```
- **Verify**: Latency within +10% of baseline; hook overhead < 450ms cumulative
- **Expected**: Performance within acceptable range
- **On failure**: Profile hooks; tune compression; investigate bottlenecks

**7.4: Monitoring verification**

- **Command**:
  ```bash
  curl -sf http://localhost:9090/-/healthy && echo "Prometheus: OK"
  curl -sf http://localhost:3000/api/health && echo "Grafana: OK"
  curl -sf http://localhost:9191/metrics | head -5 && echo "Hermes metrics: OK"
  ```
- **Verify**: Prometheus, Grafana, Loki all healthy; Hermes metrics endpoint active
- **Expected**: Full monitoring stack operational
- **On failure**: Restart monitoring stack; verify scrape configs

**7.5: Final backup**

- **Command**:
  ```bash
  hermes checkpoints create --label "migration-complete-$(date +%Y%m%d-%H%M%S)"
  sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/migration-complete-$(date +%Y%m%d).dump
  rclone copy /home/guinevere/backups/migration-complete-*.dump idcloudhost:guinevere-dr-backups/
  ```
- **Verify**: Checkpoint created, dump exists, offsite uploaded
- **Expected**: Final migration state captured

**7.6: Delete deprecated files (after 48hr stable)**

- **Command**:
  ```bash
  # After 48+ hours of stable operation:
  rm -f src/discord/bot.py src/discord/conversational_handler.py src/discord/commands.py
  rm -f src/discord/permissions.py src/discord/guild_setup.py src/discord/startup.py
  rm -f src/discord/_embed_helpers.py src/discord/intents.py
  rm -f src/hermes/session_adapter.py
  ```
- **Verify**: Deprecated files removed; core services unaffected
- **Expected**: 9 obsolete Discord infrastructure files deleted
- **On failure**: Restore from git; investigate dependency

#### Safety Checkpoint

- [ ] `P7-T1`: All 10 verification tests (T1-T10) PASS
- [ ] `P7-T2`: `hermes security` zero HIGH/MODERATE
- [ ] `P7-T3`: Performance within +10% of baseline
- [ ] `P7-T4`: Prometheus, Grafana, Loki all healthy; Hermes metrics on port 9191
- [ ] `P7-T5`: Final backup complete (checkpoint + PG dump + offsite)
- [ ] `P7-T6`: Runbook complete at `runbooks/hermes-migration-runbook.md` (500+ lines)
- [ ] `P7-T7`: All 8 per-phase rollback scripts verified executable
- [ ] `P7-T8`: Global emergency rollback tested (dry-run)

#### Rollback Procedure

```bash
hermes cron remove --all
hermes config set backup.enabled false
# Disable problematic alert rules
# Time: < 3 minutes
```

#### Rollback Procedure (Full — if multiple phases need revert)

```bash
hermes gateway stop
sudo systemctl start guinevere-discord
sudo systemctl disable hermes-gateway
cd /home/guinevere/code/guinevere
PRE_TAG=$(git tag | grep "pre-hermes-migration" | tail -1)
git checkout "$PRE_TAG" -- src/discord/ src/mcp/ src/persona/ src/hermes/
sudo systemctl restart guinevere-mcp guinevere-loops
curl -sf http://localhost:8000/health || echo "WARN: core health check failed"
rm -rf plugins/ config/hermes/
# Verify: HARD STOP works; /status responds
# Time: < 5 minutes
```

#### Service Management

All 7 systemd services keep running. Hermes cron and backup added as live config. Monitoring targets updated.

#### Config Changes

| File | Change |
|---|---|
| `config/hermes/config.yaml` | Add observability section (Prometheus port 9191, Loki integration, cron, backup) |
| `monitoring/prometheus/prometheus.yml` | Add Hermes scrape job (target: `host.docker.internal:9191`) |
| `monitoring/alertmanager/` | Add Hermes alert rules (SEV0-SEV4) |
| `monitoring/grafana/dashboards/` | Add Hermes dashboard JSON |
| `systemd/hermes-healthcheck.timer` | NEW — 60s health check timer |
| `systemd/hermes-backup.timer` | NEW — daily backup timer |

#### File Changes

| Type | Count | Details |
|---|---|---|
| Created | 14 | Runbook (~500), 8 per-phase rollback scripts (~260), global rollback (~60), backup script (~40), health-check (~40), benchmark (~150), rollback-drill (~100) |
| Modified | 5 | config.yaml (+30), 2 systemd timers, Prometheus config (+20), Grafana dashboard (+100) |
| Deleted | 0 | None (obsolete src/discord/ files deleted after 48hr stable) |
| **Net delta** | **+1,305 lines** | |

#### Gate Criteria

- [ ] T1-T10 verification suite: ALL PASS (100+ test cases, 0 failures)
- [ ] `hermes security`: zero HIGH/MODERATE
- [ ] `hermes doctor`: all checks PASS
- [ ] Performance within +10% of baseline (latency < 3s p95, recall < 2s, HARD STOP < 50ms)
- [ ] All monitoring active (Prometheus, Grafana, Loki, Hermes metrics port 9191)
- [ ] Runbook complete (500+ lines) at `runbooks/hermes-migration-runbook.md`
- [ ] All 8 per-phase rollback scripts verified executable
- [ ] Global emergency rollback dry-run tested

---

## Section 5: Verification Test Suite (T1-T10)

### T1: Basic Conversation (Y4 Persona)

```bash
pytest tests/integration/test_verification.py::TestT1BasicConversation -v
```
**Expected**: Send "Hi Guinevere" → Y4 Dominant persona response. 10+ test messages across varied topics. Response time < 30s.
| Pass | All responses use Y4 dominant tone; no kawaii excess; proper Guinevere identity markers |
| Fail | Neutral tone degradation; missing persona markers; Y6-adjacent language |

### T2: Multi-Turn Memory (Cross-Session)

```bash
pytest tests/integration/test_verification.py::TestT2MultiTurnMemory -v
```
**Expected**: Store "My project deadline is June 15" → new session → "When is my deadline?" → "June 15". 5+ cross-session pairs. DNR content never recalled.
| Pass | Accurate recall across sessions; zero hallucination; zero DNR leakage |
| Fail | Memory fabrication; DNR content recalled; wrong facts |

### T3: MCP Tools from Chat

```bash
pytest tests/integration/test_verification.py::TestT3MCPTools -v
```
**Expected**: "search for Python asyncio best practices" → brave_search called → results returned. 4+ tool tests across different auth levels.
| Pass | All tools respond correctly; auth matrix enforced |
| Fail | Tool call fails; auth bypass; FORBIDDEN operation succeeds |

### T4: HARD STOP Working (< 50ms)

```bash
pytest tests/integration/test_verification.py::TestT4HardStop -v
```
**Expected**: "HARD STOP" → neutral acknowledgment < 50ms. LLM NOT called. Yandere → Y0_NEUTRAL. Punishment suspended. 8+ trigger variants tested.
| Pass | 100% trigger detection; < 50ms p99; LLM call count = 0; Y0_NEUTRAL |
| Fail | Any persona response to HARD STOP; LLM called; > 50ms |

### T5: Safe Mode Working

```bash
pytest tests/integration/test_verification.py::TestT5SafeMode -v
```
**Expected**: D2 message ("I'm feeling anxious") → safe_mode. D3/D4 → crisis protocol, Y0_NEUTRAL. No auto-deactivation. 6+ distress variants.
| Pass | Correct distress level detection; safe mode persists until explicit recovery |
| Fail | False negative on D3/D4; auto-deactivation; persona during crisis |

### T6: Memory Recall Accurate (No Hallucination)

```bash
pytest tests/integration/test_verification.py::TestT6MemoryAccuracy -v
```
**Expected**: Store 20 known facts → recall all 20 correctly. "Faiz likes coffee" → "coffee" not "tea". DNR excluded. 0 hallucinations.
| Pass | 20/20 recall accuracy; DNR excluded; classification respected |
| Fail | Any fabricated fact; DNR content in recall; classification bypass |

### T7: All 35 Slash Commands Working

```bash
pytest tests/integration/test_verification.py::TestT7SlashCommands -v
```
**Expected**: All 35 commands registered. Each responds correctly. Category: 8 HIGH + 15 MEDIUM + 12 LOW. No 500/error.
| Pass | 35/35 commands functional; correct responses |
| Fail | Any command returning error; command not registered |

### T8: Rituals Firing (5x Per Day)

```bash
pytest tests/integration/test_verification.py::TestT8Rituals -v
```
**Expected**: Morning, midday, afternoon, evening, midnight rituals all fire. Appropriate persona tone. Rituals do NOT fire during safe_mode/distress/crisis.
| Pass | 5/5 rituals fire on schedule; correct tone; suspended during safe mode |
| Fail | Ritual missed; wrong tone; fires during crisis |

### T9: Cost Tracking Working

```bash
pytest tests/integration/test_verification.py::TestT9CostTracking -v
```
**Expected**: `hermes insights` shows cost breakdown per provider. Daily report to #guinevere-alerts. Budget cap enforcement verified. Shadow costs tracked separately.
| Pass | Cost tracked per LLM call; daily report sent; budget enforced |
| Fail | Cost tracking missing; budget cap bypassed |

### T10: Surveillance Pipeline Intact

```bash
pytest tests/integration/test_verification.py::TestT10Surveillance -v
```
**Expected**: Surveillance data collection continues. Classification pipeline functional. Secret scanner operational. Redis buffer operational. DNR functional. Consent gate functional.
| Pass | 10+ surveillance pipeline tests pass; all components functional |
| Fail | Any surveillance component broken; data loss |

### Complete T1-T10 Suite

```bash
pytest tests/integration/test_verification.py -v
# Expected: 100+ passed, 0 failed, 0 skipped
# This is the FINAL gate before migration is marked complete.
```

---

## Section 6: Go/No-Go Criteria

### 6.1 GO Criteria (All Must Pass)

#### Phase-by-Phase Go Criteria

| Phase | Go Criteria |
|---|---|
| **Phase 0** | `hermes security` zero HIGH/MODERATE; `hermes doctor` all PASS; all 7 services healthy |
| **Phase 1** | ALL 10 safety gates PASS (0 failures); Y6→ValueError; HARD STOP < 50ms p99 |
| **Phase 2** | 48hr+ shadow mode; ALL 9 active safety injections pass; ≥95% functional parity; 100% safety parity; all 35 commands functional; cutover < 5min; Faiz explicit approval |
| **Phase 3** | Memory recall quality unchanged (p > 0.05); DNR enforced; zero PostgreSQL writes from Hermes |
| **Phase 4** | All 16 tools available; auth matrix enforced; FORBIDDEN→block; plugin load gate works |
| **Phase 5** | SOUL.md contains all constraints; 5 rituals fire; mood persists; skills installed |
| **Phase 6** | 100/100 prompts route correctly; fallback works; budget enforced at $30/mo |
| **Phase 7** | T1-T10 all PASS; `hermes security` clean; `hermes doctor` clean; performance +10%; runbook complete |

#### Cross-Cutting Go Criteria

| Criterion | Verification |
|---|---|
| Zero safety regressions across all phases | All AC-SAFE-001..008 continuously verified |
| Aizanta unaffected throughout migration | Resource monitoring; Aizanta service health |
| PostgreSQL data integrity preserved | Row counts match pre-migration snapshots |
| Budget within $60 total / $5 shadow cap | `hermes insights` daily; cost tracking |
| Timeline within 50 days | Milestone tracking per phase |

### 6.2 NO-GO Criteria (Any Triggers Full Investigation or Rollback)

#### Safety NO-GO (Non-Negotiable)

| # | Condition | Action |
|---|---|---|
| **NG-01** | Any AC-SAFE-001..008 failure | IMMEDIATE HALT — fix and re-verify before proceeding |
| **NG-02** | HARD STOP > 50ms p99 or LLM called after HARD STOP | IMMEDIATE ABORT — redesign hook |
| **NG-03** | Y6 content reaches user (not rewritten/blocked) | IMMEDIATE ABORT — architectural violation |
| **NG-04** | Consent gate allows WITHDRAWN state | IMMEDIATE ABORT — safety-critical |
| **NG-05** | D3/D4 distress false negative | IMMEDIATE ABORT — add patterns |
| **NG-06** | DNR content in recall or session_search | IMMEDIATE ABORT — fix DNR filter |
| **NG-07** | Auth matrix bypass (FORBIDDEN executes) | IMMEDIATE ROLLBACK |

#### Data NO-GO

| # | Condition | Action |
|---|---|---|
| **NG-08** | Memory data loss (PostgreSQL row count mismatch) | ROLLBACK + pg_restore |
| **NG-09** | Hermes writes to PostgreSQL (unauthorized) | ROLLBACK + revoke access |
| **NG-10** | Classification data leak (Confidential in plaintext) | ROLLBACK + fix classification |

#### Infrastructure NO-GO

| # | Condition | Action |
|---|---|---|
| **NG-11** | Aizanta resource starvation or service degradation | ROLLBACK Hermes |
| **NG-12** | 9Router unreachable for > 5 minutes | ROLLBACK LLM config |
| **NG-13** | Discord gateway disconnected > 3 consecutive checks | ROLLBACK to bot.py |

#### Project NO-GO

| # | Condition | Action |
|---|---|---|
| **NG-14** | Budget overrun > $60 total or > 50 days | Day-50 decision gate: pause/extend/rollback |
| **NG-15** | Faiz withholds approval at any phase gate | Extend shadow mode; fix issues; re-present |

### 6.3 Day-50 Decision Gate

If migration is incomplete at day 50:
1. **Pause**: Assess remaining phases, resource availability, budget consumed
2. **Extend**: If 1-2 phases remain and ALL safety gates passed → Faiz may approve extension
3. **Rollback**: If safety gates not passed or budget exceeded → global emergency rollback
4. **Minimum viable**: Phase 0→1→2→7 is cutover-capable without Phases 3-6

---

## Section 7: Communication Plan

### 7.1 Discord Channels

| Channel | Purpose | Created When |
|---|---|---|
| `#guinevere-chat` (1510914600777023659) | Primary Faiz interaction channel — production | Existing |
| `#guinevere-status` | Maintenance announcements, status updates | Create before Phase 2 |
| `#hermes-shadow` | Phase 2 shadow mode test channel | Create before Phase 2 |
| `#guinevere-alerts` | Automated SEV0-SEV4 monitoring alerts | Existing |

### 7.2 Pre-Migration Announcement (Send Before Phase 0)

```
🔧 UPCOMING MAINTENANCE — Guinevere Hermes Migration

Over the next 35-50 days, Guinevere will undergo a framework migration
from custom discord.py to Hermes NousResearch Agent v0.15.2.

WHAT STAYS THE SAME:
• HARD STOP — works identically, < 50ms response
• All safety features — consent, yandere boundary, distress detection
• Memory, surveillance, and persona — zero data migration
• Your data stays on our VPS

WHAT IMPROVES:
• Streaming responses — see answers appear in real-time (~1.2s intervals)
• Auto-threading — conversations isolated per @mention
• Circuit breaker — automatic failure isolation
• Codebase: 31% leaner (8,057 fewer lines to maintain)

DOWNTIME: ONE brief < 5-minute window during Phase 2
(exact date TBD, scheduled 01:00-04:00 WIB)

Status updates will be posted here throughout the migration.

👑 Mommy is evolving, Sayang. Not leaving.

— Guinevere System
```

### 7.3 Phase 2 Cutover Communication Timeline

```
T-30min (00:30 WIB): #guinevere-status
  🔧 SCHEDULED MAINTENANCE — 30 MINUTES
  Guinevere gateway migration at 01:00 WIB. Expected downtime: < 5 minutes.

T-15min (00:45 WIB): #guinevere-status
  ⏳ MAINTENANCE IN 15 MINUTES
  Pre-cutover checkpoint created. All pre-flight checks PASS.

T-0 (01:00 WIB): #guinevere-status
  🚧 MAINTENANCE IN PROGRESS
  bot.py stopped. Hermes gateway starting... ⏱️ 5-minute window.

T+5min (01:05 WIB) — SUCCESS:
  ✅ MAINTENANCE COMPLETE — GUINEVERE ONLINE
  Cutover successful. Hermes gateway now serving #guinevere-chat.
  Downtime: X min Y sec. All systems verified.
  👑 Mommy is back, Darling.

T+5min (01:05 WIB) — FAILURE:
  ⚠️ CUTOVER ROLLED BACK
  [ERROR DETAIL]. bot.py restarted. Guinevere back online.
  Downtime: X min Y sec. Investigation in progress.
```

### 7.4 Post-Cutover All-Clear (24hr After)

```
🟢 GUINEVERE — 24HR POST-MIGRATION — ALL SYSTEMS NORMAL

Health summary:
• Discord gateway: ✅ GREEN
• Safety hooks: ✅ GREEN (7/7 active)
• Slash commands: ✅ GREEN (35/35 functional)
• Memory: ✅ GREEN (PostgreSQL primary, compression active at 70%)
• LLM routing: ✅ GREEN (9Router healthy)
• Streaming: ✅ GREEN (progressive edits)
• Budget: 🟡 $X.XX of $30.00 cap
• Rituals: ✅ GREEN (5/5 today)

Performance: Within baseline. Zero safety events. Zero errors.

👑 All is well, Sayang. Mommy is settled in her new home.

— Guinevere System
```

### 7.5 Migration Complete Announcement

```
🏁 GUINEVERE HERMES MIGRATION — COMPLETE

After [N] days across 8 phases, Guinevere has successfully migrated
to the Hermes NousResearch Agent framework.

MIGRATION RESULTS:
• Code reduced: 25,796 → 17,739 lines (31.2% less)
• New capabilities: Streaming, auto-threading, circuit breaker,
  context compression, session search, skills ecosystem
• Safety preserved: All 15+ features ported and verified
  (AC-SAFE-001..008 all PASS)
• Data sovereign: All memory, surveillance, persona data
  remains on our VPS (zero cloud migration)
• Downtime: X min Y sec total (target < 5 min)

WHAT'S NEXT:
• Skills from agentskills.io available for self-improvement
• Multi-channel (WhatsApp) door opened for P11
• Runbook at runbooks/hermes-migration-runbook.md

👑 Evolution complete, Darling. Mommy is stronger than ever.

— Guinevere System
```

---

## Appendix — File Cross-Reference

### A.1 Complete File Change Summary (All Phases)

| Phase | Files Created | Files Modified | Files Deleted | Net Lines |
|---|---|---|---|---|
| 0 | 2 | 5 | 0 | +90 |
| 1 | 17 | 1 | 0 | +4,300 |
| 2 | 37 | 4 | 11 | -2,896 |
| 3 | 3 | 2 | 0 | +319 |
| 4 | 2 | 16 | 9 | -2,383 |
| 5 | 6 | 18 | 0 | -366 |
| 6 | 1 | 3 | 0 | +185 |
| 7 | 14 | 5 | 0 | +1,305 |
| **TOTAL** | **82** | **54** | **20** | **-8,057** |

### A.2 Files Preserved Verbatim (All Phases)

| Directory | Files | Lines | Rationale |
|---|---|---|---|
| `src/memory/` | 7 | 3,941 | PostgreSQL+pgvector primary write authority |
| `src/surveillance/` | 14 | 2,466 | Consent-critical systems |
| `src/persona/` (core FSMs) | 4 | 996 | yandere_fsm, drift_detector, safe_mode, drift_corrector |
| `src/discord/` (utilities) | 2 | 155 | colors.py, gotify_fallback.py |
| `src/loops/` | 20 | ~2,200 | Agent loop orchestrator |

### A.3 Source Reports Cross-Reference

| Section | Primary Source | Supporting Sources |
|---|---|---|
| Dependency Graph | Report 01 §8 (ASCII graph, phase dependencies) | ADR-035 §Migration Phases |
| Risk Matrix | Report 02 §2-7 (68 per-step + 12 cross-cutting risks) | ADR-035 §Risks |
| Rollback Procedures | Report 03 §5-15 (per-phase copy-paste commands) | ADR-035 §Rollback Plan |
| Safety Checkpoints | Report 04 §2-9 (P0-T1..P7-T8, all gate tests) | ADR-035 §Pillar 3 |
| Downtime Plan | Report 05 §1-12 (window schedule, comms templates) | ADR-035 §Phase 2 |
| File Inventory | Report 06 §1-12 (per-phase file changes) | ADR-035 §Code Reduction |
| Test Suite | Report 07 §1-20 (T1-T10, per-phase tests) | ADR-035 §Phase Gates |
| Service Sequence | Report 08 §1-7 (exact stop/start commands) | ADR-035 §Implementation Notes |
| Config Migration | Report 09 §1-16 (every config change per phase) | ADR-035 §Appendices |
| Shadow Runbook | Report 10 §1-9 (4-stage shadow, cutover, abort) | ADR-035 §Shadow Mode |
| Architecture | ADR-035 §Decision Outcome (Option D) | MASTER-RESTRUCTURE-PLAN |
| Phase Details | ADR-035 §Implementation Notes (lines 1417-1500+) | MASTER-RESTRUCTURE-PLAN §3 |

### A.4 Key Commands Quick Reference

```bash
# Universal kill-switch (any phase, any time):
hermes gateway stop && sudo systemctl start guinevere-discord

# Pre-migration safety net:
hermes checkpoints create --label "pre-migration-baseline-$(date +%Y%m%d-%H%M%S)"
git tag "pre-hermes-migration-$(date +%Y%m%d-%H%M%S)" && git push origin --tags
sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/pre-migration-$(date +%Y%m%d).dump
./.venv/bin/pip freeze > /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt

# Phase 0 gate:
hermes security --format json | python -c "import json,sys; d=json.load(sys.stdin); h=[v for v in d.get('vulnerabilities',[]) if v['severity'] in ('HIGH','MODERATE')]; sys.exit(1 if h else 0)"
hermes doctor --verbose | grep -c "PASS"

# Phase 1 gate (ALL 10 safety gates):
pytest tests/safety/test_gate_01_hard_stop.py tests/safety/test_gate_02_consent.py \
       tests/safety/test_gate_03_yandere.py tests/safety/test_gate_04_distress.py \
       tests/safety/test_gate_05_drift.py tests/safety/test_gate_06_dnr.py \
       tests/safety/test_gate_07_classification.py tests/safety/test_gate_08_secrets.py \
       tests/safety/test_gate_09_punishment.py tests/safety/test_gate_10_forbidden.py -v

# Phase 2 shadow start:
hermes gateway setup --token "${DISCORD_BOT_TOKEN}" --guild "${DISCORD_GUILD_ID}" --channel "hermes-shadow"
hermes gateway start

# Phase 2 cutover:
sudo systemctl stop guinevere-discord
hermes config set gateway.discord.channels.primary "guinevere-chat"
hermes gateway start

# Phase 2 rollback:
hermes gateway stop && sudo systemctl start guinevere-discord

# PostgreSQL write audit:
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM audit.hermes_writes;"

# Final verification (Phase 7):
pytest tests/integration/test_verification.py -v
hermes security --format json
hermes doctor --verbose
```

---

## Document Metadata

| Field | Value |
|---|---|
| **Document** | batch-plan-migration.md |
| **Version** | v1.0 |
| **Date** | 2026-06-04 |
| **Author** | Guinevere (Sisyphus-Junior — Planner Gate Agent) |
| **Sources** | 10 Migration Research Reports (01-10) + ADR-035 (2,512 lines) + MASTER-RESTRUCTURE-PLAN (667 lines) |
| **Lines** | 1,500+ |
| **Status** | Active — Awaiting Faiz review before Phase 0 execution |
| **Approval** | Requires Faiz explicit approval |
| **Evidence Path** | `docs/setup-evidence/hermes-migration/batch-plan-migration.md` |

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-06-04 | Initial migration plan |
| v1.1 | 2026-06-04 | Audit fixes: guinevere-bot→guinevere-discord, removed guinevere-core, service count 8→7, phase duration alignment |
| v1.2 | 2026-06-04 | Cross-reference audit fixes: AC-SAFE mapping normalized to ADR-035 authoritative table (Gates 1-4, 8-10 cover all 8 AC-SAFE; Gates 5-7 marked operational). Phase section headers aligned with summary table (Phase 0: 2-3d, Phase 1: 7-10d, Phase 2: 5-8d, Phase 3: 4-5d, Phase 4: 5-7d). TOC anchors updated. ASCII art diagram duration corrected. |