"""Discord ``on_message`` listener for #x-upload channel.

Processes media uploads and enqueues them to the X Poster service via HTTP API.
Supports direct media attachments and enterprise ZIP bundles with bounded,
validated extraction.
"""

from __future__ import annotations

import mimetypes
import os
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final, cast

import discord
import httpx
import structlog

from guinevere.discord._embed_utils import (
    EmbedData,
    EmbedField,
    now_wib_str,
    to_discord_embed,
)
from guinevere.discord.colors import SUCCESS, WARNING

logger = structlog.get_logger(__name__)

_XPOSTER_API_BASE: Final[str] = "http://127.0.0.1:8097"
_TIMEOUT: Final[float] = 600.0
_NOTIFICATION_DELETE_AFTER_SECONDS: Final[float] = 60.0

_ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset({
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/quicktime", "video/webm",
})
_ZIP_CONTENT_TYPES: Final[frozenset[str]] = frozenset({
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
})
_IMAGE_EXTENSIONS: Final[dict[str, str]] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_VIDEO_EXTENSIONS: Final[dict[str, str]] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}
_ALLOWED_EXTENSIONS: Final[dict[str, str]] = {
    **_IMAGE_EXTENSIONS,
    **_VIDEO_EXTENSIONS,
}
_MAX_PHOTO_BYTES: Final[int] = 5 * 1024 * 1024       # 5MB
_MAX_VIDEO_BYTES: Final[int] = 512 * 1024 * 1024     # 512MB
_MAX_ZIP_BYTES: Final[int] = 256 * 1024 * 1024       # 256MB archive upload
_MAX_ZIP_ENTRIES: Final[int] = 2000
_MAX_ZIP_MEDIA_FILES: Final[int] = 2000
_MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES: Final[int] = 1024 * 1024 * 1024  # 1GB
_MAX_ZIP_COMPRESSION_RATIO: Final[float] = 100.0


@dataclass(frozen=True)
class _PreparedMedia:
    """A local media file ready to enqueue."""

    path: Path
    filename: str
    content_type: str
    source: str


def _resolve_upload_channel_id() -> int:
    """Read the target #x-upload channel ID from env."""
    raw = os.environ.get("X_POSTER_UPLOAD_CHANNEL_ID", "")
    if raw:
        return int(raw)
    return 0


def _resolve_dashboard_channel_id() -> int:
    """Read the #x-dashboard channel ID from env."""
    raw = os.environ.get("X_POSTER_DASHBOARD_CHANNEL_ID", "")
    if raw:
        return int(raw)
    return 0


async def on_x_upload_message(message: discord.Message) -> None:
    """Handle ``on_message`` for X Poster media uploads.

    Guards:
      - Only process in configured #x-upload channel.
      - Skip bot messages.
      - Skip messages without attachments.
    
    Batches up to 4 attachments from the same message into 1 post (1 tweet with 4 media).
    """
    # ── Channel guard ─────────────────────────────────────────────────
    channel = message.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return

    target_channel_id = _resolve_upload_channel_id()
    if target_channel_id and channel.id != target_channel_id:
        return

    # ── Bot guard ─────────────────────────────────────────────────────
    if message.author.bot:
        return

    # ── Attachment guard ─────────────────────────────────────────────
    if not message.attachments:
        return

    logger.info(
        "x_poster.upload_received",
        message_id=message.id,
        author_id=message.author.id,
        attachment_count=len(message.attachments),
    )

    # Group attachments into batches of 4 for multi-media tweets
    batch_size = 4
    attachments = list(message.attachments)
    
    for i in range(0, len(attachments), batch_size):
        batch = attachments[i:i + batch_size]
        await _process_attachment_batch(message, batch)


