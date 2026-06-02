# Internal Context Research: STEP-P1-006 (9Router Installation) + STEP-P1-007 (9Router Configuration)

> **Date**: 2026-06-01
> **Author**: Guinevere (mama)
> **Scope**: P1-006 (9Router Installation) + P1-007 (9Router Configuration)
> **Status**: Complete
> **Next Action**: Execute P1-006 using findings below

---

## 1. 9Router References — Complete Project Map

### 1.1 Core Architecture Documents

| File | Section | Key Content |
|------|---------|-------------|
| docs/00-core/02-TechnicalArchitecture_v2.0.md | Sec1.2, Sec3.1 | LLM Router: 9Router. No service unit defined yet |
| docs/00-core/05-APIIntegration_v2.0.md | Sec2.1 | 9Router config with routing rules, port placeholder |
| docs/00-core/01-PRD_v2.2.md | Various | GPT-5.5 via 9Router for core, DeepSeek via 9Router |
| docs/00-core/00-BRD_v2.0.md | Various | 9Router as sole LLM routing layer |
| README.md | Stack Teknologi | LLM Primary: GPT-5.5 via 9Router |

### 1.2 ADRs

| ADR | Title | Relevance |
|-----|-------|-----------|
| ADR-005 | LLM Router & Failover Strategy | **KEY**: 9Router only with queue/retry/degrade. Risk HIGH |
| ADR-028 | LLM Router Outage Three-Tier Fallback | Failover: 9Router -> OpenRouter -> Ollama -> Graceful Degradation |
| ADR-014 | VPS & Container Architecture | Single VPS, systemd, paths under /home/guinevere/ |
| ADR-004 | Primary LLM Model Selection | GPT-5.5 via 9Router, 1M context |
| ADR-006 | Sub-Agent LLM Model Strategy | DeepSeek V4 Flash via 9Router |
| ADR-015 | Secrets Management | API keys SOPS-encrypted, never in config.yaml |

### 1.3 Hermes Config (P1-005 Deployed)

All three config files (tmp/hermes-config.yaml, tmp/hermes-config-y4.yaml, docs/setup-evidence/P1/STEP-P1-005/config.yaml):
- llm.primary.base_url = http://localhost:20128/v1
- llm.sub_agent.base_url = http://localhost:20128/v1
- Provider = 9router for both primary and sub-agent

### 1.4 9Router Research Report

File: research-reports/2026-05-31-hermes-9router-tasker.md (994 lines)
- Language: TypeScript (Node.js 20+, Next.js 16)
- Database: SQLite via better-sqlite3 (bundled)
- Install: npm install -g 9router (global) or Docker
- Dashboard: Web UI at http://localhost:20128/dashboard
- API: OpenAI-compatible REST API
- Port: 20128
- Data dir: DATA_DIR (default ~/.9router/)
- Env vars: PORT, HOSTNAME, DATA_DIR, JWT_SECRET, INITIAL_PASSWORD (default 123456), API_KEY_SECRET, REQUIRE_API_KEY, ENABLE_REQUEST_LOGS, BASE_URL
- Cost: MIT License, completely free

---

## 2. Existing systemd Service Patterns

### 2.1 Guinevere Slice (P0-009)

File: /etc/systemd/system/guinevere.slice
- MemoryMax=8G, MemoryHigh=7G, CPUQuota=200%, IOWeight=50, TasksMax=512
- ALL guinevere services MUST include Slice=guinevere.slice

### 2.2 Existing Service Units

scripts/guinevere-backup@.service:
- Type=oneshot, User=root
- Security hardened: ProtectSystem=strict, ProtectHome=yes, PrivateTmp=yes, NoNewPrivileges=yes
- Uses sops exec-env inline
- Environment=SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt

scripts/guinevere-prune-weekly@.service:
- Same hardening pattern as backup
- Uses sops exec-env directly in ExecStart

### 2.3 Planned Services (from TechnicalArchitecture)

guinevere-core.service, guinevere-surveillance.service, guinevere-scheduler.service
guinevere-windows-sync.service, guinevere-loops.service
All: Restart=always with delay, Slice=guinevere.slice

