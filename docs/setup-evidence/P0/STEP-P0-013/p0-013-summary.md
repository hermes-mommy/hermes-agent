# STEP-P0-013 — SOPS Secrets Structure Summary

## Overview

Created the SOPS+age encryption infrastructure per ADR-015. This is the foundation for all encrypted secret storage across Guinevere's entire lifecycle. No VPS changes — all files are local to the repository.

## What Was Created

| File | Purpose |
|---|---|
| `.sops.yaml` | SOPS configuration with 3 creation_rules (yaml/env/json) |
| `secrets/guinevere-secrets.yaml` | Master secrets file, SOPS-encrypted, 8 categories |
| `secrets/.gitignore` | Prevents accidental plaintext commits |

## Encryption Details

- **Backend**: age (via SOPS)
- **Public key**: `age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj`
- **Creation rules**: Match *.yaml, *.env, *.json under `secrets/`
- **Encrypted regex**: Catches inline `password`, `token`, `api_key`, `secret`, `key` patterns
- **Round-trip**: Encrypt → decrypt → verify PASS

## Secrets Categories (8)

1. Discord — bot token, client secret, webhook URL
2. Database — PostgreSQL credentials (guinevere, surveillance, scheduler)
3. Redis — Redis ACL passwords
4. LLM — Hermes API keys, endpoint secrets
5. Hermes — Agent-specific credentials
6. Surveillance — Monitoring access tokens
7. Observability — Prometheus/Grafana/Loki credentials
8. Backup — S3 and R2 access keys

All values are currently `PLACEHOLDER` — real values filled during service deployment phases.

## Security

- No plaintext secrets in the repository
- `.gitignore` blocks accidental plaintext commits
- SOPS uses age encryption (no GPG dependency)
- Private key stays on VPS at `/home/guinevere/secrets/age-key.txt` (0600)
- Local decryption requires `SOPS_AGE_KEY_FILE` env var

## Rollback

```bash
rm .sops.yaml secrets/guinevere-secrets.yaml secrets/.gitignore
```

No VPS changes to undo.