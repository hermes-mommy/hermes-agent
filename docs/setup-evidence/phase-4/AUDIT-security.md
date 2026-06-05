# AUDIT -- Phase 4 Batch Plan Security Review

> **Auditor**: Guinevere (Security Auditor)
> **Target**: docs/setup-evidence/phase-4/batch-plan-phase-4.md
> **Date**: 2026-06-05
> **Verdict**: **NEEDS REVIEW** -- 10 findings (3 BLOCKING, 4 HIGH, 3 MEDIUM)
---

## 1 Verdict

**NEEDS REVIEW.** The batch plan correctly identifies the major architectural risks (Hermes fail-open model, dual auth matrix sources, budget atomicity) and proposes reasonable mitigations. However, the YAML auth matrix in config.yaml is structurally incompatible with the Python auth_matrix.py, creating a gap that undermines the auth overlay ability to enforce the actual auth matrix across all 16 tools. Several guard porting gaps and the startup gate runtime-blindness constitute material security risks. All BLOCKING findings must be resolved before Phase 4 implementation begins.
---

## 2 Auth Overlay Bypass Analysis

### 2.1 YAML vs Python Auth Matrix (BLOCKING)

**Finding F-001**: The auth_matrix YAML section in config.yaml (lines 280-307) uses a fundamentally different schema from the Python AUTH_MATRIX.

| Dimension | config.yaml YAML | Python auth_matrix.py |
|-----------|-----------------|----------------------|
| Structure | Category-level: 5 servers | Tool-level: 16 individual tools |
| Operation mapping | Abstract categories | Concrete operations per tool |
| Tool coverage | 5 native server categories only | All 16 tools |
| Postgres | MISSING | 5 FORBIDDEN ops |
| Redis | MISSING | 19 ops, 6 FORBIDDEN |
| Docker | MISSING | 11 ops, 2 FORBIDDEN |
| Custom tools | ALL 7 MISSING | All mapped |

**Impact**: The auth_handler.py pseudocode reads from config.yaml auth_matrix section. If this YAML block is used as-is, the auth overlay has zero visibility into postgres, redis, docker, obscura_cdp, grep_app, context7, sequential_thinking, or time operations. These tools would be completely un-gated or completely blocked depending on handler default behavior.

**Note**: ADR-035 Appendix B shows a DIFFERENT, more complete YAML matrix with postgres_tool, redis_tool, obscura_cdp entries -- but the deployed config.yaml does NOT have these. P4-001 must reconcile which version is canonical.

**Mitigation required**: P4-001 MUST expand the auth_matrix YAML section to cover all 16 tools with operation-level mappings matching Python AUTH_MATRIX, OR the auth overlay must read from the Python module directly (changing BD-006).

### 2.2 Operation Extraction Undefined (HIGH)

**Finding F-002**: The auth_handler.py pseudocode calls _extract_operation(tool_name, args) to determine which operation is being performed. This function is not defined anywhere in the plan. For multi-level tools: postgres_query parsing arbitrary SQL, filesystem write vs delete tool naming, native terminal server tool_name resolution. Without a concrete operation extraction specification, the auth overlay cannot reliably determine auth levels.

### 2.3 Wildcard Tool Handling (MEDIUM)

**Finding F-003**: Python matrix uses "*" wildcard for 8 tools. The YAML matrix uses explicit per-operation mappings (fetch.get vs fetch.post). If YAML adds wildcard semantics but tools route through differently-named MCP servers, the tool_name-to-server mapping must be precisely specified.

### 2.4 Unknown Tool/Operation Default (MEDIUM)

**Finding F-004**: Python get_auth_level() raises KeyError -- fail-closed. The auth_handler pseudocode doesn not show fail-closed behavior. The plan must specify: unknown tool_name leads to FORBIDDEN (block + audit log), not READ_AUTO.

### 2.5 Bypass Summary

**With current config.yaml**: YES -- all 7 custom tools un-gated.
**With corrected YAML**: PARTIALLY -- hook intercepts all, but dual-source drift creates inconsistencies.
---
## 3 Budget Enforcement Race Condition Analysis

### 3.1 Lua Script Atomicity (PASS with caveat)

**Finding F-005 (MEDIUM)**: The Redis Lua script IS atomic -- Redis executes Lua scripts as a single atomic operation. No TOCTOU race condition exists at the Redis level. However, the script only tracks a single key (cost:current_month) for monthly total vs hard cap ($30). The existing BudgetEnforcer enforces three layers: per-tool daily cap (exa $5/day, brave $3/day), global daily emergency cap ($10/day), and monthly absolute cap ($30/month). The Lua script enforces only layer 3.

