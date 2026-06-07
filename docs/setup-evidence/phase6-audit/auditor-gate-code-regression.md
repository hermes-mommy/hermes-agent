# Auditor Gate — Code Quality & Regression (Domains 03, 08)

| Field | Value |
|---|---|
| Audit Type | Independent post-implementation auditor gate |
| ADR | ADR-035 v1.0 (Hermes Agent Integration via MCP) |
| Domains | 03 — Code Quality, 08 — Regression |
| Auditor | Independent Code Quality & Regression Specialist |
| Date | 2026-06-07 |
| Scope | Evidence verification + source code grep validation |

---

## Domain 03 — Code Quality

### Verdict: **NEEDS REVIEW**

### Issue Found: `# type: ignore` Location Misattribution

The evidence file claims:

> `# type: ignore` in Hermes plugin — **11 matches** — scope: `src/hermes/`

**This is factually incorrect.** Independent grep verification reveals:

| Scan Target | Evidence Claim | Actual Result | Match? |
|---|---|---|---|
| `# type: ignore` in `src/hermes/` | 11 matches | **0 matches** | ❌ **WRONG** |
| `# type: ignore` in `src/` (all) | 11 matches | **12 matches** (11 active + 1 deprecated) | ⚠️ Close but off-by-one |
| `as any` in `src/` | 0 matches | 0 matches | ✅ Verified |
| `@ts-ignore` in `src/` | 0 matches | 0 matches | ✅ Verified |
| `except Exception` in `src/hermes/` | "Multiple" | **20 matches** in 4 files | ✅ Claim directionally correct |

**Where `# type: ignore` actually lives** (12 total, 0 in `src/hermes/`):

| File | Count | Pre-ADR-035? |
|---|---|---|
| `src/observability/sentry_integration.py` | 5 | Yes |
| `src/mcp/auth.py` | 2 | Likely |
| `src/discord/_entrypoint.py` | 1 | Yes |
| `src/surveillance/timescale.py` | 1 | Yes |
| `src/core/main.py` | 1 | Yes |
| `src/mcp/tools/postgres_tool.py` | 1 | Likely |
| `src/_deprecated/hermes-migration-phase-7/bot.py` | 1 | Yes (deprecated) |

The VERIFICATION-SUMMARY also propagates this error:

> "11 `# type: ignore` (pre-existing); scope: `src/hermes/`"

**Root cause of misattribution:** The evidence file appears to have incorrectly attributed the workspace-wide count to `src/hermes/` specifically. The source report (`research-reports/phase6-audit/03-code-quality.md`) correctly lists the actual file locations — none are in `src/hermes/`.

### Additional Verification

- **`except Exception` in `src/hermes/`**: 20 matches across 4 files confirmed:
  - `src/hermes/safety_plugin.py` — 15 matches
  - `src/hermes/_memory_bridge.py` — 2 matches
  - `src/hermes/plugins/persona_plugin.py` — 2 matches
  - `src/hermes/_session_adapter.py` — 1 match
- **`pytest-asyncio` in `pyproject.toml`**: Confirmed absent (0 matches)
- **`[project.optional-dependencies] test`**: Contains only `pytest-cov>=7` — no async test dependencies

### Domain 03 Sub-Checklist

- [x] Evidence file exists and is well-formed
- [ ] Claims in evidence file match source report findings — **FAIL: location misattribution**
- [x] Source code evidence supports claims (greps run) — **partial: location wrong, count close**
- [ ] `# type: ignore` count of 11 is accurate for `src/hermes/` — **FAIL: 0 in hermes, 11 in active non-hermes**
- [x] `as any` and `@ts-ignore` zero counts are accurate
- [x] Classification as "pre-existing" is justified (none are in ADR-035 scope files)
- [x] CONDITIONAL verdict is justified (multiple code quality issues confirmed)

### Required Correction

The evidence file `docs/setup-evidence/phase6-audit/03-code-quality.md` must be amended:
1. Change scope from `src/hermes/` to `src/` (workspace-wide, excluding `_deprecated`)
2. Note that zero `# type: ignore` matches exist in `src/hermes/` specifically
3. Update VERIFICATION-SUMMARY.md accordingly

---

## Domain 08 — Regression

### Verdict: **PASS** (FAIL verdict on source report is justified)

### Verification Results

| Claim | Evidence File | Actual Result | Match? |
|---|---|---|---|
| `pytest-asyncio` absent from pyproject.toml | Yes | **Confirmed: 0 matches** | ✅ |
| `[project.optional-dependencies] test` only has `pytest-cov>=7` | Implicit | **Confirmed** | ✅ |
| Phase 7 tests: 139/139 green | Yes | Not independently re-run (read-only audit) | ⚠️ |
| Async suites fail on import | Yes | Not independently re-run (read-only audit) | ⚠️ |
| Classification as pre-existing gap | Yes | **Justified**: `pyproject.toml` shows no async test deps were ever declared | ✅ |

