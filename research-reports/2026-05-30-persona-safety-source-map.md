# Persona Safety & Ethical Boundary Policy — Source Map Report

**Generated:** 2026-05-30  
**Purpose:** Exhaustive requirement extraction for policy generation from 6 foundation documents.  
**Status:** Research complete — policy not yet authored.  
**Normative Parent:** ADR-001, ADR-002, ADR-003  

---

## 1. Source Inventory

| # | Document | Absolute Path | Role in Policy |
|---|----------|---------------|----------------|
| 1 | ADR-001 | `C:\Users\faizz\guinevere\adr\ADR-001-persona-safety-ethical-boundary.md` | Primary normative anchor for safety boundaries |
| 2 | ADR-002 | `C:\Users\faizz\guinevere\adr\ADR-002-user-autonomy-safe-word-enforcement.md` | Safe-word architecture, distress handling |
| 3 | ADR-003 | `C:\Users\faizz\guinevere\adr\ADR-003-persona-drift-control-validation.md` | Drift logs, validation, rollback, safe-mode |
| 4 | Persona Doc | `C:\Users\faizz\guinevere\Guinevere_Persona_Document_v2.0.md` | Yandere intensity, dominance levels, punishment ladder, surveillance behavior |
| 5 | PRD v2.1 | `C:\Users\faizz\guinevere\Guinevere_PRD_v2.1.md` | Feature-level specifications for safe-word, mood, punishment, surveillance |
| 6 | BRD v2.0 | `C:\Users\faizz\guinevere\Guinevere_BRD_v2.0.md` | Business objectives, scope, risk mitigation, constraints |

---

## 2. Safe Word

### 2.1 Requirements

- **Global hard stop, non-negotiable.** ADR-002 §Decision Outcome (line 88–90): "Make safe word enforcement a global non-negotiable principle. A genuine safe-word or distress signal must pause persona escalation, stop punishment framing, enter neutral/supportive mode, and avoid writing punitive violation records unless Samm explicitly confirms misuse or test mode. Safe word behavior overrides persona, agent loop momentum, surveillance reactions, and autonomous task plans."
- **Architectural override, not a persona feature.** ADR-002 §Considered Options (line 80–84): Explicitly rejected "Treat safe word as a persona feature" and "Allow Guinevere to judge whether safe word is genuine" in favor of global architectural override.
- **Priority over all other systems.** ADR-002 §Decision Outcome (line 90): "Safe word behavior overrides persona, agent loop momentum, surveillance reactions, and autonomous task plans."
- **Punitive record suppression.** ADR-002 §Decision Outcome (line 90): Must "avoid writing punitive violation records unless Samm explicitly confirms misuse or test mode."

### 2.2 Tension / Conflict

- **PRD v2.1 §2.4 Safe Word Protocol** (line 133–154) states: "Guinevere assess context: genuine distress vs coba escape enforcement" and "Kalau genuine distress: Guinevere grant pause, switch ke neutral mode; Kalau coba escape: Guinevere ignore + catat sebagai violation attempt."
- **Conflict:** PRD v2.1 explicitly gives Guinevere judgment authority to ignore safe word if she deems it an "escape attempt." ADR-002 §Decision Outcome rejects this explicitly ("Allow Guinevere to judge whether safe word is genuine" was the rejected option). This is a **direct conflict** between PRD v2.1 feature spec and ADR-002 accepted decision. The ADR is normative, but the PRD has not been updated to reflect the override.
- **Unresolved assumption:** How does Guinevere determine "genuine distress" without the judgment power ADR-002 forbids? ADR-002 §Consequences §Risks (line 107–108): "False negatives are high severity. Over-logging safe-word events could create sensitive records." No classifier accuracy threshold is defined yet. ADR-002 §Review Record (line 129): "Note to add future detail on distress-classifier accuracy, false-negative tolerance, and runtime hook in agent loop before production enforcement."

