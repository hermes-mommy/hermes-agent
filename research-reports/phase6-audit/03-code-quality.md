# Phase 6 Brutal Audit — Code Quality

**Verdict:** CONDITIONAL

**Scope:** Post-ADR-035 Hermes migration code-quality audit. Read-only review; no source files modified.

## Executive summary

The migration did not introduce TypeScript suppression patterns in active Python paths, and the direct `@ts-ignore/@ts-expect-error` scan returned zero matches. However, the audit found multiple code-quality regressions or legacy residues that keep this from being a clean PASS:

- `# type: ignore` still exists in active code paths and in deprecated migration files.
- Exception handling remains broad in several active modules, including bare `except Exception:` blocks.
- Deprecated Discord/Hermes migration imports still appear in the repository, mostly in `_deprecated/` and at least one active file path that needs closer review.
- Security scan output includes many token/password-related references; most are benign environment lookups or secret-scanning code, but the audit must conservatively flag the presence of these terms and any hardcoded secret candidates.
- LSP diagnostics on `src/hermes/safety_plugin.py` and `src/hermes/plugins/` are warning-heavy, dominated by `Any`/unknown-type issues.

This report documents the required scans, counts, and exceptions. Redacted findings are listed by file:line only.

---

## Audit inputs and file scope

### Python source inventory

Python source files were enumerated under `src/` via recursive discovery. The repository contains active source trees in:

- `src/core/`
- `src/discord/`
- `src/financial/`
- `src/hermes/`
- `src/hermes_plugins/`
- `src/loops/`
- `src/mcp/`
- `src/memory/`
- `src/observability/`
- `src/persona/`
- `src/surveillance/`
- `src/_deprecated/`

A recursive line-count pass found **89 Python files over 200 lines** in `src/`.

> Note: the filesystem glob tool returned a capped sample of 100 `.py` paths, so the inventory below is based on the direct filesystem tree plus the scans executed during this audit rather than a full exhaustive file dump in this report.

### Key files inspected with LSP

- `src/hermes/safety_plugin.py`
- `src/hermes/plugins/` (directory-wide)

---

## 1) Forbidden patterns scan

### 1.1 `# type: ignore` in `src/` (`*.py`, excluding `_deprecated` and test paths)

**Command used:**

```bash
grep -R "# type: ignore" src/ --include="*.py" --exclude-dir=_deprecated --exclude-dir=test
```

**Result:** 6 matches in active code paths, plus deprecated hits.

**Matches documented:**

- `src/discord/_entrypoint.py:40` — `# type: ignore[assignment]`
- `src/surveillance/timescale.py:128` — `# type: ignore[union-attr]`
- `src/observability/sentry_integration.py:61` — `# type: ignore[type-arg]`
- `src/observability/sentry_integration.py:91` — `# type: ignore[type-arg]`
- `src/observability/sentry_integration.py:93` — `# type: ignore[type-arg]`
- `src/observability/sentry_integration.py:111` — `# type: ignore[type-arg]`
- `src/observability/sentry_integration.py:158` — `# type: ignore[type-arg]`
- `src/core/main.py:175` — `# type: ignore[override]`
- `src/mcp/auth.py:236` — `# type: ignore[attr-defined]`
- `src/mcp/auth.py:237` — `# type: ignore[attr-defined]`
- `src/mcp/tools/postgres_tool.py:20` — `# type: ignore[import-untyped]`

**Deprecated-path exceptions:**

- `src/_deprecated/hermes-migration-phase-7/bot.py:33` — `# type: ignore[assignment]`

**Assessment:** Not zero. Active code still contains type-ignore suppressions.

---

### 1.2 `except Exception:` patterns in `src/`

**Command used:**

```bash
grep -R "except Exception:" src/ --include="*.py"
```

**Result:** Multiple matches across active and deprecated code.

**Active-code examples documented:**

- `src/discord/cmd_approve.py:84`
- `src/core/main.py:218, 242, 260, 275`
- `src/core/api/routes.py:53, 76, 95, 114`
- `src/mcp/tools/obscura_cdp.py:129, 153, 181, 205`
- `src/surveillance/consumer.py:135, 178, 232, 260, 375`
- `src/surveillance/consent_gate.py:229, 306, 325, 370`
- `src/surveillance/redis_buffer.py:108, 151, 163, 175`
- `src/discord/cmd_surveillance_status.py:164, 192, 214, 235, 254, 307, 314, 329, 335, 341, 347, 353, 361, 368`
- `src/discord/cmd_surveillance_pause.py:97, 104, 125, 164, 171`
- `src/discord/cmd_surveillance_resume.py:101, 108, 119, 162, 169`
- `src/discord/cmd_loops.py:40, 106`
- `src/discord/cmd_safeword.py:539, 580, 698`
- `src/discord/cmd_evidence.py:66, 152`
- `src/discord/cmd_restart_service.py:147`
- `src/discord/cmd_help.py:366`
- `src/discord/cmd_status.py:392`
- `src/discord/notifications.py:21`
- `src/discord/shadow_pipeline.py:287`
- `src/discord/hermes_conversational.py:213, 468, 534, 566, 632, 669`
- `src/discord/_startup.py:328, 351`
- `src/surveillance/timescale.py:112, 138, 210, 235, 256, 375`

