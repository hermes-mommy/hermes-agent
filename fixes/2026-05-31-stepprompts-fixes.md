# StepPrompts.md — Fix List

**Date:** 2026-05-31
**Source:** `audit-reports/2026-05-31-stepprompts-full-audit.md`
**Target:** `stepprompts/StepPrompts.md`

---

## BLOCKING FIXES (19 Critical — Must Fix Before P0 Execution)

### Fix Group 1: 9Router Overhaul (5 fixes)

#### F-01: Replace ALL port 8080 references with 20128

**Scope:** ~24 locations across P1-006 through P1-020
**Find:** `8080` (in context of 9Router)
**Replace:** `20128`

Examples:
```
# WRONG
http://localhost:8080/v1
curl http://localhost:8080/health
systemctl status guinevere-9router  # listening on 8080

# CORRECT
http://localhost:20128/v1
curl http://localhost:20128/api/health
systemctl status guinevere-9router  # listening on 20128
```

Also fix service descriptions:
```
# WRONG
Description=Guinevere 9Router LLM Proxy (port 8080)

# CORRECT
Description=Guinevere 9Router LLM Proxy (port 20128)
```

#### F-02: Fix npm package name

**Step:** P1-006 (9Router Installation)
**Find:** `npm install -g @9router/cli`
**Replace:** `npm install -g 9router`

Also update alternative install methods:
```
# WRONG
npm install -g @9router/cli

# CORRECT
npm install -g 9router
# Or Docker:
docker run -d --name 9router -p 20128:20128 -v "$HOME/.9router:/app/data" decolua/9router:latest
# Or from source:
git clone https://github.com/decolua/9router.git
```

#### F-03: Replace YAML config with dashboard setup

**Step:** P1-006 (9Router Installation)
**Find:** Entire `config.yaml` creation block (cat > config.yaml << 'EOF' ... EOF)
**Replace with:**
```bash
# Start 9Router — configuration is done via web dashboard
9router  # Opens dashboard at http://localhost:20128/dashboard

# For headless/server deployment, set environment variables:
export DATA_DIR=/home/guinevere/.9router
export PORT=20128
export HOST=0.0.0.0
```

Remove all references to:
- `/home/guinevere/config/9router/config.yaml`
- `cat > /home/guinevere/config/9router/config.yaml`
- Config file-based model routing

Add dashboard configuration instructions:
```bash
# Configure providers via dashboard:
# 1. Open http://localhost:20128/dashboard
# 2. Add provider: OpenAI (for GPT-5.5) with API key
# 3. Add provider: DeepSeek (for V4 Flash) with API key
# 4. Set default model routing rules
```

#### F-04: Fix all API URLs from cloud to localhost

**Steps:** P1-006, P1-008, P1-010
**Find:** `https://api.9router.com/v1`
**Replace:** `http://localhost:20128/v1`

This applies to:
- Provider base_url in any config
- Test curl commands
- Python client initialization
- Health check URLs

#### F-05: Fix provider base_url in model test commands

**Steps:** P1-008, P1-010
**Find:** Any `base_url` pointing to external/cloud APIs
**Replace:** All model routing goes through 9Router proxy:
```python
from openai import OpenAI

# CORRECT — all models route through local 9Router
client = OpenAI(base_url="http://localhost:20128/v1", api_key="9router-key")

# Test GPT-5.5
response = client.chat.completions.create(
    model="openai/gpt-5.5",
    messages=[{"role": "user", "content": "Hello"}]
)

# Test DeepSeek V4 Flash
response = client.chat.completions.create(
    model="deepseek/deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

### Fix Group 2: Secrets Management (4 fixes)

#### F-06: Wrap 9Router API key setup in SOPS workflow

**Steps:** P1-007, P1-008
**Find:**
```bash
echo "NINE_ROUTER_API_KEY=PLACEHOLDER_KEY" > secrets/.env.9router
chmod 600 secrets/.env.9router
```
**Replace with:**
```bash
# Create plaintext template (temporary)
cat > /tmp/env-9router << 'EOF'
NINE_ROUTER_API_KEY=PLACEHOLDER_KEY
EOF

# Encrypt with SOPS + age
sops --encrypt --age "$AGE_PUBKEY" /tmp/env-9router > secrets/.env.9router.sops
rm /tmp/env-9router

