## P2-010–P2-012 Safety, Evidence & ADR Compliance Matrix

**Date:** 2026-06-01
**Scope:** STEP-P2-010 (Slash Commands), STEP-P2-011 (Embed Colors), STEP-P2-012 (/status Command)
**Purpose:** Fill compliance/evidence gap before planner gate. Parent already has command/code report and token cleanup report. This report covers only compliance dimensions.
**Method:** Local file search only — read IMPLEMENTATION_GUIDE.md, ADR-Index, PROGRESS.md, CHECKLIST.md, AGENTS.md, and relevant ADR files.
**Dependencies on previous reports:** esearch-reports/P2/p2-010-012-local-code-docs-report.md (already parent-read for spec conflicts).

---

## §1 Safety-Affecting Classification

### 1.1 Are P2-010..P2-012 Safety-Affecting?

**Verdict: PARTIALLY — CREDENTIALS-ADJACENT only.**

| Domain (from AGENTS.md §2-1) | P2-010..P2-012 touches? | Rationale |
|---|---|---|
| persona | No | No persona behavior, mood, or identity changes |
| surveillance | No | No surveillance data, events, or consent changes |
| memory | No | No memory schema, recall, or encryption changes |
| consent | No | No consent/revocation policy changes |
| safety-policy | No | No PersonaSafetyPolicy edits |
| encryption | No | No encryption/key-management changes |
| distress-protocol | No | No D0-D4 protocol changes |
| yandere-boundary | No | No yandere FSM changes |
| agent-loop | No | No loop FSM or orchestration changes |
| **credentials** | **Yes (token-handling)** | Bot token extraction pattern touches SOPS/credential boundary |
| System Prompt Master | No | No system prompt edits |
| persona drift control | No | No drift detection changes |

**Conclusion:** The slash commands, embed colors, and /status handler do not alter safety-critical system behavior. However, **the bot token must be handled via SOPS-only pattern** (see §4). This is a credentials-adjacent constraint, not a full safety review. No Oracle review required — but the implementation sub-agent prompt must explicitly enforce the SOPS token pattern.

### 1.2 Constraints for Planner Gate

| Constraint | Rule | Source |
|---|---|---|
| Token pattern | MUST use src.discord.guild_setup.get_token() — NEVER os.environ.get("DISCORD_BOT_TOKEN") | AGENTS.md §0 BLOCKING, ADR-015 |
| No plaintext secrets in code/docs/evidence | Bot token must never appear in source, logs, evidence artifacts, or sub-agent reports | AGENTS.md NEVER commit secrets, CHECKLIST AC-SEC-003 |
| SOPS wrapper for verification scripts | All Discord scripts invoke via scripts/run-discord-verify.sh | batch-plan-007-009 pattern |
| Auditor gate mandatory per step | Independent auditor for each step BEFORE marking complete | AGENTS.md §1, §11 |
| No destructive ops | No rm -rf, force push, DROP TABLE, production deploy without explicit operator approval | AGENTS.md §0 BLOCKING |

---

## §2 Aizanta Health Check Commands

Extracted from docs/IMPLEMENTATION_GUIDE.md §6:

| Command | Purpose | Expected Output |
|---|---|---|
| systemctl status aizanta-* | All Aizanta services running | Active/running statuses |
| docker ps --filter "name=aizanta" | Aizanta containers up | Container list non-empty |
| psql -U aizanta -d aizanta -c "SELECT 1" | Aizanta DB accessible | Returns 1 |
| edis-cli -n 10 PING | Aizanta Redis responding | Returns PONG |

**Applicability to P2-010..P2-012:** These steps are code-only (slash commands, embed colors, /status handler). They do not touch VPS services, Docker, databases, or Redis. Aizanta verification is **NOT required** for these steps.

---

## §3 Guinevere Canonical Ports & Service Matrix

Extracted from docs/IMPLEMENTATION_GUIDE.md §11 Quick Reference:

| Service | Unit | Port |
|---|---|---|
| Core API | guinevere-core | **8000** |
| Discord Bot | guinevere-discord | — (Gateway) |
| 9Router | guinevere-9router | **20128** |
| MCP | guinevere-mcp | — |
| Loops | guinevere-loops | — |
| Scheduler | guinevere-scheduler | — |
| Surveillance | guinevere-surveillance | — |
| Monitoring | guinevere-monitoring | — |

**Canonical Ports:** 5433 PostgreSQL | 6380 Redis | 8000 Core API | 20128 9Router | 9090 Prometheus | 3000 Grafana

**Redis DBs:** 0-task queue, 1-session cache, 2-surveillance buffer, 3-loop state, 4-reserved, 5-rate limits/cost. DB 10-15: Aizanta — DO NOT TOUCH.

**Applicability to P2-010..P2-012:** P2-012 /status command queries Redis DB5 (cost) and Core API port 8000 (health). Ports/DBs are read-only references, not modifications.

---

## §4 No-Secret-Leak Rules

