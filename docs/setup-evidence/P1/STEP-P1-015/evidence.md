# P1-015 LLM Routing Rules — Evidence

## What Was Done

Deployed `llm_router.py` to VPS `/home/guinevere/code/guinevere/src/core/services/llm_router.py` (90 lines).

The module implements a three-tier LLM routing layer:
1. **CORE_REASONING** → `gpt-5.5` via 9Router `localhost:20128/v1`
2. **SUB_AGENT** → `deepseek-v4-flash` via 9Router `localhost:20128/v1`
3. **FALLBACK** → `guinevere` combo via 9Router `localhost:20128/v1`

Fallback chain: for CORE_REASONING tasks, primary → sub-agent → guinevere combo. For SUB_AGENT tasks, sub-agent → guinevere combo. All models reachable through a single 9Router endpoint.

## Files Changed

- `src/core/services/llm_router.py` — NEW (90 lines). Contains `TaskType` enum, `ModelConfig` dataclass, `MODELS` dictionary, and `LLMRouter` class with `chat()` and `close()` methods.
- `docs/setup-evidence/P1/STEP-P1-015/llm_router.py` — Evidence copy.

## Validation Results

- ✅ Module created on VPS at `/home/guinevere/code/guinevere/src/core/services/llm_router.py`
- ✅ Import test: `from src.core.services.llm_router import LLMRouter, TaskType` → OK
- ✅ TaskType enum values: `core`, `sub_agent`, `fallback`
- ✅ Model routing: CORE_REASONING → gpt-5.5 @ localhost:20128/v1
- ✅ Model routing: SUB_AGENT → deepseek-v4-flash @ localhost:20128/v1
- ✅ Model routing: FALLBACK → guinevere @ localhost:20128/v1
- ✅ ALL CHECKS PASS

## Evidence Artifacts

- Module source: `src/core/services/llm_router.py`
- Evidence copy: `docs/setup-evidence/P1/STEP-P1-015/llm_router.py`

## Doc-Sync Impact

- PROGRESS.md: P1-015 → pending update
- CHECKLIST.md: P1-015 → pending update

## Boundary Compliance

- No secrets, API keys, or credentials exposed.
- No persona/safety boundary changes.
- No Aizanta impact.
- No new network exposure.

## Rollback / Re-run Safety

```bash
rm /home/guinevere/code/guinevere/src/core/services/llm_router.py
```

Safe to re-run — `cat >` overwrites. `__init__.py` already exists from P1-004.

## Design Decisions / Caveats

- The `FALLBACK` route uses `name="guinevere"` which resolves to the 9Router `guinevere` combo (currently DeepSeek V4 Flash primary, GPT-5.5 cockpit secondary).
- Fallback chain: CORE_REASONING (GPT-5.5) → SUB_AGENT (DeepSeek V4 Flash) → FALLBACK (guinevere combo / DeepSeek V4 Flash primary). The last hop retries DeepSeek through the combo route — redundant for DeepSeek but harmless.
- All models route through a single 9Router endpoint (`localhost:20128/v1`) — no separate provider URLs needed.

## Auditor Gate

Pending. Report path: `audit-reports/P1/STEP-P1-015/step-p1-015-auditor-report.md`

## Footer

- Source task: StepPrompt P1-015
- Date: 2026-06-01
- Implementer: Guinevere / Hephaestus
- Validation method: VPS import test, enum value check, model routing config check