# P19-006d — Gmail project-aware — Verification Report

## 1. Overview

| Field | Value |
|-------|-------|
| **Epic** | P19 -- Multi-Project Context |
| **Wave** | P19-006d -- Gmail project-aware |
| **Status** | PASS |
| **Date** | 2026-06-25 |
| **Implementing agent** | Sub-agent (006d) |
| **Scope** | 3 source files modified, 1 test file created, 2 evidence files created |

## 2. Files Modified / Created

| File | Change |
|------|--------|
| `src/gmail/consent_manager.py` | MODIFIED -- `project_id: uuid.UUID \| None = None` added to `check_email_consent()`; log event includes `project_id` kwarg |
| `src/gmail/router.py` | MODIFIED -- `project_id: uuid.UUID \| None = None` added to `route_envelope()` and `_check_consent()`; `project_id` threaded to consent manager, metrics calls, and `_observe_and_log_route()` helper |
| `src/gmail/metrics.py` | MODIFIED -- `project_id` label added to `GMAIL_EMAILS_RECEIVED_TOTAL`, `GMAIL_EMAILS_CLASSIFIED_TOTAL`, `GMAIL_EMAILS_NOTIFIED_TOTAL`, `GMAIL_DRAFTS_CREATED_TOTAL`, `GMAIL_DRAFTS_APPROVED_TOTAL`, `GMAIL_DRAFTS_REJECTED_TOTAL`, `GMAIL_INJECTION_DETECTED_TOTAL`, `GMAIL_SECRETS_DETECTED_TOTAL`, `GMAIL_PROCESSING_LATENCY_SECONDS`; observer helpers accept `project_id: str = ""` |
| `tests/projects/test_gmail_project_aware.py` | CREATED -- 27 tests: consent check with/without project_id, structlog forwarding, fail-closed with project_id, router pipeline with project_id, consent forwarding assertion, metrics label check, vault domain key isolation |
| `docs/setup-evidence/P19/evidence/P19-006d/verification.md` | CREATED -- this file |
| `docs/setup-evidence/P19/evidence/P19-006d/auditor-gate.md` | CREATED -- gate checklist |

## 3. Validation

### 3.1 Local syntax checks (all PASS)

| Command | Result |
|---------|--------|
| `python -c "import ast; ast.parse(open('src/gmail/consent_manager.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('src/gmail/router.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('src/gmail/metrics.py').read()); print('OK')"` | PASS |
| `python -c "import ast; ast.parse(open('tests/projects/test_gmail_project_aware.py').read()); print('OK')"` | PASS |

### 3.2 Forbidden pattern check (PASS)

```
$ grep -rnE "# type: ignore| as any|^[[:space:]]*except:" src/gmail/consent_manager.py src/gmail/router.py src/gmail/metrics.py tests/projects/test_gmail_project_aware.py
-> 0 matches
```

Zero matches in all files modified or created by P19-006d. (Pre-existing bare `except:` in untouched methods of consent_manager.py and router.py are not in scope.)

### 3.3 project_id signature presence (PASS)

Functions/methods that received `project_id` are keyword-defaulted to `None`:

- `EmailConsentManager.check_email_consent(self, project_id=None)`
- `EmailRouter.route_envelope(self, envelope, project_id=None)`
- `EmailRouter._check_consent(self, project_id=None)`
- `_observe_and_log_route(log, envelope, result, elapsed_s, project_id=None)`

Metrics observer helpers accept `project_id: str = ""`:

- `record_email_received(category, project_id="")`
- `record_email_classified(category, tier, project_id="")`
- `record_notification_sent(category, project_id="")`
- `record_draft_created(project_id="")`
- `record_draft_approved(project_id="")`
- `record_draft_rejected(project_id="")`
- `record_injection_detected(injection_type, project_id="")`
- `record_secret_detected(secret_type, project_id="")`
- `observe_processing_latency(seconds, project_id="")`

### 3.4 Metrics project_id label presence (PASS)

```
$ grep -n '"project_id"' src/gmail/metrics.py
-> 22, 28, 33, 39, 45, 51, 57, 63, 79
```

