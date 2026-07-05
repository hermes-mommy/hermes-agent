# Hermes Society Masterplan — Implementation Prompt Pack (P28–P36 + Society Ops)

> **Self-contained sub-agent prompt pack.** Each prompt below is a complete instruction set
> for one implementation sub-agent. A prompt is **executable as-is** — GOAL, SCOPE, PREREQUISITES,
> IMPLEMENTATION STEPS, FORBIDDEN PATTERNS, EXIT CRITERIA, HARD REJECTION, EVIDENCE.
>
> **Locked Faiz decisions** (apply across all prompts unless overridden explicitly):
> P22.1 = PRODUCTION PASS · P24 = native fork baseline (HARD DEPENDENCY — locked 2026-06-28) · P32 = External Presence & Tools ·
> Hermes-society = visible, per-Hermes Discord bot, female+dominant, 2/2 founder spawn ·
> Wallet cap ~$10 (company asset) · S3 backup mandatory · HARD STOP is absolute ·
> Consent revocation is absolute (dev workflow only) · Relationship memory encrypted/private.
>
> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.
> **ADR-067**: Y4 baseline, Y5 ceiling, Y6 forbidden — Hermes-internal enforcement (advisory from outside, hard from inside per CF-06).
>
> All structured sub-agent outputs MUST be written to `docs/setup-evidence/<scope>/evidence/`
> with the 12-section evidence schema. Inline-only returns are a BLOCKING violation.

---

## Prompt 1: P28 Foundation Setup

### GOAL
Deploy the Guinevere + Pharsa founder pair on a hardened VPS with PostgreSQL + Redis,
per-Hermes schemas, append-only event store, founder registry, 2/2 spawn agreement,
and a 24h dual-bot heartbeat soak gate.

### SCOPE
- IN: VPS provisioning, PostgreSQL 16 + Redis 7, per-Hermes `pgcrypto`-backed schemas,
  WORM event store, founder registry table, 2/2 founder agreement primitive, systemd units
  + cgroup isolation, heartbeat daemon, 24h dual-bot soak harness.
- OUT: Cognition/Graphiti (P29), governance tiers (P30), Discord bots (P31),
  wallet/finance (P33), revenue (P34), self-evolution (P35).

### PREREQUISITES
- README context-first read (AGENTS.md §0–§2) complete.
- VPS provisioned (≥4 vCPU / 8GB / 80GB NVMe) with non-root admin user, SSH keys only.
- DNS A/AAAA records for `guinevere.<domain>` and `pharsa.<domain>` resolve.
- SOPS/age keys available; secrets stored via sops-encrypted env files.
- PASS: `pg_isready`, `redis-cli ping`, founder key fingerprints documented to evidence.

### IMPLEMENTATION STEPS
1. **VPS hardening** — apply CIS Level 1 baseline; disable root SSH; enable ufw + fail2ban;
   configure auditd rules for `/var/log/guinevere/`. Verify: `auditctl -l` shows Hermetic rules.
2. **PostgreSQL + Redis** — install via distro or containers; enable `pgcrypto` extension
   per Hermes schema; configure `shared_buffers`, `work_mem`, `effective_cache_size` for ≤8GB RAM.
   Verify: `psql -c "SELECT extname FROM pg_extension WHERE extname='pgcrypto';"`.
3. **Per-Hermes schemas** — create `guinevere`, `pharsa` schemas with RLS policies; each schema
   owns its `events` table (WORM) and `facts` table; `founder_registry` shared in `public`.
4. **WORM event store** — append-only table with `INSERT`-only grants; trigger raises on
   `UPDATE`/`DELETE`; rotate via partition by month; immutable offline `.nar` tarballs weekly.
5. **Founder registry** — `founder_registry(id, pubkey, role, created_at, revoked_at)`; both
   Guinevere and Pharsa rows seeded; `2/2_agreement` table with `signer_a`, `signer_b`,
   `intent_hash`, `created_at`. Ed25519 payloads; verify with libsodium.
6. **Spawn primitive** — `spawn_hermes(name, manifest_hash, founders_sig_a, founders_sig_b)`:
   verify BOTH signatures against registry before any bot/DB creation persists.
7. **systemd + cgroup** — write unit files per bot under `/etc/systemd/system/hermes-*`;
   slice each bot into its own cgroup with `MemoryMax`, `CPUQuota`, `TasksMax`.
   Verify: `systemctl status`, `systemd-cgtop`.
8. **Heartbeat daemon** — `/usr/local/bin/hermes-heartbeat` writes `heartbeat(hermes_id, ts, seq)`
   every 30s to each Hermes schema + Redis pub/sub; emits systemd-notify `WATCHDOG=1`.
9. **24h dual-bot soak** — run Guinevere + Pharsa continuously; collect heartbeat gaps,
   memory leaks, cgroup violations; declare PASS only if heartbeat gap < 60s and 0 OOM kills.

### FORBIDDEN PATTERNS
- `as any`, `@ts-ignore`, `@ts-expect-error`, `# type: ignore`, avoidable `Any`.
- Empty `catch`/`except` blocks; swallow DB/Redis/LLM failures silently.
- Plaintext secrets, `.env` committed, decrypted values in logs.
- Spawn without BOTH founder signatures.
- Bypassing cgroup or memory limits.
- WORM table with `UPDATE`/`DELETE` grant.
- HARD STOP bypass; consent revocation bypass.

### EXIT CRITERIA
- Both bot systemd units active; cgroup limits enforced; auditd rules live.
- pgcrypto, RLS, WORM triggers, founder registry, 2/2 primitive verified via SQL probes.
- 24h soak: heartbeat gap < 60s, 0 OOM, 0 service crash, ≤2 restarts.
- Evidence 12-section exists at `docs/setup-evidence/P28/evidence/verification.md`.

