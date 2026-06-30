from __future__ import annotations

"""8-signal importance scorer for Gmail email classification.

Produces a numeric importance score (0–15+) for each inbound email
based on eight distinct signals.  Emails scoring at or above the
configured threshold (default 5) trigger immediate notification.
"""

import re
from dataclasses import dataclass
from typing import Final

import structlog

from guinvere.gmail.categories import EmailCategory
from guinvere.gmail.config import GmailSettings, get_gmail_settings
from guinvere.gmail.envelope import GmailMessageEnvelope

logger = structlog.get_logger(__name__)

# ── Signal weights ─────────────────────────────────────────────────────────

_WEIGHT_GMAIL_IMPORTANT: Final[int] = 3
_WEIGHT_SENDER_WHITELIST: Final[int] = 2
_WEIGHT_THREAD_DEPTH: Final[int] = 1
_WEIGHT_URGENCY_KEYWORDS: Final[int] = 2
_WEIGHT_DIRECT_ADDRESS: Final[int] = 1
_WEIGHT_FINANCIAL_AMOUNT: Final[int] = 3
_WEIGHT_ACTION_KEYWORDS: Final[int] = 2
_WEIGHT_REPLY_RATE: Final[int] = 1

# ── Keyword lists ─────────────────────────────────────────────────────────

_URGENCY_TERMS: Final[tuple[str, ...]] = (
    "urgent",
    "asap",
    "segera",
    "darurat",
    "deadline",
)

_ACTION_TERMS: Final[tuple[str, ...]] = (
    "please review",
    "action required",
    "tolong",
    "mohon",
)

_DEFAULT_NOTIFY_THRESHOLD: Final[int] = 5


@dataclass(frozen=True)
class ImportanceScore:
    """Result of an importance scoring evaluation.

    Attributes:
        total: Sum of all signal weights that fired.
        signals: Mapping of signal name → weight contributed.
        should_notify: ``True`` when ``total >= threshold``.
        reasoning: Human-readable explanation of the score.
    """

    total: int
    signals: dict[str, int]
    should_notify: bool
    reasoning: str


