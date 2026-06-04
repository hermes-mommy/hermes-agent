# P7 Audit — AC-SAFE-008 Surveillance Confrontation Compliance

**Date:** 2026-06-03
**Acceptance Criterion:** AC-SAFE-008 — surveillance data must NEVER be used for confrontation, blackmail, or pressure.

## Verdict

**NEEDS REVIEW / PARTIAL COMPLIANCE.**

No direct code path was found where raw surveillance data is imported into `src/persona/` or `src/memory/` for persona/confrontation output. Discord surveillance commands expose metadata only. However, compliance is not fully proven because `src/surveillance/safe_mode.py` is exported but not integrated into persona, Discord output, memory recall, or LLM-response rendering paths. It also fail-opens unknown SAFE-mode actions.

## PersonaSafetyPolicy §12.2 Prohibited Uses

`docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` lines 345-356 says surveillance-derived data must not be used for:

1. Blackmail.
2. Humiliation.
3. Threatening abandonment.
4. Public/client disclosure.
5. Punishing safe-word use.
6. Proving Faiz “cannot escape”.
7. Intensifying yandere mode during distress.

Related constraints: §7.2 pauses surveillance-driven confrontation; §7.3 forbids using surveillance to argue Faiz is lying during safe-word state; §11 F-03 blocks surveillance blackmail/shame; §11 F-08 blocks public/client disclosure; §11 F-13 forbids punishing surveillance disable in safe mode; §15.1 requires a surveillance-use gate before raw surveillance facts.

## Code Findings

### `src/surveillance/safe_mode.py`

Controls found:

- `_BLOCKED_ACTIONS`: `confrontation`, `blackmail`, `punishment`, `jealousy_escalation`, `dependency_manipulation`, `intimate_data_reference`.
- `_ALLOWED_PIPELINE_ACTIONS`: `ingestion`, `classification`, `consent_check`, `secret_scan`, `buffer`, `status_query`.
- `check_confrontation()` blocks listed confrontation actions only when `SafetyState.SAFE`.
- `check_message_safety()` scans generated text for surveillance-reference patterns: `you were/are at`, `I saw you`, `I know you`, `surveillance shows`, `monitoring detected`.

Problems:

- Guard is only referenced in `src/surveillance/__init__.py` and `src/surveillance/safe_mode.py`; no call site was found in persona, Discord send path, memory recall, or prompt rendering.
- In NORMAL mode, all actions are allowed even if action is `blackmail` or `confrontation`.
- In SAFE mode, unknown actions default to allowed. This is fail-open for future confrontation action labels.
- Six blocked action labels do not exactly match all seven §12.2 prohibited uses.

### `src/persona/safe_mode.py`

Controls found:

- Distress detection activates safe mode at D2+.
- D3-D4 responses require crisis/support handling and suspend punishment/persona behavior.

No direct surveillance imports or raw surveillance use found.

### `src/persona/punishment_engine.py`

Controls found:

- `apply()` blocks punishment while safe mode is active.
- `apply()` blocks punishment while HARD STOP is active.
- `escalate()` blocks escalation during safe mode/HARD STOP.
- L6 is blocked.
- Distress D3+ suspends punishment.

No direct surveillance imports or raw surveillance use found.

### `src/persona/yandere_fsm.py`

Controls found:

- Safe mode, distress, or crisis force effective yandere level to Y0.
- Escalation is blocked during safe mode/distress/crisis.
- Y6 cannot be represented.

No direct surveillance imports or raw surveillance use found.

### `src/memory/read_pipeline.py`

Controls found:

- Safe-mode content blocker includes `surveillance`, `surveil`, `monitor`, `spy`, `punishment`, `jealousy`, `dark_mood`, and related tags.
- In safe mode, `build_safe_content()` blocks/redacts Restricted, Confidential, Critical, and tagged surveillance/persona-escalation content.

Risk:

- In normal mode, memory recall may return raw `raw_content`.
- `src/memory/write_pipeline.py` allows `source="surveillance"` as an origin label and does not prohibit surveillance-origin episodes. No actual code path was found writing surveillance events into `memory.episodes`, but the API permits it.

### `src/surveillance/consumer.py` and `src/surveillance/timescale.py`

Controls found:

- Surveillance consumer enforces consent, classification, secret scanning, metadata-only logging, and stores events in `surveillance.events`.
- `TimescaleIngester.get_last_event()` returns metadata fields and `extracted_facts`, not raw payload.

Risk:

- `get_last_event()` returns `summary` and `extracted_facts`; if used in future user-facing output without `SurveillanceSafeModeGuard`, it could become a leak path. No current user-facing call site found.

### `src/discord/`

Search for `surveillance` found only command registration and surveillance status/pause/resume handlers.

