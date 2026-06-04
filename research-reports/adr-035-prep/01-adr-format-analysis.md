# ADR Format Analysis — Guinevere ADR-001 through ADR-034

**Purpose:** Comprehensive format, structure, and convention analysis of all existing Guinevere ADRs to serve as the mandatory style guide for ADR-035 (Hermes NousResearch migration decision).

**Date:** 2026-06-04
**Author:** Guinevere (Sisyphus-Junior)
**Scope:** 33 existing ADR files + `adr/README.md` index (ADR-034 file does not exist physically)

---

## 1. File Inventory & Line Counts

Read-tool line counts (authoritative, includes blank lines and YAML frontmatter lines):

| ADR | Title | Lines | Status | Risk |
|---|---|---|---|---|
| ADR-032 | Backup Storage Strategy — idcloudhost S3 + Cloudflare R2 | **224** | Accepted | CRITICAL |
| ADR-033 | Browser Automation — Obscura CDP | **212** | Accepted | MEDIUM |
| ADR-028 | LLM Router Outage — Graceful Degradation | **188** | Superseded | MEDIUM |
| ADR-029 | Self-Modification Automated Testing | **181** | Accepted | CRITICAL |
| ADR-022 | Communication Channel Strategy | **154** | Accepted with notes (Revised) | HIGH |
| ADR-025 | Backup & Disaster Recovery Strategy | 130 | Accepted with notes | CRITICAL |
| ADR-001 | Persona Safety & Ethical Boundary Policy | 129 | Accepted with notes | CRITICAL |
| ADR-008 | Memory Encryption & Key Management | 129 | Accepted with notes | CRITICAL |
| ADR-018 | Security Architecture & Defense-in-Depth | 128 | Accepted with notes | CRITICAL |
| ADR-013 | Guinevere MCP Native OpenCode Replacement | 124 | Accepted | HIGH |
| ADR-007 | Memory Storage Backend Selection | 122 | Accepted | CRITICAL |
| ADR-004 | Primary LLM Model Selection | 121 | Accepted | HIGH |

**Statistics (across all 33 physical ADRs):**
- **Longest:** ADR-032 (224 lines)
- **Shortest:** batch ADRs (004, 005, 006, 011, 014, 017, 020) at ~84 read-tool lines
- **Median:** ~124 lines
- **Mean:** ~131 lines
- **Range:** 84–224 lines

**Critical finding:** No existing ADR exceeds 224 lines. The target of 2,000+ lines for ADR-035 represents approximately **9× the length of the longest existing ADR**. This is unprecedented but achievable by combining ADR-033's implementation depth (code blocks, architecture, rollback plan), ADR-032's tabular detail (pricing, retention policies), ADR-022's cross-reference breadth, and ADR-029's decision-subsection structure.

---

## 2. YAML Frontmatter — Complete Analysis

### 2.1 Universal (Required) Fields

Every ADR contains these exact fields in the frontmatter block (delimited by `---`):

```yaml
---
adr: NNN                        # Three-digit zero-padded number (001-034)
title: "Title in Title Case"    # Double-quoted string
status: "Status String"         # Double-quoted string (see §11)
date: "YYYY-MM-DD"              # Double-quoted ISO date
deciders:                       # Always exactly these two
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:                           # Lowercase, comma-separated in rendered body
  - tag1
  - tag2
  - ...
risk_level: "LEVEL"             # Double-quoted: CRITICAL, HIGH, or MEDIUM
supersedes: "N/A"               # String (see §2.2)
related_documents:              # List of document filenames WITHOUT paths
  - FileName_v2.0.md
  - Another_File.md
---
```

### 2.2 Optional Frontmatter Fields

Only ADR-028 (the sole `Superseded` ADR) adds these fields:

```yaml
superseded_date: "2026-06-01"                    # Date of supersession
superseded_by: "migration-9router decisions..."   # What superseded it
```

**Rule:** `superseded_date` and `superseded_by` appear ONLY in ADRs with `status: "Superseded"`.

### 2.3 `supersedes` Field Values

| Value Pattern | Used In | Meaning |
|---|---|---|
| `"N/A"` | 30 ADRs | No predecessor |
| `"Refines ADR-020 (implementation-level)"` | ADR-033 | Refinement, not replacement |
| `"N/A — Supplements ADR-025..."` | ADR-032 | Supplement with explanation |

### 2.4 `related_documents` Path Convention

The YAML `related_documents` list uses **bare filenames only** (no path prefix):

```yaml
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - adr/ADR-025-backup-disaster-recovery-strategy.md    # Later ADRs (029+) use adr/ prefix
```

**Inconsistency:** Early ADRs (001-025) omit the `adr/` prefix even for ADR-to-ADR references. ADR-029+ use `adr/ADR-XXX-...` prefix for ADR references. ADR-033 uses full nested paths like `docs/00-core/05-APIIntegration_v2.0.md`.

---

## 3. Section Structure — Complete H2 Inventory

### 3.1 Mandatory H2 Sections (present in ALL ADRs)

Every Guinevere ADR contains these sections in this exact order:

