# P19 Research: Security & Secrets Boundary Per-Project

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** How secrets and security boundaries are isolated per project.

---

## 1. Executive Summary

Secrets are **global today**: one SOPS/age key encrypts `secrets/*.yaml`, and systemd units load shared `.env.*` files. P19 must introduce **per-project secret files** so project A's adapter cannot read project B's API key, and **per-project deploy boundaries** so deploying project A cannot touch Guinevere core or project B. The shared age recipient (Faiz's key) is fine because SOPS encrypts per-file.

**Key invariant (hard rejection):** Project A's adapter must NOT decrypt/read project B's secrets. Deploy of project X requires `consent.autonomy.high_blast` for project X OR explicit Faiz approval — never automatic from another project's autonomy.

---

## 2. Current Secrets Inventory

From `.sops.yaml` and `secrets/`:
- `secrets/guinevere-secrets.yaml` — global secrets.
- `secrets/db-passwords.yaml` — DB passwords.
- `secrets/redis-password.yaml` — Redis password.
- `secrets/discord-secrets.enc.yaml` — Discord bot token.
- `secrets/gmail-client-secrets.json` / `secrets/gmail-token.json` — Gmail OAuth.
- `secrets/backup/restic-password-plaintext.env`, `idcloudhost-s3-plaintext.env`, `cloudflare-r2-plaintext.env` — backup credentials (plaintext-named).
- Planned: `secrets/voice-secrets.enc.yaml` (P21), `secrets/p22/integrations.enc.yaml` (P22).

SOPS config (`.sops.yaml`): `creation_rules` for `secrets/*.yaml`, `secrets/*.env`, `.env.wearable`, all encrypted with Faiz's age recipient (public key documented in committed `.sops.yaml`; not reproduced here).

---

## 3. Current Secret Loading Pattern

- systemd units decrypt at startup: `deploy/discord/guinevere-discord.service` uses `ExecStartPre=/usr/bin/sops --decrypt ... > /run/guinevere-discord-token` then `ExecStopPost=/usr/bin/shred -u`.
- Each unit loads an `EnvironmentFile` (`.env.gmail`, `.env.x_poster`, `.env.wearable`, etc.).
- Runtime: env vars read by `GmailSettings`, `XPosterSettings`, `WearableConfig`, etc.

---

## 4. Per-Project Secret Design

### 4.1 Option A: single file per project
- `secrets/projects/{project_id}/secrets.enc.yaml` — all project-scoped secrets for one project.
- SOPS rule: `path_regex: secrets/projects/.*\.yaml$` → age key.

### 4.2 Option B: domain-prefixed within single file
- `projects.{project_id}.gmail.oauth`, `projects.{project_id}.github.pat` within one file.
- Pros: one file.
- Cons: monolithic; rotate one project's key → re-encrypt all.

### 4.3 Option C: separate SOPS files per (project, domain) (RECOMMENDED)
- `secrets/projects/{project_id}/gmail.enc.yaml`, `secrets/projects/{project_id}/github.enc.yaml`, etc.
- Pros: least-privilege (load only what's needed), independent rotation.
- Cons: more files.

### 4.4 Recommendation
**Option C** for least-privilege + independent rotation. Each adapter loads only its own project+domain secret file.

---

## 5. Hard Rejection: Secret Leak Between Projects

- Project A's adapter loads only `secrets/projects/{project_A}/gmail.enc.yaml`.
- Project B's adapter loads only `secrets/projects/{project_B}/gmail.enc.yaml`.
- No shared env var namespace: project secrets decrypted into `GUINEVERE_{PROJECT}_{DOMAIN}_{KEY}` env vars (e.g., `GUINEVERE_WORK_GMAIL_OAUTH_TOKEN`) — process-scoped, not global.
- Test: `test_secret_isolation` — project A adapter cannot read project B's secret env var.

---

## 6. Env Var Isolation

- Current: single `.env` loaded by core.
- Proposed: per-project env files `.env.projects.{project_id}` OR env var prefix `GUINEVERE_{PROJECT}_{KEY}`.
- Process-level: each project's background cognition/loop runs in a context that sets only that project's env vars.

---

## 7. Deploy Boundary Per-Project

Per ADR-016 (CI/CD & Autonomous Deployment):
- Each project has its own deploy scope.
- Project A can deploy project A's code (under project A's `consent.autonomy.high_blast` or Faiz approval).
- Project A CANNOT deploy project B's code or Guinevere core.
- Guinevere core deploy is a separate, higher gate (always requires explicit Faiz approval per AGENTS.md §0.1).

---

## 8. Deploy Policy Gate

Deploy of project X requires:
1. `consent.autonomy.high_blast` granted for project X (project-scoped), OR explicit Faiz approval.
2. Backup → canary → smoke test → rollback gate (P20 V-002/LK-014 pattern).
3. NOT automatic from another project's autonomy.
4. Audit row: `audit.audit_trail` event_type `project_deploy` with `project_id`.

A project's autonomy exception (§0.1) applies ONLY to that project's own deploy scope, not cross-project.

---

## 9. Prompt Injection Per-Project

- Untrusted input in project A labeled `<untrusted source="project_a" trust="6">`.
- Project A's injection cannot leak into project B's context (sessions are project-isolated, recall is project-filtered).
- Injection vector registry: project-scoped vectors (e.g., `V-022` voice stays global; project-specific vectors added per project as needed).

---

## 10. RBAC Per-Project

- Sub-agents for project A are task-scoped to project A's data (memory, KG, audit).
- Sub-agent cannot access project B's memory/KG/audit unless explicitly granted (rare, Faiz-approved, audited).
- `projects.loop_instances.project_id` scopes loop context; tool registry restricts tools per project.

---

## 11. Audit Journal Per-Project

- Audit rows include `project_id` (nullable for global safety events like HARD STOP).
- Audit journal queryable per-project: "all audit events for project X".
- Hash chain stays global (single chain, project_id is a column) — simpler, verified.

---

## 12. Secrets Rotation Per-Project

- Rotate project A's GitHub PAT → only project A affected (only project A's `secrets/projects/{project_A}/github.enc.yaml` re-encrypted).
- `SecretRotationLog` row per rotation (per `src/memory/models.py:1046-1061`).
- Quarterly rotation cadence per project (per SecretsRotationRunbook).

