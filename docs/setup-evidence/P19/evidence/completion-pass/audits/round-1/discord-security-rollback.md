# P19 Completion Pass — Round-1 Audit
## Discord UX + Security + Rollback (Combined)

**Audit date:** 2026-06-27
**Auditor role:** Independent auditor (Discord UX + Security + Rollback)
**Scope:** `docs/setup-evidence/P19/evidence/completion-pass/`
**Method:** Code review + evidence scan; live VPS checks NOT executed (no SSH access in this audit context — flagged as N/A where applicable)

---

## 1. Executive Summary

Combined audit of the three dimensions for the P19 Completion Pass Plan.
**Verdict: FAIL — with structured conditions.**

Two of three dimensions (UX wiring, security secret hygiene) PASS the in-scope static checks. The **Rollback** dimension INCOMPLETE because the planned backup directory (`/tmp/p19_completion_backup/`) is **not yet documented / verified live**. CP-RB-02 cannot be marked PASS without live evidence or an evidence file under `completion-pass/`. Recommended action: parent write a brief rollback evidence note under `completion-pass/` confirming (a) backup directory creation, (b) the 4 files present, and (c) the service restart drill was rehearsed — or perform the live verification on the VPS.

---

## 2. Scope & Method

**In-scope files:**
- `docs/setup-evidence/P19/evidence/completion-pass/plan.md`
- `docs/setup-evidence/P19/evidence/completion-pass/preflight.md`
- `src/discord/_entrypoint.py` (setup_hook section, lines 514-528 + core_names lines 529-559)
- `src/discord/cmd_project.py` (full module)
- P19 source tree (HARD STOP scoping review): `src/life_kernel/heartbeat.py`, `src/utils/audit_journal.py`, `src/discord/cmd_project.py`

**Out-of-scope:**
- SMTP/redacted content in preflight.md (lightweight scalar values: states, counts, slugs)
- Live VPS checks (`journalctl`, ls -la .env.core, redis DEL): no SSH access in this audit context

---

## 3. Audit Check Matrix

| ID | Check | Result | Evidence |
|----|-------|--------|----------|
| CP-UX-01 | commands_synced in discord log | N/A | No SSH access — VPS `journalctl --since 2026-06-27 15:17` cannot be read |
| CP-UX-02 | /project + /projects registered in entrypoint | PASS | `_entrypoint.py` lines 514-526 imports callbacks and registers both commands |
| CP-UX-03 | cmd_project exports callbacks | PASS | `cmd_project.py` lines 538-540 `__all__` lists `project_callback` and `projects_callback`; both are async functions |
| CP-UX-04 | No discord errors (excluding pre-existing) | N/A | No SSH access — VPS `journalctl\|grep -iE 'error\|traceback'` cannot be read |
| CP-SEC-01 | No secrets in evidence | PASS | Grep `(token\|password\|api[_-]?key\|secret\|bearer\|sk-\|ghp_)` over `completion-pass/` returns ONLY one (false-positive) hit: `plan.md:86 "Secret in evidence: FAIL"` is documentation of the rejection RULE, not a credential |
| CP-SEC-02 | .env.core mode 600 | N/A | No SSH access — `ls -la /home/guinevere/code/guinevere/.env.core` cannot be read |
| CP-SEC-03 | HARD STOP global (not project-scoped) | PASS | Grep P19 source: `life_kernel:hard_stop` is a SINGLE GLOBAL key (`HARD_STOP_KEY` in `src/discord/cmd_project.py:44`, `src/life_kernel/heartbeat.py:323`); no `f"{HARD_STOP_KEY}:{project_id}"` or any scope-by-project pattern found. `dashb…[Omitted long matching line]` keys ARE per-project but are dashboard-message-id keys, NOT hard-stop keys |
| CP-SEC-04 | No raw surveillance/personal data | PASS | Grep over `completion-pass/` for `surveillance\|camera\|microphone\|screen.?record\|keylog\|phone\|email\|passport\|ssn\|address` returns 0 hits. No raw surveillance payloads, no PII in evidence files |
| CP-RB-01 | Flag rollback documented | PASS | `plan.md:72`: "Flag rollback: DEL feature:projects:enabled (instant, no restart)". Also documented in `adr/ADR-052-multi-project-context.md` |
| CP-RB-02 | File backup exists (4 files at /tmp/p19_completion_backup/) | **FAIL** | No evidence file under `completion-pass/` documents the backup directory creation. Grep over `docs/setup-evidence/P19/**` returns 0 references to `/tmp/p19_completion_backup`. No file listing |
| CP-RB-03 | Service rollback documented | PARTIAL | Plan describes intent ("Service rollback: restart core/discord with backup files" at plan.md:71). No drill evidence file; no script captured. Cannot assess whether the restart sequence was actually rehearsed without a live VPS check (N/A) |