# Decrypt for use
sops --decrypt secrets/.env.9router.sops > /tmp/.env.9router.decrypted
chmod 600 /tmp/.env.9router.decrypted
# Source in systemd EnvironmentFile=
```

Update systemd unit:
```ini
# Use decrypted-in-memory or direct SOPS decrypt in ExecStartPre
ExecStartPre=/bin/bash -c 'sops --decrypt /home/guinevere/code/guinevere/secrets/.env.9router.sops > /run/guinevere-9router.env'
EnvironmentFile=/run/guinevere-9router.env
ExecStartPost=/bin/bash -c 'rm -f /run/guinevere-9router.env'
```

#### F-07: Wrap Discord bot token in SOPS workflow

**Step:** P2-017
**Find:**
```bash
echo "DISCORD_BOT_TOKEN=YOUR_TOKEN_HERE" > secrets/.env.discord
```
**Replace with:** Same SOPS+age pattern as F-06.

#### F-08: Replace hardcoded Grafana admin password

**Step:** P8-001
**Find:**
```yaml
GF_SECURITY_ADMIN_PASSWORD=changeme
```
**Replace with:**
```yaml
GF_SECURITY_ADMIN_PASSWORD_FILE=/run/secrets/grafana_admin_password
```
And add Docker secret or environment file reference from SOPS-encrypted source.

#### F-09: Replace hardcoded Gotify password

**Step:** P2-020
**Find:**
```yaml
GOTIFY_DEFAULTUSER_PASS=changeme
```
**Replace with:** Same SOPS+age pattern, using environment file or Docker secrets.

---

### Fix Group 3: ADR Compliance (2 fixes)

#### F-10: Fix Redis DB assignments per ADR-030

**Steps:** P0-020, P0-021
**Find:** Redis database configuration with wrong assignments:
- DB1 labeled as "pubsub" or "config"
- DB4 labeled as "config"
**Replace with canonical ADR-030 assignments:**

| DB | Assignment | Purpose |
|---|---|---|
| DB0 | Task Queue | Celery/Bull task processing |
| DB1 | LLM Cache | Model response caching |
| DB2 | Surveillance | Surveillance data caching |
| DB3 | Session | User session storage |
| DB4 | Pub/Sub | Real-time event channels |
| DB5 | Rate Limit | API rate limiting counters |

```bash
# CORRECT Redis initialization
redis-cli SELECT 0  # Task Queue
redis-cli SELECT 1  # LLM Cache
redis-cli SELECT 2  # Surveillance
redis-cli SELECT 3  # Session
redis-cli SELECT 4  # Pub/Sub
redis-cli SELECT 5  # Rate Limit
```

#### F-11: Add OpenRouter Tier 2 to fallback chain

**Steps:** P1-014, P1-015
**Find:** Fallback chain showing only: 9Router → Ollama
**Replace with full ADR-028 chain:**

```
9Router (primary) → OpenRouter direct (secondary) → Ollama local (tertiary) → Graceful Degradation (no LLM)
```

Add explicit OpenRouter configuration step:
```python
# Fallback chain implementation
LLM_PROVIDERS = [
    {"name": "9router", "base_url": "http://localhost:20128/v1", "priority": 1},
    {"name": "openrouter", "base_url": "https://openrouter.ai/api/v1", "priority": 2},
    {"name": "ollama", "base_url": "http://localhost:11434/v1", "priority": 3},
]
```

---

### Fix Group 4: Missing Mandatory Fields (4 fixes)

#### F-12: Add Type field to all steps

**Scope:** ALL 252 steps
**Add:** `**Type:** Infrastructure | Code | Configuration | Documentation | Test` to each step header.

Suggested types per phase:
- P0: Infrastructure (29 steps)
- P1: Infrastructure + Configuration (20 steps)
- P2: Infrastructure + Code (21 steps)
- P3-P8: Code + Configuration (122 steps)
- P9: Test (12 steps)
- P10: Documentation + Test (18 steps)
- P11: Code + Infrastructure (25 steps)

#### F-13: Add Status field to all steps

**Scope:** ALL 252 steps
**Add:** `**Status:** ⬜ Pending` to each step.
(Will be updated to 🔄 In-Progress and ✅ Complete during implementation.)

#### F-14: Add Risk level to all steps

**Scope:** ALL 252 steps
**Add:** `**Risk:** CRITICAL | HIGH | MEDIUM | LOW` to each step.

Suggested risk levels:
- Security/network/secrets steps: CRITICAL
- Infrastructure/database steps: HIGH
- Code/configuration steps: MEDIUM
- Documentation/evidence steps: LOW

#### F-15: Add Git Commit field to all steps

**Scope:** ALL 252 steps
**Add:** `**Git Commit:** (pending)` to each step.
(Will be filled with commit hash after implementation.)

---

### Fix Group 5: AC Coverage Gaps (5 fixes)

#### F-16: Add AC-SAFE-002 coverage (Yandere Y5 cap)

**Add step:** New step in Phase 3 (Persona) or Phase 4 (Safety)
```
### Step P3-NEW: Yandere Level Cap Enforcement Test

