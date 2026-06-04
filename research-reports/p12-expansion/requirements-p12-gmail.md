# P12 Gmail/Email Integration — Requirements Specification

> **Phase:** P12 — Gmail/Email Integration (Expansion)
> **Dependencies:** P5 (Agent Loop) + P8 (Observability) + P11-004 (ChannelAdapter spec-only)
> **Date:** 2026-06-03
> **Status:** Requirements Complete — Pending Step Breakdown Approval
> **Author:** Faiz (operator) + Guinevere (synthesis)

---

## §1 Scope

### 1.1 In Scope

| Capability | Description |
|---|---|
| Read | Fetch new emails via Gmail API (incremental sync) |
| Notify | Discord notifications for important/classified emails |
| Classify | AI-powered email classification (8 categories, cascade + LLM fallback) |
| Draft | Guinevere composes draft reply → Discord embed → Faiz approves → send |
| Financial | Extract amount + category from financial emails → P9 structured metadata |
| Loop Trigger | Client email + keywords → Faiz approval → TaskContract (P5 SDLC loop) |
| Search | Semantic email search via Discord commands |
| Briefing | Daily 8am WIB morning briefing + on-demand `!email-digest` |
| Resend | Transactional email fallback (invoices, notifications) via Resend API |

### 1.2 Out of Scope

| Capability | Reason |
|---|---|
| Auto-reply | DEFERRED — no send without explicit per-email Faiz approval |
| Multi-account | Single personal Gmail only |
| Calendar integration | Separate phase |
| Email migration | Separate phase |
| IMAP/POP3 | Gmail API only |

---

## §2 Architecture Decisions

### 2.1 Account Identity (Q3.1)

**Decision:** Faiz's personal Gmail account (`faiz@gmail.com`).
**ADR-022 Impact:** ADR-022 must be updated from `guinevere@[domain].com` to personal Gmail.

### 2.2 OAuth2 Authentication (Q3.2)

**Decision:** Testing mode acceptable. Re-auth every 7 days via `!email-reauth` Discord command.
**Scopes:** `gmail.modify` + `gmail.labels`
**Token Storage:** Pre-generated refresh token on laptop → SOPS-encrypt → deploy to VPS
**Libraries:** `google-api-python-client`, `google-auth-oauthlib`

### 2.3 GCP Project (Q3.5)

**Project Name:** `guinevere-gmail-prod`
**APIs:** Gmail API + Pub/Sub API
**Billing:** Enabled (free tier covers single-user)

### 2.4 Push/Poll Sync (Q1.4 + Research)

**Decision:** Hybrid — Pub/Sub StreamingPull (outbound gRPC, no webhook) for urgent + 5min polling fallback.
**Watch Renewal:** Integrated into main service (no separate timer unit). Daily `watch()` call.
**History Sync:** `history.list(startHistoryId=stored_old_id)` — counter-intuitive: use OLD id, not new.

### 2.5 Resend Integration (Q3.3)

**Decision:** Resend enters P12 as a separate step (not merged with Gmail API).
**Use Cases:** Invoice sending (P9 link), project notifications, fallback when Gmail API down.
**Existing:** `RESEND_API_KEY` already in deployment config.

### 2.6 Service Architecture (Q2.20)

**Unit:** `guinevere-gmail.service` (separate systemd unit, isolation priority)
**Slice:** `guinevere.slice`
**MemoryMax:** 512M
**Health Check:** 60s interval
**Auto-reconnect:** OAuth token auto-refresh + Discord alert if refresh fails

### 2.7 P11 Dependency (Q3.23)

**Decision:** Spec-only dependency (Option C). P12 builds against P11-004 ChannelAdapter spec. P11-004 retrofits later.
**ChannelType:** `ChannelType.GMAIL` already defined in spec.

### 2.8 Historical Backfill (Q3.19-20)

**Default:** Last 30 days, label-filtered only (Important, Work, Financial).
**First Run:** Classify + summarize backfilled emails, then incremental sync going forward.

---

## §3 Email Processing Pipeline

### 3.1 Classification Engine (Q3.6-7)

**Approach:** Hybrid — heuristic cascade + LLM fallback for ambiguous emails.

```
Raw Email → Hash cache (dedup)
          → Heuristic rules (~78% accuracy, <1ms)
          → [if ambiguous] Embedding similarity (~85-90%)
          → [if still ambiguous] LLM classification (~95%+, ~2s)
```