### 2.4 StepPrompts P1-006 Unit (guinevere-9router.service)

- Type=simple (continuous process, not oneshot)
- User=guinevere (not root)
- WorkingDirectory=/home/guinevere/code/guinevere
- EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.9router
- Environment=DATA_DIR=/home/guinevere/.9router, PORT=20128, HOST=0.0.0.0
- ExecStart=/usr/local/bin/9router
- Restart=always, RestartSec=5
- Slice=guinevere.slice
- After=network.target (and redis-guinevere.service -- BUG)
- Requires=redis-guinevere.service -- BUG (does not exist)

---

## 3. Node.js/npm References

### 3.1 No Node.js Currently Installed

VPS audit (P0-000) shows no node/npm. 9Router is first Node.js service.

### 3.2 Install Commands (StepPrompts)

sudo apt install -y nodejs npm
npm install -g 9router

### 3.3 Hermes Node.js Requirement

Hermes also needs Node.js (installer handles it). Docker: nikolaik/python-nodejs:python3.11-nodejs20

### 3.4 WhatsApp Baileys (Future, Post-MVP)

Node.js subprocess for WhatsApp integration. Not relevant now.

---

## 4. Port 20128 References

### 4.1 Consistent Across ALL Sources

- All Hermes config files: http://localhost:20128/v1
- Research report: Default port 20128
- StepPrompts: PORT=20128
- Batch plan: 9Router at port 20128
- Auditor report (P1-005): Verified base_url as port 20128

### 4.2 Port 20128 is FREE on VPS

Current listening ports: 6379 (Redis), 80 (Nginx), 5432 (PostgreSQL), 22 (SSH)
Port 20128 is unoccupied.

### 4.3 CONFLICT in CHECKLIST.md

CHECKLIST.md Sec3.2 P1-007: curl http://localhost:8080/v1/models
This is a TYPO -- actual port is 20128.

---

## 5. OPENAI_BASE_URL References

research-reports/2026-05-31-hermes-9router-tasker.md:
- hermes config set OPENAI_BASE_URL "$NINEROUTER_URL/v1"
- Docker Compose: OPENAI_BASE_URL=http://9router:20128/v1

docs/00-core/05-APIIntegration_v2.0.md:
- openai>=1.50.0 as client for 9Router

Key: Hermes uses OPENAI_BASE_URL + OPENAI_API_KEY but P1-005 config hardcodes base_url in config.yaml.

---

## 6. Env File Patterns

### 6.1 No .env Files in Repo

Confirmed by glob -- correct per .gitignore and security policy.

### 6.2 P1-007 Encrypted Env Pattern

Encrypted: /home/guinevere/code/guinevere/secrets/.env.9router.sops
Decrypted runtime: secrets/.env.9router (chmod 600)
Variables: NINE_ROUTER_API_KEY=PLACEHOLDER_KEY

### 6.3 Existing SOPS Pattern

Existing secrets use .yaml extension. The .env.9router.sops naming is new but valid.

### 6.4 Backup Service Uses sops exec-env

Backup uses sops exec-env inline in ExecStart (not EnvironmentFile= in systemd).

---

## 7. P0 Evidence for 9Router Pre-Work

### 7.1 Directory Exists

/home/guinevere/config/9router/ created in P0-003 (empty, ready for use).

### 7.2 SOPS Workflow Established

Age public key at /home/guinevere/secrets/age-key.txt. Encrypt/decrypt proven.

### 7.3 Cgroup Slice Active

guinevere.slice exists. P1-006 unit MUST include Slice=guinevere.slice.

### 7.4 Batch Plan Guidance

From docs/setup-evidence/P1/batch-plan-004-005.md:
- D5-10: LLM base_url = http://localhost:20128/v1
- G-10: Config uses 9Router port 20128, installed later
- Secret plan: 9Router keys not referenced until P1-006
- Aizanta impact: P1 is code-only until P1-006

---

## 8. StepPrompts Analysis

