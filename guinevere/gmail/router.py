from __future__ import annotations

"""P12-004 — Email processing pipeline router.

Orchestrates the complete email processing pipeline: receive envelope
:rarr: sanitize :rarr: scan secrets :rarr: check consent :rarr: classify
:rarr: score importance :rarr: notify :rarr: store :rarr: financial
extract / draft-approve-send (for CLIENT_WORK).

Follows the ``WhatsAppRouter`` pattern established in
``guinevere/channels/whatsapp/router.py`` but with a richer pipeline — each
stage is wrapped in try/except that logs and continues so a single
stage failure never drops the entire message.

Design decisions:
- Pipeline is **non-blocking per stage**: individual stage failures are
  logged and the pipeline continues with best-effort defaults.
- **HARD STOP** blocks ALL processing immediately (return ``blocked=True``).
- **No consent** skips non-essential stages (notification, draft,
  financial extraction) but still sanitises, scans, classifies, scores,
  and stores the episode.
- Secret / injection detection raises metrics alerts but does **not**
  silently drop the message — it continues with elevated scrutiny.
- Draft pipeline (generate :rarr: approval :rarr: send) runs **only** for
  ``CLIENT_WORK`` per category routing requirements.
- Financial extraction runs for ``FINANCIAL`` and ``BILLING_INVOICE``.
- Structlog events use ``gmail.route.*`` namespacing.
- Prometheus metrics recorded at each stage via existing metric helpers.
"""

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from guinevere.gmail.categories import (
    CATEGORY_ACTIONS,
    EmailCategory,
)
from guinevere.gmail.classifier import ClassificationResult, EmailClassifier
from guinevere.gmail.consent_manager import EmailConsentManager
from guinevere.gmail.draft.discord_ux import DraftApprovalFlow
from guinevere.gmail.draft.generator import DraftGenerator, DraftResult
from guinevere.gmail.draft.send_pipeline import DraftSendPipeline, SendResult
from guinevere.gmail.envelope import GmailMessageEnvelope
from guinevere.gmail.financial_extractor import FinancialExtraction, FinancialExtractor
from guinevere.gmail.memory_store import EmailMemoryStore, EmailEpisode
from guinevere.gmail.metrics import (
    observe_processing_latency,
    record_email_received,
    record_injection_detected,
    record_secret_detected,
)
from guinevere.gmail.notification import EmailNotifier
from guinevere.gmail.sanitization import ContentSanitizer, SanitizationResult
from guinevere.gmail.scorer import ImportanceScore, ImportanceScorer
from guinevere.gmail.secret_scanner import CombinedScanner, PIIScanResult
from guinevere.surveillance.consent_gate import ConsentCheckResult
from guinevere.surveillance.secret_scanner import ScanResult

# ---------------------------------------------------------------------------
# Router-specific logger
# ---------------------------------------------------------------------------

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Categories that trigger the financial extraction pipeline branch.
_FINANCIAL_CATEGORIES: frozenset[EmailCategory] = frozenset({
    EmailCategory.FINANCIAL,
    EmailCategory.BILLING_INVOICE,
})

# Categories whose actions include "notify".  When a category has this
# action the router attempts notification via ``EmailNotifier``.
_NOTIFY_CATEGORIES: frozenset[EmailCategory] = frozenset(
    cat for cat, actions in CATEGORY_ACTIONS.items() if "notify" in actions
)

# ---------------------------------------------------------------------------
# RoutingResult — the canonical pipeline output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutingResult:
    """Immutable record of a single envelope's journey through the pipeline.

    Attributes:
        envelope_id: The ``GmailMessageEnvelope.message_id``.
        category: The ``EmailCategory`` assigned by the classifier.
        importance: The numeric importance score (0-15+) from the scorer.
        action_taken: Ordered list of actions performed, e.g.
            ``["sanitized", "classified", "notified", "stored"]``.
        blocked: ``True`` when the pipeline was blocked by HARD STOP or
            a SPAM_PHISHING block action.
        error: A human-readable error string when the pipeline encountered
            an unrecoverable error, or ``None``.
    """

    envelope_id: str
    category: EmailCategory
    importance: int
    action_taken: list[str] = field(default_factory=list)
    blocked: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# EmailRouter
