# P24 Handoff Document — Session 2026-06-30

> **Purpose**: Resume P24 work in a FRESH Claude Code session. Read this file + memory files, then continue from "Next Step".
> **Date**: 2026-06-30 | **Branch**: feat/p24-hermes-fork | **Fork**: github.com/hermes-mommy/hermes-agent

---

## 1. Operator Intent (LOCKED, do not re-litigate)

- **"Truly 100% fork"** = new GitHub repo proper fork-and-diverge from NousResearch/hermes-agent@77a1650c + 0 mock/stub/CONFIG_MISSING in P1-P22 runtime + production live. All 3 dimensions.
- **End-game**: Guinevere = AI companion 24/7 (mama Faiz) + engineering co-pilot. NOT SaaS.
- **P24 strict** before P28-P36 (no parallel).
- **Port all src/ → guinvere/**, then hapus src/ everywhere (built-in = no src/).
- **Deploy**: side-by-side (P24-fork as new service, legacy untouched until verified, then switch).
- **Work style**: "diskusi tiap phase dulu" — autonomous WITHIN a phase, align BETWEEN phases.
- **Stub/mock = kegagalan inti** — Guinevere must not use ANY fake code. Test-fixture mocks OK.
- **9router** (VPS localhost:20128, `guinevere-9router.service`) = REAL LLM source (NOT mock). Models: `guinevere`, `deepseek-v4-flash`, `mimo`, `stepfun`. Chat works WITHOUT auth header on localhost.
- **consciousness loop should DELEGATE to Hermes AIAgent** (single brain), NOT call LLM itself. This is a design change chosen this session — see "In-Progress".
- **"multi hermes"** = NOT now, fokus P24. Multi-instance via config (1 fork, 2 instances: Guinevere+Pharsa).

## 2. State — DONE (verified, committed, pushed)

### Fork creation ✅
- Org `hermes-mommy` created (manual, GitHub removed POST /orgs API)
- Fork `hermes-mommy/hermes-agent` of NousResearch/hermes-agent (fork=true, MIT, fork badge)
- Branch `p24-initial` (default), **141 commits** pushed
- Fork relationship on GitHub confirmed via gh API

### Stabilization ✅ (commit c146466)
- .gitignore: token.json, .env.* glob, discovery-rest.txt, *.bak, cache dirs
- Redacted Grafana password in evidence/P3-ENTERPRISE-SETUP-EVIDENCE.md
- Deleted 110 junk files
- Fixed 22 swallow-except anti-patterns (Priority 1-3)
- 556 tests pass (pre-port)

### Port src/→guinvere/ ✅ (commit 38be76c4, on VPS + pushed to fork)
- **477 files ported** to guinvere/ namespace (deterministic script on VPS Linux)
- **564 total .py in guinvere/** (87 P24-native + 477 ported), **30 subpackages**
- Hybrid: 15 net-new full port + 7 overlap merge-keep-native
- 30/30 subpackages importable (prod venv + argon2-cffi installed)
- 541 tests pass, 0 `from src.` refs, 0 `guinvere.guinvere` double-nesting
- Fixes: persona/__init__ deprecated-import try/except guards; gamification/models `metadata`→`extra_metadata` (col kept)
- **Live on GitHub**: gh API confirms all 30 subpackages on p24-initial

## 3. Critical Environment Facts (caused 3 port failures, now solved)

1. **Windows NTFS forward-slash path anomaly**: `guinvere/` dir only stat-able via forward-slash paths; backslash → INVALID_FILE_ATTRIBUTES. `git add guinvere/` fails on Windows.
2. **Two indistinguishable `guinvere/` dirs on Windows local machine** (p24-fresh/guinvere vs anomalous repo /c/Users/faizz/guinevere/guinevere) → agents wrote to wrong one.
3. **`.gitignore:40 guinvere/`** (pre-existing) silently un-committed namespace — FIXED.
4. **Python text-mode subprocess `\r` injection** in git mktree stdin → tree entries named `"guinvere\r"`. Fix: bytes-mode stdin.

**SOLUTION = work on VPS Linux** (`/home/guinevere/p24-port`, clean paths, git works). DO NOT attempt port/mock-kill work on Windows local. All P24 execution should happen via `ssh guinevere-vps` on the p24-port clone.

## 4. Key Locations

- **Fork repo (remote)**: github.com/hermes-mommy/hermes-agent, branch p24-initial
- **VPS working clone**: `/home/guinevere/p24-port` (user `guinevere`, home /home/guinevere)
- **VPS prod venv** (has all deps): `/home/guinevere/code/guinevere/.venv/bin/python`
- **VPS prod (legacy, running)**: `/home/guinevere/code/guinevere` — runs `src.core.main:app` (LEGACY, NOT P24-fork)
- **VPS src/ source** (518 files, for reference): `/home/guinevere/code/guinevere/src/`
- **9router**: localhost:20128 on VPS (guinevere-9router.service, LIVE)
- **Local Windows repo** (anomalous, DO NOT use for port): `/c/Users/faizz/guinevere`
- **Port script** (proven): `C:/Users/faizz/port_vps.py`

## 5. In-Progress (NOT done — resume here)

### Phase 4.1 — MockLLMRouter → Hermes-delegate (DESIGN CHANGE)

**Original plan**: swap MockLLMRouter → RealLLMRouter (consciousness calls 9router directly via guinvere/core/services/llm_router.py).

**Operator correction this session**: consciousness loop should DELEGATE to Hermes AIAgent (single brain), NOT call LLM itself. "consciousness = hermes juga, bukan LLM sendiri."

**Current code reality** (verified):
- `guinvere/http/server.py:145` wires `_mock_router = _build_mock_llm_router()` into ConsciousnessLoop
- `guinvere/consciousness/substrates.py:67` `_self_prompt()` calls `llm_router.chat(messages, task_type, max_tokens)` DIRECTLY (not Hermes)
- consciousness/ has 0 imports of `agent`/`AIAgent`/`run_agent` — does NOT delegate to Hermes
- `guinvere/core/services/llm_router.py` (ported, 252 lines) = real router to 9router (model ds/deepseek-v4-flash default; operator said use `guinevere` combo model)
- `run_agent.py:327` = `class AIAgent` (importable, constructor takes base_url/api_key/provider/model)
- `agent/` adapters: anthropic_adapter, azure_identity_adapter, bedrock_adapter, codex_responses_adapter, gemini_cloudcode_adapter, gemini_native_adapter
- **Hermes agent NOT wired to 9router** (0 refs to 9router/20128 in agent/), and AIAgent import throws `AuthenticationError: invalid username-password pair` (provider init fails — needs wiring)

**Refactor required (operator approved "Full: wire Hermes + delegate consciousness")**:
1. Wire Hermes adapter → 9router (base_url=localhost:20128/v1, model=guinevere, no auth header needed for localhost). Resolve AuthError.
2. Refactor consciousness substrate `_self_prompt()`: replace `llm_router.chat()` → `agent.run()` (delegate to Hermes AIAgent as single brain). Adapt return shape (agent.run returns agent response, not {content,usage,model} dict).
3. Remove MockLLMRouter + `_build_mock_llm_router()` from server.py wiring.

**Research still needed**: AIAgent.run() signature/return, which adapter for OpenAI-compatible (9router), how Hermes config resolves provider (credential_pool custom_providers), where AuthError originates. I was mid-research when context ran low — see `agent/credential_pool.py:313 _iter_custom_providers`, `agent/anthropic_adapter.py`.

### Phase 4.2-4.10 — 9 tool backends stub→real (NOT started)
117/117 actions are stubs. Order (no-creds first): filesystem→vps→memory→desktop→browser→github(needs token)→social(needs creds)→email(OAuth in secrets/)→freelance(DEFER: Fiverr no API, Upwork ToS-banned, Freelancer.com stale SDK).

## 6. Next Steps (resume order)

1. **Resume Phase 4.1 refactor**: research Hermes AIAgent.run() + adapter wiring to 9router (on VPS, read run_agent.py:327+, agent/anthropic_adapter.py, agent/credential_pool.py). Then wire Hermes→9router, refactor consciousness substrate→delegate, remove MockLLMRouter. Test: real 9router inference through Hermes agent in consciousness loop.
2. Phase 4.2-4.6 (no-creds backends): filesystem, vps, memory, desktop, browser — autonomous.
3. Phase 4.4/4.8/4.9 (need creds): github (GITHUB_TOKEN), social (X/Telegram), email (Gmail OAuth in secrets/) — ASK operator.
4. Phase 4.10 freelance: document N/A (DEFER per feasibility research).
5. Phase 4.11: CONFIG_MISSING adapters → real creds (WhatsApp LIVE, X LIVE, Gmail/Telegram need creds).
6. Phase 5: deploy side-by-side (wire config, migrations, new service guinvere-core-p24:8090, verify E2E, switch, retire legacy).
7. Phase 6-8: audit, super-audit, docs.

## 7. File References (read these in fresh session)

- **This handoff**: `evidence/P24-deploy/HANDOFF-P24-SESSION.md`
- **Memory** (auto-loads): `~/.claude/projects/C--Users-faizz-guinevere/memory/` — p24-owned-fork-direction, p24-port-complete, p24-guinvere-gitignore-anomaly, p24-double-nested-import-bug, guinevere-prod-live-faiz-prod-01, p24-src-port-gotchas
- **Gap audit**: `evidence/P24-deploy/audit/full-gap-audit.md`
- **Port plan**: `evidence/P24-deploy/port/src-port-plan.md` (per-subpackage merge matrix, topological order)
- **Fork verification**: `evidence/P24-deploy/fork/fork-creation-verification.md`
- **Master plan**: `docs/superpowers/plans/2026-06-30-p24-truly-fork.md`
- **Soak log**: `docs/setup-evidence/P20/evidence/discord-visible-autonomy/soak-monitoring.md`

## 8. Caveats / Honest Notes

- **P20 soak**: legacy prod running clean (NRestarts=0, ~21h+). P24-fork NOT deployed yet — prod = legacy src/. Do NOT restart guinevere-core (legacy) unless real blocker.
- **P24 docs claim "COMPLETE"** — STALE/WRONG. Use this handoff + memory as truth, not the P24 full-completion docs.
- **2 VPS exist**: guinevere-vps (faiz-prod-01, Guinevere prod) vs ninerouter-vps (49.12.82.34, 9router-only). Don't confuse.
- Port work MUST happen on VPS Linux (p24-port clone), NOT Windows local (anomaly).
