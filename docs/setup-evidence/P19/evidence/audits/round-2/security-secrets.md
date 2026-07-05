# P19 Round-2 Re-Audit — Security & Secrets

**Auditor:** security-secrets
**Date:** 2026-06-25
**Scope:** Verify all round-1 security-secrets findings resolved.

## Verdict: PASS

## Round-1 Findings — Resolution Status

| # | Round-1 Finding | Resolution | Status |
|---|---|---|---|
| SEC-01 [HIGH] | Process-scoped env vars don't isolate | Plan §P19-006: `ProjectSecretsVault` in-memory keyed by project_id; `test_secret_isolation`; Global Constraints updated | ✅ RESOLVED |
| SEC-02 [MEDIUM] | Shared age key blast radius | Plan §P19-012: age rotation runbook verified in soak; accepted single-user risk documented | ✅ RESOLVED |
| SEC-03 [MEDIUM] | Deploy boundary test missing | Plan §P19-012: red-team project deploy ≠ core restart; `systemctl is-active` check | ✅ RESOLVED |
| SEC-04 [LOW] | Break-glass per-project scope | Plan §P19-009: `consent.emergency.break_glass_project` (project-scoped, 4h) | ✅ RESOLVED |

## Re-Audit Notes
All 4 security-secrets findings resolved. The critical SEC-01 fix replaces env vars with an in-memory `ProjectSecretsVault` — the correct isolation mechanism for a single shared process. The vault approach is now in Global Constraints, P19-006 scaffold, and the amendments table. `test_secret_isolation` asserts project A cannot access project B's token.

The hard-rejection criteria (no cross-project secret leak, deploy boundary) are mitigated with the vault + deploy boundary test.

## Hard Rejection Check
- Secrets/env leak between projects: ✅ MITIGATED (vault) + tested
- Deploy of another project touches Guinevere without gate: ✅ MITIGATED + tested
