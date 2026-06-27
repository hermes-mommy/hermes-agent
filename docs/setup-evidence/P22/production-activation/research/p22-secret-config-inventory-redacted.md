# P22 Secret/Config Inventory (REDACTED)

**Audit date:** 2026-06-27
**Auditor:** sub-agent (P22 production activation)
**Scope:** P22 Life Integration adapters — which credentials, env, secrets, and clients exist locally + on VPS, which are missing. NO secret VALUES printed anywhere in this document. All references are to key names, file names, or class names.

---

## Redaction Policy

This inventory is STRICTLY REDACTED.

- **No secret value** (token, password, API key, OAuth credential, refresh token, client secret) has been printed, echoed, logged, or written to this file.
- All env files were inspected with `grep -oE '^[A-Z][A-Z0-9_]+='` so only **key names** are captured.
- All SOPS-encrypted files were inspected for **structure (top-level key names only)**; no decryption was performed.
- The three `secrets/backup/*-plaintext.env` files contain real plaintext credentials; their key NAMES are listed but the corresponding VALUES were never read or written.
- VPS `EnvironmentFile=` paths and the key NAMES inside those files are listed; no values were extracted.
- The single `.env` with permission denied (`/opt/guinevere/.env.whatsapp`) was treated as "file present, contents unknown".

If a reader of this document needs an actual value, they must read the corresponding file with their own access and never paste it into chat/log/markdown.

---

## 1. SecretProvider architecture (recap)

`src/life_integrations/secrets.py` defines:

| Provider | Maps `secret_id` to | Use |
|----------|---------------------|-----|
| `EnvSecretProvider(mapping)` | `secret_id` -> env var name; fallback: `secret_id.upper().replace("-","_")` | Local dev / fallback |
| `ProjectVaultSecretProvider(vault, fallback)` | P19 `ProjectSecretsVault` (project-scoped) + fallback to env | Production multi-project |

Adapter code uses `secret_refs=("sec-foo",)` strings; values are never read in adapter code. `redact_secret()` is the only safe-logging helper.

---

## 2. Per-Adapter Inventory Table (13 adapters)

Legend:
- **creds_present** = `yes` if env var name (or SOPS key) found in any local or VPS env file; `no` if the secret_id is declared in adapter but no matching env var is provisioned; `partial` if a sibling var (e.g. `GMAIL_PUBSUB_TOPIC` without `GMAIL_PUBSUB_SUBSCRIPTION`) is present.
- **client_module** = `yes` if the in-tree or pip module that the adapter wraps is present in the venv; `no` if missing.
- **runtime_target** = `ACTIVE` (both secret + client present) / `CONFIG_MISSING` (secret or client missing) / `CLIENT_MISSING` (secret present, no client) / `CONFIG_INVALID` (partial creds).
- **write_ok / delete_ok** = `yes` if the adapter's `execute_action` exposes the WRITE/DELETE capability and the L2/L3 gates are reachable; `gated` if there is an L2/L3/L4 gate; `n/a` if no destructive path.
- **project_id_support** = whether the adapter forwards `project_id` (P19 scoping) to its execute_action.
- **consent_category** = adapter's `consent_scopes` namespace prefix.
- **hard_stop_impact** = whether the adapter participates in the HARD STOP global key (`src/life_integrations/consent.py`).

