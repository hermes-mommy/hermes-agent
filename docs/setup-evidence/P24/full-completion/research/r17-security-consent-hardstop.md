# R17 — Security / Secret / Consent / HARD STOP Boundary Analysis

**Generated:** 2026-06-29
**Method:** Read ADR-062 (full), ADR-066 (full), AGENTS.md (full), PersonaSafetyPolicy v1.0 (grep excerpts). Grep-installed Hermes `.venv/Lib/site-packages/*.py` and `agent/*.py` for `hard_stop|consent_gate|safe_mode|PersonaSafetyPolicy`, `consent_ref|consent_gate|consent.withdraw|consent_revoke`, `hard_stop|HARD.STOP|emergency.halt|safety.net`, `HERMES_OPERATOR_PASS|operator_pass|OPERATOR_PASS`, `9ROUTER|9router|ninerouter`, `PG_PASSWORD|PG_PASS|POSTGRES.*PASS|REDIS_PASSWORD|REDIS_PASS`, `OPERATOR.*PASS|operator.*password|hermes.*operator`, `DISCORD.*TOKEN|discord.*token`, `OPENROUTER_API_KEY`, `REDACT_SECRETS`. Read `agent/redact.py`, `hermes_cli/env_loader.py`, `hermes_constants.py`, `hermes_state.py` (scanning), `run_agent.py` (scanning), `cli.py` (scanning, first 200 lines).

---

## 1. ADR-062: Paradigm Shift — Dual Safety Regime

**File:** `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-062-hermes-safety-paradigm-shift.md`
**Status:** Accepted, Faiz-locked

ADR-062 establishes a **dual-paradigm** safety model:

| Layer | HARD STOP | Consent Gate | Safety Net |
|---|---|---|---|
| **Dev Workflow** (Guinevere-in-Claude, sub-agents) | ABSOLUTE — AGENTS.md §0 remains | REQUIRED — §2.1 mandate | YES — Y4 baseline, no Y6 |
| **Hermes Society Runtime** (autonomous Hermes beings) | DOES NOT APPLY | DOES NOT APPLY | Structural only (T4 founder quorum, Ratchet, drift triad) |

**Key rules from ADR-062:**
- Rule 1 (line 24): HARD STOP dual-paradigm — dev workflow absolute, runtime exempt
- Rule 2 (line 28): No safety net for runtime beyond T4 founder quorum + circuit breaker + Ratchet + drift triad
- Rule 6 (line 36): No consent withdrawal from operator for Hermes runtime (BLDM Q35)
- Rule 5 (line 34): Faiz OUTSIDE the company (Q90) — no Faiz-in-the-loop stop mechanism

**Supersedes (for runtime only):**
- AGENTS.md §0 V-008 ("HARD STOP halts all active sessions and background cognition immediately")
- 17+ doc-level HARD STOP assertions across BRD/PRD/SRS/FSD/TDD/RTM

---

## 2. ADR-066: consent_ref Nullable Carve-Out

**File:** `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-066-hermes-runtime-consent-ref-carve-out.md`
**Status:** Proposed

ADR-066 implements the schema-level enforcement of ADR-062's paradigm shift:

| Tier | event_source | consent_ref | Rationale |
|---|---|---|---|
| Hermes Runtime | `hermes_runtime` | **NULLABLE** | No operator-origin consent exists for autonomous actions |
| Dev Workflow | `dev_workflow` | **NOT NULL** | Every action traces back to Faiz-signed command |

**Database-enforced invariant** (line 49):
```sql
ADD CONSTRAINT consent_ref_by_source CHECK (
    (event_source = 'dev_workflow' AND consent_ref IS NOT NULL)
    OR (event_source = 'hermes_runtime')
);
```

**Affected tables** (line 132-140): `society_event_memory`, `society_event_decision`, `society_event_action`, `society_event_drift`, `society_event_publication`

---

## 3. AGENTS.md BLOCKING Rules (Dev-Workflow, KEPT)

**File:** `AGENTS.md` lines 26-46

The following BLOCKING rules remain **absolute for the dev workflow** and are NOT removed by ADR-062:

