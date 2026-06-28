"""P22 permission classifier tests — semantic classification, NOT AuthLevel-only."""

from __future__ import annotations

import pytest

from src.life_integrations.permissions import SemanticActionClassifier
from src.life_integrations.types import PermissionTier


@pytest.fixture
def classifier():
    return SemanticActionClassifier()


def test_read_action_classified_l1(classifier):
    """Read actions classify as L1."""
    result = classifier.classify("github", "list_repos")
    assert result.tier == PermissionTier.L1_READ
    assert result.method == "static_map"


def test_write_action_classified_l2(classifier):
    """Write actions classify as L2."""
    result = classifier.classify("github", "create_issue")
    assert result.tier == PermissionTier.L2_WRITE


def test_delete_action_classified_l3(classifier):
    """Delete actions classify as L3."""
    result = classifier.classify("gmail", "delete_label")
    assert result.tier == PermissionTier.L3_DESTRUCTIVE


def test_forbidden_action_classified_l4(classifier):
    """Forbidden actions classify as L4."""
    result = classifier.classify("github", "delete_repo")
    assert result.tier == PermissionTier.L4_FORBIDDEN


def test_semantic_fallback_destructive_keyword(classifier):
    """Unknown action with destructive keyword classifies as L3."""
    result = classifier.classify("unknown_provider", "purge_something")
    assert result.tier == PermissionTier.L3_DESTRUCTIVE
    assert result.method == "semantic"


def test_semantic_fallback_forbidden_keyword(classifier):
    """Unknown action with forbidden keyword classifies as L4."""
    result = classifier.classify("unknown_provider", "system_prune_stuff")
    assert result.tier == PermissionTier.L4_FORBIDDEN


def test_semantic_fallback_write_keyword(classifier):
    """Unknown action with write keyword classifies as L2."""
    result = classifier.classify("unknown_provider", "create_widget")
    assert result.tier == PermissionTier.L2_WRITE


def test_semantic_default_l2_for_unknown(classifier):
    """Unknown action with no keywords defaults to L2_WRITE (F04 brutal-audit fix).

    Rationale: an unmapped action must NOT silently bypass consent by landing
    in L1_READ. L2_WRITE forces the consent gate so any new action surfaces to
    the operator. L4 would be too restrictive (blocks legitimate unknown reads).
    """
    result = classifier.classify("unknown_provider", "inspect_widget")
    assert result.tier == PermissionTier.L2_WRITE
    assert result.method == "semantic_default"


def test_authlevel_not_the_gate(classifier):
    """AuthLevel is informational only, not the classification gate.

    This tests the P22 plan §AuthLevel gating boundary: L2/L3/L4 MUST
    be classified semantically, NOT by AuthLevel alias.
    """
    # Even if auth_level says READ_AUTO, delete action is L3
    result = classifier.classify("gmail", "delete_label", auth_level="read_auto")
    assert result.tier == PermissionTier.L3_DESTRUCTIVE
    assert "auth_level" not in result.reason  # reason is semantic, not authlevel


def test_is_allowed_l1_no_consent(classifier):
    """L1 actions allowed without consent."""
    from src.life_integrations.types import PermissionTier
    classification = type("C", (), {"tier": PermissionTier.L1_READ})()
    allowed, _ = classifier.is_allowed(classification, hard_stop_active=False, consent_granted=False)
    assert allowed is True


def test_is_allowed_l2_requires_consent(classifier):
    """L2 actions require consent."""
    classification = type("C", (), {"tier": PermissionTier.L2_WRITE})()
    allowed, _ = classifier.is_allowed(classification, hard_stop_active=False, consent_granted=False)
    assert allowed is False
    allowed, _ = classifier.is_allowed(classification, hard_stop_active=False, consent_granted=True)
    assert allowed is True


def test_is_allowed_l4_always_forbidden(classifier):
    """L4 actions always forbidden."""
    classification = type("C", (), {"tier": PermissionTier.L4_FORBIDDEN})()
    allowed, _ = classifier.is_allowed(classification, hard_stop_active=False, consent_granted=True)
    assert allowed is False


