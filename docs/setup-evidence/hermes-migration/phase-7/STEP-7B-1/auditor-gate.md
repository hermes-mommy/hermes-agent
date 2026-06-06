# Step 7b.1 — Coverage Configuration — Auditor Gate

**Status:** PENDING — Not yet independently audited.

## Scope

- `.coveragerc` — coverage gating configuration
- `pyproject.toml` — optional dependencies and tool.coverage sections
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-1/verification.md`

## Checks Required

- [ ] `.coveragerc` `fail_under` is at least 80
- [ ] `.coveragerc` `source = src` is set
- [ ] `.coveragerc` omits `tests/*` and `src/_deprecated/*`
- [ ] `.coveragerc` has branch coverage enabled
- [ ] `pyproject.toml` has `pytest-cov>=7` in `[project.optional-dependencies] test`
- [ ] `pyproject.toml` has `[tool.coverage.run]` and `[tool.coverage.report]` sections
- [ ] `pyproject.toml` existing dependencies and pytest settings are preserved
- [ ] No TypeScript type suppressions or Python `# type: ignore` used
- [ ] No secrets, credentials, or sensitive data exposed
- [ ] Verification.md documents pre-existing failures honestly
- [ ] Coverage gating works correctly (fail_under enforced)
- [ ] No Phase 7 completion or ADR-035 IMPLEMENTED claimed

## Pre-existing Failures Noted

- Async test suite is skipped (missing pytest-asyncio event loop scope config)
- Full `--cov=src tests/` command exits non-zero due to 0% coverage (pre-existing)
- Test suite times out at 5+ minutes

## Verdict

_To be filled by independent auditor._

---

*This file is a pending auditor gate placeholder created during Step 7b.1 implementation. It must be independently audited before Step 7b.1 can be marked complete.*
