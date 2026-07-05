# P23 Audit — Codex Fix P1-2 (AuthLevel Classifier)

> **Auditor:** independent  
> **Date:** 2026-06-25  
> **Scope:** READ-ONLY; no runtime code or deploy reviewed

---

## 1. Audit Scope

Verify that the Codex P1-2 finding — *"AuthLevel maps 1:1 to P23 L1-L4 risk tiers, allowing `shell_exec` at `READ_AUTO` to become P23 L1 autonomous despite `python`/`pip`/`git` being mutating"* — has been remediated in P23 planning documents.

Files reviewed:

- `src/mcp/auth.py`
- `src/mcp/tools/shell_tool.py`
- `src/mcp/auth_matrix.py`
- `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md`
- `docs/setup-evidence/P23/README.md`
- `docs/setup-evidence/P23/evidence/final-p23-planning-report.md`
- `docs/setup-evidence/P23/evidence/p23-definition-verification.md`

---

## 2. Ground-truth verification (`shell_tool` `READ_AUTO` + `python`/`pip`/`git`)

| # | Claim | Status | Evidence |
|---|---|---|---|
| 2.1 | `AuthLevel` enum exists with `READ_AUTO` | Confirmed | `src/mcp/auth.py:42-48` defines `READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`. |
| 2.2 | `shell_exec` decorated at `READ_AUTO` | Confirmed | `src/mcp/tools/shell_tool.py:350` `@require_approval(AuthLevel.READ_AUTO, tool_name="shell_exec")`. |
| 2.3 | `python`, `pip`, `git` in allowlist | Confirmed | `src/mcp/tools/shell_tool.py:43-45` lists `python`, `pip`, `git` in `ALLOWED_COMMANDS`. |
| 2.4 | `shell` → `READ_AUTO` in auth matrix | Confirmed | `src/mcp/auth_matrix.py:149-153` maps `"shell": { "*": AuthLevel.READ_AUTO, ... }`. |

The Codex P1-2 premise is grounded in code: a `READ_AUTO` shell tool can indeed run `python`, `pip`, or mutating `git` commands.

---

## 3. Fix verification

### 3.1 No 1:1 AuthLevel claims remain

Executed:

```bash
grep -rEn "maps 1:1|aliases AuthLevel|alias AuthLevel|aliasing AuthLevel|aliased to L1|1:1 to P23|1:1 to L1" \
  docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md \
  docs/setup-evidence/P23/README.md \
  docs/setup-evidence/P23/evidence/final-p23-planning-report.md \
  docs/setup-evidence/P23/evidence/p23-definition-verification.md
```

Result: 2 matches, both **negated** (i.e., explicitly stating AuthLevel is **NOT** 1:1 with L1-L4):

- `p23-embodied-operations-enterprise-plan.md:791` — *"AuthLevel mapped 1:1 to L1-L4"* appears inside the **hard-rejection criterion** (FAIL condition), not as a claim.
- `p23-embodied-operations-enterprise-plan.md:1126` — *"NOT aliased 1:1 to L1-L4 (Codex P1-2 fix)"*.

No affirmative 1:1 claims remain in the current-status P23 docs.

### 3.2 SemanticActionClassifier §22b exists with explicit `python`/`pip`/`git` rules

Executed:

```bash
grep -n "SemanticActionClassifier\|22b\|python.*pip.*git.*READ_AUTO\|READ_AUTO.*L1" \
  docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md
```

Findings:

- Section heading at `p23-embodied-operations-enterprise-plan.md:340`: `## 22b. Semantic Action Classifier (NEW — Codex P1-2 fix)`.
- `p23-embodied-operations-enterprise-plan.md:332-389` documents the classifier:
  - It takes `auth_level_hint` plus parsed intent/subcommand/target.
  - `auth_level_hint` alone **MUST NOT** determine tier.
  - `READ_AUTO` shell actions with `python`/`pip`/mutating-`git` **MUST** classify L2/L3, **never L1**.
  - Unit-test adversarial case: `shell_exec("python -c 'import os; os.remove(...)'")` at `READ_AUTO` must return L3/L4, not L1.

