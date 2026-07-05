# P22 Brutal Audit — Handoff Document

> Created: 2026-06-28 by Guinevere (previous session)
> Purpose: Handoff prompt for fresh opencode session to audit P22 Life Integration Hub

## What Happened

Faiz asked "apakah sudah full implementasi di phase 22 ini?" after P22.3 completion summary was shared. Guinevere answered: code complete, 897 tests pass, but 5 OAuth adapters need credentials + other blockers. Faiz then said "kamu audit brutal ya unlimited sub agent" — wanting a brutal audit of P22 implementation. Guinevere initially misread and fired 8 audit agents on P23/P24 plans (wrong target). Faiz corrected: "salah audit kamu, karusnya p22." All 7 wrong-target agents were cancelled. Faiz then asked for a handoff prompt for a fresh session.

## P22.3 Status (from Faiz's previous session paste)

- **897 tests pass, 12/12 runtime proof, 0 forbidden patterns, 0 secret leaks**
- 13 adapters with L1-L4 dispatch: browser, gmail, calendar, drive, notion, telegram, github, whatsapp, discord, finance, vps, memory, filesystem
  - **CORRECTION (2026-06-28 brutal audit F06):** an earlier version of this handoff listed "weather, search, obscura" as adapters — that was incorrect. `weather`/`search` are not implemented adapters (search is a browser-adapter *action*, not an adapter); `obscura` is a CDP *client shim* (`src/life_integrations/adapters/_clients/obscura_cdp_shim.py`), not an adapter. The actual 13 adapters are the real `.py` files under `src/life_integrations/adapters/` (excluding `onboarding_manifest.py`).
- 6 Discord slash commands + 6 FastAPI `/integrations` endpoints
- Waves: A (foundation fixes), B (user-facing control), C (13 adapter dispatch), D (fresh clients: Notion/Telegram/Calendar/Drive), E (tombstone/dry-run), G (operator onboarding tutorials)
- **Honest blockers**: 5 OAuth adapters need credentials (Gmail, Calendar, Drive, Notion, Telegram), GitHub test repo, WA_TEST_JID, Discord test channel, consent rows, Brave/Exa keys
- **Honest DEFERRED**: WhatsApp L3 (service-bus gap), Finance L2 (deferred-for-safety)
- L4 always `ActionNotSupportedError` (never autonomous)
- P20 soak CLEAN (NRestarts=0)
- P23-014 READY-WITH-LIMITATIONS (8 ACTIVE targets)
- Previous audits: 14 round-1 (8 PASS, 3 NEEDS_REVIEW), 6 round-2 (5 PASS, 1 NEEDS_REVIEW docs-only)

## Key File Locations

### Source Code
- `src/life_integrations/` — main package
  - `base.py` — BaseAdapter ABC
  - `registry.py` — adapter registry
  - `types.py` — type definitions
  - `scheduler.py` — scheduling logic
  - `errors.py` — error classes
  - `audit_db_writer.py` — audit trail writer
- `src/life_integrations/adapters/` — 13 adapter implementations:
  - `browser_adapter.py`, `gmail_adapter.py`, `calendar_adapter.py`, `drive_adapter.py`
  - `notion_adapter.py`, `telegram_adapter.py`, `github_adapter.py`, `whatsapp_adapter.py`
  - `discord_adapter.py`, `finance_adapter.py`, `filesystem_adapter.py`, `vps_adapter.py`
  - `memory_adapter.py`, `onboarding_manifest.py`
- `src/core/api/routes.py` — FastAPI endpoints (6 `/integrations` routes)
- Discord slash commands — likely in `src/channels/discord/` or `src/discord/`

### Tests
- `tests/p22/` — P22-specific tests:
  - `test_registry.py`, `test_integrations_endpoints.py`, `test_dry_run.py`
  - `test_capability_matrix.py`, `test_telegram_re.py`
- `scripts/p22_3_runtime_proof.py` — runtime proof script
- Other tests in `tests/life_kernel/`, `tests/channels/`, `tests/safety/` may be relevant

### Evidence & Documentation (100 files)
- `docs/setup-evidence/P22/README.md`
- `docs/setup-evidence/P22/plan/` — 2 plan files:
  - `p22-life-integration-hub-plan.md`
  - `p22-full-capability-raw-access-replan.md`
- `docs/setup-evidence/P22/research/` — research files including raw-full/ subdirectory
- `docs/setup-evidence/P22/implementation/` — plan, research, audits (round-1 + round-2), fixes, final report, verification, deploy
- `docs/setup-evidence/P22/production-activation/` — plan, research, audits (round-1 + round-2), fixes, runtime, deploy, final
- `docs/setup-evidence/P22/full-completion/verification/` — per-adapter dispatch verification (C1-C12, D1-D5, E1, F3, G1-G4)

