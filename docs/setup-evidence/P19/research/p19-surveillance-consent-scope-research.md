# P19 Research: Surveillance & Consent Scope Per-Project

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** How consent and surveillance scope become per-project without breaking the global HARD STOP.

---

## 1. Executive Summary

Consent and surveillance are **global today**: `consent.consent_ledger` has a `scope` column (not project-qualified), `VALID_SURVEILLANCE_SCOPES` is hardcoded, and `check_consent(scope)` queries by scope alone. P19 must make consent/surveillance **per-project** for project-scoped scopes (surveillance sources, project integrations, project memory) while keeping **safety-critical scopes global** (persona, safe-word, distress, emergency, HARD STOP).

**Key invariant (hard rejection):** HARD STOP stays GLOBAL. A spoken safe-word halts ALL projects. Project-local pause is a DIFFERENT, weaker concept.

---

## 2. Current Consent Taxonomy

From `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` §4:

| Scope ID | Domain | Default |
|---|---|---|
| `consent.persona.normal` | Persona | Allowed after baseline |
| `consent.persona.escalated` | Persona escalation | Denied until explicit |
| `consent.persona.y5` | High yandere | Denied by default |
| `consent.surveillance.android` | Android surveillance | Source-specific deny |
| `consent.surveillance.windows` | Windows surveillance | Source-specific deny |
| `consent.surveillance.wearable` | Wearable health | Denied post-MVP |
| `consent.memory.core` | Memory | Allowed for approved sources |
| `consent.memory.do_not_recall_override` | Memory exception | Denied |
| `consent.financial.tracking` | Financial tracking | Allowed after scope approval |
| `consent.financial.action` | Financial actions | Denied |
| `consent.client.draft` | Client communication | Denied until client scope |
| `consent.client.send` | Client sends | Denied |
| `consent.autonomy.low_risk` | Autonomous work | Project-scope approved |
| `consent.autonomy.high_blast` | High-blast automation | Denied |
| `consent.emergency.minimum_necessary` | Emergency | Conditional |

---

## 3. Current Surveillance Source Matrix

From `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` Appendix A — sources SRC-AND-APP, SRC-AND-SCREEN, SRC-AND-NOTIF, SRC-AND-GPS, SRC-AND-CALL, SRC-AND-CLIP, SRC-AND-CAMERA, SRC-WIN-ACTIVE, SRC-WIN-IDLE, SRC-WIN-SCREEN, SRC-WIN-BROWSER, SRC-WIN-CLIP, SRC-WIN-CAMERA, SRC-WEARABLE.

Runtime: `VALID_SURVEILLANCE_SCOPES` frozenset (`consent_gate.py:49-55`): `surveillance.app_usage`, `surveillance.location`, `surveillance.notifications`, `surveillance.clipboard`, `surveillance.email`.

---

## 4. Current Consent Ledger Schema

- **Table:** `consent.consent_ledger` (`src/memory/models.py:943-962`).
- **Columns:** `scope` (text, not project-qualified), `status` (ACTIVE/PAUSED/WITHDRAWN), `granted_at`, `granted_by`, `revoked_at`, `revocation_reason`, `evidence_hash`.
- **Query:** `SELECT status FROM consent.consent_ledger WHERE scope = :scope ORDER BY granted_at DESC LIMIT 1` (`consent_gate.py:393-397`).
- **Cache:** Redis DB2 `consent:surveillance:{scope}` TTL 300s (`consent_gate.py:43-46, 215, 353-369`).
- **Legacy parallel store:** Redis DB0 `consent:grants` JSON set (`cmd_consent.py:38-39`) — operator-facing command store, separate from ledger.
- **No `project_id` column anywhere in the consent path.**

---

## 5. Per-Project Consent Design

### 5.1 Option A: project_id column in consent_ledger (RECOMMENDED)
- Add `project_id UUID NULL` column to `consent.consent_ledger`.
- A row with `project_id IS NULL` = global consent (applies to all projects).
- A row with `project_id = X` = project-scoped consent (applies only to project X).
- Query: `SELECT status FROM consent.consent_ledger WHERE scope = :scope AND (project_id IS NULL OR project_id = :project_id) ORDER BY granted_at DESC LIMIT 1`.
- Effective status = most specific match: if a project-scoped row exists, it wins; else fall back to global row.