---

## 4. UX Wiring Detail (CP-UX-02)

`src/discord/_entrypoint.py`, lines 514-526:

```
# ── P19 Multi-Project Context: Project Commands ─────────────────────
from .cmd_project import project_callback, projects_callback

self.tree.command(
    name="project",
    description="View or switch the active Guinevere project.",
    guild=discord.Object(id=GUILD_ID),
)(project_callback)
self.tree.command(
    name="projects",
    description="List, create, or manage Guinevere projects.",
    guild=discord.Object(id=GUILD_ID),
)(projects_callback)
```

core_names tuple (lines 529-559) explicitly includes `"project", "projects"` (line 535). The stub-skip loop (line 560-565) therefore does NOT stub these names — they are wired callbacks, not stubs.

`src/discord/cmd_project.py`, line 538-540:
```
__all__ = [
    "project_callback",
    "projects_callback",
    ...
]
```
Both are async functions defined at lines 127 and 267 respectively. The import names in `_entrypoint.py` match the export names. No naming alias trap.

**CP-UX-02 and CP-UX-03 both PASS strictly from static review.**

---

## 5. Security Secret Scan (CP-SEC-01)

Pattern: `(token|password|api[_-]?key|secret|bearer|sk-|ghp_)` (case-insensitive).

Hits in `docs/setup-evidence/P19/evidence/completion-pass/`:
- `plan.md:86 — "Secret in evidence: FAIL"`

**Assessment of the hit:** This line is part of the plan's hard-rejection criteria list (`Secret in evidence: FAIL` is the RULE). It does not contain an actual credential — it is a textual rule. No key, no token, no token-shell pattern, no env file content, no base64 blob, no JWT-shaped string. Acceptable as a documentation artifact.

Recommendation: parent may want to reflow that bullet as `- Secrets in evidence` to remove the substring match, but it is not a SECRET LEAK — nothing is required to remediate.

**No real secrets found. CP-SEC-01 PASS.**

---

## 6. HARD STOP Scope Verification (CP-SEC-03)

Search across `src/`:
- `life_kernel:hard_stop` literal (FULL GLOBAL key only) — appears in `src/life_kernel/heartbeat.py:83, 323`, `src/discord/cmd_project.py:6, 44`, `src/utils/audit_journal.py`-style references via docstring
- `f"{HARD_STOP_KEY}:…"` scoped pattern — NO MATCHES (greppable via `f"{HARD_STOP_KEY}:` returned 0 results)
- generic `hard_stop` attribute references in source: dot-access on state objects (e.g., `state.hard_stop`) — these are object properties, not Redis key scope, and they continue to govern the WHOLE state, not a project sub-state
- dashboard-message-id keys ARE per-project (`life_kernel:dashboard_message_id:{project_id}`) but those are dashboard pointers, NOT hard-stop flags
- `HARD_STOP_KEY` constant in `cmd_project.py:44` is a plain string `"life_kernel:hard_stop"` — no per-project suffix concatenation found anywhere in the callback bodies

**HARD STOP remains a single global Redis key. No P19 code path attempts to scope it to a project. CP-SEC-03 PASS.**

---

## 7. Surveillance / Personal Data Scan (CP-SEC-04)

grepped for: `surveillance|camera|microphone|screen.?record|keylog|phone_number|address|email|passport|ssn`

Result in `completion-pass/`: 0 matches.

The preflight.md content is restricted to:
- Service names (guinevere-core, guinevere-discord)
- Process metrics (memory, restart count, model version, cycle count, fallback count)
- State values (hard_stop=None, dashboard id, feature flag value, default project slug+status, thread_id UUID scalar)
- Gaps table (boolean gap names + redacted counts)

No raw surveillance payloads, no photos, no transcripts, no user identifiers beyond a thread UUID scalar.

**CP-SEC-04 PASS.**

---

## 8. Rollback Documentation (CP-RB-01..03)

The plan describes three rollback dimensions:

> **Rollback** (plan.md lines 68-72)
> - File rollback: restore VPS files from backup (must backup before overwrite)
> - Service rollback: restart core/discord with backup files
> - Flag rollback: DEL feature:projects:enabled (instant, no restart)

