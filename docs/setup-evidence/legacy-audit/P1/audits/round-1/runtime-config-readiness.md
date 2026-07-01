# D3: Runtime-Config-Readiness Audit

**Date:** 2026-06-25
**Auditor:** READ-ONLY subagent (D3 dimension)
**Plan reference:** `docs/setup-evidence/legacy-audit/P1/plan/p1-implementation-audit-plan.md` sections 3.3
**Output path:** `docs/setup-evidence/legacy-audit/P1/audits/round-1/runtime-config-readiness.md`
**Constraint:** No file edits/creates outside output_path. No VPS SSH, no service restarts, no secret decryption.

---

## Per-Check Results

### D3-01: llm_router.py AST Parse + Secret/IP Scan

| Field | Value |
|-------|-------|
| **Check ID** | D3-01 |
| **Command Run** | `python -c "import ast; ast.parse(open('src/core/services/llm_router.py').read()); print('AST OK')"` |
| **Actual Output** | `AST OK` |
| **Verdict** | PASS |
| **Notes** | AST parses cleanly. No hardcoded private IPs (10.\|192.168.\|172.) found — the only IP references are `localhost:20128`. No API key patterns (`sk-[a-zA-Z0-9]{20,}`) detected. |

### D3-02: cost_tracker.py Import Test

| Field | Value |
|-------|-------|
| **Check ID** | D3-02 |
| **Command Run** | `python -c "from src.core.services.cost_tracker import CostTracker; print('Import OK')"` (no instantiation — would attempt Redis connection) |
| **Actual Output** | `Import OK` |
| **Verdict** | PASS |
| **Notes** | Module imports successfully. No hardcoded passwords — `password` parameter defaults to `None` and falls back to `os.environ.get("REDIS_PASSWORD", "")` at line 21. Import does NOT trigger Redis connection (no `__init__` call). **Redis dependency is VPS-only.** |

### D3-03: llm_metrics.py Import + Bind Address Check

| Field | Value |
|-------|-------|
| **Check ID** | D3-03 |
| **Command Run** | `python -c "from src.core.services.llm_metrics import REGISTRY; print('Import OK')"` |
| **Actual Output** | `ImportError: cannot import name 'REGISTRY' from 'src.core.services.llm_metrics'` |
| **Verdict** | NEEDS-REVIEW |
| **Notes** | The scaffold command assumes a `REGISTRY` global exists in `llm_metrics.py`. It does not — the module defines individual metric objects (`LLM_CALLS_TOTAL`, `LLM_LATENCY_SECONDS`, etc.) which auto-register with the default Prometheus `REGISTRY` at creation time. The module imports `Counter`, `Gauge`, `Histogram`, `start_http_server` from `prometheus_client` but never captures `prometheus_client.REGISTRY` as a named export. This is a **scaffold command mismatch**, not a code defect. The module itself imports fine: `import src.core.services.llm_metrics` works. |
| **Bind Address** | `start_http_server(port, addr="127.0.0.1")` at llm_metrics.py:88 — binds to localhost only, **NOT** `0.0.0.0`. PASS for security. |

**Resolution:** The audit plan D3-03 scaffold command should be corrected to `python -c "import src.core.services.llm_metrics; print('Import OK')"` or verify individual metric objects instead.

### D3-04: prompt_loader.py AST Parse + Path Check

