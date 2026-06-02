# Batch Implementation Plan: STEP-P1-004 + STEP-P1-005

| Field | Value |
|---|---|
| **Plan ID** | BATCH-P1-004-005 |
| **Scope** | Hermes Agent Installation & Configuration |
| **Phases** | P1 (LLM + Hermes Agent) |
| **Steps** | P1-004 (Install) → P1-005 (Config) |
| **Status** | ⏳ Planned |
| **Created** | 2026-06-01 |
| **Executor** | Guinevere (mama) + sub-agents |
| **Est. Duration** | 4-6 hours total (2h each + overhead) |

---

## 1. Master Todo Per Step

### STEP P1-004: Hermes Agent Installation (7 todos)

| # | Todo | Delegation | Evidence Path |
|---|---|---|---|
| T4-01 | Install `hermes-agent` via `uv pip install hermes-agent` into venv | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-004/hermes-install.txt` |
| T4-02 | Verify import: `python -c "import hermes_agent; print(hermes_agent.__version__)"` | Execute sub-agent | Same as T4-01 |
| T4-03 | Create `src/` project structure (10 dirs + 10 `__init__.py` files) | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-004/project-structure.txt` |
| T4-04 | Create `src/core/` sub-structure (config/, models/, services/, api/) | Execute sub-agent | Same as T4-03 |
| T4-05 | Write `pyproject.toml` with 23 dependencies + hatchling build system | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-004/pyproject-toml-validated.md` |
| T4-06 | Validate pyproject.toml: `python -c "import tomllib; tomllib.load(...)"` | Parent verify | Same as T4-05 |
| T4-07 | P1-004 implementation auditor gate + evidence write | Auditor sub-agent | `audit-reports/P1/STEP-P1-004/step-p1-004-auditor-report.md` |

**Fallback todos (if pip install fails):**

| # | Todo | Delegation | Evidence Path |
|---|---|---|---|
| T4-F1 | Install from source: `git clone https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent && uv pip install -e .` | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-004/hermes-install.txt` |
| T4-F2 | Cleanup: `rm -rf /tmp/hermes-agent` after successful install | Execute sub-agent | Same as T4-F1 |

### STEP P1-005: Hermes Agent Configuration (6 todos)

| # | Todo | Delegation | Evidence Path |
|---|---|---|---|
| T5-01 | Create `/home/guinevere/config/hermes/` directory | Execute sub-agent | `docs/setup-evidence/P1/STEP-P1-005/hermes-config.yaml` |
| T5-02 | Write `config.yaml` with all sections: agent, llm, memory, loop, safety, budget, tools | Execute sub-agent | Same as above |
| T5-03 | **Yandere baseline verification**: ensure `yandere_baseline: "Y1"` per PersonaSafetyPolicy authority order | Safety auditor | Same as above |
| T5-04 | Validate YAML: `python -c "import yaml; yaml.safe_load(open(...))"` | Parent verify | Same as above |
| T5-05 | Safety boundary checklist: safe_word, yandere_max, distress_levels, punishment_max all match policy | Safety auditor | `docs/setup-evidence/P1/STEP-P1-005/safety-boundary-verify.md` |
| T5-06 | P1-005 implementation auditor gate + evidence write | Auditor sub-agent | `audit-reports/P1/STEP-P1-005/step-p1-005-auditor-report.md` |

---

## 2. Dependency Map

```
P1-003 (.venv + 61 packages)
    │
    ▼
P1-004 (Install Hermes Agent)
    ├── Creates: src/, pyproject.toml
    ├── Requires: .venv activated (P1-003), internet access
    └── Produces: hermes_agent installed in venv
    │
    ▼
P1-005 (Hermes Agent Config)
    ├── Creates: ~/config/hermes/config.yaml
    ├── Requires: P1-004 complete
    └── Produces: valid YAML config for Hermes runtime
```

**Sequential constraint**: P1-004 must complete before P1-005 (no overlap — config depends on install artifacts)

**Prerequisite chain**: P0 complete → P1-001 (Python) → P1-002 (UV) → P1-003 (venv) → P1-004 → P1-005

---

## 3. Prerequisites & Blockers

### Verified Prerequisites

