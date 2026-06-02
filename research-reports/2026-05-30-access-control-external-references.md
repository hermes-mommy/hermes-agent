# Access Control External References

**Report Type:** External reference evidence for Access Control RBAC/ABAC Matrix  
**Date:** 2026-05-30  
**Owner:** Samm  
**Prepared by:** Guinevere de Baroque  
**Status:** Accepted evidence for RBAC/ABAC Matrix v1.0  

## Related Documents

| Document | Relationship |
|---|---|
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Normative parent ADR: Tailscale mesh, zero public ports. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent ADR: least privilege, service hardening, audit logs. |
| `adr/ADR-008-memory-encryption-key-management.md` | Normative parent ADR: key hierarchy, encryption, break-glass. |
| `adr/ADR-024-data-governance-classification-policy.md` | Normative parent ADR: classification tiers, access control. |
| `adr/ADR-012-sub-agent-orchestration-governance.md` | Normative parent ADR: sub-agent file-based output, trust levels. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Child policy: classification tiers, retention, access control, incident response. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Child standard: key hierarchy, envelope encryption, rotation, break-glass. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Cross-boundary safety policy: safe word, distress, sensitive recall restrictions. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Runtime architecture: services, network topology, systemd units, PgBouncer users. |
| `Guinevere_MemorySchema_v2.0.md` | Memory model: schemas, tables, sensitive fields, encryption profiles. |
| `research-reports/2026-05-30-access-control-source-map.md` | Source evidence report for this matrix. |
| `research-reports/2026-05-30-access-control-surface-map.md` | Surface mapping evidence for this matrix. |

---

## 1. Purpose

This report summarizes implementable IAM, RBAC, and ABAC patterns from authoritative external sources, with reference URLs for least privilege, service accounts, short-lived grants, break-glass, PostgreSQL grants/RLS, Redis ACL/key prefixes, FastAPI auth dependencies, Tailscale ACL/tags, object storage IAM prefix policies, audit logging, policy-as-code, and AI/sub-agent context gating. The final RBAC/ABAC Matrix must translate these patterns into concrete rules for Project Guinevere.

---

## 2. IAM / RBAC / ABAC Foundational Patterns

### 2.1 Least Privilege

**Principle:** Grant only the permissions necessary for a task, for the minimum time required.

**Implementation patterns:**
- Service accounts should have no more permissions than the application requires.
- Human access should be role-based with periodic access reviews.
- Break-glass accounts should be time-boxed and require approval.

**Reference:** NIST SP 800-53 Rev. 5, AC-6 Least Privilege  
URL: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final

### 2.2 Role-Based Access Control (RBAC)

**Principle:** Access decisions based on roles assigned to users/services.

**Implementation patterns:**
- Define roles with specific permissions (e.g., `reader`, `writer`, `admin`).
- Assign principals to roles, not directly to permissions.
- Use role hierarchy for inheritance where appropriate.
- Enforce separation of duties for high-risk operations.

**Reference:** NIST SP 800-162, Guide to Attribute-Based Access Control (ABAC)  
URL: https://csrc.nist.gov/publications/detail/sp/800-162/final

### 2.3 Attribute-Based Access Control (ABAC)

**Principle:** Access decisions based on attributes of subject, resource, action, and environment.

**Implementation patterns:**
- Subject attributes: role, clearance, department, location, device trust level.
- Resource attributes: classification, owner, sensitivity, data class, retention class.
- Action attributes: read, write, delete, export, decrypt, administer.
- Environmental attributes: time of day, safe-mode state, network location, threat level.
- Policy rules: "Allow if subject.role == 'guinevere_core' AND resource.classification <= 'Restricted' AND environment.safe_mode == false"

**Reference:** NIST SP 800-162, ABAC Overview  
URL: https://csrc.nist.gov/publications/detail/sp/800-162/final

### 2.4 Service Accounts

**Principle:** Dedicated identities for services, not shared credentials.

