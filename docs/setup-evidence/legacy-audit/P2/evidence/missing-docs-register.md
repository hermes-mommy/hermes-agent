# P2 Missing Docs Register

**Date:** 2026-06-25
**Auditor:** Read-only implementation audit
**Scope:** Every document P2 should have but doesn't, or has but is stale/misleading.
**Method:** Cross-referenced all audit files (6 round-1 + 6 round-2 + 4 research) against actual repo state.

---

## 1. MISSING DOCUMENTS

| ID | What is Missing | Why It Matters | Severity | Recommended Path |
|----|----------------|---------------|----------|-----------------|
| DOC-MISS-001 | P2-022 in CHECKLIST.md | CHECKLIST.md P2 section lists 21 steps (P2-001..P2-021) but omits P2-022 (service masked). The most important architectural decision of P2 is invisible in the primary onboarding doc. | HIGH | Add P2-022 row to CHECKLIST.md P2 section |
| DOC-MISS-002 | P2 → Hermes/core REST transition document | No single document explains the architectural transition from standalone bot → Hermes Gateway → core REST publisher. Information is scattered across ADR-035, P20 evidence, phase-2-discord.md, and P2-022. | HIGH | Create `docs/setup-evidence/P2/P2-ARCHITECTURE-TRANSITION.md` or `docs/50-architecture/discord-writer-ownership.md` |
| DOC-MISS-003 | Canonical service unit reconciliation | Three guinevere-discord.service copies exist (systemd/, deploy/discord/). Two hermes-gateway.service copies exist (systemd/, scripts/). No document explains which is canonical, which is deployed, and why duplicates exist. | HIGH | Create `docs/setup-evidence/P2/P2-SERVICE-UNIT-RECONCILIATION.md` |
| DOC-MISS-004 | `secrets/.env.discord.sops` | Deploy unit references this file in `ExecStartPre` but it doesn't exist. The actual encrypted file is `secrets/discord-secrets.enc.yaml` in YAML format, not dotenv. | HIGH | Either create the missing file or update the deploy unit to reference the existing file |
| DOC-MISS-005 | `#alerts` channel creation evidence | SRS, FSD, PRD, and acceptance criteria all reference `#alerts` channel. But no such channel exists in `channel-ids.yaml`. No evidence of its creation. | MEDIUM | Either create `#alerts` channel and update `channel-ids.yaml`, or update governance docs to reference `system-health` |
| DOC-MISS-006 | auditor-gate.md per P2 step | Later phases (P3+) include `auditor-gate.md` in each step evidence directory. P2 has `verification.md` and `verifiers/` but no `auditor-gate.md`. | MEDIUM | Not required for P2 (was completed before pattern established) but document the convention gap |
| DOC-MISS-007 | Gotify deployment evidence | `secrets/gotify.enc.yaml` doesn't exist. No systemd unit. No evidence `docker-compose up` was run. P2-020/021 checkboxes remain unchecked in PROGRESS.md. | MEDIUM | Create `docs/setup-evidence/P2/STEP-P2-020/gotify-deployment-evidence.md` with runtime verification |
| DOC-MISS-008 | Updated command count reference | All documents (CHECKLIST, PROGRESS, cmd_help docstring) have stale hardcoded command counts. No durable reference to `_command_registry.py:command_count()`. | MEDIUM | Replace hardcoded numbers with dynamic reference or update all to 49 |
| DOC-MISS-009 | Shadow pipeline deployment guide | `shadow_monitor.py` and `shadow_pipeline.py` exist but are disabled by default. No documentation on how to enable them or what they do. | LOW | Create `docs/setup-evidence/P2/P2-SHADOW-PIPELINE.md` |
| DOC-MISS-010 | Gotify app token generation guide | Operations doc references `secrets/gotify.enc.yaml` but no guide explains how to generate the Gotify app token or encrypt it with SOPS. | LOW | Add to `docs/setup-evidence/P2/STEP-P2-020/` |

---

## 2. STALE DOCUMENTS (DOCS THAT CONTAIN FALSE CLAIMS)

