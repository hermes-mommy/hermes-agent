# P25: Claude Code & OpenCode Endpoint Wiring to 9Router

> **Document:** p25-claudecode-opencode-endpoint-wiring.md
> **Phase:** P25 — 9Router VPS Migration (Client-Side Wiring)
> **Date:** 2026-06-25
> **Status:** RESEARCH / PLANNING
> **Author:** fazulfim

---

## 1. Executive Summary

Claude Code and OpenCode are the **only two consumers** of the P25 9Router. Both currently connect to a local 9Router instance at `http://localhost:20128/v1` via the `OPENAI_BASE_URL` environment variable. The migration to the VPS 9Router requires exactly **one change per tool**: updating that environment variable to point at the VPS Tailscale address. No code changes, no config file edits, no model renames, no API format changes.

Hermes is **not** a consumer of the P25 9Router and is completely unaffected.

The migration is reversible in under one second by reverting the single environment variable.

---

## 2. Current Connection Architecture (Local 9Router)

```
┌──────────────┐         ┌──────────────────┐
│ Claude Code  │────────▶│                  │
│              │  HTTP    │  9Router (local) │
│  port 20128  │◀────────│  localhost:20128  │
└──────────────┘         │                  │
                         │  data.sqlite     │
┌──────────────┐         │  24 models       │
│  OpenCode    │────────▶│  REQUIRE_API_KEY │
│              │  HTTP    │    = false       │
│  port 20128  │◀────────│                  │
└──────────────┘         └──────────────────┘
```

**Connection details:**

| Property | Value |
|---|---|
| Endpoint URL | `http://localhost:20128/v1` |
| Environment variable | `OPENAI_BASE_URL` |
| Authentication | None required (`REQUIRE_API_KEY=false`) |
| API protocol | OpenAI-compatible |
| Streaming | SSE (Server-Sent Events) |
| Latency | < 1 ms (localhost loopback) |

**Current environment configuration (both tools identical):**

```bash
# Claude Code
OPENAI_BASE_URL=http://localhost:20128/v1

# OpenCode
OPENAI_BASE_URL=http://localhost:20128/v1
```

No API key is set because the local 9Router runs with `REQUIRE_API_KEY=false`.

---

## 3. New Connection Architecture (VPS 9Router)

```
┌──────────────┐         ┌────────────────────┐         ┌──────────────────┐
│ Claude Code  │────────▶│    Tailscale        │────────▶│                  │
│              │  HTTP    │    WireGuard        │  HTTP    │  9Router (VPS)   │
│              │◀────────│    tunnel           │◀────────│  <tailscale-ip>  │
└──────────────┘         │    ~5-20ms          │         │  :20128          │
                         └────────────────────┘         │                  │
┌──────────────┐                                        │  data.sqlite     │
│  OpenCode    │────────▶ (same tunnel path) ──────────▶│  24 models       │
│              │◀────────                              │  REQUIRE_API_KEY │
└──────────────┘                                        │    = false       │
                                                        └──────────────────┘
```

**Connection details after migration:**

| Property | Value |
|---|---|
| Endpoint URL | `http://<tailscale-ip>:20128/v1` or `http://<magic-dns-name>:20128/v1` |
| Environment variable | `OPENAI_BASE_URL` (same variable, new value) |
| Authentication | None required (Tailscale network auth instead) |
| API protocol | OpenAI-compatible (unchanged) |
| Streaming | SSE (unchanged) |
| Latency | ~5-20 ms additional (Tailscale WireGuard overhead) |

**New environment configuration:**

```bash
# Claude Code — by Tailscale IP
OPENAI_BASE_URL=http://<new-vps-tailscale-ip>:20128/v1

# Claude Code — by MagicDNS (preferred, human-readable)
OPENAI_BASE_URL=http://p25-9router.tailnet-name.ts.net:20128/v1

# OpenCode — identical
OPENAI_BASE_URL=http://<new-vps-tailscale-ip>:20128/v1
# or
OPENAI_BASE_URL=http://p25-9router.tailnet-name.ts.net:20128/v1
```

No API key is set. Network-level security is provided by Tailscale's WireGuard encryption rather than by application-level API keys.

---

## 4. Claude Code Configuration

### Current (Local 9Router)

```bash
export OPENAI_BASE_URL=http://localhost:20128/v1
# No API key
```

- Reads `OPENAI_BASE_URL` from environment at startup
- Models specified via provider prefix: `openai/gpt-5.5`, `ds/deepseek-v4-flash`, `cx/...`
- Uses OpenAI-compatible chat completions format
- Streams responses via SSE

