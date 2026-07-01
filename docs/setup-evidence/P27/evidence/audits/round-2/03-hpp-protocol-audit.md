---
title: "HPP Protocol Envelope Fixes — Round 2 Audit"
audit_id: "P27-R2-03"
phase: "P27 Hermes Society Foundation"
audit_type: "Protocol Specification Audit"
date: "2026-06-28"
auditor: "Guinevere (parent agent)"
scope:
  - docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md (§5 L875-1142)
  - docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md (§5 HPP impl spec)
verdict: "NEEDS REVIEW (1 regression found)"
---

# HPP Protocol Envelope Fixes — Round 2 Audit

## 1. Audit Summary

| # | Check | Verdict | Detail |
|---|---|---|---|
| 1 | `idempotency_key` in HPP envelope JSON | **PASS** | Present in plan §5.2 (L898), blueprint §5.1 (L2109, L2147) |
| 2 | UUID v4 consistently (no v7 regressions) | **FAIL** | Plan §5.10 (L1092) says `id (UUID v7, dedup key)` — contradicts §5.2 envelope schema (L897: `uuid v4`) |
| 3 | Simplification note (flattened structures) | **PASS** | Blueprint L2157: explicit note about P28 flat envelope vs P27 nested |
| 4 | 11-intent taxonomy consistent | **PASS** | Plan §5.4 (L994-1006) = blueprint §5.3 (L2178-2188), same 11 intents |
| 5 | 5-tier visibility model consistent | **PASS** | Plan §5.5 (L1021-1027) = blueprint §5.4 (L2198-2203), same 5 tiers |
| 6 | SHA-256 hash-chain referenced | **PASS** | Plan §5.2 (L952-953), §5.9 (L1072-1073); blueprint L2145-2146, L437-439 |
| 7 | Redis Streams transport referenced | **PASS** | Plan §5.1 (L879), §5.7 (L1049-1050); blueprint §5.2 (L2159-2170), Step 8 |
| 8 | `sender_seq` + `idempotency_key` BOTH for replay | **PASS** | Plan §5.8 (L1063); blueprint `pharsa.yaml` L461 `inbox_dedup_by: [sender_seq, idempotency_key]` |

**Overall verdict: NEEDS REVIEW** — 7/8 checks pass; 1 regression found (UUID v7 vestige in §5.10).

---

## 2. Detailed Findings

### 2.1 Check 1: `idempotency_key` in HPP Envelope — PASS

**Evidence:**

| Location | Value | Status |
|---|---|---|
| P27 plan §5.2 (L898) | `"idempotency_key": "<uuid v4 — replay defense, UNIQUE on (received_by, idempotency_key)>"` | ✅ Present |
| P28 blueprint §5.1 (L2109) | `"idempotency_key": "<uuid v4 — replay defense>"` | ✅ Present |
| P28 blueprint §5.1 (L2147) | `"idempotency_key": "<uuid v4>"` (in provenance/audit section of same JSON) | ✅ Present |
| P28 blueprint Step 8C (L1583) | "Idempotency via `idempotency_key` UNIQUE constraint" | ✅ Present |
| P28 blueprint Step 9A (L1665-1667) | "`hpp_inbox` table with UNIQUE constraint on `(received_by, idempotency_key)`" | ✅ Present |
| P28 blueprint `pharsa.yaml` (L461) | `inbox_dedup_by: [sender_seq, idempotency_key]` | ✅ Present |

**Verdict:** PASS. `idempotency_key` is fully integrated across envelope schema, outbox pattern, inbox dedup, and config.

**Note:** The blueprint §5.1 JSON schema has `idempotency_key` appearing twice (L2109 in the header section, L2147 in the provenance/audit section). This is a cosmetic duplication — the second instance is inside a JSONC comment block and not structurally harmful, but implementers should be aware that the canonical placement is at the top level (L2109).

---

### 2.2 Check 2: UUID v4 Consistency — FAIL (1 regression)

**Evidence of v4 (correct):**

| Location | Field | Version |
|---|---|---|
| P27 plan §5.2 (L897) | `"id": "<uuid v4 — globally unique, message identity>"` | ✅ v4 |
| P27 plan §5.2 (L898) | `"idempotency_key": "<uuid v4 — replay defense, ...>"` | ✅ v4 |
| P28 blueprint §5.1 (L2108) | `"id": "<uuid v4>"` | ✅ v4 |
| P28 blueprint §5.1 (L2109) | `"idempotency_key": "<uuid v4 — replay defense>"` | ✅ v4 |
| P28 blueprint §5.1 (L2147) | `"idempotency_key": "<uuid v4>"` | ✅ v4 |

**REGRESSION — v7 vestige:**

| Location | Field | Version | Issue |
|---|---|---|---|
| **P27 plan §5.10 (L1092)** | `id (UUID v7, dedup key)` | ❌ **v7** | Contradicts §5.2 envelope schema (L897: `uuid v4`). §5.10 replay defense table was NOT updated during Phase 7 fixes. |