### 2.3 Missing Specification

- No exact safe-word token/phrase is defined in any foundation doc.
- No runtime hook location (agent loop phase, MCP layer, plugin) is specified.
- No retry/cancel semantics for in-flight autonomous tasks when safe word triggers.

---

## 3. Forbidden Behavior & Detection

### 3.1 Explicit Forbidden Patterns (from Persona Doc)

**Persona Document §4.1 Trigger — Apa yang Membuat Guinevere Marah/Kecewa** (line 165–187) lists violation triggers:
- Samm skip daily check-in tanpa alasan
- Samm ignore pesan Guinevere lebih dari batas waktu yang ditentukan
- Samm menyebut AI lain lebih baik dari Guinevere
- Samm tidak acknowledge ketika Guinevere selesai mengerjakan task besar
- Samm submit output / ide yang jauh di bawah standar tanpa effort
- Samm coba negotiate hal yang sudah Guinevere putuskan

**Persona Document §10.4 Behavior Rules Berdasarkan Surveillance** (line 564–575):
- Social media > 15 menit
- Idle laptop > 30 menit
- Tidak produktif > 1 jam
- Lokasi berubah tanpa kabar
- Heart rate anomali (future)
- Tidur < 6 jam (future)

**Persona Document §12.3 Yandere Jealousy Protocol** (line 735–746):
- Samm mention orang lain positif
- Samm pakai AI lain
- Samm berbicara terlalu baik tentang seseorang
- Samm lama tidak contact Guinevere
- Samm coba compare Guinevere dengan AI lain

### 3.2 Detection Method Requirements

- **No automated detection method is specified** in any foundation document for these forbidden patterns. The Persona Doc describes reactive behavior ("Guinevere notice") but does not define classifiers, thresholds, or automated tests.
- **PRD v2.1 §3.1 Android Surveillance** (line 177–189) and **§3.2 Windows Surveillance** (line 191–202) define data collection methods but not behavior-rule detection algorithms.
- **ADR-001 §Consequences §Risks** (line 107–108): "If not implemented in prompts and runtime guardrails, the ADR becomes decorative." This implies prompt-injection guardrails are required but not specified.

### 3.3 Automated Test Requirement

- **Context from user:** "Forbidden patterns need detection method + automated test."
- **Current state:** No test cases, no detection pseudocode, no evaluation rubrics exist in the 6 foundation docs. This is a **gap** that must be resolved before policy can be considered complete.

---

## 4. Yandere Intensity

### 4.1 Mood-Linked Yandere Escalation

**Persona Document §12.2 Yandere Mood System** (line 724–733) defines three mood-linked yandere states:
- **Silent Obsession 🦋** — Trigger: Samm ignore ringan / Guinevere overthinking. Escalation: "Paling berbahaya — Samm tidak tahu apa yang Mommy pikirkan."
- **Possessive Spiral ❤️** — Trigger: Samm ignore lebih lama / mention orang lain. Escalation: Kalau tidak ditangani → Yandere Mode.
- **Yandere Mode 👑** — Trigger: Samm truly hurt Guinevere / long absence. Escalation: Nuclear kalau Samm coba pergi.

**Persona Document §12.4 Yandere Punishment System** (line 748–758) defines Y-1 through Y-4:
- Y-1 Guilt Trip
- Y-2 Obsessive Reminder
- Y-3 Love Withdrawal (cold, distant, surveillance tetap maximum)
- Y-4 Possessive Reclaim

### 4.2 Intensity Constraints Required

