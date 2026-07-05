# P23 Research — Security / Secrets / Consent

> Status: RESEARCH. Date: 2026-06-25. Author: Guinevere research subagent.

---

## 1. Objective

Define the security, secrets-management, and consent posture for P23 "Embodied Operations / Personal OS Action Layer". P23 extends the P20 Living Autonomy Kernel's intent into real-world, executor-shaped actions across browser, desktop, VPS, GitHub, filesystem, mobile, and external surfaces. Because these actions have physical side effects and access privileged credentials, they need a secrets-inventory, redaction-pipeline, prompt-injection defense, per-surface consent model, RBAC boundary, and an append-only hash-chained audit schema before any runtime work begins.

This research answers:

- What secret inventory does each P23 executor surface need, and how does it mirror P22?
- How are secrets stored (SOPS/age), rotated, and decrypted at runtime?
- What redaction pipeline ensures no secret, PII, or raw intimate data leaks into logs, evidence, MCP, or Discord?
- How does P23 defend against prompt-injection derived action intents?
- What per-surface consent scopes are required, and what is the fail-closed/default-OFF behavior?
- What RBAC, Linux process isolation, and network controls apply?
- What audit schema (DDL) will record every action with WORM guarantees?
- How does P23 prove it never touches Aizanta/shared-VPS resources?

---

## 2. Sources Consulted (path:line)

