from __future__ import annotations

"""P13 X Auto Poster — Caption generator using Hermes bridge."""

from typing import Any
from uuid import UUID

import structlog

from .config import XPosterSettings
from .exceptions import CaptionEmptyError, CaptionGenerationError, CaptionTooLongError
from .metrics import record_caption_generated

logger = structlog.get_logger("x_poster.caption")

_FALLBACK_CAPTION = "Check this out!"
_MAX_CAPTION_LENGTH = 200
_MAX_OVERFLOW_LENGTH = 250


class CaptionGenerator:
    """Generates ~200 character English captions via Hermes bridge.
    
    Captions are generated at queue time for posts. The bridge is expected
    to provide an `invoke_for_caption(prompt)` method, or similar Hermes
    integration pattern.
    """

    def __init__(self, bridge: Any, settings: XPosterSettings) -> None:
        self.bridge = bridge
        self.settings = settings

    async def generate_caption(
        self,
        post_id: UUID,
        media_type: str,
        media_path: str,
    ) -> str:
        """Generate a caption for the given media post.

        Args:
            post_id: The unique identifier of the post.
            media_type: The type of media (e.g. 'photo', 'video').
            media_path: The filesystem path to the media file.

        Returns:
            The generated caption string.

        Raises:
            CaptionEmptyError: If the generated caption is empty or whitespace only.
            CaptionTooLongError: If the generated caption exceeds 250 characters.
        """
        prompt = (
            f"Write a pure text caption in English, max {_MAX_CAPTION_LENGTH} "
            f"characters, no hashtags, for a post with {media_type} media."
        )

        caption = ""
        status = "success"

        try:
            # Call Hermes bridge. We use `invoke_for_caption` if available,
            # otherwise fall back to a generic `generate_caption` pattern.
            if hasattr(self.bridge, "invoke_for_caption"):
                response = await self.bridge.invoke_for_caption(prompt)
            elif hasattr(self.bridge, "generate_caption"):
                response = await self.bridge.generate_caption(prompt=prompt)
            else:
                response = await self.bridge.send_message(
                    user_id=f"x_poster:{post_id}",
                    content=media_path,
                    system_prompt=prompt,
                )

            if not isinstance(response, str):
                response = str(response)

            caption = response.strip()

            if not caption:
                status = "error"
                logger.info(
                    "x_poster.caption.generated",
                    post_id=str(post_id),
                    media_type=media_type,
                    length=0,
                    status=status,
                )
                record_caption_generated(status=status)
                raise CaptionEmptyError(
                    "Generated caption is empty or whitespace only.",
                    context={"post_id": str(post_id), "media_type": media_type},
                )

            if len(caption) > _MAX_OVERFLOW_LENGTH:
                status = "error"
                logger.info(
                    "x_poster.caption.generated",
                    post_id=str(post_id),
                    media_type=media_type,
                    length=len(caption),
                    status=status,
                )
                record_caption_generated(status=status)
                raise CaptionTooLongError(
                    f"Generated caption exceeds maximum allowed length ({len(caption)} > {_MAX_OVERFLOW_LENGTH}).",
                    context={
                        "post_id": str(post_id),
                        "length": len(caption),
                        "max_length": _MAX_OVERFLOW_LENGTH,
                    },
                )

            if len(caption) > _MAX_CAPTION_LENGTH:
                logger.warning(
                    "x_poster.caption.truncated",
                    post_id=str(post_id),
                    original_length=len(caption),
                    truncated_length=_MAX_CAPTION_LENGTH,
                )
                caption = caption[:_MAX_CAPTION_LENGTH]

        except CaptionGenerationError:
            raise
        except Exception as exc:
            status = "error"
            caption = _FALLBACK_CAPTION
            logger.warning(
                "x_poster.caption.bridge_failed",
                post_id=str(post_id),
                media_type=media_type,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            logger.info(
                "x_poster.caption.generated",
                post_id=str(post_id),
                media_type=media_type,
                length=len(caption),
                status=status,
            )
            record_caption_generated(status=status)

        # Only log success if we haven't already logged an error
        if status == "success":
            logger.info(
                "x_poster.caption.generated",
                post_id=str(post_id),
                media_type=media_type,
                length=len(caption),
                status=status,
            )
            record_caption_generated(status=status)

        return caption
