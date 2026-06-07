# Security Posture Audit — Post ADR-035 Hermes Migration

**Scope:** local repository security posture review after ADR-035 Hermes migration.
**Focus areas:** open ports audit, SOPS secrets verification, plaintext secrets scan, security configuration review, env-file handling, and age-key storage.
**Note:** VPS-only checks were not performed because SSH/VPS credentials were not available in this session. Those sections are explicitly marked below.

## Executive Summary

Overall, the local post-migration security posture looks **partially compliant**:

- **Secrets management:** Secrets are stored under `secrets/` and are SOPS-encrypted with age recipients configured in `.sops.yaml`.
- **Plaintext secret exposure:** No hardcoded plaintext secrets were found in the requested scan surface (`src/` and `hermes-config/` for `.py`, `.yaml`, and `.toml` files) that matched the requested `password=|api_key=|secret=|token=` pattern after excluding common environment-variable references.
- **Age key storage:** `age-key.txt` was **not present** in the repository root, which is preferable from a repository hygiene perspective.
- **Environment file hygiene:** `.gitignore` ignores `.env` files and explicitly keeps `.env.example` tracked; however, a real `monitoring/.env` file exists in the working tree and must be treated as sensitive runtime material.
- **Configuration review:** `hermes-config/config.yaml` contains several hardcoded identifiers and operational values, but the reviewed file does not show plaintext secret material. It does include security-relevant runtime hooks and MCP exposure settings that should remain tightly controlled.
- **VPS posture:** Not verified in this session.

## 1) Plaintext Secrets in Code Scan

### Scan method
Requested pattern family:
- `password=|api_key=|secret=|token=`
- Scope: `src/` and `hermes-config/`
- File types: `*.py`, `*.yaml`, `*.toml`
- Exclusions: `os.environ`, `getenv`, `placeholder`, `example`, `test`, `$VAR`, `${VAR}` references

### Findings
No direct plaintext secret values were found in the requested scan surface. The matches below are **environment-variable lookups or safe secret plumbing**, not literal secret values.

#### Safe matches observed in `src/`
- `src/memory/embeddings.py:503` — `api_key = self._config.api_key`
- `src/memory/embeddings.py:579` — `api_key = self._config.api_key`
- `src/_deprecated/hermes-migration-phase-7/session_adapter.py:98` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/_deprecated/hermes-migration-phase-7/session_adapter.py:131` — `api_key=llm_config.get("api_key", "")`
- `src/_deprecated/hermes-migration-phase-7/conversational_handler.py:183` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/_deprecated/hermes-migration-phase-7/bot.py:541` — `token = os.environ.get("DISCORD_BOT_TOKEN")`
- `src/discord/_entrypoint.py:552` — `token = os.environ.get("DISCORD_BOT_TOKEN")`
- `src/mcp/tools/redis_tool.py:124` — `password = os.environ.get("REDIS_PASSWORD", "")`
- `src/mcp/tools/redis_tool.py:138` — `password=password`
- `src/surveillance/redis_buffer.py:203` — `password=password or os.environ.get("REDIS_PASSWORD", "")`
- `src/mcp/tools/postgres_tool.py:119` — `password = os.environ.get("POSTGRES_PASSWORD", "")`
- `src/mcp/tools/postgres_tool.py:125` — `password=password`
- `src/surveillance/secrets.py:73` — `secret = surveillance.get("hmac_secret")`
- `src/surveillance/secrets.py:111` — `_cached_secret = env_value`
- `src/surveillance/secrets.py:116` — `_cached_secret = _decrypt_sops_secret()`
- `src/surveillance/secrets.py:128` — `_cached_secret = None`
- `src/surveillance/consumer.py:402` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/surveillance/consumer.py:416` — `db_password = os.environ.get("GUINEVERE_DB_PASSWORD", "")`
- `src/surveillance/consent_gate.py:136` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/discord/hermes_conversational.py:157` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/discord/gotify_fallback.py:49` — `token = os.environ.get("GOTIFY_APP_TOKEN", "")`
- `src/surveillance/auth.py:75` — `secret = get_hmac_secret()`
- `src/surveillance/replay.py:59` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/mcp/tools/exa_search.py:79` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/mcp/tools/exa_search.py:164` — `api_key = _get_api_key()`
- `src/mcp/tools/context7.py:165` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/discord/cmd_loop_stop.py:385` — `api_key = os.environ.get("GUINEVERE_API_KEY")`
- `src/mcp/tools/brave_search.py:71` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/mcp/tools/brave_search.py:151` — `api_key = _get_api_key()`
- `src/discord/cmd_loop_start.py:344` — `api_key = os.environ.get("GUINEVERE_API_KEY")`
- `src/mcp/cost.py:61` — `password=password or os.environ.get("REDIS_PASSWORD", "")`
- `src/mcp/budget.py:81` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/core/services/cost_tracker.py:21` — `password=password or os.environ.get("REDIS_PASSWORD", "")`
- `src/core/main.py:76` — `_redis_password = os.environ.get("REDIS_PASSWORD", "")`
- `src/core/main.py:82` — `password=_redis_password`
- `src/hermes_plugins/commands_loop/loop_stop.py:118` — `api_key = os.environ.get("GUINEVERE_API_KEY")`
- `src/hermes_plugins/commands_loop/loop_start.py:78` — `api_key = os.environ.get("GUINEVERE_API_KEY")`
- `src/loops/cost.py:39` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/loops/cost.py:47` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/hermes/_session_adapter.py:109` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/hermes/_session_adapter.py:142` — `api_key=llm_config.get("api_key", "")`
- `src/hermes/safety_plugin.py:338` — `password=os.environ.get("REDIS_PASSWORD", "")`
- `src/hermes/plugins/persona_plugin.py:144` — `password=os.environ.get("REDIS_PASSWORD", "")`

#### Safe match observed in `hermes-config/`
- `hermes-config/hooks/_hook_utils.py:63` — `password = os.environ.get("REDIS_PASSWORD")`

### Assessment
- **Pass for plaintext secret exposure in the requested scan surface:** no literal secret values found.
- **Caveat:** many code paths correctly rely on environment variables and runtime secret injection, so this scan does not prove runtime secret absence on VPS or in external `.env` files.

## 2) SOPS Secrets Audit

### Secret directory contents
`secrets/` contains:
- `db-passwords.yaml`
- `guinevere-secrets.yaml`
- `redis-password.yaml`
- `backup/` (directory)

### Encryption status
All inspected secret files are SOPS-encrypted and include `ENC[AES256_GCM,...]` payloads.

#### Encrypted files verified
- `secrets/db-passwords.yaml`
- `secrets/guinevere-secrets.yaml`
- `secrets/redis-password.yaml`

#### Plaintext files found in `secrets/`
- None observed in the inspected file set.

### SOPS configuration
`.sops.yaml` defines age-based encryption rules targeting `secrets/.*\.(yaml|env|json)$` and a backup `.env` path rule. The configured age recipient is:
- `age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj`

### Assessment
- **Pass:** repository uses SOPS + age for the tracked secret files.
- **Caveat:** this audit did not decrypt any values, by design.

## 3) Age Key Security

### Result
- `age-key.txt` was **not found** at the repository root.
- No key contents were read.

### Assessment
- **Good:** absence of a committed `age-key.txt` at repo root reduces accidental exposure risk.
- **Unknown:** this does not prove the key is absent from the VPS or from another non-repo location.

## 4) Hermes Config Security Review

### File reviewed
- `hermes-config/config.yaml`

### Observations
The config includes security-relevant settings and hardcoded operational identifiers, but no plaintext secret values were observed in the reviewed content.

#### Security-relevant hardcoded values / settings
- Discord allowed user/channel IDs are hardcoded in the config.
- `require_mention: false` and `free_response_channels` imply a broad response surface within allowed channels.
- `group_sessions_per_user: true` improves isolation within shared channels.
- `auto_thread: false` keeps replies inline.
- `history_backfill: true` means the bot will ingest prior channel history on mentions, which is operationally useful but expands data handling.
- `model.base_url` and provider `base_url` point to `http://localhost:20128/v1`.
- `providers.*.key_env` references `NINEROUTER_API_KEY` rather than embedding a key.
- `fallback_providers` include `cx/gpt-5.5` and `guinevere`, with `key_env` indirection only.
- `hooks.pre_tool_call` runs `budget_check.py` and `consent_gate.py` with fail-closed `on_failure: block` behavior.
- `hooks.post_tool_call` runs `dnr_filter.py` with fail-closed blocking.
- `mcp_servers.fastmcp_custom.enabled: false`, which is important because native production tool exposure is disabled by default.
- `mcp_servers.fastmcp_custom.env_file: .env.mcp` means runtime secret loading is externalized, not embedded.
- Observability ports include `metrics_port: 9191`.

