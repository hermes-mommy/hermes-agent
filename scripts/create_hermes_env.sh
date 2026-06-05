#!/bin/bash
# Create ~/.hermes/.env from existing .env.discord values
set -euo pipefail

ENV_SOURCE="/home/guinevere/code/guinevere/.env.discord"
ENV_TARGET="$HOME/.hermes/.env"

if [ ! -f "$ENV_SOURCE" ]; then
    echo "ERROR: $ENV_SOURCE not found"
    exit 1
fi

# Source the existing env file
source "$ENV_SOURCE"

cat > "$ENV_TARGET" << 'HEADER'
# Hermes Agent Environment — Phase 2 Wave 4 Cutover
# Generated from .env.discord values
HEADER

cat >> "$ENV_TARGET" << EOF
# Discord
DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
DISCORD_ALLOWED_USERS=1146639950654214264
DISCORD_ALLOWED_CHANNELS=1510914600777023659
DISCORD_REQUIRE_MENTION=false
DISCORD_FREE_RESPONSE_CHANNELS=1510914600777023659

# LLM (9Router)
NINEROUTER_API_KEY=${GUINEVERE_9ROUTER_API_KEY}
LLM_BASE_URL=http://localhost:20128/v1
LLM_MODEL=gpt-5.5
LLM_FALLBACK_MODEL=deepseek-v4-flash

# Data Stores
DATABASE_URL=${DATABASE_URL}
REDIS_URL=redis://localhost:6380/5

# Memory
MEMORY_BACKEND=redis
GROUP_SESSIONS_PER_USER=true

# Observability
PROMETHEUS_METRICS_PORT=9191
LOG_LEVEL=info
LOG_FORMAT=json

# Shadow Mode (Phase 2)
DISCORD_SHADOW_BOT_TOKEN=${DISCORD_SHADOW_BOT_TOKEN}
DISCORD_SHADOW_BOT_ID=${DISCORD_SHADOW_BOT_ID}
DISCORD_SHADOW_CHANNEL_ID=${DISCORD_SHADOW_CHANNEL_ID}
SHADOW_ENABLED=${SHADOW_ENABLED}
SHADOW_TRAFFIC_PCT=${SHADOW_TRAFFIC_PCT}
EOF

chmod 600 "$ENV_TARGET"
echo "Created $ENV_TARGET (mode 600)"
echo "Verifying key vars..."
grep -c "DISCORD_BOT_TOKEN=" "$ENV_TARGET" && echo "  DISCORD_BOT_TOKEN: present"
grep -c "NINEROUTER_API_KEY=" "$ENV_TARGET" && echo "  NINEROUTER_API_KEY: present"
grep -c "DATABASE_URL=" "$ENV_TARGET" && echo "  DATABASE_URL: present"
grep -c "REDIS_URL=" "$ENV_TARGET" && echo "  REDIS_URL: present"
grep -c "DISCORD_ALLOWED_USERS=" "$ENV_TARGET" && echo "  DISCORD_ALLOWED_USERS: present"
grep "DISCORD_ALLOWED_USERS" "$ENV_TARGET"
