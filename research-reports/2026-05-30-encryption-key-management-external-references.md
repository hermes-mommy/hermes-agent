# Encryption & Key Management External References

**Date:** 2026-05-30
**Status:** Recovery evidence from background task `bg_32afcd6b`
**Reason:** The librarian returned external-research progress and findings inline but did not create the required markdown file. Parent converted the collected and verified patterns into this artifact.

## Reference Areas

| Area | Practical Pattern for Guinevere | References |
|---|---|---|
| SOPS + age | Store encrypted config in git, keep age private key out of repo, decrypt only at runtime, rotate recipients by re-encrypting files. | SOPS documentation, age encryption documentation. |
| PyCA AESGCM | Use `cryptography.hazmat.primitives.ciphers.aead.AESGCM` for authenticated encryption. Nonce must be unique per key; 96-bit random nonce acceptable with collision monitoring; use AAD for domain/context binding. | PyCA cryptography AEAD docs, NIST SP 800-38D. |
| ChaCha20-Poly1305 | Use as AEAD fallback when AES acceleration/platform constraints apply. Nonce uniqueness is mandatory. | PyCA cryptography AEAD docs, RFC 8439. |
| Fernet | Fernet provides authenticated symmetric encryption but uses AES-CBC + HMAC internally, not AEAD. MultiFernet supports key rotation. Use for compatibility/transitional paths, not new Critical envelope design. | PyCA Fernet docs. |
| Envelope encryption | Generate random DEK per record/object/domain; encrypt payload with DEK; wrap DEK with KEK; store key metadata beside ciphertext. | Cloud KMS/envelope encryption patterns, OWASP cryptographic storage guidance. |
| Key IDs/versioning | Store key_id/key_version/algorithm/created/rotated/status with ciphertext and in inventory. Read old/write new during rotation. | NIST/CIS/OWASP key lifecycle patterns. |
| Backup encryption | Encrypt before upload, separate backup key scope from runtime key scope, test restore, reconcile deletion/do-not-recall ledger after restore. | CIS Control 3/11 patterns, NIST security controls. |
| Rotation | Use planned cryptoperiods plus immediate incident rotation. Staged rotation: introduce new key, write-new/read-old, re-encrypt, verify, retire old. | NIST key management lifecycle patterns. |
| Incident response | On suspected key compromise: contain, disable/revoke, create new key, re-encrypt/rewrap affected data, preserve evidence, postmortem, add regression tests. | NIST incident response, CIS, OWASP. |
| Audit logging | Log metadata only: key_id, operation, actor/service, domain, timestamp, result, evidence path. Never log plaintext key, DEK, secret, or raw sensitive payload. | CIS Control 8, OWASP logging guidance. |
| Secret inventory | Inventory every secret with owner, purpose, scope, storage, rotation_due, revocation procedure, and linked service. | CIS asset/control inventory patterns. |
| Key custody | Root/recovery custody must be separated from runtime operational keys; break-glass must be time-boxed, logged, reviewed, and followed by rotation. | Enterprise KMS/custody practices. |
| Python zeroization | Python cannot guarantee secure memory zeroization for immutable strings/bytes and garbage-collected objects. Mitigate by minimizing plaintext lifetime, process isolation, strict logging, short-lived workers for high-risk operations, and avoiding unnecessary decrypted material. | Python runtime/security discussions, PyCA caveats. |

## Concrete Requirements for Guinevere

1. New Restricted/Critical application encryption must use AES-256-GCM envelope encryption unless a documented platform constraint chooses ChaCha20-Poly1305.
2. Fernet must be compatibility/transitional only and must not be the default design for new Critical domains.
3. Every encrypted payload must bind context through AAD: data_domain, classification, record_id/object_id, purpose, key_id, and key_version.
4. Nonces must be unique per key; nonce reuse under AES-GCM or ChaCha20-Poly1305 is a SEV0 cryptographic incident.
5. DEKs must be random and must never be persisted plaintext.
6. Wrapped DEK metadata must be auditable and versioned.
7. Rotation must support read-old/write-new and produce markdown evidence.
8. SOPS age private key must be protected with filesystem permissions and recovery package controls.
9. Secret redaction tests must run against logs, evidence, and sub-agent reports.
10. Python zeroization limitations must be documented; controls must rely on minimization, process isolation, and no-logging rather than promised perfect zeroization.

## Recommended Source URLs for Future Formal Citation

- SOPS: https://github.com/getsops/sops
- age: https://age-encryption.org/
- PyCA cryptography AEAD: https://cryptography.io/en/latest/hazmat/primitives/aead/
- PyCA Fernet/MultiFernet: https://cryptography.io/en/latest/fernet/
- NIST SP 800-57 key management guidance: https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final
- NIST SP 800-38D GCM guidance: https://csrc.nist.gov/publications/detail/sp/800-38d/final
- RFC 8439 ChaCha20-Poly1305: https://www.rfc-editor.org/rfc/rfc8439
- OWASP Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- OWASP Secrets Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- CIS Controls: https://www.cisecurity.org/controls