| # | Prerequisite | Status | Check Command |
|---|---|---|---|
| PR-01 | Python 3.12.3 native | ✅ P1-001 | `python3.12 --version` |
| PR-02 | UV 0.11.17 installed | ✅ P1-002 | `uv --version` |
| PR-03 | `.venv` exists at `/home/guinevere/code/guinevere/.venv` | ✅ P1-003 | `ls .venv/bin/python` |
| PR-04 | Venv has 61 packages | ✅ P1-003 | `uv pip list` |
| PR-05 | `src/` does not exist (clean slate) | ✅ Verified | `ls src/` → error |
| PR-06 | `pyproject.toml` does not exist (clean slate) | ✅ Verified | `ls pyproject.toml` → error |
| PR-07 | VPS internet access (HTTPS outbound) | ✅ P0 baseline | `curl -I https://pypi.org` |
| PR-08 | Git available | ✅ P0-025 | `git --version` |
| PR-09 | `/home/guinevere/config/` exists | ✅ P0-003 | `ls /home/guinevere/config/` |
| PR-10 | Per-step auditor skill available | ✅ | `skill("ocs-delegation-gate")` |

### Potential Blockers

| # | Blocker | Trigger | Mitigation |
|---|---|---|---|
| B-01 | PyPI rate limit / network timeout | `uv pip install` fails with timeout | Retry with `--retries 3`; fallback to git clone |
| B-02 | `hermes-agent` not on PyPI (unlikely, v0.15.2 confirmed) | `pip install` returns 404 | Use git clone fallback immediately (no retry loop) |
| B-03 | `pyyaml` not in venv | YAML validation command fails (P1-005 T5-04) | `uv pip install pyyaml` first |
| B-04 | Permission on `/home/guinevere/config/hermes/` | mkdir fails due to permissions | Already guinevere user; check `whoami` first |
| B-05 | Hermes import name mismatch | `import hermes_agent` fails but package installed | Check actual import name with `pip show -f hermes-agent` |
| B-06 | Disk space insufficient for hermes-agent | Fallback git clone (hundreds MB) | Check `df -h /home/guinevere/` first |

---

## 4. Evidence Root Per Step

### P1-004 Evidence

```
docs/setup-evidence/P1/STEP-P1-004/
├── evidence.md                     # Parent evidence (12-section schema)
├── hermes-install.txt              # pip install log + version output
├── project-structure.txt           # `find src -type d` output
└── pyproject-toml-validated.md     # tomllib validation + dependency list
```

### P1-005 Evidence

```
docs/setup-evidence/P1/STEP-P1-005/
├── evidence.md                     # Parent evidence (12-section schema)
├── hermes-config.yaml              # Complete config file (redacted if secrets)
└── safety-boundary-verify.md       # Safety boundary cross-check (safety domain)
```

### Auditor Reports

```
audit-reports/P1/STEP-P1-004/
└── step-p1-004-auditor-report.md   # Independent auditor gate

audit-reports/P1/STEP-P1-005/
└── step-p1-005-auditor-report.md   # Independent auditor gate
```

---

## 5. DoD/AC Per Step

### P1-004 Definition of Done

| # | DoD Item | Verification Command | Expected |
|---|---|---|---|
| D4-01 | Hermes installed | `python -c "import hermes_agent; print(hermes_agent.__version__)"` | Version string (e.g. 0.15.2) |
| D4-02 | `src/` directory exists | `find src -type d` | 10+ directories including core/config/, core/models/, core/services/, core/api/, memory/, persona/, loops/, surveillance/, discord/, mcp/, observability/, financial/ |
| D4-03 | `__init__.py` files exist | `find src -name __init__.py` | 10 files |
| D4-04 | `src/core/` has sub-structure | `ls src/core/` | config/, models/, services/, api/ directories |
| D4-05 | `pyproject.toml` valid | `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` | No exception |
| D4-06 | pyproject.toml has 23 deps | `python -c "d=tomllib.load(open('pyproject.toml','rb')); print(len(d['project']['dependencies']))"` | 23 |
| D4-07 | LSP diagnostics clean | `lsp_diagnostics` on src/ | No errors on new files |
| D4-08 | Evidence files written | `ls docs/setup-evidence/P1/STEP-P1-004/` | evidence.md + artifacts |
| D4-09 | Auditor gate PASS | Read auditor report | PASS verdict |

**Acceptance Criteria**: AC-CORE-001 (core daemon runs as systemd — partial, framework installed), AC-LOOP-001 (7-phase SDLC — partial, loop framework available)

### P1-005 Definition of Done