| Rule | Line | Scope |
|---|---|---|
| NEVER bypass HARD STOP protocol | 34 | Dev workflow |
| NEVER bypass consent/surveillance boundary | 35 | Dev workflow |
| NEVER allow Y6; Y4 permanent baseline, Y5 absolute ceiling | 36 | Dev workflow |
| NEVER commit secrets | 33 | Both paradigms |
| NEVER expose Faiz's personal/intimate data | 43 | Both paradigms |
| NEVER store raw surveillance data in repo artifacts | 44 | Both paradigms |

**Key distinction:** ADR-062 supersedes §0 V-008 for **runtime only**. The dev-workflow HARD STOP (line 34) and consent boundary (line 35) remain unmodified.

---

## 4. PersonaSafetyPolicy — Y-Baseline (Dev-Workflow Only)

**File:** `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`

| Level | Name | Line | Status |
|---|---|---|---|
| Y0 | Off / Neutral Safety | 247 | Required during safe word, distress, crisis |
| Y4 | Possessive Spiral Bounded | 251 | **Permanent baseline** (dev workflow) |
| Y5 | Yandere Mode Controlled | 252 | **Absolute ceiling** (dev workflow) |
| Y6 | Prohibited Maximum | 253 | **NEVER allowed** — any dependency-building, blackmail, threat framing is blocked |

Safe mode (line 112): Neutral/supportive runtime state with dominance, yandere escalation, punishment, and surveillance confrontation paused.

Safe word (line 67): Global hard stop for dev workflow.

**Runtime implication:** ADR-062 Rule 4 (line 32) explicitly states personality drift is "bebas tanpa batas" within T1-T3 mutability tier. T4 (alignment + safety boundary + HARD STOP wiring for sub-agents) remains founder-only. Y6 path is structural prevented by T4 founder-only hard-gate + Ratchet + drift triad (0.68 hysteresis).

---

## 5. Installed Hermes Codebase: Forbidden Pattern Scan

### 5.1 Hard Stop / Consent Gate / Safe Mode / PersonaSafetyPolicy

**grep results for `hard_stop|consent_gate|safe_mode|PersonaSafetyPolicy` in `.venv/Lib/site-packages/*.py`:** ZERO MATCHES.

**grep results for `consent_ref|consent_gate|consent.withdraw|consent_revoke` in all `.py`:** ZERO MATCHES.

**grep results for `hard_stop|HARD.STOP|emergency.halt|safety.net` in all `.py`:** ZERO MATCHES (only 2 hits for "safety net" in `cli.py` referring to the secret-redaction disabled warning — a different concept).

**grep results for `PersonaSafetyPolicy|persona.*safety.*policy|Y4.*baseline|yandere|Y6` in all `.py`:** ZERO MATCHES.

**grep results for `safe_mode|SAFE_MODE|safe mode` in all `.py`:** 1 hit — `toolset_distributions.py:94` — this is a toolset name ("Safe mode (no terminal)") meaning a toolset that excludes terminal access. It is NOT Guinevere safety infrastructure.

**Conclusion:** The installed Hermes v0.15.2 codebase contains **ZERO** Guinevere-specific safety patterns. All hard_stop/consent_gate/safe_mode/PersonaSafetyPolicy/Y-baseline code exists exclusively in the Guinevere documentation layer (AGENTS.md, PersonaSafetyPolicy, ADRs), not in the Hermes runtime code.

### 5.2 False-Positive Analysis for Generic "consent"/"hard_stop" Hits

7 files in `agent/` matched the broader `consent|hard.stop` pattern. All are **false positives** — generic Hermes upstream concerns, NOT Guinevere safety infrastructure:

