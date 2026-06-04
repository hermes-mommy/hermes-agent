# P13 — X Auto Poster: Enterprise Requirements Specification

> **Phase:** P13 (Expansion)
> **Dependencies:** P5 (Agent Loop), P6 (MCP Tools), P7 (Surveillance), P8 (Observability)
> **Status:** Requirements Finalized (60 Q&A across 10 rounds)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Windows (Faiz)           │       VPS (Guinevere)    │
│                           │                          │
│  Watchdog ──S3 upload──►  │  /pending/ ──► /processing/ │
│  (folder)                 │       │                      │
│                           │  ┌────┴─────┐               │
│                           │  │ Caption  │               │
│                           │  │ Pipeline │               │
│                           │  │ (Gemini) │               │
│                           │  └────┬─────┘               │
│                           │       │                      │
│                           │  ┌────┴─────┐               │
│                           │  │ X Post   │               │
│                           │  │ Engine   │               │
│                           │  │ (Obscura │               │
│                           │  │  9223)   │               │
│                           │  └────┬─────┘               │
│                           │       │                      │
│                           │  ┌────┴─────┐  /posted/     │
│                           │  │ Outcome  ├──► /failed/    │
│                           │  │          ├──► /held/      │
│                           │  └──────────┘               │
│                           │                          │
│  Discord ◄──── status ◄──┤  Notifications            │
└─────────────────────────────────────────────────────┘
```

---

## 2. Queue & Storage

### 2.1 Source → S3 Pipeline
- **Mechanism:** Windows watchdog script (`watchdog` library) monitors a local folder
  - Detects new files via `watchdog.events.FileCreatedEvent`
  - Auto-uploads to S3 `guinevere-assets/x-poster/pending/` via boto3
  - Supports JPG/PNG/WEBP only for MVP
- **Naming:** `YYYY-MM-DD_HHmmss_uuid.jpg`
- **Sidecar JSON:** Same basename with `.meta.json` extension, uploaded alongside image
- **Startup behavior:** Queue waits for heartbeat cycle, no immediate drain on startup

### 2.2 S3 Prefix State Machine

| State | Prefix | TTL | Action After TTL |
|-------|--------|-----|-------------------|
| Pending | `/pending/` | — | Polled next cycle |
| Processing | `/processing/` | 30 min | Move back to `/pending/` |
| Posted | `/posted/` | 90 days | Archive to `/archived/` |
| Failed | `/failed/` | 7 days | Archive to `/archived/` |
| Held | `/held/` | Indefinite | Awaiting manual re-auth |

- **Queue discipline:** FIFO (oldest first), 1 post per heartbeat cycle
- **No priority system** for MVP
- **Polling:** Python asyncio loop with boto3 `list_objects_v2` prefix filter

### 2.3 Sidecar JSON Format

```json
{
  "caption": "string | null",
  "custom_alt": "string | null",
  "schedule": "immediate | 2026-06-04T08:00:00+07:00",
  "tone": "professional | casual | auto",
  "language": "id | en | auto",
  "tags": ["hashtag1", "hashtag2"],
  "skip_llm": false
}
```

| Field | Behavior |
|-------|----------|
| `caption` | If non-null → use as tweet text. If null → LLM generate |
| `custom_alt` | If non-null → use as alt text. If null → LLM generate |
| `schedule` | `"immediate"` bypasses interval + night mode |
| `tone` | `"auto"` → detect from image content via LLM |
| `language` | `"auto"` → detect from content. Default: `"en"` |
| `tags` | Override LLM-generated hashtags. Empty array = no hashtags |
| `skip_llm` | `true` → skip LLM caption gen, post with `caption` field as-is |

---

## 3. Scheduling & Rate Limiting

### 3.1 Heartbeat
- **Type:** Minimum interval (not exact schedule)
  - If last post was at 09:00 and image uploaded at 10:30 → post 10:30
  - If last post was at 09:00 and image uploaded at 11:00 → post 11:00
- **Interval:** Minimum 3 hours between consecutive posts
- **Max posts/day:** 5 (self-limit, X allows ~50)
- **Cycle drain:** Exactly 1 post per heartbeat cycle (never drain entire queue)

### 3.2 Night Mode
- **Window:** 23:00-06:00 WIB
- **Behavior:** Queue is held (not skipped). Posts resume next cycle after 06:00
- **Override:** `"schedule": "immediate"` bypasses night mode

### 3.3 Immediate Post
- Sidecar `"schedule": "immediate"` bypasses:
  - Minimum 3h interval
  - Night mode window
  - Current queue position (goes to front)
- **Rate limit still applies** — immediate post counts toward 5/day cap

---

## 4. Caption Pipeline

### 4.1 LLM Configuration
| Parameter | Value |
|-----------|-------|
| Primary model | Gemini Flash (cost-optimized) |
| Fallback model | Gemini Pro (if Flash fails) |
| Provider | Existing LLMRouter (9Router) |
| Output mode | Structured JSON via `responseSchema` |

### 4.2 Generation Strategy

| Output | Source | Character Limit |
|--------|--------|-----------------|
| Tweet caption | Sidecar `caption` field OR LLM generate | 280 chars |
| Alt text | Sidecar `custom_alt` field OR LLM generate | Max 125 chars |
| Hashtags | LLM generate OR sidecar `tags` override | Max 3 |
| Tone | Sidecar `tone` OR auto-detect from content | — |

### 4.3 Content Distinction
- **Alt text:** Pure visual description for accessibility. Neutral, factual, detailed.
- **Tweet caption:** Engaging text in Guinevere's voice. Contextual, may include emojis, call-to-action.
- **Hashtags:** Relevant keywords, max 3. Generated by LLM or overridden via sidecar.

### 4.4 Content Moderation
- LLM scans image + generated caption for unsafe content
- **Block triggers:** NSFW, violence, hate speech, personal identifiable info (PII)
- **On block:** Move to `/failed/` with reason `"content_blocked"` + Discord notification
- **No auto-blur or redaction** for MVP — Faiz responsible for content filtering

### 4.5 Fallback Chain
1. Sidecar `caption` field (if non-null) → use as-is, skip LLM generation
2. LLM generate caption (Gemini Flash)
3. If Flash fails → Gemini Pro
4. If both fail → generic caption fallback (e.g., "📸 New post from Guinevere")
5. Never fail the post just because caption LLM fails

---

## 5. X Session & Authentication

### 5.1 Cookie Management
- **Storage:** SOPS-encrypted (existing ADR-016 pattern)
  - Keys: `auth_token`, `ct0`, `kdt`
  - Reuse existing age key (no dedicated key for MVP)
- **Persistence:** Obscura `--storage-dir` dedicated for X (port 9223)
  - Browser context saved between restarts
  - Session survives VPS reboots via storage-dir
- **Setup flow:** Faiz manually exports cookies from laptop browser → SOPS encrypts → syncs to VPS

### 5.2 Session Lifecycle
| Stage | Action |
|-------|--------|
| Startup | Decrypt SOPS → inject cookies into Obscura context via CDP `Network.setCookie` |
| Pre-post | Session health check (navigate to x.com, check page title/URL ≠ login) |
| Healthy | Proceed with posting |
| Expired | Move queue to `/held/` → Discord alert → Faiz manual re-auth |
| Recovery | Faiz re-exports cookies, re-encrypts, VPS picks up new session |

### 5.3 Session Health Check
Performed before every single post:
1. Navigate to `https://x.com/home` via CDP
2. Wait for page load (DOM `document.readyState === 'complete'`)
3. Check URL is not `https://x.com/login` or `https://x.com/i/flow/login`
4. Check page does not contain "Sign in to X" or "Enter your password"
5. If healthy → proceed. If not → session expired → /held/ + alert

