# ADR-035 v1.2 Regression Audit Report

**Audit Date**: 2026-06-04
**Auditor**: Guinevere (Sisyphus-Junior)
**File Audited**: `adr/ADR-035-hermes-migration.md` (2,512 lines, fully read in 5 chunks)
**Purpose**: Verify no regressions from v1.1 edits — 15 regression checks

---

## Verdict: **NEEDS REVIEW (1/15 FAIL)**

Overall structural integrity is excellent. One method-naming regression found in the `GuinevereSafetyPlugin` class. All other checks PASS.

---

## Detailed Results

| # | Check | Status | Evidence |
|---|---|---|---|
| **1** | **MADR sections present** | **PASS** | All 17 required `##` headings found: Status (L43), Date (L47), Deciders (L51), Tags (L55), Risk Level (L59), Supersedes (L63), Related Documents (L67), Context (L88), Decision Drivers (L150), Considered Options (L169), Decision Outcome (L249), Consequences (L1250), Rollback Plan (L1329), Implementation Notes (L1417), Links (L1862), Review Record (L1882), Revision History (L2506). |
| **2** | **5 Pillars intact** | **PASS** | All 5 pillars present in Decision Outcome: Discord=MIGRATE (L238-239), Memory=HYBRID (L240), Safety=HOOKS+PLUGINS (L241), MCP=HYBRID (L242), LLM=RETAIN (L243). Each pillar has dedicated subsections with detailed migration tables. |
| **3** | **8 Phases (0-7)** | **PASS** | Implementation Notes contains Phase 0 through Phase 7: Phase 0 Security Remediation (L1183/1432), Phase 1 Safety Foundation (L1184/1442), Phase 2 Discord Gateway (L1185/1458), Phase 3 Memory Bridge (L1186/1468), Phase 4 MCP + Tools (L1187/1479), Phase 5 Skills + Persona (L1188/1487), Phase 6 LLM Routing (L1189/1493), Phase 7 Hardening + Monitoring (L1190/1499). Each phase has expanded detail tables with steps, dependencies, risk mitigations, and rollback triggers. |
| **4** | **Code reduction 31.2%/44.2%** | **PASS** | L1173: "Overall reduction: **31.2%** (8,057 lines). Reduction on affected code only: **44.2%** (8,057 of 18,238 affected lines)." L1177 explicitly notes the MASTER plan's 59% figure was based on inflated line counts and is INCORRECT. The 31.2%/44.2% values are the corrected data. NOT 59%. |
| **5** | **35 slash commands** | **PASS** | L96: "35 guild-scoped slash commands". L278: "35 slash commands → Hermes plugins". L344: "Command count: TOTAL: 35". Full migration table (L284-338) enumerates all 35: 8 HIGH feasibility, 15 MEDIUM feasibility, 12 LOW feasibility. L1901 notes the MASTER plan count of 33 is incorrect. NOT 33. |
| **6** | **Hook names corrected** | **PASS** | L110: correct hook names documented: `pre_prompt`, `post_prompt`, `pre_tool_call`, `post_tool_call`, `pre_response`, `post_response`, `on_error`. L363: explicit note that MASTER plan names (`pre_gateway_dispatch`, `pre_llm_call`, `transform_llm_output`, `transform_tool_result`) are INCORRECT. L1899: Review Record confirms correction. All hook config YAML examples (L389-567) use corrected names. Safety Compliance Matrix (L1663-1710) uses corrected names. NOT old names. |
| **7** | **GuinevereSafetyPlugin class** | **FAIL** | Class exists (L708) with `__init__` (L726) and `on_load` (L742). However, 3 of 8 expected method names do NOT match — they were renamed in v1.2:<br><br>**Present (5/8 match)**: `class GuinevereSafetyPlugin` ✓ (L708), `__init__` ✓ (L726), `on_load` ✓ (L742), `_check_yandere_boundary` ✓ (L1021), `_scan_forbidden_patterns` ✓ (L1047).<br><br>**Renamed (3/8 mismatch)**: `_check_hard_stop` → now `_handle_hard_stop` (L829), `_check_consent_gate` → now `_check_consent` (L860), `_scan_secret_patterns` → now `_scan_for_secrets` (L1037).<br><br>Grep confirmed: zero occurrences of `_check_hard_stop`, `_check_consent_gate`, or `_scan_secret_patterns` anywhere in the file. Functionally equivalent methods exist but naming regression from v1.1 expected names. |
| **8** | **Auth overlay config** | **PASS** | Appendix A config.yaml L1988-1997: `auth_overlay` plugin with `class: "AuthOverlayPlugin"`, `webhook_url: "${DISCORD_APPROVAL_WEBHOOK}"` (L1996), `approval_timeout_ms: 300000` (L1997). Plugin marked `critical: true` (L1993). Full auth overlay architecture documented at L1141-1143. |
| **9** | **Memory bridge config** | **PASS** | Appendix A config.yaml L1998-2008: `memory_bridge` plugin with `class: "MemoryBridgePlugin"`, `dnr_enabled: true`, `classification_fail_closed: true`. Bridge architecture documented in Pillar 2 (L584-606) including PostgreSQL primary authority rule and ADR-007 compliance. |
| **10** | **Appendix A (config.yaml)** | **PASS** (with caveats) | Appendix A exists (L1907-2213) with full config.yaml. Sections found: `agent` (L1916), `gateway` (L1926 — covers messaging), `plugins` (L1970), `hooks` (L2011+L2058), `memory` (L2103), `mcp_servers` (L2121 — covers tools), `model` (L2155 — covers llm), `budget` (L2167), `cron` (L2174), `observability` (L2201 — covers monitoring). **Caveats**: (a) Section names differ from checklist: `model` not `llm`, `mcp_servers` not `tools`, `gateway` not `messaging`, `observability` not `monitoring`; (b) No dedicated `loop` or `safety` top-level sections — agent loop is managed by loop plugins, safety is embedded in `guinevere_safety` plugin + hooks. |
| **11** | **Appendix B (auth matrix)** | **PASS** | Appendix B exists (L2215-2300): `auth_matrix.yaml` with all 12 tool categories (web, filesystem, terminal, git, fetch, postgres_tool, redis_tool, obscura_cdp, grep_app, context7, sequential_thinking, time_tools), each with sub-actions and 4-level auth assignments (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN). Includes approval webhook config and audit configuration. |
| **12** | **Appendix C (SOUL.md)** | **PASS** | Appendix C exists (L2302-2379): SOUL.md template with all required sections: Identity (L2309-2311), Address Rules (L2355-2362 with 5 address forms: Sayang, Good boy, Mine, Faiz, Never), Communication Instructions (L2364-2371 with language ratio, emoji, formatting, length rules), Prompt Injection Defense (L2373-2378 with untrusted content handling and trust hierarchy). Plus Core Constraints and Tone and Behavior sections. |
| **13** | **Appendix D (shadow runbook)** | **PASS** | Appendix D exists (L2381-2504): Shadow Mode Runbook with prerequisites, 8 sequential steps (Prepare → Configure Mutex → Launch → Monitor → Compare → Approval → Cutover → Emergency Rollback), and constraints (max 72hr duration, $5 cost cap, Redis DB5 vs DB4, no PostgreSQL writes). Checklist format includes bash commands and verification steps for each stage. |
| **14** | **ADR-022 note (Neonize)** | **PASS** | L116: "Hermes multi-platform gateway supports WhatsApp natively; however, ADR-022 (revised 2026-06-03) mandates **Neonize** (pure Python, whatsmeow CGo) for Guinevere's WhatsApp implementation, **rejecting the Baileys/Node.js bridge approach**." Explicitly mentions Neonize (not Baileys), with ADR-022 reference. L1269 repeats the Neonize note. Related Documents (L19-38) includes ADR-022. |
| **15** | **ADR-030 note (Redis DB)** | **PASS** | L146-148: "ADR-030 Redis DB Assignment Conflict" — full acknowledgment with concrete DB assignments: "current Guinevere codebase uses Redis DB4 for session cache and DB2 for consent cache. ADR-030 canonically assigns DB2=Surveillance buffer, DB3=Sessions, DB4=Pub/Sub, DB5=Rate limiting." Documents the runtime-vs-ADR discrepancy, explicitly states "This ADR does not propose new Redis DB assignments; it inherits the existing runtime state." Tracking item for post-migration cleanup. Related Documents includes ADR-030 (L36). |