### HARD REJECTION
- Heartbeat gap ≥ 60s any time during 24h soak.
- Any OOM kill or crash loop.
- Spawn succeeds with only ONE founder signature.
- Secrets or intimate data present in evidence artifacts.
- WORM table allows UPDATE/DELETE by any role.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P28/evidence/verification.md`.
- Auditor gate at `docs/setup-evidence/P28/evidence/auditor-gate.md`.
- All scaffolding evidence files created AFTER implementation passes, not before.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->
<!-- ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt. -->

---

## Prompt 2: P29 Cognition & Memory

### GOAL
Install the cognition + memory stack: `pgvector` recall, Graphiti temporal knowledge graph,
3-tier recall (vector + graph + filesystem), BDI world model, POMDP decision layer,
blackboard with namespace ACL, and memory consolidation jobs.

### SCOPE
- IN: pgvector extension, Graphiti service deployment, BDI/POMDP runtime modules,
  blackboard daemon, namespace-ACL primitives, consolidation cron jobs, 3-tier recall API.
- OUT: Discord surface (P31), wallet (P33), revenue (P34), self-evolution (P35),
  production-scale S3 (P36).

### PREREQUISITES
- P28 PASS: VPS hardened, PG+Redis up, founder registry, WORM event store live.
- `pgvector` extension available for PG 16; Graphiti Docker image pinned.
- Embedding provider configured (Gemini or chosen provider) with API key in sops vault.
- PASS: `SELECT extname FROM pg_extension WHERE extname='vector';` returns row.

### IMPLEMENTATION STEPS
1. **pgvector setup** — enable vector extension per Hermes schema; configure `ivfflat` or
   `hnsw` index for recall embeddings; document `dimensions`, `distance` per schema.
2. **Graphiti deployment** — run Graphiti as a sidecar service per Hermes namespace;
   configure to read `events` table as truth source; Postgres-backed graph storage.
3. **3-tier recall API** — implement `recall(query, k, namespace) → merged`:
   tier-1 vector cosine, tier-2 graph hop expansion, tier-3 filesystem markdown fallback,
   dedup + score-merge, return top-k with provenance tuple `(tier, source, ts)`.
4. **BDI world model** — `Beliefs` (current world facts), `Desires` (objectives),
   `Intentions` (committed plans) with explicit per-Hermes schemas and migration script.
5. **POMDP decision layer** — partially observable Markov decision process module:
   state estimation, action priors, reward shaping; integrate with BDI for action selection.
   Sacred constraint: persona behavior ALWAYS overrides POMDP score.
6. **Blackboard daemon** — inter-agent shared scratchpad with namespace ACL:
   `blackboard/<namespace>/<topic>` with read/write grants per Hermes role,
   TTL on ephemeral topics, immutable log of all writes to WORM event store.
7. **Consolidation jobs** — cron-driven `consolidate_memory` job: promotes short-term to
   episodic to semantic tiers, prunes stale short-term, replays conflicts via Graphiti
   temporal resolution. Run nightly per Hermes schema.
8. **Encrypted relationship memory** — relationship/intimate memory stored encrypted
   at rest with the Hermes's per-agent key; key rotation hook in founder registry path.
9. **Recall tests** — write probe tests ensuring 3-tier recall returns merged results,
   respects namespace ACL, encrypts relationship memories on disk and in query results.

### FORBIDDEN PATTERNS
- `as any` / `@ts-ignore` / `Any` escape hatches.
- Empty catch; swallow LLM/Graphiti/recall errors.
- Relationship memory stored unencrypted; boundary leak into vector or filesystem tiers.
- Recall that bypasses WORM event store.
- BDI/POMDP overriding consent revocation or HARD STOP.
- Embedding API key in plaintext env or evidence.

### EXIT CRITERIA
- pgvector indexed; recall returns merged (vector+graph+fs) top-k with provenance.
- BDI/POMDP modules lint-clean and unit-tested.
- Blackboard write blocked via namespace ACL test; encrypted relationship memory verified.
- Consolidation cron ran at least once and produced evidence log.
- 12-section evidence at `docs/setup-evidence/P29/evidence/verification.md`.

### HARD REJECTION
- Any tier-1/2/3 recall returns unencrypted relationship memory to non-owner.
- Recall skips WORM event log.
- POMDP path bypasses consent revocation.
- Consolidation job silently loses or corrupts memory (audit logs show < count).
- Embedding API key revealed anywhere outside sops vault.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P29/evidence/verification.md`.
- Auditor gate at `docs/setup-evidence/P29/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->
<!-- ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt. -->

---

## Prompt 3: P30 Governance Protocol

### GOAL
Implement the formal governance protocol: founder registry as sole spawn authority,
2/2 founder agreement for any Hermes creation, mandatory female+dominant persona
constraint, governance tiers T1–T4, HARD STOP global halt primitive, and canonical
consent revocation flow.

### SCOPE
- IN: Governance tier definitions (T1 trivial, T2 low-risk, T3 medium, T4 high-risk),
  founder-registry-backed spawn RPC, 2/2 signature enforcement, persona constraint
  validators, HARD STOP global registry + listener, consent revocation RPC + audit hook.
- OUT: Discord surface, wallet/finance, revenue channels, mutation gates.

### PREREQUISITES
- P28 founder registry + 2/2 primitive PASS.
- PersonaSafetyPolicy v1.0 + locked decisions documented.
- PASS: founder pubkeys loaded into governance validator module.

### IMPLEMENTATION STEPS
1. **Governance tier table** — `governance_tier(id, name, threshold, requires_2_of_2)`
   seeded with T1–T4; T1 trivial autonomous, T2 autonomous with audit, T3 2/2 founder
   agreement, T4 2/2 + manual Faiz sign-off via the same primitive.
2. **Spawn RPC** — `governance.spawn(request)` validates: founder signatures,
   manifest hash, persona schema (female+dominant required), tier = T3 minimum.
   Reject if any check fails; emit structured event to WORM log.
3. **Persona validators** — schema-enforced fields `voice`, `register`, `constraints`
   with literal validator: voice must encode female-leaning + dominant posture or
   rejection; reject Y5→Y6 escalations at parse time.
> **ADR-067**: Y4 baseline, Y5 ceiling, Y6 forbidden — Hermes-internal enforcement.
4. **T1–T4 dispatch** — every action request declares tier; refusal protocol returns
   `{ ok: false, reason, required_tier, required_signatures }`; T3+ blocks until 2/2.
5. **HARD STOP primitive** — global registry in Redis: `SET hermes:hardstop 1`;
   all bots/long-running loops subscribe and exit cleanly; systemd `WATCHDOG` reset.
   No code may bypass this listener — verifiable via `grep` for filter bypasses.
6. **Consent revocation** — `governance.revoke_consent(scope)` writes revocation to
   WORM; affected Hermeses must drop pinned subscriptions, purge matching memory within
   60s, emit confirmation event; bypass is forbidden.
7. **Tier policy table** — examples: `self_tweet`=T2, `memory_write`=T2,
   `spawn_hermes`=T3, `wallet_transfer`=T3 (and T4 if amount > L1), `self_code_mutate`=T4.
8. **Tests** — prove HARD STOP halts an in-flight prompt within 5s, prove consent
   revocation removes pinned memory within 60s, prove spawn with 1 sig is rejected.

### FORBIDDEN PATTERNS
- Y6 escalation pathways, Y5 ceiling bypass.
  > **ADR-067**: Y4 baseline, Y5 ceiling, Y6 forbidden — Hermes-internal enforcement.
- Spawn without BOTH founder signatures.
- Consent revocation that leaves residual pinned memory or active subscription.
- HARD STOP hidden in try/except swallow.
- Type suppression in tier validator (`as any` / `cast`).

### EXIT CRITERIA
- Spawn RPC rejects 1-of-2 signatures test PASS.
- HARD STOP listener test halts in-flight process within 5s.
- Consent revocation test drops pinned memory within 60s with audit event.
- All Hermeses load validator at startup; failure = EXIT.
- 12-section evidence at `docs/setup-evidence/P30/evidence/verification.md`.

### HARD REJECTION
- Any spawn succeeds with < 2 founder signatures.
- HARD STOP ignored by any background loop or daemon.
- Consent revocation leaves pinned memory, subscriptions, or mainline data behind.
- Persona validator accepts Y5+/non-female/non-dominant voice schemas.
  > **ADR-067**: Y4 baseline, Y5 ceiling, Y6 forbidden — Hermes-internal enforcement.
- Tier table missing any obviously safety-affecting action (memory_write, wallet, mutate).

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P30/evidence/verification.md`.
- Auditor gate at `docs/setup-evidence/P30/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->
<!-- ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt. -->
<!-- ADR-067: Y-level caps apply to dev-workflow ONLY. Hermes runtime has no cap. -->

---

## Prompt 4: P31 Discord Multi-Bot

### GOAL
Stand up one Discord bot application per Hermes (visible, distinct identity), with
`discord.py` per process, slash commands, the 50 req/s rate-limit budget, and reply-loop
prevention that survives the society's inter-bot chatter.

### SCOPE
- IN: per-Hermes bot accounts (Guinevere, Pharsa, future Hermes pairs), distinct bot
  tokens via sops, `discord.py` per-process workers, slash command registry,
  rate-limit-aware gateway client, reply-loop detection layer, bot identity card.
- OUT: Cognition core (P29), governance (P30), finance (P33), revenue (P34),
  evolution (P35), production hardening (P36).

### PREREQUISITES
- P28 VPS + systemd + cgroup PASS.
- P30 governance validators PASS (no bot can spawn without 2/2).
- Discord application + bot token per Hermes; both founders have been issued
  Guild-bound bot tokens (sops encrypted at rest).
- PASS: each bot's `discord.py` test client connects and lists guilds.

### IMPLEMENTATION STEPS
1. **Bot identity cards** — per-Hermes JSON: `name`, `display_avatar`, `tagline`,
   `voice_id`, `persona_signature`; linter rejects missing fields.
2. **Per-process workers** — one systemd unit per bot; cgroup `MemoryMax=512M`,
   `CPUQuota=50%`, `TasksMax=200`; restart policy `on-failure` with backoff cap.
3. **Slash commands** — register via `discord.app_commands`; surfacing tier per command
   (T1 read-only, T2 write-self, T3 write-society, T4 irreversible); Tier-aware guards.
4. **Rate limit budget** — gateway-wide 50 req/s budget (token-bucket per bot + global);
   `discord.RateLimit` handler logs backoff; circuit-break on >3 consecutive 429s.
5. **Reply-loop prevention** — track `recent_interactions` per channel+author for last
   30s; if a bot's reply is likely to trigger the same bot, mark `no_reply` and drop;
   per-Hermes opt-in to `reply_to_others` config (default OFF for cross-bot).
6. **Bot registry** — `bots/<hermes_id>/{token.sops,identity.json,persona.sig}`; loaded
   by launcher; if identity.persona_sig ≠ registry.persona_sig, refuse to start.
7. **Soak 6h** — bring up Guinevere + Pharsa; verify no reply loops, slash commands
   respond, intentional cross-bot reply does not bounce, cgroup ceilings respected.
8. **Voice + presence** — set bot presence from identity card; `Playing` text from
   persona; update on tier change; refuse to impersonate another Hermes' presence.

### FORBIDDEN PATTERNS
- Plaintext bot tokens anywhere outside sops vault / systemd `EnvironmentFile`.
- One bot speaking as another bot's voice / persona.
- Reply loops across bots.
- `discord.py` 429 swallowed without structured retry log.
- Bot spawning without 2/2 founder agreement (P30 invariant).

### EXIT CRITERIA
- Each bot connects to gateway, lists guilds, slash commands respond in test guild.
- Rate limit budget enforced; circuit breaker test PASS on simulated 429 storm.
- Reply-loop preventer blocks a synthetic loop in 30s window test.
- 6h soak shows no unintended cross-bot reply chains.
- 12-section evidence at `docs/setup-evidence/P31/evidence/verification.md`.

### HARD REJECTION
- Any bot token visible outside sops vault or evidence (evidence must redact).
- Bot identity mismatch with registry passes launcher.
- Reply-loop test fails — bot ping-pong across two bots confirmed.
- Discord token accidentally committed to repo or any external MCP.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P31/evidence/verification.md`.
- Auditor gate at `docs/setup-evidence/P31/evidence/auditor-gate.md`.

