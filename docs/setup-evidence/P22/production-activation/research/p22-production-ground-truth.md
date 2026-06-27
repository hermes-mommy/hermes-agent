# P22 Life Integration Hub — Production Ground Truth

**Date:** 2026-06-27
**Phase:** P22 Life Integration Hub — Production Activation Assessment
**Author:** P22 Production Ground Truth Synthesizer (independent read-only sub-agent)
**Scope:** Honest current state, gap to production active, per-adapter activation feasibility.

---

## Executive Summary (Honest Status)

**P22 verdict: PASS WITH CONFIG_MISSING ADAPTERS — core runtime ACTIVE, production activation DEFERRED on operator-gated items.**

The P22 core runtime package is **code-complete, tested, audited, and locally verified.** It is **not** docs-only, **not** fake-pass, and **not** a sealed system. Specifically:

| Dimension | State | Evidence |
|---|---|---|
| Core runtime code | **Complete** (28 .py files, ~1,800 lines) | `src/life_integrations/` |
| Adapters | **Complete** (13 adapters + 1 __init__, ~1,100 lines) | `src/life_integrations/adapters/` |
| Tests | **76 passed / 0 failed** (7 files) | `tests/p22/` |
| Runtime smoke | **12/12 PASS** (exit 0) | `scripts/p22_smoke_test.py` |
| Audit round 1 | **PASS** (8 auditors, all findings fixed) | `audits/round-1/*` |
| Audit round 2 | **PASS** (4 auditors, all 8 R1 findings re-verified, no regressions) | `audits/round-2/*` |
| Hard rejection criteria | **All 11 PASS** | `p22-final-implementation-report.md` §12 |
| DB migration | **Created**, **NOT applied** to production DB | `alembic/versions/p22_001_integration_schema.py` |
| Adapters currently ACTIVE (real client wired + creds present) | **0/13** | All 13 built with `client=None` |
| Adapters with credentials provisioned | **0/13** | No external creds in SOPS |
| Adapters that structurally CAN run with no creds | **3/13** | VPS, Browser, Filesystem (local-OK) |
| Adapters needing operator-provisioned creds | **10/13** | All OAuth/token-gated |
| VPS deployment | **DEFERRED** (library code, no service restart) | P22 plan §13 |
| P20 closed files modified | **0** (additive only) | `audits/round-2/audit-p19-p20-regression.md` |
| P19 registry consumed | **read-only** via protocol | `audits/round-2/audit-p19-p20-regression.md` §2 |
| V-002 (sensors-not-triggers) | **Preserved** | `audits/round-2/audit-p19-p20-regression.md` §3 |

**The honest state:** the *code* is production-ready, but P22 is *not yet* a live runtime integration layer on the VPS. The 10 CONFIG_MISSING adapters would raise `ConfigurationMissingError` if any agent attempted to call them today. This is **by design** — the package was built to fail honestly rather than fake success.

---

## Phase Definition (P22 Production Activation)

**P22 Production Activation** is the *deployment and wiring* phase that takes P22 from "code-complete and locally verified" to "all 13 adapters live on the VPS, real clients wired, migration applied, smoke test green on the production DB." It is **not** a rewrite of the core package; that work is closed.

The activation phase has 4 sub-gates, none of which have been crossed yet:

1. **Migration applied** to production PostgreSQL (`alembic upgrade head`).
2. **Real clients wired** into `build_default_registry()` at P20 startup time (`wiring.py`).
3. **External credentials provisioned** in SOPS for the 10 currently-CONFIG_MISSING adapters.
4. **VPS code in sync** with local working tree (no drift between 28 untracked files locally and the deployed package).

The orchestrator plan (`p22-life-integration-implementation-plan.md` §13) explicitly states: *"VPS: DEFERRED to operator (P22 is development work, not P20 autonomy exception)."*

---

## Core Implementation State

### 3.1 Test Suite

