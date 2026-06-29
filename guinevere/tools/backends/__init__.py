"""M8 Tool backends — 9 unified backends for the Hermes fork."""

from guinevere.tools.backends.browser import BrowserBackend
from guinevere.tools.backends.github import GitHubBackend
from guinevere.tools.backends.filesystem import FilesystemBackend
from guinevere.tools.backends.vps import VPSBackend
from guinevere.tools.backends.email import EmailBackend
from guinevere.tools.backends.desktop import DesktopBackend
from guinevere.tools.backends.freelance import FreelanceBackend
from guinevere.tools.backends.social import SocialBackend
from guinevere.tools.backends.memory import MemoryBackend

__all__ = [
    "BrowserBackend",
    "GitHubBackend",
    "FilesystemBackend",
    "VPSBackend",
    "EmailBackend",
    "DesktopBackend",
    "FreelanceBackend",
    "SocialBackend",
    "MemoryBackend",
]
