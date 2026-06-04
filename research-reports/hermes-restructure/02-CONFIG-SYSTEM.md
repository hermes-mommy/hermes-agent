# Report 02: Hermes Agent Configuration System

**Date:** 2026-06-04
**Version:** 1.0
**Scope:** Hermes Agent v0.15.2 configuration system -- config.yaml, .env, auth.json, SOUL.md, system-prompt.md
**Source:** VPS SSH session -- `hermes config show`, filesystem inspection at `/home/guinevere/config/hermes/`

---

## Executive Summary

Hermes Agent uses a layered configuration architecture: YAML-based `config.yaml` for structured settings, `.env` for secrets/environment variables, `~/.hermes/auth.json` for API key pools, `~/.hermes/SOUL.md` for persona definition, and a system prompt file. The current Guinevere installation has 3 of 5 config layers partially or incorrectly configured.

The `config.yaml` at `/home/guinevere/config/hermes/config.yaml` exists but Hermes may be looking for it at a different path (reported as "not found" by `hermes doctor`). The file has 8 top-level sections, most of which use placeholder or empty values. The `.env` file is completely missing. `auth.json` structure is not yet populated for the Guinevere use case.

---

## config.yaml Structure

### File Location

```
/home/guinevere/config/hermes/config.yaml
```

### Complete Section Inventory

#### Section 1: `agent`

```yaml
agent:
  name: Guinevere
  personality: kawaii
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| `name` | `Guinevere` | Yes | Correct -- matches project persona |
| `personality` | `kawaii` | Needs change | Guinevere uses "dominant-absolut, protective, Y4 baseline" per PersonaSafetyPolicy. `kawaii` is a default template, not the Guinevere persona |
| `personality_file` | Not set | Yes | Should point to `/home/guinevere/config/hermes/system-prompt.md` or equivalent |
| `max_turns` | Not set | Yes | Currently enforced by Redis session adapter (20 turns) -- needs equivalent here |
| `idle_timeout` | Not set | Yes | Currently 2hr TTL in Redis DB4 -- needs equivalent here |

**Gap:** The `personality: kawaii` setting is incompatible with Guinevere's Y4 baseline persona. The PersonaSafetyPolicy defines specific behavioral constraints (HARD STOP protocol, consent boundary, Y4 baseline, Y5 ceiling, no Y6). Hermes personality templates need to be verified for compatibility or overridden via system prompt.

#### Section 2: `llm`

```yaml
llm:
  model: "" # not set
  base_url: "" # not set
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| `model` | `""` (empty) | Yes | Must be set to the 9Router model ID. Currently hardcoded in `session_adapter.py` |
| `base_url` | `""` (empty) | Yes | Must be set to 9Router endpoint. Currently hardcoded as `localhost:20128` |
| `api_key` | Not set | Yes | Should reference auth.json or .env |
| `temperature` | Not set | Optional | Currently managed in `session_adapter.py` |
| `max_tokens` | Not set | Optional | -- |
| `streaming` | Not set | Optional | Neither GuinevereBot nor Hermes currently stream |

**Gap:** Entire LLM configuration section is empty. Guinevere hardcodes `llm_config` dict in `session_adapter.py` pointing to 9Router. Migration would move this to `config.yaml` and use `hermes config set` to manage it.

#### Section 3: `memory`

