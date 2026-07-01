# P23 Audit Round 1 — Security / Secrets

> **Auditor:** Independent.  
> **Date:** 2026-06-25.  
> **Subject:** P23 "Embodied Operations / Personal OS Action Layer" — Security / Secrets / Consent / Isolation dimension.  
> **Scope:** Plan §23/§26/§27/§28/§32/§34/§36; research `p23-security-secrets-consent-research.md`; ground truth `docs/20-security/{20,21,22,23,24}_v1.0.md`, `docs/30-data/{30,32}_v1.0.md`, `src/surveillance/secret_scanner.py`, `src/surveillance/consent_gate.py`, ADR-015/018/019, `src/mcp/auth.py`.

---

## 1. Audit Scope

Evaluate whether the P23 plan/research adequately defines and justifies security/secrets posture against the project's own ground-truth policy and code:

1. **Secrets inventory & SOPS/age storage:** Are `secret_id`s mapped to `gkv1-kek-secrets-p23-*`? Is SOPS/age storage (`secrets/p23/executors.enc.yaml`) defined? Runtime decrypt to tmpfs `0600`, no plaintext, quarterly rotation, `SecretRotationLog` row?
2. **Redaction pipeline:** Does every action command/intent/outcome/artifact pass `secret_scanner` before audit write? Are secrets hash-only/dropped? No raw secrets in logs/evidence/MCP/Discord?
3. **Prompt-injection defense (V-023):** Are action intents from untrusted content (web/email/voice) Trust Level 6 with classify→sanitize→quarantine? Is V-023 registered? Is F-10 enforced?
4. **RBAC / network / host isolation:** `guinevere_core` DB user (no superuser), executor processes as `guinevere` Linux user with cgroup limits, Tailscale + TLS 1.3?
5. **Audit trail:** Hash-chained `audit.action_log`, WORM (no UPDATE/DELETE), hash-chain verification, minimal/non-punitive for safe-word?
6. **Isolation:** Per-executor isolation boundary, shared-VPS Aizanta-proof (never touch `aizanta-*`, Redis 10-15, `/home/aizanta`)?
7. **DDL/schema soundness & consistency:** Are the audit DDL (plan §27) and DB schema (plan §32) sound and consistent with P22 `audit.integration_api_log`?

---

## 2. Findings

### 2.1 Secrets inventory and `gkv1-kek-secrets-p23-*` mapping

**Status:** PASS with observation

- The plan (`p23-embodied-operations-enterprise-plan.md:26`) maps every P23 executor surface to a `secret_id` using the template `gkv1-kek-secrets-p23-<surface>`: browser (`gkv1-kek-secrets-p23-obscura-cookies`), GitHub (`gkv1-kek-secrets-p23-github-pat`), VPS reuses existing SSH/Tailscale/age keys, external reuses P22 `gkv1-kek-secrets-p22-*`, filesystem has no external secret.
- The research (`p23-security-secrets-consent-research.md:3.2`) expands this to a full 9-row inventory with owner, consumer, scope, cadence, revoke path, and evidence path, mirroring P22 (`p22-life-integration-hub-plan.md:95-100`).
- The inventory is consistent with `22-EncryptionKeyMgmt_v1.0.md` §14 (secret inventory fields), `23-SecretsRotationRunbook_v1.0.md` §5 (inventory schema), and ADR-015 (SOPS/age runtime injection).

**Observation:** The actual `secrets/p23/executors.enc.yaml` file does **not** exist yet (`Glob` returned no files). This is acceptable because P23 is in planning and no runtime secrets are added, but Wave P23-001 must create the SOPS skeleton with no real secrets before any implementation begins.

**Recommendation:** Create `secrets/p23/executors.enc.yaml` as part of P23-001 with only placeholder/key metadata; ensure `.sops.yaml` covers `secrets/p23/*.yaml` (current `.sops.yaml` matches `secrets/.*\.yaml$`, which is sufficient).

### 2.2 SOPS/age storage and runtime decrypt to tmpfs 0600

**Status:** PASS

- The plan (`p23-embodied-operations-enterprise-plan.md:388`) states storage at `secrets/p23/executors.enc.yaml` under `.sops.yaml` `secrets/.*\.yaml$` rule, runtime decrypt to tmpfs `0600`, never persist plaintext.
- The research (`p23-security-secrets-consent-research.md:3.3`) repeats the same controls and cites `22-EncryptionKeyMgmt_v1.0.md` §10.4 (runtime decrypt to tmpfs, `0600`, auto-clean, fail-closed startup) and ADR-015.
- Ground-truth `.sops.yaml` (`:6-8`) already covers `secrets/.*\.yaml$` with the age recipient, so `secrets/p23/executors.enc.yaml` will be encrypted under the existing key.

