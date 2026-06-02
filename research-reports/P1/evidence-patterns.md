# Research: P0 Evidence Patterns (for P1 Replication)

| Field | Value |
|-------|-------|
| **Research Agent** | Explore |
| **Date** | 2026-05-31 |
| **Sources** | docs/setup-evidence/P0/STEP-P0-{000..028}/ |
| **Verdict** | 12-section verification.md schema; P0-006 best reference |

---

## Evidence Directory Structure

```
docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
├── verification.md                    ← 12-section canonical schema
├── <check>-status.txt                  ← command output proofs
├── <config>-config.txt                 ← configuration dumps
├── <service>-proof.txt                 ← service validation
├── aizanta-post-check.md               ← Aizanta co-location health check
└── p{N}-{XXX}-summary.md              ← Step completion summary
```

## verification.md — 12-Section Canonical Schema

1. **What Was Done** — high-level summary + approach
2. **Files Changed** — created/modified/deleted/renamed paths
3. **Validation Results** — diagnostics, tests, pre-existing vs introduced split
4. **Evidence Artifacts** — report paths, screenshots/logs, gate summaries
5. **Shared VPS Impact** — Aizanta container health, protected ports, Docker networks
6. **ADR Compliance** — ADR references verified
7. **AC Reference** — Acceptance Criteria cross-check
8. **Rollback / Re-run Safety** — rollback path, idempotency, recovery notes
9. **Design Decisions / Caveats** — why choices were made, deferred items
10. **Evidence Gate** — proof files exist, content valid
11. **Footer** — source task, date, implementer, validation method

## Proof Files Convention

- `*-status.txt` — service/package status checks
- `*-config.txt` — configuration file dumps
- `*-proof.txt` — deterministic verification outputs

## Aizanta Post-Check

Standard check: Docker container health (≥5 running), protected ports unchanged, no Docker network conflicts.

## Tracker Sync

- PROGRESS.md — step marked [x]
- CHECKLIST.md — verification items checked
- StepPrompts.md — evidence paths confirmed

## P1 Adaptations (No VPS SSH)

P1 steps are documentation/code-only. Replace "Shared VPS Impact" and "Aizanta Post-Check" with N/A declarations. LSP diagnostics replace live SSH verification.

| Field | Value |
|-------|-------|
| **Source** | bg_cd6ed2c0 — P0 evidence patterns |
| **File** | research-reports/P1/evidence-patterns.md |