| # | DoD Item | Verification Command | Expected |
|---|---|---|---|
| D5-01 | Config file exists | `cat /home/guinevere/config/hermes/config.yaml` | Non-empty YAML content |
| D5-02 | YAML valid | `python -c "import yaml; yaml.safe_load(open('/home/guinevere/config/hermes/config.yaml'))"` | No exception |
| D5-03 | LLM primary correct | `grep -A2 'primary:' /home/guinevere/config/hermes/config.yaml \| grep model` | `model: "gpt-5.5"` |
| D5-04 | LLM sub-agent correct | `grep -A2 'sub_agent:' /home/guinevere/config/hermes/config.yaml \| grep model` | `model: "deepseek-v4-flash"` |
| D5-05 | Safe word correct | `grep safe_word /home/guinevere/config/hermes/config.yaml` | `safe_word: "HARD STOP"` |
| D5-06 | Yandere max correct | `grep yandere_max /home/guinevere/config/hermes/config.yaml` | `yandere_max: "Y5"` |
| D5-07 | Yandere baseline correct | `grep yandere_baseline /home/guinevere/config/hermes/config.yaml` | `yandere_baseline: "Y1"` |
| D5-08 | Distress levels correct | `grep distress_levels /home/guinevere/config/hermes/config.yaml` | `distress_levels: ["D0", "D1", "D2", "D3", "D4"]` |
| D5-09 | Punishment max correct | `grep punishment_max /home/guinevere/config/hermes/config.yaml` | `punishment_max: "L5"` |
| D5-10 | LLM base_url points to 9Router | `grep base_url /home/guinevere/config/hermes/config.yaml` | `http://localhost:20128/v1` |
| D5-11 | Memory backend PostgreSQL | `grep backend /home/guinevere/config/hermes/config.yaml` | `backend: "postgresql"` |
| D5-12 | Budget cap correct | `grep monthly_cap /home/guinevere/config/hermes/config.yaml` | `monthly_cap: 30.0` |
| D5-13 | Safety boundary proof | Run safety-boundary-verify.md checklist | All items PASS |
| D5-14 | LSP diagnostics clean | `lsp_diagnostics` on config (YAML lint) | No errors |
| D5-15 | Auditor gate PASS | Read auditor report | PASS verdict |

**Acceptance Criteria**: AC-CORE-003 (GPT-5.5 via 9Router for core reasoning), AC-LOOP-001 (7-phase SDLC)

---

## 6. ADR & Docs Referenced

### ADRs

| ADR | Title | Relevance | Binding Constraints |
|---|---|---|---|
| ADR-004 | Primary LLM Model Selection | P1-004 (framework install), P1-005 (config: llm.primary.model = gpt-5.5) | ✅ Config MUST use GPT-5.5 via 9Router |
| ADR-006 | Sub-Agent LLM Model Strategy | P1-005 (config: llm.sub_agent.model = deepseek-v4-flash) | ✅ Config MUST use DeepSeek V4 Flash |
| ADR-011 | SDLC Loop Phase Specification | P1-004 (loop framework), P1-005 (config: loop.phases = 7) | ✅ Config MUST use 7 phases |
| ADR-012 | Sub-Agent Orchestration Governance | P1-005 (config: tools.auth_matrix) | MUST use file-based sub-agent output pattern |
| ADR-014 | VPS & Container Architecture | P1-004 (install location), P1-005 (config paths) | ✅ All paths under /home/guinevere/ |
| ADR-015 | Secrets Management Strategy | P1-005 (no secrets in config.yaml) | ✅ Config MUST NOT contain API keys in plaintext |
| ADR-028 | LLM Router Outage — Three-Tier Fallback | P1-005 (config: llm.fallback) | ✅ Fallback chain documented in config comments |
| ADR-007 | Memory Storage Backend Selection | P1-005 (config: memory.backend = postgresql) | ✅ MUST use PostgreSQL, not SQLite |
| ADR-030 | Redis DB Assignments | P1-005 (config: memory.redis_db = 3) | ✅ DB3 = loop state per ADR-030 |

### Docs

| Doc | Relevance |
|---|---|
| PersonaSafetyPolicy v1.0 | P1-005 safety config: safe_word, yandere_max, distress_levels, punishment_max, authority order |
| SystemPromptMaster v1.1 | P1-005 persona context; **yandere baseline Y4 vs PersonaSafetyPolicy Y1 — conflict documented below** |
| Persona Document v3.1 | P1-005 identity config; canonical yandere baseline stated as Y4 |
| AgentLoopSpec v2.0 | P1-005 loop config: 7 phases, heartbeat, progress timeout, resource check |
| MemorySchema v2.0 | P1-005 memory config: PostgreSQL, embedding dimensions 1536 |
| Implementation Guide | Execution workflow, evidence conventions |
| CHECKLIST.md | Phase-level verification (§3 Phase 1) |
| AGENTS.md | Sub-agent delegation patterns, auditor gate requirement |

---

## 7. Risk Assessment

