# Secrets Rotation External References

**Report ID:** 2026-05-30-secrets-rotation-external-references  
**Date:** 2026-05-30  
**Scope:** Practical rotation best practices, concrete references, and implementable patterns for Project Guinevere secret types.  
**Status:** Complete  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Primary standard requiring rotation controls, audit evidence, and break-glass procedures. |
| `adr/ADR-015-secrets-management-strategy.md` | Parent ADR accepting SOPS + age with runtime injection. |
| `adr/ADR-008-memory-encryption-key-management.md` | Parent ADR for key hierarchy, rotation, and emergency revoke. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification tiers driving rotation cadences and audit levels. |

---

## 1. SOPS + age Rotation Best Practices

### 1.1 SOPS Overview and References

**Primary References:**
- **Mozilla SOPS Documentation:** https://getsops.io/docs/
- **SOPS GitHub Repository:** https://github.com/getsops/sops
- **age Encryption Tool:** https://age-encryption.org/

### 1.2 age Key Rotation Procedure

**Implementable Pattern:**

```bash
# 1. Generate new age key pair
age-keygen -o /tmp/new-age-key.txt

# 2. Extract public key
PUBLIC_KEY=$(age-keygen -y /tmp/new-age-key.txt)

# 3. Re-encrypt SOPS file with new public key
sops --age "$PUBLIC_KEY" -i /home/guinevere/config/.env.sops.yaml

# 4. Verify decryption works with new private key
SOPS_AGE_KEY_FILE=/tmp/new-age-key.txt sops -d /home/guinevere/config/.env.sops.yaml

# 5. Replace old age key
mv /tmp/new-age-key.txt /home/guinevere/.age/key.txt
chmod 600 /home/guinevere/.age/key.txt

# 6. Verify with production decryption
sops -d /home/guinevere/config/.env.sops.yaml > /dev/null

# 7. Securely delete old key if needed
shred -u /home/guinevere/.age/key.txt.bak
```

**Best Practices:**
- Rotate age recipient keys annually or immediately on device loss, suspected compromise, or custody change.
- Maintain backup of old age key during transition window; delete only after verification.
- Test re-encryption on a copy before applying to production SOPS files.
- Store age private key on encrypted filesystem with strict permissions (0600).
- Use separate age recipients for staging and production environments.

### 1.3 SOPS File Rotation

**Implementable Pattern:**

```bash
# 1. Decrypt current secrets
sops -d /home/guinevere/config/.env.sops.yaml > /tmp/.env.current

# 2. Edit secrets as needed
vim /tmp/.env.current

# 3. Re-encrypt
sops -e /home/guinevere/config/.env.sops.yaml < /tmp/.env.current

# 4. Verify
sops -d /home/guinevere/config/.env.sops.yaml | diff - /tmp/.env.current

# 5. Clean up
shred -u /tmp/.env.current
```

**Best Practices:**
- Never commit plaintext `.env` files to version control.
- Use `sops --in-place` for atomic updates.
- Validate SOPS file integrity after every edit with `sops -d`.
- Rotate all secrets within a SOPS file together when rotating the age key.

### 1.4 Runtime Decryption Security

**Implementable Pattern (systemd service):**

```ini
[Service]
Environment="SOPS_AGE_KEY_FILE=/home/guinevere/.age/key.txt"
ExecStartPre=/bin/bash -c 'sops -d /home/guinevere/config/.env.sops.yaml > /tmp/.env && chmod 600 /tmp/.env'
ExecStart=/usr/bin/python3 /home/guinevere/core/main.py
ExecStopPost=/bin/sh -c 'shred -u /tmp/.env || true'
```

**Best Practices:**
- Decrypt to tmpfs or `/tmp` with 0600 permissions.
- Auto-clean decrypted files after service load.
- Never back up decrypted environment files.
- Fail closed if decryption fails (startup failure).

---

## 2. GitHub PAT Rotation Best Practices

### 2.1 References

- **GitHub PAT Documentation:** https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
- **GitHub Token Permissions:** https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#selecting-scopes-for-a-personal-access-token
- **GitHub Token Expiration:** https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/rotating-your-personal-access-token