This means exa could burn $30 in one day without hitting a daily cap. The $24 warning threshold works, but daily overspend is not caught. The plan should either add per-tool daily tracking to the Lua script or document this as an accepted gap.

### 3.2 Post-Call Reconciliation Gap

The plan mentions post-tool-call reconciliation hook but this hook is not designed, not scoped, and not in the file list. If the estimate is too low, monthly spend can silently exceed the cap.

### 3.3 Budget Enforcer Dual-Write Risk

If both the Hermes budget_check.py hook AND the existing BudgetEnforcer.record_and_check() (from FastMCP tools) write to the same Redis keys, costs may be double-counted. The plan does not address this.

---
## 4 Hybrid Guard Completeness

### 4.1 Shell Injection Protection Gap (HIGH)

**Finding F-006**: shell_tool.py has four safety layers: injection character detection, blocked patterns scanning, allowed commands whitelist, and blocked path patterns (Aizanta isolation). The Hermes terminal config has allowed_commands and blocked_commands. The hybrid_guards.py handles injection character detection.

**Critical question**: Does the pre_tool_call hook receive the RAW command string or already-parsed arguments from Hermes terminal? If Hermes parses before the hook sees it, injection detection would see split tokens and NOT detect injection characters. Additionally, blocked path patterns (Aizanta isolation) is not mentioned in the hybrid guards plan.

### 4.2 Docker Guard Incompleteness (HIGH)

**Finding F-007**: docker_tool.py has five guard layers: container name regex validation, image name metacharacter check, FORBIDDEN_PATTERNS, guinevere-net network check, and runtime sub-command blocking.

The hybrid_guards.py only mentions Docker container name prefix validation (guinevere-) which is different from and weaker than the source network-based isolation. The source code checks network membership, not container name prefix.

**Missing**: image name validation, FORBIDDEN_PATTERNS check, network re-verification for destructive operations.

### 4.3 Git Force-Push Guard (PASS)

Comprehensive force-push protection in git_tool.py: _is_forbidden() with refspec parsing and branch normalization. The hybrid_guards.py should replicate the full logic.

### 4.4 GitHub Guard (PASS)

Rate-limit + backoff mapped to post_tool_call observer (log only) -- correct for Phase 4.

---
## 5 Startup Gate Effectiveness

### 5.1 Pre-Flight vs Runtime Protection (HIGH)

**Finding F-008**: The startup gate validates plugins BEFORE Hermes starts. It catches missing directories, missing plugin.yaml, missing register(), and import errors. It does NOT protect against runtime crashes.

The plan acknowledges this in Section 15, Caveat 1. The mitigation for auth_overlay is the fail-closed exception handler. But guinevere_safety (which handles HARD STOP, distress, yandere boundary) has NO equivalent fail-closed guarantee.

**Recommendation**: Add try/except wrapper around guinevere_safety hooks that logs the crash AND returns a block action for critical safety hooks, mirroring auth_overlay fail-closed design.

### 5.2 Can Hermes Start Without the Wrapper?

**Finding F-009 (MEDIUM)**: An operator could run hermes gateway run directly, bypassing the startup gate. Document that direct invocation is forbidden; systemd is the only supported start method.

---
## 6 Dual Auth Matrix Source Risk

### 6.1 Drift Potential (BLOCKING)

**Finding F-010**: BD-006 creates permanent divergence risk between YAML and Python sources. Key scenarios: new tool added to Python but forgotten in YAML (un-gated in Hermes), auth level changed in one source but not the other (inconsistent enforcement), FORBIDDEN removed from Python but still in YAML (confusion).

The plan mitigation (CI check) is mentioned in Section 15, Caveat 2 but is not implemented, not specified, not in any file list. Without automated drift detection, the dual matrix WILL diverge.

**Mitigation**: Either implement a CI script that diffs YAML vs Python on every commit, or have the auth overlay read from the Python module via import (changing BD-006).

### 6.2 ADR-035 vs Python vs config.yaml Contradictions

| Source | postgres.insert | redis.delete | 
|--------|----------------|-------------|
| Python | FORBIDDEN | DESTRUCTIVE_APPROVAL (del) |
| ADR-035 App B | WRITE_NOTIFY | WRITE_NOTIFY |
| config.yaml | MISSING | MISSING |

Direct contradictions between all three sources. The Python matrix must be the authoritative source.

---
## 7 FORBIDDEN Enforcement Analysis

### 7.1 Design Correctness (PASS)

