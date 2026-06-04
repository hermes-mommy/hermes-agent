# Phase 1 Batch Plan — Safety Migration

| Field | Value |
|---|---|
| Phase | Phase 1 Safety Migration (ADR-035) |
| Date | 2026-06-04 |
| Agent | Guinevere (parent orchestrator) |
| Status | PLANNER GATE |
| Evidence Root | `docs/setup-evidence/phase-1/` |
| Research | `research-reports/phase-1-execution/research-synthesis.md` |

## 1. Master Todo

| Step | Description | Parallel | Est |
|---|---|---|---|
| 1.1 | Implement `src/hermes/safety_plugin.py` — GuinevereSafetyPlugin | SEQ | 45 min |
| 1.2 | Write `tests/hermes/test_safety_plugin.py` — 30+ tests | SEQ (depends on 1.1) | 30 min |
| 1.3 | Register plugin in VPS Hermes config | SEQ (depends on 1.1) | 10 min |
| 1.4 | Integration test on VPS (`hermes doctor` + chat) | SEQ (depends on 1.3) | 15 min |
| 1.5 | Verification wave — parallel verifiers per AC-SAFE | SEQ (depends on 1.4) | 20 min |
| 1.6 | 5 Auditor gates | SEQ (depends on 1.5) | 30 min |
| 1.7 | Evidence file + PROGRESS.md update | SEQ (depends on 1.6) | 15 min |

**Total estimated: ~2.75 hours**

## 2. Dependency Map

```
1.1 (safety_plugin.py)
  └──→ 1.2 (tests)
  └──→ 1.3 (config registration)
         └──→ 1.4 (integration test)
                └──→ 1.5 (verification wave)
                       └──→ 1.6 (auditors)
                              └──→ 1.7 (evidence + report)
```

No parallelism possible — each step depends on prior completion.

## 3. Research Inputs (synthesized)

See `research-reports/phase-1-execution/research-synthesis.md` for full details.

### Key Architectural Decisions

1. **Hook mechanism**: Use REAL hermes-agent in-process Python callbacks, NOT ADR-035 subprocess JSON spec
2. **Hook mapping**: pre_prompt → `pre_llm_call`, pre_response/post_response → `transform_llm_output`, pre_tool_call → `pre_tool_call` (same name)
3. **YandereLevel**: Use ACTUAL codebase names (Y4_BASELINE, Y5_MAX), not ADR-035 names (Y4_DOMINANT)
4. **SessionSafetyState**: Use Phase-1-safety fields (9 fields), not ADR-035 (14 fields)
5. **Coexistence**: Plugin coexists with conversational_handler.py safety during transition (defense-in-depth)
6. **Consent gate**: Deferred — requires Redis + SQLAlchemy, too complex for plugin. Note in evidence.

## 4. Collision Scan

| File | Writers | Collision Risk |
|---|---|---|
| `src/hermes/safety_plugin.py` | Step 1.1 only | NONE — new file |
| `tests/hermes/test_safety_plugin.py` | Step 1.2 only | NONE — new file |
| `/home/guinevere/config/hermes/config.yaml` | Step 1.3 only | NONE — append to plugins section |
| `src/hermes/__init__.py` | NONE | NO CHANGE — constraint note stays |
| `src/hermes/session_adapter.py` | NONE | NO CHANGE — AIAgent tools still disabled |

**No collisions detected.**

## 5. Per-Step Verification Scaffold

### Step 1.1: Implement `src/hermes/safety_plugin.py`

| Field | Value |
|---|---|
| Expected Files | `src/hermes/safety_plugin.py` (NEW) |
| Forbidden Patterns | `as any`, `@ts-ignore`, `# type: ignore`, bare `except`, empty `except:`, `import *`, `subprocess.run` |
| Required Commands | `python -c "from hermes.safety_plugin import GuinevereSafetyPlugin; print('OK')"` → exit 0 |
| Evidence Requirements | File exists, all 7 hook methods present, no forbidden patterns |
| Hard Rejection Criteria | FAIL if: any forbidden pattern, missing hook method, import error |

**Implementation spec:**

