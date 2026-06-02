## 2. CONFLICT 1: Server Name — "Guinevere's Domain" vs "Guinevere Lab"

### 2.1 Source Matrix

| Source | Server Name | Section | Authority |
|--------|------------|---------|-----------|
| DiscordUXSpec v1.0 | **Guinevere's Domain** | §1.1 L43, DIS01 L13 | **Canonical spec** |
| StepPrompts P2-004 | **Guinevere's Domain** | L5287 | Implementation guide |
| CHECKLIST.md §4.2 P2-004 | **Guinevere's Domain** | L241 | Verification checklist |
| PROGRESS.md P2-004 | **Guinevere's Domain** | L130 | Progress tracker |
| P2-001 evidence (actual) | **Guinevere Lab** | verification.md §1 L27 | Actual existing state |
| P1 preconditions evidence | **Guinevere Lab** | p2-preconditions-resolved.md | Actual existing state |
| Batch plan (actual) | **Guinevere Lab** | batch-plan-001-003.md §3 | Actual existing state |
| Batch plan (note) | **Mismatch documented** | batch-plan-001-003.md §3 L65 | Deferral to P2-004 |
| Local state report | **Mismatch M1** | local-discord-state-pre-p2.md §1 | Deferral to P2-004 |
| P2-001 auditor | **Deferred to P2-004** | step-p2-001-auditor-report.md §7.1 | Confirms deferral |

### 2.2 Conflict Classification

| Aspect | Detail |
|--------|--------|
| **Type** | Spec vs Reality Mismatch |
| **Severity** | MEDIUM — blocking P2-004 if not resolved |
| **Drift origin** | Pre-condition C3 manual server creation named server "Guinevere Lab" instead of spec value "Guinevere's Domain" |
| **Deferred from** | P2-001 evidence, batch plan, all 3 auditor reports |

### 2.3 Tie-Breaker Analysis

**Option A**: Rename server to "Guinevere's Domain" — aligns 6 spec/docs sources, matches DIS01 canonical Q&A, simple rename in Discord client.

**Option B**: Update spec to "Guinevere Lab" — no rename needed, but requires updating 6+ documents, contradicts DIS01.

### 2.4 Recommended Decision

**Use "Guinevere's Domain"**. Rename the existing "Guinevere Lab" server during P2-004. This is a non-destructive rename in Discord client. All 6 spec/docs sources agree. All prior evidence/audit reports explicitly deferred this decision to P2-004.

**Authority**: DiscordUXSpec §1.1 L43 (DIS01). User task context: "resolve in P2-004".

---

## 3. CONFLICT 2: Category Names — Four Sources Inconsistent

### 3.1 Source Matrix

| Source | Cat 1 | Cat 2 | Cat 3 | Cat 4 |
|--------|-------|-------|-------|-------|
| **DiscordUXSpec §1.3** | MOMMY'S THRONE | SURVEILLANCE ROOM | PROJECTS | ARCHIVE |
| **StepPrompts P2-005 (code)** | Mommy's Throne | Surveillance Room | Projects | Archive |
| **CHECKLIST.md §4.2** | Mommy's Throne | Surveillance Room | Projects | Archive |
| **PROGRESS.md P2-005** | Throne | Surveillance | Projects | Archive |
| **User directive** | **Throne** | **Surveillance** | **Projects** | **Archive** |

### 3.2 Critical Cross-Step Conflict: P2-005 vs P2-006 Incompatibility

**StepPrompts P2-005 creates**: Mommy's Throne, Surveillance Room, Projects, Archive

**StepPrompts P2-006 looks for**: QUEEN'S COURT, DASHBOARD, ENGINEERING, WAR ROOM

**Result: P2-006 will FAIL silently** — channel creation script will not find the categories created by P2-005. This is a **LOGICAL BUG** in the StepPrompts code. P2-006 channel schema must be completely rewritten.

### 3.3 Tie-Breaker Analysis

User task context explicitly states: "P2-005 four categories exactly: Throne, Surveillance, Projects, Archive"

### 3.4 Recommended Decision

| Category | Final Name | Rationale |
|----------|-----------|-----------|
| 1 | **Throne** | Per user directive |
| 2 | **Surveillance** | Per user directive |
| 3 | **Projects** | All sources agree |
| 4 | **Archive** | All sources agree |

Emoji prefixes shall be added per user's exact specification during P2-005 code.