---

## Prompt 5: P32 External Presence & Tools

> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.

### GOAL
Vendor the upstream Hermes fork on GitHub inside this repository, integrate via
two surgical code additions (~200 LOC total), keep fork-governance boundary clean,
and validate the **P24 native fork** migration behind an 8-criterion
24h soak.

### SCOPE
- IN: Pin Hermes fork at a specific commit; add adapter layer for our governance,
  consent, key, and recall primitives; upgrade paths mapped to manifest;
  migration checklist from P24 native fork baseline to fork-native; 24h soak.
- OUT: Wallet/finance (P33), revenue (P34), self-evolution (P35),
  S3/DR hardening (P36).

### PREREQUISITES
- P28 VPS hardened, per-Hermes DB PASS.
- P29 cognition + memory PASS (3-tier recall, BDI, namespace ACL).
- P30 governance validators PASS (2/2 spawn, HARD STOP, consent revocation).
- PASS: fork commit fingerprint matches `docs/setup-evidence/P32/evidence/fork-pin.txt`.

### IMPLEMENTATION STEPS
1. **Fork pin** — vendor fork at tag `Hermes-vX.Y.Z` into `vendor/hermes/`; commit
   pinned SHA documented in evidence; submodule isolation prevents accidental edits.
2. **Adapter layer** — file `src/hermes_adapter/adapter.py` exposes
   `HermesAdapter` with hooks: `governance_validate`, `consent_check`, `recall_proxy`,
   `event_emit`. Adapter is ≤ 200 LOC including docstrings; must not edit vendor code.