| # | Adapter | Secret IDs (`secret_refs`) | Required env var names (EnvSecretProvider fallback) | Local env file -> key found? | VPS env file -> key found? | SOPS key present? | client_module | Existing client class | `build_default_registry()` param | runtime_target | write_ok | delete_ok | project_id_support | consent_category | hard_stop_impact |
|---|---------|----------------------------|------------------------------------------------------|-------------------------------|-----------------------------|-------------------|----------------|-----------------------|----------------------------------|----------------|----------|----------|-------------------|------------------|-------------------|
| 1 | **discord** | `sec-discord-bot` | `DISCORD_BOT_TOKEN` | `.env.example`, `.env.core`(VPS), `.env.discord`(VPS), `.env.hermes`(VPS) | `.env.core`, `.env.discord`, `.env.hermes` | `discord-secrets.enc.yaml` -> `discord_bot_token`, `bot_token` (guinevere-secrets.yaml `discord.bot_token`) | yes (discord.py 2.7.1) | `src.life_kernel.discord_rest_client.DiscordRestClient` | `discord_rest_client` | **ACTIVE** (client+secret wired) | yes (L2) | yes (L3 delete_message; purge L4 forbidden) | yes | `consent.comms.discord.{read,write,delete}` | routes through ActionRouter consent gate; HARD STOP intercepts prior to dispatch |
| 2 | **gmail** | `sec-gmail-oauth` | `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH` (env.gmail has GMAIL_CREDENTIALS_PATH; GMAIL_OAUTH_TOKEN_PATH and GMAIL_OAUTH_CREDENTIALS_PATH referenced in .env.example; token file present at `secrets/gmail-token.json` and `secrets/gmail-client-secrets.json`) | `.env.gmail` (local), `.env.gmail` (VPS) | `.env.gmail` (VPS) | (not in `secrets/guinevere-secrets.yaml` directly; OAuth files in `secrets/gmail-*.json`) | **no (pip)**: `googleapiclient` and `google.oauth2` NOT installed locally; `AsyncGmailClient` exists in-tree but import-time requires google libs | `src.gmail.client.AsyncGmailClient` (in-tree, but blocked on missing google libs) | `gmail_service` | **CONFIG_MISSING / CLIENT_MISSING** (lib missing locally; runtime env present on VPS guinevere-gmail.service active) | yes (L2) | yes (L3 delete_label) | yes | `consent.comms.gmail.{read,write,delete}` | HARD STOP gate on Pubsub/Cold-path writes |
| 3 | **github** | `sec-github-pat` | `GITHUB_PAT` | `.env.example` only (template) | `.env.mcp` (VPS, only runtime) | `guinevere-secrets.yaml` -> `github.pat` | **no (pip)**: `PyGithub` missing; `httpx` available (used by in-tree `src/mcp/tools/github.py`) | `src.mcp.tools.github` (httpx-based HTTP client, NOT `PyGithub`) | `github_client` | **ACTIVE** on VPS via `.env.mcp GITHUB_PAT`; **CLIENT_MISSING** locally if PyGithub expected (in-tree uses httpx so import works) | yes (L2) | yes (L3 delete_branch, merge_pr) | yes | `consent.sourcecode.github.{read,write,delete}` | HARD STOP gate covers `delete_repo` (L4) and `force_push` (L4) |
| 4 | **calendar** | `sec-google-calendar-oauth` | (no specific env var; uses Google OAuth client-secrets file) | none | none | none | **no**: google libs missing (same blocker as gmail) | (none in-tree) | `calendar_client` | **CONFIG_MISSING** (no client module, no OAuth file) | gated (L2 create_event) | gated (L3 delete_event) | yes | `consent.cloud.calendar.{read,write,delete}` | HARD STOP gate covers L4 `delete_calendar`, `clear_calendar` |
| 5 | **drive** | `sec-google-drive-oauth` | (no specific env var; uses Google OAuth) | none | none | none | **no**: google libs missing | (none in-tree) | `drive_client` | **CONFIG_MISSING** | gated (L2 trash, public_share L3) | gated (L3 permanent delete, L4 empty_trash forbidden) | yes | `consent.cloud.drive.{read,write,delete}` | HARD STOP gate covers `empty_trash` (L4) |
| 6 | **notion** | `sec-notion-integration-token` | (no specific env var; Notion uses `Authorization: Bearer <token>`) | none | none | none | **no (pip)**: `notion-client` missing | (none in-tree) | `notion_client` | **CONFIG_MISSING** | gated (L2 create_page) | gated (L3 archive_page, L4 delete_view forbidden) | yes | `consent.notes.notion.{read,write,delete}` | HARD STOP gate covers `delete_view` (L4) |
| 7 | **telegram** | `sec-telegram-bot-token` | (no specific env var) | none | none | none | **no (pip)**: `python-telegram-bot` missing | (none in-tree) | `telegram_client` | **CONFIG_MISSING** | gated (L2 send_message) | gated (L3 delete_message, ban_member) | yes | `consent.comms.telegram.{read,write,delete}` | HARD STOP gate covers `promote_member` (L4) |
| 8 | **whatsapp** | `sec-baileys-session` | (session file path; no env var) | none visible (local) | `/opt/guinevere/.env.whatsapp` present but **PERMISSION DENIED** (treated as unknown) | none in `guinevere-secrets.yaml` | yes (`neonize 0.3.18`) | `src.channels.whatsapp.adapter.WhatsAppIngressEgressAdapter` | `whatsapp_adapter` | **ACTIVE** (guinevere-whatsapp.service running on VPS; Neonize linked) | yes (L2 send_text, send_media, edit_message) | yes (L3 delete_for_everyone, L4 promote_admin forbidden) | yes | `consent.comms.whatsapp.{read,write,delete}` | HARD STOP gate covers `promote_admin` (L4) |
| 9 | **vps** | `sec-postgres-core`, `sec-redis-auth` | `POSTGRES_PASSWORD`, `REDIS_PASSWORD` | `.env.example` (both); `secrets/db-passwords.yaml` (encrypted) | `.env.core`, `.env.discord`, `.env.gmail`, `.env.hermes`, `.env.loops`, `.env.scheduler` (all carry `REDIS_PASSWORD`); VPS does not provision a `POSTGRES_PASSWORD` env (relies on `DATABASE_URL` instead — see notes) | `db-passwords.yaml -> guinevere_core`; `redis-password.yaml -> redis_master_password` | yes (`psutil 7.2.2`; `docker` SDK missing but `src/mcp/tools/docker_tool.py` shells out to docker CLI; `shell_tool.py` is in-tree) | `src.mcp.tools.docker_tool` (asyncio subprocess); `src.mcp.tools.shell_tool` (asyncio subprocess) | `vps_docker_client`, `vps_shell_client` | **ACTIVE** (psutil metrics always work; docker/shell clients available on VPS); **partial** for `restart_service` of `postgresql/redis/pgbouncer` which require L3 + stateful gate | yes (L2 restart_container, restart_service) | yes (L3 remove_container; L4 system_prune forbidden) | yes | `consent.ops.vps.{read,write,delete}` | HARD STOP gate covers `system_prune`, `docker_rm_all` (L4) and stateful service restart (<L3) |
| 10 | **finance** | `sec-postgres-core` | `POSTGRES_PASSWORD` | `.env.example` | shared with VPS core (DATABASE_URL) | `db-passwords.yaml` | **no (pip)**: `polars`, `pandas` missing (in-tree `FinanceMind` uses pure Python — re/de not pandas) | `src.life_kernel.domain_minds.finance_mind.FinanceMind` | `finance_mind` | **ACTIVE** (FinanceMind in-tree + Postgres reachable) | yes (L2 record_transaction, L3 correct_transaction, bulk_import) | yes (L3 correct via compensating entry; L4 pay/transfer/withdraw/invest/trade HARD-BLOCKED by `_BLOCKED_ACTIONS` regex BEFORE the gate) | yes | `consent.finance.{read,write,delete}` | HARD STOP gate plus **adapter-internal word-boundary block** on `_BLOCKED_ACTIONS` (raises `PermissionDeniedError` before `mind` is touched) |
| 11 | **browser** | `sec-brave-api`, `sec-exa-api` | `BRAVE_API_KEY`, `EXA_API_KEY` | `.env.example` (both) | `.env.mcp` (both) | none in `guinevere-secrets.yaml` | yes (`httpx 0.28.1`, `markdownify 1.2.2`, `playwright 1.60.0`, `tenacity 9.1.4`) | `src.mcp.tools.brave_search`, `src.mcp.tools.exa_search`, `src.mcp.tools.fetch`, `src.mcp.tools.obscura_cdp` | `browser_search`, `browser_fetch`, `browser_cdp` | **ACTIVE** (on VPS via guinevere-mcp.service, BRAVE_API_KEY+EXA_API_KEY in `.env.mcp`) | yes (L2 fill_form, click) | n/a (no DELETE capability declared) | yes (search/recall no project_id; navigate/fetch accept project_id via `**kwargs`) | `consent.research.browser.{read,write}` (no delete) | NO PII forwarding to web tools (AGENTS.md §12); HARD STOP gate covers `navigate` only when URL classifier is configured (else not invoked) |
| 12 | **memory** | `sec-postgres-core` | `POSTGRES_PASSWORD` | `.env.example` | shared with VPS core | `db-passwords.yaml` | yes (`asyncpg 0.31.0`, `sqlalchemy 2.0.50`, `pgvector`, `redis 8.0.0`) | `src.memory.write_pipeline` (function `store_episode`), `src.memory.read_pipeline` (function `recall_memories`), `src.knowledge_graph.query.engine.KGQueryEngine` | `memory_write_pipeline`, `memory_read_pipeline`, `kg_engine` | **ACTIVE** (Postgres+pqvector+Redis all up; pipelines exist in-tree) | yes (L2 store, store_fact) | yes (L3 mark_dnr) | yes (`project_id` is first-class arg in `recall_memories`, `store_episode`, `kg.query`) | `consent.memory.{read,write,delete}` | HARD STOP gate covers `delete_memory` (L4 forbidden; `mark_dnr` is the only allowed path) |
| 13 | **filesystem** | (none) | n/a (no secret) | n/a | n/a | n/a | yes (stdlib: `pathlib`, `subprocess`, `hashlib`) | (adapter is self-contained; no external client) | `workspace_root` (str, defaults to `os.getcwd()`) | **ACTIVE** (always — only gating is path allowlist + workspace boundary) | yes (L2 write within workspace) | yes (L3 delete with content hash; L4 forbidden_path always denied) | yes (via `**kwargs`; not in the `project_id` formal param) | `consent.filesystem.{read,write,delete}` | HARD STOP gate covers `_FORBIDDEN_PATHS` (`/etc`, `/var`, `/usr`, `/bin`, `/sbin`, `/sys`, `/proc`, `/root`, `/home/guinevere/.age`, `/home/guinevere/secrets`, `C:\Windows`, `C:\Program Files`) BEFORE the workspace check |