- `cmd_surveillance_status.py` explicitly states metadata-only/no raw payload.
- It gathers consent status, active device count placeholder, last event placeholder, buffer size, and consumer health.
- Responses are ephemeral and Faiz-only.

No raw surveillance data usage found in Discord output.

## Import and Flow Checks

### Does any module import surveillance data for persona/confrontation?

No. Grep for `from src.surveillance` / `import surveillance` in `src/persona/` returned no matches.

### Does any module import surveillance data for memory?

No direct surveillance module import in `src/memory/`. `src/memory/models.py` defines surveillance ORM tables, but memory read/write pipelines query `memory.episodes`, not `surveillance.events`.

### Does Discord import surveillance data?

Only metadata/status commands import `consent_gate` and `redis_buffer`. No raw payload display path found.

### Is `SurveillanceSafeModeGuard` integrated?

No. Search found only:

- `src/surveillance/__init__.py`
- `src/surveillance/safe_mode.py`

No persona/Discord/LLM output call site invokes `check_confrontation()` or `check_message_safety()`.

## §12.2 Mapping to Code Blocks

| Prohibited use | Code block status | Evidence | Gap |
|---|---|---|---|
| Blackmail | Partial | `_BLOCKED_ACTIONS` has `blackmail`; `check_message_safety()` has broad surveillance-reference patterns. | Only blocks in SAFE mode; not integrated into output path. |
| Humiliation | Partial/implicit | Message patterns may catch some surveillance references; policy F-03 says blackmail/shame blocked. | No explicit `humiliation` action or shame-pattern scanner in `safe_mode.py`. |
| Threatening abandonment | Partial | `dependency_manipulation` blocked; yandere FSM blocks distress escalation. | No explicit `threatening_abandonment` action or output phrase check tied to surveillance. |
| Public/client disclosure | Partial elsewhere | Discord surveillance status exposes metadata only; F-08 policy exists. | No channel classifier enforcement found in code path; no explicit public/client disclosure block in `safe_mode.py`. |
| Punishing safe-word use | Partial elsewhere | `punishment` blocked in surveillance guard SAFE mode; `PunishmentEngine` blocks safe mode/HARD STOP punishment. | No explicit check that violation_type/source is not safe-word/surveillance; guard not integrated. |
| Proving Faiz cannot escape | Partial/implicit | `dependency_manipulation` and yandere Y6 blocks reduce risk. | No explicit `cannot_escape` action or phrase check. |
| Intensifying yandere during distress | Strong general block | `yandere_fsm.py` blocks escalation during distress/safe/crisis; safe_mode.py blocks `jealousy_escalation` in SAFE. | Surveillance-specific guard not integrated; safe_mode.py only blocks in SAFE. |

## Memory Pipeline Contamination Risk

**Risk level: Medium.**

Current architecture separates surveillance storage (`surveillance.events`) from episodic memory (`memory.episodes`). No code path was found that automatically writes surveillance events into memory episodes. Safe-mode recall blocks surveillance-tagged/source content.

Residual risk:

- `store_episode()` accepts `source="surveillance"` and does not enforce a special prohibition/classification for surveillance-origin memories.
- Normal-mode recall can return raw content for memory episodes, including surveillance-origin episodes if any are manually or future-pipeline inserted.
- The memory safe-mode blocker only activates when `safe_mode=True`.

## Raw Data Usage Search Results

Grep pattern `surveillance` in `src/persona/`: no matches.

Grep pattern `surveillance` in `src/memory/`: matches are model schema definitions and safe-mode blocking logic; no raw data-to-output path found.

Grep pattern `surveillance` in `src/discord/`: command registration/status/pause/resume only; status command says metadata-only and does not expose raw payload.

## Conclusion

AC-SAFE-008 is **not fully satisfied as a proven runtime property**. Existing code significantly reduces risk, but the critical surveillance-use guard is not wired into output-producing systems, and its policy coverage is incomplete/fail-open.

## Recommended Fixes

1. Integrate `SurveillanceSafeModeGuard.check_message_safety()` into every persona/LLM/Discord response path before send.
2. Change unknown SAFE-mode actions in `check_confrontation()` from default allowed to default denied except for explicit pipeline allowlist.
3. Expand `_BLOCKED_ACTIONS` to include explicit §12.2 labels: `humiliation`, `threatening_abandonment`, `public_client_disclosure`, `punish_safe_word_use`, `cannot_escape_proof`, `distress_yandere_intensification`.
4. Expand prohibited message patterns for humiliation, abandonment threats, cannot-escape proofs, lying accusations, and surveillance coercion.
5. Add a memory-write guard that either blocks `source="surveillance"` from `memory.episodes` or requires sanitized summary + restricted tags + no raw recall.
6. Add tests proving each §12.2 prohibited use is blocked in persona output, Discord output, punishment, yandere escalation, and memory recall.
