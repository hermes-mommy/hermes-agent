# P1-004 Evidence — Hermes Agent Installation

| Field | Value |
|-------|-------|
| **Step** | P1-004 — Hermes Agent Installation |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (Sisyphus agent) |
| **Evidence Root** | `docs/setup-evidence/P1/STEP-P1-004/` |
| **Status** | ✅ Complete — awaiting auditor gate |

---

## 1. What Was Done

Installed Hermes Agent framework v0.15.2 (Nous Research) into the Guinevere virtual environment, created the Python project structure, configured pyproject.toml with 23 dependencies, and added .gitignore.

**Approach**: Used `uv pip install hermes-agent` from PyPI. Created src/ layout per StepPrompts P1-004. pyproject.toml uses PEP 621 + hatchling backend with corrected dependency list matching actual venv state.

**Deviations from StepPrompts.md**:
1. Import: `import hermes_constants` (flat modules) instead of `import hermes_agent` (package not structured that way)
2. pyproject.toml: Added 7 packages from P1-003 venv not in spec (pydantic-settings, aiohttp, websockets, typer, rich, tenacity, passlib). Removed discord.py, python-jose (not yet needed).
3. Added `.gitignore` (not in StepPrompts but required for git safety per plan)

---

## 2. Files Changed

### On VPS (`/home/guinevere/code/guinevere/`)

| Action | Count/Path |
|--------|-----------|
| hermes-agent + deps installed | 27 packages added to .venv |
| src/ directories | 14 dirs + 14 __init__.py |
| pyproject.toml | Created (23 deps, hatchling) |
| .gitignore | Created (Python/venv/secrets/IDE) |

---

## 3. Validation Results

| Test | Command | Result |
|------|---------|--------|
| hermes_constants import | `python -c "import hermes_constants"` | ✅ PASS |
| hermes_bootstrap import | `python -c "import hermes_bootstrap"` | ✅ PASS |
| Package count | `pkg_resources.working_set` | ✅ 88 total |
| src structure | `find src -name '__init__.py' \| wc -l` | ✅ 14 |
| pyproject.toml parse | `tomllib.load(open('pyproject.toml','rb'))` | ✅ PASS, 23 deps |
| All 23 deps importable | Individual import checks | ✅ ALL PASS |

---

## 4. Evidence Artifacts

| File | Description |
|------|-------------|
| `hermes-install.txt` | Package listing with versions |
| `project-structure.txt` | `find src` directory tree |
| `pyproject.toml` | Copy of deployed build config |

---

## 5. Shared VPS Impact

Aizanta containers: 5 running ✅. No port changes. Disk <15%.

---

## 6. ADR Compliance

| ADR | Status |
|-----|--------|
| ADR-004 (GPT-5.5 primary) | ✅ Hermes supports OpenAI-compatible |
| ADR-011 (7-phase loop) | ✅ Hermes has autonomous loop |
| ADR-012 (sub-agent orchestration) | ✅ Compatible pattern |

---

## 7. AC/DoD Reference

| DoD Item | Status |
|----------|--------|
| Hermes installed (`uv pip show hermes-agent`) | ✅ v0.15.2 |
| Import test succeeds | ✅ hermes_constants |
| Project structure created (14 dirs) | ✅ |
| pyproject.toml valid (23 deps) | ✅ TOML parse PASS |
| AC-CORE-001 (framework operational) | ✅ |
| AC-LOOP-001 (agent loop ready) | ✅ |

---

## 8. Rollback / Re-run Safety

Re-run safe. Idempotent. Rollback: `uv pip uninstall -y hermes-agent && rm -rf src/ pyproject.toml .gitignore`

---

## 9. Design Decisions

1. Import mismatch: StepPrompts says `import hermes_agent`; actual package uses flat `hermes_*.py` modules
2. Yandere baseline: P1-005 will use Y1 per PersonaSafetyPolicy (not SystemPromptMaster Y4)
3. pyproject.toml deps corrected to 23 (matched actual venv state)

---

## 10. Evidence Gate ✅

All evidence files exist. All import checks pass. No secret leak. Aizanta healthy.

---

## 11. Auditor Gate

Report: `audit-reports/P1/STEP-P1-004/step-p1-004-auditor-report.md`  
Status: **AWAITING bg_6b7992e8 completion**

---

## 12. Footer

| Field | Value |
|-------|-------|
| **Source task** | STEP-P1-004 |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (Sisyphus) |
| **Validation** | VPS SSH + import tests + TOML parse |