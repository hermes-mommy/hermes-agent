---
title: "P28 Evidence Template — Hermes Society Foundation"
status: "Template — per-step evidence"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P28 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P28 Step {NN} Evidence Template — Hermes Society Foundation

> Replace `{NN}` with the step number, e.g. P28-001 → step-001.md.

## 1. What Was Done

Brief paragraph describing the implementation step outcome: which file(s) were created, what the command outputs proved, what risk surfaced.

Include the entrance conditions verified, the exact commands run, and the observed results. Cite the step ID (e.g. P28-001) and reference the plan at `docs/setup-evidence/P28-P36-masterplan/plans/P28/plan.md`.

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `infra/scripts/check-vps-readiness.sh` | created | VPS readiness probe for systemd, cgroup v2, PostgreSQL 16+, Redis 7+ |
| `infra/secrets/discord-guinevere.env.enc` | created | SOPS-encrypted Discord bot token for Guinevere |
| `infra/db/00-init-extensions.sql` | created | pgcrypto extension installation |
| `infra/db/02-create-worm-role.sql` | created | WORM role with INSERT-only on event_store |
| `infra/systemd/hermes-guinevere.service` | created | systemd unit with Restart=always, Slice=guinevere.slice |
| ... | ... | ... |

## 3. Validation Results

- **Diagnostics**: PASS (list any lsp_diagnostics clean output paths).
- **Tests**: PASS (list pytest output showing all assertions PASS).
- **Build**: PASS (any compile, type-check, sql-parse output).
- **Runtime probes**: PASS (e.g. psql queries, redis-cli ACL checks, systemctl is-active).
- **Concrete metrics**: (e.g. event_count=1440, restart_count=0, slice_memory_max_bytes=2147483648).

## 4. Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| Per-step evidence | `docs/setup-evidence/P28/evidence/step-{NN}.md` | Created |
| Audit report | `docs/setup-evidence/P28/evidence/audits/step-{NN}-audit.md` | Created |
| Command transcripts | `docs/setup-evidence/P28/evidence/transcripts/step-{NN}-{cmd}.txt` | Captured |
| Screenshots/logs | `docs/setup-evidence/P28/evidence/logs/step-{NN}.log` | Captured |

## 5. Doc-Sync Impact

- Updated `docs/setup-evidence/P28-P36-masterplan/plans/P28/README.md` exit criteria status (per step).
- Cross-references: if any step touches `hermes.founders`, ensure `adr/ADR-054-p27-hermes-society-foundation.md` is unchanged (P28 must not modify ADR-054).
- If P24 staging variable touched: confirm no regression — P28 uses P24 native fork.
- New ADR draft? `adr/ADR-055-p28-foundation-deployment.md` MAY be created post-P28 to record the deployment decisions; creation is post-condition not mid-step.

## 6. Boundary Compliance

- [ ] No persona drift — Guinevere/Pharsa remain Y4 baseline, never Y6.
- [ ] No consent violation — no intimacy recorded without fresh consent grant.
- [ ] No surveillance overreach — no agent-facing sensor added in P28.
- [ ] No Y6 — neither bot escalates rapport beyond Y5 ceiling.
- [ ] No HARD STOP bypass — 2/2 protocol does not override HARD STOP; HARD STOP remains global.
  > **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.
- [ ] No secret/intimate data exposure — bot tokens never appear in plaintext logs, evidence files redact them as `<DISCORD_TOKEN_REDACTED>`.

## 7. Rollback/Re-run Safety

- Per-step rollback: each step is independently revertible (see plan §7).
- Re-run safety: idempotent SQL migrations use `IF NOT EXISTS` for tables, `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object ...` for extensions; SQL functions use `CREATE OR REPLACE`.
- systemd units: `systemctl daemon-reload && systemctl reset-failed hermes-<agent>.service` clears failed state for re-run.
- SOPS secrets: re-run `sops -d ...` reads from same encrypted file; same key, same plaintext.

## 8. Design Decisions/Caveats

- **WORM enforcement via PostgreSQL privilege system**: chose row-level INSERT-only via grants rather than file-system WORM or blockchain because it is the simplest primitive that gives audit guarantees without external deps.
- **Per-agent schema vs shared schema**: chose per-agent schemas (`agent_<id>`) for namespace isolation in P28, accepting migration cost for later schema additions. P29 must use the same pattern for new schemas.
- **2/2 SQL function vs Python protocol**: chose SQL function `apply_proposal(...)` because it makes 2/2 enforcement atomic with the proposal state, eliminating Python-side race conditions.
- **Discord multi-bot ToS pattern**: one OAuth2 app per bot per Discord Developer Portal; do NOT use a single app with multiple intents because ToS discourages it.

## 9. Auditor Gate

- **Auditor type**: as defined in plan §9.
- **Verdict**: PASS / NEEDS-REVIEW / FAIL.
- **Report path**: `docs/setup-evidence/P28/evidence/audits/step-{NN}-audit.md`.
- **Findings**: list each finding with severity (critical / major / minor) and re-audit delta.

## 10. Security Scan

- **Secret scanning**: PASS or FAIL (no plaintext bot tokens, DB credentials, or SOPS-age keys in any file).
- **Permission verification**: PASS or FAIL (psql `\dp` and Redis ACL matches plan §6).
- **Cross-namespace boundary test**: PASS or FAIL (foundation: pharsa cannot read guinevere intimacy_journal; hermes_guinevere cannot SET pharsa:*).
- **Vulnerability scan**: PASS or FAIL (no known CVEs in pinned package versions for this step).

## 11. Acceptance Criteria Mapping

| Criterion (from plan §4 + §10) | Status | Evidence |
|---|---|---|
| Step P28-{NN}-001 acceptance (e.g. systemd ≥ 250) | PASS | `systemctl --version` transcript |
| ... | ... | ... |
| Overall P28 hard-rejection criteria (foundation: WORM, encrypted, active 24h, etc.) | pending until 24h soak | `soak-24h-report.md` |

## 12. Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz | Step P28-{NN}