### 2.2 Fine-Grained PAT Rotation

**Implementable Pattern:**

```bash
# 1. Create new fine-grained PAT with minimal required scopes
# Repository access: Contents, Metadata, Pull requests, Workflows
# Organization access (if applicable): Members, Projects

# 2. Test new PAT before revoking old
curl -H "Authorization: token NEW_PAT" \
  https://api.github.com/user

# 3. Update SOPS with new PAT
sops -i -e /home/guinevere/config/.env.sops.yaml \
  -r '{"github_pat": "NEW_PAT"}'

# 4. Deploy and verify
systemctl restart guinevere-core

# 5. Verify MCP git operations
# (MCP github tool test)

# 6. Revoke old PAT via GitHub web UI or API
curl -X DELETE \
  -H "Authorization: token OLD_PAT" \
  https://api.github.com/applications/CLIENT_ID/token

# 7. Update rotation_due_at in inventory
```

**Best Practices:**
- Use fine-grained PATs instead of classic PATs for better scope control.
- Set expiration dates (maximum 1 year for classic, configurable for fine-grained).
- Use repository-scoped tokens, not account-scoped.
- Rotate quarterly or on repository exposure, scope change, or suspicious GitHub event.
- Audit PAT usage via GitHub audit log: https://github.com/organizations/YOUR_ORG/settings/audit-log

### 2.3 GitHub Webhook Secret Rotation

**Implementable Pattern:**

```bash
# 1. Generate new webhook secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Update SOPS
sops -i -e /home/guinevere/config/.env.sops.yaml \
  -r '{"github_webhook_secret": "NEW_SECRET"}'

# 3. Update GitHub webhook configuration
curl -X PATCH \
  -H "Authorization: token GITHUB_PAT" \
  https://api.github.com/repos/OWNER/REPO/hooks/HOOK_ID \
  -d '{"config": {"secret": "NEW_SECRET"}}'

# 4. Verify webhook payload signature
# (Implementation must validate X-Hub-Signature-256)
```

---

## 3. Discord Token Rotation Best Practices

### 3.1 References

- **Discord Bot Documentation:** https://discord.com/developers/docs
- **Discord Bot Token Reset:** https://discord.com/developers/docs/topics/oauth2#bot-application-security

### 3.2 Discord Bot Token Rotation

**Implementable Pattern:**

```bash
# 1. Reset bot token in Discord Developer Portal
# (Manual step: https://discord.com/developers/applications)

# 2. Update SOPS with new token
sops -i -e /home/guinevere/config/.env.sops.yaml \
  -r '{"discord_token": "NEW_TOKEN"}'

# 3. Restart service
systemctl restart guinevere-core

# 4. Verify connection
# (Discord gateway connection test; slash command response)

# 5. Monitor reconnection
# Discord handles automatic reconnection with new token
```

**Best Practices:**
- Rotate quarterly or on bot compromise, unexpected gateway behavior, or leaked logs.
- Monitor Discord gateway events for unauthorized connection attempts.
- Use Discord bot token in SOPS only; never log or expose in code.
- Implement gateway intent minimization (subscribe only to required intents).

---

## 4. OAuth Refresh Token Rotation Best Practices

### 4.1 References

- **OAuth 2.0 RFC:** https://datatracker.ietf.org/doc/html/rfc6749
- **OAuth 2.0 Token Revocation:** https://datatracker.ietf.org/doc/html/rfc7009
- **Google OAuth Token Management:** https://developers.google.com/identity/protocols/oauth2

### 4.2 OAuth Refresh Token Rotation

**Implementable Pattern (Google/Gmail OAuth):**

```python
# 1. Detect token expiry or revocation
# 2. Initiate re-auth flow
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secrets.json',
    scopes=['https://www.googleapis.com/auth/gmail.modify']
)
creds = flow.run_local_server(port=0)

# 3. Store new refresh token in SOPS
# (Encrypt with age before storing)

# 4. Verify token works
service = build('gmail', 'v1', credentials=creds)
profile = service.users().getProfile(userId='me').execute()

# 5. Revoke old token if compromised
# https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke
requests.post('https://oauth2.googleapis.com/revoke?token=OLD_REFRESH_TOKEN')
```

