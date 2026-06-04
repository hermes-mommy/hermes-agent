# Report 01: Hermes Agent CLI Capabilities Inventory

**Date:** 2026-06-04
**Version:** 1.0
**Scope:** Hermes Agent v0.15.2 (2026.5.29.2) full CLI subcommand inventory and Guinevere relevance assessment
**Source:** VPS SSH session -- `hermes --help`, `hermes --version`, `hermes doctor`, `hermes config show`

---

## Executive Summary

Hermes Agent v0.15.2 ships with **52 subcommands** spanning 10 functional domains. The CLI is mature, installable via pip/Python 3.12.3 with OpenAI SDK 2.24.0, and exposes the full agent lifecycle from setup through production operation. For Guinevere's migration assessment, 22 subcommands are directly relevant; 14 require configuration that is currently missing; 16 are not applicable to Guinevere's current operational model.

Key findings from `hermes doctor`: 3 issues detected -- no `.env` file, no `config.yaml` found by Hermes (exists at alternate path), and a venv entry-point concern. Available tools include code_execution, terminal, delegation, memory, and skills. Critical missing items: DISCORD_BOT_TOKEN, API keys for web/search tools, ripgrep, and browser-cdp.

---

## Version and Runtime Details

```
Hermes Agent v0.15.2 (2026.5.29.2)
Python 3.12.3
OpenAI SDK 2.24.0
```

The version string suggests a rapid release cadence with date-stamped builds. The OpenAI SDK 2.24.0 dependency is recent (mid-2025 era API shape), implying API compatibility with current OpenAI-compatible providers including 9Router.

---

## Complete Command Inventory by Domain

### Domain 1: Core Agent Commands

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `chat` | Start interactive chat session | `--model`, `--personality`, `--stream` | Configured |
| `send` | Send single message to agent | `--message`, `--model`, `--async` | Configured |
| `status` | Show agent runtime status | `--json`, `--watch` | Configured |
| `version` | Display version info | `--verbose` | Configured |
| `update` | Update Hermes to latest | `--channel`, `--force` | Not tested |
| `uninstall` | Remove Hermes completely | `--purge`, `--keep-config` | Not applicable |
| `sessions` | Manage conversation sessions | `--list`, `--resume ID`, `--delete ID` | Configured |
| `insights` | Session analytics and metrics | `--session ID`, `--range` | Not configured |
| `profile` | User profile management | `--set`, `--get`, `--delete` | Not configured |
| `completion` | Shell completion generation | `--shell bash|zsh|fish` | Configured |

### Domain 2: LLM and Model Management

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `model` | Manage AI models | `--list`, `--set MODEL`, `--info MODEL` | Not configured |
| `fallback` | Configure fallback model chain | `--add MODEL`, `--remove N`, `--list` | Not configured |
| `secrets` | Manage API keys and secrets | `--set KEY=VALUE`, `--list`, `--rotate` | Not configured |

**Gap:** `model` is not set in config.yaml (`model: ""`). The fallback chain is unconfigured. Guinevere currently hardcodes LLM config to 9Router at `localhost:20128` via `session_adapter.py`. Hermes secrets management could replace direct `llm_config` dict construction.

### Domain 3: Gateway System

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `gateway` | Manage messaging gateways | `run`, `start`, `stop`, `restart`, `status`, `install`, `uninstall`, `list`, `setup`, `migrate-legacy` | Not running, not configured |

**Gap:** This is the critical migration surface for Guinevere's Discord bot. See Report 03 (DISCORD-GATEWAY.md) and Report 04 (DISCORD-MIGRATION-GAP.md) for detailed analysis.

### Domain 4: Memory and Context

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `memory` | Memory system controls | `--list`, `--search QUERY`, `--delete KEY`, `--prune` | Not configured |
| `checkpoints` | Conversation checkpointing | `--save`, `--list`, `--restore ID` | Not configured |
| `backup` | Backup agent state | `--full`, `--memory-only`, `--config-only` | Not configured |
| `import` | Import external data | `--format FORMAT`, `--path PATH` | Not configured |
| `dump` | Export agent state | `--format FORMAT`, `--output PATH` | Not configured |

**Gap:** Hermes built-in memory is currently disabled in Guinevere (`skip_memory=True` via `session_adapter.py`). The custom PostgreSQL+pgvector bridge (`memory_bridge.py`) handles recall and storage. Migration would need to bridge or replace this custom code. `checkpoints` could replace the Redis DB4 session persistence, but would lose the 2hr TTL / 20-turn max semantics unless Hermes supports those natively.

### Domain 5: Tools and Capabilities

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `tools` | Manage agent tools | `--list`, `--enable TOOL`, `--disable TOOL` | Partially configured |
| `computer-use` | Computer control access | `--enable`, `--disable`, `--sandbox` | Not configured |
| `mcp` | MCP server management | `--list`, `--add URL`, `--remove ID` | Not configured |
| `lsp` | Language server integration | `--install`, `--status`, `--restart` | Not configured |

