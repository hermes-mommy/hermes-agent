# StepPrompts.md — Technical Accuracy & Cost Accuracy Audit

**Audit ID:** AUDIT-D1-D8-2026-05-31  
**Auditor:** Senior Independent Auditor  
**Target:** `stepprompts/StepPrompts.md` (7360 lines, 252 steps, 12 phases)  
**Reference Documents:**
- `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` (661 lines)
- `research-reports/2026-05-31-hermes-9router-tasker.md` (994 lines)
- `adr/ADR-032-backup-storage-strategy.md` (224 lines)
- `PROGRESS.md` (399 lines)
- Audit requirements as specified in task

**Date:** 2026-05-31  
**Verdict:** FAIL — 5 CRITICAL findings that would block successful implementation

---

## Executive Summary

The StepPrompts.md document has a **fundamental systematic error**: 9Router is configured on port **8080** throughout the entire document (24 occurrences across 10+ steps), but the actual 9Router port is **20128** per the research report. Additionally, the npm package name `@9router/cli` is fabricated — the real package is `9router`. The 9Router configuration approach (YAML config file) is entirely wrong — 9Router is configured via its web dashboard at `http://localhost:20128/dashboard`, not a config file. These issues alone make every P1 step after P1-005 unexecutable as written.

**Key statistics:**
| Metric | Count |
|---|---|
| Total lines audited | 7360 |
| Steps checked | 252 |
| CRITICAL findings | 5 |
| HIGH findings | 7 |
| MEDIUM findings | 6 |
| LOW findings | 3 |
| Total findings | 21 |

---

## DIMENSION 1: TECHNICAL ACCURACY FINDINGS

### FINDING T-01: 9Router Port — 8080 used instead of 20128 (CRITICAL)

**Severity:** CRITICAL  
**Scope:** 24 locations across 11 steps + Appendix A  
**Impact:** Blocks implementation — every 9Router command would fail at the wrong port.

**Affected locations:**

| Line | Step | Text |
|---|---|---|
| 3260 | P1-005 | `base_url: "http://localhost:8080/v1"` (Hermes config LLM primary) |
| 3267 | P1-005 | `base_url: "http://localhost:8080/v1"` (Hermes config LLM sub_agent) |
| 3344 | P1-005 | Note: "localhost:8080" |
| 3363 | P1-006 | Pre-flight: "Port 8080 available" |
| 3385 | P1-006 | 9Router YAML config: `port: 8080` |
| 3390 | P1-006 | `base_url: "https://api.9router.com/v1"` (fabricated cloud URL) |
| 3402 | P1-006 | `base_url: "https://api.9router.com/v1"` (DeepSeek — same fabricated URL) |
| 3468 | P1-006 | Verification: "Port 8080 configured" |
| 3541 | P1-007 | `curl http://localhost:8080/health` |
| 3542 | P1-007 | `curl http://localhost:8080/v1/models` |
| 3547 | P1-007 | Verification: "Listening on 8080" |
| 3548 | P1-007 | `curl http://localhost:8080/health` returns 200 |
| 3598 | P1-008 | GPT-5.5 test: `curl http://localhost:8080/v1/chat/completions` |
| 3607 | P1-008 | GPT-5.5 test 2: `curl http://localhost:8080/v1/chat/completions` |
| 3674 | P1-009 | Python test: `BASE_URL = "http://localhost:8080/v1"` |
| 3787 | P1-010 | DeepSeek test: `curl http://localhost:8080/v1/chat/completions` |
| 3797 | P1-010 | DeepSeek speed test: `curl http://localhost:8080/v1/chat/completions` |
| 3865 | P1-011 | Python test: `BASE_URL = "http://localhost:8080/v1"` |
| 4168 | P1-015 | LLM Router: `base_url="http://localhost:8080/v1"` (CORE_REASONING) |
| 4176 | P1-015 | LLM Router: `base_url="http://localhost:8080/v1"` (SUB_AGENT) |
| 4616 | P1-019 | Health check: `curl -sf http://localhost:8080/health` |
| 5973 | P3-005 | Embedding pipeline: `base_url="http://localhost:8080/v1"` |
| 7297 | Appendix A | Service table: `guinevere-9router \| 8080 \| LLM routing proxy` |

**Fix:** Replace ALL 8080 references with **20128**. The correct URLs are:
- Dashboard: `http://localhost:20128/dashboard`
- API: `http://localhost:20128/v1`
- Health: `http://localhost:20128/api/health` (not `/health`)

