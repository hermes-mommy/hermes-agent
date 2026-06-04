# Gmail API v1 — Exhaustive Capability Map for P12 Integration

> **Sources**: Google Gmail API official docs (developers.google.com/workspace/gmail), last updated 2026-04-20.
> **Scope**: Every method, quota unit, rate limit, OAuth scope, search operator, and constraint relevant to: reading inbox, searching, classifying, drafting replies, sending, managing labels, watching for new mail.

---

## 1. QUOTA UNIT COST BY METHOD

The Gmail API consumes **quota units**. Every operation costs units. The daily free threshold is **80,000,000 units per project per day**.

| Quota Bucket | Limit |
|---|---|
| Per minute per project | 1,200,000 quota units |
| Per minute per user per project | 6,000 quota units |
| Per day per project (free) | 80,000,000 quota units |
| Recipients per message | 500 max |

*Source: [developers.google.com/workspace/gmail/api/reference/quota](https://developers.google.com/workspace/gmail/api/reference/quota)*

### 1.1 Messages Resource

| Method | Quota Units | Notes |
|---|---|---|
| `messages.list` | **5** | Returns message IDs only; paginated (maxResults up to 500) |
| `messages.get` | **20** | Returns full message resource; use `format=MINIMAL/METADATA/FULL/RAW` |
| `messages.send` | **100** | ⚠️ Most expensive send; limit 500 recipients/message |
| `messages.batchDelete` | **50** | Bulk delete — efficient for multi-message cleanup |
| `messages.batchModify` | **50** | Bulk label change — efficient for mass classify |
| `messages.delete` | **10** | Single message delete → TRASH |
| `messages.modify` | **5** | Add/remove labels on one message |
| `messages.trash` | **20** | Move to TRASH |
| `messages.untrash` | **5** | Remove from TRASH → INBOX |
| `messages.import` | **25** | Import with SMTP-level scanning |
| `messages.insert` | **25** | Direct insert (IMAP APPEND-like, bypasses most scanning) |
| `messages.attachments.get` | **20** | Download a single attachment by attachmentId |

### 1.2 Threads Resource

| Method | Quota Units | Notes |
|---|---|---|
| `threads.list` | **10** | Returns thread IDs; accepts `q` parameter |
| `threads.get` | **40** | Returns full thread with all messages |
| `threads.modify` | **10** | Apply/remove labels on entire thread |
| `threads.delete` | **20** | Delete entire thread |
| `threads.trash` | **20** | Move thread to TRASH |
| `threads.untrash` | **10** | Restore thread from TRASH |

### 1.3 Drafts Resource

| Method | Quota Units | Notes |
|---|---|---|
| `drafts.list` | **5** | Returns draft IDs |
| `drafts.get` | **20** | Get draft content |
| `drafts.create` | **10** | Create new draft |
| `drafts.update` | **15** | Replace draft content |
| `drafts.send` | **100** | Send draft + auto-delete draft ⚠️ |
| `drafts.delete` | **10** | Delete draft |

### 1.4 Labels Resource

| Method | Quota Units | Notes |
|---|---|---|
| `labels.list` | **1** | All labels (system + user) |
| `labels.get` | **1** | Single label |
| `labels.create` | **5** | Create user label |
| `labels.update` | **5** | Full label update |
| `labels.delete` | **5** | Delete user label |

### 1.5 History Resource

| Method | Quota Units | Notes |
|---|---|---|
| `history.list` | **2** | Incremental sync; requires `startHistoryId` |

### 1.6 Other

| Method | Quota Units |
|---|---|
| `users.getProfile` | **1** |
| `users.watch` | **100** |
| `users.stop` | **50** |

---

## 2. OAUTH 2.0 SCOPES — COMPLETE LISTING

*Source: [developers.google.com/workspace/gmail/api/auth/scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)*

### 2.1 Non-Sensitive (lowest barrier, basic verification)

| Scope | What It Grants |
|---|---|
| `https://www.googleapis.com/auth/gmail.addons.current.action.compose` | Manage drafts and send emails when interacting with the add-on |
| `https://www.googleapis.com/auth/gmail.addons.current.message.action` | View email messages when interacting with the add-on |
| `https://www.googleapis.com/auth/gmail.labels` | See and edit email labels only |

### 2.2 Sensitive (additional OAuth verification required)

| Scope | What It Grants |
|---|---|
| `https://www.googleapis.com/auth/gmail.addons.current.message.metadata` | View email metadata (not body) when add-on is running |
| `https://www.googleapis.com/auth/gmail.addons.current.message.readonly` | View full email messages when add-on is running |
| `https://www.googleapis.com/auth/gmail.send` | **Send email only** — cannot read inbox |

### 2.3 Restricted (most powerful, requires security assessment for stored data)

| Scope | What It Grants |
|---|---|
| `https://mail.google.com/` | **Full access**: read, compose, send, permanently delete bypassing trash. ⚠️ Only use if you need immediate permanent deletion. |
| `https://www.googleapis.com/auth/gmail.readonly` | View messages and settings. Cannot modify or send. |
| `https://www.googleapis.com/auth/gmail.compose` | Manage drafts and send emails. Cannot read inbox. |
| `https://www.googleapis.com/auth/gmail.insert` | Add/import emails into mailbox only. |
| `https://www.googleapis.com/auth/gmail.modify` | Read, compose, and send emails. **Cannot permanently delete** (trash only). This is the recommended scope for most assistants. |
| `https://www.googleapis.com/auth/gmail.metadata` | View metadata (labels, headers) but not email body. |
| `https://www.googleapis.com/auth/gmail.settings.basic` | Manage email settings and filters. |
| `https://www.googleapis.com/auth/gmail.settings.sharing` | Manage delegate access. Service account + domain-wide delegation only. |

### 2.4 Recommended Scope Strategy for P12

| Use Case | Minimum Scope |
|---|---|
| Inbox reading + classify + reply | `gmail.modify` (covers read + send + label) |
| Read-only classification | `gmail.readonly` |
| Send-only (draft + send) | `gmail.compose` or `gmail.send` |
| Read metadata only (screening) | `gmail.metadata` |
| Label management only | `gmail.labels` |

---

## 3. PUSH NOTIFICATIONS (Pub/Sub Watch)

*Source: [developers.google.com/workspace/gmail/api/guides/push](https://developers.google.com/workspace/gmail/api/guides/push)*

### 3.1 Architecture

```
Gmail Mailbox → Cloud Pub/Sub Topic → Subscription (push webhook OR pull)
                                        ↓
                                Your VPS endpoint
```

### 3.2 Setup Requirements

1. **Create Cloud Pub/Sub topic**: `projects/{project}/topics/{topic}`
2. **Create subscription**: Push (HTTP POST webhook) or Pull (your app polls)
3. **Grant publish rights**: Grant `gmail-api-push@system.gserviceaccount.com` publish permission on the topic
4. **Call `users.watch`**: Start watching a mailbox

### 3.3 Watch Request

```json
POST /gmail/v1/users/me/watch
{
  "topicName": "projects/myproject/topics/mytopic",
  "labelIds": ["INBOX"],
  "labelFilterBehavior": "INCLUDE"
}
```

- `labelFilterBehavior`: `INCLUDE` or `EXCLUDE` — filters which label changes trigger notifications
- `labelIds`: Array of label IDs to filter on

### 3.4 Watch Response

```json
{
  "historyId": 1234567890,
  "expiration": 1431990098200
}
```

- `historyId`: Current mailbox history ID — use as `startHistoryId` for sync
- `expiration`: Unix timestamp in ms — watch expires after this

### 3.5 Critical Limitations

| Constraint | Value |
|---|---|
| **Watch renewal required** | At least once every **7 days** (recommended: daily) |
| **Max notification rate** | **1 event per second per user** — excess events are **dropped** |
| **Notification payload** | Base64URL-encoded JSON: `{"emailAddress": "...", "historyId": "..."}` |
| **Recovery** | Fall back to `history.list` polling if notifications stop |
| **Notification loops** | Avoid triggering a notification from notification handling |

### 3.6 Notification Payload

Webhook POST body:
```json
{
  "message": {
    "data": "eyJlbWFpbEFkZHJlc3MiOiAidXNlckBleGFtcGxlLmNvbSIsICJoaXN0b3J5SWQiOiAiOTg3NjU0MzIxMCJ9",
    "messageId": "2070443601311540",
    "publishTime": "2021-02-26T19:13:55.749Z"
  },
  "subscription": "projects/myproject/subscriptions/mysubscription"
}
```

Decoded `message.data`: `{"emailAddress": "user@example.com", "historyId": "9876543210"}`

### 3.7 Acknowledgment

- **Push subscription**: Return HTTP 200 to acknowledge
- **Pull subscription**: Call `subscriptions.acknowledge` after pulling

---

## 4. RATE LIMITS & QUOTA

*Source: [developers.google.com/workspace/gmail/api/reference/quota](https://developers.google.com/workspace/gmail/api/reference/quota)*

| Limit Type | Value | Meaning |
|---|---|---|
| Per-user per minute | **6,000 quota units** | One user can only consume 6K units/min across all API calls |
| Per-project per minute | **1,200,000 quota units** | Aggregate across all users in the project |
| Per-project per day | **80,000,000 quota units** | Free threshold; above this may incur charges (TBD with 90-day notice) |
| Recipients per message | **500** | Hard limit on To + Cc + Bcc |

### 4.1 Practical Implications

With `gmail.modify` scope (read + send + modify) for one user:

| Operation | Quota Cost | Max/min (user limit) | Max/day (user limit) |
|---|---|---|---|
| List messages (list) | 5 | 1,200 calls/min | ~16M calls (project-limited) |
| Get message (get) | 20 | 300 calls/min | ~4M calls |
| Get message metadata (format=metadata) | 20 | 300 calls/min | Same |
| Send message (send) | 100 | 60 calls/min | ~800K sends/day |
| Batch modify (batchModify) | 50 | 120 calls/min | ~1.6M ops |
| Get thread (threads.get) | 40 | 150 calls/min | ~2M gets |
| Modify message (modify) | 5 | 1,200 calls/min | ~16M ops |
| History list (history.list) | 2 | 3,000 calls/min | ~40M calls |

### 4.2 Performance Best Practices

- **Use `format=MINIMAL`** on repeated gets (only labelIds may change)
- **Use `format=METADATA`** when you don't need body (still 20 units though)
- **Batch requests**: Combine up to 100 API calls in one HTTP request (saves round trips, NOT quota)
- **Partial response**: Use `fields` parameter to reduce payload size
- **gzip**: Set `Accept-Encoding: gzip` header

---

## 5. ATTACHMENT HANDLING

*Source: [developers.google.com/workspace/gmail/api/guides/uploads](https://developers.google.com/workspace/gmail/api/guides/uploads)*

### 5.1 Downloading Attachments

- Use `messages.attachments.get` (20 quota units)
- Requires `messageId` + `attachmentId` from the message's `payload.parts[].body.attachmentId`
- Returns base64URL-encoded attachment data
- **No explicit size limit documented for downloads** — governed by Gmail's overall message limits

### 5.2 Uploading Attachments (for send/insert)

Three upload methods via the `/upload` URI prefix:

| Method | `uploadType` | Best For |
|---|---|---|
| **Simple** | `media` | Small files (≤5 MB), no metadata needed |
| **Multipart** | `multipart` | Small files + metadata in one request |
| **Resumable** | `resumable` | Large files, unreliable connections; session-based |

### 5.3 Resumable Upload Details

- Initiate: `POST /upload/gmail/v1/users/me/messages/send?uploadType=resumable`
- Headers: `X-Upload-Content-Type`, `X-Upload-Content-Length`
- Response: `Location` header with session URI (includes `upload_id`)
- Upload: `PUT` to session URI with `Content-Range` header
- **Chunk size**: Must be multiple of **256 KB** (except final chunk)
- **Session expiry**: ~1 day if unused

### 5.4 Size Limits

- **Send**: Gmail's standard 25 MB total message size (all content + attachments encoded). After base64 encoding (~33% overhead), the raw file attachment limit is roughly **18-20 MB**.
- **Draft**: Same limits as send.
- For larger files: Use Google Drive links instead.

### 5.5 MIME Types

- Set via `Content-Type` header in MIME message
- Accepts any MIME type
- `messages.attachments.get` returns the attachment with its original MIME type

---

## 6. THREAD MANAGEMENT

*Source: [developers.google.com/workspace/gmail/api/guides/threads](https://developers.google.com/workspace/gmail/api/guides/threads)*

### 6.1 How Gmail Groups Threads

Threads are collections of related messages forming a conversation. A message belongs to a thread via `threadId`.

**Thread cannot be created directly** — they form when:
1. A message is sent with `threadId` specified
2. OR Gmail's backend groups messages by `References`/`In-Reply-To` headers and matching `Subject`

### 6.2 Adding to a Thread (for replies)

To add a reply to an existing thread, you MUST satisfy all three:

1. **`threadId`** must be set in the message resource
2. **`References`** and **`In-Reply-To`** headers must be set per RFC 2822
3. **`Subject`** headers must match (Re: prefix handled automatically)

### 6.3 Thread Methods

| Method | Description |
|---|---|
| `threads.list` | List thread IDs (accepts `q` parameter for search) |
| `threads.get` | Get full thread with all messages |
| `threads.modify` | Add/remove labels on entire thread |
| `threads.delete` | Permanently delete (requires `https://mail.google.com/` scope) |
| `threads.trash` | Move to TRASH |
| `threads.untrash` | Restore from TRASH |

### 6.4 Thread Filtering

- `threads.list` accepts the same `q` parameter as `messages.list`
- **If any message in a thread matches the query, the entire thread is returned**

---

## 7. SEARCH OPERATORS (q PARAMETER)

*Source: [developers.google.com/workspace/gmail/api/guides/filtering](https://developers.google.com/workspace/gmail/api/guides/filtering) + [support.google.com/mail/answer/7190](https://support.google.com/mail/answer/7190)*

### 7.1 Core Search Operators

| Operator | Example | Description |
|---|---|---|
| `from:` | `from:amy@example.com` | Sender |
| `to:` | `to:me` | Recipient |
| `subject:` | `subject:dinner` | Subject line |
| `cc:` / `bcc:` | `cc:john@example.com` | Cc/Bcc recipients |
| `after:` / `before:` | `after:2026/01/01 before:2026/02/01` | Date range in PST timezone (use Unix seconds for other TZ) |
| `older_than:` / `newer_than:` | `older_than:1y` `newer_than:2d` | Relative time (`d`, `m`, `y`) |
| `label:` | `label:INBOX` `label:important` | Label (system or user) |
| `category:` | `category:primary` `category:social` | Inbox category |
| `is:` | `is:unread` `is:starred` `is:important` | Status flags |
| `has:` | `has:attachment` `has:drive` `has:document` | Has attachments/drive/docs |
| `filename:` | `filename:pdf` `filename:invoice.pdf` | Attachment filename |
| `in:` | `in:inbox` `in:sent` `in:trash` `in:spam` `in:anywhere` | Location |
| `size:` / `larger:` / `smaller:` | `larger:10M` | Message size |
| `list:` | `list:info@example.com` | Mailing list |
| `deliveredto:` | `deliveredto:username@example.com` | Delivery address |
| `-` (negation) | `dinner -movie` | Exclude |
| `OR` / `{ }` | `from:amy OR from:david` | Match any |
| `AND` | `from:amy AND to:david` | Match all (implicit default) |
| `" "` (exact phrase) | `"meeting tomorrow"` | Exact phrase match |
| `( )` (grouping) | `subject:(dinner movie)` | Group terms |
| `AROUND` | `holiday AROUND 10 vacation` | Proximity search |

### 7.2 `is:` Status Values

`is:unread`, `is:read`, `is:starred`, `is:important`, `is:muted`

### 7.3 `has:` Values

`has:attachment`, `has:youtube`, `has:drive`, `has:document`, `has:spreadsheet`, `has:presentation`, `has:userlabels`, `has:nouserlabels`

### 7.4 `in:` Location Values

`in:inbox`, `in:trash`, `in:spam`, `in:sent`, `in:draft`, `in:anywhere`, `in:archive`, `in:snoozed`

### 7.5 API vs Gmail UI Differences

1. **No alias expansion**: Searching `from:primary@domain.com` won't match emails sent by `alias@domain.com` (unlike the UI)
2. **No thread-wide search**: The UI allows thread-wide searches; the API doesn't
3. **Dates are PST**: `after:2026/06/01` means midnight PDT. Use Unix seconds for precision: `after:1748736000`

### 7.6 Practical Query Templates for P12

```
# Unread inbox messages from last 24h
q=in:inbox is:unread newer_than:1d

# All messages in a thread
threads.get with threadId (no q needed)

# Find replies to a specific sender
q=from:person@example.com newer_than:7d

# Messages with attachments
q=has:attachment in:inbox

# Classify: important unread
q=is:important is:unread in:inbox
```

---

## 8. DRAFTS API

*Source: [developers.google.com/workspace/gmail/api/guides/drafts](https://developers.google.com/workspace/gmail/api/guides/drafts)*

### 8.1 Draft Lifecycle

```
drafts.create → DRAFT label applied → drafts.update (replaces) → drafts.send (deletes draft, creates SENT message)
```

### 8.2 Key Behaviors

- Draft messages **cannot have any label other than DRAFT**
- Draft message content **cannot be edited** — only **replaced** (update = destroy + create new)
- **Draft ID is stable** across updates (underlying message ID changes)
- Sending a draft **auto-deletes** the draft and creates a new message with `SENT` label

### 8.3 Methods

| Method | Description |
|---|---|
| `drafts.create` | Create new draft from base64URL-encoded MIME |
| `drafts.get` | Get draft (use `format=raw` for full MIME) |
| `drafts.list` | List draft IDs |
| `drafts.update` | Replace draft content (destroy old, create new) |
| `drafts.send` | Send draft + auto-delete |
| `drafts.delete` | Delete draft |

### 8.4 Send with Update

`drafts.send` can update the draft in the same call:
```json
POST /gmail/v1/users/me/drafts/send
{
  "id": "draft_id",
  "message": {
    "raw": "base64url_encoded_new_content"
  }
}
```

### 8.5 Pattern for P12

```
1. LLM generates reply text
2. Construct MIME message with In-Reply-To + References headers
3. drafts.create (threadId set for threading)
4. User reviews → drafts.send (or discard)
```

---

## 9. HISTORY API — INCREMENTAL SYNC

*Source: [developers.google.com/workspace/gmail/api/guides/sync](https://developers.google.com/workspace/gmail/api/guides/sync)*

### 9.1 Two Sync Methods

| Method | When | How |
|---|---|---|
| **Full sync** | First connect, or history unavailable | `messages.list` → batch `messages.get` → cache `historyId` |
| **Partial sync** | After initial sync | `history.list(startHistoryId={last_known_id})` |

### 9.2 Full Sync Flow

1. Call `messages.list` to get first page of message IDs
2. Create batch request of `messages.get` for each message
3. First time: use `format=FULL` or `format=RAW`; subsequent: use `format=MINIMAL`
4. Store the `historyId` of the most recent message (first in list response) for future partial syncs

### 9.3 Partial Sync Flow

```
history.list?startHistoryId={saved_id}
```

Returns `History` objects containing:
- `id` — history record ID
- `messages[]` — message IDs affected
- `messagesAdded[]` — new messages
- `messagesDeleted[]` — deleted messages
- `labelsAdded[]` / `labelsRemoved[]` — label changes

### 9.4 Limitations

| Constraint | Value |
|---|---|
| History retention | **Typically ≥1 week**, often longer |
| History unavailable | API returns HTTP 404 → must perform full sync |
| History may be unavailable | Rare cases; handle gracefully |

### 9.5 Combined with Push Notifications

```
1. users.watch → get historyId = H1
2. Receive push notification → get historyId = H2
3. history.list(startHistoryId=H1) → get all changes
4. Store H2 as new last_known_historyId
```

---

## 10. COMPLETE METHOD INDEX — BY CAPABILITY

### 10.1 Reading Inbox

| Capability | Method | Quota | Scope Required |
|---|---|---|---|
| List message IDs | `messages.list` | 5 | read/modify/readonly |
| Get single message | `messages.get` | 20 | read/modify/readonly |
| List thread IDs | `threads.list` | 10 | read/modify/readonly |
| Get full thread | `threads.get` | 40 | read/modify/readonly |
| Get attachment | `messages.attachments.get` | 20 | read/modify/readonly |
| Get user profile | `users.getProfile` | 1 | any |

### 10.2 Searching & Filtering

| Capability | Method | Notes |
|---|---|---|
| Search messages | `messages.list` with `q` param | Full search operators |
| Search threads | `threads.list` with `q` param | Returns thread if any msg matches |
| Filter by label | `messages.list` with `labelIds` | Composable with `q` |

### 10.3 Classifying (Label Management)

| Capability | Method | Quota | Notes |
|---|---|---|---|
| List all labels | `labels.list` | 1 | System + user labels |
| Create label | `labels.create` | 5 | User label only |
| Modify message labels | `messages.modify` | 5 | Add/remove labels |
| Batch modify labels | `messages.batchModify` | 50 | Up to 1000 msg IDs |
| Modify thread labels | `threads.modify` | 10 | Entire thread at once |

### 10.4 Drafting Replies

| Capability | Method | Quota |
|---|---|---|
| Create draft | `drafts.create` | 10 |
| Read draft | `drafts.get` | 20 |
| List drafts | `drafts.list` | 5 |
| Update draft | `drafts.update` | 15 |
| Send draft | `drafts.send` | 100 |

### 10.5 Sending

| Capability | Method | Quota |
|---|---|---|
| Send directly | `messages.send` | 100 |
| Send from draft | `drafts.send` | 100 |
| Import message | `messages.import` | 25 |
| Insert message | `messages.insert` | 25 |

### 10.6 Watching for New Mail

| Capability | Method | Quota |
|---|---|---|
| Start watch | `users.watch` | 100 |
| Stop watch | `users.stop` | 50 |
| Incremental sync | `history.list` | 2 |

### 10.7 Deletion & Cleanup

| Capability | Method | Quota |
|---|---|---|
| Delete message (→ Trash) | `messages.delete` | 10 |
| Trash message | `messages.trash` | 20 |
| Untrash message | `messages.untrash` | 5 |
| Batch delete | `messages.batchDelete` | 50 |
| Delete thread | `threads.delete` | 20 |
| Trash thread | `threads.trash` | 20 |
| Untrash thread | `threads.untrash` | 10 |

---

## 11. SYSTEM LABELS (Immutable)

*Cannot be created, deleted, or renamed via API.*

| Label ID | Description |
|---|---|
| `INBOX` | Inbox |
| `SENT` | Sent mail |
| `DRAFT` | Drafts |
| `TRASH` | Trash |
| `SPAM` | Spam |
| `STARRED` | Starred |
| `IMPORTANT` | Important |
| `UNREAD` | Not a label per se — tracked via `message.labelIds` and `is:unread` |
| `CATEGORY_PERSONAL` | Category: Primary |
| `CATEGORY_SOCIAL` | Category: Social |
| `CATEGORY_PROMOTIONS` | Category: Promotions |
| `CATEGORY_UPDATES` | Category: Updates |
| `CATEGORY_FORUMS` | Category: Forums |

---

## 12. MESSAGE FORMAT OPTIONS

When calling `messages.get` or `drafts.get`:

| Format | Description | Response Size |
|---|---|---|
| `FULL` | Full message body + attachments inline (no attachment download needed) | Largest |
| `RAW` | Raw RFC 2822 MIME as base64URL in `raw` field | Large |
| `MINIMAL` | Only `id`, `threadId`, `labelIds` | Smallest |
| `METADATA` | Headers (From, To, Subject, Date) + `labelIds`, no body | Medium |

---

## 13. KEY CONSTRAINTS SUMMARY FOR P12 DESIGN

| Constraint | Value | Impact |
|---|---|---|
| Per-user quota/min | 6,000 units | ~300 `messages.get`/min or ~60 sends/min |
| Push notification rate | 1/sec per user | Cannot rely on push for high-frequency classification |
| Watch renewal | Every 7 days max | Must implement periodic re-watch (recommend daily) |
| History retention | ≥1 week | If offline >1 week, need full re-sync |
| Message send limit | 500 recipients | Single message cannot blast |
| Attachment size (send) | ~25 MB total encoded | ~18-20 MB raw file |
| Draft message immutability | Cannot edit; only replace | Store draft content client-side until final |
| Search date timezone | PST (PDT) | Use Unix timestamps for precise timezone handling |
| OAuth scope sensitivity | `gmail.modify` is Restricted | Requires OAuth verification for public apps |
| Thread linking | Requires correct RFC 2822 headers | Must preserve References/In-Reply-To from original |

---

## 14. REFERENCES (Official Sources)

| Topic | URL |
|---|---|
| REST API Reference | https://developers.google.com/workspace/gmail/api/reference/rest |
| Quota & Usage Limits | https://developers.google.com/workspace/gmail/api/reference/quota |
| OAuth Scopes | https://developers.google.com/workspace/gmail/api/auth/scopes |
| Push Notifications | https://developers.google.com/workspace/gmail/api/guides/push |
| Synchronization | https://developers.google.com/workspace/gmail/api/guides/sync |
| Drafts | https://developers.google.com/workspace/gmail/api/guides/drafts |
| Sending | https://developers.google.com/workspace/gmail/api/guides/sending |
| Threads | https://developers.google.com/workspace/gmail/api/guides/threads |
| Search/Filtering | https://developers.google.com/workspace/gmail/api/guides/filtering |
| Attachments | https://developers.google.com/workspace/gmail/api/guides/uploads |
| Performance Tips | https://developers.google.com/workspace/gmail/api/guides/performance |
| Search Operators | https://support.google.com/mail/answer/7190 |

---

*Generated 2026-06-03 from official Google Gmail API documentation (last updated 2026-04-20).*
*Map version: 1.0 — P12 Gmail Integration Research*