**Implementation patterns:**
- Unique credential per service identity.
- No human password reuse for service accounts.
- Automatic credential rotation where possible.
- Audit log for every service account authentication.
- Disable/revoke path for compromised service accounts.

**Reference:** CIS Controls v8, IAM-4: Use Unique Passwords  
URL: https://www.cisecurity.org/cis-controls/v8/0101

### 2.5 Short-Lived Grants / Just-In-Time Access

**Principle:** Grant elevated access only for the duration needed, then automatically revoke.

**Implementation patterns:**
- Time-boxed credentials with automatic expiry.
- Justification required before grant.
- Approval workflow for elevated access.
- Automatic revocation after expiry or task completion.
- Audit log of grant, use, and revocation.

**Reference:** AWS IAM Best Practices, Grant Least Privilege  
URL: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html

---

## 3. PostgreSQL Grants and Row-Level Security (RLS)

### 3.1 PostgreSQL GRANT Pattern

**Principle:** Grant specific privileges on specific schemas/tables to specific roles.

**Implementation patterns:**
- Create dedicated database roles per service/principal.
- Grant only required actions: SELECT, INSERT, UPDATE, DELETE, REFERENCES, TRIGGER.
- Revoke default public access.
- Use `REVOKE ALL ON SCHEMA public FROM PUBLIC;` as baseline.
- Grant schema-level or table-level privileges, not database-level superuser.

**Example pattern:**
```sql
-- Revoke broad access
REVOKE ALL ON SCHEMA memory FROM guinevere_core;
REVOKE ALL ON ALL TABLES IN SCHEMA memory FROM guinevere_core;

-- Grant specific access
GRANT SELECT, INSERT, UPDATE ON memory.episodes TO guinevere_core;
GRANT SELECT ON memory.semantic_facts TO guinevere_core;
-- Deny intimate/sensitive tables
REVOKE ALL ON persona.inner_journal FROM guinevere_core;
REVOKE ALL ON memory.samm_profile FROM guinevere_core;
```

**Reference:** PostgreSQL Documentation, GRANT  
URL: https://www.postgresql.org/docs/current/sql-grant.html

### 3.2 Row-Level Security (RLS)

**Principle:** Filter rows at the database level based on the current user's attributes.

**Implementation patterns:**
- Enable RLS on sensitive tables: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
- Create policies that filter rows based on `current_user` or session variables.
- Use `current_setting('app.current_principal')` to pass principal identity from application.
- Policies can restrict by row attributes (e.g., `classification`, `owner`, `sensitivity`).

**Example pattern:**
```sql
-- Enable RLS
ALTER TABLE memory.samm_profile ENABLE ROW LEVEL SECURITY;

-- Policy: allow access only to non-intimate rows for normal principals
CREATE POLICY samm_profile_access ON memory.samm_profile
  FOR SELECT TO guinevere_core
  USING (category != 'intimate' OR current_setting('app.break_glass') = 'true');

-- Policy: allow Samm full access
CREATE POLICY samm_full_access ON memory.samm_profile
  FOR ALL TO samm
  USING (true);
```

**Reference:** PostgreSQL Documentation, Row Security Policies  
URL: https://www.postgresql.org/docs/current/ddl-rowsecurity.html

---

## 4. Redis ACL and Key Prefix Policies

### 4.1 Redis ACL Pattern

**Principle:** Define per-user access rules for commands, keys, and categories.

**Implementation patterns:**
- Create ACL users per principal/service.
- Restrict commands per user (e.g., read-only users get GET, INFO; writers get SET, DEL).
- Restrict key patterns per user (e.g., `surv:*` for surveillance, `task:*` for tasks).
- Use `RESETALL` or per-user `ACL DEL` for revocation.
- Enable ACL logging for audit.