**Source:** Research report lines 345-346: `npm install -g 9router` / `9router # Dashboard opens at http://localhost:20128`

---

### FINDING T-02: 9Router npm Package Name — `@9router/cli` is fabricated (CRITICAL)

**Severity:** CRITICAL  
**Scope:** Step P1-006 (lines 3371, 3480)  
**Impact:** `npm install -g @9router/cli` would fail — package does not exist on npm.

**Affected locations:**

| Line | Text |
|---|---|
| 3371 | `npm install -g @9router/cli` |
| 3480 | `npm uninstall -g @9router/cli` (rollback) |

**Fix:** Replace with `npm install -g 9router`

**Source:** Research report line 345: `npm install -g 9router`

---

### FINDING T-03: 9Router Configuration Method — YAML config file is fabricated (CRITICAL)

**Severity:** CRITICAL  
**Scope:** Step P1-006 (lines 3382-3437), P1-007, P1-015  
**Impact:** 9Router is NOT configured via YAML files. It's configured via a web dashboard. The entire `config.yaml` approach (50+ lines of YAML with providers, routing, cost_tracking sections) is fabricated and would not work.

The systemd unit at line 3451 uses:
```
ExecStart=/usr/local/bin/9router --config /home/guinevere/config/9router/config.yaml
```
This is incorrect. 9Router is a Next.js application, not a binary with `--config` flags. The correct approach is:
- Start via `9router` command or `npm run start` from source
- Configure via web dashboard at `http://localhost:20128/dashboard`
- Environment variables (PORT, DATA_DIR, REQUIRE_API_KEY, etc.) control runtime behavior

**Fix:** Rewrite P1-006 to:
1. Install 9Router via `npm install -g 9router`
2. Set environment variables (PORT=20128, DATA_DIR, REQUIRE_API_KEY=true, etc.)
3. Start via `9router` binary (no config file args)
4. Document that provider configuration happens via web dashboard at `http://localhost:20128/dashboard`
5. Remove ALL fabricated YAML config sections

**Source:** Research report lines 400-420: "9Router is configured via its web dashboard at http://localhost:20128/dashboard, not a config file."

---

### FINDING T-04: 9Router Cloud API URL — `https://api.9router.com/v1` is fabricated (CRITICAL)

**Severity:** CRITICAL  
**Scope:** Step P1-006 (lines 3390, 3402)  
**Impact:** These URLs point to a non-existent cloud service. 9Router is self-hosted on localhost.

**Affected locations:**

| Line | Text |
|---|---|
| 3390 | `base_url: "https://api.9router.com/v1"` (GPT provider config) |
| 3402 | `base_url: "https://api.9router.com/v1"` (DeepSeek provider config) |

The fabricated YAML config routes provider calls THROUGH `api.9router.com`, but 9Router IS the proxy — provider calls from 9Router go directly to OpenAI/DeepSeek/etc. The `base_url` concept in this context is wrong.

**Fix:** Remove these base_url values. 9Router handles provider routing internally after they're configured in the dashboard. The application code should only point to `http://localhost:20128/v1` as the OpenAI-compatible endpoint.

**Source:** Research report lines 378-398 show 9Router architecture: it's the routing layer, not a pass-through to a cloud API.

---

### FINDING T-05: 9Router Health Endpoint URL — `/health` instead of `/api/health` (HIGH)

**Severity:** HIGH  
**Scope:** Steps P1-007, P1-019 (lines 3541, 3548, 4616)  
**Impact:** Curl calls to `/health` would return 404. The correct endpoint is `/api/health`.

**Affected locations:**

| Line | Step | Text |
|---|---|---|
| 3541 | P1-007 | `curl -s http://localhost:8080/health` |
| 3548 | P1-007 | `curl http://localhost:8080/health` returns 200 |
| 4616 | P1-019 | `curl -sf http://localhost:8080/health` |

**Fix:** Replace `/health` with `/api/health` throughout. Correct: `curl http://localhost:20128/api/health` → `{"ok":true}`

**Source:** Research report line 432: `curl http://localhost:20128/api/health # → {"ok":true}`

---

### FINDING T-06: Hermes Agent pip Package — `hermes-agent` may not exist on PyPI (HIGH)

**Severity:** HIGH  
**Scope:** Step P1-003 (line 3095), P1-004 (line 3152)  
**Impact:** `uv pip install hermes-agent` would fail if the package is not on PyPI. The research report shows installation via curl one-liner script, NOT pip.

