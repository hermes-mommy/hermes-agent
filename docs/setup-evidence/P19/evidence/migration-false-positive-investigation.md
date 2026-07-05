# P19 Evidence — "p19 migration EXISTS" False-Positive Investigation

**Date:** 2026-06-25
**Investigator:** Guinevere (parent)
**Trigger:** Operator (Faiz) flagged a contradictory verification output during P19 finalization: a verification command printed `!!! p19 migration EXISTS (should not) !!!` while the final report claimed "no runtime code created". This file documents the investigation and resolution.

---

## 1. The Contradictory Output

During finalize-phase verification, this command was run:

```bash
find alembic/versions/ -name "*p19*" 2>/dev/null && echo "!!! p19 migration EXISTS (should not) !!!" || echo "✓ No p19 migration file created (correct — planning-only)"
```

**Output observed:**
```
!!! p19 migration EXISTS (should not) !!!
```

This contradicted the final report's claim that P19 created no runtime code.

---

## 2. Root Cause — `find` Exit-Code Trap

The command used `find ... && echo EXISTS || echo clean`. **`find` exits 0 (success) even when it matches zero files** (0 = "ran successfully", not "found something"). So:

- `find alembic/versions/ -name "*p19*"` matched **nothing** (empty stdout).
- `find` exited **0** (success).
- The `&&` branch fired → printed `!!! p19 migration EXISTS !!!`.

This is a classic shell-logic false positive. The "EXISTS" message was triggered by find's exit code, not by an actual match. **No file path was ever printed** (find's stdout was empty) — the message appeared with no preceding file line, which is the tell-tale sign.

---

## 3. Investigation — Exhaustive Search (4 methods)

To rule out any actual p19 migration file, four independent methods were run:

| Method | Command | Result |
|---|---|---|
| A | `ls alembic/versions/ \| grep -i p19` | NO p19 file |
| B | `find alembic/ -iname "*p19*"` | NO match (stdout empty, exit 0) |
| C | `find alembic/ -iname "*project_namespace*"` | NO match |
| D | `git ls-files alembic/ \| grep -i p19` | NO tracked p19 file |
| E | `git status --short alembic/` | NO p19 entry (only pre-existing p18/p20_001/p5_*/p6_*/p7_* untracked files) |

**Conclusion: There is NO p19 migration file anywhere in the repository.** The "EXISTS" message was a false positive caused by the `find && echo` exit-code trap.

---

## 4. Pre-Existing Dirty Alembic Artifacts (NOT created by P19)

The untracked alembic files visible in `git status` are pre-existing workspace artifacts present at session start (visible in the initial git status snapshot):

- `alembic/env.py` (modified)
- `alembic/versions/p5_add_loop_indexes.py` (modified)
- `alembic/script.py.mako` (untracked)
- `alembic/versions/7239fd4b3b5a_add_reviewer_action_to_drift_log.py` (untracked)
- `alembic/versions/p18_add_memory_tiers_fsrs.py` (untracked)
- `alembic/versions/p20_001_life_kernel_schema.py` (untracked)
- `alembic/versions/p5_012_extend_loop_instances.py` (untracked)
- `alembic/versions/p5_015_add_skill_embedding.py` (untracked)
- `alembic/versions/p5_024_add_session_summaries.py` (untracked)
- `alembic/versions/p6_gamification_schema.py` (untracked)
- `alembic/versions/p6_gamification_schema.sql` (untracked)
- `alembic/versions/p7_persona_enhancement_v3.sql` (untracked)

**None of these are p19 files.** None were created or modified by the P19 session. They are pre-existing dirty workspace state (other phases' migrations not yet committed). P19 did not touch any of them.

---

## 5. P19's Actual Footprint (verified)

P19 created/modified ONLY:

```
?? docs/setup-evidence/P19/          (entire new dir — 36 markdown files)
 M CHECKLIST.md                       (P19 rows updated)
 M PROGRESS.md                        (P19 rows updated)
```

- `find docs/setup-evidence/P19 -type f ! -name "*.md"` → **empty** (only markdown, no runtime code).
- `git status --short src/ \| grep project` → **empty** (no `src/projects/` created).
- No `adr/ADR-052*` file created (planning-only; created at P19-001 execution).
- No `alembic/versions/p19_*` file created.

---

## 6. Secret Scan (re-run)

`grep -rEn` for `age12…|sk-…|ghp_…|xox…|AKIA…|AIza…` across `docs/setup-evidence/P19/` → **CLEAN** (no secret values). (The SOPS age public recipient was redacted from 2 research files earlier in finalize; re-scan confirms zero reproductions.)

---

## 7. Verdict

**P19 created NO runtime migration or code.** The "p19 migration EXISTS" message was a `find` exit-code false positive (find exits 0 on no-match, firing the `&&` "EXISTS" branch with no actual file path). The final report's "no runtime code created" claim is **correct and verified** by 4 independent search methods.

This is a **verification-tooling false positive**, not a P19 scaffold violation. No P19 artifact needs removal. The only corrective action is documentation (this file) so the contradiction is explained rather than hidden.

---

## 8. Hard-Rejection Check

| Criterion | Status |
|---|---|
| P19 created runtime migration/code → FAIL until removed | ✅ N/A — no such file exists (false positive) |
| Final report says "no runtime code" while migration exists unexplained → FAIL | ✅ RESOLVED — this file explains the false positive; no migration exists |
| Evidence hides the warning → FAIL | ✅ RESOLVED — this file surfaces and investigates the warning transparently |

---

## 9. Corrective Action for Future Verification

To avoid the `find && echo` exit-code trap, future verification commands should use:

```bash
# Correct: test find's OUTPUT, not its exit code
matches=$(find alembic/versions/ -name "*p19*" 2>/dev/null)
if [ -n "$matches" ]; then echo "EXISTS: $matches"; else echo "clean"; fi

# Or: use grep -L / test -f with explicit per-file checks
test -f alembic/versions/p19_001_project_namespaces.py && echo "EXISTS" || echo "clean"
```

Recorded as a lesson for future P19 wave verification scaffolds (P19-003 Required Commands should use `[ -n "$matches" ]` not `find && echo`).

---

## 10. Footer

| Version | Date | Author | Finding |
|---|---|---|---|
| 1.0 | 2026-06-25 | Guinevere | False positive — no p19 migration exists; P19 planning-only confirmed |