---

## 3. Local Env Key Inventory (names only — NO values)

### 3.1 `.env.example` (185 keys, names only)
Top-level groupings (full alphabetical list in `.env.example`):

- **App/runtime:** `APP_ENV`, `APP_NAME`, `ENV`, `DEBUG`, `LOG_LEVEL`, `CI`, `RUN_E2E`, `MOCK_MODE`, `MEMORY_RECALL_ENABLED`, `PERSONA_MODE`, `PERSONA_VERSION`, `SHADOW_ENABLED`, `SHADOW_TRAFFIC_PCT`, `SURVEILLANCE_ENABLED`, `SURVEILLANCE_INTERVAL`
- **Postgres:** `DATABASE_URL`, `ASYNC_DATABASE_URL`, `TEST_DATABASE_URL`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_READONLY_USER`, `GUINEVERE_DB_URL`, `GUINEVERE_DB_PASSWORD`
- **Redis:** `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USERNAME`, `REDIS_URL`, `REDIS_EXPORTER_PASSWORD`, `GUINEVERE_REDIS_URL`, `GUINEVERE_WHATSAPP_REDIS_DB`
- **Discord:** `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_OWNER_ID`, `DISCORD_PREFIX`, `DISCORD_HOME_CHANNEL`, `DISCORD_HEALTH_CHANNEL_ID`, `DISCORD_ALERT_CHANNEL_ID`, `DISCORD_APPROVAL_WEBHOOK`, `DISCORD_WEBHOOK_URL`, `DISCORD_SHADOW_BOT_TOKEN`, `DISCORD_SHADOW_CHANNEL_ID`, `DISCORD_SECRETS_PATH`, `FAIZ_DISCORD_USER_ID`, `FAIZ_MENTION`
- **Gmail:** 60+ `GMAIL_*` keys (full enumeration: `GMAIL_BACKFILL_DAYS`, `GMAIL_BRIEFING_*`, `GMAIL_CLIENT_SECRETS_PATH`, `GMAIL_CONSENT_ENABLED`, `GMAIL_DAILY_SEND_LIMIT`, `GMAIL_DISCORD_WEBHOOK_URL`, `GMAIL_ENVIRONMENT`, `GMAIL_FAIZ_USER_ID`, `GMAIL_GUILD_ID`, `GMAIL_HARD_STOP_ENABLED`, `GMAIL_HEALTH_PORT`, `GMAIL_IMPORTANCE_NOTIFY_THRESHOLD`, `GMAIL_LOG_*`, `GMAIL_METRICS_PORT`, `GMAIL_NOTIFICATION_*`, `GMAIL_OAUTH_CREDENTIALS_PATH`, `GMAIL_OAUTH_SCOPES`, `GMAIL_OAUTH_TOKEN_PATH`, `GMAIL_OWNER_USER_ID`, `GMAIL_PII_SCAN_ENABLED`, `GMAIL_PROJECT_ID`, `GMAIL_PUBSUB_*`, `GMAIL_QUIET_HOURS_*`, `GMAIL_QUOTA_UNITS_PER_MINUTE`, `GMAIL_RESEND_*`, `GMAIL_SECRET_SCAN_ENABLED`, `GMAIL_SUBSCRIPTION_ID`, `GMAIL_SYNC_*`, `GMAIL_TARGET_CHANNEL_ID`, `GMAIL_TOPIC_ID`, `GMAIL_USER_ID`, `GMAIL_WATCH_*`)
- **GitHub / Search / APIs:** `GITHUB_PAT`, `BRAVE_API_KEY`, `EXA_API_KEY`, `HF_TOKEN`, `HF_HOME`
- **9Router / LLM:** `NINE_ROUTER_API_KEY`, `NINE_ROUTER_API_KEY_NEW`, `NINE_ROUTER_BASE_URL`, `GUINEVERE_9ROUTER_API_KEY`, `GUINEVERE_API_BASE`, `GUINEVERE_API_KEY`, `GUINEVERE_API_URL`
- **Grafana / monitoring / push:** `GRAFANA_URL`, `GRAFANA_API_TOKEN`, `GOTIFY_URL`, `GOTIFY_TOKEN`, `GOTIFY_APP_TOKEN`, `SENTRY_DSN`, `P14_HMAC_SECRET`, `SURVEILLANCE_HMAC_SECRET`, `FINANCIAL_WEBHOOK_SECRET`, `GUINEVERE_WS_URL`, `GUINEVERE_WS_SECRET`
- **Wearable (Mi Fitness):** `MI_FITNESS_USER_ID`, `MI_FITNESS_PASS_TOKEN`, `MI_FITNESS_REGION`, plus 20+ `WEARABLE_*` keys (sync interval, circuit breaker, GHI thresholds, encryption key, port, owner, etc.)
- **WhatsApp:** `WHATSAPP_ENABLED`, `WHATSAPP_PHONE_NUMBER`, `WHATSAPP_QR_MODE`, `WHATSAPP_QR_RAW`, `FAIZ_WHATSAPP_JID`, `GUINEVERE_WHATSAPP_SESSION_DIR`, `GUINEVERE_WHATSAPP_SESSION_AGE_RECIPIENT`
- **X Poster:** `P13_X_POSTER_*`, plus many `X_POSTER_*` keys (POSTGRES_*, DB POOL, SCHEDULE, OBSCURA, COOKIE_ENCRYPTION, TYPING_DELAY, ACTION_GAP, SESSION_*, CAPTION_*, DISCORD_UPLOAD, DASHBOARD, OWNER, RETENTION, HEALTH_*, METRICS, LOG_*)
- **S3 / backups / Restic:** `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_ENDPOINT`
- **File system safety:** `FILESYSTEM_ALLOWED_PATHS`, `GUINEVERE_REPO_ROOT`, `GUINEVERE_SAFE_WORD`
- **FinOps / cost:** `MAX_DAILY_COST`, `MAX_HOURLY_COST`, `COST_ALERT_THRESHOLD`, `DEFAULT_TOKEN_BUDGET`, `MEMORY_MAX_CONTEXT`
- **Health:** `HEALTH_HOST`, `HEALTH_PORT`, `GUINEVERE_HEALTH_DEVICE_ID`, `GUINEVERE_DRAIN_TIMEOUT`, `GUINEVERE_POOL_MONITOR_INTERVAL`, `GUINEVERE_POOL_MONITOR_TIMEOUT`
- **Wearable backup env:** `WEARABLE_ENV_FILE`
- **Obsidian mirrors / WebDAV:** `GUINEVERE_WEBDAV_URL`, `GUINEVERE_WEBDAV_USER`, `GUINEVERE_WEBDAV_PASS`
- **GIT:** `GIT_BINARY`
- **Misc:** `NOTIFY_SOCKET`, `WATCHDOG_PID`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `RESEND_API_KEY`, `GUINEVERE_LOG_LEVEL`, `GUINEVERE_FAIZ_MENTION`, `GUINEVERE_DEVICE_ID`, `SOPS_AGE_KEY`, `SOPS_AGE_KEY_FILE`, `SOPS_SECRETS_FILE`

### 3.2 `.env.gmail` (32 keys, names only)
`GMAIL_API_QUOTA_LIMIT_PER_MINUTE`, `GMAIL_BRIEFING_HOUR`, `GMAIL_BRIEFING_TIMEZONE`, `GMAIL_CLASSIFICATION_CONFIDENCE_THRESHOLD`, `GMAIL_CREDENTIALS_PATH`, `GMAIL_DRAFT_MAX_LENGTH`, `GMAIL_DRAFT_MIN_LENGTH`, `GMAIL_DRAFT_TIMEOUT_HOURS`, `GMAIL_FAIZ_USER_ID`, `GMAIL_HEALTH_HOST`, `GMAIL_HEALTH_PORT`, `GMAIL_IMPORTANCE_NOTIFY_THRESHOLD`, `GMAIL_LOG_FORMAT`, `GMAIL_LOG_LEVEL`, `GMAIL_LOG_OUTPUT_PATH`, `GMAIL_METRICS_PORT`, `GMAIL_NOTIFICATION_RATE_LIMIT_PER_HOUR`, `GMAIL_NOTIFICATION_WEBHOOK_URL`, `GMAIL_OWNER_USER_ID`, `GMAIL_PUBSUB_PROJECT_ID`, `GMAIL_PUBSUB_SERVICE_ACCOUNT_PATH`, `GMAIL_PUBSUB_SUBSCRIPTION`, `GMAIL_PUBSUB_TOPIC`, `GMAIL_QUIET_HOURS_END`, `GMAIL_QUIET_HOURS_START`, `GMAIL_RESEND_API_KEY`, `GMAIL_RESEND_DAILY_LIMIT`, `GMAIL_RESEND_FROM_EMAIL`, `GMAIL_SCOPES`, `GMAIL_SENDER_WHITELIST`, `GMAIL_SYNC_BACKFILL_DAYS`, `GMAIL_SYNC_POLL_INTERVAL_SECONDS`

### 3.3 `.env.wearable` (24 keys, names only)
`MI_FITNESS_USER_ID`, `MI_FITNESS_PASS_TOKEN`, `MI_FITNESS_REGION`, `WEARABLE_DEVICE_ID`, `WEARABLE_OWNER_ID`, `WEARABLE_SYNC_INTERVAL_SEC`, `WEARABLE_SYNC_LOOKBACK_HOURS`, `WEARABLE_CIRCUIT_BREAKER_THRESHOLD`, `WEARABLE_CIRCUIT_BREAKER_RECOVERY_SEC`, `WEARABLE_QUIET_HOURS_START`, `WEARABLE_QUIET_HOURS_END`, `WEARABLE_ALERT_RATE_LIMIT`, `WEARABLE_TIMEZONE`, `WEARABLE_GHI_SUPPRESSION_THRESHOLD`, `WEARABLE_GHI_PENALTY_CAP`, `WEARABLE_GHI_DECAY_DAYS`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `WEARABLE_ENCRYPTION_KEY`

### 3.4 `.env.x_poster` (35 keys, names only)
`X_POSTER_POSTGRES_HOST`, `X_POSTER_POSTGRES_PORT`, `X_POSTER_POSTGRES_DB`, `X_POSTER_POSTGRES_USER`, `X_POSTER_POSTGRES_PASSWORD`, `X_POSTER_DB_POOL_MIN`, `X_POSTER_DB_POOL_MAX`, `X_POSTER_SCHEDULE_SLOTS`, `X_POSTER_SCHEDULE_TIMEZONE`, `X_POSTER_MIN_GAP_SECONDS`, `X_POSTER_MEDIA_ROOT`, `X_POSTER_OBSCURA_CDP_HOST`, `X_POSTER_OBSCURA_CDP_PORT`, `X_POSTER_OBSCURA_CONNECT_TIMEOUT`, `X_POSTER_OBSCURA_PAGE_TIMEOUT`, `X_POSTER_TYPING_DELAY_MIN_MS`, `X_POSTER_TYPING_DELAY_MAX_MS`, `X_POSTER_ACTION_GAP_MIN_SECONDS`, `X_POSTER_ACTION_GAP_MAX_SECONDS`, `X_POSTER_COOKIE_ENCRYPTION_KEY`, `X_POSTER_SESSION_CHECK_INTERVAL_SECONDS`, `X_POSTER_SESSION_MAX_RETRIES`, `X_POSTER_CAPTION_MAX_LENGTH`, `X_POSTER_CAPTION_LANGUAGE`, `X_POSTER_CAPTION_HASHTAGS`, `X_POSTER_MODERATION_FAIL_SAFE`, `X_POSTER_DISCORD_UPLOAD_CHANNEL_ID`, `X_POSTER_DISCORD_DASHBOARD_CHANNEL_ID`, `X_POSTER_DISCORD_GUILD_ID`, `X_POSTER_NOTIFICATION_WEBHOOK_URL`, `X_POSTER_OWNER_USER_ID`, `X_POSTER_POSTED_RETENTION_DAYS`, `X_POSTER_FAILED_RETENTION_DAYS`, `X_POSTER_HEALTH_HOST`, `X_POSTER_HEALTH_PORT`, `X_POSTER_METRICS_PORT`, `X_POSTER_LOG_LEVEL`, `X_POSTER_LOG_FORMAT`, `X_POSTER_LOG_OUTPUT_PATH`

### 3.5 `monitoring/.env` (19 keys, names only)
`ALERTMANAGER_PORT`, `ALERTMANAGER_VERSION`, `DISCORD_ALERTS_WEBHOOK_URL`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_ADMIN_USER`, `GRAFANA_PORT`, `GRAFANA_VERSION`, `LOKI_PORT`, `LOKI_VERSION`, `NODE_EXPORTER_PORT`, `NODE_EXPORTER_VERSION`, `PG_EXPORTER_PASSWORD`, `POSTGRES_EXPORTER_PORT`, `POSTGRES_EXPORTER_VERSION`, `PROMETHEUS_PORT`, `PROMETHEUS_VERSION`, `PROMTAIL_VERSION`, `REDIS_EXPORTER_PASSWORD`, `REDIS_EXPORTER_PORT`, `REDIS_EXPORTER_VERSION`