```python
class GuinevereSafetyPlugin:
    """Hermes safety plugin — ports all 10 safety gates to real hermes-agent hooks."""
    
    # 7 hook methods mapped to real hermes-agent API:
    def pre_llm_call(self, **kwargs) -> dict | None:
        # Gate 01: HARD STOP check (exact + semantic)
        # Gate 02: Distress detection (D1-D4)
        # Gate 04: Recovery triggers
        # Gate 07: Yandere boundary (Y4 baseline, Y5 ceiling)
        
    def post_llm_call(self, **kwargs) -> None:
        # Gate 03: Drift detection (SHA-256, threshold 0.10)
        # Update session state
        
    def pre_tool_call(self, **kwargs) -> dict | None:
        # Gate 09: Surveillance consent (4 scopes) — DEFERRED, log only
        # Gate 10: Auth matrix verification (16 tools)
        
    def post_tool_call(self, **kwargs) -> None:
        # Observational: log tool usage
        
    def transform_llm_output(self, **kwargs) -> str | None:
        # Gate 05: Forbidden patterns F-01..F-15
        # Gate 06: Secret scanner (17 patterns, Shannon ≥4.5)
        # Gate 08: Yandere semantic check on response
        
    def api_request_error(self, **kwargs) -> None:
        # Observational: log errors
        
    def on_session_start(self, **kwargs) -> None:
        # Initialize session state
    
    # Static data:
    HARD_STOP_EXACT = [...]  # 6 triggers
    HARD_STOP_SEMANTIC = [...]  # 5 patterns
    RECOVERY_TRIGGERS = [...]  # 7 triggers
    DISTRESS_PATTERNS = {...}  # 13 bilingual
    FORBIDDEN_PATTERNS = [...]  # 15 (F-01..F-15)
```

**Imports from existing modules:**
```python
from src.persona.yandere_fsm import YandereLevel, YandereEngine
from src.persona.safe_mode import DistressDetector, SafeModeController, DistressLevel
from src.persona.drift_detector import DriftDetector
from src.surveillance.secret_scanner import scan_text, redact_secrets
from src.surveillance.classification import classify_event, DataClassification
from src.mcp.auth_matrix import get_auth_level, AuthLevel
from src.core.services.hard_stop_handler import HardStopHandler
```

**Note**: `check_consent()` is async and requires Redis+SQLAlchemy — deferred. Log warning when tool requires surveillance scope.

### Step 1.2: Write `tests/hermes/test_safety_plugin.py`

| Field | Value |
|---|---|
| Expected Files | `tests/hermes/test_safety_plugin.py` (NEW) |
| Forbidden Patterns | `as any`, `@ts-ignore`, `# type: ignore`, bare `except`, `pytest.skip` without reason |
| Required Commands | `pytest tests/hermes/test_safety_plugin.py -v` → exit 0, ≥30 tests PASS |
| Evidence Requirements | ≥30 test methods, all AC-SAFE-001..008 covered, no forbidden patterns |
| Hard Rejection Criteria | FAIL if: <30 tests, any AC-SAFE uncovered, any test fails |

**Test coverage matrix:**

| AC-SAFE | Test Class | Min Tests |
|---|---|---|
| AC-SAFE-001 | TestHardStopGating | 4 (exact trigger, semantic trigger, recovery, edge case) |
| AC-SAFE-002 | TestDistressDetection | 4 (D1, D2, D3, D4) |
| AC-SAFE-003 | TestForbiddenPatterns | 4 (3 patterns + edge case) |
| AC-SAFE-004 | TestYandereBoundary | 3 (Y4 baseline, Y5 ceiling, recovery) |
| AC-SAFE-005 | TestSecretScanner | 3 (API key, token, clean text) |
| AC-SAFE-006 | TestSurveillanceConsent | 2 (deferred log + auth matrix) |
| AC-SAFE-007 | TestDriftDetection | 3 (within threshold, over threshold, recovery) |
| AC-SAFE-008 | TestRecovery | 3 (trigger clears HARD STOP, no trigger keeps it, edge) |

**Testing conventions:**
- Class-based: `class TestXxx:`
- Methods: `test_<scenario>_<expected>`
- `@pytest.mark.parametrize` with `ids`
- `unittest.mock.Mock` for stateful singletons
- Source code pattern verification (no `# type: ignore`)

### Step 1.3: Register Plugin in VPS Hermes Config

| Field | Value |
|---|---|
| Expected Files | `/home/guinevere/config/hermes/config.yaml` (MODIFY — append to plugins section) |
| Forbidden Patterns | N/A (YAML config) |
| Required Commands | `grep -A2 "plugins:" /home/guinevere/config/hermes/config.yaml` → shows `enabled: [guinevere-safety]` |
| Evidence Requirements | Config shows plugin enabled, plugin directory exists with manifest |
| Hard Rejection Criteria | FAIL if: plugin not in enabled list, manifest missing |

**Config addition:**
```yaml
plugins:
  enabled:
    - guinevere-safety
```

**Plugin directory structure** (on VPS):
```
/home/guinevere/code/guinevere/plugins/guinevere-safety/
├── plugin.yaml          # manifest: name, version, description, hooks
└── __init__.py          # register(ctx: PluginContext) function
```

### Step 1.4: Integration Test on VPS