### 5.4 Account Configuration
- **Single X account** for MVP (Guinevere)
- Multi-account support post-launch
- Account-level sensitive content setting already configured on X side

---

## 6. X Posting Engine (CDP via Obscura)

### 6.1 Obscura Configuration
| Parameter | Value |
|-----------|-------|
| Port | 9223 (dedicated, NOT shared with MCP tools on 9222) |
| Stealth | `--stealth` enabled |
| Storage dir | Dedicated `--storage-dir` for X session persistence |
| Workers | 1 (single sequential posting) |
| Resource | 256MB RAM target |

### 6.2 Posting Flow
1. **Session check** → verify logged in
2. **Navigate** to `https://x.com/compose/post` or click "Post" button
3. **Media upload** → CDP file input → `input[data-testid="fileInput"]` → attach image file
4. **Wait for media** → verify thumbnail appears (max 10s)
5. **Text input** → `div[data-testid="tweetTextarea_0"][contenteditable]`
   - Primary: `page.locator('[data-testid="tweetTextarea_0"]').fill(caption)`
   - Fallback: CDP `Input.insertText` if fill() fails
   - Fallback 2: Clipboard paste
6. **Alt text** → click "Add description" → fill alt text field
7. **Post** → click `button[data-testid="tweetButtonInline"]`
8. **Verify success** → check for "Your post was sent" toast or timeline redirect
9. **Move S3 object** → `/pending/` → `/posted/` or `/failed/`