### Security posture interpretation
- **Positive:** secret values are not hardcoded in the reviewed config; runtime hooks are explicitly defensive and fail-closed.
- **Risk note:** the config is operationally powerful, so any enabling of MCP exposure or relaxation of hooks should be treated as a security-sensitive change.

## 5) Environment Variable Security

### Findings
- `.gitignore` includes `*.env` and explicitly keeps `!.env.example` tracked.
- Existing env files discovered in the repo tree:
  - `monitoring/.env` — real env file present in working tree
  - `hermes-config/.env.template` — template, not secret
  - `monitoring/.env.example` — example, not secret
  - `monitoring/.env.enc.example` — encrypted example/template

### Assessment
- **Pass for repository ignore rules:** `.env` files are ignored globally.
- **Caution:** `monitoring/.env` exists locally and should be treated as sensitive runtime material; it should not be committed.

## 6) VPS Security Checks

**Status:** Not executed in this session.

### Reason
No SSH/VPS credentials or confirmed access path were available, and the task explicitly forbids attempting SSH when credentials are unavailable.

### Not verified
- Open ports via `ss -tlnp` filtered to public-facing interfaces
- `hermes security` output on VPS
- Age-key accessibility on VPS

### Required follow-up if VPS access becomes available
1. Run `ss -tlnp` and exclude loopback and internal-only ranges (`127.0.0.1`, `::1`, `100.94.*`).
2. Run `hermes security 2>/dev/null`.
3. Confirm age key is stored outside the repo and not world-readable.

## 7) Findings and Severity

### Low / informational
- `monitoring/.env` exists in the working tree and must remain untracked.
- `hermes-config/config.yaml` contains operationally sensitive settings and hardcoded identifiers, but no plaintext secrets were observed.
- VPS checks were not performed, so exposure status remains unknown.

### Pass conditions met locally
- No plaintext secrets found in the requested code/config scan surface.
- SOPS-encrypted secret files confirmed.
- No repository-root `age-key.txt` present.
- `.gitignore` covers `.env` files.

## 8) Conclusion

Post-ADR-035, the local repository posture is **security-hardened and mostly aligned** with the expected secrets-management model: SOPS + age encryption is in place, plaintext secret leakage was not found in the requested surface, and runtime secret handling is generally delegated to environment variables or encrypted files.

The main remaining unknown is **VPS runtime posture**, especially open ports and the live Hermes security report. Until those are checked, the audit cannot confirm the full end-to-end post-migration security posture.

## Evidence Notes

- No secret values were copied into this report.
- Any sensitive-looking findings are redacted at the file level by omission; no decrypted content was accessed.
- VPS-only sections are intentionally marked not verified.
