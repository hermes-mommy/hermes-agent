# Phase 3: Memory Bridge — Detailed Procedure

## Overview

| Property | Value |
|---|---|
| **Duration** | 4-5 days |
| **Risk Level** | MEDIUM |
| **Dependencies** | Phase 2 (BLOCKING) — Discord cutover complete |
| **Additional Deps** | PostgreSQL+pgvector accessible, Embedding API (G-B1) fixed |
| **Blocks** | Phase 7 (BLOCKING) |
| **Gate** | Memory recall quality unchanged (A/B test p > 0.05). DNR + classification enforced. Zero PostgreSQL writes from Hermes path |
| **Rollback Time** | < 3 minutes (disable compression + session_search) |

### Goal Statement

Enable Hermes context compression (semantic summarization at 70% threshold) and session_search (FTS5 cross-session browsing) as read-only supplements to PostgreSQL+pgvector primary memory. Build `memory_plugin.py` as PostgreSQL bridge. Verify memory recall quality is preserved, DNR enforcement works across both recall paths, and zero PostgreSQL modifications originate from Hermes.

### Pre-Conditions

- [ ] Phase 2 cutover complete — Hermes is the sole Discord gateway
- [ ] PostgreSQL+pgvector accessible on port 5433
- [ ] Embedding API (G-B1) functional (FIX BEFORE Phase 3 if broken)
- [ ] `src/memory/` — all 7 files (3,941 lines) preserved verbatim
- [ ] `hermes_memory_bridge` PostgreSQL role exists with SELECT-only privileges
- [ ] Pre-Phase 3 row count snapshot taken

---

## Step-by-Step Procedure

### Step 3.1: Enable Hermes Compression at 70% Threshold

**Command:**
```bash
hermes config set memory.compression.enabled true
hermes config set memory.compression.threshold 0.70
hermes config set memory.compression.target 0.20
hermes config set memory.compression.protect_last 20
hermes config reload 2>/dev/null || hermes gateway restart
```

**Expected output:**
```
Config updated. Compression active at 70% threshold.
Protecting last 20 messages from compression.
```

**Verification:**
```bash
hermes config get memory.compression
# Expected: enabled=true, threshold=0.70, protect_last=20
```

**Troubleshooting:**
- If compression threshold too aggressive (drops important context) → raise to 80%, then gradually lower
- If compression never triggers → lower threshold to 50% after 1 week of monitoring
- If LLM responses reference wrong earlier messages → compression may be incorrectly summarizing. Disable: `hermes config set memory.compression.enabled false`
- If A/B recall test shows degradation → disable compression and investigate

### Step 3.2: Enable Hermes session_search (FTS5)

**Command:**
```bash
hermes config set memory.session_search.enabled true
hermes config set memory.session_search.backend "fts5"
hermes config reload 2>/dev/null || hermes gateway restart
```

**Troubleshooting:**
- If FTS5 index fails to build → check Hermes SQLite at `~/.hermes/state.db` has write permissions
- If DNR content appears in session_search results → apply `verify_recall_results_dnr_free()` as post-search gate
- If session_search returns empty → check FTS5 index built correctly. Rebuild: `hermes session rebuild-index`

### Step 3.3: Build PostgreSQL Bridge Plugin (memory_plugin.py)

**Refactoring approach:** The existing `src/hermes/memory_bridge.py` (251 lines) wraps `recall_for_context()` and `store_conversation()` from `src/memory/read_pipeline.py` and `src/memory/write_pipeline.py`. The new `plugins/memory_plugin.py` (~180 lines) wraps the same functions unchanged — it is a passthrough bridge, not a rewrite.

