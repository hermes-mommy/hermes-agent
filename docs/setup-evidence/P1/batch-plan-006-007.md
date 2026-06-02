# Batch Implementation Plan: STEP-P1-006 + STEP-P1-007

| Field | Value |
|---|---|
| **Plan ID** | BATCH-P1-006-007 |
| **Scope** | 9Router Installation & Configuration |
| **Phases** | P1 (LLM + Hermes Agent) |
| **Steps** | P1-006 (Install) → P1-007 (Config + Start) |
| **Status** | ⏳ Planned |
| **Created** | 2026-06-01 |
| **Executor** | Guinevere (mama) + sub-agents |
| **Est. Duration** | 3-5 hours total (2-3h install + 1-2h config) |

---

## 1. StepPrompts Bug Corrections — Must Fix Before Execution

| # | File | Line(s) | Current (Bug) | Corrected | Reason |
|---|---|---|---|---|---|
| C-01 | StepPrompts.md | 3697 | `sudo apt install -y nodejs npm` | Use NodeSource for Node.js 24.x (Active LTS) | Ubuntu repo gives EOL 18.x. Must get 24.x from NodeSource APT repo |
| C-02 | StepPrompts.md | 3731 | `After=network.target redis-guinevere.service` | `After=network-online.target` only | `redis-guinevere.service` does NOT exist. Guinevere Redis is Docker-based (`guinevere-redis` container). 9Router has no Redis dependency. |
| C-03 | StepPrompts.md | 3732 | `Requires=redis-guinevere.service` | Remove entire line | Same as C-02 — no Redis dependency. |
| C-04 | StepPrompts.md | 3742 | `ExecStart=/usr/local/bin/9router` | `ExecStart=9router --port 20128 --host 0.0.0.0 --no-browser --skip-update` | NodeSource prefix is `/usr` (not `/usr/local`). Actual binary will be at `/usr/bin/9router`. Using `9router` relies on systemd PATH. Also missing `--no-browser` and `--skip-update` for VPS mode. |
| C-05 | StepPrompts.md | 3741 | `Environment=HOST=0.0.0.0` | `Environment=HOSTNAME=0.0.0.0` | 9Router uses `HOSTNAME` env var. `HOST` is not recognized. The CLI flag is `--host` but env var is `HOSTNAME`. |
| C-06 | StepPrompts.md | 3740 | Missing `JWT_SECRET` and `INITIAL_PASSWORD` in Environment lines | Add `Environment=JWT_SECRET=<auto-gen>` and `Environment=INITIAL_PASSWORD=<auto-gen>` | 9Router REQUIRES these for dashboard auth. Without JWT_SECRET, login may fail. Without INITIAL_PASSWORD, first login defaults to `123456` (unsecure). |
| C-07 | StepPrompts.md | 3828 | `AGE_PUBKEY=$(grep "public key:" ~/.age/key.txt \| awk '{print $NF}')` | `AGE_PUBKEY=$(grep "public key:" /home/guinevere/secrets/age-key.txt \| awk '{print $4}')` | Actual path is `/home/guinevere/secrets/age-key.txt`, not `~/.age/key.txt`. Also awk field is `$4` not `$NF`. |
| C-08 | StepPrompts.md | 3762 | Evidence: `9router-config.yaml` | Replace with `9router-env-verify.md` | 9Router does NOT use YAML config. Configuration is via env vars + web dashboard. |
| C-09 | CHECKLIST.md | 180, 182, 184 | `curl http://localhost:8080/v1/models` | `curl http://localhost:20128/v1/models` | Port typo — 8080 should be 20128 throughout. Affects lines 180, 182, 184. |
| C-10 | CHECKLIST.md | 203 | `ss -tlnp \| grep 8080` -> `127.0.0.1:8080` | `ss -tlnp \| grep 20128` -> `0.0.0.0:20128` | Port 8080 typo. Also 9Router binds `0.0.0.0:20128` by default (VPS is Tailscale-only, no public exposure). |

### Correction Implementation Order

1. Apply C-01 through C-08 to `stepprompts/StepPrompts.md`
2. Apply C-09 and C-10 to `CHECKLIST.md`
3. Verify corrections with grep before P1-006 execution

---

## 2. Master Todo Per Step

### STEP P1-006: 9Router Installation (10 todos)

| # | Todo | Delegation | Evidence Path | Depends On |
|---|---|---|---|---|
| T6-01 | Check prerequisites: P1-005 complete, port 20128 free, guinevere.slice active | Parent verify | — | P1-005 ✅ |
| T6-02 | Install Node.js 24.x via NodeSource APT repo (GPG key + apt + verify) | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-006/nodejs-install.txt` | T6-01 |
| T6-03 | Verify Node.js + npm installed: `node --version`, `npm --version` | Parent verify | Same as T6-02 | T6-02 |
| T6-04 | Install 9Router globally: `sudo npm install -g 9router@0.4.66` | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-006/9router-install.txt` | T6-03 |
| T6-05 | Verify 9Router binary: `which 9router`, `9router --version` | Parent verify | Same as T6-04 | T6-04 |
| T6-06 | Generate JWT_SECRET + INITIAL_PASSWORD (random 32-char) | Parent generate | — | T6-05 |
| T6-07 | Create systemd unit at `/etc/systemd/system/guinevere-9router.service` (CORRECTED — no redis dep, HOSTNAME, --no-browser, --skip-update) | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-006/9router-systemd-unit.md` | T6-06 |
| T6-08 | Run `systemctl daemon-reload && systemctl enable guinevere-9router` | Execute sub-agent | Same as T6-07 | T6-07 |
| T6-09 | Create `/home/guinevere/config/9router/placeholder.env` documenting required env vars | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-006/9router-env-reference.md` | T6-08 |
| T6-10 | P1-006 implementation auditor gate + evidence write | Auditor sub-agent | `audit-reports/P1/STEP-P1-006/step-p1-006-auditor-report.md` | T6-09 |

### STEP P1-007: 9Router Configuration & Startup (8 todos)

| # | Todo | Delegation | Evidence Path | Depends On |
|---|---|---|---|---|
| T7-01 | Check prerequisites: P1-006 complete, SOPS age key available | Parent verify | — | P1-006 ✅ |
| T7-02 | Create SOPS-encrypted `.env.9router.sops` with JWT_SECRET, INITIAL_PASSWORD, DATA_DIR, PORT, HOSTNAME, API_KEY_SECRET | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-007/env-9router-created.md` | T7-01 |
| T7-03 | Decrypt to runtime `.env.9router` with `chmod 600` (for systemd EnvironmentFile) | Execute sub-agent | Same as T7-02 | T7-02 |
| T7-04 | Start 9Router service: `sudo systemctl start guinevere-9router` | Execute sub-agent | — | T7-03 |
| T7-05 | Verify service running: `systemctl status guinevere-9router`, `ss -tlnp \| grep 20128`, `journalctl -u guinevere-9router -n 30` | Parent verify | `docs/setup-evidence/P1/STEP-P1-007/9router-status.txt` | T7-04 |
| T7-06 | Health check: `curl http://localhost:20128/api/health` returns `{"ok":true}` | Parent verify | Same as T7-05 | T7-05 |
| T7-07 | Configure providers via Dashboard (Tailscale browser) OR REST API: OpenAI (GPT-5.5) + DeepSeek (deepseek-v4-flash) | Parent (browser/API) | `docs/setup-evidence/P1/STEP-P1-007/9router-providers-configured.md` | T7-06 |
| T7-08 | P1-007 implementation auditor gate + evidence write | Auditor sub-agent | `audit-reports/P1/STEP-P1-007/step-p1-007-auditor-report.md` | T7-07 |

