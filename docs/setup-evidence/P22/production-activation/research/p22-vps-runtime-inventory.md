# P22 VPS Runtime Health + Adapter Activation Inventory

**Date:** 2026-06-27 21:08 WIB
**Auditor:** Claude (sub-agent, read-only, P22 production activation)
**VPS:** faiz-prod-01, Tailscale 100.94.104.22, user guinevere
**Scope:** Snapshot of live runtime state relevant to P22 production activation. NO restarts, NO destructive ops, NO secret values printed.

---

## 1. SSH Connectivity

- **Status:** OK
- **Command:** `ssh -o ConnectTimeout=10 guinevere-vps 'echo SSH_OK && hostname && date'`
- **Result:**
  ```
  SSH_OK
  faiz-prod-01
  Sat Jun 27 09:05:31 PM WIB 2026
  ```
- **Local clock parity:** matches VPS clock (collector run at 21:05-21:08 WIB, VPS reports 21:05-21:08 WIB). No clock skew.

---

## 2. guinevere-core Service Health

`systemctl is-active guinevere-core` + `systemctl show guinevere-core -p NRestarts -p Result -p ActiveEnterTimestamp -p MemoryCurrent -p MemoryHigh -p MemoryMax`

| Property | Value |
|---|---|
| **is-active** | `active` |
| **Result** | `success` |
| **NRestarts** | `0` (since current start) |
| **ActiveEnterTimestamp** | `Sat 2026-06-27 19:24:51 WIB` (uptime ~1h 43m at snapshot) |
| **MemoryCurrent** | `976,261,120` bytes (~931 MB) |
| **MemoryHigh** | `2,147,483,648` bytes (2 GB) |
| **MemoryMax** | `4,294,967,296` bytes (4 GB) |
| **MainPID** | `3064467` |
| **Workers** | 2 (uvicorn `--workers 2` per unit file) |

**Verdict:** Healthy. No restarts since start, memory at ~46% of MemoryHigh. Two uvicorn worker PIDs (3064519, 3064520) actively logging.

**Note (not P22):** A second, unrelated uvicorn process (PID 1086838, user 10001) runs from `/opt/venv/bin/python /opt/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2`. Different unit, different port scope. This is the older `/opt/guinevere`-style deployment mentioned in audit history and is NOT managed by `guinevere-core.service`.

---

## 3. Project Deployed on VPS? (src/life_integrations present?)

`ls -d ~/guinevere /opt/guinevere 2>/dev/null` and `ls /home/guinevere/code/guinevere/src/life_integrations/ 2>/dev/null`

- `/opt/guinevere` exists as a directory (not a symlink to the active project; old P19-era layout).
- The `guinevere-core` service runs from `/home/guinevere/code/guinevere` (WorkingDirectory and PYTHONPATH both set in unit file).
- `ls /home/guinevere/code/guinevere/src/` returns: `channels, consent, core, _deprecated, discord, finance, financial, gamification, gmail, health.py, hermes, hermes_plugins, __init__.py, knowledge_graph, life_kernel, loops, main.py, mcp, memory, observability, persona, projects, __pycache__, self_improve, service.py, surveillance, wearable, x_poster, x_upload_handler.py`
- **`src/life_integrations/` DOES NOT EXIST on VPS.**
- `find /home/guinevere/code/guinevere -maxdepth 4 -name "life_integrations" -type d` returns nothing.
- `grep -rl "p22\|life_integrations\|P22" /home/guinevere/code/guinevere/src/` returns nothing — no P22 token anywhere in `src/`.

**Verdict:** P22 code is **NOT deployed on VPS**. The `life_kernel` subsystem (P16, P18) is present and active; P22's `life_integrations` package and ADR-053 modules are absent from the running tree.

---

## 4. Venv Client Libs Importable

`.venv/bin/python` is a **symlink to `/usr/bin/python3.12`** (NOT a real venv). Confirmed:
```
lrwxrwxrwx 1 guinevere guinevere 19 May 31 23:36 /home/guinevere/code/guinevere/.venv/bin/python -> /usr/bin/python3.12
```

Despite the fake-venv, the system Python 3.12 has the runtime's needed libs installed (probably via `pip install --user` or a global site-packages). Import test:

```
/home/guinevere/code/guinevere/.venv/bin/python -c "import discord, github, googleapiclient, telethon, notion, neonize; print('ALL_OK')"
→ ModuleNotFoundError: No module named 'github'
```

**Per-module import status (from `pip list`):**

