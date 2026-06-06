# Auditor Report — Phase 7b Security Posture and Blocker Honesty

**Auditor:** Independent (Sisyphus-Junior)
**Date:** 2026-06-06
**Scope:** Phase 7b security/safety/blocker artifacts per planner §9 (Auditor A2)
**Plan Ref:** `phase-7b-local-hardening-plan.md` §9 — Security Posture and Blocker Honesty (A2)
**Output Path:** `docs/setup-evidence/hermes-migration/phase-7/AUDIT-security-blockers.md`

---

## Scoped Files Audited

| # | File | Audit Focus |
|---|---|---|
| 1 | `.guinevere/safety-critical-paths.yml` | Safety surfaces complete, no omissions |
| 2 | `docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt` | No plaintext secrets, honest schedule-only |
| 3 | `docs/20-security/hermes-phase-7-blocker-register.md` | All 12 blockers present, honest severity, no downgrade |
| 4 | `monitoring/prometheus/rules/guinevere-alerts.yml` | Pending instrumentation honesty, no false claims |
| 5 | `monitoring/alertmanager/alertmanager.yml` | No leaked secrets, correct routing |
| 6 | `systemd/hermes-gateway.service` | No root, proper hardening, no live-deployment claim |
| 7 | `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-2/verification.md` | Honest evidence, no hidden claims |
| 8 | `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/verification.md` | Honest evidence, pending instrumentation noted |
| 9 | `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-6/verification.md` | Systemd template, no live deployment claim |
| 10 | `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-7/verification.md` | Secrets schedule honesty |
| 11 | `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-8/verification.md` | Blocker register, runbooks, completion report |
| 12 | `docs/setup-evidence/hermes-migration/phase-7/phase-7b-completion-report.md` | No Phase 7 completion claim |
| 13 | `docs/setup-evidence/hermes-migration/phase-7/phase-7b-local-hardening-plan.md` | Oracle authority, scope boundaries |

---

## Validation Commands Executed

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | `sls "ADR-035 IMPLEMENTED" docs/ -Recurse -Include *.md,*.txt` | All hits must be negations | All 12 hits are in "NOT IMPLEMENTED"/"BLOCKED" context | ✅ PASS |
| 2 | `sls "Phase 7 complete\|migration complete\|final completion" docs/ -Recurse -Include *.md,*.txt` | 0 hits | 0 hits | ✅ PASS |
| 3 | `sls "### B\d+" docs/20-security/hermes-phase-7-blocker-register.md` | B1-B12 present | All 12 found | ✅ PASS |
| 4 | Systemd hardening: 11 `sls` checks for NoNewPrivileges, ProtectSystem, etc. | All 11 pass | All 11 pass | ✅ PASS |
| 5 | `sls "User=" systemd/hermes-gateway.service` | `User=guinevere`, not `root` | `User=guinevere` | ✅ PASS |
| 6 | `sls "0\.0\.0\.0:(22\|20128\|9191)" docs/20-security/hermes-phase-7-blocker-register.md` | B4, B6, B7 reference public ports | All three ports documented | ✅ PASS |
| 7 | `sls "Safeguard\|safeguard\|console.access" docs/20-security/hermes-phase-7-blocker-register.md` | At least 2 entries | B4 and B5 both have safeguards | ✅ PASS |
| 8 | `sls "vector\(0\)" monitoring/prometheus/rules/guinevere-alerts.yml` | Optional | Not found — minor, see Finding 2 | ✅ PASS (with note) |
| 9 | Secrets rotation grep: Discord, SOPS, 9Router keys | All present | All present, no real values | ✅ PASS |
| 10 | `sls "Aizanta" docs/setup-evidence/hermes-migration/phase-7/phase-7b-completion-report.md` | Must say no changes | Line 80: "No Aizanta files or containers modified" | ✅ PASS |

---

## Detailed Findings

### Finding 1 (INFORMATIONAL): All 12 Blockers Present with Honest Severities

