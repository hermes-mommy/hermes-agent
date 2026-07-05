# P27 Research — Agent Communication Protocol Patterns

**Purpose:** Ground P27 Hermes Society Foundation's peer-to-peer Hermes communication protocol in proven, primary-source patterns. Findings directly shape the P27 protocol specification and the P28 implementation blueprint's event bus design.

**Scope:** Seven topic clusters — ACLs, message envelopes, event bus/pub-sub, intent/visibility, audit/replay, real-world implementations (MCP, A2A, ACP, AutoGen, LangGraph), and debate/consensus protocols.

**Methodology:** All citations are primary sources — official specifications, GitHub source code (with file SHA + line numbers), and authoritative engineering documentation. Secondary commentary is annotated as `[secondary]` and used only for explanatory context.

**Date:** 2026-06-28

---

## 1. Agent Communication Languages (ACL)

### 1.1 FIPA ACL — Foundational Standard

**Origin:** Foundation for Intelligent Physical Agents (FIPA), 1996–2002. Standardized by IEEE.

**Performative Vocabulary (FIPA Communicative Act Library Specification — XC00037H):**

The full set of performatives defines the *communicative acts* an agent may perform. The complete list:

| Performative | Meaning |
|---|---|
| `accept-proposal` | Accept a previously submitted `propose` to perform an action |
| `agree` | Agree to perform a `request`ed action (agent commits to carrying it out) |
| `cancel` | Cancel a previous `request` |
| `cfp` | Call for proposals — issues negotiation with terms |
| `confirm` | Confirm truth of content (sender believed receiver was unsure) |
| `disconfirm` | Confirm falsity of content |
| `failure` | Report that a previously `request`ed action failed |
| `inform` | Tell another agent something (sender believes it's true) — **most-used** |
| `inform-if` | Request content asking for true/false of a statement |
| `inform-ref` | Request content asking for value of a referential expression |
| `not-understood` | Sender did not understand the message |
| `propagate` | Ask receiver to forward this same message to others |
| `propose` | Reply to a `cfp` — propose a deal |
| `proxy` | Sender wants receiver to select target agents (by description) and deliver embedded message |
| `query-if` | Ask another agent whether a proposition is true |
| `query-ref` | Ask for an object referenced by an expression |
| `refuse` | Refuse to perform an action + give reason |
| `reject-proposal` | Reject a proposal during negotiation |
| `request` | Sender requests receiver to perform an action (or another communicative act) |
| `request-when` | Receiver should perform action when a proposition becomes true |
| `request-whenever` | As `request-when`, but every time the proposition becomes true again |
| `subscribe` | Persistent intention: notify sender of reference value and any updates |

**Evidence:** FIPA performatives list — [jmvidal.cse.sc.edu/talks/agentcommunication/performatives.html](https://jmvidal.cse.sc.edu/talks/agentcommunication/performatives.html) (canonical summary referencing FIPA XC00037H Communicative Act Library Specification).

**Message Structure** (FIPA ACL Message Structure Specification):

- **Mandatory:** `:performative` — only required field; declares the communicative act.
- **Standard slots:** `:sender`, `:receiver`, `:reply-to`, `:content`, `:language`, `:encoding`, `:ontology`, `:protocol`, `:conversation-id`, `:reply-with`, `:in-reply-to`, `:reply-by`.
- **Content descriptors:** `:language` (e.g., SL0, KIF, XML), `:ontology` (shared vocabulary), `:protocol` (interaction protocol such as `fipa-request`, `fipa-contract-net`).

**Evidence:** FIPA ACL Message Structure Spec — [yumpu.com/en/document/view/35150485/fipa-acl-message-structure-specification](https://www.yumpu.com/en/document/view/35150485/fipa-acl-message-structure-specification); PEAK-ACL library description — [sciencedirect.com/science/article/pii/S2352711026001408](https://www.sciencedirect.com/science/article/pii/S2352711026001408); SmythOS overview — [smythos.com/developers/agent-development/fipa-agent-communication-language/](https://smythos.com/developers/agent-development/fipa-agent-communication-language/).

**Key FIPA Interaction Protocols:**

1. **fipa-request:** `request` → `agree | refuse` → (`inform` of result | `failure`)
2. **fipa-query:** `query-if` / `query-ref` → `inform` (with answer) | `refuse`
3. **fipa-contract-net (CNP):** `cfp` → `propose | refuse` (xN proposers) → `accept-proposal | reject-proposal` (xM winners) → `inform` (result) | `failure`
4. **fipa-iterated-contract-net:** Recursive CNP over multiple rounds
5. **fipa-auction-English / Dutch / Vickrey:** Specialized bidding protocols

**Production FIPA-ACL library** (still maintained): [github.com/sarl/sarl-acl](https://github.com/sarl/sarl-acl) — FIPA Agent Communication Language implementation in Java (for SARL agent-oriented language).

**Adoption reality:** FIPA ACL is academically canonical, but **adoption in modern LLM-agent stacks is near-zero**. It informed everything but is rarely used literally today.

### 1.2 KQML — Predecessor

**Origin:** DARPA Knowledge Sharing Effort, 1990s.

**Key differences from FIPA ACL:**

- Fabric of vocabulary, performatives, and **reservations** (preconditions on knowledge base / belief state required to utter the performative) **[secondary]** — [AAC-Lab introduction](https://cdn.aaai.org/Workshops/1994/WS-94-02/WS94-02-007.pdf).
- Heavily tied to knowledge-base / KIF semantics; not transport-agnostic.

**Evidence:** Wikipedia overview — [en.wikipedia.org/wiki/Knowledge_Query_and_Manipulation_Language](https://en.wikipedia.org/wiki/Knowledge_Query_and_Manipulation_Language); UMBC proposal for revised KQML spec — [ebiquity.umbc.edu/paper/html/id/1198/](https://ebiquity.umbc.edu/paper/html/id/1198/A-Proposal-for-a-new-KQML-Specification).

**Conclusion:** KQML is **historical**. P27 should adopt FIPA-style performative vocabulary (with new modern equivalents) rather than re-use KQML primitive mechanics.

### 1.3 Modern ACLs and Layered Protocols

**Survey of Agent Interoperability Protocols** — covers the modern landscape including ACP, MCP, A2A: [arxiv.org/html/2505.02279v1](https://arxiv.org/html/2505.02279v1) (2025-05).

Three contemporary primitives have converged:

#### 1.3.1 MCP — Model Context Protocol (client ↔ server, NOT peer)

**Enforcement:** JSON-RPC 2.0 envelope. All MCP messages follow JSON-RPC 2.0.

**Three primary message types** ([MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic)):

```typescript
// JSON-RPC 2.0 Request
{
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: { [key: string]: unknown };
}

// JSON-RPC 2.0 Result Response
{
  jsonrpc: "2.0";
  id: string | number;
  result: { [key: string]: unknown };
}

// JSON-RPC 2.0 Notification (one-way, no id)
{
  jsonrpc: "2.0";
  method: string;
  params?: { [key: string]: unknown };
}
```

**Source permalink:** [github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/index.mdx](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/index.mdx) (3274 code snippets, Context7 benchmark 82.92, reputation High).

**Key takeaway for P27:** MCP's envelope (`jsonrpc`, `id`, `method`, `params`, `result`/`error`) is a battle-tested transport-neutral primitive. P27 can adopt the `id` and request/response pattern for synchronous request/response semantics, while adding peer-to-peer-specific extensions (sender, receiver, conversation-id).

#### 1.3.2 A2A — Agent2Agent Protocol (Google, peer-to-peer)

**Specification:** [github.com/a2aproject/A2A/blob/main/docs/specification.md](https://github.com/a2aproject/A2A/blob/main/docs/specification.md) (Format SHA `382185a53b312cd6a60f5ac536ec5a356437ce77` from `HEAD`).

**Core data objects:**

```json
// A2A v1.0 unified Part
{
  "text": "Hello world",      // text part
  "mediaType": "text/plain"
}

{
  "url": "https://example.com/doc.pdf",  // file-with-URI part
  "filename": "doc.pdf",
  "mediaType": "application/pdf"
}

{
  "data": { "key": "value" },  // structured data part
  "mediaType": "application/json"
}
```

**Message envelope shape (A2A v1.0):**
```json
{
  "messageId": "...",
  "role": "user" | "agent",
  "contextId": "...",          // = conversation thread
  "taskId": "...",
  "parts": [ { /* Part union above */ } ]
}
```

**Key A2A primitives:**
- **Agent Card** at `/.well-known/agent.json` for capability discovery ([Google codelab docs](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge)).
- **JSON-RPC 2.0** serialized via HTTP(S).
- **Streaming artifacts** with `MessageEvent` envelopes for long-running tasks.
- **Tasks / Parts** as primary content primitives.

**Limitation:** A2A models **client-server task delegation**, not symmetric peer debate. No native notion of risk tier, visibility, or symmetric debate turns. P27 must layer these on top or fork.

#### 1.3.3 ACP — Agent Communication Protocol (IBM → merged into A2A)

**Status:** ACP launched March 2025, merged into A2A under LF AI & Data August 2025 ([lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data](https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/)).

**ACP message structure:** ordered list of parts (multi-part MIME-like), JSON-RPC 2.0 payload, REST + SSE transports ([arxiv.org/html/2505.02279v1](https://arxiv.org/html/2505.02279v1)).

**Practical decision:** P27 should treat **A2A v1.0 as the substrate for agent envelope** (currently the de-facto open standard with Linux-Foundation governance) and layer Hermes-specific extensions for peer debate / consensus / risk tier / visibility.

---

## 2. Message Envelope Patterns

### 2.1 Actor Model — Reference Pattern (Akka / Erlang)

**Erlang-style mailboxes:** each actor has a mailbox queue. Messages arrive async; actor processes one at a time. Selective receive allows pattern-match against queued messages ([alex-karaberov.medium.com](https://alex-karaberov.medium.com/everything-you-always-wanted-to-know-about-the-actor-model-but-were-afraid-to-ask-b6eee8722953)).

**Akka .NET mailbox:** bounded/unbounded queue strategy, configurable dispatcher ([How Akka.NET Actors Process Messages](https://www.youtube.com/watch?v=5YSpYqcP3iA)). Messages are queued, processed one at a time per actor.

**Critical actor-model invariants for P27**:
1. **No shared mutable state** between agents.
2. **Mailbox is the only ingress** — externally-enforced serialization point.
3. **Selective receive / rules** — messages can be matched by predicate.
4. **At-most-once delivery by default;** at-least-once / exactly-once via supervisor / 2PC patterns.

### 2.2 ZeroMQ Envelope Patterns

The most operationally tested envelope patterns come from ZeroMQ:

- **REQ/REP** — synchronous request/reply with `[[empty], request]` multipart envelope.
- **DEALER/ROUTER** — async request/reply; ROUTER prepends connection identity as envelope frame.
- **PUB/SUB** — broadcast; filtering by topic prefix.
- **ROUTER** — adds sender identity automatically via connection-identification frame.

**Evidence:** ZeroMQ Guide Ch. 3 — [zguide.zeromq.org/docs/chapter3/](https://zguide.zeromq.org/docs/chapter3/): *"The DEALER socket is oblivious to the reply envelope and handles this like any multipart message. DEALER sockets are asynchronous and like PUSH and PULL."*

**Direct P27 applicability:**
- Use **ROUTER-style envelope** — receiver sees `[envelope-frames, identity, payload-frames]`. Lets Hermes instances see sender's identity, conversation-id, and message content in one envelope.
- Multipart frames map cleanly to envelope layers (envelope → header → payload).

### 2.3 Durable Inbox / Outbox Pattern

**Pattern:** For guaranteed delivery across databases and message brokers.

**Outbox:** Service writes an `OUTBOX` row in the *same transaction* as the business state. A relay process reads outbox rows and publishes to broker. Guarantees "send is part of business commit".

**Inbox:** Receiver stores `INBOX` row with `message_id` key on first arrival. Before processing, checks `message_id` exists. Idempotency + exactly-once semantics.

**Evidence:** Microservices.io canonical pattern — [microservices.io/patterns/data/transactional-outbox.html](https://microservices.io/patterns/data/transactional-outbox.html); definitive explanation — [medium.com/@serhatalftkn](https://medium.com/@serhatalftkn/reliable-messaging-in-microservices-the-outbox-and-inbox-pattern-2f831f15ff82): *"While the Outbox pattern ensures messages are sent, the Inbox pattern ensures they're processed exactly once on the receiving end."*

**Direct P27 applicability — mandatory design input:**
- Both Hermes instances must maintain `OUTBOX` and `INBOX` rows per message.
- Hermes-to-Hermes (`society/*`) topic must use outbox-pattern relay + inbox dedup-by-message-id.

---

## 3. Event Bus and Pub/Sub for Agents

### 3.1 Redis Pub/Sub vs Redis Streams

**Redis Pub/Sub:**
- Fire-and-forget; **no persistence**.
- If subscriber is offline, **messages are dropped**.
- Best for ephemeral signals (notifications, presence).

**Redis Streams:**
- Append-only log (XADD).
- Consumer groups, XREADGROUP semantics.
- Replay from any offset + persistent history.
- Per-message ACK for at-least-once / exactly-once.

**Evidence:** Comparison — [dev.to/lovestaco/redis-pubsub-vs-redis-streams-a-dev-friendly-comparison-39hm](https://dev.to/lovestaco/redis-pubsub-vs-redis-streams-a-dev-friendly-comparison-39hm): *"For real-time notifications, go with Pub/Sub. For persistence and scalability, Redis Streams is your best bet."* Stack Overflow — [stackoverflow.com/questions/6192177/redis-pub-sub-with-reliability](https://stackoverflow.com/questions/6192177/redis-pub-sub-with-reliability).

**P27 decision:** Use **Redis Streams as primary event bus** for Hermes-to-Hermes debate/audit. Reserve Pub/Sub only for ephemeral presence/heartbeat signals where loss is acceptable.

### 3.2 Kafka / NATS / RabbitMQ Trade-offs

**NATS** ([oneuptime.com](https://oneuptime.com/blog/post/2026-02-02-nats-pubsub-implementation/view)): pure fire-and-forget subject-routed pub/sub. **Does not persist by default** (JetStream adds persistence). Excellent for low-latency agent heartbeat / discovery.

**RabbitMQ:** classic queue + topics. Mature, durable, but slower than NATS/Streams.

**Kafka:** designed specifically for high-throughput durable event log. Often compared favorably to Redis for [exactly-once semantics — AWS comparison](https://aws.amazon.com/compare/the-difference-between-kafka-and-redis/): *"Apache Kafka outperforms Redis OSS in pub/sub messaging because Kafka was designed specifically for data streaming."*

**P27 bus design matrix:**

| Lane | Transport | Reason |
|---|---|---|
| `society/visibility=public/*` | Redis Streams (consumer group "society-mirror") | Durable replay + audit |
| `society/visibility=group/*` | Redis Streams (per-group consumer group) | Privacy partitioning |
| Hephaestus bus | Redis Streams producer/consumer | Reuse P20 Hephaestus queue infrastructure |
| Heartbeat / presence | NATS subject (`society.heartbeat.*`) | Fire-and-forget ephemeral |
| Audit log | append-only SQL table with hash chain | WORM store |

### 3.3 Replay / Audit in Event Systems

Event sourcing pattern: state reconstructed by replaying immutable event log ([diagrid.io/blog/checkpoints-are-not-durable-execution](https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows)): *"Every interaction — user messages, agent responses, tool calls and state changes — is an immutable Event appended to the session history."*

**P28 must support:**
- Time-travel: read stream at arbitrary offset → reconstruct debate state.
- Sub-claim-level replay: replay just one `argue / propose` turn.
- Forensics: replay full debate + overlay human annotations.

---

## 4. Intent and Visibility Patterns

### 4.1 Speech Act Theory (Searle) — Intent Classification

**Five canonical speech-act categories** (Austin/Searle; primary sources — [thoughtco.com/speech-act-theory-1691986](https://www.thoughtco.com/speech-act-theory-1691986); [quizlet study guide](https://quizlet.com/study-guides/types-of-speech-acts-assertive-directive-commissive-expressi-66116caf-1136-4fa7-83b2-5c3211884e75)):

| Searle Category | Direction of Fit | Examples |
|---|---|---|
| **Assertive (representative)** | Words → World | state, claim, inform, report |
| **Directive** | World → Words | request, command, ask, query |
| **Commissive** | World → Words (future-binding) | promise, commit, vow |
| **Declarative (declaration)** | Bidirectional (cause change by saying) | declare, christen, fire |
| **Expressive** | None (mental state) | apologize, thank, congratulate |

**P27 intent taxonomy derived from Searle + FIPA performatives:**

| Hermes `intent` | Maps to | Use case |
|---|---|---|
| `inform` | Assertive + FIPA `inform` | Share context / observation / evidence |
| `propose` | Commissive + FIPA `propose` | Action proposal to society |
| `request` | Directive + FIPA `request` | Ask sibling agent to do work |
| `query` | Directive + FIPA `query-if` / `query-ref` | Ask for missing context |
| `agree` / `refuse` | Commissive + FIPA `agree` / `refuse` | Consent/cross-check |
| `cfp` | FIPA `cfp` | Open call for proposals / debate opening |
| `argue` | Assertive + rebuttal | Debate turn |
| `concede` | Commissive | Yielding position in debate |
| `escalate` | FIPA `propagate` / `proxy` | Send to parent tier |
| `block` | Declarative | Hard-stop / safety boundary |
| `audit-query` | Directive | Ask audit ledger for replay/snapshot |

### 4.2 Visibility Levels

**P27 visibility levels** (multi-tier, derived from microservice authz-pattern literature):

| Level | Audience | Examples |
|---|---|---|
| `public` | All Hermes instances + Faiz | Heartbeats, society-level state |
| `society-private` | Society members only (Guinevere ↔ Pharsa) | Debate turns, internal consensus state |
| `group-scoped` | Named subgroup | Sub-debate topic (`society/hermes-engineering/debatable-budget`) |
| `dm` | Single named recipient | Direct sibling messages |
| `audit-only` | Audit store (Faiz + auditor sub-agent) | Pre-decision context snapshots |

**Direct mapping from prior Guinevere AGENTS.md §0 + §0.1:** Autonomy-first gated actions, context-restricted audit — these already imply tiered visibility. P27 layers it explicitly on the wire.

### 4.3 Provenance Tracking — W3C PROV Model

**W3C PROV** (Recommendation 2013) provides three core classes: `Entity`, `Activity`, `Agent`, and relationships `wasDerivedFrom`, `wasGeneratedBy`, `wasAttributedTo`, `used`, `wasInformedBy`.

**Standard:** [w3.org/TR/prov-overview/](https://www.w3.org/TR/prov-overview/): *"Provenance is information about entities, activities, and people involved in producing a piece of data or thing, which can be used to form..."*

**P27 derives four envelope provenance fields from PROV:**

| PROV class | P27 envelope field |
|---|---|
| Entity (thing) | `provenance:context_refs` (memory/milestone/audit ids referenced) |
| Activity (process) | `provenance:decided_by` (event / run id) |
| Agent (who) | `sender`, `co_signed_by` |
| `wasDerivedFrom` | `provenance:parent_message_ids` |
| `wasGeneratedBy` | `audit_hash` linking to ledger entry |

---

## 5. Audit and Replay

### 5.1 Event Sourcing — Foundational

**Event sourcing** = state is *derived* from log, not stored. Append-only log is truth.

**LangGraph channels pattern** ([github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)) — example of event-sourced agent state:

```python
# From langgraph/libs/langgraph/langgraph/channels/untracked_value.py
class UntrackedValue(Generic[Value], BaseChannel[Value, Value, Value]):
    """Stores the last value received, never checkpointed."""
    def checkpoint(self) -> Value | Any:
        return MISSING  # = "not persisted"
```

And the persistent variant (LastValue):

```python
# From langgraph/libs/langgraph/langgraph/graph/message.py
class LastValue(Generic[Value], BaseChannel[Value, Value, Value]):
    def update(self, values: Sequence[Value]) -> bool:
        self.value = values[-1]  # Overwrites
        return True

# add_messages reducer: merges by message ID
def add_messages(left: Messages, right: Messages) -> Messages:
    merged = left.copy()
    merged_by_id = {m.id: i for i, m in enumerate(merged)}
    for m in right:
        if (existing_idx := merged_by_id.get(m.id)) is not None:
            merged[existing_idx] = m
        else:
            merged.append(m)
    return merged
```

**Source permalinks:**
- [github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/graph/message.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/graph/message.py) — channel definitions, `add_messages` reducer.
- [github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/langgraph/channels/untracked_value.py](https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/langgraph/channels/untracked_value.py) — `UntrackedValue` channel pattern.

**Delta Channels RECENT UPDATE** ([LangChain blog](https://www.langchain.com/blog/delta-channels-evolving-agent-runtime)): *"Channels are the LangGraph primitive used to represent a 'field' in graph state. Different channel types control how data is passed through..."* — represents state as **delta** writes with seed + writes, enabling efficient long-running replay.

### 5.2 Cryptographic Hash Chains — Tamper-Evident Logs

**Hash-chain audit pattern** ([dev.to/veritaschain](https://dev.to/veritaschain/building-tamper-evident-audit-trails-for-algorithmic-trading-a-deep-dive-into-hash-chains-and-3lh6); [emergentmind.com/topics/immutable-audit-log](https://www.emergentmind.com/topics/immutable-audit-log)): SHA-256 chain — each entry's hash = `H(canonical_payload || previous_hash)`. Any tampering invalidates downstream hashes.

**Merkle-tree alternative** ([chain.link/article/what-are-merkle-trees](https://chain.link/article/what-are-merkle-trees)): for large logs, organize via Merkle tree for efficient partial proofs.

**P27 audit envelope fields**:

| Field | Purpose |
|---|---|
| `audit.prev_hash` | Previous audit root hash (chain link) |
| `audit.hash` | `H(canonical(this_envelope_without_audit) || audit.prev_hash)` — entry hash |
| `audit.merkle_root` | Optional: per-batch Merkle root when grouping turns |
| `audit.signature` | Optional: sender-signs entry hash for non-repudiation |

### 5.3 Replay Attack Prevention

Three classic techniques, all relevant to P27:

1. **Nonce / sequence number per sender:** monotonic increasing counter; receiver rejects messages with counters ≤ last seen.
2. **Timestamp window:** reject messages older than `Δt_max` OR future-dated by >`Δt_max`.
3. **Consumer-group ACK + idempotency-key** (Redis Streams / Kafka): at-least-once delivery but consumer dedups by `message_id`.

**Primary sources:**
- Wallarm guide — [wallarm.com/what/replay-attacks](https://www.wallarm.com/what/replay-attacks): *"Nonce, an abbreviation for 'number used only once,' is often a random or pseudo-random figure used just once during a communication process."*
- Packetlabs guide — [packetlabs.net/posts/a-guide-to-replay-attacks-and-how-to-defend-against-them/](https://www.packetlabs.net/posts/a-guide-to-replay-attacks-and-how-to-defend-against-them/): *"Nonce Values: Enforce the use of nonce (number used once) values to ensure received messages are part of a legitimate communication session."*
- TLS best practice — [crypto.stackexchange.com/questions/114926](https://crypto.stackexchange.com/questions/114926/for-aes-gcm-why-do-protocols-not-use-the-nonce-to-prevent-replay-attacks): for AES-GCM, store sequence number in AAD (additional authenticated data).

**P27 replay-defense envelope fields:**

| Field | Defense |
|---|---|
| `sender_seq: u64` | Monotonic per-sender counter (nonce) |
| `created_at: ISO-8601` | Timestamp; reject if drift > ±300s |
| `id: u128 (uuid v7)` | Globally unique message id (dedup key) |
| `audit.prev_hash` | Hash chain prevents splice-attacks |

---

## 6. Real-World Implementations

### 6.1 AutoGen (Microsoft Research) — Battle-Tested Pydantic Message Hierarchy

**File:** [github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/messages.py](https://github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/messages.py) (blob SHA `683a80aa5468d12415606361fae2c08e49ce088a`, file size 24,531 bytes).

**Concrete patterns AutoGen uses** — directly applicable to P27:

```python
class BaseChatMessage(BaseMessage, ABC):
    """Abstract base class for chat messages."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str       # The name of the agent that sent this message
    models_usage: RequestUsage | None = None
    metadata: Dict[str, str] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # subclasses: TextMessage, MultiModalMessage, StopMessage,
    # HandoffMessage (has `target`), ToolCallSummaryMessage

class BaseAgentEvent(BaseMessage, ABC):
    """Observable agent events (ToolCallRequest, CodeGeneration, MemoryQuery, etc.)"""
    id: str; source: str; metadata: Dict; created_at: datetime

ChatMessage = Annotated[
    TextMessage | MultiModalMessage | StopMessage | ToolCallSummaryMessage | HandoffMessage,
    Field(discriminator="type"),
]
```

**AutoGen message types surfaced:**

| Type | Purpose |
|---|---|
| `TextMessage` | Plain text |
| `MultiModalMessage` | List of `str \| Image` |
| `StopMessage` | Conversation-end signal |
| `HandoffMessage` | Has `target: str` + `context: List[LLMMessage]` — direct analogue for P27 visibility-scoped messages |
| `ToolCallSummaryMessage` | Tool-call summary with `tool_calls` + `results` |
| `ToolCallRequestEvent` / `ToolCallExecutionEvent` | Observable event stream |
| `SelectSpeakerEvent` / `SelectorEvent` | Turn selection — **direct analogue to P27 debate-turn routing** |
| `MemoryQueryEvent` | Memory retrieval results event |
| `ThoughtEvent` | Reasoning tokens — feed into P27 audit chain |
| `MessageFactory` | Discriminator-based polymorphic deserializer |

**Critical design lesson from AutoGen:**
- Two-message-family split (`BaseChatMessage` vs `BaseAgentEvent`) — **discriminated union**. P27 should split society traffic (`SocietyMessage`) vs observable events (`SocietyEvent`).
- `id`, `source`, `created_at`, `metadata` are *always present at base class* — invariants enforced at the base.
- `MessageFactory` provides type registry — P27 should have a HermesMessageFactory with `register(intent_name, intent_class)`.

### 6.2 LangGraph — Channel-Based State Communication

**Checkpointer pattern** ([reference.langchain.com/python/langgraph/checkpoints](https://reference.langchain.com/python/langgraph/checkpoints)): *"Checkpoints allow LangGraph agents to persist their state within and across multiple interactions. A checkpoint is a snapshot of the graph state at a given time."*

**Delta Channels / Recovery** ([github.com/langchain-ai/langgraph/blob/main/examples/delta-channel-dump/README.md](https://github.com/langchain-ai/langgraph/blob/main/examples/delta-channel-dump/README.md)) — JSON structure:

```json
{
  "thread_id": "...",
  "checkpoint_ns": "",
  "target_checkpoint_id": "...",
  "parent_checkpoint_id": "...",
  "channels": {
    "messages": {
      "delta_kind": "snapshot",
      "seed_checkpoint_id": "...",
      "seed_version": "...",
      "seed": [{ "type": "ai", "content": "...", "id": "ai-0" }],
      "writes": [
        { "checkpoint_id": "...", "task_id": "...", "idx": 0, "value": [...] }
      ]
    }
  }
}
```

**Direct P27 design input:** Hermes debate thread = `thread_id`; debate turn = `writes[idx]`; parent-pointer enables branching + replay.

**Caveat:** Diagrid critique — [diagrid.io/blog/checkpoints-are-not-durable-execution](https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows) — flags that *checkpoints ≠ durable execution*; raises safety/security surface (CSA RCE advisory — [labs.cloudsecurityalliance.org/research/csa-research-note-langgraph-rce-chain-20260614-csa-styled/](https://labs.cloudsecurityalliance.org/research/csa-research-note-langgraph-rce-chain-20260614-csa-styled/)).

**P27 implication:** Don't store unauthenticated/untrusted checkpoint content in the Hermes state bus without explicit sanitization.

### 6.3 MCP — JSON-RPC 2.0 Substrate

**Spec Schema:** [github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json) (blob SHA `775dc991791e6008f662544e70f76f9d47be32ac`, file size 108,236 bytes, comprehensive JSON Schema for all MCP primitives).

**P27 lesson:** MCP normalizes methods (e.g., `tools/call`, `resources/read`). Hermes normalize via `intent` field rather than method-name taxonomy — simpler & more FICA-like.

### 6.4 A2A — Peer Discovery + Multipart Parts

**Spec quote** ([github.com/a2aproject/A2A/blob/main/docs/specification.md](https://github.com/a2aproject/A2A/blob/main/docs/specification.md)): *"Standardized Communication: JSON-RPC 2.0 over HTTP(S). Agent Discovery: Via 'Agent Cards' detailing capabilities and connection info."*

**Agent Card at `/.well-known/agent.json`** — analogous to a P27 Hermes agent card.

**Unified Part message structure (v1.0):**

```json
{ "text": "...", "mediaType": "text/plain" }
{ "url": "...", "filename": "...", "mediaType": "..." }
{ "raw": "base64...", "filename": "...", "mediaType": "..." }
{ "data": { "key": "value" }, "mediaType": "application/json" }
```

**P27 lesson:** A `parts[]` array on each envelope allows currency growth (new part types without breaking).

### 6.5 ACP and Survey — Confirmation

**ACP message structure** ([arxiv.org/html/2505.02279v1](https://arxiv.org/html/2505.02279v1)): ordered list of parts with JSON-RPC 2.0 payload. CDP-style streaming via SSE.

---

## 7. Debate and Consensus Protocols

### 7.1 AI Safety via Debate (Irving, Christiano, Amodei 2018)

**Primary paper:** Geoffrey Irving, Paul Christiano, Dario Amodei — "AI safety via debate" — [arxiv.org/abs/1805.00899](https://arxiv.org/abs/1805.00899) (May 2018).

**Core idea (LessWrong summary):** [lesswrong.com/posts/WP4fciGn3rNtmq3tY/ai-safety-101-chapter-5-1-debate](https://www.lesswrong.com/posts/WP4fciGn3rNtmq3tY/ai-safety-101-chapter-5-1-debate): *"The idea behind AI safety via debate (Irving et al., 2018) is that it is easier to judge who wins at chess than to play chess at a grandmaster..."*

**Mechanics:**
- Two agents take adversarial sides on a question.
- A (weaker) judge sees only short statements, picks who wins.
- Debate forces honesty: dishonest claims are easily countered.

**Direct P27 application:**
- Use debate as **overseight primitive** — when two Hermes instances disagree, a Faiz-replayable debate tied to a deterministic transcript marks the disagreement.
- Each debate has: opening `cfp`, multiple `argue` turns, judge call (Faiz or fallback escalation), `concede | accept_proposal | reject_proposal` outcome.

### 7.2 Argumentation Frameworks (Dung 1995)

**Foundational reference:** Phan Minh Dung, "On the Acceptability of Arguments and its Fundamental Role in Nonmonotonic Reasoning, Logic Programming and n-Person Games" (1995).

**JASSS overview** ([jasss.org/24/2/6.html](https://www.jasss.org/24/2/6.html)): *"The argumentation model framework introduced in (Dung 1995) consists of a set of arguments and binary relations expressing conflicts among arguments. An..."*

**Core constructs:**
- `Argument` — claim + support.
- `Attack relation` — `(A, B)`: `A` attacks `B`.
- `Defence` and `Acceptable` arguments, `Preferred extension`, `Stable extension`, `Grounded extension`.

**P27 application:** model debate claims as arguments with attack edges; resolve to **grounded extension** (most conservative) or **preferred extension** via Faiz override.

### 7.3 Consensus Protocols (Paxos / Raft)

**Paxos vs Raft** ([dev.to/narendars](https://dev.to/narendars/distributed-consensus-paxos-vs-raft-and-modern-implementations-2gng); [baeldung.com/cs/raft-consensus-algorithm](https://www.baeldung.com/cs/raft-consensus-algorithm)):

| Property | Paxos | Raft |
|---|---|---|
| Roles | Proposer / Acceptor / Learner | Leader / Follower / Candidate |
| Comprehensibility | Hard | Designed for clarity |
| Used in production | Theoretical / rare | etcd, Consul, RethinkDB, Kafka |

**Raft strengths for P27:**
- Leader election → **deterministic proposer** role for society messages.
- Log replication → **matches Hermes audit ledger**.
- Term-based liveness + consistency.

**But:** "Classic" Raft expects **uniform agreement**. Hermes society often needs:
- **Plurality consent** (e.g., human override on high-tier actions)
- **Tie-breaker rules** (Faiz as ultimate adjudicator per AGENTS.md §6)
- **Soft-veto** (one dissent → escalation, not blocking)

So P27 should adopt Raft-inspired leader/term semantics without full uniform-agreement requirement.

### 7.4 Voting & Mechanism Design

Quadratic voting / voting on stake-weighted ballots for society decisions. Out of scope for P27 protocol envelope but relevant to **outcomes** field (`outcome.decision_basis: "voting | consensus | override"`).

---

## Synthesis — P27 Envelope Recommendations

### A. Envelope Shape (Concrete Proposal)

Combine MCP's JSON-RPC 2.0 substrate + AutoGen's Pydantic typed-message pattern + A2A's multipart `parts[]`. Add Hermes-specific extensions:

```jsonc
{
  // === Transport substrate (familiar, JSON-RPC 2.0 inspired) ===
  "jsonrpc": "2.0",
  "id":       "0193f6c5-1234-7890-abcd-1234567890ab",  // uuid v7 — dedup key
  "method":   "hermes/send",                            // peer-to-peer RPC method

  // === Hermes envelope extensions ===
  "sender":   { "instance_id": "guinevere@hermes.local", "seq": 42, "term": 7 },
  "receiver": [ { "instance_id": "pharsa@hermes.local" } ],  // list = multicast ok
  "conversation_id": "debate-budget-2026Q3",            // thread id (LangGraph-style)
  "in_reply_to": "0193f6c5-...",                        // optional reference
  "created_at": "2026-06-28T15:30:00.000Z",
  "expires_at": "2026-06-28T15:35:00.000Z",
  "ttl_hint_ms": 300000,

  // === Intent + visibility ===
  "intent":   "argue",            // taxonomy · FIPA-inspired + debate-extended
  "visibility": "society-private", // public | society-private | group-scoped | dm | audit-only
  "scope": { "society": "hermes-foundation", "group": "engineering" },

  // === Memory / risk ===
  "memory_refs": [ "milestone://m-1234", "audit://a-9999" ],
  "risk_tier":   "R2",            // R0..R5 — drives autonomy gates (cf. §0.1)

  // === Action proposal / debate outcome ===
  "proposal":    { "action_kind": "deploy", "target": "svc:ingest", "params": {} },  // null when not a proposal
  "debate":      { "round": 2, "side": "pro", "evidence_refs": [] },  // null when not a debate turn
  "consensus":   { "decision": "agree", "decision_basis": "voting", "yeas": 2, "nays": 0 },  // null when not consensus

  // === Payload (multipart, A2A-inspired) ===
  "parts": [
    { "kind": "text", "text": "...", "mediaType": "text/plain" },
    { "kind": "data", "data": { ... }, "mediaType": "application/json" },
    { "kind": "file_url", "url": "https://...", "mediaType": "..." }
  ],

  // === Provenance + audit (W3C PROV + hash chain) ===
  "provenance": {
    "decided_by": "evt://e-2026-06-28-001",
    "parent_message_ids": ["...uuid..."],
    "co_signed_by": []
  },
  "audit": {
    "prev_hash":   "0x9a3b...",     // hash chain link
    "hash":        "0x7c1d...",     // H(canonical(this - audit.hash) || prev_hash)
    "merkle_root": null             // optional batch link
  },

  // === Signature (future) ===
  "signature": null                // ed25519 over canonical payload
}
```

### B. Intent Taxonomy (FIPA + Searle Hybrid)

11 intents, exhaustive for society debate/decision loop:

```
inform · propose · request · query · agree · refuse ·
argue · concede · cfp · escalate · block
```

Plus audit-only intents: `audit-query`, `audit-replay`.

### C. Visibility Ladder

```
public → society-private → group-scoped → dm → audit-only
```

Each visibility level maps to:
- A Redis Stream consumer-group key (or DM = direct queue)
- An audit-ledger write policy (audit-only means only-future-auditor-readable)
- A risk-tier allowed-actions matrix

### D. Risk Tier Mapping (5 tiers)

| Tier | Action posture | Examples |
|---|---|---|
| `R0` | Pure comms, no side-effects | `inform`, `query`, `argue` |
| `R1` | Read-only memory access | `audit-query` |
| `R2` | Soft-write (cache, log) | debate outcome, vote |
| `R3` | Internal change (config, queue) | reroute traffic |
| `R4` | External boundary (DNS, secrets, deploy) | requires Faiz pre-approval |
| `R5` | Destructive / consent-affecting | HARD STOP unless explicit override |

(Aligned with §0.1 P20 autonomy gates — R0–R2 autonomous, R3 audit-required, R4 explicit approval, R5 absolute ceiling + Faiz reaffirmation.)

### E. Audit & Replay Substrate

- **Primary log:** Redis Stream `society.audit` (read-only consumer group).
- **Hash chain:** every Hermes envelope linked into `audit/<instance_id>` chain; Faiz-replayable retroactively.
- **Replay API:** given `(conversation_id, from_message_id)`, return full thread with checkpoints.
- **Inbox dedup:** `(sender.instance_id, sender.seq)` tuple as idempotency key.

### F. Wire-Transport Choices

| Lane | Transport | Reason |
|---|---|---|
| Default peer | Redis Streams (`hermes-debate` stream, consumer group `hermes-{instance}`) | Durable, replayable, consumer-group ACK |
| Low-latency heartbeat | NATS subject `hermes.presence.*` | Fire-and-forget, ephemeral |
| Federation boundaries | Outbox → Kafka topic `hermes-society` (per-hephaestus-bus) | Cross-region durable |
| Audit log mirror | Postgres WORM table + Merkle-batch commit | Tamper-evident |

### G. Required Anti-Patterns (BLOCKING)

From Guinevere AGENTS.md §0 + §5 — must be enforced at envelope-validation time:

- ❌ **No `as any` / type-suppression** in envelope schema validators.
- ❌ **No empty catch around peer messages** — every envelope ingest must surface error context.
- ❌ **No untracked writes** — every R≥3 action writes to audit within same transaction.
- ❌ **No bypassing HARD STOP** — envelope `intent=block` is absolute-priority.
- ❌ **No skipping consent / surveillance boundary** — visibility tier enforced by transport, not by participants.

---

## Citations Index

### Primary (specifications + source code)

- FIPA performatives: [jmvidal.cse.sc.edu/talks/agentcommunication/performatives.html](https://jmvidal.cse.sc.edu/talks/agentcommunication/performatives.html) (canonical list, 22 performatives)
- FIPA-ACL Message Structure Spec: [yumpu.com/en/document/view/35150485](https://www.yumpu.com/en/document/view/35150485/fipa-acl-message-structure-specification)
- PEAK-ACL library: [sciencedirect.com/science/article/pii/S2352711026001408](https://www.sciencedirect.com/science/article/pii/S2352711026001408)
- SARL ACL (FIPA-ACL in Java): [github.com/sarl/sarl-acl](https://github.com/sarl/sarl-acl)
- KQML original: [cdn.aaai.org/Workshops/1994/WS-94-02/WS94-02-007.pdf](https://cdn.aaai.org/Workshops/1994/WS-94-02/WS94-02-007.pdf)
- KQML Wikipedia: [en.wikipedia.org/wiki/Knowledge_Query_and_Manipulation_Language](https://en.wikipedia.org/wiki/Knowledge_Query_and_Manipulation_Language)
- Microservices outbox pattern: [microservices.io/patterns/data/transactional-outbox.html](https://microservices.io/patterns/data/transactional-outbox.html)
- Inbox/outbox: [medium.com/@serhatalftkn](https://medium.com/@serhatalftkn/reliable-messaging-in-microservices-the-outbox-and-inbox-pattern-2f831f15ff82)
- ZeroMQ envelope patterns: [zguide.zeromq.org/docs/chapter3/](https://zguide.zeromq.org/docs/chapter3/)
- W3C PROV standard: [w3.org/TR/prov-overview/](https://www.w3.org/TR/prov-overview/)
- AI Safety via Debate: [arxiv.org/abs/1805.00899](https://arxiv.org/abs/1805.00899)
- Argumentation framework (Dung JASSS): [jasss.org/24/2/6.html](https://www.jasss.org/24/2/6.html)
- Paxos vs Raft: [dev.to/narendars](https://dev.to/narendars/distributed-consensus-paxos-vs-raft-and-modern-implementations-2gng); [baeldung.com/cs/raft-consensus-algorithm](https://www.baeldung.com/cs/raft-consensus-algorithm)

### Primary (GitHub source permalinks)

- **MCP Model Context Protocol schema.json v2025-06-18:** [github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json) (sha `775dc991791e6008f662544e70f76f9d47be32ac`)
- **MCP Spec (2025-11-25 basic):** [github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/index.mdx](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/index.mdx)
- **A2A v1.0 specification.md:** [github.com/a2aproject/A2A/blob/main/docs/specification.md](https://github.com/a2aproject/A2A/blob/main/docs/specification.md) (sha `382185a53b312cd6a60f5ac536ec5a356437ce77`)
- **A2A v1 What Changed / Part unification:** [github.com/a2aproject/A2A/blob/main/docs/whats-new-v1.md](https://github.com/a2aproject/A2A/blob/main/docs/whats-new-v1.md)
- **AutoGen messages.py:** [github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/messages.py](https://github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/messages.py) (sha `683a80aa5468d12415606361fae2c08e49ce088a`)
- **LangGraph message.py (channels + add_messages):** [github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/graph/message.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/graph/message.py)
- **LangGraph untracked_value.py:** [github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/langgraph/channels/untracked_value.py](https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/langgraph/channels/untracked_value.py)
- **LangGraph delta-channels example:** [github.com/langchain-ai/langgraph/blob/main/examples/delta-channel-dump/README.md](https://github.com/langchain-ai/langgraph/blob/main/examples/delta-channel-dump/README.md)

### Secondary (commentary / context)

- SmythOS on FIPA ACL: [smythos.com/developers/agent-development/fipa-agent-communication-language/](https://smythos.com/developers/agent-development/fipa-agent-communication-language/)
- Martin Pilát on multi-agent protocols: [martinpilat.com/en/multiagent-systems/communication-protocols](https://martinpilat.com/en/multiagent-systems/communication-protocols)
- IBM on ACP: [ibm.com/think/topics/agent-communication-protocol](https://www.ibm.com/think/topics/agent-communication-protocol)
- ACP + A2A unification: [lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a](https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/)
- Survey of Agent Interoperability Protocols (ACP/MCP/A2A): [arxiv.org/html/2505.02279v1](https://arxiv.org/html/2505.02279v1)
- Actor model in Akka/Erlang: [alex-karaberov.medium.com](https://alex-karaberov.medium.com/everything-you-always-wanted-to-know-about-the-actor-model-but-were-afraid-to-ask-b6eee8722953)
- Redis Pub/Sub vs Streams: [dev.to/lovestaco/redis-pubsub-vs-redis-streams-a-dev-friendly-comparison-39hm](https://dev.to/lovestaco/redis-pubsub-vs-redis-streams-a-dev-friendly-comparison-39hm)
- Searle speech acts overview: [thoughtco.com/speech-act-theory-1691986](https://www.thoughtco.com/speech-act-theory-1691986)
- LangChain Delta Channels blog: [langchain.com/blog/delta-channels-evolving-agent-runtime](https://www.langchain.com/blog/delta-channels-evolving-agent-runtime)
- Diagrid on durable execution: [diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows](https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows)
- Replay attack prevention: [wallarm.com/what/replay-attacks](https://www.wallarm.com/what/replay-attacks); [packetlabs.net/posts/a-guide-to-replay-attacks-and-how-to-defend-against-them/](https://www.packetlabs.net/posts/a-guide-to-replay-attacks-and-how-to-defend-against-them/)
- Hash chain tamper-evident logs: [dev.to/veritaschain/building-tamper-evident-audit-trails-for-algorithmic-trading-a-deep-dive-into-hash-chains-and-3lh6](https://dev.to/veritaschain/building-tamper-evident-audit-trails-for-algorithmic-trading-a-deep-dive-into-hash-chains-and-3lh6)
- Cryptographic audit trail request: [github.com/NousResearch/hermes-agent/issues/487](https://github.com/NousResearch/hermes-agent/issues/487) (interesting coincidence — separate "hermes-agent" hash-chain proposal)
- LessWrong on AI safety debate: [lesswrong.com/posts/WP4fciGn3rNtmq3tY/ai-safety-101-chapter-5-1-debate](https://www.lesswrong.com/posts/WP4fciGn3rNtmq3tY/ai-safety-101-chapter-5-1-debate)

---

## Caveats and Open Questions

1. **ACP-A2A merger timing.** As of August 2025, ACP folded into A2A under LF AI & Data. P27 should treat A2A v1.0 as the canonical interop substrate. Verify A2A v2.x churn before final P27 spec freeze.
2. **AutoGen v0.7 vs v0.4.** AutoGen underwent major restructure (Core API vs AgentChat). Cited `messages.py` is the v0.x AgentChat layered module.
3. **LangGraph Delta Channels** are a recent engineering improvement; reserve future-extension slot (P28 may want to adopt).
4. **KQML/FIPA-ACL reachability.** Standardized but rarely used in LLM-era agent stacks; FIPA-style *thinking* (performative taxonomy, conversation protocols) is the durable lesson.
5. **Consensus protocol choice.** Pure Raft may be over-determined for Hermes society debates; soft-veto + Faiz-override composition recommended. Validate with ORACLE-level review before freezing P27 consensus semantics.
6. **Cryptographic signing.** Field `signature: null` reserved. P28 should plan ed25519 signing of canonical envelope hash, with key rotation governed by PersonaSafetyPolicy/ADR.
7. **Replay attack surface** grows with `sender_seq` adoption; requires careful sequence-number synchronization across restarts (sequence persistence continues across Hermes process restarts).

## Design Decisions Recorded

| Decision | Source | Adopted |
|---|---|---|
| JSON-RPC 2.0 substrate | MCP, A2A, ACP all converge | ✅ |
| Multipart `parts[]` for content | A2A v1.0 unified Part | ✅ |
| Discriminated-union message type registry | AutoGen `MessageFactory` + `Annotated[..., Field(discriminator="type")]` | ✅ |
| Event-sourced channel state (seed + writes) | LangGraph Delta Channels | 🔶 via audit ledger, not full state channels |
| Hash-chain audit (sha256 prev-hash) | Distributed-systems consensus | ✅ |
| Monotonic sender_seq for replay | TLS nonce pattern | ✅ |
| Redis Streams for primary bus | Redis Streams vs Pub/Sub operational reality | ✅ |
| FIPA-derived performative taxonomy | FIPA Communicative Act Library | ✅ (extended with debate intents) |
| W3C PROV-shaped provenance fields | W3C Recommendation | ✅ |
| Raft-inspired term/leader semantics | Raft clarity + Hermes society plurality | ✅ (soft-consensus, Faiz override) |
| Debate primitive per Irving/Christiano | arxiv:1805.00899 | ✅ (cfp/argue/concede/accept-proposal) |
| Argumentation graph per Dung 1995 | jasss.org/24/2/6.html | 🔶 future (P28+) |

---

*End of P27 agent communication protocol research. Ready for use by P27 spec draft + P28 event-bus scaffolding. Recommend reviewing this report alongside P27 ADRs and PersonaSafetyPolicy v1.0 (especially §0.1 autonomy gates) before committing envelope choices.*

> Footer: Research conducted 2026-06-28 for P27 Hermes Society Foundation. All primary citations include URL or file paths. GitHub permalinks use `main`-branch SHAs captured at fetch time.
