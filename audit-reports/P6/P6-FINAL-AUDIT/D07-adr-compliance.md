# D07 — ADR Compliance Audit: P6 MCP Tools

> **Audit ID:** D07-ADR-COMPLIANCE-P6  
> **Date:** 2026-06-03  
> **Scope:** Architecture Decision Records compliance verification for P6 MCP Tools implementation  
> **Overall Verdict:** 6 PASS / 0 FAIL / **1 VIOLATION** (ADR-030: Redis DB5 collision)  

---

## Audit Summary

| # | ADR | Decision | Implementation | Verdict |
|---|-----|----------|---------------|---------|
| 1 | ADR-033 | Obscura CDP via `connect_over_cdp` on port 9222 | `obscura_cdp.py` → `src/mcp/tools/obscura_cdp.py` | ✅ COMPLIANT |
| 2 | ADR-020 | obscura primary + Playwright fallback (strategic) | Strategic decision intact; ADR-033 refines implementation only | ✅ COMPLIANT |
| 3 | ADR-005 | 9Router only, no OpenRouter fallback | No OpenRouter refs in MCP tools; LLM routing is Hermes Agent responsibility | ✅ COMPLIANT |
| 4 | ADR-030 | Redis DB0–DB5 assignments | Cost trackers use DB5, but ADR-030 assigns DB5 to **rate limiting** | ❌ VIOLATION |
| 5 | ADR-031 | DB name `guinevere` | `postgres_tool.py` defaults to `"guinevere"` | ✅ COMPLIANT |
| 6 | ADR-015 | SOPS + age, no hardcoded secrets | All secrets from `os.environ.get()`; zero hardcoded secrets found | ✅ COMPLIANT |
| 7 | — | Stale ADR references | Only ADR-033 referenced; all 33 ADRs exist | ✅ COMPLIANT |
| 8 | — | Decisions log: Obscura entry | Entry 001 exists, dated 2026-06-02, references ADR-033 | ✅ COMPLIANT |

---

## Detailed Findings

---

### 1. ADR-033 — Browser Automation (Obscura CDP)

**ADR Decision:** Replace headless Chrome + full Playwright with Obscura CDP server + playwright-core client. Client connects via `connect_over_cdp("ws://127.0.0.1:9222")`.

**Implementation:** `src/mcp/tools/obscura_cdp.py` (247 lines)

| Checkpoint | Expected | Actual | Status |
|---|---|---|---|
| Uses `connect_over_cdp` | Yes | Line 93: `self.browser = await self._pw.chromium.connect_over_cdp(_CDP_URL)` | ✅ |
| CDP URL is port 9222 | `ws://127.0.0.1:9222` | Line 40: `_CDP_URL: str = "ws://127.0.0.1:9222"` | ✅ |
| No Chromium/headless Chrome direct install | Must not exist | zero matches for `headless.?chrome` or `chromium.*install` in file | ✅ |
| Port 9222 documented | Documented in ADR and code | ADR-033 §Implementation Notes; code docstring line 8; constants line 40 | ✅ |
| Rollback plan documented | Must exist in ADR-033 | ADR-033 lines 177-196: full rollback script + <5min estimate | ✅ |
| No `page.screenshot()` (Obscura limitation) | Avoided | Docstring line 11: "No `page.screenshot()` — Obscura has no pixel rendering." | ✅ |
| Content extraction via `markdownify` | Yes | Line 155: `md_text = md_convert(raw_html, heading_style="ATX")` | ✅ |
| Playwright fallback per ADR-020 | Referenced | ADR-033 lines 143-145, 172 | ✅ |
| ADR-033 referenced in source | Documented | Line 7: `Architecture per ADR-033:` | ✅ |
| Stealth mode enabled | `--stealth` flag | Line 104 (error message): `obscura serve --port 9222 --stealth --workers 2` | ✅ |
| Use of `async_playwright` (playwright-core) | Yes | Line 21: `from playwright.async_api import async_playwright` | ✅ |

