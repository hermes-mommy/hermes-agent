# Scaffold: STEP-P6-010 — sequential_thinking

## Expected Files

- `src/mcp/tools/sequential_thinking.py` — Chain-of-thought reasoning tool
- `tests/mcp/test_sequential_thinking.py` — Unit tests for reasoning chain

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- Direct LLM API calls (this is a local reasoning structure, not LLM-powered)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_sequential_thinking.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/sequential_thinking.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/sequential_thinking.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Purpose:** Structured chain-of-thought reasoning for complex problem decomposition
- **Pattern:** Step-by-step analysis with thought numbering, branching, and revision
- **Auth Level:** `AuthLevel.READ_AUTO`
- **Cost:** LLM tokens (when used by agent loop) — tracked separately
- **State:** Each thinking session is a list of thought records (frozen dataclass)

### Data Model

```python
@dataclass(frozen=True)
class Thought:
    thought_number: int
    content: str
    is_revision: bool = False
    revises_thought: int | None = None
    branch_from_thought: int | None = None
    branch_id: str | None = None

@dataclass(frozen=True)
class ThinkingSession:
    topic: str
    total_thoughts: int
    thoughts: tuple[Thought, ...]
    needs_more_thoughts: bool = False
```

### Function Signatures

```python
async def sequential_think(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool = True,
    is_revision: bool = False,
    revises_thought: int | None = None,
    branch_from_thought: int | None = None,
    branch_id: str | None = None,
) -> dict[str, object]:
    """Record a thinking step in the chain-of-thought."""
```

### Error Handling

- Invalid thought number (> total_thoughts + 5) → log warning, accept anyway
- Revision references non-existent thought → log warning, record as new thought

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-010/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-010/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys or secrets
- [ ] Auth level `READ_AUTO` enforced
- [ ] Frozen dataclass used for Thought and ThinkingSession
- [ ] Thought numbering and branching supported
- [ ] Revision tracking (is_revision, revises_thought) supported
- [ ] `structlog` used for all logging
- [ ] Tests verify chain construction and branching