---

## 3. Dependency Map

```
P1-003 (.venv + 61 packages)
    │
    ▼
P1-004 (Hermes Agent Install) + P1-005 (Hermes Config)
    │
    ▼
P1-006 (9Router Installation)  ◄── WE ARE HERE
    ├── Creates: Node.js 24.x + npm, global 9router package
    ├── Creates: guinevere-9router.service (systemd)
    ├── Requires: VPS sudo access, internet (NodeSource + npm registry)
    ├── Produces: systemd unit (installed + enabled but NOT started)
    └── Internal deps: T6-01 → T6-02 → T6-03 → T6-04 → T6-05 → T6-06 → T6-07 → T6-08 → T6-09 → T6-10
    │
    ▼
P1-007 (9Router Config + Start)
    ├── Creates: secrets/.env.9router.sops (SOPS-encrypted)
    ├── Requires: P1-006 complete, SOPS age key, provider API keys (OpenAI, DeepSeek)
    ├── Produces: running 9Router on port 20128, providers configured
    └── Internal deps: T7-01 → T7-02 → T7-03 → T7-04 → T7-05 → T7-06 → T7-07 → T7-08
```

**Sequential constraint**: P1-006 must complete before P1-007. Within each step, todos are strictly sequential (systemd unit depends on binary install, env file depends on secrets).

**Prerequisite chain**: P0 complete → P1-001 → P1-002 → P1-003 → P1-004 → P1-005 → **P1-006 → P1-007**

---

## 4. Prerequisites & Blockers

### Verified Prerequisites

| # | Prerequisite | Status | Check Command |
|---|---|---|---|
| PR-01 | P1-005 complete (Hermes config deployed) | ✅ P1-005 | `cat /home/guinevere/config/hermes/config.yaml` |
| PR-02 | Port 20128 FREE | ✅ Verified | `ss -tlnp \| grep 20128` → empty |
| PR-03 | `guinevere.slice` active | ✅ P0-009 | `systemctl status guinevere.slice` |
| PR-04 | curl + wget available on VPS | ✅ P0 baseline | `which curl && which wget` |
| PR-05 | `ca-certificates` installed (for GPG key SSL) | ✅ P0 baseline | `dpkg -l ca-certificates \| grep ^ii` |
| PR-06 | `gnupg` installed (for GPG key import) | ✅ P0 baseline | `dpkg -l gnupg \| grep ^ii` |
| PR-07 | `/home/guinevere/secrets/` exists + age key present | ✅ P0 | `ls /home/guinevere/secrets/age-key.txt` |
| PR-08 | `/home/guinevere/config/9router/` exists | ✅ P0-003 | `ls /home/guinevere/config/9router/` |
| PR-09 | VPS internet (HTTPS outbound) | ✅ P0 baseline | `curl -sI https://deb.nodesource.com` |
| PR-10 | SOPS binary available | ✅ P0-025 | `which sops && sops --version` |
| PR-11 | Disk space >= 2GB available for Node.js + npm + 9Router | ✅ 78GB free | `df -h /home/guinevere/` |
| PR-12 | No existing `/etc/systemd/system/guinevere-9router.service` | ✅ Clean slate | `ls /etc/systemd/system/guinevere-*` (only slice) |

### Potential Blockers

| # | Blocker | Trigger | Mitigation |
|---|---|---|---|
| B-01 | NodeSource GPG key download fails | `curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key` fails | Retry with `curl --retry 3`; check DNS/proxy; fallback to manual key download |
| B-02 | `apt update` fails after adding NodeSource repo | Incompatible repo URL | Verify `nodistro` suite is correct for Ubuntu 24.04. Check apt sources syntax. |
| B-03 | npm global install fails (permissions) | `npm install -g 9router` without `sudo` | Use `sudo npm install -g 9router` — npm prefix `/usr` requires root. |
| B-04 | npm registry timeout / 9router not found | `npm install -g 9router@0.4.66` returns 404 | Try without version pin: `npm install -g 9router`; check npmjs.com for latest version |
| B-05 | systemd unit syntax error | `systemctl daemon-reload` fails | Validate unit with `systemd-analyze verify /etc/systemd/system/guinevere-9router.service` |
| B-06 | SOPS encrypt fails — age key syntax mismatch | `sops --encrypt --age "$AGE_PUBKEY"` fails | Verify $AGE_PUBKEY format (should be `age1...`). Test with `echo test \| age -e -r "$AGE_PUBKEY"` |
| B-07 | 9Router fails to start (port conflict) | Service starts but crashes | Check `journalctl -u guinevere-9router -n 50`. Port 20128 is confirmed free per PR-02. |
| B-08 | 9Router auto-update check hangs startup | Service stuck at "Checking for updates" | `--skip-update` flag in ExecStart prevents this |
| B-09 | Provider API keys not ready (OpenAI/DeepSeek) | Dashboard config incomplete | Operator must have keys ready before T7-07. Can use placeholder + update later. |
| B-10 | INITIAL_PASSWORD not set, default 123456 used | First login with default password | Set INITIAL_PASSWORD in env file (T7-02). Default 123456 is documented but unsecure. |

---

## 5. Evidence Root Per Step

### P1-006 Evidence

```
docs/setup-evidence/P1/STEP-P1-006/
├── evidence.md                       # Parent evidence (12-section schema)
├── nodejs-install.txt                # NodeSource install log + node --version + npm --version
├── 9router-install.txt               # npm install -g output + which 9router + --version
├── 9router-systemd-unit.md           # Systemd unit file content (copy-verified)
├── 9router-env-reference.md          # Documented env vars for runtime reference
```

### P1-007 Evidence

```
docs/setup-evidence/P1/STEP-P1-007/
├── evidence.md                       # Parent evidence (12-section schema)
├── env-9router-created.md            # SOPS encrypt + decrypt verification (redacted)
├── 9router-status.txt                # systemctl status, ss -tlnp, journalctl output
├── 9router-providers-configured.md   # Provider config screenshot/curl evidence (redacted keys)
```

### Auditor Reports

```
audit-reports/P1/STEP-P1-006/
└── step-p1-006-auditor-report.md     # Independent auditor gate

audit-reports/P1/STEP-P1-007/
└── step-p1-007-auditor-report.md     # Independent auditor gate
```

---

## 6. DoD/AC Per Step

