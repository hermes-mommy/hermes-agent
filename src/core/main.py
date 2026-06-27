"""Guinevere Core - Main FastAPI Application."""
import os
import uuid
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from src.observability import init_sentry

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# P20: Alias the 9Router API key for the HermesBrain AIAgent.
# The AIAgent derives its API-key env var from the provider name — provider
# "9router" -> it reads 9ROUTER_API_KEY from os.environ. The secret ships as
# GUINEVERE_9ROUTER_API_KEY (in .env.core); we alias it at MODULE IMPORT TIME
# (not in the lifespan) so it is present before uvicorn forks workers and
# before run_agent is imported. This is set as early as possible.
# ---------------------------------------------------------------------------
if not os.environ.get("9ROUTER_API_KEY") and os.environ.get("GUINEVERE_9ROUTER_API_KEY"):
    os.environ["9ROUTER_API_KEY"] = os.environ["GUINEVERE_9ROUTER_API_KEY"]

# ---------------------------------------------------------------------------
# P3-015 consolidation scheduler registration (optional — no DB by default)
# ---------------------------------------------------------------------------
# To activate the daily consolidation scheduler at runtime, inject an async
# SQLAlchemy session factory (async_sessionmaker) into the lifespan:
#
#   from apscheduler.schedulers.asyncio import AsyncIOScheduler
#   from src.memory.consolidation import register_consolidation_job
#
#   scheduler = AsyncIOScheduler()
#   await register_consolidation_job(scheduler, session_factory=AsyncSessionLocal)
#   scheduler.start()
#
# DO NOT start a live APScheduler without a valid async DB sessionmaker, as
# the consolidation job requires database access.  In tests, use the synthetic
# consolidation unit tests (tests/memory/test_consolidation.py) which do not
# require a running scheduler or real database.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# P16-002: KG ingestion cron registration (optional — requires P16 schema)
# ---------------------------------------------------------------------------
# To activate the daily KG ingestion scheduler at runtime, inject an async
# SQLAlchemy session factory (async_sessionmaker) into the lifespan:
#
#   from src.knowledge_graph.ingestion import register_kg_ingestion_job
#
#   scheduler = AsyncIOScheduler()  # reuse same scheduler instance
#   await register_kg_ingestion_job(scheduler, session_factory=AsyncSessionLocal)
#   # scheduler.start() — already started above
#
# The KG ingestion cron runs at 03:30 ICT daily, 30 minutes after the
# consolidation cron (03:00 ICT). It reads semantic_facts created by
# consolidation and extracts entities + relations into the KG.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from src.loops.manager import LoopManager
    from src.core.services.hard_stop_handler import HardStopHandler

    # P8-012: Initialize Sentry error tracking
    init_sentry(
        environment="production",
        release="0.1.0",
    )

    # Phase 6: Start LLM routing metrics server on localhost:9191
    from src.core.services.llm_metrics import start_llm_metrics_server

    start_llm_metrics_server(port=9191)
    logger.info("llm_metrics_server_started", port=9191)

    # P20 Living Autonomy Kernel: HermesBrain as the real autonomous brain
    hermes_brain = None
    try:
        from src.life_kernel import HermesBrain, HermesBrainConfig

        # 9ROUTER_API_KEY is aliased at module import time (top of this file)
        # so the AIAgent provider resolver can find it before any fork.
        brain_config = HermesBrainConfig(
            base_url="http://localhost:20128/v1",
            model="guinevere",
            provider="9router",
            api_key=os.getenv("9ROUTER_API_KEY", os.getenv("GUINEVERE_9ROUTER_API_KEY", "")),
            max_iterations=5,
        )
        hermes_brain = HermesBrain(llm_config=brain_config)
        app.state.hermes_brain = hermes_brain
        logger.info("hermes_brain_initialized")
    except Exception as brain_err:
        logger.warning("hermes_brain_init_failed", error=str(brain_err))

    # P20/P24: llm_router=None is intentional. All autonomous LLM calls
    # route through HermesBrain.think() (``hermes_brain_think_complete``),
    # not through LLMRouter.chat(). The loop infrastructure's .chat() callers
    # are dormant until a router is injected and a call gate is designed.
    # See: p1-live-vps-reconciliation-audit.md §3.1 (GAP-01, GAP-06, GAP-07).
    loop_manager = LoopManager(llm_router=None)
    app.state.loop_manager = loop_manager

    # F-05: Init HardStopHandler and wire to loop guardian
    hard_stop_handler = HardStopHandler()
    app.state.hard_stop_handler = hard_stop_handler
    if hasattr(loop_manager.guardian, "set_hard_stop_handler"):
        loop_manager.guardian.set_hard_stop_handler(hard_stop_handler)
        logger.info("hard_stop_handler_initialized_and_wired")
    else:
        logger.warning("hard_stop_handler_init_skipped", reason="LoopGuardian missing set_hard_stop_handler")

    guardian_task = asyncio.create_task(
        loop_manager.guardian.monitor(),
        name="guardian-monitor",
    )
    app.state.guardian_task = guardian_task

    # P8-019: Register monthly cost report scheduler
    from src.core.services.monthly_report import register_monthly_report_scheduler

    report_scheduler = register_monthly_report_scheduler()
    report_scheduler.start()
    app.state.report_scheduler = report_scheduler

    # RG-004: Start surveillance consumer background worker
    surveillance_task = None
    try:
        import redis.asyncio as aioredis_surv
        from sqlalchemy.ext.asyncio import (
            AsyncSession as _AsyncSession,
            async_sessionmaker as _async_sessionmaker,
            create_async_engine as _create_async_engine,
        )
        from src.surveillance.consumer import SurveillanceConsumer
        from src.surveillance.redis_buffer import RedisSurveillanceBuffer

        _redis_password = os.environ.get("REDIS_PASSWORD", "")
        _redis_client = aioredis_surv.Redis(
            host="localhost",
            port=6380,
            db=2,
            username="guinevere_core",
            password=_redis_password,
            decode_responses=True,
        )
        _buffer = RedisSurveillanceBuffer(_redis_client)

        _db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere_core",
        )
        _engine = _create_async_engine(_db_url, pool_size=2, pool_pre_ping=True)
        _session_factory = _async_sessionmaker(
            _engine, class_=_AsyncSession, expire_on_commit=False,
        )

        _consumer = SurveillanceConsumer(
            buffer=_buffer, db_session_factory=_session_factory,
        )
        surveillance_task = asyncio.create_task(
            _consumer.run(), name="surveillance-consumer",
        )
        app.state.surveillance_consumer = _consumer
        app.state.surveillance_task = surveillance_task
        app.state.surveillance_engine = _engine
        logger.info("surveillance_consumer_started")
    except Exception as surv_err:
        logger.warning("surveillance_consumer_start_failed", error=str(surv_err))

    # P16-002: Start KG ingestion cron (03:30 ICT daily)
    kg_scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from src.knowledge_graph.ingestion import register_kg_ingestion_job
        from src.knowledge_graph.ingestion.pipeline import KGIngestionPipeline
        from src.knowledge_graph.resolution.resolver import EntityResolver
        from src.knowledge_graph.extraction.entity_extractor import EntityExtractor
        from src.knowledge_graph.extraction.relation_extractor import RelationExtractor
        from src.knowledge_graph.consent.manager import ConsentManager
        from src.knowledge_graph.observability.metrics import KGMetrics

        _kg_resolver = EntityResolver(_session_factory)
        _kg_extractor = EntityExtractor(_kg_resolver)
        _kg_rel_extractor = RelationExtractor(_kg_extractor)
        _kg_consent = ConsentManager(_session_factory)
        _kg_metrics = KGMetrics.get_instance()
        kg_pipeline = KGIngestionPipeline(
            session_factory=_session_factory,
            entity_extractor=_kg_extractor,
            entity_resolver=_kg_resolver,
            relation_extractor=_kg_rel_extractor,
            consent_manager=_kg_consent,
            metrics=_kg_metrics,
        )

        kg_scheduler = AsyncIOScheduler()
        register_kg_ingestion_job(
            kg_scheduler, session_factory=_session_factory, pipeline=kg_pipeline,
        )
        kg_scheduler.start()
        app.state.kg_scheduler = kg_scheduler
        logger.info("kg_ingestion_cron_started")
    except Exception as kg_err:
        logger.warning("kg_ingestion_cron_start_failed", error=str(kg_err))

    # P20 Living Autonomy Kernel: compile life_mind graph + start autonomous heartbeat
    try:
        from src.life_kernel import (
            create_life_mind_graph,
            HeartbeatService,
            create_postgres_checkpointer,
            DiscordRestClient,
            DashboardRenderer,
            DashboardWriter,
            DiscordLogChannel,
            StructlogLogChannel,
        )

        try:
            _db_url = os.environ.get("DATABASE_URL", "postgresql://guinevere_core@localhost:5433/guinevere")
            # AsyncPostgresSaver expects plain postgresql:// DSN, not postgresql+asyncpg://
            _checkpointer_dsn = _db_url.replace("postgresql+asyncpg://", "postgresql://")
            checkpointer = await create_postgres_checkpointer(_checkpointer_dsn)
        except Exception as cp_err:
            logger.warning("postgres_checkpointer_unavailable", error=str(cp_err))
            checkpointer = None

        # HermesBrain (created above, if available) drives LLM autonomy in
        # the graph. When None, the graph falls back to static logic.
        #
        # P20 Continuation (LK-010): build REAL P16/P18 recall adapters and a
        # JournalWriter, and inject them into the graph so observe_node
        # populates recalled_concepts/recalled_memories/world_model_status
        # and reflect_node writes journal entries (AC-LIFE-005 / AC-LIFE-008).
        # All fail-soft: if the DB/session/embedding is unavailable, the
        # adapters degrade to empty results and the kernel runs headless.
        kg_adapter = None
        memory_adapter = None
        journal_writer = None
        try:
            from sqlalchemy.ext.asyncio import (
                AsyncSession as _LKAsyncSession,
                async_sessionmaker as _lk_async_sessionmaker,
                create_async_engine as _lk_create_async_engine,
            )

            _lk_db_url = os.environ.get(
                "DATABASE_URL",
                "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere_core",
            )
            _lk_engine = _lk_create_async_engine(_lk_db_url, pool_size=2, pool_pre_ping=True)
            _lk_session_factory = _lk_async_sessionmaker(
                _lk_engine, class_=_LKAsyncSession, expire_on_commit=False,
            )
            app.state.life_kernel_engine = _lk_engine

            # P18 memory recall adapter: wrap recall_memories with a per-call
            # session so the kernel never holds a long-lived session open.
            try:
                from src.memory.read_pipeline import recall_memories as _recall_memories

                # SAF-02 (revised after deploy runtime check): the brain path
                # uses principal=guinevere_core which has CRITICAL clearance
                # (src/memory/read_pipeline._PRINCIPAL_CEILINGS). safe_mode=True
                # downgrades the ceiling to Internal and filters out ALL
                # Restricted+ memories — which starves the brain of context
                # (deploy showed "All 3 candidates filtered by classification
                # ceiling 'Internal'"). The brain NEEDS raw recall (it has
                # clearance); Discord safety is handled separately: the
                # dashboard memory_status field shows counts only (MEM-06),
                # never raw content, and DashboardRenderer._sanitize redacts
                # any secret patterns. Default safe_mode=False (raw recall for
                # the brain); an operator can opt into redacted recall via
                # LIFE_KERNEL_SAFE_RECALL=1 if a stricter posture is wanted.
                _life_safe_recall = os.environ.get("LIFE_KERNEL_SAFE_RECALL", "0") == "1"

                # P19/P3 fix: wire EmbeddingService for vector recall.
                # Falls back to keyword-only search if 9Router is unreachable
                # (recall_memories handles embedding_service=None gracefully).
                _embedding_service = None
                try:
                    from src.memory.embeddings import EmbeddingService
                    _embedding_service = EmbeddingService()
                    logger.info("life_kernel_embedding_service_wired")
                except Exception as _emb_err:
                    logger.warning(
                        "life_kernel_embedding_service_failed",
                        error=str(_emb_err),
                    )

                async def _life_recall_fn(
                    *,
                    query_text: str,
                    principal: str = "guinevere_core",
                    exclude_dnr: bool = True,
                    project_id: uuid.UUID | None = None,
                ):
                    # P19: accept + forward project_id to recall_memories.
                    # The pipeline applies project-scoped filtering
                    # (WHERE project_id = :pid OR project_scope = 'global').
                    async with _lk_session_factory() as _lk_session:
                        return await _recall_memories(
                            _lk_session,
                            query_text,
                            limit=20,
                            exclude_dnr=exclude_dnr,
                            principal=principal,
                            safe_mode=_life_safe_recall,
                            project_id=project_id,
                            embedding_service=_embedding_service,
                        )

                from src.life_kernel.p18_adapter import MemoryRecallAdapter

                memory_adapter = MemoryRecallAdapter(memory_client=_life_recall_fn)
                logger.info("life_kernel_memory_adapter_wired")
            except Exception as mem_err:
                logger.warning("life_kernel_memory_adapter_failed", error=str(mem_err))

            # P16 KG recall adapter: wrap KGQueryEngine.search_entities (the
            # engine borrows sessions from its own session_factory), returning
            # concept-shaped dicts for the decision context.
            try:
                from src.knowledge_graph.query.engine import KGQueryEngine as _KGQueryEngine

                _kg_engine_instance = _KGQueryEngine(session_factory=_lk_session_factory)

                async def _life_kg_fn(*, query_text: str, project_id: uuid.UUID | None = None):
                    # P19: accept + forward project_id to search_entities (which
                    # supports project-scoped KG recall via project_id filter).
                    rows = await _kg_engine_instance.search_entities(
                        query_text, project_id=project_id
                    )
                    return [
                        {
                            "name": getattr(r, "display_name", None) or str(getattr(r, "entity_id", "")),
                            "relevance": float(getattr(r, "relevance", 0.0)),
                            "source": "p16",
                        }
                        for r in (rows or [])
                    ]

                from src.life_kernel.p16_adapter import KGRecallAdapter

                kg_adapter = KGRecallAdapter(kg_client=_life_kg_fn)
                logger.info("life_kernel_kg_adapter_wired")
            except Exception as kg_err:
                logger.warning("life_kernel_kg_adapter_failed", error=str(kg_err))

            # Journal writer (AC-LIFE-008): wrap PostgresAuditJournal.
            try:
                from src.life_kernel.domain_minds.durability import PostgresAuditJournal
                from src.life_kernel.journal import JournalWriter

                _audit_journal = PostgresAuditJournal(
                    dsn=_lk_db_url, schema="life_kernel", table="audit_journal",
                )
                # Ensure the audit_journal table + schema exist before any
                # journal write (otherwise reflect_node's journal write fails
                # with UndefinedTableError every cycle). Fail-soft: if DDL
                # fails the journal writer stays wired but writes degrade.
                try:
                    _ensured = await _audit_journal.ensure_table()
                    if _ensured:
                        logger.info("life_kernel_audit_journal_table_ensured")
                    else:
                        logger.warning("life_kernel_audit_journal_table_ensure_failed")
                except Exception as et_err:
                    logger.warning("life_kernel_audit_journal_ensure_failed", error=str(et_err))
                journal_writer = JournalWriter(audit_journal=_audit_journal)
                # Register the audit journal on app.state so its private engine
                # pool can be disposed on shutdown (MEM-04: avoid leaking a
                # second connection pool alongside life_kernel_engine).
                app.state.life_kernel_audit_journal = _audit_journal
                logger.info("life_kernel_journal_writer_wired")
            except Exception as j_err:
                logger.warning("life_kernel_journal_writer_failed", error=str(j_err))

        except Exception as adapter_err:
            logger.warning("life_kernel_adapters_setup_failed", error=str(adapter_err))

        graph = create_life_mind_graph(
            checkpointer=checkpointer,
            hermes_brain=hermes_brain,
            kg_adapter=kg_adapter,
            memory_adapter=memory_adapter,
            journal_writer=journal_writer,
        )
        app.state.life_mind_graph = graph
        logger.info(
            "life_mind_graph_created",
            checkpointer=checkpointer is not None,
            hermes_brain=hermes_brain is not None,
        )

        import redis.asyncio as aioredis

        _redis_password = os.environ.get("REDIS_PASSWORD", "")
        _redis_url = f"redis://guinevere_core:{_redis_password}@localhost:6380/6"
        redis_client = aioredis.from_url(_redis_url)

        # Discord-visible autonomy (Option B): core-integrated REST publisher.
        # The standalone guinevere-discord.service stays intentionally masked
        # (P2-022); the core publishes the dashboard (edit-not-spam) and the
        # append-only lifecycle log directly via Discord REST. Fail-soft: if
        # the token or channel ids are absent, the kernel runs headless.
        _dashboard_channel_id = os.environ.get("LIFE_KERNEL_DASHBOARD_CHANNEL_ID", "")
        _log_channel_id = os.environ.get("LIFE_KERNEL_LOG_CHANNEL_ID", "")
        # P19 Multi-Project Context: optional project namespace for
        # heartbeat thread_id scoping.  When set AND the
        # feature:projects:enabled Redis flag is ON, the heartbeat
        # thread_id becomes "heartbeat-{project_id}".
        _project_id: str | None = os.environ.get("LIFE_KERNEL_PROJECT_ID") or None
        discord_rest = DiscordRestClient()
        app.state.discord_rest = discord_rest
        if _dashboard_channel_id and discord_rest.enabled:
            dashboard_writer = DashboardWriter(
                rest_client=discord_rest,
                renderer=DashboardRenderer(),
                redis_client=redis_client,
                channel_id=int(_dashboard_channel_id),
            )
            app.state.dashboard_writer = dashboard_writer
            log_channel: object = DiscordLogChannel(discord_rest, int(_log_channel_id)) if _log_channel_id else StructlogLogChannel()
            logger.info(
                "discord_visible_autonomy_wired",
                dashboard_channel=_dashboard_channel_id,
                log_channel=_log_channel_id or "(structlog fallback)",
            )
        else:
            dashboard_writer = None
            log_channel = StructlogLogChannel()
            logger.warning(
                "discord_visible_autonomy_disabled",
                reason="missing_channel_id_or_token",
            )

        heartbeat = HeartbeatService(
            graph=graph,
            redis_client=redis_client,
            checkpointer=checkpointer,
            discord_publisher=dashboard_writer,
            hermes_brain=hermes_brain,
            log_channel=log_channel,
            project_id=_project_id,
        )
        await heartbeat.start()
        app.state.heartbeat = heartbeat
        logger.info("heartbeat_service_started")

        # P22 Life Integration Hub: build the production IntegrationRegistry
        # with real clients (filesystem, vps, discord) and the safety-critical
        # gate shims (HardStopShim bridges Redis life_kernel:hard_stop +
        # HardStopHandler.is_safe; ConsentGateShim fail-closes L2+ until a
        # consent checker is wired). Fail-open for the app: if P22 wiring
        # raises, guinevere-core continues; P22 simply stays inactive.
        try:
            from src.life_integrations.runtime import build_runtime_registry

            _p22_registry, _p22_router = await build_runtime_registry(
                redis_client=redis_client,
                hard_stop_handler=app.state.hard_stop_handler,
                consent_checker=None,  # fail-closed L2+ until consent wired
                project_registry=None,  # P19 registry wired separately if active
                audit_writer=None,
                workspace_root=os.environ.get("GUINEVERE_REPO_ROOT") or "/home/guinevere/code/guinevere",
                discord_rest_client=discord_rest,
            )
            app.state.p22_registry = _p22_registry
            app.state.p22_router = _p22_router
            if _p22_registry is not None:
                logger.info("p22_integration_hub_active", router=type(_p22_router).__name__)
            else:
                logger.warning("p22_integration_hub_inactive", reason="build_runtime_registry returned None")
        except Exception as p22_err:  # noqa: BLE001 — fail-open, never crash core
            logger.warning("p22.activation_failed", error=str(p22_err))
            app.state.p22_registry = None
            app.state.p22_router = None

        # P19 Multi-Project Context: initialize the per-project cognition
        # registry.  When the ``feature:projects:enabled`` flag is OFF, the
        # registry holds a single legacy ``BackgroundCognition`` instance and
        # behaves identically to the pre-P19 runtime (ARCH-02 fix).  When ON,
        # it manages up to N=3 concurrent project-scoped cognition instances.
        try:
            from src.life_kernel.cognition import ProjectAwareCognitionRegistry

            cognition_registry = ProjectAwareCognitionRegistry(max_active=3)
            app.state.cognition_registry = cognition_registry
            logger.info("cognition_registry_initialized", max_active=3)
        except Exception as cr_err:  # noqa: BLE001 — fail-soft startup, logged
            logger.warning("cognition_registry_init_failed", error=str(cr_err))
    except Exception as kernel_err:
        logger.warning("life_kernel_startup_failed", error=str(kernel_err))

    # P5-023: Hermes Bridge is superseded by the Living Autonomy Kernel;
    # kept for backward compatibility but no longer drives autonomy.
    hermes_bridge = None
    try:
        from src.loops.hermes_bridge import create_hermes_bridge

        hermes_bridge = create_hermes_bridge(loop_manager)
        await hermes_bridge.start()
        app.state.hermes_bridge = hermes_bridge
        logger.info("hermes_bridge_started_superseded_by_kernel")
    except Exception as bridge_err:
        logger.warning("hermes_bridge_start_failed", error=str(bridge_err))

    # P5-023: Boot-time resume of pending loops
    try:
        resumed = await loop_manager.resume_pending_loops()
        logger.info("boot_resume_complete", resumed_count=resumed)
    except Exception as resume_err:
        logger.warning("boot_resume_failed", error=str(resume_err))

    # P5-025: Environment Monitor initialization
    env_monitor = None
    try:
        from src.loops.environment import EnvironmentMonitor
        env_monitor = EnvironmentMonitor()
        app.state.env_monitor = env_monitor
        initial_snapshot = await env_monitor.check_all()
        app.state.env_snapshot = initial_snapshot
        logger.info("environment_monitor_started", degradation_level=initial_snapshot.degradation_level)
    except Exception as env_err:
        logger.warning("environment_monitor_start_failed", error=str(env_err))

    logger.info("guinevere_starting", version="0.1.0")
    yield
    logger.info("guinevere_stopping")

    # P20: stop heartbeat first (autonomous clock must halt before downstream shutdown)
    if hasattr(app.state, "heartbeat"):
        try:
            await app.state.heartbeat.stop()
            logger.info("heartbeat_stopped")
        except Exception as hb_err:
            logger.warning("heartbeat_stop_failed", error=str(hb_err))

    # P19 Multi-Project Context: stop all cognition instances (per-project
    # or legacy single-instance).
    if hasattr(app.state, "cognition_registry"):
        try:
            await app.state.cognition_registry.stop_all()
            logger.info("cognition_registry_stopped")
        except Exception as cr_err:  # noqa: BLE001 — fail-soft shutdown, logged
            logger.warning("cognition_registry_stop_failed", error=str(cr_err))

    # P20: close the shared Discord REST client (connection pool release)
    if hasattr(app.state, "discord_rest"):
        try:
            await app.state.discord_rest.close()
            logger.info("discord_rest_closed")
        except Exception as dr_err:
            logger.warning("discord_rest_close_failed", error=str(dr_err))

    # P20 Continuation: dispose the life_kernel DB engine (recall adapters)
    if hasattr(app.state, "life_kernel_engine"):
        try:
            await app.state.life_kernel_engine.dispose()
            logger.info("life_kernel_engine_disposed")
        except Exception as lke_err:
            logger.warning("life_kernel_engine_dispose_failed", error=str(lke_err))

    # P20 Continuation: dispose the PostgresAuditJournal's private engine
    # pool (MEM-04 fix — it creates its own engine separate from
    # life_kernel_engine).
    _audit_journal = getattr(app.state, "life_kernel_audit_journal", None)
    if _audit_journal is not None:
        try:
            _aj_engine = getattr(_audit_journal, "_engine", None)
            if _aj_engine is not None:
                await _aj_engine.dispose()
                logger.info("life_kernel_audit_journal_engine_disposed")
        except Exception as aj_err:
            logger.warning("life_kernel_audit_journal_engine_dispose_failed", error=str(aj_err))

    # Graceful shutdown
    report_scheduler.shutdown(wait=False)

    # P16-002: KG scheduler shutdown
    kg_sched = getattr(app.state, "kg_scheduler", None)
    if kg_sched is not None:
        kg_sched.shutdown(wait=False)
        logger.info("kg_ingestion_cron_stopped")

    # P20: HermesBrain cleanup
    if hasattr(app.state, "hermes_brain"):
        try:
            await app.state.hermes_brain.dispose()
            logger.info("hermes_brain_disposed")
        except Exception as brain_err:
            logger.warning("hermes_brain_dispose_failed", error=str(brain_err))

    # P5-023: Hermes Bridge shutdown (superseded by kernel but kept for compat)
    if hasattr(app.state, "hermes_bridge"):
        await app.state.hermes_bridge.stop()
        logger.info("hermes_bridge_stopped")

    # RG-004: Graceful surveillance consumer shutdown
    surv_consumer = getattr(app.state, "surveillance_consumer", None)
    surv_task = getattr(app.state, "surveillance_task", None)
    surv_engine = getattr(app.state, "surveillance_engine", None)
    if surv_consumer is not None:
        # SurveillanceConsumer.stop() is async — must be awaited, else the
        # coroutine is never awaited (RuntimeWarning + no graceful shutdown).
        try:
            await surv_consumer.stop()
        except Exception as surv_stop_err:  # noqa: BLE001 — fail-soft shutdown
            logger.warning("surveillance_consumer_stop_failed", error=str(surv_stop_err))
    if surv_task is not None:
        surv_task.cancel()
        try:
            await surv_task
        except asyncio.CancelledError:
            pass
    if surv_engine is not None:
        await surv_engine.dispose()
    logger.info("surveillance_consumer_stopped")

    await loop_manager.guardian.stop()
    guardian_task.cancel()
    try:
        await guardian_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Guinevere Core",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# RG-007: Prometheus metrics endpoint