**Context:** P27 plan §5.10 (Replay Attack Defense table, L1086-1093) still references `UUID v7` for the `id` field, while §5.2 (Message Envelope schema, L897) correctly specifies `uuid v4`. The Phase 7 fixes updated §5.2 but missed §5.10.

**Note:** P27 plan L361 mentions "UUID v7 or {slug}-v{epoch}-{short_hash}" for `society_id` — this is a different field (society identity, not message identity) and uses a slug format in practice (`hsoc-foundation-v1`), so it is NOT a regression. It is a separate convention that does not affect message envelope idempotency.

**Fix required:** Change P27 plan §5.10 (L1092) from:
```
| `id` (UUID v7, dedup key) | Inbox check: rejects duplicates |
```
to:
```
| `id` (UUID v4, dedup key) | Inbox check: rejects duplicates |
```

---

### 2.3 Check 3: Simplification Note (Flattened Structures) — PASS

**Evidence:**

P28 blueprint L2157:

> **P28 envelope simplification note:** P28 uses a simplified flat envelope structure (top-level `scope_society`, `prev_hash`, `hash`, `signature_algorithm`, `signature_value`) instead of P27's canonical nested structures (`scope: { society, group }`, `audit: { prev_hash, hash, merkle_root }`, `signature: { algorithm, public_key_id, value }`). P29+ will implement the full nested structure with Optional fields for deferred features (e.g., `merkle_root`, `public_key_id`, `group` sub-scope).

**Mapping verified:**

| P27 Canonical (Nested) | P28 Simplified (Flat) | Status |
|---|---|---|
| `scope: { society, group }` | `scope_society: "hsoc-foundation-v1"` | ✅ Flattened |
| `audit: { prev_hash, hash, merkle_root }` | `prev_hash`, `hash` (top-level) | ✅ Flattened; `merkle_root` deferred |
| `signature: { algorithm, public_key_id, value }` | `signature_algorithm`, `signature_value` (top-level) | ✅ Flattened; `public_key_id` deferred |

**Verdict:** PASS. The simplification note is explicit, correct, and documents the deferred fields clearly.

---

### 2.4 Check 4: 11-Intent Taxonomy Consistency — PASS

**P27 plan §5.4 (L994-1006):**

| # | Intent | FIPA |
|---|---|---|
| 1 | `inform` | `inform` |
| 2 | `request` | `request` |
| 3 | `query` | `query-if` / `query-ref` |
| 4 | `assert` | `assert` |
| 5 | `propose` | `propose` |
| 6 | `consent` | `agree` / `accept-proposal` |
| 7 | `refuse` | `refuse` / `reject-proposal` |
| 8 | `debate` | `argue` (extended) |
| 9 | `banter` | (Hermes-specific) |
| 10 | `flirt` | (Hermes-specific) |
| 11 | `block` | (Hermes-specific) |

**P28 blueprint §5.3 (L2178-2188):**

```python
class Intent(str, Enum):
    INFORM, REQUEST, QUERY, ASSERT, PROPOSE, CONSENT, REFUSE, DEBATE, BANTER, FLIRT, BLOCK
```

**Verdict:** PASS. 11 intents match exactly between plan and blueprint. Names, order, and semantics are identical.

---

### 2.5 Check 5: 5-Tier Visibility Model Consistency — PASS

**P27 plan §5.5 (L1021-1027):**

| Tier | Description |
|---|---|
| `public` | All instances + Faiz + audit |
| `peer_private` | Society Members only |
| `sealed` | Sender + receiver + Faiz + auditor (encrypted) |
| `thought` | Sender only (never transmitted) |
| `action_audit` | Faiz + auditors + operator sub-agents |

**P28 blueprint §5.4 (L2198-2203):**

```python
class Visibility(str, Enum):
    PUBLIC, PEER_PRIVATE, SEALED, THOUGHT, ACTION_AUDIT
```

**Verdict:** PASS. 5 tiers match exactly. Blueprint correctly notes P28 only uses PUBLIC + PEER_PRIVATE operationally; SEALED deferred to P30.

---

### 2.6 Check 6: SHA-256 Hash-Chain Referenced — PASS

**Evidence:**

| Location | Reference |
|---|---|
| P27 plan §5.2 (L952-953) | `"hash": "H(canonical(this minus audit.hash) \|\| prev_hash) — sha256"` |
| P27 plan §5.9 (L1072-1073) | `audit.prev_hash = sha256(...)` + `audit.hash = sha256(...)` |
| P27 plan §5.9 (L1084) | "Each Society maintains ONE shared hash chain" |
| P28 blueprint §5.1 (L2145-2146) | `"prev_hash": "0000...0000"`, `"hash": "0x7c1d..."` |
| P28 blueprint `pharsa.yaml` (L437-439) | `hash_chain: algorithm: sha256, prev_hash_required: true` |
| P28 blueprint Step 8 (L1571) | "Hash chain via `compute_hash` field populated as `sign_for_chain` step" |

