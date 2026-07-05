# P21 Voice Interface — Tool & Skill Coverage Matrix

**Phase:** P21 Voice Interface (research + planning only — NO implementation/deploy)
**Date:** 2026-06-24
**Owner:** Guinevere (parent) for Faiz
**Status:** ACTIVE — source of truth for which MCP/tools/skills are used in this phase, which are NOT used, and why. No pretending.

---

## 1. Purpose

This matrix is mandated by the P21 objective ("First create a tool/skill coverage matrix").
It records, for every relevant MCP tool, harness tool, and skill available in this session,
whether it is used in the P21 research/planning wave, and the reason for the decision. If a
relevant tool/skill is unavailable or fails, the fallback is documented here — not hidden.

Per AGENTS.md §12 and §14 (Sub-Agent Output Discipline), this file itself is parent-authored
(not a sub-agent deliverable) and lives under the P21 research root.

---

## 2. Available MCP Servers / Tools

### 2.1 Web search & content retrieval

| Tool | Used? | Reason | Output / where |
|---|---|---|---|
| `brave_web_search` | ✅ YES | General provider/API/vendor discovery; official-doc cross-reference for STT/TTS/realtime providers, Discord voice constraints, VAD/wake-word. | Cited in `p21-voice-provider-research.md`, `p21-discord-voice-research.md`, `p21-runtime-latency-deploy-research.md` |
| `brave_news_search` | ⚠️ CONDITIONAL | Only if provider pricing/news changes mid-research. Not expected to be primary. | — |
| `brave_llm_context` | ✅ YES | Pre-extracted page substance for official docs (provider docs, Discord developer docs) — gives the actual content, not just links. Reduces fetch round-trips. | Cited in provider + Discord + runtime research files |
| `brave_local_search` | ❌ NO | Voice providers are remote/cloud; no local-POI relevance. | — |
| `brave_place_search` | ❌ NO | No geographic place search needed. | — |
| `brave_image_search` | ❌ NO | No image artifacts required for a planning phase. | — |
| `brave_summarizer` | ❌ NO | Research agents synthesize their own summaries with explicit citations. | — |
| `brave_video_search` | ⚠️ CONDITIONAL | Only if a provider has a video-only changelog (rare). | — |
| `exa` (`web_search_exa`, `web_fetch_exa`) | ✅ YES | Semantic/deep search for architecture patterns (e.g. realtime voice pipelines, WebRTC audio transport, streaming STT). `web_fetch_exa` reads full official-doc pages. | Cited in hermes-core, runtime/latency, provider research |
| `context7` (`resolve-library-id`, `query-docs`) | ✅ YES | Version-aware library docs for any SDK the plan references: `discord.py` voice, `pynacl`/`PyNaCl` for Opus, `webrtc` libs, Whisper/`faster-whisper`, `elevenlabs`/`openai` SDKs. Avoids stale training-data API signatures. | Cited in discord-voice + hermes-core + runtime research |
| `tavily` (`tavily_search`, `tavily_extract`, `tavily_research`, `tavily_crawl`, `tavily_map`) | ✅ YES (research/extract) | `tavily_research` for multi-source provider/vendor comparison; `tavily_extract` for full official-doc page content (provider pricing/spec pages). `tavily_crawl`/`map` not needed. | Cited in provider + runtime + dependency-collision research |
| `linkup` (`linkup-search`, `linkup-research`, `linkup-fetch`) | ✅ YES (search/fetch) | Secondary web search + autonomous research for provider readiness / streaming-audio constraints. Cross-references brave/exa. | Cited in provider + runtime research |
| `jina-reader` (`read_url`, `parallel_read_url`, `search_web`, `parallel_search_web`, `guess_datetime_url`, `sort_by_relevance`) | ✅ YES | Clean markdown extraction of official docs; parallel reads for batched provider pages; `guess_datetime_url` to confirm doc freshness; `sort_by_relevance` to rank provider claims. | Cited across provider/discord/runtime research |
| `jina-reader` (`search_arxiv`/`parallel_search_arxiv`, `search_ssrn`, `search_bibtex`) | ❌ NO | P21 is engineering planning, not academic literature. VAD/wake-word have practical docs, not needed as papers. | — |
| `jina-reader` (`classify_text`, `deduplicate_strings`, `deduplicate_images`, `expand_query`, `primer`, `show_api_key`, `capture_screenshot_url`, `extract_pdf`) | ❌ NO | Not relevant to research/planning (screenshot/PDF/classify/dedup not needed). `expand_query`/`primer` marginally useful but research agents craft their own queries. | — |