### 3.3 P23-002 wave scaffold forbids 1:1 mapping + shell `READ_AUTO` `python`/`pip`/`git` returning L1

Executed:

```bash
grep -n "Forbidden Patterns\|1:1\|READ_AUTO" \
  docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md | \
  grep -i "23-002\|forbidden\|1:1\|read_auto"
```

Findings in P23-002 scaffold (`p23-embodied-operations-enterprise-plan.md:822-826`):

- **Expected Files:** `risk_classifier.py` (`SemanticActionClassifier.classify(action, auth_level_hint) -> RiskTier` — §22b; AuthLevel is an INPUT, not 1:1).
- **Expected Files:** `tests/life_kernel/executors/test_risk_classifier.py` with adversarial cases for shell `python -c`/`pip install`/mutating `git` at `READ_AUTO` must classify L2/L3, not L1.
- **Forbidden Patterns:** "mapping AuthLevel 1:1 to RiskTier (MUST use semantic classifier §22b)".
- **Forbidden Patterns:** "shell `python`/`pip`/mutating-`git` at READ_AUTO returning L1 (Codex P1-2 hard-rejection)".
- **Hard Rejection Criteria:** repeat both prohibitions plus L4 not blocked, no D0-D4 freeze mapping, unknown/ambiguous action not defaulting to higher tier.

---

## 4. Hard-rejection check (shell `READ_AUTO` → L1 forbidden)

Searched all P23 docs for any remaining statement that `shell_exec` at `READ_AUTO` may become P23 L1 without semantic classification.

Executed:

```bash
grep -rni "shell.*READ_AUTO.*L1\|READ_AUTO.*shell.*L1\|shell_exec.*L1\|L1.*READ_AUTO" \
  docs/setup-evidence/P23/
```

Result: 8 files, 20 matches. All matches are **negated** (i.e., they state the rule or the mitigated risk). No document asserts that `shell_exec` `READ_AUTO` can legitimately map to P23 L1.

Key negative evidence:

- `p23-embodied-operations-enterprise-plan.md:7` — *"AuthLevel is an INPUT to P23 risk classification, NOT a 1:1 map to L1-L4"*.
- `p23-embodied-operations-enterprise-plan.md:383` — *"A `READ_AUTO` shell action with `python`/`pip`/mutating-`git` MUST classify L2/L3, never L1."*
- `p23-embodied-operations-enterprise-plan.md:791` — hard-rejection criterion: *"Action risk tiers are unclear, OR AuthLevel mapped 1:1 to L1-L4, OR shell READ_AUTO can become L1 without semantic classification to **FAIL**."*
- `p23-definition-verification.md:79` — hard-rejection #11 explicitly mitigated.
- `README.md:13` — same negated claim.
- `final-p23-planning-report.md:14,44` — same negated claim.

---

## 5. Verdict

**PASS**

- Ground truth confirmed: `src/mcp/auth.py:42-48`, `src/mcp/tools/shell_tool.py:43-45`, `src/mcp/tools/shell_tool.py:350`, and `src/mcp/auth_matrix.py:149-153` match the Codex P1-2 premise.
- No affirmative 1:1 AuthLevel-to-L1-L4 claims remain in the current P23 docs.
- `SemanticActionClassifier` §22b exists and explicitly requires that `READ_AUTO` shell `python`/`pip`/mutating-`git` classify L2/L3, never L1.
- P23-002 wave scaffold hard-rejects 1:1 mapping and shell `READ_AUTO` `python`/`pip`/`git` returning L1.
- No document asserts that `shell_exec` `READ_AUTO` can become P23 L1 without semantic classification.

The Codex P1-2 fix is adequately documented in planning. Implementation (P23-002) must still enforce these rules in code; this audit covers planning documents only.