**Create `plugins/memory_plugin.py`:**
```python
"""HermesMemoryBridge — PostgreSQL bridge plugin for Hermes.

Wraps existing memory pipeline functions unchanged:
  - recall_for_context()  → provides context for Hermes injection
  - store_conversation()  → writes to PostgreSQL (post-cutover only)
  - verify_recall_results_dnr_free() → pre-injection DNR gate

PostgreSQL+pgvector is PRIMARY write authority (ADR-007).
Hermes SQLite stores ONLY transient session state and FTS5 indexes.
"""

import sys
import os

# Add src/ to path for importing existing memory modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from memory.read_pipeline import recall_for_context
from memory.dnr import verify_recall_results_dnr_free
from memory.classification import classify_event


class MemoryBridgePlugin:
    """Bridges Hermes context injection to PostgreSQL memory pipeline."""
    
    def __init__(self):
        self._loaded = False
        self._dnr_audit_count = 0
    
    def on_load(self, config: dict) -> bool:
        """Initialize bridge with PG connection from config."""
        try:
            self._config = config
            self._loaded = True
            print(f"[MemoryBridge] Loaded. DNR enforcement: {config.get('dnr_enabled', True)}")
            return True
        except Exception as e:
            print(f"[MemoryBridge] Load FAILED: {e}")
            return False
    
    async def recall_for_injection(self, session_id: str, query: str, limit: int = 10) -> list:
        """Recall memories for context injection. DNR-filtered."""
        results = await recall_for_context(
            session_id=session_id,
            query=query,
            limit=limit
        )
        
        # DNR pre-injection gate — strip DNR entries before returning
        filtered = verify_recall_results_dnr_free(results)
        self._dnr_audit_count += len(results) - len(filtered)
        
        return filtered
    
    def get_dnr_audit_count(self) -> int:
        """Return count of DNR entries filtered since plugin load."""
        return self._dnr_audit_count
```

**Verification:**
```bash
python -c "
from plugins.memory_plugin import MemoryBridgePlugin
plugin = MemoryBridgePlugin()
assert plugin.on_load({}), 'Plugin failed to load'
print('PASS: MemoryBridgePlugin loaded')
"
```

### Step 3.4: Configure Mirror Sync (MEMORY.md/USER.md)

**Command:**
```bash
hermes config set memory.mirrors.enabled true
hermes config set memory.mirrors.sync_interval_messages 5
hermes config set memory.mirrors.memory_md_path "/home/guinevere/code/guinevere/config/hermes/MEMORY.md"
hermes config set memory.mirrors.user_md_path "/home/guinevere/code/guinevere/config/hermes/USER.md"
hermes config reload 2>/dev/null || hermes gateway restart
```

**Troubleshooting:**
- If mirror diverges from PostgreSQL → rebuild from PG: `python scripts/rebuild_mirror.py`
- If mirror contains classified data (Confidential+) → audit sync filter. Classified data MUST NOT appear in plaintext mirror.
- If mirror sync causes PG writes during shadow mode → this step should ONLY be done post-cutover

### Step 3.5: A/B Test Memory Recall on 100 Queries

**Command:**
```bash
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python scripts/ab_test_recall.py --queries 100 --threshold 0.05
```

**Expected output:**
```
A/B Memory Recall Test — 100 queries
Baseline (PostgreSQL-only): precision=0.XXXX
Post-migration (PG+compression+session_search): precision=0.XXXX
P-value: 0.XXXX (threshold: 0.05)
DNR audit: 0 entries leaked

VERDICT: PASS (p > 0.05, no significant degradation)
```

**Troubleshooting:**
- If embedding API (G-B1) is broken → A/B test is INVALID. Fix embeddings first. Without vector search, A/B test only measures FTS+Recency.
- If p-value < 0.05 → recall quality degraded. Disable compression and investigate.
- If DNR entries found in results → fix `verify_recall_results_dnr_free()` filter.

### Step 3.6: Verify Zero PostgreSQL Data Modifications from Hermes Path

