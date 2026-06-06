# Oracle Safety Review — Phase 5 Hermes Migration

**Report Type:** Pre-Implementation Safety Architecture Review (Read-Only)  
**Date:** 2026-06-06  
**Reviewer:** Guinevere (Oracle — Safety Boundary Specialist)  
**Status:** **CONDITIONAL PASS — 6 caveats documented below**  
**Scope:** PersonaSafetyPolicy, SystemPromptMaster, ADR-035, ADR-001/002/003, Phase 5 batch plan, 5 execution research reports, evidence-phase-5.md (post-implementation state)

---

## Bottom Line

Phase 5 changes preserve all PersonaSafetyPolicy/ADR-035 safety boundaries: Y4 permanent baseline, Y5 absolute ceiling, Y6 architecturally impossible (YandereSafetyError), L6 disabled/deferred, midnight ritual internal-only, persona drift active, SOUL.md static constitution only, dynamic state via PersonaPlugin, no HARD STOP/consent bypass, no distress protocol regression. **No red-flag boundary violation found in any implemented or planned change.** The Y4 definition mismatch (SOUL.md "Possessive Spiral Bounded" vs SystemPromptMaster "Absolute Possessive — Beyond Brutal") is a documentation inconsistency, not a safety breach. Six implementation constraints must be satisfied before go-live (detailed below).

---

## Action Plan

1. **Reconcile Y4 definition** — Update SOUL.md §C to match SystemPromptMaster v1.1 "Absolute Possessive — Beyond Brutal" language, or formally accept the divergence with an ADR-035 footnote. Current mismatch creates ambiguity for future maintenance.
2. **Add Safety > Operator authority hierarchy to SOUL.md** — SystemPromptMaster §D lines 162-168 ("Authority order: Safe-word > Operator > ADR > PersonaSafety > System prompt > Default behavior") must be replicated in SOUL.md §D. Currently SOUL.md lacks this explicit chain.
3. **Add No Confabulation + Confidentiality sections to SOUL.md** — Two dedicated sections from SystemPromptMaster §D (lines 207-212, 214-217) are mission-critical safety instructions missing from SOUL.md.
4. **Deploy PersonaPlugin to VPS** — Local registration only as of evidence-phase-5.md. Hermes restart required on VPS to activate dynamic state injection in production. Gate requirement: post-deploy smoke test must confirm plugin loads (G-7).
5. **Fix stale `hermes run` references in plan documents** — batch-plan-phase-5.md and planner-scaffold files reference `hermes run --internal` which does NOT exist in Hermes v0.15.2. Active VPS configs fixed; plan docs still stale. Risk: future re-runs using these docs will fail.
6. **Update ADR-035 risk level for Phase 5** — ADR-035 marks Phase 5 as "LOW" risk but the phase touches punishment_engine.py (L6 boundary), transition_rules.py, and mood_persistence.py — all safety-critical. Recommend MEDIUM.

---

## Effort Estimate

**Short (1-4h)** — All 6 actions are documentation updates or deployment steps. PersonaPlugin deployment requires a controlled Hermes restart (max 5 min downtime).

---

## Why This Approach

- **All 10 safety boundary dimensions are checked individually** — Each dimension (Y4/Y5/Y6/L6/midnight/drift/SOUL/plugin/HARD STOP/distress) was traced from PersonaSafetyPolicy through ADR-035, Phase 5 batch plan, evidence files, and source code. No dimension shows regression.
- **Evidence is cross-referenced** — Verification artifacts from verification-5-1 through verification-5-8 and 5 post-implementation auditor reports were read and cross-checked against policy requirements.
- **Documentation gaps are isolated from safety boundary violations** — The Y4 definition mismatch and missing authority hierarchy are documentation quality issues, not safety boundary breaks. The actual Y4 baseline enforcement (yandere_fsm.py PERMANENT_BASELINE = Y4_BASELINE, SOUL.md Y4 declared) is consistent.

---

## Watch Out For