### 6.3 Media Constraints
| Constraint | Value |
|------------|-------|
| Max images per post | 4 |
| Max file size per image | 5MB |
| Supported formats | JPG, PNG, WEBP |
| Video/GIF | Post-launch |

### 6.4 Dry-Run Mode
- `/x-dryrun` — simulates full pipeline without actual X post
- Steps: session check ✓, caption gen ✓, media prep ✓, rate limit check ✓
- Skip: CDP compose navigation, tweet button click, S3 state transition
- Output: Discord embed with generated caption + alt text for review

---

## 7. Error Handling & Recovery

### 7.1 Error Classification

| Error Type | Action | Retry? |
|------------|--------|--------|
| Network error (connection timeout, DNS failure) | Retry with backoff | Yes (3x) |
| X rate limit hit (429 / too many requests) | Skip post, queue returns to `/pending/` for next day | No retry same day |
| DOM change (selector not found, page structure changed) | Notify Discord + pause all posting | No retry |
| Media upload fail (file too large, format rejected) | Retry media upload only, keep caption | Yes (3x) |
| Caption LLM error (API timeout, invalid response) | Use generic caption fallback | No retry |
| Session expired (health check failed) | Move to `/held/` + Discord alert | Manual |
| Corrupt file (unreadable image, 0-byte, invalid format) | Move to `/failed/` reason "corrupt_file" | No |
| Content blocked (LLM moderation triggered) | Move to `/failed/` reason "content_blocked" + notify | No |

### 7.2 Retry Policy
| Retry | Delay |
|-------|-------|
| 1st | 30 seconds |
| 2nd | 2 minutes |
| 3rd | 5 minutes |
| After 3rd | Move to `/failed/` + notify |

### 7.3 Circuit Breaker
- **Trigger:** 5 consecutive posting failures (any post, any error type)
- **Action:** Auto-pause queue, send Discord alert
- **Recovery:** Manual `/x-resume` command (after Faiz investigates)
- **Alert cooldown:** 30 minutes between consecutive failure alerts

### 7.4 Processing Timeout
- **Timeout:** 30 minutes from `/pending/` → `/processing/` move
- **Action:** Move object back to `/pending/` for retry
- **Use case:** VPS crash during processing, power outage, etc.

