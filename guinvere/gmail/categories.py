from __future__ import annotations

"""Email classification taxonomy for P12 Gmail Integration.

Defines the category and priority enums used throughout the Gmail
pipeline to classify, prioritise, and route inbound email.  Mappings
are intentionally exhaustive — every ``EmailCategory`` must appear in
both ``CATEGORY_PRIORITY`` and ``CATEGORY_ACTIONS``.
"""

from enum import Enum


class EmailCategory(str, Enum):
    """High-level email classification bucket."""

    CLIENT_WORK = "client_work"
    FINANCIAL = "financial"
    BILLING_INVOICE = "billing_invoice"
    IMPORTANT = "important"
    NEWSLETTER = "newsletter"
    PROMOTION = "promotion"
    TRANSACTIONAL = "transactional"
    SPAM_PHISHING = "spam_phishing"


class EmailPriority(str, Enum):
    """Routing priority for a categorised email."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BLOCK = "block"


CATEGORY_PRIORITY: dict[EmailCategory, EmailPriority] = {
    EmailCategory.CLIENT_WORK: EmailPriority.HIGH,
    EmailCategory.FINANCIAL: EmailPriority.HIGH,
    EmailCategory.BILLING_INVOICE: EmailPriority.MEDIUM,
    EmailCategory.IMPORTANT: EmailPriority.HIGH,
    EmailCategory.NEWSLETTER: EmailPriority.LOW,
    EmailCategory.PROMOTION: EmailPriority.LOW,
    EmailCategory.TRANSACTIONAL: EmailPriority.MEDIUM,
    EmailCategory.SPAM_PHISHING: EmailPriority.BLOCK,
}

CATEGORY_ACTIONS: dict[EmailCategory, list[str]] = {
    EmailCategory.CLIENT_WORK: ["notify", "draft_reply"],
    EmailCategory.FINANCIAL: ["notify", "p9_extract"],
    EmailCategory.BILLING_INVOICE: ["notify", "p9_extract", "archive"],
    EmailCategory.IMPORTANT: ["notify", "draft_reply"],
    EmailCategory.NEWSLETTER: ["summarise", "archive"],
    EmailCategory.PROMOTION: ["archive"],
    EmailCategory.TRANSACTIONAL: ["notify", "archive"],
    EmailCategory.SPAM_PHISHING: ["block", "report"],
}