### 4.1 Absolute Rules (BLOCKING — NEVER bypass)

| Rule | Source |
|---|---|
| NEVER commit secrets (Discord bot token, API keys, DB passwords, surveillance credentials, SOPS/age keys) | AGENTS.md §0 |
| NEVER expose Faiz's personal/intimate data in artifacts, logs, or external tools | AGENTS.md §0 |
| NEVER store raw surveillance data in repo artifacts | AGENTS.md §0 |
| Plaintext secrets forbidden in ADRs, docs, code, evidence, logs, and sub-agent reports | ADR-015 |
| No plaintext secrets anywhere in code, docs, or logs (AC-SEC-003) | CHECKLIST.md §1.3 |

### 4.2 P2-010-Specific Token Rules

| Rule | Source |
|---|---|
| Bot token ONLY in SOPS-encrypted file: secrets/discord-secrets.yaml | P2-002 evidence, AGENTS.md |
| Token via src.discord.guild_setup.get_token() — reads DISCORD_SECRETS_PATH env var | guild_setup.py |
| NEVER os.environ.get("DISCORD_BOT_TOKEN") — REJECTED pattern | p2-010-012-local-code-docs-report.md §2.5 |
| All verification scripts via scripts/run-discord-verify.sh | batch-plan-007-009 pattern |
| No decrypted secrets in evidence artifacts | AGENTS.md §4 |
| No API keys in journal: journalctl grep for key/token/secret must be empty | CHECKLIST.md §3.4 |

### 4.3 Sub-Agent Prompt Constraint

Implementation sub-agent prompt MUST include:

`
MUST DO:
- Token via get_token() from src.discord.guild_setup
- All scripts invoked via scripts/run-discord-verify.sh
- Evidence files contain NO plaintext tokens
- Verification uses REST API (http.client)

MUST NOT DO:
- Do NOT commit, print, log, or expose bot token
- Do NOT use os.environ.get("DISCORD_BOT_TOKEN")
- Do NOT store decrypted token in evidence artifacts
`

---

## §5 Evidence Schema & Paths

### 5.1 Evidence Directory Structure

`
docs/setup-evidence/P2/STEP-P2-010/verification.md
docs/setup-evidence/P2/STEP-P2-011/verification.md
docs/setup-evidence/P2/STEP-P2-012/verification.md
`

NOT evidence/phase-2/step-010/ (old pattern — REJECTED).

### 5.2 Auditor Paths

`
audit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md
audit-reports/P2/STEP-P2-011/step-p2-011-auditor-report.md
audit-reports/P2/STEP-P2-012/step-p2-012-auditor-report.md
`

### 5.3 Evidence Minimum Schema (Per AGENTS.md §11)

| Section | Required |
|---|---|
| What Was Done | Yes |
| Files Changed | Yes |
| Validation Results (diagnostics, verifier output, pre-existing vs introduced) | Yes |
| Evidence Artifacts | Yes |
| Doc-Sync Impact | Yes (PROGRESS.md, CHECKLIST.md, StepPrompts.md) |
| Boundary Compliance | Yes (no drift/violation/overreach/Y6/HARD STOP bypass/distress suppression) |
| Rollback / Re-run Safety | Yes |
| Design Decisions / Caveats | Yes (spec conflict resolutions, deferred fields) |
| Auditor Gate | Yes (verdict + report path) |
| Footer | Yes (source task, date, implementer, validation) |

### 5.4 Verification Per Step

| Step | Verification | Expected |
|---|---|---|
| P2-010 | / in chat lists 33 commands | 33 commands in 7 categories |
| P2-011 | Embed renders correct colors | PRIMARY #6B21A8, ALERT #DC2626, etc. |
| P2-012 | /status returns embed | Fields per DiscordUXSpec §2.1, degraded for unavailable services |

---

## §6 Doc-Sync Requirements

### 6.1 Files to Update

| File | Update | Owner |
|---|---|---|
| PROGRESS.md | Mark P2-010..012 ✅, update 9/21 → 12/21 | Parent |
| CHECKLIST.md §4.2 | Check P2-010..012 items as verified | Parent |
| stepprompts/StepPrompts.md | Replace old snippets with canonical patterns | Implementation → Parent verify |
| docs/setup-evidence/P2/STEP-P2-0NN/verification.md | Create 3 evidence files | Implementation sub-agent |
| scripts/run-discord-verify.sh | Add new verifier scripts to allowlist (if needed) | Implementation sub-agent |

### 6.2 Shared Docs (Parent-Only)

docs/README.md — no update needed (no doc index changes). ADR-Index — no update needed (no new ADRs).

---

## §7 ADR References

### 7.1 Relevant ADRs

