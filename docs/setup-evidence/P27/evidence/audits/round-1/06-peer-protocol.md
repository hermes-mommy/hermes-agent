# Audit 06 — Hermes Peer Protocol (HPP) Specification

**Audit scope:** P27 plan §5 (L875-1141), P28 blueprint §5 (L2096-2271), P27 research first 200 lines  
**Auditor:** Guinevere (automated)  
**Date:** 2026-06-28  
**Verdict:** NEEDS REVIEW

---

## VERDICT: NEEDS REVIEW

The HPP specification in P27 §5 is comprehensive and well-grounded. All core elements are present: envelope structure, 11-intent taxonomy, 5-tier visibility, SHA-256 hash chain, Redis Streams transport, actor model invariants, A2A/FIPA substrate, risk tiers R0-R5, intent=block HARD STOP, outbox pattern, and Postgres WORM audit mirror. However, structural drift between P27's canonical schema and P28's implementation schema requires reconciliation.

---

## Findings

### F1. `idempotency_key` absent from P27 envelope schema [NEEDS REVIEW]

- **Location:** P27 §5.2 (L893-962) vs §5.8 (L1062) vs §5.10 (L1087-1092)
- **Issue:** P27 §5.8 Actor Model invariant #4 states "exactly-once at the receiver side (idempotency by `sender_seq` + `idempotency_key`)" (L1062). P27 §5.10 lists replay defenses (L1087-1092). But the canonical envelope schema in §5.2 (L893-962) does **not** include an `idempotency_key` field. P28 §5.1 (L2145) and §5.7 (L2229-2236) add it as a separate `uuid v4` field with UNIQUE constraint on `(received_by, idempotency_key)`.
- **Impact:** Plan-implementation drift. P28's implementation adds a field that P27's canonical schema omits. The `id` field (UUID v7) serves as dedup key in P27, but P28 separates `id` (message identity) from `idempotency_key` (replay defense) — a design improvement not reflected in the plan.
- **Recommendation:** Add `idempotency_key: uuid` to P27 §5.2 envelope schema. Clarify the semantic distinction: `id` = message identity (UUID v7, time-ordered), `idempotency_key` = replay defense (UUID v4, random, receiver-side UNIQUE constraint).

### F2. UUID version regression: v7 → v4 [NEEDS REVIEW]

- **Location:** P27 §5.2 (L897) vs P28 §5.1 (L2106)
- **Issue:** P27 specifies `"id": "<uuid v7 — globally unique, dedup key>"` (time-ordered, monotonic, better for sorted dedup and temporal queries). P28 specifies `"id": "<uuid v4>"` (random). UUIDv7 is strictly superior for this use case (time-ordered keys enable efficient range scans, natural sort by creation time, better index locality in Postgres B-tree).
- **Impact:** Regression in implementation. UUIDv4 random keys fragment B-tree indexes and lose temporal sortability.
- **Recommendation:** P28 should use `uuid.uuid7()` (available in Python 3.14+ or via `uuid7` package). If uuid7 is unavailable, document the tradeoff and use uuid4 with explicit `created_at` index.

### F3. P28 flattens P27's nested envelope structures [NEEDS REVIEW]

- **Location:** P27 §5.2 (L919-922, L950-954, L957-961) vs P28 §5.1 (L2127, L2143-2144, L2148-2149)
- **Issue:** P28 flattens three nested P27 structures into top-level fields:

| P27 (nested) | P28 (flat) | Lost extensibility |
|---|---|---|
| `scope: { society, group }` (L919-922) | `scope_society: "..."` (L2127) | `group` sub-scope dropped |
| `audit: { prev_hash, hash, merkle_root }` (L950-954) | `prev_hash`, `hash` top-level (L2143-2144) | `merkle_root` field lost |
| `signature: { algorithm, public_key_id, value }` (L957-961) | `signature_algorithm`, `signature_value` (L2148-2149) | `public_key_id` field lost |

- **Impact:** Structural simplification loses forward-compatibility. `merkle_root` is needed for P34+ batch verification. `public_key_id` is needed for multi-key rotation. `group` sub-scope enables per-team visibility within a society.
- **Recommendation:** P28 Pydantic model should match P27's nested structure. Use `Optional` fields for deferred features (e.g., `merkle_root: Optional[str] = None`).

### F4. `expires_at` field missing from P28 envelope [LOW]