### New (VPS 9Router)

```bash
export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1
# No API key
```

- **Exactly one change**: the hostname/port in `OPENAI_BASE_URL`
- Everything else is identical: model names, provider prefixes, API format, streaming

### Verification Steps for Claude Code

```bash
# 1. Verify VPS 9Router health from local machine
curl http://<tailscale-ip>:20128/api/health
# Expected: {"ok":true}

# 2. Verify model list matches local
curl http://<tailscale-ip>:20128/v1/models | jq '.data | length'
# Expected: 24 (or same count as local 9Router)

# 3. Test a non-streaming chat completion
curl http://<tailscale-ip>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"Say hello"}],"stream":false}'
# Expected: Valid JSON response with model output

# 4. Set the env var and launch Claude Code
export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1
# Launch Claude Code and test a simple prompt
```

---

## 5. OpenCode Configuration

### Current (Local 9Router)

```bash
export OPENAI_BASE_URL=http://localhost:20128/v1
# No API key
```

- Reads `OPENAI_BASE_URL` from environment at startup
- Models specified via provider prefix (same format as Claude Code)
- Uses OpenAI-compatible chat completions format
- Streams responses via SSE

### New (VPS 9Router)

```bash
export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1
# No API key
```

- **Exactly one change**: the hostname/port in `OPENAI_BASE_URL`
- Everything else is identical: model names, provider prefixes, API format, streaming
- OpenCode uses the same `OPENAI_BASE_URL` mechanism as Claude Code

### Verification Steps for OpenCode

```bash
# 1. Set the env var
export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1

# 2. Launch OpenCode and test a coding task
# Verify it connects to the VPS 9Router (check 9Router logs on VPS)

# 3. Test model resolution
# Confirm that OpenCode's model selection still resolves through the same
# provider-prefixed combos (orchestrator, gpt, subagent, tester, etc.)
```

---

## 6. API Surface Used

Claude Code and OpenCode use only **three endpoints** on the 9Router. The full 9Router API surface (dashboard, embeddings, images, audio, etc.) is unused by these clients.

### Endpoints in Use

| Endpoint | Method | Purpose | Streaming | Used By |
|---|---|---|---|---|
| `/v1/models` | GET | Model discovery — lists available models | No | Claude Code, OpenCode |
| `/v1/chat/completions` | POST | Chat completions — the core LLM endpoint | Yes (SSE) and No | Claude Code, OpenCode |
| `/api/health` | GET | Health check — returns `{"ok":true}` | No | Manual verification, monitoring |

### Endpoints NOT Used

The following 9Router capabilities exist but are **not consumed** by Claude Code or OpenCode:

- `/api/dashboard` (and related dashboard endpoints)
- `/v1/embeddings`
- `/v1/images/generations`
- `/v1/audio/transcriptions`
- `/v1/audio/speech`
- Any other non-chat endpoints

This means the migration surface is minimal: only the three endpoints above need to work correctly on the VPS 9Router for both clients to function.

---

## 7. What Changes vs What Stays the Same

### What CHANGES

| Item | Before | After |
|---|---|---|
| `OPENAI_BASE_URL` value | `http://localhost:20128/v1` | `http://<tailscale-ip>:20128/v1` |
| Network path | localhost loopback | Tailscale WireGuard tunnel |
| Additional latency | < 1 ms | ~5-20 ms added |
| 9Router host machine | Local workstation | VPS (Ubuntu 24.04) |
| Network dependency | None (localhost always available) | Tailscale must be up |

### What STAYS THE SAME

| Item | Status | Notes |
|---|---|---|
| Model names | Unchanged | Same provider prefixes: `cx/`, `ds/`, `openai/`, etc. |
| Model routing | Unchanged | Same combos: orchestrator, gpt, subagent, tester, etc. |
| Model count | Unchanged | 24 models (copied from data.sqlite) |
| API format | Unchanged | OpenAI-compatible `/v1/chat/completions` |
| Streaming | Unchanged | SSE streaming |
| Authentication | Unchanged | No API key required |
| Provider prefixes | Unchanged | `cx/`, `ds/`, `openai/`, etc. |
| Environment variable name | Unchanged | `OPENAI_BASE_URL` |
| Number of config changes | One | Just the URL value |
| Code changes needed | None | Zero |
| Config file changes needed | None | Zero |

---

## 8. Endpoint Switch Procedure

### Step-by-Step: Migrate to VPS 9Router

