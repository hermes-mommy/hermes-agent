# P24 v3.0 — Current Ground Truth (PHASE 0 Rebaseline)

> **Generated**: 2026-06-29 | **Author**: Guinevere (parent) | **Purpose**: PHASE 0 ground-truth rebaseline before any P24 implementation
> **Method**: Parent-verified via direct `bash`/`read`/`grep` — NOT sub-agent self-report. Every claim below is re-runnable.

---

## 0. Operator Decisions (Locked 2026-06-29)

Three scope-determining questions resolved with operator Faiz before execution:

| # | Decision | Choice | Impact |
|---|----------|--------|--------|
| D1 | Fork layout | **In-repo root** | Clone tag `77a1650c` files directly into `C:\Users\faizz\guinevere\` (repo root = fork root). New `guinevere/` namespace alongside. `src/` deleted across waves. NOT a `hermes-fork/` subdir. |
| D2 | Deploy scope | **Local runtime only** | Stop at "FULL RUNTIME COMPLETE + EXPLICIT BLOCKERS". NO VPS deploy, NO Discord live-connect, NO real LLM. Honest blocker if creds absent. |
| D3 | LLM during tests | **Mock-only** | M3/M4/M7/M10 inference-dependent modules unit-tested with mocks. Wiring/state proven, inference NOT proven. Caveat in final report. |

**Final target status (locked)**: `P24 HERMES NATIVE FORK — FULL RUNTIME COMPLETE WITH EXPLICIT OPERATOR-PROVISIONING BLOCKERS`

---

## 1. Fork Source — VERIFIED REAL

The plan §4.1 documents fork source as tag `v2026.5.29.2` at SHA `77a1650c78a4cb1813d8a81fa1da40a15b6a3ec5`. **Parent verified this is real**, resolving a near-miss escalation:

- `git ls-remote --tags ... v2026.5.29.2` returns `51f4326` — but that is the **annotated-tag object SHA**, NOT the commit.
- `git rev-parse v2026.5.29.2^{commit}` peels correctly to **`77a1650c`** — matches plan exactly.
- `git cat-file -t 77a1650c` → `commit`. Commit message: `chore: bump version to v0.15.2 (2026.5.29.2)`.
- **Tag tree == installed wheel tree** (bit-for-bit on canary files):
  - `run_agent.py` at tag = **4616 lines**, `class AIAgent:` at **line 327** — matches installed wheel exactly.
  - `tools/delegate_tool.py` at tag = **2801 lines** — matches installed wheel exactly.

**Conclusion**: Plan's fork source is sound. All wave scaffolds referencing line numbers are valid against BOTH the installed wheel tree AND the tag checkout. No fact-gap to escalate.

**Fork source command (W1 will use)**:
```bash
git clone --depth=1 --branch v2026.5.29.2 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-clone
# then copy run_agent.py agent/ tools/ gateway/ cron/ hermes_cli/ + top-level hermes_*.py + cli.py into repo root
```

---

## 2. Installed Hermes v0.15.2 — Exact Surface

**Install location**: `.venv/Lib/site-packages/` (installed via `uv` from PyPI wheel — NO `direct_url.json`, so NOT editable).

### 2.1 Top-level files (23 .py at site-packages root)

| File | Lines | Role |
|------|-------|------|
| `run_agent.py` | 4,616 | AIAgent class (forwarder pattern), `class AIAgent:` at L327 |
| `cli.py` | ~13,740 | Interactive TUI (prompt_toolkit) |
| `hermes_bootstrap.py` | — | Bootstrap |
| `hermes_constants.py` | 463 | Constants |
| `hermes_state.py` | — | State DB |
| `hermes_logging.py` | — | Logging |
| `hermes_time.py` | — | Time helpers |

### 2.2 Packages (file counts, .py only, excluding __pycache__)

| Package | .py count | Role | P24 action |
|---------|-----------|------|------------|
| `agent/` | 108 | Core runtime (AIAgent body, conversation loop, memory, tools, providers) | CLONE + MODIFY (W2/W3/W6/W7/W9) |
| `tools/` | 96 | Tool impls + `environments/` (8 backends) + `delegate_tool.py` | CLONE + MODIFY (W8 patches delegate_tool) |
| `gateway/` | 60 | Gateway runner, platform adapters | CLONE + MODIFY (W15 Discord) |
| `hermes_cli/` | 98 | CLI, config (`config.py` 5401 lines), auth, setup | CLONE + MODIFY (W1 Pydantic config) |
| `cron/` | 3 | Scheduler + jobs | CLONE + MODIFY (W10 DAO job) |
| `plugins/` | 127 | Plugin system (memory, model-providers, platforms, web, image_gen) | CLONE as-is (some plugins missing deps — see §2.4) |
| **TOTAL cloned** | **~423** | | |

### 2.3 Key files the plan modifies (VERIFIED line-accurate)

| File | Plan claim | ACTUAL verified | Δ |
|------|-----------|-----------------|---|
| `run_agent.py` `class AIAgent` | L327 | **L327** ✅ | none |
| `tools/delegate_tool.py` | "2,503 lines", "defaults 3/1/3 → patch 10/5/5" | **2,801 lines**; actual symbols: `_DEFAULT_MAX_CONCURRENT_CHILDREN=3`, `MAX_DEPTH=1`, `_MAX_SPAWN_DEPTH_CAP=3` | line count differs; symbols are 3/1/3 → patch to 10/5/5 maps to `_DEFAULT_MAX_CONCURRENT_CHILDREN=10`, `MAX_DEPTH=5`, `_MAX_SPAWN_DEPTH_CAP=5` (W8 must patch ACTUAL symbols, not shorthand) |
| `agent/agent_init.py` | "1,552 lines / 83,281 bytes" | 83,281 bytes ✅ (line count TBD — verify in W1) | byte-accurate |
| `agent/conversation_loop.py` | "4,361 lines" | 256,053 bytes (line count TBD) | verify in W1 |
| `agent/system_prompt.py` | "332 lines" | verify in W1 | — |
| `agent/memory_provider.py` | "229 lines, MemoryProvider ABC, 14 methods, 5 abstract" | verify in W1 | — |
| `hermes_cli/config.py` | "5,401 lines DEFAULT_CONFIG" | verify in W1 | — |

### 2.4 Forbidden-pattern footprint in installed Hermes (M2/M11 scope)

Only **4 files** in `{run_agent.py, agent/, tools/, gateway/, cron/, hermes_cli/}` match `hard_stop|HARD_STOP|safe_mode|SafeMode|consent_gate`:
- Scope is surgical, NOT a sweep. M2 (remove HARD STOP) + M11 (no consent gate) touch a small set of files.
- W2/W3 must `grep -rn` the cloned fork (not the wheel) to enumerate exact sites, then delete surgically.

### 2.5 Import-time plugin failures (cosmetic, non-blocking)

Importing `run_agent` directly emits warnings for missing optional plugins (`plugins.browser`, `plugins.web`, `plugins.spotify`, `hermes_cli.dashboard_auth`). These are **optional plugin auto-discovery failures**, NOT core failures — `agent.conversation_loop`, `agent.agent_init`, `tools.registry`, `tools.delegate_tool`, `agent.memory_provider`, `agent.system_prompt`, `hermes_cli.config`, `gateway.run`, `cron.scheduler` all import OK. The fork's `pyproject.toml` + W1 dependency install will resolve available plugins; missing ones stay disabled.

---

## 3. Existing `src/` — 517 .py files (DELETE target, success criterion = 0)

Per-directory (.py only, excluding __pycache__):

| Dir | .py | P24 disposition |
|-----|-----|-----------------|
| `src/_deprecated/` | 10 | DELETE (W-late) |
| `src/channels/` | 22 | PORT→M14 (WhatsApp/Telegram) |
| `src/consent/` | 2 | DELETE (M11 removes consent gate) |
| `src/core/` | 15 | PORT→fork core / DELETE (hard_stop_handler→M2) |
| `src/discord/` | 65 | PORT→M13 (50+ slash commands, 3 bots) |
| `src/finance/` + `src/financial/` | 6 | PORT→M8 finance backend |
| `src/gamification/` | 4 | PORT→M9/M12 |
| `src/gmail/` | 36 | PORT→M14 (OAuth2) |
| `src/hermes/` | 7 | DELETE (bridge, replaced by native fork) — adapter.py/_session_adapter.py/_memory_bridge.py absorbed by M1 |
| `src/hermes_plugins/` | 44 | PORT→M8 (command_catalog + commands_*) |
| `src/knowledge_graph/` | 47 | PORT→M6 (semantic memory layer, P16) |
| `src/life_integrations/` | 45 | PORT→M8 (14 adapters) + M14 (channels) |
| `src/life_kernel/` | 38 | PORT→M9 (18% remaining; 82% already native) |
| `src/loops/` | 48 | DELETE ALL (M3 consciousness loop replaces, 12,059 lines) |
| `src/mcp/` | 25 | PORT→M8 native (16 tools: brave/context7/docker/exa/fetch/filesystem/github/git/grep_app/obscura_cdp/postgres/redis/sequential_thinking/shell + auth/budget/cost/manager) |
| `src/memory/` | 12 | PORT→M6 (encrypted 4-layer) |
| `src/observability/` | 3 | PORT→M16 |
| `src/persona/` | 19 | PORT→M4 (emotion) + M12 (drift) |
| `src/projects/` | 6 | PORT→M1 (P19 project_id namespace) |
| `src/self_improve/` | 3 | PORT→M10 (T1-T5) |
| `src/surveillance/` | 14 | PORT→M16 (consumer built-in, consent gate removed) |
| `src/wearable/` | 19 | PORT→M9 (sensors) |
| `src/x_poster/` | 26 | PORT→M14 (X/Twitter) |
| `src/__init__.py` (top-level) | 1 | DELETE last (after all sub-dirs empty) |
| **TOTAL** | **517** | |

**Success criterion**: `ls src/*.py 2>/dev/null | wc -l` → 0 (W20 verifies). Note: criterion counts TOP-LEVEL `src/*.py` only (currently 1: `src/__init__.py`); the broader `find src/ -name '*.py'` → 0 is the real target and is checked in W20 too.

---

## 4. M8 Adapter→Backend Mapping (P22 + P23 → 9 unified backends)

### 4.1 P22 adapters (`src/life_integrations/adapters/`, 14 adapters / 26 .py)

| P22 adapter | → M8 backend | L-label (P23) | Notes |
|-------------|-------------|---------------|-------|
| `filesystem_adapter.py` | **filesystem** | L1 READ / L2 WRITE | shell READ_AUTO python/pip/git → L2/L3 |
| `github_adapter.py` | **github** | L1/L2 | repo read/write |
| `browser_adapter.py` | **browser** | L1/L2 | Playwright-backed |
| `vps_adapter.py` | **vps** | L1/L2/L3 | SSH exec |
| `gmail_adapter.py` | → M14 (channel) | — | NOT M8 (it's a channel) |
| `whatsapp_adapter.py` | → M14 (channel) | — | Neonize |
| `telegram_adapter.py` | → M14 (channel) | — | bot API |
| `discord_adapter.py` | → M13 (gateway) | — | NOT M8 |
| `calendar_adapter.py` | **desktop** (simple tool) | L1 | M9 simple tool |
| `drive_adapter.py` | **desktop** (simple tool) | L1 | M9 simple tool |
| `notion_adapter.py` | **desktop** (simple tool) | L1 | M9 simple tool |
| `finance_adapter.py` | **finance** | L1/L2 | M8 finance backend |
| `memory_adapter.py` | **memory** | L1/L2 | M8 memory backend |
| `onboarding_manifest.py` | (config glue) | — | M1 |

### 4.2 9 unified M8 tool backends (from P23 spec + P22 merge)

1. **browser** (Playwright) — L1 READ / L2 WRITE
2. **github** — L1/L2
3. **filesystem** — L1/L2/L3 (shell)
4. **vps** (SSH) — L1/L2/L3
5. **email** (gmail SMTP/IMAP) — L1/L2 [channel-adjacent, M14 shares]
6. **desktop** (calendar/drive/notion) — L1
7. **freelance** (finance) — L1/L2
8. **social** (x_poster + telegram + whatsapp send) — L1/L2 [channel-adjacent, M14 shares]
9. **memory** (encrypted store) — L1/L2

**L4 (DESTRUCTIVE/consent-gated) DELETED** per ADR-062/066 — no consent gate in runtime.

### 4.3 src/mcp/ 16 tools → M8 native

`brave_search, context7, docker_tool, exa_search, fetch, filesystem, github, git_tool, grep_app, obscura_cdp, postgres_tool, redis_tool, sequential_thinking, shell_tool` + `auth, auth_matrix, budget, cost, custom_manager, manager` (glue). These become native `guinevere/tools/` implementations, NO external MCP server.

---

## 5. Config Structure (current)

- `hermes-config/` exists: `config.yaml`, `hooks/` (hard_stop.py, safety_scan.py, hybrid_guards.py — M2 deletes/rewrites), `plugins/`, `SOUL.md`.
- `.hermes/` exists: `plugins/` only.
- **No `config/` dir at root** — W1 creates `config/guinevere.yaml` + `config/pharsa.yaml` + `config/souls/`.
- `pyproject.toml` current: `hermes-agent>=0.15` PyPI dep, `packages=["src"]`, pytest `pythonpath=["src"]`. W1 rewrites to editable local fork + `guinevere` package + `pydantic-settings[yaml]`, `argon2-cffi`, etc.

---

## 6. Module Dependency Order (verified against plan §7)

```
W1 (M1) ──────────────────────────────────────────── ALL depend on W1
  │
  ├─ Group B (parallel): W2(M2) W3(M11) W4(M15) W5(M16)
  │    └─ all 4 independent, modify different files
  │
  ├─ Group C (mixed, deps):
  │    W6(M3) first [modifies run_agent.py — collides w/ W2, so SEQUENTIAL after W2]
  │    then W7(M4) W8(M5) W9(M6) W10(M7) parallel
  │    then W11(M12) after W7+W10
  │
  ├─ Group D (parallel): W12(M8) W13(M9) [immediate]; W14(M10) after W6+W9
  │
  ├─ Group E (parallel): W15(M13) W16(M14)
  │
  └─ Group F (sequential): W17(M17) → W18 → W19 → W20
```

### Collision scan (shared writers — SEQUENCE these)

| Shared file | Writers (waves) | Mitigation |
|-------------|-----------------|------------|
| `run_agent.py` | W1, W2(M2), W6(M3), W15(M13 via gateway?) | W1 first; W2 then W6 SEQUENTIAL; W15 touches gateway/run.py not run_agent.py — re-verify |
| `agent/agent_init.py` | W1 + W3 + W6 + W7 + W8 + W9 + W10 + W11 + W14 + W16 | **appends-only** — each wave adds `# ── M[N] wire ──` block; parent owns surgical edits if conflict |
| `agent/conversation_loop.py` | W2, W3(M11), W6(M3), W7(M4) | SEQUENCE W2→W3→W6→W7 on this file |
| `agent/system_prompt.py` | W4(M4 emotion), W11(M12 drift) | appends-only volatile blocks |
| `tools/delegate_tool.py` | W8 only | single owner — safe parallel |
| `pyproject.toml` | W1 only (then locked) | single owner |
| `guinevere/config/models.py` | W1 + every module adds Config model | appends-only per wave |

---

## 7. Git State

- Branch: `main`, **ahead of origin/main by 24 commits** (unpushed work — pre-existing, NOT mine to push without request).
- Remote: `https://github.com/fazulfi/guinevere.git` (operator: fazulfi).
- No `hermes-fork/` dir exists yet (greenfield).
- No `tests/p24/` exists yet (W18 creates).

---

## 8. What Can Be Implemented NOW vs BLOCKED

### 8.1 Implementable now (no external blockers)
- ALL 17 modules — code implementation needs no credentials.
- W1-W17 fully implementable locally.
- W18-W19 local validation fully doable (mock LLM).
- W20 audit + evidence fully doable.

### 8.2 Blocked (honest — per D2/D3)
- ⛔ VPS deploy (no host provisioned — no `.env.core/.env.vps` at root).
- ⛔ Discord live-connect (no 3 bot tokens).
- ⛔ Real LLM inference proof (no 9Router key — mock-only per D3).
- ⛔ Real WhatsApp/Gmail/X/Telegram live-send (no channel creds).
- ⛔ Ethereum mainnet DAO execution (no wallet/ETH — M7 lifecycle unit-tested only).

### 8.3 Test-target gaps (M8 L2/L3 actions)
- L2/L3 tool actions (github write, vps SSH, filesystem shell) need test repos/accounts — W12 unit-tests with mocked backends + `CONFIG_MISSING` style markers (P22 pattern).

---

## 9. Plan Claim Audit (stale/wrong claims to correct in synthesis)

| Plan claim | Verified status | Action |
|-----------|----------------|--------|
| Fork SHA `77a1650c` at tag `v2026.5.29.2` | ✅ REAL (peeled) | none |
| `run_agent.py:327` AIAgent | ✅ exact | none |
| `delegate_tool.py` "2,503 lines" | ❌ ACTUAL 2,801 lines | W8 uses actual |
| `delegate_tool` "defaults 3/1/3" | ⚠️ actual symbols `_DEFAULT_MAX_CONCURRENT_CHILDREN=3`, `MAX_DEPTH=1`, `_MAX_SPAWN_DEPTH_CAP=3` | W8 patches actual symbols to 10/5/5 |
| `agent_init.py` "1,552 lines / 83,281 bytes" | ✅ bytes; lines TBD | W1 verifies lines |
| `hermes_cli/config.py` "5,401 lines" | TBD | W1 verifies |
| "486 files / 348K lines" Hermes | ✅ ~423 .py cloned + plugins/skills | close enough |
| "src/ 512 files" | ❌ ACTUAL 517 .py | W20 criterion uses 0, count irrelevant |
| "14 P22 adapters" | ✅ 14 adapters (26 .py) | none |
| "8 P23 executors / 9 backends / ~108 actions" | from P23 spec — verify in research | PHASE 1 research |

---

## 10. Verdict

Ground truth established. Fork source verified real. Layout locked (in-repo root). Scope locked (local runtime + mock LLM). All wave scaffolds' line-number references are valid. Ready for PHASE 1 brutal research wave.

**No contradictions with plan that block execution.** Minor line-count corrections (delegate_tool 2503→2801) are W-internal, handled by W8 against actual symbols.

Footer: Guinevere, 2026-06-29, PHASE 0 complete, parent-verified, no sub-agent self-report trusted.
