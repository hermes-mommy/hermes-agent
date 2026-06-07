# Auditor Gate — Safety, Isolation, and Documentation (Domains 01, 06, 07)

| Field | Value |
|---|---|
| Audit Type | Independent auditor gate review |
| ADR | ADR-035 v1.0 (Hermes Agent Integration via MCP) |
| Date | 2026-06-07 |
| Auditor | Independent specialist (READ-ONLY) |
| Scope | Evidence integrity + source code verification for Domains 01, 06, 07 |

---

## Overall Gate Verdict: **FAIL**

Domain 01 evidence file contains multiple claims that are contradicted by source code and two referenced files that do not exist in the repository. Domains 06 and 07 pass or require minor review. Domain 01 failure is blocking.

---

## Domain 01 — Safety Compliance: **FAIL**

### Verdict Mismatch

| Source | Verdict |
|---|---|
| Evidence file (`01-safety-compliance.md`) | **PASS** |
| Source report (`research-reports/phase6-audit/01-safety-compliance.md`) | **CONDITIONAL PASS** |

The source report explicitly states two gaps preventing an unconditional PASS:
1. No literal `timeout_ms` enforcement parameter found in the Hermes safety plugin excerpt
2. No explicit health-data confrontation blocking logic in `src/surveillance/auth.py`

The evidence file upgrades this to a flat PASS without acknowledging or resolving these gaps.

### Non-Existent File References

The evidence file references two source code files that **do not exist** anywhere in the repository:

| Claimed Path | Status | Impact |
|---|---|---|
| `src/hermes-config/config.schema.json` | **NOT FOUND** — glob search across entire repo returned zero matches | AC-SAFE-002 claim ("config.schema.json validates") is unverifiable |
| `src/hermes-config/mcp-hermes.json` | **NOT FOUND** — glob search across entire repo returned zero matches | AC-SAFE-005 claim ("mcp-hermes.json uses fail-closed strategy") is unverifiable |

**Note:** The actual config path is `hermes-config/config.yaml` (no `src/` prefix). The evidence file also misstates the config path as `src/hermes-config/config.yaml`.

### False Claims Against Source Code

The following evidence claims are **provably false** when checked against the actual `hermes-config/config.yaml` (354 lines):

| AC-SAFE | Evidence Claim | Actual Source Code | Verdict |
|---|---|---|---|
| AC-SAFE-002 | "config.schema.json validates whitelist array" | File does not exist | **FALSE** |
| AC-SAFE-003 | `daily_cost_ceiling_usd: 5.0` in config | Config has `monthly_limit: 30.00` (line 73); no `daily_cost_ceiling_usd` key exists anywhere | **FALSE** |
| AC-SAFE-005 | `mcp-hermes.json` uses `"fail-closed"` strategy | File does not exist | **FALSE** |
| AC-SAFE-008 | `tool_timeout_seconds: 30` | No such config key exists. `postgres_tool.py` has `_QUERY_TIMEOUT_SECONDS: 30.0` (line 98), but this is a Python constant, not a Hermes config parameter | **MISREPRESENTED** |
| AC-SAFE-008 | `request_timeout_ms: 30000` | No such config key exists. Approval webhook has `timeout_ms: 300000` (line 341), which is 5 minutes, not 30 seconds | **FALSE** |
| AC-SAFE-008 | `max_retries: 2` | Approval config has `retry_count: 2` (line 342), but this applies to approval webhooks, not tool timeouts | **MISREPRESENTED** |

### Scope Mismatch

The source report evaluates **code-level safety controls** (HARD STOP hooks in `safety_plugin.py`, yandere FSM ceiling, consent gate fail-closed, memory classification, drift detection, punishment engine, surveillance auth). The evidence file evaluates **Hermes config settings** (tool whitelist, cost ceiling, timeout bounds). These are different safety scopes — the evidence file does not faithfully represent the source report's actual findings.

### What the Config Actually Contains

Verified from `hermes-config/config.yaml`:
- `approval.timeout_ms: 300000` (5 minutes) — line 341
- `approval.retry_count: 2` — line 342
- `approval.fallback_on_timeout: deny` — line 344 (fail-closed)
- `budget.monthly_limit: 30.00` — line 73
- `agent.max_iterations: 15` — line 83
- Hook `timeout_ms: 500` (budget_check), `timeout_ms: 200` (consent_gate), `timeout_ms: 50` (dnr_filter)
- MCP tools `include` list: 7 tools (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time) — not 8
- No tool whitelist enforcement mechanism (tools.include is under fastmcp_custom which is `enabled: false`)