**Best Practices:**
- Rotate OAuth refresh tokens quarterly or on token exposure.
- Store refresh tokens in SOPS; never in code or logs.
- Implement token refresh logic with automatic retry on expiry.
- Monitor for unusual API access patterns as compromise indicator.
- Revoke tokens via provider's revocation endpoint when compromised.

---

## 5. PostgreSQL/PgBouncer Credential Rotation Best Practices

### 5.1 References

- **PostgreSQL ALTER ROLE:** https://www.postgresql.org/docs/current/sql-alterrole.html
- **PgBouncer Documentation:** https://www.pgbouncer.org/config.html
- **PgBouncer Auth File:** https://www.pgbouncer.org/auth.html

### 5.2 PostgreSQL Password Rotation

**Implementable Pattern:**

```sql
-- 1. Generate new password (do this outside SQL for security)
-- 2. Update password for service user
ALTER ROLE guinevere_core WITH PASSWORD 'new_secure_password';

-- 3. Verify new password works
-- (Connection test from application)

-- 4. Update SOPS with new password
-- (sops -i -e ...)

-- 5. Reload PgBouncer
-- pgbouncer -R (reload without downtime)
-- OR: systemctl restart pgbouncer

-- 6. Verify connections
SHOW POOLS;
```

**Best Practices:**
- Use PgBouncer transaction-pooling mode to minimize connection disruption.
- Rotate per-service PgBouncer user passwords quarterly.
- Never rotate the superuser password from within the application.
- Use `pg_authid` catalog for audit of password changes.
- Test connection before updating SOPS to avoid lockout.
- Maintain a break-glass superuser credential for emergency rotation.

### 5.3 PgBouncer Auth File Rotation

**Implementable Pattern:**

```bash
# 1. Generate new auth file with hashed passwords
# PostgreSQL md5 hash format
psql -c "SELECT rolname, rolpassword FROM pg_authid WHERE rolcanlogin = true;" \
  -t -A -F':' > /tmp/userlist.txt

# 2. Update PgBouncer auth_file
mv /tmp/userlist.txt /etc/pgbouncer/userlist.txt
chmod 600 /etc/pgbouncer/userlist.txt

# 3. Reload PgBouncer
pgbouncer -R /etc/pgbouncer/pgbouncer.ini

# 4. Verify pools
psql -p 6432 -U guinevere_core -c "SELECT 1;"
```

---

## 6. Redis Authentication Rotation Best Practices

### 6.1 References

- **Redis AUTH Command:** https://redis.io/commands/auth/
- **Redis ACL:** https://redis.io/docs/management/security/acl/
- **Redis Security:** https://redis.io/docs/management/security/

### 6.2 Redis Password Rotation

**Implementable Pattern:**

```bash
# 1. Generate new strong password
NEW_PASS=$(openssl rand -base64 32)

# 2. Set new password in Redis
redis-cli CONFIG SET requirepass "$NEW_PASS"

# 3. Verify new password
redis-cli -a "$NEW_PASS" PING

# 4. Update SOPS with new password
sops -i -e /home/guinevere/config/.env.sops.yaml \
  -r '{"redis_password": "NEW_PASS"}'

# 5. Restart dependent services with new password
systemctl restart guinevere-*

# 6. Verify all services connect
redis-cli -a "$NEW_PASS" ACL LOG
```

**Best Practices:**
- Use Redis ACL for per-user permissions instead of single shared password.
- Rotate Redis password quarterly or on unauthorized access.
- Use TLS for Redis connections in addition to AUTH.
- Monitor Redis slow log for suspicious commands.
- Consider Redis ACL users with specific command restrictions.

---

## 7. R2/S3 Access Key Rotation Best Practices

### 7.1 References

- **Cloudflare R2 API Tokens:** https://developers.cloudflare.com/r2/platform/s3-compatible-api/
- **AWS S3 Access Key Rotation:** https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey
- **S3 Best Practices:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html

### 7.2 R2/S3 Access Key Rotation

**Implementable Pattern:**