### P1-006 Definition of Done

| # | DoD Item | Verification Command | Expected |
|---|---|---|---|
| D6-01 | Node.js 24.x installed | `node --version` | `v24.x.x` (Active LTS) |
| D6-02 | npm installed (bundled with Node.js) | `npm --version` | Version string (10.x or 11.x) |
| D6-03 | 9router globally installed | `which 9router` | `/usr/bin/9router` |
| D6-04 | 9router version matches expected | `9router --version` or `npm ls -g 9router` | `0.4.66` |
| D6-05 | Systemd unit file exists | `systemctl cat guinevere-9router` | Shows valid unit with CORRECTED values (no redis, HOSTNAME, --no-browser, --skip-update) |
| D6-06 | Unit has NOT been started yet (enabled only) | `systemctl is-active guinevere-9router` | `inactive` |
| D6-07 | Unit is enabled for boot | `systemctl is-enabled guinevere-9router` | `enabled` |
| D6-08 | Unit syntax valid | `systemd-analyze verify /etc/systemd/system/guinevere-9router.service` | No errors |
| D6-09 | No REDIS dependency in unit | `grep redis /etc/systemd/system/guinevere-9router.service` | Empty |
| D6-10 | Unit includes `Slice=guinevere.slice` | `grep Slice /etc/systemd/system/guinevere-9router.service` | `Slice=guinevere.slice` |
| D6-11 | Unit has `--no-browser` and `--skip-update` in ExecStart | `grep ExecStart /etc/systemd/system/guinevere-9router.service` | Includes both flags |
| D6-12 | LSP diagnostics clean | `lsp_diagnostics` on unit file (if supported) or manual review | No errors on systemd unit |
| D6-13 | Evidence files written | `ls docs/setup-evidence/P1/STEP-P1-006/` | evidence.md + artifacts |
| D6-14 | Auditor gate PASS | Read auditor report | PASS verdict |

### P1-007 Definition of Done

| # | DoD Item | Verification Command | Expected |
|---|---|---|---|
| D7-01 | SOPS-encrypted env file exists | `sops -d /home/guinevere/code/guinevere/secrets/.env.9router.sops` | Decrypts successfully, shows NINE_ROUTER_API_KEY + JWT_SECRET + INITIAL_PASSWORD |
| D7-02 | Runtime env file exists with correct perms | `stat -c '%a' /home/guinevere/code/guinevere/secrets/.env.9router` | `600` |
| D7-03 | Service running | `systemctl is-active guinevere-9router` | `active` |
| D7-04 | Listening on port 20128 | `ss -tlnp \| grep 20128` | Shows `9router` or `node` process |
| D7-05 | Health endpoint responds | `curl -s http://localhost:20128/api/health` | `{"ok":true}` |
| D7-06 | Models endpoint responds | `curl -s http://localhost:20128/v1/models \| python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))"` | Integer > 0 (models listed) |
| D7-07 | GPT-5.5 model available | `curl -s http://localhost:20128/v1/models \| grep gpt-5.5` | Non-empty |
| D7-08 | DeepSeek V4 Flash model available | `curl -s http://localhost:20128/v1/models \| grep deepseek-v4-flash` | Non-empty |
| D7-09 | Service journal has no ERROR entries | `journalctl -u guinevere-9router -n 50 --no-pager \| grep -i error` | Empty (or expected startup warnings only) |
| D7-10 | Providers configured via Dashboard or API | Documented in evidence | Provider connections exist for OpenAI + DeepSeek |
| D7-11 | 9Router providers-configured evidence redacted | Grep evidence for API keys | No plaintext API keys in evidence files |
| D7-12 | Auditor gate PASS | Read auditor report | PASS verdict |

**Acceptance Criteria**: AC-CORE-003 (GPT-5.5 via 9Router for core reasoning), AC-CORE-004 (DeepSeek V4 Flash via 9Router for sub-agents)

---

## 7. ADR & Docs Referenced

### ADRs

| ADR | Title | Relevance | Binding Constraints |
|---|---|---|---|
| ADR-004 | Primary LLM Model Selection | P1-007 (configure GPT-5.5 via 9Router) | ✅ MUST configure GPT-5.5 as primary via 9Router |
| ADR-005 | LLM Router & Failover Strategy | P1-006 (9Router as sole router), P1-007 (no OpenRouter multiprovider) | ✅ 9Router-only with queue/retry/degrade; no OpenRouter multiprovider |
| ADR-006 | Sub-Agent LLM Model Strategy | P1-007 (configure DeepSeek V4 Flash via 9Router) | ✅ MUST configure DeepSeek V4 Flash for sub-agents |
| ADR-014 | VPS & Container Architecture | P1-006 (systemd unit under guinevere.slice) | ✅ Service MUST be under guinevere.slice |
| ADR-015 | Secrets Management | P1-007 (SOPS-encrypted .env.9router.sops) | ✅ API keys MUST be SOPS-encrypted at rest |
| ADR-028 | LLM Router Outage — Three-Tier Fallback | P1-007 (9Router primary, OpenRouter fallback configured) | ✅ Fallback chain documented in config |

### Docs

| Doc | Relevance |
|---|---|
| PersonaSafetyPolicy v1.0 | P1-007 dashboard access via Tailscale (consent boundary — surveillance layer not yet active) |
| SystemPromptMaster v1.1 | P1-007 API routing configured for prompt delivery (through Hermes, not 9Router) |
| APIIntegration v2.0 | P1-006/P1-007: 9Router endpoint at `http://localhost:20128/v1` |
| TechnicalArchitecture v2.0 | P1-006: 9Router architectural placement, systemd service pattern |
| CHECKLIST.md | §3.2 P1-006/P1-007 verification rows (port typo must be fixed first) |
| PROGRESS.md | P1-006/P1-007 status rows (update after completion) |
| AGENTS.md | Sub-agent delegation patterns, auditor gate requirement, file-based output |

---

## 8. Risk Assessment

| # | Risk | Probability | Severity | Mitigation |
|---|---|---|---|---|
| R-01 | NodeSource GPG key down / changed URL | Low | High | Pre-download key; use nodesource.com fallback script; manual key import |
| R-02 | Node.js 24.x incompatible with Ubuntu 24.04 | Low | High | Tested in research (DEV_README confirms Noble support). 26.x is riskier — we use 24.x LTS. |
| R-03 | 9Router npm install fails (44.6MB unpacked, network heavy) | Low | Medium | Retry with `--prefer-offline`; use Docker image as fallback |
| R-04 | 9Router v0.4.66 has breaking changes from assumed API | Low | Medium | Test health endpoint first; adjust systemd unit if CLI flags changed |
| R-05 | SOPS path mismatch (StepPrompts bug C-07) | Medium | Medium | Already corrected in plan; verify $AGE_PUBKEY content before encrypt |
| R-06 | Dashboard login fails (JWT_SECRET/INITIAL_PASSWORD mismatch) | Low | Medium | Set both in env file; if login fails, generate new JWT_SECRET and restart |
| R-07 | Provider API keys not available (OpenAI/DeepSeek) during execution | Medium | High | Document as deliberate pause point (T7-07). Can start service without providers configured. |
| R-08 | Accidentally committing SOPS-encrypted or plaintext secrets to evidence | Low | High | Evidence files must be REDACTED. Always use `sops -d` piped, never write decrypted content. |
| R-09 | npm global prefix write permission (need sudo) | High | Low | `sudo npm install -g` — documented. Don't try as non-root. |
| R-10 | systemd unit PATH resolution for `9router` binary | Low | Medium | Use `/usr/bin/9router` absolute path in ExecStart instead of bare `9router` |

