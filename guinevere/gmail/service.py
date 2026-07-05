from __future__ import annotations

"""P12-001 — Main Gmail service that wires all components together.

Follows the ``WhatsAppService`` pattern from
``guinevere/channels/whatsapp/service.py``:

- ``__init__`` wires all dependencies (lazy init)
- ``start()`` boots OAuth, Pub/Sub, sync, watch, commands, health/metrics
- ``stop()`` graceful reverse-order shutdown
- ``handle_new_email`` / ``handle_pubsub_message`` as entry points
"""

import asyncio
import json
import os
import threading
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

import redis.asyncio as aioredis
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from guinevere.core.services.hard_stop_handler import HardStopHandler
from guinevere.gmail.briefing import BriefingGenerator
from guinevere.gmail.bridge import GmailHermesBridge
from guinevere.gmail.classifier import EmailClassifier
from guinevere.gmail.client import AsyncGmailClient, GmailClient
from guinevere.gmail.commands.consent import EmailConsentCommands
from guinevere.gmail.commands.digest import EmailDigestCommand
from guinevere.gmail.config import GmailSettings, get_gmail_settings
from guinevere.gmail.consent_manager import EmailConsentManager
from guinevere.gmail.context_manager import ThreadContextManager
from guinevere.gmail.draft.discord_ux import DraftApprovalFlow, DraftExpiredError
from guinevere.gmail.draft.generator import DraftGenerator
from guinevere.gmail.draft.send_pipeline import DraftSendPipeline
from guinevere.gmail.envelope import GmailMessageEnvelope
from guinevere.gmail.exceptions import GmailError
from guinevere.gmail.financial_extractor import FinancialExtractor
from guinevere.gmail.hard_stop import EmailHardStopChecker
from guinevere.gmail.memory_store import EmailMemoryStore
from guinevere.gmail.metrics import set_connected, set_watch_active
from guinevere.gmail.notification import EmailNotifier
from guinevere.gmail.pubsub_client import PubSubClient, WatchManager
from guinevere.gmail.resend_client import ResendClient
from guinevere.gmail.router import EmailRouter
from guinevere.gmail.sanitization import ContentSanitizer
from guinevere.gmail.scorer import ImportanceScorer
from guinevere.gmail.secret_scanner import CombinedScanner
from guinevere.gmail.sync_engine import SyncEngine, SyncScheduler
from guinevere.gmail.token_manager import TokenManager
from guinevere.hermes._memory_bridge import HermesMemoryBridge
from guinevere.surveillance.consent_gate import ConsentChecker

logger = structlog.get_logger("gmail.service")

_HEALTH_BIND_HOST: str = "127.0.0.1"
_METRICS_BIND_HOST: str = "127.0.0.1"


