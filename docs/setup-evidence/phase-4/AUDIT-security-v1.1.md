# Security Re-Audit — Phase 4 Batch Plan v1.1

| Field | Value |
|-------|-------|
| Auditor | Oracle (Security) |
| Target | `docs/setup-evidence/phase-4/batch-plan-phase-4.md` v1.1 (1034 lines) |
| Previous Verdict | NEEDS REVIEW (2 BLOCKING, 4 HIGH, 4 MEDIUM) |
| Re-Audit Verdict | **PASS** |
| Date | 2026-06-05 |

## Previous Findings Resolution

### BLOCKING

| ID | Original Finding | Resolution | Verified |
|----|-----------------|------------|----------|
| F-001 | YAML auth_matrix covers only 5/16 tools — 7 custom + 3 hybrid un-gated | BD-006 changed to single-source Python `auth_matrix.py` import. `get_auth_level()` with KeyError fail-closed. YAML marked reference-only. Verified `auth_matrix.py` has ALL 16 tools with complete operation mappings. | ✓ RESOLVED |
| F-010 | Dual-source drift without automated sync | Eliminated entirely. Single Python source. Caveat #2 documents YAML as reference-only and notes redirect requirement for any subsystem reading YAML independently. | ✓ RESOLVED |

### HIGH

| ID | Original Finding | Resolution | Verified |
|----|-----------------|------------|----------|
| F-002 | Operation extraction undefined | Full `_extract_operation()` spec table with 10 tool categories. Each has extraction method + examples. Unknown → `"__unknown__"` → fail-closed block. | ✓ RESOLVED |
| F-006 | Shell injection + missing Aizanta paths | Aizanta paths (`/home/aizanta`, `/etc/aizanta`, `/var/lib/aizanta`) added to both `filesystem.blocked_paths` in config.yaml AND `hybrid_guards.py` shell path checker. | ✓ RESOLVED |
| F-007 | Docker guards incomplete (3 of 5 layers) | Expanded from 1 to 5 layers: (1) container name regex, (2) image metacharacter rejection, (3) FORBIDDEN_PATTERNS, (4) guinevere-net network verify, (5) sub-command block. Verified against `docker_tool.py` source. | ✓ RESOLVED |
| F-008 | guinevere_safety no runtime fail-closed | Fail-closed wrapper spec added to P4-002. §7.3 amended: P4-002 may add try/except wrappers to existing hook registrations. pre_prompt crash → block, post_response crash → SEV-1 alert + block. | ✓ RESOLVED |

### MEDIUM

| ID | Original Finding | Resolution | Verified |
|----|-----------------|------------|----------|
| F-005 | Lua script only monthly cap (no daily) | Extended Lua script with per-tool daily caps + daily global cap. Three Redis keys: monthly, daily_tool, daily_global. Dual-write prevention: `hermes:cost:` prefix during shadow mode. | ✓ RESOLVED |
| F-009 | Hermes bypass without wrapper | Caveat #10: watchdog deferred to Phase 7. Compensated by startup gate (P4-006) + runtime fail-closed (auth_overlay exception handling + guinevere_safety wrapper). | ✓ RESOLVED |
| F-003 | Budget estimation accuracy | Unchanged. Documented as accepted limitation with conservative estimates (round up 20%). | ✓ Documented |
| F-004 | FastMCP sys.path hack | Unchanged. Deferred to Phase 7 (Hardening). | ✓ Documented |

## Additional Fixes Applied

| Fix | Description | Verified |
|-----|-------------|----------|
| Unknown tool fail-closed | auth_handler.py: KeyError → block + audit log. Explicit in Key Design Constraints. | ✓ |
| manifest.yaml naming | All references unified to manifest.yaml (was inconsistent between P4-002 and P4-006). | ✓ Fixed |
| fetch_url naming | Clarified: Hermes uses `fetch_url`, auth_matrix.py maps as `fetch`, `_extract_operation` handles mapping. | ✓ |

## New Issues Check

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| None | — | No new security issues found | — |

## Security Architecture Assessment

| Aspect | Assessment |
|--------|------------|
| Auth matrix completeness | ALL 16 tools, all operations, all 4 levels in single Python source |
| Fail-closed design | Unknown tool/operation → block. Plugin crash → block. Budget exceeded → block. |
| Aizanta isolation | Paths explicitly blocked in both config and runtime guards |
| Docker security | 5-layer guard matching production docker_tool.py |
| Budget enforcement | Monthly + per-tool daily + global daily caps in atomic Lua script |
| Rollback safety | Universal kill-switch (hermes gateway stop) before every rollback |

## Recommendation

**PASS.** Both BLOCKING findings eliminated by single-source auth matrix (BD-006). All 4 HIGH findings resolved with concrete specs. All 4 MEDIUM findings either resolved or documented as accepted limitations. No new security issues introduced.

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-05 | Oracle | Initial re-audit analysis |