```yaml
memory:
  compression:
    enabled: true
    threshold: 0.5
    target: 0.2
    protect_last: 20
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| `compression.enabled` | `true` | Yes | Context compression is active -- good for long conversations |
| `compression.threshold` | `0.5` (50%) | Evaluate | Triggers compression at 50% context utilization |
| `compression.target` | `0.2` (20%) | Evaluate | Compresses to 20% of original context size |
| `compression.protect_last` | `20` | Evaluate | Protects last 20 messages from compression |
| `backend` | Not set | Critical | Currently using custom PostgreSQL+pgvector via `memory_bridge.py`. Hermes built-in memory is disabled (`skip_memory=True`) |

**Gap:** Memory compression is configured but the backend is not specified. Guinevere uses `skip_memory=True` and a custom `HermesMemoryBridge` with PostgreSQL+pgvector. Migration must either:
- Configure Hermes native memory backend and migrate data, OR
- Keep `skip_memory=True` and continue using the custom bridge, OR
- Implement a Hermes memory plugin that wraps the custom bridge

#### Section 4: `loop`

```yaml
loop:
  enabled: false
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| `enabled` | `false` | Depends on use case | Agent loop (autonomous agent mode) is disabled. Guinevere operates as a Discord bot, not a loop agent |
| `interval` | Not set | No | -- |
| `max_iterations` | Not set | No | -- |

**Status:** Correctly disabled for Guinevere's Discord bot use case. The agent loop is for autonomous operation modes, not request-response chat.

#### Section 5: `safety`

```yaml
safety:
  # safety settings (placeholder)
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| All fields | Placeholder only | Critical | PersonaSafetyPolicy requires: HARD STOP protocol, consent boundary enforcement, Y4 baseline, Y5 ceiling, no Y6, distress protocol, surveillance consent |

**Gap:** Safety section is completely empty. This is the highest-risk gap. Guinevere's PersonaSafetyPolicy (18 sections) defines binding safety constraints that must be enforced at the agent level. Hermes safety settings need investigation to determine if they can enforce:
- HARD STOP interception before any message reaches the LLM
- Consent revocation bypass prevention
- Y4 personality baseline enforcement
- Y5 absolute ceiling (no Y6 escalation)
- Distress detection protocol

If Hermes safety system cannot enforce these, a custom hook or pre-processing layer will be required.

#### Section 6: `budget`

```yaml
budget:
  # budget limits (placeholder)
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| All fields | Placeholder only | Optional | Guinevere has FinOps tracking (`cost & FinOps Model v1.1`) but no hard budget caps |

**Gap:** Low priority. Budget limits are not currently enforced in Guinevere, so Hermes budget tracking would be additive, not a migration dependency.

#### Section 7: `tools`

```yaml
tools:
  # tool configuration (placeholder)
```

| Field | Current Value | Required for Guinevere | Notes |
|-------|--------------|----------------------|-------|
| All fields | Placeholder only | Yes | 12 tools available (from hermes doctor). Must be configured to match Guinevere's operational needs |

**Gap:** Tool configuration is empty. Need to:
- Enable tools used by Guinevere's conversational pipeline
- Disable tools that pose safety risks (e.g., `terminal`, `code_execution` may need sandboxing)
- Ensure `delegation` tool respects the sub-agent constraints from AGENTS.md

#### Section 8: `messaging`

```yaml
messaging:
  # messaging platform config (placeholder)
```

**Gap:** This section should contain the Discord gateway configuration (and potentially WhatsApp/Slack if used). See Report 03 (DISCORD-GATEWAY.md).

#### Section 9: `monitoring`

```yaml
monitoring:
  # observability (placeholder)
```

**Gap:** Guinevere's operational requirements include Prometheus + Grafana observability. Hermes monitoring configuration should be set up to export metrics compatible with the existing stack.

---

## Environment Variable and Secrets Management

### .env File

**Status:** MISSING (confirmed by `hermes doctor`)

Required environment variables for Guinevere:

| Variable | Priority | Source in Current System |
|----------|----------|--------------------------|
| `DISCORD_BOT_TOKEN` | Critical | Discord Developer Portal |
| `OPENAI_API_KEY` | High | auth.json pool |
| `NINEROUTER_API_KEY` | High | 9Router config |
| `DATABASE_URL` | Medium | PostgreSQL connection string |
| `REDIS_URL` | Medium | Redis connection (DB0, DB4) |
| `SURVEILLANCE_KEY` | Critical | SOPS/age encrypted |
| `SOPS_AGE_KEY` | Critical | SOPS/age key file |