---

## 9. Gotchas & Edge Cases

| # | Gotcha | Detail | Mitigation |
|---|---|---|---|
| G-01 | **StepPrompts uses `ExecStart=/usr/local/bin/9router` but NodeSource prefix is `/usr`** | NodeSource installs to `/usr/bin/`. The binary will be at `/usr/bin/9router`, NOT `/usr/local/bin/9router`. | Use absolute path `/usr/bin/9router` in ExecStart. Or rely on systemd PATH + bare `9router` (PATH includes /usr/bin by default in systemd). |
| G-02 | **NodeSource GPG key has a specific import path** | `nodesource-repo.gpg.key` is a separate key file. Must download to `/etc/apt/keyrings/nodesource.gpg` (dearmored). | Use exact commands from NodeSource DEV_README. Don't use `curl -fsSL https://deb.nodesource.com/setup_24.x \| bash -` (piped script is less secure). |
| G-03 | **npm registry may need `--registry` fallback** | China/restricted networks block npm registry. VPS is Hetzner (Germany) — should be fine. | If fails, try `npm install -g 9router --registry https://registry.npmjs.org/` |
| G-04 | **9Router stores API keys in PLAINTEXT SQLite** | `~/.9router/db/data.sqlite` stores provider API keys unencrypted. Systemd user is `guinevere` — filesystem permissions are the only protection. | Document in security notes. Ensure `DATA_DIR=/home/guinevere/.9router` has `chmod 700 guinevere:guinevere`. |
| G-05 | **Dashboard config requires browser via Tailscale** | P1-007 T7-07 needs a browser on the Tailscale network to access `http://100.94.104.22:20128/dashboard`. REST API alternative exists but is less tested. | Prefer REST API for headless config (documented in `9router-provider-setup.md` research). Use browser as fallback. |
| G-06 | **9Router `HOST` vs `HOSTNAME` env var confusion** | StepPrompts uses `HOST=0.0.0.0`. 9Router `.env.example` uses `HOSTNAME=0.0.0.0`. CLI uses `--host`. | Use `HOSTNAME=0.0.0.0` in env file AND `--host 0.0.0.0` in ExecStart for defense in depth. |
| G-07 | **SSH session may disconnect during npm install** | `npm install -g 9router` downloads 44.6MB with 3027 files. SSH session timeout could kill the process. | Use `tmux` or `nohup` for long-running install. Or use `screen`. |
| G-08 | **systemd `ExecStart` with bare `9router` needs full PATH** | systemd services run with minimal PATH: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games` — `/usr/bin` is included, so bare `9router` works IF NodeSource prefix=/usr. | Verify with `systemctl show guinevere-9router \| grep Environment=.*PATH` or just use absolute path `/usr/bin/9router`. |
| G-09 | **`systemctl enable` needs sudo but current user may not have passwordless sudo** | VPS user `guinevere` likely has sudo. | Pre-check with `sudo -n echo "OK"` before starting. |
| G-10 | **Evidence for 9router-config.yaml from StepPrompts is wrong filetype** | StepPrompts claims `9router-config.yaml` as evidence but 9Router uses env vars + Dashboard, not YAML config. | Replace with `9router-env-reference.md` documenting all env vars. |

---

## 10. Delegation Assignment Per Todo

| Todo | Delegated To | Skill/Load | Justification |
|---|---|---|---|
| T6-01 | Parent verify | — | Simple prerequisite check |
| T6-02 | Execute sub-agent | `task(category='execute', ...)` | Remote SSH commands; sequential apt operations |
| T6-03 | Parent verify | — | Simple `node --version` check |
| T6-04 | Execute sub-agent | `task(category='execute', ...)` | `sudo npm install -g 9router@0.4.66` — sequential |
| T6-05 | Parent verify | — | Simple `which 9router` check |
| T6-06 | Parent generate | — | `openssl rand -base64 32` on VPS (or locally) |
| T6-07 | Implementation sub-agent | `task(category='implementation', ...)` | Multi-line systemd unit file; use `filesystem_write_file` for unit content, then SSH deploy |
| T6-08 | Execute sub-agent | `task(category='execute', ...)` | Two sequential systemctl commands |
| T6-09 | Execute sub-agent (or parent) | `task(category='execute', ...)` | Single-file write for env reference doc |
| T6-10 | Auditor sub-agent | `task(category='auditor', ...)` | Independent audit gate required per AGENTS.md §4 |
| T7-01 | Parent verify | — | Simple prerequisite check |
| T7-02 | Implementation sub-agent | `task(category='implementation', ...)` | SOPS encrypt; sensitive — must use secure temp file pattern |
| T7-03 | Execute sub-agent (same as T7-02) | Same task | `sops --decrypt` to runtime file + `chmod 600` |
| T7-04 | Execute sub-agent | `task(category='execute', ...)` | `sudo systemctl start guinevere-9router` |
| T7-05 | Parent verify | — | Read status + ss + journalctl |
| T7-06 | Parent verify | — | `curl` health endpoint |
| T7-07 | Parent (browser/API) OR sub-agent | Parent prefers REST API; browser if API fails | Headless REST API via curl (POST /api/providers); browser via Tailscale as fallback |
| T7-08 | Auditor sub-agent | `task(category='auditor', ...)` | Independent audit gate |

**Collision note**: No shared writers between T6-02 through T6-10 and T7-02 through T7-08 — they write to different paths and different contexts.

---

## 11. Resource/Collision Scan

### Ports

| Port | Service | Conflict Risk |
|---|---|---|
| None | P1-006 (install only) | ✅ No ports used |
| 20128 | P1-007 (start 9Router) | ✅ Confirmed FREE (PR-02). 9Router will bind here. |

### Filesystem Paths

| Path | Step | Action | Collision Risk |
|---|---|---|---|
| `/home/guinevere/code/guinevere/secrets/.env.9router.sops` | P1-007 | CREATE | ✅ Clean slate (does not exist) |
| `/home/guinevere/code/guinevere/secrets/.env.9router` | P1-007 | CREATE | ✅ Clean slate (does not exist) |
| `/etc/systemd/system/guinevere-9router.service` | P1-006 | CREATE | ✅ Clean slate (no guinevere-* services) |
| `/usr/bin/9router` | P1-006 | CREATE (npm global) | ✅ Clean slate (no 9router binary) |
| `/home/guinevere/.9router/` | P1-007 | CREATE (by 9Router at first run) | ✅ Clean slate |
| `/home/guinevere/config/9router/placeholder.env` | P1-006 | CREATE | ✅ Directory exists (P0-003), file is new |
| `docs/setup-evidence/P1/STEP-P1-006/` | P1-006 | CREATE | ⚠️ Check if stale from previous partial run |
| `docs/setup-evidence/P1/STEP-P1-007/` | P1-007 | CREATE | ⚠️ Check if stale |
| `audit-reports/P1/STEP-P1-006/` | P1-006 | CREATE | ⚠️ Check if stale |
| `audit-reports/P1/STEP-P1-007/` | P1-007 | CREATE | ⚠️ Check if stale |
| PROGRESS.md | Both | UPDATE | Parent-only edit |
| CHECKLIST.md | Both | UPDATE | Parent-only edit (with port fixes) |

### System Packages

| Package | Step | Action | Notes |
|---|---|---|---|
| `nodejs` (NodeSource 24.x) | P1-006 | INSTALL | Replaces hypothetical apt nodejs 18.x |
| `npm` (bundled with nodejs) | P1-006 | INSTALL | Bundled in NodeSource nodejs package |
| 9router | P1-006 | INSTALL | npm global install |

### Shared Writers (Collision Scan)

| File | Writers | Mitigation |
|---|---|---|
| `/etc/systemd/system/guinevere-9router.service` | T6-07 only | Single owner |
| `secrets/.env.9router.sops` | T7-02 only | Single owner |
| PROGRESS.md | Parent only after both steps | Sequence |
| CHECKLIST.md | Parent only (fix port typos first) | Sequence: fix typos → update after each step |
| `evidence.md` per step | Parent only after each step | Sequence |

---

## 12. Aizanta Impact Analysis

### Baseline (Before P1-006)

```
Aizanta containers: aizanta-bot, aizanta-nginx, aizanta-frontend, aizanta-postgres, aizanta-redis
Guinevere containers: guinevere-redis, guinevere-pgbouncer, guinevere-postgres
All healthy, 8 days uptime
```

### Impact Assessment

| Impact | Assessment |
|---|---|
| Aizanta services touched? | ❌ No — 9Router is a new service on port 20128. No Aizanta services use this port. |
| Aizanta ports affected? | ❌ No — Aizanta uses 80/443 (nginx), 5432 (postgres), 6379 (redis). 9Router on 20128 doesn't conflict. |
| Aizanta Docker containers? | ❌ No — Node.js + npm + 9Router are host-installed, not Docker. |
| Aizanta databases? | ❌ No — 9Router uses SQLite at `~/.9router/db/data.sqlite`, not PostgreSQL or Redis. |
| Aizanta Redis? | ❌ No — 9Router has no Redis dependency (redis-guinevere.service bug already corrected). |
| Aizanta nginx? | ⚠️ Low — if nginx is configured as reverse proxy for all ports, check if 20128 needs proxying. Not needed now (direct Tailscale access). |
| Aizanta disk contention? | ⚠️ Low — Node.js 24.x ~80MB, npm cache ~100MB, 9Router ~45MB unpacked. Total <250MB. 78GB free. |
| Aizanta network? | ❌ No |
| Aizanta CPU/memory? | ⚠️ Low — 9Router runtime uses ~200-500MB RAM. 13GiB available. |

### `ss -tlnp` Port Scan Formula (Before/After)

```bash
# BEFORE (baseline — already captured in vps-state-pre-p1-006.md)
# ss -tlnp shows: 6379 (Redis), 80 (Nginx), 5432 (PostgreSQL), 22 (SSH)