---

## Summary

**14/15 checks PASS. 1/15 FAIL.**

### Regression Found (Check #7)

The `GuinevereSafetyPlugin` class (L708-1092) in v1.2 has three method names that do not match the expected v1.1 names:

| Expected (v1.1) | Actual (v1.2) | Line |
|---|---|---|
| `_check_hard_stop` | `_handle_hard_stop` | 829 |
| `_check_consent_gate` | `_check_consent` | 860 |
| `_scan_secret_patterns` | `_scan_for_secrets` | 1037 |

**Functional impact**: LOW. All three methods exist and implement the correct safety logic — only the names changed. `_handle_hard_stop` (L829-839) handles HARD STOP detection, `_check_consent` (L860-878) implements 7-step fail-closed consent verification, `_scan_for_secrets` (L1037-1045) runs 18 regex patterns + Shannon entropy scanning. No safety logic was lost.

**Recommendation**: If v1.1 tests or documentation reference these method names, they will break. Either (a) rename methods back to v1.1 names, or (b) update all cross-references to use the new names. The `_handle_hard_stop` rename (check→handle) is the most semantically different and most likely to cause confusion in safety gate test references.

### Structural Health

- All 17 MADR sections present and well-formed
- 5-pillar architecture intact with detailed migration tables
- 8 phases (0-7) fully expanded with step tables, dependencies, risks, and rollback triggers
- Code reduction figures correct: 31.2% net, 44.2% affected (NOT 59%)
- 35 slash commands correctly counted (NOT 33)
- All hook names use the corrected Hermes lifecycle names (NOT the MASTER plan names)
- All 4 appendices present and complete
- Cross-references to ADR-022 (Neonize) and ADR-030 (Redis DB) preserved

### Non-Regression Caveats (Check #10)

Appendix A config.yaml section names differ from the checklist names (`model` vs `llm`, `mcp_servers` vs `tools`, etc.) and two sections (`loop`, `safety`) lack dedicated top-level YAML keys. This is a naming convention difference between the audit checklist and the actual Hermes config schema — not a regression from v1.1 content loss. All functionality is covered in plugins, hooks, and other sections.

---

**Audit completed**: 2026-06-04 | File: `adr/ADR-035-hermes-migration.md` | Lines audited: 2,512 | Checks: 15 | Pass: 14 | Fail: 1