class ImportanceScorer:
    """Evaluates email importance using eight orthogonal signals.

    Signals are evaluated independently and their weights summed.
    The scorer is a pure local computation — no network calls.
    """

    _settings: GmailSettings
    _threshold: int

    def __init__(self, settings: GmailSettings | None = None) -> None:
        """Initialise with optional explicit *settings*.

        When *settings* is ``None`` the module-level singleton is
        loaded via :func:`~guinvere.gmail.config.get_gmail_settings`.
        """
        self._settings = settings or get_gmail_settings()
        self._threshold: int = (
            self._settings.importance_notify_threshold
            or _DEFAULT_NOTIFY_THRESHOLD
        )

    def score(
        self,
        envelope: GmailMessageEnvelope,
        category: EmailCategory,
    ) -> ImportanceScore:
        """Compute importance score for *envelope* under *category*.

        Evaluates all eight signals against the envelope and returns
        an aggregated ``ImportanceScore``.

        Parameters:
            envelope: The parsed inbound email envelope.
            category: The classification category for the email.

        Returns:
            An ``ImportanceScore`` instance with the aggregated result.
        """
        signals: dict[str, int] = {}

        self._eval_gmail_important(envelope, signals)
        self._eval_sender_whitelist(envelope, signals)
        self._eval_thread_depth(envelope, signals)
        self._eval_urgency_keywords(envelope, signals)
        self._eval_direct_address(envelope, signals)
        self._eval_financial_amount(category, signals)
        self._eval_action_keywords(envelope, signals)
        self._eval_reply_rate(envelope, signals)

        total = sum(signals.values())
        should_notify = total >= self._threshold
        reasoning = self._build_reasoning(signals, total, should_notify)

        score = ImportanceScore(
            total=total,
            signals=signals,
            should_notify=should_notify,
            reasoning=reasoning,
        )

        logger.info(
            "importance_scored",
            message_id=envelope.message_id,
            total_score=total,
            signal_count=len(signals),
            should_notify=should_notify,
            threshold=self._threshold,
        )

        return score

    # ── Signal evaluators ─────────────────────────────────────────────

    def _eval_gmail_important(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 1: +3 if Gmail's own IMPORTANT label is present."""
        if envelope.labels and "IMPORTANT" in envelope.labels:
            signals["gmail_important"] = _WEIGHT_GMAIL_IMPORTANT

    def _eval_sender_whitelist(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 2: +2 if sender domain/email is in the whitelist.

        Matches either an exact email address or a domain (when the
        whitelist entry does not contain ``@``).
        """
        whitelist = self._settings.sender_whitelist
        if not whitelist or not envelope.sender:
            return

        sender_lower = envelope.sender.strip().lower()
        if not sender_lower:
            return

        for entry in whitelist:
            entry_lower = entry.strip().lower()
            if not entry_lower:
                continue

            # Exact email match
            if sender_lower == entry_lower:
                signals["sender_whitelist"] = _WEIGHT_SENDER_WHITELIST
                return

            # Domain match: entry has no '@' so treat as domain
            if "@" not in entry_lower and sender_lower.endswith(
                f"@{entry_lower}",
            ):
                signals["sender_whitelist"] = _WEIGHT_SENDER_WHITELIST
                return

    def _eval_thread_depth(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 3: +1 when the thread has at least 3 references."""
        if envelope.reference_count >= 3:
            signals["thread_depth"] = _WEIGHT_THREAD_DEPTH

    def _eval_urgency_keywords(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 4: +2 for urgency keywords in subject or body.

        Searches case-insensitively for any of the configured urgency
        terms in the combined subject + body text.
        """
        text = _combine_text(envelope)
        if not text:
            return
        if re.search(
            "|".join(re.escape(t) for t in _URGENCY_TERMS),
            text,
            re.IGNORECASE,
        ):
            signals["urgency_keywords"] = _WEIGHT_URGENCY_KEYWORDS

    def _eval_direct_address(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 5: +1 when Faiz is the sole recipient.

        A sole recipient indicates the message is directly addressed
        to the user rather than being part of a mass mailing.
        """
        if envelope.recipient_count == 1:
            signals["direct_address"] = _WEIGHT_DIRECT_ADDRESS

    def _eval_financial_amount(
        self,
        category: EmailCategory,
        signals: dict[str, int],
    ) -> None:
        """Signal 6: +3 for financial or billing/invoice emails.

        These categories are inherently important because they involve
        monetary transactions or obligations.
        """
        if category in (
            EmailCategory.FINANCIAL,
            EmailCategory.BILLING_INVOICE,
        ):
            signals["financial_amount"] = _WEIGHT_FINANCIAL_AMOUNT

    def _eval_action_keywords(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 7: +2 for action-request keywords in subject or body.

        Detects phrases that indicate the sender is requesting a
        specific action or response.
        """
        text = _combine_text(envelope)
        if not text:
            return
        if re.search(
            "|".join(re.escape(t) for t in _ACTION_TERMS),
            text,
            re.IGNORECASE,
        ):
            signals["action_keywords"] = _WEIGHT_ACTION_KEYWORDS

    def _eval_reply_rate(
        self,
        envelope: GmailMessageEnvelope,
        signals: dict[str, int],
    ) -> None:
        """Signal 8: +1 when the email is a reply in an existing thread.

        Ongoing conversations are more likely to require attention than
        standalone cold messages.
        """
        if envelope.is_reply:
            signals["reply_rate"] = _WEIGHT_REPLY_RATE

    # ── Reasoning builder ─────────────────────────────────────────────

    @staticmethod
    def _build_reasoning(
        signals: dict[str, int],
        total: int,
        should_notify: bool,
    ) -> str:
        """Build a human-readable explanation of the score.

        Example::

            gmail_important(+3) | sender_whitelist(+2) | total=5 → notify
        """
        if not signals:
            return "no signals fired; score=0"

        parts = [f"{name}(+{weight})" for name, weight in signals.items()]
        verdict = "notify" if should_notify else "no-notify"
        return f"{' | '.join(parts)} | total={total} → {verdict}"


# ── Module-level helpers ───────────────────────────────────────────────────


def _combine_text(envelope: GmailMessageEnvelope) -> str:
    """Return joined subject + body text for keyword matching.

    Returns an empty string when both fields are empty or only
    whitespace.
    """
    parts: list[str] = []
    if envelope.subject:
        parts.append(envelope.subject)
    if envelope.body_text:
        parts.append(envelope.body_text)
    return " ".join(parts) if parts else ""


__all__ = [
    "ImportanceScore",
    "ImportanceScorer",
]
