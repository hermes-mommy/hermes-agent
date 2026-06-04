# Research Report: Hermes Agent Shadow Mode & Traffic Splitting Feasibility

**Date**: 2026-06-04  
**Context**: Phase 2 migration requires a 48-hour shadow mode where BOTH the custom Discord bot AND Hermes Agent run simultaneously. Hermes processes messages but responses are discarded. ADR-035 specifies 4 traffic stages: 0% → 10% → 50% → 100%.  
**Scope**: Read-only research on Hermes Agent capabilities and Discord API constraints.

---

## 1. Executive Summary

**Hermes Agent does NOT natively support shadow mode, traffic splitting, or dual-running for the Discord gateway.** 

To achieve the 48-hour shadow mode requirement, **custom implementation is mandatory**. Furthermore, running two Discord bot instances on the same `DISCORD_BOT_TOKEN` is technically possible but **highly discouraged** due to state corruption and duplicate response risks. The recommended approach is to use **two separate bot tokens** (distinct Discord Applications) during the shadow phase.

---

## 2. Hermes Agent Native Capabilities Analysis

### 2.1 Shadow Mode / Dry-Run / Traffic Splitting
- **Finding**: No native support.
- **Evidence**: The Hermes CLI `--dry-run` flags are strictly limited to infrastructure tasks (e.g., `hermes curator run --dry-run` for skill mutation previews, `hermes claw migrate --dry-run` for config migration). There is no `--shadow`, `--dry-run`, or `--passthrough` flag for the `hermes gateway` command.
- **Note on "Passthrough"**: The term "passthrough" in the Hermes codebase exclusively refers to *environment variable passthrough* for sandboxed tool execution (`tools/env_passthrough.py`), not message passthrough or shadow routing.

### 2.2 Configuring Hermes to Receive but NOT Send Responses
- **Finding**: No native "silent mode" or "drop response" toggle exists in the Discord adapter.
- **Current Behavior**: Hermes processes messages through a strict pipeline: authorization → mention check → session lookup → transcript loading → agent execution → response delivery. If a message passes the mention check, it *will* attempt to deliver a response.
- **Partial Workaround**: Setting `DISCORD_IGNORED_CHANNELS="*"` or ensuring `DISCORD_REQUIRE_MENTION=true` (and never mentioning the bot) will prevent responses. However, this causes the gateway to **bail out early**, meaning the agent does *not* process the message, defeating the purpose of shadow testing agent logic and memory updates.

### 2.3 Webhook / Event Hooks for Message Interception
- **Finding**: Not supported.
- **Evidence**: The Hermes gateway is a monolithic process (`plugins/platforms/discord/adapter.py`). It does not expose outbound webhook hooks, middleware, or event listeners that would allow intercepting and dropping the final response before it hits the Discord API.

### 2.4 Message Queue / Buffer Mode
- **Finding**: Not designed for shadow operation.
- **Evidence**: Hermes handles concurrency via session isolation (`group_sessions_per_user`), but it processes messages synchronously/asynchronously per session. There is no "buffer mode" or deferred execution queue that could be leveraged for shadow logging without immediate response.

---

## 3. Critical Question: Can Two Discord Bots Share the Same Token?

**Short Answer**: Yes, technically. **Should you do it for shadow mode? Absolutely not.**

### 3.1 Discord API Behavior
- The Discord Gateway API explicitly allows multiple concurrent connections (sessions) using the same bot token. All connected instances will receive the same `MESSAGE_CREATE` events.

### 3.2 Why This Fails for Shadow Mode
1. **Duplicate Responses**: If both the legacy bot and Hermes are configured to respond to the same triggers, both will reply, causing immediate user-facing duplication.
2. **State & Memory Corruption**: Hermes maintains session state and memory (e.g., `~/.hermes/memories/`, SQLite sessions). If two Hermes instances (or a legacy bot and Hermes) process the same message concurrently, they will race to update the same session state, leading to corrupted transcripts, overwritten memory, and unpredictable agent behavior.
3. **Resource Waste**: You incur the LLM and compute cost twice for the exact same workload.
4. **Rate Limiting**: Multiple connections increase the risk of hitting Discord's global rate limits or session start limits (max 1000 token logins per 24 hours).

### 3.3 Industry Best Practice
- **Use Separate Tokens**: Create a second Discord Application in the Developer Portal for the Hermes Agent shadow instance. This guarantees complete isolation of gateway events, session state, and memory.
- **Identity Masking (Optional)**: If the shadow bot must appear as the same "identity" to users, use Discord Webhooks to send messages, though this still requires separate bot tokens for the underlying gateway connections.

---

## 4. Required Custom Implementation for Phase 2

Since native support is absent, the following custom implementation is required to satisfy ADR-035 traffic stages (0% → 10% → 50% → 100%):

### Option A: Custom Gateway Wrapper (Recommended)
Create a lightweight Python wrapper around `hermes gateway` that intercepts outbound messages.
1. **Fork/Modify Adapter**: Modify `plugins/platforms/discord/adapter.py` in a local Hermes fork.
2. **Add Shadow Flag**: Introduce a custom env var `HERMES_SHADOW_MODE=true`.
3. **Intercept Response**: In the `_handle_message` or response delivery function, if `HERMES_SHADOW_MODE=true`, log the intended response to a file/observability tool (e.g., Prometheus/Grafana) and `return` without calling `channel.send()`.
4. **Traffic Splitting**: Implement a simple hash-based or random-based router in the wrapper: `if random.random() < shadow_percentage: enable_shadow_mode()`.

### Option B: Reverse Proxy / Event Interceptor
1. Run a custom Discord.py bot that acts as the primary gateway.
2. This bot receives all `MESSAGE_CREATE` events.
3. It forwards a copy of the payload to the Hermes Agent via a custom local HTTP endpoint (requiring a custom Hermes plugin to accept HTTP webhooks, which also requires development).
4. The primary bot handles all actual Discord responses.

### Option C: Separate Token + Observability (Safest)
1. Deploy Hermes with a **new, separate Discord bot token**.
2. Configure Hermes to only listen to a specific `DISCORD_FREE_RESPONSE_CHANNELS` or require a specific `@mention` (e.g., `@HermesShadow`).
3. Route 10% of user traffic (via your custom legacy bot) to explicitly mention `@HermesShadow`.
4. Monitor Hermes' memory updates and LLM costs via existing observability tools without risking state corruption of the primary bot.

---

## 5. Conclusion & Recommendation

**Do not attempt to run two Hermes instances or a legacy bot + Hermes on the same `DISCORD_BOT_TOKEN`.** The risk of session state corruption and memory race conditions is unacceptably high.

**Recommended Path**: 
1. Provision a **separate Discord Application and token** for the Hermes shadow instance.
2. Implement **Option A** (local fork of Hermes Discord adapter with a `HERMES_SHADOW_MODE` env var that logs but suppresses `channel.send()`).
3. Use your legacy bot to forward a percentage of messages (per ADR-035 stages) to the shadow bot's dedicated channel or via explicit mention, ensuring clean isolation and accurate shadow metrics.

---

## 6. References

- [Hermes Agent Discord Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord)
- [Hermes Agent CLI Commands Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)
- [Hermes Agent Discord Adapter Source](https://github.com/NousResearch/hermes-agent/blob/main/plugins/platforms/discord/adapter.py)
- [Discord API Multiple Sessions Discussion](https://github.com/serenity-rs/serenity/issues/1054)
- [StackOverflow: Simultaneously running separate programs using the same token](https://stackoverflow.com/questions/69796271/simultaneously-running-separate-programs-using-the-same-token)