---

## 13. Key Compromise Response

If project A's key compromised:
1. Revoke provider-side (GitHub/Google/Notion).
2. Rotate project A's secret file.
3. Pause project A (`project:{project_A}:paused`).
4. Other projects unaffected (separate secret files).
5. If shared key (e.g., the age recipient) compromised → all projects affected; rotate age recipient (Faiz-only, high gate).

---

## 14. Tailscale Mesh & Network

- Project isolation doesn't require separate Tailscale nodes (single VPS).
- ACLs can be per-project if needed (e.g., project "work" integrations route through a specific exit node) — optional, not MVP.

---

## 15. Break-Glass Access Per-Project

- Break-glass is per-project (not all-projects): `break_glass:{project_id}` with time-bound (max 4h) + audit + post-use review.
- Global break-glass only for SEV0/SEV1 incidents affecting the whole system.

---

## 16. Evidence Storage Per-Project

- `docs/setup-evidence/P19/` is project = `guinevere` (the core project itself).
- Other runtime projects (e.g., "work", "personal") have their own evidence roots under `evidence/projects/{project_id}/` (runtime evidence, separate from phase evidence).
- Guinevere-core phases (P0-P22) are project = `guinevere`.

---

## 17. Hard Rejection: Cross-Project Secret Read

- Test: `test_secret_isolation` — project A adapter cannot decrypt/read project B's `secrets/projects/{project_B}/*.enc.yaml`.
- Mechanism: each adapter loads only its project+domain file; env vars are process-scoped with project prefix.

---

## 18. SOPS Age Recipients

- Same age recipient list across projects (Faiz's public age key, as in committed `.sops.yaml`) — OK, because SOPS encrypts per-file. Faiz can decrypt any project's file (he's the owner), but runtime adapters load only their own.
- If a collaborator is added to a project, that project's files can have an additional age recipient — per-file granularity.

---

## 19. Hard Rejection: Deploy Crossing

- Test: `test_deploy_boundary` — deploying project A does NOT trigger Guinevere core restart without policy gate.
- Mechanism: project deploy is scoped to project A's files/services; core deploy is a separate gate.

---

## 20. Conclusion

P19 isolates secrets per-project via `secrets/projects/{project_id}/{domain}.enc.yaml` files (least-privilege, independent rotation), process-scoped env vars with `GUINEVERE_{PROJECT}_{KEY}` prefix, and per-project deploy boundaries gated by project-scoped `consent.autonomy.high_blast` or Faiz approval. The shared age recipient is fine (per-file encryption). Deploy of one project cannot touch another project or Guinevere core without an explicit policy gate. Key compromise in one project isolates to that project.