async def _process_attachment_batch(message: discord.Message, attachments: list[discord.Attachment]) -> None:
    """Validate, download, and enqueue a batch of attachments (up to 4) as 1 post."""
    valid_media: list[_PreparedMedia] = []
    temp_paths: list[Path] = []

    try:
        for attachment in attachments:
            content_type = attachment.content_type or ""
            filename = attachment.filename

            if _is_zip_attachment(filename, content_type):
                # ZIP handled separately - process immediately
                await _process_zip_attachment(message, attachment)
                continue

            if not _is_allowed_media(filename, content_type):
                await _reject_attachment(
                    message,
                    attachment,
                    "x_poster.upload_rejected_type",
                    f"Tipe file tidak didukung: `{content_type or 'unknown'}`",
                    content_type=content_type,
                )
                continue

            if not _validate_attachment_size(message, attachment, content_type):
                continue

            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{_safe_display_name(filename)}") as tmp:
                temp_path = Path(tmp.name)
                temp_paths.append(temp_path)
                await attachment.save(temp_path)

            media = _PreparedMedia(
                path=temp_path,
                filename=filename,
                content_type=_normalize_media_content_type(filename, content_type),
                source="attachment",
            )
            valid_media.append(media)

        if not valid_media:
            return

        # Enqueue batch
        result = await _enqueue_media_batch(message, valid_media, caption_hint=message.content or "")
        await _handle_enqueue_success(message, result, source="attachment_batch")

    except httpx.HTTPStatusError as exc:
        await _handle_http_error(message, exc)
    except Exception as exc:
        await _handle_unexpected_error(message, exc)
    finally:
        for temp_path in temp_paths:
            if temp_path and temp_path.exists():
                _safe_unlink(temp_path)


async def _process_single_attachment(message: discord.Message, attachment: discord.Attachment) -> None:
    """Validate, download, expand if needed, and enqueue one attachment (legacy)."""
    content_type = attachment.content_type or ""
    filename = attachment.filename

    if _is_zip_attachment(filename, content_type):
        await _process_zip_attachment(message, attachment)
        return

    if not _is_allowed_media(filename, content_type):
        await _reject_attachment(
            message,
            attachment,
            "x_poster.upload_rejected_type",
            f"Tipe file tidak didukung: `{content_type or 'unknown'}`",
            content_type=content_type,
        )
        return

    if not _validate_attachment_size(message, attachment, content_type):
        return

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{_safe_display_name(filename)}") as tmp:
            temp_path = Path(tmp.name)
            await attachment.save(temp_path)

        media = _PreparedMedia(
            path=temp_path,
            filename=filename,
            content_type=_normalize_media_content_type(filename, content_type),
            source="attachment",
        )
        result = await _enqueue_media(message, media, caption_hint=message.content or "")
        await _handle_enqueue_success(message, result, source="attachment")

    except httpx.HTTPStatusError as exc:
        await _handle_http_error(message, exc)
    except Exception as exc:
        await _handle_unexpected_error(message, exc)
    finally:
        if temp_path and temp_path.exists():
            _safe_unlink(temp_path)


async def _process_zip_attachment(message: discord.Message, attachment: discord.Attachment) -> None:
    """Download, securely extract, validate, and enqueue media from a ZIP bundle."""
    if attachment.size > _MAX_ZIP_BYTES:
        limit_mb = _MAX_ZIP_BYTES / (1024 * 1024)
        await _reject_attachment(
            message,
            attachment,
            "x_poster.zip_rejected_size",
            f"ZIP melebihi batas {limit_mb:.0f}MB.",
            size_mb=attachment.size / (1024 * 1024),
            limit_mb=limit_mb,
        )
        return

    zip_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{_safe_display_name(attachment.filename)}") as tmp:
            zip_path = Path(tmp.name)
            await attachment.save(zip_path)

        with tempfile.TemporaryDirectory(prefix="x-upload-zip-") as extract_dir:
            media_files = _extract_zip_media(zip_path, Path(extract_dir), attachment.filename)
            if not media_files:
                logger.warning(
                    "x_poster.zip_no_supported_media",
                    message_id=message.id,
                    filename=attachment.filename,
                )
                _ = await message.add_reaction("❌")
                await _send_error_embed(
                    message,
                    "ZIP tidak berisi media yang didukung. Gunakan JPG/PNG/GIF/WebP/MP4/MOV/WebM.",
                )
                return

            # Group media into batches of 4 for batch enqueue
            batch_size = 4
            batches = [media_files[i:i + batch_size] for i in range(0, len(media_files), batch_size)]
            
            successes: list[dict[str, object]] = []
            for batch in batches:
                result = await _enqueue_media_batch(message, batch, caption_hint=message.content or "")
                successes.append(result)

            logger.info(
                "x_poster.zip_enqueued",
                message_id=message.id,
                filename=attachment.filename,
                media_count=len(media_files),
                batch_count=len(batches),
            )
            _ = await message.add_reaction("✅")
            await _send_zip_success_embed(message, attachment.filename, successes)

    except zipfile.BadZipFile:
        logger.warning(
            "x_poster.zip_rejected_invalid",
            message_id=message.id,
            filename=attachment.filename,
        )
        _ = await message.add_reaction("❌")
        await _send_error_embed(message, "ZIP tidak valid atau corrupt.")
    except ValueError as exc:
        logger.warning(
            "x_poster.zip_rejected_security",
            message_id=message.id,
            filename=attachment.filename,
            error=str(exc),
        )
        _ = await message.add_reaction("❌")
        await _send_error_embed(message, str(exc))
    except httpx.HTTPStatusError as exc:
        await _handle_http_error(message, exc)
    except Exception as exc:
        await _handle_unexpected_error(message, exc)
    finally:
        if zip_path and zip_path.exists():
            _safe_unlink(zip_path)


