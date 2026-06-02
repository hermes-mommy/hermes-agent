# ADR Batch 2 — External Technical Sanity Report

**Date**: 2026-05-30  
**Scope**: Five infrastructure assumptions for Guinevere ADR batch 2  
**Sources**: Web research on pgvector, systemd/cron, Tailscale, Baileys/WhatsApp, Gmail API/Resend/Gotify, Android notification capture  
**Status**: Research-only; no project files modified  

---

## 1. PostgreSQL pgvector + OpenAI text-embedding-3-small

**Verdict: PLAUSIBLE with scale caveats**

pgvector on Postgres is a common pattern for semantic search up to a few million rows. OpenAI `text-embedding-3-small` produces 1536-dimensional vectors, which is well-supported.

**Caveats for reviewer notes:**

- **Fixed dimension per column.** pgvector enforces dimension count at write time. A column defined as `VECTOR(1536)` cannot accept 384-dimension vectors. Changing dimensions later requires table rebuild (`ADD COLUMN → backfill → drop old`). If multiple embedding models are needed, use separate columns or separate tables per model ([source](https://dbadataverse.com/tech/postgresql/2026/05/pgvector-gotchas-dimension-mismatch-casting-errors-and-alter-table-solved-2026)).
- **HNSW index is required for production scale.** Without an index, pgvector does sequential scans. Below a few hundred rows this is correct behavior; above that, an HNSW index is needed. The index requires tuning: `m=16` is a reasonable default for 1536-dim vectors; `m=32`–`64` for 1M–10M+ rows. `ef_construction` should be set to 128–256 during build for better graph quality ([source](https://shahvatsal.com/blog/pgvector-scaling-2026), [source](https://markaicode.com/integrate/openai-api-with-pgvector/)).
- **Memory-bound failure mode.** HNSW indexes require random-access reads that do not map well to traditional caching. At 1M–10M vectors, the index must fit in RAM or queries degrade to disk I/O, which also starves the relational workload. `halfvec` (16-bit floats) cuts memory roughly in half with <1% recall loss for `text-embedding-3-small` and buys significant runway ([source](https://ravoid.com/blog/pgvector-scaling-issues)).
- **Autovacuum bloat.** High-churn embedding workloads accumulate dead tuples. Vector indexes are slow to vacuum; without tuned autovacuum per table, index quality degrades silently ([source](https://ravoid.com/blog/pgvector-scaling-issues)).
- **Query pattern is strict.** The query must have `ORDER BY embedding <=> query_vector LIMIT N` with the matching operator class (`vector_cosine_ops`). Missing `ORDER BY ... LIMIT` causes index non-use ([source](https://dbadataverse.com/tech/postgresql/2026/05/pgvector-gotchas-dimension-mismatch-casting-errors-and-alter-table-solved-2026)).
- **OpenAI rate limits apply.** Batch embeddings (up to 100 per call) with exponential backoff. A token-bucket rate limiter is recommended. Rate limit errors return HTTP 429 and can stall embedding pipelines ([source](https://markaicode.com/integrate/openai-api-with-pgvector/)).
- **Managed Postgres support is broad.** AWS RDS (15.2+), Supabase, and Neon support pgvector. Rebuilding indexes after major PG upgrades requires re-running `CREATE EXTENSION vector` and re-indexing.

**Acceptance note:** Specify `vector(1536)` with `halfvec` migration plan, HNSW index parameters, autovacuum tuning, and an OpenAI rate-limit retry strategy in the implementation spec.

---

## 2. Self-deploy via cron + git pull on Ubuntu/systemd

**Verdict: PLAUSIBLE, but missing CI/CD safety nets**

Running `git pull && systemctl restart app` from cron is a valid self-hosted deploy primitive. systemd timers are the modern replacement for cron on systemd-based Linux, offering journald logging, `Persistent=true` catch-up on reboot, and dependency management ([source](https://thelinuxclub.com/systemd-timers-the-modern-cron-replacement-complete-setup-and-migration-guide-2026/)).

**Caveats for reviewer notes:**

- **No automated rollback.** A bad deploy via `git pull` leaves the repo at the broken commit. There is no built-in mechanism to detect failure and revert. A wrapper script must check health endpoint or exit code and revert manually.
- **No artifact/test gate.** GitHub Actions CD runs lint, tests, and builds before deploy. A cron/git-pull script runs the pull regardless of CI state. The deploy happens before verification unless the script explicitly gates on a remote health check.
- **Merge conflicts break the pull.** If the remote has diverged (force-push, or local changes), `git pull` hangs or fails. Non-interactive deploy scripts need `git fetch && git reset --hard origin/main` semantics, which discard local changes unconditionally.
- **Secrets handling.** `DEPLOY_SSH_KEY` or similar must be stored on the server (file, systemd credential, or environment). This is a different trust boundary than GitHub Actions secrets. Rotation is manual.
- **Partial deploy window.** During `git pull` + `systemctl restart`, the service is briefly down. Rolling restarts (blue/green or multiple units) require additional orchestration.
- **GitHub Actions cron unreliability is a real driver.** GitHub explicitly warns that scheduled workflows can be delayed or dropped during high load, with minimum 5-minute spacing. A self-hosted timer avoids this, but trades it for single-node reliability ([source](https://mylinux.work/guides/github-actions-for-sysadmins/), [source](https://stackoverflow.com/questions/79534419/reliability-issues-with-github-actions-with-cron-based-schedule)).
- **Log fragmentation.** Cron output goes to syslog or mail; systemd timers capture stdout/stderr in journald automatically, which is significantly better for debugging deploy failures ([source](https://thelinuxclub.com/systemd-timers-the-modern-cron-replacement-complete-setup-and-migration-guide-2026/)).

**Acceptance note:** Document the exact deploy script (fetch + reset + health check + rollback), the secret storage mechanism, and the difference from CI-gated deploys. Consider whether "self-deploy" truly replaces CD or only supplements it for latency-sensitive hotfixes.

---

## 3. Tailscale mesh with zero public admin ports

**Verdict: PLAUSIBLE for internal access, with topology caveats**

Tailscale creates a WireGuard-based mesh where no public admin ports need to be open. Access is authenticated via the tailnet ACL and identity provider. This is a legitimate architecture for zero-exposure internal management.

**Caveats for reviewer notes:**

- **DERP relay fallback throttles throughput.** When direct WireGuard cannot be established (symmetric NAT, CGNAT, restrictive firewalls), traffic falls back to Tailscale's shared DERP relays. Effective throughput is 30–100 Mbps in practice. This is adequate for SSH, HTTP admin, and small transfers; it is not adequate for backup traffic, large file sync, or high-throughput replication ([source](https://www.bigiron.cc/guides/tailscale-subnet-router-vs-relay-vs-exit-node)).
- **UDP/41641 outbound must be permitted.** Tailscale requires outbound UDP on 41641 (WireGuard) and 3478 (STUN). If both ends block UDP, DERP is the only path. Some corporate networks and mobile carriers block UDP entirely ([source](https://www.xda-developers.com/tailscale-hides-your-networking-knowledge-until-something-breaks/)).
- **Control plane is proprietary and US-hosted.** Tailscale's coordination server runs on AWS in the United States. Metadata (who connects to whom, not content) is processed there. As of May 2026, no EU region is selectable. Self-hosting the control plane is not officially supported; Headscale is the community alternative with its own maintenance burden ([source](https://www.infralovers.com/blog/2026-05-15-tailscale-mesh-vpn-market-leader/)).
- **Data residency and compliance.** For NIS2/DORA contexts, the US-hosted metadata processing requires additional vendor assessment. Tailnet Lock softens control-plane trust but does not relocate metadata ([source](https://www.infralovers.com/blog/2026-05-15-tailscale-mesh-vpn-market-leader/)).
- **Device key expiry defaults to 180 days.** Servers joining the tailnet need re-authentication after expiry unless disabled in the admin console. Automated/headless nodes require an auth key with appropriate expiry settings.
- **Subnet routing still respects upstream firewalls.** Tailscale does not bypass AWS security groups, cloud NACLs, or host firewalls. If a database is in a VPC, the subnet router's security group must be added to the database's inbound rules ([source](https://yaw.sh/blog/tailscale-aws-practical-guide-gotchas/)).
- **Overlapping CIDRs break routing.** If two sites advertise the same CIDR (e.g., both use `10.0.0.0/16`), Tailscale routes to one arbitrarily. Plan non-overlapping subnets across all tailnet members.
- **Not for public service exposure.** Tailscale is for private access. To expose an admin or API endpoint to the public internet, Tailscale Funnel or a separate reverse proxy/Cloudflare Tunnel is required ([source](https://www.bigiron.cc/guides/tailscale-subnet-router-vs-relay-vs-exit-node)).

**Acceptance note:** Clarify whether "zero public admin ports" means "no inbound ports opened on routers" (true with Tailscale) or "no public IP at all" (tailnet metadata still touches US control plane). Document fallback behavior if DERP becomes the only path.

---

## 4. WhatsApp via Baileys, Gmail API + Resend, Gotify push backup

**Verdict: PLAUSIBLE but operationally fragile**

This is a multi-provider notification stack. Each component works individually; the combined reliability depends on the weakest link.

### 4a. WhatsApp via Baileys

Baileys is an unofficial, reverse-engineered WebSocket client for WhatsApp Web. It works, but carries ongoing risk.

**Caveats:**

- **Unofficial API.** Baileys is not endorsed by Meta/WhatsApp. Accounts can receive 463 errors (timelock/restriction), 428 errors (new chat limits), or face bans. The library explicitly handles these, but they remain operational risks ([source](https://github.com/WhiskeySockets/Baileys/releases/tag/v7.0.0-rc10), [source](https://github.com/WhiskeySockets/Baileys/issues/2337)).
- **v7 is still RC as of May 2026.** The latest stable was v6; v7.0.0-rc.10 was released May 2026 after a 5-month gap. Production use requires pinning a specific RC and accepting that the API surface may change ([source](https://github.com/WhiskeySockets/Baileys)).
- **"Deaf session" bug.** Sessions can silently stop receiving messages while the WebSocket appears healthy. The root cause is a mutex holding the ACK inside message processing; if Redis or any key store operation hangs, the session stops receiving. Workarounds require health monitors that force-reconnect after N minutes of silence ([source](https://github.com/WhiskeySockets/Baileys/issues/2491)).
- **Memory leaks and reconnect storms.** Multi-session deployments (30+ sessions) have documented memory pressure. The `baileys-antiban` wrapper is a community mitigation, not an upstream guarantee ([source](https://github.com/WhiskeySockets/Baileys/issues/2337)).
- **Session state is file-based by default.** Using Redis (`makeCacheableSignalKeyStore`) is recommended for multi-process deployments, but introduces a single shared mutex bottleneck.
- **No SLA.** There is no vendor to call. Breakage is fixed by community PRs and workarounds.

**Acceptance note:** If WhatsApp is a critical path (not just a backup), document the escalation path when Baileys fails: manual QR re-scan, session recreation, or fallback to alternative notification channels. Pin the RC version and subscribe to releases.

### 4b. Gmail API

Gmail API is stable, well-documented, and production-grade for reading and sending mail.

**Caveats:**

- **Quota is per-project and per-user.** As of May 2026: 1,200,000 quota units/minute per project, 6,000/minute per user. A `messages.send` costs 100 units. A support agent handling 200 tickets/day with 3 reads + 1 send per ticket consumes ~33,000 units/day—well within limits, but burst patterns need backoff ([source](https://cli.nylas.com/guides/gmail-api-quotas-2026)).
- **Push notifications require re-watching every 7 days.** The `watch()` call expires. A cron or systemd timer must re-establish the watch daily or weekly, or notifications stop silently. Also capped at 1 event/second per user, with possible drops under burst conditions ([source](https://developers.google.com/workspace/gmail/api/guides/push)).
- **Sending limits are per-user, not per-project.** Free Gmail accounts: ~500 messages/day. Workspace accounts: higher but still bounded. 429 errors can persist for hours after limit hit. A production system must handle 429 with exponential backoff and queue deferred sends ([source](https://developers.google.com/workspace/gmail/api/guides/handle-errors)).

### 4c. Resend

Resend is a transactional email API. Rate limits and reputation rules are strict.

**Caveats:**

- **Rate limit: 5 req/sec by default.** Bursts above this receive 429. Batch API allows up to 100 emails per request (counts as 1 request). High-volume spikes require pre-arranged limit increases ([source](https://resend.mintlify.dev/docs/knowledge-base/account-quotas-and-limits)).
- **Bounce rate must stay under 4%; spam rate under 0.08%.** Violations pause sending until rates recover. Monitor via webhooks or the Metrics page.
- **Hard overage cap: 5× monthly quota.** After that, sending pauses until the next billing cycle. No unlimited burst beyond this.

### 4d. Gotify push backup

Gotify is a self-hosted push notification server. It is operationally independent of the other providers, which makes it a good fallback—but it is not free of operational cost.

**Caveats:**

- **Self-hosted means self-operated.** The operator must handle updates, backups (Docker volumes or SQLite dumps), TLS termination, and availability. There is no SaaS fallback.
- **No iOS app.** Gotify has an Android app but no native iOS client. Web push on iOS is limited.
- **Backup discipline.** Named Docker volumes must be backed up to remote storage. A tested restore procedure is required; untested backups are not a recovery strategy ([source](https://ossalt.com/guides/how-to-self-host-gotify-push-notifications-2026)).
- **Exposing to the internet requires a reverse proxy.** Internal ports should bind to localhost only. Caddy/Nginx handles HTTPS termination, rate limiting, and access logging ([source](https://ossalt.com/guides/how-to-self-host-gotify-push-notifications-2026)).

**Acceptance note:** The stack is technically coherent but the WhatsApp/Baileys leg is the highest-risk component. Resend and Gotify are reliable at low-medium volume. Gmail API is reliable within quota. Document the retry/fallback chain explicitly: if Baileys fails, does Gotify compensate fully, or are some notification types lost?

---

## 5. Android Tasker notification capture for e-wallet; bank transaction aggregation without scraping

**Verdict: PLAUSIBLE for personal use, high maintenance for production**

Notification capture via Android's `NotificationListenerService` is a well-established pattern for expense tracking. It avoids `READ_SMS` permission entirely and works on user-visible notifications only.

**Caveats for reviewer notes:**

- **Android 14+ foreground service restrictions.** A notification listener that must survive app-kill (swipe-away) requires a foreground service declared with `FOREGROUT_SERVICE_SPECIAL_USE` and `tools:replace="android:stopWithTask"`. Google Play requires a video demonstration and written justification for this permission. Apps using it are unlikely to pass Play Store review without being a default SMS/messaging app ([source](https://medium.com/@owinojumahjerome/how-i-built-a-privacy-first-auto-expense-tracker-in-flutter-without-the-read-sms-api-6c7c66d56af5)).
- **Battery optimization is aggressive.** Android kills background listeners. The user must manually set battery optimization to "Unrestricted" for the app. This is a per-device, per-user configuration step that cannot be automated programmatically on all OEM skins.
- **Regex parsing is fragile.** Bank and e-wallet notification text changes with app updates, language settings, and transaction types. Each bank/e-wallet requires a maintained adapter. No standard schema exists; parsers break silently when notification text changes ([source](https://github.com/jojoclt/ExpenseCC), [source](https://github.com/indra7777/SpendWise)).
- **Not all transactions generate notifications.** Refunds, failed transactions, reversed payments, and some offline/cash-mode e-wallet flows may not produce notifications. Credit-to-account notifications (inflows) are common and must be filtered out explicitly if only debits are wanted.
- **No guarantee of completeness.** Deferred notifications (phone was off, notification posted late) may arrive in batches. The listener may miss notifications posted while the device is in Doze mode or the app is force-stopped.
- **Notification access is a sensitive permission.** The user must manually enable it in Android Settings → Special Access → Notification Access. This is a single gate: once granted, the app can read every notification from every app. Users may be unwilling to grant this for a non-PLAY-distributed app.
- **Duplicate detection is required.** The same transaction may appear in both SMS and notification channels, or as multiple notifications (e.g., "payment initiated" + "payment completed"). A deduplication layer (transaction ID, amount + timestamp + merchant) is necessary before aggregation.
- **Sideloading is the realistic distribution path.** Play Store compliance for a notification-listening app with foreground service + special use is difficult. Users must enable "Install unknown apps" for the distribution channel (APK, Firebase App Distribution, etc.).

**Acceptance note:** If the ADR assumes "notification capture works for all e-wallet signals," that assumption is too strong. It works for many popular apps (GPay, PhonePe, Paytm, major banks) but requires per-app regex adapters and ongoing maintenance. Bank transaction aggregation without scraping is feasible, but the completeness guarantee depends on notification availability, not data access. The aggregator must handle duplicates, deferred notifications, and missing notifications explicitly.

---

## Summary Table

| # | Assumption | Verdict | Highest-Risk Caveat |
|---|---|---|---|
| 1 | pgvector + text-embedding-3-small | Plausible | Memory-bound at 5M+ vectors; requires halfvec + HNSW tuning |
| 2 | cron + git pull self-deploy | Plausible | No automated rollback or test gate; manual secret management |
| 3 | Tailscale mesh, zero public ports | Plausible | DERP fallback throttles to 30–100 Mbps; US-hosted metadata |
| 4 | Baileys + Gmail + Resend + Gotify | Plausible | Baileys is unofficial, v7 RC, and has deaf-session bugs |
| 5 | Tasker notification capture | Plausible | Regex fragility; Play Store compliance difficult; incomplete coverage |

**Overall assessment:** All five assumptions are technically achievable in 2026. None are trivial. The two that need the most explicit mitigation planning are Baileys (unofficial API instability) and Tasker notification capture (maintenance burden + completeness gaps).