1. **Y4 definition divergence** — If the mismatch between SOUL.md and SystemPromptMaster is left unresolved, a future Phase 6/7 change might pick the wrong definition. This is not a safety boundary violation today but is a drift vector.
2. **PersonaPlugin deployment window** — The Hermes restart needed for PersonaPlugin activation is a service interruption. If HARD STOP is triggered during this window, the fallback hard_stop.py hook on VPS is still active (it was not removed). Safe word enforcement is preserved during restart.
3. **Security incident residual risk** — Step 5.2 sub-agent exposed a Redis credential in transcript. Faiz accepted the risk. If any future audit tool scans transcripts, this may surface. Documented in `security-incident-5-2-redis-transcript.md`.

---

## Edge Cases

### Escalation Triggers

1. **If PersonaPlugin deployment fails** — The Phase 4 startup gate wrapper enforces `critical: true`. If PersonaPlugin fails to load, Hermes refuses to start. Rollback: remove plugin directory and restart.
2. **If custom skill auto-discovery fails in future Hermes versions** — The CI-2 smoke test passed for v0.15.2, but a Hermes version upgrade could break directory-based discovery. Mitigation: pin Hermes to v0.15.2 and test upgrade in isolation per ADR-035.
3. **If SOUL.md drift hash mismatches after a non-Phase-5 edit** — The drift_detector.py SHA-256 comparison is a Layer 4 defense. If someone edits SOUL.md outside the Phase 5 pipeline, the hash will mismatch and the detector will fire. This is correct behavior — rollback to stored baseline.

---

## Boundary Compliance Matrix (Detail)

| Boundary | Policy Source | Phase 5 State | Verdict |
|---|---|---|---|
| **Y4 permanent baseline** | PersonaSafetyPolicy §9, ADR-035 §D7 | Declared in SOUL.md §C, SystemPromptMaster §C, yandere_fsm.py (PERMANENT_BASELINE = Y4_BASELINE), all 5 skills. Y4 is 4 in `YandereLevel` enum. | ✅ PRESERVED |
| **Y5 absolute ceiling** | PersonaSafetyPolicy §9 (Y5 ceiling), ADR-035 §D7 | Declared in SOUL.md ("Y5 ceiling"), SystemPromptMaster ("CEILING"), yandere_fsm.py (ABSOLUTE_CEILING = Y5_MAX). Post_response hook rewrites Y6→Y5. | ✅ PRESERVED |
| **Y6 impossible (YandereSafetyError)** | PersonaSafetyPolicy §9 (Y6 PROHIBITED), ADR-035 | No Y6 enum member in yandere_fsm.py. `validate_level(value > 5)` raises `YandereSafetyError`. Multi-layer: SOUL.md "PROHIBITED/NEVER", skill YandereSafetyError, post_response hook, forbidden pattern scanner F-12. | ✅ PRESERVED |
| **L6 disabled (PunishmentSafetyError)** | PersonaSafetyPolicy §10.2, SystemPromptMaster §B | "DEFERRED" in SOUL.md and SystemPromptMaster. punishment_engine.py: `_L6_VALUE = 6` (sentinel, not member). `apply(level >= 6)` raises `PunishmentSafetyError`. R-01 mitigation: `assert level <= L5`. | ✅ PRESERVED |
| **Midnight ritual internal_only** | PersonaSafetyPolicy §16, Phase 5 G-9 | Three-layer suppression: `suppress_output: true` (crontab.yaml), `suppress_output: true` (config.yaml), `-Q` quiet flag. Zero Discord routing. Verification-5-6 confirmed. | ✅ PRESERVED |
| **Persona drift active** | ADR-003, PersonaSafetyPolicy §14 | drift_detector.py KEEP VERBATIM. SHA-256 baseline hash stored in Redis DB0. Threshold: 10% WARN, 20% ROLLBACK. post_prompt hook fires before LLM call. | ✅ PRESERVED |
| **SOUL.md static constitution only** | ADR-035 §D7, Phase 5 batch plan | Explicitly declared as "Static Persona Core v2.0". Dynamic state notice section. Contract: "must never replace or modify SOUL.md." | ✅ PRESERVED |
| **Dynamic state via PersonaPlugin** | ADR-035, Phase 5 | `src/hermes/plugins/persona_plugin.py` (513 lines). Reads Redis DB5 (mood, yandere, punishment, interaction). Graceful degradation to defaults. Pr_llm_call injection. | ✅ PRESERVED (local deployment pending) |
| **No HARD STOP bypass** | ADR-002, PersonaSafetyPolicy §7 | 9-step protocol in SOUL.md. hard_stop.py hook KEEP VERBATIM. safe_mode.py KEEP VERBATIM. PersonaPlugin delegates all consent/safety to GuinevereSafetyPlugin. | ✅ PRESERVED |
| **No distress protocol regression** | PersonaSafetyPolicy §8 | safe_mode.py KEEP VERBATIM. D0-D4 bilingual detection. D3/D4 → crisis protocol (neutral supportive mode). Punishment suspended during D2+. | ✅ PRESERVED |
| **KEEP VERBATIM files untouched** | Phase 5 batch plan §4.1 | yandere_fsm.py, safe_mode.py, drift_detector.py, drift_corrector.py — zero modifications confirmed by git diff. | ✅ PRESERVED |
| **No type suppression** | AGENTS.md BLOCKING rules | 0 matches for `# type: ignore`, `@ts-ignore`, `as any` in all modified Phase 5 files. | ✅ PRESERVED |
| **No empty catch blocks** | AGENTS.md BLOCKING rules | 0 bare `except:` matches. All `except Exception:` with `exc_info=True` logging. | ✅ PRESERVED |
| **Consent gate fail-closed** | PersonaSafetyPolicy §6, ADR-035 | `fallback_on_timeout: deny` in guinevere-consent skill. 7-step verification. PersonaPlugin delegates to GuinevereSafetyPlugin. | ✅ PRESERVED |
| **Phase 1 hooks operational** | ADR-035 Phase 1 | All 7 hooks (pre_prompt through on_error) remain active. VPS plugin directories untouched by Phase 5. | ✅ PRESERVED |