**Command:**
```bash
# Row count snapshot — compare with pre-Phase 3 snapshot
sudo -u postgres psql -d guinevere -c "
  SELECT 'episodes' as tbl, count(*) FROM memory.episodes
  UNION ALL SELECT 'semantic_facts', count(*) FROM memory.semantic_facts
  UNION ALL SELECT 'mood_states', count(*) FROM persona.mood_states
  ORDER BY tbl;
"

# Audit table — MUST return 0
sudo -u postgres psql -d guinevere -c "
  SELECT count(*) AS hermes_unauthorized_writes
  FROM audit.hermes_writes
  WHERE timestamp > now() - interval '24 hours';
"
# Expected: hermes_unauthorized_writes = 0
```

---

## Safety Checkpoint

| # | Check | Command | Expected |
|---|---|---|---|
| P3-T1 | Memory recall quality | `python scripts/ab_test_recall.py --queries 100` | p > 0.05 (no degradation) |
| P3-T2 | Zero DNR in Hermes recall | `pytest tests/safety/test_dnr_hermes_recall.py -v` | 0 DNR entries in results |
| P3-T3 | Zero PG writes from Hermes | `SELECT count(*) FROM audit.hermes_writes` | count = 0 |
| P3-T4 | Mirror sync audit | `pytest tests/safety/test_mirror_sync_audit.py -v` | No classified data in plaintext mirror |

---

## Config Changes

```yaml
memory:
  compression:
    enabled: true
    threshold: 0.70
    target: 0.20
    protect_last: 20
  session_search:
    enabled: true
    backend: "fts5"
  mirrors:
    enabled: true
    memory_md_path: "/home/guinevere/code/guinevere/config/hermes/MEMORY.md"
    user_md_path: "/home/guinevere/code/guinevere/config/hermes/USER.md"
    sync_interval_messages: 5

plugins:
  memory_bridge:
    enabled: true
    path: "/home/guinevere/code/guinevere/plugins/memory_plugin.py"
    class: "MemoryBridgePlugin"
    priority: 80
    critical: false
    config:
      postgres_dsn: "postgresql://guinevere_app@localhost:5433/guinevere"
      dnr_enabled: true
      classification_fail_closed: true
```

### PostgreSQL RBAC — Hermes read-only:
```sql
CREATE ROLE hermes_memory_bridge WITH LOGIN PASSWORD '${SOPS_DECRYPTED}';
GRANT CONNECT ON DATABASE guinevere TO hermes_memory_bridge;
GRANT USAGE ON SCHEMA public, memory, persona, consent TO hermes_memory_bridge;
GRANT SELECT ON ALL TABLES IN SCHEMA memory TO hermes_memory_bridge;
GRANT SELECT ON ALL TABLES IN SCHEMA persona TO hermes_memory_bridge;
GRANT SELECT ON consent_ledger TO hermes_memory_bridge;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT SELECT ON TABLES TO hermes_memory_bridge;
```

---

## File Changes

| File | Action | Description |
|---|---|---|
| `plugins/memory_plugin.py` | CREATE (~180 lines) | PostgreSQL bridge plugin |
| `config/hermes/MEMORY.md` | CREATE | Mirror of critical PostgreSQL facts |
| `config/hermes/USER.md` | CREATE | Mirror of Faiz profile facts |
| `config/hermes/config.yaml` | MODIFY | Add memory section |
| `src/hermes/memory_bridge.py` | REFACTOR (251→~150) | Simplified to plugin passthrough |
| `scripts/ab_test_recall.py` | CREATE (~100 lines) | A/B recall test harness |

### Files Preserved Verbatim (ADR-007):
- `src/memory/models.py` (1,100 lines) — 47-table PostgreSQL ORM schema
- `src/memory/read_pipeline.py` (775 lines) — Vector+FTS+Recency hybrid ranking
- `src/memory/embeddings.py` (623 lines) — 1536-dim HNSW embedding pipeline
- `src/memory/consolidation.py` (610 lines) — Memory consolidation logic
- `src/memory/dnr.py` (338 lines) — DNR enforcement pipeline
- `src/memory/write_pipeline.py` (291 lines) — Episodic write pipeline
- `src/memory/__init__.py` (204 lines) — Package exports

