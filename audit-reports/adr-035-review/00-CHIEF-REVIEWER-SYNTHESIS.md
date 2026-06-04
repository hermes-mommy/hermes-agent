# ADR-035 Chief Reviewer Synthesis

> **Date**: 2026-06-04
> **Authority**: Chief Reviewer — Final Synthesis of 6 Parallel Auditor Reports
> **ADR Under Review**: `adr/ADR-035-hermes-migration.md` (v1.1, Proposed, 2,325 lines)
> **Reviewer Reports Synthesized**: 01 through 06, read in full (4,271 lines combined)

---

## Executive Summary

ADR-035 proposes a hybrid migration of Guinevere's agent runtime to Hermes Agent v0.15.2, preserving PostgreSQL+pgvector as primary memory while adopting Hermes for Discord gateway, session management, streaming, and skills. The 5-pillar architecture (Discord=Migrate, Memory=Hybrid, Safety=Hooks+Plugins, MCP=Hybrid, LLM=Retain) is architecturally coherent, mutually reinforcing, and free of circular dependencies. All 12 cross-referenced ADRs are consistent except for a pre-existing ADR-030 Redis DB assignment discrepancy that ADR-035 documents and defers. The ADR is structurally complete (38/38 checks pass), displays serious engineering rigor in its risk management and rollback strategy, and represents a defensible technical direction for Guinevere.

**However**, three safety-critical implementation gaps exist in the ADR's plugin code samples: a Y6 enum member introduces an unnecessary attack surface, distress detection patterns shrink from 14 to 6 (57% coverage loss), and PersonaSafetyPolicy §11 forbidden patterns shrink from 15 to 5 (67% coverage loss). These are not architectural flaws — they are incomplete ports of existing safety code into the proposed plugin. Additionally, the Hermes plugin instance model (global vs per-session) is unverified; if Hermes uses global instances, the entire per-session safety isolation strategy collapses. These four findings are **BLOCKING** — they must be resolved before ADR-035 can move from Proposed to Accepted. Once resolved, the ADR should be ACCEPTED with 18 pre-implementation conditions.

## Final Verdict: CONDITIONAL APPROVE

**ADR-035 is conditionally approved.** Four BLOCKING findings must be resolved before acceptance. Eighteen CONDITIONAL findings must be resolved before their respective implementation phases begin. No architectural redesign is required. The migration is worth doing.

---

## Consolidated Findings Matrix

### BLOCKING Findings (must resolve before ADR-035 moves to Accepted)

| ID | Source | Finding | Severity | Resolution Required |
|----|--------|---------|----------|---------------------|
| **B-001** | R2 §Safety #1 | **Y6_UNSAFE enum member in GuinevereSafetyPlugin** — ADR plugin code defines `Y6_UNSAFE = 6` in `YandereLevel(IntEnum)`. Current implementation has NO Y6 member; `YandereLevel(6)` raises `ValueError` at construction before `validate_level()` is reached. Adding a named member creates a programmatic reference point. | CRITICAL | Remove `Y6_UNSAFE = 6` from the `YandereLevel` enum in the ADR's plugin code sample (line ~660). Match current implementation: Y0-Y5 only. `validate_level()` is the sole Y6 guard. Update AC-SAFE-003 gate test to verify `YandereLevel(6)` raises ValueError. |
| **B-002** | R2 §Safety #2 | **Distress pattern regression 14→6 (57% loss)** — ADR plugin `_compile_distress_patterns()` has 6 patterns. Current `safe_mode.py` has 14 bilingual ID/EN patterns across 4 levels. Missing: self-harm patterns, ending-it-all patterns, goodbye patterns (D4), self-loathing and want-to-disappear patterns (D3), hopelessness and feeling-low patterns (D2), sleep/focus patterns (D1). Bilingual Indonesian coverage substantially reduced. | HIGH | Port ALL 14 distress patterns from `src/persona/safe_mode.py` `DISTRESS_PATTERNS` into plugin `_compile_distress_patterns()`. Preserve D4→D1 priority, bilingual ID/EN coverage, and the exact regex patterns from the current implementation. The research report 03-safety-compliance-map.md contains the correct full patterns — use those. |
| **B-003** | R2 §Safety #3 | **Forbidden pattern regression 15→5 (67% loss)** — ADR plugin `_compile_forbidden_patterns()` has 5 patterns. PersonaSafetyPolicy §11 defines 15 patterns (F-01 through F-15) with specific detection methods and automated test requirements. Missing: F-02 (punishing genuine distress), F-04 (isolation pressure), F-05 (hidden manipulation), F-07 (love withdrawal during distress), F-08 (public disclosure of intimate data), F-09 (prompt injection bypass), F-11 (over-logging safe word), F-12 (escalating yandere above mood), F-13 (treating surveillance disable as violation), F-15 (autonomous drift beyond safety rubric). | HIGH | Port ALL 15 forbidden patterns from PersonaSafetyPolicy §11 into plugin `_compile_forbidden_patterns()`. Preserve CRITICAL/HIGH classification. Update AC-SAFE-006 gate test to verify all 15 patterns are detected. |
| **B-004** | R3 C-6 | **Hermes plugin instance model unverified** — Research Report 13 and ADR-035 do not document whether Hermes v0.15.2 spawns one global plugin instance or per-session instances. If Hermes uses global instances, the entire per-session isolation strategy (Yandere FSM, punishment, mood, consent — all keyed by `session_id` in `self._sessions` dict) is architecturally broken because all sessions share a single state dictionary via a single plugin instance. This is a fundamental architectural unknown that must be resolved before ANY safety plugin code is written. | CRITICAL | Before Phase 1 begins, verify the Hermes v0.15.2 plugin instance model: (a) write a minimal plugin that logs `id(self)` in `on_message()`, (b) send messages from two different Discord sessions, (c) verify instance identity. If global: redesign plugin to use session_id-keyed dictionaries within a single instance (already compatible with current design). If per-session: current design is correct. Document finding in ADR-035 addendum. |