| ADR | Title | Risk | Relevance |
|---|---|---|---|
| **ADR-022** | Communication Channel Strategy | HIGH | Primary — Discord as main channel, slash commands, UX rules |
| **ADR-015** | Secrets Management Strategy | CRITICAL | Bot token must follow SOPS+age pattern |
| **ADR-014** | VPS & Container Architecture | HIGH | Service naming, isolation from Aizanta |
| **ADR-018** | Security Architecture & Defense-in-Depth | CRITICAL | Bot permission scope, token security, Faiz-only commands |
| **ADR-001** | Persona Safety & Ethical Boundary | CRITICAL | HARD STOP via /safeword (P2-015, but command structure in P2-010) |
| **ADR-002** | User Autonomy & Safe Word Enforcement | CRITICAL | Safe word global override |

### 7.2 ADR Constraints

| ADR | Constraint | Impact |
|---|---|---|
| ADR-022 §3 | Discord-only, no web UI | All 33 commands slash-only |
| ADR-022 §5 | Faiz-only command access | Permission checks in handler |
| ADR-015 §4 | SOPS + age only for secrets | Token via get_token(); never plaintext |
| ADR-018 §6 | No overprivileged tokens | Bot must not have ADMINISTRATOR long-term |
| ADR-002 §3 | Safe word supersedes all persona | /safeword triggers immediate neutral mode |

### 7.3 Not Relevant (18 ADRs)

ADR-004-006 (LLM routing), ADR-007-009 (memory), ADR-010 (surveillance retention), ADR-011-012 (SDLC loop), ADR-013 (MCP native), ADR-016 (CI/CD), ADR-017 (monitoring), ADR-019 (Tailscale), ADR-020 (browser), ADR-021 (wearable), ADR-023 (financial), ADR-024 (data governance), ADR-025 (backup/DR), ADR-026 (Cloudflare), ADR-027 (PostgreSQL), ADR-028 (superseded), ADR-029 (self-modification), ADR-030-032 (Redis/DB naming/backup storage).

---

## §8 Rollback & Destructive-Op Boundaries

### 8.1 Rollback Per Step

| Step | Rollback | Idempotent? |
|---|---|---|
| P2-010 | REST DELETE guild commands | Yes — re-run sync re-registers |
| P2-011 | Revert colors.py via git | Yes — stateless file |
| P2-012 | Revert cmd_status.py via git; remove command via REST | Yes — stateless handler |

### 8.2 Destructive-Op Boundaries

| Operation | Allowed? | Condition |
|---|---|---|
| m -rf / force push / DROP TABLE / production deploy | **NO** | Requires explicit operator approval per action |
| Git commit + push | YES | After step complete + auditor PASS |
| REST DELETE Discord commands | YES | Idempotent, reversible |
| Create/edit source files | YES | Standard implementation |

### 8.3 Re-run Safety

All three steps are safe to re-run — no stateful side effects beyond the guild command registry.

---

## §9 Compliance Matrix Summary

| Dimension | Status | Reference |
|---|---|---|
| Safety-affecting? | PARTIAL (credentials-adjacent only) | §1 |
| Requires Oracle review? | No | §1.1 |
| Token SOPS-only enforced? | MUST DO — blocking constraint | §4.2 |
| Aizanta verification needed? | No — code-only steps | §2 |
| Port/service changes? | None — read-only queries | §3 |
| Evidence paths defined? | docs/setup-evidence/P2/STEP-P2-0NN/verification.md | §5.1 |
| Auditor paths defined? | udit-reports/P2/STEP-P2-0NN/step-p2-0NN-auditor-report.md | §5.2 |
| Doc-sync required? | PROGRESS.md, CHECKLIST.md, StepPrompts.md | §6 |
| ADR constraints tracked? | ADR-022, ADR-015, ADR-018, ADR-001, ADR-002 | §7 |
| Rollback defined? | All steps stateless/idempotent | §8 |
| Destructive-op boundary? | No destructive ops needed | §8.2 |

---

## §10 Caveats

1. **/status field degradation**: 8 of 11 DiscordUXSpec fields depend on P3/P4/P5/P7 (not yet implemented). Planner must decide placeholder strategy.
2. **Closure bug**: StepPrompts @tree.command() decorator-in-loop pattern causes closure bugs — use discord.app_commands.Command objects or unctools.partial.
3. **Faiz-only enforcement**: Both specs agree all commands are Faiz-only, but implementation pattern (guild owner check vs permission check decorator vs role check) is not settled.
4. **REST vs Gateway**: REST API (PUT /applications/{id}/guilds/{guild_id}/commands) is consistent with existing src/discord/permissions.py patterns.

---

## §11 Footer

- **Source task:** TASK retry safety/evidence/ADR compliance research for P2-010..P2-012
- **Method:** Local read-only search of IMPLEMENTATION_GUIDE.md, ADR-Index, PROGRESS.md, CHECKLIST.md, AGENTS.md, and relevant ADR files
- **Dependencies:** p2-010-012-local-code-docs-report.md (spec conflicts) — this report fills only the compliance gap
- **Validation:** Parent-verified all file paths, cross-referenced ADR numbers, confirmed no circular/missing references
- **Secret handling:** No decrypted secrets used or recorded
- **Next action:** Parent reads this report → planner gate → collision scan → implementation wave