**Gap:** Creating `.env` is a prerequisite for Hermes Discord gateway setup. The `DISCORD_BOT_TOKEN` is explicitly listed as missing in `hermes doctor`.

### auth.json Structure

**Location:** `~/.hermes/auth.json`

**Purpose:** OpenAI API key pool for multi-key rotation. Hermes uses this for:
- Provider authentication
- Key rotation across rate limits
- Fallback provider chain

**Guinevere Current State:** Not using Hermes auth layer. 9Router API key is hardcoded or environment-managed.

**Gap:** If Guinevere adopts Hermes secrets management (`hermes secrets` CLI), the auth.json pool would need to include 9Router API keys. The existing SOPS/age encryption for surveillance keys would need to coexist or be replaced.

---

## SOUL.md System

**Location:** `~/.hermes/SOUL.md`

**Purpose:** Agent persona and behavioral definition. This is Hermes' equivalent of Aizanta's System Prompt Master.

**Current State:** Unknown -- needs inspection. Likely contains default Hermes personality definition.

**Needed Customization for Guinevere:**
1. Identity: "Guinevere -- autonomous AI companion & engineering agent system"
2. Operator: Faiz (not generic user)
3. Persona: Y4 baseline (dominant-absolut, protective, consent-aware)
4. HARD STOP protocol definition
5. Consent boundary rules
6. Distress detection triggers
7. Surveillance policy constraints
8. Operator protocol (lanjut, stop, HARD STOP, kasih ruang, etc.)

**Gap:** SOUL.md must be completely rewritten for Guinevere. The current `personality: kawaii` in config.yaml suggests the SOUL.md contains a generic cute-assistant persona, which is incompatible with Guinevere's persona safety requirements.

---

## System Prompt

**Location:** `/home/guinevere/config/hermes/system-prompt.md`

**Purpose:** The base system prompt injected before every LLM call.

**Current State:** Unknown contents -- needs inspection.

**Guinevere Requirements:**
- Persona definition (from Persona Document v3.0)
- Safety constraints (from PersonaSafetyPolicy)
- Operator recognition (Faiz detection)
- HARD STOP immediate response protocol
- Memory recall formatting
- Response constraints (concise, evidence-first, no emoji unless operator requests)

**Gap:** Current conversational_handler.py assembles the system prompt dynamically (step 4 of the 10-step pipeline). Migration would mean the system-prompt.md becomes the canonical base, with dynamic assembly moved to a Hermes hook or eliminated entirely.

---

## Config CLI Commands

### Available Commands

| Command | Syntax | Purpose |
|---------|--------|---------|
| `hermes config show` | No flags | Display full current config |
| `hermes config get KEY` | `--format yaml\|json` | Get specific config value |
| `hermes config set KEY VALUE` | `--section SECTION` | Set config value |
| `hermes config edit` | Opens `$EDITOR` | Interactive config editing |
| `hermes config validate` | Not confirmed | Validate config against schema |

### Config Persistence

Config changes via CLI are written to `config.yaml`. The `hermes config set` command supports dot-notation for nested keys (e.g., `hermes config set llm.model gpt-4`).

---

## Gap Analysis Summary

### Critical Gaps (Block Migration)

| # | Gap | Current State | Required State | Effort |
|---|-----|--------------|----------------|--------|
| 1 | `.env` missing | No environment variables | DISCORD_BOT_TOKEN + API keys | Low |
| 2 | `config.yaml` path mismatch | File exists but Hermes can't find it | Align expected vs actual path | Low |
| 3 | LLM config empty | Hardcoded in session_adapter.py | 9Router model + base_url in config | Low |
| 4 | Safety section empty | PersonaSafetyPolicy enforced via code | Hermes safety settings must be populated | High |
| 5 | SOUL.md not customized | Default `kawaii` persona | Full Guinevere persona definition | High |
| 6 | Memory backend unspecified | Custom PostgreSQL+pgvector bridge | Hermes memory configured or bridge retained | Medium |