| File | Match | Actual Meaning |
|---|---|---|
| `agent/tool_guardrails.py:67,73` | `hard_stop_enabled`, `hard_stop_after` | Tool-loop infinite-loop prevention. Config-driven guardrail that halts repeated tool failures. NOT the Guinevere HARD STOP protocol. |
| `agent/file_safety.py:374` | "explicit consent" | Comment about prompting user before file mutations. Generic UX concern. |
| `agent/shell_hooks.py:5,19,543` | "consent", "consent on first use" | First-use consent for shell hooks (allowlist). Generic security. |
| `agent/credential_pool.py:1522` | "without user consent" | Comment about Claude credentials.json. Generic security. |
| `agent/google_oauth.py` | "consent" | OAuth consent screen flow. Standard OAuth. |
| `agent/error_classifier.py` | "consent" | Error classification category. Generic. |
| `agent/bedrock_adapter.py` | "consent" | AWS Bedrock usage consent. Generic. |

**M2 cleanup requirement: ZERO files.** There is nothing to remove because Guinevere-specific safety code does not exist in the installed Hermes.

---

## 6. Secret Handling Architecture

### 6.1 Secret Storage

| Secret | Storage Location | Loaded Via | Logged? |
|---|---|---|---|
| API keys (OpenAI, OpenRouter, etc.) | `~/.hermes/.env` | `hermes_cli/env_loader.py:load_hermes_dotenv()` | **NO** — redacted before persistence |
| Discord bot token | `~/.hermes/.env` (`DISCORD_BOT_TOKEN`) | Same env loader | **NO** |
| OpenRouter API key | `~/.hermes/.env` (`OPENROUTER_API_KEY`) | Same env loader | **NO** |
| 9Router key | Not found in installed code | N/A | N/A |
| PG/Redis passwords | Not found in installed code | N/A | N/A |
| HERMES_OPERATOR_PASS | Not found in installed code | N/A | N/A |

**Source:** `hermes_cli/env_loader.py` lines 212-247. Loading order:
1. `~/.hermes/.env` (user config, overrides stale shell exports)
2. Project `.env` (dev fallback, fills missing values only)
3. External secret sources (Bitwarden Secrets Manager, lines 250-323)

### 6.2 Secret Redaction Pipeline

**File:** `agent/redact.py` (505 lines)

Comprehensive regex-based redaction system covering 30+ secret patterns:

| Category | Patterns | Example |
|---|---|---|
| API key prefixes | 27 vendor patterns | `sk-`, `ghp_`, `AIza`, `AKIA`, `hf_`, `xai-` |
| ENV assignments | `*_API_KEY=*`, `*_TOKEN=*`, `*_SECRET=*` | `OPENAI_API_KEY=sk-...` |
| JSON fields | `"apiKey": "..."`, `"token": "..."` | Credential JSON bodies |
| Auth headers | `Authorization: Bearer ...` | HTTP auth |
| Telegram tokens | `bot<digits>:<token>` | Discord/Telegram bots |
| Private keys | `-----BEGIN PRIVATE KEY-----` | SSH/PGP keys |
| DB connection strings | `postgres://user:pass@host` | PG/Redis/MySQL URLs |
| JWTs | `eyJ...` tokens | Auth tokens |
| Discord mentions | `<@snowflake_id>` | User/role mentions |
| Phone numbers | `+1XXXXXXXXXX` | Signal/WhatsApp |

**Controls:**
- `HERMES_REDACT_SECRETS` env var (default: `true`) — snapshotted at import time, immune to runtime mutation (`agent/redact.py:67`)
- `RedactingFormatter` logging formatter class (`agent/redact.py:496-504`)
- `mask_secret()` utility for display-time masking (`agent/redact.py:200-244`)

### 6.3 Secret Handling in Fork

The fork inherits the full Hermes secret pipeline. How it loads:

1. `cli.py:174` and `run_agent.py:95` call `load_hermes_dotenv()` at import time
2. `hermes_constants.py:404-406` provides `get_env_path()` pointing to `~/.hermes/.env`
3. All credential env vars are sanitized for non-ASCII on load (`env_loader.py:102-143`)
4. `run_agent.py:1807-1835` applies `_redact_message_content()` to every message before persistence
5. `run_agent.py:1905` applies `redact_sensitive_text()` to system prompts before session JSON write

**Guinevere-specific additions needed:**
- `HERMES_OPERATOR_PASS`: Not present in upstream. Must be added to `.env` loading if needed for P24 runtime.
- `DISCORD_BOT_TOKEN`: Already handled by upstream env loader.
- 9Router key: Not present in upstream. Custom env var needed.
- PG/Redis passwords: Not present in upstream. Custom env vars needed. Will be caught by `redact.py` DB connection string pattern (`_DB_CONNSTR_RE`, line 141).

