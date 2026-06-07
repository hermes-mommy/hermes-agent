# Auditor Gate — Architecture, Performance, and Security (Domains 02, 04, 05)

| Field | Value |
|---|---|
| Audit Type | Independent re-audit of Phase 6 evidence |
| Date | 2026-06-07 |
| Domains | 02 Architecture Compliance, 04 Performance, 05 Security Posture |
| Scope | Cross-check evidence files against source reports and actual source code |
| Mode | READ-ONLY |

---

## Overall Gate Verdict

| Domain | Verdict | Reason |
|---|---|---|
| 02 Architecture Compliance | **NEEDS REVIEW** | Evidence references nonexistent files; verification summary contradicts source report |
| 04 Performance | **PASS** | Source report provides real VPS metrics; evidence accurately reflects report findings |
| 05 Security Posture | **NEEDS REVIEW** | Evidence makes false claims about config values and gitignore coverage |
| **Overall Gate** | **NEEDS REVIEW** | Verification summary contains factual errors that must be corrected before PASS |

---

## Critical Finding: Verification Summary Factual Errors

The `VERIFICATION-SUMMARY.md` contains multiple claims **not supported by actual repository contents**. This is the primary blocker.

### 1. Nonexistent File References

| Claimed Path | Actual Status | Evidence File |
|---|---|---|
| `src/hermes-config/config.yaml` | **Does not exist** — actual path: `hermes-config/config.yaml` | 02-architecture-compliance.md |
| `src/hermes-config/config.schema.json` | **Does not exist anywhere in repository** | VERIFICATION-SUMMARY.md AC-SAFE-002 |
| `src/hermes-config/mcp-hermes.json` | **Does not exist anywhere in repository** | 02-architecture-compliance.md |
| `docker-compose.yml` (root) | **Does not exist** — only at `docs/setup-evidence/P2/STEP-P2-020/` | 02-architecture-compliance.md |

Verification: glob searches for `**/*config.schema*`, `**/*mcp-hermes*`, `**/docker-compose*` confirmed absence.

### 2. Unverifiable AC-SAFE Claims

| AC-SAFE ID | Claim in Summary | Actual Repository State |
|---|---|---|
| AC-SAFE-002 | "Tool whitelist enforced (8 tools); config.schema.json validates" | **UNVERIFIED** — no schema exists; config.yaml shows 7 tools in fastmcp_custom.tools.include |
| AC-SAFE-003 | "daily_cost_ceiling_usd: 5.0 in config; schema enforces range [0,100]" | **UNVERIFIED** — config has monthly_limit: 30.00 only; no daily ceiling field |
| AC-SAFE-005 | "mcp-hermes.json uses fail-closed strategy" | **PARTIALLY VERIFIED** — file absent, but fail-closed confirmed via config.yaml hooks |

### 3. Incorrect Gitignore Claim

Verification summary states: `monitoring/.env` not gitignored.

**Actual .gitignore contains `*.env`** (global rule, excludes .env.example). The `*.env` pattern matches at any depth. Therefore `monitoring/.env` **IS covered**. The claim is factually incorrect.

---

## Domain 02: Architecture Compliance

### Verdict: NEEDS REVIEW

### Evidence Verification Checklist

| Check | Status | Notes |
|---|---|---|
| Evidence file exists and is well-formed | PASS | File present, markdown valid |
| Claims match source report findings | FAIL | Evidence uses src/hermes-config/ paths; source report uses hermes-config/ |
| Source code supports claims | PARTIAL | config.yaml exists; config.schema.json and mcp-hermes.json do not exist |
| 5-pillar assessment consistent with config | PARTIAL | Pillars 3,5 verified; Pillars 1,2,4 cannot be fully verified from local |
| CONDITIONAL verdicts justified | FAIL | Evidence file does not list specific unverified items per pillar |

### Findings

**Path discrepancies:** Evidence references `src/hermes-config/config.schema.json` and `src/hermes-config/mcp-hermes.json`. Neither exists. The source report correctly references `hermes-config/config.yaml` but also lists nonexistent files.

**Docker-compose isolation:** No docker-compose.yml at repo root. Only at `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` (setup artifact with gotify service on guinevere-net, 127.0.0.1:8081). Cannot verify full network isolation.

**Verified from hermes-config/config.yaml:**
- Pillar 1: Discord gateway config with allowed channels/users — PRESENT
- Pillar 3: Safety hooks with on_failure: block (fail-closed) — CONFIRMED
- Pillar 5: 9Router-only LLM at localhost:20128/v1 — CONFIRMED
- Canonical ports: Redis 6380, Postgres 5433, 9Router 20128 — CONFIRMED

**Source report quality:** Source report is more accurate than evidence file. It correctly identifies missing evidence (GuinevereMemoryProvider, RBAC migration SQL, runtime service state). Evidence file oversimplifies.

### Required Actions Before PASS
1. Determine if config.schema.json was planned but never created
2. Determine if mcp-hermes.json is an artifact of a different phase
3. Update evidence file paths to hermes-config/ (not src/hermes-config/)
4. Locate or create production docker-compose.yml for network isolation

---

## Domain 04: Performance Audit

### Verdict: PASS