```bash
# 1. Create new API token in Cloudflare dashboard
# (or idcloudhost equivalent)

# 2. Test new credentials
aws s3 ls \
  --endpoint-url https://<account_id>.r2.cloudflarestorage.com \
  --profile new-profile \
  s3://bucket-name/

# 3. Update SOPS with new credentials
sops -i -e /home/guinevere/config/.env.sops.yaml \
  -r '{"r2_access_key": "NEW_KEY", "r2_secret_key": "NEW_SECRET"}'

# 4. Deploy and verify backup job
systemctl restart guinevere-backup

# 5. Verify backup succeeds
# (Check backup job logs)

# 6. Revoke old API token from Cloudflare dashboard

# 7. Delete old credentials from all non-authoritative stores
```

**Best Practices:**
- Use per-bucket or per-prefix scoped credentials to limit blast radius.
- Enable object-level encryption in addition to bucket-level.
- Rotate R2/S3 credentials quarterly.
- Monitor Cloudflare/idcloudhost audit logs for unusual access.
- Use IAM-style policies to restrict token permissions.
- Never commit credentials to version control.

---

## 8. General API Key Rotation Best Practices

### 8.1 References

- **OWASP API Security:** https://owasp.org/www-project-api-security/
- **NIST SP 800-57 (Key Management):** https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final
- **CIS Controls (v8):** https://www.cisecurity.org/cis-controls/v8

### 8.2 API Key Rotation Pattern

**Implementable Pattern:**

```python
import httpx
import sops

async def rotate_api_key(secret_id: str, provider: str):
    # 1. Generate new key via provider API
    new_key = await provider.generate_api_key()
    
    # 2. Store new key in SOPS
    sops.update_secret(secret_id, new_key)
    
    # 3. Deploy new key
    await deploy_new_key(secret_id)
    
    # 4. Verify service health
    health = await check_service_health()
    if not health.healthy:
        raise RuntimeError("Service unhealthy after key rotation")
    
    # 5. Revoke old key
    await provider.revoke_api_key(old_key)
    
    # 6. Update inventory
    update_inventory(secret_id, rotated_at=now(), rotation_due_at=next_quarter)
    
    # 7. Write evidence
    write_rotation_evidence(secret_id, new_key_id=new_key.id, status="success")
```

**Best Practices:**
- Rotate high-risk API keys quarterly.
- Use provider-managed key rotation where available (e.g., AWS IAM automatic rotation).
- Implement key rotation as zero-downtime operation with read-old/write-new pattern.
- Monitor for key exposure via secret scanners and audit logs.
- Maintain inventory of all API keys with rotation_due_at dates.

---

## 9. Fernet and MultiFernet Rotation Best Practices

### 9.1 References

- **Python Fernet Documentation:** https://cryptography.io/en/latest/fernet/
- **Fernet Key Rotation:** https://cryptography.io/en/latest/fernet/#rotating-keys

### 9.2 Fernet Key Ring Rotation

**Implementable Pattern:**

```python
from cryptography.fernet import Fernet, MultiFernet

# 1. Generate new Fernet key
new_key = Fernet.generate_key()

# 2. Add new key to ring (new primary)
key_ring = [new_key] + existing_key_ring
fernet = MultiFernet(key_ring)

# 3. Re-encrypt existing data with new primary
for record in records_to_rotate:
    if record.is_fernet_encrypted():
        # Decrypt with old key (MultiFernet tries all keys)
        plaintext = fernet.decrypt(record.ciphertext)
        # Re-encrypt with new primary
        record.ciphertext = fernet.encrypt(plaintext)
        record.key_id = new_key_id
        record.key_version += 1

# 4. Verify re-encryption
for record in records_to_rotate:
    assert fernet.decrypt(record.ciphertext) is not None

# 5. Retire old key after verification window
key_ring = [new_key, secondary_key]  # Old primary becomes secondary
fernet = MultiFernet(key_ring)
```

**Best Practices:**
- Use `MultiFernet` for staged key rotation (new primary, read old, re-encrypt, verify, retire old).
- Never use a single global Fernet key for multiple Critical domains.
- Keep key rings domain-specific and versioned.
- Store Fernet ciphertext with external metadata: domain, key_id, key_version, classification, created_at, rotated_at.
- Treat Fernet as compatibility/transitional only; migrate to AES-256-GCM envelope encryption for new Critical domains.