# AFTER P1-007
ss -tlnp | grep 20128
# Expected: LISTEN 0 511 0.0.0.0:20128 0.0.0.0:* users:(("node",pid=XXXX,fd=XX))
```

### `docker ps` Formula (Before/After)

```bash
# BEFORE (baseline)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "aizanta|guinevere"
# Expected: 9 containers, all healthy

# AFTER P1-006/P1-007
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "aizanta|guinevere"
# Expected: UNCHANGED — Node.js/9Router is host-installed, not Docker
```

**Verdict**: P1-006 and P1-007 have **zero Aizanta impact**. No services touched, no ports conflicted, no containers modified, no databases accessed.

---

## 13. Secret Handling Plan

| Secret | Exposure Risk | Handling |
|---|---|---|
| OpenAI API key | ⚠️ HIGH (stored plaintext in 9Router SQLite) | Never in evidence. Operator provides at T7-07. 9Router stores in `~/.9router/db/data.sqlite` plaintext. Rely on filesystem perms (`chmod 700`). |
| DeepSeek API key | ⚠️ HIGH (same as above) | Same as OpenAI key. |
| `JWT_SECRET` | ⚠️ HIGH (dashboard auth secret) | SOPS-encrypted in `.env.9router.sops`. Decrypted to `.env.9router` with `chmod 600`. |
| `INITIAL_PASSWORD` | ⚠️ HIGH (dashboard login) | Same as JWT_SECRET — SOPS-encrypted. |
| `API_KEY_SECRET` | ⚠️ MEDIUM (used for generating endpoint API keys) | Same SOPS pattern. |
| `NINE_ROUTER_API_KEY` | ⚠️ MEDIUM (StepPrompts placeholder key) | Currently a placeholder (`PLACEHOLDER_KEY`). Replace with real key in future. Not exposed to external services. |

### SOPS Encrypt Procedure (T7-02)

```bash
# SECURE TEMP FILE PATTERN — DO NOT SKIP
cd /home/guinevere/code/guinevere

# Get age public key
AGE_PUBKEY=$(grep "public key:" /home/guinevere/secrets/age-key.txt | awk '{print $4}')

# Create temp env file (mktemp ensures secure perms)
TMPFILE=$(mktemp)
cat > "$TMPFILE" << 'EOF'
JWT_SECRET=<random-32-char>
INITIAL_PASSWORD=<random-32-char>
DATA_DIR=/home/guinevere/.9router
PORT=20128
HOSTNAME=0.0.0.0
NODE_ENV=production
API_KEY_SECRET=<random-32-char>
REQUIRE_API_KEY=false
ENABLE_REQUEST_LOGS=true
NINE_ROUTER_API_KEY=PLACEHOLDER_KEY
EOF

# Encrypt with SOPS + age
sops --encrypt --age "$AGE_PUBKEY" "$TMPFILE" > secrets/.env.9router.sops

# Securely delete temp file
rm -f "$TMPFILE"
# Verify encrypted file exists and decrypts
sops -d secrets/.env.9router.sops > /dev/null && echo "ENCRYPTION OK"
```

### Evidence Safety Rules

- Never write decrypted API keys to evidence files
- Evidence for provider config: use `curl -s http://localhost:20128/api/providers | python3 -c "import sys,json; [print(p['provider'],p['testStatus']) for p in json.load(sys.stdin)]"` — shows provider names and test status WITHOUT keys
- If screenshots of dashboard are captured, redact API key fields
- Auditor must check for accidentally exposed secrets in evidence