**8 Categories (Q3.7 — confirmed sufficient):**

| Category | Trigger Signals | Priority | Action |
|---|---|---|---|
| `CLIENT_WORK` | Sender in client list, project keywords | HIGH | Notify + draft |
| `FINANCIAL` | Bank domains, "invoice", amount patterns | HIGH | Notify + P9 link |
| `BILLING_INVOICE` | Invoice PDF, payment terms | HIGH | Notify + P9 extract |
| `IMPORTANT` | Gmail Important label + 2 signals | MEDIUM | Notify |
| `NEWSLETTER` | List-Unsubscribe header, known domains | LOW | Batch digest |
| `PROMOTION` | Marketing keywords, unsubscribe | LOW | Low priority |
| `TRANSACTIONAL` | Receipt, confirmation, tracking | LOW | Classify + store |
| `SPAM_PHISHING` | Suspicious sender, injection patterns | BLOCK | Drop + alert |

### 3.2 Importance Scoring (Q3.8)

**Threshold:** Score ≥ 5 = notify Faiz immediately.
**Weights:** Fixed for MVP, tunable via Discord command post-MVP.

| Signal | Weight | Source |
|---|---|---|
| Gmail Important/Starred label | +3 | Gmail API |
| Sender in whitelist | +2 | Redis whitelist |
| Thread depth (replies) | +1 per reply | Gmail thread API |
| Urgency keywords | +2 | Body scan |
| Direct addressing ("Faiz") | +1 | Body scan |
| Financial amount detected | +3 | P9 parser |
| Action keywords ("deadline", "tolong") | +2 | Body scan |
| Reply rate to sender | +1 | History DB |

### 3.3 Content Sanitization Pipeline (Q3.11)

**Decision:** Full pipeline from day 1. Security is not iterative.

```
Raw Email → HTML normalize
          → Strip hidden CSS + zero-width chars
          → Injection pattern scan (50+ regex, CVE-2026-26133 defense)
          → Secret scan (1100+ TruffleHog rules via @sanity-labs/secret-scan)
          → PII scan (email, phone, KTP, CC via datafog)
          → Boundary markers injection
          → Refusal contract prepend
          → LLM
```

**Libraries:** `@sanity-labs/secret-scan`, `datafog` (Rust core), custom regex.

### 3.4 Metadata Extraction (Q2.8)

**Decision:** Metadata only + PDF text extraction. No attachment storage.
**PDF Parser:** Kreuzberg (97+ formats) or pdfplumber.

### 3.5 Financial Email → P9 Integration (Q3.10)

**Decision:** Store as structured metadata in memory. P9 reads later.

| Data Point | Extraction Method |
|---|---|
| Amount | Regex: `Rp\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?` (Indonesian format) |
| Category | LLM classification + keyword rules |
| Sender identity | Domain → bank/fintech mapping |
| Transaction date | Email date or body extraction |
| Description | Subject + first sentence |

---

## §4 Memory & Storage

### 4.1 Memory Pipeline (Q3.9)

**Classification:** Default `Confidential`, auto-escalate to `Restricted` for financial/client emails.
**Body Storage:** Summary-only in memory. Full body encrypted in separate storage.
**Tags:** Rule-based for speed (not LLM-generated).

```python
store_episode(
    content=llm_summary,           # 2-3 sentence summary
    source="gmail",
    classification="Confidential",  # or "Restricted" for financial/client
    importance=score,               # From importance scoring
    title=email_subject,
    episode_type="email",
    tags=["email", f"sender:{domain}", f"category:{cat}"],
    metadata={"from": sender, "thread_id": tid, "subject": subj, "labels": [...]},
)
```

### 4.2 Conversation Log Schema (Q3.17)

```sql
-- 1 row per email
INSERT INTO conversations (
    channel_type = 'gmail',
    sender_id = 'sender@domain.com',
    role = 'user',           -- or 'assistant' for sent
    content = 'summary',     -- Summary, not full body
    content_hash = SHA256(...),
    message_id = 'gmail-msg-id',
    response_to_id = NULL,    -- or FK to previous in thread
    metadata_ = {
        "subject": "...",
        "cc": ["..."],
        "labels": ["Important", "INBOX"],
        "thread_id": "gmail-thread-id",
        "has_attachments": true,
        "classification": "CLIENT_WORK",
        "importance_score": 7,
        "delivery_status": "delivered"  -- Q3.17 addition
    }
)
```

