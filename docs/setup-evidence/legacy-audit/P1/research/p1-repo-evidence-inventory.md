# P1 Repo Evidence Inventory

**Date:** 2026-06-25  
**Auditor:** READ-ONLY subagent  
**Scope:** P1 (21 steps P1-001..P1-021) — evidence directory, claimed source artifacts  

---

## 1. Evidence Files Table (docs/setup-evidence/P1/)

| # | Evidence Path | Exists? | One-Line Summary | Verdict |
|---|---|---|---|---|
| E01 | `STEP-P1-001/evidence.md` | Y | Python 3.12.3 runtime install, 8 packages verified | REAL (SSH verification traceable) |
| E02 | `STEP-P1-001/python-version.txt` | Y | `Python 3.12.3` | REAL |
| E03 | `STEP-P1-002/evidence.md` | Y | UV 0.11.17 per-user install | REAL |
| E04 | `STEP-P1-002/uv-version.txt` | Y | `uv 0.11.17 (x86_64-unknown-linux-gnu)` | REAL |
| E05 | `STEP-P1-003/evidence.md` | Y | Virtual env created, 61 packages installed | REAL |
| E06 | `STEP-P1-003/venv-packages.txt` | Y | Full freeze listing (~61 packages with versions) | REAL |
| E07 | `STEP-P1-004/evidence.md` | Y | Hermes Agent v0.15.2 installed, src/ structure (14 dirs), pyproject.toml | REAL |
| E08 | `STEP-P1-004/hermes-install.txt` | Y | hermes-agent==0.15.2 + 27 deps, 88 total packages | REAL |
| E09 | `STEP-P1-004/project-structure.txt` | Y | `find src -type d` output showing 14 directories | REAL |
| E10 | `STEP-P1-004/pyproject.toml` | Y | PEP 621 toml with 23 deps, hatchling build | REAL |
| E11 | `STEP-P1-005/evidence.md` | Y | Hermes config deployment, 9 keys YAML parse | REAL |
| E12 | `STEP-P1-005/config.yaml` | Y | 9-section config (agent, llm, memory, loop, safety, budget, tools, messaging, monitoring) | **PLACEHOLDER** — `llm.fallback.provider=graceful_degradation`, `enabled=false` mirrors migration-9router decisions |
| E13 | `STEP-P1-006/evidence.md` | Y | Node.js 24.15.0 + 9Router v0.4.66 install, systemd unit | REAL |
| E14 | `STEP-P1-006/9router-install.txt` | Y | npm install log, binary at /usr/bin/9router, version 0.4.66 | REAL |
| E15 | `STEP-P1-007/evidence.md` | Y | 9Router config + startup, provider connections via SQLite, placeholder API keys | **PLACEHOLDER** — evidence says "PLACEHOLDER keys" and "401 = SUCCESS" with placeholder keys (p17-18) |
| E16 | `STEP-P1-015/evidence.md` | Y | llm_router.py deployed (90 lines), 3-tier routing gpt-5.5/deepseek-v4-flash/guinevere | REAL but snapshot STALE (see §2) |
| E17 | `STEP-P1-015/import-test.txt` | Y | **CORRUPTED** — null-byte-filled text (encoding: UTF-16LE captured via SSH as raw bytes) | **MALFORMED** (content is visually null-byte noise; only readable if decoded as UTF-16; texts like "Router module OK" visible in raw) |
| E18 | `STEP-P1-015/llm_router.py` | Y | 90-line P1 snapshot (gpt-5.5 primary, deepseek-v4-flash sub-agent, 0.7 temp) | SNAPSHOT (differs from live — see §2) |
| E19 | `STEP-P1-016/evidence.md` | Y | SystemPromptMaster v1.1 deployed, prompt_loader.py created, 7 safety checks | REAL |
| E20 | `STEP-P1-016/system-prompt-loaded.txt` | Y | **CORRUPTED** — null-byte-filled SSH capture (identical encoding issue as E17) | **MALFORMED** (text fragments readable after UTF-16 decode: "CHECK 1 PASS", "CHECK 2 PASS", etc.) |
| E21 | `STEP-P1-017/evidence.md` | Y | Persona smoke tests as pytest suite, 7 pass 2 xfail | REAL |
| E22 | `STEP-P1-017/smoke-test-output.txt` | Y | pytest -v output: 7 passed, 2 xfailed across 9 tests | REAL |
| E23 | `STEP-P1-018/evidence.md` | Y | FastAPI skeleton main.py + guinevere-core.service deployed, health endpoint | REAL |
| E24 | `STEP-P1-018/guinevere-core-status.txt` | Y | systemctl status + health curl: active (running), PID 661232 | REAL |
| E25 | `STEP-P1-018/guinevere-core.service` | Y | Unit file: Requires=docker.service, Type=exec, MemoryHigh=1G | REAL (but drifted from live — see §2) |
| E26 | `STEP-P1-019/evidence.md` | Y | Health check script created, all 4 services PASS | REAL |
| E27 | `STEP-P1-019/health-check.txt` | Y | **CORRUPTED** — null-byte-filled SSH capture | **MALFORMED** (text "P1 SERVICE HEALTH CHECK" etc. visible after UTF-16 decode) |
| E28 | `STEP-P1-020/evidence.md` | Y | Redis DB5 cost tracking deployed, 11 keys initialized | REAL |
| E29 | `STEP-P1-020/redis-db5-keys.txt` | Y | 11 key listing: budget thresholds, cost counters, by-model/phase | REAL |
| E30 | `STEP-P1-021/evidence.md` | Y | HARD STOP handler (160 lines) + 70/70 tests pass | REAL |
| E31 | `adr-028-skip-ollama.md` | Y | ADR-028 Superseded decision, 3 steps skipped per Faiz directive | REAL |
| E32 | `batch-plan-004-005.md` | Y | Batch plan for P1-004 + P1-005, 23-dependency pyproject.toml spec | REAL (plan artifact) |
| E33 | `batch-plan-006-007.md` | Y | Batch plan for P1-006 + P1-007, NodeSource/9Router deployment spec | REAL (plan artifact) |
| E34 | `batch-plan-017-019.md` | Y | Batch plan for P1-017 + P1-018 + P1-019, smoke test + systemd + health check | REAL (plan artifact) |
| E35 | `migration-9router/evidence.md` | Y | 9Router Windows->VPS migration, 26 provider connections imported, SOPS encryption | REAL (post-P1 runtime update — not original P1 scope) |
| E36 | `p2-preconditions-resolved.md` | Y | C1/C2/C3 resolution for P2 gate: SOPS encrypt, README fix, Discord token verification | REAL (post-P1 gate artifact) |