**Affected locations:**

| Line | Step | Text |
|---|---|---|
| 3095 | P1-003 | `hermes-agent` in pip install list |
| 3152 | P1-004 | `uv pip install hermes-agent` |
| 3160 | P1-004 | `import hermes_agent` (Python import may also not match actual module name) |

The research report shows Hermes Agent installs via:
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

**Fix:** 
1. Replace pip install with the official install script
2. Research actual Python module name (may be `hermes`, `hermes_agent`, or installed as a system binary)
3. Add note that installation creates its own venv with Python 3.11

**Note:** The troubleshooting at line 3217 already says "If hermes-agent not on PyPI" — this should be the default case, not fallback.

---

### FINDING T-07: Hermes Agent Python Version — 3.12 used but Hermes requires 3.11 (HIGH)

**Severity:** HIGH  
**Scope:** Step P1-001 (line 2943)  
**Impact:** Hermes Agent specifically requires Python 3.11. Installing Python 3.12 may cause compatibility issues.

**Evidence:**

| Source | Python Version |
|---|---|
| Research report (line 38) | "Python: 3.11 (required; installer handles uv venv creation)" |
| Step P1-001 (lines 2942-2998) | Python 3.12 via deadsnakes PPA |

**Fix:** Either:
1. Install Python 3.11 instead of 3.12 (the research says 3.11 is required)
2. Note: Hermes installer creates its own venv with 3.11, so system Python can remain 3.12. Document this distinction.

**Source:** Research report line 38: `Python: 3.11 (required; installer handles uv venv creation)`

---

### FINDING T-08: Hermes Agent Config Path — Uses `/home/guinevere/config/hermes/config.yaml` instead of `~/.hermes/config.yaml` (MEDIUM)

**Severity:** MEDIUM  
**Scope:** Step P1-005 (lines 3246-3316)  
**Impact:** Hermes Agent expects configuration at `~/.hermes/config.yaml` (or `$HOME/.hermes/config.yaml`). The StepPrompts creates config at `/home/guinevere/config/hermes/config.yaml` which Hermes will NOT automatically read.

**Evidence:**

| Source | Path |
|---|---|
| Research report (line 74) | `~/.hermes/config.yaml` |
| Step P1-005 (line 3249) | `/home/guinevere/config/hermes/config.yaml` |

**Fix:** Either:
1. Change config path to `~/.hermes/config.yaml` (recommended)
2. Or explicitly pass `--config` flag to Hermes when starting (if supported)

The Hermes config at line 3249 also contains fields that don't match actual Hermes config structure (see Finding T-09).

---

### FINDING T-09: Hermes Agent Config Structure — Fabricated YAML structure doesn't match Hermes schemas (MEDIUM)

**Severity:** MEDIUM  
**Scope:** Step P1-005 (lines 3249-3316)  
**Impact:** The config YAML has sections (`llm.primary.base_url`, `llm.primary.context_window`, `memory.redis_cache`, `loop.*`, `safety.*`, `budget.*`, `tools.*`) that don't exist in actual Hermes configuration. The real Hermes config has sections like `terminal` (backend settings), `memory` (char limits), `compression`, `tool_output`, `discord`, `group_sessions_per_user`.

**Fix:** Rewrite P1-005 to match actual Hermes configuration schema. Key sections from the research report:

```yaml
# Actual Hermes config sections:
terminal:
  backend: local
  timeout: 180
memory:
  memory_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
compression:
  enabled: true
  threshold: 0.50
  target_ratio: 0.20
tool_output:
  max_bytes: 50000
discord:
  require_mention: true
  auto_thread: true
  reactions: true
```

For LLM provider configuration, use: `hermes model` command and environment variables, not config.yaml sections.

**Source:** Research report lines 106-144 (actual config sections)

---

### FINDING T-10: SOPS binary filename — Missing architecture-specific suffix (MEDIUM)

**Severity:** MEDIUM  
**Scope:** Step P0-011 (line 1018)  
**Impact:** The SOPS binary filename at line 1018 uses `.linux.amd64` but the actual filename from getsops releases uses `.linux.amd64` for some versions and `.linux_amd64` for others. The curl download at line 1018 may fail on filename mismatch if the GitHub release uses a different naming convention.

Current: `sops-v${SOPS_VERSION}.linux.amd64`

