# Rule Preservation Appendix — §7 to §14

**Source**: AGENTS.md (689 lines)
**Target**: ~350-400 lines
**Scope**: §7-§14 only (lines 366-689 = ~324 lines, ~47% of file)
**Date**: 2026-06-01
**Purpose**: Checklist to ensure refactor preserves all required rules, tables, schemas, and tooling notes.

---

## §7 Operator Protocol (lines 366-403, ~38 lines)

- [ ] **Anchor**: ## §7 Operator Protocol — Faiz as Pilot, Guinevere as Protective Co-Pilot
- [ ] **Subsections**: 3 — "Faiz Says, I Do" (table), "What Faiz Doesn't Need to Say" (list), "When I Ask Faiz" (list)
- [ ] **Keywords preserved**: "lanjut", "lanjut N", "stop", "audit" / "review", "fix 1+2+3", "bypass approval", "kasih ruang" / "lighter today", "bypass off", "HARD STOP" — all 9 commands + their I-do responses
- [ ] **Auto-handle list** (7 items): reading docs/ADRs, creating/updating todos, spawning sub-agents, updating docs/README.md/evidence indexes, running diagnostics, creating evidence, spawning per-step auditor
- [ ] **When-I-ask list** (5 items): scope ambiguity, destructive action, ADR/Persona reaffirmation, 2 failed attempts + Oracle can't resolve, intent conflicts with consent-safety/surveillance
- [ ] **Preservation priority**: LOW — table format can be condensed; command names are the critical anchors. Auto-handle and When-I-ask lists can be terse bullets.
- [ ] **Formatting risk**: Pipe table | Faiz says | I do | — watch column alignment after condensing.

---

## §8 Reference Tables (lines 404-445, ~42 lines)

- [ ] **Anchor**: ## §8 Reference Tables
- [ ] **Subsections**: 3 tables — "Guinevere Document Families", "Binding Tie-Breakers", "Implementation Suite Files"
- [ ] **Table 1 — Document Families** (8 rows):
  - Families: Core product, Governance, Security, Data, Operations, Quality, Persona, FinOps
  - Each row has Family | Examples (with doc paths) | When to Read
  - Paths: docs/00-core/, docs/10-governance/, docs/20-security/, docs/30-data/, docs/40-operations/, docs/50-quality/, docs/60-persona/, docs/70-finops/
- [ ] **Table 2 — Binding Tie-Breakers** (9 rows):
  - Conflict types: Persona behavior, Architecture decision, Safety boundary, Consent/surveillance, Security/auth, Data classification, Financial/cost, Test expectation, Evidence path
  - Each row maps to specific docs. Critical: ADR-001/002 for safety boundary, PersonaSafetyPolicy + ADR-001/002 as safety > operator absolute
- [ ] **Table 3 — Implementation Suite Files** (8 rows):
  - Files/dirs: AGENTS.md, docs/README.md, adr/, audit-reports/, research-reports/, evidence/, docs/, runbooks/
- [ ] **Preservation priority**: HIGH — tables contain cross-reference data used by AGENTS.md §2.5. Must remain structurally complete.
- [ ] **Formatting risk**: Pipe tables with backtick paths in cells — ensure | and backtick escaping are preserved. Long cell content (Examples column) may overflow in narrow format.

---

## §9 Repository and Infrastructure Isolation Policy (lines 446-471, ~26 lines)

- [ ] **Anchor**: ## §9 Repository and Infrastructure Isolation Policy
- [ ] **Subsections**: 2 tables — "Never Share" (6 rows), "Allowed to Reuse" (6 rows)
- [ ] **Never Share resources**: VPS/runtime, Database, Secrets, Evidence, Surveillance data, Credentials
- [ ] **Never Share keywords**: "Dedicated VPS", "Separate PostgreSQL/Redis instances", "Separate Discord bot token", "separate evidence/ roots", "Never mix surveillance data", "Never send credentials"
- [ ] **Allowed to Reuse patterns**: Super-autopilot workflow, Plan-then-delegate, File-based sub-agent outputs, Per-step auditor gate, Post-step checklist discipline, Persona style
- [ ] **Preservation priority**: MEDIUM — already concise (26 lines). Can be kept as-is or slightly condensed.
- [ ] **Formatting risk**: Minimal — both tables are simple with short content.

---

## §10 Appendix A — Full Autonomous Task Template (lines 472-485, ~14 lines)

