#!/usr/bin/env bash
# setup-service-envs.sh — Generate per-service .env files from SOPS-encrypted secrets
# Run on VPS as user guinevere. Requires: sops, age-key at ~/secrets/age-key.txt
# Usage: bash scripts/setup-service-envs.sh
# Idempotent: overwrites existing .env files with fresh decryption.
set -euo pipefail

REPO_DIR="/home/guinevere/code/guinevere"
SECRETS_DIR="/home/guinevere/secrets"
AGE_KEY="${SECRETS_DIR}/age-key.txt"
REPO_SECRETS="${REPO_DIR}/secrets"

# Validate prerequisites
if [[ ! -f "${AGE_KEY}" ]]; then
    echo "ERROR: Age key not found at ${AGE_KEY}" >&2
    exit 1
fi
export SOPS_AGE_KEY_FILE="${AGE_KEY}"

# Decrypt Redis password
REDIS_PASSWORD=$(sops --decrypt --extract '["redis_master_password"]' "${SECRETS_DIR}/redis-password.yaml" 2>/dev/null)
if [[ -z "${REDIS_PASSWORD}" ]]; then
    echo "ERROR: Failed to decrypt Redis password" >&2
    exit 1
fi

# Decrypt DB password for surveillance
DB_PASSWORD=$(sops --decrypt --extract '["guinevere_surveillance"]' "${SECRETS_DIR}/db-passwords.yaml" 2>/dev/null)
if [[ -z "${DB_PASSWORD}" ]]; then
    echo "ERROR: Failed to decrypt surveillance DB password" >&2
    exit 1
fi

# Decrypt 9Router API key (same as INITIAL_PASSWORD)
ROUTER_API_KEY=$(sops --decrypt --extract '["INITIAL_PASSWORD"]' "${REPO_SECRETS}/.env.9router" 2>/dev/null || true)
if [[ -z "${ROUTER_API_KEY}" ]]; then
    echo "WARNING: Could not decrypt 9Router API key — memory recall will be degraded" >&2
fi

# Write .env.loops
cat > "${REPO_DIR}/.env.loops" <<EOF
REDIS_PASSWORD=${REDIS_PASSWORD}
EOF
chmod 600 "${REPO_DIR}/.env.loops"

# Write .env.mcp
cat > "${REPO_DIR}/.env.mcp" <<EOF
REDIS_PASSWORD=${REDIS_PASSWORD}
EOF
chmod 600 "${REPO_DIR}/.env.mcp"

# Write .env.scheduler
cat > "${REPO_DIR}/.env.scheduler" <<EOF
REDIS_PASSWORD=${REDIS_PASSWORD}
EOF
chmod 600 "${REPO_DIR}/.env.scheduler"

# Write .env.surveillance
cat > "${REPO_DIR}/.env.surveillance" <<EOF
REDIS_PASSWORD=${REDIS_PASSWORD}
GUINEVERE_DB_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql+asyncpg://guinevere_surveillance:${DB_PASSWORD}@localhost:5434/guinevere_surveillance
SURVEILLANCE_HMAC_KEY=$(openssl rand -hex 32)
EOF
chmod 600 "${REPO_DIR}/.env.surveillance"

# Write .env.core (if 9Router API key available)
if [[ -n "${ROUTER_API_KEY}" ]]; then
    cat > "${REPO_DIR}/.env.core" <<EOF
GUINEVERE_9ROUTER_API_KEY=${ROUTER_API_KEY}
EOF
    chmod 600 "${REPO_DIR}/.env.core"
fi

# Append GUINEVERE_9ROUTER_API_KEY to .env.discord if not already present
if [[ -n "${ROUTER_API_KEY}" ]] && [[ -f "${REPO_DIR}/.env.discord" ]]; then
    if ! grep -q 'GUINEVERE_9ROUTER_API_KEY' "${REPO_DIR}/.env.discord"; then
        echo "GUINEVERE_9ROUTER_API_KEY=${ROUTER_API_KEY}" >> "${REPO_DIR}/.env.discord"
    fi
fi

echo "Done. Generated .env files:"
for f in .env.loops .env.mcp .env.scheduler .env.surveillance .env.core; do
    if [[ -f "${REPO_DIR}/${f}" ]]; then
        echo "  ${REPO_DIR}/${f} ($(wc -l < "${REPO_DIR}/${f}") vars)"
    fi
done

# Reload systemd to pick up changes
echo "Reloading systemd..."
sudo systemctl daemon-reload
echo "systemd reloaded. Start services with:"
echo "  sudo systemctl start guinevere-loops guinevere-mcp guinevere-scheduler guinevere-surveillance"
