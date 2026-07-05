# Fix Report: ADR-056 Stale References

- **Date**: 2026-06-28
- **Scope**: 4 files in `adr-drafts/` — annotate all ADR-056 (fork-agnostic-p28-path) references as DELETED
- **Reason**: ADR-056 was deleted. P24 IS the fork (hard dependency); fork-agnostic path inverted. Superseded by ADR-062 + P24 v2.0.

## Changes Made

### 1. ADR-055-hermes-society-architecture.md (line 69)

| Before | After |
|---|---|
| `ADR-056 (Fork-Agnostic Path), ADR-057...` | `ADR-056 (Fork-Agnostic Path) (DELETED 2026-06-28 — superseded by ADR-062 + P24 v2.0 fork), ADR-057...` |

### 2. ADR-057-founder-only-spawn-2-of-2-agreement.md (line 77)

| Before | After |
|---|---|
| `ADR-056-fork-agnostic-p28-path.md — lineage portability invariant` | `ADR-056-fork-agnostic-p28-path.md — lineage portability invariant (DELETED 2026-06-28 — superseded by ADR-062 + P24 v2.0 fork)` |

### 3. ADR-059-shared-world-model-with-private-memory.md (lines 92, 117)

**Line 92** (Neutral section):

| Before | After |
|---|---|
| `The architecture is P24 fork-agnostic (ADR-056):` | `The architecture is P24 fork-agnostic (ADR-056) (DELETED 2026-06-28 — superseded by ADR-062 + P24 v2.0 fork):` |

**Line 117** (References section):

| Before | After |
|---|---|
| `ADR-056-fork-agnostic-p28-path.md` | `ADR-056-fork-agnostic-p28-path.md (DELETED 2026-06-28 — superseded by ADR-062 + P24 v2.0 fork)` |

### 4. BLDM-Hard-Locked-Faiz-Decisions.md (lines 7, 280)

**Line 7** (Authority section):

| Before | After |
|---|---|
| `ADR-056 §Compliance, ADR-057` | `ADR-056 §Compliance (ADR-056 DELETED 2026-06-28), ADR-057` |

**Line 280** (§22 References):

| Before | After |
|---|---|
| `ADR-056-fork-agnostic-p28-path.md` | `ADR-056-fork-agnostic-p28-path.md (DELETED — file no longer exists)` |

**Line 31** (Q2 row): Pre-existing annotation — "ADR-056 DELETED — fork-agnostic path inverted." No change needed.

## Verification

- All 7 ADR-056 occurrences in the 4 files now carry DELETED annotation
- No references were removed — only annotated
- BLDM line 31 was already annotated pre-fix (left untouched)
- Files outside `adr-drafts/` were not touched

## Files Changed

1. `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-055-hermes-society-architecture.md`
2. `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-057-founder-only-spawn-2-of-2-agreement.md`
3. `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-059-shared-world-model-with-private-memory.md`
4. `docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md`
