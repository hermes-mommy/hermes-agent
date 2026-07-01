# P26 RequestDetails Autoprune Security Analysis

| Field | Value |
|---|---|
| Task | P26 `requestDetails` autoprune security research |
| Output path | `docs/setup-evidence/P26/requestdetails-autoprune/research/security-analysis.md` |
| Workspace | `C:\Users\faizz\guinevere` |
| SSH target | `root@49.12.82.34 -p 39999` |
| Captured at | 2026-06-27 |
| Mode | Read-only VPS research; local markdown write only |
| Runtime mutation | None |
| Secret/payload exposure in this report | No raw secrets, env values, DB rows, request payloads, or PM2 log lines are included |

## Verdict

**NEEDS REVIEW before implementation.**

Autopruning `requestDetails` is security-positive because current evidence shows the table is capped at 1,000 rows but still holds about 601 MB of JSON data, with an average row data length around 630 KB. That JSON can include request, provider request, provider response, and response objects, so retention reduction is appropriate.

The main blocker is not the SQL delete itself; it is logging and evidence discipline around the prune workflow. The 9Router code stores sanitized request headers in `requestDetails`, but it can still retain large prompt/response payload material in DB JSON. Separately, the request logger code path can write raw request/response artifacts if `ENABLE_REQUEST_LOGS=true`, and PM2 logs currently contain risk-pattern hits by filename for `Authorization`, `Bearer`, `messages`, `completion`, and `requestDetails`. I did not print the matched log lines, so the content remains unverified and must be treated as potentially sensitive.

Network boundary is acceptable for a read-only autoprune plan with caveats: 9Router still binds `0.0.0.0:20128`, public IPv4 access to `20128` is blocked by an IPv4 iptables rule, Tailscale access works, and IPv6 has default ACCEPT but no observed `[::]:20128` listener. SSH remains broad/root/password-enabled and must be treated as out-of-scope for this autoprune task unless a separate hardening plan exists.

## Scope and Boundaries

This research checked:

- No-secret/no-payload logging requirements for the prune task.
- Firewall, Tailscale, SSH, and 9Router exposure boundaries.
- Systemd/script/log risks relevant to an autoprune implementation.
- Evidence grep patterns that should be used before completion.

This research did not:

- Delete or prune database rows.
- Read `requestDetails.data` row contents.
- Print PM2 log content.
- Read `.env`, provider rows, API keys, tokens, DB passwords, Tailscale state, SSH keys, shell history, or decrypted credentials.
- Restart PM2, systemd services, SSH, Tailscale, or firewall state.
- Change systemd units, timers, scripts, iptables, ip6tables, PM2 config, DB files, or source files.

## Inputs Read

Local files:

- `AGENTS.md`
- `docs/10-governance/17-ADR_Index_v1.0.md`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/current-dashboard-db-ground-truth.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/pre-prune-snapshot.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/research/security-network-analysis.md`
- `docs/setup-evidence/P26/p25-cluster-inventory.md`

Remote read-only checks:

- Host, service, listener, firewall, Tailscale status.
- Unit/timer inventory for 9Router/prune/request/detail/sqlite names.
- File-name inventory for possible prune/script candidates.
- Source-only inspection of `requestDetailsRepo.js`, `open-sse/handlers/chatCore/requestDetail.js`, `open-sse/utils/requestLogger.js`, and `src/sse/utils/logger.js`.
- PM2 log file sizes and pattern hit filenames only, not matching lines.

## Current `requestDetails` Retention Risk

Existing P26 snapshot records:

| Metric | Value |
|---|---:|
| `requestDetails_count` | 1,000 |
| `requestDetails_avg_data_len` | 630,474.71 |
| `requestDetails_max_data_len` | 2,081,882 |
| `requestDetails_total_data_mb` | 601.27 |
| `dbstat requestDetails` | 605.37 MB |

Schema observed in the pre-prune snapshot:

```text
CREATE TABLE requestDetails (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, status TEXT, data TEXT NOT NULL);
CREATE INDEX idx_rd_ts ON requestDetails(timestamp DESC);
CREATE INDEX idx_rd_provider ON requestDetails(provider);
CREATE INDEX idx_rd_model ON requestDetails(model);
CREATE INDEX idx_rd_conn ON requestDetails(connectionId);
```

Security interpretation:

- The `data` column is the sensitive retention surface.
- The safe evidence posture is metadata-only: counts, lengths, dbstat size, min/max timestamps, schema, and index presence are allowed.
- Raw `data`, JSON previews, request bodies, response bodies, provider request/response bodies, messages, tool payloads, authorization headers, cookies, and provider credentials must not be printed.
- The existing evidence correctly states that no `requestDetails.data` content was printed.

## `requestDetailsRepo.js` Security Observations

Relevant behavior from source inspection:

- `DEFAULT_MAX_RECORDS = 200`.
- `DEFAULT_BATCH_SIZE = 20`.
- `DEFAULT_FLUSH_INTERVAL_MS = 5000`.
- `DEFAULT_MAX_JSON_SIZE = 5 * 1024`.
- Runtime config can override through settings or env keys such as `OBSERVABILITY_MAX_RECORDS`, `OBSERVABILITY_BATCH_SIZE`, `OBSERVABILITY_FLUSH_INTERVAL_MS`, and `OBSERVABILITY_MAX_JSON_SIZE`.
- `sanitizeHeaders()` removes keys containing `authorization`, `x-api-key`, `cookie`, `token`, and `api-key` from `item.request.headers`.
- Stored record fields include `request`, `providerRequest`, `providerResponse`, and `response`.
- `truncateField()` caps oversized JSON and stores `_preview` of the first 200 characters when truncating.
- The built-in prune path deletes oldest rows when count exceeds configured max:

```text
DELETE FROM requestDetails WHERE id IN (SELECT id FROM requestDetails ORDER BY timestamp ASC LIMIT ?)
```

Risk:

- Header sanitation currently applies only to `item.request.headers`, not visibly to `providerRequest.headers`, `providerResponse.headers`, or `response` payloads.
- Even with 5 KB truncation, `_preview` can expose prompt text, response text, URLs, identifiers, or accidental secrets if the original object begins with sensitive material.
- Current DB evidence shows much larger JSON lengths than 5 KB, so the live table contains records that either predate the cap, were written with a higher cap, or are not constrained as expected.
- Error logging in `flushToDatabase()` prints exception objects. SQLite errors are usually safe, but an unexpected driver error could include SQL context. It should not include bound `data` values in evidence.

Autoprune implication:

- Prune evidence must only show row counts, byte totals, and timestamps before/after.
- Do not sample rows to prove pruning.
- Do not write a report that includes deleted IDs if IDs encode model names or timestamps beyond what is already accepted.

## Request Logger and Payload Log Risk

`open-sse/utils/requestLogger.js` is a separate risk path from the SQLite `requestDetails` table.

Observed behavior:

- Logging is disabled unless `ENABLE_REQUEST_LOGS === 'true'`.
- If enabled, it creates per-request JSON/text files under a `logs` directory.
- It writes client raw request, source request, OpenAI intermediate request, target provider request, provider response, streaming provider chunks, streaming OpenAI chunks, converted client response, and error files.
- `maskSensitiveHeaders()` currently returns headers unchanged and contains a comment stating masking is disabled for testing.
- Error logs can include `requestBody`.

Risk:

- If enabled, this path can persist raw prompts, raw responses, provider chunks, request bodies, target URLs, and full headers.
- Because masking is disabled, it can persist Authorization, cookies, API keys, or provider tokens if headers flow through it.
- This path is not solved by pruning `requestDetails`.

Required guardrail for P26 autoprune:

- Treat `ENABLE_REQUEST_LOGS=true` as a hard rejection unless the task explicitly includes a separate sanitization change and log cleanup plan.
- Evidence must inspect only env key names or config booleans, never env values.
- Do not archive or quote files under app `logs/` or `/root/.pm2/logs/` as evidence.

## PM2/Systemd Log Risk

Remote PM2 log files exist and are non-trivial in size:

| File | Size |
|---|---:|
| `9router-out-1.log` | 6,066,101 bytes |
| `9router-out-0.log` | 3,033,462 bytes |
| `9router-error-1.log` | 47,702 bytes |
| `9router-error-0.log` | 27,831 bytes |
| rotated `9router-error-0__2026-06-27_00-00-00.log` | 1,485 bytes |
| rotated `9router-out-0__2026-06-27_00-00-00.log` | 1,361 bytes |

Pattern-hit filenames from count/file-only grep:

| Pattern | Files with hits |
|---|---|
| `Authorization` | `9router-out-1.log` |
| `Bearer` | `9router-error-0.log`, `9router-error-1.log` |
| `api[_-]*key` | none |
| `JWT_SECRET` | none |
| `API_KEY_SECRET` | none |
| `STORAGE_ENCRYPTION_KEY` | none |
| `messages` | `9router-out-0.log`, `9router-out-1.log` |
| `providerResponse` | none |
| `requestDetails` | `9router-error-0.log` |
| `prompt` | none |
| `completion` | `9router-out-0.log`, rotated out log, `9router-out-1.log` |

Important limitation:

- I intentionally did not print matching log lines.
- The matches may be harmless text, redacted errors, metadata, or real sensitive material. Because content was not inspected, treat this as **NEEDS REVIEW**, not as confirmed secret leakage.

Systemd posture:

- `pm2-root.service` is active.
- legacy `9router.service` is inactive.
- `9router.service` exists but is disabled.
- No existing systemd unit/timer matching `request`, `detail`, `prune`, `sqlite`, or equivalent autoprune names was observed.

Script/unit risk for a future autoprune:

- Any prune script run through systemd must not echo SQL that includes row data.
- Avoid `set -x` in shell scripts.
- Avoid `sqlite3 ... "SELECT data ..."` or `.dump`.
- Avoid redirecting full sqlite output into journald/PM2 logs.
- Use `journalctl` evidence only with bounded, pattern-filtered, sanitized lines.
- Timer/service names should be specific, e.g. `9router-requestdetails-prune.service` and `.timer`, if implementation later becomes approved.

## Firewall, Tailscale, and SSH Boundaries

Read-only remote observations:

| Check | Observed State |
|---|---|
| Hostname | `ninerouter-vps` |
| `tailscaled` | active |
| `ssh` | active |
| `pm2-root` | active |
| legacy `9router` | inactive |
| `apache2` | inactive |
| Tailscale IP | `100.104.210.75` |
| 9Router listener | `0.0.0.0:20128` |
| SSH listener | `0.0.0.0:22`, `[::]:22` |
| Tailscale ports | `0.0.0.0:64527`, UDP `41641` on IPv4/IPv6 |
| IPv4 firewall | `ACCEPT -i tailscale0 --dport 20128`, `DROP -i venet0 --dport 20128` |
| IPv6 firewall | default `INPUT ACCEPT`; no explicit `20128` rule |

Boundary interpretation:

- Application port `20128` remains protected from public IPv4 by the targeted `venet0` drop rule.
- 9Router still binds to all IPv4 addresses, so public exposure depends on firewall correctness.
- No `[::]:20128` listener was observed, so IPv6 exposure is latent rather than active.
- If a future restart or config change causes `[::]:20128`, completion must fail unless IPv6 firewall protection is added and verified first.
- SSH is broad and root/password-enabled per prior security research. Do not change SSH/firewall/Tailscale inside this autoprune task without explicit approval and a recovery-console plan.
- Tailscale userspace networking should be preserved.

## No-Secret / No-Payload Logging Requirements

Hard requirements for P26 requestDetails autoprune:

1. Never print `requestDetails.data`.
2. Never print JSON previews from `request`, `providerRequest`, `providerResponse`, or `response`.
3. Never print request/response bodies, SSE chunks, tool calls, messages, prompts, completions, or provider payloads.
4. Never print Authorization, Cookie, API key, token, password, JWT, storage encryption key, provider credential, Tailscale state, SSH private key, shell history, decrypted env, or PM2 env values.
5. Never run `.dump`, `SELECT *`, `SELECT data`, `json_extract(data, ...)`, or row sampling as evidence.
6. Use aggregate SQL only: row counts, `length(data)` aggregates, `MIN(timestamp)`, `MAX(timestamp)`, `dbstat`, `PRAGMA integrity_check`, `PRAGMA wal_checkpoint(PASSIVE)` only if checkpoint is explicitly allowed. For read-only research, avoid checkpoint.
7. If any command accidentally prints sensitive material, stop, do not paste it into evidence, record a sanitized violation note, and ask for cleanup scope.
8. Prune implementation must not rely on app logs as evidence.
9. If a systemd timer is added later, scripts must use quiet mode and write only sanitized metrics.
10. `ENABLE_REQUEST_LOGS=true` blocks acceptance unless separately remediated.

## Safe Evidence Commands

Allowed local evidence scan, adjusted to avoid node_modules and VCS data:

```powershell
rg -n --hidden --glob '!**/.git/**' --glob '!node_modules/**' --glob '!venv/**' "(?i)(sk-[A-Za-z0-9]|authorization:\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}|api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{12,}|token\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{12,}|password\s*[:=]\s*['\"]?[^<\s]{8,}|secret\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{12,}|BEGIN (OPENSSH|RSA|EC|PRIVATE) KEY)" docs/setup-evidence/P26/requestdetails-autoprune docs/setup-evidence/P26/highend-2worker-tuning
```

Allowed payload-evidence scan:

```powershell
rg -n --hidden --glob '!**/.git/**' --glob '!node_modules/**' --glob '!venv/**' "(requestDetails\.data|SELECT\s+data|SELECT\s+\*|providerResponse|providerRequest|response\.content|\"messages\"\s*:|\"prompt\"\s*:|\"completion\"\s*:|raw response|streaming chunk)" docs/setup-evidence/P26/requestdetails-autoprune
```

Allowed remote metadata-only checks:

```bash
date -Is
hostname
systemctl is-active tailscaled ssh pm2-root 9router apache2
ss -H -tulpen | grep -E ':(20128|22|41641|64527)\b' | sort
iptables -S INPUT
ip6tables -S INPUT
tailscale status --self --peers=false
tailscale ip -4
find /root/.pm2/logs -maxdepth 1 -type f -name '9router*.log' -printf '%f %s %TY-%Tm-%TdT%TH:%TM:%TS\n' | sort
```

Allowed SQLite aggregate-only checks:

```bash
sqlite3 /var/lib/9router/db/data.sqlite "
SELECT 'requestDetails_count', COUNT(*) FROM requestDetails;
SELECT 'requestDetails_min_ts', MIN(timestamp) FROM requestDetails;
SELECT 'requestDetails_max_ts', MAX(timestamp) FROM requestDetails;
SELECT 'requestDetails_avg_data_len', ROUND(AVG(length(data)), 2) FROM requestDetails;
SELECT 'requestDetails_max_data_len', MAX(length(data)) FROM requestDetails;
SELECT 'requestDetails_total_data_mb', ROUND(SUM(length(data))/1024.0/1024.0, 2) FROM requestDetails;
"
```

Forbidden SQLite evidence commands:

```bash
sqlite3 /var/lib/9router/db/data.sqlite "SELECT data FROM requestDetails LIMIT 1;"
sqlite3 /var/lib/9router/db/data.sqlite "SELECT * FROM requestDetails LIMIT 1;"
sqlite3 /var/lib/9router/db/data.sqlite ".dump requestDetails"
sqlite3 /var/lib/9router/db/data.sqlite "SELECT json_extract(data, '$.request') FROM requestDetails LIMIT 1;"
sqlite3 /var/lib/9router/db/data.sqlite "SELECT json_extract(data, '$.providerResponse') FROM requestDetails LIMIT 1;"
```

## Hard Rejection Criteria

Reject completion of any future autoprune implementation if any of these are true:

1. Raw `requestDetails.data` appears in evidence.
2. Raw prompt, message, completion, request body, response body, provider request, provider response, or streaming chunk appears in evidence.
3. Authorization, cookie, bearer token, API key, provider credential, DB password, storage key, JWT secret, Tailscale state, SSH key, decrypted env value, or shell history appears in evidence.
4. The implementation reads PM2 logs and writes matching lines into evidence.
5. The implementation uses `SELECT *`, `SELECT data`, `.dump`, or JSON extraction from `data`.
6. The implementation changes firewall, SSH, Tailscale, PM2 process config, provider config, or app bind address without explicit scope.
7. Public IPv4 `20128` returns an application response after the task.
8. `ss` shows `[::]:20128` while IPv6 INPUT remains default ACCEPT with no explicit protection.
9. `tailscaled.service` becomes inactive or no longer uses the known userspace networking posture.
10. `pm2-root.service` becomes inactive or the expected 9Router app is no longer online.
11. A prune script uses shell tracing (`set -x`) or logs full SQL output.
12. `ENABLE_REQUEST_LOGS=true` is present for app workers without a separate approved remediation.

## Recommended Security Acceptance Gate

Before prune:

- Capture aggregate-only DB metrics.
- Capture `ss`, iptables, ip6tables, Tailscale self status, and service active states.
- Scan the target evidence root for secret and payload patterns.
- Confirm no existing prune timer/unit is active unless explicitly expected.

During prune:

- Run only a bounded delete strategy by timestamp/count.
- Do not print row data.
- Do not print deleted row IDs unless there is a specific need; aggregate deleted count is enough.
- Avoid service restarts.

After prune:

- Re-capture aggregate-only DB metrics.
- Verify `requestDetails_count` and total data MB are within the accepted target.
- Verify `PRAGMA integrity_check` returns `ok`.
- Verify service/network boundary stayed unchanged.
- Re-run secret/payload evidence scans.
- Confirm no PM2 or journald log excerpts with payload content were copied into evidence.

## Boundary Compliance

| Boundary | Result |
|---|---|
| `AGENTS.md` read first | PASS |
| Read-only remote access | PASS |
| No DB mutation | PASS |
| No firewall/Tailscale/SSH mutation | PASS |
| No PM2/systemd restart | PASS |
| No env/secret value read | PASS |
| No `requestDetails.data` read | PASS |
| No PM2 log lines printed in this report | PASS |
| Local artifact written to requested path | PASS |

## Footer

P26 requestDetails autoprune security research, generated 2026-06-27. This report authorizes no runtime mutation. It is a security gate for future implementation and evidence discipline.