**Prerequisites:**
- VPS 9Router is running and healthy
- Tailscale is connected on the local workstation
- The VPS Tailscale IP or MagicDNS name is known

**Procedure:**

```bash
# Step 1: Verify VPS 9Router is reachable and healthy
curl http://<tailscale-ip>:20128/api/health
# Expected: {"ok":true}

# Step 2: Verify model count matches expectations
curl http://<tailscale-ip>:20128/v1/models | jq '.data | length'
# Expected: 24 (same as local 9Router)

# Step 3: Verify a chat completion works
curl http://<tailscale-ip>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"Say hello"}],"stream":false}'
# Expected: Valid JSON response with model output

# Step 4: Switch Claude Code
export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1

# Step 5: Switch OpenCode
export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1

# Step 6: Launch Claude Code, test a prompt
# Confirm it works as expected

# Step 7: Launch OpenCode, test a prompt
# Confirm it works as expected

# Step 8: (Optional) Persist the change in shell profile
echo 'export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1' >> ~/.bashrc
# or ~/.zshrc, depending on shell
```

**Time estimate:** < 5 minutes total (including verification).

**Downtime:** Zero. The switch is done by changing an environment variable; there is no service restart, no process to stop, no port to free.

---

## 9. Rollback Procedure

Rollback to the local 9Router is instantaneous.

```bash
# Rollback: switch back to local 9Router
export OPENAI_BASE_URL=http://localhost:20128/v1
```

**That's it.** One command. Under one second.

| Rollback property | Value |
|---|---|
| Commands needed | 1 |
| Time to execute | < 1 second |
| Service restart needed | No |
| Data loss risk | None |
| Steps to re-try migration later | Same as Section 8 |

If the change was persisted to `~/.bashrc` or `~/.zshrc`, also remove or comment out the line:

```bash
# Edit ~/.bashrc or ~/.zshrc and remove:
# export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1
```

---

## 10. Multiple Endpoint Management

The operator may want to switch between local and VPS 9Router for testing, debugging, or rollback. Here are recommended patterns.

### Shell Aliases

```bash
# Add to ~/.bashrc or ~/.zshrc
alias use-local-9router='export OPENAI_BASE_URL=http://localhost:20128/v1'
alias use-vps-9router='export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1'
```

**Usage:**

```bash
# Switch to local
use-local-9router

# Switch to VPS
use-vps-9router

# Verify which is active
echo $OPENAI_BASE_URL
```

### Current Endpoint Check

```bash
# Quick check: which 9Router am I pointed at?
echo $OPENAI_BASE_URL
```

### Per-Session Switching

Because `OPENAI_BASE_URL` is an environment variable, different terminal sessions can point at different 9Router instances simultaneously:

- Terminal A: `use-local-9router` (for local work)
- Terminal B: `use-vps-9router` (for VPS testing)

This is useful during the migration validation phase.

### Persistent Configuration

To make the VPS 9Router the default after migration:

```bash
echo 'export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1' >> ~/.bashrc
source ~/.bashrc
```

To revert persistence:

```bash
# Remove or comment out the line from ~/.bashrc
# Then:
source ~/.bashrc
```

---

## 11. Latency Impact Analysis

### Latency Comparison

| Path | Latency | Notes |
|---|---|---|
| Local 9Router (localhost) | < 1 ms | Loopback, no network |
| VPS 9Router (Tailscale) | ~5-20 ms additional | WireGuard tunnel overhead |
| LLM response time | 10-60 seconds | The actual bottleneck |
| 9Router processing overhead | ~10-50 ms | Regardless of 9Router location |

### Impact Assessment

The additional ~5-20 ms of Tailscale latency is **negligible** compared to the LLM response time of 10-60 seconds. The percentage overhead:

- Worst case: 20 ms / 10,000 ms = **0.2%** overhead
- Typical case: 10 ms / 30,000 ms = **0.03%** overhead

This is well within acceptable bounds. Users will not perceive any difference in response times.

### Streaming Considerations

With SSE streaming, the additional latency affects:
- **Time to first token (TTFT):** +5-20 ms — imperceptible
- **Inter-token latency:** +5-20 ms per chunk — imperceptible
- **Total stream duration:** Unchanged (dominated by LLM generation time)

**Conclusion:** The latency impact of moving from local to VPS 9Router via Tailscale is effectively zero from the user's perspective.

---

## 12. Connection Reliability & Fallback

### Tailscale Reliability

Tailscale uses WireGuard under the hood and is generally reliable. However, brief interruptions can occur due to:
- Tailscale daemon restarts
- Network interface changes (e.g., Wi-Fi to Ethernet)
- Tailscale coordination server issues (rare)
- Local network disruptions