**Example pattern:**
```redis
# Create surveillance ingestor user
ACL SETUSER surveillance-ingestor on >password ~surv:* +SET +EXPIRE -GET -DEL -FLUSHALL

# Create readonly auditor user
ACL SETUSER readonly-auditor on >password ~* +GET +INFO -SET -DEL -FLUSHALL

# Create guinevere_core user with multi-DB access
ACL SETUSER guinevere_core on >password ~task:* ~llm:* ~session:* +GET +SET +DEL +EXPIRE -FLUSHALL
```

**Reference:** Redis Documentation, Access Control List  
URL: https://redis.io/docs/management/security/acl/

### 4.2 Redis Key Prefix Classification

**Principle:** Encode data class in key prefix for policy enforcement.

**Implementation patterns:**
- Prefix keys with classification: `crit:inner_journal:...`, `rest:surv:...`, `conf:session:...`
- Use key naming conventions to enforce TTL and access rules.
- Scan/keys commands should be restricted to prevent pattern enumeration attacks.

**Reference:** Redis Security Best Practices  
URL: https://redis.io/docs/management/security/

---

## 5. FastAPI Auth Dependencies

### 5.1 JWT + API Key Pattern

**Principle:** Validate identity and scope at the endpoint level.

**Implementation patterns:**
- Use FastAPI `Depends` for auth checks.
- JWT contains subject (principal), roles, and expiry.
- API keys for service-to-service calls with scoped permissions.
- Tailscale IP whitelist as network-layer enforcement.
- Safe-mode check as dependency that returns minimal responses when active.

**Example pattern:**
```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    principal = await validate_jwt(token)
    # Check Tailscale IP
    if not is_tailscale_ip(request.client.host):
        raise HTTPException(status_code=403, detail="Tailscale only")
    # Check safe mode
    if safe_mode_active() and principal.data_class_scope < "Restricted":
        raise HTTPException(status_code=403, detail="Safe mode restriction")
    return principal
```

**Reference:** FastAPI Security Documentation  
URL: https://fastapi.tiangolo.com/tutorial/security/

### 5.2 Safe-Mode as Auth Dependency

**Principle:** Safe-mode state modifies authorization decisions dynamically.

**Implementation patterns:**
- Safe-mode dependency that wraps or modifies endpoint behavior.
- Endpoints that access sensitive data check safe-mode state before returning data.
- Safe-mode can downgrade responses to summaries or empty results.

**Reference:** OAuth 2.0 Threat Model and Security Considerations (RFC 6819)  
URL: https://datatracker.ietf.org/doc/html/rfc6819

---

## 6. Tailscale ACL / Tags

### 6.1 ACL Policy Structure

**Principle:** Device-level access control based on tags and auto-approvers.

**Implementation patterns:**
- Define device tags: `tag:admin`, `tag:service`, `tag:service:guinevere`.
- Auto-approvers: specific devices can auto-approve new devices with specific tags.
- ACL rules filter traffic by source tag, destination tag, and port.
- No public funnel or HTTPS routes for internal services.

**Example ACL structure:**
```json
{
  "groups": {},
  "tagOwners": {
    "tag:admin": ["Samm"],
    "tag:service": [],
    "tag:service:guinevere": ["tag:service"]
  },
  "autoApprovers": {
    "groups": {},
    "tagOwners": ["tag:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:admin"],
      "dst": ["tag:service:guinevere:8000", "tag:service:guinevere:8001"]
    },
    {
      "action": "accept",
      "src": ["tag:service:guinevere"],
      "dst": ["tag:service:guinevere:*"]
    }
  ]
}
```

**Reference:** Tailscale ACL Documentation  
URL: https://tailscale.com/kb/1018/acls/

### 6.2 Device Authentication and Expiry

**Principle:** Auth keys must have appropriate expiry settings for headless nodes.

**Implementation patterns:**
- VPS/auth keys: disable expiry or set to >180 days.
- Human devices: standard 180-day expiry with renewal reminders.
- Recovery auth key: stored offline; used for lockout recovery.
- Renewal procedure documented and tested.

**Reference:** Tailscale Key Management  
URL: https://tailscale.com/kb/1152/device-keys/

---

## 7. Object Storage IAM Prefix Policies