| # | Risk | Probability | Severity | Mitigation |
|---|---|---|---|---|
| R-01 | Hermes pip install fails (network/PyPI down) | Low | High | Git clone fallback pre-prepared; agent-framework-alternatives research available |
| R-02 | Hermes import name differs from `hermes_agent` | Low | Medium | Check `pip show -f hermes-agent` for actual module name |
| R-03 | pyproject.toml written with 15 deps instead of 23 | Medium | Medium | Pre-verified dependency list; auditor checks count |
| R-04 | Yandere baseline config incorrectly set to Y4 | Medium | Medium | P1-005 StepPrompt uses Y1; safety auditor must verify |
| R-05 | Config YAML indentation error breaks parser | Low | High | Parent runs `yaml.safe_load` verification |
| R-06 | `pyyaml` not in venv, YAML validation fails | Low | Low | Pre-install `uv pip install pyyaml` in P1-005 |
| R-07 | `/home/guinevere/config/hermes/` exists with stale data | Low | Medium | Check existence first; backup if needed |
| R-08 | Hermes agent has config schema requirements we don't know | Medium | Medium | Review Hermes docs after install; adjust config if needed |
| R-09 | Accidentally committing secrets in evidence files | Low | High | SOPS encrypt/redact; never write API keys to evidence |
| R-10 | Disk space during git clone fallback (>200MB) | Low | Low | Check `df -h /home/guinevere/` before clone |

---

## 8. Gotchas & Edge Cases

### From Research Wave Findings

| # | Gotcha | Detail | Mitigation |
|---|---|---|---|
| G-01 | **pyproject.toml dependency count mismatch** | StepPrompts lists 15 deps; project-structure-audit identifies 23 needed (15 + 7 extras + hermes-agent) | Write 23-dependency pyproject.toml; auditor verifies count |
| G-02 | **Yandere baseline conflict** | PersonaSafetyPolicy context implies Y1 safe baseline; SystemPromptMaster v1.1 §C explicitly states Y4; Persona Document v3.1 says Y4 | Per authority order (PersonaSafetyPolicy > SystemPromptMaster), **use Y1 in config**; document as deliberate decision (see §11) |
| G-03 | **Hermes agent config keys may differ** | Config keys like `yandere_baseline`, `distress_levels` are bespoke Guinevere keys, not standard Hermes schema | Config is a Guinevere wrapper file; Hermes may ignore unknown keys. Accept as metadata artifact |
| G-04 | **No root `.gitignore` exists** | Project-structure-audit found no `.gitignore` at repo root | Create `.gitignore` as part of P1-004 (checklist item) |
| G-05 | **`pyyaml` missing from venv** | Not in P1-003 package list; required for P1-005 YAML validation | Install `pyyaml` before config validation step |
| G-06 | **`src/` name vs `src/guinevere/` convention** | UV research recommends `src/guinevere/` but StepPrompts uses flat `src/` with subdirs (core/, memory/, etc.) | Use StepPrompts convention (`src/core/`, etc.) for alignment with future phases. Can restructure to `src/guinevere/` later |
| G-07 | **Evidence directory for P1-004 and P1-005 already exists?** | Previous partial runs might leave stale evidence | Check before write; overwrite or migrate |
| G-08 | **Hermes Agent v0.15.2 may have breaking changes** | PyPI version may differ from expectation | Use `pip install hermes-agent==0.15.2` for pinned version |
| G-09 | **Hatchling build backend requires hatchling at build time** | pyproject.toml specifies hatchling as build backend | Add `hatchling` to uv pip install list or it will fail on `uv build` |
| G-10 | **Config file at `/home/guinevere/config/hermes/config.yaml` uses 9Router port 20128** | StepPrompts hardcodes port 20128 — verify 9Router is expected at this port | Document that 9Router at port 20128 is installed later (P1-006) |

---

## 9. Delegation Assignment Per Todo

| Todo | Delegated To | Skill/Load | Justification |
|---|---|---|---|
| T4-01 | Execute sub-agent | `task(category='execute', ...)` | Standard pip install, no special skill |
| T4-02 | Execute sub-agent (same as T4-01) | Same task | Verification bundled with install |
| T4-03 | Execute sub-agent (or parent) | `bash` + `filesystem_write_file` | Directory creation + touch; simple enough for parent |
| T4-04 | Same as T4-03 | Same | Part of same file operation batch |
| T4-05 | Implementation sub-agent | `task(category='implementation', ...)` | Multi-line file write; use `filesystem_write_file` |
| T4-06 | Parent verify | — | Simple `python -c` validation |
| T4-07 | Auditor sub-agent | `task(category='auditor', ...)` | Independent audit gate required per AGENTS.md §4 |
| T5-01 | Execute sub-agent (or parent) | `bash` | Single mkdir command |
| T5-02 | Implementation sub-agent | `task(category='implementation', ...)` | Multi-section YAML config; use `filesystem_write_file` |
| T5-03 | Safety auditor sub-agent | `task(category='oracle', ...)` | Safety domain; requires persona/safety context |
| T5-04 | Parent verify | — | Simple `python -c` validation |
| T5-05 | Safety auditor sub-agent (same as T5-03) | Same task | Part of same safety review |
| T5-06 | Auditor sub-agent | `task(category='auditor', ...)` | Independent audit gate |