**Verdict: COMPLIANT** — All 11 checkpoints pass. Implementation faithfully reflects ADR-033 decisions. The connection manager, error handling, and tool registration all align with the ADR's runtime architecture specification.

---

### 2. ADR-020 — Browser Automation Strategy (Strategic)

**ADR Decision:** obscura primary + Playwright fallback.

**Status:** ADR-020 (2026-05-30) remains **Accepted** and unmodified. ADR-033 (2026-06-02) explicitly states it "Refines ADR-020 (implementation-level)" — the strategic decision is unchanged.

**Verification:**
- ADR-020 frontmatter: `status: "Accepted"`, `supersedes: "N/A"` — not deprecated
- ADR-033 frontmatter: `supersedes: "Refines ADR-020 (implementation-level)"` — scoped to implementation detail
- ADR-033 §Supersedes: "ADR-020 remains the strategic decision (obscura primary + Playwright fallback). ADR-033 specifies the concrete implementation."
- Fallback path preserved in ADR-033 §Playwright Fallback (lines 143-145)
- Implementation preserves both paths: Obscura CDP primary, Playwright+Chromium available as system-level fallback

**Verdict: COMPLIANT** — Strategic decision intact. ADR-033 correctly refines without superseding.

---

### 3. ADR-005 — LLM Router & Failover Strategy

**ADR Decision:** 9Router only with queue/retry/degrade behavior. No OpenRouter fallback.

**Verification of P6 MCP Tools:**
- Searched `src/mcp/` for `9router`, `9_router`, `nine_router`, `openrouter` → **zero matches**
- The `sequential_thinking` tool (`src/mcp/tools/sequential_thinking.py`, 420 lines) is a pure in-memory data structure manager — it manages thought chains with dataclass-based session state. It does **not** invoke any LLM.
- No other P6 MCP tool invokes LLM calls directly.
- LLM routing is the responsibility of the **Hermes Agent framework**, not individual MCP tools.

**Analysis:** The ADR governs the routing layer (Hermes Agent → 9Router → model providers). P6 MCP tools are downstream consumers of agent decisions, not routing participants. The absence of any OpenRouter references in the MCP tool layer is correct behavior. The `sequential_thinking` tool is listed with cost `0.0` in `cost.py` with the note "LLM tokens only (tracked by caller, not this tool)" — confirming the architectural separation.

**Verdict: COMPLIANT** — No OpenRouter fallback exists in the MCP tool layer. The `sequential_thinking` tool is a pure computation tool with no LLM dependency. ADR-005's routing rules apply at the Hermes Agent layer, not individual MCP tools.

---

### 4. ADR-030 — Redis DB Assignments (DB0–DB5) ❌ VIOLATION

**ADR Decision (2026-05-31):**

| DB | Purpose |
|----|---------|
| DB0 | Task queue |
| DB1 | LLM cache |
| DB2 | Surveillance buffer |
| DB3 | Sessions / working memory |
| DB4 | Pub/Sub |
| DB5 | **Rate limiting** |

**What the ADR says about extending beyond DB5 (line 121):**
> "If a new Redis purpose is needed beyond DB5, a new ADR must be created to assign DB6+ or refactor."

**What the implementation does:**

| File | Line | Usage |
|------|------|-------|
| `src/mcp/cost.py` | 53 | `db: int = 5` — ToolCostTracker for per-tool MCP cost tracking |
| `src/loops/cost.py` | 32 | `db: int = 5` — LoopCostTracker for per-loop LLM cost tracking |

**Violation Details:**

Cost tracking (both tool-level and loop-level) is using Redis **DB5**, which ADR-030 assigns to **rate limiting**. Cost tracking is NOT listed in ADR-030's DB0–DB5 assignments.

This creates a **silent collision**: two distinct purposes (rate limiting and cost tracking) share the same Redis logical database without the ADR acknowledging or authorizing this co-location.

**Impact:**

