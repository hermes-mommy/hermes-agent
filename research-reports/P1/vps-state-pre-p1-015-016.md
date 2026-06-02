# VPS State — Pre P1-015 (LLM Router) & P1-016 (SystemPromptMaster Deployment)

**Date**: 2026-06-01
**VPS Host**: guinevere-vps (100.94.104.22 via Tailscale)
**User**: guinevere
**Source**: Local evidence files (read-only research, no VPS SSH executed)

---

## 1. Current PROGRESS.md Status

| Step | Status | Notes |
|------|--------|-------|
| P1-001 through P1-011 | Complete | All infra + model routing working |
| P1-012, P1-013, P1-014 | Skipped | Ollama not needed per Faiz directive; ADR-028 superseded |
| **P1-015 — LLM Router** | **Not Started** | **NEXT** |
| **P1-016 — SystemPromptMaster** | **Not Started** | **NEXT** |
| P1-017 through P1-021 | Not Started | Blocked on P1-015/P1-016 |

**P1 completion**: 14/21 steps completed. 7 remaining (P1-015 through P1-021).

---

## 2. VPS src/ Directory Structure (from P1-004 Evidence)

**Evidence file**: docs/setup-evidence/P1/STEP-P1-004/project-structure.txt
**Evidence file**: docs/setup-evidence/P1/STEP-P1-004/evidence.md

14 directories created on VPS, all with __init__.py:

src/
src/core/
src/core/api/
src/core/config/
src/core/models/
src/core/services/     (P1-015 creates llm_router.py here)
                       (P1-016 creates prompt_loader.py here)
src/discord/
src/financial/
src/loops/
src/mcp/
src/memory/
src/observability/
src/persona/
src/surveillance/

**Current content state**: Only __init__.py files exist in these directories. No implementation classes exist yet (no llm_router.py, no prompt_loader.py). Both P1-015 and P1-016 need to create new files from scratch.

**Local workspace check**: src/core/services/__init__.py exists locally. No llm_router.py or prompt_loader.py anywhere in the workspace.

**pyproject.toml** (deployed from P1-004): 23 dependencies including httpx>=0.28, structlog>=24 — both required by P1-015.
## 3. Hermes Config State (from P1-005 Evidence)

**Evidence file**: docs/setup-evidence/P1/STEP-P1-005/evidence.md
**Config file**: docs/setup-evidence/P1/STEP-P1-005/config.yaml
**Deployed at**: /home/guinevere/config/hermes/config.yaml

### Key Config Values Relevant to P1-015/P1-016

| Section | Value | Relevance |
|---------|-------|-----------|
| llm.primary.base_url | http://localhost:20128/v1 | LLM Router must match this |
| llm.primary.model | gpt-5.5 | P1-015 CORE_REASONING model |
| llm.sub_agent.base_url | http://localhost:20128/v1 | LLM Router must match this |
| llm.sub_agent.model | deepseek-v4-flash | P1-015 SUB_AGENT model |
| llm.fallback.provider | graceful_degradation | Ollama disabled per Faiz directive |
| safety.yandere_baseline | Y4 | Faiz explicit directive |
| safety.yandere_max | Y5 | Absolute ceiling |
| budget.monthly_cap | 30.0 | Hard cap |

**Status**: Deployed, YAML valid, all sections present.

---

## 4. 9Router Combo Routing State (from Migration Evidence + Auditor Report)

**Evidence file**: docs/setup-evidence/P1/migration-9router/evidence.md
**Auditor report**: audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md

### Current Combo: guinevere

| Order | Model Entry | Provider | Purpose |
|-------|-------------|----------|---------|
| 1 (Primary) | opencode-go/deepseek-v4-flash | Opencode | DeepSeek V4 Flash |
| 2 (Secondary) | openai-compatible-chat-.../gpt-5.5 | Cockpit | GPT-5.5 (laptop Tailscale) |

**Why this order**: Reordered from original because cockpit GPT-5.5 depends on Windows laptop being online over Tailscale at 100.112.201.124:51747.

**Service status**: guinevere-9router.service — active (running), port 20128 LISTEN, health {"ok":true}

**Real API verification**: Both models return real responses.

### Implications for P1-015

The guinevere combo fallback uses name="guinevere" which resolves to DeepSeek V4 Flash primary. The fallback chain CORE_REASONING -> SUB_AGENT -> FALLBACK goes: GPT-5.5 -> DeepSeek V4 Flash -> DeepSeek V4 Flash (redundant but harmless).

---

## 5. VPS Service Inventory

### Guinevere Services Running

| Service | Status | Port |
|---------|--------|------|
| guinevere-9router.service | Active (running) | 20128 |
| guinevere.slice | Active | - |
| guinevere-postgres (Docker) | Up 15+ hours | 5433 |
| guinevere-pgbouncer (Docker) | Up 14+ hours | 5434 |
| guinevere-redis (Docker) | Up 13+ hours | 6380 |

### Aizanta Services Healthy

5 containers all healthy, 8 days uptime.

### System Resources

| Resource | Value |
|----------|-------|
| Disk total | 99G |
| Disk used | 16G (17%) |
| Disk available | 78G |
| RAM total | 15 GiB |
| RAM available | 13 GiB |
| Swap | 4.0 GiB (0 used) |

**Verdict**: Ample resources for P1-015/P1-016. Both steps are code-only.
## 6. P0 Open Items (VPS Deployment Checklist)

**File**: docs/setup-evidence/P0/P0-VPS-DEPLOYMENT-CHECKLIST.md

