# ADR-028 Skip Ollama Evidence

## What Was Done

ADR-028 was updated from **Accepted** to **Superseded** per Faiz directive on 2026-06-01. Ollama local fallback is intentionally not implemented for P1.

The superseding runtime decision is based on the completed 9Router migration and the dedicated `guinevere` combo routing:

1. Primary: `opencode-go/deepseek-v4-flash`
2. Secondary: `openai-compatible-chat-d2069ce0-65f4-4191-b91f-9065118c7a0e/gpt-5.5` via `cockpit` over Tailscale
3. Final fallback: graceful degradation

Ollama is not required because DeepSeek V4 Flash is already available as a low-cost primary route.

## Files Changed

- `adr/ADR-028-llm-router-outage-graceful-degradation.md`
  - Status changed to `Superseded`.
  - Decision updated: Ollama local fallback is not implemented.
  - Superseded-by pointer added: `migration-9router decisions (2026-06-01)`.
  - Runtime chain updated to DeepSeek primary, cockpit GPT-5.5 secondary, graceful degradation fallback.

- `docs/10-governance/17-ADR_Index_v1.0.md`
  - ADR-028 status changed to `Superseded`.
  - Status summary updated from Accepted 18 to Accepted 17 + Superseded 1.

- `stepprompts/StepPrompts.md`
  - P1-012 marked `SKIPPED`.
  - P1-013 marked `SKIPPED`.
  - P1-014 marked `SKIPPED`.
  - Install/pull/test command blocks replaced with no-op skip instructions.
  - P1 transition checklist, P1-015 fallback comments, P1-019 health checks, P1-020 cost seed, P3 embedding troubleshooting, phase checklist, and service table were cleaned so no material local Ollama fallback instructions remain.
  - Note added: skipped per Faiz directive 2026-06-01.

- `PROGRESS.md`
  - P1 count updated from `11/21` to `14/21`.
  - Header completed count updated from `40/257 (15.6%)` to `43/257 (16.7%)`.
  - Total row updated to `43/257`.
  - P1-012/P1-013/P1-014 marked complete as skipped decisions.

- `CHECKLIST.md`
  - P1-012/P1-013/P1-014 marked skipped.
  - Ollama fallback integration check replaced with graceful-degradation final fallback note.

- `docs/setup-evidence/P1/STEP-P1-005/config.yaml`
  - `llm.fallback.provider` changed from `ollama` to `graceful_degradation`.
  - Ollama model/base URL removed.
  - Supersession reason and active route notes added.

- `tmp/hermes-config-y4.yaml`
  - Local deployment source copy updated with the same fallback disablement.

- `tmp/hermes-config.yaml`
  - Older local temp config normalized to Y4 and graceful degradation fallback to avoid stale Ollama copy-paste.

- `docs/IMPLEMENTATION_GUIDE.md`
  - LLM troubleshooting updated from stale port `8080` / Ollama fallback to 9Router `20128` / model `guinevere` / graceful degradation.
  - Cost strategy updated to DeepSeek primary, GPT-5.5 cockpit secondary, and graceful degradation with no local port.

## Validation Results

Completed validation checks:

- ✅ No executable Ollama install/pull/test commands remain in P1-012/P1-013/P1-014.
- ✅ ADR-028 frontmatter and Status section are `Superseded`.
- ✅ ADR Index records ADR-028 as `Superseded`.
- ✅ PROGRESS count is P1 `14/21` and total `43/257`.
- ✅ Hermes config YAML parses after disabling Ollama fallback.
- ✅ VPS `/home/guinevere/config/hermes/config.yaml` is updated: `llm.fallback.provider=graceful_degradation`, `enabled=False`.
- ✅ StepPrompts fallback examples no longer reference `provider: "ollama"`, `localhost:11434`, Ollama install/pull/service commands, or local Ollama fallback requirements.
- ✅ `docs/IMPLEMENTATION_GUIDE.md` LLM troubleshooting now uses 9Router port `20128` and model `guinevere`, with graceful degradation note.
- ✅ `docs/IMPLEMENTATION_GUIDE.md` cost strategy no longer recommends Ollama fallback when 9Router is down.
- ✅ Auditor initial verdict was NEEDS REVIEW; F1/F2/F3 findings were fixed and re-audited.

## Evidence Artifacts

- Decision evidence: `docs/setup-evidence/P1/adr-028-skip-ollama.md`
- 9Router migration evidence: `docs/setup-evidence/P1/migration-9router/evidence.md`
- Guinevere combo auditor: `audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md`

## Doc-Sync Impact

- ADR Index synced.
- StepPrompts synced.
- PROGRESS synced.
- CHECKLIST synced.

No new ADR number was created because Faiz explicitly requested updating ADR-028 status to Superseded and marking the implementation steps skipped.

## Boundary Compliance

- No secrets, API keys, JWTs, or provider credentials are recorded in this evidence.
- No new network exposure is introduced.
- No Aizanta resources are touched.
- No persona safety boundary is weakened.
- No HARD STOP, distress protocol, consent, or yandere ceiling behavior is changed.

## Rollback / Re-run Safety

Rollback would require a new Faiz directive to restore Ollama as a fallback. If that happens, create a new superseding decision before installing Ollama, pulling model artifacts, or adding `guinevere-ollama.service`.

This documentation change is safe to re-run because it only updates static project documents and Hermes config fallback metadata.

## Design Decisions / Caveats

- DeepSeek V4 Flash via `opencode-go` is the primary low-cost route.
- GPT-5.5 via `cockpit` is secondary and depends on laptop/Tailscale cockpit availability.
- Graceful degradation is the terminal fallback when routing is unavailable.
- Full offline local inference is intentionally deferred.

## Auditor Gate

Initial auditor verdict was **NEEDS REVIEW** with three findings:

1. `PROGRESS.md` header count still showed `40/257`.
2. `stepprompts/StepPrompts.md` had stale material Ollama fallback references outside P1-012/P1-013/P1-014.
3. `docs/IMPLEMENTATION_GUIDE.md` still recommended Ollama fallback in the cost strategy.

All findings were fixed before re-audit. Auditor report path:

`audit-reports/P1/adr-028-skip-ollama-auditor-report.md`

## Footer

- Source task: Faiz directive to update ADR-028 and skip Ollama P1-012/P1-013/P1-014
- Date: 2026-06-01
- Implementer: Hephaestus / Guinevere
- Validation method: file diff review, grep checks, YAML parse, VPS config sync, auditor gate
