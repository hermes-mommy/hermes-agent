# P14 Security Audit — Wearable Health Pipeline

> **Auditor:** Independent security auditor (sub-agent)
> **Date:** 2026-06-18
> **Scope:** P14 (Wearable Health Pipeline) implementation files, systemd units, install scripts, env templates, and supporting docs (ADR-037, Data Governance, PersonaSafetyPolicy).
> **Authority:** AGENTS.md §1 BLOCKING rules; ADR-015 (Secrets Management); ADR-024 (Data Governance & Classification); ADR-037 (Wearable Health Pipeline); `60-PersonaSafetyPolicy_v1.0.md`.

## Summary

| Item | Value |
|---|---|
| Files audited | 12 (8 source files, 2 systemd units, 1 install script, 1 env template) + 1 live `.env.wearable` |
| Critical findings | 2 |
| High findings | 4 |
| Medium findings | 7 |
| Low findings | 4 |
| **Overall verdict** | **NEEDS FIX — block deploy until Critical/High items closed** |

A live plaintext `.env.wearable` was observed on disk containing real-looking Mi Fitness credentials. Although it is gitignored, this directly contradicts the SOPS-encrypted-at-rest requirement stated in `ADR-015`, `ADR-037`, and the `.env.wearable.example` header. Two more Critical/High items are structural gaps (SOPS path rule missing; field-level encryption declared but never applied by the writer).

---

## Findings by Severity

### Critical

#### C-1 — Plaintext credentials in `.env.wearable` (CRITICAL — SEV0 data incident)

- **Evidence:** `C:\Users\faizz\guinevere\.env.wearable` lines 3-5 contain real-looking plaintext credentials (`MI_FITNESS_USER_ID=<email>`, `MI_FITNESS_PASS_TOKEN=<password>`). The file is 1,361 bytes, mode `-a----` (default 0644, world-readable on the deploy host).
- **Policy violated:** ADR-015 (Secrets Management: SOPS + age for all secrets at rest); `30-DataGovernance_Classification_v1.0.md` §4.2/§8.3/§8.5 (Critical classification, app-level encryption, secret leakage = data incident); `.env.wearable.example` header line 1 ("SOPS-encrypted in production"); AGENTS.md BLOCKING rule "NEVER commit secrets" (extended spirit: never store plaintext secrets at rest on a public system).
- **Risk:** Anyone with VPS shell access, backup access, or filesystem read can read the Mi Fitness credentials. Combined with C-2 below, the file is not SOPS-encrypted despite policy.
- **Required action:**
  1. Treat as a data incident per Data Governance §11.4 (SEV0: contain, revoke, rotate, postmortem).
  2. Rotate `MI_FITNESS_PASS_TOKEN` against the Mi Fitness account immediately.
  3. SOPS-encrypt the file in place with `sops --encrypt --in-place .env.wearable` and re-evaluate after C-2 is fixed.
  4. Restrict file mode to `chmod 0600` and ownership `guinevere:guinevere`.

#### C-2 — `.sops.yaml` has no path rule for `.env.wearable` (CRITICAL — root cause of C-1)

- **Evidence:** `C:\Users\faizz\guinevere\.sops.yaml` only declares `path_regex: secrets/.*\.env$`, `secrets/.*\.yaml$`, `secrets/.*\.json$`, and `secrets/backup/.*\.env$`. The project-root `.env.wearable` is not covered.
- **Risk:** `sops --encrypt .env.wearable` will not apply the canonical age recipient and therefore will not produce a SOPS-encrypted envelope. Operators following the documented procedure silently produce a plaintext file. Even with C-1 rotated, the structural defect remains and will recur.
- **Required action:** Add to `.sops.yaml`:
  ```yaml
    - path_regex: \.env\.wearable$
      input_type: dotenv
      output_type: dotenv
      age: age12c4w4cgm228yrwjueay0vdsxwdmta69mk8wlyqt7mukrqp86r5xs5u6r0w
  ```
  Then re-encrypt the file under the new rule and verify the file starts with `ENC[AES256_GCM,...]`.

### High

#### H-1 — `WEARABLE_ENCRYPTION_KEY` ephemeral fallback (HIGH)

