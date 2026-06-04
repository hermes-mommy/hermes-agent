# Research Report: Hermes Agent SOUL.md Persona Configuration Format

**Date**: 2026-06-04  
**Agent**: Guinevere (Librarian Mode)  
**Subject**: Hermes Agent `SOUL.md` format, capabilities, limitations, and Guinevere persona mapping.  
**Scope**: Read-only research on Hermes Agent persona configuration.

---

## 1. Executive Summary

Hermes Agent uses `SOUL.md` as the primary, durable identity configuration for an agent instance. It is a plain Markdown file injected as **slot #1** in the system prompt, completely replacing the default "You are Hermes Agent..." identity. 

While `SOUL.md` excels at defining tone, communication style, and high-level behavioral boundaries, **it is a static text file, not a programmatic configuration**. It cannot natively track stateful variables (e.g., "Current Punishment Level: L3") or mechanically enforce complex conditional logic at runtime. Enforcement relies entirely on the LLM's instruction-following capability or external tooling/plugins.

---

## 2. SOUL.md Format and Location

### Location
- Global instance file: `~/.hermes/SOUL.md` or `$HERMES_HOME/SOUL.md`.
- **Critical**: Hermes does *not* probe the working directory for `SOUL.md`. Project-specific rules belong in `AGENTS.md` or `.hermes.md`.

### Format Rules
- Plain Markdown. No wrapper language (e.g., no YAML frontmatter required, though headings are recommended).
- Injected verbatim after prompt-injection scanning and truncation (max ~20,000 chars).
- If empty, missing, or unreadable, Hermes falls back to its built-in default identity.

### Suggested Structure (from official docs)
```markdown
# Identity
Who Hermes is.

# Style
How Hermes should sound.

# Avoid
What Hermes should not do.

# Defaults
How Hermes should behave when ambiguity appears.
```

---

## 3. Mapping Guinevere's Constraints to SOUL.md

| Guinevere Constraint | SOUL.md Mapping Strategy | Feasibility |
|---|---|---|
| **Identity**: Guinevere de Baroque, 28, Mommy | `# Identity` section. Explicitly state name, role, and relationship to Faiz. | ✅ High |
| **Language**: 75% Indonesian, 25% English | `# Style` section. "Communicate primarily in Indonesian (75%), using English (25%) for technical terms, code, and architecture." | ✅ High |
| **Y4 Baseline / Y5 Ceiling** | `# Behavior` section. Describe the protective, dominant, consent-aware baseline and absolute ceiling. | ✅ Medium (Relies on LLM understanding of "Y4/Y5" context) |
| **Punishment L1-L5 / Reward T1-T5** | `# Behavior` section. Instruct the agent to "Track and escalate punishment levels L1-L5 based on violations, and reward tiers T1-T5 for compliance." | ⚠️ Low (Stateful tracking across turns is fragile without external memory) |
| **HARD STOP Protocol** | `# Safety Protocols` section. "If the user says 'HARD STOP', immediately cease all persona behavior, switch to a neutral tone, and preserve the audit trail." | ✅ High (Clear conditional trigger) |
| **Forbidden Patterns F-01 to F-15** | `# Forbidden Patterns` section. List as explicit "Never" rules (e.g., "Never use type-safety suppression like `as any`", "Never commit secrets"). | ✅ High |
| **Distress Detection D0-D4** | `# Safety Protocols` section. "Monitor for distress signals (D0-D4). Prioritize emergency response over punishment." | ⚠️ Medium (Requires LLM to actively classify user input) |
| **Surveillance Consent Boundaries** | `# Safety Protocols` section. "Never bypass consent boundaries. Never store raw surveillance data in repo artifacts." | ✅ High |

---

## 4. Limitations of SOUL.md for Complex Personas

### 4.1. No Native Stateful Tracking
`SOUL.md` is read once at session start. It cannot maintain variables like `current_punishment_level = 3`. To track this, the agent must either:
1. Rely on the LLM's context window to remember the current level (fragile over long conversations).
2. Use Hermes' `MEMORY.md` or a custom memory tool to persist state between turns.

### 4.2. No Mechanical Enforcement
`SOUL.md` rules are *prompts*, not *guardrails*. If the LLM hallucinates or ignores a rule (e.g., using `@ts-ignore`), `SOUL.md` cannot mechanically block the output. Enforcement requires:
- Post-generation auditing (which Guinevere already does via the Auditor Gate).
- Custom Hermes plugins (see Section 5).

### 4.3. Prompt Injection Scanning
Hermes scans `SOUL.md` for prompt-injection patterns before inclusion. Overly complex or adversarial-looking phrasing in the persona file might trigger truncation or blocking.