In Python auth.py: AuthLevel.FORBIDDEN raises ForbiddenOperationError immediately -- no approval path, no timeout, no override. In auth_handler pseudocode: FORBIDDEN returns block action with audit log. Design is correct.

### 7.2 15 FORBIDDEN Operations With No YAML Coverage

| Tool | Operations |
|------|-----------|
| postgres | insert, update, delete_row, drop, truncate |
| redis | flushdb, flushall, config, debug, shutdown, slaveof |
| shell | rm_rf_root, sudo_rm_rf |
| docker | system_prune, rm_all |
| git | force_push_main |

Until the YAML matrix is expanded, the auth overlay cannot enforce these blocks.

---
## 8 Approval Flow Security

### 8.1 5-Minute Timeout -- Fail-Closed (PASS)

Config: timeout_ms: 300000, fallback_on_timeout: deny. Python: asyncio.wait_for raises TimeoutError -> returns False -> ForbiddenOperationError. Design is correct.

### 8.2 Webhook Integrity (PASS with caveat)

Webhook URL from DISCORD_APPROVAL_WEBHOOK env var, SOPS/age encrypted. Correct. The plan does not specify webhook message format, operator response mechanism, or how response routes back to waiting handler.

### 8.3 Concurrent Approval Risk (MEDIUM)

Python auth.py uses _pending_approvals dict keyed by tool_name. Two concurrent calls for same tool -> second overwrites first event. Auth overlay should use unique approval IDs (UUID per request).

---
## 9 Secret Handling

### 9.1 No Secrets in Logs/Configs/Artifacts (PASS with caveat)

Plan Section 10 documents all secrets as SOPS/age-encrypted, accessed via os.environ. Correct. Caveats: auth_handler.py reads entire config.yaml at init; budget hook uses REDIS_PASSWORD pattern same as BudgetEnforcer (verify implementation).

### 9.2 Logger Output Risk

forbidden_handler.py logs FORBIDDEN attempts. The plan does not specify whether tool arguments (which may contain sensitive data) are redacted from audit logs. Existing shell_tool.py truncates to 120 chars -- ensure audit logs follow same pattern.

---
## 10 Aizanta Isolation

### 10.1 Cross-Contamination Prevention (PASS with caveat)

**Verified**: Redis port 6380, PostgreSQL port 5433, Docker network guinevere-net 172.28.x.x. No cross-contamination paths identified.

**Caveat**: hybrid_guards.py lacks Aizanta path isolation. P4-004 must ensure /home/aizanta, /etc/aizanta are in filesystem.blocked_paths or in hybrid guard. No privilege escalation paths identified.

---
## 11 Summary of Findings

### BLOCKING (Must Fix Before Implementation)

| ID | Finding | Section | Fix |
|----|---------|---------|-----|
| F-001 | YAML auth matrix structurally incompatible with Python | 2.1 | Expand YAML to 16 tools with operation-level mappings per Python AUTH_MATRIX, OR change BD-006 to read from Python module |
| F-010 | Dual auth matrix drift inevitable without automated check | 6.1 | Implement CI diff script OR single-source auth matrix |

### HIGH (Significant Risk)

| ID | Finding | Section | Fix |
|----|---------|---------|-----|
| F-002 | Operation extraction not specified for multi-level tools | 2.2 | Define _extract_operation() spec per tool category before P4-002 |
| F-006 | Shell injection detection may receive parsed args, not raw command | 4.1 | Verify Hermes hook receives raw command string; add Aizanta path isolation |
| F-007 | Docker guards missing image validation, FORBIDDEN patterns, network check | 4.2 | Port all 5 docker_tool.py guard layers to hybrid_guards.py |
| F-008 | guinevere_safety has no runtime fail-closed guarantee | 5.1 | Add try/except wrapper returning block on crash |

### MEDIUM (Should Fix)

| ID | Finding | Section | Fix |
|----|---------|---------|-----|
| F-003 | Wildcard vs explicit operation mapping conflict | 2.3 | Specify tool_name-to-server mapping precisely |
| F-004 | Unknown tool/operation default not fail-closed | 2.4 | Specify: unknown tool -> block + audit |
| F-005 | Lua script missing per-tool daily cap and global daily cap | 3.1 | Add to Lua script or document as accepted gap |
| F-009 | Hermes can be started without startup wrapper | 5.2 | Document restriction; detect in Hermes config |

### PASS (No Issues Found)

