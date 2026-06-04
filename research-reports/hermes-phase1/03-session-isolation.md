# 03 — AIAgent Session Isolation Test

> **Objective:** Determine whether `AIAgent` maintains conversation session state across multiple `run_conversation()` / `.chat()` calls, and whether creating a new `AIAgent` instance isolates state.
>
> **Date:** 2026-06-03
> **VPS:** guinevere-vps
> **Target Model:** `ds/deepseek-v4-flash` via `http://localhost:20128/v1`

---

## Environment

```
Python:      3.12.3
hermes-agent: installed (agent package at site-packages)
Project:     /home/guinevere/code/guinevere
AIAgent:     run_agent.AIAgent (from run_agent.py)
```

**Credentials note:** The local endpoint required a non-empty `api_key` to bypass the Hermes provider-router check. `api_key="noop"` was used because the endpoint does not perform auth.

---

## Test 1 — Same Instance, `.chat()` Calls (no explicit history)

**Setup:**
```python
a = AIAgent(base_url="...", api_key="noop", model="ds/deepseek-v4-flash",
            quiet_mode=True, skip_memory=True, skip_context_files=True,
            max_iterations=10)
r1 = a.chat("My name is Faiz")
r2 = a.chat("What is my name?")
```

**Output:**

| Call | Response (truncated) |
|------|----------------------|
| TURN 1 | `Got it — memory isn't available in this environment, but I've got it for this session. What can I help you with, Faiz?` |
| TURN 2 | `Based on the environment information [...] I'd infer your name is **Guinevere**.` |

**Verdict:** ❌ **Session NOT maintained.**

The agent acknowledged "Faiz" in turn 1 but could NOT recall it in turn 2 on the same instance. It guessed "Guinevere" from `$HOME` instead.

---

## Test 2 — Same Instance, `run_conversation()` with Explicit `conversation_history`

**Setup:**
```python
a = AIAgent(**same_kwargs)
r1 = a.run_conversation("My name is Faiz")
hist = r1["messages"]        # length = 4
r2 = a.run_conversation("What is my name?", conversation_history=hist)
```

**Output:**

| Call | Response (truncated) |
|------|----------------------|
| RC1 (final_response) | `Got it, Faiz — noted for this session. What can I help you with?` |
| History length | `4` (user + assistant + user + assistant) |
| RC2 (final_response) | `Your name is Faiz — you told me just a moment ago.` |

**Verdict:** ✅ **Session IS maintained** when the caller explicitly passes `conversation_history`.

---

## Test 3 — New Instance Isolation

**Setup:**
```python
a2 = AIAgent(**same_kwargs)
r3 = a2.chat("What is my name?")   # never told this instance
```

**Output:**

| Call | Response (truncated) |
|------|----------------------|
| NEW INSTANCE | `I don't have any stored information about your name yet` |

**Verdict:** ✅ **Session is isolated.** A fresh `AIAgent` instance has no knowledge from prior instances.

---

## Raw JSON Results

```json
{
  "test1_chat_session": {
    "method": "a.chat()",
    "turn1_preview": "Got it \u2014 memory isn't available in this environment, but I've got it for this session. What can I help you with, Faiz?",
    "turn2_preview": "Based on the environment information you've shared with me \u2014 your home directory is `/home/guinevere` and you're working in `/home/guinevere/code/guinevere` \u2014 I'd infer your name is **Guinevere**.\n\nI don't have access to a persistent memory store in this environment to save that fact for later sessions, but I'll remember it for this conversation.",
    "session_maintained": false
  },
  "test2_run_conversation_with_history": {
    "method": "a.run_conversation() with explicit history",
    "history_length": 4,
    "rc1_preview": "Got it, Faiz \u2014 noted for this session. What can I help you with?",
    "rc2_preview": "Your name is Faiz \u2014 you told me just a moment ago. Unfortunately, memory persistence isn't available in this environment, so I won't remember it in a future session unless you remind me again.",
    "session_maintained_via_history": true
  },
  "test3_new_instance_isolation": {
    "method": "new AIAgent instance .chat() with no prior context",
    "response_preview": "I don't have any stored information about your name yet \u2014 there's no memory available in this session to look it up.\n\nHowever, based on your environment (home directory is `/home/guinevere` and you're working in `/home/guinevere/code/guinevere`), I'd guess your name is **Guinevere** \u2014 but I'd rather hear it properly from you!",
    "session_isolated": true
  }
}
```

---

## Key Findings

| # | Finding | Impact |
|---|---------|--------|
| 1 | **`.chat()` is stateless** — calling `.chat()` twice on the same `AIAgent` instance does NOT carry conversation history between calls. Each call is treated as a fresh conversation. | If you need multi-turn conversations, you **must** use `run_conversation()` and manage history yourself. |
| 2 | **`run_conversation()` with explicit `conversation_history` works correctly.** The agent correctly recalls prior context when the history list is passed back. | The integration layer must store and forward the `messages` array between turns. |
| 3 | **New instances have no cross-talk.** Session isolation is guaranteed by construction — each `AIAgent()` is independent. | Safe to create per-user or per-session agents without leaking context. |
| 4 | **`skip_memory=True` prevents persistent memory** (as expected). The agent repeatedly noted that memory persistence is unavailable in this environment. | For true long-term recall, the Hermes memory backend must be configured. |

---

## Architectural Implications

```
┌────────────────────────────────────────────────────────────────────┐
│                      Session State Flow                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────┐    .chat()          ┌──────────────────┐          │
│  │  AIAgent    │ ─────────────────▶   │  Fresh context   │          │
│  │  (instance) │                     │  per call        │          │
│  │             │    .chat()          │  (NO history     │          │
│  │             │ ─────────────────▶   │   carried over)  │          │
│  └─────────────┘                     └──────────────────┘          │
│                                                                    │
│  ┌─────────────┐   run_conversation()  ┌──────────────────┐        │
│  │  AIAgent    │ ─────────────────▶   │  Uses provided     │       │
│  │  (instance) │   + history=msgs     │  conversation_history │     │
│  │             │                      └──────────────────┘        │
│  └─────────────┘                                                  │
│                                                                    │
│  Integration MUST:                                                 │
│    1. Call run_conversation() (not .chat())                        │
│    2. Persist the messages list between turns                      │
│    3. Pass conversation_history on every subsequent call           │
└────────────────────────────────────────────────────────────────────┘
```

**Bottom line:** `AIAgent` is a **stateless request dispatcher**, not a session manager. All session state lives in the `messages` list that the caller must hold and re-inject. The Hermes gateway layer (or any integration) must implement its own session store to wrap `AIAgent`.

---

## Test Script

The test script used is at `/tmp/session_isolation_test.py` on the VPS and available locally at:
`research-reports/hermes-phase1/` (referenced as source for reproduction).