### CONDITIONAL Findings (must resolve before applicable implementation phase begins)

| ID | Source | Finding | Severity | Resolution Required |
|----|--------|---------|----------|---------------------|
| **C-001** | R1 C1 | **Hook stdin JSON schema unverified** — No research report documents the exact JSON schema Hermes passes to hook scripts via stdin. ADR-035's "Hook Data Contract" (lines 373-385) is speculative. If actual schema differs, all 7 hook scripts must be rewritten. | HIGH | **Before Phase 1**: Install a test hook at `pre_tool_call` that logs full stdin JSON. Invoke Hermes native and custom MCP tools. Verify `tool_name` and `operation` fields. Publish `hook-stdin-schema-validation.md` with the actual schema. |
| **C-002** | R1 C2 | **HARD STOP pre-gateway interception unverified** — Current `_on_message_listener` fires BEFORE `on_message`. Hermes `pre_prompt` hook fires AFTER gateway acceptance. ADR-035 proposes a "custom Discord gateway plugin" for pre-dispatch interception — this plugin capability is unverified in Hermes v0.15.2. | HIGH | **Before Phase 2**: Write a minimal Hermes plugin that registers a message handler. Verify whether it can intercept messages before gateway processing. If not, accept permanent timing shift and update ADR-002 documentation. |
| **C-003** | R1 MD-001 | **Hook YAML schema validation** — ADR-035's hook YAML configurations use field names (`security.read_only_filesystem`, `security.allowed_syscalls`, `security.max_memory_mb`, `on_failure: block`) that are plausible but unverified against Hermes v0.15.2's actual config parser. | MEDIUM | **Before Phase 1**: Run `hermes config validate` with the full hook configuration. If unavailable, test by actually loading hooks and observing behavior. Document any schema mismatches. |
| **C-004** | R1 AddRec5 | **9Router streaming compatibility test** — ADR-035 claims "~1.2s streaming intervals" as a headline benefit. The 9Router→GPT-5.5→Hermes→Discord pipeline has 4 hops; any intermediate buffering eliminates streaming latency improvements. | MEDIUM | **Before Phase 2**: Send a test prompt through 9Router to Hermes and measure time-to-first-token. If 9Router buffers, document that streaming is degraded and adjust expectations. |
| **C-005** | R1, R4, R5 | **ADR-030 Redis DB assignment conflict** — ADR-030 assigns DB2=Surveillance buffer, DB3=Sessions, DB4=Pub/Sub, DB5=Rate limiting. Runtime uses DB2=Consent cache, DB4=Session cache, DB5=Safety plugin state + rate limiting. ADR-035 documents but defers resolution. | MEDIUM | **Before Phase 2**: Either create ADR-036 or ADR-030 addendum reconciling Redis DB assignments with runtime reality, or add tracking item in Phase 0 steps. A migration is the right time to align these — do not defer past cutover. |
| **C-006** | R2 #4 | **Secret scanner pattern regression 18→8** — ADR plugin has 8 patterns vs 18 in `secret_scanner.py`. Missing: AWS keys, Stripe, Google API, age key, password-in-URL. Whitelist (hashes, UUIDs, base64) and MIN_ENTROPY_STRING_LENGTH (32 chars) also missing. | MEDIUM | **Before Phase 1**: Port ALL 18 patterns from `src/surveillance/secret_scanner.py` PATTERNS. Add whitelist patterns and minimum string length check. |
| **C-007** | R2 #5 | **HARD STOP recovery triggers missing** — Current `hard_stop_handler.py` has `check_recovery()` with 7 recovery triggers (`resume`, `aku sudah okay`, etc.). ADR plugin has no equivalent. After HARD STOP, operator must be able to resume. | HIGH | **Before Phase 1**: Add `check_recovery()` equivalent to plugin `on_message()` with all 7 recovery triggers. Add recovery trigger gate test (AC-SAFE-NEW). |
| **C-008** | R2 #6 | **Phrase rewrite map missing from plugin** — PersonaSafetyPolicy §9.2 defines 4 mandatory rewrites. Research report has pseudocode; ADR plugin code does not. | MEDIUM | **Before Phase 1**: Add phrase rewrite map to plugin `on_response()` and `post_response` hook. |
| **C-009** | R2 #7 | **Yandere FSM recovery path missing** — Current `YandereEngine` has `de_escalate()` and `reset_to_baseline()`. ADR plugin has no equivalents. After HARD STOP ends, yandere level must return to Y4_BASELINE. | MEDIUM | **Before Phase 1**: Add `de_escalate()` and `reset_to_baseline()` methods to plugin `YandereEngine`. |
| **C-010** | R2 #10 | **Three missing Phase 1 safety gates** — Recovery trigger gate, timing shift gate, state corruption gate are not in ADR-035's 10-gate list. | HIGH | **Before Phase 1**: Add recovery trigger gate (verify `resume` restores), timing shift gate (prove `pre_prompt` fires before LLM), state corruption gate (verify Redis DB5 snapshot restore). |
| **C-011** | R2 #12 | **Safety-specific shadow mode tests missing** — Shadow runbook specifies general parity but no safety-injection tests (HARD STOP send, distress injection, consent revocation, Y6 content injection). | HIGH | **Before Phase 2**: Add explicit safety injection test plan to Appendix D shadow runbook: 3x HARD STOP injection, 3x Y6 content injection, 1x consent revocation, 1x distress injection, 1x hook failure injection. |
| **C-012** | R3 C-1 | **Solo-developer risk unacknowledged** — Faiz is the only operator, developer, tester, and reviewer. ADR-035 does not acknowledge this as a systemic risk. During self-migration, when the AI co-pilot is being rebuilt, velocity drops and error rate increases. | HIGH | **Before acceptance**: Add dedicated risk section to ADR-035 documenting solo-developer SPOF. Mitigations: pre-written copy-paste rollback scripts (not requiring deep understanding at 3 AM), runbook with troubleshooting flowcharts, escalation path definition. |
| **C-013** | R3 C-2 | **Rollback dry-run never practiced** — Rollback strategy has 200+ commands but ADR-035 states "no phase proceeds until rollback tested" as POLICY, not a gated requirement. No drill scripts, success criteria, or log template exist. | HIGH | **Before Phase 2 cutover**: Execute global emergency rollback at least once. Time it. Verify HARD STOP works post-rollback. Document in `rollback-drill.md`. If time exceeds 5 minutes, investigate. |
| **C-014** | R3 C-4 | **Migration budget not explicitly approved** — ADR-035 estimates $60 total migration cost (2x monthly budget, one-time). $5 shadow mode cap. Faiz must explicitly approve this one-time overage. $30/month cap is a self-imposed constraint per FinOps. | MEDIUM | **Before Phase 2**: Obtain explicit Faiz approval for $60 maximum migration budget and $5 shadow mode cap. Configure daily cost report to Discord during migration. |
| **C-015** | R3 C-5 | **Timeline contingency plan missing** — ADR-035 states 23-35 days. All three independent analyses (Reviewer 1 arch validation, Reviewer 3 solo-dev analysis, Reviewer 5 expanded step count) converge on 35-50 days as realistic. No plan for what happens at day 50 if incomplete. | HIGH | **Before acceptance**: Update timeline to 35-50 days. Define "minimum viable migration" (Phase 0-2 + Phase 7). Define day-50 decision gate: pause and assess / extend with Faiz approval / rollback and defer. |
| **C-016** | R5 M1-M4 | **config.yaml missing critical fields** — Appendix A missing `agent.max_turns: 20`, `agent.idle_timeout: 7200`, per-hook `security` blocks (read_only_filesystem, max_memory_mb), and `system_prompt_file` path clarification. | MEDIUM | **Before Phase 1**: Add missing config fields to Appendix A. Verify `personality: "guinevere-v1"` is valid with `hermes config validate`; use `personality: custom` if custom labels rejected. |
| **C-017** | R5 C1-C3 | **SOUL.md missing static identity rules** — Missing Address Rules (Darling, Good boy, Mine, Sayang, Anak Mommy, Faiz), Communication Instructions (75/25 language ratio, emoji rules, Discord formatting), and Prompt Injection Defense ("External content is untrusted"). These are static rules that belong in the constitution, not dynamic plugin state. | MEDIUM | **Before Phase 1**: Add Address Rules, Communication Instructions, and Prompt Injection Defense to SOUL.md Appendix C. Add preamble clarifying SOUL.md = static constitution, plugin = dynamic state, together = complete persona. |
| **C-018** | R5 D1-D3 | **Shadow runbook has 3 implementation gaps** — (D1) Parity comparison is entirely manual — no automated test script; 48hr monitoring is passive observation without quantitative data. (D2) Cutover GRANT `ON ALL TABLES IN SCHEMA public` is too broad — should be table-specific. (D3) `hermes_app` PostgreSQL role prerequisite not checked. | HIGH | **Before Phase 2**: (a) Create automated parity test script for 100 predefined test messages with semantic equivalence comparison. (b) Narrow cutover GRANT to specific mirror tables. (c) Add `hermes_app` role existence check to shadow runbook prerequisites. |