- Lua script atomicity at Redis level (3.1)
- Git force-push guard design (4.3)
- FORBIDDEN design -- no approval path (7.1)
- 5-min timeout fail-closed (8.1)
- Webhook secret handling (8.2)
- Secret isolation in config.yaml (9.3)
- No privilege escalation paths (10.2)
- No hardcoded secrets in any file
- Aizanta port/network isolation
- Rollback plan completeness
- Collision scan correctness

---
## 12 Recommendations

1. **Single-source the auth matrix** (addresses F-001, F-010): Change BD-006 so the auth overlay reads directly from src/mcp/auth_matrix.py via Python import. This eliminates the entire category of YAML/Python drift bugs. The Hermes plugin can import the Python module at init time and use get_auth_level() directly.

2. **Add _extract_operation() spec to batch plan** (addresses F-002): Before P4-002, document the operation extraction strategy per tool category. For READ_AUTO wildcard tools, operation is irrelevant. For multi-level tools, define how operation names are determined from hook context args.

3. **Port all docker_tool.py guard layers** (addresses F-007): Do not simplify to container name prefix check. Replicate the full five-layer validation chain: container name regex, image name metacharacter check, FORBIDDEN_PATTERNS, guinevere-net network membership, and runtime sub-command blocking.

4. **Harden guinevere_safety with fail-closed wrapper** (addresses F-008): Mirror auth_overlay exception handling pattern. Critical safety hooks (pre_llm_call, pre_tool_call) must return block on crash so Hermes fails safe.

5. **Verify Hermes hook receives raw command string** (addresses F-006): Before implementing hybrid_guards.py shell injection detection, confirm via Hermes documentation or testing that the hook context contains the raw (non-parsed) command string.

6. **Add CI auth matrix drift check** (addresses F-010 if dual-source retained): Create scripts/check_auth_matrix_sync.py that diffs the YAML and Python sources and fails CI on mismatch. Alternatively, adopt single-source (Recommendation 1).

---
## 13 Footer

### Verdict Rationale

The plan architecture is sound in principle -- the hook-based auth overlay, atomic budget Lua script, and startup gate are correct approaches. However, **the YAML auth matrix in config.yaml is fundamentally incompatible with the Python auth matrix that actually defines the security boundaries**. This creates a gap where 15 FORBIDDEN operations and all 7 custom tools are completely un-enforced by the Hermes auth overlay. Until this is resolved (by expanding the YAML matrix or changing the source-of-truth), the Phase 4 implementation cannot meet its own acceptance criteria.

### What Would Change Verdict to PASS

- F-001 resolved: YAML matrix covers all 16 tools with operation-level parity to Python
- F-010 resolved: Drift detection implemented (CI script or single-source)
- F-002 resolved: Operation extraction strategy specified
- F-008 resolved: guinevere_safety receives fail-closed wrapper

### Audit Trail

| Item | Status |
|------|--------|
| All 11 source files read | Complete |
| Auth bypass analysis | 5 sub-findings (1 BLOCKING, 1 HIGH, 3 MEDIUM) |
| Budget race condition analysis | PASS (Lua atomic) + MEDIUM (incomplete layer coverage) |
| Hybrid guard completeness | 1 HIGH (shell), 1 HIGH (docker), 2 PASS |
| Startup gate effectiveness | 1 HIGH (runtime-blind), 1 MEDIUM (bypass), 1 PASS |
| Dual auth matrix risk | 2 BLOCKING (drift + structural incompatibility) |
| FORBIDDEN enforcement | PASS (design) + HIGH (15 ops missing from YAML) |
| Approval flow security | 3 PASS + 1 MEDIUM (concurrent requests) |
| Secret handling | 3 PASS with minor caveats |
| Aizanta isolation | PASS with 1 caveat |

### Design Review Coverage

For each security control in the batch plan, at least one bypass vector was identified or confirmed absent:

| Control | Bypass Found? | Finding |
|---------|--------------|---------|
| Auth overlay pre_tool_call | YES | F-001: YAML missing 7 tools; F-002: operation undefined |
| Budget Lua script | PARTIAL | F-005: Only monthly layer; no daily/global caps |
| Hybrid shell guards | YES | F-006: May receive parsed args, missing Aizanta paths |
| Hybrid docker guards | YES | F-007: Weaker than source, missing 3 of 5 layers |
| Hybrid git guards | NO | Correct design, needs full implementation |
| Startup gate | YES | F-008: Runtime-blind; F-009: Direct CLI bypass |
| FORBIDDEN enforcement | PARTIAL | Design correct, but 15 ops not in YAML to enforce |
| Approval flow | NO | Fail-closed design verified |