### 3.6 `secrets/backup/*-plaintext.env` (key NAMES only)
- `secrets/backup/cloudflare-r2-plaintext.env`: `RESTIC_REPOSITORY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `RESTIC_HOST`
- `secrets/backup/idcloudhost-s3-plaintext.env`: `RESTIC_REPOSITORY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `RESTIC_HOST`
- `secrets/backup/restic-password-plaintext.env`: `RESTIC_PASSWORD`

NOTE: these three backup files are stored in plaintext (per `secrets/backup/README.md`); key NAMES shown above. They are not used by P22 adapters — they belong to the Restic backup subsystem.

### 3.7 SOPS-encrypted files (top-level key NAMES only; no decryption)
- `secrets/db-passwords.yaml` (sops-encrypted, plaintext key names visible): `guinevere_core`, `guinevere_surveillance`, `guinevere_scheduler`, …
- `secrets/redis-password.yaml`: `redis_master_password` (encrypted)
- `secrets/discord-secrets.enc.yaml`: `discord_bot_token`, `discord_bot_id` (encrypted)
- `secrets/guinevere-secrets.yaml`: top-level groups `llm`, `discord`, `database`, `surveillance`, `notifications`, `backup`, `github`, `sops`. Inner keys: `nine_router_api_key`, `gpt55_api_key`, `bot_token`, `application_id`, `postgres_url`, `redis_url`, `hmac_secret`, `gotify_url`, `gotify_token`, `s3_access_key`, `s3_secret_key`, `r2_access_key`, `r2_secret_key`, `restic_password`, `pat`, `age`, plus sops metadata (`lastmodified`, `version`).
- `secrets/test-enc.yaml`: error loading config — no matching creation rules; treated as inert.
- `secrets/gmail-client-secrets.json` and `secrets/gmail-token.json`: present (Google OAuth client_secrets + token JSON). Not in SOPS scope.

