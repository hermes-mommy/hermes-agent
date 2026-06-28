# P22 Brutal-Audit Deploy Plan

**Date:** 2026-06-28
**Author:** Guinevere (parent, ground-truthed)
**Mission:** Deploy all 32 P22 brutal-audit fixes to production VPS, verified live, auditor PASS.

---

## 0. Ground-Truth State (verified 2026-06-28, NOT the prompt's assumptions)

The operator-issued deploy prompt assumed "VPS runs pre-fix code" (implying a clean
base). **Ground-truth contradicts this.** Verified facts:

### Local dev box (`C:\Users\faizz\guinevere`, branch `main`)
- `main` HEAD = `f912295` — **22 commits ahead of `origin/main` (`123a31a`, a P11 WhatsApp fix).**
  None of P20 production-activation nor P22 has ever been pushed.
- P22 fixes present locally: 34 modified + 12 new untracked files (incl. `audit_db_writer.py`,
  which the prompt's list omitted).
- **972 tests pass** (`python -m pytest tests/p22/ -q` → 972 passed in 36.21s, exit 0). VERIFIED.
- Forbidden-pattern grep gate: **P22 scope clean** (0 `as any`/`type:ignore`/`target=None`/
  `except Exception` in `cmd_integrations.py`/`x_access_token[`/`_rpw` in P22 files). The 22
  pre-existing `# type: ignore` are all OUTSIDE P22 scope (whatsapp/gmail/mcp/sentry) — not regressions.
- `git check-ignore .env.core .claude/ .codex/` → exit 1 (**NOT ignored**) → selective `git add`
  is mandatory; a blanket add would commit secrets/artifacts.

### VPS (`guinevere-vps`, `/home/guinevere/code/guinevere`, branch `main`)
- HEAD = `123a31a` (same as origin/main — VPS == origin, behind local by 22).
- `guinevere-core` systemd: `active`, `NRestarts=0`, `SubState=running`.
  `ExecStart=.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2`,
  `EnvironmentFile=.env.core`, `WorkingDirectory=/home/guinevere/code/guinevere`.
  → **Service runs from `.venv`, NOT system python3.** Deps install into `.venv`.
- **DIRTY WORKING TREE: 39 files, +14,583/-9,671 lines** — `memory/models.py`,
  `consolidation.py`, `read_pipeline.py`, `write_pipeline.py`, `surveillance/consent_gate.py`
  (adds P19-009 project-scoped consent), `loops/*`, `persona/yandere_fsm.py`,
  `hermes/safety_plugin.py`, `mcp/*`. **NOT P22 — parallel dev line, never pushed.**
  5 stashes exist (`pre-p18-deploy-stash`, `vps-local-changes-pre-full-access`, …).
  **CRITICAL:** VPS dirty tree does NOT overlap P22 files (life_integrations/core-api/
  discord-entrypoint are untouched on VPS) → pull is mostly additive, conflict unlikely but possible.
- `src/life_integrations/` is **UNTRACKED on VPS** (`git ls-files` = 0) → phantom dir.
  `git pull` will track it. `alembic/versions/p22_002` MISSING on VPS → pull adds it.
  `rate_limit.py` + `cmd_integrations.py` MISSING on VPS → pull adds them. All additive/safe.
- **Alembic head on VPS = `p22_001_integration_schema`** (P22 schema already applied once).
  `p22_002` will run as the single new migration.
- **DB CLI auth broken from raw shell:** `alembic current` failed with
  `InvalidPasswordError: password authentication failed for user "guinevere_core"`,
  and `DATABASE_URL` is **not in the shell env** — it lives in `.env.core`.
  → **All migration / DB-verification steps MUST `set -a && . .env.core && set +a` first.**
  (The running service loads `.env.core` via systemd EnvironmentFile, so it has the creds;
  the failure was only my raw `ssh` shell lacking them.)

### Operator decisions (locked 2026-06-28 via AskUserQuestion)
1. **VPS dirty tree → `git stash -u` before pull, attempt `git stash pop` after.**
   Stash is precious; **NEVER drop without explicit operator OK.**
2. **Push all 22 commits as-is** (fast-forward origin → local; no history rewrite, no force-push).

---

## 1. Master Todo (atomic, ordered)

| # | Step | Phase | Parallel? | Owner |
|---|---|---|---|---|
| T1 | Write this deploy-plan.md (planner gate) | Plan | seq | parent |
| T2 | Pre-deploy grep + secrets scan + 972-test gate | Pre | done | parent |
| T3 | Selective `git add` P22 files only; verify staged diffstat (no secrets) | Git | seq | parent |
| T4 | `git commit` (detailed message) | Git | seq | parent |
| T5 | `git push origin main` (fast-forward 22 commits) | Git | seq | parent |
| T6 | VPS: `git stash -u` (preserve 14k lines); record stash ref | VPS | seq | parent |
| T7 | VPS: `git pull origin main` (22 commits) | VPS | seq | parent |
| T8 | VPS: `git stash pop`; if conflict → STOP, report, do NOT drop | VPS | seq | parent |
| T9 | VPS: verify P22 files now present (rate_limit, cmd_integrations, p22_002) | VPS | seq | parent |
| T10 | VPS: install new deps into `.venv` IF any (F07 is dep-free → likely no-op) | VPS | seq | parent |
| T11 | VPS: `set -a && . .env.core && set +a && .venv/bin/alembic upgrade head` | VPS | seq | parent |
| T12 | VPS: `sudo systemctl restart guinevere-core`; wait 10s | VPS | seq | parent |
| T13 | VPS: verify `is-active=active`, `NRestarts=0`, no traceback in journal | VPS | seq | parent |
| T14 | VPS: live verify 7 API endpoints + 401 on mutations + 429 rate-limit | VPS | seq | parent |
| T15 | VPS: live verify 6 Discord commands registered (journal) | VPS | seq | parent |
| T16 | VPS: live verify audit trail DB writes (recent rows > 0) | VPS | seq | parent |
| T17 | VPS: live verify F03 consent fail-closed + F04 L2 default (code grep on VPS = post-fix) | VPS | seq | parent |
| T18 | VPS: live verify F13 WORM TRUNCATE revoked (pg grants) | VPS | seq | parent |
| T19 | VPS: P20 regression (NRestarts=0, memory stable, no journal errors) | VPS | seq | parent |
| T20 | VPS: run `tests/p22/` on VPS if feasible | VPS | seq | parent |
| T21 | Auditor wave: 8 parallel auditors (F01-F05, F07, F13, P20, migration, git, tests, evidence) | Audit | parallel | sub-agents |
| T22 | Fix any NEEDS_REVIEW/FAIL; re-audit via continuation until PASS | Audit | seq | parent+sub |
| T23 | Write `deploy-evidence.md` + update `PROGRESS.md` | Evidence | seq | parent |
| T24 | Commit + push evidence | Evidence | seq | parent |
| T25 | Final report | Report | seq | parent |

---

## 2. Dependency Map

```
T1 (plan) ─┐
T2 (gate) ─┤
           ├─► T3 (add) ─► T4 (commit) ─► T5 (push) ─┐
                                                      ├─► T6 (stash) ─► T7 (pull) ─► T8 (pop) ─► T9 (verify files)
                                                      │                                                                  │
                                                      │                                                                  ├─► T10 (deps) ─► T11 (migrate) ─► T12 (restart) ─► T13 (stable)
                                                      │                                                                  │                                                                          │
                                                      │                                                                  │                                                                          ├─► T14-T20 (live verify) ─► T21 (auditors) ─► T22 (fix cycle) ─► T23-T25
                                                      └──────────────────────────────────────────────────────────────────────────┘
```

- T5 (push) must precede T7 (pull) — VPS pulls from origin.
- T6 (stash) MUST precede T7 (pull) — pull over dirty tree fails/merges.
- T11 (migrate) MUST precede T12 (restart) — service restart loads post-fix code + post-migrate schema.
- T13 (stable) is the **hard gate** before T14-T20: if service fails, ROLLBACK, do not verify.
- T21 auditors fire only after T14-T20 parent-verified (per §2.4 audit-batch).

---

## 3. Collision Scan

| Resource | Owner | Risk | Mitigation |
|---|---|---|---|
| `origin/main` | T5 only | none | fast-forward, no force |
| VPS working tree (39 dirty files) | T6 stash only | **HIGH** — 14k lines uncommitted | `git stash -u`; stash-pop after; STOP on conflict |
| `.env.core` (VPS) | read-only (source for migrate) | secret leak if committed | NEVER `git add` any `.env*` |
| `alembic/versions/` | T11 only | migration order | `p22_002` chains from `p22_001` (VPS head) — safe |
| `guinevere-core` service | T12 only | brief downtime | restart only after migrate; rollback if fail |
| PostgreSQL `audit.integration_api_log` | T11 only | brief lock | REVOKE is metadata-only, sub-second |
| `PROGRESS.md` | T23 only | none | parent-only |

---

## 4. Per-Step Verification Scaffold

### T3 (git add) — scaffold
- **Expected files staged:** 34 modified + 12 new + evidence dir (≈46 files). Includes `audit_db_writer.py`.
- **Forbidden patterns (staged diff must be 0):** `^---.*\.env`, `BOT_TOKEN=`, `DATABASE_URL=postgres.*password`, paths under `.claude/`, `.codex/`, `.playwright-mcp/`, `.research-cache/`, `_continuation_staging/`.
- **Required commands:**
  - `git diff --cached --stat | tail -1` → ~46 files changed
  - `git diff --cached --name-only | grep -E '\.env|\.claude/|\.codex/|playwright|research-cache|continuation_staging'` → **0 lines**
  - `git diff --cached | grep -iE 'password|token|secret|api_key' | grep -v '# ' ` → review any hit (test fixtures may legitimately use placeholders)
- **Hard reject:** any `.env*` staged; any `.claude/`/`.codex/` staged; staged file count < 40.

### T5 (push) — scaffold
- **Required:** `git push origin main` → exit 0; `git rev-parse origin/main` == `f912295` (local HEAD).
- **Hard reject:** non-fast-forward (would need force — FORBIDDEN); push rejected by remote.

### T6-T8 (VPS stash/pull/pop) — scaffold
- **Required:**
  - `git stash list` shows new stash on top
  - `git status --short` is **clean** after stash (before pull)
  - `git pull origin main` → exit 0, "Fast-forward" + 22 commits
  - `git rev-parse HEAD` on VPS == `f912295`
  - `test -f src/core/api/rate_limit.py && test -f src/discord/cmd_integrations.py && test -f alembic/versions/p22_002_revoke_truncate_audit.py` → all exist
  - `git ls-files src/life_integrations/ | wc -l` → > 0 (now tracked)
  - `git stash pop` → exit 0 (no conflict) OR report conflict + STOP
- **Hard reject:** pull leaves merge conflicts; stash-pop conflict without operator OK to resolve/drop; `life_integrations` still untracked after pull.

### T11 (migrate) — scaffold
- **Pre:** `set -a && . .env.core && set +a` (loads DATABASE_URL).
- **Required:**
  - `.venv/bin/alembic upgrade head` → exit 0, runs `p22_002_revoke_truncate_audit`
  - `.venv/bin/alembic current` → `p22_002_revoke_truncate_audit (head)`
- **Hard reject:** migration raises; `alembic current` ≠ p22_002; DB auth still fails after sourcing .env.core.

### T12-T13 (restart + stable) — scaffold
- **Required:**
  - `sudo systemctl restart guinevere-core` → exit 0
  - `sleep 10; systemctl is-active guinevere-core` → `active`
  - `systemctl show guinevere-core -p NRestarts` → `NRestarts=0`
  - `journalctl -u guinevere-core --since '2 min ago' | grep -iE 'error|traceback|exception|fail'` → **0 hits** (or only pre-existing/non-P22)
- **Hard reject:** `is-active` = `failed`; NRestarts > 0; traceback referencing P22 modules.

### T14 (API live) — scaffold
- **Required:**
  - `curl -s http://127.0.0.1:8000/api/v1/integrations/status` → 200 + JSON
  - `curl -s .../capabilities` → 200 + JSON
  - `curl -s .../missing` → 200 + JSON (CONFIG_MISSING list)
  - `curl -s -o /dev/null -w '%{http_code}' .../test -X POST -d '{}'` (no API key) → **401**
  - 50 rapid hits to `/status` → mix of 200 then **429** (rate limit active)
- **Hard reject:** status endpoint non-200; mutation returns 200 without auth (F07/auth regression); no 429 ever (rate limit not wired).

### T17 (F03/F04 code on VPS) — scaffold
- **Required:**
  - `grep 'hard_stop_checker is None' src/life_integrations/consent.py` → line 124
  - `grep 'L2_WRITE' src/life_integrations/permissions.py | tail -5` → default-L2 lines
- **Hard reject:** VPS file lacks the fix (means pull didn't land P22).

### T18 (F13 WORM) — scaffold
- **Pre:** source .env.core.
- **Required:** `psql` query `information_schema.role_table_grants` for `audit.integration_api_log`:
  `guinevere_core` has INSERT, SELECT; **NO UPDATE, NO DELETE, NO TRUNCATE.**
- **Hard reject:** TRUNCATE still granted to guinevere_core or PUBLIC.

### T19 (P20 regression) — scaffold
- **Required:** `NRestarts=0`, `MemoryCurrent` stable (not climbing to OOM), `journalctl ... | grep -iE 'error|fail|traceback'` → 0 P22-attributable hits; Discord embed/autonomy still functioning (if checkable).
- **Hard reject:** service crash-loop; P20 autonomy regression; OOM trend.

---

## 5. Rollback Plan

If deploy fails at step N:

| Failed step | Rollback action |
|---|---|
| T5 (push) | nothing to roll back (push failed pre-VPS-change) |
| T7 (pull) | VPS: `git reset --hard 123a31a` (pre-pull HEAD); `git stash pop` to restore dirty tree |
| T8 (stash-pop conflict) | `git stash` (re-stash unresolved); report to operator; **do NOT `git stash drop`**; service still on 123a31a (pre-restart) |
| T11 (migrate) | `.venv/bin/alembic downgrade p22_001_integration_schema` (reverts p22_002) |
| T12/T13 (restart fail) | `git reset --hard 123a31a` + `git stash pop` + `sudo systemctl restart guinevere-core` + verify `is-active`; write `deploy-incident.md` |
| T14-T20 (live verify fail) | depends — code fix + redeploy, OR rollback to 123a31a |

**Stash safety invariant:** the VPS stash created in T6 is NEVER dropped without explicit
operator confirmation, even on rollback. If rollback must restore the dirty tree, `git stash pop`
is used; if it conflicts, operator decides.

---

## 6. Auditor Matrix

| Auditor | Surface | Fires after |
|---|---|---|
| A1 | F01-F05 CRITICAL fixes live on VPS (git log match + code + behavior) | T17 |
| A2 | F07 rate limiting live (429 observed) | T14 |
| A3 | F13 WORM TRUNCATE revoked (pg grants) | T18 |
| A4 | P20 regression (NRestarts, memory, journal, Discord) | T19 |
| A5 | Migration safety (alembic current = p22_002, idempotent, rollback path) | T11 |
| A6 | Git hygiene (no secrets committed, no .claude/.codex, VPS git log == local) | T5+T7 |
| A7 | Test suite (972 pass; VPS run if feasible) | T20 |
| A8 | Evidence completeness (deploy-evidence.md, PROGRESS.md, all reports) | T23 |

Auditors write to `docs/setup-evidence/P22/audits/brutal-2026-06-28/deploy-audits/A{N}-*.md`.

---

## 7. Caveats

1. **VPS dirty tree is the dominant risk.** Stash-pop conflict is the most likely failure point.
   If it conflicts, deploy PAUSES — operator decides. The 14k lines are P19/memory/surveillance
   work that may or may not be wanted; not my call to drop.
2. **DB CLI auth** requires sourcing `.env.core`; the running service is fine (systemd loads it),
   but my raw `ssh` shell does not. All DB steps source it first.
3. **F07 is dependency-free** (stdlib deque middleware) → no `pip install` expected. T10 verifies.
4. **972 tests verified locally**; VPS test run (T20) is best-effort — VPS may lack test deps.
5. **P22 was "PROD PASS" per memory but VPS only has p22_001 (pre-brutal).** This deploy brings
   VPS to the post-brutal-audit state for the first time. Memory `p22-production-activation-complete`
   may reflect an earlier partial deploy; this is the canonical brutal-audit-remediated deploy.
6. **No force-push.** Push is fast-forward only (22 commits).

---

## 8. Execution Checklist (synced to todos T1-T25)

- [x] T1 plan written (this file)
- [x] T2 pre-deploy gate (972 pass, grep clean)
- [ ] T3 selective git add
- [ ] T4 commit
- [ ] T5 push (FF 22 commits)
- [ ] T6 VPS stash -u
- [ ] T7 VPS pull
- [ ] T8 VPS stash pop (STOP on conflict)
- [ ] T9 VPS verify P22 files present
- [ ] T10 VPS deps (likely no-op)
- [ ] T11 VPS migrate (source .env.core first)
- [ ] T12 VPS restart
- [ ] T13 VPS stable (active, NRestarts=0)
- [ ] T14 API live (7 endpoints, 401, 429)
- [ ] T15 Discord commands registered
- [ ] T16 audit trail DB writes
- [ ] T17 F03/F04 code on VPS
- [ ] T18 F13 WORM grants
- [ ] T19 P20 regression
- [ ] T20 VPS test suite
- [ ] T21 8 auditors
- [ ] T22 fix cycle → PASS
- [ ] T23 evidence + PROGRESS.md
- [ ] T24 commit + push evidence
- [ ] T25 final report

---

## Footer

| Field | Value |
|---|---|
| Plan basis | Ground-truthed VPS + local state 2026-06-28 (not prompt assumptions) |
| Operator decisions | stash-dirty-tree + push-22-as-is (locked via AskUserQuestion) |
| Dominant risk | VPS stash-pop conflict over 14k uncommitted lines |
| Test gate | 972 passed (verified) |
| Forbidden patterns | P22 scope clean (verified) |
| Rollback | per-step; stash never dropped without operator OK |
