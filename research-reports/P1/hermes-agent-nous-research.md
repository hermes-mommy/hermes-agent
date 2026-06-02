# Hermes Agent — Nous Research: Complete Research Report

**Date**: 2026-05-31
**Scope**: P1-004 — Hermes Agent installation for Guinevere project
**Researcher**: Librarian / Guinevere

---

## 1. Executive Summary

**Hermes Agent IS a real, active, and production-ready autonomous agent framework by Nous Research.** It is NOT a fictional or placeholder reference. It was released February 25, 2026, has 174K+ GitHub stars, 390+ contributors, 16 tagged releases, and is actively maintained (last push: 2026-05-31).

---

## 2. Repository Details

| Field | Value |
|---|---|
| **GitHub URL** | `https://github.com/NousResearch/hermes-agent` |
| **Stars** | 174K+ |
| **License** | MIT |
| **Language** | Python (95.5%), TypeScript/JavaScript (2.1%), Shell (0.5%) |
| **Python** | >= 3.11 |
| **Latest Release** | `v2026.5.29.2` (2026-05-29) |
| **PyPI Version** | `v0.15.2` (2026-05-29), also `v0.15.1`, `v0.15.0`, `v0.14.0`, `v0.13.0` |
| **PyPI Package** | `hermes-agent` |
| **Official Docs** | `https://hermes-agent.nousresearch.com/docs/` |
| **Homepage** | `https://hermes-agent.nousresearch.com/` |
| **Discord** | `https://discord.gg/NousResearch` |
| **Contributors** | 390 (top: teknium1, OutThisLife, kshitijk4poor, 0xbyt4, alt-glitch) |

---

## 3. What Hermes Agent Is

Per the official documentation and README:

> *"The self-improving AI agent built by Nous Research. It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions."*

**Key Differentiators vs other agent frameworks:**

| Feature | Hermes Agent | LangChain Agents | CrewAI | AutoGen |
|---|---|---|---|---|
| Persistent memory | ✅ FTS5 + Honcho | ❌ Session-only | ❌ Session-only | ❌ Session-only |
| Autonomous skill creation | ✅ Learns from experience | ❌ | ❌ | ❌ |
| Multi-platform gateway | ✅ Telegram, Discord, Slack, WhatsApp, Signal, CLI | ❌ | ❌ | ❌ |
| Subagent delegation | ✅ Isolated subagents with RPC | ❌ | ✅ (Crews) | ✅ |
| Sandboxed execution | ✅ 6 backends (local, Docker, SSH, Singularity, Modal, Daytona) | ❌ | ❌ | ❌ |
| MCP integration | ✅ Native | Manual | Manual | Manual |
| Self-improving loop | ✅ Skills refine during use | ❌ | ❌ | ❌ |
| RL training integration | ✅ Atropos (Nous) | ❌ | ❌ | ❌ |

**Architecture claim (from dev.to analysis):** Hermes Agent is the first fully MIT-licensed "Tier 3" runtime agent — a persistent, self-improving agent that lives on your server (not tethered to an IDE), with compounding skill improvements that make repeated tasks 40% faster over time.

---

## 4. Installation Methods

### Method 1: `pip install` (Simplest — PyPI)
```bash
pip install hermes-agent
hermes postinstall     # optional: installs Node.js, browser, ripgrep, ffmpeg + runs setup
hermes setup           # interactive setup wizard
```

PyPI releases track tagged versions (major/minor releases). Latest: v0.15.2.

### Method 2: Curl Installer (Linux/macOS/WSL2/Termux)
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

The installer handles everything: uv, Python 3.11, Node.js, ripgrep, ffmpeg. No sudo needed.