def _extract_zip_media(zip_path: Path, extract_root: Path, archive_name: str) -> list[_PreparedMedia]:
    """Safely extract supported media files from a ZIP archive."""
    media: list[_PreparedMedia] = []
    total_uncompressed = 0

    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > _MAX_ZIP_ENTRIES:
            raise ValueError(f"ZIP berisi terlalu banyak file: {len(infos)} > {_MAX_ZIP_ENTRIES}.")

        for info in infos:
            if info.is_dir():
                continue

            member_name = info.filename
            _validate_zip_member_path(member_name)
            total_uncompressed += info.file_size
            if total_uncompressed > _MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES:
                limit_mb = _MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES / (1024 * 1024)
                raise ValueError(f"Total isi ZIP melebihi batas {limit_mb:.0f}MB.")

            compressed_size = max(info.compress_size, 1)
            if info.file_size / compressed_size > _MAX_ZIP_COMPRESSION_RATIO:
                raise ValueError(f"ZIP entry `{member_name}` terlihat seperti zip bomb.")

            content_type = _content_type_from_filename(member_name)
            if content_type is None:
                logger.info(
                    "x_poster.zip_skipped_unsupported_entry",
                    archive=archive_name,
                    member=member_name,
                )
                continue

            _validate_media_size(member_name, info.file_size, content_type)

            if len(media) >= _MAX_ZIP_MEDIA_FILES:
                raise ValueError(f"ZIP berisi terlalu banyak media: > {_MAX_ZIP_MEDIA_FILES}.")

            target_path = _safe_extract_path(extract_root, member_name)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target_path.open("wb") as target:
                copied = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > info.file_size:
                        raise ValueError(f"Ukuran ekstraksi `{member_name}` tidak valid.")
                    target.write(chunk)

            media.append(
                _PreparedMedia(
                    path=target_path,
                    filename=Path(member_name).name,
                    content_type=content_type,
                    source=f"zip:{archive_name}",
                )
            )

    return media


def _validate_zip_member_path(member_name: str) -> None:
    """Reject absolute paths, traversal, and nested archives."""
    normalized = member_name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"ZIP mengandung path tidak aman: `{member_name}`.")
    if pure.name.startswith(".") or not pure.name:
        raise ValueError(f"ZIP mengandung nama file tidak aman: `{member_name}`.")
    if pure.suffix.lower() == ".zip":
        raise ValueError("Nested ZIP tidak didukung demi keamanan.")


def _safe_extract_path(root: Path, member_name: str) -> Path:
    """Resolve an extraction target and ensure it remains under root."""
    target = (root / member_name.replace("\\", "/")).resolve()
    root_resolved = root.resolve()
    if root_resolved not in target.parents:
        raise ValueError(f"ZIP mengandung path tidak aman: `{member_name}`.")
    return target


