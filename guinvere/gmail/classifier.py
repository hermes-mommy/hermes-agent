from __future__ import annotations

"""4-tier cascade email classifier for P12 Gmail Integration.

Implements a deterministic → embedding → LLM → fallback cascade that
classifies every inbound email into one of eight ``EmailCategory``
values with a confidence score and the tier that produced the result.

Cascade flow::

    Tier 1 (rule-based heuristics)   ~78% coverage,  O(μs)
        ↓ no match
    Tier 2 (embedding similarity)    ~85-90% coverage, O(ms)
        ↓ no match
    Tier 3 (LLM classification)      ~95%+ coverage,   O(100ms)
        ↓ no match
    Tier 4 (fallback)                100% coverage     O(1)
"""

import json
import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar

import structlog

from .categories import EmailCategory, EmailPriority, CATEGORY_PRIORITY
from .config import GmailSettings, get_gmail_settings
from .envelope import GmailMessageEnvelope
from .exceptions import GmailError
from .metrics import record_email_classified

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Public result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationResult:
    """Immutable result of a cascade classification pass.

    Attributes:
        category: The predicted ``EmailCategory``.
        confidence: Floating-point score in ``[0, 1]``.
        tier: Which cascade tier produced the result (1-4).
        reasoning: Human-readable explanation for the classification.
    """

    category: EmailCategory
    confidence: float
    tier: int
    reasoning: str


# ---------------------------------------------------------------------------
# Tier 3 — LLM prompt template
# ---------------------------------------------------------------------------

LLM_CLASSIFICATION_PROMPT: str = """You are an email classifier for {operator_name}. Classify the following email into exactly one of the eight categories below. Respond with a JSON object containing "category" and "confidence" (0.0-1.0).

Categories:
- CLIENT_WORK: Work-related email from a client, colleague, or business partner.
- FINANCIAL: Banking, payment, or financial transaction notification (e.g. transfer confirmation, balance alert, top-up).
- BILLING_INVOICE: Invoice, receipt, or payment due notification.
- IMPORTANT: Human-authored email requiring attention that doesn't fit other categories (personal, direct reply, high-signal).
- NEWSLETTER: Mass-sent newsletter, mailing list, or subscription-based updates.
- PROMOTION: Marketing, promotional offer, discount, or advertising email.
- TRANSACTIONAL: System-generated messages (OTP, verification code, password reset, order confirmation, welcome email).
- SPAM_PHISHING: Unsolicited bulk email, phishing attempt, or suspicious content.

Sender: {sender}
Subject: {subject}
Body (first {body_truncation_chars} chars): {body_text}

Respond ONLY with a valid JSON object: {{"category": "<CATEGORY>", "confidence": <0.0-1.0>, "reasoning": "<brief reason>"}}"""


# ---------------------------------------------------------------------------
# Email classifier
# ---------------------------------------------------------------------------


