# STEP-5 Verification — Budget Hook Registration and VPS Deploy

## 1. What Was Done

Registered the Phase 6 budget shell hook locally and on the VPS. The budget hook now runs before consent gate in `hooks.pre_tool_call` with priority 100, timeout 500ms, and `on_failure: block`. Deployed/verified hook files under VPS `~/.hermes/hooks/` and preserved existing consent/DNR hooks.

## 2. Files Changed

Local:

- `hermes-config/config.yaml`
- `docs/setup-evidence/phase-6/STEP-5/implementation-report.md`
- `docs/setup-evidence/phase-6/STEP-5/verification.md`

VPS:

- `/home/guinevere/.hermes/config.yaml`
- `/home/guinevere/.hermes/hooks/budget_check.py`
- Backup: `/home/guinevere/.hermes/config.yaml.pre-phase6-20260606-041313`

## 3. Validation Results

Local YAML validation:

- `hooks.pre_tool_call` length: 2.
- First pre-tool hook: `python3 ~/.hermes/hooks/budget_check.py`, timeout 500, `on_failure: block`, priority 100.
- Second pre-tool hook: `python3 ~/.hermes/hooks/consent_gate.py`, priority 90.
- DNR post-tool hook preserved.

VPS validation:

- VPS YAML parse succeeded.
- VPS pre-tool hook order: budget priority 100, consent priority 90.
- VPS DNR post-tool hook preserved at priority 70.
- VPS hook files exist: `budget_check.py`, `budget_lua.py`, `budget_lua_extended.py`, `_hook_utils.py`.
- VPS `python3 -m py_compile` succeeded for all four hook files.
- VPS config backup exists: `config.yaml.pre-phase6-20260606-041313`.

## 4. Evidence Artifacts

- Implementation report: `docs/setup-evidence/phase-6/STEP-5/implementation-report.md`
- Local config: `hermes-config/config.yaml`
- VPS backup: `/home/guinevere/.hermes/config.yaml.pre-phase6-20260606-041313`
- This verification file: `docs/setup-evidence/phase-6/STEP-5/verification.md`

## 5. Doc-Sync Impact

No governance or ADR docs changed. `hermes-config/config.yaml` now matches the Phase 6 runtime budget-hook registration plan.

## 6. Boundary Compliance

- No secrets, API keys, Redis passwords, Discord tokens, or env values were printed or written.
- Existing `consent_gate.py` hook remains present and fail-closed.
- Existing `dnr_filter.py` hook remains present and fail-closed.
- `plugins.enabled` was not modified.
- `src/hermes/plugins/budget_hook.py` was not created.
- `hermes-gateway` was not restarted in this step; restart is the next runtime gate.

## 7. Rollback / Re-run Safety

Local rollback before commit: `git checkout -- hermes-config/config.yaml`.

VPS rollback: `cp ~/.hermes/config.yaml.pre-phase6-20260606-041313 ~/.hermes/config.yaml` followed by a controlled `hermes-gateway` restart.

Re-run caveat: duplicate insertion must be avoided; verify no existing `budget_check.py` hook before re-running insertion scripts.

## 8. Design Decisions / Caveats

The VPS YAML dumper reordered hook-entry keys but preserved all semantic values. This is acceptable because parent verification confirmed command, event, timeout, `on_failure`, and priority values.

## 9. Auditor Gate

Pending. Step 12 cost and ADR auditors must verify the local/VPS config registration evidence after runtime tests.

## 10. Security Scan

No sensitive values were included in evidence. Commands validated structure and env-var names only.

## 11. Acceptance Criteria Mapping

- Budget hook active in config: PASS.
- Fail-closed on hook failure (`on_failure: block`): PASS.
- Priority before consent gate: PASS.
- Consent/DNR preserved: PASS.
- Hook files deployed and compile on VPS: PASS.
- VPS backup exists: PASS.

## 12. Footer

Generated 2026-06-06 for Phase 6 budget-hook registration evidence. Parent verified local and VPS state directly after subagent deployment.