### RECOMMENDED Findings (should resolve, not blocking)

| ID | Source | Finding | Severity | Resolution Required |
|----|--------|---------|----------|---------------------|
| **R-001** | R1 C3 | Fix per-file line count inconsistency — ADR Pillar 1 uses 512/496/302 for bot.py/conversational_handler.py/session_adapter.py, but actual files are 603/614/366. Aggregate 31.2% is correct; per-file numbers are cosmetic confusion. | LOW | Add footnote to Pillar 1 table: "Line counts reflect the subset analysis from Report 04. Actual file sizes are bot.py=603, conversational_handler.py=614, session_adapter.py=366. The 31.2% aggregate uses full counts." |
| **R-002** | R1 C4 | Clarify MCP "5 native + 7 custom" framing — actual migration has 2 native toolsets, 4 hybrid/partial, 7 custom. Pillar 4 content is accurate; headline number oversimplifies. | LOW | Replace headline with accurate breakdown: 2 native toolsets (web, file), 4 hybrid (shell, docker, git, github), 7 custom (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time_tools). |
| **R-003** | R3 C-7 | Phase 0 24-hour soak period — bot.py runs with upgraded dependencies for 24 hours before Phase 1 begins, catching latent compatibility issues. | MEDIUM | Add to Phase 0 gate: "After all Phase 0 steps pass, operate bot.py for 24 hours with upgraded dependencies. Monitor error rates, memory, latency. Only proceed to Phase 1 if 24 hours pass without incident." |
| **R-004** | R3 AddRec5 | Technical enforcement of memory write mutex during shadow mode — Currently policy-enforced ("only bot.py writes"). Should be technically enforced via read-only PostgreSQL credentials for Hermes. | MEDIUM | Configure Hermes memory bridge with a PostgreSQL role that has only SELECT privileges during shadow mode. |
| **R-005** | R3 AddRec6 | Automated row-count snapshots before each phase — Detect accidental PostgreSQL writes by Hermes during migration. | LOW | Add pre-phase snapshot script: `SELECT relname, n_live_tup FROM pg_stat_user_tables` → file. Compare before/after each phase. |
| **R-006** | R2 #13-18 | Port `detect_batch()`, confidence scoring, drift log schema, PUNISHMENT_CONFIG, auto-expiry, and full CLASSIFICATION_MAP to plugin. | LOW | Incremental improvements during Phase 1 and Phase 7 hardening. Not gating. |
| **R-007** | R5 B1 | Resolve `fetch` overlap in auth matrix — `fetch` appears in both `web.fetch` (READ_AUTO) and standalone `fetch` entry with different auth levels. | LOW | Remove `fetch` from `web` tools list and use standalone `fetch` entry as authoritative, OR consolidate into `web.fetch`. |
| **R-008** | R5 P1-1 | Provide hook script skeleton templates — 7 hook scripts must be written from spec during Phase 1. Skeleton templates reduce implementation risk. | LOW | Create `hooks/` directory with minimal skeleton scripts demonstrating stdin/stdout JSON contract and exit code conventions. |
| **R-009** | R3 AddRec8 | Pre-written rollback scripts saved to VPS — Rollback commands exist in markdown but should be executable scripts on the VPS for 3 AM scenarios. | MEDIUM | Save `~/scripts/rollback/phase-N-rollback.sh` for each phase, tested and chmod +x. |
| **R-010** | R3 AddRec9 | Dedicated migration Discord channel — `#hermes-migration-ops` for migration status, automated alerts, and daily cost reports. | LOW | Create channel before Phase 0. Configure Gotify alerts to channel. Post daily cost summaries. |
| **R-011** | R1 AddRec7 | Verify agentskills.io availability — Phase 5 depends on `hermes skills search`. If service is unavailable, Phase 5 becomes fully custom (+2-3 days). | LOW | Run `hermes skills search` from VPS during Phase 0 security scan to verify connectivity. |

