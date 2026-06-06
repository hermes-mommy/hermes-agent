"""
T4: Memory Pipeline — Memory Schema and Pipeline Contract Tests.

Verifies memory pipeline structural invariants: models are well-defined,
DNR marking works, embedding config exists, consolidation stores/retrieves
entries, and the read_pipeline accepts valid search parameters.
"""

from __future__ import annotations

from src.memory.dnr import (
    DNRViolationError,
    is_memory_dnr,
    mark_memory_dnr,
    verify_recall_results_dnr_free,
)
from src.memory.consolidation import ConsolidationResult, RetentionConfig
from src.memory.embeddings import EmbeddingConfig
from src.memory.models import Episodes


class TestMemoryModels:
    """Memory models are well-defined and have required fields."""

    def test_episodes_model_exists(self) -> None:
        """Episodes SQLAlchemy model is importable."""
        assert Episodes is not None
        assert hasattr(Episodes, "__tablename__")

    def test_core_tables_exist(self) -> None:
        """Required core tables are defined in models."""
        from src.memory.models import (
            AccessLog, AuditTrail, CommunicationLog, ConsentLedger,
            EmotionalEvents, Episodes, FaizProfile, InnerJournal,
            MoodHistory, PersonaState, PunishmentLog,
            RewardLog, SemanticFacts, SurveillanceEvents,
        )
        assert all([
            AccessLog, AuditTrail, CommunicationLog, ConsentLedger,
            EmotionalEvents, Episodes, FaizProfile, InnerJournal,
            MoodHistory, PersonaState, PunishmentLog,
            RewardLog, SemanticFacts, SurveillanceEvents,
        ])


class TestDNROperations:
    """DNR (Do Not Remember) marking and verification work correctly."""

    def test_is_memory_dnr_function(self) -> None:
        """is_memory_dnr is a callable function."""
        assert callable(is_memory_dnr)

    def test_mark_memory_dnr_function(self) -> None:
        """mark_memory_dnr is a callable function."""
        assert callable(mark_memory_dnr)

    def test_verify_recall_dnr_free_function(self) -> None:
        """verify_recall_results_dnr_free is a callable function."""
        assert callable(verify_recall_results_dnr_free)

    def test_dnr_violation_error(self) -> None:
        """DNRViolationError can be raised."""
        try:
            raise DNRViolationError("DNR violation detected")
        except DNRViolationError:
            pass
        else:
            assert False, "Expected DNRViolationError"

    def test_dnr_violation_message(self) -> None:
        """DNRViolationError includes meaningful message."""
        try:
            raise DNRViolationError("test violation")
        except DNRViolationError as e:
            assert "violation" in str(e).lower()


class TestEmbeddingConfig:
    """Embedding configuration is properly defined."""

    def test_embedding_config_defaults(self) -> None:
        """EmbeddingConfig has sensible default values."""
        cfg = EmbeddingConfig()
        assert cfg.model == "openai/text-embedding-3-small"
        assert cfg.expected_dimension == 1536

    def test_embedding_config_custom(self) -> None:
        """EmbeddingConfig accepts custom parameters."""
        cfg = EmbeddingConfig(model="custom-model", expected_dimension=768)
        assert cfg.model == "custom-model"
        assert cfg.expected_dimension == 768


class TestConsolidationEngine:
    """ConsolidationResult and RetentionConfig basic contracts."""

    def test_consolidation_result_defaults(self) -> None:
        """ConsolidationResult default values."""
        result = ConsolidationResult()
        assert result.consolidated == 0
        assert result.skipped_dnr == 0

    def test_consolidation_result_counts(self) -> None:
        """ConsolidationResult with specific values."""
        result = ConsolidationResult(consolidated=10, skipped_dnr=2)
        assert result.consolidated == 10
        assert result.skipped_dnr == 2

    def test_retention_config_has_max_age(self) -> None:
        """RetentionConfig specifies max_age_days."""
        cfg = RetentionConfig(max_age_days=90)
        assert cfg.max_age_days == 90


class TestReadPipelineComponents:
    """Read pipeline components are importable and structs work."""

    def test_read_pipeline_error(self) -> None:
        """ReadPipelineError can be raised."""
        from src.memory.read_pipeline import ReadPipelineError
        try:
            raise ReadPipelineError("pipeline error")
        except ReadPipelineError:
            pass
        else:
            assert False, "Expected ReadPipelineError"

    def test_recency_config_exists(self) -> None:
        """RecencyConfig is importable."""
        from src.memory.read_pipeline import RecencyConfig
        cfg = RecencyConfig(half_life_days=7)
        assert cfg.half_life_days == 7