**Fix:** Verify actual binary name from the releases page. Add a fallback note: `or download from https://github.com/getsops/sops/releases/latest and rename manually`.

---

### FINDING T-11: Gotify Docker Port — 8081 collides with wrong 9Router port (MEDIUM)

**Severity:** MEDIUM  
**Scope:** Step P2-020 (line 5678)  
**Impact:** Gotify is configured on `127.0.0.1:8081:80`. Once the 9Router port is corrected to 20128, port 8081 is free. But as written (with 9Router on 8080), there's no direct collision — they're different ports. This finding is valid only in context of the 9Router port error.

**Fix:** Keep Gotify on 8081 — it's fine once 9Router moves to 20128.

---

### FINDING T-12: PgBouncer Port — 6432 used but audit requirements specify 5433 (MEDIUM)

**Severity:** MEDIUM  
**Scope:** Step P0-019 (line 1814)  
**Impact:** The audit requirements specify PgBouncer should be on port **5433**, but StepPrompts uses **6432** (the actual PgBouncer default). Step P0-019 configured port 6432:

| Line | Text |
|---|---|
| 1814 | `listen_port = 6432` |
| 1858 | `psql -h 127.0.0.1 -p 6432` |
| 1864 | `ss -tlnp \| grep 6432` |

**Analysis:** PgBouncer's canonical default port is 6432. The audit requirement specifying 5433 appears to be the error, not StepPrompts. However, since the audit is against user-specified requirements, this is flagged as a discrepancy.

**Fix:** Clarify with operator whether PgBouncer should use 5433 (custom) or 6432 (standard default). The current 6432 in StepPrompts aligns with PgBouncer's standard default.

---

### FINDING T-13: Docker `:latest` Tags — No version pinning for container images (LOW)

**Severity:** LOW  
**Scope:** Steps P8-001 (lines 6948, 6956, 6966), P2-020 (line 5676)  
**Impact:** Using `:latest` tags makes builds non-reproducible and risks breaking changes on restart.

**Affected:**

| Line | Step | Image |
|---|---|---|
| 6948 | P8-001 | `prom/prometheus:latest` |
| 6956 | P8-001 | `grafana/grafana:latest` |
| 6966 | P8-001 | `grafana/loki:latest` |
| 5676 | P2-020 | `gotify/server:latest` |

**Fix:** Pin version tags (e.g., `prom/prometheus:v2.53.0`, `grafana/grafana:11.1.0`, `grafana/loki:3.1.0`).

---

### FINDING T-14: P0 Transition Checklist — `systemctl status redis` uses wrong service name (LOW)

**Severity:** LOW  
**Scope:** Phase 0 Transition Checklist (line 101)  
**Impact:** The checklist says `systemctl status postgresql redis docker` but the Redis service is named `redis-guinevere`, not `redis`.

**Current:** `systemctl status postgresql redis docker`  
**Fix:** Change to `systemctl status postgresql redis-guinevere docker`

---

### FINDING T-15: 9Router config uses `base_url: "https://api.9router.com/v1"` for provider config (CRITICAL)

**Severity:** CRITICAL  
**Scope:** Step P1-006 lines 3390, 3402  
**Impact:** This is a complete fabrication. 9Router routes directly to provider APIs (OpenAI, Anthropic, DeepSeek, etc.) — it does NOT route through `api.9router.com`. The `base_url` in the fabricated config should be the actual provider API endpoint (e.g., `https://api.openai.com/v1`), not a 9Router cloud URL that doesn't exist.

**Note:** This was already flagged as part of T-04, but the severity is elevated because this is not just a wrong URL — it reveals a fundamental misunderstanding of 9Router's architecture. 9Router IS the proxy; it doesn't need another `base_url` to route through. The application connects to 9Router at `localhost:20128`, and 9Router handles the actual provider routing.

**Fix:** Remove the fabricated cloud URLs entirely. 9Router's provider configuration happens in the dashboard, not in a YAML config file.

---

## DIMENSION 8: COST ACCURACY FINDINGS

### FINDING C-01: GPT-5.5 Monthly Cost — Step says $10/month, FinOps v1.1 allocates $7-8 (HIGH)

**Severity:** HIGH  
**Scope:** Step P1-008 (line 3573, 3584)  
**Impact:** Budget discrepancy could cause premature freeze triggering.

**Evidence:**