| File | Tests | Coverage |
|---|---|---|
| `test_registry.py` | 6 | register/get/unregister/list_by_capability/health_check_all |
| `test_permissions.py` | 13 | semantic classification (L1-L4), AuthLevel-not-gate, hard_stop blocks |
| `test_consent_hardstop.py` | 8 | L1 no consent, L2 requires consent, HARD STOP absolute, L4 forbidden, revocation |
| `test_audit.py` | 10 | hash, chain, tamper, redaction, project_id |
| `test_project_isolation.py` | 11 | context resolution, resource_id format, vault isolation, redaction |
| `test_adapters.py` | 12 | CONFIG_MISSING honesty, L3 delete, L4 forbidden, workspace boundary |
| `test_fixes_r1.py` | 16 | round-1 regression suite (finance word-boundary, VPS allowlist, tombstone hashes, audit value-pattern redaction) |
| **Total** | **76 pass / 0 fail** | — |

Source: `docs/setup-evidence/P22/implementation/final/p22-final-implementation-report.md` §5; `docs/setup-evidence/P22/implementation/audits/round-2/audit-adapters-regression.md` (25 of 25 in test_adapters+test_fixes_r1, plus the rest of the suite brings total to 76).

### 3.2 Runtime Smoke

`scripts/p22_smoke_test.py` runs 12 checks, exits 0:

1. Registry loads all 13 adapters ✓
2. CONFIG_MISSING adapters report honestly (≥7 UNKNOWN) ✓
3. Filesystem adapter healthy ✓
4. HARD STOP blocks L2+ write ✓
5. Consent revocation blocks L2 ✓
6. L1 read passes without consent ✓
7. L4 always forbidden ✓
8. Write action blocked by gate ✓
9. project_id in audit event ✓
10. Audit chain integrity ✓
11. Resource ID namespace format ✓
12. Permissions matrix all 4 tiers ✓

### 3.3 Audit Round 2 (4 auditors, post-fix)

| Audit | Verdict | Notable finding |
|---|---|---|
| runtime-security | **PASS** | All 8 R1 findings verified-fixed; 0 new findings at FAIL severity. 3 minor cosmetic observations (M1 audit truncation, M2 VPS allowlist no length cap, M3 wiring asyncio import site). |
| adapters-regression | **PASS** | All CONFIG_MISSING honesty, finance word-boundary, VPS shell-injection, tombstone content_hash, filesystem workspace boundary, bare-except sweep, L4 rejection: VERIFIED FIXED. 25/25 R1 regression tests pass. |
| p19-p20-regression | **PASS** | 0 `from src.life_kernel` imports; 0 restricted-path imports; 0 `from src.projects` imports; ActionRouter 5-stage gate pipeline intact; wiring.py fully async; no circular imports; 28 .py files all untracked/additive. |
| consent-project | **PASS** | Consent/HARD STOP absolute, project_id propagated, revocation blocks L2 absolutely. |

**Aggregate Round 2 verdict: PASS — 4/4. No regressions from Round 1.**

### 3.4 Type/Code Quality Scans

- Forbidden patterns (`# type: ignore`, `except Exception:`, `except:`, `as any`, `@ts-ignore`): **0 matches** in `src/life_integrations/`.
- Plaintext secrets (`ghp_`, `sk-`, `ya29.`, `xox`, `AIza`, `BEGIN PRIVATE KEY`): **0 matches** outside the audit.py redactor regex (which is the *detector*, not a real secret).

---

## Integration Roster (13 Adapters)