### 2.2 Code / repo / docs tools

| Tool | Used? | Reason | Output / where |
|---|---|---|---|
| `mcp__github__*` (search_code, search_repositories, get_file_contents, etc.) | ✅ YES (search only) | `search_code`/`grep_app`-style discovery of real-world discord.py voice + STT/TTS integration patterns. Read-only; no repo writes, no PRs, no commits in this phase (P21 is planning-only; AGENTS.md forbids deploy/commit without request). | Cited in hermes-core + discord-voice research |
| `mcp__grep_app__searchGitHub` | ✅ YES | Literal code-pattern search for production patterns of `discord.VoiceClient`, Opus encode/decode, streaming TTS, Whisper streaming. | Cited in discord-voice + hermes-core research |
| Built-in `Grep` / `Glob` / `Read` | ✅ YES | Parent recon of `src/` (hermes, life_kernel, discord, memory, core) to ground integration design in actual code. | This phase's recon + all research agent prompts |
| Built-in `Bash` (read-only) | ✅ YES (mkdir/ls only) | Created P21 directory tree; `ls`/`git status` checks. No deploy/restart/destructive ops. | P21 dir creation |

### 2.3 Reasoning / orchestration

| Tool | Used? | Reason | Output / where |
|---|---|---|---|
| `mcp__sequential-thinking__sequentialthinking` | ⚠️ OPTIONAL | Research/audit agents reason in-prose with citations; sequential-thinking not required for file-based deliverables. Parent may use it for the plan synthesis decision tree. | If used, noted in plan |
| `Workflow` tool | ✅ YES | Orchestrates the parallel research wave (9 specialists), audit waves (8×2), each writing explicit output files. **Honors surfaced memory: file-writing workflow agents MUST omit `agentType`** (Explore is read-only; cannot write). | research/, evidence/audits/ |
| `Agent` tool | ✅ YES | Fallback / targeted single-agent delegation when Workflow is unsuitable (e.g. a one-off deep read). File-writing agents use default workflow subagent (no `agentType` that is read-only). | As needed |
| `TaskCreate`/`TaskUpdate`/`TaskList` | ✅ YES | Tracking the 10-step P21 plan. | This phase's task list |

### 2.4 Not available / not connected

| Tool | Status | Impact | Fallback |
|---|---|---|---|
| `playwright` MCP | Listed in MCPConfigGuide as a Guinevere prod tool, NOT connected in this session | No browser automation for live provider dashboard screenshots. Not needed for planning. | Official-doc research via brave/exa/tavily/jina fetch tools instead. |
| `postgres` / `redis` MCP | Not connected in this session (would need prod VPS creds) | Cannot query live schema. Not needed — `src/memory/models.py` read directly gives the schema. | Direct `Read` of `src/memory/models.py`. |
| `filesystem` MCP | Not connected (use built-in Write/Read/Edit) | — | Built-in file tools. |
| `time` MCP | Not connected | Timestamps via system date (2026-06-24 given). | Inline dates. |

---

## 3. Available Skills (invoked via `Skill` tool)