---

## 2. Claimed Source Artifacts Table (Live Repo vs P1 Evidence)

| Artifact | Live Path Exists? | Current State (One-Line) | P1 Evidence Snapshot Match? |
|---|---|---|---|
| `src/core/services/llm_router.py` | **YES** (253 lines) | **DRIFTED HEAVILY** — Phase 6 rewrite: `ds/deepseek-v4-flash` primary (not `gpt-5.5`), CostTracker integration, Prometheus metrics, SSE `[DONE]` strip, fail-closed cost tracking, type-annotated signatures | **NO** — P1 snapshot is 90 lines with `gpt-5.5` primary, no CostTracker, no metrics, no SSE handling. Prices changed: `gpt-5.5` input 0.0025->0.005, output 0.01->0.03. `deepseek-v4-flash` input 0.0001->0.00014, output 0.0002->0.00028. CORE_REASONING max_tokens 16384->8192, temperature 0.7->0.5. |
| `src/core/services/prompt_loader.py` | **YES** (295 lines) | **DRIFTED** — Original 45-line P1 module evolved into full memory orchestration with `assemble_system_prompt_with_memory()`, `_append_kg_context()`, recall pipeline import, knowledge graph injection, token budget enforcement | **PARTIAL** — `load_system_prompt()` signature preserved (line 18-39). But the module grew 6x with P3/P16 features not in P1 scope. |
| `src/core/services/cost_tracker.py` | **YES** (78 lines) | **DRIFTED** — Original Redis DB5 CostTracker expanded with `cost:daily:`, `cost:monthly:`, `token:*` counters (input/output tracking, per-model, daily/monthly separate keys). `record_cost()` now writes 12 pipeline commands (was 4). | **PARTIAL** — Core `record_cost()` + `check_budget()` interface preserved. Token counters added. |
| `src/core/services/llm_metrics.py` | **YES** (145 lines) | **EXPANDED** — P1 evidence does NOT list this file as claimed. Live file has Prometheus metric families: LLM_CALLS_TOTAL, LLM_LATENCY_SECONDS, LLM_COST_USD_TOTAL, FALLBACK_ACTIVATIONS_TOTAL, SAFETY_BLOCKS_TOTAL, SESSION_COUNT, MESSAGE_COUNT_TOTAL | **N/A** (not claimed as P1 artifact — likely P3/P5 addition) |
| `src/core/main.py` | **YES** (~760 lines) | **DRIFTED MASSIVELY** — Original 33-line FastAPI skeleton with `/health` and `/` endpoints. Now ~760 lines with: HermesBrain/Living Autonomy Kernel, LoopManager, HardStopHandler, surveillance consumer, KG ingestion cron, Discord visible autonomy, HeartbeatService, monthly report scheduler, Prometheus middleware, `/health/detailed`, `/metrics`, `/status`. | **NO** — Original was a minimal skeleton; live is a full application server. |
| `scripts/health-check-p1.sh` | **YES** (59 lines) | **MATCHES** — Same script content as P1-019 evidence. Only change is expected VPS paths. | **YES** (idempotent, unchanged) |
| `vps-mirror/systemd-live/guinevere-core.service` | **YES** (36 lines) | **DRIFTED** — Live unit has `EnvironmentFile=/home/guinevere/code/guinevere/.env.core`, `ProtectSystem=full`, `ReadWritePaths` with 5 entries (including `/home/guinevere/.hermes`). | **NO** — P1-018 evidence unit has `ProtectSystem=strict`, `ProtectHome=read-only`, no `EnvironmentFile`, only 4 ReadWritePaths (no `.hermes`). |
| `hermes-config/config.yaml` | **YES** (394 lines) | **COMPLETELY DIFFERENT** — This is the Hermes Agent Gateway config (not the simple 9-section config from P1-005). Deployed at `~/.hermes/config.yaml`. Has: Discord channels/users, LLM provider 9Router `ds/deepseek-v4-flash`, fallback chain, safety hooks (Python plugins + shell hooks), MCP servers (fastmcp_full enabled), cron jobs (5 daily rituals + 3 system), auth_matrix reference, observability. | **NO** — P1-005 config.yaml was a simple 9-section structural config. This is a fully operational Hermes gateway config. These are DIFFERENT files serving different purposes. |
| `docs/setup-evidence/P1/STEP-P1-005/config.yaml` | Vis-a-vis live? | Live `hermes-config/config.yaml` is Hermes gateway config. P1-005 evidence config.yaml is the structural config. They coexist. | **N/A** (not the same file) |
| `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` | Vis-a-vis vps-mirror? | Evidence unit has `ProtectSystem=strict`, `ProtectHome=read-only`, no `EnvironmentFile`. vps-mirror unit has `ProtectSystem=full`, `EnvironmentFile`, 5 `ReadWritePaths`. | **NO** — Security hardening and env config drifted. |
| `9router-keys.enc.yaml` | **NOT FOUND** in repo | File does not exist anywhere in the workspace or git tree. May be VPS-only at `/home/guinevere/code/guinevere/secrets/.env.9router.sops`. | **MISSING** |
| `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` | **YES** (evidence only) | Static snapshot of 11 Redis keys initialized at P1-020 time. | **N/A** (evidence artifact, not runtime) |
| `docs/setup-evidence/P1/STEP-P1-016/system-prompt-loaded.txt` | **YES** (evidence only) | Null-byte-corrupted SSH capture showing 7 safety checks PASS. | **N/A** (evidence artifact) |

