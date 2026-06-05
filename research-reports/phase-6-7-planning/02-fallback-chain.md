# Hermes CLI Feature Research Report: Phase 6 (LLM Routing) & Phase 7 (Hardening)

**Target Library**: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)  
**Documentation Source**: [hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs)  
**Research Date**: 2026-06-05  
**Scope**: LLM fallback chain, budget enforcement, security, Prometheus metrics, backup/restore, custom provider configuration.

---

## 1. Hermes LLM Fallback Chain

Hermes implements a robust, multi-layered fallback system designed to keep sessions running during provider outages, rate limits, or auth failures.

### CLI Command
```bash
hermes fallback add      # Add a fallback provider:model pair
hermes fallback list     # List current fallback chain (alias: ls)
hermes fallback remove   # Remove a fallback (alias: rm)
hermes fallback clear    # Clear all fallbacks
```
*Note: The CLI reuses the same interactive provider picker as `hermes model`.*

### Configuration YAML Format
Fallbacks are configured at the top level of `~/.hermes/config.yaml` as a list:
```yaml
fallback_providers:
  - provider: openrouter
    model: anthropic/claude-sonnet-4
  - provider: nous
    model: anthropic/claude-3-5-sonnet
```
*Legacy compatibility*: A singular `fallback_model: {provider: "...", model: "..."}` is still honored, but `fallback_providers` takes priority if both exist.

### Fallback Chain Behavior
- **Trigger Conditions**: Activates automatically on:
  - Rate limits (HTTP 429) after exhausting retries.
  - Server errors (HTTP 500, 502, 503) after exhausting retries.
  - Auth failures (HTTP 401, 403) or Not Found (404) immediately (no retry).
  - Repeated invalid/malformed API responses.
- **Turn-Scoped Execution**: Fallback activates *per turn*. If the primary model fails mid-turn, Hermes swaps the provider/model/client in-place and resets the retry counter. On the *next* user message, Hermes attempts the primary model again. This prevents cascading failover loops within a single turn.
- **Auxiliary Task Fallback**: Side tasks (vision, compression, web extraction) have independent fallback chains configured under `auxiliary.<task>.fallback_chain`. If an explicit auxiliary provider fails with a capacity error (402, 429), it falls back through: (1) configured `fallback_chain`, (2) main agent provider/model, (3) warn + re-raise.

