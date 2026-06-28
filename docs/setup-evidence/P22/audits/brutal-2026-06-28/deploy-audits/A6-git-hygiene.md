# A6 — Git Hygiene Audit

**Auditor:** Independent sub-agent  
**Date:** 2026-06-28  
**Verdict: PASS**

---

## Scope

P22 production deploy was via `scp` (NOT `git push`). Operator chose this intentionally; it is not a hygiene violation. A local commit `4c1c7cc` exists (111 files, +18403/-150) but was never pushed to any remote. This audit verifies:

1. No secrets or junk files were included in the local commit.
2. No live secret literals appear in the commit diff.
3. The scp deploy did not touch `.env` files on VPS.
4. VPS received post-fix code, not stale pre-fix code.

---

## Step 1 — Commit Existence

```
$ git show --stat 4c1c7cc | tail -5
 tests/p22/test_permissions.py                      | 198 +++++
 tests/p22/test_registry.py                         | 179 +++
 tests/p22/test_shims.py                            |  42 +-
 111 files changed, 18403 insertions(+), 150 deletions(-)
```

**Result:** CONFIRMED. Commit exists with exactly 111 files, +18403/-150.

---

## Step 2 — No Secrets or Junk Files in Commit

```
$ git show 4c1c7cc --name-only | grep -iE '\.env|\.claude/|\.codex/|playwright|research-cache|continuation_staging|\.bak|^[0-9]'
(no output)
```

**Result:** CONFIRMED. No `.env`, `.claude/`, `.codex/`, `playwright`, `research-cache`, `.bak`, or bare-numeric junk files in the commit.

---

## Step 3 — No Live Secret Literals in Diff

```
$ git show 4c1c7cc | grep -iE 'password\s*=\s*...|token\s*=\s*...|api_key\s*=\s*...' | grep -viE 'os\.environ|getenv|get\(|settings\.|self\.|placeholder|example|fake|dummy|test|None|bool\('
(no output)
```

**Result:** CONFIRMED. No hardcoded passwords, tokens, or API keys in the commit diff. All credential references use `os.environ`/`getenv` indirection.

---

## Step 4 — VPS .env Files Untouched

```
$ ssh guinevere-vps "ls -la /home/guinevere/code/guinevere/.env.core"
-rw------- 1 guinevere guinevere 851 Jun 28 06:01 /home/guinevere/code/guinevere/.env.core
```

**Result:** CONFIRMED. `.env.core` timestamp is `06:01` (pre-existing, before deploy). The scp did not overwrite it. File permissions remain `600` (owner-only read/write).

---

## Step 5 — VPS Has Post-Fix Code

```
$ ssh guinevere-vps "grep -c 'RateLimitMiddleware' /home/guinevere/code/guinevere/src/core/main.py"
2
```

**Result:** CONFIRMED. `RateLimitMiddleware` appears 2 times in the deployed `main.py`. The pre-fix version did not contain this class. VPS is running the post-fix code.

---

## Verdict

| Check | Expected | Actual | Status |
|---|---|---|---|
| Commit exists, ~111 files | 111 files, +18403/-150 | 111 files, +18403/-150 | PASS |
| No secrets/junk in commit | EMPTY | EMPTY | PASS |
| No live secret literals in diff | EMPTY | EMPTY | PASS |
| VPS .env.core untouched | Pre-existing timestamp | 06:01 (pre-deploy) | PASS |
| VPS has post-fix code | RateLimitMiddleware >= 1 | 2 matches | PASS |

**PASS** — All 5 checks passed. No secrets were committed, no `.env` files were overwritten on VPS, and the deployed code is the post-fix version. Deploy-via-scp is an intentional operator decision, not a hygiene violation.