### Impact of Tailscale Downtime

If Tailscale is down:
- Claude Code and OpenCode **cannot** reach the VPS 9Router
- The environment variable `OPENAI_BASE_URL` points at an unreachable host
- Requests will timeout or fail with connection errors

### Fallback Strategy

```bash
# If VPS 9Router is unreachable, switch to local:
export OPENAI_BASE_URL=http://localhost:20128/v1
```

**Recommendation:** Keep the local 9Router installed as a permanent fallback. This ensures coding work can continue even if:
- Tailscale is down
- The VPS is unreachable
- The VPS 9Router is being restarted or updated

### Monitoring

A simple health check can detect connectivity issues:

```bash
# Quick connectivity test
curl -s --max-time 5 http://<tailscale-ip>:20128/api/health || echo "VPS 9Router unreachable — consider falling back to local"
```

---

## 13. Hermes Non-Impact

**Hermes is NOT a consumer of the P25 9Router.**

Hermes runs on the VPS and connects to its own local VPS 9Router:

```
Hermes (on VPS) → http://localhost:20128/v1 → VPS 9Router (on VPS)
```

This is a completely separate connection from the P25 coding traffic:

```
Claude Code (local) → http://<tailscale-ip>:20128/v1 → VPS 9Router (on VPS)
OpenCode (local)    → http://<tailscale-ip>:20128/v1 → VPS 9Router (on VPS)
```

| Consumer | 9Router Instance | Connection | Affected by P25? |
|---|---|---|---|
| Hermes | VPS 9Router (localhost on VPS) | `http://localhost:20128/v1` | **No** |
| Claude Code | P25 9Router (VPS via Tailscale) | `http://<tailscale-ip>:20128/v1` | **Yes** |
| OpenCode | P25 9Router (VPS via Tailscale) | `http://<tailscale-ip>:20128/v1` | **Yes** |

Hermes uses its `base_url: http://localhost:20128/v1` configuration, which resolves to the VPS's own loopback. This is unaffected by any changes to Tailscale or the P25 migration.

**No Hermes configuration changes are needed. No Hermes testing is required for P25.**

---

## 14. Verification Checklist

### Pre-Migration (Verify VPS 9Router is ready)

- [ ] VPS 9Router is running on the VPS
- [ ] `data.sqlite` has been copied to VPS with all 24 models
- [ ] `REQUIRE_API_KEY=false` is set on the VPS 9Router
- [ ] Tailscale is connected on the local workstation
- [ ] VPS Tailscale IP or MagicDNS name is known

### Connectivity Verification

```bash
# [ ] Health check passes
curl http://<tailscale-ip>:20128/api/health
# → {"ok":true}

# [ ] Model count is correct
curl http://<tailscale-ip>:20128/v1/models | jq '.data | length'
# → 24

# [ ] Chat completion works (non-streaming)
curl http://<tailscale-ip>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"Say hello"}],"stream":false}'
# → Valid JSON response

# [ ] Chat completion works (streaming)
curl http://<tailscale-ip>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"Say hello"}],"stream":true}'
# → SSE stream of tokens
```

### Client Verification

- [ ] Set `OPENAI_BASE_URL` to VPS 9Router
- [ ] Launch Claude Code — test a coding prompt
- [ ] Launch OpenCode — test a coding prompt
- [ ] Verify model selection works (provider prefixes resolve correctly)
- [ ] Verify streaming works (responses arrive incrementally)

### Rollback Verification

- [ ] Set `OPENAI_BASE_URL` back to `http://localhost:20128/v1`
- [ ] Confirm Claude Code works with local 9Router
- [ ] Confirm OpenCode works with local 9Router

### Post-Migration

- [ ] Update `~/.bashrc` or `~/.zshrc` with the new VPS URL
- [ ] Set up shell aliases for easy switching
- [ ] Document the VPS Tailscale IP / MagicDNS name for future reference
- [ ] Confirm local 9Router remains installed as fallback

---

## 15. Footer

| Field | Value |
|---|---|
| Document | p25-claudecode-opencode-endpoint-wiring.md |
| Phase | P25 — 9Router VPS Migration |
| Scope | Client-side endpoint wiring only (Claude Code + OpenCode) |
| Consumers affected | 2 (Claude Code, OpenCode) |
| Config changes needed | 1 environment variable per tool |
| Code changes needed | 0 |
| Rollback time | < 1 second |
| Hermes affected | No |
| Downtime | Zero |
