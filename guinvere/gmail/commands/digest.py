"""Discord ``!email-digest`` command — unread email digest with pagination.

Provides the ``EmailDigestCommand`` class that handles Faiz-only access
control, rate limiting (5/hour), time-range parsing, and 1900-char
pagination.  Delegates the actual digest construction to
``BriefingGenerator.digest_command()``.

Usage::

    command = EmailDigestCommand(briefing_generator, faiz_user_id=12345)
    pages = await command.handle(message, "24h")
    for page in pages:
        await message.channel.send(page)
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from guinvere.gmail.briefing import BriefingGenerator

logger = structlog.get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_DIGEST_SEPARATOR: str = "\u2501" * 21  # "━━━━━━━━━━━━━━━━━━━━━"
_DEFAULT_TIME_RANGE: str = "12h"
_MAX_PAGE_CHARS: int = 1900
_RATE_LIMIT_MAX: int = 5
_RATE_LIMIT_WINDOW: int = 3600

_VALID_RANGES: dict[str, str] = {
    "12h": "12h",
    "24h": "24h",
    "1d": "24h",
    "today": "today",
    "7d": "7d",
    "week": "7d",
}

# ── Exceptions ───────────────────────────────────────────────────────────────


class EmailDigestError(Exception):
    """Base exception for ``!email-digest`` command failures."""


class UserNotAuthorizedError(EmailDigestError):
    """Raised when a non-Faiz user invokes the command."""


class RateLimitError(EmailDigestError):
    """Raised when the per-user rate limit is exceeded."""


class CommandDisabledError(EmailDigestError):
    """Raised when the Gmail command feature flag is off."""


# ── Command Implementation ───────────────────────────────────────────────────


class EmailDigestCommand:
    """Discord ``!email-digest`` command handler with auth, rate-limit, and
    pagination.

    Parameters
    ----------
    briefing_generator:
        An instance of ``BriefingGenerator`` that implements
        ``async digest_command(time_range: str) -> str``.
    faiz_user_id:
        The Discord user ID authorised to run this command.
    rate_limit:
        Maximum number of invocations per ``rate_window`` seconds per user.
    rate_window:
        Sliding-window duration in seconds.
    enabled:
        Set to ``False`` to respond with a disabled message instead of
        executing the command.
    """

    def __init__(
        self,
        briefing_generator: BriefingGenerator,
        *,
        faiz_user_id: int,
        rate_limit: int = _RATE_LIMIT_MAX,
        rate_window: int = _RATE_LIMIT_WINDOW,
        enabled: bool = True,
    ) -> None:
        self._briefing: BriefingGenerator = briefing_generator
        self._faiz_user_id: int = faiz_user_id
        self._rate_limit: int = rate_limit
        self._rate_window: int = rate_window
        self._enabled: bool = enabled

        # Per-user sliding window: user_id -> deque[unix_timestamp]
        self._rate_limits: defaultdict[int, deque[float]] = defaultdict(deque)

    # ── Public API ───────────────────────────────────────────────────────────

    async def handle(
        self,
        message_or_interaction: object,
        time_range: str = _DEFAULT_TIME_RANGE,
    ) -> list[str]:
        """Validate, generate, paginate, and return the email digest pages.

        Steps
        -----
        1. Extract the Discord user ID from the message or interaction.
        2. Reject if the command feature flag is disabled.
        3. Reject if the user is not Faiz.
        4. Reject if the per-user rate limit is exceeded.
        5. Parse and normalise the ``time_range`` argument.
        6. Call ``BriefingGenerator.digest_command()`` for the digest text.
        7. Wrap the digest in the ``!email-digest`` output format.
        8. Paginate at 1900 characters.
        9. Log the command usage and return the page list.

        Parameters
        ----------
        message_or_interaction:
            A Discord ``Message`` (has ``author.id``) or ``Interaction``
            (has ``user.id``).
        time_range:
            One of ``"12h"``, ``"24h"``, ``"1d"``, ``"today"``, ``"7d"``,
            ``"week"``.  Defaults to ``"12h"``.

        Returns
        -------
            A list of page strings, each at most 1900 characters.

        Raises
        ------
        EmailDigestError
            For any known command-level error (auth, rate-limit, disabled).
        """
        user_id = self._resolve_user_id(message_or_interaction)
        if user_id is None:
            logger.warning("digest_handle: unable to resolve user_id from object")
            return ["Unable to identify command sender."]

        if not self._enabled:
            logger.info("digest_disabled", user_id=user_id)
            return ["Gmail commands are currently disabled."]

        if not self._validate_user(user_id):
            logger.warning("digest_unauthorized", user_id=user_id)
            return ["Only Faiz can use this command."]

        if not self._check_rate_limit(user_id):
            logger.warning("digest_rate_limited", user_id=user_id)
            return [(
                "Rate limit reached. You can use this command again in about"
                f" {self._rate_window // 60} minutes."
            )]

        resolved_range = self._parse_time_range(time_range)

        try:
            digest_text = await self._briefing.digest_command(resolved_range)
        except Exception:
            logger.exception(
                "digest_briefing_failed",
                user_id=user_id,
                time_range=resolved_range,
            )
            return [
                "Failed to generate email digest. Please try again later."
            ]

        formatted = self._format_digest(digest_text, resolved_range)
        pages = self._paginate(formatted)

        logger.info(
            "digest_ok",
            user_id=user_id,
            time_range=resolved_range,
            page_count=len(pages),
        )

        return pages

    # ── Internal: auth, rate-limit, parsing, pagination ──────────────────────

    @staticmethod
    def _resolve_user_id(obj: object) -> int | None:
        """Extract the Discord user id from a ``Message`` or ``Interaction``.

        Tries ``obj.author.id`` (prefix message) first, then
        ``obj.user.id`` (slash interaction).
        """
        user: object | None = None
        if hasattr(obj, "author"):
            user = getattr(obj, "author", None)
        if user is None and hasattr(obj, "user"):
            user = getattr(obj, "user", None)
        if user is not None:
            return getattr(user, "id", None)
        return None

    def _validate_user(self, user_id: int) -> bool:
        """Return ``True`` when *user_id* matches the configured Faiz ID."""
        return user_id == self._faiz_user_id

    def _check_rate_limit(self, user_id: int) -> bool:
        """Sliding-window rate check — returns ``True`` if the call is allowed.

        Removes expired timestamps from the user's deque before checking
        whether the remaining count is below the limit.
        """
        now = time.time()
        window = self._rate_limits[user_id]

        # Evict entries outside the sliding window
        while window and window[0] < now - self._rate_window:
            _ = window.popleft()

        if len(window) >= self._rate_limit:
            return False

        window.append(now)
        return True

    @staticmethod
    def _parse_time_range(raw: str) -> str:
        """Normalise a freeform time range to one of the canonical values.

        Recognised inputs: ``"12h"``, ``"24h"``, ``"1d"``, ``"today"``,
        ``"7d"``, ``"week"``.  Returns ``"12h"`` for anything unrecognised.
        """
        return _VALID_RANGES.get(raw.strip().lower(), _DEFAULT_TIME_RANGE)

    @staticmethod
    def _format_digest(digest_text: str, resolved_range: str) -> str:
        """Wrap the raw digest text in the ``!email-digest`` output format.

        The format::

            📬 Email Digest — last {resolved_range}
            ━━━━━━━━━━━━━━━━━━━━━
            {digest_text}
            ━━━━━━━━━━━━━━━━━━━━━
        """
        lines: list[str] = [
            f"\U0001f4ec Email Digest \u2014 last {resolved_range}",
            _DIGEST_SEPARATOR,
            digest_text,
        ]
        return "\n".join(lines)

    @staticmethod
    def _paginate(text: str, max_chars: int = _MAX_PAGE_CHARS) -> list[str]:
        """Split *text* into pages of at most *max_chars* characters each.

        Splits on newline boundaries so that individual lines are never
        broken.  If a single line exceeds *max_chars* it is placed on its
        own page as-is (Discord will word-wrap it).
        """
        if not text:
            return [text]

        if len(text) <= max_chars:
            return [text]

        lines = text.split("\n")
        pages: list[str] = []
        current: list[str] = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1  # account for the joining newline

            # If a single line is too long, flush current and put it alone
            if line_len > max_chars:
                if current:
                    pages.append("\n".join(current))
                    current = []
                    current_len = 0
                pages.append(line)
                continue

            if current_len + line_len > max_chars:
                pages.append("\n".join(current))
                current = []
                current_len = 0

            current.append(line)
            current_len += line_len

        if current:
            pages.append("\n".join(current))

        # Append page footer
        total = len(pages)
        numbered: list[str] = []
        for i, page in enumerate(pages):
            numbered.append(
                f"{page}\n{_DIGEST_SEPARATOR}\nPage {i + 1}/{total}"
            )

        return numbered
