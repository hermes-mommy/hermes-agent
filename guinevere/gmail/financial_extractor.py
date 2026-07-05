from __future__ import annotations

"""Financial email data extraction for P9 bridge.

Extracts structured financial metadata (amounts, categories, merchants)
from emails classified as FINANCIAL or BILLING_INVOICE, producing
:class:`FinancialExtraction` objects consumed by the P9 finance module
via Redis.

All extraction is purely local regex/heuristic — no network calls.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog

from .categories import EmailCategory
from .config import GmailSettings, get_gmail_settings
from .envelope import GmailMessageEnvelope

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Redis key conventions
# ---------------------------------------------------------------------------

_REDIS_HASH_PREFIX = "guinevere:gmail:financial"
_REDIS_SORTED_SET = f"{_REDIS_HASH_PREFIX}:by_time"

# ---------------------------------------------------------------------------
# Amount regex patterns (Indonesian Rupiah)
# ---------------------------------------------------------------------------

# Rp 1.500.000 | Rp1.500.000 | Rp 1.500.000,50 | Rp1.500.000,50
_AMOUNT_RP = re.compile(
    r"(?:Rp\.?\s*)([\d]{1,3}(?:\.[\d]{3})*(?:,[\d]+)?)"
    + r"|(?:Rp\.?\s*)(\d+(?:,\d+)?)"
)

# IDR 1,500,000 | IDR 500000
_AMOUNT_IDR = re.compile(r"IDR\s*([\d.,]+)")

# ---------------------------------------------------------------------------
# Transaction category keyword sets
# ---------------------------------------------------------------------------

_TRANSFER_KEYWORDS: frozenset[str] = frozenset({
    "transfer", "dana masuk", "dana keluar", "pemindahan dana",
    "trf", "diterima dari", "dikirim ke", "masuk dana",
})

_PAYMENT_KEYWORDS: frozenset[str] = frozenset({
    "pembayaran", "pembelian", "payment", "purchase", "belanja",
    "tarik tunai", "withdrawal", "penarikan", "debit",
})

_SUBSCRIPTION_KEYWORDS: frozenset[str] = frozenset({
    "langganan", "subscription", "berlangganan", "monthly",
    "annual", "recurring", "iuran",
})

_INVOICE_KEYWORDS: frozenset[str] = frozenset({
    "invoice", "faktur", "tagihan", "bill", "due date",
    "jatuh tempo", "no faktur", "kwitansi",
})

_REFUND_KEYWORDS: frozenset[str] = frozenset({
    "refund", "pengembalian", "dana kembali", "reversal",
    "pembatalan", "cancel", "kredit",
})

_SALARY_KEYWORDS: frozenset[str] = frozenset({
    "gaji", "salary", "payroll", "upah", "honorarium",
    "pendapatan", "penghasilan",
})

_INVESTMENT_KEYWORDS: frozenset[str] = frozenset({
    "investasi", "investment", "dividen", "saham", "reksadana",
    "obligasi", "return", "profit", "capital gain",
})

# ---------------------------------------------------------------------------
# Bank / fintech domain-to-name mapping
# ---------------------------------------------------------------------------

_BANK_DOMAIN_MAP: dict[str, str] = {
    "bca.co.id": "BCA",
    "mandiri.co.id": "Mandiri",
    "bri.co.id": "BRI",
    "btn.co.id": "BTN",
    "cimbniaga.co.id": "CIMB Niaga",
    "danamon.co.id": "Danamon",
    "maybank.co.id": "Maybank",
    "permata bank.com": "Permata",
    "uob.co.id": "UOB",
    "hsbc.co.id": "HSBC",
    "gopay.co.id": "Gopay",
    "gojek.com": "Gopay",
    "ovo.id": "OVO",
    "dana.id": "Dana",
    "shopee.co.id": "Shopee",
    "shopee.com": "Shopee",
    "tokopedia.com": "Tokopedia",
    "bukalapak.com": "Bukalapak",
    "blibli.com": "Blibli",
    "jago.com": "Bank Jago",
    "jenius.com": "Jenius",
    "digibank.co.id": "Digibank",
    "seabank.co.id": "SeaBank",
    "neobank.co.id": "Neo Bank",
    "superbank.id": "Superbank",
}

_BANK_TEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbca\b", re.IGNORECASE), "BCA"),
    (re.compile(r"\bmandiri\b", re.IGNORECASE), "Mandiri"),
    (re.compile(r"\bbri\b", re.IGNORECASE), "BRI"),
    (re.compile(r"\bbtn\b", re.IGNORECASE), "BTN"),
    (re.compile(r"\bcimb\b", re.IGNORECASE), "CIMB Niaga"),
    (re.compile(r"\bgopay\b", re.IGNORECASE), "Gopay"),
    (re.compile(r"\bovo\b", re.IGNORECASE), "OVO"),
    (re.compile(r"\bdana\b", re.IGNORECASE), "Dana"),
    (re.compile(r"\bshopee(?:pay)?\b", re.IGNORECASE), "Shopee"),
    (re.compile(r"\btokopedia\b", re.IGNORECASE), "Tokopedia"),
    (re.compile(r"\bseabank\b", re.IGNORECASE), "SeaBank"),
    (re.compile(r"\bjenius\b", re.IGNORECASE), "Jenius"),
    (re.compile(r"\bjago\b", re.IGNORECASE), "Bank Jago"),
    (re.compile(r"\bblu\b", re.IGNORECASE), "Blu BCA"),
    (re.compile(r"\bdigibank\b", re.IGNORECASE), "Digibank"),
]

# ---------------------------------------------------------------------------
# Reference number patterns
# ---------------------------------------------------------------------------

_REFERENCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:ref|reference|no\.?\s*ref|nomor\s*referensi)[:\s]*([A-Z0-9]{6,24})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:trx\s*id|transaction\s*(?:id|number|no))[:\s]*([A-Z0-9]{6,24})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:invoice\s*(?:no|#|number))[:\s]*([A-Z0-9]{6,24})",
        re.IGNORECASE,
    ),
    re.compile(r"\b(\d{12,20})\b"),  # Plain long numeric reference
]

# ---------------------------------------------------------------------------
# Merchant extraction patterns
# ---------------------------------------------------------------------------

_MERCHANT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:kepada|to|penerima|merchant)[:\s]+([A-Za-z\s\.]+?)(?:\.|,|\n|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:pembayaran\s+kepada|payment\s+to|paid\s+to)[:\s]+([A-Za-z\s\.]+?)(?:\.|,|\n|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:merchant|pedagang|penjual)[:\s]+([A-Za-z\s\.]+?)(?:\.|,|\n|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:dibayarkan\s+kepada|untuk)[:\s]+([A-Za-z\s\.]+?)(?:\.|,|\n|$)",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# Helper: parse Indonesian-formatted number
# ---------------------------------------------------------------------------

_COMMA_DECIMAL_RE = re.compile(r",(\d+)$")


def _parse_ina_number(raw: str) -> float | None:
    """Parse an Indonesian-formatted number string to :class:`float`.

    Handles:

    - ``1.500.000`` (dot-as-thousands  ->  1 500 000)
    - ``1.500.000,50`` (comma-as-decimal  ->  1 500 000.50)
    - ``1,500,000`` (comma-as-thousands  ->  1 500 000)
    - ``25000`` (plain)
    """
    if not raw or not raw.strip():
        return None

    raw = raw.strip()

    # Detect Indonesian decimal comma: ",XX" at end
    comma_match = _COMMA_DECIMAL_RE.search(raw)
    if comma_match:
        decimal_part = comma_match.group(1)
        whole = raw[: comma_match.start()].replace(".", "").replace(",", "")
        try:
            return float(f"{whole}.{decimal_part}")
        except (ValueError, TypeError):
            return None

    # No decimal comma — remove all dots (thousands) and commas
    cleaned = raw.replace(".", "").replace(",", "")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# FinancialExtraction dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FinancialExtraction:
    """Structured financial data extracted from a single email.

    This dataclass is the contract between the Gmail extractor and the
    P9 finance module.  All timestamps are timezone-aware UTC.
    """

    extraction_id: str
    message_id: str
    thread_id: str
    amount: float | None = None
    currency: str = "IDR"
    merchant: str | None = None
    category: str = "payment"
    bank_or_provider: str | None = None
    transaction_date: datetime | None = None
    reference_number: str | None = None
    confidence: float = 0.0
    raw_amount_text: str = ""
    extracted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# FinancialExtractor
# ---------------------------------------------------------------------------


class FinancialExtractor:
    """Extract structured financial data from classified email envelopes.

    Performs local regex/heuristic extraction — no network calls.
    Results are stored in Redis for consumption by the P9 finance module.
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        settings: GmailSettings | None = None,
    ) -> None:
        self._redis: aioredis.Redis = redis
        self._settings: GmailSettings = settings or get_gmail_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract(
        self,
        envelope: GmailMessageEnvelope,
    ) -> FinancialExtraction | None:
        """Run the full extraction pipeline on *envelope*.

        Returns ``None`` when no amount can be extracted (non-financial
        or malformed content).
        """
        text = envelope.body_text or envelope.subject or ""
        sender = envelope.sender

        amount, raw_text = self._extract_amount(text)
        if amount is None:
            logger.debug(
                "no_amount_found",
                message_id=envelope.message_id,
                thread_id=envelope.thread_id,
            )
            return None

        merchant = self._extract_merchant(text, sender)
        bank = self._identify_bank(sender, text)
        category = self._categorize_transaction(text, sender)
        reference = self._extract_reference(text)

        extraction = FinancialExtraction(
            extraction_id=uuid.uuid4().hex[:16],
            message_id=envelope.message_id,
            thread_id=envelope.thread_id,
            amount=amount,
            merchant=merchant,
            category=category,
            bank_or_provider=bank,
            reference_number=reference,
            confidence=self._calculate_confidence(amount, category, bank),
            raw_amount_text=raw_text,
        )

        await self.store_extraction(extraction)

        logger.info(
            "financial_extraction_complete",
            extraction_id=extraction.extraction_id,
            amount=extraction.amount,
            merchant=extraction.merchant,
            bank=extraction.bank_or_provider,
            category=extraction.category,
            confidence=extraction.confidence,
        )

        return extraction

    # ------------------------------------------------------------------
    # Amount extraction
    # ------------------------------------------------------------------

    def _extract_amount(self, text: str) -> tuple[float | None, str]:
        """Extract the largest amount from *text*.

        Returns ``(parsed_amount, raw_text)`` where *raw_text* is the
        original matched substring.

        When multiple amounts are found the largest is returned.  When
        none is found ``(None, "")`` is returned.
        """
        candidates: list[tuple[float, str]] = []

        # Rp-prefixed amounts
        for match in _AMOUNT_RP.finditer(text):
            raw = match.group(0)
            num_str = match.group(1) or match.group(2) or ""
            if num_str:
                parsed = _parse_ina_number(num_str)
                if parsed is not None and parsed > 0:
                    candidates.append((parsed, raw))

        # IDR-prefixed amounts
        for match in _AMOUNT_IDR.finditer(text):
            raw = match.group(0)
            num_str = match.group(1)
            if num_str:
                parsed = _parse_ina_number(num_str)
                if parsed is not None and parsed > 0:
                    candidates.append((parsed, raw))

        if not candidates:
            return (None, "")

        # Return the largest amount found
        candidates.sort(key=lambda x: x[0], reverse=True)
        return (candidates[0][0], candidates[0][1])

    # ------------------------------------------------------------------
    # Merchant extraction
    # ------------------------------------------------------------------

    def _extract_merchant(self, text: str, sender: str) -> str | None:
        """Identify the merchant or payee from email content."""
        for pattern in _MERCHANT_PATTERNS:
            match = pattern.search(text)
            if match:
                name = match.group(1).strip()
                if len(name) >= 2:
                    return name

        # Fallback: use sender domain as merchant hint
        sender_lower = sender.lower()
        for domain, name in _BANK_DOMAIN_MAP.items():
            if domain in sender_lower:
                return name

        return None

    # ------------------------------------------------------------------
    # Bank / fintech identification
    # ------------------------------------------------------------------

    def _identify_bank(self, sender: str, text: str) -> str | None:
        """Map the sender domain or text content to a bank or fintech."""
        sender_lower = sender.lower()

        # Check sender domain first (most reliable)
        for domain, name in _BANK_DOMAIN_MAP.items():
            if domain in sender_lower:
                return name

        # Fall back to text pattern matching
        for pattern, name in _BANK_TEXT_PATTERNS:
            if pattern.search(text):
                return name

        return None

    # ------------------------------------------------------------------
    # Transaction categorisation
    # ------------------------------------------------------------------

    def _categorize_transaction(self, text: str, sender: str) -> str:
        """Classify the transaction type based on *text* and *sender*."""
        text_lower = text.lower()

        # Salary (high specificity — check first)
        if any(kw in text_lower for kw in _SALARY_KEYWORDS):
            return "salary"

        # Refund
        if any(kw in text_lower for kw in _REFUND_KEYWORDS):
            return "refund"

        # Investment
        if any(kw in text_lower for kw in _INVESTMENT_KEYWORDS):
            return "investment"

        # Transfer
        if any(kw in text_lower for kw in _TRANSFER_KEYWORDS):
            return "transfer"

        # Invoice
        if any(kw in text_lower for kw in _INVOICE_KEYWORDS):
            return "invoice"

        # Subscription
        if any(kw in text_lower for kw in _SUBSCRIPTION_KEYWORDS):
            return "subscription"

        # Payment
        if any(kw in text_lower for kw in _PAYMENT_KEYWORDS):
            return "payment"

        # Default: bank notification without explicit keywords → transfer
        if self._identify_bank(sender, text) is not None:
            return "transfer"

        return "payment"

    # ------------------------------------------------------------------
    # Reference number extraction
    # ------------------------------------------------------------------

    def _extract_reference(self, text: str) -> str | None:
        """Extract a transaction reference number from *text*."""
        for pattern in _REFERENCE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_confidence(
        amount: float | None,
        category: str,
        bank: str | None,
    ) -> float:
        """Calculate extraction confidence score (0.0 — 1.0)."""
        if amount is None:
            return 0.0

        confidence = 0.5  # base confidence

        # Amount in a reasonable range for Indonesian finance
        if 1_000 <= amount <= 1_000_000_000:
            confidence += 0.15
        elif amount > 0:
            confidence += 0.05

        # Known category
        known = {"transfer", "payment", "subscription",
                 "invoice", "refund", "salary", "investment"}
        if category in known:
            confidence += 0.15

        # Known bank / fintech
        if bank is not None:
            confidence += 0.15

        # Round amount (no fractional cents) → higher confidence
        if amount == int(amount):
            confidence += 0.05

        return min(confidence, 1.0)

    # ------------------------------------------------------------------
    # Redis storage
    # ------------------------------------------------------------------

    async def store_extraction(
        self,
        extraction: FinancialExtraction,
    ) -> None:
        """Persist *extraction* to Redis for P9 consumption.

        Stores a HASH at ``guinevere:gmail:financial:{extraction_id}``
        and indexes the ID in a SORTED SET at
        ``guinevere:gmail:financial:by_time``.
        """
        pipe = self._redis.pipeline()

        key = f"{_REDIS_HASH_PREFIX}:{extraction.extraction_id}"

        mapping: dict[str, str] = {
            "extraction_id": extraction.extraction_id,
            "message_id": extraction.message_id,
            "thread_id": extraction.thread_id,
            "merchant": extraction.merchant or "",
            "category": extraction.category,
            "bank_or_provider": extraction.bank_or_provider or "",
            "reference_number": extraction.reference_number or "",
            "currency": extraction.currency,
            "raw_amount_text": extraction.raw_amount_text,
            "confidence": str(extraction.confidence),
            "extracted_at": extraction.extracted_at.isoformat(),
        }

        if extraction.amount is not None:
            mapping["amount"] = str(extraction.amount)
        if extraction.transaction_date is not None:
            mapping["transaction_date"] = extraction.transaction_date.isoformat()

        pipe.hset(key, mapping=mapping)
        pipe.zadd(
            _REDIS_SORTED_SET,
            {extraction.extraction_id: extraction.extracted_at.timestamp()},
        )

        await pipe.execute()

        logger.debug(
            "extraction_stored",
            extraction_id=extraction.extraction_id,
            redis_key=key,
        )

    async def get_extractions(
        self,
        days: int = 30,
        limit: int = 50,
    ) -> list[FinancialExtraction]:
        """Retrieve recent extractions from Redis.

        Args:
            days: Look-back window in days.
            limit: Maximum number of results.

        Returns:
            List of :class:`FinancialExtraction` objects, newest first.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        raw_ids = await self._redis.zrevrangebyscore(
            _REDIS_SORTED_SET,
            max="+inf",
            min=cutoff,
            start=0,
            num=limit,
        )
        ids: list[str] = [
            i.decode() if isinstance(i, bytes) else str(i) for i in raw_ids
        ]

        if not ids:
            return []

        # Fetch all hashes via pipelining
        pipe = self._redis.pipeline()
        for eid in ids:
            pipe.hgetall(f"{_REDIS_HASH_PREFIX}:{eid}")
        results = await pipe.execute()

        extractions: list[FinancialExtraction] = []
        for eid, data in zip(ids, results):
            if not data:
                continue
            try:
                normalised = self._normalise_hash(data)
                extractions.append(self._deserialise(normalised))
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "extraction_deserialise_failed",
                    extraction_id=eid,
                    error=str(exc),
                )

        return extractions

    async def get_extractions_since(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[FinancialExtraction]:
        """Retrieve extractions from Redis since a given datetime.

        Args:
            since: Look-back start time (timezone-aware or naive, assumed UTC).
            limit: Maximum number of results.

        Returns:
            List of :class:`FinancialExtraction` objects, newest first.
        """
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        cutoff = since.timestamp()

        raw_ids = await self._redis.zrevrangebyscore(
            _REDIS_SORTED_SET,
            max="+inf",
            min=cutoff,
            start=0,
            num=limit,
        )
        ids: list[str] = [
            i.decode() if isinstance(i, bytes) else str(i) for i in raw_ids
        ]

        if not ids:
            return []

        pipe = self._redis.pipeline()
        for eid in ids:
            pipe.hgetall(f"{_REDIS_HASH_PREFIX}:{eid}")
        results = await pipe.execute()

        extractions: list[FinancialExtraction] = []
        for eid, data in zip(ids, results):
            if not data:
                continue
            try:
                normalised = self._normalise_hash(data)
                extractions.append(self._deserialise(normalised))
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "extraction_deserialise_failed",
                    extraction_id=eid,
                    error=str(exc),
                )

        return extractions

    # ------------------------------------------------------------------
    # Redis serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_hash(data: dict[str | bytes, str | bytes]) -> dict[str, str]:
        """Convert a Redis hash (bytes or str keys) to str-keyed dict.

        Redis 5.x with RESP2 returns ``bytes`` keys from ``HGETALL``;
        RESP3 returns ``str`` keys.  This normaliser handles both.
        """
        result: dict[str, str] = {}
        for k, v in data.items():
            key = k.decode() if isinstance(k, bytes) else str(k)
            val = v.decode() if isinstance(v, bytes) else str(v)
            result[key] = val
        return result

    @staticmethod
    def _deserialise(data: dict[str, str]) -> FinancialExtraction:
        """Convert a normalised Redis hash back to :class:`FinancialExtraction`."""
        amount: float | None = None
        raw_amount = data.get("amount", "")
        if raw_amount:
            try:
                amount = float(raw_amount)
            except (ValueError, TypeError):
                amount = None

        tx_date: datetime | None = None
        raw_tx = data.get("transaction_date", "")
        if raw_tx:
            try:
                tx_date = datetime.fromisoformat(raw_tx)
            except (ValueError, TypeError):
                pass

        ext_at_str = data.get("extracted_at", "")
        extracted_at = datetime.now(timezone.utc)
        if ext_at_str:
            try:
                extracted_at = datetime.fromisoformat(ext_at_str)
            except (ValueError, TypeError):
                pass

        return FinancialExtraction(
            extraction_id=data.get("extraction_id", ""),
            message_id=data.get("message_id", ""),
            thread_id=data.get("thread_id", ""),
            amount=amount,
            currency=data.get("currency", "IDR"),
            merchant=data.get("merchant") or None,
            category=data.get("category", "payment"),
            bank_or_provider=data.get("bank_or_provider") or None,
            transaction_date=tx_date,
            reference_number=data.get("reference_number") or None,
            confidence=float(data.get("confidence", 0)),
            raw_amount_text=data.get("raw_amount_text", ""),
            extracted_at=extracted_at,
        )


__all__ = [
    "FinancialExtraction",
    "FinancialExtractor",
]