- **Evidence:** `src\wearable\encryption.py:106-115`. When `WEARABLE_ENCRYPTION_KEY` is empty, the module calls `Fernet.generate_key()` and proceeds with that. The comment correctly flags this as "NOT production-safe" and the warning reaches Sentry, but the service still happily encrypts new data with a key that will not survive process restart.
- **Risk:** Silent data loss. Records encrypted in run N become unreadable in run N+1 because the key is re-randomized. Combined with C-1, this is the most likely first on-call page after deploy.
- **Required action:** Make this fail-closed in production: when `WEARABLE_ENCRYPTION_KEY` is empty AND `WEARABLE_ENV_ALLOW_EPHEMERAL != "true"`, raise `RuntimeError` instead of generating. Keep the ephemeral path only behind an explicit test-only opt-in.

#### H-2 — No key rotation policy or procedure for `WEARABLE_ENCRYPTION_KEY` or `MI_FITNESS_PASS_TOKEN` (HIGH)

- **Evidence:** No runbook, ADR, or doc covers rotation cadence for the wearable encryption key. Data Governance §8.4 requires quarterly rotation for high-risk secrets / API tokens; the secrets rotation runbook (`docs\20-security\23-SecretsRotationRunbook_v1.0.md`) does not enumerate either value.
- **Risk:** No documented path to rotate without downtime or unrecoverable data. Re-keying a Fernet key by definition invalidates all existing ciphertexts unless a versioned key-wrap scheme is used (KMS-style `key_id || ciphertext`).
- **Required action:** Document and implement versioned key rotation: store `key_id` alongside ciphertext (or as part of the `ENC:` prefix), keep a small active keyset, and add a one-shot re-encrypt migration. Add a Secrets Rotation section to the runbook for these two values.

#### H-3 — `src\wearable\writer.py` does not call `encrypt_health_record` (HIGH)

- **Evidence:** `writer.py:1-130` writes `NormalizedHealthSample` rows to `health.*` hypertables using `asyncpg` directly. `device_id` and `owner_id` are inserted as plaintext UUIDs. There is no import of `encrypt_health_record` and no call to it. Meanwhile `encryption.py:31` declares `SENSITIVE_FIELDS = ("notes", "raw_json", "device_id")` and the file docstring states the writer "encrypts sensitive fields (notes, raw_json, device_id) before TimescaleDB insertion".
- **Risk:** Contract mismatch. The encryption module advertises a guarantee the writer does not deliver. Health data is classified **Critical** per `30-DataGovernance_Classification_v1.0.md` §5, which mandates application/field-level encryption. Plaintext `device_id` and `owner_id` in the DB would survive a TimescaleDB dump and any unencrypted backup.
- **Required action:** Wire `encrypt_health_record` into the writer path; consider double-encryption (per Data Governance §8.2 — Critical = double encryption) for at minimum `device_id` and `owner_id`. Update the encryption module's docstring to match the actual policy.

#### H-4 — `EnvironmentFile` permissions not hardened in install script (HIGH)

- **Evidence:** `scripts\install_wearable_services.sh:1-43` does not chmod 0600 the live `.env.wearable` after deploy, and does not set `SystemCallArchitectures`, `RestrictAddressFamilies`, or `LockPersonality` on the units. The file mode observed on the working copy is the default 0644 (world-readable).
- **Risk:** Plaintext secret file world-readable on the VPS; systemd does not protect EnvironmentFile content beyond the on-disk mode.
- **Required action:** Add `chmod 0600` (and ideally `chown guinevere:guinevere`) in the install script right after `sops --decrypt .env.wearable`. Add `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` and tighten `ProtectHome=true` (not just `read-only`) on both units.

### Medium

#### M-1 — Auth guard depends on `guild.owner_id` (MEDIUM)