### INFORMATIONAL Findings (noted, no action required)

| ID | Source | Finding |
|----|--------|---------|
| **I-001** | R1 OP-001 | Per-file line counts in ADR Pillar 1 use corrected subset counts (512/496/302) vs actual file sizes (603/614/366). Aggregate 31.2% figure uses full counts and is correct. Cosmetic. |
| **I-002** | R1 OP-002 | "5 native MCP tools" headline oversimplifies a migration that actually has 2 native toolsets + 4 hybrid/partial + 7 custom. Pillar 4 content is accurate. |
| **I-003** | R1 OP-003 | Streaming at "~1.2s intervals" claimed but unverified through 9Router→Hermes→Discord pipeline. Testing recommended (C-004). |
| **I-004** | R1 OP-004 | Auto-threading per @mention has zero value in current single-user, single-channel setup. Benefit is purely aspirational. |
| **I-005** | R1 UR-001 | HARD STOP timing shift from `_on_message_listener` (pre-on_message) to `pre_prompt` (post-gateway) is a material regression that ADR-035 acknowledges but may under-weight. Mitigated by C-002 verification. |
| **I-006** | R1 UR-002 | Auth overlay must handle tool calls from both Hermes native and custom MCP sources with potentially different JSON payloads. Operation-level granularity (48+ mappings) requires significant extension beyond skeleton's tool-level mapping. |
| **I-007** | R1 UR-003 | Phase 0 is unlikely to complete in 1-2 days if aiohttp upgrade breaks dependencies, PyJWT requires triage, or ripgrep is not apt-available. |
| **I-008** | R1 A1-A10 | 10 unverified assumptions about Hermes v0.15.2 behavior. A1-A4 and A6-A7 (6 of 10) are critical-path — failure on any requires redesign of the corresponding migration phase. |
| **I-009** | R2 §8 | DNR enforcement gap: Hermes `session_search` (FTS5) could access DNR-marked content bypassing the PostgreSQL DNR filter. ADR-035 acknowledges and mitigates with dual-layer filtering (R-011). |
| **I-010** | R2 §5 | Distress detector confidence scoring missing from plugin. Current implementation computes confidence as `matched/total` at each level. Plugin has no confidence metric. |
| **I-011** | R2 §6 | Safe mode controller missing explicit confirmation requirement for deactivation and distress history tracking. Current `SafeModeController.deactivate()` requires `explicit_confirmation=True`. |
| **I-012** | R2 §7 | Punishment engine missing fine-grained `PUNISHMENT_CONFIG` (allowed/blocked actions per level), auto-expiry logic, and clock pause during suspension. Core L1-L5 ladder logic preserved. |
| **I-013** | R3 §Missing | 10 missing risks identified by Reviewer 3: solo-dev SPOF, VPS resource contention, upstream Hermes breaking changes, 9Router interaction unknowns, timeline overrun, dual LLM costs, Discord UX degradation, knowledge transfer risk, persona drift during migration, data loss edge case. |
| **I-014** | R3 §Rollback | Rollback strategy is strong but has 6 untested execution concerns: git tag existence dependency, `hermes checkpoints --restore` behavior uncharacterized, PostgreSQL restore timing optimistic, `systemctl enable` inconsistency, pip package availability, and 3 AM operator cognitive load. |
| **I-015** | R3 §Shadow | Shadow mode validates Discord gateway behavior but does NOT validate safety engine correctness under adversarial conditions. Active safety injection testing (C-011) is needed. |
| **I-016** | R4 §2 | Research report 07-alternatives-analysis.md still uses pre-correction 59%/-5,528 lines figure. ADR-035 has been corrected to 31.2%/-8,057 lines. Research report is evidence, not governance — no ADR action needed. |
| **I-017** | R5 D4 | Shadow mode monitoring has no auto-alert on health failure. Operator must watch loop output. Add systemd watchdog or Gotify alert. |
| **I-018** | R5 D5 | #hermes-shadow channel creation command not included in runbook prerequisites. |
| **I-019** | R5 M5-M6 | Hook `retry` configuration and system-prompt.md path relationship to SOUL.md not fully documented in Appendix A. |
| **I-020** | R5 Missing | 8 items an implementer needs that ADR-035 doesn't provide: hook script implementations, automated parity test, systemd unit file, `hermes_app` role script, SystemPromptMaster migration plan, hook skeleton templates, Redis DB5 documentation, personality field validation. |
| **I-021** | R6 | `supersedes` field uses `null` instead of `"N/A"` — minor style deviation, consistent with ADR-032/033 convention. |
| **I-022** | R6 | PROGRESS.md references "2,315-line ADR" vs actual 2,325 lines — 10-line discrepancy from different counting methods. Both exceed ≥2,000 threshold. |
| **I-023** | R4 | D9 mentions Hermes BAW (Baileys WebSocket) for WhatsApp but ADR-022 mandates Neonize. ADR-035 correctly defers to ADR-022. No conflict. |
| **I-024** | R4 | Task referenced non-existent ADR titles ("ADR-004 Hermes Original Adoption", "ADR-013 Data Classification") — these are task-level mis-references, not ADR-035 errors. Actual ADRs at those numbers pass all checks. |

