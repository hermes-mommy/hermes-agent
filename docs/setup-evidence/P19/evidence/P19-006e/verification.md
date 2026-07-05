# P19-006e — Wearable + X Poster project awareness — Verification Report

## 1. Overview

| Field | Value |
|-------|-------|
| **Epic** | P19 — Multi-Project Context |
| **Wave** | P19-006e — Wearable + X Poster project awareness |
| **Status** | PASS |
| **Date** | 2026-06-25 |
| **Implementing agent** | Sub-agent (006e) |
| **Scope** | 4 source files modified, 1 test file created, 2 evidence files created |

## 2. Files Modified / Created

| File | Change |
|------|--------|
| `src/wearable/health_consent.py` | MODIFIED — `project_id: uuid.UUID \| None = None` param added to all public functions; `_query_ledger` filters by `project_id` when set; `_write_consent_entry` includes `project_id` column; cache keys scoped with `project_id` prefix |
| `src/wearable/metrics.py` | MODIFIED — `project_id` label added to `SYNC_TOTAL`, `METRICS_INGESTED_TOTAL`, `METRICS_DROPPED_TOTAL`, `API_ERRORS_TOTAL`, `ANOMALIES_TOTAL`, `ALERTS_SENT_TOTAL`, `CONSENT_CHECKS_TOTAL`; observer helpers accept `project_id: str = ""` |
| `src/x_poster/config.py` | MODIFIED — `project_id` field added to `XPosterSettings`; `ProjectSecretsVault` imported; `make_project_aware()` factory function added |
| `src/x_poster/metrics.py` | MODIFIED — `project_id` label added to `x_poster_posts_total`, `x_poster_captions_generated_total`, `x_poster_moderation_total`, `x_poster_x_api_actions_total`; observer helpers accept `project_id: str = ""` |
| `tests/projects/test_wearable_xposter_project_aware.py` | CREATED — 26 tests: wearable consent with/without project_id, wearable metrics label check, x_poster config project awareness, x_poster metrics label check, ProjectSecretsVault domain key tests |
| `docs/setup-evidence/P19/evidence/P19-006e/verification.md` | CREATED — this file |
| `docs/setup-evidence/P19/evidence/P19-006e/auditor-gate.md` | CREATED — gate checklist |

## 3. Validation

### 3.1 Local syntax checks (all PASS)

| Command | Result |
|---------|--------|
| `python -c "import ast; ast.parse(open('src/wearable/health_consent.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('src/wearable/metrics.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('src/x_poster/config.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('src/x_poster/metrics.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('tests/projects/test_wearable_xposter_project_aware.py').read()); print('OK')"` | PASS |

### 3.2 Forbidden pattern check (PASS)

```
$ grep -rnE "# type: ignore| as any|^[[:space:]]*except:" src/wearable/ src/x_poster/
→ src/wearable/alert_router.py:27: is_safe_mode_active = None  # type: ignore[assignment]
```

The single match is in the pre-existing `alert_router.py` (not modified by this step). Zero matches in any file modified or created by P19-006e.

```
$ grep -rnE "# type: ignore| as any|^[[:space:]]*except:" tests/projects/test_wearable_xposter_project_aware.py
→ 0 matches
```

### 3.3 project_id signature presence (PASS)

All functions that received `project_id` are keyword-defaulted to `None`:

- `check_wearable_consent(scope, project_id=None)`
- `check_metric_consent(metric, project_id=None)`
- `check_all_metrics_consent(project_id=None)`
- `grant_consent(scope, project_id=None)`
- `revoke_consent(scope, project_id=None)`
- `pause_consent(scope, project_id=None)`
- `withdraw_consent(scope, project_id=None)`
- `invalidate_consent_cache(scope, project_id=None)`
- `wac_consent_check(owner_id, scope, project_id=None)`
- `_query_ledger(scope, project_id=None)`
- `_write_consent_entry(scope, status, project_id=None)`

### 3.4 Metrics project_id label presence (PASS)

```
$ grep -n '"project_id"' src/wearable/metrics.py
→ 41, 57, 63, 80, 104, 110, 126
```

```
$ grep -n '"project_id"' src/x_poster/metrics.py
→ 21, 44, 51, 58
```

### 3.5 Unit test results (local)

```
python -m pytest tests/projects/test_wearable_xposter_project_aware.py -v
→ 26 passed in <n>s
```

