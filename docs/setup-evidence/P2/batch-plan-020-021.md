# P2 Batch 020–021 — Gotify + Discord Fallback

**Date:** 2026-06-01  
**Status:** Planning  
**Phase:** P2 Discord Bot (steps 20–21 of 21)  
**ADR:** ADR-022  
**AC:** AC-DISCORD-003 (SEV0 alert → thread within 15s), notifiable via Gotify  
**Budget:** $0 (self-hosted)

---

## 1. Known State

- P2-019 complete: notifications.py SEV routing matrix exists, send_notification() async function ready
- No existing Gotify code, Docker compose, or scripts in repo
- Docker unavailable locally (Windows); VPS deployment requires artifact-based split
- Port 8081 confirmed free (no conflict with Aizanta/Guinevere services)
- Docker-compose.yml will be created as deployment artifact (local test env config note)
- Gotify official docs confirm: Docker primary, POST /message with X-Gotify-Key, numeric priority

---

## 2. Research Inputs

| Report | Path | Key Findings |
|---|---|---|
| Local patterns | `docs/setup-evidence/P2/research/local-p2-020-021-patterns.md` | StepPrompts refer docker-compose.yml, /home/guinevere/config/gotify/, port 8081, `guinevere-net`, hardcoded password audited |
| External Gotify | `docs/setup-evidence/P2/research/gotify-external-docs.md` | Docker image gotify/server:latest, /app/data volume, X-Gotify-Key header, priority 0-10, env-var config |

---

## 3. Binding Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Default `app token`, not admin credentials | AC-SAFE-001 principle — app tokens are scoped per-application, admin credentials never in code |
| D2 | `gunicorn` not required, default Go server is lightweight | Gotify server is a single Go binary behind Caddy if exposed; for `guinevere-net` internal use, Go server suffices |
| D3 | `guinevere-net` Docker network | Existing Guinevere network — ensures inter-container resolution without port exposure to host |
| D4 | Port 8081 bound to `127.0.0.1` only | No public exposure; all access through host-local or Docker overlay |
| D5 | `gotify_fallback.py` with `httpx.AsyncClient` | Async discord.py runtime; httpx is already in project deps |
| D6 | Token via `os.environ["GOTIFY_APP_TOKEN"]`, set by systemd ExecStartPre SOPS decrypt | Same pattern as Discord bot token (D5 from P2-017 plan) |
| D7 | VPS split: docker-compose.yml is VPS-only artifact | Local testing uses mocked GotifyClient; real deployment on VPS |
| D8 | Sequential: P2-020 → P2-021 | P2-021 depends on P2-020 completion |
| D9 | Wire `gotify_fallback.send_fallback()` into `notifications.send_notification()` for SEV0/SEV1 | Minimal diff — add a fail-soft fallback call after the primary notification |
| D10 | `structlog` for all fallback events | Pattern consistent with existing logging throughout src/ |

---

## 4. Dependency Map

```
P2-020 (Gotify Docker + Python client)
  ├── Writes: docker-compose.yml artifact
  ├── Creates: tests/test_gotify_client.py (deterministic)
  └── No source-code touches (pure artifact)
  
P2-021 (gotify_fallback.py + notifications.py wire)
  ├── Creates: src/discord/gotify_fallback.py
  ├── Creates: tests/test_gotify_fallback.py
  ├── Edits: src/discord/notifications.py (add fallback call in send_notification)
  └── Edits: src/discord/colors.py (no change needed — NEUTRAL already exists)
```

**Blocking**: P2-021 waits for P2-020 auditor PASS.

---

## 5. Collision Scan

| Shared Resource | Owner | Risk |
|---|---|---|
| `src/discord/notifications.py` | P2-021 only | None — single owner |
| `src/discord/colors.py` | None needed | Already has NEUTRAL |
| `secrets/discord-secrets.yaml` (SOPS) | P2-020 only for docker-compose | Single append, no collision |
| `docs/setup-evidence/P2/` | Verifiers/evidence per step | Separate subdirectories |

**No collisions detected.**

---

## 6. P2-020 Plan — Gotify Docker Deployment + Python Client

### 6.1 Deliverable

Create deployment artifact + Python test client. No `src/` module changes.

### 6.2 Files

| Action | Path | Scope |
|---|---|---|
| Create (artifact) | `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` | VPS deployment compose file |
| Create | `tests/discord/test_gotify_client.py` | Deterministic httpx mock test |
| Create/update | `docs/setup-evidence/P2/STEP-P2-020/verification.md` | Evidence |
| Create | `docs/setup-evidence/P2/STEP-P2-020/p2-020-implementation-summary.md` | Summary |

### 6.3 Docker Compose Spec

```yaml
services:
  gotify:
    image: gotify/server:latest
    container_name: guinevere-gotify
    restart: unless-stopped
    networks:
      - guinevere-net
    ports:
      - "127.0.0.1:8081:80"
    volumes:
      - "/home/guinevere/data/gotify:/app/data"
    environment:
      - GOTIFY_DEFAULTUSER_NAME=admin
      - GOTIFY_DEFAULTUSER_PASS=${GOTIFY_ADMIN_PASSWORD}
```

Network: `guinevere-net` (external: true)

### 6.4 Python Test Client

Deterministic test using `unittest.mock.AsyncMock` for `httpx.AsyncClient`:

- `build_gotify_payload(title, message, priority) → dict`
- `async send_gotify(gotify_url, app_token, payload) → bool` — wrapped in try/except, returns False on failure
- `build_priority(severity) → int` — maps SEV0→10, SEV1→7, SEV2→5, SEV3→3, SEV4→1

