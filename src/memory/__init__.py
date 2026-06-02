"""Guinevere memory module — P3 memory pipeline."""

from src.memory.embeddings import (
    # Classification constants
    CONFIDENTIAL,
    CRITICAL,
    INTERNAL,
    PUBLIC,
    RESTRICTED,
    # Errors
    CriticalEmbeddingError,
    DimensionMismatchError,
    EmbeddingAPIError,
    EmbeddingConfigurationError,
    EmbeddingError,
    EmbeddingRateLimitError,
    EmbeddingServerError,
    RestrictedRedactionError,
    # Config
    EmbeddingConfig,
    # Service
    EmbeddingService,
    # Preprocessing
    PreparedText,
    prepare_embedding_text,
    # Convenience functions (sync)
    embed,
    embed_batch,
    # Convenience functions (async)
    aembed,
    aembed_batch,
)

from src.memory.write_pipeline import (
    # Pipeline errors
    WritePipelineError,
    WritePipelineCriticalError,
    # Store functions
    store_episode,
    store_episode_batch,
)

from src.memory.consolidation import (
    # Core consolidation
    CONSOLIDATION_JOB_ID,
    CONSOLIDATION_HOUR,
    CONSOLIDATION_MINUTE,
    ConsolidationResult,
    consolidate_episodes_to_facts,
    # Pruning
    PruneResult,
    RetentionConfig,
    prune_stale_facts,
    # APScheduler job
    daily_consolidation_job,
    register_consolidation_job,
    # Helpers (public for testability)
    AsyncSessionProtocol,
    is_safe_word_record,
    highest_classification,
    make_content_key,
)

from src.memory.dnr import (
    # DNR errors
    DNRAuthorizationError,
    DNRStateError,
    DNRViolationError,
    # DNR mutation APIs
    mark_memory_dnr,
    unmark_memory_dnr,
    is_memory_dnr,
    # Pre-injection guard
    verify_recall_results_dnr_free,
    # Event type constants
    MEMORY_DNR_MARKED,
    DNR_REVOKED,
)

from src.memory.read_pipeline import (
    # Constants
    RRF_K,
    RECENCY_HALF_LIFE_DAYS,
    EXPANDED_LIMIT_MULTIPLIER,
    SAFE_MODE_PLACEHOLDER,
    SAFE_MODE_RESTRICTED_PLACEHOLDER,
    SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER,
    DEFAULT_TOKEN_BUDGET,
    CHARS_PER_TOKEN,
    VECTOR_WEIGHT,
    FTS_WEIGHT,
    BOTH_SIGNAL_BONUS,
    RECENCY_MAX_BOOST,
    MAX_CANDIDATE_POOL,
    # Pipeline errors
    ReadPipelineError,
    ReadPipelineQueryError,
    ReadPipelineSafetyError,
    ReadPipelineTokenBudgetError,
    # Config
    RecencyConfig,
    # Ranking utilities (public for testability)
    compute_rrf_score,
    normalize_importance,
    classification_level,
    build_vector_query,
    build_fts_query,
    build_recency_query,
    EpisodeEntry,
    build_result_episode_map,
    compute_scored_results,
    build_safe_content,
    estimate_tokens,
    apply_token_budget,
    # Recall function
    recall_memories,
)

__all__ = [
    # Classification constants
    "CONFIDENTIAL",
    "CRITICAL",
    "INTERNAL",
    "PUBLIC",
    "RESTRICTED",
    # Errors
    "CriticalEmbeddingError",
    "DimensionMismatchError",
    "EmbeddingAPIError",
    "EmbeddingConfigurationError",
    "EmbeddingError",
    "EmbeddingRateLimitError",
    "EmbeddingServerError",
    "RestrictedRedactionError",
    # Config
    "EmbeddingConfig",
    # Service
    "EmbeddingService",
    # Preprocessing
    "PreparedText",
    "prepare_embedding_text",
    # Convenience functions
    "embed",
    "embed_batch",
    "aembed",
    "aembed_batch",
    # Write pipeline
    "WritePipelineError",
    "WritePipelineCriticalError",
    "store_episode",
    "store_episode_batch",
    # Read pipeline
    "RRF_K",
    "RECENCY_HALF_LIFE_DAYS",
    "EXPANDED_LIMIT_MULTIPLIER",
    "SAFE_MODE_PLACEHOLDER",
    "SAFE_MODE_RESTRICTED_PLACEHOLDER",
    "SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER",
    "DEFAULT_TOKEN_BUDGET",
    "CHARS_PER_TOKEN",
    "VECTOR_WEIGHT",
    "FTS_WEIGHT",
    "BOTH_SIGNAL_BONUS",
    "RECENCY_MAX_BOOST",
    "MAX_CANDIDATE_POOL",
    "ReadPipelineError",
    "ReadPipelineQueryError",
    "ReadPipelineSafetyError",
    "ReadPipelineTokenBudgetError",
    "RecencyConfig",
    # Ranking utilities (public for testability)
    "compute_rrf_score",
    "normalize_importance",
    "classification_level",
    "build_vector_query",
    "build_fts_query",
    "build_recency_query",
    "EpisodeEntry",
    "build_result_episode_map",
    "compute_scored_results",
    "build_safe_content",
    "estimate_tokens",
    "apply_token_budget",
    "recall_memories",
    # DNR API (P3-013)
    "DNRAuthorizationError",
    "DNRStateError",
    "DNRViolationError",
    "mark_memory_dnr",
    "unmark_memory_dnr",
    "is_memory_dnr",
    "verify_recall_results_dnr_free",
    "MEMORY_DNR_MARKED",
    "DNR_REVOKED",
    # Consolidation (P3-015)
    "CONSOLIDATION_JOB_ID",
    "CONSOLIDATION_HOUR",
    "CONSOLIDATION_MINUTE",
    "ConsolidationResult",
    "consolidate_episodes_to_facts",
    "PruneResult",
    "RetentionConfig",
    "prune_stale_facts",
    "daily_consolidation_job",
    "register_consolidation_job",
    "AsyncSessionProtocol",
    "is_safe_word_record",
    "highest_classification",
    "make_content_key",
]
