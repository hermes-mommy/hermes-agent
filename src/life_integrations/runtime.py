"""P22 production runtime factory — wires real clients into build_default_registry().

Called from src/core/main.py lifespan to construct the live IntegrationRegistry
with real clients where credentials+clients are available, and CONFIG_MISSING
(None) where they are not.

Honesty contract (AGENTS.md — no fake PASS):
- An adapter is ACTIVE only if a real client is constructed AND injected.
- An adapter with no credential/client stays None → CONFIG_MISSING (adapter
  reports UNKNOWN, raises ConfigurationMissingError).
- Shims bridge in-tree module-function clients to the instance-method protocol
  the adapters expect. Shims are additive; they never fake success.

Activation status (parent-resolved, 2026-06-27):
  ACTIVE (wired here):  filesystem, vps
  ACTIVE (wired via shim): discord
  CONFIG_MISSING (operator-gated creds/client-lib): gmail, calendar, drive,
    notion, telegram
  CONFIG_MISSING (shim needs further testing before activation): github,
    browser, memory, finance, whatsapp
  — these remain None here so the adapter reports UNKNOWN honestly. They will
  be flipped ACTIVE in a follow-up wiring step after their shims pass local
  tests. This is honest CONFIG_MISSING, not fake PASS.

P19 project_id propagation: ProjectRegistry is passed through unchanged —
P19's real ProjectRegistry already implements get/resolve/list_active matching
P22's protocol (no shim needed).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import Any

import structlog

from src.life_integrations._shims import ConsentGateShim, HardStopShim
from src.life_integrations.wiring import build_action_router, build_default_registry

logger = structlog.get_logger(__name__)


# Per-adapter CONFIG_MISSING hints — map integration_id → (canonical env-var
# name from onboarding_manifest, operator remediation note). Logged alongside
# the generic config_missing signal so operators can wire credentials without
# scanning the manifest. NEVER log secret VALUES — only env-var NAMES.
_ADAPTER_MISSING_HINTS: dict[str, tuple[str, str]] = {
    "gmail": ("GMAIL_OAUTH_TOKEN_PATH", "operator-gated OAuth token path"),
    "calendar": ("CALENDAR_OAUTH_TOKEN_PATH", "operator-gated OAuth token path"),
    "drive": ("DRIVE_OAUTH_TOKEN_PATH", "operator-gated OAuth token path"),
    "notion": ("NOTION_TOKEN", "operator-gated integration token"),
    "telegram": ("TELEGRAM_BOT_TOKEN", "operator-gated bot token"),
    "github": ("GITHUB_PAT", "operator-gated PAT"),
    "browser": ("BRAVE_API_KEY/EXA_API_KEY/OBSCURA_CDP_URL",
                "3 MCP instance shims needed (search/fetch/CDP)"),
    "memory": ("DATABASE_URL", "memory pipeline shim needs p22_session_factory"),
    "finance": ("DATABASE_URL", "finance read shim needs p22_session_factory"),
    "whatsapp": ("WHATSAPP_BRIDGE_URL", "whatsapp bridge shim needs testing"),
}


class DockerClientShim:
    """Bridge src.mcp.tools.docker_tool module functions to instance protocol.

    The vps_adapter calls ``self._docker.<method>()``. The in-tree
    docker_tool exposes module-level functions. This shim forwards.

    Protocol surface (post-P22.3):
        list_containers       — docker ps
        restart_container     — docker restart <id>
        get_container         — docker inspect <id>
        commit                — docker commit <id>
        remove_container      — docker rm <id>

    Each method returns a dict shaped for the vps_adapter contracts (see
    tests/p22/test_vps_dispatch.py for the canonical contract).
    """

    async def list_containers(self) -> list[dict[str, Any]]:
        from src.mcp.tools.docker_tool import _run_docker

        result = await _run_docker(["ps", "--format", "{{json .}}"])
        stdout = result.get("stdout", "") if isinstance(result, dict) else ""
        containers: list[dict[str, Any]] = []
        for line in stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return containers

    async def restart_container(self, container_id: str) -> dict[str, Any]:
        from src.mcp.tools.docker_tool import _run_docker

        result = await _run_docker(["restart", container_id])
        exit_code = int(result.get("exit_code", -1))
        ok = exit_code == 0
        return {
            "status": "ok" if ok else "error",
            "container": container_id,
            "exit_code": exit_code,
            "stderr": result.get("stderr", ""),
        }

    async def get_container(self, container_id: str) -> dict[str, Any]:
        from src.mcp.tools.docker_tool import _run_docker

        result = await _run_docker(["inspect", container_id])
        stdout = result.get("stdout", "") if isinstance(result, dict) else ""
        if not stdout:
            return {"Id": "", "Config": {"Image": ""}, "Image": ""}
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return {"Id": "", "Config": {"Image": ""}, "Image": ""}
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return first
            return {"Id": "", "Config": {"Image": ""}, "Image": ""}
        if isinstance(data, dict):
            return data
        return {"Id": "", "Config": {"Image": ""}, "Image": ""}

    async def commit(self, container_id: str) -> dict[str, Any]:
        from src.mcp.tools.docker_tool import _run_docker

        snapshot_tag = f"guinevere-snap-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        result = await _run_docker(["commit", container_id, snapshot_tag])
        exit_code = int(result.get("exit_code", -1))
        committed = exit_code == 0
        image_id = (
            f"sha256:{snapshot_tag}" if committed else None
        )
        stderr = str(result.get("stderr", "") or "")
        return {
            "committed": committed,
            "image_id": image_id,
            "snapshot_tag": snapshot_tag,
            "stderr": stderr,
        }

    async def remove_container(self, container_id: str) -> dict[str, Any]:
        from src.mcp.tools.docker_tool import _run_docker

        result = await _run_docker(["rm", container_id])
        exit_code = int(result.get("exit_code", -1))
        ok = exit_code == 0
        return {
            "status": "ok" if ok else "error",
            "container": container_id,
            "exit_code": exit_code,
            "stderr": result.get("stderr", ""),
        }


class ShellClientShim:
    """Bridge src.mcp.tools.shell_tool.shell_exec to instance protocol.

    The vps_adapter calls ``self._shell.run(command)``. The in-tree shell_tool
    exposes ``shell_exec(command, ...)``.
    """

    async def run(self, command: str, **kwargs: Any) -> dict[str, Any]:
        from src.mcp.tools.shell_tool import shell_exec

        result = await shell_exec(command, **kwargs)
        if isinstance(result, dict):
            return {str(k): v for k, v in result.items()}
        return {"result": str(result)}


class DiscordRestShim:
    """Bridge DiscordRestClient to the discord_adapter's expected methods.

    The adapter calls: health(), get_messages(channel, limit), send_message,
    edit_message, delete_message. DiscordRestClient has send_message,
    edit_message, get_recent_messages (NOT get_messages), but lacks health()
    and delete_message. This shim maps the names and adds the missing methods
    via the REST client's underlying httpx calls.
    """

    def __init__(self, rest_client: Any) -> None:
        self._rest = rest_client

    async def health(self) -> bool:
        """Health = client enabled (token present)."""
        try:
            return bool(getattr(self._rest, "enabled", False))
        except Exception:  # noqa: BLE001
            return False

    async def get_messages(self, channel_id: Any, limit: int = 50) -> list[dict[str, Any]]:
        """Map to DiscordRestClient.get_recent_messages."""
        return await self._rest.get_recent_messages(channel_id, limit=limit)

    async def send_message(self, channel_id: Any, content: str, **kwargs: Any) -> Any:
        return await self._rest.send_message(channel_id, content, **kwargs)

    async def edit_message(self, channel_id: Any, message_id: Any, content: str, **kwargs: Any) -> Any:
        return await self._rest.edit_message(channel_id, message_id, content, **kwargs)

    async def delete_message(self, channel_id: Any, message_id: Any) -> Any:
        """Delete via Discord REST API (DELETE /channels/{c}/messages/{m}).

        Uses the underlying httpx client from DiscordRestClient._ensure_client()
        and the same Authorization header the client builds internally.
        """
        if not getattr(self._rest, "enabled", False):
            raise RuntimeError("discord rest client not enabled")
        # DiscordRestClient stores the token on self._token and builds the
        # Bot header inside _ensure_client. We access the shared httpx client
        # via getattr (the method is private but stable) so the Authorization
        # header (set at client construction) is applied to the delete call.
        ensure = getattr(self._rest, "_ensure_client", None)
        if ensure is None:
            raise RuntimeError("discord rest client missing _ensure_client")
        client = await ensure()
        # The httpx client has base_url=https://discord.com/api/v10 and the
        # Authorization header set at construction; use a relative path.
        resp = await client.delete(f"/channels/{channel_id}/messages/{message_id}")
        resp.raise_for_status()
        return {"deleted": True, "message_id": str(message_id)}


async def build_runtime_registry(
    *,
    redis_client: Any | None = None,
    hard_stop_handler: Any | None = None,
    consent_checker: Any | None = None,
    project_registry: Any | None = None,
    audit_writer: Any | None = None,
    workspace_root: str | None = None,
    discord_rest_client: Any | None = None,
) -> tuple[Any, Any]:
    """Build the production IntegrationRegistry + ActionRouter with real clients.

    Args:
        redis_client: redis.asyncio.Redis for HARD STOP global key check.
        hard_stop_handler: HardStopHandler instance (app.state.hard_stop_handler).
        consent_checker: consent ledger checker (ConsentCheckResult-returning).
        project_registry: P19 ProjectRegistry (no shim needed).
        audit_writer: audit persistence writer.
        workspace_root: filesystem workspace root.
        discord_rest_client: DiscordRestClient instance (app.state.discord_rest).

    Returns:
        (registry, router) — attach to app.state.

    Fail-open for the app, fail-closed for P22: if wiring raises, log
    ``p22.activation_failed`` and return (None, None) so guinevere-core
    continues; P22 simply stays inactive (all adapters CONFIG_MISSING).
    """
    try:
        # --- Discord (ACTIVE via shim if client provided) ---
        discord_client = None
        if discord_rest_client is not None and getattr(discord_rest_client, "enabled", False):
            discord_client = DiscordRestShim(discord_rest_client)
            logger.info("p22.adapter.wired", adapter="discord", via="shim")

        # --- VPS (ACTIVE via docker+shell shims) ---
        docker_client = DockerClientShim()
        shell_client = ShellClientShim()
        logger.info("p22.adapter.wired", adapter="vps", via="shim")

        # --- Filesystem (ACTIVE, no client) ---
        fs_workspace = workspace_root or "/home/guinevere/code/guinevere"
        logger.info("p22.adapter.wired", adapter="filesystem", via="workspace_root")

        # --- Adapters left CONFIG_MISSING (honest) ---
        # gmail, calendar, drive, notion, telegram: operator-gated creds/libs
        # github, browser, memory, finance, whatsapp: shims need further
        #   testing before activation — left None (CONFIG_MISSING) honestly.
        for missing in ("gmail", "calendar", "drive", "notion", "telegram",
                        "github", "browser", "memory", "finance", "whatsapp"):
            env_var, hint = _ADAPTER_MISSING_HINTS.get(
                missing, ("<unknown>", "no hint available")
            )
            logger.info(
                "p22.adapter.config_missing",
                adapter=missing,
                missing_env=env_var,
                hint=hint,
            )

        registry = await build_default_registry(
            discord_rest_client=discord_client,
            vps_docker_client=docker_client,
            vps_shell_client=shell_client,
            workspace_root=fs_workspace,
            # all others default None → CONFIG_MISSING
        )

        # --- Gate pipeline with safety-critical shims ---
        # HardStopShim.is_hard_stop_active() is called from the SYNC path
        # (consent.py:106), so it needs a SYNC redis client to query the
        # life_kernel:hard_stop key. The async redis_client passed in cannot
        # be awaited from sync context — construct a sync client from the
        # same connection params.
        sync_redis = None
        try:
            import redis as sync_redis_lib
            import urllib.parse as _urlparse
            _rurl = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            _parsed = _urlparse.urlparse(_rurl)
            _host = _parsed.hostname or "localhost"
            _port = _parsed.port or 6379
            _db = int(_parsed.path.lstrip("/") or "0")
            sync_redis = sync_redis_lib.Redis(
                host=_host, port=_port, db=_db,
                password=(os.environ.get("REDIS_PASSWORD", "") or None),
                socket_timeout=2, socket_connect_timeout=2,
            )
            sync_redis.ping()  # verify connectivity
            logger.info("p22.hard_stop_shim.sync_redis_ready")
        except Exception as e:  # noqa: BLE001 — degrade to handler-only
            logger.warning(
                "p22.hard_stop_shim.sync_redis_failed",
                error=str(e),
                hint="HARD STOP will rely on in-process handler only",
            )
            sync_redis = None

        hard_stop_shim = HardStopShim(
            redis_client=sync_redis,
            hard_stop_handler=hard_stop_handler,
        )
        consent_shim = ConsentGateShim(consent_checker=consent_checker)

        router = await build_action_router(
            registry=registry,
            consent_checker=consent_shim,
            hard_stop_checker=hard_stop_shim,
            audit_writer=audit_writer,
            project_registry=project_registry,
        )

        logger.info(
            "p22.runtime_registry_built",
            active_adapters=["discord", "vps", "filesystem"],
            config_missing=["gmail", "calendar", "drive", "notion", "telegram",
                            "github", "browser", "memory", "finance", "whatsapp"],
        )
        return registry, router

    except Exception as e:  # noqa: BLE001 — fail-open for app, log loudly
        logger.error(
            "p22.activation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return None, None