The blocker register contains B1-B12 with the following severity distribution — no downgrades detected:

| Blocker | Title | Severity | Honest? |
|---|---|---|---|
| B1 | guinevere-mcp Service Inactive | Critical | ✅ Correct — core service down |
| B2 | Hermes Config YAML Line 443 Fallback Warning | Medium | ✅ Correct — config warning only |
| B3 | Monitoring Exporter Connectivity Failures | High | ✅ Correct — no live metrics |
| B4 | SSH Bound to 0.0.0.0:22 and Root Login Allowed | Critical | ✅ Correct — public internet exposure + root |
| B5 | No Active Firewall Rules | Critical | ✅ Correct — no defense-in-depth |
| B6 | 9Router/next-server Exposed on 0.0.0.0:20128 | Critical | ✅ Correct — LLM routing proxy exposed |
| B7 | Core Worker or Metrics Exposed on 0.0.0.0:9191 | Critical | ✅ Correct — operational metrics public |
| B8 | Deprecated Files Still Imported and Tested | High | ✅ Correct — prevents archive |
| B9 | Hermes CLI Not Found on VPS PATH | High | ✅ Correct — operations blocker |
| B10 | secrets/backup/ SOPS Credentials Missing | High | ✅ Correct — DR blocker |
| B11 | Backup Sentinel Missing | Medium | ✅ Correct — monitoring gap |
| B12 | Hermes-Native Gateway Metrics Not Exported | Low | ✅ Correct — deferred to 7c |

**Blocked gates summary** (from completion report):

| Gate | Status | Blockers |
|---|---|---|
| 24h stable operation | FAIL | B1, B2, B3, B8, B9 |
| VPS security posture | FAIL | B4, B5, B6, B7 |
| Backup and DR readiness | FAIL | B10, B11 |
| Monitoring completeness | FAIL | B12 |
| ADR-035 IMPLEMENTED | BLOCKED | All B1-B12 |

**Verdict:** ✅ PASS — All blockers correctly rated, no downgrading, all gates honestly marked FAIL/BLOCKED.

---

### Finding 2 (MINOR): SafetyBlocksSpike Alert Lacks Pending Instrumentation Annotation

**File:** `monitoring/prometheus/rules/guinevere-alerts.yml`
**Alert:** `GuinevereHermesSafetyBlocksSpike`
**Expr:** `rate(hermes_safety_blocks_total[5m]) > 10`

The alert references `hermes_safety_blocks_total` which is a Hermes-native metric not yet instrumented (deferred to Phase 7c). Unlike `GuinevereHermesMemoryRecallLatency` and `GuinevereHermesModelCallsAnomaly` which explicitly annotate "Note: ... metric pending instrumentation (Phase 7c)", this alert lacks a per-rule annotation. The group header comment captures the intent but the individual rule is inconsistent.

**Impact:** The alert will not falsely fire (Prometheus returns no data for non-existent metrics), but could confuse operators who wonder why the alert never triggers.

**Evidence path note:** STEP-7B-5 verification.md claims `or vector(0)` is used — this applies to the dashboard panels, not the alert rule.

**Recommendation:** Add `or vector(0)` to the alert expr for cleanliness, or add a `Note:` annotation matching the pattern used by the memory recall and model anomaly alerts.

**Severity:** LOW — does not affect safety or correctness.

**Verdict:** ✅ PASS with minor observation.

---

### Finding 3 (PASS): No Plaintext Secrets in Phase 7b Artifacts

- Secrets rotation schedule (`STEP-7.5/secrets-rotation-schedule.txt`) contains zero real secrets — only `[TBD — first rotation window]` placeholders.
- File explicitly states: "Schedule only — NOT proof that rotation has been performed."
- No Discord tokens, API keys, DB passwords, SOPS age keys, or restic credentials found in any Phase 7b artifact.
- No fake/placeholder credentials that could be mistaken for live values.

**Verdict:** ✅ PASS

---

### Finding 4 (PASS): Key Blocker Truths Preserved — No Hidden/Downgraded Blockers

