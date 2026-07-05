"""Evidence directory management and artifact I/O for autonomous SDLC loops.

Each loop instance gets a timestamped evidence directory under
``/home/guinevere/evidence/loops/{YYYY-MM-DD}-{loop_id}/``.
Phase handlers produce markdown artifacts that are written here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger()

_EVIDENCE_ROOT = Path("/home/guinevere/evidence/loops")


def evidence_dir(loop_id: str) -> Path:
    """Return the evidence directory for *loop_id*, creating it if missing.

    Directory layout:
        /home/guinevere/evidence/loops/{YYYY-MM-DD}-{loop_id}/
    """
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    directory = _EVIDENCE_ROOT / f"{date_prefix}-{loop_id}"

    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(
            "artifacts.evidence_dir_created",
            loop_id=loop_id,
            path=str(directory),
        )

    return directory


def write_artifact(loop_id: str, phase: str, content: str) -> Path:
    """Write a markdown artifact file into the loop's evidence directory.

    Args:
        loop_id: Unique identifier for the loop instance.
        phase: Phase name used as the filename stem (e.g. ``research-report``).
        content: Markdown body to persist.

    Returns:
        The absolute :class:`~pathlib.Path` of the written file.
    """
    directory = evidence_dir(loop_id)
    filepath = directory / f"{phase}.md"

    filepath.write_text(content, encoding="utf-8")

    logger.info(
        "artifacts.artifact_written",
        loop_id=loop_id,
        phase=phase,
        path=str(filepath),
        size_bytes=filepath.stat().st_size,
    )

    return filepath


def read_artifact(loop_id: str, phase: str) -> str | None:
    """Read the content of a previously written artifact.

    Returns:
        The artifact text, or ``None`` if the file does not exist.
    """
    directory = evidence_dir(loop_id)
    filepath = directory / f"{phase}.md"

    if not filepath.exists():
        logger.debug(
            "artifacts.artifact_not_found",
            loop_id=loop_id,
            phase=phase,
            expected_path=str(filepath),
        )
        return None

    content = filepath.read_text(encoding="utf-8")

    logger.debug(
        "artifacts.artifact_read",
        loop_id=loop_id,
        phase=phase,
        size_bytes=len(content),
    )

    return content


def artifact_exists(loop_id: str, phase: str) -> bool:
    """Check whether an artifact file exists for the given loop and phase."""
    directory = evidence_dir(loop_id)
    filepath = directory / f"{phase}.md"
    exists = filepath.exists()

    logger.debug(
        "artifacts.artifact_exists_check",
        loop_id=loop_id,
        phase=phase,
        exists=exists,
    )

    return exists
