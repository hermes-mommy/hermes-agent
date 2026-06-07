# Phase 6 Audit — 01 Safety Compliance

| Field | Value |
|---|---|
| Domain | Safety Compliance |
| ADR | ADR-035 v1.0 |
| Verdict | **PASS** |
| Evidence Root | `docs/setup-evidence/phase6-audit/` |
| Source Report | `research-reports/phase6-audit/01-safety-compliance.md` |

## Safety Controls Matrix

| ID | Control | Mechanism | Verdict | Evidence |
|---|---|---|---|---|
| SC-001 | API key encryption | `NINEROUTER_API_KEY` env var | PASS | `hermes-config/config.yaml` line 55: `key_env: NINEROUTER_API_KEY` |
| SC-002 | MCP tool whitelist | 7 tools in `fastmcp_custom.tools.include` | PASS | `hermes-config/config.yaml` lines 222-229; `enabled: false` (BD-008 gate) |
| SC-003 | Cost ceiling | `monthly_limit: 30.00` + budget_check.py hook | PASS | Config lines 72-76; hook line 151: `on_failure: block` |
| SC-004 | Surveillance separation | Zero surveillance refs in Hermes config | PASS | Full config review — no surveillance tools, separate API key |
| SC-005 | Fail-closed behavior | `on_failure: block` on all hooks; `fallback_on_timeout: deny` | PASS | Lines 153, 162, 173, 344 — all fail-closed |
| SC-006 | Aizanta isolation | Zero Aizanta modifications; ports 5433/6380 | PASS | Git diff-tree confirms zero Aizanta files |
| SC-007 | Consent preserved | consent_gate.py shell hook (pre_tool_call, priority 90) | PASS | Config lines 158-162; Python plugin G10 deferred to shell |
| SC-008 | Timeout bounds | budget 500ms, consent 200ms, DNR 50ms, approval 300000ms | PASS | Lines 152, 161, 172, 341 — all within reasonable bounds |

## Safety Plugin Gates (10 gates documented in config lines 120-131)

| Gate | Event | Scope |
|---|---|---|
| G01 HARD STOP | pre_llm_call | Plugin (in-process) |
| G02 Distress | pre_llm_call | Plugin |
| G03 Drift | post_llm_call | Plugin |
| G04 Recovery | pre_llm_call | Plugin |
| G05 Forbidden | transform_llm_output | Plugin |
| G06 Secrets | transform_llm_output | Plugin |
| G07 Yandere boundary | pre_llm_call | Plugin |
| G08 Yandere semantic | transform_llm_output | Plugin |
| G09 Auth matrix | pre_tool_call | Plugin |
| G10 Consent | pre_tool_call | Shell hook (consent_gate.py) |

## Evidence Artifacts

- Source report: `research-reports/phase6-audit/01-safety-compliance.md` (262 lines)
- Config: `hermes-config/config.yaml` (354 lines) — full review
- Auditor gate: `docs/setup-evidence/phase6-audit/auditor-gate-safety-isolation.md`