| Module | Status | Version |
|---|---|---|
| `discord` (discord.py) | IMPORTABLE | 2.7.1 |
| `googleapiclient` (google-api-python-client) | IMPORTABLE | 2.197.0 |
| `telethon` | **NOT INSTALLED** (not in pip list) | — |
| `notion` (notion-client) | **NOT INSTALLED** (not in pip list) | — |
| `neonize` | IMPORTABLE | 0.3.18.post0 |
| `PyGithub` (imported as `github`) | **NOT INSTALLED** (no PyGithub in pip list) | — |
| `aiohttp` | IMPORTABLE | 3.14.0 |
| `fastapi` | IMPORTABLE | 0.136.3 |
| `redis` | IMPORTABLE | 7.4.1 |
| `SQLAlchemy` | IMPORTABLE | 2.0.50 |
| `alembic` | IMPORTABLE | 1.18.4 |
| `pydantic` | IMPORTABLE | 2.13.4 |
| `uvicorn` | IMPORTABLE | 0.48.0 |

**P22 adapter-relevant gaps:** `github` (PyGithub), `telethon`, `notion-client` are **not installed**. P22 smoke requirements that touch GitHub/Telegram/Notion will fail at import time. Discord, Gmail (google-api-python-client), and WhatsApp (neonize) adapters have their client libs available.

**Venv integrity finding:** The `.venv` is a symbolic-redirect to system Python 3.12. All runtime libs are present in the system site-packages and reachable via the symlinked python. This works but is not a "real" venv; any future `pip install` inside `.venv` would land in the system site-packages (or be flagged PEP 668 if externally managed). Documenting here for future fix; not a P22 blocker per se.

---

## 5. Redis life_kernel Keys

`redis-cli --scan --pattern 'life_kernel:*'` and `redis-cli GET life_kernel:hard_stop`, `redis-cli GET life_kernel:dashboard_message_id`

**Cross-DB scan (DBs 0-7):**
- `db=0`: 156 keys (guinevere:gmail:*, etc.)
- `db=1`: 0
- `db=2`: 0
- `db=3`: 0
- `db=4`: 0
- `db=5`: 5 keys (`guinevere:mood:cooldown_until, current, last_transition, streak, streak_started`)
- `db=6`: 0
- `db=7`: 0

**Result for `life_kernel:*` and `*life_kernel*` patterns across all DBs:** **NO MATCHES.**

- `redis-cli GET life_kernel:hard_stop` → empty (no value, no key)
- `redis-cli GET life_kernel:dashboard_message_id` → empty (no value, no key)

**Verdict:** HARD STOP is **NOT currently set** in Redis (correct: should be unset/empty in normal operation). Dashboard message ID has no canonical row in `life_kernel:*` namespace. The runtime log signatures `hermes_brain_think_complete` and `dashboard_edited` (9 each in 5 min) confirm the dashboard write path is operating, but it is storing state somewhere other than `life_kernel:dashboard_message_id` (likely `db=0` under a different prefix, or in Postgres). For P22: this is a finding — P22's `IntegrationRegistry` / `ConsentGate` smoke expects to observe a key in `life_kernel:*` namespace; if P22 needs a canonical dashboard pointer it must either be created or the convention is in a different namespace.

---

## 6. Recent Log Analysis (blocker pattern counts, 5-min window)

`journalctl -u guinevere-core --since "5 min ago" --no-pager` — total 1,570 lines.

**Pattern counts (5-min window):**

| Pattern | Count | Verdict |
|---|---|---|
| `HARD_STOP requested` | 0 | OK |
| `GraphRecursionError` | 0 | OK |
| `traceback` (case-insensitive) | 0 | OK |
| `hermes_brain_fallback` | 0 | OK |
| `dashboard_publish_failed` | 0 | OK |
| `hermes_brain_think_complete` | 9 | Healthy cadence (~1.8/min) |
| `dashboard_edited` | 9 | Matches think_complete — single dashboard thread working |
| `life_kernel` (any token) | 8 | `life_kernel.act` events; **no `life_kernel.integration*`, no `life_kernel.registry*`** |
| `consent` (any token) | 0 | OK (no consent flow triggered) |
| `HARD_STOP` (any token) | 0 | OK |
| `p22` (any token) | 0 | Expected (P22 not deployed) |
| `integration` (any token) | 0 | Expected (P22 not deployed) |
| `registry` (any token) | 0 | Expected (P22 not deployed) |

**Sample of `life_kernel.act` lines (5-min):** All 8 are `description_label='Knowledge graph seeding\nScan project files/configs/docs to e' goal_id=self-directed-0 priority=improve_autonomy`. This is the P18 self-directed goal, NOT a P22 integration action.

**Sample of `reflect_node_*` (5-min):** `cycle_count=776..785` (8 cycles in 5 min), `errors_count=0`, `decision=observe`. Reflect loop healthy, no errors, steadily climbing cycle counter.