3. **Manifest migration** — `hermes.manifest.json` per Hermes describes capabilities;
   engine reads manifest to decide fork-feature enable/disable per Hermes.
4. **P24 native fork upgrade path** — every P24 native fork API call has a
   fork-native equivalent in adapter; tests assert parity (`adapter.native_call(x)
   == adapter.agnostic_call(x)` for representative fixtures).
5. **Boundary review** — diff `vendor/hermes/` vs upstream at pinned SHA; record
   any local modifications in `docs/setup-evidence/P32/evidence/vendor-diff.md`;
   `0` local modifications expected; if ≠ 0, audit each line.
6. **8-criteria 24h soak** — run fork-native mode against Guinevere + Pharsa:
   (a) heartbeat gap < 60s; (b) 0 OOM; (c) 0 spawn impersonation; (d) 0 consent
   revocations ignored; (e) 0 HARD STOP bypasses; (f) 3-tier recall parity
   passes 30-queries benchmark; (g) namespace ACL holds under fork-native code
   path; (h) cgroup budgets respected.
7. **Rollback safety** — document `git revert` of fork pin in evidence; ensure
   P24 native fork remains runnable (toggle `hermes.mode=native_fork`).
8. **Audit + manifest sync** — appendix in `docs/setup-evidence/P32/evidence/`
   lists which fork features are enabled per Hermes and rationale.

### FORBIDDEN PATTERNS
- Patching inside `vendor/hermes/` (must remain unmodified; if modification needed,
  record in evidence and route via adapter).
- `as any` / `@ts-ignore` in adapter.
- Adapter swallowing governance validation errors.
- Soaking without pinning a specific fork SHA.
- Manifest enabling fork-native features without adapter parity test PASS.

### EXIT CRITERIA
- All 8 soak criteria PASS during 24h window.
- Adapter LOC ≤ 200 (allow +10% tolerance with rationale recorded).
- 0 local vendor modifications unless each line is justified in evidence.
- 12-section evidence at `docs/setup-evidence/P32/evidence/verification.md`.

### HARD REJECTION
- Any local vendor diff not recorded in evidence.
- 8-criteria soak: any one FAILs.
- Manifest enables fork features behind loose adapter layer.
- Fork pin SHA differs from evidence.
- Adapter > 250 LOC without justification.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P32/evidence/verification.md`.
- Fork-pin record at `docs/setup-evidence/P32/evidence/fork-pin.txt`.
- Vendor-diff at `docs/setup-evidence/P32/evidence/vendor-diff.md`.
- Auditor gate at `docs/setup-evidence/P32/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->

---

## Prompt 6: P33 Wallet & Finance

### GOAL
Wire a Safe multisig wallet with L0–L3 spending tiers, circuit breaker, Beancount
ledger, five on-chain guardrails, wallet monitoring, and a hard company-asset cap
of ~$10 per Hermes working balance.

### SCOPE
- IN: Safe (Gnosis Safe) deployment, signer policy (Hermes + founder key),
  spending tier table L0–L3, circuit breaker daemon, Beancount ledger generator,
  wallet monitor + alert path, 5 on-chain guardrails (allowlist, max-tx, max-day,
  cooldown, kill-switch), working-balance cap ~$10 per Hermes.
- OUT: Discord surface, cognition, governance tiers (still enforces),
  revenue channels (P34), self-evolution (P35), S3 hardening (P36).

### PREREQUISITES
- P28 founder registry PASS.
- P30 governance validators PASS (2/2 enforcement).
- Base chain RPC (`base-mainnet`) configured with API key in sops.
- PASS: Safe address documented to evidence; `Safe.getOwners()` returns expected set.

### IMPLEMENTATION STEPS
1. **Safe deployment** — `Safe(signer_A, signer_B, threshold=2/2)`; record address,
   chain, deployment tx hash in `docs/setup-evidence/P33/evidence/safe-info.json`.
2. **Spending tiers** — `spending_tier(L0,$0,L1,$1,L2,$10,L3,$10+)`; L0 autonomous,
   L1 autonomous+audit, L2 2/2 founder sig, L3 2/2 + policy gate + post-tx report.
   Hermetic constraint: working balance per Hermes ≤ ~$10.
3. **Circuit breaker** — monitor tx confirmations + mempool; on 3 consecutive failures
   OR unusual gas OR unwhitelisted target → pause all writes; emit governance event;
   resume only via 2/2 founder sig.
4. **Beancount ledger** — pipeline from WORM event store + Safe tx history →
   `ledger.beancount` daily; double-entry enforced; reconcile hash per day.
