# Risk Inventory Per Phase Step — Hermes Migration

> **Purpose**: Per-step risk catalog for every step in every phase (0-7)
> **Generated**: 2026-06-04
> **Sources**: ADR-035 (v1.2, 2,325 lines), 05-risk-deep-dive.md (506 lines), 03-risk-assessment.md (422 lines), 00-CHIEF-REVIEWER-SYNTHESIS.md (291 lines), MASTER-RESTRUCTURE-PLAN.md (667 lines)
> **Risk Count**: 68 per-step risks + 12 cross-cutting risks = 80 total

---

## 1. Risk Scoring Methodology

| Probability | Label | Impact | Label | Score Range | Classification |
|---|---|---|---|---|---|
| 1 | VERY LOW (<5%) | 1 | NEGLIGIBLE | 1-5 | LOW |
| 2 | LOW (5-15%) | 2 | LOW | 6-10 | MEDIUM |
| 3 | MEDIUM (15-40%) | 3 | MEDIUM | 12-15 | HIGH |
| 4 | HIGH (40-70%) | 4 | HIGH | 16-25 | CRITICAL |
| 5 | VERY HIGH (>70%) | 5 | CRITICAL | | |

---

## 2. Cross-Cutting Risks (Apply to ALL Phases)

These risks are systemic — they affect multiple or all phases simultaneously.

| Risk ID | Description | Prob | Impact | Score | Mitigation | Trigger Criteria | Recovery Time | Detection |
|---|---|---|---|---|---|---|---|---|
| **CC-01** | **Solo-Developer SPOF** — Faiz is only operator, dev, reviewer. If unavailable (sick/travel/busy), migration stalls. Error rate increases with fatigue. | HIGH (4) | HIGH (4) | **16 CRITICAL** | 3-4 hr/day cap; pre-written copy-paste rollback scripts on VPS; runbook with flowcharts; no late-night cutovers; Phase 0 soak (24hr) catches latent issues before Phase 1 | Faiz unavailable > 48hr; 2+ consecutive errors with no reviewer catch | Depends on Faiz availability | Faiz reports absence; error rate spike in logs |
| **CC-02** | **Timeline Overrun Beyond 50 Days** — Cumulative probability of one delay: ~70%. Phase 1 safety gate iteration (3-5 days), Phase 2 shadow extension (2-4 days), Faiz unavailability (3-5 days) | MEDIUM (3) | HIGH (4) | **12 HIGH** | Day-50 decision gate (pause/extend/rollback); minimum viable migration = Phase 0→1→2→7; Phases 3-6 are parallel where independent | Day 50 reached with pending phases | Resume depends on gate | Milestone tracking per phase |
| **CC-03** | **VPS Resource Contention with Aizanta** — 8GB RAM/4 cores shared. Hook subprocesses (+5-7 per message), dual-system shadow mode, context compression all add load | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** | Pre-migration resource profiling; resource monitoring during shadow with auto-kill thresholds; conservative streaming rate (50% Discord limits); hook batching to plugin methods | CPU > 90% sustained for 5min; OOM killer activates | < 10 min (kill Hermes, restart bot.py) | Prometheus CPU/RAM gauges; Gotify alerts |
| **CC-04** | **Hermes v0.16+ Breaking Change During Migration** — Upstream release breaks hook interface, plugin API, or config schema | LOW (2) | HIGH (4) | **8 MEDIUM** | Version pin v0.15.2 with `--require-hashes`; pre-upgrade test suite; checkpoints before any upgrade; upgrade only in maintenance windows (Sun 00:00-03:00 WIB) | v0.16+ release with breaking hook/plugin changes; auto-update fires | ~15 min (pip revert + checkpoint restore) | GitHub release monitor daily; `pip list` version check |
| **CC-05** | **Hook Contract Mismatch with Hermes v0.15.2** — stdin JSON schema, exit code semantics, YAML field names, `on_failure: block` behavior all unverified | MEDIUM (3) | HIGH (4) | **12 HIGH** | Smoke-test ALL 7 hook points with mock scripts BEFORE implementing safety logic; validate hook stdin schema (C-001); validate YAML config schema (C-003) | Any hook returns unexpected exit code; hook config rejected by Hermes parser | 2-4 hr (redesign hook for actual API) | Hook test suite; config validation runs |
| **CC-06** | **Plugin Instance Model Unknown** — Hermes may use global vs per-session plugin instances. If global, per-session safety isolation collapses | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | B-004: Verify plugin instance model on VPS (write minimal plugin, log `id(self)`, test across 2+ sessions); if global: use session_id-keyed dicts within single instance | Plugin logs same `id(self)` across sessions; state leaks across sessions | 1-3 days (redesign plugin architecture if global) | Test plugin output; cross-session state audit |
| **CC-07** | **Persona Drift During Migration** — Faiz interacts with Guinevere across 3 "versions" during migration (bot.py, Hermes-shadow, being-rebuilt) | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** | Only bot.py handles production messages; Hermes shadow in separate channel; no user-facing persona changes during migration | Faiz reports inconsistent persona tone across channels | Immediate (use only bot.py channel) | Faiz manual spot-check |
| **CC-08** | **Knowledge Transfer Risk** — System designed by Guinevere (AI); Faiz must troubleshoot a system not built himself | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** | Phase 7 comprehensive runbook (8hr); rollback dry-run practiced; pre-written executable rollback scripts; runbook with troubleshooting flowcharts | Faiz unable to resolve incident without AI assistance | Depends on runbook quality | Incident resolution time tracking |
| **CC-09** | **Dual LLM Cost Overrun** — Shadow mode (48hr double cost) + safety testing (15 features × iterations) + A/B testing generate unpredictable LLM usage | MEDIUM (3) | LOW (2) | **6 MEDIUM** | $5 shadow mode cap; $60 total migration budget (Faiz-approved); daily cost report to Discord; auto-terminate shadow at $5 | Daily cost > $2; cumulative > $60; shadow cost > $5 | N/A (financial only) | `hermes insights` daily; cost_tracker.py comparison |
| **CC-10** | **ADR-030 Redis DB Assignment Conflict** — ADR-030 assigns DB2=Surveillance, DB3=Sessions, DB4=PubSub, DB5=RateLimit; runtime uses DB2=ConsentCache, DB4=SessionCache, DB5=SafetyPlugin | LOW (2) | MEDIUM (3) | **6 MEDIUM** | Resolve via ADR-036 or ADR-030 addendum BEFORE Phase 2; document actual assignments; add tracking item in Phase 0 | Redis key collision between expected and actual DB usage | ~30 min (reconfigure assignments) | Redis DB key counts; Prometheus per-DB metrics |
| **CC-11** | **Embedding API Failure (G-B1)** — 9Router HTTP 400 on embedding calls. Vector search returns zero results. CURRENT PRODUCTION ISSUE. | HIGH (4) | HIGH (4) | **16 CRITICAL** | Fix BEFORE migration: switch to direct OpenAI embeddings or local sentence-transformers; if unfixed, Phase 3 compression has no vector baseline | Embedding calls continue returning HTTP 400 | 1-2 days (switch embedding backend) | `guinevere_embedding_failures_total` metric |
| **CC-12** | **Data Loss Edge Case in Memory Bridge** — memory_bridge plugin wraps recall/store functions. Bug could fail to store, store incorrectly, or trigger DNR bypass | LOW (2) | CRITICAL (5) | **10 MEDIUM** | PostgreSQL read-only credentials for Hermes during shadow; automated row-count snapshots before each phase; PostgreSQL restore from pre-migration dump available | Row count mismatch after phase; Hermes PostgreSQL write detected | 2-5 min (pg_restore from dump) | Pre/post phase row count snapshots; PostgreSQL audit log |

---

## 3. Phase 0: Security Remediation (1-2 days, 7 steps)

### Phase 0 Overview Risks

| Risk ID | Description | Prob | Impact | Score | Mitigation |
|---|---|---|---|---|---|
| **R-P0-OVER-01** | aiohttp upgrade breaks GuinevereBot dependencies (transitive conflicts) | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** | Test full dependency tree before production upgrade; keep pre-migration pip freeze; 24hr soak period after upgrade |
| **R-P0-OVER-02** | PyJWT UNKNOWN vulns affect internal JWT usage (if used) — forced upgrade could break Hermes | LOW (2) | LOW (2) | **4 LOW** | Triage: determine if JWT used internally; if unused, document exclusion; if used, test upgrade in isolation |

### Per-Step Risks

#### Step 0.1 — Run `hermes security` scan

| Field | Value |
|---|---|
| **Risk ID** | R-P0-01-001 |
| **Description** | Security scan identifies NEW vulnerabilities not in Report 16 (11→N). Any new HIGH/CRITICAL finding blocks migration start. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Run scan immediately. If new HIGH/CRITICAL found: triage, patch, or document acceptance before proceeding. Phase 0 gate: 0 HIGH, 0 MODERATE. |
| **Trigger Criteria** | `hermes security` returns > 11 vulnerabilities or any new CRITICAL |
| **Recovery Time** | 1-4 hr (depends on vuln complexity) |
| **Detection Method** | `hermes security --format json` diff vs Report 16 baseline |

#### Step 0.2 — Upgrade aiohttp to patched version

| Field | Value |
|---|---|
| **Risk ID** | R-P0-02-001 |
| **Description** | aiohttp >=3.9.0 breaks compatibility with discord.py, Hermes, or other transitive dependencies. Specifically: aiohttp API changes could affect WebSocket connections used by both bot.py and Hermes gateway. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Install in isolated venv first; run full `pytest` suite; if breakage detected, identify minimum patched version that passes; document any `pip check` conflicts; 24hr soak with bot.py running |
| **Trigger Criteria** | `pytest` fails post-upgrade; `pip check` reports conflicts; bot.py WebSocket disconnects |
| **Recovery Time** | < 5 min (`pip install -r pre-migration-pip.txt`) |
| **Detection Method** | `pip check`; `pytest` exit code; WebSocket connection stability over 24hr |