- **Evidence:** `src\discord\_auth_guard.py:11-22`. `is_faiz_interaction` returns True only when `interaction.guild.owner_id == interaction.user.id`. All three `/health-*` callbacks (`cmd_health_report.py:190, 308, 404`) defer to this guard.
- **Risk:** If Faiz is ever not the guild owner (e.g., a test guild, role delegation, or temporary admin transfer), all health commands silently deny. There is no operator override and no audit log for the denial path. Also, the comparison runs in main process memory; if a non-owner spams the command the failures are not rate-limited beyond Discord's own.
- **Required action:** Add an explicit env-controlled `WEARABLE_HEALTH_ALLOWED_USER_IDS` allowlist that is checked first, with `is_faiz_interaction` as a fallback. Log denials with the user ID and a counter.

#### M-2 — `mi_fitness_client._retry_with_backoff` is fire-and-forget before raising (MEDIUM)

- **Evidence:** `src\wearable\mi_fitness_client.py:228-235` calls `_retry_with_backoff` (1s + 2s + 4s sleep loop) and then **immediately** raises `RateLimitError` without resetting the circuit breaker. Every subsequent `fetch_metrics` call within the recovery window will hit the open circuit.
- **Risk:** After one rate-limit event, the circuit opens for 30 minutes by default even though the upstream is recoverable. A single burst of 429s can suppress a full day of data.
- **Required action:** On rate-limit, treat it as a soft signal — do not increment `_circuit.consecutive_failures`. Either separate the rate-limit counter from the failure counter, or set a much higher threshold and a shorter recovery window for rate-limit specifically.

#### M-3 — Alert embed may leak sensitive values (MEDIUM)

- **Evidence:** `src\wearable\alert_router.py:184-221` embeds `event.description` and a batch summary `• {event.time} | {event.metric} | {event.severity.value} | value={event.value}` (line 211). Per the alert model contract, `description` is operator-written and can contain free text.
- **Risk:** Raw health values (HR, SpO2, sleep minutes) and any free-text description are pushed to Discord. Even though the channel is private DM, this is a Restricted/Critical payload over a third-party SaaS and may be visible to Discord trust & safety. ADR-037 §"Persona Safety Gates" says "All health-discord output is ephemeral" — `_send_discord_dm` does not set `ephemeral` (it is currently a logging stub, but the embed structure does not enforce ephemeral).
- **Required action:** When the wire-up is completed, ensure the actual Discord POST uses `flags=64` (ephemeral) for SEV1-3. Drop or hash `event.value` for SEV2/SEV3; keep value for SEV0. Add a redact pass for `event.description`.

#### M-4 — Redis token cache stores bearer token for 24h in plaintext (MEDIUM)

- **Evidence:** `src\wearable\mi_fitness_client.py:340-348` calls `redis_client.setex("wearable:mi_fitness:token", 3600 * 24, token)` — 24h TTL, plaintext value. The Redis instance used (`db 2` for wearable) is shared per `30-DataGovernance_Classification_v1.0.md` §5 and is classified Restricted.
- **Risk:** Anyone with Redis read access on db 2 can read the bearer token. A 24h TTL means a stolen token is good for a full day.
- **Required action:** Encrypt the token before storing (Fernet-encrypt using a separate `WEARABLE_TOKEN_CACHE_KEY` or the same Fernet key), and shorten the TTL to the documented Mi Fitness token lifetime. Add a Sentry/audit log on cache reads so a scrape is detectable.

#### M-5 — `_normalize_raw_sample` keeps all API keys as plaintext metadata (MEDIUM)

- **Evidence:** `src\wearable\mi_fitness_client.py:296-298`. `metadata={k: str(v) for k, v in raw.items() if k not in {...}}` — every non-`timestamp/value/...` field from the upstream payload is persisted as plaintext into the `metadata` JSONB.
- **Risk:** Upstream API fields can include device serial, MAC, or PII that the Guinevere model has not enumerated. Per Data Governance §4.2 "Highest classification wins", the whole record escalates.
- **Required action:** Maintain an allowlist of expected metadata keys; drop or hash the rest. Add a periodic scan that flags metadata records with non-allowlisted keys.

#### M-6 — `wearable_alert_rate_limit` is asymmetric across severities (MEDIUM)

