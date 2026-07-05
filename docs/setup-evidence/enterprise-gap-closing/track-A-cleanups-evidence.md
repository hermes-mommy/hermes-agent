# Track A — Cleanup Evidence

## What Was Done

Four post-sprint quality cleanups identified by exploration agents and implemented in parallel:

1. **ADR-038 naming conflict**: Master index had both a registered ADR-038 (X Auto Poster) and a backlog ADR-038 (Consent & Revocation Policy). Resolved by renumbering backlog ADR-038..ADR-049 → ADR-039..ADR-050. Zero collisions.

2. **Threat model promotion**: Status Draft→Accepted (v1.0→v1.1). Added §12 Security Review section documenting PASS verdict with note: 16 open risks require tracking, THR-029/THR-034 recommended for human security review. No threat entries modified.

3. **OpenAPI expansion**: Added 7 curl examples for write endpoints, 403 Forbidden on 6 endpoints, expanded §4 HMAC walkthrough (replay window ±300s, nonce format, rotation cross-ref to ThreatModel), promoted 4 shared error schemas (Forbidden/Conflict/UnprocessableEntity/ServiceUnavailable) in §8.

4. **CHANGELOG v0.8.0**: Added release section with enterprise gap-closing content. P13/P14 promoted from Unreleased. Link references updated.

## Files Changed

| File | Change |
|---|---|
| `docs/10-governance/17-ADR_Index_v1.0.md` | Backlog renumbered ADR-039..ADR-050 |
| `docs/20-security/25-ThreatModel_v1.0.md` | Draft→Accepted, §12 Security Review |
| `docs/00-core/05a-OpenAPISpec_v1.0.md` | +93 lines: curl examples, 403, HMAC, error schemas |
| `CHANGELOG.md` | v0.8.0 section added |

## Validation Results

- **ADR-038**: `adr_count: 38` confirmed in master index, backlog now ADR-039..ADR-050
- **Threat model**: `status: "Accepted"` confirmed in frontmatter
- **OpenAPI**: 6× `403.*Forbidden` matches confirmed (6 endpoint coverage)
- **CHANGELOG**: `## [0.8.0] — 2026-06-18` at line 45, link reference at line 386

## Evidence Artifacts

| Path | Description |
|---|---|
| `docs/setup-evidence/enterprise-gap-closing/batch-plan.md` | Batch plan (990 lines) |
| `docs/setup-evidence/enterprise-gap-closing/enterprise-gap-closing-verification.md` | Full verification of 22 gaps |
| `docs/setup-evidence/enterprise-gap-closing/enterprise-gap-closing-final-report.md` | Enterprise sprint final report |
| `docs/setup-evidence/enterprise-gap-closing/track-A-cleanups-evidence.md` | This file |

## Audit Gate

Skipped — Track A changes are additive (backlog renumber, frontmatter update, new doc sections, CHANGELOG entry). No structural edits to existing content in targeted files. All verifications confirmed by grep.

## Rollback / Re-run Safety

- ADR index: re-run safe (idempotent edit)
- Threat model: re-run safe (additive §12 only)
- OpenAPI: re-run safe (additive to existing sections)
- CHANGELOG: re-run safe (additive v0.8.0 section)

## Boundary Compliance

- No persona drift, consent violation, surveillance overreach, or Y6
- No type-safety bypass, empty catches, or secret exposure
- No destructive ops