| Skill | Used? | Reason | Output / where |
|---|---|---|---|
| `superpowers:using-superpowers` | ✅ YES (session) | Establishes skill-use discipline at session start. | — |
| `superpowers:brainstorming` | ⚠️ CONDITIONAL | P21 is a defined research/planning spec, not open creative ideation. Used implicitly via research agents. Not blocking. | — |
| `superpowers:writing-plans` | ✅ YES | The enterprise plan (`p21-voice-interface-enterprise-plan.md`) is a multi-step implementation plan for later waves — `writing-plans` discipline applies (per-step scaffold, evidence paths, hard rejection). | `plan/p21-voice-interface-enterprise-plan.md` |
| `superpowers:dispatching-parallel-agents` | ✅ YES | Research wave (9) + audit waves (8×2) are independent parallel tasks with file outputs. | research/ + evidence/audits/ |
| `superpowers:subagent-driven-development` | ❌ NO | No implementation in this phase (planning-only). Reserved for later P21-001..009 execution. | — |
| `superpowers:executing-plans` | ❌ NO | No plan execution this phase. | — |
| `superpowers:test-driven-development` | ❌ NO | No code written this phase. | — |
| `superpowers:systematic-debugging` | ❌ NO | No bug under investigation. | — |
| `superpowers:requesting-code-review` / `receiving-code-review` | ✅ YES (audit role) | The audit waves ARE the code-review-of-the-plan mechanism. Auditor findings received via `receiving-code-review` discipline (verify, don't performatively agree). | evidence/audits/round-1, round-2 |
| `superpowers:verification-before-completion` | ✅ YES | Parent must verify each research/audit file exists + is parent-read before marking complete. No self-report as evidence. | All deliverables |
| `superpowers:using-git-worktrees` | ❌ NO | No code changes; planning-only. Worktree isolation not needed (no shared-writer conflict). | — |
| `superpowers:finishing-a-development-branch` | ❌ NO | No branch to finish. | — |
| `deep-research` | ⚠️ CONDITIONAL | Research agents do targeted official-doc research with their own citations; the full `deep-research` harness is heavier than needed per-specialist. Provider/runtime agents may use it for broad multi-source questions. | If used, cited in that research file |
| `code-review` / `code-review:code-review` | ❌ NO | No diff to review (no implementation). | — |
| `feature-dev:*`, `ui-ux-pro-max`, `frontend-design` | ❌ NO | No UI/frontend build this phase. Discord voice UX is specced in prose/embed design, not built. | — |
| `skill-creator` / `writing-skills` / `claude-md-management` | ❌ NO | Not creating skills or editing CLAUDE.md this phase. | — |
| `update-config` / `keybindings-help` / `loop` / `run` / `verify` / `init` / `review` / `security-review` / `fewer-permission-prompts` | ❌ NO | Operational/harness skills not relevant to research/planning deliverables. (`security-review` applies to a diff; no diff here. `verify`/`run` apply to runtime code; none written.) | — |

---

## 4. Coverage Summary

- **Official-doc research (provider/API claims):** brave (web + llm_context), exa (search + fetch), context7 (library docs), tavily (search + extract + research), linkup (search + research + fetch), jina-reader (read_url + parallel_read_url + search_web + guess_datetime_url + sort_by_relevance). ✅ Fully covered; multiple independent sources per claim per the hard-rejection rule.
- **Code-pattern research:** github search_code, grep_app searchGitHub, built-in Grep/Glob/Read. ✅ Covered.
- **Local system grounding:** built-in Read/Grep/Glob/Bash(read-only). ✅ Covered.
- **Orchestration:** Workflow + Agent + Task tools. ✅ Covered (with the agentType-write-trap respected).
- **Plan/audit discipline:** writing-plans + dispatching-parallel-agents + requesting/receiving-code-review + verification-before-completion. ✅ Covered.

## 5. Fallback Discipline

If any research agent reports a tool failure (e.g. context7 library not found, brave rate-limited),
the agent MUST document it in its output file and fall back to another source in the same category
(brave↔exa↔tavily↔linkup↔jina are mutually substitutable for web content). No claim may rest on a
single tool that failed silently.

## 6. Footer

| Field | Value |
|---|---|
| Matrix author | Guinevere (parent) |
| Reviewed against | AGENTS.md §12 (Tool/MCP selection), §14 (sub-agent output discipline) |
| Hard rejection honored | No tool falsely marked "used"; fallbacks documented where relevant |
| Next update | If a tool fails during research wave, amend §2/§5 here before final report |