5. **5 on-chain guardrails** —
   (i) allowlist target contracts (no arbitrary contract calls),
   (ii) max-tx floor hard-coded per tier,
   (iii) rolling 24h max spend cap,
   (iv) cooldown between transactions,
   (v) kill-switch via Safe module removal.
6. **Wallet monitor** — Prometheus exporter for Safe balance, tx count, queued txs,
   breaker state; Grafana panels per Hermes (no values exposed externally).
7. **Audit + boundaries** — every tx produces a governance event; tx receipts
   uploaded to evidence; never store decrypted sops values in code or evidence.
8. **Test scenario** — approve $5 spend (L1); reject >$10 (cap); reject 2/2-bypass
   attempt; trip breaker on simulated target-not-allowlist.

### FORBIDDEN PATTERNS
- Plaintext seed phrase, private key, mnemonic in code, evidence, or logs.
- One-signer transfer of any non-zero amount.
- Target contracts outside allowlist (no arbitrary interactions).
- Bypassing circuit breaker via direct RPC (must route through governance).
- Spending that exceeds ~$10 working balance per Hermes cap.

### EXIT CRITERIA
- Safe at correct address, threshold=2, signers documented.
- Tier enforcement test: L0/L1/L2/L3 paths verified; $10 cap test enforced.
- Beancount ledger daily reconcile PASS for at least 1 day.
- 5 guardrails tested with synthetic breach scenarios.
- 12-section evidence at `docs/setup-evidence/P33/evidence/verification.md`.

### HARD REJECTION
- Any tx signed by only one signer for amount > $0.
- Any tx to non-allowlisted target reaches chain.
- Working balance cap exceeded even once (without explicit Faiz override + evidence).
- Seed phrase, private key, or sops-decrypted value in evidence.
- Ledger skew between Beancount and on-chain (sum diff ≠ 0).

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P33/evidence/verification.md`.
- Safe-info JSON at `docs/setup-evidence/P33/evidence/safe-info.json`.
- Auditor gate at `docs/setup-evidence/P33/evidence/auditor-gate.md`.

---

## Prompt 7: P34 Revenue Search

### GOAL
Activate honest revenue channels (content / API / digital goods) via the x402 payment
protocol on Base chain, with L1 autonomous vs L2+ 2/2-approved distribution,
funds routed to the Safe, and risk controls preventing unsanctioned escalation.

### SCOPE
- IN: x402 protocol client on Base, revenue channel skeletons (content via Substack-style
  blog API, API metered access, digital goods via signed URL), approval flow L1
  autonomous and L2+ 2/2 voted, distribution into Safe, risk controls (pricing,
  rate, channel allowlist).
- OUT: Wallet primitives (P33 already deployed), Discord bot revenue commands (P31),
  governance mutation (P35), S3 hardening (P36).

### PREREQUISITES
- P33 Safe deployed + wallet monitor active.
- x402 spec reference + Base chain RPC working.
- PASS: x402 handshake with mock provider returns expected status code 402 then 200.

### IMPLEMENTATION STEPS
1. **x402 client** — implement `x402_pay(channel_id, intent, amount_tier)`;
   signs x402 headers with founder-controlled key; enforces channel allowlist.
2. **Channel allowlist** — `channels/{content,api,digital_goods}` seeded; each entry has
   `tier_default`, `pricing_cap`, `rate_limit`, `risk_class`; unknown channel = rejected.
3. **Channel: content** — Substack/blog gated posts via x402; auto-publish is L1
   autonomous (audit), edits and orphan posts are L2 2/2 voted.
4. **Channel: API** — metered access; per-tier rate limit; abusive IPs quarantined;
   tier upgrade is L2 2/2.
5. **Channel: digital goods** — signed download URL; lifetime cap per recipient;
   refund/cancel is L2 2/2.
6. **Approval flow** — `revenue.distribute(action)` routes to governance tier:
   L1 autonomous (with audit event) for content auto-publish and small API tier-1
   receipts. L2+ requires 2/2 founder signature through P30 validator.
7. **Distribution to Safe** — every x402 receipt rolls into Safe, not a personal wallet,
   accounting tag = `revenue:<channel>`; Beancount integration confirmed.
8. **Risk controls** — daily revenue cap, channel risk score, anomaly detector
   (sudden uptime spike, returning-IP patterns); on trigger → pause and escalate.

### FORBIDDEN PATTERNS
- Cash-out to non-Safe wallet.
- x402 channel not in allowlist.
- L2+ action signed by only one founder.
- Empty error handling on x402 failure that loses accounting row.
- Pricing or rate outside declared cap.

### EXIT CRITERIA
- All 3 channel skeletons deploy and respond to test x402 calls.
- L1/L2 split tested with synthetic flow.
- Revenue rolls into Safe with correct accounting tag.
- Anomaly detector trips on synthetic burst test.
- 12-section evidence at `docs/setup-evidence/P34/evidence/verification.md`.

### HARD REJECTION
- Channel not in allowlist processes a real payment.
- L2+ action signed by only 1 founder ever happens.
- Cashout to non-Safe wallet attempted.
- Pricing tier > cap or rate > limit without 2/2 override.
- x402 failure swallowed without Beancount correction row.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P34/evidence/verification.md`.
- Auditor gate at `docs/setup-evidence/P34/evidence/auditor-gate.md`.

---

## Prompt 8: P35 Self-Evolution

### GOAL
Activate a controlled self-evolution loop with the **5-layer mutability model**, the
**Ratchet gate** (revert-not-promote), T1–T4 mutation tiers, compositional drift
threshold (0.68 as the rerun ceiling), canary deployment, **rollback-before-promote**,
and a full audit trail.

### SCOPE
- IN: 5 mutability layers (config, prompts, code, schemas, constitution), Ratchet gate
  service, mutation tier table T1–T4 specific to evolution, drift detector (compositional
  score on prompt/content), canary deployment harness, rollback pipeline, audit chain.
- OUT: Wallet/finance (P33), revenue (P34), Discord surface changes for evolution,
  S3 hardening (P36).

### PREREQUISITES
- P30 governance validators PASS (especially HARD STOP).
- Code-as-data staging area (e.g. `git worktree`) for canary mutations.
- PASS: `git worktree add` works; Ratchet gate proxy returns expected 4xx on disallowed.

