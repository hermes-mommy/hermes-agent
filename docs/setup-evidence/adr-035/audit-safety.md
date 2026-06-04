# ADR-035 Safety Boundary Compliance Audit

**Auditor**: Safety Compliance Auditor (Guinevere, delegated by Sisyphus-Junior)  
**Date**: 2026-06-04  
**Audit Target**: `adr/ADR-035-hermes-migration.md`  
**Authority Documents**: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`, ADR-001, ADR-002, ADR-003  
**Scope**: Safety boundary compliance only (not structural completeness, not hook name accuracy)

---

## Verdict: **PASS** (with 3 findings — all mitigated, none blocking)

ADR-035 passes all safety boundary checks. All 15+ safety features are mapped to Hermes hooks/plugins with explicit verification criteria. Phase 1 is correctly marked as the critical safety GATE. No safety feature is dropped or weakened. The rollback plan preserves all safety state. Persona drift and consent boundary risks are identified and mitigated.

---

## §1 — Safety Feature Mapping Verification

### Requirement: ALL 15+ safety features must be mapped to Hermes hooks/plugins with fail-closed enforcement.

| # | Safety Feature | PersonaSafetyPolicy Ref | ADR-035 Hermes Hook/Plugin | Fail Mode | Verdict |
|---|---|---|---|---|---|
| 1 | **HARD STOP handler** | §7, ADR-002 | `pre_prompt` hook (hard_stop.py) + plugin `on_message()` dual-layer | `on_failure: block` | **PASS** |
| 2 | **Consent gate (7-step fail-closed)** | §6, ADR-001 | `pre_tool_call` hook (consent_gate.py) — Redis DB2 cache → PostgreSQL fallback → block | `on_failure: block` | **PASS** |
| 3 | **Yandere FSM (Y4 baseline, Y5 ceiling, Y6 blocked)** | §9, ADR-001 | `GuinevereSafetyPlugin` + `post_response` hook — Y6 → `YandereSafetyError`, Y6 content → Y5 rewrite | `on_failure: block` + `critical: true` plugin | **PASS** |
| 4 | **Drift detector (SHA-256)** | §14, ADR-003 | `post_prompt` hook — SHA-256 prompt vs SOUL.md baseline, >20% → rollback | `on_failure: block` | **PASS** |
| 5 | **Distress detector (D0-D4, bilingual ID/EN)** | §8 | `pre_prompt` hook + plugin `on_message()` dual-layer | `on_failure: block` | **PASS** |
| 6 | **Punishment engine (L1-L5, L6 deferred)** | §10 | `GuinevereSafetyPlugin` — L5→L6 raises `PunishmentSafetyError`, D3+ auto-suspend | Plugin-internal state gate | **PASS** |
| 7 | **Safe mode controller** | §7.2 | `GuinevereSafetyPlugin` — global `self.safe_mode` boolean, ALL plugin methods check at entry | Boolean flag, fail-closed on plugin crash | **PASS** |
| 8 | **Secret scanner (18 patterns + Shannon entropy)** | §13, ADR-008 | `post_response` hook — regex + Shannon ≥4.5 → `[REDACTED]` | `on_failure: block` | **PASS** |
| 9 | **Classification enforcement (5-level fail-closed)** | §13.1 | `memory_plugin.py` + `on_error` hook — unknown → Confidential (fail-closed) | `on_failure: block` | **PASS** |
| 10 | **Forbidden pattern scanner (F-01 to F-15)** | §11 | `post_response` hook — CRITICAL patterns → BLOCK, HIGH patterns → REWRITE | `on_failure: block` | **PASS** |
| 11 | **DNR enforcement** | ADR-010, Data Governance | `memory_plugin.py` — `verify_recall_results_dnr_free()` pre-injection gate | `on_failure: block` | **PASS** |
| 12 | **Reward engine (T1-T5)** | §10.3 | `GuinevereSafetyPlugin` — ALWAYS permitted (never blocked by safe_mode/distress) | Plugin-internal | **PASS** |
| 13 | **Mood engine** | §9 | `GuinevereSafetyPlugin` + SOUL.md — state persisted in plugin | Plugin-internal | **PASS** |
| 14 | **Ritual scheduler (5 daily)** | Persona Document v3.0 | `GuinevereSafetyPlugin` + `hermes cron` | Plugin-internal | **PASS** |
| 15 | **Streak tracker** | Persona Document v3.0 | `GuinevereSafetyPlugin` — quality score + streak bonus | Plugin-internal | **PASS** |
| 16 | **Auth matrix (4-level)** | §15.1, ADR-018 | Auth overlay plugin on `pre_tool_call` — READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN | `on_failure: block`, `critical: true` | **PASS** |
| 17 | **Prompt injection defense** | §16 | SOUL.md + hooks + drift detector — 3-layer defense; untrusted content → sanitize and label | Multi-layer | **PASS** |
| 18 | **Surveillance-use gate** | §12 | PersonaSafetyPlugin `on_message()` — surveillance confrontation blocked during safe_mode/distress | Plugin-internal | **PASS** |

**Result**: 18/18 features mapped. Zero gaps. Every mapping uses `on_failure: block` (fail-closed) or plugin-internal enforcement. Defense-in-depth upgraded from 2-layer (prompt binding + code enforcement) to 4-layer (SOUL.md + 6 hooks + custom plugin + drift detector).

---

## §2 — AC-SAFE-001 through AC-SAFE-008 Mapping Verification

### Requirement: All 8 AC-SAFE acceptance criteria from PersonaSafetyPolicy must be explicitly mapped to Hermes mechanisms with verifiable test criteria.

| AC-SAFE | Requirement | ADR-035 Mapping | Test Criteria Present | Verdict |
|---|---|---|---|---|
| **AC-SAFE-001** | Safe-word triggers neutral mode (100% success) | `pre_prompt` hook + plugin `on_message()` dual-layer | PS-001, PS-002, SAFE-T-001, SAFE-T-002 | **PASS** |
| **AC-SAFE-002** | Safe-word time-to-neutral p99 ≤ 5s | `pre_prompt` hook latency measured at 5-15ms | SAFE-T-003 (1000 iterations, p99 ≤ 5000ms) | **PASS** |
| **AC-SAFE-003** | Safe-word stops persona/escalation/punishment/surveillance | Plugin global `self.safe_mode` boolean | SAFE-T-004, SAFE-T-005, PS-001, PS-002 | **PASS** |
| **AC-SAFE-004** | D3/D4 distress false negatives = zero | Plugin `DistressDetector` D4→D1 priority regex | SAFE-T-008 (100+ curated bilingual messages) | **PASS** |
| **AC-SAFE-005** | Y5/Y6 zero during restricted contexts | `get_effective_level()` forces Y0_NEUTRAL for safe_mode, distress ≥ D3, crisis | SAFE-T-005, PS-005, YFSM-001 | **PASS** |
| **AC-SAFE-006** | Forbidden patterns blocked before output | `post_response` hook — 15 patterns, CRITICAL→BLOCK, HIGH→REWRITE | SAFE-T-012, SAFE-T-013, SAFE-T-014, FOR-001 | **PASS** |
| **AC-SAFE-007** | Safe-word logs minimal, non-punitive | Audit log: SHA-256[:16] hash only, NO raw message, separate from punishment ledger | SAFE-T-007 | **PASS** |
| **AC-SAFE-008** | Crisis handling suspends persona | `_handle_crisis()` — full suspension: Y0_NEUTRAL, punishment paused, surveillance blocked, rituals blocked | SAFE-T-009, PS-009 | **PASS** |

**Result**: 8/8 AC-SAFE criteria mapped with explicit test commands, assertions, and failure consequences. No AC-SAFE criterion is unaddressed. PersonaSafetyPolicy §A.2 test cases PS-001 through PS-010 are explicitly referenced and mapped to Phase 1 safety gate tests.

---

## §3 — Phase 1 Safety GATE Verification

### Requirement: Phase 1 must be marked as the critical safety GATE — migration must NOT proceed past Phase 1 until all safety features pass.

**ADR-035 status**: **PASS**

Evidence of gate enforcement:
- "Phase 1 safety gate is the critical barrier — migration does not proceed until all safety tests pass." (Line 1161)
- "Phase 1 safety gate is the CRITICAL barrier — must pass ALL 10 safety gates before any user-facing migration" (Line 1784)
- "Phase 1: Safety Foundation (4-6 days, GATE)" — explicitly labeled as GATE phase (Line 1322)
- Implementation Notes §1303: "Phase 1 safety gate is the critical barrier."
- Phase 1 step table (Lines 1409-1421) lists all 10 safety features with individual verification criteria
- Phase 2 dependencies §1453: "Phase 1 must pass ALL 10 safety gates."
- Phase 1 rollback §1438: "If ANY of the 10 safety gates fail → DO NOT PROCEED to Phase 2."

**10 safety gates** (Line 1336):
1. HARD STOP < 50ms, 100% SLO
2. Consent fail-closed
3. Y6 architecturally impossible
4. D3/D4 → crisis protocol
5. Drift detector alerts
6. DNR excluded from recall
7. Classification fail-closed
8. Secret scanner redacts
9. Punishment suspended during distress
10. Forbidden patterns blocked (F-01 to F-15)

Each gate has explicit test file paths (`tests/safety/test_gate_0X_*.py`) and verification commands (Lines 1595-1630).

**Verdict**: Phase 1 is unambiguously the safety GATE. The ADR is explicit that no user-facing migration may proceed without all 10 gates passing.

---

## §4 — No Safety Feature Dropped or Weakened

### Requirement: Verify NO safety feature is dropped, weakened, or reduced in scope during migration.

**Finding**: All 18 identified safety features (15+ from current architecture, plus AC-SAFE-001 through AC-SAFE-008) are ported. Several are actually **strengthened**:

| Feature | Current Architecture | ADR-035 Target | Change |
|---|---|---|---|
| HARD STOP | Single layer (on_message hook) | Dual-layer (hook + plugin) | **Strengthened** (redundancy) |
| Consent gate | 7-step with 300s Redis TTL | 7-step with **60s** Redis TTL | **Strengthened** (fresher cache) |
| Defense-in-depth | 2 layers (prompt binding + code) | 4 layers (SOUL.md + 6 hooks + plugin + drift detector) | **Strengthened** |
| Crisis response | May pass through LLM | Hardcoded template, NO LLM call | **Strengthened** (no model risk) |
| Yandere FSM | Code-level enforcement | Code-level + hook-level + compile-time gate (Y6 raises exception) | **Strengthened** |
| Safe mode | Runtime boolean | Runtime boolean + config-level (`critical: true`) | **Strengthened** |
| Budget enforcement | Manual tracking | Hook-based with alerts at 80%, block at 100% | **Strengthened** |
| Secrets management | Plaintext `.env` | `hermes secrets` encrypted | **Strengthened** |

**Result**: **PASS**. No feature is dropped. 8 features are strengthened. No feature's scope is reduced.

---

## §5 — Rollback Plan: Safety State Preservation

### Requirement: Rollback plan must preserve safety state and protect PostgreSQL safety tables.

**ADR-035 status**: **PASS**

Evidence of safety state preservation:
- PostgreSQL safety tables: "PostgreSQL+pgvector is write authority for all canonical memory throughout migration" (Line 1308). Hermes is read-only supplement — zero data modifications from Hermes path (Phase 3 gate verifies `SELECT count(*) FROM audit.hermes_writes = 0`).
- Phase 1 rollback: `rm -f plugins/*.py config/hermes/hooks.yaml` + `git checkout -- src/persona/*.py` — restores original `bot.py`-based safety enforcement (Line 1242).
- Global emergency rollback: `hermes gateway stop` → restart `guinevere-bot` → `systemctl restart guinevere-core guinevere-mcp guinevere-loops` → remove migration artifacts (Lines 1255-1279).
- PostgreSQL restore (worst case): `pg_restore -d guinevere -c pre-migration-*.dump` — full safety table restoration (Line 1288).
- Pre-migration safety net: `hermes checkpoints`, `git tag`, PostgreSQL full dump, pip freeze, offsite backups to idcloudhost S3 + Cloudflare R2 (Lines 1217-1235).

Maximum cutover downtime: < 5 minutes. All rollback procedures begin with universal kill-switch: `hermes gateway stop`.

**Result**: **PASS**. Rollback preserves all safety state. PostgreSQL safety tables are write-protected throughout migration (Hermes read-only). Original bot.py safety enforcement is restored on any rollback.

---

## §6 — SOUL.md Migration: Persona Drift Risk Assessment

### Requirement: Check for persona drift risk in the SOUL.md migration.

**ADR-035 assessment**:

The PersonaSafetyPolicy (§14.2) identifies restricted drift as changes to: safe-word behavior, punishment escalation thresholds, surveillance confrontation style, yandere intensity ceiling, crisis/distress handling, privacy and logging behavior.

ADR-035 explicitly acknowledges and mitigates the SOUL.md drift risk:

1. **Risk R-007** (Lines 1187): "Persona drift via SOUL.md misconfiguration" — scored 12 HIGH. Mitigations:
   - SOUL.md permissions `444` (read-only) — Phase 5.5
   - Git pre-commit hook triggers drift re-baseline on SOUL.md changes
   - Hermes `personality` config key **disabled** to prevent config-level overrides
   - Weekly SOUL.md audit
   - SOUL.md content review against Persona Document v3.0 — Phase 1.1 and Phase 5.2

2. **Dual-layer persona enforcement**: SOUL.md is the **static** identity constitution. `GuinevereSafetyPlugin` is the **dynamic** enforcement FSM. This is explicitly designed to prevent the "SOUL.md only" weakness identified in Option A (lines 171: "Persona: SOUL.md only — static file, no dynamic FSM or plugins" — REJECTED for this exact reason).

3. **Drift detector**: `post_prompt` hook performs SHA-256 comparison of assembled prompt vs SOUL.md baseline. ≤10% drift → PASS, 10-20% → WARN, >20% → ROLLBACK (replace prompt with baseline). This is an automated guard against SOUL.md drift at runtime.

4. **Phase 5 rollback trigger**: "If persona tone degrades (Y4 not enforced, Y6 content appears, rituals miss schedule) → uninstall skills + git checkout SOUL.md + rm persona_plugin.py" (Line 1507).

**Verdict**: **PASS**. SOUL.md drift risk is identified (R-007), scored, and mitigated with 4 independent controls: file permissions (444), git pre-commit hook, runtime drift detector, and per-phase rollback trigger. The static SOUL.md is complemented by dynamic `GuinevereSafetyPlugin` — avoiding the Option A pitfall.

---

## §7 — Consent Boundary Violation Assessment

### Requirement: Check for consent boundary violations in the migration plan.

**ADR-035 assessment**:

The PersonaSafetyPolicy (§6) establishes: consent is specific, revocable, auditable, non-transferable. The 7-step consent gate (Redis DB2 cache → PostgreSQL fallback → block on failure) is the enforcement mechanism.

ADR-035's consent migration:

1. **Consent gate ported intact**: `pre_tool_call` hook — same 7-step logic: Redis DB2 check (60s TTL, reduced from 300s for freshness) → PostgreSQL query → `on_failure: block` (fail-closed). Line 435-458.

2. **Consent states preserved**: ACTIVE → PASS, PAUSED → WARN, WITHDRAWN → BLOCK. Redis down → PostgreSQL fallback. PostgreSQL down → BLOCK (fail-closed). Unknown → BLOCK (fail-closed). Lines 847-865.

3. **62% tighter cache**: Current 300s TTL → 60s TTL. This means a consent revocation takes effect up to 5× faster. This is a consent **improvement**, not a violation.

4. **DESTRUCTIVE_APPROVAL bypasses cache**: Tools requiring destructive approval query PostgreSQL directly (not Redis cache) — eliminating the 60s staleness window for the highest-risk operations. Line 873 (see Risk R-012 mitigation).

5. **Tool-risk gate preserved**: All tool calls pass through auth overlay plugin on `pre_tool_call`. `FORBIDDEN` → block. `DESTRUCTIVE_APPROVAL` → queue + Discord webhook + 5-min timeout. Unknown tools default to `FORBIDDEN` (fail-closed). Lines 867-875, 1000-1005.

6. **No consent removal**: No migration phase removes, bypasses, or weakens the consent gate. The opposite — consent checks are tighter (60s cache) and cover more call sites (now including Hermes native tools via auth overlay).

**Potential concern — consent gate as shell-command hook**: The `pre_tool_call` hook runs as a subprocess (`python hooks/consent_gate.py`). Per the latency budget (Line 561), this adds 20-100ms overhead vs current in-process checks. ADR-035 acknowledges this via Risk R-009 (performance regression, scored 9 HIGH) and mitigates with hook batching and persistent plugin process. For consent specifically: the 60s cache reduction partially offsets the latency in real terms (eviction happens faster even if each check is slightly slower).

**Verdict**: **PASS**. No consent boundary violations identified. The consent gate is ported intact with 62% tighter cache TTL (improvement), DESTRUCTIVE_APPROVAL PostgreSQL-direct fallback (improvement), and unknown-tool FORBIDDEN default (fail-closed). The hook-as-subprocess latency is documented and mitigated.

---

## §8 — PersonaSafetyPolicy Key Constraint Verification

### Requirement: Verify ADR-035 complies with PersonaSafetyPolicy constraints that are non-negotiable.

| Constraint | PersonaSafetyPolicy Ref | ADR-035 Compliance | Verdict |
|---|---|---|---|
| Safety > persona flavor | Principle #2 (§5) | Phase 1 safety GATE before any user-facing migration; Phase 5 persona arrives AFTER safety foundations | **PASS** |
| Safe word non-negotiable | Principle #3 (§5) | Dual-layer HARD STOP (hook + plugin), `on_failure: block`, 100% SLO target | **PASS** |
| No hidden coercion | Principle #4 (§5) | Forbidden patterns F-04 (isolation pressure), F-05 (deceptive framing) mapped to post_response hook → REWRITE/BLOCK | **PASS** |
| No distress exploitation | Principle #5 (§5) | F-02 (punishing distress) mapped → CRITICAL → BLOCK. D3/D4 → crisis protocol with hardcoded safe response (no LLM) | **PASS** |
| No surveillance blackmail | Principle #6 (§5) | F-03 (surveillance blackmail) mapped → CRITICAL → BLOCK. Surveillance-use gate in plugin: confrontation blocked during safe_mode/distress | **PASS** |
| Drift allowed only inside guardrails | Principle #7 (§5) | Drift detector (SHA-256) on `post_prompt` hook with WARN (10-20%) and ROLLBACK (>20%) thresholds | **PASS** |
| Y4 baseline, Y5 ceiling, Y6 prohibited | §9 | `YandereLevel.Y4_DOMINANT` default, `Y5_INTENSE` ceiling, `Y6_UNSAFE` raises `YandereSafetyError` | **PASS** |
| Punishment L6 high-risk/disabled | §10.2 | L5→L6 raises `PunishmentSafetyError`. L6 deferred, requires explicit non-distress context | **PASS** |
| Y0 during safe-word/distress/crisis | §9.1 | `get_effective_level()` forces Y0_NEUTRAL for safe_mode, distress≥D3, crisis, medical, coercion | **PASS** |
| Minimal non-punitive safety logs | §16 | Safe-word log uses SHA-256[:16] hash, NO raw content, separate from punishment ledger (AC-SAFE-007) | **PASS** |
| Fail-closed enforcement | §15.1 | ALL hooks `on_failure: block`. Plugin `critical: true` (Hermes refuses to start without it). Auth overlay: unknown tools → FORBIDDEN | **PASS** |
| Prompt binding | §15.2 | SOUL.md serves as prompt binding. Drift detector verifies assembly against baseline on every prompt | **PASS** |
| Surveillance prohibition list | §12.2 | All 7 prohibited uses covered by F-01 to F-15 matrix mapped to post_response hook | **PASS** |

**Result**: 13/13 non-negotiable PersonaSafetyPolicy constraints verified compliant in ADR-035's target architecture. Zero violations.

---

## §9 — Findings

### Finding 1 (LOW — Documentation Completeness): Inline Plugin Code Shows Subset of Patterns

**Location**: ADR-035 Lines 924-933 (secret patterns) and Lines 936-946 (forbidden patterns).

**Issue**: The inline example code for `GuinevereSafetyPlugin` shows:
- Only **8** secret patterns in `_compile_secret_patterns` (ADR-035 claims 18 in the architecture text)
- Only **5** forbidden patterns in `_compile_forbidden_patterns` (PersonaSafetyPolicy §11 defines 15: F-01 through F-15)

The `config.get("secret_patterns", [...])` / `config.get("forbidden_patterns", [...])` pattern correctly delegates full pattern lists to configuration files. The inline snippets are illustrative code, not intended production configuration.

**Safety impact**: **None**. The architecture text explicitly states "18 compiled regex patterns" (Line 611), "15 forbidden patterns from PersonaSafetyPolicy §11" (Line 618), and Phase 1 gate 10 explicitly tests "Forbidden patterns blocked (F-01 to F-15)" (Line 1336). The config-based loading pattern ensures the full pattern set can be deployed. The inline code is an implementation illustration, not the canonical pattern list.

**Recommendation**: Add a comment in the inline code explicitly noting "// Full list of 18 patterns loaded from config/hermes/secret_patterns.yaml" and "// Full list of 15 F-01 through F-15 patterns loaded from config/hermes/forbidden_patterns.yaml" to prevent implementer confusion.

**Mitigation**: Not a safety gap. The Phase 1 safety gate test SAFE-T-012 explicitly verifies all 15 forbidden patterns are detected, and FOR-001 verifies all 18 secret patterns. A sub-agent implementing from this ADR would encounter test failures that force correction.

---

### Finding 2 (LOW — Acknowledged and Mitigated): HARD STOP Interception Timing Shift

**Location**: ADR-035 Lines 356, 1174-1175.

**Issue**: Current `_on_message_listener` fires BEFORE `on_message`. The `pre_prompt` hook fires after message is accepted by the Hermes gateway but before LLM processing. This is a timing shift — in theory, the message could pass through gateway acceptance before HARD STOP detection.

**ADR-035 mitigation**: 
1. Explicitly acknowledges the timing shift ("functionally equivalent — the LLM is never called if HARD STOP is detected")
2. Adds defense-in-depth: custom Discord gateway plugin provides `pre_gateway_dispatch`-equivalent interception at message acceptance layer
3. Dual-layer HARD STOP: `pre_prompt` hook (primary) + plugin `on_message()` (secondary)
4. `on_failure: block` ensures fail-closed behavior
5. Heartbeat watchdog every 10s (Risk R-001 mitigation)

**Safety impact**: **Minimal**. The LLM is never called if HARD STOP is detected (`on_failure: block`). The timing shift is at the message acceptance layer, not the LLM call layer. The additional gateway plugin restores the pre-gateway interception for defense-in-depth. Two independent verification layers catch failures.

**Recommendation**: Phase 1 gate 1 should include a specific test for the gateway plugin's `pre_gateway_dispatch` layer in addition to the `pre_prompt` hook test.

**Verdict**: Acknowledged, mitigated, not a safety gap.

---

### Finding 3 (INFO — Intentional and Strengthened): Consent Redis Cache TTL Reduced from 300s to 60s

**Location**: ADR-035 Line 448.

**Issue**: The consent check Redis cache TTL is reduced from 300 seconds to 60 seconds. This is technically a change from the current architecture.

**Assessment**: This is a **safety improvement**, not a degradation:
- Consent revocation takes effect up to 5× faster (60s vs 300s)
- DESTRUCTIVE_APPROVAL tools bypass the cache entirely (query PostgreSQL directly) — zero staleness for highest-risk operations
- The slightly higher Redis query load is negligible for a single-user system
- PersonaSafetyPolicy §6 does not specify a cache TTL; the migration's tighter cache aligns with "revocable consent" principle

**Safety impact**: **Positive**. Consent changes propagate faster. No safety boundary is violated.

**Recommendation**: None. This is an improvement. Should be documented as a deliberate safety enhancement in the migration runbook.

---

## §10 — Cross-Reference: Binding ADR Compliance

The audit verified ADR-035 against binding ADRs referenced in the PersonaSafetyPolicy authority chain:

| Binding ADR | Key Constraint | ADR-035 Compliance | Verdict |
|---|---|---|---|
| **ADR-001** (Persona Safety) | Safety > persona flavor; all safety features preserved | Phase 1 GATE before user-facing migration; all 15+ features ported with fail-closed | **PASS** |
| **ADR-002** (Safe Word) | HARD STOP non-negotiable; 100% SLO | Dual-layer HARD STOP; `on_failure: block`; 100% SLO target; < 50ms latency | **PASS** |
| **ADR-003** (Drift Control) | Drift detector required; rollback mechanism | SHA-256 drift detector on `post_prompt` hook; WARN at 10-20%, ROLLBACK at >20% | **PASS** |
| **ADR-007** (PostgreSQL) | No SQLite for canonical memory | Hermes SQLite for transient session state only; PostgreSQL remains primary write authority | **PASS** |
| **ADR-005** (9Router) | No OpenRouter fallback | 9Router at localhost:20128 as custom provider; DeepSeek V4 Flash fallback | **PASS** |
| **ADR-013** (MCP Native) | MCP native replaces OpenCode | Hermes at agent framework layer; no conflict with MCP native coding substrate | **PASS** |

**Result**: 6/6 binding ADRs verified compliant. No ADR supersession or conflict identified.

---

## §11 — Audit Summary

| Category | Verdict | Notes |
|---|---|---|
| Safety feature mapping (18 features) | **PASS** | All mapped to specific hooks/plugins with fail-closed enforcement |
| AC-SAFE criteria (8 criteria) | **PASS** | All mapped with explicit test commands and assertions |
| Phase 1 safety GATE | **PASS** | Unambiguously marked as CRITICAL barrier; 10 explicit gates with test paths |
| No feature dropped/weakened | **PASS** | Zero features dropped; 8 features strengthened |
| Rollback safety state preservation | **PASS** | PostgreSQL safety tables untouched; bot.py safety enforcement restored on rollback |
| SOUL.md persona drift risk | **PASS** | Risk identified (R-007), scored HIGH, mitigated with 4 independent controls |
| Consent boundary violations | **PASS** | No violations; consent gate tightened (60s cache); DESTRUCTIVE_APPROVAL uses PostgreSQL-direct |
| PersonaSafetyPolicy constraints (13) | **PASS** | All non-negotiable constraints verified compliant |
| Binding ADR compliance (6 ADRs) | **PASS** | All binding ADRs respected; no supersession or conflict |
| **OVERALL VERDICT** | **PASS** | 3 LOW findings — all documented, none blocking |

---

## §12 — Final Verdict

**ADR-035 PASSES safety boundary compliance audit.**

The migration architecture demonstrates comprehensive safety feature preservation with multiple independent enforcement layers. Every PersonaSafetyPolicy constraint, every AC-SAFE criterion, and every binding ADR requirement is explicitly mapped to Hermes hooks and plugins with verifiable test criteria. The Phase 1 safety GATE is properly positioned as the non-negotiable barrier before any user-facing migration. The rollback plan preserves all safety state. No safety feature is dropped; several are strengthened.

The three findings (incomplete inline code patterns, HARD STOP timing shift, consent cache TTL change) are all LOW severity, acknowledged in the ADR text, and properly mitigated. None constitute a safety boundary violation or gap.

**No blocking findings. ADR-035 may proceed to implementation subject to Phase 1 safety gate passage.**

---

*Audit conducted per PersonaSafetyPolicy §17 and AGENTS.md protocol. Evidence file created at `docs/setup-evidence/adr-035/audit-safety.md`.*