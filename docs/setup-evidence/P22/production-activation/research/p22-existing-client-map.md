# P22 Existing-Client Map

**Audit date:** 2026-06-27
**Purpose:** Map each of the 13 P22 adapters to the existing in-tree client (or `None` if no client exists yet), so that `build_default_registry(...)` can be wired to real objects instead of `None`.

For every adapter:
- **adapter secret_refs** (from `secret_refs=("…",)` in the adapter's `__init__`)
- **adapter constructor param** (the kwarg name in `build_default_registry`)
- **in-tree class** to pass for that param (or "NONE — must be created" if no client exists in the repo)
- **import path**
- **library dependency** (pip package + version present in venv)
- **health-check method** the adapter calls (if any)
- **notes** on what to do for production activation

---

## 1. Discord — `discord`
- **secret_refs:** `("sec-discord-bot",)`
- **build param:** `discord_rest_client`
- **in-tree class:** `src.life_kernel.discord_rest_client.DiscordRestClient`
- **import:** `from src.life_kernel.discord_rest_client import DiscordRestClient`
- **library:** `httpx 0.28.1` (the REST client uses `httpx`; the `discord.py` 2.7.1 package is also present but NOT used by `DiscordRestClient`)
- **health_check method expected:** `await rest_client.health() -> bool` (adapter uses `hasattr(self._rest_client, "health")`); `DiscordRestClient` exposes this.
- **production note:** Pass an already-instantiated `DiscordRestClient(token=...)` (token loaded via `EnvSecretProvider` from `DISCORD_BOT_TOKEN` or via SOPS `discord_bot_token`).

## 2. Gmail — `gmail`
- **secret_refs:** `("sec-gmail-oauth",)`
- **build param:** `gmail_service`
- **in-tree class:** `src.gmail.client.AsyncGmailClient` (note: NOT `GmailService`; the adapter's param is called `gmail_service` for naming, but the class is `AsyncGmailClient`).
- **import:** `from src.gmail.client import AsyncGmailClient`
- **library:** `google-api-python-client` (MISSING locally; present on VPS in `guinevere-gmail.service` runtime), `google-auth` (same).
- **health_check method expected:** `await gmail_service.health() -> bool`
- **production note:** Module import fails on local Windows venv because `google.oauth2.credentials` is not installed. VPS runtime has the libs. Do NOT flip to ACTIVE on local; verify VPS venv first, then wire `AsyncGmailClient` from `src/gmail/client.py`.

## 3. GitHub — `github`
- **secret_refs:** `("sec-github-pat",)`
- **build param:** `github_client`
- **in-tree class:** `src.mcp.tools.github.GitHubClient` (the file `src/mcp/tools/github.py` registers MCP tools; it has an internal `GitHubClient` class).
- **import:** `from src.mcp.tools.github import GitHubClient`
- **library:** `httpx 0.28.1` (used by the in-tree client; PyGithub is NOT installed and NOT required).
- **health_check method expected:** `await github_client.check_auth() -> bool` (adapter uses `hasattr` check)
- **production note:** VPS `.env.mcp` already has `GITHUB_PAT`. Pass a `GitHubClient` constructed with the PAT loaded from `EnvSecretProvider` (default fallback name `GITHUB_PAT`).

## 4. Calendar — `calendar`
- **secret_refs:** `("sec-google-calendar-oauth",)`
- **build param:** `calendar_client`
- **in-tree class:** **NONE — must be created.** No Google Calendar client exists in the repo.
- **import:** n/a
- **library:** `google-api-python-client` (MISSING locally).
- **production note:** Adapter is honest — when `calendar_client=None`, `health_check` returns `IntegrationHealth.UNKNOWN` and `execute_action` raises `ConfigurationMissingError`. Activation requires: (1) install `google-api-python-client`, (2) create `src/life_integrations/adapters/_clients/google_calendar_client.py` (or similar), (3) provision `sec-google-calendar-oauth` via ProjectVault or env.

## 5. Drive — `drive`
- **secret_refs:** `("sec-google-drive-oauth",)`
- **build param:** `drive_client`
- **in-tree class:** **NONE — must be created.**
- **import:** n/a
- **library:** `google-api-python-client` (MISSING).
- **production note:** Same as calendar. The adapter's `trash_file` implements the trash-first policy; that must be preserved in the new client.

## 6. Notion — `notion`
- **secret_refs:** `("sec-notion-integration-token",)`
- **build param:** `notion_client`
- **in-tree class:** **NONE — must be created.**
- **import:** n/a
- **library:** `notion-client` (MISSING).
- **production note:** Adapter is honest; `archive_page` is the soft-delete (restorable via `in_trash:false`); `delete_view` is L4 forbidden. A new Notion client must mirror the `archive_page` semantics.

## 7. Telegram — `telegram`
- **secret_refs:** `("sec-telegram-bot-token",)`
- **build param:** `telegram_client`
- **in-tree class:** **NONE — must be created.**
- **import:** n/a
- **library:** `python-telegram-bot` (MISSING).
- **production note:** Adapter is honest. A `TelegramBot` wrapper exposing `get_updates()`, `send_message(chat_id, text)`, `delete_message()`, `ban_member()` (L3) needs to be created.

## 8. WhatsApp — `whatsapp`
- **secret_refs:** `("sec-baileys-session",)`
- **build param:** `whatsapp_adapter`
- **in-tree class:** `src.channels.whatsapp.adapter.WhatsAppIngressEgressAdapter`
- **import:** `from src.channels.whatsapp import WhatsAppIngressEgressAdapter`
- **library:** `neonize 0.3.18` (PRESENT).
- **health_check method expected:** `await whatsapp_adapter.health() -> bool`
- **production note:** VPS `guinevere-whatsapp.service` is `active`. `/opt/guinevere/.env.whatsapp` is `perm-denied` in this audit; before flipping to ACTIVE, the operator must re-verify session linkage. The `WhatsAppIngressEgressAdapter` already exposes `send_message(jid, text)` and `delete_message(jid, key)` which match the adapter's `execute_action` calls.

## 9. VPS — `vps`
- **secret_refs:** `("sec-postgres-core", "sec-redis-auth")`
- **build params:** `vps_docker_client`, `vps_shell_client`
- **in-tree classes:**
  - `src.mcp.tools.docker_tool.DockerTool` (shells out to `docker` CLI via `asyncio.create_subprocess_exec`)
  - `src.mcp.tools.shell_tool.ShellTool` (whitelisted shell exec via `asyncio.create_subprocess_exec`)
- **imports:**
  - `from src.mcp.tools.docker_tool import DockerTool`
  - `from src.mcp.tools.shell_tool import ShellTool`
- **library:** `psutil 7.2.2` (PRESENT, used directly by `vps_adapter._get_health_metrics`); the `docker` PyPI SDK is MISSING but not needed because `DockerTool` shells out.
- **health_check:** the adapter's `health_check` returns `OK` if either client is non-None; no `health()` method called.
- **production note:** Always-ACTIVE for read paths (`health_metrics` uses only `psutil`, no secret). For write paths (`restart_service`), the adapter's `_validate_service_name` enforces the systemd allowlist; the L3 gate additionally protects stateful services (postgres/redis/pgbouncer). Note: VPS env files do NOT expose a bare `POSTGRES_PASSWORD`; the `sec-postgres-core` is sourced from `secrets/db-passwords.yaml` (SOPS) or baked into `DATABASE_URL` strings — the `vps_adapter` does not need a Postgres client directly; it only needs docker/shell clients for ops.

## 10. Finance — `finance`
- **secret_refs:** `("sec-postgres-core",)`
- **build param:** `finance_mind`
- **in-tree class:** `src.life_kernel.domain_minds.finance_mind.FinanceMind`
- **import:** `from src.life_kernel.domain_minds.finance_mind import FinanceMind`
- **library:** stdlib + `asyncpg` (PRESENT). NO `polars` / `pandas` required (FinanceMind is pure Python in v1).
- **health_check:** adapter's `health_check` returns `OK` if `_mind is not None`; no `health()` method called.
- **production note:** Wire `FinanceMind` with a `database_url` loaded from `EnvSecretProvider` (fallback name `POSTGRES_CORE` — but the canonical pattern is to pass the URL via `DatabaseURL` config). The adapter's `_BLOCKED_ACTIONS` regex pre-blocks `pay/transfer/withdraw/invest/trade` BEFORE the gate, so the FinanceMind never sees them.

## 11. Browser — `browser`
- **secret_refs:** `("sec-brave-api", "sec-exa-api")`
- **build params:** `browser_search`, `browser_fetch`, `browser_cdp`
- **in-tree classes:**
  - `browser_search` -> `src.mcp.tools.brave_search.BraveSearchTool` (uses httpx; falls back to Exa via `src.mcp.tools.exa_search.ExaSearchTool`)
  - `browser_fetch` -> `src.mcp.tools.fetch.FetchTool`
  - `browser_cdp` -> `src.mcp.tools.obscura_cdp.ObscuraCDPTool` (uses Playwright over CDP)
- **imports:**
  - `from src.mcp.tools.brave_search import BraveSearchTool`
  - `from src.mcp.tools.fetch import FetchTool`
  - `from src.mcp.tools.obscura_cdp import ObscuraCDPTool`
- **library:** `httpx 0.28.1`, `markdownify 1.2.2`, `playwright 1.60.0`, `tenacity 9.1.4` (all PRESENT).
- **health_check:** adapter's `health_check` returns `OK` if any of the three is non-None; no `health()` method called.
- **production note:** VPS `.env.mcp` already has `BRAVE_API_KEY` and `EXA_API_KEY`. The adapter's actions are: `search(query) -> results`, `fetch(url) -> content`, `navigate(url) -> None`. Ensure `ObscuraCDPTool` is wired to the same CDP endpoint as `guinevere-obscura.service`.

## 12. Memory — `memory`
- **secret_refs:** `("sec-postgres-core",)`
- **build params:** `memory_write_pipeline`, `memory_read_pipeline`, `kg_engine`
- **in-tree objects (the adapter calls module-level FUNCTIONS, not classes):**
  - `memory_write_pipeline` -> the `store_episode` function in `src.memory.write_pipeline` (and `store_episode_batch`)
  - `memory_read_pipeline` -> the `recall_memories` function in `src.memory.read_pipeline`
  - `kg_engine` -> `src.knowledge_graph.query.engine.KGQueryEngine`
- **imports / wiring patterns:**
  - For the pipelines, the adapter calls `await self._write.store_episode(content=…, classification=…, project_id=…)` and `await self._read.recall_memories(query=…, limit=…, project_id=…)`. The current `src.memory.write_pipeline` / `src.memory.read_pipeline` modules are organized around Protocol types and module-level functions; the simplest wiring is to wrap them in small adapter-shim classes that expose `.store_episode(...)`, `.recall_memories(...)` and forward to the in-tree code. Existing tests and modules already call these as `await store_episode(...)` so a thin shim will be one-liner.
  - `kg_engine` -> `from src.knowledge_graph.query.engine import KGQueryEngine; kg = KGQueryEngine(...); adapter calls `await kg.query(query, project_id=...)`.
- **library:** `asyncpg 0.31.0`, `sqlalchemy 2.0.50`, `pgvector` (PRESENT), `redis 8.0.0` (PRESENT).
- **health_check:** adapter returns `OK` if either pipeline is non-None; no `health()` method called.
- **production note:** Postgres + pgvector + Redis are all up. The `mark_dnr` action (L3) is the only allowed "delete" path; `delete_memory` is L4 forbidden and raises `ActionNotSupportedError` BEFORE the pipeline is invoked. DNR enforcement happens inside `read_pipeline.recall_memories` (P3-010).

## 13. Filesystem — `filesystem`
- **secret_refs:** `()`
- **build param:** `workspace_root` (str path; defaults to `os.getcwd()`)
- **in-tree class:** None — the adapter is self-contained (uses `pathlib`, `subprocess`, `hashlib`).
- **library:** stdlib only.
- **health_check:** checks `workspace.exists()`.
- **production note:** Always-ACTIVE. Pass `workspace_root="/home/guinevere/code/guinevere"` (or appropriate workspace). The `_FORBIDDEN_PATHS` list MUST be kept in sync with the production host's actual forbidden paths.

---

## Summary table (one row per adapter)

| Adapter | build param | in-tree client class | import path | pip dep | ACTIVE? |
|---------|-------------|----------------------|-------------|---------|---------|
| discord | `discord_rest_client` | `DiscordRestClient` | `src.life_kernel.discord_rest_client` | httpx | yes |
| gmail | `gmail_service` | `AsyncGmailClient` | `src.gmail.client` | google-api-python-client (VPS only) | VPS-only |
| github | `github_client` | `GitHubClient` | `src.mcp.tools.github` | httpx | yes |
| calendar | `calendar_client` | NONE | n/a | google-api-python-client (missing) | no |
| drive | `drive_client` | NONE | n/a | google-api-python-client (missing) | no |
| notion | `notion_client` | NONE | n/a | notion-client (missing) | no |
| telegram | `telegram_client` | NONE | n/a | python-telegram-bot (missing) | no |
| whatsapp | `whatsapp_adapter` | `WhatsAppIngressEgressAdapter` | `src.channels.whatsapp.adapter` | neonize 0.3.18 | yes (after re-verify .env.whatsapp) |
| vps | `vps_docker_client`, `vps_shell_client` | `DockerTool`, `ShellTool` | `src.mcp.tools.docker_tool`, `src.mcp.tools.shell_tool` | psutil 7.2.2 (asyncio subprocess) | yes |
| finance | `finance_mind` | `FinanceMind` | `src.life_kernel.domain_minds.finance_mind` | asyncpg | yes |
| browser | `browser_search`, `browser_fetch`, `browser_cdp` | `BraveSearchTool`, `FetchTool`, `ObscuraCDPTool` | `src.mcp.tools.brave_search`, `src.mcp.tools.fetch`, `src.mcp.tools.obscura_cdp` | httpx, playwright, markdownify | yes |
| memory | `memory_write_pipeline`, `memory_read_pipeline`, `kg_engine` | (thin shim around `store_episode`/`recall_memories`) + `KGQueryEngine` | `src.memory.write_pipeline`, `src.memory.read_pipeline`, `src.knowledge_graph.query.engine` | asyncpg, sqlalchemy, pgvector, redis | yes |
| filesystem | `workspace_root` | self-contained | (adapter file) | stdlib | yes |

End of map.
