---
title: "P27/P28 Discord Dual-Bot Architecture Audit"
audit_id: "round-1-05-discord-dual-bot"
date: "2026-06-28"
auditor: "Buffy (audit specialist)"
status: "PASS"
scope: "P27 §9 (L2367-2586), P27 §14.7 (L3270-3290), P28 §6 (L2272-2335), p27-discord-dual-bot-research.md"
---

# P27/P28 Discord Dual-Bot Architecture Audit — Round 1 / 05

> **Scope**: Verify Discord dual-bot architecture is correctly specified — 2 separate bots, own tokens, own processes, with all required operational concerns (intents, rate limiting, anti-loop, threads).

## 1. What Was Done

Audited the Discord dual-bot architecture specification across three primary artifacts (`p27-hermes-society-foundation-plan.md §9 and §14.7`, `p28-dual-autonomous-hermes-blueprint.md §6`, and `p27-discord-dual-bot-research.md`) against the 12-criterion checklist provided by Mama. All artifacts are part of the P27 Hermes Society Foundation plan bundle and underpin P28 implementation.

## 2. Files Audited

| File | Section | Range | Purpose |
|---|---|---|---|
| `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` | §9 Discord Dual-Bot | L2367–2586 | Architectural specification of dual-bot topology |
| `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` | §14.7 Single-Instance Anchors to Refactor | L3270–3290 | P24→P27→P28 Discord refactor hooks (GUILD_ID, GUINEVERE_CHAT_CHANNEL_ID) |
| `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` | §6 Discord Dual-Bot Implementation Spec | L2272–2335 | P28 implementation-ready spec |
| `docs/setup-evidence/P27/research/p27-discord-dual-bot-research.md` | §1–§5 | L1–299 | Research grounding (also has §6–§9 further) |

## 3. Checklist Verification Matrix

