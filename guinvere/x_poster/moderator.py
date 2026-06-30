from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from .config import XPosterSettings
from .exceptions import ModerationError
from .metrics import record_moderation

logger = structlog.get_logger("x_poster.moderation")


@dataclass
class ModerationResult:
    safe: bool
    reason: str


class ContentModerator:
    def __init__(self, bridge: Any, settings: XPosterSettings) -> None:
        self.bridge = bridge
        self.settings = settings

    async def moderate_caption(self, post_id: UUID, caption: str) -> ModerationResult:
        prompt = (
            'Is this caption safe for public posting? Respond with JSON: '
            '{"safe": true/false, "reason": "..."}\n\n'
            f'Caption: {caption}'
        )
        
        try:
            response = await self.bridge.moderate(prompt=prompt)
            
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
                
            safe = bool(response_data.get("safe", False))
            reason = str(response_data.get("reason", "No reason provided"))
            
            result = ModerationResult(safe=safe, reason=reason)
            
            logger.info(
                "x_poster.moderation.caption_checked",
                post_id=str(post_id),
                safe=safe,
                reason=reason
            )
            
            if not safe:
                record_moderation(result="blocked")
                raise ModerationError(f"Caption blocked: {reason}")
                
            record_moderation(result="safe")
            return result
            
        except ModerationError:
            raise
        except Exception as e:
            logger.error(
                "x_poster.moderation.caption_checked",
                post_id=str(post_id),
                error=str(e),
                status="error"
            )
            record_moderation(result="error")
            
            safe = self.settings.moderation_fail_safe
            reason = f"Bridge failed, using fail-safe setting: {e}"
            
            if not safe:
                raise ModerationError(reason)
                
            logger.warning(
                "x_poster.moderation.fail_open",
                post_id=str(post_id),
                reason=reason
            )
            return ModerationResult(safe=safe, reason=reason)
