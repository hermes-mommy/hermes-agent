# Gotify external docs research

## Scope
- Official docs, GitHub examples, and reputable deployment notes for a self-hosted Linux Gotify service.
- Focus: Docker deployment, app token handling, HTTP API usage, channel/priority semantics, and fallback architecture considerations.

## Citable patterns

### Docker deployment
- **Official docs recommend Docker as the simplest deployment path, with either `gotify/server` or `ghcr.io/gotify/server`**. The install page shows a one-line `docker run` flow and notes the image is multi-arch. [Source](https://gotify.net/docs/install) — confirms Docker is the primary deployment pattern and that the image supports Linux-friendly architectures.
- **Persist `/app/data`**. Official install docs state `/app/data` holds the SQLite database, application images, and cert files, and should be backed up when mounted to a host directory. [Source](https://gotify.net/docs/install) — use a host volume for durable state.
- **Prefer environment variables for containerized configuration**. The config docs say Docker deployments should use env vars instead of config files. [Source](https://gotify.net/docs/config) — this is the official container-oriented configuration pattern.
- **Reverse proxy is the normal production pattern when HTTPS is needed**. Official Nginx and Traefik docs show Gotify behind a proxy with WebSocket forwarding and host preservation. [Source](https://gotify.net/docs/nginx), [Source](https://gotify.net/docs/traefik) — the proxy terminates TLS and preserves WebSocket behavior.

### App token handling
- **Application tokens authenticate message senders**. The REST docs describe `POST /message` as authenticated with an application token passed via `X-Gotify-Key`. [Source](https://context7.com/gotify/server/llms.txt) — this is the canonical sender credential.
- **Applications are the sender identity; clients are receivers**. Official docs and issues distinguish that clients do not send messages; applications do. [Source](https://github.com/gotify/server/issues/276) — useful for architecture notes and avoiding misuse of client tokens.
- **Application creation returns a token**. `POST /application` requires a client token and returns an app token for future message sends. [Source](https://context7.com/gotify/server/llms.txt) — use this flow to provision sender identities.
- **Do not rely on client endpoints for sender auth**. GitHub issue guidance says application tokens are only meant for `/message`; other API calls return unauthorized. [Source](https://github.com/gotify/server/issues/652) — sender tokens are intentionally scoped.

### HTTP API usage
- **Core send endpoint is `POST /message`**. Official API docs show JSON payloads with `title`, `message`, optional `priority`, and `extras`. [Source](https://context7.com/gotify/server/llms.txt) — this is the main integration endpoint.
- **`priority` is numeric and defaults to the application default when omitted**. The official API docs describe `priority` as 0–10 and note that an app-level default applies when the field is not sent. [Source](https://context7.com/gotify/server/llms.txt), [Source](https://github.com/gotify/server/pull/578) — use explicit integers for consistent delivery behavior.
- **JSON typing is strict for `priority`**. GitHub issues show stringified integers are rejected with a 400 parsing error, while numeric values work. [Source](https://github.com/gotify/server/issues/642), [Source](https://github.com/gotify/server/issues/870) — webhook emitters must send numeric JSON, not quoted numbers.
- **`extras` is the extension mechanism for client/server metadata**. The API docs and issue examples show `extras` for click actions or richer notification metadata. [Source](https://context7.com/gotify/server/llms.txt), [Source](https://github.com/gotify/server/issues/806) — use JSON when you need extras.
- **Form-data or query-token patterns exist in the wild, but the official API norm is JSON + header auth**. Community examples show curl forms and query-token usage, but the official docs center on `X-Gotify-Key` plus JSON POST. [Source](https://context7.com/gotify/server/llms.txt), [Source](https://github.com/gotify/server/issues/429) — prefer the documented JSON/header path for reliability.

### Channel / priority semantics
- **Gotify is application-based, not topic-based**. Reputable notes and official feature descriptions emphasize that senders are applications and receivers are clients, rather than publish/subscribe topics. [Source](https://github.com/gotify/server/) — important when mapping workloads to notification sources.
- **Priority maps to urgency, not separate channels in server config**. The server exposes numeric priority values; Android behavior and “notification channel” style urgency are discussed in community docs and issues, with higher priorities used for critical alerts. [Source](https://selfhosting.sh/apps/gotify/), [Source](https://context7.com/gotify/server/llms.txt) — treat priority as the primary routing/urgency signal.
- **Application-level default priority exists and is honored only when payload omits `priority`**. This was added specifically for integrations that cannot set per-message priority. [Source](https://github.com/gotify/server/pull/578) — useful for low-flexibility emitters.
- **Priority 0 is effectively silent/lowest urgency**. Community deployment notes describe 0 as badge/log-like behavior and higher ranges as louder alerts. [Source](https://selfhosting.sh/apps/gotify/) — this aligns with practical Android usage, though server-side semantics remain numeric 0–10.

### Fallback architecture considerations
- **Use a reverse proxy with WebSocket support in front of Gotify**. Official proxy docs set `Upgrade`, `Connection`, and `Host` headers and keep timeouts long enough for streaming. [Source](https://gotify.net/docs/nginx) — this avoids websocket failures and origin checks.
- **Preserve the `Host` header when proxying**. The official nginx guide explicitly notes Gotify verifies host/origin for websocket connections. [Source](https://gotify.net/docs/nginx) — this is a common source of 403/stream issues.
- **Trust proxy IPs only when needed**. The config docs expose `trustedproxies` to recover the real client IP from forwarded headers. [Source](https://gotify.net/docs/config) — relevant behind Docker bridge networks or reverse proxies.
- **If TLS is terminated upstream, keep Gotify’s own SSL disabled**. Official nginx guidance recommends leaving `GOTIFY_SERVER_SSL_ENABLED=false` when nginx handles HTTPS. [Source](https://gotify.net/docs/nginx) — avoids duplicate TLS termination.
- **Prefer SQLite for small single-node installs, but remember it lives under `/app/data`**. Official install/config docs show SQLite as the default and indicate the data directory holds the DB. [Source](https://gotify.net/docs/install), [Source](https://gotify.net/docs/config) — for higher durability or concurrent operational needs, operators typically back it with host volume/backup discipline or switch to a DB supported by config.

## Practical deployment notes to carry forward
- Use Docker with a host-mounted data directory and env-var configuration for most Linux self-hosted installs. [Source](https://gotify.net/docs/install), [Source](https://gotify.net/docs/config)
- Treat sender tokens as application credentials and keep them out of client-side code paths. [Source](https://context7.com/gotify/server/llms.txt), [Source](https://github.com/gotify/server/issues/652)
- Send JSON to `/message` with numeric `priority` if the integration can do it; otherwise define an application default priority. [Source](https://context7.com/gotify/server/llms.txt), [Source](https://github.com/gotify/server/pull/578)
- Put Gotify behind a reverse proxy for HTTPS and websocket correctness. [Source](https://gotify.net/docs/nginx), [Source](https://gotify.net/docs/traefik)
- Use `extras` only when the consumer actually understands the metadata schema. [Source](https://context7.com/gotify/server/llms.txt), [Source](https://github.com/gotify/server/issues/806)

## Source URLs used
- https://gotify.net/docs/install
- https://gotify.net/docs/config
- https://gotify.net/docs/nginx
- https://gotify.net/docs/traefik
- https://context7.com/gotify/server/llms.txt
- https://github.com/gotify/server/
- https://github.com/gotify/server/issues/276
- https://github.com/gotify/server/issues/429
- https://github.com/gotify/server/issues/642
- https://github.com/gotify/server/issues/652
- https://github.com/gotify/server/issues/806
- https://github.com/gotify/server/issues/870
- https://github.com/gotify/server/pull/578
- https://selfhosting.sh/apps/gotify/
