# Hermes Phase 1 Reinstall + Verify

## Objective
SSH into `guinevere-vps`, install `hermes-agent>=0.15.2` in the VPS virtual environment, verify `AIAgent` import behavior, and test minimal `chat()` and `run_conversation()` calls.

## Environment

| Item | Value |
|---|---|
| VPS user | `guinevere` |
| Project dir | `/home/guinevere/code/guinevere` |
| Python venv | `/home/guinevere/code/guinevere/.venv` |
| Python version | 3.12.3 |
| `uv` path | `/home/guinevere/.local/bin/uv` (uv 0.11.17) |
| `hermes` CLI path | `/home/guinevere/code/guinevere/.venv/bin/hermes` |
| LLM endpoint | `http://localhost:20128/v1` (9Router local proxy) |
| LLM model | `ds/deepseek-v4-flash` |

## Phase 1 — Install hermes-agent

### Command
```bash
. /home/guinevere/code/guinevere/.venv/bin/activate
/home/guinevere/.local/bin/uv pip install "hermes-agent>=0.15.2"
```

### Output
```
Using Python 3.12.3 environment at: code/guinevere/.venv
Checked 1 package in 12ms
```

**Result**: `hermes-agent` was already installed at the required version. Package metadata confirms:

```
Name: hermes-agent
Version: 0.15.2
Summary: The self-improving AI agent — creates skills from experience, improves them during use, and runs anywhere
Author: Nous Research
License: MIT
```

Dist-info path: `hermes_agent-0.15.2.dist-info` (installed in site-packages)

## Phase 2 — Verify import of `agent` module

### Command
```python
import agent
```

### Output
```
AIAgent available
```

**Result**: ✅ `import agent` succeeds.

## Phase 3 — Verify `AIAgent` import path

### Attempt A — as specified in task
```python
from agent.agent_init import AIAgent
```

### Output
```
Failed to load plugin 'nous': No module named 'hermes_cli.dashboard_auth'
ImportError: cannot import name 'AIAgent' from 'agent.agent_init'
```

**Result**: ❌ `AIAgent` is **not** in `agent.agent_init`. The `agent_init.py` module contains the `init_agent()` helper function (which powers `AIAgent.__init__`), but not the `AIAgent` class itself.

### Attempt B — correct import path (discovered)
```python
from run_agent import AIAgent
```

### Output
```
Failed to load plugin 'nous': No module named 'hermes_cli.dashboard_auth'
AIAgent import OK
<class 'type'>
```

**Result**: ✅ `AIAgent` lives in the top-level `run_agent` module (installed as `run_agent.py` at site-packages root, **not** inside the `agent/` package directory). The module's `__init__.py` docstring references `run_agent.py` but does not re-export it.

### Module structure diagram

```
site-packages/
├── run_agent.py          ← AIAgent class (line 327)
├── agent/
│   ├── __init__.py       ← docstring mentions run_agent.py but no re-export
│   ├── agent_init.py     ← init_agent() function (called by AIAgent.__init__)
│   ├── agent_runtime_helpers.py
│   └── ... (80+ helper modules)
├── hermes_cli/
├── hermes_agent-0.15.2.dist-info/
└── ...
```

## Phase 4 — `AIAgent` initialization

### Setup required
`AIAgent.__init__` checks for an LLM provider configuration. Passing `base_url` alone is insufficient — the provider check at line 693 of `agent_init.py` rejects with:

```
RuntimeError: No LLM provider configured. Run `hermes model` to select a provider, or run `hermes setup` for first-time configuration.
```

**Fix**: Pass `provider="openai-api"` and `api_key` explicitly:
```python
from run_agent import AIAgent

a = AIAgent(
    base_url="http://localhost:20128/v1",
    api_key="<any-nonempty-value>",
    model="ds/deepseek-v4-flash",
    quiet_mode=True,
    skip_memory=True,
    skip_context_files=True,
    provider="openai-api"
)
```

### Output
```
Failed to load plugin 'nous': No module named 'hermes_cli.dashboard_auth'
Import OK
Init OK
Type: AIAgent
Provider: openai-api
Model: ds/deepseek-v4-flash
```

**Result**: ✅ Initialization succeeds with `provider="openai-api"` and a non-empty `api_key`.

**Note**: The `Failed to load plugin 'nous'` warning is a pre-existing benign error — the `nous` auth plugin requires `hermes_cli.dashboard_auth` which is not installed in this environment. It does not affect functionality.

## Phase 5 — Test `chat()`

### Command
```python
from run_agent import AIAgent
a = AIAgent(base_url="http://localhost:20128/v1", api_key="dummy-skip",
            model="ds/deepseek-v4-flash", quiet_mode=True,
            skip_memory=True, skip_context_files=True, provider="openai-api")
r = a.chat("hello")
print(type(r))
print(r[:200])
```