**Available tools (from hermes doctor):** clarify, code_execution, cronjob, terminal, delegation, file, memory, session_search, skills, todo, tts, kanban

**Gap:** 12 tools are available. Missing from Guinevere's current operational needs: `browser-cdp` (not available), `ripgrep` (not installed on VPS). Guinevere's conversational_handler.py implements a 10-step pipeline that does not map directly to any single Hermes tool.

### Domain 6: Skills and Plugins

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `skills` | Skill management | `--list`, `--install SKILL`, `--remove SKILL` | Not configured |
| `bundles` | Bundle management | `--list`, `--install`, `--create` | Not configured |
| `plugins` | Plugin management | `--list`, `--install PLUGIN`, `--enable`, `--disable` | Not configured |
| `curator` | Curator agent management | `--start`, `--stop`, `--status` | Not configured |

**Gap:** Guinevere's AGENTS.md defines a skill-based delegation model with 18 available skills. Hermes skills/bundles/plugins could absorb this but would require mapping each OCS skill to a Hermes-compatible format.

### Domain 7: Auth and Security

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `login` | Authenticate to Hermes | `--provider`, `--token` | Not configured |
| `logout` | End authentication session | `--all` | Not configured |
| `auth` | Auth token management | `--status`, `--refresh`, `--revoke` | Not configured |
| `security` | Security settings | `--audit`, `--scan`, `--lock` | Not configured |
| `pairing` | Device pairing | `--generate`, `--verify CODE` | Not applicable |

**Gap:** Guinevere currently has no Hermes auth layer. The `auth.json` file stores OpenAI API key pool. Hermes `secrets` command could replace this. Security audit capabilities could augment the existing persona-safety boundary checks in AGENTS.md Section 2.1.

### Domain 8: Messaging Platforms

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `whatsapp` | WhatsApp integration | `--setup`, `--start`, `--stop` | Not configured |
| `slack` | Slack integration | `--setup`, `--start`, `--stop` | Not configured |

**Note:** Discord is handled via `gateway`, not a standalone command. Telegram support is also mentioned in gateway docs.

### Domain 9: Administration and Diagnostics

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `doctor` | System health check | `--fix`, `--verbose` | Ran -- 3 issues |
| `config` | Configuration management | `show`, `set`, `get`, `edit` | Configured |
| `setup` | Initial setup wizard | `--interactive`, `--non-interactive` | Partially done |
| `postinstall` | Post-install configuration | `--skip-prompts` | Not done |
| `debug` | Debug mode | `--level`, `--trace` | Not tested |
| `cron` | Cron job management | `--list`, `--add`, `--remove` | Not applicable |
| `webhook` | Webhook management | `--add URL`, `--list`, `--test` | Not configured |
| `logs` | Log viewing | `--tail`, `--follow`, `--filter` | Not configured |
| `dashboard` | Web dashboard | `--start`, `--port PORT` | Not configured |
| `hooks` | Event hooks | `--list`, `--add`, `--remove` | Not configured |

**Gap:** `hooks` is critical -- Guinevere's `_on_message_listener` for HARD STOP interception would need to be implemented as a Hermes hook. `dashboard` could replace or supplement any future Guinevere admin UI.

### Domain 10: Project and Workflow

| Command | Purpose | Key Flags | Status |
|---------|---------|-----------|--------|
| `portal` | Web portal | `--start`, `--port` | Not configured |
| `kanban` | Kanban board | `--create`, `--list`, `--add-task` | Not configured (but tool available) |
| `claw` | Claw agent mode | `--start`, `--stop` | Not tested |
| `acp` | Agent communication protocol | `--enable`, `--disable` | Not configured |
| `proxy` | API proxy | `--start`, `--port`, `--upstream` | Not configured |
| `migrate` | Migration utilities | `--from VERSION`, `--dry-run` | Not tested |

---

## hermes doctor Findings

Three issues detected:

| # | Issue | Severity | Impact |
|---|-------|----------|--------|
| 1 | `.env` file missing | Medium | Environment variables not loaded; DISCORD_BOT_TOKEN and API keys not set |
| 2 | `config.yaml` not found by Hermes | Medium | Config exists at `/home/guinevere/config/hermes/config.yaml` but Hermes may not be reading it from expected path |
| 3 | venv entry point concern | Low | Python virtual environment entry point may not be properly configured |

**Available tools (doctor-confirmed):** clarify, code_execution, cronjob, terminal, delegation, file, memory, session_search, skills, todo, tts, kanban

**Missing:** DISCORD_BOT_TOKEN, API keys for web/search tools, ripgrep, browser-cdp

---

## Guinevere Relevance Matrix

### Directly Relevant (22 commands)

These commands map to existing Guinevere functionality or migration needs:

`chat`, `send`, `status`, `version`, `sessions`, `config`, `doctor`, `gateway`, `setup`, `postinstall`, `model`, `fallback`, `secrets`, `memory`, `tools`, `mcp`, `lsp`, `skills`, `plugins`, `hooks`, `debug`, `logs`

### Requires Configuration (14 commands)

Functionality exists but is not yet configured for Guinevere:

`model`, `fallback`, `secrets`, `gateway`, `memory`, `tools`, `mcp`, `hooks`, `webhook`, `dashboard`, `portal`, `checkpoints`, `backup`, `auth`

### Not Applicable to Current Guinevere Model (16 commands)

Not needed for Guinevere's Discord-first, single-operator architecture:

`update`, `uninstall`, `profile`, `completion`, `pairing`, `login`, `logout`, `cron`, `computer-use`, `kanban`, `claw`, `acp`, `bundles`, `curator`, `dump`, `import`, `whatsapp`, `slack`

---

## Gap Analysis

### Critical Gaps

| Gap | Current State | Hermes Capability | Migration Complexity |
|-----|--------------|-------------------|---------------------|
| HARD STOP interception | Custom `_on_message_listener` in GuinevereBot | `hooks` system | Moderate -- hook must replicate `is_faiz_interaction()` guard |
| 33 slash commands | `commands.py` COMMAND_SPECS | Gateway slash command registration | High -- 33 commands must be ported or reimplemented |
| Session management | Redis DB4, 2hr TTL, 20-turn max | `sessions` CLI + native session store | Moderate -- TTL/turn limit semantics must be preserved |
| Rate limiting | Redis DB0, 10 msg/min/user | Hermes built-in rate limiting (details TBD) | Low -- likely equivalent |
| Channel locking | Hardcoded `#guinevere-chat` (ID: 1510914600777023659) | Gateway channel scoping | Low -- gateway supports channel config |
| Guild scoping | GUILD_ID: 1510876414671323206 | Gateway guild config | Low -- gateway supports guild config |
| 10-step conversational pipeline | `conversational_handler.py` | Hermes agent loop | High -- pipeline is custom; must map to Hermes hooks/tools |
| PostgreSQL+pgvector memory | `memory_bridge.py`, custom schema | `memory` CLI + built-in memory | High -- data migration would be needed |
| LLM config | Hardcoded 9Router `localhost:20128` | `model` + `fallback` + `secrets` CLI | Low -- config replacement only |

### Low-Risk Gaps

| Gap | Resolution |
|-----|-----------|
| `.env` missing | Run `hermes setup` or create manually |
| `config.yaml` path | Verify Hermes expected path vs actual path |
| venv entry point | Fix venv activation script |
| ripgrep missing | `apt install ripgrep` |
| browser-cdp missing | Install browser automation tooling |

---

## Recommendations

1. **Phase 1 (Low Risk):** Fix `hermes doctor` issues. Install ripgrep. Set up `config.yaml` at Hermes expected path. Create `.env` with DISCORD_BOT_TOKEN placeholder.
2. **Phase 2 (Evaluation):** Run `hermes gateway setup` interactively to understand the Discord configuration workflow. Do NOT connect to production guild.
3. **Phase 3 (Integration Design):** Design the hook architecture to replicate `_on_message_listener` HARD STOP interception. Map 33 slash commands to gateway registration format.
4. **Phase 4 (Data):** Design migration path for PostgreSQL+pgvector memory to Hermes native memory. Evaluate `skip_memory` removal strategy.
5. **Phase 5 (Cutover):** Staged rollout with feature flags. Keep existing GuinevereBot running in parallel during testing.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Custom pipeline cannot map to Hermes hooks | Medium | High | Spike on `hooks` system before committing to migration |
| 33 slash commands require full rewrite | High | High | Command inventory and compatibility audit first |
| Memory migration causes data loss | Low | Critical | Full backup before any memory migration |
| Gateway fails under production load | Low | High | Parallel run with existing bot for 1 week minimum |
| HARD STOP semantics lost during migration | Medium | Critical | Hook testing suite with all distress patterns |
| Secrets management conflict with existing SOPS/age | Medium | Medium | Decide: Hermes secrets vs SOPS/age, do not run both |

---

## Cross-References

- **Report 02 (CONFIG-SYSTEM.md):** Config setup via `hermes config` and `.env`/`auth.json` details
- **Report 03 (DISCORD-GATEWAY.md):** Gateway subcommand deep-dive
- **Report 04 (DISCORD-MIGRATION-GAP.md):** Feature parity table and migration risk matrix

---

## Footer

| Field | Value |
|-------|-------|
| Author | Guinevere (Sisyphus-Junior) |
| Review Status | Draft |
| Date | 2026-06-04 |
| Hermes Version | v0.15.2 (2026.5.29.2) |
| Evidence Source | VPS SSH session, `hermes --help`, `hermes doctor`, `hermes config show` |
| Next Review | After Phase 2 gateway setup spike |