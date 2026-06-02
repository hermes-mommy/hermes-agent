# Research Report: 9Router npm Package

**Date**: 2026-06-01  
**Researcher**: Librarian  
**Task**: P1-006 — Verify `9router` npm package, CLI binary, and installation details

---

## 1. Package Existence & Status

**Package `9router` on npmjs.com:** ✅ EXISTS

| Property | Value |
|----------|-------|
| Package Name | `9router` |
| npm Registry | https://www.npmjs.com/package/9router |
| Latest Version | **0.4.66** (published 2026-05-29) |
| Weekly Downloads | 32.4K |
| License | MIT |
| Unpacked Size | 44.6 MB |
| Total Files | 3,027 |
| Total Versions | 197 |
| First Published | 2026-01-03 |
| Dependencies | 5 (enquirer, node-forge, node-machine-id, react, react-dom) |

**Source:** [npmjs.com/package/9router](https://www.npmjs.com/package/9router)

---

## 2. GitHub Repository

**`decolua/9router`:** ✅ EXISTS — primary/official repository

| Property | Value |
|----------|-------|
| URL | https://github.com/decolua/9router |
| Default Branch | `master` |
| Created | 2026-01-05 |
| Last Push | 2026-05-31 (1 day ago) |
| Active | ✅ Very active — multiple releases per week |
| Stars | ~11K+ |
| Description | "Unlimited FREE AI coding. Connect Claude Code, Codex, Cursor, Cline, Copilot, Antigravity to FREE Claude/GPT/Gemini via 40+ providers" |

**Fork note:** Many forks exist (n9router, bluerouter, OmniRoute) but `decolua/9router` is the canonical upstream.

---

## 3. Docker Image

**Docker image available:** ✅ YES

| Registry | URL | Pull Command |
|----------|-----|-------------|
| Docker Hub | https://hub.docker.com/r/decolua/9router | `docker pull decolua/9router:latest` |
| GHCR | https://github.com/decolua/9router/pkgs/container/9router | `docker pull ghcr.io/decolua/9router:latest` |

- **Size**: 161.6 MB
- **Architecture**: linux/amd64 (GHCR has multi-platform amd64 + arm64)
- **Last update**: 3 days ago
- **Tags**: Tagged by Git tags (e.g., `0.4.59`, `0.4.52`)

**Docker quick start:**
```bash
docker run -d --name 9router -p 20128:20128 \
  -v "$HOME/.9router:/app/data" -e DATA_DIR=/app/data \
  decolua/9router:latest
```

---

## 4. Executable Binary Name

**Binary name: `9router`** (NOT `9-router` or `9Router`)

**Defined in** `cli/package.json`:
```json
"bin": {
  "9router": "./cli.js"
}
```

**Entry point:** `cli/cli.js` — a 27KB Node.js script with `#!/usr/bin/env node` shebang.

**How it works after `npm install -g 9router`:**
1. Runs `cli.js` which validates environment
2. Auto-heals SQLite runtime deps into `~/.9router/runtime`
3. Spawns a child Node.js process running `app/server.js` (Next.js standalone build)
4. The server process has `--max-old-space-size=6144` memory limit
5. Opens web browser to `http://localhost:20128/dashboard`

---

## 5. Installation Commands

**Recommended (global install):**
```bash
npm install -g 9router
9router
```

**Alternative (no install):**
```bash
npx 9router
```

---

## 6. Node.js Version Requirement

**Minimum:** `>=18.0.0`

From `cli/package.json`:
```json
"engines": {
  "node": ">=18.0.0"
}
```

Ubuntu 24.04 ships with Node.js 18+ or 20+ by default, so this is compatible.

---

## 7. Startup Command & CLI Options

**Default startup:** `9router`

**CLI options:**
```
Usage: 9router [options]

Options:
  -p, --port <port>   Port to run the server (default: 20128)
  -H, --host <host>   Host to bind (default: 0.0.0.0)
  -n, --no-browser    Don't open browser automatically
  -l, --log           Show server logs (default: hidden)
  -t, --tray          Run in system tray mode (background)
  --skip-update       Skip auto-update check
  -h, --help          Show this help message
  -v, --version       Show version
```

**For VPS (no-browser mode):**
```bash
9router --port 20128 --host 0.0.0.0 --no-browser
```

Or using env vars (preferred for systemd):
```bash
PORT=20128 HOSTNAME=0.0.0.0 NODE_ENV=production 9router --no-browser
```

---

## 8. Health Endpoint & Monitoring

**The API endpoint itself serves as health check:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `http://localhost:20128/v1/models` | GET | Returns available models in OpenAI format — reliable health check |
| `http://localhost:20128/dashboard` | GET | Web dashboard UI |
| `http://localhost:20128/v1/chat/completions` | POST | OpenAI-compatible chat API |

**Simple health check command for systemd `ExecStartPost` or monitoring:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:20128/v1/models
# Returns 200 when healthy
```

---

## 9. Environment Variables (for systemd)

From `.env.example` and README:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `JWT_SECRET` | auto-generated | ✅ | JWT signing secret for auth cookies |
| `INITIAL_PASSWORD` | `123456` | ✅ | First login password |
| `DATA_DIR` | `~/.9router` | ✅ | App data directory (SQLite DB location) |
| `PORT` | `20128` | No | Service port |
| `NODE_ENV` | `production` | No | Environment mode |
| `API_KEY_SECRET` | `endpoint-proxy-api-key-secret` | No | HMAC secret for API keys |
| `MACHINE_ID_SALT` | `endpoint-proxy-salt` | No | Stable machine ID hashing |
| `REQUIRE_API_KEY` | `false` | No | Enforce API key on `/v1/*` routes |
| `ENABLE_REQUEST_LOGS` | `false` | No | Enable request logging |
| `BASE_URL` | `http://localhost:20128` | No | Server-side base URL |
| `HOSTNAME` | `0.0.0.0` | No | Bind address |

---

## 10. Data Storage

| Platform | Path |
|----------|------|
| Linux/macOS (npm) | `~/.9router/db/data.sqlite` |
| Docker | `/app/data/db/data.sqlite` |
| Windows | `%APPDATA%/9router/db/data.sqlite` |

**SQLite database** — stores providers, combos, aliases, API keys, settings, usage history.

---

## 11. Systemd ExecStart Path Recommendation

For Ubuntu 24.04 VPS with `npm install -g 9router`:

```ini
[Service]
ExecStart=9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
Environment=NODE_ENV=production
Environment=DATA_DIR=/var/lib/9router
Environment=JWT_SECRET=<generated-secret>
Environment=INITIAL_PASSWORD=<set-password>
Environment=PORT=20128
Environment=HOSTNAME=0.0.0.0
```

Or using the direct Node.js path (if global npm bin is not in PATH):
```ini
ExecStart=/usr/bin/node /usr/lib/node_modules/9router/app/server.js
```

**Recommended:** Use the `9router` CLI binary approach above as it handles auto-healing of runtime deps and process management.

---

## 12. Summary

| Question | Answer |
|----------|--------|
| Does `9router` npm package exist? | ✅ Yes, version 0.4.66, 32.4K weekly downloads |
| Does `decolua/9router` GitHub repo exist? | ✅ Yes, actively maintained (~11K stars) |
| Is there a Docker image? | ✅ Yes, on Docker Hub and GHCR |
| Binary executable name? | `9router` (not `9-router`) |
| How to run after `npm install -g`? | Just run `9router` |
| Node.js requirement? | >= 18.0.0 |
| Default port? | 20128 |
| Health check endpoint? | `GET /v1/models` on port 20128 |

**Verdict:** `npm install -g 9router` is the correct and recommended installation method. The package is well-maintained with 197 versions and active daily development.