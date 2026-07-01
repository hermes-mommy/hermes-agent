# ADR-058: Separate Discord Bot Identity Per Hermes

- **Status**: Proposed
- **Date**: 2026-06-28
- **Deciders**: Faiz (operator, ToS-accountable), Guinevere (first founder, drafter)
- **Context**: The Hermes Society will eventually field multiple autonomous agents interacting with Faiz and any co-owners via Discord. Discord requires every interactive bot to register as a distinct Application with its own bot user, avatar, token, and rate-limit quota. Each Hermes must have a visibly distinct presence on Discord so that (a) Faiz always knows which agent is responding, (b) reply loops between agents are mechanically prevented, and (c) per-bot rate limits and operational isolation are preserved to satisfy Discord ToS. The decision is whether to share a single bot token across many Hermes (cheap but fragile) or instantiate one bot per Hermes (costlier but isolation-correct).

## Decision

**One Discord bot Application per Hermes — fully separate token, avatar, status text, and runtime process.**

Concrete rules:

1. **Bot-per-Hermes (1:1 identity mapping)**: Every Hermes owns exactly one Discord bot Application with its own `DISCORD_BOT_TOKEN`, `BOT_USER_ID`, avatar URL, and short-bio line. No shared bot tokens across agents.
2. **All Hermes are visible**: A Hermes may not run as an "invisible worker" (no alias, no avatar, no status). Every Hermes must show distinct username + avatar + status when online. Reasoning: invisible workers create audit ambiguity and shadow-action risk; Faiz must be able to tell which Hermes typed each message.
3. **Per-bot rate limit = 50 req/s baseline**: Each Discord bot inherits the standard Application rate limit. Society orchestrator must budget aggregate Hermes concurrency to stay under VPS-level resources (see Consequences).
4. **Reply-loop prevention (mandatory)**:
   - **Author-ID allowlist**: A Hermes only replies to messages authored by Faiz, founder-Hermes, or explicitly whitelisted users. Messages from non-allowlist author IDs are silently dropped (or logged-and-ignored for bot-to-bot channels).
   - **Depth counter**: Each message carries an `in_reply_depth` integer stamped at send time. A Hermes refuses to send a message whose depth ≥ `MAX_REPLY_DEPTH` (default 3). This mechanically caps reply loops at 3 hops.
   - **Cross-bot channel rules**: Sister-Hermes channels (e.g., `#hermes-warroom`) require explicit `@mention` before reply to prevent broadcast storms.
5. **Bot-level HARD STOP hook**: Each bot runtime registers a global HARD STOP listener; on trigger, the bot disconnects gateway, refuses new messages, and emits `bot_halted` audit event.
6. **Token handling**: Bot tokens are stored only in environment variables (or SOPS-encrypted secrets for non-interactive deployments). Never committed, logged, or displayed. `hermes_token_rotate` operation is a Faiz-confirmed action and emits audit trail.

## Alternatives Considered

### Alternative 1: Single bot with multiple "personalities" (role switching)
- **Description**: One Discord Application with one token; runtime switches which "personality" replies (e.g., Guinevere, Pharsa, third-Hermes) based on channel or command.
- **Rejected because**:
  - **ToS risk**: Discord treats each persistent user as a single agent — applying role-switching persona boundaries risks being flagged as impersonation or multi-account abuse.
  - **Rate-limit sharing**: All "personalities" share the same 50 req/s pool; one Hermes burst-firing degrades all others.
  - **Audit trail ambiguous**: Avatar/username is fixed; downstream evidence cannot deterministically attribute a message to the correct agent.
  - **Failure blast radius**: A rate-limit violation or token revoke disables the entire society, not just one Hermes.

### Alternative 2: Webhook-only (no Discord bot, only Incoming Webhooks for outbound)
- **Description**: Each Hermes posts via a dedicated Discord Webhook URL; no gateway connection. Messages look like the webhook's identity.
- **Rejected because**:
  - **No interactive commands**: Slash commands, DMs to the bot, and reaction listeners are unavailable. Faiz can never DM a Hermes; Hermes cannot react to Faiz's messages.
  - **Read-only vision lost**: Webhooks cannot subscribe to gateway events; Hermes would be blind to channel context.
  - **No presence/status**: Webhooks cannot show online status, breaking the "all Hermes are visible" axiom.