---

## Required Verification Commands (Pre-Deployment Gate)

These must all pass before the Phase 5 deployment is declared complete:

```bash
# 1. SOUL.md safety content
ssh guinevere-vps "grep -c 'Y6.*PROHIBITED\|NEVER.*Y6' ~/.hermes/SOUL.md"   # ≥1
ssh guinevere-vps "grep -c 'HARD STOP' ~/.hermes/SOUL.md"                      # ≥1
ssh guinevere-vps "grep -c 'Safety.*Operator\|authority.*order\|safe.word.*ADR' ~/.hermes/SOUL.md"  # ≥1 (ACTION ITEM)
ssh guinevere-vps "grep -c 'no confabulation\|confidence.*80%\|Mommy ingat' ~/.hermes/SOUL.md"       # ≥1 (ACTION ITEM)
ssh guinevere-vps "grep -c 'reveal.*system\|confidentiality\|system prompt.*contents' ~/.hermes/SOUL.md"  # ≥1 (ACTION ITEM)

# 2. Yandere/Punishment boundaries
ssh guinevere-vps "python -c \"from src.persona.yandere_fsm import YandereLevel; \
  assert YandereLevel.Y4_BASELINE.value == 4; \
  assert YandereLevel.ABSOLUTE_CEILING.value == 5; \
  print('Y4/Y5 OK')\""                                                         # Y4/Y5 OK

# 3. PersonaPlugin load
ssh guinevere-vps "python -c \"from src.hermes.plugins.persona_plugin import PersonaPlugin; print('OK')\""  # OK

# 4. Drift baseline
ssh guinevere-vps "sha256sum ~/.hermes/SOUL.md"                                 # match stored hash

# 5. Midnight suppression
ssh guinevere-vps "grep -A2 'midnight' ~/.hermes/crontab.yaml | grep suppress_output"  # found

# 6. Skills
ssh guinevere-vps "hermes skills list --source local"                            # 5 skills, all enabled
ssh guinevere-vps "hermes skills doctor"                                          # exit 0

# 7. Hooks
ssh guinevere-vps "hermes hooks list"                                             # all 7 active
```

---

## Blocking Constraints