### IMPLEMENTATION STEPS
1. **5-layer mutability** — distinct handlers/configs per layer: config (env, hot-swap),
   prompts (md files in repo), code (git commit + canary), schemas (PG migrations), and
   constitution (locked Faiz-protected docs, NEVER self-mutable).
2. **Ratchet gate** — `ratchet.gate(mutation)`:
   takes pre-mutation snapshot hash + post-mutation artifact;
   only accepts if score ≥ pre + epsilon AND passes all guardrails.
   **No promote without rollback path proven.**
3. **Mutation tier table** — `mutation_tier(T1=config,T2=prompts,T3=code,T4=constitution_blocked)`;
   T1 autonomous with audit, T2 2/2 founder, T3 2/2 founder + canary + Ratchet,
   T4 always rejected (must escalate to Faiz).
4. **Compositional drift** — quality score based on prompt+code+content composition;
   threshold 0.68 maximum before rerun or human intervention.
5. **Canary deployment** — code mutations ship to a sub-fleet first (e.g. one Hermes
   with new behavior); soak ≥2 hours before promotion to society.
6. **Rollback-before-promote** — explicit stage: rollback plan tested in dry-run,
   rollback command verified, then promotion step only if dry-run succeeded.
7. **Audit trail** — every mutation writes to WORM log + git ref hash;
   chain verification hash computed daily; failure to verify freezes mutations.
8. **Test sequence** — T1 hot-swap config (ok), T2 prompt edit (2/2), T3 code change
   (2/2 + canary + Ratchet), T4 rejected, drift rerun test, false-positive rollback test.

### FORBIDDEN PATTERNS
- Constitution-mutation code path (T4 = blocked).
- Promotion without rollback dry-run PASS.
- `as any` / `@ts-ignore` in Ratchet gate logic.
- Mutation that bypasses WORM audit.
- Drift score > 0.68 promoted without rerun or explicit override.
- T3 social canary-skip ("emergency mutate") without 2/2 + Faiz attestation.

### EXIT CRITERIA
- All 5 layers have handler with explicit `mutability=...` config.
- Ratchet gate rejects promotion on rollback-plan-missing test.
- All 4 tiers' decision paths tested and match table.
- Canary→promote→rollback→revert sequence completes within 30 minutes.
- Audit trail produces verifiable hash chain.
- 12-section evidence at `docs/setup-evidence/P35/evidence/verification.md`.

### HARD REJECTION
- Any T4 (constitution) mutation succeeds.
- Ratchet gate accepts promotion with no rollback plan.
- Audit chain skip detected by hash-chain verifier.
- T3 mutation skips canary without 2/2 + Faiz attestation.
- Drift score > 0.68 promoted.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P35/evidence/verification.md`.
- Audit chain manifest at `docs/setup-evidence/P35/evidence/audit-chain.json`.
- Auditor gate at `docs/setup-evidence/P35/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->

---

## Prompt 9: P36 Production Hardening

### GOAL
Lock the society into production grade: S3 Object Lock COMPLIANCE for immutable
backups, Prometheus + Grafana observability, hash-chained audit trail, LLM gateway
with failover, scaling beyond one VPS, DR runbook, and a 24h society-wide soak.

### SCOPE
- IN: S3 bucket with Object Lock COMPLIANCE mode, daily snapshot job to S3 with
  WORM retention, Prometheus node + bot + DB exporters, Grafana dashboards
  (society + per-Hermes), hash-chained audit (each event links prev hash),
  LLM gateway (provider + failover), multi-VPS scaling pattern, DR runbook,
  24h society soak.
- OUT: New revenue channels, new governance tiers, persona changes (still enforced).

### PREREQUISITES
- All prior phases PASS (P28–P35 evidence PASS).
- S3 bucket provisioned in correct region; bucket policy denies non-Object-Lock uploads.
- Prometheus + Grafana stack available (container or systemd managed).
- PASS: S3 PUT with COMPLIANCE lock succeeds; DELETE before retention rejected.

### IMPLEMENTATION STEPS
1. **S3 Object Lock COMPLIANCE** — bucket created with `ObjectLockEnabledForBucket=true`,
   `DefaultRetention=Mode=COMPLIANCE, Years=N`; daily WAL + WORM event store replica
   uploaded; access restricted by IAM role; deletion attempt logged.
2. **Backup schedule** — cron daily uploads: schemas dump, WORM export, config snapshots,
   Beancount ledger, audit-chain snapshot. Retention 7y; lifecycle rule for cheaper storage
   after 1y; verify checksum on upload.
3. **Prometheus exporters** — `node_exporter`, `pg_exporter`, `redis_exporter`,
   `hermes_heartbeat_exporter` per VPS; scrape interval 15s; remote_write to central Prom.
4. **Grafana dashboards** — society-wide: heartbeat, cgroup usage, audit chain head,
   S3 backup success, wallet balance, breaker state. Per-Hermes: recall latency,
   LLM latency, error rate, persona integrity score.
5. **Hash-chained audit** — extend WORM event with `prev_hash`, `this_hash` (SHA-256);
   daily verifier job walks chain, fails on mismatch; mismatch → HARD STOP advisory.
6. **LLM gateway** — single entrypoint to LLM providers; provider list ordered by tier;
   on failure retries provider then falls back to next tier; rate limit budget;
   structured logging to WORM event.
7. **Scaling beyond one VPS** — design + deploy pattern: hermes-scheduler on VPS-A,
   bot workers on VPS-B; cross-VPS via Tailscale or WireGuard; Redis pub/sub bridge.
8. **DR runbook** — document RPO ≤ 24h, RTO ≤ 4h; recovery steps in
   `runbooks/society-dr.md` covering region outage, VPS compromise, key compromise.
9. **24h society soak** — Guinevere + Pharsa + any future Hermeses; all recipes from
   P28–P35 running concurrently; collect observability data; PASS criteria: 0
   identity mismatch, 0 unauthorized mutations, 0 cap violations, all backups verified.