- **Evidence:** `src\wearable\alert_router.py:74-79`. SEV0/1/2 share `max_alerts=5` per 1h. SEV3 uses `max_alerts=5` per 24h. SEV0 is supposed to bypass quiet hours but is also rate-limited to 5/hour.
- **Risk:** A genuine SEV0 storm (e.g., sustained tachy event) will be silently suppressed after 5 alerts. That is the wrong failure mode for a health-safety severity.
- **Required action:** For SEV0, raise the cap significantly (e.g., 30/h) and add a `breach` audit log when a SEV0 is rate-limited. Add a panic-burst escape hatch that escalates to a non-rate-limited channel after N consecutive SEV0 rate-limits.

#### M-7 — Mood integration suppression on distress is read-time only (MEDIUM)

- **Evidence:** `src\wearable\mood_integration.py:88-95`. `is_safe_to_apply` reads `persona:state:active` and refuses to apply if state ∈ {`argument`, `distress`}. This is correct, but there is no symlink to the consent gate (H-3 writer does not require consent either) and no symlink to the yandere FSM — which is good, but means the suppression is best-effort.
- **Risk:** If the Redis key is missing or stale, the safety check silently allows the modifier. ADR-037 §"Persona Safety Gates" says health data is "invisible during argument/distress state" — a missing Redis key should default to **deny**, not allow.
- **Required action:** Treat `state is None` (key missing / Redis down) as deny. Add an alert when the safety check fails-closed so the operator can investigate.

### Low

#### L-1 — systemd hardening incomplete (LOW)

- **Evidence:** Both `guinevere-wearable-sync.service` and `guinevere-wearable-analysis.service` set `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`, but do **not** set `PrivateTmp=true`, `PrivateDevices=true`, `ProtectKernelTunables=true`, `ProtectKernelModules=true`, `ProtectControlGroups=true`, `RestrictAddressFamilies=`, `RestrictNamespaces=`, `LockPersonality=true`, `SystemCallArchitectures=native`, or `NoExecPaths=`.
- **Risk:** Defense-in-depth gap; a compromised Python runtime retains more capabilities than necessary.
- **Required action:** Add the standard hardening set per `docs\20-security\20-SecurityPolicy_v1.0.md` (which already mandates this). Cross-check with the other P-series service units for consistency.

#### L-2 — Install script does not verify the integrity of copied unit files (LOW)

- **Evidence:** `scripts\install_wearable_services.sh:14-18` `cp`s the units without a checksum or `install -m 0644`. If a hostile edit landed in `systemd/`, it would be promoted to `/etc/systemd/system` as-is.
- **Required action:** Use `install -m 0644 -o root -g root` and verify against a committed SHA256 manifest.

#### L-3 — `event.value` and `device_id` appear in structlog events (LOW)

- **Evidence:** `mi_fitness_client.py:171, 178, 182` and `alert_router.py:95, 100, 107, 120, 125` log `device_id=event.device_id` and metric values. `metric_unavailable` logs the metric name and error. This is not PII on its own, but combined with timestamps and metric type it is re-identifiable.
- **Risk:** Loki queries by `device_id` can correlate the operator's full health timeline. Acceptable for current scope (single user, private Loki) but the practice is risky if logs are ever exported.
- **Required action:** Hash `device_id` in logs, or use a per-record opaque correlation ID. Document the trade-off in the runbook.

#### L-4 — `cli_health_report` error path leaks configuration state (LOW)

- **Evidence:** `cmd_health_report.py:198-203, 316-321, 412-417` returns the user-facing message "WEARABLE_OWNER_ID/WEARABLE_DEVICE_ID belum diset." on every callback. This is fine for Faiz, but a future multi-tenant config would be probed.
- **Risk:** Trivial in current single-user scope; flag for future hardening.
- **Required action:** Replace with a generic "temporarily unavailable" message and log the actual env state server-side.

---

## Per-File Security Assessment