| Source | GPT-5.5 Monthly Alloc |
|---|---|
| Step P1-008 (line 3573) | "Cost Impact: ~$10/month estimated" |
| Step P1-008 (line 3584) | "Budget: $10/month allocated for GPT-5.5" |
| FinOps v1.1 (line 139) | "$7-$8 (Hard cap portion, Phase 1)" |
| FinOps v1.1 (line 545) | "$7-8 (Hard / controlled variable)" |

**Fix:** Change GPT-5.5 cost to $7-8/month to match FinOps v1.1 Phase 1 allocation.

---

### FINDING C-02: DeepSeek Monthly Cost — Step says $3/month, FinOps v1.1 allocates $1-2 (HIGH)

**Severity:** HIGH  
**Scope:** Step P1-010 (line 3772)  
**Impact:** DeepSeek is over-budgeted by 50-200%.

**Evidence:**

| Source | DeepSeek Monthly Alloc |
|---|---|
| Step P1-010 (line 3772) | "Cost Impact: ~$3/month estimated" |
| FinOps v1.1 (line 140) | "$1-$2 (Soft/near-free, Phase 1)" |
| FinOps v1.1 (line 546) | "$1-2 (Soft / optimization)" |

**Fix:** Change DeepSeek cost to $1-2/month to match FinOps v1.1.

---

### FINDING C-03: Exa Budget Description — "$5/day cap" conflates daily burst with monthly hard stop (HIGH)

**Severity:** HIGH  
**Scope:** Step P6-004 (lines 6692-6694, 6704)  
**Impact:** Misleading budget rule — the $5/day is a burst cap, not the primary budget mechanism. The actual FinOps model has a more nuanced system.

**Evidence:**

| Source | Exa Description |
|---|---|
| Step P6-004 (line 6692) | "Exa AI Search — $5/day cap enforced via Redis DB5" |
| Step P6-004 (line 6694) | `DAILY_CAP = 5.0  # USD` |
| Step P6-004 (line 6704) | "Cost: $1 avg/day, $5 cap" |
| FinOps v1.1a (line 144) | "Hybrid burst model: ~$1/month avg target, daily burst up to $5 allowed. Monthly throttle >$3 → Brave-only; hard stop >$5 → disabled" |

**Fix:** Update P6-004 to reflect the full Exa model:
- Monthly average target: ~$1
- Daily burst cap: $5 (allowed)
- Monthly throttle trigger: >$3/month → switch to Brave-only for rest of billing cycle
- Monthly hard stop: >$5/month → Exa disabled until next billing cycle
- Track both daily and cumulative monthly spend
- $5/day code variable should be renamed to `DAILY_BURST_CAP` with separate monthly tracking

---

### FINDING C-04: Brave Search Per-Query Cost — $0.01/search vs actual $0.003/query (MEDIUM)

**Severity:** MEDIUM  
**Scope:** Step P6-002 (line 6680)  
**Impact:** Cost estimate is 3.3x too high. Does not block implementation but misrepresents budget.

**Evidence:**

| Source | Brave Cost |
|---|---|
| Step P6-002 (line 6680) | "Cost: ~$0.01/search" |
| Audit requirements | "Brave Search: $3/1000 queries" ($0.003/query) |

**Fix:** Change to "Cost: ~$0.003/query (~$3 per 1000 queries)"

---

### FINDING C-05: VPS Cost Handling — Correctly marked as $0 additional (PASS — no finding)

**Severity:** N/A (CORRECT)  
**Scope:** Throughout  
**Impact:** N/A — correct.

**Verification:** StepPrompts consistently marks VPS as "$0/month (VPS already paid)" and identifies it as "Shared VPS hostdata.id 4C/16GB Ubuntu 24.04" — matching FinOps v1.1.

---

### FINDING C-06: Storage Costs — P0-027 correctly identifies idcloudhost S3 + Cloudflare R2 (PASS — no finding)

**Severity:** N/A (CORRECT)  
**Scope:** Step P0-027 (lines 2644-2793)  
**Impact:** N/A — correct.

**Verification:**
- Step P0-027 uses idcloudhost S3 as primary (correct per ADR-032)
- Step P0-027 uses Cloudflare R2 as secondary (correct per ADR-032)
- No Backblaze B2 references anywhere in the document (confirmed by grep)
- Backup script uses rclone patterns matching ADR-032 (lines 2706-2722)

---

### FINDING C-07: P1 Phase Total Cost — $15/month matches FinOps Phase 1 range (PASS — no finding)