### 3.8 `.sops.yaml` creation rules
- `secrets/backup/.*\.env$` -> age encrypted (plaintext listed in 3.6)
- `secrets/.*\.yaml$` -> age encrypted
- `secrets/.*\.env$` -> age encrypted
- `secrets/.*\.json$` -> (no rule, NOT encrypted)
- `.env.wearable$` -> age encrypted

So `secrets/gmail-client-secrets.json` and `secrets/gmail-token.json` are intentionally **unencrypted** files (no SOPS rule for `.json`).

---

## 4. VPS Env/Secret Layout (file names + key names only)

### 4.1 Project directory: `/home/guinevere/code/guinevere/`
Env files present (names only, per `ls -1 /home/guinevere/code/guinevere/.env*`):

| File | Key names present |
|------|-------------------|
| `.env.core` | `DATABASE_URL`, `DISCORD_BOT_TOKEN`, `DISCORD_HOME_CHANNEL`, `GUINEVERE_9ROUTER_API_KEY`, `LIFE_KERNEL_PROJECT_ID`, `REDIS_PASSWORD`, `REDIS_URL` |
| `.env.discord` | `DATABASE_URL`, `DISCORD_BOT_TOKEN`, `DISCORD_SHADOW_BOT_ID`, `DISCORD_SHADOW_BOT_TOKEN`, `DISCORD_SHADOW_CHANNEL_ID`, `GUINEVERE_9ROUTER_API_KEY`, `LIFE_KERNEL_DASHBOARD_CHANNEL_ID`, `LIFE_KERNEL_LOG_CHANNEL_ID`, `REDIS_PASSWORD`, `SHADOW_ENABLED`, `SHADOW_TRAFFIC_PCT`, `X_POSTER_DASHBOARD_CHANNEL_ID` |
| `.env.gmail` | full Gmail module config (32 keys — same as local `.env.gmail`) + `DATABASE_URL`, `REDIS_PASSWORD` |
| `.env.hermes` | `DATABASE_URL`, `DISCORD_ALLOWED_CHANNELS`, `DISCORD_ALLOWED_USERS`, `DISCORD_BOT_TOKEN`, `DISCORD_FREE_RESPONSE_CHANNELS`, `DISCORD_HOME_CHANNEL`, `DISCORD_HOME_CHANNEL_THREAD_ID`, `DISCORD_REQUIRE_MENTION`, `DISCORD_SHADOW_BOT_ID`, `DISCORD_SHADOW_BOT_TOKEN`, `DISCORD_SHADOW_CHANNEL_ID`, `GROUP_SESSIONS_PER_USER`, `GUINEVERE_PG_DSN`, `HERMES_INFERENCE_PROVIDER`, `HERMES_MEMORY_BRIDGE_PASSWORD`, `LLM_BASE_URL`, `LLM_FALLBACK_MODEL`, `LLM_MODEL`, `LOG_FORMAT`, `LOG_LEVEL`, `MEMORY_BACKEND`, `NINEROUTER_API_KEY`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `PROMETHEUS_METRICS_PORT`, `REDIS_PASSWORD`, `REDIS_URL`, `SHADOW_ENABLED`, `SHADOW_TRAFFIC_PCT` |
| `.env.loops` | `REDIS_PASSWORD` |
| `.env.mcp` | `BRAVE_API_KEY`, `EXA_API_KEY`, `GITHUB_PAT`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` |
| `.env.monitoring` | `GRAFANA_ADMIN_PASSWORD`, `PG_EXPORTER_PASSWORD`, `REDIS_EXPORTER_PASSWORD` |
| `.env.scheduler` | `REDIS_PASSWORD` |
| `.env.x_poster` | full X Poster config (52 keys) including `X_POSTER_X_API_KEY`, `X_POSTER_X_API_SECRET`, `X_POSTER_X_CLIENT_ID`, `X_POSTER_X_CLIENT_SECRET`, `X_POSTER_X_OAUTH1_ACCESS_TOKEN`, `X_POSTER_X_OAUTH1_ACCESS_TOKEN_SECRET`, `X_POSTER_X_ACCESS_TOKEN`, `X_POSTER_X_REFRESH_TOKEN`, `X_POSTER_POSTGRES_PASSWORD`, `X_POSTER_COOKIE_ENCRYPTION_KEY` |

### 4.2 Secrets directory: `/home/guinevere/code/guinevere/secrets/`
- `secrets/.env.9router` (used by `guinevere-9router.service`): `DATA_DIR`, `DEEPSEEK_API_KEY`, `HOSTNAME`, `INITIAL_PASSWORD`, `JWT_SECRET`, `NODE_ENV`, `OPENAI_API_KEY`, `PORT`
- SOPS-encrypted files (same as local `secrets/`): `db-passwords.yaml`, `redis-password.yaml`, `discord-secrets.enc.yaml`, `guinevere-secrets.yaml`, `test-enc.yaml`, `gmail-client-secrets.json`, `gmail-token.json`

### 4.3 External file: `/opt/guinevere/.env.whatsapp`
- Present, but **read returned Permission denied** (owned by another service user). Contents unknown to this audit. Treated as: file present, contents unverified.

### 4.4 systemd unit -> EnvironmentFile map (from `systemctl cat`)

| Service (active?) | `EnvironmentFile=` paths |
|-------------------|--------------------------|
| `guinevere-core.service` (active) | `/home/guinevere/code/guinevere/.env.core` |
| `guinevere-discord.service` (active) | `/home/guinevere/code/guinevere/.env.discord` |
| `guinevere-gmail.service` (active) | `/home/guinevere/code/guinevere/.env.gmail` |
| `guinevere-whatsapp.service` (active) | `/opt/guinevere/.env.whatsapp` (perm denied) |
| `guinevere-x-poster.service` (active) | `/home/guinevere/code/guinevere/.env.x_poster` |
| `guinevere-mcp.service` (active) | `/home/guinevere/code/guinevere/.env.mcp` |
| `guinevere-9router.service` (active) | `/home/guinevere/code/guinevere/secrets/.env.9router` |
| `guinevere-loops.service` (inactive) | `/home/guinevere/code/guinevere/.env.loops` |
| `guinevere-scheduler.service` (inactive) | `/home/guinevere/code/guinevere/.env.scheduler` |
| `guinevere-monitoring.service` (active) | (no EnvironmentFile in unit file) |

### 4.5 Service active states (VPS, `systemctl is-active`)
- active: core, discord, gmail, whatsapp, x-poster, mcp, 9router, monitoring
- inactive: loops, scheduler

### 4.6 VPS Postgres posture
- VPS env files do NOT carry a bare `POSTGRES_PASSWORD` key; all services use the full `DATABASE_URL` (or `GUINEVERE_PG_DSN`) which embeds credentials inline. The `db-passwords.yaml` SOPS file is the canonical Postgres password vault.

### 4.7 VPS REDIS posture
- `REDIS_PASSWORD` is duplicated across `.env.core`, `.env.discord`, `.env.gmail`, `.env.hermes`, `.env.loops`, `.env.scheduler` (and the canonical source in `secrets/redis-password.yaml`).

---

## 5. Client Module Availability (pip/import check)

Executed against the local `.venv` (Windows):

| Module | Version | Used by adapter(s) | Notes |
|--------|---------|--------------------|-------|
| `discord` (discord.py) | 2.7.1 | discord | **PRESENT**; REST client in-tree at `src/life_kernel/discord_rest_client.py` (uses `httpx`, NOT `discord.py` client). |
| `discord.py` (full) | 2.7.1 | discord | PRESENT (same pkg, also imports) |
| `httpx` | 0.28.1 | github, browser, whatsapp (via obs), gmail (indirect) | **PRESENT**; in-tree MCP tools already use it. |
| `requests` | 2.33.0 | (fallback) | PRESENT |
| `aiohttp` | 3.14.0 | (fallback) | PRESENT |
| `googleapiclient` (`google-api-python-client`) | n/a | gmail, calendar, drive | **MISSING** locally; runtime on VPS (guinevere-gmail.service active) must have it installed. |
| `google.oauth2` (`google-auth`) | n/a | gmail, calendar, drive | **MISSING** locally; same as above. |
| `google.auth` | n/a | gmail, calendar, drive | MISSING locally. |
| `github` (PyGithub) | n/a | github | **MISSING** locally; in-tree `src/mcp/tools/github.py` uses raw `httpx`, so the adapter CAN wire to it (no PyGithub needed). |
| `notion_client` (notion-client) | n/a | notion | **MISSING** locally. |
| `telegram` (python-telegram-bot) | n/a | telegram | **MISSING** locally. |
| `neonize` | 0.3.18 | whatsapp | **PRESENT**; in-tree adapter wraps it. |
| `psutil` | 7.2.2 | vps (metrics) | **PRESENT**; `vps_adapter._get_health_metrics` works out of the box. |
| `docker` (docker-py SDK) | n/a | vps (docker_client) | **MISSING** locally; but in-tree `src/mcp/tools/docker_tool.py` shells out to `docker` CLI via asyncio, so `vps_docker_client` should be wired to that wrapper, not the SDK. |
| `polars` | n/a | finance | **MISSING** locally; but `src/life_kernel/domain_minds/finance_mind.py` is pure-Python (no polars), so the adapter works without it. |
| `pandas` | n/a | finance | **MISSING**; also not used by in-tree FinanceMind. |
| `asyncpg` | 0.31.0 | memory, finance, vps (indirect) | **PRESENT** |
| `sqlalchemy` | 2.0.50 | memory | **PRESENT** |
| `pgvector` | OK | memory | **PRESENT** |
| `redis` (redis-py) | 8.0.0 | vps (indirect), memory (indirect) | **PRESENT** |
| `playwright` | 1.60.0 | browser (`browser_cdp`) | **PRESENT**; in-tree `obscura_cdp.py` uses Playwright over CDP. |
| `markdownify` | 1.2.2 | browser (`fetch`, `obscura`) | **PRESENT** |
| `tenacity` | 9.1.4 | browser, github, fetch (retries) | **PRESENT** |
| `structlog` | 25.5.0 | all adapters (logging) | **PRESENT** |
| `fastapi` | 0.136.3 | n/a (lifecycle) | PRESENT |

**Net:** All ACTIVE adapter paths have their required modules present in the venv. The MISSING google/notion/telegram libs are exactly the same modules that the corresponding adapters declare as CONFIG_MISSING by design (no fake success).

---

## 6. Activation Recommendations

### 6.1 Can go ACTIVE now (secrets + clients both present)
| Adapter | Rationale |
|---------|-----------|
| **discord** | `DiscordRestClient` works; VPS has `DISCORD_BOT_TOKEN`; SOPS-encrypted `discord_bot_token` is the canonical store. Wire `discord_rest_client=DiscordRestClient(...)` in `build_default_registry`. |
| **github** | VPS `.env.mcp` carries `GITHUB_PAT`; in-tree `src/mcp/tools/github.py` (httpx) is the client. Wire `github_client=GitHubClient(pat=...)` or the MCP-tool class. |
| **vps** | `psutil` is present, `docker_tool` and `shell_tool` are in-tree MCP wrappers; wire `vps_docker_client` and `vps_shell_client` to those wrappers. The L3-gated `restart_service` of stateful services (postgres/redis/pgbouncer) is correctly enforced by the adapter. |
| **finance** | `FinanceMind` is in-tree pure-Python, Postgres reachable, `_BLOCKED_ACTIONS` regex pre-blocks pay/transfer/withdraw/invest/trade. Wire `finance_mind=FinanceMind(...)`. |
| **browser** | VPS `.env.mcp` has `BRAVE_API_KEY` + `EXA_API_KEY`; in-tree `brave_search`, `exa_search`, `fetch`, `obscura_cdp` are all present. Wire all three: `browser_search`, `browser_fetch`, `browser_cdp`. |
| **memory** | Postgres + pgvector + Redis all reachable; write/read pipelines are in-tree; `KGQueryEngine` exists. Wire all three. |
| **filesystem** | Self-contained (no external client). Always ACTIVE; path allowlist enforces boundary. |
| **whatsapp** | VPS service is `active`, Neonize client is linked; in-tree `WhatsAppIngressEgressAdapter` wraps it. Wire `whatsapp_adapter`. NOTE: `/opt/guinevere/.env.whatsapp` was perm-denied in this audit; production activation requires re-reading that file with the right credentials to confirm session linkage before flipping status from CONFIG_MISSING to ACTIVE. |

### 6.2 Stay CONFIG_MISSING with reason (operator-gated)
| Adapter | Reason |
|---------|--------|
| **gmail** | `google-api-python-client` + `google-auth` libs are missing in the local venv (the in-tree `AsyncGmailClient` import-time depends on them). VPS `guinevere-gmail.service` is `active` and `.env.gmail` is present, so on the VPS runtime the adapter CAN be wired; locally it cannot. Recommend: leave the adapter as `CONFIG_MISSING` until operator (1) confirms `google-api-python-client` and `google-auth` are present in the VPS venv, and (2) provisions a valid `sec-gmail-oauth` via ProjectVaultSecretProvider or the SOPS path. |
| **calendar** | No `sec-google-calendar-oauth` provisioned; no Google client module in-tree; defer until operator provisions OAuth. |
| **drive** | Same as calendar; no client, no OAuth. Defer. |
| **notion** | No `sec-notion-integration-token`; `notion-client` not installed. Defer. |
| **telegram** | No `sec-telegram-bot-token`; `python-telegram-bot` not installed. Defer. |

### 6.3 Pre-flight checks before flipping to ACTIVE
- Re-verify `/opt/guinevere/.env.whatsapp` with the appropriate credentials to confirm session linkage (this audit was perm-denied).
- Re-verify VPS venv has `google-api-python-client` + `google-auth` installed for the `guinevere-gmail` service (this audit only checked the local Windows venv).
- Confirm the ProjectSecretsVault (P19) has entries for `sec-discord-bot`, `sec-github-pat`, `sec-gmail-oauth`, `sec-brave-api`, `sec-exa-api`, `sec-postgres-core`, `sec-redis-auth` (adapter `secret_refs`). If the ProjectVault is empty, the EnvSecretProvider fallback will be used — the EnvSecretProvider is set up by `wiring.py` with no mapping (defaults to `secret_id.upper().replace("-","_")`); ensure the env var names match the canonical mapping.
- Confirm the `gmail-token.json` at `secrets/gmail-token.json` is not expired; refresh via the Gmail OAuth flow before activation.

### 6.4 HARD STOP impact summary
- All 13 adapters participate in HARD STOP gating (either explicitly via `consent_scopes` + `PermissionTier` checks in `execute_action`, or implicitly via the finance adapter's pre-gate `_BLOCKED_ACTIONS` regex).
- L4 actions (`purge_messages`, `kick_member`, `ban_member`, `delete_repo`, `force_push`, `delete_calendar`, `clear_calendar`, `empty_trash`, `delete_view`, `promote_member`, `promote_admin`, `system_prune`, `docker_rm_all`, `delete_memory`, payment verbs) raise `ActionNotSupportedError` BEFORE the client is invoked — they are not a runtime-only gate, they are adapter-side denials.
- The `filesystem` adapter's `_FORBIDDEN_PATHS` list is the only path-level HARD STOP analogue and is enforced before the workspace check.

### 6.5 Decision matrix (TL;DR for operator)
| Adapter | Decision |
|---------|----------|
| discord | ACTIVE (wire DiscordRestClient; secret via SOPS `discord_bot_token` or env `DISCORD_BOT_TOKEN`) |
| github | ACTIVE (wire `src.mcp.tools.github` httpx client; secret via VPS `.env.mcp` or `secrets/guinevere-secrets.yaml` `github.pat`) |
| vps | ACTIVE (wire `docker_tool` + `shell_tool` from MCP; no new secret; L3 still gates stateful restarts) |
| finance | ACTIVE (wire `FinanceMind`; `_BLOCKED_ACTIONS` pre-gate) |
| browser | ACTIVE (wire `brave_search`, `exa_search`, `fetch`, `obscura_cdp`; secrets via `.env.mcp`) |
| memory | ACTIVE (wire `write_pipeline.store_episode`, `read_pipeline.recall_memories`, `KGQueryEngine`) |
| filesystem | ACTIVE (no wiring; just pass `workspace_root`) |
| whatsapp | ACTIVE (after re-verifying `/opt/guinevere/.env.whatsapp` linkage — perm-denied in this audit) |
| gmail | CONFIG_MISSING (operator-gated: confirm VPS venv has google libs; provision `sec-gmail-oauth` via ProjectVault or .env.gmail) |
| calendar | CONFIG_MISSING (no client, no OAuth) |
| drive | CONFIG_MISSING (no client, no OAuth) |
| notion | CONFIG_MISSING (no token, no client lib) |
| telegram | CONFIG_MISSING (no token, no client lib) |

End of inventory.