| File | Risk | Findings |
|---|---|---|
| `src/wearable/encryption.py` | High | H-1 (ephemeral fallback), H-3 (declared contract not honored by writer), M-5 (sensitive field list incomplete) |
| `src/wearable/mi_fitness_client.py` | Medium | M-2 (rate-limit + circuit interaction), M-4 (plaintext token cache), M-5 (metadata allowlist missing), L-3 (PII in logs), C-1 (creds source) |
| `src/wearable/health_consent.py` | Low | Clean. Fail-closed on DB error; cache TTL 5 min; cache invalidation on grant/revoke. Note: `wac_consent_check` reports `cached=True` for fail-closed blocks — minor mislabel, not security-relevant. |
| `src/wearable/config.py` | Low | Clean. No defaults that would be unsafe; region allowlist present. |
| `src/wearable/alert_router.py` | Medium | M-3 (embed leaks), M-6 (asymmetric rate limit), L-3 (PII in logs). Stub `_send_discord_dm` is acceptable pre-wire-up but must enforce ephemeral when wired. |
| `src/wearable/mood_integration.py` | Low | Clean. Does NOT touch `yandere_fsm.py` (only `mood_engine.Mood`); `_is_consent_revoked` honored; `_is_quiet_hours` bypassed for CRITICAL tier; argument/distress state respected. M-7: missing state should default to deny, currently defaults to allow. |
| `src/discord/cmd_health_report.py` | Low | M-1 (guard dependency), L-4 (error message). All three callbacks are owner-only; `defer_ephemeral` used; error handler does not leak stack. |
| `.env.wearable.example` | Low | Clean. Documented; no real values; correct security annotations. |
| `.env.wearable` | **Critical** | **C-1 (plaintext credentials), C-2 (no SOPS path rule)**. Not in git, but plaintext on disk. |
| `scripts/install_wearable_services.sh` | Medium | H-4 (no chmod 0600), L-2 (no integrity check). Otherwise uses `set -euo pipefail` and `sudo` correctly. |
| `systemd/guinevere-wearable-sync.service` | Low | L-1 (hardening incomplete). Correct: `User=guinevere`, `NoNewPrivileges`, `ProtectSystem=strict`, `ReadWritePaths=` scoped to logs. |
| `systemd/guinevere-wearable-analysis.service` | Low | L-1 (hardening incomplete). Same posture as sync unit. |

---

## Compliance Mapping

### ADR-037 (Wearable Health Pipeline)

| ADR-037 commitment | Status | Evidence |
|---|---|---|
| Y-level modifier capped at max(Y4 baseline, current - 1); never increases | **Pass** | `mood_integration.py:149-160` only maps to `Mood.{PLEASED,CONTENT,DISAPPOINTED}` — does not touch `yandere_fsm.py` or any Y-level state |
| No punishment / confrontation text from health data | **Pass** | `mood_integration.py` returns a soft `MoodModifier` with `intensity ≤ 0.7`; no punitive language in code |
| Health-discord output is ephemeral | **Partial** | `cmd_health_report.py:194, 312, 408` uses `defer_ephemeral`; `alert_router._send_discord_dm` is a stub and does not yet set `flags=64` |
| Consent revocation immediately pauses all wearable sync | **Partial** | `health_consent.py` fail-closes within 5 min (cache TTL); `mood_integration._is_consent_revoked` reads a Redis key but the writer path does not call the gate (H-3) |
| `consent ledger consulted per-sync-cycle` | **Pass** | `health_consent.py:123-157` is the per-check call site |
| Health data lives only in one place (TimescaleDB) | **Partial** | Also appears in `mood_integration` Redis keys `wearable:ghi:current` and `wearable:ghi:history` (30 days) — by design, but should be in the data-classification table |
| 15-min systemd timer (sync) and hourly (analysis) | **Pass (by installer)** | The `install_wearable_services.sh` references `*.timer` units but the `.timer` files were not in the audited set; parent should verify they exist and are not `OnCalendar=*:*` |
| HMAC keys, Mi Fitness creds, SOPS/age gate the secret boundary | **Fail** | C-1, C-2 |
| Mood integration is structurally a modifier, not a trigger | **Pass** | `mood_integration.py:97-116` returns `None` or a soft `MoodModifier`; never mutates Y-level state |

### PersonaSafetyPolicy (Y4 baseline / Y5 ceiling / Y6 prohibition)

