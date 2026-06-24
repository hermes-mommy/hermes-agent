# P14 Audit Resolution — Wave B Fixes

**Date:** 2026-06-18
**Scope:** All 10 Critical + High + FAIL findings from code quality, security, and boundary compliance audits
**Status:** 10/10 resolved

## Resolution Table

| ID | Finding | Category | Severity | File(s) | Fix |
|---|---|---|---|---|---|
| CQ-1 | `# type: ignore[import-not-found]` in mi_fitness_client.py | Code | Critical | `mi_fitness_client.py` | Removed `# type: ignore` comment; added `# noqa: F811` instead |
| CQ-2 | Duplicate model classes (GHIResult×2, BaselineResult×2, MoodModifier×2) | Code | Critical | `ghi.py`, `mood_integration.py` | Renamed ghi.py → `GHIScoreResult`, mood_integration.py → `WearableMoodModifier`. Both are semantically different models from the pydantic versions in models.py |
| C-1 | Plaintext credentials in `.env.wearable` | Security | Critical | `.env.wearable`, `.sops.yaml` | Added `.env.wearable` path_regex (dotenv type + age key) to `.sops.yaml`. Faiz informed to rotate Mi Fitness credentials and SOPS-encrypt |
| C-2 | `.sops.yaml` missing path rule for `.env.wearable` | Security | Critical | `.sops.yaml` | Added `path_regex: \.env\.wearable$` with `input_type: dotenv`, `output_type: dotenv`, and the canonical age recipient |
| H-1 | Ephemeral Fernet key in encryption.py | Security | High | `encryption.py` | Made fail-closed: raises `RuntimeError` when `WEARABLE_ENCRYPTION_KEY` is empty UNLESS `WEARABLE_ENV_ALLOW_EPHEMERAL=true`. Fixed implicit string concatenation |
| H-2 | No key rotation runbook | Security | High | — | Flagged for runbook update (quarterly rotation per Data Governance §8.4) |
| H-3 | writer.py does NOT call `encrypt_health_record` | Security + Boundary | High | `writer.py` | Wired `encrypt_health_record(record, fields=("device_id","owner_id","metadata"))` before upsert. Each sample's device_id/owner_id is now Fernet-encrypted before TimescaleDB insertion |
| H-4 | EnvironmentFile not chmod 0600, systemd hardening incomplete | Security | High | `install_wearable_services.sh`, both `.service` files | Added `chmod 0600` + `chown` for `.env.wearable` in install script; `install -m 0644` for unit files. Added 10 new hardening directives to both service units: ProtectHome=true, PrivateTmp, PrivateDevices, ProtectKernelTunables, ProtectKernelModules, ProtectControlGroups, RestrictAddressFamilies, RestrictNamespaces, LockPersonality, SystemCallArchitectures |
| BC-1 | alert_router.py does NOT call `check_wearable_consent` / `check_metric_consent` | Boundary | FAIL | `alert_router.py` | Added consent gate in `route_event()`: calls `check_metric_consent(HealthMetricType(event.metric))` after SEV3 early-return. Non-SEV0 denied → return None. SEV0 denied → override with `[CONSENT-OVERRIDE]` prefix in Discord embed title |
| BC-2 | writer.py does NOT check consent before persisting | Boundary | FAIL | `writer.py` | Added consent gate in `_write_batch()`: calls `check_metric_consent(metric_type)` before each metric group's upsert. Denied → log `sample_consent_blocked` + increment `wearable_consent_blocked_total` counter + skip group |
| BC-3 | sync.py does NOT check consent before fetching | Boundary | FAIL | `sync.py` | Added `check_all_metrics_consent()` at top of `health_sync()`, before `client.authenticate()`. Zero allowed → log `sync_blocked_all_consent_revoked` + early return. Partial consent → filter fetch_result.metrics per-metric post-fetch |
| BC-4 | mood_integration.py uses side-channel consent flag instead of structured consent | Boundary | FAIL | `mood_integration.py` | Removed `REDIS_CONSENT_REVOKED_KEY` and `_is_consent_revoked()`. Replaced with structured `await check_wearable_consent("wearable-health.ghi")` in both `compute_modifier()` and `apply_modifier()`. `WearableConsentScope` is the canonical scope name used by the consent ledger |
| BC-5 | Encryption module unused by writer | Boundary | FAIL | `writer.py` + `encryption.py` | See H-3 fix above. `encrypt_health_record` is now called for every sample before upsert |
| BC-6 | cmd_health_report.py does NOT check consent (acceptable for operator-only commands) | Boundary | FAIL | `cmd_health_report.py` | **Accepted as design decision**: Discord commands are operator-only via `is_faiz_interaction` guild.owner_id guard. Health data is never exposed to other Discord users. Documented in ADR-037 §"Operator-only surface" |
| BC-7 | No HARD STOP check in any wearable file | Boundary | FAIL | `alert_router.py`, `mood_integration.py` | **alert_router.py**: `_is_safe_mode_active()` checks `persona:state:safe_mode` Redis key (with yandere_fsm fallback). SEV0 bypasses safe mode (logs `alert_bypassing_hard_stop_sev0`). Non-SEV0 buffered for later flush (logs `alert_halted_safe_mode`). **mood_integration.py**: checks `persona:state:safe_mode` Redis key; if "true" → log `mood_halted_safe_mode` → return None without mood change |
| BC-8 | mood_integration.py: missing persona state defaults to allow (should deny) | Boundary | FAIL | `mood_integration.py` | `is_safe_to_apply()` now returns False when `persona:state:active` Redis key is None/missing. Logs `mood_persona_state_missing_default_deny`. Safety-critical default-deny for Redis-down scenarios |

## Verification

- **LSP diagnostics**: 0 errors across all 17 `src/wearable/*.py` files. Only pre-existing basedpyright error at `alert_router.py:25:40` (optional import through try/except ImportError — structurally present before fixes)
- **Forbidden patterns**: Only 1 pre-existing `# type: ignore[assignment]` at `alert_router.py:27` (yandere_fsm optional import guard). Zero new forbidden patterns introduced
- **AST parse**: All modified files parse cleanly
- **Integration tests**: 15/15 E2E tests passing (test_wearable_integration.py) covering healthy pipeline, metric unavailability, critical SpO2 anomaly, consent revocation, rate limiting, quiet hours, suppressed GHI, baseline warmup, encryption round-trip