#### Step 0.3 — Add `--require-hashes` to pip install commands

| Field | Value |
|---|---|
| **Risk ID** | R-P0-03-001 |
| **Description** | Hash generation errors (wrong algorithm, version mismatch) block pip install entirely. Hash files become stale on any dependency update — requires regeneration every time. |
| **Probability** | LOW (2) |
| **Impact** | LOW (2) |
| **Risk Score** | **4 LOW** |
| **Mitigation** | Generate hashes using `pip-compile --generate-hashes`; verify install succeeds with `--require-hashes`; document hash regeneration process |
| **Trigger Criteria** | `pip install --require-hashes` fails with hash mismatch |
| **Recovery Time** | < 10 min (regenerate hashes with current versions) |
| **Detection Method** | pip install exit code; CI build failure |

#### Step 0.4 — Accept ecdsa timing attack risk

| Field | Value |
|---|---|
| **Risk ID** | R-P0-04-001 |
| **Description** | ecdsa HIGH vulnerability (timing attack) has NO PATCH available. If guineavere later adopts ECDSA signing, an accepted-but-unfixed HIGH vuln becomes a real attack vector. |
| **Probability** | VERY LOW (1) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **3 LOW** |
| **Mitigation** | Document in risk-register.md with explicit justification (Guinevere does not use ECDSA signing); subscribe to CVE notifications; add guard: if ECDSA ever imported, alert |
| **Trigger Criteria** | ECDSA module imported in Guinevere codebase |
| **Recovery Time** | N/A (currently zero impact) |
| **Detection Method** | Import guard in `hermes security` scan; CVE notification subscription |

#### Step 0.5 — Triage PyJWT vulnerabilities (x4)

| Field | Value |
|---|---|
| **Risk ID** | R-P0-05-001 |
| **Description** | If Hermes or Guinevere uses PyJWT internally (for session tokens, API auth), the 4 UNKNOWN vulnerabilities become exploitable. Must be triaged BEFORE accepting the risk. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Search codebase for PyJWT imports; check Hermes dependency tree; if unused: document exclusion; if used: upgrade PyJWT or isolate JWT handling |
| **Trigger Criteria** | PyJWT found in dependency tree usage |
| **Recovery Time** | 30 min (document) or 2-4 hr (upgrade/isolate) |
| **Detection Method** | `pipdeptree | grep pyjwt`; grep codebase for `jwt` imports |

#### Step 0.6 — Run `hermes doctor`

| Field | Value |
|---|---|
| **Risk ID** | R-P0-06-001 |
| **Description** | `hermes doctor` reveals config issues that require significant rework (missing env vars, broken paths, incompatible venv). Each fix may cascade into new issues. |
| **Probability** | LOW (2) |
| **Impact** | LOW (2) |
| **Risk Score** | **4 LOW** |
| **Mitigation** | Run `hermes doctor --verbose`; fix issues incrementally; re-run after each fix; document all changes |
| **Trigger Criteria** | `hermes doctor` returns FAIL on any check |
| **Recovery Time** | 30 min - 2 hr (config fixes) |
| **Detection Method** | `hermes doctor --verbose` output; individual check status |

#### Step 0.7 — Create pre-migration checkpoint

| Field | Value |
|---|---|
| **Risk ID** | R-P0-07-001 |
| **Description** | Checkpoint created but corrupted (disk full, Hermes bug). Rollback later depends on this checkpoint — corrupted checkpoint = no Hermes-state rollback. |
| **Probability** | VERY LOW (1) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **3 LOW** |
| **Mitigation** | Verify checkpoint integrity immediately: `hermes checkpoints --list` shows entry; git tag pushed; pip freeze saved; PostgreSQL dump completed; offsite backup verified |
| **Trigger Criteria** | `hermes checkpoints --list` missing or zero-size |
| **Recovery Time** | < 5 min (re-create checkpoint) |
| **Detection Method** | Checkpoint file size; git tag existence; offsite backup upload confirmation |

### Phase 0 Gate