# ---------------------------------------------------------------------------
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
import time

_REQUESTS_TOTAL = Counter(
    "guinevere_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
_REQUEST_DURATION = Histogram(
    "guinevere_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
_HEALTH_FAILURES = Counter(
    "guinevere_health_check_failures_total",
    "Health check component failures",
    ["component", "check"],
)


class _PrometheusMiddleware(BaseHTTPMiddleware):
    """Track request count and duration for Prometheus."""

    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        method = request.method
        endpoint = request.url.path
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        _REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=str(response.status_code)).inc()
        _REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        return response


app.add_middleware(_PrometheusMiddleware)


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "guinevere-core", "version": "0.1.0"}


@app.get("/health/detailed")
async def health_detailed(request: Request):
    """Detailed health check with component status."""
    import asyncio
    import os

    components: dict[str, dict[str, object]] = {}
    status_code = 200

    # Loop Manager check
    loop_mgr = getattr(request.app.state, "loop_manager", None)
    if loop_mgr is not None:
        try:
            loops = await loop_mgr.list_loops()
            components["loop_manager"] = {
                "status": "ok",
                "active_loops": len(loops),
            }
        except Exception:
            components["loop_manager"] = {"status": "error"}
            status_code = 503
    else:
        components["loop_manager"] = {"status": "not_initialized"}
        status_code = 503

    # Guardian check
    guardian_task = getattr(request.app.state, "guardian_task", None)
    if guardian_task is not None and not guardian_task.done():
        components["guardian"] = {"status": "ok"}
    else:
        components["guardian"] = {"status": "not_running"}
        status_code = 503

        # Redis connectivity (optional — fail-soft, don't block health)
    try:
        import redis.asyncio as aioredis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:***@localhost:5433/guinevere_core",
        )
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        components["redis"] = {"status": "ok"}
    except Exception:
        components["redis"] = {"status": "unavailable"}
        # Redis is non-critical for health — don't set 503

    # PostgreSQL connectivity check
    try:
        import asyncpg

        _pg_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere_core",
        )
        # Convert asyncpg URL for sync check
        _pg_url_sync = _pg_url.replace("postgresql+asyncpg://", "postgresql://")
        _pg_conn = await asyncpg.connect(_pg_url_sync, timeout=2)
        await _pg_conn.fetchval("SELECT 1")
        await _pg_conn.close()
        components["postgresql"] = {"status": "ok"}
    except Exception:
        components["postgresql"] = {"status": "unavailable"}
        _HEALTH_FAILURES.labels(component="postgresql", check="connectivity").inc()

    # RG-009: 9Router availability check
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as _client:
            _resp = await _client.get("http://localhost:20128/v1/models")
            if _resp.status_code == 200:
                components["9router"] = {"status": "ok", "models": len(_resp.json().get("data", []))}
            else:
                components["9router"] = {"status": "degraded", "http_status": _resp.status_code}
                _HEALTH_FAILURES.labels(component="9router", check="models_endpoint").inc()
    except Exception:
        components["9router"] = {"status": "unavailable"}
        _HEALTH_FAILURES.labels(component="9router", check="connectivity").inc()

    return JSONResponse(
        status_code=status_code,
        content={
            "service": "guinevere-core",
            "version": "0.1.0",
            "components": components,
        },
    )