**Recommendation:** No change. Verify at P23-001 that `sops -d secrets/p23/executors.enc.yaml` succeeds only on authorized host and that file permissions are `0600` after decrypt.

### 2.3 Quarterly rotation + `SecretRotationLog` row

**Status:** PASS

- Plan (`p23-embodied-operations-enterprise-plan.md:388`) and research (`p23-security-secrets-consent-research.md:3.3`) both require quarterly rotation and a `SecretRotationLog` row.
- The `SecretRotationLog` table is verified in code at `src/memory/models.py:1046-1061` with `secret_name`, `rotation_type`, `old_key_id`, `new_key_id`, `rotated_at`.
- This mirrors P21/P22 precedent; the first rotation must create the row and evidence per `23-SecretsRotationRunbook_v1.0.md` §7.

**Recommendation:** No change. Ensure the first P23 secret rotation (Wave P23-001 or first real key rotation) writes the `SecretRotationLog` row.

### 2.4 Redaction pipeline: every command/intent/outcome/artifact passes `secret_scanner` before audit write

**Status:** PASS with observation

- The plan (`p23-embodied-operations-enterprise-plan.md:389`) explicitly states: "action command/intent/outcome/artifact passes `src/surveillance/secret_scanner.py` BEFORE audit write + artifact write. Secrets to `[REDACTED:sha256:8chars]` (hash-only/drop)."
- The research (`p23-security-secrets-consent-research.md:3.4`) defines a 6-stage redaction pipeline: collect → pattern scan → entropy scan → PII redaction → audit write → verify. It names `secret_scanner.py` with `REDACTION_MARKER = "[REDACTED]"` and Shannon entropy >= 4.5 on strings >= 32 chars.
- Ground-truth `src/surveillance/secret_scanner.py` is verified:
  - `REDACTION_MARKER = "[REDACTED]"` (`:33`)
  - `ENTROPY_THRESHOLD = 4.5`, `MIN_ENTROPY_STRING_LENGTH = 32` (`:34-35`)
  - Patterns include AWS keys, GitHub PATs, OpenAI keys, generic API keys, bearer tokens, JWTs, PEM keys, DB connection strings, Discord tokens, Slack tokens, Stripe keys, age keys, URL passwords, password assignments (`:72-170`).
  - `redact_secrets(text)` returns redacted text (`:303-318`).

**Observation:** The 6-stage pipeline is design documentation only; no runtime wrapper `src/p23/redaction.py` exists yet. P23-016 is responsible for implementing it.

**Recommendation:** Implement `src/life_kernel/executors/audit_writer.py` (P23-016) so every executor calls `secret_scanner.redact_secrets()` before any persistence or external channel write.

### 2.5 No raw secrets in logs/evidence/MCP/Discord

**Status:** PASS

- Plan (`p23-embodied-operations-enterprise-plan.md:389`, `:443`) and research (`p23-security-secrets-consent-research.md:3.4`) both explicitly forbid raw secrets in logs, evidence, MCP, Discord, sub-agent reports.
- This is consistent with AGENTS.md BLOCKING rules and `23-SecretsRotationRunbook_v1.0.md` §2.2 (plaintext prohibition) and §14 (evidence redaction rules).
- Artifact model (`p23-observability-dashboard-audit-research.md:3.6`) requires every artifact file to pass `secret_scanner` + PII redaction before write.

**Recommendation:** No change.

### 2.6 Prompt-injection defense (V-023) for action intents from untrusted content

**Status:** PASS with observation