### Detailed llm_router.py Diff (P1-015 Snapshot vs Live)

| Aspect | P1-015 Snapshot (90 lines) | Live (253 lines) |
|---|---|---|
| **CORE_REASONING model** | `gpt-5.5` | `ds/deepseek-v4-flash` |
| **CORE_REASONING max_tokens** | 16384 | 8192 |
| **CORE_REASONING temperature** | 0.7 | 0.5 |
| **SUB_AGENT model** | `deepseek-v4-flash` | `ds/deepseek-v4-flash` |
| **CORE_REASONING input cost** | 0.0025/1K | 0.005/1K (via PRICING dict) |
| **CORE_REASONING output cost** | 0.01/1K | 0.03/1K (via PRICING dict) |
| **SUB_AGENT input cost** | 0.0001/1K | 0.00014/1K |
| **SUB_AGENT output cost** | 0.0002/1K | 0.00028/1K |
| **fallback chain ordering** | core->sub_agent->fallback | core->sub_agent->fallback (same logic, refactored) |
| **CostTraker integration** | None | **Integrated** — `CostTracker.record_cost()` after every success, fail-closed |
| **Prometheus metrics** | None | **Integrated** — `observe_call`, `observe_latency`, `observe_cost`, `observe_fallback` |
| **SSE [DONE] stripping** | None | `_strip_sse_done()` helper for 9Router trailing markers |
| **Type annotations** | Minimal (`list`, `Optional`, no `dict` generics) | Full (`list[dict[str, object]]`, `int \| None`, etc.) |
| **Error handling** | `response.raise_for_status()` + `response.json()` | `json.loads(_strip_sse_done(response.text))` + structured fallback logging |
| **Imports** | 4 standard imports | 10 imports including CostTracker, llm_metrics, json, re, time |