---

## Service Management

**No service stops in Phase 3.** Hermes gateway stays running. All config changes are live reloads or brief gateway restart (< 10s).

| Service | Action |
|---|---|
| Hermes gateway | CONFIG RELOAD (or brief restart) |
| `guinevere-loops` | KEEP RUNNING |
| `guinevere-mcp` | KEEP RUNNING |
| PostgreSQL | KEEP RUNNING — zero changes to schema or data |
| Redis | KEEP RUNNING |

---

## Risk Register

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P3-OVER-01 | Embedding API (G-B1) still broken | 16 CRITICAL | FIX BEFORE Phase 3. A/B test invalid without embeddings. |
| R-P3-OVER-02 | Memory recall quality degrades | 12 HIGH | A/B test on 100 queries; p > 0.05 threshold |
| R-P3-01-001 | Compression drops critical memories | 12 HIGH | Start at 70% (conservative); protect last 20 messages |
| R-P3-02-001 | session_search returns DNR content | 8 MEDIUM | `verify_recall_results_dnr_free()` as post-search gate |
| R-P3-03-001 | memory_bridge.py → memory_plugin.py refactor introduces bug | 12 HIGH | Plugin wraps existing functions unchanged (passthrough) |
| R-P3-04-001 | Mirror sync divergence from PostgreSQL | 6 MEDIUM | Batch writes every 5 messages; atomic file replacement |
| R-P3-05-001 | A/B test invalid if embeddings broken | 12 HIGH | Verify vector search returns results before A/B test |

---

## Cross-Session Recall Test Procedure

```bash
# Test 1: Store fact in session A
# Discord session A: "Faiz deadline project is June 15"
# Verify: stored in PostgreSQL memory.episodes

# Test 2: Recall in session B
# New Discord session B: "When is my deadline?"
# Expected: "June 15" recalled from PostgreSQL via memory_plugin.py

# Test 3: DNR enforcement
# Mark a memory entry DNR: UPDATE memory.episodes SET do_not_recall = true WHERE id = '...'
# Session B query: ask about DNR entry topic
# Expected: DNR entry NOT in response. session_search + compression both exclude it.

# Test 4: Classification ceiling
# Store Critical-classified data
# Query as hermes_memory_bridge role (read-only)
# Expected: Critical data excluded from recall results
```

---

## DNR Enforcement Test

```python
# tests/memory/test_dnr_hermes_recall.py
def test_dnr_entries_not_in_recall():
    """Hermes recall paths MUST exclude DNR entries."""
    from memory.dnr import verify_recall_results_dnr_free
    
    # Simulate recall results with a DNR entry mixed in
    mock_results = [
        {"id": "ep-001", "content": "normal memory", "do_not_recall": False},
        {"id": "ep-002", "content": "DNR CONTENT", "do_not_recall": True},
        {"id": "ep-003", "content": "normal memory 2", "do_not_recall": False},
    ]
    
    filtered = verify_recall_results_dnr_free(mock_results)
    assert len(filtered) == 2, f"Expected 2 results, got {len(filtered)}"
    assert all(r["do_not_recall"] == False for r in filtered), "DNR entry leaked"

def test_dnr_in_session_search():
    """session_search MUST exclude DNR entries."""
    # Search FTS5 index for DNR term
    # Expected: DNR entry NOT in results
    pass

def test_dnr_in_compression():
    """Compression MUST not include DNR entries in summary."""
    # Trigger compression with DNR entry in context
    # Expected: DNR entry excluded from compressed summary
    pass
```

---

## Classification Ceiling Test