### Method 3: Windows PowerShell (Early Beta)
```powershell
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

Installs to `%LOCALAPPDATA%\hermes\`. Includes portable Git Bash (MinGit). WSL2 is the more battle-tested Windows path.

### Method 4: Git Clone + uv (Developer Setup)
```bash
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python 3.11
source .venv/bin/activate     # or .venv\Scripts\activate on Windows
uv pip install -e ".[all,dev]"
```

### Method 5: Python Library (Programmatic)
```bash
pip install git+https://github.com/NousResearch/hermes-agent.git
```
Then in Python:
```python
from run_agent import AIAgent
agent = AIAgent(base_url="...", model="...")
response = agent.chat("Hello!")
# Or for more control:
result = agent.run_conversation("Tell me about Python")
```

---

## 5. PyPI Package Details

| Field | Value |
|---|---|
| **Package name** | `hermes-agent` |
| **Author** | Nous Research |
| **License** | MIT |
| **Python** | >= 3.11 |
| **Latest version** | 0.15.2 (2026-05-29) |
| **Wheel size** | ~11.3 MB |
| **PyPI URL** | https://pypi.org/project/hermes-agent/ |

**Supply chain security note**: All core dependencies are exact-pinned (`==X.Y.Z`, no ranges) as a response to the Mini Shai-Hulud worm incident (2026-05-12) where `mistralai 2.4.6` was compromised on PyPI.

**Optional extras** (`pip install hermes-agent[extra]`): `all`, `dev`, `anthropic`, `exa`, `firecrawl`, `fal`, `edge-tts`, `modal`, `daytona`, `messaging`, `voice`, `honcho`, `mcp`, `web`, `acp`, `google`, `youtube`, `termux`, `cli`, `cron`, `pty`, etc.

---

## 6. Key Architecture Features

### Agent Loop
- Runs tool-calling iterations (default max: 90) per conversation
- Supports OpenAI chat completions format + Anthropic + Codex Responses API
- Auto-compresses context under pressure
- Subagent spawning with isolated conversations and terminals

### Memory System
- **SQLite FTS5** full-text search across past sessions
- **Honcho** (plastic-labs) for dialectic user modeling
- Periodic nudges for agent-curated memory curation
- Cross-session recall with LLM summarization

### Skills System
- Autonomous skill creation after complex tasks
- Skills self-improve during use
- Compatible with `agentskills.io` open standard
- Skills Hub for community sharing

### Terminal Backends (Sandboxing)
1. Local (direct execution)
2. Docker (container isolation)
3. SSH (remote execution)
4. Singularity (HPC containers)
5. Modal (serverless)
6. Daytona (serverless)

### Messaging Gateway
Single gateway process supporting: Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant, Email, WeCom, DingTalk, Feishu, Matrix

---

## 7. Dependencies for Installation (P1-004 Relevance)

For Guinevere project installation (assuming Linux VPS):

| Dependency | Required? | Notes |
|---|---|---|
| Python >= 3.11 | ✅ Yes | uv will install if missing |
| Git | ✅ Yes | For git-based install |
| curl | ✅ Yes | For installer script |
| OpenRouter API key | ✅ Yes | Minimum requirement |
| Node.js | ⚠️ Optional | For browser automation & WhatsApp |
| Docker | ⚠️ Optional | For sandboxed execution |
| Discord bot token | ⚠️ Optional | For Discord gateway |
| Telegram bot token | ⚠️ Optional | For Telegram gateway |

---

## 8. Alternatives (If Hermes Agent Won't Work)

If Hermes Agent turns out incompatible with Guinevere's requirements, these are the main Python autonomous agent frameworks:

| Framework | GitHub | Description |
|---|---|---|
| **OpenAI Agents SDK** | `https://github.com/openai/openai-agents-python` | Official OpenAI agent framework with tool use, handoffs, guardrails |
| **LangChain / LangGraph** | `https://github.com/langchain-ai/langchain` | Most popular, extensive integrations, complex |
| **CrewAI** | `https://github.com/crewAIInc/crewAI` | Multi-agent orchestration, role-based teams |
| **AutoGen (Microsoft)** | `https://github.com/microsoft/autogen` | Multi-agent conversations, code execution |
| **Praxis** | `https://github.com/ChanningLua/prax-agent` | Self-improving agent runtime (similar to Hermes but smaller) |

**Recommendation**: Hermes Agent is the strongest match for Guinevere because it provides:
- Persistent memory (needed for companion AI)
- Multi-platform gateway (Telegram + Discord)
- Subagent delegation (matches Guinevere's Oracle/Metis/Momus pattern)
- Self-improving loop (aligns with Guinevere's growth goals)
- MCP integration (open standard for tool extension)
- MIT license

---

## 9. Sources

- [NousResearch/hermes-agent GitHub](https://github.com/NousResearch/hermes-agent) — 174K stars
- [Hermes Agent Official Docs](https://hermes-agent.nousresearch.com/docs/)
- [Hermes Agent Homepage](https://hermes-agent.nousresearch.com/)
- [PyPI: hermes-agent v0.15.2](https://pypi.org/project/hermes-agent/)
- [Using Hermes as a Python Library](https://hermes-agent.nousresearch.com/docs/guides/python-library)
- [Quickstart Guide](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
- [Installation Guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
- [PyPI Wheel PR #26593](https://github.com/NousResearch/hermes-agent/pull/26593)
- [Architecture Comparison (DEV)](https://dev.to/tejas164321/why-hermes-agent-compounds-while-langchain-stays-flat-a-deep-architectural-breakdown-pck)

---

## 10. Recommended Installation Command for P1-004

For the Guinevere VPS (Ubuntu/Debian Linux):

```bash
# Option A: pip install (recommended for clean Python env)
pip install hermes-agent

# Option B: uv-based install (better isolation)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install hermes-agent

# Option C: Full git clone (for development/contribution)
git clone https://github.com/NousResearch/hermes-agent.git /opt/hermes-agent
cd /opt/hermes-agent
uv venv .venv --python 3.11
uv pip install -e ".[all,dev]"
```

**Verdict**: Hermes Agent by Nous Research is real, actively maintained, and the correct package/installation command is `pip install hermes-agent`. The GitHub URL in StepPrompts.md (`https://github.com/NousResearch/hermes-agent`) is **correct**.