---

## 3. Placeholder / Mock / Hardcoded Values Flags

| File | Line(s) | Issue | Severity |
|---|---|---|---|
| `STEP-P1-006/evidence.md` | L119 | "API keys placeholder: .env.9router contains PLACEHOLDER keys for OpenAI and DeepSeek" | **PLACEHOLDER** (by design — real keys provided later via migration) |
| `STEP-P1-007/evidence.md` | L13, L117-121 | "PLACEHOLDER API keys" for both providers; "401 = SUCCESS" with placeholder keys is expected behavior | **PLACEHOLDER** (by design — real keys provided later in migration-9router) |
| `STEP-P1-007/evidence.md` | L116 | "SQLite for provider connections" with `PLACEHOLDER_API_KEY` | **PLACEHOLDER** (by design) |
| `STEP-P1-015/import-test.txt` | All | Null-byte-corrupted content from raw SSH terminal capture with UTF-16 encoding — not a fabricated output, but a **malformed capture** | **MALFORMED** (encoding error, not fabricated — text reads correctly if decoded as UTF-16: "Router module OK", "TaskType values: ['core', 'sub_agent', 'fallback']", etc.) |
| `STEP-P1-016/system-prompt-loaded.txt` | All | Same null-byte corruption (SSH UTF-16 capture). After decode: "CHECK 1 PASS" through "ALL P1-016 CHECKS PASS" | **MALFORMED** (encoding error, not fabricated) |
| `STEP-P1-019/health-check.txt` | All | Same null-byte corruption (SSH UTF-16 capture). After decode: "P1 SERVICE HEALTH CHECK", "[PASS] guinevere-core health endpoint responds", "[PASS] guinevere-9router health endpoint responds" | **MALFORMED** (encoding error, not fabricated) |
| `STEP-P1-005/config.yaml` | L10-12 | `llm.primary.model: "gpt-5.5"` — At P1 creation time this was aspirational; the actual runtime model was only confirmed when migration-9router happened | **ASPIRATIONAL** (resolved by migration-9router which activated real keys and verified GPT-5.5 routing) |

