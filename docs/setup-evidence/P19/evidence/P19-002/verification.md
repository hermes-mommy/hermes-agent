# P19-002 Verification Report — Project Registry / Domain Models

> **Wave:** P19-002 — Project Registry / Domain Models  
> **Date:** 2026-06-25  
> **Status:** PASS / FAIL (fill at bottom)  
> **Executor:** <sub-agent>  
> **Reviewer:** Faiz (Owner)

---

## 1. Objective

Verify that `src/projects/` implements the canonical project registry
(create/list/archive/resolve/get) with typed domain models, injectable audit
hooks, default project seeding, and comprehensive unit tests.

---

## 2. File Inventory

| # | File | Purpose | Present |
|---|------|---------|---------|
| 1 | `src/projects/__init__.py` | Package init, public exports | YES |
| 2 | `src/projects/types.py` | `ProjectId`, `Project`, `ProjectStatus`, `ProjectScope` | YES |
| 3 | `src/projects/registry.py` | `ProjectRegistry` + `ProjectStore` ABC + `InMemoryProjectStore` + `AuditWriter` protocol | YES |
| 4 | `src/projects/exceptions.py` | `ProjectNotFoundError`, `ProjectAlreadyExistsError`, `ProjectArchivedError`, `InvalidProjectSlugError` | YES |
| 5 | `tests/projects/__init__.py` | Test package init | YES |
| 6 | `tests/projects/test_registry.py` | Unit tests (in-memory store, mock audit writer) | YES |
| 7 | `docs/setup-evidence/P19/evidence/P19-002/verification.md` | This report | YES |
| 8 | `docs/setup-evidence/P19/evidence/P19-002/auditor-gate.md` | Auditor sign-off | YES |

---

## 3. Domain Models (`src/projects/types.py`)

### 3.1 `ProjectId` type

- [X] Declared as `uuid.UUID` (newtype alias).
- [X] Used in all public API signatures (`create`, `get`, `archive`, `resolve`).

### 3.2 `Project` Pydantic model

- [X] Frozen (`frozen=True`, `extra="forbid"`).
- [X] Fields: `project_id`, `slug`, `name`, `status`, `project_scope`,
      `description`, `created_at`, `archived_at`, `metadata`,
      `default_channel_id`, `dashboard_channel_id`, `log_channel_id`,
      `accent_color`.
- [X] `ProjectStatus` = `Literal["active", "paused", "archived"]`.
- [X] `ProjectScope` = `Literal["global", "project"]`.
- [X] Slug validated with `pattern` regex.

### 3.3 Exceptions

- [X] `ProjectNotFoundError(LookupError)` — project ID/slug not found.
- [X] `ProjectAlreadyExistsError(ValueError)` — duplicate slug on create.
- [X] `ProjectArchivedError(RuntimeError)` — default project archive guard.
- [X] `InvalidProjectSlugError(ValueError)` — malformed slug.

---

## 4. `ProjectRegistry` (`src/projects/registry.py`)

### 4.1 Construction

- [X] Accepts `store: ProjectStore` (abstract persistence).
- [X] Accepts optional `audit_writer: AuditWriter` (protocol).
- [X] `DEFAULT_PROJECT_ID` constant = `00000000-0000-0000-0000-000000000001`.

### 4.2 Default project seeding

- [X] `_ensure_default_seeded()` called lazily on first public operation.
- [X] Default project slug = `"default"`, status = `"active"`,
      scope = `"global"`.
- [X] Cannot be archived (`ProjectArchivedError`).

### 4.3 `create(slug, ...) -> Project`

- [X] Validates slug format.
- [X] Checks slug uniqueness.
- [X] Generates UUID via `uuid.uuid4()`.
- [X] Sets `created_at` to `datetime.now(timezone.utc)`.
- [X] Defaults `name` to `slug` if omitted.
- [X] Writes `project.created` audit event.

### 4.4 `get(project_id: ProjectId) -> Project`

- [X] Returns project by UUID.
- [X] Raises `ProjectNotFoundError` when missing.

### 4.5 `resolve(slug: str) -> Project`

- [X] Returns project by slug.
- [X] Raises `ProjectNotFoundError` when missing.
- [X] Raises `InvalidProjectSlugError` on malformed slug.

### 4.6 `list() -> list[Project]`

- [X] Returns all projects (including archived).

### 4.7 `list_active() -> list[Project]`

- [X] Filters out archived projects.

### 4.8 `archive(project_id, ...) -> Project`

- [X] Sets `status = "archived"` and `archived_at`.
- [X] Raises `ProjectArchivedError` for default project.
- [X] Idempotent for already-archived (no error).
- [X] Writes `project.archived` audit event.

---

## 5. Audit Hook (`AuditWriter` Protocol)

- [X] Protocol class defines `write_event(event_type, loop_id, data)`.
- [X] Instance-level writer injected at construction.
- [X] Per-call writer override available on `create()` and `archive()`.
- [X] Falls back gracefully (no crash) when no writer configured.

---

## 6. Store Abstraction (`ProjectStore` ABC + `InMemoryProjectStore`)

- [X] `ProjectStore` ABC: `create`, `get`, `get_by_slug`, `list_all`,
      `update`, `delete`.
- [X] `InMemoryProjectStore` implements all methods with plain dicts.
- [X] No external dependencies (no Postgres, no Redis).

---

## 7. Type Safety Check

Command: `grep -rnE "# type: ignore|as any|except Exception|except:" src/projects/`

**Expected:** 0 matches  
**Actual:** 0 matches (clean)

---

## 8. Forbidden Pattern Check

Command: `grep -rn "system.projects" src/projects/`

**Expected:** 0 matches  
**Actual:** 0 matches (clean)

---

## 9. Default UUID Presence

Command: `grep -rn "00000000-0000-0000-0000-000000000001" src/projects/registry.py`

**Expected:** >= 1 match  
**Actual:** 2 matches (docstring + constant assignment)

---

## 10. Import Check

Command: `python -c "import src.projects.registry; print('import OK')"`

**Expected:** `import OK`  
**Actual:** ``import OK``

---

## 11. Test Results

Command: `python -m pytest tests/projects/test_registry.py -v`

**Expected:** All tests pass (exit 0)  
**Actual:** 50 passed in 3.00s (exit 0)

---

## 12. Verdict

- [X] **PASS** — All criteria satisfied.
- [ ] FAIL — One or more criteria unmet (see notes below).

**Notes:** None.  Default project seeding, audit hooks, type safety, and
50/50 tests all pass.  The only warnings are harmless Python 3.14 asyncio
deprecation notices (out of scope for P19-002).

---

**Signed:** Faiz (sub-agent) **Date:** 2026-06-25