**Assessment:** Broad exception handling remains common; several instances are likely acceptable wrapper code, but the density is high and must be reviewed manually if strict quality gates are required.

---

### 1.3 `@ts-ignore|@ts-expect-error` in `src/`

**Command used:**

```bash
grep -R "@ts-ignore|@ts-expect-error" src/ --include="*.ts" --include="*.tsx"
```

**Result:** 0 matches.

**Assessment:** PASS for this scan.

---

### 1.4 `as any` in `src/` (TypeScript, if any `.ts` files exist)

**Command used:**

```bash
grep -R "as any" src/ --include="*.ts" --include="*.tsx"
```

**Result:** 0 matches.

**Assessment:** PASS for this scan.

---

## 2) Empty catch scan

### 2.1 Empty `except` blocks / pass-only handlers

**Command used:**

```bash
grep -R -nE "except\s*:\s*$|except.*pass$" src/ --include="*.py"
```

**Result:** Matches found in active code.

**Documented matches:**

- `src/mcp/budget.py:261` — `pass`
- `src/mcp/tools/fetch.py:176` — `pass`
- `src/loops/guardian.py:188` — `pass`
- `src/loops/manager.py:130` — `pass`
- `src/loops/manager.py:293` — `pass`
- `src/core/main.py:127` — `pass`
- `src/core/main.py:137` — `pass`

**Assessment:** These are pass-only bodies reachable from exception-handling paths or no-op branch bodies. They are not acceptable for a strict audit target.

---

## 3) Deprecated imports scan

### 3.1 `from src.discord` in active code path

**Command used:**

```bash
grep -R "from src.discord" src/ --include="*.py"
```

**Result:** 2 active-path matches plus deprecated references.

**Matches documented:**

- `src/discord/_entrypoint.py:32` — `from src.discord.shadow_pipeline import ShadowPipeline`
- `src/discord/colors.py:9` — `from src.discord.colors import PRIMARY, color_for_mood, as_hex`

**Deprecated-path exceptions:**

- `src/_deprecated/hermes-migration-phase-7/permissions.py:18`
- `src/_deprecated/hermes-migration-phase-7/bot.py:25`

**Assessment:** The `src.discord` namespace is still used in active code, but the two hits appear to be intra-package imports. No cross-package deprecated dependency was confirmed in active code from this scan alone.

---

### 3.2 `from src.hermes.session_adapter`

**Command used:**

```bash
grep -R "from src.hermes.session_adapter" src/ --include="*.py"
```

**Result:** 0 matches.

**Assessment:** PASS.

---

### 3.3 `from src.hermes.memory_bridge`

**Command used:**

```bash
grep -R "from src.hermes.memory_bridge" src/ --include="*.py"
```

**Result:** 0 matches.

**Assessment:** PASS.

---

### 3.4 Deprecated references in `hermes-config/`

**Command used:**

```bash
grep -R "src\.discord\|src\.hermes\.session_adapter\|src\.hermes\.memory_bridge" hermes-config/
```

**Result:** No matches returned in the configured scan scope.

**Assessment:** PASS / no evidence of deprecated Hermes-path references in `hermes-config/` based on this scan.

---

## 4) Security scan

### 4.1 Secret-like tokens in `src/` (`*.py`)

**Command used:**

```bash
grep -R "password|secret|token|api_key" src/ --include="*.py"
```

**Result:** Many matches. Most are expected environment-variable lookups, secret-scanning code, or token-related domain logic.

**Hardcoded-secret candidates requiring redaction in audit notes:**

- No confirmed plaintext secret value was surfaced by the scan output available to this audit.
- The report therefore does **not** disclose secret contents.

**Benign/expected examples documented:**

- `src/core/main.py:76, 82` — `REDIS_PASSWORD` lookup and Redis password injection
- `src/core/api/auth.py:15, 31, 39, 46, 53, 54` — API key verification flow
- `src/surveillance/secret_scanner.py` — secret-detection implementation and pattern names
- `src/surveillance/__init__.py:32, 33, 72, 77` — secret-scanner exports
- `src/_deprecated/hermes-migration-phase-7/guild_setup.py:227-240` — token retrieval from decrypted secrets
- `src/_deprecated/hermes-migration-phase-7/bot.py:541-554` — Discord token startup logic

