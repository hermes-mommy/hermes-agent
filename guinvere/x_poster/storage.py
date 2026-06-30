from __future__ import annotations

"""P13 X Auto Poster — Filesystem storage manager.

Manages media files across lifecycle states (pending, posted, failed)
under a configurable ``media_root`` directory.  All operations are
synchronous and use ``pathlib.Path`` for filesystem access.
"""

import time
from pathlib import Path

import structlog
from structlog.stdlib import BoundLogger

from .config import get_xposter_settings
from .exceptions import XPosterError

_logger: BoundLogger = structlog.get_logger(__name__)

_VALID_STATES: frozenset[str] = frozenset({"pending", "posted", "failed"})
_MAX_PHOTO_BYTES: int = 5 * 1024 * 1024  # 5 MB
_MAX_VIDEO_BYTES: int = 512 * 1024 * 1024  # 512 MB
_SECONDS_PER_DAY: float = 86400.0


class StorageError(XPosterError):
    """Raised when a storage operation fails."""

    pass


class StorageManager:
    """Filesystem storage manager for X poster media assets.

    Creates and manages ``pending/``, ``posted/``, and ``failed/``
    subdirectories under the configured ``media_root``.
    """

    _media_root: Path
    _log: BoundLogger

    def __init__(self, media_root: str | Path | None = None) -> None:
        if media_root is not None:
            self._media_root = Path(media_root).resolve()
        else:
            self._media_root = Path(get_xposter_settings().media_root).resolve()

        self._log = _logger.bind(media_root=str(self._media_root))
        self._ensure_directories()

    # -- properties --------------------------------------------------------

    @property
    def media_root(self) -> Path:
        """Return the resolved media root path."""
        return self._media_root

    # -- directory setup ---------------------------------------------------

    def _ensure_directories(self) -> None:
        """Create state directories if they do not exist."""
        for state in _VALID_STATES:
            dir_path = self._media_root / state
            dir_path.mkdir(parents=True, exist_ok=True)
        self._log.info("x_poster.storage.directories_ready")

    def _state_dir(self, state: str) -> Path:
        """Return and validate the directory for a given state."""
        if state not in _VALID_STATES:
            raise StorageError(
                f"Invalid state '{state}'; must be one of {sorted(_VALID_STATES)}",
                context={"state": state},
            )
        return self._media_root / state

    def _media_path(self, post_id: str, filename: str, state: str) -> Path:
        """Construct the full path for a media file."""
        return self._state_dir(state) / f"{post_id}_{filename}"

    # -- core operations ---------------------------------------------------

    def save_media(
        self,
        post_id: str,
        filename: str,
        data: bytes,
        state: str = "pending",
    ) -> Path:
        """Write media data to the specified state directory.

        Args:
            post_id: Unique post identifier.
            filename: Original filename.
            data: Raw file bytes.
            state: Target lifecycle state.

        Returns:
            Absolute path to the saved file.

        Raises:
            StorageError: If the state is invalid or write fails.
        """
        target = self._media_path(post_id, filename, state)
        try:
            target.write_bytes(data)
            self._log.info(
                "x_poster.storage.save_media",
                post_id=post_id,
                filename=filename,
                state=state,
                size_bytes=len(data),
            )
            return target
        except OSError as exc:
            self._log.error(
                "x_poster.storage.save_media_failed",
                post_id=post_id,
                filename=filename,
                state=state,
                error=str(exc),
            )
            raise StorageError(
                f"Failed to save media: {exc}",
                context={"post_id": post_id, "filename": filename, "state": state},
            ) from exc

    def move_media(
        self,
        post_id: str,
        filename: str,
        from_state: str,
        to_state: str,
    ) -> Path:
        """Atomically move a media file between state directories.

        Args:
            post_id: Unique post identifier.
            filename: Original filename.
            from_state: Source lifecycle state.
            to_state: Destination lifecycle state.

        Returns:
            Absolute path to the moved file.

        Raises:
            StorageError: If source file is missing or move fails.
        """
        source = self._media_path(post_id, filename, from_state)
        destination = self._media_path(post_id, filename, to_state)

        if not source.exists():
            raise StorageError(
                f"Source file not found: {source}",
                context={
                    "post_id": post_id,
                    "filename": filename,
                    "from_state": from_state,
                },
            )

        try:
            source.rename(destination)
            self._log.info(
                "x_poster.storage.move_media",
                post_id=post_id,
                filename=filename,
                from_state=from_state,
                to_state=to_state,
            )
            return destination
        except OSError as exc:
            self._log.error(
                "x_poster.storage.move_media_failed",
                post_id=post_id,
                filename=filename,
                from_state=from_state,
                to_state=to_state,
                error=str(exc),
            )
            raise StorageError(
                f"Failed to move media: {exc}",
                context={
                    "post_id": post_id,
                    "filename": filename,
                    "from_state": from_state,
                    "to_state": to_state,
                },
            ) from exc

    def delete_media(self, post_id: str, filename: str, state: str) -> bool:
        """Delete a media file from the specified state directory.

        Args:
            post_id: Unique post identifier.
            filename: Original filename.
            state: Current lifecycle state.

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        target = self._media_path(post_id, filename, state)
        if not target.exists():
            self._log.warning(
                "x_poster.storage.delete_media_not_found",
                post_id=post_id,
                filename=filename,
                state=state,
            )
            return False

        try:
            target.unlink()
            self._log.info(
                "x_poster.storage.delete_media",
                post_id=post_id,
                filename=filename,
                state=state,
            )
            return True
        except OSError as exc:
            self._log.error(
                "x_poster.storage.delete_media_failed",
                post_id=post_id,
                filename=filename,
                state=state,
                error=str(exc),
            )
            raise StorageError(
                f"Failed to delete media: {exc}",
                context={"post_id": post_id, "filename": filename, "state": state},
            ) from exc

    def list_media(self, state: str) -> list[Path]:
        """List all files in a state directory.

        Args:
            state: Lifecycle state to list.

        Returns:
            Sorted list of file paths in the state directory.
        """
        state_dir = self._state_dir(state)
        files = sorted(p for p in state_dir.iterdir() if p.is_file())
        self._log.debug(
            "x_poster.storage.list_media",
            state=state,
            count=len(files),
        )
        return files

    # -- cleanup -----------------------------------------------------------

    def cleanup(self, posted_days: int, failed_days: int) -> int:
        """Delete old media files based on retention policy.

        Removes files from ``posted/`` older than ``posted_days`` and
        files from ``failed/`` older than ``failed_days``.  Never
        deletes the ``media_root`` itself or any state directories.

        Args:
            posted_days: Maximum age in days for posted media.
            failed_days: Maximum age in days for failed media.

        Returns:
            Number of files deleted.
        """
        now = time.time()
        deleted_count = 0

        retention_map: dict[str, int] = {
            "posted": posted_days,
            "failed": failed_days,
        }

        for state, max_age_days in retention_map.items():
            cutoff = now - (max_age_days * _SECONDS_PER_DAY)
            state_dir = self._media_root / state

            for file_path in state_dir.iterdir():
                if not file_path.is_file():
                    continue

                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < cutoff:
                        file_path.unlink()
                        deleted_count += 1
                        self._log.info(
                            "x_poster.storage.cleanup_deleted",
                            path=str(file_path),
                            state=state,
                            age_days=round((now - mtime) / _SECONDS_PER_DAY, 1),
                        )
                except OSError as exc:
                    self._log.error(
                        "x_poster.storage.cleanup_delete_failed",
                        path=str(file_path),
                        error=str(exc),
                    )

        self._log.info(
            "x_poster.storage.cleanup_complete",
            deleted_count=deleted_count,
            posted_days=posted_days,
            failed_days=failed_days,
        )
        return deleted_count

    # -- validation --------------------------------------------------------

    def validate_photo(self, path: Path) -> bool:
        """Validate a photo file exists and is under the size limit.

        Args:
            path: Path to the photo file.

        Returns:
            True if valid, False otherwise.
        """
        resolved = path.resolve()
        if not resolved.is_file():
            self._log.warning(
                "x_poster.storage.validate_photo_not_found",
                path=str(resolved),
            )
            return False

        size = resolved.stat().st_size
        if size > _MAX_PHOTO_BYTES:
            self._log.warning(
                "x_poster.storage.validate_photo_too_large",
                path=str(resolved),
                size_bytes=size,
                max_bytes=_MAX_PHOTO_BYTES,
            )
            return False

        self._log.debug(
            "x_poster.storage.validate_photo_ok",
            path=str(resolved),
            size_bytes=size,
        )
        return True

    def validate_video(
        self,
        path: Path,
        max_duration_s: float = 140.0,
    ) -> bool:
        """Validate a video file exists and is under the size limit.

        Args:
            path: Path to the video file.
            max_duration_s: Maximum video duration in seconds.
                Reserved for future ffprobe-based validation; currently
                only the file size constraint is enforced.

        Returns:
            True if valid, False otherwise.
        """
        resolved = path.resolve()
        if not resolved.is_file():
            self._log.warning(
                "x_poster.storage.validate_video_not_found",
                path=str(resolved),
            )
            return False

        size = resolved.stat().st_size
        if size > _MAX_VIDEO_BYTES:
            self._log.warning(
                "x_poster.storage.validate_video_too_large",
                path=str(resolved),
                size_bytes=size,
                max_bytes=_MAX_VIDEO_BYTES,
            )
            return False

        self._log.debug(
            "x_poster.storage.validate_video_ok",
            path=str(resolved),
            size_bytes=size,
            max_duration_s=max_duration_s,
        )
        return True