class GmailService:
    """Main Gmail service — wires all sub-components and manages lifecycle.

    Delegates email processing to ``EmailRouter`` and provides
    start/stop lifecycle, health (port 8096) and Prometheus
    (port 9101) HTTP endpoints.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        scheduler: AsyncIOScheduler | None = None,
        hard_stop_handler: HardStopHandler | None = None,
        consent_checker: ConsentChecker | None = None,
        persona_plugin: Any | None = None,
        memory_bridge: HermesMemoryBridge | None = None,
        discord_webhook_url: str = "",
        faiz_user_id: int = 0,
        health_port: int = 8096,
        metrics_port: int = 9101,
        hermes_runtime: Any | None = None,
    ) -> None:
        """Initialise the Gmail service with optional dependency injection.

        All components are lazily created in :meth:`start` so that
        passing ``None`` for optional deps triggers auto-creation
        from settings + defaults.

        Note:
            *hermes_runtime* is kept for backward compatibility but is
            no longer used — the bridge uses ``get_adapter()`` directly.
        """
        self._provided_redis: aioredis.Redis | None = redis_client
        self._scheduler: AsyncIOScheduler | None = scheduler
        self._hard_stop_handler: HardStopHandler | None = hard_stop_handler
        self._consent_checker: ConsentChecker | None = consent_checker
        self._persona_plugin: Any | None = persona_plugin
        self._memory_bridge: HermesMemoryBridge | None = memory_bridge
        self._discord_webhook_url: str = discord_webhook_url
        self._faiz_user_id: int = faiz_user_id
        self._health_port: int = health_port
        self._metrics_port: int = metrics_port

        # ── Lazy-initialised state ──────────────────────────────────────
        self._settings: GmailSettings | None = None
        self._redis: aioredis.Redis | None = None
        self._token_manager: TokenManager | None = None
        self._gmail_client: AsyncGmailClient | None = None
        self._sync_instance: SyncEngine | None = None
        self._sync_scheduler: SyncScheduler | None = None
        self._sanitizer: ContentSanitizer | None = None
        self._scanner: CombinedScanner | None = None
        self._consent: EmailConsentManager | None = None
        self._classifier: EmailClassifier | None = None
        self._scorer: ImportanceScorer | None = None
        self._context_manager: ThreadContextManager | None = None
        self._memory_store: EmailMemoryStore | None = None
        self._financial_extractor: FinancialExtractor | None = None
        self._draft_generator: DraftGenerator | None = None
        self._draft_approval: DraftApprovalFlow | None = None
        self._draft_sender: DraftSendPipeline | None = None
        self._notifier: EmailNotifier | None = None
        self._briefing: BriefingGenerator | None = None
        self._bridge: GmailHermesBridge | None = None
        self._router: EmailRouter | None = None
        self._pubsub: PubSubClient | None = None
        self._watch_manager: WatchManager | None = None
        self._hard_stop_checker: EmailHardStopChecker | None = None
        self._digest_command: EmailDigestCommand | None = None
        self._consent_commands: EmailConsentCommands | None = None
        self._resend_client: ResendClient | None = None
        self._health_httpd: ThreadingHTTPServer | None = None
        self._health_http_thread: threading.Thread | None = None
        self._metrics_httpd: ThreadingHTTPServer | None = None
        self._metrics_http_thread: threading.Thread | None = None

        # ── Runtime state ───────────────────────────────────────────────
        self._running: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None

        logger.info("gmail.service.initialized")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the Gmail service.

        Startup order:
        1. Load settings, connect Redis
        2. Initialise TokenManager (load credentials, start background refresh)
        3. Create GmailClient + AsyncGmailClient
        4. Initialise SyncEngine + SyncScheduler
        5. Create all security/content components
        6. Create classifier, scorer, thread context, memory, financial
        7. Create draft pipeline components
        8. Create notification + briefing components
        9. Wire EmailRouter
        10. Create PubSubClient + WatchManager, start Pub/Sub + watch
        11. Register commands
        12. Start health (8096) and Prometheus (9101) HTTP servers
        13. Start sync polling
        14. Register APScheduler jobs (briefing + watch renewal)
        """
        self._loop = asyncio.get_running_loop()
        logger.info("gmail.service.starting")

        # 1. Settings + Redis
        settings = self._initialize_settings()
        self._settings = settings
        self._redis = self._build_redis()
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()

        # 2. TokenManager
        try:
            self._token_manager = TokenManager(settings)
            await self._token_manager.initialize()
            await self._token_manager.start_background_refresh()
            set_connected(True)
            logger.info("gmail.service.token_ok")
        except GmailError as exc:
            logger.error("gmail.service.token_init_failed", error=str(exc))
            raise

        # 3. Gmail client
        try:
            creds = await self._token_manager.get_credentials()
            sync_client = GmailClient(credentials=creds, settings=settings)
            self._gmail_client = AsyncGmailClient(sync_client)
            logger.info("gmail.service.client_ok")
        except GmailError as exc:
            logger.error("gmail.service.client_init_failed", error=str(exc))
            raise

        # 4. Sync engine
        try:
            self._sync_instance = SyncEngine(
                client=self._gmail_client,
                settings=settings,
                redis_client=self._redis,
            )
            await self._sync_instance.initialize()
            self._sync_scheduler = SyncScheduler(
                engine=self._sync_instance,
                settings=settings,
                on_new_envelope=self.handle_new_email,
            )
            logger.info("gmail.service.sync_ok")
        except GmailError as exc:
            logger.warning(
                "gmail.service.sync_init_warning",
                error=str(exc),
            )

        # 5. Security + content components
        self._sanitizer = ContentSanitizer()
        self._scanner = CombinedScanner()

        # 6. Consent manager
        self._consent = EmailConsentManager(
            consent_checker=self._consent_checker or self._default_consent_checker(),
            redis=self._redis,
        )

        # 7. Hermes bridge (always created; uses get_adapter internally)
        try:
            self._bridge = GmailHermesBridge()
            logger.info("gmail.service.bridge_ok")
        except Exception as exc:
            logger.warning(
                "gmail.service.bridge_init_warning",
                error=str(exc),
            )

        # 8. Classifier + scorer (with bridge for Tier 3 LLM)
        self._classifier = EmailClassifier(settings, bridge=self._bridge)
        self._scorer = ImportanceScorer(settings)

        # 9. Thread context, memory, financial
        self._context_manager = ThreadContextManager(
            redis=self._redis,
            settings=settings,
        )
        self._memory_store = EmailMemoryStore(
            redis=self._redis,
            settings=settings,
        )
        self._financial_extractor = FinancialExtractor(
            redis=self._redis,
            settings=settings,
        )

        # 10. Draft pipeline (with bridge for LLM generation)
        self._draft_generator = DraftGenerator(settings, bridge=self._bridge)
        self._draft_approval = DraftApprovalFlow(
            redis=self._redis,
            settings=settings,
        )
        self._draft_sender = DraftSendPipeline(
            gmail_client=self._gmail_client,
            sanitizer=self._sanitizer,
            scanner=self._scanner,
            settings=settings,
        )

        # 11. Notification + briefing
        notifier_webhook = (
            self._discord_webhook_url
            or os.environ.get("GMAIL_NOTIFICATION_WEBHOOK_URL", "")
        )
        self._notifier = EmailNotifier(
            webhook_url=notifier_webhook,
            quiet_start=settings.quiet_hours_start,
            quiet_end=settings.quiet_hours_end,
            importance_threshold=settings.importance_notify_threshold,
        )
        self._briefing = BriefingGenerator(
            memory_store=self._memory_store,
            config=settings,
            webhook_url=self._discord_webhook_url,
        )

        # 12. Hard stop checker
        if self._hard_stop_handler is not None:
            try:
                self._hard_stop_checker = EmailHardStopChecker(
                    hard_stop_handler=self._hard_stop_handler,
                    settings=settings,
                )
                logger.info("gmail.service.hard_stop_ok")
            except Exception as exc:
                logger.warning(
                    "gmail.service.hard_stop_init_warning",
                    error=str(exc),
                )
        else:
            logger.info("gmail.service.hard_stop_disabled")

        # 13. Resend client
        try:
            self._resend_client = ResendClient(settings)
            await self._resend_client.initialize()
            logger.info("gmail.service.resend_ok")
        except Exception as exc:
            logger.warning(
                "gmail.service.resend_init_warning",
                error=str(exc),
            )

        # 14. EmailRouter — wires all pipeline components
        self._router = EmailRouter(
            sanitizer=self._sanitizer,
            scanner=self._scanner,
            consent=self._consent,
            classifier=self._classifier,
            scorer=self._scorer,
            notifier=self._notifier,
            memory=self._memory_store,
            financial_extractor=self._financial_extractor,
            draft_generator=self._draft_generator,
            draft_approval=self._draft_approval,
            draft_sender=self._draft_sender,
            hard_stop_handler=self._hard_stop_checker,
        )

        # 15. Mark as running before backfill + services start
        self._running = True

        # 16. Initial backfill on first boot (before polling starts)
        if self._sync_instance is not None and self._sync_instance.bootstrapped:
            try:
                count = 0
                async for envelope in self._sync_instance.backfill(days=1):
                    await self.handle_new_email(envelope)
                    count += 1
                logger.info(
                    "gmail.service.initial_backfill_done",
                    count=count,
                )
            except Exception as exc:
                logger.warning(
                    "gmail.service.initial_backfill_error",
                    error=str(exc),
                )

        # 17. Pub/Sub + Watch
        try:
            self._pubsub = PubSubClient(
                settings=settings,
                on_notification=self._on_pubsub_notification,
            )
            await self._pubsub.start()
            self._watch_manager = WatchManager(
                gmail_client=self._gmail_client,
                settings=settings,
            )
            await self._watch_manager.start()
            set_watch_active(True)
            logger.info("gmail.service.pubsub_ok")
        except GmailError as exc:
            logger.warning(
                "gmail.service.pubsub_init_warning",
                error=str(exc),
            )
        except Exception as exc:
            logger.warning(
                "gmail.service.pubsub_init_warning",
                error=str(exc),
            )

        # 17. Discord commands
        self._digest_command = EmailDigestCommand(
            briefing_generator=self._briefing,
            faiz_user_id=self._faiz_user_id,
        )
        self._consent_commands = EmailConsentCommands(
            consent_manager=self._consent,
            token_manager=self._token_manager,
        )

        # 18. Start sync polling
        if self._sync_scheduler is not None:
            try:
                await self._sync_scheduler.start()
                logger.info("gmail.service.sync_polling_started")
            except Exception as exc:
                logger.warning(
                    "gmail.service.sync_polling_start_warning",
                    error=str(exc),
                )

        # 19. APScheduler jobs
        if self._scheduler is not None:
            try:
                self._scheduler.start()
                self._briefing.start_scheduler(self._scheduler)
                logger.info(
                    "gmail.service.scheduler_ok",
                    briefing_hour=settings.briefing_hour,
                    timezone=settings.briefing_timezone,
                )
            except Exception as exc:
                logger.warning(
                    "gmail.service.scheduler_start_warning",
                    error=str(exc),
                )

        # 20. Health + Metrics HTTP servers
        self._start_health_server()
        self._start_metrics_server()

        logger.info(
            "gmail.service.started",
            health_port=self._health_port,
            metrics_port=self._metrics_port,
        )

    async def stop(self) -> None:
        """Graceful reverse-order shutdown.

        Stop order:
        1. APScheduler jobs
        2. Sync polling
        3. Pub/Sub + Watch
        4. HTTP servers
        5. Gmail client
        6. Token manager background refresh
        """
        self._running = False
        logger.info("gmail.service.stopping")

        # 1. APScheduler
        if self._briefing is not None:
            try:
                self._briefing.stop_scheduler()
            except Exception as exc:
                logger.warning(
                    "gmail.service.briefing_stop_error",
                    error=str(exc),
                )
        if self._scheduler is not None:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception as exc:
                logger.warning(
                    "gmail.service.scheduler_stop_error",
                    error=str(exc),
                )

        # 2. Sync scheduler
        if self._sync_scheduler is not None:
            try:
                await self._sync_scheduler.stop()
            except Exception as exc:
                logger.warning(
                    "gmail.service.sync_stop_error",
                    error=str(exc),
                )

        # 3. Watch + Pub/Sub
        if self._watch_manager is not None:
            try:
                await self._watch_manager.stop()
            except Exception as exc:
                logger.warning(
                    "gmail.service.watch_stop_error",
                    error=str(exc),
                )
        set_watch_active(False)

        if self._pubsub is not None:
            try:
                await self._pubsub.stop()
            except Exception as exc:
                logger.warning(
                    "gmail.service.pubsub_stop_error",
                    error=str(exc),
                )

        # 4. HTTP servers
        self._stop_health_server()
        self._stop_metrics_server()

        # 5. Token manager background refresh
        if self._token_manager is not None:
            try:
                await self._token_manager.stop()
            except Exception as exc:
                logger.warning(
                    "gmail.service.token_stop_error",
                    error=str(exc),
                )

        set_connected(False)
        logger.info("gmail.service.stopped")

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    async def handle_new_email(self, envelope: GmailMessageEnvelope) -> None:
        """Process a single inbound email through the pipeline.

        Delegates to ``EmailRouter.route_envelope()`` which runs the
        full sanitise → scan → classify → score → route pipeline.
        """
        if not self._running:
            logger.warning(
                "gmail.service.not_running",
                message_id=envelope.message_id,
            )
            return

        if self._router is None:
            logger.warning(
                "gmail.service.no_router",
                message_id=envelope.message_id,
            )
            return

        try:
            result = await self._router.route_envelope(envelope)
            logger.info(
                "gmail.service.email_processed",
                message_id=result.envelope_id,
                category=result.category.value,
                importance=result.importance,
                blocked=result.blocked,
                actions=result.action_taken,
            )
        except GmailError as exc:
            logger.error(
                "gmail.service.route_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception(
                "gmail.service.route_unexpected_error",
                message_id=envelope.message_id,
                error=str(exc),
            )

    async def handle_pubsub_message(
        self,
        _message: Any = None,
    ) -> None:
        """Handle an incoming Pub/Sub notification.

        Triggers a sync cycle via ``SyncScheduler.trigger_sync()`` and
        routes any new messages through the pipeline.
        """
        logger.debug("gmail.service.pubsub_message_received")
        if self._sync_scheduler is None:
            logger.warning("gmail.service.pubsub_no_sync_scheduler")
            return

        try:
            envelopes = await self._sync_scheduler.trigger_sync()
            logger.info(
                "gmail.service.pubsub_sync_complete",
                new_messages=len(envelopes),
            )
            for envelope in envelopes:
                await self.handle_new_email(envelope)
        except Exception as exc:
            logger.error(
                "gmail.service.pubsub_sync_error",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Return a component-level health status dict.

        Checks:
        - Service running flag
        - Token manager authentication
        - Redis connectivity
        - Sync engine state (if initialised)
        - Pub/Sub active
        - Watch active
        """
        result: dict[str, Any] = {
            "service": "gmail",
            "running": self._running,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Token
        if self._token_manager is not None:
            result["authenticated"] = self._token_manager.is_authenticated
            result["token_age_seconds"] = round(
                self._token_manager.token_age_seconds, 1,
            )
        else:
            result["authenticated"] = False
            result["token_age_seconds"] = 0.0

        # Redis
        if self._redis is not None:
            try:
                redis_ok = bool(await self._redis.ping())
            except Exception:
                logger.debug("gmail.service.redis_ping_failed", exc_info=True)
                redis_ok = False
            result["redis_ok"] = redis_ok
        else:
            result["redis_ok"] = False

        # Sync state
        if self._sync_instance is not None:
            try:
                state = await self._sync_instance.get_sync_state()
                result["sync"] = {
                    "history_id": state.history_id,
                    "mode": state.mode,
                    "total_synced": state.total_synced,
                    "last_sync_time": state.last_sync_time,
                }
            except Exception:
                logger.debug("gmail.service.sync_state_unavailable", exc_info=True)
                result["sync"] = {"error": "unavailable"}
        else:
            result["sync"] = None

        # Pub/Sub
        if self._pubsub is not None:
            result["pubsub_active"] = self._pubsub.is_active
        else:
            result["pubsub_active"] = False

        # Watch
        if self._watch_manager is not None:
            result["watch_active"] = self._watch_manager.is_watching
            exp = self._watch_manager.watch_expiration
            result["watch_expiration"] = exp.isoformat() if exp else None
        else:
            result["watch_active"] = False
            result["watch_expiration"] = None

        # Router
        result["router_initialized"] = self._router is not None

        return result

    # ------------------------------------------------------------------
    # Email Search
    # ------------------------------------------------------------------

    async def search_emails(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search gmail_memory_episodes using PostgreSQL full-text search.

        Args:
            query: Search query string.
            limit: Maximum number of results to return (capped at 50).

        Returns:
            List of dicts with: subject, date, category, importance,
            summary_snippet, rank.
        """
        dsn = os.environ.get("DATABASE_URL", "")
        if not dsn:
            logger.warning("gmail.service.search_no_database_url")
            return []

        # Normalize asyncpg DSN to psycopg format
        clean_dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

        import asyncpg  # noqa: PLC0415

        try:
            conn = await asyncpg.connect(dsn=clean_dsn)
            rows = await conn.fetch(
                """
                SELECT
                    episode_id,
                    subject,
                    category,
                    importance,
                    summary,
                    stored_at,
                    ts_rank(search_vector, plainto_tsquery('english', $1)) AS rank
                FROM gmail_memory_episodes
                WHERE search_vector @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC, stored_at DESC
                LIMIT $2
                """,
                query,
                max(1, min(limit, 50)),
            )
            await conn.close()

            results: list[dict[str, Any]] = []
            for row in rows:
                summary_text = row["summary"] or ""
                snippet = (
                    summary_text[:150] + "..."
                    if len(summary_text) > 150
                    else summary_text
                )
                stored_at = row["stored_at"]
                date_str = stored_at.isoformat() if stored_at else None

                results.append({
                    "episode_id": row["episode_id"],
                    "subject": row["subject"] or "(no subject)",
                    "date": date_str,
                    "category": row["category"] or "unknown",
                    "importance": row["importance"] or 0,
                    "summary_snippet": snippet,
                    "rank": float(row["rank"]),
                })
            return results
        except Exception as exc:
            logger.exception(
                "gmail.service.search_error",
                error=str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def router(self) -> EmailRouter | None:
        """Expose the router for external callers (e.g. Discord commands)."""
        return self._router

    @property
    def digest_command(self) -> EmailDigestCommand | None:
        """Expose the digest command handler."""
        return self._digest_command

    @property
    def consent_commands(self) -> EmailConsentCommands | None:
        """Expose the consent command handler."""
        return self._consent_commands

    @property
    def token_manager(self) -> TokenManager | None:
        """Expose the token manager for external re-auth triggers."""
        return self._token_manager

    @property
    def briefing(self) -> BriefingGenerator | None:
        """Expose the briefing generator for on-demand digests."""
        return self._briefing

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _initialize_settings(self) -> GmailSettings:
        """Load GmailSettings from environment (Pydantic)."""
        try:
            return get_gmail_settings()
        except Exception as exc:
            logger.error("gmail.service.settings_load_failed", error=str(exc))
            raise GmailError(
                f"Failed to load GmailSettings: {exc}",
            ) from exc

    def _build_redis(self) -> aioredis.Redis:
        """Return a Redis client — either injected or from env URL."""
        if self._provided_redis is not None:
            return self._provided_redis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        return aioredis.from_url(redis_url, decode_responses=False)

    def _default_consent_checker(self) -> ConsentChecker:
        """Build a permissive stub consent checker when none was injected.

        The caller should normally inject a real ``ConsentChecker``
        from ``guinevere.surveillance.consent_gate``.  This fallback
        always returns allowed=True so the pipeline can proceed.
        """
        from datetime import UTC, datetime

        from guinevere.surveillance.consent_gate import (
            ConsentCheckResult,
            ConsentStatus,
        )

        class _AllowAllConsentChecker:
            """Permissive consent checker — always allows."""

            async def check_consent(self, scope: str) -> ConsentCheckResult:
                return ConsentCheckResult(
                    allowed=True,
                    status=ConsentStatus.ACTIVE,
                    scope=scope,
                    reason="default allow-all checker (stub)",
                    checked_at=datetime.now(UTC),
                )

        return _AllowAllConsentChecker()

    async def _on_pubsub_notification(self, history_id: str) -> None:
        """Callback invoked by ``PubSubClient`` on each Gmail notification.

        Triggers a sync cycle via the ``SyncScheduler``.
        """
        logger.info(
            "gmail.service.pubsub_notification",
            history_id=history_id,
        )
        await self.handle_pubsub_message()

    # ------------------------------------------------------------------
    # Financial extracts helper (Point 4)
    # ------------------------------------------------------------------

    async def _read_financial_extracts(
        self,
        since: datetime,
    ) -> list[dict[str, Any]]:
        """Read financial extracts from Redis filtered by timestamp.

        Returns a list of dicts with extraction_id, amount, currency,
        category, sender, subject, extracted_at, and raw data.
        """
        redis = self._redis
        if redis is None:
            return []

        results: list[dict[str, Any]] = []
        since_ts: float = since.timestamp()

        try:
            member_scores: list[tuple[bytes, float]] = await redis.zrangebyscore(
                "guinevere:gmail:financial:by_time",
                min=since_ts,
                max="+inf",
                withscores=True,
            )
        except Exception:
            logger.exception("gmail.service.financial_redis_read_error")
            return []

        for member_bytes, score in member_scores:
            eid: str = member_bytes.decode("utf-8", errors="replace")
            try:
                raw: dict[bytes, bytes] = await redis.hgetall(
                    f"guinevere:gmail:financial:{eid}",
                )
                if not raw:
                    continue
                entry: dict[str, str] = {
                    k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                    for k, v in raw.items()
                }
                results.append({
                    "extraction_id": eid,
                    "amount": entry.get("amount", ""),
                    "currency": entry.get("currency", "IDR"),
                    "category": entry.get("category", ""),
                    "sender": entry.get("sender", ""),
                    "subject": entry.get("subject", ""),
                    "extracted_at": entry.get("extracted_at", ""),
                })
            except Exception:
                logger.debug("gmail.service.financial_entry_parse_failed", exc_info=True)
                continue

        return results

    # ------------------------------------------------------------------
    # HTTP servers
    # ------------------------------------------------------------------

    def _start_health_server(self) -> None:
        """Start the health-check HTTP server on port 8096 (127.0.0.1).

        Endpoints:
          GET  /health                          — component health status
          GET  /api/email-digest?range=24h      — email digest for Discord
          GET  /api/email-search?q=QUERY        — full-text email search
          GET  /api/financial-extracts?since=   — financial extraction data
          POST /api/email-consent               — consent grant/revoke/status
          POST /api/email-reauth                — force OAuth token refresh
          POST /api/approval-reaction           — draft approval reaction (✅❌✏️)
        """
        service = self

        class HealthHandler(BaseHTTPRequestHandler):
            # ── GET ────────────────────────────────────────────────────────
            def do_GET(self) -> None:  # noqa: N802
                path, params = self._parse_path()
                if path == "/health":
                    self._handle_health()
                elif path == "/api/email-digest":
                    self._handle_email_digest(params)
                elif path == "/api/financial-extracts":
                    self._handle_financial_extracts(params)
                elif path == "/api/email-search":
                    self._handle_email_search(params)
                elif path == "/api/financial-extracts":
                    self._handle_financial_extracts(params)
                else:
                    self._json_response(404, {"error": "not found"})

            # ── POST ───────────────────────────────────────────────────────
            def do_POST(self) -> None:  # noqa: N802
                path, _params = self._parse_path()
                if path == "/api/email-consent":
                    self._handle_email_consent()
                elif path == "/api/email-reauth":
                    self._handle_email_reauth()
                elif path == "/api/approval-reaction":
                    self._handle_approval_reaction()
                else:
                    self._json_response(404, {"error": "not found"})

            # ── Path + query parser ────────────────────────────────────────
            def _parse_path(
                self,
            ) -> tuple[str, dict[str, object]]:
                """Return ``(path, params_dict)``."""
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(self.path)
                qs: dict[str, list[str]] = parse_qs(parsed.query)
                params: dict[str, object] = {
                    k: v[0] for k, v in qs.items()
                }
                return (parsed.path, params)

            # ── JSON response helper ───────────────────────────────────────
            def _json_response(
                self,
                status: int,
                data: dict[str, object],
            ) -> None:
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            # ── Shorthand: run async on service loop ───────────────────────
            def _run_async(
                self,
                coro: Coroutine[Any, Any, Any],
                timeout: float = 10.0,
            ) -> Any:
                loop = service._loop
                if loop is None or not loop.is_running():
                    raise RuntimeError("event_loop_not_available")
                return asyncio.run_coroutine_threadsafe(
                    coro, loop,
                ).result(timeout=timeout)

            # ── GET /health ─────────────────────────────────────────────────
            def _handle_health(self) -> None:
                try:
                    health_data = self._run_async(service.health_check())
                except Exception as exc:
                    self._json_response(503, {
                        "status": "error",
                        "reason": str(exc),
                    })
                    return

                is_healthy = bool(
                    health_data.get("running", False)
                    and health_data.get("authenticated", False)
                )
                self._json_response(
                    200 if is_healthy else 503,
                    health_data,  # type: ignore[arg-type]
                )

            # ── GET /api/email-digest ──────────────────────────────────────
            def _handle_email_digest(
                self,
                params: dict[str, object],
            ) -> None:
                raw: object = params.get("range", "12h")
                time_range: str = str(raw) if not isinstance(raw, str) else raw
                if service._briefing is None:
                    self._json_response(503, {
                        "error": "briefing_not_available",
                    })
                    return
                try:
                    result: str = self._run_async(
                        service._briefing.digest_command(time_range),
                    )
                    self._json_response(200, {
                        "ok": True,
                        "digest": result,
                    })
                except Exception as exc:
                    logger.exception(
                        "gmail.service.api_digest_error",
                        time_range=time_range,
                    )
                    self._json_response(500, {
                        "error": str(exc),
                    })

            # ── GET /api/email-search ──────────────────────────────────────
            def _handle_email_search(
                self,
                params: dict[str, object],
            ) -> None:
                raw_q: object = params.get("q", "")
                query: str = str(raw_q) if not isinstance(raw_q, str) else raw_q
                if not query.strip():
                    self._json_response(400, {
                        "error": "missing_q_parameter",
                    })
                    return

                raw_limit: object = params.get("limit", "10")
                try:
                    limit: int = int(str(raw_limit))
                except (ValueError, TypeError):
                    limit = 10
                limit = max(1, min(limit, 50))

                try:
                    results: list[dict[str, Any]] = self._run_async(
                        service.search_emails(query, limit),
                    )
                    self._json_response(200, {
                        "ok": True,
                        "query": query,
                        "count": len(results),
                        "results": results,
                    })
                except Exception as exc:
                    logger.exception(
                        "gmail.service.api_search_error",
                        query=query,
                    )
                    self._json_response(500, {
                        "error": str(exc),
                    })

            # ── POST /api/email-consent ────────────────────────────────────
            def _handle_email_consent(self) -> None:
                body_bytes: bytes = self.rfile.read(
                    int(self.headers.get("Content-Length", 0)),
                )
                try:
                    payload: dict[str, object] = json.loads(
                        body_bytes.decode("utf-8"),
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._json_response(400, {"error": "invalid_json"})
                    return

                action: str = str(payload.get("action", ""))
                actor: str = str(
                    payload.get("actor", "faiz_via_api"),
                )

                consent = service._consent
                if consent is None:
                    self._json_response(503, {
                        "error": "consent_manager_not_available",
                    })
                    return

                try:
                    if action == "grant":
                        ok: bool = self._run_async(
                            consent.grant_consent(actor),
                        )
                        self._json_response(200, {
                            "ok": ok,
                            "status": "granted" if ok else "grant_failed",
                        })
                    elif action == "revoke":
                        ok = self._run_async(
                            consent.revoke_consent(actor),
                        )
                        self._json_response(200, {
                            "ok": ok,
                            "status": "revoked" if ok else "revoke_failed",
                        })
                    elif action == "status":
                        result = self._run_async(
                            consent.check_email_consent(),
                        )
                        self._json_response(200, {
                            "ok": True,
                            "allowed": result.allowed,
                            "status": result.status.value,
                        })
                    else:
                        self._json_response(400, {
                            "error": f"unknown action: {action}",
                        })
                except Exception as exc:
                    logger.exception(
                        "gmail.service.api_consent_error",
                        action=action,
                    )
                    self._json_response(500, {"error": str(exc)})

            # ── POST /api/email-reauth ─────────────────────────────────────
            def _handle_email_reauth(self) -> None:
                tm = service._token_manager
                if tm is None:
                    self._json_response(503, {
                        "error": "token_manager_not_available",
                    })
                    return
                try:
                    self._run_async(tm.force_refresh())
                    age: float = tm.token_age_seconds
                    self._json_response(200, {
                        "ok": True,
                        "token_age_seconds": round(age, 1),
                    })
                except Exception as exc:
                    logger.exception("gmail.service.api_reauth_error")
                    self._json_response(500, {"error": str(exc)})

            # ── POST /api/approval-reaction ──────────────────────────────────
            def _handle_approval_reaction(self) -> None:
                body_bytes: bytes = self.rfile.read(
                    int(self.headers.get("Content-Length", 0)),
                )
                try:
                    payload: dict[str, object] = json.loads(
                        body_bytes.decode("utf-8"),
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._json_response(400, {"error": "invalid_json"})
                    return

                draft_id: str = str(payload.get("message_id", ""))
                emoji: str = str(payload.get("emoji", ""))
                raw_user: object = payload.get("user_id", 0)
                try:
                    user_id: int = int(str(raw_user))
                except (ValueError, TypeError):
                    self._json_response(400, {"error": "invalid_user_id"})
                    return

                if not draft_id or not emoji:
                    self._json_response(400, {"error": "missing_message_id_or_emoji"})
                    return

                approval = service._draft_approval
                if approval is None:
                    self._json_response(503, {
                        "error": "draft_approval_not_available",
                    })
                    return

                try:
                    state: str = self._run_async(
                        approval.handle_reaction(draft_id, emoji, user_id),
                    )
                    self._json_response(200, {
                        "ok": True,
                        "state": state,
                        "message_id": draft_id,
                    })
                except DraftExpiredError as exc:
                    self._json_response(410, {
                        "ok": False,
                        "state": "expired",
                        "error": str(exc),
                    })
                except Exception as exc:
                    logger.exception(
                        "gmail.service.api_approval_reaction_error",
                        draft_id=draft_id,
                    )
                    self._json_response(500, {"error": str(exc)})

            # ── GET /api/financial-extracts ────────────────────────────────
            def _handle_financial_extracts(
                self,
                params: dict[str, object],
            ) -> None:
                raw_since: object = params.get("since", "")
                since_str: str = str(raw_since) if not isinstance(raw_since, str) else raw_since

                from datetime import datetime as dt

                if since_str:
                    try:
                        since_dt = dt.fromisoformat(since_str)
                    except (ValueError, TypeError):
                        self._json_response(400, {
                            "error": "invalid_since_format",
                            "hint": "Use ISO 8601 format (e.g. 2026-06-14T00:00:00)",
                        })
                        return
                else:
                    since_dt = dt.now(UTC) - timedelta(days=7)

                try:
                    extracts: list[dict[str, Any]] = self._run_async(
                        service._read_financial_extracts(since_dt),
                    )
                    self._json_response(200, {
                        "ok": True,
                        "since": since_dt.isoformat(),
                        "count": len(extracts),
                        "extracts": extracts,
                    })
                except Exception as exc:
                    logger.exception("gmail.service.api_financial_extracts_error")
                    self._json_response(500, {"error": str(exc)})

            # ── Logging ────────────────────────────────────────────────────
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                logger.debug("gmail.service.health_http", message=format % args)

        self._health_httpd = ThreadingHTTPServer(
            (_HEALTH_BIND_HOST, self._health_port),
            HealthHandler,
        )
        self._health_http_thread = threading.Thread(
            target=self._health_httpd.serve_forever,
            name="guinevere-gmail-health",
            daemon=True,
        )
        self._health_http_thread.start()
        logger.info(
            "gmail.service.health_server_started",
            host=_HEALTH_BIND_HOST,
            port=self._health_port,
        )

    def _stop_health_server(self) -> None:
        """Stop the health HTTP server."""
        if self._health_httpd is not None:
            try:
                self._health_httpd.shutdown()
                self._health_httpd.server_close()
            except Exception as exc:
                logger.warning(
                    "gmail.service.health_server_stop_error",
                    error=str(exc),
                )
            self._health_httpd = None
        if self._health_http_thread is not None:
            self._health_http_thread.join(timeout=2)
            self._health_http_thread = None
        logger.info("gmail.service.health_server_stopped")

    def _start_metrics_server(self) -> None:
        """Start the Prometheus metrics HTTP server on port 9101 (127.0.0.1)."""
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path != "/metrics":
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":"not found"}')
                    return

                payload = generate_latest()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                logger.debug(
                    "gmail.service.metrics_http",
                    message=format % args,
                )

        self._metrics_httpd = ThreadingHTTPServer(
            (_METRICS_BIND_HOST, self._metrics_port),
            MetricsHandler,
        )
        self._metrics_http_thread = threading.Thread(
            target=self._metrics_httpd.serve_forever,
            name="guinevere-gmail-metrics",
            daemon=True,
        )
        self._metrics_http_thread.start()
        logger.info(
            "gmail.service.metrics_server_started",
            host=_METRICS_BIND_HOST,
            port=self._metrics_port,
        )

    def _stop_metrics_server(self) -> None:
        """Stop the Prometheus metrics HTTP server."""
        if self._metrics_httpd is not None:
            try:
                self._metrics_httpd.shutdown()
                self._metrics_httpd.server_close()
            except Exception as exc:
                logger.warning(
                    "gmail.service.metrics_server_stop_error",
                    error=str(exc),
                )
            self._metrics_httpd = None
        if self._metrics_http_thread is not None:
            self._metrics_http_thread.join(timeout=2)
            self._metrics_http_thread = None
        logger.info("gmail.service.metrics_server_stopped")

    async def run_forever(self) -> None:
        """Run the service until cancelled."""
        if not self._running:
            await self.start()
        await asyncio.Event().wait()


__all__ = [
    "GmailService",
]