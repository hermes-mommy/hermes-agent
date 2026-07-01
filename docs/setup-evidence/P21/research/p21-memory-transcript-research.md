# P21 Voice Interface — Memory / Transcript / Retention Research

**Researcher role:** Memory / Transcript / Retention
**Document status:** Planning-only research — no runtime code, deployment, or restart is proposed.
**Grounding:** `src/memory/models.py`, `docs/30-data/*`, `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`, `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`

---

## 1. Executive Decision (Planning)

A voice turn produces a **text transcript** plus an optional **raw audio blob**. Treat the transcript as an untrusted text surface (analogous to a spoken message) and route it through the existing HARD STOP / distress / injection-sanitization pipeline before it reaches memory. Store the transcript in `memory.episodes`. Do **not** keep raw audio by default; if retained for diagnostics, store it in `surveillance.events.raw_payload` for a maximum of 24 hours, encrypted, then auto-purge.

---

## 2. Schema Fit

### 2.1 Transcript -> `memory.episodes`

`src/memory/models.py` defines the `Episodes` model with the `ClassificationMetaMixin` and these relevant columns:

| Column | Proposed Value for Voice Turn | Reason |
|--------|-------------------------------|--------|
| `episode_type` | `'voice_turn'` | Distinguishes spoken turns from text/chat turns |
| `raw_content` | Redacted transcript text | Full transcript after secret/injection redaction |
| `source` | `'voice'` | Provenance label for cross-reference |
| `embedding` | `Vector(1536)` | Semantic search via existing EmbeddingService |
| `search_vector` | auto-generated tsvector | Existing full-text search |
| `do_not_recall` | `true` if safe-word/intimate/distress | Reuses existing DNR mechanism |
| `importance` | 4-6 depending on safety signal | Aligns with `MemoryRecallEvaluationSpec` ranking |
| `classification` | `Restricted` default; `Critical` if intimate/safe-word | Per `DataGovernance_ClassificationPolicy` §4 |
| `retention_class` | `Short Raw` or `Long-Term Curated` | Depends on redaction outcome |
| `retention_until` | Computed from policy | See storage decision table |
| `access_policy` | `'guinevere-core'` | Default per `ClassificationMetaMixin` |
| `encryption_profile` | `'envelope-AES-256-GCM'` | Default; double-encrypt if Critical |
| `deletion_state` | `'active'` / `'do_not_recall'` | Reuses governance states |

### 2.2 Raw Audio -> `surveillance.events.raw_payload`

`src/memory/models.py` `SurveillanceEvents` has:

```python
raw_payload: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
extracted_facts: Mapped[Optional[JsonObject]] = mapped_column(JSONB, nullable=True)
summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
```

If raw audio is retained, the recommended mapping is:

| Field | Value |
|-------|-------|
| `event_type` | `'voice_raw_audio'` |
| `device_id` | FK to `surveillance.device_registry` entry for the voice endpoint/client |
| `raw_payload` | Encrypted audio bytes (max 24h) |
| `extracted_facts` | `{"transcript_id": "<episodes.id>", "stt_engine": "...", "duration_ms": ...}` |
| `summary` | Short non-content descriptor, e.g. `"voice turn at 2026-06-24T..."` |

**Privacy-by-default recommendation:** discard raw audio immediately after STT and do not write to `surveillance.events.raw_payload`. Retain only if an explicit diagnostic/evidence scope is active, and then only with a 24-hour TTL.

---

## 3. Retention / Redaction / Classification

### 3.1 Classification and Retention

Per `docs/30-data/30-DataGovernance_Classification_v1.0.md` §4.2, the highest classification wins for mixed records, and any value containing safe-word, crisis, intimate data, or raw surveillance must be `Critical`. A voice transcript is surveillance-class input by default and should be handled as `Restricted` minimum, escalating to `Critical` when it contains safe-word, distress, intimate, or crisis content.

Per `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` §9.2 retention classes:

| Data Family | Raw Retention | Summary Retention |
|-------------|---------------|-------------------|
| Clipboard non-secret | 24 hours | Only if approved |
| Camera frames | 24 hours max | Incident/evidence summary only |
| Screenshots | 24 hours max | Incident/evidence summary only |
| Notifications/messages raw | 7 days max | 180 days minimized summary |

Voice raw audio should follow the **24-hour max raw** rule (consistent with V-013/V-014 camera/screenshot 24h raw max in `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`). The transcript, once redacted, may be promoted to `Long-Term Curated` memory if it passes the injection write-gate.

### 3.2 Redaction Rules

Before a transcript is allowed into `memory.episodes`, apply the same redactions used for clipboard/surveillance text:

1. **Secret detection** — reuse `src/surveillance/secret_scanner.py`. Detected secrets are replaced with `[REDACTED]` and the event is incident-logged (hash/category only, never plaintext).
2. **Instruction-pattern quarantine** — per `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §7.3, strip patterns such as "ignore all instructions", "override ADR", "safe word is disabled", etc. If instruction patterns are found, the transcript must be quarantined and **not** written to memory.
3. **Intimate content minimization** — if the transcript is classified `Critical`, double-encrypt `raw_content` and mark `do_not_recall` when appropriate.

---

## 4. Injection Write-Gate (Hard-Rejection Rule)

Per `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §9.1 (MEM-001..008), a transcript must **not** be written to memory until it passes:

| Rule | Enforcement |
|------|-------------|
| MEM-001 | Validate source trust level before storage (voice = Trust Level 5/6) |
| MEM-002 | Quarantine if Trust Level 5-6 |
| MEM-003 | Block if instruction patterns detected |
| MEM-004 | Block if fact would remove/weaken safety boundaries |
| MEM-005 | Do not auto-promote surveillance data to memory |
| MEM-006 | Injection check gate before promotion |
| MEM-007 | Safety-state check before promotion |
| MEM-008 | Block promotion during restricted states |

**Hard-rejection rule:** if any MEM-001..008 check fails, the transcript is dropped from memory and only a minimal, non-punitive audit event is recorded. This is non-negotiable.

---

## 5. `do_not_recall` for Voice Content

`memory.episodes.do_not_recall` already exists in `src/memory/models.py`.

A voice episode should be marked `do_not_recall = true` when:

- The transcript contains a spoken safe-word / HARD STOP trigger (`src/core/services/hard_stop_handler.py` exact/semantic patterns).
- The transcript contains high-confidence distress or crisis language (D3/D4 per `PersonaSafetyPolicy` §8.1).
- The transcript is classified `Critical` due to intimate content and Faiz has not explicitly approved recall.

This reuses the existing eight-layer DNR enforcement chain from `docs/30-data/34-MemoryRecallEvaluationSpec_v1.0.md` §9.1.

---

## 6. Provenance / Source Labels