### 7.1 S3/R2 Prefix Isolation

**Principle:** Scope credentials to specific buckets and prefixes.

**Implementation patterns:**
- Create IAM policies per principal that allow only specific bucket/prefix combinations.
- Deny `ListBucket` and `GetObject` outside allowed prefixes.
- Use `s3:prefix` and `s3:delimiter` conditions in IAM policies.
- Enforce encryption (SSE-S3 or SSE-KMS) for Restricted/Critical objects.

**Example pattern:**
```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::guinevere-raw/surveillance/screenshots/*",
      "Condition": {
        "StringEquals": {"s3:x-amz-acl": "private"}
      }
    },
    {
      "Effect": "Deny",
      "Action": ["s3:*"],
      "Resource": "*",
      "Condition": {
        "StringNotLike": {"s3:prefix": ["surveillance/screenshots/*"]}
      }
    }
  ]
}
```

**Reference:** AWS S3 Bucket Policy Documentation  
URL: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html

### 7.2 Lifecycle and Encryption

**Principle:** Automate retention and enforce encryption.

**Implementation patterns:**
- Lifecycle rules for transition to cold storage and deletion.
- Server-side encryption (SSE) for all objects.
- Object metadata for classification, retention, and key version.

**Reference:** AWS S3 Lifecycle Configuration  
URL: https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-configuration-examples.html

---

## 8. Audit Logging Standards

### 8.1 Mandatory Audit Events

**Principle:** Log all access to Restricted/Critical data and all administrative actions.

**Implementation patterns:**
- Log format: JSON structured with timestamp, actor, action, target, result, classification.
- Audit events for: every decrypt, every export, every break-glass, every rotation, every admin action.
- Tamper-evident logs: append-only, signed, or WORM storage.
- Separate audit log from application log to prevent tampering.

**Reference:** NIST SP 800-92, Guide to Computer Security Log Management  
URL: https://csrc.nist.gov/publications/detail/sp/800-92/final

### 8.2 Audit Retention

**Principle:** Retain audit logs longer than the data they describe.

**Implementation patterns:**
- Audit logs for Restricted/Critical data: retain for 1+ years or regulatory requirement.
- Security incidents: retain indefinitely or as required by law.
- Log integrity checks: periodic hash verification.

**Reference:** CIS Controls v8, SI-3: Audit Logging  
URL: https://www.cisecurity.org/cis-controls/v8/0801

---

## 9. Policy-as-Code

### 9.1 Infrastructure as Code (IaC) for Access Control

**Principle:** Define access control policies in code, versioned, reviewed, and tested.

**Implementation patterns:**
- Store ACL policies, IAM policies, PostgreSQL grants, Redis ACL configs in version control.
- Use Terraform, Pulumi, or Ansible for infrastructure policy enforcement.
- Test policies in staging before production.
- CI/CD pipeline validates policy syntax and runs policy tests.

**Reference:** OWASP ASVS, V4 Access Control  
URL: https://owasp.org/www-project-application-security-verification-standard/

### 9.2 Open Policy Agent (OPA)

**Principle:** Policy decision engine separate from application code.

**Implementation patterns:**
- Define Rego policies for ABAC decisions.
- Query OPA from application for authorization decisions.
- Policy bundles versioned and audited.
- Policy testing with OPA test framework.

**Reference:** Open Policy Agent Documentation  
URL: https://www.openpolicyagent.org/docs/latest/

---

## 10. AI / Sub-Agent Context Gating

### 10.1 Context Minimization for AI Agents

**Principle:** Provide sub-agents with the minimum context necessary for the task.

**Implementation patterns:**
- Redact sensitive data from prompts before sending to sub-agents.
- Use summaries instead of raw data where possible.
- Define data class boundaries for sub-agent context.
- Log what context was provided to each sub-agent for audit.

**Reference:** OWASP Top 10 for LLMs, LLM01: Prompt Injection  
URL: https://owasp.org/www-project-top-10-for-large-language-model-applications/

