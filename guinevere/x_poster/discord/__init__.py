"""Discord integration for the X Auto Poster (Phase 13).

Exports:
- ``on_x_upload_message`` — handler for ``#x-upload`` media uploads
- ``create_dashboard`` — factory for the auto-updating ``#x-dashboard`` embed
- ``x_list_callback`` — ``/x-list`` slash command
- ``x_status_callback`` — ``/x-status`` slash command
- ``x_cancel_callback`` — ``/x-cancel`` slash command
- ``x_hold_callback`` — ``/x-hold`` slash command
- ``x_resume_callback`` — ``/x-resume`` slash command
- ``x_retry_failed_callback`` — ``/x-retry-failed`` slash command
- ``x_dryrun_callback`` — ``/x-dryrun`` slash command
"""

from .upload_handler import on_x_upload_message
from .dashboard import create_dashboard
from .commands import (
    x_list_callback,
    x_status_callback,
    x_cancel_callback,
    x_hold_callback,
    x_resume_callback,
    x_retry_failed_callback,
    x_dryrun_callback,
)

__all__ = [
    "on_x_upload_message",
    "create_dashboard",
    "x_list_callback",
    "x_status_callback",
    "x_cancel_callback",
    "x_hold_callback",
    "x_resume_callback",
    "x_retry_failed_callback",
    "x_dryrun_callback",
]