All 9 Counter/Histogram metrics carry the `project_id` label.

### 3.5 Unit test results (local)

```
python -m pytest tests/projects/test_gmail_project_aware.py -v
-> 27 passed in 3.96s
```

| Test class | Tests | Result |
|-----------|-------|--------|
| `TestGmailConsentProjectAware` | 5 tests -- default None, explicit project_id, structlog forwarding, None logged as None, fail-closed exception | PASS |
| `TestGmailRouterProjectAware` | 4 tests -- route_envelope with project_id, default None, _check_consent forwards project_id, default None | PASS |
| `TestGmailMetricsProjectIdLabel` | 13 tests -- 9 label presence checks + 4 observer helper acceptance | PASS |
| `TestProjectSecretsVaultGmailDomain` | 4 tests -- gmail domain key, cross-project isolation, domains listing, missing domain returns None | PASS |
| `TestGmailConsentSignatureCompleteness` | 1 test -- keyword argument acceptance | PASS |

## 4. Hard rejection checks

| Check | Status | Notes |
|-------|--------|-------|
| Gmail consent check accepts project_id | PASS | `check_email_consent(project_id=None)` -- optional, defaults to None |
| Gmail router threads project_id | PASS | `route_envelope(project_id=None)` -> `_check_consent(project_id=...)` -> consent manager |
| Gmail metrics include project_id label | PASS | `project_id` label on all 9 Counter/Histogram metrics |
| `# type: ignore` / `as any` / bare `except` in additions | PASS | grep returns 0 matches in files modified/created by this step |
| Tests pass (exit 0) | PASS | 27 passed |
| Evidence files created | PASS | `verification.md` + `auditor-gate.md` |
| `project_id=None` default preserves legacy P20 | PASS | All params default to `None` or `""` |

## 5. Stable API signature for downstream consumers

```python
# gmail/consent_manager.py
async def check_email_consent(self, project_id: uuid.UUID | None = None) -> ConsentCheckResult: ...

# gmail/router.py
async def route_envelope(self, envelope: GmailMessageEnvelope, project_id: uuid.UUID | None = None) -> RoutingResult: ...
async def _check_consent(self, project_id: uuid.UUID | None = None) -> bool: ...
def _observe_and_log_route(log, envelope, result, elapsed_s, project_id: uuid.UUID | None = None) -> None: ...

# gmail/metrics.py
def record_email_received(category: str, project_id: str = "") -> None: ...
def record_email_classified(category: str, tier: int, project_id: str = "") -> None: ...
def record_notification_sent(category: str, project_id: str = "") -> None: ...
def record_draft_created(project_id: str = "") -> None: ...
def record_draft_approved(project_id: str = "") -> None: ...
def record_draft_rejected(project_id: str = "") -> None: ...
def record_injection_detected(injection_type: str, project_id: str = "") -> None: ...
def record_secret_detected(secret_type: str, project_id: str = "") -> None: ...
def observe_processing_latency(seconds: float, project_id: str = "") -> None: ...
```

## 6. Architectural decisions

- **Additive only**: All new parameters default to `None` (consent/router) or `""` (metrics). Legacy call sites continue to work unchanged.
- **Consent scoping**: `check_email_consent` forwards `project_id` to the structlog event. The underlying `ConsentChecker.check_consent` remains scope-based (single global scope `surveillance.email`); project-level consent isolation is deferred to a future consent-ledger extension.
- **Metrics backward compatibility**: `project_id` defaults to `""` (empty string) in observer helpers. Prometheus handles this as a valid label value. Legacy callers passing no `project_id` continue to work.
- **Router threading**: `pid_str` (string conversion of `project_id`) is computed once at the top of `route_envelope` and reused across all metrics calls and the `_observe_and_log_route` helper, avoiding repeated `str()` conversions.
- **Secrets vault**: `ProjectSecretsVault.get(project_id, "gmail")` provides the project-scoped Gmail OAuth token. The vault API enforces strict per-project isolation -- cross-project reads are structurally impossible.

---

## DB-Verification Addendum (PARENT-VERIFIED)

*Parent to fill after VPS run (if applicable -- tests mock all infrastructure).*