### 10.2 Sub-Agent Trust Levels

**Principle:** Classify sub-agents by trust level and restrict context accordingly.

**Implementation patterns:**
- Read-only sub-agents: no write access, no secrets, no Critical data.
- Write-capable sub-agents: limited to designated paths; no cross-domain access.
- Restricted sub-agents: explicit justification required for sensitive data access.
- Parent verification: parent must read and verify sub-agent outputs before accepting.

**Reference:** AI Agent Security Best Practices  
URL: https://owasp.org/www-project-ai-security-guide/

---

## 11. Break-Glass Patterns

### 11.1 Emergency Access Pattern

**Principle:** Pre-defined emergency access path with controls.

**Implementation patterns:**
- Dedicated break-glass accounts separate from normal admin accounts.
- Time-boxed access with automatic revocation.
- Multi-person approval where feasible (Samm approval for Guinevere).
- Post-use credential rotation mandatory.
- Break-glass events logged and reviewed.

**Reference:** NIST SP 800-53 Rev. 5, IA-2 Identification and Authentication  
URL: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final

### 11.2 Just-In-Time (JIT) Privilege Elevation

**Principle:** Elevate privileges only when needed, then automatically revoke.

**Implementation patterns:**
- Request → Approval → Grant → Use → Revoke workflow.
- Time-limited grants with automatic expiry.
- Audit trail of entire JIT lifecycle.

**Reference:** Azure AD Privileged Identity Management  
URL: https://learn.microsoft.com/en-us/azure/active-directory/privileged-identity-management/

---

## 12. Secret Management Patterns

### 12.1 SOPS + Age Pattern

**Principle:** Encrypt secrets at rest; decrypt only at runtime.

**Implementation patterns:**
- SOPS encrypts secrets files with age public key.
- Private key stored with strict permissions (0600, owner-only).
- Decrypt to tmpfs or runtime-only path.
- Auto-cleanup after service load.
- No plaintext secrets in repo, logs, or backups.

**Reference:** Mozilla SOPS Documentation  
URL: https://getsops.io/

### 12.2 Secret Rotation Pattern

**Principle:** Rotate secrets on a schedule and immediately on compromise.

**Implementation patterns:**
- Quarterly rotation for high-risk API tokens.
- Annual rotation for low-risk service credentials.
- Immediate rotation on suspected compromise.
- Zero-downtime rotation: write-new/read-old pattern.
- Rotation evidence in markdown.

**Reference:** AWS Secrets Manager Rotation  
URL: https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html

---

## 13. Checklist: What the Final RBAC/ABAC Matrix Must Contain

- [ ] Authority order with explicit conflict resolution.
- [ ] All 13+ principals defined with ownership, scope, and trust level.
- [ ] PostgreSQL PgBouncer user mapping: exact schemas, tables, actions per principal.
- [ ] PostgreSQL RLS policies for sensitive tables.
- [ ] Redis ACL users and key-prefix rules per principal and data class.
- [ ] Object storage IAM prefix policies per principal and data class.
- [ ] FastAPI endpoint authorization mapping with safe-mode behavior.
- [ ] Tailscale ACL/tag policy: device tags, auto-approvers, subnet rules.
- [ ] Break-glass constraints: SEV0/SEV1 only; max 4h; Samm approval; post-use rotation.
- [ ] Sub-agent access matrix with trust levels and context gating.
- [ ] Audit log requirements: mandatory events per data class and action.
- [ ] Secret access matrix: which principals may access which secrets; rotation schedule.
- [ ] Backup and export access: who may create, read, delete; encryption requirements.
- [ ] Incident response hooks: SEV0-SEV4 triggers and containment actions.
- [ ] All controls use `must` (zero `should`).
- [ ] Language: Indonesian + technical English.
- [ ] Normative child of ADR-019, ADR-018, ADR-024, ADR-012 plus DataGovernancePolicy, EncryptionKeyMgmtStandard, PersonaSafetyPolicy.