**Verdict:** PASS. SHA-256 is consistently specified for hash-chain computation across both files.

---

### 2.7 Check 7: Redis Streams Transport Referenced — PASS

**Evidence:**

| Location | Reference |
|---|---|
| P27 plan §5.1 (L879) | "P28 implements it on Redis Streams (primary durable transport)" |
| P27 plan §5.7 (L1050) | "Default peer dialogue: Redis Streams (`hermes:{society_id}:peer:{instance_id}` consumer group)" |
| P28 blueprint §5.2 (L2159-2170) | Full Redis Streams spec: stream name, consumer group, XADD, XREADGROUP, XACK |
| P28 blueprint Step 8 (L1575-1577) | Transport implementation: stream name, consumer group, xadd/xreadgroup |
| P28 blueprint `pharsa.yaml` (L460) | `outbox_pattern: true` |

**Verdict:** PASS. Redis Streams is the primary transport, specified consistently with consumer-group ACK semantics.

---

### 2.8 Check 8: `sender_seq` + `idempotency_key` BOTH for Replay Defense — PASS

**Evidence:**

| Location | Reference |
|---|---|
| P27 plan §5.8 (L1063) | "exactly-once at the receiver side (idempotency by `sender_seq` + `idempotency_key`)" |
| P27 plan §5.10 (L1090) | `sender.seq` in replay defense table |
| P27 plan §5.2 (L898) | `idempotency_key` in envelope schema |
| P28 blueprint `pharsa.yaml` (L461) | `inbox_dedup_by: [sender_seq, idempotency_key]` |
| P28 blueprint Step 9A (L1665-1667) | `hpp_inbox` UNIQUE on `(received_by, idempotency_key)` |

**Note:** The plan §5.10 replay defense table (L1086-1093) lists `sender.seq` but does NOT list `idempotency_key` as a row — only mentions it implicitly via the `id` field. The dual-defense pattern is correctly documented in §5.8 (L1063) and the blueprint config (L461). This is a minor documentation gap in §5.10 (the table is not exhaustive) but does not constitute a failure since the pattern is correctly specified elsewhere.

**Verdict:** PASS. Both mechanisms are present and correctly combined for defense-in-depth replay protection.

---

## 3. Regression Summary

### 3.1 UUID v7 Vestige in §5.10 (NEEDS FIX)

| Attribute | Value |
|---|---|
| File | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` |
| Location | §5.10 Replay Attack Defense table, L1092 |
| Current text | `\| \`id\` (UUID v7, dedup key) \| Inbox check: rejects duplicates \|` |
| Required text | `\| \`id\` (UUID v4, dedup key) \| Inbox check: rejects duplicates \|` |
| Severity | LOW (cosmetic — envelope schema at §5.2 L897 is correct; only the prose table is stale) |
| Risk | Implementer confusion — §5.10 table could be read as authoritative over §5.2 |
| Phase 7 missed? | Yes — Phase 7 updated §5.2 envelope schema to v4 but did not update §5.10 table |

---

## 4. Overall Assessment

| Dimension | Status |
|---|---|
| Envelope completeness | ✅ `idempotency_key` added, UUID v4 standardized in schema |
| Simplification note | ✅ Explicit flattened-structure note in blueprint |
| Intent taxonomy | ✅ 11 intents consistent across both files |
| Visibility model | ✅ 5 tiers consistent across both files |
| Hash-chain audit | ✅ SHA-256 consistently referenced |
| Transport | ✅ Redis Streams with consumer-group ACK |
| Replay defense | ✅ `sender_seq` + `idempotency_key` dual defense |
| UUID consistency | ⚠️ 1 v7 vestige in §5.10 (cosmetic, low severity) |

**Conclusion:** HPP protocol envelope fixes from Phase 7 are substantively correct. The `idempotency_key` addition is fully integrated. The simplification note is explicit and accurate. The single regression (UUID v7 in §5.10) is a cosmetic prose inconsistency that does not affect the envelope schema or P28 implementation, but should be fixed to prevent implementer confusion.

---

## 5. Recommended Action

1. **Fix §5.10 L1092:** Change `UUID v7` → `UUID v4` in the Replay Attack Defense table.
2. **Optional:** Add `idempotency_key` as an explicit row in §5.10 table for completeness (currently only `sender.seq` and `id` are listed as fields).

---

> **Audit footer:** This report was generated as part of P27 Round 2 audit cycle. Evidence path: `docs/setup-evidence/P27/evidence/audits/round-2/03-hpp-protocol-audit.md`. Verdict: NEEDS REVIEW (1 regression, low severity).
