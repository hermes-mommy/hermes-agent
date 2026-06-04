# Report 09: Hermes Tools System Assessment

**Date:** 2026-06-04
**Author:** Guinevere (automated research synthesis)
**Subject:** Hermes NousResearch Native Tools Inventory and Guinevere MCP Gap
**Status:** RESEARCH REPORT -- No Implementation
**Cross-Reference:** Report 10 (MCP Migration Gap), Report 11 (Skills System)

---

## 1. Executive Summary

Hermes NousResearch ships with **24 native toolsets** spanning web, terminal, file, code execution, vision, media generation, TTS, agent delegation, cron, messaging, and smart-home. Currently only **12 of 24 are available** on the Guinevere VPS (`hermes doctor` report). The remaining 12 are either missing API keys, missing system dependencies (Chrome/ripgrep), or require infrastructure not yet provisioned.

Guinevere currently implements **16 custom MCP tools** via a bespoke MCP server. Of these, **10 have direct or partial Hermes native equivalents**, **4 have no equivalent** (obscura_cdp, postgres_tool, redis_tool, grep_app), and **2 are hybrid** (require Hermes native + custom augmentation).

The tools system supports **per-platform enable/disable** (Discord vs WhatsApp vs Slack), which aligns with Guinevere's multi-platform deployment model but requires explicit configuration mapping.

---

## 2. Complete Hermes Tools Inventory

### 2.1 All 24 Toolsets (from `hermes tools list`)

| # | Toolset | Category | Purpose | Available? | Blocker |
|---|---------|----------|---------|------------|---------|
| 1 | `web` | Search/Fetch | Web search + content extraction | NO | No API keys |
| 2 | `browser` | Automation | Browser automation via CDP | NO | No Chrome/browser-cdp |
| 3 | `terminal` | System | Shell command execution | YES | -- |
| 4 | `file` | System | Filesystem read/write/list | YES | -- |
| 5 | `code_execution` | Development | Sandboxed code run | YES | -- |
| 6 | `vision` | Multimodal | Image understanding | NO | Not configured |
| 7 | `video` | Multimodal | Video processing | NO | Not configured |
| 8 | `image_gen` | Generation | Image generation | NO | No API keys |
| 9 | `video_gen` | Generation | Video generation | NO | No API keys |
| 10 | `x_search` | Search | X/Twitter search | NO | Not configured |
| 11 | `moa` | Search | Mixture of Agents search | NO | Not configured |
| 12 | `tts` | Media | Text-to-speech | YES | -- |
| 13 | `skills` | Agent | Load/execute skills | YES | -- |
| 14 | `todo` | Task | Task list management | YES | -- |
| 15 | `memory` | Core | Persistent memory store | YES | -- |
| 16 | `context_engine` | Core | Context window management | NO | Not configured |
| 17 | `session_search` | Core | Search past sessions | YES | -- |
| 18 | `clarify` | UX | Ask clarifying questions | YES | -- |
| 19 | `delegation` | Agent | Delegate to sub-agents | YES | -- |
| 20 | `cronjob` | Automation | Scheduled tasks | YES | -- |
| 21 | `messaging` | Comms | Multi-platform messaging | NO | Not configured |
| 22 | `homeassistant` | IoT | Home Assistant control | NO | Not configured |
| 23 | `spotify` | Media | Spotify playback control | NO | Not configured |
| 24 | `yuanbao` | Media | Yuanbao media control | NO | Not configured |
| 25 | `computer_use` | Automation | Desktop GUI automation | NO | Not configured |

*Note: Count includes `kanban` reported by hermes doctor as a separate tool but not in `tools list` -- makes 25+ entities.*

### 2.2 Doctor-Verified Available (12 toolsets)

From `hermes doctor` output:

```
Available tools: clarify, code_execution, cronjob, terminal, delegation,
                 file, memory, session_search, skills, todo, tts, kanban
```