### Other
- `PROGRESS.md` — still says P22="TBD" despite P22.3 being COMPLETE (needs update)
- `AGENTS.md` — operating contract, BLOCKING rules, safety mandates

## Key Concerns for Audit

### 1. Consent Gate Conflict (CRITICAL)
- P22 has L2+ consent-gated, L4 never autonomous
- P23 v2.0 (replanned): NO consent gate (execution-layer-only)
- P24 v2.0 (replanned): NO consent gate (ADR-062 exempt)
- When Hermes (P24, no consent) calls P23 executors, and P23 calls P22 adapters (which have consent gates), what happens?
- This conflict needs resolution or documented migration path

### 2. L1-L4 Risk Tier System
- P22 uses L1-L4 dispatch (L1=auto-read, L2=notify-write, L3=approval-destructive, L4=forbidden)
- P23 v2.0 REMOVED L1-L4 risk tiers (per Q-decisions)
- Is P22's L1-L4 system still valid? Or should it be stripped like P23?

### 3. Deferred Items
- WhatsApp L3 deferred (service-bus gap) — is this documented? Tracked?
- Finance L2 deferred (deferred-for-safety) — is this documented? Tracked?
- Are there other silent deferrals?

### 4. Credential Blockers
- 5 OAuth adapters need credentials — are the credential flows implemented (just missing keys) or is code missing?
- GitHub test repo, WA_TEST_JID, Discord test channel — are these test-environment issues or code gaps?
- Brave/Exa API keys — is the browser adapter's search action coded but keyless? (no separate "weather"/"search" adapter exists)

### 5. Test Coverage Quality
- 897 tests — but how many are unit vs integration vs e2e?
- Are all 13 adapters tested?
- Are L1-L4 dispatch paths tested?
- Are error paths tested? (OAuth failure, API timeout, rate limit)
- Are consent gate paths tested?

### 6. P20 Soak
- NRestarts=0 claimed — is this verifiable? Where's the soak evidence?
- Is the soak duration adequate? (how long was it?)

### 7. Audit Trail
- `audit_db_writer.py` — what's the schema? Is it UUID v7 + SHA256 like P23?
- Or is it a different format? Are they compatible?

### 8. Discord Slash Commands
- 6 commands — what are they? Are they tested?
- How do they interact with the L1-L4 dispatch?

### 9. FastAPI Endpoints
- 6 `/integrations` endpoints — what are they? Tested?
- Authentication/authorization on these endpoints?

### 10. PROGRESS.md Discrepancy
- PROGRESS.md still says P22="TBD" but P22.3 is COMPLETE with 897 tests
- This needs to be updated

## Suggested Audit Angles (Unlimited Sub-Agents)

1. **Adapter correctness audit** — each of 13 adapters: does the code match the dispatch verification? Are API calls real? Are error paths covered?
2. **L1-L4 dispatch system audit** — is the risk classification correct? Are L4 paths truly never-autonomous? Are L3 paths truly approval-gated?
3. **Consent gate audit** — is consent checked? Where? How? Is it bypassable?
4. **Test quality audit** — 897 tests: how many are meaningful? How many are stubs/mocks? Coverage gaps?
5. **Security/secrets audit** — are credentials stored safely? Any hardcoded secrets? OAuth flows correct?
6. **P20 regression audit** — does P22 break any P20 functionality? Soak evidence real?
7. **API/Discord endpoint audit** — are all endpoints tested? Auth correct? Rate limiting?
8. **Evidence/audit trail audit** — is audit_db_writer correct? Schema? Integrity?
9. **Previous auditor verification (meta-audit)** — were round-1/round-2 PASS verdicts legitimate?
10. **Implementation completeness audit** — what's actually DONE vs DEFERRED vs MISSING?

## Context from P23/P24 Replan (Just Completed)

P23+P24 were just replanned in the previous session (all auditor PASS). Key decisions from that replan that affect P22:

- P23 v2.0 = execution-layer-only, NO consent gate, NO L1-L4 risk tiers, NO HARD STOP
- P24 v2.0 = Hermes fork, NO consent gate (ADR-062 exempt), consciousness loop, emotion system
- P28-P36 = deploy/configure (not implement) after P24
- BLDM Q-decisions Q1-Q109 are binding (NOT Q116 as some docs claim)
- ADR-062 = Hermes safety paradigm shift (HARD STOP bypass for Hermes runtime)
- Co-CEOs: Guinevere=Eng+Research+HR, Pharsa=Finance+Ops+Content
- DAO full-spectrum company, Faiz OUTSIDE company
- Wallet 2/2 multisig

P22 plan files:
- `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md`
- `docs/setup-evidence/P22/plan/p22-full-capability-raw-access-replan.md`
- `docs/setup-evidence/P22/implementation/plan/p22-life-integration-implementation-plan.md`
- `docs/setup-evidence/P22/implementation/plan/p22-p23-p24-contracts.md`