async def _enqueue_media(
    message: discord.Message,
    media: _PreparedMedia,
    *,
    caption_hint: str,
) -> dict[str, object]:
    """POST one prepared media file to the x_poster enqueue endpoint."""
    url = f"{_XPOSTER_API_BASE}/api/enqueue"
    data = {
        "filename": media.filename,
        "content_type": media.content_type,
        "author_id": str(message.author.id),
        "message_id": str(message.id),
        "caption_hint": caption_hint,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        with media.path.open("rb") as f:
            files = {"file": (media.filename, f, media.content_type)}
            response = await client.post(url, data=data, files=files)
            _ = response.raise_for_status()
            result = response.json()

    if not result.get("ok"):
        raise RuntimeError(str(result.get("error", "Unknown API error")))
    return dict(result)


async def _enqueue_media_batch(
    message: discord.Message,
    media_list: list[_PreparedMedia],
    *,
    caption_hint: str,
) -> dict[str, object]:
    """POST multiple media files to the x_poster batch enqueue endpoint."""
    url = f"{_XPOSTER_API_BASE}/api/enqueue-batch"
    data = {
        "author_id": str(message.author.id),
        "message_id": str(message.id),
        "caption_hint": caption_hint,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        files = []
        for i, media in enumerate(media_list):
            f = media.path.open("rb")
            files.append((f"file_{i}", (media.filename, f, media.content_type)))
        
        try:
            response = await client.post(url, data=data, files=files)
            _ = response.raise_for_status()
            result = response.json()
        finally:
            for _, (_, f, _) in files:
                f.close()

    if not result.get("ok"):
        raise RuntimeError(str(result.get("error", "Unknown API error")))
    return dict(result)


async def _handle_enqueue_success(
    message: discord.Message,
    result: dict[str, object],
    *,
    source: str,
) -> None:
    """React and send temporary success notification for one enqueue result."""
    post_id = str(result.get("post_id", "unknown"))
    scheduled_slot = result.get("scheduled_slot")
    scheduled_slot_str = str(scheduled_slot) if scheduled_slot else None

    logger.info(
        "x_poster.upload_enqueued",
        message_id=message.id,
        post_id=post_id,
        scheduled_slot=scheduled_slot_str,
        source=source,
    )
    _ = await message.add_reaction("✅")
    await _send_success_embed(message, post_id, scheduled_slot_str)


async def _reject_attachment(
    message: discord.Message,
    attachment: discord.Attachment,
    event_name: str,
    user_message: str,
    **log_fields: object,
) -> None:
    """Log, react, and send a temporary rejection embed."""
    logger.warning(
        event_name,
        message_id=message.id,
        filename=attachment.filename,
        size=getattr(attachment, "size", None),
        **log_fields,
    )
    _ = await message.add_reaction("❌")
    await _send_error_embed(message, user_message)


def _validate_attachment_size(
    message: discord.Message,
    attachment: discord.Attachment,
    content_type: str,
) -> bool:
    """Validate Discord attachment size before download."""
    is_video = content_type.startswith("video/")
    max_bytes = _MAX_VIDEO_BYTES if is_video else _MAX_PHOTO_BYTES
    if attachment.size <= max_bytes:
        return True

    limit_mb = max_bytes / (1024 * 1024)
    logger.warning(
        "x_poster.upload_rejected_size",
        message_id=message.id,
        filename=attachment.filename,
        size_mb=attachment.size / (1024 * 1024),
        limit_mb=limit_mb,
    )
    return False


def _validate_media_size(filename: str, file_size: int, content_type: str) -> None:
    """Validate extracted media file size."""
    is_video = content_type.startswith("video/")
    max_bytes = _MAX_VIDEO_BYTES if is_video else _MAX_PHOTO_BYTES
    if file_size > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise ValueError(f"File `{filename}` melebihi batas {limit_mb:.0f}MB.")


def _is_zip_attachment(filename: str, content_type: str) -> bool:
    """Return True if an attachment should be treated as ZIP."""
    return content_type in _ZIP_CONTENT_TYPES or Path(filename).suffix.lower() == ".zip"


def _is_allowed_media(filename: str, content_type: str) -> bool:
    """Return True if a direct attachment is an allowed media file."""
    normalized = _normalize_media_content_type(filename, content_type)
    return normalized in _ALLOWED_CONTENT_TYPES


def _normalize_media_content_type(filename: str, content_type: str) -> str:
    """Prefer trusted allowlisted content type, fallback to extension mapping."""
    if content_type in _ALLOWED_CONTENT_TYPES:
        return content_type
    guessed = _content_type_from_filename(filename)
    if guessed is not None:
        return guessed
    return content_type


def _content_type_from_filename(filename: str) -> str | None:
    """Resolve supported media content type from filename extension."""
    suffix = Path(filename).suffix.lower()
    if suffix in _ALLOWED_EXTENSIONS:
        return _ALLOWED_EXTENSIONS[suffix]
    guessed, _ = mimetypes.guess_type(filename)
    if guessed in _ALLOWED_CONTENT_TYPES:
        return guessed
    return None


def _safe_display_name(filename: str) -> str:
    """Return a basename-only filename safe for temp suffix usage."""
    name = Path(filename.replace("\\", "/")).name
    return name or "upload.bin"


def _safe_unlink(path: Path) -> None:
    """Best-effort temp-file cleanup."""
    try:
        path.unlink()
    except OSError:
        logger.warning("x_poster.temp_cleanup_failed", path=str(path))


async def _handle_http_error(message: discord.Message, exc: httpx.HTTPStatusError) -> None:
    """Handle HTTP failures from x_poster API."""
    logger.warning(
        "x_poster.upload_api_http_error",
        message_id=message.id,
        status=exc.response.status_code,
        body=exc.response.text[:300],
    )
    _ = await message.add_reaction("❌")
    await _send_error_embed(message, f"API error: {exc.response.status_code}")


async def _handle_unexpected_error(message: discord.Message, exc: Exception) -> None:
    """Handle unexpected upload failures."""
    logger.exception(
        "x_poster.upload_error",
        message_id=message.id,
        error=str(exc),
    )
    _ = await message.add_reaction("❌")
    await _send_error_embed(message, f"Terjadi kesalahan: {str(exc)}")


async def _send_success_embed(message: discord.Message, post_id: str, scheduled_slot: str | None) -> None:
    """Send temporary success embed after enqueueing for scheduled posting."""
    ts = now_wib_str()
    fields: list[EmbedField] = [
        EmbedField(name="Post ID", value=f"`{post_id}`", inline=True),
    ]
    if scheduled_slot:
        fields.append(EmbedField(name="Jadwal Post", value=f"`{scheduled_slot}`", inline=False))
    data_obj = EmbedData(
        title="✅ Media Berhasil Diunggah",
        description="File telah divalidasi dan ditambahkan ke antrean posting.",
        color=SUCCESS,
        fields=tuple(fields),
        timestamp=ts,
    )
    await _send_temporary_embed(message, data_obj)


async def _send_zip_success_embed(
    message: discord.Message,
    archive_name: str,
    results: Iterable[dict[str, object]],
) -> None:
    """Send one temporary success embed for a ZIP upload batch."""
    result_list = list(results)
    fields = [
        EmbedField(name="ZIP", value=f"`{archive_name}`", inline=False),
        EmbedField(name="Media valid", value=str(len(result_list)), inline=True),
    ]
    first_slot = next(
        (str(result.get("scheduled_slot")) for result in result_list if result.get("scheduled_slot")),
        None,
    )
    if first_slot:
        fields.append(EmbedField(name="Slot pertama", value=f"`{first_slot}`", inline=False))

    data_obj = EmbedData(
        title="✅ ZIP Berhasil Diproses",
        description="Media valid di dalam ZIP telah ditambahkan ke antrean posting.",
        color=SUCCESS,
        fields=tuple(fields),
        timestamp=now_wib_str(),
    )
    await _send_temporary_embed(message, data_obj)


async def _send_error_embed(message: discord.Message, error_msg: str) -> None:
    """Send temporary error embed after failed upload."""
    data_obj = EmbedData(
        title="❌ Upload Gagal",
        description=error_msg,
        color=WARNING,
        timestamp=now_wib_str(),
    )
    await _send_temporary_embed(message, data_obj)


async def _send_temporary_embed(message: discord.Message, data_obj: EmbedData) -> None:
    """Send a temporary notification to #x-dashboard (auto-deletes after 60s).

    Falls back to the original upload channel if the dashboard channel is not
    configured or cannot be resolved.
    """
    target_channel: discord.TextChannel | discord.Thread | None = None

    dashboard_id = _resolve_dashboard_channel_id()
    if dashboard_id:
        guild = getattr(message.channel, "guild", None)
        if guild is not None:
            fetched = guild.get_channel(dashboard_id)
            if isinstance(fetched, (discord.TextChannel, discord.Thread)):
                target_channel = fetched

    # Fallback to original channel if dashboard not found
    if target_channel is None:
        ch = message.channel
        if isinstance(ch, (discord.TextChannel, discord.Thread)):
            target_channel = ch

    if target_channel is None:
        return

    await target_channel.send(
        embed=cast(Any, to_discord_embed(data_obj)),
        delete_after=_NOTIFICATION_DELETE_AFTER_SECONDS,
    )


__all__ = ["on_x_upload_message"]