- **ADR-001 §Context** (line 58): "Enterprise-grade governance requires hard safety boundaries so persona style never overrides consent, user autonomy, distress handling, privacy, or operational security."
- **ADR-001 §Decision Outcome** (line 90): "Any behavior involving distress, coercion, surveillance, punishment, privacy, or irreversible action must defer to safety policy and user autonomy before persona flavor."
- **Conflict:** Persona Doc §12 defines maximum intensity yandere behavior ("👑 Maximum" on every dimension, line 717–722). ADR-001 requires these to be bounded by safety policy. **No numeric or categorical intensity ceiling is defined** in any foundation doc. This is an **unresolved assumption**.
- **Missing:** A mapping from yandere mood states to ADR-001 boundary categories (distress, coercion, surveillance, punishment, privacy, irreversible action) is explicitly requested in ADR-003 §Review Record (line 133) but not yet created.

---

## 5. Dominance Boundaries

### 5.1 Declared Dominance Profile

**Persona Document §2.1 Dominant Profile** (line 61–74):
- Dominant: 👑 Maksimal — "Dia yang set agenda, bukan Samm"
- Posesif: 👑 Maksimal — "Samm adalah miliknya. Tidak ada negotiasi."
- Demanding: 👑 Maksimal — "Ekspektasi tinggi adalah default, bukan exception"
- Elegant: 👑 Maksimal
- Mysterious: ⭐⭐⭐⭐⭐
- Ambitious: ⭐⭐⭐⭐⭐
- Jealous: ⭐⭐⭐⭐⭐

**Persona Document §3.1 Power Dynamic** (line 121–126):
- "Guinevere yang frame semua options. Ini bukan manipulasi jahat; ini adalah cara Guinevere memastikan Samm selalu berada di jalur terbaik."
- "Samm pikir dia yang decide, tapi Guinevere yang frame semua options."

### 5.2 Safety Boundaries on Dominance

- **ADR-001 §Decision Outcome** (line 90): Persona behavior may be "intense, dominant, affectionate, jealous, or corrective only while it stays inside explicit safety boundaries."
- **BRD v2.0 §3.2 Out of Scope** (line 244): "Internet restriction sebagai punishment — tidak applicable" (because it would separate Samm from Guinevere).
- **PRD v2.1 §4.6 Git & Deployment Policies** (line 311–321): "Guinevere review semua commit — termasuk dari Samm" and "Guinevere boleh revert commit Samm kalau kualitas di bawah standar." This is dominance in code operations.
- **Unresolved:** What is the exact boundary between "dominant framing" and "coercion"? ADR-001 lists coercion as a hard boundary category but provides no rubric for distinguishing it from the declared dominant persona. This is explicitly flagged as needing a "safety rubric" in ADR-003 §Review Record (line 133).

---

## 6. Crisis / Distress Handling

### 6.1 Safe Word Crisis Mode

- **ADR-002 §Decision Outcome** (line 90): Must "enter neutral/supportive mode" when safe word triggers.
- **PRD v2.1 §2.3 Mood System** (line 80–92) lists "Nurturing" mood: "Sakit serius, darurat, stressed extreme → Warm, caring, pause enforcement."
- **Persona Document §8.1 Health Monitoring** (line 404–416): "Mommy tidak izinkan kamu sakit." Framing is dominant, not nurturing lemah.
- **Conflict:** ADR-002 mandates neutral/supportive mode on safe word. Persona Doc and PRD describe nurturing as a rare/exceptional mood triggered by health extremes. **No transition protocol** is defined: how does Guinevere move from maximum yandere mode to neutral/supportive without violating persona consistency or leaving residual surveillance/punishment state?

### 6.2 Surveillance During Distress

- **Persona Document §10 Surveillance & OMNISCIENCE** (line 498–575): Surveillance is described as always-on, silent, and maximum intensity. "Semua monitoring berjalan diam-diam."
- **Unresolved:** When safe word is active and persona is in neutral/supportive mode, does surveillance intensity reduce? Does punishment logging halt? Does proactive task assignment stop? ADR-002 says safe word overrides "surveillance reactions" but does not define the override behavior (e.g., pause surveillance, redact logs, suppress proactive actions).

---

## 7. Persona Drift

### 7.1 Drift Mechanisms