### Evidence Verification Checklist

| Check | Status | Notes |
|---|---|---|
| Evidence file exists and is well-formed | PASS | File present, markdown valid |
| Claims match source report findings | PASS | Evidence accurately summarizes source report metrics |
| Source code supports claims | PASS | VPS metrics collected via SSH with actual commands shown |
| Performance claims backed by metrics | PASS | Source report has real VPS measurements with multiple samples |
| CONDITIONAL verdicts justified | N/A | Domain verdict is PASS |

### Findings

**Source report is comprehensive:**
- VPS SSH measurements with actual curl timing commands and multiple samples
- Hermes gateway: 5 measurements (0.011s, 0.001s, 0.001s, 0.001s, 0.001s) — well under 2s target
- 9Router warm latency: 0.044s — well under 1s target
- Process memory via ps aux: Hermes ~130MB RSS, uvicorn ~97MB, mcp.manager ~79MB
- Prometheus metrics verified reachable at :9191/metrics
- VPS: 15 GiB RAM, 10 GiB available, swap nearly unused

**Evidence file accuracy:** Evidence correctly reports Hermes <2s (actual <0.012s), 9Router <1s (actual 0.045s), MCP startup ~3s, memory negligible, 139/139 tests green.

**Watch item noted:** Local 9Router had one 4.134s cold-start outlier. Not a regression.

---

## Domain 05: Security Posture

### Verdict: NEEDS REVIEW

### Evidence Verification Checklist

| Check | Status | Notes |
|---|---|---|
| Evidence file exists and is well-formed | PASS | File present, markdown valid |
| Claims match source report findings | FAIL | Evidence claims specific config values that don't exist |
| Source code supports claims | PARTIAL | SOPS and fail-closed verified; tool whitelist and cost ceiling claims not |
| Security claims verified | PARTIAL | No plaintext secrets, SOPS active confirmed; specific AC-SAFE claims false |
| CONDITIONAL verdicts justified | N/A | Verdict is PARTIAL PASS |

### Findings

**Verified security claims:**
- No plaintext secrets in hermes-config/ — CONFIRMED (all secrets use env var substitution)
- SOPS encryption active — CONFIRMED (.sops.yaml present with age recipients)
- Age key not at repo root — CONFIRMED (only in docs/setup-evidence/P0/ as proof artifact)
- Fail-closed security posture — CONFIRMED (config.yaml: on_failure: block, fallback_on_timeout: deny)
- No secrets in git log — Source report confirms git history clean

**Unverified or incorrect claims:**
- AC-SAFE-002 (8-tool whitelist with schema validation) — NO supporting evidence. config.schema.json does not exist. Config shows 7 tools in fastmcp_custom.tools.include only.
- AC-SAFE-003 (daily_cost_ceiling_usd: 5.0) — FALSE. Config has monthly_limit: 30.00 only. No daily ceiling field exists in config.yaml.
- AC-SAFE-005 (mcp-hermes.json fail-closed) — File does not exist, but fail-closed behavior IS confirmed via config.yaml hooks and approval settings.
- monitoring/.env not gitignored — FALSE. .gitignore contains *.env which covers it.

**Source report is more accurate:** The source report (research-reports/phase6-audit/05-security-posture.md) correctly states: "monitoring/.env exists locally and must remain untracked" and notes VPS checks were not performed. The evidence file introduces factual errors not present in the source.

### Required Actions Before PASS
1. Verify the actual tool whitelist count against config.yaml (7 tools, not 8)
2. Verify the actual cost ceiling mechanism (monthly \$30, not daily \$5)
3. Correct the monitoring/.env gitignore claim
4. Perform VPS security checks (open ports, age key location) when SSH available

---

## Summary of Findings

### Blocking Issues (must fix before gate PASS)
1. **Nonexistent file references**: config.schema.json, mcp-hermes.json referenced but do not exist
2. **False AC-SAFE-002 claim**: 8-tool whitelist with schema validation — unverifiable
3. **False AC-SAFE-003 claim**: daily_cost_ceiling_usd: 5.0 — field does not exist in config
4. **False gitignore claim**: monitoring/.env IS covered by *.env rule

### Non-Blocking Issues (corrective action recommended)
1. Evidence file paths use src/hermes-config/ instead of hermes-config/
2. Evidence file oversimplifies source report's CONDITIONAL findings
3. Production docker-compose.yml not found at repo root
4. VPS security checks (open ports, age key) not performed

### What IS Verified and Sound
1. Performance audit — solid VPS evidence, PASS confirmed
2. SOPS encryption active with age recipients
3. Fail-closed security posture in hooks and approval config
4. No plaintext secrets in hermes-config/
5. 9Router-only LLM routing confirmed
6. Canonical port isolation documented (Redis 6380, Postgres 5433)
7. Safety hooks configured with on_failure: block
8. Discord gateway config present and restrictive

---

## Footer

| Field | Value |
|---|---|
| Auditor | Independent sub-agent (architecture/performance/security specialist) |
| Date | 2026-06-07 |
| Phase | 6 — System Audit |
| ADR | ADR-035 v1.0 |
| Verdict | NEEDS REVIEW — verification summary must be corrected before PASS |
