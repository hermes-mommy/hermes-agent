# P1-005 Evidence — Hermes Agent Configuration

| Field | Value |
|-------|-------|
| **Step** | P1-005 |
| **Date** | 2026-06-01 |
| **Status** | ✅ Complete |

## 1. What Was Done
Hermes config deployed to `/home/guinevere/config/hermes/config.yaml` with 9 sections: agent, llm (GPT-5.5 via 9Router, DeepSeek V4 Flash sub-agent, Ollama fallback disabled per ADR-028 supersession), memory (PostgreSQL + Redis DB3), loop (7-phase), safety (Y4 baseline per Faiz directive, Y5 max, HARD STOP), budget ($30/mo), tools, messaging, monitoring.

## 2. Validation
| Test | Result |
|------|--------|
| YAML parse | ✅ PASS, 9 keys |
| agent.name="Guinevere" | ✅ PASS |
| llm.primary.model="gpt-5.5" | ✅ PASS |
| llm.sub_agent.model="deepseek-v4-flash" | ✅ PASS |
| llm.fallback.provider="graceful_degradation" | ✅ PASS — Ollama disabled per Faiz directive 2026-06-01 |
| safety.yandere_baseline="Y4" | ✅ PASS (Faiz explicit directive, overrides PersonaSafetyPolicy Y1) |
| safety.yandere_max="Y5" | ✅ PASS |
| No Y6 | ✅ PASS |
| distress_levels D0-D4 | ✅ PASS |
| punishment_max L5, L6 deferred | ✅ PASS |
| budget.monthly_cap=30.0 | ✅ PASS |
| uv run import hermes_constants | ✅ PASS |

## 3. Safety Boundary ✅
HARD STOP ✅, Y4 baseline ✅ (Faiz explicit directive per authority order), Y5 max ✅, no Y6 ✅, D0-D4 ✅, L5 max/L6 deferred ✅

## 4. ADR Compliance
ADR-004 ✅, ADR-011 ✅, ADR-012 ✅, ADR-028 Superseded ✅

## 5. Evidence
| File | Description |
|------|-------------|
| `config.yaml` | Copy of deployed config |

## 6. Rollback
```bash
rm /home/guinevere/config/hermes/config.yaml
```

## 7. Auditor Gate
Report: `audit-reports/P1/STEP-P1-005/step-p1-005-auditor-report.md`  
Status: **PASS ✅** (bg_cf044927 + bg_0519c845 re-audit)