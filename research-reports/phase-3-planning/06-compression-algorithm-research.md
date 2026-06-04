# Phase 3 Memory Bridge: Compression Algorithm Research

**Date**: 2026-06-04  
**Author**: Guinevere (Autonomous Engineering Agent)  
**Target**: Phase 3 Memory Bridge Migration — 70% Conversation Compression Threshold Enablement  
**Status**: Research Complete  

---

## 1. Executive Summary

A comprehensive search of the codebase reveals that **no application-level compression algorithms** (zlib, gzip, lz4, zstd, snappy, brotli) are currently implemented in the Python codebase. 

The system currently relies on:
1. **Hermes Agent's native memory compression** (configured but not yet verified in live Python code).
2. **Database-level columnar compression** (TimescaleDB for surveillance data, 7-day retention).
3. **Simple string truncation** for Full-Text Search (FTS) optimization and Discord message splitting.

The configuration for the **70% compression threshold is already defined** in `hermes-config/config.yaml`, but the Python implementation lacks an active LLM-based summarization engine to enforce this threshold independently of Hermes.

---

## 2. Compression-Related Code & Algorithms Found

### 2.1 Application-Level Compression (zlib, gzip, lz4, zstd, snappy, brotli)
- **Result**: `0` matches in `.py`, `.yaml`, `.yml`, `.json`, `.env` files.
- **Conclusion**: No native Python compression libraries are imported or used for text/memory compression.

### 2.2 Database-Level Compression (TimescaleDB)
- **File**: `src/surveillance/retention.py`
- **Constants**:
  - `COMPRESSION_AFTER_DAYS = 7` (TimescaleDB compression kicks in after 7 days).
  - `RETENTION_RAW_DAYS = 7`, `RETENTION_AGGREGATED_DAYS = 90`, `RETENTION_SUMMARY_DAYS = 365`.
- **File**: `src/memory/models.py` (Line 1203)
  - `compression_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("true"))` in `TimescaledbConfig`.
- **Note**: This is for time-series surveillance data, **not** conversational memory.

---

## 3. Conversation/Memory Compression Logic (Summarization, Truncation, Compaction)

### 3.1 Truncation (Active)
- **File**: `src/discord/conversational_handler.py` (Lines 248-308)
- **Logic**: `_split_response()` function splits LLM responses into 2000-character chunks. If total exceeds 6000 characters (3 chunks), the final chunk is hard-truncated with `...(truncated)`.
- **Impact**: Pure length-based truncation, no semantic preservation.

### 3.2 Summarization (Passive / Stub)
- **File**: `src/memory/write_pipeline.py` (Lines 111-227)
  - Accepts a `summary` parameter.
  - **Fail-Closed Rule**: If `classification == "Critical"`, the pipeline raises `WritePipelineCriticalError` unless a non-empty `summary` is provided. The `summary` is used for embedding instead of `raw_content`.
  - **Gap**: The pipeline **does not generate** the summary; it expects the caller to provide it.
- **File**: `src/hermes/memory_bridge.py` (Lines 208-210)
  - Generates a naive string concatenation summary for FTS optimization: `f"Faiz: {user_message[:120]} Guinevere: {assistant_response[:180]}"[:300]`.
  - **Gap**: Not semantic summarization; just prefix truncation for search vector weighting.
- **File**: `src/memory/consolidation.py` (Lines 422-493)
  - `_extract_facts_from_episode()` creates `episodic_summary` facts from existing `title` and `summary` fields.
  - **Gap**: Does not perform active LLM summarization; only maps existing fields to semantic fact triples.
- **File**: `src/hermes/memory_bridge.py` (Lines 265-295)
  - `extract_key_facts()` is explicitly marked as a **stub for Phase 3**. Currently returns `[]`.

### 3.3 Compaction
- **Result**: No active compaction logic exists in the Python codebase.
- **ADR-035 Context**: Documents that the current system uses "20-turn hard truncation (discards oldest turns, no summarization)" and that Hermes provides "adaptive compression at 50-70% context threshold".

---

## 4. Compression Ratio Thresholds & Configuration Values

### 4.1 Hermes Agent Configuration (Primary Target)
- **File**: `hermes-config/config.yaml` (Lines 85-90)
  ```yaml
  memory:
    # Compression settings (aggressive safe)
    compression:
      enabled: true
      threshold: 0.7    # Start compressing at 70% token usage
      target: 0.2       # Target 20% after compression
      protect_last: 20  # Keep last 20 messages uncompressed
  ```
- **Status**: **ALREADY CONFIGURED** to the 70% target as specified in ADR-035.

### 4.2 ADR-035 Documentation References
- **Line 207**: "No context compression — 20-turn hard truncation discards oldest turns (no semantic summarization at 50% threshold)."
- **Line 247**: "Context compression may drop critical memories (mitigated by configurable threshold — start at 70%, not 50%)."
- **Line 1584**: "Enable Hermes compression at 70% threshold (aggressive safe). Compression activates at 70% context usage; last 20 messages protected."