class EmailClassifier:
    """4-tier cascade classifier for inbound Gmail messages.

    Usage::

        classifier = EmailClassifier(settings)
        result = await classifier.classify(envelope)
        print(result.category, result.confidence, result.tier)
    """

    # -- Tier 1 rule constants -----------------------------------------------

    # Known spam / phishing sender domains (lowercase, no leading @).
    SPAM_DOMAINS: ClassVar[tuple[str, ...]] = (
        "mailer-daemon",
        "noreply-spam",
        "spamtrap",
        "mailer@spam",
    )

    SPAM_PHRASES: ClassVar[tuple[str, ...]] = (
        "verify your account",
        "account suspended",
        "account will be closed",
        "click here immediately",
        "unusual activity",
        "security alert",
        "confirm your identity",
        "you won a prize",
        "congratulations you are a winner",
        "claim your reward",
        "act now to avoid",
        "update your payment",
        "restore your account",
        "blocked due to suspicious",
        "emergency action required",
    )

    # Indonesian bank / payment domains and identifiers.
    FINANCIAL_DOMAINS: ClassVar[tuple[str, ...]] = (
        "bca.co.id",
        "mandiri.co.id",
        "bni.co.id",
        "bri.co.id",
        "cimbniaga.co.id",
        "danamon.co.id",
        "maybank.co.id",
        "permata.co.id",
        "ocbc.id",
        "jenius.com",
        "blu.com",
        "digibank.id",
    )

    FINANCIAL_SENDERS: ClassVar[tuple[str, ...]] = (
        "gopay",
        "ovo",
        "dana",
        "shopeepay",
        "linkaja",
        "qris",
    )

    FINANCIAL_AMOUNT_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"""
        (?:^|\s|[,;:])
        (?:
            Rp\s?\d{1,3}(?:\.?\d{3})*(?:,\d{2})?    # Rp 50.000 or Rp50000
            |
            IDR\s?\d{1,3}(?:\.?\d{3})*(?:,\d{2})?    # IDR 50.000
            |
            \d{1,3}(?:\.?\d{3})*\s?(?:USD|SGD|MYR)   # 50.000 USD
        )
        (?:$|\s|[.,!?])
        """,
        re.IGNORECASE | re.VERBOSE | re.UNICODE,
    )

    # Billing / invoice keywords.
    BILLING_KEYWORDS: ClassVar[tuple[str, ...]] = (
        "invoice",
        "receipt",
        "payment confirmation",
        "payment received",
        "payment due",
        "tagihan",
        "bill",
        "statement",
        "credit note",
        "debit note",
        "tax invoice",
        "faktur",
        "kwitansi",
        "due date",
        "total due",
        "amount due",
    )

    # Newsletter indicators.
    NEWSLETTER_BODY_PATTERNS: ClassVar[tuple[str, ...]] = (
        "unsubscribe",
        "click here to unsubscribe",
        "manage your preferences",
        "you are receiving this email because",
        "email was sent to",
        "to stop receiving",
        "if you do not wish to receive",
        "no longer want to receive",
    )

    NEWSLETTER_SUBJECT_PATTERNS: ClassVar[tuple[str, ...]] = (
        "newsletter",
        "weekly digest",
        "monthly update",
        "this week in",
        "your daily",
    )

    # Promotion / marketing keywords.
    PROMOTION_KEYWORDS: ClassVar[tuple[str, ...]] = (
        "promo",
        "diskon",
        "discount",
        "sale",
        "limited time",
        "limited offer",
        "buy now",
        "shop now",
        "flash sale",
        "hari ini saja",
        "buruan",
        "gratis ongkir",
        "free shipping",
        "special offer",
        "exclusive deal",
        "best price",
        "cashback",
        "extra",
        "voucher",
    )

    # Transactional / system-generated keywords.
    TRANSACTIONAL_KEYWORDS: ClassVar[tuple[str, ...]] = (
        "otp",
        "one-time password",
        "kode verifikasi",
        "verification code",
        "password reset",
        "reset password",
        "order confirmation",
        "order confirmed",
        "pembelian",
        "transaction",
        "transaksi",
        "welcome",
        "selamat datang",
        "account created",
        "pendaftaran berhasil",
        "pin changed",
        "login alert",
    )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        settings: GmailSettings | None = None,
        bridge: Any = None,
    ) -> None:
        """Initialise the classifier with optional explicit settings.

        Args:
            settings: A ``GmailSettings`` instance.  When ``None``, the
                module-level singleton is loaded via ``get_gmail_settings``.
            bridge: Optional ``GmailHermesBridge`` instance for Tier 3 LLM
                classification.  When ``None``, Tier 3 is skipped.
        """
        self._settings: GmailSettings = (
            settings if settings is not None else get_gmail_settings()
        )
        self._log: structlog.stdlib.BoundLogger = logger
        self._bridge: Any = bridge

        # Pre-process sender whitelist for fast lookup.
        self._whitelist_domains: set[str] = {
            _extract_domain(s) for s in self._settings.sender_whitelist
        }
        self._whitelist_emails: set[str] = {
            s.lower().strip()
            for s in self._settings.sender_whitelist
        }

        self._log.info(
            "classifier_initialized",
            whitelist_count=len(self._whitelist_emails),
            confidence_threshold=self._settings
            .classification_confidence_threshold,
            bridge_available=self._bridge is not None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def classify(
        self,
        envelope: GmailMessageEnvelope,
    ) -> ClassificationResult:
        """Run the 4-tier cascade and return a ``ClassificationResult``.

        Args:
            envelope: Normalised inbound email payload.

        Returns:
            A frozen ``ClassificationResult`` with the predicted category,
            confidence score, winning tier, and reasoning text.

        Raises:
            GmailError: When classification encounters an unrecoverable
                error (e.g. unexpected internal state).
        """
        start_s: float = time.perf_counter()

        try:
            # -- Tier 1: rule-based heuristics ----------------------------------
            tier1_result: ClassificationResult | None = self._tier1_rules(
                envelope,
            )
            if tier1_result is not None:
                _log_and_record(
                    self._log,
                    tier1_result,
                    envelope,
                    time.perf_counter() - start_s,
                )
                return tier1_result

            # -- Tier 2: embedding similarity ------------------------------------
            tier2_result: ClassificationResult | None = self._tier2_embedding(
                envelope,
            )
            if tier2_result is not None:
                _log_and_record(
                    self._log,
                    tier2_result,
                    envelope,
                    time.perf_counter() - start_s,
                )
                return tier2_result

            # -- Tier 3: LLM classification -------------------------------------
            tier3_result: ClassificationResult | None = await self._tier3_llm(
                envelope,
            )
            if tier3_result is not None:
                _log_and_record(
                    self._log,
                    tier3_result,
                    envelope,
                    time.perf_counter() - start_s,
                )
                return tier3_result

            # -- Tier 4: fallback ------------------------------------------------
            fallback: ClassificationResult = self._tier4_fallback(envelope)
            _log_and_record(
                self._log,
                fallback,
                envelope,
                time.perf_counter() - start_s,
            )
            return fallback

        except GmailError:
            raise
        except Exception as exc:
            self._log.error(
                "classifier_internal_error",
                error=str(exc),
                message_id=envelope.message_id,
            )
            raise GmailError(f"Classification failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Tier 1 — Rule-based heuristics  (~78% coverage)
    # ------------------------------------------------------------------

    def _tier1_rules(
        self,
        envelope: GmailMessageEnvelope,
    ) -> ClassificationResult | None:
        """Apply deterministic rule-based classification.

        Rules are evaluated in priority order so that the most specific
        (and safety-critical) patterns are checked first.

        Returns:
            A ``ClassificationResult`` when a rule matches, or ``None``
            to signal that the cascade should continue to Tier 2.
        """
        sender_lower: str = envelope.sender.lower().strip()
        sender_domain: str = _extract_domain(sender_lower)
        subject_lower: str = envelope.subject.lower()
        body_lower: str = envelope.body_text.lower()
        labels_lower_list: list[str] = [
            lbl.lower() for lbl in envelope.labels
        ]

        # --- SPAM_PHISHING checks (highest priority) -----------------------
        # Known spam domains in sender address.
        if any(spam_domain in sender_lower for spam_domain in self.SPAM_DOMAINS):
            return ClassificationResult(
                category=EmailCategory.SPAM_PHISHING,
                confidence=0.85,
                tier=1,
                reasoning=f"Spam domain detected in sender: {sender_lower}",
            )

        # Phishing keywords in body.
        matched_spam: str | None = _first_match(
            self.SPAM_PHRASES,
            body_lower,
        )
        if matched_spam is not None:
            return ClassificationResult(
                category=EmailCategory.SPAM_PHISHING,
                confidence=0.85,
                tier=1,
                reasoning=f"Spam/phishing phrase found in body: {matched_spam}",
            )

        # --- CLIENT_WORK from sender whitelist -----------------------------
        if self._is_whitelisted(sender_lower, sender_domain):
            return ClassificationResult(
                category=EmailCategory.CLIENT_WORK,
                confidence=0.85,
                tier=1,
                reasoning=f"Sender is whitelisted: {sender_lower}",
            )

        # --- FINANCIAL checks ----------------------------------------------
        # Bank/payment domain in sender.
        if any(
            fin_domain in sender_lower
            for fin_domain in self.FINANCIAL_DOMAINS
        ):
            return ClassificationResult(
                category=EmailCategory.FINANCIAL,
                confidence=0.85,
                tier=1,
                reasoning=f"Financial domain detected: {sender_domain}",
            )

        # Known payment sender name.
        matched_fin_sender: str | None = _first_match(
            self.FINANCIAL_SENDERS,
            sender_lower,
        )
        if matched_fin_sender is not None:
            return ClassificationResult(
                category=EmailCategory.FINANCIAL,
                confidence=0.85,
                tier=1,
                reasoning=f"Payment provider detected: {matched_fin_sender}",
            )

        # Amount/curency pattern in subject or body.
        if self.FINANCIAL_AMOUNT_PATTERN.search(subject_lower) or (
            self.FINANCIAL_AMOUNT_PATTERN.search(body_lower)
        ):
            return ClassificationResult(
                category=EmailCategory.FINANCIAL,
                confidence=0.85,
                tier=1,
                reasoning="Currency/amount pattern detected in content",
            )

        # --- BILLING_INVOICE checks ----------------------------------------
        matched_billing: str | None = _first_match(
            self.BILLING_KEYWORDS,
            subject_lower,
        )
        if matched_billing is not None:
            return ClassificationResult(
                category=EmailCategory.BILLING_INVOICE,
                confidence=0.85,
                tier=1,
                reasoning=f"Billing keyword in subject: {matched_billing}",
            )

        matched_billing_body: str | None = _first_match(
            self.BILLING_KEYWORDS,
            body_lower,
        )
        if matched_billing_body is not None:
            return ClassificationResult(
                category=EmailCategory.BILLING_INVOICE,
                confidence=0.85,
                tier=1,
                reasoning=f"Billing keyword in body: {matched_billing_body}",
            )

        # --- TRANSACTIONAL checks ------------------------------------------
        matched_txn_subj: str | None = _first_match(
            self.TRANSACTIONAL_KEYWORDS,
            subject_lower,
        )
        if matched_txn_subj is not None:
            return ClassificationResult(
                category=EmailCategory.TRANSACTIONAL,
                confidence=0.85,
                tier=1,
                reasoning=f"Transactional keyword in subject: {matched_txn_subj}",
            )

        matched_txn_body: str | None = _first_match(
            self.TRANSACTIONAL_KEYWORDS,
            body_lower,
        )
        if matched_txn_body is not None:
            return ClassificationResult(
                category=EmailCategory.TRANSACTIONAL,
                confidence=0.85,
                tier=1,
                reasoning=f"Transactional keyword in body: {matched_txn_body}",
            )

        # --- NEWSLETTER checks ---------------------------------------------
        # Check for list-unsubscribe-like patterns in body.
        if _has_newsletter_indicators(
            body_lower,
            self.NEWSLETTER_BODY_PATTERNS,
        ):
            return ClassificationResult(
                category=EmailCategory.NEWSLETTER,
                confidence=0.85,
                tier=1,
                reasoning="Unsubscribe/mailing-list pattern found in body",
            )

        matched_news_subj: str | None = _first_match(
            self.NEWSLETTER_SUBJECT_PATTERNS,
            subject_lower,
        )
        if matched_news_subj is not None:
            return ClassificationResult(
                category=EmailCategory.NEWSLETTER,
                confidence=0.85,
                tier=1,
                reasoning=f"Newsletter pattern in subject: {matched_news_subj}",
            )

        # Gmail category label.
        if _label_matches(labels_lower_list, ("newsletter", "forum")):
            return ClassificationResult(
                category=EmailCategory.NEWSLETTER,
                confidence=0.85,
                tier=1,
                reasoning="Gmail label indicates newsletter/forum",
            )

        # --- PROMOTION checks ----------------------------------------------
        matched_promo: str | None = _first_match(
            self.PROMOTION_KEYWORDS,
            subject_lower,
        )
        if matched_promo is not None:
            return ClassificationResult(
                category=EmailCategory.PROMOTION,
                confidence=0.85,
                tier=1,
                reasoning=f"Promotion keyword in subject: {matched_promo}",
            )

        if _label_matches(labels_lower_list, ("promotion", "promo")):
            return ClassificationResult(
                category=EmailCategory.PROMOTION,
                confidence=0.85,
                tier=1,
                reasoning="Gmail label indicates promotion",
            )

        # No Tier-1 rule matched.
        return None

    # ------------------------------------------------------------------
    # Tier 2 — Embedding similarity  (~85-90% coverage)
    # ------------------------------------------------------------------

    def _tier2_embedding(
        self,
        _envelope: GmailMessageEnvelope,
    ) -> ClassificationResult | None:
        """Classify via cosine similarity against category exemplars.

        .. todo::

            Wire ``sentence-transformers`` model and pre-computed
            category embedding centroids.  The current implementation
            is a placeholder that always returns ``None`` so the
            cascade falls through to Tier 3.
        """
        # TODO: Implement embedding-based classification.
        # Steps once wired:
        #   1. Load SentenceTransformer model (configured via settings).
        #   2. Encode envelope subject + body_text into a query vector.
        #   3. Compute cosine similarity against pre-computed centroids
        #      for each EmailCategory (built offline from labelled data).
        #   4. If max similarity >= confidence_threshold, return that
        #      category with the similarity as confidence.
        #   5. Otherwise return None to cascade.
        return None

    # ------------------------------------------------------------------
    # Tier 3 — LLM classification  (~95%+ coverage)
    # ------------------------------------------------------------------

    async def _tier3_llm(
        self,
        envelope: GmailMessageEnvelope,
    ) -> ClassificationResult | None:
        """Classify via Hermes (bridge) LLM.

        Calls ``bridge.invoke_for_classification()`` which sends a
        structured prompt to Hermes Agent and returns a parsed JSON
        dict with ``category`` and ``confidence`` keys.

        Returns ``None`` when Hermes is unavailable or the response
        cannot be parsed, allowing the cascade to fall through to
        Tier 4.
        """
        if self._bridge is None:
            self._log.debug("classifier_tier3_skipped_no_bridge")
            return None

        try:
            parsed: dict[str, object] | None = (
                await self._bridge.invoke_for_classification(envelope)
            )
        except Exception as exc:
            self._log.warning(
                "classifier_tier3_hermes_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
            return None

        if parsed is None:
            return None

        category_str: str = str(parsed.get("category", ""))
        confidence: float = float(parsed.get("confidence", 0.5))
        reasoning: str = str(parsed.get("reasoning", "LLM classification"))

        # Validate category.
        try:
            category = EmailCategory(category_str)
        except ValueError:
            self._log.warning(
                "classifier_tier3_invalid_category",
                message_id=envelope.message_id,
                received=category_str,
            )
            return None

        # Enforce confidence threshold.
        if confidence < self._settings.classification_confidence_threshold:
            self._log.info(
                "classifier_tier3_below_threshold",
                message_id=envelope.message_id,
                category=category.value,
                confidence=round(confidence, 3),
                threshold=self._settings.classification_confidence_threshold,
            )
            return None

        return ClassificationResult(
            category=category,
            confidence=confidence,
            tier=3,
            reasoning=f"LLM (T3): {reasoning}",
        )

    # ------------------------------------------------------------------
    # Tier 4 — Fallback
    # ------------------------------------------------------------------

    def _tier4_fallback(
        self,
        envelope: GmailMessageEnvelope,
    ) -> ClassificationResult:
        """Default classification when all prior tiers produce no match.

        Returns:
            An ``IMPORTANT`` classification with modest confidence.
        """
        self._log.info(
            "classifier_tier4_fallback",
            message_id=envelope.message_id,
            subject_len=len(envelope.subject),
            sender_domain=_extract_domain(envelope.sender),
        )
        return ClassificationResult(
            category=EmailCategory.IMPORTANT,
            confidence=0.50,
            tier=4,
            reasoning="All cascade tiers returned no match; defaulting to IMPORTANT",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_whitelisted(
        self,
        sender_lower: str,
        sender_domain: str,
    ) -> bool:
        """Check if the sender email or its domain is whitelisted.

        Args:
            sender_lower: Lowercased sender email address.
            sender_domain: Domain portion extracted from the sender.

        Returns:
            ``True`` when the email or domain appears in the
            ``sender_whitelist`` from settings.
        """
        if sender_lower in self._whitelist_emails:
            return True
        if sender_domain in self._whitelist_domains:
            return True
        return False


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _extract_domain(email: str) -> str:
    """Extract the domain portion from an email address.

    Args:
        email: A raw email address (e.g. ``user@example.com``).

    Returns:
        The domain part (e.g. ``example.com``).  If no ``@`` is
        found, the entire string is returned lowercased.
    """
    if "@" in email:
        return email.split("@", 1)[1].lower().strip()
    return email.lower().strip()


def _first_match(
    patterns: tuple[str, ...],
    text: str,
) -> str | None:
    """Return the first pattern found in *text*, or ``None``.

    Args:
        patterns: A tuple of lowercase keyword strings.
        text: Lowercased text to search.

    Returns:
        The first matching pattern, or ``None``.
    """
    for pattern in patterns:
        if pattern in text:
            return pattern
    return None


def _has_newsletter_indicators(
    body_lower: str,
    patterns: tuple[str, ...],
) -> bool:
    """Check for newsletter-unsubscribe indicators in body text.

    Args:
        body_lower: Lowercased email body.
        patterns: Newsletter body indicator patterns.

    Returns:
        ``True`` when at least one indicator is found.
    """
    for pattern in patterns:
        if pattern in body_lower:
            return True
    return False


def _label_matches(
    labels: list[str],
    targets: tuple[str, ...],
) -> bool:
    """Check if any label string contains a target substring.

    Args:
        labels: List of lowercased Gmail label names.
        targets: Target substrings to look for.

    Returns:
        ``True`` when any label contains any target.
    """
    for label in labels:
        for target in targets:
            if target in label:
                return True
    return False


def _log_and_record(
    log: structlog.stdlib.BoundLogger,
    result: ClassificationResult,
    envelope: GmailMessageEnvelope,
    elapsed_s: float,
) -> None:
    """Log the classification result and emit a Prometheus metric.

    Args:
        log: Structlog logger instance.
        result: The ``ClassificationResult`` from the winning tier.
        envelope: The envelope being classified (metadata only).
        elapsed_s: End-to-end classification latency in seconds.
    """
    log.info(
        "classifier_result",
        category=result.category.value,
        confidence=round(result.confidence, 3),
        tier=result.tier,
        message_id=envelope.message_id,
        subject_len=len(envelope.subject),
        sender_domain=_extract_domain(envelope.sender),
        elapsed_s=round(elapsed_s, 6),
    )

    try:
        record_email_classified(result.category.value, result.tier)
    except Exception as exc:
        log.error(
            "classifier_metric_record_failed",
            error=str(exc),
            category=result.category.value,
            tier=result.tier,
        )


__all__: list[str] = [
    "CATEGORY_PRIORITY",
    "ClassificationResult",
    "EmailClassifier",
    "EmailPriority",
    "LLM_CLASSIFICATION_PROMPT",
    # Module helpers are not exported by default — they are internal.
]