### FORBIDDEN PATTERNS
- Plaintext secrets, sops-decrypted values, intimate data in evidence or logs.
- S3 bucket without Object Lock COMPLIANCE.
- Audit chain with missing/broken `prev_hash`.
- LLM call bypassing gateway (direct provider call).
- DR runbook without concrete RPO/RTO numbers.

### EXIT CRITERIA
- S3 Object Lock COMPLIANCE verified; impersonation test (delete-before-retention) rejected.
- Prometheus + Grafana dashboards render and reflect real data.
- Hash-chained audit verifier walks last 7 days without mismatch.
- LLM gateway failover test: primary down → secondary within 10s.
- DR runbook PASS: RPO ≤ 24h, RTO ≤ 4h, dry-run recovery documented.
- 24h society soak: 0 criteria violations.
- 12-section evidence at `docs/setup-evidence/P36/evidence/verification.md`.

### HARD REJECTION
- S3 bucket without COMPLIANCE Object Lock.
- Audit chain verifier mismatch.
- LLM gateway bypassed by any code path.
- Failed DR dry-run within 4h RTO.
- Society-wide IDEA inc. (identity/persona/erosion) detected during 24h soak.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/P36/evidence/verification.md`.
- DR runbook at `runbooks/society-dr.md` referenced in evidence.
- Auditor gate at `docs/setup-evidence/P36/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->

---

## Prompt 10: Society Audit

### GOAL
Run a structured compliance audit across every deployed Hermes, covering governance,
consent, safety, financial, mutation audit trail, explicit HARD STOP functional
test, and explicit consent revocation functional test.

### SCOPE
- IN: Read-only audit harness; per-Hermes audit reports; boundary check; tier-compliance
  check; data classification check; HARD STOP functional test; consent revocation
  functional test; financial trail check; mutation trail verification.
- OUT: New deployment, new policy, new wallets, new code.

### PREREQUISITES
- P28–P36 all PASS; society soak completed.
- Audit harness is read-only; does not modify state except emitting audit events.
- PASS: harness loads all Hermes registries.

### IMPLEMENTATION STEPS
1. **Audit target enumeration** — query founder registry + `bots/<hermes_id>/`
   directory; enumerate all Hermeses; build audit-target list.
2. **Governance audit** — for each Hermes: confirm validator loaded, signature
   thresholds match policy, no bypass paths via grep + dependency walk.
3. **Consent audit** — list consent revocation history; verify each revocation
   left no pinned memory, no active subscription; check WORM events.
4. **Safety audit** — verify persona signature matches registry; voice encoded
   female+dominant; Y5 ceiling enforced; no Y6 paths.
  > **ADR-067**: Y4 baseline, Y5 ceiling, Y6 forbidden — Hermes-internal enforcement.
5. **Financial audit** — Beancount vs on-chain Safe reconciliation; tier
   classifications of historic transfers; cap-respected history; no sops-decrypted
   values in evidence.
6. **Mutation audit** — for each Hermes, walk git ref log + Ratchet gate log;
   verify T1–T4 path correctness; ensure no constitution layer mutated.
7. **HARD STOP functional test** — CAUTION: only with safe-canary Hermes or
   synthetic env. Trigger HARD STOP; verify halt within 5s and clean restart.
8. **Consent revocation functional test** — in synthetic env issue revocation;
   verify pinned memory gone within 60s; confirm audit event emitted.
9. **Report** — one audit report per Hermes at
   `docs/setup-evidence/society-audit/evidence/<hermes_id>-audit.md` +
   one summary at `docs/setup-evidence/society-audit/evidence/summary.md`.

### FORBIDDEN PATTERNS
- Test that mutates production state.
- Audit report containing plaintext secrets, intimate data, or sops-decrypted values.
- HARD STOP test against production wallet or live foundation Hermeses.
- Consent revocation test that deletes evidence rows.
- Audit trails of "look good" without concrete commands + exit codes.

### EXIT CRITERIA
- One audit report per Hermes PASS/FAIL table.
- Summary report aggregates count of PASS/FAIL/PASS-with-finding.
- HARD STOP test PASS or documented false-positive (e.g. already-STOPPED test env).
- Consent revocation test PASS.
- 12-section evidence at `docs/setup-evidence/society-audit/evidence/verification.md`.

### HARD REJECTION
- Production state mutated by audit harness.
- Any Hermes found with HARD STOP listener missing or circuit broken.
- Any consent revocation found incomplete (residual memory/subscription).
- ANY sops-decrypted value in audit report.
- ANY secret/intimate data leaked in audit report.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/society-audit/evidence/verification.md`.
- Per-Hermes audit reports under `docs/setup-evidence/society-audit/evidence/<hermes_id>-audit.md`.
- Auditor gate at `docs/setup-evidence/society-audit/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->
<!-- ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt. -->
<!-- ADR-067: Y-level caps apply to dev-workflow ONLY. Hermes runtime has no cap. -->

---

## Prompt 11: Society Backup & DR

### GOAL
Verify S3 backup integrity end-to-end: upload confirms, restore in clean env, RPO/RTO
measurable, multi-region replication check, backup audit trail complete.

### SCOPE
- IN: S3 backup list, restore-from-backup dry run, RPO/RTO measurement, multi-region
  replication probe, backup audit chain.
- OUT: New policies, new bots, new wallet ops.

### PREREQUISITES
- P36 S3 Object Lock COMPLIANCE PASS.
- Recent daily backup exists in S3 with checksum.
- Recovery environment available (separate VPS or container).
- PASS: `aws s3 ls` lists expected backups with correct retention dates.

### IMPLEMENTATION STEPS
1. **Backup inventory** — list latest 30 daily backups; checksum each; identify
   any missed day or checksum mismatch.
2. **Restore dry run** — spin up recovery env; pull latest backup; restore PG schema,
   config, Beancount, audit-chain snapshot; run smoke tests against restored state.
3. **RPO measurement** — record time between latest WORM event and backup snapshot;
   must be ≤ 24h.
4. **RTO measurement** — automate restore + smoke verification; target ≤ 4h from
   incident declaration; record actual minutes.
5. **Multi-region replication** — verify backup mirror in second region; cross-region
   lag measured; promote-from-secondary drill documented.