### 7.5 Partial Failure Recovery
- **Caption ok, post failed:** Move back to `/pending/` (keep generated caption in sidecar)
- **Media uploaded, post failed on tweet button:** Move back to `/pending/`
- **Caption failed, post would have been ok:** N/A (post not attempted if LLM fallback used)

---

## 8. Discord Integration

### 8.1 Notification Channels

| Event | Channel | Format |
|-------|---------|--------|
| Successful post | `#guinevere-status` | Embed: tweet preview + X link + metrics |
| Failed post | `#guinevere-status` | Embed: error reason + filename + retry count + next retry |
| Content blocked | `#guinevere-alerts` | Embed: filename + moderation reason |
| Session expired | `#guinevere-alerts` | Embed: action needed (manual re-auth requested) |
| Circuit breaker | `#guinevere-alerts` | Embed: 5 consecutive failures, queue paused |
| Queue > 10 | `#guinevere-status` | Warning: queue depth growing |
| 0 posts in 24h | `#guinevere-status` | Warning: no activity detected |
| Daily summary | `#guinevere-status` | Daily 20:00 WIB: X posted, Y failed, Z pending |

### 8.2 Discord Commands

| Command | Description | Auth |
|---------|-------------|------|
| `/x-status` | Queue depth, last post time, daily count, session health, next scheduled | Faiz only |
| `/x-list` | List pending queue (filename, age, estimated post time) | Faiz only |
| `/x-cancel <filename>` | Cancel specific pending post, move to `/failed/` | Faiz only |
| `/x-hold` | Pause all posting | Faiz only |
| `/x-resume` | Resume posting after hold or circuit breaker | Faiz only |
| `/x-edit <filename> "new caption"` | Override caption before post | Faiz only |
| `/x-delete <post_id>` | Delete already-posted tweet via CDP browser UI | Faiz only |
| `/x-retry-failed` | Retry all posts in `/failed/` | Faiz only |
| `/x-retry <filename>` | Retry specific failed post | Faiz only |
| `/x-dryrun <filename>` | Simulate post without actual tweet | Faiz only |

### 8.3 Post Notification Embed Format
```
📸 **X Post — Success**
━━━━━━━━━━━━━━━━━━━━
**Caption:** "First 100 chars..."
**Hashtags:** #Guinevere #AI #Dev
**Alt:** [auto-generated alt text]
**Images:** 3
**Latency:** 12.4s
**Posted:** 2026-06-03 14:30:00 WIB
━━━━━━━━━━━━━━━━━━━━
🔗 [View on X](https://x.com/guinevere/status/...)
```

---

## 9. Monitoring & Observability

### 9.1 Grafana Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `p13_posts_total` | Counter | — | Total post attempts |
| `p13_posts_success` | Counter | — | Successful posts |
| `p13_posts_failed_total` | Counter | `reason` | Failed posts by reason |
| `p13_queue_depth` | Gauge | `state` | Queue depth by state (pending/processing) |
| `p13_session_expired` | Gauge | — | 1 if session expired, 0 if healthy |
| `p13_heartbeat_lag_seconds` | Histogram | — | Time since last post |
| `p13_caption_generated_total` | Counter | — | Captions generated by LLM |
| `p13_content_blocked_total` | Counter | — | Posts blocked by moderation |

### 9.2 Per-Post Logging
Each post log record (PostgreSQL, reuse P3 episode storage):
- `timestamp`: When post was attempted
- `image_key`: S3 object key  
- `caption_length`: Number of characters in caption
- `post_status`: success / failed / blocked
- `latency_ms`: Total time from /processing/ to outcome
- `session_age_hours`: Hours since last session refresh
- `error_reason`: If failed (nullable)
- `retry_count`: Number of retry attempts (0-3)

### 9.3 Log Retention
- **Duration:** 90 days in PostgreSQL
- **After 90 days:** Archive or delete (consistent with P7 retention policy)

---

## 10. Operations

### 10.1 Systemd Service