### Domain 01 Verdict: **FAIL**

Evidence file must be rewritten to:
1. Correctly reflect the source report's CONDITIONAL PASS verdict
2. Remove references to non-existent files (`config.schema.json`, `mcp-hermes.json`)
3. Correct the config values (no `daily_cost_ceiling_usd: 5.0`, no `tool_timeout_seconds: 30`)
4. Fix the config path (`hermes-config/config.yaml`, not `src/hermes-config/config.yaml`)

---

## Domain 06 — Aizanta Isolation: **PASS**

### Source Code Verification

All isolation claims are supported by actual source code:

| Claim | Source Code Evidence | Status |
|---|---|---|
| PostgreSQL pinned to port 5433 | `src/mcp/tools/postgres_tool.py:95` — `_DEFAULT_PORT: Final[int] = 5433` | **VERIFIED** |
| PostgreSQL port hardcoded, no env override | `postgres_tool.py:116` — `port = _DEFAULT_PORT  # 5433 — hardcoded, no env override (Aizanta isolation)` | **VERIFIED** |
| Redis pinned to port 6380 | `src/mcp/tools/redis_tool.py:42` — `_REDIS_PORT = 6380` | **VERIFIED** |
| Aizanta ports 5432/6379 blocked | `hermes-config/hooks/hybrid_guards.py:164-167` — `STANDARD_PORTS: {5432: "postgresql", 6379: "redis"}` | **VERIFIED** |
| Port pattern blocking active | `hybrid_guards.py:176-184` — regex patterns for host:port, `port=`, `-p` forms | **VERIFIED** |
| Aizanta path isolation | `hybrid_guards.py:145-159` — blocks `/home/aizanta`, `/etc/aizanta`, `/var/lib/aizanta`, `/opt/aizanta`, `/aizanta` | **VERIFIED** |
| Canonical ports documented | `hermes-config/config.yaml:199` — `Redis 6380, Postgres 5433, 9Router 20128` | **VERIFIED** |
| No Aizanta port references in config | `hermes-config/config.yaml` — zero occurrences of `5432` or `6379` | **VERIFIED** |

### docker-compose.yml Weakness

The evidence file cites `docker-compose.yml` for port isolation. The only docker-compose file found is at `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml`, which contains only a Gotify service — no PostgreSQL or Redis container definitions. This citation is misleading but **non-blocking** because the actual port isolation is enforced at the source code level (hardcoded constants + guard layer), not at the Docker infrastructure level from this file.

### Domain 06 Verdict: **PASS**

Source code evidence fully supports all isolation claims. The docker-compose citation is weak but does not affect the substantive isolation verification.

---

## Domain 07 — Documentation: **NEEDS REVIEW**

### Verdict Comparison

| Source | Verdict |
|---|---|
| Evidence file | **CONDITIONAL** |
| Source report | **PASS with documentation-gap notes** |

The evidence file's "CONDITIONAL" label is close to the source report's "PASS with documentation-gap notes." Both acknowledge the same core issue (71 stale StepPrompts markers). However, the source report's consolidated verdicts table has one explicit FAIL item:

| Check | Source Report Verdict | Evidence File Treatment |
|---|---|---|
| StepPrompts stale markers | **FAIL** | Acknowledged as "71 stale markers" but not flagged as FAIL |
| P5 marked verified/PASS | **PARTIAL PASS** | Not mentioned in evidence file |

### Source Code Verification

The source report's findings are internally consistent. The 71 stale StepPrompts markers and the PROGRESS.md P5 formatting inconsistency are real documentation hygiene issues, not evidence integrity problems.

### Domain 07 Verdict: **NEEDS REVIEW**

The evidence file should:
1. Explicitly note the StepPrompts FAIL status from the source report
2. Mention the P5 table row formatting inconsistency
3. Either match the source report's verdict label or clearly explain the divergence

---

## Evidence Verification Checklist

### Domain 01 — Safety Compliance