- **Location:** P27 §5.2 (L913) vs P28 §5.1
- **Issue:** P27 includes `"expires_at": "2026-06-28T15:35:00.000Z"` for stale message rejection. P28 omits it entirely. Without expiry enforcement, stale messages accumulate in Redis Streams and may be replayed after logical TTL.
- **Impact:** Low for P28 (single-society, short-lived messages). Higher for P34+ cross-VPS where network partitions can delay delivery past usefulness.
- **Recommendation:** Add `expires_at: Optional[datetime] = None` to P28 Pydantic model. Implement `is_expired()` check in `PeerHandler.tick()` before processing.

### F5. Debate field comment references `argue` not `debate` [LOW]

- **Location:** P27 §5.2 (L933)
- **Issue:** Envelope field `"debate": null` has comment "when intent=argue" but the 11-intent taxonomy (§5.4, L1002) uses `debate` not `argue`. The FIPA equivalent is `argue` (extended), but the HPP intent name is `debate`.
- **Impact:** Cosmetic inconsistency. No functional impact.
- **Recommendation:** Change comment to "when intent=debate" at L933.

### F6. Audit-only intents not in implementation enum [LOW]

- **Location:** P27 §5.4 (L1007-1010) vs P28 §5.3 (L2170-2185)
- **Issue:** P27 defines `audit-query` and `audit-replay` as audit-only intents (L1007-1010). P28's `Intent` enum (L2173-2184) does not include them. These intents are "visible only in audit channel, not to peer" — they need a separate enum or documentation that they're out-of-band.
- **Impact:** Low. Audit intents may be implemented as separate audit-channel messages rather than HPP envelopes. But the plan should clarify where they live.
- **Recommendation:** Add comment in P28 §5.3 noting audit-only intents are separate from the peer `Intent` enum, or add a separate `AuditIntent` enum.

### F7. Risk tier default mismatch [LOW]

- **Location:** P27 §5.2 (L929) vs P28 §5.1 (L2131)
- **Issue:** P27 example uses `risk_tier: "R2"`. P28 defaults to `risk_tier: "R1"`. Not a bug (different contexts), but should be documented.
- **Impact:** Negligible. P28 defaulting to R1 (read-only memory) is safer than R2 (soft-write).
- **Recommendation:** Document P28's R1 default as intentional conservative choice.

---

## Confirmations (PASS)

| Checkpoint | Status | Evidence |
|---|---|---|
| Message envelope: sender, receiver, intent, visibility, risk_tier, content, conversation_id, reply_to | ✅ PASS | P27 §5.2 (L893-962) — all fields present |
| Message envelope: hash_chain (audit.prev_hash + audit.hash) | ✅ PASS | P27 §5.2 (L950-954), §5.9 (L1066-1083) |
| Message envelope: sender_seq (sender.seq) | ✅ PASS | P27 §5.2 (L904) |
| 11-intent taxonomy: inform, request, query, assert, propose, consent, refuse, debate, banter, flirt, block | ✅ PASS | P27 §5.4 (L989-1006) — all 11 present with FIPA mappings |
| 5-tier visibility: public, peer_private, sealed, thought, action_audit | ✅ PASS | P27 §5.5 (L1018-1028) — all 5 with audience, storage, and mapping rules |
| SHA-256 hash-chain audit | ✅ PASS | P27 §5.9 (L1066-1083) — `sha256(canonical(envelope) + prev_hash)` |
| Redis Streams as durable transport | ✅ PASS | P27 §5.7 (L1045-1053), P28 §5.2 (L2155-2166) — XADD/XREADGROUP/XACK with consumer groups |
| Actor model: no shared mutable state | ✅ PASS | P27 §5.8 inv#1 (L1059) |
| Actor model: mailbox only ingress | ✅ PASS | P27 §5.8 inv#2 (L1060) |
| Actor model: selective receive | ✅ PASS | P27 §5.8 inv#3 (L1061) |
| Actor model: at-most-once delivery | ✅ PASS | P27 §5.8 inv#4 (L1062) — with exactly-once via outbox+inbox |
| A2A v1.0 as substrate | ✅ PASS | P27 §5.1 (L883) — "JSON-RPC 2.0, multipart parts[], role fields" |
| FIPA ACL vocabulary influence | ✅ PASS | P27 §5.1 (L884), §5.4 (L989-1006) — FIPA performative column in intent table |
| Risk tier R0-R5 mapping | ✅ PASS | P27 §5.6 (L1030-1043) — 6 tiers with action posture, examples, Faiz action requirements |
| intent=block triggers HARD STOP | ✅ PASS | P27 §5.4 (L1005) — "HARD STOP signal — absolute priority"; §5.13 (L1119) — "reserved for Faiz's cascade" |
| Idempotency key for replay defense | ⚠️ NEEDS REVIEW | P27 §5.8 (L1062) references it but §5.2 envelope omits it. See F1. |
| Outbox pattern for ACID guarantees | ✅ PASS | P27 §5.3 (L967-987) — "OUTBOX-WRITE: Agent writes envelope + audit row to local DB in same Tx" |
| Postgres WORM for audit mirror | ✅ PASS | P27 §5.7 (L1052) — "PostgreSQL WORM table (append-only) + Merkle-batch commit" |