**File:** `/etc/systemd/system/guinevere-x-poster.service`

| Parameter | Value |
|-----------|-------|
| Type | `exec` |
| User | `guinevere` |
| Slice | `guinevere.slice` |
| Obscura port | `9223` (dedicated) |
| RAM target | 256MB max |
| Dependencies | `postgresql.service`, `obscura@9223.service` (or similar) |

### 10.2 IAM/S3 Configuration
| Resource | Value |
|----------|-------|
| Bucket | Existing Guinevere S3 bucket |
| Prefix | `guinevere-assets/x-poster/` |
| Credentials | Dedicated IAM credentials scoped to prefix |
| Encryption | SSE-S3 default (MVP). SSE-KMS post-launch |
| Versioning | Enabled for posted images |
| Cross-region backup | Not for media files (too expensive). Text logs only → R2 |

### 10.3 Alert Configuration

| Alert Rule | Threshold | Channel | Cooldown |
|------------|-----------|---------|----------|
| Consecutive failures | ≥3 in a row | Discord `#guinevere-alerts` | 30 min |
| Session expired | =1 (true) | Discord `#guinevere-alerts` | Until resolved |
| Queue depth | >10 pending | Discord `#guinevere-status` | 1 hour |
| Zero posts in 24h | True | Discord `#guinevere-status` | 24h |
| Fallback: Gotify | Critical alerts only | Gotify (existing P2) | Same as Discord |

---

## 11. Acceptance Criteria

### AC-POSTING-001: Queue Flow
Upload image + sidecar → auto-queued to `/pending/`
→ `/processing/` → caption generated → posted → `/posted/`

### AC-POSTING-002: Rate Limiting
Max 5 posts/day, minimum 3h interval, night mode respected

### AC-POSTING-003: Immediate Post
`"schedule": "immediate"` bypasses interval + night mode

### AC-POSTING-004: Error Recovery
Network error → retry 3x (30s/2m/5m). Rate limit → skip. DOM change → pause.

### AC-POSTING-005: Session Management
SOPS cookie injection → health check before each post → expiry → /held/ + notify

### AC-POSTING-006: Caption Pipeline
Hybrid caption: sidecar first, LLM fallback. Alt text separate. Content moderation blocks unsafe.

### AC-POSTING-007: Discord Commands
All 10 commands functional: status, list, cancel, hold, resume, edit, delete, retry-failed, retry, dryrun

### AC-POSTING-008: Monitoring
All 8 metrics exposed. Daily summary 20:00 WIB. Alerts fire on thresholds.

### AC-POSTING-009: Operations
Dedicated systemd service, dedicated Obscura 9223, 256MB RAM, dedicated IAM

### AC-POSTING-010: Dry-Run
Full pipeline simulation without actual X post

### AC-POSTING-011: Post Delete
`/x-delete` navigates to tweet and deletes via CDP browser UI

### AC-POSTING-012: P13 GATE
All acceptance criteria verified, 30-day production soak with X account

---

## 12. Dependencies

| Dependency | Existing? | P13 Action |
|------------|-----------|------------|
| Obscura CDP | ✅ In use (port 9222) | Deploy on 9223 with dedicated storage-dir |
| S3 bucket | ✅ Existing | Add `guinevere-assets/x-poster/` prefix |
| SOPS encryption | ✅ ADR-016 | Reuse age key for X cookies |
| LLMRouter (9Router) | ✅ P1 | Same router, Gemini Flash model |
| Discord bot | ✅ P2 | Add 10 new slash commands |
| Episode storage | ✅ P3 | Wire `store_episode()` for post audit trail |
| Grafana + Prometheus | ✅ P8 | Add 8 new metrics |
| Systemd slice | ✅ P7 | Add new service to existing slice |
| Gotify fallback | ✅ P2 | Reuse for critical alerts |
| APScheduler | ✅ P5 | Use for heartbeat scheduling |
| LoopManager | ✅ P5 | Wire TaskContract for agent loop trigger |
| Windows python | ⚠️ Not yet | Need `watchdog` library + boto3 on Windows |