| PersonaSafetyPolicy rule | Status |
|---|---|
| No yandere FSM coupling from health data | **Pass** — `mood_integration.py` imports only from `mood_engine` |
| Distress state suppresses health-driven persona changes | **Partial** — M-7 (missing state defaults to allow) |
| Consent revocation respected | **Pass** — `_is_consent_revoked` in `mood_integration`; writer should also call the gate (H-3) |
| Intimate / inner-journal data never mixed with wearable | **Pass** — wearable pipeline does not touch `memory.*` or `persona.*` schemas |
| Audit trail for health-driven persona changes | **Partial** — `apply_modifier` logs to structlog; no Prometheus counter wired (M-stub in `alert_router`) |

### Data Governance (Critical classification of health data)

| DG requirement | Status |
|---|---|
| App/field-level encryption for Critical | **Fail** — H-3 (writer does not encrypt) |
| Double encryption where listed | **Fail** — H-3 |
| `access_policy` metadata for health records | **Unverified** — out of scope (depends on schema columns not present in audited files) |
| Audit log for health data access | **Partial** — structlog only; no DB audit table referenced in audited code |
| Key rotation quarterly | **Fail** — H-2 |
| Secret leakage treated as data incident | **Required** — C-1 |
| `dedicated Critical/domain key` for health data | **Partial** — single `WEARABLE_ENCRYPTION_KEY`; no documented domain separation |
| `metadata` field allowlist | **Fail** — M-5 |

### Consent boundary

| Consent requirement | Status |
|---|---|
| Fail-closed on DB error | **Pass** — `health_consent.py:136-138` returns `_BLOCK_DB_FAILURE` |
| Cache TTL appropriate (5 min) | **Pass** — balances revocation latency and DB load |
| Scope granularity (7 scopes) | **Pass** — `VALID_WEARABLE_SCOPES` covers hr/activity/spo2/stress/sleep/ghi/alerts |
| Unknown scope rejected | **Pass** — `health_consent.py:125-127` |
| Paused/withdrawn states distinguished | **Pass** — three `ConsentStatus` enum values, distinct reasons |
| Per-metric mapping | **Pass** — `METRIC_TO_SCOPE` covers all six `HealthMetricType` values |
| Writer path consults gate | **Fail** — H-3 (writer does not import or call `check_wearable_consent`) |

---

## Recommendation

**NEEDS FIX — block P14 production deploy until the following items are closed:**

1. **C-1 + C-2** (rotate Mi Fitness credentials, add `.sops.yaml` path rule, re-encrypt `.env.wearable`, chmod 0600). Treat as a data incident per Data Governance §11.4.
2. **H-1** (fail-closed on missing `WEARABLE_ENCRYPTION_KEY` unless explicit test opt-in).
3. **H-3** (wire `encrypt_health_record` into the writer; update encryption docstring to match real policy).
4. **H-4** (chmod 0600 in install script; tighten `ProtectHome` and add `RestrictAddressFamilies`).
5. **H-2** (publish rotation runbook sections for `WEARABLE_ENCRYPTION_KEY` and `MI_FITNESS_PASS_TOKEN`).

After the above are fixed, re-run this audit and verify:

- `sops --decrypt .env.wearable` produces a file starting with `ENC[`
- `grep -RE "device_id=|owner_id=" src/wearable/*.py` shows every write path through `encrypt_health_record`
- A dry-run of the sync service (no token) raises rather than silently writing with an ephemeral key
- `audit-reports/p14-security-audit.md` v2 marked PASS

**Optional follow-ups (post-fix, do not block deploy):** M-1 through M-7, L-1 through L-4. None of these independently block production, but they materially harden the surface.

---

## Audit Trail

- **Auditor method:** Direct file read (no external lookups); `git ls-files` / `git check-ignore` to verify .gitignore coverage; cross-referenced ADR-037, Data Governance v1.0, PersonaSafetyPolicy v1.0.
- **Files NOT read for safety:** no actual `.sops.yaml` decryption keys, no `secrets/` contents, no encrypted backups.
- **Tools used:** filesystem read, grep, glob, bash (git metadata only).
- **Limitations:** Did not run the services; did not verify runtime Prometheus counters (stubs noted); did not test circuit-breaker behavior under load.
- **No secrets exposed in this report.** The observed `.env.wearable` contents are summarized as "plaintext credentials" — the report deliberately does not transcribe them.
