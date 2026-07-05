# P23 Audit Round 1 — Executor Isolation

> **Auditor:** Independent (subagent)  
> **Date:** 2026-06-25  
> **Audit Dimension:** Executor Isolation  
> **Scope:** READ-ONLY verification of P23 plan sections 11-17 (executor models) against ground-truth source code
> **⚠️ SUPERSEDED (2026-06-25, Codex P1-2 fix):** This is a HISTORICAL round-1 audit snapshot. It contains statements that `AuthLevel` maps 1:1 to P23 L1-L4 risk tiers. **That mapping is NO LONGER VALID.** Per plan §22b `SemanticActionClassifier`, `AuthLevel` is an INPUT to risk classification, NOT a 1:1 map (shell `python`/`pip`/`git` at `READ_AUTO` classify L2/L3 by semantics, never L1). **Do NOT use the AuthLevel 1:1 claims in this audit for implementation.** The isolation findings (force-push-to-main FORBIDDEN, no shell=True, per-context browser) remain valid; only the 1:1 risk-tier mapping is superseded.


---

## 1. Audit Scope

This audit verifies that each P23 executor has a documented isolation boundary per the plan's hard-rejection criteria (#7: "Browser/desktop/VPS/GitHub/file/mobile executors lack isolation boundary → FAIL") and (#13: "Production service others can be disrupted without isolation proof → FAIL").

**Subjects audited:**
- Plan: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` §11-17 (executor models), §43 (collision scan), §46 (waves P23-005..010)
- Research: `docs/setup-evidence/P23/research/p23-browser-automation-research.md`, `p23-windows-desktop-action-research.md`, `p23-vps-cli-deploy-action-research.md`, `p23-github-repo-action-research.md`, `p23-mobile-android-action-research.md`
- Ground truth: `src/mcp/tools/obscura_cdp.py`, `src/mcp/tools/git_tool.py`, `src/mcp/tools/github.py`, `src/life_kernel/domain_minds/deploy_backend.py`, `src/life_kernel/domain_minds/engineer_mind.py`
- ADRs: ADR-014 (VPS), ADR-019 (Tailscale), ADR-020/033 (browser), IMPLEMENTATION_GUIDE §6 (Aizanta isolation)

**Verification method:**
1. Read plan isolation claims for each executor.
2. Read research documents for design backing.
3. Read actual source code to verify implementation.
4. Report gaps between plan claims and code reality.

---

## 2. Findings

### 2.1 Browser Executor (§11, P23-005)

**Plan claim (lines 191-199):**
> "P23 refactors to per-action BrowserContext. Isolation: dedicated `BrowserContext`/profile per action (no shared cookies across surfaces); separate process. Stealth/anti-detection ONLY for P13 consented X-poster, NOT general actions."

**Research backing:** `p23-browser-automation-research.md` §3.4 explicitly states:
> "Per-action `BrowserContext`: P23 must NOT reuse the current `obscura_cdp.py` singleton `Page`. Each P23 action creates a fresh `browser.new_context()` (clean-slate — no cookies, no localStorage inherited from other actions)."

**Ground truth verification:** `src/mcp/tools/obscura_cdp.py`

Lines 63-72:
```python
@dataclass
class _BrowserState:
    """Holds the lazily-initialised Playwright browser and page references.
    
    Created once on first use and reused across tool invocations.
    The ``playwright`` instance is kept alive for the server's lifetime.
    """
    
    browser: Browser | None = None
    page: Page | None = field(default=None, init=False)