---

## 13. Caveats & Risks

1. **X DOM changes are unpredictable** — X frequently updates their UI. The CDP selector-based approach needs regular maintenance. Mitigation: centralized selector config, `/x-*` commands for fallback.
2. **Obscura + X posting not proven** — Obscura is designed for data extraction, not form posting. May need raw Chromium fallback.
3. **X rate limits without API** — Without official X API, rate limits are enforced via UI behavior (popups, temporary blocks). 5/day cap is conservative.
4. **Cookie rotation frequency unknown** — X auth cookies may rotate without notice. Session health check is critical.
5. **Media upload via CDP** — File input `setInputFiles` or `input[type="file"]` fill via CDP may have edge cases with large files.
6. **Windows watchdog** — Requires Python + watchdog + boto3 on Faiz's Windows machine. Separate setup/deployment.
7. **Discord interactions reliability** — Discord slash commands may have latency. Use ephemeral responses.

---

## 14. Step Breakdown (28 Steps)

| # | Step | Group | Description |
|---|------|-------|-------------|
| 001 | S3 Queue Setup | Infrastructure | Bucket prefix, IAM scoped creds, polling skeleton |
| 002 | Windows Watchdog | Infrastructure | Watchdog script + boto3 upload to S3 |
| 003 | Obscura 9223 | Infrastructure | Dedicated Obscura instance with X storage-dir |
| 004 | Systemd Service | Infrastructure | `guinevere-x-poster.service`, slice, dependencies |
| 005 | Queue Polling Loop | Queue Engine | asyncio poll S3 prefix, FIFO, state machine |
| 006 | Sidecar Parser | Queue Engine | JSON parse, metadata extraction, validation |
| 007 | Rate Limiter | Queue Engine | 3h interval, 5/day, night mode, immediate override |
| 008 | Cookie Injector | X Session | SOPS decrypt, CDP cookie injection, storage-dir persist |
| 009 | Session Health Check | X Session | Pre-post verification (page title, URL, DOM) |
| 010 | Session Recovery | X Session | Expiry → /held/ + Discord alert + manual re-auth flow |
| 011 | Caption Generator | Caption | Gemini Flash structured output (caption+alt+hashtags) |
| 012 | Content Moderation | Caption | LLM unsafe detection → block → /failed/ → notify |
| 013 | Tone Controller | Caption | Auto-detect tone, language detection |
| 014 | Compose Adapter | X Posting | CDP navigate, Draft.js text input strategies |
| 015 | Media Upload | X Posting | CDP file input, ≤4 images, 5MB limit |
| 016 | Post Action | X Posting | Tweet button click, success verification, S3 state transition |
| 017 | Dry-Run Mode | X Posting | Simulate without actual post |
| 018 | Retry Engine | Error Handling | 3 attempts: 30s/2m/5m, error classification |
| 019 | Circuit Breaker | Error Handling | 5 failures → pause, 30min alert cooldown |
| 020 | Processing Timeout | Error Handling | 30min timeout → reclaim /pending/ |
| 021 | Post Notification | Discord | Embed with preview + link in #guinevere-status |
| 022 | Status Commands | Discord | /x-status, /x-list, /x-cancel, /x-hold, /x-resume |
| 023 | Edit Command | Discord | /x-edit caption override |
| 024 | Delete Command | Discord | /x-delete via CDP browser UI |
| 025 | Retry Commands | Discord | /x-retry-failed, /x-retry |
| 026 | Grafana Dashboard | Monitoring | 8 metrics, per-post logging, 90-day retention |
| 027 | Daily Summary | Monitoring | Discord 20:00 WIB (posted/failed/pending) |
| 028 | Integration Test | E2E | Full pipeline + P13 GATE |