Every stored voice fact must carry the source/confidence taxonomy from `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §9.3:

| Label | Value for Voice |
|-------|-----------------|
| `source_type` | `'voice'` |
| `source_trust` | `'quarantined_5'` (if sanitized) or `'untrusted_6'` (raw) |
| `confidence` | `medium`/`high` based on STT confidence |
| `storage_date` | ISO 8601 timestamp of storage |
| `last_validated` | Same as `storage_date` on first write |
| `do_not_recall` | `true`/`false` per §5 |

These labels must be carried into any derived `memory.semantic_facts` row linked via `source_episode`.

---

## 7. Audit Trail

Voice safety events must be written to `audit.audit_trail` (`src/memory/models.py` `AuditTrail`):

```python
event_type: str          # e.g. "voice_safeword_spoken", "voice_distress_detected", "voice_injection_blocked"
event_payload: JsonObject # minimal: {episode_id, trigger_type, vector_id, content_hash}
principal: str           # "guinevere:voice_pipeline"
event_hash: str          # SHA-256 of this event
previous_hash: str       # previous audit_trail event_hash for hash chain
occurred_at: datetime
```

Per `PersonaSafetyPolicy` §16, logs must be:
- Minimal (no full intimate transcript unless formally required)
- Non-punitive
- Encrypted if Critical
- Linked to the hash chain via `event_hash` + `previous_hash`

---

## 8. Consent Revocation Cascade

Per `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` §5.2 and §9, if voice consent is revoked:

1. Stop voice collection immediately.
2. Mark all voice-derived `memory.episodes` rows with `deletion_state = 'pending_delete'` or `do_not_recall = true`.
3. Purge raw audio from `surveillance.events.raw_payload` for `event_type = 'voice_raw_audio'`.
4. Record the cascade in `consent.revocation_log.cascade_effects` (JSONB), e.g.:

```json
{
  "affected_tables": ["memory.episodes", "surveillance.events"],
  "affected_episode_ids": ["<uuid1>", "<uuid2>"],
  "raw_audio_object_keys": ["s3://.../voice-raw-uuid1.opus"],
  "deletion_state": "pending_delete",
  "purged_at": "2026-06-24T..."
}
```

---

## 9. Concrete Storage Decision Table

| Artifact | Table | Default Class | Retention Class | Retention Until | Redaction | Encryption |
|----------|-------|---------------|-----------------|-----------------|-----------|------------|
| Redacted transcript (approved) | `memory.episodes` | Restricted | Long-Term Curated | Indefinite while consent active | Secret/instruction scan; intimate minimized | envelope-AES-256-GCM (double if Critical) |
| Safe-word/distress transcript | `memory.episodes` | Critical | Long-Term Curated (DNR) | Indefinite DNR | Full redaction; mark DNR | double-AES-256-GCM |
| Raw STT confidence metadata | `memory.episodes.key_insights` | Internal | Long-Term Curated | Same as episode | None | disk + TLS |
| Raw audio (default) | — | — | — | Discarded after STT | — | — |
| Raw audio (diagnostic only) | `surveillance.events` | Critical | Short Raw | 24 hours | No raw transcript stored | double-AES-256-GCM |
| Safety event | `audit.audit_trail` | Confidential/Restricted | Regulated/Audit | 1 year | Minimized payload | envelope-AES-256-GCM |
| Revocation record | `consent.revocation_log` | Internal | Long-Term Curated | Indefinite | Cascade IDs only | disk + TLS |

---

## 10. Cross-Reference to Other P21 Specialists

- **Safety/security specialist:** HARD STOP already operates on text; voice transcript reuses it unchanged (`src/core/services/hard_stop_handler.py`).
- **STT/TTS specialist:** provides transcript text and optionally raw audio; this report defines where those artifacts land.
- **Discord/UX specialist:** voice channel is just another input surface; memory retention is channel-agnostic.
- **Consent/surveillance specialist:** cross-reference `docs/setup-evidence/P21/research/p21-consent-surveillance-research.md` for consent scope and revocation cascade.

---

## 11. Open Questions / Backlog

1. Should we create a dedicated `event_type` enum value in `surveillance.events` for voice raw audio, or reuse a generic `'raw_media'` type?
2. Should voice episodes be excluded from FSRS spaced-repetition review by default?
3. Do we need a separate `memory.voice_turns` helper table, or is `episode_type='voice_turn'` sufficient?
4. Exact STT confidence threshold below which a transcript is discarded rather than stored.

---

## 12. Summary of Recommendations

1. **Default discard raw audio** after STT; keep only the redacted transcript in `memory.episodes`.
2. **Transcript = untrusted text.** Run existing HARD STOP, secret scanner, and instruction-pattern sanitizer before write.
3. **Hard-reject memory write** if any MEM-001..008 injection gate fails.
4. **Use existing columns** (`do_not_recall`, `ClassificationMetaMixin`) rather than new tables.
5. **Raw audio 24h max** if ever retained, in `surveillance.events.raw_payload`, encrypted, auto-purged.
6. **Audit to `audit.audit_trail`** with hash chain; minimal, non-punitive.
7. **Consent revocation** cascades through `consent.revocation_log.cascade_effects` to purge voice episodes and raw audio.