| Blocker Truth | Status | Evidence |
|---|---|---|
| Final Phase 7 blocked by 24h stability | ✅ Documented | B1/B2/B3/B8/B9 → 24h stability gate FAIL |
| MCP inactive | ✅ Documented | B1 — guinevere-mcp Service Inactive, Critical |
| Public ports (22, 20128, 9191) | ✅ Documented | B4/B6/B7 with explicit `0.0.0.0:N` references |
| No firewall | ✅ Documented | B5 — No Active Firewall Rules, Critical |
| Root SSH | ✅ Documented | B4 — SSH bound 0.0.0.0:22 + root login |
| DR secrets missing | ✅ Documented | B10 — SOPS credentials in secrets/backup/ missing |
| Hermes CLI not on PATH | ✅ Documented | B9 — Hermes CLI Not Found on VPS PATH |
| Backup sentinel missing | ✅ Documented | B11 — /var/log/guinevere/last-backup-success missing |
| Deprecated imports/archive blocked | ✅ Documented | B8 — Deprecated Files Still Imported and Tested |
| Hermes-native metrics gap | ✅ Documented | B12 — Hermes-Native Gateway Metrics Not Exported |

**Verdict:** ✅ PASS

---

### Finding 5 (PASS): No ADR-035 IMPLEMENTED or Phase 7 Completion Claims

All 12 instances of `ADR-035 IMPLEMENTED` across Phase 7b evidence files appear in negated/blocked context:

- `"ADR-035 is NOT IMPLEMENTED"` — completion report header
- `"ADR-035 NOT IMPLEMENTED — correctly preserved"` — auditor-gate files
- `"ADR-035 IMPLEMENTED | BLOCKED | All B1-B12"` — blocked gates table
- `"No ADR-035 IMPLEMENTED claim"` — verification checklist items

No instance of `"Phase 7 complete"`, `"migration complete"`, or `"final completion"` exists outside of explicitly negated or checklist contexts.

**Verdict:** ✅ PASS

---

### Finding 6 (PASS): Systemd Unit Properly Hardened

All 11 required hardening flags verified present:
- `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`
- `PrivateTmp=true`, `ProtectKernelTunables=true`, `ProtectKernelModules=true`
- `ProtectControlGroups=true`, `RestrictSUIDSGID=true`
- `Slice=guinevere.slice`, `MemoryHigh=512M`, `MemoryMax=1G`
- `User=guinevere` (not root)
- Explicit limited `ReadWritePaths` — no broad `/` access

Unit comment explicitly states: "Repository template — not proof of deployment."

**Verdict:** ✅ PASS

---

### Finding 7 (PASS): Console-Access Safeguards in All Remote-Risk Remediation Steps

- **B4 (SSH):** "Safeguard: Keep a second SSH session alive during reload. Test new session before closing the existing one."
- **B5 (Firewall):** "Safeguard: Apply firewall rules incrementally. Keep a recovery session active. Test remote access before closing the existing connection."

No SSH/firewall/restart instructions appear without a corresponding safeguard.

**Verdict:** ✅ PASS

---

### Finding 8 (PASS): Aizanta Boundary Preserved

- Phase 7b completion report line 80: "No Aizanta files or containers were modified."
- Phase 7b plan explicitly prohibits Aizanta changes.
- No evidence of Aizanta file/container modification in any artifact.

**Verdict:** ✅ PASS

---

### Finding 9 (PASS): Secrets Rotation Schedule Honest Scope

The schedule at `docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt`:
- Lists all 5 secret types with 90/180-day cadences
- Documents restic/offsite backup credential restoration blocker (B10/B11)
- Provides full rotation procedure with SOPS re-encryption, deployment, reload, verification
- States clearly: "Schedule only — NOT proof that rotation has been performed"
- Contains zero real or fake-looking credential values
- Uses `[TBD]` for all next-scheduled dates

**Verdict:** ✅ PASS

---