---

## 10. Envelope Encryption and KEK Rotation Best Practices

### 10.1 References

- **AWS Envelope Encryption:** https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#envelop-encryption
- **Google Cloud KMS Envelope Encryption:** https://cloud.google.com/kms/docs/envelope-encryption
- **NIST SP 800-57 Part 1:** https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final

### 10.2 Envelope Encryption Rotation

**Implementable Pattern:**

```python
# 1. Generate new domain KEK
new_kek = crypto_service.generate_kek(domain="secrets", version=new_version)

# 2. Re-wrap domain DEKs with new KEK
for dek in domain_deks:
    dek.wrapped_key = crypto_service.wrap_dek(
        dek=dek.plaintext_dek,
        kek=new_kek,
        domain="secrets"
    )
    dek.wrapped_by = new_kek.key_id
    dek.key_version = new_version

# 3. Verify unwrap with new KEK
for dek in domain_deks:
    unwrapped = crypto_service.unwrap_dek(
        wrapped_key=dek.wrapped_key,
        kek=new_kek
    )
    assert unwrapped == dek.plaintext_dek

# 4. Update KEK status
old_kek.status = "read_only"
new_kek.status = "active"

# 5. Verify data decrypts with new KEK
sample_records = get_sample_records(domain="secrets", limit=100)
for record in sample_records:
    dek = crypto_service.get_dek(record.dek_id)
    plaintext = crypto_service.decrypt_record(
        ciphertext=record.ciphertext,
        dek=unwrapped_dek,
        aad=record.aad
    )
    assert plaintext is not None

# 6. Retire old KEK after verification window
old_kek.status = "retired"
```

**Best Practices:**
- Rotate domain KEKs quarterly for Critical domains; annually for others.
- Use dual-key read during rotation: old key `read_only`, new key `active`.
- Verify sample decrypts before retiring old key.
- Store wrapped DEKs with key metadata: key_id, key_version, algorithm, rotated_at.
- Separate backup KEK scope from runtime data KEKs.

---

## 11. Emergency Compromise Response Best Practices

### 11.1 References

- **NIST SP 800-61 Rev. 3 (Incident Handling):** https://csrc.nist.gov/publications/detail/sp/800-61/rev-3/final
- **SANS Incident Handler's Handbook:** https://www.sans.org/white-papers/33901/
- **OWASP Incident Response:** https://owasp.org/www-community/Incident_Response

### 11.2 SEV0-SEV4 Response Matrix

From Encryption Standard Section 18.1:

| Severity | Crypto/Data Trigger | Required Response | Time Goal |
|---|---|---|---|
| SEV0 | Active Critical key compromise, nonce reuse, public Critical secret exposure, active exfiltration. | Immediate containment, revoke/disable, pause affected flows, notify Samm, incident report, re-encrypt/rewrap. | Minutes |
| SEV1 | Restricted/Critical unauthorized decrypt, backup key exposure, GitHub PAT leak, raw surveillance export mistake. | Contain, rotate, assess impact, preserve evidence, postmortem. | Hours |
| SEV2 | Confidential secret exposure, failed redaction in internal report, suspicious decrypt spike. | Rotate affected secret, scan artifacts, add regression test. | Days |
| SEV3 | Internal key metadata inconsistency, overdue rotation without exposure. | Correct inventory, complete rotation, document. | Days |
| SEV4 | Cosmetic metadata/reporting issue without exposure. | Fix during next maintenance window. | Weeks |

### 11.3 Emergency Response Procedure

**Implementable Pattern:**

