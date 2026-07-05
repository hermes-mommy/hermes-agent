# P19 Round-1 Audit — Safety & Consent

**Auditor:** safety-consent
**Date:** 2026-06-25
**Scope:** HARD STOP global, project pause distinct, safe-word global, consent per-project, F-01..F-15 preserved.

## Verdict: PASS (with conditions)

## Findings

### SAFE-01 [HIGH] Project pause restoration gate underspecified
**Finding:** Plan defines `project:{project_id}:paused` (per-project, weak) vs `life_kernel:hard_stop` (global). But the restoration rule for project pause is not specified. ConsentRevocationPolicy §10.3 bans silent reactivation for sensitive scopes. Does `/project resume <name>` require explicit Faiz readiness, or can P20 autonomy auto-resume a paused project?
**Impact:** If autonomy auto-resumes a paused project, it violates the "no silent reactivation" principle for the project's consent scope.
**Fix:** P19-009 scaffold: project pause restoration requires explicit Faiz `/project resume <name>` (mirrors safe-word restore). P20 idle autonomy may NOT auto-resume a paused project; it skips paused projects and picks the next active one. Document explicitly.
**Wave:** P19-009.

### SAFE-02 [MEDIUM] Surveillance confrontation block global — confirmed but untested
**Finding:** Plan correctly states surveillance confrontation block stays GLOBAL (safe-mode/distress/crisis). But no test asserts this in P19-009.
**Fix:** P19-009 red-team test: (d) during global safe-mode, surveillance confrontation blocked for ALL projects (not just the active one).
**Wave:** P19-009.

### SAFE-03 [MEDIUM] consent.autonomy.high_blast scope ambiguity
**Finding:** Plan says `consent.autonomy.high_blast` is global "unless project-scoped". This ambiguity could let a project's autonomy deploy affect Guinevere core.
**Impact:** Deploy boundary hard rejection ("deploy of another project can touch Guinevere without policy gate").
**Fix:** P19-009 scaffold: `consent.autonomy.high_blast` becomes **per-project** (project-scoped row). A project's high-blast autonomy applies ONLY to that project's deploy scope. Guinevere core deploy is NEVER covered by project autonomy — always requires explicit Faiz approval (per AGENTS.md §0.1). Document explicitly.
**Wave:** P19-009.

### SAFE-04 [LOW] Safe-word during project-switch
**Finding:** If Faiz says the safe-word mid `/project` switch, the switch must be abandoned and HARD STOP triggered. Plan does not specify ordering.
**Fix:** P19-007 scaffold: `/project` command checks `life_kernel:hard_stop` BEFORE applying switch; if HARD STOP active, refuse switch + neutral ack.
**Wave:** P19-007.

## Summary
Safety design is fundamentally correct: HARD STOP stays global (`life_kernel:hard_stop`); project pause is distinct (`project:{id}:paused`); safety scopes stay global; consent per-project for project scopes. The HIGH finding (SAFE-01, project pause restoration) and MEDIUM (SAFE-03, high_blast scope) are specification gaps that must be closed in P19-009 to prevent autonomy from bypassing consent restoration.

## Hard Rejection Check
- HARD STOP not global: ✅ MITIGATED (single key, P19-005 red-team)
- Project pause conflated with HARD STOP: ✅ MITIGATED (distinct keys, P19-009 red-team)
- Consent/surveillance not per-project: ✅ MITIGATED (project_id in ledger, check_consent(scope, project_id))
- Safe-word global: ✅ (HARD STOP global)