- [ ] **Anchor**: ## §10 Appendix A — Full Autonomous Task Template
- [ ] **Code block**: Single-line invocation pattern (fence: `	ext). Content spans ~3 lines wrapped.
  - Keywords: ead current state, decompose into atomic todos, ire unlimited independent sub-agents, ile-based outputs, synthesize research before planner agents, collision scan, delegate implementation clusters, parent handles shared docs, erify claimed files, lsp_diagnostics, DoD, evidence, cross-references, consent-safety/persona-drift/surveillance-overreach/HARD STOP/distress-protocol/yandere-boundary constraints, sync docs/README.md/evidence indexes, spawn independent per-step auditor, ix valid findings and re-audit via task_id, do not commit/push/deploy/destructive-op
- [ ] **Relaxation rules** (3 items): Trivial read-only (no auditor), Single-line typo (direct edit), Safety-affecting (never relax)
- [ ] **Preservation priority**: HIGH — canonical invocation template is the most-referenced pattern in AGENTS.md (referenced by §2.5, §2.5.1, §10). Content of code block must be verbatim.
- [ ] **Formatting risk**: Code fence (`	ext...`) — preserve exactly. Long single line may reflow; ensure no line breaks are introduced inside the template.

---

## §11 Appendix B — Evidence Minimum Schema (lines 486-500, ~15 lines)

- [ ] **Anchor**: ## §11 Appendix B — Evidence Minimum Schema
- [ ] **10 required sections** (numbered list):
  1. What Was Done
  2. Files Changed
  3. Validation Results (pre-existing vs introduced split)
  4. Evidence Artifacts
  5. Doc-Sync Impact
  6. Boundary Compliance (no persona drift, no consent violation, no surveillance overreach, no Y6, no HARD STOP bypass, no distress protocol suppression)
  7. Rollback / Re-run Safety
  8. Design Decisions / Caveats
  9. Auditor Gate
  10. Footer (source task, date, implementer, validation method)
- [ ] **Preservation priority**: HIGH — referenced by §4 post-step checklist (item 4) and every evidence file creator.
- [ ] **Formatting risk**: Low — simple numbered list. Section 6 boundary compliance list should remain inline as comma-separated (currently uses "no X, no Y" pattern within one line).

---

## §12 Appendix C — Tool and MCP Selection Hierarchy (lines 501-519, ~19 lines)

- [ ] **Anchor**: ## §12 Appendix C — Tool and MCP Selection Hierarchy
- [ ] **Tool table** (12 rows):
  - Needs: Local file/code search, Skill loading, Background sub-agents, Library docs, OSS code patterns, Web/current references, External provider readiness, Browser/UI validation, Time/date math, File writes, Edits, Git
  - Each row: Need | First Reach | Notes
  - Key patterns: grep, glob, read, lsp_*, load_skills=[], un_in_background=true, Context7, grep_app_searchGitHub, Brave/Exa/fetch, librarian, Playwright, 	ime_* tools, ilesystem_write_file, ilesystem_edit_file, git-master skill
- [ ] **Consent-safety constraint line** (after table): "never send secrets, Discord tokens, API keys, DB passwords, surveillance credentials, decrypted env values, or intimate personal data to external MCP/web tools. Reference docs/60-persona/62-MCPConfigGuide_v1.0.md"
- [ ] **Preservation priority**: HIGH — every row is an actionable tool decision; loss of even one row means agents may use wrong tool.
- [ ] **Formatting risk**: Pipe table with long Notes cells — ensure no truncation. The consent line is not inside the table — must remain as a separate paragraph.

---

## §13 Footer (lines 520-545, ~26 lines)

- [ ] **Anchor**: ## §13 Footer
- [ ] **Subsections**: Versioning (table), Maintenance (list), Operator Sign-Off (paragraph), Persona quote
- [ ] **Versioning table** (2 rows): v2.0 (2026-05-31, Faiz+Guinevere), v1.0 (2026-05-30, Hephaestus/Guinevere)
- [ ] **Maintenance list** (6 items): new doc/ADR, sub-agent orchestration changes, safety/privacy/governance stricter rules, MCP/tooling changes, delegation trigger coverage, re-audit after major rewrite
- [ ] **Operator Sign-Off paragraph**: "Approved by Faiz via session instruction..." — preserves consent-safety, HARD STOP protocol, persona drift, surveillance consent, no-autonomous-destructive-ops
- [ ] **Persona quote** (closing): *"Halo sayang, namaku Guinevere. Aku mama kamu..." — italic block, ~3 lines
- [ ] **Preservation priority**: MUST RETAIN PER USER DIRECTIVE. Sign-Off paragraph and persona quote are tenure markers. Versioning table needed for provenance.
- [ ] **Formatting risk**: The persona quote is inside *...* italic markers spanning multiple lines — ensure markdown italic doesn't break. Versioning table is standard.

---

## §14 Tooling Notes — Practical Rules (lines 546-689, ~144 lines)

- [ ] **Anchor**: ## §14 Tooling Notes — Practical Rules
- [ ] **Subsections**: 7 sub-sections with rules, tables, code examples
- [ ] **14.1 File writing** (22 lines): Rule + Alasan + Pattern table (5 rows) + Gak boleh (2 items). Keywords: ilesystem_write_file, write (what NOT to use), Set-Content (prohibited), BOM/CRLF corruption
- [ ] **14.2 Editing existing files** (4 lines): edit tool, read before edit, exact match oldString, expand context when ambiguous
- [ ] **14.3 Reading files** (4 lines): ead for <2000 lines, ilesystem_read_text_file for segments, Get-Content prohibited
- [ ] **14.4 Searching** (4 lines): glob for pattern matching, grep for content search, Select-String/Get-ChildItem as fallback only
- [ ] **14.5 Question tool** (4 lines): label + description required, Recommended marker, no "Other" option
- [ ] **14.6 Background tasks** (5 lines): end response after fire, ackground_cancel per-task (NOT all=true), Oracle never cancel
- [ ] **14.7 Sub-agent output discipline** (22 lines): Rule + BLOCKING output_path requirement + Applies to list (5 items) + Required pattern (5 steps) + Inline exception
- [ ] **14.8 WORKFLOW GATES** (30 lines): RESEARCH WAVE (5 rules), PLANNER GATE (4 rules), AUDITOR ORCHESTRATOR (4 rules)
- [ ] **14.9 Per-step implementation auditor gate** (30 lines): Rule + Gate order (6 steps) + Auditor wajib (6 items) + Verdict handling table (3 rows)
- [ ] **14.10 Markdown table compatibility** (2 lines): pipe table alignment, escape | in cells, avoid backtick in cell with code fence outside
- [ ] **Preservation priority**: MUST RETAIN PER USER DIRECTIVE. This is the most-used practical reference for agent behavior. All 10 sub-sections contain critical behavioral rules. The WORKFLOW GATES subsection (§14.8) is particularly important as it parallels §2 execution mandates.
- [ ] **Formatting risk**: Multiple nested subsections (###, ####, code examples, pipe tables). The auditor gate order (6-step numbered list interleaved with bolded "Auditor wajib:" list) must maintain correct nesting. Verdict handling table at lines 680-684.

---

## Summary Statistics

| Section | Lines | % of §7-§14 | Preservation Priority |
|---------|-------|-------------|----------------------|
| §7 Operator Protocol | 38 | 12% | LOW (condensable) |
| §8 Reference Tables | 42 | 13% | HIGH (structure) |
| §9 Isolation Policy | 26 | 8% | MEDIUM (already lean) |
| §10 Autonomous Template | 14 | 4% | HIGH (verbatim content) |
| §11 Evidence Schema | 15 | 5% | HIGH (numbering matters) |
| §12 Tool Hierarchy | 19 | 6% | HIGH (every row matters) |
| §13 Footer | 26 | 8% | MUST RETAIN (user directive) |
| §14 Tooling Notes | 144 | 44% | MUST RETAIN (user directive) |

### Condensation opportunities:
- §7: Table rows can be compressed (9 rows → tighter phrasing). Auto-handle and When-I-Ask lists can be merged into table or shortened.
- §9: Already lean but the "Never Share" / "Allowed to Reuse" split can be inlined into a single table.
- §14: Sub-sections are already fairly dense. Minor whitespace reduction possible (~10-15 lines from blank lines).

### Sections that MUST remain structurally unchanged (formatting-critical):
- §8 — 3 pipe tables with doc paths
- §10 — code fence content (single-line template)
- §11 — numbered list (order matters for evidence compliance)
- §12 — tool selection table with 12 rows
- §13 — versioning table + sign-off paragraph + persona quote
- §14.1, §14.7, §14.8, §14.9 — tables, code examples, and nested list formatting

### Redundancy watch:
- §2 Execution Mandates overlaps with §14 WORKFLOW GATES — but both are needed (§2 is conceptual mandate; §14 is practical tool-level rules). Marked intentional.
- §7 "What Faiz Doesn't Need to Say" partially overlaps with §2 auto-pilot mode description — could be deduplicated.