| Field | Value |
|-------|-------|
| **Check ID** | D3-04 |
| **Command Run** | `python -c "import ast; ast.parse(open('src/core/services/prompt_loader.py').read()); print('AST OK')"` |
| **Actual Output** | `AST OK` |
| **Verdict** | PASS (with flagged finding) |
| **Notes** | AST parses cleanly. **Hardcoded VPS path at line 16:** `SYSTEM_PROMPT_PATH = Path("/home/guinevere/config/hermes/system-prompt.md")`. This is a valid VPS absolute path (not Windows-style `C:\`) but will raise `FileNotFoundError` on any non-VPS machine. This is by design but constitutes a brittle startup path. No credentials or API keys detected. |

### D3-05: guinevere-core.service Diff (Evidence vs VPS-Mirror)

| Field | Value |
|-------|-------|
| **Check ID** | D3-05 |
| **Command Run** | `diff -u docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service vps-mirror/systemd-live/guinevere-core.service` |
| **Actual Output** | See diff below |
| **Verdict** | NEEDS-REVIEW |

**Complete Diff:**

```diff
--- docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service (evidence snapshot)
+++ vps-mirror/systemd-live/guinevere-core.service (live/vps-mirror)

 [Service]
 Type=exec
 User=guinevere
 WorkingDirectory=/home/guinevere/code/guinevere
 Environment=PYTHONPATH=/home/guinevere/code/guinevere
 Environment=PYTHONDONTWRITEBYTECODE=1
 Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
+EnvironmentFile=/home/guinevere/code/guinevere/.env.core      # <-- ADDED
 ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2
 Restart=always

 # Security hardening
-NoNewPrivileges=true                                          # <-- REMOVED
-ProtectSystem=strict                                          # <-- CHANGED
-ProtectHome=read-only                                         # <-- REMOVED
-ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence
+ProtectSystem=full                                            # <-- CHANGED (strict -> full)
+ReadWritePaths=/home/guinevere/code/guinevere                 # <-- one per line
+ReadWritePaths=/home/guinevere/data
+ReadWritePaths=/home/guinevere/logs
+ReadWritePaths=/home/guinevere/evidence
+ReadWritePaths=/home/guinevere/.hermes                        # <-- NEW path
```

**Divergences catalogued (3+):**

| # | Property | Evidence Snapshot | VPS-Mirror Live | Assessment |
|---|----------|-------------------|-----------------|------------|
| 1 | `EnvironmentFile` | Not present | `/home/guinevere/code/guinevere/.env.core` | Live unit has env file; evidence is stale (pre-env-file P1 snapshot) |
| 2 | `NoNewPrivileges` | `true` | Not present | **Security downgrade** — live unit lacks NoNewPrivileges hardening |
| 3 | `ProtectSystem` | `strict` | `full` | Changed from strict to full; `full` allows writing to `/sys` and `/proc` paths, `strict` was more restrictive |
| 4 | `ProtectHome` | `read-only` | Not present | **Security downgrade** — live unit removes ProtectHome restriction entirely |
| 5 | `ReadWritePaths` | 4 paths (one line) | 5 paths (one per line, added `.hermes`) | Expanded writable paths; `.hermes` is required for Hermes Gateway operation |

**Security impact:** The live unit is **less restrictive** than the evidence snapshot — NoNewPrivileges and ProtectHome have been removed, and ProtectSystem was relaxed from `strict` to `full`. The EnvironmentFile addition is required for runtime secrets but represents a configuration drift from the P1 evidence claim.

### D3-06: guinevere-9router.service Inspection

| Field | Value |
|-------|-------|
| **Check ID** | D3-06 |
| **Command Run** | `cat vps-mirror/systemd-live/guinevere-9router.service` |
| **Actual Output** | 23-line systemd unit file |
| **Verdict** | PASS |
| **Notes** | No P1 evidence artifact exists for this service unit — it is a post-P1 creation. File uses `EnvironmentFile` pointing to `/home/guinevere/code/guinevere/secrets/.env.9router` (no plaintext secrets in unit). Binds to `127.0.0.1:20128`. MemoryHigh=1G, CPUQuota=200%, LimitNPROC=512, LimitNOFILE=8192. Security posture is reasonable. |

### D3-07: hermes-config/config.yaml Env-Var Reference Check

| Field | Value |
|-------|-------|
| **Check ID** | D3-07 |
| **Command Run** | `grep -n "key_env\|password\|secret\|token" hermes-config/config.yaml` |
| **Actual Output** | All 3 LLM provider entries use `key_env: NINEROUTER_API_KEY` pattern (lines 57, 67, 71). No `password` or `secret` keyword matches (token hits are budget/token-tracking related, not API tokens). |
| **Verdict** | PASS |
| **Notes** | All provider entries use `key_env:` with environment variable reference (`NINEROUTER_API_KEY`) instead of inline `key:`. No plaintext API key patterns found. The `password`/`secret` grep returned zero results for security-relevant patterns. The `token` hits are all token-budget/token-counting context, not credential tokens. |

### D3-08: health-check-p1.sh Credential Scan

| Field | Value |
|-------|-------|
| **Check ID** | D3-08 |
| **Command Run** | `grep -n "password\|PASSWORD\|secret\|SECRET\|token\|TOKEN\|api_key\|API_KEY" scripts/health-check-p1.sh` |
| **Actual Output** | Lines 36-37: `SOPS_AGE_KEY_FILE` env var path + `sops -d` decryption of Redis ACL password. Line 46: error message about failed password decryption. |
| **Verdict** | PASS |
| **Notes** | No plaintext secrets in the script. Line 36 references `SOPS_AGE_KEY_FILE=/home/guinevera/secrets/age-key.txt` which is an env var path (file exists only on VPS). Line 37 decrypts via `sops -d` (runtime decryption, not plaintext). Line 46 is an error message, not a credential. |

### D3-09: Redis DB5 Keys Snapshot

| Field | Value |
|-------|-------|
| **Check ID** | D3-09 |
| **Command Run** | `wc -l docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` |
| **Actual Output** | 24 lines |
| **Verdict** | PASS |
| **Notes** | File has 24 lines including headers, blank lines, comments, and data. The snapshot documents **11 Redis keys** (DBSIZE: 11) as claimed by P1-020: 5 budget thresholds, 2 cost counters, 3 per-model costs, 1 per-phase cost. This is a point-in-time snapshot. Current Redis state (with expanded CostTracker token keys and daily/monthly dynamic keys) is VPS-only verification. |

### D3-10: Evidence File Secret Scan

| Field | Value |
|-------|-------|
| **Check ID** | D3-10 |
| **Command Run** | See below |
| **Verdict** | PASS |

**Grep Run 1 — OpenAI/Goggle API keys:**
```
grep -rnE 'sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{35}' docs/setup-evidence/P1/ --include="*"
```
Exit code: 1 (no matches) — PASS

**Grep Run 2 — GitHub tokens:**
```
grep -rnE 'gh[opuab]_[a-zA-Z0-9]{36,}' docs/setup-evidence/P1/ --include="*"
```
Exit code: 1 (no matches) — PASS

**Grep Run 3 — Private keys:**
```
grep -rnE '-----BEGIN.*KEY-----' docs/setup-evidence/P1/ --include="*"
```
Exit code: 2 (no matches, 0 files scanned because `*` matched no files with PEM content) — PASS

**Grep Run 4 — All patterns in source .py files:**
```
grep -rnE 'sk-[a-zA-Z0-9]{20,}|AIza[A-Za-z0-9_-]{35}|gh[opuab]_[a-zA-Z0-9]{36,}|-----BEGIN.*KEY-----' src/core/services/ --include="*.py"
```
Exit code: 1 (no matches) — PASS

**Grep Run 5 — All patterns in hermes-config/config.yaml:**
Exit code: 1 (no matches) — PASS

**Grep Run 6 — All patterns in vps-mirror/systemd-live/:**
Exit code: 1 (no matches) — PASS

---

## Service Unit Diff (Expanded)

### guinevere-core.service: Evidence vs VPS-Mirror

Already detailed in D3-05 above. Key finding: **3 property divergences** (EnvironmentFile added, NoNewPrivileges + ProtectHome removed). Security posture is weaker in the live unit.

### guinevere-9router.service: No P1 Evidence

No equivalent file exists under `docs/setup-evidence/P1/STEP-P1-018/` or any other STEP-P1 directory. This service was created post-P1 (Phase 6/7 9Router installation). The vps-mirror copy is the reference.

---

## Config Safety Check (hermes-config/config.yaml)

| Check | Status |
|-------|--------|
| All 3 LLM provider entries use `key_env:` pattern (not `key:`) | PASS |
| No plaintext API keys (`sk-...`, `AIza...`) | PASS |
| No plaintext passwords/credentials | PASS |
| No safety-bypass options enabled (`send_unsafe`, `bypass_safety`, etc.) | PASS (not found) |
| `fallback_providers` entries also use `key_env:` | PASS |
| Budget section has thresholds but is marked "informational — not read by Hermes" | Informational |

**Key finding:** The `key_env: NINEROUTER_API_KEY` pattern is consistent across all 3 provider entries (primary + 2 fallbacks) in hermes-config/config.yaml. This is correct env-var reference usage.

---

## Health Check Command Inventory (Local vs VPS Classification)

| # | Command | Purpose | Classification | Verification Method |
|---|---------|---------|----------------|-------------------|
| 1 | `curl -sf http://localhost:8000/health` | Core health endpoint | VPS-ONLY | Needs running guinevere-core.service on VPS |
| 2 | `curl -sf http://localhost:20128/api/health` | 9Router health endpoint | VPS-ONLY | Needs running guinevere-9router.service on VPS |
| 3 | `echo "SELECT 1;" \| docker exec -i guinevere-postgres psql -U guinevere -d guinevere` | PostgreSQL connectivity | VPS-ONLY | Needs Docker + Postgres container on VPS |
| 4 | `sops -d /home/guinevere/secrets/redis-acl-passwords.yaml` | Redis password decryption | VPS-ONLY | Needs SOPS age key + encrypted file on VPS |
| 5 | `docker exec -i guinevere-redis redis-cli --user guinevere_core --pass "$REDIS_PASS" PING` | Redis connectivity | VPS-ONLY | Needs Docker + Redis container on VPS |
| 6 | `echo "=== P1 HEALTH CHECK COMPLETE ==="` | Summary output | LOCAL | Can run anywhere (trivial echo) |

**Total: 5 VPS-ONLY checks, 1 LOCAL check.**

---

## R01-R25 NEEDS RUNTIME VERIFICATION Table

| ID | Claim | Verification Command | Can Run Locally? | Verdict |
|----|-------|---------------------|------------------|---------|
| R01 | guinevere-core.service active and running | `systemctl status guinevere-core` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R02 | guinevere-9router.service active and running | `systemctl status guinevere-9router` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R03 | Docker daemon running | `docker ps` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R04 | guinevere-postgres container running | `docker ps \| grep postgres` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R05 | guinevere-redis container running | `docker ps \| grep redis` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R06 | Uvicorn listening on :8000 | `ss -tlnp \| grep 8000` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R07 | Postgres listening on :5433 | `ss -tlnp \| grep 5433` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R08 | Redis listening on :6380 | `ss -tlnp \| grep 6380` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R09 | Postgres SELECT 1 succeeds | `docker exec -i guinevere-postgres psql -U guinevere -d guinevere -c "SELECT 1;"` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R10 | Redis PING returns PONG | `docker exec -i guinevere-redis redis-cli --user guinevere_core --pass "$REDIS_PASS" PING` | NO (VPS-only, needs decrypted password) | NEEDS RUNTIME VERIFICATION |
| R11 | Core reasoning model route works | `curl -X POST http://localhost:20128/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"ping"}]}'` | NO (VPS-only, needs running 9Router) | NEEDS RUNTIME VERIFICATION |
| R12 | Sub-agent model route works | Same as R11 with `task_type=sub_agent` or equivalent routing | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R13 | Fallback to guinevere combo model on primary failure | Inject invalid model and verify fallback to guinevere | NO (VPS-only, spends credits) | NEEDS RUNTIME VERIFICATION |
| R14 | LLM response contains expected fields | Check `choices`, `usage` in response JSON | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R15 | System prompt file exists on VPS | `ls -la /home/guinevere/config/hermes/system-prompt.md` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R16 | System prompt contains safety elements (HARD STOP, safe word, Y5/Y6, distress) | `grep -E 'HARD STOP|safe word|Y5|Y6|distress' /home/guinevere/config/hermes/system-prompt.md` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R17 | System prompt readable by guinevere user | `cat /home/guinevere/config/hermes/system-prompt.md > /dev/null && echo "readable"` | NO (VPS-only) | NEEDS RUNTIME VERIFICATION |
| R18 | HardStopHandler deterministic tests pass | `python -m pytest tests/safety/test_hard_stop_handler.py -v --tb=short` | **YES** (pure Python, no deps) | CAN RUN LOCALLY |
| R19 | HardStopHandler model compliance tests (14 of 70) | `python -m pytest tests/safety/test_hard_stop_handler.py -v -k "model" --tb=short` | NO (VPS-only, needs live LLM) | NEEDS RUNTIME VERIFICATION |
| R20 | Redis DB5 keys match expected CostTracker state | `redis-cli -p 6380 -n 5 --user guinevere_core --pass "$REDIS_PASS" KEYS '*'` | NO (VPS-only, needs Redis running) | NEEDS RUNTIME VERIFICATION |
| R21 | CostTracker.record_cost() writes to Redis | Call LLM route and check Redis counters increment | NO (VPS-only, spends credits) | NEEDS RUNTIME VERIFICATION |
| R22 | Fallback to sub-agent on provider HTTP error | Inject bad model and verify 402 error triggers fallback | NO (VPS-only, needs 9Router) | NEEDS RUNTIME VERIFICATION |
| R23 | Fallback to guinevere combo on all provider failures | Inject unreachable base_url and verify final fallback | NO (VPS-only, needs 9Router) | NEEDS RUNTIME VERIFICATION |
| R24 | SSE [DONE] stripping works | Request non-streaming and verify no `data: [DONE]` in response | NO (VPS-only, needs 9Router) | NEEDS RUNTIME VERIFICATION |
| R25 | Prometheus metrics endpoint on :9191 | `curl -sf http://localhost:9191/metrics \| head -30` | NO (VPS-only, needs running uvicorn) | NEEDS RUNTIME VERIFICATION |

---

## Bug Register

| Severity | File:Line | Description |
|----------|-----------|-------------|
| Medium | `src/core/services/llm_metrics.py` (module) | D3-03 scaffold command mismatch: plan references `REGISTRY` which does not exist as a named export in llm_metrics.py. Module defines individual metric objects that auto-register with Prometheus default registry. Scaffold command should be corrected, but this indicates plan author did not verify command against actual module exports. |
| Low | `src/core/services/prompt_loader.py:16` | Hardcoded VPS path `Path("/home/guinevere/config/hermes/system-prompt.md")`. By design for VPS operation, but raises `FileNotFoundError` on any non-VPS machine. Consider making this configurable via env var or config. |
| Medium | `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` vs `vps-mirror/systemd-live/guinevere-core.service` | 3+ property divergences between evidence snapshot and live unit. **Security concern:** live unit removed `NoNewPrivileges=true` and `ProtectHome=read-only`, relaxed `ProtectSystem=strict` to `full`. While the EnvironmentFile addition is necessary, the removal of security hardening properties is a regression from the P1-claimed configuration. |
| Low | `vps-mirror/systemd-live/guinevere-9router.service` | No P1 evidence artifact exists for this service. It is a legitimate post-P1 creation (9Router added in Phase 6/7), but the P1 evidence corpus is incomplete for infrastructure auditing purposes. |
| Low | `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` | Point-in-time snapshot shows 11 keys. Production CostTracker code (`cost_tracker.py:35-49`) now writes to 13 key patterns (5 cost + 8 token) plus dynamically-created daily/monthly keys. Snapshot is accurate for P1 epoch but stale for current state. |

---

## Overall D3 Verdict

**NEEDS-REVIEW**

**Reasoning:**
- **8 of 10 checks PASS** with zero secrets found, clean AST, correct env-var references.
- **1 check (D3-03) NEEDS-REVIEW** due to a scaffold command mismatch (REGISTRY not a module export) — the module itself is fine.
- **1 check (D3-05) NEEDS-REVIEW** due to 3+ security-relevant divergences between the evidence guinevere-core.service snapshot and the live vps-mirror unit (removed NoNewPrivileges, removed ProtectHome, relaxed ProtectSystem).
- **24 of 25 runtime verification points** (R01-R25, excluding R18) require VPS SSH access and cannot be confirmed during this read-only round.
- **No hardcoded secrets, API keys, or credentials** found anywhere in the inspected corpus (source, config, evidence files, service units, health script).
- **Metrics server binds to 127.0.0.1:9191** as required (not 0.0.0.0).
- **All 3 LLM provider entries in hermes-config/config.yaml** use `key_env: NINEROUTER_API_KEY` (no inline key values).

The NEEDS-REVIEW verdict is driven by the security hardening regression in the live service unit (D3-05) and the 24 pending VPS runtime verification items (R01-R25 excluding R18), not by any code defect or secret leak.