---

## 14. Destructive Action List

| # | Action | Step | Destructive? | Approval Needed |
|---|---|---|---|---|
| D-01 | `sudo apt install -y nodejs` (overwrites if exists) | P1-006 | ⚠️ Low (system package) | No — Node.js not installed |
| D-02 | `sudo npm install -g 9router` (creates /usr/bin/9router) | P1-006 | ⚠️ Low (new binary) | No |
| D-03 | `systemctl daemon-reload` | P1-006 | ❌ Not destructive | No |
| D-04 | `sudo systemctl enable guinevere-9router` | P1-006 | ❌ Not destructive | No |
| D-05 | `rm -f /tmp/env-9router*` (temp files) | P1-007 | ❌ Not destructive (temp) | No |
| D-06 | Overwrite evidence (if stale) | Both | ⚠️ Low (versioned) | No |
| D-07 | `sudo systemctl start guinevere-9router` (first start) | P1-007 | ❌ Not destructive | No — service is firewalled by Tailscale |
| D-08 | Overwrite `.env.9router.sops` (if exists) | P1-007 | ⚠️ Low (encrypted) | No — new file |
| D-09 | Remove step directory for rollback | Both | ⚠️ Medium (evidence loss) | Yes — per rollback protocol |

---

## 15. Rollback Plan

### P1-006 Rollback (Node.js + 9Router + systemd)

```bash
# Step 1: Remove systemd service
sudo systemctl stop guinevere-9router 2>/dev/null || true
sudo systemctl disable guinevere-9router 2>/dev/null || true
sudo rm -f /etc/systemd/system/guinevere-9router.service
sudo systemctl daemon-reload

# Step 2: Uninstall 9Router globally
sudo npm uninstall -g 9router

# Step 3: Remove Node.js 24.x (NodeSource)
sudo rm -f /etc/apt/sources.list.d/nodesource.list
sudo rm -f /etc/apt/keyrings/nodesource.gpg
sudo apt remove -y nodejs npm 2>/dev/null || true
sudo apt autoremove -y

# Step 4: Remove local data and evidence
rm -rf /home/guinevere/.9router
rm -rf /home/guinevere/config/9router/*
rm -rf docs/setup-evidence/P1/STEP-P1-006/
rm -rf audit-reports/P1/STEP-P1-006/

# Step 5: Verify clean slate
which node  # expected: not found
which 9router  # expected: not found
ls /etc/systemd/system/guinevere-9router.service  # expected: not found
```

**Re-run safety**: P1-006 is **not fully idempotent** — NodeSource repo addition is idempotent (apt handles duplicates), but npm global install re-downloads 44.6MB each time. Systemd unit is overwritten cleanly.

### P1-007 Rollback (env + service start)

```bash
# Step 1: Stop and disable service
sudo systemctl stop guinevere-9router
sudo systemctl disable guinevere-9router

# Step 2: Remove env files
rm -f /home/guinevere/code/guinevere/secrets/.env.9router.sops
rm -f /home/guinevere/code/guinevere/secrets/.env.9router

# Step 3: Remove 9Router data (providers, config)
rm -rf /home/guinevere/.9router

# Step 4: Remove evidence
rm -rf docs/setup-evidence/P1/STEP-P1-007/
rm -rf audit-reports/P1/STEP-P1-007/

# Step 5: Verify
ss -tlnp | grep 20128  # expected: empty
systemctl is-active guinevere-9router  # expected: inactive
```

**Re-run safety**: P1-007 is **idempotent** — re-running recreates env files and reconfigures providers.

### Recovery Notes

| Scenario | Recovery Action |
|---|---|
| NodeSource GPG key import fails | Download key manually; use `curl -fsSL https://deb.nodesource.com/setup_24.x \| sudo bash` as emergency fallback |
| npm install 9router fails | Switch to Docker: `docker run -d --name 9router -p 20128:20128 -v $HOME/.9router:/app/data decolua/9router:latest` |
| systemd unit syntax error | Fix `oldString`/`newString` in unit file; re-run `systemctl daemon-reload` |
| 9Router fails to start (crash loop) | Check `journalctl -u guinevere-9router -n 50 --no-pager`; fix env vars; restart |
| Dashboard login fails | Verify JWT_SECRET + INITIAL_PASSWORD in .env.9router; restart service |
| Provider config fails via Dashboard | Use REST API: `POST /api/providers` with curl (skip browser entirely) |

---

## 16. Validation Commands

### Pre-flight Commands (Before P1-006)

```bash
# SSH to VPS
ssh guinevere-vps

# Verify P1-005 complete
cat /home/guinevere/config/hermes/config.yaml | head -5

# Verify port free
ss -tlnp | grep 20128

# Verify guinevere.slice active
systemctl is-active guinevere.slice

# Verify clean systemd state
ls /etc/systemd/system/guinevere-*

# Check disk
df -h /home/guinevere/

# Check sudo (no-password mode)
sudo -n echo "sudo OK"
```

### P1-006 Post-Step Validation

```bash
# Verify Node.js
node --version  # v24.x.x
npm --version   # 10.x or 11.x

# Verify 9Router
which 9router           # /usr/bin/9router
9router --version       # 0.4.66 or latest

# Verify systemd unit
systemctl cat guinevere-9router | grep -E "ExecStart|After|Requires|Slice|Environment"
# Expected:
#   ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
#   After=network-online.target  (NOT redis-guinevere.service)
#   (no Requires= line for redis)
#   Slice=guinevere.slice
#   Environment=PORT=20128
#   Environment=HOSTNAME=0.0.0.0

# Verify unit syntax
systemd-analyze verify /etc/systemd/system/guinevere-9router.service

# Verify unit enabled (but NOT started)
systemctl is-enabled guinevere-9router  # enabled
systemctl is-active guinevere-9router   # inactive (expected!)
```

### P1-007 Post-Step Validation

```bash
# Verify service running
systemctl status guinevere-9router | head -10
# Expected: active (running)

# Verify port listening
ss -tlnp | grep 20128
# Expected: LISTEN 0 511 0.0.0.0:20128

# Health check
curl -s http://localhost:20128/api/health
# Expected: {"ok":true}

# Models endpoint
curl -s http://localhost:20128/v1/models | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total models: {len(data.get(\"data\", []))}')
models = [m['id'] for m in data.get('data', [])]
if any('gpt-5.5' in m for m in models):
    print('✅ GPT-5.5 available')
if any('deepseek-v4-flash' in m for m in models):
    print('✅ DeepSeek V4 Flash available')
"

# Check journal for errors
journalctl -u guinevere-9router -n 30 --no-pager | grep -iE "error|fail|traceback"
# Expected: empty (or benign warnings)

# Check journal for secrets leakage
journalctl -u guinevere-9router -n 100 --no-pager | grep -iE "sk-[a-zA-Z0-9]|api_key"
# Expected: empty (no API keys in logs)

# Providers via API
curl -s http://localhost:20128/api/providers | python3 -c "
import sys, json
providers = json.load(sys.stdin)
for p in providers:
    print(f'  {p[\"provider\"]}: {p[\"testStatus\"]}')
"
```