### 4.3 Logging Policy (Q3.12 — Confirmed Acceptable)

| Data | Log? | Redact? |
|---|---|---|
| Sender address | YES | NO |
| Subject | YES | NO |
| Body (first 200 chars) | YES | After sanitization |
| Body (full) | Memory only | NO (stored encrypted) |
| Attachments metadata | YES | NO |
| Classification verdict | YES | NO |
| Secrets found | Alert only | YES (redact from logs) |
| PII found | Alert only | YES (redact from logs) |

---

## §5 Draft Reply Pipeline

### 5.1 Generation (Q3.14)

**Context:** Last 3 messages in thread (Gmail threads API).
**Format:** HTML email (not plain text).
**Storage:** Save as Gmail Draft first (editable in Gmail web too).

### 5.2 Discord UX (Q2.12-13)

**Channel:** Private Discord channel dedicated to email.
**Approval:** Reaction emoji ✅ approve / ❌ reject / ✏️ edit.
**Edit:** Faiz types in Discord → Guinevere updates draft.
**Batch:** Batch approve multiple drafts OK.

### 5.3 Send Flow

```
Email classified → action required detected
    → Load thread history (last 3 messages)
    → Load client dossier (memory recall)
    → Load persona state
    → LLM generates HTML draft
    → Gmail API: drafts.create (saved as Gmail Draft)
    → Discord embed:
        📧 **Draft Reply for [Subject]**
        **To:** client@example.com
        **Thread:** [3 messages]
        [Draft content preview...]
        React ✅ to approve | ❌ to reject | ✏️ to edit
    → Faiz reacts ✅
    → Gmail API: drafts.send
    → Conversation log updated (role='assistant')
```

---

## §6 Discord Integration

### 6.1 Real-Time Notifications (Q2.13)

**Trigger:** Importance score ≥ 5 OR classification = CLIENT_WORK/FINANCIAL/BILLING_INVOICE.
**Format:** Discord embed with sender, subject, classification, importance score, action buttons.

### 6.2 Morning Briefing (Q3.15)

**Schedule:** Daily 8:00 AM WIB (Asia/Jakarta).
**Format:** Stats + Action Required + FYI + Filtered sections.
**Timezone:** WIB confirmed correct.

### 6.3 On-Demand Digest (Q3.15)

**Command:** `!email-digest` (default: last 12 hours).
**Output:** Same format as morning briefing but for specified time range.

### 6.4 Consent Flow (Q3.13 — Confirmed Acceptable)

| Event | Consent Check |
|---|---|
| First Gmail sync | Faiz grants via `!email-consent-grant` |
| New sender email | Auto-process if in whitelist, otherwise ignore |
| Sensitive content detected | Alert Faiz, ask classification |
| Revoke | `!email-consent-revoke` → stop all email processing |

### 6.5 Agent Loop Trigger (Q3.16)

**Decision:** Standard TaskContract (P5 SDLC loop). Not lightweight.
**Flow:** Client email + action keywords → Discord notification → Faiz ✅ → Create TaskContract → LoopManager.start()

---

## §7 Safety & Security

### 7.1 Prompt Injection Defense (Q3.11)

**Decision:** Full pipeline from day 1. CVE-2026-26133 defense mandatory.
**Layers:** HTML normalize → hidden CSS strip → zero-width char strip → injection regex (50+) → secret scan → PII scan → boundary markers → refusal contract.

### 7.2 Secret Scanning (Q2.18)

**Decision:** Scan + alert + redact from memory.
**Tool:** `@sanity-labs/secret-scan` (1100+ TruffleHog rules).
**Action:** If secret detected → Discord alert, redact from memory storage, do NOT pass to LLM.

### 7.3 Cross-Channel HARD STOP (Q1.7)

**Mechanism:** Shared Redis flag (same as P11 WhatsApp).
**Flow:** HARD STOP triggered from any channel → all channels stop immediately.

### 7.4 Surveillance Classification (Q3.9)

**Default:** All email = surveillance data (per SurveillanceDataPolicy).
**Classification:** Confidential → auto-escalate to Restricted for financial/client.

---

## §8 Operations

### 8.1 Monitoring (Q3.21 — Confirmed Sufficient)