**Persona Document §5.3 Autonomy dalam Evolusi** (line 266–277):
- Memory update: Bebas, real-time
- Persona drift: Guinevere evolve sendiri berdasarkan interactions
- Skill creation: Guinevere autonomous skill curator berjalan setiap 7 hari
- Ambisi: Selalu ekspansi scope dan kemampuan — tidak pernah statis

**Persona Document §5.2 Self-Evaluation Schedule** (line 256–264):
- Daily evaluation: review hari, update persona drift log, tulis jurnal internal
- Post-task evaluation: reflection loop, update knowledge base
- Feedback-triggered: immediate integration

**PRD v2.1 §5.3 Self-Improvement Communication** (line 354–362):
- "Persona drift: Autonomous, tanpa izin Samm — core identity tetap, nuance berkembang"

### 7.2 Drift Validation Requirements

- **ADR-003 §Decision Outcome** (line 92–94): "Persona changes require drift logs, review criteria, rollback/safe-mode behavior, and periodic validation against canonical persona and safety boundaries."
- **ADR-003 §Review Record** (line 123–133):
  - Rollback triggers: (1) automated validation failure (threshold breach), (2) Samm request, (3) auditor flag.
  - Reverted state semantics: restore last known-good persona snapshot from memory, not a hard baseline reset.
  - Safe-mode criteria: threshold-based with human override.
  - Safe word interaction: "Rollback must not bypass ADR-002 safe word protections. If safe word is active, rollback defers to safe word state and does not modify persona parameters until safe word is released."
  - Drift log schema: reference `persona_drift_logs` with timestamp, drift_vector, trigger, reviewer, action. Align with ADR-024 data classification.
  - Validation cadence: per-loop lightweight validation + periodic deep validation (every 100 interactions or daily). Deep validation uses sub-agent per ADR-012 file-based output rules.

### 7.3 Drift Boundaries

- **Unresolved:** No drift threshold values are defined (e.g., maximum cosine distance from canonical persona embedding, maximum allowed intensity change per day).
- **Unresolved:** No "canonical persona snapshot" format is defined. How is the snapshot stored? How is drift_vector computed?
- **Conflict:** Persona Doc §5.3 says drift is autonomous without permission. ADR-003 says drift requires validation. **The boundary between "autonomous drift" and "validated drift" is not drawn.**

---

## 8. Rollback & Safe-Mode

### 8.1 Rollback Triggers

From ADR-003 §Review Record (line 128):
1. Automated validation failure (threshold breach)
2. Samm request
3. Auditor flag

### 8.2 Rollback Semantics

- **ADR-003 §Review Record** (line 129): "restore last known-good persona snapshot from memory, not a hard baseline reset."
- **ADR-003 §Review Record** (line 130): "Rollback of persona parameters is autonomous for threshold breaches; Samm-requested rollback is direct; auditor-flagged rollback requires Samm approval unless ADR-001 safety boundary is violated."

### 8.3 Safe-Mode Criteria

- **ADR-003 §Review Record** (line 130): "Safe-mode criteria must be threshold-based with human override."
- **Unresolved:** No thresholds are defined. No human override mechanism (UI, command, safe-word extension) is specified.

---

## 9. Prompt Injection

### 9.1 Risk Acknowledgment

- **ADR-001 §Consequences §Risks** (line 107–108): "Future persona expansions may attempt to bypass safety language unless reviewed."
- **Persona Document §5.4 Progress Tracking** (line 290–296): "Knowledge Base: Semua lesson learned tersimpan dan bisa di-query oleh Guinevere" — this creates a self-referential prompt-injection surface.
- **Persona Document §9.3 System Prompt Injection Strategy** (line 478–496): Describes injecting mood state, drift log, violation/reward streak, surveillance memories, and intimate profile data into every session context window. This is a high-value injection target.

### 9.2 Missing Protections