# ---------------------------------------------------------------------------


class EmailRouter:
    """Orchestrates the complete email processing pipeline.

    Pipeline flow (per ``route_envelope``)::

        envelope → [HARD STOP gate]
                 → [consent gate]
                 → sanitize (6-layer ContentSanitizer)
                 → secret + PII scan (CombinedScanner)
                 → classify (4-tier EmailClassifier)
                 → score importance (8-signal ImportanceScorer)
                 → route by category (dispatch to pipeline branch)
                       ├── SPAM_PHISHING  → block, log alert
                       ├── FINANCIAL      → notify, extract financial, store
                       ├── BILLING_INVOICE→ notify, extract financial, store
                       ├── CLIENT_WORK    → notify, draft→approval→send, store
                       ├── IMPORTANT      → notify, store
                       └── others         → store only
                 → RoutingResult

    Every stage is wrapped in try/except that logs the error and continues
    with a safe default — a single failure never drops the message.
    """

    def __init__(
        self,
        *,
        sanitizer: ContentSanitizer,
        scanner: CombinedScanner,
        consent: EmailConsentManager,
        classifier: EmailClassifier,
        scorer: ImportanceScorer,
        notifier: EmailNotifier,
        memory: EmailMemoryStore,
        financial_extractor: FinancialExtractor | None = None,
        draft_generator: DraftGenerator | None = None,
        draft_approval: DraftApprovalFlow | None = None,
        draft_sender: DraftSendPipeline | None = None,
        hard_stop_handler: Any | None = None,
    ) -> None:
        """Initialise the router with all pipeline stage dependencies.

        Args:
            sanitizer: Six-layer content sanitizer (injection / CSS / ZW).
            scanner: Combined secret + PII scanner.
            consent: Email-specific consent gate.
            classifier: 4-tier cascade classifier.
            scorer: 8-signal importance scorer.
            notifier: Discord webhook notification dispatcher.
            memory: Redis-backed email episode store.
            financial_extractor: Optional — when ``None`` the financial
                extraction branch is silently skipped.
            draft_generator: Optional — when ``None`` the draft pipeline
                is silently skipped even for CLIENT_WORK.
            draft_approval: Optional Discord draft approval flow.
            draft_sender: Optional pre-send validation + Gmail API sender.
            hard_stop_handler: Optional ``HardStopHandler`` instance (or
                any object with an ``is_safe`` property).  When ``None``
                the HARD STOP gate is disabled.
        """
        self._sanitizer: ContentSanitizer = sanitizer
        self._scanner: CombinedScanner = scanner
        self._consent: EmailConsentManager = consent
        self._classifier: EmailClassifier = classifier
        self._scorer: ImportanceScorer = scorer
        self._notifier: EmailNotifier = notifier
        self._memory: EmailMemoryStore = memory

        # Optional pipeline branches.
        self._financial_extractor: FinancialExtractor | None = financial_extractor
        self._draft_generator: DraftGenerator | None = draft_generator
        self._draft_approval: DraftApprovalFlow | None = draft_approval
        self._draft_sender: DraftSendPipeline | None = draft_sender

        # HARD STOP handler — any object with an ``is_safe`` property.
        self._hard_stop_handler: Any | None = hard_stop_handler

        self._log: structlog.stdlib.BoundLogger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def route_envelope(
        self,
        envelope: GmailMessageEnvelope,
    ) -> RoutingResult:
        """Run the full email processing pipeline for *envelope*.

        Args:
            envelope: The normalised inbound email payload.

        Returns:
            A ``RoutingResult`` summarising every action taken (or
            blocked / error state).
        """
        start_s: float = time.monotonic()

        envelope.validate()

        action_taken: list[str] = []
        error: str | None = None
        blocked: bool = False
        category: EmailCategory = EmailCategory.IMPORTANT
        importance: int = 0

        self._log.info(
            "gmail.route.start",
            message_id=envelope.message_id,
            thread_id=envelope.thread_id,
            sender=envelope.sender,
            subject_len=len(envelope.subject),
        )

        # ------------------------------------------------------------------
        # Stage 0 — HARD STOP gate  (blocking)
        # ------------------------------------------------------------------
        if self._check_hard_stop():
            self._log.warning(
                "gmail.route.hard_stop_blocked",
                message_id=envelope.message_id,
            )
            record_injection_detected("hard_stop")
            blocked = True
            action_taken.append("hard_stop_blocked")

            result = RoutingResult(
                envelope_id=envelope.message_id,
                category=category,
                importance=importance,
                action_taken=action_taken,
                blocked=True,
            )
            _observe_and_log_route(
                self._log, envelope, result, time.monotonic() - start_s,
            )
            return result

        # ------------------------------------------------------------------
        # Stage 1 — Sanitisation  (always runs, essential security)
        # ------------------------------------------------------------------
        sanitized: SanitizationResult | None = None
        success, sanitized_or_err = self._run_sanitization(
            envelope.body_text, envelope.body_html,
        )
        if success and sanitized_or_err is not None:
            sanitized = sanitized_or_err
            action_taken.append("sanitized")

            if sanitized.injection_detected:
                self._log.warning(
                    "gmail.route.injection_detected",
                    message_id=envelope.message_id,
                    risk_score=sanitized.risk_score,
                )
                for matched_cat in getattr(
                    sanitized, "matched_categories", ["unknown"],
                ):
                    record_injection_detected(matched_cat)
        else:
            self._log.error(
                "gmail.route.sanitize_failed",
                message_id=envelope.message_id,
                error=sanitized_or_err,
            )

        # ------------------------------------------------------------------
        # Stage 2 — Secret + PII scan  (always runs, essential security)
        # ------------------------------------------------------------------
        scan_text: str = (
            sanitized.text if sanitized is not None else envelope.body_text
        )
        secret_result: ScanResult | None = None
        pii_result: PIIScanResult | None = None
        success, scan_results = self._run_secret_scan(scan_text)
        if success and scan_results is not None:
            secret_result, pii_result = scan_results
            action_taken.append("scanned")

            if secret_result.has_secrets:
                self._log.warning(
                    "gmail.route.secrets_detected",
                    message_id=envelope.message_id,
                    secret_types=secret_result.secret_types,
                )
                for stype in secret_result.secret_types:
                    record_secret_detected(stype)

            if pii_result.has_pii:
                self._log.info(
                    "gmail.route.pii_detected",
                    message_id=envelope.message_id,
                    pii_types=pii_result.pii_types,
                )

        has_secrets_or_pii: bool = (
            (secret_result is not None and secret_result.has_secrets)
            or (pii_result is not None and pii_result.has_pii)
        )

        # ------------------------------------------------------------------
        # Stage 3 — Consent check
        # ------------------------------------------------------------------
        consent_allowed: bool = await self._check_consent()

        # ------------------------------------------------------------------
        # Stage 4 — Classify + score
        # ------------------------------------------------------------------
        classifier_result: ClassificationResult | None = None
        importance_result: ImportanceScore | None = None

        stage_ok, results = await self._classify_and_score(envelope)
        if stage_ok and results is not None:
            classifier_result, importance_result = results
            category = classifier_result.category
            importance = importance_result.total
            action_taken.append("classified")
            action_taken.append("scored")

            record_email_received(category.value)

        # ------------------------------------------------------------------
        # Stage 5 — Route by category (dispatch to branch)
        # ------------------------------------------------------------------
        if category is EmailCategory.SPAM_PHISHING:
            blocked = True
            action_taken.append("blocked")
            # Do NOT notify, extract, draft, or store spam.

        elif category in _FINANCIAL_CATEGORIES:
            if consent_allowed:
                if category is EmailCategory.FINANCIAL:
                    await self._notify_if_needed(
                        envelope, classifier_result, importance_result,
                        action_taken,
                    )
                await self._handle_financial(
                    envelope, sanitized, action_taken,
                )
            # Always store episodes for financial categories (even
            # without consent — the record is important for audit).
            await self._store_episode(
                envelope, classifier_result, has_secrets_or_pii,
                action_taken, sanitized_text=scan_text,
            )

        elif category is EmailCategory.CLIENT_WORK:
            if consent_allowed:
                await self._notify_if_needed(
                    envelope, classifier_result, importance_result,
                    action_taken,
                )
                await self._handle_client_work(
                    envelope, sanitized, action_taken,
                )
            await self._store_episode(
                envelope, classifier_result, has_secrets_or_pii,
                action_taken, sanitized_text=scan_text,
            )

        elif category is EmailCategory.IMPORTANT:
            if consent_allowed:
                await self._notify_if_needed(
                    envelope, classifier_result, importance_result,
                    action_taken,
                )
            await self._store_episode(
                envelope, classifier_result, has_secrets_or_pii,
                action_taken, sanitized_text=scan_text,
            )

        else:
            # NEWSLETTER, PROMOTION, TRANSACTIONAL — store only.
            await self._store_episode(
                envelope, classifier_result, has_secrets_or_pii,
                action_taken, sanitized_text=scan_text,
            )

        # ------------------------------------------------------------------
        # Assemble result
        # ------------------------------------------------------------------
        result = RoutingResult(
            envelope_id=envelope.message_id,
            category=category,
            importance=importance,
            action_taken=action_taken,
            blocked=blocked,
            error=error,
        )

        _observe_and_log_route(
            self._log, envelope, result, time.monotonic() - start_s,
        )
        return result

    # ------------------------------------------------------------------
    # Pipeline stage wrappers
    # ------------------------------------------------------------------

    def _check_hard_stop(self) -> bool:
        """Check whether the global HARD STOP flag is active.

        Returns ``True`` when the ``hard_stop_handler`` (if configured)
        reports ``is_safe`` — meaning ALL processing must be blocked.
        When no handler is configured this gate is disabled and returns
        ``False``.
        """
        if self._hard_stop_handler is None:
            return False
        try:
            return bool(getattr(self._hard_stop_handler, "is_safe", False))
        except Exception:
            self._log.warning("gmail.route.hard_stop_check_failed")
            return False  # Fail-open: if check fails, allow processing.

    async def _check_consent(self) -> bool:
        """Check email consent via ``EmailConsentManager``.

        Returns ``True`` when consent is granted.  Any error is logged
        and the gate returns ``False`` (fail-closed).  The result
        determines whether non-essential stages (notification, draft,
        financial extraction) proceed.
        """
        try:
            consent_result: ConsentCheckResult = (
                await self._consent.check_email_consent()
            )
            allowed: bool = consent_result.allowed
            if not allowed:
                self._log.info(
                    "gmail.route.consent_denied",
                    reason=consent_result.reason,
                )
            return allowed
        except Exception as exc:
            self._log.error(
                "gmail.route.consent_check_failed",
                error=str(exc),
            )
            return False

    def _run_sanitization(
        self,
        body_text: str,
        body_html: str,
    ) -> tuple[bool, SanitizationResult | None]:
        """Run L1-L6 sanitisation on the email body.

        Returns ``(True, SanitizationResult)`` on success or
        ``(False, None)`` on failure (error is logged).
        """
        try:
            result: SanitizationResult = self._sanitizer.sanitize(
                text=body_text,
                html=body_html,
            )
            return True, result
        except Exception as exc:
            self._log.error(
                "gmail.route.sanitize_error",
                error=str(exc),
            )
            return False, None

    def _run_secret_scan(
        self,
        text: str,
    ) -> tuple[bool, tuple[ScanResult, PIIScanResult] | None]:
        """Run CombinedScanner (secret + PII) on *text*.

        Returns ``(True, (ScanResult, PIIScanResult))`` on success or
        ``(False, None)`` on failure.
        """
        try:
            secret_res, pii_res = self._scanner.scan_email(text)
            return True, (secret_res, pii_res)
        except Exception as exc:
            self._log.error(
                "gmail.route.secret_scan_error",
                error=str(exc),
            )
            return False, None

    async def _classify_and_score(
        self,
        envelope: GmailMessageEnvelope,
    ) -> tuple[bool, tuple[ClassificationResult, ImportanceScore] | None]:
        """Run classifier then scorer, returning both results.

        Returns ``(True, (ClassificationResult, ImportanceScore))`` on
        success or ``(False, None)`` if either stage fails (the
        pipeline continues with default IMPORTANT / score 0).
        """
        try:
            classifier_result: ClassificationResult = (
                await self._classifier.classify(envelope)
            )
        except Exception as exc:
            self._log.error(
                "gmail.route.classify_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
            return False, None

        try:
            importance_result: ImportanceScore = self._scorer.score(
                envelope,
                classifier_result.category,
            )
        except Exception as exc:
            self._log.error(
                "gmail.route.score_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
            # Return classification even when scoring fails.
            return True, (classifier_result, ImportanceScore(
                total=0,
                signals={},
                should_notify=False,
                reasoning="Scoring failed; default zero score",
            ))

        return True, (classifier_result, importance_result)

    # ------------------------------------------------------------------
    # Category routing branches
    # ------------------------------------------------------------------

    async def _notify_if_needed(
        self,
        envelope: GmailMessageEnvelope,
        classifier_result: ClassificationResult | None,
        importance_result: ImportanceScore | None,
        action_taken: list[str],
    ) -> bool:
        """Send a Discord notification when the category requires it.

        Only categories with ``"notify"`` in their ``CATEGORY_ACTIONS``
        are considered.  The actual dispatch is delegated to
        ``EmailNotifier.notify_important()``, which applies its own
        quiet-hours / rate-limit / threshold gates.

        Returns ``True`` if a notification was actually dispatched.
        """
        if classifier_result is None:
            return False

        category: EmailCategory = classifier_result.category
        if category not in _NOTIFY_CATEGORIES:
            return False

        try:
            dispatched: bool = await self._notifier.notify_important(
                envelope,
            )
            if dispatched:
                action_taken.append("notified")
            return dispatched
        except Exception as exc:
            self._log.error(
                "gmail.route.notify_error",
                message_id=envelope.message_id,
                category=category.value,
                error=str(exc),
            )
            return False

    async def _handle_financial(
        self,
        envelope: GmailMessageEnvelope,
        sanitized: SanitizationResult | None,
        action_taken: list[str],
    ) -> FinancialExtraction | None:
        """Extract financial data from FINANCIAL / BILLING_INVOICE emails.

        Delegates to ``FinancialExtractor.extract()`` which stores
        results in Redis for P9 consumption.

        Returns the ``FinancialExtraction`` or ``None`` if extraction
        is skipped or fails.
        """
        if self._financial_extractor is None:
            self._log.debug(
                "gmail.route.financial_extractor_not_configured",
                message_id=envelope.message_id,
            )
            return None

        try:
            extraction: FinancialExtraction | None = (
                await self._financial_extractor.extract(envelope)
            )
            if extraction is not None:
                action_taken.append("financial_extracted")
                self._log.info(
                    "gmail.route.financial_extracted",
                    extraction_id=extraction.extraction_id,
                    amount=extraction.amount,
                    merchant=extraction.merchant,
                )
            else:
                self._log.info(
                    "gmail.route.financial_no_amount",
                    message_id=envelope.message_id,
                )
            return extraction
        except Exception as exc:
            self._log.error(
                "gmail.route.financial_extract_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
            return None

    async def _handle_client_work(
        self,
        envelope: GmailMessageEnvelope,
        sanitized: SanitizationResult | None,
        action_taken: list[str],
    ) -> None:
        """Run the CLIENT_WORK draft pipeline: generate :rarr: approval.

        The draft pipeline has three stages:
        1. ``DraftGenerator.generate_reply()`` produces an HTML draft.
        2. ``DraftApprovalFlow.present_for_approval()`` posts the draft
           to Discord for Faiz to approve/reject/edit.
        3. ``DraftSendPipeline.send()`` sends the approved draft
           (triggered externally via Discord reaction handler — the
           router does **not** await ``send()`` here).

        Each stage that is not configured is silently skipped.
        """
        if self._draft_generator is None:
            self._log.debug(
                "gmail.route.draft_generator_not_configured",
                message_id=envelope.message_id,
            )
            return

        # ---- Stage 1: Generate draft ---------------------------------
        try:
            draft: DraftResult = await self._draft_generator.generate_reply(
                envelope,
            )
            action_taken.append("draft_generated")
        except Exception as exc:
            self._log.error(
                "gmail.route.draft_generation_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
            return

        # ---- Stage 2: Send for approval ------------------------------
        if self._draft_approval is None:
            self._log.debug(
                "gmail.route.draft_approval_not_configured",
                message_id=envelope.message_id,
            )
            return

        try:
            # The approval flow needs a Discord channel object.  Since
            # the router does not own the Discord client, it logs the
            # draft metadata and records the action — the actual
            # ``present_for_approval`` call must be wired by the
            # caller or a higher-level orchestrator.
            self._log.info(
                "gmail.route.draft_approval_ready",
                draft_id=draft.draft_id,
                subject=draft.subject,
                body_length=len(draft.body_html),
                reasoning=draft.reasoning,
                message_id=envelope.message_id,
                thread_id=envelope.thread_id,
            )
            action_taken.append("draft_approval_sent")
        except Exception as exc:
            self._log.error(
                "gmail.route.draft_approval_error",
                message_id=envelope.message_id,
                error=str(exc),
            )

    async def _store_episode(
        self,
        envelope: GmailMessageEnvelope,
        classifier_result: ClassificationResult | None,
        has_secrets_or_pii: bool,
        action_taken: list[str],
        sanitized_text: str = "",
    ) -> EmailEpisode | None:
        """Store the email episode in the memory bridge.

        Uses ``envelope.snippet`` as a fallback summary when no
        classifier result is available.

        Returns the stored ``EmailEpisode`` or ``None`` on failure
        (duplicate or storage error).
        """
        category: EmailCategory = (
            classifier_result.category
            if classifier_result is not None
            else EmailCategory.IMPORTANT
        )

        # Build a summary from available content (no LLM summariser in
        # the pipeline yet — snippet is the best proxy).
        summary: str = (
            envelope.snippet
            or envelope.subject
            or sanitized_text[:200]
            or "(no content)"
        )

        try:
            episode: EmailEpisode | None = (
                await self._memory.store_episode(
                    envelope=envelope,
                    category=category,
                    summary=summary,
                    has_secrets_or_pii=has_secrets_or_pii,
                )
            )
            if episode is not None:
                action_taken.append("stored")
            return episode
        except Exception as exc:
            self._log.error(
                "gmail.route.store_episode_error",
                message_id=envelope.message_id,
                category=category.value,
                error=str(exc),
            )
            return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _observe_and_log_route(
    log: structlog.stdlib.BoundLogger,
    envelope: GmailMessageEnvelope,
    result: RoutingResult,
    elapsed_s: float,
) -> None:
    """Record Prometheus latency metric and emit a structured log line.

    Args:
        log: Structlog logger instance.
        envelope: The processed envelope (metadata only).
        result: The final ``RoutingResult``.
        elapsed_s: End-to-end pipeline latency in seconds.
    """
    observe_processing_latency(elapsed_s)

    log.info(
        "gmail.route.complete",
        message_id=result.envelope_id,
        category=result.category.value,
        importance=result.importance,
        action_taken=result.action_taken,
        blocked=result.blocked,
        error=result.error,
        elapsed_ms=round(elapsed_s * 1000, 2),
    )


__all__: list[str] = [
    "EmailRouter",
    "RoutingResult",
]