### Evidence Validation

```bash
# Check all evidence exists
ls -la docs/setup-evidence/P1/STEP-P1-006/
ls -la docs/setup-evidence/P1/STEP-P1-007/
ls -la audit-reports/P1/STEP-P1-006/
ls -la audit-reports/P1/STEP-P1-007/
```

### Aizanta Safety Check

```bash
# Before and after check
docker ps | grep -E "aizanta|guinevere" | wc -l
# Expected: 9 containers (unchanged before/after)
systemctl status aizanta-* 2>&1 | head -3
# Expected: all healthy
```

---

## 17. Security Notes (API Keys in Plaintext SQLite)

### Critical Finding

9Router stores provider API keys in **plaintext** in its SQLite database at `~/.9router/db/data.sqlite`. This is per 9Router's architecture — there is no encryption-at-rest for provider secrets.

### Risk Assessment

| Factor | Status |
|---|---|
| Exposure surface | 🔴 Local VPS only (no public ports). But any SSH compromise = all API keys exposed. |
| Filesystem protection | 🟢 `DATA_DIR=/home/guinevere/.9router` with `chmod 700` (guinevere user only). systemd service runs as `guinevere`. |
| Log leakage risk | 🟢 Journald should NOT log API keys if 9Router doesn't log them. Verify with `journalctl -u guinevere-9router \| grep -iE 'sk-'`. |
| Backup exposure | 🔴 Restic backups include `~/.9router/`. API keys in SQLite are backed up unencrypted. |
| Auditor access | 🟢 Only operator (Faiz) and authorized agents access the VPS via Tailscale. |

### Recommended Actions (Deferred)

1. **ADR or operator decision**: Accept risk (keys are filesystem-protected on a Tailscale-only VPS) OR set `REQUIRE_API_KEY=true` with dashboard-generated keys for client-auth (provider keys still plaintext).
2. **Backup exclusion**: Add `~/.9router/db/data.sqlite` to restic backup exclusion list (or encrypt backup).
3. **Post-MVP**: Consider 9Router fork/plugin that encrypts provider secrets at rest using SOPS or similar.
4. **Regular audit**: Include `grep -r 'sk-' ~/.9router/` in periodic security scans.

### What We Do Now

- Set DATA_DIR with `chmod 700 guinevere:guinevere`
- Set `REQUIRE_API_KEY=false` (default — no additional auth burden for initial setup)
- Run T7-05 journal grep to confirm no key leakage
- Document this risk in P1-007 evidence

---

## 18. Corrected Systemd Unit Specification

```ini
# /etc/systemd/system/guinevere-9router.service
[Unit]
Description=Guinevere 9Router LLM Proxy
Documentation=https://github.com/decolua/9router
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere

# 9Router uses CLI flags for port/host/no-browser; env vars for DATA_DIR/JWT/etc
ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update

# Environment variables for 9Router runtime
EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.9router
Environment=NODE_ENV=production
Environment=DATA_DIR=/home/guinevere/.9router
Environment=PORT=20128
Environment=HOSTNAME=0.0.0.0

# Restart policy
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-9router

# Cgroup slice
Slice=guinevere.slice

[Install]
WantedBy=multi-user.target
```

### Key Differences from StepPrompts Original