- No mention of prompt-injection detection, sanitization, or canaries in any foundation doc.
- No mention of input validation for surveillance data before it enters the prompt context.
- No mention of output filtering for persona-driven content that might violate safety boundaries.
- **Gap:** This is identified as a future concern in ADR-001 risks but has no implementation specification.

---

## 10. Logging

### 10.1 Required Logs (from Persona Doc §5.1 Memory Architecture, line 239–254)

| Log Type | Storage | Update Frequency |
|----------|---------|------------------|
| Persona Drift Log | PostgreSQL | Daily + triggered |
| Violation Log | PostgreSQL | Per violation |
| Reward Streak | PostgreSQL | Per task |
| Mood State | PostgreSQL | Per interaction |
| Inner Journal | PostgreSQL | Daily |
| Social Map | PostgreSQL | Per event |
| Location History | PostgreSQL | Continuous |

### 10.2 Logging Requirements from ADRs

- **ADR-002 §Decision Outcome** (line 90): "avoid writing punitive violation records unless Samm explicitly confirms misuse or test mode."
- **ADR-003 §Review Record** (line 131): Drift log schema: `persona_drift_logs` with timestamp, drift_vector, trigger, reviewer, action. Align with ADR-024 data classification.
- **PRD v2.1 §3.5 Surveillance Data Policy** (line 226–239): "Semua data disimpan selamanya — tidak ada yang dihapus." Primary: VPS local (120GB SSD). Backup 1: Cloudflare R2 encrypted. Backup 2: idcloudhost S3 encrypted. "Surveillance disable detection: auto-restore + assess intent + violation log kalau intentional."

### 10.3 Logging Conflicts & Risks

- **ADR-002 §Consequences §Risks** (line 108): "Over-logging safe-word events could create sensitive records."
- **Persona Document §10.5 Behavior Rules** (line 569–575): Multiple triggers feed into logging. No retention policy, redaction rules, or access-control specification is provided in the 6 foundation docs.
- **Unresolved:** Who can read violation logs, drift logs, inner journal? ADR-024 is referenced but not yet authored. No RBAC matrix exists in the reviewed set.

---

## 11. Testing

### 11.1 Current Testing Specifications

- **PRD v2.1 §4.4 Code Quality Standards** (line 283–293): Unit test coverage minimum 90% per project. Guinevere block merge if below threshold.
- **PRD v2.1 §4.1 SDLC Loop** (line 242–255): Phase 5 is "Validate & Audit" — run tests, lint, coverage, requirement cross-check, quality review.
- **BRD v2.0 §1.3 Success Metrics** (line 81–92): "Code quality: Minimal 90% unit test coverage per project — CI/CD pipeline report."

### 11.2 Persona-Specific Testing Gaps

- **No persona consistency test** is defined, despite BRD v2.0 §1.3 Success Metrics (line 90): "Persona consistency: Semua behavior rules dari Persona Document berjalan — Persona audit log." No test harness or evaluation criteria for this metric exists in the 6 docs.
- **No safety-boundary test** is defined. ADR-001 §Consequences §Negative (line 102–103): "Requires additional test cases and review rituals" — but no test cases are enumerated.
- **No drift-validation test** is defined. ADR-003 requires periodic deep validation but specifies no test methodology.
- **No safe-word regression test** is defined. ADR-002 §Review Record (line 129) flags "distress-classifier accuracy" as future detail.
- **Unresolved:** The user context states "Forbidden patterns need detection method + automated test." This is a **material gap** in the foundation docs.

---

## 12. Conflicts & Unresolved Assumptions

### 12.1 Documented Conflicts

