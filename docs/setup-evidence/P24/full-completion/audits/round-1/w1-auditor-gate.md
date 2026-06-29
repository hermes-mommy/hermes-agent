# P24 W1 Auditor Gate Report — Fork Setup + Pydantic Config

- **Auditor**: Independent (sub-agent, adversarial verification)
- **Date**: 2026-06-29
- **Scope**: W1 claims — fork integrity, pyproject.toml, M1 guinevere module, wire block, scaffold commands

---

## Check Results

### A. Fork Integrity

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| A1 | `class AIAgent:` at line 327 of run_agent.py | **PASS** | `grep -n 'class AIAgent:' run_agent.py` → `327:class AIAgent:` |
| A2 | Fork SHA 77a1650c referenced, run_agent.py ~4616 lines | **PASS** | pyproject.toml comment: `hermes-agent REMOVED — now vendored at repo root (P24 fork, SHA 77a1650c)`; `wc -l run_agent.py` → `4616` |
| A3 | Hermes packages at repo root | **PASS** | `ls agent/ tools/ gateway/ cron/ hermes_cli/ plugins/ providers/ acp_adapter/ tui_gateway/` — all 9 directories exist with contents |
| A4 | PyPI hermes-agent uninstalled from site-packages | **PASS** | `ls .venv/Lib/site-packages/ | grep -i hermes` → empty (no output) |
| A5 | `import agent` resolves from repo root | **PASS** | `.venv/Scripts/python.exe -c "import agent; print(agent.__file__)"` → `C:\Users\faizz\guinevere\agent\__init__.py` |

### B. pyproject.toml Correctness

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| B6 | `guinevere` in packages list | **PASS** | `grep -A15 'packages =' pyproject.toml` shows 9 Hermes packages + `"guinevere"` |
| B7 | `hermes-agent` dependency REMOVED | **PASS** | `grep 'hermes-agent' pyproject.toml` → only comment line and script entry point (not a dep) |
| B8 | pythonpath is `["."]` not `["src"]` | **PASS** | `grep pythonpath pyproject.toml` → `pythonpath = ["."]` |
| B9 | Script entry points present | **PASS** | `grep -A3 'project.scripts' pyproject.toml` → `hermes`, `hermes-acp`, `hermes-agent` all present |
| B10 | force-include present | **PASS** | `grep 'force-include' pyproject.toml` → `[tool.hatch.build.targets.wheel.force-include]` present |

### C. M1 Module Quality

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| C11 | 12 nested models + GuinevereConfig, Pydantic v2 | **PASS** | Models: DatabaseConfig, RedisConfig, AgentConfig, HttpConfig, DelegationConfig, CircuitBreakerConfig, MemoryConfig, ConsciousnessConfig, EmotionConfig, GovernanceConfig, TailscaleConfig, PersonalityConfig (12 nested) + GuinevereConfig (root). Uses `BaseModel`, `BaseSettings`, `Field`, `model_config = SettingsConfigDict(...)` — Pydantic v2 patterns. |
| C12 | Secret fields are REFERENCES (env var names), not real values | **PASS** | `grep -iE 'token|password|secret|key' models.py loader.py config/*.yaml` — all secret fields are refs: `s4_aes_gcm_256_key_ref: "MEMORY_S4_AES_KEY"`, `auth_key_ref: "TAILSCALE_AUTH_KEY"`, `discord_bot_token_ref: "DISCORD_BOT_TOKEN"` + YAML variants `_GUIN`/`_PHARSA`. No real secret values found. |
| C13 | load_settings() handles missing YAML gracefully | **PASS** | `loader.py` checks `resolved.is_file()`, logs warning, returns `GuinevereConfig()` (defaults) on missing file. No crash. |
| C14 | guinevere.yaml and pharsa.yaml differ correctly | **PASS** | guinevere: agent_id=a1b2c3d4..., name="Guinevere", db_offset=0, instance_role="guinevere", soul=guinevere-soul.md, co_ceos={guinevere: [engineering, research, hr]}. pharsa: agent_id=b2c3d4e5..., name="Pharsa", db_offset=3, instance_role="pharsa", soul=pharsa-soul.md, co_ceos={pharsa: [finance, ops, content]}. All fields differ as expected. |

### D. Wire Block

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| D15 | M1 wire block appends-only, fail-soft, sets _guinevere_settings | **PASS** | `sed -n '1640,1665p' agent/agent_init.py`: wire block at L1652-1663, after existing anthropic block, before `__all__`. Wrapped in `try/except Exception` → sets `agent._guinevere_settings = None` on failure (fail-soft). Uses `os.environ.get("GUINEVERE_CONFIG", "config/guinevere.yaml")` for path override. Does not touch existing init_agent logic. |

### E. Scaffold Re-run (verified independently)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| E16 | `from guinevere.config.models import GuinevereConfig` | **PASS** | Output: `models OK` |
| E17 | load guinevere.yaml | **PASS** | Output: `guin Guinevere guinevere 0` |
| E18 | load pharsa.yaml | **PASS** | Output: `pharsa Pharsa pharsa 3` |
| E19 | `import guinevere` | **PASS** | Output: `pkg 0.2.0` |
| E20 | `import agent.agent_init` | **PASS** | Output: `agent_init OK` |
| E21 | No consent_gate/hard_stop/safe_mode in guinevere/ | **PASS** | `grep -rn 'consent_gate\|hard_stop\|safe_mode' guinevere/` → exit 1 (0 matches) |
| E22 | No type: ignore/as any/@ts-ignore in guinevere/ | **PASS** | `grep -rn '# type: ignore\|as any\|@ts-ignore' guinevere/` → exit 1 (0 matches) |

### F. Forbidden Pattern Scan (broader)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| F23 | No hard_stop/consent_gate/safe_mode in guinevere/ or config/ | **PASS** | `grep -rn 'hard_stop\|HARD_STOP\|consent_gate\|safe_mode' guinevere/ config/` → exit 1 (0 matches) |
| F24 | Soul files contain no intimate/personal data | **PASS** | Both `config/souls/guinevere-soul.md` and `config/souls/pharsa-soul.md` contain fictional persona descriptions only (personality axes, operating principles, portfolios, emotional baselines). No real personal data, medical records, addresses, or intimate details. References to operator as "Faiz" (known handle) only. |

---

## Findings

| ID | Severity | Description | Location | Fix Recommendation |
|----|----------|-------------|----------|--------------------|
| — | — | No findings | — | — |

**Total**: 0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW, 0 COSMETIC

---

## Verdict

# **PASS**

0 CRITICAL / 0 HIGH findings. All 24 checks verified independently with observed command output. The W1 implementation is clean: fork integrity confirmed (SHA 77a1650c, 4616 lines, class AIAgent at L327), pyproject.toml correctly restructured, 12 Pydantic v2 models + GuinevereConfig with env-var reference secrets only, graceful YAML loader, differentiated instance configs, fail-soft wire block, and zero forbidden patterns.
