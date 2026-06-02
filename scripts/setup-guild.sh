#!/usr/bin/env bash
set -euo pipefail

STEP=""
if [[ "${1:-}" == "--step" && -n "${2:-}" ]]; then
  STEP="$2"
elif [[ -n "${1:-}" ]]; then
  STEP="$1"
else
  echo "usage: scripts/setup-guild.sh --step p2-004|p2-005|p2-006" >&2
  exit 2
fi

case "$STEP" in
  p2-004|p2-005|p2-006) ;;
  *) echo "invalid step: $STEP" >&2; exit 2 ;;
esac

PROJECT_ROOT="/home/guinevere/code/guinevere"
SECRET_FILE="$PROJECT_ROOT/secrets/discord-secrets.yaml"
AGE_KEY_FILE="/home/guinevere/secrets/age-key.txt"
TEMP_SECRETS="$(mktemp /tmp/guinevere-discord-secrets.XXXXXX.yaml)"

cleanup() {
  unset DISCORD_SECRETS_PATH || true
  shred -u "$TEMP_SECRETS" 2>/dev/null || rm -f "$TEMP_SECRETS"
}
trap cleanup EXIT

export SOPS_AGE_KEY_FILE="$AGE_KEY_FILE"
sops --decrypt "$SECRET_FILE" > "$TEMP_SECRETS"
chmod 600 "$TEMP_SECRETS"
export DISCORD_SECRETS_PATH="$TEMP_SECRETS"

cd "$PROJECT_ROOT"
"$PROJECT_ROOT/.venv/bin/python" tmp/setup-discord-guild.py --step "$STEP"