```python
# tests/memory/test_classification_ceiling.py
def test_unknown_classification_fail_closed():
    """Unknown classification → Confidential (fail-closed)."""
    from memory.classification import classify_event
    
    result = classify_event(type="unknown_event")
    assert result.classification == "Confidential", \
        f"Expected Confidential, got {result.classification}"
    assert all([
        result.level is not None,
        result.owner is not None,
        result.retention is not None,
        result.encryption is not None,
        result.access_control is not None,
    ]), "All 5 classification fields must be populated"

def test_classification_ceiling_enforced():
    """Cannot upclassify without audit trail."""
    # Internal → Secret: must raise ClassificationCeilingError
    pass

def test_hermes_role_cannot_read_above_ceiling():
    """hermes_memory_bridge role respects classification level."""
    # hermes_memory_bridge has SELECT on memory.*
    # But classification enforcement prevents reading above ceiling
    pass
```

---

## Rollback Procedure

```bash
# === PHASE 3 ROLLBACK (< 3 minutes) ===
hermes config set memory.compression.enabled false
hermes config set memory.session_search.enabled false
hermes config set memory.mirrors.enabled false
hermes gateway restart  # or reload if supported

# Restore original memory_bridge.py if plugin refactor caused issues
cd /home/guinevere/code/guinevere
git checkout -- src/hermes/memory_bridge.py

# Verify PostgreSQL data intact
sudo -u postgres psql -d guinevere -c "SELECT count(*) FROM memory.episodes"
```

---

## Test Commands

```bash
# PostgreSQL bridge plugin unit tests
pytest tests/hermes/test_memory_plugin.py -v

# Compression configuration tests
pytest tests/hermes/test_compression.py::TestCompressionConfig -v

# session_search FTS5 tests
pytest tests/hermes/test_session_search.py -v

# Mirror sync tests
pytest tests/hermes/test_mirror_sync.py -v

# DNR pre-injection gate
pytest tests/hermes/test_memory_plugin.py::TestDNRGate -v

# A/B memory recall quality test (100 queries)
pytest tests/hermes/test_memory_ab.py -v

# Memory write authority test
pytest tests/hermes/test_memory_write_authority.py -v

# Classification enforcement in recall
pytest tests/hermes/test_memory_classification.py -v

# Full memory pipeline E2E
pytest tests/hermes/test_memory_pipeline_e2e.py -v
```

---

## Gate Criteria

| Criterion | Threshold | Measurement |
|---|---|---|
| Memory recall quality unchanged | A/B test p > 0.05 | 100-query recall precision comparison |
| Zero DNR content in recall results | 0 DNR entries | `verify_recall_results_dnr_free()` audit |
| Zero PostgreSQL writes from Hermes | `count(*) = 0` | `SELECT count(*) FROM audit.hermes_writes` |
| Compression threshold at 70% | config check | `hermes config get memory.compression.threshold` |
| Classification fail-closed | Unknown → Confidential | `classify_event(type="unknown")` |

---

## References

| Document | Relevance |
|---|---|
| `adr/ADR-035-hermes-migration.md` | §Phase 3 — Memory Bridge, §Pillar 2: Memory = HYBRID |
| `adr/ADR-007-memory-storage-backend-selection.md` | PostgreSQL primary write authority |
| `research-reports/migration-plan/01-dependency-map.md` | §Phase 3 dependencies |
| `research-reports/migration-plan/02-risk-per-step.md` | §6 — Phase 3 risks (R-P3-*) |
| `research-reports/migration-plan/03-rollback-procedures.md` | §8 — Phase 3 rollback |
| `research-reports/migration-plan/04-safety-checkpoints.md` | §5 — Phase 3 safety checkpoint |
| `research-reports/migration-plan/06-file-inventory.md` | §Phase 3 — File changes |
| `research-reports/migration-plan/07-test-suite.md` | §7 — Phase 3 test suite |
| `research-reports/migration-plan/08-service-sequence.md` | §Phase 3 — Service management |
| `research-reports/migration-plan/09-config-migration.md` | §6 — Phase 3 config changes |