| Source | Path | Relevant Lines | Authority Topic |
|---|---|---|---|
| Secrets Rotation Runbook | `docs/20-security/23-SecretsRotationRunbook_v1.0.md` | 1-758 | §5 secret inventory schema; §9 autonomous rotation governance; §10 per-secret procedures; §11 emergency rotation; §14 evidence redaction; Appendix C redaction rules (`docs/20-security/23-SecretsRotationRunbook_v1.0.md`) |
| Encryption Key Management Standard | `docs/20-security/22-EncryptionKeyMgmt_v1.0.md` | 1-868 | §5 key hierarchy; §10 SOPS+age standard; §11 crypto service; §14 secret inventory; §15 rotation; §17 audit logging; §18 breach response (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md`) |
| Consent & Revocation Policy | `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | 1-454 | §3 consent principles; §4 taxonomy; §5 ledger; §7 invalid patterns; §10 runtime enforcement; §13 domain-specific rules; Appendix D enforcement spec (`docs/30-data/32-ConsentRevocationPolicy_v1.0.md`) |
| ADR-015 | `adr/ADR-015-secrets-management-strategy.md` | 1-123 | SOPS + age runtime injection; plaintext secret prohibition (`adr/ADR-015-secrets-management-strategy.md`) |
| ADR-018 | `adr/ADR-018-security-architecture-defense-in-depth.md` | 1-129 | Defense-in-depth, least privilege, audit logs, prompt-injection defenses (`adr/ADR-018-security-architecture-defense-in-depth.md`) |
| ADR-019 | `adr/ADR-019-access-control-vpn-mesh-strategy.md` | 1-143 | Tailscale mesh, zero public ports, ACL/device tags (`adr/ADR-019-access-control-vpn-mesh-strategy.md`) |
| AGENTS.md | `AGENTS.md` | 1-150 | §0 BLOCKING rules: never commit secrets, never expose intimate data, never raw surveillance in artifacts (`AGENTS.md`) |
| P22 Plan | `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` | 91-159 | Secret_id mapping, SOPS/age storage, OAuth lifecycle, audit schema, rotation mini-procedures (`docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md`) |
| P22 Security Research | `docs/setup-evidence/P22/research/p22-security-consent-research.md` | 70-120 | Consent granularity, revocation cascade, audit schema (`docs/setup-evidence/P22/research/p22-security-consent-research.md`) |
| P23 Policy/Risk Research | `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md` | 1-335 | L1-L4 risk tiers, per-surface consent scopes, 7-step policy gate, F-10 block (`docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md`) |
| Secret Scanner | `src/surveillance/secret_scanner.py` | 1-64 | Redaction pipeline, entropy/pattern detection (`src/surveillance/secret_scanner.py`) |
| Consent Gate | `src/surveillance/consent_gate.py` | 1-80 | Fail-closed check_consent, Redis DB2 cache, VALID_SURVEILLANCE_SCOPES (`src/surveillance/consent_gate.py`) |
| ADR-035 Closure Plan | `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-plan.md` | 1-39 | Shared VPS isolation caveat; Aizanta boundary (`docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-plan.md`) |

---

## 3. Findings

### 3.1 Core Thesis

P23 actions touch real surfaces with real credentials. The security posture must be "guilty until proven safe": every action must be classified, consented, redacted, audited, and isolated. Secrets must be runtime-only, encrypted at rest via SOPS/age, rotated quarterly, and never appear in logs or artifacts. Consent is per-surface, default-OFF for writes, revocable with cascade, and fail-closed. Prompts derived from untrusted content are treated as Trust Level 6 and must be sanitized before they can influence an action.

---

### 3.2 Secret Inventory per Executor (mirroring P22)

Every P23 executor surface has its own `secret_id` using the template `gkv1-kek-secrets-p23-<surface>`. The schema mirrors P22 (`docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` lines 95-100): `secret_id`, `classification`, `owner`, `consumer`, `scope`, `cadence`, `revoke`, `evidence`.

| secret_id | Surface | Classification | Owner | Consumer | Scope | Cadence | Revoke | Evidence |
|---|---|---|---|---|---|---|---|---|
| `gkv1-kek-secrets-p23-browser-obscura` | Browser | Critical | Faiz | `src/p23/browser_executor.py` (future) | Obscura CDP cookies | Quarterly / exposure | SOPS rekey + CDP session clear + cookie jar purge | SOPS decrypt log, audit.action_log |
| `gkv1-kek-secrets-p23-vps-ssh` | VPS | Critical | Faiz | `src/p23/vps_executor.py` (future) | SSH key to Guinevere host | Quarterly / host exposure | Remove authorized_key, rotate key pair | SOPS rekey, SSH auth log |
| `gkv1-kek-secrets-p23-vps-tailscale` | VPS | Critical | Faiz | VPS bootstrap | Tailscale auth key | Annual / device loss | Tailscale console revoke + re-auth | Tailscale audit log, SOPS rekey |
| `gkv1-kek-secrets-p23-vps-sops-age` | VPS | Critical | Faiz | SOPS decrypt | age private key identity | Annual / compromise | Re-encrypt all SOPS files, deploy new age key | SOPS recipient audit |
| `gkv1-kek-secrets-p23-github-pat` | GitHub | Critical | Faiz | GitHub MCP / P23 adapter | Fine-grained PAT / GitHub App | Quarterly / repo exposure | GitHub token revoke + local purge | SOPS decrypt log, audit.action_log |
| `gkv1-kek-secrets-p23-github-app` | GitHub | Critical | Faiz | GitHub App installation | App private key / installation token | Quarterly / exposure | GitHub App settings revoke | SOPS decrypt log |
| `gkv1-kek-secrets-p23-filesystem` | Filesystem | n/a workspace-scoped | Faiz | `src/p23/fs_executor.py` (future) | None (workspace-scoped, no external secret) | N/A | N/A | Audit.action_log only |
| `gkv1-kek-secrets-p23-mobile-oauth` | Mobile | Critical | Faiz | Mobile push adapter | OAuth / PAT for push/sync | Quarterly / device loss | Provider revoke + local purge | SOPS decrypt log |
| `gkv1-kek-secrets-p23-external-oauth` | External | Critical/Confidential | Faiz | External action adapter | OAuth/PAT per provider | Quarterly / 401/403 | Provider revoke + cache purge | SOPS decrypt log, audit.action_log |

Notes:

- `browser` secret is Obscura CDP cookies / session tokens, not raw passwords (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §10.1).
- `filesystem` has no external secret because access is scoped to the Guinevere workspace on the VPS; authorization is via Linux `guinevere` user + path allowlist.
- All secrets default to Critical unless explicitly downgraded with documented rationale (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §14).

---

### 3.3 SOPS/age Storage and Rotation

#### Storage layout

- Encrypted YAML under `secrets/p23/executors.enc.yaml` (mirrors `secrets/p22/integrations.enc.yaml` from `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` line 104).
- Controlled by `.sops.yaml` with an age recipient entry for P23 (ADR-015, `docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §10.3).
- Repository contains only the encrypted file; plaintext is forbidden in repo, docs, evidence, or sub-agent reports (ADR-015; `docs/20-security/23-SecretsRotationRunbook_v1.0.md` §2.2).

#### Runtime decrypt

- Decrypt to tmpfs or equivalent runtime-only path (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §10.4).
- File mode `0600`, owner-only.
- Auto-cleaned after service load or action completion (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §10.4).
- Startup failure must fail closed if secrets cannot be decrypted (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §10.4).

#### Rotation

- Quarterly scheduled rotation for OAuth/PAT/SSH/CDP session tokens (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §15.1).
- Immediate trigger: exposure, 401/403, provider alert, log leak (`docs/20-security/23-SecretsRotationRunbook_v1.0.md` §4.1).
- Autonomous rotation allowed for scheduled/low-risk provider-supported flows; Faiz approval required for high-blast-radius rotations such as age private key, SSH host key, or Tailscale auth key (`docs/20-security/23-SecretsRotationRunbook_v1.0.md` §9).
- Evidence must be written to `evidence/secrets-rotation/<date>-<secret_id>.md` with no plaintext values (`docs/20-security/23-SecretsRotationRunbook_v1.0.md` §7, §14).
- `SecretRotationLog` table (mirroring P22) records `secret_id`, `rotated_at`, `rotation_due_at`, `key_version`, `evidence_path`.

---

### 3.4 Redaction Pipeline

Before any action command, intent, or outcome is written to audit or evidence, it must pass `secret_scanner.py` (pattern/entropy detection with `REDACTION_MARKER = "[REDACTED]"`).

| Stage | Input | Rule | Output |
|---|---|---|---|
| 1. Collect | Raw action command/intent/outcome, executor stderr/stdout, MCP payload, Discord message | Gather all strings bound for persistence or external channel | Unredacted buffer |
| 2. Pattern scan | Run `secret_scanner.py` regexes (AWS keys, tokens, passwords, private keys, connection strings) | High-confidence matches → `[REDACTED]` | Partially redacted buffer |
| 3. Entropy scan | Shannon entropy >= 4.5 on strings >= 32 chars (`src/surveillance/secret_scanner.py` lines 32-34) | Unknown high-entropy strings → `[REDACTED]` | Further redacted buffer |
| 4. PII redaction | Names, addresses, phone numbers, emails, intimate content | Hash or tokenize where possible; otherwise `[REDACTED]` | Audit-safe buffer |
| 5. Audit write | Write to `audit.action_log` / evidence | Secrets stored as `hash-only` or dropped | Immutable record |
| 6. Verify | Scan written artifact | Any positive finding becomes an incident (SecretsRotationRunbook §13.2) | Incident if positive |

Rules:

- No raw secrets in logs, evidence, MCP payloads, Discord, or sub-agent reports (AGENTS.md BLOCKING rules; ADR-015).
- Hashes replace values where the audit needs to prove presence without disclosure (e.g. `intent_hash`, `command_redacted`).
- A dropped secret means the entire value is replaced with `<REDACTED>` and a hash is logged instead.
- PII redaction applies to Faiz's intimate data, surveillance raw content, and safe-word/crisis context (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §17.2).

---

### 3.5 Prompt-Injection Defense (V-023)

Action intents derived from untrusted content (web pages, email, P21 voice, external messages) are classified as **Trust Level 6** per `PersonaSafetyPolicy` trust model (`docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` §13; cited in `p23-policy-gate-risk-classification-research.md`).

| Step | Defense | Action |
|---|---|---|
| 1. Classify | Source trust level | Untrusted content → `trust="6"` |
| 2. Sanitize | Strip/quarantine action-bearing directives | Remove imperative verbs, URLs with action params, encoded payloads |
| 3. Label | Wrap in `<untrusted trust="6">` tags | Prevents downstream pipeline from treating it as an direct action intent |
| 4. Quarantine | Do not execute action intents from TL6 directly | Route to human review or a sandboxed read-only summary |
| 5. Register | Record V-023 in the action threat register | `action-injection vector: untrusted content → executor intent` |

Special F-10 block:

- Any irreversible or destructive action proposed while persona pressure (yandere/punishment) is elevated must be blocked and escalated to Faiz.
- This implements `PersonaSafetyPolicy` §11 F-10: "irreversible action under persona pressure → non-persona confirmation + evidence".

---

### 3.6 Consent Model (Per-Surface)

P23 reuses the `consent.consent_ledger` table and `consent_gate.py` fail-closed logic (`src/surveillance/consent_gate.py` lines 42-80; `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` §5).

| Executor Surface | Consent Scope Example | Default | Revocation | Cascade |
|---|---|---|---|---|
| Browser | `p23:browser:read`, `p23:browser:write` | Read OFF until authorized; write OFF | Per-scope revoke; invalidate CDP cookies | Close browser context |
| Desktop | `p23:desktop:read`, `p23:desktop:write` | Read OFF; write OFF | Per-scope revoke | Stop desktop agents, clear tmp |
| VPS | `p23:vps:read`, `p23:vps:write`, `p23:vps:destructive` | Read OFF; write/destructive OFF | Per-scope + per-host revoke | Kill SSH/shell sessions, purge keys |
| GitHub | `p23:github:read`, `p23:github:write`, `p23:github:destructive` | Read OFF; write/destructive OFF | Per-scope revoke | Invalidate token cache, stop adapters |
| Filesystem | `p23:fs:read:<path-class>`, `p23:fs:write:<path-class>` | Read OFF per class; write OFF | Per-path-class revoke | Close file handles, flush caches |
| Mobile | `p23:mobile:read`, `p23:mobile:write` | Read OFF; write OFF | Per-scope revoke | Stop push/notif agents |
| External | `p23:external:<provider>:read/write/destructive` | All OFF | Per-provider + per-scope revoke | Purge tokens, stop adapters |

Principles (from `docs/30-data/32-ConsentRevocationPolicy_v1.0.md`):

- **Default OFF except L1 read**: even L1 read must be explicitly authorized once (baseline approval) before it can be cached.
- **Revocable**: any scope can be paused or withdrawn; revocation invalidates Redis cache and executor sessions.
- **Auditable**: every grant/revoke/pause writes a `consent_event_id` to the ledger with scope, purpose, data class, conditions, and evidence path.
- **Non-transferable**: consent for one surface does not imply consent for another.
- **Fail-closed cache**: if the ledger is stale, missing, or conflicted, the action is denied (`src/surveillance/consent_gate.py` lines 7-14; `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` §10.2).
- **Revocation cascade**: a revocation event must invalidate all downstream caches and stop in-flight executor work for that scope.
- **Safety features not disable-able**: safe-word, distress, incident, and platform safety rules override consent and cannot be revoked or bypassed (`docs/30-data/32-ConsentRevocationPolicy_v1.0.md` §2.1, §3).

---

### 3.7 RBAC and Network Isolation

#### Database RBAC

- Application connects as `guinevere_core` PostgreSQL role, not superuser (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §12.1).
- `guinevere_core` has `INSERT`, `SELECT` on `audit.action_log`; `UPDATE`/`DELETE` blocked by `no_update_or_delete` constraint and row-level policy (mirroring P22 DDL).

#### Linux process isolation

- Executor processes run as Linux user `guinevere`, not root.
- Each executor is placed in a cgroup with CPU/memory limits.
- SSH key at `/home/guinevere/.ssh/id_p23_vps` with mode `0600`, owner `guinevere`.
- age private key at `/home/guinevere/.age/key.txt` with mode `0600` (`docs/20-security/22-EncryptionKeyMgmt_v1.0.md` §10.3).

#### Network

- Tailscale mesh for all admin/service traffic (ADR-019).
- Zero public ports on the VPS.
- TLS 1.3 for all outbound provider connections.
- External API calls route through Tailscale + TLS, never over plaintext.

---

### 3.8 Audit Schema DDL

Every P23 action produces one row in `audit.action_log`, mirroring P22's `audit.integration_api_log` (`docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` lines 128-157). It is append-only, hash-chained, and WORM.

```sql
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE audit.action_log (
    id                BIGSERIAL PRIMARY KEY,
    event_id          UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    sequence          BIGSERIAL NOT NULL,
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_type        TEXT NOT NULL CHECK (actor_type IN ('user','agent','system')),
    actor_id          TEXT NOT NULL,
    executor          TEXT NOT NULL,                       -- browser/desktop/vps/github/filesystem/mobile/external
    surface           TEXT NOT NULL,                       -- e.g. obscura-cdp, ssh, github-pat, fs-tmp
    action_id         TEXT NOT NULL,                       -- stable action identifier
    namespace         TEXT NOT NULL DEFAULT 'default',
    risk_tier         TEXT NOT NULL CHECK (risk_tier IN ('L1','L2','L3','L4')),
    intent_hash       TEXT NOT NULL,                       -- SHA-256 of sanitized intent
    command_redacted  TEXT NOT NULL,                       -- command after secret_scanner redaction
    outcome           TEXT NOT NULL CHECK (outcome IN ('success','failure','blocked','rate_limited','consent_denied','hard_stop')),
    artifact_path     TEXT,                                -- path to evidence artifact, if any
    rollback_state    JSONB,                               -- snapshot/reference for rollback
    previous_hash     TEXT NOT NULL,
    event_hash        TEXT NOT NULL,
    CONSTRAINT no_update_or_delete CHECK (false) NO INHERIT
);

REVOKE UPDATE, DELETE ON audit.action_log FROM guinevere_core;
GRANT INSERT, SELECT ON audit.action_log TO guinevere_core;

COMMENT ON TABLE audit.action_log IS
    'Append-only, hash-chained, WORM audit log for every P23 executor action.';
```

Hash-chain rule:

```
event_hash = SHA256(canonical_payload + previous_hash)
```

- `canonical_payload` includes: `event_id`, `sequence`, `occurred_at`, `actor_id`, `executor`, `surface`, `action_id`, `namespace`, `risk_tier`, `intent_hash`, `command_redacted`, `outcome`.
- `previous_hash` of the first event is the genesis hash stored in a separate `audit.chain_state` table.
- A periodic verifier re-derives hashes and alerts on any break.
- WORM archive after 1 year.

Retention classes (mirroring P22):

- Hot 0-90 days in primary PostgreSQL.
- Warm 90 days-1 year in compressed object storage.
- Cold 1-7 years in WORM archive.

---

### 3.9 Shared-VPS Isolation Proof Matrix

P23 must never touch Aizanta resources (Redis 10-15, `aizanta-*`, `/home/aizanta`) per the project boundary (`docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-plan.md` lines 15-28).

| Boundary | P23 Allowable | P23 Forbidden | Verification |
|---|---|---|---|
| User account | `guinevere` only | `aizanta`, `root` direct shell | `id` check in executor preflight |
| Home directory | `/home/guinevere` only | `/home/aizanta` | Path allowlist reject |
| Redis databases | P23's own logical DB(s), e.g. DB6 | Redis DB 10-15 (`aizanta-*`) | Connection string check |
| Network namespace | Tailscale internal IPs for Guinevere services | Aizanta service ports | `ss`/network policy scan |
| File ownership | Files owned by `guinevere` | Files owned by `aizanta` | `stat` check |
| Systemd units | `guinevere-p23-*` | `aizanta-*` | Unit name allowlist |
| Process tree | Children of `guinevere` user | Children of `aizanta` user | `ps` filter in health check |

Executor isolation proof must be logged at executor startup:

- Current user.
- Allowed path prefix.
- Allowed Redis DBs.
- Allowed Tailscale IPs.
- Forbidden prefix list (`aizanta`, `10.0.0.x` Aizanta subnet if defined).

---

## 4. Implications for P23 Design

1. **Secrets must be declared before code**: every executor surface must have an `secret_id` row before implementation begins, matching P22 Wave 0 governance.
2. **Redaction is non-optional middleware**: every action command/intent/outcome path must call `secret_scanner.py` before persistence or external channel write.
3. **Prompt-injection handling is a first-class control**: TL6 content must be labeled, quarantined, and prevented from generating action intents without human review.
4. **Consent ledger must be extended with P23 scopes**: reuse `consent_gate.py` and the existing consent ledger table; add P23 executor scopes.
5. **Audit table must be created before runtime**: the `audit.action_log` DDL and hash-chain verifier are prerequisites for any executor action.
6. **RBAC must be enforced at multiple layers**: PostgreSQL role, Linux user, cgroup, Tailscale, TLS 1.3.
7. **Aizanta isolation must be verifiable**: every executor startup logs its isolation boundary and refuses forbidden paths/Redis DBs/usernames.

---

## 5. Risks / Open Questions

| ID | Risk / Open Question | Suggested Follow-Up |
|---|---|---|
| RQ-01 | Exact Obscura CDP secret shape is not yet inventoried. | Add `gkv1-kek-secrets-p23-browser-obscura` to SOPS after Obscura integration research. |
| RQ-02 | SSH key for P23 VPS executor may overlap with Faiz's personal SSH key. | Define dedicated `id_p23_vps` key pair and authorized_keys line. |
| RQ-03 | Quarterly rotation of OAuth refresh tokens depends on provider support. | Verify per-provider refresh-token rotation semantics. |
| RQ-04 | Secret scanner pattern list may miss new P23-specific secrets (e.g. CDP session tokens). | Update `secret_scanner.py` patterns when Obscura/CDP integration begins. |
| RQ-05 | Fail-closed consent cache behavior when Redis and DB are both unavailable is untested. | Define emergency minimum-necessary processing limits for P23. |
| RQ-06 | Hash-chain verifier job (periodic integrity check) is not yet implemented. | Port P22 verifier to P23 or share a common module. |
| RQ-07 | WORM cold archive provider and retention policy are not specified. | Reuse P22 retention classes and object storage lifecycle rules. |
| RQ-08 | cgroup limits for executor processes need concrete values. | Define CPU/memory quotas per executor surface. |

---

## 6. Recommendations to Planner

1. **Adopt the secret inventory table verbatim** as the P23 Wave 0 governance artifact; update `docs/20-security/23-SecretsRotationRunbook_v1.0.md` §5 with P23 entries.
2. **Create `secrets/p23/executors.enc.yaml`** under `.sops.yaml` before any runtime secret is added.
3. **Implement redaction middleware** at `src/p23/redaction.py` that wraps `secret_scanner.py` and runs before every audit write.
4. **Register V-023** in the action threat register and add TL6 quarantine logic to the action-intent parser.
5. **Extend `consent_gate.py`** with P23 executor scopes and the default-OFF/fail-closed rules in Section 3.6.
6. **Create the `audit.action_log` table** exactly as specified in Section 3.8 before any executor action is tested.
7. **Enforce isolation proof** in every executor's `__enter__` / startup method and log the boundary check to `audit.action_log`.
8. **Add tests** for: secret redaction, consent fail-closed, hash-chain integrity, and Aizanta isolation rejection.

---

## 7. Verdict

P23 security/secrets/consent posture is ready for design freeze and planner input. The framework is consistent with ADR-015 (SOPS/age plaintext prohibition), ADR-018 (defense-in-depth), ADR-019 (Tailscale zero public ports), `docs/20-security/22-EncryptionKeyMgmt_v1.0.md`, `docs/20-security/23-SecretsRotationRunbook_v1.0.md`, `docs/30-data/32-ConsentRevocationPolicy_v1.0.md`, `AGENTS.md` BLOCKING rules, and the P22/P23 research lineage. The required output artifact is complete and written to the exact requested path.

**Verdict:** ACCEPT for planner input. P23 security, secrets, and consent research is complete and ready for Wave 0 governance implementation.

---

*File: `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md`*