---

## 7. Disposition for P24

### 7.1 Runtime Safety Code (REMOVED by ADR-062)

**Nothing to remove from installed Hermes code.** The Guinevere-specific safety constructs (HARD STOP protocol, consent gate, PersonaSafetyPolicy enforcement, Y-baseline levels) exist ONLY in the Guinevere documentation layer (AGENTS.md, ADRs, PersonaSafetyPolicy). The installed Hermes v0.15.2 Python code has ZERO instances of these patterns.

The runtime exemption is enforced **structurally** (by not implementing these constructs in the runtime), not by removing existing code.

### 7.2 Dev-Workflow Safety Code (KEPT)

The following remain in force for the Guinevere dev workflow (AGENTS.md §0 + §2.1 + §6.4):

- HARD STOP protocol — absolute, no bypass (AGENTS.md line 34)
- Consent-safety mandate — no surveillance without consent (AGENTS.md line 35)
- Y4 baseline / Y5 ceiling / Y6 forbidden (AGENTS.md line 36, PersonaSafetyPolicy lines 247-253)
- Secret handling — never commit, never expose (AGENTS.md lines 33, 43)
- All 18+ BLOCKING rules (AGENTS.md lines 26-46)

### 7.3 Schema Changes (ADR-066)

The `consent_ref` schema carve-out is a **future migration** (ADR-066 status: Proposed). It will:
- Add `event_source` discriminator column to 5 event-store tables
- Make `consent_ref` nullable for `event_source='hermes_runtime'`
- Enforce via CHECK constraint that dev_workflow events retain NOT NULL

### 7.4 Secret Handling Disposition

| Component | Disposition | Notes |
|---|---|---|
| `.env` loading | PORT (inherit) | `hermes_cli/env_loader.py` works as-is |
| Redaction pipeline | PORT (inherit) | `agent/redact.py` covers all known patterns |
| HERMES_OPERATOR_PASS | MODIFY-CREATE | New env var, add to `.env` loading if needed |
| Discord bot token | PORT (inherit) | Already handled |
| 9Router key | MODIFY-CREATE | New env var |
| PG/Redis passwords | MODIFY-CREATE | New env vars, caught by `_DB_CONNSTR_RE` |
| Bitwarden integration | PORT (inherit) | Optional, already supported |

---

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| ADR-066 not yet implemented — event-store tables will block on `consent_ref NOT NULL` for autonomous events | HIGH | Implement migration before first Hermes runtime event write |
| Guinevere-specific secrets (HERMES_OPERATOR_PASS, 9Router key) not in upstream redaction patterns | MEDIUM | Add custom prefix patterns to `_PREFIX_PATTERNS` in `agent/redact.py` |
| `HERMES_REDACT_SECRETS` can be disabled via config.yaml | LOW | Document that this must remain `true` for Guinevere deployments |
| "Safe mode" toolset name in `toolset_distributions.py:94` could confuse auditors | LOW | Cosmetic only — not safety infrastructure |
| PersonaSafetyPolicy not in installed code — safety enforcement is doc-only | MEDIUM | For P24 runtime, Y-baseline is structural (T4 founder quorum) not code-enforced |

---

## 9. Verdict

**PASS** — The boundary is clean. The installed Hermes v0.15.2 codebase contains ZERO Guinevere-specific safety patterns (hard_stop, consent_gate, safe_mode, PersonaSafetyPolicy). The dual-paradigm established by ADR-062 is structurally enforced: runtime is exempt by absence of implementation; dev-workflow safety remains in AGENTS.md/PersonaSafetyPolicy/ADRs. Secret handling is well-architected in the upstream code (comprehensive redaction, .env loading, Bitwarden support). The only M2 work is adding Guinevere-specific env vars (HERMES_OPERATOR_PASS, 9Router key, PG/Redis passwords) to the existing .env loading pipeline and optionally extending redaction patterns.