### Evidence
- [Fallback Providers Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers)
- [Agent Loop Internals: Fallback Behavior](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop#budget-and-fallback-behavior)

---

## 2. Hermes Budget Enforcement

**Status**: *Not natively implemented as a core CLI command yet.* Currently exists as an active RFC/Feature Request.

### Current State
- The `/usage` and `/insights` commands display historical token/cost usage.
- `nous_rate_guard.py` enforces API rate limits for Nous Portal users, but does not cap dollar amounts.
- No native `hermes budget` CLI commands (`show`, `set`, `list`, `reset`) exist in the current stable release.

### Proposed/RFC Implementation (Issue #26382, #31399)
The community has proposed an opt-in budget enforcement layer (`agent/budget_guard.py`) with the following YAML schema:
```yaml
budget:
  daily_usd_cap: 50.0
  monthly_usd_cap: 500.0
  alert_at_pct: [50, 75, 90]
```
- **Enforcement**: Check accumulated spend before each LLM call. If breached, return a structured error to halt the agent loop gracefully.
- **Reset**: Daily at midnight UTC; monthly on the 1st. Manual reset via proposed `hermes budget reset`.

### Best-Practice Recommendations for Migration
Since native budget capping is not yet available, implement hardening via:
1. **Proxy-Level Enforcement**: Route Hermes through LiteLLM or OpenRouter and set hard spend limits at the provider level.
2. **Skill-Based Budgeting**: Use custom skills (e.g., the `autoresearch` skill pattern) that include `state.py` scripts to enforce token/time/experiment hard caps before delegating tool calls.
3. **External Monitoring**: Parse Hermes session logs or use the `/api/analytics/usage` endpoint from the web dashboard to trigger external alerts (e.g., via cron + webhook).

### Evidence
- [RFC: Configurable daily/monthly hard budget cap](https://github.com/NousResearch/hermes-agent/issues/26382)
- [RFC: OS-style skill scheduling with resource budgets](https://github.com/NousResearch/hermes-agent/issues/31399)

---

## 3. Hermes Security

Hermes includes built-in supply-chain and runtime security features, accessible via the CLI.

### CLI Command
```bash
hermes security audit [--json] [--fail-on critical|high|moderate|low] [--skip-venv] [--skip-plugins] [--skip-mcp]
```

### What It Scans
- **Hermes venv**: Installed PyPI distributions.
- **Plugins**: Python dependencies declared under `~/.hermes/plugins/`.
- **MCP Servers**: Pinned `npx`/`uvx` MCP servers referenced in `config.yaml`.
- *Exclusions*: Does not scan globally-installed packages, OS-level binaries, or editor/browser extensions.

### Vulnerability Severity Levels
Integrates with **OSV.dev**. Severity levels are: `low`, `moderate`, `high`, `critical`. The `--fail-on` flag dictates the CLI exit code (default: `critical`).

### Integration with Safety Hooks
- **Dangerous Command Detection**: Regex patterns in `tools/approval.py` intercept destructive commands (`rm -rf`, `DROP TABLE`, `curl | bash`) and require explicit user approval (`once`, `session`, `always`, `deny`).
- **Shell Injection Prevention**: All user input interpolated into shell commands is sanitized via `shlex.quote()`.
- **Path Traversal Prevention**: Write deny lists resolve paths via `os.path.realpath()` to prevent symlink bypasses.
- **Container Hardening**: When using Docker/Singularity backends, all capabilities are dropped, and PID limits are enforced. Dangerous command checks are skipped *only* because the container itself is the security boundary.
- **Cron Prompt Injection**: Scanner blocks instruction-override patterns in scheduled tasks.

### Evidence
- [CLI Commands Reference: hermes security](https://hermes-agent.nousresearch.com/docs/reference/cli-commands#hermes-security)
- [Security Considerations in Contributing Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#security-considerations)

---

## 4. Hermes Prometheus Metrics

**Status**: *Not natively supported.* Hermes does **not** expose built-in Prometheus metrics on port 9191 (or any other port), nor does it provide Grafana dashboard templates.

### Current Observability Alternatives
1. **Web Dashboard Analytics API**: The built-in web dashboard (port **9119**, not 9191) exposes a JSON endpoint: `GET /api/analytics/usage?days=30`. This returns:
   - Total tokens (input/output), cache hit percentage, estimated cost.
   - Daily token usage breakdowns.
   - Per-model token and cost aggregates.
2. **Session JSONL Logs**: Hermes can be configured to `save_trajectories: true`, dumping all conversations, tool calls, and token counts to JSONL files for external parsing.
3. **External Proxy Metrics**: If routing through LiteLLM or a similar proxy, Prometheus metrics should be scraped from the proxy layer, not Hermes itself.

### Best-Practice Recommendation for Migration
Do not attempt to implement Prometheus scraping directly in Hermes. Instead:
- Enable the web dashboard and scrape its `/api/analytics/usage` endpoint via a custom Prometheus exporter (e.g., `prometheus-python-client`).
- Route all LLM traffic through a proxy (LiteLLM) that natively exposes `/metrics` for Grafana consumption.

### Evidence
- [Web Dashboard Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard)
- [Programmatic Integration Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration)

---

## 5. Hermes Backup & Restore

Hermes provides two distinct mechanisms for state persistence: full home directory backups and granular filesystem checkpoints.

### CLI Commands: Backup & Restore
```bash
hermes backup              # Back up Hermes home directory (~/.hermes/) to a zip file
hermes import <file.zip>   # Restore a Hermes backup from a zip file
hermes update --backup     # Optional: trigger a full pre-update backup
```
*Note: Full backups include `config.yaml`, `auth.json`, `skills/`, `memories/`, and `sessions/`.*

### CLI Commands: Checkpoints (Shadow Git Store)
```bash
hermes checkpoints         # Show total size, project count, per-project breakdown
hermes checkpoints prune   # Force cleanup: delete orphans/stale, GC, enforce size cap
hermes checkpoints clear   # Delete entire checkpoint base (irreversible)
```

### State Persistence Format
- **Checkpoints**: Powered by an internal Checkpoint Manager that maintains a **single shared shadow git repository** at `~/.hermes/checkpoints/store/`. 
- **Triggers**: Automatically snapshots the project before destructive file tools (`write_file`, `patch`) or terminal commands (`rm`, `rmdir`, `git reset`, `sed -i`).
- **In-Session Rollback**: Users can type `/rollback` to list checkpoints, `/rollback diff <N>` to preview changes, or `/rollback <N>` to restore the filesystem and undo the last conversation turn.
- **SQLite `state.db`**: Hermes primarily uses JSON/YAML for config, auth, and session history. While some specific tools or skills may utilize SQLite for local state, the core backup/checkpoint system relies on the shadow git store and JSON serialization, not a monolithic `state.db`.

### Evidence
- [Checkpoints and /rollback Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback)
- [CLI Commands Reference: hermes backup](https://hermes-agent.nousresearch.com/docs/reference/cli-commands#hermes-backup)

---

## 6. Hermes Custom Provider Configuration

Hermes fully supports any OpenAI-compatible API endpoint, with advanced features for named providers, auth pooling, and environment variable injection.

### Custom Provider YAML Format
Defined under the `custom_providers` list in `~/.hermes/config.yaml`:
```yaml
custom_providers:
  - name: "local-dev"
    base_url: "http://localhost:8080/v1"
    key_env: "LOCAL_API_KEY"        # Preferred: reference env var
    # api_key: "sk-..."             # Alternative: hardcoded (not recommended)
    api_mode: "chat_completions"    # Options: chat_completions, anthropic_messages, codex_responses
    extra_body:                     # Optional: inject provider-specific fields
      enable_thinking: true
    models:                         # Optional: override auto-discovered context lengths
      qwen-2.5-72b:
        context_length: 32000
```

### Auth Pooling Behavior
- Hermes supports **Credential Pools** for automatic key rotation when rate limits (429) or quota errors (402) occur.
- Custom endpoints get their own pools, keyed by the provider name (e.g., `custom:local-dev`) in `~/.hermes/auth.json`.
- Rotation strategies (`round_robin`, `least_used`) are configured in `config.yaml` under `credential_pool_strategies`.
- Auto-seeding: Hermes automatically discovers and seeds pools from environment variables, OAuth tokens, and manual entries.

### API Key Management (`key_env`)
- **Best Practice**: Use `key_env: "MY_API_KEY"` instead of hardcoding `api_key`. Hermes resolves this at runtime from `os.environ` or the `.env` file.
- **Known Caveat**: As of mid-2026, there is a known UI bug where the interactive model picker (`hermes model` or TUI) may fail to resolve `key_env` for `custom_providers` list entries, showing "0 models listed". However, the *runtime* chat completion path correctly resolves `key_env` and functions normally. Workaround: manually populate the `models:` list in the YAML to bypass live discovery in the picker.

### Streaming Compatibility
- Fully compatible with OpenAI-compatible streaming (`/v1/chat/completions` with `stream: true`). Hermes handles Server-Sent Events (SSE) parsing natively for all `chat_completions` api_mode providers.

### Evidence
- [AI Providers Documentation](https://hermes-agent.nousresearch.com/docs/integrations/providers#custom--self-hosted-llm-providers)
- [Credential Pools Documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/credential-pools)
- [Bug: model picker ignores key_env on custom_providers](https://github.com/NousResearch/hermes-agent/issues/30653)

---

## Summary & Migration Recommendations

| Feature | Hermes Native Support | Migration Recommendation |
|---|---|---|
| **LLM Fallback** | ✅ Robust, turn-scoped, multi-layered | Use `hermes fallback` CLI or `fallback_providers` YAML. |
| **Budget Enforcement** | ❌ RFC only (not implemented) | Implement at proxy layer (LiteLLM) or via custom skill guards. |
| **Security Scanning** | ✅ Built-in OSV.dev audit + runtime guards | Run `hermes security audit` in CI/CD pipelines. |
| **Prometheus Metrics** | ❌ Not supported (Dashboard is port 9119 JSON) | Scrape `/api/analytics/usage` or use proxy-level metrics. |
| **Backup/Restore** | ✅ Zip backups + Shadow Git checkpoints | Enable `checkpoints.enabled: true` for destructive ops. |
| **Custom Providers** | ✅ Full support with `key_env` + auth pooling | Use `key_env` for secrets; be aware of model picker UI bug. |

*Report generated for Phase 6 (LLM Routing) and Phase 7 (Hardening) planning.*
</80>