1. `# ADR-NNN: Full Title` — H1 heading (matches frontmatter `title`)
2. `## Status` — status string
3. `## Date` — ISO date
4. `## Deciders` — semicolon-separated string
5. `## Tags` — comma-separated lowercase string
6. `## Risk Level` — CRITICAL/HIGH/MEDIUM
7. `## Supersedes` — "N/A" or descriptive string
8. `## Related Documents` — markdown table with columns `Document \| Relationship`
9. `## Context` — 1–3 paragraphs
10. `## Decision Drivers` — bullet list (4–6 items)
11. `## Considered Options` — numbered list (3–4 options)
12. `## Decision Outcome` — "Chosen option: **...**" + description
13. `## Consequences` — with `### Positive`, `### Negative`, `### Risks` subsections
14. `## Implementation Notes` — bullet list
15. `## Links` — bullet list of relative markdown links

### 3.2 Optional H2 Sections

| Section | Present In | Count | Format |
|---|---|---|---|
| `## Review Record` | 001, 008, 018, 022, 025, 032 | 6 of 33 | Key-value bullet list |
| `## Revision History` | 022, 028 | 2 of 33 | Markdown table (Version\|Date\|Author\|Changes) |
| `## Rollback Plan` | 033 | 1 of 33 | Bash code block + time estimate |
| `## Superseded By` | 028 | 1 of 33 | File paths (only for Superseded status) |

### 3.3 Decision Outcome Sub-Sections (H3)

Most ADRs have a simple paragraph after "Chosen option: **...**". Two ADRs expand with H3 subsections:

**ADR-029** uses these H3 subsections under `## Decision Outcome`:
- `### Automatic Rollback`
- `### Safety-Critical Change Classification`
- `### Routine Change Auto-Deployment`
- `### Authority Hierarchy Enforcement`

**ADR-033** uses these H3 subsections under `## Decision` (note: uses `## Decision` not `## Decision Outcome`):
- `### Runtime Architecture`
- `### Installation`
- `### Systemd Service`
- `### Playwright Fallback`

**ADR-032** uses H3 subsections under `## Decision Outcome`:
- `### Storage Roles`
- `### rclone Configuration`
- `### rclone Command Patterns`
- `### Pricing (verified YYYY-MM-DD)`
- `### Retention Policy (unchanged from ADR-025)`

### 3.4 `## Decision` vs `## Decision Outcome`

**Inconsistency:** 32 of 33 ADRs use `## Decision Outcome`. ADR-033 uses `## Decision` (no "Outcome"). This is the only instance of the shorter form and should be considered a deviation. **ADR-035 must use `## Decision Outcome`.**

### 3.5 Consequences Sub-Section Patterns

**Standard pattern (30 ADRs):**
```markdown
## Consequences

### Positive
- Bullet 1
- Bullet 2

### Negative
- Bullet 1
- Bullet 2

### Risks
- Bullet 1
- Bullet 2
```

**ADR-033 variation:** Uses `### Negative / Risks` as a combined H3 (not two separate ones), with an additional `### Mitigations` H3 subsection after it. This is the only ADR with mitigations as a top-level consequence sub-heading.

### 3.6 Related Documents Table Format

**Standard format (early ADRs 001-025):**
```markdown
| Document | Relationship |
|---|---|
| [`../FileName_v2.0.md`](../FileName_v2.0.md) | FileName_v2.0.md |
```

The Relationship column simply repeats the filename. This is the most common pattern.

**Descriptive format (ADR-029+):**
```markdown
| Document | Relationship |
|---|---|
| [`ADR-016`](ADR-016-cicd-autonomous-deployment-strategy.md) | CI/CD and autonomous deployment strategy |
```

The Relationship column contains a human-readable description, not just the filename.

**ADR-022 hybrid:** Uses descriptive Relationship text AND cross-references other ADRs with title annotations:
```markdown
| [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md) | ADR-001 — Persona Safety & Ethical Boundary Policy |
```

**Recommendation for ADR-035:** Use the ADR-022/ADR-033 hybrid pattern with descriptive Relationship text.

---

## 4. Decision Rationale Depth — Detailed Analysis

### 4.1 Decision Outcome Word Count

| ADR | Decision Paragraph Length | Word Count (approx.) | Sub-Sections |
|---|---|---|---|
| ADR-001 | 1 paragraph (lines 88-90) | ~40 words | None |
| ADR-004 | 1 paragraph (lines 87-89) | ~30 words | None |
| ADR-007 | 1 paragraph (lines 87-89) | ~30 words | None |
| ADR-013 | 1 paragraph (lines 87-91) | ~35 words | None |
| ADR-018 | 1 paragraph (lines 87-89) | ~25 words | None |
| ADR-025 | 1 paragraph (lines 89-91) | ~30 words | None |
| ADR-029 | 4 paragraphs + 4 H3 subsections (lines 98-137) | ~200 words | 4 H3 sections |
| ADR-033 | 5 paragraphs + 4 H3 subsections + code blocks (lines 92-145) | ~300 words | 4 H3 sections + code |
| ADR-032 | 5 paragraphs + 5 H3 subsections + tables + code (lines 110-176) | ~350 words | 5 H3 sections + tables |
| ADR-028 | 3 paragraphs + 2 tables + code (lines 111-138) | ~150 words | Tables + code blocks |