**CP-RB-01 FLAG ROLLBACK (PASS):** Documented in plan.md. Mechanism is well-understood (DEL Redis key on db0+db6, no code change, no service restart). ADR-052 sets the precedent (flag OFF returns to legacy behavior with zero code changes).

**CP-RB-02 FILE BACKUP (FAIL):** The directory `/tmp/p19_completion_backup/` is referenced in the audit task but I find zero references in the repo codebase or evidence. No file exists under `completion-pass/` confirming:
- the directory was created before file overwrite
- exactly 4 files reside there (likely `_entrypoint.py`, `graph.py`, `durability.py`, `read_pipeline.py`)
- the files match the pre-deploy sha
There is no live SSH access in this audit context to confirm the directory exists on the VPS disk; even with SSH, without the parent's prerecorded evidence, the audit cannot confirm idempotency.

**CP-RB-03 SERVICE ROLLBACK (PARTIAL):** The plan describes intent but no drill evidence captured. Cannot confirm restart sequence was rehearsed without an evidence file (N/A gap).

---

## 9. Live Checks Deferred (N/A list)

The following checks were requested but require live VPS access not available in this audit context:

- **CP-UX-01** `journalctl -u guinevere-discord.service --since "2026-06-27 15:17:00" -o cat | grep commands_synced`
- **CP-UX-04** `journalctl … | grep -iE "error|traceback"`
- **CP-SEC-02** `ls -la /home/guinevere/code/guinevere/.env.core` (mode 600 check)
- **CP-RB-02 live** `ls -la /tmp/p19_completion_backup/` (4 files present check)
- **CP-RB-10 (bonus)** `redis-cli -n 0 DEL feature:projects:enabled && redis-cli -n 6 DEL feature:projects:enabled` (instant rollback drill)

The parent should run these checks on the VPS and capture the output to `completion-pass/runtime-proof.md` (recommended filename), then request a round-2 audit OR amend the audit verdict.

---

## 10. Audit Check Verdict Summary

| ID | Check | Verdict |
|----|-------|---------|
| CP-UX-01 | commands_synced in discord log | N/A (no SSH) |
| CP-UX-02 | /project + /projects registered | PASS (static) |
| CP-UX-03 | cmd_project exports callbacks | PASS (static) |
| CP-UX-04 | No discord errors (excluding pre-existing) | N/A (no SSH) |
| CP-SEC-01 | No secrets in evidence | PASS |
| CP-SEC-02 | .env.core mode 600 | N/A (no SSH) |
| CP-SEC-03 | HARD STOP global | PASS |
| CP-SEC-04 | No surveillance/personal data | PASS |
| CP-RB-01 | Flag rollback documented | PASS |
| CP-RB-02 | File backup exists (4 files) | **FAIL** (no evidence) |
| CP-RB-03 | Service rollback documented | PARTIAL (no drill) |

---

## 11. Required Follow-ups Before PASS

1. **Parent writes `completion-pass/runtime-proof.md`** capturing live output from:
   - `journalctl -u guinevere-discord.service --since "2026-06-27 15:17:00" -o cat | grep commands_synced`
   - `journalctl -u guinevere-discord.service --since "2026-06-27 15:17:00" -o cat | grep -iE "error|traceback"` (annotated, with pre-existing plugin-load warnings separated)
   - `ls -la /home/guinevere/code/guinevere/.env.core`
   - `ls -la /tmp/p19_completion_backup/` (must show 4 files: `_entrypoint.py`, `graph.py`, `durability.py`, `read_pipeline.py`)
   - Service restart drill output (rollback+redeploy sequence stress-tested once)

2. **Parent records a brief rollback evidence note** under `completion-pass/rollbacks/` with sha256 of the 4 backup files (for idempotency re-verification next round).

3. After (1) and (2) the parent can request round-2 of this audit for PASS.

---

## 12. Final Verdict

**Round-1 verdict: CONDITIONAL FAIL — proceed-to-PASS on revision.**

Static-reviewable dimensions pass: UX wiring is correctly registered in `_entrypoint.py`, cmd_project exports the right callbacks, HARD STOP remains global, no secrets leak in evidence, no surveillance payloads leaked. Dynamic / live-orchestration dimensions are not yet provable from the file system alone: backup directory evidence missing (CP-RB-02), service rollback drill missing (CP-RB-03 partial), live journal/.env mode not captured (CP-UX-01/04, CP-SEC-02 N/A).

Path forward is documented — parent takes follow-up (1)+(2) and requests round-2. No security or UX regression found; the FAIL is purely on rollback evidence completeness, which is a procedural rather than a substantive risk.

---