- The plan (`p23-embodied-operations-enterprise-plan.md:391`) states: "action intents from untrusted content (web/email/P21 voice) = Trust Level 6. Classify → sanitize → label untrusted → quarantine → L7-L9. F-10 blocks persona-pressure to irreversible."
- The research (`p23-security-secrets-consent-research.md:3.5`) registers V-023 as "action-injection vector: untrusted content → executor intent" and defines the 5-step defense: classify, sanitize, label, quarantine, register.
- Ground-truth `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §5:
  - V-003 (web) and V-004 (email) are TL6 untrusted.
  - V-005 (WhatsApp) and V-017 (GitHub content) are TL6.
  - V-021 covers indirect injection via tool output.
  - Section 7.3 lists instruction patterns (role redefinition, policy override, safe-word bypass, authority manipulation, memory manipulation, consent manipulation, tool-gating bypass).
  - F-10 is listed in §13.2 as "Irreversible action under persona pressure → CRITICAL" with detection method "Tool-risk gate + high-blast-radius action check".
- Plan hard-rejection criterion #8 links to §26 redaction and §36 secret-scan test.

**Observation:** V-023 is conceptually registered, but the actual `24-PromptInjection_ModelSafety_v1.0.md` catalog does not yet list a vector ID "V-023"; it stops at V-021. The plan says P23-001 will add the V-023 section to `24-PromptInjection_ModelSafety_v1.0.md`.

**Recommendation:** P23-001 must add the explicit V-023 entry to `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` with vector ID, surface (action intents), trust level 6, primary defense (classify/sanitize/quarantine), and test ID PI-0xx.

### 2.7 RBAC: `guinevere_core` DB user (no superuser)

**Status:** PASS

- Plan (`p23-embodied-operations-enterprise-plan.md:529`) states: "No superuser: `guinevere_core` DB user (RBAC, ADR-018)."
- Research (`p23-security-secrets-consent-research.md:3.7`) states: "Application connects as `guinevere_core` PostgreSQL role, not superuser... `guinevere_core` has `INSERT`, `SELECT` on `audit.action_log`; `UPDATE`/`DELETE` blocked."
- Ground-truth `docs/20-security/21-AccessControl_RBAC_ABAC_v1.0.md` §8.1 defines `db_core_memory_rw` and other least-privilege roles, with explicit denial of broad all-schema runtime roles.

**Recommendation:** No change. Ensure the P23 migration grants only `INSERT, SELECT` on `audit.action_log` and `p23.action_queue` to `guinevere_core`.

### 2.8 Linux process isolation: executor processes as `guinevere` user, cgroup-limited

**Status:** PASS

- Plan (`p23-embodied-operations-enterprise-plan.md:13`, `:38`) references `MemoryMax=8G`, `CPUQuota=200%` per `IMPLEMENTATION_GUIDE.md` §6 and the `guinevere-actions.service` with scoped limits.
- Research (`p23-security-secrets-consent-research.md:3.7`) states executor processes run as Linux user `guinevere`, not root, with cgroup CPU/memory limits, SSH key mode `0600`, age key mode `0600`.
- Ground-truth `IMPLEMENTATION_GUIDE.md` §6 (cited in plan) defines the shared-VPS isolation matrix with separate users, Docker networks, PostgreSQL DBs, Redis DB numbers, and systemd prefixes.

**Recommendation:** No change.

### 2.9 Tailscale + TLS 1.3

**Status:** PASS

- Plan (`p23-embodied-operations-enterprise-plan.md:390`) and research (`p23-security-secrets-consent-research.md:3.7`) require Tailscale mesh + TLS 1.3 for all outbound provider connections.
- Ground-truth ADR-019 accepts "Tailscale mesh for all devices with zero public ports." `22-EncryptionKeyMgmt_v1.0.md` §6.4 requires "Transport: Tailscale WireGuard + TLS."

**Recommendation:** No change.

### 2.10 Hash-chained `audit.action_log`, WORM, hash-chain verification

**Status:** PASS with observation

- Plan (`p23-embodied-operations-enterprise-plan.md:27`, `:407-432`) provides the full `audit.action_log` DDL mirroring P22 `audit.integration_api_log`:
  - `event_hash = SHA256(canonical_payload + previous_hash)`
  - `CONSTRAINT no_update_or_delete CHECK (false) NO INHERIT`
  - `REVOKE UPDATE, DELETE ON audit.action_log FROM guinevere_core;`
  - `GRANT INSERT, SELECT ON audit.action_log TO guinevere_core;`
- The research (`p23-security-secrets-consent-research.md:3.8`) provides an equivalent DDL with the same hash-chain and WORM properties.
- P22 precedent (`p22-life-integration-hub-plan.md:128-157`) verifies the same pattern for `audit.integration_api_log`.
- Plan (`p23-embodied-operations-enterprise-plan.md:435`) notes minimal/non-punitive safe-word/distress events per `PersonaSafetyPolicy` §16.

**Observation:** The `audit.action_log` table and hash-chain verifier are design-only; the Alembic migration `p23_001_action_layer.py` does not exist yet. P23-003/016 will create it.

**Recommendation:** Ensure P23-003 creates the Alembic migration with `down_revision = 'p20_001_life_kernel_schema'` and that the hash-chain verifier is implemented in P23-016.

### 2.11 Shared-VPS Aizanta-proof boundary

**Status:** PASS

- Plan (`p23-embodied-operations-enterprise-plan.md:13`, `:226`) states: "NEVER touches `aizanta-*` services, `/home/aizanta`, Redis DBs 10-15, aizanta DB. SSH only `guinevere@localhost` or Tailscale nodes. Every VPS action asserts no Aizanta impact."
- Plan hard-rejection criterion #13 (#7 in this audit's numbering) requires isolation proof.
- Research (`p23-security-secrets-consent-research.md:3.9`) provides a full "Shared-VPS Isolation Proof Matrix" with user account, home directory, Redis databases, network namespace, file ownership, systemd units, and process tree checks.
- Ground-truth `IMPLEMENTATION_GUIDE.md` §6 defines the Guinevere/Aizanta separation (Redis 0-5 vs 10-15, separate users, etc.).

**Recommendation:** No change. Ensure every VPS executor startup logs the isolation boundary check to `audit.action_log`.

### 2.12 Audit DDL and DB schema consistency with P22 `audit.integration_api_log`

**Status:** PASS with observation

- Plan (`p23-embodied-operations-enterprise-plan.md:485-525`) provides `p23.action_queue` DDL with idempotency key, retry/backoff, cancel, and rollback state. It references `audit.action_log` for compliance audit.
- The `audit.action_log` DDL in plan §27 mirrors P22 `audit.integration_api_log` with renamed/context-specific columns (`executor`, `surface`, `action_id`, `risk_tier`, `command_redacted`, `rollback_state`).
- `p23-rollback-idempotency-research.md` proposes a separate `audit.p23_action_log` table, but the plan resolves to a single `audit.action_log` table (plan §27). This is a deliberate design decision to keep the audit surface unified.

**Observation:** The rollback research's `audit.p23_action_log` proposal could create schema drift if implemented literally. The plan's `audit.action_log` should be the authoritative schema.

**Recommendation:** Reject or supersede the `audit.p23_action_log` table from `p23-rollback-idempotency-research.md`; implement only `audit.action_log` as defined in plan §27. Document this decision in P23-003/016.

---

## 3. Hard-Rejection Criteria Check (#7, #8, #13)

| Hard-Rejection Criterion | Requirement | Verdict | Evidence |
|---|---|---|---|
| **#7** — Browser/desktop/VPS/GitHub/file/mobile executors lack isolation boundary. | Every executor must have a defined isolation boundary (per-context browser, workspace-only filesystem, guinevere-user VPS, scoped GitHub PAT, Aizanta-proof). | **PASS** | Plan §11-17 defines per-executor isolation; research §3.9 gives isolation proof matrix; `IMPLEMENTATION_GUIDE.md` §6 gives shared-VPS rules. |
| **#8** — Secrets can enter logs/evidence/artifacts. | Every command/intent/outcome/artifact must pass `secret_scanner`; secrets hash-only/dropped; no raw secrets in logs/evidence/MCP/Discord. | **PASS** | Plan §26, §28; research §3.4; `src/surveillance/secret_scanner.py` verified. |
| **#13** — Production service others can be disrupted without isolation proof. | P23 must prove it never touches Aizanta/shared-VPS resources and has independent systemd service/feature flags. | **PASS** | Plan §13 Aizanta-proof; §38 isolated `guinevere-actions.service`; §43 collision scan; hard-rejection #13 mitigated. |

---

## 4. Verdict

**VERDICT: PASS**

The P23 plan and research present a sound, internally consistent, and ground-truth-aligned security/secrets posture. Secrets are mapped to `gkv1-kek-secrets-p23-*`, SOPS/age storage and runtime tmpfs `0600` decrypt are defined, quarterly rotation + `SecretRotationLog` is bound to the existing model, and the redaction pipeline explicitly wraps `secret_scanner.py` before any audit/artifact write. V-023 action-injection is conceptually registered and F-10 is enforced via the L3/persona-pressure gate. RBAC (`guinevere_core` non-superuser), Linux user/cgroup isolation, Tailscale + TLS 1.3, and Aizanta-proof shared-VPS boundaries are all specified. The `audit.action_log` DDL mirrors P22's proven hash-chained WORM pattern.

The remaining work is implementation (P23-001 creates the SOPS skeleton, P23-003 creates the migration, P23-016 implements the redaction/audit writer, and P23-001 adds the explicit V-023 entry to `24-PromptInjection_ModelSafety_v1.0.md`), not design.

**Output path:** `docs/setup-evidence/P23/evidence/audits/round-1/security-secrets.md`