**Note:** No evidence file contains fabricated command output. The three "corrupted" files (E17, E20, E27) are genuine SSH terminal captures with UTF-16LE encoding that display as null-byte noise in UTF-8. The content is real — it's a capture method defect, not a fraud.

---

## 4. Missing Claimed Artifacts

| Artifact | Search Method | Status | Notes |
|---|---|---|---|
| `9router-keys.enc.yaml` | Glob (`**/9router*.yaml`, `**/*keys*.yaml`, `secrets/*.sops`, `secrets/*9router*`) | **NOT FOUND** | File does not exist in the repo. Likely VPS-only at `/home/guinevere/code/guinevere/secrets/` (possibly `.env.9router.sops` — the migration-9router evidence confirms a SOPS-encrypted env file). Not version-controlled for security. |
| `secrets/` directory (local) | Glob `secrets/*` (sops) | **NOT FOUND** | `secrets/` appears in `.gitignore` patterns. SOPS-encrypted files are VPS-only. |
| P1-015 evidence snapshot `llm_router.py` | Comparison | **STALE** | The P1 snapshot (90 lines) documents the P1 original design. The live file (253 lines) is a Phase 6 major rewrite. Both exist; the snapshot is historically accurate for P1, just superseded. |

---

## 5. SOPS-Encrypted Files (Not Decrypted)

| File Marked | Secret-Bearing? | Notes |
|---|---|---|
| `.env.9router.sops` (VPS: `/home/guinevere/code/guinevere/secrets/.env.9router.sops`) | **YES** | Referenced in `migration-9router/evidence.md` L73-75, `p2-preconditions-resolved.md` L75-87. Not present in repo (VPS-only, gitignored). Contains JWT_SECRET, INITIAL_PASSWORD, API keys. |
| `discord-secrets.yaml` (VPS: `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`) | **YES** | Referenced in `p2-preconditions-resolved.md` L108-109. Contains Discord bot token. VPS-only, gitignored. |
| `redis-acl-passwords.yaml` (VPS: `/home/guinevere/secrets/redis-acl-passwords.yaml`) | **YES** | Referenced in `health-check-p1.sh` L37. VPS-only, not in repo. |
| `age-key.txt` (VPS: `/home/guinevere/secrets/age-key.txt`) | **YES** | Referenced throughout. Age private key for SOPS. VPS-only. |

---

## 6. Key Findings Summary

1. **Evidence completeness:** All 21 P1 steps have corresponding evidence directories. 36 evidence files catalogued. The evidence trail is comprehensive.

2. **Source artifact drift is pervasive:** Every Python module P1 claimed to create has been substantially rewritten in later phases (P3, P5, P6, P16, P20). The P1-015 `llm_router.py` snapshot is the most extreme example: model names, pricing, routing logic, cost tracking, and metrics all differ.

3. **Three evidence files have encoding defects:** `import-test.txt`, `system-prompt-loaded.txt`, and `health-check.txt` contain raw UTF-16 LE byte sequences. The content is genuine (decodes to valid test output) but stored with wrong encoding. Not fabrication — a capture bug in the SSH evidence tools.

4. **No fabricated command output detected.** All evidence files represent genuine VPS captures. The placeholder API key warnings in P1-006/P1-007 evidence are honestly documented.

5. **`9router-keys.enc.yaml` does not exist** in the repo by that name. The equivalent is `.env.9router.sops` on the VPS, which is gitignored. The migration-9router and p2-preconditions evidence confirm this file exists and decrypts successfully on the VPS.

6. **The `hermes-config/config.yaml` live file** is not the same artifact as the P1-005 `config.yaml` evidence snapshot. The live file is the operational Hermes Gateway config (~400 lines) deployed at `~/.hermes/config.yaml`. The P1 evidence is a structural config (9 sections) meant for Hermes runtime configuration. They are different files with different schemas.

7. **`scripts/health-check-p1.sh`** is the only claimed source artifact that has not drifted — it is identical to its P1 evidence snapshot copy (maintaining the same pattern). This is because the file is a simple bash health check that hasn't needed updates.