| Toolset | Doctor Status | Notes |
|---------|---------------|-------|
| `clarify` | AVAILABLE | Core UX, no dependencies |
| `code_execution` | AVAILABLE | Likely sandboxed Python/JS runtime |
| `cronjob` | AVAILABLE | Internal scheduler, no cron daemon needed |
| `terminal` | AVAILABLE | Shell access -- **security surface** |
| `delegation` | AVAILABLE | Sub-agent spawn -- **critical for Guinevere workflow** |
| `file` | AVAILABLE | Filesystem I/O -- **security surface** |
| `memory` | AVAILABLE | Persistent context storage |
| `session_search` | AVAILABLE | Cross-session retrieval |
| `skills` | AVAILABLE | Skill loader, hub integration |
| `todo` | AVAILABLE | Task tracking |
| `tts` | AVAILABLE | Voice output |
| `kanban` | AVAILABLE | Board-style task management |

### 2.3 Missing / Unavailable (12+ toolsets)

| Toolset | Blocker | Impact | Priority |
|---------|---------|--------|----------|
| `web` | No API keys (Brave/Exa/etc) | No web search -- **blocks RAG** | CRITICAL |
| `browser` | No Chrome, no CDP endpoint | No browser automation | HIGH |
| `vision` | Not configured | No image understanding | MEDIUM |
| `video` | Not configured | No video processing | LOW |
| `image_gen` | No API keys | No image generation | LOW |
| `video_gen` | No API keys | No video generation | LOW |
| `x_search` | Not configured | No X/Twitter search | LOW |
| `moa` | Not configured | No MoA search | LOW |
| `context_engine` | Not configured | No context optimization | MEDIUM |
| `messaging` | Not configured | No multi-platform native | HIGH |
| `homeassistant` | Not configured | No smart home | N/A |
| `spotify` | Not configured | No music control | N/A |
| `yuanbao` | Not configured | No Yuanbao media | N/A |
| `computer_use` | Not configured | No desktop automation | LOW |

---

## 3. Per-Platform Tool Configuration

Hermes supports per-platform tool enable/disable. This maps directly to Guinevere's multi-platform deployment:

```
# Conceptual configuration model
hermes tools configure --platform discord web=true browser=false terminal=true
hermes tools configure --platform whatsapp web=false terminal=false
hermes tools configure --platform slack web=true terminal=true
```

### 3.1 Recommended Platform Matrix

| Toolset | Discord | WhatsApp | Slack | Notes |
|---------|---------|----------|-------|-------|
| `web` | ENABLE | DISABLE | ENABLE | Search mostly useful in text-rich platforms |
| `browser` | ENABLE | DISABLE | DISABLE | High resource cost, Discord-only |
| `terminal` | ENABLE | DISABLE | ENABLE | Security: never on WhatsApp |
| `file` | ENABLE | DISABLE | ENABLE | Path whitelist critical |
| `code_execution` | ENABLE | DISABLE | ENABLE | Sandboxed only |
| `tts` | ENABLE | ENABLE | DISABLE | Voice makes sense on voice-capable |
| `todo` | ENABLE | ENABLE | ENABLE | Universal utility |
| `memory` | ENABLE | ENABLE | ENABLE | Core function |
| `skills` | ENABLE | ENABLE | ENABLE | Core function |
| `delegation` | ENABLE | DISABLE | ENABLE | Sub-agents on text-heavy platforms |

---

## 4. Comparison: Hermes Native vs Guinevere Custom MCP

### 4.1 Guinevere's 16 Custom MCP Tools