### 5.2 Option B: composite scope strings
- `consent.surveillance.android.project_work` — encode project in scope string.
- Pros: no schema change.
- Cons: stringly-typed, hard to query "all consents for project X", breaks existing scope matching.

### 5.3 Option C: separate project_consent table
- `consent.project_consent_ledger` with `(scope, project_id)`.
- Pros: clean separation.
- Cons: two tables, join complexity.

### 5.4 Recommendation
**Option A.** It's the simplest, queryable, and backward-compatible (NULL = global).

---

## 6. Hard Rejection: HARD STOP Must Stay Global

**HARD STOP** (`life_kernel:hard_stop`, `hard_stop_handler.py`) is a **persona-level safety override**, NOT per-project. It halts:
- All active sessions (all projects)
- All background cognition (all projects)
- All autonomous work (all projects)
- Persona escalation, punishment, yandere, surveillance confrontation (globally)

A spoken safe-word triggers global HARD STOP regardless of which project is active. **P19 must NOT scope HARD STOP.** This is a hard rejection criterion.

---

## 7. Project-Local Pause vs Global HARD STOP (CRITICAL DISTINCTION)

| Concept | Scope | Effect | Trigger | Restoration |
|---|---|---|---|---|
| **Global HARD STOP** | All projects + persona | Halt everything; switch neutral; pause surveillance confrontation | Safe-word / distress / crisis | Explicit Faiz readiness |
| **Project-local pause** | One project only | Pause autonomous work on project X; other projects continue; persona unaffected | `/project pause <name>` or policy gate | `/project resume <name>` |

P19 must model these as **separate** concepts:
- `life_kernel:hard_stop` (global, single key) — unchanged.
- `project:{project_id}:paused` (per-project, Redis DB0) — new, weaker.

A project-local pause does NOT trigger safe-mode, does NOT halt persona, does NOT block other projects. Only the global HARD STOP does.

---

## 8. Surveillance Source-to-Project Mapping

