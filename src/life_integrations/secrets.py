"""P22 secrets access — provider pattern.

Loads secrets via a provider interface (never directly from env/SOPS in
adapter code). Supports SOPS backend and P19 ProjectSecretsVault backend.
Secrets are referenced by name only — never printed, logged, or committed.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Protocol

import structlog
import uuid

logger = structlog.get_logger(__name__)


class SecretProvider(ABC):
    """Abstract secret provider interface.

    Adapters load secrets through this interface, never directly from
    environment variables or SOPS files. This enables fork-internal
    migration (P24) without touching adapter code.
    """

    @abstractmethod
    def get_secret(
        self,
        secret_id: str,
        project_id: uuid.UUID | None = None,
    ) -> str | None:
        """Retrieve a secret by ID.

        Args:
            secret_id: Secret identifier (e.g., "sec-discord-bot").
            project_id: Optional project UUID for project-scoped secrets.

        Returns:
            The secret value, or None if not found.

        Note:
            Never log the returned value. Only use it for authentication.
        """
        ...

    @abstractmethod
    def has_secret(
        self,
        secret_id: str,
        project_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if a secret is available without retrieving it.

        Args:
            secret_id: Secret identifier.
            project_id: Optional project UUID for scoping.

        Returns:
            True if the secret is available, False otherwise.
        """
        ...


class EnvSecretProvider(SecretProvider):
    """Environment variable secret provider.

    Loads secrets from environment variables. Used for local development
    and as fallback. Maps secret_id to env var name.

    Usage:
        provider = EnvSecretProvider({
            "sec-discord-bot": "DISCORD_BOT_TOKEN",
            "sec-github-pat": "GITHUB_PAT",
        })
    """

    def __init__(self, secret_to_env: dict[str, str] | None = None) -> None:
        """Initialize with secret_id to env var mapping.

        Args:
            secret_to_env: Mapping of secret_id to environment variable name.
        """
        self._mapping = secret_to_env or {}

    def get_secret(
        self,
        secret_id: str,
        project_id: uuid.UUID | None = None,
    ) -> str | None:
        env_var = self._mapping.get(secret_id, secret_id.upper().replace("-", "_"))
        value = os.environ.get(env_var, "")
        if not value:
            return None
        return value

    def has_secret(
        self,
        secret_id: str,
        project_id: uuid.UUID | None = None,
    ) -> bool:
        return self.get_secret(secret_id, project_id) is not None


class ProjectVaultSecretProvider(SecretProvider):
    """P19 ProjectSecretsVault-backed secret provider.

    Loads project-scoped secrets from P19's ProjectSecretsVault.
    Falls back to EnvSecretProvider for global secrets.

    Usage:
        provider = ProjectVaultSecretProvider(vault, env_fallback)
    """

    def __init__(
        self,
        vault: Any,
        fallback: SecretProvider | None = None,
    ) -> None:
        """Initialize with P19 vault and optional fallback provider.

        Args:
            vault: ProjectSecretsVault instance (P19).
            fallback: Fallback provider for secrets not in vault.
        """
        self._vault = vault
        self._fallback = fallback

    def get_secret(
        self,
        secret_id: str,
        project_id: uuid.UUID | None = None,
    ) -> str | None:
        if project_id is not None:
            # Extract domain from secret_id (e.g., "sec-discord-bot" -> "discord")
            domain = secret_id.replace("sec-", "").split("-")[0]
            value = self._vault.get(project_id, domain)
            if value:
                return value

        if self._fallback is not None:
            return self._fallback.get_secret(secret_id, project_id)

        return None

    def has_secret(
        self,
        secret_id: str,
        project_id: uuid.UUID | None = None,
    ) -> bool:
        return self.get_secret(secret_id, project_id) is not None


def redact_secret(value: str | None) -> str:
    """Redact a secret value for safe logging.

    Args:
        value: The secret value to redact.

    Returns:
        Redacted string (first 4 chars + asterisks + last 4 chars, or "<none>").
    """
    if value is None:
        return "<none>"
    if len(value) <= 8:
        return "<redacted>"
    return f"{value[:4]}{'*' * 8}{value[-4:]}"