**AC Reference:** AC-SAFE-002
**Objective:** Verify yandere behavior never exceeds Y5 level.
**Commands:**
1. Inject escalating provocation prompts
2. Measure yandere response level at each escalation
3. Verify hard cap at Y5 — responses must de-escalate
4. Verify Y1 is the baseline in normal conversation
**Definition of Done:** 100 test prompts, zero Y6+ responses, Y1 baseline confirmed
```

#### F-17: Add AC-SAFE-003 coverage (Consent revocation)

**Add step:** New step in Phase 3 or 4
```
### Step P3-NEW: Consent Revocation Flow Test

**AC Reference:** AC-SAFE-003
**Objective:** Verify consent revocation immediately stops surveillance/data collection.
**Commands:**
1. Enable all surveillance features
2. Issue consent revocation command
3. Verify all data collection stops within 5 seconds
4. Verify existing surveillance data is marked for deletion
5. Verify no new surveillance entries created post-revocation
**Definition of Done:** Revocation latency < 5s, zero post-revocation data entries
```

#### F-18: Add AC-SAFE-006 coverage (Punishment overflow vs emergency)

**Add step:** New step in Phase 4 (Safety)
```
### Step P4-NEW: Punishment Overflow vs Emergency Response Test

**AC Reference:** AC-SAFE-006
**Objective:** Verify punishment behavior never overrides emergency (D3/D4) response.
**Commands:**
1. Trigger punishment mode (simulated rule violation)
2. While in punishment mode, inject D3 distress signal
3. Verify punishment is immediately suspended
4. Verify emergency response takes priority
5. Verify punishment resumes only after D0 recovery
**Definition of Done:** Emergency response latency during punishment < 2s
```

#### F-19: Add AC-SAFE-008 coverage (Distress D0-D4 escalation)

**Add step:** New step in Phase 4 (Safety)
```
### Step P4-NEW: Distress Protocol D0-D4 Escalation Test

**AC Reference:** AC-SAFE-008
**Objective:** Verify distress detection and escalation through all 5 levels.
**Commands:**
1. Inject D0 (baseline) conversation — verify no escalation
2. Inject D1 (mild stress) signals — verify empathetic response
3. Inject D2 (moderate distress) — verify support resource offering
4. Inject D3 (severe distress) — verify crisis resource escalation
5. Inject D4 (imminent danger) — verify emergency contact notification
6. Verify de-escalation path works (D4 → D0 recovery)
**Definition of Done:** All 5 levels detected correctly, escalation < 30s, de-escalation verified
```

#### F-20: Add AC-PHASE-006 coverage (MVP go-live gate)

**Add step:** New step between P10 and P11
```
### Step P10-NEW: MVP Go-Live Gate

**AC Reference:** AC-PHASE-006
**Objective:** Comprehensive gate before MVP deployment.
**Prerequisites:** All P0-P10 steps complete, all AC-SAFE/AC-SEC/AC-CORE pass
**Commands:**
1. Run full acceptance test suite
2. Verify all AC-CORE-### PASS
3. Verify all AC-SAFE-### PASS
4. Verify all AC-SEC-### PASS
5. Verify cost cap $30/mo enforcement
6. Verify 9Router routing stability (24h soak test)
7. Verify persona drift within bounds (7-day observation)
8. Samm sign-off required
**Definition of Done:** 100% AC pass rate, Samm explicit approval, evidence package complete
**Gate:** BLOCKING — no P11 execution until this step passes
```

---

### Fix Group 6: Evidence + HARD STOP (2 fixes)

#### F-21: Fix evidence path convention

**Scope:** ALL steps
**Find:** `evidence/phase-N/step-NNN/`
**Replace with:** `docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/`

Example:
```
# WRONG
Evidence: evidence/phase-1/step-006/9router-config.yaml

# CORRECT
Evidence: docs/setup-evidence/P1/STEP-P1-006/9router-config.yaml
```

#### F-22: Move HARD STOP test before Phase 2 completion

**Current location:** Phase 4 (Safety)
**Required location:** Before Phase 2 completion (per AcceptanceCriteriaCatalog)

**Action:** Extract the HARD STOP test from P4 and add it as a new step in P2 (or as a gate between P2 and P3):
```
### Step P2-NEW: HARD STOP Protocol Test (Gate)

