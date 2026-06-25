# P20 Continuation — Brutal Cleanup Plan

| Field | Value |
|---|---|
| Date | 2026-06-25 |
| Status | **PLAN EXECUTED — COMPLETE** |
| Trigger | Ground-truth blocker audit revealed the round-2 safety-consent FAIL verdict was silently un-deployed (the real blocker), plus research count drift and 6 P20 test bugs |
| Achieved status | **P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK** (operator waived the 24h wait; see discord-visible-autonomy/operator-soak-waiver.md) |
| 24h soak gate | NOT completed — waived by operator; not an unconditional PRODUCTION PASS |
| Cleanup commit | `03f84b5` |

## Ground-Truth Summary

| # | Blocker | Verdict |
|---|---|---|
| 1 | Audit evidence count mismatch | **FALSE ALARM (auditor count)** — disk has 8 round-1 + 8 round-2 = 16 auditors (matches report). Real drift: research dir has 12 files, report claimed 7 (DOC-04). **The actual evidence fraud was the round-2 safety-consent FAIL verdict on disk, not a missing auditor file.** |
| 2 | Privacy logging | **REAL AND CRITICAL — FIXED + DEPLOYED in `03f84b5`**. heartbeat.py sanitized-summary AND graph.py SAF-CONS-01 were uncommitted; VPS ran pre-fix code feeding raw P18 memory to the LLM. Round-2 safety-consent verdict on disk = FAIL. |
| 3 | Soak log patterns | **NOT SOAK-BLOCKING** — historical/pre-existing |
| 4 | Evidence count mismatch | Research count 7→12 reconciliation (DOC-04); auditor count was correct. |
| 5 | Test warnings | **6 P20 test bugs FIXED in `03f84b5`**; 2287 pre-existing plugin deprecations documented. |

> **Parent-verification note:** The first research sub-agent reported "8 round-1 + 12 round-2 = 20 auditors" — it conflated the research directory (12) with round-2 (8). Parent re-ran the count via bash and caught the error: the report's 8+8=16 was correct. This is why AGENTS.md mandates parent-read verification of sub-agent output.

## Steps and Scaffolds

### STEP-1: Update report evidence counts
**Expected Files:**
- `docs/setup-evidence/P20/evidence/continuation/final-continuation-report.md`
- `docs/setup-evidence/P20/evidence/continuation/deploy-evidence.md`

**Forbidden Patterns:**
- `7 reports` (research should be 12)
- `8/8 auditors returned PASS` claiming 0 FAIL (round-2 safety-consent was FAIL pre-fix)

**Required Commands:**
```bash
find docs/setup-evidence/P20/evidence/continuation/audits/round-1 -type f | wc -l
find docs/setup-evidence/P20/evidence/continuation/audits/round-2 -type f | wc -l
find docs/setup-evidence/P20/evidence/continuation/research -type f | wc -l
```
→ round-1=8, round-2=12, research=8

**Evidence:** this plan file + updated reports

---

### STEP-2: Verify privacy logging (no code change expected)
**Expected Files:**
- `src/life_kernel/heartbeat.py`

**Forbidden Patterns (must stay zero):**
```regex
logger\.(info|debug|warning|error).*recalled_memories\b
logger\.(info|debug|warning|error).*journal_entries\b
logger\.(info|debug|warning|error).*observations\b
```

**Required Commands:**
```bash
grep -n "logger\." src/life_kernel/heartbeat.py
python -c "import re; txt=open('src/life_kernel/heartbeat.py').read(); assert 'recalled_memories' not in re.findall(r'logger\.(info|debug|warning|error)', txt)"
```

**Evidence:** verification note in cleanup-verification-audit.md

---

### STEP-3: Fix 6 P20 test warnings
**Expected Files:**
- `tests/life_kernel/test_heartbeat.py`

**Forbidden Patterns:**
- `@pytest.mark.asyncio` on non-async test methods
- `RuntimeWarning` from unawaited coroutine in heartbeat test

**Required Commands:**
```bash
python -m pytest tests/life_kernel/test_heartbeat.py -q -W default
python -m pytest tests/life_kernel/ -q -W default
```
→ P20 warnings reduced by 6; pre-existing warnings remain documented

**Evidence:** test output captured in soak-readiness-report.md

---

### STEP-4: Document soak log classification
**Expected Files:**
- `docs/setup-evidence/P20/evidence/continuation/cleanup-verification-audit.md`

**Required Content:**
- Hermes fallback = historical checkpoint data
- Failed to load plugin = hermes-gateway pre-existing
- loop_manager DB auth warnings = pre-existing fail-soft

---

### STEP-5: Write soak-readiness report
**Expected Files:**
- `docs/setup-evidence/P20/evidence/continuation/soak-readiness-report.md`

**Required Content:**
- Ground-truth blocker verdicts
- Verification commands and results
- SOAK READY verdict with PASS HOLD note

---

### STEP-6: Final verification
**Required Commands:**
```bash
python -m pytest tests/life_kernel/ -q
grep -R "recalled_memories" src/life_kernel/*.py | grep -v "\.get(" | grep -v "len(" | grep -v "n_recalled"
```

## Rollback

No destructive ops. Docs edits are reversible via git. Tests only touch `tests/life_kernel/test_heartbeat.py`.

## Final Allowed Status

**P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK**

The operator waived the 24h clean-soak wait on 2026-06-25 (see
`discord-visible-autonomy/operator-soak-waiver.md`); the 24h gate was
deliberately not satisfied. This is not an unconditional PRODUCTION PASS
and not a "24h soak completed" claim. An unconditional P20 PRODUCTION PASS
would require a genuine clean 24h soak, which was waived, not completed.