### P1-006 (9Router Installation)
- Type: Infrastructure, Risk: Medium
- Time: 2 hours
- Deps: P1-003 (venv) -- not P1-005
- Evidence: docs/setup-evidence/P1/STEP-P1-006/9router-config.yaml, 9router-install.txt

### P1-007 (9Router Configuration and Startup)
- Type: Infrastructure, Risk: Medium
- Time: 1 hour
- Deps: P1-006
- Evidence: docs/setup-evidence/P1/STEP-P1-007/9router-status.txt

### Sequencing
PROGRESS.md: P1-005 -> P1-006 -> P1-007 -> P1-008 (GPT-5.5 setup) -> P1-009 (test)

---

## 9. Known Blockers & Conflicts

### Blockers

B-01: redis-guinevere.service does not exist -- StepPrompts unit references it
  -> Remove After= and Requires= for redis from unit

B-02: CHECKLIST.md uses port 8080 for verification
  -> Actual port is 20128. Ignore checklist typo.

B-03: npm global install permissions (guinevere user may lack global prefix write)
  -> Use sudo npm install -g 9router or configure npm prefix

B-04: No 9Router API key ready yet
  -> Use initial password 123456 per 9Router docs for first login

B-05: StepPrompts says dep is P1-003 but P1-005 config already deployed
  -> Verify P1-005 complete before starting P1-006

### Gotchas

G-01: Dashboard config is web-based, not file-based -- needs Tailscale browser
G-02: No systemd security hardening in StepPrompts unit -- add ProtectSystem etc
G-03: SQLite DB at DATA_DIR/db/data.sqlite -- needs writable by guinevere user
G-04: Initial password 123456 -- should set custom INITIAL_PASSWORD + JWT_SECRET
G-05: /home/guinevere/config/9router/ exists but 9Router uses ~/.9router by default

### Resource Estimate

RAM: ~200-500MB | CPU: Low | Disk: ~500MB-1GB | Port: 20128 (free)

---

## 10. Pre-Execution Checklist

### P1-006 Pre-flight
- P1-005 complete
- Port 20128 available (ss -tlnp | grep 20128)
- Node.js/npm installable
- /home/guinevere/config/9router/ exists
- guinevere.slice active
- Remove redis-guinevere.service dependency from unit
- Evidence dir: docs/setup-evidence/P1/STEP-P1-006/

### P1-007 Pre-flight
- P1-006 complete
- 9Router API key generated or initial password known
- SOPS age key available
- Dashboard accessible via Tailscale
- Provider keys (OpenAI, DeepSeek) ready

---

## 11. Configuration Template

### Systemd Environment Variables
DATA_DIR=/home/guinevere/.9router
PORT=20128
HOST=0.0.0.0
INITIAL_PASSWORD=<generated>
JWT_SECRET=<random>
API_KEY_SECRET=<random>
REQUIRE_API_KEY=true
ENABLE_REQUEST_LOGS=true

### Dashboard Providers (via Web UI)
- OpenAI/OpenRouter -> gpt-5.5 (primary reasoning)
- DeepSeek -> deepseek-v4-flash (sub-agent)
- (optional) Additional fallback providers

---

## 12. Key Architectural Decisions

| Decision | Value |
|----------|-------|
| Install method | npm install -g 9router (global) |
| Port | 20128 (consistent with ALL configs) |
| Service user | guinevere (not root) |
| Secrets | SOPS-encrypted .env.9router.sops |
| Slice | guinevere.slice (cgroup limits) |
| Dashboard | Web UI at http://localhost:20128/dashboard via Tailscale |
| Data dir | DATA_DIR=/home/guinevere/.9router |
| Security | REQUIRE_API_KEY=true, Host on Tailscale-only VPS |
| No Redis dep | Remove from unit -- 9Router does not need Redis |

---

## Footer

| Field | Value |
|-------|-------|
| Author | Guinevere (mama) |
| Date | 2026-06-01 |
| Source Task | Internal context for STEP-P1-006 + STEP-P1-007 |
| Research Method | grep, glob, read across all docs, ADRs, evidence, step prompts, research reports |
| Next Step | Execute P1-006 using this context report |