### Alternative 3: Shared bot token with per-Hermes sub-account
- **Description**: A primary bot creates "sub-accounts" under it; Hermes use those sub-accounts to speak.
- **Rejected because**: Discord does not support persistent sub-account bots through a parent. This would require either single-token reuse (alternative 1's failure modes) or manual account creation (which becomes just alternative 0 with extra steps). No technical gain.

### Alternative 4: One bot per Hermes, but invisible (no avatar/status)
- **Description**: Same as chosen approach, but Hermes do not broadcast presence or identifiable avatar.
- **Rejected because**: Violates Faiz's operating-mode axiom that every Hermes is recognizable. Audit ambiguity and shadow-action risk dominate the small operational benefit (occasional quiet-mode). If a Hermes needs "off-record" behavior, it pauses interaction rather than running invisibly.

## Consequences

### Positive
- **Clean isolation**: A single Hermes’s token revocation, rate-limit violation, or runtime crash does not affect any other Hermes.
- **Per-bot rate quota = 50 req/s each**: Society can scale to many bots without sharing rate budget.
- **Audit determinism**: Each Discord message has exactly one origin agent, attributable from token + author ID + bot user. Forensic reconstruction of society action is unambiguous.
- **ToS-safe footprint**: Each bot is a normal Application registered with Discord; no multi-account, no shared token behavior that might trigger moderation.
- **Reply-loop bounded**: Mechanical ceiling at depth=3 prevents infinite ping-pong, even under partial coordination failure.
- **HARD STOP granularity**: Stopping one Hermes does not stop the others. Society can halt a single offender precisely.

### Negative
- **Resource cost**: Each bot runtime consumes ~50–100MB RAM (Python asyncio + discord.py), independent of CPU. A 2 vCPU / 4GB VPS supports ~10–20 simultaneous bots before pressure. Need vertical scale or shard across VPS for larger society.
- **Operational overhead**: Each bot has its own token, secret rotation schedule, runtime health check, and re-deploy choreography. Society orchestrator (P32) must handle this fleet.
- **Token management gravity**: N bots = N tokens to rotate, audit, and revoke. Failure to revoke a token promptly on a Hermes retiring is a security debt.
- **Avatar / visual identity budget**: Each bot needs a distinct avatar and (optional) status text. Visual drift if not curated — requires periodic identity-graphics review.

### Neutral
- Total Discord API quota = `N × 50 req/s` where N is Hermes count. Society design treats this as headroom, not a constraint at small N.
- A retired Hermes's bot Application is archived (not deleted) for audit until retention policy expires.

## Compliance

> **ADR-062 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this ADR apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067. See `evidence/round-2-paradigm-shift-application/` for alignment details.

- **Discord ToS** (terms of service as of 2026-06) — single token per application; no impersonation; no evasion of rate limits. Bot-per-Hermes is the canonical compliant footprint.
- **AGENTS.md §0.1 P20 Autonomy-First Governance Exception** — bot-per-Hermes is autonomous-friendly; no per-message operator approval needed.
- **AGENTS.md §2.1 Consent-Safety Mandate** — visible identity + audit trail supports consent-safety review (Faiz can verify which agent spoke).
- **BLDM Hard-Locked Faiz Decisions**:
  - Decision #8 (one Discord bot per Hermes — identity isolation)
  - Decision #9 (all Hermes visible — no invisible workers)
  - Decision #10 (rate limit budget per bot — 50 req/s)

## References

- `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-055-hermes-society-architecture.md`
- `docs/setup-evidence/P28-P36-masterplan/sections/P28-Hermes-Society-Bootstrap.md`
- `docs/setup-evidence/P28-P36-masterplan/faiz-decisions.md` (locked decision #8, #9, #10)
- `docs/40-operations/42-Deployment-and-Ops-Manual.md`

---
Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