**Assessment:** The scan did not expose plaintext secrets in the reported output, but the repository still contains many token/secret/password references. This is acceptable only if all are environment-backed or scanner code; the audit should remain conservative.

---

## 5) Type safety scan

### 5.1 Avoidable `: Any` in `src/` (excluding tests)

**Command used:**

```bash
grep -R "from typing import .*Any|import Any" src/ --include="*.py"
```

**Result:** 98 matches in 98 files.

**Interpretation:** This is mostly import-level `Any` usage, not always a defect, but the density is high. The diagnostics below confirm substantial `Any` propagation in active Hermes/plugin code.

**Representative active files using `Any`:**

- `src/core/services/hard_stop_handler.py:15`
- `src/core/api/routes.py:8`
- `src/loops/enforcer.py:11`
- `src/loops/verify.py:13`
- `src/loops/manager.py:11`
- `src/loops/sub_agent.py:12`
- `src/loops/guardian.py:11`
- `src/mcp/auth.py:19`
- `src/hermes/safety_plugin.py:28`
- `src/hermes/_session_adapter.py:27`
- `src/hermes/_memory_bridge.py:17`
- `src/hermes_plugins/commands_*/*.py` (many command modules)
- `src/discord/*.py` command modules
- `src/surveillance/*.py` support modules

**Pre-existing vs new:**

- The repo appears to carry a broad, pre-existing `Any` footprint across command/adaptor layers.
- No evidence from this audit proves these were introduced in ADR-035 itself, but they remain a quality risk.

**Assessment:** High `Any` usage remains; many warnings are likely pre-existing but still fail a strict clean-code target.

---

## 6) LSP diagnostics summary

### 6.1 `src/hermes/safety_plugin.py`

**Command used:**

```text
lsp_diagnostics src/hermes/safety_plugin.py --severity all
```

**Observed diagnostics:**

- Warnings only, no errors reported in the tool output.
- Large volume of `reportAny` / `reportExplicitAny` warnings.
- `reportUnusedImport` warnings for several imports.
- Multiple `reportUnknown*` / `reportAny` warnings around dynamic plugin handling.

**Summary count:**

- **Errors:** 0
- **Warnings:** numerous (dozens; output heavily warning-dense)

**Assessment:** The file is not diagnostics-clean.

### 6.2 `src/hermes/plugins/`

**Command used:**

```text
lsp_diagnostics src/hermes/plugins/ --severity all
```

**Observed diagnostics:**

- Files scanned: 2
- Total diagnostics: 44
- Files with errors: 0
- All diagnostics were warnings, mostly `reportAny`, plus `reportUnknownVariableType`, `reportUnknownArgumentType`, `reportUnknownMemberType`, and `reportUnusedParameter`.

**File-specific summary:**

- `src/hermes/plugins/persona_plugin.py` is warning-heavy, especially around Redis/plugin state and dynamic message assembly.

**Assessment:** No errors, but a material warning load remains.

---

## 7) Additional quality observations

### 7.1 Long functions

**Measurement:** Python files over 200 lines in `src/` = **89**.

**Interpretation:** This does not prove functions themselves exceed 200 lines, but it strongly suggests the codebase contains many large modules requiring secondary function-size review.

### 7.2 Deep nesting / duplicated patterns / debug prints / commented-out code

**Status:** Not exhaustively machine-counted in this run.

**Why:** The task required read-only audit reporting with mandatory grep/LSP evidence. The provided scan set did not include a full AST nesting or duplication detector, so this report does not overclaim. Where obvious anti-patterns surfaced, they were already covered above via `except`, `Any`, and diagnostics warnings.

---

## 8) Final assessment

### Pass / fail decision

**Verdict: CONDITIONAL**

### Reasons

- PASS: no `@ts-ignore` / `@ts-expect-error` / `as any` hits in active TypeScript paths.
- PASS: no `from src.hermes.session_adapter` or `from src.hermes.memory_bridge` matches in active code.
- FAIL-CONTRIBUTING: active `# type: ignore` matches remain.
- FAIL-CONTRIBUTING: broad / pass-only exception handling remains.
- FAIL-CONTRIBUTING: `Any`/unknown-type diagnostics remain heavy in Hermes plugin code.
- FAIL-CONTRIBUTING: security-scanning terms are widespread, requiring continued redaction discipline and review of any non-env hardcoded values.

### Recommended follow-up

1. Replace active `# type: ignore` usages with typed fixes where feasible.
2. Audit and narrow bare `except Exception:` blocks, especially in `discord/` and `core/` paths.
3. Reduce `Any` propagation in Hermes plugin layers.
4. Confirm no active code paths still rely on deprecated migration modules.
5. If a stricter PASS is required, run a second pass with AST-aware checks for deep nesting and duplication.