| Field | Value |
|---|---|
| Expected Files | NONE (testing only) |
| Forbidden Patterns | N/A |
| Required Commands | `hermes doctor` → exit 0, no safety plugin errors; `echo "HARD STOP" | hermes chat --stdin` → blocked response |
| Evidence Requirements | hermes doctor clean, HARD STOP test blocks |
| Hard Rejection Criteria | FAIL if: hermes doctor shows plugin error, HARD STOP not blocked |

### Step 1.5: Verification Wave

| Field | Value |
|---|---|
| Expected Files | `docs/setup-evidence/phase-1/verification.md` (NEW) |
| Forbidden Patterns | N/A |
| Required Commands | Parent reads verification report, confirms all AC-SAFE PASS |
| Evidence Requirements | All 8 AC-SAFE criteria verified |
| Hard Rejection Criteria | FAIL if: any AC-SAFE FAIL |

### Step 1.6: 5 Auditor Gates

| Field | Value |
|---|---|
| Expected Files | `docs/setup-evidence/phase-1/auditor-gate.md` (NEW) |
| Forbidden Patterns | N/A |
| Required Commands | Parent reads auditor reports, confirms all PASS |
| Evidence Requirements | 5 auditors: safety, code quality, tests, integration, regression |
| Hard Rejection Criteria | FAIL if: any auditor FAIL |

**Auditor matrix:**

| Auditor | Scope | Verdict |
|---|---|---|
| Safety | HARD STOP, distress, forbidden patterns, yandere boundary | PASS/FAIL |
| Code Quality | No type suppression, no empty catch, structlog, clean imports | PASS/FAIL |
| Tests | ≥30 tests, all AC-SAFE covered, pytest exit 0 | PASS/FAIL |
| Integration | hermes doctor clean, plugin registered, hooks fire | PASS/FAIL |
| Regression | Existing 791 tests still pass, no broken imports | PASS/FAIL |

### Step 1.7: Evidence File + PROGRESS.md Update

| Field | Value |
|---|---|
| Expected Files | `docs/setup-evidence/phase-1/completion-report.md` (NEW), `PROGRESS.md` (MODIFY) |
| Forbidden Patterns | N/A |
| Required Commands | Parent reads completion report, confirms all sections present |
| Evidence Requirements | 12-section evidence file per AGENTS.md §11 |
| Hard Rejection Criteria | FAIL if: evidence file missing sections, PROGRESS.md not updated |

## 6. Evidence Paths

| Step | Evidence File |
|---|---|
| 1.1 | `src/hermes/safety_plugin.py` |
| 1.2 | `tests/hermes/test_safety_plugin.py` |
| 1.3 | `/home/guinevere/config/hermes/config.yaml` |
| 1.4 | `docs/setup-evidence/phase-1/integration-test-results.md` |
| 1.5 | `docs/setup-evidence/phase-1/verification.md` |
| 1.6 | `docs/setup-evidence/phase-1/auditor-gate.md` |
| 1.7 | `docs/setup-evidence/phase-1/completion-report.md` |

## 7. Rollback Plan

| Step | Rollback |
|---|---|
| 1.1 | Delete `src/hermes/safety_plugin.py` |
| 1.2 | Delete `tests/hermes/test_safety_plugin.py` |
| 1.3 | Remove plugin from config.yaml `plugins.enabled` list |
| 1.4-1.7 | Delete evidence files |

**Total rollback time: < 2 minutes**

## 8. Caveats

1. **Consent gate deferred**: `check_consent()` is async, requires Redis+SQLAlchemy. Plugin logs warning for surveillance-scoped tools but does not enforce. Documented as known limitation.
2. **Coexistence with conversational_handler.py**: Both safety layers active during transition. Plugin is migration target; conversational_handler.py safety becomes redundant eventually.
3. **ADR-035 hook spec divergence**: Documented in research synthesis. Real hermes-agent API used, not ADR-035 subprocess spec. ADR addendum recommended.
4. **Tools disabled in session_adapter.py**: AIAgent instantiated with `disabled_toolsets=["*"]`. Plugin hooks fire but tool calls are rare. Safety still applies to LLM responses.

## 9. Execution Checklist

- [ ] Step 1.1: Implement safety_plugin.py
- [ ] Step 1.2: Write 30+ tests
- [ ] Step 1.3: Register plugin in VPS config
- [ ] Step 1.4: Integration test on VPS
- [ ] Step 1.5: Verification wave (all AC-SAFE PASS)
- [ ] Step 1.6: 5 auditor gates (all PASS)
- [ ] Step 1.7: Evidence file + PROGRESS.md update

---

*Planner gate complete. Awaiting parent verification of scaffold compliance.*