### Output
```
=== Calling chat() ===
Response type: <class 'str'>
Response length: 38
Response preview: Hey there! 👋 How can I help you today?
```

**Result**: ✅ `chat("hello")` returns a valid string response of 38 characters from the VPS LLM endpoint.

## Phase 6 — Test `run_conversation()`

### Command
```python
from run_agent import AIAgent
a = AIAgent(base_url="http://localhost:20128/v1", api_key="dummy-skip",
            model="ds/deepseek-v4-flash", quiet_mode=True,
            skip_memory=True, skip_context_files=True, provider="openai-api")
r = a.run_conversation("say hello in 5 words")
print(type(r))
print(list(r.keys()))
print("final_response:", r.get("final_response", "N/A"))
```

### Output
```
=== Calling run_conversation() ===
Response type: <class 'dict'>
Keys: ['final_response', 'last_reasoning', 'messages', 'api_calls', 'completed',
       'turn_exit_reason', 'failed', 'partial', 'interrupted', 'response_transformed',
       'response_previewed', 'model', 'provider', 'base_url', 'input_tokens',
       'output_tokens', 'cache_read_tokens', 'cache_write_tokens', 'reasoning_tokens',
       'prompt_tokens', 'completion_tokens', 'total_tokens', 'last_prompt_tokens',
       'estimated_cost_usd', 'cost_status', 'cost_source', 'session_id']
final_response: Hello there, how are you?
```

**Result**: ✅ `run_conversation()` returns a dict with 27 keys including `final_response`, token usage metrics, cost estimation, and session tracking.

## Phase 7 — Additional diagnostics

### hermes CLI
The `hermes` CLI is also functional:
```
hermes
usage: hermes [-h] [--version] [-z PROMPT] [-m MODEL] [--provider PROVIDER] ...
```

However, the interactive setup (`hermes model`, `hermes setup`) requires a TTY and cannot run in non-interactive SSH sessions.

### Environment variables
VPS non-interactive SSH sessions have no API keys or provider env vars set by default. `OPENAI_API_KEY`, `HERMES_PROVIDER`, and `HERMES_MODEL` are all empty. The LLM endpoint `http://localhost:20128/v1` accepts requests without authentication (internal proxy).

### Plugin warning
```
Failed to load plugin 'nous': No module named 'hermes_cli.dashboard_auth'
```
This is raised during any Python import of the `agent` package in this environment. The `nous` plugin relies on `hermes_cli.dashboard_auth` (a gateway/portal auth module) which is not included in the base `hermes-agent` installation. This is benign but should be noted if auth via Nous Portal is needed later.

## Summary

| Check | Status | Notes |
|---|---|---|
| `hermes-agent>=0.15.2` installed | ✅ | Already at 0.15.2; `uv pip install` confirmed |
| `import agent` | ✅ | Works |
| `from agent.agent_init import AIAgent` | ❌ | **Wrong import path** — AIAgent is not in `agent_init.py` |
| `from run_agent import AIAgent` | ✅ | **Correct path** — AIAgent lives in top-level `run_agent` |
| `AIAgent.__init__()` | ✅ | Works with `provider="openai-api"` + non-empty `api_key` |
| `chat("hello")` returns string | ✅ | Returns valid 38-char response |
| `run_conversation()` returns dict | ✅ | Returns dict with `final_response` key |
| LLM endpoint reachable | ✅ | `localhost:20128` returns useful responses |
| TTY-only commands (`hermes model`) | ⚠️ | Cannot run non-interactively |

### Deviations from task specification

1. **Import path**: The task specified `from agent.agent_init import AIAgent`, which fails in hermes-agent 0.15.2. The correct import is `from run_agent import AIAgent`. The `agent_init.py` module contains the `init_agent()` helper function, not the `AIAgent` class.

2. **API key requirement**: The task did not include `api_key` or `provider` in the AIAgent constructor. In practice, `AIAgent.__init__` requires both `provider="openai-api"` and a non-empty `api_key` to pass the provider configuration gate.

3. **`uv` not in PATH**: `uv` is at `/home/guinevere/.local/bin/uv` but not added to the default PATH. The command worked with the full path.

### Recommendations

- If `from agent.agent_init import AIAgent` is required for compatibility, a re-export alias should be added to `agent/__init__.py` or `agent/agent_init.py`.
- For future automated/hermes-agent scripting tasks, ensure `provider` and `api_key` are always explicitly passed.
- The benign `nous` plugin warning can be resolved by installing the `hermes-cli` extras package that includes `dashboard_auth`, though this is not required for core functionality.
