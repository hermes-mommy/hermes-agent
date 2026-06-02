# Feature Name Reference Inventory

**Generated:** 2026-06-02
**Task:** Map old P9/P10/P11 feature names to new P11-P22 phases

## Summary Statistics

| Term | Matches | Files |
|------|---------|-------|
| Financial | ~865 | ~177 |
| Hardening | ~429 | ~144 |
| Integration | ~1378 | ~353 |
| WhatsApp | ~279 | ~64 |
| Gmail / Email | ~138 | ~46 |
| Wearable / Xiaomi | ~329 | ~127 |
| Windows Daemon / WebSocket Bridge | ~85 | ~38 |
| Knowledge Graph | ~38 | ~16 |
| Cross-Device | ~7 | ~5 |
| Voice Interface | ~1 | ~1 |
| X Auto Poster / autopost | ~6 | ~3 |
| Self-Improvement | ~52 | ~27 |

## PRIMARY TARGETS (Phase definitions to edit)

1. `PROGRESS.md` — P9 (L708), P10 (L37, L345), P11 (L38, L368-395)
2. `CHECKLIST.md` — P9 (L708-743), P10, P11 (L788-813)
3. `StepPrompts.md` — P9 (L7597-7644), P10 (L7648-7678), P11 (L7771-7833)
4. `StepPrompts.md.bak` — mirror of above
5. `IMPLEMENTATION_GUIDE.md` — phase summary table rows (L42-44)
6. `audit-reports/2026-05-31-implementation-synthesis.md` — P9-P11 synthesis (L71, L492-523, L628-629)

## Feature Redistribution Map (old P11 steps -> new phases)

- Windows Daemon (P11-001 to P11-008) -> P15 Windows Daemon+WebSocket
- WhatsApp (P11-005 to P11-008) -> P11 WhatsApp
- Gmail/Email (P11-009 to P11-010) -> P12 Gmail/Email
- Wearable (P11-011 to P11-012) -> P14 Wearable/Xiaomi Watch
- Knowledge Graph (P11-015 to P11-016) -> P16 Knowledge Graph
- Cross-Device (P11-020 to P11-021) -> P17 Cross-Device Sync
- X Auto Poster -> P13 X Auto Poster (Obscura CDP)
- Voice Interface -> P21 Voice Interface
- Self-Improvement -> P20 Self-Improvement Loop
- Advanced Memory (P11-018 to P11-019) -> P18 Advanced Memory
- Multi-Project Context (P11-013 to P11-014) -> P19 Multi-Project Context

## HIGH-PRIORITY References by Feature

### WhatsApp
- PROGRESS.md L375-378, CHECKLIST.md L804, StepPrompts.md L7790-7792
- ADR-022, APIIntegration §7.1, SRS F.2, FSD FSD-COM-001
- DeploymentGuide 3.7, SecurityPolicy Component 8, Persona §14.3

### Gmail/Email
- PROGRESS.md L379, CHECKLIST.md L805, StepPrompts.md L7793-7795
- ADR-022, APIIntegration §7.2, SRS F.3, FSD FSD-COM-002

### Wearable/Xiaomi
- PROGRESS.md L381-382, CHECKLIST.md L806, ADR-021 (entire file)
- PRD §3.3, Persona §8.9, SurveillanceDataPolicy, ConsentRevocationPolicy

### Windows Daemon
- PROGRESS.md L371-374, CHECKLIST.md L802, TechArch §6.3
- APIIntegration §5.3, FSD FSD-SUR-002, SurveillanceDataPolicy

### Knowledge Graph
- PROGRESS.md L385-386, MemorySchema §3.2, Persona §9.7

### X Auto Poster
- ADR-033 L73,80,152,212 (Obscura stealth requirements)
- setup-evidence/decisions/obscura-adoption/verification.md L24

## Boilerplate References (~30 file headers)
"wearable integrations post-MVP" canonical decision in ~30 docs. Bulk replaceable.

## Archived Docs (skip)
`docs/_archive/` contain ~150+ references but are historical. Do not edit.

## Code References
- `src/financial/__init__.py` — module root
- `src/memory/models.py` L551-618 — Financial schema ORM (4 tables)
- `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` L203-263 — Financial migration
