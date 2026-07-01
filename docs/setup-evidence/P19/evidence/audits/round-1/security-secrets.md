# P19 Round-1 Audit — Security & Secrets

**Auditor:** security-secrets
**Date:** 2026-06-25
**Scope:** Per-project secrets, env isolation, deploy boundary, no cross-project read.

## Verdict: PASS (with conditions)

## Findings

### SEC-01 [HIGH] Process-scoped env vars on single shared process
**Finding:** Plan proposes `GUINEVERE_{PROJECT}_{KEY}` process-scoped env vars. But Guinevere runs as a single `guinevere-core` systemd process with multiple projects' background cognition in-process. Process-scoped env vars cannot isolate between projects within one process — all in-process code sees all env vars.
**Impact:** Project A's in-process adapter could read project B's env var (no OS-level isolation within a process).
**Fix:** P19-006 scaffold: secrets are NOT loaded into env vars for in-process multi-project. Instead, secrets are decrypted into an in-memory `ProjectSecretsVault` keyed by `project_id`; each adapter requests `vault.get(project_id, domain)` and only receives its own. Env vars (`GUINEVERE_{PROJECT}_*`) are only for single-project systemd units (per-project service instances, optional). Document the vault approach as primary.
**Wave:** P19-006.

### SEC-02 [MEDIUM] age recipient shared — compromise blast radius
**Finding:** Plan says shared age recipient (Faiz's key) is OK because SOPS encrypts per-file. But if Faiz's age key is compromised, ALL projects' secrets are exposed (one key decrypts all files).
**Impact:** Single point of failure for all project secrets.
**Fix:** Document this as accepted risk (single-user, Faiz is owner). Mitigation: age key rotation procedure (SecretsRotationRunbook §10, Faiz-only) on suspected compromise. P19-012 soak: verify age rotation runbook works. Not a blocker for single-user scope.
**Wave:** P19-012 (runbook verification).

### SEC-03 [MEDIUM] Deploy boundary test missing
**Finding:** Plan §Security/Secrets Model says deploy of one project cannot touch Guinevere core without policy gate, but P19-012 scaffold does not include a test asserting this.
**Fix:** P19-012 scaffold: red-team test — deploy project X does NOT restart `guinevere-core` (unless X is the core project). Verify `systemctl is-active` for other services unchanged.
**Wave:** P19-012.

### SEC-04 [LOW] Break-glass per-project scope
**Finding:** Plan mentions break-glass per-project but doesn't define the consent scope.
**Fix:** P19-009: add `consent.emergency.break_glass_project` scope (project-scoped, time-bound max 4h, audited).
**Wave:** P19-009.

## Summary
Security design is mostly sound: per-project secret files, deploy boundaries, key compromise isolation. The HIGH finding (SEC-01, process-scoped env vars don't isolate within one process) is the key gap — must use an in-memory `ProjectSecretsVault` instead of env vars for in-process multi-project. SEC-02 (shared age key) is accepted single-user risk with documented rotation.

## Hard Rejection Check
- Secrets/env leak between projects: ✅ MITIGATED after SEC-01 fix (vault approach)
- Deploy of another project touches Guinevere without gate: ✅ MITIGATED (project-scoped high_blast; SEC-03 test)