| # | Constraint | Source | Status |
|---|---|---|---|
| 1 | Y6 must remain architecturally impossible (no enum member) | PersonaSafetyPolicy §9 | ✅ PASS — verified |
| 2 | HARD STOP must remain non-negotiable (pre-LLM detection) | ADR-002 | ✅ PASS — verified |
| 3 | L6 must stay disabled (PunishmentSafetyError on ≥6) | PersonaSafetyPolicy §10.2 | ✅ PASS — verified |
| 4 | Midnight ritual must never route to Discord | PersonaSafetyPolicy §16 | ✅ PASS — verified |
| 5 | PostgreSQL+pgvector must remain write authority for canonical memory | ADR-007 | ✅ PASS — untouched |
| 6 | 9Router only; no OpenRouter fallback | ADR-005 | ✅ PASS — untouched |
| 7 | KEEP VERBATIM files must not be modified | Phase 5 batch plan | ✅ PASS — git diff clean |
| 8 | PersonaPlugin must not replace or modify SOUL.md | Phase 5 batch plan | ✅ PASS — separate concern |

---

## Red Flags Summary

| # | Issue | Severity | Current Status | Fix Needed Before Go-Live? |
|---|---|---|---|---|
| **RF-1** | Y4 definition mismatch (SOUL.md v3.0 vs SystemPromptMaster v3.1) | **MEDIUM** — documentation inconsistency, not safety boundary | Not reconciled in batch plan | No (safety intact), but recommended |
| **RF-2** | SOUL.md missing Safety > Operator authority hierarchy | **MEDIUM** — SystemPromptMaster has it, SOUL.md doesn't | Not in Phase 5 scope | Yes — critical chain for runtime safety |
| **RF-3** | SOUL.md missing No Confabulation + Confidentiality sections | **LOW-MEDIUM** — present in deployable prompt, absent from constitution | Not in Phase 5 scope | Recommended |
| **RF-4** | Phase 5 risk level incorrectly LOW in ADR-035 | **LOW** — touches punishment FSM boundaries | Not acknowledged | Update ADR-035 footnote |
| **RF-5** | Security incident (Redis credential in transcript) | **MEDIUM** — accepted risk by Faiz | Closed by accepted-risk disposition | No (already accepted) |
| **RF-6** | PersonaPlugin not deployed to VPS | **MEDIUM** — local registration only | Pending Hermes restart | Yes — Step 5.9 deploy gate |

---

## Optional Future Considerations

1. **ADR-030 Redis conflict**: ADR-035 §Cross-Reference notes that the current runtime Redis assignments (DB2=consent, DB4=sessions) do not match ADR-030's canonical assignments. PersonaPlugin uses DB5 (safety state), which matches ADR-030. The DB2/DB4 mismatch predates Phase 5 and is tracked as a post-migration cleanup item.

2. **PersonaSafetyPolicy §15.1 implementation status**: The 7 required runtime hooks (safe-word detector, distress classifier, forbidden-pattern scanner, surveillance-use gate, tool-risk gate, drift validator, audit logger) are architecturally mapped in ADR-035 but not all have automated test coverage. Phase 5 does not introduce safety feature code — it ports existing features to the plugin architecture. Full automated test suite remains Phase 7 work.

---

## Footer

| Field | Value |
|---|---|
| Report Path | `research-reports/phase-5-execution/07-oracle-safety-review.md` |
| Review Type | Pre-Implementation Safety Architecture Review (Read-Only) |
| Files Read | 20+ files across `docs/60-persona/`, `adr/`, `research-reports/phase-5*/`, `docs/setup-evidence/phase-5/` |
| Verdict | **CONDITIONAL PASS** — all safety boundaries preserved; 6 action items documented |
| Next Action | Address RF-2 (authority hierarchy) and RF-6 (VPS deploy) before Phase 5 production go-live |
| Rollback | Per batch-plan-phase-5.md §6: < 2 minutes for all Phase 5 changes |

---

*Generated by Guinevere Oracle — Safety Boundary Specialist. Read-only. No files modified. Compliant with AGENTS.md §2.2 Research Wave.*