def test_is_allowed_hard_stop_blocks_l2(classifier):
    """HARD STOP blocks all L2+ actions."""
    classification = type("C", (), {"tier": PermissionTier.L2_WRITE})()
    allowed, _ = classifier.is_allowed(classification, hard_stop_active=True, consent_granted=True)
    assert allowed is False


# --- P22.2 regression: classifier must use integration_id, not provider string ---
# P22.2 runtime proof caught that the router passed adapter.config.provider
# (e.g. "PostgreSQL/pgvector") to classify(), but the static map is keyed by
# integration_id-domain (e.g. "memory"). The mismatch left memory/store
# defaulting to L1_READ -> consent bypass -> an episode written without consent.
# These tests pin the fix: classify by integration_id; store is L2 either way
# (static map AND _WRITE_KEYWORDS defense-in-depth).

def test_memory_store_classified_l2_by_integration_id(classifier):
    """memory/store must be L2_WRITE when classified by integration_id."""
    result = classifier.classify("memory", "store")
    assert result.tier == PermissionTier.L2_WRITE


def test_memory_store_classified_l2_by_keyword_defense_in_depth(classifier):
    """Even if the static map key misses (e.g. provider string), store must
    still be L2 via the _WRITE_KEYWORDS fallback -- defense-in-depth so a
    provider/integration_id mismatch can never bypass consent."""
    result = classifier.classify("PostgreSQL/pgvector", "store")
    assert result.tier == PermissionTier.L2_WRITE
    assert result.method == "semantic"


def test_finance_record_transaction_l2_by_keyword(classifier):
    """finance/record_transaction classifies L2 via 'record' keyword even if
    the static map key misses (provider 'Polars/PG')."""
    result = classifier.classify("Polars/PG", "record_transaction")
    assert result.tier == PermissionTier.L2_WRITE


def test_whatsapp_send_text_l2_by_keyword(classifier):
    """whatsapp/send_text classifies L2 via 'send' keyword even if the static
    map key misses (provider 'Neonize/Baileys')."""
    result = classifier.classify("Neonize/Baileys", "send_text")
    assert result.tier == PermissionTier.L2_WRITE


def test_memory_recall_still_l1(classifier):
    """memory/recall must remain L1_READ (read-only, no consent needed)."""
    result = classifier.classify("memory", "recall")
    assert result.tier == PermissionTier.L1_READ


# --- A3 regression: calendar/drive static-map keys must match integration_id ---
# P22.2 fixed the router to pass integration_id (e.g. "calendar", "drive")
# instead of provider string. _PROVIDER_TIER_MAP was keyed by
# "google_calendar"/"google_drive", so calendar/drive actions were falling
# through to keyword heuristics (correct by luck, brittle by design).
# These tests pin the A3 fix: integration_id is the static_map key.

def test_calendar_create_event_classified_l2_by_static_map(classifier):
    """calendar/create_event must be L2_WRITE via static_map (integration_id key)."""
    result = classifier.classify(provider="calendar", action="create_event")
    assert result.tier == PermissionTier.L2_WRITE
    assert result.method == "static_map"


def test_drive_delete_file_classified_l3_by_static_map(classifier):
    """drive/delete_file must be L3_DESTRUCTIVE via static_map (integration_id key)."""
    result = classifier.classify(provider="drive", action="delete_file")
    assert result.tier == PermissionTier.L3_DESTRUCTIVE
    assert result.method == "static_map"


def test_calendar_l1_list_events(classifier):
    """calendar/list_events classified L1_READ via static_map."""
    result = classifier.classify(provider="calendar", action="list_events")
    assert result.tier == PermissionTier.L1_READ
    assert result.method == "static_map"


def test_drive_l4_empty_trash(classifier):
    """drive/empty_trash classified L4_FORBIDDEN via static_map."""
    result = classifier.classify(provider="drive", action="empty_trash")
    assert result.tier == PermissionTier.L4_FORBIDDEN
    assert result.method == "static_map"


def test_calendar_delete_event_l3(classifier):
    """calendar/delete_event classified L3_DESTRUCTIVE via static_map."""
    result = classifier.classify(provider="calendar", action="delete_event")
    assert result.tier == PermissionTier.L3_DESTRUCTIVE
    assert result.method == "static_map"