### Moderate Gaps

| # | Gap | Resolution |
|---|-----|-----------|
| 7 | Tool configuration empty | Configure enabled/disabled tool set |
| 8 | Messaging section empty | Populate with Discord gateway config (after gateway setup) |
| 9 | Budget section empty | Optional -- set if FinOps integration desired |
| 10 | Monitoring section empty | Add Prometheus/Grafana export config |
| 11 | Agent `personality` field is `kawaii` | Change to custom or set to use SOUL.md/system-prompt.md |
| 12 | No max_turns / idle_timeout | Add equivalents of Redis DB4 20-turn, 2hr-TTL limits |

---

## Config Migration Path

```
Phase A: Fix Blockers
  1. Create .env with DISCORD_BOT_TOKEN (placeholder)
  2. Fix config.yaml path
  3. Set llm.model and llm.base_url via hermes config set

Phase B: Persona Migration
  4. Inspect current SOUL.md and system-prompt.md
  5. Rewrite SOUL.md with Guinevere persona
  6. Rewrite system-prompt.md with PersonaSafetyPolicy constraints
  7. Change agent.personality to custom

Phase C: Safety Configuration
  8. Research Hermes safety settings capabilities
  9. Map PersonaSafetyPolicy rules to Hermes safety config
  10. Implement hooks for rules Hermes safety can't enforce natively

Phase D: Operational Tuning
  11. Configure memory backend (keep custom bridge or migrate)
  12. Enable/disable tools per Guinevere operational needs
  13. Set up monitoring export
  14. Add max_turns and idle_timeout
```

---

## Recommendations

1. **Do NOT change config.yaml until .env exists.** Hermes may fail to start without environment variables.
2. **Inspect SOUL.md and system-prompt.md** before rewriting. Understand Hermes' native persona format to minimize friction.
3. **Consider keeping the custom memory bridge.** PostgreSQL+pgvector is working, migration risk is high, and `skip_memory=True` already keeps Hermes memory out of the way.
4. **Safety section is the highest priority after unblocking.** Without safety config, Hermes will operate with default (potentially `kawaii`) persona, which violates PersonaSafetyPolicy.
5. **Use `hermes config validate`** (if available) after each config change to catch schema errors.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Hermes safety system cannot enforce PersonaSafetyPolicy | Medium | Critical | Custom hook layer as safety shim |
| SOUL.md rewrite changes agent behavior unpredictably | Medium | High | Staged persona testing with Faiz-only channel |
| Config path mismatch causes silent fallback to defaults | Medium | High | Explicit path via `--config` flag or env var |
| Memory migration causes data loss | Low | Critical | Full PostgreSQL backup before any migration attempt |
| auth.json format incompatible with SOPS/age secrets | Medium | Medium | Keep SOPS/age for surveillance keys, use Hermes for LLM keys |
| Multiple config sources cause drift (env vs yaml vs CLI) | Medium | Medium | Single source of truth: config.yaml with .env for secrets only |

---

## Cross-References

- **Report 01 (CLI-CAPABILITIES.md):** `hermes config`, `hermes secrets`, `hermes setup` command details
- **Report 03 (DISCORD-GATEWAY.md):** Gateway config within messaging section
- **Report 04 (DISCORD-MIGRATION-GAP.md):** Config impact on migration strategy
- **PersonaSafetyPolicy:** `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- **AGENTS.md Section 2.1:** Consent-Safety Mandate

---

## Footer

| Field | Value |
|-------|-------|
| Author | Guinevere (Sisyphus-Junior) |
| Review Status | Draft |
| Date | 2026-06-04 |
| Hermes Version | v0.15.2 (2026.5.29.2) |
| Config Path | `/home/guinevere/config/hermes/config.yaml` |
| Evidence Source | `hermes config show`, `hermes doctor`, filesystem inspection |
| Next Review | After SOUL.md and system-prompt.md inspection |