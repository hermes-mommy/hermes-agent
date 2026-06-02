# Batch Plan: P3-016 to P3-019 — Final Memory System Steps

| Field | Value |
|-------|-------|
| Batch | P3-016, P3-017, P3-018, P3-019 |
| Date | 2026-06-02 |
| Planner | Guinevere (parent) |
| Status | IN PROGRESS |

## Master Todo

| Step | Description | Files | Agent |
|------|-------------|-------|-------|
| P3-016+017+wire | Discord memory commands + bot.py wiring | `src/discord/cmd_memory_search.py`, `src/discord/cmd_memory_add.py`, `src/discord/bot.py` | Agent A |
| P3-018 | E2E memory test suite | `tests/memory/test_memory_e2e.py` | Agent B |
| P3-019 | Performance benchmark script | `scripts/bench_memory.py` | Agent C |

## Dependency Map

```
P3-016+017+wire  ──┐
                    ├── Verification ── Auditor Gate ── PROGRESS.md
P3-018             ──┤
                    │
P3-019             ──┘
```

All 3 agents are independent (no shared files). Full parallelism.

## Collision Scan

| File | Owner | Conflict? |
|------|-------|-----------|
| `src/discord/cmd_memory_search.py` | Agent A | No (new) |
| `src/discord/cmd_memory_add.py` | Agent A | No (new) |
| `src/discord/bot.py` | Agent A | No (append only) |
| `tests/memory/test_memory_e2e.py` | Agent B | No (new) |
| `scripts/bench_memory.py` | Agent C | No (new) |
| `PROGRESS.md` | Parent only | No |

**Verdict**: Zero collisions. Full parallel safe.

## Research Inputs

- `src/discord/cmd_status.py` — canonical command pattern reference
- `src/discord/cmd_mood.py` — secondary pattern reference
- `src/discord/bot.py` — wiring pattern (core_names, tree.command)
- `src/discord/commands.py` — COMMAND_SPECS, is_faiz_interaction
- `src/memory/read_pipeline.py` — recall_memories API
- `src/memory/write_pipeline.py` — store_episode API
- `src/memory/embeddings.py` — EmbeddingService, classification constants
- `tests/memory/test_read_pipeline_hybrid.py` — FakeEpisode, test patterns
- `tests/memory/test_consolidation.py` — FakeSession pattern
- `tests/discord/test_cmd_mood.py` — Discord test patterns

## Binding Decisions

1. **Session factory**: bot.py gains `get_session_factory()` method. Callbacks access via `interaction.client.get_session_factory()`. Lazy-initialized from `DATABASE_URL` env var.
2. **Option extraction**: Helper `_get_option_value(interaction, name)` reads from `interaction.data["options"]` list.
3. **E2E tests**: Deterministic with FakeSession + AsyncMock (no live DB required). Follow existing `asyncio.run()` wrapper pattern.
4. **Benchmark**: Standalone script under `scripts/`, uses `asyncio.run()` + `time.perf_counter()`. No pytest-benchmark dependency.

## Per-Step Verification Scaffold

### P3-016+017+wire

| Field | Criteria |
|-------|----------|
| Expected Files | `src/discord/cmd_memory_search.py`, `src/discord/cmd_memory_add.py`, `src/discord/bot.py` (modified) |
| Forbidden Patterns | `as any`, `@ts-ignore`, empty `except:`, `except Exception: pass`, `type: ignore` on new code |
| Required Commands | `python -m pytest tests/discord/test_bot.py -v` → exit 0 |
| Hard Rejection | Callback not following cmd_status pattern; missing is_faiz_interaction guard; missing try/except with degraded fallback; bot.py core_names not updated |

### P3-018

| Field | Criteria |
|-------|----------|
| Expected Files | `tests/memory/test_memory_e2e.py` |
| Forbidden Patterns | `as any`, empty `except:`, live DB connections without skip-if-unavailable |
| Required Commands | `python -m pytest tests/memory/test_memory_e2e.py -v` → exit 0 |
| Hard Rejection | Missing DNR test; missing safe-mode test; missing write→recall round-trip test |

### P3-019

| Field | Criteria |
|-------|----------|
| Expected Files | `scripts/bench_memory.py` |
| Forbidden Patterns | `as any`, hardcoded credentials, secrets |
| Required Commands | `python scripts/bench_memory.py --help` → exit 0 |
| Hard Rejection | Missing p95 calculation; missing ADR-009 target documentation |

## Evidence Paths

| Step | Verification | Auditor |
|------|-------------|---------|
| P3-016 | `docs/setup-evidence/P3/STEP-P3-016/verification.md` | `docs/setup-evidence/P3/STEP-P3-016/auditor-gate.md` |
| P3-017 | `docs/setup-evidence/P3/STEP-P3-017/verification.md` | `docs/setup-evidence/P3/STEP-P3-017/auditor-gate.md` |
| P3-018 | `docs/setup-evidence/P3/STEP-P3-018/verification.md` | `docs/setup-evidence/P3/STEP-P3-018/auditor-gate.md` |
| P3-019 | `docs/setup-evidence/P3/STEP-P3-019/verification.md` | `docs/setup-evidence/P3/STEP-P3-019/auditor-gate.md` |

## Rollback Plan

- New files: delete `cmd_memory_search.py`, `cmd_memory_add.py`, `test_memory_e2e.py`, `bench_memory.py`
- bot.py: revert core_names tuple and import additions
- No database migrations or config changes

## Caveats

1. Discord callbacks cannot be tested with live Discord — tests use deterministic builder/converter functions + mock interactions
2. E2E tests use FakeSession (no real PostgreSQL) — integration with real DB deferred to deployment verification
3. Benchmark script supports both dry-run (synthetic data) and live-DB modes
4. bot.py session factory requires `DATABASE_URL` env var at runtime — graceful fallback when unavailable
