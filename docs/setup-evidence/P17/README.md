# P17 — Cross-Device Sync: Index

**Status:** ⏳ NOT STARTED
**Date:** 2026-06-18
**Phase:** Expansion (TBD)

## Planned Scope

Phase 17 establishes a unified sync layer that keeps Guinevere state coherent
across operator devices (Android phone, Windows desktop, Discord interface,
and the VPS runtime). Building on the existing surveillance and memory
layers, this phase introduces conflict resolution, device pairing, and
end-to-end-encrypted sync channels for memory deltas, persona state, and
operator preferences.

Planned deliverables include: device registry and pairing protocol,
CRDT-based or vector-clock conflict resolution for memory writes, E2E
encryption of sync payloads, sync queue with retry/backoff, and observability
hooks for sync latency and conflict rates.

## Directory Structure

```
P17/
├── README.md                    ← You are here
├── plan/                        ← Implementation plan (future)
├── evidence/                    ← Per-step evidence (future)
└── research/                    ← Research artifacts (future)
```

## Production Code Location

| Artifact | Path |
|---|---|
| Package | `src/sync/` (planned) |
| DB Migration | `migrations/p17_sync_schema.sql` (planned) |

## Progress

| Step | Status | Description |
|---|---|---|
| P17-001 | ⬜ | Device registry + pairing protocol |
| P17-002 | ⬜ | CRDT/vector-clock conflict resolution |
| P17-003 | ⬜ | E2E encrypted sync channel |
| P17-004 | ⬜ | Sync queue with retry/backoff |
| P17-005 | ⬜ | Observability + conflict rate metrics |

> **Note:** This directory is a placeholder for a future phase. No
> implementation has started. Entries above describe planned scope only
> and are subject to change.