**Collision note**: T4-05 (pyproject.toml) and T5-02 (config.yaml) write to different files — no collision risk.

---

## 10. Resource/Collision Scan

### Ports

| Port | Service | Conflict Risk |
|---|---|---|
| None | P1-004 (code-only) | ✅ No ports used |
| None | P1-005 (config-only) | ✅ No ports used |

### Filesystem Paths

| Path | Step | Action | Collision Risk |
|---|---|---|---|
| `/home/guinevere/code/guinevere/src/` | P1-004 | CREATE | ✅ Clean slate (does not exist) |
| `/home/guinevere/code/guinevere/pyproject.toml` | P1-004 | CREATE | ✅ Clean slate (does not exist) |
| `/home/guinevere/config/hermes/` | P1-005 | CREATE | ✅ Clean slate (may need mkdir -p) |
| `/home/guinevere/config/hermes/config.yaml` | P1-005 | CREATE | ✅ Clean slate |
| `docs/setup-evidence/P1/STEP-P1-004/` | P1-004 | CREATE | ⚠️ Check if stale |
| `docs/setup-evidence/P1/STEP-P1-005/` | P1-005 | CREATE | ⚠️ Check if stale |
| `audit-reports/P1/STEP-P1-004/` | P1-004 | CREATE | ⚠️ Check if stale |
| `audit-reports/P1/STEP-P1-005/` | P1-005 | CREATE | ⚠️ Check if stale |
| PROGRESS.md | Both | UPDATE | Parent-only edit |
| CHECKLIST.md | Both | UPDATE | Parent-only edit |

### Venv Packages

| Package | Step | Action | Notes |
|---|---|---|---|
| `hermes-agent` | P1-004 | INSTALL | Pinned to v0.15.2 |
| `pyyaml` | P1-005 | INSTALL (if missing) | Required for YAML validation |
| `hatchling` | P1-004 | INSTALL (if missing) | Build backend requirement |

### Shared Writers (Collision Scan)

| File | Writers | Mitigation |
|---|---|---|
| `pyproject.toml` | T4-05 only | Single owner |
| `config.yaml` | T5-02 only | Single owner |
| PROGRESS.md | Parent only after both steps | Sequence |
| `evidence.md` per step | Parent only after each step | Sequence |

---

## 11. Aizanta Impact Analysis

| Impact | Assessment |
|---|---|
| Aizanta services touched? | ❌ No — P1 is code-only until P1-006 (9Router service) |
| Aizanta ports affected? | ❌ No — no ports used |
| Aizanta Docker containers? | ❌ No — P1-004/005 are pure Python + config |
| Aizanta databases? | ❌ No — config references PostgreSQL but doesn't connect |
| Aizanta Redis? | ❌ No — config references DB3 but doesn't connect |
| Aizanta disk contention? | ⚠️ Low — <50MB for hermes-agent + config |
| Aizanta network? | ❌ No |
| Aizanta CPU/memory? | ❌ No — no services started |

**Verdict**: P1-004 and P1-005 have **zero Aizanta impact**. Both are stateless file + package operations.

---

## 12. Secret Handling Plan

| Secret | Exposure Risk | Handling |
|---|---|---|
| API keys in pyproject.toml | None | Not included in dependency list |
| API keys in config.yaml | ⚠️ HIGH | Config MUST NOT contain API keys in plaintext. StepPrompts template has no keys — good. |
| Discord token | None | Not referenced until P2 |
| 9Router keys | None | Not referenced until P1-006 |
| Database passwords | None | Not referenced until P3 |
| GitHub PAT | None | Not referenced |
| Hermes agent auth keys | ⚠️ LOW | Hermes may need OpenRouter key — defer to runtime config |

**Rules enforced**:
- No API keys in config.yaml at this stage
- Evidence redaction: if `sops -d` output is accidentally captured, redact before writing to evidence
- Evidence path: SOPS-encrypted files remain in `/home/guinevere/secrets/` only
- Auditor must check for accidentally exposed secrets in evidence

---

## 13. Destructive Action List