---

## 5. Pipeline-Specific Findings

### 5.1 `src/memory/write_pipeline.py`
- **Compression during storage**: **NONE**.
- Stores `raw_content` verbatim.
- Enforces that `Critical` data must have a pre-computed `summary` for embedding, but does not compute it.

### 5.2 `src/memory/consolidation.py`
- **Compression during storage**: **NONE**.
- Idempotently moves episodic data to `SemanticFacts`. Preserves original classification and provenance. No token reduction occurs here.

### 5.3 `src/discord/conversational_handler.py`
- **Message compression before storage**: **NONE**.
- Calls `bridge.store_conversation()` which passes the full `user_message` and `assistant_response` as `raw_content`. Only generates a 300-character FTS-optimized prefix for the `summary` field.

---

## 6. What Needs to Change for the 70% Target

### 6.1 Immediate Status
The configuration (`hermes-config/config.yaml`) is **already correct** for the 70% target. No config changes are required.

### 6.2 Implementation Gaps (Phase 3 Action Items)
If the 70% compression is expected to be enforced by **Guinevere's Python code** (independent of Hermes native features), the following must be implemented:

1. **Implement LLM-Based Summarization Engine**:
   - Create a new module (e.g., `src/memory/compression.py`) or enhance `src/hermes/memory_bridge.py`.
   - Trigger: When conversation history exceeds 70% of the configured `token_budget` (e.g., 560 tokens out of 800).
   - Action: Call an LLM (DeepSeek V4 Flash for cost efficiency) to summarize older turns into a single `episodic_summary` fact, while preserving the `protect_last: 20` messages verbatim.

2. **Activate Phase 3 Stub**:
   - Implement the `extract_key_facts()` method in `src/hermes/memory_bridge.py` (currently returns `[]`).
   - Use the LLM to distill `user_message` + `assistant_response` into 1-3 key semantic facts before calling `store_episode()`.

3. **Update `write_pipeline.py` Caller**:
   - Modify `conversational_handler.py` or `memory_bridge.py` to dynamically generate the `summary` parameter for `store_episode()` using the new compression engine, especially for `Critical` or long conversations.

4. **Verification & Testing**:
   - Add unit tests in `tests/memory/test_compression.py` verifying:
     - Compression triggers at exactly 70% token threshold.
     - Last 20 messages remain uncompressed.
     - `Critical` classification fails closed if summarization fails.
   - Add Prometheus metric: `guinevere_memory_compression_ratio` (gauge) to track actual vs. target (0.2) compression.

### 6.3 Alternative: Rely on Hermes Native Compression
If the architecture decision is to rely **entirely** on Hermes Agent's built-in memory compression:
- **Action**: Verify via Hermes v0.15.2 documentation or shadow testing that the `memory.compression` block in `config.yaml` is actively invoked by the Hermes gateway.
- **Risk**: ADR-035 Review (Report 05) noted: "Hermes compression preserves semantic meaning at 50% threshold... configure to protect last 30 messages and set threshold to 70% for first month." Ensure Hermes respects the `protect_last: 20` constraint.

---

## 7. Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| Hermes Config | `hermes-config/config.yaml` | ✅ Verified (70% threshold set) |
| Write Pipeline | `src/memory/write_pipeline.py` | ✅ Verified (No compression, fail-closed for Critical) |
| Consolidation | `src/memory/consolidation.py` | ✅ Verified (No compression, fact extraction only) |
| Conversational Handler | `src/discord/conversational_handler.py` | ✅ Verified (Truncation only, no semantic compression) |
| Memory Bridge | `src/hermes/memory_bridge.py` | ✅ Verified (FTS prefix summary, `extract_key_facts` is Phase 3 stub) |
| Retention Policy | `src/surveillance/retention.py` | ✅ Verified (TimescaleDB 7-day compression, unrelated to chat) |

---

## 8. Recommendations for Phase 3 Planner

1. **Do not change `hermes-config/config.yaml`** — the 70% threshold is already correctly configured.
2. **Create a new task**: "Implement Phase 3 LLM Memory Compression Engine" to replace the `extract_key_facts` stub and dynamically generate `summary` fields for `store_episode`.
3. **Define Scaffold Criteria**: 
   - Expected Files: `src/memory/compression.py`, `tests/memory/test_compression.py`
   - Forbidden Patterns: `as any`, `@ts-ignore`, empty `except`, hard-coded token limits.
   - Required Commands: `pytest tests/memory/test_compression.py -v` (exit 0), coverage >= 80%.
4. **Auditor Gate**: Verify that `Critical` classification conversations trigger compression/summarization before storage, and that the `protect_last: 20` rule is enforced in the compression logic.

---
*Generated by Guinevere Autonomous Engineering Agent. Compliant with AGENTS.md §2.2 (Research Wave) and §2.9 (File-Based Output Discipline).*