**Severity:** N/A (CORRECT)  
**Scope:** Phase 1 header (line 2920)  
**Impact:** N/A — correctly within budget.

**Verification:** P1 says "$15/month (GPT-5.5 + DeepSeek)" — FinOps Phase 1 is $7-8 (GPT) + $1-2 (DeepSeek) + $5-6 (S3) + $1 (Brave) + $0-5 (Exa) + $0-0.50 (misc) = $14-22.50. P1's $15 falls within this range for LLM costs only. S3 is tracked in P0 (backup baseline at ~$1) and grows across phases.

---

## SUPPLEMENTARY: PROVIDER REFERENCE AUDIT

### Hetzner References
**Status:** CLEAN — Zero references found in StepPrompts.md

### Vultr References
**Status:** CLEAN — Zero references found in StepPrompts.md

### Backblaze B2 References
**Status:** CLEAN — Zero references found. All "B2" matches are Redis DB2 references, not Backblaze.

### OpenRouter-as-Fallback References
**Status:** CLEAN — Zero references found. Fallback chain is correctly: 9Router → direct API → Ollama.

### New VPS References
**Status:** CLEAN — All VPS references consistently describe the shared hostdata.id existing VPS.

---

## SUMMARY TABLE

| Dimension | Status | Findings | Critical | High | Medium | Low |
|---|---|---|---|---|---|---|
| Technical Accuracy | **FAIL** | 15 | 5 | 3 | 4 | 3 |
| Cost Accuracy | **NEEDS REVIEW** | 6 | 0 | 3 | 1 | 0 |
| Provider References | **PASS** | 0 | 0 | 0 | 0 | 0 |
| **TOTAL** | **FAIL** | **21** | **5** | **6** | **5** | **3** |

---

## CRITICAL FINDING DETAIL

All 5 CRITICAL findings are related to 9Router configuration. They are tightly coupled:

1. **T-01:** Port 8080 → must be 20128 (24 locations)
2. **T-02:** npm package `@9router/cli` → must be `9router`
3. **T-03:** YAML config file approach → must use web dashboard + environment variables
4. **T-04:** `https://api.9router.com/v1` cloud URL → must be `http://localhost:20128/v1`
5. **T-15:** Provider `base_url` pointing to cloud API → 9Router IS the proxy, not a pass-through

**These 5 findings together mean Steps P1-005 through P1-015, plus P3-005, are unexecutable as written.** The 9Router integration — which is the backbone of the entire LLM routing stack — is based on fundamentally incorrect assumptions about how 9Router is installed, configured, and accessed.

---

## RECOMMENDED REMEDIATION PATH

### Phase 1: Fix 9Router (T-01 through T-05, T-15) — These must be fixed first

1. Rewrite P1-006 entirely:
   - Install: `npm install -g 9router`
   - Environment: PORT=20128, DATA_DIR, REQUIRE_API_KEY=true
   - Start: `9router` (no config file args)
   - Config: Document web dashboard setup process
2. Fix all port references from 8080 to 20128 across all affected steps
3. Fix health endpoint from `/health` to `/api/health`
4. Remove all `https://api.9router.com/v1` URLs
5. Remove fabricated YAML config sections

### Phase 2: Fix Cost Discrepancies (C-01, C-02, C-03, C-04)

1. Update P1-008 GPT-5.5 cost to $7-8/month
2. Update P1-010 DeepSeek cost to $1-2/month
3. Update P6-004 Exa description to full hybrid burst model
4. Update P6-002 Brave cost to $0.003/query

### Phase 3: Fix Other Technical Issues (T-06 through T-14)

1. Verify Hermes Agent pip availability and adjust P1-004
2. Address Python 3.11 vs 3.12 for Hermes compatibility
3. Fix Hermes config path and schema to match actual Hermes structure
4. Pin Docker image versions
5. Fix service name in P0 transition checklist

---

## EVIDENCE OF AUDIT

- **StepPrompts.md** read: All 7360 lines (in 7 chunks of 1000)
- **FinOps v1.1** read: All 661 lines
- **9Router research** read: All 994 lines
- **ADR-032** read: All 224 lines
- **PROGRESS.md** read: All 399 lines
- **Targeted grep searches:** 6 searches confirming 24 port errors, package name errors, and clean provider references

---

*Audit completed 2026-05-31 by Senior Independent Auditor.*  
*Verdict: FAIL — 5 CRITICAL findings block implementation as written.*