| # | integration_id | Name | Provider | Capabilities | Default Tier | Risk | Current config_status | Secret refs |
|---|---|---|---|---|---|---|---|---|
| 1 | `discord` | Discord | Discord | read/write/delete/execute | L1 | medium | **CONFIG_MISSING** | `sec-discord-bot` |
| 2 | `gmail` | Gmail | Google | read/write/delete/sync | L1 | medium | **CONFIG_MISSING** | `sec-gmail-oauth` |
| 3 | `github` | GitHub | GitHub | read/write/delete/execute/sync | L1 | high | **CONFIG_MISSING** | `sec-github-pat` |
| 4 | `calendar` | Google Calendar | Google | read/write/delete/sync | L1 | medium | **CONFIG_MISSING** | `sec-google-calendar-oauth` |
| 5 | `drive` | Google Drive | Google | read/write/delete | L1 | high | **CONFIG_MISSING** | `sec-google-drive-oauth` |
| 6 | `notion` | Notion | Notion | read/write/delete/search | L1 | medium | **CONFIG_MISSING** | `sec-notion-integration-token` |
| 7 | `telegram` | Telegram | Telegram | read/write/delete/execute | L1 | medium | **CONFIG_MISSING** | `sec-telegram-bot-token` |
| 8 | `whatsapp` | WhatsApp | Neonize/Baileys | read/write/delete | L1 | medium | **CONFIG_MISSING** | `sec-baileys-session` |
| 9 | `vps` | VPS System Health | Docker/Systemd | read/write/delete/execute | L1 | high | **OK (local)** — needs no creds, needs `docker_client` and `shell_client` wired | `sec-postgres-core`, `sec-redis-auth` (for downstream, not VPS health itself) |
| 10 | `finance` | Finance Tracker | Polars/PG | read/write/delete | L1 | high | **CONFIG_MISSING** — needs `finance_mind` (the `FinanceMind` domain mind instance); structurally the wrapper is ready, but no mind is instantiated with creds at startup | `sec-postgres-core` (downstream) |
| 11 | `browser` | Browser/Research | Brave/Exa/Obscura | read/write/search | L1 | low | **OK (local)** — `search/fetch/browser` clients already exist in `src/mcp/tools/`; only needs wiring in `build_default_registry()` | `sec-brave-api`, `sec-exa-api` |
| 12 | `memory` | Memory/KG | PostgreSQL/pgvector | read/write/delete/search | L1 | critical | **CONFIG_MISSING** — needs write/read pipelines + kg engine injected (they exist in `src/memory/` and `src/knowledge_graph/`, but no current hookup) | `sec-postgres-core` (downstream) |
| 13 | `filesystem` | Filesystem/Repo | Local | read/write/delete | L1 | medium | **OK (local)** — workspace-rooted (defaults to `os.getcwd()`); zero external creds | none |

**Per-adapter CONFIG_MISSING honesty mechanism** (all 13 verified by `audit-adapters-regression.md`):
- `health_check()`: if injected client is `None` → returns `IntegrationHealth.UNKNOWN` (with optional structlog `*.config_missing` event).
- `execute_action()`: if injected client is `None` → raises `ConfigurationMissingError` (or per-action if multi-client like Browser/Memory).

---

## The Production Gap (4 Items)

The distance between **"core implementation done"** and **"production active on VPS"** is exactly four items:

### Gap 1 — Migration unapplied

`alembic/versions/p22_001_integration_schema.py` exists and chains from `p19_003_audit_chain_version`. It creates:
- `audit.integration_api_log` (WORM, hash-chained)
- `p22.integration_registry` (per-integration enabled flag + status)
- `p22.secret_ref_metadata` (secret reference registry)

It backfills 12 integrations (all `disabled=true`, `config_missing`).

**Status:** file on disk, not executed on production DB. Per AGENTS.md, this is **operator-gated** and cannot be applied autonomously by an agent.

### Gap 2 — `build_default_registry()` not called with real clients at startup