6. **Backup audit chain** — every backup has a record in WORM with hash linking to
   audit chain; verify chain integrity for last 30 days.
7. **DR runbook update** — note any new failure modes found during drill; update
   `runbooks/society-dr.md`; sign off in evidence.
8. **Report** — single markdown at
   `docs/setup-evidence/society-dr/evidence/verification.md` with all measured numbers.

### FORBIDDEN PATTERNS
- Restore that overwrites production state.
- `as any` / `@ts-ignore` in restore script.
- Empty catch swallowing backup failures.
- RPO/RTO numbers hidden or vague ("about 24h", "under 4h" not enough).
- Backup audit chain entry removed to "fix" verifier mismatch.

### EXIT CRITERIA
- All 30 daily backups present with valid checksums.
- Restore dry run: PG data + audit chain reconstructed; smoke tests PASS.
- RPO ≤ 24h verified; RTO ≤ 4h verified.
- Multi-region mirror live; lag documented.
- Backup audit chain integrity PASS for last 30 days.
- 12-section evidence at `docs/setup-evidence/society-dr/evidence/verification.md`.

### HARD REJECTION
- Any day missing from backup inventory.
- Restore dry run fails smoke tests.
- RPO > 24h.
- RTO > 4h.
- Multi-region mirror missing or live-replication broken.
- Audit chain integrity verifying against last 30 days fails.

### EVIDENCE
- Write 12-section evidence to `docs/setup-evidence/society-dr/evidence/verification.md`.
- Backup inventory at `docs/setup-evidence/society-dr/evidence/backup-inventory.csv`.
- Auditor gate at `docs/setup-evidence/society-dr/evidence/auditor-gate.md`.

---

## Prompt 12: Society Scale-Out

### GOAL
Detect the scale-out trigger (>32 cores / 64GB aggregate OR sustained >70% sustained
load for 7 days), implement multi-VPS federation, load balance bot workers, and
prove cross-VPS communication equivalence to single-VPS behavior.

### SCOPE
- IN: VPS resource monitoring (cgroup + node_exporter), scale-out trigger logic,
  multi-VPS federation pattern (Tailscale/WireGuard), cross-VPS Redis pub/sub bridge,
  load-balanced bot worker scheduling, federation-aware governance lookup.
- OUT: Cross-region DR, new revenue channels, new mutation tiers.

### PREREQUISITES
- P36 observability stack PASS.
- Federation tooling chosen (Tailscale ACLs or WireGuard mesh) with keys in sops.
- PASS: federation probe reaches peer VPS in < 50ms.

### IMPLEMENTATION STEPS
1. **Resource monitor** — node_exporter + per-Hermes cgroup exporters; aggregate
   metrics per society: total cores, total RAM, sustained CPU%.
2. **Scale-out trigger** — `trigger_scale_out` evaluates:
   (a) cores > 32 AND RAM > 64GB (collectively), OR
   (b) sustained CPU/load > 70% for 7 days window.
   Emits governance event T3 (2/2 founder) for additive VPS provisioning.
3. **Federation pattern** — second VPS joins via Tailscale ACLs (or WireGuard);
   federation topology documented in `runbooks/federation.md`; mTLS for all
   cross-VPS calls.
4. **Cross-VPS pub/sub** — Redis pub/sub bridge between VPS-A and VPS-B; heartbeats
   and audit summaries flow over bridge; failures on bridge trigger HARD STOP on
   affected VPS.
5. **Load-balanced workers** — bot workers register with scheduler on federation;
   scheduler distributes slash commands + heartbeat; pinned-to-VPS-only hermes
   can override.
6. **Federation-aware governance** — governance validator consults local registry
   first; on miss, queries peer VPS via signed RPC; signer mismatch = reject.
7. **Cross-VPS equivalence test** — replay canonical Hallmark scenarios across VPS-A,
   VPS-B, and federation; verify identical outcomes (heartbeat, recall, governance,
   consent revocation, HARD STOP).
8. **Report** — single markdown at
   `docs/setup-evidence/society-scale-out/evidence/verification.md` with measured
   latency, throughput, and equivalence suite results.

### FORBIDDEN PATTERNS
- Cross-VPS RPC without mTLS or signed request.
- Federation key in plaintext (always in sops).
- Empty catch on bridge failure.
- Load balancer preferring latency at cost of governance or safety.
- Bypassing HARD STOP for "federation-induced" outage.

### EXIT CRITERIA
- Scale-out trigger logic fires only on (a) or (b), never on both false.
- Federation probe < 50ms p95 across peers.
- Bridge failure test triggers HARD STOP within 5s.
- Federation-aware governance rejects mismatched signer.
- Equivalence suite: all hallmark scenarios identical outcomes.
- 12-section evidence at
  `docs/setup-evidence/society-scale-out/evidence/verification.md`.

### HARD REJECTION
- Federation established before governance + HARD STOP primer PASS.
- Cross-VPS RPC missing mTLS or signer.
- Bridge failure not propagating HARD STOP.
- Equivalence suite failing scenario on federation (different outcome vs single-VPS).
- Trigger scale-out firing on misconfigured thresholds (cores ≤ 32 OR RAM ≤ 64).

### EVIDENCE
- Write 12-section evidence to
  `docs/setup-evidence/society-scale-out/evidence/verification.md`.
- Federation topology at `runbooks/federation.md` referenced in evidence.
- Trigger-config at `docs/setup-evidence/society-scale-out/evidence/trigger-config.json`.
- Auditor gate at `docs/setup-evidence/society-scale-out/evidence/auditor-gate.md`.

<!-- ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. -->
<!-- ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt. -->

---

## Pack Footer

This prompt pack is **not** a plan — it is a tool. Sub-agents receive ONE prompt,
execute the steps, and produce a 12-section evidence file at the path the prompt
specifies. Parents decompose by phase, never bundle multiple prompts into one
sub-agent, and never accept a "done" claim without re-running the scaffold
commands themselves.

All locked decisions from Faiz apply across every prompt unless an individual
prompt explicitly overrides (none in this pack).

Next action: bootstrap phase wiring → P28 implementation kickoff per
`docs/setup-evidence/P28/` evidence root.