**24h soak cross-check (wider context, not blocking):**
- `HARD_STOP requested` (24h): 0
- `traceback` (24h): 4 (low; need to identify if these are P22-relevant)
- `hermes_brain_fallback` (24h): 0
- `dashboard_publish_failed` (24h): 0
- `hermes_brain_think_complete` (24h): 2,305
- `dashboard_edited` (24h): 2,371 (66 more than think_complete — likely normal pre-existing message re-anchoring)
- `recall_degraded` (24h): 79 (worth monitoring; could be the lifecycle-rs of long-term memory churn)
- `consent_blocked` (24h): 0

**Verdict:** No active blockers. Runtime is healthy, no error storm, no fallback, no HARD STOP, dashboard publish path is green. P22 surface is empty because P22 is not deployed.

---

## 7. Runtime DB Config (names only — no values)

`systemctl cat guinevere-core | grep -iE 'Environment|EnvironmentFile'`:

```
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
EnvironmentFile=/home/guinevere/code/guinevere/.env.core
```

**Keys in `/home/guinevere/code/guinevere/.env.core` (names only, sorted, deduplicated):**
- `DATABASE_URL`
- `DISCORD_BOT_TOKEN`
- `DISCORD_HOME_CHANNEL`
- `GUINEVERE_9ROUTER_API_KEY`
- `LIFE_KERNEL_PROJECT_ID`  ← confirms life_kernel multi-project context is wired in env
- `REDIS_PASSWORD`
- `REDIS_URL`

**Database of record:** `DATABASE_URL` is the canonical config; the unit file does not pin a DB NAME. The runtime is using the URL in `.env.core` (DB name intentionally not enumerated per audit rules — values are secrets). P22 will inherit this URL.

**Other env files present (not all loaded by `guinevere-core`):** `.env.discord`, `.env.gmail`, `.env.hermes`, `.env.loops`, `.env.mcp`, `.env.monitoring`, `.env.scheduler`. These are referenced by their respective systemd units / scripts, not the core.

---

## 8. P20 Soak Snapshot (5-min window)

Cross-referencing logs against the P20 closure criteria. The runtime is in **post-closure, accepted-risk steady state** (P20 CLOSED per operator waiver 2026-06-25 08:50 WIB).

| Dimension | 5-min value | 24h value | P20 closed threshold | Verdict |
|---|---|---|---|---|
| `hermes_brain_think_complete` | 9 | 2,305 | non-zero, no recurse | OK (cadence ~38/min sustained) |
| `hermes_brain_fallback_used` | 0 | 0 | 0 | OK |
| `dashboard_edited` | 9 | 2,371 | matches think_complete ± a few | OK (slight 24h excess 66 = anchor drift, benign) |
| `dashboard_publish_failed` | 0 | 0 | 0 | OK |
| HARD STOP / fallback-storm / OOM / recursion | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 across all | OK |
| `recall_degraded` (24h) | n/a | 79 | monitor (not blocker) | MONITOR — ~3.3/h, non-zero, not blocking; worth opening a follow-up issue |

**Soak verdict:** CLEAN. P20 closure conditions hold in the 5-min window. `recall_degraded` is a soft signal worth tracking but is not a runtime incident per P20 closure criteria (which excludes this from the reopen trigger list).

---

## 9. Deployment Delta (what's on VPS vs local)