### 6.5 Secret Handling

- `GOTIFY_ADMIN_PASSWORD` and `GOTIFY_APP_TOKEN` go into SOPS storage for deployment
- No plaintext in evidence, logs, or code
- docker-compose.yml references `${GOTIFY_ADMIN_PASSWORD}` for compose substitution

### 6.6 Validation

- `python -m py_compile tests/discord/test_gotify_client.py` — exit 0
- `python -m pytest tests/discord/test_gotify_client.py -v` — all pass
- LSP clean for test file
- Unsafe scan: no type ignore, no bare except, no token strings

---

## 7. P2-021 Plan — Gotify Fallback + Notification Wire

### 7.1 Deliverable

Create `gotify_fallback.py` module. Wire into `notifications.py` — SEV0/SEV1 only.

### 7.2 Files

| Action | Path | Scope |
|---|---|---|
| Create | `src/discord/gotify_fallback.py` | Async gotify client with structlog |
| Create | `tests/discord/test_gotify_fallback.py` | Deterministic tests |
| Edit | `src/discord/notifications.py` | Add fallback call in `send_notification` |
| Create/update | `docs/setup-evidence/P2/STEP-P2-021/verification.md` | Evidence |
| Create | `docs/setup-evidence/P2/STEP-P2-021/p2-021-implementation-summary.md` | Summary |

### 7.3 gotify_fallback.py Design

```python
GOTIFY_URL = "http://localhost:8081"
GOTIFY_APP_TOKEN = os.environ.get("GOTIFY_APP_TOKEN", "")

def build_gotify_payload(title: str, description: str, priority: int) -> dict
def send_fallback(title: str, description: str, severity: str) -> None  # Async
def get_priority(severity: str) -> int
```

`send_fallback()`:
- Reads env token
- Silently returns if no token set (graceful degradation)
- `httpx.AsyncClient.post(GOTIFY_URL + "/message", ...)`
- structlog: `gotify_fallback_attempt` / `gotify_fallback_sent` / `gotify_fallback_failed`
- No exceptions propagated (fail-soft)

### 7.4 notifications.py Wire

In `send_notification()`, after primary channel send succeeds:
```python
if payload.severity in ("SEV0", "SEV1"):
    await send_fallback(payload.title, payload.description, payload.severity)
```

No structural change. One import line + one conditional.

### 7.5 Validation

- LSP clean for both files
- py_compile clean
- Deterministic tests: env mock, httpx mock, priority mapping, token missing (returns False silently)
- P2-019 tests still pass after edit (no regression)
- Unsafe scan: no type ignore, no bare except, no token strings

---

## 8. Delegation Assignments

| Step | Implementation Owner | Scope | Must Not Touch |
|---|---|---|---|
| P2-020 | One Sisyphus-Junior (deep) | docker-compose artifact + test client | P2-021 files, src/ modules |
| P2-021 | One Sisyphus-Junior (deep) | gotify_fallback.py + notifications.py wire | Trackers, secrets, evidence structure |

---

## 9. Parent Verification

| Verifier | Per-Step Output Path | Scope |
|---|---|---|
| LSP/static | `docs/setup-evidence/P2/STEP-P2-0XX/verifiers/lsp-static-verifier.md` | py_compile, tests, import checks |
| Token/unsafe | `docs/setup-evidence/P2/STEP-P2-0XX/verifiers/token-unsafe-scan-verifier.md` | No token strings, no type ignores, no bare except |
| VPS/Aizanta | `docs/setup-evidence/P2/STEP-P2-0XX/verifiers/vps-aizanta-health-verifier.md` | VPS read-only health check (deferred to deployment) |

---

## 10. Auditor Matrix

| Step | Auditor Surface | Blocking Criteria |
|---|---|---|
| P2-020 | docker-compose artifact validity | Compose spec correctness, port security (127.0.0.1), network `guinevere-net`, no plaintext secrets |
| P2-020 | Python test client | Deterministic tests PASS, priority mapping correct, gotify URL format, fail-soft on connection error |
| P2-020 | Secret handling | No GOTIFY_ADMIN_PASSWORD/GOTIFY_APP_TOKEN in plaintext in any artifact |
| P2-021 | gotify_fallback module | send_fallback implemented async, token from env, fail-soft, structlog events, no exception propagation |
| P2-021 | notifications.py wire | SEV0/SEV1 fallback only, one import + conditional, no structural refactor, P2-019 tests still pass |
| P2-021 | Fallback behavior | Deterministic tests cover: env token missing → fails silently, httpx sends correct payload, priority maps correctly, failure logged not raised |

---

## 11. Rollback Plan

| Step | Rollback |
|---|---|
| P2-020 | `rm docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml tests/discord/test_gotify_client.py` |
| P2-021 | `rm src/discord/gotify_fallback.py tests/discord/test_gotify_fallback.py`; `git checkout src/discord/notifications.py` |

---

## 12. Execution Checklist

- [ ] Research wave complete
- [ ] Planner created and parent-read
- [ ] Todos synced
- [ ] Collision scan clear
- [ ] P2-020 implemented → verified → evidence → auditor PASS
- [ ] P2-021 implemented → verified → evidence → auditor PASS (P2-020 PASS required first)
- [ ] Trackers synced
- [ ] Final report delivered

---

*Planner parent-read: verify file exists > read fully > sync todos > begin implementation.*