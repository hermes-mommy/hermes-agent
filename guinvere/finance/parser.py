"""Finance Transaction Parser — parses casual Indonesian messages into structured transactions.

This module handles:
- Casual message detection (is this a finance message?)
- Transaction type detection (income/expense/transfer/debt)
- Amount parsing (25rb, 1.5jt, 500k, etc.)
- Category classification (dynamic based on keywords)
- Account detection (from context)
- Database storage (PostgreSQL finance schema)

Usage:
    from guinvere.finance.parser import FinanceParser
    parser = FinanceParser()
    result = parser.parse("makan nasi goreng 25rb")
    # Returns: {"type": "expense", "amount": 25000, "category": "Food", "description": "makan nasi goreng"}
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))


@dataclass
class ParseResult:
    """Result of parsing a finance message."""
    is_finance: bool
    type: Optional[str] = None  # "income", "expense", "transfer", "debt"
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    account: Optional[str] = None
    to_account: Optional[str] = None
    raw_message: Optional[str] = None
    confidence: float = 0.0


class FinanceParser:
    """Parse casual Indonesian finance messages."""

    # Amount patterns
    AMOUNT_PATTERNS = [
        # "25rb", "25 rb", "25ribu"
        (r'(\d+(?:\.\d+)?)\s*(?:rb|ribu)', lambda m: float(m.group(1)) * 1000),
        # "1.5jt", "1.5 jt", "1juta"
        (r'(\d+(?:\.\d+)?)\s*(?:jt|juta)', lambda m: float(m.group(1)) * 1000000),
        # "500k", "500 k" (word boundary to avoid matching "ke")
        (r'(\d+(?:\.\d+)?)\s*k\b', lambda m: float(m.group(1)) * 1000),
        # "300,000" or "1,500,000" (comma-separated thousands)
        (r'(\d{1,3}(?:,\d{3})+)', lambda m: float(m.group(1).replace(',', ''))),
        # "25000", "25.000" (dot-separated thousands)
        (r'(\d{1,3}(?:\.\d{3})+)', lambda m: float(m.group(1).replace('.', ''))),
        # "rp25000", "rp 25000", "rp25.000", "rp 300,000"
        (r'(?:rp|rupiah)\s*(\d[\d.,]*)', lambda m: float(re.sub(r'[.,]', '', m.group(1)))),
        # Plain numbers (4+ digits to avoid false positives)
        (r'\b(\d{4,})\b', lambda m: float(m.group(1))),
    ]

    # Account aliases (shorthand → account name pattern)
    ACCOUNT_ALIASES = {
        's': 'Sea Bank',
        'sea': 'Sea Bank',
        'seabank': 'Sea Bank',
        'b': 'Blu BCA',
        'blu': 'Blu BCA',
        'bc': 'Blu BCA',
        'okx': 'OKX',
        'tw': 'Trust Wallet',
        'trust': 'Trust Wallet',
        'sb': 'Stockbit',
        'stockbit': 'Stockbit',
        'cash': 'Cash',
        'tunai': 'Cash',
    }

    # Transaction type keywords
    INCOME_KEYWORDS = [
        'gajian', 'gaji', 'masuk', 'dapat', 'dibayar', 'freelance', 'project',
        'client', 'bonus', 'thr', 'hadiah', 'refund', 'cashback', 'dividen',
        'untung', 'profit', 'cair', 'withdraw', 'tarik'
    ]

    EXPENSE_KEYWORDS = [
        'makan', 'beli', 'bayar', 'keluar', 'habis', 'buang', 'jajan',
        'grab', 'gojek', 'ojol', 'transport', 'bensin', 'parkir', 'tol',
        'listrik', 'air', 'internet', 'pulsa', 'wifi', 'bpjs', 'tagihan',
        'shopee', 'tokopedia', 'lazada', 'baju', 'sepatu', 'kos', 'kosan',
        'nonton', 'game', 'netflix', 'spotify', 'steam', 'obat', 'dokter',
        'kursus', 'buku', 'traktir', 'sumbangan', 'arisan', 'sedekah',
        'kop', 'kopi', 'snack', 'jajan', 'warteg', 'kfc', 'mcd', 'starbucks'
    ]

    TRANSFER_KEYWORDS = [
        'transfer', 'pindah', 'kirim', 'topup', 'top up', 'isi', 'tarik',
        'withdraw', 'cair'
    ]

    DEBT_KEYWORDS = [
        'hutang', 'utang', 'pinjam', 'bayar hutang', 'bayar utang', 'lunasi',
        'cicil', 'cicilan', 'angsur'
    ]

    # Category keywords
    CATEGORY_KEYWORDS = {
        'Food': [
            'makan', 'nasi', 'ayam', 'ikan', 'sayur', 'roti', 'mie', 'bakso',
            'soto', 'rendang', 'padang', 'warteg', 'kfc', 'mcd', 'starbucks',
            'kopi', 'teh', 'jus', 'snack', 'jajan', 'coklat', 'es krim',
            'sarapan', 'makan siang', 'makan malam', 'ngopi', 'ngemil'
        ],
        'Transport': [
            'grab', 'gojek', 'ojol', 'taxi', 'bus', 'kereta', 'mrt', 'transjakarta',
            'bensin', 'solar', 'parkir', 'tol', 'ojek', 'angkot', 'becak',
            'motor', 'mobil', 'sewa kendaraan'
        ],
        'Bills': [
            'listrik', 'air', 'pdam', 'internet', 'wifi', 'pulsa', 'bpjs',
            'tagihan', 'bayar tagihan', 'asuransi', 'pajak', 'retribusi'
        ],
        'Shopping': [
            'beli', 'shopee', 'tokopedia', 'lazada', 'bukalapak', 'blibli',
            'baju', 'sepatu', 'celana', 'jaket', 'tas', 'dompet', 'jam',
            'elektronik', 'hp', 'laptop', 'komputer', 'charger', 'kabel'
        ],
        'Entertainment': [
            'nonton', 'bioskop', 'game', 'steam', 'playstation', 'xbox',
            'netflix', 'spotify', 'youtube', 'tiktok', 'instagram', 'facebook',
            'konser', 'festival', 'liburan', 'jalan-jalan', 'wisata'
        ],
        'Health': [
            'obat', 'dokter', 'rumah sakit', 'klinik', 'apotek', 'vitamin',
            'suplemen', 'medical', 'checkup', 'laboratorium', 'rontgen'
        ],
        'Education': [
            'kursus', 'seminar', 'workshop', 'buku', 'modul', 'ebook',
            'pelatihan', 'training', 'sertifikasi', 'ujian', 'kuliah'
        ],
        'Social': [
            'traktir', 'hadiah', 'sumbangan', 'arisan', 'sedekah', 'zakat',
            'infaq', 'kado', 'nikah', 'khitan', 'wisuda', 'ulang tahun'
        ],
    }

    # Income category keywords
    INCOME_CATEGORIES = {
        'Salary': ['gajian', 'gaji', 'payroll', 'upah', 'honor'],
        'Freelance': ['freelance', 'project', 'client', 'order', 'job'],
        'Investment': ['dividen', 'untung', 'profit', 'cair', 'return'],
        'Other Income': ['bonus', 'thr', 'hadiah', 'refund', 'cashback'],
    }

    def __init__(self):
        """Initialize the parser with compiled patterns."""
        self._amount_patterns = [(re.compile(p, re.IGNORECASE), fn) for p, fn in self.AMOUNT_PATTERNS]
        self._income_re = re.compile('|'.join(self.INCOME_KEYWORDS), re.IGNORECASE)
        self._expense_re = re.compile('|'.join(self.EXPENSE_KEYWORDS), re.IGNORECASE)
        self._transfer_re = re.compile('|'.join(self.TRANSFER_KEYWORDS), re.IGNORECASE)
        self._debt_re = re.compile('|'.join(self.DEBT_KEYWORDS), re.IGNORECASE)
        # Account pattern: "dari s", "dari blu", "ke okx", "pakai b", "dari seabank"
        self._account_re = re.compile(
            r'(?:dari|dari\s+akun|pakai|pakai\s+dari|dari\s+rekening|dari\s+tabungan|ke)\s+(\w+)',
            re.IGNORECASE
        )

    def parse(self, message: str) -> ParseResult:
        """Parse a casual finance message.

        Args:
            message: The raw message text from Faiz.

        Returns:
            ParseResult with detected fields.
        """
        if not message or not message.strip():
            return ParseResult(is_finance=False)

        msg = message.strip()
        msg_lower = msg.lower()

        # Extract amount first
        amount = self._extract_amount(msg)
        if amount is None or amount <= 0:
            return ParseResult(is_finance=False, raw_message=msg)

        # Detect transaction type
        tx_type = self._detect_type(msg_lower)
        if tx_type is None:
            # Default to expense if amount found but no type detected
            tx_type = "expense"

        # Classify category
        category = self._classify_category(msg_lower, tx_type)

        # Extract account hint
        account = self._extract_account(msg_lower)
        to_account = self._extract_to_account(msg_lower)

        # Generate description (clean up the message)
        description = self._clean_description(msg, amount)

        # Calculate confidence
        confidence = self._calculate_confidence(tx_type, category, amount)

        logger.info(
            "finance_message_parsed",
            type=tx_type,
            amount=amount,
            category=category,
            account=account,
            confidence=confidence,
        )

        return ParseResult(
            is_finance=True,
            type=tx_type,
            amount=amount,
            category=category,
            description=description,
            account=account,
            to_account=to_account,
            raw_message=msg,
            confidence=confidence,
        )

    def _extract_amount(self, message: str) -> Optional[float]:
        """Extract amount from message using multiple patterns."""
        for pattern, converter in self._amount_patterns:
            match = pattern.search(message)
            if match:
                try:
                    amount = converter(match)
                    if amount > 0:
                        return amount
                except (ValueError, IndexError):
                    continue
        return None

    def _detect_type(self, msg_lower: str) -> Optional[str]:
        """Detect transaction type from keywords."""
        # Check transfer first (most specific)
        if self._transfer_re.search(msg_lower):
            return "transfer"

        # Check debt
        if self._debt_re.search(msg_lower):
            return "debt"

        # Check income
        if self._income_re.search(msg_lower):
            return "income"

        # Check expense
        if self._expense_re.search(msg_lower):
            return "expense"

        return None

    def _classify_category(self, msg_lower: str, tx_type: str) -> str:
        """Classify message into category based on keywords."""
        if tx_type == "income":
            for category, keywords in self.INCOME_CATEGORIES.items():
                for kw in keywords:
                    if kw in msg_lower:
                        return category
            return "Other Income"

        if tx_type == "transfer":
            return "Transfer"

        if tx_type == "debt":
            return "Debt Payment"

        # Expense categories
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in msg_lower:
                    return category

        return "Other"

    def _extract_account(self, msg_lower: str) -> Optional[str]:
        """Extract source account from message.

        Looks for patterns like "dari s", "pakai blu", "dari seabank".
        Returns the account name if found, None otherwise.
        """
        # Pattern: "dari <alias>", "pakai <alias>" — NOT "ke" (that's destination)
        match = re.search(
            r'(?:dari|pakai|dari\s+rekening|dari\s+tabungan|dari\s+akun)\s+(\w+)',
            msg_lower
        )
        if match:
            alias = match.group(1).lower()
            # Only return if it's a known account alias
            if alias in self.ACCOUNT_ALIASES:
                return self.ACCOUNT_ALIASES[alias]
        return None

    def _extract_to_account(self, msg_lower: str) -> Optional[str]:
        """Extract destination account from transfer/income messages.

        Looks for patterns like "ke okx", "ke blu".
        Returns the account name if found, None otherwise.
        """
        # For transfers and income (money going TO an account)
        if not (self._transfer_re.search(msg_lower) or self._income_re.search(msg_lower)):
            return None

        # Pattern: "ke <alias>" (but not "ke ibu", "ke mama" which are people)
        match = re.search(r'ke\s+(\w+)', msg_lower)
        if match:
            alias = match.group(1).lower()
            # Only return if it's a known account alias
            if alias in self.ACCOUNT_ALIASES:
                return self.ACCOUNT_ALIASES[alias]
        return None

    def _clean_description(self, message: str, amount: float) -> str:
        """Clean up message to create a readable description."""
        # Remove amount patterns
        desc = message
        for pattern, _ in self._amount_patterns:
            desc = pattern.sub('', desc)

        # Clean up extra spaces
        desc = re.sub(r'\s+', ' ', desc).strip()

        # Remove common prefixes
        desc = re.sub(r'^(rp|rupiah)\s*', '', desc, flags=re.IGNORECASE).strip()

        # Capitalize first letter
        if desc:
            desc = desc[0].upper() + desc[1:]

        return desc if desc else message

    def _calculate_confidence(self, tx_type: str, category: str, amount: float) -> float:
        """Calculate confidence score for the parse result."""
        confidence = 0.5  # Base confidence

        # Higher confidence if type was detected (not defaulted)
        if tx_type in ("income", "expense", "transfer", "debt"):
            confidence += 0.2

        # Higher confidence if category is specific (not "Other")
        if category not in ("Other", "Other Income"):
            confidence += 0.2

        # Higher confidence if amount is reasonable
        if 1000 <= amount <= 100000000:  # 1rb to 100jt
            confidence += 0.1

        return min(confidence, 1.0)