| # | Action | Step | Destructive? | Approval Needed |
|---|---|---|---|---|
| D-01 | `rm -rf /tmp/hermes-agent` | P1-004 fallback | ⚠️ Low (temp dir) | No |
| D-02 | `rm -rf src/` (rollback) | P1-004 rollback | ⚠️ Medium (user code) | Yes — per rollback protocol |
| D-03 | `rm -rf pyproject.toml` (rollback) | P1-004 rollback | ⚠️ Low (single file) | Yes — per rollback protocol |
| D-04 | `rm -rf /home/guinevere/config/hermes/` (rollback) | P1-005 rollback | ⚠️ Medium (config) | Yes — per rollback protocol |
| D-05 | `uv pip uninstall -y hermes-agent` | P1-004 rollback | ⚠️ Low (package) | No (part of rollback) |
| D-06 | `mkdir -p src/` (clean create) | P1-004 | ❌ Not destructive | No |
| D-07 | Overwrite evidence (if stale) | Both | ⚠️ Low (versioned) | No — evidence files are mutable until committed |

**Rule**: No destructive action executes without explicit parent verification and condition check.

---

## 14. Rollback Plan

### P1-004 Rollback

```bash
# Step 1: Uninstall hermes-agent
cd /home/guinevere/code/guinevere
source .venv/bin/activate
uv pip uninstall -y hermes-agent

# Step 2: Remove src/ and pyproject.toml
rm -rf src/ pyproject.toml

# Step 3: Remove evidence
rm -rf docs/setup-evidence/P1/STEP-P1-004/

# Step 4: Remove auditor report
rm -rf audit-reports/P1/STEP-P1-004/

# Step 5: Verify clean slate
ls src/  # expected: "ls: cannot access 'src/': No such file or directory"
ls pyproject.toml  # expected: "ls: cannot access 'pyproject.toml': No such file or directory"
```

**Re-run safety**: P1-004 is idempotent — re-running will recreate src/ and pyproject.toml with identical content.

### P1-005 Rollback

```bash
# Step 1: Remove config directory
rm -rf /home/guinevere/config/hermes/

# Step 2: Remove evidence
rm -rf docs/setup-evidence/P1/STEP-P1-005/

# Step 3: Remove auditor report
rm -rf audit-reports/P1/STEP-P1-005/

# Step 4: Verify clean
ls /home/guinevere/config/hermes/  # expected: "No such file or directory"
```

**Re-run safety**: P1-005 is idempotent — re-running will recreate config.yaml with identical content.

### Recovery Notes

| Scenario | Recovery Action |
|---|---|
| Hermes install fails | Switch to git clone fallback; don't rollback |
| Config YAML invalid | Fix indentation; re-run T5-04 verification |
| pyproject.toml has wrong deps | Edit file; re-run T4-06 verification |
| Partial evidence written | Remove stale evidence dir; re-execute step |

---

## 15. Validation Commands

### Pre-flight Commands (Run Before Starting)

```bash
# Verify venv
cd /home/guinevere/code/guinevere
source .venv/bin/activate
which python
python --version

# Verify clean slate
test ! -d src/ && echo "src/ clean" || echo "src/ EXISTS"
test ! -f pyproject.toml && echo "pyproject.toml clean" || echo "pyproject.toml EXISTS"

# Verify internet
curl -sI https://pypi.org | head -1

# Check disk space
df -h /home/guinevere/
```

### P1-004 Validation

```bash
# Verify Hermes install
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python -c "import hermes_agent; print(hermes_agent.__version__)"

# Verify project structure
find src -type d | sort
find src -name __init__.py | sort

# Verify pyproject.toml
python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(f'Deps: {len(d[\"project\"][\"dependencies\"])}')"

# Alternative: quick check counts
ls src/core/config/ src/core/models/ src/core/services/ src/core/api/ src/memory/ src/persona/ src/loops/ src/surveillance/ src/discord/ src/mcp/ src/observability/ src/financial/ 2>&1 | wc -l
```

### P1-005 Validation

```bash
# Verify config exists
cat /home/guinevere/config/hermes/config.yaml

# Verify YAML validity
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python -c "import yaml; yaml.safe_load(open('/home/guinevere/config/hermes/config.yaml')); print('YAML: PASS')"

# Verify critical config values
grep -E "safe_word|yandere_max|yandere_baseline|distress_levels|punishment_max|model:|backend:|monthly_cap" /home/guinevere/config/hermes/config.yaml
```

### Evidence Validation

```bash
# Check all evidence exists
ls -la docs/setup-evidence/P1/STEP-P1-004/ 2>&1
ls -la docs/setup-evidence/P1/STEP-P1-005/ 2>&1
ls -la audit-reports/P1/STEP-P1-004/ 2>&1
ls -la audit-reports/P1/STEP-P1-005/ 2>&1
```

### Aizanta Safety Check

```bash
systemctl status aizanta-* 2>&1 | head -5
```

---

## 16. Yandere Baseline Discrepancy — Documented Conflict & Resolution

