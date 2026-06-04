# Gmail API: Polling vs Push Notifications — Technical Comparison

**Date**: 2026-06-03
**Researcher**: Librarian (OpenCode)
**Evidence Sources**: Google Gmail API docs, Google Cloud Pub/Sub docs, Nylas CLI, StackOverflow, community Gists

---

## Executive Summary

**For a single-user personal assistant on a VPS: use Push (Pub/Sub StreamingPull) with polling fallback.** The key insight most people miss is that **push does NOT require a webhook**. Pub/Sub's **StreamingPull** (gRPC streaming pull) gives you sub-second latency via an **outbound-only** connection — no exposed ports, no SSL certificates, no domain name needed.

---

## 1. Gmail Push Notifications — Full Architecture

### 1.1 How It Works

The Gmail API does **not** push email content. It pushes a **single event**: "something changed." Your app then calls `history.list()` to find out what changed.

Push notification payload (decoded from Base64 in `message.data`):
```json
{"emailAddress": "user@example.com", "historyId": "9876543210"}
```

Source: [Google Gmail API Push Docs, 2026-04-20](https://developers.google.com/workspace/gmail/api/guides/push)

### 1.2 Setup Steps

| Step | Action |
|------|--------|
| 1 | Create GCP project with billing enabled |
| 2 | Enable Pub/Sub API: `gcloud services enable pubsub.googleapis.com` |
| 3 | Create Pub/Sub topic: `projects/{project}/topics/{topic}` |
| 4 | Grant `gmail-api-push@system.gserviceaccount.com` `roles/pubsub.publisher` |
| 5 | Create subscription (push HTTPS or pull/streaming pull) |
| 6 | Call `users.watch()` with topic name |
| 7 | Schedule `watch()` renewal daily (expires in 7 days) |

### 1.3 Incremental Sync Algorithm (Critical)

```
1. Call watch() → store historyId A (e.g., 1234567890)
2. Push notification arrives → historyId B (e.g., 9876543210)
3. Call history.list(startHistoryId=A)     ← use OLD id, NOT B!
4. Receive changes + new historyId C
5. Store C as next "A"
6. Process messagesAdded entries
```

Source: [Google Sync Guide](https://developers.google.com/gmail/api/guides/sync)

---

## 2. Subscription Types

### 2.1 Push Subscription (HTTPS Webhook)

- Requires: Public HTTPS endpoint with CA-signed SSL certificate
- Self-signed certificates WILL NOT WORK
- Needs domain name + certbot (Let's Encrypt OK)
- Exposes port 443 to internet

Source: [Google Pub/Sub Push Docs](https://cloud.google.com/pubsub/docs/create-push-subscription), [Google Groups confirmation](https://groups.google.com/g/cloud-pubsub-discuss/c/CSmgwFxoWk0)

### 2.2 Pull Subscription (StreamingPull) — VPS Winner

- No webhook, no HTTPS, no SSL, no exposed ports
- Outbound gRPC connection to Google, Google pushes through it
- Sub-second latency
- Client library auto-reconnects on disconnect

Source: [Google Pub/Sub Pull Docs](https://cloud.google.com/pubsub/docs/pull)

Setup commands:
```bash
gcloud pubsub topics create gmail-watch
gcloud pubsub topics add-iam-policy-binding gmail-watch \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
gcloud pubsub subscriptions create gmail-watch-pull --topic=gmail-watch
gcloud iam service-accounts create gmail-pubsub-reader
gcloud pubsub subscriptions add-iam-policy-binding gmail-watch-pull \
  --member="serviceAccount:gmail-pubsub-reader@PROJECT.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"
```

Python client:
```python
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("PROJECT", "gmail-watch-pull")

def callback(message):
    data = json.loads(message.data)
    process_changes(data['emailAddress'], my_stored_history_id)
    message.ack()

subscriber.subscribe(subscription_path, callback=callback).result()
```

---

## 3. Push Limitations

- **7-day watch expiry**: Must call `watch()` at least every 7 days, recommended daily
- **Rate limit**: 1 event/sec per user (sufficient for single user)
- **Notifications can be delayed or dropped**: Fallback polling required
- **No domain verification required** for Pub/Sub (unlike some claims)

Source: [Google Push Docs](https://developers.google.com/workspace/gmail/api/guides/push)

---

## 4. Polling Approach

### 4.1 Pure Polling with history.list

```python
async def poll_incremental(gmail_service, last_history_id):
    try:
        result = gmail_service.users().history().list(
            userId='me',
            startHistoryId=last_history_id,
            historyTypes=['messageAdded']
        ).execute()
    except HttpError as e:
        if e.resp.status == 404:
            return await full_sync(gmail_service)  # historyId expired
        raise

    for record in result.get('history', []):
        for added in record.get('messagesAdded', []):
            yield added['message']  # {id, threadId}

    return result.get('historyId', last_history_id)
```

### 4.2 Quota Analysis

| Method | Quota Units | Per-User Limit |
|--------|-------------|----------------|
| `history.list` | 2 | 15,000/min |
| `messages.list` | 5 | 15,000/min |
| `messages.get` | 5 | 15,000/min |
| `users.watch` | 100 | 15,000/min |

Polling every 30s: 5,760 units/day = 0.4% of daily budget.

Source: [Gmail API Quota Reference, 2026-05-01](https://developers.google.com/workspace/gmail/api/reference/quota)

### 4.3 2026 Quota Changes

New projects after May 1, 2026 get adjusted quotas. Later in 2026: quota increases require billing, usage above thresholds may be charged (90 days notice will be given). Existing projects (used Nov 2025-Apr 2026) preserved for 60 days.

Source: [Nylas CLI Gmail API Quotas 2026](https://cli.nylas.com/guides/gmail-api-quotas-2026)

---

## 5. VPS Feasibility

| Approach | Domain Needed | SSL Needed | Ports Exposed | Setup Effort |
|----------|--------------|------------|---------------|-------------|
| Push (HTTPS webhook) | Yes | CA-signed | 443 | Medium |
| Push (StreamingPull) | **No** | **No** | **None** | Low |
| Polling | No | No | None | Lowest |
| IMAP IDLE | No | No | 993 (imap.gmail.com outbound) | Low |

---

## 6. IMAP IDLE Alternative

**Pros**: No GCP project, no Pub/Sub, one persistent TCP connection
**Cons**: One folder per connection, MIME parsing needed, Gmail labels as IMAP folders (quirky), manual UID tracking, 15 connection limit

[canarymail/aioimaplib](https://github.com/canarymail/aioimaplib) — native async IDLE for Python.

---

## 7. GCP Requirements

- **Billing required**: Yes (credit card needed)
- **Free tier**: 10 GiB messages/month — single user at ~600 KB/month = **$0.00**
- **Service accounts**: One for Pub/Sub pull (minimal `roles/pubsub.subscriber` on subscription only)
- **No domain-wide delegation** needed for single user

Source: [Google Cloud Free Tier](https://cloud.google.com/free/docs/free-cloud-features)

---

## 8. Cost Comparison

| Approach | Monthly Cost | Notes |
|----------|-------------|-------|
| Polling | $0 | Gmail API is free, quotas are generous |
| Push (StreamingPull) | $0 | Pub/Sub free tier covers it |
| Push (HTTPS webhook) | $0 | Pub/Sub free tier + domain/SSL cost if any |
| IMAP IDLE | $0 | No cloud costs |

Both approaches are effectively free for a single user.

---

## 9. Reliability

### Push Failure Modes

| Failure | Mitigation |
|---------|------------|
| Watch expires | Daily cron renewal |
| StreamingPull disconnect | Client library auto-reconnects |
| Pub/Sub outage | Polling fallback after N seconds |
| Gmail drops notification (>1/sec) | Polling catches missed changes |
| historyId expires (404) | Full sync from scratch |

### Recommended Hybrid Pattern

```
StreamingPull (primary, sub-second)
    ↓
On notification: history.list(oldId) → process
    ↓
FALLBACK (every 60s): if no notification in 120s → history.list()
```

---

## 10. Final Recommendation

### Phase 1: Pure Polling (Start Here)

- Zero infrastructure: just OAuth + Gmail API
- Zero maintenance: no watch renewal, no gRPC, no Pub/Sub
- 30-second polling = 30s worst-case latency — adequate for personal assistant
- Same history.list pattern works with or without push

### Phase 2: Add StreamingPull (Optional)

- When 30s feels too slow
- When you want sub-5-second response
- Adds low maintenance burden (daily watch() renewal cron)

### Never: HTTPS Push Webhook on VPS

- StreamingPull gives same latency with zero attack surface
- HTTPS push requires domain, SSL, exposed port — all downsides, no upsides

### Decision Matrix

| Criterion | Polling | Push (StreamingPull) | Push (HTTPS) | IMAP IDLE |
|-----------|---------|---------------------|-------------|-----------|
| Setup time | 30 min | 2-3 hrs | 3-4 hrs | 30 min |
| GCP project | No | Yes | Yes | No |
| Billing | No | Yes (free) | Yes (free) | No |
| Domain+SSL | No | No | Yes | No |
| Exposed ports | No | No | Yes (443) | No |
| Latency | 30-60s | 2-3s | 2-3s | 1-2s |
| Maintenance | None | Daily renewal | Daily+SSL | Reconnects |
| Cost | $0 | $0 | $0 | $0 |
| Code complexity | Low | Medium | Med-High | Medium |

---

## Source Index

1. [Gmail API Push Notifications Guide](https://developers.google.com/workspace/gmail/api/guides/push) — 2026-04-20
2. [Gmail API users.watch Reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/watch) — 2026-04-15
3. [Gmail API Synchronization Guide](https://developers.google.com/gmail/api/guides/sync)
4. [Gmail API users.history.list Reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list)
5. [Gmail API Quota Reference](https://developers.google.com/workspace/gmail/api/reference/quota) — 2026-05-01
6. [Pub/Sub Create Push Subscription](https://cloud.google.com/pubsub/docs/create-push-subscription)
7. [Pub/Sub Pull Subscriptions](https://cloud.google.com/pubsub/docs/pull)
8. [Pub/Sub Pricing](https://cloud.google.com/pubsub/pricing)
9. [Google Cloud Free Tier](https://cloud.google.com/free/docs/free-cloud-features)
10. [StreamingPull Gist — jrork, 2026-01-27](https://gist.github.com/jrork/c2e37e7bb3fd0e7a72041bc846feeb94)
11. [Nylas CLI: Gmail API Quotas 2026](https://cli.nylas.com/guides/gmail-api-quotas-2026)
12. [Google Workspace Agent Tools Safety (quota changes)](https://developers.google.com/workspace/tools-safety)
13. [aioimaplib — async IMAP with IDLE](https://github.com/canarymail/aioimaplib)
14. [Nylas CLI: IMAP vs Gmail API vs Graph API](https://cli.nylas.com/guides/imap-vs-gmail-api-vs-graph-api) — 2026-05-21
15. [Google Groups: Pub/Sub self-signed cert not supported](https://groups.google.com/g/cloud-pubsub-discuss/c/CSmgwFxoWk0)