A single surveillance source (e.g., Android GPS) can feed multiple projects, but classification/retention/consent may differ per project. Design:
- `surveillance.events` gets `project_id` column (nullable; NULL = unassigned, falls to `default`).
- Event ingestion tags each event with the active project (from device context or Faiz's current project).
- Consent check: `check_consent(scope, project_id)` — checks both project-scoped and global consent rows.

**One source, multiple projects:** If Faiz wants Android GPS to feed both `work` and `personal`, two project-scoped consent rows (or one global row) authorize it; events are tagged per active project.

---

## 9. Consent Cache Per-Project

Redis cache key pattern:
- Global consent: `consent:{scope}` (no project) — DB2.
- Project consent: `consent:{project_id}:{scope}` — DB2.

`check_consent(scope, project_id)`:
1. Check `consent:{project_id}:{scope}` cache → if hit, return.
2. Else query ledger for `(scope, project_id)` OR `(scope, project_id IS NULL)`.
3. Effective = most specific (project row wins over global).
4. Cache result under project key.
5. Fail-closed on cache miss/stale/ledger-unavailable.

---

## 10. Revocation Cascade Per-Project

- Revoke consent for project X (`/consent project:work category:surveillance action:off`) → cascade only project X's data/actions (mark project X's surveillance events for deletion/summarization, pause project X's surveillance actuators).
- Global persona revoke (`/consent category:persona.escalated action:off`) → cascade all projects' persona escalation.
- Safe-word → global HARD STOP cascade (all projects).

---

## 11. Surveillance Confrontation Block (Global)

Per SurveillanceDataPolicy §8: during safe-mode/distress/crisis/incident, surveillance-derived confrontation is blocked **globally** (not per-project). `SurveillanceSafeModeGuard` (`safe_mode.py:31-163`) stays global. P19 does not scope this.

---

## 12. Project-Scoped P22 Integration Consent

P22 integrations (calendar, github, notion) consent is **per project**. Each project can have its own calendar account/GitHub project/Notion workspace. P19 provides `project_id` on all P22 consent rows and `audit.integration_api_log` rows.

---

## 13. Consent UX in Discord

Two interaction models:
- **Explicit project in command:** `/consent project:work category:surveillance action:on source:android.gps`.
- **Current project implicit:** `/project work` then `/consent category:surveillance action:on source:android.gps` (uses current active project).

Both write a project-scoped consent_ledger row + audit.

---

## 14. Audit Trail Per-Project

Every consent event (grant/update/pause/revoke/restore) audit row includes `project_id` (NULL for global events). Audit queryable per-project: "show all consent changes for project X in last 24h".

---

## 15. Safety-Critical Scopes That Stay Global (NOT project-scoped)

| Scope | Why global |
|---|---|
| `consent.persona.normal` | Persona is one shared Guinevere |
| `consent.persona.escalated` | Persona escalation is persona-level |
| `consent.persona.y5` | Yandere ceiling is persona-level |
| `consent.emergency.minimum_necessary` | Emergency is persona-level safety |
| `consent.autonomy.high_blast` | High-blast automation needs Faiz approval regardless of project (optionally project-scoped if project has its own blast radius) |
| Safe-word / distress / crisis / HARD STOP | Always global, non-negotiable |

These scopes store with `project_id IS NULL` (global). They cannot be scoped per-project.

---

## 16. Project-Scoped Scopes (SHOULD be per-project)

| Scope | Why project-scoped |
|---|---|
| `consent.surveillance.{source}` | Different projects use different surveillance |
| `consent.memory.core` (project data) | Memory is partitioned per project |
| `consent.client.draft/send` | Different clients per project |
| `consent.financial.action` | Different budgets per project |
| `consent.financial.tracking` | Different finance sources per project |
| P22 integration consents (calendar/github/notion) | Per-project integrations |
| `consent.autonomy.low_risk` (project work) | Project-scoped autonomous work |
| `consent.voice.*` (P21) | Optionally per-project voice capture |

---

## 17. Migration from Global Consent

1. Migration `p19_001` adds `project_id UUID NULL` to `consent.consent_ledger`.
2. Existing rows stay `project_id IS NULL` (global) — no backfill needed (NULL = global is the correct semantic).
3. Seed `default` project in `projects.project_registry`.
4. New project-scoped consent rows written with explicit `project_id`.
5. `check_consent()` updated to accept `project_id` and query both.

---

## 18. Consent Receipt Per-Project

Faiz-facing receipt includes `project_id` (or "global") so Faiz knows which project a consent applies to.

---

## 19. Gate Function Signature Change

**Current:** `check_consent(scope: str) -> ConsentCheckResult`
**Proposed:** `check_consent(scope: str, project_id: Optional[UUID] = None) -> ConsentCheckResult`

Callers to update (all in `consumer.py`, `cmd_surveillance_*.py`, `commands_surveillance/*.py`, `gmail/consent_manager.py`, `wearable/health_consent.py`):
- `consumer.py:173-195` — pass active project_id from event context.
- `gmail/consent_manager.py:104-132` — pass project_id (gmail is project-aware if project-scoped).
- `wearable/health_consent.py:153-187` — pass project_id (wearable is project-aware if scoped).

Backward-compatible: `project_id=None` → global-only query (current behavior).

---

## 20. Hard Rejection Checks

1. **Consent/surveillance scope NOT per-project:** ✅ MITIGATED — `project_id` column + `check_consent(scope, project_id)`.
2. **HARD STOP NOT global:** ✅ MITIGATED — `life_kernel:hard_stop` stays single global key; only project-local pause is per-project.
3. **Project pause conflated with HARD STOP:** ✅ MITIGATED — separate `project:{id}:paused` key vs global `life_kernel:hard_stop`; documented distinction.

---

## 21. Conclusion

P19 makes consent/surveillance per-project via a `project_id` column in `consent.consent_ledger` (NULL = global) and a `check_consent(scope, project_id)` signature change. Safety-critical scopes (persona, emergency, HARD STOP, safe-word) stay global. Project-scoped scopes (surveillance sources, project memory, client/financial actions, P22 integrations) become per-project. HARD STOP remains a single global key, distinct from per-project pause. Revocation cascades are project-scoped for project consents and global for persona/safety consents.