### Domain 08 Sub-Checklist

- [x] Evidence file exists and is well-formed
- [x] Claims in evidence file match source report findings
- [x] Source code evidence supports claims (`pytest-asyncio` confirmed absent)
- [x] `pytest-asyncio` absence from pyproject.toml is confirmed
- [x] Classification as "pre-existing" is justified (dependency was never declared)
- [x] FAIL verdict is justified (missing test dependency blocks async test execution)

### Notes

- The source report's test failure counts (28 hermes + 104 memory + 241 mcp + 148 persona + 148 surveillance = 669 total failures) could not be independently re-run in this read-only audit, but the root cause (`pytest-asyncio` missing) is verified against `pyproject.toml`.
- The PASS verdict here means the FAIL classification on the regression domain is **correctly reasoned** — the dependency gap is real and pre-existing.

---

## Overall Gate Verdict

### **CONDITIONAL PASS**

| Domain | Verdict | Gate Status |
|---|---|---|
| 03 — Code Quality | NEEDS REVIEW | ⚠️ Requires evidence correction |
| 08 — Regression | PASS | ✅ FAIL classification justified |

### Summary

**Domain 03** requires evidence file correction before it can pass this auditor gate. The `# type: ignore` count of 11 is approximately correct for active code across `src/`, but the scope attribution to `src/hermes/` is factually wrong — there are zero `# type: ignore` matches in `src/hermes/`. All 11 active matches are in other modules (observability, mcp, discord, surveillance, core). The "pre-existing" classification remains valid regardless.

**Domain 08** passes cleanly. The `pytest-asyncio` absence is verified, the FAIL verdict is justified, and the pre-existing classification is supported by the fact that the dependency was never declared in `pyproject.toml`.

### Action Required

1. **Correct** `docs/setup-evidence/phase6-audit/03-code-quality.md` — fix scope from `src/hermes/` to `src/` (active paths, excluding `_deprecated`)
2. **Correct** `docs/setup-evidence/phase6-audit/VERIFICATION-SUMMARY.md` — update the `# type: ignore` scope description
3. **Re-submit** Domain 03 for auditor gate after correction

---

## Audit Evidence — Raw Grep Results

### Grep 1: `# type: ignore` in `src/hermes/` (expecting 11)
```
Result: 0 matches (NO MATCHES FOUND)
```

### Grep 2: `# type: ignore` in `src/` (workspace-wide)
```
Result: 12 matches in 7 files
  src/observability/sentry_integration.py: 5 matches (lines 61, 91, 93, 111, 158)
  src/mcp/auth.py: 2 matches (lines 236, 237)
  src/_deprecated/hermes-migration-phase-7/bot.py: 1 match (line 33)
  src/surveillance/timescale.py: 1 match (line 128)
  src/mcp/tools/postgres_tool.py: 1 match (line 20)
  src/discord/_entrypoint.py: 1 match (line 40)
  src/core/main.py: 1 match (line 175)
Active (excluding _deprecated): 11 matches in 6 files
```

### Grep 3: `as any` in `src/`
```
Result: 0 matches (NO MATCHES FOUND)
```

### Grep 4: `@ts-ignore` in `src/` (.ts + .tsx)
```
Result: 0 matches (NO MATCHES FOUND)
```

### Grep 5: `pytest-asyncio` in `pyproject.toml`
```
Result: 0 matches (NO MATCHES FOUND)
Confirmed: pyproject.toml [project.optional-dependencies] test = ["pytest-cov>=7"]
```

### Grep 6: `except Exception` in `src/hermes/`
```
Result: 20 matches in 4 files
  src/hermes/safety_plugin.py: 15 matches (lines 344, 369, 384, 397, 410, 424, 441, 558, 601, 649, 678, 773, 864, 971, 1004)
  src/hermes/_memory_bridge.py: 2 matches (lines 159, 260)
  src/hermes/plugins/persona_plugin.py: 2 matches (lines 148, 180)
  src/hermes/_session_adapter.py: 1 match (line 241)
```

---

## Footer

| Field | Value |
|---|---|
| Auditor | Independent Code Quality & Regression Specialist |
| Date | 2026-06-07 |
| Gate Verdict | CONDITIONAL PASS |
| Next Action | Correct Domain 03 evidence file, re-submit |
| Audit Method | Read-only grep verification against source code |