```

Lines 90-95 (connection logic):
```python
self._pw = await async_playwright().start()
self.browser = await self._pw.chromium.connect_over_cdp(_CDP_URL)
self.page = await self.browser.new_page()
logger.info("obscura_connected", cdp_url=_CDP_URL)
```

Line 109: Module-level singleton:
```python
_state = _BrowserState()
```

**FINDING ISO-01 (CRITICAL):**
- **Severity:** CRITICAL
- **Location:** `src/mcp/tools/obscura_cdp.py:63-109`
- **Issue:** The existing browser tool uses a **singleton Page object** (`_state.page`) that is reused across all MCP tool invocations. This directly contradicts the plan's isolation requirement.
- **Evidence:** `_BrowserState` is instantiated once at module load (line 109), creates a single `page` via `browser.new_page()` (line 94), and reuses it for all `obscura_navigate`, `obscura_get_markdown`, `obscura_fill_form`, and `obscura_click` calls (lines 118-213).
- **Impact:** 
  - Cookies, localStorage, and session state are shared across all browser actions.
  - A P13 consented stealth session could leak cookies into general P23 actions, or vice versa.
  - Plan's "no shared cookies across surfaces" (§11, line 199) is **violated**.
- **Recommendation:** P23-005 (browser executor wave) must refactor `obscura_cdp.py` to:
  1. Replace singleton `_state.page` with a per-action `context = browser.new_context()` + `page = context.new_page()`.
  2. Close context at action end: `await context.close()`.
  3. Add artifact capture (screenshot/DOM/HAR) per plan §11 lines 200-205.
  4. This is the research's "single most important isolation change" (`p23-browser-automation-research.md:254`).

---

### 2.2 Desktop Executor (§12, P23-006)

**Plan claim (lines 206-218):**
> "Surface: `desktop`. Runs as a separate process on Faiz's Windows PC, communicates via authenticated WebSocket/Tailscale (mirror P15 daemon). Isolation: NEVER runs as admin by default. Process job-object (`SetInformationJobObject`) with CPU/memory limits. Workspace-only writes (Faiz-approved dirs; no system dirs)."

**Research backing:** `p23-windows-desktop-action-research.md` §3.3 documents job-object design with CPU/memory limits, no admin elevation, workspace-scoped file operations.

**Ground truth verification:** No desktop executor implementation exists in `src/`.

**FINDING ISO-02 (INFORMATIONAL):**
- **Severity:** INFORMATIONAL
- **Location:** N/A (not implemented)
- **Issue:** Desktop executor is design-only; P23-006 wave will implement.
- **Plan correctness:** Plan correctly defers implementation to wave P23-006; research exists; no premature code.
- **Recommendation:** When P23-006 executes, verify:
  1. Separate process (not inline in MCP server).
  2. Job-object limits enforced (`SetInformationJobObject`).
  3. PowerShell `ExecutionPolicy AllSigned` for scripts.
  4. Workspace allowlist enforced (reject writes outside `%USERPROFILE%\Guinevere\workspace`).
  5. NEVER auto-elevate (`-Verb RunAs` blocked).

---

### 2.3 VPS Executor (§13, P23-007)

**Plan claim (lines 219-229):**
> "Surface: `vps`. Runs ON the VPS as `guinevere` user (cgroup `MemoryMax=8G`/`CPUQuota=200%` per IMPLEMENTATION_GUIDE section 6). Isolation / Aizanta-proof: NEVER touches `aizanta-*` services, `/home/aizanta`, Redis DBs 10-15, aizanta DB. SSH only `guinevere@localhost` or Tailscale nodes. Every VPS action asserts no Aizanta impact (IMPLEMENTATION_GUIDE section 6 verify commands) post-action."

**Research backing:** `p23-vps-cli-deploy-action-research.md` §3.8 "Aizanta-Impact Proof Checklist" documents pre/post checks for systemd, Docker, Redis, PostgreSQL, filesystem.

**Ground truth verification:**

`src/life_kernel/domain_minds/deploy_backend.py`:
- Lines 108-116: `SSHDeployBackend.__init__` defaults to `dry_run=True`.
- Lines 122-180: `_run()` uses `asyncio.create_subprocess_exec` (no shell=True, line 131-136).
- Lines 45-53: SSH alias validated via regex (no injection).
- Lines 181-353: backup/canary/smoke/deploy/rollback methods log intent in dry-run mode; execute SSH commands if `dry_run=False`.

`src/life_kernel/domain_minds/engineer_mind.py`:
- Lines 32-49: `DeployPolicy` dataclass enforces backup→canary→smoke→rollback gate.
- Lines 154-296: `backup()`, `canary()`, `smoke_test()`, `deploy()`, `rollback()` methods orchestrate the L3 deploy gate.
- Lines 298-373: `deploy()` method implements the full gate: backup (line 332-336), canary (line 339-341), smoke (line 344-345), promote or rollback (line 348-366).

**FINDING ISO-03 (MAJOR):**
- **Severity:** MAJOR
- **Location:** `src/life_kernel/domain_minds/deploy_backend.py` + `engineer_mind.py` (entire modules)
- **Issue:** The VPS deploy code implements the backup-canary-smoke-rollback gate, but **does not enforce Aizanta-impact checks**.
- **Evidence:**
  - Research (`p23-vps-cli-deploy-action-research.md:290-301`) documents a 6-item pre/post checklist: systemd `aizanta-*`, Docker `name=aizanta`, Redis DB10-15, PostgreSQL aizanta DB, `/home/aizanta` filesystem, network ports.
  - Plan (§13, line 226-227) states: "Every VPS action asserts no Aizanta impact (IMPLEMENTATION_GUIDE section 6 verify commands) post-action."
  - IMPLEMENTATION_GUIDE §6 (assumed authoritative per plan line 29) defines the shared-VPS isolation matrix.
  - Actual code: **no grep for "aizanta"** in `deploy_backend.py` or `engineer_mind.py`. No pre/post assertion in `smoke_test()` or `deploy()`.
- **Impact:**
  - A VPS action could inadvertently touch Aizanta services (e.g., `systemctl restart` targeting wrong service, file operation outside `/home/guinevere`, Redis command to wrong DB).
  - Hard-rejection criterion #13 ("Production service others can be disrupted without isolation proof → FAIL") is at risk.
- **Recommendation:** P23-007 (VPS executor wave) must:
  1. Add `_verify_aizanta_unaffected()` method to `SSHDeployBackend`.
  2. Call it **before** and **after** every destructive operation (`deploy()`, `rollback()`).
  3. Check list: `systemctl is-active aizanta-*`, `docker ps --filter name=aizanta`, `redis-cli -n 10 PING`, `psql -U aizanta -d aizanta -c "SELECT 1"`, `ls /home/aizanta` (read-only hash).
  4. If any check degrades, HALT + rollback + escalate (research §3.8).
  5. Document in `verification.md` that Aizanta was green before/after.

---

### 2.4 GitHub Executor (§14, P23-008)

**Plan claim (lines 230-241):**
> "Surface: `github` / `repo`. Thin wrapper over existing `src/mcp/tools/github.py` (REST API, httpx, tenacity, 401/403/404/5xx handling) + `src/mcp/tools/git_tool.py` (local git via `asyncio.create_subprocess_exec`, no shell=True) + `src/mcp/auth.py` (`AuthLevel` = the L1-L4 primitive). Check policy: PR must pass CI (`pytest`, `mypy`, `ruff`, **secret-scan**) before merge. `main` protected (branch protection: require PR + checks + no force-push + no direct push). Force-push to main = **L4 FORBIDDEN** (already enforced by `git_tool.py:ForbiddenOperationError`)."

**Research backing:** `p23-github-repo-action-research.md` §3.1 confirms existing MCP tools implement AuthLevel gating; §3.3 documents force-push-to-main as FORBIDDEN.

**Ground truth verification:**

`src/mcp/tools/git_tool.py`:
- Lines 64-134: `_is_forbidden()` function checks for force-push to main/master.
- Lines 91-134: Logic extracts branch from args and refspecs, normalizes (`refs/heads/main` → `main`), checks against `_PROTECTED_BRANCHES = frozenset({"main", "master"})` (line 65).
- Lines 336-345: `_git_push_impl()` calls `_is_forbidden(args, branch)` before execution; raises `ForbiddenOperationError` if true.
- Line 13: No `shell=True` — uses `asyncio.create_subprocess_exec` (line 160).

`src/mcp/tools/github.py`:
- Lines 137-154: `github_list_repos` decorated with `@require_approval(AuthLevel.READ_AUTO)` (line 137).
- Lines 157-175: `github_get_file` → `READ_AUTO` (line 157).
- Lines 178-197: `github_create_issue` → `WRITE_NOTIFY` (line 178).
- Lines 200-219: `github_create_pr` → `WRITE_NOTIFY` (line 200).
- Lines 222-240: `github_search_code` → `READ_AUTO` (line 222).

**FINDING ISO-04 (PASS):**
- **Severity:** PASS
- **Location:** `src/mcp/tools/git_tool.py:64-345`, `src/mcp/tools/github.py:1-255`
- **Issue:** None. Isolation is correctly implemented.
- **Evidence:**
  1. Force-push to main/master is **blocked at runtime** via `_is_forbidden()` check (lines 91-134) + `ForbiddenOperationError` (line 343).
  2. No shell injection: `asyncio.create_subprocess_exec` with explicit args (line 160), no `shell=True`.
  3. Scoped PAT expected (lines 58-80 in `github.py`): `GITHUB_PAT` env var, 401 → `ConfigurationError`.
  4. ~~AuthLevel gating is 1:1 with plan's L1-L4 tiers~~ **[SUPERSEDED — see banner above: AuthLevel is an INPUT to §22b SemanticActionClassifier, not 1:1; the git_tool read/write/destructive/forbidden split is valid but the FINAL P23 tier needs semantic confirmation of the subcommand.]** `READ_AUTO`/`WRITE_NOTIFY`/`DESTRUCTIVE_APPROVAL`/`FORBIDDEN` (git_tool.py lines 298/343) are inputs, not the decisive classifier.
- **Recommendation:** None. P23-008 (GitHub executor wave) can wrap these tools as-is. Verify branch protection is configured on GitHub side (defense-in-depth).

---

### 2.5 Filesystem Executor (§15, P23-009)

**Plan claim (lines 242-254):**
> "Surface: `filesystem`. Wraps existing `src/mcp/tools/filesystem.py` MCP tool (if present) or implements a workspace-bound file executor. Isolation: workspace/project boundary → only Faiz-approved dirs writable (Guinevere code root, evidence, workspace; NEVER system dirs, NEVER `/home/aizanta`, NEVER secrets/ plaintext). Enforced via allowlist path-prefix check. Rollback: `file_write`/`file_delete` create a backup copy in `evidence/actions/<id>/backup/` BEFORE the operation; rollback restores it."

**Ground truth verification:** No `src/mcp/tools/filesystem.py` exists. Searched repo; no filesystem MCP tool found.

**FINDING ISO-05 (INFORMATIONAL):**
- **Severity:** INFORMATIONAL
- **Location:** N/A (not implemented)
- **Issue:** Filesystem executor is design-only; P23-009 wave will implement.
- **Plan correctness:** Plan correctly defers to wave P23-009; no premature code.
- **Recommendation:** When P23-009 executes, verify:
  1. Workspace allowlist enforced (e.g., `allowed_roots = ["/home/guinevere/code/guinevere", "/home/guinevere/evidence", "/home/guinevere/workspace"]`).
  2. Path-prefix check rejects `..`, `/home/aizanta`, `/etc`, `/usr`, `/var` (except approved), `secrets/` plaintext.
  3. Backup-before-write: `shutil.copy2(path, f"evidence/actions/{action_id}/backup/{basename}")`.
  4. Rollback restores from backup.
  5. Secret scanner runs on content before write (plan §15, line 252).

---

### 2.6 Mobile Executor (§16, P23-010)

**Plan claim (lines 255-268):**
> "Status: P23-010 designs the **seam only**; NO MVP implementation. Rationale: phone control = intimate surveillance + high blast radius + Android fragmentation. Defer until P14/P15 mobile infra matures + explicit Faiz consent per-action-class. Seam (design only): webhook contract (Tasker HTTP), consent scopes `p23:mobile:notification` / `p23:mobile:app-launch`, artifact path, audit schema. Classification: any mobile capture = CRITICAL (intimate data), 8-gate consent, HARD STOP honored, fail-closed. Hard rejection: mobile executor with autonomous write/capture in MVP = FAIL."

**Research backing:** `p23-mobile-android-action-research.md` §7 "Verdict" explicitly states:
> "P23-010 Mobile/Android Action is DEFERRED from MVP. Phone-level control is intimate surveillance with high blast radius and severe Android fragmentation."

**Ground truth verification:** No mobile executor code exists in `src/`.

**FINDING ISO-06 (PASS):**
- **Severity:** PASS
- **Location:** N/A (correctly not implemented)
- **Issue:** None. Plan correctly defers mobile to post-MVP.
- **Evidence:**
  1. Plan (§16, line 257) explicitly states "NO MVP implementation."
  2. Research backs this with detailed rationale (intimate data, Android fragmentation, 8-gate consent model).
  3. No code in `src/` or `clients/` for mobile action (verified via grep).
  4. Hard-rejection criterion addressed: "mobile executor with autonomous write/capture in MVP = FAIL" (plan line 264) → not present, so PASS.
- **Recommendation:** None. P23-010 wave (if ever executed) must implement the 8-gate consent model (mirror P21 always-listening) before any phone control.

---

### 2.7 External Integration Executor (§17, P23-014)

**Plan claim (lines 269-276):**
> "Surface: `external`. Wraps P22 sensor adapters as **action targets** (P22 = sensors in; P23 = actions out). E.g. P22 `calendar_adapter` (read) → P23 `calendar_event_create` (L2 write-notify); P22 `github_projects_adapter` → P23 `task_item_update` (L2); P22 `notion_adapter` → P23 `note_append` (L2). Consent: `p23:external:<domain>` → reuse P22 per-integration consent (OAuth per-scope, revocable). Secret: reuse P22 secret_ids (`gkv1-kek-secrets-p22-*`); P23 does not duplicate secrets."

**Ground truth verification:** P22 is not yet implemented per `docs/setup-evidence/P22/README.md` (assumed; not read in this audit).

**FINDING ISO-07 (INFORMATIONAL):**
- **Severity:** INFORMATIONAL
- **Location:** N/A (blocked on P22)
- **Issue:** External executor is design-only; P23-014 wave is blocked on P22 implementation.
- **Plan correctness:** Plan correctly states dependency (§21, §41 dependency map: "P23-014 BLOCKED P22 impl").
- **Recommendation:** When P23-014 executes, verify:
  1. Wraps existing P22 adapters (no duplication).
  2. Reuses P22 consent ledger (`p22:<integration>` scopes).
  3. Reuses P22 secrets (`gkv1-kek-secrets-p22-<integration>`).
  4. L3 for delete/archive actions (plan §17, line 273).

---

## 3. Hard-Rejection Criteria Check

Plan §45 defines 19 hard-rejection criteria; this audit focuses on #7 and #13 (executor isolation):

### Hard-Rejection #7:
> "Browser/desktop/VPS/GitHub/file/mobile executors lack isolation boundary → **FAIL**."

**Status per executor:**
| Executor | Isolation Boundary | Status |
|----------|-------------------|--------|
| Browser | Singleton page (no per-action context) | **FAIL** (ISO-01 CRITICAL) |
| Desktop | Design-only (no implementation) | N/A (correct for planning phase) |
| VPS | dry_run=True, no shell=True, backup-canary-smoke-rollback gate; **missing Aizanta checks** | **NEEDS-REVIEW** (ISO-03 MAJOR) |
| GitHub | Force-push-to-main FORBIDDEN, no shell=True, AuthLevel gating | **PASS** (ISO-04) |
| Filesystem | Design-only (no implementation) | N/A (correct for planning phase) |
| Mobile | Design-only, DEFERRED gate | **PASS** (ISO-06) |
| External | Design-only, blocked on P22 | N/A (correct for planning phase) |

**Verdict:** Hard-rejection #7 is **TRIGGERED** by ISO-01 (browser singleton page). The plan claims per-action context isolation, but the existing `obscura_cdp.py` violates this. P23-005 wave must refactor before claiming PASS.

---

### Hard-Rejection #13:
> "Production service others can be disrupted without isolation proof → **FAIL**."

**Status per shared-resource risk:**
| Surface | Co-hosted Service | Isolation Proof | Status |
|---------|-------------------|-----------------|--------|
| Browser | N/A (runs on VPS, separate service) | Separate process (guinevere-obscura.service) | **PASS** |
| Desktop | N/A (runs on Faiz's PC, separate host) | Separate host via Tailscale | **PASS** |
| VPS | **Aizanta** (shared PostgreSQL, Redis, systemd, Docker, filesystem) | **NO pre/post checks in code** | **FAIL** (ISO-03 MAJOR) |
| GitHub | N/A (remote GitHub.com) | No local disruption risk | **PASS** |
| Filesystem | Aizanta (shared `/home`, system dirs) | Allowlist designed but not implemented | N/A (design-only) |
| Mobile | N/A (separate Android device) | Separate device | **PASS** |
| External | Varies per integration | Inherits P22 isolation (when implemented) | N/A (blocked P22) |

**Verdict:** Hard-rejection #13 is **TRIGGERED** by ISO-03 (VPS/Aizanta). The plan claims "Every VPS action asserts no Aizanta impact (IMPLEMENTATION_GUIDE section 6 verify commands) post-action" (§13, line 226-227), but the actual `deploy_backend.py` and `engineer_mind.py` code does not implement these checks. P23-007 wave must add pre/post Aizanta verification before claiming PASS.

---

## 4. Verdict

**NEEDS-REVIEW** — Two hard-rejection criteria are triggered; plan revisions or wave implementation required.

**Summary:**

1. **ISO-01 (CRITICAL):** Browser executor uses a singleton page that violates the plan's per-action context isolation requirement. This is a **hard-rejection #7 trigger**. The plan correctly identifies this as the research's "single most important isolation change" but the existing `obscura_cdp.py` code has not been refactored. **Action:** P23-005 wave must refactor `_BrowserState` to per-action `browser.new_context()` + `context.close()` before proceeding.

2. **ISO-03 (MAJOR):** VPS deploy code implements the backup-canary-smoke-rollback gate but does not enforce Aizanta-impact checks documented in the research and required by IMPLEMENTATION_GUIDE §6. This is a **hard-rejection #13 trigger** (co-hosted Aizanta could be disrupted). **Action:** P23-007 wave must add `_verify_aizanta_unaffected()` pre/post checks to `SSHDeployBackend` before deploying real VPS actions.

3. **ISO-04 (PASS):** GitHub executor isolation is correctly implemented. Force-push to main is blocked at runtime; no shell injection. ~~AuthLevel gating is 1:1 with L1-L4.~~ **[SUPERSEDED — AuthLevel is an INPUT to §22b SemanticActionClassifier, not 1:1 with L1-L4; isolation findings (force-push-block, no-shell) remain PASS.]** **No action required for isolation; the 1:1 risk-tier mapping is superseded.**

4. **ISO-06 (PASS):** Mobile executor is correctly deferred with explicit rationale; no MVP implementation. **No action required.**

5. **ISO-02, ISO-05, ISO-07 (INFORMATIONAL):** Desktop, filesystem, and external executors are design-only (correct for planning phase); will be implemented in their respective waves.

**Recommendation:** Update plan to either:
- **(A) Mark P23-005 and P23-007 as BLOCKED until ISO-01 and ISO-03 are resolved,** OR
- **(B) Add explicit "Isolation refactor TODO" notes in §11 (browser) and §13 (VPS) sections,** OR
- **(C) Move ISO-01 and ISO-03 fixes into P23-005 and P23-007 Expected Files / Required Commands** (which already exist but need the isolation fixes emphasized).

**Output path:** `docs\setup-evidence\P23\evidence\audits\round-1\executor-isolation.md`