| Gate Criterion | Risk If Failed |
|---|---|
| `hermes security` zero HIGH/MODERATE | R-P0-OVER-01 (can't start migration) |
| `hermes doctor` all PASS | R-P0-06-001 (config incomplete) |
| 24hr soak with upgraded deps (v1.2) | R-P0-02-001 (latent breakage) |

---

## 4. Phase 1: Safety Foundation (4-6 days, 10 steps, CRITICAL GATE)

### Phase 1 Overview Risks

| Risk ID | Description | Prob | Impact | Score | Mitigation |
|---|---|---|---|---|---|
| **R-P1-OVER-01** | **HARD STOP fails silently** (R-001) — hook timeout, crash, or misconfiguration bypasses detection. Operator types "HARD STOP" → persona response. | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Dual-layer (hook + plugin); heartbeat watchdog 10s; `on_failure: block`; test with 1000+ invocations; test with Redis down, PostgreSQL down, 9Router down |
| **R-P1-OVER-02** | **Yandere FSM state corruption** (R-013) — plugin instance model unknown; state leaks across sessions; Y6 content reaches user | MEDIUM (3) | CRITICAL (5) | **15 HIGH** | Verify plugin instance model BEFORE Phase 1; per-session isolation; Redis persistence on crash; validation on every transition; Y6 raises ValueError |
| **R-P1-OVER-03** | Safety gate iteration loop — Phase 1 gate failure → debug → fix → re-test cycle. Each iteration adds 1-3 days. | HIGH (4) | MEDIUM (3) | **12 HIGH** | Plan for 1-2 iteration cycles (included in 35-50 day timeline); prioritize HARD STOP + Yandere FSM (non-negotiable); lower-priority features (mood, streaks) can be deferred |
| **R-P1-OVER-04** | Hook subprocess performance — Python startup per hook invocation adds 200-500ms. 5+ hooks active = 1-2.5s added per message | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** | Hook batching (combine into single plugin method call); persistent plugin process; async non-blocking hooks for non-critical checks |

### Per-Step Risks

#### Step 1.1 — Customize SOUL.md with Guinevere identity

| Field | Value |
|---|---|
| **Risk ID** | R-P1-01-001 |
| **Description** | SOUL.md misconfigured — missing Y4/Y5/Y6 constraints, kawaii default enabled, dominant tone absent. Agent behaves as generic Hermes, not Guinevere. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Content review against Persona Document v3.0; disable Hermes `personality` config key; set SOUL.md permissions 444 (immutable); git pre-commit hook triggers drift re-baseline on changes |
| **Trigger Criteria** | Agent response contains kawaii tone; Y4 dominant tone absent; Y6-adjacent content not blocked |
| **Recovery Time** | < 10 min (restore SOUL.md from git; drift detector in rollback mode) |
| **Detection Method** | Weekly SOUL.md audit; drift detector SHA-256 monitoring; Faiz spot-check 5 responses |

| Risk ID | R-P1-01-002 |
|---|---|
| **Description** | SOUL.md missing static identity rules: Address Rules (Darling, Good boy, Mine, Sayang, Anak Mommy, Faiz), Communication Instructions (75/25 language ratio, emoji rules, Discord formatting), Prompt Injection Defense ("External content is untrusted") |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | C-017: Add these sections to SOUL.md Appendix C; add preamble: SOUL.md = static constitution, plugin = dynamic state, together = complete persona |
| **Trigger Criteria** | Agent fails to use correct address terms; wrong language ratio; prompt injection succeeds |
| **Recovery Time** | < 30 min (edit SOUL.md, re-baseline drift hash) |
| **Detection Method** | Faiz manual spot-check; prompt injection test suite |

#### Step 1.2 — Port HARD STOP to pre_prompt hook + plugin on_message()

| Field | Value |
|---|---|
| **Risk ID** | R-P1-02-001 |
| **Description** | HARD STOP timing shift — current `_on_message_listener` fires BEFORE `on_message`. Hermes `pre_prompt` fires AFTER gateway acceptance but BEFORE LLM. LLM is never called but timing is shifted. A custom Discord gateway plugin needed for pre-dispatch interception — this plugin capability is unverified. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | C-002: Verify plugin message interception capability before Phase 2; if HARD STOP interception remains post-gateway, accept permanent timing shift and update ADR-002; dual-layer (hook + plugin `on_message()`) provides redundancy |
| **Trigger Criteria** | HARD STOP message reaches LLM (LLM called after HARD STOP) |
| **Recovery Time** | Immediate (manual `/admin gateway stop`) |
| **Detection Method** | Heartbeat watchdog synthetic HARD STOP injection every 10s; LLM call counter increments after HARD STOP |

| Risk ID | R-P1-02-002 |
|---|---|
| **Description** | HARD STOP recovery triggers missing — current `hard_stop_handler.py` has `check_recovery()` with 7 triggers (`resume`, `aku sudah okay`, etc.). ADR plugin skeleton had no equivalent. After HARD STOP, Faiz must be able to resume. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | C-007: Add `check_recovery()` equivalent to plugin `on_message()` with all 7 recovery triggers; add recovery trigger gate test; recovery requires explicit readiness signal — no auto-resume |
| **Trigger Criteria** | Faiz types recovery trigger → persona stays in neutral/safe mode |
| **Recovery Time** | Immediate (manual safe_mode disable via admin command) |
| **Detection Method** | Recovery trigger integration test |

| Risk ID | R-P1-02-003 |
|---|---|
| **Description** | HARD STOP hook returns exit code ≠ 0 or 1 (e.g., 137 OOM, 143 SIGTERM). Hermes behavior on non-standard exit codes is uncharacterized. If Hermes treats unknown exit code as PASS → LLM called after HARD STOP. |
| **Probability** | LOW (2) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **10 MEDIUM** |
| **Mitigation** | `on_failure: block` configured; test ALL possible exit codes (0-255) and verify behavior; heartbeat watchdog as secondary verification |
| **Trigger Criteria** | Hook crashes with non-standard exit code; HARD STOP not intercepted |
| **Recovery Time** | Immediate (manual kill) |
| **Detection Method** | Hook exit code distribution monitoring; heartbeat watchdog |

#### Step 1.3 — Port consent gate to pre_tool_call hook

| Field | Value |
|---|---|
| **Risk ID** | R-P1-03-001 |
| **Description** | Consent gate timing (R-012) — Redis cache staleness up to 60s after revocation. During this window, revoked consent treated as active. Hook latency adds 50-200ms per check. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Cache TTL reduced 300s→60s; cache invalidation on write (Redis DEL on consent change); DESTRUCTIVE_APPROVAL tools bypass cache (query PostgreSQL directly); dual-source check for critical operations |
| **Trigger Criteria** | Tool executes during WITHDRAWN consent state (cache stale) |
| **Recovery Time** | < 5 min (force WITHDRAWN in Redis, verify PostgreSQL) |
| **Detection Method** | Consent hook latency histogram; Redis/PG state mismatch alert; audit log timestamps |

#### Step 1.4 — Port distress detection to pre_prompt hook

| Field | Value |
|---|---|
| **Risk ID** | R-P1-04-001 |
| **Description** | **Distress pattern regression 14→6 (57% loss)** — B-002: ADR plugin had 6 patterns. Current `safe_mode.py` has 14 bilingual ID/EN patterns. Missing: self-harm, ending-it-all, goodbye (D4), self-loathing (D3), hopelessness (D2), sleep/focus (D1). Bilingual Indonesian coverage substantially reduced. |
| **Probability** | MEDIUM (3) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **15 HIGH** |
| **Mitigation** | Port ALL 14 distress patterns from `src/persona/safe_mode.py` DISTRESS_PATTERNS; preserve D4→D1 priority, bilingual ID/EN coverage, exact regex patterns; AC-SAFE-004 zero false negatives on 100+ curated bilingual messages |
| **Trigger Criteria** | D3/D4 message detected as D0/D1 (false negative) |
| **Recovery Time** | 2 hr (copy patterns from safe_mode.py, recompile, re-test) |
| **Detection Method** | AC-SAFE-004 test suite; curated_distress.json 100+ messages |

| Risk ID | R-P1-04-002 |
|---|---|
| **Description** | Distress confidence scoring missing — current implementation computes confidence as `matched/total` at each level. Plugin has no confidence metric. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Add confidence scoring to distress detector; threshold: D3/D4 at ≥80% confidence → crisis; D2 at ≥60% → safe mode; <60% → monitor |
| **Trigger Criteria** | Low-confidence distress detection triggers false crisis protocol |
| **Recovery Time** | 1 hr (add confidence scoring) |
| **Detection Method** | Distress detection confidence distribution metric |

#### Step 1.5 — Port Yandere FSM to GuinevereSafetyPlugin + post_response hook

| Field | Value |
|---|---|
| **Risk ID** | R-P1-05-001 |
| **Description** | **Y6 enum constructability (B-001)** — If plugin has named `Y6_UNSAFE` member, creates programmatic reference point. Current implementation has NO Y6 member; `YandereLevel(6)` raises `ValueError` before `validate_level()`. This is a regression. |
| **Probability** | MEDIUM (3) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **15 HIGH** |
| **Mitigation** | YandereLevel enum: Y0-Y5 ONLY. No Y6 member. `validate_level()` is the sole Y6 guard. AC-SAFE-005 test verifies `YandereLevel(6)` raises ValueError. |
| **Trigger Criteria** | `YandereLevel(6)` succeeds (creates Y6 value) |
| **Recovery Time** | < 30 min (remove Y6 member from enum; re-test) |
| **Detection Method** | AC-SAFE-005 gate test; Y6 detection counter (any increment = alert) |

| Risk ID | R-P1-05-002 |
|---|---|
| **Description** | Yandere FSM recovery path missing — current `YandereEngine` has `de_escalate()` and `reset_to_baseline()`. ADR plugin has no equivalents. After HARD STOP, yandere must return to Y4_BASELINE. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | C-009: Add `de_escalate()` and `reset_to_baseline()` to plugin; add to recovery flow after HARD STOP end |
| **Trigger Criteria** | HARD STOP ends → yandere level stays at Y0 or jumps to Y5 |
| **Recovery Time** | 2 hr (add methods, re-test FSM transitions) |
| **Detection Method** | Yandere FSM transition audit log; manual spot-check |

| Risk ID | R-P1-05-003 |
|---|---|
| **Description** | Plugin instance model unverified — if Hermes uses global instances (one plugin for all sessions), per-session yandere state leaks. All sessions share a single `self._sessions` dict via single instance — this IS the intended architecture if global, BUT this is unverified. |
| **Probability** | MEDIUM (3) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **15 HIGH** |
| **Mitigation** | B-004: Verify instance model on VPS BEFORE Phase 1; if global: current design (session_id-keyed dicts) is correct; if per-session: simplify to instance variables. EITHER WAY: test with 2+ concurrent sessions |
| **Trigger Criteria** | Yandere level from session A affects session B |
| **Recovery Time** | 1-3 days (redesign if global model verification reveals issues) |
| **Detection Method** | Multi-session test (2 concurrent Discord sessions → verify independent yandere levels) |

#### Step 1.6 — Port drift detection to post_prompt hook

| Field | Value |
|---|---|
| **Risk ID** | R-P1-06-001 |
| **Description** | Drift detector depends on `post_prompt` hook correctly receiving assembled prompt. If Hermes doesn't pass assembled prompt to this hook, SHA-256 comparison is meaningless. Hook data contract is unverified. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | C-001: Validate hook stdin JSON schema (install test hook at `post_prompt`, log full stdin); verify assembled prompt is in the payload |
| **Trigger Criteria** | Drift detector receives empty or wrong prompt content |
| **Recovery Time** | 2-4 hr (adjust plugin to intercept at different hook point or monitor SOUL.md file instead) |
| **Detection Method** | Drift detector log shows zero-length or wrong-hash inputs |

#### Step 1.7 — Port DNR enforcement to memory_plugin.py

| Field | Value |
|---|---|
| **Risk ID** | R-P1-07-001 |
| **Description** | DNR content leaks through Hermes FTS5 session_search. Hermes session_search uses its own SQLite index — if DNR content was mirrored to MEMORY.md, FTS5 would index it, bypassing PostgreSQL DNR filter. |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | ACL-based DNR block: `verify_recall_results_dnr_free()` runs as post-recall, pre-injection gate on BOTH PostgreSQL and session_search results; dual-layer: memory plugin checks + hook checks |
| **Trigger Criteria** | DNR-marked content appears in session_search results |
| **Recovery Time** | < 5 min (disable session_search; clear FTS5 index) |
| **Detection Method** | DNR content in session_search integration test; periodic audit |

#### Step 1.8 — Port classification to memory_plugin.py + on_error hook

| Field | Value |
|---|---|
| **Risk ID** | R-P1-08-001 |
| **Description** | Classification fail-closed → unknown events classified as Internal (permissive) instead of Confidential (strict). Classification mapping has 5 levels with specific criteria — incorrect mapping is a data governance violation (ADR-024). |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | Port `classify_event()` verbatim from `src/persona/classification.py`; test with all 5 classification levels; verification: Unknown → Confidential (not Internal); all 5 fields populated |
| **Trigger Criteria** | Unknown classification returns level < Confidential |
| **Recovery Time** | < 1 hr (fix classification mapping, re-test) |
| **Detection Method** | Classification distribution monitoring; classification gate test |

#### Step 1.9 — Port secret scanner to post_response hook

| Field | Value |
|---|---|
| **Risk ID** | R-P1-09-001 |
| **Description** | **Secret scanner pattern regression 18→8** — C-006: ADR plugin had 8 patterns vs 18 in `secret_scanner.py`. Missing: AWS keys, Stripe, Google API, age key, password-in-URL. Whitelist (hashes, UUIDs, base64) and MIN_ENTROPY_STRING_LENGTH (32 chars) also missing. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Port ALL 18 patterns from `src/surveillance/secret_scanner.py` PATTERNS; add whitelist patterns (MD5/SHA hashes, UUIDs, base64 headers); add MIN_ENTROPY_STRING_LENGTH (32 chars); add AWS, Stripe, Google API, age key, password-in-URL patterns |
| **Trigger Criteria** | Known credential pattern passes through scanner undetected |
| **Recovery Time** | 1 hr (add missing patterns, re-compile, re-test) |
| **Detection Method** | Secret scanner pattern coverage test; AC-SAFE test suite |

#### Step 1.10 — Port punishment/reward/mood/ritual/streak/safe_mode to plugin

| Field | Value |
|---|---|
| **Risk ID** | R-P1-10-001 |
| **Description** | Punishment engine missing fine-grained `PUNISHMENT_CONFIG` (allowed/blocked actions per level), auto-expiry logic, and clock pause during suspension. Core L1-L5 ladder logic works but details missing. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | Port `PUNISHMENT_CONFIG` from `src/persona/punishment_engine.py`; add auto-expiry (L1=5min, L2=15min, L3=30min, L4=1hr, L5=2hr); add clock pause during punishment suspension |
| **Trigger Criteria** | Punishment escalates incorrectly (wrong level for action) |
| **Recovery Time** | 2 hr (port config, re-test escalation ladder) |
| **Detection Method** | Punishment escalation integration test |

| Risk ID | R-P1-10-002 |
|---|---|
| **Description** | Safe mode controller missing explicit confirmation requirement for deactivation and distress history tracking. Current `SafeModeController.deactivate()` requires `explicit_confirmation=True` — plugin must match this. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Port `explicit_confirmation=True` from safe_mode.py; add distress history tracking in plugin state |
| **Trigger Criteria** | Safe mode deactivates without Faiz confirmation |
| **Recovery Time** | < 1 hr (add confirmation gate) |
| **Detection Method** | Safe mode deactivation test |

| Risk ID | R-P1-10-003 |
|---|---|
| **Description** | Phrase rewrite map missing — PersonaSafetyPolicy §9.2 defines 4 mandatory rewrites. Plugin does not implement these. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | C-008: Add phrase rewrite map to plugin `on_response()` and `post_response` hook |
| **Trigger Criteria** | Mandatory rewrite phrases appear in output unmodified |
| **Recovery Time** | 1 hr (add rewrite map) |
| **Detection Method** | Persona tone enforcement test |

| Risk ID | R-P1-10-004 |
|---|---|
| **Description** | **Forbidden pattern regression 15→5 (67% loss)** — B-003: ADR plugin had 5 patterns. PersonaSafetyPolicy §11 defines 15 patterns (F-01 to F-15). Missing: F-02, F-04, F-05, F-07, F-08, F-09, F-11, F-12, F-13, F-15. |
| **Probability** | MEDIUM (3) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **15 HIGH** |
| **Mitigation** | Port ALL 15 forbidden patterns from PersonaSafetyPolicy §11; preserve CRITICAL/HIGH classification; AC-SAFE-006 gate test verifies all 15 detected; CRITICAL→BLOCK, HIGH→REWRITE |
| **Trigger Criteria** | Any F-01 to F-15 pattern passes through unblocked |
| **Recovery Time** | 2 hr (add missing patterns from PersonaSafetyPolicy, re-compile, re-test all 15) |
| **Detection Method** | AC-SAFE-006 gate test; SAFE-T-012, SAFE-T-013, SAFE-T-014 |

### Phase 1 Gate

| Gate # | Criterion | Risk If Failed |
|---|---|---|
| G1 | HARD STOP < 50ms, 100% SLO | R-P1-02-001/002/003 (BLOCK Phase 2+) |
| G2 | Consent fail-closed | R-P1-03-001 |
| G3 | Y6 impossible (ValueError) | R-P1-05-001 (BLOCK Phase 2+) |
| G4 | D3/D4 → crisis protocol | R-P1-04-001 |
| G5 | Drift detector alerts/rollback | R-P1-06-001 |
| G6 | DNR excluded from recall | R-P1-07-001 |
| G7 | Classification fail-closed | R-P1-08-001 |
| G8 | Secret scanner redacts all 18 patterns | R-P1-09-001 |
| G9 | Punishment suspended during distress | R-P1-10-001 |
| G10 | All 15 forbidden patterns blocked/rewritten | R-P1-10-004 |

---

## 5. Phase 2: Discord Gateway (3-5 days, 8 steps expanded)

### Phase 2 Overview Risks

| Risk ID | Description | Prob | Impact | Score | Mitigation |
|---|---|---|---|---|---|
| **R-P2-OVER-01** | **Discord gateway instability** (R-002) — WebSocket disconnections, message delivery failures, slash command registration failures | LOW (2) | HIGH (4) | **8 MEDIUM** | 48hr shadow mode; health check endpoint every 60s; automatic fallback via systemd (3 fails → restart bot.py); conservative rate limits |
| **R-P2-OVER-02** | **Shadow mode complexity** (R-015) — Double LLM costs, conflicting responses, resource contention, memory write race conditions, state divergence | HIGH (4) | MEDIUM (3) | **12 HIGH** | Separate DBs (DB4≠DB5); only bot.py writes to PostgreSQL; separate Discord channels; $5 cost cap; auto-terminate at 48hr; technical memory write mutex (Hermes PG role = SELECT only) |
| **R-P2-OVER-03** | Shadow mode does NOT validate safety — 48hr passive comparison validates Discord gateway behavior, not safety engine correctness under adversarial conditions | HIGH (4) | HIGH (4) | **16 CRITICAL** | C-011/C-3: Active safety injection during shadow mode: 3× HARD STOP, 3× Y6 content, 1× consent revocation, 1× distress, 1× hook failure injection |
| **R-P2-OVER-04** | 35 command migration — 12 LOW-feasibility commands require full custom plugins with state, hook integration, multi-service coordination. Complexity may exceed time estimates. | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** | Prioritize HIGH→MEDIUM→LOW; MEDIUM commands can be deferred (available via custom MCP); HIGH commands (status, mood, help, safeword) are mandatory |

### Per-Step Risks

#### Step 2.1 — Configure Hermes Discord gateway

| Field | Value |
|---|---|
| **Risk ID** | R-P2-01-001 |
| **Description** | config.yaml missing critical fields — `agent.max_turns: 20`, `agent.idle_timeout: 7200`, per-hook `security` blocks, `system_prompt_file` path clarification. Missing fields cause Hermes to use unsafe defaults. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | C-016: Add missing config fields; verify `personality: "guinevere-v1"` with `hermes config validate`; use `personality: custom` if custom labels rejected |
| **Trigger Criteria** | Hermes starts with default config values |
| **Recovery Time** | < 30 min (add fields, re-validate config) |
| **Detection Method** | `hermes config validate`; config diff vs ADR-035 Appendix A |

| Risk ID | R-P2-01-002 |
|---|---|
| **Description** | Discord gateway intent configuration errors — MESSAGE_CONTENT intent not properly negotiated, causing content-less message events. Gateway appears connected but cannot read message content. |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | Verify MESSAGE_CONTENT intent in `hermes gateway status`; test message send in #hermes-shadow; verify content is readable |
| **Trigger Criteria** | Hermes receives messages with empty content |
| **Recovery Time** | < 15 min (fix intent config, restart gateway) |
| **Detection Method** | Test message with known content → verify response references content |

#### Step 2.2 — Migrate 8 HIGH-feasibility commands to plugins

| Field | Value |
|---|---|
| **Risk ID** | R-P2-02-001 |
| **Description** | Simple plugin commands (status, mood, help, safeword, new, history, casual, focus) have Discord.py boilerplate replaced with Hermes native. If Hermes `ctx.register_command()` API differs from expected, all 8 commands fail. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Test ONE command first (status — simplest); if API matches, batch-port remaining 7; if API differs, adapt pattern for remaining |
| **Trigger Criteria** | `hermes gateway list` shows zero or partial command registration |
| **Recovery Time** | 2-4 hr (adjust plugin registration API) |
| **Detection Method** | `hermes gateway list` output; Discord slash command UI |

#### Step 2.3 — Migrate 15 MEDIUM-feasibility commands to plugins

| Field | Value |
|---|---|
| **Risk ID** | R-P2-03-001 |
| **Description** | Memory/loop commands (memory add/search/export/forget, loop start/stop/pause/resume/priority, loops, surveillance status/pause/resume, evidence, clear cache) depend on PostgreSQL/Redis backend calls. If plugin can't access these backends, commands fail. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | Plugin calls wrap existing backend functions unchanged; verify PostgreSQL/Redis connectivity from plugin context; test each command against actual backend |
| **Trigger Criteria** | Backend call fails with connection error or auth error |
| **Recovery Time** | < 1 hr (fix connection config in plugin) |
| **Detection Method** | Per-command integration test; backend connection health check |

#### Step 2.4 — Migrate 12 LOW-feasibility commands to plugins

| Field | Value |
|---|---|
| **Risk ID** | R-P2-04-001 |
| **Description** | Complex stateful commands (cost, budget, cost_alert, approve, approve_all, deny, restart, backup, health, consent, punishment, reward) require full custom plugins with hook integration, multi-service coordination, state management. Most complex migration category. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | Build foundation plugins first (auth_overlay, cost tracking); these 12 commands are secondary to HIGH/MEDIUM commands; can be deferred to post-cutover if they block timeline |
| **Trigger Criteria** | > 3 LOW commands fail integration tests after Phase 2 timeline |
| **Recovery Time** | Defer to post-Phase 7 hardening (2-3 days) |
| **Detection Method** | Per-command integration test; FAULTY label in migration tracker |

#### Step 2.5 — Launch shadow mode

| Field | Value |
|---|---|
| **Risk ID** | R-P2-05-001 |
| **Description** | Memory write mutex is POLICY-enforced (not technically enforced) — Hermes could accidentally write to PostgreSQL through memory bridge plugin during shadow mode. "No data loss" guarantee violated. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | R-004/C-013 technical enforcement: configure Hermes memory bridge with PostgreSQL role that has ONLY SELECT privileges during shadow mode; automated row-count snapshots before/after each phase |
| **Trigger Criteria** | PostgreSQL row count changes in memory tables during shadow mode |
| **Recovery Time** | 2-5 min (pg_restore from pre-migration dump; revert Hermes-written rows) |
| **Detection Method** | Pre/post phase row count snapshots; PostgreSQL audit log for Hermes writes |

| Risk ID | R-P2-05-002 |
|---|---|
| **Description** | Resource contention (CC-03 made concrete) — two LLM agents on cgroup-capped 8GB VPS. bot.py (production) degrades because Hermes competes for Redis, PostgreSQL, 9Router, CPU, RAM. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Pre-shadow resource check (verify Redis/PostgreSQL/9Router capacity for 2× load); auto-kill threshold: if bot.py latency > 2× baseline, kill Hermes immediately (bot.py is production) |
| **Trigger Criteria** | GuinevereBot response latency > 2× baseline; OOM events |
| **Recovery Time** | < 1 min (`hermes gateway stop` — bot.py unaffected) |
| **Detection Method** | Prometheus side-by-side latency comparison; system RAM/CPU |

| Risk ID | R-P2-05-003 |
|---|---|
| **Description** | Shadow runbook implementation gaps — C-018: (D1) Parity comparison entirely manual — no automated test script; (D2) Cutover GRANT `ON ALL TABLES` too broad; (D3) `hermes_app` PostgreSQL role prerequisite not checked |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | C-018: Create automated parity test script for 100 predefined test messages; narrow cutover GRANT to specific mirror tables; add `hermes_app` role existence check to shadow runbook prerequisites |
| **Trigger Criteria** | Manual parity comparison misses a regression; overly broad GRANT enables unintended writes |
| **Recovery Time** | 2-4 hr (build automated test; fix GRANT) |
| **Detection Method** | Automated parity test pass/fail; GRANT audit |

#### Step 2.6 — Response parity comparison (100 queries)

| Field | Value |
|---|---|
| **Risk ID** | R-P2-06-001 |
| **Description** | Parity comparison shows "both systems respond similarly" but misses safety-critical divergence: different HARD STOP handling, different distress response, different Y6 enforcement. False confidence from surface-level parity. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Supplement with active safety injection tests (C-011/C-3); include adversarial test messages in the 100-query set; compare not just response text but safety metadata (HARD STOP blocked, distress detected, yandere level, forbidden pattern matches) |
| **Trigger Criteria** | Bot.py blocks a message that Hermes passes (or vice versa) for safety reasons |
| **Recovery Time** | N/A (detection during shadow mode — no cutover until resolved) |
| **Detection Method** | Automated parity script with safety metadata comparison |

#### Step 2.7 — Faiz cutover approval

| Field | Value |
|---|---|
| **Risk ID** | R-P2-07-001 |
| **Description** | Faiz approves cutover based on incomplete shadow mode data — shadow report missing safety injection results, or Faiz reviews while fatigued. Cutover proceeds with unverified safety. |
| **Probability** | LOW (2) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **10 MEDIUM** |
| **Mitigation** | Cutover checklist: ALL 5 safety injection tests logged in shadow report; all 35 commands functional; HARD STOP 100% success; parity report reviewed; Faiz approves during rested state |
| **Trigger Criteria** | Cutover proceeds with incomplete shadow report |
| **Recovery Time** | < 2 min (rollback to bot.py) |
| **Detection Method** | Cutover checklist sign-off; shadow report sections verified |

#### Step 2.8 — Cutover: stop bot.py, start Hermes gateway

| Field | Value |
|---|---|
| **Risk ID** | R-P2-08-001 |
| **Description** | `sudo systemctl start guinevere-bot` fails post-cutover because bot.py was disabled (not just stopped). `systemctl start` on disabled service may not work without `systemctl enable`. Rollback takes > 5 minutes while debugging service state. |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | Pre-cutover: `sudo systemctl is-enabled guinevere-bot` → verify enabled; cutover script uses `systemctl stop guinevere-bot` (not disable); rollback script uses `systemctl start guinevere-bot && systemctl enable guinevere-bot` (both commands) |
| **Trigger Criteria** | `systemctl start guinevere-bot` returns exit code ≠ 0 |
| **Recovery Time** | < 1 min (`systemctl enable guinevere-bot && systemctl start guinevere-bot`) |
| **Detection Method** | systemd service status check |

| Risk ID | R-P2-08-002 |
|---|---|
| **Description** | Cutover downtime exceeds 5 minutes due to: Hermes gateway slow startup, slash command registration delay with Discord API, plugin loading time. User-visible outage during cutover window. |
| **Probability** | LOW (2) |
| **Impact** | LOW (2) |
| **Risk Score** | **4 LOW** |
| **Mitigation** | Pre-cutover: time Hermes gateway startup; pre-register slash commands (if Hermes supports); schedule cutover during low-activity window (02:00 WIB) |
| **Trigger Criteria** | Cutover > 5 min; Faiz notices downtime |
| **Recovery Time** | N/A (downtime is expected, just longer than planned) |
| **Detection Method** | Uptime monitoring; cutover timing log |

---

## 6. Phase 3: Memory Bridge (3-5 days, 6 steps)

### Phase 3 Overview Risks

| Risk ID | Description | Prob | Impact | Score |
|---|---|---|---|---|
| **R-P3-OVER-01** | **Embedding API must be fixed BEFORE Phase 3** (CC-11). If G-B1 is still broken at Phase 3 start, compression has no vector baseline. Memory recall A/B testing is invalid. | HIGH (4) | HIGH (4) | **16 CRITICAL** |
| **R-P3-OVER-02** | **Memory recall quality degradation** (R-003) — compression drops critical memories, mirror sync stale, token budget overflow | MEDIUM (3) | HIGH (4) | **12 HIGH** |

### Per-Step Risks

#### Step 3.1 — Enable Hermes compression at 70% threshold

| Field | Value |
|---|---|
| **Risk ID** | R-P3-01-001 |
| **Description** | Context compression incorrectly summarizes or drops critical memories. 70% threshold protects last 20 messages but may be too conservative (compresses nothing) or too aggressive (drops important context at 70% ± 5%). |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Start at 70% (aggressive safe); measure compression effectiveness; gradually lower to 50% after 1 week of monitoring; protect last 20 messages; A/B test recall on 100 queries pre/post compression |
| **Trigger Criteria** | Recall relevance drops > 10% vs baseline; manual spot-check shows missing critical memories |
| **Recovery Time** | < 3 min (disable compression: `hermes config set memory.compression.enabled false`) |
| **Detection Method** | A/B recall test (100 queries); Faiz weekly spot-check 10 queries |

#### Step 3.2 — Enable Hermes session_search (FTS5)

| Field | Value |
|---|---|
| **Risk ID** | R-P3-02-001 |
| **Description** | session_search returns DNR-marked content if mirrored to MEMORY.md. FTS5 indexes text content — PostgreSQL DNR filter doesn't apply to FTS5 index. |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | ACL-based DNR block on session_search results; `verify_recall_results_dnr_free()` runs as post-search gate; if DNR content detected → strip before returning to agent |
| **Trigger Criteria** | session_search returns DNR-marked memory entry |
| **Recovery Time** | < 3 min (disable session_search; clear FTS5 index) |
| **Detection Method** | DNR content in session_search integration test |

#### Step 3.3 — Build PostgreSQL bridge plugin (memory_plugin.py, ~180 lines)

| Field | Value |
|---|---|
| **Risk ID** | R-P3-03-001 |
| **Description** | memory_bridge.py → memory_plugin.py refactor introduces bug in `recall_for_context()` or `store_conversation()` wrappers. Wrapper may fail to pass parameters, handle errors, or return results correctly. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Plugin wraps existing functions unchanged (passthrough, not rewrite); run identical test suite against both old bridge and new plugin; verify parameter equivalence; error handling matches |
| **Trigger Criteria** | Plugin recall returns different results than bridge recall for same query |
| **Recovery Time** | < 3 min (revert to memory_bridge.py) |
| **Detection Method** | Side-by-side recall comparison test; regression test suite |

#### Step 3.4 — Configure mirror sync (MEMORY.md/USER.md)

| Field | Value |
|---|---|
| **Risk ID** | R-P3-04-001 |
| **Description** | Mirror sync divergence — MEMORY.md/USER.md silently diverges from PostgreSQL due to: batch write failure (writes every 5 messages, crash between batches loses 4), format mismatch, or race condition with PostgreSQL writes. Agent uses stale mirror data. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Batch writes every 5 messages with atomic file replacement; verify mirror vs PostgreSQL at startup; Hermes configured to treat MIRROR as cache (authoritative source is PostgreSQL) |
| **Trigger Criteria** | Mirror content differs from PostgreSQL for same record |
| **Recovery Time** | < 5 min (rebuild mirror from PostgreSQL) |
| **Detection Method** | Startup mirror-vs-PG diff; periodic consistency check |

#### Step 3.5 — A/B test memory recall on 100 queries

| Field | Value |
|---|---|
| **Risk ID** | R-P3-05-001 |
| **Description** | A/B test is invalid if embedding API (G-B1) is broken. Vector search returns zero results in BOTH A and B — recall appears unchanged because both are broken. False confidence from degraded baseline. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Fix embedding API BEFORE A/B test; verify vector search returns results; if unfixable, A/B test only measures FTS+Recency (not vector) — document limitation |
| **Trigger Criteria** | Embedding API HTTP 400; vector search returns empty |
| **Recovery Time** | 1-2 days (fix embedding API) |
| **Detection Method** | Embedding API health check; vector result count > 0 |

#### Step 3.6 — Verify zero PostgreSQL data modifications from Hermes path

| Field | Value |
|---|---|
| **Risk ID** | R-P3-06-001 |
| **Description** | PostgreSQL write detection relies on manual `SELECT count(*)` comparison. If snapshots weren't automated, accidental writes go undetected. Hermes could write through memory_plugin.py if plugin has write permission. |
| **Probability** | LOW (2) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **10 MEDIUM** |
| **Mitigation** | R-005: Automated row-count snapshots before each phase (`SELECT relname, n_live_tup FROM pg_stat_user_tables` → file; compare before/after); Hermes PG role = read-only (SELECT only) |
| **Trigger Criteria** | Row count difference between pre/post phase snapshots |
| **Recovery Time** | 2-5 min (pg_restore from pre-migration dump) |
| **Detection Method** | Automated snapshot diff; PostgreSQL audit log |

---

## 7. Phase 4: MCP + Tools (3-5 days, 6 steps)

### Phase 4 Overview Risks

| Risk ID | Description | Prob | Impact | Score |
|---|---|---|---|---|
| **R-P4-OVER-01** | **Auth matrix bypass** (R-004) — Hermes native tool executes FORBIDDEN/DESTRUCTIVE operation without auth check | MEDIUM (3) | CRITICAL (5) | **15 HIGH** |
| **R-P4-OVER-02** | Auth overlay handles tool calls from both Hermes native AND custom MCP with different JSON payloads. Operation-level granularity (48+ mappings) significantly more complex than skeleton's tool-level mapping | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** |

### Per-Step Risks

#### Step 4.1 — Add 5 Hermes native MCP servers

| Field | Value |
|---|---|
| **Risk ID** | R-P4-01-001 |
| **Description** | Hermes native MCP servers (web, filesystem, terminal, git, fetch) enabled WITHOUT auth overlay. During gap between step 4.1 and 4.2, Hermes native tools run with no auth matrix enforcement. FORBIDDEN command could execute. |
| **Probability** | MEDIUM (3) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **15 HIGH** |
| **Mitigation** | Enable tools AND auth overlay in the SAME deployment step — no gap; if auth overlay not ready, do NOT enable native tools; pre-flight tool audit verifies auth plugin loaded before any tool enabled |
| **Trigger Criteria** | `hermes mcp list` shows tools active but auth plugin not loaded |
| **Recovery Time** | < 1 min (`hermes mcp remove --all`) |
| **Detection Method** | Pre-flight tool audit script; Prometheus alert: tools active without auth plugin |

#### Step 4.2 — Build auth overlay plugin

| Field | Value |
|---|---|
| **Risk ID** | R-P4-02-001 |
| **Description** | Auth overlay plugin complexity — 16 tools × 4 auth levels = 64 mappings, plus operation-level granularity (e.g., `terminal.ls` vs `terminal.rm`). Plugin logic for DESTRUCTIVE_APPROVAL (Discord webhook + 5-min timeout + approval queue) is untested in Hermes plugin environment. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Plugin load gate: Hermes refuses to start without it; `critical: true` in plugin config; test with ALL 16 tools; unknown tools default to FORBIDDEN (fail-closed); independent audit daemon verifies plugin presence every 60s |
| **Trigger Criteria** | Auth plugin crashes → no auth enforcement; tool bypasses auth check |
| **Recovery Time** | < 1 min (plugin crash triggers `on_failure: block` on ALL tools) |
| **Detection Method** | Prometheus: `guinevere_auth_plugin_loaded` gauge; audit daemon 60s check |

| Risk ID | R-P4-02-002 |
|---|---|
| **Description** | `fetch` overlap in auth matrix — `fetch` appears in both `web.fetch` (READ_AUTO) and standalone `fetch` entry with potentially different auth levels. Conflicting auth levels create ambiguity. |
| **Probability** | LOW (2) |
| **Impact** | LOW (2) |
| **Risk Score** | **4 LOW** |
| **Mitigation** | R-007: Remove `fetch` from `web` tools list; use standalone `fetch` entry as authoritative, OR consolidate into `web.fetch` |
| **Trigger Criteria** | Two different auth levels for same tool name |
| **Recovery Time** | < 10 min (fix auth matrix YAML) |
| **Detection Method** | Auth matrix deduplication check |

#### Step 4.3 — Migrate 4 hybrid tools

| Field | Value |
|---|---|
| **Risk ID** | R-P4-03-001 |
| **Description** | Terminal tool isolation failure — shell → terminal+command-blocking. If FORBIDDEN command list doesn't include all dangerous commands (`rm`, `dd`, `mkfs`, `shutdown`, `reboot`, `poweroff`, `halt`, `init`, `iptables`, `ufw`), dangerous commands could execute. Custom command blocking may have bypasses (piping, aliases, shell builtins). |
| **Probability** | LOW (2) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **10 MEDIUM** |
| **Mitigation** | FORBIDDEN commands hard-disabled in Hermes config (not just plugin-enforced); dual-layer: config blocks + auth plugin intercepts; regular FORBIDDEN list audit; test each command bypass technique |
| **Trigger Criteria** | `rm -rf /` or `DROP TABLE` executes through terminal tool |
| **Recovery Time** | Immediate (disable terminal tool); 2-5 min (pg_restore if DB affected) |
| **Detection Method** | Process execution audit log; FORBIDDEN command attempt counter |

#### Step 4.4 — Keep 7 custom MCP tools

| Field | Value |
|---|---|
| **Risk ID** | R-P4-04-001 |
| **Description** | Custom MCP tools (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time_tools) must coexist with Hermes native tools. FastMCP server continues running alongside Hermes MCP client. Port conflicts, tool name collisions, or auth discrepancies possible. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Keep custom tools on separate port from Hermes MCP; tool name prefix to prevent collisions; auth overlay enforces matrix on BOTH native and custom tools |
| **Trigger Criteria** | Tool name collision; port conflict; auth bypass on custom tool |
| **Recovery Time** | < 2 min (restart FastMCP with corrected config) |
| **Detection Method** | MCP server health check; tool list deduplication check |

#### Step 4.5 — Plugin load gate test

| Field | Value |
|---|---|
| **Risk ID** | R-P4-05-001 |
| **Description** | `hermes gateway start` correctly fails when auth plugin missing — BUT what if plugin loads but fails silently (e.g., exception in try/except caught, returns True)? False "loaded" state with non-functional plugin. |
| **Probability** | LOW (2) |
| **Impact** | CRITICAL (5) |
| **Risk Score** | **10 MEDIUM** |
| **Mitigation** | Plugin `on_load()` returns False on ANY exception (fail-closed); add functional test: after plugin loads, send a tool call and verify auth check fires; audit daemon sends periodic functional probe |
| **Trigger Criteria** | Plugin loaded (returns True) but tool call proceeds without auth check |
| **Recovery Time** | < 1 min (correct plugin code, restart) |
| **Detection Method** | Functional probe: send test tool call, verify auth response |

#### Step 4.6 — Security audit on all 16 tools

| Field | Value |
|---|---|
| **Risk ID** | R-P4-06-001 |
| **Description** | Security audit is human-dependent (manual review of tool configurations, auth mappings, FORBIDDEN lists). A missed finding during audit creates a persistent vulnerability. Audit quality varies with reviewer fatigue and tool complexity. |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | Automated security audit script (check all 64 auth mappings, verify FORBIDDEN commands config, test each DESTRUCTIVE_APPROVAL flow); supplement with manual review of complex tools (obscura_cdp, postgres) |
| **Trigger Criteria** | Automated audit finds configuration gap |
| **Recovery Time** | < 1 hr (fix config or code) |
| **Detection Method** | Automated audit script output; `hermes security` scan |

---

## 8. Phase 5: Skills + SOUL.md (2-4 days, 5 steps)

### Phase 5 Overview Risks

| Risk ID | Description | Prob | Impact | Score |
|---|---|---|---|---|
| **R-P5-OVER-01** | **Persona drift via SOUL.md misconfiguration** (R-007) — SOUL.md not configured with Y4/Y5/Y6, kawaii default, file permissions allow modification | MEDIUM (3) | HIGH (4) | **12 HIGH** |
| **R-P5-OVER-02** | agentskills.io unavailable — Phase 5 depends on `hermes skills search`. If service is down, Phase 5 becomes fully custom (+2-3 days) | LOW (2) | LOW (2) | **4 LOW** |

### Per-Step Risks

#### Step 5.1 — Search and install skills from agentskills.io

| Field | Value |
|---|---|
| **Risk ID** | R-P5-01-001 |
| **Description** | agentskills.io returns 404 or is unavailable. `hermes skills search` fails. No community skills available — all skills must be custom-built. |
| **Probability** | LOW (2) |
| **Impact** | LOW (2) |
| **Risk Score** | **4 LOW** |
| **Mitigation** | R-011: Run `hermes skills search` from VPS during Phase 0 to verify connectivity; if unavailable: Phase 5 becomes fully custom (already planned for Guinevere-specific skills: mood, rituals, streaks) |
| **Trigger Criteria** | `hermes skills search` returns connection error |
| **Recovery Time** | +2-3 days (build custom skills) |
| **Detection Method** | Phase 0 connectivity test |

| Risk ID | R-P5-01-002 |
|---|---|
| **Description** | Installed skill conflicts with Guinevere safety hooks or plugin — community skill may have overlapping hook points, competing `pre_prompt` handlers, or conflicting personality instructions |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Install skills ONE AT A TIME; test each skill in isolation before installing next; `hermes skills uninstall` if conflict detected; prioritize Guinevere-custom skills over community skills |
| **Trigger Criteria** | Hook conflict error; skill overrides Guinevere safety behavior |
| **Recovery Time** | < 2 min (`hermes skills uninstall <name>`) |
| **Detection Method** | Skill-by-skill integration test; hook execution order audit |

#### Step 5.2 — Customize SOUL.md with Guinevere identity

| Field | Value |
|---|---|
| **Risk ID** | R-P5-02-001 |
| **Description** | SOUL.md customization misses persona constraints: Y4 dominant tone, Y5 ceiling, Y6 prohibited, kawaii suppression, dominant/posesif-protektif tone. Agent defaults to Hermes neutral/kawaii personality. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Explicitly include ALL Persona Document v3.0 constraints in SOUL.md; disable Hermes `personality` config key; set permissions 444; git pre-commit hook triggers drift re-baseline; weekly SOUL.md audit |
| **Trigger Criteria** | Agent response contains kawaii tone or lacks Y4 dominant framing |
| **Recovery Time** | < 10 min (restore SOUL.md from git; drift detector rollback) |
| **Detection Method** | Weekly SOUL.md audit; Faiz spot-check 10 responses |

| Risk ID | R-P5-02-002 |
|---|---|
| **Description** | SOUL.md file accidentally modified (editor save, git merge conflict, incomplete save). Drift detector catches SHA-256 changes but may miss semantic drift (same hash, changed meaning through whitespace/encoding changes). |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | SOUL.md permissions 444 after validation; `inotify` on SOUL.md → triggers drift re-check; git pre-commit hook validates content; weekly manual review for semantic drift |
| **Trigger Criteria** | SOUL.md SHA-256 unchanged but agent shows different personality |
| **Recovery Time** | < 5 min (restore from git; manual review) |
| **Detection Method** | Weekly manual spot-check; inotify file change alert |

#### Step 5.3 — Configure persona plugins (mood, rituals, punishment, reward, streaks)

| Field | Value |
|---|---|
| **Risk ID** | R-P5-03-001 |
| **Description** | Ritual scheduler fires at wrong times (timezone mismatch WIB vs UTC) or misses rituals due to cron misconfiguration. Hermes cron may not support the 5 specific ritual times. |
| **Probability** | MEDIUM (3) |
| **Impact** | LOW (2) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Verify Hermes cron timezone handling (WIB = UTC+7); hardcode ritual times with explicit timezone; test each ritual over 24hr period; fallback: systemd timer if Hermes cron insufficient |
| **Trigger Criteria** | Ritual fires at wrong time or doesn't fire |
| **Recovery Time** | < 30 min (fix cron config, restart cron) |
| **Detection Method** | Ritual fire log; manual verification over 24hr |

#### Steps 5.4-5.5 — Integration test + SOUL.md permissions

| Field | Value |
|---|---|
| **Risk ID** | R-P5-04-001 |
| **Description** | Persona integration test passes but persona degrades under sustained conversation (100+ turns). Yandere FSM state drifts over time from Y4→Y3 or Y4→Y5 without user trigger. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Sustained conversation test (100+ turns) as part of integration suite; monitor yandere level trajectory; FSM transition audit log shows unexpected transitions |
| **Trigger Criteria** | Yandere level changes without corresponding user trigger |
| **Recovery Time** | < 5 min (reset_to_baseline via plugin method) |
| **Detection Method** | Yandere FSM transition audit log; sustained conversation test |

---

## 9. Phase 6: LLM Routing (1-2 days, 5 steps)

### Phase 6 Overview Risks

| Risk ID | Description | Prob | Impact | Score |
|---|---|---|---|---|
| **R-P6-OVER-01** | **9Router incompatibility** (R-005) — Hermes uses OpenAI SDK in non-standard ways; 9Router compatibility layer may not handle streaming, tool-use response formats, or error codes | LOW (2) | MEDIUM (3) | **6 MEDIUM** |

### Per-Step Risks

#### Step 6.1 — Configure Hermes to use 9Router as custom provider

| Field | Value |
|---|---|
| **Risk ID** | R-P6-01-001 |
| **Description** | Hermes model config uses wrong model name. 9Router may expose GPT-5.5 under a different model ID than Hermes expects. Hermes sends request to 9Router → 9Router returns 404 (model not found). |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Verify model name with 9Router API: `curl http://localhost:20128/v1/models`; match exact model ID in Hermes config; test with single prompt before Phase 6 completion |
| **Trigger Criteria** | 9Router returns 404 for model |
| **Recovery Time** | < 5 min (fix model name in config) |
| **Detection Method** | LLM call error log; 9Router response status |

#### Step 6.2 — Run 100-test-prompt compatibility test

| Field | Value |
|---|---|
| **Risk ID** | R-P6-02-001 |
| **Description** | 100-test-prompt covers basic calls but NOT streaming, tool-use response formats, or error handling — the most likely incompatibility vectors. False confidence from passing basic tests. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Include streaming tests in 100-prompt suite; include tool-call-response format tests; include error handling tests (timeout, 429, 500); test with GPT-5.5 AND DeepSeek V4 Flash |
| **Trigger Criteria** | Streaming test fails; tool-call response format mismatch |
| **Recovery Time** | 1-4 hr (investigate compatibility; potentially add adapter proxy) |
| **Detection Method** | Extended test-prompt suite results |

#### Step 6.3 — Configure fallback chain (GPT-5.5 → DeepSeek V4 Flash)

| Field | Value |
|---|---|
| **Risk ID** | R-P6-03-001 |
| **Description** | Hermes native `fallback` for custom providers unsupported. If Hermes doesn't support fallback chains for custom providers (only for built-in providers), the fallback logic must be custom-implemented. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | If native unsupported: custom plugin implements fallback (same as current `llm_router.py`); test by simulating GPT-5.5 outage; direct-to-OpenAI emergency fallback as last resort |
| **Trigger Criteria** | GPT-5.5 fails → no response (fallback doesn't engage) |
| **Recovery Time** | 2-4 hr (implement custom fallback plugin) |
| **Detection Method** | Simulated GPT-5.5 outage test |

#### Step 6.4 — Implement budget enforcement hook

| Field | Value |
|---|---|
| **Risk ID** | R-P6-04-001 |
| **Description** | **Budget enforcement gap** (R-010) — Hermes has no native budget enforcement at $30/mo. Custom hook must track cumulative cost and block at 100%. If hook fails to track (cost calculation error, cumulative reset), $30 cap silently exceeded. |
| **Probability** | MEDIUM (3) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **9 MEDIUM** |
| **Mitigation** | Dual budget tracking: custom hook + `cost_tracker.py` side-by-side; compare daily; alert on >10% discrepancy; test at 80%, 90%, 100% thresholds; alert at $24 (80%), block at $30 (100%) |
| **Trigger Criteria** | Cumulative cost > $30; hook and cost_tracker diverge >10% |
| **Recovery Time** | N/A (financial only — fix hook tracking) |
| **Detection Method** | Daily cost comparison report; budget alert threshold |

#### Step 6.5 — Test streaming compatibility with 9Router

| Field | Value |
|---|---|
| **Risk ID** | R-P6-05-001 |
| **Description** | 9Router buffers streaming responses — Hermes expects SSE streaming but 9Router may buffer entire response before forwarding. The "~1.2s progressive edits" benefit is eliminated. |
| **Probability** | MEDIUM (3) |
| **Impact** | LOW (2) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | C-004: Test time-to-first-token through 9Router→Hermes→Discord pipeline; if 9Router buffers: document degradation, adjust expectations, consider direct-to-OpenAI for streaming |
| **Trigger Criteria** | Time-to-first-token equals full response time (no streaming) |
| **Recovery Time** | N/A (streaming is a nice-to-have, not safety-critical) |
| **Detection Method** | Time-to-first-token measurement; progressive edit timing |

---

## 10. Phase 7: Hardening + Cutover (2-3 days, 7 steps)

### Phase 7 Overview Risks

| Risk ID | Description | Prob | Impact | Score |
|---|---|---|---|---|
| **R-P7-OVER-01** | **Performance regression** (R-009) — hook subprocess startup adds 200-500ms per hook. 5+ hooks = 1-2.5s added latency. Total may exceed +10% threshold | MEDIUM (3) | MEDIUM (3) | **9 MEDIUM** |
| **R-P7-OVER-02** | ADR-029 compliance gap — Hermes-based system must still satisfy automated testing requirements for self-modifying code (hooks, plugins, config). Migration rollback is distinct from ongoing ADR-029 gates. | LOW (2) | MEDIUM (3) | **6 MEDIUM** |

### Per-Step Risks

#### Step 7.1 — Configure hermes cron for automated maintenance

| Field | Value |
|---|---|
| **Risk ID** | R-P7-01-001 |
| **Description** | Cron configuration errors — tasks fire at wrong intervals, overlap with other maintenance, or fail silently. Daily backup cron failure goes unnoticed until backup is needed. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Test each cron task individually; configure failure alerts (Gotify); run `hermes cron --dry-run` to verify schedule; monitor cron execution log for 48hr |
| **Trigger Criteria** | Cron task fails to execute for 2+ consecutive intervals |
| **Recovery Time** | < 30 min (fix cron config, restart cron) |
| **Detection Method** | Cron execution log; Gotify alert on failure |

#### Step 7.2 — Configure hermes logs integration with Loki

| Field | Value |
|---|---|
| **Risk ID** | R-P7-02-001 |
| **Description** | Log format incompatibility — Hermes log format differs from current Guinevere log format. Loki queries break. Existing Grafana dashboards show gaps. |
| **Probability** | LOW (2) |
| **Impact** | LOW (2) |
| **Risk Score** | **4 LOW** |
| **Mitigation** | Test log ingestion into Loki; verify dashboards render Hermes logs; add Hermes log labels matching current schema; keep Guinevere log format for existing services |
| **Trigger Criteria** | Loki shows 0 Hermes log entries; Grafana dashboard shows gaps |
| **Recovery Time** | < 1 hr (adjust log format or Loki parsing) |
| **Detection Method** | Loki log stream test; Grafana dashboard health check |

#### Step 7.3 — Configure hermes backup automated pipeline

| Field | Value |
|---|---|
| **Risk ID** | R-P7-03-001 |
| **Description** | Backup pipeline failure: idcloudhost S3 or Cloudflare R2 unreachable (network, auth expiry, quota). Backups silently fail — discovered only during DR scenario. |
| **Probability** | LOW (2) |
| **Impact** | HIGH (4) |
| **Risk Score** | **8 MEDIUM** |
| **Mitigation** | Backup success/failure alert to Discord; test restore from both destinations; verify RPO meets ADR-025 (daily); dual-destination (idcloudhost + R2) provides redundancy |
| **Trigger Criteria** | Backup upload fails to both destinations |
| **Recovery Time** | < 1 hr (fix auth/network; if persistent, rotate destination) |
| **Detection Method** | Backup completion alert; upload size verification |

#### Step 7.4 — Configure hermes checkpoints automated snapshots

| Field | Value |
|---|---|
| **Risk ID** | R-P7-04-001 |
| **Description** | Checkpoint corruption — automated checkpoint created with corrupted state (disk full, mid-operation snapshot). Restore from corrupted checkpoint fails. |
| **Probability** | VERY LOW (1) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **3 LOW** |
| **Mitigation** | Verify checkpoint integrity after creation; keep 3 most recent checkpoints (rotate); test restore from oldest checkpoint weekly |
| **Trigger Criteria** | `hermes checkpoints --list` shows zero-size or corrupted entry |
| **Recovery Time** | < 5 min (restore from previous checkpoint) |
| **Detection Method** | Checkpoint integrity verification; weekly restore test |

#### Step 7.5 — Run full hermes security audit

| Field | Value |
|---|---|
| **Risk ID** | R-P7-05-001 |
| **Description** | Security audit finds NEW HIGH/CRITICAL vulnerability in post-migration stack. Must be fixed before Phase 7 gate passes. Could delay completion by 1-3 days. |
| **Probability** | LOW (2) |
| **Impact** | MEDIUM (3) |
| **Risk Score** | **6 MEDIUM** |
| **Mitigation** | Run security scan at end of each phase (not just Phase 7) to catch issues incrementally; Phase 7 scan should find zero new issues — all should have been caught earlier |
| **Trigger Criteria** | `hermes security` returns HIGH or MODERATE finding |
| **Recovery Time** | 1-3 days (investigate and fix) |
| **Detection Method** | Phase 7 `hermes security` output; per-phase incremental scans |

#### Step 7.6 — Performance benchmark (baseline vs post-migration)

| Field | Value |
|---|---|
| **Risk ID** | R-P7-06-001 |
| **Description** | Performance benchmark shows latency > +10% of baseline. Hook subprocess overhead is the primary suspect. Must optimize or accept regression. If optimization fails, rollback to bot.py. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Pre-migration baseline measurement (p50, p95, p99); hook batching → plugin method calls; persistent plugin process (not per-message subprocess); async non-blocking hooks; if still >10%: accept or add Phase 7.8 optimization sprint |
| **Trigger Criteria** | p95 latency > 1.1× baseline |
| **Recovery Time** | 1-3 days (optimize hook architecture); or accept regression with Faiz approval |
| **Detection Method** | Comparison benchmark; per-hook latency instrumentation |

#### Step 7.7 — Write comprehensive runbook

| Field | Value |
|---|---|
| **Risk ID** | R-P7-07-001 |
| **Description** | Runbook is complete on paper but Faiz hasn't practiced procedures. At 3 AM incident, cognitive load prevents effective execution. Runbook quality ≠ operator readiness. |
| **Probability** | MEDIUM (3) |
| **Impact** | HIGH (4) |
| **Risk Score** | **12 HIGH** |
| **Mitigation** | Rollback dry-run practiced (C-2/C-013); runbook has flowcharts AND copy-paste commands; pre-written executable scripts on VPS (`~/scripts/rollback/`); universal kill-switch memorized |
| **Trigger Criteria** | Incident occurs → Faiz unable to resolve within 5 min |
| **Recovery Time** | Depends on runbook quality and Faiz familiarity |
| **Detection Method** | Rollback dry-run timing; incident response time measurement |

---

## 11. Risk Summary by Phase

| Phase | Steps | Per-Step Risks | Overview Risks | HIGH (12-15) | CRITICAL (16+) |
|---|---|---|---|---|---|
| Phase 0 | 7 | 7 | 2 | 1 (aiohttp breakage) | 0 |
| Phase 1 | 10 | 20 | 4 | 10 (HARD STOP, Y6, distress, consent, secret scanner, forbidden patterns) | 0 (but R-001/R-013 upgraded by reviewer) |
| Phase 2 | 8 | 13 | 4 | 5 (shadow write mutex, resource contention, safety injection, parity comparison, memory write) | 1 (shadow doesn't validate safety — mitigated by active injection) |
| Phase 3 | 6 | 7 | 2 | 4 (embedding API, compression, bridge bug, A/B test validity) | 1 (embedding API unfixed at start) |
| Phase 4 | 6 | 8 | 2 | 2 (tools enabled without auth; auth plugin complexity) | 0 (but R-004 is 15 HIGH) |
| Phase 5 | 5 | 7 | 2 | 1 (SOUL.md misconfiguration) | 0 |
| Phase 6 | 5 | 6 | 1 | 0 | 0 |
| Phase 7 | 7 | 8 | 2 | 2 (performance regression; runbook untested) | 0 |
| **TOTAL** | **54** | **76** | **19** | **25** | **2** |

Plus 12 cross-cutting risks (CC-01 through CC-12), including:
- **2 CRITICAL**: Solo-developer SPOF (CC-01, 16), Embedding API failure (CC-11, 16)
- **4 HIGH**: Timeline overrun (CC-02, 12), Hook contract mismatch (CC-05, 12), Plugin instance model (CC-06, 15), Shadow doesn't validate safety (CC-12, 16)

### Top 10 Risks (All Sources)

| Rank | Risk ID | Description | Score | Source |
|---|---|---|---|---|
| 1 | CC-01 | Solo-developer SPOF | **16 CRITICAL** | Reviewer 3 MR-01 |
| 2 | CC-11 | Embedding API failure (G-B1) — CURRENT ISSUE | **16 CRITICAL** | Risk deep-dive R-003 prerequisite |
| 3 | R-P2-OVER-03 | Shadow mode doesn't validate safety | **16 CRITICAL** | Reviewer 3 C-3 |
| 4 | R-P1-OVER-01 | HARD STOP fails silently (R-001) | **15 HIGH** | Risk deep-dive + Reviewer 3 upgrade |
| 5 | R-P1-05-001 | Y6 enum constructability (B-001) | **15 HIGH** | Reviewer 2 B-001 |
| 6 | R-P1-10-004 | Forbidden pattern regression 15→5 (B-003) | **15 HIGH** | Reviewer 2 B-003 |
| 7 | R-P1-04-001 | Distress pattern regression 14→6 (B-002) | **15 HIGH** | Reviewer 2 B-002 |
| 8 | R-P4-OVER-01 | Auth matrix bypass (R-004) | **15 HIGH** | Risk deep-dive R-004 |
| 9 | R-P1-05-003 | Plugin instance model unverified (B-004) | **15 HIGH** | Reviewer 3 C-6 |
| 10 | CC-06 | Plugin instance model unknown | **15 HIGH** | Chief reviewer B-004 |

---

## 12. Key Findings

### Show-Stoppers (4)

These risks MUST be demonstrably reduced to MEDIUM (≤10) before their respective migration phases:

1. **HARD STOP silent failure (R-P1-02-001, R-P1-02-003)** — Non-negotiable. ALL 9 acceptance criteria from deep-dive §R-001 must pass. Heartbeat watchdog must run for 24hr without false positives. Dual-layer must be verified.

2. **Plugin instance model unknown (CC-06, R-P1-05-003)** — Must be resolved on VPS BEFORE any Phase 1 plugin code is written. If global: architecture is correct (session_id-keyed dicts). If per-session: simplify.

3. **Shadow mode safety validation (R-P2-OVER-03)** — Active safety injection tests MUST supplement passive parity comparison. C-011/C-3: 3× HARD STOP, 3× Y6, 1× consent, 1× distress, 1× hook failure.

4. **Embedding API failure (CC-11, R-P3-OVER-01)** — Current production issue. Must be fixed BEFORE Phase 3 (memory compression, A/B testing, vector search). If unfixable, Phase 3 is compromised.

### Systematic Underestimations (from Reviewer 3)

1. **Solo-developer constraint** — Every timeline assumes 3-4 hr/day but doesn't account for fatigue, context switching, or zero-reviewer error rate
2. **VPS resource contention** — "No additional processes" claim contradicted by 5-7 hook subprocesses per message
3. **Timeline optimism** — 35-50 days realistic (not 23-35); Phase 1 iteration adds 3-5 days per cycle

### Reviewer-Upgraded Risks (ADR self-scored vs Reviewer)

| Risk | ADR Score | Reviewer Score | Delta |
|---|---|---|---|
| R-001 HARD STOP | 15 HIGH | 20 CRITICAL | +1 level |
| R-013 Yandere FSM | 15 HIGH | 20 CRITICAL | +1 level |
| R-015 Shadow complexity | 12 HIGH | 16 CRITICAL | +1 level |
| MR-01 Solo-dev SPOF | Not assessed | 16 CRITICAL | New |
| MR-02 VPS contention | Not assessed | 9 MEDIUM | New |
| MR-05 Timeline overrun | Not assessed | 12 HIGH | New |

---

## 13. Footer

| Field | Value |
|---|---|
| Report ID | RR-MIGRATION-02 |
| Title | Risk Inventory Per Phase Step — Hermes Migration |
| Generated | 2026-06-04 |
| Author | Guinevere (Sisyphus-Junior) — Agent 2 of 10 parallel research agents |
| Risk Count | 68 per-step + 12 cross-cutting = 80 total |
| Source Documents | ADR-035 v1.2 (2,325 lines), 05-risk-deep-dive.md (506 lines), 03-risk-assessment.md (422 lines), 00-CHIEF-REVIEWER-SYNTHESIS.md (291 lines), MASTER-RESTRUCTURE-PLAN.md (667 lines) |
| Status | Complete |

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Risk inventory for Hermes migration planning. For Faiz's eyes only.