`wiring.py` exposes 18 keyword arguments to `build_default_registry()` — all default to `None`. In the current state, the call site that would supply these (P20 startup) is **not yet wired**. Specifically:
- `discord_rest_client` → needs the existing `src/life_kernel/discord_rest_client.py` instance
- `gmail_service` → needs the existing `src/gmail/` service
- `github_client` → needs the existing `src/mcp/tools/github.py` tool
- `vps_docker_client`, `vps_shell_client` → need docker_tool.py and shell_tool.py instances
- `memory_*_pipeline`, `kg_engine` → need existing `src/memory/` and `src/knowledge_graph/` instances
- `finance_mind` → needs the existing `src/life_kernel/domain_minds/finance_mind.py` instance
- `browser_*` → need existing `src/mcp/tools/brave_search.py`, `fetch.py`, `obscura_cdp.py`
- `whatsapp_adapter` → needs `src/channels/whatsapp/` ingress/egress
- `calendar_client`, `drive_client` → NEW clients, not yet built (would wrap Google API clients with OAuth)
- `notion_client`, `telegram_client` → NEW clients, not yet built

Until those args are populated at P20 startup, every adapter starts in `client=None` mode.

### Gap 3 — VPS code may be behind local

`src/life_integrations/` is **fully untracked in git** (round-2 audit: `git log --oneline -- src/life_integrations/` returns zero commits). The directory exists only in the local working tree. The VPS has not received these 28 new files.

**Implication:** Even if all 18 client args were wired locally, the deployed VPS runtime would not have the package until `git add` + commit + push + VPS pull + service restart. Per AGENTS.md §0.1, P22 is development work and does not trigger a P20-style autonomy exception; the VPS deploy is operator-gated.

### Gap 4 — 10 adapters lack external credentials

The CONFIG_MISSING adapters need secrets in SOPS before they can be considered ACTIVE (vs. structurally ready). See §CONFIG_MISSING Criteria and §Activation Feasibility below.

---

## CONFIG_MISSING / CONFIG_INVALID / CLIENT_MISSING Criteria

P22 distinguishes four honest states for an adapter's runtime status. **Faking PASS is a HARD REJECTION** — no adapter may report `OK` when a credential, client, or capability is missing.

| State | When honest | Example |
|---|---|---|
| `CONFIG_MISSING` | Credential genuinely absent from SOPS; adapter is structurally ready but has no client injected. Adapter reports `IntegrationHealth.UNKNOWN` from `health_check()` and raises `ConfigurationMissingError` from `execute_action()`. | `discord_adapter._rest_client is None` |
| `CONFIG_INVALID` | Credential present in SOPS but fails validation (revoked token, expired OAuth refresh, wrong scope). Adapter should report `IntegrationHealth.ERROR` and a typed error. (P22 does not yet auto-detect this; relies on underlying client to raise — known minor gap.) | Not currently exercised; smoke only tests CONFIG_MISSING. |
| `CLIENT_MISSING` | Client library not installed in the Python environment (e.g., `google-api-python-client` not present for Drive). Differs from CONFIG_MISSING in that the *code* cannot even attempt to construct the client. Currently implicit — surfaces as `ImportError` at adapter construction. | If `src/mcp/tools/github.py` were not importable. |
| `ACTIVE` | All three present: (a) credential in SOPS, (b) client constructed and injected via `build_default_registry()` kwargs, (c) `health_check()` returns `OK`. Adapter routes traffic. | `filesystem` adapter, with no creds, defaults to OK because its "client" is `os.getcwd()` and the workspace is local. |

**The hard rule:** an adapter must never report `OK` in any of the first three states. P22's verification chain (smoke + audit R2 adapters-regression) confirms this is enforced for all 13 adapters.

**Honest CONFIG_MISSING vs. fake PASS** — what to watch for in operator review:
- A truly CONFIG_MISSING adapter's `health_check()` returns `UNKNOWN`, and the `health_check_all()` call from the registry lists it as `UNKNOWN`.
- A fake PASS would have `health_check()` return `OK` when the client is `None`. The 8 R1+R2 audit findings (and the `audit-adapters-regression.md` per-adapter table) were structured precisely to detect this.

---

## Activation Feasibility per Adapter

### 5.1 Zero-cred-activatable (local-OK)

These three adapters need **no new external credentials** to go ACTIVE. The blockers are mechanical (wiring) rather than provisioning.