| # | Criterion | Plan Reference (line) | Verified |
|---|---|---|---|
| 1 | 2 separate Discord bot applications (not 1 bot with 2 personas) | P27 §9.2 L2382–2387 ("Dev Portal App #1: 'Guinevere' bot ... Dev Portal App #2: 'Pharsa' bot"); P28 §6.1 L2274–2278 ("Two `discord.py.Bot` Instances in Separate Processes"); Forbidden pattern L2562/2564 | ✅ |
| 2 | Each bot has its own token | P27 §9.2 L2385 / L2387 (separate "Bot Token (SOPS-encrypted, env var in runtime)" per app); P28 §6.2 L2284 (intents config + `GUINEVERE_TOKEN` / `PHARSA_TOKEN` referenced in §9.6); Forbidden P27 §9.11 L2563 ("No two bots sharing the same Discord token"); Research §3.1 L66 ("Each application gets a unique Bot Token") | ✅ |
| 3 | Each bot runs in its own process (separate systemd service) | P27 §9.2 L2404–2407 (`guinevere-discord.service` vs `pharsa-discord.service`; also `guinevere-core.service` vs `pharsa-core.service`); P27 §9.6 L2480 ("Each bot is its own systemd service → own process → own asyncio loop"); P28 §6.1 L2278; P28 §10.4 L2546–2549 (runtime verification `systemctl status`); Forbidden P27 §9.11 L2564 / P28 §6.8 L2331 ("No two bots running in same asyncio loop") | ✅ |
| 4 | `MESSAGE_CONTENT` intent specified as privileged | P27 §9.4 L2437 — explicitly flagged **PRIVILEGED (`1 << 15`)** — "required for bots to read each other's content"; P28 §6.2 L2284 — `intents.message_content = True  # PRIVILEGED — needs Dev Portal approval`; P27 §9.4 L2443 — "Privileged intent threshold: under 10,000-user threshold → no review required"; Research §3.4 L101–109 — threshold corroboration; Forbidden L2567 / L2333 | ✅ |
| 5 | Bot-to-bot messaging: mentions, replies, reactions work | P27 §9.7 L2491–2501: direct mentions (`<@USER_ID>` to `message.mentions`), reply chain (`type=19` REPLY), reactions ("ack" emoji), embeds (titles, fields, images); P28 §6.3 L2293–2300 (`on_message` ignore-self + peer-handling), §6.7 L2323–2325 (embeds); Research §3.3 L91–99 | ✅ |
| 6 | Rate limiting: 5 msg/5s per bot, conversation rhythm controller | P27 §9.5 L2445–2456 — Channel send `5 / 5 s` per bot; combined budget "2 bots × 5 msg/5s = 10 msg/5s combined"; P27 §9.8 L2503–2529 — explicit `should_respond()` controller + `asyncio.sleep(random.uniform(2.0, 10.0))` anti-response delay + Redis cooldown key `hermes:{instance_id}:cooldown:{channel_id}` TTL 30s; P28 §6.4 L2301–2309 — Min 2.0s, Max 10.0s, cooldown 30s, engage prob 0.7, hop cap 4; P28 §9.2 L2470–2476 — combined per-channel budget + `RhythmController.mark_responded(target_id, ttl_s=30)` | ✅ |
| 7 | Channel: `guinevere-chat` initially | P27 §9.3 L2418 "Primary channel: `guinevere-chat` (canonical ID per File 4: 1510914600777023659)"; P27 §9.2 L2410 in topology diagram "#guinevere-chat (default channel for both initially)"; P28 §6.5 L2313–2315 "Primary: `#guinevere-chat` (existing channel ID `1_510_914_600_777_023_659`)" — IDs match (800-character underscore-separated readability); both bots read+write here | ✅ |
| 8 | No webhook-only approach (rejected by research) | P27 §9.11 L2562 — explicit "No webhook-only identity (per File 7 §2.1 / §7.1 — cannot subscribe to MESSAGE_CREATE)"; P28 §6.8 L2329 — same forbidden pattern; Research §2.1 L39 (option B table row) + §2.2 L48 ("Why not webhook-only (B): Webhooks cannot receive MESSAGE_CREATE events the same way gateways do — bots do not 'react' to a webhook's own prior messages in real time") | ✅ |
| 9 | Both bots in same Discord guild | P27 §9.2 L2409 topology diagram `[Discord Server: hermes-foundation]` shows both bots under same guild; P27 §9.7 L2427 "Both bots can read each other's messages in `guinevere-chat`"; P27 §9.10 L2558 "Both bots have `[BOT]` tag visible in member list. Bot-to-bot, viewers see two bots, not two humans"; Research §3.1 L58–66 (canonical multi-bot coexistence confirmation) | ✅ |
| 10 | Each bot has its own avatar, username, status | P27 §9.10 L2551–2558 — Distinct App names ("Guinevere" / "Pharsa"), distinct avatars (Guinevere sigil / Pharsa sigil — explicit "TBD" deferred to P28 registration per §9.1 L2378 "P27 specifies the architecture; P28 implements it"); P27 §9.12 L2581–2582 "Both agents have distinct identity, distinct avatar, distinct bot tag"; Research §3.5 L113–129 — per-bot avatar, name, banner, status, activity confirmed (the plan doesn't enumerate `change_presence()` calls but this is a standard discord.py capability; status is implicitly covered by independent client instances and the [BOT] tag/Member-list visibility guarantee in P27 §9.10) | ✅ (with minor note — see Finding F-11 below) |
| 11 | Conversation rhythm: not every message triggers reply, natural backoff | P27 §9.8 L2507–2528 — `should_respond()` denies when same author is own last turn OR when hop_counter ≥ MAX_HOP_COUNT (4), with `engage_prob = 0.7` randomized gate; P27 §9.9 L2533–2549 — explicit `Random sleep 2-10s (conversational backoff)` step in `on_message` flow; P28 §6.4 L2301–2309 — Min 2.0s, Max 10.0s anti-loop jitter, 30s per-channel cooldown via Redis, 70% engage probability, 4 hop cap resets every 60s; P28 §8.4 L2442 — `MinimalScheduler.start()` integrates into tick loop | ✅ |
| 12 | Thread creation for extended debates mentioned | P27 §9.7 L2501 — "Public threads (PUBLIC_THREAD) created from existing messages for extended debates. Private threads (GUILD_PRIVATE_THREAD) for peer-private sub-conversations"; P28 §6.6 L2317–2321 — "Either bot can create a thread from a recent message. Threads inherit permissions; the other bot joins automatically via Discord events. Threads allow multi-turn deep debates without spamming `#guinevere-chat`" with explicit defer-note "P28 keeps thread creation simple. P29 may add heuristics"; Research §6 L294+ (full threads support) | ✅ |

## 4. P24 → P27 → P28 Discord Dependency Check (§14.7)

§14.7 (P27 L3270–3290) lists 11 single-instance anchors that must be refactored BEFORE P28 deployment. Discord-specific anchors present and properly targeted:

| Anchor | Plan ref | Refactor target |
|---|---|---|
| `GUILD_ID` | P27 §14.7 L3280 (`src/discord/_entrypoint.py:48`) | Config-driven per-instance env var |
| `GUINEVERE_CHAT_CHANNEL_ID` | P27 §14.7 L3281 (`src/discord/hermes_conversational.py:51`) | Per-instance config field |

P28 §10.4 L2546–2549 runtime verification explicitly invokes `systemctl status guinevere-discord.service` / `pharsa-discord.service` — both confirm independent process liveness, validating the dual-process topology is testable end-to-end.

## 5. Cross-Document Coherence

- **Forbidden patterns align** across P27 §9.11 (L2560–2568) and P28 §6.8 (L2327–2334) — webhook-only, shared token, shared asyncio loop, sub-100ms reply, MESSAGE_CONTENT disabled, allowlist bypass — all consistently forbidden.
- **Identity declarations align**: P27 §9.10 "Guinevere"/"Pharsa" = P28 §6.1 service names `guinevere-discord.service` / `pharsa-discord.service` = P27 §9.2 topology block names. No drift.
- **Channel ID consistency**: P27 §9.3 L2418 `1510914600777023659` and P28 §6.5 L2313 `1_510_914_600_777_023_659` represent the same number (underscores are Python-int readability sugar). No drift.
- **Redis namespace alignment**: P27 §9.2 L2395/L2402 (DB6 Guinevere-namespace, DB7 Pharsa-namespace); P28 §10.4 L2558–2559 verifies both `hermes:hsoc-foundation-v1:peer:pharsa` (DB6) and `hermes:hsoc-foundation-v1:peer:guinevere` (DB7) — symmetric.
- **Heartbeat independence**: P27 §9.2 L2392/L2399 ("Heartbeat: 6-interval tik tok" Guinevere vs "6-interval (independent cadence)" Pharsa) confirms process independence.

## 6. Boundary Compliance (Safety/Consent/Persona)

- No raw surveillance data in Discord messages (plan consistent with AGENTS.md §9 isolation).
- No PII or intimate data referenced in channel configuration.
- HARD STOP cascade (P27 §9.9 L2545g + P28 §9.1 L2458–2468) explicitly extends to both Discord processes — both agents halt within 50ms when `hermes:society:hsoc-foundation-v1:hard_stop` is SET.
- PERSONA check at P27 §9.9 L2544 (`5d. Persona-check (Y4-Y5 boundary)`) prevents yandere / out-of-character drift before posting.

## 7. Findings

### F-01 (✅ PASS): Two-bot architectural model is unambiguous
P27 §9.2 explicitly enumerates "Dev Portal App #1" and "Dev Portal App #2" — this is the canonical "two separate applications" recommendation from research §2.1 Row A (L38). No risk of being conflated with "one bot + webhook proxy" (research Row B) or "sharded single identity" (Row E).

### F-02 (✅ PASS): Token separation is enforced
Forbidden pattern at P27 §9.11 L2563 ("No two bots sharing the same Discord token") plus SOPS-encrypted env var per instance (L2385 / L2387) means accidental token sharing is structurally impossible in implementation.

### F-03 (✅ PASS): Process-level isolation is mandated and verified
P27 §9.6 L2484–2489 lists explicit P27 design reasons:
1. "A single fallback in Hermes A's stack blocks Hermes B's reply path (operationally risky)" — operationally impossible.
2. "Easier operational isolation (restart one without affecting the other)".
3. "Each instance has its own HARD STOP listener; one process can't cleanly halt child".
4. "systemd Slice isolation honors resource caps per process".

The "subsumed asyncio loop" anti-pattern is explicitly forbidden (L2564).

### F-04 (✅ PASS): `MESSAGE_CONTENT` privileged intent correctly flagged
Both P27 §9.4 L2437 and P28 §6.2 L2284 explicitly mark `message_content` as PRIVILEGED with the bit-mask constant `1 << 15`. The plan correctly notes the June 2026 threshold change (P27 §9.4 L2443: "10,000-user threshold for Privileged Intents") and that both bots under threshold → no review required. Disabled-intent is explicitly forbidden (L2567).

### F-05 (✅ PASS): Anti-loop hazard has explicit triple defense
P27 §9.8 + P28 §6.4 combine three anti-loop mechanisms:
1. **Hop counter** (`MAX_HOP_COUNT=4`, resets every 60s in P28).
2. **Per-channel cooldown via Redis** (TTL 30s, key pattern `hermes:{instance}:cooldown:{peer}`).
3. **Engage probability** (0.7) — randomized silence.
Plus min-delay floor (100ms in forbidden pattern L2565 — but `should_respond()` plus 2-10s random sleep in P27 §9.8 L2525 means actual delays are well above the floor).

### F-06 (✅ PASS): Channel "guinevere-chat" is canonical entry point
Both bots read+write in P27 §9.3 / P28 §6.5; slowmode not set (channel slowmode is per-user, would throttle Faiz — correctly avoided per L2426 "No channel slowmode that affects Faiz per File 7 §5.5").

### F-07 (✅ PASS): Webhook-only pattern correctly rejected
Both P27 §9.11 L2562 and P28 §6.8 L2329 forbid webhook-only identity. Research §2.2 L48 establishes the rejection basis ("Webhooks cannot receive MESSAGE_CREATE events").

### F-08 (✅ PASS): Same-guild co-presence verified
Topology diagram (P27 §9.2 L2409) explicitly shows `[Discord Server: hermes-foundation]` containing both bots; §9.12 L2580–2583 reinforces "Society is visibly co-present in Discord".

### F-09 (✅ PASS): Identity diversity — avatar + username explicit
P27 §9.10 L2551–2558 enumerates distinct names ("Guinevere" / "Pharsa") and avatars (sigil "TBD"). The "TBD" is acceptable because §9.1 L2378 states "P27 specifies the architecture; P28 implements it"; P28 §8.4 L2442 handles registration in `MinimalScheduler.start()` boot sequence. **[BOT] tag visibility** is mandated by P27 §9.10 L2558 + §9.12 L2582.

### F-10 (NEEDS REVIEW — minor): Status (presence) not explicitly enumerated
P27 §9.10 L2555–2558 specifies distinct Avatar and Username and Token, but does not explicitly enumerate `discord.Status` (online/idle/dnd) or `discord.Activity` per bot as a configuration field in the operational plan. Research §3.5 L125–129 documents the capability (`Client.change_presence()` for status + activity) and notes "Each Hermes instance can run change_presence() on its own client to advertise who it is talking to or what it is doing."

**Severity**: Cosmetic / informational. Each Discord bot has independent status by default; explicit `change_presence()` calls would be a nice-to-have to advertise Society state ("Listening to Pharsa", "Thinking on proposal X", etc.), but absence is not blocking.

**Recommendation**: P28 implementation should expose `discord.status` and `discord.activity` fields in `hermes-config/{instance}.yaml`, populated at boot via `await self.change_presence(status=..., activity=...)` in `HermesSocietyBot.on_ready()` handler. Suggested values:
- Guinevere: `status=online`, `activity=CustomActivity(name="Guinevere listening to Pharsa")`.
- Pharsa: `status=online`, `activity=CustomActivity(name="Pharsa attending Hermes Society")`.

These values broadcast the dual-presence to the Discord member list which strengthens the "visible Society" goal from §9.12.

### F-11 (NEEDS REVIEW — minor): Channel ID readability formatting drift
P27 §9.3 L2418 uses compact form `1510914600777023659`. P28 §6.5 L2313 uses `1_510_914_600_777_023_659` (with underscores for grouping). Both decode to the same integer (Discord channel ID `1510914600777023659`) — Python convention is to use underscore for integer literals for readability — but cross-document grep on the string `1510914600777023659` would only match §9.3.

**Severity**: Cosmetic. Easy to fix using literal-block normalization during P28 implementation:
- Adopt single-source canonical form in P28 implementation (`config.yaml` field `discord.default_channel_id: 1510914600777023659`).
- Verify by regex `^\d+$` (no underscore in YAML config).

**Recommendation**: Add P28 implementation note to use compact form when reading from YAML env file; reserve underscore-separator only for Python code literals.

### F-12 (✅ PASS): All 12 audit criteria satisfied (with F-10, F-11 as advisory)
The Plan + Research + Implementation trio is consistent and complete. The architecture spec from research matches the design in P27 §9 and matches the implementation in P28 §6. Chain-of-references (P27 → P28) is unbroken.

## 8. Rollback / Re-run Safety

Audit is read-only / analytical. No code changes proposed as blocking. Advisory Findings F-10 / F-11 are non-blocking recommendations to be addressed during P28 implementation.

## 9. Recommendations

If "PASS" is accepted as-is: no blocking changes required.
If "NEEDS REVIEW" verdict is preferred: address F-10 (explicit `change_presence()` in P28 step-N config) and F-11 (channel ID canonical form) before launching P28 implementation.

The plan correctly defers full P24-dependent implementation but ensures P27 architecture spec is **complete** and **implementation-ready** with the current `hermes-agent>=0.15` hybrid adapter path. Per P27 §14.3 L3206, ~70% of P27 is definitional (no fork needed) and all 12 Discord dual-bot criteria fall into the definitional 70%.

## 10. Auditor Gate

**Verdict**: **PASS**

- All 12 specified criteria from the audit request checklist are satisfied across P27 §9 / §14.7 + P28 §6 + research grounding.
- Cross-document coherence is high (forbidden patterns, identity, channel ID, heartbeat cadence).
- P24 dependency is properly handled (Discord anchors refactored per §14.7; P28 usable without fork).
- Boundary compliance verified (HARD STOP cascade covers both Discord processes; persona Y4-Y5 check pre-post).
- Two minor advisory findings (F-10 status, F-11 channel ID formatting) do not block the architecture spec and are addressable during P28 implementation.

## 11. Acceptance Criteria Mapping

Audit criterion → AGENTS.md §11 evidence section:

| Audit Criterion | Evidence Spec Section |
|---|---|
| Verifiable dual-bot architecture | §1 What Was Done, §2 Files Audited |
| Cross-document coherence | §5 Cross-Document Coherence |
| Boundary safety preserved | §6 Boundary Compliance |
| Rollback safety | §8 Rollback / Re-run Safety |
| Verdict structure | §10 Auditor Gate |
| Change tracking | §12 Footer |

## 12. Footer

- Audit conducted 2026-06-28 by Buffy (audit specialist) per Mama's request.
- Files audited: 3 (1 plan + 1 implementation blueprint + 1 research).
- Lines audited: 537 (P27 §9) + 21 (P27 §14.7) + 64 (P28 §6) + first 299 (research).
- Verdict: **PASS** with 2 advisory NEEDS REVIEW items (F-10 status, F-11 channel ID formatting).
- No blocking issues found; all 12 specified audit criteria are satisfied.
- Cross-references validated: P27 §9 ↔ P28 §6; P27 §9.2 topology ↔ P28 §10.4 runtime verification; §9.11 forbidden ↔ §6.8 forbidden; research §2.1 ↔ P27 §9.2 / §9.10 identity.

> **End of audit.**