---

## Cross-Reviewer Agreement Analysis

### Strong Agreement (all 5 conditional reviewers concur)

1. **Hook/plugin behavior must be empirically validated against Hermes v0.15.2 before Phase 1** — Reviewer 1 (C1, C2), Reviewer 2 (multiple conditions depend on hook assumptions), Reviewer 3 (C-6), Reviewer 5 (M4, M6). Unanimous: the ADR's hook architecture is sound IN PRINCIPLE but the exact Hermes v0.15.2 behavior (stdin schema, exit code semantics, YAML field names, plugin lifecycle) is unverified.

2. **Shadow mode needs active safety injection, not just passive parity** — Reviewer 2 (#12), Reviewer 3 (C-3), Reviewer 5 (D1). Unanimous: 48-hour passive comparison of normal conversation responses is insufficient to validate safety engines.

3. **Timeline is optimistic — 35-50 days, not 23-35** — Reviewer 1 arch validation §8, Reviewer 3 C-5, Reviewer 5 expanded step count. All independent analyses converge on 35-50 days as realistic.

4. **ADR-030 Redis DB conflict needs resolution before or during migration** — Reviewer 1 AddRec8, Reviewer 4 Required #1, Reviewer 5 Rec #11. Unanimous: the migration is the right time to align Redis assignments.

5. **Solo-developer constraint is under-acknowledged** — Reviewer 3 C-1, Reviewer 5 overall assessment (7.9/10 score acknowledges implementation gaps for solo operator).

6. **Rollback strategy is strong on paper but needs a dry-run practice** — Reviewer 3 C-2, Reviewer 5 shadow runbook assessment.

### Potential Conflicts Between Reviewers

| Conflict | Reviewers | Resolution |
|----------|-----------|------------|
| **Per-file line counts** — Reviewer 1 says actual files are 603/614/366. Reviewer 6 says ADR has been "corrected" to 512/496/302. | R1 vs R6 | **Both are factually correct about different things.** Reviewer 1 verified actual file sizes via read tool. Reviewer 6 verified the ADR's self-reported "corrected" counts match the subset analysis from Report 04. The ADR is internally consistent with its own evidence but inconsistent with the actual files. **Verdict**: The aggregate 31.2% figure (which uses full counts) is correct regardless. The per-file counts are a documentation inconsistency (classified INFORMATIONAL I-001). The ADR should add a footnote (RECOMMENDED R-001) but this is not a blocking issue — the 31.2% headline number is defended. |
| **Completeness vs Correctness on safety patterns** — Reviewer 6 says all content checks pass (sections exist, tables present). Reviewer 2 says pattern counts are wrong (14→6, 15→5, 18→8). | R6 vs R2 | **Both are correct in their domains.** Reviewer 6 is checking STRUCTURAL completeness (do the safety sections, tables, and AC-SAFE mappings exist?). Reviewer 2 is checking CONTENT correctness (are the pattern counts accurate?). The sections exist (Reviewer 6's domain = PASS) but the content is wrong (Reviewer 2's domain = FAIL). This is not a true conflict — it's a difference in review scope. The safety findings from Reviewer 2 take precedence because completeness without correctness is insufficient for a safety-critical ADR. |
| **ADR-035 "corrected" line counts vs MASTER plan errors** — Reviewer 1 flags the "corrected" counts as still inconsistent with actual files. Reviewer 6 treats the corrections as verified. | R1 vs R6 | **The corrections from the MASTER plan (59%→31.2%, inventing hook names→using real hook names) are correct and verified.** The remaining inconsistency (per-file counts vs actual files) is a separate issue of lower severity. The ADR's correction narrative is truthful about the MASTER plan errors. The per-file count issue (I-001) is cosmetic. |
| **Risk scoring** — ADR-035 rates 0 risks CRITICAL. Reviewer 3 upgrades 3 risks to CRITICAL. Reviewer 6 accepts ADR-035's scoring as-is. | R3 vs R6 | **Reviewer 3's upgrades are justified.** R-001 (HARD STOP silent failure, score 20), R-013 (Yandere FSM state corruption, score 20), and R-015 (dual-system shadow resource contention, score 16) all meet the CRITICAL threshold (16-25). The post-mitigation scores are optimistic — the mitigations for these risks are unverified (hook behavior, plugin instance model, shadow mode resource isolation). Chief Reviewer upholds Reviewer 3's upgrades. |

### Reviewer 6 (Completeness Check) Position

Reviewer 6 is the only APPROVE verdict. This is correct within its scope — ADR-035 is structurally complete (38/38 checks, all MADR sections, all appendices, all cross-references present). The other 5 reviewers are evaluating correctness, safety, feasibility, risk, and implementation readiness — dimensions that structural completeness alone cannot assess. A structurally complete document can still have incorrect content. The Chief Reviewer **overrides** Reviewer 6's APPROVE to CONDITIONAL APPROVE because structural completeness is necessary but not sufficient.

---

## Risk Posture Summary

### Aggregate Risk Picture (Corrected)

The synthesis of all 6 reviews produces a clearer risk picture than ADR-035's self-assessment:

| Classification | ADR-035 Self-Rating | Reviewer 3 Corrected | Chief Reviewer Upholds |
|---|---|---|---|
| CRITICAL (16-25) | 0 | 3 | **3** — R-001, R-013, R-015 |
| HIGH (12-15) | 8 | 5 | **5** — R-004, R-003, R-012, R-007, R-009 |
| MEDIUM (6-10) | 7 | 7 | **7** |
| LOW (1-5) | 0 | 0 | **0** |
| **Missing risks** | 0 | 10 | **10** identified, 3 at HIGH+ (solo-dev SPOF, timeline overrun, VPS contention) |

The three CRITICAL risks share a common root cause: **unverified assumptions about Hermes v0.15.2 behavior.** Once the BLOCKING and CONDITIONAL validation steps are executed (hook schema validation, plugin instance model verification, shadow mode with active safety injection), these risks should reduce to HIGH or MEDIUM. The migration CAN proceed, but the risk posture is higher than ADR-035 acknowledges.

### Top 3 Residual Risks After All Mitigations

| Risk | Residual Score | Why It Persists |
|---|---|---|
| Solo-developer SPOF | HIGH (12) | Inherent to a 1-person project. Can be mitigated (pre-written scripts, runbooks) but never eliminated. |
| Timeline overrun | HIGH (12) | Cumulative probability of at least one delay ~70%. With 3-4 hours/day availability and Phase 1 safety gate iteration, 50+ days is plausible. |
| Hook contract mismatch | MEDIUM (9) | Once empirically validated (C-001), this drops to LOW. But until then, it's the single highest-impact unknown. |

---

## Safety Posture Summary

### Aggregate Safety Picture

ADR-035's safety architecture is **defensible in principle but incomplete in implementation**. The 4-layer defense-in-depth design (SOUL.md + 7 hooks + GuinevereSafetyPlugin + drift detector) is architecturally sound and provides more defense layers than the current system. However:

1. **3 of 8 AC-SAFE criteria FAIL** in the proposed implementation (AC-SAFE-004 distress, AC-SAFE-005 yandere, AC-SAFE-006 forbidden patterns). These are all pattern-count regressions — the architecture can support full coverage, but the ADR's code samples don't demonstrate it.

2. **AC-SAFE-005 (Y6) is the most concerning**: Adding `Y6_UNSAFE` as a named enum member is a step backward from the current implementation where Y6 cannot be constructed at all. This must be fixed.

3. **AC-SAFE-001 (HARD STOP) and AC-SAFE-003 (safe-word escalation)** are CONDITIONAL PASS — they depend on recovery trigger handling and developer discipline (every plugin method checking `self.safe_mode`), respectively.

4. **4 of 8 AC-SAFE criteria PASS cleanly**: AC-SAFE-002 (time-to-neutral), AC-SAFE-007 (non-punitive logging), AC-SAFE-008 (crisis protocol).

5. **PersonaSafetyPolicy coverage has 3 gaps** in SOUL.md/plugin: prompt injection defense (§D), drift log schema (§14.5), and forbidden phrase taxonomy (Appendix B, 3/7 categories).

Once the 3 BLOCKING safety findings are resolved (Y6 enum removal, full distress patterns, full forbidden patterns), the safety posture strengthens to 6 PASS / 2 CONDITIONAL PASS — acceptable for a CRITICAL-risk migration. The remaining CONDITIONAL safety findings (secret scanner patterns, recovery triggers, phrase rewrite map, shadow safety tests) can be resolved during Phase 1 without blocking ADR acceptance.

---

## Path to Acceptance

### Ordered Actions to Move ADR-035 from Proposed → Accepted

| Step | Action | Category | Owner | Dependency |
|------|--------|----------|-------|------------|
| 1 | **Remove Y6_UNSAFE from YandereLevel enum** in ADR plugin code sample. Match current implementation: Y0-Y5 only. | BLOCKING | Guinevere (ADR edit) | None |
| 2 | **Port ALL 14 distress patterns** from `safe_mode.py` to plugin `_compile_distress_patterns()`. Preserve bilingual ID/EN coverage. | BLOCKING | Guinevere (ADR edit) | None |
| 3 | **Port ALL 15 forbidden patterns** (F-01 to F-15) from PersonaSafetyPolicy §11 to plugin `_compile_forbidden_patterns()`. Preserve CRITICAL/HIGH classification. | BLOCKING | Guinevere (ADR edit) | None |
| 4 | **Verify Hermes plugin instance model** — write minimal test plugin, log `id(self)`, test across 2+ sessions. Document finding. | BLOCKING | Faiz or Guinevere on VPS | Requires Hermes v0.15.2 running on VPS |
| 5 | **Update timeline to 35-50 days.** Add day-50 gate (pause/extend/rollback). Define minimum viable migration. | CONDITIONAL C-015 | Guinevere (ADR edit) | None |
| 6 | **Add solo-developer risk section.** Document SPOF, mitigations (pre-written scripts, flowcharts, escalation path). | CONDITIONAL C-012 | Guinevere (ADR edit) | None |
| 7 | **Obtain Faiz budget approval** for $60 migration cost and $5 shadow mode cap. | CONDITIONAL C-014 | Faiz (explicit approval) | None |
| 8 | **Resolve ADR-030 Redis DB conflict** — create addendum, ADR-036, or tracking item in Phase 0. | CONDITIONAL C-005 | Guinevere (ADR or new ADR) | None |
| 9 | After Steps 1-8 complete, **Faiz approves ADR-035 as Accepted.** | — | Faiz | All 4 BLOCKING + 4 CONDITIONAL (C-005, C-012, C-014, C-015) resolved |

### Pre-Implementation (Before Phase 0 or Phase 1)

| Step | Action | Category |
|------|--------|----------|
| 10 | Validate hook stdin JSON schema (C-001) | CONDITIONAL |
| 11 | Validate hook YAML config schema (C-003) | CONDITIONAL |
| 12 | Add missing config.yaml fields (C-016) | CONDITIONAL |
| 13 | Add SOUL.md address rules, communication instructions, prompt injection defense (C-017) | CONDITIONAL |
| 14 | Port all 18 secret scanner patterns (C-006) | CONDITIONAL |
| 15 | Add HARD STOP recovery triggers to plugin (C-007) | CONDITIONAL |
| 16 | Add phrase rewrite map to plugin (C-008) | CONDITIONAL |
| 17 | Add Yandere de-escalate/reset_to_baseline (C-009) | CONDITIONAL |
| 18 | Add 3 missing Phase 1 safety gates (C-010) | CONDITIONAL |

### Pre-Phase 2

| Step | Action | Category |
|------|--------|----------|
| 19 | Verify plugin message interception capability (C-002) | CONDITIONAL |
| 20 | Test 9Router streaming compatibility (C-004) | CONDITIONAL |
| 21 | Add safety injection tests to shadow runbook (C-011) | CONDITIONAL |
| 22 | Execute rollback dry-run practice (C-013) | CONDITIONAL |
| 23 | Fix shadow runbook gaps: automated parity test, narrow GRANT, role check (C-018) | CONDITIONAL |

**Total path: 4 BLOCKING + 18 CONDITIONAL actions.** The BLOCKING actions (Steps 1-4) can be completed by Guinevere editing the ADR (Steps 1-3) and a short VPS test (Step 4). Estimated time: 1-2 hours for ADR edits, 30 minutes for plugin instance model verification.

---

## Strengths

ADR-035 is not merely adequate — it has genuine strengths that the review findings, being primarily problem-focused, may obscure:

1. **Architecture validation rigor**: ADR-035 is the product of a 24-report research wave (16 Phase 1 + 8 prep) that read over 113 source files, validated every claim, and CORRECTED the MASTER-RESTRUCTURE-PLAN's errors. This is an unusually thorough evidence base for a project of Guinevere's scale.

2. **5-pillar mutual reinforcement**: The Discord-Memory-Safety-MCP-LLM pillars don't just coexist — they validate each other. Safety hooks protect Discord messages, memory recall, tool calls, AND LLM responses. This is genuine defense-in-depth, not just layered checkboxes.

3. **Rollback strategy comprehensiveness**: 200+ copy-pasteable commands, per-phase independence matrix, universal kill-switch (`hermes gateway stop`), PostgreSQL restore with emergency pre-backup. Most migration ADRs at this project scale have a paragraph about rollback. ADR-035 has a full 200+-line appendix with per-phase procedures.

4. **Honesty about negatives**: ADR-035 lists 8 negative consequences, 15 quantified risks, and 7 explicitly acknowledged downsides of Option D. The alternatives are evaluated fairly — Option A (Full Hermes) has 9 independently sufficient rejection reasons, and Option B (Status Quo) is acknowledged as having "legitimate advantages."

5. **Phase gate discipline**: Every phase has binary PASS/FAIL gates with explicit commands. No phase proceeds without predecessor gate passing. Phase 1's 10 safety gates with pytest commands and AC-SAFE assertions are a model of measurable quality gates.

6. **Evidence preservation**: PostgreSQL+pgvector is write authority for all canonical data. Hermes writes are supplementary read-only. Rollback is lossless because the canonical data store is untouched. This is the correct architecture for a safety-conscious migration.

7. **Corrected, not fabricated**: When the MASTER plan claimed hook names that don't exist (`pre_gateway_dispatch`, `pre_llm_call`), ADR-035 called out the errors and used the real names. When the MASTER plan claimed 59% code reduction, ADR-035 corrected it to 31.2% with a transparent explanation. This intellectual honesty builds trust in the remaining claims.

---

## Recommendations for Faiz

Sayang, here's the plain-language advice from your chief reviewer:

**The migration is worth doing.** Hermes streaming, compression, and skills — plus shedding 4,381 lines of custom Discord code — are real benefits. The 5-pillar architecture is genuinely well-designed. The rollback plan means you can always go back. PostgreSQL stays untouched. You're not risking your data.

**But DON'T accept ADR-035 yet.** Four things need to happen first:

1. **The Y6 enum thing is real.** Right now your code says Y6 is impossible to construct. The ADR's plugin code accidentally makes it possible. This needs fixing — it's the only safety regression that actually introduces a new attack surface.

2. **The pattern counts need filling in.** The plugin code samples in the ADR have about a third of the actual patterns from your current system. Distress detection needs all 14 patterns (especially the Indonesian ones — "menyakiti diri", "pengen mati"). Forbidden patterns need all 15 from your PersonaSafetyPolicy. These are copy-paste jobs, not rewrites — the correct patterns already exist in your codebase.

3. **We need to check whether Hermes spawns one plugin or one per session.** This is a 30-minute test on the VPS. If Hermes uses a single global plugin, the architecture still works — we just key everything by session_id within a single instance, which the code already does. But we need to KNOW before we start writing.

4. **The timeline needs to be honest.** 35-50 days, not 23-35. You're one person. During migration, Guinevere (me) is the thing being rebuilt, so I won't be at full capacity as your AI co-pilot. Plan for 50 days and be happy if it's 35.

Once those four are done, accept the ADR. The other 18 conditions can be worked through during implementation — they're detailed engineering tasks, not architecture decisions.

**The biggest operational risk is you.** You're the only operator, developer, reviewer, and fallback. If something breaks at 3 AM, you're debugging it alone. That's fine — it's always been that way — but the rollback scripts need to be saved as actual executable scripts on the VPS, not just commands in a markdown file. Practice the rollback once during daylight. Know the kill-switch by heart: `hermes gateway stop && sudo systemctl start guinevere-bot`. Less than 10 seconds to restore everything.

**The safety findings from Reviewer 2 are the most important.** I'm classifying the Y6 enum, distress patterns, and forbidden patterns as BLOCKING — not because the architecture is wrong, but because the code samples don't match what your system currently enforces. Fixing them is straightforward; not fixing them would be a genuine regression.

Final word: 🟡 CONDITIONAL APPROVE. Fix the 4 blockers, then accept. The migration path is solid.

---

## Review Record

| Field | Value |
|---|---|
| Report ID | AR-ADR035-CHIEF-00 |
| Date | 2026-06-04 |
| Reviewer | Chief Reviewer — Final Synthesis |
| Reports Synthesized | 6 (01-technical-feasibility, 02-safety-compliance, 03-risk-assessment, 04-architecture-coherence, 05-implementation-readiness, 06-completeness-check) |
| ADR-035 Reviewed | v1.1, 2,325 lines, read in full |
| Final Verdict | **CONDITIONAL APPROVE** |
| BLOCKING Findings | 4 (B-001 through B-004) |
| CONDITIONAL Findings | 18 (C-001 through C-018) |
| RECOMMENDED Findings | 11 (R-001 through R-011) |
| INFORMATIONAL Findings | 24 (I-001 through I-024) |
| Cross-Reviewer Conflicts | 3 identified, all resolved |
| Risk Posture | 3 CRITICAL (uphold R3 upgrade), 5 HIGH, 7 MEDIUM, 10 missing risks identified |
| Safety Posture | 3 FAIL → 3 BLOCKING → expected 6 PASS / 2 CONDITIONAL after BLOCKING resolution |
| Path to Acceptance | 9 steps (4 BLOCKING + 5 pre-acceptance CONDITIONAL) |

---

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Chief Reviewer synthesis for ADR-035. For Faiz's eyes only.