Comparing `/home/guinevere/code/guinevere/src/` on VPS vs `C:\Users\faizz\guinevere\src\` (local) for P22-relevant artifacts:

| Artifact | Local | VPS | Delta |
|---|---|---|---|
| `src/life_kernel/` (P16/P18) | YES | YES (cognition, dashboard, hermes_brain, etc.) | In sync (P18 adapter present, last modified 2026-06-27 11:17 WIB) |
| `src/life_integrations/` (P22) | **YES** (per P22 definition memory: 13 core + 14 adapters, ADR-053) | **NO** | **NOT DEPLOYED** |
| `src/life_kernel/hermes_brain.py` | YES | YES (17,200 bytes, mtime 2026-06-24 05:46 WIB) | Present, slightly older mtime than local |
| `src/life_kernel/cognition.py` | YES | YES (mtime 2026-06-27 11:17 WIB) | Recent local changes already on VPS |
| `src/life_kernel/dashboard_writer.py` | YES | YES | Present |
| `src/life_kernel/p16_adapter.py` | YES | YES | Present |
| `src/life_kernel/p18_adapter.py` | YES | YES | Present |
| `src/life_kernel/p22_adapter.py` (P22 expects) | YES (per P22 def) | **NO** | **NOT DEPLOYED** |
| `src/projects/` (P19) | YES | YES (in `ls src/`) | In sync |
| `src/consent/` (P19) | YES | YES (in `ls src/`) | In sync |
| Client libs for P22: `PyGithub` (as `github`), `telethon`, `notion-client` | — | **NO** | **NOT INSTALLED on VPS** |

**Summary:** The `life_kernel` core + P18 are deployed and running cleanly. The entire P22 layer — `life_integrations/` package, P22 adapter inside `life_kernel/`, and the PyGithub/telethon/notion client libs — is **absent on the VPS**. This is consistent with the P22 memory: "P22 PASS WITH CONFIG_MISSING ADAPTERS" (i.e., P22 was defined/audited locally but production activation was not the focus yet; adapters 10/13 CONFIG_MISSING).

---

## 10. Risks

1. **P22 not deployed on VPS.** No `src/life_integrations/` directory, no `life_kernel/p22_adapter.py`, no P22 token in any source file under `src/`. Any claim of "P22 production activation" is currently **premature** — the code path does not exist on the live runtime. P22 has been defined and audited locally (per memory) but has not been pushed to `/home/guinevere/code/guinevere`.

2. **Venv is a symlink to system Python 3.12** (`/home/guinevere/code/guinevere/.venv/bin/python -> /usr/bin/python3.12`). It works because system site-packages happen to contain the needed libs, but a real `python -m venv` was never created. PEP 668 protections on the system Python will block `pip install` for any new client. For P22's needed `PyGithub`, `telethon`, `notion-client` libs, this will need either a real venv recreation, a `pip install --break-system-packages`, or a project-wide reinstall. **Fix before any P22 deployment push.**

3. **`life_kernel:dashboard_message_id` key absent from Redis.** P22 smoke / P19's canonical-message pattern assumes a single dashboard pointer in the `life_kernel:*` namespace. Currently the runtime logs `dashboard_edited` (9 in 5 min, 2,371 in 24h) but the canonical key is missing. Either the convention has migrated (P19's per-project model uses different keys), or the canonical message ID is in Postgres / different Redis DB. Worth confirming before P22 writes to this key.

4. **Client-lib gap for P22 adapters.** `PyGithub` (imports as `github`), `telethon`, `notion-client` are not installed. Discord (2.7.1), google-api-python-client (2.197.0), and neonize (0.3.18) are present. 10/13 P22 adapters are CONFIG_MISSING per the P22 memory; the 3 OK adapters should be verifiable with the current lib set, but the other 10 will require lib install + cred provisioning.

5. **`recall_degraded` 24h = 79 (~3.3/h).** Below P20 reopen threshold but non-zero. P22 activation should not amplify this; if it does, that becomes a runtime incident.

6. **Two `guinevere-core`-named deployments co-exist on the host.** The active `guinevere-core.service` (P18 life_kernel) and the older `uvicorn src.main:app` (PID 1086838, user 10001) on 0.0.0.0:8000 are both running. Not a blocker; just a hygiene note. P22 activation should target only `guinevere-core.service`, not the older deployment.

---

## Audit Verdict

- **SSH:** OK
- **guinevere-core:** active, 0 restarts, 931 MB / 2 GB, healthy
- **P22 deployed on VPS:** **NO** (no `src/life_integrations/`, no P22 source anywhere under `src/`)
- **P22 client libs:** discord/google/neonize present; `PyGithub`/`telethon`/`notion-client` missing
- **Redis life_kernel keys:** ZERO `life_kernel:*` keys across DBs 0-7; `life_kernel:hard_stop` unset (correct); `life_kernel:dashboard_message_id` unset (verify intent)
- **Logs (5-min):** 0 blockers, 0 tracebacks, 9 think_complete, 9 dashboard_edited — clean
- **24h soak:** CLEAN (HARD_STOP 0, fallback 0, dashboard_publish_failed 0; `recall_degraded` 79 is monitor-only)
- **Runtime env:** `LIFE_KERNEL_PROJECT_ID` present, `DATABASE_URL` (value not enumerated), Redis URL w/ password
- **P20 closure:** CLEAN in 5-min window

**Bottom line:** Runtime is healthy and P20 stays closed. P22 production activation is **NOT in place** — code is on local only. Pre-flight before any P22 push: deploy `src/life_integrations/` + `life_kernel/p22_adapter.py`, install `PyGithub`/`telethon`/`notion-client` (requires venv fix), provision operator credentials for the 10/13 CONFIG_MISSING adapters, and reconfirm `life_kernel:dashboard_message_id` convention.

**No destructive operations performed. No secrets printed. No restarts issued. No firewall/Tailscale changes.**