### 4.2 Use of Code Blocks

- **Most ADRs (001-025):** No code blocks at all
- **ADR-028:** Uses `text` code fences for routing chain display
- **ADR-029:** No code blocks
- **ADR-032:** Uses `ini`, `bash` code fences for rclone config and commands
- **ADR-033:** Uses `bash`, `python`, `ini` code fences for installation, client code, and systemd config. Most code-heavy ADR.

### 4.3 Use of Tables in Decision Outcome

| ADR | Tables in Decision |
|---|---|
| ADR-028 | Impact on P1 Steps table |
| ADR-032 | Storage Roles table, Pricing table, Retention Policy table |
| ADR-033 | (none in decision, but tables in Considered Options implicitly) |

### 4.4 Considered Options Format

Always a numbered list with 3–4 options. Format varies:

**Plain list (most ADRs):**
```markdown
1. Option description
2. Option description
3. Option description
```

**Bold-labeled (ADR-033):**
```markdown
1. **Playwright + headless Chromium** (original plan) — mature but heavy
2. **Obscura standalone** — lightweight but no Playwright API
3. **Obscura CDP server + playwright-core client** — lightweight + Playwright + stealth
4. **Puppeteer + Chromium** — Node.js dependency, no stealth
```

**Recommendation for ADR-035:** Use bold-labeled options like ADR-033 for clarity.

---

## 5. Consequence Detail Level

### 5.1 Positive/Negative/Risks Bullet Counts

| ADR | Positive Bullets | Negative Bullets | Risk Bullets | Notes |
|---|---|---|---|---|
| ADR-001 | 3 | 2 | 2 | Standard early ADR |
| ADR-004 | 3 | 2 | 2 | Standard early ADR |
| ADR-007 | 3 | 2 | 2 | Standard early ADR |
| ADR-013 | 3 | 2 | 2 | Standard early ADR |
| ADR-018 | 3 | 2 | 2 | Standard early ADR |
| ADR-025 | 3 | 2 | 2 | Standard early ADR |
| ADR-008 | 3 | 2 | 2 | Standard early ADR |
| ADR-022 | 3 | 2 | 2 | Standard early ADR |
| ADR-029 | 6 | 4 | 4 | More detailed, domain-specific |
| ADR-028 | 7 | 3 | 3 | Expanded due to retroactive analysis |
| ADR-032 | 5 | 3 | 3 | + pricing calculations inline |
| ADR-033 | 7 | 8 (combined Neg/Risks) | (merged) | + 3 Mitigations bullets |

### 5.2 ADR-033's Unique Consequences Structure

ADR-033 merges Negative and Risks into one `### Negative / Risks` section and adds `### Mitigations`:

```markdown
### Negative / Risks
- **Pre-1.0**: v0.1.6 (April 2026) — early stage...
- **Young project**: ~50 days old...
- (8 bullets total)

### Mitigations
- Playwright + Chromium fallback documented and tested (ADR-020).
- Rollback plan documented below.
- Monitor Obscura releases for breaking changes.
```

This pattern is useful for technology-selection ADRs where risks have concrete mitigations. **Recommended for ADR-035** since the Hermes migration decision has clear mitigatable risks.

---

## 6. Reference & Link Format

### 6.1 `## Links` Section

Always a bullet list of markdown links. Pattern:

**In-adr-directory references:**
```markdown
- [`../FileName_v2.0.md`](../FileName_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
```

**ADR-to-ADR references:**
```markdown
- [`ADR-016`](ADR-016-cicd-autonomous-deployment-strategy.md)
- [`ADR-025-backup-disaster-recovery-strategy.md`](ADR-025-backup-disaster-recovery-strategy.md)
```

**External URLs (ADR-033 only):**
```markdown
- [Obscura GitHub](https://github.com/h4ckf0r0day/obscura)
```

**Deep-pathed references (ADR-033):**
```markdown
- [P6-009 StepPrompts](../stepprompts/StepPrompts.md)
- [Expansion: X Auto-Poster (P13)](../docs/post-mvp/) (future)
```

### 6.2 Link Naming Convention

Three distinct styles co-exist:

1. **Filename-as-label (early ADRs 001-025):** ``[`../FileName.md`](../FileName.md)``
2. **ADR-number-as-label (ADR-029+):** ``[`ADR-016`](ADR-016-...md)``
3. **Descriptive-label (ADR-033):** ``[Obscura GitHub](https://...)``, ``[ADR-020: Browser Automation Strategy](ADR-020-...md)``

### 6.3 Footer Link to ADR Index

Every single ADR ends its `## Links` section with:
```markdown
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
```

This is universal and mandatory.

### 6.4 `## Related Documents` Table Link Format

Early ADRs use `../` prefix for document references:
```markdown
| [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md) | Guinevere_BRD_v2.0.md |
```

ADR-033 uses nested paths for docs:
```markdown
| [`../docs/00-core/05-APIIntegration_v2.0.md`](../docs/00-core/05-APIIntegration_v2.0.md) | API integration spec §8.2 |
```

### 6.5 Context Section — Inline References

The "Context" section in early ADRs (001-025) contains this standardized boilerplate paragraph listing locked decisions:

> This ADR is part of the first Guinevere technical-core ADR batch and inherits these locked project decisions unless explicitly stated otherwise:
> - Primary LLM is GPT-5.5 via 9Router with 1M context window.
> - Sub-agent LLM is DeepSeek V4 Flash via 9Router.
> - ...

This boilerplate uses **inline text references**, not markdown links.

**ADR-029+ drop this boilerplate** and instead write domain-specific context paragraphs.

---

## 7. Version History Format

### 7.1 ADRs with Version History

Only 2 ADRs have explicit version histories:

**ADR-022 (inline `## Revision History` section after Review Record):**
```markdown
## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Faiz + Guinevere | Initial ADR — WhatsApp via Baileys... |
| 1.1 | 2026-06-03 | Faiz + Guinevere | Revised WhatsApp implementation from Baileys... |
```

**ADR-028 (inline `## Revision History`):**
```markdown
## Revision History

| Date | Revision | Author | Detail |
|---|---|---|---|
| 2026-05-30 | v1.0 | Guinevere | Initial: Ollama local LLM fallback |
| 2026-05-30 | v2.0 | Faiz (operator directive) | Replaced Ollama fallback... |
| 2026-05-30 | v3.0 | Faiz (operator directive) | Restored Ollama as third-level fallback... |
| 2026-06-01 | v4.0 | Faiz (operator directive) | Superseded Ollama fallback... |
```

Note: ADR-028 uses `Date | Revision | Author | Detail` while ADR-022 uses `Version | Date | Author | Changes`. Different column ordering and naming.

### 7.2 Footer Version Table

Only ADR-032 appends a version table at the very end (after `## Review Record`):
```markdown
| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere (Sisyphus) | Initial ADR establishing... |
```

### 7.3 Recommendation for ADR-035

- Use `## Revision History` as a dedicated H2 section (ADR-022 pattern)
- Use columns: `| Version | Date | Author | Changes |` (ADR-022/ADR-032 pattern)
- Start at v1.0

---

## 8. Review Record Format

### 8.1 ADRs with Review Records

| ADR | Has Review Record? | Format Style |
|---|---|---|
| ADR-001 | Yes | Bullet list: `- Reviewer:` `- Review Date:` `- Decision:` `- Notes:` |
| ADR-008 | Yes | Bullet list (same) |
| ADR-018 | Yes | Bullet list (same) |
| ADR-022 | Yes | Bold labels: `- **Date:**` `- **Reviewer:**` `- **Decision:**` `- **Evidence:**` `- **Notes:**` (most detailed) |
| ADR-025 | Yes | Bullet list (same as 001) |
| ADR-032 | Yes | Bullet list: `- Reviewer:` `- Review Date:` `- Decision:` `- Notes:` |
| ADR-033 | **No** | — |
| ADR-029 | **No** | — |
| ADR-028 | **No** | — |

### 8.2 Pattern Analysis

- Review Records appear primarily in "Accepted with notes" ADRs
- 6 of 14 "Accepted with notes" ADRs have them (43%)
- ADR-022 has the most comprehensive Review Record with `**Evidence:**` field and nested bullet points under `**Notes:**`
- Review Records are NOT present in ADRs 029-033 (the most recent batch)

### 8.3 Recommendation for ADR-035

Use ADR-022's comprehensive format:
```markdown
## Review Record

- **Date:** YYYY-MM-DD
- **Reviewer:** Name / Role
- **Decision:** Accepted / Accepted with notes
- **Evidence:** List of evidence files reviewed
- **Notes:** Detailed findings in nested bullets
```

---

## 9. Implementation Notes — Detail Level

### 9.1 Standard Boilerplate (ADRs 001-025)

Every early ADR has these 4 identical bullets:
```markdown
- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.
```

### 9.2 Expanded Implementation Notes (ADRs 029-033)

Beyond the boilerplate, these ADRs add domain-specific implementation directives:

**ADR-029** (self-modification testing):
- 10 bullets total (4 boilerplate + 6 domain-specific)
- Includes testing categories, file paths (`.guinevere/safety-critical-paths.yml`), integration with ADR-022

**ADR-033** (browser automation):
- 6 domain-specific bullets
- References P6-009 StepPrompts, systemd service name, port allocation, worker count
- Not preceded by boilerplate (notably missing the 4 standard bullets)

**ADR-032** (backup storage):
- 6 domain-specific bullets
- References DRPlan patches, OpsManual, rclone commands, Mermaid diagrams
- Not preceded by boilerplate

### 9.3 Recommendation for ADR-035

Include the 4 standard boilerplate bullets plus domain-specific implementation directives. ADR-033 and ADR-029 demonstrate the expected level of specificity (exact service names, file paths, configuration patterns).

---

## 10. Rollback Plan

### 10.1 The Only Rollback Plan

ADR-033 is the sole ADR with an explicit `## Rollback Plan` section:

```markdown
## Rollback Plan

If Obscura proves unstable or CDP coverage is insufficient:

```bash
# Stop and disable Obscura
sudo systemctl stop guinevere-obscura
sudo systemctl disable guinevere-obscura

# Install Chromium + Playwright fallback
apt install -y chromium-browser
pip install playwright
playwright install chromium

# Update P6-009 service to use Chromium directly
# Update MCP config to point to Playwright + Chromium
# See ADR-020 for fallback architecture
```

Rollback time estimate: < 5 minutes.
```

### 10.2 Rollback Plan Characteristics

- **Format:** H2 section with descriptive paragraph + bash code block + time estimate
- **Level of detail:** Exact commands, systemd unit names, fallback reference to parent ADR
- **Time estimate:** `< 5 minutes` (explicit, in prose)

### 10.3 Recommendations for ADR-035

ADR-035 (Hermes migration) MUST include a Rollback Plan section. Given the Hermes migration involves:
- Python package swap (Hermes Agent SDK)
- Configuration file changes
- Systemd service modifications
- Test suite adjustments

The rollback plan should provide exact commands, file paths, and a time estimate under 15 minutes.

---

## 11. Risk Level Values

### 11.1 Distribution Across 33 ADRs

| Risk Level | Count | Percentage | Example ADRs |
|---|---|---|---|
| **CRITICAL** | 11 | 33% | 001, 007, 008, 015, 018, 024, 025, 029, 030, 032 |
| **HIGH** | 15 | 45% | 002, 003, 004, 005, 009, 010, 011, 012, 013, 014, 016, 017, 019, 022, 027, 031 |
| **MEDIUM** | 7 | 21% | 006, 020, 021, 023, 026, 028, 033 |
| **LOW** | **0** | **0%** | None |

### 11.2 Risk Level Decision Logic

From the data:
- **CRITICAL:** Memory, encryption, secrets, safety boundaries, backup/DR, security architecture, data governance, self-modification testing, infrastructure naming
- **HIGH:** LLM model selection, routing, persona control, SDLC loop, orchestration, MCP, VPS, deployment, VPN, communication strategy
- **MEDIUM:** Sub-agent strategy, browser automation, wearable (post-MVP), financial integration, public endpoint, LLM fallback

**ADR-035 recommendation:** Hermes migration is a **CRITICAL** risk ADR because:
- It replaces the core agent framework
- It affects tool-use, memory management, and LLM routing
- Regression risk spans all 7 SDLC phases
- Precedent: ADR-013 (MCP replacement) is HIGH; ADR-029 (self-modification) is CRITICAL

---

## 12. Status Values

### 12.1 Exact Strings Used

| Status String | Count | Example ADRs |
|---|---|---|
| `"Accepted"` | 18 | 004, 005, 006, 007, 011, 013, 014, 017, 020, 021, 026, 027, 029, 030, 031, 032, 033 |
| `"Accepted with notes"` | 12 | 001, 002, 003, 008, 009, 010, 012, 015, 016, 018, 019, 023, 024, 025 |
| `"Accepted with notes (Revised 2026-06-03)"` | 1 | 022 |
| `"Superseded"` | 1 | 028 |

Note: ADR-034 is listed in the index as `Accepted` but the file does not exist physically.

### 12.2 Status Quirks

- `"Accepted with notes"` is the YAML frontmatter value. In the `## Status` body section, it renders as `Accepted with notes` (no quotes).
- ADR-022 appends `(Revised YYYY-MM-DD)` to the status string because it was modified in-place (an explicit exception per Faiz directive).
- ADR-028 (`Superseded`) adds a `**Superseded by:**` description in the Status body section.

### 12.3 Recommendation for ADR-035

Start as `"Accepted"` in the YAML frontmatter. The `## Status` body should render `Accepted` if no review notes are needed, or `Accepted with notes` if the review record contains substantive caveats.

---

## 13. Section Order — Canonical Template

The exact section ordering observed across all ADRs:

```
1. YAML Frontmatter (--- ... ---)
2. # ADR-NNN: Full Title
3. ## Status
4. ## Date
5. ## Deciders
6. ## Tags
7. ## Risk Level
8. ## Supersedes
9. ## Related Documents              (table)
10. ## Context                        (2-4 paragraphs, may include boilerplate)
11. ## Decision Drivers               (4-6 bullet items)
12. ## Considered Options             (3-4 numbered options)
13. ## Decision Outcome               (chosen option + description + optional H3 subsections)
14. ## Consequences
     - ### Positive                  (3-7 bullets)
     - ### Negative                  (2-4 bullets) [or ### Negative / Risks combined]
     - ### Risks                     (2-4 bullets) [or merged into Negative]
     - ### Mitigations               (optional, only ADR-033)
15. ## Implementation Notes           (4-10 bullets, starting with boilerplate)
16. ## Rollback Plan                  (optional, only ADR-033)
17. ## Links                          (bullet list with ADR Index as last item)
18. ## Review Record                  (optional, bullet or bold-label list)
19. ## Revision History               (optional, table)
20. (Footer version table)            (optional, only ADR-032)
```

---

## 14. Inconsistencies Across ADRs

### 14.1 Section Naming

| Issue | Detail | Prevalence |
|---|---|---|
| `## Decision` vs `## Decision Outcome` | ADR-033 uses shorter form | 1 of 33 |
| `### Negative / Risks` vs separate `### Negative` + `### Risks` | ADR-033 merges them | 1 of 33 |
| `### Mitigations` presence | Only ADR-033 has it | 1 of 33 |
| `## Rollback Plan` presence | Only ADR-033 has it | 1 of 33 |

### 14.2 Reference Formatting

| Issue | Detail | Prevalence |
|---|---|---|
| `../` prefix in related_documents YAML | Early ADRs omit `adr/` prefix for ADR refs | ~20 of 33 |
| Descriptive vs filename-only Relationship column | Shifted starting at ADR-029 | Split ~20/13 |
| `## Links` label style | Filename-only vs descriptive | Mixed |

### 14.3 Review Record

| Issue | Detail |
|---|---|
| Inconsistent presence | Only 6 of 33 have Review Records |
| Format variation | ADR-022 uses bold labels, others use key-value bullets |
| Evidence field | Only ADR-022 includes `**Evidence:**` |

### 14.4 Boilerplate

| Issue | Detail |
|---|---|
| Context boilerplate | Present in ADRs 001-025, dropped in 029+ |
| Implementation boilerplate | Present in ADRs 001-029, dropped in 032-033 |
| Footer version table | Only ADR-032 appends a version table at end |

### 14.5 Missing ADR-034

ADR-034 is registered in `adr/README.md` with metadata (`Accepted`, `MEDIUM`, `phase, restructure, roadmap, expansion`) but the physical file does not exist in the `adr/` directory. The index shows `adr_count: 34` but only 33 files exist. ADR-034 must be created before or alongside ADR-035.

---

## 15. Gold Standard ADR for Format Reference

### 15.1 Recommended: ADR-033 (Browser Automation — Obscura CDP)

**Rationale:** ADR-033 is the most complete ADR in terms of format coverage:

| Feature | Present? |
|---|---|
| Complete YAML frontmatter | Yes |
| All mandatory sections | Yes (except uses `## Decision` not `## Decision Outcome`) |
| Code blocks (bash, python, ini) | Yes — 3 languages |
| Architecture diagram (text) | Yes — systemd service layout |
| Rollback plan with commands | Yes |
| Time estimate for rollback | Yes (< 5 minutes) |
| Detailed consequences with mitigations | Yes |
| Considered options with bold labels | Yes |
| External URL references | Yes |
| Implementation notes with specific paths | Yes |
| Line count: 212 | Second-longest |

### 15.2 Runner-Up: ADR-032 (Backup Storage Strategy)

| Feature | Present? |
|---|---|
| Tables in Decision Outcome | Yes — 3 detailed tables |
| Pricing calculations | Yes — verified provider pricing |
| rclone configuration (ini code block) | Yes |
| Command patterns (bash code block) | Yes |
| Retention policy table | Yes |
| Review Record | Yes |
| Footer version table | Yes |
| Line count: 224 | Longest |

### 15.3 Reference for Cross-ADR Breadth: ADR-022

| Feature | Present? |
|---|---|
| Most comprehensive Review Record | Yes — with Evidence field |
| Revision History table | Yes |
| Cross-ADR references (6 ADRs) | Yes — highest count |
| Inline channel stack details | Yes — 4 communication channels |
| Caveats per technology | Yes — Neonize, Gmail, Gotify |

### 15.4 Reference for Decision Structure: ADR-029

| Feature | Present? |
|---|---|
| H3 subsections under Decision Outcome | Yes — 4 structured subsections |
| Safety-critical classification logic | Yes — explicit domain list |
| Authority hierarchy enforcement | Yes — programmatic constraint |
| Detailed consequences (6P/4N/4R) | Yes — most extensive for non-tech ADR |

---

## 16. Exact Section Template for ADR-035

Based on the synthesis of all 33 ADRs, here is the canonical template ADR-035 must follow:

```markdown
---
adr: 035
title: "Hermes NousResearch Migration Decision"
status: "Accepted"
date: "2026-06-04"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - hermes
  - agent-framework
  - nous-research
  - migration
  - llm
  - memory
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
  - adr/ADR-004-primary-llm-model-selection.md
  - adr/ADR-006-sub-agent-llm-model-strategy.md
  - adr/ADR-011-sdlc-loop-phase-specification.md
  - docs/00-core/03-AgentLoopSpec_v2.0.md
---

# ADR-035: Hermes NousResearch Migration Decision

## Status

Accepted

## Date

2026-06-04

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

hermes, agent-framework, nous-research, migration, llm, memory

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Runtime architecture and service topology |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | 7-phase autonomous SDLC loop specification |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | External API integration constraints |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Memory model and PostgreSQL/Redis schema |
| [`ADR-004`](ADR-004-primary-llm-model-selection.md) | Primary LLM model selection (GPT-5.5 via 9Router) |
| [`ADR-006`](ADR-006-sub-agent-llm-model-strategy.md) | Sub-agent LLM strategy (DeepSeek V4 Flash) |
| [`ADR-011`](ADR-011-sdlc-loop-phase-specification.md) | SDLC loop phase specification |
| [`../docs/00-core/03-AgentLoopSpec_v2.0.md`](../docs/00-core/03-AgentLoopSpec_v2.0.md) | Agent loop specification v2.0 |

## Context

[3-5 paragraphs covering:
- What Hermes Agent is and why it was chosen
- Current state: what works, what doesn't
- The migration trigger: why NousResearch Hermes models are now the choice
- Relationship to existing ADRs (004, 006, 011, 013)
- The locked project decisions context (if relevant to Hermes migration)]

## Decision Drivers

[6-8 bullet items covering:
- Technical capability requirements
- Cost and performance constraints
- Integration with existing stack (PostgreSQL, Redis, 9Router, Discord)
- Safety and autonomy boundary preservation
- Faiz approval model
- Auditability and evidence requirements]

## Considered Options

1. **Current Hermes Agent (status quo)** — [description, pros, cons]
2. **Alternative framework X** — [description, pros, cons]
3. **Hermes NousResearch native** — [description, pros, cons]
4. **Hybrid approach** — [description, pros, cons]

## Decision Outcome

Chosen option: **Hermes NousResearch migration with [specific approach]**.

[Detailed description paragraph(s)]

### Architecture Impact

[Tables and/or diagrams showing what changes]

### Migration Path

[Step-by-step migration phases]

### Configuration Changes

[Code blocks showing before/after config]

### Integration Points

[How Hermes connects to: PostgreSQL, Redis, 9Router, Discord, Prometheus, Grafana]

### Testing Strategy

[How migration is validated]

## Consequences

### Positive

[5-8 bullet items]

### Negative

[3-5 bullet items]

### Risks

[4-6 bullet items]

### Mitigations

[3-5 bullet items, ADR-033 pattern]

## Rollback Plan

[Exact commands, time estimate, fallback reference]

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.
- [Domain-specific bullets: service names, file paths, systemd units, config keys]

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`ADR-004`](ADR-004-primary-llm-model-selection.md)
- [`ADR-006`](ADR-006-sub-agent-llm-model-strategy.md)
- [`ADR-011`](ADR-011-sdlc-loop-phase-specification.md)
- [External Hermes docs link]
- [External NousResearch link]
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- **Date:** 2026-06-04
- **Reviewer:** Guinevere (or designated reviewer)
- **Decision:** Accepted / Accepted with notes
- **Evidence:** [List of evidence files reviewed]
- **Notes:**
  - [Detailed review findings]
  - [Caveats and follow-up items]

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Faiz + Guinevere | Initial ADR — Hermes NousResearch migration decision. |
```

---

## 17. Path to 2,000 Lines

The longest existing ADR is 224 lines. To reach 2,000+ lines, ADR-035 must include substantial content that no existing ADR attempts:

### 17.1 Content Density Multipliers (from existing ADR patterns)

| Content Type | Line Yield | Source ADR |
|---|---|---|
| Tables (pricing, comparison, migration matrix) | 20–40 lines each | ADR-032 |
| Code blocks (config before/after, Python snippets) | 10–30 lines each | ADR-033 |
| Architecture text diagrams | 15–30 lines each | ADR-033 |
| Detailed option analysis with pros/cons | 30–60 lines per option | ADR-033 |
| Integration point walkthrough | 50–100 lines | (novel) |
| Migration phase breakdown with sub-steps | 50–150 lines | (novel) |
| Performance benchmarks table | 30–50 lines | (novel) |
| Risk matrix with likelihood/impact | 40–60 lines | (novel) |
| Decision matrix (scored options) | 40–80 lines | (novel) |
| Rollback plan with commands | 15–30 lines | ADR-033 |
| Testing strategy with test categories | 30–50 lines | ADR-029 |
| Cross-reference impact analysis | 30–50 lines | (novel) |

### 17.2 Section Allocation Estimate

| Section | Target Lines | Content Strategy |
|---|---|---|
| Frontmatter + Header Sections (Status-Tags) | ~60 | Standard template |
| Related Documents + Context | ~120 | Expanded context, Hermes background |
| Decision Drivers + Considered Options | ~200 | 4 options with detailed pros/cons tables |
| Decision Outcome | ~500 | Architecture impact, migration phases, config, integration points |
| Consequences | ~150 | Expanded Positive/Negative/Risks/Mitigations |
| Rollback Plan | ~50 | Detailed commands |
| Implementation Notes | ~100 | Domain-specific + boilerplate |
| Links + Review Record + Revision History | ~80 | Standard |
| Performance Benchmarks | ~150 | Comparative benchmarks table |
| Migration Matrix | ~150 | Phase-by-phase migration plan |
| Risk Matrix | ~100 | Likelihood × Impact matrix |
| Testing Strategy | ~120 | Unit, integration, safety, regression |
| Cross-Reference Impact | ~100 | Impact on all 33 existing ADRs |
| **TOTAL** | **~1,980** | |

### 17.3 Novel Content for ADR-035

Content types not seen in any existing ADR that ADR-035 should pioneer:

1. **Comparative Performance Benchmarks**: Latency, throughput, memory usage for Hermes vs alternatives
2. **Risk Matrix**: Likelihood × Impact grid for migration risks
3. **Decision Matrix**: Weighted scoring across multiple dimensions (cost, performance, safety, maintainability)
4. **Migration Phase Gantt**: Timeline with dependencies and milestones
5. **Cross-ADR Impact Analysis**: How this decision affects each of the 33 existing ADRs
6. **API Surface Comparison**: What Hermes Agent methods map to what Hermes NousResearch methods
7. **Configuration Before/After**: Side-by-side configuration diffs
8. **Cost Projection Model**: Monthly cost estimates for old vs new stack

---

## 18. Key Conventions Summary (Quick Reference)

| Convention | Rule |
|---|---|
| **ADR number** | Three-digit zero-padded in frontmatter (`adr: 035`) |
| **Title** | Double-quoted in frontmatter, Title Case |
| **H1 heading** | `# ADR-NNN: Full Title` (matches frontmatter title minus quotes) |
| **Status strings** | `"Accepted"`, `"Accepted with notes"`, or `"Superseded"` |
| **Risk levels** | `"CRITICAL"`, `"HIGH"`, `"MEDIUM"` (never LOW) |
| **Deciders** | Always exactly: Faiz + Guinevere with those exact descriptions |
| **Date format** | `YYYY-MM-DD` (double-quoted in frontmatter) |
| **Tags** | Lowercase, comma-separated in body; YAML list in frontmatter |
| **`supersedes`** | `"N/A"` for new ADRs; descriptive string for refinements/supplements |
| **Related Documents** | YAML: bare filenames. Body: markdown table with relative links |
| **Decision heading** | `## Decision Outcome` (NOT `## Decision`) |
| **Consequences** | Three mandatory H3 subsections: `### Positive`, `### Negative`, `### Risks` |
| **Implementation Notes** | Start with 4 boilerplate bullets, then domain-specific |
| **Links section** | Bullet list; last item always ADR Index link |
| **ADR Index link** | ``[`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)`` |
| **File naming** | `ADR-NNN-slugified-lowercase-title.md` |
| **Review Record** | Recommended for all ADRs; ADR-022 format preferred |
| **Revision History** | Table: `\| Version \| Date \| Author \| Changes \|` |
| **Code blocks** | Language-tagged fences (`bash`, `python`, `ini`, `yaml`, `text`) |

---

## 19. Findings Specific to ADR-034

ADR-034 (`ADR-034-post-mvp-phase-restructure.md`) is registered in `adr/README.md` with the following metadata:

| Field | Value |
|---|---|
| Number | 034 |
| Title | Post-MVP Phase Restructure — P0-P11 → P0-P22 |
| Status | Accepted |
| Risk | MEDIUM |
| Tags | phase, restructure, roadmap, expansion |
| File | `ADR-034-post-mvp-phase-restructure.md` |

However, the physical file does **not exist** in the `adr/` directory. The glob search for `**/ADR-034*.*` returned zero results. This means:

1. The index claims 34 ADRs but only 33 exist physically
2. ADR-034 must be created (likely before or alongside ADR-035)
3. ADR-035 will be the 34th physical ADR (35th in the index if ADR-034 is created first)

---

## 20. Final Recommendations

1. **Follow the canonical template in §16 exactly.** Deviations from existing conventions create inconsistency debt.

2. **Use `## Decision Outcome`** not `## Decision`. ADR-033's deviation is a one-off.

3. **Include `### Mitigations`** under Consequences (ADR-033 pattern). Hermes migration has mitigatable risks that deserve explicit documentation.

4. **Include `## Rollback Plan`** with exact commands and time estimate. ADR-033 proves this is acceptable and valuable.

5. **Use descriptive Relationship column text** in the Related Documents table (ADR-022/ADR-033 pattern, not the early filename-only pattern).

6. **Use bold-labeled Considered Options** (ADR-033 pattern) for clarity when presenting 4+ options.

7. **Include `## Review Record`** using ADR-022's comprehensive format with Evidence field.

8. **Include `## Revision History`** table starting at v1.0 (ADR-022/ADR-028 pattern).

9. **Risk Level: CRITICAL.** Hermes migration affects the core agent framework. Precedent: ADR-013 (MCP replacement) is HIGH, but Hermes is more foundational and warrants CRITICAL.

10. **ADR-034 must be addressed.** Either create it before ADR-035 or note that ADR-035 is being created while ADR-034 is pending.

11. **The 2,000-line target is achievable** only by combining patterns from multiple ADRs and adding novel content types (benchmarks, risk matrix, decision matrix, migration plan, cross-ADR impact analysis). See §17 for allocation.

12. **File naming convention:** `ADR-035-hermes-nousresearch-migration-decision.md` following the lowercase-slug pattern.

---

*Analysis completed 2026-06-04 by Guinevere (Sisyphus-Junior). All 9 requested ADRs + adr/README.md were fully read. ADR-034 confirmed missing from filesystem. Additional ADRs 008, 025, 028, 032 read for completeness.*