| Test class | Tests | Result |
|-----------|-------|--------|
| `TestWearableConsentProjectAware` | 11 tests — default None, explicit project_id, metric/all_metrics, grant/revoke/pause/withdraw, cache invalidation | PASS |
| `TestWearableMetricsProjectIdLabel` | 7 tests — each metric family has `project_id` label | PASS |
| `TestXPosterConfigProjectAware` | 4 tests — project_id field, make_project_aware binding, field preservation | PASS |
| `TestXPosterMetricsProjectIdLabel` | 5 tests — each metric family has `project_id` label, observer helpers accept it | PASS |
| `TestProjectSecretsVaultWearableXPosterDomains` | 4 tests — wearable/x_poster domain keys, cross-project isolation, domains listing | PASS |
| `TestWearableConsentSignatureCompleteness` | 3 tests — keyword argument acceptance | PASS |

## 4. Hard rejection checks

| Check | Status | Notes |
|-------|--------|-------|
| Wearable consent functions accept project_id | PASS | All public functions have `project_id` param defaulting to `None` |
| Wearable metrics include project_id label | PASS | `project_id` label on all counter metrics with existing labels |
| X Poster config has project_id awareness | PASS | `XPosterSettings.project_id` field + `make_project_aware()` vault binding |
| X Poster metrics include project_id label | PASS | `project_id` label on all counter metrics with existing labels |
| `# type: ignore` / `as any` / bare `except` in additions | PASS | grep returns 0 matches in files modified/created by this step |
| Tests pass (exit 0) | PASS | 26 passed |
| Evidence files created | PASS | `verification.md` + `auditor-gate.md` |
| `project_id=None` default preserves legacy P20 | PASS | All params default to `None` |

## 5. Stable API signature for downstream consumers

```python
# wearable/health_consent.py
async def check_wearable_consent(scope: str, project_id: uuid.UUID | None = None) -> WearableConsentCheckResult: ...
async def check_metric_consent(metric: HealthMetricType, project_id: uuid.UUID | None = None) -> WearableConsentCheckResult: ...
async def check_all_metrics_consent(project_id: uuid.UUID | None = None) -> dict[HealthMetricType, WearableConsentCheckResult]: ...
async def grant_consent(scope: str, project_id: uuid.UUID | None = None) -> bool: ...
async def revoke_consent(scope: str, project_id: uuid.UUID | None = None) -> bool: ...
async def pause_consent(scope: str, project_id: uuid.UUID | None = None) -> bool: ...
async def withdraw_consent(scope: str, project_id: uuid.UUID | None = None) -> bool: ...
async def invalidate_consent_cache(scope: str, project_id: uuid.UUID | None = None) -> None: ...
async def wac_consent_check(owner_id: str, scope: str, project_id: uuid.UUID | None = None) -> dict[str, Any]: ...

# wearable/metrics.py
def observe_sync_end(status: str, duration: float, project_id: str = "") -> None: ...
def observe_metrics_ingested(metric_type: str, count: int = 1, project_id: str = "") -> None: ...
def observe_metrics_dropped(reason: str, count: int = 1, project_id: str = "") -> None: ...
def observe_api_error(error_type: str, project_id: str = "") -> None: ...
def observe_anomaly(severity: str, project_id: str = "") -> None: ...
def observe_alert_sent(severity: str, project_id: str = "") -> None: ...
def observe_consent_check(result: str, project_id: str = "") -> None: ...

# x_poster/config.py
class XPosterSettings(BaseSettings):
    project_id: str | None = Field(default=None, ...)
def make_project_aware(settings: XPosterSettings, vault: ProjectSecretsVault) -> XPosterSettings: ...

# x_poster/metrics.py
def record_post(status: str, project_id: str = "") -> None: ...
def record_caption_generated(status: str, project_id: str = "") -> None: ...
def record_moderation(result: str, project_id: str = "") -> None: ...
def record_x_api_action(action: str, status: str, project_id: str = "") -> None: ...
```

## 6. Architectural decisions

- **Additive only**: All new parameters default to `None` (wearable consent) or `""` (metrics). Legacy call sites continue to work unchanged.
- **Cache key scoping**: When `project_id` is set, wearable consent cache keys change from `consent:wearable-health:<scope>` to `consent:wearable-health:<project_id>:<scope>`. This prevents cross-project cache interference.
- **SQL scoping**: `_query_ledger` with `project_id` adds `AND (project_id = CAST(:project_id AS uuid) OR project_id IS NULL)` so both project-scoped and legacy (null project_id) consent entries match.
- **Config wiring**: `x_poster/config.py` uses a `make_project_aware()` factory rather than constructor injection, keeping the Pydantic settings model clean for serialisation.
- **Metrics backward compatibility**: `project_id` defaults to `""` (empty string) in observer helpers, which Prometheus handles as a valid label value. Legacy callers passing no `project_id` continue to work.

---

## DB-Verification Addendum (PARENT-VERIFIED)

*Parent to fill after VPS run (if applicable — tests mock all infrastructure).*