| Metric | Type | Alert |
|---|---|---|
| `gmail_connected` | Gauge | 0 for >10min |
| `gmail_emails_received_total` | Counter | — |
| `gmail_emails_classified_total` | Counter (by category) | — |
| `gmail_emails_notified_total` | Counter | — |
| `gmail_drafts_created_total` | Counter | — |
| `gmail_drafts_approved_total` | Counter | — |
| `gmail_drafts_rejected_total` | Counter | — |
| `gmail_injection_detected_total` | Counter | >0 |
| `gmail_secrets_detected_total` | Counter | >0 |
| `gmail_api_quota_usage` | Gauge | >80% |
| `gmail_oauth_token_age_seconds` | Gauge | >50 days |
| `gmail_processing_latency_seconds` | Histogram | p95 >5s |
| `gmail_watch_active` | Gauge | 0 |

### 8.2 Re-Auth Flow (Q3.25 addition)

**AC-EMAIL-009:** Re-auth flow < 2 minutes via Discord `!email-reauth` command.
**Flow:** Command → OAuth URL embed → Faiz opens on laptop → grants → token stored → SOPS encrypted → service resumes.

### 8.3 Systemd Service (Q2.20)

```ini
[Unit]
Description=Guinevere Gmail Integration Service
After=guinevere-core.service postgresql.service redis.service

[Service]
Type=simple
User=guinevere
ExecStart=/opt/guinevere/.venv/bin/python -m src.gmail.main
Slice=guinevere.slice
MemoryMax=512M
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## §9 E2E Gate Test (Q3.22)

**10 scenarios, P12 GATE before P13:**

| # | Scenario | Verifies |
|---|---|---|
| 1 | Gmail API connected + OAuth valid | Auth |
| 2 | New email → classify → notify Discord | Pipeline |
| 3 | Financial email → P9 extract | Integration |
| 4 | Client email → draft → approve → send | Full flow |
| 5 | Prompt injection email → detected + blocked | Security |
| 6 | HARD STOP from email → all channels stop | Cross-channel |
| 7 | Secret in email → redacted from memory | Privacy |
| 8 | OAuth token refresh → no interruption | Operations |
| 9 | Morning briefing → delivered at 8am WIB | Scheduled |
| 10 | !email-digest → last 12h summary | On-demand |

---

## §10 Acceptance Criteria

| AC | Criterion | Test |
|---|---|---|
| AC-EMAIL-001 | Gmail connected, OAuth valid | Token refresh test |
| AC-EMAIL-002 | Emails classified within 5s | Latency test |
| AC-EMAIL-003 | Draft → approve → sent within 30s | E2E test |
| AC-EMAIL-004 | Zero prompt injection leaks | Red-team test |
| AC-EMAIL-005 | Secrets redacted from memory | Verification query |
| AC-EMAIL-006 | Financial → P9 linked | Cross-phase test |
| AC-EMAIL-007 | Morning briefing at 8am WIB | Cron test |
| AC-EMAIL-008 | HARD STOP cross-channel | Integration test |
| AC-EMAIL-009 | Re-auth flow < 2 min via Discord | UX test |

---

## §11 ADR-022 Revision Required

ADR-022 currently references `guinevere@[domain].com`. Must be revised to:
- Faiz's personal Gmail account
- Testing mode OAuth (7-day refresh, `!email-reauth`)
- Pub/Sub StreamingPull (not webhook)

---

## §12 Binding References

| Document | Relevance |
|---|---|
| ADR-022 | Channel strategy (needs revision for personal Gmail) |
| SRS-IR-011 to 015 | Gmail interface specs |
| FSD-COM-002 | Gmail functional spec |
| P11-004 | ChannelAdapter interface spec (spec-only dep) |
| PersonaSafetyPolicy | Email = surveillance data |
| SurveillanceDataPolicy | Classification + consent |
| ADR-002 | Safe word cross-channel |

---

## §13 Research Reports

| Report | Path |
|---|---|
| Gmail API capability map | `research-reports/gmail-api-capability-map.md` |
| Email AI classification patterns | `research-reports/p12-email-intelligence-patterns.md` |
| Email security + privacy | `research-reports/email-surveillance-security-privacy-architecture.md` |
| AI email landscape 2026 | `research-reports/p12-ai-email-landscape-2026-06-03.md` |
| Gmail push vs polling | `research-reports/gmail-push-vs-polling-comparison.md` |