```markdown
## SEV0-SEV2 Incident Response Checklist

1. [ ] Declare severity (SEV0-SEV4).
2. [ ] Identify compromised key/secret and scope.
3. [ ] Isolate affected service (systemctl stop / docker stop).
4. [ ] Revoke/disable affected key/secret:
     - Provider dashboard revocation
     - SOPS key status update to `compromised`
     - Runtime key status update to `compromised`
5. [ ] Freeze affected exports and non-essential decrypts.
6. [ ] Preserve minimal evidence with hashes:
     - Export/ciphertext hashes
     - Log excerpts (redacted)
     - Timeline of access
7. [ ] Generate replacement key/secret.
8. [ ] Rewrap/re-encrypt affected data.
9. [ ] Verify integrity:
     - Record counts
     - Sample decrypts
     - Ciphertext hash validation
     - Application health checks
10. [ ] Update inventory:
      - key_status: compromised → retired
      - rotated_at: timestamp
      - evidence_path: incident report path
11. [ ] Add regression test.
12. [ ] Write postmortem with:
      - Timeline
      - Impact
      - Root cause
      - Data classes affected
      - Containment actions
      - Recovery actions
      - Preventive actions
      - Owner
      - Due date
13. [ ] Notify Samm.
```

**Best Practices:**
- Maintain offline break-glass credentials for emergency access.
- Test incident response procedures quarterly via tabletop exercises.
- Preserve evidence without storing plaintext secrets.
- Use cryptographic hashes (SHA-256) for evidence integrity.
- Rotate dependent credentials if blast radius is uncertain.

---

## 12. Audit Evidence Best Practices

### 12.1 References

- **NIST SP 800-92 (Log Management):** https://csrc.nist.gov/publications/detail/sp/800-92/final
- **OWASP Logging Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- **CIS Audit Logging:** https://www.cisecurity.org/controls/cis-controls-8/

### 12.2 Key Usage Audit Log Format

**Implementable Pattern:**

```json
{
  "timestamp": "2026-05-30T14:32:01Z",
  "event_id": "audit-key-rotation-001",
  "event_type": "key_rotation",
  "actor": "guinevere-runtime",
  "service": "guinevere-core",
  "domain": "secrets",
  "classification": "Critical",
  "key_id": "gkv1-kek-secrets-v1",
  "key_version_old": 1,
  "key_version_new": 2,
  "operation": "rotate",
  "result": "success",
  "records_affected": 1523,
  "records_verified": 100,
  "ciphertext_hash_before": "sha256:abc123...",
  "ciphertext_hash_after": "sha256:def456...",
  "sample_decrypt_result": "success",
  "application_health": "healthy",
  "evidence_path": "evidence/rotations/2026-05-30-kek-secrets-v1-to-v2.md",
  "correlation_id": "rot-2026-05-30-001",
  "samm_notified": true
}
```

**Best Practices:**
- Log every Restricted/Critical key operation with timestamp, actor, operation, domain, classification, key_id, key_version, result, and evidence path.
- Never log plaintext key material, DEKs, or secrets.
- Use structured JSON logging for machine-readable audit trails.
- Store audit logs in tamper-evident storage (append-only).
- Retain audit logs for minimum 1 year for Critical operations.
- Include correlation IDs linking rotation events to incident reports.

### 12.3 Rotation Evidence Template

**Implementable Pattern:**

```markdown
# Key Rotation Evidence: [KEY_ID] v[OLD] → v[NEW]

**Date:** YYYY-MM-DD HH:MM:SS UTC  
**Actor:** [Service/Human]  
**Reason:** [Scheduled / Incident / Break-glass]  
**Classification:** Critical  
**Correlation ID:** [UUID]

## Steps Performed
1. [Step 1]
2. [Step 2]
...

## Verification Results
- Records affected: [N]
- Records verified: [N]
- Sample decrypts: [N]/[N] success
- Application health: [Healthy/Unhealthy]
- Ciphertext hash match: [Yes/No]

## Key Status Transitions
- Old key: active → retired
- New key: created → active

## Inventory Updates
- rotated_at: [timestamp]
- rotation_due_at: [timestamp]
- evidence_path: [this file]

## Regression Tests
- [Test name]: [Pass/Fail]

## Samm Notification
- [Required/Not required]
- [Notification method]
```

---

## 13. Recovery Package Testing Best Practices

### 13.1 References

- **NIST SP 800-34 (Contingency Planning):** https://csrc.nist.gov/publications/detail/sp/800-34/rev-1/final
- **Backup/Restore Best Practices:** https://aws.amazon.com/disaster-recovery/

### 13.2 Recovery Package Testing Procedure

