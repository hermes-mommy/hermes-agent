# P12 Email Intelligence — Production Pattern Research

**Generated**: 2026-06-03 | **Scope**: Email importance scoring, classification, action extraction, summarization, priority inbox, threading, attachments, deduplication, unsubscribe, sentiment/urgency

---

## 1. EMAIL IMPORTANCE SCORING

### 1.1 Gmail Priority Inbox — The Authoritative Reference

**Paper**: [The Learning Behind Gmail Priority Inbox](https://research.google/pubs/the-learning-behind-gmail-priority-inbox/) (Google Research, NIPS 2010)

**Core Algorithm**:
- **Model**: Linear logistic regression — chosen for scalability over complex models
- **Architecture**: Global model + per-user model with **transfer learning**
  - Final prediction = sum of global model log-odds + user model log-odds
  - Global model trained on all users, held fixed during personal model updates
  - User model only represents how different the user is from the global model
  - Enables compact user models + quick adoption of global changes (new features)

**Ground Truth (no explicit labels needed)**:
```
p = Pr(action ∈ {opens, replies, manual corrections},
      time ∈ (Tmin, Tmax) | features, user-has-seen)
```
- Actions counted as "important": opens, replies, manual corrections
- Tmin < 24 hours (gives user time to react)
- Tmax measured in days (resource constraint on storing features)

**Feature Categories**:
| Category | Examples |
|---|---|
| **Social** | Degree of interaction between sender/recipient, % of sender's mail read by recipient |
| **Content** | Headers and body terms highly correlated with user action/inaction |
| **Thread** | User's interaction with thread so far (started thread? replied?) |
| **Label** | Labels user applies via filters |
| **Sender-specific** | Per-sender reply rate, open rate, archive rate |

**Online Learning**: Passive-aggressive updates (PA-II regression variant)
```
wi ← wi + fi * e / (||fi||² + 1/(2C))
```
- `C` = regularization parameter, adjusted per-mail to represent label confidence
- Manual corrections get higher `C` than implicit signals
- User models get higher `C` than global model
- New user models get highest `C` to promote initial learning

**Threshold Tuning**: Per-user threshold, adjusted in real-time when user marks messages consistently in one direction. False negative rate is 3-4x the false positive rate.

**Measured Impact**: ~80% accuracy (±5%). Priority Inbox users spent 6% less time on email overall, 13% less on unimportant email.

### 1.2 Replicable Signals (without Google-scale infrastructure)

From multiple implementations (`mailfiler`, `ai-email-triage`, `email-classifier`):

```python
# Heuristic-based importance scoring (no ML required)
def score_importance(email, user_context):
    score = 0
    signals = []

    # 1. Sender signal (highest weight)
    if email.from_address in user_context.vip_list:      score += 30; signals.append("vip_sender")
    if email.from_address in user_context.frequent_contacts: score += 15; signals.append("frequent_contact")
    if user_context.sender_reply_rate.get(email.from_address, 0) > 0.5: score += 10

    # 2. Direct address
    if f"@{user_context.email.split('@')[1]}" not in email.from_address:  # external sender
        if user_context.email in (email.to + email.cc): score += 10; signals.append("direct_recipient")

    # 3. Urgency keywords
    urgency_words = {"deadline", "urgent", "asap", "overdue", "critical", "by EOD", "by tomorrow"}
    if any(w in email.subject.lower() + email.body.lower() for w in urgency_words):
        score += 15; signals.append("urgency_keyword")

    # 4. Thread engagement
    if email.thread_id and user_context.has_participated_in_thread(email.thread_id):
        score += 20; signals.append("active_thread")

    # 5. Reply expectation
    if email.subject.lower().strip().startswith("re:"): score += 5
    if "?" in email.subject or "?" in email.body[:500]: score += 10; signals.append("question_mark")

    # 6. Temporal recency
    age_hours = (now - email.date).total_seconds() / 3600
    if age_hours < 2: score += 5  # very recent gets boost

    return {"score": min(score, 100), "signals": signals}
```

### 1.3 emai SDK — Priority Scoring API

**Source**: [rafapetter/emai](https://github.com/rafapetter/emai)

```typescript
const priority = await emai.ai.prioritize(email, {
  userEmail: 'me@company.com',
  vipList: ['ceo@company.com', 'investor@fund.com'],
});
// Returns: { score: 85, level: 'high',
//   reasoning: 'From VIP sender, contains deadline, requires action',
//   suggestedResponseTime: '2 hours' }
```

Levels: `critical` | `high` | `medium` | `low` | `none`
Suggested response times: `immediate` | `within 1 hour` | `today` | `this week` | `when convenient`

---

## 2. CLASSIFICATION TAXONOMIES

### 2.1 Production Taxonomies Compared

| System | Categories | Approach |
|---|---|---|
| **UpGPT email-classifier** ([GitHub](https://github.com/upgpt-ai/email-classifier)) | ACTION_REQUIRED, FYI, NEWSLETTER, PROMOTION, RECEIPT, EXPIRED, SOCIAL, AUTOMATED | 7-rule heuristic cascade → AI fallback |
| **inboxzero/mailfiler** ([GitHub](https://github.com/JoeCotellese/inboxzero)) | 10 built-in: inbox, newsletter, marketing, github, jira, automated, receipts, calendar, security, archived | 3-layer: cache → heuristics → LLM |
| **gmail-automation-suite** ([GitHub](https://github.com/bhargavachary/gmail-automation-suite)) | Finance & Bills, Purchases & Receipts, Security & Alerts, Services & Subscriptions, Promotions & Marketing, Personal & Social | 5 ML models + rule ensemble |
| **MAE** ([GitHub](https://github.com/ankitdaf/mae_my_agentic_employee)) | Inbox, Transactions, Feed, Promotional | MobileBERT + rules on RK3566 SBC |
| **MailSort AI** ([GitHub](https://github.com/omexzihan/MailSort-AI)) | Work, Personal, Finance, Spam | TF-IDF + XGBoost / ensemble |

### 2.2 The 7-Rule Cascade Pattern (Most Replicable)

From [UpGPT email-classifier](https://github.com/upgpt-ai/email-classifier) — production-hardened with 78% accuracy on heuristics alone:

```
Priority order (first match wins):
1. LEARNED RULES     — AI-validated sender/domain overrides
2. GMAIL LABELS      — Gmail's CATEGORY_ labels mapped
3. SOCIAL            — Exact domain match against known social networks
4. AUTOMATED         — No-reply prefix OR subject pattern (2FA, password reset)
5. RECEIPT           — Order/shipping/invoice subject patterns
6. NEWSLETTER        — List-Unsubscribe header + known domain/subject combos
7. PROMOTION         — Prefix + subject + domain patterns
8. EXPIRED           — Date extraction + context keyword
9. ACTION/FYI        — Reply pattern, urgency keywords, read status
```

**Confidence scoring**: Each rule produces 0-1 based on signal alignment. Multiple signals = higher confidence. Default threshold: >0.85 for auto-classify.

### 2.3 Recommended P12 Taxonomy

For a personal AI email assistant, start with these 7 categories (expandable):

| Category | Purpose | Routing |
|---|---|---|
| `ACTION_REQUIRED` | Needs reply, approval, decision | High priority, notify |
| `FYI` | Informational, no response needed | Archive after read |
| `NEWSLETTER` | Subscribed editorial content | Digest, archive |
| `PROMOTION` | Marketing, sales, offers | Archive, optional unsubscribe |
| `RECEIPT` | Order confirmations, invoices | Archive, extract data |
| `SOCIAL` | Notifications from social platforms | Batch, low priority |
| `AUTOMATED` | System-generated (2FA, password resets) | Archive, extract codes |

Add these as needed: `CALENDAR`, `FINANCE`, `SECURITY_ALERT`, `EXPIRED`.

---

## 3. ACTION ITEM EXTRACTION

### 3.1 emai SDK — Production API

**Source**: [rafapetter/emai](https://github.com/rafapetter/emai)

```typescript
const actions = await emai.ai.detectActions(email);
// Returns:
[
  {
    description: 'Send Q1 report to finance team',
    assignee: 'you',
    dueDate: '2026-03-07',
    priority: 'high',
    status: 'pending'
  }
]

// Thread-level (deduplicates completed items):
const threadActions = await emai.ai.detectActionsInThread(thread);
```

### 3.2 Meeting-to-Action — Production Schema

**Source**: [swapnanil/meeting-to-action](https://github.com/swapnanil/meeting-to-action)

Full output schema for action extraction from transcripts (adaptable to email):

```json
{
  "action_items": [
    {
      "task": "Fix Redis latency on auth service",
      "owner": "Bob",
      "deadline": "Wednesday EOD",
      "priority": "high"
    }
  ],
  "decisions": ["string"],
  "open_questions": ["string"],
  "risk_flags": [
    { "description": "string", "severity": "critical|moderate|low" }
  ]
}
```

### 3.3 Langmail Task Extractor Agent

**Source**: [A-makarim/langmail](https://github.com/A-makarim/langmail)

Architecture: Dedicated `Task Extractor` sub-agent (Claude Haiku) with isolated context. Receives only the email thread, returns structured action items with deadlines. Runs as part of a LangGraph supervisor workflow.

### 3.4 Melusine — Enterprise Email Processing

**Source**: [MAIF/melusine](https://github.com/maif/melusine) — 363★, production at French insurance company MAIF

Features:
- Email conversation segmentation (split thread into individual messages)
- Message part tagging (body, signatures, footers)
- Transferred email handling
- Emergency/urgency flagging
- Pipeline execution with debug mode and parallelization

### 3.5 Action Extraction Patterns (NLP)

From [Enron-based neural network research](https://github.com/aifenaike/Action-Items-Detection-In-Email):
- 93% test accuracy on action item detection
- 87% precision, 62% recall
- Key indicators: imperative verbs ("please send", "confirm"), deadlines ("by Friday"), question marks

**LLM-based extraction prompt pattern** (from multiple implementations):
```
For each sentence in this email, determine if it contains an action item.
Action items are: explicit requests, commitments ("I will..."), deadlines,
tasks assigned to someone.

Return JSON: [{ "description": "...", "assignee": "...", "deadline": "...", "confidence": 0.0-1.0 }]
```

---

## 4. EMAIL SUMMARIZATION

### 4.1 Extractive vs Abstractive

| Approach | Method | Best For | Production Examples |
|---|---|---|---|
| **Extractive** | Select key sentences from original | Short emails, deterministic output | Melusine snippet extraction |
| **Abstractive** | LLM generates new summary text | Long threads, multi-message context | emai, langmail, uOttaMail |
| **Hybrid** | Extract key facts, then LLM-formatted | Structured output, audit trail | Iteration Layer pipeline |

### 4.2 Length Targets (from production systems)

| Use Case | Target Length | System |
|---|---|---|
| Inbox preview | 1 line (~15 words) | uOttaMail "one-line AI summaries" |
| Email card | 2-3 sentences | AI Inbox Agent, emai |
| Thread digest | 3-5 bullet points | emai `summarizeThread()` |
| Batch digest | Per-email 1-liner + total count | emai `summarizeBatch()` |
| Full summary | 2-3 paragraphs | langmail context prep |

### 4.3 What to Preserve

From multiple implementations, the consensus on what summaries **must** include:

1. **Who**: Sender identity and their relationship to recipient
2. **What**: Core request/information being conveyed
3. **When**: Any deadlines, dates, or time sensitivity
4. **Action needed**: Whether a reply/action is required
5. **Context**: How this relates to previous thread messages

### 4.4 emai Summarization API

```typescript
// Single email
const summary = await emai.ai.summarize(email);

// Thread-aware (deduplicates across messages)
const threadSummary = await emai.ai.summarizeThread(thread);

// Batch digest
const digest = await emai.ai.summarizeBatch(emails);
```

---

## 5. PRIORITY INBOX IMPLEMENTATIONS

### 5.1 Gmail Priority Inbox — Full Architecture

**Paper**: [research.google.com/pubs/archive/36955.pdf](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/36955.pdf)

**Key design decisions**:

1. **Ranking, not classification**: Priority Inbox ranks mail rather than classifying important/not — because per-user thresholds vary wildly and can't be auto-determined.

2. **Global + user model transfer learning**: 
   - Global model weights `g` updated independently
   - User model weights `w` represent only deviation from global
   - Final log-odds = global log-odds + user log-odds
   - New features added to global propagate instantly

3. **Passive-aggressive online updates (PA-II)**:
   - Robust to noisy training data (user behavior is indirect signal)
   - `C` parameter tuned per-mail based on label confidence
   - Manual corrections > opens > no action

4. **Bigtable for scale**: Models globally replicated, features logged per `user:message-id` for real-time merging with user actions.

### 5.2 Replicable Signals (Single-User Scale)

Without Google infrastructure, a single-user P12 can use:

| Signal | Weight | Source |
|---|---|---|
| **VIP sender** | High | User-defined VIP list |
| **Sender reply rate** | High | Track per-sender: replies/emails_received |
| **Sender open rate** | Medium | Track per-sender opens |
| **Thread participation** | High | Has user replied in this thread? |
| **Direct address** (To:/CC: user) | Medium | Parse headers |
| **Urgency keywords** | Medium | Regex list |
| **Time since last interaction with sender** | Low | Recent senders get boost |
| **Question mark in subject/body** | Low | Implies response needed |
| **Email age** | Low | Fresher = possibly more urgent |

### 5.3 mailfiler — Local Priority Inbox Implementation

**Source**: [JoeCotellese/inboxzero](https://github.com/JoeCotellese/inboxzero)

3-layer pipeline:
```
Layer 1: Cache (SQLite)     → Sender/domain DB lookup → apply immediately if high confidence
Layer 2: Heuristics          → Header analysis + scoring → apply + cache if high confidence
Layer 3: LLM Classifier      → Anthropic Claude or LM Studio → apply + cache
```

**Implicit learning**: Watches for user corrections in Gmail — if user moves archived email back to inbox, sender gets pinned. After 3+ overrides: sender is pinned permanently.

---

## 6. THREAD-AWARE PROCESSING

### 6.1 email-origin-chain — Deep Thread Parsing

**Source**: [yodjii/email-origin-chain](https://github.com/yodjii/email-origin-chain)

Hybrid strategy for extracting full conversation history:
1. **MIME Layer**: Recursively descends through `message/rfc822` attachments
2. **Inline Layer**: Scans body for forwarded blocks using regex patterns (15+ languages)
3. **Date Normalization**: any-date-parser + luxon for international date parsing
4. **Signal-Based Confidence**: Detects garbage/incomplete chains via email density checks

Returns: Full history array `[deepest...root]` with per-message `from`, `to`, `cc`, `subject`, `date_iso`, `text`, `flags`.

### 6.2 Enterprise Threading (Relativity/Reveal)

**Source**: [Relativity Email Threading docs](https://help.relativity.com/RelativityOne/Content/Relativity/Analytics/Email_threading.htm)

Key concepts for P12:
- **Inclusive emails**: Messages with unique content not present in any other thread message
- **Email Duplicate Spare**: Exact duplicate of another message in set
- **Conversation Index**: Outlook/Exchange metadata for thread grouping
- **Shingling**: Content similarity via set intersection of text shingles

### 6.3 What to Summarize in Threads

Pattern from emai, langmail, and enterprise systems:

1. **Latest message only** — for quick triage when thread context is known
2. **Unread messages in thread** — incremental summarization
3. **Inclusive messages only** — skip quoted/forwarded content that appeared earlier
4. **Thread evolution** — who said what, when, and what changed
5. **Outstanding actions** — which action items from earlier messages remain unresolved

---

## 7. ATTACHMENT INTELLIGENCE

### 7.1 emai — Most Complete Single SDK

**Source**: [rafapetter/emai](https://github.com/rafapetter/emai)

```typescript
// Auto-detect and parse
const parsed = await emai.attachments.parse(attachment, { depth: 'deep' });
// → { text, markdown, metadata, pages, tables, images, structuredData }

// Plain text
const text = await emai.attachments.toText(attachment);

// OCR scanned documents
const ocrText = await emai.attachments.ocr(attachment);

// Vision AI description
const description = await emai.attachments.describe(attachment);

// Structured data extraction
const data = await emai.attachments.extract(attachment, InvoiceSchema);
```

**Supported formats**: PDF, images (JPG/PNG/GIF/WebP), Word (DOCX), Excel (XLSX), PowerPoint (PPTX), CSV, plain text

### 7.2 Kreuzberg — Polyglot Document Intelligence

**Source**: [kreuzberg-dev/kreuzberg](https://github.com/kreuzberg-dev/kreuzberg/)

97+ formats across 8 categories. Rust core with bindings for Python, TypeScript, Ruby, Java, Go, PHP. OCR via Tesseract, PaddleOCR, EasyOCR, or VLM (143 vision model providers).

### 7.3 MailParse — Production Attachment Pipeline

**Source**: [mailparse.dev](https://www.mailparse.dev/learn/email-automation/document-extraction)

Architecture for production document extraction from email:
```
Inbound email → MIME parse → Filter by content-type + filename regex
→ Store raw in S3 (keyed by messageId/SHA256-filename)
→ Extract: PDF parser → OCR fallback → schema mapping → event bus
```

**Edge cases handled**: Nested multiparts, inline CID images, TNEF (`winmail.dat`), RFC 2231/2047 encoded filenames, S/MIME.

### 7.4 OpenMail — Auto Text Extraction

**Source**: [OpenMail docs](https://docs.openmail.sh/concepts/attachments)

Automatically extracts text from attachments on receipt. `extractionMethod` field indicates method: `pdf`, `ocr`, `office`, `csv`, `text`. Returns `parsedText` in webhook payload. Files >10MB skipped, text capped at 50K chars.

---

## 8. DEDUPLICATION

### 8.1 Three-Layer Dedupe Strategy

**Source**: [Mailhook Blog](https://mailhook.co/blog/clean-emails-in-pipelines-dedup-normalize-store)

| Layer | Goal | Key | Strategy |
|---|---|---|---|
| **Delivery** | Don't process same delivery twice | `provider_delivery_id`, webhook event ID | Upsert message, append-only delivery events |
| **Message** | One row per logical email | `Message-ID` (normalized), content hash | UPSERT by `(inbox_id, provider_message_id)` |
| **Artifact** | Consume once (OTP, magic link) | `sha256(artifact_type + value + context)` | UNIQUE constraint on `artifact_hash` |

**Critical insight**: No single field is universally reliable. `Message-ID` can be missing or duplicated. Always keep a fallback (content hash).

### 8.2 Sedna — Enterprise Deduplication

**Source**: [Sedna Help Center](https://support.sedna.com/hc/en-us/articles/25456979333655-How-does-Sedna-Deduplicate-Messages)

Dedup chain (only when Message-ID matches):
1. Subject line comparison
2. Attachments: sorted + checksummed
3. Plaintext AND HTML body comparison
4. Click-tracking link normalization (strip unique recipient identifiers)
5. 5-day window: messages >5 days apart not checked

### 8.3 Notification vs Actual Email

**Forwarded email detection** (from StackOverflow / crisp-oss):
- **Manual forward**: New `Message-ID`, subject starts with "Fwd:" (localized per client)
- **Auto-forward**: Extra headers like `Delivered-To`, `X-Loop`, `X-Original-To` (not standardized)
- **Resent headers**: `Resent-From`, `Resent-Date`, `Resent-Message-ID` — from RFC 5322, but rarely used

**[crisp-oss/email-forward-parser](https://github.com/crisp-oss/email-forward-parser)**: Handles 20+ email client forwarding formats (Outlook, Gmail, Yahoo, Thunderbird, etc.) via regex patterns.

---

## 9. UNSUBSCRIBE DETECTION

### 9.1 RFC 2369 List-Unsubscribe Header

**Standard header format**:
```
List-Unsubscribe: <mailto:unsubscribe@example.com>, <https://example.com/unsub>
```

**RFC 8058 One-Click** (newer):
```
List-Unsubscribe-Post: List-Unsubscribe=One-Click
```
Enables mail clients to unsubscribe with a single POST request.

### 9.2 Production Parsers

**Mailspring** ([GitHub](https://github.com/Foundry376/Mailspring/blob/master/app/internal_packages/list-unsubscribe/lib/unsubscribe-service.ts)):
```typescript
export interface UnsubscribeOption {
  type: 'https' | 'http' | 'mailto';
  uri: string;
}
// Parses: "<mailto:unsub@example.com>, <https://example.com/unsub>"
```

**Voicemail** ([GitHub](https://github.com/tomblomfield/voicemail/blob/main/src/app/lib/unsubscribe.ts)):
```typescript
interface UnsubscribeInfo {
  listUnsubscribe: string | null;
  listUnsubscribePost: string | null;  // RFC 8058
  httpsUrls: string[];
  mailtoUrls: string[];
  bodyLinks: string[];       // Fallback: unsubscribe links in HTML body
  senderEmail: string;
  senderName: string;
}
```

### 9.3 Heuristic Detection (for emails without header)

From [UpGPT blog](https://upgpt.ai/blog/how-we-built-ai-email-client-that-never-sees-your-emails) and [elizaOS email-classifier](https://github.com/elizaOS/eliza/blob/develop/plugins/plugin-lifeops/src/lifeops/email-classifier.ts):

```python
def detect_newsletter_marketing(email):
    signals = []
    confidence = 0.0

    # 1. List-Unsubscribe header (strongest signal)
    if email.headers.get('List-Unsubscribe'):
        confidence = max(confidence, 0.85)
        signals.append("list_unsubscribe_header")

    # 2. Gmail category labels
    if 'CATEGORY_PROMOTIONS' in email.labels:
        confidence = max(confidence, 0.80)
        signals.append("gmail_promotions_label")

    # 3. Sender domain patterns
    newsletter_domains = {'mailchimp', 'substack', 'convertkit', 'beehiiv', 'ghost.io',
                          'campaign-email', 'sendgrid', 'mailerlite', 'buttondown'}
    sender_domain = email.from_address.split('@')[1].lower()
    if any(d in sender_domain for d in newsletter_domains):
        confidence = max(confidence, 0.75)
        signals.append(f"newsletter_domain:{sender_domain}")

    # 4. Body text unsubscribe patterns
    unsub_patterns = [r'unsubscribe', r'opt.out', r'email preferences',
                      r'manage.*subscription', r'update.*preferences']
    for pattern in unsub_patterns:
        if re.search(pattern, email.body, re.IGNORECASE):
            confidence += 0.10
            signals.append("unsubscribe_text")
            break

    # 5. From address patterns
    no_reply_patterns = ['noreply@', 'no-reply@', 'donotreply@', 'newsletter@',
                         'marketing@', 'hello@', 'team@', 'info@']
    if any(pattern in email.from_address.lower() for pattern in no_reply_patterns):
        confidence += 0.05
        signals.append("no_reply_sender")

    return min(confidence, 1.0), signals
```

---

## 10. SENTIMENT / URGENCY DETECTION

### 10.1 uOttaMail — Multi-Agent Tone Analysis

**Source**: [Divi76h/uOttaMail](https://github.com/Divi76h/uOttaMail)

Dedicated `email_tone_analyzer` agent that classifies tone as: Professional, Friendly, Urgent, etc. Part of a 6-agent parallel pipeline using Solace Agent Mesh and AWS Bedrock (Claude 3.5 Haiku).

### 10.2 VerdictMail — Threat/Urgency Scoring

**Source**: [ascarola/verdictmail](https://github.com/ascarola/verdictmail)

Multi-stage pipeline for threat analysis: SPF/DKIM/DMARC → DNSBL reputation → WHOIS domain age → display-name spoofing → URL reputation (URLhaus + VirusTotal) → AI analysis (OpenAI/Anthropic/Ollama) → decision (pass/flag/move_to_junk). Confidence thresholds: flag at 0.55, junk at 0.80.

### 10.3 Urgency Heuristics (from patent + implementations)

```python
def detect_urgency(email):
    score = 0

    # Temporal urgency
    immediacy = [
        r'(as\s*soon\s*as\s*possible|asap)',
        r'(urgent|emergency|critical)',
        r'(by\s*(today|tomorrow|EOD|end\s*of\s*day|COB))',
        r'(within\s*the\s*(next|hour|day))',
        r'(deadline|overdue|past\s*due)',
        r'(time.sensitive|time.critical)',
    ]
    for pattern in immediacy:
        if re.search(pattern, email.subject + " " + email.body[:1000], re.IGNORECASE):
            score += 0.15

    # Escalation language
    escalation = [r'escalat', r'attention.*required', r'action.*(required|needed)',
                  r'(please|kindly).*(respond|reply|confirm|approve)']
    for pattern in escalation:
        if re.search(pattern, email.body[:1000], re.IGNORECASE):
            score += 0.10

    # ALL CAPS subject or excessive punctuation
    if email.subject == email.subject.upper() and len(email.subject) > 10:
        score += 0.10
    if email.subject.count('!') >= 2 or email.subject.count('?') >= 2:
        score += 0.05

    # Sender signals
    if email.from_address in vip_list:
        score += 0.20

    return min(score, 1.0)
```

### 10.4 Sentiment Analysis for Email

**Research finding** ([UC San Diego / Microsoft, SIGIR 2017](https://cseweb.ucsd.edu/classes/fa17/cse291-b/reading/sigir17a_email.pdf)): Sentiment features (along with request/commitment predictions) are among the top-3 feature groups for predicting whether an email will receive a reply. But **historical interaction features** ("HistIndiv" — how sender and recipient have interacted before) are the #1 predictor of reply behavior.

---

## KEY TAKEAWAYS FOR P12 PIPELINE DESIGN

### Architecture Pattern: Cascade, Not Single Model

Every production system uses a **cascading pipeline** — never a single model for everything:

```
Hash Cache → Heuristic Rules → Embedding Similarity → LLM Fallback
```

This minimizes cost (deterministic rules are free), maximizes speed (cache hits skip all processing), and uses expensive LLM calls only for truly ambiguous cases.

### Recommended P12 Processing Steps

| Step | Method | Cost |
|---|---|---|
| 1. Deduplicate | Message-ID + content hash | Free |
| 2. Detect unsubscribe | List-Unsubscribe header + body patterns | Free |
| 3. Classify category | 7-rule heuristic cascade | Free |
| 4. Score importance | Sender history + keyword heuristics | Free |
| 5. Extract action items | LLM (only for ACTION_REQUIRED emails) | ~$0.001/email |
| 6. Summarize | LLM (only ACTION_REQUIRED + long threads) | ~$0.001/email |
| 7. Attachment intelligence | PDF parse → OCR fallback → extract | Free-$0.01/attachment |
| 8. Sentiment/urgency | Regex heuristics + LLM for ambiguous | Mostly free |

### Libraries to Use

| Need | Library | Language |
|---|---|---|
| Full email AI pipeline | [emai](https://github.com/rafapetter/emai) | TypeScript/JS |
| Classification cascade | [@upgpt/email-classifier](https://github.com/upgpt-ai/email-classifier) | TypeScript |
| Local priority inbox | [mailfiler](https://github.com/JoeCotellese/inboxzero) | Python |
| Document parsing (97+ formats) | [kreuzberg](https://github.com/kreuzberg-dev/kreuzberg) | Python/Rust/TS |
| Email thread reconstruction | [email-origin-chain](https://github.com/yodjii/email-origin-chain) | TypeScript |
| Forwarded email detection | [email-forward-parser](https://github.com/crisp-oss/email-forward-parser) | JavaScript |
| Enterprise email pipeline | [melusine](https://github.com/maif/melusine) | Python |
| Multi-agent email system | [langmail](https://github.com/A-makarim/langmail) | Python (LangGraph) |
| Spam/threat analysis | [verdictmail](https://github.com/ascarola/verdictmail) | Python |

### Data Privacy: Keep It Local

The UpGPT architecture is the privacy gold standard: classify in-browser, only send metadata to AI provider when needed, store all user data in IndexedDB. For P12 (single-user), this approach eliminates compliance headaches entirely.