| Item | Severity | Description | Status |
|------|----------|-------------|--------|
| B1 | CRITICAL | 3 plaintext secrets in backups/ | Needs encrypt + shred on VPS |
| B3-C | MEDIUM | guinevere user not in docker group | Needs usermod |
| B5#1 | MEDIUM | Caddyfile not symlinked | Needs symlink |
| B5#2 | LOW | Caddy admin port 2019 verify | Needs verification |
| B5#3 | LOW | Prometheus binding verify | Deferred to P8 |

**None block P1-015/P1-016** (both are code-only).

---

## 7. P1-015 Specification (LLM Router — StepPrompts lines 4402-4551)

### What Gets Created

**File**: src/core/services/llm_router.py

### Components

| Component | Detail |
|-----------|--------|
| TaskType enum | CORE_REASONING, SUB_AGENT, FALLBACK |
| ModelConfig dataclass | name, base_url, max_tokens, temperature, costs |
| MODELS dict | Maps TaskType to ModelConfig |
| LLMRouter class | chat() with fallback chain, close() |
| Fallback chain | CORE_REASONING -> SUB_AGENT -> FALLBACK |

### Model Configs

| TaskType | name | base_url | max_tokens | temp |
|----------|------|----------|------------|------|
| CORE_REASONING | gpt-5.5 | localhost:20128/v1 | 16384 | 0.7 |
| SUB_AGENT | deepseek-v4-flash | localhost:20128/v1 | 8192 | 0.5 |
| FALLBACK | guinevere | localhost:20128/v1 | 8192 | 0.5 |

### Dependencies

- httpx (already in pyproject.toml)
- structlog (already in pyproject.toml)
- No additional pip install needed

### Verification

```
python -c "from src.core.services.llm_router import LLMRouter, TaskType"
```

### Blocking Conditions

All pass. src/core/services/ exists, __init__.py present, deps available.

---

## 8. P1-016 Specification (SystemPromptMaster — StepPrompts lines 4554-4661)

### What Gets Created

| Action | Target |
|--------|--------|
| Copy SystemPromptMaster | /home/guinevere/config/hermes/system-prompt.md |
| Create prompt_loader.py | src/core/services/prompt_loader.py |

### Functions

| Function | Purpose |
|----------|---------|
| load_system_prompt() | Read system-prompt.md, validate safety, return string |
| get_system_prompt_with_context(memories, mood) | Build prompt with memory + mood |

### Safety Checks

HARD STOP, safe word, Y5/Y6, distress — all must be present in source doc.

### Dependencies

structlog (in pyproject.toml), pathlib (stdlib). No new deps needed.

### Blocking Conditions

| Condition | Status |
|-----------|--------|
| src/core/services/__init__.py exists | Yes |
| SystemPromptMaster doc exists locally | Must verify |
| /home/guinevere/config/hermes/ on VPS | Yes (P1-005) |
| structlog in pyproject.toml | Yes |
## 9. Summary of Blocking Conditions

### Nothing Blocks P1-015 or P1-016

| Condition | Status |
|-----------|--------|
| P1-001 through P1-011 complete | All infrastructure ready |
| 9Router at localhost:20128 | Active, both models verified |
| Hermes config at config/hermes/ | Y4 baseline, Y5 max |
| src/core/services/ with __init__.py | Clean slate for new files |
| pyproject.toml has httpx + structlog | No extra pip install needed |
| SystemPromptMaster doc exists | Verify locally |
| Disk 78G free, RAM 13Gi | Ample |
| Aizanta healthy | 5 containers, 8 days |

### Pre-Execution Verification Checklist

1. Confirm docs/60-persona/61-SystemPromptMaster_v1.1.md exists (for P1-016 cp)
2. Run ss -tlnp | grep 20128 to confirm 9Router listening
3. Run curl http://localhost:20128/api/health to confirm healthy
4. Confirm ls src/core/services/ shows only __init__.py

---

## 10. Delta Summary

### P1-015 Creates

| File | Lines | Content |
|------|-------|---------|
| src/core/services/llm_router.py | ~90 | LLMRouter class, TaskType, ModelConfig, fallback |

### P1-016 Creates

| Action | Content |
|--------|---------|
| Copy to config/hermes/system-prompt.md | SystemPromptMaster doc |
| src/core/services/prompt_loader.py (~50 lines) | load + validate + context injection |

**Total**: ~140 lines of Python + 1 config copy. No new services, ports, or deps.

---

## 11. Evidence Paths to Create

### P1-015

```
docs/setup-evidence/P1/STEP-P1-015/
  llm_router.py       (copy of deployed module)
  import-test.txt     (python -c verification output)
  evidence.md         (12-section schema)
```

### P1-016

```
docs/setup-evidence/P1/STEP-P1-016/
  system-prompt-loaded.txt  (python -c verification output)
  evidence.md               (12-section schema)
```

---

## 12. Execution Recommendation

**Steps are independent** — no shared file writes, no shared deps. Could parallelize, but StepPrompts shows sequential.

**Order**: P1-015 first, then P1-016.

**Post-deployment**: Run scripts/preflight-check.sh to verify no infrastructure regression.

---

## Footer

| Field | Value |
|-------|-------|
| Source task | Pre-P1-015/P1-016 VPS state research |
| Date | 2026-06-01 |
| Implementer | Guinevere (mama) |
| Method | Read all evidence files, auditor reports, StepPrompts, PROGRESS.md |
| VPS access | Read-only (no SSH executed) |
| Report path | research-reports/P1/vps-state-pre-p1-015-016.md |