| Adapter | What's needed to go ACTIVE | Local vs. VPS effort |
|---|---|---|
| **vps** | Inject `docker_tool` and `shell_tool` instances from `src/life_kernel/` into `build_default_registry(vps_docker_client=..., vps_shell_client=...)`. Existing infrastructure; no OAuth. | Small wiring change in P20 startup. |
| **browser** | Inject the three existing MCP search/fetch/CDP clients from `src/mcp/tools/brave_search.py`, `fetch.py`, `obscura_cdp.py`. | Small wiring change; clients already exist. |
| **filesystem** | Default workspace root is `os.getcwd()`. No wiring strictly required, but should pass `workspace_root` explicitly to keep P22 audit logs accurate. | Trivial. |

**Note:** "no new external creds" means *no OAuth/token*. Browser does reference `sec-brave-api` and `sec-exa-api` — these are existing API keys (already in SOPS) that the upstream MCP tools already require. So even browser is "no new creds" relative to current state.

### 5.2 Operator-gated (need creds)

These ten adapters require the operator (Faiz) to provision external credentials before they can be wired ACTIVE.

| Adapter | What operator must do | What wiring does after creds exist |
|---|---|---|
| **discord** | Provision `sec-discord-bot` in SOPS (bot token). | Construct the existing `DiscordRestClient` from `src/life_kernel/discord_rest_client.py`; inject. |
| **gmail** | Provision `sec-gmail-oauth` (OAuth2 refresh + access). | Construct the existing Gmail service from `src/gmail/`; inject. |
| **github** | Provision `sec-github-pat` (fine-grained PAT). | Construct existing GitHub MCP tool from `src/mcp/tools/github.py`; inject. |
| **calendar** | Provision `sec-google-calendar-oauth`; build a new `GoogleCalendarClient` (does not exist yet). | Build client (new code), inject. |
| **drive** | Provision `sec-google-drive-oauth`; build a new `GoogleDriveClient` (does not exist yet). | Build client (new code), inject. |
| **notion** | Provision `sec-notion-integration-token`; build a new `NotionClient` (does not exist yet). | Build client (new code), inject. |
| **telegram** | Provision `sec-telegram-bot-token`; build a new `TelegramClient` (does not exist yet). | Build client (new code), inject. |
| **whatsapp** | Link `sec-baileys-session` (existing Neonize session); pass existing `WhatsAppIngressEgressAdapter` from `src/channels/whatsapp/`. | Inject existing adapter. |
| **finance** | Existing `FinanceMind` (`src/life_kernel/domain_minds/finance_mind.py`) needs DB connection string from `sec-postgres-core`. | Inject existing FinanceMind instance. |
| **memory** | `MemoryIntegrationAdapter` needs the existing `src/memory/` write/read pipelines and `src/knowledge_graph/` engine. Postgres is already in SOPS. | Inject existing pipeline instances. |