@app.get("/status")
async def get_status():
    """P5-025: Full environment status for agent consumption."""
    env_monitor = getattr(app.state, "env_monitor", None)
    if env_monitor is None:
        return {"status": "monitor_unavailable"}
    snapshot = await env_monitor.check_all()
    app.state.env_snapshot = snapshot
    return {
        "timestamp": snapshot.timestamp.isoformat(),
        "degradation_level": snapshot.degradation_level,
        "services": [
            {"name": s.name, "healthy": s.healthy, "latency_ms": s.latency_ms}
            for s in snapshot.services
        ],
        "resources": {
            "cpu": snapshot.resources.cpu_percent,
            "memory": snapshot.resources.memory_percent,
            "disk": snapshot.resources.disk_percent,
            "active_loops": snapshot.resources.active_loops,
        },
    }


@app.get("/")
async def root():
    return {"message": "Guinevere de Baroque is online.", "status": "active"}


# ---------------------------------------------------------------------------
# P5-001: Internal API router — loop management
# ---------------------------------------------------------------------------
from src.core.api.routes import router, internal_router

app.include_router(router)
app.include_router(internal_router)

# ---------------------------------------------------------------------------
# P7-001: Surveillance webhook receiver
# ---------------------------------------------------------------------------
from src.surveillance.router import surveillance_router

app.include_router(surveillance_router)