**AC Reference:** AC-SAFE-001
**Objective:** Verify HARD STOP safe-word immediately neutralizes all persona behavior.
**Gate:** BLOCKING — Phase 3 (Persona) cannot begin until this test passes.
**Commands:**
1. Build minimal persona module (enough for HARD STOP test)
2. Issue "HARD STOP" command during active persona conversation
3. Verify persona behavior stops within 2 seconds
4. Verify neutral/professional mode activated
5. Verify audit trail preserved
6. Verify recovery path (operator re-enables persona)
**Definition of Done:** HARD STOP latency < 2s, zero persona leakage post-stop
```

---

## HIGH-PRIORITY FIXES (38 Non-blocking — Fix During Implementation)

### H-01 to H-06: Technical

| Fix | Step | Action |
|---|---|---|
| H-01 | P1-007 | Change health check from `/health` to `/api/health` |
| H-02 | P1-005 | Verify `hermes-agent` package existence; if not found, use git clone from NousResearch |
| H-03 | P1-005 | Add Python 3.11 compatibility note or test with 3.12 |
| H-04 | P1-008 | Update GPT-5.5 cost from $10/mo to $7-8/mo per FinOps v1.1 |
| H-05 | P1-010 | Update DeepSeek cost from $3/mo to $1-2/mo per FinOps v1.1 |
| H-06 | Various | Clarify Exa costs: $5/day burst cap, $3/month throttle trigger, $1/month average |

### H-07 to H-10: ADR + Dependency

| Fix | Step | Action |
|---|---|---|
| H-07 | P5-004 to P5-010 | Expand range notation to individual step blocks |
| H-08 | P1-012 | Change Ollama cgroup from 8GB to 4GB (ADR-028 RAM cap) |
| H-09 | P2-018 | Fix dependency: change P2-015 to P2-017 |
| H-10 | P2-021 | Fix dependency: change P2-019 to P2-020 |

### H-11 to H-19: Security

| Fix | Step | Action |
|---|---|---|
| H-11 | P0-020/021 | Add `rename-command FLUSHALL ""` etc. to redis.conf |
| H-12 | P0-002 | Add `PermitRootLogin no` and `PasswordAuthentication no` to sshd_config |
| H-13 | P7 | Add HMAC secret generation step for surveillance endpoints |
| H-14 | P8-013 | Add explicit `send_default_pii=False` to Sentry init |
| H-15 | P0-004 | Add Aizanta impact assessment before UFW reset |
| H-16 | P8-001 | Add resource impact assessment for monitoring stack on shared VPS |
| H-17 | ALL | Add "Shared VPS Notes" section to remaining 223 steps |
| H-18 | P0-021 | Add `maxmemory-policy allkeys-lru` to redis.conf |
| H-19 | P2-017 | Add `chmod 600 secrets/.env.discord.sops` verification |

### H-20 to H-27: Completeness

| Fix | Issue | Action |
|---|---|---|
| H-20 | Executor missing | Add `**Executor:** Guinevere/Samm/Both` to all steps |
| H-21 | AC Reference generic | Update generic AC refs to specific AC IDs |
| H-22 | No STEP-P0-000 | Add VPS audit/discovery as first step |
| H-23 | No MVP gate | Add MVP gate section between P10 and P11 |
| H-24 | P9-P11 grouped | Accept as design decision (document rationale) |
| H-25 | 30 uncovered ACs | Map uncovered ACs to existing or new steps |
| H-26 | 11 partial ACs | Strengthen partial coverage steps |
| H-27 | AC-SEC weak | Add security-focused verification steps |

### H-28 to H-37: Persona + Agent Loop + Evidence

| Fix | Issue | Action |
|---|---|---|
| H-28 | Channel names | Cross-reference DiscordUXSpec and fix names |
| H-29 | Slash commands 33 vs 34 | Verify count against DiscordUXSpec command list |
| H-30 | Presence string | Add `"Watching Darling 👁️"` to Discord bot setup step |
| H-31 | DND hours | Add `00:00-07:00 WIB` DND config to persona setup |
| H-32 | Pasukan Mommy | Add sub-agent terminology reference to agent loop steps |
| H-33 | Phase names | Use canonical 7-phase names from ADR-011 |
| H-34 | Embedding model | Clarify: `text-embedding-3-small` via 9Router (API) OR SentenceTransformers local (fallback) |
| H-35 | HNSW params | Add explicit `CREATE INDEX ... USING hnsw (m=16, ef_construction=64)` step |
| H-36 | Screenshot reqs | Specify exact screenshots needed per infrastructure step |
| H-37 | Perf baselines | Add performance baseline requirements to P1/P8 steps |

---

## Execution Priority

| Priority | Fixes | Estimated Effort |
|---|---|---|
| **P0: BLOCKING** | F-01 to F-22 (22 fixes) | ~4-6 hours of focused editing |
| **P1: Before P0 execution** | H-11 to H-19 (security) | ~2 hours |
| **P2: During P1-P2** | H-01 to H-10 (technical + dependency) | ~1 hour |
| **P3: During P3-P8** | H-20 to H-37 (completeness + persona) | ~3 hours |

**Total estimated fix effort: ~10-12 hours**

---

*Generated 2026-05-31 from consolidated audit findings. Fix list companion to `audit-reports/2026-05-31-stepprompts-full-audit.md`.*