| ID | What is Stale | Where | Actual State | Severity |
|----|--------------|-------|-------------|----------|
| DOC-STALE-001 | `[x] P2-017: systemctl status guinevere-discord -> active` | CHECKLIST.md:273 | Service is masked per P2-022 | HIGH |
| DOC-STALE-002 | `[x] P2-018: journalctl ... "Connected to Discord Gateway"` | CHECKLIST.md:274 | Service is masked; Hermes Gateway handles Discord now | HIGH |
| DOC-STALE-003 | `[x] P2-019: SEV0 alert test -> thread in #alerts within 15s` | CHECKLIST.md:275 | `#alerts` doesn't exist; `send_alert()` never called | HIGH |
| DOC-STALE-004 | "33 slash commands" / `commands_count=33` | CHECKLIST.md:243,265 | Code has 49 commands | HIGH |
| DOC-STALE-005 | "35 commands" | PROGRESS.md:146 | Code has 49 commands | MEDIUM |
| DOC-STALE-006 | "lists all 33 slash commands" | `cmd_help.py:4` docstring | Code has 49 commands | LOW |
| DOC-STALE-007 | "No bot.py listener exists yet... inactive until P2-017" | `cmd_safeword.py:598-601` | `_entrypoint.py` DOES wire it | LOW |
| DOC-STALE-008 | "13 channels" | CHECKLIST.md:261, PROGRESS.md:142 | `channel-ids.yaml` has 14 channels (incl. rituals) | LOW |
| DOC-STALE-009 | "Port 8080" | `docs/audit/P2-AUDIT-COMPLETE.md:64` | Gotify uses port 8081 (code + compose) | LOW |
| DOC-STALE-010 | "P2-001 through P2-021 (21 steps)" | CHECKLIST.md:244 | Actually 22 steps (P2-022 service masked) | MEDIUM |
| DOC-STALE-011 | "21 steps" header | PROGRESS.md:134 | Lists 22 steps including P2-022 | LOW |
| DOC-STALE-012 | `guinevere-dev` channel name | `channel-ids.yaml` | Channel is now used as `guinevere-logs` per P20 evidence | LOW |
| DOC-STALE-013 | P2-018 VPS checks all "PENDING" | `STEP-P2-018/verification.md` | Step was marked PASS in old audit despite VPS checks being pending | MEDIUM |
| DOC-STALE-014 | P2-019 claimed "SEV0 alert test" verified | PROGRESS.md:156 | `send_alert()` is dead code; no alert test could have passed | HIGH |
| DOC-STALE-015 | `#alerts` references in SRS/FSD/PRD | `docs/10-governance/` (13 refs) | Channel doesn't exist; code routes to `system-health` | MEDIUM |
| DOC-STALE-016 | `secrets/gotify.enc.yaml` reference | `docs/40-operations/47-WebSocketLifecycle_v1.0.md:351` | File does not exist | MEDIUM |

---

## 3. P2-FIX-PLAN.md OUTSTANDING ITEMS

| Phase | Action | Status | Notes |
|-------|--------|--------|-------|
| 2 | Update PROGRESS.md: 33 → 35 commands | PARTIALLY DONE | Now needs 35 → 49 |
| 3 | Delete ghost channels (project-alpha-dev, project-alpha-docs, project-beta-dev) | NOT DONE | Channels still in channel-ids.yaml |
| 3 | Rename guinevere-dev → guinevere-logs | NOT DONE | Channel is functionally guinevere-logs but named guinevere-dev in YAML |
| 4 | Create cron for #system-health | NOT DONE | No automation |
| 4 | Create cron for #cost-tracker | NOT DONE | No automation |
| 4 | Create cron for #guinevere-evidence | NOT DONE | No automation |

---

## 4. SEVERITY SUMMARY

| Severity | Missing | Stale | Total |
|----------|---------|-------|-------|
| HIGH | 4 | 5 | 9 |
| MEDIUM | 5 | 5 | 10 |
| LOW | 1 | 5 | 6 |
| **TOTAL** | **10** | **16** | **26** |

---

## 5. RECOMMENDATIONS (PRIORITY ORDER)

1. **CRITICAL:** Update CHECKLIST.md P2-017/018/019 to reflect masked service and current architecture
2. **CRITICAL:** Update CHECKLIST.md command count from 33 to 49 (or dynamic reference)
3. **HIGH:** Create `secrets/.env.discord.sops` or update deploy unit to reference existing `secrets/discord-secrets.enc.yaml`
4. **HIGH:** Create P2 → Hermes/core REST transition document
5. **HIGH:** Create canonical service unit reconciliation document
6. **MEDIUM:** Resolve `#alerts` channel: create it or update governance docs
7. **MEDIUM:** Update PROGRESS.md command count to 49
8. **MEDIUM:** Complete P2-FIX-PLAN.md Phase 3 and 4 items
9. **LOW:** Update stale docstrings (cmd_help.py, cmd_safeword.py)
10. **LOW:** Update channel-ids.yaml to reflect guinevere-logs rename

---

*End of missing docs register.*