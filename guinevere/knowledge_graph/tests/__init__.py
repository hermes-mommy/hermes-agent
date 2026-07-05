"""Internal test utilities for the KG module.

Not part of the public surface — holds pytest fixtures, mock session
factories, and canned dataset helpers used by :mod:`src.knowledge_graph.eval`
and per-step unit tests.

Per-step unit-test layout (P16-012 — adversarial safety suite):

* :mod:`test_adversarial_safety` — HARD STOP / DNR / revocation /
  surveillance / token-budget / persona-drift boundaries.
* :mod:`test_consent_boundary`  — consent token generation, RLS
  policies, audit trail invariants.
* :mod:`test_entity_resolution` — canonical-key derivation, fuzzy
  matching, same-as / merge semantics.
* :mod:`test_query_engine`     — RCTE traversal, PPR, RRF fusion.
* :mod:`test_ingestion`        — single-fact and batched ingestion
  (mocked ``KGIngestor`` until the real implementation lands).
* :mod:`smoke_extraction`      — pre-existing smoke harness for the
  rule-based entity / relation extractor.

All tests use ``AsyncMock`` / ``MagicMock`` so they run without a live
PostgreSQL instance.  Integration tests against the real database live
under ``evidence/p16-kg/verification/`` (P16-009 verification wave).
"""
from __future__ import annotations

__all__: list[str] = []