| Concern | Severity |
|---------|----------|
| Key namespace collision risk | Medium — different key prefixes (`tool:cost:*`, `loop:cost:*` vs likely `ratelimit:*`) provide some isolation, but logical DB separation is the intended isolation mechanism per ADR |
| Eviction policy mismatch | High — ADR-030 specifies `allkeys-lru` for DB5 (rate limiting). Cost tracking data should use `noeviction` (financial data loss is unacceptable). LRU could silently evict cost records. |
| DR/backup scope ambiguity | Medium — backup scripts keyed to DB assignments would not know to include cost tracking in DB5 restore procedures |
| ADR process bypass | Low — but ADR-030 §Risks explicitly states new purposes beyond DB5 require a new ADR |

**Remediation Options:**

1. **Preferred:** Create a new ADR (e.g., ADR-034) to assign **DB6** for cost tracking with `noeviction` persistence policy and update both `cost.py` files to use `db=6`.
2. **Alternative:** Amend ADR-030 to acknowledge cost tracking co-located on DB5 with rate limiting, explicitly documenting key prefix separation and shared eviction policy rationale.

**Verdict: VIOLATION** — Cost tracking uses DB5 which ADR-030 assigns to rate limiting. Cost tracking is not listed in ADR-030's assignments. This requires either an ADR amendment or a new DB allocation (DB6+).

---

### 5. ADR-031 — Database Naming Convention

**ADR Decision:** Production database name = `guinevere` (no `_db` suffix).

**Implementation:** `src/mcp/tools/postgres_tool.py`

| Checkpoint | Expected | Actual | Status |
|---|---|---|---|
| Default DB name | `"guinevere"` | Line 96: `_DEFAULT_DB: Final[str] = "guinevere"` | ✅ |
| Configurable via env var | `POSTGRES_DB` | Line 117: `db = os.environ.get("POSTGRES_DB", _DEFAULT_DB)` | ✅ |
| Connection string portable | DB sourced from env | All connection params (host, port, user, password, db) from `os.environ.get()` | ✅ |

**Verification:** The default hardcoded name exactly matches ADR-031's production database name. The `POSTGRES_DB` environment variable override allows test/staging variants (`guinevere_test`, `guinevere_staging`) as specified in ADR-031.

**Verdict: COMPLIANT** — Default database name `"guinevere"` matches ADR-031. Environment variable override supports test/staging variants.

---

### 6. ADR-015 — Secrets Management Strategy

**ADR Decision:** SOPS + age with runtime injection. Plaintext secrets forbidden in ADRs, docs, code, evidence, logs, and sub-agent reports.

**Verification — Hardcoded Secret Scan:**

| Pattern Searched | Files Scanned | Matches |
|---|---|---|
| `(api_key\|token\|password\|secret\|credential)\s*=\s*["'][^"']{8,}` | All `src/mcp/` (*.py) | **0** |

**Verification — Environment Variable Usage:**

| File | Secrets via env |
|---|---|
| `src/mcp/cost.py` | `REDIS_PASSWORD` |
| `src/mcp/budget.py` | `REDIS_PASSWORD` |
| `src/mcp/tools/postgres_tool.py` | `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_READONLY_USER` |
| `src/mcp/tools/brave_search.py` | `BRAVE_API_KEY`, `REDIS_PASSWORD` |
| `src/mcp/tools/exa_search.py` | `EXA_API_KEY`, `REDIS_PASSWORD` |
| `src/mcp/tools/github.py` | `GITHUB_PAT` |
| `src/mcp/tools/context7.py` | `REDIS_PASSWORD` |
| `src/mcp/tools/redis_tool.py` | `REDIS_PASSWORD` |
| `src/mcp/tools/git_tool.py` | `GIT_BINARY` (non-secret, but env-configurable) |
| `src/mcp/tools/filesystem.py` | `FILESYSTEM_ALLOWED_PATHS` |
| `src/mcp/auth.py` | `DISCORD_WEBHOOK_URL` |
| `src/loops/cost.py` | `REDIS_PASSWORD` |