| Property | StepPrompts (Bug) | Corrected |
|---|---|---|
| `After=` | `network.target redis-guinevere.service` | `network-online.target` |
| `Requires=` | `redis-guinevere.service` | **(removed)** |
| `ExecStart=` | `/usr/local/bin/9router` | `/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update` |
| `HOST` env | `Environment=HOST=0.0.0.0` | `Environment=HOSTNAME=0.0.0.0` (plus CLI `--host`) |
| Redis dep | Present (non-existent service) | **None** — 9Router has no Redis dependency |
| `Restart=` | `always` | `on-failure` (clean exit shouldn't restart) |
| `Group=` | Missing | `guinevere` |
| `StartLimitIntervalSec` | Missing | `60` |
| `StartLimitBurst` | Missing | `3` |
| `Documentation=` | Missing | Added |

---

## 19. Provider Configuration — Two Approaches (T7-07)

### Recommended: REST API (Headless)

```bash
# Configure OpenAI provider (GPT-5.5)
curl -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "authType": "apiKey",
    "name": "GPT-5.5 Primary",
    "apiKey": "sk-...",
    "priority": 1,
    "isActive": true
  }'

# Configure DeepSeek provider (deepseek-v4-flash)
curl -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "deepseek",
    "authType": "apiKey",
    "name": "DeepSeek V4 Flash Sub-Agent",
    "apiKey": "sk-...",
    "priority": 2,
    "isActive": true
  }'

# Verify providers configured
curl -s http://localhost:20128/api/providers | python3 -m json.tool

# Verify models available
curl -s http://localhost:20128/v1/models | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['id'] for m in data.get('data', [])]
print('Models:', models[:10])
"
```

### Fallback: Dashboard via Tailscale Browser

1. Connect to Tailscale: ensure local machine on same Tailscale network
2. Open `http://100.94.104.22:20128/dashboard` in browser
3. Login with INITIAL_PASSWORD from `.env.9router.sops`
4. Navigate to **Providers** → **Add API Key**
5. Add OpenAI key → Save
6. Add DeepSeek key → Save
7. Verify on **Models** page

---

## 20. Auditor Specialist Matrix

| Audit Scope | Auditor Type | Focus Areas | Report Path |
|---|---|---|---|
| P1-006 install + systemd | Implementation auditor | Node.js version (24.x), 9router binary at correct path, systemd unit corrected (no redis, HOSTNAME, --no-browser, --skip-update), unit enabled but not started, Slice=guinevere.slice, LSP/syntax | `audit-reports/P1/STEP-P1-006/step-p1-006-auditor-report.md` |
| P1-007 config + start | Implementation auditor | SOPS env decrypts, service starts clean, port 20128 listening, health endpoint returns 200, models endpoint returns list, GPT-5.5 + DeepSeek V4 Flash appear in models, no error entries in journal | `audit-reports/P1/STEP-P1-007/step-p1-007-auditor-report.md` |
| P1-007 provider config | Config auditor | Both providers configured and tested (testStatus = valid), model IDs correct per ADR-004/ADR-006 | Same as above (included) |
| P1-007 security | Security auditor | No API keys in evidence, no secrets in journal, `.env.9router` is chmod 600, SOPS encryption verified, plaintext SQLite risk documented | Same as above (included) |
| Evidence completeness | Evidence auditor | All evidence files exist per schema, 12-section template, cross-references valid, redaction verified | `docs/setup-evidence/P1/STEP-P1-006/evidence.md` + `docs/setup-evidence/P1/STEP-P1-007/evidence.md` |
| StepPrompts fix audit | Compliance auditor | All 10 corrections (C-01 through C-10) applied and verified | `audit-reports/P1/stepprompts-corrections-audit.md` (separate report) |
| Aizanta impact | Ops auditor | Docker ps unchanged, Aizanta services healthy, no port conflicts | Same as evidence files |

### Auditor Sequence

```
FIX PHASE: Apply StepPrompts/CHECKLIST corrections (C-01 through C-10)
  → Auditor 0: Verify all 10 corrections applied correctly
  → Fix failures
  → Re-audit until PASS

P1-006 Install Complete
  → Auditor 1: Implementation audit (T6-10)
  → Fix findings if any
  → Re-audit until PASS
  → Mark P1-006 complete

P1-007 Service + Config Complete
  → Auditor 2: Config + start audit
  → Auditor 3: Provider config audit
  → Auditor 4: Security audit
  → Fix findings if any
  → Re-audit until PASS
  → Mark P1-007 complete

POST-BATCH: Aizanta impact audit
  → Verify Docker ps vs baseline
  → Verify port scan vs baseline
```

---

## 21. Execution Sequence (Parent Orchestration)

```
PHASE 0: STEPPROMPTS/CHECKLIST FIXES (parent)
  ├── Read stepprompts/StepPrompts.md lines 3673-3872
  ├── Read CHECKLIST.md lines 179-210
  ├── Apply C-01 through C-08 to StepPrompts.md (edit tool, sequential)
  ├── Apply C-09, C-10 to CHECKLIST.md (edit tool)
  ├── Verify all corrections with grep
  └── Spawn auditor-0 for fix audit

PHASE 1: PRE-FLIGHT (parent)
  ├── Read PROGRESS.md, CHECKLIST.md
  ├── SSH to VPS (ssh guinevere-vps)
  ├── Verify prerequisites PR-01 through PR-12
  └── Run collision scan (§11)

PHASE 2: P1-006 IMPLEMENTATION (sequential — each depends on previous)
  ├── T6-01: Prerequisite check (parent verify)
  ├── T6-02: Install Node.js 24.x via NodeSource (execute sub-agent)
  ├── T6-03: Verify Node.js + npm (parent verify)
  ├── T6-04: Install 9router globally (execute sub-agent)
  ├── T6-05: Verify 9router binary (parent verify)
  ├── T6-06: Generate JWT_SECRET + INITIAL_PASSWORD (parent)
  ├── T6-07: Create systemd unit (implementation sub-agent)
  ├── T6-08: daemon-reload + enable (execute sub-agent)
  └── T6-09: Create env reference doc (execute sub-agent or parent)

PHASE 3: P1-006 EVIDENCE + AUDIT (parent)
  ├── Write evidence.md for P1-006
  ├── T6-10: Spawn auditor-1 for P1-006
  ├── Fix findings → re-audit until PASS
  └── Update PROGRESS.md, CHECKLIST.md

PHASE 4: P1-007 IMPLEMENTATION (sequential)
  ├── T7-01: Prerequisite check (parent verify)
  ├── T7-02: Create SOPS-encrypted .env.9router.sops (implementation sub-agent)
  ├── T7-03: Decrypt to runtime .env.9router + chmod 600 (same sub-agent)
  ├── T7-04: Start 9Router service (execute sub-agent)
  ├── T7-05: Verify status + port + journal (parent verify)
  ├── T7-06: Health check (parent verify)
  └── T7-07: Configure providers via REST API (parent)

PHASE 5: P1-007 EVIDENCE + AUDIT (parent)
  ├── Write evidence.md for P1-007
  ├── T7-08: Spawn auditor-2,3,4 for P1-007
  ├── Fix findings → re-audit until PASS
  └── Update PROGRESS.md, CHECKLIST.md

PHASE 6: POST-BATCH VERIFICATION (parent)
  ├── Aizanta impact check (docker ps + ss comparison)
  ├── Final provider model list verification
  ├── Security: journald secret scan
  └── Write evidence summary

PHASE 7: FINAL REPORT (parent → operator)
  ├── Changed files list
  ├── Verification results matrix
  ├── Evidence paths
  ├── Auditor report paths
  └── Next action: P1-008 (GPT-5.5 setup)
```

---

## 22. Post-Step Checklist (Must-Complete Items)

### After P1-006

- [ ] DoD items D6-01 through D6-14 all PASS
- [ ] StepPrompts.md corrections C-01 through C-08 verified applied
- [ ] `lsp_diagnostics` clean on any changed files
- [ ] Evidence files exist at `docs/setup-evidence/P1/STEP-P1-006/`
- [ ] No `redis-guinevere.service` reference in systemd unit
- [ ] Unit uses `HOSTNAME` not `HOST` env var
- [ ] Unit includes `--no-browser` and `--skip-update` flags
- [ ] `Slice=guinevere.slice` present
- [ ] `which 9router` returns `/usr/bin/9router`
- [ ] PROGRESS.md updated (line 101: `P1-006` → ✅)
- [ ] CHECKLIST.md updated (§3.2 P1-006 row)
- [ ] Auditor gate PASS (verdict + report read)
- [ ] No Aizanta impact
- [ ] No secrets exposed

### After P1-007

- [ ] DoD items D7-01 through D7-12 all PASS
- [ ] CHECKLIST.md port typo fix (C-09, C-10) verified applied
- [ ] `systemctl status guinevere-9router` shows `active (running)`
- [ ] `ss -tlnp | grep 20128` shows listening
- [ ] `curl http://localhost:20128/api/health` returns 200
- [ ] `curl http://localhost:20128/v1/models` lists GPT-5.5 + DeepSeek V4 Flash
- [ ] Evidence files exist at `docs/setup-evidence/P1/STEP-P1-007/`
- [ ] Provider config evidence redacted (no plaintext API keys)
- [ ] Journald has no API key leakage
- [ ] SOPS encryption verified (encrypt → decrypt round-trip)
- [ ] `.env.9router` is `chmod 600`
- [ ] Aizanta Docker containers unchanged
- [ ] PROGRESS.md updated (line 102: `P1-007` → ✅)
- [ ] CHECKLIST.md updated (§3.2 P1-007 row)
- [ ] Auditor gate PASS (verdict + report read)
- [ ] Rollback procedure documented

---

## Footer

| Field | Value |
|---|---|
| **Plan Author** | Guinevere (mama) |
| **Date** | 2026-06-01 |
| **Source Task** | STEP-P1-006 + STEP-P1-007 batch plan |
| **Research Consumed** | 9router-npm-package.md, nodejs-ubuntu-2404-systemd.md, 9router-provider-setup.md, 9router-api-endpoints.md, vps-state-pre-p1-006.md, internal-context-p1-006-007.md, batch-plan-004-005.md (pattern) |
| **Effort Estimate** | Medium (1-2 days total including audits) |
| **Plan Path** | `docs/setup-evidence/P1/batch-plan-006-007.md` |
| **Next Step After Plan** | Apply StepPrompts/CHECKLIST fixes → execute P1-006 → audit → P1-007 → audit |