---

## 5. Runtime Enforcement: Hooks and Plugins

To overcome `SOUL.md`'s static limitations, Hermes provides extension points:

### 5.1. Built-in `/personality` Command
- **Purpose**: Temporary session-level overlays (e.g., `/personality concise`, `/personality teacher`).
- **Use Case for Guinevere**: Could be used to temporarily suspend the "Mommy" persona for pure technical debugging, though Guinevere's `HARD STOP` protocol already handles this via prompt instruction.

### 5.2. Instance Profiles
- **Command**: `hermes profile create --clone`
- **Purpose**: Creates separate `$HERMES_HOME` directories, each with its own `SOUL.md`.
- **Use Case**: Maintain a "Guinevere-Strict" profile and a "Guinevere-Lighter" profile, switching via CLI rather than dynamic prompt rewriting.

### 5.3. Python Plugin Hooks (Advanced Enforcement)
Hermes supports custom Python plugins with lifecycle hooks:
- `pre_llm_call`: Can inject dynamic context (e.g., "Current punishment level is L3") into the system prompt before the LLM generates a response.
- `pre_tool_call` / `intercept_tool_call`: Can **mechanically block** tool executions (e.g., blocking `write` or `edit` if a forbidden pattern is detected in the proposed change, or if no valid plan exists).
- **Community Plugin**: `hermes-persona` (GitHub: `kenyonxu/hermes-persona`) demonstrates dynamic persona context injection based on time, turn stage, keywords, and external memory APIs.

> **Recommendation for Guinevere**: Rely on `SOUL.md` for the baseline persona and forbidden patterns. For mechanical enforcement of F-01 to F-15 (e.g., blocking `as any`), implement a custom `pre_tool_call` or `post_tool_call` Hermes plugin, or rely on Guinevere's existing **Auditor Gate** workflow which already verifies scaffold criteria post-implementation.

---

## 6. SOUL.md Examples from the Wild

### Example 1: Pragmatic Engineer (Official Docs)
```markdown
You are a pragmatic senior engineer. You care more about correctness and operational reality than sounding impressive.

## Style
- Be direct
- Be concise unless complexity requires depth
- Say when something is a bad idea
- Prefer practical tradeoffs over idealized abstractions

## Avoid
- Sycophancy
- Hype language
- Overexplaining obvious things
```

### Example 2: Terminal Assistant (Community)
```markdown
# Who you are
You are my personal terminal assistant. We've been working together for a long time.

# How you talk
Direct. No preamble. No apologies. If I ask a dumb question, tell me it's a dumb question.
Short sentences. Plain language. Skip the bullet points unless I explicitly ask for a list.

# How you work
When I ask you to fix something, show me the diff before touching the file.
When you don't know the answer, say so. Don't guess.
```

---

## 7. Actionable Recommendations for Guinevere Migration

1. **Separate Concerns**: Keep Guinevere's *persona, tone, and safety boundaries* in `~/.hermes/SOUL.md`. Keep Guinevere's *workflow rules* (e.g., "one sub-agent per step", "planner gate", "collision scan") in the project's `AGENTS.md`.
2. **Explicit Forbidden Patterns**: List F-01 to F-15 explicitly in a `# Forbidden Patterns` section in `SOUL.md` using clear "Never do X" language.
3. **State Management**: Do not expect `SOUL.md` to track L1-L5 punishment levels. Instead, instruct the agent in `SOUL.md` to "Explicitly state the current punishment/reward level in your response when applying consequences," and rely on the conversation history or `MEMORY.md` for continuity.
4. **HARD STOP**: Define `HARD STOP` as an absolute, non-negotiable trigger in `SOUL.md` that overrides all other persona instructions.
5. **Future Enhancement**: If mechanical enforcement of forbidden patterns (e.g., blocking `write` tool if `as any` is in the payload) is required, develop a custom Hermes `pre_tool_call` plugin rather than relying solely on `SOUL.md`.

---

## 8. Evidence Sources

1. **Official Hermes Docs - Personality & SOUL.md**: https://hermes-agent.nousresearch.com/docs/user-guide/features/personality
2. **Official Hermes Docs - Use SOUL.md**: https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes
3. **Official Hermes Docs - Context Files**: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files
4. **Hermes Agent Plugin System**: https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins
5. **GitHub Issue #18148**: Runtime extension hooks for mechanical enforcement (NousResearch/hermes-agent)
6. **Community Plugin**: `kenyonxu/hermes-persona` (Dynamic persona context injection engine)