**Total: 18 `os.environ.get()` calls across 11 files. Zero hardcoded secrets.**

All credentials are sourced exclusively from environment variables with sensible fallback defaults (empty strings for passwords, well-known ports/hosts for connection params). This aligns with the SOPS + age workflow: secrets are decrypted at deployment time and injected into the runtime environment.

**Verdict: COMPLIANT** — No hardcoded secrets. All credentials via `os.environ.get()`. Pattern consistent with SOPS + age runtime injection strategy.

---

### 7. Stale ADR References

**Source code ADR references found:**

| File | ADR Referenced | ADR Exists? |
|------|---------------|-------------|
| `src/mcp/tools/obscura_cdp.py` line 7 | ADR-033 | ✅ Yes (`adr/ADR-033-browser-automation-obscura.md`) |

**No stale or broken ADR references** were found in `src/mcp/`. The full ADR directory contains 33 files (ADR-001 through ADR-033), all present and accounted for.

**Verdict: COMPLIANT** — Only valid, existing ADR referenced. No broken links. All 33 ADR files exist in `adr/`.

---

### 8. Decisions Log — Obscura Adoption Entry

**Expected:** Entry documenting Obscura CDP adoption decision.

**Found:** `docs/10-governance/decisions-log.md` — Entry 001

| Field | Value |
|-------|-------|
| # | 001 |
| Date | 2026-06-02 |
| Decision | Adopt Obscura CDP as browser automation runtime |
| Category | Tooling |
| ADR | [ADR-033](../../adr/ADR-033-browser-automation-obscura.md) |
| Rationale | Replace Playwright + headless Chromium with Obscura CDP server (Rust, Apache-2.0, 14K stars). Stealth anti-detection built-in, 5x lighter, systemd-managed. Playwright retained as CDP client via `connect_over_cdp`. Supersedes ADR-020 at implementation level; strategic decision unchanged. |
| Approved By | **Faiz** |

**Verdict: COMPLIANT** — Entry exists, correctly linked to ADR-033, approved by Faiz (sole owner).

---

## Overall Assessment

### Compliance Score

| Category | Count |
|----------|-------|
| COMPLIANT | 6 |
| VIOLATION | 1 |
| **Total Checks** | **8** |

### Violation Severity

| ID | ADR | Issue | Severity |
|----|-----|-------|----------|
| D07-V01 | ADR-030 | Cost tracking uses Redis DB5 (assigned to rate limiting); cost tracking not in ADR-030's DB assignments | **MEDIUM** |

### Summary

P6 MCP Tools demonstrate strong ADR compliance overall. Seven of eight audit checks pass cleanly. The single violation (ADR-030 DB5 collision) is a **namespace management issue** rather than a safety or security concern — cost tracking and rate limiting share DB5 with different key prefixes, but this deviates from ADR-030's explicit DB-per-purpose isolation model and risks eviction policy mismatch.

### Recommended Next Steps

1. **Remediate D07-V01:** Create ADR-034 to assign DB6 for cost tracking, or amend ADR-030 to explicitly document the DB5 co-location with rationale for shared `allkeys-lru` eviction policy.
2. **Update cost.py and loops/cost.py:** Change `db=5` to the assigned DB once the ADR is updated.
3. **No other remediation needed** — all other ADRs are fully compliant.

---

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| This report | `audit-reports/P6/P6-FINAL-AUDIT/D07-adr-compliance.md` |
| Source ADR files | `adr/ADR-005.md`, `adr/ADR-015.md`, `adr/ADR-020.md`, `adr/ADR-030.md`, `adr/ADR-031.md`, `adr/ADR-033.md` |
| Verified source | `src/mcp/tools/obscura_cdp.py`, `src/mcp/tools/sequential_thinking.py`, `src/mcp/tools/postgres_tool.py`, `src/mcp/cost.py`, `src/loops/cost.py` |
| Decisions log | `docs/10-governance/decisions-log.md` |

---

*Audit completed by Sisyphus-Junior (Guinevere executor) at 2026-06-03.*