**Implementable Pattern:**

```bash
#!/bin/bash
# recovery_test.sh — Test offline recovery package

set -euo pipefail

echo "=== Recovery Package Test ==="

# 1. Verify recovery package exists and checksum matches
echo "[1] Verifying recovery package integrity..."
sha256sum -c /home/samm/recovery-package/checksum.sha256

# 2. Decrypt recovery package
echo "[2] Decrypting recovery package..."
openssl aes-256-gcm -d \
  -in /home/samm/recovery-package/package.tar.gz.enc \
  -out /tmp/recovery-test.tar.gz \
  -pass file:/home/samm/.recovery-package-pass

# 3. Extract recovery package
echo "[3] Extracting recovery package..."
tar -xzf /tmp/recovery-test.tar.gz -C /tmp/recovery-test

# 4. Verify age key from recovery package
echo "[4] Verifying age key..."
age -d -i /tmp/recovery-test/age-key.txt \
  /tmp/recovery-test/test-file.age > /tmp/recovery-test-decrypted

diff /tmp/recovery-test/test-file.txt /tmp/recovery-test-decrypted

# 5. Verify domain KEK wrapped material
echo "[5] Verifying KEK wrapped material..."
python3 -c "
from crypto_service import unwrap_dek
dek = unwrap_dek(
    wrapped_key_file='/tmp/recovery-test/kek-wrapped-dek.bin',
    kek_file='/tmp/recovery-test/domain-kek.enc'
)
assert dek is not None
print('KEK unwrap: SUCCESS')
"

# 6. Verify SOPS re-encryption capability
echo "[6] Testing SOPS re-encryption with recovery age key..."
SOPS_AGE_KEY_FILE=/tmp/recovery-test/age-key.txt \
  sops -d /home/guinevere/config/.env.sops.yaml > /dev/null

# 7. Verify break-glass credentials
echo "[7] Verifying break-glass credentials..."
# (Test break-glass access procedure)

# 8. Clean up
echo "[8] Cleaning up..."
rm -rf /tmp/recovery-test /tmp/recovery-test.tar.gz /tmp/recovery-test-decrypted

echo "=== Recovery Package Test: SUCCESS ==="
```

**Best Practices:**
- Test recovery package quarterly (lightweight) and annually (full).
- Include age key, domain KEK wrapped material, break-glass credentials, and manifest.
- Store recovery package separately from VPS (Samm-controlled offline storage).
- Document recovery package contents manifest, checksum, creation date, expiry/review date.
- Test recovery procedure without modifying production state.
- Verify recovered key material matches expected fingerprints.

---

## 14. Additional External References

### 14.1 Key Management Standards

| Standard | Title | URL |
|---|---|---|
| NIST SP 800-57 Part 1 | Recommendation for Key Management | https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final |
| NIST SP 800-57 Part 2 | Best Practices for Key Management Organizations | https://csrc.nist.gov/publications/detail/sp/800-57/part-2/ |
| NIST SP 800-34 | Contingency Planning Guide | https://csrc.nist.gov/publications/detail/sp/800-34/rev-1/final |
| NIST SP 800-61 Rev. 3 | Incident Handling Guide | https://csrc.nist.gov/publications/detail/sp/800-61/rev-3/final |
| OWASP Key Management Cheat Sheet | Key Management Best Practices | https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html |
| CIS Controls v8 | Controls for Key Management | https://www.cisecurity.org/cis-controls/v8 |

### 14.2 Secrets Management Tools

| Tool | Purpose | URL |
|---|---|---|
| Mozilla SOPS | Encrypted secrets management | https://getsops.io/ |
| age | Simple file encryption | https://age-encryption.org/ |
| HashiCorp Vault | Secrets management (enterprise) | https://www.vaultproject.io/ |
| AWS Secrets Manager | Managed secrets rotation | https://aws.amazon.com/secrets-manager/ |
| GCP Secret Manager | Managed secrets | https://cloud.google.com/secret-manager |
| Doppler | Centralized secrets management | https://www.doppler.com/ |

### 14.3 Cryptographic Libraries

