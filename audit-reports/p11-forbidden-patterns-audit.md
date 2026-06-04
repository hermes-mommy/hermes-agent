# P11 Forbidden Patterns & Scope Compliance Audit

| Field | Value |
|---|---|
| Audit Date | 2026-06-03 |
| Auditor | Guinevere (automated) |
| Scope | 23 P11 step files (`P11-001.md`–`P11-023.md`) + `requirements-p11-whatsapp.md` + `evidence-p11-expansion.md` |
| Directory | `research-reports/p11-expansion/` + `docs/setup-evidence/p11-expansion/` |
| Verdict | **CONDITIONAL PASS** — 1 real violation, 1 low-severity observation |

---

## 1. Type Suppression Patterns

**Patterns checked:** `as any`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error`

| Result | Matches | Files |
|---|---|---|
| RAW grep | 12 | P11-004 through P11-023 (12 files) |
| After triage | **0 violations** | — |

**Triage:** All 12 matches are verification checklist items in the format `- [ ] No 'as any', '# type: ignore', or type suppression patterns`. These document what implementers must NOT include — they are references to the forbidden pattern rule, not instances of the pattern itself.

**Verdict: PASS** (false positives only)

---

## 2. Empty Error Handling

**Patterns checked:** `except: pass`, `except Exception: pass`, bare `except:` without handling

| Result | Matches | Files |
|---|---|---|
| `except ImportError:` | 1 | P11-003.md:49 |
| `except (ValueError, TypeError):` | 1 | P11-003.md:66 |
| `except Exception:` | 1 | P11-003.md:259 |
| `except Exception:` | 1 | P11-011.md:130 |
| `except: pass` / `except Exception: pass` | **0** | — |

**Triage:**
- P11-003.md:49 — `except ImportError:` with `print('DisconnectedEv: NOT available')` diagnostic fallback. Meaningful handling.
- P11-003.md:66 — `except (ValueError, TypeError):` with `print(f'{m}(...)')` fallback for unresolvable signatures. Meaningful handling.
- P11-003.md:259 — `except Exception:` with `logger.exception("whatsapp_event_handler_error", handler=...)` structured logging. Meaningful handling.
- P11-011.md:130 — `except Exception:` with `await typing.stop_typing(jid)` cleanup + `raise` re-raise. Meaningful handling.

**Verdict: PASS** — all `except` blocks have proper error handling (logging, cleanup, or re-raise)

---

## 3. Stale Library References

**Patterns checked:** `baileys`, `whatsapp-web.js`, `wppconnect`, `venom-bot`

| Result | Matches | Files |
|---|---|---|
| `baileys-antiban` | 2 | P11-014.md:21, P11-014.md:184 |
| `whatsapp-web.js` | 0 | — |
| `wppconnect` | 0 | — |
| `venom-bot` | 0 | — |

**Triage:**
- P11-014.md:21 — Mentions `baileys-antiban` npm library as a comparative reference for jitter patterns. Context: "The `baileys-antiban` npm library (reference implementation for Baileys-based bots) uses similar jitter patterns and validates that this approach effectively avoids velocity-based detection."
- P11-014.md:184 — Explicitly states "Reference only; not a dependency." Compares Gaussian vs uniform jitter approaches.

**Verdict: LOW SEVERITY OBSERVATION** — Both references are comparative documentation, explicitly marked "Reference only; not a dependency." No code dependency on Baileys exists. Consider rewording to remove the library name if strict compliance is required, but functionally this is safe.

---

## 4. Stale Terminology (`post-MVP`)

**Pattern checked:** `post-MVP`, `post-mvp`

| Result | Matches | Files |
|---|---|---|
| `post-MVP` | 5 | P11-008.md:210, P11-009.md:213, P11-012.md:252, P11-013.md:11, P11-013.md:23 |

**Exact occurrences:**

| File | Line | Context |
|---|---|---|
| P11-008.md | 210 | "Streaming integration is a P11 post-MVP optimization." |
| P11-009.md | 213 | "`VOICE_COMMAND` (after voice transcription in post-MVP)" |
| P11-012.md | 252 | "streaming integration is post-MVP." |
| P11-013.md | 11 | "media support deferred to post-MVP" |
| P11-013.md | 23 | "Future post-MVP expansion: voice transcription via Whisper API" |

**Verdict: VIOLATION** — 5 occurrences across 4 files should use "Expansion" or "Stabilization" instead of "post-MVP".

### Required Fixes

| File | Line | Current | Suggested |
|---|---|---|---|
| P11-008.md | 210 | "P11 post-MVP optimizations" | "P11 Expansion-phase optimizations" |
| P11-009.md | 213 | "in post-MVP" | "in Expansion phase" |
| P11-012.md | 252 | "streaming integration is post-MVP" | "streaming integration is Expansion-phase" |
| P11-013.md | 11 | "deferred to post-MVP" | "deferred to Expansion phase" |
| P11-013.md | 23 | "Future post-MVP expansion" | "Future Expansion-phase" |

---

## 5. Node.js Bridge References

**Patterns checked:** `Node.js subprocess`, `HTTP bridge`, `Express server`

| Result | Matches | Files |
|---|---|---|
| `Node.js subprocess` | 2 | P11-001.md:17, P11-001.md:161 |
| `HTTP bridge` | 2 | P11-001.md:161, requirements-p11-whatsapp.md:449 |
| `Express server` | 0 | — |

**Triage:**
- P11-001.md:17 — Documents what ADR-022 currently states and what must be replaced: "This **replaces** the ADR-022 Baileys decision entirely."
- P11-001.md:161 — ADR-022 revision checklist: "(1) replace 'Baileys' with 'Neonize', (2) replace 'Node.js subprocess' with 'Python-native Neonize client', (3) replace 'HTTP bridge' with 'direct Python integration'"
- requirements-p11-whatsapp.md:448-449 — Same ADR-022 revision instructions

**Verdict: PASS** — These document what is being REPLACED (from-state), not actual implementation patterns. They are governance task descriptions for the ADR revision.

---

## 6. Secrets Exposure

**Patterns checked:** `api_key`, `api_secret`, `token`, `password`, `secret`, hardcoded credentials (`sk-*`, `ghp_*`, `Bearer`)

| Result | Matches | Files |
|---|---|---|
| Broad pattern grep | 30 | 11 files |
| Hardcoded credentials | **0** | — |

**Triage of 30 broad matches:**
- `os.getenv('REDIS_PASSWORD', '')` — environment variable read, not secret value (P11-001, P11-008, P11-010, P11-013)
- `token_cost`, `estimate_token_cost`, `CostTracker` — LLM token counting functions, not API tokens (P11-006)
- `GOTIFY_APP_TOKEN` — environment variable name reference, no value (P11-019)
- `.env` file references — configuration file paths, not secret values (P11-002)
- SOPS+age encryption references — security infrastructure documentation (P11-002, requirements)
- `secrets/` directory references — path references, not secret values (P11-002, requirements)

**Verdict: PASS** — zero hardcoded secrets, all references are to environment variable names and configuration patterns

---

## 7. P11-008.md Scope Check

| Check | Result |
|---|---|
| Contains only P11-008 content (message routing pipeline) | **PASS** |
| No embedded P11-009 content | **PASS** |
| No embedded other step content | **PASS** |
| Last line is legitimate note | **PASS** (line 213: shared VPS constraint note) |
| No `<!-- OMO_INTERNAL_INITIATOR -->` marker | **PASS** |
| Total lines | 213 |
| Cross-references other steps by ID (expected) | Yes — P11-004, P11-005, P11-006, P11-007, P11-009, P11-010, P11-011, P11-012, P11-018 (dependency references, not embedded content) |

**Verdict: PASS** — P11-008.md is clean and in-scope

---

## Summary

| Check | Verdict | Severity |
|---|---|---|
| Type suppression | PASS | — |
| Empty error handling | PASS | — |
| Stale library references | LOW SEVERITY | Comparative references only, explicitly marked "not a dependency" |
| Stale terminology (`post-MVP`) | **VIOLATION** | 5 occurrences in 4 files need renaming |
| Node.js bridge references | PASS | From-state documentation for ADR revision |
| Secrets exposure | PASS | Zero hardcoded secrets |
| P11-008.md scope | PASS | Clean, in-scope |

**Overall: CONDITIONAL PASS** — 1 real violation (post-MVP terminology) requiring 5 text replacements across 4 files.

---

## Action Items

1. **MUST FIX:** Replace `post-MVP` with `Expansion phase` or `Expansion-phase` in P11-008.md:210, P11-009.md:213, P11-012.md:252, P11-013.md:11, P11-013.md:23
2. **OPTIONAL:** Consider rewording `baileys-antiban` comparative references in P11-014.md:21,184 to remove the library name if strict no-stale-library compliance is desired

---

## Appendix: Files Scanned

23 step files:
P11-001.md, P11-002.md, P11-003.md, P11-004.md, P11-005.md, P11-006.md, P11-007.md, P11-008.md, P11-009.md, P11-010.md, P11-011.md, P11-012.md, P11-013.md, P11-014.md, P11-015.md, P11-016.md, P11-017.md, P11-018.md, P11-019.md, P11-020.md, P11-021.md, P11-022.md, P11-023.md

2 supplementary files:
requirements-p11-whatsapp.md, evidence-p11-expansion.md

Note: 4 dedicated "tracker" files were not found in the P11 directory structure. The P11 expansion directory contains 23 step files + 1 requirements doc + 1 assembly script (`_assemble_p11.py`). The evidence file is at `docs/setup-evidence/p11-expansion/`.