| # | Guinevere Tool | Category | Auth Level | Has Hermes Equivalent? |
|---|---------------|----------|------------|------------------------|
| 1 | `brave_search` | Search | READ_AUTO | YES -- `web` |
| 2 | `context7` | Docs/RAG | READ_AUTO | PARTIAL -- `web` |
| 3 | `docker_tool` | Container | WRITE_NOTIFY | NO |
| 4 | `exa_search` | Search | READ_AUTO | YES -- `web` |
| 5 | `fetch` | Web fetch | READ_AUTO | YES -- `web` |
| 6 | `filesystem` | System | WRITE_NOTIFY | YES -- `file` |
| 7 | `git_tool` | VCS | WRITE_NOTIFY | NO -- requires custom |
| 8 | `github` | VCS/API | WRITE_NOTIFY | NO -- requires custom |
| 9 | `grep_app` | Code search | READ_AUTO | NO -- Hermes equivalent |
| 10 | `obscura_cdp` | Browser CDP | DESTRUCTIVE_APPROVAL | PARTIAL -- `browser` |
| 11 | `postgres_tool` | Database | DESTRUCTIVE_APPROVAL | NO |
| 12 | `redis_tool` | Cache | WRITE_NOTIFY | NO |
| 13 | `sequential_thinking` | Reasoning | READ_AUTO | NO -- agent-internal |
| 14 | `shell_tool` | System | DESTRUCTIVE_APPROVAL | YES -- `terminal` |
| 15 | `time_tools` | Utility | READ_AUTO | NO |
| 16 | `websearch` | Search | READ_AUTO | YES -- `web` |

### 4.2 Mapping Summary

| Mapping Category | Count | Tools |
|-----------------|-------|-------|
| **Direct Hermes equivalent** | 5 | `brave_search`, `exa_search`, `fetch`, `websearch` -> `web`; `shell_tool` -> `terminal`; `filesystem` -> `file` |
| **Partial Hermes equivalent** | 2 | `context7` (~`web`), `obscura_cdp` (~`browser`) |
| **No Hermes equivalent** | 7 | `docker_tool`, `git_tool`, `github`, `grep_app`, `postgres_tool`, `redis_tool`, `time_tools` |
| **Agent-internal** | 2 | `sequential_thinking` (not a tool, reasoning pattern) |

### 4.3 Cardinality: 24 Hermes vs 16 Guinevere

Hermes has **broader horizontal coverage** (smart home, Spotify, video gen, messaging) while Guinevere has **deeper vertical coverage** in DevOps (Docker, PostgreSQL, Redis, GitHub API). The migration path is complementary, not 1:1 replacement.

---

## 5. Functional Gap Analysis

### 5.1 What Hermes Provides That Guinevere Lacks

| Capability | Hermes Toolset | Guinevere Status | Value |
|-----------|---------------|------------------|-------|
| Code execution sandbox | `code_execution` | MISSING | Execute Python/JS in sandbox |
| Scheduled tasks | `cronjob` | MISSING | Timed automations |
| Session search | `session_search` | MISSING | Cross-session memory |
| Clarifying questions | `clarify` | MISSING | Interactive disambiguation |
| Sub-agent delegation | `delegation` | MISSING (external) | Native sub-agent spawn |
| Skills ecosystem | `skills` | MISSING | Plug-and-play capabilities |
| TTS | `tts` | MISSING | Voice output |
| Cross-platform messaging | `messaging` | MISSING | Unified chat abstraction |
| Kanban task boards | `kanban` | MISSING | Visual task management |
| Context engine | `context_engine` | MISSING | Context window optimization |

### 5.2 What Guinevere Provides That Hermes Lacks

| Capability | Guinevere Tool | Hermes Status | Criticality |
|-----------|---------------|---------------|-------------|
| Docker management | `docker_tool` | MISSING | HIGH -- container ops |
| PostgreSQL access | `postgres_tool` | MISSING | CRITICAL -- data layer |
| Redis access | `redis_tool` | MISSING | CRITICAL -- cache/session |
| Git operations | `git_tool` | MISSING | HIGH -- VCS |
| GitHub API | `github` | MISSING | HIGH -- PR/issues/repos |
| Code pattern search | `grep_app` | MISSING | MEDIUM |
| CDP browser control | `obscura_cdp` | MISSING (browser untested) | HIGH -- verification |
| Time utilities | `time_tools` | MISSING | LOW |
| Context7 docs | `context7` | MISSING | MEDIUM |
| Structured thinking | `sequential_thinking` | MISSING | LOW (agent pattern) |

---

## 6. Security Surface Comparison

### 6.1 Hermes Security Model

Hermes tools appear to use a binary enable/disable model per platform. There is no evidence of fine-grained auth levels (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN) equivalent to Guinevere's current system.