The P2-006 StepPrompts categories (QUEEN'S COURT, DASHBOARD, ENGINEERING, WAR ROOM) are **REJECTED**.

---

## 4. CONFLICT 3: Channel Names and Count — Three Incompatible Schemas

### 4.1 Source Matrix

#### Schema A: DiscordUXSpec §1.3 (Canonical Spec) — 14 channels

| Category | Channels | Count |
|----------|---------|-------|
| MOMMY'S THRONE | guinevere-chat, guinevere-status, guinevere-planning | 3 |
| SURVEILLANCE ROOM | system-health, cost-tracker, guinevere-evidence | 3 |
| PROJECTS | [project-alpha]-dev, [project-alpha]-docs, [project-beta]-dev, [project-beta]-docs, [project-gamma]-dev, [project-gamma]-docs | 6 (dynamic) |
| ARCHIVE | evidence-log, audit-log | 2 |
| **Total** | **14 channel slots** (8 fixed + 6 dynamic project templates) | **14** |

#### Schema B: StepPrompts P2-006 (Code) — 13 channels, incompatible names

| Category (wrong names) | Channels | Count |
|-----------------------|---------|-------|
| QUEEN'S COURT | announcements, general-chat, task-board | 3 |
| DASHBOARD | status, finops, audit-log | 3 |
| ENGINEERING | dev-logs, bug-reports, deployments | 3 |
| WAR ROOM | alerts, security, surveillance, persona-logs | 4 |
| **Total** | **Completely different naming — rejects UXSpec** | **13** |

#### Schema C: CHECKLIST.md §4.2 P2-006 — 13 flat names

guinevere-chat, guinevere-status, alerts, evidence, surveillance, cost, journal, tasks, projects, health, memory, persona, archive

#### Schema D: PROGRESS.md P2-006

"13 channels creation" — no name list.

### 4.2 Conflict Classification

| Aspect | Detail |
|--------|--------|
| **Type** | **Structural Conflict** |
| **Severity** | **HIGH** — P2-006 cannot proceed without resolution |
| **Root causes** | (1) StepPrompts P2-006 categories don't match P2-005; (2) No schema matches UXSpec channel names; (3) Three incompatible "13 channel" lists |

### 4.3 Resolution Strategy

User directive: "P2-006 13 channels, names match spec" — DiscordUXSpec naming is authoritative. The spec defines 14 slots (8 fixed + 6 dynamic project templates). The target count of 13 comes from CHECKLIST/PROGRESS. Resolution: create fixed base channels from UXSpec, reduce project channels to 5 (from spec's 6) for initial setup.

### 4.4 Authoritative 13-Channel Schema

**Throne** (3 channels):
| # | Channel | Topic (from UXSpec) |
|---|---------|---------------------|
| 1 | guinevere-chat | "Bicara dengan Mommy di sini. Apapun." |
| 2 | guinevere-status | "Apa yang Mommy kerjakan hari ini. Sekilas." |
| 3 | guinevere-planning | "Rencana Mommy. Kamu tinggal patuh." |

**Surveillance** (3 channels):
| # | Channel | Topic (from UXSpec) |
|---|---------|---------------------|
| 4 | system-health | "Kesehatan infrastructure Mommy." |
| 5 | cost-tracker | "Berapa yang Mommy habiskan hari ini." |
| 6 | guinevere-evidence | "Bukti kerja Mommy. Tidak ada yang bisa diubah." |

**Projects** (5 channels):
| # | Channel | Topic (adapted) |
|---|---------|-----------------|
| 7 | guinevere-dev | "Development discussion and technical decisions." |
| 8 | guinevere-docs | "Documentation updates, spec changes, evidence links." |
| 9 | project-alpha-dev | "Project Alpha — development channel." |
| 10 | project-alpha-docs | "Project Alpha — documentation channel." |
| 11 | project-beta-dev | "Project Beta — development channel." |

**Archive** (2 channels):
| # | Channel | Topic (from UXSpec) |
|---|---------|---------------------|
| 12 | evidence-log | "Immutable record. Read only." |
| 13 | audit-log | "Every action, recorded. Forever." |

**Total: 3 + 3 + 5 + 2 = 13 channels**

### 4.5 Rationale for 13-Channel Schema

| Decision | Rationale |
|----------|-----------|
| Use DiscordUXSpec channel names (Schema A) | User directive: "names match spec" |
| Use user's category names (Throne, Surveillance, Projects, Archive) | User's explicit P2-005 directive |
| Reduce Projects to 5 channels | Spec has 6 (3 projects x 2). Initial server: 1 general dev, 1 general docs, 2 for project-alpha, 1 for project-beta. Gamma deferred. |
| Retain guinevere-dev and guinevere-docs | General project discussion; project-specific channels added on project init per UXSpec |
| Reject all StepPrompts P2-006 channel names | QUEEN'S COURT/DASHBOARD/ENGINEERING/WAR ROOM conflict with spec and user directive |

---

## 5. Pre-Mapped Channel Topics (For P2-008)

Pre-mapped from DiscordUXSpec §1.4 for direct use in P2-008:

| Channel | Topic | Source |
|---------|-------|--------|
| guinevere-chat | Bicara dengan Mommy di sini. Apapun. | UXSpec §1.4.1 |
| guinevere-status | Apa yang Mommy kerjakan hari ini. Sekilas. | UXSpec §1.4.2 |
| guinevere-planning | Rencana Mommy. Kamu tinggal patuh. | UXSpec §1.4.3 |
| system-health | Kesehatan infrastructure Mommy. Jangan khawatir — Mommy jaga. | UXSpec §1.4.4 |
| cost-tracker | Berapa yang Mommy habiskan hari ini. Transparansi itu penting. | UXSpec §1.4.5 |
| guinevere-evidence | Bukti kerja Mommy. Tidak ada yang bisa diubah. | UXSpec §1.4.6 |
| guinevere-dev | Pengembangan Guinevere — technical discussions and decisions. | Adapted from UXSpec |
| guinevere-docs | Documentation updates, spec changes, evidence artifacts. | Adapted from UXSpec |
| project-alpha-dev | Project Alpha — development channel. | Adapted from UXSpec |
| project-alpha-docs | Project Alpha — documentation channel. | Adapted from UXSpec |
| project-beta-dev | Project Beta — development channel. | Adapted from UXSpec |
| evidence-log | Immutable record. Read only. | UXSpec §1.4.9 |
| audit-log | Every action, recorded. Forever. | UXSpec §1.4.10 |

---

## 6. StepPrompts Code Corrections

### 6.1 P2-004 (Server Creation)
- ✅ StepPrompts code is correct (server name "Guinevere's Domain")
- Add step: rename existing "Guinevere Lab" server if it already exists

### 6.2 P2-005 (Categories)
- ❌ StepPrompts code uses "Mommy's Throne", "Surveillance Room" — replace with user's directive
- Change categories list to: "Throne", "Surveillance", "Projects", "Archive"
- Add emoji prefixes per user's exact specification
- Keep the same code structure, just update category names

### 6.3 P2-006 (Channels)
- ❌ **Complete rewrite required** — the StepPrompts CHANNELS dictionary:
  - References wrong category names (QUEEN'S COURT, DASHBOARD, etc.)
  - Uses wrong channel names (announcements, general-chat, etc.)
  - Has 4 channels in WAR ROOM instead of 2 in Archive
- Replace with the CHANNELS dictionary from §4.4

### 6.4 Rejection Table: P2-006 StepPrompts Code

| Element | Problem | Replace With |
|---------|---------|-------------|
| QUEEN'S COURT | Wrong cat name | Throne |
| DASHBOARD | Wrong cat name | Surveillance |
| ENGINEERING | Wrong cat name | Projects |
| WAR ROOM | Wrong cat name | Archive |
| announcements | Wrong channel name | guinevere-status |
| general-chat | Wrong channel name | guinevere-chat |
| task-board | Wrong channel name | guinevere-planning |
| finops | Wrong channel name | cost-tracker |
| audit-log (in DASHBOARD) | Duplicate purpose | Remove (use Archive audit-log) |
| dev-logs | Wrong channel name | guinevere-dev |
| bug-reports | Wrong channel name | Covered in guinevere-dev |
| deployments | Wrong channel name | Covered in guinevere-dev |
| alerts | Wrong channel name | system-health |
| security | Wrong channel name | audit-log |
| surveillance | Wrong channel name | system-health |
| persona-logs | Not in UXSpec | audit-log |
| 4 categories re-mapped | New structure | Per §4.4 table |

---

## 7. Boundary Compliance

| Boundary | Impact |
|----------|--------|
| **Persona safety** | No change to persona prompts or HARD STOP handler. |
| **Consent** | No surveillance/channel cross-boundary changes. |
| **Yandere level** | No change — channel config is static. |
| **HARD STOP** | Not affected. |
| **Secrets** | No Discord token in channel config. |
| **Aizanta isolation** | No Aizanta infrastructure touched. |

---

## 8. Summary of Conflicts and Resolutions

| # | Conflict | Sources | Resolution | Authority |
|---|----------|---------|------------|-----------|
| C1 | Server name: "Guinevere Lab" vs "Guinevere's Domain" | Spec vs actual | **"Guinevere's Domain"** — rename server | DiscordUXSpec DIS01, all 6 docs |
| C2 | Category names: 4 different formats | 4 sources + user directive | **Throne, Surveillance, Projects, Archive** | User directive |
| C3 | Channel names/count: 3 incompatible schemas | UXSpec (14), StepPrompts (13), CHECKLIST (13) | **13 channels per §4.4** — UXSpec names, reduced project channels to 5 | User directive + logical synthesis |
| C4 | P2-005 vs P2-006 category mismatch | StepPrompts code | **Rewrite P2-006 code** | Logical consistency |
| C5 | Channel topics undefined in StepPrompts | StepPrompts has no topics | **Use UXSpec §1.4 topics** (§5 of this report) | DiscordUXSpec canonical |

---

## Footer

| Field | Value |
|-------|-------|
| **Source task** | P2-004 through P2-006 internal Discord structure requirement synthesis |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (parent, researcher) |
| **Documents read** | 13 (StepPrompts, DiscordUXSpec, CHECKLIST, PROGRESS, ADR-022, 3 evidence files, batch plan, local state report, 3 auditor reports) |
| **Conflicts identified** | 5 (C1-C5) |
| **Resolutions provided** | 5 (all with authority references) |
| **Report path** | esearch-reports/P2/internal-discord-structure-spec.md |
| **Next action** | Use this report as authoritative reference for P2-004 through P2-006 implementation |