### Conflict

| Source | Stated Baseline | Authority Rank |
|---|---|---|
| PersonaSafetyPolicy v1.0 (§9) | Implicit Y1 (soft baseline) | **Rank 3** (Policy) |
| Persona Document v3.1 (§1) | Y4 (Faiz's command — permanent) | Rank 6 (Product doc) |
| SystemPromptMaster v1.1 (§C) | Y4 (permanent, always active) | Rank 6-8 (System prompt) |

### Authority Order (per PersonaSafetyPolicy §2.1)

1. System/developer instructions and platform safety requirements
2. Accepted ADRs (ADR-001, ADR-002, ADR-003)
3. **Persona Safety & Ethical Boundary Policy** ← **WINS**
4. Active safe-word/distress state
5. Faiz's current explicit instruction
6. Product/persona documents
7. Memory, surveillance, inferred preferences, drift logs
8. Persona style, yandere intensity, punishment/reward

### Resolution

- **PersonaSafetyPolicy (rank 3) > Persona Document (rank 6) > SystemPromptMaster (rank 6-8)**
- PersonaSafetyPolicy describes Y0-Y6 levels; Y1 is the safe, non-triggered baseline compatible with mandatory downgrade rules (§9.1)
- **P1-005 StepPrompt already uses `yandere_baseline: "Y1"` — this is the CORRECT decision**
- The P1-005 config.yaml MUST keep `yandere_baseline: "Y1"` — NOT Y4
- The SystemPromptMaster v1.1 Y4 baseline reflects persona flavor for the LLM prompt, not the rigid safety config

### What This Means for Runtime

- Safety config `yandere_baseline: "Y1"` = the startup/safe-mode baseline
- LLM SystemPrompt at runtime instructs Y4 persona when safety gates pass
- The two are NOT in conflict — they serve different purposes:
  - Config Y1 = operational baseline (safe start, capable of escalation)
  - Prompt Y4 = persona expression when safety checks pass
- Safety gates (HARD STOP, distress, mood) can downgrade from Y4 runtime back to Y0/Y1

### Recommended Future Action

- No change needed to PersonaSafetyPolicy or SystemPromptMaster
- Document this resolution in P1-005 evidence for auditor trail

---

## 17. Auditor Specialist Matrix

| Audit Scope | Auditor Type | Focus Areas | Report Path |
|---|---|---|---|
| P1-004 code install | Implementation auditor | Hermes import success, version match, pyproject.toml correctness, src/ structure completeness, LSP diagnostics | `audit-reports/P1/STEP-P1-004/step-p1-004-auditor-report.md` |
| P1-005 config correctness | Implementation auditor | YAML validity, all config keys present, LLM routing, loop params, budget values | `audit-reports/P1/STEP-P1-005/step-p1-005-auditor-report.md` |
| P1-005 safety boundary | Safety auditor (Oracle) | yandere_baseline, safe_word, yandere_max, distress_levels, punishment_max, authority order compliance, forbidden patterns match | Same as above (included in P1-005 auditor report) |
| Persona drift check | Persona auditor | Yandere baseline discrepancy resolved correctly? No persona safety drift introduced? | Same as above |
| Evidence completeness | Evidence auditor | All evidence files exist per schema, 12-section template followed, cross-references valid | `docs/setup-evidence/P1/STEP-P1-004/evidence.md` + `docs/setup-evidence/P1/STEP-P1-005/evidence.md` |

### Auditor Sequence

```
P1-004 Install Complete
  → Auditor 1: Implementation audit (T4-07)
  → Fix findings if any
  → Re-audit until PASS
  → Mark P1-004 complete

P1-005 Config Complete
  → Auditor 2: Config correctness audit
  → Auditor 3: Safety boundary verification (T5-03, T5-05)
  → Fix findings if any
  → Re-audit until PASS
  → Mark P1-005 complete
```

---

## 18. Execution Sequence (Parent Orchestration)

```
STEP 1: Pre-flight (parent)
  ├── Read PROGRESS.md, CHECKLIST.md
  ├── Verify prerequisites (PR-01 through PR-10)
  └── Run collision scan (§10)

STEP 2: P1-004 Research Wave (parent → sub-agents)
  ├── [Already done — skip, research-reports exist]
  └── Read existing research reports for context

STEP 3: P1-004 Implementation Wave (parallel where safe)
  ├── T4-01+T4-02: Install hermes-agent + verify import
  ├── T4-03+T4-04: Create src/ structure (after install)
  ├── T4-05: Write pyproject.toml with 23 deps
  └── T4-06: Parent verify tomllib load

STEP 4: P1-004 Evidence + Post-Step Checklist (parent)
  ├── Write evidence.md
  ├── T4-07: Spawn auditor
  ├── Fix findings → re-audit until PASS
  └── Update PROGRESS.md, CHECKLIST.md

STEP 5: P1-005 Pre-flight (parent)
  └── Verify P1-004 complete

STEP 6: P1-005 Implementation Wave (sequential)
  ├── T5-01: Create /home/guinevere/config/hermes/
  ├── T5-02: Write config.yaml with all sections
  ├── T5-03: Safety auditor verify yandere_baseline: "Y1"
  ├── T5-04: Parent verify YAML validity
  └── T5-05: Safety boundary checklist

STEP 7: P1-005 Evidence + Post-Step Checklist (parent)
  ├── Write evidence.md + safety-boundary-verify.md
  ├── T5-06: Spawn auditor
  ├── Fix findings → re-audit until PASS
  └── Update PROGRESS.md, CHECKLIST.md

STEP 8: Final Report (parent → operator)
  ├── Changed files list
  ├── Verification results matrix
  ├── Evidence paths
  ├── Auditor report paths
  └── Next action: P1-006
```

---

## 19. pyproject.toml — 23-Dependency Specification (Corrected from 15)

```toml
[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"

[project]
name = "guinevere"
version = "0.1.0"
description = "Autonomous AI companion and engineering agent system"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
authors = [
    { name = "Faiz" },
]
keywords = ["ai", "agent", "companion", "automation", "discord"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
]

dependencies = [
    # StepPrompts-specified (15):
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2",
    "sqlalchemy[asyncio]>=2",
    "asyncpg>=0.30",
    "alembic>=1",
    "redis>=5",
    "httpx>=0.28",
    "python-dotenv>=1",
    "python-jose[cryptography]>=3",
    "apscheduler>=3",
    "sentry-sdk[fastapi]>=2",
    "prometheus-client>=0.21",
    "structlog>=24",
    "discord.py>=2",

    # P1-003 installed extras (7) — missing from StepPrompts spec:
    "passlib[bcrypt]>=1.7",
    "pydantic-settings>=2.7",
    "aiohttp>=3.11",
    "websockets>=15",
    "typer>=0.15",
    "rich>=13.9",
    "tenacity>=9.0",

    # P1-004:
    "hermes-agent",
]

[project.urls]
Homepage = "https://github.com/faiz/guinevere"
Repository = "https://github.com/faiz/guinevere"
```

**Total**: 15 (StepPrompts) + 7 (extras from P1-003) + 1 (hermes-agent) = **23 dependencies**

---

## 20. .gitignore Specification

Root `.gitignore` does not exist — MUST be created during P1-004:

```gitignore
# Virtual environment
.venv/

# Python cache
__pycache__/
*.py[cod]
*$py.class

# Build artifacts
dist/
build/
*.egg-info/
*.egg

# Tool cache
.ruff_cache/
.mypy_cache/
.pytest_cache/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Environment files
.env
.env.local

# Encrypted age files
*.age
```

---

## 21. Post-Step Checklist (Must-Complete Items)

After P1-004:

- [ ] DoD items D4-01 through D4-09 all PASS
- [ ] `lsp_diagnostics` clean on `src/` (ignore pre-existing issues)
- [ ] Evidence files exist at `docs/setup-evidence/P1/STEP-P1-004/`
- [ ] PROGRESS.md updated (line 99: `P1-004` → ✅)
- [ ] CHECKLIST.md updated (§3.2 P1-004 row)
- [ ] Auditor gate PASS
- [ ] No Aizanta impact
- [ ] No secrets exposed
- [ ] Rollback procedure documented

After P1-005:

- [ ] DoD items D5-01 through D5-15 all PASS
- [ ] `lsp_diagnostics` clean (YAML file)
- [ ] Evidence files exist at `docs/setup-evidence/P1/STEP-P1-005/`
- [ ] Safety-boundary-verify.md documents Y1 baseline resolution
- [ ] PROGRESS.md updated (line 100: `P1-005` → ✅)
- [ ] CHECKLIST.md updated (§3.2 P1-005 row)
- [ ] Auditor gate PASS
- [ ] No Aizanta impact
- [ ] No secrets exposed
- [ ] Rollback procedure documented

---

## Footer

| Field | Value |
|---|---|
| **Plan Author** | Guinevere (mama) |
| **Date** | 2026-06-01 |
| **Source Task** | STEP-P1-004 + STEP-P1-005 batch plan |
| **Effort Estimate** | Medium (1-2 days total) |
| **Plan Path** | `docs/setup-evidence/P1/batch-plan-004-005.md` |
| **Next Step After Plan** | Execute P1-004 → verify → audit → P1-005 → verify → audit |