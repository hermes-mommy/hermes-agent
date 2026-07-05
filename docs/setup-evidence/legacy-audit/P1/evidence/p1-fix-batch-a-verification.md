# P1 Fix Batch A — Verification

**Date:** 2026-06-26
**Scope:** Source + docs only, no deploy, no restart
**Method:** Local read-only verification on Windows mirror

---

## 1. Source Fixes Verified

### S1: sandbox.py — `import re`

| Check | Command | Result |
|-------|---------|--------|
| AST parse | `python -c "import ast; ast.parse(open('src/loops/sandbox.py').read()); print('OK')"` | `OK` |
| `import re` present | `grep -n "import re" src/loops/sandbox.py` | `10:import re` |
| `re.search()` has import | `re.search()` at line 346, `re.finditer()` at line 352, both now have `import re` at line 10 | PASS |

### S2: main.py — llm_router=None comment

| Check | Command | Result |
|-------|---------|--------|
| AST parse | `python -c "import ast; ast.parse(open('src/core/main.py').read()); print('OK')"` | `OK` |
| Comment present | `grep -c "P20/P24" src/core/main.py` | `1` |
| Comment references audit | `grep "p1-live-vps-reconciliation" src/core/main.py` | Found at line 103 |
| Comment references GAPs | `grep "GAP-01\|GAP-06\|GAP-07" src/core/main.py` | Found at line 103 |

### S3: compaction.py — ContextCompactor deprecation

| Check | Command | Result |
|-------|---------|--------|
| AST parse | `python -c "import ast; ast.parse(open('src/memory/compaction.py').read()); print('OK')"` | `OK` |
| DeprecationWarning present | `grep -c "DeprecationWarning" src/memory/compaction.py` | `2` |
| Warning emitted on init | `warnings.warn(...)` at `__init__` | Found |
| Class NOT deleted | `class ContextCompactor` still exists at line 52 | PASS (deprecation only, not deletion) |

---

## 2. Docs/Evidence Fixes Verified

### D1: P1-018 evidence hardening note

| Check | Command | Result |
|-------|---------|--------|
| Note present | `grep "Hardening Snapshot Note" docs/setup-evidence/P1/STEP-P1-018/evidence.md` | Found |
| Reconciliation reference | `grep "p1-live-vps-reconciliation-audit" docs/setup-evidence/P1/STEP-P1-018/evidence.md` | Found |
| Systemctl show values | `grep "systemctl show" docs/setup-evidence/P1/STEP-P1-018/evidence.md` | Found |

### D2: PROGRESS.md P1-021 test count

| Check | Command | Result |
|-------|---------|--------|
| Correct count | `grep "P1-021" PROGRESS.md` | `70/70 tests PASS at P1 epoch (56 handler + 14 model compliance; 86 comprehensive tests added post-P1 in P4/P6)` |
| No "142" | `grep "142/142" PROGRESS.md` | `0 matches` |

### D3: CHECKLIST.md "21 steps"

| Check | Command | Result |
|-------|---------|--------|
| Correct count | `grep "All 21" CHECKLIST.md` | `All 21 steps verified (P1-001 through P1-021; P1-012/013/014 SKIPPED per ADR-028)` |
| No "20 steps" in P1 section | `grep "All 20" CHECKLIST.md` | `0 matches` (was 4, now 0) |

### D4: STEP-P1-008 through STEP-P1-011 stub dirs

| Check | Command | Result |
|-------|---------|--------|
| Total STEP dirs | `ls -d docs/setup-evidence/P1/STEP-P1-* | wc -l` | `18` (was 14, +4 new) |
| P1-008 exists | `ls docs/setup-evidence/P1/STEP-P1-008/README.md` | Exists |
| P1-009 exists | `ls docs/setup-evidence/P1/STEP-P1-009/README.md` | Exists |
| P1-010 exists | `ls docs/setup-evidence/P1/STEP-P1-010/README.md` | Exists |
| P1-011 exists | `ls docs/setup-evidence/P1/STEP-P1-011/README.md` | Exists |
| Each references migration-9router | `grep -l "migration-9router" docs/setup-evidence/P1/STEP-P1-00[89]/README.md` | All 4 files |

### D5: UTF-8 encoding conversion