**Subcategories within operator-gated:**
- *Wraps existing code* (5): discord, gmail, github, whatsapp, finance, memory — adapters exist; clients exist; only injection is needed.
- *New client required* (4): calendar, drive, notion, telegram — the adapter is ready but a new client wrapper is needed.
- All 10 are blocked on **operator action** (OAuth dance requires Faiz's browser, not automatable).

---

## P19 / P20 / P23 / P24 Dependencies

### 6.1 P19 dependency (read-only consumer)

P22 consumes the P19 `ProjectRegistry` via a `ProjectRegistryProtocol` declared in `src/life_integrations/project_context.py`:
- `async get(project_id) -> Any`
- `async resolve(slug) -> Any`
- `async list_active() -> list[Any]`

These are the only 3 methods. The mutation methods on the real P19 `ProjectRegistry` (`create`, `update`, `archive`, `delete`, `list_all`, `get_by_slug`) are **not** called from P22 — verified by grep in `audit-p19-p20-regression.md` §2.4.

`DEFAULT_PROJECT_ID = 00000000-0000-0000-0000-000000000001` (P19 canonical).

Resource ID format: `p22:<domain>:<provider>:<resource-id>`, propagated through audit events.

### 6.2 P20 dependency (additive, no closed-file modifications)

P22 registers itself via `SensorRegistry.register()` (existing P20 API), which is additive. The round-2 regression audit confirms:
- 0 `from src.life_kernel` imports in `src/life_integrations/`
- 0 imports of restricted modules (heartbeat, graph, hermes_brain, cognition, sensors, state.models)
- 0 modifications to any of the 12 P20 closed files
- V-002 preserved: `ActionRouter` is the gate pipeline; `router.py:177-182` invokes `adapter.execute_action` AFTER all 5 prior gate stages pass; `act_node` is never reached from P22

**P20 status:** CLOSED 2026-06-25 with operator waiver (per memory `p20-closed-accepted-risk.md`). P22 must not reopen P20. Wiring is additive only; the `wiring.py` module is a new file that P20 may optionally `import` at startup.

### 6.3 P23 forward contract (consumer)

P23 (Embodied Operations, defined 2026-06-25) consumes P22 adapters as **ExternalExecutor targets**. Specifically:
- P23-014: action layer consumes `IntegrationRegistry` from P22 to resolve which adapter to dispatch a user-requested side effect to.
- P23 SemanticActionClassifier (when it lands) will **replace** the P22-local scaffold classifier in `permissions.py`. P22 implements a local scaffold as a documented bridge; P23-014 is unblocked by P22's pass.
- P23B is currently BLOCKED on (a) P19 runtime registry — DONE, (b) P21 impl, (c) P23-014 — P22 closure unblocks (c).

### 6.4 P24 forward contract (fork migration)

P24 (Hermes fork convergence, 2026-06-25 verdict: full owned fork preferred) migrates P22 adapters to fork-internal modules. Specifically:
- P22 adapter file `src/life_integrations/adapters/<name>_adapter.py` → `src/hermes_plugins/commands_<name>/` (fork-internal)
- P22's `SecretProvider` interface is already shaped to allow backend swap (currently `EnvSecretProvider`; Hermes fork will swap to its own vault).
- P24 is gated by mama's next audit; implementation is on hold until then. P22 does not block P24, but P24 is the long-term home for the adapter code.

---

## Hard Rejection Criteria Recap

From `p22-final-implementation-report.md` §12 and `p22-local-verification.md` §3 — the 11 hard rejection criteria for P22. All **PASS** in current state:

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | P22 is docs-only | ✗ PASS (not docs-only) | 28 .py files of runtime code |
| 2 | Adapters fake success | ✗ PASS (not fake) | `ConfigurationMissingError` raised by 10/13 when called |
| 3 | Secrets printed/committed | ✗ PASS (none) | 0 plaintext secrets in repo |
| 4 | project_id not propagated | ✗ PASS (propagated) | Every ActionRouter call carries it; audit logs it |
| 5 | HARD STOP doesn't block L2+ | ✗ PASS (blocks) | `ConsentGate` absolute |
| 6 | Consent revoke doesn't block | ✗ PASS (blocks) | Revocation absolute, tested |
| 7 | Delete/write missing | ✗ PASS (declared) | All adapters declare DELETE/WRITE |
| 8 | Delete/write bypass gates | ✗ PASS (gated) | `ActionRouter` 5-stage pipeline |
| 9 | P20/P19 regressions unchecked | ✗ PASS (checked) | Round-2 audit, 0 closed files modified |
| 10 | AuthLevel-only gating for L2+ | ✗ PASS (semantic) | `SemanticActionClassifier` |
| 11 | Inline-only sub-agent output | ✗ PASS (file-based) | All evidence file-based |

**No criterion is currently violated.** A future regression that flips any of these would invalidate the PASS verdict.

---

## Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Operator provisions 10 OAuth flows sequentially; process is slow and may fail midway. | medium | P22 is structured to accept *partial* provisioning: each adapter's status is independent. Failures don't block others. |
| R2 | The 4 NEW client wrappers (calendar, drive, notion, telegram) need to be written. This is fresh code, not a wiring change. | medium | P22 plan noted these as "wrap existing X" but the underlying wrappers don't exist in the repo. Must be built and audited before production. |
| R3 | `CONFIG_INVALID` state is not explicitly handled. If a provisioned token expires, the adapter will surface the underlying client error, not a clean P22 typed error. | low | Documented as a future round-3 candidate. Will need `health_check()` retry logic. |
| R4 | VPS drift: the 28 P22 files are untracked. If a different process (CI, P20 hot-fix) deploys to VPS before P22 is committed, the P22 package may not arrive. | low | P22 is closed on local; commit + push is a 1-step operator action. |
| R5 | P22 currently does not auto-detect when a previously-CONFIG_MISSING adapter becomes ACTIVE (no scheduler reconnect on secret change). | low | `IntegrationScheduler` is built but not started in production. Restart of P20 picks up new creds. |
| R6 | Round-2 noted 3 cosmetic observations (M1 audit truncation, M2 VPS allowlist no length cap, M3 wiring asyncio import site) — not blockers but indicative of small surface to harden later. | cosmetic | Recorded in `audit-runtime-security.md` Minor Observations. |
| R7 | `__import__('datetime')` used in discord/whatsapp instead of top-level import — code-quality nit, not a bug. | cosmetic | Trivial cleanup PR. |
| R8 | `dispatcher.py` was the round-1 audit's expected filename; P22 uses `router.py` instead. No correctness impact. | cosmetic | Informational. |

---

## Next Steps (Operator-Side)

**Ordered, in sequence of dependency:**

1. **Commit P22 to git** (unblock VPS deploy).
   - `git add src/life_integrations/ alembic/versions/p22_001_integration_schema.py tests/p22/ scripts/p22_smoke_test.py adr/ADR-053-p22-life-integration-hub.md docs/setup-evidence/P22/`
   - Commit with a P22 closure message.
   - Push to origin.

2. **Build the 4 missing client wrappers** (calendar, drive, notion, telegram) and audit them.
   - These do not exist yet; P22 plan referenced them as "wraps existing X" but the wrappers are not in repo.
   - Each gets the same audit treatment: CONFIG_MISSING honesty, value-pattern redaction, L4 rejection, tombstone for destructive ops.

3. **Wire the 13 existing clients into `build_default_registry()` at P20 startup**.
   - Add a P20 startup hook in P20-closed files? NO — that would reopen P20. Instead, add an additive file `src/life_integrations/startup_hook.py` that P20 may import.
   - Or: a separate P22-orchestrator process that builds the registry and exposes it via Redis.

4. **Apply the migration** (`alembic upgrade head`) to production DB. Operator-gated per AGENTS.md.

5. **Provision external credentials in SOPS** for the 10 OAuth/token-gated adapters. This is the longest step; expect ~1-2 days of OAuth flow per service.

6. **Restart P20** (or new P22-orchestrator) to pick up the registry with real clients. Verify smoke test on the VPS.

7. **Re-run audit round 3** after activation to verify the four gap items are closed and no new regressions.

8. **P23-014 unblocked** — P23 Embodied Operations can now consume P22 adapters as ExternalExecutor targets.

9. **P24 Wave 4** — eventually migrates `src/life_integrations/adapters/*` to `src/hermes_plugins/commands_*/` in the owned fork.

---

## Verdict

**P22 core: PASS WITH CONFIG_MISSING ADAPTERS — production-ready code, not yet production-active on VPS.**

The code is honest, audited, tested, and additively safe. Activation is a 4-item operator-gated sequence (migration, client wiring, creds, VPS sync), not a code rewrite. The hard rejection criteria are all met; no fake pass; no fake credentials.

**P22 is closed as a code phase. Activation is a separate, operator-driven phase.**