- [x] Evidence file exists and is well-formed
- [ ] Claims in evidence file match source report findings — **FAIL**: verdict mismatch (PASS vs CONDITIONAL PASS); scope mismatch (config vs code-level safety)
- [ ] Source code evidence supports claims — **FAIL**: `config.schema.json` and `mcp-hermes.json` do not exist; multiple config values are false
- [ ] No contradictions between evidence and source reports — **FAIL**: verdict, scope, and multiple factual claims contradict
- [x] Safety boundaries preserved — no consent violations or surveillance overreach detected in source code
- [x] Aizanta isolation verified — zero Aizanta touch confirmed

### Domain 06 — Aizanta Isolation

- [x] Evidence file exists and is well-formed
- [x] Claims in evidence file match source report findings
- [x] Source code evidence supports claims (postgres_tool.py, redis_tool.py, hybrid_guards.py)
- [x] No contradictions between evidence and source reports
- [x] Safety boundaries preserved
- [x] Aizanta isolation verified (zero touch, correct ports 5433/6380, blocked 5432/6379)

### Domain 07 — Documentation

- [x] Evidence file exists and is well-formed
- [ ] Claims in evidence file match source report findings — **PARTIAL**: StepPrompts FAIL not surfaced; P5 inconsistency not mentioned
- [x] Source code evidence supports claims
- [x] No contradictions between evidence and source reports (minor label difference only)
- [x] Safety boundaries preserved
- [x] Aizanta isolation verified (N/A for documentation domain)

---

## Summary Table

| Domain | Verdict | Blocking Issues |
|---|---|---|
| 01 — Safety Compliance | **FAIL** | Verdict mismatch; 2 non-existent files referenced; 4+ false config claims; scope mismatch with source report |
| 06 — Aizanta Isolation | **PASS** | None (docker-compose citation weak but non-blocking) |
| 07 — Documentation | **NEEDS REVIEW** | StepPrompts FAIL not surfaced; P5 inconsistency not mentioned |
| **Overall Gate** | **FAIL** | Domain 01 blocks completion |

---

## Remediation Required

### Blocking (must resolve before gate passes):

1. **Rewrite `01-safety-compliance.md`** to correctly reflect the source report's CONDITIONAL PASS verdict and its two explicit gaps
2. **Remove references to non-existent files** (`config.schema.json`, `mcp-hermes.json`)
3. **Correct false config claims**: `daily_cost_ceiling_usd: 5.0` → `monthly_limit: 30.00`; `tool_timeout_seconds: 30` → `_QUERY_TIMEOUT_SECONDS: 30.0` (Python constant, not Hermes config)
4. **Fix config path**: `hermes-config/config.yaml` (not `src/hermes-config/config.yaml`)

### Non-blocking (should fix):

5. Update `07-documentation-audit.md` to surface StepPrompts FAIL status from source report
6. Remove or qualify the docker-compose.yml citation in `06-aizanta-isolation.md`

---

## Files Audited

| File | Role |
|---|---|
| `docs/setup-evidence/phase6-audit/VERIFICATION-SUMMARY.md` | Evidence summary |
| `docs/setup-evidence/phase6-audit/01-safety-compliance.md` | Domain 01 evidence (FAIL) |
| `docs/setup-evidence/phase6-audit/06-aizanta-isolation.md` | Domain 06 evidence (PASS) |
| `docs/setup-evidence/phase6-audit/07-documentation-audit.md` | Domain 07 evidence (NEEDS REVIEW) |
| `research-reports/phase6-audit/01-safety-compliance.md` | Domain 01 source report |
| `research-reports/phase6-audit/06-aizanta-isolation.md` | Domain 06 source report |
| `research-reports/phase6-audit/07-documentation-audit.md` | Domain 07 source report |
| `hermes-config/config.yaml` | Hermes gateway config (354 lines) |
| `hermes-config/hooks/hybrid_guards.py` | Port/path isolation guards (740 lines) |
| `src/mcp/tools/postgres_tool.py` | PostgreSQL tool with port 5433 (296 lines) |
| `src/mcp/tools/redis_tool.py` | Redis tool with port 6380 (408 lines) |
| `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` | Docker compose (Gotify only, 18 lines) |

---

| Field | Value |
|---|---|
| Auditor | Independent specialist |
| Date | 2026-06-07 |
| Gate Result | **FAIL** |
| Blocking Domain | 01 — Safety Compliance |
| Next Action | Rewrite evidence file 01 to match source report; remove non-existent file references; correct false config claims |