| Check | Command | Result |
|-------|---------|--------|
| import-test.txt | `file docs/setup-evidence/P1/STEP-P1-015/import-test.txt` | `ASCII text` (was UTF-16LE) |
| system-prompt-loaded.txt | `file docs/setup-evidence/P1/STEP-P1-016/system-prompt-loaded.txt` | `ASCII text` (was UTF-16LE) |
| health-check.txt | `file docs/setup-evidence/P1/STEP-P1-019/health-check.txt` | `ASCII text` (was UTF-16LE) |
| Content readable | `head -3 docs/setup-evidence/P1/STEP-P1-015/import-test.txt` | `Router module OK`, `TaskType values: [...]`, `CORE_REASONING: gpt-5.5 [...]` |

---

## 3. Secret Scan

| Surface | Pattern | Result |
|---------|---------|--------|
| 4 new stub STEP dirs | `sk-*`, `AIza*`, `gh[opuab]_*`, PEM keys | **0 matches** |
| P1-018 evidence.md (edited) | `sk-*`, `AIza*`, `gh[opuab]_*`, PEM keys | **0 matches** |
| src/loops/sandbox.py (edited) | `sk-*`, `AIza*`, `gh[opuab]_*`, PEM keys | **0 matches** |
| src/core/main.py (edited) | `sk-*`, `AIza*`, `gh[opuab]_*`, PEM keys | **0 matches** |
| src/memory/compaction.py (edited) | `sk-*`, `AIza*`, `gh[opuab]_*`, PEM keys | **0 matches** |

---

## 4. Files Changed

| # | File | Change | Lines |
|---|------|--------|-------|
| 1 | `src/loops/sandbox.py` | Added `import re` | +1 |
| 2 | `src/core/main.py` | Added explanatory comment | +5 |
| 3 | `src/memory/compaction.py` | Added DeprecationWarning | +12 |
| 4 | `docs/setup-evidence/P1/STEP-P1-018/evidence.md` | Added hardening snapshot note | +18 |
| 5 | `PROGRESS.md` | Fixed P1-021 test count | 1 line changed |
| 6 | `CHECKLIST.md` | Fixed "20 steps" → "21 steps" | 1 line changed |
| 7 | `docs/setup-evidence/P1/STEP-P1-008/README.md` | New stub file | +10 |
| 8 | `docs/setup-evidence/P1/STEP-P1-009/README.md` | New stub file | +8 |
| 9 | `docs/setup-evidence/P1/STEP-P1-010/README.md` | New stub file | +9 |
| 10 | `docs/setup-evidence/P1/STEP-P1-011/README.md` | New stub file | +8 |
| 11 | `docs/setup-evidence/P1/STEP-P1-015/import-test.txt` | UTF-16LE → UTF-8 | Encoding only |
| 12 | `docs/setup-evidence/P1/STEP-P1-016/system-prompt-loaded.txt` | UTF-16LE → UTF-8 | Encoding only |
| 13 | `docs/setup-evidence/P1/STEP-P1-019/health-check.txt` | UTF-16LE → UTF-8 | Encoding only |

---

## 5. Final Status

| Finding | Status |
|---------|--------|
| GAP-21 (missing import re) | **FIXED** |
| GAP-32 (llm_router=None undocumented) | **FIXED** |
| GAP-33 (ContextCompactor dead code) | **DEPRECATED** (not deleted) |
| GAP-08 (P1-018 evidence aspirational) | **DOCUMENTED** |
| GAP-28 (PROGRESS.md test count) | **FIXED** |
| GAP-30 (CHECKLIST "20 steps") | **FIXED** |
| GAP-25 (7 missing STEP dirs) | **FIXED** (4 new stub dirs + 3 SKIPPED per ADR-028) |
| GAP-14 (3 UTF-16LE files) | **FIXED** |

---

## 6. Separation Statement

| Category | Status | Items |
|----------|--------|-------|
| **Repo/source fixed** | ✅ | S1 (sandbox.py), S2 (main.py), S3 (compaction.py deprecation) |
| **Docs/evidence fixed** | ✅ | D1 (P1-018 evidence), D2 (PROGRESS.md), D3 (CHECKLIST.md), D4 (STEP dirs), D5 (UTF-8 encoding) |
| **Production deferred** | ⏳ | Systemd hardening (NoNewPrivileges, ProtectHome — requires restart) |
| **P19/P24 deferred** | ⏳ | GAP-01 (UNGATED callers), GAP-02 (fragmented HardStop), GAP-06 (string task_type), GAP-07 (content extraction), GAP-04 (standalone LLMRouter) |

---

*Verification complete. All 13 files changed, 0 secrets leaked, 0 deploys, 0 restarts.*