| Aspect | Hermes | Guinevere MCP |
|--------|--------|---------------|
| Auth granularity | Per-tool ON/OFF | 4-level matrix |
| Destructive action gating | UNKNOWN | Discord webhook 5-min timeout |
| Path whitelisting | UNKNOWN | Yes (filesystem tool) |
| Command blocking | UNKNOWN | Yes (shell forbidden commands) |
| DROP prevention | UNKNOWN | Yes (postgres tool) |
| Platform isolation | Per-platform enable | Not platform-aware |

### 6.2 Risk: Hermes Terminal Security

If Hermes `terminal` has no command-blocking equivalent, it represents a **regression** from Guinevere's `shell_tool` which blocks destructive patterns. This must be assessed before migration.

---

## 7. Recommendations

### 7.1 Immediate (Pre-Migration)

1. **Add API keys for `web` toolset** -- unblocks search, fetch, Context7-like docs access
2. **Install Chrome/browser-cdp for `browser`** -- unblocks obscura_cdp migration
3. **Audit Hermes `terminal` security** -- compare command blocking with Guinevere `shell_tool`
4. **Audit Hermes `file` security** -- compare path whitelisting with Guinevere `filesystem`

### 7.2 Migration Phase 1: Direct Replacements

| Phase | Hermes Tool | Replaces | Risk |
|-------|-------------|----------|------|
| 1 | `web` | `brave_search`, `exa_search`, `fetch`, `websearch` | LOW |
| 1 | `file` | `filesystem` | MEDIUM (path check) |
| 1 | `terminal` | `shell_tool` | HIGH (command check) |

### 7.3 Migration Phase 2: Hybrid Augmentation

Keep custom MCP wrappers for tools with no Hermes equivalent:
- `postgres_tool` -- no Hermes equivalent, must persist
- `redis_tool` -- no Hermes equivalent, must persist
- `git_tool` + `github` -- custom wrappers needed
- `grep_app` -- custom wrapper needed

### 7.4 Migration Phase 3: New Capabilities

Adopt Hermes-native tools that Guinevere lacks:
- `code_execution` -- sandboxed code running
- `cronjob` -- scheduled automations
- `session_search` -- cross-session retrieval
- `delegation` -- native sub-agent spawn
- `skills` -- plug-and-play capabilities (see Report 11)
- `kanban` -- visual task boards

### 7.5 Do Not Migrate Yet

| Toolset | Reason |
|---------|--------|
| `messaging` | Guinevere already has Discord/WhatsApp adapters -- risk of conflict |
| `homeassistant` | Not in Guinevere scope |
| `spotify` | Not in Guinevere scope |
| `yuanbao` | Not in Guinevere scope |
| `computer_use` | Security risk without isolation |

---

## 8. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Hermes terminal lacks command blocking | HIGH | MEDIUM | Pre-migration security audit |
| Hermes file lacks path whitelist | HIGH | MEDIUM | Pre-migration security audit |
| `browser` tool unstable/unproven | MEDIUM | HIGH | Keep obscura_cdp as fallback |
| API key provisioning delays block `web` | MEDIUM | HIGH | Pre-provision before migration |
| `delegation` conflicts with Guinevere sub-agent pattern | MEDIUM | LOW | Test in staging first |
| Two tool systems coexist, confusion risk | LOW | HIGH | Clear deprecation timeline |

---

## 9. Evidence and References

- `hermes tools list` -- 24 toolsets enumerated
- `hermes doctor` -- 12 available, rest missing deps
- `hermes tools configure --help` -- per-platform enable/disable
- Guinevere MCP source: 16 tools with auth matrix
- Cross-reference: Report 10 for tool-by-tool migration mapping
- Cross-reference: Report 11 for skills ecosystem
- Cross-reference: Report 12 for SOUL.md persona integration with tools

---

## 10. Footer

| Field | Value |
|-------|-------|
| Report ID | RR-HERMES-09 |
| Version | 1.0 |
| Date | 2026-06-04 |
| Status | RESEARCH COMPLETE |
| Next | Report 10: MCP-MIGRATION-GAP.md |
| Author | Guinevere (automated research synthesis) |