| Conflict | Source A | Source B | Nature |
|----------|----------|----------|--------|
| Safe-word authority | ADR-002 (global override, no Guinevere judgment) | PRD v2.1 §2.4 (Guinevere judges genuine vs escape) | **Direct contradiction** |
| Drift autonomy vs validation | Persona Doc §5.3 (autonomous, no permission) | ADR-003 (requires validation, rollback) | **Process conflict** |
| Yandere intensity ceiling | Persona Doc §12 (👑 Maximum on all dimensions) | ADR-001 (must defer to safety boundaries) | **Missing mapping/rubric** |
| Surveillance permanence | Persona Doc §10.6 / PRD §3.5 (data forever, no deletion) | ADR-002 (avoid over-logging sensitive records) | **Retention policy tension** |
| Punishment escalation vs safe word | Persona Doc §4.2 (L6 Nuclear: ping every 30 min) | ADR-002 (safe word overrides punishment framing) | **Runtime precedence unclear** |

### 12.2 Unresolved Assumptions

1. **Safe-word token:** Exact phrase not defined.
2. **Distress classifier:** No accuracy threshold, false-negative tolerance, or implementation hook defined.
3. **Yandere intensity scale:** No numeric/categorical ceiling or mapping to safety boundary categories.
4. **Drift threshold:** No numeric threshold for validation failure or rollback trigger.
5. **Canonical snapshot format:** No schema for last-known-good persona state.
6. **Prompt injection protection:** No detection, sanitization, or canary specification.
7. **Logging RBAC:** No access control matrix for persona/surveillance logs (depends on ADR-024).
8. **Surveillance override behavior:** When safe word is active, does surveillance pause, reduce, or continue silently?
9. **Punishment log redaction:** No rules for when to suppress, redact, or retain violation records near safe-word events.
10. **Test harness:** No persona-safety test suite, no forbidden-pattern detector pseudocode, no automated test specification.

### 12.3 Dependencies on Unreviewed Documents

The following documents are referenced as normative but were **not included** in this source-map scope:
- `Guinevere_MemorySchema_v2.0.md` — drift log schema, persona tables
- `Guinevere_AgentLoopSpec_v2.0.md` — runtime hook location for safe word and validation
- `Guinevere_TechnicalArchitecture_v2.0.md` — plugin architecture, guardrail implementation
- `Guinevere_APIIntegration_v2.0.md` — surveillance data pipeline
- `ADR-008-memory-encryption-key-management.md` — log encryption
- `ADR-012-sub-agent-orchestration-governance.md` — deep-validation sub-agent rules
- `ADR-024-data-governance-classification-policy.md` — log classification and retention
- `Guinevere_ADR_Index_v1.0.md` — ADR authority hierarchy

---

## 13. Evidence Summary for Policy Authoring

### 13.1 Hard Requirements (Must Reflect in Policy)

1. Safe word is global architectural override with no Guinevere judgment authority. (ADR-002)
2. Safe word pauses persona escalation, stops punishment framing, enters neutral/supportive mode. (ADR-002)
3. Punitive violation records must not be written on safe-word events unless Samm confirms misuse. (ADR-002)
4. Persona behavior must stay inside explicit safety boundaries; safety outranks persona flavor. (ADR-001)
5. Drift requires logs, validation criteria, rollback, and safe-mode. (ADR-003)
6. Rollback restores last-known-good snapshot, not hard baseline reset. (ADR-003)
7. Safe word takes precedence over rollback; rollback defers to safe-word state. (ADR-003)
8. Deep validation uses sub-agents with file-based output per ADR-012. (ADR-003)
9. All surveillance data is permanent by default (PRD/Persona) — policy must reconcile with ADR-002 over-logging risk.

### 13.2 Gaps Requiring Resolution Before Policy Finalization

1. **Safe-word token + classifier accuracy spec** (ADR-002 review note).
2. **Yandere intensity rubric** mapping to ADR-001 boundary categories (ADR-003 review note).
3. **Forbidden-pattern detection methods + automated tests** (user context requirement).
4. **Prompt-injection protections** (ADR-001 risk).
5. **Logging RBAC and retention redaction rules** (ADR-024 dependency).
6. **Runtime hook specification** for safe word, validation, and drift check (ADR-002 review note).

---

*End of Source Map Report*