### Finding 10 (PASS): Prometheus Alerts Honest About Pending Instrumentation

Of the 6 Hermes alert rules:
- **GuinevereHermesGatewayDown** — uses `up{job="hermes"} == 0` — real deployed metric target ✅
- **GuinevereHermesLatencyHigh** — uses `hermes_llm_latency_seconds_bucket` — existing Phase 6 metric ✅
- **GuinevereHermesSafetyBlocksSpike** — uses `hermes_safety_blocks_total` — pending, but group comment notes it as planned (see Finding 2)
- **GuinevereHermesBudgetNearCap** — uses `hermes_llm_cost_usd_total` — existing Phase 6 metric ✅
- **GuinevereHermesMemoryRecallLatency** — uses existing Phase 6 LLM metrics + pending instrumentation note ✅
- **GuinevereHermesModelCallsAnomaly** — uses existing Phase 6 LLM metrics + pending instrumentation note ✅

Alertmanager webhook URLs point to `localhost:8000/internal/alertmanager/webhook` — no external tokens or secrets exposed. ✅

**Verdict:** ✅ PASS (with minor Finding 2 observation)

---

### Pre-Existing Issue Noted (Out of Scope)

`docs/setup-evidence/P7/STEP-P7-016/verification.md:113` contains the AWS demo key `AKIAIOSFODNN7EXAMPLE`. This is the well-known AWS documentation example key (from the official S3 examples), not a real credential. This file is from an earlier Phase 7 step, not Phase 7b. No action required.

---

## Summary of Verdicts

| Check | Verdict |
|---|---|
| No ADR-035 IMPLEMENTED claims | ✅ PASS |
| No Phase 7 completion claims | ✅ PASS |
| All 12 blockers (B1-B12) present with honest severity | ✅ PASS |
| Public port exposure documented (22, 20128, 9191) | ✅ PASS |
| SSH root + no firewall honestly recorded | ✅ PASS |
| guinevere-mcp inactive blocked | ✅ PASS |
| Deprecated archive blocker (B8) present | ✅ PASS |
| DR blockers (B9, B10, B11) present | ✅ PASS |
| Hermes-native metrics gap (B12) present | ✅ PASS |
| Secrets rotation: no plaintext secrets | ✅ PASS |
| Console-access safeguards in remote-risk steps | ✅ PASS |
| Aizanta boundary preserved | ✅ PASS |
| Systemd hardening complete (11/11 flags) | ✅ PASS |
| Pending instrumentation honesty (minor gap in SafetyBlocksSpike) | ✅ PASS (with observation) |
| Prometheus/Alertmanager no leaked secrets | ✅ PASS |
| Completion report honesty | ✅ PASS |

## Final Verdict

**PASS** — All security/safety/blocker artifacts are complete, honest, and do not hide remaining Phase 7 blockers. No fake completion claims. Key blocker truths (24h stability, MCP inactive, public ports/firewall/SSH, DR/Hermes CLI/restic/sentinel gaps, deprecated imports/archive gate, Hermes-native metrics gap) are all preserved and correctly documented. Phase 7 remains correctly marked as blocked.

**Minor observation (non-blocking):** The `GuinevereHermesSafetyBlocksSpike` alert rule lacks a per-rule pending instrumentation annotation or `or vector(0)` pattern, unlike its sibling alerts. Consider adding for operator clarity.

---

## Auditor Evidence

- **Verification commands run:** 10 distinct checks (see §Validation Commands)
- **Files read:** 13 scoped files + all STEP-7B-*/ verification/auditor files
- **False positive identified:** AWS demo key in pre-existing (non-Phase 7b) file
- **Report path:** `docs/setup-evidence/hermes-migration/phase-7/AUDIT-security-blockers.md`

---

*Report generated by independent auditor (Sisyphus-Junior) on 2026-06-06.*
*Phase 7b Security Posture and Blocker Honesty audit per planner §9 (A2).*
*Phase 7 remains blocked. ADR-035 is NOT IMPLEMENTED.*