| Library | Purpose | URL |
|---|---|---|
| Python cryptography | Fernet, AES-GCM, key derivation | https://cryptography.io/ |
| libsodium | Modern crypto library | https://libsodium.org/ |
| age Python bindings | age encryption in Python | https://github.com/C2SP/age |

### 14.4 Audit and Compliance

| Framework | Purpose | URL |
|---|---|---|
| SOC 2 Type II | Security audit framework | https://www.aicpa.org/audit-attest/audit-and-attest-standards/at-c/soc-2-suite-of-services |
| ISO 27001 | Information security management | https://www.iso.org/isoiec-27001-information-security.html |
| GDPR | Data protection regulation | https://gdpr.eu/ |
| PCI DSS | Payment card security | https://www.pcisecuritystandards.org/ |

---

## 15. Implementable Rotation Workflow Summary

### 15.1 Quarterly Rotation Checklist (High-Risk Secrets)

For each high-risk secret (9Router, Discord, GitHub PAT, DB passwords, Redis, R2/S3, OAuth tokens, Sentry):

1. [ ] Open rotation evidence markdown.
2. [ ] Generate new credential via provider dashboard/API.
3. [ ] Test new credential in isolation.
4. [ ] Update SOPS with new credential.
5. [ ] Verify `sops -d` succeeds.
6. [ ] Deploy new credential (service restart or hot-reload).
7. [ ] Verify service health and integration tests.
8. [ ] Revoke old credential via provider.
9. [ ] Update inventory: `rotated_at`, `rotation_due_at`, `evidence_path`.
10. [ ] Write rotation evidence markdown.
11. [ ] Notify Samm if required.

### 15.2 Annual Rotation Checklist (age Key, Domain KEKs, Backup Keys)

1. [ ] Schedule maintenance window.
2. [ ] Notify Samm.
3. [ ] Generate new key material.
4. [ ] Test re-encryption/re-wrapping on non-production copy.
5. [ ] Perform rotation during maintenance window.
6. [ ] Verify all affected data accessible.
7. [ ] Update inventory and evidence.
8. [ ] Securely destroy old key material after verification.
9. [ ] Update recovery package with new material.

### 15.3 Emergency Rotation Checklist (SEV0-SEV2)

1. [ ] Declare severity.
2. [ ] Isolate affected service.
3. [ ] Revoke/disable affected credential.
4. [ ] Preserve minimal evidence (hashes, timestamps).
5. [ ] Generate replacement credential.
6. [ ] Re-encrypt/rewrap affected data.
7. [ ] Verify integrity.
8. [ ] Update inventory and key status.
9. [ ] Write incident report.
10. [ ] Notify Samm.
11. [ ] Add regression test.

---

## 16. Secret Scanner Implementation References

### 16.1 References

- **GitHub Secret Scanning:** https://docs.github.com/en/code-security/secret-scanning
- **truffleHog:** https://github.com/trufflesecurity/truffleHog
- **gitleaks:** https://github.com/gitleaks/gitleaks
- **detect-secrets:** https://github.com/Yelp/detect-secrets

### 16.2 Secret Scanner Pattern

**Implementable Pattern:**

```yaml
# .gitleaks.toml
title = "gitleaks config"

[extend]
useDefault = true

[allowlists]
paths = [
    '''node_modules''',
    '''\.git''',
    '''research-reports/.*\.md''',  # Allow historical reports
]

# Custom rules for Guinevere patterns
[[rules]]
id = "guinevere-age-key"
description = "Guinevere age private key"
regex = '''age1[a-z0-9]{58}'''
tags = ["key", "guinevere"]

[[rules]]
id = "guinevere-sops-key"
description = "Guinevere SOPS encrypted key marker"
regex = '''ENC\[AES256 GCM,.*\]'''
tags = ["sops", "guinevere"]
```

**Best Practices:**
- Run secret scanners on all commits, PRs, branches, and evidence files.
- Exclude historical evidence files that may contain revoked secrets with clear markers.
- Maintain allowlist for intentional test fixtures.
- Alert on any detected real secret immediately.
- Integrate scanner into CI/CD pipeline.

---

*Report generated: 2026-05-30 | Guinevere de Baroque — autonomous system steward*
