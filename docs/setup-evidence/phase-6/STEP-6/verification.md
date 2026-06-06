# STEP-6 Verification — Fallback Chain Configuration

## 1. What Was Done

Configured and parent-verified the Phase 6 fallback chain through the local 9Router endpoint only. Primary remains `ds/deepseek-v4-flash` via provider `ninerouter`; fallback chain has two 9Router-local entries: `cx/gpt-5.5` and `guinevere`. The invalid user-supplied `ninerouter/balance` model was explicitly verified absent and was not configured.

## 2. Files Changed

Local:

- `hermes-config/config.yaml`
- `docs/setup-evidence/phase-6/STEP-6/implementation-report.md`
- `docs/setup-evidence/phase-6/STEP-6/verification.md`

VPS:

- `/home/guinevere/.hermes/config.yaml`
- Backup: `/home/guinevere/.hermes/config.yaml.phase6-step6-bak`

## 3. Validation Results

VPS 9Router model check:

- `/v1/models` HTTP status: 200.
- `ds/deepseek-v4-flash`: present.
- `cx/gpt-5.5`: present.
- `guinevere`: present.
- `ninerouter/balance`: absent.

Local config validation:

- `model.provider`: `ninerouter`.
- `model.base_url`: `http://localhost:20128/v1`.
- `model.model`: `ds/deepseek-v4-flash`.
- `fallback_providers`: two entries: `cx/gpt-5.5`, `guinevere`, both with `base_url: http://localhost:20128/v1` and `key_env: NINEROUTER_API_KEY`.

VPS Hermes validation:

- `hermes config check` passed with config version 24.
- `hermes fallback list` reports primary `ds/deepseek-v4-flash` via `ninerouter` and fallback chain:
  1. `cx/gpt-5.5` via `custom` at `http://localhost:20128/v1`
  2. `guinevere` via `custom` at `http://localhost:20128/v1`
- Budget hook remains first pre-tool hook: priority 100, block.
- Consent gate remains second pre-tool hook: priority 90, block.
- DNR hook remains post-tool hook: priority 70, block.

Forbidden endpoint/model checks:

- No `api.openai.com`, `openrouter.ai`, `api.anthropic.com`, or `ninerouter/balance` appears in local `hermes-config/config.yaml`.

## 4. Evidence Artifacts

- Implementation report: `docs/setup-evidence/phase-6/STEP-6/implementation-report.md`
- Local config: `hermes-config/config.yaml`
- VPS config backup: `/home/guinevere/.hermes/config.yaml.phase6-step6-bak`
- This verification file: `docs/setup-evidence/phase-6/STEP-6/verification.md`

## 5. Doc-Sync Impact

No ADR/governance docs changed. Evidence explicitly records the current-user override of `ninerouter/balance`: it is invalid/absent and not configured; `guinevere` is the operational 9Router combo fallback.

## 6. Boundary Compliance

- All LLM traffic remains via 9Router at `http://localhost:20128/v1`.
- No direct provider URLs were introduced.
- No provider secrets or env values were printed or written.
- Budget, consent, and DNR hooks were preserved.
- `hermes-gateway` was not restarted in this step.

## 7. Rollback / Re-run Safety

Local rollback before commit: `git checkout -- hermes-config/config.yaml`.

VPS rollback: restore `/home/guinevere/.hermes/config.yaml.phase6-step6-bak` to `/home/guinevere/.hermes/config.yaml` and then perform a controlled service restart.

## 8. Design Decisions / Caveats

`cx/gpt-5.5` is present but known degraded due expired Codex OAuth credentials. It remains configured as first fallback so the chain can recover automatically after credentials are refreshed; Hermes is expected to continue to `guinevere` when `cx/gpt-5.5` fails with 401/404. `guinevere` is the operational VPS combo and the second fallback.

## 9. Auditor Gate

Pending. Step 12 routing auditor must verify the fallback chain and the deliberate exclusion of invalid `ninerouter/balance`.

## 10. Security Scan

No direct provider endpoints or secret values were added to local config. Evidence uses only model IDs and env-var names.

## 11. Acceptance Criteria Mapping

- Primary DeepSeek via 9Router: PASS.
- Two fallbacks configured: PASS.
- All fallbacks through 9Router localhost: PASS.
- Invalid `ninerouter/balance` excluded with proof: PASS.
- Budget/consent/DNR hooks preserved: PASS.

## 12. Footer

Generated 2026-06-06 for Phase 6 fallback-chain evidence. Parent verified local and VPS state directly after subagent configuration.
