"""Hash-anchored edit validation.

Computes SHA-256 hashes of specific file lines and validates
that the line content matches the expected hash before allowing
an edit operation.  Prevents blind overwrites when file content
has changed since the edit was planned.
"""

from __future__ import annotations

import hashlib

import structlog

logger = structlog.get_logger()


class HashAnchorError(Exception):
    """Raised when a line's hash does not match the expected anchor.

    Attributes:
        line_number: The 0-based line number that failed validation.
        expected_hash: The SHA-256 hash that was expected.
    """

    def __init__(self, line_number: int, expected_hash: str, message: str = "") -> None:
        self.line_number = line_number
        self.expected_hash = expected_hash
        if not message:
            message = (
                f"Hash anchor mismatch at line {line_number}: "
                f"expected {expected_hash}"
            )
        super().__init__(message)


def compute_line_hash(content: str, line_number: int) -> str:
    """Compute the SHA-256 hash of a specific line in the given content.

    Args:
        content: Full text content (newline-separated lines).
        line_number: 0-based line index.

    Returns:
        Hex digest of the SHA-256 hash of the line.

    Raises:
        IndexError: If line_number is out of range.
    """
    lines = content.split("\n")
    if line_number < 0 or line_number >= len(lines):
        raise IndexError(
            f"Line number {line_number} out of range "
            f"(content has {len(lines)} lines)"
        )
    line_text = lines[line_number]
    digest = hashlib.sha256(line_text.encode("utf-8")).hexdigest()
    logger.debug("line_hash_computed",
                 line_number=line_number,
                 hash_prefix=digest[:12])
    return digest


def validate_edit_content(content: str, line_number: int, expected_hash: str) -> bool:
    """Validate that a line in the given content matches the expected hash.

    Args:
        content: Full text content (newline-separated lines).
        line_number: 0-based line index to validate.
        expected_hash: Expected SHA-256 hex digest.

    Returns:
        True if the hash matches, False otherwise.
    """
    try:
        actual_hash = compute_line_hash(content, line_number)
    except IndexError:
        logger.error("hash_anchor_index_error",
                     line_number=line_number,
                     expected_hash=expected_hash)
        return False

    matches = actual_hash == expected_hash
    if not matches:
        logger.warning("hash_anchor_mismatch",
                       line_number=line_number,
                       expected_hash=expected_hash,
                       actual_prefix=actual_hash[:12])
    else:
        logger.debug("hash_anchor_valid", line_number=line_number)
    return matches


def validate_edit(file_path: str, line_number: int, expected_hash: str) -> bool:
    """Validate that a line in a file matches the expected hash.

    Reads the file from disk and delegates to ``validate_edit_content``.

    Args:
        file_path: Path to the file to validate.
        line_number: 0-based line index to validate.
        expected_hash: Expected SHA-256 hex digest.

    Returns:
        True if the hash matches, False otherwise.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except FileNotFoundError:
        logger.error("hash_anchor_file_not_found",
                     file_path=file_path,
                     line_number=line_number)
        return False
    except OSError as exc:
        logger.error("hash_anchor_file_read_error",
                     file_path=file_path,
                     error=str(exc))
        return False

    return validate_edit_content(content, line_number, expected_hash)