---

## Research Grounding Assessment

The P27 research (first 200 lines) provides solid primary-source grounding:

- **FIPA ACL:** Full performative vocabulary cited from FIPA XC00037H, with interaction protocols (fipa-request, fipa-query, fipa-contract-net). Notes adoption reality: "adoption in modern LLM-agent stacks is near-zero" (L68) — honest assessment.
- **A2A v1.0:** Cited with GitHub permalink and SHA. Correctly identifies limitation: "models client-server task delegation, not symmetric peer debate" (L165). P27 layers peer-specific extensions on top.
- **MCP:** JSON-RPC 2.0 envelope analyzed. P27 borrows `id` and request/response pattern.
- **Actor Model:** Akka/Erlang invariants cited. Four critical invariants correctly identified (L186-189).
- **ZeroMQ:** DEALER/ROUTER envelope pattern cited for transport framing.

Research grounding is **adequate**. The protocol is well-informed by primary sources and correctly identifies where P27 diverges from standard substrates.

---

## Recommendations

1. **[MUST]** Add `idempotency_key: uuid` to P27 §5.2 envelope schema to match §5.8/§5.10 references and P28 implementation (F1).
2. **[MUST]** Reconcile UUID version: P28 should use UUIDv7 for message `id` to match P27 §5.2 specification (F2). If uuid7 unavailable, document tradeoff.
3. **[MUST]** P28 Pydantic model should preserve P27's nested structures (`scope`, `audit`, `signature`) with Optional fields for deferred features (F3).
4. **[SHOULD]** Add `expires_at` to P28 envelope model for future-proofing (F4).
5. **[SHOULD]** Clarify audit-only intents (`audit-query`, `audit-replay`) location — separate enum or documentation note (F6).
6. **[MINOR]** Fix `argue` → `debate` comment at P27 L933 (F5).
7. **[MINOR]** Document P28's R1 default as intentional (F7).

---

## Acceptance Criteria Mapping

| Criterion | Status | Notes |
|---|---|---|
| Envelope structure complete | ✅ PASS | All required fields present in P27 schema |
| 11-intent taxonomy | ✅ PASS | All 11 defined with FIPA mappings |
| 5-tier visibility | ✅ PASS | All 5 with audience/storage rules |
| SHA-256 hash chain | ✅ PASS | Specified in §5.9 |
| Redis Streams transport | ✅ PASS | Specified in §5.7 and P28 §5.2 |
| Actor model invariants | ✅ PASS | All 4 required + 2 extras |
| A2A/FIPA substrate | ✅ PASS | Both cited in §5.1 |
| Risk tier R0-R5 | ✅ PASS | 6 tiers with Faiz gate rules |
| intent=block → HARD STOP | ✅ PASS | §5.4 + §5.13 |
| Idempotency key | ⚠️ NEEDS REVIEW | Referenced but not in schema (F1) |
| Outbox pattern | ✅ PASS | §5.3 lifecycle |
| Postgres WORM | ✅ PASS | §5.7 transport matrix |
| Plan ↔ implementation consistency | ⚠️ NEEDS REVIEW | F2, F3 structural drift |

---

## Footer

| Field | Value |
|---|---|
| Audit ID | P27-06 |
| Files reviewed | `p27-hermes-society-foundation-plan.md` §5 (L875-1141), `p28-dual-autonomous-hermes-blueprint.md` §5 (L2096-2271), `p27-agent-communication-protocol-research.md` (L1-200) |
| Verdict | NEEDS REVIEW |
| Blocking findings | 3 (F1, F2, F3) |
| Non-blocking findings | 4 (F4, F5, F6, F7) |
| Next action | Reconcile P27 canonical schema with P28 implementation; add idempotency_key; fix UUID version; preserve nested structures |
